from dataclasses import dataclass
from typing import Protocol

import numpy as np
import pandas as pd

from tradebot.timeframe import Timeframe


@dataclass(frozen=True)
class DataRequirement:
    """One piece of supporting data a Strategy Candidate declares it needs, beyond its own ohlcv.
    reference_market=None means "the traded instrument itself, on this Timeframe" (what an MTF
    Candidate's Trend Filter needs); a Reference Market label (e.g. "DXY") is what a Market Filter
    needs instead — see CONTEXT.md's Market Filter and Reference Market entries."""

    timeframe: Timeframe
    reference_market: str | None = None

    def __str__(self) -> str:
        return f"{self.timeframe.value} ({self.reference_market})" if self.reference_market else self.timeframe.value


class StrategyCandidate(Protocol):
    name: str
    timeframe: Timeframe
    supporting_data: tuple[DataRequirement, ...]

    def generate_signals(self, ohlcv: pd.DataFrame, supporting: dict[DataRequirement, pd.DataFrame] | None = None) -> pd.Series:
        """Target position state per bar: -1 (short), 0 (flat), 1 (long). `supporting` holds exactly
        the DataFrames named by this candidate's own `supporting_data`; a candidate that declares none
        gets an empty dict and can ignore the parameter entirely."""
        ...


def resolve_supporting_data(
    candidate: StrategyCandidate, data_by_requirement: dict[DataRequirement, pd.DataFrame]
) -> dict[DataRequirement, pd.DataFrame]:
    """Builds the `supporting` dict generate_signals() expects, from whatever data is already loaded.
    `data_by_requirement` is keyed by DataRequirement itself (reference_market=None for the traded
    instrument's own data on a Timeframe, a Reference Market name for a Market Filter's own data) —
    a candidate's requirement is simply looked up, so a Trend Filter's gold-on-a-higher-Timeframe
    requirement and a Market Filter's DXY/silver/real-yield requirement resolve identically. Used by
    the Backtest and Walk-Forward Validation so neither needs its own resolution logic."""
    resolved: dict[DataRequirement, pd.DataFrame] = {}
    for requirement in getattr(candidate, "supporting_data", ()):
        if requirement not in data_by_requirement:
            available = sorted(str(r) for r in data_by_requirement)
            raise KeyError(f"{candidate.name} needs {requirement}, but it wasn't loaded (available: {available})")
        resolved[requirement] = data_by_requirement[requirement]
    return resolved


def candidate_rule_set_key(candidate: StrategyCandidate) -> tuple[str, str]:
    """Groups a Strategy Candidate by (Rule Set, Entry Timeframe), ignoring any Trend/Market Filter —
    an MtfCandidate and its unfiltered counterpart share this key with each other (via its
    entry_strategy), since Ensemble selection admits at most one variant of a given Rule Set on a
    given Entry Timeframe at once (see CONTEXT.md's Ensemble entry)."""
    base = getattr(candidate, "entry_strategy", candidate)
    return (base.name, candidate.timeframe.value)


def align_htf_signal(htf_signal: pd.Series, entry_index: pd.DatetimeIndex) -> pd.Series:
    """Aligns a higher-timeframe signal onto a lower-timeframe (entry) index without look-ahead: each
    entry bar gets the most recent htf_signal value at-or-before its own timestamp, never a future one.
    Entry bars before the first htf bar closes get NaN (no filter opinion yet)."""
    htf_sorted = htf_signal.sort_index()
    htf_df = pd.DataFrame({"time": htf_sorted.index, "htf": htf_sorted.to_numpy()})
    entry_df = pd.DataFrame({"time": entry_index})
    merged = pd.merge_asof(entry_df, htf_df, on="time", direction="backward")
    return merged.set_index("time")["htf"]


def _stateful_breakout_signals(
    close: pd.Series,
    entry_upper: pd.Series,
    entry_lower: pd.Series,
    exit_upper: pd.Series,
    exit_lower: pd.Series,
    inclusive: bool,
    entry_confirmed: pd.Series | None = None,
) -> pd.Series:
    """Shared shape behind band_state_signals and channel_breakout_signals: enter long/short on an
    entry-channel breakout, stay until price recrosses back through the (possibly narrower) exit
    channel. `inclusive` controls whether the exit trigger is <=/>= (band_state_signals, where entry
    and exit channel are the same width so a hair-trigger re-entry needs the inclusive edge) or </>
    (channel_breakout_signals, where the exit channel is strictly narrower so the edge case doesn't
    arise the same way) — kept as a parameter rather than unified, to leave band_state_signals'
    already-shipped behavior for ATR Channel Breakout and Bollinger Breakout untouched. `entry_confirmed`
    gates new entries only (e.g. Volume-Confirmed Breakout's tick-volume condition) — a breakout bar
    with entry_confirmed False is skipped outright, not remembered for a later bar; exits are never gated."""
    signals = np.zeros(len(close))
    state = 0
    close_v = close.to_numpy()
    entry_upper_v, entry_lower_v = entry_upper.to_numpy(), entry_lower.to_numpy()
    exit_upper_v, exit_lower_v = exit_upper.to_numpy(), exit_lower.to_numpy()
    confirmed_v = np.full(len(close), True) if entry_confirmed is None else entry_confirmed.to_numpy()
    for i in range(len(close_v)):
        c, eu, el, xu, xl = close_v[i], entry_upper_v[i], entry_lower_v[i], exit_upper_v[i], exit_lower_v[i]
        if np.isnan(eu) or np.isnan(el) or np.isnan(xu) or np.isnan(xl):
            signals[i] = 0
            continue
        if c > eu and confirmed_v[i]:
            state = 1
        elif c < el and confirmed_v[i]:
            state = -1
        elif state == 1 and (c <= xl if inclusive else c < xl):
            state = 0
        elif state == -1 and (c >= xu if inclusive else c > xu):
            state = 0
        signals[i] = state
    return pd.Series(signals, index=close.index, name="signal")


def band_state_signals(close: pd.Series, upper: pd.Series, lower: pd.Series, middle: pd.Series) -> pd.Series:
    """Stateful breakout signal: enter long/short on a band breakout, stay until price recrosses the middle line."""
    return _stateful_breakout_signals(close, upper, lower, middle, middle, inclusive=True)


def channel_breakout_signals(
    close: pd.Series,
    entry_upper: pd.Series,
    entry_lower: pd.Series,
    exit_upper: pd.Series,
    exit_lower: pd.Series,
    entry_confirmed: pd.Series | None = None,
) -> pd.Series:
    """Stateful breakout signal with a narrower exit channel than the entry channel (e.g. Donchian
    Breakout's 20-bar entry / 10-bar exit): enter long/short on an entry-channel breakout, stay until
    price recrosses back through the exit channel on its own side. `entry_confirmed`, when given, must
    also be true on the breakout bar for a new entry to take (Volume-Confirmed Breakout's volume gate)."""
    return _stateful_breakout_signals(close, entry_upper, entry_lower, exit_upper, exit_lower, inclusive=False, entry_confirmed=entry_confirmed)


def threshold_reversion_signals(indicator: pd.Series, oversold: float, overbought: float, midpoint: float = 50) -> pd.Series:
    """Stateful mean-reversion signal shared by RSI Reversion and Stochastic Reversion: go long when
    the indicator drops below `oversold`, short when it rises above `overbought`, and flat once it
    crosses back through `midpoint` on its own side (an oversold-triggered long clears at >= midpoint;
    an overbought-triggered short clears at <= midpoint)."""
    signals = np.zeros(len(indicator))
    state = 0
    values = indicator.to_numpy()
    for i in range(len(values)):
        v = values[i]
        if np.isnan(v):
            signals[i] = 0
            continue
        if v < oversold:
            state = 1
        elif v > overbought:
            state = -1
        elif state == 1 and v >= midpoint:
            state = 0
        elif state == -1 and v <= midpoint:
            state = 0
        signals[i] = state
    return pd.Series(signals, index=indicator.index, name="signal")
