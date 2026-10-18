"""Live end-to-end test: real server.py + real client.py as separate OS
processes talking over real TCP, with the interactive server console
driven automatically.

This is the closest possible reproduction of the real two-terminal usage:

    Terminal 1:  python server.py --host 127.0.0.1 --port 5577
    Terminal 2:  python client.py --host 127.0.0.1 --port 5577

Here we manage both stdin of the server (typing SEND/LIST commands) and
capture its stdout to confirm the result comes back intact.
"""

import re
import subprocess
import sys
import threading
import time

PORT = 5577
CID_RE = re.compile(r"\s+([0-9a-f]{8})\s+127\.0\.0\.1:\d+")


def read_stream(stream, label, sink):
    """Continuously read a subprocess stream line by line into `sink`."""
    for line in iter(stream.readline, ""):
        line = line.rstrip()
        sink.append(line)
        print(f"[{label}] {line}", flush=True)
    stream.close()


def main():
    server_proc = subprocess.Popen(
        [sys.executable, "server.py", "--host", "127.0.0.1", "--port", str(PORT)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    client_proc = subprocess.Popen(
        [sys.executable, "client.py", "--host", "127.0.0.1", "--port", str(PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    server_out = []
    client_out = []

    t_server = threading.Thread(target=read_stream, args=(server_proc.stdout, "server", server_out), daemon=True)
    t_client = threading.Thread(target=read_stream, args=(client_proc.stdout, "client", client_out), daemon=True)
    t_server.start()
    t_client.start()

    try:
        time.sleep(2.5)
        assert server_proc.poll() is None, "server crashed at startup"
        assert client_proc.poll() is None, "client crashed at startup"

        # Ask the server to list its clients so we can learn the real cid.
        server_proc.stdin.write("LIST\n")
        server_proc.stdin.flush()
        time.sleep(0.8)

        cid = None
        for line in server_out:
            m = CID_RE.search(line)
            if m:
                cid = m.group(1)
                break

        if cid is None:
            print("[FAIL] Could not extract a client cid from LIST output")
            return 1
        print(f"[TEST] Using cid={cid}")

        # Real PowerShell command via Get-ChildItem.
        ps_ls = "Get-ChildItem | Out-String"
        commands = [
            "hostname",
            "Write-Output 'PS_HELLO_123'",
            ps_ls,
        ]

        for command in commands:
            line = f"SEND {cid} {command}"
            server_proc.stdin.write(line + "\n")
            server_proc.stdin.flush()
            time.sleep(2.2)

        server_proc.stdin.write("EXIT\n")
        server_proc.stdin.flush()
        server_proc.stdin.close()
        server_proc.wait(timeout=8.0)
        client_proc.terminate()
        try:
            client_proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            client_proc.kill()

        combined = "\n".join(server_out + client_out)
        print("\n" + "=" * 60)
        print("FULL CAPTURED OUTPUT (end):")

        ok = True
        checks = [
            ("Client connected", "client registration"),
            (f"[RESULT] cid={cid}", "a RESULT block for our cid"),
            ("exit code: 0", "at least one success (exit 0)"),
            ("PS_HELLO_123", "PowerShell Write-Output output"),
        ]
        for needle, desc in checks:
            if needle in combined:
                print(f"[OK] contains {needle!r} ({desc})")
            else:
                print(f"[FAIL] missing {needle!r} ({desc})")
                ok = False

        # The Get-ChildItem listing should produce several filename matches,
        # and must NOT contain the classic cmd.exe "not recognized" error.
        for marker in ("client.py", "server.py", "README.md"):
            if marker in combined:
                print(f"[OK] directory listing contains {marker!r}")
            else:
                print(f"[FAIL] directory listing missing {marker!r}")
                ok = False
        if "not recognized" in combined.lower():
            print("[FAIL] found a cmd.exe 'not recognized' error -> shell fallback happened")
            ok = False
        else:
            print("[OK] no cmd.exe fallback errors (PowerShell used)")

        print("=" * 60)
        print("E2E RESULT:", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    finally:
        for p in (server_proc, client_proc):
            if p and p.poll() is None:
                p.terminate()


if __name__ == "__main__":
    sys.exit(main())
