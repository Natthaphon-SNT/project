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

        # === ADVICE - full card inspect ===
        print('=== ADVICE CPU - full selectors ===')
        await page.goto('https://www.advice.co.th/product/cpu', timeout=35000, wait_until='domcontentloaded')
        await page.wait_for_timeout(5000)
        cards = await page.query_selector_all('div.list-product')
        print(f'Cards: {len(cards)}')
        for card in cards[:2]:
            # Name
            name_el = await card.query_selector('a.fn-name')
            name = (await name_el.inner_text()).strip() if name_el else ''
            # Price
            price_el = await card.query_selector('span.item-price-sale')
            price = parse_price((await price_el.inner_text()).strip() if price_el else '')
            # Image
            img_el = await card.query_selector('div.item-img img')
            img = await img_el.get_attribute('src') if img_el else ''
            if not img:
                img_el2 = await card.query_selector('img')
                img = await img_el2.get_attribute('src') if img_el2 else ''
            print(f'  Name={name[:50]!r}')
            print(f'  Price={price}')
            print(f'  Img={img[:80]!r}')
            print()

        # === JIB - discover correct category IDs ===
        print('=== JIB - category URLs ===')
        jib_urls = [
            ('CPU',           'https://www.jib.co.th/web/product/product_list/1/42'),
            ('Mainboard',     'https://www.jib.co.th/web/product/product_list/1/43'),
            ('Mainboard2',    'https://www.jib.co.th/web/product/product_list/3/2988'),
            ('GPU',           'https://www.jib.co.th/web/product/product_list/1/44'),
            ('RAM',           'https://www.jib.co.th/web/product/product_list/1/45'),
            ('SSD',           'https://www.jib.co.th/web/product/product_list/1/46'),
            ('PSU',           'https://www.jib.co.th/web/product/product_list/1/50'),
            ('Case',          'https://www.jib.co.th/web/product/product_list/1/51'),
            ('LiquidCooler',  'https://www.jib.co.th/web/product/product_list/1/48'),
            ('AirCooler',     'https://www.jib.co.th/web/product/product_list/1/47'),
        ]
        for cat, url in jib_urls:
            await page.goto(url, timeout=25000, wait_until='networkidle')
            await page.wait_for_timeout(2000)
            count_el = await page.query_selector('.total-items, .count-item, span[class*=total]')
            cards = await page.query_selector_all('div.divboxpro')
            # check page title for redirect
            actual_url = page.url
            print(f'{cat}: cards={len(cards)} url={actual_url[-40:]!r}')
            if cards:
                n_el = await cards[0].query_selector('span.promo_name')
                p_el = await cards[0].query_selector('p.price_total')
                i_el = await cards[0].query_selector('img')
                n = (await n_el.inner_text()).strip() if n_el else ''
                p = parse_price((await p_el.inner_text()).strip() if p_el else '')
                i = await i_el.get_attribute('src') if i_el else ''
                print(f'  sample: {n[:40]!r} | {p} | {i[:60]!r}')

        await browser.close()

asyncio.run(main())
