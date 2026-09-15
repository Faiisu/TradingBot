# 30: รัน demo execution อย่างน้อย 3 เดือน + ตรวจเกณฑ์พร้อม live

**What to build:** รันการส่งออเดอร์จริงบน demo ต่อเนื่องอย่างน้อย 3 เดือน และมีอย่างน้อย 100 trade จากนั้นตรวจเกณฑ์ความพร้อมเข้า Live Trading ที่กำหนดไว้ล่วงหน้า dashboard ต้องแสดงสถานะผ่าน/ไม่ผ่านของทุกข้อ

1. Walk-Forward v2: DSR ≥ 0.95 และ Sharpe out-of-sample (ต้นทุน 2×) ≥ 0.7
2. ไม่มี regime ใดที่ drawdown out-of-sample เกิน 1.5 เท่าของ DD budget
3. ต้นทุน execution จริงไม่เกินต้นทุนที่ model ไว้ในแบบ stressed
4. ผลของ demo อยู่ในช่วง percentile ที่ 5–95 ของช่วงผลที่คาดหวัง
5. ทดสอบ kill switch และ reconcile กับ position จริงแล้ว

การรัน 3 เดือนและการยอมรับผลเป็นหน้าที่ของผู้ใช้ ส่วนการแสดงเกณฑ์บน dashboard ทำโดย agent ได้

**Blocked by:** 18 — Vol target และ DD budget; 28 — ส่งออเดอร์จริงบน demo; 29 — ช่วงผลที่คาดหวัง + กฎหยุด

**Status:** ready-for-human

- [ ] Dashboard แสดงสถานะผ่าน/ไม่ผ่านของเกณฑ์ 1–5
- [ ] Demo execution รันครบอย่างน้อย 3 เดือนและอย่างน้อย 100 trade
- [ ] ผู้ใช้บันทึกผลการตรวจเกณฑ์และการตัดสินใจไว้ใน `## Comments`
