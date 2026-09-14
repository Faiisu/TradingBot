# 07: DXY Market Filter, end to end

**What to build:** Introduce the first Reference Market and the Market-Filtered Candidate shape (see glossary). Fetch US Dollar Index H1 history from MT5 into the same common window as gold. The DXY Market Filter reads the direction of DXY's EMA(50) against its value 5 bars earlier. A rising dollar allows only short gold entries; a falling dollar allows only long ones (inverse relationship). Apply it to the six trend Rule Sets (MA Crossover, MACD, ATR Channel, Donchian, Supertrend, ADX/DMI) on M15 and M5 entries (+12 candidates). A candidate carries at most one filter, never stacked with a Trend Filter. This ticket establishes the pattern that the silver and real-yield filters reuse.

**Blocked by:** 02 — Prefactor: one way for candidates to receive supporting data; 05 — New trend Rule Sets (the filter must cover all six trend Rule Sets)

**Status:** ready-for-agent

- [ ] DXY H1 history is fetched and cached, and its coverage is reported like gold's
- [ ] At every entry bar, the filter only uses DXY bars that had already closed at that moment (test with a DXY series that turns at a known bar)
- [ ] 12 Market-Filtered Candidates appear in the Backtest ranking, trade history and Walk-Forward Validation (if present)
- [ ] The one-per-(Rule Set, Entry Timeframe) selection limit treats a DXY-filtered candidate as a variant of its unfiltered one
- [ ] The Backtest page labels these candidates with their Market Filter
- [ ] Paper Trading fetches live DXY H1 bars and applies the filter to these members
- [ ] The test suite stays green
