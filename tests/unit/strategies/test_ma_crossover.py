from tradebot.strategies.ma_crossover import MaCrossoverStrategy
from tradebot.timeframe import Timeframe


def test_goes_long_during_sustained_uptrend(trending_ohlcv):
    strategy = MaCrossoverStrategy(timeframe=Timeframe.H1, fast=5, slow=20)
    signals = strategy.generate_signals(trending_ohlcv)
    assert signals.iloc[-1] == 1
    assert set(signals.unique()).issubset({-1, 0, 1})


def test_flat_before_warmup(trending_ohlcv):
    strategy = MaCrossoverStrategy(timeframe=Timeframe.H1, fast=5, slow=20)
    signals = strategy.generate_signals(trending_ohlcv)
    assert signals.iloc[0] == 0
