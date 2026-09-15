# 04: Fill สมจริง: เข้าที่ open แท่งถัดไป, trailing เริ่มจากราคาเข้า, fill ที่ open เมื่อโดน gap

**What to build:** ทำให้ทั้ง Backtest และ Paper Trading (ผ่านการตัดสินใจชุดเดียวจาก ticket 02) fill ด้วยราคาที่ได้จริง:

- **สัญญาณรู้ได้หลังแท่งปิดเท่านั้น:** Backtest เข้าที่ open ของแท่งถัดไป ส่วน Paper Trading เข้าที่ราคาแรกที่ได้หลังแท่งปิด ไม่ใช่ close ของแท่งที่ปิดไปแล้ว
- **Trailing stop เริ่มจากราคาเข้า:** ไม่ใช้ high/low ของแท่งสัญญาณ ซึ่งเกิดก่อนเข้าออเดอร์
- **Gap:** ถ้าแท่งเปิดเลยระดับ stop หรือ target ไปแล้ว ให้ fill ที่ราคาเปิดของแท่งนั้น

หลักฐานจาก audit วันที่ 2026-09-15: ผลรวมต่อ return ไม่มาก แต่ max DD ของ Donchian H1 เพิ่มจาก 1.15% เป็น 1.78% และลำดับของ H1 breakout เปลี่ยน

**Blocked by:** 01 — Paper loop ตัดสินใจตรงเวลาปิดแท่ง; 02 — Prefactor: การตัดสินใจรายแท่งชุดเดียว

**Status:** ready-for-agent

- [ ] Backtest เข้าที่ open ของแท่งถัดจากแท่งสัญญาณ รวมถึงการ re-entry หลังโดน stop หรือ target (มี test)
- [ ] Trailing stop ไม่เคยใช้ extreme ของแท่งก่อนเข้าออเดอร์ (มี test ที่แท่งสัญญาณมี high สูงผิดปกติ)
- [ ] Stop และ target ที่แท่งเปิดเลยระดับไปแล้วถูก fill ที่ราคาเปิด (มี test ทั้งฝั่ง long และ short)
- [ ] Paper Trading ใช้ราคาแรกหลังแท่งปิดเป็นราคาเข้า และ Backtest กับ Paper ยังให้ trade ตรงกันเมื่อป้อนแท่งชุดเดียวกัน
- [ ] รัน Backtest ใหม่ และบันทึกใน `## Answer` ว่าผลของ candidate อันดับต้นเปลี่ยนไปเท่าไร
- [ ] The test suite stays green
