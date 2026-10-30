#!/usr/bin/env python3
"""Finder summaries skip only exact device-compatibility lead paragraphs."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent
GEO = HERE.parent
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import build_pages_i18n
import portfolio_app_finder


DUO_NOTE = (
    "Optimized for iPhone Duo. Built with the latest SDK, the app fills the "
    "entire inner display and automatically adjusts its layout whether the "
    "device is folded or open."
)
FEATURE_LEAD = (
    "A calculator you will actually keep using, because it remembers the "
    "thinking behind each number."
)


class DeviceNoteSummaryTests(unittest.TestCase):
    def summary(self, key: str, description: str) -> str:
        with mock.patch.object(
            build_pages_i18n,
            "external_localized_values",
            return_value={"description": description},
        ), mock.patch.dict(portfolio_app_finder.APPS[key], {"sub": ""}):
            return portfolio_app_finder.store_copy_summary(key, "en-US")

    def test_listed_paragraphs_cover_every_locale_and_match_claim_source(self):
        payload = json.loads(
            portfolio_app_finder.DEVICE_NOTE_PARAGRAPHS_PATH.read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(DUO_NOTE, payload["paragraphs"]["en-US"])
        self.assertIn(DUO_NOTE, portfolio_app_finder.device_note_paragraphs())
        claim = GEO.parent / "aso" / "duo" / "claim_lines.json"
        if claim.is_file():
            source = json.loads(claim.read_text(encoding="utf-8"))
            self.assertEqual(
                source["description_block"], payload["paragraphs"]
            )

    def test_device_note_lead_falls_through_to_second_paragraph(self):
        description = f"{DUO_NOTE}\n\n{FEATURE_LEAD} More detail follows.\n\nThird."
        self.assertEqual(
            f"{FEATURE_LEAD} More detail follows.",
            self.summary("caldaily", description),
        )
        # Localized note (de-DE) is skipped too, by exact paragraph match.
        de_note = json.loads(
            portfolio_app_finder.DEVICE_NOTE_PARAGRAPHS_PATH.read_text(
                encoding="utf-8"
            )
        )["paragraphs"]["de-DE"]
        self.assertEqual(
            f"{FEATURE_LEAD} More detail follows.",
            self.summary(
                "caldaily", f"{de_note}\n\n{FEATURE_LEAD} More detail follows."
            ),
        )

    def test_unlisted_paragraphs_keep_prior_behavior(self):
        # A paragraph that merely starts like the note is not an exact match.
        partial = "Optimized for iPhone Duo. Track every receipt in one tap."
        self.assertEqual(
            "Optimized for iPhone Duo. Track every receipt in one tap.",
            self.summary("caldaily", f"{partial}\n\n{FEATURE_LEAD}"),
        )
        self.assertEqual(
            FEATURE_LEAD, self.summary("caldaily", f"{FEATURE_LEAD}\n\nNext one.")
        )

    def test_lite_pro_shared_paragraph_is_not_skipped(self):
        shared = (
            "Getting a small child to brush teeth, finish meals or tidy toys "
            "should not take a battle every single day."
        )
        for key in ("lumimission", "lumimissionpro"):
            with self.subTest(key=key):
                self.assertEqual(
                    shared,
                    self.summary(key, f"{DUO_NOTE}\n\n{shared}\n\nMore copy."),
                )
                self.assertEqual(
                    shared, self.summary(key, f"{shared}\n\nMore copy.")
                )


if __name__ == "__main__":
    unittest.main()
