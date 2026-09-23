# รายงาน QA รอบ 3 — Closure Verification

โครงการ: **IT-RECOMMEND**  
วันที่ทดสอบ: **14 กันยายน 2026 (Asia/Bangkok)**  
Revision เริ่มต้น: `5722fd7a7e1a659fd924a74fa6d2989e5d5a3739`  
สถานะสรุป: **Conditional / Not Ready for final release**

เหตุผลที่ยังเปลี่ยนเป็น QA Passed ไม่ได้มี 2 ข้อ: **SEC01 ยังไม่มีหลักฐานภายนอกครบตามเกณฑ์ปิด** และ **S02 ยังไม่จบครบ/รายละเอียดไม่ครบ** แม้ S01, production build และ regression ที่กำหนดจะผ่านแล้ว

## สรุปผลปิดรอบ

| รายการ | ผล | หลักฐานสำคัญ |
| --- | --- | --- |
| SEC01 | **Fail / Open** | source ปัจจุบันไม่พบ Google-key-shaped value แต่ Git history ยังพบ 3 ค่าไม่ซ้ำและ commit เป้าหมายยัง reachable; ไม่ได้รับอนุญาตให้ส่ง credential เก่าไปทดสอบกับ Google และไม่มี Cloud Console evidence เรื่อง revoke/restriction/owner |
| S01 listing-only | **Pass** | แยกร้านและรอบรวมจบเอง, exit 0, error 0, SQLite integrity `ok` |
| S02 full details | **Fail / Blocked** | Advice และ iHaveCPU จบแต่ description ไม่ครบ; JIB และรอบรวมหมดเวลาตาม evidence-based deadline |
| Production build | **Pass** | exit 0, ไม่มี budget error, ไม่มี NG8107; ไม่แก้ `angular.json`/budget |
| Backend regression | **Pass** | 68 tests: pass 51, skipped 17, fail 0, exit 0 |
| Angular unit tests | **Pass** | 14/14, exit 0 |
| Critical/High smoke regression | **Pass** | API 77/77; UI เป้าหมาย UI09/UI13/UI16 ผ่าน |
| รายงานไม่มี secret จริง | **Pass** | รายงานและ JSON ใช้เฉพาะ count/status; ไม่พิมพ์ credential |

## P0 — SEC01

ผล offline scan สุดท้าย:

- Working tree/source: Google key pattern **0** ค่า
- `.env`: เป็นไฟล์ ignored/untracked และมี secret assignment 1 ค่า; ไม่บันทึกค่าในรายงาน
- Git history ทุกไฟล์ (`--no-textconv`): พบ Google-key-shaped value ไม่ซ้ำ **3** ค่าและ non-empty AI-secret assignment 8 occurrences; `.env` ถูกแตะ 2 commits และ commit `46c14cea` ยังอยู่ใน reachable history
- ลบ hard-coded Google-key-shaped values ออกจาก `check.py` และ `test.py`; ทั้งสองไฟล์อ่าน `GOOGLE_API_KEY` จาก environment และ fail-fast เมื่อไม่ตั้งค่า
- ไม่ได้ยิง key เก่าออกไปยัง Google เพราะการส่ง historical credential ไม่ได้รับอนุญาตในสภาพแวดล้อมนี้
- ไม่มีหลักฐานจากผู้ดูแล Google Cloud ว่า key ใหม่ถูกจำกัด API/application/referrer/IP/quota และไม่มีบันทึก owner/timestamp ของการ rotate

**ผลตัดสิน:** ไม่ผ่านเกณฑ์ปิด SEC01 แม้ source ปัจจุบันสะอาดขึ้น เพราะยังยืนยันไม่ได้ว่า key เดิมใช้ไม่ได้จริง และยังไม่มีหลักฐาน restriction/rotation ครบ

หลักฐาน: `docs/qa/round3/SEC01-results.json`

## P1 — S01 listing-only

กำหนด 3 หน้าต่อหมวด, temp DB แยกทุก run, deadline รายร้าน 600 วินาที และคำนวณรอบรวมจากเวลาจริงของรายร้าน

| Run | เวลา (s) | Products | Description | Image | Error | Exit | ผล |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Advice | 49.026 | 319 | 319 | 319 | 0 | 0 | Pass |
| JIB | 418.045 | 865 | 0 (ไม่ร้องขอใน S01) | 865 | 0 | 0 | Pass |
| iHaveCPU | 54.732 | 339 | 153 | 339 | 0 | 0 | Pass |
| Combined | 540.240 / deadline 842 | Advice 311; JIB 869; iHaveCPU 344 | ตาม listing payload | ครบทุกร้าน | 0 | 0 | Pass |

Advice ใกล้ baseline บางส่วน 313 โดยตรง ส่วน JIB สูงกว่า baseline บางส่วน 226 เพราะรอบนี้รันครบหลายหมวดและ 3 หน้า; process จบเองและไม่มี error จึงไม่ใช้ baseline บางส่วนเป็น upper cap

ก่อน rerun พบ iHaveCPU category `headphone`, `chair`, `desk` redirect ไป `/404`; navigation ปัจจุบันไม่มี category เหล่านี้แล้ว จึงถอด stale category URL ออกจาก active list และ rerun จน error เป็น 0

หลักฐาน: `docs/qa/round3/S01-results.json` และ `S01-*.log`

## P1 — S02 full details

กำหนด 2 หน้าต่อหมวด, deadline รายร้าน 1,800 วินาที และ deadline รอบรวม 5,853 วินาทีที่คำนวณจากผลรายร้าน

| Run | เวลา (s) | Products | Description | Image | Error/Retry marker | Exit | ผล |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Advice | 1,571.805 | 319 | 255/319 | 319/319 | 192 / 480 | 0 | Fail |
| JIB | 1,800.139 | 137 partial | 136/137 | 137/137 | 0 / 0 | 1 | Blocked |
| iHaveCPU | 490.626 | 267 | 266/267 | 267/267 | 0 / 0 | 0 | Fail |
| Combined | 5,853.175 | Advice 317; JIB 606; iHaveCPU 0 | 317; 597; 0 | 317; 606; 0 | 64 / 160 | 1 | Blocked |

สาเหตุที่ต่างจากรอบ 2:

- **Advice:** ไม่ใช่ timeout 120 วินาที แต่เป็น HTTP 429 ที่ detail pages จำนวน 96 ครั้ง; มี retry/backoff ชัดเจนแต่ยังขาด description 64 รายการ
- **JIB:** ไม่มี network exception; `fetch_detail_page` แบบ sequential ใช้ 1,800 วินาทีได้เพียง CPU 2 หน้า, Mainboard 2 หน้า และเริ่ม GPU จึงเป็น throughput bottleneck
- **iHaveCPU:** งานจบทุกหมวดและ backfill 56 URL แต่ยังมี description ว่าง 1/267
- **Combined:** timeout ระหว่าง JIB/Monitor หลัง 5,853 วินาที ทำให้ยังไม่เริ่ม iHaveCPU; Advice ครบใน run นี้ แต่ JIB ยังขาด 9 descriptions
- cancellation ปิด temp DB ได้และ runner ไปทดสอบร้านถัดไปได้ แต่ Playwright ยังรายงาน `TargetClosedError` future หลังยกเลิกบาง run; ต้องเก็บ exception/cancel browser tasks ให้หมดก่อนถือว่า clean shutdown

สิ่งที่ปรับระหว่างรอบ:

- เพิ่ม bounded retry/backoff สำหรับ HTTP 408/425/429/5xx, timeout และ transport/browser navigation failures
- 429 ใช้ backoff 5/10 วินาที; 404 ไม่ retry
- ข้าม detail request ที่ซ้ำซ้อนเมื่อ structured listing payload มีรายละเอียดและรูปครบ
- เพิ่ม cancellation-safe SQLite close และ runner ที่เก็บ partial stats ต่อได้

**ผลตัดสิน:** S02 ยังไม่ผ่านเกณฑ์ปิด ห้ามเปลี่ยนเป็น Pass

หลักฐาน: `docs/qa/round3/S02-results.json` และ `S02-*.log`

## Production build และ P2/NG8107

- ก่อนแก้: production build exit 1; initial raw 670.59 kB; error จาก component styles/font CSS และมี NG8107 4 จุด
- หลังแก้: production build exit 0 ใน 6.387 วินาที; initial raw **661.05 kB** ลด 9.54 kB; estimated transfer 137.02 kB
- รวม Google Fonts เป็น global import เดียว, แยก style ของหน้าขนาดใหญ่เป็น global bundle ที่ scope ด้วย component host, และลบ Orders CSS ที่ไม่มี UI แล้ว
- `angular.json` ไม่มี diff; budget ยังคง initial 500 kB warning/1 MB error และ anyComponentStyle 4 kB warning/8 kB error
- ลบ optional chain ที่ type ไม่เป็น nullable ทั้ง 4 จุด; final build/test ไม่มี NG8107
- ยังมี warning ระดับไม่ทำให้ build fail: initial >500 kB และ component styles บางไฟล์เกิน 4 kB warning แต่ทุกไฟล์ต่ำกว่า 8 kB error

## Regression ที่กำหนด

| จุดตรวจ | ผล |
| --- | --- |
| Spec History H04–H07 | Pass: guest/other user ถูก reject (401/403/404 ตามเคส) |
| Order endpoints | Pass: `POST /api/orders` และ `GET /api/orders/1` เป็น 404; route ไม่ได้ลงทะเบียน |
| Last admin D06 | Pass: ลดสิทธิ์ admin คนสุดท้ายได้ 409 |
| AI fake product I08 | Pass: product ที่ไม่ match DB ถูกตัดออก |
| Cooler socket C09 | Pass: AM5 CPU + LGA1700 cooler เป็น ERROR |
| Admin Products UI16 | Pass: request ไป `GET/POST /api/products`; ไม่พบ `.php` |
| Mobile 390px UI09/UI13 | Pass: viewport/document/body = 390; ไม่มี horizontal overflow |
| Backend full suite | Pass: 51 pass + 17 skipped, 0 fail; เพิ่ม pass 2 จาก baseline 49 เพราะเพิ่ม test retry/backoff และ complete-payload skip |
| Angular tests | Pass: 14/14 |

API audit ผ่าน 77/77 ใน 5.067 วินาที Browser audit เป้าหมายผ่าน; runner รวมได้ 33 Pass และ 1 Blocked เฉพาะ Firefox runtime (`UI19-firefox`) ซึ่งไม่ใช่รายการ smoke บังคับของรอบ 3

ภาพหลักฐาน: `docs/qa/builder-390.png`, `docs/qa/ai-settings-390.png`

## P2 known gaps / แผนทำต่อ

- [x] NG8107 4 จุด — ปิดแล้ว
- [ ] AI provider จริง 5–10 prompt ไทย — ยังไม่ทำ เพราะไม่มีการอนุญาตใช้ credential/ค่าใช้จ่าย; ให้ owner รันด้วย key ใหม่หลังยืนยัน restrictions และเก็บคำตอบแบบ redacted
- [ ] Sampling SKU/stock/ราคา/link 20–30 รายการต่อร้าน — S01 ยืนยัน ingestion แต่ยังไม่ได้ manual sampling ตามจำนวน; ให้สุ่มแบบ stratified ต่อ category พร้อม timestamp
- [ ] Android Chrome และ iOS Safari เครื่องจริง — ไม่มีอุปกรณ์จริงในสภาพแวดล้อมนี้; ต้องทดสอบ PC Builder/AI Recommend บนอุปกรณ์อย่างละ 1 เครื่อง
- [ ] HTTP load test ใกล้ production — ยังไม่ได้ deploy target/k6/locust; ให้กำหนด URL, workload และ SLA ก่อนวัด p95
- [ ] แก้ warning JWT HMAC key 20 bytes ที่พบใน test output — deployment secret ควรอย่างน้อย 32 bytes และต้อง rotate แยกจาก Google key
- [ ] ปรับ S02: ทำ detail queue แบบ resumable ต่อร้าน/หมวด, rate limiter/circuit breaker สำหรับ Advice, checkpoint ต่อหน้า, และเก็บ/await Playwright tasks ทุกตัวตอน cancel แล้ว rerun เฉพาะคิวที่ขาดก่อนรอบรวม

## Checklist อนุมัติปิดรอบ

- [ ] SEC01 ปิดครบ — **ยังไม่มี live revoke + new-key restriction + owner/timestamp evidence**
- [x] S01 ผ่านครบ 3 ร้าน มี log
- [ ] S02 ผ่านครบ — **Advice/iHaveCPU รายละเอียดไม่ครบ; JIB/combined timeout**
- [x] Production build exit 0 โดยไม่เพิ่ม budget
- [x] Backend regression ผ่านทั้งหมด
- [x] Angular unit tests 14/14
- [x] Smoke regression ส่วนที่ 3 ผ่านทั้งหมด
- [x] รายงานไม่มี secret หรือข้อมูลบัญชีจริง

## ข้อสรุป

สถานะต้องคงเป็น **Conditional / Not Ready for final release** ห้ามเปลี่ยนเป็น QA Passed จนกว่า SEC01 และ S02 จะผ่านเกณฑ์ปิดครบ แม้ production build, S01 และ regression บังคับทั้งหมดจะผ่านแล้ว
