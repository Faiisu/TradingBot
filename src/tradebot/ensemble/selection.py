import json
from dataclasses import asdict, dataclass
from pathlib import Path

from tradebot.backtest.result import BacktestResult
from tradebot.metrics.performance import ENSEMBLE_METRIC_THRESHOLD, performance_metric
from tradebot.strategies.base import StrategyCandidate, candidate_rule_set_key


@dataclass(frozen=True)
class EnsembleMember:
    candidate_name: str
    timeframe: str
    performance_metric: float
    capital_fraction: float


@dataclass(frozen=True)
class Ensemble:
    members: list[EnsembleMember]


def select_ensemble(
    candidates_and_results: list[tuple[StrategyCandidate, BacktestResult]],
    threshold: float = ENSEMBLE_METRIC_THRESHOLD,
) -> Ensemble:
    """Every qualifying candidate (Performance Metric above threshold) joins the Ensemble, except that
    at most one member is admitted per (Rule Set, Entry Timeframe): among an unfiltered candidate and
    its Trend/Market-Filtered variants, only the best Performance Metric survives (see CONTEXT.md's
    Ensemble entry, and ADR 0002 — this same rule is what Walk-Forward Validation judges)."""
    scored = [(candidate, result, performance_metric(result.equity_curve)) for candidate, result in candidates_and_results]
    qualifying = [(candidate, result, metric) for candidate, result, metric in scored if metric > threshold]
    if not qualifying:
        return Ensemble(members=[])

    best_per_pair: dict[tuple[str, str], tuple] = {}
    for candidate, result, metric in qualifying:
        key = candidate_rule_set_key(candidate)
        if key not in best_per_pair or metric > best_per_pair[key][2]:
            best_per_pair[key] = (candidate, result, metric)

    selected = list(best_per_pair.values())
    capital_fraction = 1.0 / len(selected)
    members = [
        EnsembleMember(
            candidate_name=result.candidate_name,
            timeframe=result.timeframe,
            performance_metric=metric,
            capital_fraction=capital_fraction,
        )
        for _candidate, result, metric in selected
    ]
    return Ensemble(members=members)


def save_ensemble(ensemble: Ensemble, path: Path) -> None:
    path.write_text(json.dumps({"members": [asdict(m) for m in ensemble.members]}, indent=2))


def load_ensemble(path: Path) -> Ensemble:
    data = json.loads(path.read_text())
    return Ensemble(members=[EnsembleMember(**m) for m in data["members"]])
