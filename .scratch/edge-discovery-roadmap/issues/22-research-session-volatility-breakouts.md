# 22: Research — Breakout ตามช่วง session/volatility

**Type:** research

**What to build:** ทดสอบ breakout ที่ผูกกับช่วงเวลาที่ liquidity และข้อมูลใหม่เข้าตลาด เช่น การเปิดตลาด London และ New York

- **สมมติฐาน:** ช่วงเวลาเหล่านี้สร้าง momentum ระยะสั้นที่เกิดซ้ำได้
- **เวลา:** ใช้ broker server time (UTC ตาม `CONTEXT.md`)
- **Baseline:** Asian Range Breakout ที่มีอยู่แล้ว
- **ข้อควรระวัง:** ช่วงนี้ spread มักกว้างขึ้น จึงต้องผ่านการทดสอบที่ต้นทุน 2× และ 3×

**เกณฑ์ falsify (เขียนก่อนรัน):** ทิ้ง ถ้า break-even cost ต่ำกว่า 3 เท่าของต้นทุนปกติ หรือ DSR ของ Walk-Forward v2 ต่ำกว่า 0.95

**Blocked by:** 10 — Baseline 9 ปี + go/no-go; 13 — Walk-Forward v2

**Status:** ready-for-agent

- [ ] สมมติฐานและเกณฑ์ falsify บันทึกไว้ก่อนรัน
- [ ] Rule Set ใหม่มี test ที่ขอบเวลาของ session
- [ ] ผ่าน Backtest ที่ต้นทุน 1×/2×/3× และ Walk-Forward v2 และบันทึกลง research ledger
- [ ] `## Answer` สรุปผลเทียบกับ Asian Range Breakout และคำตัดสินว่าจะเก็บหรือทิ้ง
- [ ] The test suite stays green
