# 03: Run backtest against real data and sanity-check results

**What to build:** `scripts/run_backtest.py` run against real cached data, ranked results reviewed for plausibility. On synthetic data this surfaced runaway compounding (millions-of-percent returns) from 5x leverage over thousands of trades (see ticket 04) — this ticket's job is to check whether that reappears on real data, not to assume the fix from ticket 04 is sufficient.

**Blocked by:** 02

**Status:** done — plausibility check failed, root-caused, partially fixed; full fix deferred to ticket 06

- [x] `run_backtest.py` runs against real cached parquet data
- [x] Results reviewed; returns/drawdowns look like plausible trading outcomes, not compounding artifacts — **failed** on first real-data run (see Answer), improved but not fully resolved after the fix
- [x] `data/ensemble.json` reflects real-data results

## Answer

First real-data run (728-day common window): `macd_12_26_9` on M5 showed **+57,042% return at 2.09% max drawdown** over 11,862 trades — not plausible. Root-caused in ticket 04: `max_position_fraction` was capping position size on 83–99.5% of trades (worse on finer Timeframes), which made realized stop-loss size much smaller than the intended 1% risk almost all the time, while signal-change exits stayed unbounded — a structural asymmetry, not a data bug.

Applied the first half of the fix (lower `max_position_fraction` to 0.2): `macd_12_26_9` on M5 now shows **+260.55% return at 0.64% max drawdown**, a 223x reduction, with stop-losses (mean -0.045%) and winning trades (mean +0.050%) much closer to symmetric. Real improvement, but still smoother than real trading would be — bounding the winning side too (a trailing stop/profit target) is deferred to ticket 06, by agreement with the user ("A now, B later").
