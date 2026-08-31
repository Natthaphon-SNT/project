# ⚡ IT-RECOMMEND — ระบบแนะนำและจัดสเปคคอมพิวเตอร์เปรียบเทียบ 3 ร้าน

> **เว็บแอปพลิเคชันจัดสเปคคอมพิวเตอร์อัจฉริยะ เปรียบเทียบราคาจริงแบบ Real-time จาก 3 ร้านค้าไอทีชั้นนำของไทย (Advice, JIB, iHaveCPU) พร้อมระบบ AI แนะนำสเปคแบบ Hybrid RAG และระบบตรวจเช็คความเข้ากันได้แบบ Deterministic 100%**

---

## 🌟 จุดเด่นของระบบ (Key Highlights & Value Proposition)

1. **Zero-Hallucination Pricing & Links (ราคาและลิงก์จริง 100%):**
   - ราคาและสินค้าทุกชิ้นมาจาก **ฐานข้อมูลจริงที่ดึงจากหน้าร้านค้าไทย**
   - ไม่มีปัญหา AI คิดราคาขึ้นมาเอง หรือให้ลิงก์สั่งซื้อปลอม
2. **Cross-Store 3-Store Matrix & Arbitrage (เปรียบเทียบราคา 3 ร้าน):**
   - เปรียบเทียบราคาสินค้าชิ้นต่อชิ้นระหว่าง **Advice**, **JIB**, และ **iHaveCPU**
   - คำนวณราคารวมของแต่ละร้าน และคำนวณราคาแบบ **"Mixed Best" (ซื้อแยกชิ้นที่ถูกที่สุด)** เพื่อประหยัดเงินสูงสุด
   - มี **ปุ่มลิงก์ตรง (Direct Buy Link)** ไปยังหน้าสินค้าของแต่ละร้านทันที
3. **Deterministic Compatibility Engine (ตรวจความเข้ากันได้ระดับโค้ด):**
   - ตรวจสอบความเข้ากันได้ของชิ้นส่วนแบบ Real-time (Socket CPU ↔ Mainboard, RAM DDR Gen, PSU Wattage, Cooler TDP)
   - แจ้งเตือนข้อผิดพลาดทันทีในหน้าจัดสเปกด้วยแถบเตือนสีแดง/เหลือง/เขียว พร้อมวิธีแก้ไข
4. **SmartMatcher Deduplication Engine:**
   - รวมสินค้าตัวเดียวกันที่มีชื่อต่างกันข้าม 3 ร้านค้า ให้เป็น 1 รายการโดยอัตโนมัติ พร้อมสเปกและรูปภาพความละเอียดสูง
5. **Spec History & Sharing (`/history`):**
   - บันทึกสเปกที่จัดเองหรือสเปกที่ AI แนะนำ พร้อมตารางสรุป 3 ร้านและลิงก์สั่งซื้อย้อนหลัง

---

## 🏗️ สถาปัตยกรรมระบบ (System Architecture)

```
                            ┌──────────────────────────────────────────────┐
                            │               USER INTERFACE                 │
                            │         Angular 17 / SCSS / TypeScript       │
                            └──────────────────────┬───────────────────────┘
                                                   │
                         ┌─────────────────────────┴─────────────────────────┐
                         │                                                   │
                         ▼ (HTTP REST API)                                   ▼
┌─────────────────────────────────────────────────────────┐   ┌─────────────────────────────────────┐
│ 1. PC BUILDER & INTERACTIVE CATALOG                    │   │ 2. AI RECOMMENDATION (Hybrid RAG)   │
│  - เลือก Component 8 ชิ้น                               │   │  - Intent & Budget Extraction       │
│  - Real-time 3-Store Price Calculation                 │   │  - Candidate Retrieval จาก DB       │
│  - คำนวณ Best Store / Mixed Savings                     │   │  - OpenCode Zen LLM Reasoning       │
│  - บันทึกประวัติสเปกลง /api/spec-history                │   │  - Natural Language Explanations    │
└────────────────────────┬────────────────────────────────┘   └──────────────────┬──────────────────┘
                         │                                                       │
                         ▼                                                       ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 3. DETERMINISTIC COMPATIBILITY ENGINE (Backend Validation)                                        │
│  - spec_parser.py: สกัด Socket, DDR, Form Factor, Wattage ด้วย Rule & Regex                      │
│  - compat_engine.py: รัน Deterministic Checks (R1 Socket, R2 DDR, R3 PSU Watt, R5 Form Factor)     │
│  - rules/*.md: Domain Rules Knowledge Base สำหรับตรวจสอบความถูกต้อง                                │
└────────────────────────────────────────────────┬──────────────────────────────────────────────────┘
                                                 │
                                                 ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────┐
│ 4. DATABASE & SCRAPER ENGINE (shop.db SQLite)                                                     │
│  - full_scraper.py / scraper.py: Playwright Auto-Scraper ดึง Advice, JIB, iHaveCPU                 │
│  - SmartMatcher: Multi-level Token Matching รวมสินค้าตัวเดียวกันข้าม 3 ร้าน                         │
│  - Direct URLs, High-Res CDN/S3 Images, Real Specs                                                │
└───────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📂 โครงสร้างโปรเจกต์ (Project Directory Structure)

```text
Project/
├── backend/                  # FastAPI (Python) Backend & AI Services
│   ├── shop_api.py           # REST API Server หลัก (Auth, Products, Orders, Builder, History)
│   ├── recommender.py        # Hybrid RAG pipeline (OpenCode Zen LLM + Post-validation)
│   ├── compat_engine.py      # Deterministic Compatibility Rule Engine
│   ├── spec_parser.py        # Regex Hardware Spec Parser (Socket, DDR, Wattage, TDP)
│   ├── full_scraper.py       # Full Scraper ดึงข้อมูล Advice, JIB, iHaveCPU + SmartMatcher
│   ├── scraper.py            # Quick Scraper สำหรับอัปเดตราคาสินค้า
│   ├── rules/                # Markdown Rule Knowledge Base
│   │   ├── cpu_socket_rules.md
│   │   ├── ram_rules.md
│   │   ├── psu_rules.md
│   │   └── cooler_rules.md
│   └── shop.db               # ฐานข้อมูล SQLite (สินค้า, ผู้ใช้, ออเดอร์, ประวัติสเปก)
│
├── It-shop/                  # Angular 17 Frontend Web Application
│   ├── src/app/
│   │   ├── pages/
│   │   │   ├── home/         # หน้าแรก (Hero, Flash Sale, Featured Specs)
│   │   │   ├── products/     # หน้ารวมสินค้า ค้นหา และกรองตามหมวดหมู่
│   │   │   ├── product-detail/# หน้ารายละเอียดสินค้า พร้อมตารางราคา 3 ร้าน
│   │   │   ├── pc-builder/   # หน้าจัดสเปกเอง + Real-time Compatibility Warning + สรุป 3 ร้าน
│   │   │   ├── ai-recommend/ # หน้า AI จัดสเปก (แนะนำ / เปรียบเทียบ / เช็คความเข้ากัน)
│   │   │   ├── history/      # หน้าประวัติการจัดสเปก (แยก 3 ร้าน + ลิงก์ตรงสั่งซื้อ)
│   │   │   ├── cart/         # ตะกร้าสินค้า
│   │   │   ├── checkout/     # ยืนยันการสั่งซื้อ
│   │   │   ├── profile/      # ข้อมูลผู้ใช้และประวัติคำสั่งซื้อ
│   │   │   └── admin/        # หน้าจัดการสินค้า ออเดอร์ และผู้ใช้สำหรับ Admin
│   │   ├── services/         # Angular Services (Auth, Cart, API, Spec)
│   │   └── guards/           # Route Guards (AuthGuard, AdminGuard)
│
├── .env                      # Environment Variables (API Keys, Zen LLM)
├── start_backend.bat         # สคริปต์รัน Backend อย่างรวดเร็ว
└── README.md                 # เอกสารโปรเจกต์
```

---

## 🛠️ เทคโนโลยีที่ใช้ (Tech Stack)

| ส่วนของระบบ | เทคโนโลยีที่ใช้ | เวอร์ชัน / รายละเอียด |
| :--- | :--- | :--- |
| **Frontend** | Angular (Standalone Components) | Angular 17+, TypeScript, SCSS, RxJS |
| **Backend** | Python FastAPI | FastAPI, Uvicorn, SQLite3, SQLAlchemy |
| **AI Engine** | OpenCode Zen Gateway / Hybrid RAG | `x-preview-f-free` / OpenCode Zen API |
| **Scraper** | Playwright (Async Python) | Headless Chromium, Anti-bot bypass, CDN/S3 parser |
| **Security** | JWT + BCrypt | JSON Web Token Authentication, Bcrypt Password Hash |
| **Ports** | Frontend: `4200` | Backend: `3000` |

---

## 🚀 การติดตั้งและเริ่มใช้งาน (Installation & Setup)

### ข้อกำหนดเบื้องต้น (Prerequisites)
- **Python:** 3.10 ขึ้นไป
- **Node.js:** 18 ขึ้นไป + npm
- **Angular CLI:** `npm install -g @angular/cli`

---

### 1. ตั้งค่าและรัน Backend (FastAPI)

```powershell
# 1. เข้าไปที่โฟลเดอร์ Project
cd "d:\year 4 term 1\Project"

# 2. ติดตั้ง Python Dependencies (หากยังไม่ได้ติดตั้ง)
.\venv\Scripts\python.exe -m pip install fastapi uvicorn sqlalchemy bcrypt pyjwt httpx python-multipart playwright --no-color

# 3. รัน Backend API Server
cd backend
..\venv\Scripts\uvicorn.exe shop_api:app --reload --port 3000 --host 0.0.0.0
```

> 🌐 **Backend API:** `http://localhost:3000`  
> 📖 **Interactive API Docs (Swagger):** `http://localhost:3000/docs`

---

### 2. ตั้งค่าและรัน Frontend (Angular)

```powershell
# 1. เข้าไปที่โฟลเดอร์ It-shop
cd "d:\year 4 term 1\Project\It-shop"

# 2. ติดตั้ง Node Dependencies (ครั้งแรก)
npm install

# 3. รัน Angular Development Server
ng serve --port 4200 --open
```

> 💻 **Frontend Web App:** `http://localhost:4200`

---

### 3. การรัน Scraper เพื่ออัปเดตข้อมูลสินค้าจาก 3 ร้าน (Optional)

```powershell
cd "d:\year 4 term 1\Project\backend"

# รัน Full Scraper ครอบคลุม 3 ร้าน (Advice, JIB, iHaveCPU)
python full_scraper.py --pages 3

# หรือรันดึงแบบละเอียดพร้อมคำอธิบาย (Fetch Details)
python full_scraper.py --pages 2 --details
```

---

## 🔑 บัญชีทดสอบระบบ (Test Accounts)

| บทบาท (Role) | Email | Password | สิทธิ์การใช้งาน |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@itrecommend.com` | `admin1234` | จัดการสินค้า, ออเดอร์, เปลี่ยนสถานะ, จัดการสมาชิก |
| **User ทั่วไป** | สมัครใหม่ผ่านหน้า `/register` | ตามที่ตั้ง | จัดสเปก, ใช้งาน AI, บันทึกประวัติ, สั่งซื้อสินค้า |

---

## 🧭 แผนผังหน้าเว็บไซต์ (Route Map)

| เส้นทาง (URL) | หน้าเว็บ | ฟังก์ชันการทำงาน |
| :--- | :--- | :--- |
| `/` | หน้าแรก (Home) | แบนเนอร์, สินค้าราคาพิเศษ, สเปกแนะนำยอดนิยม |
| `/products` | สินค้าทั้งหมด | ค้นหา, กรองราคา, เลือกดูเปรียบเทียบ 3 ร้าน |
| `/category/:type` | สินค้าแยกตามหมวด | แยกหมวด CPU, GPU, Mainboard, RAM, SSD, PSU, Case, Cooler ฯลฯ |
| `/product/:id` | หน้ารายละเอียดสินค้า | สเปกละเอียด, รูปภาพ High-Res, ตารางเปรียบเทียบราคา Advice / JIB / iHaveCPU พร้อมปุ่มกดซื้อ |
| `/pc-builder` | **🛠️ จัดสเปกเอง** | เลือก 8 ชิ้นส่วน, **ตรวจ Compatibility แบบ Real-time**, กล่องสรุป 3 ร้าน, บันทึกลงประวัติ |
| `/ai-recommend` | **🤖 AI จัดสเปก** | แนะนำสเปกตามงบ, เปรียบเทียบสเปก 2 ชุด, เช็คความเข้ากันได้ด้วย AI |
| `/history` | **📜 ประวัติการจัดสเปก** | ดูสเปกที่เคยจัด, ดูสรุปราคารวม 3 ร้าน, ลิงก์ตรงสั่งซื้อแต่ละชิ้น |
| `/cart` | ตะกร้าสินค้า | สรุปสินค้าที่เลือกสั่งซื้อ |
| `/checkout` | สั่งซื้อสินค้า | กรอกที่อยู่จัดส่ง และเลือกวิธีชำระเงิน |
| `/profile` | โปรไฟล์ของฉัน | แก้ไขข้อมูลส่วนตัว, ดูประวัติคำสั่งซื้อ |
| `/admin/products` | จัดการสินค้า (Admin) | เพิ่ม, แก้ไข, ลบรายการสินค้า |
| `/admin/orders` | จัดการออเดอร์ (Admin) | ดูรายการสั่งซื้อ, เปลี่ยนสถานะ (รอดำเนินการ → จัดส่งแล้ว → สำเร็จ) |
| `/admin/users` | จัดการผู้ใช้ (Admin) | ดูรายชื่อสมาชิก, กำหนดสิทธิ์ Admin |

---

## 📡 REST API Reference

### 1. Authentication & Users
- `POST /api/register` — สมัครสมาชิกใหม่
- `POST /api/login` — เข้าสู่ระบบ รับ JWT Token
- `GET /api/profile` — ข้อมูลโปรไฟล์ผู้ใช้
- `PUT /api/profile` — แก้ไขข้อมูลส่วนตัว
- `PUT /api/profile/password` — เปลี่ยนรหัสผ่าน

### 2. Products & Pricing
- `GET /api/products` — ดึงรายการสินค้าทั้งหมด (รองรับ `category`, `search`, `page`, `limit`)
- `GET /api/products/{id}` — รายละเอียดสินค้า พร้อมราคา 3 ร้านและลิงก์ตรง
- `POST /api/products` — เพิ่มสินค้าใหม่ (Admin)
- `PUT /api/products/{id}` — แก้ไขสินค้า (Admin)
- `DELETE /api/products/{id}` — ลบสินค้า (Admin)

### 3. PC Builder & Compatibility
- `POST /api/compatibility/check` — ตรวจสอบความเข้ากันได้ของชิ้นส่วน (Deterministic Engine)
- `POST /api/compatibility/check-parts` — ตรวจสอบชิ้นส่วนจากหน้า PC Builder แบบ Real-time
- `GET /api/spec-history` — ดึงประวัติการจัดสเปกของผู้ใช้
- `POST /api/spec-history` — บันทึกสเปกที่จัดเองหรือสเปกจาก AI
- `DELETE /api/spec-history/{id}` — ลบประวัติสเปก

### 4. AI Recommend & Chat
- `POST /api/ai/recommend` — ส่ง prompt จัดสเปก / เปรียบเทียบ / ตรวจสอบความเข้ากันได้ผ่าน OpenCode Zen

### 5. Orders
- `POST /api/orders` — สร้างคำสั่งซื้อ
- `GET /api/orders/my` — ดึงออเดอร์ของผู้ใช้ปัจจุบัน
- `GET /api/orders` — ดึงออเดอร์ทั้งหมด (Admin)
- `PUT /api/orders/{id}/status` — เปลี่ยนสถานะออเดอร์ (Admin)

---

## 🛡️ กฎความเข้ากันได้ของฮาร์ดแวร์ (Hardware Compatibility Rules)

ระบบใช้ **Deterministic Rule Engine** ร่วมกับไฟล์ Markdown Rule Knowledge Base:
- **R1 (CPU ↔ Mainboard Socket):** ตรวจสอบ Socket ตรงกัน 100% (เช่น Intel LGA1700, LGA1851, AMD AM4, AM5)
- **R2 (RAM ↔ Mainboard DDR Generation):** ตรวจสอบ DDR4 / DDR5 ให้ตรงกับที่เมนบอร์ดรองรับ
- **R3 (PSU Wattage Calculation):** คำนวณ Total System TDP (CPU TDP + GPU TDP + 100W Base System) × 1.25 Headroom และเทียบกับขนาดกำลังวัตต์ของพาวเวอร์ซัพพลาย
- **R4 (Cooler TDP & Socket Support):** ตรวจสอบว่าพัดลม/ชุดน้ำรองรับ Socket ของ CPU และระบายความร้อนได้เพียงพอ
- **R5 (Case & Motherboard Form Factor):** ตรวจสอบขนาดเคส (ATX, Micro-ATX, Mini-ITX) ว่าใส่เมนบอร์ดได้

---

## 👥 ผู้พัฒนา (Developers)

- **โครงงานระบบแนะนำและจัดสเปคคอมพิวเตอร์เปรียบเทียบ 3 ร้าน (IT-RECOMMEND)**
- ภาควิชาวิทยาการคอมพิวเตอร์ / วิศวกรรมคอมพิวเตอร์ (Year 4 Project)
