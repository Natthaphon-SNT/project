# -*- coding: utf-8 -*-
import sqlite3, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

conn = sqlite3.connect('shop.db')
cur = conn.cursor()
row = cur.execute("SELECT product_id, p_name, p_price, price_ihavecpu, category, cid, img_url, url_ihavecpu FROM products WHERE p_name LIKE '%WARTHOG%'").fetchone()
print("Corsair Warthog Case:")
print("  PID:     ", row[0])
print("  Name:    ", row[1])
print("  Price:   ", row[2])
print("  iHC:     ", row[3])
print("  Category:", row[4], f"({row[5]})")
print("  Image:   ", row[6])
print("  URL:     ", row[7])

print("\nCategory Distribution:")
for cat, cid, count in cur.execute("SELECT category, cid, COUNT(*) FROM products GROUP BY category, cid ORDER BY category").fetchall():
    print(f"  - {cat} ({cid}): {count} items")

conn.close()
