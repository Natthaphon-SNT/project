import asyncio, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.async_api import async_playwright

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36'

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=['--no-sandbox','--disable-blink-features=AutomationControlled'])
        ctx = await browser.new_context(user_agent=UA, viewport={'width':1280,'height':800})
        page = await ctx.new_page()

        print('--- Advice CPU (with fresh context) ---')
        await page.goto('https://www.advice.co.th/product/cpu', timeout=35000, wait_until='domcontentloaded')
        await page.wait_for_timeout(5000)
        title = await page.title()
        print('Title:', title[:60])
        cards = await page.query_selector_all('div.list-product')
        print('Cards:', len(cards))
        if cards:
            name_el = await cards[0].query_selector('a.fn-name')
            name = await name_el.get_attribute('title') if name_el else 'none'
            print('Name:', name)
            price_el = await cards[0].query_selector('span.item-price-sale')
            price = await price_el.inner_text() if price_el else 'none'
            print('Price:', price)
        else:
            body = await page.inner_text('body')
            print('Body preview:', body[:300])

        print()
        print('--- JIB Mainboard ---')
        await page.goto('https://www.jib.co.th/web/product/product_list/1/43', timeout=35000, wait_until='networkidle')
        await page.wait_for_timeout(4000)
        title2 = await page.title()
        print('Title:', title2[:60])
        cards2 = await page.query_selector_all('div.divboxpro')
        print('Cards:', len(cards2))
        if not cards2:
            body2 = await page.inner_text('body')
            print('Body:', body2[:400])

        await browser.close()

asyncio.run(main())
