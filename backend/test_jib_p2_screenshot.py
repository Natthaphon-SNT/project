import asyncio, sys, io
from playwright.async_api import async_playwright

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36'
ANTI_BOT = "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});window.chrome={runtime:{}};"

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=UA)
        await ctx.add_init_script(ANTI_BOT)
        pg = await ctx.new_page()
        
        url = "https://www.jib.co.th/web/product/product_list/3/2988/100"
        print(f"Loading {url}...")
        try:
            await pg.goto(url, timeout=40000, wait_until="domcontentloaded")
            await pg.wait_for_timeout(5000)
            await pg.screenshot(path="jib_p2.png")
            print("Screenshot saved to jib_p2.png")
            cards = await pg.query_selector_all("div.divboxpro")
            print(f"Cards found on page 2: {len(cards)}")
        except Exception as e:
            print(f"Error: {e}")
            
        await browser.close()

asyncio.run(main())
