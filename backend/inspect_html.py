"""
ตรวจสอบโครงสร้าง HTML จริงจาก JIB และ iHaveCPU
รัน: python inspect_html.py
"""
import asyncio
from playwright.async_api import async_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"

async def inspect():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=UA,
        )
        await ctx.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = await ctx.new_page()

        # ── JIB CPU ──────────────────────────────
        print("=" * 60)
        print("JIB: https://www.jib.co.th/web/product/product_list/1/42")
        print("=" * 60)
        await page.goto("https://www.jib.co.th/web/product/product_list/1/42",
                        timeout=45000, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # dump top-level class names of first 5 child divs
        jib_info = await page.evaluate("""() => {
            const results = [];
            // ลอง divboxpro
            const boxes = document.querySelectorAll('div.divboxpro');
            if (boxes.length > 0) {
                const b = boxes[0];
                const nameEl = b.querySelector('span.promo_name') || b.querySelector('p.name') || b.querySelector('h3');
                const priceEl = b.querySelector('p.price_total') || b.querySelector('[class*="price"]');
                const imgEl = b.querySelector('img');
                results.push({
                    selector: 'div.divboxpro',
                    count: boxes.length,
                    sample_name: nameEl ? nameEl.innerText.trim() : 'NOT FOUND',
                    sample_price: priceEl ? priceEl.innerText.trim() : 'NOT FOUND',
                    sample_img: imgEl ? (imgEl.src || imgEl.dataset.src || '') : 'NOT FOUND',
                    html_snippet: b.innerHTML.substring(0, 500)
                });
            } else {
                results.push({ selector: 'div.divboxpro', count: 0 });
                // probe other selectors
                for (const sel of ['li.product-item','div.product-item','.pro-item','.product-box','div[class*="product"]']) {
                    const els = document.querySelectorAll(sel);
                    if (els.length > 0) {
                        results.push({ selector: sel, count: els.length, html_snippet: els[0].innerHTML.substring(0, 300) });
                        break;
                    }
                }
            }
            return results;
        }""")
        for r in jib_info:
            print(f"Selector: {r.get('selector')} | Count: {r.get('count')}")
            if r.get('sample_name'):
                print(f"  Name:  {r.get('sample_name')}")
                print(f"  Price: {r.get('sample_price')}")
                print(f"  Img:   {r.get('sample_img', '')[:80]}")
            if r.get('html_snippet'):
                print(f"  HTML:  {r.get('html_snippet', '')[:300]}")

        # ── iHaveCPU CPU ─────────────────────────
        print()
        print("=" * 60)
        print("iHaveCPU: https://www.ihavecpu.com/category/cpu")
        print("=" * 60)
        await page.goto("https://www.ihavecpu.com/category/cpu",
                        timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(5000)

        ihc_info = await page.evaluate("""() => {
            const results = [];
            // ลอง a[href*='/product/']
            const links = document.querySelectorAll("a[href*='/product/']");
            if (links.length > 0) {
                const a = links[0];
                const nameEl = a.querySelector('h3') || a.querySelector('p') || a.querySelector('[class*="name"]');
                const priceEl = a.querySelector('span') || a.querySelector('[class*="price"]');
                const imgEl = a.querySelector('img');
                results.push({
                    selector: "a[href*='/product/']",
                    count: links.length,
                    sample_name: nameEl ? nameEl.innerText.trim() : 'NOT FOUND',
                    sample_price: priceEl ? priceEl.innerText.trim() : 'NOT FOUND',
                    sample_img: imgEl ? (imgEl.src || imgEl.dataset.src || '') : 'NOT FOUND',
                    html_snippet: a.innerHTML.substring(0, 500)
                });
            } else {
                results.push({ selector: "a[href*='/product/']", count: 0 });
                // probe
                for (const sel of ['.product-card','div.card','div[class*="product"]','article']) {
                    const els = document.querySelectorAll(sel);
                    if (els.length > 0) {
                        results.push({ selector: sel, count: els.length, html_snippet: els[0].innerHTML.substring(0,400) });
                        break;
                    }
                }
            }
            // แสดง title ของหน้า
            results.push({ info: 'page_title', title: document.title });
            return results;
        }""")
        for r in ihc_info:
            if r.get('info'):
                print(f"Page title: {r.get('title')}")
                continue
            print(f"Selector: {r.get('selector')} | Count: {r.get('count')}")
            if r.get('sample_name'):
                print(f"  Name:  {r.get('sample_name')}")
                print(f"  Price: {r.get('sample_price')}")
                print(f"  Img:   {r.get('sample_img', '')[:80]}")
            if r.get('html_snippet'):
                print(f"  HTML:  {r.get('html_snippet', '')[:400]}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
