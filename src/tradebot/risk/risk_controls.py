from dataclasses import dataclass

import pandas as pd

from tradebot.risk.position_sizing import position_fraction
from tradebot.risk.stop_loss import atr_stop_distance, stop_price
from tradebot.risk.swap import count_rollover_nights, swap_price


@dataclass(frozen=True)
class RiskControls:
    risk_pct_per_trade: float = 0.01
    atr_stop_multiplier: float = 2.0
    # Caps notional exposure at 1x equity (no leverage) by default. The original 5.0 default let a
    # tight-stop trade take on 5x leveraged exposure, which combined with thousands of trades over a
    # 2-year backtest compounded into unrealistic (millions-of-percent) returns. Revisit once real
    # trade counts/frequency are known from real MT5 data.
    max_position_fraction: float = 1.0
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
