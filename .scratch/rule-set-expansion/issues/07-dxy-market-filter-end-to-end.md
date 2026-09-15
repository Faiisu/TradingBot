# 07: DXY Market Filter, end to end

**What to build:** Introduce the first Reference Market and the Market-Filtered Candidate shape (see glossary). Fetch US Dollar Index H1 history from MT5 into the same common window as gold. The DXY Market Filter reads the direction of DXY's EMA(50) against its value 5 bars earlier. A rising dollar allows only short gold entries; a falling dollar allows only long ones (inverse relationship). Apply it to the six trend Rule Sets (MA Crossover, MACD, ATR Channel, Donchian, Supertrend, ADX/DMI) on M15 and M5 entries (+12 candidates). A candidate carries at most one filter, never stacked with a Trend Filter. This ticket establishes the pattern that the silver and real-yield filters reuse.

**Blocked by:** 02 — Prefactor: one way for candidates to receive supporting data; 05 — New trend Rule Sets (the filter must cover all six trend Rule Sets)

**Status:** done

- [x] DXY H1 history is fetched and cached, and its coverage is reported like gold's
- [x] At every entry bar, the filter only uses DXY bars that had already closed at that moment (test with a DXY series that turns at a known bar)
- [x] 12 Market-Filtered Candidates appear in the Backtest ranking, trade history and Walk-Forward Validation (if present)
- [x] The one-per-(Rule Set, Entry Timeframe) selection limit treats a DXY-filtered candidate as a variant of its unfiltered one
- [x] The Backtest page labels these candidates with their Market Filter
- [x] Paper Trading fetches live DXY H1 bars and applies the filter to these members
- [x] The test suite stays green

## Answer

**Confirmed via MT5** (`symbols_get()`): DXY is `DXYm`, silver is `XAGUSDm` — both follow gold's `XAUUSDm` "m"-suffix convention, both have 700+ days of H1 history available, saving ticket 08 the same discovery step.

**The central prefactor**: `resolve_supporting_data`'s data source generalized from `dict[Timeframe, DataFrame]` (gold-only) to `dict[DataRequirement, DataFrame]` — `DataRequirement` already *was* the right compound key (timeframe + reference_market), so resolution became a plain dict lookup with no special-casing. This removed `ensure_reference_market_resolvable`'s blanket `NotImplementedError` entirely; an unloaded Reference Market now fails the same way a missing Timeframe always has (a clear `KeyError`, readable via a new `DataRequirement.__str__`). Threaded through `run_backtest.py`, `walk_forward.py`, and `paper/loop.py`'s `update_member` (which now resolves a Reference Market requirement to its own MT5 symbol via `registry.py`'s `REFERENCE_MARKETS`, instead of always fetching the traded instrument's own symbol).

**MarketFilteredCandidate** (`market_filter.py`) mirrors `MtfCandidate` closely — same `align_htf_signal` no-lookahead alignment, same wrap-and-gate shape — differing only in its data source (a Reference Market's own OHLCV, not gold's on a higher Timeframe) and a `relationship: "same" | "inverse"` parameter, so DXY (inverse) and silver (ticket 08, same direction) share one class. `ema_slope_filter` is reused verbatim — its defaults (period=50, lookback=5) already match the ticket's "EMA(50) against its value 5 bars earlier" exactly.

**registry.py** wires `MARKET_FILTER_ENTRY_RULE_SETS` (the six trend Rule Sets) × `MARKET_FILTER_ENTRY_TIMEFRAMES` ([M15, M5]) × `REFERENCE_MARKETS` (currently just DXY) = 12 candidates, wrapping only bare Rule Set classes (never an `MtfCandidate`), so a Market-Filtered candidate can never also carry a Trend Filter. `candidate_rule_set_key()` needed no changes — it already extracts `.entry_strategy` generically, which `MarketFilteredCandidate` exposes the same way `MtfCandidate` does. Dashboard labeling needed no changes either — `persistence.py` already reads `filter_name`/`filter_timeframe` generically off any candidate, and `MarketFilteredCandidate` exposes them (`filter_name = "DXY"`), so `app.js`'s existing `filterLabel()` fallback renders "H1 DXY filter" without a new mapping entry.

**Not in scope, correctly deferred**: CONTEXT.md's Market Filter entry also describes a staleness rule ("more than 3 business days old has no opinion"). That's specifically about a Reference Market with a *publication lag* — irrelevant to DXY and silver, whose MT5 bars are available the moment they close, same as gold's. Ticket 09 (real yield, FRED data with a 2-day publish lag) is where that rule actually applies and gets built.

**Verified against real MT5 data** (729 days, DXY H1 alongside gold's 4 timeframes): all 12 DXY-filtered candidates produced trades, candidate count 53→65, and the 53 pre-existing candidates' trade histories were byte-identical before/after (confirming the data-plumbing refactor changed nothing about existing candidates). Walk-Forward Validation still passed (metric 4257.02; window compositions legitimately shift since the new candidates can now be selected). Full suite: 178 passed.

Code review (Standards + Spec, parallel sub-agents) found real issues on both axes, all fixed and re-verified byte-identical against real data:
- **Standards**: the new `resolve_supporting_data` KeyError printed `DataRequirement`'s raw repr (`<Timeframe.H1: 'H1'>` and all) instead of something readable — fixed with a `DataRequirement.__str__`. `REFERENCE_MARKETS`' `dict[str, dict]` shape (accessed via bare string keys — `config["symbol"]`, `config["relationship"]` — in four separate files) was Primitive Obsession — replaced with a typed `ReferenceMarketConfig` dataclass. `MarketFilteredCandidate`'s missing-data error message read inconsistently with `MtfCandidate`'s — aligned. `DataRequirement`'s docstring still described Market Filter resolution in future tense, pointing at this now-closed ticket — updated to point at CONTEXT.md instead.
- **Spec**: the ticket's literal acceptance criterion — "test with a DXY series that turns at a known bar" — wasn't satisfied by a new test; no-lookahead coverage relied entirely on the pre-existing, unbranded `align_htf_signal` test in `test_mtf.py`. Added `test_only_already_closed_reference_market_bars_are_used_at_each_entry_bar`, exercising a turning DXY-like series end to end through `MarketFilteredCandidate` itself.
