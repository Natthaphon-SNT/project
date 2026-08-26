import asyncio, json
from playwright.async_api import async_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=UA)
        page = await ctx.new_page()
        await page.goto("https://ihavecpu.com", timeout=30000, wait_until="networkidle")
        
        data = await page.evaluate("""() => {
            const el = document.getElementById('__NEXT_DATA__');
            if (!el) return null;
            const d = JSON.parse(el.textContent);
            return {
                categorySetComputer: d?.props?.pageProps?.categorySetComputer || null,
                bannerpopupdiy: d?.props?.pageProps?.bannerpopupdiy || null
            };
        }""")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
