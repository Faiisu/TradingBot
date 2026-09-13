from tradebot.strategies.macd import MacdStrategy
from tradebot.timeframe import Timeframe


def test_goes_long_during_sustained_uptrend(trending_ohlcv):
    strategy = MacdStrategy(timeframe=Timeframe.H1, fast=5, slow=15, signal_period=5)
    signals = strategy.generate_signals(trending_ohlcv)
    assert signals.iloc[-1] == 1
    assert set(signals.unique()).issubset({-1, 0, 1})
