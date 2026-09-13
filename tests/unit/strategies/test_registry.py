from tradebot.strategies.mtf import MtfCandidate
from tradebot.strategies.registry import build_candidates
from tradebot.timeframe import Timeframe


def test_build_candidates_returns_single_timeframe_plus_mtf():
    candidates = build_candidates()

    single_timeframe = [c for c in candidates if not isinstance(c, MtfCandidate)]
    mtf = [c for c in candidates if isinstance(c, MtfCandidate)]

    assert len(single_timeframe) == 20  # 5 rule sets x 4 timeframes (H1, M30, M15, M5)
    assert len(mtf) == 9  # 3 entry rule sets x 3 filters
    assert len(candidates) == 29


def test_mtf_candidates_all_trade_m15_filtered_by_h1():
    mtf = [c for c in build_candidates() if isinstance(c, MtfCandidate)]

    assert all(c.timeframe == Timeframe.M15 for c in mtf)
    assert all(c.filter_timeframe == Timeframe.H1 for c in mtf)


def test_mtf_candidates_have_unique_names():
    mtf = [c for c in build_candidates() if isinstance(c, MtfCandidate)]
    names = [c.name for c in mtf]
    assert len(names) == len(set(names))


def test_single_timeframe_candidates_have_no_filter_timeframe():
    single_timeframe = [c for c in build_candidates() if not isinstance(c, MtfCandidate)]
    assert all(getattr(c, "filter_timeframe", None) is None for c in single_timeframe)
