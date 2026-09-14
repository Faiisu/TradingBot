# 03: Walk-Forward Validation on the Backtest page

**What to build:** Judge the Ensemble selection rule on data it has never seen (see ADR 0002 and the Walk-Forward Validation, Selection Window and Test Window entries in the glossary). Use anchored walk-forward: the first Selection Window is 180 days, followed by consecutive 60-day Test Windows (~9 over the full history). Before each Test Window, choose an Ensemble using only its Selection Window, then score that Ensemble on the Test Window alone. Each window starts with no open positions and closes everything at its last bar. The selection rule is Performance Metric above zero, with at most one member per (Rule Set, Entry Timeframe): among an unfiltered candidate and its filtered variants, the best Performance Metric wins. Join the Test Window results into one out-of-sample record; it passes when that record's Performance Metric is above zero. The Ensemble saved for Paper Trading is the same rule applied to all history. The Backtest page shows the whole result.

**Blocked by:** 02 — Prefactor: one way for candidates to receive supporting data

**Status:** ready-for-agent

- [ ] Test Windows are consecutive, never overlap their Selection Window, and use no data from their own window when choosing
- [ ] Every Test Window's Ensemble starts flat, and any position still open at the window's end is closed at its last bar
- [ ] The selection rule admits at most one member per (Rule Set, Entry Timeframe), keeping the best Performance Metric from the Selection Window
- [ ] The joined out-of-sample record, its Performance Metric and a pass/fail verdict are saved alongside the backtest results
- [ ] The Paper Trading Ensemble is produced by the same rule (including the one-per-pair limit) over all history
- [ ] Backtest page shows: the out-of-sample equity curve; a table of Test Windows with dates, chosen members and each window's result; a clear pass/fail status
- [ ] A test proves no Test Window's choice can see that window's data (e.g. a candidate that only profits inside one Test Window is never chosen for that window)
- [ ] The test suite stays green
