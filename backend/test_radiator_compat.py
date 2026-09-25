"""Radiator fit checks must use explicit case specifications, not fan sizes."""
import unittest

from compat_engine import check_build
from spec_parser import parse_part


CASE_SPECS = """Radiator Support
- Top : 280 / 360 / 420 mm
- Right : 280 / 360 / 420 mm
- Bottom : 280 / 360 / 420 mm
"""


class RadiatorCompatibilityTests(unittest.TestCase):
    def _check(self, cooler_name, case_specs=CASE_SPECS):
        parts = [
            parse_part("Case", "CASE HAVN HS 420 (BLACK) (E-ATX)", case_specs),
            parse_part("Liquid Cooler", cooler_name),
        ]
        result = check_build(parts)
        radiator = next(c for c in result["checks"] if c["rule"].startswith("R9"))
        return result, radiator

    def test_240mm_radiator_is_rejected_when_case_lists_other_sizes(self):
        result, radiator = self._check("CPU LIQUID COOLER ID COOLING SPACE SL240 BLACK")
        self.assertEqual(radiator["severity"], "ERROR")
        self.assertEqual(result["overall"], "error")

    def test_listed_360mm_radiator_passes(self):
        _, radiator = self._check("CPU LIQUID COOLER 360 BLACK")
        self.assertEqual(radiator["severity"], "PASS")

    def test_missing_case_spec_is_not_a_false_error(self):
        result, radiator = self._check("CPU LIQUID COOLER ID COOLING SPACE SL240 BLACK", "")
        self.assertEqual(radiator["severity"], "UNKNOWN")
        self.assertNotEqual(result["overall"], "error")

    def test_case_fan_sizes_are_not_treated_as_radiator_support(self):
        _, radiator = self._check(
            "CPU LIQUID COOLER ID COOLING SPACE SL240 BLACK",
            "Fan Support\n- Top : 3 x 120 mm\n- Bottom : 3 x 120 mm",
        )
        self.assertEqual(radiator["severity"], "UNKNOWN")

    def test_manufacturer_liquid_cooling_support_label(self):
        _, radiator = self._check(
            "CPU LIQUID COOLER ID COOLING SPACE SL240 BLACK",
            CASE_SPECS.replace("Radiator Support", "Liquid Cooling Support"),
        )
        self.assertEqual(radiator["severity"], "ERROR")

    def test_liquid_cooling_name_and_all_supported_sockets_are_recognized(self):
        cooler = parse_part(
            "Liquid Cooler",
            "LIQUID COOLING OCYPUS DELTA L36 ELITE ARGB WHITE",
            "CPU Socket Support: Intel : 1851, 1700, 1200, 1151, 1150, 1155 AMD : AM4, AM5",
        )
        self.assertTrue(cooler["is_cpu_cooler"])
        self.assertEqual(cooler["radiator_size_mm"], 360)
        self.assertIn("LGA1851", cooler["sockets"])
        self.assertIn("AM5", cooler["sockets"])

        result = check_build([
            parse_part("CPU", "INTEL CORE ULTRA 5 245K LGA1851"),
            cooler,
        ])
        socket_check = next(c for c in result["checks"] if c["rule"].startswith("R4S"))
        cooler_check = next(c for c in result["checks"] if c["rule"] == "R4 CPU Cooler TDP")
        self.assertEqual(socket_check["severity"], "PASS")
        self.assertEqual(cooler_check["severity"], "PASS")
        self.assertIn("LGA1851", socket_check["detail"])


if __name__ == "__main__":
    unittest.main()
