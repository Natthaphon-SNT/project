"""Resumable full JIB crawl for selected product groups.

Listings and product details are separate phases so a temporary block never
turns an unfinished detail run into an apparently complete catalogue.
"""

import argparse
import asyncio
from collections import defaultdict
from datetime import datetime
import os
import random
import re
import sqlite3
import subprocess
import sys
from urllib.parse import quote_plus, urljoin

import httpx
from bs4 import BeautifulSoup

import full_scraper as core


JIB_FULL_GROUPS = {
    42: "PC Components",
    58: "Monitor",
    60: "Storage",
    1419: "Keyboard / Mouse",
    1420: "Headset",
    1393: "Cooling",
    1263: "Gaming Chair",
    1466: "Gaming Desk",
}
JIB_SEARCH_GROUPS = {
    # JIB's category pages do not expose reliable pagination for these groups.
    # Search provides an explicit next-page link; classify() rejects unrelated
    # matches returned by its broad text search.
    1263: "gaming chair",
    1466: "gaming desk",
}
PRODUCT_ID = re.compile(r"/readProduct/(\d+)/", re.I)
COLORS = ("BLACK", "WHITE", "RED", "BLUE", "PINK", "GREEN", "GRAY",
          "SILVER", "GOLD", "PURPLE")


def explicit_color_conflict(first: str, second: str) -> bool:
    def colors(name: str) -> set[str]:
        upper = name.upper().replace("GREY", "GRAY")
        return {color for color in COLORS
                if re.search(rf"\b{color}\b", upper)}

    left, right = colors(first), colors(second)
    return bool(left and right and left.isdisjoint(right))


def listing_url(category_id: int, offset: int) -> str:
    if category_id in JIB_SEARCH_GROUPS:
        term = quote_plus(JIB_SEARCH_GROUPS[category_id])
        return ("https://www.jib.co.th/web/product/product_search/"
                f"{offset}/?str_search={term}&cate_id%5B0%5D=")
    return ("https://www.jib.co.th/web/product/product_search/"
            f"{offset}/?str_search=&cate_id%5B0%5D={category_id}")


def classify(name: str, category_id: int) -> str | None:
    """Apply the requested exclusions, then assign a precise store category."""
    title = re.sub(r"\s+", " ", name.upper()).strip()
    if not title:
        return None
    if category_id in JIB_SEARCH_GROUPS:
        expected = JIB_FULL_GROUPS[category_id]
        return expected if title.startswith(expected.upper() + " ") else None
    if category_id == 42:
        if re.search(r"\b(?:CD[ -]?ROM|DVD|BLU[ -]?RAY|OPTICAL DRIVE|SOUND CARD|AUDIO CARD)\b|เครื่องอ่านแผ่น|การ์ดเสียง", title):
            return None
        if re.search(r"\b(?:PC|CASE)\s+CARRYING\s+BAG\b", title):
            return "Case Accessories"
        if core.is_pc_set_name(name):
            return "PC Set"
        if re.search(r"\b(?:CPU|AIR)\s+(?:AIR\s+)?COOLER\b", title):
            return "Air Cooler"
        if re.search(r"\b(?:CPU\s+)?(?:LIQUID|WATER)\s+COOLER\b|\bAIO\s+COOLER\b", title):
            return "Liquid Cooler"
        if re.search(r"\b(?:CASE|CHASSIS)\s+FAN\b|พัดลมเคส", title):
            return None
        if re.search(r"\b(?:MAINBOARD|MAINBAORD|MOTHERBOARD)\b", title):
            return "Mainboard"
        if re.search(r"\bLCD\s+PANEL\b", title):
            return "Monitor Accessories"
        if re.search(r"\b(?:VGA|GRAPHIC(?:S)? CARD|GPU)\b", title):
            return "GPU"
        if re.search(r"\b(?:POWER SUPPLY|PSU)\b", title):
            return "PSU"
        if re.search(r"\b(?:HDD|HARD\s*DISK|HARDDISK)\b", title):
            return "HDD"
        if re.search(r"\b(?:SSD|NVME|M\.2)\b", title):
            return "SSD"
        if re.search(r"\b(?:RAM|DDR[345])\b", title):
            return "RAM"
        if re.search(r"\bCPU\b|\bPROCESSOR\b", title):
            return "CPU"
        if re.search(r"\bCASE\b|\bCHASSIS\b", title):
            return "Case"
        return "PC Components"
    if category_id == 58:
        return "Monitor" if re.search(r"\bMONITOR\b|จอมอนิเตอร์", title) else "Monitor Accessories"
    if category_id == 60:
        if re.search(r"\b(?:NAS|FLASH\s*DRIVE|FLASHDRIVE|MEMORY\s*CARD|CARD\s*READER|SD\s*CARD|MICRO\s*SD)\b", title):
            return None
        if re.search(r"\b(?:EXTERNAL|PORTABLE)\b", title):
            return "External Storage"
        if re.search(r"\b(?:HDD|HARD\s*DISK|HARDDISK)\b", title):
            return "HDD"
        if re.search(r"\b(?:SSD|NVME|M\.2)\b", title):
            return "SSD"
        return "Storage Accessories"
    if category_id == 1419:
        if re.search(r"\b(?:WRIST\s*REST|TOP\s*PLATE|MOUSE\s*PAD|MOUSEPAD)\b|ที่รองข้อมือ|แผ่นรองเมาส์", title):
            return None
        if re.match(r"^(?:KEYBOARD\s+)?(?:MECHANICAL\s+)?SWITCH(?:ES)?\b", title):
            return None
        if re.search(r"\b(?:GRAPHIC\s+TABLET|PEN\s+DISPLAY\s+TABLET|MOVINKPAD)\b", title):
            return "Graphic Tablet"
        if re.search(r"\b(?:NUMPAD|NUMERIC\s+KEYPAD|MACROPAD)\b", title):
            return "Keypad"
        if re.search(r"\bMOUSE\b", title):
            return "Mouse"
        if re.match(r"^(?:BLUETOOTH\s+|WIRELESS\s+|GAMING\s+|MECHANICAL\s+)*KEYBOARD\b", title):
            return "Keyboard"
        return "Keyboard Accessories"
    if category_id == 1420:
        if re.search(r"\b(?:TRUE\s*WIRELESS|TWS|KARAOKE|SPEAKER\s*PHONE|SPEAKERPHONE|ADAPTER|CONVERTER|HEAD(?:SET|PHONE)\s*STAND)\b|คาราโอเกะ|หัวแปลง|ขาตั้งหูฟัง", title):
            return None
        return "Headset" if re.search(r"\b(?:HEADSET|HEADPHONE|EARPHONE|EARBUD|IN[ -]?EAR|IEM)\b|หูฟัง", title) else None
    if category_id == 1393:
        if re.search(r"\b(?:CASE|CHASSIS)\s+FAN\b|\bFAN\b.*\bCASE\b|พัดลมเคส", title):
            return None
        if re.search(r"\b(?:CPU\s+)?(?:LIQUID|WATER)\s+COOLER\b|\bAIO\s+COOLER\b|ชุดน้ำปิด", title):
            return "Liquid Cooler"
        if re.search(r"\b(?:CPU\s+)?AIR\s+COOLER\b|\bCPU\s+COOLER\b|ฮีตซิงก์ซีพียู", title):
            return "Air Cooler"
        return "Cooling Accessories"
    raise ValueError(f"Unsupported JIB category: {category_id}")


def parse_card(card, category_id: int) -> dict | None:
    name_element = card.select_one("span.promo_name")
    link_element = card.select_one('a[href*="/readProduct/"]')
    if not name_element or not link_element:
        return None
    name = name_element.get_text(" ", strip=True)
    product_url = urljoin("https://www.jib.co.th", link_element.get("href", ""))
    match = PRODUCT_ID.search(product_url)
    if not match:
        return None
    category = classify(name, category_id)
    if not category:
        return {"source_product_id": int(match.group(1)), "excluded": True}
    price_element = card.select_one("p.price_total")
    price = core.parse_price(price_element.get_text(" ", strip=True) if price_element else "", min_price=1)
    image_element = link_element.select_one("img")
    image = ""
    if image_element:
        raw_image = image_element.get("src") or image_element.get("data-src") or ""
        image = urljoin("https://www.jib.co.th", raw_image) if raw_image else ""
    return {
        "source_product_id": int(match.group(1)), "name": name,
        "price": price, "url": product_url, "img": image,
        "category": category, "excluded": False,
    }


def next_offset(soup, current: int) -> int | None:
    for link in soup.select("a[href]"):
        label = link.get_text(" ", strip=True).lower()
        href = link.get("href", "")
        if not label.startswith("next") or "product_search/" not in href:
            continue
        match = re.search(r"product_search/(\d+)", href)
        if match and int(match.group(1)) > current:
            return int(match.group(1))
    return None


def setup_inventory(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS jib_scrape_inventory (
            source_category_id INTEGER NOT NULL,
            source_product_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            product_name TEXT NOT NULL,
            price INTEGER NOT NULL,
            image_url TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            product_url TEXT NOT NULL,
            db_product_id TEXT NOT NULL DEFAULT '',
            detail_status TEXT NOT NULL DEFAULT 'pending',
            listing_seen_at TEXT NOT NULL,
            detail_checked_at TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (source_category_id, source_product_id)
        );
        CREATE TABLE IF NOT EXISTS jib_scrape_category_audit (
            source_category_id INTEGER PRIMARY KEY,
            listing_pages INTEGER NOT NULL,
            unique_cards INTEGER NOT NULL,
            accepted_products INTEGER NOT NULL,
            excluded_products INTEGER NOT NULL,
            completed_at TEXT NOT NULL
        );
    """)


def reconcile_hdd_category(conn: sqlite3.Connection) -> int:
    """Correct a legacy SSD-bucket row when JIB identifies the same drive as HDD."""
    changed = conn.execute("""
        UPDATE products SET category='HDD', cid='c19'
        WHERE product_id IN (
            SELECT i.db_product_id FROM jib_scrape_inventory AS i
            WHERE i.category='HDD' AND i.db_product_id!=''
        ) AND category='SSD'
          AND (upper(p_name) LIKE '%HDD%' OR upper(p_name) LIKE '%HARD DISK%')
    """).rowcount
    conn.commit()
    return changed


def promote_jib_images(conn: sqlite3.Connection) -> int:
    """Use the detail page's full-size image for products sourced only from JIB."""
    changed = conn.execute("""
        UPDATE products AS p SET img_url=i.image_url
        FROM jib_scrape_inventory AS i
        WHERE p.product_id=i.db_product_id
          AND i.image_url LIKE 'https://www.jib.co.th/img_master/product/original/%'
          AND (p.img_url LIKE '%/medium/%' OR coalesce(p.img_url, '')='')
          AND coalesce(p.price_advice, 0)=0
          AND coalesce(p.price_ihavecpu, 0)=0
    """).rowcount
    conn.commit()
    return changed


def sync_complete_inventory(conn: sqlite3.Connection) -> int:
    """Copy already-hydrated, source-matched inventory facts into products.

    Older runs could mark an inventory row complete before its canonical
    product link was repaired. A later details-only run then skipped the row,
    leaving ``products.desc_jib`` empty despite a complete inventory record.
    """
    changed = conn.execute("""
        UPDATE products AS p SET
            desc_jib=i.description,
            p_description=CASE
                WHEN length(trim(coalesce(p.p_description, ''))) < 30
                THEN i.description ELSE p.p_description END,
            specs=CASE
                WHEN length(trim(coalesce(p.specs, ''))) < 30
                THEN i.description ELSE p.specs END,
            img_url=CASE
                WHEN i.image_url LIKE 'https://www.jib.co.th/img_master/product/original/%'
                  AND (coalesce(p.img_url, '')='' OR p.img_url LIKE '%/medium/%'
                       OR p.img_url LIKE '%placeholder%' OR p.img_url LIKE '%nophoto%')
                THEN i.image_url ELSE p.img_url END,
            updated_at=?
        FROM jib_scrape_inventory AS i
        WHERE p.product_id=i.db_product_id
          AND i.detail_status='complete'
          AND length(trim(coalesce(i.description, '')))>=30
          AND instr(p.url_jib, '/readProduct/' || i.source_product_id || '/')>0
          AND (length(trim(coalesce(p.desc_jib, ''))) < 30
               OR length(trim(coalesce(p.p_description, ''))) < 30
               OR length(trim(coalesce(p.specs, ''))) < 30)
    """, (datetime.now().isoformat(timespec="seconds"),)).rowcount
    conn.commit()
    return changed


def reconcile_lcd_panels(conn: sqlite3.Connection) -> int:
    """Keep case-mounted secondary screens out of the generic PC bucket."""
    changed = conn.execute("""
        UPDATE jib_scrape_inventory
        SET category='Monitor Accessories'
        WHERE source_category_id=42 AND category='PC Components'
          AND upper(product_name) LIKE 'LCD PANEL%'
    """).rowcount
    conn.execute("""
        UPDATE products SET category='Monitor Accessories', cid='c25'
        WHERE product_id IN (
            SELECT db_product_id FROM jib_scrape_inventory
            WHERE source_category_id=42 AND category='Monitor Accessories'
              AND db_product_id!=''
        ) AND category='PC Components'
    """)
    conn.commit()
    return changed


def reconcile_jib_subcategories(conn: sqlite3.Connection) -> int:
    """Apply current category rules to previously checkpointed listing rows."""
    rows = conn.execute("""
        SELECT source_category_id, source_product_id, product_name,
               category, db_product_id
        FROM jib_scrape_inventory
    """).fetchall()
    cursor = conn.cursor()
    changed = 0
    for source_group, source_id, name, old_category, product_id in rows:
        category = classify(name, source_group)
        if not category or category == old_category:
            continue
        cursor.execute("""
            UPDATE jib_scrape_inventory SET category=?
            WHERE source_category_id=? AND source_product_id=?
        """, (category, source_group, source_id))
        if product_id:
            cursor.execute("""
                UPDATE products SET category=?, cid=?
                WHERE product_id=? AND category=?
            """, (category, core.get_cid(category), product_id, old_category))
        changed += 1
    conn.commit()
    return changed


def clear_unpriced_jib_prices(conn: sqlite3.Connection) -> int:
    """Do not keep an old JIB price when its current listing says N/A."""
    rows = conn.execute("""
        SELECT DISTINCT p.product_id
        FROM jib_scrape_inventory AS i
        JOIN products AS p ON p.product_id=i.db_product_id
        WHERE i.price=0 AND p.price_jib>0
          AND instr(p.url_jib, '/readProduct/' || i.source_product_id || '/')>0
    """).fetchall()
    cursor = conn.cursor()
    for (product_id,) in rows:
        cursor.execute("UPDATE products SET price_jib=0 WHERE product_id=?", (product_id,))
        core._refresh_lowest_price(cursor, product_id)
    conn.commit()
    return len(rows)


def add_unpriced_jib_products(conn: sqlite3.Connection) -> int:
    """Expose JIB N/A listings in the catalogue without inventing a price."""
    rows = conn.execute("""
        SELECT source_category_id, source_product_id, category,
               product_name, image_url, description, product_url
        FROM jib_scrape_inventory
        WHERE price=0 AND db_product_id=''
          AND description!='' AND image_url!='' AND product_url!=''
    """).fetchall()
    cursor = conn.cursor()
    added = 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for group_id, source_id, category, name, image, description, url in rows:
        product_id = f"jib_{source_id}"
        cursor.execute("""
            INSERT OR IGNORE INTO products
                (product_id, p_name, p_description, p_price,
                 price_advice, price_jib, price_ihavecpu,
                 url_advice, url_jib, url_ihavecpu,
                 desc_advice, desc_jib, desc_ihavecpu,
                 p_stock, cid, category, img_url, specs,
                 created_at, updated_at)
            VALUES (?, ?, ?, 0, 0, 0, 0, '', ?, '', '', ?, '',
                    0, ?, ?, ?, ?, ?, ?)
        """, (product_id, name, description, url, description,
              core.get_cid(category), category, image, description, now, now))
        if not cursor.rowcount:
            # A colliding product ID must never be claimed without verifying
            # that its JIB URL contains the same retailer product ID.
            existing = cursor.execute(
                "SELECT url_jib FROM products WHERE product_id=?", (product_id,),
            ).fetchone()
            if not existing or f"/readProduct/{source_id}/" not in (existing[0] or ""):
                core.log(f"  [JIB full] unpriced ID collision {source_id}; left pending")
                continue
        else:
            added += 1
        cursor.execute("""
            UPDATE jib_scrape_inventory SET db_product_id=?
            WHERE source_category_id=? AND source_product_id=?
        """, (product_id, group_id, source_id))
    conn.commit()
    return added


def repair_conflicting_source_matches(conn: sqlite3.Connection,
                                      matcher: core.SmartMatcher) -> int:
    """Separate a JIB source ID from a clearly different cross-store model.

    Older fuzzy merges sometimes attached one JIB URL to a different Advice or
    iHaveCPU product.  Preserve that other store's row and create a JIB-owned
    row for the authoritative product ID instead of merging their specs.
    """
    rows = conn.execute("""
        SELECT i.source_category_id, i.source_product_id, i.category,
               i.product_name, i.price, i.image_url, i.description,
               i.product_url, i.db_product_id, p.p_name,
               p.price_advice, p.price_ihavecpu, p.url_jib
        FROM jib_scrape_inventory AS i
        JOIN products AS p ON p.product_id=i.db_product_id
        WHERE i.price>0 AND (p.price_advice>0 OR p.price_ihavecpu>0)
    """).fetchall()
    fixed = 0
    seen_source_ids: set[int] = set()
    cursor = conn.cursor()
    for (group_id, source_id, category, name, price, image, description,
         url, old_pid, old_name, _advice_price, _ihc_price, old_url) in rows:
        if source_id in seen_source_ids:
            continue
        seen_source_ids.add(source_id)
        if f"/readProduct/{source_id}/" not in (old_url or ""):
            continue
        color_conflict = explicit_color_conflict(name, old_name)
        if (core.is_same_product(name, category, old_name, category)
                and not color_conflict):
            continue
        # These types may have abbreviated retailer titles even when the
        # same exact model is present; do not detach on a fuzzy-score failure.
        if (category in {"CPU", "Mouse"} and not color_conflict
                and not core.has_identity_conflict(name, old_name, category)):
            continue
        linked = cursor.execute("""
            SELECT product_id, p_name FROM products WHERE url_jib LIKE ?
        """, (f"%/readProduct/{source_id}/%",)).fetchall()
        preferred = next(
            (pid for pid, linked_name in linked
             if linked_name.strip().upper() == name.strip().upper()),
            None,
        )
        for linked_pid, _linked_name in linked:
            if linked_pid == preferred:
                continue
            cursor.execute("""
                UPDATE products SET
                    p_description=CASE WHEN p_description=desc_jib THEN
                        COALESCE(NULLIF(desc_advice,''), NULLIF(desc_ihavecpu,''), '')
                        ELSE p_description END,
                    specs=CASE WHEN specs=desc_jib THEN
                        COALESCE(NULLIF(desc_advice,''), NULLIF(desc_ihavecpu,''), '')
                        ELSE specs END,
                    price_jib=0, url_jib='', desc_jib=''
                WHERE product_id=?
            """, (linked_pid,))
            core._refresh_lowest_price(cursor, linked_pid)
        core.upsert_product(cursor, matcher, {
            "name": name, "price": price, "img_url": image,
            "url": url, "category": category, "store": "jib",
            "description": description, "full_catalog": True,
        })
        canonical = cursor.execute(
            "SELECT product_id FROM products WHERE url_jib LIKE ? LIMIT 1",
            (f"%/readProduct/{source_id}/%",),
        ).fetchone()
        if not canonical:
            raise RuntimeError(f"Could not relink JIB product {source_id}")
        cursor.execute("""
            UPDATE jib_scrape_inventory SET db_product_id=?
            WHERE source_product_id=?
        """, (canonical[0], source_id))
        fixed += 1
    conn.commit()
    return fixed


def repair_duplicate_jib_links(conn: sqlite3.Connection) -> int:
    """Keep one verified product row per JIB product ID, preserving other stores.

    Legacy scrapes sometimes reused a JIB URL for several unrelated products.
    The scraped inventory is authoritative for the source ID, title and specs;
    never choose a linked row solely because it happens to be first in SQLite.
    """
    inventory = conn.execute("""
        SELECT source_product_id, category, product_name, price,
               product_url, description, db_product_id
        FROM jib_scrape_inventory WHERE price>0
    """).fetchall()
    linked_by_id: dict[int, list[tuple]] = defaultdict(list)
    for row in conn.execute("""
        SELECT product_id, p_name, category, price_advice,
               price_ihavecpu, url_jib
        FROM products WHERE url_jib LIKE '%/readProduct/%'
    """):
        match = re.search(r"/readProduct/(\d+)/", row[5] or "")
        if match:
            linked_by_id[int(match.group(1))].append(row[:5])
    cursor = conn.cursor()
    detached = 0
    seen_ids: set[int] = set()
    for source_id, category, name, price, url, description, inventory_pid in inventory:
        if source_id in seen_ids:
            continue
        seen_ids.add(source_id)
        linked = linked_by_id.get(source_id, [])
        if len(linked) < 2:
            continue

        def match_score(row: tuple) -> tuple[int, int, int]:
            pid, linked_name, linked_category, advice_price, ihc_price = row
            if explicit_color_conflict(name, linked_name):
                return (-1, 0, 0)
            exact = linked_name.strip().upper() == name.strip().upper()
            compatible = exact or core.is_same_product(
                name, category, linked_name, linked_category,
            )
            if not compatible:
                return (-1, 0, 0)
            return (2 if exact else 1,
                    int(bool(advice_price or ihc_price)),
                    int(pid == inventory_pid))

        canonical = max(linked, key=match_score)
        if match_score(canonical)[0] < 0:
            core.log(f"  [JIB full] could not safely resolve duplicate ID {source_id}")
            continue
        canonical_pid = canonical[0]
        for pid, _linked_name, _cat, _advice, _ihc in linked:
            if pid == canonical_pid:
                continue
            cursor.execute("""
                UPDATE products SET
                    p_description=CASE WHEN p_description=desc_jib THEN
                        COALESCE(NULLIF(desc_advice,''), NULLIF(desc_ihavecpu,''), '')
                        ELSE p_description END,
                    specs=CASE WHEN specs=desc_jib THEN
                        COALESCE(NULLIF(desc_advice,''), NULLIF(desc_ihavecpu,''), '')
                        ELSE specs END,
                    price_jib=0, url_jib='', desc_jib=''
                WHERE product_id=?
            """, (pid,))
            core._refresh_lowest_price(cursor, pid)
            detached += 1
        cursor.execute("""
            UPDATE products SET price_jib=?, url_jib=?,
                desc_jib=CASE WHEN ?!='' THEN ? ELSE desc_jib END,
                p_description=CASE WHEN COALESCE(price_advice,0)=0
                    AND COALESCE(price_ihavecpu,0)=0 THEN ? ELSE p_description END,
                specs=CASE WHEN COALESCE(price_advice,0)=0
                    AND COALESCE(price_ihavecpu,0)=0 THEN ? ELSE specs END
            WHERE product_id=?
        """, (price, url, description, description, description,
              description, canonical_pid))
        core._refresh_lowest_price(cursor, canonical_pid)
        cursor.execute("""
            UPDATE jib_scrape_inventory SET db_product_id=?
            WHERE source_product_id=?
        """, (canonical_pid, source_id))
    conn.commit()
    return detached


def reconcile_current_inventory_links(conn: sqlite3.Connection, since: str) -> int:
    """Give each freshly listed JIB ID one catalogue row with its own source URL.

    A legacy product_id can already belong to a different JIB source ID even
    when the title is identical (colour/stock variants). Never overwrite that
    row: use a separate, stable source-owned ID instead.
    """
    rows = conn.execute("""
        SELECT i.source_product_id, i.category, i.product_name, i.price,
               i.image_url, i.description, i.product_url, i.db_product_id
        FROM jib_scrape_inventory AS i
        LEFT JOIN products AS p ON p.product_id=i.db_product_id
        WHERE i.listing_seen_at>=?
          AND (p.product_id IS NULL OR instr(COALESCE(p.url_jib,''),
              '/readProduct/' || i.source_product_id || '/')=0)
        ORDER BY i.source_product_id
    """, (since,)).fetchall()
    cursor = conn.cursor()
    fixed = 0
    for source_id, category, name, price, image, description, url, old_pid in rows:
        marker = f"/readProduct/{source_id}/"
        if marker not in url:
            raise RuntimeError(f"JIB inventory URL does not match source ID {source_id}")
        linked = cursor.execute("""
            SELECT product_id, p_name FROM products WHERE url_jib LIKE ?
        """, (f"%{marker}%",)).fetchall()
        canonical = next((pid for pid, linked_name in linked
                          if linked_name.strip().upper() == name.strip().upper()), None)
        if canonical is None and linked:
            canonical = linked[0][0]
        if canonical is None and old_pid:
            candidate = cursor.execute("""
                SELECT p_name, url_jib FROM products WHERE product_id=?
            """, (old_pid,)).fetchone()
            if (candidate and not (candidate[1] or "").strip()
                    and candidate[0].strip().upper() == name.strip().upper()):
                canonical = old_pid
        if canonical is None:
            # Prefer the short ID only if it is vacant or explicitly unclaimed.
            for proposed in (f"jib_{source_id}", f"jib_source_{source_id}"):
                candidate = cursor.execute(
                    "SELECT p_name, url_jib FROM products WHERE product_id=?",
                    (proposed,),
                ).fetchone()
                if candidate is None:
                    canonical = proposed
                    break
                if (not (candidate[1] or "").strip()
                        and candidate[0].strip().upper() == name.strip().upper()):
                    canonical = proposed
                    break
        if canonical is None:
            raise RuntimeError(f"No safe catalogue ID for JIB product {source_id}")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT OR IGNORE INTO products
                (product_id, p_name, p_description, p_price,
                 price_advice, price_jib, price_ihavecpu,
                 url_advice, url_jib, url_ihavecpu,
                 desc_advice, desc_jib, desc_ihavecpu,
                 p_stock, cid, category, img_url, specs,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, 0, ?, 0, '', ?, '', '', ?, '',
                    99, ?, ?, ?, ?, ?, ?)
        """, (canonical, name, description, price, price, url,
              description, core.get_cid(category), category, image,
              description, now, now))
        cursor.execute("""
            UPDATE products SET price_jib=?, url_jib=?,
                desc_jib=CASE WHEN ?!='' THEN ? ELSE desc_jib END,
                img_url=CASE WHEN COALESCE(img_url,'')='' THEN ? ELSE img_url END,
                p_description=CASE WHEN COALESCE(p_description,'')='' THEN ?
                    ELSE p_description END, updated_at=?
            WHERE product_id=? AND (COALESCE(url_jib,'')='' OR url_jib LIKE ?)
        """, (price, url, description, description, image, description, now,
              canonical, f"%{marker}%"))
        if not cursor.rowcount:
            raise RuntimeError(f"JIB product {source_id} has a conflicting source URL")
        core._refresh_lowest_price(cursor, canonical)
        cursor.execute("""
            UPDATE jib_scrape_inventory SET db_product_id=?
            WHERE source_product_id=? AND listing_seen_at>=?
        """, (canonical, source_id, since))
        if old_pid != canonical:
            fixed += 1
    conn.commit()
    return fixed


async def fetch_listing(client, limiter, category_id: int, offset: int):
    url = listing_url(category_id, offset)
    for attempt in range(6):
        # JIB occasionally returns a full-size HTTP 200 shell without cards.
        # The alternate, equivalent query spelling avoids a stale empty cache.
        request_url = (url if attempt % 2 == 0 else
                       url.replace("cate_id%5B0%5D", "cate_id%5B%5D"))
        response = await core.request_with_retry(
            client, "GET", request_url, rate_limiter=limiter,
        )
        if response.status_code in (403, 429):
            raise PermissionError(f"JIB listing blocked: HTTP {response.status_code} {url}")
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        cards = soup.select("div.divboxpro")
        if cards:
            return soup, cards
        if attempt < 5:
            core.log(f"    [JIB empty page] {url}; retrying after pause")
            await asyncio.sleep(min(5 * (attempt + 1), 20))
    raise RuntimeError(f"JIB returned no product cards after retries: {url}")


async def crawl_listings(conn, matcher, client, limiter, category_ids: list[int]) -> None:
    cursor = conn.cursor()
    for category_id in category_ids:
        offset, pages = 0, 0
        seen: set[int] = set()
        accepted = excluded = 0
        while pages < 100:
            soup, cards = await fetch_listing(client, limiter, category_id, offset)
            parsed = [parse_card(card, category_id) for card in cards]
            if all(item is None or item["source_product_id"] in seen for item in parsed):
                raise RuntimeError(f"JIB repeated page {category_id} offset {offset}")
            for item in parsed:
                if not item or item["source_product_id"] in seen:
                    continue
                seen.add(item["source_product_id"])
                if item["excluded"]:
                    excluded += 1
                    continue
                accepted += 1
                previous = cursor.execute("""
                    SELECT category, product_name, price, image_url, product_url,
                           db_product_id FROM jib_scrape_inventory
                    WHERE source_category_id=? AND source_product_id=?
                """, (category_id, item["source_product_id"])).fetchone()
                unchanged = previous and previous[:5] == (
                    item["category"], item["name"], item["price"],
                    item["img"], item["url"],
                ) and previous[5]
                if not unchanged and item["price"]:
                    core.upsert_product(cursor, matcher, {
                        "name": item["name"], "price": item["price"],
                        "img_url": item["img"], "url": item["url"],
                        "category": item["category"], "store": "jib",
                        "description": "", "full_catalog": True,
                    })
                stored = (previous[5],) if unchanged else cursor.execute(
                    "SELECT product_id FROM products WHERE url_jib LIKE ? LIMIT 1",
                    (f"%/readProduct/{item['source_product_id']}/%",),
                ).fetchone()
                cursor.execute("""
                    INSERT INTO jib_scrape_inventory
                        (source_category_id, source_product_id, category, product_name,
                         price, image_url, product_url, db_product_id, listing_seen_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_category_id, source_product_id) DO UPDATE SET
                        category=excluded.category, product_name=excluded.product_name,
                        price=excluded.price, image_url=excluded.image_url,
                        product_url=excluded.product_url, db_product_id=excluded.db_product_id,
                        listing_seen_at=excluded.listing_seen_at
                """, (category_id, item["source_product_id"], item["category"],
                      item["name"], item["price"], item["img"], item["url"],
                      stored[0] if stored else "", datetime.now().isoformat(timespec="seconds")))
            conn.commit()
            pages += 1
            following = next_offset(soup, offset)
            core.log(f"  [JIB full] category={category_id} offset={offset} cards={len(cards)} "
                     f"unique={len(seen)} accepted={accepted} excluded={excluded} next={following}")
            if following is None:
                break
            offset = following
            await asyncio.sleep(random.uniform(1.0, 2.0))
        else:
            raise RuntimeError(f"JIB category {category_id} exceeded 100 pages")
        cursor.execute("""
            INSERT INTO jib_scrape_category_audit VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_category_id) DO UPDATE SET
                listing_pages=excluded.listing_pages, unique_cards=excluded.unique_cards,
                accepted_products=excluded.accepted_products,
                excluded_products=excluded.excluded_products,
                completed_at=excluded.completed_at
        """, (category_id, pages, len(seen), accepted, excluded,
              datetime.now().isoformat(timespec="seconds")))
        conn.commit()


async def hydrate_details(conn, matcher, client, limiter, category_ids: list[int],
                          concurrency: int = 2) -> None:
    placeholders = ",".join("?" for _ in category_ids)
    reusable = conn.execute(f"""
        UPDATE jib_scrape_inventory AS i
        SET description=p.desc_jib, detail_status='complete',
            detail_checked_at=?
        FROM products AS p
        WHERE i.db_product_id=p.product_id
          AND i.source_category_id IN ({placeholders})
          AND i.detail_status!='complete'
          AND length(trim(coalesce(p.desc_jib, '')))>=30
          AND instr(p.url_jib, '/readProduct/' || i.source_product_id || '/')>0
    """, (datetime.now().isoformat(timespec="seconds"), *category_ids)).rowcount
    conn.commit()
    core.log(f"  [JIB full] reused {reusable} existing source-matched JIB descriptions")
    rows = conn.execute(f"""
        SELECT source_category_id, source_product_id, category, product_name,
               price, image_url, product_url
        FROM jib_scrape_inventory
        WHERE source_category_id IN ({placeholders}) AND detail_status != 'complete'
        ORDER BY source_category_id, source_product_id
    """, category_ids).fetchall()
    unique = {row[6]: row for row in rows}
    core.log(f"  [JIB full] details pending={len(rows)} unique_urls={len(unique)}")
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def fetch_one(row):
        async with semaphore:
            url = row[6]
            cached = core._read_detail_checkpoint(conn, "jib", url)
            if cached is not None:
                return url, cached
            desc, img = await core.fetch_jib_detail_http(
                client, url, row[3], row[2], rate_limiter=limiter,
                strict_block=True,
            )
            core._write_detail_checkpoint(conn, "jib", {
                "url": url, "category": row[2], "name": row[3],
            }, desc, img)
            return url, (desc, img)

    completed = missing = 0
    work = list(unique.values())
    for start in range(0, len(work), 20):
        batch = work[start:start + 20]
        tasks = [asyncio.create_task(fetch_one(row)) for row in batch]
        try:
            results = dict(await asyncio.gather(*tasks))
        except BaseException:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        for url, (description, detail_image) in results.items():
            rows_for_url = conn.execute("""
                SELECT source_category_id, source_product_id, category,
                       product_name, price, image_url
                FROM jib_scrape_inventory WHERE product_url=?
            """, (url,)).fetchall()
            for row in rows_for_url:
                image = detail_image or row[5]
                status = "complete" if len(description.strip()) >= 30 else "missing"
                if row[4]:
                    core.upsert_product(conn.cursor(), matcher, {
                        "name": row[3], "price": row[4], "img_url": image,
                        "url": url, "category": row[2], "store": "jib",
                        "description": description, "full_catalog": True,
                    })
                product = conn.execute(
                    "SELECT product_id FROM products WHERE url_jib LIKE ? LIMIT 1",
                    (f"%/readProduct/{row[1]}/%",),
                ).fetchone()
                conn.execute("""
                    UPDATE jib_scrape_inventory SET image_url=?, description=?,
                        detail_status=?, db_product_id=?, detail_checked_at=?
                    WHERE source_category_id=? AND source_product_id=?
                """, (image, description, status, product[0] if product else "",
                      datetime.now().isoformat(timespec="seconds"), row[0], row[1]))
                if status == "complete":
                    completed += 1
                else:
                    missing += 1
        conn.commit()
        core.log(f"  [JIB full] details {min(start + 20, len(work))}/{len(work)} "
                 f"complete={completed} missing={missing} 429={limiter.total_429}")


async def run(category_ids: list[int], *, list_only: bool = False,
              details_only: bool = False, concurrency: int = 2,
              interval: float = 1.2) -> None:
    conn = sqlite3.connect(core.DB_PATH)
    try:
        crawl_started_at = datetime.now().isoformat(timespec="seconds")
        core.setup_db(conn)
        setup_inventory(conn)
        matcher = core.SmartMatcher(conn.cursor())
        limiter = core.AdaptiveRateLimiter(
            "jib", threshold=2, base_cooldown_seconds=30,
            max_cooldown_seconds=180, min_interval_seconds=interval,
        )
        async with httpx.AsyncClient(
            headers={"User-Agent": core.UA, "Accept": "text/html,application/xhtml+xml",
                     "Accept-Language": "th-TH,th;q=0.9,en;q=0.8"},
            follow_redirects=True, timeout=httpx.Timeout(35.0, connect=15.0),
            limits=httpx.Limits(max_connections=max(2, concurrency + 1)),
        ) as client:
            if not details_only:
                await crawl_listings(conn, matcher, client, limiter, category_ids)
            if not list_only:
                await hydrate_details(conn, matcher, client, limiter, category_ids, concurrency)
        fixed = reconcile_hdd_category(conn)
        if fixed:
            core.log(f"  [JIB full] corrected {fixed} legacy HDD category rows")
        panels = reconcile_lcd_panels(conn)
        if panels:
            core.log(f"  [JIB full] separated {panels} LCD panels as monitor accessories")
        recategorized = reconcile_jib_subcategories(conn)
        if recategorized:
            core.log(f"  [JIB full] refined {recategorized} product subcategories")
        conflicts = repair_conflicting_source_matches(conn, matcher)
        if conflicts:
            core.log(f"  [JIB full] repaired {conflicts} conflicting cross-store source links")
        duplicates = repair_duplicate_jib_links(conn)
        if duplicates:
            core.log(f"  [JIB full] detached {duplicates} duplicate JIB source links")
        unpriced = clear_unpriced_jib_prices(conn)
        if unpriced:
            core.log(f"  [JIB full] cleared {unpriced} stale JIB prices marked N/A")
        n_a_products = add_unpriced_jib_products(conn)
        if n_a_products:
            core.log(f"  [JIB full] catalogued {n_a_products} JIB items with N/A price")
        if not details_only:
            relinked = reconcile_current_inventory_links(conn, crawl_started_at)
            if relinked:
                core.log(f"  [JIB full] relinked {relinked} current source IDs")
        promoted = promote_jib_images(conn)
        if promoted:
            core.log(f"  [JIB full] promoted {promoted} product images to full size")
        synced = sync_complete_inventory(conn)
        if synced:
            core.log(f"  [JIB full] synced {synced} completed inventory details")
        core.log(f"  [JIB full] finished categories={category_ids} 429={limiter.total_429}")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--categories", type=int, nargs="+", choices=JIB_FULL_GROUPS,
                        default=list(JIB_FULL_GROUPS))
    parser.add_argument("--db-path", default="",
                        help="Existing SQLite catalogue to update (required when it is outside backend/)")
    parser.add_argument("--list-only", action="store_true")
    parser.add_argument("--details-only", action="store_true")
    parser.add_argument("--skip-compat-training", action="store_true")
    parser.add_argument("--repair-links-since", default="",
                        help="Repair inventory links listed since ISO timestamp, without network")
    parser.add_argument("--concurrency", type=int, default=2, choices=range(1, 5))
    parser.add_argument("--interval", type=float, default=1.2,
                        help="Minimum seconds between JIB requests (default: 1.2)")
    args = parser.parse_args()
    if args.db_path:
        db_path = os.path.abspath(args.db_path)
        if not os.path.isfile(db_path):
            parser.error(f"Catalogue database does not exist: {db_path}")
        core.DB_PATH = db_path
    if args.repair_links_since:
        conn = sqlite3.connect(core.DB_PATH)
        try:
            core.setup_db(conn)
            setup_inventory(conn)
            count = reconcile_current_inventory_links(conn, args.repair_links_since)
            core.log(f"  [JIB full] relinked {count} current source IDs")
        finally:
            conn.close()
        return
    if args.list_only and args.details_only:
        parser.error("--list-only and --details-only are mutually exclusive")
    if args.interval < 0.8:
        parser.error("--interval must be at least 0.8 seconds")
    asyncio.run(run(list(dict.fromkeys(args.categories)), list_only=args.list_only,
                    details_only=args.details_only, concurrency=args.concurrency,
                    interval=args.interval))
    if not args.list_only and not args.skip_compat_training:
        trainer = os.path.join(os.path.dirname(__file__), "train_compat_knowledge.py")
        result = subprocess.run([sys.executable, "-X", "utf8", trainer, "--apply"],
                                check=False)
        if result.returncode:
            core.log("  [JIB full] compatibility normalization failed; raw specs remain saved")


if __name__ == "__main__":
    main()
