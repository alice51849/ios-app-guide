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
os.environ.setdefault("POST_QA_OFFLINE", "1")  # the pre-post QA gate makes no network calls in tests

import clip_posts as C  # noqa: E402
import clip_progress as P  # noqa: E402


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

    def test_a_posted_clip_is_never_posted_again(self):
        day = dt.date(2026, 10, 15)
        key = next(e["clip"] for e in DATA["schedule"] if e["channel"] == "telegram" and e["slot"] == 1)
        with mock.patch.object(C, "already_posted", return_value={key}):
            self.assertIsNone(C.scheduled(DATA, day, 1, "telegram"))

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

    def test_every_caption_starts_with_the_problem_line(self):
        for app in ("a", "bb", "ccc", "dddd"):
            for channel in ("telegram", "instagram", "threads"):
                self.assertEqual(C.caption(clip(app, "en"), channel).split("\n")[0], f"{app} hook")

    def test_search_caption_shape_per_platform(self):
        c = dict(clip("u", "en"), name="UsageNow: AI Usage Tracker", search="UsageNow",
                 keyline="Claude, Codex & Copilot Limits", keywords=["quota", "reset"],
                 tags=["#AIUsageTracker", "#iphoneapps", "#Quota", "#Reset", "#Countdown", "#Developer", "#UsageNow"],
                 hooks=[{"id": "a", "lead": "Hit your AI limit mid-task again?", "benefit": "See what's left and when it resets"},
                        {"id": "b", "lead": "See what's left and when it resets", "benefit": "Alerts before you run out"}])
        ig = C.caption(c, "instagram")
        self.assertTrue(ig.startswith("Hit your AI limit mid-task again?\nSee what's left"))
        self.assertIn("Claude, Codex & Copilot Limits", ig[:125])  # keyword phrase before "more"
        tags = ig.splitlines()[-1].split()
        self.assertEqual(len(tags), 5)
        self.assertNotIn("#iphoneapps", tags)  # generic store tags never go out
        self.assertEqual(C.caption(c, "threads").splitlines()[-1], "#AIUsageTracker")  # one topic tag
        self.assertEqual(len(C.caption(c, "telegram").splitlines()[-1].split()), 3)
        long = dict(c, hooks=[dict(c["hooks"][0], benefit="x" * 120)])
        self.assertIn("Claude, Codex & Copilot Limits", C.caption(long, "instagram")[:125])
        self.assertTrue(C.caption(c, "instagram", c["hooks"][1]).startswith("See what's left"))

    def test_hook_variants_rotate_and_winner_is_preferred(self):
        import search_caption as SC
        c = dict(clip("u", "en"), hooks=[{"id": i, "lead": f"lead {i}", "benefit": ""} for i in "abc"])
        days = [dt.date(2026, 10, 15) + dt.timedelta(days=i) for i in range(6)]
        picked = {SC.choose(c, ch, d, wins={})["id"] for d in days for ch in ("telegram", "instagram", "threads")}
        self.assertEqual(picked, {"a", "b", "c"})
        same_day = {SC.choose(c, ch, days[0], wins={})["id"] for ch in ("telegram", "instagram", "threads", "bluesky")}
        self.assertGreater(len(same_day), 1)  # platforms test different variants on the same day
        won = [SC.choose(dict(c, hook_best="c"), "instagram", d, wins={})["id"] for d in days]
        self.assertGreaterEqual(won.count("c"), 4)  # winner two days in three, rotation keeps testing
        exploit = next(d for d in days if d.toordinal() % 3)
        self.assertEqual(SC.choose(c, "x", exploit, wins={"locales": {"en": "b"}})["id"], "b")
        self.assertEqual(SC.choose(clip("old", "en"), "x", days[0])["lead"], "old hook")  # no variants: the hook

    def test_posted_variant_is_recorded(self):
        c = dict(clip("a", "en"), hooks=[{"id": "a", "lead": "A", "benefit": ""}, {"id": "b", "lead": "B", "benefit": ""}])
        data = {"clips": {"a/en": c}, "schedule": [{"date": "2026-10-15", "slot": 1, "channel": "telegram", "clip": "a/en"}]}
        with mock.patch.object(C, "load", return_value=data), mock.patch.object(C.CLIPS.__class__, "exists", return_value=True), \
                mock.patch.object(C.post_qa, "store_lookup", return_value={"trackName": "a name", "description": "", "price": 0}), \
                mock.patch.object(C.post_qa, "url_status", return_value=200), \
                mock.patch.object(C, "post_telegram", return_value={"id": 1, "link": None}) as post, \
                mock.patch.object(P, "record_post") as rec, mock.patch.object(sys, "argv", ["x", "telegram", "--slot", "1",
                                                                                           "--date", "2026-10-15"]):
            C.main()
        variant = post.call_args[0][1]
        self.assertEqual(rec.call_args.kwargs["variant"], variant["id"])

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
            self.assertEqual(C.post_telegram(clip("a", "en")), {"id": 7, "link": None})
        self.assertTrue(sent["endpoint"].endswith("/sendVideo"))
        button = json.loads(sent["reply_markup"])["inline_keyboard"][0][0]
        self.assertIn("ct=h7_a_en_tg", button["url"])

    def test_public_channel_post_gets_a_link(self):
        reply = {"ok": True, "result": {"message_id": 9, "chat": {"username": "lumiapps"}}}
        with mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "c"}), \
                mock.patch.object(C, "_post", return_value=reply):
            self.assertEqual(C.post_telegram(clip("a", "en"))["link"], "https://t.me/lumiapps/9")

    def test_android_apps_get_a_google_play_button_and_caption_line(self):
        sent = {}
        play = "https://play.google.com/store/apps/details?id=x&referrer=r"
        with mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "c"}), \
                mock.patch.object(C, "play_store_url", return_value=play), \
                mock.patch.object(C, "_post", side_effect=lambda u, f, timeout=60: sent.update(f) or
                                  {"ok": True, "result": {"message_id": 1}}):
            C.post_telegram(clip("a", "ja"))
            self.assertIn("AndroidはGoogle Playで", C.caption(clip("a", "ja"), "instagram"))
        row = json.loads(sent["reply_markup"])["inline_keyboard"][0]
        self.assertEqual([b["text"] for b in row], ["App Storeで入手", "Google Play"])
        with mock.patch.object(C, "play_store_url", return_value=None):
            self.assertNotIn("Google Play", C.caption(clip("a", "ja"), "instagram"))

    def test_threads_video_then_link_reply(self):
        calls = []

        def fake_post(url, fields, timeout=60):
            calls.append(fields)
            return {"id": f"id{len(calls)}"}

        with mock.patch.dict(os.environ, {"THREADS_TOKEN": "t", "THREADS_USER_ID": "u"}), \
                mock.patch.object(C, "_post", side_effect=fake_post), \
                mock.patch.object(C, "_get", side_effect=[{"id": "u"}, {"status": "FINISHED"}, {"permalink": "https://www.threads.net/@x/post/1"}]), \
                mock.patch.object(C, "play_store_url", return_value=None), \
                mock.patch.object(C.time, "sleep"):
            out = C.post_threads(clip("a", "en"))
        self.assertEqual(out["link"], "https://www.threads.net/@x/post/1")
        self.assertEqual(calls[0]["media_type"], "VIDEO")
        self.assertNotIn("https://", calls[0]["text"])
        self.assertEqual(calls[2]["reply_to_id"], "id2")
        self.assertIn("ct=h7_a_en_th", calls[2]["text"])


def real(locale="en", **kw):
    c = dict(clip("u", locale), name="UsageNow: AI Usage Tracker", search="UsageNow", keyline="",
             hooks=[{"id": "a", "lead": "Hit your AI limit mid-task again?", "benefit": "See what's left"}])
    c.update(kw)
    return c


class PostQaTest(unittest.TestCase):
    """The pre-post QA gate (post_qa.py) refuses broken or non-compliant posts."""

    def test_wrong_locale_text_is_refused(self):
        import post_qa as Q
        self.assertTrue(Q.locale_problems("Wazige foto?\nSearch “Unblurry” on the App Store", "nl"))
        self.assertEqual(Q.locale_problems("Wazige foto?\nZoek op ‘Unblurry’ in de App Store\nLink in bio", "nl"), [])
        self.assertTrue(Q.locale_problems("写真をくっきり", "ja") == [])
        self.assertTrue(Q.locale_problems("照片变清晰", "ja"))           # no kana: not Japanese
        self.assertTrue(Q.locale_problems("照片变清晰 这个", "zh-Hant"))  # Simplified characters
        self.assertTrue(Q.locale_problems("사진 선명하게 写真", "ko") == [])
        self.assertTrue(Q.locale_problems("Blurry? 사진", "en"))
        self.assertEqual(Q.locale_problems("Blurry?\n#模糊", "en", allowed=("Unblurry 照片",)), [])  # tags excluded

    def test_banned_and_unsupported_claims_are_refused(self):
        import post_qa as Q
        self.assertTrue(Q.claim_problems("The best to-do app"))
        self.assertTrue(Q.claim_problems("最好用的記帳"))
        self.assertTrue(Q.claim_problems("Better than CamScanner"))
        self.assertEqual(Q.claim_problems("Claude, Codex & Copilot limits"), [])
        self.assertEqual(Q.claim_problems("Track ChatGPT limits", facts="Tracks ChatGPT and Claude"), [])
        self.assertTrue(Q.claim_problems("Free, no ads", facts="A calm calculator"))
        self.assertEqual(Q.claim_problems("Free download", price=0), [])
        self.assertEqual(Q.claim_problems("零廣告，內容先看再處理", facts="零廣告，內容先看再處理"), [])
        self.assertEqual(Q.claim_problems("Photo cleaner frees storage; free up space"), [])
        self.assertEqual(Q.claim_problems("Best Planner", allowed=("Best Planner",)), [])  # the store name itself

    def test_counts_must_be_on_the_product_page(self):
        import post_qa as Q
        self.assertTrue(Q.count_problems(["Race the clock for 60 seconds"], "46 question types"))
        self.assertEqual(Q.count_problems(["100 themes built in"], "One hundred themes are built in"), [])
        self.assertEqual(Q.count_problems(["內建一百款主題", "35 種尺寸"], "35 種證件照尺寸"), [])

    def test_length_tags_and_leftovers(self):
        import post_qa as Q
        self.assertTrue(Q.text_problems("x" * 501, "en", "threads"))
        self.assertTrue(Q.text_problems("Hook\n#a #b", "en", "threads"))
        self.assertEqual(Q.text_problems("Hook\n#a #b", "en", "telegram"), [])
        self.assertTrue(Q.text_problems("Hook\nSearch {s}", "en", "telegram"))
        self.assertTrue(Q.text_problems("Hook with *accent*", "en", "telegram"))
        self.assertEqual(Q.text_problems("", "en", "telegram"), ["caption is empty"])

    def test_missing_fields_and_dead_links_are_refused(self):
        import post_qa as Q
        c = real()
        self.assertEqual(Q.clip_problems(c, "telegram", C.caption(c, "telegram"), online=False), [])
        self.assertIn("clip has no url", Q.clip_problems(dict(c, url=""), "telegram", C.caption(c, "telegram"), online=False))
        self.assertIn("clip has no hook line", Q.clip_problems(dict(c, hooks=[], hook=""), "telegram", "x\ny", online=False))
        with mock.patch.object(Q, "store_lookup", return_value={}), mock.patch.object(Q, "url_status", return_value=200):
            self.assertTrue(any("dead store link" in p for p in Q.link_problems(c["store_url"], c["url"])))
        with mock.patch.object(Q, "store_lookup", return_value={"trackName": "x"}), \
                mock.patch.object(Q, "url_status", return_value=404):
            self.assertTrue(any("404" in p for p in Q.link_problems(c["store_url"], c["url"])))
        with mock.patch.object(Q, "store_lookup", return_value=None), mock.patch.object(Q, "url_status", return_value=None):
            self.assertEqual(Q.link_problems(c["store_url"], c["url"]), [])  # network trouble never blocks

    def test_a_refused_variant_falls_back_to_one_that_passes(self):
        c = real(hooks=[{"id": "a", "lead": "Hit your AI limit mid-task again?", "benefit": ""},
                        {"id": "b", "lead": "The best AI tracker", "benefit": ""}])
        v, problems = C.qa_variant(c, "instagram", C.SC.variants(c)[1], online=False)
        self.assertEqual((v["id"], problems), ("a", []))
        bad = real(hooks=[{"id": "a", "lead": "The best tracker", "benefit": ""}])
        v, problems = C.qa_variant(bad, "instagram", C.SC.variants(bad)[0], online=False)
        self.assertIsNone(v)
        self.assertTrue(problems)

    def test_refused_clip_is_not_posted(self):
        bad = real(hooks=[{"id": "a", "lead": "The best tracker", "benefit": ""}])
        data = {"clips": {"u/en": bad}, "schedule": [{"date": "2026-10-15", "slot": 1, "channel": "telegram", "clip": "u/en"}]}
        with mock.patch.object(C, "load", return_value=data), mock.patch.object(C.CLIPS.__class__, "exists", return_value=True), \
                mock.patch.object(C, "post_telegram") as post, mock.patch.object(P, "record_post") as rec, \
                mock.patch.object(sys, "argv", ["x", "telegram", "--slot", "1", "--date", "2026-10-15"]), \
                mock.patch("sys.stdout"):
            self.assertEqual(C.main(), 1)
        post.assert_not_called()
        rec.assert_not_called()

    # The posting workflows run this file right before they post; there one broken clip must only stop
    # itself (clip_posts.main gates it), not the whole day, so the full-feed audit runs locally / in review.
    @unittest.skipIf(os.environ.get("GITHUB_ACTIONS"), "per-clip gate in clip_posts.main covers posting runs")
    def test_every_planned_clip_caption_passes_the_gate(self):
        import post_qa as Q
        data = C.load()
        for key, c in data["clips"].items():
            for channel in ("telegram", "instagram", "threads"):
                for v in C.SC.variants(c):
                    self.assertEqual(Q.clip_problems(c, channel, C.caption(c, channel, v), online=False), [],
                                     f"{key} {channel} {v['id']}")


class CaptionQualityTest(unittest.TestCase):
    def test_every_clip_locale_gets_native_template_lines(self):
        for loc in ("nl", "da", "nb", "cs", "el", "ar", "pl", "zh-Hans"):
            self.assertIsNot(C.text_for(loc), C.TEXT["en"], loc)
            self.assertIn(loc, C.PLAY_LINE)
        nl = C.caption(dict(clip("u", "nl"), hook="Wazige foto?"), "instagram")
        self.assertIn("in de App Store", nl)
        self.assertNotIn("on the App Store", nl)

    def test_keyline_the_name_already_says_is_not_repeated(self):
        c = dict(clip("mochi", "zh-Hant"), name="Mochi: 可愛待辦清單", search="Mochi 可愛待辦清單", keyline="可愛待辦清單",
                 hooks=[{"id": "a", "lead": "待辦清單 也可以這麼可愛", "benefit": "點一下就完成"}])
        lines = C.caption(c, "telegram").splitlines()
        self.assertNotIn("可愛待辦清單", lines)
        self.assertIn("Mochi: 可愛待辦清單", lines)

    def test_no_space_after_full_width_punctuation(self):
        c = dict(clip("u", "zh-Hant"), hooks=[{"id": "a", "lead": "照片拍糊了？ 秒變清晰", "benefit": "挑一張、 模糊照片"}])
        self.assertTrue(C.caption(c, "telegram").startswith("照片拍糊了？秒變清晰\n挑一張、模糊照片"))

    def test_reels_cover_is_the_settled_hook_frame(self):
        sent = []
        with mock.patch.dict(os.environ, {"IG_ACCESS_TOKEN": "t"}), \
                mock.patch.object(C, "_get", side_effect=[{}, {"user_id": "1"}, {"status_code": "FINISHED"}, {"permalink": "p"}]), \
                mock.patch.object(C, "_post", side_effect=lambda u, f, timeout=60: sent.append(f) or {"id": "m"}):
            C.post_instagram(real())
        self.assertEqual(sent[0]["thumb_offset"], str(C.COVER_MS))
        self.assertLess(C.COVER_MS, 1000)  # inside beat 1 (>= 1.5s), before the first cut


class ClipProgressTest(unittest.TestCase):
    NOW = dt.datetime(2026, 10, 15, 2, 0, tzinfo=dt.timezone.utc)

    def test_section_lists_links_schedule_and_channel_progress(self):
        posts = [{"channel": "telegram", "clip": "a/zh-Hant", "link": "https://t.me/x/5",
                  "posted_at": "2026-10-15T01:00:03Z"}]
        md = P.build_section(DATA, posts, {"a": "App A"}, self.NOW, 53, ["note"])
        self.assertTrue(md.startswith(P.HEADING))
        self.assertIn("[T](https://t.me/x/5)", md)                      # posted link
        self.assertIn("10/15 23:20 b", md)                              # next IG post, 15:20 UTC
        self.assertIn("[en](https://files.catbox.moe/a_en.mp4)", md)
        self.assertIn("2／53 款 · 3 支", md)
        self.assertIn("| Telegram | 自動 2 支／天 | 1 |", md)
        self.assertIn("| 備註 | note |", md)
        with_play = P.build_section(DATA, [], {}, self.NOW, None, (), {"a": "https://play.google.com/x"})
        self.assertIn("| a 🤖 |", with_play)
        self.assertIn("Android 已上架 | 1 款", with_play)

    def test_section_replaced_in_place_and_other_sections_kept(self):
        summary = "# T\n\n## A\nx\n\n" + P.HEADING + "\nold\n\n## B\ny\n"
        out = P.replace_section(summary, P.HEADING + "\nnew")
        self.assertIn("## A\nx", out)
        self.assertIn("## B\ny", out)
        self.assertIn("new", out)
        self.assertNotIn("old", out)
        self.assertEqual(P.replace_section("# T", P.HEADING), "# T\n\n" + P.HEADING + "\n")

    def test_section_body_ignores_only_the_clock_line(self):
        page = lambda clock, rows: f"# 外宣成效\n\n{P.HEADING}\n\n{clock}\n\n{rows}\n\n## 成效排行\n\n更新 10/15 · x\n"
        a = P.section_body(page("更新 10/15 13:47（台灣）", "| a | 1 |"))
        self.assertEqual(a, P.section_body(page("更新 10/15 14:20（台灣）", "| a | 1 |")))
        self.assertNotEqual(a, P.section_body(page("更新 10/15 14:20（台灣）", "| a | 2 |")))
        self.assertNotIn("13:47", a)
        self.assertIn("更新 10/15 · x", a)                                 # later sections untouched
        self.assertEqual(a, P.section_body(page("更新：10/15 13:47", "| a | 1 |")))  # older form
        self.assertEqual(P.section_body("# 外宣成效\n"), "")              # no section yet

    def test_section_body_matches_what_build_section_writes(self):
        md = P.build_section(DATA, [], {}, self.NOW, None)
        later = P.build_section(DATA, [], {}, self.NOW + dt.timedelta(minutes=33), None)
        self.assertNotEqual(md, later)
        self.assertEqual(P.section_body("# T\n\n" + md), P.section_body("# T\n\n" + later))


if __name__ == "__main__":
    unittest.main()
