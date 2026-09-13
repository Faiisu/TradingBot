import json
from dataclasses import asdict, dataclass
from pathlib import Path

from tradebot.backtest.result import BacktestResult
from tradebot.metrics.performance import ENSEMBLE_METRIC_THRESHOLD, performance_metric


@dataclass(frozen=True)
class EnsembleMember:
    candidate_name: str
    timeframe: str
    performance_metric: float
    capital_fraction: float


@dataclass(frozen=True)
class Ensemble:
    members: list[EnsembleMember]


def select_ensemble(results: list[BacktestResult], threshold: float = ENSEMBLE_METRIC_THRESHOLD) -> Ensemble:
    qualifying = [
        (result, performance_metric(result.equity_curve))
        for result in results
        if performance_metric(result.equity_curve) > threshold
    ]
    if not qualifying:
        return Ensemble(members=[])

    capital_fraction = 1.0 / len(qualifying)
    members = [
        EnsembleMember(
            candidate_name=result.candidate_name,
            timeframe=result.timeframe,
            performance_metric=metric,
            capital_fraction=capital_fraction,
        )
        for result, metric in qualifying
    ]
    return Ensemble(members=members)


def save_ensemble(ensemble: Ensemble, path: Path) -> None:
    path.write_text(json.dumps({"members": [asdict(m) for m in ensemble.members]}, indent=2))


def load_ensemble(path: Path) -> Ensemble:
    data = json.loads(path.read_text())
    return Ensemble(members=[EnsembleMember(**m) for m in data["members"]])
