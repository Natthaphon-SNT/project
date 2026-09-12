import json
import sqlite3
import unittest

import full_scraper as scraper


class ScraperSourceDataTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
