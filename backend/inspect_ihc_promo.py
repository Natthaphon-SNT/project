import asyncio, json
from playwright.async_api import async_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=UA)
        page = await ctx.new_page()
        
        await page.goto("https://ihavecpu.com/category/promotion", timeout=25000, wait_until="networkidle")
        data = await page.evaluate("""() => {
            const el = document.getElementById('__NEXT_DATA__');
            if (!el) return null;
            const d = JSON.parse(el.textContent);
            const prods = d?.props?.pageProps?.products || [];
            return prods.slice(0, 3).map(p => ({
                id: p.product_id,
                name: p.name_th || p.name_gb,
                price: p.market_price || p.sell_price,
                img: p.image_url || p.img_url || (p.images && p.images[0] ? p.images[0].url : '')
            }));
        }""")
        print("Category promotion sample products:")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        
        # Also check pagination on /category/promotion
        await page.goto("https://ihavecpu.com/category/promotion?page=2", timeout=25000, wait_until="networkidle")
        data2 = await page.evaluate("""() => {
            const el = document.getElementById('__NEXT_DATA__');
            if (!el) return null;
            const d = JSON.parse(el.textContent);
            const prods = d?.props?.pageProps?.products || [];
            return { total: prods.length, first: prods[0]?.name_th };
        }""")
        print("Page 2:", data2)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
