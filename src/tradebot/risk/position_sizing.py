def position_fraction(entry_price: float, stop_distance: float, risk_pct_per_trade: float, max_position_fraction: float) -> float:
    """Fraction of equity notionally exposed, sized so a stop-loss hit loses risk_pct_per_trade of equity."""
    if stop_distance <= 0:
        return 0.0
    fraction = risk_pct_per_trade / (stop_distance / entry_price)
    return min(fraction, max_position_fraction)
