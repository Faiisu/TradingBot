import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from tradebot.backtest.result import BacktestResult
from tradebot.backtest.walk_forward import WalkForwardResult
from tradebot.metrics.drawdown import max_drawdown_pct
from tradebot.metrics.performance import ENSEMBLE_METRIC_THRESHOLD, performance_metric, total_return_pct
from tradebot.strategies.base import StrategyCandidate


def _serialize_walk_forward(walk_forward: WalkForwardResult | None) -> dict | None:
    if walk_forward is None:
        return None
    return {
        "passed": walk_forward.passed,
        "performance_metric": walk_forward.performance_metric,
        "equity_curve": [
            {"date": str(date), "equity": float(equity)} for date, equity in walk_forward.equity_curve.items()
        ],
        "windows": [
            {
                "index": outcome.bounds.index,
                "selection_start": str(outcome.bounds.selection_start),
                "selection_end": str(outcome.bounds.selection_end),
                "test_start": str(outcome.bounds.test_start),
                "test_end": str(outcome.bounds.test_end),
                "return_pct": outcome.return_pct,
                "members": [
                    {
                        "candidate_name": member.candidate_name,
                        "timeframe": member.timeframe,
                        "performance_metric": member.performance_metric,
                        "capital_fraction": member.capital_fraction,
                    }
                    for member in outcome.members
                ],
            }
            for outcome in walk_forward.windows
        ],
    }


def save_backtest_results(
    candidates_and_results: list[tuple[StrategyCandidate, BacktestResult]],
    path: Path,
    window_start: pd.Timestamp | None = None,
    window_end: pd.Timestamp | None = None,
    walk_forward: WalkForwardResult | None = None,
) -> None:
    """The single source of truth for backtest output: one run, one save. Consumed by the dashboard's
    /api/backtest route (src/tradebot/dashboard/server.py) — nothing re-runs the backtest to display it."""
    candidates = []
    for candidate, result in candidates_and_results:
        filter_timeframe = getattr(candidate, "filter_timeframe", None)
        metric = performance_metric(result.equity_curve)
        candidates.append(
            {
                "candidate_name": result.candidate_name,
                "timeframe": result.timeframe,
                "filter_name": getattr(candidate, "filter_name", None),
                "filter_timeframe": filter_timeframe.value if filter_timeframe else None,
                "trade_count": len(result.trades),
                "return_pct": total_return_pct(result.equity_curve),
                "max_drawdown_pct": max_drawdown_pct(result.equity_curve),
                "performance_metric": metric,
                "in_ensemble": metric > ENSEMBLE_METRIC_THRESHOLD,
                "trades": [
                    {
                        "direction": t.direction,
                        "entry_time": str(t.entry_time),
                        "exit_time": str(t.exit_time),
                        "entry_price": round(t.entry_price, 3),
                        "exit_price": round(t.exit_price, 3),
                        "pnl_pct": round(t.pnl_pct * 100, 4),
                        "exit_reason": t.exit_reason,
                    }
                    for t in result.trades
                ],
            }
        )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_start": str(window_start) if window_start is not None else None,
        "window_end": str(window_end) if window_end is not None else None,
        "candidates": candidates,
        "walk_forward": _serialize_walk_forward(walk_forward),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def load_backtest_results(path: Path) -> dict:
    return json.loads(path.read_text())


def save_walk_forward_verdict(walk_forward: WalkForwardResult, path: Path) -> None:
    """A small side file so the Paper Trading page's status poll (every 1-4s) never has to parse the
    much larger backtest_results.json just to show the latest verdict — mirrors ensemble.json."""
    payload = {
        "passed": walk_forward.passed,
        "performance_metric": walk_forward.performance_metric,
        "window_count": len(walk_forward.windows),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def load_walk_forward_verdict(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())
