# 09: US 10Y real yield Market Filter, end to end

**What to build:** Add the US 10-year real yield as a Reference Market, using FRED's daily series, which downloads without an API key. A value dated day D only becomes usable from 00:00 UTC on D+2, because FRED publishes late; using it earlier would let the Backtest see the future. The filter reads the 20-business-day change: rising yields allow only short gold entries, falling yields only long ones (inverse). Apply it to the same six trend Rule Sets on M15 and M5 (+12 candidates). In Paper Trading, refresh the series once a day. If its latest usable value is more than 3 business days old, the filter has **no opinion**: that candidate opens no new trades until fresh data arrives, its open trades still exit normally, and the rest of the Ensemble keeps running.

**Blocked by:** 07 — DXY Market Filter, end to end

**Status:** ready-for-agent

- [ ] The FRED series is downloaded and cached; a failed download is reported, not silently ignored
- [ ] A value for day D is never used before 00:00 UTC on D+2 (test with a series that changes on a known date)
- [ ] 12 new candidates appear in the Backtest ranking, trade history and Walk-Forward Validation, labeled with their Market Filter
- [ ] Paper Trading refreshes the series daily; after more than 3 business days without a fresh value, affected members open no new trades while open trades exit normally and other members are unaffected
- [ ] The Paper Trading page shows when the real-yield data is stale and which members it is holding back
- [ ] The test suite stays green
