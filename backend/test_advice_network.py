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

async def test_advice_network():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=UA)
        page = await ctx.new_page()
        
        # Listen to requests/responses
        async def on_response(response):
            if "product" in response.url or "pic" in response.url or "image" in response.url or "api" in response.url:
                if response.status == 200:
                    ct = response.headers.get("content-type", "")
                    if "image" in ct:
                        print("Image loaded:", response.url)
                    elif "json" in ct and "product" in response.url:
                        try:
                            j = await response.json()
                            print("JSON response from:", response.url)
                            # print first 500 chars
                            print(str(j)[:300])
                        except Exception:
                            pass
                        
        page.on("response", on_response)
        
        await page.goto("https://www.advice.co.th/product/search?keyword=MOUSE+LOGITECH+M100R+BLACK", timeout=30000)
        await page.wait_for_timeout(6000)
        
        # Let's inspect HTML elements
        cards = await page.query_selector_all("[class*='product'], [class*='card'], [class*='item']")
        print("Cards found:", len(cards))
        
        for el in cards[:10]:
            html = await el.inner_html()
            if "M100R" in html or "A0052566" in html:
                print("Card HTML with M100R:\n", html[:1000])
                break
                
        await browser.close()

asyncio.run(test_advice_network())
