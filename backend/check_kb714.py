# -*- coding: utf-8 -*-
import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = sqlite3.connect('shop.db')
cur = conn.cursor()
cols = [c[1] for c in cur.execute('PRAGMA table_info(products)').fetchall()]
rows = cur.execute("SELECT * FROM products WHERE p_name LIKE '%KB-714%' OR p_name LIKE '%NESTTER%'").fetchall()
for r in rows:
    d = dict(zip(cols, r))
    for k, v in d.items():
        print(f'{k}: {v}')
    print('-'*40)

adv_search = cur.execute("SELECT COUNT(*) FROM products WHERE url_advice LIKE '%search?keyword%'").fetchone()[0]
adv_empty_img = cur.execute("SELECT COUNT(*) FROM products WHERE price_advice > 0 AND (img_url = '' OR img_url IS NULL)").fetchone()[0]
print(f'Advice products with search?keyword URL: {adv_search}')
print(f'Advice products with empty img_url: {adv_empty_img}')
conn.close()
