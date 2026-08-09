import sqlite3, asyncio, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Step 1: Delete ALL products
conn = sqlite3.connect('shop.db')
cur = conn.cursor()
before = cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]
cur.execute('DELETE FROM products')
conn.commit()
after = cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]
conn.close()
print(f'Cleared DB: {before} -> {after}')

# Step 2: Reimport scraper (fresh - no old module cache)
import importlib, scraper
importlib.reload(scraper)
import scraper as sc

# Step 3: Scrape sequentially
async def main():
    print()
    print('=== iHaveCPU (2 pages) ===')
    r1 = await sc.scrape_ihavecpu(2)
    print(f'Done: {r1}')
    
    print()
    print('=== JIB (5 pages) ===')
    r2 = await sc.scrape_jib(5)
    print(f'Done: {r2}')
    
    # Final stats
    conn2 = sqlite3.connect('shop.db')
    cur2 = conn2.cursor()
    total = cur2.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    jib   = cur2.execute('SELECT COUNT(*) FROM products WHERE price_jib > 0').fetchone()[0]
    ihc   = cur2.execute('SELECT COUNT(*) FROM products WHERE price_ihavecpu > 0').fetchone()[0]
    imgs  = cur2.execute("SELECT COUNT(*) FROM products WHERE img_url IS NOT NULL AND length(img_url)>5").fetchone()[0]
    print(f'\n=== FINAL DB ===')
    print(f'Total={total} | JIB={jib} | IHC={ihc} | WithImg={imgs}')
    cats = cur2.execute('SELECT category, COUNT(*) FROM products GROUP BY category ORDER BY 2 DESC').fetchall()
    for c in cats: print(f'  {c[0]}: {c[1]}')
    conn2.close()

asyncio.run(main())
