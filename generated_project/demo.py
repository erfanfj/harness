"""Live demo: start a real server + real client and send commands.

This mimics the exact production flow (server.py + client.py) but runs
both sides inside one process so you can see the results immediately.

It sends:
    - `ls`   (works when the client runs on Linux/macOS)
    - `dir`  (works when the client runs on Windows)

and prints whatever comes back.
"""

import queue
import socket
import threading
import time

import server as server_mod
from client import Agent

RESULTS = queue.Queue()


def on_event(mtype, data):
    if mtype == "result":
        RESULTS.put(data)


def wait_until(predicate, timeout=5.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(0.05)
    return False


def main():
    srv = server_mod.CommandServer(host="127.0.0.1", port=0)
    srv.on_event = on_event

    # Bind to an ephemeral port (same trick the tests use).
    srv._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv._server_sock.bind(("127.0.0.1", 0))
    srv.port = srv._server_sock.getsockname()[1]
    srv._server_sock.listen(8)
    srv._running = True
    srv._accept_thread = threading.Thread(target=srv._accept_loop, daemon=True)
    srv._accept_thread.start()

    # Real client agent.
    agent = Agent(host="127.0.0.1", port=srv.port)
    agent.connect()
    threading.Thread(target=agent._message_loop, daemon=True).start()

    assert wait_until(lambda: len(srv.list_clients()) == 1)
    cid = srv.list_clients()[0]["cid"]
    print(f"\n[CLIENT CONNECTED] cid={cid}\n")

    for command in ("ls", "dir"):
        print("=" * 60)
        print(f"SENDING: {command!r}  ->  cid={cid}")
        print("=" * 60)
        srv.cmd_send(cid, command)
        try:
            res = RESULTS.get(timeout=10)
        except queue.Empty:
            print("!! no result received in time !!\n")
            continue

        print(f"\n[RESULT] exit code: {res.get('returncode')}")
        print(f"[STDOUT]\n{res.get('stdout', '').rstrip()}")
        if res.get("stderr"):
            print(f"[STDERR]\n{res.get('stderr','').rstrip()}")
        print()

    srv.stop()
    agent.disconnect()
    print("[DONE]")


if __name__ == "__main__":
    main()
