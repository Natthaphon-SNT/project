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
    db: Session = Depends(get_db)
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
# AI Recommend — optional auth, per-user provider/key
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

def get_ai_optional_user(creds: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    return get_current_user(creds, db) if creds else None

@app.post("/api/ai/recommend")
@limiter.limit("10/minute")
async def ai_recommend(
    request: Request,
    body: AIRecommendBody,
    user: Optional[User] = Depends(get_ai_optional_user),
    db: Session = Depends(get_db)
):
    """
    Hybrid recommendation pipeline (no login required).
    If logged in, uses user's stored AI settings and saves to session.
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
async def compat_check(body: CompatCheckBody):
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
def check_compatibility_parts(body: CompatibilityPartsBody, db: Session = Depends(get_db)):
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
