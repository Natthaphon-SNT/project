import sqlite3, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
conn = sqlite3.connect('shop.db')
c = conn.cursor()
t   = c.execute('SELECT COUNT(*) FROM products').fetchone()[0]
adv = c.execute('SELECT COUNT(*) FROM products WHERE price_advice > 0').fetchone()[0]
jib = c.execute('SELECT COUNT(*) FROM products WHERE price_jib > 0').fetchone()[0]
ihc = c.execute('SELECT COUNT(*) FROM products WHERE price_ihavecpu > 0').fetchone()[0]
img = c.execute("SELECT COUNT(*) FROM products WHERE img_url IS NOT NULL AND length(img_url)>5").fetchone()[0]
print(f'Total={t} Advice={adv} JIB={jib} IHC={ihc} WithImg={img}')
cats = c.execute('SELECT category, COUNT(*) FROM products GROUP BY category ORDER BY 2 DESC').fetchall()
for x in cats: print(f'  {x[0]}: {x[1]}')
print()
samp = c.execute("SELECT p_name, price_jib, price_ihavecpu, img_url FROM products WHERE price_jib>0 AND img_url IS NOT NULL AND length(img_url)>5 LIMIT 3").fetchall()
print('Sample JIB with img:')
for x in samp: print(f'  {x[0][:45]} | jib={x[1]} ihc={x[2]} | img={x[3][:50]}')
conn.close()
