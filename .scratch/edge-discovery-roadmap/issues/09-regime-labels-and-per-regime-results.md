# 09: ป้าย regime (ใช้ข้อมูลอดีตเท่านั้น) + ผลแยกตาม regime

**What to build:** ติดป้าย regime ให้ทุกแท่ง ได้แก่ trend-up, trend-down, range และ high-vol โดยคำนวณจากข้อมูลที่เกิดขึ้นแล้วเท่านั้น

ตัวชี้วัดที่ใช้ได้ เช่น efficiency ratio, ความชันของเส้นแนวโน้มระดับรายวัน และ percentile ของ volatility เกณฑ์ที่เลือกต้องบันทึกไว้ใน ticket และใช้ค่าเดียวกันตลอด

หน้า Backtest แสดงผลของแต่ละ candidate แยกตาม regime เพื่อตอบคำถามว่า "ถ้า regime เปลี่ยน จะเสียเท่าไร"

**Blocked by:** 03 — ประวัติ Exness 9 ปี; 05 — Equity แบบ mark-to-market

**Status:** ready-for-agent

- [ ] ป้าย regime ของแต่ละแท่งไม่ใช้ข้อมูลอนาคต (test: เปลี่ยนข้อมูลหลังแท่ง t แล้วป้ายที่ t ต้องไม่เปลี่ยน)
- [ ] รายงานการกระจายของ regime ช่วง 2017–2026 แสดงให้เห็นว่ามีครบทุก regime และอยู่ช่วงไหนบ้าง
- [ ] หน้า Backtest มีตาราง candidate × regime แสดง Sharpe, return, max DD และจำนวน trade
- [ ] เกณฑ์ของ labeler บันทึกไว้ใน `## Answer` ของ ticket นี้
- [ ] The test suite stays green
