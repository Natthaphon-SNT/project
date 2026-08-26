import asyncio
from playwright.async_api import async_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=UA)
        page = await ctx.new_page()
        
        # Test campaign / category URLs
        test_urls = [
            "https://ihavecpu.com/campaign/1023",
            "https://ihavecpu.com/category/promotion",
            "https://ihavecpu.com/campaign/1024",
            "https://ihavecpu.com/promotion",
        ]
        for url in test_urls:
            await page.goto(url, timeout=25000, wait_until="networkidle")
            await page.wait_for_timeout(2000)
            res = await page.evaluate("""() => {
                const el = document.getElementById('__NEXT_DATA__');
                if (!el) return { title: document.title, url: window.location.href, count: 0 };
                const d = JSON.parse(el.textContent);
                const products = d?.props?.pageProps?.products || d?.props?.pageProps?.product || [];
                return {
                    title: document.title,
                    url: window.location.href,
                    prodCount: Array.isArray(products) ? products.length : (products ? 1 : 0),
                    pagePropsKeys: Object.keys(d?.props?.pageProps || {})
                };
            }""")
            print(f"{url} -> {res}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
