# -*- coding: utf-8 -*-
import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = sqlite3.connect('shop.db')
cur = conn.cursor()
cols = [c[1] for c in cur.execute('PRAGMA table_info(products)').fetchall()]
rows = cur.execute("SELECT * FROM products WHERE p_name LIKE '%250K%' LIMIT 1").fetchall()
if rows:
    d = dict(zip(cols, rows[0]))
    for k, v in d.items():
        print(f'{k}: {v}')
conn.close()
