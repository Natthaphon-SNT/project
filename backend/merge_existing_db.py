# -*- coding: utf-8 -*-
"""
Merge duplicate products across stores in shop.db with refined matching
"""
import sqlite3
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB_PATH = "shop.db"

NOISE_WORDS = {
    'CPU', 'VGA', 'GPU', 'RAM', 'SSD', 'M2', 'M.2', 'PSU', 'CASE', 'LIQUID', 
    'COOLER', 'MONITOR', 'KEYBOARD', 'MOUSE', 'HEADSET', 'MAINBOARD', 'MOTHERBOARD', 
    'NEXT', 'TRAY', 'BOX', 'PLUS', 'SERIES', 'GAMING', 'WARRANTY', '3Y', '5Y', '2Y', '1Y',
    'WITH', 'FAN', 'FANS', 'DDR4', 'DDR5', 'GEN', 'RETAIL', 'OEM', 'SANS', 'BLACK', 'WHITE',
    'EDITION', 'PRO', 'MAX', 'SUPER', 'TI' # Note: TI/SUPER keep in tokens if needed, but let's check
}

# Unit patterns to ignore in model codes
UNIT_PATTERN = re.compile(r'^\d+(\.\d+)?(GHZ|MHZ|MB|GB|TB|W|MM|RPM)$', re.IGNORECASE)
CORE_PATTERN = re.compile(r'^\d+[CT]$', re.IGNORECASE)

def get_product_signature(name: str):
    n = name.upper()
    # Remove Thai
    n = re.sub(r'[\u0E00-\u0E7F]+', ' ', n)
    # Remove brackets
    n = re.sub(r'\(.*?\)|\[.*?\]', ' ', n)
    # Replace separators
    n = re.sub(r'[\-_/+,:]+', ' ', n)
    
    words = [w for w in n.split() if w]
    
    # Specific model identifiers: e.g. 250K, 250KF, 14900K, 7800X3D, 4070, 4070TI, 4060, B650M, Z790, SN850X, 990PRO
    model_codes = set()
    for w in words:
        if UNIT_PATTERN.match(w) or CORE_PATTERN.match(w):
            continue
        if w in {'3Y', '5Y', '2Y', '1Y', 'DDR4', 'DDR5', 'WARRANTY'}:
            continue
        # Words containing digits (e.g. 250K, 4070, B650, 1851, 14700)
        if re.search(r'\d', w):
            model_codes.add(w)
            
    # Significant word tokens
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
    # Check category compatibility
    c1, c2 = (p1_cat or '').lower(), (p2_cat or '').lower()
    if c1 and c2 and c1 != c2:
        if not ('cooler' in c1 and 'cooler' in c2):
            return False

    # 1. Exact match
    if p1_name.strip().upper() == p2_name.strip().upper():
        return True

    m1, t1 = get_product_signature(p1_name)
    m2, t2 = get_product_signature(p2_name)

    # 2. Strong model code match (e.g. 250K in both, or RTX 4070 in both)
    # Check key SKU numbers
    if m1 and m2:
        # If both have model codes, the primary SKU codes must match
        # Specifically: numbers with letters like 250K, 250KF, 14900K, 7800X3D, B650M, RTX4070
        sku_m1 = {x for x in m1 if re.search(r'[A-Z]', x) and re.search(r'\d', x)}
        sku_m2 = {x for x in m2 if re.search(r'[A-Z]', x) and re.search(r'\d', x)}
        
        if sku_m1 and sku_m2:
            if sku_m1 == sku_m2:
                # Suffixes like KF vs K must not conflict
                sim = token_similarity(t1, t2)
                if sim >= 0.25:
                    return True
            else:
                # Different SKU codes (e.g. 250K vs 250KF) -> NOT same product
                return False
        
        # If pure numbers (e.g. 1851, 4070)
        intersect = m1 & m2
        if len(intersect) >= 2:
            sim = token_similarity(t1, t2)
            if sim >= 0.35:
                return True
        elif len(intersect) == 1:
            # e.g., only 250K or only 4070
            sim = token_similarity(t1, t2)
            if sim >= 0.40:
                return True

    # 3. High token similarity
    sim = token_similarity(t1, t2)
    if sim >= 0.65:
        return True

    return False

def merge_duplicates():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM products")
    total_before = cur.fetchone()[0]

    cols = [c[1] for c in cur.execute("PRAGMA table_info(products)").fetchall()]
    rows = cur.execute("SELECT * FROM products ORDER BY product_id").fetchall()
    
    products = [dict(zip(cols, r)) for r in rows]

    merged_count = 0
    deleted_pids = set()
    active_records = []

    for p in products:
        p_name = (p.get("p_name") or "").strip()
        p_cat = (p.get("category") or "").strip()
        if not p_name:
            continue

        matched_master = None
        for master in active_records:
            if is_same_product(p_name, p_cat, master["p_name"], master.get("category") or ""):
                matched_master = master
                break

        if matched_master:
            m_pid = matched_master["product_id"]
            p_pid = p["product_id"]

            # Combine prices
            p_adv = p.get("price_advice") or 0
            p_jib = p.get("price_jib") or 0
            p_ihc = p.get("price_ihavecpu") or 0

            if p_adv > 0 and (matched_master.get("price_advice") or 0) == 0:
                matched_master["price_advice"] = p_adv
            if p_jib > 0 and (matched_master.get("price_jib") or 0) == 0:
                matched_master["price_jib"] = p_jib
            if p_ihc > 0 and (matched_master.get("price_ihavecpu") or 0) == 0:
                matched_master["price_ihavecpu"] = p_ihc

            # Combine URLs
            if p.get("url_advice") and not matched_master.get("url_advice"):
                matched_master["url_advice"] = p["url_advice"]
            if p.get("url_jib") and not matched_master.get("url_jib"):
                matched_master["url_jib"] = p["url_jib"]
            if p.get("url_ihavecpu") and not matched_master.get("url_ihavecpu"):
                matched_master["url_ihavecpu"] = p["url_ihavecpu"]

            # Combine descriptions
            if p.get("desc_advice") and not matched_master.get("desc_advice"):
                matched_master["desc_advice"] = p["desc_advice"]
            if p.get("desc_jib") and not matched_master.get("desc_jib"):
                matched_master["desc_jib"] = p["desc_jib"]
            if p.get("desc_ihavecpu") and not matched_master.get("desc_ihavecpu"):
                matched_master["desc_ihavecpu"] = p["desc_ihavecpu"]

            if not matched_master.get("p_description") and p.get("p_description"):
                matched_master["p_description"] = p["p_description"]

            if not matched_master.get("img_url") and p.get("img_url"):
                matched_master["img_url"] = p["img_url"]

            # Update base p_price (minimum positive price)
            prices = [
                matched_master.get("price_advice") or 0,
                matched_master.get("price_jib") or 0,
                matched_master.get("price_ihavecpu") or 0
            ]
            valid_prices = [pr for pr in prices if pr > 0]
            if valid_prices:
                matched_master["p_price"] = min(valid_prices)

            deleted_pids.add(p_pid)
            merged_count += 1
        else:
            active_records.append(p)

    print(f"Total products before: {total_before}")
    print(f"Found {merged_count} duplicate items to merge into {len(active_records)} distinct products.")

    # Apply updates to DB
    for master in active_records:
        cur.execute("""
            UPDATE products SET
                price_advice = ?,
                price_jib = ?,
                price_ihavecpu = ?,
                url_advice = ?,
                url_jib = ?,
                url_ihavecpu = ?,
                desc_advice = ?,
                desc_jib = ?,
                desc_ihavecpu = ?,
                p_description = ?,
                img_url = ?,
                p_price = ?
            WHERE product_id = ?
        """, (
            master.get("price_advice") or 0,
            master.get("price_jib") or 0,
            master.get("price_ihavecpu") or 0,
            master.get("url_advice") or "",
            master.get("url_jib") or "",
            master.get("url_ihavecpu") or "",
            master.get("desc_advice") or "",
            master.get("desc_jib") or "",
            master.get("desc_ihavecpu") or "",
            master.get("p_description") or "",
            master.get("img_url") or "",
            master.get("p_price") or 0,
            master["product_id"],
        ))

    if deleted_pids:
        cur.executemany("DELETE FROM products WHERE product_id = ?", [(pid,) for pid in deleted_pids])

    conn.commit()

    # Verify 250K product specifically
    print("\n--- Verifying Intel Core Ultra 5 250K after merge ---")
    rows250 = cur.execute("SELECT product_id, p_name, price_advice, price_jib, price_ihavecpu, url_advice, url_jib, url_ihavecpu FROM products WHERE p_name LIKE '%250K%'").fetchall()
    for r in rows250:
        print(f"PID: {r[0]}")
        print(f"Name: {r[1]}")
        print(f"Advice: {r[2]} | {r[5]}")
        print(f"JIB: {r[3]} | {r[6]}")
        print(f"iHaveCPU: {r[4]} | {r[7]}")
        print("-" * 50)

    cur.execute("SELECT COUNT(*) FROM products")
    total_after = cur.fetchone()[0]
    multi = cur.execute("""
        SELECT COUNT(*) FROM products WHERE
        (CASE WHEN price_advice>0 THEN 1 ELSE 0 END +
         CASE WHEN price_jib>0    THEN 1 ELSE 0 END +
         CASE WHEN price_ihavecpu>0 THEN 1 ELSE 0 END) >= 2
    """).fetchone()[0]

    print(f"\nTotal products after: {total_after}")
    print(f"Multi-store products (>= 2 stores): {multi}")
    conn.close()

if __name__ == "__main__":
    merge_duplicates()
