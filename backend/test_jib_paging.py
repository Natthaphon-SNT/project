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
        print("Fetching Page 1...")
        await pg.goto("https://www.jib.co.th/web/product/product_list/3/2988", timeout=30000, wait_until="networkidle")
        p1_names = [await el.inner_text() for el in await pg.query_selector_all("span.promo_name")]
        
        # Page 2
        print("Fetching Page 2...")
        await pg.goto("https://www.jib.co.th/web/product/product_list/3/2988/2", timeout=30000, wait_until="networkidle")
        p2_names = [await el.inner_text() for el in await pg.query_selector_all("span.promo_name")]
        
        print(f"Page 1 items count: {len(p1_names)}")
        print(f"Page 2 items count: {len(p2_names)}")
        if p1_names and p2_names:
            overlap = set(p1_names).intersection(set(p2_names))
            print(f"Overlap items: {len(overlap)}")
            if len(overlap) == len(p1_names):
                print("WARNING: Pages are identical! Paging URL is incorrect.")
            else:
                print("SUCCESS: Pages are different! Pagination is working.")
        
        await browser.close()

asyncio.run(main())
