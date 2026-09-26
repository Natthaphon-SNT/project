"""Check live retailer product links and retire confirmed missing offers.

Dry-run by default. Example:
    python audit_product_links.py --stores ihavecpu --limit 25
    python audit_product_links.py --stores ihavecpu --apply
"""

import argparse
import asyncio
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx


STORE_COLUMNS = {
    "advice": ("url_advice", "price_advice", "www.advice.co.th", "/product/"),
    "jib": ("url_jib", "price_jib", "www.jib.co.th", "/web/product/readProduct/"),
    "ihavecpu": ("url_ihavecpu", "price_ihavecpu", "ihavecpu.com", "/product/"),
}


def retailer_url_is_valid(store: str, url: str) -> bool:
    _, _, host, prefix = STORE_COLUMNS[store]
    parsed = urlparse(url)
    allowed_hosts = {host}
    if store == "ihavecpu":
        allowed_hosts.add("www.ihavecpu.com")
    return (parsed.scheme == "https" and parsed.hostname in allowed_hosts
            and parsed.path.startswith(prefix))


async def check_link(client: httpx.AsyncClient, semaphore: asyncio.Semaphore,
                     store: str, url: str) -> str:
    if not retailer_url_is_valid(store, url):
        return "invalid-path"
    async with semaphore:
        for attempt in range(2):
            try:
                response = await client.get(url, follow_redirects=True)
                if response.status_code in (404, 410):
                    if attempt == 0:
                        await asyncio.sleep(0.4)
                        continue
                    return "missing"
                if response.status_code == 200:
                    return "ok"
                return f"http-{response.status_code}"
            except (httpx.TimeoutException, httpx.TransportError):
                if attempt == 0:
                    await asyncio.sleep(0.4)
                    continue
                return "network-error"
    return "network-error"


async def audit(db_path: Path, stores: list[str], limit: int, product_id: str,
                concurrency: int, apply: bool) -> int:
    conn = sqlite3.connect(db_path, timeout=60)
    rows = []
    for store in stores:
        url_col, price_col, _, _ = STORE_COLUMNS[store]
        query = f"""SELECT product_id, p_name, {url_col} FROM products
                    WHERE COALESCE({price_col}, 0)>0 AND LENGTH(TRIM(COALESCE({url_col}, '')))>0"""
        params = []
        if product_id:
            query += " AND product_id=?"
            params.append(product_id)
        query += " ORDER BY product_id"
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        rows.extend((store, *row) for row in conn.execute(query, params))

    headers = {"User-Agent": "Mozilla/5.0 (compatible; IT-Recommend-LinkAudit/1.0)",
               "Accept": "text/html,application/xhtml+xml"}
    timeout = httpx.Timeout(15.0, connect=8.0)
    semaphore = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        checks = await asyncio.gather(*(
            check_link(client, semaphore, store, url)
            for store, _, _, url in rows
        ))

    counts = Counter()
    retired = 0
    missing_ids = {store: [] for store in stores}
    for (store, pid, name, url), result in zip(rows, checks):
        counts[(store, result)] += 1
        if result == "missing":
            missing_ids[store].append(pid)
        if result != "ok":
            print(f"{store:8} {result:13} {pid} {name[:55]} {url}", flush=True)
        if apply and result == "missing":
            url_col, price_col, _, _ = STORE_COLUMNS[store]
            # Guard against a concurrent scrape changing the offer mid-audit.
            cursor = conn.execute(
                f"UPDATE products SET {price_col}=0, {url_col}='', updated_at=? "
                f"WHERE product_id=? AND {url_col}=?",
                (datetime.now(timezone.utc).isoformat(timespec="seconds"), pid, url),
            )
            if cursor.rowcount:
                prices = conn.execute(
                    "SELECT price_advice, price_jib, price_ihavecpu FROM products WHERE product_id=?",
                    (pid,),
                ).fetchone()
                remaining = [int(price) for price in prices if price and price > 0]
                conn.execute("UPDATE products SET p_price=? WHERE product_id=?",
                             (min(remaining) if remaining else 0, pid))
                retired += 1
    if apply:
        conn.commit()
    conn.close()
    for (store, result), count in sorted(counts.items()):
        print(f"SUMMARY {store:8} {result:13} {count}")
    for store, ids in missing_ids.items():
        if ids:
            print(f"MISSING_IDS {store} {','.join(ids)}")
    print(f"CHECKED {len(rows)} RETIRED {retired} APPLY {apply}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(__file__).with_name("shop.db"))
    parser.add_argument("--stores", choices=[*STORE_COLUMNS, "all"], nargs="+", default=["all"])
    parser.add_argument("--limit", type=int, default=0, help="Maximum offers per store (0 = all)")
    parser.add_argument("--product-id", default="")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--apply", action="store_true", help="Clear price and URL only for confirmed 404/410")
    args = parser.parse_args()
    if args.limit < 0 or not 1 <= args.concurrency <= 8:
        parser.error("--limit must be nonnegative and --concurrency must be 1-8")
    stores = list(STORE_COLUMNS) if "all" in args.stores else list(dict.fromkeys(args.stores))
    return asyncio.run(audit(args.db, stores, args.limit, args.product_id,
                             args.concurrency, args.apply))


if __name__ == "__main__":
    raise SystemExit(main())
