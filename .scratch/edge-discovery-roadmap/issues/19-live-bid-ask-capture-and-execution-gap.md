# 19: บันทึก bid/ask จริงใน Paper Trading + รายงาน execution gap

**What to build:** การเทียบผล Paper Trading กับ Backtest บนแท่งชุดเดียวกัน วัด execution gap ไม่ได้ เพราะทั้งสองฝั่งใช้ logic เดียวกัน ผลย่อมตรงกันเสมอ

ให้ Paper Trading บันทึก **bid/ask จริงและเวลา** ในจุดต่อไปนี้:
- ทุกครั้งที่ตัดสินใจ
- ทุกครั้งที่เข้า position
- ทุกครั้งที่ออกด้วย stop, target หรือ signal change

จากนั้นรายงานต้นทุนจริง (spread + ราคาที่ขยับไปจากราคาอ้างอิง) เทียบกับ cost model จาก ticket 06 และเสนอตัวคูณ spread ที่ calibrate จากข้อมูลจริง

**Blocked by:** 01 — Paper loop ตัดสินใจตรงเวลา; 06 — ต้นทุนตาม spread จริง

**Status:** ready-for-agent

- [ ] ราคา bid/ask และเวลาของทุกเหตุการณ์ข้างต้นถูกบันทึกเก็บไว้
- [ ] หน้า Paper Trading แสดงต้นทุนตาม model เทียบกับต้นทุนที่วัดได้ ทั้งราย trade และค่าเฉลี่ยแบบ rolling
- [ ] รายงานตัวคูณ spread ที่แนะนำ พร้อมจำนวนตัวอย่างที่ใช้คำนวณ
- [ ] The test suite stays green
