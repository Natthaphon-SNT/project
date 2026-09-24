import unittest

import compat_engine as ce
import spec_parser as sp


class CaseFormFactorTests(unittest.TestCase):
    def test_frame_4000d_supports_all_four_sizes(self):
        name = "CASE CORSAIR FRAME 4000D TEMPERED GLASS (WHITE)(E-ATX)"
        details = "Mainboard Support: E-ATX, ATX, Micro-ATX, Mini-ITX"
        case = sp.parse_part("Case", name, details)
        self.assertEqual(case["supports_ff"], ["E-ATX", "ATX", "mATX", "ITX"])
        self.assertEqual(case["form_factor"], "E-ATX")
        board = sp.parse_part("Mainboard", "MAINBOARD ASUS X670E E-ATX AM5")
        self.assertEqual(board["form_factor"], "E-ATX")
        self.assertEqual(ce.check_case_ff([case, board])["severity"], "PASS")

    def test_saved_support_list_does_not_change_case_size(self):
        case = sp.parse_part(
            "Case", "CASE CORSAIR FRAME 4000D (E-ATX)",
            "Supported Motherboard: E-ATX, ATX, mATX, ITX",
        )
        self.assertEqual(case["form_factor"], "E-ATX")
        self.assertEqual(case["supports_ff"], ["E-ATX", "ATX", "mATX", "ITX"])

    def test_unspecified_case_support_remains_unknown(self):
        case = sp.parse_part("Case", "CASE MONTECH X3 MESH")
        board = sp.parse_part("Mainboard", "MAINBOARD ASUS B650 ATX AM5")
        self.assertIsNone(case["supports_ff"])
        self.assertEqual(ce.check_case_ff([case, board])["severity"], "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
