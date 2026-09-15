from tradebot.strategies.stochastic_reversion import StochasticReversionStrategy
from tradebot.timeframe import Timeframe


def test_oscillates_between_long_and_short(oscillating_ohlcv):
    strategy = StochasticReversionStrategy(timeframe=Timeframe.H1)
    signals = strategy.generate_signals(oscillating_ohlcv)

    assert 1 in signals.values
    assert -1 in signals.values
    assert set(signals.unique()).issubset({-1, 0, 1})


def test_returns_to_flat_after_recrossing_fifty(oscillating_ohlcv):
    strategy = StochasticReversionStrategy(timeframe=Timeframe.H1)
    signals = strategy.generate_signals(oscillating_ohlcv)

    assert 0 in signals.values


def test_name_encodes_k_and_d_periods():
    strategy = StochasticReversionStrategy(timeframe=Timeframe.H1, k_period=14, d_period=3)
    assert strategy.name == "stochastic_reversion_14_3"
