import pandas as pd
import pytest

from tradebot.paper.simulated_broker import SimulatedBroker
from tradebot.risk.risk_controls import RiskControls


@pytest.fixture
def broker():
    controls = RiskControls(risk_pct_per_trade=0.01, atr_stop_multiplier=2.0, max_position_fraction=5.0)
    return SimulatedBroker(risk_controls=controls, initial_equity=1.0)


def _ts(i):
    return pd.Timestamp("2024-01-01") + pd.Timedelta(hours=i)


def test_opens_holds_and_closes_on_signal_flip(broker):
    broker.on_bar(_ts(0), open_=100, high=101, low=99, close=100, signal=1, atr_at_bar=1.0)
    assert broker.position is not None
    assert broker.position.direction == 1
    assert broker.position.stop_price == 98

    # signal still long, price moves favorably, no stop hit -> position untouched
    broker.on_bar(_ts(1), open_=105, high=106, low=104, close=105, signal=1, atr_at_bar=1.0)
    assert broker.trades == []
    assert broker.position.entry_price == 100  # unchanged, still the original position

    # signal flips to short -> closes the long at this bar's close, opens a new short
    broker.on_bar(_ts(2), open_=110, high=111, low=109, close=110, signal=-1, atr_at_bar=1.0)
    assert len(broker.trades) == 1
    closed = broker.trades[0]
    assert closed.direction == 1
    assert closed.exit_reason == "signal_change"
    assert closed.exit_price == 110
    assert broker.equity > 1.0  # long from 100 -> 110 was profitable net of cost

    assert broker.position is not None
    assert broker.position.direction == -1
    assert broker.position.entry_price == 110


def test_stop_loss_closes_the_position_at_the_stop_price(broker):
    broker.on_bar(_ts(0), open_=100, high=101, low=99, close=100, signal=1, atr_at_bar=1.0)
    stop = broker.position.stop_price
    assert stop == 98

    # low breaches the stop
    broker.on_bar(_ts(1), open_=99, high=99.5, low=95, close=96, signal=1, atr_at_bar=1.0)

    assert len(broker.trades) == 1
    closed = broker.trades[0]
    assert closed.exit_reason == "stop_loss"
    assert closed.exit_price == stop
    assert broker.equity < 1.0

    # strategy still signals long, and the same bar re-opens a fresh position after the stop-out
    assert broker.position is not None
    assert broker.position.direction == 1
    assert broker.position.entry_price == 96


def test_no_position_opened_while_signal_is_flat(broker):
    broker.on_bar(_ts(0), open_=100, high=101, low=99, close=100, signal=0, atr_at_bar=1.0)
    assert broker.position is None
    assert broker.trades == []


def test_no_position_opened_during_atr_warmup(broker):
    broker.on_bar(_ts(0), open_=100, high=101, low=99, close=100, signal=1, atr_at_bar=float("nan"))
    assert broker.position is None


@pytest.fixture
def trailing_broker():
    controls = RiskControls(risk_pct_per_trade=0.01, atr_stop_multiplier=2.0, max_position_fraction=5.0, trailing_stop_multiplier=2.0)
    return SimulatedBroker(risk_controls=controls, initial_equity=1.0)


def test_trailing_stop_ratchets_up_as_price_makes_new_highs(trailing_broker):
    # entry bar's own high (101) seeds the initial extreme, matching BacktestEngine's convention
    trailing_broker.on_bar(_ts(0), open_=100, high=101, low=99, close=100, signal=1, atr_at_bar=1.0)
    assert trailing_broker.position.stop_price == 98  # initial fixed stop, atr=1.0 * 2.0

    # bar 1's stop reflects the extreme through bar 0 only (101 - 2*1.0 = 99) — no look-ahead onto its
    # own high; bar 1's high of 106 only updates the extreme for bar 2 onward
    trailing_broker.on_bar(_ts(1), open_=104, high=106, low=103, close=105, signal=1, atr_at_bar=1.0)
    assert trailing_broker.trades == []
    assert trailing_broker.position.stop_price == 99
    assert trailing_broker.position.extreme_price == 106

    # bar 2's stop now trails the 106 extreme from bar 1 -> 106 - 2*1.0 = 104
    trailing_broker.on_bar(_ts(2), open_=105, high=105, low=104.5, close=104.5, signal=1, atr_at_bar=1.0)
    assert trailing_broker.trades == []
    assert trailing_broker.position.stop_price == 104

    # price pulls back but stays above the trail -> stop must not loosen back down
    trailing_broker.on_bar(_ts(3), open_=104.5, high=104.5, low=104.2, close=104.2, signal=1, atr_at_bar=1.0)
    assert trailing_broker.trades == []
    assert trailing_broker.position.stop_price == 104


def test_trailing_stop_closes_the_position_when_price_pulls_back_through_the_trail(trailing_broker):
    trailing_broker.on_bar(_ts(0), open_=100, high=101, low=99, close=100, signal=1, atr_at_bar=1.0)
    trailing_broker.on_bar(_ts(1), open_=104, high=106, low=103, close=105, signal=1, atr_at_bar=1.0)  # extreme -> 106
    trailing_broker.on_bar(_ts(2), open_=105, high=105, low=104.5, close=104.5, signal=1, atr_at_bar=1.0)  # trail -> 104

    # low breaches the trailing level (104), not the original fixed stop (98)
    trailing_broker.on_bar(_ts(3), open_=104, high=104, low=103, close=103.5, signal=1, atr_at_bar=1.0)

    assert len(trailing_broker.trades) == 1
    closed = trailing_broker.trades[0]
    assert closed.exit_reason == "trailing_stop"
    assert closed.exit_price == 104
    assert closed.pnl_pct > 0  # still a winning trade, unlike a fixed-stop loss


def test_trailing_stop_disabled_by_default_matches_pre_ticket_06_behavior(broker):
    """`broker` fixture has no trailing_stop_multiplier configured — must be identical to the fixed
    stop-only behavior that existed before ticket 06."""
    broker.on_bar(_ts(0), open_=100, high=101, low=99, close=100, signal=1, atr_at_bar=1.0)
    broker.on_bar(_ts(1), open_=110, high=120, low=109, close=115, signal=1, atr_at_bar=1.0)
    assert broker.position.stop_price == 98  # never trails, stays at the original fixed stop


@pytest.fixture
def target_broker():
    controls = RiskControls(risk_pct_per_trade=0.01, atr_stop_multiplier=2.0, max_position_fraction=5.0, profit_target_r_multiple=1.0)
    return SimulatedBroker(risk_controls=controls, initial_equity=1.0)


def test_profit_target_closes_the_position_once_reached(target_broker):
    # 1R = atr_stop_multiplier * atr = 2.0, so target = entry + 1.0*2.0 = 102
    target_broker.on_bar(_ts(0), open_=100, high=101, low=99, close=100, signal=1, atr_at_bar=1.0)
    target_broker.on_bar(_ts(1), open_=101, high=103, low=100, close=102, signal=1, atr_at_bar=1.0)

    assert len(target_broker.trades) == 1
    closed = target_broker.trades[0]
    assert closed.exit_reason == "profit_target"
    assert closed.exit_price == 102
    assert closed.pnl_pct > 0


def test_stop_loss_takes_priority_over_profit_target_on_the_same_bar():
    controls = RiskControls(
        risk_pct_per_trade=0.01, atr_stop_multiplier=2.0, max_position_fraction=5.0, profit_target_r_multiple=1.0
    )
    broker = SimulatedBroker(risk_controls=controls, initial_equity=1.0)
    broker.on_bar(_ts(0), open_=100, high=101, low=99, close=100, signal=1, atr_at_bar=1.0)  # stop=98, target=102

    # a wide bar whose range spans both the stop (98) and the target (102)
    broker.on_bar(_ts(1), open_=100, high=200, low=50, close=100, signal=1, atr_at_bar=1.0)

    assert len(broker.trades) == 1
    assert broker.trades[0].exit_reason == "stop_loss"
