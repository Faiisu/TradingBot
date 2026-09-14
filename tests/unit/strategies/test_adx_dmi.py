import numpy as np
import pandas as pd

from tradebot.strategies.adx_dmi import AdxDmiStrategy
from tradebot.timeframe import Timeframe


def test_goes_long_when_adx_is_strong_and_plus_di_leads(trending_ohlcv):
    strategy = AdxDmiStrategy(timeframe=Timeframe.H1, period=14, threshold=25)
    signals = strategy.generate_signals(trending_ohlcv)

    assert signals.iloc[-1] == 1  # a steady uptrend: strong ADX, +DI above -DI


def test_goes_short_when_adx_is_strong_and_minus_di_leads():
    close = np.linspace(160, 100, 200)  # steady downtrend: -DI should dominate
    index = pd.date_range("2024-01-01", periods=len(close), freq="h")
    ohlcv = pd.DataFrame({"open": close, "high": close + 0.05, "low": close - 0.05, "close": close}, index=index)

    strategy = AdxDmiStrategy(timeframe=Timeframe.H1, period=14, threshold=25)
    signals = strategy.generate_signals(ohlcv)

    assert signals.iloc[-1] == -1


def test_flat_while_adx_is_at_or_below_the_threshold(flat_ohlcv):
    strategy = AdxDmiStrategy(timeframe=Timeframe.H1, period=14, threshold=25)
    signals = strategy.generate_signals(flat_ohlcv)

    assert (signals == 0).all()  # a flat series never develops directional strength


def test_name_encodes_the_period():
    strategy = AdxDmiStrategy(timeframe=Timeframe.H1, period=14)
    assert strategy.name == "adx_dmi_14"
