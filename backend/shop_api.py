"""
🚀 IT-RECOMMEND Shop API - FastAPI backend
รัน: uvicorn shop_api:app --reload --port 3000
"""
import os, re, json, shutil, asyncio, httpx
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, ForeignKey, func, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base, relationship
import bcrypt
import jwt

# ─────────────────────────────────────────
# Config
# ─────────────────────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "tak-tech-secret-2025")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 72
DB_URL = "sqlite:///./shop.db"
UPLOAD_DIR = Path("uploads/profile")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# OpenCode Zen AI gateway (OpenAI-compatible)
ZEN_BASE_URL  = os.getenv("ZEN_BASE_URL", "https://opencode.ai/zen/v1")
OPENCODE_API_KEY = os.getenv("OPENCODE_API_KEY", "")
ZEN_MODEL     = os.getenv("ZEN_MODEL", "x-preview-f-free")

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
security = HTTPBearer(auto_error=False)

app = FastAPI(title="IT-RECOMMEND Shop API", version="3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

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
    uid          = Column(String, default="")
    username     = Column(String, default="")
    type         = Column(String, default="ai")
    mode         = Column(String, default="recommend")
    title        = Column(String, default="")
    inputSummary = Column(Text, default="")
    result_data  = Column(Text, default="{}")
    createdAt    = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

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

        # เพิ่ม categories ใหม่ (Gaming Gear + Furniture + PC Set)
        new_cats = [
            ("c10", "Mouse",         "Gaming Mouse / Optical Mouse"),
            ("c11", "Keyboard",      "Mechanical Keyboard / Gaming Keyboard"),
            ("c12", "Headset",       "Gaming Headset / Headphone"),
            ("c13", "Microphone",    "Condenser Mic / USB Microphone"),
            ("c14", "Monitor",       "Gaming Monitor / LED Monitor"),
            ("c15", "Gaming Chair",  "Ergonomic Chair / Gaming Chair"),
            ("c16", "Gaming Desk",   "Gaming Desk / Adjustable Desk"),
            ("c18", "PC Set",        "ชุดคอมประกอบสำเร็จรูปจากร้าน iHaveCPU / JIB / Advice"),
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


run_migrations(engine)

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
    payload["exp"] = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    if not creds:
        raise HTTPException(status_code=401, detail="ไม่ได้เข้าสู่ระบบ")
    try:
        payload = decode_token(creds.credentials)
        user = db.query(User).filter(User.uid == payload["uid"]).first()
        if not user:
            raise HTTPException(status_code=401, detail="ไม่พบผู้ใช้")
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="Token ไม่ถูกต้องหรือหมดอายุ")

def require_admin(user: User = Depends(get_current_user)):
    if user.u_role != "admin":
        raise HTTPException(status_code=403, detail="ต้องมีสิทธิ์ Admin")
    return user

def product_to_dict(p: Product) -> dict:
    """แปลง Product object เป็น dict ที่มีทุก field"""
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
        "updated_at":     getattr(p, 'updated_at', '') or ""
    }

# ─────────────────────────────────────────
# Schemas (Pydantic)
# ─────────────────────────────────────────
class RegisterBody(BaseModel):
    uid: str
    u_name: str
    u_email: str
    u_phone: str
    dob: str
    u_password: str
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
    p_price: float
    p_stock: int = 0
    img_url: str = ""
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
    p_price: Optional[float] = None
    p_stock: Optional[int] = None
    img_url: Optional[str] = None
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

class OrderItemSchema(BaseModel):
    product_id: str
    p_name: str
    quantity: int
    price: float

class CustomerInfo(BaseModel):
    name: str
    phone: str
    address: str

class PlaceOrderBody(BaseModel):
    uid: Optional[str] = None
    customer: CustomerInfo
    items: List[OrderItemSchema]
    total_price: float
    payment_method: str = "cod"

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

class AIRecommendBody(BaseModel):
    prompt: str
    mode: str = "recommend"   # recommend | compare | compat

# ─────────────────────────────────────────
# Auth Routes
# ─────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "message": "🚀 IT-RECOMMEND Shop API v3"}

# ─────────────────────────────────────────
# Image Proxy — bypass hotlink/CORS/Referer blocking from store CDNs
# ─────────────────────────────────────────
from fastapi.responses import Response as FastAPIResponse
import urllib.parse as _urlparse

@app.get("/api/image-proxy")
async def image_proxy(url: str = Query(..., description="URL รูปภาพต้นทาง")):
    """
    Proxy รูปภาพจากร้านค้า (JIB, iHaveCPU, Advice) เพื่อหลีกเลี่ยง
    hotlink-block / CORS / Referer ที่ทำให้ browser โหลดรูปไม่ได้โดยตรง
    """
    # Whitelist domain ที่อนุญาต
    ALLOWED_DOMAINS = (
        "jib.co.th", "ihavecpu.com", "advice.co.th",
        "ihcupload-bkk.s3.ap-southeast-7.amazonaws.com",
        "img.advice.co.th", "cdn.advice.co.th",
    )
    try:
        parsed = _urlparse.urlparse(url)
        host = parsed.netloc.lower()
        if not any(host.endswith(d) for d in ALLOWED_DOMAINS):
            raise HTTPException(400, f"Domain ไม่ได้รับอนุญาต: {host}")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "URL ไม่ถูกต้อง")

    # Headers ที่ช่วยให้ได้รูปจริง (simulate browser + Referer)
    headers = {
        "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36",
        "Referer":         f"{parsed.scheme}://{parsed.netloc}/",
        "Accept":          "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                raise HTTPException(502, f"ร้านค้าตอบกลับ {resp.status_code}")
            content_type = resp.headers.get("content-type", "image/jpeg")
            return FastAPIResponse(
                content=resp.content,
                media_type=content_type,
                headers={"Cache-Control": "public, max-age=86400"},  # cache 1 วัน
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"โหลดรูปไม่ได้: {str(e)[:100]}")

@app.post("/api/register")
def register(body: RegisterBody, db: Session = Depends(get_db)):
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
def login(body: LoginBody, db: Session = Depends(get_db)):
    username = body.email or body.u_name or ""
    password = body.password or body.u_password or ""
    user = db.query(User).filter(
        (User.u_name == username) | (User.u_email == username)
    ).first()
    if not user or not verify_password(password, user.u_password):
        raise HTTPException(401, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
    user.u_last_login = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.commit()
    token = create_token({"uid": user.uid, "role": user.u_role})
    return {
        "status": "success",
        "message": "เข้าสู่ระบบสำเร็จ",
        "token": token,
        "user": {"id": user.uid, "name": user.u_name, "role": user.u_role, "email": user.u_email}
    }

# ─────────────────────────────────────────
# Products
# ─────────────────────────────────────────
@app.get("/api/products")
def get_products(
    category: str = "", cid: str = "", search: str = "", name: str = "",
    db: Session = Depends(get_db)
):
    q = db.query(Product)
    if category:
        q = q.filter(func.lower(Product.category) == category.lower())
    if cid:      q = q.filter(Product.cid == cid)
    if search:   q = q.filter(Product.p_name.contains(search) | Product.p_description.contains(search))
    if name:     q = q.filter(Product.p_name.contains(name))
    products = q.order_by(Product.created_at.desc()).all()
    return {"status": "success", "data": [product_to_dict(p) for p in products]}

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
    p = Product(**body.dict())
    db.add(p); db.commit()
    return {"status": "success", "message": "เพิ่มสินค้าสำเร็จ"}

@app.put("/api/products/{product_id}")
def update_product(product_id: str, body: ProductUpdate, admin=Depends(require_admin), db: Session = Depends(get_db)):
    p = db.query(Product).filter(Product.product_id == product_id).first()
    if not p: raise HTTPException(404, "ไม่พบสินค้า")
    for k, v in body.dict(exclude_none=True).items():
        setattr(p, k, v)
    db.commit()
    return {"status": "success", "message": "แก้ไขสินค้าสำเร็จ"}

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
    pr = Promotion(**body.dict())
    db.add(pr); db.commit()
    return {"status": "success", "message": "เพิ่มโปรโมชั่นสำเร็จ", "promo_id": pr.promo_id}

@app.put("/api/promotions/{promo_id}")
def update_promo(promo_id: int, body: PromoCreate, admin=Depends(require_admin), db: Session = Depends(get_db)):
    pr = db.query(Promotion).filter(Promotion.promo_id == promo_id).first()
    if not pr: raise HTTPException(404, "ไม่พบโปรโมชั่น")
    for k, v in body.dict().items(): setattr(pr, k, v)
    db.commit()
    return {"status": "success", "message": "แก้ไขโปรโมชั่นสำเร็จ"}

@app.delete("/api/promotions/{promo_id}")
def delete_promo(promo_id: int, admin=Depends(require_admin), db: Session = Depends(get_db)):
    pr = db.query(Promotion).filter(Promotion.promo_id == promo_id).first()
    if not pr: raise HTTPException(404, "ไม่พบโปรโมชั่น")
    db.delete(pr); db.commit()
    return {"status": "success", "message": "ลบโปรโมชั่นสำเร็จ"}

# ─────────────────────────────────────────
# Orders
# ─────────────────────────────────────────
@app.post("/api/orders")
def place_order(body: PlaceOrderBody, db: Session = Depends(get_db)):
    order = Order(
        uid=body.uid,
        customer_name=body.customer.name,
        phone=body.customer.phone,
        address=body.customer.address,
        payment_method=body.payment_method,
        total_price=body.total_price,
        o_status="pending"
    )
    db.add(order); db.flush()
    for item in body.items:
        detail = OrderItem(
            order_id=order.order_id,
            product_id=item.product_id,
            p_name=item.p_name,
            oi_quantity=item.quantity,
            oi_price=item.price
        )
        db.add(detail)
    db.commit()
    return {"status": "success", "message": "สั่งซื้อสำเร็จ", "order_id": order.order_id}

@app.get("/api/orders")
def get_all_orders(admin=Depends(require_admin), db: Session = Depends(get_db)):
    orders = db.query(Order).order_by(Order.order_date.desc()).all()
    result = []
    for o in orders:
        result.append({
            "order_id": o.order_id, "uid": o.uid,
            "customer_name": o.customer_name, "phone": o.phone,
            "address": o.address, "payment_method": o.payment_method,
            "total_price": o.total_price, "status": o.o_status,
            "order_date": str(o.order_date) if o.order_date else "",
            "u_name": o.user.u_name if o.user else o.customer_name,
            "u_email": o.user.u_email if o.user else "",
            "u_phone": o.user.u_phone if o.user else o.phone,
            "items": [{"product_id": d.product_id, "p_name": d.p_name,
                       "quantity": d.oi_quantity, "price": d.oi_price} for d in o.items]
        })
    return {"status": "success", "data": result}

@app.get("/api/orders/my")
def get_my_orders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.uid == user.uid).order_by(Order.order_date.desc()).all()
    result = []
    for o in orders:
        result.append({
            "order_id": o.order_id, "total_price": o.total_price,
            "status": o.o_status, "order_date": str(o.order_date) if o.order_date else "",
            "payment_method": o.payment_method,
            "items": [{"product_id": d.product_id, "p_name": d.p_name,
                       "quantity": d.oi_quantity, "price": d.oi_price} for d in o.items]
        })
    return {"status": "success", "data": result}

@app.get("/api/orders/{order_id}")
def get_order_detail(order_id: int, db: Session = Depends(get_db)):
    o = db.query(Order).filter(Order.order_id == order_id).first()
    if not o: raise HTTPException(404, "ไม่พบคำสั่งซื้อ")
    return {"status": "success", "data": {
        "order_id": o.order_id, "customer_name": o.customer_name,
        "phone": o.phone, "address": o.address,
        "payment_method": o.payment_method, "total_price": o.total_price,
        "status": o.o_status, "order_date": str(o.order_date) if o.order_date else "",
        "items": [{"product_id": d.product_id, "p_name": d.p_name,
                   "quantity": d.oi_quantity, "price": d.oi_price} for d in o.items]
    }}

@app.put("/api/orders/{order_id}/status")
def update_order_status(order_id: int, payload: dict, admin=Depends(require_admin), db: Session = Depends(get_db)):
    o = db.query(Order).filter(Order.order_id == order_id).first()
    if not o: raise HTTPException(404, "ไม่พบคำสั่งซื้อ")
    o.o_status = payload.get("status", o.o_status)
    db.commit()
    return {"status": "success", "message": "อัปเดตสถานะสำเร็จ"}

# ─────────────────────────────────────────
# Spec History
# ─────────────────────────────────────────
class SpecHistoryCreate(BaseModel):
    uid: str
    username: str = ""
    type: str = "ai"
    mode: str = "recommend"
    title: str = ""
    inputSummary: str = ""
    result_data: str = "{}"

@app.get("/api/spec-history")
def get_spec_history(uid: str = "", limit: int = 20, db: Session = Depends(get_db)):
    q = db.query(SpecHistory)
    if uid: q = q.filter(SpecHistory.uid == uid)
    items = q.order_by(SpecHistory.createdAt.desc()).limit(limit).all()
    return {"status": "success", "data": [
        {"id": i.id, "uid": i.uid, "username": i.username,
         "type": i.type, "mode": i.mode, "title": i.title,
         "inputSummary": i.inputSummary, "result_data": i.result_data,
         "createdAt": i.createdAt}
        for i in items
    ]}

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

@app.post("/api/spec-history")
def save_spec_history(body: SpecHistoryCreate, db: Session = Depends(get_db)):
    item = SpecHistory(**body.dict())
    db.add(item); db.commit()
    return {"status": "success", "message": "บันทึกประวัติสำเร็จ", "id": item.id}

@app.delete("/api/spec-history/{id}")
def delete_spec_history(id: int, db: Session = Depends(get_db)):
    item = db.query(SpecHistory).filter(SpecHistory.id == id).first()
    if not item: raise HTTPException(404, "ไม่พบข้อมูล")
    db.delete(item); db.commit()
    return {"status": "success", "message": "ลบสำเร็จ"}

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
    db_user.u_updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.commit()
    return {"status": "success", "message": "เปลี่ยนรหัสผ่านสำเร็จ"}

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
        order_count = db.query(Order).filter(Order.uid == u.uid).count()
        spec_count  = db.query(SpecHistory).filter(SpecHistory.uid == u.uid).count()
        result.append({
            "uid": u.uid, "u_name": u.u_name, "u_email": u.u_email,
            "u_phone": u.u_phone, "u_role": u.u_role, "dob": u.dob,
            "u_image": u.u_image, "u_address": u.u_address,
            "u_created_at": u.u_created_at, "u_last_login": u.u_last_login,
            "order_count": order_count, "spec_count": spec_count
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
    if body.u_role: u.u_role = body.u_role
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

@app.get("/api/admin/users/{uid}/orders")
def admin_get_user_orders(uid: str, admin=Depends(require_admin), db: Session = Depends(get_db)):
    orders = db.query(Order).filter(Order.uid == uid).order_by(Order.order_date.desc()).all()
    return {"status": "success", "data": [
        {
            "order_id": o.order_id, "total_price": o.total_price,
            "status": o.o_status, "order_date": str(o.order_date) if o.order_date else "",
            "payment_method": o.payment_method,
            "items": [{"product_id": d.product_id, "p_name": d.p_name,
                       "quantity": d.oi_quantity, "price": d.oi_price} for d in o.items]
        } for o in orders
    ]}

# ─────────────────────────────────────────
# AI Recommend – Hybrid RAG + Compatibility Engine (OpenCode Zen)
# ─────────────────────────────────────────

@app.post("/api/ai/recommend")
async def ai_recommend(body: AIRecommendBody, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Hybrid recommendation pipeline:
      mode=recommend → RAG candidates from Product DB + LLM selection + deterministic validation
      mode=compat    → deterministic compatibility engine (+ optional LLM suggestions)
      mode=compare   → LLM comparison via OpenCode Zen
    Response shape unchanged for the frontend: {"status": "success", "data": "<json text>"}
    """
    import recommender as rec

    try:
        if body.mode == "compat":
            result = await rec.compat_check_hybrid(body.prompt)
            return {"status": "success", "data": json.dumps(result, ensure_ascii=False)}

        if body.mode == "compare":
            m = re.search(r"ชุดที่ 1[:：]\s*(.+?)\s*\|?\s*ชุดที่ 2[:：]\s*(.+)", body.prompt, re.DOTALL)
            if not m:
                # frontend sends spec1 | spec2 inside its own prompt; fallback: split by newline pairs
                lines = [l for l in body.prompt.splitlines() if l.strip()]
                m = re.search(r"ชุดที่ 1[:：](.+?)\n.*?ชุดที่ 2[:：](.+)", body.prompt, re.DOTALL)
            if not m:
                raise HTTPException(400, "รูปแบบข้อมูลเปรียบเทียบไม่ถูกต้อง")
            text = await rec.compare_specs(m.group(1).strip(), m.group(2).strip())
            return {"status": "success", "data": text}

        # default: recommend (primary build + Top-3 scored alternatives)
        result = await rec.recommend_with_alternatives(db, body.prompt)
        return {"status": "success", "data": json.dumps(result, ensure_ascii=False)}

    except RuntimeError as e:
        msg = str(e)
        if msg == "rate_limit":
            return {"status": "rate_limit", "message": "คนใช้งานเยอะ กรุณาลองใหม่อีกครั้ง"}
        raise HTTPException(502, f"AI Provider Error: {msg}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"AI Error: {str(e)}")


class CompatCheckBody(BaseModel):
    parts_text: str

@app.post("/api/compat/check")
async def compat_check(body: CompatCheckBody):
    """Deterministic compatibility engine — no LLM involved in the verdict."""
    import recommender as rec
    result = await rec.compat_check_hybrid(body.parts_text)
    return {"status": "success", "data": result}


class CompatibilityPartsBody(BaseModel):
    parts: list[dict]
    budget: Optional[int] = None

@app.post("/api/compatibility/check-parts")
@app.post("/api/compatibility/check")
def check_compatibility_parts(body: CompatibilityPartsBody):
    """Real-time deterministic compatibility check for structured parts from PC Builder."""
    import spec_parser as sp
    import compat_engine as ce
    
    parsed = []
    for p in body.parts:
        cat = p.get("category") or ""
        name = p.get("name") or p.get("p_name") or ""
        price = p.get("price") or p.get("p_price") or 0
        part_info = sp.parse_part(cat, name)
        part_info["price"] = price
        parsed.append(part_info)
        
    result = ce.check_build(parsed, body.budget)
    return {"status": "success", "data": result}


class SpecHistoryCreate(BaseModel):
    uid: str
    username: Optional[str] = ""
    type: Optional[str] = "manual"
    mode: Optional[str] = "manual"
    title: Optional[str] = "จัดสเปกเอง"
    inputSummary: Optional[str] = ""
    result_data: object

@app.get("/api/spec-history")
def get_spec_history(uid: Optional[str] = None, limit: int = 50, db: Session = Depends(get_db)):
    q = db.query(SpecHistory)
    if uid:
        q = q.filter(SpecHistory.uid == uid)
    items = q.order_by(SpecHistory.createdAt.desc()).limit(limit).all()
    return {"status": "success", "data": [
        {
            "id": s.id, "uid": s.uid, "username": s.username,
            "type": s.type, "mode": s.mode, "title": s.title,
            "inputSummary": s.inputSummary, "result_data": s.result_data,
            "createdAt": s.createdAt
        } for s in items
    ]}

@app.post("/api/spec-history")
def create_spec_history(body: SpecHistoryCreate, db: Session = Depends(get_db)):
    res_str = json.dumps(body.result_data, ensure_ascii=False) if not isinstance(body.result_data, str) else body.result_data
    item = SpecHistory(
        uid=body.uid,
        username=body.username or "",
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
            "id": item.id, "uid": item.uid, "username": item.username,
            "type": item.type, "mode": item.mode, "title": item.title,
            "inputSummary": item.inputSummary, "result_data": item.result_data,
            "createdAt": item.createdAt
        }
    }

@app.delete("/api/spec-history/{id}")
def delete_spec_history(id: int, db: Session = Depends(get_db)):
    item = db.query(SpecHistory).filter(SpecHistory.id == id).first()
    if not item:
        raise HTTPException(404, "ไม่พบประวัติการจัดสเปค")
    db.delete(item)
    db.commit()
    return {"status": "success", "message": "ลบประวัติสำเร็จ"}


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
