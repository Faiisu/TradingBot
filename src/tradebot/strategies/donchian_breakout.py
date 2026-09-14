import pandas as pd

from tradebot.indicators import donchian_channel
from tradebot.strategies.base import DataRequirement, channel_breakout_signals
from tradebot.timeframe import Timeframe


class DonchianBreakoutStrategy:
    supporting_data: tuple[DataRequirement, ...] = ()

    def __init__(self, timeframe: Timeframe, entry_period: int = 20, exit_period: int = 10):
        self.timeframe = timeframe
        self.entry_period = entry_period
        self.exit_period = exit_period
        self.name = f"donchian_breakout_{entry_period}_{exit_period}"

    def generate_signals(self, ohlcv: pd.DataFrame, supporting: dict[DataRequirement, pd.DataFrame] | None = None) -> pd.Series:
        entry_upper, entry_lower = donchian_channel(ohlcv["high"], ohlcv["low"], self.entry_period)
        exit_upper, exit_lower = donchian_channel(ohlcv["high"], ohlcv["low"], self.exit_period)
        return channel_breakout_signals(ohlcv["close"], entry_upper, entry_lower, exit_upper, exit_lower)
