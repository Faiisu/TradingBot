"""Run every Strategy Candidate through the Backtest engine, rank by Performance Metric, and print the resulting Ensemble.

Uses real cached historical data from data/cache/ if fetch_history.py has been run; otherwise falls back to a
synthetic random-walk price series per timeframe, purely to validate the pipeline end-to-end before MT5 is involved.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tradebot.backtest.engine import BacktestEngine
from tradebot.backtest.persistence import save_backtest_results
from tradebot.backtest.result import BacktestResult
from tradebot.ensemble.selection import save_ensemble, select_ensemble
from tradebot.metrics.drawdown import max_drawdown_pct
from tradebot.metrics.performance import performance_metric, total_return_pct
from tradebot.risk.risk_controls import RiskControls
from tradebot.strategies.registry import TIMEFRAMES, build_candidates
from tradebot.timeframe import Timeframe

SYMBOL = "XAUUSDm"  # this Exness demo server suffixes gold with "m"; confirmed via symbols_get()
CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"

BARS_PER_YEAR = {Timeframe.H1: 6000, Timeframe.M30: 12000, Timeframe.M15: 24000, Timeframe.M5: 72000}
NUM_YEARS = 2


def _synthetic_ohlcv(timeframe: Timeframe, seed: int = 42) -> pd.DataFrame:
    num_bars = BARS_PER_YEAR[timeframe] * NUM_YEARS
    rng = np.random.default_rng(seed)
    log_returns = rng.normal(loc=0.0, scale=0.0015, size=num_bars)
    close = 2400.0 * np.exp(np.cumsum(log_returns))
    noise = rng.uniform(0.0, 0.0015, size=num_bars) * close
    high = close + noise
    low = close - noise
    freq = {Timeframe.H1: "h", Timeframe.M30: "30min", Timeframe.M15: "15min", Timeframe.M5: "5min"}[timeframe]
    index = pd.date_range("2024-01-01", periods=num_bars, freq=freq)
    return pd.DataFrame({"open": close, "high": high, "low": low, "close": close}, index=index)


def load_ohlcv(timeframe: Timeframe) -> pd.DataFrame:
    cache_path = CACHE_DIR / f"{SYMBOL}_{timeframe.value}.parquet"
    if cache_path.exists():
        return pd.read_parquet(cache_path)
    print(f"[{timeframe.value}] no cached data at {cache_path}, using synthetic data for pipeline validation")
    return _synthetic_ohlcv(timeframe)


def trim_to_common_window(ohlcv_by_timeframe: dict[Timeframe, pd.DataFrame]) -> dict[Timeframe, pd.DataFrame]:
    """Trims every timeframe's data to the same start date, so all candidates are compared over
    identical market conditions rather than some getting a longer history than others (M5's broker
    retention is shorter than H1/M30/M15's, so it was previously the limiting factor)."""
    common_start = max(df.index.min() for df in ohlcv_by_timeframe.values())
    print(f"Trimming all timeframes to a common window starting {common_start} (the shortest available history)")
    return {tf: df.loc[df.index >= common_start] for tf, df in ohlcv_by_timeframe.items()}


def run() -> None:
    # swap_long_points/swap_short_points/point_value fetched live from MT5's symbol_info("XAUUSDm")
    # on the connected Exness demo account. Real swap rates drift over time and should be re-checked
    # periodically rather than trusted indefinitely.
    risk_controls = RiskControls(swap_long_points=-534.9, swap_short_points=0.0, point_value=0.001)
    engine = BacktestEngine(risk_controls=risk_controls)

    ohlcv_by_timeframe = trim_to_common_window({tf: load_ohlcv(tf) for tf in TIMEFRAMES})

    candidates_and_results: list[tuple] = []
    for candidate in build_candidates():
        ohlcv = ohlcv_by_timeframe[candidate.timeframe]
        htf_ohlcv = ohlcv_by_timeframe.get(getattr(candidate, "filter_timeframe", None))
        candidates_and_results.append((candidate, engine.run(candidate, ohlcv, htf_ohlcv)))

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
