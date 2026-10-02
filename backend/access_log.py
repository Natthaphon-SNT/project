"""Best-effort security access logs; no SQLite writes or request content capture."""

import asyncio
from contextlib import asynccontextmanager
import hmac
from ipaddress import ip_address, ip_network
import os
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
import httpx


LOG_PREFIXES = (
    "/admin", "/api/admin", "/login", "/api/login", "/register", "/api/register",
    "/auth", "/api/auth", "/api/profile", "/api/ai/settings", "/api/ai/sessions",
    "/api/ai/recommend", "/api/spec-history", "/api/scrape",
)
ADMIN_WRITE_PREFIXES = ("/api/products", "/api/promotions")
MAX_PENDING_LOGS = 256


def should_log(method: str, path: str) -> bool:
    if path.startswith(LOG_PREFIXES):
        return True
    return method in {"POST", "PUT", "PATCH", "DELETE"} and any(
        path == prefix or path.startswith(prefix + "/") for prefix in ADMIN_WRITE_PREFIXES
    )


def _valid_ip(value: str | None) -> str | None:
    try:
        return str(ip_address(value.strip())) if value else None
    except ValueError:
        return None


def _trusted_proxy(request: Request) -> bool:
    # Preserve the socket peer with Uvicorn --no-proxy-headers, so forwarded
    # headers cannot influence the decision to trust a proxy.
    peer = _valid_ip(request.client.host if request.client else None)
    if not peer:
        return False
    for cidr in os.getenv("ACCESS_LOG_TRUSTED_PROXY_CIDRS", "").split(","):
        try:
            network = ip_network(cidr.strip())
            if network.prefixlen and ip_address(peer) in network:
                return True
        except ValueError:
            continue
    return False


def _vercel_proxy(request: Request) -> bool:
    secret = os.getenv("ACCESS_LOG_PROXY_SECRET", "")
    supplied = request.headers.get("x-access-log-proxy-secret", "")
    return (_trusted_proxy(request) and len(secret) >= 32
            and hmac.compare_digest(secret.encode(), supplied.encode()))


def _client_ip(request: Request) -> str | None:
    if _trusted_proxy(request):
        if _vercel_proxy(request):
            # Railway replaces XFF/X-Real-IP with Vercel's IP, while this
            # Vercel-managed client header survives the external rewrite.
            visitor = _valid_ip(request.headers.get("x-vercel-forwarded-for", "").split(",", 1)[0])
            if visitor:
                return visitor
        # The configured Railway edge replaces these even on direct requests.
        # Vercel/Cloudflare metadata alone never establishes proxy identity.
        for name in ("x-forwarded-for", "x-real-ip"):
            candidate = _valid_ip(request.headers.get(name, "").split(",", 1)[0])
            if candidate:
                return candidate
    return _valid_ip(request.client.host if request.client else None)


def _client_country(request: Request) -> str | None:
    if not _vercel_proxy(request):
        return None
    country = request.headers.get("x-vercel-ip-country", "").strip().upper()
    return country if len(country) == 2 and country.isascii() and country.isalpha() else None


def log_payload(request: Request, status: int) -> dict:
    user_id = getattr(request.state, "user_id", None)
    return {
        "method": request.method,
        "path": request.url.path[:300],
        "status": status,
        "ip": _client_ip(request),
        "country": _client_country(request),
        "user_agent": request.headers.get("user-agent", "")[:300],
        "user_id": str(user_id) if user_id is not None else None,
    }


class AccessLogger:
    def __init__(self):
        self.client: httpx.AsyncClient | None = None
        self.url = ""
        self.pending: set[asyncio.Task] = set()

    def start(self):
        try:
            base = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
            key = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
            parsed = urlsplit(base)
            if (not key or parsed.scheme != "https" or not parsed.hostname
                    or parsed.username or parsed.password or parsed.query or parsed.fragment
                    or parsed.path):
                return
            self.client = httpx.AsyncClient(timeout=5.0, follow_redirects=False, headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            })
            self.url = base + "/rest/v1/access_logs"
        except Exception:
            self.client = None

    async def send(self, payload: dict):
        try:
            if self.client is not None:
                response = await self.client.post(self.url, json=payload)
                response.raise_for_status()
        except Exception:
            # Never print Supabase errors/headers: they may contain credentials.
            pass

    def enqueue(self, request: Request, status: int):
        try:
            if self.client is None or len(self.pending) >= MAX_PENDING_LOGS:
                return
            task = asyncio.create_task(self.send(log_payload(request, status)))
            self.pending.add(task)
            task.add_done_callback(self.pending.discard)
        except Exception:
            pass

    async def close(self):
        try:
            if self.pending:
                _, unfinished = await asyncio.wait(tuple(self.pending), timeout=5.0)
                for task in unfinished:
                    task.cancel()
                if unfinished:
                    await asyncio.gather(*unfinished, return_exceptions=True)
            if self.client is not None:
                await self.client.aclose()
        except Exception:
            pass
        finally:
            self.client = None
            self.pending.clear()


def install_access_logging(app: FastAPI):
    if getattr(app.state, "access_logger", None) is not None:
        return
    logger = AccessLogger()
    app.state.access_logger = logger
    previous_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application):
        async with previous_lifespan(application) as state:
            logger.start()
            try:
                yield state
            finally:
                await logger.close()

    app.router.lifespan_context = lifespan

    @app.middleware("http")
    async def access_logging(request: Request, call_next):
        if not should_log(request.method, request.url.path):
            return await call_next(request)
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            # No await here: the API response does not wait for Supabase.
            logger.enqueue(request, status)
