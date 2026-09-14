import pandas as pd

from tradebot.indicators import bollinger_bands
from tradebot.strategies.base import DataRequirement, band_state_signals
from tradebot.timeframe import Timeframe


class BollingerBreakoutStrategy:
    supporting_data: tuple[DataRequirement, ...] = ()

    def __init__(self, timeframe: Timeframe, period: int = 20, num_std: float = 2.0):
        self.timeframe = timeframe
        self.period = period
        self.num_std = num_std
        self.name = f"bollinger_breakout_{period}_{num_std}"

    def generate_signals(self, ohlcv: pd.DataFrame, supporting: dict[DataRequirement, pd.DataFrame] | None = None) -> pd.Series:
        close = ohlcv["close"]
        upper, middle, lower = bollinger_bands(close, self.period, self.num_std)
        return band_state_signals(close, upper, lower, middle)
