import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from tradebot.paper.loop import (
    decide_and_update,
    decision_latency_seconds,
    fetch_recent_bars,
    member_key,
    missed_nominal_closes,
    nominal_bar_close,
    run_tick,
    seconds_until_next_bar_close,
    timeframe_closed_at,
    update_member,
    wait_or_stop,
)
from tradebot.paper.simulated_broker import SimulatedBroker
from tradebot.risk.risk_controls import RiskControls
from tradebot.strategies.base import DataRequirement
from tradebot.timeframe import TIMEFRAME_SECONDS, Timeframe


class _AlwaysLongStrategy:
    name = "always_long"
    timeframe = Timeframe.H1
    supporting_data: tuple = ()

    def generate_signals(self, ohlcv: pd.DataFrame, supporting: dict | None = None) -> pd.Series:
        return pd.Series(1.0, index=ohlcv.index)


class _AlwaysLongCandidate:
    """Like _AlwaysLongStrategy, but with a configurable name/timeframe — needed to build several
    members that differ only in Timeframe for the alignment tests below."""

    supporting_data: tuple = ()

    def __init__(self, name: str, timeframe: Timeframe):
        self.name = name
        self.timeframe = timeframe

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

    processed, bar_time, last_close, _ = update_member(fake, "XAUUSD", candidate, broker, 40, last_bar_time=None)
    assert processed is True
    assert last_close is not None
    position_after_first = broker.position

    # market closed: MT5 keeps returning the same final bar
    processed_again, bar_time_again, _, _ = update_member(fake, "XAUUSD", candidate, broker, 40, last_bar_time=bar_time)
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

    processed, _, _, _ = update_member(fake, "XAUUSD", candidate, broker, 40, last_bar_time=None)

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

    processed, _, _, _ = update_member(fake, "XAUUSDm", candidate, broker, 40, last_bar_time=None)

    assert processed is True
    key = DataRequirement(timeframe=Timeframe.H1, reference_market="DXY")
    assert key in candidate.seen_supporting
    assert not candidate.seen_supporting[key].empty
    assert "XAUUSDm" in fake.symbols_requested  # the candidate's own entry bars
    assert "DXYm" in fake.symbols_requested  # DXY's own bars, not XAUUSDm again


def test_update_member_refreshes_a_fred_backed_reference_market_instead_of_fetching_it_from_mt5(tmp_path, monkeypatch):
    """A real-yield-filtered candidate's DataRequirement names "REAL_YIELD", which registry.py's
    REFERENCE_MARKETS configures with a fred_series_id, not an MT5 symbol — update_member must refresh
    the FRED-backed cache (data/real_yield.py) instead of calling MT5 with a None symbol."""
    import tradebot.paper.loop as loop_module

    monkeypatch.setattr(loop_module, "CACHE_DIR", tmp_path)

    class _RealYieldFilteredLikeCandidate:
        name = "real_yield_filtered_like"
        timeframe = Timeframe.M15
        supporting_data = (DataRequirement(timeframe=Timeframe.H1, reference_market="REAL_YIELD"),)
        reference_market = "REAL_YIELD"
        max_staleness_business_days = 3

        def __init__(self):
            self.seen_supporting = None

        def generate_signals(self, ohlcv, supporting=None):
            self.seen_supporting = supporting
            return pd.Series(1.0, index=ohlcv.index)

    fake = _FakeMt5()
    candidate = _RealYieldFilteredLikeCandidate()
    broker = SimulatedBroker(risk_controls=RiskControls(), initial_equity=1.0)

    csv_text = "observation_date,DFII10\n2024-01-02,1.50\n"
    processed, _, _, reference_market_ages = update_member(
        fake, "XAUUSDm", candidate, broker, 40, last_bar_time=None, fetch_csv=lambda: csv_text
    )

    assert processed is True
    key = DataRequirement(timeframe=Timeframe.H1, reference_market="REAL_YIELD")
    assert key in candidate.seen_supporting
    assert not candidate.seen_supporting[key].empty
    assert "REAL_YIELD" in reference_market_ages
    assert isinstance(reference_market_ages["REAL_YIELD"], int)


def test_update_member_reports_reference_market_ages_only_for_staleness_tracked_markets():
    """DXY has no max_staleness_business_days (sourced live from MT5 every tick) — update_member must
    not report an age for it, since nothing on the dashboard needs to explain DXY as "stale"."""

    class _DxyFilteredLikeCandidate:
        name = "dxy_filtered_like"
        timeframe = Timeframe.M15
        supporting_data = (DataRequirement(timeframe=Timeframe.H1, reference_market="DXY"),)

        def generate_signals(self, ohlcv, supporting=None):
            return pd.Series(1.0, index=ohlcv.index)

    fake = _FakeMt5()
    broker = SimulatedBroker(risk_controls=RiskControls(), initial_equity=1.0)

    _, _, _, reference_market_ages = update_member(fake, "XAUUSDm", _DxyFilteredLikeCandidate(), broker, 40, last_bar_time=None)

    assert reference_market_ages == {}


def test_fetch_recent_bars_handles_no_data():
    class _EmptyMt5:
        def copy_rates_from_pos(self, symbol, timeframe, start_pos, count):
            return None

    df = fetch_recent_bars(_EmptyMt5(), "XAUUSD", Timeframe.M15, count=5)
    assert df.empty


# ---------------------------------------------------------------------------
# Ticket 01: members act on their own Timeframe's real wall-clock close, not on a loop-local tick
# counter that drifts with whatever moment the loop happened to start.
# ---------------------------------------------------------------------------


def test_nominal_bar_close_rounds_down_to_the_smallest_timeframes_boundary():
    # 1_726_000_200 % 300 == 0 already (a true M5 boundary) — pick a moment 47s into that bar to
    # prove rounding-down, not just echoing an already-aligned instant.
    now = datetime.fromtimestamp(1_726_000_200 + 47, tz=timezone.utc)
    nominal = nominal_bar_close(now, Timeframe.M5)
    assert nominal.timestamp() == 1_726_000_200
    assert nominal.timestamp() % TIMEFRAME_SECONDS[Timeframe.M5] == 0


def test_nominal_bar_close_is_idempotent_on_an_exact_boundary():
    now = datetime.fromtimestamp(1_726_000_200, tz=timezone.utc)
    assert nominal_bar_close(now, Timeframe.M5).timestamp() == 1_726_000_200


def test_timeframe_closed_at_true_only_for_boundaries_shared_with_the_larger_timeframe():
    h1_boundary = datetime.fromtimestamp(1_726_002_000, tz=timezone.utc)  # multiple of 3600
    assert h1_boundary.timestamp() % 3600 == 0
    non_h1_m5_boundary = datetime.fromtimestamp(1_726_002_000 + 300, tz=timezone.utc)  # +5min, not /3600
    assert non_h1_m5_boundary.timestamp() % 3600 != 0

    assert timeframe_closed_at(Timeframe.H1, h1_boundary) is True
    assert timeframe_closed_at(Timeframe.H1, non_h1_m5_boundary) is False
    # every smallest-Timeframe boundary is trivially one of its own Timeframe's boundaries
    assert timeframe_closed_at(Timeframe.M5, non_h1_m5_boundary) is True


def test_h1_boundaries_land_on_exact_epoch_multiples_regardless_of_where_the_scan_starts():
    """Regression test for the original bug: a loop-local tick counter starting at whatever moment the
    loop happened to launch could make an H1 member fire up to 55 minutes after the real H1 close.
    Wall-clock alignment has no notion of a "start" at all — scanning any run of real M5 boundaries
    must flag exactly the ones that are true multiples of 3600s, however that run of ticks happens to
    be lined up against the clock."""
    for start_epoch in (1_726_000_000, 1_726_000_037, 1_726_000_122, 1_726_000_299):
        first_m5_boundary = start_epoch - (start_epoch % 300) + 300
        fired = []
        for i in range(24):  # 2 hours of M5 ticks
            now = datetime.fromtimestamp(first_m5_boundary + i * 300, tz=timezone.utc)
            nominal = nominal_bar_close(now, Timeframe.M5)
            if timeframe_closed_at(Timeframe.H1, nominal):
                fired.append(int(nominal.timestamp()))
        assert fired, f"no H1 boundary detected starting from offset {start_epoch}"
        assert all(t % 3600 == 0 for t in fired)


def test_run_tick_updates_only_members_whose_own_timeframe_closed_this_tick():
    fake = _FakeMt5()
    m5_broker = SimulatedBroker(risk_controls=RiskControls(), initial_equity=1.0)
    h1_broker = SimulatedBroker(risk_controls=RiskControls(), initial_equity=1.0)
    members = [
        (_AlwaysLongCandidate("m5cand", Timeframe.M5), m5_broker),
        (_AlwaysLongCandidate("h1cand", Timeframe.H1), h1_broker),
    ]
    last_bar_time_by_member: dict = {}
    decision_latency_by_member: dict = {}

    # An M5 boundary that is deliberately NOT an H1 boundary.
    non_h1_tick = datetime.fromtimestamp(1_726_002_000 + 300, tz=timezone.utc)
    assert non_h1_tick.timestamp() % 3600 != 0
    run_tick(
        non_h1_tick, non_h1_tick, fake, "XAUUSD", members, 40,
        last_bar_time_by_member, decision_latency_by_member, {}, [],
    )

    assert m5_broker.position is not None
    assert h1_broker.position is None  # not due yet — this is exactly the bug ticket 01 fixes

    # The next true H1 boundary: now H1 must be updated too.
    h1_tick = datetime.fromtimestamp(1_726_005_600, tz=timezone.utc)  # a multiple of 3600
    assert h1_tick.timestamp() % 3600 == 0
    run_tick(
        h1_tick, h1_tick, fake, "XAUUSD", members, 40,
        last_bar_time_by_member, decision_latency_by_member, {}, [],
    )
    assert h1_broker.position is not None


def test_run_tick_records_decision_latency_after_processing():
    fake = _FakeMt5()
    broker = SimulatedBroker(risk_controls=RiskControls(), initial_equity=1.0)
    candidate = _AlwaysLongCandidate("m5cand", Timeframe.M5)
    last_bar_time_by_member: dict = {}
    decision_latency_by_member: dict = {}

    now = datetime.fromtimestamp(1_726_000_200, tz=timezone.utc)
    run_tick(
        now, now, fake, "XAUUSD", [(candidate, broker)], 40,
        last_bar_time_by_member, decision_latency_by_member, {}, [],
    )

    key = member_key(candidate)
    assert key in decision_latency_by_member
    assert decision_latency_by_member[key] > 0


def test_run_tick_skips_already_processed_bars_without_recording_new_latency():
    fake = _FakeMt5()
    broker = SimulatedBroker(risk_controls=RiskControls(), initial_equity=1.0)
    candidate = _AlwaysLongCandidate("m5cand", Timeframe.M5)
    last_bar_time_by_member: dict = {}
    decision_latency_by_member: dict = {}

    now = datetime.fromtimestamp(1_726_000_200, tz=timezone.utc)
    run_tick(now, now, fake, "XAUUSD", [(candidate, broker)], 40, last_bar_time_by_member, decision_latency_by_member, {}, [])
    first_latency = decision_latency_by_member[member_key(candidate)]

    later = datetime.fromtimestamp(1_726_000_500, tz=timezone.utc)  # market closed: same final bar
    run_tick(later, later, fake, "XAUUSD", [(candidate, broker)], 40, last_bar_time_by_member, decision_latency_by_member, {}, [])

    assert decision_latency_by_member[member_key(candidate)] == first_latency


def test_run_tick_uses_the_nominal_close_for_gating_but_now_for_latency():
    """The catch-up scheduler (missed_nominal_closes) can hand run_tick a `nominal_close` earlier than
    the actual wall-clock `now` it's processed at — e.g. a slow iteration made the loop late. Gating
    (which members are due) must use the boundary being caught up on, but the reported decision latency
    must reflect how late it *actually* ran, so a slow-processing incident shows up on the dashboard
    instead of being hidden by pretending it ran on time."""

    class _BarsEndingAtMt5:
        """Enough bars (for a non-NaN ATR) ending exactly at `last_bar_epoch`."""

        def __init__(self, last_bar_epoch, count=20, spacing=3600):
            self.last_bar_epoch = last_bar_epoch
            self.count = count
            self.spacing = spacing

        def copy_rates_from_pos(self, symbol, timeframe, start_pos, count):
            dtype = [("time", "i8"), ("open", "f8"), ("high", "f8"), ("low", "f8"), ("close", "f8"), ("tick_volume", "i8")]
            start = self.last_bar_epoch - (self.count - 1) * self.spacing
            return np.array(
                [(start + i * self.spacing, 100.0 + i, 101.0 + i, 99.0 + i, 100.5 + i, 10) for i in range(self.count)],
                dtype=dtype,
            )

    stale_h1_boundary = datetime.fromtimestamp(1_726_005_600, tz=timezone.utc)  # a true H1 boundary
    actually_ran_at = stale_h1_boundary + timedelta(seconds=400)  # processed 400s late
    fake = _BarsEndingAtMt5(int(stale_h1_boundary.timestamp()))
    broker = SimulatedBroker(risk_controls=RiskControls(), initial_equity=1.0)
    candidate = _AlwaysLongCandidate("h1cand", Timeframe.H1)
    decision_latency_by_member: dict = {}

    run_tick(actually_ran_at, stale_h1_boundary, fake, "XAUUSD", [(candidate, broker)], 40, {}, decision_latency_by_member, {}, [])

    assert broker.position is not None  # gated on the H1 boundary, so it did fire
    key = member_key(candidate)
    assert decision_latency_by_member[key] == pytest.approx(400.0)


def test_decision_latency_seconds_handles_a_timezone_naive_bar_time():
    bar_time = pd.Timestamp(1_726_000_000, unit="s")  # naive, as produced by fetch_recent_bars
    decided_at = datetime.fromtimestamp(1_726_000_030, tz=timezone.utc)
    assert decision_latency_seconds(bar_time, decided_at) == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# missed_nominal_closes: catch-up when an iteration runs later than one smallest-Timeframe interval,
# so a larger Timeframe's boundary is processed (possibly late) instead of silently skipped forever.
# ---------------------------------------------------------------------------


def test_missed_nominal_closes_returns_only_current_when_nothing_was_missed():
    previous = datetime.fromtimestamp(1_726_000_200, tz=timezone.utc)
    current = datetime.fromtimestamp(1_726_000_500, tz=timezone.utc)  # exactly one M5 step later
    assert missed_nominal_closes(previous, current, Timeframe.M5) == [current]


def test_missed_nominal_closes_returns_current_when_there_is_no_previous_tick():
    current = datetime.fromtimestamp(1_726_000_200, tz=timezone.utc)
    assert missed_nominal_closes(None, current, Timeframe.M5) == [current]


def test_missed_nominal_closes_backfills_every_boundary_skipped_by_a_slow_iteration():
    previous = datetime.fromtimestamp(1_726_000_200, tz=timezone.utc)
    current = datetime.fromtimestamp(1_726_000_200 + 300 * 3, tz=timezone.utc)  # 2 boundaries skipped
    result = missed_nominal_closes(previous, current, Timeframe.M5)
    assert result == [previous + timedelta(seconds=300), previous + timedelta(seconds=600), current]


def test_missed_nominal_closes_caps_catch_up_after_a_long_gap():
    previous = datetime.fromtimestamp(1_726_000_200, tz=timezone.utc)
    current = previous + timedelta(seconds=300 * 200)  # e.g. the machine slept for ~16.7 hours
    result = missed_nominal_closes(previous, current, Timeframe.M5, max_catch_up=12)
    assert len(result) == 12
    assert result[-1] == current  # always ends on the real current boundary
    assert all((result[i + 1] - result[i]).total_seconds() == 300 for i in range(len(result) - 1))
