import unittest

import full_scraper as scraper


class ProductMatchingTests(unittest.TestCase):
    def test_psu_wattage_conflict_never_merges(self):
        self.assertFalse(scraper.is_same_product(
            "PSU THERMALTAKE SMART BX1 650W",
            "PSU",
            "POWER SUPPLY THERMALTAKE SMART BX1 750W",
            "PSU",
        ))

    def test_gpu_board_brand_conflict_never_merges(self):
        self.assertFalse(scraper.is_same_product(
            "VGA ASUS TURBO RADEON AI PRO R9700 32GB",
            "GPU",
            "VGA POWERCOLOR RADEON AI PRO R9700 32GB",
            "GPU",
        ))

    def test_gpu_model_conflict_never_merges(self):
        self.assertFalse(scraper.is_same_product(
            "VGA ASUS PRIME RADEON RX 9060 XT 8GB",
            "GPU",
            "VGA ASUS TURBO RADEON AI PRO R9700 32GB",
            "GPU",
        ))

    def test_mainboard_sibling_model_conflict_never_merges(self):
        self.assertFalse(scraper.is_same_product(
            "MAINBOARD GIGABYTE H610M S2H V2 DDR4",
            "Mainboard",
            "MAINBOARD GIGABYTE H610M K GEN5 DDR4",
            "Mainboard",
        ))

    def test_same_retail_model_can_still_merge(self):
        self.assertTrue(scraper.is_same_product(
            "MONITOR AOC 22B40HM 21.45 120Hz",
            "Monitor",
            "Monitor AOC 22B40HM/67 21.45 Inch FHD 120Hz",
            "Monitor",
        ))

    def test_store_url_model_conflict_is_rejected(self):
        self.assertTrue(scraper.source_url_conflicts(
            "VGA ASUS PRIME GEFORCE RTX 5050 OC EDITION 8GB",
            "https://www.jib.co.th/web/product/readProduct/1/VGA-ASUS-DUAL-GEFORCE-RTX-5050-8GB",
            "GPU",
        ))

    def test_store_url_matching_model_is_allowed(self):
        self.assertFalse(scraper.source_url_conflicts(
            "POWER SUPPLY CORSAIR RM850E 850W",
            "https://www.ihavecpu.com/product/1/psu-corsair-rm850e-850w",
            "PSU",
        ))

    def test_detail_cookie_banner_is_rejected(self):
        self.assertFalse(scraper.detail_description_is_relevant(
            "PSU GIGABYTE GP-P650SS ICE 650W", 
            "เราใช้คุกกี้เพื่อเพิ่มประสบการณ์การใช้งานและการยอมรับข้อมูลส่วนบุคคล",
            "PSU",
        ))

    def test_detail_title_only_is_rejected_but_specs_are_allowed(self):
        name = "MAINBOARD GIGABYTE B760M D3HP DDR4"
        self.assertFalse(scraper.detail_description_is_relevant(name, name, "Mainboard"))
        self.assertTrue(scraper.detail_description_is_relevant(
            name,
            "CPU Socket\tLGA 1700\nChipset\tIntel B760\nMemory Type\tDDR4\nForm Factor\tMicro-ATX",
            "Mainboard",
        ))


if __name__ == "__main__":
    unittest.main()
