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
import download_links as D  # noqa: E402
import post_qa as Q  # noqa: E402
import clip_progress as P  # noqa: E402
import review_links as R  # noqa: E402
import threads_cap  # noqa: E402


def setUpModule():
    # threads_cap.py reads the account's 24-hour post count right before each top-level Threads post. These tests
    # are about other things, so the account has room here; test_threads_cap.py covers the cap itself. Entered
    # directly rather than with start(), so a test's mock.patch.stopall cannot undo it for the tests after it.
    room = mock.patch.object(threads_cap, "quota_usage", return_value=0)
    room.__enter__()
    unittest.addModuleCleanup(room.__exit__, None, None, None)


def clip(app, locale):
    return {"app": app, "locale": locale, "url": f"https://files.catbox.moe/{app}_{locale}.mp4",
            "store_url": f"https://apps.apple.com/us/app/id1?pt=118326163&ct=h7_{app}_{locale}&mt=8",
            "hook": f"{app} hook", "name": f"{app} name", "search": app, "compliance": COMPLIANT}


# The record 00_GrowthEngine schedule_posts.py puts on a real-recording clip (post_qa.video_compliance_problems).
COMPLIANT = {"store_claims_ok": True, "screen_text_ok": True, "board": "0123456789abcdef", "real_recording": False}


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

    def test_a_taken_down_cut_does_not_block_the_new_real_recording_of_the_same_key(self):
        # video_takedown.py marks a non-compliant post "taken_down"; the entry stays, the key can go out again
        # (lumibopomofo / battai / snapport got real-recording cuts under their old keys on 2026-10-17).
        day = dt.date(2026, 10, 15)
        gone = [{"channel": "telegram", "clip": "a/zh-Hant", "id": "355", "posted_at": "2026-10-14T05:47:26Z",
                 "taken_down": {"status": "video_replaced"}}]
        self.assertEqual(set(), C.already_posted("telegram", gone))
        with mock.patch.object(C, "posted_log", return_value=gone):
            self.assertEqual("zh-Hant", C.scheduled(DATA, day, 1, "telegram")["locale"])
        live = gone + [{"channel": "telegram", "clip": "a/zh-Hant", "id": "400", "posted_at": "2026-10-15T01:00:00Z"}]
        self.assertEqual({"a/zh-Hant"}, C.already_posted("telegram", live))   # the new cut went out: once only
        with mock.patch.object(C, "posted_log", return_value=live):
            self.assertIsNone(C.scheduled(DATA, day, 1, "telegram"))
        self.assertEqual({"a/zh-Hant"}, C.already_posted("instagram", [dict(live[1], channel="instagram")]))

    def test_unknown_clip_or_empty_day_posts_nothing(self):
        self.assertIsNone(C.scheduled(DATA, dt.date(2026, 10, 16), 15, "telegram"))
        self.assertIsNone(C.scheduled(DATA, dt.date(2026, 10, 17), 1, "instagram"))

    def test_campaign_token_gets_channel_suffix_and_stays_short(self):
        url = C.with_campaign("https://apps.apple.com/tw/app/id1?pt=1&ct=h7_claudeusagemini_zh-Hant&mt=8", "tg")
        self.assertIn("ct=" + D.app_campaign("telegram", "1") + "&", url)  # one campaign per app and channel: locale and clip stay in the post log
        long = C.with_campaign("https://apps.apple.com/us/app/id1?ct=" + "x" * 45, "ig")
        ct = dict(p.split("=") for p in long.split("?")[1].split("&"))["ct"]
        self.assertLessEqual(len(ct), 40)

    def test_clip_campaign_drops_only_the_locale(self):
        cases = {"h7_mochi_en": "h7_mochi", "h7_mochi_zh-Hant": "h7_mochi", "h7_mochi_b_pt-BR": "h7_mochi_b",
                 "h7_mochi_th": "h7_mochi", "h7_mochi": "h7_mochi", "h7_mochi_b": "h7_mochi_b", "": "h7"}
        for token, merged in cases.items():
            self.assertEqual(C.clip_campaign(token), merged, token)
        # the variant clip goes out under the same YouTube campaign as the main one
        self.assertIn("ct=" + D.app_campaign("youtube", "1"), C.with_campaign("https://apps.apple.com/us/app/id1?ct=h7_mochi_b", "yt"))

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
                mock.patch.object(C, "posted_log", return_value=[]), \
                mock.patch.object(P, "record_post") as rec, mock.patch.object(sys, "argv", ["x", "telegram", "--slot", "1",
                                                                                           "--date", "2026-10-15"]):
            C.main()
        variant = post.call_args[0][1]
        self.assertEqual(rec.call_args.kwargs["variant"], variant["id"])

    def test_the_days_ramp_allowance_stops_a_slot_and_a_slow_down_answer_throttles(self):
        c = clip("a", "en")
        data = {"clips": {"a/en": c}, "schedule": [{"date": "2026-10-20", "slot": 15, "channel": "instagram", "clip": "a/en"}]}
        ramp = {"schema": C.volume_ramp.SCHEMA, "stage_days": 3, "hold_days": 7,
                "channels": {"instagram": {"start": "2026-10-17", "stages": [2, 3], "slots": [1, 15, 12]}}}
        log = [{"channel": "instagram", "clip": f"x{i}/en", "posted_at": "2026-10-20T01:21:00Z"} for i in range(3)]
        argv = ["x", "instagram", "--slot", "15", "--date", "2026-10-20"]
        with mock.patch.object(C, "load", return_value=data), mock.patch.object(C.CLIPS.__class__, "exists", return_value=True), \
                mock.patch.object(C.volume_ramp, "load", return_value=ramp), mock.patch.object(C, "posted_log", return_value=log), \
                mock.patch.object(C, "post_instagram") as post, mock.patch.object(sys, "argv", argv), mock.patch("sys.stdout"):
            self.assertEqual(C.main(), 0)
        post.assert_not_called()  # 3 of today's 3 already out: the slot is skipped, nothing fails
        with mock.patch.object(C, "load", return_value=data), mock.patch.object(C.CLIPS.__class__, "exists", return_value=True), \
                mock.patch.object(C.volume_ramp, "load", return_value=ramp), mock.patch.object(C, "posted_log", return_value=log[:1]), \
                mock.patch.object(C.post_qa, "store_lookup", return_value={"trackName": "a name", "description": "", "price": 0}), \
                mock.patch.object(C.post_qa, "url_status", return_value=200), \
                mock.patch.object(C, "post_instagram", side_effect=RuntimeError('HTTP 400: {"error":{"code":4,"message":"(#4) Application request limit reached"}}')), \
                mock.patch.object(C.volume_ramp, "handle_error") as handle, mock.patch.object(sys, "argv", argv), mock.patch("sys.stdout"):
            with self.assertRaises(RuntimeError):
                C.main()
        self.assertEqual(handle.call_args[0][0], "instagram")
        self.assertTrue(C.volume_ramp.is_throttle_error(handle.call_args[0][1]))

    def test_threads_morning_clip_gives_way_to_the_evening_conversion_post(self):
        queued = {"date": "2026-10-18", "app": "mochi", "app_id": "6785004775", "ct": "bm_mochi_br_th",
                  "locale": "pt-BR", "text": "Semana de prova? Link nos comentários."}
        day = dt.date(2026, 10, 18)
        self.assertEqual(C.yields_to_evening("threads", 1, day, [queued])["ct"], "bm_mochi_br_th")
        self.assertIsNone(C.yields_to_evening("threads", 1, dt.date(2026, 10, 24), [queued]))  # no post that day
        self.assertIsNone(C.yields_to_evening("threads", 15, day, [queued]))  # the evening fallback clip itself
        for channel in ("telegram", "instagram"):
            self.assertIsNone(C.yields_to_evening(channel, 1, day, [queued]))
        broken = dict(queued, ct="soc_th")  # a post the evening slot would refuse keeps the clip
        self.assertIsNone(C.yields_to_evening("threads", 1, day, [broken]))
        data = {"clips": {"a/en": clip("a", "en")}, "schedule": [
            {"date": "2026-10-18", "slot": 1, "channel": ch, "clip": "a/en"} for ch in ("threads", "telegram")]}
        common = [mock.patch.object(C, "load", return_value=data), mock.patch.object(C.CLIPS.__class__, "exists", return_value=True),
                  mock.patch.object(C.threads_series, "load_evening_queue", return_value=[queued]),
                  mock.patch.object(C.post_qa, "store_lookup", return_value={"trackName": "a name", "description": "", "price": 0}),
                  mock.patch.object(C.post_qa, "url_status", return_value=200),
                  mock.patch.object(C, "posted_log", return_value=[]), mock.patch.object(P, "record_post"), mock.patch("sys.stdout")]
        for patch in common:
            patch.start()
        self.addCleanup(mock.patch.stopall)
        with mock.patch.object(C, "post_threads") as th, \
                mock.patch.object(sys, "argv", ["x", "threads", "--slot", "1", "--date", "2026-10-18"]):
            self.assertEqual(C.main(), 0)
        th.assert_not_called()
        with mock.patch.object(C, "post_telegram", return_value={"id": 1, "link": None}) as tg, \
                mock.patch.object(sys, "argv", ["x", "telegram", "--slot", "1", "--date", "2026-10-18"]):
            self.assertEqual(C.main(), 0)
        tg.assert_called_once()

    def test_the_real_evening_queue_dates_take_the_threads_morning_slot(self):
        queue = C.threads_series.load_evening_queue(C.threads_series.EVENING_QUEUE)
        for p in queue:
            self.assertIsNotNone(C.yields_to_evening("threads", 1, dt.date.fromisoformat(p["date"]), queue), p["date"])

    def test_http_errors_carry_the_api_reason_not_the_token(self):
        import io
        import urllib.error
        err = urllib.error.HTTPError("https://graph.instagram.com/x?access_token=SECRET", 429, "Too Many Requests", {},
                                     io.BytesIO(b'{"error":{"message":"(#4) Application request limit reached","code":4}}'))
        with mock.patch.object(C.urllib.request, "urlopen", side_effect=err):
            with self.assertRaises(RuntimeError) as cm:
                C._get("https://graph.instagram.com/x?access_token=SECRET")
        self.assertIn("HTTP 429", str(cm.exception))
        self.assertIn("request limit", str(cm.exception))
        self.assertNotIn("SECRET", str(cm.exception))

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
        self.assertIn("ct=" + D.app_campaign("telegram", "1") + "&", button["url"])

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
        self.assertIn("ct=" + D.app_campaign("threads", "1") + "&", calls[2]["text"])

    def test_play_link_uses_the_same_per_platform_ct_as_the_app_store_link(self):
        # Mochi is Android-live in the snapshot: each platform's Play referrer is that platform's App Store ct
        # (the channel-level campaign, download_links.coarse_campaign).
        mochi = dict(clip("mochi", "ja"), store_url="https://apps.apple.com/jp/app/id6785004775?pt=118326163"
                     "&ct=h7_mochi_ja&mt=8")
        sent = {"th": "threads", "tg": "telegram", "yt": "youtube", "bs": "bluesky", "fb": "social", "tb": "social"}
        for channel, campaign in sent.items():
            with self.subTest(channel=channel):
                self.assertIn(f"ct={campaign}&", C.with_campaign(mochi["store_url"], channel))
                self.assertEqual(
                    "https://play.google.com/store/apps/details?id=com.alice51849.MochiTodo"
                    f"&referrer=utm_source%3D{campaign}%26utm_campaign%3Dmochi",
                    C.play_url(mochi, channel))
        self.assertIsNone(C.play_url(clip("a", "en"), "th"))  # id1 is not on Android

    def test_threads_reply_lists_app_store_then_tracked_play(self):
        calls = []
        mochi = dict(clip("mochi", "en"), store_url="https://apps.apple.com/us/app/id6785004775?pt=118326163"
                     "&ct=h7_mochi_en&mt=8")

        def fake_post(url, fields, timeout=60):
            calls.append(fields)
            return {"id": f"id{len(calls)}"}

        with mock.patch.dict(os.environ, {"THREADS_TOKEN": "t", "THREADS_USER_ID": "u"}), \
                mock.patch.object(C, "_post", side_effect=fake_post), \
                mock.patch.object(C, "_get", side_effect=[{"id": "u"}, {"status": "FINISHED"}, {"permalink": "p"}]), \
                mock.patch.object(C.time, "sleep"):
            C.post_threads(mochi)
        self.assertNotIn("https://", calls[0]["text"])  # links never in the post body
        reply = calls[2]["text"].splitlines()
        self.assertIn("ct=threads&", reply[0])
        self.assertEqual("Google Play: https://play.google.com/store/apps/details?id=com.alice51849.MochiTodo"
                         "&referrer=utm_source%3Dthreads%26utm_campaign%3Dmochi", reply[1])


class DownloadLinkTest(unittest.TestCase):
    """Every hook clip post carries the app's direct download link (owner rule 2026-10-17)."""
    MOCHI = dict(clip("mochi", "en"), store_url="https://apps.apple.com/us/app/id6785004775?pt=118326163&ct=h7_mochi_en&mt=8",
                 name="Mochi: Cute To-Do", search="Mochi",
                 hooks=[{"id": "a", "lead": "Task list too boring to open?", "benefit": "A cute checklist"}])

    def test_instagram_caption_holds_the_full_urls_and_the_bio_hint(self):
        # Owner 2026-10-17 「改成原版的好了 請大家去個人檔案下載」「但是你的 tag 可以直接放一個我 app 的名稱」: no URL on
        # Instagram (it cannot be tapped), the profile-link line closes the text, the brand hashtag leads the tags.
        text = C.caption(self.MOCHI, "instagram")
        self.assertNotIn("https://", text)
        self.assertNotIn("apps.apple.com", text)
        self.assertNotIn("play.google.com", text)
        self.assertIn("Also on Google Play", text)   # Mochi is on Android: said in words, the hub has the button
        lines = text.split("\n")
        self.assertEqual(lines[0], "Task list too boring to open?")  # the hook still opens the caption
        self.assertEqual(lines[-3], "📲 Download via the link in bio")
        self.assertEqual(lines[-1].split()[0], "#Mochi")
        self.assertEqual(1, lines[-1].split().count("#Mochi"))   # one brand hashtag
        self.assertLessEqual(len(lines[-1].split()), C.post_qa.MAX_TAGS["instagram"])
        self.assertLessEqual(len(text), 2200)
        self.assertEqual(C.post_qa.clip_problems(self.MOCHI, "instagram", text, online=False), [])

    def test_telegram_caption_holds_the_urls_too_and_threads_text_does_not(self):
        text = C.caption(self.MOCHI, "telegram")
        self.assertIn("ct=telegram&", text)
        self.assertIn("play.google.com", text)
        self.assertNotIn("https://", C.caption(self.MOCHI, "threads"))  # Threads links go in the first reply
        self.assertEqual(C.post_qa.clip_problems(self.MOCHI, "threads", C.caption(self.MOCHI, "threads"), online=False), [])

    def test_ios_only_app_gets_the_app_store_link_only(self):
        text = C.caption(clip("a", "en"), "telegram")
        self.assertIn("https://apps.apple.com/us/app/id1?", text)
        self.assertNotIn("play.google.com", text)
        ig = C.caption(clip("a", "en"), "instagram")   # Instagram: no URL at all, and no Google Play line either
        self.assertNotIn("https://", ig)
        self.assertNotIn("Google Play", ig)
        self.assertIn("📲 Download via the link in bio", ig)

    def test_qa_refuses_a_caption_without_the_link(self):
        bare = "Task list too boring to open?\nMochi: Cute To-Do\nSearch “Mochi” on the App Store\nLink in bio"
        problems = C.post_qa.clip_problems(self.MOCHI, "telegram", bare, online=False)
        self.assertTrue(any("download link" in p for p in problems), problems)
        # Instagram: the old "Link in bio" text has neither the profile-link line nor the brand hashtag.
        problems = C.post_qa.clip_problems(self.MOCHI, "instagram", bare, online=False)
        self.assertTrue(any("profile-link line" in p for p in problems), problems)
        self.assertTrue(any("brand hashtag #Mochi" in p for p in problems), problems)
        good = C.caption(self.MOCHI, "instagram")
        self.assertEqual(C.post_qa.clip_problems(self.MOCHI, "instagram", good, online=False), [])
        # ... and a URL is refused on Instagram, the store links of this very app included.
        store, play = C.download_urls(self.MOCHI, "instagram")
        for url in (store, play, "apps.apple.com/app/id6785004775", "open.cait518.cc/ig/"):
            linked = good.replace("📲 Download via the link in bio", f"📲 Download via the link in bio\n{url}")
            problems = C.post_qa.clip_problems(self.MOCHI, "instagram", linked, online=False)
            self.assertTrue(any("must not carry a URL" in p for p in problems), (url, problems))
        # Telegram keeps the rule it had: both links for an Android app.
        no_play = C.caption(self.MOCHI, "telegram").split("Also on Google Play")[0]
        self.assertTrue(any("Google Play" in p for p in C.post_qa.clip_problems(self.MOCHI, "telegram", no_play, online=False)))
        only_ios = C.caption(clip("a", "en"), "telegram")
        self.assertEqual(C.post_qa.clip_problems(clip("a", "en"), "telegram", only_ios, online=False), [])

    def test_a_clip_without_a_store_link_is_never_posted(self):
        broken = dict(self.MOCHI, store_url="")
        variant, problems = C.qa_variant(broken, "instagram", C.SC.variants(broken)[0], online=False)
        self.assertIsNone(variant)
        self.assertTrue(problems)

    def test_an_over_long_caption_is_refused_by_qa_not_sent_with_a_cut_link(self):
        long = dict(self.MOCHI, hooks=[{"id": "a", "lead": "Task list too boring to open?", "benefit": "cute " * 400}])
        text = C.caption(long, "telegram")
        self.assertIn("https://apps.apple.com/", text)
        self.assertTrue(any("characters" in p for p in C.post_qa.clip_problems(long, "telegram", text, online=False)))

    def test_the_send_calls_never_send_a_caption_without_the_link(self):
        sent = {}

        def fake_post(url, fields, timeout=60):
            sent.setdefault(url.rsplit("/", 1)[-1], fields)
            return {"id": "m1", "ok": True, "result": {"message_id": 1}}

        with mock.patch.dict(os.environ, {"IG_ACCESS_TOKEN": "t", "TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "c"}), \
                mock.patch.object(C, "_post", side_effect=fake_post), \
                mock.patch.object(C, "caption", return_value="Hook only, nothing else"), \
                mock.patch.object(C, "_get", side_effect=[{}, {"user_id": "u"}, {"status_code": "FINISHED"}, {"permalink": "p"}]), \
                mock.patch.object(C.time, "sleep"):
            C.post_instagram(self.MOCHI)
            C.post_telegram(self.MOCHI)
        field = sent["sendVideo"]["caption"]
        self.assertTrue(C.DL.has_download_link(field, self.MOCHI["store_url"], C.play_url(self.MOCHI, "tg")))
        # Instagram: the send call itself adds the profile-link line and the brand hashtag, never a URL.
        field = sent["media"]["caption"]
        self.assertEqual([], C.DL.instagram_problems(field, self.MOCHI["name"], locale="en"), field)
        self.assertIn("📲 Download via the link in bio", field)
        self.assertNotIn("https://", field)
        sent.clear()
        with mock.patch.dict(os.environ, {"IG_ACCESS_TOKEN": "t"}), \
                mock.patch.object(C, "_post", side_effect=fake_post), \
                mock.patch.object(C, "caption", return_value="Hook\nhttps://apps.apple.com/app/id6785004775"), \
                mock.patch.object(C, "_get", side_effect=[{}, {"user_id": "u"}]), mock.patch.object(C.time, "sleep"):
            with self.assertRaises(C.DL.MissingDownloadLink):
                C.post_instagram(self.MOCHI)
        self.assertEqual(sent, {}, "a caption with a URL never reaches Instagram")

    def test_a_retry_does_not_double_a_reply_that_was_published_after_all(self):
        calls = []

        def post(url, fields, timeout=60):
            calls.append(fields)
            if fields.get("reply_to_id") and len([c for c in calls if c.get("reply_to_id")]) == 1:
                raise RuntimeError("timeout")  # the platform published it, but the answer never came back
            return {"id": f"id{len(calls)}"}

        store, play = C.download_urls(self.MOCHI, "threads")
        mine = {"data": [{"text": f"{store}\n{play}", "is_reply_owned_by_me": True}]}
        gets = [{"id": "u"}, {"status": "FINISHED"}, mine, {"permalink": "p"}]
        with mock.patch.dict(os.environ, {"THREADS_TOKEN": "t", "THREADS_USER_ID": "u"}), \
                mock.patch.object(C, "_post", side_effect=post), mock.patch.object(C, "_get", side_effect=gets), \
                mock.patch.object(C.time, "sleep"):
            out = C.post_threads(self.MOCHI)
        self.assertTrue(out["link_reply"])
        self.assertEqual(len([c for c in calls if c.get("reply_to_id")]), 1, "no second reply once ours is found")

    def test_a_retry_that_cannot_look_does_not_post_a_second_reply(self):
        calls = []

        def post(url, fields, timeout=60):
            calls.append(fields)
            if fields.get("reply_to_id"):
                raise RuntimeError("timeout")  # maybe published, maybe not
            return {"id": f"id{len(calls)}"}

        gets = [{"id": "u"}, {"status": "FINISHED"}, RuntimeError("down"), {"permalink": "p"}]   # the look fails
        with mock.patch.dict(os.environ, {"THREADS_TOKEN": "t", "THREADS_USER_ID": "u"}), \
                mock.patch.object(C, "_post", side_effect=post), mock.patch.object(C, "_get", side_effect=gets), \
                mock.patch.object(C.time, "sleep"), mock.patch("sys.stdout"):   # the ::error:: line is not this run's
            out = C.post_threads(self.MOCHI)
        self.assertFalse(out["link_reply"], "the sweeper looks again later")
        self.assertEqual(len([c for c in calls if c.get("reply_to_id")]), 1, "a second reply could double the first")

    def test_a_post_whose_link_reply_failed_is_recorded_and_the_step_stays_green(self):
        data = {"clips": {"u/en": self.MOCHI}, "schedule": [{"date": "2026-10-15", "slot": 1, "channel": "threads", "clip": "u/en"}]}
        posted = {"id": "9", "link": "https://www.threads.com/@b/post/9", "link_reply": False}
        with mock.patch.object(C, "load", return_value=data), mock.patch.object(C.CLIPS.__class__, "exists", return_value=True), \
                mock.patch.object(C, "post_threads", return_value=posted), mock.patch.object(P, "record_post") as rec, \
                mock.patch.object(C, "posted_log", return_value=[]), \
                mock.patch.object(C, "qa_variant", return_value=({"id": "a"}, [])), \
                mock.patch.object(sys, "argv", ["x", "threads", "--slot", "1", "--date", "2026-10-15"]), \
                mock.patch("sys.stdout") as out:
            self.assertEqual(C.main(), 0, "a red step would re-dispatch the slot and post the clip twice")
        rec.assert_called_once()
        self.assertIn("::error::", "".join(str(c.args[0]) for c in out.write.call_args_list))

    def test_threads_link_reply_is_retried_and_a_missing_one_is_flagged(self):
        calls = []

        def flaky(url, fields, timeout=60):
            calls.append(fields)
            if fields.get("reply_to_id") and len([c for c in calls if c.get("reply_to_id")]) < 3:
                raise RuntimeError("HTTP 500")
            return {"id": f"id{len(calls)}"}

        with mock.patch.dict(os.environ, {"THREADS_TOKEN": "t", "THREADS_USER_ID": "u"}), \
                mock.patch.object(C, "_post", side_effect=flaky), \
                mock.patch.object(C, "_get", side_effect=[{"id": "u"}, {"status": "FINISHED"}, {"data": []}, {"data": []}, {"permalink": "p"}]), \
                mock.patch.object(C.time, "sleep"):
            out = C.post_threads(self.MOCHI)
        self.assertTrue(out["link_reply"])
        self.assertEqual(len([c for c in calls if c.get("reply_to_id")]), 3)
        always = lambda url, fields, timeout=60: (_ for _ in ()).throw(RuntimeError("x")) if fields.get("reply_to_id") else {"id": "i"}  # noqa: E731
        with mock.patch.dict(os.environ, {"THREADS_TOKEN": "t", "THREADS_USER_ID": "u"}), \
                mock.patch.object(C, "_post", side_effect=always), \
                mock.patch.object(C, "_get", side_effect=[{"id": "u"}, {"status": "FINISHED"}, {"data": []}, {"data": []}, {"permalink": "p"}]), \
                mock.patch.object(C.time, "sleep"), mock.patch("sys.stdout"):   # the ::error:: line is not this run's
            self.assertFalse(C.post_threads(self.MOCHI)["link_reply"])

    def test_a_failed_publish_publishes_the_same_container_again_after_the_wait(self):
        calls, waits = [], []

        def post(url, fields, timeout=60):
            calls.append((url.rsplit("/", 1)[-1], dict(fields)))
            if url.endswith("threads_publish") and fields.get("creation_id") == "reply-1" and sum(
                    1 for u, f in calls if f.get("creation_id") == "reply-1") < 2:
                raise RuntimeError("HTTP 400 (#24) The requested resource does not exist")   # not ready yet
            return {"id": "reply-1" if "reply_to_id" in fields else f"id{len(calls)}"}

        with mock.patch.dict(os.environ, {"THREADS_TOKEN": "t", "THREADS_USER_ID": "u"}), \
                mock.patch.object(C, "_post", side_effect=post), \
                mock.patch.object(C, "_get", side_effect=[{"id": "u"}, {"status": "FINISHED"}, {"data": []}, {"permalink": "p"}]), \
                mock.patch.object(C.time, "sleep", side_effect=waits.append):
            out = C.post_threads(self.MOCHI)
        self.assertTrue(out["link_reply"])
        self.assertEqual(1, len([f for _u, f in calls if f.get("reply_to_id")]), "one container for the reply")
        self.assertEqual(2, len([f for _u, f in calls if f.get("creation_id") == "reply-1"]), "published again")
        self.assertIn(C.REPLY_WAIT, waits)   # the new container gets time before the first publish

    def test_every_planned_clip_caption_carries_its_link_on_instagram_and_telegram(self):
        data = C.load()
        self.assertEqual(("telegram",), C.LINK_IN_CAPTION)
        for key, c in sorted(data["clips"].items()):
            for channel in C.LINK_IN_CAPTION:
                store, play = C.download_urls(c, channel)
                self.assertTrue(C.DL.has_download_link(C.caption(c, channel), store, play), (key, channel))
            # Instagram (owner 2026-10-17): the profile-link line in the clip's language and the app's brand
            # hashtag instead of a URL - for every planned clip, the non-Latin store names included.
            ig = C.caption(c, "instagram")
            self.assertEqual([], C.IGB.caption_problems(ig, c["locale"], c["name"], c["store_url"]), (key, ig))
            self.assertEqual(1, sum(t.casefold() == C.IGB.brand_tag(c["name"], c["store_url"]).casefold()
                                    for t in ig.split()), key)


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
                mock.patch.object(C, "posted_log", return_value=[]), \
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


class ReviewLinksTest(unittest.TestCase):
    """review_links.json: the existing-user review link goes only to the 9 App x country pairs whose
    category leader has <= 20 ratings (00_GrowthEngine reports/top1_gap_2026-10-16.md), in their locale."""

    PAIRS = {("6818607603", "kr"), ("6806826699", "de"), ("6798814385", "tw"), ("6798814385", "kr"),
             ("6779552704", "de"), ("6818607603", "us"), ("6782275018", "jp"), ("6773017109", "us"),
             ("6781337213", "kr")}

    @staticmethod
    def pair_clip(app_id, locale, hook):
        return dict(clip("claudeusagemini", locale), hook=hook, name="UsageNow", search="UsageNow",
                    store_url=f"https://apps.apple.com/us/app/id{app_id}?pt=118326163&ct=h7_x&mt=8")

    def test_exactly_the_nine_pairs_with_their_own_locale(self):
        cfg = R.config()
        self.assertEqual({(p["app_id"], p["country"]) for p in cfg["pairs"]}, self.PAIRS)
        self.assertTrue(all(p["top1_ratings"] <= 20 for p in cfg["pairs"]))
        country_locale = {"kr": ("ko", "ko"), "de": ("de-DE", "de"), "tw": ("zh-Hant", "zh-Hant"),
                          "us": ("en-US", "en"), "jp": ("ja", "ja")}
        for p in cfg["pairs"]:
            self.assertEqual((p["official_locale"], p["clip_locale"]), country_locale[p["country"]])

    def test_labels_are_the_geo_review_sentences_word_for_word(self):
        import ast
        geo = Path(__file__).resolve().parents[2] / "_engine" / "geo" / "gen_app_store_review_ctas.py"
        tree = ast.parse(geo.read_text(encoding="utf-8"))
        labels = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                      and getattr(node.targets[0], "id", None) == "REVIEW_LABELS")
        for locale, label in R.config()["labels"].items():
            self.assertEqual(label, labels[locale], locale)

    def test_link_is_the_bare_review_action_without_attribution(self):
        url = R.review_url("6818607603")
        self.assertEqual(url, "https://apps.apple.com/app/id6818607603?action=write-review")
        self.assertRegex(url, R.REVIEW_URL_RE)
        for token in ("ct=", "pt=", "mt="):
            self.assertNotIn(token, url)
        with self.assertRaises(ValueError):
            R.review_url("12")

    def test_incentives_superlatives_and_duplicates_are_refused(self):
        base = R.config()
        for bad in ("Leave 5 stars!", "Rate it ⭐", "Review it and get a gift", "Get Pro free",
                    "給五星好評", "The best app? Rate it", "Rate it: https://x"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    R.validate(dict(base, labels=dict(base["labels"], ko=bad)))
        with self.assertRaises(ValueError):
            R.validate(dict(base, pairs=base["pairs"] + base["pairs"][:1]))

    def test_matched_by_app_id_and_locale_never_by_key(self):
        self.assertIsNotNone(R.for_clip(self.pair_clip("6818607603", "ko", "AI 한도 초과?")))  # key claudeusagemini
        self.assertIsNotNone(R.for_clip(self.pair_clip("6818607603", "en", "Hit your AI limit?")))
        self.assertIsNone(R.for_clip(self.pair_clip("6818607603", "ja", "上限？")))       # JP leader has 11,602
        self.assertIsNone(R.for_clip(self.pair_clip("6785004775", "en", "Cute list")))  # Mochi: not a pair
        self.assertIsNone(R.for_clip(clip("a", "en")))
        self.assertEqual(R.for_official("6798814385", "zh-Hant")["url"],
                         "https://apps.apple.com/app/id6798814385?action=write-review")
        self.assertIsNone(R.for_official("6798814385", "zh-Hans"))
        self.assertIsNone(R.for_official("6818607603", "en-GB"))

    def test_only_the_telegram_caption_carries_it_and_it_passes_qa(self):
        c = self.pair_clip("6818607603", "ko", "작업 중에 또 AI 한도 초과?")
        variant = {"id": "a", "lead": c["hook"]}
        cap = C.caption(c, "telegram", variant)
        self.assertIn("https://apps.apple.com/app/id6818607603?action=write-review", cap)
        self.assertIn(R.config()["labels"]["ko"], cap)
        self.assertEqual(C.post_qa.clip_problems(c, "telegram", cap, online=False), [])
        self.assertTrue(cap.split("\n")[-1].startswith("#"))  # hashtags stay last
        for channel in ("instagram", "threads"):
            self.assertNotIn("write-review", C.caption(c, channel, variant))
        other = clip("a", "ko")
        self.assertNotIn("write-review", C.caption(other, "telegram", {"id": "a", "lead": "훅"}))


class VideoComplianceGateTest(unittest.TestCase):
    """Owner rule: only real screen recordings with no price / Free / Pro on screen are ever posted."""

    def test_a_clip_without_the_compliance_record_is_refused(self):
        bad = {k: v for k, v in clip("a", "en").items() if k != "compliance"}
        self.assertTrue(Q.video_compliance_problems(bad))
        self.assertTrue(Q.clip_problems(bad, "telegram", "text", online=False)[0].startswith("clip has no video compliance"))

    def test_an_incomplete_record_is_refused(self):
        for rec in ({}, {"real_recording": True}, {"real_recording": True, "screen_text_ok": False, "board": "x"},
                    {"real_recording": "yes", "screen_text_ok": True, "board": "x"}, "ok",
                    {"store_claims_ok": False, "screen_text_ok": True, "board": "x", "real_recording": False},
                    {"store_claims_ok": True, "screen_text_ok": True, "board": ""}):
            self.assertTrue(Q.video_compliance_problems(dict(clip("a", "en"), compliance=rec)), rec)

    def test_the_record_passes(self):
        # Owner rule 2026-10-18: a store-screenshot cut (real_recording False) that passed both floors goes out.
        self.assertEqual(Q.video_compliance_problems(clip("a", "en")), [])
        older = {"real_recording": True, "screen_text_ok": True, "board": "0123456789abcdef"}  # the stricter record
        self.assertEqual(Q.video_compliance_problems(dict(clip("a", "en"), compliance=older)), [])

    def test_qa_variant_never_picks_a_variant_for_a_non_compliant_clip(self):
        bad = {k: v for k, v in clip("a", "en").items() if k != "compliance"}
        variant, problems = C.qa_variant(bad, "telegram", {"id": "a", "lead": "a hook"}, online=False)
        self.assertIsNone(variant)
        self.assertTrue(problems)


if __name__ == "__main__":
    unittest.main()
