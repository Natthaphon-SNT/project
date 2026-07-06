"""
สร้าง Database ตาม Schema จาก docs/pc_part.sql (พจนานุกรมข้อมูลบทที่ 3)
รัน: python init_db.py
"""
import sqlite3, json, csv, os, sys
from datetime import datetime
from pathlib import Path

DB_PATH = "shop.db"
CSV_PATH = "../hardware_updated.csv"

# ─────────────────────────────────────────────────
# สร้างตารางทั้งหมดตาม Data Dictionary บทที่ 3
# ─────────────────────────────────────────────────
SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- ตารางผู้ใช้งาน
CREATE TABLE IF NOT EXISTS users (
    uid             TEXT PRIMARY KEY,
    u_name          TEXT NOT NULL UNIQUE,
    u_email         TEXT NOT NULL UNIQUE,
    u_password      TEXT NOT NULL,
    u_phone         TEXT DEFAULT '',
    u_address       TEXT DEFAULT '',
    u_image         TEXT DEFAULT '',
    dob             TEXT DEFAULT '',
    u_role          TEXT NOT NULL DEFAULT 'customer' CHECK(u_role IN ('customer','admin')),
    u_created_at    TEXT DEFAULT (datetime('now','localtime')),
    u_updated_at    TEXT DEFAULT (datetime('now','localtime')),
    u_last_login    TEXT
);

-- ตารางหมวดหมู่สินค้า
CREATE TABLE IF NOT EXISTS categories (
    cid             TEXT PRIMARY KEY,
    c_name          TEXT NOT NULL UNIQUE,
    c_description   TEXT DEFAULT ''
);

-- ตารางสินค้า
CREATE TABLE IF NOT EXISTS products (
    product_id      TEXT PRIMARY KEY,
    p_name          TEXT NOT NULL,
    p_description   TEXT DEFAULT '',
    p_price         REAL NOT NULL DEFAULT 0,
    price_advice    INTEGER DEFAULT 0,
    price_jib       INTEGER DEFAULT 0,
    price_ihavecpu  INTEGER DEFAULT 0,
    p_stock         INTEGER NOT NULL DEFAULT 0,
    cid             TEXT DEFAULT '',
    category        TEXT DEFAULT '',
    img_url         TEXT DEFAULT '',
    specs           TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (cid) REFERENCES categories(cid)
);

-- ตารางโปรโมชั่น
CREATE TABLE IF NOT EXISTS promotions (
    promo_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    promo_name      TEXT NOT NULL,
    promo_description TEXT DEFAULT '',
    promo_img       TEXT DEFAULT '',
    discount_type   TEXT DEFAULT 'percent' CHECK(discount_type IN ('percent','fixed')),
    discount_value  REAL DEFAULT 0,
    promo_stock     INTEGER DEFAULT 0,
    promo_price     REAL DEFAULT 0,
    start_date      TEXT NOT NULL,
    end_date        TEXT NOT NULL,
    status          TEXT DEFAULT 'active' CHECK(status IN ('active','inactive','expired'))
);

-- ตารางออร์เดอร์
CREATE TABLE IF NOT EXISTS orders (
    order_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    uid             TEXT,
    customer_name   TEXT DEFAULT '',
    phone           TEXT DEFAULT '',
    address         TEXT DEFAULT '',
    payment_method  TEXT DEFAULT 'cod',
    total_price     REAL DEFAULT 0,
    total_amount    REAL DEFAULT 0,
    o_status        TEXT DEFAULT 'pending' CHECK(o_status IN ('pending','paid','shipped','completed','cancelled')),
    order_date      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (uid) REFERENCES users(uid)
);

-- ตารางรายการสินค้าในออร์เดอร์
CREATE TABLE IF NOT EXISTS order_items (
    order_item_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL,
    product_id      TEXT NOT NULL,
    p_name          TEXT DEFAULT '',
    oi_quantity     INTEGER DEFAULT 1,
    oi_price        REAL DEFAULT 0,
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

-- ตารางการชำระเงิน
CREATE TABLE IF NOT EXISTS payments (
    payment_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL,
    payment_date    TEXT DEFAULT (date('now','localtime')),
    pa_amount       REAL DEFAULT 0,
    pa_method       TEXT DEFAULT 'cod' CHECK(pa_method IN ('transfer','credit_card','cod')),
    pa_status       TEXT DEFAULT 'pending' CHECK(pa_status IN ('pending','confirmed','failed')),
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

-- ตารางประวัติการแนะนำสเปค (หัวใจของระบบ AI)
CREATE TABLE IF NOT EXISTS spec_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    uid             TEXT NOT NULL,
    username        TEXT DEFAULT '',
    type            TEXT DEFAULT 'ai' CHECK(type IN ('ai','manual')),
    mode            TEXT DEFAULT 'recommend',
    title           TEXT DEFAULT '',
    inputSummary    TEXT DEFAULT '',
    result_data     TEXT DEFAULT '{}',
    createdAt       TEXT DEFAULT (datetime('now','localtime'))
);

-- ตารางตะกร้าสินค้า
CREATE TABLE IF NOT EXISTS cart (
    cart_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    uid             TEXT NOT NULL,
    created_at      TEXT DEFAULT (date('now','localtime')),
    FOREIGN KEY (uid) REFERENCES users(uid)
);

-- ตารางรายการในตะกร้า
CREATE TABLE IF NOT EXISTS cart_items (
    cart_item_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    cart_id         INTEGER NOT NULL,
    product_id      TEXT NOT NULL,
    c_quantity      INTEGER DEFAULT 1,
    FOREIGN KEY (cart_id) REFERENCES cart(cart_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- ตารางรีวิว
CREATE TABLE IF NOT EXISTS reviews (
    reviews_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id          TEXT NOT NULL,
    uid                 TEXT NOT NULL,
    r_rating            INTEGER DEFAULT 5 CHECK(r_rating BETWEEN 1 AND 5),
    r_comment           TEXT DEFAULT '',
    r_media_url         TEXT DEFAULT '',
    r_helpful_count     INTEGER DEFAULT 0,
    r_verified_purchase INTEGER DEFAULT 0,
    review_status       TEXT DEFAULT 'pending' CHECK(review_status IN ('pending','approved','rejected')),
    r_created_at        TEXT DEFAULT (date('now','localtime')),
    r_updated_at        TEXT DEFAULT (date('now','localtime')),
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (uid) REFERENCES users(uid)
);

-- ตารางการจัดส่ง
CREATE TABLE IF NOT EXISTS shipping (
    shipping_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL,
    tracking_number TEXT DEFAULT '',
    s_carrier       TEXT DEFAULT '',
    shipping_date   TEXT DEFAULT (date('now','localtime')),
    s_status        TEXT DEFAULT 'processing' CHECK(s_status IN ('processing','in_transit','delivered')),
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

-- ตารางคืนสินค้า
CREATE TABLE IF NOT EXISTS returns (
    return_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL,
    product_id      TEXT NOT NULL,
    r_reason        TEXT DEFAULT '',
    r_status        TEXT DEFAULT 'pending' CHECK(r_status IN ('pending','approved','rejected','refunded')),
    r_created_at    TEXT DEFAULT (date('now','localtime')),
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

-- ตารางการคืนเงิน
CREATE TABLE IF NOT EXISTS refunds (
    refund_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    return_id       INTEGER NOT NULL,
    payment_id      INTEGER,
    refund_amount   REAL DEFAULT 0,
    refund_date     TEXT DEFAULT (date('now','localtime')),
    refund_status   TEXT DEFAULT 'pending' CHECK(refund_status IN ('pending','processed','failed')),
    FOREIGN KEY (return_id) REFERENCES returns(return_id)
);

-- ตาราง Activity Log
CREATE TABLE IF NOT EXISTS activity_logs (
    log_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    uid             TEXT NOT NULL,
    l_action        TEXT DEFAULT '',
    l_description   TEXT DEFAULT '',
    l_created_at    TEXT DEFAULT (datetime('now','localtime'))
);

-- ตาราง Wishlist
CREATE TABLE IF NOT EXISTS wishlist (
    wishlist_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    uid             TEXT NOT NULL,
    product_id      TEXT NOT NULL,
    w_added_at      TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (uid) REFERENCES users(uid),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

-- ตาราง Promotion-Products mapping
CREATE TABLE IF NOT EXISTS promotion_products (
    pp_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    promo_id    INTEGER NOT NULL,
    product_id  TEXT NOT NULL,
    FOREIGN KEY (promo_id) REFERENCES promotions(promo_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);
"""

# ─────────────────────────────────────────────────
# ข้อมูล Categories ตาม PC part types
# ─────────────────────────────────────────────────
DEFAULT_CATEGORIES = [
    ("c01", "CPU",           "ซีพียู (Processor)"),
    ("c02", "Mainboard",     "เมนบอร์ด (Motherboard)"),
    ("c03", "GPU",           "การ์ดจอ (Graphics Card)"),
    ("c04", "RAM",           "แรม (Memory)"),
    ("c05", "M.2",           "เอสเอสดี (SSD/NVMe)"),
    ("c06", "PSU",           "อุปกรณ์จ่ายไฟ (Power Supply)"),
    ("c07", "Case",          "เคส (Computer Case)"),
    ("c08", "Liquid Cooler", "ชุดน้ำปิด (AIO Liquid Cooler)"),
    ("c09", "Air Cooler",    "ซิงค์ลม (Air Cooler)"),
]

# Map CSV category → cid
CATEGORY_MAP = {
    "CPU": "c01", "Mainboard": "c02", "GPU": "c03",
    "RAM": "c04", "SSD": "c05", "M.2": "c05",
    "PSU": "c06", "Case": "c07",
    "Liquid Cooler": "c08", "Cooler": "c09", "Air Cooler": "c09",
}

def import_csv_products(conn: sqlite3.Connection):
    """นำเข้าสินค้าจาก hardware_updated.csv"""
    csv_file = Path(CSV_PATH)
    if not csv_file.exists():
        print(f"[SKIP] ไม่พบไฟล์ {CSV_PATH}")
        return

    cursor = conn.cursor()
    count = 0
    seen_ids = set()

    with open(csv_file, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)  # อ่าน header

        for i, row in enumerate(reader):
            if len(row) < 3:
                continue
            try:
                cat_raw  = row[0].strip()
                brand    = row[1].strip()
                model    = row[2].strip()
                price_jib      = int(row[3])  if len(row) > 3 and row[3].strip().lstrip('-').isdigit() else 0
                price_advice   = int(row[4])  if len(row) > 4 and row[4].strip().lstrip('-').isdigit() else 0
                price_ihavecpu = int(row[5])  if len(row) > 5 and row[5].strip().lstrip('-').isdigit() else 0

                prices = [p for p in [price_jib, price_advice, price_ihavecpu] if p > 0]
                best_price = min(prices) if prices else 0

                cid = CATEGORY_MAP.get(cat_raw, "c01")
                product_id = f"{cat_raw[:3].lower()}{i+1:04d}"

                if product_id in seen_ids:
                    product_id = f"{cat_raw[:3].lower()}{i+1:05d}"
                seen_ids.add(product_id)

                p_name = f"{brand} {model}"

                cursor.execute("""
                    INSERT OR IGNORE INTO products
                    (product_id, p_name, p_description, p_price,
                     price_advice, price_jib, price_ihavecpu,
                     p_stock, cid, category, img_url)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    product_id, p_name, "", best_price,
                    price_advice, price_jib, price_ihavecpu,
                    999, cid, cat_raw, ""
                ))
                count += 1
            except Exception as e:
                continue

    conn.commit()
    print(f"[OK] นำเข้าสินค้าจาก CSV: {count} รายการ")


def main():
    print("=" * 50)
    print("  Database Init - ระบบแนะนำสเปคคอมพิวเตอร์")
    print("  Schema: บทที่ 3 Data Dictionary")
    print("=" * 50)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # สร้างตาราง
    cur.executescript(SCHEMA)
    conn.commit()
    print("[OK] สร้างตารางทั้งหมดสำเร็จ (15 ตาราง)")

    # ใส่ Categories
    for cid, name, desc in DEFAULT_CATEGORIES:
        cur.execute("INSERT OR IGNORE INTO categories (cid, c_name, c_description) VALUES (?,?,?)",
                    (cid, name, desc))
    conn.commit()
    print("[OK] เพิ่มหมวดหมู่สินค้า 9 หมวด")

    # นำเข้าสินค้าจาก CSV
    import_csv_products(conn)

    # สรุป
    tables = ["users","categories","products","orders","order_items",
              "payments","promotions","spec_history","reviews",
              "cart","cart_items","shipping","returns","refunds","activity_logs"]
    print("\n[สรุป จำนวนข้อมูล]")
    for t in tables:
        try:
            n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
            print(f"  {t:<20}: {n} rows")
        except:
            pass

    conn.close()
    print("\n[DONE] shop.db พร้อมใช้งาน!")


if __name__ == "__main__":
    main()
