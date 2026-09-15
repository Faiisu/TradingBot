import pandas as pd

from tradebot.strategies.asian_range_breakout import AsianRangeBreakoutStrategy
from tradebot.timeframe import Timeframe


def _asian_ohlcv() -> pd.DataFrame:
    """Two UTC days of hourly bars exercising every boundary the ticket calls out:
    day 1 — a 00:00-07:00 range of [95, 105] (high spikes at h03, low dips at h05), a long entry at
    07:00, a flip to short at h10, an extreme close at h16 that must NOT re-flip (entry window closed
    at 16:00), and a forced-flat at 21:00 regardless of price.
    day 2 — an independent 00:00-07:00 range of [98, 102] (high at h02, low at h04); closes inside the
    range at 07:00/08:00 open no position; a breakout at h09 finally enters long."""
    index = pd.date_range("2024-01-01 00:00", periods=34, freq="h")
    high = pd.Series(100.0, index=index)
    low = pd.Series(100.0, index=index)
    close = pd.Series(100.0, index=index)

    high.iloc[3] = 105.0  # day 1 range-high source (00:00-07:00 session)
    low.iloc[5] = 95.0  # day 1 range-low source

    close.iloc[7] = 106.0  # day1 07:00: breaks range high -> long
    close.iloc[8] = 104.0
    close.iloc[9] = 104.0
    close.iloc[10] = 90.0  # day1 10:00: breaks range low -> flips short
    for h in range(11, 16):
        close.iloc[h] = 93.0
    close.iloc[16] = 110.0  # day1 16:00: entry window just closed -> must NOT flip back to long
    close.iloc[17] = 110.0
    for h in range(18, 21):
        close.iloc[h] = 93.0
    close.iloc[21] = 999.0  # day1 21:00: forced flat regardless of an extreme close
    close.iloc[22] = 999.0
    close.iloc[23] = 999.0

    high.iloc[26] = 102.0  # day2 range-high source (h02)
    low.iloc[28] = 98.0  # day2 range-low source (h04)
    close.iloc[31] = 99.0  # day2 07:00: inside [98, 102] -> stays flat
    close.iloc[32] = 101.0  # day2 08:00: inside range -> stays flat
    close.iloc[33] = 103.0  # day2 09:00: breaks the day's own range high -> long

    return pd.DataFrame({"open": close, "high": high, "low": low, "close": close}, index=index)


def test_boundaries_at_07_16_and_21_utc_across_two_independent_days():
    strategy = AsianRangeBreakoutStrategy(timeframe=Timeframe.H1)
    signals = strategy.generate_signals(_asian_ohlcv())

    expected = [0] * 7 + [1, 1, 1] + [-1] * 11 + [0] * 12 + [1]
    assert list(signals) == expected


def test_never_opens_a_position_outside_07_00_16_00_utc():
    strategy = AsianRangeBreakoutStrategy(timeframe=Timeframe.H1)
    ohlcv = _asian_ohlcv()
    signals = strategy.generate_signals(ohlcv)

    outside_window = (ohlcv.index.hour < 7) | (ohlcv.index.hour >= 16)
    was_flat_before = signals.shift(1).fillna(0) == 0
    opened_outside_window = outside_window & was_flat_before & (signals != 0)
    assert not opened_outside_window.any()


def test_never_holds_a_position_past_21_00_utc():
    strategy = AsianRangeBreakoutStrategy(timeframe=Timeframe.H1)
    ohlcv = _asian_ohlcv()
    signals = strategy.generate_signals(ohlcv)

    at_or_after_21 = ohlcv.index.hour >= 21
    assert (signals[at_or_after_21] == 0).all()


def test_name_has_no_tunable_parameters():
    strategy = AsianRangeBreakoutStrategy(timeframe=Timeframe.H1)
    assert strategy.name == "asian_range_breakout"
