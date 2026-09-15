import time
from datetime import datetime, timedelta, timezone
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


def nominal_bar_close(now: datetime, smallest: Timeframe) -> datetime:
    """The wall-clock close time of the most recently completed `smallest`-Timeframe bar as of `now`
    (run_paper_trading_loop calls this within buffer_seconds of that close). Every Timeframe closes
    only at multiples of its own length in seconds since the epoch, and every larger Timeframe in use
    is an exact multiple of `smallest` — so rounding `now` down to this one boundary, and comparing
    against it (see timeframe_closed_at), tells each member whether this is one of its own bar closes
    without counting how many outer-loop iterations have run since the loop happened to start. Ticket
    01: that counting is what let an H1 member fire up to 55 minutes late, depending on the arbitrary
    moment the loop was launched."""
    seconds_into_bar = now.timestamp() % TIMEFRAME_SECONDS[smallest]
    return now - timedelta(seconds=seconds_into_bar)


def timeframe_closed_at(timeframe: Timeframe, nominal_close: datetime) -> bool:
    """Whether `nominal_close` (a smallest-Timeframe boundary from nominal_bar_close) is also one of
    `timeframe`'s own boundaries."""
    return nominal_close.timestamp() % TIMEFRAME_SECONDS[timeframe] == 0


def missed_nominal_closes(
    previous: datetime | None, current: datetime, smallest: Timeframe, max_catch_up: int = 12
) -> list[datetime]:
    """Every smallest-Timeframe boundary from just after `previous` up to and including `current`.
    Normally that's just `[current]` — but if one iteration of the loop ran long enough (a slow MT5
    call, a GC pause) that wall-clock time crossed more than one smallest-Timeframe boundary before the
    next iteration checked, using only `current` would silently skip whichever boundaries fell in
    between — permanently, for any larger Timeframe whose own boundary was among them, since the next
    check for it is up to a full Timeframe length later. Backfilling those boundaries here means a
    larger-Timeframe member still gets processed (late, with that lateness visible via
    decision_latency_seconds) instead of never at all. Capped at `max_catch_up` (nearest `current`) so
    a long gap — the machine suspended, not just one slow tick — doesn't replay hours of stale ticks."""
    step = TIMEFRAME_SECONDS[smallest]
    if previous is None:
        return [current]
    elapsed_steps = round((current.timestamp() - previous.timestamp()) / step)
    if elapsed_steps <= 1:
        return [current]
    elapsed_steps = min(elapsed_steps, max_catch_up)
    return [current - timedelta(seconds=step * i) for i in range(elapsed_steps - 1, -1, -1)]


def decision_latency_seconds(bar_time: pd.Timestamp, decided_at: datetime) -> float:
    """Seconds between a bar's own close time and the moment it was actually decided on — surfaced on
    the dashboard so a delay like ticket 01's bug is visible instead of silent. `bar_time` comes from
    fetch_recent_bars as a timezone-naive Timestamp built from MT5's UTC epoch seconds; it is treated
    as UTC, matching broker server time (see CONTEXT.md)."""
    bar_time_utc = bar_time.tz_localize("UTC") if bar_time.tzinfo is None else bar_time.tz_convert("UTC")
    return (pd.Timestamp(decided_at) - bar_time_utc).total_seconds()


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


def run_tick(
    now: datetime,
    nominal_close: datetime,
    mt5_api,
    symbol: str,
    members: list[tuple[StrategyCandidate, SimulatedBroker]],
    lookback_bars: int,
    last_bar_time_by_member: dict[str, pd.Timestamp],
    decision_latency_by_member: dict[str, float],
    reference_market_age_business_days: dict[str, int],
    recent_trades: list[dict],
    last_close_by_member: dict[str, float] | None = None,
) -> None:
    """Updates every member whose own Timeframe closed a bar as of `nominal_close` — a smallest-
    Timeframe boundary decided by wall-clock alignment (nominal_bar_close/timeframe_closed_at) rather
    than by counting how many wake-ups have happened since the loop started (see ticket 01).
    `nominal_close` and `now` (the actual wall-clock moment this runs) are separate parameters because
    the catch-up scheduler (missed_nominal_closes) can call this once per boundary a slow iteration
    skipped past — gating uses `nominal_close`, but decision_latency_seconds is measured against the
    real `now`, so a slow-processing incident is visible on the dashboard instead of hidden. Mutates
    last_bar_time_by_member, decision_latency_by_member, reference_market_age_business_days,
    recent_trades and last_close_by_member in place."""
    last_close_by_member = {} if last_close_by_member is None else last_close_by_member

    for candidate, broker in members:
        if not timeframe_closed_at(candidate.timeframe, nominal_close):
            continue
        key = member_key(candidate)
        trades_before = len(broker.trades)
        processed, bar_time, last_close, reference_market_ages = update_member(
            mt5_api, symbol, candidate, broker, lookback_bars, last_bar_time_by_member.get(key)
        )
        if not processed:
            print(f"[{now.isoformat()}] {key}: no new closed bar, skipped", flush=True)
            continue
        last_bar_time_by_member[key] = bar_time
        decision_latency_by_member[key] = decision_latency_seconds(bar_time, now)
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
            f"[{now.isoformat()}] {key} bar {bar_time}: "
            f"equity={broker.equity:.4f}, {position_state}, trades={len(broker.trades)}, "
            f"decision_latency={decision_latency_by_member[key]:.1f}s",
            flush=True,
        )


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
    whose own timeframe closed a bar too, via run_tick. Runs until interrupted (Ctrl+C) or until
    stop_path appears (the dashboard's Stop button — see paper/supervisor.py). Never places a real
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
    decision_latency_by_member: dict[str, float] = {}
    reference_market_age_business_days: dict[str, int] = {}

    def save_state() -> None:
        equity_history.append(
            {"time": datetime.now(timezone.utc).isoformat(), "equity": sum(broker.equity for _, broker in members)}
        )
        state = build_state(
            members,
            equity_history,
            recent_trades,
            last_close_by_member,
            session_started_at,
            reference_market_age_business_days,
            decision_latency_by_member,
        )
        write_state(state, state_path)

    save_state()

    last_nominal_close: datetime | None = None
    try:
        while True:
            sleep_seconds = seconds_until_next_bar_close(smallest, datetime.now(timezone.utc)) + buffer_seconds
            if wait_or_stop(sleep_seconds, stop_path):
                print("Stop requested — exiting cleanly.", flush=True)
                break

            now = datetime.now(timezone.utc)
            current_nominal_close = nominal_bar_close(now, smallest)
            for nominal_close in missed_nominal_closes(last_nominal_close, current_nominal_close, smallest):
                run_tick(
                    now,
                    nominal_close,
                    mt5_api,
                    symbol,
                    members,
                    lookback_bars,
                    last_bar_time_by_member,
                    decision_latency_by_member,
                    reference_market_age_business_days,
                    recent_trades,
                    last_close_by_member,
                )
            last_nominal_close = current_nominal_close
            save_state()
    finally:
        save_state()
        if stop_path is not None and stop_path.exists():
            stop_path.unlink()
