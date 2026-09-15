from dataclasses import dataclass
from typing import Literal

import pandas as pd

from tradebot.strategies.base import DataRequirement, StrategyCandidate, align_htf_signal
from tradebot.timeframe import Timeframe

Relationship = Literal["same", "inverse"]


@dataclass(frozen=True)
class ReferenceMarketConfig:
    """A Reference Market's fixed properties (registry.py's REFERENCE_MARKETS): its relationship to
    gold, and the MT5 symbol it trades under on this broker's server."""

    symbol: str
    relationship: Relationship


class MarketFilteredCandidate:
    """Wraps an entry Strategy Candidate with a Market Filter: a Reference Market's own direction
    (the same EMA-slope computation a Trend Filter uses, but read from a different market's own data,
    not the traded instrument's) gates entries the way a Trend Filter does. `relationship` is "same"
    when a rising Reference Market allows only long entries (e.g. silver), or "inverse" when it allows
    only short entries (e.g. DXY, real yield) — see CONTEXT.md's Market Filter entry. Distinct from
    MtfCandidate only in its data source and in carrying this relationship."""

    def __init__(
        self,
        entry_strategy: StrategyCandidate,
        filter_fn,
        reference_market: str,
        filter_timeframe: Timeframe,
        relationship: Relationship,
    ):
        self.entry_strategy = entry_strategy
        self.filter_fn = filter_fn
        self.reference_market = reference_market
        self.filter_timeframe = filter_timeframe
        self.relationship = relationship
        self.timeframe = entry_strategy.timeframe
        self.name = f"{entry_strategy.name}_marketfilter_{reference_market.lower()}"
        # exposed for persistence.py's dashboard labeling, which already reads filter_name/filter_timeframe
        # generically off any candidate (getattr) — the same attributes MtfCandidate exposes
        self.filter_name = reference_market
        self._requirement = DataRequirement(timeframe=filter_timeframe, reference_market=reference_market)
        self.supporting_data = (self._requirement,)

    def generate_signals(self, ohlcv: pd.DataFrame, supporting: dict[DataRequirement, pd.DataFrame] | None = None) -> pd.Series:
        market_ohlcv = (supporting or {}).get(self._requirement)
        if market_ohlcv is None:
            raise ValueError(f"{self.name} requires its {self.reference_market} Market Filter data in `supporting`")

        entry_signal = self.entry_strategy.generate_signals(ohlcv)
        market_trend = self.filter_fn(market_ohlcv)
        aligned_trend = align_htf_signal(market_trend, ohlcv.index)
        required_direction = aligned_trend if self.relationship == "same" else -aligned_trend

        return entry_signal.where(entry_signal == required_direction, 0.0)
