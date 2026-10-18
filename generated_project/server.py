"""Remote Command Management System - Server (Command Center).

The server listens for incoming agent connections, keeps track of every
connected client, and lets the operator send shell commands to a specific
client (or broadcast to all of them). Results are relayed back and printed.

Usage:
    python server.py [--host HOST] [--port PORT]

    --host   Address to bind (default 0.0.0.0)
    --port   TCP port to listen on (default 5555)
"""

import argparse
import json
import socket
import threading
import uuid

from protocol import recv_msg, send_msg


class ClientSession:
    """Represents one connected agent."""

    def __init__(self, sock, addr, cid):
        self.sock = sock
        self.addr = addr
        self.cid = cid
        self._send_lock = threading.Lock()

    def send(self, msg):
        with self._send_lock:
            send_msg(self.sock, msg)

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


class CommandServer:
    """Central command center managing many connected agents."""

    def __init__(self, host="0.0.0.0", port=5555):
        self.host = host
        self.port = port
        self.clients = {}  # cid -> ClientSession
        self._lock = threading.Lock()
        self._running = False
        self._server_sock = None
        self._accept_thread = None
        # Optional callback: on_event(event_type, data). Used by tests and
        # integrations to observe results without touching the wire sockets.
        self.on_event = None

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _track(self, session):
        with self._lock:
            self.clients[session.cid] = session

    def _untrack(self, cid):
        with self._lock:
            return self.clients.pop(cid, None)

    def list_clients(self):
        with self._lock:
            return [
                {"cid": cid, "addr": s.addr}
                for cid, s in self.clients.items()
            ]

    def _announce(self, title, text=""):
        print("=" * 60)
        print(title)
        if text:
            print(text)
        print("Syntax:  SEND  <cid>  <command...>")
        print("         LIST")
        print("         BROADCAST  <command...>")
        print("         EXIT")
        print("=" * 60)

    # ------------------------------------------------------------------ #
    # Client reader loop (runs in its own thread)
    # ------------------------------------------------------------------ #
    def _handle_client(self, session):
        cid = session.cid
        print(f"[+] Client connected  cid={cid}  addr={session.addr[0]}:{session.addr[1]}")
        while True:
            try:
                msg = recv_msg(session.sock)
            except (ConnectionError, OSError):
                break
            except Exception as exc:
                print(f"[!] Bad message from {cid}: {exc}")
                break

            mtype = msg.get("type")
            if mtype == "hello":
                print(f"[i] Client registered: {msg.get('hostname', 'unknown')}")
            elif mtype == "result":
                print(f"\n[RESULT] cid={cid}  cmd={msg.get('command', '')!r}")
                print(f"--- exit code: {msg.get('returncode')} ---")
                if msg.get("stdout"):
                    print(msg["stdout"].rstrip())
                if msg.get("stderr"):
                    print("[stderr]", msg["stderr"].rstrip())
                print("-----------------------------------------")
            elif mtype == "pong":
                print(f"[PONG] cid={cid}")
            else:
                print(f"[i] Unknown message from {cid}: {mtype}")

            if self.on_event is not None:
                data = dict(msg)
                data["cid"] = cid
                try:
                    self.on_event(mtype, data)
                except Exception:
                    pass

        self._untrack(cid)
        session.close()
        print(f"[-] Client disconnected  cid={cid}")

    # ------------------------------------------------------------------ #
    # Accept loop (runs in its own thread)
    # ------------------------------------------------------------------ #
    def _accept_loop(self):
        while self._running:
            try:
                sock, addr = self._server_sock.accept()
            except OSError:
                break
            session = ClientSession(sock, addr, uuid.uuid4().hex[:8])
            self._track(session)
            threading.Thread(
                target=self._handle_client,
                args=(session,),
                daemon=True,
            ).start()

    # ------------------------------------------------------------------ #
    # Server lifecycle
    # ------------------------------------------------------------------ #
    def start(self):
        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind((self.host, self.port))
        self._server_sock.listen(16)
        self._running = True
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()
        print(f"[*] Server listening on {self.host}:{self.port}")
        self._announce("Welcome to Remote Command Server")

    def stop(self):
        self._running = False
        if self._server_sock is not None:
            try:
                self._server_sock.close()
            except OSError:
                pass
        with self._lock:
            for session in list(self.clients.values()):
                session.close()
            self.clients.clear()
        print("[*] Server stopped")

    # ------------------------------------------------------------------ #
    # Operator commands
    # ------------------------------------------------------------------ #
    def _require_clients(self):
        clients = self.list_clients()
        if not clients:
            print("No clients connected.")
            return None
        return clients

    def cmd_list(self):
        clients = self._require_clients()
        if clients is None:
            return
        print(f"{len(clients)} client(s) connected:")
        for c in clients:
            print(f"  {c['cid']}   {c['addr'][0]}:{c['addr'][1]}")

    def cmd_send(self, cid, command):
        with self._lock:
            session = self.clients.get(cid)
        if session is None:
            print(f"Unknown client cid={cid}")
            return
        session.send({"type": "exec", "command": command})
        print(f"[>] Command sent to {cid}: {command!r}")

    def cmd_broadcast(self, command):
        clients = self._require_clients()
        if clients is None:
            return
        sent = 0
        cids = [c["cid"] for c in clients]
        with self._lock:
            for cid in cids:
                session = self.clients.get(cid)
                if session is not None:
                    session.send({"type": "exec", "command": command})
                    sent += 1
        print(f"[>] Broadcast sent to {sent} client(s): {command!r}")

    # ------------------------------------------------------------------ #
    # Interactive REPL
    # ------------------------------------------------------------------ #
    def run(self):
        while True:
            try:
                raw = input("server> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not raw:
                continue
            parts = raw.split(maxsplit=1)
            verb = parts[0].upper()
            arg = parts[1] if len(parts) > 1 else ""

            if verb in ("EXIT", "QUIT"):
                break
            elif verb == "LIST":
                self.cmd_list()
            elif verb == "SEND":
                sub = arg.split(maxsplit=1)
                if len(sub) != 2:
                    print("Usage: SEND <cid> <command...>")
                    continue
                self.cmd_send(sub[0], sub[1])
            elif verb == "BROADCAST":
                if not arg:
                    print("Usage: BROADCAST <command...>")
                    continue
                self.cmd_broadcast(arg)
            else:
                print(f"Unknown command: {verb}")
                self._announce("Available commands")
        self.stop()


def main():
    parser = argparse.ArgumentParser(description="Remote Command Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind address (default 0.0.0.0)")
    parser.add_argument("--port", type=int, default=5555, help="TCP port (default 5555)")
    args = parser.parse_args()

    server = CommandServer(host=args.host, port=args.port)
    try:
        server.start()
        server.run()
    except KeyboardInterrupt:
        server.stop()


if __name__ == "__main__":
    main()
