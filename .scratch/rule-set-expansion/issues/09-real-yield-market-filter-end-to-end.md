# 09: US 10Y real yield Market Filter, end to end

**What to build:** Add the US 10-year real yield as a Reference Market, using FRED's daily series, which downloads without an API key. A value dated day D only becomes usable from 00:00 UTC on D+2, because FRED publishes late; using it earlier would let the Backtest see the future. The filter reads the 20-business-day change: rising yields allow only short gold entries, falling yields only long ones (inverse). Apply it to the same six trend Rule Sets on M15 and M5 (+12 candidates). In Paper Trading, refresh the series once a day. If its latest usable value is more than 3 business days old, the filter has **no opinion**: that candidate opens no new trades until fresh data arrives, its open trades still exit normally, and the rest of the Ensemble keeps running.

**Blocked by:** 07 — DXY Market Filter, end to end

**Status:** done

- [x] The FRED series is downloaded and cached; a failed download is reported, not silently ignored
- [x] A value for day D is never used before 00:00 UTC on D+2 (test with a series that changes on a known date)
- [x] 12 new candidates appear in the Backtest ranking, trade history and Walk-Forward Validation, labeled with their Market Filter
- [x] Paper Trading refreshes the series daily; after more than 3 business days without a fresh value, affected members open no new trades while open trades exit normally and other members are unaffected
- [x] The Paper Trading page shows when the real-yield data is stale and which members it is holding back
- [x] The test suite stays green

## Answer

The biggest ticket in the series — confirmed via curl that FRED's DFII10 series (10-Year Treasury Inflation-Indexed Security, the real yield) downloads as a plain CSV from `fred.stlouisfed.org/graph/fredgraph.csv?id=DFII10`, no API key, full history to 2003.

**Data layer** (new `data/real_yield.py`): `fetch_real_yield()` downloads and re-indexes the series by `usable_from` (each value's own date + 2 days, at 00:00 UTC) rather than the date it describes — so every existing no-lookahead mechanism (`align_htf_signal`) treats it exactly like any other Reference Market's data, no special-casing. A download failure raises `RealYieldDownloadError` clearly. Two loading modes sit on top: `load_real_yield()` (Backtest: cache-or-fetch-once, failure propagates loud) and `refresh_real_yield_cache()` (Paper Trading: refetches at most once a day, falls back to the stale cache and *reports* — prints a warning — on a failed refresh rather than crashing the loop). New `data/reference_markets.py` centralizes the MT5-vs-FRED dispatch for the Backtest side, shared by `fetch_history.py` and `run_backtest.py`.

**The staleness gate**: `MarketFilteredCandidate` gained an optional `max_staleness_business_days` parameter (`None` for DXY/silver — sourced live from MT5, never stale). When set, a new `_apply_market_filter()` stateful gate applies the ticket's exact rule: fresh data gates normally; stale data opens no new trades, and a position already held continues only if the entry Rule Set's own signal still agrees with the direction already held — any disagreement (including a would-be flip) goes flat rather than reversing. Exits are never blocked by staleness: a flat/exit signal (0) can never equal a nonzero held direction, so the gate's own condition always lets it through.

**Real yield's own filter**: a new `real_yield_change_filter()` (20-business-day raw change, no smoothing — unlike DXY/silver's EMA-slope) reused verbatim since the data is already one row per business day, `usable_from`-indexed.

**Real bugs found and fixed via real-data testing, not caught by any synthetic unit test**: pandas 3.x's `merge_asof` refuses to match keys of different datetime64 *resolutions* even when the underlying instants agree — MT5-sourced OHLCV and a parquet round-trip of FRED data landed on different resolutions. This broke both `align_htf_signal` (aligning the real yield's own filter) and the new staleness age computation. Fixed by normalizing both merge sides to `datetime64[ns]`, with regression tests reproducing the exact failure in both places, then re-verified byte-identical against real data.

**Paper Trading + dashboard**: `paper/loop.py`'s `update_member` now dispatches each supporting-data requirement to MT5 or FRED (via a new `resolve_requirement_data()`) and reports, per tick, each FRED-backed Reference Market's age in business days. `build_state()` (dashboard/state.py) turns that into per-member `held_back_by_stale_data`/`stale_data_age_business_days` fields, computed generically off any candidate exposing `reference_market`/`max_staleness_business_days` (works for any future FRED-backed market too). The Paper Trading page shows a per-member "Stale data" badge plus a summary line naming every held-back member and the data's age.

**Verified against real MT5+FRED data**: all 12 real-yield-filtered candidates traded, candidate count 77→89, and the 77 pre-existing candidates' trade histories were byte-identical before and after every change in this ticket (including the two dtype bugfixes and the later review-driven refactor). Walk-Forward Validation still passed. Full suite: 208 passed.

Code review (Standards + Spec, parallel sub-agents): Spec review found the implementation matched every acceptance criterion exactly, including tracing the staleness gate's exit-never-blocked behavior by hand; its one flagged nit — the dashboard's staleness age is computed against wall-clock "now" while the trading gate computes it against each entry bar's own timestamp — was judged low-risk and documented with a comment rather than unified, since the two only differ by sub-tick timing. Standards review's one actionable finding — `align_htf_signal` and the staleness age computation had independently grown the identical datetime64-normalization fix, a duplication the earlier bug already proved risky to leave uncentralized — was fixed by extracting a shared `match_backward()` helper in `base.py`; re-verified byte-identical against real data after the refactor.
