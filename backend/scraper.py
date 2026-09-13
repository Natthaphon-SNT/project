"""
Web Scraper v6 - Advice / JIB / iHaveCPU
Scrapes: name, price, image, description, direct URL per store
- Visits individual product pages to get full description & better images
- Filters out notebooks/laptops (both name-level and category-level)
"""
import asyncio, random, re, sqlite3, sys
from datetime import datetime
from playwright.async_api import async_playwright

DB_PATH = "shop.db"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
ANTI_BOT = ("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            "window.chrome={runtime:{}};")

# Keywords to SKIP (notebook, laptop, accessories we don't want)
GLOBAL_SKIP_KEYWORDS = [
    "NOTEBOOK", "LAPTOP", "โน๊ตบุ๊ค", "โน้ตบุ๊ค", "โน้ตบุค", "โนตบุค",
    "NOTEBOOK PC", "LAPTOP PC", "GAMING LAPTOP", "GAMING NOTEBOOK",
    "MACBOOK", "CHROMEBOOK", "ULTRABOOK",
    "MOUSE PAD", "MOUSEPAD", "SPEAKER", "WEBCAM", "HUB",
    "CABLE", "UPS", "JOYSTICK", "PRINTER", "EXTERNAL",
    "NAS", "ROUTER", "NETWORK", "ACCESS POINT", "SWITCH",
    "GAMEPAD", "PROJECTOR", "SCANNER", "STABILIZER", "BY ORDER",
    "PRE ORDER",
]

# URL keywords that indicate a notebook/laptop category — skip entire category
NOTEBOOK_URL_KEYWORDS = [
    "notebook", "laptop", "macbook", "chromebook", "ultrabook",
    "โน๊ตบุ๊ค", "โน้ตบุ๊ค",
]

# ────────────────────────────────────────────────
# Advice categories
# ────────────────────────────────────────────────
# NOTE: Advice category landing pages are now marketing pages with no product
# cards. Products are fetched via their official JSON API (product/get,
# category:"search") using keyword queries, authenticated with the browser's
# user_token JWT cookie.
ADVICE_SEARCH_KEYWORDS = [
    ("CPU",           ["ryzen", "intel core"]),
    ("Mainboard",     ["mainboard"]),
    ("GPU",           ["vga rtx", "vga radeon"]),
    ("RAM",           ["ram ddr4", "ram ddr5"]),
    ("SSD",           ["ssd nvme", "ssd sata", "harddisk ssd"]),
    ("PSU",           ["psu atx", "power supply"]),
    ("Case",          ["case atx", "case matx", "case itx"]),
    ("Liquid Cooler", ["liquid cooler", "aio cooler"]),
    ("Air Cooler",    ["air cooler", "cpu cooler fan"]),
    ("Monitor",       ["monitor gaming", "monitor ips"]),
    ("Mouse",         ["mouse gaming"]),
    ("Keyboard",      ["keyboard gaming"]),
    ("Headset",       ["headset gaming"]),
    ("Gaming Chair",  ["gaming chair", "เก้าอี้เกมมิ่ง"]),
    ("Gaming Desk",   ["gaming desk", "โต๊ะคอม"]),
]

ADVICE_API = "https://prodbackadvice.advice.in.th/api/v1.0.0/product/get"

ADVICE_FETCH_JS = """
async (args) => {
    const getCookie = n => (document.cookie.split('; ').find(c => c.startsWith(n+'='))||'').split('=')[1];
    const token = decodeURIComponent(getCookie('user_token') || '');
    const r = await fetch('%s', {
        method: 'POST', credentials: 'include',
        headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
        body: JSON.stringify({category:"search",category_sub:"",product:"",keyword:args.kw,
            take:12,skip:args.skip,refSearch:"",page:"product",arr_filter_brand:[],
            arr_filter_ict:[],arr_filter_price_ict:[],arr_filter_cate:[],addView:false,
            group_end:false})
    });
    const j = await r.json();
    const pl = ((j.data||{}).data_res||{}).product_list || {};
    const out = [];
    for (const g of (pl.result_search||[])) {
        for (const p of (g.product||[])) {
            out.push({code:p.code, name:(p.name||"").trim(), price:p.price||0,
                      cat2:g.category1||"", cat3:p.cat3||""});
        }
    }
    return {status:j.status, items:out};
}
""" % ADVICE_API

# ────────────────────────────────────────────────
# JIB
# ────────────────────────────────────────────────
# JIB — list of category URLs
# NOTE: JIB remapped category IDs (2026): old GPU 2/47, RAM 2/49, PSU 2/55,
# Mouse/Keyboard 2/1419, Headset 2/1420 now redirect to homepage.
JIB_CATS = [
    ("CPU",          "https://www.jib.co.th/web/product/product_list/2/43"),
    ("Mainboard",    "https://www.jib.co.th/web/product/product_list/2/46"),
    ("GPU",          "https://www.jib.co.th/web/product/product_list/2/51"),   # การ์ดแสดงผล
    ("RAM",          "https://www.jib.co.th/web/product/product_list/2/53"),   # แรมคอมพิวเตอร์
    ("SSD",          "https://www.jib.co.th/web/product/product_list/2/52"),
    ("PSU",          "https://www.jib.co.th/web/product/product_list/3/185"),  # พาวเวอร์ซัพพลาย
    ("Case",         "https://www.jib.co.th/web/product/product_list/3/184"),  # เคสคอมพิวเตอร์
    ("Liquid Cooler","https://www.jib.co.th/web/product/product_list/2/1393"),
    ("Air Cooler",   "https://www.jib.co.th/web/product/product_list/2/1367"), # ระบบระบายอากาศ
    ("Monitor",      "https://www.jib.co.th/web/product/product_list/1/58"),
    ("Mouse",        "https://www.jib.co.th/web/product/product_list/2/346"),  # เมาส์เกมมิ่ง
    ("Keyboard",     "https://www.jib.co.th/web/product/product_list/2/345"),  # เกมมิ่งคีย์บอร์ด
    ("Headset",      "https://www.jib.co.th/web/product/product_list/2/348"),
]
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
    "NOTEBOOK", "LAPTOP",
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
    "NOTEBOOK", "LAPTOP",
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
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'))

def should_skip(name: str) -> bool:
    """Return True if the product name matches any global skip keyword."""
    name_up = name.upper()
    for kw in GLOBAL_SKIP_KEYWORDS:
        if kw in name_up:
            return True
    return False

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
        ("updated_at",    "TEXT DEFAULT ''"),
    ]
    cur.execute("PRAGMA table_info(products)")
    existing = {row[1] for row in cur.fetchall()}
    for col, defn in new_cols:
        if col not in existing:
            cur.execute(f"ALTER TABLE products ADD COLUMN {col} {defn}")
            log(f"[DB] Added column: {col}")
    # Price history table (data freshness / trend analysis)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id  TEXT NOT NULL,
            store       TEXT NOT NULL,
            price       REAL NOT NULL,
            captured_at TEXT NOT NULL
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_ph_product ON price_history(product_id, captured_at)")
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
    n = n.upper().replace('-', ' ').replace('/', ' ').replace('+', ' ')
    n = re.sub(r'\b(AM4|AM5|LGA1700|LGA1200|LGA1151|LGA1851|1700|1851|1200|1151)\b', '', n)
    n = re.sub(r'\b\d+(?:\.\d+)?\s*GHZ\b', '', n)
    n = re.sub(r'\b\d+\s*C\s*/?\\s*\d+\s*T\b|\b\d+\s*CORES?\b', '', n)
    n = re.sub(r'\(.*?\)|\[.*?\]', '', n)
    n = re.sub(r'\b(WARRANTY|3Y|5Y|YEARS?|BOX|SANS?|WITH|COOLING|FANS?)\b', '', n)
    n = re.sub(r'\b(CPU|VGA|GPU|RAM|SSD|M\.2|PSU|CASE|LIQUID|COOLER|MONITOR|MOUSE|KEYBOARD|HEADSET|MAINBOARD|MOTHERBOARD)\b', '', n)
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
    store = p.get("store","")
    price = p.get("price", 0)
    name  = p.get("name","").strip()
    img   = p.get("img_url","").strip()
    cat   = p.get("category","")
    cid   = get_cid(cat)
    url   = p.get("url","").strip()
    desc  = p.get("description","").strip()

    if not name or not price: return

    # Global notebook/laptop filter
    if should_skip(name):
        return

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
        cleaned_input = clean_name(name)
        if cleaned_input:
            cache = get_cleaned_cache(cur)
            if cleaned_input in cache:
                pid = cache[cleaned_input]

    if pid:
        cur.execute(f"""
            UPDATE products SET
                {price_col} = ?,
                {url_col}   = CASE WHEN ? != '' THEN ? ELSE {url_col} END,
                {desc_col}  = CASE WHEN ? != '' THEN ? ELSE {desc_col} END,
                img_url     = CASE WHEN ? != '' AND (img_url IS NULL OR img_url = '') THEN ? ELSE img_url END,
                updated_at  = ?
            WHERE product_id = ?
        """, (
            price,
            url, url,
            desc, desc,
            img, img,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            pid
        ))
        cur.execute("""
            UPDATE products
            SET p_price = COALESCE((
                SELECT MIN(store_price)
                FROM (
                    SELECT price_advice AS store_price
                    UNION ALL SELECT price_jib
                    UNION ALL SELECT price_ihavecpu
                )
                WHERE store_price > 0
            ), 0)
            WHERE product_id = ?
        """, (pid,))
        _record_price_history(cur, pid, store, price)
    else:
        pid = make_pid(name, store)
        cur.execute("""
            INSERT OR IGNORE INTO products
            (product_id,p_name,p_description,p_price,
             price_advice,price_jib,price_ihavecpu,
             url_advice,url_jib,url_ihavecpu,
             desc_advice,desc_jib,desc_ihavecpu,
             p_stock,cid,category,img_url,specs,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
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
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        _record_price_history(cur, pid, store, price)
        cleaned_input = clean_name(name)
        if cleaned_input:
            CLEANED_CACHE[cleaned_input] = pid

    cur.connection.commit()


def _record_price_history(cur: sqlite3.Cursor, pid: str, store: str, price: float):
    """Append a price point for trend tracking. Skips duplicate same-day points."""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    row = cur.execute(
        "SELECT id FROM price_history WHERE product_id=? AND store=? AND captured_at LIKE ? LIMIT 1",
        (pid, store, f"{today}%")).fetchone()
    if row:
        cur.execute("UPDATE price_history SET price=? WHERE id=?", (price, row[0]))
    else:
        cur.execute(
            "INSERT INTO price_history (product_id, store, price, captured_at) VALUES (?,?,?,?)",
            (pid, store, price, now.strftime("%Y-%m-%d %H:%M:%S")))

# ────────────────────────────────────────────────
# Helper: Visit product detail page to get full description + better image
# ────────────────────────────────────────────────
async def _try_get_img(el) -> str:
    """ลองดึง src / data-src / data-lazy จาก element"""
    for attr in ["src", "data-src", "data-lazy", "data-original"]:
        try:
            v = await el.get_attribute(attr) or ""
            if v and v.startswith("http") and not v.endswith(".gif"):
                return v
        except:
            pass
    return ""

async def fetch_advice_detail(page, url: str) -> tuple[str, str]:
    """Returns (description, image_url) from Advice product page."""
    desc = ""
    img = ""
    try:
        await page.goto(url, timeout=35000, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # ── Description: Advice ใช้ Vue/Nuxt — ลอง selectors ที่น่าจะมี ──
        desc_selectors = [
            ".spec-content",
            ".product-description",
            ".spec-list",
            "[class*='spec']",
            "[class*='description']",
            "[class*='detail']",
            ".tab-content",
            "#tab-description",
            "#tab-spec",
            "div.product-spec",
            "table.spec-table",
        ]
        for sel in desc_selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    t = (await el.inner_text()).strip()
                    if t and len(t) > 20:
                        desc = t
                        break
            except:
                pass

        # Fallback: ดึง og:description จาก meta tag
        if not desc:
            try:
                meta = await page.query_selector('meta[name="description"]')
                if meta:
                    content = await meta.get_attribute("content") or ""
                    if content and len(content) > 20:
                        desc = content.strip()
            except:
                pass

        # ── Image: Advice ── ลอง selectors หลายแบบ
        img_selectors = [
            "img.main-product-image",
            "img#main-product-img",
            "div.product-gallery img:first-child",
            ".swiper-slide-active img",
            ".product-img img",
            "[class*='gallery'] img",
            "[class*='product-image'] img",
            "img[src*='img.advice']",
            "picture source",
            "img[class*='product']",
        ]
        for sel in img_selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    src = await _try_get_img(el)
                    if src:
                        img = src
                        break
            except:
                pass

        # Fallback: og:image
        if not img:
            try:
                meta = await page.query_selector('meta[property="og:image"]')
                if meta:
                    content = await meta.get_attribute("content") or ""
                    if content and content.startswith("http"):
                        img = content
            except:
                pass

    except Exception as e:
        log(f"    [Advice detail err] {e}")
    return desc, img

async def fetch_jib_detail(page, url: str) -> tuple[str, str]:
    """Returns (description, image_url) from JIB product page."""
    desc = ""
    img = ""
    try:
        await page.goto(url, timeout=35000, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

        # ── Description: JIB ──
        desc_selectors = [
            "#product-description",
            "div#tab_description",
            "div.description",
            "table.table-spec",
            "div.product-detail-content",
            "div[id*='description']",
            "div[id*='spec']",
            "div[class*='description']",
            "div[class*='spec']",
            "#detail_spec",
            "#product_detail",
            ".detail_spec",
            "table.spec",
        ]
        for sel in desc_selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    t = (await el.inner_text()).strip()
                    if t and len(t) > 20:
                        desc = t
                        break
            except:
                pass

        # Fallback: ดึงข้อมูล meta description
        if not desc:
            try:
                meta = await page.query_selector('meta[name="description"]')
                if meta:
                    content = await meta.get_attribute("content") or ""
                    if content and len(content) > 20:
                        desc = content.strip()
            except:
                pass

        # ── Image: JIB ──
        img_selectors = [
            "img#main_img",
            "img#bigimage",
            "div#bigimage img",
            "div.product-bigimage img",
            "img[id*='main']",
            "div.product-image img",
            "div.img-content img",
            "img[src*='jib']",
            "img[class*='main']",
            "div.product-gallery img:first-child",
        ]
        for sel in img_selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    src = await _try_get_img(el)
                    if src:
                        img = src
                        break
            except:
                pass

        # Fallback: og:image
        if not img:
            try:
                meta = await page.query_selector('meta[property="og:image"]')
                if meta:
                    content = await meta.get_attribute("content") or ""
                    if content and content.startswith("http"):
                        img = content
            except:
                pass

    except Exception as e:
        log(f"    [JIB detail err] {e}")
    return desc, img

async def fetch_ihc_detail(page, url: str) -> tuple[str, str]:
    """Returns (description, image_url) from iHaveCPU product page."""
    desc = ""
    img = ""
    try:
        await page.goto(url, timeout=35000, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

        # ── Description: iHaveCPU ──
        desc_selectors = [
            "div.product-description",
            "div.description",
            "#product-description",
            "[class*='product-desc']",
            "[class*='product-spec']",
            "[class*='spec-content']",
            "div.tabs-content",
            "div.tab-content",
            "#tab-description",
            "#tab-spec",
            "table.spec-table",
            "div.product-detail",
            "div[class*='detail']",
        ]
        for sel in desc_selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    t = (await el.inner_text()).strip()
                    if t and len(t) > 20:
                        desc = t
                        break
            except:
                pass

        # Fallback: meta description
        if not desc:
            try:
                meta = await page.query_selector('meta[name="description"]')
                if meta:
                    content = await meta.get_attribute("content") or ""
                    if content and len(content) > 20:
                        desc = content.strip()
            except:
                pass

        # ── Image: iHaveCPU ──
        img_selectors = [
            "img.product-main-img",
            "img#main-image",
            "img#mainImage",
            "div.product-gallery img:first-child",
            "div.product-images img:first-child",
            "div.swiper-slide:first-child img",
            "div.swiper-wrapper img:first-child",
            "[class*='product-image'] img",
            "[class*='gallery'] img",
            "img[src*='ihavecpu']",
        ]
        for sel in img_selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    src = await _try_get_img(el)
                    if src:
                        img = src
                        break
            except:
                pass

        # Fallback: og:image
        if not img:
            try:
                meta = await page.query_selector('meta[property="og:image"]')
                if meta:
                    content = await meta.get_attribute("content") or ""
                    if content and content.startswith("http"):
                        img = content
            except:
                pass

    except Exception as e:
        log(f"    [iHaveCPU detail err] {e}")
    return desc, img

# ────────────────────────────────────────────────
# Scraper: Advice
# ────────────────────────────────────────────────
async def scrape_advice(pages: int = 2) -> int:
    """Advice scraper v7 - uses Advice official JSON product API (search mode).
    Category landing pages no longer render product cards in HTML."""
    import urllib.parse
    total = 0
    conn = sqlite3.connect(DB_PATH)
    ensure_columns(conn)
    cur = conn.cursor()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        ctx = await browser.new_context(user_agent=UA, locale="th-TH")
        page = await ctx.new_page()

        # Authenticate once: landing page sets user_token JWT cookie
        try:
            await page.goto("https://www.advice.co.th/", timeout=30000,
                            wait_until="domcontentloaded")
            await page.wait_for_timeout(4000)
        except Exception as e:
            log(f"  [Advice] homepage err: {e}")

        has_token = await page.evaluate(
            "() => (document.cookie.split('; ').find(c => c.startsWith('user_token=')) || '').length > 20")
        if not has_token:
            log("  [Advice] WARNING: user_token cookie missing - API may 401")

        seen_codes = set()
        for cat_name, keywords in ADVICE_SEARCH_KEYWORDS:
            cat_count = 0
            for kw in keywords:
                for pn in range(max(1, pages)):
                    skip = pn * 12
                    try:
                        res = await page.evaluate(ADVICE_FETCH_JS, {"kw": kw, "skip": skip})
                    except Exception as e:
                        log(f"    [Advice] api err ({kw} p{pn}): {str(e)[:100]}")
                        break
                    items = res.get("items") or []
                    if not items:
                        break
                    new_count = 0
                    for it in items:
                        code = it.get("code") or ""
                        name = (it.get("name") or "").strip()
                        price = int(it.get("price") or 0)
                        if not name or not price or should_skip(name):
                            continue
                        if code and code in seen_codes:
                            continue
                        if code:
                            seen_codes.add(code)
                        url = ("https://www.advice.co.th/search?keyword="
                               + urllib.parse.quote(name[:60]))
                        upsert_product(cur, {
                            "name": name, "price": price, "img_url": "",
                            "category": cat_name, "store": "advice",
                            "url": url, "description": "",
                        })
                        new_count += 1
                    cat_count += new_count
                    if new_count == 0:
                        break
            total += cat_count
            log(f"  [Advice] {cat_name}: +{cat_count}")

        await browser.close()
    conn.close()
    return total

async def scrape_jib(pages: int = 5, fetch_details: bool = False) -> int:
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
        detail_page = await ctx.new_page()

        # ── Scrape each JIB category ──
        for cat_name, base_url in JIB_CATS:
            # Skip notebook/laptop categories at URL level
            if any(kw in base_url.lower() for kw in NOTEBOOK_URL_KEYWORDS):
                log(f"  [JIB] SKIP notebook category: {cat_name}")
                continue

            cat_count = 0
            for pn in range(1, pages+1):
                url = base_url if pn == 1 else f"{base_url}/{pn}"
                log(f"  [JIB] {cat_name} p{pn} -> {url}")
                try:
                    await page.goto(url, timeout=40000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(5000)
                except Exception as e:
                    log(f"    err: {e}"); break

                # JIB product cards: try multiple selectors
                cards = await page.query_selector_all("div.divboxpro")
                if not cards:
                    cards = await page.query_selector_all("div[class*='divboxpro']")
                if not cards:
                    log("    no cards"); break

                count = 0
                for card in cards:
                    try:
                        # Product name: try span.promo_name first, then any text
                        ne = await card.query_selector("span.promo_name")
                        if not ne:
                            ne = await card.query_selector("[class*='name']")
                        if not ne: continue
                        name = (await ne.inner_text()).strip()
                        if not name or should_skip(name): continue

                        # Auto-detect category from name if needed
                        detected_cat = detect_jib_category(name)
                        actual_cat = detected_cat if detected_cat else cat_name
                        # Skip if still can't determine category
                        if detected_cat is None and cat_name not in [
                            "CPU","Mainboard","GPU","RAM","SSD","HDD",
                            "PSU","Case","Liquid Cooler","Air Cooler",
                            "Monitor","Mouse","Keyboard","Headset"
                        ]:
                            continue

                        # Price
                        pe = await card.query_selector("p.price_total")
                        if not pe:
                            pe = await card.query_selector("[class*='price']")
                        price = parse_price(await pe.inner_text() if pe else "")
                        if not price: continue

                        # URL — JIB product links use readProduct pattern
                        prod_url = ""
                        for link_sel in [
                            "a[href*='readProduct']",
                            "a[href*='product_detail']",
                            "a[href*='/web/product/']",
                            "a[href*='product']",
                            "a[href]",
                        ]:
                            link_el = await card.query_selector(link_sel)
                            if link_el:
                                href = await link_el.get_attribute("href") or ""
                                if href and href not in ['#', 'javascript:void(0)', 'javascript:;']:
                                    prod_url = (
                                        "https://www.jib.co.th" + href
                                        if not href.startswith("http") else href
                                    )
                                    break

                        # Image
                        img = ""
                        ie = await card.query_selector("img")
                        if ie:
                            img = (await ie.get_attribute("src") or
                                   await ie.get_attribute("data-src") or
                                   await ie.get_attribute("data-lazy") or "")
                            if img and not img.startswith("http"):
                                img = "https://www.jib.co.th" + img

                        # Visit product detail page (optional - slow)
                        desc = ""
                        if fetch_details and prod_url:
                            detail_desc, detail_img = await fetch_jib_detail(detail_page, prod_url)
                            desc = detail_desc
                            if detail_img and not img:
                                img = detail_img

                        upsert_product(cur, {
                            "name": name, "price": price, "img_url": img,
                            "category": actual_cat, "store": "jib",
                            "url": prod_url, "description": desc
                        })
                        count += 1
                    except Exception as e:
                        log(f"    card err: {e}")

                cat_count += count
                conn.commit()
                log(f"    -> {count} items saved")
                if count == 0 and pn > 1:
                    break

            total += cat_count
            log(f"  [JIB] {cat_name}: {cat_count} total")
            await asyncio.sleep(random.uniform(2, 4))

        await browser.close()
    conn.close()
    return total

# ────────────────────────────────────────────────
# Scraper: iHaveCPU
# ────────────────────────────────────────────────
async def scrape_ihavecpu(pages: int = 2, fetch_details: bool = False) -> int:
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
        detail_page = await ctx.new_page()

        try:
            await page.goto("https://www.ihavecpu.com/", timeout=20000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
        except: pass

        for cat_name, base_url in IHC_CATS:
            # ── กรอง URL ระดับ category ที่มีคำว่า notebook/laptop ──
            if any(kw in base_url.lower() for kw in NOTEBOOK_URL_KEYWORDS):
                log(f"  [iHaveCPU] SKIP notebook category: {cat_name}")
                continue

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
                        if should_skip(raw) or not is_ihc_pc_component(raw): continue
                        name = clean_ihc_name(raw)
                        if not name: continue

                        # Price
                        price = 0
                        for sp in await le.query_selector_all("span"):
                            t = (await sp.inner_text()).strip()
                            p = parse_price(t)
                            if p: price = p; break
                        if not price: continue

                        # URL
                        prod_url = ""
                        href = await le.get_attribute("href") or ""
                        if href:
                            prod_url = (href if href.startswith("http")
                                        else "https://www.ihavecpu.com" + href)

                        # Image — try src then data-src
                        img = ""
                        ie = await le.query_selector("img")
                        if ie:
                            img = (await ie.get_attribute("src") or
                                   await ie.get_attribute("data-src") or
                                   await ie.get_attribute("data-lazy") or "")
                            if img and not img.startswith("http"):
                                img = "https://www.ihavecpu.com" + img

                        # Visit product detail page for description + better image
                        desc = ""
                        if fetch_details and prod_url:
                            detail_desc, detail_img = await fetch_ihc_detail(detail_page, prod_url)
                            desc = detail_desc
                            if detail_img and not img:
                                img = detail_img

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
async def run_scraper(stores: list, pages: int = 2, fetch_details: bool = False) -> dict:
    results = {}
    if "advice"   in stores:
        log("\n=== [Advice] ===")
        results["advice"]   = await scrape_advice(pages)
    if "jib"      in stores:
        log("\n=== [JIB] ===")
        results["jib"]      = await scrape_jib(pages, fetch_details)
    if "ihavecpu" in stores:
        log("\n=== [iHaveCPU] ===")
        results["ihavecpu"] = await scrape_ihavecpu(pages, fetch_details)
    return results

if __name__ == "__main__":
    store_arg = sys.argv[1] if len(sys.argv)>1 else "all"
    pages_arg = int(sys.argv[2]) if len(sys.argv)>2 else 2
    stores = ["advice","jib","ihavecpu"] if store_arg=="all" else [store_arg]
    log(f"=== IT-RECOMMEND Scraper v5 ===")
    log(f"Stores: {stores} | Pages: {pages_arg}")
    fetch_details = "details" in sys.argv
    r = asyncio.run(run_scraper(stores, pages_arg, fetch_details))
    log("\n=== DONE ===")
    for k,v in r.items(): log(f"  {k:10}: {v} items")
    log(f"  Total: {sum(r.values())}")
