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

async def test_ihc_dom():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=UA)
        page = await ctx.new_page()
        
        await page.goto("https://ihavecpu.com/category/promotion-comset", timeout=30000)
        await page.wait_for_timeout(6000)
        
        links = await page.query_selector_all("a[href*='/product/']")
        print("Product links found:", len(links))
        for a in links[:10]:
            href = await a.get_attribute("href") or ""
            text = (await a.inner_text()).strip().replace('\n', ' ')
            print(f"HREF: {href}")
            print(f"TEXT: {text[:60]}")
            print("-" * 30)
            
        await browser.close()

asyncio.run(test_ihc_dom())
