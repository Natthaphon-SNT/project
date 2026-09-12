"""
Full Scraper v3 - Advice / JIB / iHaveCPU
==========================================
Features:
  - ดึงสินค้าจาก 3 ร้าน: Advice (API), JIB (HTML), iHaveCPU (HTML)
  - SmartMatcher 3 ระดับ:
      1. Exact match (case-insensitive)
      2. Model-key match  — ถ้า SKU/รุ่น token ชุดเดิมตรงกันหมด (เช่น 250K, RTX4070)
      3. Token-based Jaccard similarity >= 0.50
  - Dedup ข้ามร้าน → 1 record, 3 URL/ราคา
  - --details: visit หน้าสินค้าแต่ละชิ้นเพื่อดึง description + รูปภาพเต็ม

การใช้งาน:
  python full_scraper.py                          # เร็ว: listing เท่านั้น
  python full_scraper.py --details                # ครบ: + visit หน้าสินค้า (ช้า)
  python full_scraper.py --stores jib ihavecpu    # เลือกร้าน
  python full_scraper.py --stores ihavecpu --details --pages 3
"""

import asyncio
import argparse
import hashlib
import html as html_lib
import json
import re
import sqlite3
import sys
import io
import random
import os
import subprocess
from urllib.parse import quote, unquote, urlparse
from datetime import datetime
import httpx
from playwright.async_api import async_playwright

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "shop.db")
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
ANTI_BOT = (
    "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
    "window.chrome={runtime:{}};"
)

# ─────────────────────────────────────────────────────────────────────────────
# Skip filters
# ─────────────────────────────────────────────────────────────────────────────
SKIP_KEYWORDS = [
    "NOTEBOOK", "LAPTOP", "โน๊ตบุ๊ค", "โน้ตบุ๊ค", "โน้ตบุค", "โนตบุค",
    "MACBOOK", "CHROMEBOOK", "ULTRABOOK", "GAMING LAPTOP", "GAMING NOTEBOOK",
    "MOUSE PAD", "MOUSEPAD", "SPEAKER", "WEBCAM", "HUB", "CABLE",
    "UPS", "JOYSTICK", "PRINTER", "EXTERNAL", "NAS", "ROUTER",
    "NETWORK", "ACCESS POINT", "SWITCH", "GAMEPAD", "PROJECTOR",
    "SCANNER", "STABILIZER", "BY ORDER", "PRE ORDER",
    "VACUUM", "CLEANER", "เครื่องดูดฝุ่น", "หุ่นยนต์ดูดฝุ่น", "DUST MITE",
    "FLASH DRIVE", "SD CARD", "MICRO SD", "THUMB DRIVE", "DVD TRAY", "CARD READER",
    "EXT SSD", "EXTERNAL SSD", "PORTABLE SSD", "EXTERNAL HDD",
    "POWER BANK", "POWER TRACK", "POWER STATION", "เต้ารับ", "รางไฟ", "ปลั๊ก",
    "PS5", "PS4", "PLAYSTATION", "XBOX", "NINTENDO", "SWITCH",
    "CONTROLLER", "WHEEL", "พวงมาลัย", "ROG ALLY", "XBOX ALLY",
    "SMART GUARD", "CHARGER", "แผ่นเกม", "GAME SONY", "ADAPTER",
    "IPHONE", "IPAD", "GALAXY", "เคสโทรศัพท์", "เคสมือถือ", "ซอง", "ฟิล์ม", "AIRSUIT", "FORCEGUARD",
    "SOUND CARD", "SOUNDCARD", "DAC", "AUDIO INTERFACE",
    "DESKTOP ASUS", "DESKTOP LENOVO", "AIO ASUS", "ALL-IN-ONE",
    "MINI PC", "NVIDIA DGX", "TABLET", "SURFACE", "LED TV", "SMART TV", "ขาแขวน",
    "WALL RACK", "RACK SERVER", "ตู้ RACK", "คีม", "FACE PLATE", "WALL SCREEN", "TOUCH SCREEN",
]
NOTEBOOK_URL_KW = ["notebook", "laptop", "macbook", "chromebook"]

# ─────────────────────────────────────────────────────────────────────────────
# Store categories
# ─────────────────────────────────────────────────────────────────────────────
ADVICE_API = "https://prodbackadvice.advice.in.th/api/v1.0.0/product/get"
ADVICE_SEARCH_KW = [
    ("CPU",           ["ryzen", "intel core"]),
    ("Mainboard",     ["mainboard"]),
    ("GPU",           ["vga rtx", "vga radeon"]),
    ("RAM",           ["ram ddr4", "ram ddr5"]),
    ("SSD",           ["ssd nvme", "ssd sata"]),
    ("PSU",           ["psu atx", "power supply"]),
    ("Case",          ["case atx", "case matx", "case itx"]),
    ("Liquid Cooler", ["liquid cooler", "aio cooler"]),
    ("Air Cooler",    ["air cooler", "cpu cooler fan"]),
    ("Monitor",       ["monitor gaming", "monitor ips"]),
    ("Mouse",         ["mouse gaming"]),
    ("Keyboard",      ["keyboard gaming"]),
    ("Headset",       ["headset gaming"]),
    ("Gaming Chair",  ["gaming chair"]),
    ("Gaming Desk",   ["gaming desk"]),
]
ADVICE_FETCH_JS = """
async (args) => {
    const getCookie = n => (document.cookie.split('; ').find(c => c.startsWith(n+'='))||'').split('=')[1];
    let token = decodeURIComponent(getCookie('user_token') || '');
    // Advice search API requires a token even for public browsing. The site
    // issues a short-lived guest token, so use it when no member cookie exists.
    if (!token) {
        token = window.__adviceGuestToken || '';
        if (!token) {
            try {
                const guest = await fetch('https://prodbackadvice.advice.in.th/api/v1.0.0/user/guest', {
                    method: 'POST', credentials: 'omit',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({type: 'online'})
                });
                const guestJson = await guest.json();
                token = (guestJson.data || {}).token || '';
                if (token) window.__adviceGuestToken = token;
            } catch (_) {}
        }
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 25000);
    try {
        const r = await fetch('%s', {
            method: 'POST', credentials: 'include', signal: controller.signal,
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
    } finally {
        clearTimeout(timer);
    }
}
""" % ADVICE_API

JIB_CATS = [
    ("CPU",           "https://www.jib.co.th/web/product/product_list/2/43"),
    ("Mainboard",     "https://www.jib.co.th/web/product/product_list/2/46"),
    ("GPU",           "https://www.jib.co.th/web/product/product_list/2/51"),
    ("RAM",           "https://www.jib.co.th/web/product/product_list/2/53"),
    ("SSD",           "https://www.jib.co.th/web/product/product_list/2/52"),
    ("PSU",           "https://www.jib.co.th/web/product/product_list/3/185"),
    ("Case",          "https://www.jib.co.th/web/product/product_list/3/184"),
    ("Liquid Cooler", "https://www.jib.co.th/web/product/product_list/2/1393"),
    ("Air Cooler",    "https://www.jib.co.th/web/product/product_list/2/1367"),
    ("Monitor",       "https://www.jib.co.th/web/product/product_list/1/58"),
    ("Mouse",         "https://www.jib.co.th/web/product/product_list/2/346"),
    ("Keyboard",      "https://www.jib.co.th/web/product/product_list/2/345"),
    ("Headset",       "https://www.jib.co.th/web/product/product_list/2/348"),
]
JIB_PREFIX_MAP = {
    "CPU": "CPU", "MAINBOARD": "Mainboard", "VGA": "GPU", "GRAPHIC CARD": "GPU",
    "RAM": "RAM", "SSD": "SSD", "HARDDISK": "SSD", "M.2": "SSD",
    "POWER SUPPLY": "PSU", "CASE": "Case",
    "LIQUID COOLER": "Liquid Cooler", "CPU COOLER": "Air Cooler", "COOLER": "Air Cooler",
    "LCD PANEL": "Monitor", "MONITOR": "Monitor",
    "KEYBOARD": "Keyboard", "MOUSE": "Mouse", "HEADSET": "Headset",
}
JIB_SKIP_PREFIXES = {
    "MOUSE PAD", "SPEAKER", "WEBCAM", "HUB", "CABLE", "UPS",
    "JOYSTICK", "PRINTER", "EXTERNAL", "NAS", "ROUTER",
    "NETWORK", "ACCESS POINT", "SWITCH", "NOTEBOOK", "LAPTOP",
}

IHC_CATS = [
    ("CPU",          "https://www.ihavecpu.com/category/cpu"),
    ("Mainboard",    "https://www.ihavecpu.com/category/mainboard"),
    ("GPU",          "https://www.ihavecpu.com/category/graphic-card"),
    ("RAM",          "https://www.ihavecpu.com/category/ram"),
    ("SSD",          "https://www.ihavecpu.com/category/storage"),
    ("PSU",          "https://www.ihavecpu.com/category/power-supply"),
    ("Case",         "https://www.ihavecpu.com/category/case"),
    ("Cooler",       "https://www.ihavecpu.com/category/heat-sink"),
    ("Monitor",      "https://www.ihavecpu.com/category/monitor"),
    ("Mouse",        "https://www.ihavecpu.com/category/mouse"),
    ("Keyboard",     "https://www.ihavecpu.com/category/keyboard"),
    ("Headset",      "https://www.ihavecpu.com/category/headphone"),
    ("Gaming Chair", "https://www.ihavecpu.com/category/chair"),
    ("Gaming Desk",  "https://www.ihavecpu.com/category/desk"),
]
IHC_SKIP = [
    "MOUSE PAD", "MOUSEPAD", "WEBCAM", "GAMEPAD", "JOYSTICK", "SPEAKER",
    "EXTERNAL HDD", "EXTERNAL SSD", "PROJECTOR", "PRINTER", "SCANNER",
    "UPS", "STABILIZER", "NETWORK", "ROUTER", "SWITCH", "ACCESS POINT",
    "NAS", "BY ORDER", "PRE ORDER", "CABLE", "HUB", "NOTEBOOK", "LAPTOP",
]

CID_MAP = {
    "cpu": "c01", "mainboard": "c02", "gpu": "c03", "vga": "c03",
    "ram": "c04", "ssd": "c05", "psu": "c06", "case": "c07",
    "liquid": "c08", "air cooler": "c09", "cooler": "c09",
    "mouse": "c10", "keyboard": "c11", "headset": "c12",
    "microphone": "c13", "monitor": "c14",
    "gaming chair": "c15", "chair": "c15",
    "gaming desk": "c16", "desk": "c16",
    "pc set": "c18", "computer set": "c18",
}

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def log(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))


def should_skip(name: str) -> bool:
    up = name.upper()
    return any(kw in up for kw in SKIP_KEYWORDS)


def is_pc_set_name(name: str) -> bool:
    up = (name or "").upper()
    return any(token in up for token in (
        "COMPUTER SET", "PC SET", "\u0e04\u0e2d\u0e21\u0e1b\u0e23\u0e30\u0e01\u0e2d\u0e1a",
    ))


def parse_price(text: str) -> int:
    if not text:
        return 0
    text = text.strip().replace(",", "").replace("฿", "").replace("THB", "").replace("baht", "").strip()
    m = re.search(r"\d+(?:\.\d+)?", text)
    if not m:
        return 0
    try:
        n = int(float(m.group(0)))
    except Exception:
        return 0
    return n if 200 <= n <= 500_000 else 0


PRICE_FLOORS = {
    "CPU": 500,
    "Mainboard": 700,
    "GPU": 1_000,
    "RAM": 200,
    "SSD": 200,
    "PSU": 300,
    "Case": 200,
    "Air Cooler": 200,
    "Liquid Cooler": 500,
    "Monitor": 500,
    "PC Set": 2_000,
}


def valid_product_price(category: str, price: int) -> bool:
    """Reject installment/discount amounts accidentally parsed as a sale price."""
    try:
        value = int(price)
    except (TypeError, ValueError):
        return False
    return PRICE_FLOORS.get(category, 200) <= value <= 500_000


def _plain_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html_lib.unescape(value or ""))
    return re.sub(r"\s+", " ", text).strip()


def extract_next_data(document: str) -> dict:
    """Read the server-rendered Next.js payload without executing page JavaScript."""
    match = re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        document or "", flags=re.S | re.I,
    )
    if not match:
        return {}
    try:
        return json.loads(match.group(1))
    except (TypeError, ValueError):
        try:
            return json.loads(html_lib.unescape(match.group(1)))
        except (TypeError, ValueError):
            return {}


def ihc_product_url(product_id, name: str) -> str:
    if not product_id:
        return ""
    slug = re.sub(r"\s+", "-", (name or "product").strip().lower())
    slug = re.sub(r"[-/]+", "-", slug).strip("-") or "product"
    return f"https://ihavecpu.com/product/{int(product_id)}/{quote(slug, safe='-.')}"


def ihc_product_description(product: dict) -> str:
    """Convert iHaveCPU's structured properties to auditable Key: Value lines."""
    lines: list[str] = []
    seen: set[str] = set()
    for prop in product.get("property") or []:
        key = (prop.get("filter_text") or prop.get("name_th") or prop.get("name_gb") or "").strip()
        values = []
        for detail in prop.get("detail") or []:
            value = (detail.get("name_th") or detail.get("name_gb") or "").strip()
            if value and value not in values:
                values.append(value)
        if key and values:
            line = f"{key}: {', '.join(values)}"
            if line not in seen:
                seen.add(line)
                lines.append(line)
    for label, field in (
        ("Summary", "size_guide_th"),
        ("Description", "description_th"),
    ):
        value = _plain_html(product.get(field) or "")
        if value and not (label == "Description" and len(value) < 10):
            line = f"{label}: {value}"
            if line not in seen:
                seen.add(line)
                lines.append(line)
    return "\n".join(lines)


def ihc_listing_products(document: str) -> list[dict]:
    data = extract_next_data(document)
    product = data.get("props", {}).get("pageProps", {}).get("product", {})
    return product.get("data", []) if isinstance(product, dict) else []


def ihc_detail_product(document: str) -> dict:
    data = extract_next_data(document)
    product = data.get("props", {}).get("pageProps", {}).get("product", {})
    return product if isinstance(product, dict) else {}


def combine_descriptions(*parts: str) -> str:
    """Keep concise structured facts first, followed by non-duplicate detail text."""
    result: list[str] = []
    compact_seen: set[str] = set()
    for part in parts:
        value = (part or "").strip()
        compact = re.sub(r"\s+", " ", value).lower()
        if not value or compact in compact_seen:
            continue
        compact_seen.add(compact)
        result.append(value)
    return "\n".join(result)


def advice_api_items(payload: dict) -> list[dict]:
    """Normalize Advice's public product API response."""
    output: list[dict] = []
    groups = (payload.get("data") or {}).get("product") or []
    for group in groups:
        for product in group.get("product") or []:
            raw_url = (product.get("product_url") or "").strip()
            url = raw_url if raw_url.startswith("http") else (
                "https://www.advice.co.th/product/" + raw_url.lstrip("/")
                if raw_url else ""
            )
            code = product.get("code") or ""
            output.append({
                "code": code,
                "name": (product.get("product") or product.get("name") or "").strip(),
                "price": product.get("price_sale_true") or product.get("price_srp") or product.get("price") or 0,
                "url": url,
                "img": product.get("pic_url") or (
                    f"https://img.advice.co.th/images_nas/pic_product4/{code}/{code}_1.jpg"
                    if code else ""
                ),
                "spec": (product.get("spec") or "").strip(),
            })
    return output


def get_cid(category: str) -> str:
    c = category.lower()
    for k, v in CID_MAP.items():
        if k in c:
            return v
    return "c01"


def make_pid(name: str, store: str) -> str:
    slug = re.sub(r"[^a-z0-9]", "", name.lower())[:12]
    h = hashlib.md5(f"{name}_{store}".encode()).hexdigest()[:8]
    return f"{slug}_{store[:3]}_{h}"


# Unit patterns to ignore in model codes
UNIT_PATTERN = re.compile(r'^\d+(\.\d+)?(GHZ|MHZ|MB|GB|TB|W|MM|RPM)$', re.IGNORECASE)
CORE_PATTERN = re.compile(r'^\d+[CT]$', re.IGNORECASE)

# Known GPU/CPU brands — must match between products
HW_BRANDS = [
    'ASUS', 'GIGABYTE', 'MSI', 'ZOTAC', 'GALAX', 'PALIT', 'INNO3D', 'POWERCOLOR',
    'SAPPHIRE', 'XFX', 'ASROCK', 'EVGA', 'PNY', 'COLORFUL', 'GAINWARD',
    'INTEL', 'AMD', 'RYZEN', 'CORE',
    'CORSAIR', 'GSKILL', 'KINGSTON', 'CRUCIAL', 'TEAMGROUP', 'ADATA',
    'SAMSUNG', 'WESTERN', 'SEAGATE', 'TOSHIBA', 'HYNIX',
    'SEASONIC', 'BE QUIET', 'ANTEC', 'COOLER MASTER', 'NOCTUA', 'DEEPCOOL',
    'LIAN LI', 'PHANTEKS', 'FRACTAL', 'NZXT', 'THERMALTAKE',
    'LOGITECH', 'RAZER', 'STEELSERIES', 'HYPERX', 'BENQ', 'DELL', 'LG', 'AOC', 'VIEWSONIC',
]


def extract_brand(name: str) -> str:
    """Extract the first known brand found in product name (uppercase)."""
    n = name.upper()
    # Retailers use both POWER COLOR and POWERCOLOR. Canonicalize the spaced
    # spelling before comparing brands across listings and product URLs.
    if re.search(r"\bPOWER\s+COLOR\b", n):
        return "POWERCOLOR"
    for brand in HW_BRANDS:
        if brand in n:
            return brand
    return ''


def extract_numeric_model(name: str) -> set:
    """Extract pure numeric tokens (e.g. 3050, 5050, 4070, 13600) — these must match exactly."""
    n = name.upper()
    n = re.sub(r'[\u0E00-\u0E7F]+', ' ', n)
    n = re.sub(r'[\-_/+,:]+', ' ', n)
    nums = set()
    for w in n.split():
        # Pure numbers 3+ digits (likely model numbers, not years/units)
        if re.fullmatch(r'\d{3,5}', w):
            nums.add(w)
    return nums


def _normalized_match(pattern: str, name: str) -> str:
    match = re.search(pattern, name.upper())
    return re.sub(r"[^A-Z0-9]", "", match.group(0)) if match else ""


def extract_category_identity(name: str, category: str) -> dict:
    """Extract fields that must agree before two listings can be merged."""
    cat = (category or "").lower()
    identity = {"brand": extract_brand(name)}
    if cat == "gpu":
        identity["model"] = _normalized_match(
            r"\b(?:RTX\s*PRO\s*\d{4}|RTX\s*\d{4}|RX\s*\d{4}|R\d{4})"
            r"(?:\s*(?:TI|SUPER|XT|XTX|GRE))?\b", name
        )
        vram = re.search(r"\b(\d{1,2})\s*GB\s*GDDR", name.upper())
        identity["vram_gb"] = int(vram.group(1)) if vram else None
        series_tokens = {
            token for token in (
                "PRIME", "TURBO", "DUAL", "TUF", "STRIX", "WINDFORCE", "AORUS",
                "GAMING", "VENTUS", "SUPRIM", "TRIO", "TWIN", "ICHILL", "PULSE",
                "PURE", "NITRO", "HELLHOUND", "REDDEVIL", "FIGHTER", "IGAME",
                "ULTRA", "BATTLEAX", "HOF", "EX", "SG", "X2", "X3",
                "REAPER", "CHALLENGER", "STEEL LEGEND", "POLAR", "WHITE",
                "PHANTOMLINK",
            )
            if re.search(rf"\b{token}\b", name.upper())
        }
        identity["variant"] = tuple(sorted(series_tokens))
    elif cat == "cpu":
        identity["model"] = _normalized_match(
            r"\b(?:CORE\s*ULTRA\s*[3579]\s*\d{3}[A-Z+]*|I[3579][ -]?\d{4,5}[A-Z]*|"
            r"RYZEN\s*[3579]\s*\d{4}[A-Z0-9]*)\b", name
        )
    elif cat == "psu":
        watt = re.search(r"\b(\d{3,4})\s*W\b", name.upper())
        identity["watt"] = int(watt.group(1)) if watt else None
    elif cat in ("ssd", "ram"):
        capacity = re.search(r"\b(\d+(?:\.\d+)?)\s*(TB|GB)\b", name.upper())
        if capacity:
            amount = float(capacity.group(1)) * (1024 if capacity.group(2) == "TB" else 1)
            identity["capacity_gb"] = int(amount)
        if cat == "ram":
            kit = re.search(r"\(\s*(\d{1,3})(?:GB)?\s*[X×]\s*(\d{1,2})\s*\)", name.upper())
            identity["kit"] = (int(kit.group(1)), int(kit.group(2))) if kit else None
    elif cat == "mainboard":
        chipset = re.search(r"\b([ABHXZW]\d{3}[A-Z]*)\b", name.upper())
        identity["chipset"] = chipset.group(1) if chipset else ""
        memory = re.search(r"\bDDR\s*([45])\b", name.upper())
        identity["memory_type"] = f"DDR{memory.group(1)}" if memory else ""
        if chipset:
            tail = name.upper()[chipset.end():]
            words = re.findall(r"[A-Z0-9]+", tail)
            noise = {
                "AMD", "INTEL", "SOCKET", "DDR4", "DDR5", "ATX", "MATX", "MICRO",
                "MINI", "REV", "WIFI", "WIFI6", "WIFI6E", "MAINBOARD", "MOTHERBOARD",
            }
            identity["variant"] = tuple(
                word for word in words
                if word not in noise and not re.fullmatch(r"\d+", word)
            )[:3]
    return identity


def has_identity_conflict(name1: str, name2: str, category: str) -> bool:
    """True when two listings contain explicit, incompatible identities."""
    first = extract_category_identity(name1, category)
    second = extract_category_identity(name2, category)
    if first.get("brand") and second.get("brand") and first["brand"] != second["brand"]:
        return True
    for field in ("model", "watt", "capacity_gb", "chipset", "vram_gb", "kit"):
        if first.get(field) and second.get(field) and first[field] != second[field]:
            return True
    if (category or "").lower() in ("mainboard", "gpu"):
        v1, v2 = set(first.get("variant") or ()), set(second.get("variant") or ())
        if (category or "").lower() == "gpu":
            distinctive = {
                "PRIME", "TURBO", "DUAL", "TUF", "STRIX", "WINDFORCE", "AORUS",
                "VENTUS", "SUPRIM", "TRIO", "ICHILL", "PULSE", "PURE", "NITRO",
                "HELLHOUND", "REDDEVIL", "FIGHTER", "IGAME", "BATTLEAX", "HOF",
                "REAPER", "CHALLENGER", "STEEL LEGEND",
            }
            d1, d2 = v1 & distinctive, v2 & distinctive
            if d1 and d2 and d1.isdisjoint(d2):
                return True
            strict_variant = {"POLAR", "WHITE"}
            if (v1 & strict_variant) != (v2 & strict_variant):
                return True
        overlap = len(v1 & v2) / min(len(v1), len(v2)) if v1 and v2 else 1.0
        if v1 and v2 and overlap < 0.5:
            return True
    return False


def get_product_signature(name: str):
    n = name.upper()
    n = re.sub(r'[\u0E00-\u0E7F]+', ' ', n)
    n = re.sub(r'\(.*?\)|\[.*?\]', ' ', n)
    n = re.sub(r'[\-_/+,:]+', ' ', n)
    
    words = [w for w in n.split() if w]
    model_codes = set()
    for w in words:
        if UNIT_PATTERN.match(w) or CORE_PATTERN.match(w):
            continue
        if w in {'3Y', '5Y', '2Y', '1Y', 'DDR4', 'DDR5', 'WARRANTY'}:
            continue
        if re.search(r'\d', w):
            model_codes.add(w)
            
    tokens = set()
    for w in words:
        if w not in {'CPU', 'VGA', 'GPU', 'RAM', 'SSD', 'PSU', 'CASE', 'MONITOR', 'KEYBOARD', 'MOUSE', 'HEADSET', 'MAINBOARD', 'MOTHERBOARD', 'NEXT', 'TRAY', 'BOX', '3Y', '5Y', '2Y', '1Y', 'WARRANTY', 'SYSTEM'}:
            if not UNIT_PATTERN.match(w) and not CORE_PATTERN.match(w):
                tokens.add(w)
                
    return frozenset(model_codes), frozenset(tokens)


def token_similarity(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def is_same_product(p1_name: str, p1_cat: str, p2_name: str, p2_cat: str) -> bool:
    c1, c2 = (p1_cat or '').lower(), (p2_cat or '').lower()
    if c1 and c2 and c1 != c2:
        if not ('cooler' in c1 and 'cooler' in c2):
            return False

    if p1_name.strip().upper() == p2_name.strip().upper():
        return True

    # Explicit model, capacity, wattage and brand conflicts always win over
    # fuzzy token similarity. This prevents 650W/750W PSUs and sibling GPU or
    # motherboard models from sharing prices and source details.
    if has_identity_conflict(p1_name, p2_name, p1_cat or p2_cat):
        return False

    # --- Guard 2: Pure numeric model numbers must match exactly ---
    # e.g. 3050 vs 5050, 4070 vs 4080 — these must NEVER merge
    nums1 = extract_numeric_model(p1_name)
    nums2 = extract_numeric_model(p2_name)
    if nums1 and nums2 and nums1 != nums2:
        return False

    m1, t1 = get_product_signature(p1_name)
    m2, t2 = get_product_signature(p2_name)

    if m1 and m2:
        # SKU tokens must contain both letters AND digits (e.g. RTX3050, i5-13600K)
        # Exclude pure-alpha tokens like "OC", "V2", "DUAL" from sku matching
        sku_m1 = {x for x in m1 if re.search(r'[A-Z]', x) and re.search(r'\d', x)
                  and not re.fullmatch(r'[A-Z]+\d', x)}  # exclude V2, V3 etc
        sku_m2 = {x for x in m2 if re.search(r'[A-Z]', x) and re.search(r'\d', x)
                  and not re.fullmatch(r'[A-Z]+\d', x)}
        
        if sku_m1 and sku_m2:
            if sku_m1 == sku_m2:
                sim = token_similarity(t1, t2)
                if sim >= 0.30:  # raised from 0.25
                    return True
            else:
                return False
        
        intersect = m1 & m2
        if len(intersect) >= 2:
            sim = token_similarity(t1, t2)
            if sim >= 0.50:  # raised from 0.35
                return True
        elif len(intersect) == 1:
            sim = token_similarity(t1, t2)
            if sim >= 0.60:  # raised from 0.40
                return True

    sim = token_similarity(t1, t2)
    if sim >= 0.72:  # raised from 0.65
        return True

    return False


def clean_ihc_name(name: str) -> str:
    name = re.sub(r"^\[.*?\]\s*", "", name).strip()
    m = re.match(r"^([A-Z0-9/\-\. ]+?)\s*\([^\)]+\)\s*(.*)", name)
    if m:
        return (m.group(1).strip() + " " + m.group(2).strip()).strip()
    return name


def detect_jib_cat(name: str):
    up = name.upper()
    for skip in JIB_SKIP_PREFIXES:
        if up.startswith(skip):
            return None
    for prefix, cat in JIB_PREFIX_MAP.items():
        if up.startswith(prefix):
            return cat
    return None


def detect_obvious_category(name: str, fallback: str) -> str:
    """Correct broad search results that clearly belong to another category."""
    if is_pc_set_name(name):
        return "PC Set"
    detected = detect_jib_cat(name)
    if detected:
        return detected
    up = (name or "").upper()
    for token, category in (
        ("KEYBOARD", "Keyboard"), ("MOUSE", "Mouse"),
        ("MAINBOARD", "Mainboard"), ("MOTHERBOARD", "Mainboard"),
        ("POWER SUPPLY", "PSU"), ("GRAPHIC CARD", "GPU"),
    ):
        if re.search(rf"\b{re.escape(token)}\b", up):
            return category
    return fallback


def _source_slug(url: str) -> str:
    """Return the human-readable product slug from a store URL."""
    path = unquote(urlparse(url).path or "")
    parts = [part for part in path.split("/") if part and not part.isdigit()]
    return parts[-1] if parts else path


def source_url_conflicts(name: str, url: str, category: str) -> bool:
    """Detect an obvious name/URL mismatch before visiting or storing a URL.

    Store listing pages occasionally return a stale link from an adjacent card.
    Keep the product row, but never attach that other model's detail page to it.
    """
    if not name or not url:
        return False
    slug = _source_slug(url)
    if len(slug) < 5:
        return False
    expected = extract_category_identity(name, category)
    actual = extract_category_identity(slug, category)
    if expected.get("brand") and actual.get("brand") and expected["brand"] != actual["brand"]:
        return True
    for field in ("model", "watt", "capacity_gb", "chipset", "vram_gb", "kit", "memory_type"):
        if expected.get(field) and actual.get(field) and expected[field] != actual[field]:
            return True
    if (category or "").lower() in ("mainboard", "gpu"):
        first = set(expected.get("variant") or ())
        second = set(actual.get("variant") or ())
        if (category or "").lower() == "gpu":
            distinctive = {
                "PRIME", "TURBO", "DUAL", "TUF", "STRIX", "WINDFORCE", "AORUS",
                "VENTUS", "SUPRIM", "TRIO", "ICHILL", "PULSE", "PURE", "NITRO",
                "HELLHOUND", "REDDEVIL", "FIGHTER", "IGAME", "BATTLEAX", "HOF",
                "REAPER", "CHALLENGER", "STEEL LEGEND",
            }
            d1, d2 = first & distinctive, second & distinctive
            if d1 and d2 and d1.isdisjoint(d2):
                return True
            strict_variant = {"POLAR", "WHITE"}
            if (first & strict_variant) != (second & strict_variant):
                return True
        overlap = len(first & second) / min(len(first), len(second)) if first and second else 1.0
        if first and second and overlap < 0.5:
            return True
    return False


def source_url_score(name: str, url: str, category: str) -> int:
    """Score a candidate href so a card's link follows its displayed name."""
    if source_url_conflicts(name, url, category):
        return -1000
    wanted = set(re.findall(r"[A-Z0-9]{3,}", re.sub(r"[^A-Z0-9]+", " ", name.upper())))
    slug = _source_slug(url).upper()
    found = set(re.findall(r"[A-Z0-9]{3,}", re.sub(r"[^A-Z0-9]+", " ", slug)))
    return len(wanted & found)


# ─────────────────────────────────────────────────────────────────────────────
# DB Setup
# ─────────────────────────────────────────────────────────────────────────────
def setup_db(conn: sqlite3.Connection):
    cur = conn.cursor()
    new_cols = [
        ("url_advice",    "TEXT DEFAULT ''"),
        ("url_jib",       "TEXT DEFAULT ''"),
        ("url_ihavecpu",  "TEXT DEFAULT ''"),
        ("desc_advice",   "TEXT DEFAULT ''"),
        ("desc_jib",      "TEXT DEFAULT ''"),
        ("desc_ihavecpu", "TEXT DEFAULT ''"),
        ("updated_at",    "TEXT DEFAULT ''"),
    ]
    cur.execute("PRAGMA table_info(products)")
    existing = {row[1] for row in cur.fetchall()}
    for col, defn in new_cols:
        if col not in existing:
            cur.execute(f"ALTER TABLE products ADD COLUMN {col} {defn}")
            log(f"[DB] Added column: {col}")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id  TEXT NOT NULL,
            store       TEXT NOT NULL,
            price       REAL NOT NULL,
            captured_at TEXT NOT NULL
        )
    """)
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_ph_prod ON price_history(product_id, captured_at)"
    )
    conn.commit()


def repair_pc_set_categories(conn: sqlite3.Connection) -> int:
    """Move obvious computer-set rows out of component categories."""
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT product_id, p_name, category FROM products "
        "WHERE upper(p_name) LIKE '%COMPUTER SET%' "
        "OR upper(p_name) LIKE '%PC SET%' "
        "OR p_name LIKE '%\u0e04\u0e2d\u0e21\u0e1b\u0e23\u0e30\u0e01\u0e2d\u0e1a%'"
    ).fetchall()
    changed = 0
    for pid, name, category in rows:
        if (category or "").strip().lower() == "pc set":
            continue
        cur.execute(
            "UPDATE products SET category='PC Set', cid='c18', updated_at=? WHERE product_id=?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pid),
        )
        changed += 1
    if changed:
        conn.commit()
        log(f"  [repair] reclassified {changed} computer-set rows as PC Set")
    return changed


def repair_obvious_product_categories(conn: sqlite3.Connection) -> int:
    """Repair rows polluted by broad store-search results."""
    cur = conn.cursor()
    changed = 0
    rows = cur.execute("SELECT product_id, p_name, category FROM products").fetchall()
    for pid, name, category in rows:
        detected = detect_obvious_category(name or "", category or "")
        if not detected or detected == (category or ""):
            continue
        cur.execute(
            "UPDATE products SET category=?, cid=?, updated_at=? WHERE product_id=?",
            (detected, get_cid(detected), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pid),
        )
        changed += 1
    if changed:
        conn.commit()
        log(f"  [repair] corrected categories for {changed} product rows")
    return changed


def repair_conflicting_source_data(conn: sqlite3.Connection) -> int:
    """Clear stale store URLs/details that point at a different model.

    This repairs rows produced by older scraper runs before the next detail
    pass, without deleting prices or the canonical product record.
    """
    cur = conn.cursor()
    repaired = 0
    for store, price_col, url_col, desc_col in (
        ("advice", "price_advice", "url_advice", "desc_advice"),
        ("jib", "price_jib", "url_jib", "desc_jib"),
        ("ihavecpu", "price_ihavecpu", "url_ihavecpu", "desc_ihavecpu"),
    ):
        rows = cur.execute(
            f"SELECT product_id, p_name, category, {url_col} FROM products "
            f"WHERE {url_col} IS NOT NULL AND trim({url_col}) != ''"
        ).fetchall()
        for pid, name, category, url in rows:
            if source_url_conflicts(name or "", url or "", category or ""):
                cur.execute(
                    f"UPDATE products SET {price_col} = 0, {url_col} = '', {desc_col} = '' WHERE product_id = ?",
                    (pid,),
                )
                _refresh_lowest_price(cur, pid)
                repaired += 1
                log(f"  [repair] cleared stale {store} URL: {(name or '')[:70]}")
    conn.commit()
    if repaired:
        log(f"  [repair] cleared {repaired} mismatched store URL/detail records")
    return repaired


def repair_implausible_prices(conn: sqlite3.Connection) -> int:
    """Remove stale installment/discount amounts left by older scraper versions."""
    cur = conn.cursor()
    repaired = 0
    for category, floor in PRICE_FLOORS.items():
        rows = cur.execute(
            "SELECT product_id FROM products WHERE category=? AND ("
            "(price_advice>0 AND price_advice<?) OR "
            "(price_jib>0 AND price_jib<?) OR "
            "(price_ihavecpu>0 AND price_ihavecpu<?))",
            (category, floor, floor, floor),
        ).fetchall()
        for (pid,) in rows:
            cur.execute(
                "UPDATE products SET "
                "price_advice=CASE WHEN price_advice>0 AND price_advice<? THEN 0 ELSE price_advice END, "
                "price_jib=CASE WHEN price_jib>0 AND price_jib<? THEN 0 ELSE price_jib END, "
                "price_ihavecpu=CASE WHEN price_ihavecpu>0 AND price_ihavecpu<? THEN 0 ELSE price_ihavecpu END "
                "WHERE product_id=?",
                (floor, floor, floor, pid),
            )
            _refresh_lowest_price(cur, pid)
            repaired += 1
    if repaired:
        conn.commit()
        log(f"  [repair] cleared implausible prices from {repaired} product rows")
    return repaired


def _record_price_history(cur: sqlite3.Cursor, pid: str, store: str, price: int):
    if price > 0:
        cur.execute(
            "INSERT INTO price_history (product_id, store, price, captured_at) VALUES (?,?,?,?)",
            (pid, store, price, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )


# ─────────────────────────────────────────────────────────────────────────────
# SmartMatcher — deduplication engine
# ─────────────────────────────────────────────────────────────────────────────
class SmartMatcher:
    def __init__(self, cur: sqlite3.Cursor):
        self.cur = cur
        # List of (product_id, p_name, category)
        self._items: list[tuple[str, str, str]] = []
        self._exact_cache: dict[str, str] = {}
        self._load_existing()

    def _load_existing(self):
        """Pre-load existing products into memory caches."""
        self.cur.execute("SELECT product_id, p_name, category FROM products")
        for pid, pname, cat in self.cur.fetchall():
            if not pname:
                continue
            self._exact_cache[pname.strip().upper()] = pid
            self._items.append((pid, pname, cat or ""))

    def find(self, name: str, cat: str = "") -> str | None:
        """Return product_id of a matching existing product, or None."""
        if not name:
            return None
        key = name.strip().upper()

        if key in self._exact_cache:
            return self._exact_cache[key]

        for pid, existing_name, existing_cat in self._items:
            if is_same_product(name, cat, existing_name, existing_cat):
                return pid

        return None

    def register(self, pid: str, name: str, cat: str = ""):
        """Register newly inserted product in cache."""
        self._exact_cache[name.strip().upper()] = pid
        self._items.append((pid, name, cat))


# ─────────────────────────────────────────────────────────────────────────────
# Upsert helper
# ─────────────────────────────────────────────────────────────────────────────
def upsert_product(cur: sqlite3.Cursor, matcher: SmartMatcher, p: dict) -> bool:
    """
    Insert or update a product record with smart deduplication.
    """
    name  = (p.get("name") or "").strip()
    price = int(p.get("price") or 0)
    store = p.get("store") or ""
    cat   = p.get("category") or ""
    img   = (p.get("img_url") or "").strip()
    url   = (p.get("url") or "").strip()
    desc  = (p.get("description") or "").strip()

    if url and source_url_conflicts(name, url, cat):
        log(f"    [url mismatch] {store}: {name[:70]} -> {_source_slug(url)[:90]}")
        url = ""

    if not name or not price:
        return False
    if should_skip(name):
        return False
    if not valid_product_price(cat, price):
        log(f"    [invalid price] {store}: {cat} {name[:65]} -> {price:,} B")
        return False

    cid       = get_cid(cat)
    now_str   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    price_col = {"advice": "price_advice", "jib": "price_jib", "ihavecpu": "price_ihavecpu"}.get(store, "price_advice")
    url_col   = {"advice": "url_advice",   "jib": "url_jib",   "ihavecpu": "url_ihavecpu"}.get(store, "url_advice")
    desc_col  = {"advice": "desc_advice",  "jib": "desc_jib",  "ihavecpu": "desc_ihavecpu"}.get(store, "desc_advice")

    pid = matcher.find(name, cat)

    if pid:
        cur.execute(f"""
            UPDATE products SET
                {price_col} = ?,
                {url_col}   = CASE WHEN ? != '' THEN ? ELSE {url_col} END,
                {desc_col}  = CASE WHEN ? != '' THEN ? ELSE {desc_col} END,
                p_price     = CASE WHEN p_price = 0 THEN ? ELSE p_price END,
                img_url     = CASE WHEN ? != '' AND (img_url IS NULL OR img_url = '') THEN ? ELSE img_url END,
                p_description = CASE WHEN (p_description IS NULL OR p_description = '') AND ? != '' THEN ? ELSE p_description END,
                specs       = CASE WHEN (specs IS NULL OR specs = '') AND COALESCE({desc_col}, '') != '' THEN {desc_col} ELSE specs END,
                updated_at  = ?
            WHERE product_id = ?
        """, (
            price,
            url, url,
            desc, desc,
            price,
            img, img,
            desc, desc,
            now_str,
            pid,
        ))
        _refresh_lowest_price(cur, pid)
        _record_price_history(cur, pid, store, price)
        return False
    else:
        pid = make_pid(name, store)
        cur.execute("""
            INSERT OR IGNORE INTO products
            (product_id, p_name, p_description, p_price,
             price_advice, price_jib, price_ihavecpu,
             url_advice, url_jib, url_ihavecpu,
             desc_advice, desc_jib, desc_ihavecpu,
             p_stock, cid, category, img_url, specs, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            pid, name, desc, price,
            price if store == "advice"   else 0,
            price if store == "jib"      else 0,
            price if store == "ihavecpu" else 0,
            url   if store == "advice"   else "",
            url   if store == "jib"      else "",
            url   if store == "ihavecpu" else "",
            desc  if store == "advice"   else "",
            desc  if store == "jib"      else "",
            desc  if store == "ihavecpu" else "",
            99, cid, cat, img, desc,
            now_str, now_str,
        ))
        _record_price_history(cur, pid, store, price)
        matcher.register(pid, name, cat)
        return True


def _refresh_lowest_price(cur: sqlite3.Cursor, pid: str) -> int:
    row = cur.execute(
        "SELECT price_advice, price_jib, price_ihavecpu FROM products WHERE product_id=?",
        (pid,),
    ).fetchone()
    prices = [int(value) for value in (row or ()) if value and value > 0]
    lowest = min(prices) if prices else 0
    cur.execute("UPDATE products SET p_price=? WHERE product_id=?", (lowest, pid))
    return lowest


def needs_detail(cur: sqlite3.Cursor, matcher: SmartMatcher,
                 name: str, category: str, store: str) -> bool:
    """Avoid revisiting a product whose description and image are already cached."""
    pid = matcher.find(name, category)
    if not pid:
        return True
    desc_col = {"advice": "desc_advice", "jib": "desc_jib",
                "ihavecpu": "desc_ihavecpu"}.get(store, "p_description")
    row = cur.execute(
        f"SELECT {desc_col}, img_url FROM products WHERE product_id = ?", (pid,)
    ).fetchone()
    if not row:
        return True
    return len((row[0] or "").strip()) < 30 or not (row[1] or "").strip()


# ─────────────────────────────────────────────────────────────────────────────
# fetch_detail_page — visit product URL to get description + better image
# ─────────────────────────────────────────────────────────────────────────────
_DESC_SELECTORS = [
    # iHaveCPU
    "div.product-description", "div.description", "#product-description",
    "[class*='product-spec']", "[class*='spec-content']",
    # iHaveCPU renders the current product's facts in a plain table.
    "div.table-wrapper", "table",
    # JIB
    "#product-description", "div#tab_description", "#detail_spec",
    "table.table-spec", "div.product-detail-content",
    # Advice
    ".spec-content", ".spec-list", "div.product-spec", "table.spec-table",
    # Generic
    "[class*='description']", "[class*='detail']",
    "div.tabs-content", "div.tab-content",
    "#tab-description", "#tab-spec",
    "#specification", "#specifications", "#product-specification",
    ".product-specification", ".product-specifications", ".specification",
    ".product-info-detail", ".product-detail-info", ".product-detail__description",
    "article", "main [role='main']", "main",
]
_IMG_SELECTORS = [
    # iHaveCPU
    "img.product-main-img", "img#main-image", "img#mainImage",
    # JIB
    "img#main_img", "img#bigimage", "div#bigimage img",
    # Advice
    "img.main-product-image", "img#main-product-img",
    # Generic
    "div.product-gallery img:first-child",
    "div.product-images img:first-child",
    "div.swiper-slide:first-child img",
    "[class*='product-image'] img",
    "[class*='gallery'] img",
]


def detail_description_is_relevant(name: str, description: str, category: str) -> bool:
    """Reject cookie banners, related-product cards, and another model's specs."""
    text = (description or "").strip()
    if len(text) < 30:
        return False
    low = text.lower()
    if low.startswith(("{", "[")) and '"@type"' in low:
        return False
    if any(term in low for term in (
        "cookie", "consent", "privacy policy",
        "\u0e02\u0e49\u0e2d\u0e21\u0e39\u0e25\u0e2a\u0e48\u0e27\u0e19\u0e1a\u0e38\u0e04\u0e04\u0e25",
        "\u0e40\u0e23\u0e35\u0e22\u0e19\u0e23\u0e39\u0e49\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e40\u0e15\u0e34\u0e21",
    )):
        return False
    if name:
        compact_text = re.sub(r"[^a-z0-9]+", "", text.lower())
        compact_name = re.sub(r"[^a-z0-9]+", "", name.lower())
        if compact_text == compact_name or (
            len(text) < 140 and compact_name and compact_name in compact_text
        ):
            return False
    if name and category:
        if category.lower() == "mainboard":
            expected = extract_category_identity(name, category)
            actual = extract_category_identity(text, category)
            expected_chipset = expected.get("chipset", "")
            actual_chipset = actual.get("chipset", "")
            if (expected_chipset and actual_chipset and
                    not (expected_chipset.startswith(actual_chipset) or
                         actual_chipset.startswith(expected_chipset))):
                return False
            if (expected.get("memory_type") and actual.get("memory_type") and
                    expected["memory_type"] != actual["memory_type"]):
                return False
        elif has_identity_conflict(name, text, category):
            return False
    return True


async def fetch_ihc_detail_http(client: httpx.AsyncClient, url: str,
                                expected_name: str = "", category: str = "") -> tuple[str, str]:
    try:
        response = await client.get(url)
        response.raise_for_status()
        product = ihc_detail_product(response.text)
        actual_name = product.get("name_th") or product.get("name_gb") or ""
        if not product or (expected_name and actual_name and
                           has_identity_conflict(expected_name, actual_name, category)):
            return "", ""
        desc = ihc_product_description(product)
        pictures = product.get("picture") or []
        img = ""
        if pictures:
            img = pictures[0].get("pic_800") or pictures[0].get("pic_150") or ""
        return desc, img
    except Exception as e:
        log(f"      [iHaveCPU HTTP detail err] {str(e)[:100]}")
        return "", ""


async def fetch_detail_page(page, url: str, expected_name: str = "",
                            category: str = "", timeout_ms: int = 20000,
                            settle_ms: int = 1800,
                            http_client: httpx.AsyncClient | None = None) -> tuple[str, str]:
    """
    Visit a product detail page and extract (description, image_url).
    """
    desc = ""
    img  = ""
    if not url or url.startswith("https://www.advice.co.th/search"):
        return desc, img
    if "ihavecpu.com" in url.lower() and http_client is not None:
        return await fetch_ihc_detail_http(http_client, url, expected_name, category)
    try:
        await page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
        # Allow client-rendered specs/images to settle without waiting several
        # seconds for every product page. Selectors below still fall back to
        # meta description/og:image when a page is slow or partially blocked.
        await page.wait_for_timeout(settle_ms)
        if "ihavecpu.com" in url.lower():
            try:
                await page.wait_for_selector("div.table-wrapper table", timeout=6000)
            except Exception:
                pass

        # Some JIB/iHaveCPU pages keep specifications behind a tab. Clicking
        # only tab-like controls exposes the content without triggering menus.
        for sel in ("[role='tab']", ".tab button", ".tabs li", ".nav-tabs a", "button"):
            try:
                for el in await page.query_selector_all(sel):
                    label = (await el.inner_text()).strip().lower()
                    if any(word in label for word in ("spec", "detail", "description", "รายละเอียด", "ข้อมูลสินค้า", "คุณสมบัติ")):
                        if await el.is_visible():
                            await el.click(timeout=1200)
                            await page.wait_for_timeout(350)
                    if any(word in label for word in (
                        "\u0e23\u0e32\u0e22\u0e25\u0e30\u0e40\u0e2d\u0e35\u0e22\u0e14",
                        "\u0e02\u0e49\u0e2d\u0e21\u0e39\u0e25\u0e2a\u0e34\u0e19\u0e04\u0e49\u0e32",
                        "\u0e04\u0e38\u0e13\u0e2a\u0e21\u0e1a\u0e31\u0e15\u0e34",
                    )):
                        if await el.is_visible():
                            await el.click(timeout=1200)
                            await page.wait_for_timeout(350)
            except Exception:
                pass

        # Prefer structured specification blocks. Score candidates instead of
        # stopping at the first generic `.detail` wrapper, which is often only
        # the product title/price shell.
        candidates: list[tuple[int, str]] = []
        if "ihavecpu.com" in url.lower():
            # iHaveCPU's related-product cards also use classes containing
            # `detail`/`description`; the plain table is the current product's
            # authoritative specification block.
            selectors = (
                "div.table-wrapper", "table", "[class*='product-spec']",
                "[class*='spec-content']", "meta[name='description']",
            )
        else:
            selectors = _DESC_SELECTORS
        for sel in selectors:
            try:
                for el in await page.query_selector_all(sel):
                    t = (await el.inner_text()).strip()
                    if len(t) < 30:
                        continue
                    if len(t) > 18000:
                        t = t[:18000]
                    low = t.lower()
                    score = min(len(t), 6000)
                    score += sum(180 for word in (
                        "spec", "socket", "ddr", "watt", "dimension", "รายละเอียด",
                        "คุณสมบัติ", "การรับประกัน", "interface", "capacity",
                    ) if word in low)
                    keyword_hits = sum(1 for word in (
                        "spec", "socket", "ddr", "watt", "dimension", "brand", "model",
                        "form factor", "chipset", "memory type", "continuous power", "warranty",
                        "interface", "capacity",
                    ) if word in low)
                    score += keyword_hits * 180
                    if sel in ("main", "article", "main [role='main']"):
                        score -= 900
                    if ("detail" in sel or "description" in sel) and keyword_hits == 0:
                        score -= 900
                    if sel in ("table", "div.table-wrapper"):
                        score += 350
                    candidates.append((score, t))
            except Exception:
                pass
        if candidates:
            desc = max(candidates, key=lambda item: item[0])[1]
        if desc and not detail_description_is_relevant(expected_name, desc, category):
            desc = ""
        if not desc:
            try:
                m = await page.query_selector('meta[name="description"]')
                if m:
                    c = (await m.get_attribute("content") or "").strip()
                    if len(c) > 30 and detail_description_is_relevant(expected_name, c, category):
                        desc = c
            except Exception:
                pass
        if not desc:
            try:
                m = await page.query_selector('meta[property="og:description"]')
                if m:
                    c = (await m.get_attribute("content") or "").strip()
                    if len(c) > 30 and detail_description_is_relevant(expected_name, c, category):
                        desc = c
            except Exception:
                pass
        if not desc:
            # Product pages rendered by React/Next often expose the full data
            # in JSON-LD even when the visible tab is not server-rendered.
            try:
                for script in await page.query_selector_all("script[type='application/ld+json']"):
                    raw = (await script.inner_text()).strip()
                    if len(raw) < 30:
                        continue
                    if len(raw) > 18000:
                        raw = raw[:18000]
                    try:
                        data = json.loads(raw)
                        if isinstance(data, dict) and isinstance(data.get("description"), str):
                            desc = data["description"].strip()
                        elif isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict) and isinstance(item.get("description"), str):
                                    desc = item["description"].strip()
                                    break
                        if desc and not detail_description_is_relevant(expected_name, desc, category):
                            desc = ""
                    except (TypeError, ValueError):
                        if detail_description_is_relevant(expected_name, raw, category):
                            desc = raw
                    break
            except Exception:
                pass

        for sel in _IMG_SELECTORS:
            try:
                el = await page.query_selector(sel)
                if el:
                    for attr in ["src", "data-src", "data-lazy", "data-original"]:
                        v = (await el.get_attribute(attr) or "").strip()
                        if v and v.startswith("http") and not v.endswith(".gif"):
                            img = v
                            break
                if img:
                    break
            except Exception:
                pass
        if not img:
            try:
                m = await page.query_selector('meta[property="og:image"]')
                if m:
                    c = (await m.get_attribute("content") or "").strip()
                    if c.startswith("http"):
                        img = c
            except Exception:
                pass
    except Exception as e:
        log(f"      [detail err] {str(e)[:80]}")
    return desc, img


# ─────────────────────────────────────────────────────────────────────────────
# Scraper: Advice (JSON API)
# ─────────────────────────────────────────────────────────────────────────────
async def scrape_advice(conn: sqlite3.Connection, matcher: SmartMatcher,
                        pages: int = 3, fetch_details: bool = False):
    import urllib.parse
    cur = conn.cursor()
    total_new = total_upd = 0

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        ctx = await browser.new_context(user_agent=UA, locale="th-TH")
        detail_pg = await ctx.new_page()
        api_client = httpx.AsyncClient(
            headers={"User-Agent": UA, "Accept": "application/json"},
            follow_redirects=True,
            timeout=httpx.Timeout(30.0, connect=15.0),
        )
        try:
            guest_response = await api_client.post(
                "https://prodbackadvice.advice.in.th/api/v1.0.0/user/guest",
                json={"type": "online"},
            )
            guest_response.raise_for_status()
            token = ((guest_response.json().get("data") or {}).get("token") or "").strip()
        except Exception as e:
            token = ""
            log(f"  [Advice] guest token error: {str(e)[:120]}")
        api_headers = {"Authorization": f"Bearer {token}"} if token else {}

        seen_codes: set[str] = set()

        for cat_name, keywords in ADVICE_SEARCH_KW:
            cat_new = cat_upd = 0
            for kw in keywords:
                for pn in range(pages):
                    skip = pn * 12
                    try:
                        api_response = await api_client.post(
                            ADVICE_API,
                            headers=api_headers,
                            json={
                                "category": "search", "category_sub": "", "product": "",
                                "keyword": kw, "take": 24, "skip": skip,
                                "refSearch": "", "page": "product",
                                "arr_filter_brand": [], "arr_filter_ict": [],
                                "arr_filter_price_ict": [], "arr_filter_cate": [],
                                "addView": False, "group_end": False,
                            },
                        )
                        api_response.raise_for_status()
                        items = advice_api_items(api_response.json())
                    except Exception as e:
                        log(f"    [Advice] HTTP API err ({kw} p{pn}): {str(e)[:120]}")
                        break
                    if not items:
                        break

                    page_new = 0
                    for it in items:
                        code  = it.get("code") or ""
                        name  = (it.get("name") or "").strip()
                        price = int(it.get("price") or 0)
                        url   = it.get("url") or ""
                        img   = it.get("img") or ""

                        if not name or not price:
                            continue
                        if code and code in seen_codes:
                            continue
                        if code:
                            seen_codes.add(code)

                        if not url:
                            url = "https://www.advice.co.th/search?keyword=" + urllib.parse.quote(name[:60])

                        actual_cat = detect_obvious_category(name, cat_name)
                        det_desc = ""
                        det_img  = ""
                        if (fetch_details and url and not url.startswith("https://www.advice.co.th/search")
                                and needs_detail(cur, matcher, name, actual_cat, "advice")):
                            det_desc, det_img = await fetch_detail_page(
                                detail_pg, url, name, actual_cat
                            )
                            await asyncio.sleep(random.uniform(0.7, 1.4))

                        is_new = upsert_product(cur, matcher, {
                            "name": name, "price": price,
                            "img_url": det_img or img, "url": url,
                            "category": actual_cat, "store": "advice",
                            # Advice's API spec is the most reliable source for
                            # compatibility fields. Keep it even when the page
                            # also exposes a longer marketing description.
                            "description": combine_descriptions(
                                it.get("spec") or "", det_desc
                            ),
                        })
                        if is_new:
                            cat_new += 1
                        else:
                            cat_upd += 1
                        page_new += 1

                    conn.commit()
                    if page_new == 0:
                        break

            total_new += cat_new
            total_upd += cat_upd
            log(f"  [Advice] {cat_name}: +{cat_new} new, ~{cat_upd} updated")

        await api_client.aclose()
        await browser.close()

    log(f"  [Advice] TOTAL: {total_new} new | {total_upd} merged into existing")
    return total_new, total_upd


# ─────────────────────────────────────────────────────────────────────────────
# Scraper: JIB (HTML category pages)
# ─────────────────────────────────────────────────────────────────────────────
async def scrape_jib(conn: sqlite3.Connection, matcher: SmartMatcher,
                     pages: int = 5, fetch_details: bool = False):
    cur = conn.cursor()
    total_new = total_upd = 0

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        ctx = await browser.new_context(user_agent=UA, viewport={"width": 1280, "height": 800})
        await ctx.add_init_script(ANTI_BOT)
        page = await ctx.new_page()
        detail_pg = await ctx.new_page()

        for cat_name, base_url in JIB_CATS:
            if any(kw in base_url.lower() for kw in NOTEBOOK_URL_KW):
                log(f"  [JIB] SKIP notebook cat: {cat_name}")
                continue

            cat_new = cat_upd = 0
            for pn in range(1, pages + 1):
                url = base_url if pn == 1 else f"{base_url}/{pn}"
                log(f"  [JIB] {cat_name} p{pn}")

                try:
                    await page.goto(url, timeout=40000, wait_until="domcontentloaded")
                    await page.wait_for_timeout(4000)
                except Exception as e:
                    log(f"    err: {e}")
                    break

                cards = await page.query_selector_all("div.divboxpro")
                if not cards:
                    cards = await page.query_selector_all("div[class*='divboxpro']")
                if not cards:
                    log("    no cards")
                    break

                count = 0
                for card in cards:
                    try:
                        ne = await card.query_selector("span.promo_name")
                        if not ne:
                            ne = await card.query_selector("[class*='name']")
                        if not ne:
                            continue
                        name = (await ne.inner_text()).strip()
                        if not name or should_skip(name):
                            continue

                        actual_cat = "PC Set" if is_pc_set_name(name) else (detect_jib_cat(name) or cat_name)

                        pe = await card.query_selector("p.price_total")
                        if not pe:
                            pe = await card.query_selector("[class*='price']")
                        price = parse_price(await pe.inner_text() if pe else "")
                        if not price:
                            continue

                        # A JIB card can contain several anchors and the first
                        # one is sometimes a stale link from a neighboring
                        # product. Choose the href whose slug agrees with the
                        # displayed model, then reject explicit conflicts.
                        url_candidates = []
                        for le in await card.query_selector_all("a[href]"):
                            href = (await le.get_attribute("href") or "").strip()
                            if not href or href in ["#", "javascript:void(0)", "javascript:;"]:
                                continue
                            candidate_url = (
                                "https://www.jib.co.th" + href
                                if not href.startswith("http") else href
                            )
                            url_candidates.append(candidate_url)
                        prod_url = max(
                            url_candidates,
                            key=lambda candidate: source_url_score(name, candidate, actual_cat),
                            default="",
                        )
                        if prod_url and source_url_conflicts(name, prod_url, actual_cat):
                            prod_url = ""

                        img = ""
                        ie = await card.query_selector("img")
                        if ie:
                            img = (
                                await ie.get_attribute("src") or
                                await ie.get_attribute("data-src") or
                                await ie.get_attribute("data-lazy") or ""
                            )
                            if img and not img.startswith("http"):
                                img = "https://www.jib.co.th" + img

                        det_desc = ""
                        det_img  = ""
                        if fetch_details and prod_url and needs_detail(cur, matcher, name, actual_cat, "jib"):
                            det_desc, det_img = await fetch_detail_page(
                                detail_pg, prod_url, name, actual_cat
                            )
                            await asyncio.sleep(random.uniform(0.7, 1.4))

                        is_new = upsert_product(cur, matcher, {
                            "name": name, "price": price,
                            "img_url": det_img or img, "url": prod_url,
                            "category": actual_cat, "store": "jib",
                            "description": det_desc,
                        })
                        if is_new:
                            cat_new += 1
                        else:
                            cat_upd += 1
                        count += 1

                    except Exception as e:
                        log(f"    card err: {e}")

                conn.commit()
                log(f"    -> {count} products processed")
                if count == 0 and pn > 1:
                    break

            total_new += cat_new
            total_upd += cat_upd
            log(f"  [JIB] {cat_name}: +{cat_new} new, ~{cat_upd} merged")
            await asyncio.sleep(random.uniform(1, 2))

        await browser.close()

    log(f"  [JIB] TOTAL: {total_new} new | {total_upd} merged into existing")
    return total_new, total_upd


# ─────────────────────────────────────────────────────────────────────────────
# Scraper: iHaveCPU (HTML category pages)
# ─────────────────────────────────────────────────────────────────────────────
async def scrape_ihavecpu(conn: sqlite3.Connection, matcher: SmartMatcher,
                          pages: int = 3, fetch_details: bool = False):
    """Scrape iHaveCPU from its server-rendered Next.js JSON payload.

    The storefront no longer renders `/product/` anchors reliably to headless
    browsers and may return an Access Denied shell.  The same public category
    response contains authoritative product ids, prices, stock, images and
    properties in `__NEXT_DATA__`, so read that directly over HTTP.
    """
    cur = conn.cursor()
    total_new = total_upd = 0

    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
    }
    timeout = httpx.Timeout(30.0, connect=15.0)
    async with httpx.AsyncClient(
        headers=headers, follow_redirects=True, timeout=timeout
    ) as client:
        for cat_name, configured_url in IHC_CATS:
            base_url = configured_url.replace("www.ihavecpu.com", "ihavecpu.com")
            cat_new = cat_upd = 0
            seen_ids: set[int] = set()

            for pn in range(1, pages + 1):
                url = base_url if pn == 1 else f"{base_url}?page={pn}"
                log(f"  [iHaveCPU] {cat_name} p{pn}")
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    items = ihc_listing_products(response.text)
                except Exception as e:
                    log(f"    [iHaveCPU HTTP err] {str(e)[:120]}")
                    break
                if not items:
                    log("    no structured products")
                    break

                count = 0
                for item in items:
                    product_id = item.get("product_id")
                    if not product_id or product_id in seen_ids:
                        continue
                    seen_ids.add(product_id)
                    raw = (item.get("name_th") or item.get("name_gb") or "").strip()
                    if not raw or should_skip(raw) or any(s in raw.upper() for s in IHC_SKIP):
                        continue
                    name = clean_ihc_name(raw)
                    price = parse_price(str(item.get("price_sale") or item.get("price_before") or ""))
                    actual_cat = "PC Set" if is_pc_set_name(name) else cat_name
                    if cat_name == "Cooler":
                        low = name.lower()
                        actual_cat = "Liquid Cooler" if any(k in low for k in (
                            "liquid", "water", "240", "360", "120", "ryujin",
                            "kraken", "valkyrie", "galahad", "frozen",
                        )) else "Air Cooler"
                    n_up = name.upper()
                    if n_up.startswith(("RAM ", "DDR4", "DDR5")):
                        actual_cat = "RAM"
                    elif n_up.startswith("CPU ") and "COOLER" not in n_up:
                        actual_cat = "CPU"
                    elif n_up.startswith(("MAINBOARD ", "MOTHERBOARD ")):
                        actual_cat = "Mainboard"
                    elif n_up.startswith(("VGA ", "GPU ")):
                        actual_cat = "GPU"
                    elif n_up.startswith(("POWER SUPPLY ", "PSU ")):
                        actual_cat = "PSU"

                    prod_url = ihc_product_url(product_id, name)
                    img = (item.get("image800") or item.get("image") or "").strip()
                    desc = ihc_product_description(item)
                    if (fetch_details and prod_url and
                            needs_detail(cur, matcher, name, actual_cat, "ihavecpu")):
                        try:
                            detail_response = await client.get(prod_url)
                            detail_response.raise_for_status()
                            detail_product = ihc_detail_product(detail_response.text)
                            if detail_product and int(detail_product.get("product_id") or 0) == int(product_id):
                                desc = combine_descriptions(
                                    ihc_product_description(detail_product), desc
                                )
                                pictures = detail_product.get("picture") or []
                                if pictures:
                                    img = pictures[0].get("pic_800") or pictures[0].get("pic_150") or img
                        except Exception as e:
                            log(f"      [iHaveCPU detail err] {str(e)[:100]}")

                    is_new = upsert_product(cur, matcher, {
                        "name": name, "price": price, "img_url": img,
                        "url": prod_url, "category": actual_cat,
                        "store": "ihavecpu", "description": desc,
                    })
                    if is_new:
                        cat_new += 1
                    else:
                        cat_upd += 1
                    count += 1

                conn.commit()
                log(f"    -> {count} structured products processed")
                if count == 0 or len(items) < 24:
                    break

            total_new += cat_new
            total_upd += cat_upd
            log(f"  [iHaveCPU] {cat_name}: +{cat_new} new, ~{cat_upd} merged")

    log(f"  [iHaveCPU] TOTAL: {total_new} new | {total_upd} merged into existing")
    return total_new, total_upd


async def backfill_missing_details(conn: sqlite3.Connection, stores: list[str]):
    """Visit already-known store URLs whose detail text is still missing.

    Listing pages are paginated and sometimes omit older products.  A second
    pass over the URLs already stored in the database makes those products
    eligible for detail extraction as well (including the JIB/iHaveCPU rows
    that users can already open from the product page).
    """
    columns = {
        "jib": ("url_jib", "desc_jib"),
        "ihavecpu": ("url_ihavecpu", "desc_ihavecpu"),
        "advice": ("url_advice", "desc_advice"),
    }
    pending: list[tuple[str, str, str, str, str]] = []
    cur = conn.cursor()
    for store in stores:
        pair = columns.get(store)
        if not pair:
            continue
        url_col, desc_col = pair
        rows = cur.execute(
            f"SELECT product_id, p_name, category, {url_col}, {desc_col} "
            f"FROM products WHERE trim(COALESCE({url_col}, '')) != ''"
        ).fetchall()
        for row in rows:
            _pid, _name, _category, _url, _desc = row
            if (len((_desc or '').strip()) < 30 or
                    not detail_description_is_relevant(_name or '', _desc or '', _category or '')):
                pending.append((store, *row))

    if not pending:
        log("  [Detail backfill] no missing store descriptions")
        return {store: 0 for store in stores}

    log(f"  [Detail backfill] {len(pending)} product URLs queued")
    updated = {store: 0 for store in stores}
    cleared = 0
    ihc_client = httpx.AsyncClient(
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
        },
        follow_redirects=True,
        timeout=httpx.Timeout(30.0, connect=15.0),
    )

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        ctx = await browser.new_context(user_agent=UA, viewport={"width": 1280, "height": 800})
        await ctx.add_init_script(ANTI_BOT)
        page = await ctx.new_page()

        for index, (store, pid, name, category, url, _old_desc) in enumerate(pending, 1):
            url_col, desc_col = columns[store]
            if source_url_conflicts(name or "", url or "", category or ""):
                cur.execute(
                    f"UPDATE products SET {url_col}='', {desc_col}='', updated_at=? WHERE product_id=?",
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pid),
                )
                cleared += 1
                continue

            desc, img = await fetch_detail_page(
                page, url, name, category, timeout_ms=10000, settle_ms=1000,
                http_client=ihc_client,
            )
            if desc or img:
                cur.execute(
                    f"UPDATE products SET {desc_col} = ?, "
                    "img_url = CASE WHEN ? != '' THEN ? ELSE img_url END, "
                    "specs = CASE WHEN (specs IS NULL OR specs='') AND ? != '' THEN ? ELSE specs END, "
                    "updated_at=? WHERE product_id=?",
                    (desc, img, img, desc, desc,
                     datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pid),
                )
                updated[store] += 1
            elif not detail_description_is_relevant(name, _old_desc or '', category):
                # Do not leave a known related-product/cookie description in
                # the row when the source page currently exposes no valid
                # detail block.
                cur.execute(
                    f"UPDATE products SET {desc_col}='', updated_at=? WHERE product_id=?",
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pid),
                )
            if index % 25 == 0:
                conn.commit()
                log(f"    [Detail backfill] {index}/{len(pending)} processed")
            await asyncio.sleep(random.uniform(0.4, 0.9))

        conn.commit()
        await browser.close()
    await ihc_client.aclose()

    log(f"  [Detail backfill] updated: {updated} | cleared mismatches: {cleared}")
    return updated


# ─────────────────────────────────────────────────────────────────────────────
# Main orchestrator
# ─────────────────────────────────────────────────────────────────────────────
async def run_all(stores: list[str], pages: int, fetch_details: bool = False,
                  backfill_only: bool = False):
    conn = sqlite3.connect(DB_PATH)
    setup_db(conn)
    repair_pc_set_categories(conn)
    repair_obvious_product_categories(conn)
    repair_conflicting_source_data(conn)
    repair_implausible_prices(conn)

    matcher = SmartMatcher(conn.cursor())

    start = datetime.now()
    log(f"\n{'='*60}")
    log(f"  IT-RECOMMEND Full Scraper v3")
    log(f"  Stores      : {', '.join(stores)}")
    log(f"  Pages       : {pages} per category")
    log(f"  Fetch detail: {'YES (slow)' if fetch_details else 'NO (fast)'}")
    log(f"  Started     : {start.strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"{'='*60}\n")

    summary = {}

    if not backfill_only and "advice" in stores:
        log("=== [Advice] ===")
        n, u = await scrape_advice(conn, matcher, pages, fetch_details)
        summary["advice"] = {"new": n, "updated": u}

    if not backfill_only and "jib" in stores:
        log("\n=== [JIB] ===")
        n, u = await scrape_jib(conn, matcher, pages, fetch_details)
        summary["jib"] = {"new": n, "updated": u}

    if not backfill_only and "ihavecpu" in stores:
        log("\n=== [iHaveCPU] ===")
        n, u = await scrape_ihavecpu(conn, matcher, pages, fetch_details)
        summary["ihavecpu"] = {"new": n, "updated": u}

    if fetch_details or backfill_only:
        log("\n=== [Detail backfill] ===")
        summary["detail_backfill"] = await backfill_missing_details(conn, stores)

    conn.close()

    elapsed = (datetime.now() - start).total_seconds()
    log(f"\n{'='*60}")
    log(f"  DONE — elapsed {elapsed:.0f}s")
    log(f"{'='*60}")

    # DB stats
    c = sqlite3.connect(DB_PATH)
    cur = c.cursor()
    total  = cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    adv    = cur.execute("SELECT COUNT(*) FROM products WHERE price_advice>0").fetchone()[0]
    jib    = cur.execute("SELECT COUNT(*) FROM products WHERE price_jib>0").fetchone()[0]
    ihc    = cur.execute("SELECT COUNT(*) FROM products WHERE price_ihavecpu>0").fetchone()[0]
    multi  = cur.execute(
        "SELECT COUNT(*) FROM products WHERE "
        "(CASE WHEN price_advice>0 THEN 1 ELSE 0 END + "
        " CASE WHEN price_jib>0    THEN 1 ELSE 0 END + "
        " CASE WHEN price_ihavecpu>0 THEN 1 ELSE 0 END) >= 2"
    ).fetchone()[0]
    c.close()

    log(f"\n  Products total   : {total}")
    log(f"  With Advice price: {adv}")
    log(f"  With JIB price   : {jib}")
    log(f"  With iHaveCPU    : {ihc}")
    log(f"  Multi-store (>=2): {multi}  ← สินค้าที่เปรียบเทียบราคาได้")
    log(f"\n  Per-store breakdown:")
    for store, s in summary.items():
        if store == "detail_backfill":
            log(f"    {'details':10}: {s}")
        else:
            log(f"    {store:10}: +{s['new']} new  |  ~{s['updated']} merged into existing")


def main():
    parser = argparse.ArgumentParser(
        description="Full 3-store scraper with SmartMatcher deduplication",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
ตัวอย่าง:
  python full_scraper.py                          # เร็ว: listing เท่านั้น
  python full_scraper.py --details                # ครบ: + visit หน้าสินค้า (ช้า)
  python full_scraper.py --stores ihavecpu jib --pages 3
  python full_scraper.py --stores ihavecpu --details --pages 2
"""
    )
    parser.add_argument(
        "--stores", nargs="+", default=["all"],
        choices=["all", "advice", "jib", "ihavecpu"],
        help="Stores to scrape (default: all)",
    )
    parser.add_argument(
        "--pages", type=int, default=3,
        help="Max pages per category (default: 3)",
    )
    parser.add_argument(
        "--details", action="store_true", default=False,
        help="Visit each product page to fetch description + full image (slow, ~3-5s per product)",
    )
    parser.add_argument(
        "--backfill-only", action="store_true", default=False,
        help="Skip listing pages and fetch details for existing store URLs with missing descriptions",
    )
    parser.add_argument(
        "--skip-compat-training", action="store_true", default=False,
        help="Do not normalize scraped details into compatibility facts after --details",
    )
    args = parser.parse_args()

    stores = ["advice", "jib", "ihavecpu"] if "all" in args.stores else args.stores

    if args.details:
        log("[WARNING] --details เปิดอยู่ — จะ visit หน้าสินค้าทุกชิ้น (ใช้เวลาหลายชั่วโมง)")
        log("          กด Ctrl+C เพื่อหยุดได้ตลอดเวลา (ข้อมูลที่ scrape ไปแล้วจะถูกบันทึก)")

    asyncio.run(run_all(stores, args.pages, args.details, args.backfill_only))

    if (args.details or args.backfill_only) and not args.skip_compat_training:
        log("\n[Compat Knowledge] Normalizing sourced product details...")
        trainer = os.path.join(os.path.dirname(__file__), "train_compat_knowledge.py")
        completed = subprocess.run([sys.executable, "-X", "utf8", trainer, "--apply"], check=False)
        if completed.returncode != 0:
            log("[Compat Knowledge] Training step failed; raw scraped details remain intact")


if __name__ == "__main__":
    main()
