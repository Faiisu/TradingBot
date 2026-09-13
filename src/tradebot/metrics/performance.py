import pandas as pd

from tradebot.metrics.drawdown import max_drawdown_pct

EPSILON = 0.01
ENSEMBLE_METRIC_THRESHOLD = 0.0


def total_return_pct(equity_curve: pd.Series) -> float:
    return (float(equity_curve.iloc[-1]) / float(equity_curve.iloc[0]) - 1) * 100


def performance_metric(equity_curve: pd.Series) -> float:
    """Calmar-like ratio: return % per unit of max drawdown %. Higher is better; >0 means net profitable."""
    return_pct = total_return_pct(equity_curve)
    drawdown_pct = max(max_drawdown_pct(equity_curve), EPSILON)
    return return_pct / drawdown_pct
