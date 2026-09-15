# 23: Research — สัญญาณ macro รายวัน

**Type:** research

**What to build:** ทดสอบ real yield และ DXY เป็น **สัญญาณหลักบน D1** แทนการใช้เป็น Market Filter ของ M5/M15

ความสัมพันธ์ระหว่างทองกับ real yield และดอลลาร์เป็นปัจจัยพื้นฐานที่ทำงานบน horizon ยาว การใช้เป็น filter ของ Timeframe เล็กจึงไม่สอดคล้องกับ horizon นี้

**ข้อจำกัดด้านข้อมูล:** DXY และ XAGUSD บน MT5 มีแค่ตั้งแต่ 2022-08 ticket นี้ต้องหาแหล่งข้อมูลรายวันที่ยาวกว่าและดาวน์โหลดได้โดยไม่ต้องใช้ API key ถ้าหาไม่ได้ ให้ทดสอบเฉพาะ real yield

กฎ publication lag เดิมยังต้องใช้เหมือนเดิม

**เกณฑ์ falsify (เขียนก่อนรัน):** ทิ้ง ถ้า DSR ของ Walk-Forward v2 ต่ำกว่า 0.95 หรือไม่มีส่วนเพิ่มเมื่อเทียบกับ momentum รอบยาวจาก ticket 20 (correlation สูงและไม่ได้ Sharpe เพิ่ม)

**Blocked by:** 13 — Walk-Forward v2; 20 — Time-series momentum บน H4/D1

**Status:** ready-for-agent

- [ ] สมมติฐานและเกณฑ์ falsify บันทึกไว้ก่อนรัน
- [ ] บันทึกแหล่งข้อมูลและ coverage ไว้ และถ้าดาวน์โหลดไม่สำเร็จต้องรายงาน
- [ ] ค่าของแต่ละวันถูกใช้ได้ตั้งแต่เวลาที่ข้อมูลเผยแพร่จริงเท่านั้น (มี test)
- [ ] ผ่าน Walk-Forward v2 และบันทึกลง research ledger
- [ ] `## Answer` สรุปผล, ส่วนเพิ่มเมื่อเทียบกับ ticket 20 และคำตัดสินว่าจะเก็บหรือทิ้ง
- [ ] The test suite stays green
