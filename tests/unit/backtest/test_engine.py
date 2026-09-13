import numpy as np
import pandas as pd
import pytest

from tradebot.backtest.engine import BacktestEngine
from tradebot.risk.risk_controls import RiskControls
from tradebot.timeframe import Timeframe


class _NoOpStrategy:
    name = "no_op"

    def __init__(self, timeframe):
        self.timeframe = timeframe

    def generate_signals(self, ohlcv: pd.DataFrame, htf_ohlcv: pd.DataFrame | None = None) -> pd.Series:
        return pd.Series(0.0, index=ohlcv.index)


class _AlwaysLongAfterWarmupStrategy:
    name = "always_long"

    def __init__(self, timeframe, warmup: int = 20):
        self.timeframe = timeframe
        self.warmup = warmup

    def generate_signals(self, ohlcv: pd.DataFrame, htf_ohlcv: pd.DataFrame | None = None) -> pd.Series:
        signal = pd.Series(0.0, index=ohlcv.index)
        signal.iloc[self.warmup :] = 1
        return signal


def _ohlcv(close, band=0.2):
    close = np.asarray(close, dtype=float)
    index = pd.date_range("2024-01-01", periods=len(close), freq="h")
    return pd.DataFrame(
        {
            "open": close,
            "high": close + band,
            "low": close - band,
            "close": close,
        },
        index=index,
    )


@pytest.fixture
def risk_controls():
    return RiskControls(risk_pct_per_trade=0.01, atr_stop_multiplier=2.0, max_position_fraction=5.0)


def test_no_signal_means_no_trades_and_flat_equity(risk_controls):
    ohlcv = _ohlcv(np.full(60, 100.0))
    engine = BacktestEngine(risk_controls=risk_controls)
    result = engine.run(_NoOpStrategy(Timeframe.H1), ohlcv)

    assert result.trades == []
    assert (result.equity_curve == 1.0).all()
    assert (result.drawdown_series == 0.0).all()


def test_transaction_cost_reduces_pnl(risk_controls):
    close = np.concatenate([np.full(20, 100.0), np.linspace(100, 160, 40)])
    ohlcv = _ohlcv(close)
    strategy = _AlwaysLongAfterWarmupStrategy(Timeframe.H1)

    no_cost_controls = RiskControls(
        risk_pct_per_trade=risk_controls.risk_pct_per_trade,
        atr_stop_multiplier=risk_controls.atr_stop_multiplier,
        max_position_fraction=risk_controls.max_position_fraction,
        round_trip_cost_price=0.0,
    )
    free_result = BacktestEngine(risk_controls=no_cost_controls).run(strategy, ohlcv)
    costly_result = BacktestEngine(risk_controls=risk_controls).run(strategy, ohlcv)

    assert costly_result.trades[0].cost_pct > 0
    assert costly_result.equity_curve.iloc[-1] < free_result.equity_curve.iloc[-1]


def test_sustained_uptrend_produces_one_profitable_trade(risk_controls):
    close = np.concatenate([np.full(20, 100.0), np.linspace(100, 160, 40)])
    ohlcv = _ohlcv(close)
    engine = BacktestEngine(risk_controls=risk_controls)
    result = engine.run(_AlwaysLongAfterWarmupStrategy(Timeframe.H1), ohlcv)

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.direction == 1
    assert trade.exit_reason == "signal_change"
    assert trade.pnl_pct > 0
    assert result.equity_curve.iloc[-1] > result.equity_curve.iloc[0]


def test_sharp_drop_triggers_stop_loss_and_reenters_if_signal_is_unchanged(risk_controls):
    warmup = np.tile([100.2, 99.8], 10)  # small oscillation so ATR is nonzero
    crash = np.array([90.0, 80.0, 80.0, 80.0, 80.0])
    close = np.concatenate([warmup, crash])
    ohlcv = _ohlcv(close, band=0.3)
    engine = BacktestEngine(risk_controls=risk_controls)
    result = engine.run(_AlwaysLongAfterWarmupStrategy(Timeframe.H1, warmup=20), ohlcv)

    # the strategy is still signalling long after the stop-out, so the engine re-enters immediately
    # (same-bar), matching SimulatedBroker's paper-trading behavior rather than sitting out for free
    assert len(result.trades) == 2
    stopped_out, reentry = result.trades
    assert stopped_out.exit_reason == "stop_loss"
    assert stopped_out.exit_price == stopped_out.stop_price
    assert reentry.entry_time == stopped_out.exit_time
    assert reentry.entry_price == 80.0  # re-enters at that bar's close, not the stop price it exited at

    loss = result.equity_curve.iloc[-1] / result.equity_curve.iloc[0] - 1
    assert -0.03 < loss < -0.003  # both trades lose a bit; not exact due to ATR shape


def test_reentry_loop_never_reads_past_the_segments_own_end(risk_controls):
    """Regression check for the re-entry loop's bound: even when a stop hits on the segment's second-
    to-last bar (forcing a re-entry attempt on the very last bar), the loop must not read into the
    flat (signal=0) bars beyond the segment."""

    class _LongThenFlatStrategy:
        name = "long_then_flat"

        def __init__(self, timeframe):
            self.timeframe = timeframe

        def generate_signals(self, ohlcv, htf_ohlcv=None):
            signal = pd.Series(0.0, index=ohlcv.index)
            signal.iloc[20:22] = 1  # long for exactly bars 20-21, flat after
            return signal

    warmup = np.tile([100.2, 99.8], 10)
    crash = np.array([90.0, 80.0, 80.0, 80.0, 80.0])
    close = np.concatenate([warmup, crash])
    ohlcv = _ohlcv(close, band=0.3)
    engine = BacktestEngine(risk_controls=risk_controls)
    result = engine.run(_LongThenFlatStrategy(Timeframe.H1), ohlcv)

    # bar 21 (the segment's last bar) triggers the stop, forcing a same-bar re-entry that then has
    # nowhere left to go within the segment: both trades close at/before bar 21, never touching bar 22+
    assert len(result.trades) == 2
    assert result.trades[0].exit_reason == "stop_loss"
    assert all(t.exit_time <= ohlcv.index[21] for t in result.trades)


def test_engine_runs_an_mtf_candidate_with_htf_ohlcv(risk_controls):
    from tradebot.strategies.mtf import MtfCandidate

    close = np.concatenate([np.full(20, 100.0), np.linspace(100, 160, 40)])
    ohlcv = _ohlcv(close)  # M15-shaped in name only; freq doesn't matter for this test
    htf_ohlcv = _ohlcv(close)  # same series stands in for the H1 filter feed

    entry = _AlwaysLongAfterWarmupStrategy(Timeframe.M15, warmup=20)
    always_up_filter = lambda df: pd.Series(1.0, index=df.index)  # noqa: E731
    candidate = MtfCandidate(entry, always_up_filter, "always_up", Timeframe.H1)

    engine = BacktestEngine(risk_controls=risk_controls)
    result = engine.run(candidate, ohlcv, htf_ohlcv)

    assert len(result.trades) == 1
    assert result.trades[0].direction == 1
    assert result.trades[0].pnl_pct > 0

    always_down_filter = lambda df: pd.Series(-1.0, index=df.index)  # noqa: E731
    blocked_candidate = MtfCandidate(entry, always_down_filter, "always_down", Timeframe.H1)
    blocked_result = engine.run(blocked_candidate, ohlcv, htf_ohlcv)

    assert blocked_result.trades == []
