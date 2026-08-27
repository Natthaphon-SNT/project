# -*- coding: utf-8 -*-
import asyncio, sys, io
from playwright.async_api import async_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
URL = "https://ihavecpu.com/product/48823/case-(%E0%B9%80%E0%B8%84%E0%B8%AA)-corsair-warthog-rs-performance-(green)(e-atx)(cc-9011352-ww)-(2y)"

async def check_warthog():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=UA)
        page = await ctx.new_page()
        
        await page.goto(URL, timeout=30000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        
        # Check all price elements or text
        content = await page.content()
        
        spans = await page.query_selector_all("span, div, p, h1, h2, h3")
        prices = []
        for s in spans:
            t = (await s.inner_text()).strip()
            if "฿" in t or "THB" in t or (t.replace(',', '').isdigit() and len(t) >= 4):
                prices.append(t)
        print("Prices found on page:")
        for p in set(prices):
            print("  ", p)
            
        await browser.close()

asyncio.run(check_warthog())
