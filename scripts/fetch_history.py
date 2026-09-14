"""Pull ~2 years of history (all TIMEFRAMES from the strategy registry) for XAUUSD from the connected
Exness DEMO account and cache it locally.

Requires a running "MetaTrader 5 EXNESS" terminal logged into the demo account described in .env
(copy .env.example to .env first). Refuses to run against anything but a demo account.

If a cached parquet file already exists for a timeframe it is skipped — pass ``--force`` to
re-download everything.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tradebot.data.cache import load_ohlcv
from tradebot.data.history import ensure_bar_capacity
from tradebot.mt5_client import mt5_session
from tradebot.strategies.registry import TIMEFRAMES

SYMBOL = "XAUUSDm"  # this Exness demo server suffixes gold with "m"; confirmed via symbols_get()
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
NUM_YEARS = 2


def run(force: bool = False) -> None:
    with mt5_session() as mt5:
        print(f"MT5 Max bars in chart: {mt5.terminal_info().maxbars:,}")
        ensure_bar_capacity(mt5, TIMEFRAMES, NUM_YEARS)
        for timeframe in TIMEFRAMES:
            load_ohlcv(
                timeframe,
                mt5_api=mt5,
                symbol=SYMBOL,
                cache_dir=CACHE_DIR,
                num_years=NUM_YEARS,
                force_refresh=force,
            )


if __name__ == "__main__":
    force = "--force" in sys.argv
    run(force=force)
