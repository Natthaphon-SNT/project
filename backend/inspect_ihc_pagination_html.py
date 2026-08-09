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
        
        await pg.goto("https://www.ihavecpu.com/category/graphic-card", timeout=30000, wait_until="networkidle")
        await pg.wait_for_timeout(3000)
        
        el = await pg.query_selector(".pagination")
        if el:
            print("Pagination Inner HTML:")
            print(await el.inner_html())
            
        await browser.close()

asyncio.run(main())
