import math
from datetime import datetime, timedelta

import pandas as pd

from tradebot.timeframe import TIMEFRAME_SECONDS, Timeframe, to_mt5_timeframe


class InsufficientBarCapacity(RuntimeError):
    pass


def ensure_bar_capacity(mt5_api, timeframes: list[Timeframe], num_years: int) -> None:
    """Refuses to fetch when the MT5 terminal's 'Max bars in chart' setting could cut history short.
    MT5 silently returns at most that many bars per symbol/timeframe, which looks exactly like the broker
    not keeping enough history — this is what truncated M5 to ~514 days before."""
    maxbars = mt5_api.terminal_info().maxbars
    for timeframe in timeframes:
        needed = math.ceil(num_years * 365 * 24 * 3600 / TIMEFRAME_SECONDS[timeframe])
        if needed > maxbars:
            raise InsufficientBarCapacity(
                f"MT5 'Max bars in chart' is {maxbars:,}, but {num_years} years of {timeframe.value} can need up to "
                f"{needed:,} bars. Set Tools → Options → Charts → Max bars in chart to Unlimited, restart the terminal, "
                f"then fetch again."
            )


def fetch_history(mt5_api, symbol: str, timeframe: Timeframe, date_from: datetime, date_to: datetime) -> pd.DataFrame:
    """Pulls bars in 90-day chunks (defensive against any per-call size limit), dedupes, and returns
    a DataFrame indexed by bar close time. May legitimately return less than [date_from, date_to] if
    the broker's server doesn't retain that much history for this symbol/timeframe — see report_coverage."""
    mt5_api.symbol_select(symbol, True)
    mt5_timeframe = to_mt5_timeframe(timeframe)

    chunks = []
    chunk_start = date_from
    while chunk_start < date_to:
        chunk_end = min(chunk_start + timedelta(days=90), date_to)
        rates = mt5_api.copy_rates_range(symbol, mt5_timeframe, chunk_start, chunk_end)
        if rates is not None and len(rates) > 0:
            chunks.append(pd.DataFrame(rates))
        chunk_start = chunk_end

    if not chunks:
        return pd.DataFrame(columns=["open", "high", "low", "close", "tick_volume", "spread"])

    df = pd.concat(chunks, ignore_index=True)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df = df.drop_duplicates(subset="time").sort_values("time").set_index("time")
    return df[["open", "high", "low", "close", "tick_volume", "spread"]]


def report_coverage(df: pd.DataFrame, date_from: datetime, date_to: datetime) -> dict:
    requested_days = (date_to - date_from).days
    if df.empty:
        return {
            "bars": 0,
            "actual_start": None,
            "actual_end": None,
            "requested_days": requested_days,
            "actual_days": 0,
        }
    actual_start, actual_end = df.index.min(), df.index.max()
    return {
        "bars": len(df),
        "actual_start": actual_start,
        "actual_end": actual_end,
        "requested_days": requested_days,
        "actual_days": (actual_end - actual_start).days,
    }
