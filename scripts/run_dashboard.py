"""Serves the TradeBot dashboard (backtest results + paper trading monitor and controls).

Port 8765, not 8000: 8000 is already bound by another local service on this machine. Bound to every
interface (0.0.0.0), so other devices on the local network can reach it too, including the Paper
Trading page's Start/Stop controls — a deliberate choice; see server.py's ALLOWED_HOSTS comment for
how requests are still checked against this machine's own known addresses.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import uvicorn

from tradebot.dashboard.server import ALLOWED_HOSTS, HOST, PORT

if __name__ == "__main__":
    print("Dashboard reachable at:", flush=True)
    for host in sorted(ALLOWED_HOSTS):
        print(f"  http://{host}/", flush=True)
    uvicorn.run("tradebot.dashboard.server:app", host=HOST, port=PORT, reload=False)
