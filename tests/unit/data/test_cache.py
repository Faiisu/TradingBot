"""Tests for tradebot.data.cache — the local-first OHLCV cache layer."""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from tradebot.data.cache import load_ohlcv
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
    """Returns one bar per day for any copy_rates_range call."""

    def __init__(self):
        self.fetch_count = 0

    def symbol_select(self, symbol, enable):
        return True

    def copy_rates_range(self, symbol, timeframe, date_from, date_to):
        self.fetch_count += 1
        num_days = (date_to - date_from).days
        rows = []
        for day in range(num_days):
            ts = int((date_from + timedelta(days=day)).timestamp())
            rows.append((ts, 100.0, 101.0, 99.0, 100.5, 10, 2))
        return np.array(rows, dtype=RATE_DTYPE)


def test_load_ohlcv_fetches_and_caches_on_first_call(tmp_path):
    """First call with no cache → fetches from MT5, writes parquet, returns DataFrame."""
    fake = _FakeMt5()
    df = load_ohlcv(Timeframe.H1, mt5_api=fake, cache_dir=tmp_path, num_years=1)

    assert not df.empty
    assert fake.fetch_count > 0
    assert (tmp_path / "XAUUSDm_H1.parquet").exists()


def test_load_ohlcv_reads_from_cache_without_mt5(tmp_path):
    """Second call (cache exists) → returns cached data, no MT5 needed."""
    # Pre-populate cache
    index = pd.date_range("2024-01-01", periods=100, freq="h")
    cached = pd.DataFrame(
        {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "tick_volume": 10, "spread": 2},
        index=index,
    )
    cached.index.name = "time"
    path = tmp_path / "XAUUSDm_H1.parquet"
    cached.to_parquet(path)

    # Load without providing mt5_api — should succeed from cache
    df = load_ohlcv(Timeframe.H1, cache_dir=tmp_path)
    assert len(df) == 100


def test_load_ohlcv_raises_when_no_cache_and_no_mt5(tmp_path):
    """No cache + no mt5_api → raises FileNotFoundError with a helpful message."""
    with pytest.raises(FileNotFoundError, match="No cached data"):
        load_ohlcv(Timeframe.M15, cache_dir=tmp_path)


def test_load_ohlcv_force_refresh_re_fetches(tmp_path):
    """force_refresh=True ignores existing cache and fetches from MT5."""
    # Pre-populate cache with 10 rows
    index = pd.date_range("2024-01-01", periods=10, freq="h")
    cached = pd.DataFrame(
        {"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "tick_volume": 1, "spread": 1},
        index=index,
    )
    cached.index.name = "time"
    (tmp_path / "XAUUSDm_H1.parquet").to_parquet if False else cached.to_parquet(tmp_path / "XAUUSDm_H1.parquet")

    fake = _FakeMt5()
    df = load_ohlcv(Timeframe.H1, mt5_api=fake, cache_dir=tmp_path, num_years=1, force_refresh=True)

    assert fake.fetch_count > 0  # actually went to MT5
    assert len(df) > 10  # got fresh data, not the 10-row stub


def test_load_ohlcv_skips_cache_write_on_empty_result(tmp_path):
    """If MT5 returns no data, the parquet file should NOT be written."""

    class _EmptyMt5:
        def symbol_select(self, symbol, enable):
            return True

        def copy_rates_range(self, symbol, timeframe, date_from, date_to):
            return None

    df = load_ohlcv(Timeframe.M30, mt5_api=_EmptyMt5(), cache_dir=tmp_path, num_years=1)
    assert df.empty
    assert not (tmp_path / "XAUUSDm_M30.parquet").exists()
