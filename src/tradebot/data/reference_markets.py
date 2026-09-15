from pathlib import Path

import pandas as pd

from tradebot.data.cache import load_ohlcv
from tradebot.data.real_yield import load_real_yield
from tradebot.strategies.market_filter import ReferenceMarketConfig
from tradebot.timeframe import Timeframe


def load_reference_market_data(
    market: str,
    config: ReferenceMarketConfig,
    cache_dir: Path,
    market_filter_timeframe: Timeframe,
    mt5_api=None,
    num_years: int = 2,
    force_refresh: bool = False,
    fetch_csv=None,
) -> pd.DataFrame:
    """One Reference Market's own data, dispatched to whichever source its config names: MT5 (a
    `symbol`, live like gold's own OHLCV — DXY, silver) or FRED (a `fred_series_id`, a daily series
    with a publication lag — real yield). Both scripts/fetch_history.py and scripts/run_backtest.py
    call this, so the dispatch lives in one place rather than being duplicated across them."""
    if config.symbol is not None:
        print(f"Fetching Reference Market {market} ({config.symbol})...")
        return load_ohlcv(
            market_filter_timeframe,
            mt5_api=mt5_api,
            symbol=config.symbol,
            cache_dir=cache_dir,
            num_years=num_years,
            force_refresh=force_refresh,
        )

    if config.fred_series_id is not None:
        print(f"Fetching Reference Market {market} (FRED series {config.fred_series_id})...")
        path = cache_dir / f"{market}.parquet"
        if force_refresh and path.exists():
            path.unlink()
        return load_real_yield(path, series_id=config.fred_series_id, fetch_csv=fetch_csv)

    raise ValueError(f"Reference Market {market!r} has neither an MT5 symbol nor a FRED series id configured")
