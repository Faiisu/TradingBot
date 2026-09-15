import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from tradebot.backtest.persistence import load_backtest_results, load_walk_forward_verdict
from tradebot.dashboard.state import read_state
from tradebot.paper.supervisor import AlreadyRunning, NotRunning, PaperTradingSupervisor

HOST = "127.0.0.1"
PORT = 8765

DASHBOARD_DIR = Path(__file__).resolve().parent
REPO_DIR = DASHBOARD_DIR.parent.parent.parent
DATA_DIR = REPO_DIR / "data"
STATE_PATH = DATA_DIR / "paper_state.json"
BACKTEST_RESULTS_PATH = DATA_DIR / "backtest_results.json"
ENSEMBLE_PATH = DATA_DIR / "ensemble.json"
WALK_FORWARD_VERDICT_PATH = DATA_DIR / "walk_forward_verdict.json"
PAPER_TRADING_SCRIPT = REPO_DIR / "scripts" / "run_paper_trading.py"

# Control endpoints start and stop a process, so they only accept requests from this dashboard's own pages.
# A fixed allowlist, not one derived from the Host header: a DNS-rebinding page could otherwise make both
# Host and Origin look local.
ALLOWED_HOSTS = {f"{HOST}:{PORT}", f"localhost:{PORT}"}
ALLOWED_ORIGINS = {f"http://{host}" for host in ALLOWED_HOSTS}

app = FastAPI()
app.mount("/assets", StaticFiles(directory=DASHBOARD_DIR / "assets"), name="assets")

supervisor = PaperTradingSupervisor(
    command=[sys.executable, str(PAPER_TRADING_SCRIPT)],
    data_dir=DATA_DIR,
    cwd=REPO_DIR,
    script_marker=PAPER_TRADING_SCRIPT.name,
)


def require_dashboard_request(request: Request) -> None:
    """Blocks cross-site requests: a JSON content type forces a CORS preflight this server never approves,
    and Host/Origin must be this dashboard. Requests with no Origin (curl, scripts) are allowed."""
    if request.headers.get("host") not in ALLOWED_HOSTS:
        raise HTTPException(status_code=403, detail="Requests must be made to the local dashboard address.")
    origin = request.headers.get("origin")
    if origin is not None and origin not in ALLOWED_ORIGINS:
        raise HTTPException(status_code=403, detail="Cross-site requests are not allowed.")
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        raise HTTPException(status_code=415, detail="Send the request with Content-Type: application/json.")


@app.get("/", response_class=HTMLResponse)
def paper_trading_page():
    return (DASHBOARD_DIR / "dashboard.html").read_text(encoding="utf-8")


@app.get("/api/state")
def state():
    if not STATE_PATH.exists():
        return JSONResponse(
            {
                "updated_at": None,
                "session_started_at": None,
                "total_equity": 0,
                "total_initial_equity": 0,
                "total_return_pct": 0,
                "equity_history": [],
                "members": [],
                "recent_trades": [],
                "worst_decision_latency_seconds": None,
            }
        )
    return JSONResponse(read_state(STATE_PATH))


@app.get("/api/paper/status")
def paper_status():
    return JSONResponse({**supervisor.status(), "ensemble": ensemble_summary(), "walk_forward": walk_forward_summary()})


@app.post("/api/paper/start")
async def paper_start(request: Request):
    require_dashboard_request(request)
    try:
        body = await request.json()
    except ValueError:
        body = {}

    summary = ensemble_summary()
    if not summary["members"]:
        raise HTTPException(status_code=409, detail="No Ensemble to trade yet. Run scripts/run_backtest.py first.")

    verdict = walk_forward_summary()
    if verdict is not None and not verdict["passed"] and not body.get("acknowledge_failed_walk_forward"):
        raise HTTPException(
            status_code=409,
            detail=(
                f"The latest Walk-Forward Validation did not pass (out-of-sample Performance Metric "
                f"{verdict['performance_metric']:.2f}). Starting anyway needs explicit acknowledgment."
            ),
        )

    try:
        return JSONResponse({**supervisor.start(), "ensemble": summary})
    except AlreadyRunning as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/api/paper/stop")
def paper_stop(request: Request):
    require_dashboard_request(request)
    try:
        return JSONResponse({**supervisor.stop(), "ensemble": ensemble_summary()})
    except NotRunning as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


def ensemble_summary() -> dict:
    """What Start will trade. Uses ensemble.json's own mtime (written by the same backtest run) rather than
    parsing the multi-megabyte backtest_results.json on every status poll."""
    if not ENSEMBLE_PATH.exists():
        return {"members": 0, "saved_at": None}
    members = len(json.loads(ENSEMBLE_PATH.read_text(encoding="utf-8")).get("members", []))
    saved_at = datetime.fromtimestamp(ENSEMBLE_PATH.stat().st_mtime, tz=timezone.utc).isoformat()
    return {"members": members, "saved_at": saved_at}


def walk_forward_summary() -> dict | None:
    """The latest Walk-Forward Validation verdict, or None when no backtest run has produced one yet
    (an older backtest_results.json predating this file, or no backtest run at all)."""
    return load_walk_forward_verdict(WALK_FORWARD_VERDICT_PATH)


@app.get("/backtest", response_class=HTMLResponse)
def backtest_page():
    return (DASHBOARD_DIR / "backtest.html").read_text(encoding="utf-8")


@app.get("/api/backtest")
def backtest_results():
    if not BACKTEST_RESULTS_PATH.exists():
        return JSONResponse({"generated_at": None, "window_start": None, "window_end": None, "candidates": []})
    return JSONResponse(load_backtest_results(BACKTEST_RESULTS_PATH))
