"""
Full Scraper v1 - Advice / JIB / iHaveCPU
==========================================
Features:
  - ดึงสินค้าจาก 3 ร้าน: Advice (API), JIB (HTML), iHaveCPU (HTML)
  - SmartMatcher: ถ้าชื่อสินค้าเดียวกัน → ใช้ record เดียว เพิ่ม URL/ราคาร้านใหม่
  - Matching 2 ระดับ: exact (case-insensitive) → token-based fuzzy
  - บันทึก url_advice / url_jib / url_ihavecpu แยกต่อร้านค้า
  - ลูกค้าเปรียบเทียบราคาได้ผ่าน API /products/{id}/compare

การใช้งาน:
  python full_scraper.py                    # รัน 3 ร้าน, 3 หน้าต่อ category
  python full_scraper.py --stores jib ihavecpu --pages 5
  python full_scraper.py --stores all --pages 3
"""

import asyncio
import argparse
import hashlib
import re
import sqlite3
import sys
import io
import random
from datetime import datetime
from playwright.async_api import async_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
DB_PATH = "shop.db"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
ANTI_BOT = (
    "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
    "window.chrome={runtime:{}};"
)

# ─────────────────────────────────────────────────────────────────────────────
# Skip filters
# ─────────────────────────────────────────────────────────────────────────────
SKIP_KEYWORDS = [
    "NOTEBOOK", "LAPTOP", "โน๊ตบุ๊ค", "โน้ตบุ๊ค", "โน้ตบุค", "โนตบุค",
    "MACBOOK", "CHROMEBOOK", "ULTRABOOK", "GAMING LAPTOP", "GAMING NOTEBOOK",
    "MOUSE PAD", "MOUSEPAD", "SPEAKER", "WEBCAM", "HUB", "CABLE",
    "UPS", "JOYSTICK", "PRINTER", "EXTERNAL", "NAS", "ROUTER",
    "NETWORK", "ACCESS POINT", "SWITCH", "GAMEPAD", "PROJECTOR",
    "SCANNER", "STABILIZER", "BY ORDER", "PRE ORDER",
]
NOTEBOOK_URL_KW = ["notebook", "laptop", "macbook", "chromebook"]

# ─────────────────────────────────────────────────────────────────────────────
# Store categories
# ─────────────────────────────────────────────────────────────────────────────
ADVICE_API = "https://prodbackadvice.advice.in.th/api/v1.0.0/product/get"
ADVICE_SEARCH_KW = [
    ("CPU",           ["ryzen", "intel core"]),
    ("Mainboard",     ["mainboard"]),
    ("GPU",           ["vga rtx", "vga radeon"]),
    ("RAM",           ["ram ddr4", "ram ddr5"]),
    ("SSD",           ["ssd nvme", "ssd sata"]),
    ("PSU",           ["psu atx", "power supply"]),
    ("Case",          ["case atx", "case matx", "case itx"]),
    ("Liquid Cooler", ["liquid cooler", "aio cooler"]),
    ("Air Cooler",    ["air cooler", "cpu cooler fan"]),
    ("Monitor",       ["monitor gaming", "monitor ips"]),
    ("Mouse",         ["mouse gaming"]),
    ("Keyboard",      ["keyboard gaming"]),
    ("Headset",       ["headset gaming"]),
    ("Gaming Chair",  ["gaming chair"]),
    ("Gaming Desk",   ["gaming desk"]),
]
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
            const slug = encodeURIComponent((p.name||'').trim().replace(/\\s+/g,' ').substring(0,80));
            out.push({
                code: p.code,
                name: (p.name||'').trim(),
                price: p.price||0,
                url: p.slug ? 'https://www.advice.co.th/product/' + p.slug : '',
                img: p.image||''
            });
        }
    }
    return {status:j.status, items:out};
}
""" % ADVICE_API

JIB_CATS = [
    ("CPU",           "https://www.jib.co.th/web/product/product_list/2/43"),
    ("Mainboard",     "https://www.jib.co.th/web/product/product_list/2/46"),
    ("GPU",           "https://www.jib.co.th/web/product/product_list/2/51"),
    ("RAM",           "https://www.jib.co.th/web/product/product_list/2/53"),
    ("SSD",           "https://www.jib.co.th/web/product/product_list/2/52"),
    ("PSU",           "https://www.jib.co.th/web/product/product_list/3/185"),
    ("Case",          "https://www.jib.co.th/web/product/product_list/3/184"),
    ("Liquid Cooler", "https://www.jib.co.th/web/product/product_list/2/1393"),
    ("Air Cooler",    "https://www.jib.co.th/web/product/product_list/2/1367"),
    ("Monitor",       "https://www.jib.co.th/web/product/product_list/1/58"),
    ("Mouse",         "https://www.jib.co.th/web/product/product_list/2/346"),
    ("Keyboard",      "https://www.jib.co.th/web/product/product_list/2/345"),
    ("Headset",       "https://www.jib.co.th/web/product/product_list/2/348"),
]
JIB_PREFIX_MAP = {
    "CPU": "CPU", "MAINBOARD": "Mainboard", "VGA": "GPU", "GRAPHIC CARD": "GPU",
    "RAM": "RAM", "SSD": "SSD", "HARDDISK": "SSD", "M.2": "SSD",
    "POWER SUPPLY": "PSU", "CASE": "Case",
    "LIQUID COOLER": "Liquid Cooler", "CPU COOLER": "Air Cooler", "COOLER": "Air Cooler",
    "LCD PANEL": "Monitor", "MONITOR": "Monitor",
    "KEYBOARD": "Keyboard", "MOUSE": "Mouse", "HEADSET": "Headset",
}
JIB_SKIP_PREFIXES = {
    "MOUSE PAD", "SPEAKER", "WEBCAM", "HUB", "CABLE", "UPS",
    "JOYSTICK", "PRINTER", "EXTERNAL", "NAS", "ROUTER",
    "NETWORK", "ACCESS POINT", "SWITCH", "NOTEBOOK", "LAPTOP",
}

IHC_CATS = [
    ("CPU",          "https://www.ihavecpu.com/category/cpu"),
    ("Mainboard",    "https://www.ihavecpu.com/category/mainboard"),
    ("GPU",          "https://www.ihavecpu.com/category/graphic-card"),
    ("RAM",          "https://www.ihavecpu.com/category/ram"),
    ("SSD",          "https://www.ihavecpu.com/category/storage"),
    ("PSU",          "https://www.ihavecpu.com/category/power-supply"),
    ("Case",         "https://www.ihavecpu.com/category/case"),
    ("Cooler",       "https://www.ihavecpu.com/category/heat-sink"),
    ("Monitor",      "https://www.ihavecpu.com/category/monitor"),
    ("Mouse",        "https://www.ihavecpu.com/category/mouse"),
    ("Keyboard",     "https://www.ihavecpu.com/category/keyboard"),
    ("Headset",      "https://www.ihavecpu.com/category/headphone"),
    ("Gaming Chair", "https://www.ihavecpu.com/category/chair"),
    ("Gaming Desk",  "https://www.ihavecpu.com/category/desk"),
]
IHC_SKIP = [
    "MOUSE PAD", "MOUSEPAD", "WEBCAM", "GAMEPAD", "JOYSTICK", "SPEAKER",
    "EXTERNAL HDD", "EXTERNAL SSD", "PROJECTOR", "PRINTER", "SCANNER",
    "UPS", "STABILIZER", "NETWORK", "ROUTER", "SWITCH", "ACCESS POINT",
    "NAS", "BY ORDER", "PRE ORDER", "CABLE", "HUB", "NOTEBOOK", "LAPTOP",
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


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def log(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))


def should_skip(name: str) -> bool:
    up = name.upper()
    return any(kw in up for kw in SKIP_KEYWORDS)


def parse_price(text: str) -> int:
    if not text:
        return 0
    text = text.strip().replace(",", "").replace("฿", "").replace("THB", "").replace("baht", "").strip()
    m = re.search(r"\d+(?:\.\d+)?", text)
    if not m:
        return 0
    try:
        n = int(float(m.group(0)))
    except Exception:
        return 0
    return n if 200 <= n <= 500_000 else 0


def get_cid(category: str) -> str:
    c = category.lower()
    for k, v in CID_MAP.items():
        if k in c:
            return v
    return "c01"


def make_pid(name: str, store: str) -> str:
    slug = re.sub(r"[^a-z0-9]", "", name.lower())[:12]
    h = hashlib.md5(f"{name}_{store}".encode()).hexdigest()[:8]
    return f"{slug}_{store[:3]}_{h}"


def clean_name_tokens(name: str) -> frozenset:
    """Normalize and tokenize a product name for fuzzy matching."""
    n = name.upper().replace("-", " ").replace("/", " ").replace("+", " ").replace("_", " ")
    # Remove socket/platform suffixes
    n = re.sub(r"\b(AM4|AM5|LGA\d+|\d{4})\b", "", n)
    # Remove frequency
    n = re.sub(r"\b\d+(?:\.\d+)?\s*GHZ\b", "", n)
    # Remove cores/threads
    n = re.sub(r"\b\d+\s*C\s*/?\s*\d+\s*T\b|\b\d+\s*CORES?\b", "", n)
    # Remove parentheses/brackets content
    n = re.sub(r"\(.*?\)|\[.*?\]", "", n)
    # Remove generic words
    n = re.sub(
        r"\b(WARRANTY|3Y|5Y|YEARS?|BOX|SANS?|WITH|COOLING|FANS?|"
        r"CPU|VGA|GPU|RAM|SSD|M\.2|PSU|CASE|LIQUID|COOLER|MONITOR|"
        r"MOUSE|KEYBOARD|HEADSET|MAINBOARD|MOTHERBOARD|DDR4|DDR5)\b",
        "", n,
    )
    tokens = frozenset(
        t for t in re.findall(r"\b[A-Z0-9]+\b", n)
        if len(t) > 1 or any(c.isdigit() for c in t)
    )
    return tokens


def token_similarity(a: frozenset, b: frozenset) -> float:
    """Jaccard similarity between two token sets."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def clean_ihc_name(name: str) -> str:
    name = re.sub(r"^\[.*?\]\s*", "", name).strip()
    m = re.match(r"^([A-Z0-9/\-\. ]+?)\s*\([^\)]+\)\s*(.*)", name)
    if m:
        return (m.group(1).strip() + " " + m.group(2).strip()).strip()
    return name


def detect_jib_cat(name: str):
    up = name.upper()
    for skip in JIB_SKIP_PREFIXES:
        if up.startswith(skip):
            return None
    for prefix, cat in JIB_PREFIX_MAP.items():
        if up.startswith(prefix):
            return cat
    return None


# ─────────────────────────────────────────────────────────────────────────────
# DB Setup
# ─────────────────────────────────────────────────────────────────────────────
def setup_db(conn: sqlite3.Connection):
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

    cur.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id  TEXT NOT NULL,
            store       TEXT NOT NULL,
            price       REAL NOT NULL,
            captured_at TEXT NOT NULL
        )
    """)
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_ph_prod ON price_history(product_id, captured_at)"
    )
    conn.commit()


# ─────────────────────────────────────────────────────────────────────────────
# SmartMatcher — deduplication engine
# ─────────────────────────────────────────────────────────────────────────────
class SmartMatcher:
    """
    Finds existing products in DB that match an incoming product name.
    Matching order:
      1. Exact match (case-insensitive, trimmed)
      2. Token-based Jaccard similarity >= TOKEN_THRESHOLD
    """

    TOKEN_THRESHOLD = 0.75

    def __init__(self, cur: sqlite3.Cursor):
        self.cur = cur
        # Cache: {normalized_name_upper: product_id}
        self._exact_cache: dict[str, str] = {}
        # Cache: {product_id: frozenset_of_tokens}
        self._token_cache: dict[str, frozenset] = {}
        self._loaded = False

    def _load(self):
        if self._loaded:
            return
        self.cur.execute("SELECT product_id, p_name FROM products")
        for pid, name in self.cur.fetchall():
            self._exact_cache[name.strip().upper()] = pid
            tokens = clean_name_tokens(name)
            if tokens:
                self._token_cache[pid] = tokens
        self._loaded = True

    def find(self, name: str) -> str | None:
        """Return product_id of best match, or None if no match."""
        self._load()

        # 1. Exact match
        key = name.strip().upper()
        if key in self._exact_cache:
            return self._exact_cache[key]

        # 2. Token similarity
        tokens = clean_name_tokens(name)
        if not tokens:
            return None

        best_pid = None
        best_score = self.TOKEN_THRESHOLD
        for pid, t in self._token_cache.items():
            score = token_similarity(tokens, t)
            if score > best_score:
                best_score = score
                best_pid = pid

        return best_pid

    def register(self, pid: str, name: str):
        """Add a newly inserted product to the cache."""
        self._exact_cache[name.strip().upper()] = pid
        tokens = clean_name_tokens(name)
        if tokens:
            self._token_cache[pid] = tokens


# ─────────────────────────────────────────────────────────────────────────────
# Upsert with deduplication
# ─────────────────────────────────────────────────────────────────────────────
def _record_price_history(cur: sqlite3.Cursor, pid: str, store: str, price: int):
    if not price:
        return
    today = datetime.now().strftime("%Y-%m-%d")
    row = cur.execute(
        "SELECT id FROM price_history WHERE product_id=? AND store=? AND captured_at LIKE ?",
        (pid, store, f"{today}%"),
    ).fetchone()
    if row:
        cur.execute("UPDATE price_history SET price=? WHERE id=?", (price, row[0]))
    else:
        cur.execute(
            "INSERT INTO price_history (product_id, store, price, captured_at) VALUES (?,?,?,?)",
            (pid, store, price, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )


def upsert_product(cur: sqlite3.Cursor, matcher: SmartMatcher, p: dict) -> bool:
    """
    Insert or update a product record with smart deduplication.
    If a product with a matching name already exists, only its store-specific
    price/url/desc columns are updated — no duplicate row is created.
    Returns True if a new row was inserted, False if an existing row was updated.
    """
    name  = (p.get("name") or "").strip()
    price = int(p.get("price") or 0)
    store = p.get("store") or ""
    cat   = p.get("category") or ""
    img   = (p.get("img_url") or "").strip()
    url   = (p.get("url") or "").strip()
    desc  = (p.get("description") or "").strip()

    if not name or not price:
        return False
    if should_skip(name):
        return False

    cid       = get_cid(cat)
    now_str   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    price_col = {"advice": "price_advice", "jib": "price_jib", "ihavecpu": "price_ihavecpu"}.get(store, "price_advice")
    url_col   = {"advice": "url_advice",   "jib": "url_jib",   "ihavecpu": "url_ihavecpu"}.get(store, "url_advice")
    desc_col  = {"advice": "desc_advice",  "jib": "desc_jib",  "ihavecpu": "desc_ihavecpu"}.get(store, "desc_advice")

    pid = matcher.find(name)

    if pid:
        # ── UPDATE existing record with this store's data ──
        cur.execute(f"""
            UPDATE products SET
                {price_col} = ?,
                {url_col}   = CASE WHEN ? != '' THEN ? ELSE {url_col} END,
                {desc_col}  = CASE WHEN ? != '' THEN ? ELSE {desc_col} END,
                p_price     = CASE WHEN p_price = 0 THEN ? ELSE p_price END,
                img_url     = CASE WHEN ? != '' AND (img_url IS NULL OR img_url = '') THEN ? ELSE img_url END,
                updated_at  = ?
            WHERE product_id = ?
        """, (
            price,
            url, url,
            desc, desc,
            price,
            img, img,
            now_str,
            pid,
        ))
        _record_price_history(cur, pid, store, price)
        return False
    else:
        # ── INSERT new record ──
        pid = make_pid(name, store)
        cur.execute("""
            INSERT OR IGNORE INTO products
            (product_id, p_name, p_description, p_price,
             price_advice, price_jib, price_ihavecpu,
             url_advice, url_jib, url_ihavecpu,
             desc_advice, desc_jib, desc_ihavecpu,
             p_stock, cid, category, img_url, specs, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            pid, name, desc, price,
            price if store == "advice"   else 0,
            price if store == "jib"      else 0,
            price if store == "ihavecpu" else 0,
            url   if store == "advice"   else "",
            url   if store == "jib"      else "",
            url   if store == "ihavecpu" else "",
            desc  if store == "advice"   else "",
            desc  if store == "jib"      else "",
            desc  if store == "ihavecpu" else "",
            99, cid, cat, img, "",
            now_str, now_str,
        ))
        _record_price_history(cur, pid, store, price)
        matcher.register(pid, name)
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Scraper: Advice (JSON API)
# ─────────────────────────────────────────────────────────────────────────────
async def scrape_advice(conn: sqlite3.Connection, matcher: SmartMatcher, pages: int = 3):
    import urllib.parse
    cur = conn.cursor()
    total_new = total_upd = 0

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        ctx = await browser.new_context(user_agent=UA, locale="th-TH")
        page = await ctx.new_page()

        # Authenticate — landing page sets user_token JWT cookie
        try:
            await page.goto("https://www.advice.co.th/", timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(4000)
        except Exception as e:
            log(f"  [Advice] homepage err: {e}")

        has_token = await page.evaluate(
            "() => (document.cookie.split('; ').find(c => c.startsWith('user_token=')) || '').length > 20"
        )
        if not has_token:
            log("  [Advice] WARNING: user_token cookie missing — API may 401")

        seen_codes: set[str] = set()

        for cat_name, keywords in ADVICE_SEARCH_KW:
            cat_new = cat_upd = 0
            for kw in keywords:
                for pn in range(pages):
                    skip = pn * 12
                    try:
                        res = await page.evaluate(ADVICE_FETCH_JS, {"kw": kw, "skip": skip})
                    except Exception as e:
                        log(f"    [Advice] api err ({kw} p{pn}): {str(e)[:120]}")
                        break

                    items = res.get("items") or []
                    if not items:
                        break

                    page_new = 0
                    for it in items:
                        code  = it.get("code") or ""
                        name  = (it.get("name") or "").strip()
                        price = int(it.get("price") or 0)
                        url   = it.get("url") or ""
                        img   = it.get("img") or ""

                        if not name or not price:
                            continue
                        if code and code in seen_codes:
                            continue
                        if code:
                            seen_codes.add(code)

                        # Fallback URL: search page
                        if not url:
                            url = "https://www.advice.co.th/search?keyword=" + urllib.parse.quote(name[:60])

                        is_new = upsert_product(cur, matcher, {
                            "name": name, "price": price,
                            "img_url": img, "url": url,
                            "category": cat_name, "store": "advice",
                            "description": "",
                        })
                        if is_new:
                            cat_new += 1
                        else:
                            cat_upd += 1
                        page_new += 1

                    conn.commit()
                    if page_new == 0:
                        break

            total_new += cat_new
            total_upd += cat_upd
            log(f"  [Advice] {cat_name}: +{cat_new} new, ~{cat_upd} updated")

        await browser.close()

    log(f"  [Advice] TOTAL: {total_new} new | {total_upd} merged into existing")
    return total_new, total_upd


# ─────────────────────────────────────────────────────────────────────────────
# Scraper: JIB (HTML category pages)
# ─────────────────────────────────────────────────────────────────────────────
async def scrape_jib(conn: sqlite3.Connection, matcher: SmartMatcher, pages: int = 5):
    cur = conn.cursor()
    total_new = total_upd = 0

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        ctx = await browser.new_context(user_agent=UA, viewport={"width": 1280, "height": 800})
        await ctx.add_init_script(ANTI_BOT)
        page = await ctx.new_page()

        for cat_name, base_url in JIB_CATS:
            if any(kw in base_url.lower() for kw in NOTEBOOK_URL_KW):
                log(f"  [JIB] SKIP notebook cat: {cat_name}")
                continue

            cat_new = cat_upd = 0
            for pn in range(1, pages + 1):
                url = base_url if pn == 1 else f"{base_url}/{pn}"
                log(f"  [JIB] {cat_name} p{pn}")

                try:
                    await page.goto(url, timeout=40000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(4000)
                except Exception as e:
                    log(f"    err: {e}")
                    break

                cards = await page.query_selector_all("div.divboxpro")
                if not cards:
                    cards = await page.query_selector_all("div[class*='divboxpro']")
                if not cards:
                    log("    no cards")
                    break

                count = 0
                for card in cards:
                    try:
                        # Name
                        ne = await card.query_selector("span.promo_name")
                        if not ne:
                            ne = await card.query_selector("[class*='name']")
                        if not ne:
                            continue
                        name = (await ne.inner_text()).strip()
                        if not name or should_skip(name):
                            continue

                        actual_cat = detect_jib_cat(name) or cat_name

                        # Price
                        pe = await card.query_selector("p.price_total")
                        if not pe:
                            pe = await card.query_selector("[class*='price']")
                        price = parse_price(await pe.inner_text() if pe else "")
                        if not price:
                            continue

                        # URL — prefer readProduct links
                        prod_url = ""
                        for link_sel in [
                            "a[href*='readProduct']",
                            "a[href*='product_detail']",
                            "a[href*='/web/product/']",
                            "a[href*='product']",
                            "a[href]",
                        ]:
                            le = await card.query_selector(link_sel)
                            if le:
                                href = await le.get_attribute("href") or ""
                                if href and href not in ["#", "javascript:void(0)", "javascript:;"]:
                                    prod_url = (
                                        "https://www.jib.co.th" + href
                                        if not href.startswith("http") else href
                                    )
                                    break

                        # Image
                        img = ""
                        ie = await card.query_selector("img")
                        if ie:
                            img = (
                                await ie.get_attribute("src") or
                                await ie.get_attribute("data-src") or
                                await ie.get_attribute("data-lazy") or ""
                            )
                            if img and not img.startswith("http"):
                                img = "https://www.jib.co.th" + img

                        is_new = upsert_product(cur, matcher, {
                            "name": name, "price": price,
                            "img_url": img, "url": prod_url,
                            "category": actual_cat, "store": "jib",
                            "description": "",
                        })
                        if is_new:
                            cat_new += 1
                        else:
                            cat_upd += 1
                        count += 1

                    except Exception as e:
                        log(f"    card err: {e}")

                conn.commit()
                log(f"    -> {count} products processed")
                if count == 0 and pn > 1:
                    break

            total_new += cat_new
            total_upd += cat_upd
            log(f"  [JIB] {cat_name}: +{cat_new} new, ~{cat_upd} merged")
            await asyncio.sleep(random.uniform(2, 4))

        await browser.close()

    log(f"  [JIB] TOTAL: {total_new} new | {total_upd} merged into existing")
    return total_new, total_upd


# ─────────────────────────────────────────────────────────────────────────────
# Scraper: iHaveCPU (HTML category pages)
# ─────────────────────────────────────────────────────────────────────────────
async def scrape_ihavecpu(conn: sqlite3.Connection, matcher: SmartMatcher, pages: int = 3):
    cur = conn.cursor()
    total_new = total_upd = 0

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        ctx = await browser.new_context(user_agent=UA, viewport={"width": 1280, "height": 800})
        await ctx.add_init_script(ANTI_BOT)
        page = await ctx.new_page()

        try:
            await page.goto("https://www.ihavecpu.com/", timeout=20000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
        except Exception:
            pass

        for cat_name, base_url in IHC_CATS:
            if any(kw in base_url.lower() for kw in NOTEBOOK_URL_KW):
                log(f"  [iHaveCPU] SKIP notebook cat: {cat_name}")
                continue

            cat_new = cat_upd = 0
            seen: set[str] = set()

            for pn in range(1, pages + 1):
                url = base_url if pn == 1 else f"{base_url}?page={pn}"
                log(f"  [iHaveCPU] {cat_name} p{pn}")

                try:
                    await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(5000)
                except Exception as e:
                    log(f"    err: {e}")
                    break

                links = await page.query_selector_all("a[href*='/product/']")
                if not links:
                    log("    no products")
                    break

                count = 0
                for le in links:
                    try:
                        h3 = await le.query_selector("h3")
                        if not h3:
                            continue
                        raw = (await h3.inner_text()).strip()
                        if not raw or raw in seen:
                            continue
                        seen.add(raw)
                        if should_skip(raw):
                            continue
                        up = raw.upper()
                        if any(s in up for s in IHC_SKIP):
                            continue

                        name = clean_ihc_name(raw)
                        if not name:
                            continue

                        # Price
                        price = 0
                        for sp in await le.query_selector_all("span"):
                            t = (await sp.inner_text()).strip()
                            p = parse_price(t)
                            if p:
                                price = p
                                break
                        if not price:
                            continue

                        # URL
                        href = await le.get_attribute("href") or ""
                        prod_url = (
                            href if href.startswith("http")
                            else "https://www.ihavecpu.com" + href
                        ) if href else ""

                        # Image
                        img = ""
                        ie = await le.query_selector("img")
                        if ie:
                            img = (
                                await ie.get_attribute("src") or
                                await ie.get_attribute("data-src") or
                                await ie.get_attribute("data-lazy") or ""
                            )
                            if img and not img.startswith("http"):
                                img = "https://www.ihavecpu.com" + img

                        # Auto-classify cooler type
                        actual_cat = cat_name
                        if cat_name == "Cooler":
                            lower = name.lower()
                            if any(k in lower for k in [
                                "liquid", "water", "240", "360", "120",
                                "ryujin", "kraken", "valkyrie", "galahad", "frozen",
                            ]):
                                actual_cat = "Liquid Cooler"
                            else:
                                actual_cat = "Air Cooler"

                        is_new = upsert_product(cur, matcher, {
                            "name": name, "price": price,
                            "img_url": img, "url": prod_url,
                            "category": actual_cat, "store": "ihavecpu",
                            "description": "",
                        })
                        if is_new:
                            cat_new += 1
                        else:
                            cat_upd += 1
                        count += 1

                    except Exception:
                        pass

                conn.commit()
                log(f"    -> {count} products processed")
                if count == 0:
                    break

            total_new += cat_new
            total_upd += cat_upd
            log(f"  [iHaveCPU] {cat_name}: +{cat_new} new, ~{cat_upd} merged")

        await browser.close()

    log(f"  [iHaveCPU] TOTAL: {total_new} new | {total_upd} merged into existing")
    return total_new, total_upd


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
async def run_all(stores: list[str], pages: int):
    conn = sqlite3.connect(DB_PATH)
    setup_db(conn)

    # SmartMatcher is shared across all 3 scrapers so cross-store dedup works
    matcher = SmartMatcher(conn.cursor())

    start = datetime.now()
    log(f"\n{'='*60}")
    log(f"  IT-RECOMMEND Full Scraper")
    log(f"  Stores : {', '.join(stores)}")
    log(f"  Pages  : {pages} per category")
    log(f"  Started: {start.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"{'='*60}\n")

    summary = {}

    if "advice" in stores:
        log("=== [Advice] ===")
        n, u = await scrape_advice(conn, matcher, pages)
        summary["advice"] = {"new": n, "updated": u}

    if "jib" in stores:
        log("\n=== [JIB] ===")
        n, u = await scrape_jib(conn, matcher, pages)
        summary["jib"] = {"new": n, "updated": u}

    if "ihavecpu" in stores:
        log("\n=== [iHaveCPU] ===")
        n, u = await scrape_ihavecpu(conn, matcher, pages)
        summary["ihavecpu"] = {"new": n, "updated": u}

    conn.close()

    elapsed = (datetime.now() - start).total_seconds()
    log(f"\n{'='*60}")
    log(f"  DONE — elapsed {elapsed:.0f}s")
    log(f"{'='*60}")

    # DB stats
    c = sqlite3.connect(DB_PATH)
    cur = c.cursor()
    total  = cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    adv    = cur.execute("SELECT COUNT(*) FROM products WHERE price_advice>0").fetchone()[0]
    jib    = cur.execute("SELECT COUNT(*) FROM products WHERE price_jib>0").fetchone()[0]
    ihc    = cur.execute("SELECT COUNT(*) FROM products WHERE price_ihavecpu>0").fetchone()[0]
    multi  = cur.execute(
        "SELECT COUNT(*) FROM products WHERE "
        "(CASE WHEN price_advice>0 THEN 1 ELSE 0 END + "
        " CASE WHEN price_jib>0    THEN 1 ELSE 0 END + "
        " CASE WHEN price_ihavecpu>0 THEN 1 ELSE 0 END) >= 2"
    ).fetchone()[0]
    c.close()

    log(f"\n  Products total   : {total}")
    log(f"  With Advice price: {adv}")
    log(f"  With JIB price   : {jib}")
    log(f"  With iHaveCPU    : {ihc}")
    log(f"  Multi-store (>=2): {multi}  ← สินค้าที่เปรียบเทียบราคาได้")
    log(f"\n  Per-store breakdown:")
    for store, s in summary.items():
        log(f"    {store:10}: +{s['new']} new  |  ~{s['updated']} merged into existing")


def main():
    parser = argparse.ArgumentParser(description="Full 3-store scraper with deduplication")
    parser.add_argument(
        "--stores", nargs="+", default=["all"],
        choices=["all", "advice", "jib", "ihavecpu"],
        help="Stores to scrape (default: all)",
    )
    parser.add_argument(
        "--pages", type=int, default=3,
        help="Max pages per category (default: 3)",
    )
    args = parser.parse_args()

    stores = ["advice", "jib", "ihavecpu"] if "all" in args.stores else args.stores
    asyncio.run(run_all(stores, args.pages))


if __name__ == "__main__":
    main()
