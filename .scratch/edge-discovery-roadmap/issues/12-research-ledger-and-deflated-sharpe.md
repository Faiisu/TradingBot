# 12: Research ledger + Deflated Sharpe ที่ใช้ effective N

**What to build:** ทุกการรัน Backtest (candidate × พารามิเตอร์ × ช่วงข้อมูล × ระดับต้นทุน) ต้องถูกบันทึกลง ledger แบบ append-only พร้อม code version, config hash และผลลัพธ์ ledger นี้คือจำนวนครั้งที่ "ลอง" อย่างซื่อสัตย์ รวมทั้งครั้งที่ล้มเหลว

จากนั้นคำนวณ **Deflated Sharpe Ratio** โดยใช้ **จำนวน trial อิสระที่มีผลจริง (effective N)** ซึ่งประมาณจากการจัด cluster ของ trial ที่ correlate กัน

ห้ามใช้ N ดิบ เพราะ candidate ส่วนใหญ่ correlate กันสูง ถ้าใช้ N ดิบ hurdle จะเข้มเกินจริงจนไม่มีอะไรผ่าน

**Blocked by:** 08 — Performance Metric v2

**Status:** ready-for-agent

- [ ] ทุกการรัน Backtest และ Walk-Forward Validation เพิ่มรายการลง ledger อัตโนมัติ
- [ ] การรัน config เดิมซ้ำไม่นับเป็น trial ใหม่
- [ ] หน้า Backtest แสดง N ดิบ, effective N และ DSR ของทุก candidate
- [ ] Test: trial ที่เป็น noise และ correlate กันจำนวนมาก ต้องได้ effective N น้อยกว่า N ดิบมาก และตัวที่ดีที่สุดในกลุ่มนั้นได้ DSR ต่ำ
- [ ] The test suite stays green
