import numpy as np
import pandas as pd

from tradebot.indicators import ema
from tradebot.strategies.base import DataRequirement, StrategyCandidate, align_htf_signal
from tradebot.timeframe import Timeframe


def ema_slope_filter(htf_ohlcv: pd.DataFrame, period: int = 50, lookback: int = 5) -> pd.Series:
    """Trend Filter: EMA(period) rising vs. its value `lookback` bars ago -> 1 (up) / -1 (down),
    0 during warmup. Same warmup convention as ma_crossover.py's always-in-market state."""
    close = htf_ohlcv["close"]
    ema_values = ema(close, period)
    prior = ema_values.shift(lookback)
    valid = ema_values.notna() & prior.notna()

    signal = pd.Series(0.0, index=close.index, name="signal")
    signal[valid & (ema_values > prior)] = 1
    signal[valid & (ema_values <= prior)] = -1
    return signal


class MtfCandidate:
    """Wraps an entry-timeframe Strategy Candidate with a higher-timeframe Trend Filter: the entry
    signal is only kept where it agrees in direction with the aligned filter, forced flat otherwise."""

    def __init__(self, entry_strategy: StrategyCandidate, filter_fn, filter_name: str, filter_timeframe: Timeframe):
        self.entry_strategy = entry_strategy
        self.filter_fn = filter_fn
        self.filter_name = filter_name
        self.filter_timeframe = filter_timeframe
        self.timeframe = entry_strategy.timeframe
        self.name = f"{entry_strategy.name}_mtf_{filter_name}_{filter_timeframe.value}filter"
        self._requirement = DataRequirement(timeframe=filter_timeframe)
        self.supporting_data = (self._requirement,)

    def generate_signals(self, ohlcv: pd.DataFrame, supporting: dict[DataRequirement, pd.DataFrame] | None = None) -> pd.Series:
        htf_ohlcv = (supporting or {}).get(self._requirement)
        if htf_ohlcv is None:
            raise ValueError(f"{self.name} requires its {self.filter_timeframe.value} Trend Filter data in `supporting`")

        entry_signal = self.entry_strategy.generate_signals(ohlcv)
        htf_trend = self.filter_fn(htf_ohlcv)
        aligned_trend = align_htf_signal(htf_trend, ohlcv.index)

        return entry_signal.where(entry_signal == aligned_trend, 0.0)
