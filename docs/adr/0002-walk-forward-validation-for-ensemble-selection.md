# Judge the Ensemble selection rule with anchored walk-forward validation, not an in-sample backtest

Until now every Strategy Candidate was ranked, and the Ensemble chosen, on the same history the numbers were measured on. With more Rule Sets and Market Filters being added, picking the best of many candidates on one dataset mostly rewards luck, and the in-sample numbers can't show it. We now judge the **selection rule itself** out of sample: history is cut into consecutive 60-day Test Windows; before each, the Ensemble is chosen using only the growing Selection Window before it (starting at 180 days), then scored on that window alone, starting flat and closing everything at the window's end. The joined Test Window record passes if its Performance Metric is above zero. The Ensemble used for Paper Trading is the same rule applied to all history — the validated rule, not an extra layer of picking.

## Considered Options

- **Keep ranking in-sample** — rejected: selection bias grows with every candidate added, and nothing would reveal it.
- **One fixed holdout (e.g. last 30%)** — rejected in favor of walk-forward: a single split judges the rule on one market regime only.
- **Rolling Selection Window (fixed 180 days)** — rejected: with roughly two years of data, discarding older history leaves too little to choose from.
- **Extra consistency filter for the live Ensemble** (admit only candidates profitable in most Test Windows) — rejected: that is a second, unvalidated selection step.

## Consequences

- The one-per-`(Rule Set, Entry Timeframe)` limit is part of the selection rule, so it is validated too.
- A failing walk-forward does not block Paper Trading, but starting it requires explicit acknowledgment on the dashboard.
