# สรุปผล QA และรายการที่ต้องดำเนินการเพิ่มเติม

โครงการ: **IT-RECOMMEND**  
รอบทดสอบ: 12–13 กันยายน 2026 (Asia/Bangkok)  
เอกสารอ้างอิงฉบับเต็ม: [QA_REPORT_2026-09-12.md](QA_REPORT_2026-09-12.md)  
ผลทดสอบแบบโครงสร้าง: [all-results.json](qa/all-results.json)

## สรุปสำหรับผู้บริหาร

ระบบผ่าน regression และ functional test ส่วนใหญ่แล้ว แต่ **ยังไม่ควรประกาศว่าปิด QA 100%** เพราะยังมีความเสี่ยงด้านความปลอดภัย 1 รายการ และการทดสอบ scraper แบบ live อีก 2 รายการที่หมดเวลาก่อนจบ

| สถานะ | จำนวน | สัดส่วน |
| --- | ---: | ---: |
| Pass | 141 | 96.58% |
| Fail | 1 | 0.68% |
| Blocked | 2 | 1.37% |
| N/A | 2 | 1.37% |
| **รวม** | **146** | **100%** |

หากไม่นับ 2 ฟีเจอร์ที่ไม่มีอยู่ในขอบเขตระบบปัจจุบัน (N/A) อัตราผ่านของเคสที่ทดสอบได้หรือเริ่มทดสอบแล้วคือ **141/144 หรือ 97.92%**

## ผลแยกตามระบบ

| ระบบ | Pass | Fail | Blocked | N/A | สถานะรอบนี้ |
| --- | ---: | ---: | ---: | ---: | --- |
| Auth & Users | 17 | 0 | 0 | 0 | ผ่าน |
| Products & Pricing | 21 | 0 | 0 | 0 | ผ่าน |
| PC Builder & Compatibility | 19 | 0 | 0 | 0 | ผ่าน |
| AI Recommend | 20 | 0 | 0 | 0 | ผ่านด้วย mock provider |
| Spec History | 12 | 0 | 0 | 0 | ผ่าน |
| Cart / Checkout / Orders | 0 | 0 | 0 | 1 | ไม่อยู่ในขอบเขตรุ่นนี้ |
| Admin Panel | 6 | 0 | 0 | 1 | ผ่านส่วนที่มีอยู่; ไม่มี admin/orders |
| Scraper & Database | 8 | 0 | 2 | 0 | ยังต้องทดสอบ live ซ้ำ |
| Non-Functional | 38 | 1 | 0 | 0 | ค้าง SEC01 |

## สิ่งที่แก้ไขและยืนยันแล้วในรอบนี้

- ปิดช่องโหว่ Spec History: ทุก endpoint ใช้ JWT, ยึดเจ้าของข้อมูลจาก token และตรวจ owner/admin ก่อนลบ
- ยกเลิก endpoint คำสั่งซื้อทั้งหมดตามขอบเขตที่ยืนยันว่าโครงการนี้ไม่ใช่ระบบ e-commerce
- เพิ่ม backend validation สำหรับอีเมล รหัสผ่าน ราคา และข้อมูลสินค้า
- ทำให้ JWT เก่าถูกยกเลิกหลังผู้ใช้เปลี่ยนรหัสผ่าน
- ป้องกันการลดสิทธิ์หรือลบผู้ดูแลระบบคนสุดท้าย
- ปรับ AI post-validation ให้ตัดสินค้าที่จับคู่ฐานข้อมูลไม่ได้ ตรวจงบประมาณ และกรองคำแนะนำ compatibility ที่ขัดแย้ง
- ปรับ compatibility ของ socket/cooler/TDP และข้อความแนะนำให้ deterministic มากขึ้น
- แก้ราคาหลักของสินค้าให้คำนวณใหม่จากราคาที่เป็นบวกต่ำสุดของร้านค้า
- ย้าย Admin Products มาใช้ FastAPI พร้อม JWT และเพิ่ม pagination/search/error state
- เพิ่ม timeout/cancel/error state ในหน้า AI Recommend
- แยก error state ออกจาก empty state ในหน้าสินค้า รายละเอียดสินค้า PC Builder ประวัติ โปรไฟล์ และหน้าผู้ดูแล
- ปรับ navbar บนหน้าจอมือถือ และเพิ่ม/ปรับ unit tests ของ Angular

## รายการที่ต้องดำเนินการเพิ่มเติม

### P0 — ต้องทำก่อนเผยแพร่หรือปิด QA

#### SEC01: Google API key เคยถูก commit ใน Git history

- สถานะ: **Fail / High**
- หลักฐาน: commit `46c14cea` มี `.env` ที่บันทึก `GOOGLE_API_KEY` แบบไม่ว่าง
- ความเสี่ยง: แม้ `.env` ปัจจุบันจะไม่ถูก track แต่ key เดิมยังอาจถูกอ่านได้จากประวัติ repository และสำเนาที่เผยแพร่ไปแล้ว
- สิ่งที่ต้องทำ:
  1. เพิกถอน key เดิมใน Google Cloud Console ทันที
  2. สร้าง key ใหม่และจำกัด API, application/referrer/IP และ quota เท่าที่จำเป็น
  3. อัปเดต secret ในสภาพแวดล้อม deploy โดยไม่ commit ลง Git
  4. ประเมินการล้าง `.env` ออกจาก Git history ด้วย `git filter-repo` หรือวิธีที่ทีมอนุมัติ แล้ว force-push และแจ้งผู้ร่วมงานให้ clone ใหม่
  5. ตรวจ Git history และ secret scanner ซ้ำ โดยห้ามพิมพ์ค่าของ key ลง log หรือรายงาน
- ผู้รับผิดชอบที่เหมาะสม: เจ้าของ Google Cloud project และผู้ดูแล Git repository
- เกณฑ์ปิด: key เดิมใช้งานไม่ได้, key ใหม่ถูกจำกัดสิทธิ์, secret scan ไม่พบค่า secret ที่ใช้งานได้ และมีบันทึกการดำเนินการ

### P1 — ต้องทดสอบซ้ำก่อนรับรอง scraper

#### S01: Full scraper แบบไม่เก็บรายละเอียดหมดเวลา

- สถานะ: **Blocked**
- ผลล่าสุด: เกิน 120 วินาที; เก็บได้บางส่วนจาก Advice 313 และ JIB 226 รายการ แต่ยังไม่จบครบสามร้าน
- สิ่งที่ต้องทำ: รันซ้ำในสภาพแวดล้อมที่เข้าถึงเครือข่ายได้ เพิ่มเวลาอย่างมีขอบเขต เก็บ elapsed time/จำนวนสินค้า/error แยกร้าน และตรวจว่า process จบเองได้
- เกณฑ์ปิด: ทั้งสามร้านจบครบตามจำนวนหน้าที่กำหนด ไม่มี exception ที่ไม่ถูกจัดการ และฐานข้อมูลชั่วคราวมีข้อมูลถูกต้อง

#### S02: Full scraper พร้อมรายละเอียดหมดเวลา

- สถานะ: **Blocked**
- ผลล่าสุด: เกิน 120 วินาทีและยังไม่มีผลรวมที่ใช้สรุปได้
- สิ่งที่ต้องทำ: รันแยกร้านหรือแยกหมวดเพื่อหาจุดช้า ตรวจ timeout/retry/rate limit และค่อยรันรวมพร้อมเวลาที่เหมาะสม
- เกณฑ์ปิด: งานครบทุกหน้าที่กำหนด รายละเอียดสินค้าถูกบันทึก และกรณี network failure ถูก retry หรือรายงานอย่างชัดเจน

### P1 — แก้ก่อนสร้าง production artifact

#### Production build ติด Angular CSS budget

- สถานะ: **ยังไม่ผ่าน production build**
- ผลล่าสุด: development build ผ่าน แต่ default production build exit code 1 เพราะ style ของบาง component และ inlined fonts เกิน `anyComponentStyle` maximumError 8 kB
- สิ่งที่ต้องทำ: ลด/รวม CSS ที่ซ้ำ แยก global utility ที่ใช้ร่วมกัน และตรวจ font loading; ปรับ budget เฉพาะเมื่อทีมยอมรับขนาด bundle และมีเหตุผล ไม่ควรเพิ่มเพดานเพื่อซ่อนปัญหา
- เกณฑ์ปิด: `npm --prefix It-shop run build` จบด้วย exit code 0 โดยไม่มี budget error

### P2 — ปรับคุณภาพและเพิ่มความมั่นใจ

- แก้คำเตือน Angular `NG8107` จำนวน 4 จุด โดยลบ optional chaining ที่ type ระบุว่าไม่เป็น null หรือแก้ type ให้ตรงกับข้อมูลจริง
- ทดสอบ AI กับ provider จริงแบบจำกัดค่าใช้จ่าย เพื่อตรวจภาษาไทย คุณภาพคำอธิบาย benchmark และความสอดคล้องของคำตอบ ไม่ใช้ผล mock เป็นหลักฐานรับรอง semantic quality
- ทำ sampling สินค้าจริงเพิ่มสำหรับ SKU, stock, ราคา และลิงก์ของแต่ละร้าน โดยบันทึกวันเวลาที่ตรวจ เพราะข้อมูลร้านค้าเปลี่ยนได้
- ทดสอบ responsive บนอุปกรณ์จริงอย่างน้อย Android Chrome และ iOS Safari; รอบนี้ Firefox/WebKit เป็น browser engine บนเครื่องทดสอบ
- เพิ่ม HTTP/network load test ในสภาพแวดล้อมใกล้ production ก่อนกำหนด SLA; ผล TestClient ปัจจุบันเป็นเพียง smoke test

## ข้อที่ไม่ใช่บั๊กในขอบเขตรุ่นนี้

- `NA01`: ไม่มีหน้า cart/checkout และไม่มี flow แก้จำนวนหรือชำระเงิน
- `NA02`: ไม่มีหน้า admin/orders
- ทั้งสองรายการต้องกลับมาออกแบบและทดสอบใหม่เฉพาะเมื่อมีการเพิ่มฟีเจอร์ e-commerce ในอนาคต

## หลักฐานการทดสอบหลัก

| ชุดทดสอบ | ผลล่าสุด |
| --- | --- |
| Backend unittest discovery | 66 tests: ผ่าน 49, skipped 17, ไม่มี fail |
| Regression suites เดิม REG01–REG05 | 38/38 ผ่าน |
| AI UI script | ผ่าน |
| Angular unit tests | 14/14 ผ่าน |
| Angular development build | ผ่าน; มีคำเตือน NG8107 4 จุด |
| API audit | 77/77 ผ่าน |
| Browser audit (Chromium) | 34/34 ผ่าน |
| Cross-browser audit (Firefox/WebKit) | 8/8 ผ่าน |
| Scraper audit | ผ่าน 9, blocked 2, fail 0 |
| Production build | ไม่ผ่าน CSS budget |

## ลำดับดำเนินงานรอบถัดไป

1. เจ้าของระบบ revoke/rotate Google API key และส่งหลักฐานที่ไม่เปิดเผยค่า secret
2. ผู้ดูแล repository วางแผนล้าง Git history และประสานผู้ร่วมงานก่อน force-push
3. Frontend ลด CSS เพื่อให้ production build ผ่าน และแก้ NG8107
4. รัน S01/S02 ใหม่แบบแยกร้านก่อน แล้วรันรวมเมื่อทราบเวลาที่เหมาะสม
5. รัน backend, Angular, API, browser และ security regression อีกครั้ง
6. อัปเดต `all-results.json` และรายงานฉบับเต็ม จากนั้นจึงพิจารณาเปลี่ยนสถานะเป็น QA Passed

## Checklist สำหรับอนุมัติปิดรอบ

- [ ] SEC01 ปิดครบทั้ง revoke/rotate, จำกัดสิทธิ์ และตรวจประวัติซ้ำ
- [ ] S01 ผ่าน
- [ ] S02 ผ่าน
- [ ] Production build ผ่าน
- [ ] Backend regression ผ่านทั้งหมด
- [ ] Angular unit tests ผ่านทั้งหมด
- [ ] API และ browser regression ผ่านทั้งหมด
- [ ] รายงานผลไม่มี secret หรือข้อมูลบัญชีจริง

**ข้อสรุป:** โค้ดส่วนหลักพร้อมสำหรับการทดสอบยืนยันรอบถัดไป แต่รอบ QA นี้ยังมีสถานะ **Conditional / Not Ready for final release** จนกว่า SEC01, S01, S02 และ production build จะถูกปิดครบ
