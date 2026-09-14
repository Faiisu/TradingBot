"""Run every Strategy Candidate through the Backtest engine, rank by Performance Metric, and print the resulting Ensemble.

Reads OHLCV data from the local parquet cache (data/cache/).  If the cache is empty, run
``python scripts/fetch_history.py`` first to pull history from the MT5 demo account.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tradebot.backtest.engine import BacktestEngine
from tradebot.backtest.persistence import save_backtest_results
from tradebot.backtest.result import BacktestResult
from tradebot.data.cache import load_ohlcv, trim_to_common_window
from tradebot.ensemble.selection import save_ensemble, select_ensemble
from tradebot.metrics.drawdown import max_drawdown_pct
from tradebot.metrics.performance import performance_metric, total_return_pct
from tradebot.risk.risk_controls import RiskControls
from tradebot.strategies.base import resolve_supporting_data
from tradebot.strategies.registry import TIMEFRAMES, build_candidates

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"


def run() -> None:
    # swap_long_points/swap_short_points/point_value fetched live from MT5's symbol_info("XAUUSDm")
    # on the connected Exness demo account. Real swap rates drift over time and should be re-checked
    # periodically rather than trusted indefinitely.
    risk_controls = RiskControls(swap_long_points=-534.9, swap_short_points=0.0, point_value=0.001)
    engine = BacktestEngine(risk_controls=risk_controls)

    ohlcv_by_timeframe = trim_to_common_window({tf: load_ohlcv(tf, cache_dir=CACHE_DIR) for tf in TIMEFRAMES})

    candidates_and_results: list[tuple] = []
    for candidate in build_candidates():
        ohlcv = ohlcv_by_timeframe[candidate.timeframe]
        supporting = resolve_supporting_data(candidate, ohlcv_by_timeframe)
        candidates_and_results.append((candidate, engine.run(candidate, ohlcv, supporting)))

    results: list[BacktestResult] = [r for _, r in candidates_and_results]
    ranked = sorted(results, key=lambda r: performance_metric(r.equity_curve), reverse=True)

    print(f"\nrisk controls: {risk_controls}")
    print(f"\n{'candidate':<30} {'timeframe':<6} {'trades':>7} {'return %':>10} {'max dd %':>10} {'metric':>8}")
    for result in ranked:
        print(
            f"{result.candidate_name:<30} {result.timeframe:<6} {len(result.trades):>7} "
            f"{total_return_pct(result.equity_curve):>10.2f} {max_drawdown_pct(result.equity_curve):>10.2f} "
            f"{performance_metric(result.equity_curve):>8.2f}"
        )

    ensemble = select_ensemble(results)
    print(f"\nEnsemble: {len(ensemble.members)} member(s), equal capital split")
    for member in ensemble.members:
        print(
            f"  {member.candidate_name} ({member.timeframe}): metric={member.performance_metric:.2f}, "
            f"capital_fraction={member.capital_fraction:.2%}"
        )

    ensemble_path = CACHE_DIR.parent / "ensemble.json"
    save_ensemble(ensemble, ensemble_path)
    print(f"\nEnsemble saved to {ensemble_path} (used by scripts/run_paper_trading.py)")

    results_path = CACHE_DIR.parent / "backtest_results.json"
    window_start = max(df.index.min() for df in ohlcv_by_timeframe.values())
    window_end = min(df.index.max() for df in ohlcv_by_timeframe.values())
    save_backtest_results(candidates_and_results, results_path, window_start, window_end)
    print(f"Full results (incl. trade-by-trade history) saved to {results_path} (used by the dashboard's /backtest page)")


if __name__ == "__main__":
    run()
