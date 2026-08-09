# IT-RECOMMEND — ระบบแนะนำและจัดสเปคคอมพิวเตอร์

ระบบเว็บแอปพลิเคชันสำหรับเปรียบเทียบราคาสินค้า IT จัดสเปคคอมพิวเตอร์ และใช้ AI แนะนำสเปคที่เหมาะสมกับงบประมาณและการใช้งาน

---

## สถาปัตยกรรมระบบ

```
IT-RECOMMEND/
├── backend/          # FastAPI (Python) — REST API + SQLite
│   ├── shop_api.py   # ไฟล์หลักของ API ทั้งหมด
│   ├── shop.db       # ฐานข้อมูล SQLite
│   └── scraper.py    # ดึงข้อมูลสินค้าจากเว็บร้านค้า
└── It-shop/          # Angular 17 (TypeScript) — Frontend
    └── src/app/
        ├── pages/    # หน้าต่างๆ
        ├── services/ # Services (Auth, Cart, API)
        ├── guards/   # Route Guards (Auth, Admin)
        └── components/navbar/
```

| ส่วน | เทคโนโลยี | Port |
|------|-----------|------|
| Frontend | Angular 17 (Standalone) | 4200 |
| Backend | FastAPI + SQLite | 3000 |

---

## การติดตั้งและรัน

### ข้อกำหนดเบื้องต้น

- **Python** 3.10+ (มี venv)
- **Node.js** 18+ + npm
- **Angular CLI** (`npm install -g @angular/cli`)

---

### 1. รัน Backend (FastAPI)

```powershell
# เข้าไปที่ root project
cd "d:\year 4 term 1\Project"

# ติดตั้ง dependencies (ครั้งแรก)
.\venv\Scripts\python.exe -m pip install fastapi uvicorn sqlalchemy bcrypt pyjwt httpx python-multipart --no-color

# รัน backend จาก folder backend/
cd backend
..\venv\Scripts\uvicorn.exe shop_api:app --reload --port 3000 --host 0.0.0.0
```

> Backend จะรันที่ `http://localhost:3000`
> API Docs อยู่ที่ `http://localhost:3000/docs`

---

### 2. รัน Frontend (Angular)

```powershell
# เข้าไปที่ It-shop
cd "d:\year 4 term 1\Project\It-shop"

# ติดตั้ง dependencies (ครั้งแรก)
npm install

# รัน development server
ng serve --port 4200 --open
```

> Frontend จะเปิดที่ `http://localhost:4200`

---

## บัญชีสำหรับทดสอบ

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@itrecommend.com | admin1234 |
| ผู้ใช้ทั่วไป | สมัครใหม่ผ่านหน้า /register | - |

---

## หน้าต่างๆ ในระบบ

| URL | หน้า | สิทธิ์ |
|-----|------|--------|
| `/` | หน้าแรก | ทุกคน |
| `/login` | เข้าสู่ระบบ | ทุกคน |
| `/register` | สมัครสมาชิก | ทุกคน |
| `/products` | สินค้าทั้งหมด | ทุกคน |
| `/category/:type` | สินค้าตามหมวดหมู่ | ทุกคน |
| `/product/:id` | รายละเอียดสินค้า | ทุกคน |
| `/ai-recommend` | AI จัดสเปค | ทุกคน |
| `/cart` | ตะกร้าสินค้า / สเปค | ทุกคน |
| `/checkout` | ยืนยันคำสั่งซื้อ | ต้อง Login |
| `/history` | ประวัติ AI Recommend | ต้อง Login |
| `/profile` | โปรไฟล์ของฉัน | ต้อง Login |
| `/admin/products` | จัดการสินค้า | Admin เท่านั้น |
| `/admin/orders` | จัดการออเดอร์ | Admin เท่านั้น |
| `/admin/users` | จัดการผู้ใช้ | Admin เท่านั้น |

---

## API Endpoints หลัก

### Authentication
| Method | Endpoint | คำอธิบาย |
|--------|----------|----------|
| POST | `/api/register` | สมัครสมาชิก |
| POST | `/api/login` | เข้าสู่ระบบ (รับ JWT token) |

### Products
| Method | Endpoint | คำอธิบาย |
|--------|----------|----------|
| GET | `/api/products` | ดึงสินค้าทั้งหมด |
| GET | `/api/products?category=cpu` | ดึงตามหมวดหมู่ |
| GET | `/api/products?search=rtx` | ค้นหาสินค้า |
| GET | `/api/products/{id}` | รายละเอียดสินค้า |
| PUT | `/api/products/{id}` | แก้ไขสินค้า (Admin) |
| DELETE | `/api/products/{id}` | ลบสินค้า (Admin) |

### Orders
| Method | Endpoint | คำอธิบาย |
|--------|----------|----------|
| POST | `/api/orders` | สร้างคำสั่งซื้อ |
| GET | `/api/orders/my` | ออเดอร์ของฉัน |
| GET | `/api/orders` | ออเดอร์ทั้งหมด (Admin) |
| PUT | `/api/orders/{id}/status` | เปลี่ยนสถานะ (Admin) |

### Profile
| Method | Endpoint | คำอธิบาย |
|--------|----------|----------|
| GET | `/api/profile` | ดูโปรไฟล์ |
| PUT | `/api/profile` | แก้ไขโปรไฟล์ |
| PUT | `/api/profile/password` | เปลี่ยนรหัสผ่าน |
| POST | `/api/profile/upload-image` | อัปโหลดรูปโปรไฟล์ |

### AI Recommend
| Method | Endpoint | คำอธิบาย |
|--------|----------|----------|
| POST | `/api/ai/recommend` | ขอคำแนะนำจาก AI |
| GET | `/api/spec-history` | ประวัติ AI Recommend |
| DELETE | `/api/spec-history/{id}` | ลบประวัติ |

---

## วิธีใช้งานสำหรับผู้ใช้ทั่วไป

### สมัครสมาชิก
1. ไปที่ `/register`
2. กรอก ชื่อผู้ใช้, อีเมล, เบอร์โทร, วันเกิด, รหัสผ่าน
3. กดปุ่ม "สมัครสมาชิก"
4. ระบบจะพาไปหน้า Login อัตโนมัติ

### จัดสเปคด้วยตัวเอง
1. เข้าที่ `/products` เลือกหมวดหมู่จาก Navbar
2. กด **เพิ่มลงสเปค** ที่สินค้าที่ต้องการ
3. ไปที่ `/cart` เพื่อดูรายการที่เลือก
4. กด **ยืนยันคำสั่งซื้อ** → กรอกที่อยู่ → กด **ยืนยัน**

### ใช้ AI จัดสเปค
1. เข้าที่ `/ai-recommend`
2. เลือก Mode:
   - **แนะนำสเปค** — บอกงบประมาณและการใช้งาน AI จะแนะนำชิ้นส่วนทั้งหมด
   - **เปรียบเทียบสเปค** — วางสเปค 2 ชุดให้ AI วิเคราะห์
   - **เช็คความเข้ากัน** — ใส่รายการชิ้นส่วน AI จะตรวจสอบ compatibility
3. ดูผลลัพธ์และประวัติ AI ได้ที่ `/history`

### ดูโปรไฟล์และประวัติการสั่งซื้อ
- ไปที่ `/profile` เพื่อแก้ไขข้อมูลส่วนตัวและดูออเดอร์ที่ผ่านมา

---

## วิธีใช้งานสำหรับ Admin

### เข้าสู่ระบบ Admin
1. Login ด้วย Email: `admin@itrecommend.com` / Password: `admin1234`
2. Navbar จะแสดงลิงก์ Admin เพิ่มเติม

### จัดการสินค้า (`/admin/products` หรือ `/products`)
- ในหน้า Products ปุ่มจะเปลี่ยนเป็น **ดู / แก้ไข / ลบ**
- กด **แก้ไข** เพื่อเปิด Modal แก้ไขสินค้า

### จัดการออเดอร์ (`/admin/orders`)
- ดูออเดอร์ทั้งหมด กรองตามสถานะ
- กดที่ออเดอร์เพื่อขยายดูรายละเอียด
- เปลี่ยนสถานะ: **รอดำเนินการ → กำลังจัดส่ง → สำเร็จ**

### จัดการผู้ใช้ (`/admin/users`)
- ค้นหาและดูข้อมูลผู้ใช้ทั้งหมด
- เปลี่ยน Role ระหว่าง admin / customer

---

## หมวดหมู่สินค้า

### PC Components
- CPU / Processor
- GPU / Graphic Card
- Mainboard
- RAM
- SSD / M.2
- PSU
- Case
- Liquid Cooler
- Air Cooler

### Gaming Gear
- Mouse, Keyboard, Headset, Microphone, Monitor

### เฟอร์นิเจอร์
- Gaming Chair, Gaming Desk

---

## โครงสร้างฐานข้อมูล (SQLite)

| ตาราง | คำอธิบาย |
|-------|----------|
| `users` | ข้อมูลผู้ใช้ (uid, u_name, u_email, u_role, ...) |
| `products` | สินค้าทั้งหมด พร้อมราคา 3 ร้าน |
| `orders` | คำสั่งซื้อ |
| `order_items` | รายการสินค้าในแต่ละออเดอร์ |
| `spec_history` | ประวัติ AI Recommend |
| `categories` | หมวดหมู่สินค้า |

---

## การแก้ปัญหาเบื้องต้น

### Backend ไม่ขึ้น
- ตรวจสอบว่ารันคำสั่งจาก folder `backend/` เสมอ
- `shop.db` ต้องอยู่ใน `backend/` folder

### Frontend เชื่อมต่อ Backend ไม่ได้
- ตรวจสอบว่า Backend รันที่ port **3000**
- ตรวจสอบ CORS ใน `shop_api.py` (รองรับ `http://localhost:4200`)

### Login ไม่ได้
- ตรวจสอบว่าสมัครสมาชิกด้วยรูปแบบอีเมลที่ถูกต้อง
- ตรวจสอบ password ขั้นต่ำ 6 ตัวอักษร

### Admin Login
- Email: `admin@itrecommend.com`
- Password: `admin1234`
