"""Does the Rule Set add anything beyond the shared exit machinery + gold's 2024-26 drift?

For each target candidate: run the real engine on (1) the real signal, (2) random signals with the same
flip frequency (N seeds), Also split the real trades by direction and by year.
"""
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\projects\TradeBot\src")
from tradebot.backtest.engine import BacktestEngine
from tradebot.data.cache import load_ohlcv
from tradebot.metrics.drawdown import max_drawdown_pct
from tradebot.metrics.performance import performance_metric, total_return_pct
from tradebot.risk.risk_controls import RiskControls
from tradebot.strategies.registry import build_candidates
from tradebot.timeframe import Timeframe

CACHE = Path(r"C:\projects\TradeBot\data\cache")
RC = RiskControls(swap_long_points=-534.9, swap_short_points=0.0, point_value=0.001,
                  trailing_stop_multiplier=2.0, profit_target_r_multiple=3.0)
ENGINE = BacktestEngine(risk_controls=RC)


class Fixed:
    def __init__(self, name, tf, sig):
        self.name, self.timeframe, self._sig = name, tf, sig
        self.supporting_data = ()

    def generate_signals(self, ohlcv, supporting=None):
        return pd.Series(self._sig, index=ohlcv.index)


def random_signal(n, flips_per_bar, rng):
    sig = np.empty(n)
    cur = rng.choice([-1.0, 1.0])
    for i in range(n):
        if rng.random() < flips_per_bar:
            cur = -cur
        sig[i] = cur
    return sig


def stats(res):
    eq = res.equity_curve
    return len(res.trades), total_return_pct(eq), max_drawdown_pct(eq), performance_metric(eq)


start, end = pd.Timestamp("2024-09-15 23:00:00"), pd.Timestamp("2026-09-14 03:00:00")
data = {tf: load_ohlcv(tf, cache_dir=CACHE).loc[start:end] for tf in (Timeframe.M5, Timeframe.H1)}
first, last = data[Timeframe.H1]["close"].iloc[0], data[Timeframe.H1]["close"].iloc[-1]
print(f"gold {first:.0f} -> {last:.0f} ({(last / first - 1) * 100:+.1f}%) over the window")

targets = {("macd_12_26_9", "M5"), ("macd_12_26_9", "H1"), ("donchian_breakout_20_10", "H1"), ("bollinger_breakout_20_2.0", "M5")}
rng = np.random.default_rng(7)
for cand in build_candidates():
    key = (cand.name, cand.timeframe.value)
    if key not in targets or getattr(cand, "supporting_data", ()):
        continue
    df = data[cand.timeframe]
    real_sig = cand.generate_signals(df, None).to_numpy()
    flips = np.count_nonzero(np.diff(real_sig) != 0) / len(real_sig)
    real = ENGINE.run(cand, df)
    n, ret, dd, pm = stats(real)
    print(f"\n== {cand.name} {cand.timeframe.value}  flip rate {flips:.4f}/bar")
    print(f"  REAL        trades={n:6d} ret={ret:8.1f}% dd={dd:5.2f}% PM={pm:8.2f}")

    by_dir = defaultdict(float)
    by_year = defaultdict(float)
    for t in real.trades:
        by_dir["long" if t.direction == 1 else "short"] += t.pnl_pct * 100
        by_year[(t.exit_time.year, "long" if t.direction == 1 else "short")] += t.pnl_pct * 100
    print("  simple-sum pnl by direction:", {k: round(v, 1) for k, v in by_dir.items()})
    print("  by (year,dir):", {k: round(v, 1) for k, v in sorted(by_year.items())})

    pms, rets = [], []
    for s in range(6 if cand.timeframe == Timeframe.M5 else 20):
        r = ENGINE.run(Fixed("rand", cand.timeframe, random_signal(len(df), flips, rng)), df)
        _, rr, _, pp = stats(r)
        pms.append(pp)
        rets.append(rr)
    print(f"  RANDOM x{len(pms)}   ret mean={np.mean(rets):7.1f}% [min {np.min(rets):.1f}, max {np.max(rets):.1f}]  PM mean={np.mean(pms):7.2f} [min {np.min(pms):.2f}, max {np.max(pms):.2f}]")
