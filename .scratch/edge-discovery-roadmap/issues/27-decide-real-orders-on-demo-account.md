# 27: ตัดสินใจ — อนุญาตให้ส่งออเดอร์จริงบนบัญชี demo ไหม (ADR แก้นิยาม Phase 1)

**Type:** grilling

**What to build:** ตัดสินใจว่าจะขยายขอบเขต Phase 1 ให้ **ส่งออเดอร์จริงไปที่บัญชี demo ของ Exness** ที่แยกไว้หรือไม่ ซึ่งยังไม่มีเงินจริงเกี่ยวข้อง

เหตุผลที่ต้องตัดสินใจ:
- Fill แบบจำลองเปิดเผย execution gap ไม่ได้ เช่น requote, การ fill ของ SL ฝั่ง server, spread ช่วงข่าว และ latency
- แม้ ticket 19 จะบันทึก bid/ask จริงได้ ก็ยังไม่ได้ fill จริง
- นิยามปัจจุบันใน `CONTEXT.md` (Paper Trading = simulated execution) และ ADR 0001 ไม่ได้ครอบคลุมการส่งออเดอร์บน demo

ถ้าอนุญาต ต้องกำหนดมาตรการป้องกัน:
- การตรวจว่าเป็นบัญชี demo ต้องยังอยู่
- เส้นทางส่งออเดอร์ต้องปฏิเสธบัญชีที่ไม่ใช่ demo
- ต้องแยกคำศัพท์ใหม่ (เช่น Demo Execution) ออกจาก Paper Trading

**Blocked by:** None (can start immediately)

**Status:** ready-for-human

- [ ] ผู้ใช้ตัดสินใจและบันทึกเหตุผลไว้
- [ ] ถ้าอนุญาต: เขียน ADR ใหม่ที่อ้างถึง ADR 0001 และเพิ่ม/แก้คำศัพท์ใน `CONTEXT.md`
- [ ] ถ้าไม่อนุญาต: ปรับขอบเขตของ ticket 28–30 และบันทึกไว้ใน `## Comments`
