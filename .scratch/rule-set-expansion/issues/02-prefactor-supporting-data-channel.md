# 02: Prefactor — one way for candidates to receive supporting data

**What to build:** Make the upcoming changes easy before making them. Today a Strategy Candidate can only receive one kind of extra data: gold on a higher Timeframe, for a Trend Filter. Market Filters will also need Reference Market data (DXY, silver, US 10Y real yield). Give every candidate one general way to receive whatever supporting data it declares it needs, and move history loading plus common-window trimming out of the backtest script into shared code, so that Walk-Forward Validation and Paper Trading can reuse them. No behavior changes.

**Blocked by:** 01 — Backtest on the full two-year history (so the before/after comparison below runs on the final dataset)

**Status:** done

- [x] Every Strategy Candidate shape receives supporting data through the same channel; nothing is specific to "higher-timeframe gold" anymore
- [x] A candidate declares which supporting data it needs; the Backtest and the Paper Trading loop supply exactly that
- [x] Loading cached history and trimming to the common window live in shared code, not in the backtest script
- [x] A Backtest run before and after this change produces identical results: same candidates, same trades, same Performance Metric for every candidate
- [x] The Paper Trading loop still starts and processes bars for MTF Candidates
- [x] The test suite stays green

## Answer

`StrategyCandidate` gained `supporting_data: tuple[DataRequirement, ...]` (empty for plain candidates) and `generate_signals(ohlcv, supporting: dict[DataRequirement, pd.DataFrame] | None)`. `DataRequirement(timeframe, reference_market=None)` names one feed — `reference_market=None` means "the traded instrument itself" (what `MtfCandidate`'s Trend Filter needs today); a label like `"DXY"` is what a Market Filter will need later, and resolving one raises `NotImplementedError` for now (tickets 07-09). `resolve_supporting_data()` (Backtest/Walk-Forward) and `update_member()` (Paper Trading) both turn a candidate's declared requirements into that dict — no code still special-cases "higher-timeframe gold". `trim_to_common_window` moved from the script into `data/cache.py`, generically keyed so Market Filter data can share it too.

**Equivalence, checked directly rather than assumed:** saved the pre-refactor `backtest_results.json` (29 candidates, real 728-day data), re-ran the full Backtest through the new code path, and diffed every field plus every trade for all 29 candidates — trade_count, return_pct, max_drawdown_pct, performance_metric, in_ensemble, and the full trade list were all identical. Also added a paper-trading test (`test_update_member_fetches_and_passes_through_declared_supporting_data`) proving `update_member` fetches every declared requirement's Timeframe from MT5 and passes it through, not just the candidate's own Timeframe — the MTF criterion wasn't previously covered by any test. Full suite: 112/112.
