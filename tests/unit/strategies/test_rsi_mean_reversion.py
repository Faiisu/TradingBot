from tradebot.strategies.rsi_mean_reversion import RsiMeanReversionStrategy
from tradebot.timeframe import Timeframe


def test_oscillates_between_long_and_short(oscillating_ohlcv):
    strategy = RsiMeanReversionStrategy(timeframe=Timeframe.H1)
    signals = strategy.generate_signals(oscillating_ohlcv)
    assert 1 in signals.values
    assert -1 in signals.values
    assert set(signals.unique()).issubset({-1, 0, 1})


def test_returns_to_flat_after_recrossing_fifty(oscillating_ohlcv):
    strategy = RsiMeanReversionStrategy(timeframe=Timeframe.H1)
    signals = strategy.generate_signals(oscillating_ohlcv)
    assert 0 in signals.values
