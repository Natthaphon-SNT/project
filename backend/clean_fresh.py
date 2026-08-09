import sqlite3, asyncio, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import importlib, scraper
importlib.reload(scraper)
import scraper as sc

# Clear DB
conn = sqlite3.connect('shop.db')
cur = conn.cursor()
before = cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]
cur.execute('DELETE FROM products')
conn.commit()
conn.close()
print(f'Cleared: {before} -> 0')

async def main():
    print('\n=== iHaveCPU (2 pages) ===')
    r1 = await sc.scrape_ihavecpu(2)
    print(f'iHaveCPU: {r1}')

    print('\n=== JIB (5 pages) ===')
    r2 = await sc.scrape_jib(5)
    print(f'JIB: {r2}')

    conn2 = sqlite3.connect('shop.db')
    cur2 = conn2.cursor()
    total = cur2.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    jib   = cur2.execute('SELECT COUNT(*) FROM products WHERE price_jib > 0').fetchone()[0]
    ihc   = cur2.execute('SELECT COUNT(*) FROM products WHERE price_ihavecpu > 0').fetchone()[0]
    imgs  = cur2.execute("SELECT COUNT(*) FROM products WHERE img_url IS NOT NULL AND length(img_url)>5").fetchone()[0]
    print(f'\n=== DONE ===')
    print(f'Total={total} | JIB={jib} | IHC={ihc} | WithImg={imgs}')
    cats = cur2.execute('SELECT category, COUNT(*) FROM products GROUP BY category ORDER BY 2 DESC').fetchall()
    for c in cats: print(f'  {c[0]}: {c[1]}')
    conn2.close()

asyncio.run(main())
