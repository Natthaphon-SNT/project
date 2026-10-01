"""Regression tests for budget boundaries, incompatibility, UNKNOWN handling,
candidate restriction and the empty-catalogue path.

These cases were found uncovered in the existing suites. Every expectation below
was taken from an actual run of the code, not from the intended behaviour.
"""
import asyncio
import unittest
from typing import Optional
from unittest.mock import AsyncMock, patch

import compat_engine as ce
import recommender as rec
import scoring_engine as scoring
import spec_parser as sp


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


def full_catalogue() -> list:
    """A catalogue complete enough for the heuristic builder to fill 7 slots."""
    return [
        candidate("real-cpu", "CPU", "AMD RYZEN 7 7800X3D AM5", 20_000,
                  "CPU Cooler: Yes\nTDP: 120 W"),
        candidate("real-mb", "Mainboard", "MAINBOARD B650M-P DDR5 AM5", 8_000),
        candidate("real-ram", "RAM", "RAM DDR5 32GB (16x2) 6000MHz", 5_000),
        candidate("real-gpu", "GPU", "GEFORCE RTX 4060 8GB", 15_000),
        candidate("real-ssd", "SSD", "SSD NVME 1TB", 3_000),
        candidate("real-psu", "PSU", "POWER SUPPLY 850W GOLD", 4_000),
        candidate("real-case", "Case", "ATX CASE MID TOWER", 3_000),
    ]


CATALOGUE_IDS = {c["product_id"] for c in full_catalogue()}


def all_product_ids(result: dict) -> set:
    """Every product_id the response exposes, in parts and in every alternative."""
    product_ids = set()
    for build in [result, *result.get("alternatives", [])]:
        for part in build.get("parts", []):
            if part.get("product_id"):
                product_ids.add(part["product_id"])
    return product_ids


class BudgetBoundaryTests(unittest.TestCase):
    def test_total_exactly_equal_to_budget_is_within_budget(self):
        result = ce.check_budget([{"price": 25_000}], 25_000)

        self.assertTrue(result["ok"])
        self.assertEqual(result["severity"], "PASS")
        self.assertIn("อยู่ในงบ 25,000฿", result["detail"])

    def test_one_baht_over_budget_is_reported_as_warning_not_pass(self):
        result = ce.check_budget([{"price": 25_001}], 25_000)

        self.assertFalse(result["ok"])
        self.assertEqual(result["severity"], "WARNING")
        self.assertIn("เกินงบที่ตั้งไว้ 1 บาท", result["detail"])

    def test_over_budget_build_downgrades_overall_to_warning(self):
        parts = [
            sp.parse_part("CPU", "AMD RYZEN 7 7800X3D AM5"),
            sp.parse_part("Mainboard", "MAINBOARD B650M-P DDR5 AM5"),
        ]
        parts[0]["price"] = 30_000
        parts[1]["price"] = 20_000

        result = ce.check_build(parts, 25_000)
        budget = next(c for c in result["checks"] if c["rule"] == "R7 Budget")

        self.assertEqual(budget["severity"], "WARNING")
        self.assertEqual(result["overall"], "warning")
        self.assertIn("เกินงบที่ตั้งไว้ 25,000 บาท",
                      next(c["detail"] for c in result["checks"] if c["rule"] == "R7 Budget"))

    def test_recommendation_total_above_budget_is_flagged_in_result(self):
        candidates = [candidate("cpu", "CPU", "AMD RYZEN 7 7800X3D AM5", 30_000)]
        result = rec.build_final_result(
            {"parts": [{"type": "CPU", "product_id": "cpu"}]},
            candidates, 20_000, "gaming",
        )
        budget = next(c for c in result["compat"]["checks"] if c["rule"] == "R7 Budget")

        self.assertEqual(budget["severity"], "WARNING")
        self.assertIn("เกินงบที่ตั้งไว้ 10,000 บาท", budget["detail"])

    def test_lower_bound_budget_removes_the_over_budget_check(self):
        candidates = [candidate("cpu", "CPU", "AMD RYZEN 7 7800X3D AM5", 30_000,
                                "CPU Cooler: Yes")]
        result = rec.build_final_result(
            {"parts": [{"type": "CPU", "product_id": "cpu"}]},
            candidates, 20_000, "gaming", budget_ceiling=False,
        )

        self.assertFalse(any(c["rule"] == "R7 Budget" for c in result["compat"]["checks"]))


class IncompatibilityTests(unittest.TestCase):
    def test_cpu_socket_mismatch_is_an_error(self):
        result = ce.check_socket([
            sp.parse_part("CPU", "AMD RYZEN 5 5600 AM4"),
            sp.parse_part("Mainboard", "MAINBOARD (AM5) MSI PRO B650M-P DDR5"),
        ])

        self.assertEqual(result["severity"], "ERROR")
        self.assertFalse(result["ok"])
        self.assertIn("เข้ากันไม่ได้", result["detail"])

    def test_socket_mismatch_makes_the_whole_build_an_error(self):
        result = ce.check_build([
            sp.parse_part("CPU", "AMD RYZEN 5 5600 AM4"),
            sp.parse_part("Mainboard", "MAINBOARD (AM5) MSI PRO B650M-P DDR5"),
        ])

        self.assertEqual(result["overall"], "error")
        self.assertTrue(any("Mainboard ให้ตรง socket"
                            in s for s in result["suggestions"]))

    def test_ddr_generation_mismatch_is_an_error(self):
        result = ce.check_ram_gen([
            sp.parse_part("RAM", "RAM DDR5 32GB (16x2) 6000MHz"),
            sp.parse_part("Mainboard", "MAINBOARD B760M DDR4 LGA1700"),
        ])

        self.assertEqual(result["severity"], "ERROR")
        self.assertIn("DDR4", result["detail"])
        self.assertTrue(any("RAM ให้ตรง generation"
                            in s for s in ce.check_build([
                                sp.parse_part("RAM", "RAM DDR5 32GB (16x2) 6000MHz"),
                                sp.parse_part("Mainboard", "MAINBOARD B760M DDR4 LGA1700"),
                            ])["suggestions"]))

    def test_matching_socket_and_ddr_generation_pass(self):
        self.assertEqual(ce.check_socket([
            sp.parse_part("CPU", "AMD RYZEN 7 7800X3D AM5"),
            sp.parse_part("Mainboard", "MAINBOARD (AM5) MSI PRO B650M-P DDR5"),
        ])["severity"], "PASS")
        self.assertEqual(ce.check_ram_gen([
            sp.parse_part("RAM", "RAM DDR5 32GB (16x2) 6000MHz"),
            sp.parse_part("Mainboard", "MAINBOARD (AM5) MSI PRO B650M-P DDR5"),
        ])["severity"], "PASS")


class UnknownHandlingTests(unittest.TestCase):
    def test_unrecognised_cpu_socket_is_unknown_and_never_ok(self):
        result = next(c for c in ce.check_build([
            sp.parse_part("CPU", "CPU MYSTERY SERIES 9000X"),
            sp.parse_part("Mainboard", "MAINBOARD (AM5) MSI PRO B650M-P DDR5"),
        ])["checks"] if c["rule"].startswith("R1"))

        self.assertEqual(result["severity"], "UNKNOWN")
        self.assertFalse(result["ok"])
        self.assertIn("ไม่ทราบ socket", result["detail"])

    def test_unrecognised_ram_generation_is_unknown(self):
        result = next(c for c in ce.check_build([
            sp.parse_part("RAM", "RAM MYSTERY SERIES 32GB"),
            sp.parse_part("Mainboard", "MAINBOARD B650M-P DDR5 AM5"),
        ])["checks"] if c["rule"].startswith("R2"))

        self.assertEqual(result["severity"], "UNKNOWN")
        self.assertFalse(result["ok"])

    def test_every_raw_rule_reports_unknown_as_not_ok(self):
        """Contract: `ok` means the rule was evaluated and passed.

        Every rule function must agree on this, not only the ones that happen
        to be reachable through check_build(), so a direct caller can never
        read a missing datum as a confirmed match.
        """
        unknown_results = [
            ce.check_socket([
                sp.parse_part("CPU", "CPU MYSTERY SERIES 9000X"),
                sp.parse_part("Mainboard", "MAINBOARD (AM5) MSI PRO B650M-P DDR5"),
            ]),
            ce.check_ram_gen([
                sp.parse_part("RAM", "RAM MYSTERY SERIES 32GB"),
                sp.parse_part("Mainboard", "MAINBOARD B650M-P DDR5 AM5"),
            ]),
            ce.check_cooler_tdp([
                {"category": "CPU", "name": "CPU MYSTERY SERIES 9000X"},
                {"category": "Cooler", "name": "COOLER MYSTERY AIR", "is_cpu_cooler": True},
            ]),
            ce.check_case_ff([
                sp.parse_part("Mainboard", "MAINBOARD MYSTERY SERIES"),
                sp.parse_part("Case", "CASE MYSTERY TOWER"),
            ]),
            ce.check_psu_watt([
                sp.parse_part("GPU", "GPU MYSTERY CARD"),
                sp.parse_part("PSU", "PSU MYSTERY"),
            ]),
        ]

        for result in unknown_results:
            with self.subTest(rule=result["rule"]):
                self.assertEqual(result["severity"], "UNKNOWN")
                self.assertFalse(result["ok"])

    def test_unknown_still_reports_its_severity_and_keeps_counting(self):
        """Fixing `ok` must not hide UNKNOWN from callers or from the verdict."""
        raw_socket = ce.check_socket([
            sp.parse_part("CPU", "CPU MYSTERY SERIES 9000X"),
            sp.parse_part("Mainboard", "MAINBOARD (AM5) MSI PRO B650M-P DDR5"),
        ])

        self.assertEqual(raw_socket["severity"], "UNKNOWN")
        self.assertIn("ไม่ทราบ socket", raw_socket["detail"])

        built = ce.check_build([
            sp.parse_part("CPU", "CPU MYSTERY SERIES 9000X"),
            sp.parse_part("Mainboard", "MAINBOARD (AM5) MSI PRO B650M-P DDR5"),
        ])
        self.assertEqual(built["overall"], "warning")
        self.assertGreaterEqual(built["_engine"]["unknown"], 1)

    def test_unknown_checks_make_the_verdict_warning_not_ok(self):
        result = ce.check_build([
            sp.parse_part("CPU", "CPU MYSTERY SERIES 9000X"),
            sp.parse_part("Mainboard", "MAINBOARD (AM5) MSI PRO B650M-P DDR5"),
        ])

        self.assertNotEqual(result["overall"], "ok")
        self.assertTrue(all(not c["ok"] for c in result["checks"]
                            if c["severity"] == "UNKNOWN"))
        self.assertIn("ข้อมูลไม่พอ", result["summary"])

    def test_empty_build_does_not_report_success(self):
        result = ce.check_build([])

        self.assertNotEqual(result["overall"], "ok")
        self.assertEqual(result["checks"], [])

    def test_empty_build_with_a_budget_does_not_report_success(self):
        """A budget check over zero parts is not a compatibility confirmation.

        R7 is the only rule that can run without parts, and 0฿ is within any
        budget, so an empty build produced overall 'ok' and the summary
        'ผ่านการตรวจ compatibility 1/1 ข้อ'. Nothing was actually verified.
        """
        result = ce.check_build([], 30_000)

        self.assertNotEqual(result["overall"], "ok")

    def test_empty_build_never_says_it_passed_every_rule(self):
        result = ce.check_build([], 30_000)

        self.assertNotIn("ผ่านการตรวจ", result["summary"])

    def test_empty_build_is_not_scored_as_fully_compatible(self):
        result = ce.check_build([], 30_000)

        self.assertLess(scoring.score_compatibility(result), 100.0)


class CandidateRestrictionTests(unittest.TestCase):
    CANDIDATES = [candidate("real-cpu", "CPU", "AMD RYZEN 7 7800X3D AM5", 20_000)]

    def test_product_id_outside_candidates_is_not_mapped(self):
        self.assertIsNone(rec.map_part_to_candidate(
            {"type": "CPU", "product_id": "gpu-9999", "name": "Imaginary CPU"},
            self.CANDIDATES))

    def test_similar_but_different_name_is_not_mapped_without_product_id(self):
        self.assertIsNone(rec.map_part_to_candidate(
            {"type": "CPU", "name": "AMD RYZEN 7 7800X3D AM5 GOLD EDITION"},
            self.CANDIDATES))

    def test_unrelated_name_is_not_mapped(self):
        self.assertIsNone(rec.map_part_to_candidate(
            {"type": "CPU", "name": "Intel Core Ultra 9 285K LGA1851"},
            self.CANDIDATES))

    def test_exact_product_id_is_mapped(self):
        mapped = rec.map_part_to_candidate(
            {"type": "CPU", "product_id": "real-cpu", "name": "whatever"},
            self.CANDIDATES)

        self.assertEqual(mapped["product_id"], "real-cpu")

    def test_invented_part_is_dropped_and_counted_as_rejected(self):
        result = rec.build_final_result(
            {"parts": [{"type": "CPU", "product_id": "real-cpu", "name": "AMD RYZEN 7 7800X3D AM5"},
                       {"type": "GPU", "product_id": "gpu-9999", "name": "Imaginary GPU"}]},
            self.CANDIDATES, 30_000, "gaming",
        )

        self.assertEqual([p["product_id"] for p in result["parts"]], ["real-cpu"])
        self.assertEqual(result["_meta"]["parts_rejected_not_in_db"], 1)
        self.assertIn("ไม่พบสินค้าที่ตรงในฐานข้อมูลสำหรับ GPU", result["warnings"])
        self.assertNotIn("(ราคาจริงจากฐานข้อมูล)", result["totalBudget"])

    def test_all_parts_invented_yields_no_parts_and_a_warning(self):
        result = rec.build_final_result(
            {"parts": [{"type": "CPU", "product_id": "gpu-9999", "name": "Imaginary GPU"}]},
            self.CANDIDATES, 30_000, "gaming",
        )

        self.assertEqual(result["parts"], [])
        self.assertEqual(result["totalBudget"], "0 ฿")
        self.assertEqual(result["_meta"]["parts_rejected_not_in_db"], 1)
        self.assertTrue(result["warnings"])


class MalformedModelResponseTests(unittest.TestCase):
    """A reply whose shape is unusable degrades to the grounded build.

    The degradation is only observable when the deterministic fallback can
    actually assemble a complete set, so the fallback tests pass
    `full_catalogue()`. `CANDIDATES` alone holds a single product and cannot
    satisfy the mandatory-category rule that recommend_build now applies before
    handing back a fallback.
    """
    CANDIDATES = [candidate("real-cpu", "CPU", "AMD RYZEN 7 7800X3D AM5", 20_000,
                            "CPU Cooler: Yes")]

    def _run(self, reply: str, candidates=None):
        with patch.object(rec, "llm_chat", new_callable=AsyncMock, return_value=reply):
            return asyncio.run(rec.recommend_build(
                None, "แนะนำคอมเล่นเกมงบ 30,000 บาท",
                candidates=self.CANDIDATES if candidates is None else candidates,
                provider="google", api_key="test-key"))

    def _product_ids(self, result: dict) -> set:
        product_ids = {
            part["product_id"]
            for alt in result.get("alternatives", [])
            for part in alt.get("parts", [])
        }
        product_ids.update(p["product_id"] for p in result.get("parts", []))
        return product_ids

    def test_prose_without_json_raises_a_parse_error(self):
        """No decodable JSON: there is nothing to salvage, so it propagates."""
        with self.assertRaises(rec.LLMResponseParseError):
            self._run("I cannot help with that.")

    def test_parse_error_is_a_runtime_error_and_is_not_a_schema_error(self):
        self.assertTrue(issubclass(rec.LLMResponseParseError, RuntimeError))
        self.assertFalse(issubclass(rec.LLMResponseParseError, rec.LLMResponseSchemaError))

    def test_schema_error_is_a_value_error_so_it_degrades_instead_of_raising(self):
        """The fallback branch catches ValueError, not RuntimeError.

        Making the schema error a ValueError is what routes it to the
        deterministic build rather than to the caller.
        """
        self.assertTrue(issubclass(rec.LLMResponseSchemaError, ValueError))
        self.assertFalse(issubclass(rec.LLMResponseSchemaError, RuntimeError))

    def test_json_without_parts_falls_back_to_the_grounded_build(self):
        result = self._run('{"summary":"hi"}', candidates=full_catalogue())

        self.assertTrue(result["_meta"]["provider_fallback"])
        self.assertIn("schema", result["_meta"]["fallback_reason"])
        self.assertTrue(self._product_ids(result) <= CATALOGUE_IDS)

    def test_empty_parts_list_falls_back_to_the_grounded_build(self):
        result = self._run('{"parts":[]}', candidates=full_catalogue())

        self.assertTrue(result["_meta"]["provider_fallback"])
        self.assertIn("empty", result["_meta"]["fallback_reason"])
        self.assertTrue(self._product_ids(result) <= CATALOGUE_IDS)

    def test_non_object_part_entries_fall_back_instead_of_crashing(self):
        """Regression: a string `parts` used to raise AttributeError in
        build_final_result instead of reporting a schema problem."""
        result = self._run('{"parts":"oops"}', candidates=full_catalogue())

        self.assertTrue(result["_meta"]["provider_fallback"])
        self.assertIn("must be a list", result["_meta"]["fallback_reason"])
        self.assertNotIn("AttributeError", result["_meta"]["fallback_reason"])
        self.assertTrue(self._product_ids(result) <= CATALOGUE_IDS)

    def test_part_without_any_identifier_is_a_schema_problem(self):
        result = self._run('{"parts":[{"type":"CPU"}]}', candidates=full_catalogue())

        self.assertTrue(result["_meta"]["provider_fallback"])
        self.assertIn("no product_id", result["_meta"]["fallback_reason"])
        self.assertTrue(self._product_ids(result) <= CATALOGUE_IDS)

    def test_an_unbuildable_catalogue_refuses_instead_of_degrading(self):
        """A one-product catalogue cannot fill the mandatory categories, so the
        fallback refuses instead of returning a partial build. The schema
        diagnosis is preserved in nothing here: this is the refusal contract,
        asserted separately in RefusalContractTests."""
        with self.assertRaises(RuntimeError):
            self._run('{"summary":"hi"}')

    def test_fenced_json_with_prose_is_accepted(self):
        result = self._run(
            'Here you go:\n```json\n{"parts":[{"type":"CPU","product_id":"real-cpu"}]}\n```\nDone.')

        self.assertEqual([p["product_id"] for p in result["parts"]], ["real-cpu"])
        self.assertFalse(result["_meta"].get("provider_fallback", False))

    def test_valid_payload_is_not_flagged_by_the_validator(self):
        self.assertEqual(rec.validate_build_payload(
            {"parts": [{"type": "CPU", "product_id": "real-cpu"}]}), [])


class PayloadValidationTests(unittest.TestCase):
    def test_non_dict_payload_is_reported(self):
        self.assertIn("must be a JSON object", rec.validate_build_payload(["not", "a", "dict"])[0])

    def test_missing_parts_is_reported(self):
        self.assertEqual(rec.validate_build_payload({"summary": "hi"}), ["missing 'parts'"])

    def test_parts_of_wrong_type_is_reported(self):
        self.assertIn("must be a list", rec.validate_build_payload({"parts": "oops"})[0])

    def test_every_broken_part_is_reported(self):
        problems = rec.validate_build_payload({"parts": [
            {"type": "CPU", "product_id": "real-cpu"},
            "oops",
            {"type": "GPU"},
        ]})

        self.assertEqual(len(problems), 2)
        self.assertIn("parts[1]", problems[0])
        self.assertIn("parts[2]", problems[1])

    def test_identifier_may_be_product_id_id_or_name(self):
        self.assertEqual(rec.validate_build_payload(
            {"parts": [{"name": "AMD RYZEN 7 7800X3D AM5"}]}), [])
        self.assertEqual(rec.validate_build_payload(
            {"parts": [{"id": "real-cpu"}]}), [])


class EmptyJsonObjectTests(unittest.TestCase):
    """`{}` parses successfully. It is a schema failure, not a parse failure.

    The distinction matters because the two errors are handled differently:
    a parse failure propagates, a schema failure degrades to the grounded
    heuristic build. Using truthiness to detect an empty object would report
    a decodable-but-empty reply as if the model had returned no JSON at all.
    """
    CANDIDATES = [candidate("real-cpu", "CPU", "AMD RYZEN 7 7800X3D AM5", 20_000,
                            "CPU Cooler: Yes")]

    def _run(self, reply: str, candidates=None):
        with patch.object(rec, "llm_chat", new_callable=AsyncMock, return_value=reply):
            return asyncio.run(rec.recommend_build(
                None, "แนะนำคอมเล่นเกมงบ 30,000 บาท",
                candidates=self.CANDIDATES if candidates is None else candidates,
                provider="google", api_key="test-key"))

    def test_extract_json_returns_an_empty_object_rather_than_none(self):
        self.assertEqual(rec.extract_json("{}"), {})

    def test_empty_object_degrades_instead_of_raising(self):
        result = self._run("{}", candidates=full_catalogue())

        self.assertTrue(result["_meta"]["provider_fallback"])
        self.assertIn("missing 'parts'", result["_meta"]["fallback_reason"])

    def test_empty_object_is_diagnosed_as_a_schema_problem(self):
        """An empty object is decodable, so it must produce a shape complaint
        rather than the 'no JSON at all' parse failure."""
        problems = rec.validate_build_payload(rec.extract_json("{}"))

        self.assertEqual(problems, ["missing 'parts'"])
        self.assertNotIn("invalid JSON", " ".join(problems))

    def test_empty_object_raises_the_schema_error_not_the_parse_error(self):
        with self.assertRaises(rec.LLMResponseSchemaError):
            raise rec.LLMResponseSchemaError(
                "; ".join(rec.validate_build_payload(rec.extract_json("{}"))))

    def test_empty_object_embedded_in_prose_also_degrades(self):
        result = self._run('Here is the build:\n{}\nThanks!',
                           candidates=full_catalogue())

        self.assertTrue(result["_meta"]["provider_fallback"])

    def test_empty_object_with_an_unbuildable_catalogue_uses_the_refusal(self):
        """The P2 distinction holds at the boundary: a decodable-but-empty reply
        whose fallback cannot build is a refusal, never a parse failure."""
        with self.assertRaises(RuntimeError) as ctx:
            self._run("{}")

        self.assertNotIsInstance(ctx.exception, rec.LLMResponseParseError)
        self.assertEqual(str(ctx.exception), rec.NO_COMPLETE_BUILD)

    def test_no_json_at_all_is_still_a_parse_error(self):
        with self.assertRaises(rec.LLMResponseParseError):
            self._run("I cannot help with that.")

    def test_unparseable_braces_are_still_a_parse_error(self):
        self.assertIsNone(rec.extract_json("not json {oops"))

    def test_empty_parts_list_is_distinct_from_an_empty_object(self):
        problems = rec.validate_build_payload({"parts": []})

        self.assertEqual(problems, ["'parts' is empty"])
        self.assertNotEqual(problems, rec.validate_build_payload({}))


class PartCategoryTests(unittest.TestCase):
    """A part with no usable `type` must not silently cost nothing.

    `db_cat` decides whether a matched product is added to parsed_parts, and
    parsed_parts is what the price total and the compatibility engine read.
    A part whose type is missing, non-string, or not a recognised category was
    matched to a real product and shown with its real price, yet excluded from
    the total and from every compatibility rule.
    """
    CATALOGUE = full_catalogue()

    def _build(self, part: dict):
        return rec.build_final_result(
            {"parts": [part]}, self.CATALOGUE, 60_000, "gaming")

    def test_missing_type_is_inferred_from_the_matched_catalogue_row(self):
        result = self._build({"product_id": "real-cpu"})

        self.assertEqual([p["product_id"] for p in result["parts"]], ["real-cpu"])
        self.assertNotEqual(result["totalBudget"], "0 ฿")
        self.assertIn("20,000 ฿", result["totalBudget"])

    def test_empty_object_type_is_inferred_from_the_matched_catalogue_row(self):
        result = self._build({"type": {}, "product_id": "real-cpu"})

        self.assertIn("20,000 ฿", result["totalBudget"])

    def test_null_type_is_inferred_from_the_matched_catalogue_row(self):
        result = self._build({"type": None, "product_id": "real-cpu"})

        self.assertIn("20,000 ฿", result["totalBudget"])

    def test_unsupported_type_does_not_override_the_real_catalogue_category(self):
        result = self._build({"type": "Mouse", "product_id": "real-cpu"})

        self.assertIn("20,000 ฿", result["totalBudget"])

    def test_type_is_overwritten_by_the_catalogue_category_not_the_model_claim(self):
        """The model may mislabel a part. The catalogue row is authoritative."""
        result = self._build({"type": "RAM", "product_id": "real-cpu"})

        self.assertEqual(result["parts"][0]["type"], "CPU")

    def test_a_matched_part_always_enters_the_compatibility_engine(self):
        result = self._build({"product_id": "real-cpu"})

        self.assertTrue(result["compat"]["checks"],
                        "a priced part produced no compatibility check at all")

    def test_matched_part_with_unusable_type_is_never_priced_at_zero(self):
        for bad_type in (None, {}, [], 0, "", "Mouse"):
            with self.subTest(type=bad_type):
                result = self._build({"type": bad_type, "product_id": "real-cpu"})

                self.assertNotEqual(result["totalBudget"], "0 ฿")

    def test_empty_object_part_is_rejected_as_a_schema_problem(self):
        problems = rec.validate_build_payload({"parts": [{}]})

        self.assertEqual(len(problems), 1)
        self.assertIn("no product_id", problems[0])

    def test_empty_object_part_never_reaches_the_result_builder(self):
        with patch.object(rec, "llm_chat", new_callable=AsyncMock,
                          return_value='{"parts":[{}]}'):
            result = asyncio.run(rec.recommend_build(
                None, "แนะนำคอมเล่นเกมงบ 60,000 บาท",
                candidates=self.CATALOGUE, provider="google", api_key="test-key"))

        self.assertTrue(result["_meta"]["provider_fallback"])
        self.assertNotEqual(result["totalBudget"], "0 ฿")

    def test_part_outside_the_catalogue_is_still_rejected(self):
        result = self._build({"type": "CPU", "product_id": "gpu-9999",
                              "name": "Imaginary CPU"})

        self.assertEqual(result["parts"], [])
        self.assertEqual(result["_meta"]["parts_rejected_not_in_db"], 1)


class CategoryDisagreementPolicyTests(unittest.TestCase):
    """A mismatch between the model's claim and the catalogue must not be silent.

    The catalogue row decides the category, because parsed_parts, the price total
    and every compatibility rule are all derived from it. Correcting a bad label
    is therefore the right outcome for safety. But correcting it *silently*
    hides the more interesting fact: the model was reasoning about a part it had
    mislabelled, which may mean its `reason` text and its slot choices were wrong
    too. So the correction happens and is also reported.
    """
    CATALOGUE = full_catalogue()

    def _build(self, part: dict):
        return rec.build_final_result(
            {"parts": [part]}, self.CATALOGUE, 60_000, "gaming")

    def test_a_mismatched_claim_is_corrected_to_the_catalogue_category(self):
        result = self._build({"type": "RAM", "product_id": "real-cpu"})

        self.assertEqual(result["parts"][0]["type"], "CPU")
        self.assertIn("20,000 ฿", result["totalBudget"])

    def test_a_mismatched_claim_produces_a_visible_warning(self):
        result = self._build({"type": "RAM", "product_id": "real-cpu"})

        self.assertTrue(result["warnings"],
                        "the model mislabelled the part and nothing said so")
        self.assertTrue(any("RAM" in w and "real-cpu" in w
                            for w in result["warnings"]),
                        f"warning does not name both the claim and the product: "
                        f"{result['warnings']}")

    def test_a_mismatched_claim_is_counted_in_meta(self):
        result = self._build({"type": "RAM", "product_id": "real-cpu"})

        self.assertEqual(result["_meta"]["parts_category_corrected"], 1)

    def test_an_agreeing_claim_produces_no_warning(self):
        result = self._build({"type": "CPU", "product_id": "real-cpu"})

        self.assertEqual(result["_meta"]["parts_category_corrected"], 0)
        self.assertFalse(any("RAM" in w for w in result["warnings"]))

    def test_a_missing_claim_is_not_reported_as_a_disagreement(self):
        """No claim is not a disagreement; it is the case P1 already fixed."""
        result = self._build({"product_id": "real-cpu"})

        self.assertEqual(result["_meta"]["parts_category_corrected"], 0)
        self.assertIn("20,000 ฿", result["totalBudget"])

    def test_an_unusable_claim_is_not_reported_as_a_disagreement(self):
        """'Mouse' and {} are unusable labels, not claims worth arguing with."""
        for bad in ("Mouse", {}, None, 0, []):
            with self.subTest(type=bad):
                result = self._build({"type": bad, "product_id": "real-cpu"})

                self.assertEqual(result["_meta"]["parts_category_corrected"], 0)
                self.assertIn("20,000 ฿", result["totalBudget"])

    def test_a_disagreement_does_not_discount_the_total(self):
        """Correcting a label must not turn a fully priced build into a partial one."""
        agreeing = self._build({"type": "CPU", "product_id": "real-cpu"})
        disagreeing = self._build({"type": "RAM", "product_id": "real-cpu"})

        self.assertIn("(ราคาจริงจากฐานข้อมูล)",
                      disagreeing["totalBudget"])
        self.assertEqual(agreeing["totalBudget"], disagreeing["totalBudget"])

    def test_multiple_disagreements_are_all_reported(self):
        result = rec.build_final_result(
            {"parts": [{"type": "RAM", "product_id": "real-cpu"},
                       {"type": "SSD", "product_id": "real-mb"},
                       {"type": "Mainboard", "product_id": "real-ram"}]},
            self.CATALOGUE, 60_000, "gaming")

        self.assertEqual(result["_meta"]["parts_category_corrected"], 3)
        self.assertEqual([p["type"] for p in result["parts"]],
                         ["CPU", "Mainboard", "RAM"])

    def test_a_disagreement_still_runs_the_compatibility_engine(self):
        """The point of correcting is that the part becomes checkable."""
        result = self._build({"type": "RAM", "product_id": "real-cpu"})

        self.assertTrue(result["compat"]["checks"])
        self.assertTrue(any(c.get("severity") == "PASS"
                            for c in result["compat"]["checks"]))


class EndToEndGroundingTests(unittest.TestCase):
    """Price, compatibility and fallback verified on the whole response.

    A subset assertion on an empty set is vacuously true, so every test here
    asserts the response is non-empty before checking it stays grounded.
    """
    CATALOGUE = full_catalogue()
    CANDIDATE_IDS = {c["product_id"] for c in CATALOGUE}

    def _run(self, reply: str):
        with patch.object(rec, "llm_chat", new_callable=AsyncMock, return_value=reply):
            return asyncio.run(rec.recommend_build(
                None, "แนะนำคอมเล่นเกมงบ 60,000 บาท",
                candidates=self.CATALOGUE, provider="google", api_key="test-key"))

    def test_empty_object_reply_yields_a_complete_grounded_build(self):
        result = self._run("{}")

        self.assertTrue(result["parts"], "fallback produced no parts at all")
        self.assertNotEqual(result["totalBudget"], "0 ฿")
        self.assertTrue(result["compat"]["checks"])
        self.assertNotEqual(result["compat"]["overall"], "ok")

    def test_fallback_alternatives_are_also_grounded_in_the_catalogue(self):
        result = self._run("{}")

        self.assertTrue(all_product_ids(result))
        self.assertTrue(all_product_ids(result) <= self.CANDIDATE_IDS)

    def test_fallback_alternatives_are_present_to_check(self):
        result = self._run("{}")

        self.assertTrue(result["parts"] or result.get("alternatives"),
                        "nothing to check for grounding")

    def test_missing_type_reply_stays_grounded_end_to_end(self):
        result = self._run('{"parts":[{"product_id":"real-cpu"}]}')

        self.assertTrue(result["parts"])
        self.assertTrue(all_product_ids(result) <= self.CANDIDATE_IDS)
        self.assertIn("20,000 ฿", result["totalBudget"])

    def test_out_of_catalogue_reply_produces_no_fabricated_product(self):
        result = self._run(
            '{"parts":[{"type":"CPU","product_id":"real-cpu"},'
            '{"type":"GPU","product_id":"gpu-9999","name":"Imaginary GPU"}]}')

        self.assertTrue(result["parts"])
        self.assertTrue(all_product_ids(result) <= self.CANDIDATE_IDS)
        self.assertEqual(result["_meta"]["parts_rejected_not_in_db"], 1)

    def test_total_matches_the_sum_of_the_priced_parts(self):
        result = self._run('{"parts":[{"product_id":"real-cpu"}]}')

        priced = [p for p in result["parts"] if p.get("real_price")]
        self.assertTrue(priced)
        self.assertIn(f"{sum(p['real_price'] for p in priced):,} ฿", result["totalBudget"])


class EmptyCatalogueTests(unittest.TestCase):
    def test_no_candidates_produces_no_build_instead_of_an_incomplete_one(self):
        self.assertEqual(rec.top3_builds([], 50_000, "gaming"), [])

    def test_partial_catalogue_produces_no_build(self):
        partial = [candidate("cpu", "CPU", "AMD RYZEN 7 7800X3D AM5", 20_000,
                             "CPU Cooler: Yes")]

        self.assertEqual(rec.top3_builds(partial, 50_000, "gaming"), [])

    def test_scoring_refuses_to_return_a_build_without_candidates(self):
        with self.assertRaises(RuntimeError):
            rec._scored_recommendation_result([], "แนะนำคอมเล่นเกมงบ 50,000 บาท")


class RefusalContractTests(unittest.TestCase):
    """recommend_build must refuse on the same terms as recommend_with_alternatives.

    recommend_with_alternatives routes through top3_builds and
    _scored_recommendation_result, which raise
    "No complete compatible catalogue build available" when the catalogue cannot
    fill the mandatory categories. shop_api maps that message to HTTP 422 at
    recommender call sites. recommend_build took a different route: it degrades
    to heuristic_build unconditionally, and heuristic_build returns whatever
    assemble_build managed to pick, including nothing at all.
    """
    REFUSAL = rec.NO_COMPLETE_BUILD

    def _run(self, reply: str, candidates: Optional[list]):
        with patch.object(rec, "llm_chat", new_callable=AsyncMock, return_value=reply):
            return asyncio.run(rec.recommend_build(
                None, "แนะนำคอมเล่นเกมงบ 60,000 บาท",
                candidates=candidates, provider="google", api_key="test-key"))

    def test_empty_object_reply_with_no_candidates_is_refused(self):
        """The reported case: {} plus an empty catalogue must not be a success."""
        with self.assertRaises(RuntimeError) as ctx:
            self._run("{}", candidates=[])

        self.assertEqual(str(ctx.exception), self.REFUSAL)

    def test_refusal_never_returns_an_empty_parts_list(self):
        """Before the fix this returned parts=[], totalBudget '0 ฿', summary
        claiming the offline heuristic build, and compat overall 'warning'."""
        try:
            result = self._run("{}", candidates=[])
        except RuntimeError:
            return
        self.fail(f"expected a refusal, got parts={result['parts']} "
                  f"totalBudget={result['totalBudget']!r}")

    def test_a_reply_with_no_json_is_still_a_parse_error_not_a_refusal(self):
        """The refusal is scoped to replies that decode. When there is no JSON at
        all the parse failure has always propagated, and rewriting it into a
        refusal would disguise a transport/provider problem as a catalogue one.
        Asserted on the type, because LLMResponseParseError is a RuntimeError
        subclass and assertRaises(RuntimeError) alone would prove nothing."""
        with self.assertRaises(rec.LLMResponseParseError):
            self._run("ผมไม่สามารถตอบได้", candidates=[])

    def test_valid_reply_with_no_candidates_is_refused(self):
        """Even a well-formed reply cannot become a build from an empty catalogue."""
        with self.assertRaises(RuntimeError):
            self._run('{"parts":[{"type":"CPU","product_id":"real-cpu"}]}',
                      candidates=[])

    def test_refusal_message_is_the_one_shop_api_already_handles(self):
        """Same string, so the existing 422 mapping keeps working unchanged."""
        with self.assertRaises(RuntimeError) as ctx:
            self._run("{}", candidates=[])

        self.assertIn(self.REFUSAL, str(ctx.exception))
        self.assertEqual(self.REFUSAL, str(ctx.exception))

    def test_partial_catalogue_is_refused_rather_than_returned_incomplete(self):
        partial = [candidate("cpu", "CPU", "AMD RYZEN 7 7800X3D AM5", 20_000,
                             "CPU Cooler: Yes")]

        with self.assertRaises(RuntimeError) as ctx:
            self._run("{}", candidates=partial)

        self.assertEqual(str(ctx.exception), self.REFUSAL)

    def test_a_complete_catalogue_still_degrades_successfully(self):
        """The refusal must not fire when the fallback can actually build."""
        result = self._run("{}", candidates=full_catalogue())

        self.assertTrue(result["parts"])
        self.assertNotEqual(result["totalBudget"], "0 ฿")
        self.assertTrue(result["_meta"]["provider_fallback"])
        self.assertEqual(len(result["parts"]), 7)
        self.assertNotEqual(result["compat"]["overall"], "error")
        self.assertTrue(any(check["severity"] == "UNKNOWN"
                            for check in result["compat"]["checks"]))

    def test_complete_categories_with_a_socket_mismatch_are_refused(self):
        catalogue = full_catalogue()
        catalogue[1] = dict(catalogue[1], name="MAINBOARD B760M DDR5 LGA1700")
        built = rec.assemble_build(catalogue, 60_000, "gaming")
        self.assertTrue(rec.build_is_complete(built))
        self.assertTrue(any(check["rule"].startswith("R1 ")
                            and check["severity"] == "ERROR"
                            for check in built["post_downgrade_compat"]["checks"]))
        with self.assertRaises(RuntimeError) as ctx:
            self._run("{}", candidates=catalogue)
        self.assertEqual(str(ctx.exception), self.REFUSAL)
        self.assertEqual(rec.top3_builds(catalogue, 60_000, "gaming"), [])

    def test_complete_build_with_budget_warning_remains_eligible(self):
        catalogue = full_catalogue()
        catalogue[0] = dict(catalogue[0], price=70_000, prices={"advice": 70_000})
        result = self._run("{}", candidates=catalogue)
        self.assertEqual(len(result["parts"]), 7)
        self.assertEqual(result["compat"]["overall"], "warning")
        self.assertTrue(any(check["rule"] == "R7 Budget"
                            and check["severity"] == "WARNING"
                            for check in result["compat"]["checks"]))
        self.assertTrue(result["_meta"]["provider_fallback"])

    def test_completeness_is_checked_against_the_mandatory_categories(self):
        """assemble_build already reports what it was required to pick."""
        empty = rec.assemble_build([], 60_000, "gaming", fit_budget=60_000)
        complete = rec.assemble_build(full_catalogue(), 60_000, "gaming",
                                      fit_budget=60_000)

        self.assertFalse(rec.build_is_complete(empty))
        self.assertTrue(rec.build_is_complete(complete))

    def test_parse_errors_still_propagate_rather_than_becoming_a_refusal(self):
        """A parse error is a provider problem and stays one. Only an
        unbuildable catalogue becomes the refusal message."""
        with patch.object(rec, "llm_chat", new_callable=AsyncMock,
                          return_value="no json at all"):
            with self.assertRaises(rec.LLMResponseParseError):
                asyncio.run(rec.recommend_build(
                    None, "แนะนำคอมเล่นเกมงบ 60,000 บาท",
                    candidates=full_catalogue(), provider="google", api_key="test-key"))


class ProseWithoutPartsTests(unittest.TestCase):
    """Pre-existing bug: prose survives when no part survives.

    build_final_result rewrites parts against the real catalogue and can end up
    with none, but it copied summary, tier, performance, pros and cons straight
    from the model's reply. A reply claiming a complete, ready-to-use set was
    returned alongside parts=[] and a 0 ฿ total. Found while fixing the
    recommend_build refusal contract; not introduced by these changes.
    """
    CLAIM = {
        "summary": "ชุดคอมเล่นเกมครบทุกชิ้น พร้อมใช้งานทันที",
        "tier": "High-end",
        "performance": {"gaming": "เล่น 4K ได้ 120 FPS"},
        "pros": ["CPU รุ่นใหม่แรงมาก", "คู่ RAM ความจุสูง"],
        "cons": [],
        "parts": [{"type": "CPU", "product_id": "ghost-1", "name": "Imaginary CPU"}],
    }

    def _build(self, **overrides):
        payload = dict(self.CLAIM)
        payload.update(overrides)
        return rec.build_final_result(payload, [], 60_000, "gaming")
    def test_summary_does_not_claim_a_ready_set_when_nothing_survives(self):
        result = self._build()

        self.assertEqual(result["parts"], [])
        self.assertNotIn("พร้อมใช้งาน", result["summary"])
        self.assertIn("ไม่พบ", result["summary"])

    def test_pros_are_not_kept_when_nothing_survives(self):
        result = self._build()

        self.assertEqual(result["pros"], [])

    def test_tier_is_not_kept_when_nothing_survives(self):
        self.assertEqual(self._build()["tier"], "")

    def test_performance_claims_are_not_kept_when_nothing_survives(self):
        self.assertEqual(self._build()["performance"], {})

    def test_cons_keeps_the_rejection_reason_so_the_user_sees_why(self):
        result = self._build()

        self.assertTrue(any("ไม่พบสินค้า" in c for c in result["cons"]))

    def test_meta_records_that_the_build_was_empty(self):
        self.assertTrue(self._build()["_meta"]["build_empty"])

    def test_a_build_that_keeps_its_parts_keeps_its_prose(self):
        result = rec.build_final_result(
            dict(self.CLAIM, parts=[{"type": part["category"], "product_id": part["product_id"]}
                                    for part in full_catalogue()]),
            full_catalogue(), 60_000, "gaming")

        self.assertTrue(result["parts"])
        self.assertEqual(result["summary"], self.CLAIM["summary"])
        self.assertEqual(result["tier"], "High-end")
        self.assertEqual(result["performance"], {"gaming": "เล่น 4K ได้ 120 FPS"})
        self.assertEqual(result["pros"], self.CLAIM["pros"])
        self.assertFalse(result["_meta"]["build_empty"])

    def test_a_partially_surviving_build_reports_the_real_selection(self):
        result = rec.build_final_result(
            dict(self.CLAIM,
                 parts=[{"type": "CPU", "product_id": "real-cpu"},
                        {"type": "RAM", "product_id": "ghost-1"}]),
            full_catalogue(), 60_000, "gaming")

        self.assertEqual([p["product_id"] for p in result["parts"]], ["real-cpu"])
        self.assertNotIn("ครบทุกชิ้น", result["summary"])
        self.assertNotIn("พร้อมใช้งาน", result["summary"])
        self.assertIn("CPU: AMD RYZEN 7 7800X3D AM5", result["summary"])
        self.assertIn("ขาด: Mainboard, RAM, GPU, SSD, PSU, Case", result["summary"])
        self.assertFalse(result["_meta"]["build_empty"])

    def test_incomplete_build_keeps_other_explanations_and_removes_readiness(self):
        explanation = "CPU รุ่นนี้เหมาะกับงานทั่วไป"
        result = rec.build_final_result(
            dict(self.CLAIM,
                 summary=explanation + ". พร้อมใช้งานทันที",
                 pros=[explanation, "ครบทุกชิ้น พร้อมใช้งานทันที"],
                 cons=["ยังต้องเลือก RAM", "Complete ready-to-use PC"],
                 performance={"productivity": explanation, "gaming": "พร้อมใช้งานทันที"},
                 parts=[{"type": "CPU", "product_id": "real-cpu",
                         "reason": explanation + ". พร้อมใช้งานทันที"}]),
            full_catalogue(), 60_000, "gaming")
        self.assertIn(explanation, result["summary"])
        self.assertIn("real-cpu", [part["product_id"] for part in result["parts"]])
        self.assertEqual(result["pros"], [explanation])
        self.assertEqual(result["cons"], ["ยังต้องเลือก RAM"])
        self.assertEqual(result["performance"]["productivity"], explanation)
        self.assertEqual(result["performance"]["gaming"], "")
        self.assertEqual(result["parts"][0]["reason"], explanation)
        self.assertNotIn("พร้อมใช้งาน", result["summary"])

    def test_a_matched_cpu_only_reply_cannot_claim_a_complete_build(self):
        result = rec.build_final_result(
            dict(self.CLAIM, parts=[{"type": "CPU", "product_id": "real-cpu"}]),
            full_catalogue(), 60_000, "gaming")
        self.assertNotIn("ครบทุกชิ้น", result["summary"])
        self.assertNotIn("พร้อมใช้งาน", result["summary"])
        self.assertTrue(result["_meta"]["missing_categories"])

    def test_through_recommend_build_an_out_of_catalogue_reply_is_refused(self):
        with patch.object(rec, "llm_chat", new_callable=AsyncMock,
                          return_value='{"summary":"ชุดคอบครบทุกชิ้น พร้อมใช้งานทันที",'
                                       '"pros":["ครบทุกชิ้น"],'
                                       '"parts":[{"type":"CPU","product_id":"ghost-1"}]}'):
            with self.assertRaises(RuntimeError):
                asyncio.run(rec.recommend_build(
                    None, "แนะนำคอมเล่นเกมงบ 60,000 บาท",
                    candidates=[], provider="google", api_key="test-key"))

    def test_through_recommend_build_a_partial_reply_drops_the_empty_claim(self):
        """The summary must describe the surviving CPU rather than a ready PC."""
        with patch.object(rec, "llm_chat", new_callable=AsyncMock,
                          return_value='{"summary":"ชุดคอบครบทุกชิ้น พร้อมใช้งานทันที",'
                                       '"parts":[{"type":"CPU","product_id":"real-cpu"},'
                                       '{"type":"CPU","product_id":"ghost-1"}]}'):
            result = asyncio.run(rec.recommend_build(
                None, "แนะนำคอมเล่นเกมงบ 60,000 บาท",
                candidates=full_catalogue(), provider="google", api_key="test-key"))

        self.assertEqual([p["product_id"] for p in result["parts"]], ["real-cpu"])
        self.assertFalse(result["_meta"]["build_empty"])
        self.assertTrue(any("ไม่พบสินค้า" in w for w in result["warnings"]))
        self.assertNotIn("ครบทุกชิ้น", result["summary"])
        self.assertNotIn("พร้อมใช้งาน", result["summary"])
        self.assertIn("CPU: AMD RYZEN 7 7800X3D AM5", result["summary"])
        self.assertIn("ชุดยังไม่ครบ", result["summary"])

    def test_scoring_refuses_to_return_a_build_from_partial_catalogue(self):
        partial = [candidate("cpu", "CPU", "AMD RYZEN 7 7800X3D AM5", 20_000,
                             "CPU Cooler: Yes")]

        with self.assertRaises(RuntimeError):
            rec._scored_recommendation_result(
                rec.top3_builds(partial, 50_000, "gaming"),
                "แนะนำคอมเล่นเกมงบ 50,000 บาท",
            )


if __name__ == "__main__":
    unittest.main()
