"""SSRF-guarded retailer image cache using a private S3-compatible bucket.

Approved source URLs map deterministically to object keys. The stable public
URL is /api/cached-image/<sha256>; the API redirects it to a short-lived signed
bucket URL. No bucket credentials or local-disk cache are needed in production.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import httpx

logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 8 * 1024 * 1024
ALLOWED_HOSTS = (
    "jib.co.th", "ihavecpu.com", "advice.co.th",
    "ihcupload-bkk.s3.ap-southeast-7.amazonaws.com",
)
CACHE_DIR = Path(__file__).resolve().parent / "product_image_cache"


def validated_host(url: str) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if (parsed.scheme != "https" or parsed.username or parsed.password
            or parsed.port or not host
            or not any(host == allowed or host.endswith("." + allowed)
                       for allowed in ALLOWED_HOSTS)):
        raise ValueError("Unsupported product image URL")
    return host


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


def storage_config() -> dict | None:
    names = {
        "endpoint": "IMAGE_S3_ENDPOINT",
        "bucket": "IMAGE_S3_BUCKET",
        "access_key": "IMAGE_S3_ACCESS_KEY_ID",
        "secret_key": "IMAGE_S3_SECRET_ACCESS_KEY",
    }
    cfg = {key: os.getenv(name, "").strip() for key, name in names.items()}
    if not all(cfg.values()):
        return None
    if not cfg["endpoint"].startswith("https://"):
        raise ValueError("IMAGE_S3_ENDPOINT must be HTTPS")
    cfg["region"] = os.getenv("IMAGE_S3_REGION", "auto").strip() or "auto"
    cfg["url_style"] = os.getenv("IMAGE_S3_URL_STYLE", "virtual").strip()
    if cfg["url_style"] not in ("virtual", "path"):
        raise ValueError("IMAGE_S3_URL_STYLE must be virtual or path")
    return cfg


def _s3_client():
    cfg = storage_config()
    if cfg is None:
        return None, None
    import boto3
    from botocore.config import Config
    client = boto3.client(
        "s3",
        endpoint_url=cfg["endpoint"],
        aws_access_key_id=cfg["access_key"],
        aws_secret_access_key=cfg["secret_key"],
        region_name=cfg["region"],
        config=Config(signature_version="s3v4", s3={"addressing_style": cfg["url_style"]}),
    )
    return client, cfg


def _digest(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _object_key(url: str) -> str:
    digest = _digest(url)
    return f"images/{digest[:2]}/{digest}"


def _stable_url(url: str) -> str:
    return f"/api/cached-image/{_digest(url)}"


def get_cached_url(url: str) -> str | None:
    """Return a stable same-origin URL if an approved source was uploaded."""
    validated_host(url)
    client, cfg = _s3_client()
    if client is None:
        return None
    try:
        client.head_object(Bucket=cfg["bucket"], Key=_object_key(url))
    except Exception as exc:
        code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
        if str(code) in ("404", "NoSuchKey", "NotFound"):
            return None
        raise
    return _stable_url(url)


def existing_object_keys() -> set[str]:
    """List cached keys once so bulk prefetch does not issue one HEAD per image."""
    client, cfg = _s3_client()
    if client is None:
        raise RuntimeError("Image bucket is not configured")
    keys: set[str] = set()
    pages = client.get_paginator("list_objects_v2").paginate(
        Bucket=cfg["bucket"], Prefix="images/"
    )
    for page in pages:
        keys.update(item["Key"] for item in page.get("Contents", []))
    return keys


def presigned_image_url(digest: str) -> str:
    """Issue a short-lived URL for a cached image; the stable route never expires."""
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("Invalid cached image ID")
    client, cfg = _s3_client()
    if client is None:
        raise RuntimeError("Image bucket is not configured")
    key = f"images/{digest[:2]}/{digest}"
    client.head_object(Bucket=cfg["bucket"], Key=key)
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": cfg["bucket"], "Key": key},
        ExpiresIn=3600,
    )


async def fetch_image_bytes(url: str, http_client: httpx.AsyncClient) -> tuple[bytes, str]:
    """Download a validated retailer image without following redirects."""
    host = validated_host(url)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36"
        ),
        "Referer": (
            "https://www.advice.co.th/" if host.endswith("advice.co.th")
            else "https://www.jib.co.th/" if host.endswith("jib.co.th")
            else "https://ihavecpu.com/"
        ),
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
    }
    chunks: list[bytes] = []
    size = 0
    async with http_client.stream(
        "GET", url, headers=headers, follow_redirects=False
    ) as response:
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
    return data, mime


async def fetch_and_upload(url: str, http_client: httpx.AsyncClient) -> tuple[str, str]:
    """Fetch once, upload to the private bucket, and return the stable API URL."""
    validated_host(url)
    client, cfg = _s3_client()
    if client is None:
        raise RuntimeError("Image bucket is not configured")
    data, mime = await fetch_image_bytes(url, http_client)
    await asyncio.to_thread(
        client.put_object,
        Bucket=cfg["bucket"],
        Key=_object_key(url),
        Body=data,
        ContentType=mime,
        CacheControl="public, max-age=31536000, immutable",
    )
    return _stable_url(url), mime


# Legacy local-cache helpers are retained only for existing development tests.
# The production proxy and prefetch job never call fetch_image().
def cache_path(url: str) -> Path:
    validated_host(url)
    digest = _digest(url)
    return CACHE_DIR / digest[:2] / digest


def cached_image(url: str) -> tuple[Path, str] | None:
    path = cache_path(url)
    if not path.is_file():
        return None
    with path.open("rb") as f:
        mime = image_mime(f.read(16))
    return (path, mime) if mime else None


async def fetch_image(url: str, client: httpx.AsyncClient) -> tuple[Path, str]:
    existing = cached_image(url)
    if existing:
        return existing
    data, mime = await fetch_image_bytes(url, client)
    path = cache_path(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
    return path, mime
