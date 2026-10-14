#!/usr/bin/env python3
"""Tests for utility_cards.py (no network)."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import clip_progress as P  # noqa: E402
import utility_cards as U  # noqa: E402

DAY0 = U.EPOCH


class PickTest(unittest.TestCase):
    def test_types_rotate_daily_and_start_at_the_top_of_each_list(self):
        cards = [U.pick(DAY0 + dt.timedelta(days=i)) for i in range(6)]
        self.assertEqual([c["type"] for c in cards], ["word", "zhuyin", "photo"] * 2)
        self.assertEqual(cards[1]["item"]["symbol"], "ㄅ")
        self.assertEqual(cards[4]["item"]["symbol"], "ㄆ")
        self.assertEqual(cards[0]["item"]["word"], "invoice")

    def test_every_item_and_locale_comes_round_and_apps_match_types(self):
        data = U.load()
        seen = {"word": set(), "zhuyin": set(), "photo": set()}
        for i in range(3 * 37 * 4):
            c = U.pick(DAY0 + dt.timedelta(days=i), data)
            seen[c["type"]].add((c["item"]["id"], c["locale"]))
            self.assertIn(c["locale"], U.LOCALES[c["type"]])
            self.assertEqual(c["app"], {"zhuyin": "lumibopomofo", "photo": "snapportlite"}.get(c["type"], c["app"]))
            self.assertIn(c["app"], U.APPS)
        self.assertEqual(len({i for i, _ in seen["zhuyin"]}), 37)
        self.assertEqual({loc for _, loc in seen["photo"]}, {"en", "zh-Hant", "ja", "ko"})
        self.assertEqual({c["app"] for c in (U.pick(DAY0 + dt.timedelta(days=3 * k)) for k in range(2))},
                         {"aim990", "wordmatelite"})

    def test_curated_data_is_complete_for_every_locale(self):
        data = U.load()
        for w in data["words"]:
            self.assertEqual(set(w["meaning"]), {"en", "zh-Hant", "ja", "ko"})
        for z in data["zhuyin"]:
            self.assertEqual(len(z["word"]), len(z["zhuyin"]))
            self.assertIn(z["kind"], U.KIND_TIP)
        for p in data["photos"]:
            self.assertEqual(set(p["doc"]), {"en", "zh-Hant", "ja", "ko"})
            self.assertIn(p["bg"], U.BACKGROUND)
        shown = {"aim990": U.LOCALES["word"], "wordmatelite": U.LOCALES["word"],
                 "lumibopomofo": U.LOCALES["zhuyin"], "snapportlite": U.LOCALES["photo"]}
        for app, locales in shown.items():  # every locale an app appears in has its pitch and screenshot
            for loc in locales:
                self.assertIn(loc, U.APPS[app]["pitch"])
                self.assertTrue((U.ASSETS / f"{app}_{loc}.png").exists(), f"{app}_{loc}.png")


class CopyTest(unittest.TestCase):
    def test_caption_has_content_app_and_store_line(self):
        c = U.pick(DAY0 + dt.timedelta(days=2))  # first photo size, English
        text = U.caption(c, DAY0)
        self.assertIn("U.S. passport", text)
        self.assertIn("2 × 2 in", text)
        self.assertIn("check the official site", text)
        self.assertIn("Snapport Lite", text)
        word = U.caption(U.pick(DAY0), DAY0)
        self.assertIn("invoice", word)
        self.assertIn("發票", word)
        self.assertIn("Aim990", word)

    def test_store_links_carry_a_short_campaign_per_channel(self):
        c = U.pick(DAY0 + dt.timedelta(days=1))
        url = U.store_url(c, "tg")
        self.assertTrue(url.startswith("https://apps.apple.com/tw/app/id6773017109?"))
        self.assertIn("ct=ut_zhuyin_lumibopomofo_tg", url)
        self.assertLessEqual(len(U.campaign(c, "th")), 40)


class ThreadsCapTest(unittest.TestCase):
    def schedule(self, n):
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump({"schedule": [{"date": "2026-10-20", "slot": 1 + 14 * i, "channel": "threads", "clip": "a/en"}
                                for i in range(n)] + [{"date": "2026-10-20", "slot": 1, "channel": "instagram",
                                                       "clip": "a/en"}]}, f)
        f.close()
        self.addCleanup(os.unlink, f.name)
        return Path(f.name)

    def test_threads_only_when_the_day_stays_at_three_posts(self):
        day = dt.date(2026, 10, 20)
        self.assertEqual(U.threads_planned(day, self.schedule(2)), 3)
        self.assertFalse(U.threads_has_room(day, self.schedule(2)))
        self.assertTrue(U.threads_has_room(day, self.schedule(1)))
        self.assertTrue(U.threads_has_room(day, Path("/nonexistent.json")))

    def test_full_threads_day_posts_nothing_there(self):
        with mock.patch.object(U, "threads_has_room", return_value=False), \
                mock.patch.object(U.cd, "threads_image") as image:
            self.assertIsNone(U.post_threads("https://x/card.jpg", {"caption": "c"}, U.pick(DAY0), DAY0))
        image.assert_not_called()


class PostTest(unittest.TestCase):
    def test_telegram_buttons_and_message_link(self):
        c = U.pick(DAY0)
        result = {"ok": True, "result": {"message_id": 9, "chat": {"username": "lumiapps"}}}
        with mock.patch.object(U.cd, "send_photo", return_value=result) as send:
            link = U.post_telegram("card.jpg", {"caption": "c"}, c)
        self.assertEqual(link, "https://t.me/lumiapps/9")
        row = send.call_args[0][2]
        self.assertIn("ct=ut_word_aim990_tg", row[0]["url"])
        self.assertEqual(row[-1]["text"], "Google Play")  # Aim990 is on Android

    def test_posts_are_recorded_on_the_promotion_page(self):
        meta = {"type": "word", "item": "invoice", "locale": "zh-Hant", "app": "aim990",
                "key": "utility/word/aim990/invoice/zh-Hant", "caption": "c"}
        with tempfile.TemporaryDirectory() as tmp:
            card = Path(tmp) / "card.jpg"
            card.with_suffix(".json").write_text(json.dumps(meta), encoding="utf-8")
            with mock.patch.object(sys, "argv", ["u", "post", "--card", str(card), "--date", "2026-10-15"]), \
                    mock.patch.object(U, "post_telegram", return_value="https://t.me/x/1"), \
                    mock.patch.object(U, "post_instagram", return_value=None), \
                    mock.patch.object(U, "post_threads", side_effect=RuntimeError("down")), \
                    mock.patch.object(P, "record_post") as record:
                self.assertEqual(U.main(), 0)
        record.assert_called_once_with("telegram", "utility/word/aim990/invoice/zh-Hant", "https://t.me/x/1")

    def test_section_counts_utility_posts_apart_from_clips(self):
        posts = [{"channel": "telegram", "clip": "a/en", "link": "https://t.me/x/5", "posted_at": "2026-10-15T01:00:03Z"},
                 {"channel": "telegram", "clip": "utility/photo/snapportlite/us_passport/en", "link": "https://t.me/x/6",
                  "posted_at": "2026-10-15T05:10:40Z"},
                 {"channel": "instagram", "clip": "utility/photo/snapportlite/us_passport/en", "link": "https://ig/p/1",
                  "posted_at": "2026-10-15T05:11:10Z"}]
        md = P.build_section({"clips": {}, "schedule": []}, posts, {}, dt.datetime(2026, 10, 15, 6, tzinfo=dt.timezone.utc))
        self.assertIn("| 已發出 | 1 則 |", md)
        import own_posts
        hit = own_posts.Catalog({}, posts, {}).resolve("instagram", {"permalink": "https://ig/p/1"})
        self.assertEqual((hit["app"], hit["locale"], hit["kind"]), ("snapportlite", "en", "utility"))
        self.assertIn("| 每日實用卡 | 已發 2 則 · 最新 10/15 證件照尺寸 [TG](https://t.me/x/6) [IG](https://ig/p/1) |", md)


@unittest.skipUnless(Path(U.cd.FONT).exists(), "CJK font not installed")
class MakeTest(unittest.TestCase):
    def test_every_type_draws_a_card_with_meta(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i in range(3):
                out = Path(tmp) / f"c{i}.jpg"
                meta = U.make(out, DAY0 + dt.timedelta(days=i))
                self.assertTrue(out.exists())
                self.assertEqual(json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))["key"], meta["key"])
                self.assertEqual(U.card_from_meta(meta)["item"]["id"], meta["item"])


if __name__ == "__main__":
    unittest.main()
