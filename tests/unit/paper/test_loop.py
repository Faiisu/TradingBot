import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from tradebot.paper.loop import (
    decide_and_update,
    fetch_recent_bars,
    member_key,
    seconds_until_next_bar_close,
    update_member,
    wait_or_stop,
)
from tradebot.paper.simulated_broker import SimulatedBroker
from tradebot.risk.risk_controls import RiskControls
from tradebot.strategies.base import DataRequirement
from tradebot.timeframe import Timeframe


class _AlwaysLongStrategy:
    name = "always_long"
    timeframe = Timeframe.H1
    supporting_data: tuple = ()

    def generate_signals(self, ohlcv: pd.DataFrame, supporting: dict | None = None) -> pd.Series:
        return pd.Series(1.0, index=ohlcv.index)


def test_decide_and_update_opens_a_position_from_recent_bars():
    close = np.linspace(100, 120, 30)
    index = pd.date_range("2024-01-01", periods=30, freq="h")
    ohlcv = pd.DataFrame({"open": close, "high": close + 0.5, "low": close - 0.5, "close": close}, index=index)

    broker = SimulatedBroker(risk_controls=RiskControls(), initial_equity=1.0)
    decide_and_update(_AlwaysLongStrategy(), broker, ohlcv)

    assert broker.position is not None
    assert broker.position.direction == 1
    assert broker.position.entry_price == close[-1]


def test_decide_and_update_noop_on_empty_data():
    broker = SimulatedBroker(risk_controls=RiskControls(), initial_equity=1.0)
    decide_and_update(_AlwaysLongStrategy(), broker, pd.DataFrame(columns=["open", "high", "low", "close"]))
    assert broker.position is None


def test_seconds_until_next_bar_close_matches_hand_calculation():
    now = datetime.fromtimestamp(1000, tz=timezone.utc)  # 1000 % 900 == 100
    assert seconds_until_next_bar_close(Timeframe.M15, now) == pytest.approx(800)

    now = datetime.fromtimestamp(3600, tz=timezone.utc)  # exactly on an H1 boundary
    assert seconds_until_next_bar_close(Timeframe.H1, now) == pytest.approx(3600)


class _FakeMt5:
    """copy_rates_from_pos returning a fixed, growing bar series (including tick_volume, matching
    MT5's real rate dtype); records every start position requested."""

    def __init__(self, bars: int = 40):
        self.bars = bars
        self.start_positions: list[int] = []

    def copy_rates_from_pos(self, symbol, timeframe, start_pos, count):
        self.start_positions.append(start_pos)
        dtype = [("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"), ("close", "f8"), ("tick_volume", "i8")]
        n = min(count, self.bars)
        return np.array([(1000 + i * 900, 100.0 + i, 101.0 + i, 99.0 + i, 100.5 + i, 10 + i) for i in range(n)], dtype=dtype)


def test_fetch_recent_bars_converts_rates_to_dataframe():
    df = fetch_recent_bars(_FakeMt5(), "XAUUSD", Timeframe.M15, count=5)
    assert len(df) == 5
    assert list(df.columns) == ["open", "high", "low", "close", "tick_volume"]
    assert df.index.is_monotonic_increasing


def test_fetch_recent_bars_carries_tick_volume_through():
    df = fetch_recent_bars(_FakeMt5(), "XAUUSD", Timeframe.M15, count=5)
    assert list(df["tick_volume"]) == [10, 11, 12, 13, 14]


def test_fetch_recent_bars_skips_the_bar_still_forming():
    fake = _FakeMt5()
    fetch_recent_bars(fake, "XAUUSD", Timeframe.M15, count=5)
    assert fake.start_positions == [1]  # position 0 is the incomplete, still-forming bar


def test_wait_or_stop_returns_early_when_a_stop_is_requested(tmp_path):
    stop_path = tmp_path / "paper_trading.stop"
    stop_path.write_text("now")
    started = time.monotonic()
    assert wait_or_stop(30, stop_path) is True
    assert time.monotonic() - started < 1


def test_wait_or_stop_times_out_without_a_stop_request(tmp_path):
    assert wait_or_stop(0.05, tmp_path / "paper_trading.stop", poll_seconds=0.01) is False


def test_update_member_skips_a_bar_it_already_processed():
    fake = _FakeMt5()
    broker = SimulatedBroker(risk_controls=RiskControls(), initial_equity=1.0)
    candidate = _AlwaysLongStrategy()

    processed, bar_time, last_close = update_member(fake, "XAUUSD", candidate, broker, 40, last_bar_time=None)
    assert processed is True
    assert last_close is not None
    position_after_first = broker.position

    # market closed: MT5 keeps returning the same final bar
    processed_again, bar_time_again, _ = update_member(fake, "XAUUSD", candidate, broker, 40, last_bar_time=bar_time)
    assert processed_again is False
    assert bar_time_again == bar_time
    assert broker.position is position_after_first


def test_member_key_distinguishes_timeframes():
    class _Candidate:
        name = "macd_12_26_9"

        def __init__(self, timeframe):
            self.timeframe = timeframe

    assert member_key(_Candidate(Timeframe.M5)) != member_key(_Candidate(Timeframe.H1))


def test_update_member_fetches_and_passes_through_declared_supporting_data():
    """An MTF Candidate declares a DataRequirement; update_member must fetch that Timeframe's bars
    too and pass them through generate_signals' `supporting` dict — not just its own Timeframe."""

    class _RecordingMtfLikeCandidate:
        name = "mtf_like"
        timeframe = Timeframe.M15
        supporting_data = (DataRequirement(timeframe=Timeframe.H1),)

        def __init__(self):
            self.seen_supporting = None

        def generate_signals(self, ohlcv, supporting=None):
            self.seen_supporting = supporting
            return pd.Series(1.0, index=ohlcv.index)

    class _TrackingFakeMt5(_FakeMt5):
        def copy_rates_from_pos(self, symbol, timeframe, start_pos, count):
            self.timeframes_requested = getattr(self, "timeframes_requested", [])
            self.timeframes_requested.append(timeframe)
            return super().copy_rates_from_pos(symbol, timeframe, start_pos, count)

    fake = _TrackingFakeMt5()
    candidate = _RecordingMtfLikeCandidate()
    broker = SimulatedBroker(risk_controls=RiskControls(), initial_equity=1.0)

    processed, _, _ = update_member(fake, "XAUUSD", candidate, broker, 40, last_bar_time=None)

    assert processed is True
    assert candidate.seen_supporting is not None
    key = DataRequirement(timeframe=Timeframe.H1)
    assert key in candidate.seen_supporting
    assert not candidate.seen_supporting[key].empty
    # both the entry Timeframe (M15) and the declared requirement (H1) were actually fetched from MT5
    from tradebot.timeframe import to_mt5_timeframe

    assert to_mt5_timeframe(Timeframe.M15) in fake.timeframes_requested
    assert to_mt5_timeframe(Timeframe.H1) in fake.timeframes_requested


def test_update_member_fetches_a_reference_market_requirement_from_its_own_symbol():
    """A Market-Filtered Candidate's DataRequirement names a Reference Market (e.g. "DXY"), not the
    traded instrument — update_member must fetch that market's own MT5 symbol (registry.py's
    REFERENCE_MARKETS), not gold's."""

    class _MarketFilteredLikeCandidate:
        name = "market_filtered_like"
        timeframe = Timeframe.M15
        supporting_data = (DataRequirement(timeframe=Timeframe.H1, reference_market="DXY"),)

        def __init__(self):
            self.seen_supporting = None

        def generate_signals(self, ohlcv, supporting=None):
            self.seen_supporting = supporting
            return pd.Series(1.0, index=ohlcv.index)

    class _SymbolTrackingFakeMt5(_FakeMt5):
        def copy_rates_from_pos(self, symbol, timeframe, start_pos, count):
            self.symbols_requested = getattr(self, "symbols_requested", [])
            self.symbols_requested.append(symbol)
            return super().copy_rates_from_pos(symbol, timeframe, start_pos, count)

    fake = _SymbolTrackingFakeMt5()
    candidate = _MarketFilteredLikeCandidate()
    broker = SimulatedBroker(risk_controls=RiskControls(), initial_equity=1.0)

    processed, _, _ = update_member(fake, "XAUUSDm", candidate, broker, 40, last_bar_time=None)

    assert processed is True
    key = DataRequirement(timeframe=Timeframe.H1, reference_market="DXY")
    assert key in candidate.seen_supporting
    assert not candidate.seen_supporting[key].empty
    assert "XAUUSDm" in fake.symbols_requested  # the candidate's own entry bars
    assert "DXYm" in fake.symbols_requested  # DXY's own bars, not XAUUSDm again


def test_fetch_recent_bars_handles_no_data():
    class _EmptyMt5:
        def copy_rates_from_pos(self, symbol, timeframe, start_pos, count):
            return None

    df = fetch_recent_bars(_EmptyMt5(), "XAUUSD", Timeframe.M15, count=5)
    assert df.empty
