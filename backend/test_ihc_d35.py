# -*- coding: utf-8 -*-
import unittest
if __name__ != "__main__":
    raise unittest.SkipTest("manual live-site diagnostic")
import asyncio
import sys
import io
from playwright.async_api import async_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

URL = "https://ihavecpu.com/product/49489/ram-(%E0%B9%81%E0%B8%A3%E0%B8%A1)-adata-xpg-gammix-x-d35-32gb-(16x2)-ddr4-3200mhz-black-(ax4u320016g16a-dtbkd35)-(lt)"

async def check_ihc_page():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=UA)
        page = await ctx.new_page()
        
        await page.goto(URL, timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(4000)
        
        # 1. Check og:image
        og_img = ""
        m = await page.query_selector('meta[property="og:image"]')
        if m:
            og_img = await m.get_attribute("content")
        print("og:image:", og_img)
        
        # 2. Check main product images
        imgs = await page.query_selector_all("img")
        print("Total img tags:", len(imgs))
        for img in imgs:
            src = await img.get_attribute("src") or ""
            dsrc = await img.get_attribute("data-src") or ""
            dlazy = await img.get_attribute("data-lazy") or ""
            cls = await img.get_attribute("class") or ""
            if "product" in src or "product" in dsrc or "amazonaws" in src or "amazonaws" in dsrc:
                print(f"Img tag: src={src}, data-src={dsrc}, class={cls}")
                
        # 3. Check spec / description
        desc = ""
        for sel in ["div.product-description", "div.description", "#product-description", "[class*='spec']"]:
            el = await page.query_selector(sel)
            if el:
                desc = (await el.inner_text()).strip()
                if desc and len(desc) > 30:
                    break
        print("\nDescription:\n", desc[:300])
        
        await browser.close()

asyncio.run(check_ihc_page())
