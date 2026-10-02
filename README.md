# IT-RECOMMEND — ระบบแนะนำและจัดสเปกคอมพิวเตอร์

เว็บแอปพลิเคชันสำหรับค้นหาอุปกรณ์ เปรียบเทียบราคา Advice, JIB และ iHaveCPU จัดสเปกด้วยตนเอง หรือขอคำแนะนำจาก AI โดยใช้รายการสินค้าและราคาในฐานข้อมูลร่วมกับกฎตรวจสอบฮาร์ดแวร์

เอกสารนี้อ้างอิงโค้ดปัจจุบัน ณ วันที่ 2 ตุลาคม 2026 ระบบหลักคือ `It-shop/` และ `backend/shop_api.py`

## ความสามารถปัจจุบัน

- ค้นหาและกรองสินค้า ดูรายละเอียด รูปภาพ ราคาและลิงก์ร้านค้า รวมถึงประวัติราคาที่บันทึกไว้
- จัดสเปกด้วยตนเองผ่าน PC Builder ตรวจความเข้ากันได้ สรุปราคา และบันทึกประวัติสเปก
- ใช้ AI ใน 3 โหมด: แนะนำสเปก (`recommend`), เปรียบเทียบสเปก (`compare`) และตรวจความเข้ากันได้ (`compat`)
- เลือกผู้ให้บริการ AI ได้ระหว่าง Google, OpenAI, OpenRouter และ OpenCode Zen พร้อมระบุ model ID เอง
- ต้องเข้าสู่ระบบก่อนใช้ปุ่มสินค้า จัดสเปก AI ตรวจสเปก และประวัติ; หน้าแรก เข้าสู่ระบบ และสมัครสมาชิกเปิดได้โดยไม่ล็อกอิน
- สมัครสมาชิก เข้าสู่ระบบด้วย JWT แก้ไขโปรไฟล์ เปลี่ยนรหัสผ่าน และอัปโหลดรูปโปรไฟล์
- ผู้ดูแลระบบจัดการสินค้า สมาชิก และเรียกอัปเดตข้อมูลผ่าน scraper ได้

ราคาที่แสดงเป็นข้อมูลจากการดึงข้อมูลครั้งล่าสุด ไม่ใช่ราคาสดทุกครั้งที่เปิดหน้าเว็บ สินค้าบางรายการอาจมีข้อมูลเพียงบางร้าน ความครบถ้วนของสเปกและข้อมูลต้นทางมีผลต่อผลตรวจความเข้ากันได้ ซึ่งอาจแสดง `UNKNOWN` เมื่อยังยืนยันไม่ได้

## เทคโนโลยีและโครงสร้าง

| ส่วน | เทคโนโลยี / ไฟล์หลัก |
| --- | --- |
| Frontend | Angular 21.2, TypeScript 5.9, SCSS, Tailwind CSS 4 |
| Backend | Python, FastAPI, Uvicorn, SQLAlchemy, Pydantic |
| ฐานข้อมูล | SQLite (`backend/shop.db`) |
| Authentication | PyJWT และ bcrypt |
| AI | HTTP API ผ่าน httpx, retrieval จากฐานข้อมูลและกฎ Markdown |
| Scraper | httpx และ Playwright Chromium |
| การทดสอบ | Python unittest และ Angular/Vitest |

```text
Project/
├── It-shop/                     # Frontend หลัก
│   └── src/app/
│       ├── pages/               # สินค้า, AI, PC Builder, ประวัติ, ผู้ดูแล
│       ├── services/            # API และ authentication
│       └── guards/              # ตรวจสิทธิ์หน้าเว็บ
├── backend/
│   ├── shop_api.py              # FastAPI และ migration เมื่อเริ่มระบบ
│   ├── shop.db                  # ฐานข้อมูลที่ระบบหลักใช้
│   ├── init_db.py               # สร้างฐานข้อมูลเริ่มต้นและนำเข้า CSV
│   ├── recommender.py           # ดึงตัวเลือกสินค้าและสร้างคำแนะนำ AI
│   ├── compat_engine.py         # กฎตรวจความเข้ากันได้
│   ├── spec_parser.py           # แปลงข้อมูลสินค้าเป็นสเปกที่ตรวจสอบได้
│   ├── gpu_power_reference.py   # ข้อมูลอ้างอิงกำลังไฟ GPU
│   ├── full_scraper.py          # ดึงสินค้า ราคา และรายละเอียดจาก 3 ร้าน
│   ├── train_compat_knowledge.py # ปรับข้อมูลต้นทางเป็นข้อเท็จจริงฮาร์ดแวร์
│   ├── rules/                  # ฐานความรู้ Markdown
│   └── test_*.py               # ชุดทดสอบและสคริปต์ตรวจสอบ
├── docs/                       # เอกสารโครงงานและ schema เดิม
├── pc-recommender/             # Frontend อีกชุด ไม่ได้เรียกโดย run.bat
├── pc_part/                    # ระบบ PHP เดิม
├── main.py, main2.py           # จุดเข้าใช้งานรุ่นก่อน
├── .env                        # การตั้งค่าฝั่งเซิร์ฟเวอร์
├── run.bat                     # เปิด backend และ frontend บน Windows
└── start_backend.bat           # ติดตั้ง requirements และเปิด backend
```

## ติดตั้งและเปิดใช้งานบน Windows

ใช้ Python 3.11 ขึ้นไป และ Node.js ที่ตรงกับ `engines` ของ Angular CLI ในโปรเจกต์ (`^20.19.0 || ^22.12.0 || >=24.0.0`) พร้อม npm

### 1. ติดตั้ง dependencies

เปิด PowerShell ที่โฟลเดอร์รากของโปรเจกต์:

```powershell
$env:PYTHONUTF8 = '1'
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r backend\requirements.txt
npm --prefix It-shop ci
```

`python-dotenv`, `cryptography`, Playwright และ `boto3` อยู่ใน `backend/requirements.txt` แล้ว `shop_api.py` โหลด `.env` ที่รากโปรเจกต์ โดยไม่ทับ environment variables ที่ตั้งไว้ใน process หรือ hosting platform

หากต้องใช้ scraper หรือทดสอบส่วนที่ใช้ Playwright ให้ติดตั้งเพิ่ม:

```powershell
.\venv\Scripts\python.exe -m playwright install chromium
```

### 2. ตั้งค่าเซิร์ฟเวอร์

สร้างหรือแก้ไข `.env` ที่รากโปรเจกต์ โดยรักษาค่าที่ตั้งไว้เดิม ตัวอย่างนี้แสดงเฉพาะ placeholder:

```dotenv
JWT_SECRET=replace-with-a-random-secret-of-at-least-32-bytes
AI_KEY_ENCRYPTION_KEY=replace-with-a-generated-fernet-key

# ทางเลือกสำหรับ local; ค่า default อิง working directory
DATABASE_URL=sqlite:///./shop.db
UPLOAD_ROOT=uploads
REQUIRE_EXISTING_DB=1
CORS_ORIGINS=http://localhost:4200

# เลือกตั้งค่าเฉพาะผู้ให้บริการที่ต้องการใช้
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
GOOGLE_API_KEY=
GOOGLE_MODEL=gemini-3-flash-preview
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENCODE_ZEN_API_KEY=
OPENCODE_ZEN_MODEL=minimax-m2.5
```

placeholder ของ `JWT_SECRET` และ `AI_KEY_ENCRYPTION_KEY` ต้องแทนด้วยค่าสุ่มที่สร้างเองก่อน startup ทั้งสองตัวจำเป็นแม้ยังไม่ได้ใช้ AI โดย `AI_KEY_ENCRYPTION_KEY` ต้องเป็น Fernet key: ข้อมูลสุ่ม 32 bytes ที่เข้ารหัสเป็น URL-safe Base64 (โดยทั่วไปยาว 44 ตัวอักษร รวม padding) ห้ามใช้ข้อความสุ่มทั่วไปหรือ AI provider key แทน

สำหรับเครื่องใหม่ที่ **ยังไม่มี `.env`** คำสั่งนี้สร้าง key ทั้งสองและเขียนลงไฟล์โดยไม่แสดงค่าใน terminal และจะหยุดหากไฟล์มีอยู่แล้ว:

```powershell
.\venv\Scripts\python.exe -c "from pathlib import Path; import secrets; from cryptography.fernet import Fernet; p=Path('.env'); f=p.open('x', encoding='utf-8'); f.write('JWT_SECRET=' + secrets.token_urlsafe(48) + '\nAI_KEY_ENCRYPTION_KEY=' + Fernet.generate_key().decode('ascii') + '\n'); f.close()"
```

ถ้ามี `.env` อยู่แล้ว ให้รักษา key เดิม และเพิ่มเฉพาะค่าที่ขาดผ่าน secret manager หรือ editor ที่เชื่อถือได้ สร้าง encryption key ด้วย `Fernet.generate_key().decode('ascii')` แล้วเก็บทั้งสตริง รวม `=` ท้ายค่า ใน `AI_KEY_ENCRYPTION_KEY` ของ `.env` สำหรับ local หรือ Railway service variables สำหรับ hosting จำกัดสิทธิ์อ่านไฟล์ สำรอง key แยกอย่างปลอดภัยจาก DB และใช้ค่าเดิมทุก restart/replica ห้ามใส่ key ลง repository, frontend, log หรือรายงาน

การเปลี่ยน encryption key โดยไม่มีการ decrypt ด้วย key เดิมและ re-encrypt ข้อมูล จะทำให้ AI key ที่บันทึกไว้ถอดรหัสไม่ได้ โค้ดปัจจุบันคืนค่าที่ decrypt ไม่สำเร็จเป็นข้อความเดิมเพื่อรองรับข้อมูลเก่า จึงไม่ตรวจพบ key ที่ rotate ผิดอย่างชัดเจน และไม่มี migration ที่เข้ารหัส plaintext เก่าทั้งหมดอัตโนมัติ

| ตัวแปร | เงื่อนไข startup / การใช้งาน |
| --- | --- |
| `JWT_SECRET` | บังคับ; ค่าสุ่มอย่างน้อย 32 bytes และห้ามซ้ำกับ provider key |
| `AI_KEY_ENCRYPTION_KEY` | บังคับ; ต้องเป็น Fernet key ที่ถูกต้อง |
| `DATABASE_URL` | default `sqlite:///./shop.db`; ใช้ SQLite ตาม implementation ปัจจุบัน ซึ่งมี SQLite-specific connect args และ SQL migrations |
| `REQUIRE_EXISTING_DB` | ทางเลือก; ค่า `1` ปฏิเสธ startup หากไฟล์ SQLite ไม่มีอยู่ ต้องสร้าง DB ก่อน |
| `UPLOAD_ROOT` | default `uploads`; ต้องเขียนได้ เพราะ startup สร้างโฟลเดอร์ `profile` และ mount `/uploads` |
| `CORS_ORIGINS` | default `http://localhost:4200`; คั่น origins ด้วย comma เมื่อ frontend เรียก backend ข้าม origin |
| `PORT` | ใช้ใน start command ของ Railway; local ใช้ `--port 3000` |

ชื่อโมเดลข้างต้นเป็นค่าเริ่มต้นในโค้ด ต้องเลือกโมเดลที่บัญชีผู้ให้บริการของคุณเรียกใช้งานได้ Google รองรับ `GEMINI_API_KEY` เป็นค่าแทน `GOOGLE_API_KEY` ด้วย

ระบบเลือกผู้ให้บริการเริ่มต้นจาก key ฝั่งเซิร์ฟเวอร์ตามลำดับ OpenAI → Google → OpenRouter → OpenCode Zen หากไม่มี key จะใช้ OpenAI เป็นค่าเริ่มต้น สมาชิกตั้งค่า provider, model, custom model และ key ของตนเองได้ในหน้า AI โดย custom model มีลำดับความสำคัญเหนือโมเดลที่เลือกจากรายการ

เมื่อส่งคำขอ AI ระบบใช้ key ที่ส่งมากับคำขอ ตามด้วย key ที่สมาชิกบันทึกไว้สำหรับ provider เดียวกัน และ key ฝั่งเซิร์ฟเวอร์ Provider key ไม่จำเป็นต่อ startup: โหมด `recommend` ใช้ผลจัดสเปกจาก catalog ได้เมื่อไม่มี key ส่วน `compare`, `compat` และ `ask` ผ่าน `/api/ai/recommend` ต้องมี key มิฉะนั้นตอบ HTTP 400 API ตรวจสเปกแบบ deterministic ไม่ต้องใช้ provider key แต่ต้องเข้าสู่ระบบ การเปลี่ยน `.env` ต้องเริ่ม backend ใหม่

AI key ของสมาชิกที่บันทึกผ่าน `PUT /api/ai/settings` เข้ารหัสด้วย Fernet ก่อนเก็บใน `user_ai_settings.api_key` ของ SQLite ส่วน `GET /api/ai/settings` ถอดรหัสและส่งคืนเฉพาะเจ้าของที่ยืนยันตัวตนแล้ว Browser เก็บ key ในหน่วยความจำของ component และลบรายการเก่า `ai_provider_settings` ใน localStorage เมื่อโหลด settings ข้อมูลเก่าที่เป็น plaintext ยังอ่านได้ จึงต้องรักษา DB, backup และ `.env` เป็นข้อมูลส่วนตัว และใช้ HTTPS เมื่อ hosting

`JWT_SECRET` ต้องเป็นค่าสุ่มอย่างน้อย 32 bytes และห้ามใช้ค่าเดียวกับ key ของ AI provider ระบบจะปฏิเสธการเริ่มทำงานเมื่อไม่ได้ตั้งค่าหรือค่าสั้นเกินไป เมื่อต้อง rotate ให้แจ้ง deploy window ก่อน แล้วรัน `python backend/rotate_jwt_secret.py --apply`; การ restart ด้วยค่าใหม่จะทำให้ JWT เดิมทั้งหมดใช้ไม่ได้และผู้ใช้ทุกคนต้องเข้าสู่ระบบใหม่ สคริปต์ไม่พิมพ์ secret แต่รายงานเฉพาะความยาว fingerprint และเวลา rotate

### 3. เตรียมฐานข้อมูล

หากมี `backend/shop.db` ที่ใช้งานอยู่แล้ว ให้ใช้ไฟล์เดิมและข้ามการสร้างฐานข้อมูล

สำหรับฐานข้อมูลใหม่เท่านั้น ให้รันจากโฟลเดอร์ `backend`:

```powershell
Set-Location backend
..\venv\Scripts\python.exe init_db.py
Set-Location ..
```

คำสั่งนี้สร้างตารางและหมวดหมู่ พร้อมนำเข้าสินค้าจาก `hardware_updated.csv` ถ้ามีไฟล์ จากนั้น backend จะเพิ่มคอลัมน์และตารางเพิ่มเติม เช่น ประวัติราคา การตั้งค่า AI และบทสนทนา เมื่อเริ่มทำงาน

`init_db.py` ไม่ได้สร้างบัญชีผู้ดูแลเริ่มต้น สมัครสมาชิกผ่าน `/register` ได้ และให้ผู้ดูแลที่มีอยู่กำหนดสิทธิ์ผ่านหน้าจัดการสมาชิก กรณีฐานข้อมูลใหม่ที่ยังไม่มีผู้ดูแล ต้องกำหนด `users.u_role` เป็น `admin` ให้บัญชีที่ต้องการในฐานข้อมูลโดยตรง

### 4. เปิด backend และ frontend

เปิด PowerShell สองหน้าต่างจากรากโปรเจกต์

หน้าต่างแรก:

```powershell
Set-Location backend
..\venv\Scripts\python.exe -m uvicorn shop_api:app --reload --host 127.0.0.1 --port 3000
```

หน้าต่างที่สอง:

```powershell
npm --prefix It-shop start -- --port 4200
```

- หน้าเว็บ: http://localhost:4200
- API และสถานะพื้นฐาน: http://localhost:3000
- Swagger UI: http://localhost:3000/docs
- OpenAPI schema: http://localhost:3000/openapi.json

หลังติดตั้งครบแล้ว ใช้ `.\run.bat` จากรากโปรเจกต์เพื่อเปิดทั้งสองส่วนได้ โดยสคริปต์นี้ใช้ `venv` ที่รากโปรเจกต์และเปิด backend ที่ `0.0.0.0:3000`

**เมื่อใช้ค่า default ต้องเริ่ม backend จากโฟลเดอร์ `backend`** เพราะ `DATABASE_URL=sqlite:///./shop.db` และ `UPLOAD_ROOT=uploads` อิง working directory สามารถกำหนด absolute paths เพื่อใช้ DB/uploads ที่อื่นได้ แต่ `init_db.py` ยังสร้าง `shop.db` ใน working directory และไม่อ่าน `DATABASE_URL` ต้องตรวจตำแหน่งก่อนรันเสมอ URL ของ backend ใช้ `It-shop/src/environments/environment.ts` สำหรับ development และ `environment.prod.ts` สำหรับ production (same-origin proxy ของ Vercel)

### ทดสอบ startup ด้วย DB ชั่วคราว

จากรากโปรเจกต์ เปิด PowerShell แยกหน้าต่างสำหรับการทดสอบนี้ ตัวแปรมีผลเฉพาะ process นี้ ไม่เขียน `.env` และไม่ใช้ DB จริง:

```powershell
$projectRoot = (Get-Location).Path
$env:PYTHONUTF8 = '1'
$startupDir = Join-Path ([System.IO.Path]::GetTempPath()) ('it-recommend-startup-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $startupDir | Out-Null
$env:JWT_SECRET = & "$projectRoot\venv\Scripts\python.exe" -c "import secrets; print(secrets.token_urlsafe(48))"
$env:AI_KEY_ENCRYPTION_KEY = & "$projectRoot\venv\Scripts\python.exe" -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode('ascii'))"
$env:DATABASE_URL = 'sqlite:///' + (Join-Path $startupDir 'shop.db').Replace('\', '/')
$env:UPLOAD_ROOT = Join-Path $startupDir 'uploads'
$env:REQUIRE_EXISTING_DB = '1'
Set-Location $startupDir
& "$projectRoot\venv\Scripts\python.exe" -B "$projectRoot\backend\init_db.py"
Set-Location "$projectRoot\backend"
& "$projectRoot\venv\Scripts\python.exe" -B -m uvicorn shop_api:app --host 127.0.0.1 --port 3000
```

คำสั่งสร้าง key สองบรรทัดเก็บ stdout ใน environment variables โดยไม่แสดงค่า ห้ามนำค่าตัวแปรออกมาพิมพ์ ตรวจ `http://localhost:3000/health` และหยุดด้วย Ctrl+C จากนั้นปิดหน้าต่างนี้เพื่อทิ้ง environment variables; DB และ uploads ที่สร้างอยู่ใต้ `$startupDir` เท่านั้น หากพอร์ต 3000 ถูกใช้อยู่ เลือกพอร์ตทดสอบอื่นและปรับ URL ตรวจ health ให้ตรงกัน

## Configuration สำหรับตรวจทาน Railway / Vercel

ตรวจจากไฟล์ใน repository และตรวจ hosting แบบ read-only เมื่อ 2 ตุลาคม 2026: Railway service `api` ใน production มี volume `/data`, `DATABASE_URL` ชี้ `/data/shop.db`, `UPLOAD_ROOT=/data/uploads` และ `REQUIRE_EXISTING_DB=1`; JWT/encryption key มีค่าและผ่านการตรวจความยาว/รูปแบบโดยไม่แสดงค่า Vercel project `recommend` ใช้ root `It-shop`, Angular, `npm run build` และ output `dist/lt-shop/browser` ยังไม่ได้ตรวจข้อมูลใน DB, ไฟล์ uploads หรือ bucket จริง และยังไม่มี Supabase variables บน backend ตอนตรวจ:

| หัวข้อ | ตรวจแล้วใน repository | สิ่งที่ต้องยืนยันบน hosting เพิ่มเติม |
| --- | --- | --- |
| Railway startup | `backend/railway.json` ใช้ Railpack, `uvicorn main:app --host 0.0.0.0 --port $PORT`, healthcheck `/`; `backend/main.py` import `shop_api.app` | Root directory เป็น `backend`, start command ที่มีผลจริง, `PORT` และผล healthcheck |
| JWT / encryption | ตรวจความยาว JWT และ Fernet key ที่ import; ไม่มีค่า default ที่ใช้งานได้ | ตั้งทั้งสองใน backend service อย่างถูกต้อง โดยไม่เปิดเผยค่า; encryption key ตรงกับ DB เดิมและคงเดิมทุก restart/replica; JWT แยกจาก provider credentials |
| DB / persistent volume | อ่าน `DATABASE_URL`, default SQLite; `REQUIRE_EXISTING_DB=1` ตรวจไฟล์ก่อนเปิด | SQLite URL ชี้ไฟล์บน volume ที่ mount จริง เช่น `sqlite:////data/shop.db`, ไฟล์มี schema, backup และสิทธิ์เขียน DB/WAL/SHM; repository ไม่ยืนยันว่า volume mount ที่ `/data` อยู่จริง |
| Profile uploads | `UPLOAD_ROOT/profile` เก็บไฟล์บน filesystem และ mount `/uploads`; ไม่อัปโหลดโปรไฟล์ไป S3 | `UPLOAD_ROOT` ชี้ volume เช่น `/data/uploads`, ไฟล์เก่ายังอยู่และเขียนได้ รวมทั้งเข้าถึง `/uploads/profile/...` หลัง restart |
| Product images / S3 | `product_image_cache.py` ใช้ `IMAGE_S3_ENDPOINT`, `IMAGE_S3_BUCKET`, `IMAGE_S3_ACCESS_KEY_ID`, `IMAGE_S3_SECRET_ACCESS_KEY`; ต้องครบจึงใช้ bucket; endpoint ต้อง HTTPS, `IMAGE_S3_REGION` default `auto`, `IMAGE_S3_URL_STYLE` default `virtual` (รองรับ `path`) | ค่าครบ, private bucket, สิทธิ์อ่าน/เขียน/สร้าง signed URLs และรูปที่ cache อยู่จริง; ทดสอบ proxy และ signed redirect ผ่าน Vercel โดยไม่เผย credentials; S3 ไม่เก็บ DB หรือ profile uploads |
| S3 fallback | `/api/image-proxy` stream รูปจากร้านเมื่อไม่ได้ตั้ง bucket โดยไม่เขียน disk; `/api/cached-image/{digest}` ต้องใช้ bucket | ตั้ง bucket ตามระบบ production ที่ตั้งใจใช้ และยืนยันรูปต้นทาง/ภาพสำรอง; local helper cache ไม่ใช่ persistent storage ของ endpoint นี้ |
| Vercel | `It-shop/vercel.json` build Angular, output `dist/lt-shop/browser`, rewrite `/api` และ `/uploads` ไป Railway ก่อน SPA fallback; production `apiUrl=''` | Root directory เป็น `It-shop`, build/output/rewrites ที่ deploy จริงตรงไฟล์, ปลายทาง Railway ถูกต้อง และ deep links ทำงาน; JWT/encryption/S3 secrets ต้องอยู่ backend service |
| CORS / AI | `CORS_ORIGINS` default localhost; provider key/model เป็นทางเลือกสำหรับ startup | Origins ของ frontend เมื่อเรียกข้าม origin, provider/model ที่บัญชีใช้งานได้ และค่าฝั่ง server ที่ตั้งใจใช้ |

ค่าพาธในตารางเป็นตัวอย่างสำหรับการตรวจยืนยัน ไม่ใช่หลักฐานว่ามี volume หรือ variables เหล่านั้นบน Railway/Vercel แล้ว

Backend รองรับ access logging ไป Supabase แยกจาก SQLite โดยตั้ง `SUPABASE_URL` และ `SUPABASE_SERVICE_KEY` เฉพาะ backend service เมื่อไม่ได้ตั้งค่า ระบบยังทำงานตามปกติ ดู migration, รายการ routes, SQL ตรวจสิทธิ์/ดู log และขั้นตอนทดสอบจริงใน [เอกสาร access logging](docs/access-logging/README.md) ห้ามนำ service key ไปไว้ใน Angular หรือ Vercel

สำหรับ IP audit ผ่าน Vercel ให้ตั้ง `ACCESS_LOG_TRUSTED_PROXY_CIDRS` เฉพาะ Railway peer ที่ตรวจจริง และ `ACCESS_LOG_PROXY_SECRET` เป็น random secret แยกต่างหากอย่างน้อย 32 ตัวอักษรที่ตรงกันบน Railway backend กับ Vercel server routing เท่านั้น ห้ามใส่ใน Angular หรือ Git `It-shop/vercel.json` ใส่ secret request header ด้วย transform ก่อน rewrite API; backend เลือก `x-vercel-forwarded-for` เฉพาะเมื่อยืนยัน proxy แล้ว Railway start command ใช้ `--no-proxy-headers` เพื่อรักษา socket peer สำหรับตรวจ trust เมื่อเริ่มเองและเปิด proxy trust ต้องใช้ flag นี้ด้วย หาก env trust ไม่ครบจะใช้ peer เป็น fallback; country เป็น null หาก proxy ไม่ส่งมา

## หน้าที่มีใน Frontend

| เส้นทาง | การใช้งาน | สิทธิ์ |
| --- | --- | --- |
| `/` | หน้าแรก | สาธารณะ |
| `/login`, `/register` | เข้าสู่ระบบและสมัครสมาชิก | สาธารณะ |
| `/ai-recommend` | AI และการตั้งค่าบทสนทนา | สมาชิก |
| `/products`, `/category/:type` | ค้นหาและดูสินค้าตามหมวด | สมาชิก |
| `/product/:id` | รายละเอียดและเปรียบเทียบราคา | สมาชิก |
| `/pc-builder` | จัดสเปกด้วยตนเอง | สมาชิก |
| `/history` | ประวัติสเปก | สมาชิก |
| `/profile` | โปรไฟล์ | สมาชิก |
| `/admin/products` | จัดการสินค้า | ผู้ดูแล |
| `/admin/users` | จัดการสมาชิก | ผู้ดูแล |

Backend ยังมี API โปรโมชั่น แต่ปิด API คำสั่งซื้อแล้ว; router ของ `It-shop` ไม่มีหน้า `/cart`, `/checkout` หรือ `/admin/orders` ปุ่มเข้าสู่ feature routes จะพาไปหน้า login พร้อม redirect กลับ ส่วนปุ่มเลือกหมวดสินค้าบนหน้าแรกต้องเข้าสู่ระบบก่อนเปลี่ยนหมวด

## API หลัก

รายละเอียด request/response ดูจาก Swagger UI ของ backend ที่กำลังรัน Endpoint ที่ต้องยืนยันตัวตนใช้ `Authorization: Bearer <token>`

| กลุ่ม | Endpoint |
| --- | --- |
| Authentication | `POST /api/register`, `POST /api/login` |
| โปรไฟล์ | `GET/PUT /api/profile`, `PUT /api/profile/password`, `POST /api/profile/upload-image` |
| สินค้า | `GET /api/products`, `GET /api/products/{product_id}`, `GET /api/products/{product_id}/compare` |
| จัดการสินค้า | `POST /api/products`, `PUT/DELETE /api/products/{product_id}` |
| หมวดหมู่และราคา | `GET /api/categories`, `GET /api/price-history/{product_id}` |
| AI | `POST /api/ai/recommend`, `GET/PUT /api/ai/settings` |
| บทสนทนา AI | `GET/POST /api/ai/sessions`, `GET/PUT/DELETE /api/ai/sessions/{session_id}` |
| ความเข้ากันได้ | `POST /api/compat/check`, `POST /api/compatibility/check`, `POST /api/compatibility/check-parts` |
| ประวัติสเปก | `GET/POST /api/spec-history`, `DELETE /api/spec-history/{id}`, `GET /api/spec-history/all` |
| ผู้ดูแลสมาชิก | `GET /api/admin/users`, `GET/PUT/DELETE /api/admin/users/{uid}`, `PUT /api/admin/users/{uid}/role` |
| Scraper | `POST /api/scrape` (ผู้ดูแล), `GET /api/scrape/status` |
| โปรโมชั่น | `GET/POST /api/promotions`, `PUT/DELETE /api/promotions/{promo_id}` |

`GET /api/products` รองรับ `category`, `cid`, `search`, `name`, `store`, `brand`, `page` และ `limit` ดูตัวกรองที่ใช้ได้จาก `GET /api/products/filters` การอ่าน catalog และรูปบนหน้าแรกเป็น public API; `/api/ai/recommend` ทุกโหมดและ API ตรวจสเปกทั้งสามเส้นทางบังคับ JWT และตอบ HTTP 401 เมื่อไม่มี token หรือ token ใช้ไม่ได้

## การทำงานของ AI และการตรวจสเปก

`recommender.py` วิเคราะห์งบและลักษณะงาน ดึงรายการสินค้าจากฐานข้อมูลเป็นตัวเลือก แล้วให้โมเดลช่วยเลือกและอธิบายผล ระบบนำผลกลับมาจับคู่กับสินค้า คำนวณราคา และตรวจสอบด้วย `compat_engine.py` ร่วมกับ `spec_parser.py` และความรู้ใน `backend/rules/`

กฎตรวจสอบครอบคลุม socket CPU/เมนบอร์ด, DDR ของ RAM, กำลังไฟ PSU, เงื่อนไข GPU ระดับสูงและหัวต่อไฟ, กำลังระบายความร้อน, ขนาดเมนบอร์ดกับเคส และงบประมาณ โดยเกณฑ์ PSU พิจารณาทั้งค่าที่ผู้ผลิต GPU แนะนำและค่าประมาณ `(CPU + GPU + 80W) × 1.25` ผลลัพธ์อาศัยข้อมูลสเปกที่มีและอาจยังยืนยันไม่ได้เมื่อข้อมูลไม่ครบ

บทสนทนาของสมาชิกผูกกับผู้ใช้และตรวจสิทธิ์ก่อนเข้าถึง สามารถสร้าง เปิด เปลี่ยนชื่อ และลบได้ รายการบทสนทนาคืนล่าสุดไม่เกิน 100 รายการ migration เปลี่ยนค่า provider เดิม `zen` เป็น Google พร้อมล้าง key และ custom model โดยยังอ่านบทสนทนาเก่าได้ ส่วน OpenCode Zen ปัจจุบันใช้ provider ID `opencode_zen`

## อัปเดตข้อมูลสินค้า

ติดตั้ง Playwright และ Chromium ตามขั้นตอนด้านบน แล้วรันจาก `backend`:

```powershell
# ดึง listing จากทั้ง 3 ร้าน จำกัดจำนวนหน้าต่อหมวด
..\venv\Scripts\python.exe full_scraper.py --stores all --pages 3

# ดึงรายละเอียดสินค้าจากร้านที่เลือกด้วย
..\venv\Scripts\python.exe full_scraper.py --stores jib ihavecpu --pages 3 --details

# เติมรายละเอียดที่ขาดจาก URL ที่มีในฐานข้อมูล
..\venv\Scripts\python.exe full_scraper.py --backfill-only

# ดึงทุกหน้าของ 12 หมวด iHaveCPU พร้อมหน้ารายละเอียดสินค้า (ไม่แตะอีก 2 ร้าน)
..\venv\Scripts\python.exe full_scraper.py --ihavecpu-full

# ดึงเฉพาะเก้าอี้และโต๊ะเกมมิ่งจาก iHaveCPU
..\venv\Scripts\python.exe full_scraper.py --ihavecpu-full --ihavecpu-categories gaming-chair gaming-desk

# ดึง Advice ทุกหมวดที่เลือก (รันซ้ำจะต่อจาก checkpoint)
..\venv\Scripts\python.exe advice_full_scraper.py --interval 1.5

# รีเฟรชรายการ Advice จากหน้าแรก โดยเก็บรายละเอียดเดิมที่ยังใช้ได้
..\venv\Scripts\python.exe advice_full_scraper.py --refresh-listings --interval 1.5

# เติมรูปหลักของทั้งสามร้านลง private image bucket (รันซ้ำจะข้ามไฟล์ที่มีแล้ว)
..\venv\Scripts\python.exe prefetch_product_images.py
```

คำสั่งเหล่านี้เขียนข้อมูลลง `backend/shop.db` ควรสำรองฐานข้อมูลก่อนรันงานปรับข้อมูลจำนวนมาก จำนวนสินค้าที่ดึงได้ขึ้นอยู่กับหน้าเว็บต้นทาง การแบ่งหน้า และการตอบสนองของแต่ละร้าน

โหมด `--ihavecpu-full` ไล่หน้าจนจำนวนรหัสสินค้าไม่ซ้ำครบตามยอดที่เว็บรายงาน และเก็บชื่อ ราคา URL รูปหลัก และรายละเอียดที่อ่านได้จากหน้าสินค้าลง `products` พร้อมบัญชีตรวจสอบรายหมวดในตาราง `ihavecpu_scrape_inventory` หากต้นทางให้รายละเอียดเป็นภาพอย่างเดียว ระบบจะเก็บ URL ภาพรายละเอียดแทนข้อความที่ไม่มีจริง ผลการดึงหน้าสินค้ามี checkpoint สำหรับรันต่อได้

### Full scrape JIB (8 กลุ่ม รวม Gaming Chair / Gaming Desk)

```powershell
cd backend
..\venv\Scripts\python.exe jib_full_scraper.py

# หากเว็บตอบกลับชั่วคราวผิดปกติ ให้รันต่อจากข้อมูลที่บันทึกไว้
..\venv\Scripts\python.exe jib_full_scraper.py --details-only

# ตรวจรายการสินค้าอย่างเดียว โดยยังไม่เปิดหน้ารายละเอียด
..\venv\Scripts\python.exe jib_full_scraper.py --list-only

# อัปเดตเฉพาะเก้าอี้และโต๊ะเกมมิ่ง
..\venv\Scripts\python.exe jib_full_scraper.py --categories 1263 1466 --skip-compat-training
```

ครอบคลุมหมวดค้นหา JIB รหัส 42, 58, 60, 1419, 1420, 1393, 1263 และ 1466 โดยแยกสินค้าเป็น CPU, Mainboard, GPU, RAM, SSD, HDD, PSU, Case, Monitor, Mouse, Keyboard, Keypad, Graphic Tablet, Headset, Air/Liquid Cooler, Gaming Chair, Gaming Desk และหมวดอุปกรณ์เสริมที่เกี่ยวข้อง สองหมวดเฟอร์นิเจอร์ใช้ผลค้นหาที่มี pagination และรับเฉพาะชื่อที่ขึ้นต้นด้วย `GAMING CHAIR` หรือ `GAMING DESK` เพื่อไม่ปนสินค้าประเภทอื่น ตัวกรองตัดเครื่องอ่านแผ่น ซีดี/ดีวีดี การ์ดเสียง NAS และ RAM สำหรับ NAS แฟลชไดรฟ์ เมมโมรีการ์ด เครื่องอ่านการ์ด สวิตช์คีย์บอร์ดแยก ที่รองข้อมือ top plate แผ่นรองเมาส์ หูฟัง true wireless คาราโอเกะ สปีกเกอร์โฟน หัวแปลง ขาตั้งหูฟัง และพัดลมเคสตามที่กำหนด

หากฐานข้อมูลอยู่คนละที่กับโฟลเดอร์ `backend` (เช่น Railway ใช้ `/data/shop.db`) ให้ระบุ `--db-path /data/shop.db` หลังสำรองไฟล์นั้นแล้ว สคริปต์จะปฏิเสธพาธที่ไม่มีไฟล์อยู่ก่อน เพื่อไม่สร้างฐานข้อมูลว่างผิดตำแหน่ง

รายการและสถานะรายละเอียดอยู่ใน `jib_scrape_inventory`; จำนวนหน้าจากการรันล่าสุดอยู่ใน `jib_scrape_category_audit` สคริปต์จำกัดอัตราคำขอและใช้ checkpoint รายหน้าสินค้า รูปเก็บเป็น URL ภาพของ JIB ไม่ได้ดาวน์โหลดไฟล์ภาพ หากเว็บแสดงราคา `N/A` จะเพิ่มสินค้าเข้ารายการด้วยราคา 0 เพื่อแสดง “สอบถามราคา” โดยไม่เดาราคา และจะไม่นำสินค้านั้นเข้าตัวเลือกจัดสเปกจนกว่าจะมีราคาจริง

Advice เก็บรายละเอียดสินค้า URL ภาพหลักและภาพทั้งหมด รายการคุณสมบัติ และลิงก์ต้นทางไว้ใน `advice_scrape_inventory`; ดูคำอธิบายเพิ่มเติมใน [ADVICE_FULL_SCRAPE.md](backend/ADVICE_FULL_SCRAPE.md) ส่วนรายการ JIB ที่ไม่อยู่ในหน้าร้านรอบล่าสุดยังคงอยู่ใน inventory เป็นประวัติ ไม่ควรนำจำนวนสะสมมานับเป็นจำนวนสินค้าปัจจุบัน

Production ใช้ `/api/image-proxy` ร่วมกับ private image bucket; CDN ของบางร้านอาจปฏิเสธ IP ของ Railway แม้ URL รูปยังเปิดได้จากเครื่องอื่น จึงต้องเติมรูปลง bucket หลังการอัปเดต catalog ไม่ควรพึ่ง proxy ดึงรูปที่ยังไม่แคชได้เสมอ หน้าเว็บจะลอง URL รูปของร้านโดยตรงหาก proxy ล้มเหลว แล้วใช้ภาพสำรองในเว็บหากทั้งสองทางใช้ไม่ได้

เมื่อต้องการเติมรูปตามข้อมูล production ปัจจุบันจากเครื่องที่เข้าถึง CDN ได้ ให้รันจาก `backend` (ต้องมี `boto3` จาก `requirements.txt`):

```powershell
railway run --service api --environment production -- python prefetch_product_images.py --api-base https://api-production-8990.up.railway.app --categories GPU --stores advice jib ihavecpu
```

คำสั่งนี้อ่านสินค้าจาก API ที่ใช้งานจริงและข้ามรูปที่อยู่ใน bucket แล้ว หลัง scrape/นำเข้าสินค้าใหม่ให้รันซ้ำตามหมวดที่เปลี่ยน ไม่ควรใส่ค่า `IMAGE_S3_*` หรือ API key ลงในคำสั่งหรือ repository

หลังเติมรายละเอียด สคริปต์ปรับข้อมูลสำหรับตรวจความเข้ากันได้อัตโนมัติ เว้นแต่ใช้ `--skip-compat-training`

เมื่อใช้ `--details` หรือ `--backfill-only` scraper จะเรียก `train_compat_knowledge.py --apply` ต่อเพื่อปรับข้อมูลเป็นข้อเท็จจริงสำหรับตรวจสเปก เว้นแต่ระบุ `--skip-compat-training` ชื่อสคริปต์นี้หมายถึงการปรับข้อมูลความรู้ในฐานข้อมูล ไม่ใช่การฝึกน้ำหนักโมเดล AI

## คำสั่งตรวจสอบสำหรับนักพัฒนา

รันจากรากโปรเจกต์:

```powershell
# ตรวจสอบการ build ของ frontend
npm --prefix It-shop run build -- --configuration development

# ทดสอบ Angular
npm --prefix It-shop test -- --watch=false

# ทดสอบ AI settings, sessions และการแยกข้อมูลผู้ใช้
.\venv\Scripts\python.exe -B backend\test_ai_sessions.py

# ตรวจ isolation ของชุดทดสอบและ recommendation/compatibility regressions
.\venv\Scripts\python.exe -B backend\test_db_isolation_audit.py
.\venv\Scripts\python.exe -B backend\test_recommendation_compat_regression.py

# ทดสอบกฎกำลังไฟและความรู้สำหรับคำแนะนำ
.\venv\Scripts\python.exe -B backend\test_power_compatibility.py
.\venv\Scripts\python.exe -B backend\test_recommender_knowledge.py

# ทดสอบการจับคู่สินค้าและข้อมูลต้นทางของ scraper
.\venv\Scripts\python.exe -B backend\test_product_matching.py
.\venv\Scripts\python.exe -B backend\test_scraper_source_data.py
```

ชุดทดสอบ AI sessions ใช้ฐานข้อมูลชั่วคราวและ mock การเรียกผู้ให้บริการ ส่วนไฟล์ `test_*.py` อื่นบางไฟล์เป็นสคริปต์ตรวจเว็บจริง จึงควรอ่านก่อนรัน ไม่ควรรันทุกไฟล์รวมกันโดยสมมติว่าเป็น unit test ทั้งหมด

ก่อน commit ต้องรวม `backend/test_db_isolation_audit.py` และ `backend/test_recommendation_compat_regression.py` ด้วย ตรวจว่าไม่ถูก ignore ด้วย `git check-ignore -v -- backend/test_db_isolation_audit.py backend/test_recommendation_compat_regression.py` (ไม่มี output และ exit code 1 หมายถึงไม่ถูก ignore) และตรวจ staged paths ด้วย `git diff --cached --name-only` เอกสารที่แก้เพียงอย่างเดียวไม่จำเป็นต้องรันชุดใหญ่ซ้ำ แต่การแก้ authentication ต้องทดสอบส่วนที่ได้รับผลกระทบ

## แก้ปัญหาเบื้องต้น

| อาการ | จุดที่ควรตรวจ |
| --- | --- |
| `No module named dotenv` | ติดตั้ง `python-dotenv` ด้วย Python ใน `venv` |
| Startup แจ้ง `JWT_SECRET` หรือ `AI_KEY_ENCRYPTION_KEY` | ตั้งทั้งสองตามขั้นตอนข้างต้น; encryption key ต้องเป็น Fernet key และใช้ค่าเดิมของ DB ที่มีอยู่ |
| Playwright หา browser ไม่พบ | รัน `python -m playwright install chromium` ด้วย Python ใน `venv` |
| `no such table` หรือสินค้าไม่ตรงกับที่เคยมี | ตรวจว่าเปิด backend จาก `backend/` และใช้ฐานข้อมูลถูกไฟล์; ฐานข้อมูลใหม่ต้องรัน `init_db.py` ก่อน |
| Frontend ติดต่อ API ไม่ได้ | ตรวจพอร์ต 3000 และ `baseUrl` ในทั้งสอง service |
| AI ตอบ HTTP 400 เรื่อง key | ตั้ง key ของ provider ที่เลือกในหน้า AI หรือ `.env` |
| AI แจ้ง provider unavailable หรือ timeout | ตรวจ model ID, API key และโควตาของผู้ให้บริการ; บางโหมดมี deterministic fallback และ timeout อาจตอบ HTTP 504 |
| เข้า `/admin/products` หรือ `/admin/users` ไม่ได้ | ตรวจ role ของบัญชีและเข้าสู่ระบบใหม่หลังเปลี่ยนสิทธิ์ |
