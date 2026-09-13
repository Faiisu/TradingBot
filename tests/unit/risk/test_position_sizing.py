from tradebot.risk.position_sizing import position_fraction


def test_sizes_down_for_a_wide_stop():
    fraction = position_fraction(entry_price=100, stop_distance=2, risk_pct_per_trade=0.01, max_position_fraction=5.0)
    assert fraction == 0.5


def test_caps_at_max_position_fraction_for_a_tight_stop():
    fraction = position_fraction(entry_price=100, stop_distance=0.1, risk_pct_per_trade=0.01, max_position_fraction=5.0)
    assert fraction == 5.0


def test_zero_stop_distance_yields_zero_fraction():
    fraction = position_fraction(entry_price=100, stop_distance=0, risk_pct_per_trade=0.01, max_position_fraction=5.0)
    assert fraction == 0.0
