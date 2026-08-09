"""
migrate_db.py - Add url/desc columns and fix Advice URL data
"""
import sqlite3

DB = 'shop.db'
conn = sqlite3.connect(DB)
cur = conn.cursor()

# 1. Add new columns
new_cols = [
    ('url_advice',    "TEXT DEFAULT ''"),
    ('url_jib',       "TEXT DEFAULT ''"),
    ('url_ihavecpu',  "TEXT DEFAULT ''"),
    ('desc_advice',   "TEXT DEFAULT ''"),
    ('desc_jib',      "TEXT DEFAULT ''"),
    ('desc_ihavecpu', "TEXT DEFAULT ''"),
]

cur.execute('PRAGMA table_info(products)')
existing = {row[1] for row in cur.fetchall()}
print('Existing columns:', sorted(existing))

for col, defn in new_cols:
    if col not in existing:
        cur.execute(f'ALTER TABLE products ADD COLUMN {col} {defn}')
        print(f'  [+] Added column: {col}')
    else:
        print(f'  [ok] Already exists: {col}')

conn.commit()

# 2. Move href from p_description to url_advice (old scraper stored href there)
cur.execute("""
    UPDATE products
    SET url_advice = p_description,
        p_description = ''
    WHERE (p_description LIKE 'http%advice%' OR p_description LIKE 'https://www.advice%')
    AND (url_advice IS NULL OR url_advice = '')
""")
updated = cur.rowcount
conn.commit()
print(f'\n[Fix] Moved {updated} Advice URLs: p_description -> url_advice')

# 3. Stats
cur.execute('SELECT COUNT(*) FROM products')
total = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM products WHERE price_advice > 0")
adv_price = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM products WHERE price_jib > 0")
jib_price = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM products WHERE price_ihavecpu > 0")
ihc_price = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM products WHERE url_advice != ''")
adv_url = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM products WHERE url_jib != ''")
jib_url = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM products WHERE url_ihavecpu != ''")
ihc_url = cur.fetchone()[0]

print(f'\n=== Database Status ===')
print(f'Total products:         {total}')
print(f'Advice  (price / url):  {adv_price} / {adv_url}')
print(f'JIB     (price / url):  {jib_price} / {jib_url}')
print(f'iHaveCPU (price / url): {ihc_price} / {ihc_url}')

# Sample URL check
cur.execute("SELECT p_name, url_jib FROM products WHERE url_jib != '' LIMIT 3")
rows = cur.fetchall()
print(f'\nSample JIB URLs:')
for r in rows:
    print(f'  {r[0][:40]} -> {r[1][:60]}')

cur.execute("SELECT p_name, url_ihavecpu FROM products WHERE url_ihavecpu != '' LIMIT 3")
rows = cur.fetchall()
print(f'\nSample iHaveCPU URLs:')
for r in rows:
    print(f'  {r[0][:40]} -> {r[1][:60]}')

conn.close()
print('\nMigration complete!')
