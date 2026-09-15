# 20: Research — Time-series momentum บน H4/D1

**Type:** research

**What to build:** เพิ่ม Timeframe H4 และ D1 และเพิ่ม Rule Set แบบ time-series momentum รอบยาว คือถือตามทิศของ return ย้อนหลัง 1–12 เดือน โดยปรับขนาดตาม volatility

- **ทำไมอยู่ลำดับแรกของการค้นหา:** มีงานวิจัยรองรับข้ามหลายสินทรัพย์รวมทั้งทองคำ (Moskowitz, Ooi & Pedersen, 2012) และต้นทุนต่อ trade เล็กมากเมื่อเทียบกับ edge
- **ข้อมูล:** H4 สร้างจาก H1 ของ Exness (มีจริงตั้งแต่ 2017-05) ส่วน D1 มีบน MT5

**ต้องเขียนสมมติฐานและเกณฑ์ falsify ไว้ใน ticket ก่อนรัน:**
- ทิ้งไอเดีย ถ้า DSR ของ Walk-Forward v2 ต่ำกว่า 0.95
- ทิ้งไอเดีย ถ้าขาดทุนในช่วง regime ขาลงหรือ range จน DD เกิน budget

**Blocked by:** 10 — Baseline 9 ปี + go/no-go; 13 — Walk-Forward v2

**Status:** ready-for-agent

- [ ] สมมติฐานและเกณฑ์ falsify บันทึกไว้ก่อนรัน
- [ ] H4 และ D1 ใช้งานได้ครบทั้ง Backtest, Walk-Forward Validation และ Paper Trading
- [ ] ทุก trial ถูกบันทึกลง research ledger
- [ ] `## Answer` สรุปผล, ผลแยกตาม regime, correlation กับสมาชิกเดิม และคำตัดสินว่าจะเก็บหรือทิ้ง
- [ ] The test suite stays green
