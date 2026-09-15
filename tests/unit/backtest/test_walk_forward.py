import numpy as np
import pandas as pd
import pytest

from tradebot.backtest.walk_forward import WindowOutcome, chain_equity_curve, compute_windows, run_walk_forward
from tradebot.ensemble.selection import EnsembleMember


def test_first_selection_window_is_180_days_from_the_data_start():
    windows = compute_windows(pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-01") + pd.Timedelta(days=400))

    assert windows[0].selection_start == pd.Timestamp("2024-01-01")
    assert windows[0].test_start == pd.Timestamp("2024-01-01") + pd.Timedelta(days=180)


def test_selection_window_is_anchored_and_grows_while_test_windows_are_fixed_length():
    start = pd.Timestamp("2024-01-01")
    windows = compute_windows(start, start + pd.Timedelta(days=400))

    assert all(w.selection_start == start for w in windows)  # anchored: never moves
    for w in windows:
        assert (w.test_end - w.test_start) == pd.Timedelta(days=60)
        assert w.selection_end == w.test_start  # selection grows to exactly where the next test begins


def test_test_windows_are_consecutive_and_never_overlap_their_own_selection_window():
    start = pd.Timestamp("2024-01-01")
    windows = compute_windows(start, start + pd.Timedelta(days=400))

    for w in windows:
        assert w.selection_end <= w.test_start  # selection strictly precedes its own test window
    for earlier, later in zip(windows, windows[1:]):
        assert earlier.test_end == later.test_start  # back-to-back, no gap, no overlap


def test_real_728_day_range_produces_nine_windows():
    start = pd.Timestamp("2024-09-15 23:00:00")
    end = start + pd.Timedelta(days=728)

    windows = compute_windows(start, end)

    assert len(windows) == 9


def test_no_windows_when_the_range_is_shorter_than_one_full_cycle():
    start = pd.Timestamp("2024-01-01")
    windows = compute_windows(start, start + pd.Timedelta(days=100))  # < 180 + 60
    assert windows == []


def _bounds(index, test_start_day, test_days=60):
    start = pd.Timestamp("2024-01-01") + pd.Timedelta(days=index * test_days)
    from tradebot.backtest.walk_forward import WindowBounds

    return WindowBounds(
        index=index,
        selection_start=pd.Timestamp("2024-01-01"),
        selection_end=pd.Timestamp("2024-01-01") + pd.Timedelta(days=test_start_day),
        test_start=pd.Timestamp("2024-01-01") + pd.Timedelta(days=test_start_day),
        test_end=pd.Timestamp("2024-01-01") + pd.Timedelta(days=test_start_day + test_days),
    )


def test_chain_equity_curve_compounds_each_windows_return_in_order():
    outcomes = [
        WindowOutcome(bounds=_bounds(0, 180), members=[], return_pct=10.0),  # +10%
        WindowOutcome(bounds=_bounds(1, 240), members=[], return_pct=-5.0),  # -5%
        WindowOutcome(bounds=_bounds(2, 300), members=[], return_pct=20.0),  # +20%
    ]
    curve = chain_equity_curve(outcomes)

    # a starting baseline point, then one point per window: 1.0 -> 1.10 -> 1.045 -> 1.254
    assert len(curve) == 4
    assert curve.iloc[0] == pytest.approx(1.0)
    assert curve.iloc[1] == pytest.approx(1.10)
    assert curve.iloc[2] == pytest.approx(1.045)
    assert curve.iloc[3] == pytest.approx(1.254)
    # indexed by real dates: the start point sits at the first window's test_start, not before it
    assert curve.index[0] == outcomes[0].bounds.test_start
    assert curve.index[-1] == outcomes[-1].bounds.test_end


def test_chain_equity_curve_handles_no_windows():
    curve = chain_equity_curve([])
    assert len(curve) == 1
    assert curve.iloc[0] == pytest.approx(1.0)


class _TrapCandidate:
    """Only ever signals long from `reveal_at` onward — a stand-in for a candidate that "happens to
    know" a specific stretch is profitable. If Selection ever picked this for the window whose test
    range starts at reveal_at, that would prove the selection saw data it shouldn't have."""

    name = "trap"
    timeframe = None  # set in the test, to match whatever Timeframe the synthetic data uses
    supporting_data: tuple = ()

    def __init__(self, reveal_at: pd.Timestamp, timeframe):
        self.reveal_at = reveal_at
        self.timeframe = timeframe

    def generate_signals(self, ohlcv, supporting=None):
        return pd.Series(np.where(ohlcv.index >= self.reveal_at, 1.0, 0.0), index=ohlcv.index)


def test_a_candidate_that_only_profits_in_one_test_window_is_never_chosen_for_that_window():
    from tradebot.backtest.engine import BacktestEngine
    from tradebot.risk.risk_controls import RiskControls
    from tradebot.timeframe import Timeframe

    # small, fast windows: selection=3 days, test=2 days, over 15 days of hourly bars
    index = pd.date_range("2024-01-01", periods=15 * 24, freq="h")
    rng = np.random.default_rng(0)
    close = 100 + np.cumsum(rng.normal(0, 0.05, size=len(index)))
    ohlcv = pd.DataFrame({"open": close, "high": close + 0.2, "low": close - 0.2, "close": close}, index=index)

    windows = compute_windows(index[0], index[-1], selection_days=3, test_days=2)
    target_window = windows[2]  # some window in the middle, not the first or last
    trap = _TrapCandidate(reveal_at=target_window.test_start, timeframe=Timeframe.H1)

    engine = BacktestEngine(risk_controls=RiskControls())
    from tradebot.strategies.base import DataRequirement

    result = run_walk_forward([trap], {DataRequirement(timeframe=Timeframe.H1): ohlcv}, engine, selection_days=3, test_days=2)

    chosen_names_for_target_window = {m.candidate_name for m in result.windows[2].members}
    assert "trap" not in chosen_names_for_target_window

    # sanity: earlier windows (whose selection ends even earlier) also never see it
    for outcome in result.windows[:2]:
        assert "trap" not in {m.candidate_name for m in outcome.members}
