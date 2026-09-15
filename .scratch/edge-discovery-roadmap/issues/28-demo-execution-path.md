# 28: ส่งออเดอร์จริงบน demo — ออเดอร์แบบ net, SL ฝั่ง server, แก้ trailing, reconcile

**What to build:** ส่ง net position จาก ticket 16 เป็นออเดอร์จริงบนบัญชี demo:

- **Stop และ target:** วางเป็น SL/TP ฝั่ง server (บัญชีนี้มี stops level = 0) และแก้ SL ทุกแท่งตาม trailing stop
- **Reconcile:** ทุกแท่งเทียบ position จริงของ broker กับ position ที่ระบบตั้งใจถือ ถ้าไม่ตรงให้แจ้งเตือนบน dashboard
- **เทียบผล:** รันคู่ขนานกับการบันทึกแบบจำลองของ Paper Trading เพื่อเทียบ fill จริงกับ fill จำลอง
- **Stop:** ปุ่ม Stop ต้องให้เลือกชัดเจนว่าจะปิด position ทั้งหมดหรือถือไว้

ใน backtest และ paper ปัจจุบัน stop ถูกตรวจหลังแท่งปิดแล้ว fill ที่ราคา stop ย้อนหลัง แต่ในการส่งออเดอร์จริง stop ต้องเป็นออเดอร์ที่วางอยู่บน server ตลอดเวลา

**Blocked by:** 04 — Fill สมจริง; 16 — Net position; 27 — ตัดสินใจเรื่องออเดอร์บน demo

**Status:** ready-for-agent

- [ ] เส้นทางส่งออเดอร์ทำงานเฉพาะบัญชี demo และปฏิเสธบัญชีอื่น (test ด้วย MT5 API ปลอม)
- [ ] ทุก position มี SL ฝั่ง server และ TP เมื่อเปิดใช้ target และ SL ถูกแก้ตาม trailing ทุกแท่ง
- [ ] Reconcile ทุกแท่ง และแจ้งเตือนบน dashboard เมื่อ position ไม่ตรง
- [ ] Fill จริง (ราคา, เวลา, slippage) ถูกบันทึกเทียบกับ fill จำลอง
- [ ] ปุ่ม Stop ให้เลือกระหว่างปิด position หรือถือไว้ และทั้งสองทางมี test
- [ ] The test suite stays green
