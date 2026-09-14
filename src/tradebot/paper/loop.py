import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from tradebot.dashboard.state import build_state, write_state
from tradebot.indicators import atr
from tradebot.paper.simulated_broker import SimulatedBroker
from tradebot.strategies.base import StrategyCandidate
from tradebot.timeframe import TIMEFRAME_SECONDS, Timeframe, to_mt5_timeframe

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data"
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
    htf_ohlcv: pd.DataFrame | None = None,
) -> float | None:
    """Returns the last close price processed, or None if there was no data to act on."""
    if len(recent_ohlcv) == 0:
        return None
    signal_series = candidate.generate_signals(recent_ohlcv, htf_ohlcv)
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
        return pd.DataFrame(columns=["open", "high", "low", "close"])
    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df.set_index("time")[["open", "high", "low", "close"]]


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


def update_member(
    mt5_api,
    symbol: str,
    candidate: StrategyCandidate,
    broker: SimulatedBroker,
    lookback_bars: int,
    last_bar_time: pd.Timestamp | None,
) -> tuple[bool, pd.Timestamp | None, float | None]:
    """Feeds the member its latest closed bar. Returns (processed, bar_time, last_close). A bar that was
    already processed is skipped — while the market is closed MT5 keeps returning the same final bar, and
    replaying it could re-trigger a stop-out and re-entry on stale prices."""
    recent = fetch_recent_bars(mt5_api, symbol, candidate.timeframe, lookback_bars)
    if recent.empty:
        return False, last_bar_time, None
    bar_time = recent.index[-1]
    if last_bar_time is not None and bar_time <= last_bar_time:
        return False, last_bar_time, None

    filter_timeframe = getattr(candidate, "filter_timeframe", None)
    htf_recent = fetch_recent_bars(mt5_api, symbol, filter_timeframe, lookback_bars) if filter_timeframe else None
    last_close = decide_and_update(candidate, broker, recent, htf_recent)
    return True, bar_time, last_close


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

    def save_state() -> None:
        equity_history.append(
            {"time": datetime.now(timezone.utc).isoformat(), "equity": sum(broker.equity for _, broker in members)}
        )
        state = build_state(members, equity_history, recent_trades, last_close_by_member, session_started_at)
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
                processed, bar_time, last_close = update_member(
                    mt5_api, symbol, candidate, broker, lookback_bars, last_bar_time_by_member.get(key)
                )
                if not processed:
                    print(f"[{datetime.now(timezone.utc).isoformat()}] {key}: no new closed bar, skipped", flush=True)
                    continue
                last_bar_time_by_member[key] = bar_time
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
