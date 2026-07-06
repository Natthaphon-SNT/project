"""
อัปเดต img_url ของสินค้าจาก pc_part.sql เข้า shop.db
รัน: python import_images.py
"""
import sqlite3, re
from pathlib import Path

DB_PATH = "shop.db"
SQL_PATH = "../docs/pc_part.sql"

def extract_products_from_sql(sql_path: str) -> dict:
    """ดึง product_id → img_url จากไฟล์ SQL"""
    content = Path(sql_path).read_text(encoding="utf-8", errors="ignore")
    
    # หา INSERT INTO products ทั้งหมด
    pattern = r"\('([^']+)',\s*'([^']*)',\s*'[^']*',\s*[\d.]+,\s*\d+,\s*\d+,\s*\d+,\s*\d+,\s*'[^']*',\s*'([^']*)'\)"
    matches = re.findall(pattern, content)
    
    result = {}
    for product_id, p_name, img_url in matches:
        if img_url:
            result[product_id] = img_url
    
    print(f"[INFO] พบรูปภาพใน SQL: {len(result)} รายการ")
    return result

def update_images():
    sql_file = Path(SQL_PATH)
    if not sql_file.exists():
        print(f"[ERROR] ไม่พบ {SQL_PATH}")
        return
    
    product_images = extract_products_from_sql(SQL_PATH)
    if not product_images:
        print("[WARN] ไม่พบข้อมูลรูปภาพ")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # ดู product_id ที่มีในฐานข้อมูล
    existing = {row[0] for row in cur.execute("SELECT product_id FROM products")}
    print(f"[INFO] สินค้าใน DB: {len(existing)} รายการ")
    
    # อัปเดต img_url ที่ตรงกัน
    updated = 0
    inserted = 0
    
    for pid, img_url in product_images.items():
        if pid in existing:
            cur.execute("UPDATE products SET img_url = ? WHERE product_id = ?", (img_url, pid))
            updated += 1
        # ถ้า product_id ไม่ตรงกัน ข้ามไป (สินค้า CSV ใช้ format id ต่างกัน)
    
    conn.commit()
    print(f"[OK] อัปเดตรูป: {updated} รายการ")
    
    # ตรวจสอบสินค้าที่ยังไม่มีรูป
    no_img = cur.execute("SELECT COUNT(*) FROM products WHERE img_url = '' OR img_url IS NULL").fetchone()[0]
    has_img = cur.execute("SELECT COUNT(*) FROM products WHERE img_url != '' AND img_url IS NOT NULL").fetchone()[0]
    print(f"[INFO] มีรูป: {has_img} | ไม่มีรูป: {no_img}")
    
    conn.close()

if __name__ == "__main__":
    update_images()
