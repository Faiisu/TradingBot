"""Local-first OHLCV cache: reads from parquet files under CACHE_DIR if they exist,
otherwise fetches from MT5, stores to parquet, and returns the DataFrame.

Callers never need to care whether the data was already cached — the function
handles both paths transparently.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from tradebot.data.history import fetch_history, report_coverage
from tradebot.timeframe import Timeframe

DEFAULT_CACHE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "cache"
DEFAULT_SYMBOL = "XAUUSDm"
DEFAULT_NUM_YEARS = 2


def _cache_path(cache_dir: Path, symbol: str, timeframe: Timeframe) -> Path:
    return cache_dir / f"{symbol}_{timeframe.value}.parquet"


def load_ohlcv(
    timeframe: Timeframe,
    *,
    mt5_api=None,
    symbol: str = DEFAULT_SYMBOL,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    num_years: int = DEFAULT_NUM_YEARS,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """Load OHLCV data for *timeframe*, pulling from local cache when available.

    Behaviour:
    1. If a cached parquet file exists **and** ``force_refresh`` is False → read
       and return it immediately (no MT5 connection needed).
    2. Otherwise, fetch from the running MT5 terminal via *mt5_api*, write the
       result to parquet, and return it.
    3. If there is no cache **and** no *mt5_api* is provided → raise
       ``FileNotFoundError`` so the caller gets a clear error instead of silently
       falling back to synthetic data.

    Parameters
    ----------
    timeframe:
        The candle interval to load.
    mt5_api:
        An initialised MetaTrader5 module (or compatible fake).  Only needed
        when the cache doesn't exist yet or *force_refresh* is True.
    symbol:
        The instrument symbol on the broker's server.
    cache_dir:
        Directory for parquet files.  Created automatically if it doesn't exist.
    num_years:
        How many years of history to request when fetching from MT5.
    force_refresh:
        If True, always re-fetch from MT5 regardless of cache state.
    """
    path = _cache_path(cache_dir, symbol, timeframe)

    # --- fast path: cache hit ---
    if path.exists() and not force_refresh:
        return pd.read_parquet(path)

    # --- slow path: fetch from MT5, store, return ---
    if mt5_api is None:
        raise FileNotFoundError(
            f"No cached data at {path} and no MT5 connection provided. "
            f"Run `python scripts/fetch_history.py` first, or pass mt5_api= to fetch live."
        )

    cache_dir.mkdir(parents=True, exist_ok=True)

    date_to = datetime.now()
    date_from = date_to - timedelta(days=365 * num_years)

    df = fetch_history(mt5_api, symbol, timeframe, date_from, date_to)
    cov = report_coverage(df, date_from, date_to)

    print(
        f"[{timeframe.value}] requested {cov['requested_days']}d, got {cov['bars']} bars "
        f"spanning {cov['actual_days']}d ({cov['actual_start']} -> {cov['actual_end']})"
    )

    if cov["bars"] == 0:
        print(f"[{timeframe.value}] WARNING: no data returned, skipping cache write")
        return df

    if cov["actual_days"] < cov["requested_days"] * 0.9:
        print(
            f"[{timeframe.value}] WARNING: broker only retains {cov['actual_days']}d of history "
            f"for this symbol/timeframe, short of the requested {cov['requested_days']}d"
        )

    df.to_parquet(path)
    print(f"[{timeframe.value}] cached to {path}")

    return df
