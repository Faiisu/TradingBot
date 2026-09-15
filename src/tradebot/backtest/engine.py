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
            # A risk-control exit (fixed stop, trailing stop, or profit target) only ends this specific
            # trade, not the strategy's underlying directional view: if the signal is still the same
            # direction, re-enter immediately at the exit bar, matching SimulatedBroker's same-bar
            # re-entry (paper trading). Without this, a segment that exits early would sit out the rest
            # of a still-adverse (or, symmetrically, still-favorable) move for free — a systematic,
            # unrealistic advantage backtest-only would have over paper trading. This is a deliberate
            # extension of the pre-ticket-06 stop-loss-only re-entry rule to the two new exit reasons:
            # a trend that keeps running after a profit-target-out is expected to chain several
            # capped-size wins rather than sit out, which is what "bounding the winning side" should
            # look like for a still-intact trend, not one uncapped ride.
            entry_idx = start
            while entry_idx <= end:
                entry_price = close[entry_idx]
                atr_at_entry = atr_values[entry_idx]
                if np.isnan(entry_price) or np.isnan(atr_at_entry):
                    break

                stop = self.risk_controls.stop_price(entry_price, atr_at_entry, direction)
                target = self.risk_controls.profit_target_price(entry_price, atr_at_entry, direction)
                exit_idx = end
                exit_price = close[end]
                exit_reason = "signal_change"

                # Bounds the winning side the same way the fixed stop bounds the losing side (rule-set-
                # expansion phase-1 ticket 06): a trailing stop ratchets with the best price reached
                # since entry (never loosening) and/or a profit target caps at a fixed multiple of the
                # trade's own initial risk. Both are optional (RiskControls returns None when disabled,
                # making this identical to the pre-ticket-06 fixed-stop-only behavior); checked bar by
                # bar since the trailing level moves. When a bar's range could plausibly hit both the
                # stop and the target, the stop-loss is checked first — the risk-defining boundary wins
                # on the conservative side, since only OHLC (not tick data) is available to sequence them.
                current_stop = stop
                extreme = high[entry_idx] if direction == 1 else low[entry_idx]
                for i in range(entry_idx + 1, end + 1):
                    trailing = self.risk_controls.trailing_stop_price(entry_price, atr_at_entry, direction, extreme)
                    if trailing is not None:
                        current_stop = max(current_stop, trailing) if direction == 1 else min(current_stop, trailing)

                    stop_hit = (direction == 1 and low[i] <= current_stop) or (direction == -1 and high[i] >= current_stop)
                    target_hit = target is not None and (
                        (direction == 1 and high[i] >= target) or (direction == -1 and low[i] <= target)
                    )

                    if stop_hit:
                        exit_idx, exit_price = i, current_stop
                        exit_reason = "trailing_stop" if current_stop != stop else "stop_loss"
                        break
                    if target_hit:
                        exit_idx, exit_price, exit_reason = i, target, "profit_target"
                        break

                    extreme = max(extreme, high[i]) if direction == 1 else min(extreme, low[i])

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
                        stop_price=float(current_stop),
                        position_fraction=float(position_fraction),
                        cost_pct=float(cost_pct),
                        swap_pct=float(swap_pct),
                        pnl_pct=float(pnl_pct),
                        exit_reason=exit_reason,
                    )
                )

                if exit_reason == "signal_change":
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
