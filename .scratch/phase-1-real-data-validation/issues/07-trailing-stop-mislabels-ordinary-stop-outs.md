# 07: Trailing stop mislabels ordinary stop-outs as "trailing_stop"

**What to build:** Fix the trailing-stop ratchet (ticket 06's uncommitted work) so a trade that never had a genuine favorable move after entry is labeled `exit_reason="stop_loss"`, not `"trailing_stop"` — matching what the Backtest/Paper Trading pages, and any future analysis of exit-reason breakdowns, actually mean by those two labels.

Found during code review of ticket 01: both `BacktestEngine.run()` and `SimulatedBroker._open()` seed the trailing ratchet's initial "extreme price" from the **entry bar's own high (long) or low (short)**, not from `entry_price`. Since a position is entered at that same bar's close, its own high/low reflects intrabar movement that happened *before or at* the entry decision, not favorable movement *since* entry. This makes the ratchet tighten immediately on entry even with zero real favorable excursion — e.g. entry at close=100 with that bar's high=101 (ATR=1.0, `trailing_stop_multiplier=2.0`, fixed stop=98) immediately computes a trailing level of 99; if the very next bar crashes straight through (no favorable move at all), the exit is labeled `"trailing_stop"` at 99 instead of `"stop_loss"` at 98, even though `pnl_pct` is negative — contradicting the meaning both pages already give the two labels (e.g. Paper Trading's trade log implies a `"trailing_stop"` exit rode a real favorable move first).

This was implemented consistently between `engine.py` and `simulated_broker.py` (intentional, per `test_simulated_broker.py`'s existing comment "entry bar's own high seeds the initial extreme, matching BacktestEngine's convention") — but the convention itself is the bug. The existing trailing-stop tests in both files happen to use bars with the entry bar's high/low equal to the entry price (zero range at entry), which hides this: `extreme_price` seeded from the entry bar's high/low only differs from `entry_price` when that bar actually has range, which real market bars always do.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] `BacktestEngine.run()` and `SimulatedBroker._open()` seed the trailing ratchet's initial extreme from `entry_price`, not the entry bar's own high/low
- [ ] A trade that stops out on the very next bar with no favorable excursion since entry is labeled `"stop_loss"` and exits at the original fixed-stop price, not a tighter "trailing" level (test with a bar that has range at entry, unlike the current tests)
- [ ] Existing trailing-stop tests in both files are updated to bars with real range at entry, and still pass
- [ ] A trade that does have a genuine favorable move before pulling back still labels `"trailing_stop"` and exits at the ratcheted level (regression test for the existing behavior)
- [ ] Re-running the Backtest and comparing exit-reason counts before/after is noted in `## Answer` so the size of the mislabeling is visible
- [ ] The test suite stays green
