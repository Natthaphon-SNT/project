# -*- coding: utf-8 -*-
"""
1. Remove vacuum cleaners from shop.db
2. Fix 14 broken iHaveCPU PC set URLs with valid slugs
"""
import sqlite3
import re
import urllib.parse

DB_PATH = "shop.db"

def slugify(text: str) -> str:
    # Match iHaveCPU slug format: lowercase, replace spaces/slashes with -
    s = text.lower()
    s = re.sub(r'[\s/\\+_]+', '-', s)
    s = re.sub(r'[^a-z0-9\.\-\(\)]', '', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s

def fix_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Delete vacuum cleaners
    cur.execute("SELECT COUNT(*) FROM products WHERE p_name LIKE '%VACUUM%' OR p_name LIKE '%เครื่องดูดฝุ่น%' OR p_name LIKE '%ROBOT VACUUM%'")
    vac_count = cur.fetchone()[0]
    cur.execute("DELETE FROM products WHERE p_name LIKE '%VACUUM%' OR p_name LIKE '%เครื่องดูดฝุ่น%' OR p_name LIKE '%ROBOT VACUUM%'")
    print(f"[1] Deleted {vac_count} vacuum cleaners from shop.db")

    # 2. Fix broken iHaveCPU URLs (without slug)
    rows = cur.execute("SELECT product_id, p_name, url_ihavecpu FROM products WHERE url_ihavecpu != ''").fetchall()
    fixed_count = 0
    for pid, name, url in rows:
        m = re.search(r'ihavecpu\.com/product/(\d+)/?$', url)
        if m:
            item_id = m.group(1)
            slug = slugify(name)
            new_url = f"https://ihavecpu.com/product/{item_id}/{slug}"
            cur.execute("UPDATE products SET url_ihavecpu = ? WHERE product_id = ?", (new_url, pid))
            fixed_count += 1
            print(f"Fixed URL for [{name[:40]}...]:\n  -> {new_url}")

    conn.commit()
    print(f"\n[2] Fixed {fixed_count} iHaveCPU product URLs.")
    conn.close()

if __name__ == "__main__":
    fix_db()
