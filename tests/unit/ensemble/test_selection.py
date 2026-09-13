import pandas as pd
import pytest

from tradebot.backtest.result import BacktestResult
from tradebot.ensemble.selection import load_ensemble, save_ensemble, select_ensemble


def _fake_result(name: str, equity_values: list[float]) -> BacktestResult:
    equity_curve = pd.Series(equity_values)
    drawdown_series = equity_curve / equity_curve.cummax() - 1
    return BacktestResult(
        candidate_name=name,
        timeframe="H1",
        trades=[],
        equity_curve=equity_curve,
        drawdown_series=drawdown_series,
    )


def test_only_profitable_candidates_join_the_ensemble():
    results = [
        _fake_result("winner_a", [1.0, 1.2, 1.5]),  # net profitable
        _fake_result("winner_b", [1.0, 1.1, 1.3]),  # net profitable
        _fake_result("loser", [1.0, 0.9, 0.7]),  # net losing
    ]
    ensemble = select_ensemble(results)

    names = {member.candidate_name for member in ensemble.members}
    assert names == {"winner_a", "winner_b"}


def test_capital_splits_equally_across_qualifying_members():
    results = [
        _fake_result("a", [1.0, 1.5]),
        _fake_result("b", [1.0, 1.2]),
    ]
    ensemble = select_ensemble(results)

    assert len(ensemble.members) == 2
    for member in ensemble.members:
        assert member.capital_fraction == pytest.approx(0.5)


def test_empty_ensemble_when_nothing_qualifies():
    results = [_fake_result("loser", [1.0, 0.5])]
    ensemble = select_ensemble(results)
    assert ensemble.members == []


def test_flat_equity_curve_does_not_qualify():
    # exactly zero return -> performance_metric == 0, threshold is exclusive
    results = [_fake_result("flat", [1.0, 1.0, 1.0])]
    ensemble = select_ensemble(results)
    assert ensemble.members == []


def test_save_and_load_ensemble_round_trips(tmp_path):
    results = [_fake_result("a", [1.0, 1.5]), _fake_result("b", [1.0, 1.2])]
    ensemble = select_ensemble(results)

    path = tmp_path / "ensemble.json"
    save_ensemble(ensemble, path)
    loaded = load_ensemble(path)

    assert loaded == ensemble
