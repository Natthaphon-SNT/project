import sqlite3, asyncio, sys
import scraper as sc

# Step 1: Clear all scrape-originated products (keep only manually added ones if any)
conn = sqlite3.connect('shop.db')
cur = conn.cursor()
before = cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]
# Delete products that have at least one price set (these are all scrape products)
cur.execute("""
    DELETE FROM products
    WHERE price_advice > 0 OR price_jib > 0 OR price_ihavecpu > 0
    OR p_name LIKE 'CPU%' OR p_name LIKE 'MAINBOARD%' OR p_name LIKE 'VGA%'
    OR p_name LIKE 'RAM%' OR p_name LIKE 'SSD%' OR p_name LIKE 'PSU%'
    OR p_name LIKE 'CASE%' OR p_name LIKE 'COOLER%' OR p_name LIKE 'LIQUID%'
    OR p_name LIKE 'AMD%' OR p_name LIKE 'Intel%' OR p_name LIKE 'ASUS%'
    OR p_name LIKE 'MSI%' OR p_name LIKE 'GIGABYTE%' OR p_name LIKE 'CORSAIR%'
    OR p_name LIKE 'POWER SUPPLY%' OR p_name LIKE 'LCD%'
""")
conn.commit()
after = cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]
conn.close()
print(f'Cleared: {before} -> {after} products remaining')

# Step 2: Re-scrape all 3 stores fresh
print()
print('=== Re-scraping all stores ===')
r = asyncio.run(sc.run_scraper(['ihavecpu', 'jib'], pages=1))
print()
print('=== DONE ===')
for k, v in r.items(): print(f'  {k}: {v}')
print(f'  Total: {sum(r.values())}')

# Step 3: Show stats
conn = sqlite3.connect('shop.db')
cur = conn.cursor()
total = cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]
has_img = cur.execute("SELECT COUNT(*) FROM products WHERE img_url != '' AND img_url IS NOT NULL").fetchone()[0]
jib_c = cur.execute("SELECT COUNT(*) FROM products WHERE price_jib > 0").fetchone()[0]
ihc_c = cur.execute("SELECT COUNT(*) FROM products WHERE price_ihavecpu > 0").fetchone()[0]
print(f'\nFinal: Total={total} | JIB={jib_c} | IHC={ihc_c} | WithImg={has_img}')
conn.close()
