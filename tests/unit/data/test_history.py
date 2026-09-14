from datetime import datetime, timedelta

import numpy as np
import pytest

from tradebot.data.history import InsufficientBarCapacity, ensure_bar_capacity, fetch_history, report_coverage
from tradebot.timeframe import Timeframe


class _FakeTerminalMt5:
    """Only what the capacity check needs: the terminal's 'Max bars in chart' setting."""

    def __init__(self, maxbars: int):
        self.maxbars = maxbars

    def terminal_info(self):
        return self


def test_refuses_to_fetch_when_the_terminal_bar_limit_would_truncate_history():
    # the real failure: a 100,000-bar cap cut two years of M5 XAUUSD down to ~514 days
    with pytest.raises(InsufficientBarCapacity, match="Max bars"):
        ensure_bar_capacity(_FakeTerminalMt5(maxbars=100_000), [Timeframe.H1, Timeframe.M5], num_years=2)


def test_allows_fetching_when_every_requested_timeframe_fits_the_bar_limit():
    # two years of H1 is at most 2 * 365 * 24 = 17,520 bars, well under a 100,000 cap
    ensure_bar_capacity(_FakeTerminalMt5(maxbars=100_000), [Timeframe.H1], num_years=2)
    ensure_bar_capacity(_FakeTerminalMt5(maxbars=100_000_000), [Timeframe.H1, Timeframe.M5], num_years=2)

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
    """Mimics the MetaTrader5 module's copy_rates_range: returns one daily bar per day in [start, end)."""

    def __init__(self):
        self.calls: list[tuple] = []

    def symbol_select(self, symbol, enable):
        return True

    def copy_rates_range(self, symbol, timeframe, date_from, date_to):
        self.calls.append((date_from, date_to))
        num_days = (date_to - date_from).days
        rows = []
        for day in range(num_days):
            ts = int((date_from + timedelta(days=day)).timestamp())
            rows.append((ts, 100.0, 101.0, 99.0, 100.5, 10, 2))
        return np.array(rows, dtype=RATE_DTYPE)


def test_fetch_history_chunks_dedupes_and_sorts():
    fake = _FakeMt5()
    date_from = datetime(2024, 1, 1)
    date_to = date_from + timedelta(days=200)

    df = fetch_history(fake, "XAUUSD", Timeframe.H1, date_from, date_to)

    assert len(fake.calls) == 3  # 90 + 90 + 20 day chunks
    assert len(df) == 200
    assert df.index.is_monotonic_increasing
    assert not df.index.duplicated().any()
    assert list(df.columns) == ["open", "high", "low", "close", "tick_volume", "spread"]


def test_fetch_history_returns_empty_frame_when_no_data():
    class _EmptyMt5:
        def symbol_select(self, symbol, enable):
            return True

        def copy_rates_range(self, symbol, timeframe, date_from, date_to):
            return None

    df = fetch_history(_EmptyMt5(), "XAUUSD", Timeframe.M15, datetime(2024, 1, 1), datetime(2024, 1, 5))
    assert df.empty


def test_report_coverage_flags_a_shortfall():
    fake = _FakeMt5()
    date_from = datetime(2024, 1, 1)
    date_to = date_from + timedelta(days=100)
    df = fetch_history(fake, "XAUUSD", Timeframe.H1, date_from, date_to)

    coverage = report_coverage(df, date_from, date_to)
    assert coverage["bars"] == 100
    assert coverage["requested_days"] == 100
    assert coverage["actual_days"] == 99  # last bar is at day 99 (bars run 0..99)


def test_report_coverage_on_empty_frame():
    import pandas as pd

    coverage = report_coverage(pd.DataFrame(), datetime(2024, 1, 1), datetime(2024, 1, 5))
    assert coverage["bars"] == 0
    assert coverage["actual_start"] is None
