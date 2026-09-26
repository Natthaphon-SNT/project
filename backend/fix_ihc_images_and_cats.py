# -*- coding: utf-8 -*-
"""
1. Fix invalid img_urls (data:image or .gif) in shop.db by fetching real og:image from product URLs
2. Fix misclassified categories (e.g. RAM classified as Headset/Gaming Desk)
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

# Category detection rules based on name prefixes & keywords
NAME_TO_CAT = [
    (r'^(?:RAM|DDR4|DDR5)\b|\b(?:DDR4|DDR5)\s*(?:RAM|MEMORY|3200|3600|5200|5600|6000|6400)', 'RAM', 'c04'),
    (r'^(?:CPU|INTEL|RYZEN|CORE ULTRA)\b', 'CPU', 'c01'),
    (r'^(?:MAINBOARD|MOTHERBOARD|เมนบอร์ด)\b', 'Mainboard', 'c02'),
    (r'^(?:VGA|GPU|GRAPHIC CARD|การ์ดจอ|GEFORCE|RADEON)\b', 'GPU', 'c03'),
    (r'^(?:SSD|M\.2|NVME)\b', 'SSD', 'c05'),
    (r'^(?:POWER SUPPLY|PSU|พาวเวอร์ซัพพลาย)\b', 'PSU', 'c06'),
    (r'^(?:CASE|เคส)\b', 'Case', 'c07'),
    (r'^(?:CPU LIQUID COOLER|LIQUID COOLER|AIO COOLER|ชุดน้ำ)\b', 'Liquid Cooler', 'c08'),
    (r'^(?:CPU COOLER|AIR COOLER|COOLER|พัดลมซีพียู)\b', 'Air Cooler', 'c09'),
    (r'^(?:MOUSE|เมาส์)\b', 'Mouse', 'c10'),
    (r'^(?:KEYBOARD|คีย์บอร์ด)\b', 'Keyboard', 'c11'),
    (r'^(?:HEADSET|HEADPHONE|หูฟัง)\b', 'Headset', 'c12'),
    (r'^(?:MICROPHONE|ไมโครโฟน)\b', 'Microphone', 'c13'),
    (r'^(?:MONITOR|จอภาพ|จอคอม)\b', 'Monitor', 'c14'),
    (r'^(?:GAMING CHAIR|CHAIR|เก้าอี้)\b', 'Gaming Chair', 'c15'),
    (r'^(?:GAMING DESK|DESK|โต๊ะ)\b', 'Gaming Desk', 'c16'),
]

def detect_category(name: str) -> tuple[str, str] | None:
    n_up = name.strip().upper()
    for pat, cat, cid in NAME_TO_CAT:
        if re.search(pat, n_up):
            return cat, cid
    return None

async def fix_database():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Fix Categories
    print("--- [1] Checking and fixing categories ---")
    rows = cur.execute("SELECT product_id, p_name, category, cid FROM products").fetchall()
    cat_fixed = 0
    for pid, name, cat, cid in rows:
        # Don't change PC Sets
        if cat == 'PC Set':
            continue
        det = detect_category(name)
        if det:
            correct_cat, correct_cid = det
            if correct_cat != cat or correct_cid != cid:
                cur.execute("UPDATE products SET category = ?, cid = ? WHERE product_id = ?", (correct_cat, correct_cid, pid))
                cat_fixed += 1
                print(f"Fixed Cat: [{name[:40]}...]\n   {cat} ({cid}) -> {correct_cat} ({correct_cid})")
    conn.commit()
    print(f"Categories fixed: {cat_fixed}")

    # 2. Fix Invalid Image URLs
    print("\n--- [2] Checking and fixing invalid image URLs ---")
    bad_rows = cur.execute("""
        SELECT product_id, p_name, img_url, url_advice, url_jib, url_ihavecpu
        FROM products
        WHERE img_url LIKE '%data:image%' OR img_url LIKE '%base64%' OR img_url LIKE '%.gif%' OR img_url = '' OR img_url IS NULL
    """).fetchall()

    print(f"Products with bad/missing image URLs: {len(bad_rows)}")

    if bad_rows:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            ctx = await browser.new_context(user_agent=UA)
            page = await ctx.new_page()

            for i, (pid, name, img, url_adv, url_jib, url_ihc) in enumerate(bad_rows):
                target_url = url_ihc or url_jib or url_adv
                if not target_url or target_url.startswith("https://www.advice.co.th/search"):
                    continue

                try:
                    await page.goto(target_url, timeout=30000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(3000)

                    new_img = ""
                    # 1. Try og:image
                    m = await page.query_selector('meta[property="og:image"]')
                    if m:
                        c = (await m.get_attribute("content") or "").strip()
                        if c.startswith("http") and not c.endswith(".gif") and "data:" not in c:
                            new_img = c

                    # 2. Try product image tags
                    if not new_img:
                        imgs = await page.query_selector_all("img")
                        for im in imgs:
                            for attr in ["src", "data-src", "data-lazy", "data-original"]:
                                val = (await im.get_attribute(attr) or "").strip()
                                if val.startswith("http") and not val.endswith(".gif") and "data:" not in val:
                                    if "product" in val or "amazonaws" in val or "jib" in val or "advice" in val:
                                        new_img = val
                                        break
                            if new_img:
                                break

                    if new_img:
                        cur.execute("UPDATE products SET img_url = ? WHERE product_id = ?", (new_img, pid))
                        print(f"[{i+1}/{len(bad_rows)}] Fixed image for [{name[:35]}...]:\n    -> {new_img}")
                        conn.commit()
                except Exception as e:
                    print(f"[{i+1}/{len(bad_rows)}] Error visiting {target_url[:50]}: {e}")

            await browser.close()

    conn.commit()

    # Verify D35 RAM specifically
    print("\n--- Verifying RAM ADATA XPG GAMMIX X D35 after fix ---")
    rows_d35 = cur.execute("SELECT product_id, p_name, category, cid, img_url, url_ihavecpu FROM products WHERE p_name LIKE '%D35%32GB%'").fetchall()
    for r in rows_d35:
        print(f"PID: {r[0]}")
        print(f"Name: {r[1]}")
        print(f"Category: {r[2]} ({r[3]})")
        print(f"Img: {r[4]}")
        print(f"URL: {r[5]}")
        print("-" * 50)

    conn.close()

if __name__ == "__main__":
    asyncio.run(fix_database())
