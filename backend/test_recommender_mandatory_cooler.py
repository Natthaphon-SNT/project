"""Regression tests for mandatory CPU cooling and severity-based scoring."""
import unittest
from unittest.mock import patch

import recommender as rec
import scoring_engine as scoring


def candidate(product_id: str, category: str, name: str, price: int,
              specs: str = "") -> dict:
    return {
        "product_id": product_id,
        "category": category,
        "name": name,
        "price": price,
        "prices": {"advice": price},
        "urls": {},
        "url": "",
        "specs": specs,
    }


class MandatoryCoolerTests(unittest.TestCase):
    def test_cpu_without_stock_cooler_adds_socket_matched_cooler_and_price(self):
        candidates = [
            candidate(
                "cpu-9950x", "CPU", "AMD RYZEN 9 9950X AM5", 20_000,
                "CPU Cooler: No\nTDP: 170 W",
            ),
            candidate("mb-am5", "Mainboard", "MAINBOARD X870 AM5 ATX DDR5", 10_000),
            candidate("ram-ddr5", "RAM", "RAM DDR5 64GB", 8_000),
            candidate("gpu-4060", "GPU", "GEFORCE RTX 4060 8GB", 15_000),
            candidate("ssd-1tb", "SSD", "SSD NVME 1TB", 3_000),
            candidate("psu-850", "PSU", "POWER SUPPLY 850W", 4_000),
            candidate("case-atx", "Case", "ATX CASE", 3_000),
            candidate(
                "cooler-am5", "Liquid Cooler", "AIO LIQUID COOLER 360 AM5", 5_000,
                "CPU Socket Support: AM5\nRadiator Size: 360 mm",
            ),
        ]

        builds = rec.top3_builds(candidates, 100_000, "ai")

        self.assertTrue(builds)
        selected = builds[0]
        parts_by_type = {part["type"]: part for part in selected["parts"]}
        self.assertIn("Cooler", parts_by_type)
        self.assertEqual(parts_by_type["Cooler"]["product_id"], "cooler-am5")
        self.assertEqual(
            selected["total_price"],
            sum(part["price"] for part in selected["parts"]),
        )
        self.assertEqual(selected["total_price"], 68_000)


class CompatibilitySeverityTests(unittest.TestCase):
    @staticmethod
    def passing_checks(except_rule: int) -> list[dict]:
        return [
            {"rule": f"R{number} passing rule", "severity": "PASS", "ok": True}
            for number in range(1, 9) if number != except_rule
        ]

    def test_r1_critical_failure_caps_score_with_every_other_rule_passing(self):
        checks = self.passing_checks(except_rule=1)
        checks.append({
            "rule": "R1 CPU ↔ Mainboard Socket",
            "severity": "ERROR",
            "score_severity": "critical",
            "ok": False,
        })

        self.assertLessEqual(scoring.score_compatibility({"checks": checks}), 50)

    def test_r8_critical_failure_caps_score_with_every_other_rule_passing(self):
        checks = self.passing_checks(except_rule=8)
        checks.append({
            "rule": "R8 GPU ↔ PSU Power Connector",
            "severity": "UNKNOWN",
            "score_severity": "critical",
            "ok": False,
            "required_connectors": {"12VHPWR": 1},
            "available_connectors": {"PCIe 8-pin": 4},
        })

        self.assertLessEqual(scoring.score_compatibility({"checks": checks}), 50)

    def test_recommend_mode_caps_real_r8_connector_mismatch(self):
        candidates = [
            candidate("cpu", "CPU", "AMD RYZEN 5 7600 AM5", 7_000, "CPU Cooler: Yes"),
            candidate("mb", "Mainboard", "MAINBOARD B650 AM5 ATX DDR5", 6_000),
            candidate("ram", "RAM", "RAM DDR5 32GB 6000MHz", 4_000),
            candidate(
                "gpu", "GPU", "GEFORCE RTX 5070 12GB 1 x 12VHPWR", 30_000,
                "Power Connectors: 1 x 12VHPWR",
            ),
            candidate("ssd", "SSD", "SSD NVME 1TB", 3_000),
            candidate(
                "psu", "PSU", "POWER SUPPLY 850W 4 x PCIe 8-pin", 5_000,
                "Power Connectors: 4 x PCIe 8-pin",
            ),
            candidate("case", "Case", "ATX CASE", 3_000),
        ]

        with patch.object(rec, "select_candidates", return_value=candidates):
            result = rec.recommend_without_provider(
                None, "แนะนำคอมเล่นเกมงบ 100,000 บาท", reason="test"
            )

        alternative = result["alternatives"][0]
        r8 = next(check for check in alternative["compat"]["checks"]
                  if check["rule"].startswith("R8"))
        self.assertEqual(r8["score_severity"], "critical")
        self.assertLessEqual(alternative["breakdown"]["compatibility"], 50)


class BudgetFitFallbackTests(unittest.TestCase):
    def test_ram_is_downgraded_before_gpu_or_ssd_to_fit_budget(self):
        candidates = [
            candidate("cpu", "CPU", "AMD RYZEN 5 7600 AM5", 10_000, "CPU Cooler: Yes"),
            candidate("mb", "Mainboard", "MAINBOARD B650 AM5 ATX DDR5", 7_000),
            candidate("ram-128", "RAM", "RAM DDR5 128GB 6000MHz", 9_000),
            candidate("ram-64", "RAM", "RAM DDR5 64GB 6000MHz", 6_000),
            candidate("ram-32", "RAM", "RAM DDR5 32GB 6000MHz", 4_000),
            candidate("gpu", "GPU", "GEFORCE RTX 4060 8GB", 15_000),
            candidate("ssd", "SSD", "SSD NVME 1TB", 4_000),
            candidate("psu", "PSU", "POWER SUPPLY 650W", 4_000),
            candidate("case", "Case", "ATX CASE", 2_000),
        ]

        builds = rec.top3_builds(candidates, 50_000, "ai")

        self.assertTrue(builds)
        selected = builds[0]
        ram = next(part for part in selected["parts"] if part["type"] == "RAM")
        self.assertEqual(ram["product_id"], "ram-64")
        self.assertLessEqual(selected["total_price"], 50_000)
        self.assertEqual(selected["budget_adjustments"][0]["category"], "RAM")
        result = rec._scored_recommendation_result(
            builds, "แนะนำคอมสำหรับ AI งบ 50,000 บาท"
        )
        self.assertIn("ปรับ RAM จาก 128GB เป็น 64GB", result["ranking_explanation"])

    def test_3d_floor_keeps_32gb_dual_channel_and_downgrades_later_parts(self):
        query = "3D workload, budget 30,000-50,000฿"
        self.assertEqual(rec.detect_budget_thb(query), 50_000)
        self.assertEqual(rec.detect_use_case(query), "3d")
        candidates = [
            candidate("cpu", "CPU", "AMD RYZEN 9 9950X AM5", 12_000,
                      "CPU Cooler: No\nTDP: 170 W"),
            candidate("mb", "Mainboard", "MAINBOARD B650 AM5 ATX DDR5", 8_000),
            candidate("ram-128", "RAM", "RAM DDR5 128GB 6000MHz (64x2)", 8_000),
            candidate("ram-64", "RAM", "RAM DDR5 64GB 6000MHz (32x2)", 6_000),
            candidate("ram-32", "RAM", "RAM DDR5 32GB 6000MHz (16x2)", 4_000),
            candidate("ram-16", "RAM", "RAM DDR5 16GB 6000MHz (8x2)", 2_000),
            candidate("ram-8", "RAM", "RAM DDR5 8GB 6000MHz (8x1)", 1_000),
            candidate("gpu-high", "GPU", "GEFORCE RTX 4060 8GB", 12_000),
            candidate("gpu-low", "GPU", "GEFORCE RTX 3050 8GB", 9_000),
            candidate("ssd-1tb", "SSD", "SSD NVME 1TB", 6_000),
            candidate("ssd-500", "SSD", "SSD NVME 500GB", 3_000),
            candidate("psu", "PSU", "POWER SUPPLY 850W", 5_000),
            candidate("case", "Case", "ATX CASE", 4_000),
            candidate(
                "cooler-low", "Air Cooler", "CPU AIR COOLER BASIC AM5", 1_000,
                "Socket Support: AM5\nSingle Tower\nHeatsink Height: 145 mm",
            ),
            candidate(
                "cooler-medium", "Air Cooler", "CPU AIR COOLER DUAL TOWER AM5", 3_000,
                "Socket Support: AM5\nDual Tower\nHeatsink Height: 158 mm",
            ),
        ]

        with patch.object(rec, "select_candidates", return_value=candidates):
            result = rec.recommend_without_provider(None, query, reason="test")

        selected = result["alternatives"][0]
        ram = next(part for part in selected["parts"] if part["type"] == "RAM")
        parsed_ram = rec.sp.parse_part("RAM", ram["name"])
        self.assertGreaterEqual(parsed_ram["capacity_gb"], 32)
        self.assertTrue(parsed_ram["dual_channel"])
        self.assertNotEqual(ram["product_id"], "ram-16")
        self.assertNotEqual(ram["product_id"], "ram-8")
        self.assertLessEqual(selected["total_price"], 50_000)
        self.assertEqual(next(part for part in selected["parts"]
                              if part["type"] == "GPU")["product_id"], "gpu-low")
        self.assertIn("ปรับ cooler เป็นรุ่นที่ระบายความร้อนแรงขึ้น", result["ranking_explanation"])


class DowngradeExecutionTests(unittest.TestCase):
    def test_gpu_downgrade_rechecks_r3_with_replacement_psu_requirement(self):
        candidates = [
            candidate("cpu", "CPU", "AMD RYZEN 5 7600 AM5", 8_000, "CPU Cooler: Yes"),
            candidate("mb", "Mainboard", "MAINBOARD B650 AM5 ATX DDR5", 6_000),
            candidate("ram", "RAM", "RAM DDR5 16GB 6000MHz (8x2)", 3_000),
            candidate("gpu-old", "GPU", "GEFORCE RTX 3070 8GB", 20_000,
                      "Recommended PSU: 650 W"),
            candidate("gpu-new", "GPU", "GEFORCE GTX 1050 TI 4GB", 10_000,
                      "PSU Require 350w"),
            candidate("ssd", "SSD", "SSD NVME 1TB", 3_000),
            candidate("psu", "PSU", "POWER SUPPLY 750W", 4_000),
            candidate("case", "Case", "ATX CASE", 2_000),
        ]

        built = rec.assemble_build(candidates, 42_000, "work", alloc={"GPU": .48})
        r3 = next(check for check in built["post_downgrade_compat"]["checks"]
                  if check["rule"] == "R3 PSU Wattage")

        self.assertEqual(built["picked"]["GPU"]["product_id"], "gpu-new")
        self.assertEqual(r3["severity"], "PASS")
        self.assertEqual(r3["required_watt"], 350)
        self.assertEqual(built["need_watt"], r3["required_watt"])
        self.assertEqual(built["parsed"][3]["name"], "GEFORCE GTX 1050 TI 4GB")

    def test_work_ram_above_floor_downgrades_before_gpu_or_ssd(self):
        candidates = [
            candidate("cpu", "CPU", "AMD RYZEN 5 7600 AM5", 8_000, "CPU Cooler: Yes"),
            candidate("mb", "Mainboard", "MAINBOARD B650 AM5 ATX DDR5", 6_000),
            candidate("ram-32", "RAM", "RAM DDR5 32GB 6000MHz (16x2)", 5_000),
            candidate("ram-16", "RAM", "RAM DDR5 16GB 5600MHz (8x2)", 3_000),
            candidate("gpu-high", "GPU", "GEFORCE RTX 4060 8GB", 10_000),
            candidate("gpu-low", "GPU", "GEFORCE RTX 3050 8GB", 8_000),
            candidate("ssd-1tb", "SSD", "SSD NVME 1TB", 3_000),
            candidate("ssd-500", "SSD", "SSD NVME 500GB", 2_000),
            candidate("psu", "PSU", "POWER SUPPLY 650W", 4_000),
            candidate("case", "Case", "ATX CASE", 2_000),
        ]

        built = rec.assemble_build(candidates, 37_751, "work", alloc={"GPU": .27})
        ram = rec.sp.parse_part("RAM", built["picked"]["RAM"]["name"])

        self.assertEqual(rec.ram_floor_gb("work"), 16)
        self.assertEqual(built["picked"]["RAM"]["product_id"], "ram-16")
        self.assertEqual(ram["capacity_gb"], 16)
        self.assertTrue(ram["dual_channel"])
        self.assertEqual(built["picked"]["GPU"]["product_id"], "gpu-high")
        self.assertEqual(built["picked"]["SSD"]["product_id"], "ssd-1tb")
        self.assertEqual([step["category"] for step in built["budget_adjustments"]], ["RAM"])
        self.assertLessEqual(sum(part["price"] for part in built["picked"].values()), 37_751)


class CoolerUpgradeTests(unittest.TestCase):
    @staticmethod
    def _intel_build(cpu_tdp: int = 170) -> list[dict]:
        return [
            candidate("cpu", "CPU", "INTEL CORE I7-14700KF LGA1700", 14_000,
                      f"TDP: {cpu_tdp} W\nCPU Cooler: No"),
            candidate("mb", "Mainboard", "MAINBOARD Z790 LGA1700 ATX DDR5", 7_000),
            candidate("ram", "RAM", "RAM DDR5 32GB 6000MHz (16x2)", 5_000),
            candidate("gpu-fast", "GPU", "GEFORCE RTX 4060 8GB", 13_000),
            candidate("gpu-cheap", "GPU", "GEFORCE RTX 3050 8GB", 9_000),
            candidate("ssd", "SSD", "SSD NVME 1TB", 3_000),
            candidate("psu", "PSU", "POWER SUPPLY 850W", 5_000),
            candidate("case", "Case", "ATX CASE", 3_000),
            candidate("mugen", "Air Cooler", "CPU AIR COOLER SCYTHE MUGEN 6 LGA1700", 1_000,
                      "Socket Support: LGA1700\nDual Tower\nHeatsink Height: 158 mm\nRated TDP: 160 W"),
            candidate("aio-240", "Liquid Cooler", "AIO LIQUID COOLER 240 LGA1700", 3_500,
                      "Socket Support: LGA1700"),
            candidate("aio-360", "Liquid Cooler", "AIO LIQUID COOLER 360 LGA1700", 8_000,
                      "Socket Support: LGA1700"),
        ]

    def test_tight_budget_retries_240mm_after_gpu_downgrade(self):
        candidates = self._intel_build()
        builds = rec.top3_builds(candidates, 50_000, "3d")

        self.assertTrue(builds)
        selected = builds[0]
        parts = {part["type"]: part for part in selected["parts"]}
        self.assertEqual(parts["Cooler"]["product_id"], "aio-240")
        self.assertEqual(parts["GPU"]["product_id"], "gpu-cheap")
        self.assertLessEqual(selected["total_price"], 50_000)
        self.assertEqual(rec.sp.parse_part("RAM", parts["RAM"]["name"])["capacity_gb"], 32)
        r4 = next(check for check in selected["compat"]["checks"]
                  if check["rule"] == "R4 CPU Cooler TDP")
        self.assertEqual(r4["severity"], "PASS")
        built = rec.assemble_build(candidates, 50_000, "3d")
        self.assertEqual(
            built["post_downgrade_compat"],
            rec.ce.check_build(built["parsed"], 50_000),
        )
        result = rec._scored_recommendation_result(
            builds, "3D workload, budget 30,000-50,000฿"
        )
        self.assertIn(
            "ปรับ cooler เป็นรุ่นที่ระบายความร้อนแรงขึ้นเพื่อรองรับ CPU ตัวนี้ "
            "และปรับ GPU ลงหนึ่งขั้นเพื่อให้อยู่ในงบ",
            result["ranking_explanation"],
        )

    def test_roomy_budget_still_selects_high_tier_aio(self):
        candidates = self._intel_build(cpu_tdp=250)
        built = rec.assemble_build(candidates, 100_000, "3d")
        selected = rec.top3_builds(candidates, 100_000, "3d")[0]

        self.assertEqual(built["picked"]["Cooler"]["product_id"], "aio-360")
        self.assertEqual(
            next(part for part in selected["parts"] if part["type"] == "Cooler")["product_id"],
            "aio-360",
        )
        self.assertFalse(built["budget_adjustments"])
        self.assertEqual(
            next(check for check in selected["compat"]["checks"]
                 if check["rule"] == "R4 CPU Cooler TDP")["severity"],
            "PASS",
        )

    def test_no_upgrade_fits_budget_keeps_original_r4_warning(self):
        candidates = self._intel_build()
        # Even after the one available GPU downgrade, both AIOs exceed 50,000.
        for item in candidates:
            if item["product_id"] == "aio-240":
                item["price"] = 10_000
            elif item["product_id"] == "aio-360":
                item["price"] = 14_000
            elif item["product_id"] == "gpu-cheap":
                item["price"] = 12_000

        selected = rec.top3_builds(candidates, 50_000, "3d")[0]
        self.assertEqual(
            next(part for part in selected["parts"] if part["type"] == "Cooler")["product_id"],
            "mugen",
        )
        self.assertFalse(selected["component_adjustments"])
        self.assertEqual(
            next(check for check in selected["compat"]["checks"]
                 if check["rule"] == "R4 CPU Cooler TDP")["severity"],
            "WARNING",
        )

    def test_no_passing_cooler_skips_upgrade_loop(self):
        candidates = [item for item in self._intel_build()
                      if item["product_id"] not in {"aio-240", "aio-360"}]
        built = rec.assemble_build(candidates, 50_000, "3d")
        self.assertEqual(built["picked"]["Cooler"]["product_id"], "mugen")

    def test_r4_failure_upgrades_to_cheapest_passing_socket_matched_cooler(self):
        candidates = [
            candidate("cpu", "CPU", "AMD RYZEN 9 9950X AM5", 20_000,
                      "CPU Cooler: No\nTDP: 170 W"),
            candidate("mb", "Mainboard", "MAINBOARD X870 AM5 ATX DDR5", 10_000),
            candidate("ram", "RAM", "RAM DDR5 64GB 6000MHz (32x2)", 8_000),
            candidate("gpu", "GPU", "GEFORCE RTX 4060 8GB", 15_000),
            candidate("ssd", "SSD", "SSD NVME 1TB", 3_000),
            candidate("psu", "PSU", "POWER SUPPLY 850W", 5_000),
            candidate("case", "Case", "ATX CASE", 3_000),
            candidate(
                "cooler-low", "Air Cooler", "CPU AIR COOLER BASIC AM5", 3_500,
                "Socket Support: AM5\nSingle Tower\nHeatsink Height: 145 mm",
            ),
            candidate(
                "cooler-medium", "Air Cooler", "CPU AIR COOLER DUAL TOWER AM5", 5_000,
                "Socket Support: AM5\nDual Tower\nHeatsink Height: 158 mm",
            ),
            candidate(
                "cooler-high", "Liquid Cooler", "AIO LIQUID COOLER 360 AM5", 8_000,
                "Socket Support: AM5",
            ),
        ]

        built = rec.assemble_build(candidates, 100_000, "3d")

        self.assertEqual(built["picked"]["Cooler"]["product_id"], "cooler-medium")
        r4 = next(check for check in rec.ce.check_build(built["parsed"])["checks"]
                  if check["rule"] == "R4 CPU Cooler TDP")
        self.assertEqual(r4["severity"], "PASS")
        self.assertIn(
            "ปรับ cooler เป็นรุ่นที่ระบายความร้อนแรงขึ้นเพื่อรองรับ CPU ตัวนี้",
            [item["message"] for item in built["component_adjustments"]],
        )


if __name__ == "__main__":
    unittest.main()
