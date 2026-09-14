import pandas as pd
import pytest

from tradebot.backtest.result import BacktestResult
from tradebot.ensemble.selection import load_ensemble, save_ensemble, select_ensemble
from tradebot.timeframe import Timeframe


class _FakeCandidate:
    """entry_strategy=None means a plain (unfiltered) candidate; set it to simulate an MTF/Market-
    Filtered variant wrapping that base candidate, the way MtfCandidate does."""

    def __init__(self, name: str, timeframe: Timeframe = Timeframe.H1, entry_strategy=None):
        self.name = name
        self.timeframe = timeframe
        if entry_strategy is not None:
            self.entry_strategy = entry_strategy


def _fake_result(name: str, equity_values: list[float], timeframe: str = "H1") -> BacktestResult:
    equity_curve = pd.Series(equity_values)
    drawdown_series = equity_curve / equity_curve.cummax() - 1
    return BacktestResult(
        candidate_name=name,
        timeframe=timeframe,
        trades=[],
        equity_curve=equity_curve,
        drawdown_series=drawdown_series,
    )


def _pair(name: str, equity_values: list[float], *, timeframe: Timeframe = Timeframe.H1, entry_strategy=None):
    candidate = _FakeCandidate(name, timeframe, entry_strategy)
    result = _fake_result(name, equity_values, timeframe.value)
    return candidate, result


def test_only_profitable_candidates_join_the_ensemble():
    pairs = [
        _pair("winner_a", [1.0, 1.2, 1.5]),  # net profitable
        _pair("winner_b", [1.0, 1.1, 1.3], timeframe=Timeframe.M15),  # net profitable, different pair
        _pair("loser", [1.0, 0.9, 0.7], timeframe=Timeframe.M30),  # net losing
    ]
    ensemble = select_ensemble(pairs)

    names = {member.candidate_name for member in ensemble.members}
    assert names == {"winner_a", "winner_b"}


def test_capital_splits_equally_across_qualifying_members():
    pairs = [
        _pair("a", [1.0, 1.5]),
        _pair("b", [1.0, 1.2], timeframe=Timeframe.M15),
    ]
    ensemble = select_ensemble(pairs)

    assert len(ensemble.members) == 2
    for member in ensemble.members:
        assert member.capital_fraction == pytest.approx(0.5)


def test_empty_ensemble_when_nothing_qualifies():
    pairs = [_pair("loser", [1.0, 0.5])]
    ensemble = select_ensemble(pairs)
    assert ensemble.members == []


def test_flat_equity_curve_does_not_qualify():
    # exactly zero return -> performance_metric == 0, threshold is exclusive
    pairs = [_pair("flat", [1.0, 1.0, 1.0])]
    ensemble = select_ensemble(pairs)
    assert ensemble.members == []


def test_save_and_load_ensemble_round_trips(tmp_path):
    pairs = [_pair("a", [1.0, 1.5]), _pair("b", [1.0, 1.2], timeframe=Timeframe.M15)]
    ensemble = select_ensemble(pairs)

    path = tmp_path / "ensemble.json"
    save_ensemble(ensemble, path)
    loaded = load_ensemble(path)

    assert loaded == ensemble


def test_at_most_one_member_per_rule_set_and_entry_timeframe():
    """An unfiltered candidate and its MTF-filtered variants share a (Rule Set, Entry Timeframe) —
    only the best Performance Metric among them should ever enter the Ensemble."""
    base = _FakeCandidate("macd_12_26_9", Timeframe.M15)
    unfiltered = _pair("macd_12_26_9", [1.0, 1.5], timeframe=Timeframe.M15)  # +50%
    mtf_better = _pair(
        "macd_12_26_9_mtf_macd_H1filter", [1.0, 2.0], timeframe=Timeframe.M15, entry_strategy=base
    )  # +100%, wins the pair
    mtf_worse = _pair(
        "macd_12_26_9_mtf_ema_slope_H1filter", [1.0, 1.2], timeframe=Timeframe.M15, entry_strategy=base
    )  # +20%, loses the pair
    unrelated = _pair("ma_crossover_20_50", [1.0, 1.3], timeframe=Timeframe.M15)  # different Rule Set, unaffected

    ensemble = select_ensemble([unfiltered, mtf_better, mtf_worse, unrelated])

    names = {member.candidate_name for member in ensemble.members}
    assert names == {"macd_12_26_9_mtf_macd_H1filter", "ma_crossover_20_50"}


def test_the_pair_limit_is_per_entry_timeframe_not_just_per_rule_set():
    """The same Rule Set on two different Entry Timeframes is two separate pairs — both may qualify."""
    pairs = [
        _pair("macd_12_26_9", [1.0, 1.5], timeframe=Timeframe.M15),
        _pair("macd_12_26_9", [1.0, 1.3], timeframe=Timeframe.H1),
    ]
    ensemble = select_ensemble(pairs)

    assert {(m.candidate_name, m.timeframe) for m in ensemble.members} == {
        ("macd_12_26_9", "M15"),
        ("macd_12_26_9", "H1"),
    }
