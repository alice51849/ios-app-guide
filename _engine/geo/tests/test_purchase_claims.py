"""買斷／無訂閱字樣只給證實是一次購買的款（不實價格字樣防線）。"""

from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
GEO = HERE.parent
sys.path.insert(0, str(GEO.parent / "social"))
sys.path.insert(0, str(GEO))

import purchase_types  # noqa: E402
from videogen.registry import APPS, APPSTORE  # noqa: E402

ONE_TIME_MODELS = {"paid_upfront", "free_with_lifetime_unlock", "flexible"}
APP_ID_RE = re.compile(r"apps\.apple\.com/[^\"'\s]*?/id(\d+)|apps\.apple\.com/app/id(\d+)")
FEATURE_LIST_RE = re.compile(r'"featureList":\[(.*?)\]')
PILL_RE = re.compile(r'<span class="(?:pill|iag-decision-card__fact)"[^>]*>(.*?)</span>')


def _pages_root() -> Path | None:
    candidates = [os.environ.get("GEO_PAGES"), str(GEO / "pages"), str(GEO.parent.parent)]
    for value in candidates:
        if value and (Path(value) / "answers").is_dir():
            return Path(value)
    return None


class VerifiedPurchaseTypesTest(unittest.TestCase):
    def test_every_app_has_a_known_type(self):
        data = purchase_types.load()
        for key in APPSTORE:
            self.assertIn(key, data, key)
            self.assertIn(data[key]["type"], purchase_types.TYPES, key)
            self.assertTrue(data[key]["evidence"], key)

    def test_registry_one_time_claims_need_evidence(self):
        for key, app in APPS.items():
            if key not in APPSTORE:
                continue
            claims = [str(v) for v in app.get("cta_bullets", [])] + [str(app.get("tag", ""))]
            claims_one_time = app.get("purchase_model") in ONE_TIME_MODELS or any(
                purchase_types.is_purchase_claim(text) for text in claims
            )
            if claims_one_time:
                self.assertTrue(
                    purchase_types.one_time_verified(key),
                    f"{key}: 登錄檔寫一次購買，但 verified_purchase_types.json 沒有證據",
                )

    def test_mochi_is_verified_non_consumable(self):
        entry = purchase_types.load()["mochi"]
        self.assertEqual(purchase_types.ONE_TIME_UNLOCK, entry["type"])
        self.assertIn("NON_CONSUMABLE", entry["evidence"])
        self.assertIn("com.alice51849.MochiTodo.premium", entry["evidence"])

    def test_classify_rules(self):
        fetched = "2026-09-06"
        sub = purchase_types.classify("x", {"x": {"subscription": True, "unlock_iap": True, "products": ["p"]}}, {}, fetched)
        self.assertEqual(purchase_types.SUBSCRIPTION, sub["type"])
        once = purchase_types.classify("x", {"x": {"subscription": False, "unlock_iap": True, "products": ["p"]}}, {}, fetched)
        self.assertEqual(purchase_types.ONE_TIME_UNLOCK, once["type"])
        paid = purchase_types.classify(
            "x", {"x": {"subscription": False, "unlock_iap": False, "products": []}},
            {"x": {"en": {"price": 4.99}}}, fetched,
        )
        self.assertEqual(purchase_types.PAID_UPFRONT, paid["type"])
        with mock.patch.object(purchase_types, "_store_description", return_value="Premium, an in-app purchase."):
            self.assertEqual(purchase_types.UNKNOWN, purchase_types.classify("x", {}, {}, fetched)["type"])
        with mock.patch.object(
            purchase_types, "_store_description",
            return_value="Lifetime access or $2.99 per month, auto-renews.",
        ):
            self.assertEqual(purchase_types.UNKNOWN, purchase_types.classify("x", {}, {}, fetched)["type"])
        with mock.patch.object(
            purchase_types, "_store_description",
            return_value="One optional Lifetime purchase unlocks more, with no subscription.",
        ):
            self.assertEqual(purchase_types.ONE_TIME_UNLOCK, purchase_types.classify("x", {}, {}, fetched)["type"])

    def test_claim_patterns_cover_locales(self):
        for text in ("Pay once", "No subscription", "一次買斷", "終生購買", "買い切り", "평생 이용", "Lifetime Pro"):
            self.assertTrue(purchase_types.is_purchase_claim(text), text)
        for text in ("No ads", "Free to start", "Offline", "Simple"):
            self.assertFalse(purchase_types.is_purchase_claim(text), text)


class GeneratorGateTest(unittest.TestCase):
    def _unverified(self, key):
        data = dict(purchase_types.load())
        data[key] = {"type": purchase_types.UNKNOWN, "evidence": "test"}
        return mock.patch.object(purchase_types, "load", return_value=data)

    def test_aeo_attrs_drop_claims_for_unknown_and_subscription(self):
        import aeo_pages

        key = "mochi"
        self.assertTrue(aeo_pages.app_attrs(key)["Pay once"])
        with self._unverified(key):
            attrs = aeo_pages.app_attrs(key)
        self.assertFalse(attrs["Pay once"])
        self.assertFalse(attrs["No subscription"])
        data = dict(purchase_types.load())
        data[key] = {"type": purchase_types.SUBSCRIPTION, "evidence": "test"}
        with mock.patch.object(purchase_types, "load", return_value=data):
            attrs = aeo_pages.app_attrs(key)
        self.assertFalse(attrs["Pay once"])
        self.assertFalse(attrs["No subscription"])

    def test_decision_card_facts_omit_claims_for_unverified(self):
        import gen_app_decision_cards as cards

        source = (
            '<p><span class="pill">Free to start</span><span class="pill">Pay once</span>'
            '<span class="pill">No subscription</span><span class="pill">No ads</span></p>'
        )
        self.assertIn("Pay once", cards._facts(source, True, "mochi"))
        with self._unverified("mochi"):
            facts = cards._facts(source, True, "mochi")
        self.assertEqual(["Free to start", "No ads"], facts)


class PublishedPagesTest(unittest.TestCase):
    def test_answer_pages_claim_one_time_only_for_verified_apps(self):
        root = _pages_root()
        if root is None:
            self.skipTest("指南站頁面不在這個 checkout（GEO_PAGES／geo/pages／指南站根目錄都沒有 answers/）")
        id_to_key = {str(app_id): key for key, app_id in APPSTORE.items()}
        problems = []
        for path in sorted((root / "answers").glob("*.html")):
            text = path.read_text(encoding="utf-8", errors="replace")
            claims = [m.group(1) for m in PILL_RE.finditer(text)]
            for block in FEATURE_LIST_RE.findall(text):
                claims.extend(re.findall(r'"([^"]*)"', block))
            if not any(purchase_types.is_purchase_claim(c) for c in claims):
                continue
            match = APP_ID_RE.search(text)
            app_id = next((g for g in match.groups() if g), "") if match else ""
            key = id_to_key.get(app_id, "")
            if not purchase_types.one_time_verified(key):
                problems.append(f"{path.name}: {key or app_id or '?'}")
        self.assertEqual([], problems[:20])


if __name__ == "__main__":
    unittest.main()
