"""
ทดสอบ scraper ทีละร้าน เพียง 1 page - รัน: python test_scraper.py
"""
import asyncio
from scraper import scrape_ihavecpu, scrape_advice, scrape_jib
from playwright.async_api import async_playwright

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"

async def test():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        ctx = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=UA,
        )
        await ctx.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = await ctx.new_page()

        # ── iHaveCPU ──────────────────────────────
        print("=== iHaveCPU (CPU, 1 page) ===")
        items = await scrape_ihavecpu(page, "https://www.ihavecpu.com/category/cpu", "CPU", 1)
        for p in items[:3]:
            name = p["p_name"][:50]
            price = p["p_price"]
            img = p["img_url"][:60]
            print(f"  {name} | {price} | {img}")
        print(f"  Total: {len(items)}")

        # ── Advice ────────────────────────────────
        print()
        print("=== Advice (CPU, 1 page) ===")
        items2 = await scrape_advice(page, "https://www.advice.co.th/product/cpu", "CPU", 1)
        for p in items2[:3]:
            name = p["p_name"][:50]
            price = p["p_price"]
            img = p["img_url"][:60]
            print(f"  {name} | {price} | {img}")
        print(f"  Total: {len(items2)}")

        # ── JIB ───────────────────────────────────
        print()
        print("=== JIB (CPU, 1 page) ===")
        items3 = await scrape_jib(page, "https://www.jib.co.th/web/product/product_list/1/42", "CPU", 1)
        for p in items3[:3]:
            name = p["p_name"][:50]
            price = p["p_price"]
            img = p["img_url"][:60]
            print(f"  {name} | {price} | {img}")
        print(f"  Total: {len(items3)}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test())
