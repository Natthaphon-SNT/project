"""
scrape_pcset.py – ดึงชุดคอมประกอบสำเร็จรูปจาก iHaveCPU / JIB / Advice
เก็บลง DB ในหมวดหมู่ category="PC Set", cid="c18"

รัน: python -X utf8 scrape_pcset.py [store] [pages]
     python -X utf8 scrape_pcset.py all 3
"""
import asyncio, hashlib, os, re, sqlite3, sys
from playwright.async_api import async_playwright

DB_PATH = os.path.join(os.path.dirname(__file__), "shop.db")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
ANTI_BOT = ("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            "window.chrome={runtime:{}};")

PCSET_URLS = {
    "ihavecpu": [
        "https://ihavecpu.com/promotion?type=M",        # ชุดคอม (Promotion type M)
    ],
    "jib": [
        "https://www.jib.co.th/web/product/product_list/1/1400",  # เซ็ตคอม JIB
    ],
    "advice": [
        "https://www.advice.co.th/product/computer-set-amd",     # ชุดคอม AMD
        "https://www.advice.co.th/product/computer-set-intel",   # ชุดคอม Intel
    ],
}

SKIP_KEYWORDS = [
    "NOTEBOOK", "LAPTOP", "โน๊ตบุ๊ค", "MACBOOK", "MOUSE PAD",
    "PRE ORDER", "BY ORDER",
]

def log(msg):
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'), flush=True)

def should_skip(name: str) -> bool:
    n = name.upper()
    return any(kw in n for kw in SKIP_KEYWORDS)


def looks_like_pcset(name: str) -> bool:
    n = (name or "").upper().strip()
    return bool(re.search(r"COMPUTER\s*SET|PC\s*SET|\u0e04\u0e2d\u0e21\u0e1b\u0e23\u0e30\u0e01\u0e2d\u0e1a|^AUG\d", n))

def parse_price(text) -> int:
    if not text:
        return 0
    if isinstance(text, (int, float)):
        return int(text)
    text = str(text).strip().replace(",", "").replace("฿", "").replace("THB", "").strip()
    m = re.search(r"\d+(?:\.\d+)?", text)
    if not m:
        return 0
    try:
        n = int(float(m.group(0)))
    except Exception:
        return 0
    return n if 500 <= n <= 999_999 else 0

def make_pid(name: str, store: str) -> str:
    slug = re.sub(r"[^a-z0-9]", "", name.lower())[:12]
    h = hashlib.md5(f"{name}_{store}".encode()).hexdigest()[:8]
    return f"pcset_{slug}_{store[:3]}_{h}"

def init_db(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO categories (cid, c_name, c_description) VALUES (?,?,?)",
        ("c18", "PC Set", "ชุดคอมประกอบสำเร็จรูปจากร้าน iHaveCPU / JIB / Advice")
    )
    conn.commit()

# ────────────────────────────────────────────
# iHaveCPU PC Sets
# ────────────────────────────────────────────
async def scrape_ihavecpu_pcsets(page, max_pages: int = 3) -> list[dict]:
    items = []
    base_url = PCSET_URLS["ihavecpu"][0]  # https://ihavecpu.com/promotion?type=M

    for page_num in range(1, max_pages + 1):
        # URL pattern: ?type=M&page=2, ?type=M&page=3 ...
        url = f"{base_url}&page={page_num}" if page_num > 1 else base_url
        log(f"[iHaveCPU] Page {page_num}: {url}")
        try:
            await page.goto(url, timeout=30000, wait_until="networkidle")
            await page.wait_for_timeout(2500)

            products = await page.evaluate("""
                () => {
                    // Try __NEXT_DATA__ first
                    const el = document.getElementById('__NEXT_DATA__');
                    if (el) {
                        try {
                            const d = JSON.parse(el.textContent);
                            const items = d?.props?.pageProps?.product?.data
                                       || d?.props?.pageProps?.products
                                       || d?.props?.pageProps?.data
                                       || [];
                            if (items.length > 0) {
                                return items.map(p => ({
                                    name:  p.name_th || p.name_gb || p.name || '',
                                    price: p.price_sale || p.price_before || p.price || 0,
                                    img:   p.image800 || p.image || '',
                                    url:   p.product_id
                                           ? 'https://ihavecpu.com/product/' + p.product_id
                                           : (p.url || ''),
                                }));
                            }
                        } catch(e) {}
                    }
                    // Fallback: parse DOM cards
                    const cards = document.querySelectorAll(
                        '.product-card, .product-item, [class*="product"], .card'
                    );
                    return Array.from(cards).map(card => {
                        const nameEl  = card.querySelector('[class*="name"], h3, h4, a[title]');
                        const priceEl = card.querySelector('[class*="price"], .price');
                        const imgEl   = card.querySelector('img');
                        const linkEl  = card.querySelector('a');
                        return {
                            name:  nameEl  ? (nameEl.getAttribute('title') || nameEl.innerText.trim()) : '',
                            price: priceEl ? priceEl.innerText.trim() : '0',
                            img:   imgEl   ? (imgEl.src || imgEl.getAttribute('data-src') || '') : '',
                            url:   linkEl  ? linkEl.href : '',
                        };
                    }).filter(p => p.name && p.name.length > 3);
                }
            """)

            if not products:
                log(f"[iHaveCPU] Page {page_num}: ไม่มีสินค้า → หยุด")
                break

            for p in products:
                if not p.get("name") or should_skip(p["name"]):
                    continue
                price = parse_price(p.get("price", 0))
                if price < 500:
                    continue
                items.append({
                    "name":  p["name"],
                    "price": price,
                    "img":   p.get("img", ""),
                    "url":   p.get("url", ""),
                    "store": "ihavecpu",
                })
            log(f"[iHaveCPU] Page {page_num}: +{len(products)} raw → {len(items)} kept so far")
        except Exception as e:
            log(f"[iHaveCPU] Page {page_num} error: {e}")
            break

    return items

# ────────────────────────────────────────────
# JIB PC Sets
# ────────────────────────────────────────────
async def scrape_jib_pcsets(page, max_pages: int = 3) -> list[dict]:
    items = []
    base_url = PCSET_URLS["jib"][0]  # https://www.jib.co.th/web/product/product_list/1/1400

    for page_num in range(1, max_pages + 1):
        url = f"{base_url}/{page_num}" if page_num > 1 else base_url
        log(f"[JIB] Page {page_num}: {url}")
        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            products = await page.evaluate("""
                () => {
                    const cards = document.querySelectorAll(
                        'div.divboxpro, .div_product, .product_list_item, .box_product, [class*="product_box"]'
                    );
                    return Array.from(cards).map(card => {
                        const nameEl  = card.querySelector('span.promo_name')
                                      || card.querySelector('.proname, .product-name, .title, h3, a[title]');
                        const priceEl = card.querySelector('p.price_total')
                                      || card.querySelector('.price, .product-price, [class*="price"]');
                        const imgEl   = card.querySelector('img');
                        const links   = Array.from(card.querySelectorAll('a[href]'));
                        const linkEl  = links.find(a => (a.href || '').includes('/web/product/readProduct/')) || links[0];
                        return {
                            name:  nameEl  ? (nameEl.getAttribute('title') || nameEl.innerText.trim()) : '',
                            price: priceEl ? priceEl.innerText.trim() : '',
                            img:   imgEl   ? (imgEl.src || imgEl.getAttribute('data-src') || '') : '',
                            url:   linkEl  ? linkEl.href : '',
                        };
                    }).filter(p => p.name && p.name.length > 3);
                }
            """)

            if not products:
                log(f"[JIB] Page {page_num}: ไม่มีสินค้า → หยุด")
                break

            for p in products:
                name = p.get("name", "")
                if not name or should_skip(name) or not looks_like_pcset(name):
                    continue
                price = parse_price(p.get("price", ""))
                if price < 500:
                    continue
                items.append({
                    "name":  name,
                    "price": price,
                    "img":   p.get("img", ""),
                    "url":   p.get("url", ""),
                    "store": "jib",
                })
            log(f"[JIB] Page {page_num}: +{len(products)} raw → {len(items)} kept so far")
        except Exception as e:
            log(f"[JIB] Page {page_num} error: {e}")
            break

    return items

# ────────────────────────────────────────────
# Advice PC Sets
# ────────────────────────────────────────────
async def scrape_advice_pcsets(page, max_pages: int = 3) -> list[dict]:
    items = []
    urls = PCSET_URLS["advice"]  # [amd_url, intel_url]

    for base_url in urls:
        tag = "AMD" if "amd" in base_url else "Intel"
        for page_num in range(1, max_pages + 1):
            url = f"{base_url}?page={page_num}" if page_num > 1 else base_url
            log(f"[Advice-{tag}] Page {page_num}: {url}")
            try:
                await page.goto(url, timeout=30000, wait_until="networkidle")
                await page.wait_for_timeout(3000)

                products = await page.evaluate("""
                    () => {
                        const cards = document.querySelectorAll(
                            '.product-item, .product-card, .box-product, [class*="product-item"]'
                        );
                        return Array.from(cards).map(card => {
                            const nameEl  = card.querySelector('.product-name, .name, h3, [class*="name"]');
                            const priceEl = card.querySelector('.price, [class*="price"]');
                            const imgEl   = card.querySelector('img');
                            const linkEl  = card.querySelector('a');
                            return {
                                name:  nameEl  ? nameEl.innerText.trim() : '',
                                price: priceEl ? priceEl.innerText.trim() : '',
                                img:   imgEl   ? (imgEl.src || imgEl.getAttribute('data-src') || '') : '',
                                url:   linkEl  ? linkEl.href : '',
                            };
                        }).filter(p => p.name.length > 5);
                    }
                """)

                if not products:
                    log(f"[Advice-{tag}] Page {page_num}: ไม่มีสินค้า → หยุด")
                    break

                for p in products:
                    name = p.get("name", "")
                    if not name or should_skip(name):
                        continue
                    price = parse_price(p.get("price", ""))
                    if price < 500:
                        continue
                    items.append({
                        "name":  name,
                        "price": price,
                        "img":   p.get("img", ""),
                        "url":   p.get("url", ""),
                        "store": "advice",
                    })
                log(f"[Advice-{tag}] Page {page_num}: +{len(products)} raw → {len(items)} kept so far")
            except Exception as e:
                log(f"[Advice-{tag}] Page {page_num} error: {e}")
                break

    return items

# ────────────────────────────────────────────
# Save to DB
# ────────────────────────────────────────────
def save_pcsets(conn: sqlite3.Connection, items: list[dict]):
    cur = conn.cursor()
    added = updated = skipped = 0

    for item in items:
        name  = item["name"].strip()
        price = item["price"]
        img   = item.get("img", "")
        url   = item.get("url", "")
        store = item["store"]
        pid   = make_pid(name, store)

        url_col   = f"url_{store}"
        price_col = f"price_{store}"

        cur.execute("SELECT product_id FROM products WHERE product_id=?", (pid,))
        existing = cur.fetchone()

        if existing:
            cur.execute(
                f"UPDATE products SET {price_col}=?, {url_col}=?, p_price=? WHERE product_id=?",
                (price, url, price, pid)
            )
            updated += 1
        else:
            try:
                cur.execute("""
                    INSERT INTO products
                        (product_id, p_name, p_description, p_price,
                         price_advice, price_jib, price_ihavecpu,
                         url_advice, url_jib, url_ihavecpu,
                         p_stock, cid, category, img_url, specs)
                    VALUES (?,?,?,?, 0,0,0, '','','', 0,'c18','PC Set',?,?)
                """, (
                    pid, name, f"เซ็ตคอมประกอบจากร้าน {store.upper()}: {name}",
                    price, img, ""
                ))
                cur.execute(
                    f"UPDATE products SET {price_col}=?, {url_col}=? WHERE product_id=?",
                    (price, url, pid)
                )
                added += 1
            except Exception as e:
                log(f"  [DB] Insert error ({name[:40]}): {e}")
                skipped += 1

    conn.commit()
    return added, updated, skipped

# ────────────────────────────────────────────
# Main
# ────────────────────────────────────────────
async def main():
    store_arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    stores = ["ihavecpu", "jib", "advice"] if store_arg == "all" else [store_arg]
    log(f"[PC Sets] Scraping stores: {stores}, pages: {max_pages}")

    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    total_added = total_updated = 0

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        ctx = await browser.new_context(user_agent=UA, viewport={"width": 1280, "height": 900})
        await ctx.add_init_script(ANTI_BOT)
        page = await ctx.new_page()

        for store in stores:
            log(f"\n{'='*50}")
            log(f"[{store.upper()}] เริ่ม scrape PC Sets...")

            if store == "ihavecpu":
                items = await scrape_ihavecpu_pcsets(page, max_pages)
            elif store == "jib":
                items = await scrape_jib_pcsets(page, max_pages)
            elif store == "advice":
                items = await scrape_advice_pcsets(page, max_pages)
            else:
                log(f"  Unknown store: {store}")
                continue

            log(f"[{store.upper()}] ดึงได้ {len(items)} รายการ → บันทึก DB...")
            added, updated, skipped = save_pcsets(conn, items)
            log(f"[{store.upper()}] added={added} updated={updated} skipped={skipped}")
            total_added += added
            total_updated += updated

        await browser.close()

    conn.close()
    log(f"\n[PC Sets] เสร็จสิ้น: เพิ่มใหม่ {total_added}, อัปเดต {total_updated} รายการ")
    log("[PC Sets] สามารถดูผ่าน /category/pc+set หรือ /products?category=PC+Set")

if __name__ == "__main__":
    asyncio.run(main())
