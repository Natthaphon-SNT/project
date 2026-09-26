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
import time
from collections import deque
from urllib.parse import quote, unquote, urlparse
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

if __name__ == "__main__" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "shop.db")
DETAIL_CONCURRENCY = {"advice": 1, "jib": 4, "ihavecpu": 1}
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
]
IHC_FULL_CATS = [
    ("CPU", "https://ihavecpu.com/category/cpu"),
    ("GPU", "https://ihavecpu.com/category/graphic-card"),
    ("Mainboard", "https://ihavecpu.com/category/mainboard"),
    ("RAM", "https://ihavecpu.com/category/ram"),
    ("SSD", "https://ihavecpu.com/category/storage"),
    ("PSU", "https://ihavecpu.com/category/power-supply"),
    ("Case", "https://ihavecpu.com/category/case"),
    ("Cooler", "https://ihavecpu.com/category/heat-sink"),
    ("Gaming Gear", "https://ihavecpu.com/category/gaming-gear"),
    ("Monitor", "https://ihavecpu.com/category/monitor"),
    ("Gaming Chair", "https://ihavecpu.com/category/gaming-chair"),
    ("Gaming Desk", "https://ihavecpu.com/category/gaming-desk"),
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
    "mouse": "c10", "keyboard accessories": "c21", "keyboard": "c11", "headset": "c12",
    "microphone": "c13", "monitor accessories": "c25", "monitor": "c14",
    "gaming chair": "c15", "chair": "c15",
    "gaming desk": "c16", "desk": "c16", "gaming gear": "c17",
    "pc set": "c18", "computer set": "c18",
    "hdd": "c19", "external storage": "c20", "cooling accessories": "c22",
    "pc components": "c23", "storage accessories": "c24",
    "case accessories": "c26", "keypad": "c27", "graphic tablet": "c28",
    "case fan": "c29", "dual mode monitor": "c30",
    "portable monitor": "c31", "curved monitor": "c32",
    "gaming headset": "c33", "wireless headset": "c34",
    "gpu accessories": "c35", "in-ear headphone": "c36",
    "true wireless earbuds": "c37",
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


def parse_price(text: str, min_price: int = 200) -> int:
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
    return n if min_price <= n <= 500_000 else 0


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
    has_meta_text = any(_plain_html(product.get(key) or "") for key in (
        "meta_description_th", "meta_description_gb",
    ))
    for label, field in (
        ("Summary", "size_guide_th"),
        ("Description", "description_th"),
        # Some products (for example iHaveCPU 44014) contain only an image in
        # description_th.  The server-provided meta description is then the
        # only textual product description and is preferable to invented text.
        ("Meta description", "meta_description_th"),
        ("Meta description", "meta_description_gb"),
    ):
        raw_value = product.get(field) or ""
        value = _plain_html(raw_value)
        if label == "Description" and not value and raw_value and not has_meta_text:
            # A few iHaveCPU listings provide their description only as an
            # image. Preserve that source asset instead of silently dropping it.
            for image in BeautifulSoup(raw_value, "html.parser").select("img[src]"):
                image_url = (image.get("src") or "").strip()
                if image_url.startswith(("https://", "http://")):
                    line = f"Detail image: {image_url}"
                    if line not in seen:
                        seen.add(line)
                        lines.append(line)
        if value and not (label == "Description" and len(value) < 10):
            line = f"{label}: {value}"
            if line not in seen:
                seen.add(line)
                lines.append(line)
    return "\n".join(lines)


def ihc_listing_products(document: str) -> list[dict]:
    data = extract_next_data(document)
    product = data.get("props", {}).get("pageProps", {}).get("product", {})
    items = product.get("data", []) if isinstance(product, dict) else []
    if not isinstance(items, list):
        return []
    # The product ID alone is not a usable storefront URL, and rebuilding a
    # slug from our cleaned display name drops iHaveCPU's Thai category prefix.
    # Use the exact href rendered by the retailer for each listing card.
    links = {}
    for anchor in BeautifulSoup(document or "", "html.parser").select("a[href]"):
        href = (anchor.get("href") or "").strip()
        match = re.fullmatch(r"/product/(\d+)/[^?#]+", href)
        if match:
            links[int(match.group(1))] = "https://ihavecpu.com" + href
    for item in items:
        if isinstance(item, dict):
            try:
                product_id = int(item.get("product_id") or 0)
            except (TypeError, ValueError):
                continue
            if product_id in links:
                item["product_url"] = links[product_id]
    return items


def ihc_item_url(item: dict) -> str:
    """Prefer the merchant's listing href; use an ID-based slug only as fallback."""
    url = (item.get("product_url") or "").strip()
    if re.fullmatch(r"https://ihavecpu\.com/product/\d+/[^?#]+", url):
        return url
    name = (item.get("name_th") or item.get("name_gb") or "").strip()
    return ihc_product_url(item.get("product_id"), name)


def ihc_listing_total(document: str) -> int:
    """The Next.js `row` field is the total across every category page."""
    product = extract_next_data(document).get("props", {}).get("pageProps", {}).get("product", {})
    try:
        return max(0, int(product.get("row") or 0))
    except (TypeError, ValueError, AttributeError):
        return 0


def ihc_full_category(name: str, listing_category: str) -> str:
    """Keep requested listing groups without misfiling gaming accessories."""
    upper = (name or "").upper()
    if listing_category == "Gaming Gear":
        for prefix, category in (
            ("MOUSE PAD", "Gaming Gear"), ("MOUSE", "Mouse"),
            ("KEYBOARD", "Keyboard"), ("HEADSET", "Headset"),
            ("HEADPHONE", "Headset"), ("EARPHONE", "Headset"),
            ("MICROPHONE", "Microphone"), ("GAMING CHAIR", "Gaming Chair"),
            ("GAMING DESK", "Gaming Desk"),
        ):
            if upper.startswith(prefix):
                return category
        return "Gaming Gear"
    return "PC Set" if is_pc_set_name(name) else listing_category


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
    if isinstance(groups, dict):
        groups = groups.values()
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
                "price": (product.get("price_sale_true") or product.get("price_sale")
                          or product.get("price_srp") or product.get("price") or 0),
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
    if c in CID_MAP:
        return CID_MAP[c]
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
    if up.startswith(("CPU AIR COOLER", "AIR COOLER", "CPU COOLER")):
        return "Air Cooler"
    if up.startswith(("CPU LIQUID COOLER", "LIQUID COOLER", "AIO COOLER")):
        return "Liquid Cooler"
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


def source_url_is_out_of_scope(url: str) -> bool:
    """Reject explicit accessory/category paths returned by broad searches."""
    path = unquote(urlparse(url or "").path).lower()
    return any(part in path for part in (
        "/gaming-microphone/", "/microphone/", "/cable/",
        "/cctv-accessories/", "/ups-", "/ups/",
        "/case-iphone", "/case-ipad", "/case-samsung",
        "/notebook/", "/laptop/",
    ))


# ─────────────────────────────────────────────────────────────────────────────
# DB Setup
# ─────────────────────────────────────────────────────────────────────────────
def setup_db(conn: sqlite3.Connection):
    cur = conn.cursor()
    if cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='categories'"
    ).fetchone():
        cur.executemany(
            "INSERT OR IGNORE INTO categories (cid, c_name, c_description) VALUES (?, ?, ?)",
            [
                ("c17", "Gaming Gear", "iHaveCPU gaming-gear products"),
                ("c19", "HDD", "Internal hard disk drives"),
                ("c20", "External Storage", "External SSD and HDD devices"),
                ("c21", "Keyboard Accessories", "Keycaps and keyboard accessories"),
                ("c22", "Cooling Accessories", "Cooling fittings, blocks and thermal accessories"),
                ("c23", "PC Components", "Other PC components"),
                ("c24", "Storage Accessories", "Storage enclosures and accessories"),
                ("c25", "Monitor Accessories", "Monitor mounts and accessories"),
                ("c26", "Case Accessories", "Case bags and other case accessories"),
                ("c27", "Keypad", "Numeric and macro keypads"),
                ("c28", "Graphic Tablet", "Pen and display tablets"),
                ("c29", "Case Fan", "Case cooling fans"),
                ("c30", "Dual Mode Monitor", "Dual-mode displays"),
                ("c31", "Portable Monitor", "Portable displays"),
                ("c32", "Curved Monitor", "Curved displays"),
                ("c33", "Gaming Headset", "Wired gaming headsets"),
                ("c34", "Wireless Headset", "Wireless gaming headsets"),
                ("c35", "GPU Accessories", "GPU supports and riser cables"),
                ("c36", "In-Ear Headphone", "In-ear gaming headphones"),
                ("c37", "True Wireless Earbuds", "True wireless gaming earbuds"),
            ],
        )
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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scrape_detail_checkpoint (
            store       TEXT NOT NULL,
            url_hash    TEXT NOT NULL,
            url         TEXT NOT NULL,
            category    TEXT DEFAULT '',
            status      TEXT NOT NULL,
            description TEXT DEFAULT '',
            image_url   TEXT DEFAULT '',
            attempts    INTEGER NOT NULL DEFAULT 0,
            last_error  TEXT DEFAULT '',
            updated_at  TEXT NOT NULL,
            PRIMARY KEY (store, url_hash)
        )
    """)
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_detail_checkpoint_status "
        "ON scrape_detail_checkpoint(store, status)"
    )
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ihavecpu_scrape_inventory (
            category_url TEXT NOT NULL,
            source_product_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            product_name TEXT NOT NULL,
            price INTEGER NOT NULL,
            image_url TEXT NOT NULL,
            description TEXT NOT NULL,
            product_url TEXT NOT NULL,
            db_product_id TEXT NOT NULL DEFAULT '',
            scraped_at TEXT NOT NULL,
            PRIMARY KEY (category_url, source_product_id)
        )
    """)
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


def sync_best_product_descriptions(conn: sqlite3.Connection) -> int:
    """Fill legacy display descriptions from verified per-store detail text."""
    changed = conn.execute("""
        UPDATE products SET
            p_description=CASE
                WHEN length(trim(coalesce(desc_advice,''))) >=
                     length(trim(coalesce(desc_jib,'')))
                 AND length(trim(coalesce(desc_advice,''))) >=
                     length(trim(coalesce(desc_ihavecpu,'')))
                THEN desc_advice
                WHEN length(trim(coalesce(desc_jib,''))) >=
                     length(trim(coalesce(desc_ihavecpu,'')))
                THEN desc_jib
                ELSE desc_ihavecpu END,
            specs=CASE
                WHEN length(trim(coalesce(specs,''))) >= 30 THEN specs
                WHEN length(trim(coalesce(desc_advice,''))) >=
                     length(trim(coalesce(desc_jib,'')))
                 AND length(trim(coalesce(desc_advice,''))) >=
                     length(trim(coalesce(desc_ihavecpu,'')))
                THEN desc_advice
                WHEN length(trim(coalesce(desc_jib,''))) >=
                     length(trim(coalesce(desc_ihavecpu,'')))
                THEN desc_jib
                ELSE desc_ihavecpu END
        WHERE length(trim(coalesce(p_description,''))) < 30
          AND max(length(trim(coalesce(desc_advice,''))),
                  length(trim(coalesce(desc_jib,''))),
                  length(trim(coalesce(desc_ihavecpu,'')))) >= 30
    """).rowcount
    conn.commit()
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


def repair_out_of_scope_source_data(conn: sqlite3.Connection) -> int:
    """Clear store data for accessories leaked in by broad search APIs."""
    cur = conn.cursor()
    repaired = 0
    for store, price_col, url_col, desc_col in (
        ("advice", "price_advice", "url_advice", "desc_advice"),
        ("jib", "price_jib", "url_jib", "desc_jib"),
        ("ihavecpu", "price_ihavecpu", "url_ihavecpu", "desc_ihavecpu"),
    ):
        rows = cur.execute(
            f"SELECT product_id, p_name, {url_col} FROM products "
            f"WHERE {price_col}>0 AND trim(coalesce({url_col},''))<>''"
        ).fetchall()
        for pid, name, url in rows:
            if not should_skip(name or "") and not source_url_is_out_of_scope(url or ""):
                continue
            cur.execute(
                f"UPDATE products SET {price_col}=0, {url_col}='', {desc_col}='' "
                "WHERE product_id=?",
                (pid,),
            )
            _refresh_lowest_price(cur, pid)
            repaired += 1
            log(f"  [repair] cleared out-of-scope {store} item: {(name or '')[:70]}")
    conn.commit()
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
    if is_placeholder_image_url(img):
        img = ""
    url   = (p.get("url") or "").strip()
    desc  = (p.get("description") or "").strip()
    full_ihc = store == "ihavecpu" and bool(p.get("full_catalog"))
    full_jib = store == "jib" and bool(p.get("full_catalog"))
    full_advice = store == "advice" and bool(p.get("full_catalog"))
    full_source = full_ihc or full_jib or full_advice

    if url and not (full_jib or full_advice) and source_url_conflicts(name, url, cat):
        log(f"    [url mismatch] {store}: {name[:70]} -> {_source_slug(url)[:90]}")
        url = ""

    if not name or not price:
        return False
    if should_skip(name) and not full_source:
        return False
    if source_url_is_out_of_scope(url) and not full_advice:
        log(f"    [out of scope] {store}: {name[:65]}")
        return False
    price_ok = (1 <= price <= 500_000) if full_source else valid_product_price(cat, price)
    if not price_ok:
        log(f"    [invalid price] {store}: {cat} {name[:65]} -> {price:,} B")
        return False

    cid       = get_cid(cat)
    now_str   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    price_col = {"advice": "price_advice", "jib": "price_jib", "ihavecpu": "price_ihavecpu"}.get(store, "price_advice")
    url_col   = {"advice": "url_advice",   "jib": "url_jib",   "ihavecpu": "url_ihavecpu"}.get(store, "url_advice")
    desc_col  = {"advice": "desc_advice",  "jib": "desc_jib",  "ihavecpu": "desc_ihavecpu"}.get(store, "desc_advice")

    source_row = cur.execute(
        f"SELECT product_id FROM products WHERE {url_col} = ? LIMIT 1", (url,)
    ).fetchone() if url else None
    ihc_source_id = ""
    if full_ihc:
        source_match = re.search(r"/product/(\d+)/", url)
        ihc_source_id = source_match.group(1) if source_match else ""
        if ihc_source_id and not source_row:
            source_row = cur.execute(
                "SELECT product_id FROM products WHERE url_ihavecpu LIKE ? LIMIT 1",
                (f"%/product/{ihc_source_id}/%",),
            ).fetchone()
    jib_source_id = ""
    if full_jib:
        source_match = re.search(r"/readProduct/(\d+)/", url)
        jib_source_id = source_match.group(1) if source_match else ""
        if jib_source_id and not source_row:
            source_row = cur.execute(
                "SELECT product_id FROM products WHERE url_jib LIKE ? LIMIT 1",
                (f"%/readProduct/{jib_source_id}/%",),
            ).fetchone()
    advice_source_code = ""
    if full_advice:
        advice_source_code = re.sub(r"[^A-Za-z0-9]", "", p.get("source_code") or "")
    pid = source_row[0] if source_row else matcher.find(name, cat)
    if full_source and pid and not source_row:
        candidate = cur.execute(
            f"SELECT p_name, {url_col} FROM products WHERE product_id = ?", (pid,)
        ).fetchone()
        # A fuzzy name match must not combine two distinct retailer product IDs.
        if (not candidate or candidate[0].strip().upper() != name.strip().upper()
                or (candidate[1] or "").strip()):
            pid = None

    if pid:
        if full_source and source_row:
            # Source-only rows may carry a stale title from an earlier fuzzy
            # merge. The retailer's ID and current listing are authoritative.
            other_price_cols = [column for column in
                                ("price_advice", "price_jib", "price_ihavecpu")
                                if column != price_col]
            cur.execute(f"""
                UPDATE products SET p_name=?, category=?, cid=?,
                    img_url=CASE WHEN ? != '' THEN ? ELSE img_url END
                WHERE product_id=? AND COALESCE({other_price_cols[0]}, 0)=0
                    AND COALESCE({other_price_cols[1]}, 0)=0
            """, (name, cat, get_cid(cat), img, img, pid))
        # A later listing-only scrape must not replace a PSU's verified
        # connector table with Advice's short wattage/modularity summary.
        if store == "advice" and cat == "PSU" and desc:
            import spec_parser
            previous = cur.execute(
                f"SELECT {desc_col} FROM products WHERE product_id = ?", (pid,)
            ).fetchone()
            old_desc = (previous[0] or "") if previous else ""
            if (spec_parser.extract_detail_facts("PSU", old_desc).get("power_connectors")
                    and not spec_parser.extract_detail_facts("PSU", desc).get("power_connectors")):
                desc = combine_descriptions(desc, old_desc)
        cur.execute(f"""
            UPDATE products SET
                {price_col} = ?,
                {url_col}   = CASE WHEN ? != '' THEN ? ELSE {url_col} END,
                {desc_col}  = CASE WHEN ? != '' THEN ? ELSE {desc_col} END,
                p_price     = CASE WHEN p_price = 0 THEN ? ELSE p_price END,
                img_url     = CASE WHEN ? != '' AND
                    (img_url IS NULL OR img_url = '' OR
                     lower(img_url) LIKE '%/logos/android-chrome-%' OR
                     lower(img_url) LIKE '%placeholder%' OR
                     lower(img_url) LIKE '%nophoto%' OR
                     lower(img_url) LIKE '%no-photo%')
                    THEN ? ELSE img_url END,
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
        if full_ihc and ihc_source_id:
            pid = f"ihc_{ihc_source_id}"
        elif full_jib and jib_source_id:
            pid = f"jib_{jib_source_id}"
        elif full_advice and advice_source_code:
            pid = f"adv_{advice_source_code}"
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
    return source_payload_needs_detail(row[0] or "", row[1] or "", category, store)


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
    "[id*='spec']", "table.table-spec", "div.product-detail-content",
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

_TRANSIENT_HTTP_STATUSES = {408, 425, 429, 500, 502, 503, 504}


class AdaptiveRateLimiter:
    """Store-local 429 circuit breaker shared by listing/detail workers.

    Advice has historically throttled even low request rates.  A rolling event
    window is used instead of a simple consecutive counter because a successful
    retry between two 429 responses must not immediately erase the signal.
    """

    def __init__(self, store: str, *, threshold: int = 2,
                 window_seconds: float = 60.0,
                 base_cooldown_seconds: float = 15.0,
                 max_cooldown_seconds: float = 120.0,
                 min_interval_seconds: float = 0.0):
        self.store = store
        self.threshold = threshold
        self.window_seconds = window_seconds
        self.base_cooldown_seconds = base_cooldown_seconds
        self.max_cooldown_seconds = max_cooldown_seconds
        self.rate_limit_events: deque[float] = deque()
        self.pause_until = 0.0
        self.total_429 = 0
        self.circuit_open_count = 0
        self.min_interval_seconds = min_interval_seconds
        self.next_request_at = 0.0
        self._lock = asyncio.Lock()

    async def before_request(self) -> None:
        async with self._lock:
            now = time.monotonic()
            circuit_delay = max(0.0, self.pause_until - now)
            start_at = max(now, self.pause_until, self.next_request_at)
            delay = start_at - now
            self.next_request_at = start_at + self.min_interval_seconds
        if circuit_delay:
            log(f"    [circuit wait] store={self.store} seconds={delay:.1f}")
        if delay:
            await asyncio.sleep(delay)

    async def record_status(self, status_code: int) -> None:
        if status_code != 429:
            return
        now = time.monotonic()
        async with self._lock:
            self.total_429 += 1
            self.rate_limit_events.append(now)
            while (self.rate_limit_events and
                   now - self.rate_limit_events[0] > self.window_seconds):
                self.rate_limit_events.popleft()
            recent = len(self.rate_limit_events)
            if recent < self.threshold:
                return
            exponent = min(recent - self.threshold, 3)
            cooldown = min(
                self.max_cooldown_seconds,
                self.base_cooldown_seconds * (2 ** exponent),
            )
            self.pause_until = max(self.pause_until, now + cooldown)
            self.circuit_open_count += 1
        log(
            f"    [circuit open] store={self.store} status=429 "
            f"recent={recent} cooldown={cooldown:.1f}s"
        )

    def metrics(self) -> dict[str, int]:
        return {
            "http_429": self.total_429,
            "circuit_open": self.circuit_open_count,
        }


async def request_with_retry(client: httpx.AsyncClient, method: str, url: str,
                             *, attempts: int = 3,
                             rate_limiter: AdaptiveRateLimiter | None = None,
                             **kwargs) -> httpx.Response:
    """Retry only transient HTTP/transport failures with bounded backoff."""
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        retry_after = 0.0
        if rate_limiter is not None:
            await rate_limiter.before_request()
        try:
            response = await client.request(method, url, **kwargs)
            if rate_limiter is not None:
                await rate_limiter.record_status(response.status_code)
            if response.status_code not in _TRANSIENT_HTTP_STATUSES:
                return response
            if response.status_code == 429:
                try:
                    retry_after = float(response.headers.get("retry-after", "0"))
                except ValueError:
                    retry_after = 0.0
            last_error = httpx.HTTPStatusError(
                f"transient HTTP {response.status_code}",
                request=response.request,
                response=response,
            )
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_error = exc
        if attempt < attempts:
            base_delay = 5.0 if getattr(last_error, "response", None) is not None and last_error.response.status_code == 429 else 0.5
            delay = max(retry_after, base_delay * (2 ** (attempt - 1)))
            log(
                f"    [retry] {method.upper()} transient failure "
                f"attempt {attempt}/{attempts}; backoff {delay:.1f}s"
            )
            await asyncio.sleep(delay)
    assert last_error is not None
    raise last_error


async def goto_with_retry(page, url: str, *, timeout_ms: int,
                          wait_until: str = "domcontentloaded", attempts: int = 3,
                          rate_limiter: AdaptiveRateLimiter | None = None):
    """Retry transient browser navigation failures and HTTP 429/5xx responses."""
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        retry_after = 0.0
        transient_status = 0
        if rate_limiter is not None:
            await rate_limiter.before_request()
        try:
            response = await page.goto(url, timeout=timeout_ms, wait_until=wait_until)
            status = response.status if response else 0
            if rate_limiter is not None:
                await rate_limiter.record_status(status)
            if status not in _TRANSIENT_HTTP_STATUSES:
                return response
            transient_status = status
            if status == 429 and response:
                try:
                    retry_after = float(await response.header_value("retry-after") or 0)
                except (TypeError, ValueError):
                    retry_after = 0.0
            last_error = RuntimeError(f"transient HTTP {status}")
        except Exception as exc:
            # Playwright raises its own TimeoutError type; other navigation
            # failures are also safe to retry because page.goto is read-only.
            last_error = exc
        if attempt < attempts:
            base_delay = 5.0 if transient_status == 429 else 0.5
            delay = max(retry_after, base_delay * (2 ** (attempt - 1)))
            log(
                f"    [retry] browser navigation attempt {attempt}/{attempts}; "
                f"backoff {delay:.1f}s"
            )
            await asyncio.sleep(delay)
    assert last_error is not None
    raise last_error


def source_payload_needs_detail(description: str, image_url: str,
                                category: str = "", store: str = "") -> bool:
    """Return true only when a store listing lacks usable detail evidence."""
    if (len((description or "").strip()) < 30
            or not (image_url or "").strip()
            or is_placeholder_image_url(image_url)):
        return True
    if store == "advice" and category == "PSU":
        import spec_parser
        return not spec_parser.extract_detail_facts(
            "PSU", description
        ).get("power_connectors")
    return False


def is_placeholder_image_url(url: str) -> bool:
    """Identify retailer/site chrome that must never be used as a product photo."""
    value = (url or "").strip().lower().split("?", 1)[0]
    return any(marker in value for marker in (
        "/logos/android-chrome-",
        "/logo/",
        "/logos/",
        "placeholder",
        "no-photo",
        "nophoto",
        "no_image",
        "no-image",
    ))


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


def select_best_relevant_description(
    candidates: list[tuple[int, str]], name: str, category: str
) -> str:
    """Pick the highest-scoring candidate after relevance filtering.

    A large related-products container must not hide a smaller authoritative
    specification table merely because the container received a higher score.
    """
    relevant = [
        item for item in candidates
        if detail_description_is_relevant(name, item[1], category)
    ]
    if category == "PSU":
        import spec_parser
        with_connectors = [
            item for item in relevant
            if spec_parser.extract_detail_facts("PSU", item[1]).get("power_connectors")
        ]
        if with_connectors:
            relevant = with_connectors
    return max(relevant, key=lambda item: item[0])[1] if relevant else ""


async def fetch_ihc_detail_http(client: httpx.AsyncClient, url: str,
                                expected_name: str = "", category: str = "",
                                *, rate_limiter: AdaptiveRateLimiter | None = None,
                                strict_block: bool = False) -> tuple[str, str]:
    try:
        response = await request_with_retry(
            client, "GET", url, rate_limiter=rate_limiter,
        )
        if strict_block and response.status_code in (403, 429):
            raise PermissionError(f"iHaveCPU blocked detail request: HTTP {response.status_code}")
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
        if strict_block and (
            isinstance(e, PermissionError) or
            isinstance(e, httpx.HTTPStatusError) and e.response.status_code in (403, 429)
        ):
            raise PermissionError(f"iHaveCPU blocked detail request: {e}") from e
        log(f"      [iHaveCPU HTTP detail err] {str(e)[:100]}")
        return "", ""


async def fetch_jib_detail_http(client: httpx.AsyncClient, url: str,
                                expected_name: str, category: str,
                                *, rate_limiter: AdaptiveRateLimiter | None = None,
                                strict_block: bool = False) -> tuple[str, str]:
    """Extract JIB's server-rendered spec without Chromium per product."""
    try:
        response = await request_with_retry(
            client, "GET", url, rate_limiter=rate_limiter,
        )
        if strict_block and response.status_code in (403, 429):
            raise PermissionError(f"JIB blocked detail request: HTTP {response.status_code}")
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        # JIB's own specification pane is tied to this readProduct page.
        # Generic name-vs-spec identity checks can falsely reject RAM kits:
        # the title says 32 GB while the table also says 16 GB per DIMM.
        own_spec = soup.find(id="specspecial")
        own_description = own_spec.get_text("\n", strip=True) if own_spec else ""
        candidates: list[tuple[int, str]] = []
        for selector in (() if len(own_description) >= 30 else _DESC_SELECTORS):
            try:
                elements = soup.select(selector)
            except Exception:
                continue
            for element in elements:
                # Keep table cell boundaries for compatibility fact parsing.
                text_value = element.get_text("\n", strip=True)
                if len(text_value) < 30:
                    continue
                if len(text_value) > 18000:
                    text_value = text_value[:18000]
                low = text_value.lower()
                score = min(len(text_value), 6000)
                score += sum(180 for word in (
                    "spec", "socket", "ddr", "watt", "dimension", "รายละเอียด",
                    "คุณสมบัติ", "การรับประกัน", "interface", "capacity",
                ) if word in low)
                keyword_hits = sum(1 for word in (
                    "spec", "socket", "ddr", "watt", "dimension", "brand", "model",
                    "form factor", "chipset", "memory type", "continuous power",
                    "warranty", "interface", "capacity",
                ) if word in low)
                score += keyword_hits * 180
                if selector in ("main", "article", "main [role='main']"):
                    score -= 900
                if ("detail" in selector or "description" in selector) and not keyword_hits:
                    score -= 900
                if selector in ("table", "div.table-wrapper", "[id*='spec']"):
                    score += 350
                candidates.append((score, text_value))
        desc = (own_description if len(own_description) >= 30 else
                select_best_relevant_description(candidates, expected_name, category))
        if not desc:
            for script in soup.select("script[type='application/ld+json']"):
                try:
                    payload = json.loads(script.get_text(strip=True))
                except (TypeError, ValueError):
                    continue
                objects = payload if isinstance(payload, list) else [payload]
                for item in objects:
                    value = item.get("description", "") if isinstance(item, dict) else ""
                    if detail_description_is_relevant(expected_name, value, category):
                        desc = value.strip()
                        break
                if desc:
                    break
        if not desc:
            meta = soup.select_one("meta[name='description']")
            meta_text = (meta.get("content") or "").strip() if meta else ""
            if len(meta_text) >= 30 and not any(
                word in meta_text.lower() for word in ("cookie", "privacy policy")
            ):
                desc = meta_text
        image_meta = soup.find("meta", attrs={"property": "og:image"})
        img = (image_meta.get("content") or "").strip() if image_meta else ""
        if not img.startswith("http"):
            img = ""
        for selector in (() if img else _IMG_SELECTORS):
            try:
                element = soup.select_one(selector)
            except Exception:
                element = None
            if not element:
                continue
            for attr in ("src", "data-src", "data-lazy", "data-original"):
                value = (element.get(attr) or "").strip()
                if value.startswith("http") and not value.endswith(".gif"):
                    img = value
                    break
            if img:
                break
        if not img:
            meta = soup.select_one("meta[property='og:image']")
            value = (meta.get("content") or "").strip() if meta else ""
            if value.startswith("http"):
                img = value
        return desc, img
    except Exception as exc:
        if strict_block and (
            isinstance(exc, PermissionError) or
            isinstance(exc, httpx.HTTPStatusError) and
            exc.response.status_code in (403, 429)
        ):
            raise PermissionError(f"JIB blocked detail request: {exc}") from exc
        log(f"      [JIB HTTP detail err] {str(exc)[:100]}")
        return "", ""


async def fetch_detail_page(page, url: str, expected_name: str = "",
                            category: str = "", timeout_ms: int = 20000,
                            settle_ms: int = 1800,
                            http_client: httpx.AsyncClient | None = None,
                            rate_limiter: AdaptiveRateLimiter | None = None) -> tuple[str, str]:
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
        await goto_with_retry(
            page, url, timeout_ms=timeout_ms, rate_limiter=rate_limiter
        )
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
            desc = select_best_relevant_description(
                candidates, expected_name, category
            )
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


def _detail_checkpoint_key(url: str) -> str:
    return hashlib.sha256((url or "").strip().encode("utf-8")).hexdigest()


def _read_detail_checkpoint(conn: sqlite3.Connection, store: str,
                            url: str) -> tuple[str, str] | None:
    row = conn.execute(
        "SELECT description, image_url FROM scrape_detail_checkpoint "
        "WHERE store=? AND url_hash=? AND status='success'",
        (store, _detail_checkpoint_key(url)),
    ).fetchone()
    if not row:
        return None
    return (row[0] or "", row[1] or "")


def _write_detail_checkpoint(conn: sqlite3.Connection, store: str, item: dict,
                             desc: str, img: str, error: str = "") -> None:
    success = len((desc or "").strip()) >= 30
    conn.execute(
        """
        INSERT INTO scrape_detail_checkpoint
            (store, url_hash, url, category, status, description, image_url,
             attempts, last_error, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
        ON CONFLICT(store, url_hash) DO UPDATE SET
            category=excluded.category,
            status=excluded.status,
            description=excluded.description,
            image_url=excluded.image_url,
            attempts=scrape_detail_checkpoint.attempts + 1,
            last_error=excluded.last_error,
            updated_at=excluded.updated_at
        """,
        (
            store, _detail_checkpoint_key(item["url"]), item["url"],
            item.get("category", ""), "success" if success else "failed",
            desc or "", img or "", error[:300],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()


async def fetch_browser_detail_queue(
    ctx,
    conn: sqlite3.Connection,
    store: str,
    items: list[dict],
    *,
    concurrency: int | None = None,
    rate_limiter: AdaptiveRateLimiter | None = None,
    timeout_ms: int = 20000,
    settle_ms: int = 1800,
) -> tuple[dict[str, tuple[str, str]], dict]:
    """Fetch product details with bounded workers and durable checkpoints.

    Every worker owns one Playwright page.  On cancellation all worker tasks
    are cancelled and awaited before their pages (and later the context) close,
    preventing orphan Playwright futures from reporting TargetClosedError.
    """
    limit = max(1, concurrency or DETAIL_CONCURRENCY.get(store, 1))
    results: dict[str, tuple[str, str]] = {}
    queue: asyncio.Queue[dict] = asyncio.Queue()
    checkpoint_hits = 0
    unique: dict[str, dict] = {}
    for item in items:
        if item.get("url"):
            unique[item["url"]] = item
    for url, item in unique.items():
        cached = _read_detail_checkpoint(conn, store, url)
        if cached is not None:
            results[url] = cached
            checkpoint_hits += 1
        else:
            queue.put_nowait(item)

    queued = queue.qsize()
    started = time.perf_counter()

    async def worker(worker_id: int) -> None:
        page = await ctx.new_page()
        try:
            while True:
                try:
                    item = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return
                error = ""
                try:
                    desc, img = await fetch_detail_page(
                        page, item["url"], item.get("name", ""),
                        item.get("category", ""), timeout_ms=timeout_ms,
                        settle_ms=settle_ms, rate_limiter=rate_limiter,
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    desc, img = "", ""
                    error = f"{type(exc).__name__}: {str(exc)[:220]}"
                _write_detail_checkpoint(conn, store, item, desc, img, error)
                results[item["url"]] = (desc, img)
                queue.task_done()
        finally:
            try:
                await page.close()
            except Exception:
                pass

    workers = [
        asyncio.create_task(worker(index), name=f"{store}-detail-{index}")
        for index in range(min(limit, queued))
    ]
    try:
        if workers:
            await asyncio.gather(*workers)
    except asyncio.CancelledError:
        for task in workers:
            task.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        raise
    finally:
        for task in workers:
            if not task.done():
                task.cancel()
        if workers:
            await asyncio.gather(*workers, return_exceptions=True)

    elapsed = time.perf_counter() - started
    metrics = {
        "store": store,
        "queued": queued,
        "checkpoint_hits": checkpoint_hits,
        "concurrency": limit,
        "elapsed_seconds": round(elapsed, 3),
        "pages_per_second": round(queued / elapsed, 4) if elapsed else 0.0,
    }
    if rate_limiter is not None:
        metrics.update(rate_limiter.metrics())
    log(f"  [Detail queue metrics] {json.dumps(metrics, ensure_ascii=False)}")
    return results, metrics


async def fetch_http_detail_queue(
    client: httpx.AsyncClient,
    conn: sqlite3.Connection,
    store: str,
    items: list[dict],
    *,
    concurrency: int | None = None,
    rate_limiter: AdaptiveRateLimiter | None = None,
    strict_block: bool = False,
) -> tuple[dict[str, tuple[str, str]], dict]:
    """HTTP counterpart of the resumable browser queue (currently iHaveCPU)."""
    limit = max(1, concurrency or DETAIL_CONCURRENCY.get(store, 1))
    results: dict[str, tuple[str, str]] = {}
    unique = {item["url"]: item for item in items if item.get("url")}
    pending: list[dict] = []
    checkpoint_hits = 0
    for url, item in unique.items():
        cached = _read_detail_checkpoint(conn, store, url)
        if cached is None:
            pending.append(item)
        else:
            results[url] = cached
            checkpoint_hits += 1

    started = time.perf_counter()
    semaphore = asyncio.Semaphore(limit)

    async def fetch_one(item: dict) -> None:
        async with semaphore:
            fetcher = fetch_jib_detail_http if store == "jib" else fetch_ihc_detail_http
            desc, img = await fetcher(
                client, item["url"], item.get("name", ""), item.get("category", ""),
                rate_limiter=rate_limiter, strict_block=strict_block,
            )
            _write_detail_checkpoint(conn, store, item, desc, img)
            results[item["url"]] = (desc, img)

    tasks = [
        asyncio.create_task(fetch_one(item), name=f"{store}-detail-{index}")
        for index, item in enumerate(pending)
    ]
    try:
        if tasks:
            await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
    finally:
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = time.perf_counter() - started
    metrics = {
        "store": store,
        "queued": len(pending),
        "checkpoint_hits": checkpoint_hits,
        "concurrency": limit,
        "elapsed_seconds": round(elapsed, 3),
        "pages_per_second": round(len(pending) / elapsed, 4) if elapsed else 0.0,
    }
    log(f"  [Detail queue metrics] {json.dumps(metrics, ensure_ascii=False)}")
    return results, metrics


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
        # Advice starts at one detail request at a time.  Its limiter can open
        # a longer shared pause when multiple 429s arrive in a rolling window.
        advice_limiter = AdaptiveRateLimiter("advice")
        api_client = httpx.AsyncClient(
            headers={"User-Agent": UA, "Accept": "application/json"},
            follow_redirects=True,
            timeout=httpx.Timeout(30.0, connect=15.0),
        )
        try:
            guest_response = await request_with_retry(
                api_client, "POST",
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
                        api_response = await request_with_retry(
                            api_client, "POST", ADVICE_API,
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
                    normalized: list[dict] = []
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
                        if source_url_is_out_of_scope(url):
                            log(f"    [Advice] out-of-scope search result skipped: {name[:70]}")
                            continue

                        actual_cat = detect_obvious_category(name, cat_name)
                        api_spec = it.get("spec") or ""
                        normalized.append({
                            "name": name, "price": price, "url": url,
                            "img": img, "category": actual_cat,
                            "api_spec": api_spec,
                        })

                    detail_items = [
                        item for item in normalized
                        if (fetch_details and item["url"] and
                            not item["url"].startswith("https://www.advice.co.th/search") and
                            source_payload_needs_detail(
                                item["api_spec"], item["img"], item["category"], "advice"
                            ) and
                            needs_detail(cur, matcher, item["name"], item["category"], "advice"))
                    ]
                    detail_results: dict[str, tuple[str, str]] = {}
                    if detail_items:
                        try:
                            detail_results, _metrics = await fetch_browser_detail_queue(
                                ctx, conn, "advice", detail_items,
                                concurrency=DETAIL_CONCURRENCY["advice"],
                                rate_limiter=advice_limiter,
                            )
                        except asyncio.CancelledError:
                            await browser.close()
                            raise

                    for item in normalized:
                        det_desc, det_img = detail_results.get(item["url"], ("", ""))
                        is_new = upsert_product(cur, matcher, {
                            "name": item["name"], "price": item["price"],
                            "img_url": det_img or item["img"], "url": item["url"],
                            "category": item["category"], "store": "advice",
                            # Advice's API spec is the most reliable source for
                            # compatibility fields. Keep it even when the page
                            # also exposes a longer marketing description.
                            "description": combine_descriptions(
                                item["api_spec"], det_desc
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
    detail_client = httpx.AsyncClient(
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

        for cat_name, base_url in JIB_CATS:
            if any(kw in base_url.lower() for kw in NOTEBOOK_URL_KW):
                log(f"  [JIB] SKIP notebook cat: {cat_name}")
                continue

            cat_new = cat_upd = 0
            for pn in range(1, pages + 1):
                url = base_url if pn == 1 else f"{base_url}/{pn}"
                log(f"  [JIB] {cat_name} p{pn}")

                try:
                    await goto_with_retry(page, url, timeout_ms=40000)
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
                normalized: list[dict] = []
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
                        if source_url_is_out_of_scope(prod_url):
                            continue

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

                        normalized.append({
                            "name": name, "price": price, "url": prod_url,
                            "img": img, "category": actual_cat,
                        })
                    except Exception as e:
                        log(f"    card err: {e}")

                detail_items = [
                    item for item in normalized
                    if (fetch_details and item["url"] and
                        needs_detail(cur, matcher, item["name"], item["category"], "jib"))
                ]
                detail_results: dict[str, tuple[str, str]] = {}
                if detail_items:
                    try:
                        detail_results, _metrics = await fetch_http_detail_queue(
                            detail_client, conn, "jib", detail_items,
                            concurrency=DETAIL_CONCURRENCY["jib"],
                        )
                    except asyncio.CancelledError:
                        await detail_client.aclose()
                        await browser.close()
                        raise

                for item in normalized:
                    try:
                        det_desc, det_img = detail_results.get(item["url"], ("", ""))
                        is_new = upsert_product(cur, matcher, {
                            "name": item["name"], "price": item["price"],
                            "img_url": det_img or item["img"], "url": item["url"],
                            "category": item["category"], "store": "jib",
                            "description": det_desc,
                        })
                        if is_new:
                            cat_new += 1
                        else:
                            cat_upd += 1
                        count += 1

                    except Exception as e:
                        log(f"    upsert err: {e}")

                conn.commit()
                log(f"    -> {count} products processed")
                if count == 0 and pn > 1:
                    break

            total_new += cat_new
            total_upd += cat_upd
            log(f"  [JIB] {cat_name}: +{cat_new} new, ~{cat_upd} merged")
            await asyncio.sleep(random.uniform(1, 2))

        await browser.close()
        await detail_client.aclose()

    log(f"  [JIB] TOTAL: {total_new} new | {total_upd} merged into existing")
    return total_new, total_upd


# ─────────────────────────────────────────────────────────────────────────────
# Scraper: iHaveCPU (HTML category pages)
# ─────────────────────────────────────────────────────────────────────────────
async def scrape_ihavecpu(conn: sqlite3.Connection, matcher: SmartMatcher,
                          pages: int = 3, fetch_details: bool = False,
                          full_catalog: bool = False,
                          categories: list[tuple[str, str]] | None = None,
                          full_interval_seconds: float = 1.5):
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
    limiter = (AdaptiveRateLimiter(
        "ihavecpu", threshold=2, base_cooldown_seconds=30,
        max_cooldown_seconds=180, min_interval_seconds=full_interval_seconds,
    ) if full_catalog else None)
    async with httpx.AsyncClient(
        headers=headers, follow_redirects=True, timeout=timeout
    ) as client:
        for cat_name, configured_url in (
            categories if categories is not None else
            (IHC_FULL_CATS if full_catalog else IHC_CATS)
        ):
            base_url = configured_url.replace("www.ihavecpu.com", "ihavecpu.com")
            cat_new = cat_upd = 0
            seen_ids: set[int] = set()
            pn = 1
            page_limit = pages if not full_catalog else None
            reported_total = 0
            full_page_safety_limit = 0

            while page_limit is None or pn <= page_limit:
                url = base_url if pn == 1 else f"{base_url}?page={pn}"
                log(f"  [iHaveCPU] {cat_name} p{pn}")
                try:
                    response = await request_with_retry(
                        client, "GET", url, rate_limiter=limiter,
                    )
                    if full_catalog and response.status_code in (403, 429):
                        raise PermissionError(f"iHaveCPU listing blocked: HTTP {response.status_code}")
                    response.raise_for_status()
                    items = ihc_listing_products(response.text)
                except Exception as e:
                    log(f"    [iHaveCPU HTTP err] {str(e)[:120]}")
                    if full_catalog:
                        raise
                    break
                if not items:
                    if full_catalog and len(seen_ids) < reported_total:
                        raise RuntimeError(
                            f"iHaveCPU ended {cat_name} at {len(seen_ids)}/{reported_total} products"
                        )
                    log("    no structured products")
                    break

                if full_catalog and not reported_total:
                    reported_total = ihc_listing_total(response.text)
                    if not reported_total:
                        raise RuntimeError(f"iHaveCPU did not provide a product total: {url}")
                    # Pages overlap by 12 items even though each renders 24.
                    # Drive completion by unique product IDs, not a guessed page count.
                    full_page_safety_limit = reported_total + 2
                    log(f"    {reported_total} listing products; scanning until all IDs are seen")

                page_ids = {item.get("product_id") for item in items if item.get("product_id")}
                if full_catalog and page_ids and page_ids.issubset(seen_ids):
                    raise RuntimeError(f"iHaveCPU repeated a category page: {url}")

                detail_results = {}
                if full_catalog:
                    detail_items = []
                    for item in items:
                        raw_name = (item.get("name_th") or item.get("name_gb") or "").strip()
                        if not item.get("product_id") or not raw_name:
                            continue
                        item_name = clean_ihc_name(raw_name)
                        detail_items.append({
                            "url": ihc_item_url(item),
                            "name": item_name,
                            "category": ihc_full_category(item_name, cat_name),
                        })
                    detail_results, _metrics = await fetch_http_detail_queue(
                        client, conn, "ihavecpu", detail_items, concurrency=1,
                        rate_limiter=limiter, strict_block=True,
                    )

                count = 0
                for item in items:
                    product_id = item.get("product_id")
                    if not product_id or product_id in seen_ids:
                        continue
                    seen_ids.add(product_id)
                    raw = (item.get("name_th") or item.get("name_gb") or "").strip()
                    if not raw or (not full_catalog and (
                            should_skip(raw) or any(s in raw.upper() for s in IHC_SKIP))):
                        continue
                    name = clean_ihc_name(raw)
                    price = parse_price(
                        str(item.get("price_sale") or item.get("price_before") or ""),
                        min_price=1 if full_catalog else 200,
                    )
                    actual_cat = ihc_full_category(name, cat_name) if full_catalog else (
                        "PC Set" if is_pc_set_name(name) else cat_name
                    )
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

                    prod_url = ihc_item_url(item)
                    img = (item.get("image800") or item.get("image") or "").strip()
                    desc = ihc_product_description(item)
                    if full_catalog:
                        det_desc, det_img = detail_results.get(prod_url, ("", ""))
                        desc = combine_descriptions(det_desc, desc)
                        img = det_img or img
                    elif (fetch_details and prod_url and
                            source_payload_needs_detail(desc, img) and
                            needs_detail(cur, matcher, name, actual_cat, "ihavecpu")):
                        try:
                            detail_response = await request_with_retry(
                                client, "GET", prod_url
                            )
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
                        "full_catalog": full_catalog,
                    })
                    if full_catalog:
                        stored = cur.execute(
                            "SELECT product_id FROM products WHERE url_ihavecpu LIKE ? LIMIT 1",
                            (f"%/product/{int(product_id)}/%",),
                        ).fetchone()
                        cur.execute("""
                            INSERT INTO ihavecpu_scrape_inventory
                                (category_url, source_product_id, category, product_name,
                                 price, image_url, description, product_url,
                                 db_product_id, scraped_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(category_url, source_product_id) DO UPDATE SET
                                category=excluded.category,
                                product_name=excluded.product_name,
                                price=excluded.price,
                                image_url=excluded.image_url,
                                description=excluded.description,
                                product_url=excluded.product_url,
                                db_product_id=excluded.db_product_id,
                                scraped_at=excluded.scraped_at
                        """, (
                            base_url, int(product_id), actual_cat, name, price,
                            img, desc, prod_url, stored[0] if stored else "",
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        ))
                    if is_new:
                        cat_new += 1
                    else:
                        cat_upd += 1
                    count += 1

                conn.commit()
                log(f"    -> {count} structured products processed; {len(seen_ids)}/{reported_total or '?'} unique IDs")
                if not full_catalog and (count == 0 or len(items) < 24):
                    break
                if full_catalog and len(seen_ids) >= reported_total:
                    break
                pn += 1
                if full_catalog and pn > full_page_safety_limit:
                    raise RuntimeError(
                        f"iHaveCPU pagination stalled: {cat_name} {len(seen_ids)}/{reported_total}"
                    )

            total_new += cat_new
            total_upd += cat_upd
            log(f"  [iHaveCPU] {cat_name}: +{cat_new} new, ~{cat_upd} merged")

    log(f"  [iHaveCPU] TOTAL: {total_new} new | {total_upd} merged into existing")
    return total_new, total_upd


def apply_successful_detail_checkpoints(
    conn: sqlite3.Connection, stores: list[str]
) -> int:
    """Attach completed queue results that an ambiguous matcher did not apply.

    Checkpoints are keyed by the authoritative source URL.  This reconciliation
    is intentionally conservative: it only fills a missing description when a
    same-category URL slug has a strong, conflict-free score for the row.
    """
    columns = {
        "jib": ("price_jib", "url_jib", "desc_jib"),
        "ihavecpu": ("price_ihavecpu", "url_ihavecpu", "desc_ihavecpu"),
        "advice": ("price_advice", "url_advice", "desc_advice"),
    }
    cur = conn.cursor()
    applied = 0
    for store in stores:
        price_col, url_col, desc_col = columns[store]
        checkpoints = cur.execute(
            "SELECT url, category, description, image_url "
            "FROM scrape_detail_checkpoint "
            "WHERE store=? AND status='success' AND length(trim(description))>=30",
            (store,),
        ).fetchall()
        if not checkpoints:
            continue
        rows = cur.execute(
            f"SELECT product_id, p_name, category FROM products "
            f"WHERE {price_col}>0 AND length(trim(coalesce({desc_col},'')))<30"
        ).fetchall()
        for pid, name, category in rows:
            candidates = []
            for url, checkpoint_category, desc, img in checkpoints:
                if checkpoint_category != category:
                    continue
                score = source_url_score(name or "", url or "", category or "")
                if score >= 2 and not source_url_conflicts(
                    name or "", url or "", category or ""
                ):
                    candidates.append((score, url, desc, img))
            if not candidates:
                continue
            score, url, desc, img = max(candidates, key=lambda item: item[0])
            cur.execute(
                f"UPDATE products SET {url_col}=?, {desc_col}=?, "
                "img_url=CASE WHEN trim(coalesce(img_url,''))='' THEN ? ELSE img_url END, "
                "specs=CASE WHEN trim(coalesce(specs,''))='' THEN ? ELSE specs END, "
                "updated_at=? WHERE product_id=?",
                (url, desc, img, desc,
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pid),
            )
            applied += 1
            log(f"  [checkpoint reconcile] {store} score={score}: {(name or '')[:65]}")
    if applied:
        conn.commit()
    return applied


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
    pending: dict[str, list[tuple[str, str, str, str, str]]] = {
        store: [] for store in stores
    }
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
            if (source_payload_needs_detail(
                    _desc or '', 'present', _category or '', store
                ) or not detail_description_is_relevant(
                    _name or '', _desc or '', _category or ''
                )):
                pending[store].append(row)

    pending_count = sum(len(rows) for rows in pending.values())
    if not pending_count:
        log("  [Detail backfill] no missing store descriptions")
        return {store: 0 for store in stores}

    log(f"  [Detail backfill] {pending_count} product URLs queued")
    updated = {store: 0 for store in stores}
    cleared = 0
    advice_limiter = AdaptiveRateLimiter("advice")
    async with httpx.AsyncClient(
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
        },
        follow_redirects=True,
        timeout=httpx.Timeout(30.0, connect=15.0),
    ) as ihc_client:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
            )
            try:
                ctx = await browser.new_context(
                    user_agent=UA, viewport={"width": 1280, "height": 800}
                )
                await ctx.add_init_script(ANTI_BOT)

                for store in stores:
                    valid_items: list[dict] = []
                    rows_by_url: dict[str, tuple[str, str, str, str, str]] = {}
                    for pid, name, category, url, old_desc in pending.get(store, []):
                        url_col, desc_col = columns[store]
                        if source_url_conflicts(name or "", url or "", category or ""):
                            cur.execute(
                                f"UPDATE products SET {url_col}='', {desc_col}='', updated_at=? "
                                "WHERE product_id=?",
                                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pid),
                            )
                            cleared += 1
                            continue
                        item = {
                            "url": url, "name": name or "",
                            "category": category or "",
                        }
                        valid_items.append(item)
                        rows_by_url[url] = (pid, name, category, url, old_desc)
                    conn.commit()

                    if store in {"ihavecpu", "jib"}:
                        detail_results, _metrics = await fetch_http_detail_queue(
                            ihc_client, conn, store, valid_items,
                            concurrency=DETAIL_CONCURRENCY[store],
                        )
                    else:
                        detail_results, _metrics = await fetch_browser_detail_queue(
                            ctx, conn, store, valid_items,
                            concurrency=DETAIL_CONCURRENCY[store],
                            rate_limiter=advice_limiter if store == "advice" else None,
                            timeout_ms=10000, settle_ms=1000,
                        )

                    for index, (url, row) in enumerate(rows_by_url.items(), 1):
                        pid, name, category, _url, old_desc = row
                        _url_col, desc_col = columns[store]
                        desc, img = detail_results.get(url, ("", ""))
                        if desc:
                            cur.execute(
                                f"UPDATE products SET {desc_col} = ?, "
                                "img_url = CASE WHEN ? != '' THEN ? ELSE img_url END, "
                                "specs = CASE WHEN (specs IS NULL OR specs='') AND ? != '' "
                                "THEN ? ELSE specs END, updated_at=? WHERE product_id=?",
                                (desc, img, img, desc, desc,
                                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pid),
                            )
                            updated[store] += 1
                        else:
                            log(
                                f"    [{store} missing description] "
                                f"product_id={pid} url={url}"
                            )
                            if not detail_description_is_relevant(
                                name, old_desc or "", category
                            ):
                                cur.execute(
                                    f"UPDATE products SET {desc_col}='', updated_at=? "
                                    "WHERE product_id=?",
                                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pid),
                                )
                        if index % 25 == 0:
                            conn.commit()
                            log(
                                f"    [Detail backfill] store={store} "
                                f"{index}/{len(rows_by_url)} processed"
                            )
                    conn.commit()
            finally:
                await browser.close()

    log(f"  [Detail backfill] updated: {updated} | cleared mismatches: {cleared}")
    return updated


# ─────────────────────────────────────────────────────────────────────────────
# Main orchestrator
# ─────────────────────────────────────────────────────────────────────────────
async def run_all(stores: list[str], pages: int, fetch_details: bool = False,
                  backfill_only: bool = False):
    conn = sqlite3.connect(DB_PATH)
    # asyncio.wait_for cancels this coroutine when a bounded QA run expires.
    # Close SQLite from the task completion callback even if cancellation
    # happens inside a store/browser context before the normal close below.
    task = asyncio.current_task()
    if task is not None:
        task.add_done_callback(lambda _task: conn.close())
    setup_db(conn)
    repair_pc_set_categories(conn)
    repair_obvious_product_categories(conn)
    repair_conflicting_source_data(conn)
    repair_out_of_scope_source_data(conn)
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
        apply_successful_detail_checkpoints(conn, stores)
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
        "--ihavecpu-full", action="store_true", default=False,
        help="Scrape every page of the twelve iHaveCPU categories and visit every product",
    )
    parser.add_argument(
        "--ihavecpu-categories", nargs="+", metavar="SLUG",
        help="With --ihavecpu-full, scrape only these category URL slugs",
    )
    parser.add_argument(
        "--ihavecpu-interval", type=float, default=1.5,
        help="Minimum seconds between iHaveCPU requests during a full scrape",
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
    if args.ihavecpu_interval < 0.8:
        parser.error("--ihavecpu-interval must be at least 0.8 seconds")

    stores = ["advice", "jib", "ihavecpu"] if "all" in args.stores else args.stores

    if args.ihavecpu_full:
        if args.backfill_only:
            parser.error("--ihavecpu-full cannot be combined with --backfill-only")
        category_by_slug = {
            url.rsplit("/", 1)[-1]: (name, url) for name, url in IHC_FULL_CATS
        }
        selected_categories = IHC_FULL_CATS
        if args.ihavecpu_categories:
            unknown = sorted(set(args.ihavecpu_categories) - category_by_slug.keys())
            if unknown:
                parser.error(f"Unknown iHaveCPU category slug(s): {', '.join(unknown)}")
            selected_categories = [
                category_by_slug[slug] for slug in dict.fromkeys(args.ihavecpu_categories)
            ]
        conn = sqlite3.connect(DB_PATH)
        try:
            setup_db(conn)
            matcher = SmartMatcher(conn.cursor())
            asyncio.run(scrape_ihavecpu(
                conn, matcher, pages=0, fetch_details=True, full_catalog=True,
                categories=selected_categories,
                full_interval_seconds=args.ihavecpu_interval,
            ))
        finally:
            conn.close()
        if not args.skip_compat_training:
            trainer = os.path.join(os.path.dirname(__file__), "train_compat_knowledge.py")
            completed = subprocess.run(
                [sys.executable, "-X", "utf8", trainer, "--apply"], check=False
            )
            if completed.returncode != 0:
                log("[Compat Knowledge] Training failed; raw scraped details remain intact")
        return

    if args.ihavecpu_categories:
        parser.error("--ihavecpu-categories requires --ihavecpu-full")

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
