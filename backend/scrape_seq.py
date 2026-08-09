"""Run scrapers sequentially (not parallel) to fix SQLite concurrent write issue"""
import asyncio, sqlite3, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import scraper as sc

async def main():
    # Sequential: avoid SQLite concurrent writes
    print('=== iHaveCPU ===')
    r1 = await sc.scrape_ihavecpu(2)
    print(f'iHaveCPU total: {r1}')
    
    print()
    print('=== JIB ===')
    r2 = await sc.scrape_jib(5)
    print(f'JIB total: {r2}')
    
    # Stats
    conn = sqlite3.connect('shop.db')
    cur = conn.cursor()
    total  = cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    jib    = cur.execute('SELECT COUNT(*) FROM products WHERE price_jib > 0').fetchone()[0]
    ihc    = cur.execute('SELECT COUNT(*) FROM products WHERE price_ihavecpu > 0').fetchone()[0]
    imgs   = cur.execute('SELECT COUNT(*) FROM products WHERE img_url IS NOT NULL AND length(img_url) > 5').fetchone()[0]
    print(f'\nDB: total={total} jib={jib} ihc={ihc} imgs={imgs}')
    conn.close()

asyncio.run(main())
