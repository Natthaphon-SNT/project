import asyncio
import contextlib
import importlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import warnings
from unittest.mock import AsyncMock, patch

import httpx
import sqlite3

from fastapi.testclient import TestClient
from sqlalchemy.orm import Query


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

    def test_health_endpoint_is_public_and_ok(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

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
        repeated = self.client.delete(
            f"/api/spec-history/{item['id']}", headers=self.auth("qa-alice")
        )
        self.assertEqual(repeated.status_code, 200)
        self.assertTrue(repeated.json()["already_deleted"])

    def test_concurrent_delete_is_idempotent_without_sqlalchemy_warning(self):
        """Simulates the Railway incident: several DELETEs for one id at once.

        The row is removed by a second connection after the endpoint has already
        read it, so the endpoint's own DELETE matches 0 rows. It must answer 200
        with already_deleted=True and must not raise SQLAlchemy's
        "expected to delete 1 row(s); 0 were matched" SAWarning.
        """
        api = self.api
        created = self.client.post(
            "/api/spec-history",
            headers=self.auth("qa-alice"),
            json={"uid": "qa-alice", "title": "race", "result_data": {}},
        )
        item_id = created.json()["data"]["id"]

        real_delete = Query.delete
        raced = {"done": False}

        def racing_delete(query_self, *args, **kwargs):
            # Race only the endpoint's own bulk delete of this id.
            if not raced["done"] and kwargs.get("synchronize_session") is False:
                raced["done"] = True
                with api.SessionLocal() as other:
                    real_delete(
                        other.query(api.SpecHistory).filter(
                            api.SpecHistory.id == item_id
                        ),
                        synchronize_session=False,
                    )
                    other.commit()
            return real_delete(query_self, *args, **kwargs)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with patch.object(Query, "delete", racing_delete):
                response = self.client.delete(
                    f"/api/spec-history/{item_id}", headers=self.auth("qa-alice")
                )

        self.assertTrue(raced["done"], "endpoint never issued a bulk delete")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["already_deleted"])

        matched_warnings = [
            w for w in caught if "were matched" in str(w.message)
        ]
        self.assertEqual(
            matched_warnings, [],
            f"SQLAlchemy still warns on concurrent delete: {matched_warnings}",
        )

        # And a third call after the dust settles stays idempotent.
        after = self.client.delete(
            f"/api/spec-history/{item_id}", headers=self.auth("qa-alice")
        )
        self.assertEqual(after.status_code, 200)
        self.assertTrue(after.json()["already_deleted"])

    def test_delete_of_never_existing_id_is_still_200(self):
        """Undistinguishable from 'already deleted', so stays a safe 200."""
        response = self.client.delete(
            "/api/spec-history/99999999", headers=self.auth("qa-alice")
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["already_deleted"])

    def test_delete_rejects_missing_token_and_other_users_row(self):
        """Auth behaviour must be unchanged by the race fix."""
        self.assertEqual(
            self.client.delete("/api/spec-history/1").status_code, 401
        )
        created = self.client.post(
            "/api/spec-history",
            headers=self.auth("qa-alice"),
            json={"uid": "qa-alice", "title": "auth", "result_data": {}},
        )
        item_id = created.json()["data"]["id"]

        for uid in ("qa-bob", "qa-admin"):
            expected = 403 if uid == "qa-bob" else 200
            response = self.client.delete(
                f"/api/spec-history/{item_id}", headers=self.auth(uid)
            )
            self.assertEqual(response.status_code, expected)
            if uid == "qa-bob":
                # The forbidden attempt must not have removed anything.
                self.assertEqual(
                    self.client.get(
                        f"/api/spec-history?uid=qa-alice",
                        headers=self.auth("qa-alice"),
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

    def test_store_then_brand_filters_full_catalog_before_pagination(self):
        with self.api.SessionLocal() as db:
            db.add_all([
                self.api.Product(product_id="qa-gear-jib-1", p_name="MOUSE LOGITECH G1",
                                 p_price=1000, price_jib=1000, category="Mouse"),
                self.api.Product(product_id="qa-gear-jib-2", p_name="MOUSE LOGITECH G2",
                                 p_price=1200, price_jib=1200, category="Mouse"),
                self.api.Product(product_id="qa-gear-advice", p_name="MOUSE RAZER R1",
                                 p_price=1300, price_advice=1300, category="Mouse"),
            ])
            db.commit()

        filters = self.client.get("/api/products/filters?category=Mouse&store=jib")
        self.assertEqual(filters.status_code, 200)
        self.assertIn("LOGITECH", filters.json()["data"]["brands"])
        self.assertNotIn("RAZER", filters.json()["data"]["brands"])

        page = self.client.get("/api/products?category=Mouse&store=jib&brand=LOGITECH&page=2&limit=1")
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.json()["pagination"]["total"], 2)
        self.assertEqual(len(page.json()["data"]), 1)
        self.assertEqual(self.client.get("/api/products?store=unknown").status_code, 400)

    def test_jib_furniture_brand_skips_category_description(self):
        with self.api.SessionLocal() as db:
            db.add_all([
                self.api.Product(
                    product_id="qa-jib-chair-onex",
                    p_name="GAMING CHAIR (เก้าอี้เกมมิ่ง) ONEX GX3",
                    p_price=3500, price_jib=3500, category="Gaming Chair",
                ),
                self.api.Product(
                    product_id="qa-jib-desk-eblue",
                    p_name="GAMING DESK (โต๊ะเกมมิ่ง) E-BLUE EGT571",
                    p_price=5900, price_jib=5900, category="Gaming Desk",
                ),
            ])
            db.commit()

        chair = self.client.get("/api/products/filters?category=Gaming%20Chair&store=jib")
        desk = self.client.get("/api/products/filters?category=Gaming%20Desk&store=jib")
        self.assertEqual(chair.json()["data"]["brands"], ["ONEX"])
        self.assertEqual(desk.json()["data"]["brands"], ["E-BLUE"])
        selected = self.client.get(
            "/api/products?category=Gaming%20Chair&store=jib&brand=ONEX"
        )
        self.assertEqual(selected.json()["pagination"]["total"], 1)

    def test_admin_created_product_is_searchable_after_save(self):
        payload = {
            "product_id": "admin-qa-searchable",
            "p_name": "QA Admin Searchable CPU",
            "p_price": 4590,
            "p_stock": 3,
            "cid": "c01",
            "category": "CPU",
            "p_description": "Manual catalog item",
        }
        created = self.client.post(
            "/api/products", headers=self.auth("qa-admin"), json=payload
        )
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json()["data"]["p_name"], payload["p_name"])

        for headers in ({}, self.auth("qa-admin")):
            with self.subTest(authenticated=bool(headers)):
                result = self.client.get(
                    "/api/products?search=QA%20Admin%20Searchable", headers=headers
                )
                self.assertEqual(result.status_code, 200)
                self.assertEqual(
                    [item["product_id"] for item in result.json()["data"]],
                    [payload["product_id"]],
                )

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
        self.assertEqual(self.client.get("/api/profile", headers=old_headers).status_code, 200)
        updated = self.client.put(
            "/api/profile", headers=old_headers,
            json={"u_name": "qa_password", "u_phone": "0812345678"},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["data"]["u_phone"], "0812345678")
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
        replacement = changed.json().get("token")
        self.assertTrue(replacement)
        new_headers = {"Authorization": f"Bearer {replacement}"}
        self.assertEqual(self.client.get("/api/profile", headers=new_headers).status_code, 200)
        saved = self.client.post(
            "/api/spec-history", headers=new_headers,
            json={"type": "manual", "title": "QA build", "result_data": {"parts": []}},
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["data"]["uid"], "qa-password")
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
        self.assertIsNone(rec.detect_budget_thb("ใช้ 13600K กับ DDR5-6000"))
        self.assertIsNone(rec.detect_budget_thb("เปรียบเทียบ i7-14700 กับ Ryzen 7600X"))
        self.assertEqual(rec.detect_budget_thb("จัดเครื่อง 50000 เล่นเกม"), 50000)

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
        self.assertEqual(response.status_code, 504)

    def test_llm_chat_retries_network_errors(self):
        rec = importlib.import_module("recommender")
        response = httpx.Response(200, json={
            "choices": [{"message": {"content": "ok"}}]
        })
        for error in (
            httpx.ReadTimeout("timed out"),
            httpx.ConnectError("connect failed"),
            httpx.ReadError("connection reset"),
        ):
            with self.subTest(error=type(error).__name__):
                client = AsyncMock()
                client.__aenter__.return_value = client
                client.post.side_effect = [error, response]
                with patch.object(rec.httpx, "AsyncClient", return_value=client), \
                     patch("asyncio.sleep", new_callable=AsyncMock):
                    result = asyncio.run(rec.llm_chat(
                        [{"role": "user", "content": "hello"}], api_key="test"
                    ))
                self.assertEqual(result, "ok")
                self.assertEqual(client.post.await_count, 2)

    def test_compare_invalid_provider_json_keeps_response_schema(self):
        rec = importlib.import_module("recommender")
        with patch.object(
            rec,
            "llm_chat",
            new_callable=AsyncMock,
            return_value="not json",
        ):
            result = json.loads(asyncio.run(
                rec.compare_specs("Spec A", "Spec B", api_key="test")
            ))
        self.assertTrue(result["error"])
        self.assertEqual(result["categories"], [])
        self.assertIn("compatibility", result)

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

    def test_pc_builder_catalog_only_accepts_the_requested_component(self):
        accepted = [
            ("cpu", "CPU AMD RYZEN 5 9600", "CPU"),
            ("mb", "MAINBAORD AM4 ASROCK B550M", "Mainboard"),
            ("gpu", "VGA ASUS GEFORCE RTX 5070", "GPU"),
            ("ram", "RAM KINGSTON 32GB DDR5", "RAM"),
            ("ssd", "M.2 SAMSUNG 990 PRO NVME SSD", "SSD"),
            ("hdd", "4 TB HDD SEAGATE BARRACUDA", "SSD"),
            ("psu", "PSU CORSAIR RM850E 850W", "PSU"),
            ("case", "CASE CORSAIR 4000D ATX", "Case"),
            ("cooler", "CPU AIR COOLER NOCTUA NH-D15", "Air Cooler"),
            ("cooler", "LIQUID COOLER DEEPCOOL LE720", "Liquid Cooler"),
        ]
        rejected = [
            ("cpu", "AIO Lenovo ThinkCentre Neo 55a", "CPU"),
            ("mb", "Keypad ELGATO STREAM DECK", "Mainboard"),
            ("ssd", "4 TB HDD SEAGATE BARRACUDA", "SSD"),
            ("hdd", "1 TB EXT HDD SEAGATE ONE TOUCH", "SSD"),
            ("hdd", "Tray DVD Drive For HDD N/B", "SSD"),
            ("psu", "ATX CASE ANTEC C5 ARGB", "PSU"),
            ("case", "CASE FAN 120MM ARGB", "Case"),
            ("cooler", "Cooler Pad OKER C-818", "Air Cooler"),
            ("cooler", "FAN iHAVECPU FLOE 120 PACK3", "Liquid Cooler"),
            ("cooler", "AIO Lenovo IdeaCentre AIO 24IRH9", "Liquid Cooler"),
        ]

        for component, name, category in accepted:
            with self.subTest(component=component, name=name, accepted=True):
                product = self.api.Product(p_name=name, category=category)
                self.assertTrue(
                    self.api.product_matches_builder_component(product, component)
                )
        for component, name, category in rejected:
            with self.subTest(component=component, name=name, accepted=False):
                product = self.api.Product(p_name=name, category=category)
                self.assertFalse(
                    self.api.product_matches_builder_component(product, component)
                )

    # ── AI provider failure handling (POST /api/ai/recommend) ────────────────
    def _provider_response(self, status_code, payload=None, text=None):
        """Build a mocked httpx.Response for a provider call."""
        if text is not None:
            return httpx.Response(status_code, text=text)
        return httpx.Response(status_code, json=payload or {})

    def test_llm_chat_raises_runtime_error_on_rate_limit(self):
        rec = importlib.import_module("recommender")
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.return_value = self._provider_response(429, {"error": {"message": "slow down"}})
        with patch.object(rec.httpx, "AsyncClient", return_value=client):
            with self.assertRaises(RuntimeError) as ctx:
                asyncio.run(rec.llm_chat(
                    [{"role": "user", "content": "hi"}],
                    provider="openai", api_key="test-key", max_attempts=2,
                ))
        self.assertEqual(str(ctx.exception), "rate_limit")
        # rate_limit must not be retried
        self.assertEqual(client.post.await_count, 1)

    def test_llm_chat_distinguishes_exhausted_credits_from_temporary_limit(self):
        rec = importlib.import_module("recommender")
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.return_value = self._provider_response(
            429, {"error": {"code": "credit_balance_exhausted", "message": "Add credits"}}
        )
        with patch.object(rec.httpx, "AsyncClient", return_value=client):
            with self.assertRaisesRegex(RuntimeError, "quota_exhausted: credit_balance_exhausted"):
                asyncio.run(rec.llm_chat(
                    [{"role": "user", "content": "hi"}],
                    provider="openai", api_key="test-key", max_attempts=2,
                ))
        self.assertEqual(client.post.await_count, 1)

    def test_llm_chat_retries_5xx_then_succeeds(self):
        rec = importlib.import_module("recommender")
        ok = self._provider_response(200, {"choices": [{"message": {"content": "ok"}}]})
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.side_effect = [self._provider_response(503, {"error": "upstream"}), ok]
        with patch.object(rec.httpx, "AsyncClient", return_value=client), \
             patch("asyncio.sleep", new_callable=AsyncMock):
            result = asyncio.run(rec.llm_chat(
                [{"role": "user", "content": "hi"}], api_key="test-key", max_attempts=2,
            ))
        self.assertEqual(result, "ok")
        self.assertEqual(client.post.await_count, 2)

    def test_llm_chat_wraps_non_json_provider_body(self):
        rec = importlib.import_module("recommender")
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.return_value = self._provider_response(200, text="<html>bad gateway</html>")
        with patch.object(rec.httpx, "AsyncClient", return_value=client), \
             patch("asyncio.sleep", new_callable=AsyncMock):
            with self.assertRaises(RuntimeError) as ctx:
                asyncio.run(rec.llm_chat(
                    [{"role": "user", "content": "hi"}], api_key="test-key", max_attempts=1,
                ))
        self.assertIn("non-JSON", str(ctx.exception))

    def test_llm_chat_uses_max_completion_tokens_for_gpt5_family(self):
        rec = importlib.import_module("recommender")
        for model, expect_token_field in (
            ("gpt-4o-mini", "max_tokens"),
            ("gpt-5", "max_completion_tokens"),
            ("gpt-5-mini", "max_completion_tokens"),
        ):
            with self.subTest(model=model):
                client = AsyncMock()
                client.__aenter__.return_value = client
                client.post.return_value = self._provider_response(
                    200, {"choices": [{"message": {"content": "ok"}}]}
                )
                with patch.object(rec.httpx, "AsyncClient", return_value=client):
                    asyncio.run(rec.llm_chat(
                        [{"role": "user", "content": "hi"}],
                        provider="openai", model=model, api_key="k",
                    ))
                sent = client.post.await_args.kwargs["json"]
                self.assertIn(expect_token_field, sent)
                self.assertNotIn(
                    "max_tokens" if expect_token_field == "max_completion_tokens" else "max_completion_tokens",
                    sent,
                )
                if expect_token_field == "max_completion_tokens":
                    self.assertNotIn("temperature", sent)

    def test_reasoning_models_are_detected_across_families(self):
        rec = importlib.import_module("recommender")
        for model in ("gpt-5", "gpt-5.6-sol", "gpt-5-mini", "gpt-6", "gpt-6.1",
                      "o1", "o1-mini", "o3-mini", "o4-mini"):
            with self.subTest(model=model):
                self.assertTrue(rec.is_reasoning_model(model))
        for model in ("gpt-4o-mini", "gpt-4.1", "gemini-3-flash-preview", ""):
            with self.subTest(model=model):
                self.assertFalse(rec.is_reasoning_model(model))

    def test_reasoning_models_get_a_token_floor_large_enough_for_thinking(self):
        """A reasoning model bills thinking against the completion budget, so a
        chat-sized budget (700) would leave nothing for the visible answer."""
        rec = importlib.import_module("recommender")
        for model in ("gpt-5.6-sol", "gpt-6.1", "o3-mini"):
            with self.subTest(model=model):
                client = AsyncMock()
                client.__aenter__.return_value = client
                client.post.return_value = self._provider_response(
                    200, {"choices": [{"message": {"content": "ok"}}]}
                )
                with patch.object(rec.httpx, "AsyncClient", return_value=client):
                    asyncio.run(rec.llm_chat(
                        [{"role": "user", "content": "hi"}],
                        provider="openai", model=model, api_key="k",
                        max_tokens=700,
                    ))
                sent = client.post.await_args.kwargs["json"]
                self.assertNotIn("max_tokens", sent)
                self.assertGreaterEqual(
                    sent["max_completion_tokens"], rec.REASONING_MIN_COMPLETION_TOKENS,
                )

    def test_reasoning_model_with_long_thinking_no_longer_returns_empty_content(self):
        """Simulate a provider that spends a fixed number of reasoning tokens and
        only emits visible content when the completion budget has room left."""
        rec = importlib.import_module("recommender")
        thinking_tokens = 2_000

        def fake_post(url, json=None, headers=None):
            budget = json.get("max_completion_tokens", json.get("max_tokens", 0))
            room = budget - thinking_tokens
            spent = min(thinking_tokens, budget)
            message = {"role": "assistant", "content": "คำตอบที่ถูกต้อง" if room > 0 else ""}
            return self._provider_response(200, {
                "model": json["model"],
                "choices": [{"message": message}],
                "usage": {
                    "completion_tokens": budget,
                    "completion_tokens_details": {"reasoning_tokens": spent},
                },
            })

        for model in ("gpt-5.6-sol", "gpt-6", "gpt-5-mini"):
            with self.subTest(model=model):
                client = AsyncMock()
                client.__aenter__.return_value = client
                client.post.side_effect = fake_post
                with patch.object(rec.httpx, "AsyncClient", return_value=client):
                    result = asyncio.run(rec.llm_chat(
                        [{"role": "user", "content": "hi"}],
                        provider="openai", model=model, api_key="k",
                        max_tokens=700, max_attempts=1,
                    ))
                self.assertEqual(result, "คำตอบที่ถูกต้อง")

    def test_empty_content_error_names_the_model_and_reasoning_tokens(self):
        rec = importlib.import_module("recommender")
        client = AsyncMock()
        client.__aenter__.return_value = client
        client.post.return_value = self._provider_response(200, {
            "model": "gpt-5.6-sol",
            "choices": [{"message": {"role": "assistant", "content": "  "}}],
            "usage": {"completion_tokens_details": {"reasoning_tokens": 8192}},
        })
        with patch.object(rec.httpx, "AsyncClient", return_value=client), \
             patch("asyncio.sleep", new_callable=AsyncMock):
            with self.assertRaises(RuntimeError) as ctx:
                asyncio.run(rec.llm_chat(
                    [{"role": "user", "content": "hi"}],
                    provider="openai", model="gpt-5.6-sol", api_key="k", max_attempts=1,
                ))
        message = str(ctx.exception)
        self.assertIn("gpt-5.6-sol", message)
        self.assertIn("reasoning_tokens=8192", message)

    def test_compare_falls_back_to_deterministic_on_provider_error(self):
        rec = importlib.import_module("recommender")
        for error in (
            RuntimeError("AI provider error 400: max_tokens is not supported"),
            RuntimeError("Auth/Credits error (401): invalid api key"),
            httpx.ConnectError("connection refused"),
        ):
            with self.subTest(error=type(error).__name__ + ": " + str(error)):
                with patch.object(rec, "compare_specs", new_callable=AsyncMock, side_effect=error):
                    response = self.client.post("/api/ai/recommend", json={
                        "prompt": "compare", "mode": "compare",
                        "spec1": "CPU AMD RYZEN 5 5600", "spec2": "CPU INTEL CORE I5 12400F",
                        "provider": "openai", "api_key": "test-key",
                    })
                self.assertEqual(response.status_code, 200)
                data = json.loads(response.json()["data"])
                self.assertTrue(data["error"])
                self.assertEqual(data["status"], "provider_unavailable")
                self.assertEqual(data["provider_label"], "OpenAI")
                self.assertIn("deterministic", data["message"])
                self.assertIn("compatibility", data)

    def test_ask_falls_back_to_deterministic_on_provider_error(self):
        rec = importlib.import_module("recommender")
        with patch.object(rec, "answer_spec_question", new_callable=AsyncMock,
                          side_effect=RuntimeError("Auth/Credits error (401): bad key")):
            response = self.client.post("/api/ai/recommend", json={
                "prompt": "ทำไมต้อง DDR5", "mode": "ask",
                "provider": "openai", "api_key": "test-key",
                "spec_context": "CPU AMD RYZEN 5 5600 (9,900 ฿)",
            })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.json()["data"])
        self.assertTrue(data["error"])
        self.assertEqual(data["status"], "provider_unavailable")
        self.assertIn("deterministic", data["message"])

    def test_recommend_provider_failure_never_returns_bare_502(self):
        """A provider failure (and even a failing deterministic fallback) must
        surface a readable message instead of an unexplained 502."""
        rec = importlib.import_module("recommender")
        for provider_error in (
            RuntimeError("rate_limit"),
            RuntimeError("AI provider error 400: max_tokens is not supported"),
            RuntimeError("Auth/Credits error (401): invalid api key"),
            httpx.ConnectError("connection refused"),
        ):
            with self.subTest(error=type(provider_error).__name__ + ": " + str(provider_error)):
                with patch.object(rec, "recommend_with_alternatives", new_callable=AsyncMock,
                                  side_effect=provider_error):
                    response = self.client.post("/api/ai/recommend", json={
                        "prompt": "คอมเล่นเกม 25000", "mode": "recommend",
                        "provider": "openai", "api_key": "test-key",
                    })
                self.assertNotEqual(response.status_code, 502)
                body = response.json()
                # Either a usable payload or a readable detail message.
                self.assertTrue(
                    body.get("status") == "success" or str(body.get("detail", "")).strip(),
                    msg=f"no meaningful payload: {body}",
                )


if __name__ == "__main__":
    unittest.main()
