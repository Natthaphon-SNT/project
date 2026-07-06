"""
Debug: ทดสอบว่า scrape_ihavecpu ใน run_scraper (fresh page) ทำงานได้ไหม
"""
import asyncio, re
from playwright.async_api import async_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"

def parse_price(text: str) -> int:
    text = text.strip().replace("฿", "").replace("THB", "").replace("บาท", "").strip()
    m = re.search(r"(\d{1,3}(?:,\d{3})*|\d+)(?:\.\d+)?", text)
    if not m:
        return 0
    num = int(m.group(0).replace(",", ""))
    return num if 200 <= num <= 200000 else 0

async def debug():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])

        # สร้าง fresh context/page เหมือน run_scraper
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=UA,
            ignore_https_errors=True,
        )
        await ctx.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = await ctx.new_page()

        print("Warm-up...")
        await page.goto("https://www.ihavecpu.com/", timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)

        print("Going to category...")
        await page.goto("https://www.ihavecpu.com/category/cpu",
                        timeout=30000, wait_until="domcontentloaded")

        print("Waiting for h3...")
        try:
            await page.wait_for_selector("h3", timeout=12000)
            print("  h3 FOUND!")
        except Exception as e:
            print(f"  h3 TIMEOUT: {e}")
            await page.wait_for_timeout(5000)

        # นับ elements
        info = await page.evaluate("""() => ({
            links: document.querySelectorAll("a[href*='/product/']").length,
            h3s: document.querySelectorAll("h3").length,
            title: document.title,
            url: window.location.href
        })""")
        print(f"  Links: {info['links']}, h3s: {info['h3s']}")
        print(f"  URL: {info['url']}")
        print(f"  Title: {info['title']}")

        # ลอง scrape
        cards = await page.query_selector_all("a[href*='/product/']")
        print(f"\nFound {len(cards)} cards")
        count = 0
        seen = set()
        for card in cards[:20]:
            try:
                name_el = await card.query_selector("h3")
                if not name_el:
                    continue
                name = (await name_el.inner_text()).strip()
                if not name or name in seen:
                    continue
                seen.add(name)

                spans = await card.query_selector_all("span")
                price = 0
                for sp in spans:
                    txt = (await sp.inner_text()).strip()
                    p = parse_price(txt)
                    if p > 0:
                        price = p
                        break

                img_el = await card.query_selector("img")
                img = (await img_el.get_attribute("src") or "") if img_el else ""
                print(f"  [{count+1}] {name[:50]} | {price} | {img[:50]}")
                count += 1
            except Exception as e:
                print(f"  ERR: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug())
