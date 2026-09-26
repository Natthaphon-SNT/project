"""Retire iHaveCPU offers independently confirmed as HTTP 404/410.

No network requests are made here. Every supplied product ID must match the
expected iHaveCPU source ID before any row is changed. Dry-run by default.
"""

import argparse
import re
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from audit_product_links import retailer_url_is_valid


def parse_pairs(raw: str) -> list[tuple[str, int]]:
    pairs = []
    for token in raw.split(","):
        match = re.fullmatch(r"([A-Za-z0-9_-]+):(\d+)", token.strip())
        if not match:
            raise ValueError(f"Invalid product/source pair: {token!r}")
        pairs.append((match.group(1), int(match.group(2))))
    if not pairs or len(set(pid for pid, _ in pairs)) != len(pairs):
        raise ValueError("Supply at least one unique product ID")
    return pairs


def retire(db_path: Path, pairs: list[tuple[str, int]], apply: bool) -> int:
    with closing(sqlite3.connect(db_path, timeout=60)) as conn:
        rows = []
        for pid, source_id in pairs:
            row = conn.execute("""SELECT price_advice, price_jib, price_ihavecpu,
                url_ihavecpu, p_price FROM products WHERE product_id=?""", (pid,)).fetchone()
            if not row:
                raise ValueError(f"Unknown product ID: {pid}")
            url = row[3] or ""
            if row[2] == 0 and not url:
                print(f"ALREADY_RETIRED {pid}")
                continue
            if (row[2] <= 0 or not retailer_url_is_valid("ihavecpu", url)
                    or f"/product/{source_id}/" not in url):
                raise ValueError(f"Offer/source mismatch: {pid} expected {source_id}: {url}")
            print(f"CANDIDATE {pid} source={source_id} price={row[2]} url={url}")
            rows.append((pid, row))
        if not apply:
            print(f"DRY_RUN candidates={len(rows)}")
            return 0
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        for pid, row in rows:
            remaining = [int(price) for price in row[:2] if price and price > 0]
            cursor = conn.execute("""UPDATE products SET price_ihavecpu=0,
                url_ihavecpu='', p_price=?, updated_at=?
                WHERE product_id=? AND url_ihavecpu=? AND price_ihavecpu=?""",
                (min(remaining) if remaining else 0, now, pid, row[3], row[2]))
            if cursor.rowcount != 1:
                conn.rollback()
                raise RuntimeError(f"Concurrent offer change: {pid}")
        conn.commit()
    print(f"RETIRED {len(rows)}")
    return len(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(__file__).with_name("shop.db"))
    parser.add_argument("--pairs", required=True, help="product_id:source_id,...")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    retire(args.db, parse_pairs(args.pairs), args.apply)


if __name__ == "__main__":
    main()
