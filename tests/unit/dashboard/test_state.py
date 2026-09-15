import pandas as pd
import pytest

from tradebot.dashboard.state import build_state, read_state, write_state
from tradebot.paper.simulated_broker import SimulatedBroker
from tradebot.risk.risk_controls import RiskControls
from tradebot.timeframe import Timeframe


class _StubCandidate:
    def __init__(self, name, timeframe):
        self.name = name
        self.timeframe = timeframe


class _RealYieldFilteredStubCandidate:
    def __init__(self, name, timeframe, max_staleness_business_days=3):
        self.name = name
        self.timeframe = timeframe
        self.reference_market = "REAL_YIELD"
        self.max_staleness_business_days = max_staleness_business_days


def test_build_state_summarizes_members_with_no_open_positions():
    broker = SimulatedBroker(risk_controls=RiskControls(), initial_equity=100.0)
    members = [(_StubCandidate("macd_12_26_9", Timeframe.H1), broker)]

    state = build_state(members, equity_history=[], recent_trades=[], last_close_by_member={})

    assert state["total_equity"] == 100.0
    assert state["total_return_pct"] == 0.0
    assert state["members"][0]["candidate_name"] == "macd_12_26_9"
    assert state["members"][0]["position"] is None


def test_build_state_computes_unrealized_pnl_for_open_positions():
    broker = SimulatedBroker(risk_controls=RiskControls(risk_pct_per_trade=0.01, atr_stop_multiplier=2.0), initial_equity=100.0)
    broker.on_bar(pd.Timestamp("2024-01-01"), open_=100, high=101, low=99, close=100, signal=1, atr_at_bar=1.0)
    members = [(_StubCandidate("ma_crossover", Timeframe.H1), broker)]

    state = build_state(members, equity_history=[], recent_trades=[], last_close_by_member={"ma_crossover__H1": 105.0})

    position = state["members"][0]["position"]
    assert position["direction"] == 1
    assert position["unrealized_pct"] > 0  # price moved up while long


def test_build_state_flags_a_member_held_back_by_stale_reference_market_data():
    broker = SimulatedBroker(risk_controls=RiskControls(), initial_equity=100.0)
    members = [(_RealYieldFilteredStubCandidate("macd_12_26_9_marketfilter_real_yield", Timeframe.M15), broker)]

    state = build_state(
        members, equity_history=[], recent_trades=[], last_close_by_member={}, reference_market_age_business_days={"REAL_YIELD": 5}
    )

    member = state["members"][0]
    assert member["held_back_by_stale_data"] is True
    assert member["stale_data_age_business_days"] == 5


def test_build_state_does_not_flag_a_member_within_the_staleness_threshold():
    broker = SimulatedBroker(risk_controls=RiskControls(), initial_equity=100.0)
    members = [(_RealYieldFilteredStubCandidate("macd_12_26_9_marketfilter_real_yield", Timeframe.M15), broker)]

    state = build_state(
        members, equity_history=[], recent_trades=[], last_close_by_member={}, reference_market_age_business_days={"REAL_YIELD": 2}
    )

    member = state["members"][0]
    assert member["held_back_by_stale_data"] is False
    assert member["stale_data_age_business_days"] == 2


def test_build_state_never_flags_a_member_with_no_staleness_tracked_reference_market():
    """A plain candidate (or one Market-Filtered by DXY/silver, which never carries
    max_staleness_business_days) has nothing to hold back — even if some unrelated Reference Market
    happens to be stale."""
    broker = SimulatedBroker(risk_controls=RiskControls(), initial_equity=100.0)
    members = [(_StubCandidate("macd_12_26_9", Timeframe.H1), broker)]

    state = build_state(
        members, equity_history=[], recent_trades=[], last_close_by_member={}, reference_market_age_business_days={"REAL_YIELD": 99}
    )

    member = state["members"][0]
    assert member["held_back_by_stale_data"] is False
    assert member["stale_data_age_business_days"] is None


def test_build_state_reports_each_members_decision_latency():
    broker = SimulatedBroker(risk_controls=RiskControls(), initial_equity=100.0)
    members = [(_StubCandidate("macd_12_26_9", Timeframe.H1), broker)]

    state = build_state(
        members, equity_history=[], recent_trades=[], last_close_by_member={},
        decision_latency_seconds_by_member={"macd_12_26_9__H1": 12.5},
    )

    assert state["members"][0]["decision_latency_seconds"] == 12.5


def test_build_state_reports_none_decision_latency_for_a_member_never_yet_processed():
    broker = SimulatedBroker(risk_controls=RiskControls(), initial_equity=100.0)
    members = [(_StubCandidate("macd_12_26_9", Timeframe.H1), broker)]

    state = build_state(members, equity_history=[], recent_trades=[], last_close_by_member={})

    assert state["members"][0]["decision_latency_seconds"] is None


def test_build_state_reports_the_worst_decision_latency_across_members():
    broker_a = SimulatedBroker(risk_controls=RiskControls(), initial_equity=100.0)
    broker_b = SimulatedBroker(risk_controls=RiskControls(), initial_equity=100.0)
    members = [
        (_StubCandidate("macd_12_26_9", Timeframe.H1), broker_a),
        (_StubCandidate("ma_crossover_20_50", Timeframe.M5), broker_b),
    ]

    state = build_state(
        members, equity_history=[], recent_trades=[], last_close_by_member={},
        decision_latency_seconds_by_member={"macd_12_26_9__H1": 3.0, "ma_crossover_20_50__M5": 41.0},
    )

    assert state["worst_decision_latency_seconds"] == 41.0


def test_build_state_worst_decision_latency_is_none_when_nothing_processed_yet():
    broker = SimulatedBroker(risk_controls=RiskControls(), initial_equity=100.0)
    members = [(_StubCandidate("macd_12_26_9", Timeframe.H1), broker)]

    state = build_state(members, equity_history=[], recent_trades=[], last_close_by_member={})

    assert state["worst_decision_latency_seconds"] is None


def test_write_and_read_state_round_trips(tmp_path):
    state = {"updated_at": "now", "total_equity": 123.45, "members": [], "recent_trades": [], "equity_history": []}
    path = tmp_path / "paper_state.json"

    write_state(state, path)
    loaded = read_state(path)

    assert loaded == state
