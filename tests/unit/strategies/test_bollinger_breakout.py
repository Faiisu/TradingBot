from tradebot.strategies.bollinger_breakout import BollingerBreakoutStrategy
from tradebot.timeframe import Timeframe


def test_breakout_then_revert_cycle(breakout_ohlcv):
    strategy = BollingerBreakoutStrategy(timeframe=Timeframe.H1, period=20, num_std=2.0)
    signals = strategy.generate_signals(breakout_ohlcv)

    # index 60-89 is the upward spike; the breakout bar and the bars right after should be long
    assert signals.iloc[61] == 1
    # index 90-119 reverts to the mean; should have returned to flat by the end of that segment
    assert signals.iloc[118] == 0
    # index 120-149 is the downward spike; should go short
    assert signals.iloc[121] == -1
    assert set(signals.unique()).issubset({-1, 0, 1})
