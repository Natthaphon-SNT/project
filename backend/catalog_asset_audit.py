"""Audit displayed catalogue rows for usable images and product details."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import sqlite3

import full_scraper as core
from product_image_cache import cached_image


ACTIVE = "(price_advice > 0 OR price_jib > 0 OR price_ihavecpu > 0)"
GENERIC_DESCRIPTION_MARKERS = (
    "ihavecpu เพื่อนรู้ใจ สายไอที จำหน่ายคอมประกอบ",
    "จำหน่ายคอมประกอบ คอมพิวเตอร์สำเร็จรูป อุปกรณ์คอมพิวเตอร์",
)


def usable_description(value: str | None) -> bool:
    text = " ".join((value or "").split()).strip()
    lowered = text.lower()
    return len(text) >= 30 and not any(
        marker in lowered for marker in GENERIC_DESCRIPTION_MARKERS
    )


def image_state(url: str | None) -> tuple[bool, bool]:
    value = (url or "").strip()
    if not value or core.is_placeholder_image_url(value):
        return False, False
    try:
        return True, bool(cached_image(value))
    except ValueError:
        return False, False


def audit() -> tuple[dict, list[dict], list[dict], list[dict]]:
    connection = sqlite3.connect(core.DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        total = connection.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        rows = connection.execute(f"""
            SELECT product_id, p_name, category, img_url, p_description,
                   price_advice, price_jib, price_ihavecpu,
                   url_advice, url_jib, url_ihavecpu
            FROM products
            WHERE {ACTIVE}
            ORDER BY category, p_name
        """).fetchall()
    finally:
        connection.close()

    missing_images: list[dict] = []
    uncached_images: list[dict] = []
    missing_details: list[dict] = []
    image_urls = set()
    cached_urls = set()
    pcset = Counter()
    for row in rows:
        item = dict(row)
        usable_image, locally_cached = image_state(row["img_url"])
        if usable_image:
            image_urls.add(row["img_url"])
            if locally_cached:
                cached_urls.add(row["img_url"])
        else:
            missing_images.append(item)
        if usable_image and not locally_cached:
            uncached_images.append(item)
        if not usable_description(row["p_description"]):
            missing_details.append(item)

        if row["category"] == "PC Set":
            pcset["active"] += 1
            pcset["usable_image"] += int(usable_image)
            pcset["cached_image"] += int(locally_cached)
            pcset["usable_details"] += int(usable_description(row["p_description"]))

    summary = {
        "all_rows": total,
        "active_rows": len(rows),
        "active_rows_with_usable_image": len(rows) - len(missing_images),
        "active_rows_with_cached_image": (
            len(rows) - len(missing_images) - len(uncached_images)
        ),
        "active_rows_with_usable_details": len(rows) - len(missing_details),
        "distinct_active_image_urls": len(image_urls),
        "distinct_active_images_cached": len(cached_urls),
        "pc_sets": dict(pcset),
        "missing_image_rows": len(missing_images),
        "uncached_image_rows": len(uncached_images),
        "missing_detail_rows": len(missing_details),
    }
    return summary, missing_images, uncached_images, missing_details


def compact(row: dict) -> dict:
    return {
        "product_id": row["product_id"],
        "name": row["p_name"],
        "category": row["category"],
        "prices": {
            "advice": row["price_advice"],
            "jib": row["price_jib"],
            "ihavecpu": row["price_ihavecpu"],
        },
        "source_urls": [
            value for value in (
                row["url_advice"], row["url_jib"], row["url_ihavecpu"]
            ) if (value or "").strip()
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=30)
    parser.add_argument("--strict", action="store_true",
                        help="Exit non-zero when any active row is incomplete")
    args = parser.parse_args()
    summary, missing_images, uncached_images, missing_details = audit()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if missing_images:
        print("\nMISSING_IMAGES")
        print(json.dumps([compact(row) for row in missing_images[:args.limit]],
                         ensure_ascii=False, indent=2))
    if uncached_images:
        print("\nUNCACHED_IMAGES")
        print(json.dumps([compact(row) for row in uncached_images[:args.limit]],
                         ensure_ascii=False, indent=2))
    if missing_details:
        print("\nMISSING_DETAILS")
        print(json.dumps([compact(row) for row in missing_details[:args.limit]],
                         ensure_ascii=False, indent=2))
    if args.strict and (missing_images or uncached_images or missing_details):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
