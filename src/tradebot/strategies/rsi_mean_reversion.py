import pandas as pd

from tradebot.indicators import rsi
from tradebot.strategies.base import DataRequirement, threshold_reversion_signals
from tradebot.timeframe import Timeframe


class RsiMeanReversionStrategy:
    supporting_data: tuple[DataRequirement, ...] = ()

    def __init__(self, timeframe: Timeframe, period: int = 14, oversold: float = 30, overbought: float = 70):
        self.timeframe = timeframe
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.name = f"rsi_mean_reversion_{period}"

    def generate_signals(self, ohlcv: pd.DataFrame, supporting: dict[DataRequirement, pd.DataFrame] | None = None) -> pd.Series:
        rsi_values = rsi(ohlcv["close"], self.period)
        return threshold_reversion_signals(rsi_values, self.oversold, self.overbought)
