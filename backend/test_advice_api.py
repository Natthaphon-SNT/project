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

async def test_advice():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=UA)
        page = await ctx.new_page()
        
        await page.goto("https://www.advice.co.th/", timeout=30000)
        await page.wait_for_timeout(3000)
        
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
        
        data_res = ((res or {}).get("data") or {}).get("data_res") or {}
        pl = data_res.get("product_list") or {}
        result_search = pl.get("result_search") or []
        
        print("Groups count:", len(result_search))
        for g in result_search:
            print("Category:", g.get("category1"), g.get("category2"))
            products = g.get("product") or []
            for p in products:
                print("Product keys:", list(p.keys()))
                print("Sample product:", json.dumps(p, indent=2, ensure_ascii=False))
        
        await browser.close()

asyncio.run(test_advice())
