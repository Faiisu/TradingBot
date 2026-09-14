import numpy as np
import pandas as pd

from tradebot.backtest.result import BacktestResult
from tradebot.backtest.trade import Trade
from tradebot.indicators import atr
from tradebot.risk.risk_controls import RiskControls
from tradebot.strategies.base import DataRequirement, StrategyCandidate


def _find_segments(signal: np.ndarray) -> list[tuple[int, int, int]]:
    """Contiguous runs of a constant nonzero signal value: (start_idx, end_idx, direction)."""
    segments = []
    n = len(signal)
    i = 0
    while i < n:
        if signal[i] == 0:
            i += 1
            continue
        direction = int(signal[i])
        start = i
        j = i
        while j + 1 < n and signal[j + 1] == direction:
            j += 1
        segments.append((start, j, direction))
        i = j + 1
    return segments


class BacktestEngine:
    def __init__(self, risk_controls: RiskControls, initial_equity: float = 1.0, atr_period: int = 14):
        self.risk_controls = risk_controls
        self.initial_equity = initial_equity
        self.atr_period = atr_period

    def run(
        self,
        candidate: StrategyCandidate,
        ohlcv: pd.DataFrame,
        supporting: dict[DataRequirement, pd.DataFrame] | None = None,
    ) -> BacktestResult:
        signal = candidate.generate_signals(ohlcv, supporting).to_numpy()
        close = ohlcv["close"].to_numpy()
        low = ohlcv["low"].to_numpy()
        high = ohlcv["high"].to_numpy()
        atr_values = atr(ohlcv["high"], ohlcv["low"], ohlcv["close"], self.atr_period).to_numpy()

        trades: list[Trade] = []
        for start, end, direction in _find_segments(signal):
            # A stop-loss only ends this specific trade, not the strategy's underlying directional
            # view: if the signal is still the same direction, re-enter immediately at the stop-out
            # bar, matching SimulatedBroker's same-bar re-entry (paper trading). Without this, a
            # segment that gets stopped out early would sit out the rest of a still-adverse move for
            # free, which is a systematic, unrealistic advantage backtest-only would have over paper
            # trading.
            entry_idx = start
            while entry_idx <= end:
                entry_price = close[entry_idx]
                atr_at_entry = atr_values[entry_idx]
                if np.isnan(entry_price) or np.isnan(atr_at_entry):
                    break

                stop = self.risk_controls.stop_price(entry_price, atr_at_entry, direction)
                exit_idx = end
                exit_price = close[end]
                exit_reason = "signal_change"

                if entry_idx + 1 <= end:
                    if direction == 1:
                        hit_mask = low[entry_idx + 1 : end + 1] <= stop
                    else:
                        hit_mask = high[entry_idx + 1 : end + 1] >= stop
                    if hit_mask.any():
                        offset = int(np.argmax(hit_mask))
                        exit_idx = entry_idx + 1 + offset
                        exit_price = stop
                        exit_reason = "stop_loss"

                entry_time = ohlcv.index[entry_idx]
                exit_time = ohlcv.index[exit_idx]

                position_fraction = self.risk_controls.position_fraction(entry_price, atr_at_entry)
                cost_pct = self.risk_controls.cost_pct(entry_price) * position_fraction
                swap_pct = self.risk_controls.swap_pct(entry_price, direction, entry_time, exit_time) * position_fraction
                pnl_pct = direction * (exit_price / entry_price - 1) * position_fraction - cost_pct + swap_pct

                trades.append(
                    Trade(
                        direction=direction,
                        entry_time=entry_time,
                        exit_time=exit_time,
                        entry_price=float(entry_price),
                        exit_price=float(exit_price),
                        stop_price=float(stop),
                        position_fraction=float(position_fraction),
                        cost_pct=float(cost_pct),
                        swap_pct=float(swap_pct),
                        pnl_pct=float(pnl_pct),
                        exit_reason=exit_reason,
                    )
                )

                if exit_reason != "stop_loss":
                    break
                entry_idx = exit_idx

        equity_curve = pd.Series(index=ohlcv.index, dtype=float)
        equity_curve.iloc[0] = self.initial_equity
        running_equity = self.initial_equity
        for trade in trades:
            running_equity *= 1 + trade.pnl_pct
            equity_curve.loc[trade.exit_time] = running_equity
        equity_curve = equity_curve.ffill()

        drawdown_series = equity_curve / equity_curve.cummax() - 1

        return BacktestResult(
            candidate_name=candidate.name,
            timeframe=candidate.timeframe.value,
            trades=trades,
            equity_curve=equity_curve,
            drawdown_series=drawdown_series,
        )
