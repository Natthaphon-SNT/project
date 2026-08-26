"""
ค้นหา URL ที่ถูกต้องสำหรับ PC Set บน ihavecpu
"""
import asyncio
from playwright.async_api import async_playwright

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

TEST_URLS = [
    "https://ihavecpu.com/category/computer",
    "https://ihavecpu.com/category/pc-bundle",
    "https://ihavecpu.com/category/set",
    "https://ihavecpu.com/category/desktop",
    "https://ihavecpu.com/category/computer-set",
]

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=UA, viewport={"width": 1280, "height": 800})
        page = await ctx.new_page()

        # ไปหน้า category หลักก่อนเพื่อดู subcategories
        print("=== Checking ihavecpu.com main nav ===")
        await page.goto("https://ihavecpu.com", timeout=30000, wait_until="networkidle")
        await page.wait_for_timeout(3000)

        # ดึง __NEXT_DATA__ เพื่อหา category list
        cats = await page.evaluate("""
            () => {
                const el = document.getElementById('__NEXT_DATA__');
                if (!el) return null;
                try {
                    const d = JSON.parse(el.textContent);
                    // หา categories ใน props
                    const cats = d?.props?.pageProps?.categories || 
                                 d?.props?.pageProps?.menuCategories ||
                                 d?.props?.pageProps?.navCategories || null;
                    return cats ? JSON.stringify(cats).substring(0, 3000) : 
                                  JSON.stringify(Object.keys(d?.props?.pageProps || {}));
                } catch(e) { return 'error: ' + e.message; }
            }
        """)
        print(f"Categories from __NEXT_DATA__: {cats}")

        # ลองดูจาก nav links ใน HTML
        nav_links = await page.evaluate("""
            () => {
                const links = document.querySelectorAll('nav a, header a, [class*="nav"] a, [class*="menu"] a');
                return Array.from(links)
                    .map(a => ({ text: a.innerText.trim(), href: a.href }))
                    .filter(l => l.text && l.href.includes('ihavecpu') && l.href.includes('category'))
                    .slice(0, 30);
            }
        """)
        print("\n=== Nav Category Links ===")
        for l in nav_links:
            print(f"  {l['text']}: {l['href']}")

        # ทดสอบแต่ละ URL
        print("\n=== Testing candidate URLs ===")
        for url in TEST_URLS:
            try:
                await page.goto(url, timeout=15000, wait_until="networkidle")
                await page.wait_for_timeout(2000)
                result = await page.evaluate("""
                    () => {
                        const el = document.getElementById('__NEXT_DATA__');
                        if (!el) return 'no __NEXT_DATA__';
                        const d = JSON.parse(el.textContent);
                        const products = d?.props?.pageProps?.products || [];
                        return `products: ${products.length}, url: ${window.location.href}`;
                    }
                """)
                print(f"  {url}: {result}")
            except Exception as e:
                print(f"  {url}: ERROR - {e}")

        await browser.close()

asyncio.run(main())
