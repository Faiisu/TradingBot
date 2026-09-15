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
    # Bounds the winning side of a trade the same way the ATR stop already bounds the losing side —
    # see .scratch/phase-1-real-data-validation/issues/06-bound-the-winning-side-of-trades.md. Both
    # None by default (disabled, byte-identical to pre-ticket-06 behavior); either or both can be set.
    # trailing_stop_multiplier: a chandelier-style stop that ratchets with the highest high (long) /
    # lowest low (short) seen since entry, never loosening — caps giveback from a move's peak without
    # hard-capping total profit. profit_target_r_multiple: a hard cap at N times the trade's own initial
    # risk (1R = atr_stop_multiplier * ATR at entry, the same distance the fixed stop-loss uses).
    trailing_stop_multiplier: float | None = None
    profit_target_r_multiple: float | None = None
    # Round-trip transaction cost in price points for the Exness Standard (commission-free) account.
    # XAUUSD typical spread on Standard/Standard Cent sits in the 16–35 pip range ($0.16–$0.35,
    # where 1 pip = $0.01 for XAUUSDm); 0.30 ($0.30 = 30 pips) is a conservative mid-range
    # estimate. The "spreads starting from 0.2 pips" advertised by Exness refers to major forex
    # pairs (e.g. EURUSD), not gold.
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

    def trailing_stop_price(self, entry_price: float, atr_at_entry: float, direction: int, extreme_price: float) -> float | None:
        """None when disabled. Otherwise the chandelier stop for `extreme_price` (the highest high (long)
        or lowest low (short) reached since entry) — the same ATR distance the fixed stop-loss uses,
        trailing from the extreme instead of from entry_price."""
        if self.trailing_stop_multiplier is None:
            return None
        distance = atr_stop_distance(atr_at_entry, self.trailing_stop_multiplier)
        return stop_price(extreme_price, distance, direction)

    def profit_target_price(self, entry_price: float, atr_at_entry: float, direction: int) -> float | None:
        """None when disabled. Otherwise entry_price + direction * profit_target_r_multiple * 1R, where
        1R is the same initial risk distance (atr_stop_multiplier * ATR) the fixed stop-loss uses."""
        if self.profit_target_r_multiple is None:
            return None
        one_r = self.stop_distance(atr_at_entry)
        return entry_price + direction * self.profit_target_r_multiple * one_r

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
