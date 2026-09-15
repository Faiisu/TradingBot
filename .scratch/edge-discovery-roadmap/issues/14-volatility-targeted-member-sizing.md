# 14: Sizing แบบ volatility target ระดับสมาชิก

**What to build:** ทำให้ candidate ถูกเปรียบเทียบที่ความเสี่ยงเท่ากัน

ตอนนี้ cap ของ position (0.2 เท่าของทุน) ถูกใช้แทบทุก trade ทำให้ risk ต่อ trade ที่ตั้งไว้ 1% ไม่มีผล ความเสี่ยงจริงต่อ trade อยู่ที่แค่ ~0.01–0.06% และแต่ละ candidate ก็เสี่ยงไม่เท่ากัน

แนวทางใหม่:
- **ระดับ trade:** ขนาด position มาจาก risk budget ต่อ trade จริงๆ cap มีไว้กันกรณีผิดปกติเท่านั้น และใช้ leverage/margin จริงของบัญชีเป็นขอบบน
- **ระดับสมาชิก:** scale ให้ volatility ที่เกิดขึ้นจริงเข้าใกล้เป้า (เช่น 10%/ปี) โดยใช้ข้อมูลอดีตเท่านั้น และจำกัดตัวคูณไว้ที่ 0.25×–2×

**Blocked by:** 05 — Equity แบบ mark-to-market; 08 — Performance Metric v2

**Status:** ready-for-agent

- [ ] รายงานสัดส่วน trade ที่ cap ถูกใช้ ซึ่งควรเกิดน้อยมาก
- [ ] Volatility ที่เกิดขึ้นจริงของสมาชิกบนข้อมูล 9 ปีอยู่ในช่วงที่กำหนดรอบเป้า
- [ ] ตัวคูณ volatility ใช้ข้อมูลอดีตเท่านั้น (มี test)
- [ ] หน้า Backtest เปรียบเทียบ candidate ข้าม Timeframe ที่ความเสี่ยงเท่ากัน
- [ ] Paper Trading ใช้ sizing เดียวกัน
- [ ] The test suite stays green
