import pandas as pd

from tradebot.indicators import adx_dmi
from tradebot.strategies.base import DataRequirement
from tradebot.timeframe import Timeframe


class AdxDmiStrategy:
    supporting_data: tuple[DataRequirement, ...] = ()

    def __init__(self, timeframe: Timeframe, period: int = 14, threshold: float = 25.0):
        self.timeframe = timeframe
        self.period = period
        self.threshold = threshold
        self.name = f"adx_dmi_{period}"

    def generate_signals(self, ohlcv: pd.DataFrame, supporting: dict[DataRequirement, pd.DataFrame] | None = None) -> pd.Series:
        adx, plus_di, minus_di = adx_dmi(ohlcv["high"], ohlcv["low"], ohlcv["close"], self.period)
        strong = adx > self.threshold

        signal = pd.Series(0.0, index=ohlcv.index, name="signal")
        signal[strong & (plus_di > minus_di)] = 1
        signal[strong & (plus_di <= minus_di)] = -1
        return signal
