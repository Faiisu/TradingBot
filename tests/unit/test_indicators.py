import numpy as np
import pandas as pd

from tradebot.indicators import atr, bollinger_bands, ema, macd, rsi, sma


def test_sma_matches_manual_average():
    close = pd.Series([1, 2, 3, 4, 5], dtype=float)
    result = sma(close, period=3)
    assert np.isnan(result.iloc[1])
    assert result.iloc[2] == 2.0
    assert result.iloc[4] == 4.0


def test_ema_reacts_faster_than_sma_to_a_jump():
    close = pd.Series([100.0] * 20 + [200.0] * 5)
    sma_result = sma(close, period=10)
    ema_result = ema(close, period=10)
    assert ema_result.iloc[-1] > sma_result.iloc[-1]


def test_rsi_bounds_and_extremes(oscillating_ohlcv):
    result = rsi(oscillating_ohlcv["close"], period=14).dropna()
    assert (result >= 0).all() and (result <= 100).all()
    assert result.max() > 70
    assert result.min() < 30


def test_macd_zero_on_flat_series(flat_ohlcv):
    macd_line, signal_line = macd(flat_ohlcv["close"])
    assert np.allclose(macd_line.dropna(), 0.0)
    assert np.allclose(signal_line.dropna(), 0.0)


def test_bollinger_band_ordering(trending_ohlcv):
    upper, middle, lower = bollinger_bands(trending_ohlcv["close"], period=20)
    valid = upper.notna()
    assert (upper[valid] >= middle[valid]).all()
    assert (middle[valid] >= lower[valid]).all()


def test_atr_non_negative(trending_ohlcv):
    result = atr(trending_ohlcv["high"], trending_ohlcv["low"], trending_ohlcv["close"], period=14).dropna()
    assert (result >= 0).all()
