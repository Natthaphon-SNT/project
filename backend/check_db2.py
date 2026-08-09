import sqlite3
conn = sqlite3.connect('shop.db')
cur = conn.cursor()
total = cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]
has_img = cur.execute("SELECT COUNT(*) FROM products WHERE img_url != '' AND img_url IS NOT NULL AND img_url != 'None'").fetchone()[0]
jib_img = cur.execute("SELECT COUNT(*) FROM products WHERE price_jib > 0 AND img_url != '' AND img_url IS NOT NULL").fetchone()[0]
ihc_img = cur.execute("SELECT COUNT(*) FROM products WHERE price_ihavecpu > 0 AND img_url != '' AND img_url IS NOT NULL").fetchone()[0]
print(f'Total={total} | WithImg={has_img} | JIBwithImg={jib_img} | IHCwithImg={ihc_img}')
print()
# Sample new products with image
rows = cur.execute("SELECT p_name, category, price_jib, img_url FROM products WHERE price_jib > 0 AND img_url != '' LIMIT 5").fetchall()
print('--- JIB with images ---')
for r in rows: print(f'  [{r[1]}] {r[0][:45]} | {r[2]}bht | {r[3][:60]}')
print()
rows2 = cur.execute("SELECT p_name, category, price_ihavecpu, img_url FROM products WHERE price_ihavecpu > 0 AND img_url != '' AND category='CPU' LIMIT 5").fetchall()
print('--- iHaveCPU CPU with images ---')
for r in rows2: print(f'  {r[0][:45]} | {r[2]}bht | {r[3][:60]}')
print()
# Show sample img_url values
sample = cur.execute("SELECT img_url FROM products WHERE img_url != '' LIMIT 3").fetchall()
print('--- Sample img_url ---')
for r in sample: print(f'  {r[0][:80]}')
conn.close()
