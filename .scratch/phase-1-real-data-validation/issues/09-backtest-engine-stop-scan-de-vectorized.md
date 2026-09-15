# 09: Backtest engine's stop-scan is de-vectorized even when trailing/target are disabled

**What to build:** Restore vectorized (numpy) performance for the common case — `trailing_stop_multiplier=None` and `profit_target_r_multiple=None`, still `RiskControls`' default — while keeping the bar-by-bar loop (needed because the trailing level moves) for candidates that actually enable a trailing stop or profit target.

Found during code review of ticket 01. Ticket 06's uncommitted work replaced `BacktestEngine.run()`'s vectorized stop-scan (a single `low <= stop` mask plus `np.argmax`) with a bar-by-bar Python `for` loop that calls two `RiskControls` methods every bar of every re-entry segment — even when both `trailing_stop_multiplier` and `profit_target_r_multiple` are `None`, i.e. for every backtest that doesn't use ticket 06's new controls at all. Given the codebase's own numbers (hundreds of thousands of M5 bars per Timeframe, thousands of trades per candidate, dozens of candidates), this is a measurable, avoidable slowdown introduced purely by supporting a feature most runs don't enable.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] When both `trailing_stop_multiplier` and `profit_target_r_multiple` are `None`, `BacktestEngine.run()` uses a vectorized stop-scan (no per-bar Python loop or per-bar `RiskControls` calls) for each re-entry segment, producing byte-identical trades to today's loop-based result
- [ ] When either is set, the existing bar-by-bar loop still runs (unchanged behavior)
- [ ] A benchmark (or the existing full-suite `macd_12_26_9` M5 backtest) run before and after is noted in `## Answer` with timing, showing the vectorized path is at least as fast as it was before ticket 06
- [ ] Existing trailing-stop/profit-target tests (which exercise the loop path) still pass unchanged
- [ ] The test suite stays green
