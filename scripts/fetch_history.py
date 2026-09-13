"""Pull ~2 years of history (all TIMEFRAMES from the strategy registry) for XAUUSD from the connected
Exness DEMO account and cache it locally.

Requires a running "MetaTrader 5 EXNESS" terminal logged into the demo account described in .env
(copy .env.example to .env first). Refuses to run against anything but a demo account.
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tradebot.data.history import fetch_history, report_coverage
from tradebot.mt5_client import mt5_session
from tradebot.strategies.registry import TIMEFRAMES

SYMBOL = "XAUUSDm"  # this Exness demo server suffixes gold with "m"; confirmed via symbols_get()
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
NUM_YEARS = 2


def run() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    date_to = datetime.now()
    date_from = date_to - timedelta(days=365 * NUM_YEARS)

    with mt5_session() as mt5:
        for timeframe in TIMEFRAMES:
            df = fetch_history(mt5, SYMBOL, timeframe, date_from, date_to)
            coverage = report_coverage(df, date_from, date_to)

            print(f"[{timeframe.value}] requested {coverage['requested_days']}d, got {coverage['bars']} bars "
                  f"spanning {coverage['actual_days']}d ({coverage['actual_start']} -> {coverage['actual_end']})")
            if coverage["bars"] == 0:
                print(f"[{timeframe.value}] WARNING: no data returned, skipping cache write")
                continue
            if coverage["actual_days"] < coverage["requested_days"] * 0.9:
                print(f"[{timeframe.value}] WARNING: broker only retains {coverage['actual_days']}d of history "
                      f"for this symbol/timeframe, short of the requested {coverage['requested_days']}d")

            cache_path = CACHE_DIR / f"{SYMBOL}_{timeframe.value}.parquet"
            df.to_parquet(cache_path)
            print(f"[{timeframe.value}] cached to {cache_path}")


if __name__ == "__main__":
    run()
