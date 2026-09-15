# 11: Null model แบบ circular shift + p-value ต่อ candidate

**What to build:** พิสูจน์ว่า Rule Set มีส่วนต่อกำไรจริง ไม่ใช่กำไรมาจาก exit rule หรือ drift ของตลาด

วิธีคือเลื่อนสัญญาณจริงของ candidate แบบวนรอบ (circular shift) ด้วย offset สุ่ม การเลื่อนแบบนี้รักษาระยะถือ position และ turnover ไว้ แต่ทำลายจังหวะเวลาของสัญญาณ จากนั้นรันด้วย exit และต้นทุนชุดเดียวกัน

- **p-value** = สัดส่วนของรอบที่เลื่อนแล้วได้ Sharpe ≥ ของจริง
- เกณฑ์เข้า Ensemble เพิ่มเงื่อนไข **p < 0.05**

ใช้วิธีนี้แทน random signal ที่มีความถี่สลับทิศเท่ากัน เพราะวิธีนั้นทำให้ระยะถือ position ต่างจากของจริง

**Blocked by:** 08 — Performance Metric v2

**Status:** ready-for-agent

- [ ] ทุก candidate ถูกรันแบบเลื่อนสัญญาณอย่างน้อย 100 offset และรายงานเวลาที่ใช้ ถ้ารันทั้งหมดเกิน ~15 นาทีให้รันขนานข้าม candidate
- [ ] หน้า Backtest แสดง p-value ของทุก candidate
- [ ] เกณฑ์เข้า Ensemble รวมเงื่อนไข p < 0.05
- [ ] Test: สัญญาณสังเคราะห์ที่ฝัง edge ไว้ได้ p ต่ำ ส่วนสัญญาณสุ่มได้ p ไม่ต่ำ
- [ ] The test suite stays green
