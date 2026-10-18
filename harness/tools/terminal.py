import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any


class TerminalTools:
    """
    Executes shell commands in the target workspace directory with robust timeout handling,
    process tree termination, and output truncation to prevent infinite hanging.
    """

    def __init__(self, workspace_dir: Path, default_timeout: int = 60):
        self.workspace_dir = workspace_dir.resolve()
        self.default_timeout = default_timeout

    def execute_command(self, command: str, timeout: Any = 0) -> str:
        """
        Executes a shell command in the project workspace directory.
        - Uses stdin=DEVNULL to prevent hanging on interactive input prompts.
        - Forcefully terminates the full process tree on timeout.
        - Captures partial output produced up to timeout.
        - Truncates excessive output to preserve context.
        """
        # Safely convert timeout parameter (handles strings, floats, ints)
        try:
            eff_timeout = int(float(timeout)) if timeout else self.default_timeout
        except (ValueError, TypeError):
            eff_timeout = self.default_timeout

        if eff_timeout <= 0:
            eff_timeout = self.default_timeout

        start_time = time.time()
        is_win = os.name == "nt"

        try:
            proc = subprocess.Popen(
                command,
                cwd=str(self.workspace_dir),
                shell=True,
                stdin=subprocess.DEVNULL,  # Prevent blocking on interactive prompts
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                start_new_session=(not is_win),  # New process group on Unix
            )

            timed_out = False
            try:
                stdout, stderr = proc.communicate(timeout=eff_timeout)
                exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
                exit_code = 124  # Standard timeout exit code

                # Forcefully kill the entire process tree
                if is_win:
                    try:
                        subprocess.run(
                            f"taskkill /F /T /PID {proc.pid}",
                            shell=True,
                            capture_output=True,
                            timeout=5,
                        )
                    except Exception:
                        pass
                else:
                    try:
                        pgid = os.getpgid(proc.pid)
                        os.killpg(pgid, signal.SIGKILL)
                    except Exception:
                        pass

                try:
                    proc.kill()
                except Exception:
                    pass

                # Cleanly retrieve any output collected before termination
                try:
                    stdout, stderr = proc.communicate(timeout=2)
                except Exception:
                    stdout, stderr = "", ""

            duration = round(time.time() - start_time, 2)
            stdout = (stdout or "").strip()
            stderr = (stderr or "").strip()

            combined = []
            if stdout:
                combined.append(f"STDOUT:\n{stdout}")
            if stderr:
                combined.append(f"STDERR:\n{stderr}")
            if not combined:
                combined.append("(Command produced no output)")

            raw_output = "\n\n".join(combined)

            # Limit output lines if too verbose
            lines = raw_output.splitlines()
            max_lines = 140
            if len(lines) > max_lines:
                head = lines[:70]
                tail = lines[-70:]
                omitted = len(lines) - 140
                truncated_output = (
                    "\n".join(head)
                    + f"\n\n... [{omitted} lines omitted to save context] ...\n\n"
                    + "\n".join(tail)
                )
            else:
                truncated_output = raw_output

            if timed_out:
                status = f"TIMED_OUT (Exceeded {eff_timeout}s limit; process tree terminated)"
            elif exit_code == 0:
                status = "SUCCESS"
            else:
                status = f"FAILED (Exit Code {exit_code})"

            result_str = (
                f"Command: {command}\n"
                f"Status: {status}\n"
                f"Duration: {duration}s\n"
                f"Output:\n{truncated_output}"
            )
            return result_str

        except Exception as e:
            duration = round(time.time() - start_time, 2)
            return f"Error executing command: {str(e)} (Duration: {duration}s)."
