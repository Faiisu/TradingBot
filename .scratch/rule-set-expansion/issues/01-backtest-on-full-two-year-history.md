# 01: Backtest on the full two-year history

**What to build:** Now that the MT5 terminal's bar cap is lifted, re-fetch every gold Timeframe so all of them cover the same ~728 days, then re-run the Backtest. Until now M5 was cut to 100,000 bars (~514 days), and that cut shortened the common window for every candidate. After this ticket the Backtest page shows results over the full window (2024-09 → 2026-09).

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] MT5 terminal reports an unlimited (or ≥ 10M) max-bars setting before fetching
- [ ] Cached H1, M30, M15 and M5 gold history each cover ~728 days; the coverage report shows no shortfall warning for any of them
- [ ] The Backtest runs on the common window, which now starts around 2024-09 instead of 2025-04
- [ ] The Backtest page's run info shows the new data window
- [ ] The test suite stays green
