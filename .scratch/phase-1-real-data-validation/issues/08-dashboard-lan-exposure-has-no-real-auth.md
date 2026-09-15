# 08: Dashboard's LAN exposure has no real authentication

**What to build:** The dashboard (uncommitted work binding it to `0.0.0.0` so it's reachable from other devices on the local network) must not let an arbitrary device on that network read live trading state or control Paper Trading. Today it does both.

Found during code review of ticket 01. Two separate gaps in `dashboard/server.py`:

1. **`require_dashboard_request` is spoofable by anything that isn't a browser.** It checks `request.headers.get("host")` against `ALLOWED_HOSTS` and, if present, `Origin` against `ALLOWED_ORIGINS` — but explicitly allows requests with no `Origin` at all ("curl, scripts"). `Host` and `Origin` are both attacker-controlled on a raw HTTP request; a same-origin check only does anything against a *browser*, which enforces `Origin` itself. Any device on the LAN can send `curl -X POST http://<this machine's LAN IP>:8765/api/paper/start -H "Host: <that same IP>:8765" -H "Content-Type: application/json"` and pass this check — the IP is trivially discoverable since `scripts/run_dashboard.py` prints it at startup and port 8765 is one port-scan away.
2. **The GET endpoints have no check at all.** `/`, `/api/state`, `/api/backtest`, and `/api/paper/status` never call `require_dashboard_request` (it's only wired into the POST start/stop handlers), so any LAN device can read the account's live equity, open positions, trade history, and full backtest results with zero restriction — a real change from the previous loopback-only binding, where the OS-level network boundary itself was the access control.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] A request whose `Host`/`Origin` headers merely *match* the allowlist, but that carries no real proof of same-origin browser context (no session/token), cannot start or stop Paper Trading — pick one real control: a per-session token issued by the dashboard page and required on every state-changing request, or reverting control endpoints to loopback-only regardless of `HOST`
- [ ] Reading live trading state, trade history, and backtest results requires the same real control as the control endpoints — not left open by omission
- [ ] A test proves a request with a forged but allowlist-matching `Host` header, and no other credential, is rejected by every endpoint that exposes trading state or control
- [ ] `scripts/run_dashboard.py`'s startup output and any related comments are updated to describe the actual protection in place, not the disproven Host/Origin-only model
- [ ] The test suite stays green
