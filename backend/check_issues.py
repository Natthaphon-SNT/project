# -*- coding: utf-8 -*-
import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = sqlite3.connect('shop.db')
cur = conn.cursor()

# 1. Vacuum cleaner check
rows = cur.execute("SELECT product_id, p_name, category, cid FROM products WHERE p_name LIKE '%VACUUM%' OR p_name LIKE '%เครื่องดูดฝุ่น%'").fetchall()
print(f"Vacuum cleaners count: {len(rows)}")
for r in rows[:5]:
    print(r)

# 2. iHaveCPU AUG26-D4-001 check
print("\n--- AUG26-D4-001 check ---")
rows2 = cur.execute("SELECT product_id, p_name, price_ihavecpu, url_ihavecpu FROM products WHERE p_name LIKE '%AUG26%' OR p_name LIKE '%5500GT%'").fetchall()
for r in rows2:
    print(r)

# 3. Cooler categories check
print("\n--- Cooler categories in DB ---")
rows3 = cur.execute("SELECT category, cid, COUNT(*) FROM products WHERE category LIKE '%Cooler%' OR category LIKE '%liquid%' OR category LIKE '%air%' GROUP BY category, cid").fetchall()
for r in rows3:
    print(r)

# 4. All categories check
print("\n--- All categories in DB ---")
rows4 = cur.execute("SELECT category, cid, COUNT(*) FROM products GROUP BY category, cid").fetchall()
for r in rows4:
    print(r)

conn.close()
