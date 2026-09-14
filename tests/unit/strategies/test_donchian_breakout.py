import pandas as pd

from tradebot.strategies.donchian_breakout import DonchianBreakoutStrategy
from tradebot.timeframe import Timeframe


def _ohlcv(closes: list[float]) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=len(closes), freq="h")
    close = pd.Series(closes, index=index)
    return pd.DataFrame({"open": close, "high": close, "low": close, "close": close}, index=index)


def test_enters_long_on_a_close_above_the_prior_20_bar_high_then_flat_below_the_prior_10_bar_low():
    # 25 flat bars at 100 (warms up both channels), a breakout to 110, drift back down through the
    # narrower 10-bar exit channel (105) without breaking the wider 20-bar entry channel (100) —
    # isolates "flat" from "reversed straight to short"
    closes = [100.0] * 25 + [110.0] + [105.0] * 9 + [102.0]
    strategy = DonchianBreakoutStrategy(timeframe=Timeframe.H1, entry_period=20, exit_period=10)
    signals = strategy.generate_signals(_ohlcv(closes))

    assert signals.iloc[25] == 1  # the breakout bar itself
    assert signals.iloc[30] == 1  # still above the narrower 10-bar exit channel
    assert signals.iloc[-1] == 0  # closed below the prior 10-bar low -> flat


def test_enters_short_on_a_close_below_the_prior_20_bar_low():
    closes = [100.0] * 25 + [90.0]
    strategy = DonchianBreakoutStrategy(timeframe=Timeframe.H1, entry_period=20, exit_period=10)
    signals = strategy.generate_signals(_ohlcv(closes))

    assert signals.iloc[25] == -1


def test_short_goes_flat_when_it_closes_above_the_prior_10_bar_high():
    # mirror of the long->flat test: a short breakout to 90, drift back up through the narrower
    # 10-bar exit channel (95) without breaking the wider 20-bar entry channel (100) — isolates
    # "flat" from "reversed straight to long"
    closes = [100.0] * 25 + [90.0] + [95.0] * 9 + [98.0]
    strategy = DonchianBreakoutStrategy(timeframe=Timeframe.H1, entry_period=20, exit_period=10)
    signals = strategy.generate_signals(_ohlcv(closes))

    assert signals.iloc[25] == -1  # the breakout bar itself
    assert signals.iloc[30] == -1  # still below the narrower 10-bar exit channel
    assert signals.iloc[-1] == 0  # closed above the prior 10-bar high -> flat


def test_name_encodes_entry_and_exit_periods():
    strategy = DonchianBreakoutStrategy(timeframe=Timeframe.H1, entry_period=20, exit_period=10)
    assert strategy.name == "donchian_breakout_20_10"
