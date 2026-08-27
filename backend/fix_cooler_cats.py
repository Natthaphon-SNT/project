# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('shop.db')
cur = conn.cursor()

# If name contains COOLER or LIQUID or WATER, it must be cooler, NOT CPU
cur.execute("""
    UPDATE products 
    SET category = 'Liquid Cooler', cid = 'c08'
    WHERE (p_name LIKE '%LIQUID COOLER%' OR p_name LIKE '%AIO COOLER%' OR p_name LIKE '%WATER COOL%')
""")

cur.execute("""
    UPDATE products 
    SET category = 'Air Cooler', cid = 'c09'
    WHERE (p_name LIKE '%CPU COOLER%' OR p_name LIKE '%AIR COOLER%' OR p_name LIKE '%HEAT SINK%')
      AND p_name NOT LIKE '%LIQUID%' AND p_name NOT LIKE '%AIO%' AND p_name NOT LIKE '%WATER%'
""")

conn.commit()

# Verify
rows = cur.execute("SELECT product_id, p_name, category, cid FROM products WHERE p_name LIKE '%CPU COOLER%' LIMIT 5").fetchall()
for r in rows:
    print(r)

conn.close()
