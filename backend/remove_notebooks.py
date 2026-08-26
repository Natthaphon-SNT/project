"""
Script สำหรับ:
1. ลบสินค้า Notebook/Laptop ออกจาก DB
2. แสดงสถิติก่อน-หลัง
"""
import sqlite3

DB_PATH = "shop.db"

NOTEBOOK_KEYWORDS = [
    "NOTEBOOK", "LAPTOP", "โน๊ตบุ๊ค", "โน้ตบุ๊ค", "โน้ตบุค", "โนตบุค",
    "MACBOOK", "CHROMEBOOK", "ULTRABOOK",
    "NOTEBOOK PC", "LAPTOP PC", "GAMING LAPTOP", "GAMING NOTEBOOK",
]

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# แสดงจำนวนก่อน
cur.execute("SELECT COUNT(*) FROM products")
before = cur.fetchone()[0]
print(f"ก่อนลบ: {before} สินค้า")

# หาสินค้า Notebook/Laptop
to_delete = []
cur.execute("SELECT product_id, p_name FROM products")
rows = cur.fetchall()
for pid, name in rows:
    name_upper = (name or "").upper()
    if any(kw in name_upper for kw in NOTEBOOK_KEYWORDS):
        to_delete.append((pid, name))

print(f"\nพบ Notebook/Laptop: {len(to_delete)} รายการ")
for pid, name in to_delete:
    print(f"  - {name[:60]}")

if to_delete:
    ids = [t[0] for t in to_delete]
    placeholders = ",".join("?" * len(ids))
    cur.execute(f"DELETE FROM products WHERE product_id IN ({placeholders})", ids)
    conn.commit()
    print(f"\nลบแล้ว {len(to_delete)} รายการ")
else:
    print("\nไม่มีสินค้าที่ต้องลบ")

# แสดงจำนวนหลัง
cur.execute("SELECT COUNT(*) FROM products")
after = cur.fetchone()[0]
print(f"หลังลบ: {after} สินค้า")

conn.close()
print("เสร็จสิ้น")
