import pandas as pd

from tradebot.indicators import macd
from tradebot.timeframe import Timeframe


class MacdStrategy:
    def __init__(self, timeframe: Timeframe, fast: int = 12, slow: int = 26, signal_period: int = 9):
        self.timeframe = timeframe
        self.fast = fast
        self.slow = slow
        self.signal_period = signal_period
        self.name = f"macd_{fast}_{slow}_{signal_period}"

    def generate_signals(self, ohlcv: pd.DataFrame, htf_ohlcv: pd.DataFrame | None = None) -> pd.Series:
        close = ohlcv["close"]
        macd_line, signal_line = macd(close, self.fast, self.slow, self.signal_period)
        valid = macd_line.notna() & signal_line.notna()

        signal = pd.Series(0.0, index=close.index, name="signal")
        signal[valid & (macd_line > signal_line)] = 1
        signal[valid & (macd_line <= signal_line)] = -1
        return signal
