import asyncio
from playwright.async_api import async_playwright
import re

async def test_scrape():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        url = "https://www.advice.co.th/search?keyword=ryzen+5+7600"
        print(f"Fetching {url}")
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        
        html = await page.content()
        with open("advice_html.txt", "w", encoding="utf-8") as f:
            f.write(html)
            
        selectors = ['.product-grid .price-normal', '.product-grid .price', '.product-list .price', '.cart-price', '.price_total', '.product-price', '.price']
        for sel in selectors:
            elements = await page.query_selector_all(sel)
            for el in elements[:5]:
                text = await el.inner_text()
                print(f"Sel '{sel}': {text}")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_scrape())
