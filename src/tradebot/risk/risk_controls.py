from dataclasses import dataclass

import pandas as pd

from tradebot.risk.position_sizing import position_fraction
from tradebot.risk.stop_loss import atr_stop_distance, stop_price
from tradebot.risk.swap import count_rollover_nights, swap_price


@dataclass(frozen=True)
class RiskControls:
    risk_pct_per_trade: float = 0.01
    atr_stop_multiplier: float = 2.0
    # Caps notional exposure at 0.2x of a candidate's own allocated capital per trade. The original 5.0
    # default (5x leverage) and the later 1.0 (no leverage) both still let 2*ATR-based stops be tight
    # enough, on real data, that this cap binds on 83-99.5% of bars across every Timeframe (H1 to M5) —
    # so almost every trade was sized at the cap rather than at the risk-based fraction the formula
    # intends, and stop-losses ended up costing far less than risk_pct_per_trade while signal-change
    # exits stayed unbounded. That asymmetry (tiny bounded losses vs. unbounded gains) compounded across
    # thousands of trades into implausible returns (e.g. macd_12_26_9 on M5: +57,042% at 2.09% max
    # drawdown). Lowering the cap to 0.2 shrinks every trade proportionally and was chosen as the
    # immediate mitigation; it does not remove the underlying asymmetry — bounding the winning side too
    # (a trailing stop or profit target) is the follow-up (see .scratch/phase-1-real-data-validation/
    # issues/06-bound-the-winning-side-of-trades.md).
    max_position_fraction: float = 0.2
    # Placeholder round-trip transaction cost in price points (spread + commission), until step 9
    # reads the real spread from MT5's symbol_info() for the connected Exness account.
    round_trip_cost_price: float = 0.30
    # Overnight holding (swap) cost, in points per night, per direction — 0 by default so existing
    # backtests/tests are unaffected. scripts/run_backtest.py passes real values read from MT5's
    # symbol_info() for XAUUSDm (asymmetric: costly to hold long, free to hold short, as of the date
    # fetched — real swap rates drift and should be re-checked periodically).
    swap_long_points: float = 0.0
    swap_short_points: float = 0.0
    point_value: float = 0.01

    def stop_distance(self, atr_at_entry: float) -> float:
        return atr_stop_distance(atr_at_entry, self.atr_stop_multiplier)

    def stop_price(self, entry_price: float, atr_at_entry: float, direction: int) -> float:
        return stop_price(entry_price, self.stop_distance(atr_at_entry), direction)

    def position_fraction(self, entry_price: float, atr_at_entry: float) -> float:
        return position_fraction(
            entry_price,
            self.stop_distance(atr_at_entry),
            self.risk_pct_per_trade,
            self.max_position_fraction,
        )

    def cost_pct(self, entry_price: float) -> float:
        return self.round_trip_cost_price / entry_price

    def swap_pct(self, entry_price: float, direction: int, entry_time: pd.Timestamp, exit_time: pd.Timestamp) -> float:
        points = self.swap_long_points if direction == 1 else self.swap_short_points
        nights = count_rollover_nights(entry_time, exit_time)
        return swap_price(points, self.point_value, nights) / entry_price
