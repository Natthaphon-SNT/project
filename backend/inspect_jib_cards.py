import asyncio
from playwright.async_api import async_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=UA)
        page = await ctx.new_page()
        
        url = "https://www.jib.co.th/web/product/product_list/3/2988"
        await page.goto(url, timeout=25000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        
        cards_info = await page.evaluate("""() => {
            const boxes = document.querySelectorAll('div[class*="product"]');
            const samples = Array.from(boxes).slice(0, 5).map(b => ({
                class: b.className,
                text: b.innerText.substring(0, 100).replace(/\\n/g, ' ')
            }));
            return samples;
        }""")
        print(cards_info)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
