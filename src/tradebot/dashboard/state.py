import json
import os
from datetime import datetime, timezone
from pathlib import Path

MAX_EQUITY_HISTORY = 1000
MAX_RECENT_TRADES = 50


def build_state(
    members,
    equity_history: list[dict],
    recent_trades: list[dict],
    last_close_by_member: dict[str, float],
    session_started_at: str | None = None,
) -> dict:
    total_equity = sum(broker.equity for _, broker in members)
    total_initial = sum(broker.initial_equity for _, broker in members)

    member_states = []
    for candidate, broker in members:
        position = None
        if broker.position is not None:
            # same "name__timeframe" key as paper/loop.py's member_key (names repeat across timeframes)
            last_close = last_close_by_member.get(f"{candidate.name}__{candidate.timeframe.value}")
            unrealized_pct = None
            if last_close is not None:
                unrealized_pct = (
                    broker.position.direction
                    * (last_close / broker.position.entry_price - 1)
                    * broker.position.position_fraction
                    * 100
                )
            position = {
                "direction": broker.position.direction,
                "entry_price": broker.position.entry_price,
                "entry_time": str(broker.position.entry_time),
                "stop_price": broker.position.stop_price,
                "unrealized_pct": unrealized_pct,
            }
        member_states.append(
            {
                "candidate_name": candidate.name,
                "timeframe": candidate.timeframe.value,
                "equity": broker.equity,
                "initial_equity": broker.initial_equity,
                "return_pct": (broker.equity / broker.initial_equity - 1) * 100 if broker.initial_equity else 0.0,
                "position": position,
                "trade_count": len(broker.trades),
            }
        )

    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "session_started_at": session_started_at,
        "total_equity": total_equity,
        "total_initial_equity": total_initial,
        "total_return_pct": (total_equity / total_initial - 1) * 100 if total_initial else 0.0,
        "equity_history": equity_history[-MAX_EQUITY_HISTORY:],
        "members": member_states,
        "recent_trades": recent_trades[-MAX_RECENT_TRADES:],
    }


def write_state(state: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(state, indent=2, default=str))
    os.replace(tmp_path, path)


def read_state(path: Path) -> dict:
    return json.loads(path.read_text())
