# 04: Start button warns when Walk-Forward Validation fails

**What to build:** Paper Trading can still be started when the latest Walk-Forward Validation did not pass, but only as a deliberate choice. When the saved result is "not passed", the Paper Trading page shows why before starting (the out-of-sample Performance Metric), and Start requires explicit confirmation. When it passed, or no result exists yet, Start behaves as it does today.

**Blocked by:** 03 — Walk-Forward Validation on the Backtest page

**Status:** done

- [x] The Paper Trading page shows the latest walk-forward verdict next to what Start will trade
- [x] With a failed verdict, pressing Start asks for confirmation that names the failed out-of-sample result; cancelling starts nothing
- [x] With a passed verdict, Start does not ask for extra confirmation
- [x] Starting without confirmation cannot bypass the warning (the start request itself carries the acknowledgment)
- [x] The test suite stays green

## Answer

**Storage:** `run_backtest.py` now also writes a small side file, `data/walk_forward_verdict.json` (`{passed, performance_metric, window_count, generated_at}`), via new `save_walk_forward_verdict()`/`load_walk_forward_verdict()` in `persistence.py`. This mirrors the existing `ensemble.json` pattern: `server.py`'s `walk_forward_summary()` reads this small file instead of parsing the 11.8MB `backtest_results.json` on every `/api/paper/status` poll (every 1-4s while the page is open).

**Server-side gate (the part that actually matters for "cannot bypass"):** `POST /api/paper/start` independently calls `walk_forward_summary()` itself — it never trusts the client's claim alone. It rejects with 409 (naming the out-of-sample Performance Metric) only when its own check finds the verdict failed *and* the request body lacks `acknowledge_failed_walk_forward: true`. A client that omits the flag, sends a stale/wrong flag, or sends a malformed body still gets the same enforcement — malformed JSON is caught and treated as no acknowledgment (409, not a 500), verified by `test_start_with_a_malformed_body_is_treated_as_no_acknowledgment_rather_than_erroring`.

**Frontend:** `dashboard.html` gained a `wfv-detail` line directly under `ensemble-detail`; `paper.js`'s `renderWalkForward()` shows a Passed/Failed pill (matching the Backtest page's own pill convention, not the numeric-sign `.pos`/`.neg` style) plus the out-of-sample metric and window count. `control('start')` checks `lastStatus.walk_forward` before calling `/api/paper/start`: a failed verdict triggers a `confirm()` naming the metric, and cancelling returns before any request is sent; a passed or missing verdict starts exactly as before, no extra prompt.

**Verified:** ran the real backtest against live MT5 data to produce `walk_forward_verdict.json`, restarted the dashboard, and confirmed via curl that `/api/paper/status` returns the verdict and the served HTML/JS carry the new UI. Did not call `POST /api/paper/start` against the live server (would actually spawn a real paper-trading process against the MT5 demo account) — the gating logic itself is covered by 8 new unit tests in `test_server.py` (no verdict, passed, failed+no-ack, failed+ack, malformed body) using the existing fake-supervisor pattern. Full suite: 132 passed.

Code review (Standards + Spec, parallel sub-agents): Spec review found all five criteria satisfied, no scope creep, confirmed the server-side gate can't be bypassed client-side. Standards review found one hard violation (verdict rendered with `.pos`/`.neg` instead of the established `.pill good`/`.pill bad` convention already used for verdicts on the Backtest page and for session state on this same page) — fixed. Also addressed two judgement calls: reordered `paper_start()` to parse the request body once up front (handling malformed JSON gracefully) before its two guard clauses, and simplified `walk_forward_summary()` from a field-dropping reconstruction to a plain passthrough of the persisted verdict.
