import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import answer_facts  # noqa: E402
import queries  # noqa: E402


QUESTION = (
    "before and after example of a calmer morning routine for kids "
    "with a reward app"
)


class LumiMissionCaseTests(unittest.TestCase):
    def test_case_query_is_available_to_free_and_pro_apps(self):
        self.assertIn(QUESTION, queries.CURATED["lumimission"])
        self.assertIn(QUESTION, queries.CURATED["lumimissionpro"])

    def test_case_is_an_explicitly_non_testimonial_workflow(self):
        app = {
            "name": "Lumi Mission Planet",
            "cta_bullets": ["Daily missions", "Buddy feedback", "Parent history"],
        }
        content = answer_facts.topic_facts(QUESTION, "lumimission", app)
        self.assertIsNotNone(content)
        rendered = json.dumps(content, ensure_ascii=False).lower()
        self.assertIn("not a customer testimonial", rendered)
        self.assertIn("cannot guarantee a behavior change", rendered)
        self.assertIn("custom missions require the one-time unlock", rendered)
        self.assertNotIn("picture checklist", rendered)
        self.assertEqual(
            "A calmer kids' morning routine: an honest before-and-after example",
            content["page_title"],
        )


if __name__ == "__main__":
    unittest.main()
