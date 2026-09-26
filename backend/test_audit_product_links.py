import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

import audit_product_links as links


class LinkAuditTests(unittest.IsolatedAsyncioTestCase):
    def test_retailer_paths_are_scoped(self):
        self.assertTrue(links.retailer_url_is_valid(
            "ihavecpu", "https://www.ihavecpu.com/product/10962/example"))
        self.assertFalse(links.retailer_url_is_valid(
            "ihavecpu", "https://malicious.example/product/10962/example"))
        self.assertTrue(links.retailer_url_is_valid(
            "jib", "https://www.jib.co.th/web/product/readProduct/123/45/example"))

    async def test_apply_retires_only_confirmed_missing_offer(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "shop.db"
            conn = sqlite3.connect(db_path)
            conn.execute("""CREATE TABLE products (
                product_id TEXT, p_name TEXT, p_price INTEGER,
                price_advice INTEGER, price_jib INTEGER, price_ihavecpu INTEGER,
                url_advice TEXT, url_jib TEXT, url_ihavecpu TEXT, updated_at TEXT
            )""")
            conn.execute("""INSERT INTO products VALUES
                ('psu1','PSU',5990,0,6500,5990,'',
                 'https://www.jib.co.th/web/product/readProduct/1/2/psu',
                 'https://ihavecpu.com/product/49964/psu','')""")
            conn.commit()
            conn.close()
            with patch.object(links, "check_link", new=AsyncMock(return_value="missing")):
                await links.audit(db_path, ["ihavecpu"], 0, "psu1", 1, True)
            conn = sqlite3.connect(db_path)
            row = conn.execute("""SELECT p_price, price_jib, price_ihavecpu,
                url_ihavecpu FROM products WHERE product_id='psu1'""").fetchone()
            conn.close()
            self.assertEqual(row, (6500, 6500, 0, ""))


if __name__ == "__main__":
    unittest.main()
