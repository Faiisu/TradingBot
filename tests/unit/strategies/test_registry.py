from tradebot.strategies.market_filter import MarketFilteredCandidate
from tradebot.strategies.mtf import MtfCandidate
from tradebot.strategies.registry import build_candidates
from tradebot.timeframe import Timeframe


def test_build_candidates_returns_single_timeframe_plus_mtf_plus_market_filtered():
    candidates = build_candidates()

    single_timeframe = [c for c in candidates if not isinstance(c, (MtfCandidate, MarketFilteredCandidate))]
    mtf = [c for c in candidates if isinstance(c, MtfCandidate)]
    market_filtered = [c for c in candidates if isinstance(c, MarketFilteredCandidate)]

    assert len(single_timeframe) == 44  # 11 rule sets x 4 timeframes (H1, M30, M15, M5)
    assert len(mtf) == 9  # 3 entry rule sets x 3 filters
    assert len(market_filtered) == 36  # 6 trend rule sets x 2 entry timeframes (M15, M5) x 3 Reference Markets
    assert len(candidates) == 89


def test_mtf_candidates_all_trade_m15_filtered_by_h1():
    mtf = [c for c in build_candidates() if isinstance(c, MtfCandidate)]

    assert all(c.timeframe == Timeframe.M15 for c in mtf)
    assert all(c.filter_timeframe == Timeframe.H1 for c in mtf)


def test_mtf_candidates_have_unique_names():
    mtf = [c for c in build_candidates() if isinstance(c, MtfCandidate)]
    names = [c.name for c in mtf]
    assert len(names) == len(set(names))


def test_single_timeframe_candidates_have_no_filter_timeframe():
    candidates = build_candidates()
    single_timeframe = [c for c in candidates if not isinstance(c, (MtfCandidate, MarketFilteredCandidate))]
    assert all(getattr(c, "filter_timeframe", None) is None for c in single_timeframe)


def test_the_new_trend_rule_sets_are_single_timeframe_only_not_mtf_entries():
    mtf_entry_names = [c.entry_strategy.name for c in build_candidates() if isinstance(c, MtfCandidate)]
    excluded_prefixes = (
        "donchian_breakout",
        "supertrend",
        "adx_dmi",
        "stochastic_reversion",
        "asian_range_breakout",
        "volume_confirmed_breakout",
    )
    assert not any(name.startswith(excluded_prefixes) for name in mtf_entry_names)


def test_market_filtered_candidates_trade_m15_and_m5_filtered_on_h1():
    market_filtered = [c for c in build_candidates() if isinstance(c, MarketFilteredCandidate)]

    assert all(c.timeframe in (Timeframe.M15, Timeframe.M5) for c in market_filtered)
    assert all(c.filter_timeframe == Timeframe.H1 for c in market_filtered)


def test_dxy_market_filtered_candidates_are_inverse():
    dxy = [c for c in build_candidates() if isinstance(c, MarketFilteredCandidate) and c.reference_market == "DXY"]
    assert len(dxy) == 12
    assert all(c.relationship == "inverse" for c in dxy)


def test_silver_market_filtered_candidates_are_same_direction():
    silver = [c for c in build_candidates() if isinstance(c, MarketFilteredCandidate) and c.reference_market == "XAGUSD"]
    assert len(silver) == 12
    assert all(c.relationship == "same" for c in silver)


def test_real_yield_market_filtered_candidates_are_inverse_with_staleness_tracking():
    real_yield = [c for c in build_candidates() if isinstance(c, MarketFilteredCandidate) and c.reference_market == "REAL_YIELD"]
    assert len(real_yield) == 12
    assert all(c.relationship == "inverse" for c in real_yield)
    assert all(c.max_staleness_business_days == 3 for c in real_yield)


def test_dxy_and_silver_market_filtered_candidates_have_no_staleness_tracking():
    """DXY/silver are sourced live from MT5 every tick — the "no opinion" staleness gate is specific
    to real yield's FRED publication lag."""
    market_filtered = [c for c in build_candidates() if isinstance(c, MarketFilteredCandidate)]
    for candidate in market_filtered:
        if candidate.reference_market in ("DXY", "XAGUSD"):
            assert candidate.max_staleness_business_days is None


def test_market_filtered_candidates_cover_exactly_the_six_trend_rule_sets_for_every_reference_market():
    market_filtered = [c for c in build_candidates() if isinstance(c, MarketFilteredCandidate)]
    expected_names = {
        "ma_crossover_20_50",
        "macd_12_26_9",
        "atr_channel_breakout_20_14_2.0",
        "donchian_breakout_20_10",
        "supertrend_10_3.0",
        "adx_dmi_14",
    }
    for market in ("DXY", "XAGUSD", "REAL_YIELD"):
        entry_names = {c.entry_strategy.name for c in market_filtered if c.reference_market == market}
        assert entry_names == expected_names


def test_market_filtered_candidates_are_unique_per_name_and_timeframe():
    """Names repeat across the two Entry Timeframes (same convention as every other Rule Set, e.g.
    donchian_breakout_20_10 names both its H1 and M5 candidates identically) — identity is the
    (name, timeframe) pair, not the name alone."""
    market_filtered = [c for c in build_candidates() if isinstance(c, MarketFilteredCandidate)]
    keys = [(c.name, c.timeframe) for c in market_filtered]
    assert len(keys) == len(set(keys))
