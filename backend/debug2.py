import asyncio, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from playwright.async_api import async_playwright
import re

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36'

def parse_price(text):
    if not text: return 0
    text = text.replace(',','').replace('\u0e3f','').replace('THB','').strip()
    m = re.search(r'\d+(?:\.\d+)?', text)
    if not m: return 0
    n = int(float(m.group(0)))
    return n if 200 <= n <= 200000 else 0

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=['--no-sandbox'])
        ctx = await browser.new_context(user_agent=UA, viewport={'width':1280,'height':800})
        await ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
        page = await ctx.new_page()

        # Advice - inspect all selectors in card
        print('=== Advice CPU selectors ===')
        await page.goto('https://www.advice.co.th/product/cpu', timeout=35000, wait_until='domcontentloaded')
        await page.wait_for_timeout(5000)
        cards = await page.query_selector_all('div.list-product')
        print(f'Cards: {len(cards)}')
        if cards:
            card = cards[0]
            # Try different name selectors
            for sel in ['a.fn-name', 'p.fn-name', '.product-name', 'h3', '.fn-name', 'a[title]', '.item-name']:
                el = await card.query_selector(sel)
                if el:
                    txt = await el.inner_text()
                    ttl = await el.get_attribute('title')
                    print(f'  [{sel}] text={txt[:40]!r} title={ttl!r}')
            # Try price
            for psel in ['span.item-price-sale', '.price', 'strong', 'span[class*=price]', '.price-sale']:
                pel = await card.query_selector(psel)
                if pel:
                    ptxt = await pel.inner_text()
                    print(f'  price[{psel}]={ptxt!r}')
            # dump card inner html
            html = await card.inner_html()
            print('HTML:', html[:800])

        print()
        print('=== JIB - find correct Mainboard URL ===')
        # Try the correct mainboard URL
        for url in [
            'https://www.jib.co.th/web/product/product_list/1/43',
            'https://www.jib.co.th/web/product/product_list/3/2988',
            'https://www.jib.co.th/web/index.php?cid=43',
        ]:
            await page.goto(url, timeout=30000, wait_until='networkidle')
            await page.wait_for_timeout(3000)
            title = await page.title()
            cards = await page.query_selector_all('div.divboxpro')
            print(f'URL={url}')
            print(f'  Title={title[:50]} | Cards={len(cards)}')
            if cards: break

        await browser.close()

asyncio.run(main())
