# -*- coding: utf-8 -*-
import unittest
if __name__ != "__main__":
    raise unittest.SkipTest("manual live-site diagnostic")
import asyncio
import json
import sys
import io
from playwright.async_api import async_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

async def test_ihc_next():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=UA)
        page = await ctx.new_page()
        
        await page.goto("https://ihavecpu.com/category/promotion-comset", timeout=30000)
        await page.wait_for_timeout(3000)
        
        data = await page.evaluate("""
        () => {
            const el = document.getElementById('__NEXT_DATA__');
            if (!el) return null;
            const d = JSON.parse(el.textContent);
            const prodObj = d?.props?.pageProps?.product;
            const dataList = prodObj?.data || [];
            if (dataList.length > 0) return dataList[0];
            return null;
        }
        """)
        
        print("Sample iHaveCPU Next product:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # Also check all <a> tags on page to see what href they have!
        links = await page.query_selector_all("a[href*='/product/']")
        for a in links[:5]:
            href = await a.get_attribute("href")
            print("Link on page:", href)
            
        await browser.close()

asyncio.run(test_ihc_next())
