import sqlite3
conn = sqlite3.connect('shop.db')
cur = conn.cursor()
total = cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]
adv   = cur.execute('SELECT COUNT(*) FROM products WHERE price_advice > 0').fetchone()[0]
jib   = cur.execute('SELECT COUNT(*) FROM products WHERE price_jib > 0').fetchone()[0]
ihc   = cur.execute('SELECT COUNT(*) FROM products WHERE price_ihavecpu > 0').fetchone()[0]
imgs  = cur.execute("SELECT COUNT(*) FROM products WHERE img_url != '' AND img_url IS NOT NULL").fetchone()[0]
print(f'Total={total} | Advice={adv} | JIB={jib} | iHaveCPU={ihc} | WithImg={imgs}')
print()
print('--- Sample JIB ---')
rows = cur.execute('SELECT p_name, category, price_jib, img_url FROM products WHERE price_jib > 0 LIMIT 5').fetchall()
for r in rows: print(f'  [{r[1]}] {r[0][:45]} | {r[2]}bht | img={r[3][:60]}')
print()
print('--- Sample iHaveCPU CPU ---')
rows2 = cur.execute("SELECT p_name, price_ihavecpu, img_url FROM products WHERE price_ihavecpu > 0 AND category='CPU' LIMIT 5").fetchall()
for r in rows2: print(f'  {r[0][:50]} | {r[1]}bht | img={r[2][:60]}')
conn.close()
