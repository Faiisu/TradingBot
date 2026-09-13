import json
import os
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

import psutil

LOG_TAIL_LINES = 30


class AlreadyRunning(RuntimeError):
    pass


class NotRunning(RuntimeError):
    pass


class PaperTradingSupervisor:
    """Starts, stops and reports on the paper trading loop as a separate child process, so the dashboard can
    crash or restart without touching trading. Everything it knows lives on disk (PID file + log), not in
    memory, so a restarted dashboard still sees a session it started earlier.

    Stop is cooperative: it writes a stop-request file the loop checks every second (see
    paper/loop.py wait_or_stop), letting the loop shut MT5 down cleanly. A process that ignores it is
    terminated after stop_timeout seconds."""

    def __init__(self, command: list[str], data_dir: Path, cwd: Path, script_marker: str, stop_timeout: float = 15.0):
        self.command = command
        self.cwd = cwd
        self.script_marker = script_marker
        self.stop_timeout = stop_timeout
        self.pid_path = data_dir / "paper_trading.pid"
        self.stop_path = data_dir / "paper_trading.stop"
        self.log_path = data_dir / "paper_trading.log"
        self._proc: subprocess.Popen | None = None
        self._lock = threading.Lock()

    # --- public API ---

    def start(self) -> dict:
        with self._lock:
            current = self.status()
            if current["state"] in ("running", "stopping", "running_external"):
                raise AlreadyRunning(f"Paper trading is already {current['state'].replace('_', ' ')}.")

            self.pid_path.parent.mkdir(parents=True, exist_ok=True)
            if self.stop_path.exists():
                self.stop_path.unlink()

            # Windows: its own process group (Ctrl+C in the dashboard's terminal doesn't reach it) and no shared
            # console (closing that terminal window doesn't kill it). Output goes to the log file instead.
            creationflags = (
                subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS if sys.platform == "win32" else 0
            )
            with open(self.log_path, "w", encoding="utf-8") as log:
                self._proc = subprocess.Popen(
                    self.command,
                    cwd=self.cwd,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    # UTF-8 so the log (read back as UTF-8 for the page) survives Windows' default code page
                    env={**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1"},
                    creationflags=creationflags,
                )

            self._write_pid_file(
                {
                    "pid": self._proc.pid,
                    "create_time": psutil.Process(self._proc.pid).create_time(),
                    "started_at": _now(),
                    "stop_requested_at": None,
                }
            )
            return self.status()

    def stop(self) -> dict:
        with self._lock:
            current = self.status()
            if current["state"] != "running":
                raise NotRunning(f"Paper trading is not running (it is {current['state'].replace('_', ' ')}).")

            info = self._read_pid_file()
            info["stop_requested_at"] = _now()
            self._write_pid_file(info)
            self.stop_path.write_text(info["stop_requested_at"], encoding="utf-8")

            threading.Thread(target=self._terminate_if_stuck, args=(info,), daemon=True).start()
            return self.status()

    def status(self) -> dict:
        info = self._read_pid_file()
        process = self._our_process(info)
        base = {
            "pid": info.get("pid") if info else None,
            "started_at": info.get("started_at") if info else None,
            "stop_requested_at": info.get("stop_requested_at") if info else None,
            "exit_code": self._exit_code(),
            "log_tail": self._log_tail(),
        }

        if process is not None:
            state = "stopping" if info.get("stop_requested_at") else "running"
        elif self._external_process() is not None:
            state = "running_external"
        elif not info:
            state = "stopped"
        elif info.get("stop_requested_at"):
            state = "stopped"
        else:
            state = "crashed"  # gone, and nobody asked it to stop
        return {"state": state, **base}

    # --- internals ---

    def _our_process(self, info: dict | None) -> psutil.Process | None:
        if not info:
            return None
        try:
            process = psutil.Process(info["pid"])
            # a recycled PID belongs to some other process with a different create time
            if abs(process.create_time() - info["create_time"]) > 1 or not process.is_running():
                return None
            if process.status() == psutil.STATUS_ZOMBIE:
                return None
            return process
        except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError):
            return None

    def _external_process(self) -> psutil.Process | None:
        """A loop started by hand from a terminal. Starting a second one would double-trade the Ensemble."""
        for process in psutil.process_iter(["pid", "cmdline"]):
            try:
                cmdline = process.info["cmdline"] or []
                if any(self.script_marker in part for part in cmdline) and process.pid != os.getpid():
                    return process
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None

    def _terminate_if_stuck(self, info: dict) -> None:
        process = self._our_process(info)
        if process is None:
            return
        try:
            process.wait(timeout=self.stop_timeout)
        except psutil.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=5)
            except psutil.TimeoutExpired:
                process.kill()
        except psutil.NoSuchProcess:
            pass
        if self._proc is not None:
            self._proc.poll()

    def _exit_code(self) -> int | None:
        if self._proc is None:
            return None
        return self._proc.poll()

    def _log_tail(self) -> list[str]:
        if not self.log_path.exists():
            return []
        return self.log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-LOG_TAIL_LINES:]

    def _read_pid_file(self) -> dict | None:
        if not self.pid_path.exists():
            return None
        try:
            return json.loads(self.pid_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def _write_pid_file(self, info: dict) -> None:
        tmp = self.pid_path.with_suffix(".pid.tmp")
        tmp.write_text(json.dumps(info), encoding="utf-8")
        os.replace(tmp, self.pid_path)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
