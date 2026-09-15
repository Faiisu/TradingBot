# 13: Walk-Forward v2 (Selection 3 ปี / Test 3 เดือน / embargo, ผ่านเมื่อ DSR ≥ 0.95) + ADR 0004

**What to build:** ปรับ Walk-Forward Validation ให้ใช้กับข้อมูล 9 ปีและมีอำนาจแยกแยะจริง แทนการ "ผ่านง่าย" แบบเดิม ที่ผ่าน 9/9 window เพราะทั้งช่วงเป็น regime เดียว

- **หน้าต่าง:** ยังเป็นแบบ anchored ตาม ADR 0002 แต่ Selection Window แรกยาว **3 ปี**, Test Window ยาว **3 เดือน** และมี **embargo 1 วัน** คั่นระหว่างสองหน้าต่าง
- **เกณฑ์เข้า Ensemble ในแต่ละขั้น:** metric, จำนวน trade, break-even, null p-value และ DSR ต้องคำนวณจาก Selection Window เท่านั้น
- **เกณฑ์ผ่าน:** DSR ของ out-of-sample record ที่ต้นทุน 2× ต้อง ≥ 0.95 (แทนเกณฑ์ > 0)
- **รายงานผล:** แยกผล out-of-sample ตาม regime

บันทึกเป็น ADR 0004 ที่อ้างถึง ADR 0002 (หลักการเดิมคงไว้ เปลี่ยนแค่พารามิเตอร์และเกณฑ์ผ่าน) และอัปเดตรายการ Walk-Forward Validation, Selection Window และ Test Window ใน `CONTEXT.md`

PBO/CSCV ยังไม่อยู่ในขอบเขตของ ticket นี้

**Blocked by:** 03 — ประวัติ 9 ปี; 08 — Performance Metric v2; 11 — Null model; 12 — Ledger + DSR

**Status:** ready-for-agent

- [ ] ได้ Test Window ประมาณ 25 ช่วงบนข้อมูล 9 ปี และมี embargo คั่นทุกขั้น (มี test)
- [ ] Test เดิมที่พิสูจน์ว่าการเลือกในแต่ละขั้นมองไม่เห็นข้อมูลของ Test Window ของตัวเอง ยังผ่าน และครอบคลุม null p-value กับ DSR ด้วย
- [ ] Verdict ใหม่ (DSR, ผ่าน/ไม่ผ่าน, ผลแยกตาม regime) ถูกบันทึก และปุ่ม Start ของ Paper Trading ใช้ verdict นี้
- [ ] หน้า Backtest แสดงตาราง Test Window และผลแยกตาม regime
- [ ] รายงานเวลาที่ใช้รันทั้งหมด ถ้าเกิน ~30 นาทีให้รันขนาน
- [ ] ADR 0004 และ `CONTEXT.md` อัปเดตแล้ว
- [ ] The test suite stays green
