from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))
import high_intent_decision_routes as routes
import conversion_route_contract as contracts


class ConversionFocusLocaleTests(unittest.TestCase):
    def setUp(self):
        source = json.loads(routes.SOURCE_PATH.read_text())
        self.routes = {row["app_key"]: row for row in source["routes"]}
        self.contracts = json.loads(
            (GEO / "data/high_intent_conversion_contracts_v1.json").read_text()
        )["apps"]

    def test_recent_paying_markets_have_complete_native_contracts(self):
        for app, locale in (("cyca", "zh-Hant"), ("mochidonestamp", "de-DE")):
            with self.subTest(app=app):
                route = self.routes[app]
                contract = self.contracts[app]
                self.assertEqual(set(route["locales"]), set(contract["localized"]))
                copy = contract["localized"][locale]
                routes._native_copy(locale, route["locales"][locale])
                self.assertIn(copy["free"], route["locales"][locale]["decision_rule"])
                self.assertIn(copy["paid"], route["locales"][locale]["decision_rule"])
                self.assertEqual({}, copy["asset_captions"])
                self.assertFalse(contracts.PRICE_RE.search(json.dumps(copy, ensure_ascii=False)))

    def test_german_does_not_accept_an_english_fallback(self):
        copy = deepcopy(self.routes["mochidonestamp"]["locales"]["en-US"])
        copy.update(language="de", market="Deutschland")
        copy["culture_route"] += " Deutschland"
        with self.assertRaises(ValueError):
            routes._native_copy("de-DE", copy)

    def test_german_interface_has_all_native_labels(self):
        self.assertEqual(set(routes.UI["en-US"]), set(routes.UI["de-DE"]))
        for text in routes.UI["de-DE"]["feature_labels"].values():
            routes._validate_native_text("de-DE", text)
        self.assertIn("App Store", contracts.UI["de-DE"]["price"])


if __name__ == "__main__":
    unittest.main()
