"""Best-effort security access logs; no SQLite writes or request content capture."""

import asyncio
from contextlib import asynccontextmanager
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


def log_payload(request: Request, status: int) -> dict:
    forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
    ip = forwarded or request.headers.get("x-real-ip", "").strip()
    if not ip:
        ip = request.client.host if request.client else None
    user_id = getattr(request.state, "user_id", None)
    return {
        "method": request.method,
        "path": request.url.path[:300],
        "status": status,
        "ip": ip,
        "country": request.headers.get("x-vercel-ip-country") or None,
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
