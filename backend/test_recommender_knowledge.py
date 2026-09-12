import unittest

import recommender


class RecommenderKnowledgeTests(unittest.TestCase):
    def test_candidate_prompt_contains_normalized_power_facts_and_source(self):
        source = "https://shop.example/gpu-r9700"
        candidate = {
            "product_id": "gpu-1",
            "category": "GPU",
            "name": "SAPPHIRE RADEON AI PRO R9700 32GB GDDR6",
            "price": 60800,
            "specs": (
                "TDP: 300 W\n"
                "TDP Source Store: advice\n"
                f"TDP Source URL: {source}\n"
                "Recommended PSU: 750 W\n"
                f"Recommended PSU Source URL: {source}\n"
                "Power Connectors: 1 x 12VHPWR"
            ),
        }
        text = recommender.candidates_to_text([candidate])
        self.assertIn("board power=300W", text)
        self.assertIn("minimum system PSU=750W", text)
        self.assertIn("GPU power input=12VHPWR x1", text)
        self.assertIn(source, text)


if __name__ == "__main__":
    unittest.main()
