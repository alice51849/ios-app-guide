#!/usr/bin/env python3
"""The store-copy guard only applies while the data description is unchanged."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import store_copy_guard  # noqa: E402

OLD = "Line one\n\nTools\n• Old feature\n• Kept feature"
NEW = "Line one\n\nTools\n• Kept feature"


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class StoreCopyGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "guard.json"
        self.path.write_text(json.dumps({"apps": {"demo": {"en-US": {
            "old_sha256": _sha(OLD),
            "description": NEW,
            "old_keywords": "a,old,b",
            "keywords": "a,b",
            "old_subtitle": "Sub・Old",
            "subtitle": "Sub",
        }}}}), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def values(self, description=OLD, keywords="a,old,b", subtitle="Sub・Old"):
        return {
            "en-US": {"description": description, "keywords": keywords,
                      "subtitle": subtitle, "name": "Demo"},
            "ja": {"description": OLD, "keywords": "x", "name": "Demo"},
        }

    def test_matching_hash_uses_filtered_copy(self):
        result = store_copy_guard.guarded_locales("demo", self.values(), self.path)
        self.assertEqual(NEW, result["en-US"]["description"])
        self.assertEqual("a,b", result["en-US"]["keywords"])
        self.assertEqual("Sub", result["en-US"]["subtitle"])
        self.assertEqual("Demo", result["en-US"]["name"])
        self.assertEqual(OLD, result["ja"]["description"])

    def test_changed_field_keeps_its_current_value(self):
        result = store_copy_guard.guarded_locales(
            "demo", self.values(keywords="a,b,c"), self.path)
        self.assertEqual(NEW, result["en-US"]["description"])
        self.assertEqual("a,b,c", result["en-US"]["keywords"])

    def test_new_description_still_filters_old_keywords(self):
        values = self.values(description=NEW + "\n• Updated")
        result = store_copy_guard.guarded_locales("demo", values, self.path)
        self.assertEqual(NEW + "\n• Updated", result["en-US"]["description"])
        self.assertEqual("a,b", result["en-US"]["keywords"])

    def test_new_subtitle_kept_as_is(self):
        values = self.values(subtitle="Fresh subtitle")
        result = store_copy_guard.guarded_locales("demo", values, self.path)
        self.assertEqual("Fresh subtitle", result["en-US"]["subtitle"])
        self.assertEqual(NEW, result["en-US"]["description"])

    def test_all_fields_updated_keeps_original(self):
        values = self.values(description=NEW + "\n• Updated",
                             keywords="a,b,c", subtitle="Fresh")
        result = store_copy_guard.guarded_locales("demo", values, self.path)
        self.assertEqual(values, result)

    def test_missing_guard_file_keeps_original(self):
        values = self.values()
        missing = Path(self.tmp.name) / "absent.json"
        self.assertEqual(values, store_copy_guard.guarded_locales("demo", values, missing))
        self.assertIsNone(store_copy_guard.guard_signature(missing))

    def test_other_app_untouched(self):
        values = self.values()
        self.assertEqual(values, store_copy_guard.guarded_locales("other", values, self.path))

    def test_shipped_guard_matches_current_data(self):
        guard = store_copy_guard.load_guard()
        root = Path(store_copy_guard.HERE).parent / "data"
        for key in ("snapport", "snapportlite"):
            data_path = root / f"{key}_full.json"
            if key not in guard or not data_path.exists():
                continue
            data = json.loads(data_path.read_text(encoding="utf-8"))
            result = store_copy_guard.guarded_locales(key, data)
            matched = 0
            for locale, row in guard[key].items():
                if _sha(data[locale]["description"]) == row["old_sha256"]:
                    matched += 1
                    self.assertEqual(row["description"], result[locale]["description"])
            self.assertGreaterEqual(matched, 1, key)


if __name__ == "__main__":
    unittest.main()
