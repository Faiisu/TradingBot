import pandas as pd

from tradebot.risk.risk_controls import RiskControls


def test_bundles_stop_and_sizing_consistently():
    controls = RiskControls(risk_pct_per_trade=0.01, atr_stop_multiplier=2.0, max_position_fraction=5.0)
    assert controls.stop_distance(atr_at_entry=1.0) == 2.0
    assert controls.stop_price(entry_price=100, atr_at_entry=1.0, direction=1) == 98
    assert controls.position_fraction(entry_price=100, atr_at_entry=1.0) == 0.5


def test_cost_pct_scales_with_entry_price():
    controls = RiskControls(round_trip_cost_price=0.30)
    assert controls.cost_pct(entry_price=100) == 0.003
    assert controls.cost_pct(entry_price=2400) == 0.30 / 2400


def test_swap_pct_defaults_to_zero_when_unconfigured():
    controls = RiskControls()
    assert controls.swap_pct(100, 1, pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02")) == 0.0


def test_swap_pct_uses_direction_specific_points_and_nights():
    controls = RiskControls(swap_long_points=-500.0, swap_short_points=100.0, point_value=0.001)
    entry = pd.Timestamp("2024-01-01 10:00")  # Monday
    exit_ = pd.Timestamp("2024-01-02 10:00")  # Tuesday, 1 rollover night

    long_swap = controls.swap_pct(entry_price=2000, direction=1, entry_time=entry, exit_time=exit_)
    assert long_swap == (-500.0 * 0.001 * 1) / 2000

    short_swap = controls.swap_pct(entry_price=2000, direction=-1, entry_time=entry, exit_time=exit_)
    assert short_swap == (100.0 * 0.001 * 1) / 2000
