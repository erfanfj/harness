"""Remote Command Management System - Client (Agent).

The client dials the server, registers itself, and then waits for `exec`
commands. Whenever the server sends a command it runs it with
`subprocess.run` and streams the captured output back as a `result`
message.

By default the client runs commands through **PowerShell** on Windows,
so you can type PowerShell commands (Get-ChildItem, Get-Process, etc.)
straight from the server console. If PowerShell is unavailable it falls
back to the platform default shell.

Usage:
    python client.py [--host HOST] [--port PORT] [--shell SHELL]

    --host   Server address (default 127.0.0.1)
    --port   Server TCP port (default 5555)
    --shell  Shell used to run commands:
                 powershell  -> use PowerShell (default on Windows)
                 cmd         -> use Windows cmd.exe
                 auto        -> PowerShell if available, else default shell
"""

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time

from protocol import recv_msg, send_msg

# Executable names used to locate the PowerShell binary.
_PWSH_NAMES = ("pwsh", "powershell")


def _find_powershell():
    """Return the PowerShell executable path, or None if not found."""
    for name in _PWSH_NAMES:
        path = shutil.which(name)
        if path:
            return path
    return None


def resolve_shell(choice):
    """Resolve a --shell argument to a concrete shell configuration.

    Returns a dict with:
        name      : "powershell" | "cmd" | "auto"
        executable: list of command prefixes (or None)
        ls_command: the platform file-listing command for tests
    """
    choice = (choice or "").strip().lower()

    if choice in ("powershell", "ps"):
        ps = _find_powershell()
        if ps is None:
            raise SystemExit(
                "PowerShell executable not found. Install PowerShell or "
                "use --shell auto/cmd."
            )
        return {
            "name": "powershell",
            "executable": [ps, "-NoProfile", "-Command"],
            "ls_command": "Get-ChildItem",
        }

    if choice in ("cmd", "cmd.exe"):
        return {
            "name": "cmd",
            "executable": ["cmd.exe", "/c"],
            "ls_command": "dir",
        }

    # auto: PowerShell if available, otherwise default shell.
    ps = _find_powershell()
    if ps is not None:
        return {
            "name": "powershell",
            "executable": [ps, "-NoProfile", "-Command"],
            "ls_command": "Get-ChildItem",
        }
    return {
        "name": "auto",
        "executable": None,
        "ls_command": "dir" if os.name == "nt" else "ls",
    }


def run_command(command, shell, timeout=None):
    """Execute *command* through the configured shell.

    Returns (returncode, stdout, stderr). If `shell` has an `executable`
    list, the command is run as an argument to that executable (PowerShell
    or cmd). Otherwise it is run through the platform default shell.
    """
    executable = shell.get("executable")
    if executable is not None:
        args = executable + [command]
        return _spawn(args, shell=False, timeout=timeout)

    # Default-platform shell fallback.
    return _spawn(command, shell=True, timeout=timeout)


def _spawn(args, shell, timeout):
    proc = subprocess.run(
        args,
        shell=shell,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout, proc.stderr


class Agent:
    def __init__(self, host="127.0.0.1", port=5555, reconnect_delay=3.0, shell=None):
        self.host = host
        self.port = port
        self.reconnect_delay = reconnect_delay
        self.shell = resolve_shell(shell or "powershell")
        self.sock = None

    # ------------------------------------------------------------------ #
    # Connection handling
    # ------------------------------------------------------------------ #
    def connect(self):
        self.sock = socket.create_connection((self.host, self.port), timeout=10)
        self.sock.settimeout(None)
        send_msg(self.sock, {"type": "hello", "hostname": socket.gethostname()})
        print(f"[*] Connected to {self.host}:{self.port} as {socket.gethostname()}")

    def disconnect(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

    # ------------------------------------------------------------------ #
    # Main loop
    # ------------------------------------------------------------------ #
    def run_forever(self, auto_reconnect=True):
        while True:
            try:
                self.connect()
            except (OSError, ConnectionError) as exc:
                if not auto_reconnect:
                    print(f"[!] Cannot connect: {exc}")
                    return
                print(f"[!] Cannot connect ({exc}); retrying in {self.reconnect_delay}s...")
                time.sleep(self.reconnect_delay)
                continue

            self._message_loop()

            # Message loop ended -> connection lost
            self.disconnect()
            if not auto_reconnect:
                print("[!] Connection closed by server")
                return
            print(f"[!] Connection lost; reconnecting in {self.reconnect_delay}s...")
            time.sleep(self.reconnect_delay)

    def _message_loop(self):
        while True:
            try:
                msg = recv_msg(self.sock)
            except (ConnectionError, OSError):
                return

            mtype = msg.get("type")
            if mtype == "exec":
                self._handle_exec(msg.get("command", ""))
            elif mtype == "ping":
                send_msg(self.sock, {"type": "pong"})
            elif mtype == "shutdown":
                print("[*] Shutdown requested by server")
                self.disconnect()
                raise SystemExit(0)
            else:
                print(f"[i] Ignoring unknown message: {mtype}")

    def _handle_exec(self, command):
        if not command or not isinstance(command, str):
            send_msg(self.sock, {
                "type": "result",
                "command": command,
                "returncode": -1,
                "stdout": "",
                "stderr": "empty command",
            })
            return

        print(f"[>] Executing: {command}")
        try:
            returncode, stdout, stderr = run_command(command, self.shell)
        except subprocess.TimeoutExpired:
            returncode, stdout, stderr = -2, "", "command timed out"
        except OSError as exc:
            returncode, stdout, stderr = -3, "", str(exc)

        send_msg(self.sock, {
            "type": "result",
            "command": command,
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
        })
        print(f"[<] Result sent (exit code {returncode})")


def main():
    parser = argparse.ArgumentParser(description="Remote Command Client (Agent)")
    parser.add_argument("--host", default="127.0.0.1", help="Server address (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5555, help="Server TCP port (default 5555)")
    parser.add_argument(
        "--shell",
        default="powershell",
        choices=["powershell", "ps", "cmd", "auto"],
        help="Shell used to run commands (default: powershell)",
    )
    args = parser.parse_args()

    Agent(host=args.host, port=args.port, shell=args.shell).run_forever()


if __name__ == "__main__":
    main()
