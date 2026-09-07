"""
extract_compat_specs.py
========================
ดึง spec ที่สำคัญสำหรับ compatibility จากหน้า product ของ 3 ร้าน
แล้วเก็บลง DB column `specs` เป็นรูปแบบ "Key: Value" แต่ละบรรทัด

Fields ที่สำคัญ:
  - CPU    : Socket, TDP, Max Memory Type (DDR4/DDR5)
  - MB     : Socket, Memory Type, Form Factor, Max Memory Speed
  - RAM    : DDR Gen, Speed (MHz), Capacity (GB), Voltage
  - GPU    : TDP, Power Connector, VRAM
  - PSU    : Wattage, 80+ Grade, Modular
  - Case   : Form Factor support, Max Cooler Height
  - Cooler : TDP Rating, Socket Support, Height (mm)

รัน:
  python -X utf8 extract_compat_specs.py all 100
  python -X utf8 extract_compat_specs.py ihavecpu 50
  python -X utf8 extract_compat_specs.py jib 50
  python -X utf8 extract_compat_specs.py advice 50
"""

import asyncio, re, sqlite3, sys
from datetime import datetime, timezone
from playwright.async_api import async_playwright

DB_PATH = "shop.db"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
ANTI_BOT = ("Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            "window.chrome={runtime:{}};")

def log(msg):
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"), flush=True)

# ─────────────────────────────────────────────────────────────────────────────
# Compat-relevant key filters
# ─────────────────────────────────────────────────────────────────────────────
COMPAT_KEYS = [
    "required system power", "minimum system power", "recommended psu", "recommended power supply",
    "total graphics power", "total board power", "maximum turbo power",
    "socket", "cpu socket", "platform",
    "tdp", "thermal design power", "power consumption", "wattage",
    "max memory type", "memory type", "supported memory", "memory standard",
    "memory speed", "max memory speed", "memory frequency", "memory slot",
    "memory channel", "max memory",
    "chipset", "form factor", "form-factor",
    "ddr", "capacity", "frequency", "speed", "voltage", "cl latency", "cas latency",
    "cuda", "stream processor", "vram", "memory bus",
    "recommended psu", "minimum psu", "power connector", "pcie power",
    "80 plus", "80+", "modular",
    "supported motherboard", "max gpu length", "max cooler height", "cooler clearance",
    "radiator support", "drive bay",
    "socket support", "compatible socket", "rated tdp", "height",
    "fan size",
]

def is_compat_key(key: str) -> bool:
    k = key.lower()
    return any(ck in k for ck in COMPAT_KEYS)

def filter_compat_lines(raw_text: str) -> str:
    lines = raw_text.strip().splitlines()
    kept = []
    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        parts = re.split(r":\s+|\t", line, maxsplit=1)
        if len(parts) == 2:
            key, val = parts[0].strip(), parts[1].strip()
            if is_compat_key(key) and val:
                kept.append(f"{key}: {val}")
        elif is_compat_key(line):
            kept.append(line)
    return "\n".join(kept)

# ─────────────────────────────────────────────────────────────────────────────
# iHaveCPU
# ─────────────────────────────────────────────────────────────────────────────
async def fetch_ihc_specs(page, url: str) -> str:
    try:
        await page.goto(url, timeout=35000, wait_until="domcontentloaded")
        await page.wait_for_timeout(2500)
        spec_text = await page.evaluate("""
            () => {
                const el = document.getElementById('__NEXT_DATA__');
                if (!el) return null;
                try {
                    const data = JSON.parse(el.textContent);
                    const product = data?.props?.pageProps?.product;
                    if (!product) return null;
                    const props = product.property;
                    if (!props || !Array.isArray(props) || props.length === 0) return null;
                    return props.map(p => {
                        const key = p.filter_text || p.name_th || p.name_gb || '';
                        const vals = (p.detail || []).map(d => d.name_th || d.name_gb || '').join(', ');
                        return key + ': ' + vals;
                    }).filter(line => line.trim().length > 2).join('\n');
                } catch(e) { return null; }
            }
        """)
        if spec_text and len(spec_text) > 10:
            return filter_compat_lines(spec_text)

        spec_text = await page.evaluate("""
            () => {
                const rows = document.querySelectorAll('table tr');
                const seen = new Set(); const lines = [];
                for (const r of rows) {
                    const cells = r.querySelectorAll('td, th');
                    if (cells.length >= 2) {
                        const key = cells[0].innerText.trim();
                        const val = cells[1].innerText.trim();
                        if (key && !seen.has(key)) { seen.add(key); lines.push(key + ': ' + val); }
                    }
                }
                return lines.join('\n');
            }
        """)
        if spec_text and len(spec_text) > 10:
            return filter_compat_lines(spec_text)
    except Exception as e:
        log(f"    [iHaveCPU spec err] {e}")
    return ""

# ─────────────────────────────────────────────────────────────────────────────
# JIB
# ─────────────────────────────────────────────────────────────────────────────
async def fetch_jib_specs(page, url: str) -> str:
    try:
        await page.goto(url, timeout=35000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3500)
        spec_text = await page.evaluate("""
            () => {
                const selectors = [
                    'table.table-spec', 'table.spec', '#detail_spec',
                    'div.product-spec table', 'table.table-bordered',
                    'div[id*="spec"]', 'div[class*="spec"]'
                ];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (!el) continue;
                    const rows = el.querySelectorAll('tr');
                    const seen = new Set(); const lines = [];
                    for (const r of rows) {
                        const cells = r.querySelectorAll('td, th');
                        if (cells.length >= 2) {
                            const key = cells[0].innerText.trim();
                            const val = cells[1].innerText.trim();
                            if (key && val && !seen.has(key)) { seen.add(key); lines.push(key + ': ' + val); }
                        }
                    }
                    if (lines.length > 0) return lines.join('\n');
                }
                return null;
            }
        """)
        if spec_text and len(spec_text) > 10:
            return filter_compat_lines(spec_text)
    except Exception as e:
        log(f"    [JIB spec err] {e}")
    return ""

# ─────────────────────────────────────────────────────────────────────────────
# Advice
# ─────────────────────────────────────────────────────────────────────────────
async def fetch_advice_specs(page, url: str) -> str:
    try:
        await page.goto(url, timeout=35000, wait_until="networkidle")
        await page.wait_for_timeout(3000)
        spec_text = await page.evaluate("""
            () => {
                const selectors = [
                    'table.spec-table', 'div.spec-content', 'div.product-spec',
                    'table', 'div[class*="spec"]', 'div[id*="spec"]',
                    '#tab-spec', '#tab-description', 'div.product-detail-content'
                ];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (!el) continue;
                    const rows = el.querySelectorAll('tr');
                    if (rows.length >= 2) {
                        const seen = new Set(); const lines = [];
                        for (const r of rows) {
                            const cells = r.querySelectorAll('td, th');
                            if (cells.length >= 2) {
                                const key = cells[0].innerText.trim();
                                const val = Array.from(cells).slice(1).map(c => c.innerText.trim()).join(' ').trim();
                                if (key && val && !seen.has(key)) { seen.add(key); lines.push(key + ': ' + val); }
                            }
                        }
                        if (lines.length > 0) return lines.join('\n');
                    }
                    const t = el.innerText.trim();
                    if (t && t.length > 30) return t;
                }
                return null;
            }
        """)
        if spec_text and len(spec_text) > 10:
            return filter_compat_lines(spec_text)
    except Exception as e:
        log(f"    [Advice spec err] {e}")
    return ""

# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
FETCH_FN = {
    "advice":   fetch_advice_specs,
    "jib":      fetch_jib_specs,
    "ihavecpu": fetch_ihc_specs,
}

async def extract_for_store(store: str, batch: int = 100):
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    url_col   = f"url_{store}"
    price_col = f"price_{store}"

    cur.execute(f"""
        SELECT product_id, p_name, category, {url_col}
        FROM products
        WHERE {url_col} != '' AND {url_col} IS NOT NULL
          AND {price_col} > 0
          AND (specs IS NULL OR specs = '' OR LENGTH(specs) < 50)
        ORDER BY category, p_name
        LIMIT ?
    """, (batch,))
    rows = cur.fetchall()

    if not rows:
        log(f"[{store}] No products need spec extraction (batch={batch})")
        conn.close()
        return

    log(f"[{store}] Extracting compat specs for {len(rows)} products...")
    fetch_fn = FETCH_FN[store]

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        ctx = await browser.new_context(user_agent=UA, viewport={"width": 1280, "height": 900})
        await ctx.add_init_script(ANTI_BOT)
        page = await ctx.new_page()

        success = fail = 0
        for i, (pid, name, cat, url) in enumerate(rows):
            if not url:
                continue
            log(f"  [{i+1}/{len(rows)}] [{cat}] {name[:55]}")
            specs = await fetch_fn(page, url)

            # Reject mismatched GPU detail pages (merged store URLs can point at another SKU).
            if specs and cat == "GPU":
                title = await page.title()
                expected = re.search(r"\b(?:RTX\s*(?:PRO\s*)?\d{4}|RX\s*\d{4})(?:\s*(?:TI|SUPER|XT|XTX))?", name, re.I)
                normalize = lambda value: re.sub(r"[^A-Z0-9]", "", value.upper())
                identity_tokens = re.findall(r"\b(?:ASUS|MSI|GIGABYTE|GALAX|INNO3D|COLORFUL|LEADTEK|PRIME|DUAL|WINDFORCE|GAMING|TWIN|ULTRA|BLACKWELL)\b", name, re.I)
                if (expected and normalize(expected[0]) not in normalize(title)) or any(normalize(t) not in normalize(title) for t in identity_tokens):
                    log("    -> skipped: source page does not match product model/board")
                    continue
            if specs and len(specs) > 10:
                specs += f"\nSource URL: {page.url}\nSource checked at: {datetime.now(timezone.utc).isoformat()}"
                cur.execute("UPDATE products SET specs = ? WHERE product_id = ?", (specs, pid))
                conn.commit()
                success += 1
                lines = specs.count("\n") + 1
                log(f"    -> OK: {lines} compat fields extracted")
                for line in specs.splitlines()[:6]:
                    log(f"       {line}")
                if lines > 6:
                    log(f"       ... (+{lines-6} more)")
            else:
                fail += 1
                log(f"    -> no compat specs found")

        await browser.close()
    conn.close()
    log(f"\n[{store}] Done: {success} OK, {fail} not found")

async def main():
    store_arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    batch     = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    stores = ["advice", "jib", "ihavecpu"] if store_arg == "all" else [store_arg]
    for s in stores:
        if s not in FETCH_FN:
            log(f"Unknown store: {s}"); continue
        await extract_for_store(s, batch)

if __name__ == "__main__":
    asyncio.run(main())
