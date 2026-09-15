# 05: Paper trading dry run

**What to build:** `scripts/run_paper_trading.py` running live against the demo account's streaming prices for a real stretch of time, confirming the polling loop opens/closes simulated positions correctly and never places a real order.

**Blocked by:** 03 (and 04's real-data re-confirmation)

**Status:** ready-for-human — long-running, needs to be started/monitored by the user

- [ ] Paper trading loop runs without crashing across multiple bar closes
- [ ] Simulated trades logged match expectations from signals
- [ ] No real orders placed (demo account, but worth confirming)

## Comments

2026-09-16: Two earlier dry runs (2026-09-13, then again 2026-09-15) ran against a buggy loop —
`run_paper_trading_loop` gated each member on a local `tick % multiple` counter that started from
whatever moment the loop happened to launch, instead of true wall-clock alignment. This let a
Timeframe larger than M5 fire up to (multiple − 1) × 5 minutes after its real bar close while still
recording the entry price as that bar's close, which by execution time was already stale — e.g. an
M15 bar that closed at 16:45 was processed at 16:50, a 5-minute-plus lag that grows to up to 55
minutes for H1 members depending on start time. Fixed in `.scratch/edge-discovery-roadmap/issues/
01-paper-loop-acts-on-every-timeframe-close.md`: members are now scheduled by rounding the current
time down to the smallest Timeframe's own boundary and checking whether that boundary is also a
multiple of each candidate's own Timeframe length — independent of when the loop started. Every
processed bar now also records a decision-latency (seconds between bar close and decision), surfaced
on the Paper Trading page as "Worst decision latency". The dry run was restarted at 2026-09-16 on
the fixed loop; this ticket's checklist should be evaluated against that run, not the two earlier ones.
