import json
import sys
import time
import uuid

import psutil
import pytest

from tradebot.paper.supervisor import AlreadyRunning, NotRunning, PaperTradingSupervisor

# Stands in for scripts/run_paper_trading.py: behaves like the real loop's stop handling without MT5.
COOPERATIVE_CHILD = """
import pathlib, sys, time
stop = pathlib.Path(sys.argv[1])
print("dummy loop started", flush=True)
while not stop.exists():
    time.sleep(0.1)
stop.unlink()
print("stop requested, exiting cleanly", flush=True)
"""

CRASHING_CHILD = """
import sys
print("could not connect to MT5", flush=True)
sys.exit(3)
"""


def _wait_for(predicate, timeout=10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.1)
    return False


@pytest.fixture
def make_supervisor(tmp_path):
    supervisors = []

    def factory(child_source: str) -> PaperTradingSupervisor:
        marker = f"dummy_loop_{uuid.uuid4().hex}.py"
        script = tmp_path / marker
        script.write_text(child_source)
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)
        supervisor = PaperTradingSupervisor(
            command=[sys.executable, str(script), str(data_dir / "paper_trading.stop")],
            data_dir=data_dir,
            cwd=tmp_path,
            script_marker=marker,
            stop_timeout=5,
        )
        supervisors.append(supervisor)
        return supervisor

    yield factory

    for supervisor in supervisors:  # never leave a child running after a test
        # only a process this supervisor launched (PID *and* create time match) — the recycled-PID test
        # points the PID file at pytest itself
        process = supervisor._our_process(supervisor._read_pid_file())
        if process is not None:
            try:
                process.kill()
            except psutil.NoSuchProcess:
                pass


def test_start_reports_running_and_refuses_a_second_start(make_supervisor):
    supervisor = make_supervisor(COOPERATIVE_CHILD)

    status = supervisor.start()
    assert status["state"] == "running"
    assert json.loads(supervisor.pid_path.read_text())["pid"] == status["pid"]

    with pytest.raises(AlreadyRunning):
        supervisor.start()


def test_stop_is_cooperative_and_ends_as_stopped(make_supervisor):
    supervisor = make_supervisor(COOPERATIVE_CHILD)
    supervisor.start()
    assert _wait_for(lambda: "dummy loop started" in "\n".join(supervisor.status()["log_tail"]))

    status = supervisor.stop()
    assert status["state"] in ("stopping", "stopped")

    assert _wait_for(lambda: supervisor.status()["state"] == "stopped")
    assert "stop requested, exiting cleanly" in supervisor.status()["log_tail"]


def test_stop_when_not_running_is_refused(make_supervisor):
    supervisor = make_supervisor(COOPERATIVE_CHILD)
    with pytest.raises(NotRunning):
        supervisor.stop()


def test_a_process_that_exits_on_its_own_is_reported_as_crashed_with_its_log(make_supervisor):
    supervisor = make_supervisor(CRASHING_CHILD)
    supervisor.start()

    assert _wait_for(lambda: supervisor.status()["state"] == "crashed")
    status = supervisor.status()
    assert status["exit_code"] == 3
    assert "could not connect to MT5" in status["log_tail"]


def test_a_recycled_pid_is_not_mistaken_for_our_process(make_supervisor):
    supervisor = make_supervisor(COOPERATIVE_CHILD)
    me = psutil.Process()
    supervisor.pid_path.write_text(
        json.dumps({"pid": me.pid, "create_time": me.create_time() - 10_000, "started_at": "x", "stop_requested_at": None})
    )
    assert supervisor.status()["state"] == "crashed"  # our record, but that PID now belongs to something else


def test_status_survives_a_new_supervisor_instance(make_supervisor):
    """A restarted dashboard creates a fresh supervisor — it must still see the running session."""
    first = make_supervisor(COOPERATIVE_CHILD)
    first.start()

    second = PaperTradingSupervisor(
        command=first.command, data_dir=first.pid_path.parent, cwd=first.cwd, script_marker=first.script_marker
    )
    assert second.status()["state"] == "running"
