import pandas as pd

from tradebot.indicators import donchian_channel
from tradebot.strategies.base import DataRequirement, channel_breakout_signals
from tradebot.timeframe import Timeframe


class VolumeConfirmedBreakoutStrategy:
    """Identical to DonchianBreakoutStrategy, except the breakout bar's tick volume must also exceed
    volume_multiplier x its volume_period-bar average — isolated as the only difference, so any gap
    between the two Rule Sets' results is attributable to volume."""

    supporting_data: tuple[DataRequirement, ...] = ()

    def __init__(
        self,
        timeframe: Timeframe,
        entry_period: int = 20,
        exit_period: int = 10,
        volume_period: int = 20,
        volume_multiplier: float = 1.5,
    ):
        self.timeframe = timeframe
        self.entry_period = entry_period
        self.exit_period = exit_period
        self.volume_period = volume_period
        self.volume_multiplier = volume_multiplier
        self.name = f"volume_confirmed_breakout_{entry_period}_{exit_period}"

    def generate_signals(self, ohlcv: pd.DataFrame, supporting: dict[DataRequirement, pd.DataFrame] | None = None) -> pd.Series:
        entry_upper, entry_lower = donchian_channel(ohlcv["high"], ohlcv["low"], self.entry_period)
        exit_upper, exit_lower = donchian_channel(ohlcv["high"], ohlcv["low"], self.exit_period)

        tick_volume = ohlcv["tick_volume"]
        average_volume = tick_volume.shift(1).rolling(window=self.volume_period).mean()
        entry_confirmed = tick_volume > self.volume_multiplier * average_volume

        return channel_breakout_signals(ohlcv["close"], entry_upper, entry_lower, exit_upper, exit_lower, entry_confirmed)
