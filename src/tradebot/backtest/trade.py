from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Trade:
    direction: int  # 1 long, -1 short
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    entry_price: float
    exit_price: float
    stop_price: float
    position_fraction: float
    cost_pct: float  # transaction (spread) cost charged against pnl_pct, leveraged by position_fraction
    swap_pct: float  # overnight holding cost/credit charged against pnl_pct, leveraged by position_fraction
    pnl_pct: float  # net return contributed to equity by this trade, after cost_pct and swap_pct
    exit_reason: str  # "signal_change", "stop_loss", "trailing_stop", or "profit_target"
