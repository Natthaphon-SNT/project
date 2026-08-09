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

        # JIB Search API test
        print('=== JIB Search API ===')
        searches = [
            ('Mainboard', 'https://www.jib.co.th/web/product/search_product/0?q=mainboard'),
            ('GPU',       'https://www.jib.co.th/web/product/search_product/0?q=vga+การ์ดจอ'),
            ('RAM',       'https://www.jib.co.th/web/product/search_product/0?q=ram+memory'),
            ('SSD',       'https://www.jib.co.th/web/product/search_product/0?q=ssd+m.2'),
            ('PSU',       'https://www.jib.co.th/web/product/search_product/0?q=power+supply'),
            ('Case',      'https://www.jib.co.th/web/product/search_product/0?q=computer+case+เคส'),
        ]
        for cat, url in searches:
            await page.goto(url, timeout=25000, wait_until='networkidle')
            await page.wait_for_timeout(2000)
            cards = await page.query_selector_all('div.divboxpro')
            print(f'{cat}: cards={len(cards)} | url: ...{url[-50:]}')
            if cards:
                n_el = await cards[0].query_selector('span.promo_name')
                p_el = await cards[0].query_selector('p.price_total')
                i_el = await cards[0].query_selector('img')
                n = (await n_el.inner_text()).strip() if n_el else ''
                p = parse_price((await p_el.inner_text()).strip() if p_el else '')
                i = await i_el.get_attribute('src') if i_el else ''
                print(f'  -> {n[:45]!r} | {p}บ | img={bool(i)}')

        # ADVICE - check price with scroll
        print()
        print('=== Advice - price with scroll ===')
        await page.goto('https://www.advice.co.th/product/cpu', timeout=35000, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        await page.evaluate('window.scrollTo(0, 600)')
        await page.wait_for_timeout(3000)
        cards = await page.query_selector_all('div.list-product')
        for card in cards[:3]:
            name_el = await card.query_selector('a.fn-name')
            name = (await name_el.inner_text()).strip() if name_el else ''
            price_el = await card.query_selector('span.item-price-sale')
            price = parse_price((await price_el.inner_text()).strip() if price_el else '')
            img_el = await card.query_selector('div.item-img img')
            img = await img_el.get_attribute('src') if img_el else ''
            print(f'  {name[:40]!r} | {price}บ | img={img[:50]!r}')

        await browser.close()

asyncio.run(main())
