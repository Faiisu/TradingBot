from dataclasses import dataclass
from typing import Callable, Literal

import numpy as np
import pandas as pd

from tradebot.strategies.base import DataRequirement, StrategyCandidate, align_htf_signal, match_backward
from tradebot.timeframe import Timeframe

Relationship = Literal["same", "inverse"]


@dataclass(frozen=True)
class ReferenceMarketConfig:
    """A Reference Market's fixed properties (registry.py's REFERENCE_MARKETS). Exactly one data
    source is set: `symbol` for a Reference Market sourced live from MT5 (DXY, silver), or
    `fred_series_id` for one sourced from FRED (real yield) — see data/real_yield.py. `filter_fn`
    defaults to None, meaning "use the standard EMA-slope Trend Filter shape" (mtf.py's
    ema_slope_filter); real yield overrides it with a plain N-business-day change instead.
    `max_staleness_business_days` activates the "no opinion" staleness gate (CONTEXT.md's Market
    Filter entry) — only meaningful for a data source with a publication lag, like FRED."""

    relationship: Relationship
    symbol: str | None = None
    fred_series_id: str | None = None
    filter_fn: Callable[[pd.DataFrame], pd.Series] | None = None
    max_staleness_business_days: int | None = None


def real_yield_change_filter(real_yield_ohlcv: pd.DataFrame, lookback: int = 20) -> pd.Series:
    """Market Filter: the real yield's raw change over `lookback` rows -> 1 (rising) / -1 (falling),
    0 during warmup. The real-yield DataFrame is already one row per business day, re-indexed by the
    moment each value becomes usable (see data/real_yield.py) — so `lookback` rows back is literally
    `lookback` business days back, matching the ticket's "20-business-day change." Unlike
    ema_slope_filter (an EMA-smoothed trend), this reads the raw change with no smoothing, per the
    ticket's exact wording."""
    close = real_yield_ohlcv["close"]
    prior = close.shift(lookback)
    valid = close.notna() & prior.notna()

    signal = pd.Series(0.0, index=close.index, name="signal")
    signal[valid & (close > prior)] = 1
    signal[valid & (close <= prior)] = -1
    return signal


def _age_in_business_days(data_index: pd.DatetimeIndex, entry_index: pd.DatetimeIndex) -> pd.Series:
    """For each entry bar, how many business days old the most recent `data_index` bar at-or-before it
    is. NaN before the first data bar closes (no value has ever existed yet — treated as maximally
    stale by callers, same as "no opinion"). Reuses base.py's match_backward (the payload here is each
    data point's own timestamp, so the match's age can be measured against the entry bar's time)."""
    merged = match_backward(data_index, data_index, entry_index)

    age = pd.Series(np.nan, index=entry_index, dtype=float)
    has_match = merged["value"].notna().to_numpy()
    matched_days = merged.loc[has_match, "value"].to_numpy().astype("datetime64[D]")
    entry_days = merged.loc[has_match, "time"].to_numpy().astype("datetime64[D]")
    age.iloc[has_match] = np.busday_count(matched_days, entry_days)
    return age


def _apply_market_filter(entry_signal: pd.Series, required_direction: pd.Series, stale: pd.Series | None) -> pd.Series:
    """Fresh (or no staleness tracking at all): standard Market Filter gating — an entry is kept only
    where it agrees with `required_direction`. Stale ("no opinion", CONTEXT.md's Market Filter entry):
    opens no new trades; a position already held continues only while the entry Rule Set's own signal
    still agrees with the direction already held, otherwise goes flat rather than flipping straight to
    the opposite side."""
    if stale is None:
        return entry_signal.where(entry_signal == required_direction, 0.0)

    entry_v = entry_signal.to_numpy()
    required_v = required_direction.to_numpy()
    stale_v = stale.to_numpy()
    out = np.zeros(len(entry_v))
    held = 0.0
    for i in range(len(entry_v)):
        if not stale_v[i]:
            out[i] = entry_v[i] if entry_v[i] == required_v[i] else 0.0
        else:
            out[i] = entry_v[i] if (held != 0.0 and entry_v[i] == held) else 0.0
        held = out[i]
    return pd.Series(out, index=entry_signal.index, name="signal")


class MarketFilteredCandidate:
    """Wraps an entry Strategy Candidate with a Market Filter: a Reference Market's own direction
    (typically the same EMA-slope computation a Trend Filter uses, but read from a different market's
    own data, not the traded instrument's) gates entries the way a Trend Filter does. `relationship`
    is "same" when a rising Reference Market allows only long entries (e.g. silver), or "inverse" when
    it allows only short entries (e.g. DXY, real yield) — see CONTEXT.md's Market Filter entry.
    Distinct from MtfCandidate only in its data source and in carrying this relationship.

    `max_staleness_business_days`, when given, activates the "no opinion" staleness gate CONTEXT.md's
    Market Filter entry describes (real yield's FRED publication lag makes gaps possible; DXY and
    silver, sourced live from MT5, never need this — left None, behavior is byte-identical to before
    this parameter existed)."""

    def __init__(
        self,
        entry_strategy: StrategyCandidate,
        filter_fn,
        reference_market: str,
        filter_timeframe: Timeframe,
        relationship: Relationship,
        max_staleness_business_days: int | None = None,
    ):
        self.entry_strategy = entry_strategy
        self.filter_fn = filter_fn
        self.reference_market = reference_market
        self.filter_timeframe = filter_timeframe
        self.relationship = relationship
        self.max_staleness_business_days = max_staleness_business_days
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

        stale = None
        if self.max_staleness_business_days is not None:
            age = _age_in_business_days(market_ohlcv.index, ohlcv.index)
            stale = age.isna() | (age > self.max_staleness_business_days)

        return _apply_market_filter(entry_signal, required_direction, stale)
