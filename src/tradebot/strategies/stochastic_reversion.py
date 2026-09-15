import pandas as pd

from tradebot.indicators import stochastic
from tradebot.strategies.base import DataRequirement, threshold_reversion_signals
from tradebot.timeframe import Timeframe


class StochasticReversionStrategy:
    """Ticket calls this "Stochastic Reversion (14, 3)" — d_period is kept as the standard Stochastic
    (14, 3) setting so the name/identity matches convention, but the entry rule reads only %K, "the
    same shape as RSI Reversion" (see the rule-set-expansion ticket); %D is computed by the shared
    indicator but deliberately unused here."""

    supporting_data: tuple[DataRequirement, ...] = ()

    def __init__(self, timeframe: Timeframe, k_period: int = 14, d_period: int = 3, oversold: float = 20, overbought: float = 80):
        self.timeframe = timeframe
        self.k_period = k_period
        self.d_period = d_period
        self.oversold = oversold
        self.overbought = overbought
        self.name = f"stochastic_reversion_{k_period}_{d_period}"

    def generate_signals(self, ohlcv: pd.DataFrame, supporting: dict[DataRequirement, pd.DataFrame] | None = None) -> pd.Series:
        percent_k, _percent_d = stochastic(ohlcv["high"], ohlcv["low"], ohlcv["close"], self.k_period, self.d_period)
        return threshold_reversion_signals(percent_k, self.oversold, self.overbought)
