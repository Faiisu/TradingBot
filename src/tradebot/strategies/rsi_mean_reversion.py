import numpy as np
import pandas as pd

from tradebot.indicators import rsi
from tradebot.timeframe import Timeframe


class RsiMeanReversionStrategy:
    def __init__(self, timeframe: Timeframe, period: int = 14, oversold: float = 30, overbought: float = 70):
        self.timeframe = timeframe
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self.name = f"rsi_mean_reversion_{period}"

    def generate_signals(self, ohlcv: pd.DataFrame, htf_ohlcv: pd.DataFrame | None = None) -> pd.Series:
        close = ohlcv["close"]
        rsi_values = rsi(close, self.period).to_numpy()

        signals = np.zeros(len(close))
        state = 0
        for i in range(len(rsi_values)):
            r = rsi_values[i]
            if np.isnan(r):
                signals[i] = 0
                continue
            if r < self.oversold:
                state = 1
            elif r > self.overbought:
                state = -1
            elif state == 1 and r >= 50:
                state = 0
            elif state == -1 and r <= 50:
                state = 0
            signals[i] = state
        return pd.Series(signals, index=close.index, name="signal")
