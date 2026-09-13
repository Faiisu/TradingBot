import pandas as pd
import pytest

from tradebot.risk.swap import count_rollover_nights, swap_price


def test_no_nights_within_the_same_day():
    entry = pd.Timestamp("2024-01-02 10:00")
    exit_ = pd.Timestamp("2024-01-02 18:00")
    assert count_rollover_nights(entry, exit_) == 0


def test_one_night_for_a_single_weekday_hold():
    # Monday 10:00 -> Tuesday 10:00: one rollover, not Wednesday
    entry = pd.Timestamp("2024-01-01 10:00")  # Monday
    exit_ = pd.Timestamp("2024-01-02 10:00")  # Tuesday
    assert count_rollover_nights(entry, exit_) == 1


def test_wednesday_rollover_counts_triple():
    # Wednesday 10:00 -> Thursday 10:00: crosses into Thursday = the triple-swap night
    entry = pd.Timestamp("2024-01-03 10:00")  # Wednesday
    exit_ = pd.Timestamp("2024-01-04 10:00")  # Thursday
    assert count_rollover_nights(entry, exit_) == 3


def test_weekend_crossing_does_not_double_charge():
    # Friday 10:00 -> Monday 10:00: crosses into Sat, Sun (free), Mon (1 normal night) -> just 1
    entry = pd.Timestamp("2024-01-05 10:00")  # Friday
    exit_ = pd.Timestamp("2024-01-08 10:00")  # Monday
    assert count_rollover_nights(entry, exit_) == 1


def test_full_week_hold_totals_seven_charged_nights():
    # Monday -> next Monday: crossings into Tue(1), Wed(1), Thu(3, the weekend-carrying rollover),
    # Fri(1), Sat(0, free), Sun(0, free), Mon(1) = 7
    entry = pd.Timestamp("2024-01-01 10:00")  # Monday
    exit_ = pd.Timestamp("2024-01-08 10:00")  # next Monday
    assert count_rollover_nights(entry, exit_) == 7


def test_swap_price_scales_with_points_and_nights():
    assert swap_price(points=-534.9, point_value=0.001, nights_held=1) == pytest.approx(-0.5349)
    assert swap_price(points=-534.9, point_value=0.001, nights_held=3) == pytest.approx(-1.6047)
    assert swap_price(points=0.0, point_value=0.001, nights_held=5) == 0.0
