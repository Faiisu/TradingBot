import pandas as pd

from tradebot.indicators import supertrend
from tradebot.strategies.base import DataRequirement
from tradebot.timeframe import Timeframe


class SupertrendStrategy:
    supporting_data: tuple[DataRequirement, ...] = ()

    def __init__(self, timeframe: Timeframe, period: int = 10, multiplier: float = 3.0):
        self.timeframe = timeframe
        self.period = period
        self.multiplier = multiplier
        self.name = f"supertrend_{period}_{multiplier}"

    def generate_signals(self, ohlcv: pd.DataFrame, supporting: dict[DataRequirement, pd.DataFrame] | None = None) -> pd.Series:
        direction = supertrend(ohlcv["high"], ohlcv["low"], ohlcv["close"], self.period, self.multiplier)
        return direction.fillna(0.0).rename("signal")
