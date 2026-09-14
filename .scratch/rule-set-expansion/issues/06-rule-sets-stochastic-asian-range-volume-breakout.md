# 06: New Rule Sets — Stochastic Reversion, Asian Range Breakout, Volume-Confirmed Breakout

**What to build:** Add three more Rule Sets. Each uses one fixed set of default parameters, trades both directions, and runs on all four Timeframes (+12 Strategy Candidates). All of them also use the shared Risk Controls ATR stop:
- **Stochastic Reversion (14, 3):** long when %K is below 20, short when above 80; flat when %K crosses back through 50 (the same shape as RSI Reversion).
- **Asian Range Breakout:** the range is the high/low of 00:00–07:00 UTC (fixed UTC, no daylight-saving adjustment; broker server time is UTC). Between 07:00 and 16:00 UTC, go long on a close above the range, short on a close below it, and flip if the opposite side breaks the same day. Always flat at 21:00 UTC.
- **Volume-Confirmed Breakout:** identical to Donchian Breakout, except the breakout bar's tick volume must also exceed 1.5× its 20-bar average. It deliberately differs only in that condition, so any difference in results is attributable to volume.

Tick volume is already in cached history but is dropped from the live bars Paper Trading reads; carry it through.

**Blocked by:** 02 — Prefactor: one way for candidates to receive supporting data

**Status:** ready-for-agent

- [ ] Each Rule Set produces the entry/exit behavior above, verified by tests on synthetic series (including session boundaries at 07:00, 16:00 and 21:00 UTC, and a breakout rejected for low volume)
- [ ] Asian Range Breakout never holds a position past 21:00 UTC and never opens one outside 07:00–16:00 UTC
- [ ] 12 new candidates appear in the Backtest ranking, trade history and Walk-Forward Validation (if present)
- [ ] Paper Trading receives tick volume with live bars, and all three Rule Sets run there
- [ ] The test suite stays green
