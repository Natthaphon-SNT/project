# IT-RECOMMEND — ระบบแนะนำและจัดสเปกคอมพิวเตอร์

เว็บแอปพลิเคชันสำหรับค้นหาอุปกรณ์ เปรียบเทียบราคา Advice, JIB และ iHaveCPU จัดสเปกด้วยตนเอง หรือขอคำแนะนำจาก AI โดยใช้รายการสินค้าและราคาในฐานข้อมูลร่วมกับกฎตรวจสอบฮาร์ดแวร์

เอกสารนี้อ้างอิงโค้ดปัจจุบัน ณ วันที่ 12 กันยายน 2026 ระบบหลักคือ `It-shop/` และ `backend/shop_api.py`

## ความสามารถปัจจุบัน

- ค้นหาและกรองสินค้า ดูรายละเอียด รูปภาพ ราคาและลิงก์ร้านค้า รวมถึงประวัติราคาที่บันทึกไว้
- จัดสเปกด้วยตนเองผ่าน PC Builder ตรวจความเข้ากันได้ สรุปราคา และบันทึกประวัติสเปก
- ใช้ AI ใน 3 โหมด: แนะนำสเปก (`recommend`), เปรียบเทียบสเปก (`compare`) และตรวจความเข้ากันได้ (`compat`)
- เลือกผู้ให้บริการ AI ได้ระหว่าง Google, OpenAI และ OpenRouter พร้อมระบุ model ID เอง
- ผู้เยี่ยมชมใช้หน้า AI ได้ ส่วนสมาชิกบันทึกการตั้งค่า AI และจัดการหลายบทสนทนาได้
- สมัครสมาชิก เข้าสู่ระบบด้วย JWT แก้ไขโปรไฟล์ เปลี่ยนรหัสผ่าน และอัปโหลดรูปโปรไฟล์
- ผู้ดูแลระบบจัดการสินค้า สมาชิก และเรียกอัปเดตข้อมูลผ่าน scraper ได้

ราคาที่แสดงเป็นข้อมูลจากการดึงข้อมูลครั้งล่าสุด ไม่ใช่ราคาสดทุกครั้งที่เปิดหน้าเว็บ สินค้าบางรายการอาจมีข้อมูลเพียงบางร้าน ความครบถ้วนของสเปกและข้อมูลต้นทางมีผลต่อผลตรวจความเข้ากันได้ ซึ่งอาจแสดง `UNKNOWN` เมื่อยังยืนยันไม่ได้

## เทคโนโลยีและโครงสร้าง

| ส่วน | เทคโนโลยี / ไฟล์หลัก |
| --- | --- |
| Frontend | Angular 21.1, TypeScript 5.9, SCSS, Tailwind CSS 4 |
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
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\venv\Scripts\python.exe -m pip install python-dotenv
npm --prefix It-shop ci
```

ปัจจุบัน `shop_api.py` ใช้ `python-dotenv` แต่แพ็กเกจนี้ยังไม่ได้อยู่ใน `backend/requirements.txt` จึงต้องติดตั้งเพิ่มตามคำสั่งข้างต้น

หากต้องใช้ scraper หรือทดสอบส่วนที่ใช้ Playwright ให้ติดตั้งเพิ่ม:

```powershell
.\venv\Scripts\python.exe -m pip install playwright
.\venv\Scripts\python.exe -m playwright install chromium
```

### 2. ตั้งค่าเซิร์ฟเวอร์

สร้างหรือแก้ไข `.env` ที่รากโปรเจกต์ โดยรักษาค่าที่ตั้งไว้เดิม ตัวอย่างนี้แสดงเฉพาะ placeholder:

```dotenv
JWT_SECRET=replace-with-a-random-secret-of-at-least-32-bytes

# เลือกตั้งค่าเฉพาะผู้ให้บริการที่ต้องการใช้
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
GOOGLE_API_KEY=
GOOGLE_MODEL=gemini-2.0-flash
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openai/gpt-4o-mini
```

ชื่อโมเดลข้างต้นเป็นค่าเริ่มต้นในโค้ด ต้องเลือกโมเดลที่บัญชีผู้ให้บริการของคุณเรียกใช้งานได้ Google รองรับ `GEMINI_API_KEY` เป็นค่าแทน `GOOGLE_API_KEY` ด้วย

ระบบเลือกผู้ให้บริการเริ่มต้นจาก key ฝั่งเซิร์ฟเวอร์ตามลำดับ OpenAI → Google → OpenRouter หากไม่มี key จะใช้ Google เป็นค่าเริ่มต้น สมาชิกตั้งค่า provider, model, custom model และ key ของตนเองได้ในหน้า AI โดย custom model มีลำดับความสำคัญเหนือโมเดลที่เลือกจากรายการ

เมื่อส่งคำขอ AI ระบบใช้ key ที่ส่งมากับคำขอ ตามด้วย key ที่สมาชิกบันทึกไว้สำหรับ provider เดียวกัน และ key ฝั่งเซิร์ฟเวอร์ หากไม่มี key จะตอบ HTTP 400 การเปลี่ยน `.env` ต้องเริ่ม backend ใหม่

การตั้งค่า key ของสมาชิกถูกเก็บเป็นข้อความธรรมดาใน SQLite ตาม implementation ปัจจุบัน ส่วน browser ไม่เก็บ AI key ใน localStorage การตั้งค่าของผู้เยี่ยมชมอยู่ใน component ชั่วคราว จึงควรเก็บ `.env` และฐานข้อมูลที่มี key เป็นข้อมูลส่วนตัว

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

**ต้องเริ่ม backend จากโฟลเดอร์ `backend`** เนื่องจาก `shop_api.py` ใช้เส้นทางฐานข้อมูล `sqlite:///./shop.db` และโฟลเดอร์ `uploads/profile` อิง working directory การรันผิดโฟลเดอร์อาจไปใช้ `shop.db` คนละไฟล์ หากเปลี่ยน URL ของ backend ต้องปรับทั้ง `It-shop/src/app/services/api.ts` และ `It-shop/src/app/services/auth.ts` ซึ่งตั้งไว้เป็น `http://localhost:3000`

## หน้าที่มีใน Frontend

| เส้นทาง | การใช้งาน | สิทธิ์ |
| --- | --- | --- |
| `/` | หน้าแรก | สาธารณะ |
| `/login`, `/register` | เข้าสู่ระบบและสมัครสมาชิก | สาธารณะ |
| `/ai-recommend` | AI และการตั้งค่าบทสนทนา | เปิดหน้าได้โดยไม่ล็อกอิน; การบันทึกต้องเป็นสมาชิก |
| `/products`, `/category/:type` | ค้นหาและดูสินค้าตามหมวด | สมาชิก |
| `/product/:id` | รายละเอียดและเปรียบเทียบราคา | สมาชิก |
| `/pc-builder` | จัดสเปกด้วยตนเอง | สมาชิก |
| `/history` | ประวัติสเปก | สมาชิก |
| `/profile` | โปรไฟล์ | สมาชิก |
| `/admin/products` | จัดการสินค้า | ผู้ดูแล |
| `/admin/users` | จัดการสมาชิก | ผู้ดูแล |

Backend ยังมี API คำสั่งซื้อและโปรโมชั่น แต่ router ของ `It-shop` ปัจจุบันไม่มีหน้า `/cart`, `/checkout` หรือ `/admin/orders`

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
| คำสั่งซื้อ | `GET/POST /api/orders`, `GET /api/orders/my`, `GET /api/orders/{order_id}`, `PUT /api/orders/{order_id}/status` |

`GET /api/products` รองรับ `category`, `cid`, `search` และ `name` ปัจจุบันยังไม่มี pagination parameters

## การทำงานของ AI และการตรวจสเปก

`recommender.py` วิเคราะห์งบและลักษณะงาน ดึงรายการสินค้าจากฐานข้อมูลเป็นตัวเลือก แล้วให้โมเดลช่วยเลือกและอธิบายผล ระบบนำผลกลับมาจับคู่กับสินค้า คำนวณราคา และตรวจสอบด้วย `compat_engine.py` ร่วมกับ `spec_parser.py` และความรู้ใน `backend/rules/`

กฎตรวจสอบครอบคลุม socket CPU/เมนบอร์ด, DDR ของ RAM, กำลังไฟ PSU, เงื่อนไข GPU ระดับสูงและหัวต่อไฟ, กำลังระบายความร้อน, ขนาดเมนบอร์ดกับเคส และงบประมาณ โดยเกณฑ์ PSU พิจารณาทั้งค่าที่ผู้ผลิต GPU แนะนำและค่าประมาณ `(CPU + GPU + 80W) × 1.25` ผลลัพธ์อาศัยข้อมูลสเปกที่มีและอาจยังยืนยันไม่ได้เมื่อข้อมูลไม่ครบ

บทสนทนาของสมาชิกผูกกับผู้ใช้และตรวจสิทธิ์ก่อนเข้าถึง สามารถสร้าง เปิด เปลี่ยนชื่อ และลบได้ รายการบทสนทนาคืนล่าสุดไม่เกิน 100 รายการ ระบบเลิกใช้ Zen แล้ว และ migration เปลี่ยนการตั้งค่า Zen เดิมเป็น Google พร้อมล้าง key และ custom model โดยยังอ่านบทสนทนาเก่าได้

## อัปเดตข้อมูลสินค้า

ติดตั้ง Playwright และ Chromium ตามขั้นตอนด้านบน แล้วรันจาก `backend`:

```powershell
# ดึง listing จากทั้ง 3 ร้าน จำกัดจำนวนหน้าต่อหมวด
..\venv\Scripts\python.exe full_scraper.py --stores all --pages 3

# ดึงรายละเอียดสินค้าจากร้านที่เลือกด้วย
..\venv\Scripts\python.exe full_scraper.py --stores jib ihavecpu --pages 3 --details

# เติมรายละเอียดที่ขาดจาก URL ที่มีในฐานข้อมูล
..\venv\Scripts\python.exe full_scraper.py --backfill-only
```

คำสั่งเหล่านี้เขียนข้อมูลลง `backend/shop.db` ควรสำรองฐานข้อมูลก่อนรันงานปรับข้อมูลจำนวนมาก จำนวนสินค้าที่ดึงได้ขึ้นอยู่กับหน้าเว็บต้นทาง การแบ่งหน้า และการตอบสนองของแต่ละร้าน

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

# ทดสอบกฎกำลังไฟและความรู้สำหรับคำแนะนำ
.\venv\Scripts\python.exe -B backend\test_power_compatibility.py
.\venv\Scripts\python.exe -B backend\test_recommender_knowledge.py

# ทดสอบการจับคู่สินค้าและข้อมูลต้นทางของ scraper
.\venv\Scripts\python.exe -B backend\test_product_matching.py
.\venv\Scripts\python.exe -B backend\test_scraper_source_data.py
```

ชุดทดสอบ AI sessions ใช้ฐานข้อมูลชั่วคราวและ mock การเรียกผู้ให้บริการ ส่วนไฟล์ `test_*.py` อื่นบางไฟล์เป็นสคริปต์ตรวจเว็บจริง จึงควรอ่านก่อนรัน ไม่ควรรันทุกไฟล์รวมกันโดยสมมติว่าเป็น unit test ทั้งหมด

## แก้ปัญหาเบื้องต้น

| อาการ | จุดที่ควรตรวจ |
| --- | --- |
| `No module named dotenv` | ติดตั้ง `python-dotenv` ด้วย Python ใน `venv` |
| Playwright หา browser ไม่พบ | รัน `python -m playwright install chromium` ด้วย Python ใน `venv` |
| `no such table` หรือสินค้าไม่ตรงกับที่เคยมี | ตรวจว่าเปิด backend จาก `backend/` และใช้ฐานข้อมูลถูกไฟล์; ฐานข้อมูลใหม่ต้องรัน `init_db.py` ก่อน |
| Frontend ติดต่อ API ไม่ได้ | ตรวจพอร์ต 3000 และ `baseUrl` ในทั้งสอง service |
| AI ตอบ HTTP 400 เรื่อง key | ตั้ง key ของ provider ที่เลือกในหน้า AI หรือ `.env` |
| AI ตอบ HTTP 502 | ตรวจ model ID, API key และโควตาของผู้ให้บริการ |
| เข้า `/admin/products` หรือ `/admin/users` ไม่ได้ | ตรวจ role ของบัญชีและเข้าสู่ระบบใหม่หลังเปลี่ยนสิทธิ์ |
