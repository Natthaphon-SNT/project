"""The displayed recommendation must be the first scored build, never an LLM build."""
import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch

import httpx

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
        # AI pros are merged on top of the deterministic default, not replacing it.
        self.assertEqual(result["pros"], [
            "สินค้า ราคา และผลตรวจความเข้ากันได้มาจากชุดเดียวกัน", "ดีมาก",
        ])
        self.assertEqual(result["_meta"]["llm_provider"], "google")
        self.assertEqual(result["_meta"]["requested_provider"], "google")

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
        # The reason must stay debuggable from the response alone.
        self.assertEqual(result["_meta"]["fallback_reason"], "RuntimeError: offline")

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

    def test_failure_reason_keeps_type_and_message_within_limit(self):
        self.assertEqual(
            rec.failure_reason(RuntimeError("Auth/Credits error (401): bad key")),
            "RuntimeError: Auth/Credits error (401): bad key",
        )
        # Long provider payloads must not bloat the response.
        reason = rec.failure_reason(ValueError("x" * 5_000))
        self.assertTrue(reason.startswith("ValueError: "))
        self.assertEqual(len(reason) - len("ValueError: "), rec.FAILURE_REASON_MAX_LEN)

    def test_timeout_reason_keeps_the_timeout_detail(self):
        parts = [{"type": "CPU", "name": "Real CPU", "price": 99_000,
                  "product_id": "real-cpu", "reason": ""}]
        winner = {"parts": parts, "total_price": 99_000, "label": "Balanced",
                  "score": 80, "breakdown": {"availability": 80},
                  "compat": {"overall": "ok", "summary": "checked", "checks": []},
                  "compat_overall": "ok"}
        with patch.object(rec, "select_candidates", return_value=[]), \
             patch.object(rec, "top3_builds", return_value=[winner]), \
             patch.object(rec, "llm_chat", new_callable=AsyncMock,
                          side_effect=httpx.ReadTimeout("provider timed out")):
            result = asyncio.run(rec.recommend_with_alternatives(
                None, "gaming budget 100,000 ฿", api_key="test-key"))
        self.assertTrue(result["_meta"]["provider_fallback"])
        self.assertIn("ReadTimeout", result["_meta"]["fallback_reason"])
        self.assertIn("provider timed out", result["_meta"]["fallback_reason"])

    def test_compat_check_records_enrichment_failure_reason(self):
        with patch.object(rec, "llm_chat", new_callable=AsyncMock,
                          side_effect=RuntimeError("Auth/Credits error (401): bad key")):
            result = asyncio.run(rec.compat_check_hybrid(
                "CPU AMD RYZEN 5 5600", api_key="test-key"))
        # The deterministic verdict must survive an enrichment failure...
        self.assertTrue(result["_engine"]["deterministic"])
        # ...and the reason must be visible in the response.
        self.assertTrue(result["_meta"]["provider_fallback"])
        self.assertIn("Auth/Credits error (401)", result["_meta"]["fallback_reason"])

    def _enrich(self, ai_payload, availability=80):
        """Run recommend_with_alternatives with a scripted AI explanation."""
        parts = [{"type": "CPU", "name": "Real CPU", "price": 99_000,
                  "product_id": "real-cpu", "reason": ""}]
        winner = {"parts": parts, "total_price": 99_000, "label": "Balanced",
                  "score": 80, "breakdown": {"availability": availability},
                  "compat": {"overall": "ok", "summary": "checked", "checks": []},
                  "compat_overall": "ok"}
        with patch.object(rec, "select_candidates", return_value=[]), \
             patch.object(rec, "top3_builds", return_value=[winner]), \
             patch.object(rec, "llm_chat", new_callable=AsyncMock,
                          return_value=json.dumps(ai_payload, ensure_ascii=False)):
            return asyncio.run(rec.recommend_with_alternatives(
                None, "gaming budget 100,000 ฿", api_key="test-key"))

    def test_merge_keeps_deterministic_cons_alongside_ai_cons(self):
        result = self._enrich({"cons": ["สีของเคสออกแบบไม่ชอบ"]}, availability=40)
        # The availability warning seeded by the deterministic engine must survive.
        self.assertIn("อุปกรณ์บางชิ้นอาจหาซื้อได้ยากในขณะนี้", result["cons"])
        self.assertIn("สีของเคสออกแบบไม่ชอบ", result["cons"])
        self.assertFalse(result["_meta"].get("provider_fallback"))

    def test_merge_deduplicates_and_caps_the_lists(self):
        repeated = "สินค้า ราคา และผลตรวจความเข้ากันได้มาจากชุดเดียวกัน"
        result = self._enrich({
            "pros": [repeated] + [f"ข้อดี {i}" for i in range(5)],
            "cons": [f"ข้อเสีย {i}" for i in range(5)],
        }, availability=80)
        # The AI repeated the deterministic default; it must appear exactly once.
        self.assertEqual(result["pros"].count(repeated), 1)
        self.assertEqual(result["pros"][0], repeated)
        # clean_lists keeps at most 5 AI items, so pros = 1 deterministic + 4 unique.
        self.assertEqual(len(result["pros"]), 5)
        # cons = 1 deterministic + 5 AI, which lands exactly on the cap.
        self.assertEqual(len(result["cons"]), rec.MAX_PROS_CONS_ITEMS)
        for field in ("pros", "cons"):
            with self.subTest(field=field):
                self.assertLessEqual(len(result[field]), rec.MAX_PROS_CONS_ITEMS)
                self.assertEqual(len(result[field]), len(set(result[field])))

    def test_self_contradiction_is_rejected_for_deterministic_prose(self):
        result = self._enrich({
            "summary": "ชุดนี้คุ้มค่า",
            "performance": {"productivity": "โหลดเร็วมาก"},
            "cons": ["ความเร็ว SSD ต่ำกว่ามาตรฐาน"],
        })
        # The contradiction is refused, so the deterministic prose is kept intact.
        self.assertTrue(result["_meta"]["provider_fallback"])
        self.assertIn("self-contradicts", result["_meta"]["fallback_reason"])
        self.assertEqual(result["performance"]["productivity"], "ยังไม่ได้ประเมิน")
        self.assertNotIn("โหลดเร็วมาก", result["performance"].values())
        self.assertNotIn("ความเร็ว SSD ต่ำกว่ามาตรฐาน", result["cons"])

    def test_consistent_ai_prose_is_kept(self):
        result = self._enrich({
            "summary": "ชุดนี้สมดุล",
            "performance": {"gaming": "เล่นเกมได้ลื่น"},
            "cons": ["สีของเคสออกแบบไม่ชอบ"],
        })
        self.assertFalse(result["_meta"].get("provider_fallback"))
        self.assertEqual(result["performance"]["gaming"], "เล่นเกมได้ลื่น")
        self.assertIn("สีของเคสออกแบบไม่ชอบ", result["cons"])

    def test_contradiction_detector_ignores_unrelated_pairs(self):
        self.assertFalse(rec.has_self_contradiction(
            {"productivity": "โหลดเร็ว"}, ["หน่วยความจำน้อยเกินไป"]))
        self.assertFalse(rec.has_self_contradiction({}, ["อะไรบางอย่าง"]))
        self.assertFalse(rec.has_self_contradiction({"gaming": "เร็ว"}, []))
        self.assertTrue(rec.has_self_contradiction(
            {"productivity": "โหลดเร็ว"}, ["ความเร็วต่ำกว่ามาตรฐาน"]))


if __name__ == "__main__":
    unittest.main()
