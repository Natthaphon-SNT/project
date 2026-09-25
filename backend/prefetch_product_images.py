"""Download verified primary product images for the three full catalogues.

Resumable: a successfully cached URL is skipped on later runs. This imports
image bytes, not just image URLs, so the storefront can serve a local copy.
"""

import argparse
import asyncio
from collections import Counter
import sqlite3
from urllib.parse import urlparse

import httpx

import full_scraper as core
from product_image_cache import cached_image, fetch_image, validated_host


QUERIES = {
    "advice": """SELECT DISTINCT img_url FROM products
                   WHERE price_advice>0 AND trim(coalesce(img_url,''))!=''""",
    "jib": """SELECT DISTINCT img_url FROM products
                WHERE price_jib>0 AND trim(coalesce(img_url,''))!=''""",
    "ihavecpu": """SELECT DISTINCT img_url FROM products
                     WHERE price_ihavecpu>0 AND trim(coalesce(img_url,''))!=''""",
}


def source_urls(stores: list[str]) -> list[tuple[str, str]]:
    conn = sqlite3.connect(core.DB_PATH)
    try:
        items: dict[str, str] = {}
        for store in stores:
            for (url,) in conn.execute(QUERIES[store]):
                if url not in items:
                    items[url] = store
        return [(store, url) for url, store in items.items()]
    finally:
        conn.close()


async def run(stores: list[str], concurrency: int, interval: float,
              limit: int | None) -> int:
    urls = source_urls(stores)
    pending = []
    skipped = 0
    for store, url in urls:
        try:
            validated_host(url)
            if cached_image(url):
                skipped += 1
            else:
                pending.append((store, url))
        except ValueError:
            pending.append((store, url))
    if limit is not None:
        pending = pending[:limit]
    print(f"images: total={len(urls)} cached={skipped} pending={len(pending)}", flush=True)
    if not pending:
        return 0

    queue = asyncio.Queue()
    for item in pending:
        queue.put_nowait(item)
    host_locks: dict[str, asyncio.Lock] = {}
    last_request: dict[str, float] = {}
    results = Counter()
    errors: list[tuple[str, str]] = []
    completed = 0
    loop = asyncio.get_running_loop()

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(35.0, connect=15.0),
        limits=httpx.Limits(max_connections=concurrency),
        follow_redirects=False,
    ) as client:
        async def worker() -> None:
            nonlocal completed
            while True:
                try:
                    store, url = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return
                try:
                    host = urlparse(url).hostname or ""
                    lock = host_locks.setdefault(host, asyncio.Lock())
                    async with lock:
                        wait = interval - (loop.time() - last_request.get(host, 0.0))
                        if wait > 0:
                            await asyncio.sleep(wait)
                        last_request[host] = loop.time()
                    await fetch_image(url, client)
                    results[store] += 1
                except Exception as exc:
                    errors.append((url, str(exc)[:140]))
                    # Do not keep hammering a store that explicitly rate-limits.
                    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in (403, 429):
                        print(f"{store}: stopped after HTTP {exc.response.status_code}", flush=True)
                        return
                finally:
                    completed += 1
                    queue.task_done()
                    if completed % 100 == 0 or completed == len(pending):
                        print(f"images: {completed}/{len(pending)} saved={sum(results.values())} "
                              f"failed={len(errors)}", flush=True)

        await asyncio.gather(*(worker() for _ in range(concurrency)))

    print(f"saved_by_store={dict(results)} failed={len(errors)}", flush=True)
    for url, error in errors[:20]:
        print(f"  FAILED {url}: {error}", flush=True)
    return len(errors)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stores", nargs="+", choices=QUERIES,
                        default=list(QUERIES))
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--interval", type=float, default=0.35,
                        help="Minimum seconds between requests to the same host")
    parser.add_argument("--limit", type=int, default=None,
                        help="Only fetch this many uncached images (for smoke tests)")
    args = parser.parse_args()
    if not 1 <= args.concurrency <= 12 or args.interval < 0.2:
        parser.error("concurrency must be 1..12 and interval at least 0.2 seconds")
    if args.limit is not None and args.limit < 1:
        parser.error("limit must be positive")
    raise SystemExit(int(asyncio.run(run(args.stores, args.concurrency,
                                         args.interval, args.limit)) > 0))


if __name__ == "__main__":
    main()
