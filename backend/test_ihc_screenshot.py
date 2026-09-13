import unittest
if __name__ != "__main__":
    raise unittest.SkipTest("manual live-site diagnostic")

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
        
        print("Going to VGA category...")
        await pg.goto("https://www.ihavecpu.com/category/vga", timeout=30000, wait_until="networkidle")
        await pg.wait_for_timeout(5000)
        
        await pg.screenshot(path="ihc_gpu.png")
        print("Screenshot saved to ihc_gpu.png")
        
        links = await pg.query_selector_all("a[href*='/product/']")
        print(f"Links found: {len(links)}")
        
        await browser.close()

asyncio.run(main())
