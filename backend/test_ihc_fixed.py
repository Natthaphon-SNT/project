"""
Quick test: ทดสอบ fetch_ihc_detail ที่แก้ใหม่กับ URL จริง
"""
import asyncio, sys
sys.path.insert(0, '.')
from fetch_descriptions import fetch_ihc_detail
from playwright.async_api import async_playwright

URL = "https://ihavecpu.com/product/46353/mouse-(%E0%B9%80%E0%B8%A1%E0%B8%B2%E0%B8%AA%E0%B9%8C)-asus-rog-keris-ii-origin-kjp-wireless-(white)-(p727)-(2y)"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
ANTI_BOT = ("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            "window.chrome={runtime:{}};")

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
        ctx = await browser.new_context(user_agent=UA, viewport={"width": 1280, "height": 800})
        await ctx.add_init_script(ANTI_BOT)
        page = await ctx.new_page()

        print(f"Testing URL: {URL[:60]}...")
        desc, img = await fetch_ihc_detail(page, URL)

        print(f"\n{'='*60}")
        print(f"DESC ({len(desc)} chars):")
        print(desc if desc else "(empty)")
        print(f"\nIMG: {img if img else '(empty)'}")
        print('='*60)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
