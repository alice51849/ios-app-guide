#!/usr/bin/env python3
"""Tests for clip_posts.py (no network)."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import clip_posts as C  # noqa: E402


def clip(app, locale):
    return {"app": app, "locale": locale, "url": f"https://files.catbox.moe/{app}_{locale}.mp4",
            "store_url": f"https://apps.apple.com/us/app/id1?pt=118326163&ct=h7_{app}_{locale}&mt=8",
            "hook": f"{app} hook", "name": f"{app} name", "search": app}


class ClipPostsTest(unittest.TestCase):
    def setUp(self):
        self.clips = [clip("a", "en"), clip("a", "zh-Hant"), clip("b", "en"), clip("c", "ja")]
        self.priority = {"b": 0, "a": 1}

    def test_slot_prefers_its_audience_language(self):
        chosen = [C.pick(self.clips, self.priority, C.EPOCH + dt.timedelta(days=d), 1) for d in range(6)]
        self.assertTrue(all(c["locale"] in ("zh-Hant", "ja", "en") for c in chosen))
        a = [c for c in chosen if c["app"] == "a"]
        self.assertTrue(a and all(c["locale"] == "zh-Hant" for c in a))

    def test_rotation_covers_every_app(self):
        seen = {C.pick(self.clips, self.priority, C.EPOCH + dt.timedelta(days=d), 15)["app"] for d in range(10)}
        self.assertEqual(seen, {"a", "b"})  # c has no Americas locale

    def test_held_apps_are_never_posted(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "clips.json"
            path.write_text(json.dumps({"clips": self.clips, "hold": ["b"], "priority": ["b", "a"]}))
            clips, priority = C.load(path)
        self.assertNotIn("b", {c["app"] for c in clips})

    def test_campaign_token_gets_channel_suffix_and_stays_short(self):
        url = C.with_campaign("https://apps.apple.com/tw/app/id1?pt=1&ct=h7_claudeusagemini_zh-Hant&mt=8", "tg")
        self.assertIn("ct=h7_claudeusagemini_zh-Hant_tg", url)
        long = C.with_campaign("https://apps.apple.com/us/app/id1?ct=" + "x" * 45, "ig")
        ct = dict(p.split("=") for p in long.split("?")[1].split("&"))["ct"]
        self.assertLessEqual(len(ct), 40)

    def test_instagram_caption_points_to_search_and_bio(self):
        text = C.caption(clip("mochi", "ja"), "instagram")
        self.assertIn("App Storeで「mochi」を検索", text)
        self.assertIn("プロフィール", text)

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
