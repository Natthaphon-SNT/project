import unittest
import spec_parser as sp
import compat_engine as ce


class PowerCompatibilityTests(unittest.TestCase):
    def build(self, gpu, psu="450W", specs=""):
        return [sp.parse_part("CPU", "AMD RYZEN 5 5500"),
                sp.parse_part("GPU", gpu, specs), sp.parse_part("PSU", "POWER SUPPLY " + psu)]

    def power(self, parts):
        return ce.check_psu_watt(parts)

    def test_5050_requires_550_not_board_draw(self):
        parts = self.build("ASUS PRIME GEFORCE RTX 5050 OC")
        result = self.power(parts)
        self.assertEqual(parts[1]["tdp"], 130)
        self.assertEqual(result["required_watt"], 550)
        self.assertEqual(result["severity"], "ERROR")
        self.assertFalse(result["ok"])
        self.assertTrue(any(s["value"] == 550 and 'nvidia.com' in s["url"] for s in result["sources"]))
        self.assertEqual(self.power(self.build("RTX 5050", "550W"))["severity"], "PASS")

    def test_screenshot_pro5000_is_distinct(self):
        parts = self.build("LEADTEK NVIDIA RTX PRO 5000 BLACKWELL - 48GB GDDR7 WITH ECC")
        self.assertEqual(parts[1]["tdp"], 300)
        self.assertNotIn("recommended_psu_watt", parts[1])
        result = self.power(parts)
        self.assertEqual(result["severity"], "ERROR")
        self.assertEqual(result["required_watt"], 557)
        self.assertIsNone(result["manufacturer_min_watt"])

    def test_unknown_cannot_pass(self):
        for parts in (self.build("Unknown GPU"), self.build("RTX 5050", "unknown"),
                      [sp.parse_part("GPU", "RTX 5050"), sp.parse_part("PSU", "550W")],
                      [sp.parse_part("CPU", "Ryzen 5 5500")], []):
            result = ce.check_build(parts)
            self.assertNotEqual(result["overall"], "ok")
            for check in result["checks"]:
                if check["severity"] == "UNKNOWN":
                    self.assertFalse(check["ok"])

    def test_board_specs_raise_requirement_and_keep_consumption_separate(self):
        specs = 'Recommended PSU:650W\nPower Consumption: 140 W\nSource URL: https://example.com/board'
        parts = self.build("RTX 5050", "550W", specs)
        self.assertEqual(parts[1]["tdp"], 140)
        self.assertEqual(parts[1]["recommended_psu_watt"], 650)
        self.assertNotIn("watt", parts[1])
        self.assertEqual(self.power(parts)["severity"], "ERROR")
        self.assertTrue(any(s["value"] == 650 for s in parts[1]["power_sources"]))

    def test_rail_power_not_total_psu_rating(self):
        result = sp.parse_part("PSU", "PSU 450W", '+12V rail: 350 W\nOutput voltage: 230 V')
        self.assertEqual(result["watt"], 450)

    def test_desktop_reference_does_not_match_other_models(self):
        for name in ('RTX 50500', 'RTX 5050 Laptop', 'RTX PRO 5000 Ada', 'RTX 5050 Ti'):
            self.assertNotIn('recommended_psu_watt', sp.parse_gpu(name))

    def test_cpu_draw_can_exceed_manufacturer_baseline(self):
        parts = self.build('RTX 5050', '550W')
        parts[0]['tdp'] = 300
        result = self.power(parts)
        self.assertEqual(result['required_watt'], 638)
        self.assertEqual(result['severity'], 'ERROR')


if __name__ == '__main__':
    unittest.main()
