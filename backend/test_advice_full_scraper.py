import sqlite3
import unittest

import advice_full_scraper as scraper
import spec_parser


class AdviceFullScraperTests(unittest.TestCase):
    def test_requested_categories_and_specific_classification(self):
        self.assertEqual(len(scraper.CATEGORIES), 17)
        self.assertEqual(scraper.classify("MAINBOARD ASUS B850", "mainboard"),
                         "Mainboard")
        self.assertEqual(scraper.classify("CPU LIQUID COOLER 240", "cooling-system"),
                         "Liquid Cooler")
        self.assertEqual(scraper.classify("LIQUID COOLING MSI 240", "cooling-system"),
                         "Liquid Cooler")
        self.assertEqual(scraper.classify("CPU AIR COOLER 120", "cooling-system"),
                         "Air Cooler")
        self.assertEqual(scraper.classify("CASE FAN 120", "cooling-system"),
                         "Case Fan")
        self.assertEqual(scraper.classify("FAN CASEOCYPUS 120", "cooling-system"),
                         "Case Fan")
        self.assertEqual(scraper.classify(
            "ARCTIC FAN HUB", "case",
            "https://www.advice.co.th/product/case/accessories-case/arctic-fan-hub"),
            "Case Accessories")
        self.assertEqual(scraper.classify(
            "LCD PANEL CORSAIR XENEON EDGE", "case",
            "https://www.advice.co.th/product/case/accessories-case/lcd-panel"),
            "Portable Monitor")
        self.assertEqual(scraper.classify(
            "GRAPHICS CARD HOLDER", "graphic-card-vga-",
            "https://www.advice.co.th/product/graphic-card-vga-/vga-holder/gpu-holder"),
            "GPU Accessories")
        self.assertEqual(scraper.classify(
            "TRUE WIRELESS ONIKUMA", "gaming-headset-wireless",
            "https://www.advice.co.th/product/gaming-headset-wireless/"
            "gaming-true-wireless/true-wireless-onikuma"),
            "True Wireless Earbuds")
        self.assertEqual(scraper.classify("GAMING HEADSET", "gaming-headset-wireless"),
                         "Wireless Headset")
        self.assertEqual(scraper.classify("27 INCH DISPLAY", "portable-monitor"),
                         "Portable Monitor")

    def test_catalog_payload_uses_detail_page_path(self):
        payload = scraper.catalog_payload(
            "headset", "device", product_url=(
                "https://www.advice.co.th/product/cpu/amd-am4/"
                "cpu-amd-am4-athlon-3000g-next-"),
        )
        self.assertEqual(payload["category"], "cpu")
        self.assertEqual(payload["category_sub"], "amd-am4")
        self.assertEqual(payload["product"], "cpu-amd-am4-athlon-3000g-next-")
        self.assertTrue(payload["addView"])
        self.assertFalse(payload["group_end"])

    def test_grouped_listing_and_complete_details(self):
        cards = scraper.product_cards({"product": {
            "one": {"product": [{"code": "A1"}]},
            "two": {"product": [{"code": "A2"}]},
        }})
        self.assertEqual([card["code"] for card in cards], ["A1", "A2"])
        description, image, images = scraper.flatten_detail({
            "spec_detail": [{"title": "Power", "data": [
                {"title": "PCIe Power Connector", "value": "(6+2 Pin) x 4"},
            ]}],
            "picture": [{"pic_url": "https://img.example/large.jpg"}],
            "pic_url": "https://img.example/small.jpg",
            "detail": {"feature": "<p>ATX 3.0</p>"},
        }, "750W")
        self.assertIn("PCIe Power Connector: (6+2 Pin) x 4", description)
        self.assertIn("ATX 3.0", description)
        self.assertEqual(
            spec_parser.extract_detail_facts("PSU", description).get("power_connectors"),
            {"PCIe 8-pin": 4},
        )
        self.assertEqual(image, "https://img.example/large.jpg")
        self.assertEqual(len(images), 2)

    def test_subtype_priority_and_source_matching(self):
        self.assertGreater(scraper.category_priority("gaming-headset-wireless"),
                           scraper.category_priority("headset"))
        self.assertTrue(scraper.source_name_matches(
            "HEADSET NUBWO X1", "Wireless Headset",
            "HEADSET NUBWO X1", "Headset"))
        self.assertFalse(scraper.source_name_matches(
            "CPU INTEL 14700", "CPU", "HEADSET NUBWO X1", "Headset"))

    def test_explicit_microphone_category_can_be_saved(self):
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
        """)
        matcher = scraper.core.SmartMatcher(conn.cursor())
        created = scraper.core.upsert_product(conn.cursor(), matcher, {
            "name": "MICROPHONE TEST M1", "category": "Microphone",
            "store": "advice", "price": 500, "full_catalog": True,
            "source_code": "A1234567",
            "url": "https://www.advice.co.th/product/gaming-microphone/"
                   "gaming-microphone/microphone-test-m1",
            "description": "Connector: USB", "img_url": "https://img.example/m1.jpg",
        })
        self.assertTrue(created)
        self.assertEqual(conn.execute("SELECT product_id FROM products").fetchone()[0],
                         "adv_A1234567")
        conn.close()


if __name__ == "__main__":
    unittest.main()
