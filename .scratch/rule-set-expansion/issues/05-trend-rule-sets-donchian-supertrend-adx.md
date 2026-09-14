# 05: New trend Rule Sets — Donchian, Supertrend, ADX/DMI

**What to build:** Add three trend-following Rule Sets. Each uses one fixed set of default parameters, trades both directions, and runs on all four Timeframes (+12 Strategy Candidates). All of them also use the shared Risk Controls ATR stop:
- **Donchian Breakout:** long on a close above the highest high of the prior 20 bars, short on a close below the lowest low of the prior 20 bars; flat when a long closes below the prior 10-bar low, or a short closes above the prior 10-bar high.
- **Supertrend (ATR 10 × 3):** always follows Supertrend's direction; no flat state.
- **ADX/DMI (14):** when ADX is above 25, long if +DI > −DI, otherwise short; flat whenever ADX is 25 or below.

**Blocked by:** 02 — Prefactor: one way for candidates to receive supporting data

**Status:** ready-for-agent

- [ ] Each Rule Set produces the entry/exit behavior above, verified by tests on synthetic price series with known breakouts/crossovers
- [ ] 12 new candidates appear in the Backtest ranking, trade history and Walk-Forward Validation (if present) with readable names on the Backtest page
- [ ] Paper Trading can run them: they load from the saved Ensemble and process live bars
- [ ] The test suite stays green
