# 17: Ensemble แบบ cluster ตาม correlation ของ PnL, แบ่งความเสี่ยงเท่ากันต่อ cluster

**What to build:** เปลี่ยนการคัดเลือก Ensemble จาก "นับจำนวนสมาชิก" เป็น "นับจำนวน bet ที่เป็นอิสระต่อกัน" ตอนนี้ correlation เฉลี่ยของ PnL รายวันระหว่างสมาชิกคือ 0.47 สมาชิก 36 ตัวจึงเป็นแค่ไม่กี่ bet ที่ถูกนับซ้ำ

ในแต่ละ Selection Window:
1. จัด cluster ของ candidate ที่ผ่านเกณฑ์ ด้วย hierarchical clustering บน correlation ของ PnL รายวันแบบ mark-to-market
2. เลือกตัวแทนไม่เกิน 1–2 ตัวต่อ cluster (ตัวที่มี DSR สูงสุด)
3. แบ่งความเสี่ยงเท่ากันต่อ cluster

กติกานี้มาแทนกฎ one-per-(Rule Set, Entry Timeframe) เดิม และต้องผ่านการตรวจด้วย Walk-Forward Validation ตามหลักการของ ADR 0002

Ensemble สำหรับ Paper Trading ใช้กติกาเดียวกันกับข้อมูลทั้งหมด

บันทึกเป็น ADR 0005 และอัปเดตรายการ Ensemble ใน `CONTEXT.md`

**Blocked by:** 13 — Walk-Forward v2; 14 — Sizing แบบ volatility target

**Status:** ready-for-agent

- [ ] หน้า Backtest แสดง cluster, ตัวแทนที่ถูกเลือก และจำนวน effective bets
- [ ] Clustering ใช้เฉพาะข้อมูลใน Selection Window (มี test)
- [ ] Test: candidate ที่ซ้ำกันเกือบทุกประการต้องอยู่ใน cluster เดียวกัน และได้ตัวแทนแค่ตัวเดียว
- [ ] Walk-Forward v2 รันด้วยกติกาใหม่ และบันทึกผลเทียบกับกติกาเดิมไว้ใน `## Answer`
- [ ] ADR 0005 และ `CONTEXT.md` อัปเดตแล้ว
- [ ] The test suite stays green
