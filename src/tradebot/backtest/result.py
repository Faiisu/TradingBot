from dataclasses import dataclass

import pandas as pd

from tradebot.backtest.trade import Trade


@dataclass(frozen=True)
class BacktestResult:
    candidate_name: str
    timeframe: str
    trades: list[Trade]
    equity_curve: pd.Series
    drawdown_series: pd.Series
