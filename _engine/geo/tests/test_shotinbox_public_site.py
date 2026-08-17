#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path
import sys
import unittest


GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import shotinbox_public_site


class ShotInboxPublicSiteTests(unittest.TestCase):
    def test_public_site_matches_durable_generator(self) -> None:
        result = shotinbox_public_site.validate_site()
        self.assertEqual(
            {"locales": 50, "pages": 200, "page_types": 4},
            result,
        )

    def test_public_contract_has_one_email_and_no_source_app_claim(self) -> None:
        localized = shotinbox_public_site.load_localized_copy()
        self.assertEqual(
            set(shotinbox_public_site.OFFICIAL_LOCALES),
            set(localized),
        )
        self.assertEqual(
            "hourstag.app@gmail.com",
            shotinbox_public_site.SUPPORT_EMAIL,
        )
        english = localized["en-US"]
        self.assertIn("not the source app", english["limits_alerts"])
        self.assertIn("not real-time or guaranteed", english["limits_alerts"])
        self.assertIn(
            "does not upload screenshot data",
            english["privacy_data"],
        )
        self.assertIn("not original screenshots", english["extensions_backup"])


if __name__ == "__main__":
    unittest.main()
