import asyncio
from playwright.async_api import async_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=UA)
        page = await ctx.new_page()
        
        # Test Advice
        print("Testing Advice...")
        for url in [
            "https://www.advice.co.th/product/computer-set",
            "https://www.advice.co.th/product/desktop-computer",
            "https://www.advice.co.th/product/diy"
        ]:
            try:
                await page.goto(url, timeout=20000, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)
                cards = await page.evaluate("() => document.querySelectorAll('.product-item, .box-product, div[class*=\"product\"]').length")
                print(f"  Advice {url} -> cards: {cards}")
            except Exception as e:
                print(f"  Advice {url} -> error: {e}")
                
        # Test JIB
        print("Testing JIB...")
        for url in [
            "https://www.jib.co.th/web/product/product_list/2/44",
            "https://www.jib.co.th/web/product/product_list/1/2",
            "https://www.jib.co.th/web/product/product_list/3/2988"
        ]:
            try:
                await page.goto(url, timeout=20000, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)
                cards = await page.evaluate("() => document.querySelectorAll('.product_list_item, div[class*=\"product\"]').length")
                print(f"  JIB {url} -> cards: {cards}")
            except Exception as e:
                print(f"  JIB {url} -> error: {e}")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
