# 01: Set up Exness demo account & MT5 credentials

**What to build:** a working local MT5 connection — `.env` filled in with demo credentials, the "MetaTrader 5 EXNESS" terminal running and logged into the demo account, confirmed by a successful connection that passes the demo-account assertion in `mt5_client.py`.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Exness demo account created
- [x] `.env` filled in with `MT5_DEMO_LOGIN` / `MT5_DEMO_PASSWORD` / `MT5_DEMO_SERVER`
- [x] `python scripts/fetch_history.py` connects successfully (no `Mt5ConnectionError` / `Mt5NotDemoAccountError`)

## Answer

Verified 2026-09-14:
- The connected account reports `trade_mode=0` (demo) with a balance of 5,000 USD. Its only deal is the opening balance deposit (2026-09-13, comment `D-trial-USD…`), and it has placed no orders.
- `scripts/fetch_history.py --force` connected and passed the demo-account check in `mt5_session`, then fetched all timeframes.
