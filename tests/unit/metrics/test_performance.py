import pandas as pd
import pytest

from tradebot.metrics.performance import performance_metric, total_return_pct


def test_total_return_matches_hand_calculation():
    equity_curve = pd.Series([1.0, 1.5])
    assert total_return_pct(equity_curve) == pytest.approx(50.0)

    equity_curve = pd.Series([1.0, 0.8])
    assert total_return_pct(equity_curve) == pytest.approx(-20.0)


def test_performance_metric_divides_return_by_drawdown():
    equity_curve = pd.Series([1.0, 1.5, 1.125, 1.5])  # +50% return, 25% max drawdown
    assert performance_metric(equity_curve) == pytest.approx(2.0)


def test_performance_metric_is_negative_for_a_losing_curve():
    equity_curve = pd.Series([1.0, 0.8, 0.9])
    assert performance_metric(equity_curve) < 0


def test_performance_metric_uses_epsilon_guard_for_zero_drawdown():
    equity_curve = pd.Series([1.0, 1.1, 1.2])  # monotonic, zero drawdown
    metric = performance_metric(equity_curve)
    assert metric == pytest.approx(total_return_pct(equity_curve) / 0.01)
