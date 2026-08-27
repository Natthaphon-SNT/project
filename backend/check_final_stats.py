# -*- coding: utf-8 -*-
import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = sqlite3.connect('shop.db')
cur = conn.cursor()
adv_search = cur.execute("SELECT COUNT(*) FROM products WHERE url_advice LIKE '%search?keyword%'").fetchone()[0]
adv_empty_img = cur.execute("SELECT COUNT(*) FROM products WHERE price_advice > 0 AND (img_url = '' OR img_url IS NULL)").fetchone()[0]
total = cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]
print(f'Total products in DB: {total}')
print(f'Remaining Advice search?keyword URLs: {adv_search}')
print(f'Remaining Advice products with empty img_url: {adv_empty_img}')
conn.close()
