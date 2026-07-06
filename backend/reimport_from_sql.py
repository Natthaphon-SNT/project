"""
Reimport สินค้าจาก pc_part.sql โดยตรง (มีรูปภาพครบ)
รัน: python reimport_from_sql.py
"""
import sqlite3, re, sys
from pathlib import Path

DB_PATH    = "shop.db"
SQL_PATH   = "../docs/pc_part.sql"

def parse_sql_products(sql_path: str) -> list[dict]:
    """แยก products ทั้งหมดจากไฟล์ SQL"""
    text = Path(sql_path).read_text(encoding="utf-8", errors="ignore")

    # หา block INSERT ของ products
    block_re = re.compile(
        r"INSERT INTO `products`.*?VALUES(.*?);\s*\n\s*--",
        re.DOTALL
    )

    all_rows = []
    for block in block_re.finditer(text):
        values_str = block.group(1)
        # แยกแต่ละ row
        row_re = re.compile(
            r"\('([^']+)',\s*'((?:[^'\\]|\\.)*)',\s*'((?:[^'\\]|\\.)*)',\s*"
            r"([\d.]+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*'([^']*)',\s*'([^']*)'\)"
        )
        for m in row_re.finditer(values_str):
            all_rows.append({
                "product_id":    m.group(1),
                "p_name":        m.group(2).replace("\\r\\n", "\n").replace("\\'", "'"),
                "p_description": m.group(3).replace("\\r\\n", "\n").replace("\\'", "'"),
                "p_price":       float(m.group(4)),
                "price_advice":  int(m.group(5)),
                "price_jib":     int(m.group(6)),
                "price_ihavecpu":int(m.group(7)),
                "p_stock":       int(m.group(8)),
                "cid":           m.group(9),
                "img_url":       m.group(10),
            })
    return all_rows

# map cid → category name
CID_MAP = {
    "c01": "CPU",     "c02": "Mainboard", "c03": "GPU",
    "c04": "RAM",     "c05": "M.2",       "c06": "PSU",
    "c07": "Case",    "c08": "Liquid Cooler", "c09": "Air Cooler",
}

def reimport():
    sql_file = Path(SQL_PATH)
    if not sql_file.exists():
        print(f"[ERROR] ไม่พบ {SQL_PATH}")
        sys.exit(1)

    products = parse_sql_products(SQL_PATH)
    print(f"[INFO] พบสินค้าใน SQL: {len(products)} รายการ")
    if not products:
        print("[WARN] ไม่พบข้อมูลสินค้า — ตรวจสอบ regex")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    count = 0
    skip  = 0
    for p in products:
        category = CID_MAP.get(p["cid"], p["cid"])
        try:
            cur.execute("""
                INSERT OR REPLACE INTO products
                (product_id, p_name, p_description, p_price,
                 price_advice, price_jib, price_ihavecpu,
                 p_stock, cid, category, img_url)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (
                p["product_id"], p["p_name"], p["p_description"], p["p_price"],
                p["price_advice"], p["price_jib"], p["price_ihavecpu"],
                p["p_stock"], p["cid"], category, p["img_url"]
            ))
            count += 1
        except Exception as e:
            skip += 1

    conn.commit()

    total    = cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    has_img  = cur.execute("SELECT COUNT(*) FROM products WHERE img_url != '' AND img_url IS NOT NULL").fetchone()[0]
    no_img   = total - has_img

    print(f"[OK]   Import สำเร็จ: {count} | ข้าม: {skip}")
    print(f"[INFO] รวมสินค้าทั้งหมด: {total}")
    print(f"[INFO] มีรูปภาพ: {has_img} | ไม่มีรูป: {no_img}")
    conn.close()

if __name__ == "__main__":
    reimport()
