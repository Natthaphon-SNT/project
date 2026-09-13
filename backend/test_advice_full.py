# -*- coding: utf-8 -*-
import unittest
if __name__ != "__main__":
    raise unittest.SkipTest("manual live-site diagnostic")
import asyncio
import json
import sys
import io
from playwright.async_api import async_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"

async def test_advice_full():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=UA)
        page = await ctx.new_page()
        
        await page.goto("https://www.advice.co.th/product/search?keyword=MOUSE+LOGITECH+M100R+BLACK", timeout=30000)
        await page.wait_for_timeout(4000)
        
        res = await page.evaluate("""
        async () => {
            const getCookie = n => (document.cookie.split('; ').find(c => c.startsWith(n+'='))||'').split('=')[1];
            const token = decodeURIComponent(getCookie('user_token') || '');
            const r = await fetch('https://prodbackadvice.advice.in.th/api/v1.0.0/product/get', {
                method: 'POST', credentials: 'include',
                headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token},
                body: JSON.stringify({category:"search",category_sub:"",product:"",keyword:"MOUSE LOGITECH M100R",
                    take:5,skip:0,refSearch:"",page:"product",arr_filter_brand:[],
                    arr_filter_ict:[],arr_filter_price_ict:[],arr_filter_cate:[],addView:false,
                    group_end:false})
            });
            return await r.json();
        }
        """)
        
        print("Data keys:", list((res.get("data") or {}).keys()))
        prod_list = ((res.get("data") or {}).get("product") or [])
        print("data.product length:", len(prod_list))
        if prod_list:
            print("First item in data.product:", json.dumps(prod_list[0], indent=2, ensure_ascii=False))
            
        await browser.close()

asyncio.run(test_advice_full())
