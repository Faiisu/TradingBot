import pandas as pd

from tradebot.indicators import sma
from tradebot.strategies.base import DataRequirement
from tradebot.timeframe import Timeframe


class MaCrossoverStrategy:
    supporting_data: tuple[DataRequirement, ...] = ()

    def __init__(self, timeframe: Timeframe, fast: int = 20, slow: int = 50):
        self.timeframe = timeframe
        self.fast = fast
        self.slow = slow
        self.name = f"ma_crossover_{fast}_{slow}"

    def generate_signals(self, ohlcv: pd.DataFrame, supporting: dict[DataRequirement, pd.DataFrame] | None = None) -> pd.Series:
        close = ohlcv["close"]
        fast_ma = sma(close, self.fast)
        slow_ma = sma(close, self.slow)
        valid = fast_ma.notna() & slow_ma.notna()

        signal = pd.Series(0.0, index=close.index, name="signal")
        signal[valid & (fast_ma > slow_ma)] = 1
        signal[valid & (fast_ma <= slow_ma)] = -1
        return signal
