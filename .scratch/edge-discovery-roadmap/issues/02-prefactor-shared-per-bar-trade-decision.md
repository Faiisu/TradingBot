# 02: Prefactor — Backtest กับ Paper Trading ใช้ logic ตัดสินใจรายแท่งชุดเดียวกัน

**What to build:** ทำให้การเปลี่ยนแปลงที่จะตามมาง่ายก่อน วันนี้ Backtest และ Paper Trading มี logic เรื่อง stop-loss, trailing stop, profit target, signal-change exit และการ re-entry ในแท่งเดียวกันเขียนแยกกันสองชุด โดยใช้ comment คอยบอกว่า "ต้องตรงกัน" ให้รวมเป็นการตัดสินใจรายแท่งชุดเดียวที่ทั้งสองฝั่งเรียกใช้ เพื่อให้ ticket 04–06 แก้ครั้งเดียวแล้วมีผลทั้งสองฝั่ง **พฤติกรรมต้องไม่เปลี่ยน**

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [ ] มีการตัดสินใจรายแท่งชุดเดียวที่ทั้ง Backtest และ Paper Trading ใช้
- [ ] Backtest ก่อนและหลังการเปลี่ยนแปลงให้ผลเหมือนกันทุกประการ: candidate เดิม trade เดิม และ Performance Metric เดิมทุกตัว
- [ ] มี test ที่ป้อนแท่งชุดเดียวกันทีละแท่งเข้าฝั่ง Paper Trading แล้วได้ trade ตรงกับ Backtest ทุก trade สำหรับ candidate ตัวแทน (ครอบคลุม trailing stop, profit target, stop-loss และ re-entry ในแท่งเดียวกัน)
- [ ] Paper Trading loop ยังเริ่มและประมวลผลแท่งได้ตามปกติ
- [ ] The test suite stays green
