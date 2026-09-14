import numpy as np
import pandas as pd

from tradebot.indicators import adx_dmi, atr, bollinger_bands, donchian_channel, ema, macd, rsi, sma, supertrend


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


def test_donchian_channel_only_looks_at_prior_bars():
    high = pd.Series([10.0, 12.0, 11.0, 9.0, 20.0, 8.0])
    low = pd.Series([5.0, 6.0, 5.5, 4.0, 4.5, 3.0])
    upper, lower = donchian_channel(high, low, period=3)

    # at index 4, the prior 3 bars are indices 1-3 (highs 12,11,9 / lows 6,5.5,4) — bar 4's own
    # high of 20 must NOT be included, or a breakout could never register against its own bar
    assert upper.iloc[4] == 12.0
    assert lower.iloc[4] == 4.0


def test_supertrend_direction_matches_a_clean_trend_then_reversal():
    up = np.linspace(100, 160, 100)
    down = np.linspace(160, 100, 100)
    close = np.concatenate([up, down])
    index = pd.date_range("2024-01-01", periods=len(close), freq="h")
    high = pd.Series(close + 0.3, index=index)
    low = pd.Series(close - 0.3, index=index)
    close = pd.Series(close, index=index)

    direction = supertrend(high, low, close, period=10, multiplier=3)

    assert direction.iloc[90] == 1  # deep in the uptrend
    assert direction.iloc[-1] == -1  # deep in the downtrend after the reversal
    assert set(direction.dropna().unique()).issubset({1, -1})  # no flat state


def test_adx_dmi_plus_di_leads_in_a_steady_uptrend(trending_ohlcv):
    adx, plus_di, minus_di = adx_dmi(trending_ohlcv["high"], trending_ohlcv["low"], trending_ohlcv["close"], period=14)

    valid = adx.notna() & plus_di.notna() & minus_di.notna()
    assert (adx[valid] >= 0).all() and (adx[valid] <= 100).all()
    assert (plus_di[valid] >= 0).all() and (minus_di[valid] >= 0).all()
    assert (plus_di[valid].iloc[-20:] > minus_di[valid].iloc[-20:]).all()
