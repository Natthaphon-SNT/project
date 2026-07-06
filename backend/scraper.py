"""
Web Scraper - ดึงสินค้า+ราคา+รูป จาก 3 ร้านค้า:
  1. iHaveCPU  (ihavecpu.com)
  2. Advice    (advice.co.th)
  3. JIB       (jib.co.th)

รัน: python scraper.py
หรือ เรียกผ่าน API: POST /api/scrape  (body: {"store": "ihavecpu|advice|jib|all", "pages": 3})
"""
import asyncio, re, sqlite3, json
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Page

DB_PATH = "shop.db"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0.0.0 Safari/537.36")

# ─────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────
def parse_price(text: str) -> int:
    """แปลงข้อความราคาเป็น int (รองรับ ฿3,190.00 / 3,190 / 3190)"""
    text = text.strip().replace("฿", "").replace("THB", "").replace("บาท", "").strip()
    # จับตัวเลขแรกที่พบ รวม comma
    m = re.search(r"(\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?", text)
    if not m:
        return 0
    num = int(m.group(0).replace(",", ""))
    # กรองราคาสมเหตุสมผล: 200 ถึง 200,000 บาท
    if 200 <= num <= 200000:
        return num
    return 0

def upsert_product(cur: sqlite3.Cursor, p: dict):
    """เพิ่ม/อัปเดตสินค้าใน DB"""
    # กำหนด cid จาก category
    CID_MAP = {
        "cpu": "c01", "mainboard": "c02", "vga": "c03", "gpu": "c03",
        "ram": "c04", "ssd": "c05", "m.2": "c05", "nvme": "c05",
        "psu": "c06", "case": "c07", "liquid": "c08", "cooler": "c09",
    }
    cat_lower = p.get("category", "").lower()
    cid = next((v for k, v in CID_MAP.items() if k in cat_lower), "c01")

    cur.execute("""
        INSERT INTO products
            (product_id, p_name, p_description, p_price,
             price_advice, price_jib, price_ihavecpu,
             p_stock, cid, category, img_url, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(product_id) DO UPDATE SET
            p_name        = excluded.p_name,
            p_price       = CASE WHEN excluded.p_price > 0 THEN excluded.p_price ELSE p_price END,
            price_advice  = CASE WHEN excluded.price_advice > 0 THEN excluded.price_advice ELSE price_advice END,
            price_jib     = CASE WHEN excluded.price_jib > 0 THEN excluded.price_jib ELSE price_jib END,
            price_ihavecpu= CASE WHEN excluded.price_ihavecpu > 0 THEN excluded.price_ihavecpu ELSE price_ihavecpu END,
            img_url       = CASE WHEN excluded.img_url != '' THEN excluded.img_url ELSE img_url END,
            category      = excluded.category,
            cid           = excluded.cid
    """, (
        p["product_id"], p["p_name"], p.get("p_description", ""),
        p.get("p_price", 0),
        p.get("price_advice", 0), p.get("price_jib", 0), p.get("price_ihavecpu", 0),
        999, cid, p.get("category", ""),
        p.get("img_url", ""),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

# ─────────────────────────────────────────────────
# iHaveCPU Scraper  (ihavecpu.com/category/diy-*)
# ─────────────────────────────────────────────────
IHC_CATEGORIES = [
    ("CPU",          "https://www.ihavecpu.com/category/cpu"),
    ("Mainboard",    "https://www.ihavecpu.com/category/mainboard"),
    ("GPU",          "https://www.ihavecpu.com/category/vga"),
    ("RAM",          "https://www.ihavecpu.com/category/ram"),
    ("M.2",          "https://www.ihavecpu.com/category/ssd-m2"),
    ("PSU",          "https://www.ihavecpu.com/category/psu"),
    ("Case",         "https://www.ihavecpu.com/category/case"),
    ("Liquid Cooler","https://www.ihavecpu.com/category/liquid-cooler"),
    ("Air Cooler",   "https://www.ihavecpu.com/category/air-cooler"),
]

async def scrape_ihavecpu(page: Page, url: str, category: str, max_pages: int = 3) -> list[dict]:
    products = []

    # Warm-up: เข้าหน้าแรกก่อน เพื่อตั้ง session/cookie
    try:
        await page.goto("https://www.ihavecpu.com/", timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
    except Exception:
        pass

    for pg in range(1, max_pages + 1):
        paged = f"{url}?page={pg}" if pg > 1 else url
        try:
            # domcontentloaded เร็วกว่า networkidle (iHaveCPU มี lazy loading ทำให้ networkidle timeout)
            await page.goto(paged, timeout=30000, wait_until="domcontentloaded")
            # รอ React render สินค้า
            try:
                await page.wait_for_selector("a[href*='/product/'] h3", timeout=12000)
            except Exception:
                await page.wait_for_timeout(5000)

            title = await page.title()
            if "cloudflare" in title.lower() or "moment" in title.lower():
                print(f"  [iHaveCPU] Cloudflare block on page {pg}")
                break

            # Selector จาก browser inspection: a[href*='/product/']
            cards = await page.query_selector_all("a[href*='/product/']")
            if not cards:
                print(f"  [iHaveCPU] {category} page {pg}: no cards found")
                break

            page_count = 0
            seen = set()
            for card in cards:
                try:
                    # ชื่อ: h3 ภายใน card
                    name_el = await card.query_selector("h3")
                    if not name_el:
                        continue
                    name = (await name_el.inner_text()).strip()
                    if not name or len(name) < 5 or name in seen:
                        continue
                    seen.add(name)

                    # ราคา: span ที่มีตัวเลข
                    spans = await card.query_selector_all("span")
                    price = 0
                    for sp in spans:
                        txt = (await sp.inner_text()).strip()
                        p = parse_price(txt)
                        if 100 <= p <= 500000:
                            price = p
                            break

                    # รูปภาพ
                    img_el = await card.query_selector("img")
                    img_src = ""
                    if img_el:
                        img_src = (await img_el.get_attribute("src") or
                                   await img_el.get_attribute("data-src") or "")
                        if img_src.startswith("//"):
                            img_src = "https:" + img_src
                        # แปลง _150.jpg → _800.jpg ให้ได้รูปใหญ่ขึ้น
                        img_src = img_src.replace("_150.jpg", "_800.jpg").replace("_300.jpg", "_800.jpg")

                    href = await card.get_attribute("href") or ""
                    if href and not href.startswith("http"):
                        href = "https://www.ihavecpu.com" + href

                    pid = re.sub(r"[^a-z0-9]", "", name.lower())[:12] + f"_ihc{abs(hash(name)) % 9999:04d}"

                    products.append({
                        "product_id":     pid,
                        "p_name":         name,
                        "p_price":        price,
                        "price_ihavecpu": price,
                        "img_url":        img_src,
                        "category":       category,
                        "p_description":  "",
                        "source_url":     href,
                    })
                    page_count += 1
                except Exception:
                    continue

            print(f"  [iHaveCPU] {category} page {pg}: {page_count} products")
            if page_count == 0:
                break

        except Exception as e:
            print(f"  [iHaveCPU] Error page {pg}: {e}")
            break

    return products


# ─────────────────────────────────────────────────
# Advice Scraper  (advice.co.th/product/computer-hardware)
# ─────────────────────────────────────────────────
ADVICE_CATEGORIES = [
    ("CPU",          "https://www.advice.co.th/product/cpu"),
    ("Mainboard",    "https://www.advice.co.th/product/mainboard"),
    ("GPU",          "https://www.advice.co.th/product/graphic-card"),
    ("RAM",          "https://www.advice.co.th/product/ram"),
    ("M.2",          "https://www.advice.co.th/product/ssd-harddisk"),
    ("PSU",          "https://www.advice.co.th/product/power-supply"),
    ("Case",         "https://www.advice.co.th/product/case"),
    ("Liquid Cooler","https://www.advice.co.th/product/liquid-cooling"),
    ("Air Cooler",   "https://www.advice.co.th/product/cpu-cooler"),
]

async def scrape_advice(page: Page, url: str, category: str, max_pages: int = 3) -> list[dict]:
    products = []
    for pg in range(1, max_pages + 1):
        # Advice ใช้ ?page= parameter
        paged = f"{url}?page={pg}" if pg > 1 else url
        try:
            await page.goto(paged, timeout=45000, wait_until="networkidle")
            await page.wait_for_timeout(3000)

            title = await page.title()
            if "cloudflare" in title.lower() or "moment" in title.lower():
                print(f"  [Advice] Cloudflare block")
                break

            # Selector จาก browser inspection: div.list-product
            cards = await page.query_selector_all("div.list-product")
            if not cards:
                print(f"  [Advice] {category} page {pg}: no cards found")
                break

            page_count = 0
            seen = set()
            for card in cards:
                try:
                    # ชื่อ: a.fn-name
                    name_el = await card.query_selector("a.fn-name")
                    name = ""
                    if name_el:
                        name = ((await name_el.get_attribute("title")) or
                                (await name_el.inner_text())).strip()
                    if not name or len(name) < 3 or name in seen:
                        continue
                    seen.add(name)

                    # ราคา: .item-price-sale
                    price_el = await card.query_selector(".item-price-sale, .price-sale")
                    price_txt = (await price_el.inner_text()).strip() if price_el else "0"
                    price = parse_price(price_txt)

                    # รูป: img.img-product
                    img_el = await card.query_selector("img.img-product, img")
                    img_src = ""
                    if img_el:
                        img_src = (await img_el.get_attribute("src") or
                                   await img_el.get_attribute("data-src") or "")
                        if img_src.startswith("//"):
                            img_src = "https:" + img_src
                        if img_src and not img_src.startswith("http"):
                            img_src = "https://www.advice.co.th" + img_src

                    link_el = await card.query_selector("a.fn-name, a[href]")
                    href = await link_el.get_attribute("href") if link_el else ""

                    pid = re.sub(r"[^a-z0-9]", "", name.lower())[:12] + f"_adv{abs(hash(name)) % 9999:04d}"

                    if name and price > 0:
                        products.append({
                            "product_id":   pid,
                            "p_name":       name,
                            "p_price":      price,
                            "price_advice": price,
                            "img_url":      img_src,
                            "category":     category,
                            "p_description": "",
                            "source_url":   href,
                        })
                        page_count += 1
                except Exception:
                    continue

            print(f"  [Advice] {category} page {pg}: {page_count} products")
            if page_count == 0:
                break

        except Exception as e:
            print(f"  [Advice] Error page {pg}: {e}")
            break

    return products


# ─────────────────────────────────────────────────
# JIB Scraper  (jib.co.th)
# ─────────────────────────────────────────────────
JIB_CATEGORIES = [
    ("CPU",          "https://www.jib.co.th/web/product/product_list/1/42"),
    ("Mainboard",    "https://www.jib.co.th/web/product/product_list/1/43"),
    ("GPU",          "https://www.jib.co.th/web/product/product_list/1/44"),
    ("RAM",          "https://www.jib.co.th/web/product/product_list/1/45"),
    ("M.2",          "https://www.jib.co.th/web/product/product_list/1/46"),
    ("PSU",          "https://www.jib.co.th/web/product/product_list/1/50"),
    ("Case",         "https://www.jib.co.th/web/product/product_list/1/51"),
    ("Liquid Cooler","https://www.jib.co.th/web/product/product_list/1/48"),
    ("Air Cooler",   "https://www.jib.co.th/web/product/product_list/1/47"),
]

async def scrape_jib(page: Page, url: str, category: str, max_pages: int = 3) -> list[dict]:
    products = []
    for pg in range(1, max_pages + 1):
        # JIB เพิ่ม page ท้าย URL: /1/42/2  (page 2)
        paged = url.rstrip("/") + f"/{pg}" if pg > 1 else url
        try:
            await page.goto(paged, timeout=45000, wait_until="networkidle")
            await page.wait_for_timeout(3000)

            title = await page.title()
            if "cloudflare" in title.lower() or "moment" in title.lower():
                print(f"  [JIB] Cloudflare block")
                break

            # Selector จาก browser inspection: div.divboxpro
            cards = await page.query_selector_all("div.divboxpro")
            if not cards:
                # fallback: li.product-item
                cards = await page.query_selector_all("li.product-item, .product-box")
            if not cards:
                print(f"  [JIB] {category} page {pg}: no cards found")
                break

            page_count = 0
            seen = set()
            for card in cards:
                try:
                    # ชื่อ: span.promo_name
                    name_el = await card.query_selector("span.promo_name, p.name, .name")
                    name = (await name_el.inner_text()).strip() if name_el else ""
                    if not name or len(name) < 3 or name in seen:
                        continue
                    seen.add(name)

                    # ราคา: p.price_total
                    price_el = await card.query_selector("p.price_total, .price_total, [class*='price']")
                    price_txt = (await price_el.inner_text()).strip() if price_el else "0"
                    price = parse_price(price_txt)

                    # รูป: img.imgpspecial
                    img_el = await card.query_selector("img.imgpspecial, img")
                    img_src = ""
                    if img_el:
                        img_src = (await img_el.get_attribute("src") or
                                   await img_el.get_attribute("data-src") or "")
                        if img_src.startswith("//"):
                            img_src = "https:" + img_src
                        if img_src and not img_src.startswith("http"):
                            img_src = "https://www.jib.co.th" + img_src

                    link_el = await card.query_selector("a[href*='/readProduct/'], a[href]")
                    href = await link_el.get_attribute("href") if link_el else ""
                    if href and not href.startswith("http"):
                        href = "https://www.jib.co.th" + href

                    pid = re.sub(r"[^a-z0-9]", "", name.lower())[:12] + f"_jib{abs(hash(name)) % 9999:04d}"

                    if name and price > 0:
                        products.append({
                            "product_id":  pid,
                            "p_name":      name,
                            "p_price":     price,
                            "price_jib":   price,
                            "img_url":     img_src,
                            "category":    category,
                            "p_description": "",
                            "source_url":  href,
                        })
                        page_count += 1
                except Exception:
                    continue

            print(f"  [JIB] {category} page {pg}: {page_count} products")
            if page_count == 0:
                break

        except Exception as e:
            print(f"  [JIB] Error page {pg}: {e}")
            break

    return products


# ─────────────────────────────────────────────────
# Main Runner
# ─────────────────────────────────────────────────
async def run_scraper(stores: list[str] = ["ihavecpu", "advice", "jib"],
                      max_pages: int = 3) -> dict:
    summary = {"ihavecpu": 0, "advice": 0, "jib": 0, "total": 0, "errors": []}

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox", "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--window-size=1280,800",
            ]
        )

        async def new_page():
            ctx = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=UA,
                ignore_https_errors=True,
            )
            await ctx.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            return await ctx.new_page()

        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()

        # ── iHaveCPU ─────────────────────────────
        if "ihavecpu" in stores:
            print("\n[iHaveCPU] เริ่ม scrape...")
            for category, url in IHC_CATEGORIES:
                page = await new_page()   # fresh page ทุก category
                try:
                    items = await scrape_ihavecpu(page, url, category, max_pages)
                    for p in items:
                        upsert_product(cur, p)
                    conn.commit()
                    summary["ihavecpu"] += len(items)
                    print(f"  [iHaveCPU] {category}: +{len(items)} สินค้า")
                except Exception as e:
                    summary["errors"].append(f"iHaveCPU/{category}: {e}")
                finally:
                    await page.close()

        # ── Advice ───────────────────────────────
        if "advice" in stores:
            print("\n[Advice] เริ่ม scrape...")
            for category, url in ADVICE_CATEGORIES:
                page = await new_page()
                try:
                    items = await scrape_advice(page, url, category, max_pages)
                    for p in items:
                        upsert_product(cur, p)
                    conn.commit()
                    summary["advice"] += len(items)
                    print(f"  [Advice] {category}: +{len(items)} สินค้า")
                except Exception as e:
                    summary["errors"].append(f"Advice/{category}: {e}")
                finally:
                    await page.close()

        # ── JIB ──────────────────────────────────
        if "jib" in stores:
            print("\n[JIB] เริ่ม scrape...")
            for category, url in JIB_CATEGORIES:
                page = await new_page()
                try:
                    items = await scrape_jib(page, url, category, max_pages)
                    for p in items:
                        upsert_product(cur, p)
                    conn.commit()
                    summary["jib"] += len(items)
                    print(f"  [JIB] {category}: +{len(items)} สินค้า")
                except Exception as e:
                    summary["errors"].append(f"JIB/{category}: {e}")
                finally:
                    await page.close()

        await browser.close()
        conn.close()

    summary["total"] = summary["ihavecpu"] + summary["advice"] + summary["jib"]
    return summary


# ─────────────────────────────────────────────────
# CLI entry
# ─────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    stores = sys.argv[1:] if len(sys.argv) > 1 else ["ihavecpu", "advice", "jib"]
    pages  = 3

    print(f"Scraping: {stores}  |  max {pages} pages/category")
    result = asyncio.run(run_scraper(stores, pages))
    print(f"\n=== DONE ===")
    print(f"  iHaveCPU : {result['ihavecpu']}")
    print(f"  Advice   : {result['advice']}")
    print(f"  JIB      : {result['jib']}")
    print(f"  Total    : {result['total']}")
    if result["errors"]:
        print(f"  Errors   : {len(result['errors'])}")
        for e in result["errors"][:5]:
            print(f"    - {e}")
