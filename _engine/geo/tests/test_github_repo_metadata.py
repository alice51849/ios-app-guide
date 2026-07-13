#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
GEO = os.path.dirname(HERE)
if GEO not in sys.path:
    sys.path.insert(0, GEO)

import sync_github_repo_metadata as metadata


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


class GitHubRepositoryMetadataTests(unittest.TestCase):
    def test_live_apps_map_to_only_their_support_repositories(self):
        grouped = metadata.group_apps_by_repository(LIVE_KEYS)
        self.assertEqual(21, len(grouped))
        self.assertEqual(
            ["lumibopomofo", "lumibopomofopro"],
            grouped["lumi-support"],
        )
        self.assertEqual(
            ["lumiletters", "lumiletterspro"],
            grouped["lumi-letters-support"],
        )
        self.assertEqual(["lumiweather"], grouped["lumi-weather-support"])
        self.assertEqual(["mochi"], grouped["mochitodo-support"])
        self.assertEqual(["sononote"], grouped["sono-note-support"])
        self.assertEqual(["tripplanet"], grouped["trip-planet-support"])
        for unlisted in ("astrea-support", "zafe-support"):
            self.assertNotIn(unlisted, grouped)

    def test_desired_metadata_is_searchable_bounded_and_deterministic(self):
        desired = metadata.desired_repositories(LIVE_KEYS)
        self.assertEqual(37, len(desired))
        self.assertEqual(
            desired,
            metadata.desired_repositories(reversed(sorted(LIVE_KEYS))),
        )
        for repository, values in desired.items():
            if "description" in values:
                self.assertLessEqual(len(values["description"]), 350)
            if "homepage" in values:
                self.assertTrue(values["homepage"].startswith("https://"))
            if "topics" in values:
                self.assertLessEqual(len(values["topics"]), metadata.TOPIC_LIMIT)
                self.assertEqual(
                    len(values["topics"]), len(set(values["topics"]))
                )
                for topic in values["topics"]:
                    self.assertRegex(topic, metadata.TOPIC_PATTERN)
                    self.assertLessEqual(len(topic), 50)
        self.assertEqual(
            f"https://{metadata.OWNER}.github.io/snapport-support/",
            desired["snapport-support"]["homepage"],
        )
        self.assertIn(
            "zhuyin", desired["lumi-support"]["topics"]
        )
        self.assertIn(
            "passport-photo", desired["snapport-support"]["topics"]
        )
        self.assertIn(
            "white-noise", desired["sereno-support"]["topics"]
        )
        self.assertEqual(
            f"{metadata.SITE}/kids-learning.html",
            desired["awesome-ios-kids-learning"]["homepage"],
        )
        self.assertIn(
            "passport-photo",
            desired["awesome-ios-photo-utilities"]["topics"],
        )
        self.assertIn(
            "machine-readable", desired["lumi-open-data"]["topics"]
        )
        self.assertEqual(
            {"homepage"},
            set(desired["awesome-ios-language-learning"]),
        )

    def test_metadata_changes_are_idempotent_and_field_specific(self):
        desired = {
            "description": "Support",
            "homepage": "https://example.com/",
            "topics": ("ios", "iphone"),
        }
        self.assertEqual({}, metadata.metadata_changes(desired, desired))
        self.assertEqual(
            {},
            metadata.metadata_changes(
                {
                    "description": "Support",
                    "homepage": "https://example.com/",
                    "topics": ["iphone", "ios"],
                },
                desired,
            ),
        )
        self.assertEqual(
            {"topics": ("ios", "iphone")},
            metadata.metadata_changes(
                {
                    "description": "Support",
                    "homepage": "https://example.com/",
                    "topics": [],
                },
                desired,
            ),
        )
        self.assertEqual(
            {},
            metadata.metadata_changes(
                {"homepage": "https://example.com/", "topics": ["legacy"]},
                {"homepage": "https://example.com/"},
            ),
        )
        self.assertEqual(
            {"homepage": "https://new.example/"},
            metadata.metadata_changes(
                {"homepage": "https://example.com/"},
                {"homepage": "https://new.example/"},
            ),
        )

    def test_topic_normalization_rejects_empty_or_malformed_results(self):
        self.assertEqual("voice-to-text", metadata.topic_slug("Voice to Text"))
        self.assertEqual("photo-and-video", metadata.topic_slug("Photo & Video"))
        for topic in metadata.topics_for_apps(["snapport"]):
            self.assertTrue(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", topic))


if __name__ == "__main__":
    unittest.main()
