import numpy as np
import pandas as pd
import pytest

from tradebot.data.reference_markets import load_reference_market_data
from tradebot.strategies.market_filter import ReferenceMarketConfig
from tradebot.timeframe import Timeframe

RATE_DTYPE = [
    ("time", "i8"),
    ("open", "f8"),
    ("high", "f8"),
    ("low", "f8"),
    ("close", "f8"),
    ("tick_volume", "i8"),
    ("spread", "i4"),
]


class _FakeMt5:
    def symbol_select(self, symbol, enable):
        return True

    def copy_rates_range(self, symbol, timeframe, date_from, date_to):
        num_days = (date_to - date_from).days
        rows = [(int((date_from + pd.Timedelta(days=d)).timestamp()), 1.0, 1.0, 1.0, 1.0, 1, 1) for d in range(num_days)]
        return np.array(rows, dtype=RATE_DTYPE)


def test_dispatches_to_mt5_when_the_config_has_a_symbol(tmp_path):
    config = ReferenceMarketConfig(symbol="DXYm", relationship="inverse")
    df = load_reference_market_data(
        "DXY", config, cache_dir=tmp_path, mt5_api=_FakeMt5(), market_filter_timeframe=Timeframe.H1, num_years=1
    )

    assert not df.empty
    assert (tmp_path / "DXYm_H1.parquet").exists()  # the same cache convention as gold's own OHLCV


def test_dispatches_to_fred_when_the_config_has_a_fred_series_id(tmp_path):
    config = ReferenceMarketConfig(relationship="inverse", fred_series_id="DFII10")
    df = load_reference_market_data(
        "REAL_YIELD",
        config,
        cache_dir=tmp_path,
        market_filter_timeframe=Timeframe.H1,
        fetch_csv=lambda: "observation_date,DFII10\n2024-01-02,1.50\n",
    )

    assert not df.empty
    assert (tmp_path / "REAL_YIELD.parquet").exists()


def test_raises_a_clear_error_when_the_config_has_neither_a_symbol_nor_a_fred_series_id(tmp_path):
    config = ReferenceMarketConfig(relationship="inverse")
    with pytest.raises(ValueError, match="REAL_YIELD"):
        load_reference_market_data("REAL_YIELD", config, cache_dir=tmp_path, market_filter_timeframe=Timeframe.H1)
