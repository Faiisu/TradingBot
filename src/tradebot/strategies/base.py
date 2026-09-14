from dataclasses import dataclass
from typing import Protocol

import numpy as np
import pandas as pd

from tradebot.timeframe import Timeframe


@dataclass(frozen=True)
class DataRequirement:
    """One piece of supporting data a Strategy Candidate declares it needs, beyond its own ohlcv.
    reference_market=None means "the traded instrument itself, on this Timeframe" (what an MTF
    Candidate's Trend Filter needs today); a Reference Market label (e.g. "DXY") is what a Market
    Filter will need — see .scratch/rule-set-expansion/issues/07-dxy-market-filter-end-to-end.md."""

    timeframe: Timeframe
    reference_market: str | None = None


class StrategyCandidate(Protocol):
    name: str
    timeframe: Timeframe
    supporting_data: tuple[DataRequirement, ...]

    def generate_signals(self, ohlcv: pd.DataFrame, supporting: dict[DataRequirement, pd.DataFrame] | None = None) -> pd.Series:
        """Target position state per bar: -1 (short), 0 (flat), 1 (long). `supporting` holds exactly
        the DataFrames named by this candidate's own `supporting_data`; a candidate that declares none
        gets an empty dict and can ignore the parameter entirely."""
        ...


def ensure_reference_market_resolvable(requirement: DataRequirement) -> None:
    """Reference Market resolution isn't built yet (rule-set-expansion tickets 07-09). Shared by every
    caller that walks a candidate's supporting_data — the Backtest (via resolve_supporting_data below)
    and Paper Trading (paper/loop.py's update_member, which fetches live bars per requirement instead
    of looking them up in an already-loaded dict, so it can't just call resolve_supporting_data itself)
    — so a Market-Filtered Candidate fails identically everywhere instead of the two diverging."""
    if requirement.reference_market is not None:
        raise NotImplementedError(
            f"Reference Market {requirement.reference_market!r} is not resolvable yet "
            f"(Market Filters land in rule-set-expansion tickets 07-09)"
        )


def resolve_supporting_data(
    candidate: StrategyCandidate, ohlcv_by_timeframe: dict[Timeframe, pd.DataFrame]
) -> dict[DataRequirement, pd.DataFrame]:
    """Builds the `supporting` dict generate_signals() expects, from whatever data is already loaded.
    Used by the Backtest and Walk-Forward Validation so neither needs to know how an individual
    candidate's requirements map to concrete data."""
    resolved: dict[DataRequirement, pd.DataFrame] = {}
    for requirement in getattr(candidate, "supporting_data", ()):
        ensure_reference_market_resolvable(requirement)
        if requirement.timeframe not in ohlcv_by_timeframe:
            raise KeyError(
                f"{candidate.name} needs {requirement.timeframe.value} data, but it wasn't loaded "
                f"(available: {[tf.value for tf in ohlcv_by_timeframe]})"
            )
        resolved[requirement] = ohlcv_by_timeframe[requirement.timeframe]
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
    close: pd.Series, entry_upper: pd.Series, entry_lower: pd.Series, exit_upper: pd.Series, exit_lower: pd.Series, inclusive: bool
) -> pd.Series:
    """Shared shape behind band_state_signals and channel_breakout_signals: enter long/short on an
    entry-channel breakout, stay until price recrosses back through the (possibly narrower) exit
    channel. `inclusive` controls whether the exit trigger is <=/>= (band_state_signals, where entry
    and exit channel are the same width so a hair-trigger re-entry needs the inclusive edge) or </>
    (channel_breakout_signals, where the exit channel is strictly narrower so the edge case doesn't
    arise the same way) — kept as a parameter rather than unified, to leave band_state_signals'
    already-shipped behavior for ATR Channel Breakout and Bollinger Breakout untouched."""
    signals = np.zeros(len(close))
    state = 0
    close_v = close.to_numpy()
    entry_upper_v, entry_lower_v = entry_upper.to_numpy(), entry_lower.to_numpy()
    exit_upper_v, exit_lower_v = exit_upper.to_numpy(), exit_lower.to_numpy()
    for i in range(len(close_v)):
        c, eu, el, xu, xl = close_v[i], entry_upper_v[i], entry_lower_v[i], exit_upper_v[i], exit_lower_v[i]
        if np.isnan(eu) or np.isnan(el) or np.isnan(xu) or np.isnan(xl):
            signals[i] = 0
            continue
        if c > eu:
            state = 1
        elif c < el:
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
    close: pd.Series, entry_upper: pd.Series, entry_lower: pd.Series, exit_upper: pd.Series, exit_lower: pd.Series
) -> pd.Series:
    """Stateful breakout signal with a narrower exit channel than the entry channel (e.g. Donchian
    Breakout's 20-bar entry / 10-bar exit): enter long/short on an entry-channel breakout, stay until
    price recrosses back through the exit channel on its own side."""
    return _stateful_breakout_signals(close, entry_upper, entry_lower, exit_upper, exit_lower, inclusive=False)
