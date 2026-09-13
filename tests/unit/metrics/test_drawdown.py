import pandas as pd
import pytest

from tradebot.metrics.drawdown import max_drawdown_pct


def test_max_drawdown_matches_hand_calculation():
    equity_curve = pd.Series([1.0, 1.2, 0.9, 1.1])
    assert max_drawdown_pct(equity_curve) == pytest.approx(25.0)


def test_zero_drawdown_for_monotonic_equity():
    equity_curve = pd.Series([1.0, 1.1, 1.2, 1.3])
    assert max_drawdown_pct(equity_curve) == 0.0
