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
        
        print("Loading home page...")
        await pg.goto("https://ihavecpu.com/", timeout=30000, wait_until="networkidle")
        await pg.wait_for_timeout(3000)
        
        # Get all links containing "/category/"
        links = await pg.query_selector_all("a[href*='/category/']")
        print(f"Found {len(links)} category links:")
        seen = set()
        for le in links:
            href = await le.get_attribute("href")
            text = (await le.inner_text()).strip()
            if href and href not in seen:
                seen.add(href)
                print(f"  {text} -> {href}")
                
        await browser.close()

asyncio.run(main())
