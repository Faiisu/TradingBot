from dataclasses import dataclass

import pandas as pd

from tradebot.backtest.trade import Trade
from tradebot.risk.risk_controls import RiskControls


@dataclass
class OpenPosition:
    direction: int
    entry_price: float
    entry_time: pd.Timestamp
    stop_price: float
    position_fraction: float


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
            stop_hit = (self.position.direction == 1 and low <= self.position.stop_price) or (
                self.position.direction == -1 and high >= self.position.stop_price
            )
            if stop_hit:
                self._close(exit_price=self.position.stop_price, exit_time=time, reason="stop_loss")
            elif direction != self.position.direction:
                self._close(exit_price=close, exit_time=time, reason="signal_change")

        if self.position is None and direction != 0 and not pd.isna(atr_at_bar):
            self._open(direction=direction, entry_price=close, entry_time=time, atr_at_entry=atr_at_bar)

    def _open(self, direction: int, entry_price: float, entry_time: pd.Timestamp, atr_at_entry: float) -> None:
        stop = self.risk_controls.stop_price(entry_price, atr_at_entry, direction)
        fraction = self.risk_controls.position_fraction(entry_price, atr_at_entry)
        self.position = OpenPosition(
            direction=direction,
            entry_price=entry_price,
            entry_time=entry_time,
            stop_price=stop,
            position_fraction=fraction,
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
