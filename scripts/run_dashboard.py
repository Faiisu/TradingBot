"""Serves the TradeBot dashboard (backtest results + paper trading monitor and controls).

Port 8765, not 8000: 8000 is already bound by another local service on this machine. Bound to 127.0.0.1
only — the Paper Trading page can start and stop a process, so it must never be reachable from the network.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import uvicorn

from tradebot.dashboard.server import HOST, PORT

if __name__ == "__main__":
    print(f"Dashboard: http://{HOST}:{PORT}/")
    uvicorn.run("tradebot.dashboard.server:app", host=HOST, port=PORT, reload=False)
