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
        
        url = "https://www.jib.co.th/web/product/product_list/3/2988"
        print(f"Loading {url}...")
        await pg.goto(url, timeout=40000, wait_until="networkidle")
        await pg.wait_for_timeout(3000)
        
        initial_count = len(await pg.query_selector_all("span.promo_name"))
        print(f"Initial count: {initial_count}")
        
        # Scroll down 5 times
        for i in range(1, 6):
            print(f"Scrolling {i}...")
            await pg.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await pg.wait_for_timeout(3000)
            
        final_count = len(await pg.query_selector_all("span.promo_name"))
        print(f"Final count after scrolling: {final_count}")
        
        await browser.close()

asyncio.run(main())
