import unittest
if __name__ != "__main__":
    raise unittest.SkipTest("manual live-site diagnostic")

import asyncio, sys, io
from playwright.async_api import async_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36'
ANTI_BOT = "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});window.chrome={runtime:{}};"

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=UA)
        await ctx.add_init_script(ANTI_BOT)
        pg = await ctx.new_page()
        
        url = "https://www.jib.co.th/web/product/product_list/2/43"
        print(f"Loading {url}...")
        await pg.goto(url, timeout=30000, wait_until="domcontentloaded")
        await pg.wait_for_timeout(5000)
        
        await pg.screenshot(path="jib_cpu.png")
        print(f"Saved screenshot. Title: {await pg.title()}")
        print(f"Final URL: {pg.url}")
        
        cards = await pg.query_selector_all("div.divboxpro")
        print(f"Product cards found: {len(cards)}")
        
        # Check standard pagination class or links
        pagination = await pg.query_selector_all(".pagination li")
        print(f"Pagination items found: {len(pagination)}")
        for p in pagination:
            print(f"  Inner HTML: {await p.inner_html()}")
            
        await browser.close()

asyncio.run(main())
