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


def test_write_and_read_state_round_trips(tmp_path):
    state = {"updated_at": "now", "total_equity": 123.45, "members": [], "recent_trades": [], "equity_history": []}
    path = tmp_path / "paper_state.json"

    write_state(state, path)
    loaded = read_state(path)

    assert loaded == state
