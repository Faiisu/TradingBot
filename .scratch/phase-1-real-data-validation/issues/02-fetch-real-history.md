# 02: Fetch & validate real XAUUSD history coverage

**What to build:** real H1/M30/M15 XAUUSD bars cached to `data/cache/*.parquet` via `scripts/fetch_history.py`, with actual date coverage confirmed against the 2-year target (Exness's M15/M30 retention may fall short — that's expected and just needs documenting, not fixing).

**Blocked by:** 01 (needs a working MT5 demo connection)

**Status:** done

- [x] All three timeframes cached (four since M5 was added: H1, M30, M15, M5)
- [x] Coverage report reviewed (bars returned, actual date range vs. requested)
- [x] Any shortfall vs. 2 years noted, not silently worked around

## Answer

- **Coverage:** every timeframe covers the full 2-year target: 728 days of `XAUUSDm`, 2024-09-15 → 2026-09-14 (H1 11,781 bars, M30 23,547, M15 47,080, M5 141,145).
- **Shortfall, noted and fixed:**
  - The shortfall this ticket expected for M15/M30 never happened.
  - One did appear on M5: 514 days, which looked like broker retention.
  - The real cause was the MT5 terminal's "Max bars in chart" limit of 100,000 bars.
  - Raising that limit and re-fetching restored the full history (rule-set-expansion ticket 01, commit `adfdd5a`).
  - Fetching now refuses to run if that limit would cut history short.
