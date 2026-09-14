# 05: New trend Rule Sets — Donchian, Supertrend, ADX/DMI

**What to build:** Add three trend-following Rule Sets. Each uses one fixed set of default parameters, trades both directions, and runs on all four Timeframes (+12 Strategy Candidates). All of them also use the shared Risk Controls ATR stop:
- **Donchian Breakout:** long on a close above the highest high of the prior 20 bars, short on a close below the lowest low of the prior 20 bars; flat when a long closes below the prior 10-bar low, or a short closes above the prior 10-bar high.
- **Supertrend (ATR 10 × 3):** always follows Supertrend's direction; no flat state.
- **ADX/DMI (14):** when ADX is above 25, long if +DI > −DI, otherwise short; flat whenever ADX is 25 or below.

**Blocked by:** 02 — Prefactor: one way for candidates to receive supporting data

**Status:** done

- [x] Each Rule Set produces the entry/exit behavior above, verified by tests on synthetic price series with known breakouts/crossovers
- [x] 12 new candidates appear in the Backtest ranking, trade history and Walk-Forward Validation (if present) with readable names on the Backtest page
- [x] Paper Trading can run them: they load from the saved Ensemble and process live bars
- [x] The test suite stays green

## Answer

**Indicators** (`indicators.py`): `donchian_channel(high, low, period)` — the highest high / lowest low of the prior `period` bars, shifted by 1 so the current bar's own high/low is never included (verified by a dedicated test). `supertrend(high, low, close, period, multiplier)` — the standard band-tightening algorithm, returning direction only (1/-1, NaN only during ATR warmup); this is the one genuinely path-dependent new indicator so it keeps an explicit loop, matching the existing precedent (`band_state_signals`/`rsi` in this codebase already use stateful loops for path-dependent signals). `adx_dmi(high, low, close, period)` — Wilder's ADX/+DI/-DI, sharing a new `true_range()` helper factored out of `atr()` (previously duplicated inline). Both `atr()` and `adx_dmi()` now call it.

**Rule Sets**: `DonchianBreakoutStrategy` (entry 20-bar channel, exit 10-bar channel — a new `channel_breakout_signals()` helper in `base.py` handles the asymmetric entry/exit width, since the existing `band_state_signals()` only supports a single shared middle line). `SupertrendStrategy` (direction is the signal directly, no flat state). `AdxDmiStrategy` (long/short only when ADX > 25, using strict `>`; flat otherwise). All three registered in `registry.py`'s `RULE_SETS`, deliberately NOT added to `MTF_ENTRY_RULE_SETS` (the ticket asks for 12 single-timeframe candidates only, verified by a dedicated registry test). Dashboard labels added to `app.js`'s `RULE_SET_LABELS`.

**Verified against real MT5 data** (728 days, XAUUSD H1/M30/M15/M5): all three Rule Sets produced trades on all four timeframes, candidate count went from 29 to 41, Ensemble grew from 16 to 28 members, Walk-Forward Validation still passed (9 windows, out-of-sample metric 5005.09). Full test suite: 149 passed. Nothing outside `registry.py`, `app.js` and the new strategy/indicator modules needed touching — Paper Trading and the ATR stop are both already rule-set-agnostic (Paper Trading resolves candidates purely through `registry.build_candidates()`; the ATR stop is applied uniformly by `BacktestEngine` regardless of Rule Set).

Code review (Standards + Spec, parallel sub-agents): Spec review found two test-coverage gaps — ADX/DMI's short branch and Donchian's short→flat transition were implemented correctly but untested — both fixed with new tests. Standards review found a real duplication (the new `channel_breakout_signals` was a near-line-for-line copy of the existing `band_state_signals`) and a zero-division gap in `adx_dmi` (a flat run of bars could produce `inf`/`NaN` instead of a clean "no direction" reading). Both fixed: the two breakout-signal functions now share a private `_stateful_breakout_signals` helper (parameterized by inclusive/exclusive exit boundary, so `band_state_signals`' already-shipped behavior for ATR Channel Breakout and Bollinger Breakout is untouched), and `adx_dmi` guards its two division points the same way `rsi()` already does elsewhere in the file. Re-verified byte-identical against real MT5 data after all fixes (0 mismatches across all 41 candidates, identical Walk-Forward result).
