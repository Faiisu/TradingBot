# 25: Grid พารามิเตอร์เล็กๆ ที่เลือกจาก plateau ภายใน Selection Window

**Type:** research

**What to build:** ตอนนี้ Rule Set ใช้พารามิเตอร์ default ชุดเดียว วิธีนี้ปลอดภัยเรื่อง overfitting แต่อาจทิ้ง edge ที่อยู่ใกล้ๆ ไป

ทดสอบ grid เล็กๆ (ไม่เกิน 3 ค่าต่อพารามิเตอร์) โดยมีกติกาดังนี้:
- เลือกค่าที่อยู่ **กลาง plateau** คือค่าที่เพื่อนบ้านใน grid ให้ผลใกล้กัน ไม่ใช่ค่าที่ดีที่สุดจุดเดียว
- การเลือกเกิดขึ้นภายใน Selection Window ของแต่ละขั้นของ Walk-Forward เท่านั้น
- ทุกจุดใน grid นับเป็น trial ใน research ledger ซึ่งจะทำให้ hurdle ของ DSR สูงขึ้นตามจริง

**เกณฑ์ falsify (เขียนก่อนรัน):** ไม่ใช้ grid ถ้าผล out-of-sample ของ Walk-Forward v2 ไม่ดีกว่าการใช้ default หลังหักผลของ trial ที่เพิ่มขึ้นแล้ว

**Blocked by:** 12 — Research ledger + DSR; 13 — Walk-Forward v2

**Status:** ready-for-agent

- [ ] สมมติฐานและเกณฑ์ falsify บันทึกไว้ก่อนรัน
- [ ] การเลือก plateau ใช้เฉพาะข้อมูลใน Selection Window (มี test)
- [ ] ทุกจุดใน grid ถูกบันทึกลง research ledger
- [ ] `## Answer` เทียบ plateau กับ default บน Walk-Forward v2 และคำตัดสินว่าจะใช้ grid หรือไม่
- [ ] The test suite stays green
