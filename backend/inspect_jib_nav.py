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
        
        await pg.goto("https://www.jib.co.th/web/product/product_list/3/2988", timeout=30000, wait_until="networkidle")
        
        # Look for pagination elements
        print("Searching pagination links...")
        pages = await pg.query_selector_all("a[href*='product_list']")
        print(f"Found {len(pages)} links with product_list in href.")
        for p in pages[:10]:
            href = await p.get_attribute("href")
            text = await p.inner_text()
            print(f"  Text: '{text.strip()}' -> Href: '{href}'")
            
        print("\nSearching other pagination selectors:")
        for sel in ["ul.pagination", ".pagination", ".page", ".page_nav"]:
            el = await pg.query_selector(sel)
            if el:
                print(f"Found selector '{sel}':")
                print(await el.inner_html())
                
        await browser.close()

asyncio.run(main())
