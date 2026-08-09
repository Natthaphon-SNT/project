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
        
        # Go to graphic-card
        url = "https://www.ihavecpu.com/category/graphic-card"
        print(f"Loading {url}...")
        await pg.goto(url, timeout=30000, wait_until="networkidle")
        await pg.wait_for_timeout(3000)
        
        print("Checking pagination elements...")
        # Check standard pagination class or links
        pagination = await pg.query_selector_all("a[href*='page=']")
        print(f"Found {len(pagination)} links containing 'page='")
        for p in pagination[:10]:
            print(f"  Href: {await p.get_attribute('href')} | Text: {await p.inner_text()}")
            
        # Check selector .pagination or similar
        for selector in [".pagination", "ul.pagination", ".page-link", ".page-item", ".next"]:
            els = await pg.query_selector_all(selector)
            if els:
                print(f"Found selector '{selector}' count: {len(els)}")
                
        await browser.close()

asyncio.run(main())
