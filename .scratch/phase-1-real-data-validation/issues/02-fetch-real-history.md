# 02: Fetch & validate real XAUUSD history coverage

**What to build:** real H1/M30/M15 XAUUSD bars cached to `data/cache/*.parquet` via `scripts/fetch_history.py`, with actual date coverage confirmed against the 2-year target (Exness's M15/M30 retention may fall short — that's expected and just needs documenting, not fixing).

**Blocked by:** 01 (needs a working MT5 demo connection)

**Status:** ready-for-agent (once 01 is done)

- [ ] All three timeframes cached
- [ ] Coverage report reviewed (bars returned, actual date range vs. requested)
- [ ] Any shortfall vs. 2 years noted, not silently worked around
