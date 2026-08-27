# -*- coding: utf-8 -*-
"""
Fix Advice products in shop.db by fetching real pic_url, product_url, and spec from Advice API
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

ADVICE_SEARCH_KW = [
    "ryzen", "intel core", "mainboard", "vga rtx", "vga radeon",
    "ram ddr4", "ram ddr5", "ssd nvme", "ssd sata", "psu atx", "power supply",
    "case atx", "case matx", "case itx", "liquid cooler", "aio cooler",
    "air cooler", "cpu cooler", "monitor gaming", "monitor ips",
    "mouse gaming", "mouse logitech", "keyboard gaming", "headset gaming",
    "gaming chair", "gaming desk"
]

ADVICE_FETCH_JS = """
async (args) => {
    const getCookie = n => (document.cookie.split('; ').find(c => c.startsWith(n+'='))||'').split('=')[1];
    const token = decodeURIComponent(getCookie('user_token') || '');
    const r = await fetch('https://prodbackadvice.advice.in.th/api/v1.0.0/product/get', {
        method: 'POST', credentials: 'include',
        headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
        body: JSON.stringify({category:"search",category_sub:"",product:"",keyword:args.kw,
            take:24,skip:args.skip,refSearch:"",page:"product",arr_filter_brand:[],
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
    return {status:j.status, items:out};
}
"""

async def fix_advice_data():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Load all products from shop.db
    cur.execute("SELECT product_id, p_name, img_url, url_advice, p_description, desc_advice FROM products")
    db_prods = cur.fetchall()
    
    print(f"Total products in DB: {len(db_prods)}")
    
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=UA)
        page = await ctx.new_page()
        
        await page.goto("https://www.advice.co.th/", timeout=30000)
        await page.wait_for_timeout(3000)
        
        updated_count = 0
        
        for kw in ADVICE_SEARCH_KW:
            for pn in range(3):
                skip = pn * 24
                try:
                    res = await page.evaluate(ADVICE_FETCH_JS, {"kw": kw, "skip": skip})
                    items = res.get("items") or []
                    if not items:
                        break
                    
                    for it in items:
                        name = it["name"]
                        img = it["img"]
                        url = it["url"]
                        spec = it["spec"]
                        
                        if not name:
                            continue
                            
                        # Find matching product in DB
                        # 1. By exact name or close match
                        for pid, db_name, db_img, db_url, db_desc, db_desc_adv in db_prods:
                            if db_name.strip().upper() == name.strip().upper() or name.strip().upper() in db_name.strip().upper() or db_name.strip().upper() in name.strip().upper():
                                # Update fields
                                updates = []
                                params = []
                                
                                if img and (not db_img or "placeholder" in db_img or db_img == ""):
                                    updates.append("img_url = ?")
                                    params.append(img)
                                
                                if url and (not db_url or "search?keyword=" in db_url or db_url == ""):
                                    updates.append("url_advice = ?")
                                    params.append(url)
                                    
                                if spec:
                                    if not db_desc or db_desc == "":
                                        updates.append("p_description = ?")
                                        params.append(spec)
                                    if not db_desc_adv or db_desc_adv == "":
                                        updates.append("desc_advice = ?")
                                        params.append(spec)
                                        
                                if updates:
                                    params.append(pid)
                                    sql = f"UPDATE products SET {', '.join(updates)} WHERE product_id = ?"
                                    cur.execute(sql, params)
                                    updated_count += 1
                                    break
                    conn.commit()
                except Exception as e:
                    print(f"Error on {kw} p{pn}: {e}")
                    break
                    
        await browser.close()
        
    print(f"Updated {updated_count} product fields with Advice data.")
    
    # Check M100R specifically
    rows = cur.execute("SELECT product_id, p_name, img_url, url_advice, p_description FROM products WHERE p_name LIKE '%M100R%'").fetchall()
    print("\n--- M100R after fix ---")
    for r in rows:
        print(f"ID: {r[0]}")
        print(f"Name: {r[1]}")
        print(f"Img: {r[2]}")
        print(f"URL Advice: {r[3]}")
        print(f"Desc: {r[4]}")
        print("-" * 40)
        
    conn.close()

if __name__ == "__main__":
    asyncio.run(fix_advice_data())
