import pandas as pd

from tradebot.backtest.persistence import load_backtest_results, save_backtest_results
from tradebot.backtest.result import BacktestResult
from tradebot.backtest.trade import Trade
from tradebot.timeframe import Timeframe


class _StubCandidate:
    def __init__(self, name, timeframe, filter_name=None, filter_timeframe=None):
        self.name = name
        self.timeframe = timeframe
        self.filter_name = filter_name
        self.filter_timeframe = filter_timeframe


def _fake_trade(direction=1, pnl_pct=0.02) -> Trade:
    return Trade(
        direction=direction,
        entry_time=pd.Timestamp("2024-01-01"),
        exit_time=pd.Timestamp("2024-01-02"),
        entry_price=100.0,
        exit_price=102.0,
        stop_price=98.0,
        position_fraction=1.0,
        cost_pct=0.001,
        swap_pct=0.0,
        pnl_pct=pnl_pct,
        exit_reason="signal_change",
    )


def _fake_result(name: str, timeframe: str, trades: list[Trade], equity=(1.0, 1.02, 1.04)) -> BacktestResult:
    equity_curve = pd.Series(list(equity))
    drawdown_series = equity_curve / equity_curve.cummax() - 1
    return BacktestResult(
        candidate_name=name, timeframe=timeframe, trades=trades, equity_curve=equity_curve, drawdown_series=drawdown_series
    )


def test_save_and_load_round_trips_trades_and_summary_stats(tmp_path):
    candidate = _StubCandidate("macd_12_26_9", Timeframe.M15)
    result = _fake_result("macd_12_26_9", "M15", [_fake_trade(direction=1), _fake_trade(direction=-1, pnl_pct=-0.01)])

    path = tmp_path / "backtest_results.json"
    save_backtest_results([(candidate, result)], path)
    record = load_backtest_results(path)["candidates"][0]

    assert record["candidate_name"] == "macd_12_26_9"
    assert record["timeframe"] == "M15"
    assert record["filter_name"] is None
    assert record["filter_timeframe"] is None
    assert record["trade_count"] == 2
    assert [t["direction"] for t in record["trades"]] == [1, -1]
    assert "performance_metric" in record and "return_pct" in record and "max_drawdown_pct" in record


def test_save_records_run_time_and_window(tmp_path):
    path = tmp_path / "backtest_results.json"
    save_backtest_results(
        [(_StubCandidate("a", Timeframe.H1), _fake_result("a", "H1", []))],
        path,
        window_start=pd.Timestamp("2025-04-15 14:55"),
        window_end=pd.Timestamp("2026-09-11 20:55"),
    )
    payload = load_backtest_results(path)

    assert payload["generated_at"]
    assert payload["window_start"] == "2025-04-15 14:55:00"
    assert payload["window_end"] == "2026-09-11 20:55:00"


def test_save_captures_mtf_filter_metadata(tmp_path):
    candidate = _StubCandidate("macd_12_26_9_mtf_macd_H1filter", Timeframe.M15, filter_name="macd", filter_timeframe=Timeframe.H1)
    result = _fake_result("macd_12_26_9_mtf_macd_H1filter", "M15", [_fake_trade()])

    path = tmp_path / "backtest_results.json"
    save_backtest_results([(candidate, result)], path)
    record = load_backtest_results(path)["candidates"][0]

    assert record["filter_name"] == "macd"
    assert record["filter_timeframe"] == "H1"


def test_in_ensemble_follows_the_performance_metric_threshold(tmp_path):
    pairs = [
        (_StubCandidate("winner", Timeframe.H1), _fake_result("winner", "H1", [_fake_trade()], equity=(1.0, 1.1))),
        (_StubCandidate("loser", Timeframe.M5), _fake_result("loser", "M5", [], equity=(1.0, 0.9))),
    ]
    path = tmp_path / "backtest_results.json"
    save_backtest_results(pairs, path)
    candidates = load_backtest_results(path)["candidates"]

    assert candidates[0]["in_ensemble"] is True
    assert candidates[1]["in_ensemble"] is False
    assert candidates[1]["trade_count"] == 0
