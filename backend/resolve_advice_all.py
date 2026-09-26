# -*- coding: utf-8 -*-
"""
Resolve all Advice products with search URLs or missing images by querying Advice API directly
"""
import asyncio
import sqlite3
import sys
import io
import re
from playwright.async_api import async_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB_PATH = "shop.db"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

ADVICE_FETCH_SINGLE_JS = """
async (kw) => {
    const getCookie = n => (document.cookie.split('; ').find(c => c.startsWith(n+'='))||'').split('=')[1];
    const token = decodeURIComponent(getCookie('user_token') || '');
    const r = await fetch('https://prodbackadvice.advice.in.th/api/v1.0.0/product/get', {
        method: 'POST', credentials: 'include',
        headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
        body: JSON.stringify({category:"search",category_sub:"",product:"",keyword:kw,
            take:6,skip:0,refSearch:"",page:"product",arr_filter_brand:[],
            arr_filter_ict:[],arr_filter_price_ict:[],arr_filter_cate:[],addView:false,
            group_end:false})
    });
    const j = await r.json();
    const out = [];
    const prodGroups = (j.data||{}).product || [];
    for (const g of prodGroups) {
        for (const p of (g.product||[])) {
            const rawUrl = p.product_url || '';
            const fullUrl = rawUrl ? (rawUrl.startsWith('http') ? rawUrl : 'https://www.advice.co.th/product/' + rawUrl) : '';
            out.push({
                code: p.code || '',
                name: (p.product || p.name || '').trim(),
                price: p.price_sale_true || p.price_srp || p.price || 0,
                url: fullUrl,
                img: p.pic_url || (p.code ? `https://img.advice.co.th/images_nas/pic_product4/${p.code}/${p.code}_1.jpg` : ''),
                spec: p.spec || ''
            });
        }
    }
    return out;
}
"""

def clean_kw(name: str) -> str:
    # Remove Thai
    n = re.sub(r'[\u0E00-\u0E7F]+', ' ', name)
    # Remove brackets
    n = re.sub(r'\(.*?\)|\[.*?\]', ' ', n)
    n = re.sub(r'[\-_/+,:]+', ' ', n)
    words = [w for w in n.split() if w]
    # Take first 4-5 key words
    return " ".join(words[:5])

async def resolve_all_advice_products():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Find all products that have Advice price > 0 and either search URL or missing image
    rows = cur.execute("""
        SELECT product_id, p_name, img_url, url_advice, p_description, desc_advice
        FROM products
        WHERE price_advice > 0 AND (url_advice LIKE '%search?keyword%' OR url_advice = '' OR img_url = '' OR img_url IS NULL)
    """).fetchall()

    print(f"Products to resolve: {len(rows)}")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=UA)
        page = await ctx.new_page()

        await page.goto("https://www.advice.co.th/", timeout=30000)
        await page.wait_for_timeout(3000)

        resolved_count = 0

        for i, (pid, name, img, url, desc, desc_adv) in enumerate(rows):
            kw = clean_kw(name)
            if not kw:
                kw = name[:30]

            try:
                items = await page.evaluate(ADVICE_FETCH_SINGLE_JS, kw)
                if not items and len(kw.split()) > 2:
                    # try shorter kw
                    shorter = " ".join(kw.split()[:2])
                    items = await page.evaluate(ADVICE_FETCH_SINGLE_JS, shorter)

                if items:
                    # Pick best matching item
                    best_item = items[0]
                    # Check if exact or close match
                    for it in items:
                        if it['name'].upper() == name.upper():
                            best_item = it
                            break

                    updates = []
                    params = []

                    if best_item['img']:
                        updates.append("img_url = ?")
                        params.append(best_item['img'])

                    if best_item['url']:
                        updates.append("url_advice = ?")
                        params.append(best_item['url'])

                    if best_item['spec']:
                        if not desc:
                            updates.append("p_description = ?")
                            params.append(best_item['spec'])
                        updates.append("desc_advice = ?")
                        params.append(best_item['spec'])

                    if updates:
                        params.append(pid)
                        sql = f"UPDATE products SET {', '.join(updates)} WHERE product_id = ?"
                        cur.execute(sql, params)
                        resolved_count += 1
                        print(f"[{i+1}/{len(rows)}] Resolved [{name[:35]}...]:\n    URL: {best_item['url'][:70]}...\n    IMG: {best_item['img'][:70]}...")

                if (i + 1) % 10 == 0:
                    conn.commit()
            except Exception as e:
                print(f"[{i+1}/{len(rows)}] Error on {name[:30]}: {e}")

        conn.commit()
        await browser.close()

    print(f"\nSuccessfully resolved {resolved_count} products!")

    # Check KB-714 specifically
    rows_check = cur.execute("SELECT product_id, p_name, img_url, url_advice, p_description FROM products WHERE p_name LIKE '%KB-714%'").fetchall()
    print("\n--- KB-714 after resolve ---")
    for r in rows_check:
        print(f"ID: {r[0]}")
        print(f"Name: {r[1]}")
        print(f"Img: {r[2]}")
        print(f"URL: {r[3]}")
        print(f"Desc: {r[4]}")
        print("-" * 40)

    conn.close()

if __name__ == "__main__":
    asyncio.run(resolve_all_advice_products())
