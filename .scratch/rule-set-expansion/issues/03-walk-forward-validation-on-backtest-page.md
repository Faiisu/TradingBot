# 03: Walk-Forward Validation on the Backtest page

**What to build:** Judge the Ensemble selection rule on data it has never seen (see ADR 0002 and the Walk-Forward Validation, Selection Window and Test Window entries in the glossary). Use anchored walk-forward: the first Selection Window is 180 days, followed by consecutive 60-day Test Windows (~9 over the full history). Before each Test Window, choose an Ensemble using only its Selection Window, then score that Ensemble on the Test Window alone. Each window starts with no open positions and closes everything at its last bar. The selection rule is Performance Metric above zero, with at most one member per (Rule Set, Entry Timeframe): among an unfiltered candidate and its filtered variants, the best Performance Metric wins. Join the Test Window results into one out-of-sample record; it passes when that record's Performance Metric is above zero. The Ensemble saved for Paper Trading is the same rule applied to all history. The Backtest page shows the whole result.

**Blocked by:** 02 — Prefactor: one way for candidates to receive supporting data

**Status:** done

- [x] Test Windows are consecutive, never overlap their Selection Window, and use no data from their own window when choosing
- [x] Every Test Window's Ensemble starts flat, and any position still open at the window's end is closed at its last bar
- [x] The selection rule admits at most one member per (Rule Set, Entry Timeframe), keeping the best Performance Metric from the Selection Window
- [x] The joined out-of-sample record, its Performance Metric and a pass/fail verdict are saved alongside the backtest results
- [x] The Paper Trading Ensemble is produced by the same rule (including the one-per-pair limit) over all history
- [x] Backtest page shows: the out-of-sample equity curve; a table of Test Windows with dates, chosen members and each window's result; a clear pass/fail status
- [x] A test proves no Test Window's choice can see that window's data (e.g. a candidate that only profits inside one Test Window is never chosen for that window)
- [x] The test suite stays green

## Answer

Built in two parts:

**One-per-pair Ensemble selection.** `candidate_rule_set_key(candidate)` (`strategies/base.py`) groups a candidate by `(base.name, timeframe.value)`, where `base` is `candidate.entry_strategy` for a Market-Filtered candidate, or the candidate itself otherwise — so an unfiltered strategy and each of its filtered variants collide into the same key. `select_ensemble` (`ensemble/selection.py`) now takes `list[tuple[StrategyCandidate, BacktestResult]]` (a breaking signature change from `list[BacktestResult]`, both call sites updated) and keeps only the best-Performance-Metric member per key.

**Walk-Forward Validation.** New `backtest/walk_forward.py`: `compute_windows()` produces anchored windows (Selection Window always starts at the data's start and grows; Test Windows are consecutive, fixed 60-day, half-open `[test_start, test_end)` so a window never sees its own future data); `run_walk_forward()` runs every candidate on each Selection Window, calls `select_ensemble` on those results, then re-runs only the chosen members on the following Test Window (a fresh, isolated `BacktestEngine.run()` per window — no state carries across windows, so each Test Window's Ensemble is guaranteed to start flat and close everything at the window's last bar, inherited from `BacktestEngine`'s existing tested behaviour); `chain_equity_curve()` compounds each window's equal-weighted Test Window return onto the last, producing the joined out-of-sample record. No-lookahead is proven by `test_a_candidate_that_only_profits_in_one_test_window_is_never_chosen_for_that_window`, which uses a `_TrapCandidate` that only signals from a specific `reveal_at` timestamp and asserts it's never selected for the window whose Test data would reveal it.

`scripts/run_backtest.py` now runs both: `select_ensemble` once over full, unwindowed history (unchanged) to produce `ensemble.json` for Paper Trading, and `run_walk_forward` separately to validate that same selection rule out-of-sample. Results are persisted together in `backtest_results.json` (`_serialize_walk_forward` in `persistence.py`); the Backtest page (`backtest.html` / `backtest.js`) renders a new "Walk-Forward Validation" panel above the candidate list: a pass/fail pill, out-of-sample Performance Metric, window count and compounded out-of-sample return as stat tiles, the out-of-sample equity curve via the existing `lineChart()` helper, and a table of every Test Window (dates, return, member count, chosen members).

**Verified against real MT5 data** (728 days, XAUUSD H1/M30/M15/M5): 9 Test Windows produced, every one individually profitable (2.21%–8.03% return), out-of-sample Performance Metric 5419.77 (large because the joined curve has zero observed drawdown at this resolution, hitting the pre-existing `EPSILON` floor in `performance_metric` — not new to this ticket), `passed=True`. Full test suite: 124 passed, 0 warnings.

Code review (Standards + Spec, parallel sub-agents) found no hard violations. Standards flagged minor judgement-call smells (duplicate `performance_metric` computation in `select_ensemble`, a slightly-duplicated selection/test scoring loop shape, a redundant `build_candidates()` call, a `len(outcomes) >= 1` guard) — all fixed, and the real-data run was re-verified byte-identical after the fixes. Spec review's one finding — that nothing gates starting Paper Trading on a failed walk-forward verdict — is intentionally out of scope here: that's ticket 04, blocked by this one.
