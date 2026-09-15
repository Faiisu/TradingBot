# แผนพัฒนา Auto Trading Algorithm: จาก "Backtest ที่ดูดี" สู่ "Edge ที่พิสูจน์ได้"

**สถานะ:** แตกเป็น ticket แล้ว (`issues/01`–`31`) และมีการแก้ไขหลังประเมินในข้อ 9 ซึ่ง **มีผลเหนือข้อก่อนหน้าเมื่อขัดกัน**
**วันที่:** 2026-09-15 (แก้ไข 2026-09-16)
**ขอบเขต:** ต่อจาก Phase 1 (Backtest + Paper Trading) จนถึงการตัดสินใจเข้า Live Trading และการดูแลระยะยาว

> คำศัพท์ในเอกสารนี้ (Rule Set, Strategy Candidate, Ensemble, Walk-Forward Validation, Performance Metric, Risk Controls, Market Filter ฯลฯ) ใช้ตามความหมายใน `CONTEXT.md`

---

## 0. สรุปสั้น (TL;DR)

1. **ตัวเลข Backtest ตอนนี้ดีเกินจริง** และสิ่งที่อธิบายได้ดีที่สุดคือระบบกำลังเดิมพัน **ปัจจัยเดียว** คือ momentum ของทองในช่วงขาขึ้นแรงปี 2024–26 (ทองขึ้นจาก 2,579 ไป 4,331 หรือ +68%) ส่วน Ensemble 36 ตัวก็คือสำเนาของ bet เดียวกันที่ correlate กันสูง
2. **ปัญหาหลักไม่ใช่ "มี Rule Set น้อยไป"** แต่เป็น **"เครื่องมือวัดยังแยก edge จริงออกจากโชคและ regime ไม่ได้"** ข้อมูลมีแค่ 2 ปีใน regime เดียว, Performance Metric เอนเอียงไปทาง timeframe เล็ก, เกณฑ์ผ่านคือแค่ "> 0" และยังไม่มีการนับจำนวนครั้งที่ลอง (multiple testing)
3. **ลำดับที่ตัดสินใจ:** (A) ทำเครื่องมือวัดให้เชื่อถือได้ → (B) ขยายข้อมูลเป็น 10+ ปีให้ครอบคลุมหลาย regime → (C) ค่อยค้นหา edge ใหม่อย่างมีระบบ โดยเรียงตามโอกาสสำเร็จ → (D) สร้าง portfolio ตามปัจจัย ไม่ใช่ตามจำนวน candidate → (E) พิสูจน์ว่า live ตรงกับ backtest (parity) → (F) Live ด้วยเงินน้อยพร้อมเกณฑ์ขยาย/หยุดที่กำหนดไว้ล่วงหน้า
4. **เหตุผลรวม:** โอกาสได้กำไรจริงขึ้นกับว่า candidate ที่ผ่านการคัดเลือกเป็น edge จริงกี่ % การเพิ่ม candidate โดยที่ตัวกรองยังหลวมจะเพิ่ม false positive เร็วกว่า true positive การทำตัวกรองให้แม่นก่อนจึงเพิ่มผลตอบแทนที่คาดหวังของ **ทุก** ไอเดียที่จะทดสอบหลังจากนั้น

---

## 1. สถานะปัจจุบัน: หลักฐานจากการตรวจสอบ (audit) วันที่ 2026-09-15

ผมรันการทดลองเพิ่มบนข้อมูลจริงใน cache (สคริปต์อยู่ใน `evidence/`) ได้ผลดังนี้

### 1.1 ตัวเลขที่ "ดีเกินจริง"

| ตัวชี้วัด | ค่า | ทำไมน่าสงสัย |
|---|---|---|
| `macd_12_26_9` M5 | +169% ที่ max DD 0.78% จาก 21,287 trades | return/DD ≈ 216 ขณะที่กลยุทธ์ systematic ระดับโลกส่วนใหญ่ทำได้แค่ 1–3 |
| Ensemble (รวมกำไรรายวัน) | Sharpe รายปีประมาณ 7.3, วันที่กำไร 65% | Sharpe > 3 หลังหักต้นทุนแทบไม่พบในโลกจริงสำหรับรายย่อย |
| Walk-Forward | ผ่านครบ 9/9 Test Window, metric 3,237 | ผ่านง่ายเกินไป แสดงว่าเกณฑ์ไม่มีอำนาจแยกแยะ |
| สมาชิก Ensemble | correlation เฉลี่ยของ PnL รายวันระหว่างคู่ = 0.47 | 36 ตัวไม่ใช่ 36 bet แต่เป็นไม่กี่ bet ที่ถูกนับซ้ำ |

### 1.2 ข่าวดี: ไม่ใช่ bug ด้าน fill เป็นหลัก

ทดสอบโดยค่อยๆ ทำให้ fill สมจริงขึ้นแบบสะสม (`evidence/bias_audit.py`)

| Variant | macd M5 return | macd H1 return | donchian H1 PM |
|---|---|---|---|
| A: engine ปัจจุบัน | 168.9% | 59.4% | 31.6 |
| B: trailing ไม่นับ high/low ของแท่งที่เข้า (ซึ่งเกิดก่อนเข้า) | 189.2% | 62.5% | 31.9 |
| C: + stop/target โดน gap ให้ fill ที่ราคาเปิด | 185.9% | 61.8% | 31.7 |
| D: + เข้าที่ open ของแท่งถัดไป | 175.1% | 59.7% | 19.2 |
| E: + slippage $0.10 ทุกครั้งที่โดน stop | 163.2% | 59.2% | 18.9 |

**สรุป:** มี bias เล็กๆ จริง (engine ตั้งค่า trailing stop เริ่มต้นจาก high/low ของแท่งที่เข้า และ fill stop ที่ราคา stop แม้ตลาดจะ gap) แต่แก้แล้วตัวเลขเปลี่ยนไม่มาก จึงไม่ใช่คำอธิบายหลัก ที่ควรสังเกตคือ DD ของ H1 breakout เพิ่มขึ้นชัดเจน (1.15% → 1.78%) เมื่อเข้าที่ open ถัดไป

### 1.3 Rule Set มีส่วนจริง ไม่ใช่แค่ exit machinery

ใช้ random signal ที่มีความถี่สลับทิศเท่ากับของจริง แล้วใส่ exit/cost ชุดเดียวกัน (`evidence/null_model.py`)

| Candidate | จริง | Random (ค่าเฉลี่ย) |
|---|---|---|
| macd M5 | +169% | **−27%** (ช่วง −30 ถึง −25) ≈ ต้นทุน spread ล้วนๆ |
| bollinger M5 | +87% | −27% |
| macd H1 | +59% | −0.2% (ช่วง −11 ถึง +9) |
| donchian H1 | +36% | +2.2% (ช่วง −7 ถึง +19) |

ทั้งฝั่ง long และ short ของ macd M5 ทำกำไรพอกัน (+51 / +48 simple-sum %) แม้ทองจะขึ้นแรง แปลว่าไม่ใช่แค่ "ถือ long ในตลาดขาขึ้น" แต่เป็น **short-term autocorrelation (momentum) ของราคาทองในช่วงนี้**

### 1.4 หลักฐานสำคัญที่สุด: ทุกอย่างคือปัจจัยเดียว

กำไรขั้นต้น (ก่อนหักต้นทุน) ต่อ trade หน่วย $ เทียบกับต้นทุนที่ใช้ใน model ($0.30 ไป-กลับ)

| กลุ่ม | H1 | M5 |
|---|---|---|
| Trend/Breakout (MACD, Bollinger, Donchian, ATR channel, Supertrend, ADX, Volume breakout) | **+$3.5 ถึง +$7.3** (11–24 เท่าของต้นทุน) | +$0.7 ถึง +$1.5 (2–5 เท่า) |
| MA Crossover | +$2.3 (7.8×) | +$0.30 (**0.98× หรือเสมอตัว**) |
| Mean Reversion (RSI, Stochastic) | **−$3.3 ถึง −$4.2** | −$0.6 ถึง −$1.1 |

- Trend family ชนะ **ทุก** timeframe ส่วน mean-reversion แพ้ **ทุก** timeframe ด้วยขนาดใกล้เคียงกันแบบกลับด้าน นี่คือลายเซ็นของ **regime ที่ราคามี momentum แรง** ไม่ใช่ลายเซ็นของ "Rule Set ที่ฉลาด"
- Timeframe ยิ่งเล็ก edge ต่อ trade ยิ่งบางเมื่อเทียบกับต้นทุน **M5 จึงเปราะที่สุด** เมื่อต้นทุนจริงสูงกว่าที่ model ไว้ (ช่วงข่าว, spread ขยาย, slippage)
- Walk-Forward ผ่าน 9/9 เพราะทั้ง 2 ปีเป็น regime เดียวกัน เลยพิสูจน์ได้แค่ว่า "momentum ใช้ได้ในปี 2025–26" ไม่ได้พิสูจน์ว่า "วิธีคัดเลือกนี้ใช้ได้ในอนาคต"

### 1.5 จุดอ่อนเชิงระเบียบวิธี (methodology)

1. **ข้อมูล 2 ปี = 1 regime:** ไม่เคยเจอช่วงทองขาลง (2013–15) หรือช่วง sideways ยาว (2016–18, 2021–23)
2. **Performance Metric = return/maxDD โดย DD มี floor 0.01%:** candidate ที่ trade ถี่แต่ขนาดเล็กจะได้ค่าสูงผิดปกติ, ไม่คิด DD ระหว่างถือ (equity update เฉพาะตอนปิด trade) และเทียบข้าม timeframe ไม่ได้อย่างยุติธรรม
3. **เกณฑ์ผ่าน "> 0":** ไม่มี hurdle เรื่องต้นทุนที่แย่ลง ความมีนัยสำคัญทางสถิติ หรือจำนวนครั้งที่ลอง (ตอนนี้ลองไปแล้ว 89 candidate และจะเพิ่มอีก)
4. **Position sizing:** `max_position_fraction = 0.2` bind เกือบทุก trade ทำให้ `risk_pct_per_trade = 1%` ไม่มีความหมาย ความเสี่ยงจริงต่อ trade ≈ 0.01–0.06% ของ equity และแต่ละ candidate เสี่ยงไม่เท่ากัน จึงเทียบกันไม่ได้
5. **Ensemble = นับจำนวน ไม่ใช่นับความเสี่ยง:** equal capital ต่อสมาชิก แต่สมาชิก 30 กว่าตัวเป็น momentum เดียวกัน ถ้า regime เปลี่ยน ทุกตัวจะแพ้พร้อมกัน

---

## 2. หลักคิดที่ใช้ตัดสินใจทั้งแผน

### 2.1 สมการของกำไรที่ "หาเจอจริง"

```
กำไรจริงใน Live = Edge จริง − Selection bias (โชคที่ถูกเลือก) − Execution gap (backtest ≠ live) − Regime decay
```

ทุกการตัดสินใจในแผนนี้ต้องทำอย่างน้อยหนึ่งอย่าง: **เพิ่ม Edge จริง**, **ลด Selection bias**, **ลด Execution gap** หรือ **ตรวจจับ Regime decay ให้เร็ว**

### 2.2 Research funnel: ความแม่นของตัวกรองสำคัญกว่าจำนวนไอเดีย

ถ้าในไอเดียที่ทดสอบมีแค่ ~10% ที่เป็น edge จริง และตัวกรองปล่อย false positive ผ่าน 30%:
- ทดสอบ 100 ไอเดีย → edge จริงผ่าน ~8–9 ตัว + โชคผ่าน ~27 ตัว → **ตัวที่ผ่านเป็นของจริงแค่ ~25%**
- ถ้าลด false positive เหลือ 3% → edge จริงผ่าน ~7 + โชคผ่าน ~3 → **ของจริง ~70%**

ข้อสรุปคือ **ปรับตัวกรองให้แม่นก่อน แล้วค่อยเร่งหาไอเดีย** และนี่คือเหตุผลที่ Phase A มาก่อน Phase C

### 2.3 หลักย่อย

1. **Falsify ก่อน optimize:** ทุกสมมติฐานต้องมี "ผลที่ถ้าเกิดแล้วจะทิ้งไอเดียนี้" เขียนไว้ก่อนรัน
2. **เปรียบเทียบที่ความเสี่ยงเท่ากัน:** กลยุทธ์ต่างๆ ต้องถูก size ให้มี volatility เท่ากันก่อนจัดอันดับ
3. **นับทุกการทดลอง:** รวมทั้งที่ล้มเหลว เพื่อหักล้าง multiple testing อย่างซื่อสัตย์
4. **หลาย regime ดีกว่าหลาย candidate:** edge ที่อยู่รอดข้าม 3–4 regime มีค่ามากกว่า candidate ใหม่ 50 ตัวใน regime เดียว
5. **Portfolio ตามปัจจัย (factor):** กระจายข้าม "แหล่งที่มาของกำไร" ไม่ใช่ข้าม "ชื่อ indicator"
6. **ตั้งกฎหยุดไว้ล่วงหน้า:** เกณฑ์หยุด/ลดขนาดใน live ต้องกำหนดก่อนเห็นผล

---

## 3. การตัดสินใจหลัก (Decisions) พร้อมเหตุผล

### D1 — หยุดเพิ่ม Rule Set/Filter ชั่วคราว จนกว่าเครื่องมือวัดจะผ่าน Phase A

- **ตัดสินใจ:** ไม่เพิ่ม candidate ใหม่จนกว่า D2–D5 จะเสร็จ
- **เหตุผล:** ตาม 2.2 ทุก candidate ที่เพิ่มตอนนี้เพิ่ม selection bias โดยที่เรายังวัดมันไม่ได้ ข้อมูลใน 1.4 ชี้ว่า candidate ใหม่แบบ trend จะ "ผ่าน" แทบแน่นอน ซึ่งไม่ได้ให้ข้อมูลใหม่อะไรเลย
- **ทางเลือกที่ไม่เลือก:** เพิ่ม Rule Set ต่อไปพร้อมๆ กับแก้เครื่องมือ → ไม่เลือก เพราะผลที่ได้ช่วงนี้จะต้องรันใหม่ทั้งหมดอยู่ดี

### D2 — ขยายประวัติเป็น 10+ ปี จากแหล่งข้อมูลที่สอง

- **ตัดสินใจ:** ดึงข้อมูล XAUUSD ย้อนหลังอย่างน้อยตั้งแต่ปี 2012 จากแหล่งที่ให้ tick/M1 ฟรี (ตัวเลือกแรกคือ Dukascopy ต้องยืนยันความพร้อมใช้งานใน ticket แรก) แล้วทำเป็น M1 ก่อน resample เป็น M5–D1
- **เหตุผล:**
  - ต้องมีช่วงทองขาลง (2013–15), sideways (2016–18), COVID spike (2020), sideways ดอกเบี้ยขึ้น (2021–23) และขาขึ้น (2024–26) ถึงจะแยก "edge" ออกจาก "regime" ได้
  - Test Window เพิ่มจาก 9 เป็น ~40+ ทำให้สถิติมีความหมาย
  - M1 ใช้จำลองลำดับราคาภายในแท่ง (intrabar) สำหรับ stop/target ของ M15–H1 ได้ถูกต้องขึ้น
- **การควบคุมความต่างของ feed:** ในช่วงที่ซ้อนกัน (2024–26) ต้องเทียบกับข้อมูล Exness ทั้ง correlation ของ return รายแท่ง, ส่วนต่างราคา และตรวจว่า candidate เดียวกันให้สัญญาณ/ผลใกล้กันไหม ถ้าไม่ใกล้ต้องรู้เหตุผลก่อนใช้
- **ทางเลือกที่ไม่เลือก:** ใช้แค่ Exness → ไม่เลือก เพราะ Exness เก็บย้อนหลังได้จำกัด / ใช้ข้อมูลรายวันอย่างเดียว → ไม่เลือก เพราะ candidate ส่วนใหญ่อยู่บน intraday

### D3 — ทำ Backtest ให้สมจริง (execution realism) และทำให้ Paper Trading ใช้ logic เดียวกัน

- **ตัดสินใจ:**
  1. เข้าออเดอร์ที่ **open ของแท่งถัดไป** (สัญญาณรู้ได้หลัง close เท่านั้น)
  2. trailing extreme เริ่มจาก **ราคาเข้า** ไม่ใช่ high/low ของแท่งสัญญาณ
  3. stop/target ที่โดน gap → fill ที่ **open**
  4. ต้นทุน = **spread ต่อแท่งจากข้อมูลจริง × ตัวคูณ** (MT5 เก็บ spread ขั้นต่ำของแท่ง จึงต้องคูณ) + **slippage ต่อการโดน stop** (เริ่มที่ $0.10) + swap จริง
  5. เมื่อแท่งเดียวกันโดนทั้ง stop และ target ให้ใช้ **M1 ตัดสินลำดับ** ถ้าไม่มี M1 ให้ถือว่าโดน stop ก่อน (แบบเดิม)
  6. **Mark-to-market equity ทุกแท่ง** เพื่อให้ DD และ Sharpe รวมช่วงที่ถือ position อยู่
  7. BacktestEngine และ SimulatedBroker ต้องใช้ **ฟังก์ชันตัดสินใจเดียวกัน** (ลดโอกาสที่สองฝั่งจะ drift ออกจากกัน)
- **เหตุผล:** ข้อ 1.2 แสดงว่าแต่ละข้อผลไม่มาก แต่รวมกันแล้วเปลี่ยน DD และอันดับของ H1 breakout อย่างชัดเจน และ execution gap คือตัวทำลาย edge อันดับหนึ่งเมื่อเข้า live จุดสำคัญที่สุดคือข้อ 6 เพราะถ้าไม่มี Sharpe/DD จะผิดตั้งแต่ต้น
- **Stress test บังคับ:** ทุก candidate ต้องรันที่ต้นทุน **1×, 2× และ 3×** แล้วรายงาน "break-even cost" (ต้นทุนที่ทำให้กำไรเป็น 0)

### D4 — เปลี่ยน Performance Metric และเกณฑ์ผ่าน (ต้องเขียน ADR 0003)

- **ตัดสินใจ:**
  - **ตัวจัดอันดับหลัก:** Sharpe รายปีจาก **equity รายวันแบบ mark-to-market** หลังหักต้นทุน 2× (stressed)
  - **รายงานประกอบ:** Calmar ที่ vol-target 10%/ปี, max DD, จำนวน trade, break-even cost, สัดส่วนปีที่กำไร
  - **เกณฑ์ขั้นต่ำในการเข้า Ensemble (ทุกข้อ):**
    1. Sharpe (stressed cost) > 0 ทั้งช่วง
    2. จำนวน trade ≥ 200 (หรือ ≥ 30 ต่อปี)
    3. break-even cost ≥ 3× ต้นทุนปกติ
    4. ชนะ **null model** (random signal ที่ turnover เท่ากัน + exit เดียวกัน) ที่ p < 0.05
- **เหตุผล:**
  - Calmar ที่ floor DD ไว้ 0.01% ให้รางวัลกับ "trade ถี่ ขนาดเล็ก" จึงเอนไปทาง M5 อย่างเป็นระบบ (ดู 1.1)
  - Sharpe บน MTM รายวันเทียบข้าม timeframe ได้ และมีเครื่องมือทางสถิติรองรับ (D5)
  - null model จับกรณีที่กำไรมาจาก exit rule หรือจาก drift ของตลาดแทน Rule Set ได้โดยตรง (ดู 1.3)
- **ทางเลือกที่ไม่เลือก:** Sortino/Omega → ไม่เลือกเป็นตัวหลัก เพราะ deflation ทำได้ยากกว่า ใช้เป็นตัวเสริมได้

### D5 — Research Ledger + การหักล้าง Multiple Testing

- **ตัดสินใจ:**
  - ทุกการรัน (ทุก candidate × parameter × ช่วงข้อมูล) บันทึกลง **ledger** (ไฟล์ append-only เช่น parquet/jsonl) พร้อม config hash, git commit และผล
  - ใช้ **Deflated Sharpe Ratio (Bailey & López de Prado, 2014)** โดย N = จำนวน trial ที่ไม่ซ้ำกันใน ledger
  - ประเมิน **Probability of Backtest Overfitting (PBO)** ด้วย CSCV ของ Ensemble selection rule
  - **เกณฑ์ผ่านของ Walk-Forward:** DSR ของ out-of-sample record ≥ 0.95 และ PBO < 0.3
- **เหตุผล:** เป็นวิธีเดียวที่ทำให้ "ลองมาก" ไม่กลายเป็น "หลอกตัวเองมาก" เพราะยิ่งลองมาก hurdle ก็ยิ่งสูงขึ้นตามอัตโนมัติ ledger ยังช่วยให้ไม่ต้องลองสิ่งที่เคยล้มเหลวซ้ำ
- **ทางเลือกที่ไม่เลือก:** Bonferroni → เข้มเกินไปเมื่อ candidate correlate กัน / White's Reality Check, Hansen SPA → ใช้ได้ดีแต่ implement หนักกว่า เก็บไว้เป็น optional

### D6 — Walk-Forward แบบใหม่บน 10+ ปี

- **ตัดสินใจ:** anchored เหมือนเดิม (ตาม ADR 0002) แต่ Selection Window เริ่มที่ **3 ปี**, Test Window **3 เดือน**, มี **embargo 1 วัน** ระหว่าง Selection/Test และรายงานผลแยกตาม regime (trend-up / trend-down / range / high-vol)
- **เหตุผล:**
  - ข้อมูล 10+ ปีทำให้ Test Window ยาวขึ้นได้ ช่วยลด noise ต่อ window
  - Selection 3 ปีทำให้ผ่าน regime อย่างน้อย 1 รอบก่อนเลือก
  - ผลแยกตาม regime ตอบคำถามสำคัญที่สุดได้: "ถ้า regime เปลี่ยน จะเสียเท่าไร"
- **ความสอดคล้องกับ ADR 0002:** ยังคงหลักการเดิม (validate selection rule ไม่ใช่ candidate, anchored) เปลี่ยนแค่พารามิเตอร์และเกณฑ์ผ่าน จึงเป็น ADR ใหม่ที่อ้างถึง 0002

### D7 — Sizing แบบ Volatility Targeting (แทน fixed fraction ที่ bind)

- **ตัดสินใจ:**
  - **ระดับ trade:** stop ยังเป็น ATR-based แต่ขนาด position คำนวณจาก risk budget ต่อ trade ที่เท่ากันจริงๆ (ไม่ให้ cap bind เป็นปกติ) cap มีไว้แค่กันกรณีผิดปกติ และใช้ leverage/margin จริงของ Exness เป็นขอบบน
  - **ระดับ member:** scale ให้ realized vol ของแต่ละ member เท่ากัน (เช่น 10%/ปี) ก่อนนำไปรวมกัน
  - **ระดับ portfolio:** vol target รวม 10%/ปี มี DD budget ที่ 15% และถ้าเกินให้ลดขนาดครึ่งหนึ่ง
- **เหตุผล:** ทำให้ candidate เทียบกันได้อย่างยุติธรรม (D4), ทำให้ `risk_pct_per_trade` มีความหมายจริง และทำให้ "กำไรที่คาดหวังต่อความเสี่ยงที่รับได้" คำนวณได้ ตอนนี้ความเสี่ยงจริงต่ำจนผลตอบแทนเป็นเงินจริงจะน้อยมากแม้ edge จะจริง
- **ข้อควรระวัง:** vol targeting เพิ่มขนาดตอนตลาดเงียบ จึงต้องมี cap ขั้นต่ำ-สูงของตัวคูณ (เช่น 0.25×–2×)

### D8 — Ensemble → Portfolio ตามปัจจัย (Factor Buckets)

- **ตัดสินใจ:**
  1. จัดกลุ่ม candidate ด้วย **hierarchical clustering บน correlation ของ PnL รายวัน** (ใช้เฉพาะ Selection Window)
  2. จากแต่ละ cluster เลือก **ไม่เกิน 1–2 ตัวแทน** (ตัวที่ DSR สูงสุด)
  3. แบ่งความเสี่ยง **เท่ากันต่อ cluster** (risk parity แบบง่าย) แทนการแบ่งเงินเท่ากันต่อสมาชิก
  4. กฎ one-per-(Rule Set, Entry Timeframe) เดิมถูกแทนด้วยกฎ cluster ซึ่งครอบคลุมกว่า
  5. selection rule ใหม่ทั้งหมดต้องถูก validate ด้วย Walk-Forward (หลักการเดียวกับ ADR 0002)
- **เหตุผล:** correlation 0.47 (1.1) แปลว่าการมี 36 สมาชิกให้การกระจายความเสี่ยงน้อยกว่าที่ดู กำไรระยะยาวของ portfolio มาจาก **จำนวน bet ที่เป็นอิสระต่อกัน** (breadth) ไม่ใช่จำนวนสมาชิก
- **ทางเลือกที่ไม่เลือก:** mean-variance optimization → ไม่เลือก เพราะไวต่อ estimation error มากเกินไปสำหรับข้อมูลขนาดนี้

### D9 — ลำดับการค้นหา Edge ใหม่ (เรียงตามโอกาสสำเร็จ × ความถูกของการทดสอบ)

หลักการเลือก: เริ่มจากสิ่งที่ **มีเหตุผลทางเศรษฐศาสตร์/พฤติกรรมรองรับ** และ **มีหลักฐานในงานวิจัยสาธารณะ** ก่อน แล้วค่อยไปสิ่งที่เป็นแค่ pattern

| ลำดับ | แหล่ง Edge | สมมติฐาน (ทำไมอาจมีอยู่จริง) | วิธีทดสอบ / เกณฑ์ falsify |
|---|---|---|---|
| **1** | **Time-series momentum รอบยาว (H4 / D1, lookback 1–12 เดือน)** | มีงานวิจัยรองรับข้ามหลายสินทรัพย์รวมทั้งทองคำ (Moskowitz, Ooi & Pedersen, 2012) ต้นทุนต่อ trade ต่ำมากเมื่อเทียบกับ edge | ถ้า 10+ ปีแล้ว DSR < 0.95 หรือแพ้ใน regime ขาลง/sideways จนรวมแล้วติดลบ → ทิ้ง |
| **2** | **Regime-conditional: trend เมื่อ trend แรง, mean-reversion เมื่อ range** | หลักฐาน 1.4 แสดงว่า MR แพ้เพราะอยู่ใน trend regime ถ้าจับ regime ได้ MR อาจกลายเป็น bet ที่ correlate ต่ำ | ตัว classifier ใช้ข้อมูลในอดีตเท่านั้น (ADX, Kaufman efficiency ratio, vol percentile) ต้องชนะ "MR ตลอด" และ "trend ตลอด" ใน OOS |
| **3** | **Session / volatility breakout (London open, NY open, หลังข่าว US สำคัญ)** | liquidity และข้อมูลใหม่เข้ามาเป็นช่วงเวลา ทำให้เกิด momentum ระยะสั้นที่ซ้ำกันได้ | Asian Range Breakout เดิมเป็นแค่ baseline ต้องทดสอบด้วยต้นทุน stressed เพราะช่วงข่าว spread กว้าง |
| **4** | **Macro รอบวัน/สัปดาห์ (real yield, DXY เป็นสัญญาณหลักไม่ใช่ filter ของ M5)** | ความสัมพันธ์ทอง-real yield เป็นปัจจัยพื้นฐาน แต่ทำงานบน horizon ยาว การใช้เป็น filter ของ M5 ไม่สอดคล้องกับ horizon นี้ | ทดสอบบน D1 เท่านั้น ใช้ publication lag ตามกฎเดิม |
| **5** | **Exit research แยกออกมาเป็นมิติของตัวเอง** | ข้อ 1.3 แสดงว่า exit มีผลมาก: random entry + exit ปัจจุบันบน H1 ≈ 0 ไม่ใช่ −27% | ทดสอบ exit หลายแบบกับ **random entry** ก่อน exit ที่ดีต้องทำให้ random entry ดีขึ้นอย่างมีนัยสำคัญ |
| **6** | **Seasonality / day-of-week / time-of-day** | หลักฐานอ่อน เสี่ยงเป็น data mining สูง | ทำเป็นลำดับท้าย และต้องผ่าน DSR ที่ N รวมทั้งหมด |

**Parameter policy:**
- อนุญาต grid ขนาดเล็ก (≤ 3 ค่าต่อพารามิเตอร์) แต่เลือกจาก **"ที่ราบ" (plateau)** คือค่าที่เพื่อนบ้านใน grid ให้ผลใกล้กัน ไม่ใช่ค่าที่ดีที่สุดจุดเดียว
- ทุก grid point นับเป็น trial ใน ledger (D5)
- การเลือกพารามิเตอร์ต้องอยู่ **ภายใน** Selection Window ของ Walk-Forward เท่านั้น
- **เหตุผล:** default ค่าเดียวปลอดภัยเรื่อง overfitting แต่ทิ้ง edge ที่อยู่ใกล้ๆ ส่วน plateau ให้ความทนทาน (robust) โดยไม่ต้อง optimize จนเกินไป

### D10 — Paper/Backtest Parity เป็น gate บังคับ

- **ตัดสินใจ:**
  - ทุกวัน re-run BacktestEngine บนแท่งเดียวกับที่ Paper Trading เพิ่งประมวลผล แล้วเทียบ **trade-by-trade** (เวลาเข้า/ออก, ทิศ, exit reason, PnL)
  - เก็บ **ราคา bid/ask จริงตอนตัดสินใจ** ใน Paper Trading (ไม่ใช่แค่ close ของแท่ง) เพื่อวัด spread/slippage จริงเทียบกับที่ model ไว้
  - **Gate:** trade ต้องตรงกัน ≥ 95% และ execution cost จริงต้องไม่เกิน cost ที่ model ไว้ในแบบ stressed
- **เหตุผล:** execution gap เป็นสาเหตุอันดับหนึ่งที่กลยุทธ์ที่ backtest ดีตายใน live ถ้าไม่วัดตั้งแต่ paper เราจะรู้ตอนเสียเงินจริง
- **หมายเหตุ:** Paper Trading dry run ที่รันอยู่ตอนนี้ (ticket 05) มีค่าในฐานะ **engineering test** แต่ **ใช้เป็นหลักฐานเรื่องกำไรไม่ได้** เพราะช่วงเวลาสั้นเกินไป

### D11 — เกณฑ์เข้า Live Trading (Phase 3) ต้องกำหนดล่วงหน้า

ต้องผ่าน **ทุกข้อ** ก่อนเขียน ADR เรื่องการเปลี่ยนจาก demo ไป live (ADR 0001 กำหนดว่าต้องมี phase ที่ออกแบบเรื่องนี้โดยเฉพาะ)

1. Walk-Forward บน 10+ ปี: DSR ≥ 0.95, PBO < 0.3, OOS Sharpe (stressed cost) ≥ 0.7
2. ไม่มี regime ใดที่ OOS DD เกิน DD budget ×1.5
3. Paper parity ผ่าน D10 ต่อเนื่อง **≥ 3 เดือน** และมี trade ≥ 100
4. ผลของ Paper Trading อยู่ภายใน **ช่วง 5–95 percentile** ของการกระจายที่ได้จาก bootstrap ของ backtest ในช่วงเวลายาวเท่ากัน
5. มี kill switch, จำกัดความเสี่ยงรายวัน และ reconcile กับ position จริงของ broker

- **เหตุผลของตัวเลข:** Sharpe 0.7 หลังต้นทุนสูงเป็นระดับที่มีคุณค่าจริงสำหรับกลยุทธ์ systematic เดี่ยวบนสินทรัพย์เดียว ส่วน 3 เดือนเป็นระยะขั้นต่ำที่ยังพอเห็น execution ในหลายสภาพตลาด

### D12 — Live แบบค่อยๆ ขยาย และมีกฎหยุดอัตโนมัติ

- **ขั้นที่ 1:** เงินจริงขนาดเล็ก (ขนาดที่ยอมเสียได้ทั้งหมด) ที่ vol target 1/4 ของเป้าหมาย
- **ขยาย:** ทุก 3 เดือนที่ผลอยู่ในช่วงคาดหวัง (ตามข้อ 4 ของ D11) และ parity ยังผ่าน → ขยายได้ครั้งละไม่เกิน 2×
- **หยุด/ลด (กำหนดไว้ล่วงหน้า):**
  - DD เกิน budget → ลดครึ่ง
  - DD เกิน 1.5× budget → หยุด แล้วกลับไปทำ research
  - rolling 60 วันต่ำกว่า percentile ที่ 5 ของการกระจายที่คาดหวัง → หยุดสมาชิกนั้น
  - execution cost จริงเกิน model 50% ติดต่อกัน 2 สัปดาห์ → หยุดทั้งหมด
- **เหตุผล:** ความเสียหายที่ใหญ่ที่สุดมักมาจาก "ไม่ยอมหยุด" มากกว่า "เลือกกลยุทธ์ผิด" การกำหนดล่วงหน้าตัดอคติทางอารมณ์ออกไป

### D13 — ความเร็วของ research เป็น feature

- **ตัดสินใจ:** ทำ engine ให้ vectorized/numba, cache สัญญาณและผลต่อ config hash, รันขนานข้าม candidate ได้
- **เหตุผล:** DSR/PBO/null model/bootstrap/stress cost ต้องรันมากกว่าเดิม 10–100 เท่า ถ้ารันช้า ทีมจะ "ข้าม" ขั้นตอนตรวจสอบ ซึ่งทำให้ตัวกรองหลวมกลับมาอีก
- **เป้า:** รันครบทุก candidate ที่ต้นทุน 3 ระดับบน 10 ปีได้ภายใน ~10 นาทีบนเครื่องนี้

---

## 4. Roadmap แบ่งตาม Phase (พร้อมเกณฑ์ "เสร็จ")

ลำดับถูกออกแบบให้แต่ละ phase **ลดความเสี่ยงที่ใหญ่ที่สุดที่เหลืออยู่** ก่อนเริ่มสิ่งที่พึ่งพามัน

### Phase A — เครื่องมือวัดที่เชื่อถือได้ (Measurement Integrity)
**ทำไมก่อน:** ทุกผลลัพธ์หลังจากนี้พึ่งพามัน (D1)

| # | งาน | เสร็จเมื่อ |
|---|---|---|
| A1 | Execution realism ใน engine + shared decision function กับ SimulatedBroker (D3 ข้อ 1–3, 7) | test พิสูจน์ next-open entry, gap fill, ไม่มี pre-entry extreme และ Backtest กับ Paper ให้ trade เดียวกันบนแท่งชุดเดียวกัน |
| A2 | Mark-to-market equity รายวัน + cost model ตาม spread จริง + slippage + stress 1×/2×/3× (D3 ข้อ 4, 6) | ทุก candidate มี break-even cost และ Sharpe บน MTM |
| A3 | Null model (random signal, turnover เท่ากัน, หลาย seed) + p-value (D4) | รายงาน p-value ต่อ candidate บนหน้า Backtest |
| A4 | Research ledger + DSR (D5) | ledger บันทึกทุก run อัตโนมัติ และแสดง DSR พร้อม N |
| A5 | ADR 0003: Performance Metric และเกณฑ์ผ่านใหม่ + อัปเดต `CONTEXT.md` (D4) | ADR merged และ glossary ตรงกับ code |
| A6 | Speed-up engine (D13) | full run ≤ ~10 นาที |

**Exit criteria ของ Phase A:** รัน 89 candidate เดิมด้วยเครื่องมือใหม่แล้วได้ **รายการที่ยังรอดหลังต้นทุน 2× + null model + DSR** เป็น baseline ใหม่ (คาดว่าจะเหลือน้อยกว่าเดิมมาก ซึ่งถือเป็นผลที่ถูกต้อง ไม่ใช่ความล้มเหลว)

### Phase B — ประวัติยาวและ Regime (History & Regimes)
**ทำไมลำดับนี้:** ต้องมีเครื่องมือจาก A ก่อนถึงจะใช้ข้อมูล 10 ปีได้คุ้ม และต้องมี B ก่อน C เพราะการค้นหา edge บน regime เดียวจะซ้ำรอยปัญหาเดิม

| # | งาน | เสร็จเมื่อ |
|---|---|---|
| B1 | ดึง + ตรวจ + cache XAUUSD M1 ย้อนหลัง 2012→ปัจจุบัน จากแหล่งที่สอง (D2) | coverage report + รายงานเทียบกับ Exness ช่วงซ้อนกัน |
| B2 | Reference Market ย้อนหลัง 10+ ปี (DXY, XAG, real yield) | Market Filter รันบน 10 ปีได้ |
| B3 | Regime labeler (ใช้ข้อมูลอดีตเท่านั้น) + รายงานผลแยก regime (D6) | หน้า Backtest แสดงตาราง candidate × regime |
| B4 | Walk-Forward แบบใหม่ (3y/3m/embargo) + PBO (D5, D6) + ADR 0004 | verdict ใหม่ใช้ DSR/PBO |
| B5 | รัน baseline ทั้งหมดใหม่บน 10+ ปี | **คำตอบว่า momentum edge ในปัจจุบันอยู่รอดข้าม regime หรือไม่** |

**จุดตัดสินใจสำคัญหลัง B5:**
- ถ้า trend family **รอด** ข้าม regime (ขาดทุนไม่เกิน budget ในช่วง range/ขาลง) → ใช้เป็นแกนของ portfolio แล้วไป C เพื่อหา bet ที่ correlate ต่ำมาเสริม
- ถ้า **ไม่รอด** (กำไรมาจากปี 2024–26 เป็นหลัก) → ห้ามเข้า live ด้วยชุดเดิม ให้ C เน้น regime-conditional (D9 ลำดับ 2) และ momentum รอบยาว (ลำดับ 1)

### Phase C — ค้นหา Edge อย่างมีระบบ (Edge Discovery)
**ทำไมลำดับนี้:** ตัวกรองแม่นแล้ว (A) และข้อมูลครอบคลุมแล้ว (B) ทุกไอเดียจึงถูกตัดสินอย่างยุติธรรม

- ทำตามลำดับใน D9 ทีละหัวข้อ
- แต่ละหัวข้อเป็น **ticket ประเภท research** ที่มี: สมมติฐาน → เกณฑ์ falsify (เขียนก่อนรัน) → ผล → บันทึก ledger
- **กฎการเพิ่ม candidate เข้า registry:** ต้องผ่าน DSR + null model + stress cost + ไม่ correlate > 0.7 กับสมาชิกที่มีอยู่ **หรือ** ดีกว่าสมาชิกใน cluster เดียวกันอย่างมีนัยสำคัญ
- **เป้าหมาย:** ได้ **3–5 cluster ที่ไม่ correlate กัน** ใน portfolio ไม่ใช่ได้ candidate จำนวนมาก

### Phase D — Portfolio Construction
- Vol targeting 3 ระดับ (D7), factor buckets (D8), DD budget/de-risking
- Walk-Forward ของ selection + allocation rule ทั้งชุด
- **เสร็จเมื่อ:** OOS portfolio บน 10+ ปีผ่านเกณฑ์ข้อ 1–2 ของ D11

### Phase E — Paper Parity (ขยายจาก Phase 1 ticket 05)
- Daily reconciliation, บันทึก bid/ask จริง, dashboard เปรียบเทียบ paper กับ backtest distribution (D10)
- รันต่อเนื่อง ≥ 3 เดือน
- **เสร็จเมื่อ:** ผ่านเกณฑ์ข้อ 3–5 ของ D11

### Phase F — Live แบบจำกัดความเสี่ยง (Phase 3 ตาม CONTEXT)
- ADR ใหม่เรื่องการแยก live account, order execution path, reconcile, kill switch
- เริ่มตาม D12
- **Research loop ต่อเนื่อง:** re-run Walk-Forward รายเดือนเมื่อมีข้อมูลใหม่, ติดตาม decay และทำ Phase C วนต่อไปเพื่อหา bet ใหม่มาแทนตัวที่เสื่อม

```
A (วัดให้ถูก) → B (ข้อมูลหลาย regime) → [จุดตัดสินใจ] → C (หา edge) → D (portfolio) → E (parity 3 เดือน) → F (live เล็ก → ขยายตามเกณฑ์)
                                                          ↑__________________ research loop ต่อเนื่อง __________________|
```

---

## 5. สิ่งที่ตัดสินใจ "ไม่ทำ" และเหตุผล

| ไม่ทำ | เหตุผล |
|---|---|
| Optimize พารามิเตอร์บนข้อมูลทั้งหมด | selection bias สูงสุด และ Walk-Forward จับไม่ได้ถ้าทำนอก Selection Window |
| Deep learning / ML บนราคาดิบ | สัญญาณต่อ noise ต่ำ ข้อมูล 1 สินทรัพย์ไม่พอ และ overfit ง่ายมาก ถ้าจะใช้ ML ให้ใช้เป็น regime classifier ที่มี feature น้อยหลังจากผ่าน Phase B แล้วเท่านั้น |
| Martingale / grid / เพิ่มขนาดตอนขาดทุน | backtest ดูดีจนวันที่ระเบิด ส่วน tail risk ไม่ปรากฏในข้อมูล 2–10 ปี |
| Scalping M1 / tick | edge ต่อ trade บางกว่าต้นทุน (M5 ก็เปราะแล้วตามข้อ 1.4) |
| ซ้อน Trend Filter + Market Filter หลายชั้น | เพิ่ม degrees of freedom โดยไม่มีเหตุผลรองรับ (กฎเดิมใน CONTEXT ถูกต้องแล้ว) |
| เพิ่ม indicator ใหม่บน M5 | ข้อ 1.4 แสดงว่าเป็น bet เดียวกันที่เปราะต่อต้นทุน |
| เชื่อผล Paper Trading ระยะสั้นว่า "กำไร" | ไม่มีนัยสำคัญทางสถิติ ใช้วัด parity เท่านั้น |

---

## 6. ความเสี่ยงหลักและวิธีรับมือ

| ความเสี่ยง | สัญญาณเตือน | การรับมือ |
|---|---|---|
| Edge ปัจจุบันเป็นแค่ regime 2024–26 | B5 แสดงว่าขาดทุนหนักในช่วง range/ขาลง | จุดตัดสินใจหลัง B5, portfolio ตามปัจจัย, regime-conditional |
| ข้อมูลจากแหล่งที่สองไม่ตรงกับ Exness | correlation ของ return ต่ำ หรือสัญญาณต่างกันมาก | ใช้ข้อมูลยาวสำหรับ "ความทนทานของสัญญาณ" เท่านั้น ส่วนต้นทุนใช้ของ Exness |
| Overfit ผ่านการลองซ้ำหลายรอบ | DSR ลดลงเมื่อ N เพิ่ม | ledger + DSR/PBO เป็น gate อัตโนมัติ |
| Execution จริงแย่กว่า model (ข่าว, spread กว้าง, requote) | parity < 95% หรือ cost จริง > model | D10 gate, stress cost 2× เป็นค่ามาตรฐาน, กรองเวลาข่าวถ้าจำเป็น |
| เป้าหมายผลตอบแทนไม่สมจริง | คาดหวังระดับ backtest ปัจจุบัน | ตั้งความคาดหวังที่ Sharpe 0.7–1.5 และผลตอบแทนตาม vol target (~7–15%/ปีที่ vol 10%) |
| ความซับซ้อนของ code เพิ่ม → bug ใน live path | parity test ไม่ผ่านแบบสุ่มๆ | shared decision function (D3.7) และ test ที่ใช้ข้อมูลจริงเป็น fixture |

---

## 7. นิยาม KPI ที่ใช้ตลอดโครงการ

| KPI | นิยาม | ใช้ที่ไหน |
|---|---|---|
| **Sharpe (MTM, stressed)** | mean/std ของ return รายวันแบบ mark-to-market ×√252 ที่ต้นทุน 2× | ตัวจัดอันดับหลัก |
| **DSR** | Deflated Sharpe Ratio ที่ N = trial ไม่ซ้ำใน ledger | gate ของ candidate และ Walk-Forward |
| **PBO** | ความน่าจะเป็นที่ตัวที่ดีที่สุดใน-sample จะแย่กว่ามัธยฐาน out-of-sample (CSCV) | gate ของ selection rule |
| **Break-even cost** | ต้นทุนไป-กลับ ($) ที่ทำให้กำไรสุทธิ = 0 | ความเปราะต่อ execution |
| **Null p-value** | สัดส่วน random-signal run ที่ Sharpe ≥ ของจริง | ยืนยันว่า Rule Set มีส่วนจริง |
| **Regime DD** | max DD แยกตาม regime label | ความทนทาน |
| **Parity rate** | % trade ใน paper ที่ตรงกับ backtest re-run | gate เข้า live |
| **Execution gap** | cost จริง (bid/ask + slippage) − cost ที่ model ไว้ | gate เข้า live และ kill switch |
| **Effective bets** | จำนวน cluster อิสระใน portfolio | คุณภาพการกระจายความเสี่ยง |

---

## 8. สิ่งที่ควรทำทันที (5 ticket แรก ตามลำดับ)

1. **A1 — Execution realism + shared decision function** แก้ pre-entry extreme, next-open entry, gap fill และทำให้ Backtest กับ Paper ใช้ logic เดียวกัน
2. **A2 — MTM equity + cost stress 1×/2×/3× + break-even cost**
3. **A3 — Null model benchmark บนหน้า Backtest**
4. **A4 + A5 — Research ledger + DSR + ADR 0003 (Performance Metric ใหม่)**
5. **B1 — Spike: ยืนยันแหล่งข้อมูล 10+ ปี** และเทียบกับ Exness ช่วง 2024–26 (ทำคู่ขนานกับ A ได้ เพราะไม่ขึ้นต่อกัน)

ระหว่างนี้: **ปล่อย Paper Trading dry run (Phase 1 ticket 05) รันต่อ** เพื่อปิด ticket ในฐานะ engineering test แต่ **ยังไม่ควร** ใช้ Ensemble ปัจจุบันเป็นพื้นฐานของการตัดสินใจเรื่องเงินจริง

---

## 9. การแก้ไขหลังประเมินเทียบกับการใช้งานจริง (2026-09-16)

ตรวจสอบกับบัญชี Exness demo, paper loop ที่กำลังรัน และ engine จริงแล้ว พบว่าต้องแก้ข้อต่อไปนี้ (ticket ทั้งหมดสะท้อนการแก้ไขนี้แล้ว)

### 9.1 ข้อที่เขียนผิด

| เดิม | ความจริงที่ตรวจพบ | แก้เป็น |
|---|---|---|
| D2 / B1: ต้องใช้แหล่งข้อมูลที่สอง (Dukascopy) | Exness มี M1 และ H1 ที่มี spread จริงตั้งแต่ **2017-05** (~9.3 ปี) ครอบคลุมขาลงปี 2018, COVID, sideways ปี 2021–23 และขาขึ้นปี 2024–26 ส่วนข้อมูลก่อนปี 2017 เป็นแท่งหลอก (H1 ~78 แท่งต่อไตรมาส) | ใช้ Exness ก่อนและต้องมีตัวตรวจแท่งหลอก (ticket 03) ส่วน XAG/DXY บน MT5 มีแค่ตั้งแต่ 2022-08 จึงห้ามตัดช่วงข้อมูลทองตาม |
| D10 / Phase E: parity ระหว่าง paper กับ backtest ที่ใช้ logic เดียวกัน | ถ้าใช้ logic เดียวกันกับแท่งชุดเดียวกัน ผลย่อมตรงกันเสมอ จึงวัด execution gap ไม่ได้ | บันทึก bid/ask จริง (ticket 19) และเพิ่มขั้นส่งออเดอร์จริงบน demo (ticket 27–28) |
| D5: DSR ใช้ N = จำนวน trial ทั้งหมด | candidate correlate กันสูง ถ้าใช้ N ดิบจะเข้มเกินจริง | ใช้ effective N จากการจัด cluster (ticket 12) และเลื่อน PBO/CSCV ออกไปก่อน |
| A3: random signal ที่ความถี่สลับทิศเท่ากัน | ระยะถือ position ต่างจากสัญญาณจริง | ใช้ circular shift ของสัญญาณจริง (ticket 11) |
| A6 / D13: speed-up เป็นงานของ Phase A | MACD M5 ข้อมูล 2 ปีใช้แค่ 1.6 วินาทีต่อรอบ | ไม่ใช่งานแยก ให้รันขนานเมื่อเวลาเกินเกณฑ์ที่ระบุใน ticket 11 และ 13 |
| ใช้ swap ปัจจุบันกับทั้งช่วงข้อมูล | ปี 2017–21 ดอกเบี้ยต่ำ swap จริงต่างจากวันนี้มาก | ใช้ swap ตามประวัติดอกเบี้ย (ticket 07) |
| Spread ในแท่ง MT5 คือ spread ขั้นต่ำของแท่ง | ยังไม่ได้ยืนยัน | ถือตัวคูณเป็นพารามิเตอร์สำหรับ stress แล้ว calibrate จาก bid/ask จริง (ticket 06, 19) |

### 9.2 ข้อจำกัดในโลกจริงที่แผนเดิมพลาดไป

1. **Lot ขั้นต่ำ:** XAUUSDm มีขั้นต่ำ 0.01 lot = 1 oz ≈ $4,300 notional ขณะที่สมาชิก Ensemble ปัจจุบันถือ notional ได้ ~$28 (ทุน ~$139 × 0.2) ซึ่ง **เล็กกว่าขั้นต่ำประมาณ 150 เท่า Ensemble ปัจจุบันจึงส่งออเดอร์จริงไม่ได้** เรื่องทุนต้องเป็นเงื่อนไขในการคัดเลือก (ticket 15, บัญชีเริ่มต้น $5,000)
2. **บัญชีแบบ hedging:** สมาชิกที่ถือทิศตรงข้ามจะเสีย spread สองฝั่ง ต้องมีชั้น netting (ticket 16)
3. **Stop ใน live:** ต้องเป็น SL ฝั่ง server และแก้ trailing ทุกแท่ง ไม่ใช่ตรวจหลังแท่งปิด (ticket 28)
4. **Bug ใน paper loop:** loop นับรอบ M5 จากเวลาที่เริ่มรัน สมาชิก Timeframe ใหญ่จึงตัดสินใจช้า 5–55 นาทีแต่ยังบันทึกราคาเข้าเป็น close ของแท่ง (ticket 01)

### 9.3 ลำดับที่ปรับใหม่

แกนหลักคือ **01 → 02 → 03–09 → 10 (จุดตัดสินใจ go/no-go)** เพราะการรัน candidate เดิมบนข้อมูล 9 ปีด้วยต้นทุน stress และ equity แบบ MTM เป็นทางที่เร็วที่สุดในการรู้ว่า edge รอดข้าม regime หรือไม่

ส่วนงาน execution (27 → 28 → 29 → 30 → 31) เดินคู่ขนานได้หลัง ticket 16

---

## ภาคผนวก: การ reproduce หลักฐาน

```bash
.venv/Scripts/python.exe .scratch/edge-discovery-roadmap/evidence/bias_audit.py   # ข้อ 1.2
.venv/Scripts/python.exe .scratch/edge-discovery-roadmap/evidence/null_model.py    # ข้อ 1.3
```

- ตัวเลขข้อ 1.1 และ 1.4 คำนวณจาก `data/backtest_results.json` (generated 2026-09-15T10:54 UTC)
- Sharpe รายวันและ correlation ในข้อ 1.1 คำนวณจาก PnL ณ เวลาปิด trade (ยังไม่ใช่ MTM) จึงเป็นค่าประมาณที่ **ดีเกินจริง** อยู่แล้ว ซึ่งยิ่งสนับสนุนข้อสรุป

### เอกสารอ้างอิงแนวคิด
- Moskowitz, Ooi & Pedersen (2012), *Time Series Momentum*, Journal of Financial Economics
- Bailey & López de Prado (2014), *The Deflated Sharpe Ratio*, Journal of Portfolio Management
- Bailey, Borwein, López de Prado & Zhu (2017), *The Probability of Backtest Overfitting*, Journal of Computational Finance
- White (2000), *A Reality Check for Data Snooping*, Econometrica; Hansen (2005), *A Test for Superior Predictive Ability*
