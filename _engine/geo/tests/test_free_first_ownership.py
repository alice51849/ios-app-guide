#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""免費門歸屬(free_first_ownership)+ 付費門頁重生(reclaim)+ 稽核 gate。

2026-09-05 稽核:38 條「付費事實斷言付費模式、所以不換門」的 answer 頁裡,有
7 條其實是免費兄弟版能誠實回答的品類問句(Lumi 四對的 _PRO_INHERITS 共用題、
WiFi Aid Lite persona 已涵蓋的 Wi-Fi 診斷題),卻因為頁面由付費 key 產生而停在
頁→下載 0–2.7% 的付費門。這支測試把三件事釘住:
  • 歸屬規則只搬那一類(付費事實斷言付費模式 × 免費版誠實可答),其餘不動;
  • 零內購意圖永遠歸付費版,連 _PRO_INHERITS 的跳過規則也不能把它讓給免費版;
  • reclaim 只重生「只帶付費 id」的既有頁,免費版不公開或答不出來就保留,
    --check 有待處理頁即 exit 1(fail-closed gate),audit --strict 亦然。
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))
sys.path.insert(0, str(GEO.parents[0] / "social"))

import answer_facts  # noqa: E402
import free_first_ownership as O  # noqa: E402
import gen_free_first_links as F  # noqa: E402
import queries  # noqa: E402
import reclaim_free_first_answers as R  # noqa: E402
from app_pairs import paid_to_free  # noqa: E402
from publisher_intent_catalog import slugify  # noqa: E402
from videogen.registry import APPS, APPSTORE  # noqa: E402

ZERO_IAP = "Is there a math app for kids with no ads and no in-app purchases"
WIFI_Q1 = "how to troubleshoot wi-fi connected but no internet on iphone"
WIFI_Q2 = "how to tell if one website is down or my whole internet connection on iphone"
WIFI_Q3 = "how to document intermittent internet problems on iphone for isp support"
LUMI_COMPLETE = {
    "lumibopomofopro": "best complete zhuyin app for bilingual children",
    "lumiletterspro": "best complete phonics app for homeschool kindergarten prep",
}
MATH_COMPLETE = "best complete math learning app for preschool and early grades"


def need_pair(paid):
    if paid not in paid_to_free():
        raise unittest.SkipTest(f"{paid} pair not in registry")
    return paid_to_free()[paid]


class OwnershipRules(unittest.TestCase):
    def test_explicit_math_pro_edition_keeps_its_canonical_owner(self):
        self.assertEqual("lumimathpro", O.declared_answer_owner(MATH_COMPLETE))
        self.assertEqual("lumimathpro", O.owner_for("lumimathpro", MATH_COMPLETE))
        self.assertFalse(O.free_answers_honestly(MATH_COMPLETE, "lumimath"))
        self.assertIn(MATH_COMPLETE, queries.ALL["lumimathpro"])
        self.assertNotIn(MATH_COMPLETE, queries.ALL["lumimath"])
        self.assertEqual(
            "lumimathpro", F.paid_model_answer_slugs()[slugify(MATH_COMPLETE)]
        )
        self.assertEqual("6776958488", APPSTORE["lumimathpro"])
        self.assertEqual("6778269699", APPSTORE["lumimath"])

    def test_explicit_owner_reclaims_an_inherited_free_copy_without_duplication(self):
        result, _ = O.apply_free_first_ownership({
            "lumimath": [MATH_COMPLETE],
            "lumimathpro": [MATH_COMPLETE],
        })
        self.assertEqual([], result["lumimath"])
        self.assertEqual([MATH_COMPLETE], result["lumimathpro"])
        self.assertEqual(
            "lumimathpro", O.declared_answer_owner("  " + MATH_COMPLETE.upper() + "  ")
        )

    def test_zero_iap_intent_always_stays_with_the_paid_app(self):
        free = need_pair("lumimathpro")
        self.assertTrue(O.paid_only_intent(ZERO_IAP))
        self.assertFalse(O.free_answers_honestly(ZERO_IAP, free))
        self.assertEqual("lumimathpro", O.owner_for("lumimathpro", ZERO_IAP))
        self.assertNotIn(ZERO_IAP, queries.ALL[free])
        self.assertIn(ZERO_IAP, queries.ALL["lumimathpro"])
        self.assertIn(ZERO_IAP, queries.FREE_FIRST_MOVES["to_paid"].get(free, []))

    def test_no_free_app_with_a_paid_sibling_owns_a_zero_iap_question(self):
        for paid, free in paid_to_free().items():
            for question in queries.ALL.get(free, []):
                self.assertFalse(
                    O.paid_only_intent(question),
                    f"{free} 靠內購解鎖,不能擁有零內購題:{question}",
                )

    def test_inherited_zero_iap_question_is_not_skipped_for_the_pro(self):
        self.assertFalse(
            queries.is_inherited_query("lumimathpro", ZERO_IAP, {"lumimath", "lumimathpro"})
        )

    def test_lumi_complete_questions_moved_to_the_free_owner(self):
        for paid, question in LUMI_COMPLETE.items():
            free = need_pair(paid)
            with self.subTest(paid=paid):
                self.assertTrue(O.paid_asserts_paid_model(question, paid))
                self.assertTrue(O.free_answers_honestly(question, free))
                self.assertEqual(free, O.owner_for(paid, question))
                self.assertIn(question, queries.ALL[free])
                self.assertNotIn(question, queries.ALL[paid])

    def test_wifi_diagnostic_questions_moved_but_isp_evidence_stays_paid(self):
        free = need_pair("wifiaid")
        for question in (WIFI_Q1, WIFI_Q2):
            with self.subTest(question=question):
                facts = answer_facts.topic_facts(question, free, APPS[free])
                self.assertTrue(facts, "Lite persona 觸發詞沒對上這一題")
                self.assertFalse(F.PAID_MODEL_RESIDUE_RE.search(O.facts_text(facts)))
                self.assertIn(question, queries.ALL[free])
                self.assertNotIn(question, queries.ALL["wifiaid"])
        # 「留證據給 ISP」不在 Lite persona 的承諾內,誠實起見維持付費版。
        self.assertIn(WIFI_Q3, queries.ALL["wifiaid"])
        self.assertNotIn(WIFI_Q3, queries.ALL[free])

    def test_only_paid_model_pages_move(self):
        """歸屬只搬「付費事實斷言付費模式」那一類;其他品類問句維持原歸屬,
        門由 gen_free_first_links 換。否則 _PRO_INHERITS 的整份共用題都會被搬走。"""
        for paid, moved in queries.FREE_FIRST_MOVES["to_free"].items():
            for question in moved:
                with self.subTest(paid=paid, question=question):
                    self.assertTrue(O.paid_asserts_paid_model(question, paid))
                    self.assertTrue(O.free_answers_honestly(question, paid_to_free()[paid]))
        total = sum(len(v) for v in queries.FREE_FIRST_MOVES["to_free"].values())
        self.assertLess(total, 20, "搬動數暴增,規則可能退化成搬整份共用題")
        for paid in queries.FREE_FIRST_MOVES["to_free"]:
            self.assertGreater(len(queries.ALL[paid]), 10, f"{paid} 的題庫被搬空")

    def test_moved_questions_are_no_longer_paid_copy_exempt(self):
        """搬走之後,這些 slug 不該再被當成付費文案頁豁免;免費版重生後就是免費門。"""
        slugs = F.paid_model_answer_slugs()
        for moved in queries.FREE_FIRST_MOVES["to_free"].values():
            for question in moved:
                self.assertNotIn(slugify(question), slugs)

    def test_wordmate_lite_does_not_take_over_paid_only_feature_questions(self):
        """Lite 只有一種語言、每天五字;44 語/Watch/widget 的題免費版答不出來。"""
        free = need_pair("wordmate")
        self.assertEqual([], queries.FREE_FIRST_MOVES["to_free"].get("wordmate", []))
        for question in queries.ALL["wordmate"]:
            if O.paid_asserts_paid_model(question, "wordmate"):
                self.assertFalse(O.free_answers_honestly(question, free), question)


def fake_page(app_id):
    return (
        "<html><body><h1>x</h1>"
        f'<a class="cta" href="https://apps.apple.com/app/id{app_id}?pt=1&ct=geo_pick&mt=8">'
        "Get</a></body></html>"
    )


class ReclaimCandidates(unittest.TestCase):
    def setUp(self):
        self.paid = "wifiaid"
        self.free = need_pair(self.paid)
        self.pid, self.fid = APPSTORE[self.paid], APPSTORE[self.free]
        self.tmp = tempfile.TemporaryDirectory()
        self.pages = Path(self.tmp.name)
        (self.pages / "answers").mkdir()
        self.slug = slugify(WIFI_Q1)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, app_id):
        (self.pages / "answers" / f"{self.slug}.html").write_text(fake_page(app_id))

    def test_paid_only_page_for_a_free_owned_question_is_reclaimable(self):
        self.write(self.pid)
        reclaim, held = R.find_candidates(self.pages, queries.ALL, {self.free})
        self.assertEqual([self.slug], [row["slug"] for row in reclaim])
        self.assertEqual([], held)

    def test_free_door_page_is_left_alone(self):
        self.write(self.fid)
        reclaim, held = R.find_candidates(self.pages, queries.ALL, {self.free})
        self.assertEqual(([], []), (reclaim, held))

    def test_missing_page_is_not_a_candidate(self):
        reclaim, held = R.find_candidates(self.pages, queries.ALL, {self.free})
        self.assertEqual(([], []), (reclaim, held))

    def test_unpublished_free_app_holds_the_paid_door(self):
        self.write(self.pid)
        reclaim, held = R.find_candidates(self.pages, queries.ALL, set())
        self.assertEqual([], reclaim)
        self.assertEqual(["free_app_not_public"], [row["reason"] for row in held])

    def test_dishonest_free_facts_hold_the_paid_door(self):
        self.write(self.pid)
        all_queries = {self.free: [WIFI_Q3]}  # Lite 答不出來的題被硬掛過來
        (self.pages / "answers" / f"{slugify(WIFI_Q3)}.html").write_text(fake_page(self.pid))
        reclaim, held = R.find_candidates(self.pages, all_queries, {self.free})
        self.assertEqual([], reclaim)
        self.assertEqual(["free_facts_not_honest"], [row["reason"] for row in held])

    def test_check_mode_fails_closed_without_writing(self):
        self.write(self.pid)
        before = (self.pages / "answers" / f"{self.slug}.html").read_text()
        env = dict(os.environ, GEO_PAGES=str(self.pages), PYTHONDONTWRITEBYTECODE="1")
        env.pop("PYTHONPATH", None)
        state = self.pages / ".appstore_live_state.json"
        state.write_text(json.dumps({"live_ids": [self.fid, self.pid], "miss_counts": {}}))
        proc = subprocess.run(
            [sys.executable, str(GEO / "reclaim_free_first_answers.py"), "--check",
             "--pages-dir", str(self.pages), "--report", str(self.pages / "r.json")],
            capture_output=True, text=True, env=env, cwd=str(GEO),
        )
        self.assertEqual(1, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn(self.slug, proc.stdout)
        self.assertEqual(before, (self.pages / "answers" / f"{self.slug}.html").read_text())
        report = json.loads((self.pages / "r.json").read_text())
        self.assertTrue(report["check_only"])
        self.assertEqual([self.slug], [row["slug"] for row in report["reclaimable"]])


if __name__ == "__main__":
    unittest.main()
