"""Start paper trading for the Ensemble saved by scripts/run_backtest.py (data/ensemble.json).

Requires a running "MetaTrader 5 EXNESS" terminal logged into the demo account in .env. Never places
a real order: every Ensemble member trades through a SimulatedBroker that only logs simulated fills.
Runs until interrupted (Ctrl+C).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tradebot.ensemble.selection import load_ensemble
from tradebot.mt5_client import mt5_session
from tradebot.paper.loop import run_paper_trading_loop
from tradebot.paper.simulated_broker import SimulatedBroker
from tradebot.risk.risk_controls import RiskControls
from tradebot.strategies.registry import build_candidates

SYMBOL = "XAUUSDm"  # this Exness demo server suffixes gold with "m"; confirmed via symbols_get()
ENSEMBLE_PATH = Path(__file__).resolve().parent.parent / "data" / "ensemble.json"


def run() -> None:
    if not ENSEMBLE_PATH.exists():
        raise SystemExit(f"No Ensemble found at {ENSEMBLE_PATH}. Run scripts/run_backtest.py against real cached data first.")

    ensemble = load_ensemble(ENSEMBLE_PATH)
    if not ensemble.members:
        raise SystemExit("Ensemble is empty (no candidate cleared the profitability threshold) — nothing to paper trade.")

    candidates_by_key = {(c.name, c.timeframe.value): c for c in build_candidates()}
    risk_controls = RiskControls()

    with mt5_session() as mt5:
        account = mt5.account_info()
        print(f"Connected to demo account, balance={account.balance:.2f}")

        members = []
        for ensemble_member in ensemble.members:
            key = (ensemble_member.candidate_name, ensemble_member.timeframe)
            candidate = candidates_by_key.get(key)
            if candidate is None:
                print(f"WARNING: could not find candidate for {key}, skipping")
                continue
            initial_equity = account.balance * ensemble_member.capital_fraction
            broker = SimulatedBroker(risk_controls=risk_controls, initial_equity=initial_equity)
            members.append((candidate, broker))

        run_paper_trading_loop(mt5, SYMBOL, members)


if __name__ == "__main__":
    run()
