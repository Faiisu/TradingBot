# 24: Research — ศึกษา exit ด้วย random entry

**Type:** research

**What to build:** แยกผลของ exit ออกจากผลของ entry

หลักฐานเดิม: เมื่อใช้ exit ชุดปัจจุบัน, random entry บน H1 ได้ผลใกล้ศูนย์ แต่บน M5 ขาดทุนประมาณ 27% ซึ่งใกล้กับต้นทุน spread ล้วนๆ แสดงว่า exit มีผลมาก

วิธีทดสอบ:
1. ทดสอบ exit หลายแบบ (trailing หลายระยะ, target หลายค่า, time stop) กับ entry แบบสุ่มหรือแบบเลื่อนสัญญาณก่อน
2. exit ที่ดีต้องทำให้ผลของ random entry ดีขึ้นอย่างมีนัยสำคัญ
3. จากนั้นจึงนำ exit ที่ผ่านไปใช้กับ candidate จริง

**เกณฑ์ falsify (เขียนก่อนรัน):** ไม่เปลี่ยน exit ถ้า exit ใหม่ไม่ช่วย random entry อย่างมีนัยสำคัญ

**Blocked by:** 11 — Null model; 13 — Walk-Forward v2

**Status:** ready-for-agent

- [ ] สมมติฐานและเกณฑ์ falsify บันทึกไว้ก่อนรัน
- [ ] ผลของทุก exit บน random entry ถูกบันทึกลง research ledger
- [ ] Exit ที่ผ่านถูกทดสอบกับ candidate จริงผ่าน Walk-Forward v2
- [ ] `## Answer` สรุปผลและคำตัดสินว่าจะเปลี่ยน Risk Controls หรือไม่
- [ ] The test suite stays green
