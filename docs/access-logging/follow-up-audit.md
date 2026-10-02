# Access logging follow-up audit

ตรวจวันที่ 2 ตุลาคม 2026 (Asia/Bangkok) ต่อจาก commit `3c0d718c`

## User ID

`get_current_user` ใน `backend/shop_api.py` ตั้ง `request.state.user_id = user.uid`
หลังตรวจ token, ผู้ใช้ และ token version สำเร็จอยู่แล้ว `require_admin` ใช้ dependency นี้ต่อ
จึงไม่ต้องแก้ logic การยืนยันตัวตนหรือ schema ของ SQLite

เพิ่ม regression ใน `backend/test_ai_sessions.py` โดยใช้ JWT ที่ลงนามจริงสำหรับผู้ใช้ใน DB
ชั่วคราว เรียก `/api/profile` ผ่าน middleware และตรวจ JSON ที่ส่งไป Supabase MockTransport:
token ถูกต้องได้ HTTP 200 และ user ID; ไม่มี token/invalid token ได้ 401 และ user ID เป็น null
assert ว่า log ไม่มีอีเมลหรือ token และปรับ fixture proxy ของ integration test เดิมให้ตรงระบบปัจจุบัน
เทสต์นี้ไม่สร้างบัญชีหรือแก้ข้อมูลบน production

## Profile upload

Angular ตรวจ file size ก่อนสร้าง request ถ้าเกิน `4 * 1024 * 1024` bytes จะล้าง input
และแสดง “ไฟล์ใหญ่เกินไป กรุณาเลือกรูปไม่เกิน 4 MB” โดยไม่ส่ง HTTP request
ไฟล์ที่ขนาดเท่าขีดจำกัดส่งได้ และมีพื้นที่เหลือสำหรับ multipart overhead ก่อนถึง Function limit

Proxy แปลง upstream 413 เป็น JSON ที่มี `code=PAYLOAD_TOO_LARGE` และข้อความไทย
หาก Vercel ปฏิเสธก่อน Function ทำงาน proxy จะไม่ได้รับ request นั้น Angular จึงตรวจ status 413
โดยตรงด้วย รองรับ error body แบบ JSON, text หรือ HTML โดยแสดงข้อความไทยเดียวกัน
ตรวจ multipart/body/auth forwarding เดิมด้วย Node tests

## Secret audit

- ตรวจ tracked files และไฟล์ untracked ที่ไม่ถูก ignore รวม README, docs และ full source snapshot
- ตรวจทุก unique text blob ที่เข้าถึงได้จาก history ของ `main` รวม commit `3c0d718c`
- ใช้ pattern สำหรับชื่อตัวแปรพร้อม literal ยาว, JWT prefix และ Supabase secret prefix
  พร้อมตรวจ exact match กับ proxy/Supabase service keys ที่อ่านจาก Railway อย่างเป็นส่วนตัว
- การสแกนครั้งแรกตรวจ 7,509 เวอร์ชันไฟล์ข้อความ: real-key exact matches 0 และ candidates
  ที่ต้องตรวจต่อ 0; พบเฉพาะ synthetic fixtures ที่ระบุชัด ไม่ใช่ค่าจริงของ hosting
- ตำแหน่ง fixture ใน source: `It-shop/tests/proxy.test.mjs:14`,
  `backend/test_access_log.py:33`, `backend/test_ai_sessions.py:89`; snapshot/history มีสำเนาของ fixtures
- `.env` และ `backend/.env` ถูก ignore และไม่ tracked; `.env.example` มีแต่ชื่อตัวแปรกับค่าว่าง
- ไม่พิมพ์ matched values หรือ credentials ลง terminal/report ไม่พบเหตุให้ rotate proxy secret
  หรือ Supabase service key และไม่ต้องตั้ง environment variable เพิ่มสำหรับงานนี้

## Validation

- Backend automated suites ทั้ง 19 modules: 330 tests ผ่าน ด้วย DB/uploads ชั่วคราว
- Angular ทั้ง 18 test files: 58 tests ผ่าน
- Node proxy: 6 tests ผ่าน
- Production build ผ่าน; มี warnings เรื่อง bundle/CSS size เดิม ไม่มี build errors
- `git diff --check` ผ่าน

ไฟล์ `test_*.py` ที่เป็นสคริปต์ตรวจเว็บ/DB แบบ manual ไม่ใช่ automated test suites
ไม่ได้ import เพื่อรันรวมโดยสุ่ม เพราะบางไฟล์เรียกเว็บจริงหรือ DB จริง
ไม่มีการแก้ AI recommendation logic หรือ SQLite schema ในงานนี้
