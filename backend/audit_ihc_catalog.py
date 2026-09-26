"""Compare iHaveCPU offers with live category listings, then verify omissions.

Read-only. Category pages contain 12-24 products each, so this is much gentler
than requesting every product page. PC sets and omitted IDs are checked by URL.
"""

import argparse
import asyncio
import re
import sqlite3
from collections import Counter
from pathlib import Path

import httpx

import audit_product_links as link_audit
import full_scraper as scraper
from retire_missing_ihc_offers import parse_pairs


async def category_ids(client: httpx.AsyncClient, semaphore: asyncio.Semaphore,
                       name: str, base_url: str) -> set[int]:
    seen: set[int] = set()
    total = 0
    page = 1
    while True:
        url = base_url if page == 1 else f"{base_url}?page={page}"
        async with semaphore:
            response = await client.get(url)
        response.raise_for_status()
        data = scraper.extract_next_data(response.text)
        product = data.get("props", {}).get("pageProps", {}).get("product", {})
        if not isinstance(product, dict):
            raise RuntimeError(f"{name}: missing listing payload at {url}")
        total = max(total, scraper.ihc_listing_total(response.text))
        items = product.get("data") or []
        page_ids = {int(item["product_id"]) for item in items if item.get("product_id")}
        if not total or not page_ids or page_ids.issubset(seen):
            raise RuntimeError(f"{name}: incomplete listing at page {page}; {len(seen)}/{total}")
        seen.update(page_ids)
        if len(seen) >= total:
            print(f"LISTING {name}: {len(seen)}/{total} IDs in {page} pages", flush=True)
            return seen
        page += 1
        if page > total + 2:
            raise RuntimeError(f"{name}: page safety limit exceeded")
        await asyncio.sleep(0.15)


def source_id(url: str) -> int:
    match = re.search(r"https?://(?:www\.)?ihavecpu\.com/product/(\d+)/", url or "")
    return int(match.group(1)) if match else 0


async def run(db_path: Path, concurrency: int = 5,
              verify_pairs: str = "") -> None:
    conn = sqlite3.connect(db_path)
    rows = conn.execute("""SELECT product_id, p_name, category, url_ihavecpu
        FROM products WHERE price_ihavecpu>0 AND LENGTH(TRIM(COALESCE(url_ihavecpu,'')))>0
        ORDER BY product_id""").fetchall()
    conn.close()
    if verify_pairs:
        requested = dict(parse_pairs(verify_pairs))
        candidates = [row for row in rows if row[0] in requested]
        if len(candidates) != len(requested) or any(
            source_id(row[3]) != requested[row[0]] for row in candidates
        ):
            raise ValueError("Verify pairs do not match local iHaveCPU offers")
        print(f"VERIFY requested={len(candidates)}", flush=True)
    else:
        listing_headers = {
            "User-Agent": scraper.UA,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
        }
        listing_semaphore = asyncio.Semaphore(4)
        async with httpx.AsyncClient(headers=listing_headers, timeout=25,
                                     follow_redirects=True) as client:
            groups = await asyncio.gather(*(
                category_ids(client, listing_semaphore, name, url)
                for name, url in scraper.IHC_FULL_CATS
            ))
        live_ids = set().union(*groups)
        candidates = [row for row in rows if source_id(row[3]) not in live_ids]
        print(f"CATALOG checked={len(rows)} listed={len(rows)-len(candidates)} "
              f"need_detail={len(candidates)}", flush=True)
    results = Counter()
    missing = []
    unknown = []
    detail_semaphore = asyncio.Semaphore(concurrency)
    detail_headers = {"User-Agent": scraper.UA, "Accept": "text/html,application/xhtml+xml"}
    async with httpx.AsyncClient(headers=detail_headers, timeout=httpx.Timeout(15, connect=8)) as client:
        async def check(row):
            result = await link_audit.check_link(client, detail_semaphore, "ihavecpu", row[3])
            return row, result
        for row, result in await asyncio.gather(*(check(row) for row in candidates)):
            results[result] += 1
            if result == "missing":
                missing.append((row[0], source_id(row[3])))
                print(f"MISSING {row[0]} {source_id(row[3])} {row[3]}", flush=True)
            elif result != "ok":
                unknown.append((row[0], source_id(row[3])))
    print(f"SUMMARY listed={len(rows)-len(candidates)} "
          + " ".join(f"{key}={value}" for key, value in sorted(results.items())), flush=True)
    print("MISSING_IDS " + ",".join(f"{pid}:{sid}" for pid, sid in missing), flush=True)
    print("UNKNOWN_IDS " + ",".join(f"{pid}:{sid}" for pid, sid in unknown), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(__file__).with_name("shop.db"))
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--verify-pairs", default="")
    args = parser.parse_args()
    if not 1 <= args.concurrency <= 8:
        parser.error("--concurrency must be 1-8")
    asyncio.run(run(args.db, args.concurrency, args.verify_pairs))
