import urllib.parse
import os
import re
import sys
import json
import asyncio
import uvicorn
import httpx
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from datetime import datetime
from google import genai
from playwright.async_api import async_playwright
from dotenv import load_dotenv

load_dotenv()

if sys.platform == "win32" and sys.version_info < (3, 16):
    try:
        import uvicorn.loops.asyncio # type: ignore
        uvicorn.loops.asyncio.asyncio_setup = lambda *args, **kwargs: None # type: ignore
    except ImportError:
        pass

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("🚨 GOOGLE_API_KEY is missing! Please check your .env file.")

MODEL_NAME = 'gemma-3-12b-it' 

client = genai.Client(api_key=GOOGLE_API_KEY)
app = FastAPI(title="Agentic PC Recommender API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Agentic PC Recommender API is running 🚀"}

SQLALCHEMY_DATABASE_URL = "sqlite:///./pc_builds.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class BuildHistory(Base):
    __tablename__ = "build_history"
    id = Column(Integer, primary_key=True, index=True)
    user_input = Column(String)
    budget = Column(Integer)
    usage_type = Column(String)
    ai_advice = Column(Text) 
    total_price = Column(Integer)
    parts_json = Column(Text)
    created_at = Column(DateTime, default=datetime.now)

Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

HARDWARE_DF = None
if os.path.exists("hardware_updated.csv"):
    try:
        df = pd.read_csv("hardware_updated.csv")
        df.columns = df.columns.str.strip()
        cols = ['price_jib', 'price_advice', 'price_ihavecpu']
        df['price'] = df[cols].replace(0, np.nan).min(axis=1).fillna(0).astype(int)
        HARDWARE_DF = df
        print(f"✅ Loaded baseline catalog.")
    except Exception as e:
        pass

async def call_gemini(prompt: str, retries: int = 3) -> str:
    for attempt in range(retries):
        try:
            await asyncio.sleep(2)
            response = client.models.generate_content(model=MODEL_NAME, contents=prompt)
            return response.text if response.text else ""
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                await asyncio.sleep((attempt + 1) * 6)
            else:
                return ""
    return ""

# 🌟 1. ระบบตัดคำแบบ "สไนเปอร์" (ดึงเฉพาะแก่นของชิ้นส่วน รับรองเว็บช็อปปิ้งหาเจอ 100%)
def clean_keyword(keyword: str, category: str) -> str:
    kw = keyword.lower()
    kw = re.sub(r'\(.*?\)', '', kw) # ตัดวงเล็บ
    kw = re.sub(r'80\+.*', '', kw) # ตัดเรทติ้ง PSU
    kw = kw.replace("nvidia ", "").replace("amd ", "").replace("intel ", "").replace("radeon ", "").replace("geforce ", "")

    if category == "GPU":
        # ดึงมาแค่รหัสการ์ดจอ เช่น "rtx 4060 ti", "rx 7700 xt"
        match = re.search(r'(rtx|gtx|rx)\s*\d{3,4}\s*(ti|super|xtx|xt|gre)?', kw)
        if match: return match.group(0)
    
    elif category == "CPU":
        # ดึงมาแค่รหัส CPU เช่น "ryzen 5 7600", "i5 13400f"
        if "ryzen" in kw:
            match = re.search(r'ryzen\s*\d\s*\d{4}[x]?', kw)
            if match: return match.group(0)
        match = re.search(r'(i\d\s*\d{4,5}[k|f|ks]*|core\s*ultra\s*\d\s*\d{3}[k|f]*)', kw)
        if match: return match.group(0)

    # สำหรับชิ้นส่วนอื่นๆ ดึงมาแค่แบรนด์และรุ่นซีรีส์ (2 คำแรก)
    words = kw.split()
    if not words: return kw
    
    if category == "Mainboard": return ' '.join(words[:2]) # type: ignore
    if category == "RAM": return ' '.join(words[:2]) # type: ignore
    if category == "SSD": return ' '.join(words[:2]) # type: ignore
    if category == "PSU": return ' '.join(words[:2]) # type: ignore
    if category == "Case": return ' '.join(words[:2]) # type: ignore

    return ' '.join(words[:3]) # type: ignore

async def fetch_live_prices_for_all(parts: list) -> list:
    print("🚀 [Agent] Launching Headless Browser (ดึงราคาจริงจากหน้าเว็บ)...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            channel="chrome", 
            args=[
                '--window-size=1280,720', 
                '--disable-blink-features=AutomationControlled', 
                '--disable-infobars',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            ignore_https_errors=True
        )
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        sem = asyncio.Semaphore(3)

        async def scrape_task(part_index, store, part_name, baseline_price, category):
            search_kw = clean_keyword(part_name, category)
            store_kw = search_kw.strip()
            encoded_kw = urllib.parse.quote(store_kw)
            
            # กันเหนียว: ถ้าราคาประเมินของ AI ผิดปกติ ให้ตั้งราคาฐานไว้กลางๆ
            if baseline_price <= 0:
                baseline_price = 3000

            price = 0
            async with sem:
                page = await context.new_page()
                try:
                    await page.route("**/*", lambda route: route.abort() 
                        if route.request.resource_type in ["image", "media", "font"] 
                        else route.continue_()
                    )
                    
                    url = ""
                    if store == "advice":
                        url = f"https://www.advice.co.th/search?keyword={encoded_kw}"
                    elif store == "jib":
                        url = f"https://www.jib.co.th/web/product/product_search/0?str_search={encoded_kw}"
                    elif store == "ihavecpu":
                        url = f"https://www.ihavecpu.com/search?keyword={encoded_kw}"
                    
                    await page.goto(url, timeout=40000, wait_until="domcontentloaded")
                    
                    # 🌟 เพิ่มเวลาให้ Javascript พ่นข้อมูลราคาออกมาให้เสร็จ (สำคัญมากสำหรับ Advice/iHAVECPU)
                    await page.wait_for_timeout(5000) 
                    
                    if "Just a moment" in await page.title() or "Cloudflare" in await page.title():
                        print(f"🚨 [{store.upper()}] ติด Cloudflare ข้ามเว็บนี้")
                        return part_index, store, price

                    # 🌟 อัปเดต Selectors ให้ครอบคลุมทุกคลาสที่เว็บร้านค้าชอบใช้
                    selectors = [
                        '.price-normal', '.price', '.product-price', '.cart-price', '.price_total', 
                        '.text-danger', '.text-primary', 'div[class*="price"]', 'span[class*="price"]'
                    ]
                    
                    for sel in selectors:
                        try:
                            elements = await page.query_selector_all(sel)
                            if elements:
                                for el in elements[:40]: 
                                    price_text = await el.inner_text()
                                    clean_text = price_text.split('.')[0]
                                    nums = re.sub(r'[^\d]', '', clean_text)
                                    raw_price = int(nums) if nums else 0
                                    
                                    if raw_price > 0:
                                        # 🌟 บีบกรอบราคาให้แคบลง (60% - 140%) ป้องกันดึง "คอมประกอบทั้งเซ็ต" มาแทน
                                        lower_bound = baseline_price * 0.6 
                                        upper_bound = baseline_price * 1.4 
                                        
                                        if lower_bound <= raw_price <= upper_bound:
                                            price = raw_price
                                            print(f"✅ [{store.upper()}] เจอหน้าร้าน: {search_kw} -> {price} THB")
                                            break 
                                if price > 0:
                                    break
                        except Exception:
                            continue 
                    
                    if price == 0:
                        print(f"⚠️ [{store.upper()}] โหลดผ่านแต่หาไม่เจอ หรือราคาหลุดกรอบ (Search: '{store_kw}')")
                        
                except Exception as e:
                    pass
                finally:
                    await page.close()
            return part_index, store, price

        tasks = []
        for i, part in enumerate(parts):
            baseline_price = part['price'] 
            for store in ["advice", "jib", "ihavecpu"]:
                tasks.append(scrape_task(i, store, part['name'], baseline_price, part['category']))
        
        results = await asyncio.gather(*tasks)
        await browser.close()
        
        for i, store, price in results:
            if price > 0:
                parts[i]['shop_prices'][store] = price
                
        # 🌟 ระบบ Fallback อัจฉริยะ (ดึงจาก CSV ก่อน -> ถ้าไม่มีค่อยใช้ AI ประเมิน)
        for part in parts:
            valid_prices = [p for p in part['shop_prices'].values() if p > 0]
            if valid_prices:
                part['price'] = min(valid_prices) 
            else:
                fallback_price = 0
                
                # 1. พยายามหาจากไฟล์ hardware_updated.csv ที่เรามี
                if HARDWARE_DF is not None:
                    search_term = clean_keyword(part['name'], part['category']).lower()
                    matches = HARDWARE_DF[HARDWARE_DF['model'].str.lower().str.contains(search_term, na=False)]
                    if not matches.empty:
                        fallback_price = int(matches.iloc[0]['price'])
                        print(f"📊 [CSV Fallback] เจอในฐานข้อมูลออฟไลน์: {part['name']} -> {fallback_price} THB")
                
                # 2. ถ้าใน CSV ไม่มี ค่อยเชื่อราคาจาก AI (หรือตั้งค่า Default ป้องกันพัง)
                if fallback_price <= 0:
                    fallback_price = part.get('price', 0)
                
                if fallback_price <= 0: 
                    fallback_price = 1500 
                    
                part['price'] = fallback_price
                if fallback_price == part.get('price'):
                     print(f"🔄 [AI Fallback] ใช้ราคาประเมิน: {part['name']} -> {part['price']} THB")
            
        return parts

class UserRequest(BaseModel):
    user_input: str

@app.get("/api/history")
def get_build_history(limit: int = 10, db: Session = Depends(get_db)):
    history = db.query(BuildHistory).order_by(BuildHistory.created_at.desc()).limit(limit).all()
    return {"status": "success", "data": history}

@app.post("/api/analyze-requirement")
async def analyze_requirement(req: UserRequest, db: Session = Depends(get_db)):
    try:
        intent_prompt = f"""
        You are an expert PC builder AI. Analyze this user request: '{req.user_input}'.
        Return ONLY a valid JSON object.
        {{
            "budget": <integer, default 25000>,
            "usage_category": "<Gaming|Work|Streaming|AI_Render>"
        }}
        """
        ai_intent_raw = await call_gemini(intent_prompt)
        budget = 25000
        usage = 'Gaming'
        
        if ai_intent_raw:
            try:
                clean_json = re.sub(r'```json\n|\n```|```', '', ai_intent_raw).strip()
                json_match = re.search(r'\{.*\}', clean_json, re.DOTALL)
                if json_match:
                    intent_data = json.loads(json_match.group(0))
                    budget = intent_data.get('budget', 25000)
                    usage = intent_data.get('usage_category', 'Gaming')
            except Exception:
                pass
        
        # 🌟 2. อัปเกรด Prompt: บังคับให้ AI ประเมินราคาตั้งต้นให้ตรงเป๊ะกับตลาดไทย ป้องกันราคามั่ว
        # 🌟 แก้ไข Prompt ให้ AI กล้าจัดสเปกโหดๆ ถ้างบถึง
        print(f"🧠 AI is drafting the initial build for budget: {budget} THB...")
        
        # เพิ่ม Logic การแนะนำสเปกตามช่วงราคา
        guideline = ""
        if budget > 100000:
            guideline = "Budget is VERY HIGH. MUST select High-End parts: RTX 4090, Core i9/Ryzen 9, 64GB+ RAM, 2TB+ SSD."
        elif budget > 50000:
            guideline = "Budget is High. Select RTX 4070/4080, Core i7/Ryzen 7, 32GB RAM."
        else:
            guideline = "Budget is Entry-Mid. Select best value parts."

        draft_prompt = f"""
        You are an expert PC Builder in Thailand. Draft a PC build for '{req.user_input}' with a STRICT budget of {budget} THB.
        
        PRICING GUIDELINE: {guideline}
        
        IMPORTANT INSTRUCTIONS:
        - Provide highly accurate current 'estimated_price' in THB.
        - Ensure the total estimated price is CLOSE to {budget} THB (Do not underspend).
        
        Return ONLY a valid JSON object with the exact keys below:
        {{
            "CPU": {{"name": "Brand and Model", "estimated_price": 0}},
            "Mainboard": {{"name": "Brand and Model", "estimated_price": 0}},
            "RAM": {{"name": "Brand, Capacity, Speed", "estimated_price": 0}},
            "GPU": {{"name": "Brand and Model", "estimated_price": 0}},
            "SSD": {{"name": "Brand, Capacity", "estimated_price": 0}},
            "PSU": {{"name": "Brand, Wattage", "estimated_price": 0}},
            "Case": {{"name": "Brand and Model", "estimated_price": 0}}
        }}
        """
        
        ai_draft_raw = await call_gemini(draft_prompt)
        draft_parts = []
        
        if ai_draft_raw:
            try:
                clean_draft_json = re.sub(r'```json\n|\n```|```', '', ai_draft_raw).strip()
                draft_data = json.loads(clean_draft_json)
                
                for cat, item_data in draft_data.items():
                    est_price = item_data.get("estimated_price", 1000)
                    draft_parts.append({
                        "category": cat,
                        "name": str(item_data.get("name", "Unknown")),
                        "price": int(est_price), 
                        "shop_prices": {"advice": 0, "jib": 0, "ihavecpu": 0}
                    })
            except Exception:
                raise HTTPException(status_code=500, detail="AI could not draft the build. Try again.")

        print("🔍 Scanning live prices from stores with Headless Browser...")
        final_parts = await fetch_live_prices_for_all(draft_parts)
        total_price = sum(p['price'] for p in final_parts)

        parts_list_str = ", ".join([f"{p['category']}: {p['name']} ({p['price']} THB)" for p in final_parts])
        budget_alert = ""
        if total_price > budget * 1.15: 
            budget_alert = f"WARNING: ราคา ({total_price} THB) เกินงบที่ผู้ใช้ตั้งไว้ ({budget} THB). คุณต้องแนะนำให้ลดสเปกชิ้นส่วนที่แพงเกินไปในหัวข้อ 'คำแนะนำการอัปเกรด/ปรับลด'"

        analysis_prompt = f"""
        You are a highly skilled Thai PC Hardware Expert. 
        Analyze this final selected PC build for a user who wants it for '{req.user_input}' (Budget: {budget} THB).
        
        Build List: {parts_list_str}
        Total Price: {total_price} THB
        
        {budget_alert}
        
        CRITICAL RULES FOR YOUR RESPONSE:
        1. DO NOT use any HTML tags.
        2. DO NOT write long paragraphs. Keep it short, punchy, and easy to read.
        3. Respond EXACTLY with the 4 headings below, and provide 1-3 bullet points under each heading.
        
        🎯 ภาพรวมความเหมาะสม:
        - 
        🚀 ประสิทธิภาพที่คาดหวัง:
        - 
        ⚠️ จุดเด่น & ข้อควรระวัง:
        - 
        💡 คำแนะนำการอัปเกรด/ปรับลด:
        - 
        """
        
        print("🧠 Generating Expert Analysis...")
        ai_advice_raw = await call_gemini(analysis_prompt)
        
        if not ai_advice_raw:
            ai_advice_list = ["🎯 ภาพรวมความเหมาะสม:", "- ระบบไม่สามารถวิเคราะห์ได้เนื่องจากโควตา AI เต็ม"]
        else:
            ai_advice_list = [line.strip() for line in ai_advice_raw.split('\n') if line.strip()]

        new_rec = BuildHistory(
            user_input=req.user_input, 
            budget=budget, 
            usage_type=usage,
            ai_advice=json.dumps(ai_advice_list, ensure_ascii=False), 
            total_price=total_price, 
            parts_json=json.dumps(final_parts)
        )
        db.add(new_rec)
        db.commit()

        return {
            "status": "success",
            "data": {
                "budget": budget,
                "usage": usage,
                "parts": final_parts,
                "total_price": total_price,
                "advice": ai_advice_list 
            }
        }

    except Exception as e:
        print(f"❌ Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/history/{id}")
def delete_history_item(id: int, db: Session = Depends(get_db)):
    try:
        record = db.query(BuildHistory).filter(BuildHistory.id == id).first()
        if not record:
            raise HTTPException(status_code=404, detail="ไม่พบข้อมูลสเปกนี้ในระบบ")
        
        db.delete(record)
        db.commit()
        return {"status": "success", "message": "ลบข้อมูลสำเร็จ"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ✅ Helper function: Fetch price from PHP backend
async def fetch_price_from_php(product_name: str) -> str:
    """Query ราคาจาก PHP API / Database"""
    try:
        # วิธี 1: ดึงจาก search_products.php
        async with httpx.AsyncClient(timeout=5) as client:
            # ลองดึงจาก get_product.php (query ตรงชื่อ)
            search_term = product_name.replace("(", "").replace(")", "").split()[0:3]  # ดึง 3 คำแรก
            search_query = " ".join(search_term)
            
            response = await client.get(
                f"http://localhost/pc_part/api/get_product.php?name={search_query}"
            )
            data = response.json()
            
            if data.get("status") == "success" and data.get("data"):
                products = data["data"]
                # จัดการ response แบบ list
                if isinstance(products, list) and len(products) > 0:
                    price = products[0].get("p_price", products[0].get("price", "0"))
                elif isinstance(products, dict):
                    price = products.get("p_price", products.get("price", "0"))
                else:
                    price = "0"
                
                if price and price != "0":
                    print(f"✅ Got price from PHP: {product_name} = {price}")
                    return str(price)
    except Exception as e:
        print(f"⚠️ PHP query error for '{product_name}': {e}")
    
    # วิธี 2: Fallback - ดึงจาก CSV
    try:
        if HARDWARE_DF is not None and not HARDWARE_DF.empty:
            # ค้นหาแบบ fuzzy match (เลือกคำแรก)
            search_text = product_name.split()[0] if product_name else ""
            product_rows = HARDWARE_DF[HARDWARE_DF['name'].str.contains(search_text, case=False, na=False)]
            
            if not product_rows.empty:
                price = product_rows.iloc[0]['price']
                print(f"✅ Got price from CSV: {product_name} = {price}")
                return str(price)
    except Exception as e:
        print(f"⚠️ CSV query error: {e}")
    
    print(f"❌ No price found for: {product_name}")
    return "0"

# ✅ WebSocket สำหรับอัปเดตราคาแบบ Real-time
@app.websocket("/ws/prices")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("✅ WebSocket Client Connected")
    try:
        while True:
            # รับข้อมูลจาก Client
            data = await websocket.receive_text()
            message = json.loads(data)
            action = message.get("action", "")
            
            if action == "subscribe":
                # Client สมัครสมาชิกเพื่อรับการอัปเดตราคา
                product_id = message.get("product_id", "")
                print(f"📌 Client subscribed to: {product_id}")
                
                # ดึงราคาจาก PHP หรือ CSV
                price = await fetch_price_from_php(product_id)
                price_data = {
                    "id": product_id,
                    "price": price,
                    "timestamp": datetime.now().isoformat()
                }
                await websocket.send_json(price_data)
                print(f"💰 Sent price for {product_id}: {price_data}")
            
            elif action == "ping":
                # Heartbeat เพื่อตรวจสอบการเชื่อมต่อ
                await websocket.send_json({"status": "pong", "timestamp": datetime.now().isoformat()})
                
    except WebSocketDisconnect:
        print("❌ WebSocket Client Disconnected")
    except Exception as e:
        print(f"⚠️ WebSocket Error: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Server on http://127.0.0.1:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)


# ===== Live scraping endpoint (Advice / JIB / iHaveCPU)
async def _scrape_with_selectors(page, url: str, selectors: list[str], min_limit: int = 100, max_limit: int = 10_000_000) -> int:
    """Navigate to URL and try multiple CSS selectors to extract numeric prices.
    Returns the minimum valid price found or 0."""
    try:
        await page.goto(url, timeout=30000, wait_until='domcontentloaded')
        await page.wait_for_timeout(1000)

        # Try each selector and gather numeric values
        for sel in selectors:
            try:
                prices = await page.eval_on_selector_all(sel, "elements => elements.map(e => e.innerText || e.textContent || '').filter(Boolean)")
            except Exception:
                prices = []

            # flatten and extract numbers
            import re
            extracted = []
            for t in prices:
                if not t: continue
                # find patterns like 1,234 or 1234
                for m in re.findall(r'([1-9]\d{0,2}(?:,\d{3})+|\d{3,})', t):
                    v = int(m.replace(',', ''))
                    if min_limit <= v <= max_limit:
                        extracted.append(v)

            if extracted:
                return min(extracted)

        # fallback: scan entire page text
        text = await page.inner_text('body')
        import re as _re
        matches = _re.findall(r'([1-9]\d{0,2}(?:,\d{3})+)', text)
        prices = [int(m.replace(',', '')) for m in matches]
        prices = [p for p in prices if min_limit <= p <= max_limit]
        return min(prices) if prices else 0
    except Exception:
        return 0


@app.get('/api/live_prices')
async def api_live_prices(name: str):
    """Return live scraped prices from three stores for given product name."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        q = urllib.parse.quote_plus(name)
        results = {
            'advice': 0,
            'jib': 0,
            'ihavecpu': 0
        }

        try:
            # Advice selectors (try multiple patterns)
            advice_url = f'https://www.advice.co.th/search?keyword={q}'
            advice_selectors = [
                '.product-card .price, .product-card .price-sale, .product-card .product-price',
                '.box-product .price, .box-product .product-price',
                '.product-item .price, .product-item .product-price',
                '.price, .pricing, .product-price'
            ]
            results['advice'] = await _scrape_with_selectors(page, advice_url, advice_selectors)

            # JIB selectors
            jib_url = f'https://www.jib.co.th/web/product/product_search/0?str_search={q}'
            jib_selectors = [
                '.product-box .price, .product-box .price-sale, .product-box .product-price',
                '.product-item .price, .product-item .product-price',
                '.price, .pricing'
            ]
            results['jib'] = await _scrape_with_selectors(page, jib_url, jib_selectors)

            # iHaveCPU selectors
            ihavecpu_url = f'https://www.ihavecpu.com/product/search/{q}'
            ihavecpu_selectors = [
                '.product-list .price, .product-list .product-price',
                '.product-card .price, .product-card .product-price',
                '.price'
            ]
            results['ihavecpu'] = await _scrape_with_selectors(page, ihavecpu_url, ihavecpu_selectors)

        finally:
            try:
                await browser.close()
            except:
                pass

    # Prefer non-zero prices; return all three
    return { 'status': 'success', 'query': name, 'data': results }