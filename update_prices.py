import sys
import re
import asyncio
import pandas as pd
from playwright.async_api import async_playwright

# 🌟 1. ปิดโค้ดส่วนนี้ทิ้งเพื่อแก้ปัญหาข้อความแจ้งเตือนสีแดง (DeprecationWarning)
# if sys.platform == "win32":
#     asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

def get_search_keyword(brand, model, cat):
    model_str = str(model).lower().replace('-', ' ')
    brand_str = str(brand).lower()
    
    if cat == "GPU":
        match = re.search(r'(rtx|gtx|rx)\s+\d+(?:\s+(ti|super|xt|xtx|gre))?', model_str)
        if match:
            prefix = "geforce " if "rtx" in match.group(0) or "gtx" in match.group(0) else "radeon "
            return f"{brand_str} {prefix}{match.group(0)}"
        return f"{brand_str} {model_str}"
    elif cat == "Mainboard":
        words = model_str.split()
        return f"{brand_str} {words[0]}"
    elif cat in ["RAM", "SSD"]:
        clean_model = re.sub(r'\(.*?\)|nvme|sata|gen\d|ssd|m\.2', '', model_str).strip()
        return f"{brand_str} {clean_model}"
    elif cat == "CPU":
        if "ultra" in model_str:
            match = re.search(r'ultra\s+\d+\s+\w+', model_str)
            return match.group(0) if match else model_str
        elif "core" in model_str:
            match = re.search(r'i\d+\s+\w+', model_str)
            return match.group(0) if match else model_str
        elif "ryzen" in model_str:
            match = re.search(r'ryzen\s+\d+\s+\w+', model_str)
            return match.group(0) if match else model_str
        return model_str
    else:
        return f"{brand_str} {model_str}"

def validate_item(card_text, brand, model, cat):
    card = card_text.lower().replace('-', '').replace(' ', '')
    model_str = str(model).lower().replace('-', ' ')
    
    if any(b in card for b in ['notebook', 'laptop', 'minipc', 'barebone', 'aio', 'allinone', 'คอมเซ็ต', 'คอมประกอบ']):
        return False
        
    if cat == "RAM" and any(b in card for b in ['sodimm', 'so-dimm', 'mac']): return False
    if cat == "SSD" and any(b in card for b in ['external', 'portable', 'enclosure']): return False
    if cat == "GPU" and any(b in card for b in ['block', 'water', 'bracket', 'riser', 'cable']): return False

    if cat == "GPU":
        chip_match = re.search(r'\d{4}', model_str)
        if chip_match and chip_match.group(0) not in card: return False
        for suf in ['ti', 'super', 'xtx', 'xt', 'gre']:
            if suf in model_str.split() and suf not in card: return False
        return True
    elif cat == "Mainboard":
        chip_match = re.search(r'[a-z]\d{3}[a-z]?', model_str)
        if chip_match and chip_match.group(0) not in card: return False
        if 'wifi' in model_str and 'wifi' not in card: return False
        if 'ddr4' in model_str and 'ddr4' not in card: return False
        if 'ddr5' in model_str and 'ddr5' not in card: return False
        return True
    elif cat == "RAM":
        if 'ddr4' in model_str and 'ddr4' not in card: return False
        if 'ddr5' in model_str and 'ddr5' not in card: return False
        speed_match = re.search(r'\d{4}', model_str)
        if speed_match and speed_match.group(0) not in card: return False
        cap_match = re.search(r'\d+gb', model_str)
        if cap_match and cap_match.group(0) not in card: return False
        return True
    elif cat == "SSD":
        cap_match = re.search(r'\d+(?:gb|tb)', model_str)
        if cap_match and cap_match.group(0) not in card: return False
        clean_model = re.sub(r'\(.*?\)|nvme|sata|gen\d|ssd|m\.2|\d+(?:gb|tb)', '', model_str).strip()
        key_words = [w for w in clean_model.split() if any(c.isdigit() for c in w) or len(w) > 3]
        if key_words:
            main_key = key_words[-1].replace('-', '')
            if main_key not in card: return False
        return True
    elif cat == "CPU":
        if 'ultra' in model_str and 'ultra' not in card: return False
        num_match = re.search(r'\d{3,5}', model_str)
        if not num_match: return False
        target_word = [w for w in model_str.split() if num_match.group(0) in w][0]
        if target_word.replace('-', '') not in card: return False
        return True
    else:
        key_words = [w for w in model_str.split() if len(w) > 2]
        if key_words:
            if key_words[0].replace('-', '') not in card: return False
        return True

async def scrape_store(page, store, row_data):
    brand = str(row_data['brand'])
    model = str(row_data['model'])
    cat = str(row_data['category'])
    
    # 🌟 2. เพิ่มชื่อหมวดหมู่ (cat) เข้าไปข้างหน้าคำค้นหาเพื่อกันการเจออุปกรณ์เสริม
    raw_kw = get_search_keyword(brand, model, cat)
    search_kw = f"{cat} {raw_kw}" if cat in ["CPU", "Mainboard", "VGA", "Case", "PSU"] else raw_kw
    
    try:
        ref_price = max(int(row_data['price_jib']), int(row_data['price_advice']), int(row_data['price_ihavecpu']))
    except:
        ref_price = 0
        
    if ref_price > 500:
        min_limit = ref_price * 0.4
        max_limit = ref_price * 1.6
    else:
        min_limit = 350
        max_limit = 95000 if cat == "GPU" else 45000

    price = 0
    try:
        url = ""
        if store == "advice": 
            url = f"https://www.advice.co.th/search?keyword={search_kw.replace(' ', '+')}"
        elif store == "jib": 
            url = f"https://www.jib.co.th/web/product/product_search/0?str_search={search_kw.replace(' ', '%20')}"
        elif store == "ihavecpu": 
            url = f"https://www.ihavecpu.com/product/search/{search_kw.replace(' ', '%20')}"

        await page.goto(url, timeout=45000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2500)
        
        title = await page.title()
        if any(bad in title for bad in ["Just a moment", "Cloudflare", "Attention", "Challenge"]):
            print(f"\n🚨 [{store.upper()}] Cloudflare เด้ง! รอคลิกยืนยัน (มีเวลา 20 วิ)...")
            await page.wait_for_timeout(20000) 
            
        await page.mouse.wheel(0, 800)
        await page.wait_for_timeout(3000)
        
        curr_url = page.url
        fake_prices = [4590, 19990, 20990]

        is_single_page = False
        if store == "advice" and "/product/" in curr_url: is_single_page = True
        elif store == "jib" and "/view/" in curr_url: is_single_page = True
        elif store == "ihavecpu" and "/product/" in curr_url and "search" not in curr_url: is_single_page = True

        if is_single_page:
            body_text = await page.inner_text('body')
            matches = re.findall(r'([1-9]\d{0,2}(?:,\d{3})+)', body_text)
            if matches:
                valid_prices = [int(m.replace(',', '')) for m in matches]
                valid_prices = [p for p in valid_prices if min_limit <= p <= max_limit and p not in fake_prices]
                if valid_prices:
                    price = min(valid_prices) 
        else:
            js_script = """
            () => {
                let cards = [];
                document.querySelectorAll('.box-product, .buy_promotion, .product-item, .product-box, .product-card, .product-detail, .summary-info, article, .item, a').forEach(el => {
                    let text = el.innerText || '';
                    if(text.length > 20 && text.length < 2500 && /[1-9]\\d{0,2},\\d{3}/.test(text)) {
                        cards.push(text.toLowerCase());
                    }
                });
                return [...new Set(cards)];
            }
            """
            cards = await page.evaluate(js_script)
            
            for card in cards:
                if not validate_item(card, brand, model, cat): continue
                
                matches = re.findall(r'([1-9]\d{0,2}(?:,\d{3})+)', card)
                if matches:
                    valid_prices = [int(m.replace(',', '')) for m in matches]
                    valid_prices = [p for p in valid_prices if min_limit <= p <= max_limit and p not in fake_prices]
                    if valid_prices:
                        price = min(valid_prices)
                        break 

            if price == 0:
                body_text = await page.inner_text('body')
                lines = [line.strip().lower() for line in body_text.split('\n') if line.strip()]
                for i, line in enumerate(lines):
                    if validate_item(line, brand, model, cat):
                        search_chunk = " ".join(lines[i:i+25])
                        matches = re.findall(r'([1-9]\d{0,2}(?:,\d{3})+)', search_chunk)
                        if matches:
                            valid_prices = [int(m.replace(',', '')) for m in matches]
                            valid_prices = [p for p in valid_prices if min_limit <= p <= max_limit and p not in fake_prices]
                            if valid_prices:
                                price = min(valid_prices)
                                break
    except Exception as e:
        pass
    return price

async def main():
    print("📦 Loading hardware_latest.csv...")
    try:
        df = pd.read_csv("hardware_latest.csv")
    except FileNotFoundError:
        print("❌ ไม่พบไฟล์ hardware_latest.csv")
        return

    total_items = len(df)
    print(f"🔍 Found {total_items} items. Starting Playwright (V18 - MASTER REDIRECT)...")

    chunk_size = 40 
    
    for start_idx in range(0, total_items, chunk_size):
        end_idx = min(start_idx + chunk_size, total_items)
        print(f"\n🚀 --- กำลังรันชุดที่ {start_idx+1} ถึง {end_idx} ---")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                channel="chrome", 
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-infobars'
                ]
            )
            
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            
            # 🌟 [ไฮไลท์สำคัญ] ฝังสคริปต์พรางตัว (Stealth) ระดับลึกด้วยตัวเองแบบไม่ง้อไลบรารี
            await context.add_init_script("""
                // 1. ซ่อนสถานะ Webdriver
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                // 2. หลอกว่ามีตัวแปร Chrome อยู่ (บอทมักจะไม่มีตัวนี้)
                window.chrome = { runtime: {} };
                // 3. หลอกว่ามี Plugins ติดตั้งอยู่เหมือนคนเล่นเว็บปกติ
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                // 4. ตั้งค่าภาษาให้ดูเหมือนเครื่องคนไทยจริงๆ
                Object.defineProperty(navigator, 'languages', {get: () => ['th-TH', 'th', 'en-US', 'en']});
            """)
            
            # สร้างหน้าต่างตามปกติ (ไม่ต้องมี stealth_async แล้ว)
            page_advice = await context.new_page()
            page_jib = await context.new_page()
            page_ihavecpu = await context.new_page()
            
            for index in range(start_idx, end_idx):
                row = df.iloc[index]
                part_name = f"{row['brand']} {row['model']}"
                search_kw = get_search_keyword(row['brand'], row['model'], row['category'])
                
                # แสดงผลคีย์เวิร์ดใหม่ที่เพิ่มหมวดหมู่เข้าไปแล้ว
                display_kw = f"{row['category']} {search_kw}" if row['category'] in ["CPU", "Mainboard", "VGA", "Case", "PSU"] else search_kw
                
                print(f"[{index+1}/{total_items}] Fetching: {part_name} (Search: '{display_kw}') ...", end=" ", flush=True)
                
                p_advice = await scrape_store(page_advice, "advice", row)
                p_jib = await scrape_store(page_jib, "jib", row)
                p_ihavecpu = await scrape_store(page_ihavecpu, "ihavecpu", row)
                
                if p_jib > 0: df.at[index, 'price_jib'] = p_jib
                if p_advice > 0: df.at[index, 'price_advice'] = p_advice
                if p_ihavecpu > 0: df.at[index, 'price_ihavecpu'] = p_ihavecpu
                
                print(f"✅ [A:{p_advice} | J:{p_jib} | I:{p_ihavecpu}]")

            await browser.close()
            
        df.to_csv("hardware_updated.csv", index=False)
        print(f"💾 บันทึกชุดที่ {end_idx} สำเร็จ! (พักเครื่อง 5 วิ ก่อนลุยต่อ...)")
        await asyncio.sleep(5)

    print("\n🎉 Mission Accomplished! กวาดข้อมูลจบครบ 100% แล้วครับ!")

if __name__ == "__main__":
    asyncio.run(main())