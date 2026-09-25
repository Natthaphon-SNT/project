"""The displayed recommendation must be the first scored build, never an LLM build."""
import json
import unittest
from unittest.mock import AsyncMock, patch

import recommender as rec


def scored_build(index, total, score, availability):
    picked = {}
    candidates = []
    for category in rec.PC_CATEGORIES:
        price = total - 6000 if category == "Case" else 1000
        candidate = {
            "product_id": f"{index}-{category}", "category": category,
            "name": f"{category} test {index}", "price": price,
            "prices": {"jib": price}, "urls": {}, "url": "", "specs": "",
        }
        picked[category] = candidate
        candidates.append(candidate)
    built = {"picked": picked, "parsed": [{"variant": index}], "need_watt": 750}
    scores = {
        "score": score,
        "breakdown": {"performance": 70, "budget": 70, "compatibility": 90,
                      "preference": 70, "availability": availability},
        "compat": {"overall": "ok", "summary": "checked", "checks": []},
    }
    return built, scores, candidates


class ScoredRankingTests(unittest.TestCase):
    def _rank(self, totals, scores, availability, budget_ceiling=True):
        values = [scored_build(i, totals[i], scores[i], availability[i]) for i in range(4)]
        candidates = [c for _, _, rows in values for c in rows]
        with patch.object(rec, "assemble_build", side_effect=[v[0] for v in values]), \
             patch("scoring_engine.score_build", side_effect=[v[1] for v in values]):
            return rec.top3_builds(candidates, 100_000, "gaming", budget_ceiling=budget_ceiling)

    def test_in_budget_build_precedes_higher_scoring_overspend(self):
        ranked = self._rank([105_000, 99_000, 98_000, 101_000],
                            [95, 70, 80, 75], [70, 75, 40, 70])
        self.assertEqual(ranked[0]["parts"][0]["product_id"], "2-CPU")
        self.assertEqual(ranked[1]["parts"][0]["product_id"], "1-CPU")
        self.assertEqual(ranked[0]["total_price"], 98_000)

    def test_no_affordable_build_chooses_smallest_overrun(self):
        ranked = self._rank([105_000, 102_000, 101_000, 108_000],
                            [95, 70, 80, 75], [70, 70, 70, 70])
        self.assertEqual(ranked[0]["total_price"], 101_000)

    def test_open_ended_budget_prefers_build_at_or_above_floor(self):
        ranked = self._rank([95_000, 101_000, 99_000, 102_000],
                            [95, 75, 90, 70], [70, 70, 70, 70], budget_ceiling=False)
        self.assertEqual(ranked[0]["total_price"], 101_000)


class SingleSourceResultTests(unittest.IsolatedAsyncioTestCase):
    async def test_llm_cannot_change_parts_prices_or_totals(self):
        parts = [{"type": "CPU", "name": "Real CPU", "price": 101_000,
                  "product_id": "real-cpu", "reason": ""}]
        winner = {"parts": parts, "total_price": 101_000, "label": "Balanced",
                  "score": 80, "breakdown": {"availability": 40},
                  "compat": {"overall": "ok", "summary": "checked", "checks": []},
                  "compat_overall": "ok"}
        backup = {**winner, "parts": [{**parts[0], "product_id": "backup", "price": 99_000}],
                  "total_price": 99_000, "label": "Backup", "breakdown": {"availability": 80}}
        malicious = json.dumps({
            "parts": [{"name": "Invented GPU", "price": 1}],
            "totalBudget": "1 ฿", "summary": "รวม 1 บาท",
            "pros": ["ดีมาก"],
        }, ensure_ascii=False)
        with patch.object(rec, "select_candidates", return_value=[]), \
             patch.object(rec, "top3_builds", return_value=[winner, backup]), \
             patch.object(rec, "recommend_build", new_callable=AsyncMock, side_effect=AssertionError("LLM cannot pick parts")), \
             patch.object(rec, "llm_chat", new_callable=AsyncMock, return_value=malicious):
            result = await rec.recommend_with_alternatives(
                None, "gaming budget 100,000 ฿", api_key="test-key")
        self.assertIs(result["parts"], result["alternatives"][0]["parts"])
        self.assertEqual(result["parts"], parts)
        self.assertEqual(result["totalBudget"], "101,000 ฿ (ราคาจริงจากฐานข้อมูล)")
        self.assertIn("เกินงบ", result["summary"])
        self.assertTrue(any("หาซื้อได้ยาก" in item for item in result["warnings"]))
        self.assertEqual(result["pros"], ["ดีมาก"])

    async def test_provider_failure_still_returns_scored_build(self):
        parts = [{"type": "CPU", "name": "Real CPU", "price": 99_000,
                  "product_id": "real-cpu", "reason": ""}]
        winner = {"parts": parts, "total_price": 99_000, "label": "Balanced",
                  "score": 80, "breakdown": {"availability": 80},
                  "compat": {"overall": "ok", "summary": "checked", "checks": []},
                  "compat_overall": "ok"}
        with patch.object(rec, "select_candidates", return_value=[]), \
             patch.object(rec, "top3_builds", return_value=[winner]), \
             patch.object(rec, "llm_chat", new_callable=AsyncMock, side_effect=RuntimeError("offline")):
            result = await rec.recommend_with_alternatives(
                None, "gaming budget 100,000 ฿", api_key="test-key")
        self.assertIs(result["parts"], result["alternatives"][0]["parts"])
        self.assertTrue(result["_meta"]["provider_fallback"])

    async def test_minimum_budget_searches_above_floor_without_a_ceiling(self):
        parts = [{"type": "CPU", "name": "Real CPU", "price": 104_000,
                  "product_id": "real-cpu", "reason": ""}]
        winner = {"parts": parts, "total_price": 104_000, "label": "Balanced",
                  "score": 80, "breakdown": {"availability": 80},
                  "compat": {"overall": "ok", "summary": "checked", "checks": []},
                  "compat_overall": "ok"}
        with patch.object(rec, "select_candidates", return_value=[]) as select, \
             patch.object(rec, "top3_builds", return_value=[winner]) as rank:
            result = await rec.recommend_with_alternatives(
                None, "gaming budget 100,000 ฿ ขึ้นไป")
        self.assertEqual(select.call_args.args[1], 110_000)
        self.assertEqual(rank.call_args.kwargs["target_budget"], 110_000)
        self.assertFalse(any("เกินงบ" in warning for warning in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
