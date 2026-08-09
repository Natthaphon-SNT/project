
import sqlite3, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
conn = sqlite3.connect('shop.db')
cur = conn.cursor()
total  = cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]
adv    = cur.execute('SELECT COUNT(*) FROM products WHERE price_advice > 0').fetchone()[0]
jib    = cur.execute('SELECT COUNT(*) FROM products WHERE price_jib > 0').fetchone()[0]
ihc    = cur.execute('SELECT COUNT(*) FROM products WHERE price_ihavecpu > 0').fetchone()[0]
has_img = cur.execute('SELECT COUNT(*) FROM products WHERE img_url IS NOT NULL AND length(img_url) > 5').fetchone()[0]
print(f'TOTAL={total} | Advice={adv} | JIB={jib} | iHaveCPU={ihc} | WithImg={has_img}')
cats = cur.execute('SELECT category, COUNT(*) FROM products GROUP BY category ORDER BY 2 DESC').fetchall()
for c in cats: print(f'  {c[0]}: {c[1]}')
print()
r1 = cur.execute('SELECT p_name, price_jib, img_url FROM products WHERE price_jib > 0 LIMIT 3').fetchall()
for x in r1: print('JIB:', x[0][:45], x[1], x[2][:50] if x[2] else 'NO_IMG')
r2 = cur.execute('SELECT p_name, price_ihavecpu, img_url FROM products WHERE price_ihavecpu > 0 AND category=chr(67)+chr(80)+chr(85) LIMIT 3').fetchall()
for x in r2: print('IHC:', x[0][:45], x[1], x[2][:50] if x[2] else 'NO_IMG')
r3 = cur.execute('SELECT p_name, price_advice, img_url FROM products WHERE price_advice > 0 LIMIT 3').fetchall()
for x in r3: print('ADV:', x[0][:45], x[1], x[2][:50] if x[2] else 'NO_IMG')
conn.close()

