import numpy as np
import pandas as pd
import pytest

from tradebot.strategies.base import DataRequirement, ensure_reference_market_resolvable, resolve_supporting_data
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
