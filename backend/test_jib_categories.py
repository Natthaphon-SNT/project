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
        
        # Test CPU category (2998)
        print("Fetching JIB CPU category...")
        await pg.goto("https://www.jib.co.th/web/product/product_list/3/2998", timeout=30000, wait_until="networkidle")
        cpu_names = [await el.inner_text() for el in await pg.query_selector_all("span.promo_name")]
        
        # Test GPU category (3004)
        print("Fetching JIB GPU category...")
        await pg.goto("https://www.jib.co.th/web/product/product_list/3/3004", timeout=30000, wait_until="networkidle")
        gpu_names = [await el.inner_text() for el in await pg.query_selector_all("span.promo_name")]
        
        print(f"JIB CPU items count: {len(cpu_names)}")
        print(f"JIB GPU items count: {len(gpu_names)}")
        if cpu_names:
            print("First 3 CPUs:")
            for x in cpu_names[:3]: print("  ", x.strip())
        if gpu_names:
            print("First 3 GPUs:")
            for x in gpu_names[:3]: print("  ", x.strip())
            
        await browser.close()

asyncio.run(main())
