"""End-to-end tests for the remote command management system.

These tests spin up a real CommandServer on an ephemeral port, connect
a real Agent client, and verify that commands sent by the server are
executed on the client and the results are received back through the
server's own message-handling path (via the `on_event` callback).
"""

import os
import queue
import socket
import threading
import time

import pytest

from client import Agent, resolve_shell, run_command
from server import CommandServer


@pytest.fixture
def server():
    srv = CommandServer(host="127.0.0.1", port=0)
    srv._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv._server_sock.bind(("127.0.0.1", 0))
    srv.port = srv._server_sock.getsockname()[1]
    srv._server_sock.listen(8)
    srv._running = True
    srv._accept_thread = threading.Thread(target=srv._accept_loop, daemon=True)
    srv._accept_thread.start()
    yield srv
    srv.stop()


def wait_until(predicate, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def make_client(server_host, server_port, shell="powershell"):
    agent = Agent(host=server_host, port=server_port, shell=shell)
    agent.connect()
    # Start the client's message loop (this is what Agent.run_forever
    # normally does after connect()) so the test client can actually
    # receive and answer messages from the server.
    thread = threading.Thread(target=agent._message_loop, daemon=True)
    thread.start()
    agent._test_thread = thread
    return agent


def test_run_command_echo():
    returncode, stdout, stderr = run_command("echo hello", {"name": "auto", "executable": None})
    assert returncode == 0
    assert "hello" in stdout
    assert stderr == ""


def test_client_connects_and_registers(server):
    agent = make_client("127.0.0.1", server.port)
    try:
        assert wait_until(lambda: len(server.list_clients()) == 1)
        info = server.list_clients()[0]
        assert info["cid"]
        assert info["addr"][0] == "127.0.0.1"
    finally:
        agent.disconnect()


def test_server_sends_command_and_receives_result(server):
    results = queue.Queue()

    def on_event(mtype, data):
        if mtype == "result":
            results.put(data)

    server.on_event = on_event

    agent = make_client("127.0.0.1", server.port)
    try:
        assert wait_until(lambda: len(server.list_clients()) == 1)
        cid = server.list_clients()[0]["cid"]

        server.cmd_send(cid, "echo remote-ok-123")
        try:
            result = results.get(timeout=5)
        except queue.Empty:
            pytest.fail("server did not receive a result in time")

        assert "remote-ok-123" in result.get("stdout", "")
        assert result.get("returncode") == 0
        assert result.get("command") == "echo remote-ok-123"
        assert result["cid"] == cid
    finally:
        agent.disconnect()


def test_broadcast_to_all_clients(server):
    results = queue.Queue()

    def on_event(mtype, data):
        if mtype == "result":
            results.put(data)

    server.on_event = on_event

    agents = [make_client("127.0.0.1", server.port) for _ in range(2)]
    try:
        assert wait_until(lambda: len(server.list_clients()) == 2)
        server.cmd_broadcast("echo broadcast-hello")

        got = []
        deadline = time.time() + 5
        while len(got) < 2 and time.time() < deadline:
            try:
                got.append(results.get(timeout=0.5))
            except queue.Empty:
                continue

        assert len(got) == 2, f"expected one result per client, got {len(got)}"
        for r in got:
            assert "broadcast-hello" in r.get("stdout", "")
            assert r.get("returncode") == 0
    finally:
        for a in agents:
            a.disconnect()


def test_ping_pong(server):
    pongs = queue.Queue()

    def on_event(mtype, data):
        if mtype == "pong":
            pongs.put(data)

    server.on_event = on_event

    agent = make_client("127.0.0.1", server.port)
    try:
        assert wait_until(lambda: len(server.list_clients()) == 1)
        cid = server.list_clients()[0]["cid"]

        with server._lock:
            session = server.clients[cid]
        session.send({"type": "ping"})

        try:
            data = pongs.get(timeout=5)
        except queue.Empty:
            pytest.fail("server did not receive pong in time")
        assert data["cid"] == cid
    finally:
        agent.disconnect()


def test_unknown_client_send_is_ignored(server):
    server.cmd_send("nonexistent-cid", "echo nope")  # should not raise


# --------------------------------------------------------------------- #
# PowerShell shell handling
# --------------------------------------------------------------------- #
POWER_AVAILABLE = None  # memoized


def _powershell_available():
    global POWER_AVAILABLE
    if POWER_AVAILABLE is None:
        ps = resolve_shell("powershell")
        POWER_AVAILABLE = bool(ps and ps.get("executable"))
    return POWER_AVAILABLE


def test_resolve_shell_defaults_on_windows():
    # On Windows the default resolves to PowerShell when it exists.
    default = resolve_shell("powershell")
    if os.name == "nt":
        assert default["name"] == "powershell"
        assert default["executable"] is not None
    else:
        # Fallback to default shell on other platforms.
        assert default["name"] in ("powershell", "auto")


@pytest.mark.skipif(not _powershell_available(), reason="PowerShell not installed")
def test_run_command_through_powershell():
    ps = resolve_shell("powershell")
    rc, out, err = run_command("Write-Output 'ps-hello'", ps)
    assert rc == 0
    assert "ps-hello" in out


@pytest.mark.skipif(not _powershell_available(), reason="PowerShell not installed")
def test_powershell_get_childitem(server):
    results = queue.Queue()

    def on_event(mtype, data):
        if mtype == "result":
            results.put(data)

    server.on_event = on_event
    agent = make_client("127.0.0.1", server.port, shell="powershell")
    try:
        assert wait_until(lambda: len(server.list_clients()) == 1)
        cid = server.list_clients()[0]["cid"]
        server.cmd_send(cid, "Get-ChildItem | Select-Object -First 3 | Out-String")
        try:
            res = results.get(timeout=8)
        except queue.Empty:
            pytest.fail("no PowerShell Get-ChildItem result received")

        assert res.get("returncode") == 0
        # PowerShell's own output; check it is not a cmd error message.
        assert "not recognized" not in res.get("stderr", "").lower()
    finally:
        agent.disconnect()
