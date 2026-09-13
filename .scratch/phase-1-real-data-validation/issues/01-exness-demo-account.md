# 01: Set up Exness demo account & MT5 credentials

**What to build:** a working local MT5 connection — `.env` filled in with demo credentials, the "MetaTrader 5 EXNESS" terminal running and logged into the demo account, confirmed by a successful connection that passes the demo-account assertion in `mt5_client.py`.

**Blocked by:** None (can start immediately)

**Status:** ready-for-human — cannot be automated by an agent (requires the user to interact with Exness's signup flow directly)

- [ ] Exness demo account created
- [ ] `.env` filled in with `MT5_DEMO_LOGIN` / `MT5_DEMO_PASSWORD` / `MT5_DEMO_SERVER`
- [ ] `python scripts/fetch_history.py` connects successfully (no `Mt5ConnectionError` / `Mt5NotDemoAccountError`)
