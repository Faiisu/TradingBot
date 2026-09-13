import numpy as np
import pandas as pd
import pytest


def _make_ohlcv(close: np.ndarray, noise: float = 0.05) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=len(close), freq="h")
    rng = np.random.default_rng(42)
    high = close + rng.uniform(0, noise, size=len(close))
    low = close - rng.uniform(0, noise, size=len(close))
    open_ = close + rng.uniform(-noise, noise, size=len(close))
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close}, index=index)


@pytest.fixture
def trending_ohlcv() -> pd.DataFrame:
    """Steady uptrend for ~200 bars, long enough for slow-period indicators to warm up."""
    close = np.linspace(100, 160, 200)
    return _make_ohlcv(close)


@pytest.fixture
def oscillating_ohlcv() -> pd.DataFrame:
    """Sine-wave price series that repeatedly swings between overbought/oversold extremes."""
    x = np.linspace(0, 8 * np.pi, 400)
    close = 100 + 15 * np.sin(x)
    return _make_ohlcv(close, noise=0.02)


@pytest.fixture
def flat_ohlcv() -> pd.DataFrame:
    """Flat price series: no trend, no volatility expansion."""
    close = np.full(100, 100.0)
    return _make_ohlcv(close, noise=0.0)


@pytest.fixture
def breakout_ohlcv() -> pd.DataFrame:
    """Flat -> spike up -> revert -> spike down -> revert, to exercise band-breakout strategies."""
    close = np.concatenate(
        [
            np.full(60, 100.0),  # warm up tight bands
            np.full(30, 140.0),  # break upper band
            np.full(30, 100.0),  # recross middle -> flat
            np.full(30, 60.0),  # break lower band
            np.full(20, 100.0),  # recross middle -> flat
        ]
    )
    return _make_ohlcv(close, noise=0.01)
