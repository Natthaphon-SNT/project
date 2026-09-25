"""Refresh active PC sets and repair their primary images/descriptions.

Sources:
* iHaveCPU public product-search API plus the current Next.js detail payload.
* JIB product detail pages for rows already linked by retailer product ID.

The job is resumable through normal product/inventory upserts. Retired iHaveCPU
rows are not deleted; source-only PC sets whose detail page is confirmed gone
are assigned a zero source price so the storefront no longer shows stale cards.
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
import html as html_lib
import json
import re
import sqlite3
from urllib.parse import quote

import httpx

import full_scraper as core
import jib_full_scraper as jib


IHC_API = "https://apisp.ihavecpu.com/api"
IHC_WEB = "https://ihavecpu.com"
MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN",
          "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")


def month_prefixes(count: int) -> list[str]:
    now = datetime.now()
    year, month = now.year, now.month
    result = []
    for _ in range(count):
        result.append(f"{MONTHS[month - 1]}{year % 100:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return result


def listing_description(item: dict) -> str:
    summary = core._plain_html(item.get("size_guide_th") or "")
    title = (item.get("name_th") or item.get("name_gb") or "").strip()
    parts = []
    if summary:
        parts.append(f"Summary: {summary}")
    if title:
        parts.append(f"Product specification: {title}")
    return "\n".join(parts)


async def search_pcsets(client: httpx.AsyncClient, prefixes: list[str]) -> list[dict]:
    found: dict[int, dict] = {}
    for prefix in prefixes:
        offset = 0
        total = None
        while total is None or offset < total:
            response = await core.request_with_retry(
                client, "POST", f"{IHC_API}/product/search",
                json={"search": prefix, "lang": "th", "field": "sell_price",
                      "sort": "asc", "offset": offset, "limit": 200},
            )
            response.raise_for_status()
            payload = response.json()
            if payload.get("res_code") != "00":
                raise RuntimeError(f"iHaveCPU search failed for {prefix}")
            result = payload.get("res_result") or {}
            total = int(result.get("count") or 0)
            rows = result.get("data") or []
            for item in rows:
                name = (item.get("name_th") or item.get("name_gb") or "").strip()
                category_name = item.get("cat_name_th") or ""
                if (item.get("category_id") == 61
                        or "คอมพิวเตอร์เซต" in category_name
                        or core.is_pc_set_name(name)):
                    product_id = int(item.get("product_id") or 0)
                    if product_id and name and not core.should_skip(name):
                        found[product_id] = item
            core.log(f"  [PC Set/iHaveCPU] {prefix} {min(offset + len(rows), total)}/{total}")
            if not rows:
                break
            offset += len(rows)
            await asyncio.sleep(0.35)
    return list(found.values())


async def next_build_id(client: httpx.AsyncClient) -> str:
    response = await core.request_with_retry(client, "GET", f"{IHC_WEB}/promotion")
    response.raise_for_status()
    match = re.search(r"/_next/static/([^/]+)/_buildManifest\.js", response.text)
    if not match:
        raise RuntimeError("Could not discover iHaveCPU Next.js build ID")
    return match.group(1)


async def hydrate_ihc_pcsets(conn: sqlite3.Connection,
                             client: httpx.AsyncClient, items: list[dict],
                             build_id: str, concurrency: int,
                             interval: float) -> dict[int, tuple[str, str]]:
    semaphore = asyncio.Semaphore(concurrency)
    host_lock = asyncio.Lock()
    last_request = 0.0
    loop = asyncio.get_running_loop()
    completed = 0
    results: dict[int, tuple[str, str]] = {}
    pending = []
    for item in items:
        product_id = int(item["product_id"])
        cached = conn.execute("""
            SELECT desc_ihavecpu, img_url FROM products
            WHERE url_ihavecpu LIKE ? AND length(trim(coalesce(desc_ihavecpu,'')))>=30
            LIMIT 1
        """, (f"%/product/{product_id}/%",)).fetchone()
        if cached and cached[1] and not core.is_placeholder_image_url(cached[1]):
            results[product_id] = (cached[0], cached[1])
        else:
            pending.append(item)
    core.log(f"  [PC Set/iHaveCPU] details cached={len(results)} pending={len(pending)}")

    async def one(item: dict) -> tuple[int, tuple[str, str]]:
        nonlocal last_request, completed
        product_id = int(item["product_id"])
        async with semaphore:
            async with host_lock:
                wait = interval - (loop.time() - last_request)
                if wait > 0:
                    await asyncio.sleep(wait)
                last_request = loop.time()
            url = (f"{IHC_WEB}/_next/data/{quote(build_id, safe='')}/product/"
                   f"{product_id}/product.json?product_id={product_id}&slug=product")
            description = ""
            image = ""
            for attempt in range(3):
                try:
                    response = await client.get(url)
                    if response.status_code in (403, 429):
                        await asyncio.sleep(4 * (attempt + 1))
                        continue
                    response.raise_for_status()
                    product = (response.json().get("pageProps") or {}).get("product") or {}
                    if int(product.get("product_id") or 0) != product_id:
                        raise RuntimeError("detail product ID mismatch")
                    description = core.ihc_product_description(product)
                    pictures = product.get("picture") or []
                    if pictures:
                        image = pictures[0].get("pic_800") or pictures[0].get("pic_150") or ""
                    break
                except Exception:
                    if attempt == 2:
                        break
                    await asyncio.sleep(1.5 * (attempt + 1))
            completed += 1
            if completed % 50 == 0 or completed == len(pending):
                core.log(f"  [PC Set/iHaveCPU] details {completed}/{len(pending)}")
            return product_id, (description, image)

    if pending:
        results.update(dict(await asyncio.gather(*(one(item) for item in pending))))
    return results


def save_ihc_pcsets(conn: sqlite3.Connection, items: list[dict],
                    details: dict[int, tuple[str, str]], prefixes: list[str]) -> set[int]:
    matcher = core.SmartMatcher(conn.cursor())
    active_ids: set[int] = set()
    now = datetime.now().isoformat(timespec="seconds")
    for item in items:
        source_id = int(item["product_id"])
        active_ids.add(source_id)
        name = (item.get("name_th") or item.get("name_gb") or "").strip()
        price = core.parse_price(str(item.get("price_sale") or item.get("price_before") or ""),
                                 min_price=1)
        detail_description, detail_image = details.get(source_id, ("", ""))
        description = core.combine_descriptions(detail_description, listing_description(item))
        image = (detail_image or item.get("image800") or item.get("image") or "").strip()
        url = core.ihc_product_url(source_id, name)
        core.upsert_product(conn.cursor(), matcher, {
            "name": name, "price": price, "img_url": image, "url": url,
            "category": "PC Set", "store": "ihavecpu",
            "description": description, "full_catalog": True,
        })
        stored = conn.execute(
            "SELECT product_id FROM products WHERE url_ihavecpu LIKE ? LIMIT 1",
            (f"%/product/{source_id}/%",),
        ).fetchone()
        prefix = next((value for value in prefixes if name.upper().startswith(value)), prefixes[0])
        conn.execute("""
            INSERT INTO ihavecpu_scrape_inventory
                (category_url, source_product_id, category, product_name, price,
                 image_url, description, product_url, db_product_id, scraped_at)
            VALUES (?, ?, 'PC Set', ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(category_url, source_product_id) DO UPDATE SET
                category=excluded.category, product_name=excluded.product_name,
                price=excluded.price, image_url=excluded.image_url,
                description=excluded.description, product_url=excluded.product_url,
                db_product_id=excluded.db_product_id, scraped_at=excluded.scraped_at
        """, (f"api://product/search/{prefix}", source_id, name, price, image,
              description, url, stored[0] if stored else "", now))
    conn.commit()
    return active_ids


async def retire_dead_placeholder_sets(conn: sqlite3.Connection,
                                       client: httpx.AsyncClient,
                                       active_ids: set[int]) -> int:
    rows = conn.execute("""
        SELECT product_id, url_ihavecpu FROM products
        WHERE category='PC Set' AND price_ihavecpu>0
          AND lower(img_url) LIKE '%/logos/android-chrome-%'
          AND price_advice=0 AND price_jib=0
    """).fetchall()
    retired = 0
    for product_id, url in rows:
        match = re.search(r"/product/(\d+)", url or "")
        source_id = int(match.group(1)) if match else 0
        if source_id in active_ids:
            continue
        try:
            response = await client.get(url)
            gone = response.status_code == 404 or str(response.url).rstrip("/").endswith("/404")
        except Exception:
            gone = False
        if gone:
            conn.execute("UPDATE products SET price_ihavecpu=0 WHERE product_id=?",
                         (product_id,))
            core._refresh_lowest_price(conn.cursor(), product_id)
            retired += 1
        await asyncio.sleep(0.25)
    conn.commit()
    return retired


async def repair_jib_pcsets(conn: sqlite3.Connection, client: httpx.AsyncClient,
                            concurrency: int, interval: float) -> tuple[int, int]:
    rows = conn.execute("""
        SELECT product_id, p_name, url_jib FROM products
        WHERE category='PC Set' AND price_jib>0 AND trim(coalesce(url_jib,''))!=''
        ORDER BY product_id
    """).fetchall()
    semaphore = asyncio.Semaphore(concurrency)
    lock = asyncio.Lock()
    loop = asyncio.get_running_loop()
    last_request = 0.0

    async def one(row):
        nonlocal last_request
        async with semaphore:
            async with lock:
                wait = interval - (loop.time() - last_request)
                if wait > 0:
                    await asyncio.sleep(wait)
                last_request = loop.time()
            desc, image = await core.fetch_jib_detail_http(
                client, row[2], row[1], "PC Set", strict_block=True,
            )
            return row, desc, image

    repaired = failed = 0
    results = await asyncio.gather(*(one(row) for row in rows))
    now = datetime.now().isoformat(timespec="seconds")
    for row, description, image in results:
        if len(description.strip()) < 30 or not image:
            failed += 1
            continue
        conn.execute("""
            UPDATE products SET desc_jib=?, p_description=?, specs=?, img_url=?, updated_at=?
            WHERE product_id=?
        """, (description, description, description, image, now, row[0]))
        repaired += 1
    conn.commit()
    return repaired, failed


async def run(months: int, concurrency: int, interval: float) -> None:
    prefixes = month_prefixes(months)
    headers = {"User-Agent": core.UA, "Accept": "text/html,application/json",
               "Origin": IHC_WEB, "Referer": f"{IHC_WEB}/"}
    conn = sqlite3.connect(core.DB_PATH)
    try:
        core.setup_db(conn)
        async with httpx.AsyncClient(
            headers=headers, follow_redirects=True,
            timeout=httpx.Timeout(35.0, connect=15.0),
            limits=httpx.Limits(max_connections=concurrency + 2),
        ) as client:
            core.log(f"  [PC Set] iHaveCPU search prefixes={prefixes}")
            items = await search_pcsets(client, prefixes)
            build_id = await next_build_id(client)
            details = await hydrate_ihc_pcsets(
                conn, client, items, build_id, concurrency, interval,
            )
            active_ids = save_ihc_pcsets(conn, items, details, prefixes)
            retired = await retire_dead_placeholder_sets(conn, client, active_ids)
            repaired, failed = await repair_jib_pcsets(
                conn, client, concurrency=min(concurrency, 4),
                interval=max(interval, 0.8),
            )
        core.log(f"  [PC Set] iHaveCPU active={len(active_ids)} retired_stale={retired}")
        core.log(f"  [PC Set] JIB repaired={repaired} failed={failed}")
        synced = core.sync_best_product_descriptions(conn)
        if synced:
            core.log(f"  [PC Set] synced best display descriptions={synced}")
        if failed:
            raise RuntimeError(f"JIB PC Set details still missing for {failed} rows")
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--months", type=int, default=2,
                        help="Current and previous month prefixes to import")
    parser.add_argument("--concurrency", type=int, choices=range(1, 7), default=4)
    parser.add_argument("--interval", type=float, default=0.4,
                        help="Minimum seconds between iHaveCPU detail requests")
    args = parser.parse_args()
    if not 1 <= args.months <= 6:
        parser.error("--months must be 1..6")
    if args.interval < 0.3:
        parser.error("--interval must be at least 0.3")
    asyncio.run(run(args.months, args.concurrency, args.interval))


if __name__ == "__main__":
    main()
