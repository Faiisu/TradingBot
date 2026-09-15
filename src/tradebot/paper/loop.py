import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from tradebot.dashboard.state import build_state, write_state
from tradebot.data.real_yield import refresh_real_yield_cache
from tradebot.indicators import atr
from tradebot.paper.simulated_broker import SimulatedBroker
from tradebot.strategies.base import DataRequirement, StrategyCandidate
from tradebot.strategies.registry import REFERENCE_MARKETS
from tradebot.timeframe import TIMEFRAME_SECONDS, Timeframe, to_mt5_timeframe

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
CACHE_DIR = DATA_DIR / "cache"
DEFAULT_STATE_PATH = DATA_DIR / "paper_state.json"
DEFAULT_STOP_PATH = DATA_DIR / "paper_trading.stop"


def member_key(candidate: StrategyCandidate) -> str:
    """Candidate names repeat across timeframes (macd_12_26_9 runs on H1, M30, M15, M5), so per-member
    bookkeeping must key on name and timeframe together."""
    return f"{candidate.name}__{candidate.timeframe.value}"


def decide_and_update(
    candidate: StrategyCandidate,
    broker: SimulatedBroker,
    recent_ohlcv: pd.DataFrame,
    supporting: dict[DataRequirement, pd.DataFrame] | None = None,
) -> float | None:
    """Returns the last close price processed, or None if there was no data to act on."""
    if len(recent_ohlcv) == 0:
        return None
    signal_series = candidate.generate_signals(recent_ohlcv, supporting)
    atr_series = atr(recent_ohlcv["high"], recent_ohlcv["low"], recent_ohlcv["close"], period=broker.atr_period)
    last = recent_ohlcv.iloc[-1]
    last_close = float(last["close"])
    broker.on_bar(
        time=recent_ohlcv.index[-1],
        open_=float(last["open"]),
        high=float(last["high"]),
        low=float(last["low"]),
        close=last_close,
        signal=float(signal_series.iloc[-1]),
        atr_at_bar=float(atr_series.iloc[-1]),
    )
    return last_close


def seconds_until_next_bar_close(timeframe: Timeframe, now: datetime) -> float:
    interval = TIMEFRAME_SECONDS[timeframe]
    return interval - (now.timestamp() % interval)


def fetch_recent_bars(mt5_api, symbol: str, timeframe: Timeframe, count: int) -> pd.DataFrame:
    """Latest *closed* bars, oldest first. Position 0 in MT5 is the bar still forming, so this starts at 1 —
    otherwise every decision would be made on an incomplete bar a few seconds old. MT5's Python API has no
    streaming/push callback, so the loop polls this after each bar close."""
    rates = mt5_api.copy_rates_from_pos(symbol, to_mt5_timeframe(timeframe), 1, count)
    if rates is None or len(rates) == 0:
        return pd.DataFrame(columns=["open", "high", "low", "close", "tick_volume"])
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df.set_index("time")[["open", "high", "low", "close", "tick_volume"]]


def wait_or_stop(seconds: float, stop_path: Path | None, poll_seconds: float = 1.0) -> bool:
    """Sleeps in short slices so a stop request is noticed within ~poll_seconds. Returns True if a stop
    was requested."""
    deadline = time.monotonic() + seconds
    while True:
        if stop_path is not None and stop_path.exists():
            return True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False
        time.sleep(min(poll_seconds, remaining))


def resolve_requirement_data(
    mt5_api, symbol: str, requirement: DataRequirement, lookback_bars: int, fetch_csv=None
) -> tuple[pd.DataFrame, tuple[str, int | None] | None]:
    """One supporting-data requirement's live data, dispatched by source: the traded instrument's own
    Timeframe or an MT5-backed Reference Market (DXY, silver) both come from fetch_recent_bars, live
    every tick; a FRED-backed Reference Market (real yield) refreshes at most once a day and falls
    back to its stale cache on a failed download (data/real_yield.py) rather than crashing the loop.
    Returns (data, staleness_info); staleness_info is None except for a FRED-backed market, where it's
    (market_name, age_in_business_days) — surfaced so the dashboard can explain why a member might be
    holding back new entries, without duplicating MarketFilteredCandidate's own gating logic here."""
    if requirement.reference_market is None:
        return fetch_recent_bars(mt5_api, symbol, requirement.timeframe, lookback_bars), None

    config = REFERENCE_MARKETS[requirement.reference_market]
    if config.symbol is not None:
        return fetch_recent_bars(mt5_api, config.symbol, requirement.timeframe, lookback_bars), None

    if config.fred_series_id is not None:
        path = CACHE_DIR / f"{requirement.reference_market}.parquet"
        df, error = refresh_real_yield_cache(path, series_id=config.fred_series_id, fetch_csv=fetch_csv)
        if error is not None:
            print(
                f"[{datetime.now(timezone.utc).isoformat()}] WARNING: {requirement.reference_market} refresh "
                f"failed, using cached data ({error})",
                flush=True,
            )
        # Wall-clock "now", not any candidate's own entry-bar timestamp — this age is for the
        # dashboard's "is this stale right now" display (dashboard/state.py), a separate question
        # from the per-bar age MarketFilteredCandidate computes internally to decide each signal (see
        # market_filter.py's _age_in_business_days, which measures against the entry bar's own time).
        # The two would only disagree by the sub-tick delay between fetching here and generate_signals
        # running moments later — immaterial next to a 3-business-day threshold.
        age = None if df.empty else int(np.busday_count(df.index.max().date(), datetime.now(timezone.utc).date()))
        return df, (requirement.reference_market, age)

    raise ValueError(f"Reference Market {requirement.reference_market!r} has neither an MT5 symbol nor a FRED series id configured")


def update_member(
    mt5_api,
    symbol: str,
    candidate: StrategyCandidate,
    broker: SimulatedBroker,
    lookback_bars: int,
    last_bar_time: pd.Timestamp | None,
    fetch_csv=None,
) -> tuple[bool, pd.Timestamp | None, float | None, dict[str, int]]:
    """Feeds the member its latest closed bar. Returns (processed, bar_time, last_close,
    reference_market_ages) — the last element names, for every FRED-backed Reference Market this
    candidate's requirements touched, how many business days old its latest usable value is. A bar
    that was already processed is skipped — while the market is closed MT5 keeps returning the same
    final bar, and replaying it could re-trigger a stop-out and re-entry on stale prices."""
    recent = fetch_recent_bars(mt5_api, symbol, candidate.timeframe, lookback_bars)
    if recent.empty:
        return False, last_bar_time, None, {}
    bar_time = recent.index[-1]
    if last_bar_time is not None and bar_time <= last_bar_time:
        return False, last_bar_time, None, {}

    supporting: dict[DataRequirement, pd.DataFrame] = {}
    reference_market_ages: dict[str, int] = {}
    for requirement in getattr(candidate, "supporting_data", ()):
        data, staleness_info = resolve_requirement_data(mt5_api, symbol, requirement, lookback_bars, fetch_csv=fetch_csv)
        supporting[requirement] = data
        if staleness_info is not None:
            market, age = staleness_info
            if age is not None:
                reference_market_ages[market] = age

    last_close = decide_and_update(candidate, broker, recent, supporting)
    return True, bar_time, last_close, reference_market_ages


def run_paper_trading_loop(
    mt5_api,
    symbol: str,
    members: list[tuple[StrategyCandidate, SimulatedBroker]],
    lookback_bars: int = 250,
    buffer_seconds: float = 5.0,
    state_path: Path = DEFAULT_STATE_PATH,
    stop_path: Path | None = DEFAULT_STOP_PATH,
) -> None:
    """Polls the smallest timeframe in use for each newly closed bar, and updates every Ensemble member
    whose timeframe just closed a bar too (a multiple of the smallest). Runs until interrupted (Ctrl+C) or
    until stop_path appears (the dashboard's Stop button — see paper/supervisor.py). Never places a real
    order — every update below is SimulatedBroker bookkeeping only.

    Writes state_path at startup and after every tick so a separate dashboard process can read and display
    it — decoupled via a file rather than an in-process server, so the dashboard can be started, stopped,
    or crash independently of this loop."""
    timeframes_in_use = sorted({candidate.timeframe for candidate, _ in members}, key=lambda tf: TIMEFRAME_SECONDS[tf])
    smallest = timeframes_in_use[0]
    session_started_at = datetime.now(timezone.utc).isoformat()

    print(
        f"Starting paper trading loop for {len(members)} member(s) across timeframes "
        f"{[tf.value for tf in timeframes_in_use]}",
        flush=True,
    )
    equity_history: list[dict] = []
    recent_trades: list[dict] = []
    last_close_by_member: dict[str, float] = {}
    last_bar_time_by_member: dict[str, pd.Timestamp] = {}
    reference_market_age_business_days: dict[str, int] = {}

    def save_state() -> None:
        equity_history.append(
            {"time": datetime.now(timezone.utc).isoformat(), "equity": sum(broker.equity for _, broker in members)}
        )
        state = build_state(
            members, equity_history, recent_trades, last_close_by_member, session_started_at, reference_market_age_business_days
        )
        write_state(state, state_path)

    save_state()

    tick = 0
    try:
        while True:
            sleep_seconds = seconds_until_next_bar_close(smallest, datetime.now(timezone.utc)) + buffer_seconds
            if wait_or_stop(sleep_seconds, stop_path):
                print("Stop requested — exiting cleanly.", flush=True)
                break
            tick += 1

            for candidate, broker in members:
                multiple = TIMEFRAME_SECONDS[candidate.timeframe] // TIMEFRAME_SECONDS[smallest]
                if tick % multiple != 0:
                    continue
                key = member_key(candidate)
                trades_before = len(broker.trades)
                processed, bar_time, last_close, reference_market_ages = update_member(
                    mt5_api, symbol, candidate, broker, lookback_bars, last_bar_time_by_member.get(key)
                )
                if not processed:
                    print(f"[{datetime.now(timezone.utc).isoformat()}] {key}: no new closed bar, skipped", flush=True)
                    continue
                last_bar_time_by_member[key] = bar_time
                reference_market_age_business_days.update(reference_market_ages)
                if last_close is not None:
                    last_close_by_member[key] = last_close
                if len(broker.trades) > trades_before:
                    new_trade = broker.trades[-1]
                    recent_trades.append(
                        {
                            "candidate_name": candidate.name,
                            "timeframe": candidate.timeframe.value,
                            "direction": new_trade.direction,
                            "entry_time": str(new_trade.entry_time),
                            "exit_time": str(new_trade.exit_time),
                            "entry_price": new_trade.entry_price,
                            "exit_price": new_trade.exit_price,
                            "pnl_pct": new_trade.pnl_pct * 100,
                            "exit_reason": new_trade.exit_reason,
                        }
                    )

                position_state = "flat" if broker.position is None else f"direction={broker.position.direction}"
                print(
                    f"[{datetime.now(timezone.utc).isoformat()}] {key} bar {bar_time}: "
                    f"equity={broker.equity:.4f}, {position_state}, trades={len(broker.trades)}",
                    flush=True,
                )

            save_state()
    finally:
        save_state()
        if stop_path is not None and stop_path.exists():
            stop_path.unlink()
