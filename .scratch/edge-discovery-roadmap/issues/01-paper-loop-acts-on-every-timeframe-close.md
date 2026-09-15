# 01: Paper loop ตัดสินใจตรงเวลาปิดแท่งของทุก Timeframe

**What to build:** สมาชิกทุกตัวของ Ensemble ใน Paper Trading ต้องตัดสินใจภายในไม่กี่วินาทีหลังแท่งของ Timeframe ตัวเองปิด ไม่ว่า loop จะเริ่มรันตอนไหน

ปัจจุบัน loop นับรอบของ Timeframe ที่เล็กที่สุด (M5) จากเวลาที่เริ่มรัน สมาชิก Timeframe ใหญ่จึงตัดสินใจช้าได้สูงสุด (ตัวคูณ − 1) × 5 นาที เช่น H1 ช้าได้ถึง 55 นาที แต่ยังบันทึกราคาเข้าเป็น close ของแท่งนั้น ซึ่ง ณ เวลาตัดสินใจเป็นราคาที่ไม่มีอยู่แล้ว

ตัวอย่างที่เจอจริงวันที่ 2026-09-15: แท่ง M15 ที่ปิด 16:45 ถูกประมวลผลตอน 16:50:05

**Blocked by:** None (can start immediately)

**Status:** done

- [x] สมาชิกทุก Timeframe (M5, M15, M30, H1) ประมวลผลแท่งที่เพิ่งปิดภายใน buffer หลังเวลาปิดแท่งของตัวเอง โดยอิงเวลานาฬิกา ไม่ใช่การนับรอบ ต้องมี test ที่จำลองเวลาเริ่มรันหลาย offset ภายในรอบของ M15/M30/H1
- [x] ทุกแท่งที่ประมวลผลบันทึก decision latency (วินาทีระหว่างเวลาปิดแท่งกับเวลาตัดสินใจ)
- [x] หน้า Paper Trading แสดง decision latency ล่าสุดที่แย่ที่สุดของสมาชิก
- [x] พฤติกรรมตอนตลาดปิด (ไม่มีแท่งใหม่) เหมือนเดิม คือไม่ replay แท่งเก่า
- [x] หลังแก้แล้วเริ่ม dry run ใหม่ และบันทึกไว้ใน `## Comments` ของ phase-1-real-data-validation ticket 05 ว่ารอบก่อนหน้ามี bug นี้
- [x] The test suite stays green

## Answer

Replaced the `tick % multiple` counter in `run_paper_trading_loop` (paper/loop.py) with two pure,
directly-testable functions: `nominal_bar_close(now, smallest)` rounds the current time down to the
smallest Timeframe's own wall-clock boundary, and `timeframe_closed_at(timeframe, nominal_close)`
checks whether that boundary is also one of a larger Timeframe's own boundaries. Neither depends on
when the loop started. The per-tick update logic was extracted into `run_tick(...)`, called each
wake-up with the current time, so it's testable without driving the real sleep loop.

Added `decision_latency_seconds(bar_time, decided_at)` (handles the timezone-naive `bar_time` MT5
returns) and a `decision_latency_by_member` dict threaded through `run_tick` → `build_state`. The
Paper Trading page shows it as a "Worst decision latency" stat tile.

Restarted the dry run at 2026-09-16 on the fixed loop; noted the prior bug in phase-1 ticket 05's
`## Comments` so its checklist isn't evaluated against the two earlier, buggy runs.

**Code review follow-up:** review flagged that pure wall-clock gating, on its own, would silently skip
a larger Timeframe's boundary forever if one iteration ran longer than a smallest-Timeframe interval
(slow MT5 call, laptop sleep) — unlike the old counter, which stayed misaligned but never skipped.
Added `missed_nominal_closes(previous, current, smallest, max_catch_up=12)`: backfills every boundary
between the last processed one and the current one (capped, so a multi-hour suspend doesn't replay
hours of stale ticks), and `run_paper_trading_loop` now calls `run_tick` once per boundary in that
list. `run_tick` takes `now` and `nominal_close` as separate parameters so a caught-up (late) tick
still gates on the boundary it belongs to while decision_latency_seconds reflects how late it actually
ran — a slow-processing incident is visible on the dashboard instead of hidden.

Review also flagged three findings entirely outside this diff (in pre-existing, already-modified-but-
uncommitted `simulated_broker.py`, `engine.py`, and `dashboard/server.py` from earlier ticket-06 work):
an exit-reason mislabeling bug (trailing-stop ratchet seeded from the entry bar's own high/low instead
of entry_price, occasionally mislabeling an ordinary stop-loss as "trailing_stop"), a CSRF/host-binding
weakness on the dashboard's process-control endpoints, and a performance regression from de-vectorizing
the stop-scan. Left untouched — not part of this ticket's scope — and flagged to the user for separate
tickets. Review also confirmed the duplicated exit logic between engine.py and simulated_broker.py that
ticket 02 already exists to fix.

Full test suite: 243 passed.
