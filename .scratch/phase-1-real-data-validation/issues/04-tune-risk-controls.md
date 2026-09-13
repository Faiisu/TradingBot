# 04: Tune risk controls to remove runaway leverage compounding

**What to build:** adjust `RiskControls` defaults (`max_position_fraction`, `risk_pct_per_trade`) so backtest results stay plausible instead of compounding into millions-of-percent returns over thousands of trades, and confirm the fix with a backtest re-run.

**Blocked by:** 03 (originally) — started early using synthetic data since 01-03 were blocked on account creation; needs re-confirmation against real data once 03 completes.

**Status:** done (synthetic-data pass) — see `## Answer` below for what changed and why

- [x] Root cause identified
- [x] `RiskControls` defaults adjusted
- [x] Backtest re-run on synthetic data to confirm more plausible numbers
- [ ] Re-confirmed against real data (pending ticket 03)

## Answer

Two separate issues were found and fixed, not just a leverage number:

1. **`max_position_fraction` lowered from 5.0 to 1.0** (`risk/risk_controls.py`) — capping notional exposure at 1x equity instead of allowing 5x leveraged trades. This alone brought the worst case (MACD/M15) from ~4.3M% down to ~380K% over 2 years — better, but still absurd, so leverage wasn't the main driver.

2. **Real bug: `BacktestEngine` didn't re-enter after a stop-loss within the same signal segment** (`backtest/engine.py`), while `SimulatedBroker` (paper trading) does. This meant the backtest let "always in market" strategies (MA crossover, MACD) sit out for free for the rest of any segment that got stopped out, even though the underlying signal still favored that direction — a systematic advantage backtesting had that paper trading never would. Fixed by making the engine re-enter same-bar after a stop, exactly matching `SimulatedBroker`'s behavior, so backtest results are now a fair preview of what paper trading will actually do. This is the fix that mattered more: combined with the leverage cap, MACD/M15 dropped to ~9,000% over 2 years.

**Still not fully trusted, and said so rather than declaring victory**: ~9,000% over 2 years for a strategy trading a synthetic random walk is still more edge than should exist on genuinely random data. I did not chase this further — it's very possibly an artifact of how the synthetic OHLC noise is constructed (never meant to be statistically realistic, only to exercise the pipeline), and real judgment on strategy quality has to wait for ticket 03 with real market data. Updated `tests/unit/backtest/test_engine.py` to cover the re-entry behavior (2 new/updated tests), full suite still green (50/50), and the 15-candidate backtest still runs in ~3s.
