import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import answer_deep  # noqa: E402
import answer_facts  # noqa: E402
import queries  # noqa: E402


QUESTION = (
    "What is the difference between Lumi Bopomofo free and Pro, "
    "and is the one-time purchase worth it?"
)


class BopomofoProRescueTests(unittest.TestCase):
    def test_pro_query_lists_are_independent(self):
        for pro_key, free_key in queries._PRO_INHERITS.items():
            self.assertIsNot(queries.CURATED[pro_key], queries.CURATED[free_key])

    def test_pro_inherits_shared_queries_without_leaking_pro_only_query(self):
        shared = "best app to learn zhuyin bopomofo for kids"
        self.assertIn(shared, queries.CURATED["lumibopomofo"])
        self.assertIn(shared, queries.CURATED["lumibopomofopro"])
        self.assertNotIn(QUESTION, queries.CURATED["lumibopomofo"])
        self.assertIn(QUESTION, queries.CURATED["lumibopomofopro"])
        self.assertIn(
            QUESTION,
            answer_deep.ALL_DEEP_QUERIES["lumibopomofopro"],
        )

    def test_no_pro_deep_query_leaks_to_any_free_edition(self):
        for pro_key, free_key in queries._PRO_INHERITS.items():
            leaked = set(
                answer_deep.ALL_DEEP_QUERIES.get(pro_key, [])
            ).intersection(queries.CURATED[free_key])
            self.assertEqual(set(), leaked, f"{pro_key} leaked into {free_key}")

    def test_comparison_is_first_party_price_dated_and_non_promissory(self):
        app = {
            "name": "Lumi Bopomofo Pro",
            "cta_bullets": ["Pay once", "No ads", "Kid-safe"],
        }
        content = answer_facts.topic_facts(
            QUESTION, "lumibopomofopro", app
        )
        self.assertIsNotNone(content)
        rendered = json.dumps(content, ensure_ascii=False).lower()
        self.assertIn("we develop both lumi bopomofo apps", rendered)
        self.assertIn("nt$290", rendered)
        self.assertIn("17 july 2026", rendered)
        self.assertIn("prices can change", rendered)
        self.assertIn("cannot guarantee a learning outcome", rendered)
        self.assertIn("start with the free app", rendered)
        self.assertEqual("2026-07-17", content["date_modified"])
        self.assertEqual(2, len(content["sources"]))


if __name__ == "__main__":
    unittest.main()
