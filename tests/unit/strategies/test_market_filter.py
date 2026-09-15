import numpy as np
import pandas as pd
import pytest

from tradebot.strategies.base import DataRequirement
from tradebot.strategies.market_filter import MarketFilteredCandidate
from tradebot.timeframe import Timeframe


def _ohlcv_from_close(close: np.ndarray, freq: str = "h") -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=len(close), freq=freq)
    return pd.DataFrame({"open": close, "high": close + 0.5, "low": close - 0.5, "close": close}, index=index)


class _StubEntryStrategy:
    def __init__(self, timeframe, fixed_signal):
        self.timeframe = timeframe
        self.name = "stub_entry"
        self.fixed_signal = fixed_signal
        self.supporting_data = ()

    def generate_signals(self, ohlcv, supporting=None):
        return pd.Series(self.fixed_signal, index=ohlcv.index)


def test_only_already_closed_reference_market_bars_are_used_at_each_entry_bar():
    """A DXY-like series that turns at a known bar (03:00), exercised end to end through
    MarketFilteredCandidate — not just the underlying align_htf_signal helper in isolation — proves an
    entry bar can never see a Reference Market bar that hadn't closed yet. If 03:15 leaked the future
    04:00 DXY value, this candidate would go flat there instead of staying long."""
    market_index = pd.date_range("2024-01-01 00:00", periods=5, freq="h")  # 00:00 .. 04:00
    turning_trend = pd.Series([1.0, 1.0, 1.0, -1.0, 1.0], index=market_index)  # dips down only at 03:00
    market_ohlcv = _ohlcv_from_close(np.linspace(100, 104, 5), freq="h")
    stub_filter = lambda df: turning_trend  # noqa: E731 — stands in for DXY's real EMA-slope result

    entry_index = pd.DatetimeIndex(
        [
            "2024-01-01 02:00",  # sees DXY's 02:00 bar (up) -> inverse: shorts only -> long forced flat
            "2024-01-01 02:45",  # still before DXY's 03:00 close -> still up -> still flat
            "2024-01-01 03:00",  # DXY's 03:00 bar (down) just closed -> inverse: longs now allowed
            "2024-01-01 03:15",  # DXY's 04:00 bar (up again) hasn't closed yet -> must still see "down"
        ]
    )
    ohlcv = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0}, index=entry_index)

    entry = _StubEntryStrategy(Timeframe.M15, fixed_signal=1.0)  # always long
    candidate = MarketFilteredCandidate(entry, stub_filter, "DXY", Timeframe.H1, relationship="inverse")
    signals = candidate.generate_signals(ohlcv, {DataRequirement(timeframe=Timeframe.H1, reference_market="DXY"): market_ohlcv})

    assert list(signals) == [0.0, 0.0, 1.0, 1.0]


def test_market_filtered_candidate_declares_its_reference_markets_data_as_a_requirement():
    entry = _StubEntryStrategy(Timeframe.M15, fixed_signal=1.0)
    candidate = MarketFilteredCandidate(entry, lambda df: df, "DXY", Timeframe.H1, relationship="inverse")

    assert candidate.supporting_data == (DataRequirement(timeframe=Timeframe.H1, reference_market="DXY"),)


def test_inverse_relationship_keeps_only_short_entries_when_the_market_rises():
    ohlcv = _ohlcv_from_close(np.linspace(100, 110, 10), freq="15min")
    market_ohlcv = _ohlcv_from_close(np.linspace(100, 110, 10), freq="h")

    entry = _StubEntryStrategy(Timeframe.M15, fixed_signal=1.0)  # always long
    rising_filter = lambda df: pd.Series(1.0, index=df.index)  # noqa: E731 — market is rising

    candidate = MarketFilteredCandidate(entry, rising_filter, "DXY", Timeframe.H1, relationship="inverse")
    signals = candidate.generate_signals(ohlcv, {DataRequirement(timeframe=Timeframe.H1, reference_market="DXY"): market_ohlcv})

    # DXY rising -> only shorts allowed; an always-long entry is forced flat
    assert (signals == 0.0).all()


def test_inverse_relationship_keeps_short_entries_when_the_market_rises():
    ohlcv = _ohlcv_from_close(np.linspace(100, 110, 10), freq="15min")
    market_ohlcv = _ohlcv_from_close(np.linspace(100, 110, 10), freq="h")

    entry = _StubEntryStrategy(Timeframe.M15, fixed_signal=-1.0)  # always short
    rising_filter = lambda df: pd.Series(1.0, index=df.index)  # noqa: E731

    candidate = MarketFilteredCandidate(entry, rising_filter, "DXY", Timeframe.H1, relationship="inverse")
    signals = candidate.generate_signals(ohlcv, {DataRequirement(timeframe=Timeframe.H1, reference_market="DXY"): market_ohlcv})

    assert (signals == -1.0).all()


def test_same_relationship_keeps_only_long_entries_when_the_market_rises():
    ohlcv = _ohlcv_from_close(np.linspace(100, 110, 10), freq="15min")
    market_ohlcv = _ohlcv_from_close(np.linspace(100, 110, 10), freq="h")

    entry = _StubEntryStrategy(Timeframe.M15, fixed_signal=-1.0)  # always short
    rising_filter = lambda df: pd.Series(1.0, index=df.index)  # noqa: E731

    candidate = MarketFilteredCandidate(entry, rising_filter, "XAGUSD", Timeframe.H1, relationship="same")
    signals = candidate.generate_signals(ohlcv, {DataRequirement(timeframe=Timeframe.H1, reference_market="XAGUSD"): market_ohlcv})

    # silver rising -> only longs allowed; an always-short entry is forced flat
    assert (signals == 0.0).all()


def test_market_filtered_candidate_requires_its_filter_data_in_supporting():
    entry = _StubEntryStrategy(Timeframe.M15, fixed_signal=1.0)
    candidate = MarketFilteredCandidate(entry, lambda df: df, "DXY", Timeframe.H1, relationship="inverse")
    ohlcv = _ohlcv_from_close(np.linspace(100, 110, 10), freq="15min")

    with pytest.raises(ValueError):
        candidate.generate_signals(ohlcv, supporting=None)
    with pytest.raises(ValueError):
        candidate.generate_signals(ohlcv, supporting={})


def test_market_filtered_candidate_name_and_timeframe():
    entry = _StubEntryStrategy(Timeframe.M15, fixed_signal=1.0)
    entry.name = "macd_12_26_9"
    candidate = MarketFilteredCandidate(entry, lambda df: df, "DXY", Timeframe.H1, relationship="inverse")

    assert candidate.name == "macd_12_26_9_marketfilter_dxy"
    assert candidate.timeframe == Timeframe.M15


def test_market_filtered_candidate_exposes_filter_name_and_timeframe_for_the_dashboard():
    """persistence.py reads filter_name/filter_timeframe generically off any candidate (getattr), the
    same attributes MtfCandidate already exposes — so a Market-Filtered candidate is labeled on the
    Backtest page without persistence.py needing to know Market Filters exist."""
    entry = _StubEntryStrategy(Timeframe.M15, fixed_signal=1.0)
    candidate = MarketFilteredCandidate(entry, lambda df: df, "DXY", Timeframe.H1, relationship="inverse")

    assert candidate.filter_name == "DXY"
    assert candidate.filter_timeframe == Timeframe.H1
