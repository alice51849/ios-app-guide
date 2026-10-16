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
os.environ.setdefault("POST_QA_OFFLINE", "1")  # the pre-post QA gate makes no network calls in tests

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
        self.assertIn("ct=ut_lumibopomofo_tg", url)
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
        # The 21:00 evening slot (threads_series.py or the slot-15 clip) always takes one post.
        self.assertFalse(U.threads_has_room(day, self.schedule(1)))
        self.assertEqual(U.threads_planned(day, self.schedule(0)), 2)
        self.assertTrue(U.threads_has_room(day, self.schedule(0)))
        self.assertTrue(U.threads_has_room(day, Path("/nonexistent.json")))

    def test_full_threads_day_posts_nothing_there(self):
        with mock.patch.object(U, "threads_has_room", return_value=False), \
                mock.patch.object(U.cd, "threads_image") as image:
            self.assertIsNone(U.post_threads("https://x/card.jpg", {"caption": "c"}, U.pick(DAY0), DAY0))
        image.assert_not_called()

    def test_card_image_checks_the_live_account_cap_before_posting(self):
        import threads_series as S
        env = {"THREADS_TOKEN": "t", "THREADS_USER_ID": "u"}
        with mock.patch.dict(os.environ, env), \
                mock.patch.object(S, "posts_today", return_value=3), \
                mock.patch.object(U.cd, "_post") as post:
            self.assertIsNone(U.cd.threads_image("https://x/card.jpg", "c", ["App Store: x"], label="utility"))
        post.assert_not_called()
        # A count that fails holds the post too.
        with mock.patch.dict(os.environ, env), \
                mock.patch.object(S, "posts_today", side_effect=OSError("down")), \
                mock.patch.object(U.cd, "_post") as post:
            self.assertIsNone(U.cd.threads_image("https://x/card.jpg", "c", ["App Store: x"]))
        post.assert_not_called()
        # Under the cap the image goes out and the links go in the first reply.
        with mock.patch.dict(os.environ, env), \
                mock.patch.object(S, "posts_today", return_value=2), \
                mock.patch.object(U.cd, "_get", return_value={"id": "u"}), \
                mock.patch.object(U.cd.time, "sleep"), \
                mock.patch.object(U.cd, "_post", side_effect=[{"id": "c1"}, {"id": "m1"}, {"id": "r1"}, {"id": "r2"}]) as post:
            self.assertEqual(U.cd.threads_image("https://x/card.jpg", "c", ["App Store: x"]), "m1")
        self.assertEqual(post.call_count, 4)


class PostTest(unittest.TestCase):
    def test_telegram_buttons_and_message_link(self):
        c = U.pick(DAY0)
        result = {"ok": True, "result": {"message_id": 9, "chat": {"username": "lumiapps"}}}
        with mock.patch.object(U.cd, "send_photo", return_value=result) as send:
            link = U.post_telegram("card.jpg", {"caption": "c"}, c)
        self.assertEqual(link, "https://t.me/lumiapps/9")
        row = send.call_args[0][2]
        self.assertIn("ct=ut_aim990_tg", row[0]["url"])
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
                    mock.patch.object(U, "qa_problems", return_value=[]), \
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
class SearchTest(unittest.TestCase):
    def test_instagram_card_gets_alt_text_and_keyword_tags(self):
        import search_caption as SC
        sent = []
        card = U.pick(DAY0)
        seo = {"seo": {card["app"]: {card["locale"]: {"tags": ["#kw1", "#kw2"], "keyline": "search phrase"}}}}
        with mock.patch.dict(os.environ, {"IG_ACCESS_TOKEN": "t"}), mock.patch.object(SC, "_feed", return_value=seo), \
                mock.patch.object(U.cd, "_get", return_value={"user_id": "u"}), mock.patch.object(U.cd.time, "sleep"), \
                mock.patch.object(U.cd, "_post", side_effect=lambda url, f, timeout=60: sent.append(f) or {"id": "m"}), \
                mock.patch.object(U, "_permalink", return_value="https://instagram.com/p/x"):
            U.post_instagram("https://x/card.jpg", {"caption": "Head\nBody"}, card)
        self.assertIn("search phrase", sent[0]["alt_text"])
        self.assertTrue(sent[0]["caption"].endswith("#kw1 #kw2"))


class MakeTest(unittest.TestCase):
    def test_every_type_draws_a_card_with_meta(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i in range(3):
                out = Path(tmp) / f"c{i}.jpg"
                meta = U.make(out, DAY0 + dt.timedelta(days=i))
                self.assertTrue(out.exists())
                self.assertEqual(json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))["key"], meta["key"])
                self.assertEqual(U.card_from_meta(meta)["item"]["id"], meta["item"])


class LegibilityTest(unittest.TestCase):
    """Card text keeps WCAG AA contrast and a phone-readable size (utility and countdown cards)."""

    def palettes(self):
        cd = U.cd
        return [a["colors"] for a in U.APPS.values()] + [e["colors"] for e in cd.EVENTS]

    def test_white_text_reaches_aa_on_every_gradient_row_and_the_footer(self):
        cd = U.cd
        for top, bottom, accent in ((U._rgb(c) for c in p) for p in self.palettes()):
            for k in (0, 0.25, 0.5, 0.75, 1):
                row = cd.legible(tuple(top[i] + (bottom[i] - top[i]) * k for i in range(3)))
                self.assertGreaterEqual(cd.contrast(cd.WHITE, row), cd.AA, (top, bottom, k))
                if k <= 0.35:  # accent text (headline, count, meaning) only sits in the top third
                    self.assertGreaterEqual(cd.contrast(accent, row), 3.0, (accent, row))  # large text
            self.assertGreaterEqual(cd.contrast(cd.WHITE, cd.legible(bottom, cd.WHITE, 7.0)), 7.0)
            pill_ink = top if cd.contrast(top, cd.WHITE) >= cd.AA else cd.legible(top)
            self.assertGreaterEqual(cd.contrast(pill_ink, cd.WHITE), cd.AA)  # store line on the white pill

    def test_the_old_pink_gradient_failed_and_is_now_darkened(self):
        cd = U.cd
        pink = U._rgb("#e58fb6")  # Lumi注音星球 bottom colour: white on it was ~2.4:1
        self.assertLess(cd.contrast(cd.WHITE, pink), cd.AA)
        self.assertGreaterEqual(cd.contrast(cd.WHITE, cd.legible(pink)), cd.AA)

    def test_long_lines_wrap_at_punctuation_instead_of_shrinking(self):
        from PIL import Image, ImageDraw, ImageFont
        cd = U.cd
        draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
        font = lambda s: ImageFont.truetype(cd.FONT, s, index=cd.FONT_INDEX["ja"])  # noqa: E731
        lines, size = cd.wrap(draw, U.TEXT["ja"]["check"], font, 36, 960)
        self.assertEqual(len(lines), 2)
        self.assertGreaterEqual(size, cd.MIN_TEXT)
        self.assertTrue(lines[0].endswith("。"))
        self.assertGreaterEqual(cd.MIN_TEXT, 34)

    def test_every_card_of_a_full_rotation_passes_the_qa_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            for i in range(12):
                day = DAY0 + dt.timedelta(days=i)
                out = Path(tmp) / f"c{i}.jpg"
                meta = U.make(out, day)
                card = U.card_from_meta(meta)
                for ch in ("telegram", "instagram", "threads"):
                    self.assertEqual(U.qa_problems(meta, card, ch, image=out, online=False), [], f"{meta['key']} {ch}")
            for d in ("2026-10-15", "2026-11-19", "2026-12-20", "2027-01-20", "2027-02-01"):
                out = Path(tmp) / f"cd{d}.jpg"
                meta = U.cd.make(out, dt.date.fromisoformat(d))
                e = next(x for x in U.cd.EVENTS if x["id"] == meta["event"])
                for ch in ("telegram", "instagram", "threads"):
                    self.assertEqual(U.cd.qa_problems(meta, e, ch, image=out, online=False), [], f"{d} {ch}")

    def test_a_missing_card_image_is_refused(self):
        meta = {"type": "word", "item": "invoice", "locale": "en", "app": "aim990", "key": "k",
                "caption": "Business English word of the day: invoice"}
        card = U.card_from_meta(meta)
        self.assertTrue(any("image" in p for p in U.qa_problems(meta, card, "telegram", image="/no/card.jpg", online=False)))


if __name__ == "__main__":
    unittest.main()
