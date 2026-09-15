# 16: รวม exposure ของทุกสมาชิกเป็น net position

**What to build:** บัญชี Exness เป็นแบบ hedging ถ้าสมาชิกถือทิศตรงข้ามกัน ระบบจะเปิด position จริงสองฝั่งและเสีย spread ทั้งสองฝั่งโดยไม่ได้อะไรเลย

ให้รวม position ที่สมาชิกแต่ละตัวต้องการเป็น **net position เดียว** (หน่วย lot):
- Backtest ของ Ensemble คิดต้นทุนเฉพาะเมื่อ net position เปลี่ยน
- หน้า Paper Trading แสดงสัดส่วนของแต่ละสมาชิกและ net lot

การ netting ยังช่วยเรื่อง lot ขั้นต่ำด้วย เพราะ exposure ของหลายสมาชิกรวมกันแล้วปัดเป็น lot ได้

**Blocked by:** 15 — ตรวจทุนพอส่งออเดอร์จริง

**Status:** ready-for-agent

- [ ] Net position = ผลรวม exposure ของสมาชิก ปัดตาม step ของ lot
- [ ] สมาชิกที่ถือทิศตรงข้ามและหักล้างกันพอดีได้ net เป็นศูนย์และไม่เสียต้นทุน (มี test)
- [ ] หน้า Backtest แสดงผลของ Ensemble แบบคิดต้นทุนที่ net เทียบกับแบบคิดต้นทุนรายสมาชิก
- [ ] หน้า Paper Trading แสดง net lot และสัดส่วนของแต่ละสมาชิก
- [ ] The test suite stays green
