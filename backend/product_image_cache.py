"""Validated, on-disk cache for retailer product images.

The catalogue stores the retailer's original image URL. This module keeps a
local copy of each image so a grid of products does not repeatedly hit store
CDNs (or a per-client API rate limit).
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import httpx


CACHE_DIR = Path(__file__).resolve().parent / "product_image_cache"
MAX_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_HOSTS = (
    "jib.co.th", "ihavecpu.com", "advice.co.th",
    "ihcupload-bkk.s3.ap-southeast-7.amazonaws.com",
)


def validated_host(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if (parsed.scheme != "https" or parsed.username or parsed.password
            or parsed.port or not host
            or not any(host == allowed or host.endswith("." + allowed)
                       for allowed in ALLOWED_HOSTS)):
        raise ValueError("Unsupported product image URL")
    return host


def cache_path(url: str) -> Path:
    validated_host(url)
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return CACHE_DIR / digest[:2] / digest


def image_mime(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    if len(data) >= 12 and data[4:8] == b"ftyp" and data[8:12] in (b"avif", b"avis"):
        return "image/avif"
    return None


def cached_image(url: str) -> tuple[Path, str] | None:
    path = cache_path(url)
    if not path.is_file():
        return None
    with path.open("rb") as image:
        mime = image_mime(image.read(16))
    if not mime:
        return None
    return path, mime


async def fetch_image(url: str, client: httpx.AsyncClient) -> tuple[Path, str]:
    existing = cached_image(url)
    if existing:
        return existing
    host = validated_host(url)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36",
        "Referer": "https://www.advice.co.th/" if host.endswith("advice.co.th")
                   else "https://www.jib.co.th/" if host.endswith("jib.co.th")
                   else "https://ihavecpu.com/",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
    }
    chunks: list[bytes] = []
    size = 0
    # No redirects: a retailer-controlled redirect must not escape the host
    # allowlist and turn this unauthenticated endpoint into an open proxy.
    async with client.stream("GET", url, headers=headers, follow_redirects=False) as response:
        response.raise_for_status()
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > MAX_IMAGE_BYTES:
                raise ValueError("Product image exceeds size limit")
            chunks.append(chunk)
    data = b"".join(chunks)
    mime = image_mime(data[:16])
    if not mime:
        raise ValueError("Retailer returned non-image content")
    path = cache_path(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return path, mime
