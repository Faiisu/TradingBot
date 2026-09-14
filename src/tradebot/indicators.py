import numpy as np
import pandas as pd


def sma(close: pd.Series, period: int) -> pd.Series:
    return close.rolling(window=period).mean()


def ema(close: pd.Series, period: int) -> pd.Series:
    return close.ewm(span=period, adjust=False).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    result = 100 - (100 / (1 + rs))
    return result.where(avg_loss != 0, 100.0)


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.Series, pd.Series]:
    macd_line = ema(close, fast) - ema(close, slow)
    signal_line = ema(macd_line, signal)
    return macd_line, signal_line


def bollinger_bands(close: pd.Series, period: int = 20, num_std: float = 2.0) -> tuple[pd.Series, pd.Series, pd.Series]:
    middle = sma(close, period)
    std = close.rolling(window=period).std()
    upper = middle + num_std * std
    lower = middle - num_std * std
    return upper, middle, lower


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    return pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    return true_range(high, low, close).ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def donchian_channel(high: pd.Series, low: pd.Series, period: int) -> tuple[pd.Series, pd.Series]:
    """The highest high / lowest low of the prior `period` bars — shifted so the current bar's own
    high/low is never included, or a breakout could never register against its own bar."""
    upper = high.shift(1).rolling(window=period).max()
    lower = low.shift(1).rolling(window=period).min()
    return upper, lower


def supertrend(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 10, multiplier: float = 3.0) -> pd.Series:
    """Direction only (1 = uptrend, -1 = downtrend); there is no flat state. Standard Supertrend: a
    volatility band around the midprice that only tightens toward price, flipping direction when
    price closes through it."""
    atr_values = atr(high, low, close, period)
    mid = (high + low) / 2
    basic_upper = (mid + multiplier * atr_values).to_numpy()
    basic_lower = (mid - multiplier * atr_values).to_numpy()
    close_v = close.to_numpy()

    final_upper = np.full(len(close_v), np.nan)
    final_lower = np.full(len(close_v), np.nan)
    direction = np.full(len(close_v), np.nan)

    for i in range(len(close_v)):
        if np.isnan(basic_upper[i]) or np.isnan(basic_lower[i]):
            continue
        prev_upper = final_upper[i - 1] if i > 0 and not np.isnan(final_upper[i - 1]) else basic_upper[i]
        prev_lower = final_lower[i - 1] if i > 0 and not np.isnan(final_lower[i - 1]) else basic_lower[i]
        final_upper[i] = basic_upper[i] if basic_upper[i] < prev_upper or close_v[i - 1] > prev_upper else prev_upper
        final_lower[i] = basic_lower[i] if basic_lower[i] > prev_lower or close_v[i - 1] < prev_lower else prev_lower

        prev_direction = direction[i - 1] if i > 0 and not np.isnan(direction[i - 1]) else 1.0
        if close_v[i] > final_upper[i]:
            direction[i] = 1.0
        elif close_v[i] < final_lower[i]:
            direction[i] = -1.0
        else:
            direction[i] = prev_direction

    return pd.Series(direction, index=close.index, name="supertrend_direction")


def adx_dmi(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Wilder's ADX/+DI/-DI. Returns (adx, plus_di, minus_di)."""
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0.0), index=high.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0.0), index=high.index)

    smoothed_tr = true_range(high, low, close).ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    smoothed_plus_dm = plus_dm.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    smoothed_minus_dm = minus_dm.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    # a flat run of bars (zero True Range) has no directional movement either — 0/0 reads as "no
    # direction" (0.0), not NaN/inf, matching rsi()'s guard for the same kind of zero-denominator bar
    no_range = smoothed_tr == 0
    plus_di = (100 * smoothed_plus_dm / smoothed_tr.replace(0, float("nan"))).where(~no_range, 0.0)
    minus_di = (100 * smoothed_minus_dm / smoothed_tr.replace(0, float("nan"))).where(~no_range, 0.0)
    di_sum = plus_di + minus_di
    dx = (100 * (plus_di - minus_di).abs() / di_sum.replace(0, float("nan"))).where(di_sum != 0, 0.0)
    adx = dx.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    return adx, plus_di, minus_di
