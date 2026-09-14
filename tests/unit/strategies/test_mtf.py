import numpy as np
import pandas as pd
import pytest

from tradebot.strategies.base import DataRequirement, align_htf_signal
from tradebot.strategies.mtf import MtfCandidate, ema_slope_filter
from tradebot.timeframe import Timeframe


def test_align_htf_signal_never_uses_a_future_htf_bar():
    """The core look-ahead-bias regression test: every entry-timeframe timestamp must only ever see
    an htf value from a bar that closed at or before it, never after."""
    htf_index = pd.date_range("2024-01-01 00:00", periods=5, freq="h")  # 00:00, 01:00, ..., 04:00
    htf_signal = pd.Series([1.0, -1.0, 1.0, 1.0, -1.0], index=htf_index)

    # M15 bars: some exactly on an H1 boundary, some strictly between two H1 closes
    entry_index = pd.DatetimeIndex(
        [
            "2024-01-01 00:00",  # exactly at htf[0] -> 1
            "2024-01-01 00:45",  # still before htf[1] closes -> 1
            "2024-01-01 01:00",  # exactly at htf[1] -> -1
            "2024-01-01 01:15",  # after htf[1], before htf[2] -> -1
            "2024-01-01 02:00",  # exactly at htf[2] -> 1
            "2024-01-01 04:30",  # after the last htf bar -> -1 (the last known value)
        ]
    )

    aligned = align_htf_signal(htf_signal, entry_index)

    assert aligned.tolist() == [1.0, 1.0, -1.0, -1.0, 1.0, -1.0]


def test_align_htf_signal_is_nan_before_the_first_htf_bar():
    htf_index = pd.date_range("2024-01-01 01:00", periods=2, freq="h")
    htf_signal = pd.Series([1.0, -1.0], index=htf_index)
    entry_index = pd.DatetimeIndex(["2024-01-01 00:00", "2024-01-01 00:45"])  # before any htf bar closes

    aligned = align_htf_signal(htf_signal, entry_index)

    assert aligned.isna().all()


def _ohlcv_from_close(close: np.ndarray, freq: str = "h") -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=len(close), freq=freq)
    return pd.DataFrame({"open": close, "high": close + 0.5, "low": close - 0.5, "close": close}, index=index)


def test_ema_slope_filter_detects_uptrend_and_downtrend():
    up = _ohlcv_from_close(np.linspace(100, 160, 80))
    down = _ohlcv_from_close(np.linspace(160, 100, 80))

    up_signal = ema_slope_filter(up, period=20, lookback=5)
    down_signal = ema_slope_filter(down, period=20, lookback=5)

    assert up_signal.iloc[-1] == 1
    assert down_signal.iloc[-1] == -1


def test_ema_slope_filter_flat_during_warmup():
    flat = _ohlcv_from_close(np.linspace(100, 160, 80))
    signal = ema_slope_filter(flat, period=20, lookback=5)
    assert signal.iloc[0] == 0


class _StubEntryStrategy:
    def __init__(self, timeframe, fixed_signal):
        self.timeframe = timeframe
        self.name = "stub_entry"
        self.fixed_signal = fixed_signal
        self.supporting_data = ()

    def generate_signals(self, ohlcv, supporting=None):
        return pd.Series(self.fixed_signal, index=ohlcv.index)


def test_mtf_candidate_declares_its_filter_timeframe_as_a_requirement():
    entry = _StubEntryStrategy(Timeframe.M15, fixed_signal=1.0)
    candidate = MtfCandidate(entry, lambda df: df, "ema_slope", Timeframe.H1)

    assert candidate.supporting_data == (DataRequirement(timeframe=Timeframe.H1),)


def test_mtf_candidate_keeps_entry_signal_when_filter_agrees():
    ohlcv = _ohlcv_from_close(np.linspace(100, 110, 10), freq="15min")
    htf_ohlcv = _ohlcv_from_close(np.linspace(100, 110, 10), freq="h")

    entry = _StubEntryStrategy(Timeframe.M15, fixed_signal=1.0)  # always long
    always_up_filter = lambda df: pd.Series(1.0, index=df.index)  # noqa: E731

    candidate = MtfCandidate(entry, always_up_filter, "always_up", Timeframe.H1)
    signals = candidate.generate_signals(ohlcv, {DataRequirement(timeframe=Timeframe.H1): htf_ohlcv})

    assert (signals == 1.0).all()


def test_mtf_candidate_forces_flat_when_filter_disagrees():
    ohlcv = _ohlcv_from_close(np.linspace(100, 110, 10), freq="15min")
    htf_ohlcv = _ohlcv_from_close(np.linspace(100, 110, 10), freq="h")

    entry = _StubEntryStrategy(Timeframe.M15, fixed_signal=1.0)  # always long
    always_down_filter = lambda df: pd.Series(-1.0, index=df.index)  # noqa: E731

    candidate = MtfCandidate(entry, always_down_filter, "always_down", Timeframe.H1)
    signals = candidate.generate_signals(ohlcv, {DataRequirement(timeframe=Timeframe.H1): htf_ohlcv})

    assert (signals == 0.0).all()


def test_mtf_candidate_requires_its_filter_data_in_supporting():
    entry = _StubEntryStrategy(Timeframe.M15, fixed_signal=1.0)
    candidate = MtfCandidate(entry, lambda df: df, "noop", Timeframe.H1)
    ohlcv = _ohlcv_from_close(np.linspace(100, 110, 10), freq="15min")

    with pytest.raises(ValueError):
        candidate.generate_signals(ohlcv, supporting=None)
    with pytest.raises(ValueError):
        candidate.generate_signals(ohlcv, supporting={})  # present but missing this candidate's own key


def test_mtf_candidate_name_and_timeframe():
    entry = _StubEntryStrategy(Timeframe.M15, fixed_signal=1.0)
    entry.name = "macd_12_26_9"
    candidate = MtfCandidate(entry, lambda df: df, "ema_slope", Timeframe.H1)

    assert candidate.name == "macd_12_26_9_mtf_ema_slope_H1filter"
    assert candidate.timeframe == Timeframe.M15
