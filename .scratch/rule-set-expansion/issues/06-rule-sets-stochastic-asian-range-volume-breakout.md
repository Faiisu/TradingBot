# 06: New Rule Sets — Stochastic Reversion, Asian Range Breakout, Volume-Confirmed Breakout

**What to build:** Add three more Rule Sets. Each uses one fixed set of default parameters, trades both directions, and runs on all four Timeframes (+12 Strategy Candidates). All of them also use the shared Risk Controls ATR stop:
- **Stochastic Reversion (14, 3):** long when %K is below 20, short when above 80; flat when %K crosses back through 50 (the same shape as RSI Reversion).
- **Asian Range Breakout:** the range is the high/low of 00:00–07:00 UTC (fixed UTC, no daylight-saving adjustment; broker server time is UTC). Between 07:00 and 16:00 UTC, go long on a close above the range, short on a close below it, and flip if the opposite side breaks the same day. Always flat at 21:00 UTC.
- **Volume-Confirmed Breakout:** identical to Donchian Breakout, except the breakout bar's tick volume must also exceed 1.5× its 20-bar average. It deliberately differs only in that condition, so any difference in results is attributable to volume.

Tick volume is already in cached history but is dropped from the live bars Paper Trading reads; carry it through.

**Blocked by:** 02 — Prefactor: one way for candidates to receive supporting data

**Status:** done

- [x] Each Rule Set produces the entry/exit behavior above, verified by tests on synthetic series (including session boundaries at 07:00, 16:00 and 21:00 UTC, and a breakout rejected for low volume)
- [x] Asian Range Breakout never holds a position past 21:00 UTC and never opens one outside 07:00–16:00 UTC
- [x] 12 new candidates appear in the Backtest ranking, trade history and Walk-Forward Validation (if present)
- [x] Paper Trading receives tick volume with live bars, and all three Rule Sets run there
- [x] The test suite stays green

## Answer

**Stochastic Reversion**: new `stochastic(high, low, close, k_period, d_period)` indicator (%K/%D, with a zero-range guard matching `adx_dmi`'s and `rsi`'s existing convention). The threshold-crossing entry/exit logic ("same shape as RSI Reversion") is now a shared `threshold_reversion_signals()` helper in `base.py`, extracted from `RsiMeanReversionStrategy` (which was refactored to use it too, verified byte-identical via its existing tests) and reused by `StochasticReversionStrategy`, which reads only %K.

**Volume-Confirmed Breakout**: `channel_breakout_signals()` (and its shared `_stateful_breakout_signals` internals) gained an optional `entry_confirmed` mask — true by default, so `DonchianBreakoutStrategy`'s behavior is unchanged. `VolumeConfirmedBreakoutStrategy` reuses Donchian's exact channel logic (same 20/10 entry/exit defaults) and gates only new entries on tick volume exceeding 1.5x its prior-20-bar average (`shift(1).rolling(20).mean()`, excluding the breakout bar's own volume — no lookahead).

**Asian Range Breakout**: new module with fixed UTC session boundaries (00:00–07:00 range, 07:00–16:00 entry window, 21:00 forced flat) as module constants, and a dedicated stateful loop (distinct in shape from `_stateful_breakout_signals` — three-way forced-flat/entry-window-breakout/persist branching rather than entry/exit channels). Each day's range is computed once from that day's own session bars only and broadcast to every bar of that day, so the entry window never sees its own range still growing. The fact this depends on ("broker server time is UTC, no DST") wasn't actually documented anywhere in the repo before this ticket — added to `CONTEXT.md`'s Broker glossary entry, and the strategy's docstring citation now points somewhere real.

**Tick volume threading**: `paper/loop.py`'s `fetch_recent_bars()` now includes `tick_volume` in both the success path and the empty-data fallback columns; the `_FakeMt5` test fixture was updated to provide real varying tick_volume values so the coverage isn't vacuous.

All three Rule Sets wired into `registry.py`'s `RULE_SETS` (44 single-timeframe + 9 MTF = 53 total candidates), deliberately excluded from `MTF_ENTRY_RULE_SETS` per the ticket's single-timeframe-only scope. Dashboard labels added to `app.js`.

**Verified against real MT5 data** (728 days, XAUUSD H1/M30/M15/M5): all three Rule Sets produced trades on all four timeframes, candidate count 41→53, and diffing the 41 pre-existing candidates' trade histories before/after showed 0 mismatches (the `base.py` refactor didn't change any existing Rule Set's behavior). Walk-Forward Validation still passed (9 windows, out-of-sample metric 4287.16). Full test suite: 167 passed.

Code review (Standards + Spec, parallel sub-agents): Standards found one real issue — `StochasticReversionStrategy`'s `d_period` constructor param had no effect on the actual signal (only on naming), which read as unexplained dead configuration — fixed with a docstring clarifying it's kept for indicator-name parity with the ticket's "(14, 3)" framing, not because %D drives the entry rule. Spec review found one real issue — the strategy's docstring claimed "(see CONTEXT.md)" for the UTC-broker-time assumption the whole feature depends on, but that fact wasn't actually in CONTEXT.md anywhere — fixed by documenting it there for real. Both axes otherwise found the implementation matched the spec's prose exactly, including the exact boundary bars (07:00, 16:00, 21:00) and the flip-within-window behavior.
