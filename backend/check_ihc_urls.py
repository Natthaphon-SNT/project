# -*- coding: utf-8 -*-
import sqlite3, re

conn = sqlite3.connect('shop.db')
cur = conn.cursor()

rows = cur.execute("SELECT product_id, p_name, url_ihavecpu FROM products WHERE url_ihavecpu != ''").fetchall()
bad_urls = []
for pid, name, url in rows:
    # URL without slug e.g. https://ihavecpu.com/product/48898 (only numbers at end)
    if re.search(r'ihavecpu\.com/product/\d+/?$', url):
        bad_urls.append((pid, name, url))

print(f"Total iHaveCPU URLs: {len(rows)}")
print(f"URLs without slug (broken 404): {len(bad_urls)}")
for b in bad_urls[:10]:
    print(b)
conn.close()
