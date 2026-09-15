# 21: Research — Rule Set ที่สลับตาม regime

**Type:** research

**What to build:** ทดสอบว่า mean-reversion ขาดทุนเพราะไอเดียผิด หรือเพราะถูกใช้ผิด regime

หลักฐานเดิม: บนข้อมูล 2 ปี RSI และ Stochastic Reversion ขาดทุนทุก Timeframe ในขนาดใกล้เคียงกับที่ trend family กำไร

ทดสอบ Rule Set ที่ใช้ mean-reversion เฉพาะช่วง range และใช้ trend เฉพาะช่วง trend ตามป้าย regime ที่ใช้ข้อมูลอดีตเท่านั้น (ticket 09)

**เกณฑ์ falsify (เขียนก่อนรัน):** ผล out-of-sample ต้องชนะทั้ง "mean-reversion ตลอดเวลา" และ "trend ตลอดเวลา" ไม่เช่นนั้นให้ทิ้ง

**Blocked by:** 09 — ป้าย regime; 10 — Baseline 9 ปี + go/no-go; 13 — Walk-Forward v2

**Status:** ready-for-agent

- [ ] สมมติฐานและเกณฑ์ falsify บันทึกไว้ก่อนรัน
- [ ] Rule Set ใหม่ใช้ป้าย regime ที่ไม่มองอนาคต (มี test)
- [ ] ผ่าน Backtest, Walk-Forward v2 และบันทึกลง research ledger
- [ ] `## Answer` เทียบกับ baseline ทั้งสองแบบ รายงาน correlation กับสมาชิกเดิม และคำตัดสินว่าจะเก็บหรือทิ้ง
- [ ] The test suite stays green
