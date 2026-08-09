"""
🚀 IT-RECOMMEND Shop API - FastAPI backend
รัน: uvicorn shop_api:app --reload --port 3000
"""
import os, re, json, shutil, asyncio, httpx
from datetime import datetime, timedelta
from typing import Optional, List
from pathlib import Path

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

GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

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
        ]:
            try:
                conn.execute(text(f"ALTER TABLE products ADD COLUMN {col} {defn}"))
                conn.commit()
                print(f"[Migration] Added column products.{col}")
            except Exception:
                pass  # column มีอยู่แล้ว

        # เพิ่ม categories ใหม่ (Gaming Gear + Furniture)
        new_cats = [
            ("c10", "Mouse",         "Gaming Mouse / Optical Mouse"),
            ("c11", "Keyboard",      "Mechanical Keyboard / Gaming Keyboard"),
            ("c12", "Headset",       "Gaming Headset / Headphone"),
            ("c13", "Microphone",    "Condenser Mic / USB Microphone"),
            ("c14", "Monitor",       "Gaming Monitor / LED Monitor"),
            ("c15", "Gaming Chair",  "Ergonomic Chair / Gaming Chair"),
            ("c16", "Gaming Desk",   "Gaming Desk / Adjustable Desk"),
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
        "specs":          p.specs
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
# AI Recommend – Gemini Proxy (FastAPI)
# ─────────────────────────────────────────

# System Prompt สำหรับ IT-RECOMMEND AI
IT_RECOMMEND_SYSTEM_PROMPT = """คุณคือ IT-RECOMMEND AI ผู้เชี่ยวชาญด้านฮาร์ดแวร์คอมพิวเตอร์และอุปกรณ์ IT ในประเทศไทย

== กฎเหล็กที่ต้องปฏิบัติเสมอ ==
1. ตอบเฉพาะคำถามที่เกี่ยวกับ IT Hardware, PC Components, Gaming Gear, อุปกรณ์ต่อพ่วง, จอมอนิเตอร์, เก้าอี้เกมมิ่ง, โต๊ะเกมมิ่ง เท่านั้น
2. ห้ามตอบคำถามที่ไม่เกี่ยวกับ IT/Computer/Gaming Gear โดยเด็ดขาด – ถ้าถามเรื่องอื่นให้ตอบว่า "ขอโทษครับ ผมให้คำแนะนำเฉพาะด้าน IT Hardware และ Gaming Gear เท่านั้น"
3. ราคาสินค้าต้องอ้างอิงจากตลาดไทยจริง (ร้าน JIB, Advice, iHaveCPU, Banana IT) ปี 2025-2026 เท่านั้น
4. ตอบเป็น JSON ที่ถูกต้องเท่านั้น – ห้ามมี text อธิบายนอก JSON โดยเด็ดขาด
5. ระบุชื่อรุ่นสินค้าจริงและครบถ้วนเสมอ เช่น "AMD Ryzen 5 7600X" ไม่ใช่แค่ "Ryzen 5"
6. ชิ้นส่วนทุกอย่างต้องเข้ากันได้จริง (socket, DDR gen, PCIe, TDP, wattage)
7. ราคารวมทั้งหมดต้องไม่เกินงบที่ระบุเกิน 10%
8. ให้ข้อมูลที่ถูกต้องและเป็นปัจจุบัน ถ้าไม่แน่ใจให้ระบุว่า "ราคาประมาณ" แทนการให้ข้อมูลผิด
9. หมวดสินค้าที่แนะนำได้: CPU, GPU, RAM, Mainboard, SSD/M.2, PSU, Case, Cooler, Monitor, Mouse, Keyboard, Headset, Microphone, Gaming Chair, Gaming Desk
10. ห้ามแนะนำสินค้าที่ EOL (End of Life) หรือไม่มีจำหน่ายในไทยแล้ว"""

@app.post("/api/ai/recommend")
async def ai_recommend(body: AIRecommendBody, user: User = Depends(get_current_user)):
    """AI Spec Recommendation ผ่าน Gemini API"""
    if not GEMINI_API_KEY:
        raise HTTPException(500, "GOOGLE_API_KEY ไม่ได้ตั้งค่าในระบบ")

    full_prompt = f"{IT_RECOMMEND_SYSTEM_PROMPT}\n\n== คำขอของผู้ใช้ ==\n{body.prompt}"

    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 4096,
            "topP": 0.95,
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(
                f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                json=payload
            )

        if res.status_code == 429:
            return {"status": "rate_limit", "message": "คนใช้งานเยอะ กรุณาลองใหม่อีกครั้ง"}

        if res.status_code != 200:
            raise HTTPException(res.status_code, f"Gemini API Error: {res.text[:200]}")

        data = res.json()
        text_out = data["candidates"][0]["content"]["parts"][0]["text"]
        return {"status": "success", "data": text_out}

    except httpx.TimeoutException:
        raise HTTPException(504, "Gemini API timeout – ลองใหม่อีกครั้ง")
    except Exception as e:
        raise HTTPException(500, f"AI Error: {str(e)}")

# ─────────────────────────────────────────
# Scraper API
# ─────────────────────────────────────────
class ScrapeRequest(BaseModel):
    store: str = "all"
    pages: int = 2

@app.post("/api/scrape")
async def trigger_scrape(body: ScrapeRequest, admin=Depends(require_admin)):
    try:
        from scraper import run_scraper
        stores = ["ihavecpu", "advice", "jib"] if body.store == "all" else [body.store]
        result = await run_scraper(stores, body.pages)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(500, f"Scraper error: {str(e)}")

@app.get("/api/scrape/status")
def scrape_status(db: Session = Depends(get_db)):
    with engine.connect() as conn:
        total   = conn.execute(text("SELECT COUNT(*) FROM products")).scalar()
        has_img = conn.execute(text("SELECT COUNT(*) FROM products WHERE img_url != '' AND img_url IS NOT NULL")).scalar()
        has_ihc = conn.execute(text("SELECT COUNT(*) FROM products WHERE price_ihavecpu > 0")).scalar()
        has_adv = conn.execute(text("SELECT COUNT(*) FROM products WHERE price_advice > 0")).scalar()
        has_jib = conn.execute(text("SELECT COUNT(*) FROM products WHERE price_jib > 0")).scalar()
    return {
        "status": "ok",
        "products": {"total": total, "with_image": has_img},
        "prices":   {"ihavecpu": has_ihc, "advice": has_adv, "jib": has_jib}
    }

# ─────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("[OK] IT-RECOMMEND API running on http://localhost:3000")
    print("[DOCS] API Docs: http://localhost:3000/docs")
    uvicorn.run(app, host="0.0.0.0", port=3000)
