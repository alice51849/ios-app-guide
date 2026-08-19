#!/usr/bin/env python3
"""Fail closed when a translation recommends a different portfolio app.

2026-08-18..20: the daily GEO rebuild stayed red for two days because sixteen
zh-Hant travel-expense answers led with "Snapport 之外,G+Money Lite ..." while
the page itself links G+Money Lite.  The English source never mentioned
Snapport -- the clause was invented inside the translation memory, so every
page built from that entry sent readers of one app's page to another app.

`reconcile_answer_semantics.py` catches it at publish time, but only after the
bad copy is already committed and only for the page lead.  This test catches it
at the source: the shared per-locale dictionaries every localized page is
rendered from.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from official_locales import OFFICIAL_LOCALES  # noqa: E402
import aeo_answers_i18n  # noqa: E402


TRANS_DIR = ROOT / "i18n_trans"


class TranslationMemoryAppNameTests(unittest.TestCase):
    def test_detector_catches_the_historical_regression(self) -> None:
        """Guard the guard: the 2026-08 defect must still be detected."""
        source = (
            "For a short trip, a useful free-to-start tracker should let you "
            "log a few local-currency expenses — G+Money Lite is built for this."
        )
        injected = (
            "短程旅行時,好用的免費記帳工具應該讓你先記幾筆當地幣別的支出 — "
            "Snapport 之外,G+Money Lite 正是這樣設計的。"
        )
        self.assertEqual(
            ["Snapport"],
            aeo_answers_i18n.cross_app_names_introduced(source, injected),
        )

    def test_sibling_editions_are_not_treated_as_a_different_app(self) -> None:
        """A Pro/base slip is a naming bug, not a cross-app recommendation."""
        self.assertEqual(
            [],
            aeo_answers_i18n.cross_app_names_introduced(
                "We develop Lumi Math Pro, a pay-once kids early math app.",
                "Wir entwickeln Lumi Math Planet, eine Frühmathe-App.",
            ),
        )

    def test_locale_dictionaries_never_introduce_another_app(self) -> None:
        offenders: list[str] = []
        for locale in sorted(OFFICIAL_LOCALES):
            path = TRANS_DIR / f"{locale}.json"
            if not path.is_file():
                continue
            entries = json.loads(path.read_text(encoding="utf-8"))
            for source, target in entries.items():
                if not isinstance(target, str):
                    continue
                # An entry whose English side names no app carries no app
                # identity to contradict -- naming the page's own app there is
                # a phrasing choice the page-level check already covers.
                if not aeo_answers_i18n.portfolio_app_names_in(source):
                    continue
                introduced = aeo_answers_i18n.cross_app_names_introduced(
                    source,
                    target,
                )
                if introduced:
                    offenders.append(
                        f"{locale}: {introduced} added to {source[:70]!r} "
                        f"-> {target[:70]!r}"
                    )
        self.assertEqual([], offenders, "\n".join(offenders))


if __name__ == "__main__":
    unittest.main()
