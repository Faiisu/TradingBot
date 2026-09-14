import pandas as pd

from tradebot.indicators import atr, ema
from tradebot.strategies.base import DataRequirement, band_state_signals
from tradebot.timeframe import Timeframe


class AtrChannelBreakoutStrategy:
    supporting_data: tuple[DataRequirement, ...] = ()

    def __init__(self, timeframe: Timeframe, ema_period: int = 20, atr_period: int = 14, multiplier: float = 2.0):
        self.timeframe = timeframe
        self.ema_period = ema_period
        self.atr_period = atr_period
        self.multiplier = multiplier
        self.name = f"atr_channel_breakout_{ema_period}_{atr_period}_{multiplier}"

    def generate_signals(self, ohlcv: pd.DataFrame, supporting: dict[DataRequirement, pd.DataFrame] | None = None) -> pd.Series:
        close = ohlcv["close"]
        center = ema(close, self.ema_period)
        atr_values = atr(ohlcv["high"], ohlcv["low"], close, self.atr_period)
        upper = center + self.multiplier * atr_values
        lower = center - self.multiplier * atr_values
        return band_state_signals(close, upper, lower, center)
