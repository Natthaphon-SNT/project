"""Resumable full Advice crawl for the user-selected public categories.

Advice's own category pages use the guest product/get API. This scraper uses
the same paginated endpoint, a single paced request stream, and durable SQLite
checkpoints. It stops on access blocks instead of bypassing them.
"""

import argparse
import asyncio
from datetime import datetime
import json
import os
import re
import sqlite3
import subprocess
import sys
from urllib.parse import urlparse
from uuid import uuid4

from bs4 import BeautifulSoup
import httpx

import full_scraper as core


GUEST_API = "https://prodbackadvice.advice.in.th/api/v1.0.0/user/guest"
CATALOG_API = "https://prodbackadvice.advice.in.th/api/v1.0.0/product/get"
PAGE_SIZE = 12  # The storefront's own page size.
CATEGORIES = {
    "cpu": "CPU",
    "mainboard": "Mainboard",
    "graphic-card-vga-": "GPU",
    "ram-for-pc": "RAM",
    "case": "Case",
    "power-supply": "PSU",
    "cooling-system": "Cooling Accessories",
    "monitor": "Monitor",
    "dual-mode-monitor": "Dual Mode Monitor",
    "portable-monitor": "Portable Monitor",
    "curved-monitor": "Curved Monitor",
    "gaming-chairs": "Gaming Chair",
    "gaming-desk": "Gaming Desk",
    "headset": "Headset",
    "gaming-microphone": "Microphone",
    "gaming-headset": "Gaming Headset",
    "gaming-headset-wireless": "Wireless Headset",
}
CATEGORY_PRIORITY = {
    "monitor": 0, "headset": 0,
    "dual-mode-monitor": 2, "portable-monitor": 2,
    "curved-monitor": 2, "gaming-headset": 2,
    "gaming-headset-wireless": 3,
}


def classify(name: str, slug: str, source_url: str = "") -> str:
    upper = re.sub(r"\s+", " ", name.upper())
    source_path = urlparse(source_url).path.lower()
    if slug == "graphic-card-vga-" and "/vga-holder/" in source_path:
        return "GPU Accessories"
    if slug == "gaming-headset" and "/in-ear-headphone/" in source_path:
        return "In-Ear Headphone"
    if slug == "gaming-headset-wireless" and "/gaming-true-wireless/" in source_path:
        return "True Wireless Earbuds"
    if slug == "cooling-system":
        for token, category in (
            ("/liquid-cooling/", "Liquid Cooler"),
            ("/cpu-cooler/", "Air Cooler"),
            ("/fan-case/", "Case Fan"),
            ("/silicone-cpu/", "Cooling Accessories"),
        ):
            if token in source_path:
                return category
        if upper.startswith(("CASE FAN", "FAN CASE", "CHASSIS FAN")):
            return "Case Fan"
        if (upper.startswith(("LIQUID COOLING", "WATER COOLING")) or
                re.search(r"\b(?:CPU\s+)?(?:LIQUID|WATER|AIO)\s+COOLER\b|\bWATER\s*BLOCK\b", upper)):
            return "Liquid Cooler"
        if (upper.startswith(("CPU COOLER", "AIR COOLER")) or
                re.search(r"\b(?:AIR|CPU)\s*COOLER\b|\bHEATSINK\b", upper)):
            return "Air Cooler"
        return "Cooling Accessories"
    if slug == "case":
        if upper.startswith("LCD PANEL CORSAIR XENEON EDGE"):
            return "Portable Monitor"
        if "/accessories-case/" in source_path:
            return "Case Accessories"
        if re.search(r"\b(?:CASE\s*FAN|FAN\s*CASE)\b", upper):
            return "Case Fan"
    if slug in {"monitor", "dual-mode-monitor", "portable-monitor", "curved-monitor"}:
        if re.search(r"\b(?:MONITOR\s*ARM|MONITOR\s*STAND|WALL\s*MOUNT)\b", upper):
            return "Monitor Accessories"
        return CATEGORIES[slug]
    if slug in {"headset", "gaming-headset", "gaming-headset-wireless"}:
        return CATEGORIES[slug]
    return CATEGORIES[slug]


def category_priority(slug: str) -> int:
    return CATEGORY_PRIORITY.get(slug, 1)


def clean_html(value: object) -> str:
    if not value:
        return ""
    if not isinstance(value, str):
        value = str(value)
    return re.sub(r"\s+", " ", BeautifulSoup(value, "html.parser").get_text(" ", strip=True)).strip()


def flatten_detail(product: dict, listing_spec: str) -> tuple[str, str, list[str]]:
    lines: list[str] = []
    seen: set[str] = set()

    def add(value: str) -> None:
        value = value.strip()
        if value and value.casefold() not in seen:
            lines.append(value)
            seen.add(value.casefold())

    add(clean_html(listing_spec))
    for group in product.get("spec_detail") or []:
        if not isinstance(group, dict):
            continue
        title = clean_html(group.get("title"))
        if title:
            add(title)
        for row in group.get("data") or []:
            if not isinstance(row, dict):
                continue
            key, value = clean_html(row.get("title")), clean_html(row.get("value"))
            if key and value and value.upper() not in {"N/A", "NONE", "-"}:
                add(f"{key}: {value}")
    detail = product.get("detail") or {}
    if isinstance(detail, dict):
        for key in ("feature", "product_detail", "short_spec_ai", "text_note"):
            value = clean_html(detail.get(key))
            if value:
                add(value)
    warranty = clean_html(product.get("warranty"))
    if warranty:
        add(f"Warranty: {warranty}")

    images: list[str] = []
    for picture in product.get("picture") or []:
        url = picture.get("pic_url", "") if isinstance(picture, dict) else ""
        if url.startswith("https://") and url not in images:
            images.append(url)
    primary = images[0] if images else product.get("pic_url") or ""
    if product.get("pic_url") and product["pic_url"] not in images:
        images.append(product["pic_url"])
    return "\n".join(lines), primary, images


def setup_inventory(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS advice_scrape_inventory (
            source_code TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            listing_slug TEXT NOT NULL,
            product_name TEXT NOT NULL,
            price INTEGER NOT NULL,
            image_url TEXT NOT NULL,
            images_json TEXT NOT NULL DEFAULT '[]',
            description TEXT NOT NULL DEFAULT '',
            spec_json TEXT NOT NULL DEFAULT '[]',
            product_url TEXT NOT NULL,
            db_product_id TEXT NOT NULL DEFAULT '',
            detail_status TEXT NOT NULL DEFAULT 'pending',
            listing_seen_at TEXT NOT NULL,
            detail_checked_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS advice_scrape_membership (
            category_slug TEXT NOT NULL,
            source_code TEXT NOT NULL,
            PRIMARY KEY (category_slug, source_code)
        );
        CREATE TABLE IF NOT EXISTS advice_scrape_category_audit (
            category_slug TEXT PRIMARY KEY,
            next_skip INTEGER NOT NULL DEFAULT 0,
            listing_pages INTEGER NOT NULL DEFAULT 0,
            accepted_products INTEGER NOT NULL DEFAULT 0,
            is_complete INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        );
    """)


def reclassify_inventory(conn: sqlite3.Connection) -> int:
    changed = 0
    for code, slug, name, category, url in conn.execute("""
        SELECT source_code, listing_slug, product_name, category, product_url
        FROM advice_scrape_inventory
    """).fetchall():
        expected = classify(name, slug, url)
        if expected != category:
            conn.execute("""
                UPDATE advice_scrape_inventory SET category=? WHERE source_code=?
            """, (expected, code))
            changed += 1
    if changed:
        conn.commit()
    return changed


def inventory_audit(conn: sqlite3.Connection, slugs: list[str]) -> dict:
    placeholders = ",".join("?" for _ in slugs)
    categories = conn.execute(f"""
        SELECT category_slug, accepted_products, is_complete
        FROM advice_scrape_category_audit
        WHERE category_slug IN ({placeholders})
    """, slugs).fetchall()
    rows = conn.execute(f"""
        SELECT DISTINCT i.source_code, i.detail_status, i.description,
               i.image_url, i.product_url, i.db_product_id
        FROM advice_scrape_inventory AS i
        JOIN advice_scrape_membership AS m ON m.source_code=i.source_code
        WHERE m.category_slug IN ({placeholders})
    """, slugs).fetchall()
    return {
        "requested_categories": len(slugs),
        "completed_categories": sum(bool(row[2]) for row in categories),
        "category_counts": {row[0]: row[1] for row in categories},
        "unique_products": len(rows),
        "complete_details": sum(row[1] == "complete" and bool(row[2]) and
                                bool(row[3]) and bool(row[4]) and bool(row[5])
                                for row in rows),
        "missing_details": sum(row[1] == "missing" for row in rows),
    }


def catalog_payload(slug: str, device_id: str, *, skip: int = 0,
                    product_url: str = "") -> dict:
    category_sub = product = ""
    if product_url:
        parts = urlparse(product_url).path.split("/product/", 1)[-1].strip("/").split("/")
        if len(parts) < 2:
            raise ValueError(f"Invalid Advice product URL: {product_url}")
        slug = parts[0]
        if len(parts) > 2:
            category_sub = parts[1]
        product = parts[-1]
    return {
        "category": slug, "category_sub": category_sub, "product": product,
        "keyword": "", "take": PAGE_SIZE, "device_id": device_id,
        "skip": skip, "refSearch": "", "page": "product",
        "arr_filter_brand": [], "arr_filter_ict": [],
        "arr_filter_price_ict": [], "arr_filter_cate": [],
        "addView": bool(product_url), "group_end": not bool(product_url),
    }


async def guest_token(client: httpx.AsyncClient,
                      limiter: core.AdaptiveRateLimiter) -> str:
    response = await core.request_with_retry(
        client, "POST", GUEST_API, json={"type": "online"},
        rate_limiter=limiter, attempts=2,
    )
    if response.status_code in (403, 429):
        raise PermissionError(f"Advice guest access blocked: HTTP {response.status_code}")
    response.raise_for_status()
    token = ((response.json().get("data") or {}).get("token") or "").strip()
    if not token:
        raise RuntimeError("Advice did not return a public guest token")
    return token


async def fetch_catalog(client: httpx.AsyncClient, limiter: core.AdaptiveRateLimiter,
                        token: str, payload: dict) -> dict:
    response = await core.request_with_retry(
        client, "POST", CATALOG_API, json=payload,
        headers={"Authorization": f"Bearer {token}"},
        rate_limiter=limiter, attempts=2,
    )
    if response.status_code in (401, 403, 429):
        raise PermissionError(f"Advice catalogue access blocked: HTTP {response.status_code}")
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "SUCCESS" or not isinstance(data.get("data"), dict):
        raise RuntimeError(f"Advice catalogue returned status {data.get('status')}")
    return data["data"]


def product_cards(data: dict) -> list[dict]:
    groups = data.get("product") or {}
    if isinstance(groups, dict):
        groups = groups.values()
    products = []
    for group in groups:
        if isinstance(group, dict):
            products.extend(item for item in group.get("product") or []
                            if isinstance(item, dict))
    return products


def product_url(raw: str) -> str:
    if raw.startswith("https://www.advice.co.th/product/"):
        return raw
    return "https://www.advice.co.th/product/" + raw.lstrip("/")


async def crawl_listings(conn: sqlite3.Connection, client: httpx.AsyncClient,
                         limiter: core.AdaptiveRateLimiter, token: str,
                         device_id: str, slugs: list[str], refresh: bool) -> None:
    cursor = conn.cursor()
    for slug in slugs:
        progress = cursor.execute("""
            SELECT next_skip, listing_pages, is_complete
            FROM advice_scrape_category_audit WHERE category_slug=?
        """, (slug,)).fetchone()
        if progress and progress[2] and not refresh:
            core.log(f"  [Advice full] {slug}: listing checkpoint complete")
            continue
        skip = 0 if refresh or not progress else progress[0]
        pages = 0 if refresh or not progress else progress[1]
        seen_page_codes: set[str] = set()
        while pages < 200:
            payload = catalog_payload(slug, device_id, skip=skip)
            data = await fetch_catalog(client, limiter, token, payload)
            cards = product_cards(data)
            if not cards:
                # An empty page can be a transient API shell. Check twice
                # before treating it as the end of a populated category.
                for retry in range(2):
                    await asyncio.sleep(3 * (retry + 1))
                    data = await fetch_catalog(client, limiter, token, payload)
                    cards = product_cards(data)
                    if cards:
                        break
                if not cards and skip == 0:
                    raise RuntimeError(f"Advice returned no products in {slug}")
            codes = {str(item.get("code") or "") for item in cards}
            codes.discard("")
            if cards and codes and codes.issubset(seen_page_codes):
                raise RuntimeError(f"Advice repeated {slug} page at skip={skip}")
            seen_page_codes.update(codes)
            accepted = 0
            for item in cards:
                code = str(item.get("code") or "").strip()
                name = str(item.get("product") or "").strip()
                raw_url = str(item.get("product_url") or "").strip()
                if not (code and name and raw_url):
                    continue
                url = product_url(raw_url)
                image = str(item.get("pic_url") or "").strip()
                price = core.parse_price(str(
                    item.get("price_sale_true") or item.get("price_sale")
                    or item.get("price_srp") or 0), min_price=1,
                )
                category = classify(name, slug, url)
                old = cursor.execute("""
                    SELECT listing_slug, category, product_name, product_url,
                           image_url, detail_status, db_product_id
                    FROM advice_scrape_inventory WHERE source_code=?
                """, (code,)).fetchone()
                if old and category_priority(old[0]) > category_priority(slug):
                    category, primary_slug = old[1], old[0]
                else:
                    primary_slug = slug
                # Preserve a full-size detail image and description on a
                # recurring listing crawl; refetch only changed product URLs.
                if old and old[5] == "complete" and old[3] == url:
                    image = old[4] or image
                    status = "complete"
                else:
                    status = "pending"
                cursor.execute("""
                    INSERT INTO advice_scrape_inventory
                        (source_code, category, listing_slug, product_name,
                         price, image_url, product_url, detail_status,
                         listing_seen_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_code) DO UPDATE SET
                        category=excluded.category,
                        listing_slug=excluded.listing_slug,
                        product_name=excluded.product_name,
                        price=excluded.price,
                        image_url=excluded.image_url,
                        product_url=excluded.product_url,
                        detail_status=excluded.detail_status,
                        listing_seen_at=excluded.listing_seen_at
                """, (code, category, primary_slug, name, price, image,
                      url, status, datetime.now().isoformat(timespec="seconds")))
                cursor.execute("""
                    INSERT OR IGNORE INTO advice_scrape_membership
                        (category_slug, source_code) VALUES (?, ?)
                """, (slug, code))
                accepted += 1
            pages += 1
            skip += PAGE_SIZE
            complete = len(cards) < PAGE_SIZE
            total_accepted = cursor.execute("""
                SELECT COUNT(*) FROM advice_scrape_membership WHERE category_slug=?
            """, (slug,)).fetchone()[0]
            cursor.execute("""
                INSERT INTO advice_scrape_category_audit
                    (category_slug, next_skip, listing_pages,
                     accepted_products, is_complete, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(category_slug) DO UPDATE SET
                    next_skip=excluded.next_skip,
                    listing_pages=excluded.listing_pages,
                    accepted_products=excluded.accepted_products,
                    is_complete=excluded.is_complete,
                    updated_at=excluded.updated_at
            """, (slug, skip, pages, total_accepted, int(complete),
                  datetime.now().isoformat(timespec="seconds")))
            conn.commit()
            core.log(f"  [Advice full] {slug} page={pages} cards={len(cards)} "
                     f"unique_this_pass={len(seen_page_codes)} next={skip if not complete else 'done'}")
            if complete:
                break
        else:
            raise RuntimeError(f"Advice page limit reached in {slug}")


def source_name_matches(name: str, category: str,
                        linked_name: str, linked_category: str) -> bool:
    if name.strip().upper() == linked_name.strip().upper():
        return True
    if category != linked_category:
        # Monitor and headset subtype changes are expected, but mismatched
        # hardware families must not share one retailer URL.
        monitor_cats = {"Monitor", "Dual Mode Monitor", "Portable Monitor", "Curved Monitor"}
        headset_cats = {"Headset", "Gaming Headset", "Wireless Headset"}
        if not ({category, linked_category} <= monitor_cats or
                {category, linked_category} <= headset_cats):
            return False
    return core.is_same_product(name, linked_category, linked_name, linked_category)


def upsert_catalog_product(conn: sqlite3.Connection, matcher: core.SmartMatcher,
                           item: tuple) -> str:
    (code, category, name, price, image, description, url) = item
    cursor = conn.cursor()
    linked = cursor.execute("""
        SELECT product_id, p_name, category, price_jib, price_ihavecpu
        FROM products WHERE url_advice=?
    """, (url,)).fetchall()
    matching = [row for row in linked if source_name_matches(name, category, row[1], row[2])]
    preferred = max(matching, key=lambda row: (
        row[1].strip().upper() == name.strip().upper(),
        bool(row[3] or row[4]),
    )) if matching else None
    for pid, _old_name, _old_cat, _jib, _ihc in linked:
        if preferred and pid == preferred[0]:
            continue
        cursor.execute("""
            UPDATE products SET
                p_description=CASE WHEN p_description=desc_advice THEN
                    COALESCE(NULLIF(desc_jib,''), NULLIF(desc_ihavecpu,''), '')
                    ELSE p_description END,
                specs=CASE WHEN specs=desc_advice THEN
                    COALESCE(NULLIF(desc_jib,''), NULLIF(desc_ihavecpu,''), '')
                    ELSE specs END,
                price_advice=0, url_advice='', desc_advice=''
            WHERE product_id=?
        """, (pid,))
        core._refresh_lowest_price(cursor, pid)
    if price:
        core.upsert_product(cursor, matcher, {
            "name": name, "price": price, "img_url": image,
            "url": url, "category": category, "store": "advice",
            "description": description, "full_catalog": True,
            "source_code": code,
        })
    else:
        # Preserve unavailable-price listings without creating a fake price.
        pid = preferred[0] if preferred else f"adv_{code}"
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT OR IGNORE INTO products
                (product_id, p_name, p_description, p_price,
                 price_advice, price_jib, price_ihavecpu,
                 url_advice, url_jib, url_ihavecpu,
                 desc_advice, desc_jib, desc_ihavecpu,
                 p_stock, cid, category, img_url, specs,
                 created_at, updated_at)
            VALUES (?, ?, ?, 0, 0, 0, 0, ?, '', '', ?, '', '',
                    0, ?, ?, ?, ?, ?, ?)
        """, (pid, name, description, url, description, core.get_cid(category),
              category, image, description, now, now))
        cursor.execute("""
            UPDATE products SET price_advice=0, url_advice=?, desc_advice=?
            WHERE product_id=?
        """, (url, description, pid))
        core._refresh_lowest_price(cursor, pid)
    row = cursor.execute(
        "SELECT product_id FROM products WHERE url_advice=? ORDER BY product_id LIMIT 1",
        (url,),
    ).fetchone()
    if not row:
        raise RuntimeError(f"Advice product {code} could not be saved in products")
    specific_category = category in {
        "Case Fan", "Case Accessories", "GPU Accessories", "Dual Mode Monitor",
        "Portable Monitor", "Curved Monitor", "Gaming Headset",
        "Wireless Headset", "In-Ear Headphone", "True Wireless Earbuds",
    }
    cursor.execute("""
        UPDATE products SET category=?, cid=?
        WHERE product_id=? AND
            ((COALESCE(price_jib, 0)=0 AND COALESCE(price_ihavecpu, 0)=0)
             OR ?)
    """, (category, core.get_cid(category), row[0], int(specific_category)))
    cursor.execute("""
        UPDATE advice_scrape_inventory SET db_product_id=? WHERE source_code=?
    """, (row[0], code))
    conn.commit()
    return row[0]


async def hydrate_details(conn: sqlite3.Connection, matcher: core.SmartMatcher,
                          client: httpx.AsyncClient,
                          limiter: core.AdaptiveRateLimiter, token: str,
                          device_id: str, slugs: list[str]) -> None:
    placeholders = ",".join("?" for _ in slugs)
    rows = conn.execute(f"""
        SELECT DISTINCT i.source_code, i.category, i.product_name, i.price,
               i.image_url, i.description, i.product_url, i.detail_status
        FROM advice_scrape_inventory AS i
        JOIN advice_scrape_membership AS m ON m.source_code=i.source_code
        WHERE m.category_slug IN ({placeholders})
        ORDER BY i.source_code
    """, slugs).fetchall()
    pending = sum(status != "complete" or not description
                  for _code, _cat, _name, _price, _img, description, _url, status in rows)
    core.log(f"  [Advice full] inventory={len(rows)} detail_pending={pending}")
    done = 0
    for code, category, name, price, image, old_description, url, status in rows:
        if status == "complete" and old_description:
            # A new listing pass may have changed price or subtype. Keep the
            # full detail but reconcile those fields in the product table.
            upsert_catalog_product(conn, matcher,
                                   (code, category, name, price, image, old_description, url))
            continue
        payload = catalog_payload(category, device_id, product_url=url)
        data = await fetch_catalog(client, limiter, token, payload)
        product = data.get("product") or {}
        detail_code = str(product.get("code") or "") if isinstance(product, dict) else ""
        same_url_alias = bool(detail_code and detail_code != code and
                              conn.execute("""
                                  SELECT 1 FROM advice_scrape_inventory
                                  WHERE source_code=? AND product_url=?
                                    AND product_name=?
                              """, (detail_code, url, name)).fetchone())
        if not isinstance(product, dict) or (detail_code != code and not same_url_alias):
            conn.execute("""
                UPDATE advice_scrape_inventory SET detail_status='missing',
                    detail_checked_at=? WHERE source_code=?
            """, (datetime.now().isoformat(timespec="seconds"), code))
            conn.commit()
            core.log(f"  [Advice full] detail missing for {code}; source URL may have changed")
            continue
        description, detail_image, images = flatten_detail(
            product, str(product.get("spec") or ""),
        )
        if not description:
            core.log(f"  [Advice full] no specification text for {code}")
        image = detail_image or image
        conn.execute("""
            UPDATE advice_scrape_inventory SET
                image_url=?, images_json=?, description=?, spec_json=?,
                detail_status=?, detail_checked_at=?
            WHERE source_code=?
        """, (image, json.dumps(images, ensure_ascii=False), description,
              json.dumps(product.get("spec_detail") or [], ensure_ascii=False),
              "complete" if description and image else "missing",
              datetime.now().isoformat(timespec="seconds"), code))
        conn.commit()
        if description and image:
            upsert_catalog_product(conn, matcher,
                                   (code, category, name, price, image, description, url))
        done += 1
        if done % 25 == 0 or done == pending:
            core.log(f"  [Advice full] detail {done}/{pending} "
                     f"429={limiter.total_429}")


async def run(slugs: list[str], *, list_only: bool,
              details_only: bool, refresh_listings: bool,
              interval: float) -> None:
    conn = sqlite3.connect(core.DB_PATH)
    try:
        core.setup_db(conn)
        setup_inventory(conn)
        changed = reclassify_inventory(conn)
        if changed:
            core.log(f"  [Advice full] corrected categories={changed}")
        matcher = core.SmartMatcher(conn.cursor())
        limiter = core.AdaptiveRateLimiter(
            "advice", threshold=2, base_cooldown_seconds=45,
            max_cooldown_seconds=240, min_interval_seconds=interval,
        )
        device_id = uuid4().hex
        async with httpx.AsyncClient(
            headers={"User-Agent": core.UA,
                     "Origin": "https://www.advice.co.th",
                     "Referer": "https://www.advice.co.th/",
                     "Accept": "application/json, text/plain, */*",
                     "Accept-Language": "th-TH,th;q=0.9,en;q=0.8"},
            timeout=httpx.Timeout(35.0, connect=15.0),
            follow_redirects=True,
            limits=httpx.Limits(max_connections=2),
        ) as client:
            token = await guest_token(client, limiter)
            if not details_only:
                await crawl_listings(conn, client, limiter, token,
                                     device_id, slugs, refresh_listings)
            if not list_only:
                await hydrate_details(conn, matcher, client, limiter,
                                      token, device_id, slugs)
        audit = inventory_audit(conn, slugs)
        core.log(f"  [Advice full] audit={json.dumps(audit, ensure_ascii=False)} "
                 f"429={limiter.total_429}")
        if not list_only and (audit["completed_categories"] != len(slugs) or
                              audit["complete_details"] != audit["unique_products"]):
            raise RuntimeError("Advice inventory is incomplete; rerun to retry missing items")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--categories", nargs="+", choices=CATEGORIES,
                        default=list(CATEGORIES))
    parser.add_argument("--list-only", action="store_true")
    parser.add_argument("--details-only", action="store_true")
    parser.add_argument("--refresh-listings", action="store_true")
    parser.add_argument("--skip-compat-training", action="store_true")
    parser.add_argument("--interval", type=float, default=1.2)
    args = parser.parse_args()
    if args.list_only and args.details_only:
        parser.error("--list-only and --details-only are mutually exclusive")
    if args.details_only and args.refresh_listings:
        parser.error("--refresh-listings cannot be used with --details-only")
    if args.interval < 0.8:
        parser.error("--interval must be at least 0.8 seconds")
    asyncio.run(run(list(dict.fromkeys(args.categories)),
                    list_only=args.list_only,
                    details_only=args.details_only,
                    refresh_listings=args.refresh_listings,
                    interval=args.interval))
    if not args.list_only and not args.skip_compat_training:
        trainer = os.path.join(os.path.dirname(__file__), "train_compat_knowledge.py")
        result = subprocess.run([sys.executable, "-X", "utf8", trainer, "--apply"],
                                check=False)
        if result.returncode:
            raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
