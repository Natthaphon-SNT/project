import unittest
import asyncio
import sqlite3
from unittest.mock import AsyncMock, patch
from bs4 import BeautifulSoup
import httpx

import jib_full_scraper as jib
import full_scraper as core


class JibFullScraperTests(unittest.TestCase):
    def test_requested_exclusions(self):
        excluded = [
            (42, "DVD WRITER ASUS"), (42, "SOUND CARD CREATIVE"),
            (60, "NAS SYNOLOGY"), (60, "RAM FOR NAS 16GB"),
            (60, "FLASH DRIVE USB 128GB"), (60, "MEMORY CARD 64GB"),
            (60, "CARD READER USB"), (1419, "SWITCH GATERON BROWN"),
            (1419, "WRIST REST LOGITECH"), (1419, "TOP PLATE KEYBOARD"),
            (1419, "MOUSE PAD XXL"), (1420, "TRUE WIRELESS HEADPHONE"),
            (1420, "KARAOKE HEADSET"), (1420, "SPEAKERPHONE"),
            (1420, "HEADPHONE ADAPTER"), (1420, "HEADSET STAND"),
            (1393, "CASE FAN CORSAIR 120MM"),
        ]
        for category_id, name in excluded:
            with self.subTest(category_id=category_id, name=name):
                self.assertIsNone(jib.classify(name, category_id))

    def test_color_variants_are_not_merged_across_stores(self):
        self.assertTrue(jib.explicit_color_conflict(
            "CASE MONTECH XR (BLACK)", "CASE MONTECH XR (WHITE)"
        ))
        self.assertFalse(jib.explicit_color_conflict(
            "CASE MONTECH XR (BLACK)", "CASE MONTECH XR BLACK"
        ))

    def test_kept_products_are_split_into_subcategories(self):
        expected = [
            (42, "CPU AMD RYZEN 7", "CPU"),
            (42, "MAINBOARD ASUS B650M", "Mainboard"),
            (42, "VGA NVIDIA RTX 5070", "GPU"),
            (42, "PSU 750W", "PSU"),
            (42, "LCD PANEL CORSAIR XENEON EDGE", "Monitor Accessories"),
            (42, "PC CARRYING BAG DEEPCOOL CASEFREE", "Case Accessories"),
            (60, "2 TB HDD SEAGATE", "HDD"),
            (60, "1 TB SSD SAMSUNG", "SSD"),
            (60, "EXTERNAL SSD WD", "External Storage"),
            (1419, "KEYBOARD LOGITECH RED SWITCH", "Keyboard"),
            (1419, "BLUETOOTH KEYBOARD RAPOO", "Keyboard"),
            (1419, "WIRELESS NUMPAD KEYCHRON", "Keypad"),
            (1419, "GRAPHIC TABLET WACOM INTUOS", "Graphic Tablet"),
            (1420, "HEADSET CORSAIR", "Headset"),
            (1393, "CPU AIR COOLER NOCTUA", "Air Cooler"),
            (1393, "CPU LIQUID COOLER CORSAIR", "Liquid Cooler"),
        ]
        for category_id, name, category in expected:
            with self.subTest(category_id=category_id, name=name):
                self.assertEqual(jib.classify(name, category_id), category)
        for category, cid in (
            ("HDD", "c19"), ("External Storage", "c20"),
            ("Keyboard Accessories", "c21"),
            ("Cooling Accessories", "c22"),
            ("Monitor Accessories", "c25"),
            ("Case Accessories", "c26"), ("Keypad", "c27"),
            ("Graphic Tablet", "c28"),
        ):
            self.assertEqual(core.get_cid(category), cid)

    def test_card_uses_product_link_not_favorite_link(self):
        soup = BeautifulSoup('''<div class="divboxpro">
          <a href="/web/signin/product_favorite_add/123">favorite</a>
          <a href="/web/product/readProduct/456/12/CPU-INTEL">
            <img src="/img_master/product/medium/456.jpg">
          </a>
          <span class="promo_name">CPU INTEL CORE I5</span>
          <p class="price_total">4,590.-</p>
        </div>''', "html.parser")
        item = jib.parse_card(soup.select_one("div.divboxpro"), 42)
        self.assertEqual(item["source_product_id"], 456)
        self.assertEqual(item["category"], "CPU")
        self.assertEqual(item["price"], 4590)
        self.assertTrue(item["img"].startswith("https://www.jib.co.th/"))

    def test_source_spec_does_not_reject_ram_kit_per_dimm_capacity(self):
        url = "https://www.jib.co.th/web/product/readProduct/50216/2364/ram"
        html = """<html><title>32GB (16GBx2) DDR5 RAM KINGSTON</title>
          <meta property="og:image" content="https://www.jib.co.th/img_master/product/original/50216.jpg">
          <div id="specspecial">Part No<br>KF552C40BBK2-32<br>
          Capacity per DIMM<br>16 GB<br>Total Capacity<br>32 GB<br>
          Type<br>DDR5</div></html>"""
        response = httpx.Response(200, request=httpx.Request("GET", url), text=html)
        with patch.object(core, "request_with_retry", AsyncMock(return_value=response)):
            description, image = asyncio.run(core.fetch_jib_detail_http(
                None, url, "32GB (16GBx2) DDR5 RAM KINGSTON", "RAM",
            ))
        self.assertIn("Total Capacity", description)
        self.assertIn("32 GB", description)
        self.assertTrue(image.endswith("/50216.jpg"))

    def test_promotes_only_jib_owned_image(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("""CREATE TABLE products (
            product_id TEXT, img_url TEXT, price_advice INTEGER,
            price_ihavecpu INTEGER)""")
        jib.setup_inventory(conn)
        medium = "https://www.jib.co.th/img_master/product/medium/a.jpg"
        original = "https://www.jib.co.th/img_master/product/original/a.jpg"
        conn.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", [
            ("jib_only", medium, 0, 0), ("shared", medium, 1, 0),
        ])
        conn.executemany("""INSERT INTO jib_scrape_inventory
            (source_category_id, source_product_id, category, product_name,
             price, image_url, product_url, db_product_id, listing_seen_at)
            VALUES (42, ?, 'CPU', 'CPU TEST', 1000, ?, 'https://example.test', ?, '')
        """, [(1, original, "jib_only"), (2, original, "shared")])
        self.assertEqual(jib.promote_jib_images(conn), 1)
        self.assertEqual(conn.execute(
            "SELECT img_url FROM products WHERE product_id='jib_only'"
        ).fetchone()[0], original)
        self.assertEqual(conn.execute(
            "SELECT img_url FROM products WHERE product_id='shared'"
        ).fetchone()[0], medium)
        conn.close()

    def test_clears_stale_price_when_source_now_says_na(self):
        conn = sqlite3.connect(":memory:")
        conn.execute("""CREATE TABLE products (
            product_id TEXT, url_jib TEXT, price_advice INTEGER,
            price_jib INTEGER, price_ihavecpu INTEGER, p_price INTEGER)""")
        jib.setup_inventory(conn)
        source_url = "https://www.jib.co.th/web/product/readProduct/123/1/gpu"
        conn.execute("INSERT INTO products VALUES (?, ?, 0, 9999, 0, 9999)",
                     ("jib_123", source_url))
        conn.execute("""INSERT INTO jib_scrape_inventory
            (source_category_id, source_product_id, category, product_name,
             price, image_url, product_url, db_product_id, listing_seen_at)
            VALUES (42, 123, 'GPU', 'VGA TEST', 0, 'https://img', ?, 'jib_123', '')
        """, (source_url,))
        self.assertEqual(jib.clear_unpriced_jib_prices(conn), 1)
        self.assertEqual(conn.execute(
            "SELECT price_jib, p_price FROM products WHERE product_id='jib_123'"
        ).fetchone(), (0, 0))
        conn.close()

    def test_unpriced_jib_item_keeps_details_without_fabricated_price(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript("""
            CREATE TABLE products (
                product_id TEXT PRIMARY KEY, p_name TEXT, p_description TEXT,
                p_price INTEGER, price_advice INTEGER, price_jib INTEGER,
                price_ihavecpu INTEGER, url_advice TEXT, url_jib TEXT,
                url_ihavecpu TEXT, desc_advice TEXT, desc_jib TEXT,
                desc_ihavecpu TEXT, p_stock INTEGER, cid TEXT, category TEXT,
                img_url TEXT, specs TEXT, created_at TEXT, updated_at TEXT
            );
        """)
        jib.setup_inventory(conn)
        url = "https://www.jib.co.th/web/product/readProduct/987/1/GPU-TEST"
        conn.execute("""INSERT INTO jib_scrape_inventory
            (source_category_id, source_product_id, category, product_name,
             price, image_url, description, product_url, listing_seen_at)
            VALUES (42, 987, 'GPU', 'VGA TEST', 0, 'https://img',
                    'GPU specification', ?, '')
        """, (url,))
        self.assertEqual(jib.add_unpriced_jib_products(conn), 1)
        self.assertEqual(jib.add_unpriced_jib_products(conn), 0)
        self.assertEqual(conn.execute("""SELECT p_price, price_jib,
            p_description, img_url, url_jib FROM products
            WHERE product_id='jib_987'""").fetchone(),
            (0, 0, "GPU specification", "https://img", url))
        self.assertEqual(conn.execute("""SELECT db_product_id FROM
            jib_scrape_inventory WHERE source_product_id=987"""
        ).fetchone()[0], "jib_987")
        conn.close()

    def test_conflicting_jib_url_is_detached_from_other_store_model(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript("""
            CREATE TABLE products (
                product_id TEXT PRIMARY KEY, p_name TEXT, p_description TEXT,
                p_price INTEGER, price_advice INTEGER, price_jib INTEGER,
                price_ihavecpu INTEGER, url_advice TEXT, url_jib TEXT,
                url_ihavecpu TEXT, desc_advice TEXT, desc_jib TEXT,
                desc_ihavecpu TEXT, p_stock INTEGER, cid TEXT, category TEXT,
                img_url TEXT, specs TEXT, created_at TEXT, updated_at TEXT
            );
            CREATE TABLE price_history (
                product_id TEXT, store TEXT, price INTEGER, captured_at TEXT
            );
        """)
        jib.setup_inventory(conn)
        old_name = "500 GB SSD WD BLACK SN750SE WDS500G1B0E"
        new_name = "500 GB SSD WD BLACK SN7100 WDS500G4X0E"
        source_url = "https://www.jib.co.th/web/product/readProduct/123/1/WD-SN7100"
        conn.execute("""INSERT INTO products
            (product_id, p_name, p_description, p_price, price_advice,
             price_jib, price_ihavecpu, url_jib, desc_advice, desc_jib,
             category, cid, img_url, specs)
            VALUES ('advice_s750', ?, 'JIB wrong spec', 7000, 6000,
                    7000, 0, ?, 'Advice correct spec', 'JIB wrong spec',
                    'SSD', 'c05', 'https://img', 'JIB wrong spec')
        """, (old_name, source_url))
        conn.execute("""INSERT INTO jib_scrape_inventory
            (source_category_id, source_product_id, category, product_name,
             price, image_url, description, product_url, db_product_id,
             listing_seen_at)
            VALUES (60, 123, 'SSD', ?, 7000, 'https://img',
                    'JIB correct product specification', ?, 'advice_s750', '')
        """, (new_name, source_url))
        matcher = core.SmartMatcher(conn.cursor())
        self.assertEqual(jib.repair_conflicting_source_matches(conn, matcher), 1)
        self.assertEqual(conn.execute("""SELECT price_jib, url_jib,
            p_description FROM products WHERE product_id='advice_s750'"""
        ).fetchone(), (0, "", "Advice correct spec"))
        self.assertEqual(conn.execute("""SELECT db_product_id FROM
            jib_scrape_inventory WHERE source_product_id=123"""
        ).fetchone()[0], "jib_123")
        self.assertEqual(conn.execute("SELECT price_jib FROM products WHERE product_id='jib_123'").fetchone()[0], 7000)

        second_url = "https://www.jib.co.th/web/product/readProduct/124/1/WD-SN8100"
        second_name = "1 TB SSD WD BLACK SN8100 WDS100T1X0M"
        conn.execute("""INSERT INTO products
            (product_id, p_name, p_description, p_price, price_advice,
             price_jib, price_ihavecpu, url_jib, category, cid)
            VALUES ('advice_s850', '1 TB SSD WD BLACK SN850X WDS100T2XHE',
                    '', 8000, 8000, 9000, 0, ?, 'SSD', 'c05')
        """, (second_url,))
        conn.execute("""INSERT INTO products
            (product_id, p_name, p_description, p_price, price_advice,
             price_jib, price_ihavecpu, url_jib, category, cid)
            VALUES ('jib_existing', ?, '', 9000, 0, 9000, 0, ?, 'SSD', 'c05')
        """, (second_name, second_url))
        conn.execute("""INSERT INTO jib_scrape_inventory
            (source_category_id, source_product_id, category, product_name,
             price, image_url, description, product_url, db_product_id,
             listing_seen_at)
            VALUES (60, 124, 'SSD', ?, 9000, 'https://img',
                    'JIB correct product specification', ?, 'advice_s850', '')
        """, (second_name, second_url))
        matcher = core.SmartMatcher(conn.cursor())
        self.assertEqual(jib.repair_conflicting_source_matches(conn, matcher), 1)
        self.assertEqual(conn.execute("""SELECT db_product_id FROM
            jib_scrape_inventory WHERE source_product_id=124"""
        ).fetchone()[0], "jib_existing")
        self.assertEqual(conn.execute("SELECT url_jib FROM products WHERE product_id='advice_s850'").fetchone()[0], "")
        conn.close()

    def test_duplicate_jib_url_keeps_only_authoritative_model(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript("""
            CREATE TABLE products (
                product_id TEXT PRIMARY KEY, p_name TEXT, category TEXT,
                price_advice INTEGER, price_jib INTEGER, price_ihavecpu INTEGER,
                p_price INTEGER, url_jib TEXT, desc_jib TEXT, desc_advice TEXT,
                desc_ihavecpu TEXT, p_description TEXT, specs TEXT
            );
        """)
        jib.setup_inventory(conn)
        url = "https://www.jib.co.th/web/product/readProduct/123/53/RIGHT-RAM"
        conn.executemany("""INSERT INTO products VALUES
            (?, ?, 'RAM', ?, ?, 0, ?, ?, ?, ?, '', ?, ?)""", [
            ("wrong", "RAM KLEVV BOLT X KD48GU880", 2500, 3000,
             2500, url, "wrong JIB specs", "correct Advice specs",
             "wrong JIB specs", "wrong JIB specs"),
            ("right", "RAM G.SKILL TRIDENT Z F4-3200C16D", 0, 4990,
             4990, url, "old specs", "", "old specs", "old specs"),
        ])
        conn.execute("""INSERT INTO jib_scrape_inventory
            (source_category_id, source_product_id, category, product_name,
             price, image_url, description, product_url, db_product_id,
             listing_seen_at)
            VALUES (42, 123, 'RAM', 'RAM G.SKILL TRIDENT Z F4-3200C16D',
                    4990, 'https://img', 'new specs', ?, 'wrong', '')
        """, (url,))
        self.assertEqual(jib.repair_duplicate_jib_links(conn), 1)
        self.assertEqual(conn.execute("""SELECT price_jib, url_jib,
            p_description, p_price FROM products WHERE product_id='wrong'"""
        ).fetchone(), (0, "", "correct Advice specs", 2500))
        self.assertEqual(conn.execute("""SELECT price_jib, url_jib,
            desc_jib, specs FROM products WHERE product_id='right'"""
        ).fetchone(), (4990, url, "new specs", "new specs"))
        self.assertEqual(conn.execute("""SELECT db_product_id FROM
            jib_scrape_inventory WHERE source_product_id=123"""
        ).fetchone()[0], "right")
        self.assertEqual(jib.repair_duplicate_jib_links(conn), 0)
        conn.close()


if __name__ == "__main__":
    unittest.main()
