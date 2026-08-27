# -*- coding: utf-8 -*-
import asyncio
import sys
import io
from playwright.async_api import async_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

async def test_advice_image():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=UA)
        page = await ctx.new_page()
        
        # Check product detail by code or search
        # Advice detail URL format: https://www.advice.co.th/product/mouse/mouse-wired/mouse-logitech-m100r-black
        # Or let's see if Advice has a product detail API by code, e.g. api/v1.0.0/product/detail or product/get
        await page.goto("https://www.advice.co.th/search?keyword=A0052566", timeout=30000)
        await page.wait_for_timeout(4000)
        
        # Check all img tags and links on search page
        imgs = await page.query_selector_all("img")
        for img in imgs:
            src = await img.get_attribute("src") or ""
            if "advice" in src or "product" in src or "A0052566" in src:
                print("Image src found:", src)
                
        links = await page.query_selector_all("a[href*='product']")
        for a in links:
            href = await a.get_attribute("href") or ""
            print("Product link found:", href)
            
        await browser.close()

asyncio.run(test_advice_image())
