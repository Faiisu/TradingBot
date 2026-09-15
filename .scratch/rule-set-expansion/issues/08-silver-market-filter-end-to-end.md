# 08: Silver Market Filter, end to end

**What to build:** Add silver (XAGUSD) as a Reference Market, following the Market Filter pattern from the DXY ticket. The silver Market Filter reads the direction of silver's EMA(50) on H1 against its value 5 bars earlier. Rising silver allows only long gold entries; falling silver allows only short ones (same direction as gold). Apply it to the same six trend Rule Sets on M15 and M5 (+12 candidates).

**Blocked by:** 07 — DXY Market Filter, end to end

**Status:** done

- [x] Silver H1 history is fetched and cached into the common window, and its coverage is reported
- [x] The filter only uses silver bars that had already closed at each entry bar
- [x] The direction relationship is the same as gold's (not inverse), verified by a test
- [x] 12 new candidates appear in the Backtest ranking, trade history and Walk-Forward Validation, labeled with their Market Filter
- [x] Paper Trading fetches live silver H1 bars and applies the filter
- [x] The test suite stays green

## Answer

Exactly the thin diff ticket 07's design was meant to produce: confirmed silver's MT5 symbol is `XAGUSDm` (729 days of H1 history), added one entry to `registry.py`'s `REFERENCE_MARKETS` (`"XAGUSD": ReferenceMarketConfig(symbol="XAGUSDm", relationship="same")`), and updated `test_registry.py`'s counts. Every other piece — data fetch/cache/coverage reporting, no-lookahead alignment, one-per-pair selection, dashboard labeling, Paper Trading's live-symbol resolution — was already generic across every `REFERENCE_MARKETS` entry from ticket 07 and needed zero new code.

While fetching silver's history, caught and fixed a real bug from ticket 07's own code review: `fetch_history.py`'s print statement still used `config['symbol']` (dict-style), left over from before `REFERENCE_MARKETS`' values became the typed `ReferenceMarketConfig` dataclass — would have crashed with `TypeError` the moment this script actually ran again. No test caught it (nothing covers this script's print output); only running it against live MT5 did. Fixed to `config.symbol`, and grepped the whole repo to confirm it was the only leftover.

**Verified against real MT5 data** (729 days, XAGUSD H1 alongside gold and DXY): all 12 silver-filtered candidates traded, candidate count 65→77, and the 65 pre-existing candidates' trade histories were byte-identical before/after. Walk-Forward Validation still passed (metric 4113.54). Full suite: 180 passed.

Code review (Standards + Spec, parallel sub-agents): clean on both axes, no findings. The `fetch_history.py` bugfix was confirmed complete (repo-wide grep found no other leftover dict-style `ReferenceMarketConfig` access), and the split of the old single "all candidates are DXY" registry test into per-market DXY/XAGUSD tests was confirmed to strengthen rather than weaken coverage.
