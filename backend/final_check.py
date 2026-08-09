import sqlite3, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
conn = sqlite3.connect('shop.db')
cur = conn.cursor()
total  = cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]
adv    = cur.execute('SELECT COUNT(*) FROM products WHERE price_advice > 0').fetchone()[0]
jib    = cur.execute('SELECT COUNT(*) FROM products WHERE price_jib > 0').fetchone()[0]
ihc    = cur.execute('SELECT COUNT(*) FROM products WHERE price_ihavecpu > 0').fetchone()[0]
has_img = cur.execute("SELECT COUNT(*) FROM products WHERE img_url != '' AND img_url IS NOT NULL").fetchone()[0]
print(f'TOTAL={total} | Advice={adv} | JIB={jib} | iHaveCPU={ihc} | WithImg={has_img}')
print()
cats = cur.execute('SELECT category, COUNT(*) FROM products GROUP BY category ORDER BY 2 DESC').fetchall()
print('Categories:')
for c in cats: print(f'  {c[0]}: {c[1]}')
print()
sample = cur.execute("SELECT p_name, price_jib, img_url FROM products WHERE price_jib > 0 AND img_url != '' AND category='GPU' LIMIT 3").fetchall()
print('Sample GPU from JIB with image:')
for r in sample: print(f'  {r[0][:50]} | {r[1]}bht | {r[2][:65]}')
print()
sample2 = cur.execute("SELECT p_name, price_ihavecpu, img_url FROM products WHERE price_ihavecpu > 0 AND img_url != '' AND category='CPU' LIMIT 3").fetchall()
print('Sample CPU from iHaveCPU with image:')
for r in sample2: print(f'  {r[0][:50]} | {r[1]}bht | {r[2][:65]}')
conn.close()
