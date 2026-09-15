"""Measure how much each fill-realism assumption inflates backtest results.

Variants (cumulative):
  A baseline   - replicates BacktestEngine exactly
  B no_prehigh - trailing extreme starts at entry price, not the entry bar's high/low (which printed before the close entry)
  C gap_fill   - a stop/target is filled at the bar's open when the bar opens beyond it
  D next_open  - entries happen at the next bar's open (signal known only after close)
  E slip       - D + 0.10 extra slippage on every stop exit
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, r"C:\projects\TradeBot\src")
from tradebot.backtest.engine import _find_segments
from tradebot.data.cache import load_ohlcv
from tradebot.indicators import atr
from tradebot.metrics.drawdown import max_drawdown_pct
from tradebot.risk.risk_controls import RiskControls
from tradebot.strategies.registry import build_candidates
from tradebot.timeframe import Timeframe

CACHE = Path(r"C:\projects\TradeBot\data\cache")
RC = RiskControls(swap_long_points=-534.9, swap_short_points=0.0, point_value=0.001,
                  trailing_stop_multiplier=2.0, profit_target_r_multiple=3.0)


def run(signal, df, prehigh=True, gap=False, next_open=False, slip=0.0):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    a = atr(df["high"], df["low"], df["close"], 14).to_numpy()
    idx = df.index
    n = len(c)
    pnls, exit_times = [], []
    for start, end, d in _find_segments(signal):
        e = start
        while e <= end:
            if next_open:
                if e + 1 >= n:
                    break
                ep, first_bar = o[e + 1], e + 1
            else:
                ep, first_bar = c[e], e + 1
            av = a[e]
            if np.isnan(ep) or np.isnan(av):
                break
            stop = RC.stop_price(ep, av, d)
            tgt = RC.profit_target_price(ep, av, d)
            last = min(end + (1 if next_open else 0), n - 1)
            xi, xp, reason = last, (o[last] if next_open else c[end]), "signal_change"
            cur = stop
            if next_open:
                ext = ep
                scan_from = first_bar
            else:
                ext = (h[e] if d == 1 else l[e]) if prehigh else ep
                scan_from = first_bar
            for i in range(scan_from, last + (0 if next_open else 1)):
                tr = RC.trailing_stop_price(ep, av, d, ext)
                cur = max(cur, tr) if d == 1 else min(cur, tr)
                stop_hit = (d == 1 and l[i] <= cur) or (d == -1 and h[i] >= cur)
                tgt_hit = (d == 1 and h[i] >= tgt) or (d == -1 and l[i] <= tgt)
                if stop_hit:
                    fill = cur
                    if gap and ((d == 1 and o[i] < cur) or (d == -1 and o[i] > cur)):
                        fill = o[i]
                    xi, xp, reason = i, fill - d * slip, "stop"
                    break
                if tgt_hit:
                    fill = tgt
                    if gap and ((d == 1 and o[i] > tgt) or (d == -1 and o[i] < tgt)):
                        fill = o[i]
                    xi, xp, reason = i, fill, "target"
                    break
                ext = max(ext, h[i]) if d == 1 else min(ext, l[i])
            pf = RC.position_fraction(ep, av)
            cost = RC.cost_pct(ep) * pf
            swap = RC.swap_pct(ep, d, idx[e], idx[xi]) * pf
            pnls.append(d * (xp / ep - 1) * pf - cost + swap)
            exit_times.append(idx[xi])
            if reason == "signal_change":
                break
            e = xi if not next_open else xi  # re-enter decision at the exit bar, filled next open
    eq = pd.Series(1.0, index=idx, dtype=float)
    s = pd.Series(np.cumprod(1 + np.array(pnls)), index=pd.DatetimeIndex(exit_times)) if pnls else pd.Series(dtype=float)
    s = s.groupby(level=0).last()
    eq = s.reindex(idx).ffill().fillna(1.0)
    ret = (eq.iloc[-1] - 1) * 100
    dd = max_drawdown_pct(eq)
    wins = sum(p > 0 for p in pnls)
    return len(pnls), ret, dd, ret / max(dd, 0.01), wins / max(len(pnls), 1)


targets = {("macd_12_26_9", "M5"), ("bollinger_breakout_20_2.0", "M5"), ("macd_12_26_9", "H1"),
           ("donchian_breakout_20_10", "H1"), ("supertrend_10_3.0", "H1"), ("ma_crossover_20_50", "H1")}
data = {tf: load_ohlcv(tf, cache_dir=CACHE) for tf in (Timeframe.M5, Timeframe.H1)}
start = pd.Timestamp("2024-09-15 23:00:00")
end = pd.Timestamp("2026-09-14 03:00:00")
data = {tf: df.loc[start:end] for tf, df in data.items()}

variants = [
    ("A baseline", dict()),
    ("B no_prehigh", dict(prehigh=False)),
    ("C +gap_fill", dict(prehigh=False, gap=True)),
    ("D +next_open", dict(prehigh=False, gap=True, next_open=True)),
    ("E +slip0.10", dict(prehigh=False, gap=True, next_open=True, slip=0.10)),
]
for cand in build_candidates():
    key = (cand.name, cand.timeframe.value)
    if key not in targets or getattr(cand, "supporting_data", ()):
        continue
    df = data[cand.timeframe]
    sig = cand.generate_signals(df, None).to_numpy()
    print(f"\n{cand.name} {cand.timeframe.value}")
    for label, kw in variants:
        n, ret, dd, pm, wr = run(sig, df, **kw)
        print(f"  {label:14s} trades={n:6d} ret={ret:8.1f}% dd={dd:6.2f}% PM={pm:8.2f} win={wr:.2f}")
