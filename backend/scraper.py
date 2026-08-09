"""
Web Scraper v4 - Advice / JIB / iHaveCPU
Scrapes: name, price, image, description, direct URL per store

Usage: python scraper.py [advice|jib|ihavecpu|all] [pages]
"""
import asyncio, re, sqlite3, sys
from datetime import datetime
from playwright.async_api import async_playwright

DB_PATH = "shop.db"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
ANTI_BOT = ("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            "window.chrome={runtime:{}};")

# ────────────────────────────────────────────────
# Advice categories
# ────────────────────────────────────────────────
ADVICE_CATS = [
    ("CPU",           "https://www.advice.co.th/product/cpu"),
    ("Mainboard",     "https://www.advice.co.th/product/mainboard"),
    ("GPU",           "https://www.advice.co.th/product/graphic-card"),
    ("RAM",           "https://www.advice.co.th/product/ram"),
    ("SSD",           "https://www.advice.co.th/product/ssd-harddisk"),
    ("PSU",           "https://www.advice.co.th/product/power-supply"),
    ("Case",          "https://www.advice.co.th/product/case"),
    ("Liquid Cooler", "https://www.advice.co.th/product/liquid-cooling"),
    ("Air Cooler",    "https://www.advice.co.th/product/cpu-cooler"),
    ("Monitor",       "https://www.advice.co.th/product/monitor"),
    ("Mouse",         "https://www.advice.co.th/product/mouse"),
    ("Keyboard",      "https://www.advice.co.th/product/keyboard"),
    ("Headset",       "https://www.advice.co.th/product/headset"),
    ("Gaming Chair",  "https://www.advice.co.th/product/gaming-chair"),
    ("Gaming Desk",   "https://www.advice.co.th/product/gaming-desk"),
]

# ────────────────────────────────────────────────
# JIB - DIY hardware pages
# ────────────────────────────────────────────────
JIB_DIY_BASE = "https://www.jib.co.th/web/product/product_list/3/2988"
JIB_PREFIX_MAP = {
    "CPU":            "CPU",
    "MAINBOARD":      "Mainboard",
    "VGA":            "GPU",
    "GRAPHIC CARD":   "GPU",
    "RAM":            "RAM",
    "SSD":            "SSD",
    "HARDDISK":       "SSD",
    "M.2":            "SSD",
    "POWER SUPPLY":   "PSU",
    "CASE":           "Case",
    "LIQUID COOLER":  "Liquid Cooler",
    "CPU COOLER":     "Air Cooler",
    "COOLER":         "Air Cooler",
    "LCD PANEL":      "Monitor",
    "MONITOR":        "Monitor",
    "KEYBOARD":       "Keyboard",
    "MOUSE":          "Mouse",
    "HEADSET":        "Headset",
    "MICROPHONE":     "Microphone",
}

JIB_SKIP_PREFIXES = {
    "MOUSE PAD", "SPEAKER", "WEBCAM", "HUB", "CABLE", "UPS",
    "JOYSTICK", "PRINTER", "EXTERNAL", "NAS", "ROUTER",
    "NETWORK", "ACCESS POINT", "SWITCH",
}

# ────────────────────────────────────────────────
# iHaveCPU categories
# ────────────────────────────────────────────────
IHC_CATS = [
    ("CPU",           "https://www.ihavecpu.com/category/cpu"),
    ("Mainboard",     "https://www.ihavecpu.com/category/mainboard"),
    ("GPU",           "https://www.ihavecpu.com/category/graphic-card"),
    ("RAM",           "https://www.ihavecpu.com/category/ram"),
    ("SSD",           "https://www.ihavecpu.com/category/storage"),
    ("PSU",           "https://www.ihavecpu.com/category/power-supply"),
    ("Case",          "https://www.ihavecpu.com/category/case"),
    ("Cooler",        "https://www.ihavecpu.com/category/heat-sink"),
    ("Monitor",       "https://www.ihavecpu.com/category/monitor"),
    ("Mouse",         "https://www.ihavecpu.com/category/mouse"),
    ("Keyboard",      "https://www.ihavecpu.com/category/keyboard"),
    ("Headset",       "https://www.ihavecpu.com/category/headphone"),
    ("Gaming Chair",  "https://www.ihavecpu.com/category/chair"),
    ("Gaming Desk",   "https://www.ihavecpu.com/category/desk"),
]

IHC_SKIP_KEYWORDS = [
    "MOUSE PAD", "MOUSEPAD", "WEBCAM", "GAMEPAD", "JOYSTICK", "SPEAKER",
    "EXTERNAL HDD", "EXTERNAL SSD", "PROJECTOR", "PRINTER", "SCANNER",
    "UPS", "STABILIZER", "NETWORK", "ROUTER", "SWITCH", "ACCESS POINT", "NAS",
    "BY ORDER", "PRE ORDER", "CABLE", "HUB",
]

CID_MAP = {
    "cpu": "c01", "mainboard": "c02", "gpu": "c03", "vga": "c03",
    "ram": "c04", "ssd": "c05", "psu": "c06", "case": "c07",
    "liquid": "c08", "air cooler": "c09", "cooler": "c09",
    "mouse": "c10", "keyboard": "c11", "headset": "c12",
    "microphone": "c13", "monitor": "c14",
    "gaming chair": "c15", "chair": "c15",
    "gaming desk": "c16", "desk": "c16",
}

# ────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────
def log(msg):
    """Print safe for all Windows consoles (no unicode arrows)"""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))

def parse_price(text: str) -> int:
    if not text: return 0
    text = text.strip().replace(",","").replace("\u0e3f","").replace("THB","").replace("baht","").strip()
    m = re.search(r"\d+(?:\.\d+)?", text)
    if not m: return 0
    try: n = int(float(m.group(0)))
    except: return 0
    return n if 200 <= n <= 500_000 else 0

def get_cid(category: str) -> str:
    c = category.lower()
    for k, v in CID_MAP.items():
        if k in c: return v
    return "c01"

def make_pid(name: str, store: str) -> str:
    import hashlib
    slug = re.sub(r"[^a-z0-9]","", name.lower())[:12]
    h = hashlib.md5(f"{name}_{store}".encode()).hexdigest()[:8]
    return f"{slug}_{store[:3]}_{h}"

def ensure_columns(conn: sqlite3.Connection):
    """Add new columns if not exist"""
    cur = conn.cursor()
    new_cols = [
        ("url_advice",    "TEXT DEFAULT ''"),
        ("url_jib",       "TEXT DEFAULT ''"),
        ("url_ihavecpu",  "TEXT DEFAULT ''"),
        ("desc_advice",   "TEXT DEFAULT ''"),
        ("desc_jib",      "TEXT DEFAULT ''"),
        ("desc_ihavecpu", "TEXT DEFAULT ''"),
    ]
    cur.execute("PRAGMA table_info(products)")
    existing = {row[1] for row in cur.fetchall()}
    for col, defn in new_cols:
        if col not in existing:
            cur.execute(f"ALTER TABLE products ADD COLUMN {col} {defn}")
            log(f"[DB] Added column: {col}")
    conn.commit()

def clean_ihc_name(name: str) -> str:
    name = re.sub(r'^\[.*?\]\s*', '', name).strip()
    m = re.match(r'^([A-Z0-9/\-\. ]+?)\s*\([^\)]+\)\s*(.*)', name)
    if m: return (m.group(1).strip() + " " + m.group(2).strip()).strip()
    return name

def is_ihc_pc_component(name: str) -> bool:
    name_up = name.upper()
    for skip in IHC_SKIP_KEYWORDS:
        if skip in name_up:
            return False
    return True

def detect_jib_category(name: str):
    name_up = name.upper()
    for skip in JIB_SKIP_PREFIXES:
        if name_up.startswith(skip): return None
    for prefix, cat in JIB_PREFIX_MAP.items():
        if name_up.startswith(prefix): return cat
    return None

CLEANED_CACHE = {}

def clean_name(n: str) -> str:
    # Normalize to uppercase and replace common separators with spaces
    n = n.upper().replace('-', ' ').replace('/', ' ').replace('+', ' ')
    # Remove socket names specifically
    n = re.sub(r'\b(AM4|AM5|LGA1700|LGA1200|LGA1151|LGA1851|1700|1851|1200|1151)\b', '', n)
    # Remove speeds e.g. 3.5GHZ, 3.5 GHZ, 4.2 GHZ
    n = re.sub(r'\b\d+(?:\.\d+)?\s*GHZ\b', '', n)
    # Remove cores/threads e.g. 6C/12T, 6C 12T, 8C
    n = re.sub(r'\b\d+\s*C\s*/?\s*\d+\s*T\b|\b\d+\s*CORES?\b', '', n)
    # Remove warranty info or parentheticals
    n = re.sub(r'\(.*?\)|\[.*?\]', '', n)
    n = re.sub(r'\b(WARRANTY|3Y|5Y|YEARS?|BOX|SANS?|WITH|COOLING|FANS?)\b', '', n)
    # Remove generic shop words
    n = re.sub(r'\b(CPU|VGA|GPU|RAM|SSD|M\.2|PSU|CASE|LIQUID|COOLER|MONITOR|MOUSE|KEYBOARD|HEADSET|MAINBOARD|MOTHERBOARD)\b', '', n)
    # Split tokens, keep alphanumeric tokens that have at least one digit or are longer than 2 characters
    tokens = []
    for token in re.findall(r'\b[A-Z0-9]+\b', n):
        if len(token) > 2 or any(c.isdigit() for c in token):
            tokens.append(token)
    return ' '.join(sorted(tokens))

def get_cleaned_cache(cur: sqlite3.Cursor):
    global CLEANED_CACHE
    if not CLEANED_CACHE:
        cur.execute("SELECT product_id, p_name FROM products")
        for pid, p_name in cur.fetchall():
            cleaned = clean_name(p_name)
            if cleaned:
                CLEANED_CACHE[cleaned] = pid
    return CLEANED_CACHE

def upsert_product(cur: sqlite3.Cursor, p: dict):
    """
    Upsert product with URL and description per store.
    Match by exact name, and fallback to cleaned name match.
    """
    store = p.get("store","")
    price = p.get("price", 0)
    name  = p.get("name","").strip()
    img   = p.get("img_url","").strip()
    cat   = p.get("category","")
    cid   = get_cid(cat)
    url   = p.get("url","").strip()
    desc  = p.get("description","").strip()

    if not name or not price: return

    price_col = {"advice":"price_advice","jib":"price_jib","ihavecpu":"price_ihavecpu"}.get(store,"price_advice")
    url_col   = {"advice":"url_advice",  "jib":"url_jib",  "ihavecpu":"url_ihavecpu"}.get(store,"url_advice")
    desc_col  = {"advice":"desc_advice", "jib":"desc_jib", "ihavecpu":"desc_ihavecpu"}.get(store,"desc_advice")

    # Match exact name
    existing = cur.execute(
        "SELECT product_id FROM products WHERE p_name = ?", (name,)
    ).fetchone()

    pid = None
    if existing:
        pid = existing[0]
    else:
        # Fallback to cleaned name match
        cleaned_input = clean_name(name)
        if cleaned_input:
            cache = get_cleaned_cache(cur)
            if cleaned_input in cache:
                pid = cache[cleaned_input]

    if pid:
        # Update existing product
        cur.execute(f"""
            UPDATE products SET
                {price_col} = ?,
                {url_col}   = CASE WHEN ? != '' THEN ? ELSE {url_col} END,
                {desc_col}  = CASE WHEN ? != '' THEN ? ELSE {desc_col} END,
                p_price     = CASE WHEN p_price=0 THEN ? ELSE p_price END,
                img_url     = CASE WHEN ? != '' AND (img_url IS NULL OR img_url = '') THEN ? ELSE img_url END
            WHERE product_id = ?
        """, (
            price,
            url, url,
            desc, desc,
            price,
            img, img,
            pid
        ))
    else:
        # Create new product
        pid = make_pid(name, store)
        cur.execute("""
            INSERT OR IGNORE INTO products
            (product_id,p_name,p_description,p_price,
             price_advice,price_jib,price_ihavecpu,
             url_advice,url_jib,url_ihavecpu,
             desc_advice,desc_jib,desc_ihavecpu,
             p_stock,cid,category,img_url,specs,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            pid, name, desc, price,
            price if store=="advice"   else 0,
            price if store=="jib"      else 0,
            price if store=="ihavecpu" else 0,
            url   if store=="advice"   else "",
            url   if store=="jib"      else "",
            url   if store=="ihavecpu" else "",
            desc  if store=="advice"   else "",
            desc  if store=="jib"      else "",
            desc  if store=="ihavecpu" else "",
            99, cid, cat, img, "",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        # Add to cache for subsequent matching
        cleaned_input = clean_name(name)
        if cleaned_input:
            CLEANED_CACHE[cleaned_input] = pid

    cur.connection.commit()

# ────────────────────────────────────────────────
# Scraper: Advice
# ────────────────────────────────────────────────
async def scrape_advice(pages: int = 2) -> int:
    import random
    total = 0
    conn = sqlite3.connect(DB_PATH)
    ensure_columns(conn)
    cur = conn.cursor()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox","--disable-blink-features=AutomationControlled",
                  "--disable-web-security","--disable-features=VizDisplayCompositor"]
        )

        for cat_idx, (cat_name, base_url) in enumerate(ADVICE_CATS):
            ctx = await browser.new_context(
                user_agent=UA,
                viewport={"width": random.randint(1200,1400), "height": random.randint(768,900)},
                locale="th-TH",
            )
            await ctx.add_init_script(ANTI_BOT)
            page = await ctx.new_page()

            if cat_idx == 0:
                try:
                    await page.goto("https://www.advice.co.th/", timeout=25000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(3000)
                except: pass

            cat_count = 0
            for pn in range(1, pages+1):
                url = base_url if pn==1 else f"{base_url}?page={pn}"
                log(f"  [Advice] {cat_name} p{pn}")
                try:
                    await page.goto(url, timeout=40000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(5000)
                    for scroll_y in [300, 600, 900, 1200]:
                        await page.evaluate(f"window.scrollTo(0,{scroll_y})")
                        await page.wait_for_timeout(600)
                    await page.wait_for_timeout(2000)
                except Exception as e:
                    log(f"    err: {e}"); break

                cards = await page.query_selector_all("div.list-product")
                if not cards:
                    log("    no cards"); break

                count = 0
                for card in cards:
                    try:
                        ne = await card.query_selector("a.fn-name")
                        if not ne: continue
                        name = (await ne.inner_text()).strip()
                        if not name: continue

                        # URL
                        href = await ne.get_attribute("href") or ""
                        if href and not href.startswith("http"):
                            href = "https://www.advice.co.th" + href

                        # Price
                        price = 0
                        for ps in ["span.item-price-sale","span.price-sale",".fn-price-sale",
                                   "div.price-box span","strong.price","[class*=price-sale]"]:
                            pe = await card.query_selector(ps)
                            if pe:
                                price = parse_price(await pe.inner_text())
                                if price: break
                        if not price:
                            dp = await card.query_selector("[data-price]")
                            if dp: price = parse_price(await dp.get_attribute("data-price") or "")
                        if not price:
                            for sp in await card.query_selector_all("span,strong"):
                                t = (await sp.inner_text()).strip()
                                p = parse_price(t)
                                if p: price = p; break

                        # Image
                        img = ""
                        for img_sel in ["div.item-img img","img[src*='advice']","img"]:
                            ie = await card.query_selector(img_sel)
                            if ie:
                                img = await ie.get_attribute("src") or ""
                                if img and img.startswith("http"): break

                        # Description
                        desc = ""
                        for desc_sel in ["div.item-des","div.product-desc","p.desc",
                                         "div.item-specification","div.spec-list","p.product-name"]:
                            de = await card.query_selector(desc_sel)
                            if de:
                                desc = (await de.inner_text()).strip()
                                if desc: break

                        upsert_product(cur, {
                            "name": name, "price": price, "img_url": img,
                            "category": cat_name, "store": "advice",
                            "url": href, "description": desc
                        })
                        count += 1
                    except: pass

                cat_count += count
                log(f"    -> {count} items saved")
                if count == 0: break

            total += cat_count
            log(f"  [Advice] {cat_name}: +{cat_count}")
            await ctx.close()
            await asyncio.sleep(random.uniform(3, 6))

        await browser.close()
    conn.close()
    return total

# ────────────────────────────────────────────────
# Scraper: JIB
# ────────────────────────────────────────────────
async def scrape_jib(pages: int = 5) -> int:
    total = 0
    conn = sqlite3.connect(DB_PATH)
    ensure_columns(conn)
    cur = conn.cursor()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox","--disable-blink-features=AutomationControlled"]
        )
        ctx = await browser.new_context(user_agent=UA, viewport={"width":1280,"height":800})
        await ctx.add_init_script(ANTI_BOT)
        page = await ctx.new_page()

        for pn in range(1, pages+1):
            url = JIB_DIY_BASE if pn==1 else f"{JIB_DIY_BASE}/{pn}"
            log(f"  [JIB] DIY page {pn} → {url}")
            try:
                await page.goto(url, timeout=40000, wait_until="domcontentloaded")
                await page.wait_for_timeout(5000)
            except Exception as e:
                log(f"    err: {e}"); break

            cards = await page.query_selector_all("div.divboxpro")
            if not cards:
                log("    no cards"); break

            count = 0
            for card in cards:
                try:
                    ne = await card.query_selector("span.promo_name")
                    if not ne: continue
                    name = (await ne.inner_text()).strip()
                    if not name: continue

                    cat = detect_jib_category(name)
                    if cat is None: continue

                    pe = await card.query_selector("p.price_total")
                    price = parse_price(await pe.inner_text() if pe else "")
                    if not price: continue

                    # URL - try multiple selectors for JIB product link
                    prod_url = ""
                    for link_sel in ["a.divboxpro-click","a[href*='/web/product/product_detail']",
                                     "a[onclick*='product']","a[href*='product']","a[href]"]:
                        link_el = await card.query_selector(link_sel)
                        if link_el:
                            href = await link_el.get_attribute("href") or ""
                            if href and href not in ['#','javascript:void(0)']:
                                prod_url = ("https://www.jib.co.th" + href
                                            if not href.startswith("http") else href)
                                break
                    # If no direct link, try parent
                    if not prod_url:
                        parent = await card.evaluate_handle("el => el.closest('a')")
                        if parent:
                            try:
                                href = await parent.get_attribute("href") or ""
                                if href and href not in ['#']:
                                    prod_url = ("https://www.jib.co.th" + href
                                                if not href.startswith("http") else href)
                            except: pass

                    # Image
                    img = ""
                    ie = await card.query_selector("img")
                    if ie:
                        img = await ie.get_attribute("src") or ""
                        if img and not img.startswith("http"):
                            img = "https://www.jib.co.th" + img

                    # Description
                    desc = ""
                    for desc_sel in ["div.product-spec","div.divboxpro-spec","p.spec","div.spec-box"]:
                        de = await card.query_selector(desc_sel)
                        if de:
                            desc = (await de.inner_text()).strip()
                            if desc: break

                    upsert_product(cur, {
                        "name": name, "price": price, "img_url": img,
                        "category": cat, "store": "jib",
                        "url": prod_url, "description": desc
                    })
                    count += 1
                except: pass

            total += count
            log(f"    -> {count} PC items saved")
            if count == 0 and pn > 1: break

        await browser.close()
    conn.close()
    return total

# ────────────────────────────────────────────────
# Scraper: iHaveCPU
# ────────────────────────────────────────────────
async def scrape_ihavecpu(pages: int = 2) -> int:
    total = 0
    conn = sqlite3.connect(DB_PATH)
    ensure_columns(conn)
    cur = conn.cursor()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox","--disable-blink-features=AutomationControlled"]
        )
        ctx = await browser.new_context(user_agent=UA, viewport={"width":1280,"height":800})
        await ctx.add_init_script(ANTI_BOT)
        page = await ctx.new_page()

        try:
            await page.goto("https://www.ihavecpu.com/", timeout=20000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
        except: pass

        for cat_name, base_url in IHC_CATS:
            cat_count = 0
            seen = set()
            for pn in range(1, pages+1):
                url = base_url if pn==1 else f"{base_url}?page={pn}"
                log(f"  [iHaveCPU] {cat_name} p{pn}")
                try:
                    await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(5000)
                except Exception as e:
                    log(f"    err: {e}"); break

                links = await page.query_selector_all("a[href*='/product/']")
                if not links:
                    log("    no products"); break

                count = 0
                for le in links:
                    try:
                        h3 = await le.query_selector("h3")
                        if not h3: continue
                        raw = (await h3.inner_text()).strip()
                        if not raw or raw in seen: continue
                        seen.add(raw)
                        if not is_ihc_pc_component(raw): continue
                        name = clean_ihc_name(raw)
                        if not name: continue

                        # Price
                        price = 0
                        for sp in await le.query_selector_all("span"):
                            t = (await sp.inner_text()).strip()
                            p = parse_price(t)
                            if p: price = p; break
                        if not price: continue

                        # URL (direct product link from anchor href)
                        prod_url = ""
                        href = await le.get_attribute("href") or ""
                        if href:
                            prod_url = (href if href.startswith("http")
                                        else "https://www.ihavecpu.com" + href)

                        # Image
                        img = ""
                        ie = await le.query_selector("img")
                        if ie:
                            img = await ie.get_attribute("src") or await ie.get_attribute("data-src") or ""
                            if img and not img.startswith("http"):
                                img = "https://www.ihavecpu.com" + img

                        # Description
                        desc = ""
                        for desc_sel in ["p.product-desc","div.desc","p.description",
                                         "span.spec","div.product-short-desc"]:
                            de = await le.query_selector(desc_sel)
                            if de:
                                desc = (await de.inner_text()).strip()
                                if desc: break

                        # Auto-categorize cooler type
                        actual_cat = cat_name
                        if cat_name == 'Cooler':
                            lower = name.lower()
                            if any(k in lower for k in ['liquid','water','240','360','120',
                                                         'ryujin','kraken','valkyrie','galahad','frozen']):
                                actual_cat = 'Liquid Cooler'
                            else:
                                actual_cat = 'Air Cooler'

                        upsert_product(cur, {
                            "name": name, "price": price, "img_url": img,
                            "category": actual_cat, "store": "ihavecpu",
                            "url": prod_url, "description": desc
                        })
                        count += 1
                    except: pass

                cat_count += count
                log(f"    -> {count} items saved")
                if count == 0: break

            total += cat_count
            log(f"  [iHaveCPU] {cat_name}: +{cat_count}")

        await browser.close()
    conn.close()
    return total

# ────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────
async def run_scraper(stores: list, pages: int = 2) -> dict:
    results = {}
    if "advice"   in stores:
        log("\n=== [Advice] ===")
        results["advice"]   = await scrape_advice(pages)
    if "jib"      in stores:
        log("\n=== [JIB] ===")
        results["jib"]      = await scrape_jib(pages)
    if "ihavecpu" in stores:
        log("\n=== [iHaveCPU] ===")
        results["ihavecpu"] = await scrape_ihavecpu(pages)
    return results

if __name__ == "__main__":
    store_arg = sys.argv[1] if len(sys.argv)>1 else "all"
    pages_arg = int(sys.argv[2]) if len(sys.argv)>2 else 2
    stores = ["advice","jib","ihavecpu"] if store_arg=="all" else [store_arg]
    log(f"=== IT-RECOMMEND Scraper v4 ===")
    log(f"Stores: {stores} | Pages: {pages_arg}")
    r = asyncio.run(run_scraper(stores, pages_arg))
    log("\n=== DONE ===")
    for k,v in r.items(): log(f"  {k:10}: {v} items")
    log(f"  Total: {sum(r.values())}")
