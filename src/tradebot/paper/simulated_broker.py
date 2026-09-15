from dataclasses import dataclass

import pandas as pd

from tradebot.backtest.trade import Trade
from tradebot.risk.risk_controls import RiskControls


@dataclass
class OpenPosition:
    direction: int
    entry_price: float
    entry_time: pd.Timestamp
    stop_price: float  # current effective stop — ratchets when a trailing stop is configured
    initial_stop_price: float  # the original fixed stop from entry, to label trailing_stop vs stop_loss
    position_fraction: float
    atr_at_entry: float  # frozen at entry, same convention BacktestEngine uses for the trailing distance
    extreme_price: float  # highest high (long) / lowest low (short) seen since entry
    target_price: float | None  # fixed profit target, None if disabled


class SimulatedBroker:
    """Simulates fills against real/live bars for one Ensemble member. Never places a real order —
    every decision here is bookkeeping only, mirroring BacktestEngine's per-segment logic but applied
    incrementally, one closed bar at a time, as paper trading streams them in."""

    def __init__(self, risk_controls: RiskControls, initial_equity: float, atr_period: int = 14):
        self.risk_controls = risk_controls
        self.initial_equity = initial_equity
        self.equity = initial_equity
        self.atr_period = atr_period
        self.position: OpenPosition | None = None
        self.trades: list[Trade] = []

    def on_bar(self, time: pd.Timestamp, open_: float, high: float, low: float, close: float, signal: float, atr_at_bar: float) -> None:
        direction = int(signal)

        if self.position is not None:
            position = self.position
            # Bounds the winning side the same way the fixed stop bounds the losing side (rule-set-
            # expansion phase-1 ticket 06). The stop level effective for THIS bar reflects the extreme
            # through the PREVIOUS bar only (no look-ahead); the extreme itself is only updated with
            # this bar's own high/low afterward, for the next bar's check — mirroring BacktestEngine's
            # per-bar trailing loop exactly, so Paper Trading and Backtest never diverge.
            current_stop = position.stop_price
            trailing = self.risk_controls.trailing_stop_price(position.entry_price, position.atr_at_entry, position.direction, position.extreme_price)
            if trailing is not None:
                current_stop = max(current_stop, trailing) if position.direction == 1 else min(current_stop, trailing)

            stop_hit = (position.direction == 1 and low <= current_stop) or (position.direction == -1 and high >= current_stop)
            target_hit = position.target_price is not None and (
                (position.direction == 1 and high >= position.target_price) or (position.direction == -1 and low <= position.target_price)
            )

            if stop_hit:
                reason = "trailing_stop" if current_stop != position.initial_stop_price else "stop_loss"
                position.stop_price = current_stop
                self._close(exit_price=current_stop, exit_time=time, reason=reason)
            elif target_hit:
                self._close(exit_price=position.target_price, exit_time=time, reason="profit_target")
            elif direction != position.direction:
                self._close(exit_price=close, exit_time=time, reason="signal_change")
            else:
                position.stop_price = current_stop
                position.extreme_price = max(position.extreme_price, high) if position.direction == 1 else min(position.extreme_price, low)

        if self.position is None and direction != 0 and not pd.isna(atr_at_bar):
            self._open(direction=direction, entry_price=close, entry_time=time, atr_at_entry=atr_at_bar, high=high, low=low)

    def _open(self, direction: int, entry_price: float, entry_time: pd.Timestamp, atr_at_entry: float, high: float, low: float) -> None:
        stop = self.risk_controls.stop_price(entry_price, atr_at_entry, direction)
        target = self.risk_controls.profit_target_price(entry_price, atr_at_entry, direction)
        fraction = self.risk_controls.position_fraction(entry_price, atr_at_entry)
        self.position = OpenPosition(
            direction=direction,
            entry_price=entry_price,
            entry_time=entry_time,
            stop_price=stop,
            initial_stop_price=stop,
            position_fraction=fraction,
            atr_at_entry=atr_at_entry,
            extreme_price=high if direction == 1 else low,
            target_price=target,
        )

    def _close(self, exit_price: float, exit_time: pd.Timestamp, reason: str) -> None:
        position = self.position
        cost_pct = self.risk_controls.cost_pct(position.entry_price) * position.position_fraction
        swap_pct = (
            self.risk_controls.swap_pct(position.entry_price, position.direction, position.entry_time, exit_time)
            * position.position_fraction
        )
        pnl_pct = (
            position.direction * (exit_price / position.entry_price - 1) * position.position_fraction
            - cost_pct
            + swap_pct
        )
        self.equity *= 1 + pnl_pct

        self.trades.append(
            Trade(
                direction=position.direction,
                entry_time=position.entry_time,
                exit_time=exit_time,
                entry_price=position.entry_price,
                exit_price=exit_price,
                stop_price=position.stop_price,
                position_fraction=position.position_fraction,
                cost_pct=cost_pct,
                swap_pct=swap_pct,
                pnl_pct=pnl_pct,
                exit_reason=reason,
            )
        )
        self.position = None
