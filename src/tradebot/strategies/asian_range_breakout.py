from datetime import time

import numpy as np
import pandas as pd

from tradebot.strategies.base import DataRequirement
from tradebot.timeframe import Timeframe

SESSION_START = time(0, 0)
SESSION_END = time(7, 0)  # exclusive: the range never includes its own entry-window bars
ENTRY_WINDOW_END = time(16, 0)  # exclusive: no new entries or flips from here on
FORCED_FLAT_AT = time(21, 0)  # inclusive: flat from this bar onward, until the next day's range


class AsianRangeBreakoutStrategy:
    """Fixed UTC session times, no daylight-saving adjustment — broker server time is already UTC
    (see CONTEXT.md). The 00:00-07:00 range is known in full before the entry window opens at 07:00,
    so there is no lookahead even though every bar of a day carries that day's fixed range value."""

    supporting_data: tuple[DataRequirement, ...] = ()

    def __init__(self, timeframe: Timeframe):
        self.timeframe = timeframe
        self.name = "asian_range_breakout"

    def generate_signals(self, ohlcv: pd.DataFrame, supporting: dict[DataRequirement, pd.DataFrame] | None = None) -> pd.Series:
        index = ohlcv.index
        times = index.time
        day = index.normalize()

        in_session = (times >= SESSION_START) & (times < SESSION_END)
        in_entry_window = (times >= SESSION_END) & (times < ENTRY_WINDOW_END)
        forced_flat = times >= FORCED_FLAT_AT

        session_high_by_day = ohlcv["high"].where(in_session).groupby(day).max()
        session_low_by_day = ohlcv["low"].where(in_session).groupby(day).min()
        range_high = pd.Series(day, index=index).map(session_high_by_day).to_numpy()
        range_low = pd.Series(day, index=index).map(session_low_by_day).to_numpy()

        close_v = ohlcv["close"].to_numpy()
        signals = np.zeros(len(close_v))
        state = 0
        for i in range(len(close_v)):
            if forced_flat[i]:
                state = 0
            elif in_entry_window[i] and not np.isnan(range_high[i]) and not np.isnan(range_low[i]):
                if close_v[i] > range_high[i]:
                    state = 1
                elif close_v[i] < range_low[i]:
                    state = -1
            signals[i] = state
        return pd.Series(signals, index=index, name="signal")
