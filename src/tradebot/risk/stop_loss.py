def atr_stop_distance(atr_at_entry: float, multiplier: float = 2.0) -> float:
    return multiplier * atr_at_entry


def stop_price(entry_price: float, stop_distance: float, direction: int) -> float:
    """direction: 1 for long, -1 for short."""
    return entry_price - direction * stop_distance
