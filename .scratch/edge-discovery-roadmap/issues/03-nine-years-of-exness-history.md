# 03: ประวัติ Exness 9 ปี (ตั้งแต่ 2017-05) พร้อมตัดแท่งหลอก

**What to build:** Backtest ใช้ประวัติทองทุก Timeframe ตั้งแต่จุดที่ Exness เริ่มมีข้อมูล intraday จริง (ตรวจแล้ววันที่ 2026-09-15 ว่า M1 และ H1 ที่มี spread เริ่มราวเดือน 2017-05) จนถึงปัจจุบัน แทนข้อมูลแค่ 2 ปี เพื่อให้ครอบคลุมหลาย regime: ขาลงปี 2018, ขาขึ้นปี 2019, COVID ปี 2020, sideways/ขาลงปี 2021–23 และขาขึ้นแรงปี 2024–26

ข้อมูลก่อนปี 2017 เป็นแท่งหลอก (H1 มีแค่ ~78 แท่งต่อไตรมาส แทนที่จะเป็น ~1,460) ห้ามปนเข้ามาโดยไม่รู้ตัว

Reference Market บน MT5 (DXY, XAGUSD) มีข้อมูลแค่ตั้งแต่ 2022-08 จึง **ต้องไม่ตัดช่วงข้อมูลทองให้สั้นลงตาม** Market-Filtered Candidate ประเมินเฉพาะช่วงที่ Reference Market ของตัวเองมีข้อมูล ส่วน candidate ที่ใช้แค่ทองใช้ช่วงเต็ม

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] การตรวจ bar capacity ของ MT5 ครอบคลุม M5 ประมาณ 9.5 ปี
- [ ] Coverage report ตรวจเจอช่วงแท่งเบาบางหรือแท่งหลอกในแต่ละ Timeframe และจุดเริ่มต้นของข้อมูลทองอยู่หลังช่วงนั้น ไม่รวมเข้ามาเงียบๆ
- [ ] Candidate ที่ใช้แค่ทองรันบนช่วง 2017-05 → ปัจจุบัน ส่วน Market-Filtered Candidate รันบนช่วงที่ Reference Market ของตัวเองมีข้อมูล
- [ ] เมื่อ candidate แบบไม่มี filter กับแบบมี filter แข่งกันในช่อง (Rule Set, Entry Timeframe) เดียวกัน ให้เปรียบเทียบบนช่วงข้อมูลที่ซ้อนกันเท่านั้น
- [ ] ใน Walk-Forward Validation, Market-Filtered Candidate จะเข้าคัดเลือกได้เฉพาะขั้นที่ทั้ง Selection Window และ Test Window อยู่ในช่วงที่ Reference Market มีข้อมูล
- [ ] หน้า Backtest แสดงช่วงข้อมูลของแต่ละ candidate และรายงานเวลาที่ใช้รันทั้งหมด
- [ ] Paper Trading ไม่ได้รับผลกระทบ
- [ ] The test suite stays green
