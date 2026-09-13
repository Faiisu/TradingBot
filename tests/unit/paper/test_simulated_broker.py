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
