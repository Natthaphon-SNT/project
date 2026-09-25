"""Budget ranges must not turn a minimum into an upper limit."""
import unittest

import recommender as rec


class BudgetSemanticsTests(unittest.TestCase):
    def test_open_ended_thai_budget_is_not_a_ceiling(self):
        prompt = "Recommend a PC for gaming, budget 100,000 ฿ ขึ้นไป. Answer in Thai."
        self.assertEqual(rec.detect_budget_thb(prompt), 100_000)
        self.assertTrue(rec.budget_is_lower_bound(prompt))

    def test_bounded_budget_keeps_ceiling(self):
        self.assertFalse(rec.budget_is_lower_bound("gaming budget 50,000 - 100,000 ฿"))

    def test_result_does_not_flag_price_above_a_minimum(self):
        candidate = {
            "product_id": "cpu-1", "category": "CPU", "name": "CPU AMD AM5 RYZEN 7 7800X3D",
            "price": 100_660, "prices": {}, "urls": {}, "url": "", "specs": "",
        }
        proposal = {"parts": [{"type": "CPU", "product_id": "cpu-1"}]}
        result = rec.build_final_result(proposal, [candidate], 100_000, "gaming",
                                        budget_ceiling=False)
        self.assertFalse(any(c["rule"] == "R7 Budget" for c in result["compat"]["checks"]))


if __name__ == "__main__":
    unittest.main()
