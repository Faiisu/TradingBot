import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from tradebot.backtest.result import BacktestResult
from tradebot.metrics.drawdown import max_drawdown_pct
from tradebot.metrics.performance import ENSEMBLE_METRIC_THRESHOLD, performance_metric, total_return_pct
from tradebot.strategies.base import StrategyCandidate


def save_backtest_results(
    candidates_and_results: list[tuple[StrategyCandidate, BacktestResult]],
    path: Path,
    window_start: pd.Timestamp | None = None,
    window_end: pd.Timestamp | None = None,
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
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload))


def load_backtest_results(path: Path) -> dict:
    return json.loads(path.read_text())
