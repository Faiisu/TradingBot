# 05: Paper trading dry run

**What to build:** `scripts/run_paper_trading.py` running live against the demo account's streaming prices for a real stretch of time, confirming the polling loop opens/closes simulated positions correctly and never places a real order.

**Blocked by:** 03 (and 04's real-data re-confirmation)

**Status:** ready-for-human — long-running, needs to be started/monitored by the user

- [ ] Paper trading loop runs without crashing across multiple bar closes
- [ ] Simulated trades logged match expectations from signals
- [ ] No real orders placed (demo account, but worth confirming)
