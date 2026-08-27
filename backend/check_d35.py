# -*- coding: utf-8 -*-
import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = sqlite3.connect('shop.db')
cur = conn.cursor()
cols = [c[1] for c in cur.execute('PRAGMA table_info(products)').fetchall()]
rows = cur.execute("SELECT * FROM products WHERE p_name LIKE '%D35%' OR p_name LIKE '%AX4U320016G%'").fetchall()
for r in rows:
    d = dict(zip(cols, r))
    for k, v in d.items():
        print(f'{k}: {v}')
    print('-'*40)

# Also check how many iHaveCPU products have empty img_url or wrong category
ihc_empty_img = cur.execute("SELECT COUNT(*) FROM products WHERE price_ihavecpu > 0 AND (img_url = '' OR img_url IS NULL)").fetchone()[0]
print(f'iHaveCPU products with empty img_url: {ihc_empty_img}')

# Check all products with empty img_url
all_empty_img = cur.execute("SELECT COUNT(*) FROM products WHERE img_url = '' OR img_url IS NULL").fetchall()[0][0]
print(f'Total products in DB with empty img_url: {all_empty_img}')

conn.close()
