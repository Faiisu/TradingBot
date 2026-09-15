# 08: Performance Metric v2 + เกณฑ์เข้า Ensemble + ADR 0003

**What to build:** เปลี่ยน Performance Metric จาก "return % ÷ max DD % (DD มี floor 0.01%)" เป็น **Sharpe รายปีจาก return รายวันแบบ mark-to-market ที่ต้นทุน 2×**

เหตุผลที่ต้องเปลี่ยน:
- Metric เดิมให้รางวัลกับ candidate ที่ trade ถี่แต่ขนาดเล็ก จึงเอนไปทาง M5 อย่างเป็นระบบ
- Metric เดิมเทียบข้าม Timeframe อย่างยุติธรรมไม่ได้
- Metric เดิมใช้กับ Deflated Sharpe (ticket 12) ไม่ได้

กำหนด **เกณฑ์เข้า Ensemble** (ต้องผ่านทุกข้อ):
1. Sharpe (ต้นทุน 2×) > 0
2. จำนวน trade ≥ 200 และ ≥ 30 ต่อปี
3. Break-even cost ≥ 3 เท่าของต้นทุนปกติ

รายงานประกอบ: Calmar ที่ vol 10%/ปี, max DD, จำนวน trade, break-even cost และสัดส่วนปีที่กำไร

บันทึกเหตุผลเป็น ADR 0003 และอัปเดตรายการ Performance Metric กับ Ensemble ใน `CONTEXT.md`

**Blocked by:** 05 — Equity แบบ mark-to-market; 06 — ต้นทุน + stress + break-even

**Status:** ready-for-agent

- [ ] อันดับ candidate บนหน้า Backtest เรียงตาม Sharpe (MTM, ต้นทุน 2×)
- [ ] การคัดเลือก Ensemble และ Walk-Forward Validation ใช้ metric และเกณฑ์ใหม่ (เกณฑ์ผ่านของ Walk-Forward ยังเป็น > 0 จนกว่าจะถึง ticket 13)
- [ ] หน้า Backtest แสดงคอลัมน์รายงานประกอบครบทุกค่า
- [ ] ADR 0003 บันทึกทางเลือกที่พิจารณาและเหตุผล และ `CONTEXT.md` อัปเดตแล้ว
- [ ] The test suite stays green
