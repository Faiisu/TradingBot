from dataclasses import dataclass

import pandas as pd

from tradebot.backtest.engine import BacktestEngine
from tradebot.ensemble.selection import EnsembleMember, select_ensemble
from tradebot.metrics.performance import ENSEMBLE_METRIC_THRESHOLD, performance_metric, total_return_pct
from tradebot.strategies.base import StrategyCandidate, resolve_supporting_data
from tradebot.timeframe import Timeframe

DEFAULT_SELECTION_DAYS = 180
DEFAULT_TEST_DAYS = 60


@dataclass(frozen=True)
class WindowBounds:
    index: int
    selection_start: pd.Timestamp
    selection_end: pd.Timestamp  # exclusive; always equals test_start
    test_start: pd.Timestamp  # inclusive
    test_end: pd.Timestamp  # exclusive


def compute_windows(
    start: pd.Timestamp,
    end: pd.Timestamp,
    selection_days: int = DEFAULT_SELECTION_DAYS,
    test_days: int = DEFAULT_TEST_DAYS,
) -> list[WindowBounds]:
    """Anchored walk-forward window boundaries (see Walk-Forward Validation, Selection Window, Test
    Window in CONTEXT.md, and ADR 0002): the Selection Window always starts at `start` and grows;
    Test Windows are consecutive, fixed-length, and never overlap the Selection Window that chose
    their Ensemble. Only full test_days-length windows are produced — a shorter trailing remainder is
    dropped rather than judged on a partial window."""
    windows: list[WindowBounds] = []
    boundary = start + pd.Timedelta(days=selection_days)
    index = 0
    while boundary + pd.Timedelta(days=test_days) <= end:
        test_start = boundary
        test_end = test_start + pd.Timedelta(days=test_days)
        windows.append(
            WindowBounds(index=index, selection_start=start, selection_end=test_start, test_start=test_start, test_end=test_end)
        )
        boundary = test_end
        index += 1
    return windows


@dataclass(frozen=True)
class WindowOutcome:
    bounds: WindowBounds
    members: list[EnsembleMember]  # the Ensemble chosen from this window's Selection Window
    return_pct: float  # this window's combined equal-weight return, in percent


@dataclass(frozen=True)
class WalkForwardResult:
    windows: list[WindowOutcome]
    equity_curve: pd.Series  # the joined out-of-sample record: chained, compounded window returns
    performance_metric: float
    passed: bool  # performance_metric > ENSEMBLE_METRIC_THRESHOLD


def chain_equity_curve(outcomes: list[WindowOutcome], initial_equity: float = 1.0) -> pd.Series:
    """The out-of-sample record: each Test Window's return compounded onto the last, joined end to
    end (see CONTEXT.md's Walk-Forward Validation entry). A single point at `initial_equity` when
    there are no windows to chain, so callers never have to special-case an empty curve."""
    if not outcomes:
        return pd.Series([initial_equity], index=[pd.Timestamp.now()])

    index = [outcomes[0].bounds.test_start]
    values = [initial_equity]
    equity = initial_equity
    for outcome in outcomes:
        equity *= 1 + outcome.return_pct / 100
        index.append(outcome.bounds.test_end)
        values.append(equity)
    return pd.Series(values, index=pd.DatetimeIndex(index))


def _slice_window(data: dict[Timeframe, pd.DataFrame], start: pd.Timestamp, end: pd.Timestamp) -> dict[Timeframe, pd.DataFrame]:
    return {key: df.loc[(df.index >= start) & (df.index < end)] for key, df in data.items()}


def _run_on_slice(engine: BacktestEngine, candidate: StrategyCandidate, data_slice: dict[Timeframe, pd.DataFrame]):
    """Runs one Candidate on one windowed slice of data, or None if the slice has nothing for its
    Entry Timeframe (an edge window can be too short to contain any bars for a given timeframe)."""
    ohlcv = data_slice.get(candidate.timeframe)
    if ohlcv is None or ohlcv.empty:
        return None
    supporting = resolve_supporting_data(candidate, data_slice)
    return engine.run(candidate, ohlcv, supporting)


def run_walk_forward(
    candidates: list[StrategyCandidate],
    ohlcv_by_timeframe: dict[Timeframe, pd.DataFrame],
    engine: BacktestEngine,
    selection_days: int = DEFAULT_SELECTION_DAYS,
    test_days: int = DEFAULT_TEST_DAYS,
) -> WalkForwardResult:
    """Judges the Ensemble selection rule out of sample (ADR 0002): for each anchored window, choose
    an Ensemble using only its Selection Window, then score that same Ensemble on the Test Window that
    follows — a Test Window's own data is never part of the choice made for it."""
    common_start = max(df.index.min() for df in ohlcv_by_timeframe.values())
    common_end = min(df.index.max() for df in ohlcv_by_timeframe.values())
    # Keyed by each candidate's own name (not candidate_rule_set_key's base-strategy name), because an
    # EnsembleMember names the exact candidate chosen — the unfiltered strategy and each of its
    # Market-Filtered variants must resolve back to their own, distinct candidate here.
    candidates_by_key = {(c.name, c.timeframe.value): c for c in candidates}

    outcomes: list[WindowOutcome] = []
    for bounds in compute_windows(common_start, common_end, selection_days, test_days):
        selection_data = _slice_window(ohlcv_by_timeframe, bounds.selection_start, bounds.selection_end)
        candidates_and_selection_results = [
            (candidate, result)
            for candidate in candidates
            if (result := _run_on_slice(engine, candidate, selection_data)) is not None
        ]
        ensemble = select_ensemble(candidates_and_selection_results)

        test_data = _slice_window(ohlcv_by_timeframe, bounds.test_start, bounds.test_end)
        member_returns = [
            total_return_pct(result.equity_curve)
            for member in ensemble.members
            if (result := _run_on_slice(engine, candidates_by_key[(member.candidate_name, member.timeframe)], test_data)) is not None
        ]
        window_return = sum(member_returns) / len(member_returns) if member_returns else 0.0

        outcomes.append(WindowOutcome(bounds=bounds, members=ensemble.members, return_pct=window_return))

    equity_curve = chain_equity_curve(outcomes)
    metric = performance_metric(equity_curve) if outcomes else 0.0
    return WalkForwardResult(
        windows=outcomes,
        equity_curve=equity_curve,
        performance_metric=metric,
        passed=metric > ENSEMBLE_METRIC_THRESHOLD,
    )
