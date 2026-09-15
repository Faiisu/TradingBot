# 18: Vol target และ DD budget ระดับ portfolio

**What to build:** ควบคุมความเสี่ยงของทั้ง Ensemble ด้วยกติกาที่กำหนดไว้ล่วงหน้า:

- **Vol target:** 10% ต่อปีสำหรับทั้ง portfolio
- **DD budget:** 15% ถ้า drawdown ของ portfolio เกิน budget ให้ลดขนาดลงครึ่งหนึ่งจนกว่า equity จะฟื้นกลับตามเกณฑ์ที่กำหนด

กติกานี้ใช้เหมือนกันใน Backtest ของ Ensemble, Walk-Forward Validation และ Paper Trading

**Blocked by:** 16 — Net position; 17 — Ensemble แบบ cluster

**Status:** ready-for-agent

- [ ] กราฟ equity บนหน้า Backtest ทำเครื่องหมายช่วงที่ลดขนาด
- [ ] ผล out-of-sample ของ Walk-Forward รายงานทั้งแบบมีและไม่มี DD budget
- [ ] หน้า Paper Trading แสดงตัวคูณขนาดปัจจุบัน และบอกว่ากำลังอยู่ในช่วงลดขนาดหรือไม่
- [ ] เกณฑ์ลดขนาดและเกณฑ์กลับมาขนาดเต็มมี test
- [ ] The test suite stays green
