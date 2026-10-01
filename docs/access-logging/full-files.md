# Access logging ? full source files

Snapshot: 2026-10-02 (Asia/Bangkok). Complete file contents, including prior edits in shared files.
The generated snapshot itself is excluded to avoid recursive inclusion. Real .env files and credentials are excluded.

## .gitignore

SHA-256 of source file: `57416c1047274182c31f8aeaebf045b62ed480814a8e002c3561c05f24cf5efd`

````text
# Secrets
.env
*.env.local

# Python
__pycache__/
venv/
*.pyc

# Node
node_modules/
dist/
.angular/

# Databases (local build artifacts)
*.db
*.db-shm
*.db-wal
*.db-journal
docs/qa/round4/*.db
docs/qa/round4/*.db-shm
docs/qa/round4/*.db-wal

# Logs / temp
*.log
advice_html.txt
uploads/
backend/product_image_cache/
backend/.deploy/

.vercel
.env*
!.env.example

# Local one-off migration/deployment helpers (not application code)
backend/_fix_shop_api.py
backend/_inject_recommender.py
backend/_patch_ask_mode.py
backend/_patch_html.py
backend/set_railway_secrets.py
backend/snapshot_shop_db.py
````

## .env.example

SHA-256 of source file: `d03bedd5a70bf6a41b2f315552768655845ad5957077d85f4f244d76e92954df`

````text
# Backend only. Copy to .env locally and fill privately; never commit real values.
JWT_SECRET=
AI_KEY_ENCRYPTION_KEY=

# Optional; unset values use shop_api.py defaults.
# DATABASE_URL=sqlite:///./shop.db
# REQUIRE_EXISTING_DB=1
# UPLOAD_ROOT=uploads
# CORS_ORIGINS=http://localhost:4200

# Access logs only: configure these in the Railway backend service.
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
````

## README.md

SHA-256 of source file: `ed8898909306fd93505942e53ae9c68c321af3acb6bb54fcc30e31a96da39fef`

````markdown
﻿# IT-RECOMMEND — ระบบแนะนำและจัดสเปกคอมพิวเตอร์

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
````

## backend/access_log.py

SHA-256 of source file: `47c423777855cb3630f64a4dc9bdb85977515b1101f5780a407c83faa31b17cf`

````python
"""Best-effort security access logs; no SQLite writes or request content capture."""

import asyncio
from contextlib import asynccontextmanager
import os
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
import httpx


LOG_PREFIXES = (
    "/admin", "/api/admin", "/login", "/api/login", "/register", "/api/register",
    "/auth", "/api/auth", "/api/profile", "/api/ai/settings", "/api/ai/sessions",
    "/api/ai/recommend", "/api/spec-history", "/api/scrape",
)
ADMIN_WRITE_PREFIXES = ("/api/products", "/api/promotions")
MAX_PENDING_LOGS = 256


def should_log(method: str, path: str) -> bool:
    if path.startswith(LOG_PREFIXES):
        return True
    return method in {"POST", "PUT", "PATCH", "DELETE"} and any(
        path == prefix or path.startswith(prefix + "/") for prefix in ADMIN_WRITE_PREFIXES
    )


def log_payload(request: Request, status: int) -> dict:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    ip = forwarded or request.headers.get("x-real-ip", "").strip()
    if not ip:
        ip = request.client.host if request.client else None
    user_id = getattr(request.state, "user_id", None)
    return {
        "method": request.method,
        "path": request.url.path[:300],
        "status": status,
        "ip": ip,
        "country": request.headers.get("x-vercel-ip-country") or None,
        "user_agent": request.headers.get("user-agent", "")[:300],
        "user_id": str(user_id) if user_id is not None else None,
    }


class AccessLogger:
    def __init__(self):
        self.client: httpx.AsyncClient | None = None
        self.url = ""
        self.pending: set[asyncio.Task] = set()

    def start(self):
        try:
            base = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
            key = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
            parsed = urlsplit(base)
            if (not key or parsed.scheme != "https" or not parsed.hostname
                    or parsed.username or parsed.password or parsed.query or parsed.fragment
                    or parsed.path):
                return
            self.client = httpx.AsyncClient(timeout=5.0, follow_redirects=False, headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            })
            self.url = base + "/rest/v1/access_logs"
        except Exception:
            self.client = None

    async def send(self, payload: dict):
        try:
            if self.client is not None:
                response = await self.client.post(self.url, json=payload)
                response.raise_for_status()
        except Exception:
            # Never print Supabase errors/headers: they may contain credentials.
            pass

    def enqueue(self, request: Request, status: int):
        try:
            if self.client is None or len(self.pending) >= MAX_PENDING_LOGS:
                return
            task = asyncio.create_task(self.send(log_payload(request, status)))
            self.pending.add(task)
            task.add_done_callback(self.pending.discard)
        except Exception:
            pass

    async def close(self):
        try:
            if self.pending:
                _, unfinished = await asyncio.wait(tuple(self.pending), timeout=5.0)
                for task in unfinished:
                    task.cancel()
                if unfinished:
                    await asyncio.gather(*unfinished, return_exceptions=True)
            if self.client is not None:
                await self.client.aclose()
        except Exception:
            pass
        finally:
            self.client = None
            self.pending.clear()


def install_access_logging(app: FastAPI):
    if getattr(app.state, "access_logger", None) is not None:
        return
    logger = AccessLogger()
    app.state.access_logger = logger
    previous_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application):
        async with previous_lifespan(application) as state:
            logger.start()
            try:
                yield state
            finally:
                await logger.close()

    app.router.lifespan_context = lifespan

    @app.middleware("http")
    async def access_logging(request: Request, call_next):
        if not should_log(request.method, request.url.path):
            return await call_next(request)
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            # No await here: the API response does not wait for Supabase.
            logger.enqueue(request, status)
````

## backend/shop_api.py

SHA-256 of source file: `501ff9d0cf2e332c4c04768cdcd0c80362c0be80fde1fb47abd0bd4f40cb742e`

````python
"""
IT-RECOMMEND Shop API - FastAPI backend
รัน: uvicorn shop_api:app --reload --port 3000
"""
import os, re, json, shutil, asyncio, httpx, logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, List, Literal
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from fastapi import FastAPI, HTTPException, Depends, Request, status, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, ForeignKey, func, text, or_, and_
from sqlalchemy.orm import sessionmaker, Session, declarative_base, relationship
import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────
# Config
# ─────────────────────────────────────────
def load_jwt_secret() -> str:
    """Load a dedicated HMAC key and reject unsafe deployment settings."""
    secret = os.getenv("JWT_SECRET", "")
    if len(secret.encode("utf-8")) < 32:
        raise RuntimeError(
            "JWT_SECRET must be set to a random value of at least 32 bytes; "
            "run backend/rotate_jwt_secret.py --apply during an announced deploy window"
        )
    provider_keys = {
        os.getenv("GOOGLE_API_KEY", ""), os.getenv("GEMINI_API_KEY", ""),
        os.getenv("OPENAI_API_KEY", ""), os.getenv("OPENROUTER_API_KEY", ""),
        os.getenv("OPENCODE_ZEN_API_KEY", ""),
    }
    provider_keys.discard("")
    if secret in provider_keys:
        raise RuntimeError("JWT_SECRET must not reuse an AI provider credential")
    return secret


def load_ai_key_cipher() -> Fernet:
    """Load the symmetric key used to encrypt user AI provider keys at rest.

    Generate one with:
      python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    and put it in .env as AI_KEY_ENCRYPTION_KEY. Rotating this key makes every
    previously-saved AI key unreadable, so treat it like JWT_SECRET.
    """
    raw = os.getenv("AI_KEY_ENCRYPTION_KEY", "")
    if not raw:
        raise RuntimeError(
            "AI_KEY_ENCRYPTION_KEY must be set (see load_ai_key_cipher docstring "
            "for how to generate one) before saving or reading user AI keys"
        )
    try:
        return Fernet(raw.encode("utf-8"))
    except Exception as e:
        raise RuntimeError(f"AI_KEY_ENCRYPTION_KEY is not a valid Fernet key: {e}")


AI_KEY_CIPHER = load_ai_key_cipher()


def encrypt_ai_key(plain: str) -> str:
    """Encrypt a user-supplied AI provider key before it touches SQLite."""
    if not plain:
        return ""
    return AI_KEY_CIPHER.encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_ai_key(stored: str) -> str:
    """Decrypt a stored AI key. Tolerates rows written before encryption was
    added (plain OpenAI/Google/OpenRouter keys never look like a Fernet token,
    so a failed decrypt is treated as legacy plaintext instead of an error)."""
    if not stored:
        return ""
    try:
        return AI_KEY_CIPHER.decrypt(stored.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        return stored


SECRET_KEY = load_jwt_secret()
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 72
DB_URL = os.getenv("DATABASE_URL", "sqlite:///./shop.db")
if os.getenv("REQUIRE_EXISTING_DB") == "1" and DB_URL.startswith("sqlite:///"):
    db_path = Path(DB_URL.removeprefix("sqlite:///"))
    if not db_path.is_file():
        raise RuntimeError(f"Database file does not exist: {db_path}")

UPLOAD_ROOT = Path(os.getenv("UPLOAD_ROOT", "uploads"))
UPLOAD_DIR = UPLOAD_ROOT / "profile"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


engine = create_engine(DB_URL, connect_args={"check_same_thread": False, "timeout": 60})
with engine.connect() as _c:
    try:
        _c.execute(text("PRAGMA journal_mode=WAL;"))
        _c.commit()
    except Exception:
        pass
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
security = HTTPBearer(auto_error=False)

# Comma-separated list in .env, e.g. CORS_ORIGINS=http://localhost:4200,https://it-recommend.example.com
ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:4200").split(",") if o.strip()
]

app = FastAPI(title="IT-RECOMMEND Shop API", version="3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_ROOT)), name="uploads")

# ── Rate limiting (per client IP) ───────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

from access_log import install_access_logging
install_access_logging(app)

# ─────────────────────────────────────────
# Models
# ─────────────────────────────────────────
class User(Base):
    __tablename__ = "users"
    uid          = Column(String, primary_key=True, index=True)
    u_name       = Column(String, unique=True, nullable=False)
    u_email      = Column(String, unique=True, nullable=False)
    u_password   = Column(String, nullable=False)
    u_phone      = Column(String, default="")
    u_address    = Column(Text, default="")
    u_image      = Column(String, default="")
    u_role       = Column(String, default="customer")
    dob          = Column(String, default="")
    u_created_at = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    u_updated_at = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    u_last_login = Column(String, nullable=True)
    token_version = Column(Integer, nullable=False, default=0)
    orders       = relationship("Order", back_populates="user")

class Category(Base):
    __tablename__ = "categories"
    cid           = Column(String, primary_key=True)
    c_name        = Column(String, unique=True, nullable=False)
    c_description = Column(Text, default="")

class Product(Base):
    __tablename__ = "products"
    product_id      = Column(String, primary_key=True, index=True)
    p_name          = Column(String, nullable=False)
    p_description   = Column(Text, default="")
    p_price         = Column(Float, nullable=False, default=0)
    price_advice    = Column(Integer, default=0)
    price_jib       = Column(Integer, default=0)
    price_ihavecpu  = Column(Integer, default=0)
    url_advice      = Column(String, default="")   # ลิงก์ตรงสินค้า Advice
    url_jib         = Column(String, default="")   # ลิงก์ตรงสินค้า JIB
    url_ihavecpu    = Column(String, default="")   # ลิงก์ตรงสินค้า iHaveCPU
    desc_advice     = Column(Text, default="")     # รายละเอียดจาก Advice
    desc_jib        = Column(Text, default="")     # รายละเอียดจาก JIB
    desc_ihavecpu   = Column(Text, default="")     # รายละเอียดจาก iHaveCPU
    p_stock         = Column(Integer, default=0)
    cid             = Column(String, default="")
    category        = Column(String, default="")
    img_url         = Column(String, default="")
    specs           = Column(Text, default="")
    created_at      = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

class Promotion(Base):
    __tablename__ = "promotions"
    promo_id          = Column(Integer, primary_key=True, autoincrement=True)
    promo_name        = Column(String, nullable=False)
    promo_description = Column(Text, default="")
    promo_img         = Column(String, default="")
    discount_type     = Column(String, default="percent")
    discount_value    = Column(Float, default=0)
    promo_stock       = Column(Integer, default=0)
    promo_price       = Column(Float, default=0)
    start_date        = Column(String)
    end_date          = Column(String)
    status            = Column(String, default="active")

class Order(Base):
    __tablename__ = "orders"
    order_id       = Column(Integer, primary_key=True, autoincrement=True)
    uid            = Column(String, ForeignKey("users.uid"), nullable=True)
    customer_name  = Column(String, default="")
    phone          = Column(String, default="")
    address        = Column(Text, default="")
    payment_method = Column(String, default="cod")
    total_price    = Column(Float, default=0)
    total_amount   = Column(Float, default=0)
    o_status       = Column(String, default="pending")
    order_date     = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    user           = relationship("User", back_populates="orders")
    items          = relationship("OrderItem", back_populates="order")

class OrderItem(Base):
    __tablename__ = "order_items"
    order_item_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id      = Column(Integer, ForeignKey("orders.order_id"))
    product_id    = Column(String, default="")
    p_name        = Column(String, default="")
    oi_quantity   = Column(Integer, default=1)
    oi_price      = Column(Float, default=0)
    order         = relationship("Order", back_populates="items")

class SpecHistory(Base):
    __tablename__ = "spec_history"
    id           = Column(Integer, primary_key=True, autoincrement=True)
    uid          = Column(String, default="", index=True)
    email        = Column(String, default="", index=True)
    username     = Column(String, default="")
    type         = Column(String, default="ai")
    mode         = Column(String, default="recommend")
    title        = Column(String, default="")
    inputSummary = Column(Text, default="")
    result_data  = Column(Text, default="{}")
    createdAt    = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

class UserAiSettings(Base):
    """Per-user AI provider configuration (API keys, model choice) linked to user and email."""
    __tablename__ = "user_ai_settings"
    uid          = Column(String, ForeignKey("users.uid"), primary_key=True, index=True)  # FK → users.uid
    email        = Column(String, default="", index=True)
    provider     = Column(String, default="google")   # google | openai | openrouter | opencode_zen
    model        = Column(String, default="gemini-3-flash-preview")
    api_key      = Column(Text, default="")        # Fernet-encrypted at rest (S02)
    custom_model = Column(String, default="")      # user-typed custom model id
    updated_at   = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

class AiChatSession(Base):
    """One chat session per conversation thread linked to user and email."""
    __tablename__ = "ai_chat_sessions"
    id         = Column(Integer, primary_key=True, autoincrement=True)
    uid        = Column(String, ForeignKey("users.uid"), index=True, nullable=False)
    email      = Column(String, index=True, default="")
    title      = Column(String, default="New Chat")
    mode       = Column(String, default="recommend")  # recommend | compare | compat
    provider   = Column(String, default="google")
    model      = Column(String, default="")
    messages   = Column(Text, default="[]")  # JSON array of {role, content, ts}
    created_at = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    updated_at = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

# ─────────────────────────────────────────
# DB Migration – เพิ่ม columns ใหม่ถ้ายังไม่มี
# ─────────────────────────────────────────
def run_migrations(db_engine):
    with db_engine.connect() as conn:
        # เพิ่ม url + desc columns ใน products
        for col, defn in [
            ("url_advice",    "TEXT DEFAULT ''"),
            ("url_jib",       "TEXT DEFAULT ''"),
            ("url_ihavecpu",  "TEXT DEFAULT ''"),
            ("desc_advice",   "TEXT DEFAULT ''"),
            ("desc_jib",      "TEXT DEFAULT ''"),
            ("desc_ihavecpu", "TEXT DEFAULT ''"),
            ("updated_at",    "TEXT DEFAULT ''"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE products ADD COLUMN {col} {defn}"))
                conn.commit()
                print(f"[Migration] Added column products.{col}")
            except Exception:
                pass  # column มีอยู่แล้ว

        # Price history table (freshness / trend)
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id  TEXT NOT NULL,
                    store       TEXT NOT NULL,
                    price       REAL NOT NULL,
                    captured_at TEXT NOT NULL
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ph_product ON price_history(product_id, captured_at)"))
            conn.commit()
        except Exception as e:
            print(f"[Migration Warning] price_history: {e}")

        # AI settings per user
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_ai_settings (
                    uid          TEXT PRIMARY KEY REFERENCES users(uid),
                    email        TEXT DEFAULT '',
                    provider     TEXT DEFAULT 'google',
                    model        TEXT DEFAULT 'gemini-3-flash-preview',
                    api_key      TEXT DEFAULT '',
                    custom_model TEXT DEFAULT '',
                    updated_at   TEXT DEFAULT ''
                )
            """))
            conn.commit()
        except Exception as e:
            print(f"[Migration Warning] user_ai_settings: {e}")

        # AI chat sessions
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS ai_chat_sessions (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    uid        TEXT NOT NULL REFERENCES users(uid),
                    email      TEXT DEFAULT '',
                    title      TEXT DEFAULT 'New Chat',
                    mode       TEXT DEFAULT 'recommend',
                    provider   TEXT DEFAULT 'google',
                    model      TEXT DEFAULT '',
                    messages   TEXT DEFAULT '[]',
                    created_at TEXT DEFAULT '',
                    updated_at TEXT DEFAULT ''
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS idx_acs_uid ON ai_chat_sessions(uid, updated_at)"))
            conn.commit()
        except Exception as e:
            print(f"[Migration Warning] ai_chat_sessions: {e}")

        # Add email columns if they don't exist yet & backfill
        for tbl in ["user_ai_settings", "ai_chat_sessions", "spec_history"]:
            try:
                conn.execute(text(f"ALTER TABLE {tbl} ADD COLUMN email TEXT DEFAULT ''"))
                conn.commit()
            except Exception:
                pass

        try:
            conn.execute(text("""
                UPDATE spec_history
                SET email = (SELECT u_email FROM users WHERE users.uid = spec_history.uid)
                WHERE (email = '' OR email IS NULL) AND uid != '' AND uid IS NOT NULL
            """))
            conn.execute(text("""
                UPDATE user_ai_settings
                SET email = (SELECT u_email FROM users WHERE users.uid = user_ai_settings.uid)
                WHERE (email = '' OR email IS NULL) AND uid != '' AND uid IS NOT NULL
            """))
            conn.execute(text("""
                UPDATE ai_chat_sessions
                SET email = (SELECT u_email FROM users WHERE users.uid = ai_chat_sessions.uid)
                WHERE (email = '' OR email IS NULL) AND uid != '' AND uid IS NOT NULL
            """))
            conn.commit()
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0"))
            conn.commit()
        except Exception:
            pass

        # เพิ่ม categories ใหม่ (Gaming Gear + Furniture + PC Set)
        new_cats = [
            ("c10", "Mouse",         "Gaming Mouse / Optical Mouse"),
            ("c11", "Keyboard",      "Mechanical Keyboard / Gaming Keyboard"),
            ("c12", "Headset",       "Gaming Headset / Headphone"),
            ("c13", "Microphone",    "Condenser Mic / USB Microphone"),
            ("c14", "Monitor",       "Gaming Monitor / LED Monitor"),
            ("c15", "Gaming Chair",  "Ergonomic Chair / Gaming Chair"),
            ("c16", "Gaming Desk",   "Gaming Desk / Adjustable Desk"),
            ("c17", "Gaming Gear",   "Gaming accessories and peripherals"),
            ("c18", "PC Set",        "ชุดคอมประกอบสำเร็จรูปจากร้าน iHaveCPU / JIB / Advice"),
            ("c19", "HDD",           "Internal hard disk drives"),
            ("c20", "External Storage", "External SSD and HDD devices"),
            ("c21", "Keyboard Accessories", "Keycaps and keyboard accessories"),
            ("c22", "Cooling Accessories", "Cooling fittings, blocks and thermal accessories"),
            ("c23", "PC Components", "Other PC components"),
            ("c24", "Storage Accessories", "Storage enclosures and accessories"),
            ("c25", "Monitor Accessories", "Monitor mounts and accessories"),
            ("c26", "Case Accessories", "Case bags and other case accessories"),
            ("c27", "Keypad", "Numeric and macro keypads"),
            ("c28", "Graphic Tablet", "Pen and display tablets"),
            ("c29", "Case Fan", "Case cooling fans"),
            ("c30", "Dual Mode Monitor", "Dual-mode displays"),
            ("c31", "Portable Monitor", "Portable displays"),
            ("c32", "Curved Monitor", "Curved displays"),
            ("c33", "Gaming Headset", "Wired gaming headsets"),
            ("c34", "Wireless Headset", "Wireless gaming headsets"),
            ("c35", "GPU Accessories", "GPU supports and riser cables"),
            ("c36", "In-Ear Headphone", "In-ear gaming headphones"),
            ("c37", "True Wireless Earbuds", "True wireless gaming earbuds"),
        ]
        for cid, name, desc in new_cats:
            try:
                conn.execute(
                    text("INSERT OR IGNORE INTO categories (cid, c_name, c_description) VALUES (:cid, :name, :desc)"),
                    {"cid": cid, "name": name, "desc": desc}
                )
                conn.commit()
            except Exception as e:
                print(f"[Migration] Category {cid}: {e}")


def migrate_ai_foreign_keys(db_engine):
    """Preserve legacy AI rows, indexes and triggers while adding owner FKs."""
    with db_engine.begin() as conn:
        for table in ("user_ai_settings", "ai_chat_sessions"):
            if conn.execute(text(f"PRAGMA foreign_key_list({table})")).fetchall():
                continue
            ddl = conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:name"), {"name": table}).scalar()
            if not ddl:
                continue
            columns = [row[1] for row in conn.execute(text(f"PRAGMA table_info({table})"))]
            quoted = ", ".join('"' + c.replace('"', '""') + '"' for c in columns)
            objects = conn.execute(text("SELECT sql FROM sqlite_master WHERE tbl_name=:name AND type IN ('index','trigger') AND sql IS NOT NULL"), {"name": table}).scalars().all()
            temporary = table + "_fk_migration"
            new_ddl = re.sub(r"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?[\w\"]+", f'CREATE TABLE "{temporary}"', ddl, count=1, flags=re.I)
            closing = new_ddl.rfind(")")
            new_ddl = new_ddl[:closing] + ", FOREIGN KEY(uid) REFERENCES users(uid)" + new_ddl[closing:]
            conn.execute(text(new_ddl))
            conn.execute(text(f'INSERT INTO "{temporary}" ({quoted}) SELECT {quoted} FROM "{table}"'))
            conn.execute(text(f'DROP TABLE "{table}"'))
            conn.execute(text(f'ALTER TABLE "{temporary}" RENAME TO "{table}"'))
            for ddl_object in objects:
                conn.execute(text(ddl_object))


run_migrations(engine)
migrate_ai_foreign_keys(engine)
# Retire the provider configuration without changing historical conversations.
with engine.begin() as conn:
    conn.execute(text("UPDATE user_ai_settings SET provider='google', model='gemini-3-flash-preview', custom_model='', api_key='', updated_at=:now WHERE provider='zen'"), {"now": datetime.now().isoformat()})
    conn.execute(text("UPDATE user_ai_settings SET model='gemini-3-flash-preview', custom_model='' WHERE provider='google' AND (model IN ('gemini-2.5-pro', 'gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro') OR custom_model IN ('gemini-2.5-pro', 'gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro'))"))

# ─────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def create_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
    request: Request = None,
):
    if not creds:
        raise HTTPException(status_code=401, detail="ไม่ได้เข้าสู่ระบบ")
    try:
        payload = decode_token(creds.credentials)
        user = db.query(User).filter(User.uid == payload["uid"]).first()
        if not user:
            raise HTTPException(status_code=401, detail="ไม่พบผู้ใช้")
        if payload.get("token_version", 0) != (user.token_version or 0):
            raise HTTPException(status_code=401, detail="Token ถูกยกเลิกแล้ว")
        if request is not None:
            request.state.user_id = user.uid
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="Token ไม่ถูกต้องหรือหมดอายุ")

def require_admin(user: User = Depends(get_current_user)):
    if user.u_role != "admin":
        raise HTTPException(status_code=403, detail="ต้องมีสิทธิ์ Admin")
    return user

def ensure_admin_remains(user: User, new_role: str, db: Session) -> None:
    """Reject every update path that would demote the system's final admin."""
    if user.u_role == "admin" and new_role != "admin":
        admin_count = db.query(User).filter(User.u_role == "admin").count()
        if admin_count <= 1:
            raise HTTPException(409, "ไม่สามารถถอดสิทธิ์ admin คนสุดท้ายได้ — ระบบต้องมี admin อย่างน้อย 1 คน")

def get_optional_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Like get_current_user but returns None instead of raising 401."""
    if not creds:
        return None
    try:
        payload = decode_token(creds.credentials)
        return db.query(User).filter(User.uid == payload["uid"]).first()
    except Exception:
        return None

def product_compatibility_text(p: Product) -> str:
    """Combine normalized facts with retailer detail text for compatibility parsing."""
    blocks = []
    for field in ("specs", "desc_advice", "desc_jib", "desc_ihavecpu", "p_description"):
        value = (getattr(p, field, "") or "").strip()
        if value and value not in blocks:
            blocks.append(value)
    return "\n".join(blocks)


def product_to_dict(p: Product) -> dict:
    """แปลง Product object เป็น dict ที่มีทุก field"""
    try:
        import spec_parser as _spec_parser
        compatibility = _spec_parser.parse_part(
            p.category or "", p.p_name or "", specs=product_compatibility_text(p)
        )
    except Exception:
        compatibility = {}
    # เลือก description ที่ดีที่สุด (fallback chain)
    best_desc = (
        getattr(p, 'desc_advice', '')  or
        getattr(p, 'desc_jib', '')     or
        getattr(p, 'desc_ihavecpu', '') or
        p.p_description or ''
    )
    return {
        "product_id":     p.product_id,
        "p_name":         p.p_name,
        "p_description":  best_desc,
        "p_price":        p.p_price,
        "price_advice":   p.price_advice   or 0,
        "price_jib":      p.price_jib      or 0,
        "price_ihavecpu": p.price_ihavecpu or 0,
        "url_advice":     getattr(p, 'url_advice', '')    or "",
        "url_jib":        getattr(p, 'url_jib', '')       or "",
        "url_ihavecpu":   getattr(p, 'url_ihavecpu', '')  or "",
        "desc_advice":    getattr(p, 'desc_advice', '')   or "",
        "desc_jib":       getattr(p, 'desc_jib', '')      or "",
        "desc_ihavecpu":  getattr(p, 'desc_ihavecpu', '') or "",
        "p_stock":        p.p_stock,
        "img_url":        p.img_url,
        "category":       p.category,
        "cid":            p.cid,
        "specs":          p.specs,
        "compatibility":  compatibility,
        "updated_at":     getattr(p, 'updated_at', '') or ""
    }

# ─────────────────────────────────────────
# Schemas (Pydantic)
# ─────────────────────────────────────────
class RegisterBody(BaseModel):
    uid: str
    u_name: str
    u_email: EmailStr
    u_phone: str
    dob: str
    u_password: str = Field(min_length=6)
    confirm: str

class LoginBody(BaseModel):
    email: Optional[str] = None
    u_name: Optional[str] = None
    password: Optional[str] = None
    u_password: Optional[str] = None

class ProductCreate(BaseModel):
    product_id: str
    p_name: str
    p_description: str = ""
    p_price: float = Field(ge=0)
    p_stock: int = Field(default=0, ge=0)
    img_url: str = ""
    cid: str = ""
    category: str = ""
    specs: str = ""
    url_advice: str = ""
    url_jib: str = ""
    url_ihavecpu: str = ""
    desc_advice: str = ""
    desc_jib: str = ""
    desc_ihavecpu: str = ""

class ProductUpdate(BaseModel):
    p_name: Optional[str] = None
    p_description: Optional[str] = None
    p_price: Optional[float] = Field(default=None, ge=0)
    p_stock: Optional[int] = Field(default=None, ge=0)
    img_url: Optional[str] = None
    cid: Optional[str] = None
    category: Optional[str] = None
    specs: Optional[str] = None
    url_advice: Optional[str] = None
    url_jib: Optional[str] = None
    url_ihavecpu: Optional[str] = None
    desc_advice: Optional[str] = None
    desc_jib: Optional[str] = None
    desc_ihavecpu: Optional[str] = None

class PromoCreate(BaseModel):
    promo_name: str
    promo_description: str = ""
    promo_img: str = ""
    discount_type: str = "percent"
    discount_value: float = 0
    start_date: str
    end_date: str

class ProfileUpdate(BaseModel):
    u_name: Optional[str] = None
    u_phone: Optional[str] = None
    u_address: Optional[str] = None

class PasswordChangeBody(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class AdminUserUpdate(BaseModel):
    u_name: Optional[str] = None
    u_email: Optional[str] = None
    u_phone: Optional[str] = None
    u_address: Optional[str] = None
    u_role: Optional[str] = None

class RoleUpdate(BaseModel):
    role: str

# ─────────────────────────────────────────
# Auth Routes
# ─────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "message": "IT-RECOMMEND Shop API v3"}


@app.get("/health")
def health():
    return {"status": "ok"}


# ─────────────────────────────────────────
# Image Proxy — bypass hotlink/CORS/Referer blocking from store CDNs
# ─────────────────────────────────────────
from fastapi.responses import RedirectResponse, Response
import product_image_cache

@app.get("/api/cached-image/{digest}")
async def cached_product_image(digest: str):
    """Stable image URL backed by a short-lived private-bucket download link."""
    try:
        signed_url = await asyncio.to_thread(product_image_cache.presigned_image_url, digest)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
        if str(code) in ("404", "NoSuchKey", "NotFound"):
            raise HTTPException(404, "Cached image not found") from exc
        raise HTTPException(502, "Image storage unavailable") from exc
    return RedirectResponse(url=signed_url, status_code=302,
                            headers={"Cache-Control": "public, max-age=300"})

@app.get("/api/image-proxy")
async def image_proxy(request: Request, url: str = Query(..., description="URL รูปภาพต้นทาง")):
    """
    Proxy รูปภาพจากร้านค้า (JIB, iHaveCPU, Advice) เพื่อหลีกเลี่ยง
    hotlink-block / CORS / Referer.
    ลำดับ: 1) bucket cache → redirect  2) fetch+upload → redirect
    ถ้ายังไม่ได้ตั้ง bucket ในเครื่อง dev จะ stream bytes โดยไม่เขียนไฟล์
    """
    try:
        product_image_cache.validated_host(url)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    try:
        cached_url = await asyncio.to_thread(product_image_cache.get_cached_url, url)
        if cached_url:
            return RedirectResponse(url=cached_url, status_code=302,
                                    headers={"Cache-Control": "public, max-age=86400"})
        async with httpx.AsyncClient(timeout=20.0) as client:
            if product_image_cache.storage_config() is not None:
                cached_url, _ = await product_image_cache.fetch_and_upload(url, client)
                return RedirectResponse(url=cached_url, status_code=302,
                                        headers={"Cache-Control": "public, max-age=86400"})
            data, mime = await product_image_cache.fetch_image_bytes(url, client)
            return Response(content=data, media_type=mime,
                            headers={"Cache-Control": "public, max-age=86400"})
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"Product image unavailable: {str(exc)[:100]}") from exc

@app.post("/api/register")
@limiter.limit("5/minute")
def register(request: Request, body: RegisterBody, db: Session = Depends(get_db)):
    if body.u_password != body.confirm:
        raise HTTPException(400, "รหัสผ่านไม่ตรงกัน")
    if db.query(User).filter(User.u_email == body.u_email).first():
        raise HTTPException(400, "อีเมลนี้ถูกใช้งานแล้ว")
    if db.query(User).filter(User.u_name == body.u_name).first():
        raise HTTPException(400, "ชื่อผู้ใช้นี้ถูกใช้งานแล้ว")
    if db.query(User).filter(User.uid == body.uid).first():
        raise HTTPException(400, "User ID นี้ถูกใช้งานแล้ว")
    user = User(
        uid=body.uid, u_name=body.u_name, u_email=body.u_email,
        u_phone=body.u_phone, dob=body.dob,
        u_password=hash_password(body.u_password)
    )
    db.add(user); db.commit()
    return {"status": "success", "message": "สมัครสมาชิกสำเร็จ"}

@app.post("/api/login")
@limiter.limit("5/minute")
def login(request: Request, body: LoginBody, db: Session = Depends(get_db)):
    username = body.email or body.u_name or ""
    password = body.password or body.u_password or ""
    user = db.query(User).filter(
        (User.u_name == username) | (User.u_email == username)
    ).first()
    if not user or not verify_password(password, user.u_password):
        raise HTTPException(401, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    user.u_last_login = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.commit()
    token = create_token({
        "uid": user.uid,
        "role": user.u_role,
        "token_version": user.token_version or 0,
    })
    request.state.user_id = user.uid
    return {
        "status": "success",
        "message": "เข้าสู่ระบบสำเร็จ",
        "token": token,
        "user": {"id": user.uid, "name": user.u_name, "role": user.u_role, "email": user.u_email}
    }

# ─────────────────────────────────────────
# Products
# ─────────────────────────────────────────
BUILDER_COMPONENT_RULES = {
    "cpu": {
        "categories": ("CPU",),
        "required": re.compile(
            r"\b(?:RYZEN|THREADRIPPER|ATHLON|XEON|CORE\s+(?:I[3579]|ULTRA)|"
            r"INTEL\s+(?:CORE|PENTIUM|CELERON))\b", re.I
        ),
        "forbidden": re.compile(
            r"\b(?:COOLER|MAINBOARD|MOTHERBOARD|DESKTOP|MINI\s*PC|PC\s*SET)\b|"
            r"\bAIO\b.*\b(?:IDEACENTRE|THINKCENTRE|ASPIRE|ALL[ -]?IN[ -]?ONE)\b", re.I
        ),
    },
    "mb": {
        "categories": ("Mainboard",),
        "required": re.compile(r"\b(?:MAINB(?:OARD|AORD)|MOTHERBOARD)\b", re.I),
    },
    "gpu": {
        "categories": ("GPU",),
        "required": re.compile(
            r"\b(?:VGA|GRAPHICS?\s*CARD|GEFORCE|RADEON|RTX\s*\d|GTX\s*\d|"
            r"ARC\s+[AB]\d)\b", re.I
        ),
    },
    "ram": {
        "categories": ("RAM",),
        "required": re.compile(r"\bRAM\b|\bDDR[345]\b", re.I),
        "forbidden": re.compile(r"\b(?:GDDR\d?|VGA|GPU|GRAPHICS?\s*CARD)\b", re.I),
    },
    "ssd": {
        "categories": ("SSD",),
        "required": re.compile(r"\bSSD\b|\bM\.?2\b|\bNVME\b|SOLID\s*STATE", re.I),
        "forbidden": re.compile(
            r"\b(?:HDD|HARD\s*DISK|EXTERNAL|PORTABLE|ENCLOSURE|DOCK)\b", re.I
        ),
    },
    "hdd": {
        "categories": ("SSD", "HDD"),
        "required": re.compile(r"\bHDD\b|\bHARD\s*DISK\b|\bHARDDISK\b", re.I),
        "forbidden": re.compile(
            r"\b(?:EXT|EXTERNAL|PORTABLE|ENCLOSURE|DOCK|TRAY|DVD|CADDY)\b", re.I
        ),
    },
    "psu": {
        "categories": ("PSU",),
        "required": re.compile(r"\bPSU\b|\bPOWER\s*SUPPLY\b", re.I),
        "forbidden": re.compile(r"\b(?:UPS|POWER\s*BANK|POWER\s*STATION|ADAPTER|CHARGER)\b", re.I),
    },
    "case": {
        "categories": ("Case",),
        "required": re.compile(r"\bCASE\b|เคส", re.I),
        "forbidden": re.compile(
            r"\b(?:CASE\s*FAN|FAN\s*CASE|CABLE|BRACKET|STAND|PHONE|TABLET)\b", re.I
        ),
    },
    "cooler": {
        "categories": ("Air Cooler", "Liquid Cooler"),
        "required": re.compile(
            r"\b(?:AIR\s*COOLER|CPU\s*(?:AIR\s*)?COOLER|LIQUID\s*COOL(?:ER|ING)|"
            r"WATER\s*COOL(?:ER|ING)|AIO\s*COOLER|HEATSINK)\b", re.I
        ),
        "forbidden": re.compile(
            r"\b(?:COOLER\s*PAD|NOTEBOOK\s*COOLER|LAPTOP\s*COOLER|CASE\s*FAN|"
            r"FAN\s*CASE|FAN\s*PACK)\b|\bAIO\b.*\b(?:IDEACENTRE|THINKCENTRE|ASPIRE)\b", re.I
        ),
    },
}

BUILDER_COMPONENT_ALIASES = {
    "mainboard": "mb",
    "motherboard": "mb",
    "vga": "gpu",
    "power_supply": "psu",
    "air_cooler": "cooler",
    "liquid_cooler": "cooler",
}


def normalize_builder_component(component: str) -> str:
    key = re.sub(r"[\s-]+", "_", (component or "").strip().lower())
    return BUILDER_COMPONENT_ALIASES.get(key, key)


def product_matches_builder_component(product: Product, component: str) -> bool:
    """Strict PC Builder filter for catalog rows whose stored category is dirty."""
    key = normalize_builder_component(component)
    rule = BUILDER_COMPONENT_RULES.get(key)
    if not rule:
        return False

    valid_categories = {category.casefold() for category in rule["categories"]}
    if (product.category or "").casefold() not in valid_categories:
        return False

    name = product.p_name or ""
    if not rule["required"].search(name):
        return False
    forbidden = rule.get("forbidden")
    return not forbidden or not forbidden.search(name)


def public_product_filter():
    """Products sold by a retailer, plus in-stock products created manually.

    Imported products always carry at least one source URL. A product created in
    the admin screen has no retailer URL, so its own price determines whether
    it is visible in the public catalog. Out-of-stock items remain searchable
    and are labelled as unavailable by the UI.
    """
    retailer_has_price = or_(
        Product.price_advice > 0,
        Product.price_jib > 0,
        Product.price_ihavecpu > 0,
    )
    manual_product_is_available = and_(
        Product.p_price > 0,
        func.coalesce(Product.url_advice, "") == "",
        func.coalesce(Product.url_jib, "") == "",
        func.coalesce(Product.url_ihavecpu, "") == "",
    )
    return or_(retailer_has_price, manual_product_is_available)


# Retailer imports do not have a separate brand column. Resolve a display
# brand from the product title so facets and paginated results use one rule.
PRODUCT_BRANDS = (
    "ROYAL KLUDGE", "COOLER MASTER", "THERMALTAKE", "STEELSERIES", "TURTLE BEACH",
    "ANDA SEAT", "SECRET LAB", "DARKFLASH", "VIEWSONIC", "LOGITECH", "CORSAIR",
    "RAZER", "HYPERX", "FANTECH", "SIGNO", "NUBWO", "EGA", "COUGAR",
    "DXRACER", "KEYCHRON", "AKKO", "REDRAGON", "ONIKUMA", "SADES",
    "ASUS", "ACER", "MSI", "GIGABYTE", "SAMSUNG", "BENQ", "DELL", "AOC",
    "LG", "HP", "LENOVO", "HUAWEI", "XIAOMI", "PHILIPS", "SONY",
    "MARSHALL", "JBL", "CREATIVE", "BEWELL", "MODENA", "INDEX",
)
GENERIC_PRODUCT_WORDS = {
    "GAMING", "MOUSE", "KEYBOARD", "HEADSET", "HEADPHONE", "MONITOR", "DESK",
    "CHAIR", "TABLE", "MICROPHONE", "WIRELESS", "WIRED", "USB", "LED", "RGB",
    "โต๊ะ", "เก้าอี้", "หูฟัง", "เมาส์", "คีย์บอร์ด", "จอ", "จอมอนิเตอร์",
}


def product_brand(name: str) -> str:
    title = (name or "").upper()
    for brand in PRODUCT_BRANDS:
        if re.search(r"(?<![A-Z0-9])" + re.escape(brand) + r"(?![A-Z0-9])", title):
            return brand
    # JIB prefixes furniture names with a Thai category description between
    # the English category and the actual brand. Do not expose that description
    # as a brand when the maker is not in PRODUCT_BRANDS.
    title = re.sub(r"^GAMING\s+(?:CHAIR|DESK)\b\s*", "", title)
    title = re.sub(r"^\([^A-Z]*\)\s*", "", title)
    for token in re.findall(r"[A-Z][A-Z0-9-]+|[ก-๙]+", title):
        if token not in GENERIC_PRODUCT_WORDS and not token.isdigit() and len(token) > 1:
            return token
    return "Other"


def filter_product_store(q, store: str):
    if not store:
        return q
    column = {
        "advice": Product.price_advice,
        "jib": Product.price_jib,
        "ihavecpu": Product.price_ihavecpu,
    }.get(store.lower())
    if column is None:
        raise HTTPException(400, "Unsupported store")
    return q.filter(column > 0)


@app.get("/api/products/filters")
def get_product_filters(
    category: str = "", search: str = "", store: str = "",
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    q = db.query(Product).filter(public_product_filter())
    if category:
        q = q.filter(func.lower(Product.category) == category.lower())
    if search:
        q = q.filter(Product.p_name.contains(search) | Product.p_description.contains(search))
    q = filter_product_store(q, store)
    brands = sorted({product_brand(name) for (name,) in q.with_entities(Product.p_name).all()})
    return {"status": "success", "data": {"brands": brands}}


@app.get("/api/products")
def get_products(
    category: str = "", cid: str = "", search: str = "", name: str = "",
    component: str = "", store: str = "", brand: str = "",
    page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(get_optional_user),
):
    is_admin = user and user.u_role == "admin"
    q = db.query(Product)

    # Admins can manage every row. Public users see retailer products and
    # in-stock products that were entered manually in the admin screen.
    if not is_admin:
        q = q.filter(public_product_filter())

    component_key = normalize_builder_component(component)
    component_rule = BUILDER_COMPONENT_RULES.get(component_key) if component else None
    if component and not component_rule:
        raise HTTPException(400, "Unsupported PC Builder component")
    if component_rule:
        q = q.filter(func.lower(Product.category).in_(
            [value.lower() for value in component_rule["categories"]]
        ))
        q = q.filter(public_product_filter())
    if category:
        q = q.filter(func.lower(Product.category) == category.lower())
    if cid:      q = q.filter(Product.cid == cid)
    if search:   q = q.filter(Product.p_name.contains(search) | Product.p_description.contains(search))
    if name:     q = q.filter(Product.p_name.contains(name))
    q = filter_product_store(q, store)
    if component_rule:
        matching_products = [
            product for product in q.order_by(Product.created_at.desc()).all()
            if product_matches_builder_component(product, component_key)
        ]
        if brand:
            matching_products = [p for p in matching_products if product_brand(p.p_name).casefold() == brand.casefold()]
        total = len(matching_products)
        start = (page - 1) * limit
        products = matching_products[start:start + limit]
    elif brand:
        matching_products = [
            product for product in q.order_by(Product.created_at.desc()).all()
            if product_brand(product.p_name).casefold() == brand.casefold()
        ]
        total = len(matching_products)
        start = (page - 1) * limit
        products = matching_products[start:start + limit]
    else:
        total = q.count()
        products = q.order_by(Product.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return {
        "status": "success",
        "data": [product_to_dict(p) for p in products],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": (total + limit - 1) // limit,
        },
    }

@app.get("/api/products/{product_id}")
def get_product(product_id: str, db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.product_id == product_id).first()
    if not p: raise HTTPException(404, "ไม่พบสินค้า")
    return {"status": "success", "data": product_to_dict(p)}

@app.get("/api/products/{product_id}/compare")
def compare_product_prices(product_id: str, db: Session = Depends(get_db)):
    """
    เปรียบเทียบราคาสินค้าชิ้นเดียวกันจากหลายร้านค้า
    Response:
    {
      product_id, p_name, img_url, description,
      stores: [ {store, store_name, price, url, available: bool} ],
      cheapest: {store, store_name, price, url},
      price_range: {min, max, diff}
    }
    """
    p = db.query(Product).filter(Product.product_id == product_id).first()
    if not p:
        raise HTTPException(404, "ไม่พบสินค้า")

    store_data = [
        {
            "store":      "advice",
            "store_name": "Advice",
            "price":      int(getattr(p, "price_advice",   0) or 0),
            "url":        getattr(p, "url_advice",   "") or "",
        },
        {
            "store":      "jib",
            "store_name": "JIB",
            "price":      int(getattr(p, "price_jib",     0) or 0),
            "url":        getattr(p, "url_jib",     "") or "",
        },
        {
            "store":      "ihavecpu",
            "store_name": "iHaveCPU",
            "price":      int(getattr(p, "price_ihavecpu", 0) or 0),
            "url":        getattr(p, "url_ihavecpu", "") or "",
        },
    ]

    # Mark available stores (price > 0)
    available = [
        {**s, "available": s["price"] > 0}
        for s in store_data
    ]
    available_only = [s for s in available if s["available"]]

    # Sort by price ascending
    available_sorted = sorted(available_only, key=lambda s: s["price"])

    cheapest = available_sorted[0] if available_sorted else None
    prices   = [s["price"] for s in available_only]

    best_desc = (
        getattr(p, "desc_advice",   "") or
        getattr(p, "desc_jib",      "") or
        getattr(p, "desc_ihavecpu", "") or
        p.p_description or ""
    )

    return {
        "status": "success",
        "data": {
            "product_id":  p.product_id,
            "p_name":      p.p_name,
            "img_url":     p.img_url or "",
            "description": best_desc,
            "category":    p.category,
            "stores":      available,          # ทุกร้าน (รวมที่ไม่มีราคา)
            "available_stores": available_sorted,  # เฉพาะร้านที่มีราคา เรียงราคาถูก→แพง
            "cheapest":    cheapest,           # ร้านถูกสุด
            "price_range": {
                "min":  min(prices) if prices else 0,
                "max":  max(prices) if prices else 0,
                "diff": max(prices) - min(prices) if len(prices) >= 2 else 0,
            },
            "store_count": len(available_only),  # จำนวนร้านที่มีสินค้านี้
            "updated_at":  getattr(p, "updated_at", "") or "",
        },
    }

@app.post("/api/products")
def create_product(body: ProductCreate, admin=Depends(require_admin), db: Session = Depends(get_db)):
    if db.query(Product).filter(Product.product_id == body.product_id).first():
        raise HTTPException(400, "product_id นี้มีอยู่แล้ว")
    p = Product(**body.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return {
        "status": "success",
        "message": "เพิ่มสินค้าสำเร็จ",
        "data": product_to_dict(p),
    }

@app.put("/api/products/{product_id}")
def update_product(product_id: str, body: ProductUpdate, admin=Depends(require_admin), db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.product_id == product_id).first()
    if not p: raise HTTPException(404, "ไม่พบสินค้า")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return {
        "status": "success",
        "message": "แก้ไขสินค้าสำเร็จ",
        "data": product_to_dict(p),
    }

@app.delete("/api/products/{product_id}")
def delete_product(product_id: str, admin=Depends(require_admin), db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.product_id == product_id).first()
    if not p: raise HTTPException(404, "ไม่พบสินค้า")
    db.delete(p); db.commit()
    return {"status": "success", "message": "ลบสินค้าสำเร็จ"}

# ─────────────────────────────────────────
# Promotions
# ─────────────────────────────────────────
@app.get("/api/promotions")
def get_promotions(db: Session = Depends(get_db)):
    promos = db.query(Promotion).filter(Promotion.status == "active").order_by(Promotion.promo_id.desc()).all()
    return {"status": "success", "data": [
        {
            "promo_id": pr.promo_id, "promo_name": pr.promo_name,
            "promo_description": pr.promo_description, "promo_img": pr.promo_img,
            "discount_type": pr.discount_type, "discount_value": pr.discount_value,
            "start_date": pr.start_date, "end_date": pr.end_date, "status": pr.status
        } for pr in promos
    ]}

@app.post("/api/promotions")
def create_promo(body: PromoCreate, admin=Depends(require_admin), db: Session = Depends(get_db)):
    pr = Promotion(**body.model_dump())
    db.add(pr); db.commit()
    return {"status": "success", "message": "เพิ่มโปรโมชั่นสำเร็จ", "promo_id": pr.promo_id}

@app.put("/api/promotions/{promo_id}")
def update_promo(promo_id: int, body: PromoCreate, admin=Depends(require_admin), db: Session = Depends(get_db)):
    pr = db.query(Promotion).filter(Promotion.promo_id == promo_id).first()
    if not pr: raise HTTPException(404, "ไม่พบโปรโมชั่น")
    for k, v in body.model_dump().items(): setattr(pr, k, v)
    db.commit()
    return {"status": "success", "message": "แก้ไขโปรโมชั่นสำเร็จ"}

@app.delete("/api/promotions/{promo_id}")
def delete_promo(promo_id: int, admin=Depends(require_admin), db: Session = Depends(get_db)):
    pr = db.query(Promotion).filter(Promotion.promo_id == promo_id).first()
    if not pr: raise HTTPException(404, "ไม่พบโปรโมชั่น")
    db.delete(pr); db.commit()
    return {"status": "success", "message": "ลบโปรโมชั่นสำเร็จ"}

# ─────────────────────────────────────────
# Spec History (the authenticated CRUD handlers are defined below)
# ─────────────────────────────────────────

@app.get("/api/spec-history/all")
def get_all_spec_history(admin=Depends(require_admin), limit: int = 100, db: Session = Depends(get_db)):
    items = db.query(SpecHistory).order_by(SpecHistory.createdAt.desc()).limit(limit).all()
    return {"status": "success", "data": [
        {"id": i.id, "uid": i.uid, "username": i.username,
         "type": i.type, "mode": i.mode, "title": i.title,
         "inputSummary": i.inputSummary, "result_data": i.result_data,
         "createdAt": i.createdAt}
        for i in items
    ]}


# ─────────────────────────────────────────
# Profile
# ─────────────────────────────────────────
@app.get("/api/profile")
def get_profile(user: User = Depends(get_current_user)):
    return {"status": "success", "data": {
        "uid": user.uid, "u_name": user.u_name, "u_email": user.u_email,
        "u_phone": user.u_phone, "u_address": user.u_address,
        "u_image": user.u_image, "u_role": user.u_role, "dob": user.dob,
        "u_created_at": user.u_created_at, "u_last_login": user.u_last_login
    }}

@app.put("/api/profile")
def update_profile(body: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.uid == user.uid).first()
    if body.u_name:
        # ตรวจสอบว่าชื่อซ้ำกับคนอื่นไหม
        existing = db.query(User).filter(User.u_name == body.u_name, User.uid != user.uid).first()
        if existing:
            raise HTTPException(400, "ชื่อผู้ใช้นี้ถูกใช้งานแล้ว")
        db_user.u_name = body.u_name
    if body.u_phone is not None: db_user.u_phone = body.u_phone
    if body.u_address is not None: db_user.u_address = body.u_address
    db_user.u_updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.commit()
    return {"status": "success", "message": "อัปเดตโปรไฟล์สำเร็จ", "data": {
        "uid": db_user.uid, "u_name": db_user.u_name, "u_email": db_user.u_email,
        "u_phone": db_user.u_phone, "u_address": db_user.u_address,
        "u_image": db_user.u_image, "u_role": db_user.u_role, "dob": db_user.dob
    }}

@app.put("/api/profile/password")
def change_password(body: PasswordChangeBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.uid == user.uid).first()
    if not verify_password(body.current_password, db_user.u_password):
        raise HTTPException(400, "รหัสผ่านปัจจุบันไม่ถูกต้อง")
    if body.new_password != body.confirm_password:
        raise HTTPException(400, "รหัสผ่านใหม่ไม่ตรงกัน")
    if len(body.new_password) < 6:
        raise HTTPException(400, "รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร")
    db_user.u_password = hash_password(body.new_password)
    db_user.token_version = (db_user.token_version or 0) + 1
    db_user.u_updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.commit()
    # The old token is revoked; replace it for this verified session.
    token = create_token({
        "uid": db_user.uid,
        "role": db_user.u_role,
        "token_version": db_user.token_version,
    })
    return {"status": "success", "message": "เปลี่ยนรหัสผ่านสำเร็จ", "token": token}

@app.post("/api/profile/upload-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    allowed = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, "อนุญาตเฉพาะไฟล์รูปภาพ")
    filename = f"{user.uid}_{int(datetime.now().timestamp())}{ext}"
    filepath = UPLOAD_DIR / filename
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)
    db_user = db.query(User).filter(User.uid == user.uid).first()
    db_user.u_image = f"uploads/profile/{filename}"
    db.commit()
    return {"status": "success", "image_url": db_user.u_image}

# ─────────────────────────────────────────
# Categories
# ─────────────────────────────────────────
@app.get("/api/categories")
def get_categories(db: Session = Depends(get_db)):
    cats = db.query(Category).all()
    return {"status": "success", "data": [
        {"cid": c.cid, "name": c.c_name, "description": c.c_description}
        for c in cats
    ]}

# ─────────────────────────────────────────
# Admin – User Management
# ─────────────────────────────────────────
@app.get("/api/admin/users")
def admin_get_all_users(admin=Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.u_created_at.desc()).all()
    result = []
    for u in users:
        spec_count  = db.query(SpecHistory).filter(SpecHistory.uid == u.uid).count()
        result.append({
            "uid": u.uid, "u_name": u.u_name, "u_email": u.u_email,
            "u_phone": u.u_phone, "u_role": u.u_role, "dob": u.dob,
            "u_image": u.u_image, "u_address": u.u_address,
            "u_created_at": u.u_created_at, "u_last_login": u.u_last_login,
            "spec_count": spec_count
        })
    return {"status": "success", "data": result}

@app.get("/api/admin/users/{uid}")
def admin_get_user(uid: str, admin=Depends(require_admin), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.uid == uid).first()
    if not u: raise HTTPException(404, "ไม่พบผู้ใช้")
    return {"status": "success", "data": {
        "uid": u.uid, "u_name": u.u_name, "u_email": u.u_email,
        "u_phone": u.u_phone, "u_role": u.u_role, "dob": u.dob,
        "u_image": u.u_image, "u_address": u.u_address,
        "u_created_at": u.u_created_at, "u_last_login": u.u_last_login
    }}

@app.put("/api/admin/users/{uid}")
def admin_update_user(uid: str, body: AdminUserUpdate, admin=Depends(require_admin), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.uid == uid).first()
    if not u: raise HTTPException(404, "ไม่พบผู้ใช้")
    if body.u_name:
        existing = db.query(User).filter(User.u_name == body.u_name, User.uid != uid).first()
        if existing:
            raise HTTPException(400, "ชื่อผู้ใช้นี้ถูกใช้งานแล้ว")
        u.u_name = body.u_name
    if body.u_email:
        existing = db.query(User).filter(User.u_email == body.u_email, User.uid != uid).first()
        if existing:
            raise HTTPException(400, "อีเมลนี้ถูกใช้งานแล้ว")
        u.u_email = body.u_email
    if body.u_phone is not None: u.u_phone = body.u_phone
    if body.u_address is not None: u.u_address = body.u_address
    if body.u_role:
        ensure_admin_remains(u, body.u_role, db)
        u.u_role = body.u_role
    u.u_updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.commit()
    return {"status": "success", "message": "อัปเดตข้อมูลผู้ใช้สำเร็จ"}

@app.delete("/api/admin/users/{uid}")
def admin_delete_user(uid: str, admin=Depends(require_admin), db: Session = Depends(get_db)):
    if uid == admin.uid:
        raise HTTPException(400, "ไม่สามารถลบบัญชีของตัวเองได้")
    u = db.query(User).filter(User.uid == uid).first()
    if not u: raise HTTPException(404, "ไม่พบผู้ใช้")
    db.delete(u); db.commit()
    return {"status": "success", "message": "ลบผู้ใช้สำเร็จ"}

@app.put("/api/admin/users/{uid}/role")
def admin_change_role(uid: str, body: RoleUpdate, admin=Depends(require_admin), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.uid == uid).first()
    if not u: raise HTTPException(404, "ไม่พบผู้ใช้")
    allowed_roles = ["customer", "admin", "staff"]
    if body.role not in allowed_roles:
        raise HTTPException(400, f"role ต้องเป็น: {', '.join(allowed_roles)}")
    ensure_admin_remains(u, body.role, db)
    u.u_role = body.role
    u.u_updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.commit()
    return {"status": "success", "message": f"เปลี่ยน role เป็น '{body.role}' สำเร็จ"}

@app.get("/api/admin/users/{uid}/specs")
def admin_get_user_specs(uid: str, admin=Depends(require_admin), db: Session = Depends(get_db)):
    specs = db.query(SpecHistory).filter(SpecHistory.uid == uid).order_by(SpecHistory.createdAt.desc()).all()
    return {"status": "success", "data": [
        {"id": s.id, "type": s.type, "mode": s.mode, "title": s.title,
         "inputSummary": s.inputSummary, "result_data": s.result_data, "createdAt": s.createdAt}
        for s in specs
    ]}

# ─────────────────────────────────────────
# AI Recommend – Hybrid RAG + Compatibility Engine (Multi-provider)
# ─────────────────────────────────────────

# ─────────────────────────────────────────
# AI Provider Settings (per user)
# ─────────────────────────────────────────
class AiSettingsBody(BaseModel):
    provider:     Literal["google", "openai", "openrouter", "opencode_zen"] = "google"
    model:        str = "gemini-3-flash-preview"
    api_key:      str = ""
    custom_model: str = ""


def server_ai_credentials(provider: str) -> tuple[str, str]:
    """Use server-configured credentials as a private fallback for the AI page."""
    provider = (provider or "").lower()
    if provider == "google":
        return os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", ""), os.getenv("GOOGLE_MODEL", "gemini-3-flash-preview")
    if provider == "openai":
        return os.getenv("OPENAI_API_KEY", ""), os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    if provider == "openrouter":
        return os.getenv("OPENROUTER_API_KEY", ""), os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini").strip() or "openai/gpt-4o-mini"
    if provider == "opencode_zen":
        return os.getenv("OPENCODE_ZEN_API_KEY", ""), os.getenv("OPENCODE_ZEN_MODEL", "minimax-m2.5").strip() or "minimax-m2.5"
    return "", ""


RETIRED_GOOGLE_MODELS = {"gemini-2.5-pro", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"}


def normalize_ai_model(provider: str, model: str) -> str:
    """Remap known unavailable Google IDs while preserving user-defined models."""
    return "gemini-3-flash-preview" if provider == "google" and model in RETIRED_GOOGLE_MODELS else model


def default_ai_provider() -> tuple[str, str]:
    for provider in ("openai", "google", "openrouter", "opencode_zen"):
        key, model = server_ai_credentials(provider)
        if key:
            return provider, model
    return "openai", "gpt-4o-mini"

@app.get("/api/ai/settings")
def get_ai_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(UserAiSettings).filter(UserAiSettings.uid == user.uid).first()
    if not row:
        provider, model = default_ai_provider()
        return {"status": "success", "data": {
            "uid": user.uid, "email": user.u_email,
            "provider": provider, "model": model, "api_key": "", "custom_model": ""
        }}
    # Migrate the effective default for old rows created with Google but no key.
    row_key, _ = server_ai_credentials(row.provider)
    if not row.api_key and not row_key:
        provider, model = default_ai_provider()
        return {"status": "success", "data": {
            "uid": user.uid, "email": row.email or user.u_email,
            "provider": provider, "model": model, "api_key": "", "custom_model": ""
        }}
    return {"status": "success", "data": {
        "uid":          row.uid,
        "email":        row.email or user.u_email,
        "provider":     row.provider,
        "model":        normalize_ai_model(row.provider, row.model),
        "api_key":      decrypt_ai_key(row.api_key),
        "custom_model": normalize_ai_model(row.provider, row.custom_model) if row.custom_model else "",
        "updated_at":   row.updated_at,
    }}

@app.put("/api/ai/settings")
def save_ai_settings(body: AiSettingsBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.query(UserAiSettings).filter(UserAiSettings.uid == user.uid).first()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    encrypted_key = encrypt_ai_key(body.api_key)
    if row:
        row.email        = user.u_email
        row.provider     = body.provider
        row.model        = normalize_ai_model(body.provider, body.model)
        row.api_key      = encrypted_key
        row.custom_model = normalize_ai_model(body.provider, body.custom_model) if body.custom_model else ""
        row.updated_at   = now
    else:
        row = UserAiSettings(
            uid=user.uid, email=user.u_email, provider=body.provider,
            model=normalize_ai_model(body.provider, body.model),
            api_key=encrypted_key,
            custom_model=normalize_ai_model(body.provider, body.custom_model) if body.custom_model else "",
            updated_at=now
        )
        db.add(row)
    db.commit()
    return {"status": "success", "message": "บันทึก AI settings สำเร็จ"}


# ─────────────────────────────────────────
# AI Chat Sessions
# ─────────────────────────────────────────
class ChatSessionCreate(BaseModel):
    title:    str = "New Chat"
    mode:     Literal["recommend", "compare", "compat"] = "recommend"
    provider: Literal["google", "openai", "openrouter", "opencode_zen"] = "google"
    model:    str = ""

class ChatSessionUpdate(BaseModel):
    title:    Optional[str] = None
    messages: Optional[str] = None  # JSON string

    @field_validator("messages")
    @classmethod
    def valid_messages(cls, value):
        if value is None: return value
        try:
            messages = json.loads(value)
        except (ValueError, TypeError):
            raise ValueError("messages must contain a JSON array")
        if not isinstance(messages, list) or any(not isinstance(m, dict) or m.get("role") not in ("user", "assistant") or not isinstance(m.get("content"), str) for m in messages):
            raise ValueError("Invalid chat messages")
        return value

    provider: Optional[Literal["google", "openai", "openrouter", "opencode_zen"]] = None
    model:    Optional[str] = None

def _session_dict(s: AiChatSession) -> dict:
    return {
        "id": s.id, "uid": s.uid, "email": getattr(s, "email", "") or "", "title": s.title,
        "mode": s.mode, "provider": s.provider, "model": s.model,
        "messages": s.messages, "created_at": s.created_at, "updated_at": s.updated_at,
    }

@app.get("/api/ai/sessions")
def list_sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sessions = db.query(AiChatSession).filter(
        AiChatSession.uid == user.uid
    ).order_by(AiChatSession.updated_at.desc(), AiChatSession.id.desc()).limit(100).all()
    return {"status": "success", "data": [_session_dict(s) for s in sessions]}

@app.post("/api/ai/sessions")
def create_session(body: ChatSessionCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    s = AiChatSession(
        uid=user.uid, email=user.u_email, title=body.title, mode=body.mode,
        provider=body.provider, model=body.model,
        messages="[]", created_at=now, updated_at=now
    )
    db.add(s); db.commit(); db.refresh(s)
    return {"status": "success", "data": _session_dict(s)}

@app.get("/api/ai/sessions/{session_id}")
def get_session(session_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(AiChatSession).filter(
        AiChatSession.id == session_id, AiChatSession.uid == user.uid
    ).first()
    if not s: raise HTTPException(404, "ไม่พบ session")
    return {"status": "success", "data": _session_dict(s)}

@app.put("/api/ai/sessions/{session_id}")
def update_session(session_id: int, body: ChatSessionUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(AiChatSession).filter(
        AiChatSession.id == session_id, AiChatSession.uid == user.uid
    ).first()
    if not s: raise HTTPException(404, "ไม่พบ session")
    if body.title    is not None: s.title    = body.title
    if body.messages is not None: s.messages = body.messages
    if body.provider is not None: s.provider = body.provider
    if body.model    is not None: s.model    = body.model
    s.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.commit()
    return {"status": "success", "data": _session_dict(s)}

@app.delete("/api/ai/sessions/{session_id}")
def delete_session(session_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.query(AiChatSession).filter(
        AiChatSession.id == session_id, AiChatSession.uid == user.uid
    ).first()
    if not s: raise HTTPException(404, "ไม่พบ session")
    db.delete(s); db.commit()
    return {"status": "success", "message": "ลบ session สำเร็จ"}


# ─────────────────────────────────────────
# AI Recommend — authenticated, per-user provider/key
# ─────────────────────────────────────────
class AIRecommendBody(BaseModel):
    spec1: Optional[str] = None
    spec2: Optional[str] = None
    prompt:     str
    mode:         Literal["recommend", "compare", "compat", "ask"] = "recommend"
    provider:     Optional[Literal["google", "openai", "openrouter", "opencode_zen"]] = None
    model:        Optional[str] = None
    api_key:      Optional[str] = None
    session_id:   Optional[int] = None
    spec_context: Optional[str] = None  # plain-text build summary for mode="ask"

@app.post("/api/ai/recommend")
@limiter.limit("10/minute")
async def ai_recommend(
    request: Request,
    body: AIRecommendBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Hybrid recommendation pipeline for authenticated users.
    Uses the user's stored AI settings and saves to their session.
    Provider priority: body override > DB settings > env defaults

    Recommendation responses expose a severity-based compatibility score in
    each alternative and in `_meta.compatibility_score_policy`. Failed or
    unknown rules reduce the score proportionally; a confirmed critical
    failure (for example R1 socket or R8 GPU/PSU connector mismatch) caps the
    compatibility component at 50/100.
    """
    # Safe defaults so the outer exception handlers can always name the provider,
    # even when the failure happens before provider/model are resolved.
    provider = "unknown"
    model = ""
    provider_label = "AI provider"
    try:
        import recommender as rec

        # ── Resolve provider / model / api_key ──────────────────────────
        db_settings = db.query(UserAiSettings).filter(UserAiSettings.uid == user.uid).first() if user else None
        fallback_provider, fallback_model = default_ai_provider()
        provider = body.provider if body.provider is not None else (db_settings.provider if db_settings else fallback_provider)
        same_provider = db_settings is not None and db_settings.provider == provider
        model = body.model if body.model is not None else ((db_settings.custom_model or db_settings.model) if same_provider else "")
        model = normalize_ai_model(provider, model.strip() or (fallback_model if provider == fallback_provider else rec.DEFAULT_MODELS[provider]))
        configured_key, _ = server_ai_credentials(provider)
        stored_key = decrypt_ai_key(db_settings.api_key) if db_settings else ""
        api_key = body.api_key if body.api_key is not None and body.api_key.strip() else (stored_key if same_provider and stored_key else configured_key)
        if not api_key.strip() and body.mode != "recommend":
            raise HTTPException(400, f"ยังไม่ได้ตั้งค่า API Key สำหรับ {provider} กรุณาเปิด Settings หรือกำหนด key ฝั่งเซิร์ฟเวอร์")
        provider_label = {"openai": "OpenAI", "google": "Google Gemini", "openrouter": "OpenRouter", "opencode_zen": "OpenCode Zen"}.get(provider, provider)
        session = None
        if body.session_id is not None:
            if not user:
                raise HTTPException(401, "Login required to use a saved session")
            session = db.query(AiChatSession).filter(AiChatSession.id == body.session_id, AiChatSession.uid == user.uid).first()
            if session is None:
                raise HTTPException(404, "Session not found")
            # A conversation may naturally move from a comparison to a build
            # request. Keep the same session so the earlier context is available.
        if not body.prompt.strip():
            raise HTTPException(422, "Prompt cannot be empty")

        try:
            previous = json.loads(session.messages or "[]") if session else []
        except (TypeError, ValueError):
            previous = []
        context = "\n".join(f"{m['role']}: {m['content']}" for m in previous[-12:])
        contextual_prompt = f"Previous conversation:\n{context}\n\nCurrent request:\n{body.prompt}" if context else body.prompt
        if body.mode == "compare" and previous and (not body.spec1 or not body.spec2):
            source = next((m for m in reversed(previous) if m.get("spec1") and m.get("spec2")), {})
            body.spec1 = body.spec1 or source.get("spec1")
            body.spec2 = body.spec2 or source.get("spec2")

        if body.mode == "ask":
            # Prefer the displayed build; otherwise find the latest build in
            # this user's session (not the latest free-form ask answer).
            spec_ctx = (body.spec_context or "").strip()
            if not spec_ctx and previous:
                for message in reversed(previous):
                    if message.get("role") != "assistant":
                        continue
                    try:
                        parsed = rec.extract_json(message.get("content", ""))
                    except Exception:
                        continue
                    if not isinstance(parsed, dict) or not isinstance(parsed.get("parts"), list):
                        continue
                    lines_ctx = [
                        f"- {part.get('type', '')}: {part.get('name', '')} ({part.get('price', '')})"
                        for part in parsed["parts"] if isinstance(part, dict)
                    ]
                    if lines_ctx:
                        budget = parsed.get("totalBudget")
                        spec_ctx = "\n".join(lines_ctx)
                        if budget:
                            spec_ctx += f"\nงบประมาณรวม: {budget}"
                        break
            if not spec_ctx:
                raise HTTPException(422, "No recommended PC spec is available for this question")
            try:
                raw = await rec.answer_spec_question(
                    body.prompt, spec_ctx,
                    provider=provider, model=model, api_key=api_key,
                )
            except httpx.TimeoutException:
                # Transient: keep the existing 504 mapping so the client can retry.
                raise
            except (RuntimeError, httpx.HTTPError) as provider_error:
                logger.warning(
                    "AI provider unavailable for mode=ask (provider=%s model=%s): %s",
                    provider, model, provider_error,
                )
                ask_compat, _, _ = rec.deterministic_compatibility_from_text(spec_ctx)
                raw = json.dumps({
                    "error": True,
                    "status": "provider_unavailable",
                    "provider": provider,
                    "provider_label": provider_label,
                    "reason": str(provider_error)[:300],
                    "message": (
                        f"{provider_label} ใช้งานไม่ได้ชั่วคราว "
                        f"จึงแสดงผลจากระบบ deterministic แทน "
                        f"กรุณาตรวจสอบ API key, โมเดล และโควตาของ {provider_label}"
                    ),
                    "compatibility": ask_compat,
                }, ensure_ascii=False)
        elif body.mode == "compat":
            result = await rec.compat_check_hybrid(contextual_prompt, provider=provider, model=model, api_key=api_key)
            raw = json.dumps(result, ensure_ascii=False)
        elif body.mode == "compare":
            if not body.spec1 or not body.spec2:
                match = re.search(r"(?:spec|\u0e2a\u0e40\u0e1b\u0e04|\u0e2a\u0e40\u0e1b\u0e01)\s*1\s*[:?]\s*(.+?)\s*(?:\n|\|)\s*(?:spec|\u0e2a\u0e40\u0e1b\u0e04|\u0e2a\u0e40\u0e1b\u0e01)\s*2\s*[:?]\s*(.+)", body.prompt, re.I | re.S)
                if not match:
                    raise HTTPException(400, "Both specs are required")
                body.spec1, body.spec2 = match.group(1).strip(), match.group(2).strip()
            try:
                raw = await rec.compare_specs(body.spec1, body.spec2, context=contextual_prompt,
                                              provider=provider, model=model, api_key=api_key)
            except httpx.TimeoutException:
                # Transient: keep the existing 504 mapping so the client can retry.
                raise
            except (RuntimeError, httpx.HTTPError) as provider_error:
                logger.warning(
                    "AI provider unavailable for mode=compare (provider=%s model=%s): %s",
                    provider, model, provider_error,
                )
                compat1, _, _ = rec.deterministic_compatibility_from_text(body.spec1)
                compat2, _, _ = rec.deterministic_compatibility_from_text(body.spec2)
                raw = json.dumps({
                    "error": True,
                    "status": "provider_unavailable",
                    "provider": provider,
                    "provider_label": provider_label,
                    "reason": str(provider_error)[:300],
                    "message": (
                        f"{provider_label} ใช้งานไม่ได้ชั่วคราว "
                        f"จึงแสดงผลจากระบบ deterministic แทน "
                        f"กรุณาตรวจสอบ API key, โมเดล และโควตาของ {provider_label}"
                    ),
                    "spec1Name": "Spec 1",
                    "spec2Name": "Spec 2",
                    "winner": "tie",
                    "verdict": f"{provider_label} ใช้งานไม่ได้ชั่วคราว",
                    "categories": [],
                    "spec1Pros": [],
                    "spec2Pros": [],
                    "recommendation": "กรุณาลองเปรียบเทียบอีกครั้ง",
                    "compatibility": {"spec1": compat1, "spec2": compat2},
                    "compatibilityWarnings": [],
                }, ensure_ascii=False)
        else:
            try:
                result = await rec.recommend_with_alternatives(db, contextual_prompt,
                                                               provider=provider, model=model, api_key=api_key)
            except (RuntimeError, httpx.TimeoutException, httpx.ConnectError, httpx.HTTPError) as provider_error:
                if str(provider_error).startswith("Requested GPU unavailable:"):
                    requested_gpu = str(provider_error).partition(":")[2].strip()
                    raise HTTPException(
                        422,
                        f"ไม่พบการ์ดจอ {requested_gpu} ที่มีราคาในฐานข้อมูลตอนนี้ กรุณาเลือก GPU รุ่นอื่นหรือลองใหม่ภายหลัง",
                    )
                if str(provider_error) == "No complete compatible catalogue build available":
                    raise HTTPException(422, "ยังไม่มีชุดสินค้าที่ครบและผ่านการตรวจความเข้ากันได้ในฐานข้อมูล")
                reason = ("rate_limit" if str(provider_error) == "rate_limit" else
                          "invalid_response" if str(provider_error) == "LLM returned invalid JSON" else
                          "provider_unavailable")
                # Keep the coarse bucket for the log line, but hand the response a
                # self-describing reason so the JSON alone is enough to debug.
                detailed_reason = f"{reason} — {rec.failure_reason(provider_error)}"
                logger.warning(
                    "AI recommend fell back to deterministic (provider=%s model=%s reason=%s): %s",
                    provider, model, reason, provider_error,
                )
                try:
                    result = rec.recommend_without_provider(db, contextual_prompt, reason=detailed_reason)
                except RuntimeError as fallback_error:
                    # The deterministic fallback can itself fail (e.g. an empty or
                    # incomplete catalogue). Surface a real message instead of letting
                    # it escape and become a bare 502.
                    logger.error(
                        "Deterministic fallback also failed (provider=%s reason=%s): %s",
                        provider, reason, fallback_error, exc_info=True,
                    )
                    if str(fallback_error) == "No complete compatible catalogue build available":
                        raise HTTPException(422, "ยังไม่มีชุดสินค้าที่ครบและผ่านการตรวจความเข้ากันได้ในฐานข้อมูล")
                    raise HTTPException(
                        503,
                        f"{provider_label} ใช้งานไม่ได้ชั่วคราว และระบบ deterministic "
                        "ไม่สามารถสร้างชุดสินค้าได้ กรุณาลองใหม่อีกครั้ง",
                    )
            raw = json.dumps(result, ensure_ascii=False)

        raw = rec.strip_emojis(raw)

        # ── Save to chat session if logged in ───────────────────────────
        if user:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            session = None
            if body.session_id:
                session = db.query(AiChatSession).filter(
                    AiChatSession.id == body.session_id, AiChatSession.uid == user.uid
                ).first()
            if not session:
                # สร้าง session ใหม่อัตโนมัติ (title = 40 ตัวแรกของ prompt)
                title = body.prompt[:40].replace("\n", " ").strip() or "New Chat"
                session = AiChatSession(
                    uid=user.uid, email=user.u_email, title=title, mode=body.mode,
                    provider=provider, model=model,
                    messages="[]", created_at=now, updated_at=now
                )
                db.add(session); db.flush()
            else:
                if not getattr(session, "email", ""):
                    session.email = user.u_email

            # Append messages
            try:
                msgs = json.loads(session.messages or "[]")
            except Exception:
                msgs = []
            msgs.append({"role": "user",      "content": body.prompt, "ts": now, "spec1": body.spec1, "spec2": body.spec2})
            msgs.append({"role": "assistant", "content": raw,         "ts": now})
            session.messages   = json.dumps(msgs, ensure_ascii=False)
            if body.mode != "ask":
                session.mode = body.mode
            session.provider = provider
            session.model = model
            if session.title == "New Chat": session.title = body.prompt[:40].replace("\n", " ")
            session.updated_at = now
            db.commit()

        return {"status": "success", "data": raw,
                "session_id": session.id if user and session else None}

    except httpx.TimeoutException:
        logger.warning("AI provider timed out", exc_info=True)
        raise HTTPException(504, "AI provider หมดเวลา กรุณาลองใหม่")
    except (httpx.ConnectError, httpx.HTTPError):
        logger.warning("AI provider connection failed", exc_info=True)
        raise HTTPException(503, "AI provider เชื่อมต่อไม่ได้ กรุณาลองใหม่")
    except RuntimeError as e:
        msg = str(e)
        if msg == "rate_limit":
            return {"status": "rate_limit", "message": "คนใช้งานเยอะ กรุณาลองใหม่อีกครั้ง"}
        logger.error(
            "AI provider request failed (mode=%s provider=%s model=%s): %s",
            body.mode, provider, model, msg, exc_info=True,
        )
        if "timed out" in msg.lower():
            raise HTTPException(504, "AI provider หมดเวลา กรุณาลองใหม่")
        raise HTTPException(502, f"{provider_label} ใช้งานไม่ได้ชั่วคราว กรุณาตรวจสอบโมเดล, API key และโควตา")
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected /api/ai/recommend failure (mode=%s)", body.mode)
        raise HTTPException(500, "Unable to complete AI request; the server logged the failure for diagnosis")


class CompatCheckBody(BaseModel):
    parts_text: str

@app.post("/api/compat/check")
async def compat_check(body: CompatCheckBody, user: User = Depends(get_current_user)):
    """Deterministic compatibility engine — no LLM involved in the verdict.

    Every check retains its PASS/ERROR/WARNING/UNKNOWN result and also exposes
    `score_severity` (`critical` or `warning`) for recommendation ranking.
    """
    import recommender as rec
    result = await rec.compat_check_hybrid(body.parts_text)
    return {"status": "success", "data": result}


class CompatPartItem(BaseModel):
    """T1-2: Typed part item to prevent 500 on bad payload (C14, C15)"""
    category: str = ""
    name: Optional[str] = None
    p_name: Optional[str] = None
    price: Optional[float] = None
    p_price: Optional[float] = None
    product_id: Optional[str] = None
    id: Optional[str] = None

class CompatibilityPartsBody(BaseModel):
    parts: List[CompatPartItem]
    budget: Optional[int] = None

@app.post("/api/compatibility/check-parts")
@app.post("/api/compatibility/check")
def check_compatibility_parts(
    body: CompatibilityPartsBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Real-time deterministic compatibility check for structured parts.

    Check results include `score_severity`; confirmed critical failures cap the
    recommendation compatibility score at 50/100 without changing rule verdicts.
    """
    import spec_parser as sp
    import compat_engine as ce

    parsed = []
    for p in body.parts:
        cat   = p.category or ""
        name  = p.name or p.p_name or ""
        price = p.price or p.p_price or 0
        pid   = p.product_id or p.id or ""

        # ดึง specs จาก DB ถ้ามี product_id — ใช้ข้อมูลจากหน้าสินค้าจริง (แม่นกว่า regex)
        specs_text = ""
        if pid:
            row = db.query(Product).filter(Product.product_id == pid).first()
            if not row:
                raise HTTPException(404, "Product not found: " + str(pid))
            specs_text = product_compatibility_text(row)
            name = row.p_name
            cat = row.category

        part_info = sp.parse_part(cat, name, specs=specs_text)
        part_info["product_id"] = pid
        part_info["price"] = price
        parsed.append(part_info)

    result = ce.check_build(parsed, body.budget)
    return {"status": "success", "data": result}


class SpecHistoryCreate(BaseModel):
    uid: Optional[str] = ""  # ignored — server uses JWT
    email: Optional[str] = ""
    username: Optional[str] = ""
    type: Optional[str] = "manual"
    mode: Optional[str] = "manual"
    title: Optional[str] = "จัดสเปกเอง"
    inputSummary: Optional[str] = ""
    # The database stores this field as JSON text. Accept objects as well as
    # the JSON string used by the AI page so all save clients share one API.
    result_data: Any = "{}"


def refreshed_history_result(item: SpecHistory, db: Session) -> str:
    """Re-run deterministic checks for saved manual builds using current product facts."""
    if item.mode != "manual":
        return item.result_data
    try:
        data = json.loads(item.result_data or "{}")
        parts = data.get("parts") or []
        names = [part.get("name", "") for part in parts if part.get("name")]
        if not names:
            return item.result_data

        products = db.query(Product).filter(Product.p_name.in_(names)).all()
        products_by_name = {product.p_name: product for product in products}
        category_by_key = {
            "cpu": "CPU", "mb": "Mainboard", "gpu": "GPU", "ram": "RAM",
            "ssd": "SSD", "hdd": "SSD", "psu": "PSU", "case": "Case",
            "cooler": "Cooler",
        }
        import spec_parser as sp
        import compat_engine as ce

        parsed = []
        for part in parts:
            name = part.get("name", "")
            product = products_by_name.get(name)
            category = product.category if product else category_by_key.get(part.get("key", ""), "")
            specs = product_compatibility_text(product) if product else ""
            parsed_part = sp.parse_part(category, name, specs=specs)
            parsed_part["price"] = part.get("min_price") or part.get("price") or 0
            parsed.append(parsed_part)

        data["compatibility"] = ce.check_build(parsed)
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return item.result_data

@app.get("/api/spec-history")
def get_spec_history(request: Request, current_user: User = Depends(get_current_user), limit: int = 50, db: Session = Depends(get_db)):
    # T0-1: Filter by JWT uid only — no uid/email query params (H04, H05)
    requested_uid = request.query_params.get("uid")
    if requested_uid and requested_uid != current_user.uid:
        raise HTTPException(403, "ไม่มีสิทธิ์ดูประวัติของผู้ใช้อื่น")
    items = db.query(SpecHistory).filter(
        SpecHistory.uid == current_user.uid
    ).order_by(SpecHistory.createdAt.desc()).limit(limit).all()
    return {"status": "success", "data": [
        {
            "id": s.id, "uid": s.uid, "email": s.email or "", "username": s.username,
            "type": s.type, "mode": s.mode, "title": s.title,
            "inputSummary": s.inputSummary, "result_data": refreshed_history_result(s, db),
            "createdAt": s.createdAt
        } for s in items
    ]}

@app.post("/api/spec-history")
def create_spec_history(body: SpecHistoryCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # T0-1: uid from JWT only — ignore body.uid (H06)
    res_str = json.dumps(body.result_data, ensure_ascii=False) if not isinstance(body.result_data, str) else body.result_data

    item = SpecHistory(
        uid=current_user.uid,
        email=current_user.u_email,
        username=body.username or current_user.u_name,
        type=body.type or "manual",
        mode=body.mode or "manual",
        title=body.title or "จัดสเปกเอง",
        inputSummary=body.inputSummary or "",
        result_data=res_str,
        createdAt=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {
        "status": "success",
        "message": "บันทึกประวัติการจัดสเปคสำเร็จ",
        "data": {
            "id": item.id, "uid": item.uid, "email": item.email, "username": item.username,
            "type": item.type, "mode": item.mode, "title": item.title,
            "inputSummary": item.inputSummary, "result_data": item.result_data,
            "createdAt": item.createdAt
        }
    }

@app.delete("/api/spec-history/{id}")
def delete_spec_history(id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Idempotent delete.

    Race-safe: the row is read once for the ownership check, then removed with a
    single bulk DELETE statement. A bulk `Query.delete()` issues one SQL DELETE and
    reports how many rows it actually matched, so two concurrent requests for the
    same id can never both "succeed" and we never hit the ORM unit-of-work path
    (`db.delete(obj)`) whose stale-identity-map check emits
    "expected to delete 1 row(s); 0 were matched".
    """
    item = db.query(SpecHistory).filter(SpecHistory.id == id).first()
    if not item:
        # The row is already gone — deleted by an earlier or concurrent request.
        # Same end state as a successful delete, so this is a 200, not a 404.
        logger.debug("spec-history delete: id=%s not found (already deleted)", id)
        return {"status": "success", "message": "ประวัตินี้ถูกลบไปแล้ว", "already_deleted": True}

    # T0-1: Only owner or admin can delete (H07). Checked before deleting so an
    # unauthorised caller still gets 403 and can never remove the row.
    if item.uid != current_user.uid and current_user.u_role != "admin":
        raise HTTPException(403, "ไม่มีสิทธิ์ลบประวัตินี้")

    # Drop the stale identity-map entry so autoflush cannot re-issue work for it.
    db.expunge(item)
    deleted = (
        db.query(SpecHistory)
        .filter(SpecHistory.id == id)
        .delete(synchronize_session=False)
    )
    db.commit()

    if deleted == 0:
        # Lost the race: another request deleted the row between our SELECT and
        # our DELETE. Expected under concurrent clicks — debug, not warning.
        logger.debug(
            "spec-history delete race: id=%s uid=%s already removed by a concurrent request",
            id, current_user.uid,
        )
        return {"status": "success", "message": "ประวัตินี้ถูกลบไปแล้ว", "already_deleted": True}

    return {"status": "success", "message": "ลบประวัติสำเร็จ", "already_deleted": False}


@app.get("/api/price-history/{product_id}")
def get_price_history(product_id: str, db: Session = Depends(get_db)):
    """Price trend for one product across tracked stores (data freshness / history)."""
    rows = db.execute(
        text("""SELECT store, price, captured_at FROM price_history
                WHERE product_id = :pid ORDER BY captured_at ASC"""),
        {"pid": product_id}).fetchall()
    p = db.query(Product).filter(Product.product_id == product_id).first()
    if not p:
        raise HTTPException(404, "ไม่พบสินค้า")

    series = {}
    for store, price, captured_at in rows:
        series.setdefault(store, []).append({"date": captured_at[:10], "price": int(price)})

    stores = {
        "advice":   {"name": "Advice",   "price": p.price_advice,   "url": p.url_advice},
        "jib":      {"name": "JIB",      "price": p.price_jib,      "url": p.url_jib},
        "ihavecpu": {"name": "iHaveCPU", "price": p.price_ihavecpu, "url": p.url_ihavecpu},
    }
    sources = [{"store": v["name"], "price": int(v["price"]), "url": v["url"] or ""}
               for v in stores.values() if v["price"] and v["price"] > 0]

    trend = None
    all_points = [pt["price"] for pts in series.values() for pt in pts]
    if len(all_points) >= 2:
        first, last = all_points[0], all_points[-1]
        change = last - first
        trend = {
            "direction": "down" if change < 0 else ("up" if change > 0 else "flat"),
            "change_thb": int(change),
            "change_pct": round(change / first * 100, 1) if first else 0,
        }

    return {
        "status": "success",
        "data": {
            "product_id": product_id,
            "p_name": p.p_name,
            "last_updated": getattr(p, "updated_at", "") or "",
            "current_prices": sorted(sources, key=lambda s: s["price"]),
            "history": series,
            "trend": trend,
        },
    }

# ─────────────────────────────────────────
# Scraper API
# ─────────────────────────────────────────
class ScrapeRequest(BaseModel):
    store: str = "all"
    pages: int = 2

@app.post("/api/scrape")
async def trigger_scrape(body: ScrapeRequest, admin=Depends(require_admin)):
    """
    ทริกเกอร์ full scraper (full_scraper.py) แบบ background
    - store: "all" | "advice" | "jib" | "ihavecpu"
    - pages: จำนวนหน้าต่อ category
    """
    try:
        import subprocess, sys
        stores_arg = body.store  # "all" or single store name
        cmd = [
            sys.executable, "full_scraper.py",
            "--stores", stores_arg,
            "--pages",  str(body.pages),
        ]
        # รัน subprocess แบบ detached (non-blocking) — ไม่รอผล
        subprocess.Popen(
            cmd,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {
            "status":  "started",
            "message": f"Scraper กำลังทำงานใน background (stores={stores_arg}, pages={body.pages})",
        }
    except Exception as e:
        raise HTTPException(500, f"Scraper launch error: {str(e)}")

@app.get("/api/scrape/status")
def scrape_status(db: Session = Depends(get_db)):
    with engine.connect() as conn:
        total   = conn.execute(text("SELECT COUNT(*) FROM products")).scalar()
        has_img = conn.execute(text("SELECT COUNT(*) FROM products WHERE img_url != '' AND img_url IS NOT NULL")).scalar()
        has_ihc = conn.execute(text("SELECT COUNT(*) FROM products WHERE price_ihavecpu > 0")).scalar()
        has_adv = conn.execute(text("SELECT COUNT(*) FROM products WHERE price_advice > 0")).scalar()
        has_jib = conn.execute(text("SELECT COUNT(*) FROM products WHERE price_jib > 0")).scalar()
        multi   = conn.execute(text(
            "SELECT COUNT(*) FROM products WHERE "
            "(CASE WHEN price_advice>0 THEN 1 ELSE 0 END + "
            " CASE WHEN price_jib>0 THEN 1 ELSE 0 END + "
            " CASE WHEN price_ihavecpu>0 THEN 1 ELSE 0 END) >= 2"
        )).scalar()
    return {
        "status": "ok",
        "products": {"total": total, "with_image": has_img},
        "prices":   {"ihavecpu": has_ihc, "advice": has_adv, "jib": has_jib},
        "multi_store": multi,  # สินค้าที่เปรียบเทียบราคาได้ (>= 2 ร้าน)
    }

# ─────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("[OK] IT-RECOMMEND API running on http://localhost:3000")
    print("[DOCS] API Docs: http://localhost:3000/docs")
    uvicorn.run(app, host="0.0.0.0", port=3000)
````

## backend/test_access_log.py

SHA-256 of source file: `18d193b85e8c8f4303f8424ffb2e153544e16e11209073136e11c154e8fc19d9`

````python
"""Access logging tests with synthetic requests and mocked Supabase only."""

import asyncio
import contextlib
from contextlib import asynccontextmanager
import json
import io
import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI
import httpx
from starlette.requests import Request

import access_log
import verify_access_logs


def request(path="/api/login", headers=(), client=("127.0.0.1", 5000)):
    return Request({
        "type": "http", "method": "POST", "path": path,
        "query_string": b"password=never-record-this", "headers": [
            (name.lower().encode(), value.encode()) for name, value in headers
        ], "client": client, "scheme": "http", "server": ("test", 80),
    })


class PayloadTests(unittest.TestCase):
    def test_ip_precedence_limits_and_allowlist(self):
        req = request("/api/admin/" + "a" * 400, headers=[
            ("x-forwarded-for", " 203.0.113.1, 192.0.2.2"),
            ("x-real-ip", "192.0.2.3"), ("user-agent", "u" * 500),
            ("x-vercel-ip-country", "TH"), ("authorization", "secret"),
            ("cookie", "secret"),
        ])
        req.state.user_id = "alice"
        payload = access_log.log_payload(req, 403)
        self.assertEqual(set(payload), {
            "method", "path", "status", "ip", "country", "user_agent", "user_id",
        })
        self.assertEqual(payload["ip"], "203.0.113.1")
        self.assertEqual(payload["country"], "TH")
        self.assertEqual(payload["user_id"], "alice")
        self.assertEqual(len(payload["path"]), 300)
        self.assertEqual(len(payload["user_agent"]), 300)
        self.assertNotIn("never-record-this", json.dumps(payload))
        self.assertNotIn("secret", json.dumps(payload))

    def test_ip_fallbacks_and_null_values(self):
        req = request(headers=[("x-forwarded-for", " , 192.0.2.2"),
                               ("x-real-ip", "198.51.100.2")])
        self.assertEqual(access_log.log_payload(req, 401)["ip"], "198.51.100.2")
        payload = access_log.log_payload(request(), 401)
        self.assertEqual(payload["ip"], "127.0.0.1")
        self.assertIsNone(payload["country"])
        self.assertIsNone(payload["user_id"])
        self.assertIsNone(access_log.log_payload(request(client=None), 401)["ip"])

    def test_route_selection(self):
        for prefix in access_log.LOG_PREFIXES:
            self.assertTrue(access_log.should_log("GET", prefix + "/test"), prefix)
        for path in ("/products", "/api/products", "/api/products/1", "/health", "/uploads/profile/a"):
            self.assertFalse(access_log.should_log("GET", path), path)
        self.assertTrue(access_log.should_log("DELETE", "/api/products/1"))
        self.assertTrue(access_log.should_log("POST", "/api/promotions"))
        self.assertFalse(access_log.should_log("POST", "/api/products-unrelated"))


class LiveVerifierTests(unittest.TestCase):
    def test_live_verifier_checks_keys_denial_and_tagged_backend_rows(self):
        rows = []
        def handler(req):
            if req.url.host == "127.0.0.1":
                self.assertNotIn("apikey", req.headers)
                self.assertNotIn("authorization", req.headers)
                if req.url.path in ("/api/login", "/api/admin/users"):
                    rows.append({"path": req.url.path, "status": 401,
                                 "ip": "127.0.0.1", "user_agent": req.headers["user-agent"]})
                    return httpx.Response(401)
                return httpx.Response(200)
            if req.url.path == "/auth/v1/settings":
                return httpx.Response(200, json={})
            if req.headers["apikey"] == "synthetic-anon":
                return httpx.Response(401 if req.method == "GET" else 403)
            if "user_agent" in req.url.params:
                return httpx.Response(200, json=rows)
            return httpx.Response(200, json=[])
        with httpx.Client(transport=httpx.MockTransport(handler)) as client, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            verify_access_logs.verify(client, "https://logs.example.test",
                "synthetic-service", "synthetic-anon", "http://127.0.0.1:3000")
        self.assertIn("real Supabase rows", output.getvalue())
        self.assertNotIn("synthetic-service", output.getvalue())
        self.assertNotIn("synthetic-anon", output.getvalue())

    def test_invalid_anon_key_is_not_mistaken_for_a_secure_table(self):
        paths = []
        def handler(req):
            paths.append(req.url.path)
            return httpx.Response(401)
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaisesRegex(RuntimeError, "no access-control conclusion"):
                verify_access_logs.verify(client, "https://logs.example.test",
                    "synthetic-service", "invalid-anon")
        self.assertEqual(paths, ["/auth/v1/settings"])

    def test_read_or_write_access_for_anon_fails_verification(self):
        def handler(req):
            return httpx.Response(200, json=[])
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaisesRegex(RuntimeError, "Anon access is not denied"):
                verify_access_logs.verify(client, "https://logs.example.test",
                    "synthetic-service", "synthetic-anon")


class AsyncLoggingTests(unittest.IsolatedAsyncioTestCase):
    def configured_logger(self, handler):
        logger = access_log.AccessLogger()
        original = httpx.AsyncClient
        with patch.dict(os.environ, {"SUPABASE_URL": "https://logs.example.test",
                                     "SUPABASE_SERVICE_KEY": "synthetic-service-key"}), \
             patch.object(access_log.httpx, "AsyncClient", side_effect=lambda **kwargs:
                          original(transport=httpx.MockTransport(handler), **kwargs)):
            logger.start()
        return logger

    async def test_shared_client_headers_task_references_and_cleanup(self):
        received = []
        async def handler(req):
            received.append(req)
            return httpx.Response(201)
        logger = self.configured_logger(handler)
        client = logger.client
        self.assertEqual(client.timeout.read, 5.0)
        logger.enqueue(request(), 401)
        logger.enqueue(request(), 403)
        self.assertEqual(len(logger.pending), 2)
        await asyncio.gather(*tuple(logger.pending))
        await asyncio.sleep(0)
        self.assertFalse(logger.pending)
        self.assertIs(logger.client, client)
        self.assertEqual(len(received), 2)
        for req in received:
            self.assertEqual(str(req.url), "https://logs.example.test/rest/v1/access_logs")
            self.assertEqual(req.headers["apikey"], "synthetic-service-key")
            self.assertEqual(req.headers["authorization"], "Bearer synthetic-service-key")
            self.assertEqual(req.headers["prefer"], "return=minimal")
            self.assertEqual(req.headers["content-type"], "application/json")
        await logger.close()
        self.assertTrue(client.is_closed)

    async def test_missing_invalid_or_insecure_environment_disables_logging(self):
        for url, key in (("", ""), ("https://logs.example.test", ""), ("wrong", "key"),
                         ("http://logs.example.test", "key"),
                         ("https://user:pass@logs.example.test", "key")):
            with self.subTest(url=url), patch.dict(os.environ, {
                "SUPABASE_URL": url, "SUPABASE_SERVICE_KEY": key,
            }):
                logger = access_log.AccessLogger()
                logger.start()
                logger.enqueue(request(), 401)
                self.assertIsNone(logger.client)
                self.assertFalse(logger.pending)
                await logger.close()

    async def test_failure_timeout_and_http_errors_are_swallowed(self):
        for failure in (httpx.ConnectError("down"), httpx.ReadTimeout("timeout"), None):
            async def handler(req):
                if failure:
                    raise failure
                return httpx.Response(503)
            logger = self.configured_logger(handler)
            logger.enqueue(request(), 401)
            await asyncio.gather(*tuple(logger.pending))
            await logger.close()

    async def test_response_does_not_wait_for_supabase_and_preserves_lifespan(self):
        sending = asyncio.Event()
        release = asyncio.Event()
        received = []
        lifecycle = []
        async def handler(req):
            sending.set()
            await release.wait()
            received.append(req)
            return httpx.Response(201)
        @asynccontextmanager
        async def original_lifespan(app):
            lifecycle.append("start")
            yield
            lifecycle.append("stop")
        app = FastAPI(lifespan=original_lifespan)
        @app.get("/api/admin/test")
        async def endpoint():
            return {"ok": True}
        access_log.install_access_logging(app)
        access_log.install_access_logging(app)
        original = httpx.AsyncClient
        with patch.dict(os.environ, {"SUPABASE_URL": "https://logs.example.test",
                                     "SUPABASE_SERVICE_KEY": "synthetic-service-key"}), \
             patch.object(access_log.httpx, "AsyncClient", side_effect=lambda **kwargs:
                          original(transport=httpx.MockTransport(handler), **kwargs)):
            async with app.router.lifespan_context(app):
                async with original(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                    response = await asyncio.wait_for(client.get("/api/admin/test"), timeout=1.0)
                    self.assertEqual(response.status_code, 200)
                    await asyncio.wait_for(sending.wait(), timeout=1.0)
                    self.assertFalse(received)
                    release.set()
        self.assertEqual(len(received), 1)
        self.assertEqual(lifecycle, ["start", "stop"])

    async def test_unhandled_failure_records_500_and_is_not_hidden(self):
        received = []
        async def handler(req):
            received.append(json.loads(req.content))
            return httpx.Response(201)
        app = FastAPI()
        @app.get("/api/admin/failure")
        async def endpoint():
            raise RuntimeError("application failure")
        access_log.install_access_logging(app)
        logger = self.configured_logger(handler)
        app.state.access_logger.client = logger.client
        app.state.access_logger.url = logger.url
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            with self.assertRaises(RuntimeError):
                await client.get("/api/admin/failure")
        await app.state.access_logger.close()
        self.assertEqual(received[0]["status"], 500)

    async def test_task_backlog_is_bounded(self):
        release = asyncio.Event()
        async def handler(req):
            await release.wait()
            return httpx.Response(201)
        logger = self.configured_logger(handler)
        for _ in range(access_log.MAX_PENDING_LOGS + 5):
            logger.enqueue(request(), 401)
        self.assertEqual(len(logger.pending), access_log.MAX_PENDING_LOGS)
        release.set()
        await logger.close()
        self.assertFalse(logger.pending)


if __name__ == "__main__":
    unittest.main()
````

## backend/test_ai_sessions.py

SHA-256 of source file: `e3d40024bf64ad6e783722fabc192c19a95bd1c39108c8e72e7bdfea32ff849b`

````python

import asyncio
import contextlib
import importlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

class AiSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = os.getcwd()
        cls.original_db_url = os.environ.get("DATABASE_URL")
        cls.temp = tempfile.TemporaryDirectory()
        os.chdir(cls.temp.name)
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        os.environ.setdefault(
            "JWT_SECRET", "qa-ai-sessions-secret-012345678901234567890123"
        )
        # Point DATABASE_URL at this suite's own temporary file *before* shop_api
        # is imported. shop_api reads it once at import time and builds its
        # engine from it, so setting it later would be too late. Depending on
        # the process cwd alone is not enough: another suite that imported
        # shop_api earlier in the same interpreter would hand us its engine.
        cls.db_path = Path(cls.temp.name) / "ai_sessions_test.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{cls.db_path.as_posix()}"
        # Force a fresh module so the engine is rebuilt against the URL above.
        sys.modules.pop("shop_api", None)
        with contextlib.redirect_stdout(io.StringIO()):
            cls.api = importlib.import_module('shop_api')
        cls.assertIsolatedDatabase()
        cls.api.Base.metadata.create_all(cls.api.engine)
        cls.rec = importlib.import_module('recommender')
        cls.client = TestClient(cls.api.app)
        with cls.api.SessionLocal() as db:
            db.add_all([cls.api.User(uid=u, u_name=u, u_email=u+'@example.com', u_password='unused') for u in ('alice','bob')])
            db.commit()

    @classmethod
    def assertIsolatedDatabase(cls):
        """Fail loudly if this suite is pointed at the real shop.db."""
        url = str(cls.api.engine.url)
        assert cls.db_path.name in url, f"expected a temporary database, got {url}"
        assert url != "sqlite:///./shop.db", "refusing to run against the real shop.db"
        assert Path.cwd().resolve() != Path(__file__).resolve().parent, \
            "cwd must be the temporary directory, not the backend source directory"

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        # Release the SQLite handle before TemporaryDirectory.cleanup(), or
        # Windows keeps the file locked and cleanup raises PermissionError.
        cls.api.engine.dispose()
        sys.modules.pop("shop_api", None)
        if cls.original_db_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = cls.original_db_url
        os.chdir(cls.original)
        cls.temp.cleanup()

    def auth(self, user='alice'):
        return {'Authorization': 'Bearer '+self.api.create_token({'uid': user})}

    def setUp(self):
        # Endpoint rate limits should not leak between independent unit tests.
        self.api.limiter._storage.reset()

    def test_access_logs_for_real_login_admin_and_owner_routes(self):
        import httpx
        import access_log
        rows = []
        original = httpx.AsyncClient
        async def store(req):
            rows.append(json.loads(req.content))
            return httpx.Response(201)
        headers = {'x-forwarded-for': '203.0.113.7, 192.0.2.5',
                   'x-real-ip': '198.51.100.8', 'user-agent': 'AccessAudit/1.0',
                   'x-vercel-ip-country': 'TH'}
        with patch.dict(os.environ, {'SUPABASE_URL': 'https://logs.example.test',
                                     'SUPABASE_SERVICE_KEY': 'synthetic-service-key'}), \
             patch.object(access_log.httpx, 'AsyncClient', side_effect=lambda **kwargs:
                          original(transport=httpx.MockTransport(store), **kwargs)):
            with TestClient(self.api.app) as client:
                self.assertEqual(client.post('/api/login?password=do-not-log', headers=headers,
                    json={'email': 'missing@example.com', 'password': 'wrong-password'}).status_code, 401)
                self.assertEqual(client.get('/api/admin/users', headers=headers).status_code, 401)
                self.assertEqual(client.get('/api/admin/users', headers={**headers, **self.auth()}).status_code, 403)
                self.assertEqual(client.get('/api/profile', headers={**headers, **self.auth()}).status_code, 200)
                self.assertEqual(client.get('/api/products', headers=headers).status_code, 200)
                self.assertEqual(client.get('/products', headers=headers).status_code, 404)
                with self.api.SessionLocal() as db:
                    db.add(self.api.User(uid='log-admin', u_name='log-admin',
                        u_email='log-admin@example.com', u_password=self.api.hash_password('synthetic-password'),
                        u_role='admin'))
                    db.commit()
                self.assertEqual(client.post('/api/login', headers=headers, json={
                    'email': 'log-admin@example.com', 'password': 'wrong-password'}).status_code, 401)
                login = client.post('/api/login', headers=headers, json={
                    'email': 'log-admin@example.com', 'password': 'synthetic-password'})
                self.assertEqual(login.status_code, 200)
                admin_auth = {'Authorization': 'Bearer ' + login.json()['token']}
                self.assertEqual(client.get('/api/admin/users', headers={**headers, **admin_auth}).status_code, 200)
        self.assertEqual(len(rows), 7)
        self.assertEqual([(row['path'], row['status'], row['user_id']) for row in rows], [
            ('/api/login', 401, None), ('/api/admin/users', 401, None),
            ('/api/admin/users', 403, 'alice'), ('/api/profile', 200, 'alice'),
            ('/api/login', 401, None),
            ('/api/login', 200, 'log-admin'), ('/api/admin/users', 200, 'log-admin'),
        ])
        for row in rows:
            self.assertEqual(row['ip'], '203.0.113.7')
            self.assertEqual(row['user_agent'], 'AccessAudit/1.0')
            self.assertEqual(row['country'], 'TH')
        self.assertNotIn('synthetic-password', json.dumps(rows))
        self.assertNotIn('do-not-log', json.dumps(rows))
        self.assertNotIn('wrong-password', json.dumps(rows))

    def test_admin_and_private_route_dependencies(self):
        from fastapi.routing import APIRoute
        admins = []
        private_prefixes = ('/api/profile', '/api/ai/settings', '/api/ai/sessions', '/api/spec-history')
        for route in self.api.app.routes:
            if not isinstance(route, APIRoute):
                continue
            dependencies = {dep.call for dep in route.dependant.dependencies}
            is_admin = route.path.startswith('/api/admin/') or route.path == '/api/spec-history/all'
            is_admin = is_admin or (route.path.startswith(('/api/products', '/api/promotions'))
                                    and bool(route.methods & {'POST', 'PUT', 'DELETE'}))
            is_admin = is_admin or (route.path == '/api/scrape' and 'POST' in route.methods)
            if is_admin:
                admins.append(route)
                self.assertIn(self.api.require_admin, dependencies, route.path)
            elif route.path.startswith(private_prefixes):
                self.assertIn(self.api.get_current_user, dependencies, route.path)
        self.assertTrue(admins)
        for route in admins:
            for method in route.methods:
                self.assertEqual(self.client.request(method, route.path.replace('{uid}', 'alice')
                    .replace('{product_id}', 'test').replace('{promo_id}', '1')).status_code, 401)
                self.assertEqual(self.client.request(method, route.path.replace('{uid}', 'alice')
                    .replace('{product_id}', 'test').replace('{promo_id}', '1'), headers=self.auth()).status_code, 403)

    def test_wrong_supabase_url_does_not_break_real_api(self):
        import httpx
        import access_log
        original = httpx.AsyncClient
        async def down(req):
            raise httpx.ConnectError('unreachable Supabase', request=req)
        with patch.dict(os.environ, {'SUPABASE_URL': 'https://unreachable.invalid',
                                     'SUPABASE_SERVICE_KEY': 'synthetic-service-key'}), \
             patch.object(access_log.httpx, 'AsyncClient', side_effect=lambda **kwargs:
                          original(transport=httpx.MockTransport(down), **kwargs)):
            with TestClient(self.api.app) as client:
                self.assertEqual(client.get('/api/admin/users').status_code, 401)
                self.assertEqual(client.get('/api/profile', headers=self.auth()).status_code, 200)

    def test_settings_isolation_and_validation(self):
        c=self.client
        self.assertEqual(c.get('/api/ai/settings').status_code,401)
        for u,p in [('alice','google'),('bob','openai')]:
            r=c.put('/api/ai/settings', headers=self.auth(u), json={'provider':p,'model':'test-model','api_key':u+'-key'})
            self.assertEqual(r.status_code,200)
        for u in ('alice','bob'):
            self.assertEqual(c.get('/api/ai/settings', headers=self.auth(u)).json()['data']['api_key'],u+'-key')
        self.assertEqual(c.put('/api/ai/settings',headers=self.auth(),json={'provider':'invalid'}).status_code,422)

    def test_session_crud_and_ownership(self):
        c=self.client; h=self.auth()
        item=c.post('/api/ai/sessions',headers=h,json={'title':'Test'}).json()['data']
        url='/api/ai/sessions/'+str(item['id'])
        for method,body in [('get',None),('put',{'title':'hacked'}),('delete',None)]:
            kwargs={'headers':self.auth('bob')}
            if body: kwargs['json']=body
            self.assertEqual(getattr(c,method)(url,**kwargs).status_code,404)
        ids=[x['id'] for x in c.get('/api/ai/sessions',headers=self.auth('bob')).json()['data']]
        self.assertNotIn(item['id'],ids)
        self.assertEqual(c.put(url,headers=h,json={'messages':'{}'}).status_code,422)
        messages=json.dumps([{'role':'user','content':'hello'}])
        self.assertEqual(c.put(url,headers=h,json={'messages':messages,'title':'Renamed'}).status_code,200)
        self.assertEqual(c.get(url,headers=h).json()['data']['title'],'Renamed')
        self.assertEqual(c.delete(url,headers=h).status_code,200)
        self.assertEqual(c.get(url,headers=h).status_code,404)

    def test_recommend_resolution_append_and_failure(self):
        c=self.client;h=self.auth()
        c.put('/api/ai/settings',headers=h,json={'provider':'google','model':'saved','custom_model':'custom','api_key':'alice-key'})
        with patch.object(self.rec,'recommend_with_alternatives',new_callable=AsyncMock,return_value={'summary':'ok','parts':[]}) as call:
            first=c.post('/api/ai/recommend',headers=h,json={'prompt':'Budget 30000'}).json()
            self.assertEqual(first['status'],'success')
            self.assertEqual(call.call_args.kwargs,{'provider':'google','model':'custom','api_key':'alice-key'})
            sid=first['session_id']
            second=c.post('/api/ai/recommend',headers=h,json={'prompt':'Prefer AMD','session_id':sid,'provider':'openai','api_key':'override-key'}).json()
            self.assertEqual(second['session_id'],sid)
            self.assertEqual(call.call_args.kwargs['provider'],'openai')
            self.assertEqual(call.call_args.kwargs['api_key'],'override-key')
            self.assertIn('Budget 30000',call.call_args.args[1])
            messages=json.loads(c.get('/api/ai/sessions/'+str(sid),headers=h).json()['data']['messages'])
            self.assertEqual(len(messages),4)
            count=call.await_count
            self.assertEqual(c.post('/api/ai/recommend',headers=self.auth('bob'),json={'prompt':'x','session_id':sid,'provider':'openai','api_key':'override-key'}).status_code,404)
            self.assertEqual(call.await_count,count)
            self.assertEqual(c.post('/api/ai/recommend',json={'prompt':'guest','provider':'openai','api_key':'override-key'}).status_code,401)
            self.assertEqual(c.post('/api/ai/recommend',json={'prompt':'x','session_id':sid,'api_key':'guest-key'}).status_code,401)
            with patch.dict(os.environ, {'GOOGLE_API_KEY': '', 'GEMINI_API_KEY': ''}, clear=False):
                self.assertEqual(c.post('/api/ai/recommend',headers=self.auth('bob'),json={'prompt':'x','provider':'google'}).status_code,200)
                self.assertEqual(call.call_args.kwargs['api_key'], '')

    def test_ask_uses_latest_recommended_build_in_owned_session(self):
        build = {'summary': 'build', 'parts': [
            {'type': 'CPU', 'name': 'Ryzen test CPU', 'price': 9000},
            {'type': 'GPU', 'name': 'RTX test GPU', 'price': 12000},
        ], 'totalBudget': '30,000 ฿'}
        with patch.object(self.rec, 'recommend_with_alternatives', new_callable=AsyncMock,
                          return_value=build) as recommend:
            first = self.client.post('/api/ai/recommend', headers=self.auth(), json={
                'prompt': 'Recommend a PC', 'provider': 'google', 'api_key': 'test-key',
            })
            self.assertEqual(first.status_code, 200)
            sid = first.json()['session_id']
            with patch.object(self.rec, 'answer_spec_question', new_callable=AsyncMock,
                              return_value='เล่นได้') as answer:
                for question in ('เล่นเกมได้ไหม', 'แล้วตัดต่อวิดีโอได้ไหม'):
                    response = self.client.post('/api/ai/recommend', headers=self.auth(), json={
                        'prompt': question, 'mode': 'ask', 'session_id': sid,
                        'provider': 'google', 'api_key': 'test-key',
                    })
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()['data'], 'เล่นได้')
                    self.assertIn('Ryzen test CPU', answer.call_args.args[1])
                self.assertEqual(answer.await_count, 2)
            self.assertEqual(recommend.await_count, 1)
        self.assertEqual(self.client.post('/api/ai/recommend', headers=self.auth('bob'), json={
            'prompt': 'Can it game?', 'mode': 'ask', 'session_id': sid,
            'api_key': 'test-key',
        }).status_code, 404)

    def test_ask_requires_a_build_and_uses_llm_chat_directly(self):
        self.assertEqual(self.client.post('/api/ai/recommend', headers=self.auth(), json={
            'prompt': 'Can it game?', 'mode': 'ask', 'api_key': 'test-key',
        }).status_code, 422)
        with patch.object(self.rec, 'llm_chat', new_callable=AsyncMock,
                          return_value='ตอบสั้น') as chat:
            result = asyncio.run(self.rec.answer_spec_question(
                'เล่น Valorant ได้ไหม', 'CPU: Ryzen, GPU: RTX',
                provider='google', model='test-model', api_key='test-key'))
        self.assertEqual(result, 'ตอบสั้น')
        self.assertIn('CPU: Ryzen, GPU: RTX', chat.call_args.args[0][0]['content'])

    def test_compare_session_can_continue_as_a_gpu_build_request(self):
        compared = json.dumps({
            'spec1Name': 'RTX 4060', 'spec2Name': 'RX 7600', 'winner': '1',
            'verdict': 'test', 'categories': [], 'spec1Pros': [],
            'spec2Pros': [], 'recommendation': 'test',
        })
        with patch.object(self.rec, 'compare_specs', new_callable=AsyncMock,
                          return_value=compared):
            first = self.client.post('/api/ai/recommend', headers=self.auth(), json={
                'prompt': 'Spec 1: RTX 4060 | Spec 2: RX 7600',
                'mode': 'compare', 'provider': 'google', 'api_key': 'test-key',
            })
        self.assertEqual(first.status_code, 200)
        sid = first.json()['session_id']

        build = {'summary': '4060 build', 'parts': []}
        with patch.object(self.rec, 'recommend_with_alternatives', new_callable=AsyncMock,
                          return_value=build) as recommend:
            follow_up = self.client.post('/api/ai/recommend', headers=self.auth(), json={
                'prompt': 'จัดสเปกที่ใช้ 4060 มาให้หน่อย', 'mode': 'recommend',
                'session_id': sid, 'provider': 'google', 'api_key': 'test-key',
            })

        self.assertEqual(follow_up.status_code, 200)
        self.assertEqual(follow_up.json()['session_id'], sid)
        self.assertIn('Spec 1: RTX 4060', recommend.call_args.args[1])
        self.assertIn('Current request:\nจัดสเปกที่ใช้ 4060', recommend.call_args.args[1])
        saved = self.client.get(
            f'/api/ai/sessions/{sid}', headers=self.auth()
        ).json()['data']
        self.assertEqual(saved['mode'], 'recommend')

    def test_provider_emojis_are_removed_from_response_and_saved_session(self):
        compared = json.dumps({
            'spec1Name': 'RTX 4060', 'spec2Name': 'RX 7600',
            'winner': '1', 'verdict': 'Fast \U0001f680 and cool \u2744\ufe0f',
            'categories': [], 'spec1Pros': [], 'spec2Pros': [],
            'recommendation': 'Choose RTX 4060 \u2705',
        })
        with patch.object(self.rec, 'compare_specs', new_callable=AsyncMock,
                          return_value=compared):
            response = self.client.post('/api/ai/recommend', headers=self.auth(), json={
                'prompt': 'Spec 1: RTX 4060 | Spec 2: RX 7600', 'mode': 'compare',
                'provider': 'google', 'api_key': 'test-key',
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.json()['data'])['verdict'], 'Fast  and cool ')
        saved = self.client.get(
            f"/api/ai/sessions/{response.json()['session_id']}", headers=self.auth()
        ).json()['data']
        self.assertNotIn('\\u', saved['messages'])

    def test_gpu_model_is_not_mistaken_for_budget_and_is_detected(self):
        self.assertIsNone(self.rec.detect_budget_thb('จัดสเปกที่ใช้ 4060 มาให้หน่อย'))
        self.assertEqual(
            self.rec.detect_requested_gpu(
                'Previous conversation: RTX 4060 vs RX 7600\n\n'
                'Current request:\nจัดสเปกที่ใช้ 4060 มาให้หน่อย'
            ),
            '4060',
        )

    def test_follow_up_budget_overrides_earlier_chat_budget(self):
        context = (
            'Previous conversation:\n'
            'user: จัดสเปกคอมงบ 100000 บาท\n'
            'assistant: ชุดคอมราคา 99450 บาท\n\n'
            'Current request:\nลองจัดสเปกที่ใช้ 4060 งบ 50000 ให้หน่อย'
        )
        self.assertEqual(self.rec.detect_budget_thb(context), 50000)
        self.assertEqual(
            self.rec.detect_budget_thb(context.replace('งบ 50000', 'งบ 30000-50000')),
            50000,
        )
        self.assertFalse(self.rec.budget_is_lower_bound(
            'Previous conversation:\nuser: งบ 100000 บาทขึ้นไป\n\n'
            'Current request:\nจัดสเปกงบ 30000-50000 บาท'
        ))
        self.assertEqual(
            self.rec.detect_budget_thb(
                'Previous conversation:\nuser: จัดสเปกคอมงบ 50000 บาท\n\n'
                'Current request:\nเพิ่ม RAM เป็น 32GB'
            ),
            50000,
        )
        self.assertTrue(self.rec.gpu_name_matches_request(
            'MSI GEFORCE RTX 4060 VENTUS 2X 8G', '4060'
        ))
        self.assertFalse(self.rec.gpu_name_matches_request(
            'MSI GEFORCE RTX 4060 TI VENTUS 2X 8G', '4060'
        ))

    def test_missing_requested_gpu_does_not_return_a_different_model(self):
        response = self.client.post('/api/ai/recommend', headers=self.auth(), json={
            'prompt': 'จัดสเปกที่ใช้ RTX 4060 มาให้หน่อย',
            'mode': 'recommend', 'provider': 'openrouter',
        })
        self.assertEqual(response.status_code, 422)
        self.assertIn('RTX 4060', response.json()['detail'])

    def test_retired_google_model_uses_verified_default(self):
        self.assertEqual(self.api.normalize_ai_model('google', 'gemini-2.5-pro'), 'gemini-3-flash-preview')
        self.assertEqual(self.api.normalize_ai_model('google', 'custom-model'), 'custom-model')
        self.assertEqual(self.api.normalize_ai_model('openai', 'gemini-2.5-pro'), 'gemini-2.5-pro')

    def test_extract_json_accepts_fenced_response_with_trailing_text(self):
        parsed = self.rec.extract_json('Here is the build:\n```json\n{"parts":[{"type":"CPU"}]}\n```\nDone.')
        self.assertEqual(parsed['parts'][0]['type'], 'CPU')

    def test_provider_failure_returns_labelled_build_and_saves_history(self):
        fallback = {'summary': 'catalogue build', 'parts': [], '_meta': {'provider_fallback': True}}
        with patch.object(self.rec, 'recommend_with_alternatives', new_callable=AsyncMock, side_effect=RuntimeError('provider down')):
            with patch.object(self.rec, 'recommend_without_provider', return_value=fallback):
                response = self.client.post('/api/ai/recommend', headers=self.auth(), json={
                    'prompt': 'Budget 30000', 'provider': 'google', 'model': 'gemini-2.5-pro', 'api_key': 'test-key'
                })
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(json.loads(payload['data'])['_meta']['provider_fallback'])
        saved = self.client.get(f"/api/ai/sessions/{payload['session_id']}", headers=self.auth()).json()['data']
        self.assertEqual(len(json.loads(saved['messages'])), 2)
        self.assertEqual(saved['model'], 'gemini-3-flash-preview')

    def test_legacy_fk_migration_preserves_rows(self):
        from sqlalchemy import create_engine, text
        engine=create_engine('sqlite://')
        with engine.begin() as db:
            db.execute(text('CREATE TABLE users (uid TEXT PRIMARY KEY)'))
            db.execute(text("INSERT INTO users VALUES ('alice')"))
            db.execute(text('CREATE TABLE user_ai_settings (uid TEXT PRIMARY KEY, api_key TEXT)'))
            db.execute(text("INSERT INTO user_ai_settings VALUES ('alice', 'test-key')"))
            db.execute(text('CREATE INDEX legacy_ai_idx ON user_ai_settings(uid)'))
        self.api.migrate_ai_foreign_keys(engine)
        self.api.migrate_ai_foreign_keys(engine)
        with engine.connect() as db:
            self.assertEqual(db.execute(text('SELECT api_key FROM user_ai_settings')).scalar(),'test-key')
            self.assertEqual(db.execute(text('PRAGMA foreign_key_list(user_ai_settings)')).first()[2],'users')
            self.assertTrue(db.execute(text("SELECT name FROM sqlite_master WHERE name='legacy_ai_idx'")).first())
        engine.dispose()

    def test_product_power_uses_database_identity(self):
        with self.api.SessionLocal() as db:
            db.add(self.api.Product(product_id='gpu-power-test',p_name='ASUS RTX 5050',category='GPU',specs='Recommended PSU: 650 W',p_price=1))
            db.commit()
        res=self.client.post('/api/compatibility/check-parts',headers=self.auth(),json={'parts':[
            {'category':'CPU','name':'Ryzen 5 5500'},
            {'product_id':'gpu-power-test','name':'RTX 3050','category':'PSU'},
            {'category':'PSU','name':'PSU 450W'}]}).json()['data']
        check=next(c for c in res['checks'] if c['item'].startswith('R3'))
        self.assertEqual(check['required_watt'],650)
        self.assertEqual(res['overall'],'error')
        self.assertTrue(check['sources'])
        self.assertEqual(self.client.post('/api/compatibility/check-parts',headers=self.auth(),json={'parts':[{'product_id':'missing'}]}).status_code,404)

    def test_ai_and_compatibility_actions_require_a_valid_session(self):
        from datetime import datetime, timedelta, timezone
        import jwt

        expired = jwt.encode({
            'uid': 'alice', 'exp': datetime.now(timezone.utc) - timedelta(seconds=1),
            'token_version': 0,
        }, self.api.SECRET_KEY, algorithm=self.api.ALGORITHM)
        revoked = self.api.create_token({'uid': 'alice', 'token_version': -1})
        cases = [
            ('/api/ai/recommend', {'prompt': 'test', 'mode': mode})
            for mode in ('recommend', 'compare', 'compat', 'ask')
        ] + [
            ('/api/compat/check', {'parts_text': 'CPU: Ryzen'}),
            ('/api/compatibility/check', {'parts': []}),
            ('/api/compatibility/check-parts', {'parts': []}),
        ]
        with patch.object(self.rec, 'recommend_with_alternatives', new_callable=AsyncMock) as recommend, \
             patch.object(self.rec, 'compat_check_hybrid', new_callable=AsyncMock) as compat:
            for url, body in cases:
                for token in (None, 'invalid', expired, revoked):
                    with self.subTest(url=url, mode=body.get('mode'), token_type='missing' if token is None else 'unusable'):
                        headers = {'Authorization': f'Bearer {token}'} if token else {}
                        self.assertEqual(self.client.post(url, headers=headers, json=body).status_code, 401)
            recommend.assert_not_awaited()
            compat.assert_not_awaited()
        with patch.object(self.rec, 'compat_check_hybrid', new_callable=AsyncMock, return_value={}) as compat:
            self.assertEqual(self.client.post('/api/compat/check', headers=self.auth(), json={'parts_text': 'CPU: Ryzen'}).status_code, 200)
            compat.assert_awaited_once()
        for url in ('/api/compatibility/check', '/api/compatibility/check-parts'):
            self.assertEqual(self.client.post(url, headers=self.auth(), json={'parts': []}).status_code, 200)

    def test_unknown_provider_rejected(self):
        for url in ('/api/ai/settings', '/api/ai/sessions', '/api/ai/recommend'):
            method = self.client.put if url.endswith('settings') else self.client.post
            self.assertEqual(method(url, headers=self.auth(), json={'provider':'zen','prompt':'test'}).status_code,422)

    def test_provider_http_requests(self):
        import httpx
        for provider,model in [('google','gemini-2.0-flash'),('openai','gpt-4o-mini'),('openai','o1-mini'),('openrouter','custom/model'),('opencode_zen','minimax-m2.5')]:
            response=httpx.Response(200,json={'choices':[{'message':{'content':'ok'}}]})
            fake=AsyncMock()
            fake.__aenter__.return_value=fake
            fake.post.return_value=response
            with patch.object(self.rec.httpx,'AsyncClient',return_value=fake):
                result=asyncio.run(self.rec.llm_chat([{'role':'user','content':'hello'}],provider=provider,model=model,api_key='user-key'))
                self.assertEqual(result,'ok')
                args=fake.post.call_args
                self.assertTrue(args.args[0].startswith(self.rec.PROVIDER_BASE_URLS[provider]))
                self.assertEqual(args.kwargs['headers']['Authorization'],'Bearer user-key')
                self.assertEqual(args.kwargs['json']['model'],model)
                if model=='o1-mini':
                    self.assertIn('max_completion_tokens',args.kwargs['json'])
                    self.assertNotIn('temperature',args.kwargs['json'])

    def test_opencode_zen_settings_and_responses_endpoint(self):
        saved = self.client.put('/api/ai/settings', headers=self.auth(), json={
            'provider': 'opencode_zen', 'model': 'gpt-6-luna', 'api_key': 'zen-test-key',
        })
        self.assertEqual(saved.status_code, 200)
        settings = self.client.get('/api/ai/settings', headers=self.auth()).json()['data']
        self.assertEqual(settings['provider'], 'opencode_zen')
        self.assertEqual(settings['model'], 'gpt-6-luna')

        import httpx
        fake = AsyncMock()
        fake.__aenter__.return_value = fake
        fake.post.return_value = httpx.Response(200, json={
            'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': 'ok'}]}],
        })
        with patch.object(self.rec.httpx, 'AsyncClient', return_value=fake):
            answer = asyncio.run(self.rec.llm_chat(
                [{'role': 'user', 'content': 'hello'}], provider='opencode_zen',
                model='gpt-6-luna', api_key='zen-test-key',
            ))
        self.assertEqual(answer, 'ok')
        args = fake.post.call_args
        self.assertEqual(args.args[0], 'https://opencode.ai/zen/v1/responses')
        self.assertEqual(args.kwargs['headers']['Authorization'], 'Bearer zen-test-key')
        self.assertEqual(args.kwargs['json']['input'][0]['content'], 'hello')
        self.assertIn('max_output_tokens', args.kwargs['json'])
        self.assertNotIn('messages', args.kwargs['json'])

if __name__ == '__main__':
    unittest.main()
````

## backend/verify_access_logs.py

SHA-256 of source file: `e58ebb28b737c1b53ddf153f75732f53e384913356f1dbfe7b915ddbff662db5`

````python
"""Run live Supabase checks without printing keys or request/response content."""

import argparse
import getpass
import os
from pathlib import Path
import time
from urllib.parse import urlsplit
import uuid

from dotenv import load_dotenv
import httpx


def verify(client, base, service_key, anon_key, api_base=None):
    parsed = urlsplit(base)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment or parsed.path):
        raise RuntimeError("SUPABASE_URL must be an HTTPS project origin")
    if not service_key or not anon_key:
        raise RuntimeError("Both service_role and anon keys are required for verification")
    service = {"apikey": service_key, "Authorization": f"Bearer {service_key}"}
    anon = {"apikey": anon_key, "Authorization": f"Bearer {anon_key}"}
    endpoint = base + "/rest/v1/access_logs"
    # A denied request with an invalid key does not prove table permissions.
    if client.get(base + "/auth/v1/settings", headers=anon).status_code != 200:
        raise RuntimeError("Anon key validity check failed; no access-control conclusion")
    if client.get(endpoint, headers=service, params={"select": "id", "limit": "1"}).status_code != 200:
        raise RuntimeError("Service-role table read failed; verify migration and backend key")
    read = client.get(endpoint, headers=anon, params={"select": "id", "limit": "1"})
    write = client.post(endpoint, headers={**anon, "Prefer": "return=minimal"}, json={
        "method": "POST", "path": "/api/auth/anon-permission-test", "status": 401,
        "ip": "203.0.113.100", "user_agent": "anon-permission-test", "user_id": None,
    })
    if read.status_code not in (401, 403) or write.status_code not in (401, 403):
        raise RuntimeError("Anon access is not denied; review privileges and RLS immediately")
    print("PASS: valid anon key cannot read/write access_logs; service_role can read")
    if not api_base:
        return
    parsed_api = urlsplit(api_base)
    if (parsed_api.scheme not in ("http", "https")
            or parsed_api.hostname not in ("localhost", "127.0.0.1", "::1")
            or parsed_api.username or parsed_api.password or parsed_api.query
            or parsed_api.fragment or parsed_api.path):
        raise RuntimeError("--api-base must be a local backend origin")
    marker = "AccessAudit/" + uuid.uuid4().hex
    headers = {"User-Agent": marker}
    responses = [
        client.post(api_base + "/api/login", headers=headers, json={
            "email": uuid.uuid4().hex + "@example.invalid", "password": "synthetic-wrong-password",
        }),
        client.get(api_base + "/api/admin/users", headers=headers),
    ]
    if any(response.status_code != 401 for response in responses):
        raise RuntimeError("Local login/admin did not return expected 401")
    client.get(api_base + "/api/products", headers=headers)
    client.get(api_base + "/products", headers=headers)
    deadline = time.monotonic() + 8
    rows = []
    while time.monotonic() < deadline:
        response = client.get(endpoint, headers=service, params={
            "select": "path,status,ip,user_agent", "user_agent": "eq." + marker,
        })
        if response.status_code != 200:
            raise RuntimeError("Cannot read verification rows with service_role")
        rows = response.json()
        if len(rows) >= 2:
            break
        time.sleep(0.2)
    expected = sorted([("/api/login", 401), ("/api/admin/users", 401)])
    if sorted((row["path"], row["status"]) for row in rows) != expected:
        raise RuntimeError("Expected login/admin rows missing, or an excluded path was recorded")
    if any(not row["ip"] or row["user_agent"] != marker for row in rows):
        raise RuntimeError("IP/User-Agent verification failed")
    print("PASS: real Supabase rows contain login/admin 401, IP and User-Agent; products excluded")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", help="Optional local FastAPI origin, e.g. http://127.0.0.1:3000")
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    base = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    service_key = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
    if not base or not service_key:
        print("NOT VERIFIED: set SUPABASE_URL and SUPABASE_SERVICE_KEY privately")
        return 1
    anon_key = os.getenv("SUPABASE_ANON_KEY", "").strip() or getpass.getpass("Anon key (hidden): ")
    try:
        with httpx.Client(timeout=10.0, follow_redirects=False) as client:
            verify(client, base, service_key, anon_key, args.api_base)
    except (httpx.HTTPError, ValueError, KeyError):
        print("NOT VERIFIED: network or response validation failed; no secrets printed")
        return 1
    except RuntimeError as error:
        print("NOT VERIFIED: " + str(error))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
````

## supabase/migrations/20261002000000_access_logs.sql

SHA-256 of source file: `383a50a1bcd57a5357d93e23b1c449070e01c168be763bc60d3e9ceaa71b1237`

````sql
begin;

create table public.access_logs (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  method text,
  path text,
  status int,
  ip text,
  country text,
  user_agent text,
  user_id text
);
create index access_logs_created_at_idx on public.access_logs (created_at desc);
create index access_logs_ip_idx on public.access_logs (ip);
alter table public.access_logs enable row level security;

-- No policies. Also revoke table/sequence privileges so anon reads fail rather
-- than returning an empty array; only the backend service_role uses REST.
revoke all on table public.access_logs from public, anon, authenticated;
revoke all on sequence public.access_logs_id_seq from public, anon, authenticated;
grant select, insert, delete on table public.access_logs to service_role;
grant usage, select on sequence public.access_logs_id_seq to service_role;

-- Fail this migration rather than silently accepting an insecure table.
do $$
begin
  if not (select relrowsecurity from pg_class
          where oid = 'public.access_logs'::regclass) then
    raise exception 'access_logs must have RLS enabled';
  end if;
  if exists (select 1 from pg_policies
             where schemaname = 'public' and tablename = 'access_logs') then
    raise exception 'access_logs must have no policies';
  end if;
end;
$$;

commit;
````

## docs/access-logging/queries.sql

SHA-256 of source file: `e73f7907effc2efab50a01ead8d88a19996c1ca47f2734f343420fbe19d60777`

````sql
-- Run with Supabase SQL Editor / a trusted administrative connection.

-- RLS must be true; policy_count must be 0.
select c.relrowsecurity as rls_enabled,
       (select count(*) from pg_policies
        where schemaname = 'public' and tablename = 'access_logs') as policy_count
from pg_class c
where c.oid = 'public.access_logs'::regclass;

-- All anon/authenticated privileges below must be false.
select role_name,
       has_table_privilege(role_name, 'public.access_logs', 'SELECT') as can_read,
       has_table_privilege(role_name, 'public.access_logs', 'INSERT') as can_write
from (values ('anon'), ('authenticated')) as roles(role_name);

-- Latest requests.
select id, created_at, method, path, status, ip, country, user_agent, user_id
from public.access_logs
order by created_at desc, id desc
limit 100;

-- IPs with repeated 401/403 responses in the last 7 days.
select ip, count(*) as denied_requests,
       count(*) filter (where status = 401) as unauthorized,
       count(*) filter (where status = 403) as forbidden,
       max(created_at) as last_seen
from public.access_logs
where created_at >= now() - interval '7 days'
  and status in (401, 403)
group by ip
order by denied_requests desc, last_seen desc;

-- Successful admin APIs, including admin actions outside the /api/admin prefix.
select created_at, method, path, status, ip, country, user_agent, user_id
from public.access_logs
where status = 200 and (
  path like '/api/admin/%' or path = '/api/admin'
  or path like '/admin/%' or path = '/admin'
  or path = '/api/spec-history/all'
  or (method = 'POST' and path = '/api/scrape')
  or (method in ('POST', 'PUT', 'PATCH', 'DELETE') and (
    path in ('/api/products', '/api/promotions')
    or path like '/api/products/%' or path like '/api/promotions/%'
  ))
)
order by created_at desc;

-- Retention: execute separately after reviewing the affected count.
select count(*) as older_than_90_days
from public.access_logs where created_at < now() - interval '90 days';
delete from public.access_logs where created_at < now() - interval '90 days';
````

## docs/access-logging/README.md

SHA-256 of source file: `da8dc4f773735ae3f970c20879cb96db0f3f2e76557e6f81cdf5f6f366fcfbe5`

````markdown
# Access logging สำหรับ Railway backend

โค้ดและเอกสารอ้างอิงวันที่ 2 ตุลาคม 2026 ใช้ Supabase project
[`uervyttvxzqsctwyogso`](https://supabase.com/dashboard/project/uervyttvxzqsctwyogso)
เพื่อเก็บ access logs เท่านั้น ข้อมูลหลักและ schema ของ SQLite ไม่เปลี่ยน

## สิ่งที่ทำแล้วและสิ่งที่ยังไม่ได้ยืนยัน

- เพิ่ม `backend/access_log.py` และติดตั้ง middleware หลัง CORS/slowapi ใน `shop_api.py`
- ใช้ `httpx` ที่มีใน requirements อยู่แล้ว ไม่เพิ่ม dependencies
- บันทึกเฉพาะ method, path, status, IP, country, User-Agent และ user ID
- ไม่อ่าน/เก็บ body, query string, incoming Authorization header หรือ cookie
- ใช้ AsyncClient ตัวเดียวต่อ app lifespan, timeout 5 วินาที; ไม่ตาม redirect
- ส่งด้วย `asyncio.create_task`, เก็บ reference ใน set และ discard เมื่อเสร็จ
- ทดสอบด้วย requests/DB ชั่วคราวและ Supabase MockTransport รวมถึง HTTP 401/403/200,
  IP fallback, User-Agent, การตัดความยาว, การไม่บันทึก products และ Supabase ล่ม
- ผลล่าสุด: 62 tests ผ่าน (logging, verifier, routes/ownership และ DB isolation audit)
  และเรียก Uvicorn ผ่าน HTTP จริงกับ SQLite ชั่วคราวผ่าน: รหัสผิด 401, ไม่มี token 401,
  สมาชิกเข้า admin 403, admin 200, products/health 200 แม้ Supabase URL ติดต่อไม่ได้
  server ทดสอบหยุดแล้วและลบ DB/uploads ชั่วคราวแล้ว
- ตรวจ Railway production ผ่านบัญชี CLI เดิมแล้ว: JWT/encryption key มีค่าและรูปแบบถูกต้อง,
  volume `/data` อยู่ในสถานะ READY, DB `/data/shop.db`, uploads `/data/uploads`
  และ `REQUIRE_EXISTING_DB=1` โดยไม่เปิดเผย secret
- ตรวจ Vercel project `recommend` แล้ว: root `It-shop`, Angular, Node 24.x,
  build `npm run build`, output `dist/lt-shop/browser`; production build ผ่าน
  (มี warnings เรื่องขนาด bundle/CSS) และ recommendation regressions เพิ่มอีก 100 tests ผ่าน
- ยังไม่ได้ apply migration, ตรวจ RLS จริง, ทดสอบ anon key จริง หรือตั้ง Supabase variables
  บน Railway เพราะยังไม่มี Supabase connection/credentials;
  `SUPABASE_URL` และ `SUPABASE_SERVICE_KEY` ยังไม่อยู่ใน backend variables ตอนตรวจ
- Dashboard URL ระบุ project ได้ แต่ไม่แทนสิทธิ์เข้าถึงบัญชี
  มี Supabase plugin ให้ติดตั้ง/เชื่อม; หากเชื่อมแล้วสามารถ apply และตรวจต่อได้

## Routes และสิทธิ์ที่ตรวจจาก backend

Routes จริงใช้ `/api/login`, `/api/register` และ `/api/admin/users/...`;
ไม่มี route `/login` หรือ `/admin/...` ใน backend ปัจจุบัน และการเรียกชื่อเหล่านั้นจะได้ 404
ยังเก็บ prefix เหล่านั้นไว้ตามข้อกำหนด เพื่อบันทึกการลองเข้าหรือรองรับ routes ภายหลัง

| กลุ่ม | บันทึก | สิทธิ์ฝั่งเซิร์ฟเวอร์ |
| --- | --- | --- |
| `/admin`, `/api/admin`, `/auth`, `/api/auth`, `/login`, `/api/login`, `/register`, `/api/register` และ paths ที่ขึ้นต้นด้วยค่าเหล่านี้ | ทุก method/status | Login/register เปิดให้สมัคร/ยืนยันตัวตน; admin routes จริงใช้ `require_admin` |
| `/api/profile` และ endpoints ย่อย | ทุก method/status | `get_current_user`; ใช้บัญชีจาก JWT |
| `/api/ai/settings`, `/api/ai/sessions` และ endpoints ย่อย | ทุก method/status | JWT + การกรอง uid เจ้าของ; admin ไม่มีสิทธิ์อ่าน key ของคนอื่นผ่าน owner API |
| `/api/ai/recommend` | ทุก method/status | `get_current_user`; ไม่เปลี่ยน logic AI |
| `/api/spec-history` และ endpoints ย่อย | ทุก method/status | เจ้าของใช้ JWT/uid; `/api/spec-history/all` ต้อง `require_admin` |
| `/api/scrape` และ endpoints ย่อย | ทุก method/status | POST สั่ง scrape ต้อง `require_admin`; GET status เดิมคืนเฉพาะสถิติสินค้า เป็น public |
| `/api/products`, `/api/promotions` และ endpoints ย่อย | เฉพาะ POST/PUT/PATCH/DELETE | Routes ที่มีจริงสำหรับการแก้ข้อมูลใช้ `require_admin` |
| GET products, categories, images, uploads, `/health` และ paths อื่น | ไม่บันทึก | คงสิทธิ์เดิม |

ตรวจแล้วว่า `require_admin` เรียก `get_current_user` และตรวจ role จาก DB
API จัดการผู้ใช้ทั้ง GET list/detail/specs, PUT detail/role และ DELETE มี dependency ครบ
รวมทั้ง GET `/api/spec-history/all`, การแก้สินค้า/โปรโมชั่น และ POST `/api/scrape`
**ไม่มี endpoint ที่ต้องเพิ่ม `require_admin` ใหม่**

ข้อมูลส่วนตัวของเจ้าของใช้ JWT และตรวจ ownership ตามคำยืนยันของผู้ใช้
`get_current_user` เซ็ต `request.state.user_id` หลังตรวจ JWT, ผู้ใช้ และ token_version สำเร็จ
Login สำเร็จเซ็ต uid หลังตรวจรหัสผ่าน การล็อกอินล้มเหลวหรือ token ไม่ถูกต้องไม่อ้าง uid
ลูกค้าที่ล็อกอินแล้วแต่ถูกปฏิเสธ admin ได้ status 403 และ uid ของบัญชีนั้น

## สร้างตารางใน Supabase

เปิด SQL Editor ของ project ที่ระบุและรัน
[`20261002000000_access_logs.sql`](../../supabase/migrations/20261002000000_access_logs.sql)
ครั้งเดียว หากมีตารางอยู่แล้ว ให้ตรวจ schema/สิทธิ์ก่อน ห้ามลบตารางเดิมเพื่อรันซ้ำ

Migration สร้างเฉพาะตาราง/index ใน Supabase, เปิด RLS, **ไม่สร้าง policy**,
revoke สิทธิ์ table/identity sequence จาก PUBLIC, anon และ authenticated
และให้ service_role ใช้อ่าน/เพิ่ม/ลบ log โดยมี assertion ตรวจ RLS และ policy ภายใน transaction
ถ้า assertion ล้มเหลว transaction ไม่ commit การตรวจในไฟล์ยังไม่ใช่ผลตรวจฐานข้อมูลจริง
การใช้ service_role bypass RLS เป็นพฤติกรรมของ Supabase จึงต้องรักษา key ฝั่ง backend
([เอกสาร Supabase](https://supabase.com/docs/guides/database/postgres/row-level-security))

รันส่วนแรกของ [`queries.sql`](queries.sql) หลัง migration ต้องได้
`rls_enabled=true`, `policy_count=0` และ `can_read=false`, `can_write=false`
สำหรับทั้ง anon และ authenticated
ไฟล์เดียวกันมี query ดูล่าสุด, IP ที่ได้ 401/403 ใน 7 วัน,
admin API ที่ตอบ 200 และ SQL ลบเก่ากว่า 90 วัน
ให้รันส่วนลบแยกต่างหากหลังดูจำนวนแถว; ไม่ได้ตั้ง scheduled deletion อัตโนมัติ

## Environment และการ deploy

ใน Railway **backend service เท่านั้น** ตั้ง:

```dotenv
SUPABASE_URL=https://uervyttvxzqsctwyogso.supabase.co
SUPABASE_SERVICE_KEY=<service_role-key-from-this-project>
```

URL เป็นข้อมูล project ไม่ใช่ secret ส่วน key ต้องใช้ `service_role` ของ project นี้
ไม่ใช่ anon/publishable key ห้ามพิมพ์ key ใน terminal/log/report
อย่าวาง key ใน Angular, Vercel, source code หรือ Git
`.env.example` มีชื่อและค่าว่าง; `.gitignore` ignore `.env*` แต่ยกเว้น `.env.example`
JWT/encryption key เดิมยังจำเป็นต่อ startup และต้องคงค่าเดิมของ DB

Backend สร้าง client ใน lifespan ตอน startup ต้อง restart/redeploy หลังตั้ง variables
เมื่อ env ขาด/URL ไม่ถูกต้องจะปิด logging; URL ต้องเป็น HTTPS origin ไม่มี credentials/query
ความผิดพลาดการส่ง Supabase ถูกข้ามเงียบ ๆ และไม่เปลี่ยน HTTP response ของ API
ไม่มี log error ที่อาจพิมพ์ service key

## ตรวจ IP เมื่อผ่าน Vercel

`It-shop/vercel.json` rewrite `/api/:path*` ไป Railway และ production Angular ใช้ same-origin
Vercel ระบุว่า `x-forwarded-for`/`x-real-ip` เป็น public IP ของผู้เรียก
และ `x-vercel-ip-country` เป็นรหัสประเทศ
([เอกสาร request headers](https://vercel.com/docs/headers/request-headers))
External rewrites เป็น reverse proxy
([เอกสาร rewrites](https://vercel.com/kb/guide/vercel-reverse-proxy-rewrites-external))

จากเอกสารคาดว่า IP ผู้ใช้ควรถูกส่งต่อ แต่ **ยังไม่ได้ยืนยัน header chain จริงระหว่าง
Vercel กับ Railway ของ deployment นี้** Railway หรือ proxy อีกชั้นอาจเขียน header ทับ
middleware ทำตามลำดับที่กำหนด: ค่าแรก X-Forwarded-For → X-Real-IP → request.client.host
เมื่อไม่มี country header เก็บ null; ไม่เดาประเทศ

หลัง deploy ให้เทียบ IP ในแถวที่เกิดจาก browser เรียก same-origin `/api/admin/users`
กับ IP ของผู้ใช้ขณะนั้น แล้วเทียบการเรียก Railway โดยตรงจากเครือข่ายเดียวกัน
ทำซ้ำจากอีกเครือข่าย ถ้าทั้งสองเครือข่ายเห็น IP คงที่ของ Vercel ให้ถือว่ายังระบุผู้ใช้ไม่ได้

ทางแก้ที่เลือกได้หากยืนยันว่า IP เป็นของ Vercel:

1. ให้ Angular เรียก Railway URL โดยตรง และตั้ง CORS_ORIGINS สำหรับโดเมน frontend
   วิธีนี้ตัด Vercel rewrite ออกจากเส้นทาง API โดย service key ยังอยู่ backend เท่านั้น
2. ใช้ proxy ที่อ่าน client IP ของ Vercel และส่งต่ออย่างชัดเจน พร้อมจำกัด origin backend
   หรือยืนยัน proxy ด้วย signed header เพื่อป้องกันการปลอมค่า forwarded headers

ยังไม่ได้เปลี่ยน proxy หรือค่าความปลอดภัย/DB/volume ของ production
Forwarded IP/country เป็นข้อมูลที่ proxy อ้าง ไม่ใช่หลักฐานยืนยันตัวตน;
ถ้าเปิด Railway origin ให้เรียกตรง ผู้เรียกอาจปลอม headers ได้

## ทดสอบจริงหลังสร้างตาราง

สำหรับ local ให้ตั้ง variables อย่างเป็นส่วนตัวและเริ่ม backend กับ DB/uploads ชั่วคราว
ตาม README หลัก ห้ามใช้ DB จริงสำหรับการทดสอบนี้
จากรากโปรเจกต์รัน:

```powershell
.\venv\Scripts\python.exe -B backend\verify_access_logs.py --api-base http://127.0.0.1:3000
```

สคริปต์อ่าน URL/service key จาก environment หรือ root `.env`
และถาม anon key แบบซ่อน input (หรืออ่าน `SUPABASE_ANON_KEY` เฉพาะ process ทดสอบ)
ตรวจว่า anon key ใช้ได้จริงผ่าน `/auth/v1/settings` ก่อนทดสอบสิทธิ์ตาราง
แล้วตรวจว่า service_role อ่านได้ ส่วน anon อ่าน/เขียนต้องได้ 401/403
ถ้าตารางไม่ปลอดภัย อาจมีแถวสังเคราะห์ `anon-permission-test` ถูกเพิ่มจากการทดสอบเขียน
ให้แก้สิทธิ์และลบเฉพาะแถวนั้นผ่าน SQL Editor

เมื่อมี `--api-base` จะเรียก `/api/login` ด้วยบัญชีสังเคราะห์ที่ไม่มีอยู่และ `/api/admin/users`
โดยไม่มี token แล้วรอ log ไม่เกิน 8 วินาที ตรวจว่ามี 401, IP และ User-Agent ที่ตรง marker
และไม่มีแถว products จาก marker เดียวกัน ไม่พิมพ์ key หรือข้อมูล response
ไม่ใส่ `--api-base` จะตรวจสิทธิ์ Supabase อย่างเดียว

ตรวจเพิ่มใน browser หลัง deploy:

- เข้า login ด้วยรหัสผิด: log `/api/login` ต้องมี 401
- ไม่ล็อกอินเรียก `/api/admin/users`: 401, user_id null
- สมาชิกเรียก `/api/admin/users`: 403, user_id สมาชิก
- Admin เรียก `/api/admin/users`: 200, user_id admin
- Profile/settings/sessions/history ของเจ้าของยังใช้ได้ และเข้าถึงของคนอื่นไม่ได้
- เรียก products: ไม่ควรมีแถว log
- ทดสอบ local ด้วย `SUPABASE_URL=https://unreachable.invalid`: API ยังตอบตามสิทธิ์เดิม

## ข้อจำกัดของการส่งเบื้องหลัง

Fire-and-forget ไม่รับประกันว่าเก็บครบทุก request: process ถูก kill, Supabase ล่ม,
หรือมี task ค้างครบ 256 รายการ จะข้าม log โดยไม่รบกวน API
ตอน shutdown รอ task ไม่เกิน 5 วินาที จากนั้น cancel และปิด client
ไม่มี retry/persistent queue และไม่เก็บสำเนาใน SQLite
หลัง deploy จึงต้องตรวจว่ามีแถวจริงเข้าตาราง ไม่ใช่ดูเพียงว่า API ยังตอบได้

## ส่งมอบไฟล์ฉบับเต็ม

[`full-files.md`](full-files.md) เป็น snapshot เนื้อหาทุกไฟล์ที่เพิ่ม/แก้สำหรับงานนี้
ทั้งไฟล์ รวม `shop_api.py` ฉบับเต็ม ไม่ใช่ diff (ไม่รวม snapshot ตัวมันเองเพื่อไม่ให้วนซ้ำ)
ไฟล์ที่เปลี่ยนในงานก่อนหน้ายังคงอยู่และไม่ได้ย้อนการแก้เหล่านั้น
````
