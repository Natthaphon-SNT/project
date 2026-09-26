"""Prefetch approved retailer images into the configured S3-compatible bucket.

Run manually or as a scheduled job after a scrape. Existing objects are
listed once and skipped; no local-disk cache is used.
"""

import argparse
import asyncio
from collections import Counter
import os
from pathlib import Path
import sqlite3
from urllib.parse import urlparse

import httpx

from product_image_cache import (
    _object_key, existing_object_keys, fetch_and_upload,
    storage_config, validated_host,
)


QUERIES = {
    "advice": """SELECT DISTINCT img_url FROM products
                   WHERE price_advice>0 AND trim(coalesce(img_url,''))!=''""",
    "jib": """SELECT DISTINCT img_url FROM products
                WHERE price_jib>0 AND trim(coalesce(img_url,''))!=''""",
    "ihavecpu": """SELECT DISTINCT img_url FROM products
                     WHERE price_ihavecpu>0 AND trim(coalesce(img_url,''))!=''""",
}


def database_path() -> Path:
    db_url = os.getenv("DATABASE_URL", "")
    if db_url:
        if not db_url.startswith("sqlite:///"):
            raise ValueError("Prefetch supports a SQLite DATABASE_URL only")
        return Path(db_url.removeprefix("sqlite:///"))
    return Path(__file__).resolve().parent / "shop.db"


def source_urls(stores: list[str], db_path: Path | None = None,
                categories: list[str] | None = None) -> list[tuple[str, str]]:
    conn = sqlite3.connect(db_path or database_path())
    try:
        items: dict[str, str] = {}
        for store in stores:
            query = QUERIES[store]
            params: tuple[str, ...] = ()
            if categories:
                query += " AND lower(category) IN (" + ",".join("?" for _ in categories) + ")"
                params = tuple(category.lower() for category in categories)
            # The public catalog shows newest items first. Warm those images
            # first, so a bounded repair helps the products customers see now.
            query += " ORDER BY created_at DESC"
            for (url,) in conn.execute(query, params):
                if url not in items:
                    items[url] = store
        return [(store, url) for url, store in items.items()]
    finally:
        conn.close()


def source_urls_from_api(base_url: str, stores: list[str],
                         categories: list[str]) -> list[tuple[str, str]]:
    """Use the deployed catalog rather than assuming a local DB is identical."""
    if not base_url.startswith("https://"):
        raise ValueError("Catalog API base must use HTTPS")
    items: dict[str, str] = {}
    with httpx.Client(timeout=30.0) as client:
        for category in categories:
            page = 1
            while True:
                response = client.get(
                    base_url.rstrip("/") + "/api/products",
                    params={"category": category, "page": page, "limit": 100},
                )
                response.raise_for_status()
                payload = response.json()
                if payload.get("status") != "success" or not isinstance(payload.get("data"), list):
                    raise ValueError("Catalog API returned invalid products")
                for product in payload["data"]:
                    url = product.get("img_url") or ""
                    for store in stores:
                        if product.get("price_" + store, 0) > 0 and url:
                            items.setdefault(url, store)
                            break
                total_pages = int(payload.get("pagination", {}).get("total_pages", 0))
                if page >= total_pages:
                    break
                page += 1
    return [(store, url) for url, store in items.items()]


async def run(stores: list[str], concurrency: int, interval: float,
              limit: int | None, db_path: Path | None = None,
              hosts: list[str] | None = None,
              categories: list[str] | None = None,
              api_base: str | None = None) -> int:
    urls = (source_urls_from_api(api_base, stores, categories or []) if api_base
            else source_urls(stores, db_path, categories))
    if storage_config() is None:
        raise RuntimeError("Set IMAGE_S3_* bucket credentials before prefetching")
    cached_keys = existing_object_keys()
    print(f"Storage mode: object bucket; existing={len(cached_keys)}", flush=True)

    pending = []
    skipped = 0
    for store, url in urls:
        try:
            host = validated_host(url)
            if hosts and not any(host == allowed or host.endswith('.' + allowed)
                                 for allowed in hosts):
                skipped += 1
                continue
            if _object_key(url) in cached_keys:
                skipped += 1
            else:
                pending.append((store, url))
        except ValueError:
            # Invalid host — skip silently
            skipped += 1

    if limit is not None:
        pending = pending[:limit]
    print(f"images: total={len(urls)} cached={skipped} pending={len(pending)}", flush=True)
    if not pending:
        return 0

    queue: asyncio.Queue = asyncio.Queue()
    for item in pending:
        queue.put_nowait(item)
    host_locks: dict[str, asyncio.Lock] = {}
    last_request: dict[str, float] = {}
    results: Counter = Counter()
    errors: list[tuple[str, str]] = []
    blocked_hosts: set[str] = set()
    blocked_count = 0
    completed = 0
    loop = asyncio.get_running_loop()

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(35.0, connect=15.0),
        limits=httpx.Limits(max_connections=concurrency),
        follow_redirects=False,
    ) as client:
        async def worker() -> None:
            nonlocal completed, blocked_count
            while True:
                try:
                    store, url = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return
                try:
                    host = urlparse(url).hostname or ""
                    lock = host_locks.setdefault(host, asyncio.Lock())
                    async with lock:
                        if host in blocked_hosts:
                            blocked_count += 1
                            continue
                        wait = interval - (loop.time() - last_request.get(host, 0.0))
                        if wait > 0:
                            await asyncio.sleep(wait)
                        last_request[host] = loop.time()

                    cached_url, _ = await fetch_and_upload(url, client)
                    if not cached_url:
                        raise ValueError("Image upload returned no cached URL")

                    results[store] += 1
                except Exception as exc:
                    errors.append((url, str(exc)[:140]))
                    # Do not keep hammering a store that explicitly rate-limits.
                    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in (403, 429):
                        blocked_hosts.add(urlparse(url).hostname or "")
                        print(f"{store}: pausing blocked host after HTTP {exc.response.status_code}", flush=True)
                finally:
                    completed += 1
                    queue.task_done()
                    if completed % 100 == 0 or completed == len(pending):
                        print(
                            f"images: {completed}/{len(pending)} "
                            f"saved={sum(results.values())} failed={len(errors)} blocked={blocked_count}",
                            flush=True,
                        )

        await asyncio.gather(*(worker() for _ in range(concurrency)))

    print(f"saved_by_store={dict(results)} failed={len(errors)} blocked={blocked_count}", flush=True)
    for url, error in errors[:20]:
        print(f"  FAILED {url}: {error}", flush=True)
    return len(errors)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stores", nargs="+", choices=QUERIES, default=list(QUERIES))
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--interval", type=float, default=0.35,
                        help="Minimum seconds between requests to the same host")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only fetch this many uncached images (for smoke tests)")
    parser.add_argument("--database", type=Path, default=None,
                        help="SQLite file; overrides DATABASE_URL (useful with railway run)")
    parser.add_argument("--hosts", nargs="+", default=None,
                        help="Only prefetch these approved host suffixes")
    parser.add_argument("--categories", nargs="+", default=None,
                        help="Only prefetch products in these catalog categories, e.g. GPU")
    parser.add_argument("--api-base", default=None,
                        help="Read current products from an HTTPS deployment instead of a local SQLite DB")
    args = parser.parse_args()
    if not 1 <= args.concurrency <= 12 or args.interval < 0.2:
        parser.error("concurrency must be 1..12 and interval at least 0.2 seconds")
    if args.limit is not None and args.limit < 1:
        parser.error("limit must be positive")
    if args.api_base and not args.categories:
        parser.error("--api-base requires --categories to keep the fetch bounded")
    raise SystemExit(int(asyncio.run(
        run(args.stores, args.concurrency, args.interval, args.limit,
            args.database, args.hosts, args.categories, args.api_base)
    ) > 0))


if __name__ == "__main__":
    main()
