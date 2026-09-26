import asyncio
import json
import sqlite3
import unittest
from unittest.mock import AsyncMock, patch

import httpx

import full_scraper as scraper


class ScraperSourceDataTests(unittest.TestCase):
    def test_transient_http_failures_retry_but_404_does_not(self):
        request = httpx.Request("GET", "https://store.example/category")
        rate_limited = httpx.Response(429, request=request)
        success = httpx.Response(200, request=request, text="ok")
        client = AsyncMock()
        client.request.side_effect = [rate_limited, success]

        with patch.object(scraper.asyncio, "sleep", AsyncMock()) as sleep:
            response = asyncio.run(
                scraper.request_with_retry(client, "GET", str(request.url))
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(client.request.await_count, 2)
        sleep.assert_awaited_once_with(5.0)

        not_found = httpx.Response(404, request=request)
        client = AsyncMock()
        client.request.return_value = not_found
        response = asyncio.run(
            scraper.request_with_retry(client, "GET", str(request.url))
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(client.request.await_count, 1)

    def test_complete_store_payload_skips_redundant_detail_request(self):
        self.assertFalse(scraper.source_payload_needs_detail("x" * 30, "https://img"))
        self.assertTrue(scraper.source_payload_needs_detail("short", "https://img"))
        self.assertTrue(scraper.source_payload_needs_detail("x" * 30, ""))

    def test_ihavecpu_full_catalog_uses_all_requested_groups_and_low_price_gear(self):
        self.assertEqual(len(scraper.IHC_FULL_CATS), 12)
        self.assertIn(
            ("Gaming Gear", "https://ihavecpu.com/category/gaming-gear"),
            scraper.IHC_FULL_CATS,
        )
        self.assertIn(
            ("Gaming Chair", "https://ihavecpu.com/category/gaming-chair"),
            scraper.IHC_FULL_CATS,
        )
        self.assertIn(
            ("Gaming Desk", "https://ihavecpu.com/category/gaming-desk"),
            scraper.IHC_FULL_CATS,
        )
        self.assertEqual(
            scraper.ihc_full_category("GAMING CHAIR TEST", "Gaming Chair"),
            "Gaming Chair",
        )
        self.assertEqual(
            scraper.ihc_full_category("GAMING DESK TEST", "Gaming Desk"),
            "Gaming Desk",
        )
        self.assertEqual(scraper.parse_price("129.00", min_price=1), 129)
        self.assertEqual(scraper.ihc_full_category("MOUSE PAD FANTECH MP78", "Gaming Gear"),
                         "Gaming Gear")
        self.assertEqual(scraper.ihc_full_category("MOUSE LOGITECH B100", "Gaming Gear"),
                         "Mouse")
        payload = {"props": {"pageProps": {"product": {"row": 791, "data": [{}]}}}}
        document = '<script id="__NEXT_DATA__" type="application/json">' + json.dumps(payload) + '</script>'
        self.assertEqual(scraper.ihc_listing_total(document), 791)

    def test_ihavecpu_image_only_description_keeps_source_detail_image(self):
        product = {
            "description_th": '<p><img src="https://img.example/detail.jpg"></p>',
        }
        self.assertEqual(
            scraper.ihc_product_description(product),
            "Detail image: https://img.example/detail.jpg",
        )

    def test_advice_psu_summary_without_connectors_needs_spec_table(self):
        summary = "750W / 80 PLUS BRONZE / Full Modular"
        detail = "PCIe Power Connector: (6+2 Pin) x 4 Connector"
        self.assertTrue(scraper.source_payload_needs_detail(
            summary, "https://img", "PSU", "advice"
        ))
        self.assertFalse(scraper.source_payload_needs_detail(
            summary + "\n" + detail, "https://img", "PSU", "advice"
        ))
        self.assertEqual(scraper.select_best_relevant_description(
            [(5000, summary), (1500, detail + "\nPower Capacity: 750W")],
            "POWER SUPPLY 750W DTECH PW071A", "PSU",
        ), detail + "\nPower Capacity: 750W")

    def test_advice_listing_update_keeps_saved_psu_connector_details(self):
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
                product_id TEXT, store TEXT, price REAL, captured_at TEXT
            );
            INSERT INTO products (product_id, p_name, p_price, price_advice,
                                  category, desc_advice, specs) VALUES
                ('psu', 'POWER SUPPLY 750W DTECH PW071A', 1450, 1450,
                 'PSU', 'PCIe Power Connector: (6+2 Pin) x 4 Connector', '');
        """)
        matcher = scraper.SmartMatcher(conn.cursor())
        scraper.upsert_product(conn.cursor(), matcher, {
            "name": "POWER SUPPLY 750W DTECH PW071A", "category": "PSU",
            "store": "advice", "price": 1450,
            "description": "750W / 80 PLUS BRONZE / Full Modular",
        })
        saved = conn.execute("SELECT desc_advice FROM products WHERE product_id='psu'").fetchone()[0]
        self.assertIn("PCIe Power Connector: (6+2 Pin) x 4 Connector", saved)
        conn.close()

    def test_ihavecpu_full_catalog_does_not_merge_distinct_source_ids(self):
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
                product_id TEXT, store TEXT, price REAL, captured_at TEXT
            );
            INSERT INTO products (product_id, p_name, p_price, price_ihavecpu,
                                  category, url_ihavecpu) VALUES
                ('old', 'KEYCAP LOGA RED', 100, 100, 'Gaming Gear',
                 'https://ihavecpu.com/product/123/keycap-loga-red');
        """)
        matcher = scraper.SmartMatcher(conn.cursor())
        matcher.find = lambda name, category: "old"
        scraper.upsert_product(conn.cursor(), matcher, {
            "name": "KEYCAP LOGA BLUE", "category": "Gaming Gear", "store": "ihavecpu",
            "price": 100, "full_catalog": True,
            "url": "https://ihavecpu.com/product/456/keycap-loga-blue",
            "description": "Color: Blue", "img_url": "https://img.example/blue.jpg",
        })
        rows = conn.execute(
            "SELECT product_id, url_ihavecpu FROM products ORDER BY product_id"
        ).fetchall()
        self.assertEqual(rows, [
            ("ihc_456", "https://ihavecpu.com/product/456/keycap-loga-blue"),
            ("old", "https://ihavecpu.com/product/123/keycap-loga-red"),
        ])
        conn.close()

    def test_relevant_spec_beats_larger_related_product_container(self):
        name = "CPU AMD RYZEN 5 5600 3.5 GHz SOCKET AM4"
        unrelated = "CPU INTEL CORE I9 14900K " + ("related product " * 300)
        specs = (
            "Model Ryzen 5 Brand AMD Socket AM4 CPU Core 6 Cores 12 Threads "
            "Frequency 3.5 GHz Turbo 4.4 GHz Cache L3 32 MB TDP 65 W"
        )
        selected = scraper.select_best_relevant_description(
            [(5000, unrelated), (900, specs)], name, "CPU"
        )
        self.assertEqual(selected, specs)

    def test_jib_http_detail_uses_server_rendered_spec_block(self):
        request = httpx.Request("GET", "https://jib.example/product/52538")
        html = """
        <html><head><meta property="og:image" content="https://img.example/cpu.jpg"></head>
        <body>
          <div class="detail">CPU INTEL CORE I9 14900K related product related product</div>
          <div id="product_specification">
            Model Ryzen 5 Brand AMD Socket AM4 CPU Core 6 Cores 12 Threads
            Frequency 3.5 GHz Turbo 4.4 GHz Cache L3 32 MB TDP 65 W
          </div>
        </body></html>
        """
        client = AsyncMock()
        client.request.return_value = httpx.Response(
            200, request=request, text=html
        )
        desc, image = asyncio.run(scraper.fetch_jib_detail_http(
            client, str(request.url),
            "CPU AMD RYZEN 5 5600 3.5 GHz SOCKET AM4", "CPU",
        ))
        self.assertIn("Socket AM4", desc)
        self.assertIn("TDP 65 W", desc)
        self.assertEqual(image, "https://img.example/cpu.jpg")

    def test_ihavecpu_next_payload_produces_structured_specs(self):
        product = {
            "product_id": 24243,
            "name_th": "CPU AMD AM5 RYZEN 5 7500F",
            "price_sale": "4990.00",
            "property": [
                {"filter_text": "Socket Type", "detail": [{"name_th": "AM5"}]},
                {"filter_text": "Default TDP", "detail": [{"name_th": "65W"}]},
            ],
            "size_guide_th": "<p>Socket : AM5&nbsp; 6 cores 12 threads</p>",
        }
        payload = {"props": {"pageProps": {"product": {"data": [product]}}}}
        document = (
            '<html><script id="__NEXT_DATA__" type="application/json">'
            + json.dumps(payload)
            + "</script></html>"
        )

        self.assertEqual(scraper.ihc_listing_products(document), [product])
        description = scraper.ihc_product_description(product)
        self.assertIn("Socket Type: AM5", description)
        self.assertIn("Default TDP: 65W", description)
        self.assertIn("Summary: Socket : AM5 6 cores 12 threads", description)
        self.assertIn("/product/24243/", scraper.ihc_product_url(24243, product["name_th"]))

    def test_ihavecpu_listing_keeps_retailer_product_href(self):
        product = {
            "product_id": 10933,
            "name_th": "PSU (อุปกรณ์จ่ายไฟ) AZZA PSAZ 550W (80+BRONZE) (3Y)",
        }
        href = "/product/10933/psu-(%E0%B8%AD%E0%B8%B8)-azza-psaz-550w-(80bronze)(3y)"
        payload = {"props": {"pageProps": {"product": {"data": [product]}}}}
        document = (
            f'<a href="{href}">product</a>'
            '<script id="__NEXT_DATA__" type="application/json">'
            + json.dumps(payload) + "</script>"
        )
        item = scraper.ihc_listing_products(document)[0]
        self.assertEqual(scraper.ihc_item_url(item), "https://ihavecpu.com" + href)
        self.assertNotEqual(scraper.ihc_item_url(item), scraper.ihc_product_url(10933, item["name_th"]))

    def test_ihavecpu_image_only_description_uses_source_meta_description(self):
        product = {
            "product_id": 44014,
            "name_th": "SILICONE ARCTIC THERMAL MX-7 2G",
            "description_th": '<p><img src="https://img.example/detail.jpg"></p>',
            "meta_description_th": "SILICONE ARCTIC THERMAL MX-7 2G",
        }
        description = scraper.ihc_product_description(product)
        self.assertEqual(
            description,
            "Meta description: SILICONE ARCTIC THERMAL MX-7 2G",
        )
        self.assertGreaterEqual(len(description), 30)

    def test_gpu_installment_amount_is_not_accepted_as_price(self):
        self.assertFalse(scraper.valid_product_price("GPU", 500))
        self.assertTrue(scraper.valid_product_price("GPU", 17_900))

    def test_advice_api_uses_sale_price_and_direct_product_url(self):
        payload = {"data": {"product": [{"product": [{
            "code": "A0185122",
            "product": "VGA SAPPHIRE RADEON RX 9070XT",
            "price_sale_true": 38800,
            "price_srp": 38900,
            "product_url": "graphic-card/vga-sapphire-rx-9070xt",
            "spec": "PSU Require 850w",
        }]}]}}
        item = scraper.advice_api_items(payload)[0]
        self.assertEqual(item["price"], 38800)
        self.assertEqual(
            item["url"],
            "https://www.advice.co.th/product/graphic-card/vga-sapphire-rx-9070xt",
        )
        self.assertEqual(item["spec"], "PSU Require 850w")

    def test_gpu_sibling_variants_and_gre_do_not_merge(self):
        nitro = "VGA SAPPHIRE RADEON RX 9070XT NITRO GAMING 16GB GDDR6"
        pulse = "VGA SAPPHIRE RADEON RX 9070XT PULSE GAMING 16GB GDDR6"
        xt = "VGA GIGABYTE RADEON RX 9070XT GAMING 16GB GDDR6"
        gre = "VGA GIGABYTE RADEON RX 9070 GRE GAMING 12GB GDDR6"
        self.assertFalse(scraper.is_same_product(nitro, "GPU", pulse, "GPU"))
        self.assertFalse(scraper.is_same_product(xt, "GPU", gre, "GPU"))
        self.assertTrue(scraper.source_url_conflicts(
            nitro,
            "https://www.advice.co.th/product/vga-sapphire-radeon-rx-9070xt-pulse-gaming-16gb-gddr6",
            "GPU",
        ))
        self.assertTrue(scraper.source_url_conflicts(
            "VGA SAPPHIRE RX 9070XT NITRO PHANTOMLINK OC 16GB GDDR6",
            "https://www.advice.co.th/product/vga-sapphire-rx-9070xt-nitro-phantomlink-polar-oc-16gb-gddr6",
            "GPU",
        ))

    def test_power_color_alias_and_asrock_gpu_do_not_merge(self):
        powercolor = "VGA POWER COLOR RADEON RX 9060XT REAPER FIGHTER - 16GB GDDR6"
        asrock = "VGA ASROCK RADEON RX 9060 XT CHALLENGER OC 16GB GDDR6"
        asrock_url = (
            "https://www.advice.co.th/product/graphic-card-vga-/amd-radeon-rx-9000-series/"
            "vga-asrock-radeon-rx-9060xt-challenger-oc-16gb-gddr6"
        )
        self.assertEqual(scraper.extract_brand(powercolor), "POWERCOLOR")
        self.assertFalse(scraper.is_same_product(powercolor, "GPU", asrock, "GPU"))
        self.assertTrue(scraper.source_url_conflicts(powercolor, asrock_url, "GPU"))

    def test_broad_search_result_category_is_corrected(self):
        self.assertEqual(
            scraper.detect_obvious_category("Apple Magic Keyboard with Touch ID", "Mainboard"),
            "Keyboard",
        )
        self.assertEqual(
            scraper.detect_jib_cat("CPU AIR COOLER NOCTUA NH-D12L"),
            "Air Cooler",
        )

    def test_broad_search_accessory_urls_are_out_of_scope(self):
        self.assertTrue(scraper.source_url_is_out_of_scope(
            "https://www.advice.co.th/product/gaming-microphone/gaming-microphone/microphone-razer"
        ))
        self.assertTrue(scraper.source_url_is_out_of_scope(
            "https://www.advice.co.th/product/cctv-accessories/power-supply/unit"
        ))
        self.assertTrue(scraper.source_url_is_out_of_scope(
            "https://www.advice.co.th/product/ups-เครื่องสำรองไฟ-/1000-va/unit"
        ))
        self.assertFalse(scraper.source_url_is_out_of_scope(
            "https://www.advice.co.th/product/power-supply/850w/corsair-rm850"
        ))

    def test_repair_recalculates_lowest_price(self):
        conn = sqlite3.connect(":memory:")
        conn.execute(
            "CREATE TABLE products (product_id TEXT PRIMARY KEY, category TEXT, "
            "price_advice INTEGER, price_jib INTEGER, price_ihavecpu INTEGER, p_price INTEGER)"
        )
        conn.execute(
            "INSERT INTO products VALUES ('gpu1','GPU',500,0,17490,500)"
        )

        self.assertEqual(scraper.repair_implausible_prices(conn), 1)
        row = conn.execute(
            "SELECT price_advice, price_ihavecpu, p_price FROM products WHERE product_id='gpu1'"
        ).fetchone()
        self.assertEqual(row, (0, 17490, 17490))
        conn.close()


class _FakePage:
    async def close(self):
        return None


class _FakeContext:
    async def new_page(self):
        return _FakePage()


class DetailQueueTests(unittest.IsolatedAsyncioTestCase):
    def connection(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE products (product_id TEXT PRIMARY KEY)")
        scraper.setup_db(conn)
        return conn

    async def test_jib_queue_is_bounded_and_reports_throughput(self):
        conn = self.connection()
        active = 0
        max_active = 0

        async def fake_fetch(*_args, **_kwargs):
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.02)
            active -= 1
            return "d" * 40, "https://img.example/item.jpg"

        items = [
            {"url": f"https://jib.example/{n}", "name": f"item {n}", "category": "CPU"}
            for n in range(8)
        ]
        with patch.object(scraper, "fetch_detail_page", side_effect=fake_fetch):
            results, metrics = await scraper.fetch_browser_detail_queue(
                _FakeContext(), conn, "jib", items, concurrency=4
            )
        self.assertEqual(len(results), 8)
        self.assertEqual(max_active, 4)
        self.assertEqual(metrics["concurrency"], 4)
        self.assertGreater(metrics["pages_per_second"], 0)
        conn.close()

    async def test_cancel_then_resume_uses_checkpoint_and_leaves_no_tasks(self):
        conn = self.connection()
        items = [
            {"url": f"https://jib.example/{n}", "name": f"item {n}", "category": "CPU"}
            for n in range(4)
        ]
        second_started = asyncio.Event()
        calls = 0

        async def interrupted_fetch(*_args, **_kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                return "d" * 40, "https://img.example/1.jpg"
            second_started.set()
            await asyncio.sleep(60)
            return "d" * 40, "https://img.example/later.jpg"

        with patch.object(scraper, "fetch_detail_page", side_effect=interrupted_fetch):
            task = asyncio.create_task(
                scraper.fetch_browser_detail_queue(
                    _FakeContext(), conn, "jib", items, concurrency=1
                )
            )
            await second_started.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task

        completed_before_resume = conn.execute(
            "SELECT count(*) FROM scrape_detail_checkpoint WHERE status='success'"
        ).fetchone()[0]
        self.assertEqual(completed_before_resume, 1)

        resume_calls = 0

        async def resumed_fetch(*_args, **_kwargs):
            nonlocal resume_calls
            resume_calls += 1
            await asyncio.sleep(0.005)
            return "d" * 40, "https://img.example/resumed.jpg"

        with patch.object(scraper, "fetch_detail_page", side_effect=resumed_fetch):
            results, metrics = await scraper.fetch_browser_detail_queue(
                _FakeContext(), conn, "jib", items, concurrency=1
            )
        self.assertEqual(len(results), 4)
        self.assertEqual(resume_calls, 3)
        self.assertEqual(metrics["checkpoint_hits"], 1)
        self.assertFalse(any(
            task.get_name().startswith("jib-detail-")
            for task in asyncio.all_tasks() if task is not asyncio.current_task()
        ))
        conn.close()

    async def test_advice_circuit_opens_after_two_recent_429s(self):
        limiter = scraper.AdaptiveRateLimiter(
            "advice", threshold=2, base_cooldown_seconds=20
        )
        before = scraper.time.monotonic()
        await limiter.record_status(429)
        await limiter.record_status(429)
        self.assertEqual(limiter.metrics()["http_429"], 2)
        self.assertEqual(limiter.metrics()["circuit_open"], 1)
        self.assertGreaterEqual(limiter.pause_until, before + 19)


if __name__ == "__main__":
    unittest.main()
