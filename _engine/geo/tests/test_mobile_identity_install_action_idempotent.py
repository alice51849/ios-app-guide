"""InstallAction injection must be idempotent across daily runs.

gen_mobile_app_identity writes a canonical ``https://apps.apple.com/app/id…``
InstallAction; gen_store_attribution later rewrites that target to a
storefront + campaign URL (``/us/app/id…?pt=…&ct=geo_ask&mt=8``).  The next
identity pass used to miss the attributed action and append another one, so
answers pages grew one InstallAction per run (~200 by October 2026).
"""

import json
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import gen_mobile_app_identity as identity  # noqa: E402

APP_ID = "6788236641"
CANONICAL = f"https://apps.apple.com/app/id{APP_ID}"
ATTRIBUTED = f"https://apps.apple.com/us/app/id{APP_ID}?pt=118326163&ct=geo_ask&mt=8"


def _attribute(value):
    """Mimic gen_store_attribution's storefront + campaign rewrite."""
    text = json.dumps(value)
    text = text.replace(CANONICAL, ATTRIBUTED)
    return json.loads(text)


def _actions(value):
    return value if isinstance(value, list) else [value]


def _page(body: str) -> str:
    return (
        "<html><head><script type=\"application/ld+json\">"
        + body
        + "</script></head><body></body></html>"
    )


def _ld_bodies(source: str):
    return [
        json.loads(match.group("body"))
        for match in identity.JSON_LD_RE.finditer(source)
    ]


class InstallActionIdempotenceTest(unittest.TestCase):
    def test_attributed_target_is_recognised_not_appended(self):
        result = identity._install_action(
            {"@type": "InstallAction", "target": ATTRIBUTED}, APP_ID
        )
        self.assertEqual(
            result, {"@type": "InstallAction", "target": CANONICAL}
        )

    def test_identity_then_attribution_loop_stays_at_one_action(self):
        value = None
        for _ in range(10):
            value = identity._install_action(value, APP_ID)
            value = _attribute(value)
        self.assertEqual(len(_actions(value)), 1)
        self.assertEqual(_actions(value)[0]["target"], ATTRIBUTED)

    def test_existing_duplicates_collapse_to_one(self):
        duplicated = [{"@type": "InstallAction", "target": ATTRIBUTED}] * 198
        result = identity._install_action(duplicated, APP_ID)
        self.assertEqual(
            result, {"@type": "InstallAction", "target": CANONICAL}
        )

    def test_unrelated_actions_are_preserved(self):
        search = {"@type": "SearchAction", "target": "https://example.com/?q={q}"}
        result = identity._install_action(
            [search, {"@type": "InstallAction", "target": ATTRIBUTED}, search],
            APP_ID,
        )
        self.assertEqual(
            result,
            [search, {"@type": "InstallAction", "target": CANONICAL}],
        )

    def test_unmanaged_cleanup_removes_attributed_install_actions(self):
        remaining = identity._without_managed_install_actions(
            [{"@type": "InstallAction", "target": ATTRIBUTED}], {APP_ID}
        )
        self.assertIsNone(remaining)


class DedupeExistingPagesTest(unittest.TestCase):
    def test_compact_block_is_deduped_and_rest_untouched(self):
        actions = [{"@type": "InstallAction", "target": ATTRIBUTED}] * 199
        node = {
            "@context": "https://schema.org",
            "@type": "MobileApplication",
            "@id": CANONICAL,
            "potentialAction": actions,
            "name": "ShotInbox",
        }
        source = _page(json.dumps(node, separators=(",", ":")))
        updated = identity.dedupe_install_actions(source)
        self.assertIsNotNone(updated)
        self.assertEqual(updated.count('"InstallAction"'), 1)
        (document,) = _ld_bodies(updated)
        self.assertEqual(
            document["potentialAction"],
            [{"@type": "InstallAction", "target": ATTRIBUTED}],
        )
        strip = lambda text: re.sub(r'"potentialAction":\[.*?\]', "", text)
        self.assertEqual(strip(source), strip(updated))
        self.assertIsNone(identity.dedupe_install_actions(updated))

    def test_indented_block_stays_valid_json(self):
        node = {
            "@type": "MobileApplication",
            "potentialAction": [
                {"@type": "InstallAction", "target": CANONICAL},
                {"@type": "InstallAction", "target": ATTRIBUTED},
            ],
            "name": "ShotInbox",
        }
        source = _page("\n" + json.dumps(node, indent=2) + "\n")
        updated = identity.dedupe_install_actions(source)
        (document,) = _ld_bodies(updated)
        self.assertEqual(
            document["potentialAction"],
            [{"@type": "InstallAction", "target": CANONICAL}],
        )
        self.assertEqual(document["name"], "ShotInbox")
        self.assertIsNone(identity.dedupe_install_actions(updated))

    def test_distinct_apps_are_kept(self):
        other = "https://apps.apple.com/us/app/id1234567890?pt=1&ct=geo_ask&mt=8"
        node = {
            "potentialAction": [
                {"@type": "InstallAction", "target": ATTRIBUTED},
                {"@type": "InstallAction", "target": other},
            ]
        }
        self.assertIsNone(
            identity.dedupe_install_actions(_page(json.dumps(node)))
        )

    def test_dedupe_existing_rewrites_only_duplicated_pages(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dup = root / "answers" / "dup.html"
            clean = root / "answers" / "clean.html"
            dup.parent.mkdir()
            dup.write_text(
                _page(json.dumps({"potentialAction": [
                    {"@type": "InstallAction", "target": ATTRIBUTED}
                ] * 3})),
                encoding="utf-8",
            )
            clean_source = _page(json.dumps({"potentialAction": {
                "@type": "InstallAction", "target": ATTRIBUTED
            }}))
            clean.write_text(clean_source, encoding="utf-8")
            self.assertEqual(identity.dedupe_existing(root), 1)
            self.assertEqual(dup.read_text().count("InstallAction"), 1)
            self.assertEqual(clean.read_text(), clean_source)
            self.assertEqual(identity.dedupe_existing(root), 0)


if __name__ == "__main__":
    unittest.main()
