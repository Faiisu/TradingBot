# 26: Research — Seasonality (ลำดับความสำคัญต่ำสุด)

**Type:** research

**What to build:** ทดสอบรูปแบบตามเวลา ได้แก่ วันในสัปดาห์ ช่วงเวลาในวัน และช่วงของเดือนหรือปี

หลักฐานสาธารณะของรูปแบบเหล่านี้อ่อนและเสี่ยงเป็น data mining สูง จึงอยู่ลำดับท้ายสุด

**เกณฑ์ falsify (เขียนก่อนรัน):** ต้องผ่าน DSR ที่คิดจาก effective N ของ research ledger ทั้งหมด (ไม่ใช่เฉพาะ trial ของ ticket นี้) และต้องผ่าน null model ไม่เช่นนั้นให้ทิ้ง

**Blocked by:** 12 — Research ledger + DSR; 13 — Walk-Forward v2

**Status:** ready-for-agent

- [ ] สมมติฐานและเกณฑ์ falsify บันทึกไว้ก่อนรัน
- [ ] ทุก trial ถูกบันทึกลง research ledger
- [ ] `## Answer` สรุปผลและคำตัดสินว่าจะเก็บหรือทิ้ง
- [ ] The test suite stays green
