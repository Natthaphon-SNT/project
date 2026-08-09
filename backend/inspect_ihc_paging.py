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
        
        # GPU (vga)
        await pg.goto("https://www.ihavecpu.com/category/vga", timeout=30000, wait_until="networkidle")
        p1 = [await el.inner_text() for el in await pg.query_selector_all("a[href*='/product/'] h3")]
        
        await pg.goto("https://www.ihavecpu.com/category/vga?page=2", timeout=30000, wait_until="networkidle")
        p2 = [await el.inner_text() for el in await pg.query_selector_all("a[href*='/product/'] h3")]
        
        print(f"IHC GPU Page 1 count: {len(p1)}")
        print(f"IHC GPU Page 2 count: {len(p2)}")
        
        overlap = set(p1).intersection(set(p2))
        print(f"Overlap: {len(overlap)}")
        
        # Display pagination elements if any
        pages = await pg.query_selector_all("a[href*='page=']")
        print(f"Pagination page= links: {len(pages)}")
        for p in pages[:5]:
            print(f"  Text: {await p.inner_text()} -> {await p.get_attribute('href')}")
            
        await browser.close()

asyncio.run(main())
