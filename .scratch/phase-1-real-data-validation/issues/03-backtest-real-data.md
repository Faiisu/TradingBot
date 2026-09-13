# 03: Run backtest against real data and sanity-check results

**What to build:** `scripts/run_backtest.py` run against real cached data, ranked results reviewed for plausibility. On synthetic data this surfaced runaway compounding (millions-of-percent returns) from 5x leverage over thousands of trades (see ticket 04) — this ticket's job is to check whether that reappears on real data, not to assume the fix from ticket 04 is sufficient.

**Blocked by:** 02

**Status:** ready-for-agent (once 02 is done)

- [ ] `run_backtest.py` runs against real cached parquet data
- [ ] Results reviewed; returns/drawdowns look like plausible trading outcomes, not compounding artifacts
- [ ] `data/ensemble.json` reflects real-data results
