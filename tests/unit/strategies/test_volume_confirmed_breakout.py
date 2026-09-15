import pandas as pd

from tradebot.strategies.volume_confirmed_breakout import VolumeConfirmedBreakoutStrategy
from tradebot.timeframe import Timeframe


def _ohlcv(closes: list[float], tick_volumes: list[float]) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=len(closes), freq="h")
    close = pd.Series(closes, index=index)
    return pd.DataFrame(
        {"open": close, "high": close, "low": close, "close": close, "tick_volume": tick_volumes}, index=index
    )


def test_breakout_is_confirmed_when_volume_exceeds_1_5x_its_20_bar_average():
    # 25 flat bars at 100 with volume 100 (warms up both the price channel and the 20-bar volume
    # average at 100), then a breakout to 110 on 3x volume
    closes = [100.0] * 25 + [110.0]
    volumes = [100.0] * 25 + [300.0]
    strategy = VolumeConfirmedBreakoutStrategy(timeframe=Timeframe.H1)
    signals = strategy.generate_signals(_ohlcv(closes, volumes))

    assert signals.iloc[25] == 1


def test_breakout_is_rejected_when_volume_does_not_exceed_1_5x_its_20_bar_average():
    closes = [100.0] * 25 + [110.0]
    volumes = [100.0] * 25 + [110.0]  # 1.1x average -> below the 1.5x threshold
    strategy = VolumeConfirmedBreakoutStrategy(timeframe=Timeframe.H1)
    signals = strategy.generate_signals(_ohlcv(closes, volumes))

    assert signals.iloc[25] == 0


def test_it_is_otherwise_identical_to_donchian_breakout():
    # same entry/exit channel behavior as Donchian: only the entry bar needs confirmed volume, since
    # exits are never volume-gated
    closes = [100.0] * 25 + [110.0] + [105.0] * 9 + [102.0]
    volumes = [100.0] * 25 + [300.0] + [100.0] * 10
    strategy = VolumeConfirmedBreakoutStrategy(timeframe=Timeframe.H1)
    signals = strategy.generate_signals(_ohlcv(closes, volumes))

    assert signals.iloc[25] == 1
    assert signals.iloc[30] == 1
    assert signals.iloc[-1] == 0


def test_name_encodes_entry_and_exit_periods():
    strategy = VolumeConfirmedBreakoutStrategy(timeframe=Timeframe.H1, entry_period=20, exit_period=10)
    assert strategy.name == "volume_confirmed_breakout_20_10"
