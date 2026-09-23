import asyncio
import contextlib
import importlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import httpx
import sqlite3

from fastapi.testclient import TestClient


class QaFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_cwd = os.getcwd()
        cls.temp_dir = tempfile.TemporaryDirectory(
            dir=str(Path(__file__).resolve().parent)
        )
        os.chdir(cls.temp_dir.name)
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        os.environ.setdefault(
            "JWT_SECRET", "qa-fixes-jwt-secret-012345678901234567890123"
        )
        # Other test modules also import shop_api against their own temporary
        # databases.  Discovery runs in one interpreter, so force this suite
        # to construct a fresh engine after changing into its isolated cwd.
        sys.modules.pop("shop_api", None)
        with contextlib.redirect_stdout(io.StringIO()):
            cls.api = importlib.import_module("shop_api")
        cls.api.Base.metadata.create_all(cls.api.engine)
        cls.client = TestClient(cls.api.app)
        with cls.api.SessionLocal() as db:
            db.add_all([
                cls.api.User(
                    uid="qa-alice",
                    u_name="qa_alice",
                    u_email="qa-alice@example.com",
                    u_password="unused",
                    u_role="customer",
                ),
                cls.api.User(
                    uid="qa-bob",
                    u_name="qa_bob",
                    u_email="qa-bob@example.com",
                    u_password="unused",
                    u_role="customer",
                ),
                cls.api.User(
                    uid="qa-admin",
                    u_name="qa_admin",
                    u_email="qa-admin@example.com",
                    u_password="unused",
                    u_role="admin",
                ),
            ])
            db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.api.engine.dispose()
        os.chdir(cls.original_cwd)
        cls.temp_dir.cleanup()

    @classmethod
    def auth(cls, uid):
        token = cls.api.create_token({"uid": uid})
        return {"Authorization": f"Bearer {token}"}

    def test_jwt_rotation_rejects_old_token_and_accepts_new_token(self):
        old_secret = "old-qa-jwt-secret-012345678901234567890123"
        new_secret = "new-qa-jwt-secret-012345678901234567890123"
        with patch.object(self.api, "SECRET_KEY", old_secret):
            old_token = self.api.create_token({"uid": "qa-alice"})
        with patch.object(self.api, "SECRET_KEY", new_secret):
            with self.assertRaises(self.api.jwt.InvalidSignatureError):
                self.api.decode_token(old_token)
            new_token = self.api.create_token({"uid": "qa-alice"})
            self.assertEqual(self.api.decode_token(new_token)["uid"], "qa-alice")

    def test_jwt_secret_must_be_long_and_separate_from_provider_keys(self):
        with patch.dict(os.environ, {"JWT_SECRET": "too-short"}, clear=True):
            with self.assertRaises(RuntimeError):
                self.api.load_jwt_secret()
        reused = "same-secret-value-012345678901234567890123"
        with patch.dict(
            os.environ,
            {"JWT_SECRET": reused, "GOOGLE_API_KEY": reused},
            clear=True,
        ):
            with self.assertRaises(RuntimeError):
                self.api.load_jwt_secret()

    def test_routes_are_unique_and_order_api_is_retired(self):
        routes = [
            (method, route.path)
            for route in self.api.app.routes
            for method in getattr(route, "methods", set())
        ]
        self.assertEqual(len(routes), len(set(routes)))
        self.assertFalse(any(path.startswith("/api/orders") for _, path in routes))
        self.assertFalse(any(path.endswith("/orders") for _, path in routes))
        self.assertEqual(self.client.get("/api/orders/1").status_code, 404)
        self.assertEqual(self.client.post("/api/orders", json={}).status_code, 404)

    def test_spec_history_requires_auth_and_enforces_owner(self):
        self.assertEqual(self.client.get("/api/spec-history").status_code, 401)
        self.assertEqual(
            self.client.post(
                "/api/spec-history",
                json={"uid": "qa-bob", "title": "forged", "result_data": {}},
            ).status_code,
            401,
        )

        created = self.client.post(
            "/api/spec-history",
            headers=self.auth("qa-alice"),
            json={"uid": "qa-bob", "title": "owner test", "result_data": {}},
        )
        self.assertEqual(created.status_code, 200)
        item = created.json()["data"]
        self.assertEqual(item["uid"], "qa-alice")

        bob_response = self.client.get(
            "/api/spec-history?uid=qa-alice", headers=self.auth("qa-bob")
        )
        self.assertEqual(bob_response.status_code, 403)
        self.assertEqual(
            self.client.delete(
                f"/api/spec-history/{item['id']}", headers=self.auth("qa-bob")
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.delete(
                f"/api/spec-history/{item['id']}", headers=self.auth("qa-alice")
            ).status_code,
            200,
        )

    def test_compatibility_payload_is_validated_before_business_logic(self):
        for part in (
            {"category": "CPU", "name": 123},
            {"category": "CPU", "name": "Ryzen 5", "price": {"amount": 1000}},
        ):
            response = self.client.post(
                "/api/compatibility/check-parts", json={"parts": [part]}
            )
            self.assertEqual(response.status_code, 422)

    def test_unmatched_ai_products_are_removed_and_reported(self):
        rec = importlib.import_module("recommender")
        candidates = [{
            "product_id": "real-cpu",
            "category": "CPU",
            "name": "Real CPU",
            "price": 2500,
            "prices": {"advice": 2500, "jib": 0, "ihavecpu": 0},
            "urls": {"advice": "https://example.com/real-cpu"},
            "url": "https://example.com/real-cpu",
            "specs": "",
        }]
        result = rec.build_final_result(
            {
                "parts": [
                    {"type": "CPU", "product_id": "real-cpu", "name": "Real CPU"},
                    {"type": "GPU", "product_id": "invented", "name": "Imaginary GPU"},
                ]
            },
            candidates,
            10000,
            "gaming",
        )
        self.assertEqual([part["product_id"] for part in result["parts"]], ["real-cpu"])
        self.assertTrue(all(part["matched_real_product"] for part in result["parts"]))
        self.assertIn("ไม่พบสินค้าที่ตรงในฐานข้อมูลสำหรับ GPU", result["warnings"])
        self.assertNotIn("(ราคาจริงจากฐานข้อมูล)", result["totalBudget"])
        self.assertEqual(result["_meta"]["parts_rejected_not_in_db"], 1)

    def test_last_admin_cannot_be_demoted_but_one_of_two_can(self):
        response = self.client.put(
            "/api/admin/users/qa-admin/role",
            headers=self.auth("qa-admin"),
            json={"role": "customer"},
        )
        self.assertEqual(response.status_code, 409)

        with self.api.SessionLocal() as db:
            db.add(self.api.User(
                uid="qa-admin-2",
                u_name="qa_admin_2",
                u_email="qa-admin-2@example.com",
                u_password="unused",
                u_role="admin",
            ))
            db.commit()
        response = self.client.put(
            "/api/admin/users/qa-admin/role",
            headers=self.auth("qa-admin-2"),
            json={"role": "customer"},
        )
        self.assertEqual(response.status_code, 200)

    def test_registration_product_price_and_pagination_validation(self):
        invalid_email = self.client.post("/api/register", json={
            "uid": "qa-invalid-email",
            "u_name": "qa_invalid_email",
            "u_email": "not-an-email",
            "u_phone": "0800000000",
            "dob": "2000-01-01",
            "u_password": "QaPass123!",
            "confirm": "QaPass123!",
        })
        short_password = self.client.post("/api/register", json={
            "uid": "qa-short-password",
            "u_name": "qa_short_password",
            "u_email": "short-password@example.com",
            "u_phone": "0800000000",
            "dob": "2000-01-01",
            "u_password": "x",
            "confirm": "x",
        })
        self.assertEqual(invalid_email.status_code, 422)
        self.assertEqual(short_password.status_code, 422)

        with self.api.SessionLocal() as db:
            admin = db.query(self.api.User).filter(self.api.User.uid == "qa-product-admin").first()
            if not admin:
                db.add(self.api.User(
                    uid="qa-product-admin",
                    u_name="qa_product_admin",
                    u_email="qa-product-admin@example.com",
                    u_password="unused",
                    u_role="admin",
                ))
            for index in range(3):
                db.add(self.api.Product(
                    product_id=f"qa-page-{index}",
                    p_name=f"qa-page-{index}",
                    p_price=1000 + index,
                    category="CPU",
                ))
            db.commit()

        negative = self.client.post(
            "/api/products",
            headers=self.auth("qa-product-admin"),
            json={"product_id": "qa-negative", "p_name": "QA negative", "p_price": -1},
        )
        self.assertEqual(negative.status_code, 422)
        page = self.client.get("/api/products?search=qa-page-&page=2&limit=1")
        self.assertEqual(page.status_code, 200)
        self.assertEqual(len(page.json()["data"]), 1)
        self.assertEqual(page.json()["pagination"]["total"], 3)
        self.assertEqual(self.client.get("/api/products?page=-1&limit=0").status_code, 422)
        self.assertEqual(self.client.get("/api/products?page=abc&limit=xyz").status_code, 422)

    def test_password_change_revokes_existing_tokens(self):
        with self.api.SessionLocal() as db:
            db.add(self.api.User(
                uid="qa-password",
                u_name="qa_password",
                u_email="qa-password@example.com",
                u_password=self.api.hash_password("old-pass"),
                u_role="customer",
            ))
            db.commit()
        old_headers = self.auth("qa-password")
        changed = self.client.put(
            "/api/profile/password",
            headers=old_headers,
            json={
                "current_password": "old-pass",
                "new_password": "new-pass",
                "confirm_password": "new-pass",
            },
        )
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(self.client.get("/api/profile", headers=old_headers).status_code, 401)
        login = self.client.post(
            "/api/login", json={"email": "qa-password@example.com", "password": "new-pass"}
        )
        self.assertEqual(login.status_code, 200)
        self.assertEqual(
            self.client.get(
                "/api/profile",
                headers={"Authorization": f"Bearer {login.json()['token']}"},
            ).status_code,
            200,
        )

    def test_budget_cooler_socket_and_llm_suggestion_guards(self):
        rec = importlib.import_module("recommender")
        ce = importlib.import_module("compat_engine")
        self.assertEqual(rec.detect_budget_thb("งบ 500 บาท"), 500)
        self.assertIsNone(rec.detect_budget_thb("ใช้ RTX 500 รุ่นใหม่"))

        cooler = ce.check_cooler_socket([
            {"category": "CPU", "socket": "AM5", "tdp": 65},
            {
                "category": "Cooler",
                "is_cpu_cooler": True,
                "rating_watt": 150,
                "sockets": ["LGA1700"],
            },
        ])
        self.assertEqual(cooler["severity"], "ERROR")
        budget = ce.check_budget([{"price": 27000}], 25000)
        self.assertFalse(budget["ok"])
        self.assertIn("เกินงบที่ตั้งไว้ 2,000 บาท", budget["detail"])

        with patch.object(
            rec,
            "llm_chat",
            new_callable=AsyncMock,
            return_value='["Everything is compatible", "ตรวจ BIOS version ก่อนใช้งาน"]',
        ):
            guarded = asyncio.run(rec.compat_check_hybrid(
                "CPU Ryzen 5 7500F AM5\nMainboard B760 LGA1700",
                api_key="test-key",
            ))
        self.assertEqual(guarded["overall"], "error")
        self.assertNotIn("Everything is compatible", guarded["suggestions"])
        self.assertIn("ตรวจ BIOS version ก่อนใช้งาน", guarded["suggestions"])

    def test_scraper_recalculates_lowest_price_after_every_update(self):
        scraper = importlib.import_module("scraper")
        scraper.CLEANED_CACHE.clear()
        conn = sqlite3.connect(":memory:")
        conn.executescript("""
            CREATE TABLE products (
                product_id TEXT PRIMARY KEY, p_name TEXT, p_description TEXT,
                p_price REAL, price_advice REAL, price_jib REAL, price_ihavecpu REAL,
                url_advice TEXT, url_jib TEXT, url_ihavecpu TEXT,
                desc_advice TEXT, desc_jib TEXT, desc_ihavecpu TEXT,
                p_stock INTEGER, cid TEXT, category TEXT, img_url TEXT, specs TEXT,
                created_at TEXT, updated_at TEXT
            );
            CREATE TABLE price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, product_id TEXT, store TEXT,
                price REAL, captured_at TEXT
            );
            INSERT INTO products VALUES (
                'qa-price', 'QA Price Product', '', 5000, 5000, 5100, 0,
                '', '', '', '', '', '', 1, 'c01', 'CPU', '', '', '', ''
            );
        """)
        scraper.upsert_product(conn.cursor(), {
            "store": "advice",
            "price": 5200,
            "name": "QA Price Product",
            "category": "CPU",
        })
        row = conn.execute(
            "SELECT p_price, price_advice FROM products WHERE product_id='qa-price'"
        ).fetchone()
        self.assertEqual(row, (5100, 5200))
        conn.close()

    def test_ai_provider_timeout_is_mapped_to_bad_gateway(self):
        rec = importlib.import_module("recommender")
        with patch.object(
            rec,
            "compare_specs",
            new_callable=AsyncMock,
            side_effect=httpx.ReadTimeout("provider timed out"),
        ):
            response = self.client.post("/api/ai/recommend", json={
                "prompt": "compare",
                "mode": "compare",
                "spec1": "A",
                "spec2": "B",
                "provider": "openai",
                "api_key": "test-key",
            })
        self.assertEqual(response.status_code, 502)

    def test_compare_removes_unverified_price_claims(self):
        rec = importlib.import_module("recommender")
        with patch.object(
            rec,
            "llm_chat",
            new_callable=AsyncMock,
            return_value='{"winner":"1","verdict":"invented market price 1 THB"}',
        ):
            result = asyncio.run(rec.compare_specs("Spec A", "Spec B", api_key="test"))
        self.assertNotIn("invented market price", result)
        self.assertIn("ไม่มีแหล่งข้อมูลยืนยัน", result)


if __name__ == "__main__":
    unittest.main()
