# 02: Prefactor — one way for candidates to receive supporting data

**What to build:** Make the upcoming changes easy before making them. Today a Strategy Candidate can only receive one kind of extra data: gold on a higher Timeframe, for a Trend Filter. Market Filters will also need Reference Market data (DXY, silver, US 10Y real yield). Give every candidate one general way to receive whatever supporting data it declares it needs, and move history loading plus common-window trimming out of the backtest script into shared code, so that Walk-Forward Validation and Paper Trading can reuse them. No behavior changes.

**Blocked by:** 01 — Backtest on the full two-year history (so the before/after comparison below runs on the final dataset)

**Status:** ready-for-agent

- [ ] Every Strategy Candidate shape receives supporting data through the same channel; nothing is specific to "higher-timeframe gold" anymore
- [ ] A candidate declares which supporting data it needs; the Backtest and the Paper Trading loop supply exactly that
- [ ] Loading cached history and trimming to the common window live in shared code, not in the backtest script
- [ ] A Backtest run before and after this change produces identical results: same candidates, same trades, same Performance Metric for every candidate
- [ ] The Paper Trading loop still starts and processes bars for MTF Candidates
- [ ] The test suite stays green
