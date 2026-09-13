from typing import Protocol

import numpy as np
import pandas as pd

from tradebot.timeframe import Timeframe


class StrategyCandidate(Protocol):
    name: str
    timeframe: Timeframe

    def generate_signals(self, ohlcv: pd.DataFrame, htf_ohlcv: pd.DataFrame | None = None) -> pd.Series:
        """Target position state per bar: -1 (short), 0 (flat), 1 (long). htf_ohlcv is only used by
        MTF Candidates (see strategies/mtf.py); single-timeframe candidates ignore it."""
        ...


def align_htf_signal(htf_signal: pd.Series, entry_index: pd.DatetimeIndex) -> pd.Series:
    """Aligns a higher-timeframe signal onto a lower-timeframe (entry) index without look-ahead: each
    entry bar gets the most recent htf_signal value at-or-before its own timestamp, never a future one.
    Entry bars before the first htf bar closes get NaN (no filter opinion yet)."""
    htf_sorted = htf_signal.sort_index()
    htf_df = pd.DataFrame({"time": htf_sorted.index, "htf": htf_sorted.to_numpy()})
    entry_df = pd.DataFrame({"time": entry_index})
    merged = pd.merge_asof(entry_df, htf_df, on="time", direction="backward")
    return merged.set_index("time")["htf"]


def band_state_signals(close: pd.Series, upper: pd.Series, lower: pd.Series, middle: pd.Series) -> pd.Series:
    """Stateful breakout signal: enter long/short on a band breakout, stay until price recrosses the middle line."""
    signals = np.zeros(len(close))
    state = 0
    close_v, upper_v, lower_v, middle_v = close.to_numpy(), upper.to_numpy(), lower.to_numpy(), middle.to_numpy()
    for i in range(len(close_v)):
        c, u, l, m = close_v[i], upper_v[i], lower_v[i], middle_v[i]
        if np.isnan(u) or np.isnan(l) or np.isnan(m):
            signals[i] = 0
            continue
        if c > u:
            state = 1
        elif c < l:
            state = -1
        elif state == 1 and c <= m:
            state = 0
        elif state == -1 and c >= m:
            state = 0
        signals[i] = state
    return pd.Series(signals, index=close.index, name="signal")
