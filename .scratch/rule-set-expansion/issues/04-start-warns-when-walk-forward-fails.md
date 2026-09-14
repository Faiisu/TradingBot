# 04: Start button warns when Walk-Forward Validation fails

**What to build:** Paper Trading can still be started when the latest Walk-Forward Validation did not pass, but only as a deliberate choice. When the saved result is "not passed", the Paper Trading page shows why before starting (the out-of-sample Performance Metric), and Start requires explicit confirmation. When it passed, or no result exists yet, Start behaves as it does today.

**Blocked by:** 03 — Walk-Forward Validation on the Backtest page

**Status:** ready-for-agent

- [ ] The Paper Trading page shows the latest walk-forward verdict next to what Start will trade
- [ ] With a failed verdict, pressing Start asks for confirmation that names the failed out-of-sample result; cancelling starts nothing
- [ ] With a passed verdict, Start does not ask for extra confirmation
- [ ] Starting without confirmation cannot bypass the warning (the start request itself carries the acknowledgment)
- [ ] The test suite stays green
