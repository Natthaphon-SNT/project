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
        
        # Go to VGA
        url = "https://www.ihavecpu.com/category/vga"
        print(f"Navigating to {url}...")
        await pg.goto(url, timeout=30000, wait_until="networkidle")
        await pg.wait_for_timeout(3000)
        print(f"Final URL: {pg.url}")
        
        # Go to CPU
        url_cpu = "https://www.ihavecpu.com/category/cpu"
        print(f"\nNavigating to {url_cpu}...")
        await pg.goto(url_cpu, timeout=30000, wait_until="networkidle")
        await pg.wait_for_timeout(3000)
        print(f"Final URL: {pg.url}")
        
        await browser.close()

asyncio.run(main())
