#!/usr/bin/env python3
"""Tests for clip_posts.py (no network)."""
import datetime as dt
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import clip_posts as C  # noqa: E402


def clip(app, locale):
    return {"app": app, "locale": locale, "url": f"https://files.catbox.moe/{app}_{locale}.mp4",
            "store_url": f"https://apps.apple.com/us/app/id1?pt=118326163&ct=h7_{app}_{locale}&mt=8",
            "hook": f"{app} hook", "name": f"{app} name", "search": app}


DATA = {
    "clips": {"a/en": clip("a", "en"), "a/zh-Hant": clip("a", "zh-Hant"), "b/en": clip("b", "en")},
    "schedule": [
        {"date": "2026-10-15", "slot": 1, "channel": "telegram", "clip": "a/zh-Hant"},
        {"date": "2026-10-15", "slot": 15, "channel": "instagram", "clip": "b/en"},
        {"date": "2026-10-16", "slot": 15, "channel": "telegram", "clip": "missing/en"},
    ],
}


class ClipPostsTest(unittest.TestCase):
    def test_only_the_scheduled_clip_goes_out(self):
        day = dt.date(2026, 10, 15)
        self.assertEqual(C.scheduled(DATA, day, 1, "telegram")["locale"], "zh-Hant")
        self.assertIsNone(C.scheduled(DATA, day, 15, "telegram"))
        self.assertEqual(C.scheduled(DATA, day, 15, "instagram")["app"], "b")

    def test_unknown_clip_or_empty_day_posts_nothing(self):
        self.assertIsNone(C.scheduled(DATA, dt.date(2026, 10, 16), 15, "telegram"))
        self.assertIsNone(C.scheduled(DATA, dt.date(2026, 10, 17), 1, "instagram"))

    def test_campaign_token_gets_channel_suffix_and_stays_short(self):
        url = C.with_campaign("https://apps.apple.com/tw/app/id1?pt=1&ct=h7_claudeusagemini_zh-Hant&mt=8", "tg")
        self.assertIn("ct=h7_claudeusagemini_zh-Hant_tg", url)
        long = C.with_campaign("https://apps.apple.com/us/app/id1?ct=" + "x" * 45, "ig")
        ct = dict(p.split("=") for p in long.split("?")[1].split("&"))["ct"]
        self.assertLessEqual(len(ct), 40)

    def test_instagram_caption_points_to_search_and_bio_with_few_tags(self):
        text = C.caption(clip("mochi", "ja"), "instagram")
        self.assertIn("App Storeで「mochi」を検索", text)
        self.assertIn("プロフィール", text)
        self.assertLessEqual(text.count("#"), 3)

    def test_captions_vary_between_apps(self):
        layouts = {tuple(C.caption(clip(app, "en"), "telegram").split("\n")[:1]) == (f"{app} hook",)
                   for app in ("a", "bb", "ccc", "dddd", "eeeee", "ffffff")}
        self.assertEqual(layouts, {True, False})

    def test_reels_wait_for_the_token(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(C.post_instagram(clip("a", "en")))

    def test_telegram_sends_video_with_store_button(self):
        sent = {}

        def fake_post(url, fields, timeout=60):
            sent.update(fields, endpoint=url)
            return {"ok": True, "result": {"message_id": 7}}

        with mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "c"}), \
                mock.patch.object(C, "_post", side_effect=fake_post):
            self.assertEqual(C.post_telegram(clip("a", "en")), 7)
        self.assertTrue(sent["endpoint"].endswith("/sendVideo"))
        button = json.loads(sent["reply_markup"])["inline_keyboard"][0][0]
        self.assertIn("ct=h7_a_en_tg", button["url"])


if __name__ == "__main__":
    unittest.main()
