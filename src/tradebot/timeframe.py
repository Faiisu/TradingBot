from enum import Enum


class Timeframe(str, Enum):
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"


def to_mt5_timeframe(timeframe: Timeframe):
    import MetaTrader5 as mt5

    return {
        Timeframe.M5: mt5.TIMEFRAME_M5,
        Timeframe.M15: mt5.TIMEFRAME_M15,
        Timeframe.M30: mt5.TIMEFRAME_M30,
        Timeframe.H1: mt5.TIMEFRAME_H1,
    }[timeframe]
