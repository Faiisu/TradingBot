import numpy as np
import pandas as pd
import pytest

from tradebot.strategies.base import DataRequirement
from tradebot.strategies.market_filter import MarketFilteredCandidate, real_yield_change_filter
from tradebot.timeframe import Timeframe


def _ohlcv_from_close(close: np.ndarray, freq: str = "h") -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=len(close), freq=freq)
    return pd.DataFrame({"open": close, "high": close + 0.5, "low": close - 0.5, "close": close}, index=index)


class _StubEntryStrategy:
    def __init__(self, timeframe, fixed_signal):
        self.timeframe = timeframe
        self.name = "stub_entry"
        self.fixed_signal = fixed_signal
        self.supporting_data = ()

    def generate_signals(self, ohlcv, supporting=None):
        return pd.Series(self.fixed_signal, index=ohlcv.index)


def test_only_already_closed_reference_market_bars_are_used_at_each_entry_bar():
    """A DXY-like series that turns at a known bar (03:00), exercised end to end through
    MarketFilteredCandidate — not just the underlying align_htf_signal helper in isolation — proves an
    entry bar can never see a Reference Market bar that hadn't closed yet. If 03:15 leaked the future
    04:00 DXY value, this candidate would go flat there instead of staying long."""
    market_index = pd.date_range("2024-01-01 00:00", periods=5, freq="h")  # 00:00 .. 04:00
    turning_trend = pd.Series([1.0, 1.0, 1.0, -1.0, 1.0], index=market_index)  # dips down only at 03:00
    market_ohlcv = _ohlcv_from_close(np.linspace(100, 104, 5), freq="h")
    stub_filter = lambda df: turning_trend  # noqa: E731 — stands in for DXY's real EMA-slope result

    entry_index = pd.DatetimeIndex(
        [
            "2024-01-01 02:00",  # sees DXY's 02:00 bar (up) -> inverse: shorts only -> long forced flat
            "2024-01-01 02:45",  # still before DXY's 03:00 close -> still up -> still flat
            "2024-01-01 03:00",  # DXY's 03:00 bar (down) just closed -> inverse: longs now allowed
            "2024-01-01 03:15",  # DXY's 04:00 bar (up again) hasn't closed yet -> must still see "down"
        ]
    )
    ohlcv = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0}, index=entry_index)

    entry = _StubEntryStrategy(Timeframe.M15, fixed_signal=1.0)  # always long
    candidate = MarketFilteredCandidate(entry, stub_filter, "DXY", Timeframe.H1, relationship="inverse")
    signals = candidate.generate_signals(ohlcv, {DataRequirement(timeframe=Timeframe.H1, reference_market="DXY"): market_ohlcv})

    assert list(signals) == [0.0, 0.0, 1.0, 1.0]


def test_market_filtered_candidate_declares_its_reference_markets_data_as_a_requirement():
    entry = _StubEntryStrategy(Timeframe.M15, fixed_signal=1.0)
    candidate = MarketFilteredCandidate(entry, lambda df: df, "DXY", Timeframe.H1, relationship="inverse")

    assert candidate.supporting_data == (DataRequirement(timeframe=Timeframe.H1, reference_market="DXY"),)


def test_inverse_relationship_keeps_only_short_entries_when_the_market_rises():
    ohlcv = _ohlcv_from_close(np.linspace(100, 110, 10), freq="15min")
    market_ohlcv = _ohlcv_from_close(np.linspace(100, 110, 10), freq="h")

    entry = _StubEntryStrategy(Timeframe.M15, fixed_signal=1.0)  # always long
    rising_filter = lambda df: pd.Series(1.0, index=df.index)  # noqa: E731 — market is rising

    candidate = MarketFilteredCandidate(entry, rising_filter, "DXY", Timeframe.H1, relationship="inverse")
    signals = candidate.generate_signals(ohlcv, {DataRequirement(timeframe=Timeframe.H1, reference_market="DXY"): market_ohlcv})

    # DXY rising -> only shorts allowed; an always-long entry is forced flat
    assert (signals == 0.0).all()


def test_inverse_relationship_keeps_short_entries_when_the_market_rises():
    ohlcv = _ohlcv_from_close(np.linspace(100, 110, 10), freq="15min")
    market_ohlcv = _ohlcv_from_close(np.linspace(100, 110, 10), freq="h")

    entry = _StubEntryStrategy(Timeframe.M15, fixed_signal=-1.0)  # always short
    rising_filter = lambda df: pd.Series(1.0, index=df.index)  # noqa: E731

    candidate = MarketFilteredCandidate(entry, rising_filter, "DXY", Timeframe.H1, relationship="inverse")
    signals = candidate.generate_signals(ohlcv, {DataRequirement(timeframe=Timeframe.H1, reference_market="DXY"): market_ohlcv})

    assert (signals == -1.0).all()


def test_same_relationship_keeps_only_long_entries_when_the_market_rises():
    ohlcv = _ohlcv_from_close(np.linspace(100, 110, 10), freq="15min")
    market_ohlcv = _ohlcv_from_close(np.linspace(100, 110, 10), freq="h")

    entry = _StubEntryStrategy(Timeframe.M15, fixed_signal=-1.0)  # always short
    rising_filter = lambda df: pd.Series(1.0, index=df.index)  # noqa: E731

    candidate = MarketFilteredCandidate(entry, rising_filter, "XAGUSD", Timeframe.H1, relationship="same")
    signals = candidate.generate_signals(ohlcv, {DataRequirement(timeframe=Timeframe.H1, reference_market="XAGUSD"): market_ohlcv})

    # silver rising -> only longs allowed; an always-short entry is forced flat
    assert (signals == 0.0).all()


def test_market_filtered_candidate_requires_its_filter_data_in_supporting():
    entry = _StubEntryStrategy(Timeframe.M15, fixed_signal=1.0)
    candidate = MarketFilteredCandidate(entry, lambda df: df, "DXY", Timeframe.H1, relationship="inverse")
    ohlcv = _ohlcv_from_close(np.linspace(100, 110, 10), freq="15min")

    with pytest.raises(ValueError):
        candidate.generate_signals(ohlcv, supporting=None)
    with pytest.raises(ValueError):
        candidate.generate_signals(ohlcv, supporting={})


def test_market_filtered_candidate_name_and_timeframe():
    entry = _StubEntryStrategy(Timeframe.M15, fixed_signal=1.0)
    entry.name = "macd_12_26_9"
    candidate = MarketFilteredCandidate(entry, lambda df: df, "DXY", Timeframe.H1, relationship="inverse")

    assert candidate.name == "macd_12_26_9_marketfilter_dxy"
    assert candidate.timeframe == Timeframe.M15


def test_market_filtered_candidate_exposes_filter_name_and_timeframe_for_the_dashboard():
    """persistence.py reads filter_name/filter_timeframe generically off any candidate (getattr), the
    same attributes MtfCandidate already exposes — so a Market-Filtered candidate is labeled on the
    Backtest page without persistence.py needing to know Market Filters exist."""
    entry = _StubEntryStrategy(Timeframe.M15, fixed_signal=1.0)
    candidate = MarketFilteredCandidate(entry, lambda df: df, "DXY", Timeframe.H1, relationship="inverse")

    assert candidate.filter_name == "DXY"
    assert candidate.filter_timeframe == Timeframe.H1


def test_real_yield_change_filter_reads_the_lookback_business_day_change():
    # one row per business day (already usable_from-indexed) — bar 20 is 1.0 higher than bar 0
    index = pd.date_range("2024-01-01", periods=25, freq="D")
    close = pd.Series([1.5] * 20 + [2.5] * 5, index=index)
    df = pd.DataFrame({"close": close}, index=index)

    signal = real_yield_change_filter(df, lookback=20)

    assert signal.iloc[19] == 0  # still warming up: no value 20 rows back yet
    assert signal.iloc[20] == 1  # 2.5 now vs 1.5 twenty rows back -> rising
    assert signal.iloc[24] == 1


def test_real_yield_change_filter_detects_falling_yields():
    index = pd.date_range("2024-01-01", periods=25, freq="D")
    close = pd.Series([2.5] * 20 + [1.5] * 5, index=index)
    df = pd.DataFrame({"close": close}, index=index)

    signal = real_yield_change_filter(df, lookback=20)

    assert signal.iloc[20] == -1


class _RememberingEntryStrategy:
    """Like _StubEntryStrategy, but the fixed signal can vary bar to bar (a plain list, not one
    constant) — needed to exercise the staleness gate's "continue only if it still agrees with the
    already-held direction" rule, which a constant-signal stub can't distinguish from a flip."""

    def __init__(self, timeframe, signal_values):
        self.timeframe = timeframe
        self.name = "remembering_entry"
        self.signal_values = signal_values
        self.supporting_data = ()

    def generate_signals(self, ohlcv, supporting=None):
        return pd.Series(self.signal_values, index=ohlcv.index)


def test_staleness_blocks_a_fresh_entry_but_allows_continuing_the_same_direction():
    """rule-set-expansion ticket 09's "no opinion" rule: while the Reference Market's data is stale,
    a candidate opens no new trades, but a position already held continues as long as the entry Rule
    Set's own signal still agrees with it. Staleness is measured in business days, so this test uses
    daily bars spanning real calendar dates rather than an arbitrary bar count."""
    # 2024-01-01 is a Monday. The real yield's last-ever close is 2024-01-02 (Tue).
    market_ohlcv = _ohlcv_from_close(np.array([100.0, 101.0]), freq="D")
    market_ohlcv.index = pd.DatetimeIndex(["2024-01-01", "2024-01-02"])

    # Jan 1/2: fresh (0 business days old). Jan 8/9/10: stale (4+ business days old — Jan 6-7 is a
    # weekend, so busday_count skips it, same as np.busday_count / any real business-day calendar).
    entry_index = pd.DatetimeIndex(["2024-01-01", "2024-01-02", "2024-01-08", "2024-01-09", "2024-01-10"])
    # bar 0: flat. bar 1: opens long while fresh. bars 2-4: entry keeps signalling long while stale.
    entry = _RememberingEntryStrategy(Timeframe.M15, [0.0, 1.0, 1.0, 1.0, 1.0])
    always_up_filter = lambda df: pd.Series(1.0, index=df.index)  # noqa: E731

    ohlcv = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0}, index=entry_index)
    candidate = MarketFilteredCandidate(
        entry, always_up_filter, "REAL_YIELD", Timeframe.H1, relationship="same", max_staleness_business_days=3
    )
    signals = candidate.generate_signals(
        ohlcv, {DataRequirement(timeframe=Timeframe.H1, reference_market="REAL_YIELD"): market_ohlcv}
    )

    assert list(signals) == [0.0, 1.0, 1.0, 1.0, 1.0]


def test_staleness_blocks_a_flip_to_the_opposite_direction_going_flat_instead():
    # the real yield's one and only close, ever, is 2024-01-01 (Mon) — everything from Jan 8 onward
    # (4+ business days later) is stale.
    market_ohlcv = _ohlcv_from_close(np.array([100.0]), freq="D")
    market_ohlcv.index = pd.DatetimeIndex(["2024-01-01"])

    entry_index = pd.DatetimeIndex(["2024-01-01", "2024-01-08", "2024-01-09"])
    # bar 0: long while fresh. bar 1: now stale AND the entry signal flips short -> per the
    # "continue only same-direction, else flat" rule, this goes flat, not short — and stays flat.
    entry = _RememberingEntryStrategy(Timeframe.M15, [1.0, -1.0, -1.0])
    always_up_filter = lambda df: pd.Series(1.0, index=df.index)  # noqa: E731

    ohlcv = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0}, index=entry_index)
    candidate = MarketFilteredCandidate(
        entry, always_up_filter, "REAL_YIELD", Timeframe.H1, relationship="same", max_staleness_business_days=3
    )
    signals = candidate.generate_signals(
        ohlcv, {DataRequirement(timeframe=Timeframe.H1, reference_market="REAL_YIELD"): market_ohlcv}
    )

    assert list(signals) == [1.0, 0.0, 0.0]  # never goes short — flat instead, and stays flat


def test_staleness_tolerates_mismatched_datetime64_resolutions():
    """Same root cause as test_align_htf_signal_tolerates_mismatched_datetime64_resolutions in
    test_mtf.py, hit again in the staleness age computation specifically: a parquet round-trip of
    real yield data resolves to a different datetime64 resolution than gold's own MT5-sourced OHLCV
    index, and pandas 3's merge_asof refuses to match keys of different resolutions outright. Caught
    running ticket 09's real yield Market Filter against real cached data, not by any earlier
    same-resolution synthetic test."""
    market_ohlcv = _ohlcv_from_close(np.array([100.0, 101.0]), freq="D")
    market_ohlcv.index = pd.DatetimeIndex(["2024-01-01", "2024-01-02"]).astype("datetime64[us]")

    entry_index = pd.DatetimeIndex(["2024-01-02", "2024-01-08"]).astype("datetime64[ms]")
    entry = _RememberingEntryStrategy(Timeframe.M15, [1.0, 1.0])
    always_up_filter = lambda df: pd.Series(1.0, index=df.index)  # noqa: E731

    ohlcv = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0}, index=entry_index)
    candidate = MarketFilteredCandidate(
        entry, always_up_filter, "REAL_YIELD", Timeframe.H1, relationship="same", max_staleness_business_days=3
    )
    signals = candidate.generate_signals(
        ohlcv, {DataRequirement(timeframe=Timeframe.H1, reference_market="REAL_YIELD"): market_ohlcv}
    )

    assert list(signals) == [1.0, 1.0]  # fresh, then continues while stale — no crash either way


def test_staleness_opens_no_fresh_trade_from_flat():
    # the real yield's only close is decades before any entry bar — always stale
    market_ohlcv = _ohlcv_from_close(np.array([100.0]), freq="D")
    market_ohlcv.index = pd.DatetimeIndex(["2000-01-01"])

    entry_index = pd.DatetimeIndex(["2024-01-01", "2024-01-02"])
    entry = _RememberingEntryStrategy(Timeframe.M15, [0.0, 1.0])  # tries to open long while already stale
    always_up_filter = lambda df: pd.Series(1.0, index=df.index)  # noqa: E731

    ohlcv = pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0}, index=entry_index)
    candidate = MarketFilteredCandidate(
        entry, always_up_filter, "REAL_YIELD", Timeframe.H1, relationship="same", max_staleness_business_days=3
    )
    signals = candidate.generate_signals(
        ohlcv, {DataRequirement(timeframe=Timeframe.H1, reference_market="REAL_YIELD"): market_ohlcv}
    )

    assert list(signals) == [0.0, 0.0]
