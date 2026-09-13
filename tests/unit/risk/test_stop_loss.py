from tradebot.risk.stop_loss import atr_stop_distance, stop_price


def test_atr_stop_distance_scales_by_multiplier():
    assert atr_stop_distance(atr_at_entry=1.5, multiplier=2.0) == 3.0


def test_stop_price_below_entry_for_long():
    assert stop_price(entry_price=100, stop_distance=4, direction=1) == 96


def test_stop_price_above_entry_for_short():
    assert stop_price(entry_price=100, stop_distance=4, direction=-1) == 104
