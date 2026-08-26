import sqlite3
conn = sqlite3.connect('shop.db')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM products')
total = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM products WHERE desc_advice != '' AND desc_advice IS NOT NULL")
adv = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM products WHERE desc_jib != '' AND desc_jib IS NOT NULL")
jib = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM products WHERE desc_ihavecpu != '' AND desc_ihavecpu IS NOT NULL")
ihc = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM products WHERE img_url != '' AND img_url IS NOT NULL")
img_count = cur.fetchone()[0]
print(f'Total: {total}')
print(f'desc_advice filled: {adv}')
print(f'desc_jib filled: {jib}')
print(f'desc_ihavecpu filled: {ihc}')
print(f'img_url filled: {img_count}')

# Check for notebook products
cur.execute("SELECT p_name, category FROM products WHERE UPPER(p_name) LIKE '%NOTEBOOK%' OR UPPER(p_name) LIKE '%LAPTOP%' LIMIT 5")
rows = cur.fetchall()
print(f'\nNotebook/Laptop in DB: {len(rows)} samples')
for r in rows:
    print(f'  {r[0][:60]} | cat: {r[1]}')

# Sample products
cur.execute("SELECT p_name, category, img_url, desc_advice FROM products WHERE price_advice > 0 LIMIT 3")
rows = cur.fetchall()
print('\nSample Advice products:')
for r in rows:
    print(f'  {r[0][:50]} | {r[1]} | img:{bool(r[2])} | desc_adv:{len(r[3] or "")}')
conn.close()
