"""Heuristic CPU-cooler capacity estimation and compatibility integration."""
import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch

from compat_engine import check_build
from spec_parser import estimate_cooler_tdp_tier, parse_part
import recommender


class CoolerTdpTierTests(unittest.TestCase):
    def test_montech_dual_tower_spec_is_medium(self):
        result = estimate_cooler_tdp_tier(
            "CPU COOLER MONTECH NX600 ARGB WHITE",
            {
                "category": "Air Cooler",
                "tower_count": 2,
                "heatsink_height_mm": 158,
            },
        )

        self.assertEqual(result["cooler_type"], "air")
        self.assertEqual(result["tdp_tier"], "medium")
        self.assertEqual(result["estimated_watt_range"], (150, 180))
        self.assertEqual(result["confidence"], "spec")

    def test_ocypus_l36_name_is_360mm_high_tier(self):
        result = estimate_cooler_tdp_tier(
            "LIQUID COOLING OCYPUS DELTA L36 ELITE ARGB WHITE", {}
        )

        self.assertEqual(result["cooler_type"], "aio")
        self.assertEqual(result["radiator_mm"], 360)
        self.assertEqual(result["tdp_tier"], "high")
        self.assertEqual(result["estimated_watt_range"], (200, 280))
        self.assertEqual(result["confidence"], "name")

    def test_corsair_bare_360_name_is_high_tier(self):
        result = estimate_cooler_tdp_tier(
            "CORSAIR iCUE LINK TITAN II 360 RX LCD", {}
        )

        self.assertEqual(result["cooler_type"], "aio")
        self.assertEqual(result["radiator_mm"], 360)
        self.assertEqual(result["tdp_tier"], "high")
        self.assertEqual(result["confidence"], "name")

    def test_estimated_range_warns_when_cpu_tdp_exceeds_maximum(self):
        cpu = parse_part("CPU", "Test CPU")
        cpu["tdp"] = 300
        cooler = parse_part(
            "Liquid Cooler", "LIQUID COOLING OCYPUS DELTA L36 ELITE ARGB WHITE"
        )

        result = check_build([cpu, cooler])
        check = next(item for item in result["checks"] if item["rule"] == "R4 CPU Cooler TDP")

        self.assertEqual(check["severity"], "WARNING")
        self.assertIn("cooler นี้อาจไม่พอสำหรับ CPU 300W", check["detail"])

    def test_unknown_cooler_keeps_original_skip_warning(self):
        result = estimate_cooler_tdp_tier("CPU COOLER UNKNOWN MODEL", {})

        self.assertIsNone(result["tdp_tier"])
        self.assertEqual(result["confidence"], "unknown")
        self.assertEqual(
            result["skip_reason"],
            "ข้ามการตรวจ (ประเมิน TDP/cooler rating ไม่ได้จากชื่อสินค้า)",
        )

    def test_aio_fan_geometry_is_used_when_name_has_no_size(self):
        result = estimate_cooler_tdp_tier(
            "AIO COOLER MODEL X",
            {"category": "Liquid Cooler", "fan_count": 3, "fan_size_mm": 120},
        )

        self.assertEqual(result["radiator_mm"], 360)
        self.assertEqual(result["tdp_tier"], "high")
        self.assertEqual(result["confidence"], "spec")

    def test_compare_mode_includes_deterministic_cooler_checks(self):
        llm_response = json.dumps({
            "spec1Name": "Build 1",
            "spec2Name": "Build 2",
            "winner": "tie",
            "verdict": "Comparable",
            "categories": [],
            "spec1Pros": [],
            "spec2Pros": [],
            "recommendation": "Review compatibility warnings",
        })
        spec = (
            "CPU AMD RYZEN 9 7950X AM5\n"
            "Liquid Cooler LIQUID COOLING OCYPUS DELTA L36 ELITE ARGB WHITE"
        )

        with patch.object(recommender, "llm_chat", new_callable=AsyncMock,
                          return_value=llm_response):
            raw = asyncio.run(recommender.compare_specs(spec, spec, api_key="test"))
        result = json.loads(raw)

        self.assertIn("compatibility", result)
        checks = result["compatibility"]["spec1"]["checks"]
        cooler_check = next(item for item in checks if item["rule"] == "R4 CPU Cooler TDP")
        self.assertEqual(cooler_check["tdp_tier"], "high")
        self.assertEqual(cooler_check["severity"], "PASS")

    def test_recommend_mode_preserves_liquid_category_for_tier_check(self):
        candidates = [
            {
                "product_id": "cpu-1", "category": "CPU",
                "name": "AMD RYZEN 9 7950X AM5", "price": 18000,
                "prices": {"jib": 18000}, "urls": {}, "url": "", "specs": "",
            },
            {
                "product_id": "cooler-1", "category": "Liquid Cooler",
                "name": "CORSAIR iCUE LINK TITAN II 360 RX LCD", "price": 9000,
                "prices": {"jib": 9000}, "urls": {}, "url": "", "specs": "",
            },
        ]
        result = recommender.build_final_result(
            {"parts": [
                {"type": "CPU", "product_id": "cpu-1"},
                {"type": "Liquid Cooler", "product_id": "cooler-1"},
            ]},
            candidates,
            budget=None,
            use_case="work",
        )

        cooler_check = next(
            item for item in result["compat"]["checks"]
            if item["rule"] == "R4 CPU Cooler TDP"
        )
        self.assertEqual(cooler_check["tdp_tier"], "high")
        self.assertEqual(cooler_check["severity"], "PASS")


if __name__ == "__main__":
    unittest.main()
