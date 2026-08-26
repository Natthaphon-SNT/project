"""
Script: fetch_descriptions.py
ดึงเฉพาะ description + image ที่ยังขาดอยู่สำหรับสินค้าที่มีใน DB แล้ว
โดยเยี่ยมชมหน้า product detail ของแต่ละร้านโดยตรง

รัน: python -X utf8 fetch_descriptions.py [batch_size] [store]
ตัวอย่าง: python -X utf8 fetch_descriptions.py 50 advice
          python -X utf8 fetch_descriptions.py 50 jib
          python -X utf8 fetch_descriptions.py 50 ihavecpu
          python -X utf8 fetch_descriptions.py 50 all
"""
import asyncio, sqlite3, sys
from playwright.async_api import async_playwright

DB_PATH = "shop.db"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
ANTI_BOT = ("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            "window.chrome={runtime:{}};")

def log(msg):
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode('ascii', 'replace').decode('ascii'), flush=True)


async def _try_get_img(el) -> str:
    for attr in ["src", "data-src", "data-lazy", "data-original"]:
        try:
            v = await el.get_attribute(attr) or ""
            if v and v.startswith("http") and not v.endswith(".gif"):
                return v
        except:
            pass
    return ""


async def get_og_image(page) -> str:
    """Fallback: ดึง og:image จาก meta tag"""
    try:
        meta = await page.query_selector('meta[property="og:image"]')
        if meta:
            content = await meta.get_attribute("content") or ""
            if content and content.startswith("http"):
                return content
    except:
        pass
    return ""


async def get_meta_desc(page) -> str:
    """Fallback: ดึง meta description"""
    try:
        meta = await page.query_selector('meta[name="description"]')
        if meta:
            content = await meta.get_attribute("content") or ""
            if content and len(content) > 20:
                return content.strip()
    except:
        pass
    return ""


async def fetch_advice_detail(page, url: str) -> tuple[str, str]:
    desc, img = "", ""
    try:
        await page.goto(url, timeout=35000, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        desc_selectors = [
            ".spec-content", ".product-description", ".spec-list",
            "[class*='spec']", "[class*='description']", "[class*='detail']",
            ".tab-content", "#tab-description", "#tab-spec",
            "div.product-spec", "table.spec-table",
        ]
        for sel in desc_selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    t = (await el.inner_text()).strip()
                    if t and len(t) > 20:
                        desc = t; break
            except: pass

        if not desc:
            desc = await get_meta_desc(page)

        img_selectors = [
            "img.main-product-image", "img#main-product-img",
            "div.product-gallery img:first-child",
            ".swiper-slide-active img", ".product-img img",
            "[class*='gallery'] img", "[class*='product-image'] img",
            "img[src*='img.advice']", "img[class*='product']",
        ]
        for sel in img_selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    src = await _try_get_img(el)
                    if src: img = src; break
            except: pass

        if not img:
            img = await get_og_image(page)
    except Exception as e:
        log(f"    [Advice err] {e}")
    return desc, img


async def fetch_jib_detail(page, url: str) -> tuple[str, str]:
    desc, img = "", ""
    try:
        await page.goto(url, timeout=35000, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

        desc_selectors = [
            "#product-description", "div#tab_description", "div.description",
            "table.table-spec", "div.product-detail-content",
            "div[id*='description']", "div[id*='spec']",
            "div[class*='description']", "div[class*='spec']",
            "#detail_spec", "#product_detail", ".detail_spec", "table.spec",
        ]
        for sel in desc_selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    t = (await el.inner_text()).strip()
                    if t and len(t) > 20:
                        desc = t; break
            except: pass

        if not desc:
            desc = await get_meta_desc(page)

        img_selectors = [
            "img#main_img", "img#bigimage", "div#bigimage img",
            "div.product-bigimage img", "img[id*='main']",
            "div.product-image img", "div.img-content img",
            "img[src*='jib']", "img[class*='main']",
            "div.product-gallery img:first-child",
        ]
        for sel in img_selectors:
            try:
                el = await page.query_selector(sel)
                if el:
                    src = await _try_get_img(el)
                    if src: img = src; break
            except: pass

        if not img:
            img = await get_og_image(page)
    except Exception as e:
        log(f"    [JIB err] {e}")
    return desc, img


async def fetch_ihc_detail(page, url: str) -> tuple[str, str]:
    desc, img = "", ""
    try:
        await page.goto(url, timeout=35000, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)

        # ─── วิธีที่ 1: ดึง spec จาก __NEXT_DATA__ (Next.js server-rendered JSON) ───
        # ihavecpu เป็น Next.js – ข้อมูล spec อยู่ใน <script id="__NEXT_DATA__"> แบบ structured
        try:
            spec_text = await page.evaluate("""
                () => {
                    const el = document.getElementById('__NEXT_DATA__');
                    if (!el) return null;
                    try {
                        const data = JSON.parse(el.textContent);
                        const product = data?.props?.pageProps?.product;
                        if (!product) return null;
                        const props = product.property;
                        if (!props || !Array.isArray(props) || props.length === 0) return null;
                        // แปลง property array เป็น text "Key: Value" แต่ละบรรทัด
                        return props.map(p => {
                            const key = p.filter_text || p.name_th || p.name_gb || '';
                            const vals = (p.detail || []).map(d => d.name_th || d.name_gb || '').join(', ');
                            return key + ': ' + vals;
                        }).filter(line => line.trim().length > 2).join('\\n');
                    } catch(e) { return null; }
                }
            """)
            if spec_text and len(spec_text) > 20:
                desc = spec_text.strip()
                log(f"    [iHaveCPU] spec from __NEXT_DATA__: {len(desc)} chars")
        except Exception as e:
            log(f"    [iHaveCPU __NEXT_DATA__ err] {e}")

        # ─── วิธีที่ 2: fallback ดึงจาก table tr ───
        if not desc:
            try:
                spec_text = await page.evaluate("""
                    () => {
                        const rows = document.querySelectorAll('table tr');
                        if (rows.length === 0) return null;
                        const lines = Array.from(rows)
                            .map(r => r.innerText.trim())
                            .filter(t => t.length > 0);
                        // deduplicate (ihavecpu renders spec twice)
                        const seen = new Set();
                        const unique = [];
                        for (const line of lines) {
                            const key = line.split('\\t')[0].trim();
                            if (!seen.has(key)) { seen.add(key); unique.push(line); }
                        }
                        return unique.join('\\n');
                    }
                """)
                if spec_text and len(spec_text) > 20:
                    desc = spec_text.strip()
                    log(f"    [iHaveCPU] spec from table tr: {len(desc)} chars")
            except Exception as e:
                log(f"    [iHaveCPU table err] {e}")

        # ─── วิธีที่ 3: fallback เดิม – CSS selectors ───
        if not desc:
            desc_selectors = [
                "div.product-description", "div.description", "#product-description",
                "[class*='product-desc']", "[class*='product-spec']",
                "[class*='spec-content']", "div.tabs-content", "div.tab-content",
                "#tab-description", "#tab-spec", "table.spec-table",
                "div.product-detail", "div[class*='detail']",
            ]
            for sel in desc_selectors:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        t = (await el.inner_text()).strip()
                        if t and len(t) > 20:
                            desc = t; break
                except:
                    pass

        # ─── วิธีที่ 4: meta description ───
        if not desc:
            desc = await get_meta_desc(page)

        # ─── ดึงรูปภาพจาก __NEXT_DATA__ ก่อน ───
        try:
            og_img = await page.evaluate("""
                () => {
                    const el = document.getElementById('__NEXT_DATA__');
                    if (!el) return null;
                    try {
                        const data = JSON.parse(el.textContent);
                        const product = data?.props?.pageProps?.product;
                        if (!product) return null;
                        // หารูปหลักจาก product images array
                        const images = product.images || product.product_images || [];
                        if (images.length > 0) {
                            const img = images[0];
                            return img.image_url || img.url || img.src || null;
                        }
                        return null;
                    } catch(e) { return null; }
                }
            """)
            if og_img and og_img.startswith("http"):
                img = og_img
        except:
            pass

        # ─── fallback รูปจาก og:image / CSS selectors ───
        if not img:
            img_selectors = [
                "img.product-main-img", "img#main-image", "img#mainImage",
                "div.product-gallery img:first-child",
                "div.product-images img:first-child",
                "div.swiper-slide:first-child img", "div.swiper-wrapper img:first-child",
                "[class*='product-image'] img", "[class*='gallery'] img",
                "img[src*='ihavecpu']", "img[src*='ihcupload']",
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

        if not img:
            img = await get_og_image(page)

    except Exception as e:
        log(f"    [iHaveCPU err] {e}")
    return desc, img


async def fill_descriptions(store: str, batch: int = 50):
    """ดึง description + image สำหรับ store ที่กำหนด"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    url_col  = {"advice": "url_advice",    "jib": "url_jib",    "ihavecpu": "url_ihavecpu"}[store]
    desc_col = {"advice": "desc_advice",   "jib": "desc_jib",   "ihavecpu": "desc_ihavecpu"}[store]
    price_col = {"advice": "price_advice", "jib": "price_jib",  "ihavecpu": "price_ihavecpu"}[store]

    # ดึงสินค้าที่มี URL แต่ยังไม่มี description หรือรูป
    cur.execute(f"""
        SELECT product_id, p_name, {url_col}, img_url
        FROM products
        WHERE {url_col} != '' AND {url_col} IS NOT NULL
          AND {price_col} > 0
          AND ({desc_col} = '' OR {desc_col} IS NULL
               OR img_url = '' OR img_url IS NULL)
        LIMIT ?
    """, (batch,))
    rows = cur.fetchall()

    if not rows:
        log(f"[{store}] ไม่มีสินค้าที่ต้องดึง description (batch={batch})")
        conn.close()
        return

    log(f"[{store}] กำลังดึง description/image สำหรับ {len(rows)} สินค้า...")

    fetch_fn = {"advice": fetch_advice_detail, "jib": fetch_jib_detail, "ihavecpu": fetch_ihc_detail}[store]

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        ctx = await browser.new_context(user_agent=UA, viewport={"width": 1280, "height": 800})
        await ctx.add_init_script(ANTI_BOT)
        page = await ctx.new_page()

        success = 0
        for i, (pid, name, url, cur_img) in enumerate(rows):
            if not url:
                continue
            log(f"  [{i+1}/{len(rows)}] {name[:45]}")
            desc, img = await fetch_fn(page, url)

            updates = []
            params = []
            if desc:
                updates.append(f"{desc_col} = ?")
                params.append(desc)
            if img and (not cur_img or not cur_img.startswith("http")):
                updates.append("img_url = ?")
                params.append(img)

            if updates:
                params.append(pid)
                cur.execute(f"UPDATE products SET {', '.join(updates)} WHERE product_id = ?", params)
                conn.commit()
                success += 1
                log(f"    -> desc:{bool(desc)} img:{bool(img)}")
            else:
                log(f"    -> no data found")

        await browser.close()
    conn.close()
    log(f"\n[{store}] สำเร็จ {success}/{len(rows)} รายการ")


async def main():
    store_arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    batch = int(sys.argv[2]) if len(sys.argv) > 2 else 50

    stores = ["advice", "jib", "ihavecpu"] if store_arg == "all" else [store_arg]
    for s in stores:
        await fill_descriptions(s, batch)


if __name__ == "__main__":
    asyncio.run(main())
