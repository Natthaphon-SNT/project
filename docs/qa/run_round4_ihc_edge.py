"""Verify the single round-3 iHaveCPU description edge without logging HTML."""

from __future__ import annotations

import asyncio
from datetime import datetime
import json
from pathlib import Path
import sys

import httpx


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "round4"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / "backend"))

import full_scraper as fs


PRODUCT_ID = 44014
PRODUCT_NAME = "SILICONE (ซิลิโคน) ARCTIC THERMAL MX-7 2G"
URL = fs.ihc_product_url(PRODUCT_ID, PRODUCT_NAME)


async def main() -> int:
    async with httpx.AsyncClient(
        headers={"User-Agent": fs.UA}, follow_redirects=True,
        timeout=httpx.Timeout(30, connect=15),
    ) as client:
        response = await fs.request_with_retry(client, "GET", URL)
    product = fs.ihc_detail_product(response.text) if response.status_code == 200 else {}
    raw_description = fs._plain_html(product.get("description_th") or "")
    metadata = fs._plain_html(product.get("meta_description_th") or "")
    normalized = fs.ihc_product_description(product)
    result = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "product_id": PRODUCT_ID,
        "url": URL,
        "http_status": response.status_code,
        "root_cause": "description_th is image-only after HTML normalization",
        "raw_description_text_length": len(raw_description),
        "meta_description_text_length": len(metadata),
        "normalized_description_length": len(normalized),
        "source_field_used": "meta_description_th",
        "status": "Pass" if (
            response.status_code == 200 and not raw_description and
            len(metadata) >= 30 and len(normalized) >= 30
        ) else "Fail",
    }
    path = OUT / "B5-ihavecpu-edge-live.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"result": str(path), "status": result["status"]}))
    return 0 if result["status"] == "Pass" else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
