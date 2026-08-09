"""One script - clear DB then scrape all 3 stores sequentially. No imports of stale modules."""
import sqlite3, asyncio, re, sys, io, hashlib
from datetime import datetime
from playwright.async_api import async_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB_PATH = 'shop.db'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36'
ANTI_BOT = "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});window.chrome={runtime:{}};"

ADVICE_CATS = [
    ('CPU','https://www.advice.co.th/product/cpu'),
    ('Mainboard','https://www.advice.co.th/product/mainboard'),
    ('GPU','https://www.advice.co.th/product/graphic-card'),
    ('RAM','https://www.advice.co.th/product/ram'),
    ('SSD','https://www.advice.co.th/product/ssd-harddisk'),
    ('PSU','https://www.advice.co.th/product/power-supply'),
    ('Case','https://www.advice.co.th/product/case'),
    ('Liquid Cooler','https://www.advice.co.th/product/liquid-cooling'),
    ('Air Cooler','https://www.advice.co.th/product/cpu-cooler'),
]
JIB_CATS = [
    ('CPU', 'https://www.jib.co.th/web/product/product_list/2/43'),
    ('Mainboard', 'https://www.jib.co.th/web/product/product_list/2/46'),
    ('GPU', 'https://www.jib.co.th/web/product/product_list/2/51'),
    ('RAM', 'https://www.jib.co.th/web/product/product_list/2/53'),
    ('SSD', 'https://www.jib.co.th/web/product/product_list/2/52'),
    ('PSU', 'https://www.jib.co.th/web/product/product_list/3/185'),
    ('Case', 'https://www.jib.co.th/web/product/product_list/3/184'),
    ('Liquid Cooler', 'https://www.jib.co.th/web/product/product_list/2/1438'),
    ('Air Cooler', 'https://www.jib.co.th/web/product/product_list/2/1367'),
]
IHC_CATS = [
    ('CPU','https://www.ihavecpu.com/category/cpu'),
    ('Mainboard','https://www.ihavecpu.com/category/mainboard'),
    ('GPU','https://www.ihavecpu.com/category/graphic-card'),
    ('RAM','https://www.ihavecpu.com/category/ram'),
    ('SSD','https://www.ihavecpu.com/category/storage'),
    ('PSU','https://www.ihavecpu.com/category/power-supply'),
    ('Case','https://www.ihavecpu.com/category/case'),
    ('Cooler','https://www.ihavecpu.com/category/heat-sink'),
]
IHC_SKIP = ['GAMING CHAIR','DESK','TABLE','CHAIR','WEBCAM','MICROPHONE','HEADSET',
            'KEYBOARD','MOUSE','MOUSEPAD','GAMEPAD','JOYSTICK','SPEAKER',
            'EXTERNAL','PROJECTOR','PRINTER','UPS','NETWORK','ROUTER','NAS','BY ORDER']
CID_MAP = {'cpu':'c01','mainboard':'c02','gpu':'c03','vga':'c03',
           'ram':'c04','ssd':'c05','psu':'c06','case':'c07',
           'liquid':'c08','air cooler':'c09','cooler':'c09'}

def parse_price(t):
    if not t: return 0
    t = t.strip().replace(',','').replace('\u0e3f','').replace('THB','')
    m = re.search(r'\d+(?:\.\d+)?', t)
    if not m: return 0
    try: n = int(float(m.group(0)))
    except: return 0
    return n if 200 <= n <= 200000 else 0

def get_cid(cat):
    c = cat.lower()
    for k,v in CID_MAP.items():
        if k in c: return v
    return 'c10'

def make_pid(name, store):
    slug = re.sub(r'[^a-z0-9]','',name.lower())[:12]
    h = hashlib.md5(f'{name}|{store}'.encode()).hexdigest()[:8]
    return f'{slug}_{store[:3]}_{h}'

def clean_ihc(name):
    name = re.sub(r'^\[.*?\]\s*','',name).strip()
    m = re.match(r'^([A-Z0-9/\-\. ]+?)\s*\([^\)]+\)\s*(.*)',name)
    return (m.group(1).strip()+' '+m.group(2).strip()).strip() if m else name

def ihc_ok(name):
    nu = name.upper()
    return not any(s in nu for s in IHC_SKIP)

def jib_cat(name):
    nu = name.upper()
    for s in JIB_SKIP:
        if nu.startswith(s): return None
    for p,c in JIB_PREFIX_MAP.items():
        if nu.startswith(p): return c
    return None

def upsert(cur, name, price, img, cat, store, desc=''):
    if not name or not price: return
    price_col = {'advice':'price_advice','jib':'price_jib','ihavecpu':'price_ihavecpu'}.get(store,'price_advice')
    cid = get_cid(cat)
    pid = make_pid(name, store)
    ex = cur.execute('SELECT product_id FROM products WHERE p_name=?',(name,)).fetchone()
    if ex:
        cur.execute(f'UPDATE products SET {price_col}=?, p_price=CASE WHEN p_price=0 THEN ? ELSE p_price END, img_url=CASE WHEN ?!=\'\' THEN ? ELSE img_url END WHERE product_id=?',
                    (price,price,img,img,ex[0]))
    else:
        cur.execute('INSERT OR IGNORE INTO products (product_id,p_name,p_description,p_price,price_advice,price_jib,price_ihavecpu,p_stock,cid,category,img_url,specs,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (pid,name,desc,price,
                     price if store=='advice' else 0,
                     price if store=='jib' else 0,
                     price if store=='ihavecpu' else 0,
                     99,cid,cat,img,'',datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    cur.connection.commit()

async def scrape_advice(conn, pages=1):
    import random
    cur = conn.cursor()
    total = 0
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-blink-features=AutomationControlled'])
        for i,(cat,base) in enumerate(ADVICE_CATS):
            ctx = await browser.new_context(user_agent=UA, viewport={'width':random.randint(1200,1400),'height':800}, locale='th-TH')
            await ctx.add_init_script(ANTI_BOT)
            pg = await ctx.new_page()
            if i==0:
                try: await pg.goto('https://www.advice.co.th/',timeout=20000,wait_until='domcontentloaded'); await pg.wait_for_timeout(2000)
                except: pass
            ct = 0
            for pn in range(1,pages+1):
                url = base if pn==1 else f'{base}?page={pn}'
                print(f'  [Advice] {cat} p{pn}')
                try:
                    await pg.goto(url,timeout=40000,wait_until='networkidle')
                    await pg.wait_for_timeout(5000)
                    for y in [300,600,900]: await pg.evaluate(f'window.scrollTo(0,{y})'); await pg.wait_for_timeout(700)
                    await pg.wait_for_timeout(2000)
                except Exception as e: print(f'    err:{e}'); break
                cards = await pg.query_selector_all('div.list-product')
                if not cards: print('    no cards'); break
                for card in cards:
                    try:
                        ne = await card.query_selector('a.fn-name')
                        if not ne: continue
                        name = (await ne.inner_text()).strip()
                        if not name: continue
                        price = 0
                        for ps in ['span.item-price-sale','span.price-sale','.fn-price-sale','div.price-box span','strong.price']:
                            pe = await card.query_selector(ps)
                            if pe: price = parse_price(await pe.inner_text()); 
                            if price: break
                        if not price:
                            for sp in await card.query_selector_all('span,strong'):
                                price = parse_price(await sp.inner_text())
                                if price: break
                        img = ''
                        ie = await card.query_selector('div.item-img img')
                        if ie: img = await ie.get_attribute('src') or ''
                        if not img:
                            ie2 = await card.query_selector("img[src*='advice']")
                            if ie2: img = await ie2.get_attribute('src') or ''
                        href = await ne.get_attribute('href') or ''
                        upsert(cur,name,price,img,cat,'advice',href)
                        ct += 1
                    except: pass
                print(f'    -> {ct}')
                if ct==0: break
            total += ct
            print(f'  [Advice] {cat}: +{ct}')
            await ctx.close()
            await asyncio.sleep(random.uniform(3,5))
        await browser.close()
    return total

async def scrape_jib(conn, pages=2):
    cur = conn.cursor()
    total = 0
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-blink-features=AutomationControlled'])
        ctx = await browser.new_context(user_agent=UA, viewport={'width':1280,'height':800})
        await ctx.add_init_script(ANTI_BOT)
        pg = await ctx.new_page()
        for cat, base_url in JIB_CATS:
            cat_count = 0
            for pn in range(1, pages+1):
                offset = (pn - 1) * 100
                url = base_url if pn==1 else f'{base_url}/{offset}'
                print(f'  [JIB] {cat} page {pn} (offset {offset})')
                try:
                    await pg.goto(url, timeout=40000, wait_until='domcontentloaded')
                    await pg.wait_for_timeout(4000)
                except Exception as e:
                    print(f'    err: {e}')
                    break
                cards = await pg.query_selector_all('div.divboxpro')
                if not cards:
                    print('    no cards')
                    break
                ct = 0
                for card in cards:
                    try:
                        ne = await card.query_selector('span.promo_name')
                        if not ne: continue
                        name = (await ne.inner_text()).strip()
                        if not name: continue
                        pe = await card.query_selector('p.price_total')
                        price = parse_price(await pe.inner_text() if pe else '')
                        if not price: continue
                        img = ''
                        ie = await card.query_selector('img')
                        if ie:
                            img = await ie.get_attribute('src') or ''
                            if img and not img.startswith('http'): img = 'https://www.jib.co.th'+img
                        upsert(cur, name, price, img, cat, 'jib')
                        ct += 1
                    except: pass
                cat_count += ct
                print(f'    -> {ct} items')
                if ct < 30:
                    break
            total += cat_count
            print(f'  [JIB] {cat} total: {cat_count}')
            await asyncio.sleep(2)
        await browser.close()
    return total

async def scrape_ihavecpu(conn, pages=2):
    cur = conn.cursor()
    total = 0
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-blink-features=AutomationControlled'])
        ctx = await browser.new_context(user_agent=UA, viewport={'width':1280,'height':800})
        await ctx.add_init_script(ANTI_BOT)
        pg = await ctx.new_page()
        try: await pg.goto('https://www.ihavecpu.com/',timeout=20000,wait_until='domcontentloaded'); await pg.wait_for_timeout(2000)
        except: pass
        for cat,base in IHC_CATS:
            seen = set()
            ct = 0
            
            print(f'  [IHC] {cat} page 1')
            try:
                await pg.goto(base, timeout=30000, wait_until='domcontentloaded')
                await pg.wait_for_timeout(5000)
            except Exception as e:
                print(f'    err: {e}')
                continue
                
            for pn in range(1,pages+1):
                if pn > 1:
                    print(f'  [IHC] {cat} page {pn} (clicking next)')
                    next_btn = await pg.query_selector('li.next a, li.next button')
                    if not next_btn:
                        print('    no next button')
                        break
                    
                    try:
                        is_disabled = await pg.eval_on_selector('li.next', 'el => el.classList.contains("disabled")')
                    except:
                        is_disabled = False
                    if is_disabled:
                        print('    next page disabled')
                        break
                        
                    try:
                        await next_btn.click()
                        await pg.wait_for_timeout(5000)
                    except Exception as e:
                        print(f'    click err: {e}')
                        break
                        
                links = await pg.query_selector_all("a[href*='/product/']")
                if not links: print('    no products'); break
                pc = 0
                for le in links:
                    try:
                        h3 = await le.query_selector('h3')
                        if not h3: continue
                        raw = (await h3.inner_text()).strip()
                        if not raw or raw in seen: continue
                        seen.add(raw)
                        if not ihc_ok(raw): continue
                        name = clean_ihc(raw)
                        if not name: continue
                        price = 0
                        for sp in await le.query_selector_all('span'):
                            t = (await sp.inner_text()).strip()
                            p = parse_price(t)
                            if p: price=p; break
                        if not price: continue
                        img = ''
                        ie = await le.query_selector('img')
                        if ie:
                            img = await ie.get_attribute('src') or await ie.get_attribute('data-src') or ''
                            if img and not img.startswith('http'): img = 'https://www.ihavecpu.com'+img
                        actual_cat = cat
                        if cat == 'Cooler':
                            lower_name = name.lower()
                            if any(k in lower_name for k in ['liquid', 'water', '240', '360', '120', 'ปิด', 'ชุดน้ำ', 'ryujin', 'kraken', 'valkyrie', 'galahad', 'frozen']):
                                actual_cat = 'Liquid Cooler'
                            else:
                                actual_cat = 'Air Cooler'
                        upsert(cur,name,price,img,actual_cat,'ihavecpu')
                        pc += 1
                    except: pass
                ct += pc
                print(f'    -> {pc}')
                if pc==0: break
            total += ct
            print(f'  [IHC] {cat}: +{ct}')
        await browser.close()
    return total

async def main():
    # Clear
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    before = cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    cur.execute('DELETE FROM products')
    conn.commit()
    print(f'DB cleared: {before}->0\n')

    # Scrape sequentially using same connection
    print('=== iHaveCPU ===')
    r1 = await scrape_ihavecpu(conn, 2)
    print(f'iHaveCPU: {r1}')

    print('\n=== JIB ===')
    r2 = await scrape_jib(conn, 5)
    print(f'JIB: {r2}')

    print('\n=== Advice ===')
    r3 = await scrape_advice(conn, 1)
    print(f'Advice: {r3}')

    # Final stats
    t   = cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]
    adv = cur.execute('SELECT COUNT(*) FROM products WHERE price_advice>0').fetchone()[0]
    jib = cur.execute('SELECT COUNT(*) FROM products WHERE price_jib>0').fetchone()[0]
    ihc = cur.execute('SELECT COUNT(*) FROM products WHERE price_ihavecpu>0').fetchone()[0]
    img = cur.execute("SELECT COUNT(*) FROM products WHERE img_url IS NOT NULL AND length(img_url)>5").fetchone()[0]
    print(f'\n=== FINAL ===')
    print(f'Total={t} Advice={adv} JIB={jib} IHC={ihc} WithImg={img}')
    cats = cur.execute('SELECT category, COUNT(*) FROM products GROUP BY category ORDER BY 2 DESC').fetchall()
    for x in cats: print(f'  {x[0]}: {x[1]}')
    conn.close()

asyncio.run(main())
