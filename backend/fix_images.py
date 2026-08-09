"""Update img_url for existing products by re-scraping with image fix"""
import asyncio, re, sqlite3, sys
sys.path.insert(0, '.')

# Patch upsert to always update img
import scraper as sc

# Override upsert to force-update images
_orig_upsert = sc.upsert_product
def upsert_with_img(cur, p):
    store = p.get('store','')
    price_col = {'advice':'price_advice','jib':'price_jib','ihavecpu':'price_ihavecpu'}.get(store,'price_advice')
    price = p.get('price', 0)
    name  = p.get('name','').strip()
    img   = p.get('img_url','').strip()
    cat   = p.get('category','')
    cid   = sc.get_cid(cat)
    if not name or not price: return
    pid = sc.make_pid(name, store)
    existing = cur.execute("SELECT product_id FROM products WHERE p_name = ?", (name,)).fetchone()
    if existing:
        pid = existing[0]
        cur.execute(f"""
            UPDATE products SET {price_col}=?,
            p_price = CASE WHEN p_price=0 THEN ? ELSE p_price END,
            img_url = CASE WHEN ?!='' THEN ? ELSE img_url END
            WHERE product_id=?
        """, (price, price, img, img, pid))
    else:
        from datetime import datetime
        cur.execute("""
            INSERT OR IGNORE INTO products
            (product_id,p_name,p_description,p_price,price_advice,price_jib,price_ihavecpu,
             p_stock,cid,category,img_url,specs,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (pid, name, p.get('description',''), price,
              price if store=='advice'   else 0,
              price if store=='jib'      else 0,
              price if store=='ihavecpu' else 0,
              99, cid, cat, img, '',
              datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    cur.connection.commit()

sc.upsert_product = upsert_with_img

async def main():
    print('=== Fixing images: JIB (5 pages) ===')
    r1 = await sc.scrape_jib(5)
    print(f'JIB: {r1}')
    print()
    print('=== Fixing images: iHaveCPU (1 page) ===')
    r2 = await sc.scrape_ihavecpu(1)
    print(f'iHaveCPU: {r2}')

asyncio.run(main())
