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
        
        # Page 1
        await pg.goto("https://www.ihavecpu.com/category/graphic-card", timeout=30000, wait_until="networkidle")
        await pg.wait_for_timeout(3000)
        p1 = [await el.inner_text() for el in await pg.query_selector_all("a[href*='/product/'] h3")]
        
        # Page 2
        await pg.goto("https://www.ihavecpu.com/category/graphic-card?page=2", timeout=30000, wait_until="networkidle")
        await pg.wait_for_timeout(3000)
        p2 = [await el.inner_text() for el in await pg.query_selector_all("a[href*='/product/'] h3")]
        
        print(f"Page 1 items count: {len(p1)}")
        print(f"Page 2 items count: {len(p2)}")
        overlap = set(p1).intersection(set(p2))
        print(f"Overlap: {len(overlap)}")
        if len(p2) > 0 and len(overlap) < len(p1):
            print("SUCCESS: ?page=2 URL format is working on IHC!")
        else:
            print("WARNING: ?page=2 did not load different items. We might need to click the page button.")
            
        await browser.close()

asyncio.run(main())
