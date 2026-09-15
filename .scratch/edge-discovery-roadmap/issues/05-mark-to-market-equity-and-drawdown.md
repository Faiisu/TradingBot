# 05: Equity และ drawdown แบบ mark-to-market รายแท่ง

**What to build:** ตอนนี้ equity ของ Backtest เปลี่ยนเฉพาะตอนปิด trade ทำให้ drawdown ระหว่างถือ position หายไป และ Performance Metric ดูดีเกินจริง ให้คิด equity ทุกแท่งโดยรวมกำไร/ขาดทุนที่ยังไม่ปิด แล้วใช้ค่านี้กับ max drawdown, กราฟ equity, out-of-sample record ของ Walk-Forward Validation และ Paper Trading

**Blocked by:** 02 — Prefactor: การตัดสินใจรายแท่งชุดเดียว

**Status:** ready-for-agent

- [ ] Equity ถูกคิดทุกแท่ง รวม unrealized PnL ของ position ที่เปิดอยู่ (หักต้นทุนตั้งแต่ตอนเข้า)
- [ ] Max drawdown และ Performance Metric คำนวณจาก equity แบบ mark-to-market
- [ ] Equity สุดท้ายเท่ากับแบบเดิม (เปลี่ยนแค่เส้นทางระหว่างทาง) มี test ยืนยัน
- [ ] Out-of-sample equity ที่ต่อกันจากหลาย Test Window ใช้ equity แบบ mark-to-market
- [ ] กราฟ equity บนหน้า Backtest และหน้า Paper Trading แสดงค่า mark-to-market
- [ ] The test suite stays green
