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


def test_trailing_stop_exits_on_a_pullback_from_the_peak_while_still_profitable():
    """rule-set-expansion phase-1 ticket 06: bounds the winning side the same way the fixed stop bounds
    the losing side. Constant-true-range warmup (band=0, closes alternating +1/-1) lets ATR converge to
    a known value (2.0) before entry, so the trailing level can be checked exactly via the same
    (independently unit-tested in test_risk_controls.py) RiskControls.trailing_stop_price formula —
    this test's job is only to confirm the engine wires atr_at_entry and the running peak into that
    formula correctly, bar by bar, not to re-derive the formula itself."""
    from tradebot.indicators import atr as atr_indicator

    warmup = np.tile([101.0, 99.0], 30)  # constant true range = 2.0/bar (band=0) -> ATR converges to ~2.0
    rally = np.linspace(103.0, 180.0, 20)  # steady rally to a peak of 180
    pullback = np.array([170.0, 160.0, 150.0, 150.0, 150.0])  # sharp pullback below the trailing level
    close = np.concatenate([warmup, rally, pullback])
    ohlcv = _ohlcv(close, band=0.0)

    controls = RiskControls(risk_pct_per_trade=0.01, atr_stop_multiplier=2.0, max_position_fraction=5.0, trailing_stop_multiplier=2.0)
    engine = BacktestEngine(risk_controls=controls)
    result = engine.run(_AlwaysLongAfterWarmupStrategy(Timeframe.H1, warmup=len(warmup)), ohlcv)

    entry_idx = len(warmup)
    atr_at_entry = atr_indicator(ohlcv["high"], ohlcv["low"], ohlcv["close"], period=engine.atr_period).iloc[entry_idx]
    expected_exit_price = controls.trailing_stop_price(entry_price=close[entry_idx], atr_at_entry=atr_at_entry, direction=1, extreme_price=180.0)

    trade = result.trades[0]
    assert trade.exit_reason == "trailing_stop"
    assert trade.exit_price == pytest.approx(expected_exit_price, abs=0.05)
    assert trade.exit_price == trade.stop_price  # the trailing level in effect at exit, same convention as a fixed stop-loss
    assert trade.pnl_pct > 0  # exited well above entry, despite pulling back from the peak


def test_trailing_stop_never_loosens_after_an_interim_pullback_that_does_not_hit_it():
    """A dip that doesn't breach the trail must not reset the tracked peak — the next rally's trail
    still measures from the ORIGINAL higher peak, never from the interim low."""
    warmup = np.tile([101.0, 99.0], 30)
    first_rally = np.linspace(103.0, 140.0, 15)  # peak at 140
    shallow_dip = np.linspace(139.0, 137.0, 5)  # dips a little, not enough to hit a trail from 140
    second_rally = np.linspace(138.0, 200.0, 15)  # new peak at 200
    crash = np.array([190.0, 170.0, 150.0, 150.0, 150.0])  # crashes hard, well past a trail from either peak
    close = np.concatenate([warmup, first_rally, shallow_dip, second_rally, crash])
    ohlcv = _ohlcv(close, band=0.0)

    controls = RiskControls(risk_pct_per_trade=0.01, atr_stop_multiplier=2.0, max_position_fraction=5.0, trailing_stop_multiplier=2.0)
    engine = BacktestEngine(risk_controls=controls)
    result = engine.run(_AlwaysLongAfterWarmupStrategy(Timeframe.H1, warmup=len(warmup)), ohlcv)

    trade = result.trades[0]
    assert trade.exit_reason == "trailing_stop"
    # the trail that finally triggered must reflect the 200 peak, not the earlier 140 peak or the dip
    assert trade.exit_price > 180.0


def test_profit_target_exits_exactly_at_n_times_the_initial_risk():
    from tradebot.indicators import atr as atr_indicator

    warmup = np.tile([100.2, 99.8], 10)  # 20 bars of oscillation
    rally = np.full(10, 110.0)  # far enough above entry to guarantee the target is crossed
    close = np.concatenate([warmup, rally])
    ohlcv = _ohlcv(close, band=0.2)

    # entry partway through the oscillation (bar 14, once ATR's 14-period warmup is satisfied), so the
    # rally afterward is a genuine favorable move away from the entry price, not flat from bar one
    entry_warmup = 14
    controls = RiskControls(risk_pct_per_trade=0.01, atr_stop_multiplier=2.0, max_position_fraction=5.0, profit_target_r_multiple=1.0)
    engine = BacktestEngine(risk_controls=controls)
    result = engine.run(_AlwaysLongAfterWarmupStrategy(Timeframe.H1, warmup=entry_warmup), ohlcv)

    entry_idx = entry_warmup
    atr_at_entry = atr_indicator(ohlcv["high"], ohlcv["low"], ohlcv["close"], period=engine.atr_period).iloc[entry_idx]
    expected_target = controls.profit_target_price(entry_price=close[entry_idx], atr_at_entry=atr_at_entry, direction=1)

    trade = result.trades[0]
    assert trade.exit_reason == "profit_target"
    assert trade.exit_price == pytest.approx(expected_target, abs=0.01)
    assert trade.pnl_pct > 0


def test_stop_loss_takes_priority_over_profit_target_when_both_could_trigger_the_same_bar():
    """No intrabar sequencing is available (only OHLC), so a bar whose range spans both the stop and the
    target is resolved conservatively: the stop-loss (the risk-defining boundary) is checked first."""
    warmup = np.tile([100.2, 99.8], 10)
    wide_bar_close = np.array([100.0])
    close = np.concatenate([warmup, wide_bar_close])
    index = pd.date_range("2024-01-01", periods=len(close), freq="h")
    ohlcv = pd.DataFrame(
        {
            "open": close,
            "high": np.concatenate([close[:-1] + 0.2, [200.0]]),  # last bar's range spans both target and stop
            "low": np.concatenate([close[:-1] - 0.2, [50.0]]),
            "close": close,
        },
        index=index,
    )

    controls = RiskControls(
        risk_pct_per_trade=0.01, atr_stop_multiplier=2.0, max_position_fraction=5.0, profit_target_r_multiple=1.0
    )
    engine = BacktestEngine(risk_controls=controls)
    # entry partway through the oscillation (bar 14) so the segment still has bars left to reach the
    # final wide bar, rather than entry and the wide bar being the same single-bar segment
    result = engine.run(_AlwaysLongAfterWarmupStrategy(Timeframe.H1, warmup=14), ohlcv)

    trade = result.trades[0]
    assert trade.exit_reason == "stop_loss"


def test_bounding_mechanisms_disabled_by_default_leave_engine_behavior_unchanged(risk_controls):
    """Regression guard: with trailing_stop_multiplier and profit_target_r_multiple left at their
    default None, the engine's behavior must be byte-identical to before ticket 06."""
    close = np.concatenate([np.full(20, 100.0), np.linspace(100, 160, 40)])
    ohlcv = _ohlcv(close)
    result = BacktestEngine(risk_controls=risk_controls).run(_AlwaysLongAfterWarmupStrategy(Timeframe.H1), ohlcv)

    assert len(result.trades) == 1
    assert result.trades[0].exit_reason == "signal_change"


def test_engine_runs_an_mtf_candidate_via_the_supporting_data_channel(risk_controls):
    from tradebot.strategies.base import DataRequirement
    from tradebot.strategies.mtf import MtfCandidate

    close = np.concatenate([np.full(20, 100.0), np.linspace(100, 160, 40)])
    ohlcv = _ohlcv(close)  # M15-shaped in name only; freq doesn't matter for this test
    htf_ohlcv = _ohlcv(close)  # same series stands in for the H1 filter feed
    supporting = {DataRequirement(timeframe=Timeframe.H1): htf_ohlcv}

    entry = _AlwaysLongAfterWarmupStrategy(Timeframe.M15, warmup=20)
    always_up_filter = lambda df: pd.Series(1.0, index=df.index)  # noqa: E731
    candidate = MtfCandidate(entry, always_up_filter, "always_up", Timeframe.H1)

    engine = BacktestEngine(risk_controls=risk_controls)
    result = engine.run(candidate, ohlcv, supporting)

    assert len(result.trades) == 1
    assert result.trades[0].direction == 1
    assert result.trades[0].pnl_pct > 0

    always_down_filter = lambda df: pd.Series(-1.0, index=df.index)  # noqa: E731
    blocked_candidate = MtfCandidate(entry, always_down_filter, "always_down", Timeframe.H1)
    blocked_result = engine.run(blocked_candidate, ohlcv, supporting)

    assert blocked_result.trades == []
