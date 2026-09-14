import numpy as np
import pandas as pd

from tradebot.strategies.supertrend import SupertrendStrategy
from tradebot.timeframe import Timeframe


def test_follows_the_trend_with_no_flat_state(trending_ohlcv):
    strategy = SupertrendStrategy(timeframe=Timeframe.H1, period=10, multiplier=3.0)
    signals = strategy.generate_signals(trending_ohlcv)

    valid = signals != 0  # 0 only appears during ATR warmup, never as a real "flat" state
    assert signals[valid].iloc[-1] == 1  # a steady uptrend ends in an uptrend
    assert set(signals[valid].unique()).issubset({1, -1})


def test_flips_direction_on_a_trend_reversal():
    up = np.linspace(100, 160, 100)
    down = np.linspace(160, 100, 100)
    close = np.concatenate([up, down])
    index = pd.date_range("2024-01-01", periods=len(close), freq="h")
    ohlcv = pd.DataFrame({"open": close, "high": close + 0.3, "low": close - 0.3, "close": close}, index=index)

    strategy = SupertrendStrategy(timeframe=Timeframe.H1, period=10, multiplier=3.0)
    signals = strategy.generate_signals(ohlcv)

    assert signals.iloc[90] == 1
    assert signals.iloc[-1] == -1


def test_name_encodes_period_and_multiplier():
    strategy = SupertrendStrategy(timeframe=Timeframe.H1, period=10, multiplier=3.0)
    assert strategy.name == "supertrend_10_3.0"
