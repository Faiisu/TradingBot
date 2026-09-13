from tradebot.strategies.atr_channel_breakout import AtrChannelBreakoutStrategy
from tradebot.timeframe import Timeframe


def test_breakout_then_revert_cycle(breakout_ohlcv):
    strategy = AtrChannelBreakoutStrategy(timeframe=Timeframe.H1, ema_period=20, atr_period=14, multiplier=2.0)
    signals = strategy.generate_signals(breakout_ohlcv)

    assert signals.iloc[61] == 1
    assert signals.iloc[121] == -1
    assert set(signals.unique()).issubset({-1, 0, 1})
