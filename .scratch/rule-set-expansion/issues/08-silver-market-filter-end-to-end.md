# 08: Silver Market Filter, end to end

**What to build:** Add silver (XAGUSD) as a Reference Market, following the Market Filter pattern from the DXY ticket. The silver Market Filter reads the direction of silver's EMA(50) on H1 against its value 5 bars earlier. Rising silver allows only long gold entries; falling silver allows only short ones (same direction as gold). Apply it to the same six trend Rule Sets on M15 and M5 (+12 candidates).

**Blocked by:** 07 — DXY Market Filter, end to end

**Status:** ready-for-agent

- [ ] Silver H1 history is fetched and cached into the common window, and its coverage is reported
- [ ] The filter only uses silver bars that had already closed at each entry bar
- [ ] The direction relationship is the same as gold's (not inverse), verified by a test
- [ ] 12 new candidates appear in the Backtest ranking, trade history and Walk-Forward Validation, labeled with their Market Filter
- [ ] Paper Trading fetches live silver H1 bars and applies the filter
- [ ] The test suite stays green
