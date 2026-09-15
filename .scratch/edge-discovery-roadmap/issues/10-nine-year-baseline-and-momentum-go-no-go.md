# 10: รัน baseline 9 ปี แล้วตัดสินใจ go/no-go ว่า momentum edge รอดข้าม regime ไหม

**Type:** research

**What to build:** รัน Strategy Candidate เดิมทั้งหมดบนข้อมูล 9 ปี โดยใช้เครื่องมือวัดใหม่จาก ticket 03–09 ครบแล้ว เพื่อตอบคำถามที่สำคัญที่สุดของ roadmap: **กำไรที่เห็นบนข้อมูล 2 ปีเป็น edge จริง หรือเป็นแค่ regime ขาขึ้นแรงของทองปี 2024–26?**

หลักฐานก่อนหน้า (2026-09-15): trend family กำไรทุก Timeframe ส่วน mean-reversion ขาดทุนทุก Timeframe ในขนาดใกล้เคียงกันแบบกลับด้าน, Ensemble มี Sharpe ประมาณ 7 และ correlation เฉลี่ยของ PnL รายวันระหว่างสมาชิกเท่ากับ 0.47

ผลของ ticket นี้กำหนดทิศทางของ ticket 17–26

**Blocked by:** 03 — ประวัติ 9 ปี; 04 — Fill สมจริง; 07 — Swap ย้อนหลัง; 08 — Performance Metric v2; 09 — ป้าย regime

**Status:** ready-for-agent

- [ ] รันครบทุก candidate และบันทึกผลแล้ว
- [ ] `## Answer` มีข้อมูลต่อไปนี้:
  - รายชื่อ candidate ที่ผ่านเกณฑ์เข้า Ensemble
  - ตาราง trend family vs mean-reversion family แยกตาม regime
  - Break-even cost ของ M5 เทียบกับ H1
  - การเปรียบเทียบกับตัวเลขจากข้อมูล 2 ปีเดิม
- [ ] มีคำแนะนำชัดเจนตามจุดตัดสินใจใน spec:
  - ถ้า **รอด** → ใช้เป็นแกนของ portfolio แล้วหา bet ที่ correlate ต่ำมาเสริม
  - ถ้า **ไม่รอด** → ไม่ใช้ Ensemble ชุดเดิมเป็นฐานของเงินจริง และให้ ticket 20–21 มาก่อน
- [ ] ผู้ใช้บันทึกการตัดสินใจ go/no-go ไว้ใน `## Comments`
