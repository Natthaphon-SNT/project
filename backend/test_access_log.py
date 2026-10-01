"""Access logging tests with synthetic requests and mocked Supabase only."""

import asyncio
import contextlib
from contextlib import asynccontextmanager
import json
import io
import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI
import httpx
from starlette.requests import Request

import access_log
import verify_access_logs


def request(path="/api/login", headers=(), client=("127.0.0.1", 5000)):
    return Request({
        "type": "http", "method": "POST", "path": path,
        "query_string": b"password=never-record-this", "headers": [
            (name.lower().encode(), value.encode()) for name, value in headers
        ], "client": client, "scheme": "http", "server": ("test", 80),
    })


class PayloadTests(unittest.TestCase):
    def test_ip_precedence_limits_and_allowlist(self):
        req = request("/api/admin/" + "a" * 400, headers=[
            ("x-forwarded-for", " 203.0.113.1, 192.0.2.2"),
            ("x-real-ip", "192.0.2.3"), ("user-agent", "u" * 500),
            ("x-vercel-ip-country", "TH"), ("authorization", "secret"),
            ("cookie", "secret"),
        ])
        req.state.user_id = "alice"
        payload = access_log.log_payload(req, 403)
        self.assertEqual(set(payload), {
            "method", "path", "status", "ip", "country", "user_agent", "user_id",
        })
        self.assertEqual(payload["ip"], "203.0.113.1")
        self.assertEqual(payload["country"], "TH")
        self.assertEqual(payload["user_id"], "alice")
        self.assertEqual(len(payload["path"]), 300)
        self.assertEqual(len(payload["user_agent"]), 300)
        self.assertNotIn("never-record-this", json.dumps(payload))
        self.assertNotIn("secret", json.dumps(payload))

    def test_ip_fallbacks_and_null_values(self):
        req = request(headers=[("x-forwarded-for", " , 192.0.2.2"),
                               ("x-real-ip", "198.51.100.2")])
        self.assertEqual(access_log.log_payload(req, 401)["ip"], "198.51.100.2")
        payload = access_log.log_payload(request(), 401)
        self.assertEqual(payload["ip"], "127.0.0.1")
        self.assertIsNone(payload["country"])
        self.assertIsNone(payload["user_id"])
        self.assertIsNone(access_log.log_payload(request(client=None), 401)["ip"])

    def test_route_selection(self):
        for prefix in access_log.LOG_PREFIXES:
            self.assertTrue(access_log.should_log("GET", prefix + "/test"), prefix)
        for path in ("/products", "/api/products", "/api/products/1", "/health", "/uploads/profile/a"):
            self.assertFalse(access_log.should_log("GET", path), path)
        self.assertTrue(access_log.should_log("DELETE", "/api/products/1"))
        self.assertTrue(access_log.should_log("POST", "/api/promotions"))
        self.assertFalse(access_log.should_log("POST", "/api/products-unrelated"))


class LiveVerifierTests(unittest.TestCase):
    def test_live_verifier_checks_keys_denial_and_tagged_backend_rows(self):
        rows = []
        def handler(req):
            if req.url.host == "127.0.0.1":
                self.assertNotIn("apikey", req.headers)
                self.assertNotIn("authorization", req.headers)
                if req.url.path in ("/api/login", "/api/admin/users"):
                    rows.append({"path": req.url.path, "status": 401,
                                 "ip": "127.0.0.1", "user_agent": req.headers["user-agent"]})
                    return httpx.Response(401)
                return httpx.Response(200)
            if req.url.path == "/auth/v1/settings":
                return httpx.Response(200, json={})
            if req.headers["apikey"] == "synthetic-anon":
                return httpx.Response(401 if req.method == "GET" else 403)
            if "user_agent" in req.url.params:
                return httpx.Response(200, json=rows)
            return httpx.Response(200, json=[])
        with httpx.Client(transport=httpx.MockTransport(handler)) as client, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            verify_access_logs.verify(client, "https://logs.example.test",
                "synthetic-service", "synthetic-anon", "http://127.0.0.1:3000")
        self.assertIn("real Supabase rows", output.getvalue())
        self.assertNotIn("synthetic-service", output.getvalue())
        self.assertNotIn("synthetic-anon", output.getvalue())

    def test_invalid_anon_key_is_not_mistaken_for_a_secure_table(self):
        paths = []
        def handler(req):
            paths.append(req.url.path)
            return httpx.Response(401)
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaisesRegex(RuntimeError, "no access-control conclusion"):
                verify_access_logs.verify(client, "https://logs.example.test",
                    "synthetic-service", "invalid-anon")
        self.assertEqual(paths, ["/auth/v1/settings"])

    def test_read_or_write_access_for_anon_fails_verification(self):
        def handler(req):
            return httpx.Response(200, json=[])
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            with self.assertRaisesRegex(RuntimeError, "Anon access is not denied"):
                verify_access_logs.verify(client, "https://logs.example.test",
                    "synthetic-service", "synthetic-anon")


class AsyncLoggingTests(unittest.IsolatedAsyncioTestCase):
    def configured_logger(self, handler):
        logger = access_log.AccessLogger()
        original = httpx.AsyncClient
        with patch.dict(os.environ, {"SUPABASE_URL": "https://logs.example.test",
                                     "SUPABASE_SERVICE_KEY": "synthetic-service-key"}), \
             patch.object(access_log.httpx, "AsyncClient", side_effect=lambda **kwargs:
                          original(transport=httpx.MockTransport(handler), **kwargs)):
            logger.start()
        return logger

    async def test_shared_client_headers_task_references_and_cleanup(self):
        received = []
        async def handler(req):
            received.append(req)
            return httpx.Response(201)
        logger = self.configured_logger(handler)
        client = logger.client
        self.assertEqual(client.timeout.read, 5.0)
        logger.enqueue(request(), 401)
        logger.enqueue(request(), 403)
        self.assertEqual(len(logger.pending), 2)
        await asyncio.gather(*tuple(logger.pending))
        await asyncio.sleep(0)
        self.assertFalse(logger.pending)
        self.assertIs(logger.client, client)
        self.assertEqual(len(received), 2)
        for req in received:
            self.assertEqual(str(req.url), "https://logs.example.test/rest/v1/access_logs")
            self.assertEqual(req.headers["apikey"], "synthetic-service-key")
            self.assertEqual(req.headers["authorization"], "Bearer synthetic-service-key")
            self.assertEqual(req.headers["prefer"], "return=minimal")
            self.assertEqual(req.headers["content-type"], "application/json")
        await logger.close()
        self.assertTrue(client.is_closed)

    async def test_missing_invalid_or_insecure_environment_disables_logging(self):
        for url, key in (("", ""), ("https://logs.example.test", ""), ("wrong", "key"),
                         ("http://logs.example.test", "key"),
                         ("https://user:pass@logs.example.test", "key")):
            with self.subTest(url=url), patch.dict(os.environ, {
                "SUPABASE_URL": url, "SUPABASE_SERVICE_KEY": key,
            }):
                logger = access_log.AccessLogger()
                logger.start()
                logger.enqueue(request(), 401)
                self.assertIsNone(logger.client)
                self.assertFalse(logger.pending)
                await logger.close()

    async def test_failure_timeout_and_http_errors_are_swallowed(self):
        for failure in (httpx.ConnectError("down"), httpx.ReadTimeout("timeout"), None):
            async def handler(req):
                if failure:
                    raise failure
                return httpx.Response(503)
            logger = self.configured_logger(handler)
            logger.enqueue(request(), 401)
            await asyncio.gather(*tuple(logger.pending))
            await logger.close()

    async def test_response_does_not_wait_for_supabase_and_preserves_lifespan(self):
        sending = asyncio.Event()
        release = asyncio.Event()
        received = []
        lifecycle = []
        async def handler(req):
            sending.set()
            await release.wait()
            received.append(req)
            return httpx.Response(201)
        @asynccontextmanager
        async def original_lifespan(app):
            lifecycle.append("start")
            yield
            lifecycle.append("stop")
        app = FastAPI(lifespan=original_lifespan)
        @app.get("/api/admin/test")
        async def endpoint():
            return {"ok": True}
        access_log.install_access_logging(app)
        access_log.install_access_logging(app)
        original = httpx.AsyncClient
        with patch.dict(os.environ, {"SUPABASE_URL": "https://logs.example.test",
                                     "SUPABASE_SERVICE_KEY": "synthetic-service-key"}), \
             patch.object(access_log.httpx, "AsyncClient", side_effect=lambda **kwargs:
                          original(transport=httpx.MockTransport(handler), **kwargs)):
            async with app.router.lifespan_context(app):
                async with original(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                    response = await asyncio.wait_for(client.get("/api/admin/test"), timeout=1.0)
                    self.assertEqual(response.status_code, 200)
                    await asyncio.wait_for(sending.wait(), timeout=1.0)
                    self.assertFalse(received)
                    release.set()
        self.assertEqual(len(received), 1)
        self.assertEqual(lifecycle, ["start", "stop"])

    async def test_unhandled_failure_records_500_and_is_not_hidden(self):
        received = []
        async def handler(req):
            received.append(json.loads(req.content))
            return httpx.Response(201)
        app = FastAPI()
        @app.get("/api/admin/failure")
        async def endpoint():
            raise RuntimeError("application failure")
        access_log.install_access_logging(app)
        logger = self.configured_logger(handler)
        app.state.access_logger.client = logger.client
        app.state.access_logger.url = logger.url
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            with self.assertRaises(RuntimeError):
                await client.get("/api/admin/failure")
        await app.state.access_logger.close()
        self.assertEqual(received[0]["status"], 500)

    async def test_task_backlog_is_bounded(self):
        release = asyncio.Event()
        async def handler(req):
            await release.wait()
            return httpx.Response(201)
        logger = self.configured_logger(handler)
        for _ in range(access_log.MAX_PENDING_LOGS + 5):
            logger.enqueue(request(), 401)
        self.assertEqual(len(logger.pending), access_log.MAX_PENDING_LOGS)
        release.set()
        await logger.close()
        self.assertFalse(logger.pending)


if __name__ == "__main__":
    unittest.main()
