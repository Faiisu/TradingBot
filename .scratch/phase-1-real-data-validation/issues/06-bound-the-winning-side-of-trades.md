# 06: Bound the winning side of trades (deferred half of the risk-control fix)

**What to build:** Ticket 04 found that lowering `max_position_fraction` (5.0 → 1.0 → 0.2, this ticket's predecessor) only shrinks every trade proportionally — it does not fix the underlying asymmetry between stop-losses (bounded tight by `2×ATR`) and signal-change exits (unbounded, ride the move as far as it goes before the Rule Set's own signal reverses). That asymmetry, not leverage, is the main reason backtest returns still compound to implausible levels even after ticket 04's leverage fixes. Add a way to bound the winning side too — a trailing stop and/or a profit target, evaluated the same way the ATR stop is today — and confirm it visibly reduces the gap between backtest returns and something a real trader would recognize.

**Blocked by:** None technically (RiskControls and BacktestEngine are already in place), but should follow the Walk-Forward Validation work (rule-set-expansion tickets 02–03) so this can be judged out of sample rather than by eye on the same data used to design it.

**Status:** ready-for-agent

- [ ] A trailing-stop or profit-target mechanism exists in `RiskControls`/`BacktestEngine`, applied uniformly to every Strategy Candidate like the ATR stop is today
- [ ] Re-running the Backtest shows a visibly smaller gap between average winning-trade size and average losing-trade size for the same candidates checked in ticket 04 (e.g. `macd_12_26_9` on M5)
- [ ] Max drawdown for top candidates moves closer to a plausible range for their return (a rule of thumb, not a hard number: real systematic strategies rarely sustain a return many multiples of their max drawdown for thousands of trades)
- [ ] The one-per-(Rule Set, Entry Timeframe) Ensemble selection and Walk-Forward Validation both still pass with this control in place
- [ ] The test suite stays green

## Context from ticket 04's follow-up investigation

On real data, `2×ATR/price` came in under the 1% `risk_pct_per_trade` target on the large majority of bars at every Timeframe (H1 83%, M30 95%, M15 98%, M5 99.5%), so `max_position_fraction` was capping position size on nearly every trade rather than the risk-based formula doing so. That made realized stop-loss size much smaller than the configured 1% almost all the time, while signal-change exits were never bounded at all. Lowering `max_position_fraction` to 0.2 (this ticket's predecessor, done) shrank every trade proportionally — `macd_12_26_9` on M5 went from +57,042% return / 2.09% max drawdown to +260.55% / 0.64% — but a sub-1% max drawdown across ~12,000 trades over 2 years is still smoother than real execution would produce. Bounding gains the same way losses already are is the fix this ticket exists to make.
