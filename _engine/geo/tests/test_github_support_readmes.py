#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
GEO = os.path.dirname(HERE)
if GEO not in sys.path:
    sys.path.insert(0, GEO)

import sync_github_support_readmes as readmes


LIVE_KEYS = {
    "aim990",
    "cvdesk",
    "cyca",
    "gmoney",
    "hourstag",
    "lockhour",
    "lumibopomofo",
    "lumibopomofopro",
    "lumiletters",
    "lumiletterspro",
    "lumimath",
    "lumimathpro",
    "lumimission",
    "lumimissionpro",
    "lumiweather",
    "mochi",
    "photocream",
    "picclear",
    "scanto",
    "sereno",
    "snapport",
    "sononote",
    "tripbee",
    "tripplanet",
    "unblurry",
}


class GitHubSupportReadmeTests(unittest.TestCase):
    def test_every_live_app_has_one_direct_store_link(self):
        blocks = readmes.desired_blocks(LIVE_KEYS)
        self.assertEqual(21, len(blocks))
        self.assertIn("trip-planet-support", blocks)
        combined = "\n".join(blocks.values())
        for key in LIVE_KEYS:
            store_url = readmes.app_store_url(key)
            guide_url = f"{readmes.SITE}/guides/{key}.html"
            self.assertEqual(1, combined.count(f"]({store_url})"))
            self.assertEqual(1, combined.count(f"]({guide_url})"))

    def test_multi_app_repository_lists_both_variants(self):
        block = readmes.desired_blocks(LIVE_KEYS)["lumi-support"]
        self.assertIn("### Lumi Bopomofo\n", block)
        self.assertIn("### Lumi Bopomofo Pro\n", block)
        self.assertEqual(1, block.count(readmes.START_MARKER))
        self.assertEqual(1, block.count(readmes.END_MARKER))

    def test_merge_preserves_existing_documentation_and_is_idempotent(self):
        original = "# Existing support notes\n\nKeep this.\n"
        block = readmes.render_managed_block(
            "snapport-support", ["snapport"]
        )
        merged = readmes.merge_managed_block(original, block)
        self.assertTrue(merged.startswith(original.rstrip()))
        self.assertIn(block, merged)
        self.assertEqual(merged, readmes.merge_managed_block(merged, block))

    def test_replace_changes_only_the_managed_block(self):
        old = (
            "# Existing\n\n"
            f"{readmes.START_MARKER}\nold\n{readmes.END_MARKER}\n\n"
            "After\n"
        )
        new_block = (
            f"{readmes.START_MARKER}\nnew\n{readmes.END_MARKER}"
        )
        replaced = readmes.merge_managed_block(old, new_block)
        self.assertEqual(
            "# Existing\n\n"
            f"{readmes.START_MARKER}\nnew\n{readmes.END_MARKER}\n\n"
            "After\n",
            replaced,
        )

    def test_stale_block_removal_preserves_unmanaged_content(self):
        content = (
            "# Existing\n\n"
            f"{readmes.START_MARKER}\nold\n{readmes.END_MARKER}\n\n"
            "After\n"
        )
        self.assertEqual(
            "# Existing\n\nAfter\n",
            readmes.remove_managed_block(content),
        )

    def test_malformed_markers_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "malformed"):
            readmes.merge_managed_block(readmes.START_MARKER, "new")
        with self.assertRaisesRegex(ValueError, "malformed"):
            readmes.merge_managed_block(
                (
                    f"{readmes.START_MARKER}\na\n{readmes.END_MARKER}\n"
                    f"{readmes.START_MARKER}\nb\n{readmes.END_MARKER}"
                ),
                "new",
            )
        with self.assertRaisesRegex(ValueError, "malformed"):
            readmes.merge_managed_block(
                f"{readmes.END_MARKER}\n{readmes.START_MARKER}",
                "new",
            )

    def test_put_readme_accepts_a_stale_cleanup_message(self):
        with mock.patch.object(readmes, "gh_api") as api:
            readmes.put_readme(
                "example-support",
                "main",
                "README.md",
                "content",
                "abc123",
                message=readmes.REMOVE_MESSAGE,
            )
        self.assertEqual(readmes.REMOVE_MESSAGE, api.call_args.args[1]["message"])


if __name__ == "__main__":
    unittest.main()
