import pandas as pd


def count_rollover_nights(entry_time: pd.Timestamp, exit_time: pd.Timestamp) -> int:
    """Counts broker daily-rollover charges between entry and exit. Standard forex/CFD convention:
    no separate charge for nights crossing into Saturday/Sunday (market closed); that cost is instead
    bundled into a 3x charge on the Wednesday-to-Thursday rollover. This is an approximation — it
    doesn't know the broker's exact rollover time, only the calendar date of each bar timestamp."""
    if exit_time <= entry_time:
        return 0

    entry_date = entry_time.normalize()
    exit_date = exit_time.normalize()

    total = 0
    current = entry_date + pd.Timedelta(days=1)
    while current <= exit_date:
        if current.dayofweek in (5, 6):  # Saturday, Sunday: bundled into Wednesday's rollover instead
            pass
        elif current.dayofweek == 3:  # Thursday: the Wed-night rollover, carries the weekend
            total += 3
        else:
            total += 1
        current += pd.Timedelta(days=1)
    return total


def swap_price(points: float, point_value: float, nights_held: int) -> float:
    return points * point_value * nights_held
