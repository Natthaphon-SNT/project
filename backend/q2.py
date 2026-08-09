import sqlite3, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
conn = sqlite3.connect('shop.db')
cur = conn.cursor()
total  = cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]
adv    = cur.execute('SELECT COUNT(*) FROM products WHERE price_advice > 0').fetchone()[0]
jib    = cur.execute('SELECT COUNT(*) FROM products WHERE price_jib > 0').fetchone()[0]
ihc    = cur.execute('SELECT COUNT(*) FROM products WHERE price_ihavecpu > 0').fetchone()[0]
has_img = cur.execute('SELECT COUNT(*) FROM products WHERE img_url IS NOT NULL AND length(img_url) > 5').fetchone()[0]
print(f'TOTAL={total}')
print(f'Advice={adv} | JIB={jib} | iHaveCPU={ihc} | WithImg={has_img}')
cats = cur.execute('SELECT category, COUNT(*) FROM products GROUP BY category ORDER BY 2 DESC').fetchall()
print('Categories:')
for c in cats: print(f'  {c[0]}: {c[1]}')
r1 = cur.execute('SELECT p_name, price_advice, price_jib, price_ihavecpu, img_url FROM products WHERE price_ihavecpu > 0 LIMIT 3').fetchall()
print()
print('Sample IHC products:')
for x in r1: print(f'  {x[0][:40]} adv={x[1]} jib={x[2]} ihc={x[3]} img={bool(x[4] and len(x[4])>5)}')
conn.close()
