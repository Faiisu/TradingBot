import numpy as np
import pandas as pd
import pytest

from tradebot.strategies.base import (
    DataRequirement,
    channel_breakout_signals,
    ensure_reference_market_resolvable,
    resolve_supporting_data,
    threshold_reversion_signals,
)
from tradebot.timeframe import Timeframe


class _PlainCandidate:
    name = "plain"
    timeframe = Timeframe.M15
    supporting_data: tuple = ()


def _ohlcv(periods=5):
    index = pd.date_range("2024-01-01", periods=periods, freq="h")
    close = np.linspace(100, 100 + periods, periods)
    return pd.DataFrame({"open": close, "high": close, "low": close, "close": close}, index=index)


def test_plain_candidate_gets_an_empty_supporting_dict():
    result = resolve_supporting_data(_PlainCandidate(), ohlcv_by_timeframe={Timeframe.M15: _ohlcv()})
    assert result == {}


class _MtfLikeCandidate:
    name = "mtf_like"
    timeframe = Timeframe.M15
    supporting_data = (DataRequirement(timeframe=Timeframe.H1),)


def test_candidate_with_a_requirement_gets_the_matching_timeframe_data():
    h1_data = _ohlcv()
    result = resolve_supporting_data(_MtfLikeCandidate(), ohlcv_by_timeframe={Timeframe.M15: _ohlcv(), Timeframe.H1: h1_data})

    assert result == {DataRequirement(timeframe=Timeframe.H1): h1_data}


def test_missing_required_timeframe_raises_a_clear_error():
    with pytest.raises(KeyError, match="H1"):
        resolve_supporting_data(_MtfLikeCandidate(), ohlcv_by_timeframe={Timeframe.M15: _ohlcv()})


class _MarketFilteredLikeCandidate:
    name = "market_filtered_like"
    timeframe = Timeframe.M15
    supporting_data = (DataRequirement(timeframe=Timeframe.H1, reference_market="DXY"),)


def test_reference_market_requirement_is_not_yet_resolvable():
    with pytest.raises(NotImplementedError, match="DXY"):
        resolve_supporting_data(_MarketFilteredLikeCandidate(), ohlcv_by_timeframe={Timeframe.H1: _ohlcv()})


def test_ensure_reference_market_resolvable_is_the_single_shared_check():
    """Both resolve_supporting_data (Backtest) and paper/loop.py's update_member (Paper Trading) call
    this directly, so a Market-Filtered Candidate is rejected identically everywhere rather than the
    two implementations drifting apart."""
    ensure_reference_market_resolvable(DataRequirement(timeframe=Timeframe.H1))  # no reference market: fine

    with pytest.raises(NotImplementedError, match="DXY"):
        ensure_reference_market_resolvable(DataRequirement(timeframe=Timeframe.H1, reference_market="DXY"))


def test_channel_breakout_signals_uses_a_narrower_exit_channel_than_entry():
    index = pd.date_range("2024-01-01", periods=6, freq="h")
    close = pd.Series([100.0, 100.0, 105.0, 101.0, 97.0, 98.0], index=index)
    entry_upper = pd.Series([104.0] * 6, index=index)
    entry_lower = pd.Series([96.0] * 6, index=index)
    exit_upper = pd.Series([103.0] * 6, index=index)  # narrower than entry_upper
    exit_lower = pd.Series([99.0] * 6, index=index)  # narrower than entry_lower

    signals = channel_breakout_signals(close, entry_upper, entry_lower, exit_upper, exit_lower)

    # bar 2: close 105 > entry_upper 104 -> enters long
    # bar 3: close 101 is still above exit_lower 99 -> stays long (exit channel is narrower than entry)
    # bar 4: close 97 breaks below exit_lower 99 -> goes flat
    # bar 5: close 98 is inside both channels -> stays flat
    assert list(signals) == [0, 0, 1, 1, 0, 0]


def test_threshold_reversion_signals_goes_long_then_flat_at_the_midpoint():
    index = pd.date_range("2024-01-01", periods=6, freq="h")
    # RSI-like series: dips below 30 (long), recovers, crosses back through 50 (flat)
    indicator = pd.Series([50.0, 25.0, 28.0, 45.0, 51.0, 60.0], index=index)

    signals = threshold_reversion_signals(indicator, oversold=30, overbought=70, midpoint=50)

    assert list(signals) == [0, 1, 1, 1, 0, 0]


def test_threshold_reversion_signals_goes_short_then_flat_at_the_midpoint():
    index = pd.date_range("2024-01-01", periods=6, freq="h")
    indicator = pd.Series([50.0, 75.0, 72.0, 55.0, 49.0, 40.0], index=index)

    signals = threshold_reversion_signals(indicator, oversold=30, overbought=70, midpoint=50)

    assert list(signals) == [0, -1, -1, -1, 0, 0]


def test_threshold_reversion_signals_ignores_nan_warmup_bars():
    index = pd.date_range("2024-01-01", periods=3, freq="h")
    indicator = pd.Series([float("nan")] * 3, index=index)

    signals = threshold_reversion_signals(indicator, oversold=30, overbought=70)

    assert list(signals) == [0, 0, 0]


def test_channel_breakout_signals_rejects_an_unconfirmed_entry():
    index = pd.date_range("2024-01-01", periods=4, freq="h")
    close = pd.Series([100.0, 105.0, 105.0, 90.0], index=index)
    entry_upper = pd.Series([104.0] * 4, index=index)
    entry_lower = pd.Series([96.0] * 4, index=index)
    exit_upper = pd.Series([103.0] * 4, index=index)
    exit_lower = pd.Series([94.0] * 4, index=index)
    entry_confirmed = pd.Series([True, False, True, True], index=index)

    signals = channel_breakout_signals(close, entry_upper, entry_lower, exit_upper, exit_lower, entry_confirmed=entry_confirmed)

    # bar 1 breaks the entry channel but isn't confirmed (e.g. insufficient volume) -> stays flat,
    #   not "remembered" for later
    # bar 2 breaks the entry channel again, now confirmed -> enters long on this fresh breakout
    # bar 3 breaks the exit/entry lower channel and is confirmed -> flips straight to short
    assert list(signals) == [0, 0, 1, -1]


def test_channel_breakout_signals_ignores_nan_warmup_bars():
    index = pd.date_range("2024-01-01", periods=3, freq="h")
    close = pd.Series([100.0, 100.0, 100.0], index=index)
    nan_series = pd.Series([float("nan")] * 3, index=index)

    signals = channel_breakout_signals(close, nan_series, nan_series, nan_series, nan_series)

    assert list(signals) == [0, 0, 0]
