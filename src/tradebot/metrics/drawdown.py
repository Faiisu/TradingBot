import pandas as pd


def max_drawdown_pct(equity_curve: pd.Series) -> float:
    drawdown = equity_curve / equity_curve.cummax() - 1
    return abs(float(drawdown.min())) * 100
