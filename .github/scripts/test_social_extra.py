#!/usr/bin/env python3
"""Tests for social_extra.py (mocked HTTP, no network)."""
import datetime as dt
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.parse
import xmlrpc.client
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("POST_QA_OFFLINE", "1")  # the pre-post QA gate makes no network calls in tests

import clip_progress as P  # noqa: E402
import download_links as DL  # noqa: E402
import social_extra as S  # noqa: E402

S.PAUSE = 0
# Many tests patch os.environ with clear=True, which drops POST_QA_OFFLINE; on a runner with direct
# internet the gate then looked up the fixtures' fake app id1, got "no such app" and cached it
# (lru_cache), refusing every fixture clip for the rest of the run (social-extra failed 2026-10-15).
S.post_qa.offline = lambda: True
S.STAGGER = 0
DAY = dt.date(2026, 10, 15)


def clip(app, locale):
    return {"app": app, "locale": locale, "url": f"https://files.catbox.moe/{app}_{locale}.mp4",
            "store_url": f"https://apps.apple.com/us/app/id1?pt=118326163&ct=h7_{app}_{locale}&mt=8",
            "hook": f"{app} {HOOK.get(locale, 'hook')} {locale}", "name": f"{app} name", "search": app,
            "tags": ["#a", "#b", "#c"], "compliance": COMPLIANT}


# The record 00_GrowthEngine schedule_posts.py puts on a real-recording clip (post_qa.video_compliance_problems).
COMPLIANT = {"real_recording": True, "screen_text_ok": True, "board": "0123456789abcdef"}


HOOK = {"zh-Hant": "鉤子", "ko": "훅", "ja": "フック"}  # each locale's hook line is in its own script (post_qa)


DATA = {
    "clips": {"a/en": clip("a", "en"), "a/zh-Hant": clip("a", "zh-Hant"), "a/ko": clip("a", "ko"),
              "b/en": clip("b", "en")},
    "schedule": [
        {"date": "2026-10-10", "slot": 1, "channel": "telegram", "clip": "a/ko"},
        {"date": "2026-10-15", "slot": 1, "channel": "telegram", "clip": "a/zh-Hant"},
        {"date": "2026-10-15", "slot": 1, "channel": "instagram", "clip": "a/en"},
        {"date": "2026-10-15", "slot": 15, "channel": "instagram", "clip": "b/en"},
    ],
}


class Fake:
    """Answers http() calls from (method, url-substring, response) routes, in order of first match."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __call__(self, method, url, data=None, headers=None, timeout=180, raw=False):
        self.calls.append({"method": method, "url": url, "data": data, "headers": headers or {}})
        for m, part, resp in self.routes:
            if m == method and part in url:
                out = resp(url, data, headers) if callable(resp) else resp
                if isinstance(out, Exception):
                    raise out
                return out
        raise AssertionError(f"unexpected {method} {url}")

    def find(self, part, method=None):
        return [c for c in self.calls if part in c["url"] and (method is None or c["method"] == method)]


def without_android(ios_id):
    """The real Android snapshot minus one app: the card fixture's CountDaysNow went live on Google Play
    (2026-10-17), so the iPhone-only tests take it out of the snapshot instead of depending on live data."""
    import social_post_common as common
    snapshot = {k: v for k, v in common.android_apps().items() if k != ios_id}
    return mock.patch.object(common, "android_apps", return_value=snapshot)


def item(kind="clip", locale="en"):
    if kind == "clip":
        return S.clip_item(f"a/{locale}", clip("a", locale), "bluesky")
    return {"kind": "card", "key": "card/x/2026-10-15", "locale": locale, "image": "https://raw.example/card.jpg",
            "caption": "Christmas 70 days to go\nPlan\n\nSearch", "title": "Christmas 70 days to go",
            "name": "CountDaysNow", "hook": "Christmas 70 days to go", "tags": ["#countdown"],
            "button": "Get it on the App Store", "store": "https://apps.apple.com/us/app/id6807079789?ct=cd_x",
            "play": None}


ENV_ALL = {k: "v" for keys in S.SECRETS.values() for k in keys}
ENV_ALL.update({"FB_PAGE_ID": "123", "TUMBLR_BLOG": "lumiapps", "NAVER_ID": "lumi"})


def search_clip(app="u", locale="en", lead="Hit your AI limit mid-task again?"):
    return dict(clip(app, locale), name="UsageNow: AI Usage Tracker", search="UsageNow",
                keyline="Claude, Codex & Copilot Limits", keywords=["quota", "reset", "countdown"],
                tags=["#AIUsageTracker", "#Quota", "#Reset", "#appstore", "#UsageNow"],
                hooks=[{"id": "a", "lead": lead, "benefit": "See what's left and when it resets"},
                       {"id": "b", "lead": "See what's left and when it resets", "benefit": "Alerts before you run out"}])


class SearchShapeTest(unittest.TestCase):
    def test_youtube_title_is_problem_plus_app_plus_shorts(self):
        it = S.clip_item("u/en", search_clip(lead="L" * 150), "youtube", DAY)
        title, desc, words = S.yt_meta(it)
        self.assertLessEqual(len(title), 100)
        self.assertTrue(title.endswith("| UsageNow #Shorts"))
        self.assertIn("quota · reset · countdown", desc)
        self.assertIn("App Store: https://apps.apple.com", desc)
        self.assertEqual(desc.splitlines()[-1].split()[0], "#Shorts")
        self.assertIn("quota", words)
        self.assertNotIn("appstore", words)
        self.assertLessEqual(sum(len(w) + 1 for w in words), 450)

    def test_pinterest_title_and_alt_text_carry_the_keywords(self):
        fake = Fake([("POST", "/v5/media", {"media_id": "m1", "upload_url": "https://s3.example/up", "upload_parameters": {}}),
                     ("POST", "s3.example", {}), ("GET", "/media/m1", {"status": "succeeded"}), ("POST", "/pins", {"id": "p"})])
        it = S.clip_item("u/en", search_clip(), "pinterest", DAY)
        with mock.patch.dict(os.environ, {"PINTEREST_TOKEN": "t", "PINTEREST_BOARD_ID": "b"}, clear=True), \
                mock.patch.object(S, "http", fake), mock.patch.object(S, "fetch_bytes", return_value=b"mp4"):
            S.post_pinterest(it)
        pin = json.loads(fake.find("/pins")[0]["data"])
        self.assertIn("Claude, Codex & Copilot Limits", pin["title"])
        self.assertLessEqual(len(pin["title"]), 100)
        self.assertIn("UsageNow: AI Usage Tracker", pin["alt_text"])
        self.assertIn("Claude, Codex & Copilot Limits", pin["alt_text"])

    def test_bluesky_alt_and_item_variant(self):
        it = S.clip_item("u/en", search_clip(), "bluesky", DAY)
        self.assertIn(it["variant"], ("a", "b"))
        self.assertTrue(it["caption"].startswith(it["hook"]))
        self.assertIn("Claude, Codex & Copilot Limits", it["alt"])
        text, facets = S.bsky_rich(it["caption"] + "\n" + "x" * 400, [("App Store", "https://a")])
        self.assertLessEqual(len(text), 300)

    def test_cards_take_keyword_tags_and_alt_from_the_planner(self):
        import search_caption as SC
        seo = {"seo": {"countdaysnow": {"ko": {"tags": ["#카운트다운", "#수능", "#appstore"], "keyline": "D-day 계산"}}}}
        with mock.patch.object(SC, "_feed", return_value=seo):
            self.assertEqual(SC.card_tags("countdaysnow", "ko"), ["#카운트다운", "#수능"])
            self.assertIn("D-day 계산", SC.card_alt("CountDaysNow", "수능 D-35\n오늘도", "countdaysnow", "ko"))
            self.assertEqual(SC.card_tags("nothing", "ko"), [])
            day = dt.date(2026, 10, 15)
            with mock.patch.object(S.countdown_cards, "due", return_value=None):
                cards = S.todays_cards(day, "bluesky")
            for c in cards:
                self.assertTrue(c.get("alt"))


class PlanTest(unittest.TestCase):
    def test_mirrors_the_instagram_entry_first_and_skips_posted_clips(self):
        items = S.plan("dailymotion", DATA, [], DAY, 1, check=False)
        self.assertEqual([i["key"] for i in items], ["a/en"])
        posts = [{"channel": "facebook", "clip": "a/en", "posted_at": "2026-10-14T01:00:00Z"}]
        self.assertEqual([i["key"] for i in S.plan("facebook", DATA, posts, DAY, 1, check=False)], ["a/zh-Hant"])

    def test_daily_cap_is_honored(self):
        posts = [{"channel": "dailymotion", "clip": "z/en", "posted_at": "2026-10-15T01:00:00Z"}]
        self.assertEqual(S.plan("dailymotion", DATA, posts, DAY, 15, check=False), [])

    def test_locale_only_platforms_take_their_locale_from_the_backlog(self):
        self.assertEqual([i["key"] for i in S.todays_clips(DATA, [], "naver", DAY, 1)], ["a/ko"])
        self.assertEqual([i["key"] for i in S.todays_clips(DATA, [], "plurk", DAY, 1)], ["a/zh-Hant"])
        done = [{"channel": "naver", "clip": "a/ko", "posted_at": "2026-10-11T01:50:00Z"}]
        self.assertEqual(S.todays_clips(DATA, done, "naver", DAY, 15), [])

    def test_cards_only_in_slot_15_and_only_when_published(self):
        day = dt.date(2026, 11, 1)  # 수능 + Christmas countdowns active
        with mock.patch.object(S, "exists", return_value=True):
            keys = [i["key"] for i in S.plan("pinterest", {"clips": {}, "schedule": []}, [], day, 15)]
            self.assertTrue(any(k.startswith("card/") for k in keys))
            self.assertEqual(S.plan("pinterest", {"clips": {}, "schedule": []}, [], day, 1), [])
        with mock.patch.object(S, "exists", return_value=False):
            self.assertEqual(S.plan("pinterest", {"clips": {}, "schedule": []}, [], day, 15), [])

    def test_caption_and_campaign_follow_the_platform(self):
        it = S.clip_item("a/zh-Hant", clip("a", "zh-Hant"), "plurk")
        self.assertIn("ct=h7_a_pk", it["store"])
        self.assertIn("a 鉤子 zh-Hant", it["caption"])

    def test_android_clip_play_link_carries_each_platforms_own_ct(self):
        mochi = dict(clip("mochi", "en"), store_url="https://apps.apple.com/us/app/id6785004775?pt=118326163"
                     "&ct=h7_mochi_en&mt=8")
        for channel, ct in S.CT.items():
            with self.subTest(channel=channel):
                it = S.clip_item("mochi/en", mochi, channel)
                self.assertIn(f"ct=h7_mochi_{ct}", it["store"])
                self.assertTrue(it["play"].endswith(f"&referrer=utm_source%3Dh7_mochi_{ct}%26utm_campaign%3Dmochi"))
                self.assertEqual(f"Google Play: {it['play']}", S.link_lines(it)[1])
        it = S.clip_item("mochi/en", mochi, "youtube")
        self.assertIn(f"Google Play: {it['play']}", S.yt_meta(it)[1])
        self.assertIsNone(S.clip_item("a/en", clip("a", "en"), "bluesky")["play"])  # id1 is iOS only

    def test_missing_secrets_log_not_configured_and_post_nothing(self):
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(S, "http") as h, \
                mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(S.run(S.CHANNELS, DAY, 1, data=DATA), 0)
            self.assertEqual(S.whoami(S.CHANNELS), 0)
        h.assert_not_called()
        self.assertEqual(out.getvalue().count("not configured"), 2 * len(S.CHANNELS))

    def test_dry_run_posts_nothing(self):
        with mock.patch.dict(os.environ, ENV_ALL, clear=True), mock.patch.object(S, "http") as h, \
                mock.patch.object(P, "record_post") as rec, mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            S.run(("dailymotion", "bluesky"), DAY, 1, dry_run=True, data=DATA)
        h.assert_not_called()
        rec.assert_not_called()
        self.assertIn("would post clip a/en", out.getvalue())

    def test_a_failure_is_logged_and_the_run_still_succeeds(self):
        with mock.patch.dict(os.environ, ENV_ALL, clear=True), \
                mock.patch.object(S, "post_dailymotion", side_effect=RuntimeError("boom")), \
                mock.patch.dict(S.POSTERS, {"dailymotion": S.post_dailymotion}), \
                mock.patch.object(P, "record_post") as rec, mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(S.run(("dailymotion",), DAY, 1, data=DATA), 0)
        rec.assert_not_called()
        self.assertIn("::warning::dailymotion", out.getvalue())

    def test_successful_post_is_recorded_once_per_platform(self):
        posted = mock.Mock(return_value={"id": "9", "link": "https://www.dailymotion.com/video/x9"})
        with mock.patch.dict(os.environ, ENV_ALL, clear=True), mock.patch.dict(S.POSTERS, {"dailymotion": posted}), \
                mock.patch.object(S, "load_posts", return_value=[]), \
                mock.patch.object(P, "record_post") as rec, mock.patch("sys.stdout", new_callable=io.StringIO):
            S.run(("dailymotion",), DAY, 1, data=DATA)
        rec.assert_called_once_with("dailymotion", "a/en", "https://www.dailymotion.com/video/x9", media_id="9",
                                    variant="a")


class ServedElsewhereTest(unittest.TestCase):
    def test_bluesky_is_left_to_threads_autopilot_unless_forced(self):
        with mock.patch.dict(os.environ, ENV_ALL, clear=True), mock.patch.object(S, "http") as h, \
                mock.patch.object(P, "record_post") as rec, mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertFalse(S.configured("bluesky"))
            S.run(("bluesky",), DAY, 1, data=DATA)
        h.assert_not_called()
        rec.assert_not_called()
        self.assertIn("served by threads-autopilot", out.getvalue())
        with mock.patch.dict(os.environ, dict(ENV_ALL, FORCE_GUIDE_BLUESKY="1"), clear=True):
            self.assertTrue(S.configured("bluesky"))
        self.assertNotIn("mastodon", S.CHANNELS)

    def test_youtube_is_left_to_the_mac_unless_forced(self):
        with mock.patch.dict(os.environ, ENV_ALL, clear=True), mock.patch.object(S, "http") as h, \
                mock.patch.object(P, "record_post") as rec, mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertFalse(S.configured("youtube"))
            S.run(("youtube",), DAY, 1, data=DATA)
        h.assert_not_called()
        rec.assert_not_called()
        self.assertIn("served by 00_GrowthEngine hook-shorts-youtube.yml", out.getvalue())
        self.assertIn("FORCE_GUIDE_YOUTUBE=1", out.getvalue())
        with mock.patch.dict(os.environ, dict(ENV_ALL, FORCE_GUIDE_YOUTUBE="1"), clear=True):
            self.assertTrue(S.configured("youtube"))
            self.assertFalse(S.configured("bluesky"))  # one override never releases the other channel

    def test_pinterest_is_left_to_the_mac_unless_forced(self):
        with mock.patch.dict(os.environ, ENV_ALL, clear=True), mock.patch.object(S, "http") as h, \
                mock.patch.object(P, "record_post") as rec, mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertFalse(S.configured("pinterest"))
            S.run(("pinterest",), DAY, 15, data=DATA)
        h.assert_not_called()
        rec.assert_not_called()
        self.assertIn("served by 00_GrowthEngine social/feed_poster.py (Mac)", out.getvalue())
        with mock.patch.dict(os.environ, dict(ENV_ALL, FORCE_GUIDE_PINTEREST="1"), clear=True):
            self.assertTrue(S.configured("pinterest"))

    def test_tiktok_is_export_only_with_every_link_written_out(self):
        self.assertNotIn("tiktok", S.CHANNELS)  # the Mac posts it; nothing here ever calls TikTok
        it = mochi_item("tiktok")
        text = S.final_text(it, "tiktok")
        self.assertIn("ct=h7_mochi_tt", it["store"])
        self.assertIn(it["store"], text)
        self.assertIn(S.play_of(it), text)
        self.assertLessEqual(len(text), 2200)
        self.assertEqual(S.qa_problems(it, "tiktok", online=False), [])
        long = mochi_item("tiktok", caption="word " * 600)
        self.assertLessEqual(len(S.final_text(long, "tiktok")), 2200)  # the caption gives way, never a link
        self.assertIn(long["store"], S.final_text(long, "tiktok"))

    def test_feed_carries_the_exact_pieces_the_mac_sends(self):
        data = {"clips": {"a/en": search_clip("a", "en")}, "schedule": []}
        with mock.patch.object(S, "exists", return_value=True), mock.patch.object(S.SC, "winners", return_value={}):
            feed = S.export(DAY, data=data, perf={})
        tt = feed["pool"]["tiktok"][0]
        self.assertIn("ct=h7_a_tt", tt["store"])
        self.assertIn(tt["store"], tt["tiktok"]["caption"])
        pin = feed["pool"]["pinterest"][0]
        self.assertEqual(pin["pinterest"]["link"], pin["store"])
        self.assertIn(pin["store"], pin["pinterest"]["description"])
        self.assertNotIn("tiktok", feed["pool"]["youtube"][0])
        json.dumps(feed)

    def test_youtube_uses_a_known_winner_instead_of_the_problem_line(self):
        with mock.patch.object(S.SC, "winners", return_value={}):
            it = S.clip_item("u/en", dict(search_clip(), hook_best="b"), "youtube", DAY)
            self.assertEqual(it["variant"], "b")
            it = S.clip_item("u/en", search_clip(), "youtube", DAY)
            self.assertEqual(it["variant"], "a")

    def test_export_pool_ranks_boost_apps_first_with_search_fields(self):
        data = {"clips": {"a/en": search_clip("a", "en"), "b/en": search_clip("b", "en"),
                          "b/ja": search_clip("b", "ja"), "c/en": dict(clip("c", "en"), url="")},
                "schedule": []}
        perf = {"boost": ["b"]}
        with mock.patch.object(S, "exists", return_value=True), mock.patch.object(S.SC, "winners", return_value={}):
            feed = S.export(DAY, data=data, perf=perf)
        self.assertEqual(set(feed["pool"]), {"bluesky", "youtube", "pinterest", "tiktok"})
        self.assertEqual([i["key"] for i in feed["pool"]["youtube"]], ["b/en", "b/ja", "a/en"])  # c has no video
        top = feed["pool"]["youtube"][0]
        self.assertEqual(top["boost_rank"], 1)
        self.assertEqual(top["youtube"]["title"], "Hit your AI limit mid-task again? | UsageNow #Shorts")  # problem first
        self.assertEqual(top["variant"], "a")
        self.assertLessEqual(len(top["youtube"]["title"]), 100)
        self.assertIn("ct=h7_b_yt", top["store"])
        self.assertIn("quota · reset · countdown", top["youtube"]["description"])
        self.assertEqual(top["youtube"]["tags"][:3], ["quota", "reset", "countdown"])
        bs = feed["pool"]["bluesky"][-1]
        self.assertNotIn("boost_rank", bs)
        self.assertTrue(bs["alt"] and bs["variant"] and bs["keywords"])
        self.assertIn("_bs", bs["store"])
        self.assertEqual(feed["performance"], perf)
        json.dumps(feed)


class YoutubeLinksTest(unittest.TestCase):
    def test_mac_uploads_join_the_post_log_once_and_show_on_the_page(self):
        import youtube_links as YL
        posted = {"posted": {
            "a/en": {"at": "2026-10-15T12:20:00Z", "videoId": "abcDEF12345", "url": "https://youtube.com/shorts/abcDEF12345"},
            "b/en": {"at": "2026-10-15T18:20:00Z", "videoId": "x", "url": "https://evil.example/x"},
            "bad": {"at": "2026-10-15T18:20:00Z", "url": "https://youtube.com/shorts/abcDEF12345"}}}
        log = {"posts": [{"channel": "instagram", "clip": "a/en", "link": "https://ig/1", "posted_at": "2026-10-15T01:20:00Z"}]}
        self.assertEqual(YL.merge(posted, log), 1)
        self.assertEqual(YL.merge(posted, log), 0)  # never twice
        yt = [p for p in log["posts"] if p["channel"] == "youtube"]
        self.assertEqual(yt, [{"channel": "youtube", "clip": "a/en", "link": "https://youtube.com/shorts/abcDEF12345",
                               "posted_at": "2026-10-15T12:20:00Z", "id": "abcDEF12345"}])
        clips = {"clips": {"a/en": clip("a", "en")}, "schedule": []}
        section = P.build_section(clips, log["posts"], {}, dt.datetime(2026, 10, 16, 1, tzinfo=dt.timezone.utc))
        self.assertIn("[YT](https://youtube.com/shorts/abcDEF12345)", section)
        self.assertIn("| YouTube Shorts | 自動 | 1 | — |", section)

    def test_a_short_taken_down_on_the_mac_is_marked_here_and_its_link_leaves_the_page(self):
        import youtube_links as YL
        mark = {"at": "2026-10-17T10:00:00Z", "status": "private", "reversible": True}
        posted = {"posted": {
            "a/en": {"at": "2026-10-15T12:20:00Z", "videoId": "abcDEF12345",
                     "url": "https://youtube.com/shorts/abcDEF12345", "taken_down": mark},
            "c/en": {"at": "2026-10-15T13:20:00Z", "videoId": "keepME12345",
                     "url": "https://youtube.com/shorts/keepME12345"}}}
        log = {"posts": [{"channel": "youtube", "clip": "a/en", "link": "https://youtube.com/shorts/abcDEF12345",
                          "posted_at": "2026-10-15T12:20:00Z", "id": "abcDEF12345"},
                         {"channel": "instagram", "clip": "a/en", "link": "https://ig/1",
                          "posted_at": "2026-10-15T01:20:00Z"}]}
        self.assertEqual(YL.merge(posted, log), 1)   # c/en joins; a/en is there already
        self.assertEqual(YL.carry_takedowns(posted, log), 1)
        self.assertEqual(YL.carry_takedowns(posted, log), 0)   # never twice
        by = {(p["channel"], p["clip"]): p for p in log["posts"]}
        self.assertEqual(mark, by[("youtube", "a/en")]["taken_down"])
        self.assertNotIn("taken_down", by[("instagram", "a/en")])
        self.assertNotIn("taken_down", by[("youtube", "c/en")])
        clips = {"clips": {"a/en": clip("a", "en")}, "schedule": []}
        section = P.build_section(clips, log["posts"], {}, dt.datetime(2026, 10, 17, 11, tzinfo=dt.timezone.utc))
        self.assertNotIn("abcDEF12345", section)
        self.assertIn("https://ig/1", section)

    def test_a_new_cut_of_a_taken_down_short_joins_the_log_and_the_old_one_keeps_its_mark(self):
        import youtube_links as YL
        mark = {"at": "2026-10-17T10:00:00Z", "status": "private", "reversible": True}
        log = {"posts": [{"channel": "youtube", "clip": "a/en", "link": "https://youtube.com/shorts/oldOLD12345",
                          "posted_at": "2026-10-15T12:20:00Z", "id": "oldOLD12345"}]}
        # the Mac moved the old upload to "<key>#taken_down@<time>" when the new real-recording cut went up
        posted = {"posted": {
            "a/en#taken_down@2026-10-15T12:20:00Z": {"at": "2026-10-15T12:20:00Z", "videoId": "oldOLD12345",
                                                    "url": "https://youtube.com/shorts/oldOLD12345", "taken_down": mark},
            "a/en": {"at": "2026-10-18T12:20:00Z", "videoId": "newNEW12345", "url": "https://youtube.com/shorts/newNEW12345"}}}
        self.assertEqual(YL.merge(posted, log), 1)
        self.assertEqual(YL.merge(posted, log), 0)
        self.assertEqual(YL.carry_takedowns(posted, log), 1)   # the mark still reaches the old entry
        by = {p["id"]: p for p in log["posts"]}
        self.assertEqual(mark, by["oldOLD12345"]["taken_down"])
        self.assertNotIn("taken_down", by["newNEW12345"])
        self.assertEqual(["a/en", "a/en"], [p["clip"] for p in log["posts"]])
        clips = {"clips": {"a/en": clip("a", "en")}, "schedule": []}
        section = P.build_section(clips, log["posts"], {}, dt.datetime(2026, 10, 18, 13, tzinfo=dt.timezone.utc))
        self.assertIn("newNEW12345", section)
        self.assertNotIn("oldOLD12345", section)

    def test_missing_upload_log_leaves_the_page_alone(self):
        import youtube_links as YL
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(P, "POSTS", Path(tmp) / "posts.json"), \
                mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(YL.main(["--posted", str(Path(tmp) / "missing.json")]), 0)
            self.assertFalse((Path(tmp) / "posts.json").exists())
        self.assertIn("unreadable", out.getvalue())

    def test_export_lists_the_days_items_per_consumer_channel(self):
        with mock.patch.object(S, "exists", return_value=True):
            feed = S.export(dt.date(2026, 11, 1), data={"clips": DATA["clips"], "schedule": [
                dict(e, date="2026-11-01") if e["date"] == "2026-10-15" else e for e in DATA["schedule"]]})
        self.assertEqual(feed["schema"], S.FEED_SCHEMA)
        self.assertEqual(set(feed["items"]), {"bluesky", "mastodon", "youtube", "pinterest", "tiktok"})
        bs = feed["items"]["bluesky"]
        clips = [i["key"] for i in bs if i["kind"] == "clip"]
        self.assertEqual(clips, ["a/en", "a/zh-Hant", "b/en"])  # Instagram first, slot 1 then 15
        self.assertEqual([i["slot"] for i in bs if i["kind"] == "clip"], [1, 1, 15])
        self.assertTrue(any(i["kind"] == "card" for i in bs))
        self.assertFalse(any(i["kind"] == "card" for i in feed["items"]["youtube"]))
        self.assertIn("_ma", feed["items"]["mastodon"][0]["store"])
        json.dumps(feed)  # plain data only
        with mock.patch.object(S, "exists", return_value=False):
            feed = S.export(dt.date(2026, 11, 1), data={"clips": {}, "schedule": []})
        self.assertEqual(feed["items"]["bluesky"], [])

    def test_feed_and_posts_skip_items_the_qa_gate_refuses(self):
        broken = dict(DATA["clips"]["b/en"], hook="The best app ever")  # banned superlative
        data = {"clips": dict(DATA["clips"], **{"b/en": broken}), "schedule": DATA["schedule"]}
        with mock.patch.object(S, "exists", return_value=True), mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            feed = S.export(DAY, data=data)
        self.assertNotIn("b/en", [i["key"] for i in feed["items"]["bluesky"]])
        self.assertIn("a/en", [i["key"] for i in feed["items"]["bluesky"]])
        self.assertIn("QA refused", out.getvalue())
        posted = mock.Mock(return_value={"id": "9", "link": "l"})
        with mock.patch.dict(os.environ, ENV_ALL, clear=True), mock.patch.dict(S.POSTERS, {"dailymotion": posted}), \
                mock.patch.object(S, "load_posts", return_value=[]), mock.patch.object(P, "record_post"), \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            S.run(("dailymotion",), DAY, 15, data=data)
        posted.assert_not_called()


class HelpersTest(unittest.TestCase):
    def test_oauth1_signature_matches_the_reference_example(self):
        header = S.oauth1_header(
            "POST", "https://api.twitter.com/1.1/statuses/update.json?include_entities=true",
            "xvz1evFS4wEEPTGEFPHBog", "kAcSOqF21Fu85e7zjz7ZN2U4ZRhfV3WpwPAoE3Z7kBw",
            "370773112-GmHxMAgYyLbNEtIKZeRNFsMKPR9EyMZeS9weJAEb", "LswwdoUaIvS8ltyTt5jkRh4J50vUPVVHtR2YPi5kE",
            {"status": "Hello Ladies + Gentlemen, a signed OAuth request!"},
            nonce="kYjzVBB8Y0ZFabxSWbWovY3uYSQ2pTgmZeNu2VS4cg", timestamp=1318622958)
        self.assertIn('oauth_signature="hCtSmYh%2BiHYCEqBWrE7C7hYmtUk%3D"', header)

    def test_png_card_becomes_a_small_jpeg(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("pillow missing")
        buf = io.BytesIO()
        Image.effect_noise((1400, 1400), 90).convert("RGB").save(buf, "PNG")
        out = S.to_jpeg(buf.getvalue(), limit=300_000)
        self.assertTrue(out.startswith(b"\xff\xd8\xff"))
        self.assertLessEqual(len(out), 300_000)


class CardsTest(unittest.TestCase):
    def test_countdown_and_utility_cards_carry_their_own_caption_and_campaign(self):
        cards = S.todays_cards(dt.date(2026, 11, 1), "tumblr")
        kinds = {c["key"].split("/")[0] for c in cards}
        self.assertIn("card", kinds)
        for c in cards:
            self.assertTrue(c["image"].startswith("https://raw.githubusercontent.com/"))
            self.assertIn("_tb", c["store"])
            self.assertRegex(c["store"], r"ct=(cd_tb|ut_[a-z0-9]+_tb)&")  # app x platform, no event / type id
            self.assertTrue(c["caption"])
        self.assertTrue(all(c["locale"] == "ko" for c in S.todays_cards(dt.date(2026, 11, 1), "naver")))


class FacebookTest(unittest.TestCase):
    def test_reel_upload_flow_with_link_comment(self):
        fake = Fake([("POST", "rupload.facebook.com", {"success": True}),
                     ("POST", "/123/video_reels", lambda u, d, h: {"video_id": "v1"} if b"start" in d else {"success": True}),
                     ("POST", "/v1/comments", {"id": "c1"})])
        with mock.patch.dict(os.environ, {"FB_PAGE_ID": "123", "FB_PAGE_TOKEN": "pt"}, clear=True), \
                mock.patch.object(S, "http", fake):
            res = S.post_facebook(item())
        self.assertEqual(res, {"id": "v1", "link": "https://www.facebook.com/reel/v1"})
        up = fake.find("rupload")[0]
        self.assertEqual(up["headers"]["file_url"], item()["video"])
        self.assertEqual(up["headers"]["Authorization"], "OAuth pt")
        finish = fake.calls[2]["data"].decode()
        self.assertIn("video_state=PUBLISHED", finish)
        self.assertIn("upload_phase=finish", finish)
        self.assertIn("apps.apple.com", fake.find("/comments")[0]["data"].decode().replace("%2F", "/").replace("%3A", ":"))

    def test_ig_token_probe_supplies_a_page_token_when_fb_secrets_are_absent(self):
        pages = {"data": [{"id": "9", "name": "Read only", "access_token": "x", "tasks": ["ANALYZE"]},
                          {"id": "7", "name": "Lumi", "access_token": "page-tok", "tasks": ["CREATE_CONTENT", "MANAGE"]}]}
        fake = Fake([("GET", "/me/accounts", pages)])
        with mock.patch.dict(os.environ, {"IG_ACCESS_TOKEN": "ig"}, clear=True), mock.patch.object(S, "http", fake), \
                mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertTrue(S.configured("facebook"))
            self.assertEqual(S.fb_creds(), {"page": "7", "token": "page-tok"})
        self.assertIn("using Page 'Lumi' (7)", out.getvalue())
        self.assertNotIn("page-tok", out.getvalue())

    def test_instagram_login_token_that_cannot_list_pages_is_not_configured(self):
        fake = Fake([("GET", "/me/accounts", RuntimeError("HTTP 400 graph.facebook.com/v21.0/me/accounts: invalid"))])
        with mock.patch.dict(os.environ, {"IG_ACCESS_TOKEN": "IGAA"}, clear=True), mock.patch.object(S, "http", fake), \
                mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertIsNone(S.post_facebook(item()))
        self.assertIn("not configured", out.getvalue())


class BlueskyTest(unittest.TestCase):
    def session(self):
        return ("POST", "createSession", {"accessJwt": "jwt", "did": "did:plc:me", "handle": "lumi.bsky.social",
                                          "didDoc": {"service": [{"id": "#atproto_pds", "serviceEndpoint": "https://pds.example"}]}})

    def test_link_facets_point_at_byte_offsets(self):
        text, facets = S.bsky_rich("寫到一半", [("App Store", "https://a"), ("Google Play", "https://g")])
        raw = text.encode("utf-8")
        for f, label in zip(facets, ("App Store", "Google Play")):
            self.assertEqual(raw[f["index"]["byteStart"]:f["index"]["byteEnd"]].decode(), label)
        long, _ = S.bsky_rich("x" * 400, [("App Store", "https://a")])
        self.assertLessEqual(len(long), 300)

    def test_video_post_uses_the_video_service(self):
        fake = Fake([self.session(), ("GET", "getServiceAuth", {"token": "svc"}),
                     ("POST", "uploadVideo", {"jobId": "j1", "state": "JOB_STATE_RUNNING"}),
                     ("GET", "getJobStatus", {"jobStatus": {"jobId": "j1", "state": "JOB_STATE_COMPLETED", "blob": {"ref": "b"}}}),
                     ("POST", "createRecord", {"uri": "at://did:plc:me/app.bsky.feed.post/3abc"})])
        with mock.patch.dict(os.environ, {"BSKY_HANDLE": "lumi.bsky.social", "BSKY_APP_PASSWORD": "p"}, clear=True), \
                mock.patch.object(S, "http", fake), mock.patch.object(S, "fetch_bytes", return_value=b"mp4"):
            res = S.post_bluesky(item())
        self.assertEqual(res["link"], "https://bsky.app/profile/lumi.bsky.social/post/3abc")
        self.assertIn("aud=did%3Aweb%3Apds.example", fake.find("getServiceAuth")[0]["url"])
        self.assertEqual(fake.find("uploadVideo")[0]["headers"]["Authorization"], "Bearer svc")
        record = json.loads(fake.find("createRecord")[0]["data"])["record"]
        self.assertEqual(record["embed"]["$type"], "app.bsky.embed.video")
        kinds = [f["features"][0]["$type"].rsplit("#", 1)[1] for f in record["facets"]]
        self.assertEqual(sorted(kinds), ["link", "tag", "tag", "tag"])  # App Store link + #a #b #c

    def test_video_failure_falls_back_to_a_link_card(self):
        fake = Fake([self.session(), ("GET", "getServiceAuth", RuntimeError("HTTP 403 no video quota")),
                     ("POST", "createRecord", {"uri": "at://did:plc:me/app.bsky.feed.post/3x"})])
        with mock.patch.dict(os.environ, {"BSKY_HANDLE": "h", "BSKY_APP_PASSWORD": "p"}, clear=True), \
                mock.patch.object(S, "http", fake), mock.patch.object(S, "fetch_bytes", return_value=b"mp4"), \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            S.post_bluesky(item())
        embed = json.loads(fake.find("createRecord")[0]["data"])["record"]["embed"]
        self.assertEqual(embed["$type"], "app.bsky.embed.external")
        self.assertIn("apps.apple.com", embed["external"]["uri"])

    def test_card_is_uploaded_as_jpeg_blob(self):
        fake = Fake([self.session(), ("POST", "uploadBlob", {"blob": {"ref": "img"}}),
                     ("POST", "createRecord", {"uri": "at://did:plc:me/app.bsky.feed.post/3c"})])
        with mock.patch.dict(os.environ, {"BSKY_HANDLE": "h", "BSKY_APP_PASSWORD": "p"}, clear=True), \
                mock.patch.object(S, "http", fake), mock.patch.object(S, "fetch_bytes", return_value=b"png"), \
                mock.patch.object(S, "to_jpeg", return_value=b"\xff\xd8\xffjpg") as conv:
            S.post_bluesky(item("card"))
        conv.assert_called_once_with(b"png")
        self.assertEqual(fake.find("uploadBlob")[0]["headers"]["Content-Type"], "image/jpeg")
        self.assertEqual(json.loads(fake.find("createRecord")[0]["data"])["record"]["embed"]["$type"], "app.bsky.embed.images")


class YouTubeTest(unittest.TestCase):
    def test_resumable_upload_with_shorts_title_links_and_localizations(self):
        fake = Fake([("POST", "oauth2.googleapis.com/token", {"access_token": "at"}),
                     ("POST", "upload/youtube/v3/videos", (200, {"location": "https://upload.example/s1"}, b"")),
                     ("PUT", "upload.example/s1", {"id": "yt1", "status": {"privacyStatus": "private"}})])
        env = {"YT_CLIENT_ID": "c", "YT_CLIENT_SECRET": "s", "YT_REFRESH_TOKEN": "r"}
        it = S.clip_item("a/en", clip("a", "en"), "youtube")
        it["hook"] = "h" * 150
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(S, "http", fake), \
                mock.patch.object(S, "fetch_bytes", return_value=b"mp4"), mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            res = S.post_youtube(it, DATA)
        self.assertEqual(res["link"], "https://youtube.com/shorts/yt1")
        init = fake.find("uploadType=resumable")[0]
        body = json.loads(init["data"])
        self.assertLessEqual(len(body["snippet"]["title"]), 100)
        self.assertTrue(body["snippet"]["title"].endswith("#Shorts"))
        self.assertIn("apps.apple.com", body["snippet"]["description"])
        self.assertEqual(body["status"]["privacyStatus"], "public")
        self.assertEqual(set(body["localizations"]), {"zh-TW", "ko"})
        self.assertEqual(init["headers"]["X-Upload-Content-Length"], "3")
        self.assertIn("private until", out.getvalue())

    def test_localizations_dropped_when_refused(self):
        def init(url, data, headers):
            if b"localizations" in data:
                return RuntimeError("HTTP 400 invalidLanguage")
            return (200, {"location": "https://upload.example/s2"}, b"")
        fake = Fake([("POST", "oauth2", {"access_token": "at"}), ("POST", "upload/youtube", init),
                     ("PUT", "s2", {"id": "yt2"})])
        with mock.patch.dict(os.environ, {"YT_CLIENT_ID": "c", "YT_CLIENT_SECRET": "s", "YT_REFRESH_TOKEN": "r"}, clear=True), \
                mock.patch.object(S, "http", fake), mock.patch.object(S, "fetch_bytes", return_value=b"m"), \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(S.post_youtube(S.clip_item("a/en", clip("a", "en"), "youtube"), DATA)["id"], "yt2")
        self.assertEqual(len(fake.find("upload/youtube")), 2)


class PinterestTest(unittest.TestCase):
    def test_image_pin_finds_or_creates_the_board(self):
        fake = Fake([("GET", "/boards", {"items": [{"id": "b0", "name": "Other"}]}),
                     ("POST", "/boards", {"id": "b1"}), ("POST", "/pins", {"id": "p1"})])
        with mock.patch.dict(os.environ, {"PINTEREST_TOKEN": "t"}, clear=True), mock.patch.object(S, "http", fake):
            res = S.post_pinterest(item("card"))
        self.assertEqual(res["link"], "https://www.pinterest.com/pin/p1/")
        self.assertEqual(json.loads(fake.find("/boards", "POST")[0]["data"])["name"], "Lumi Apps")
        pin = json.loads(fake.find("/pins")[0]["data"])
        self.assertEqual(pin["board_id"], "b1")
        self.assertEqual(pin["media_source"], {"source_type": "image_url", "url": "https://raw.example/card.jpg"})
        self.assertIn("apps.apple.com", pin["link"])

    def test_video_pin_through_media_upload_and_token_refresh(self):
        fake = Fake([("POST", "/oauth/token", {"access_token": "fresh"}),
                     ("POST", "/v5/media", {"media_id": "m1", "upload_url": "https://s3.example/up",
                                            "upload_parameters": {"key": "k", "policy": "p"}}),
                     ("POST", "s3.example", {}), ("GET", "/media/m1", {"status": "succeeded"}),
                     ("POST", "/pins", {"id": "p2"})])
        env = {"PINTEREST_TOKEN": "old", "PINTEREST_REFRESH_TOKEN": "r", "PINTEREST_APP_ID": "a",
               "PINTEREST_APP_SECRET": "s", "PINTEREST_BOARD_ID": "b9"}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(S, "http", fake), \
                mock.patch.object(S, "fetch_bytes", return_value=b"mp4"):
            S.post_pinterest(item())
        s3 = fake.find("s3.example")[0]
        self.assertNotIn("Authorization", s3["headers"])
        self.assertIn(b'name="key"', s3["data"])
        pin = fake.find("/pins")[0]
        self.assertEqual(pin["headers"]["Authorization"], "Bearer fresh")
        self.assertEqual(json.loads(pin["data"])["media_source"]["media_id"], "m1")


class TumblrTest(unittest.TestCase):
    def test_npf_video_post_with_link_block_and_oauth1(self):
        fake = Fake([("POST", "/blog/lumiapps.tumblr.com/posts", {"response": {"id": 77, "id_string": "77"}})])
        env = {k: "v" for k in S.SECRETS["tumblr"]}
        env["TUMBLR_BLOG"] = "lumiapps"
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(S, "http", fake), \
                mock.patch.object(S, "fetch_bytes", return_value=b"mp4bytes"):
            res = S.post_tumblr(item())
        self.assertEqual(res["link"], "https://www.tumblr.com/lumiapps/77")
        call = fake.calls[0]
        self.assertTrue(call["headers"]["Authorization"].startswith("OAuth "))
        self.assertIn(b"mp4bytes", call["data"])
        payload = json.loads(call["data"].split(b"application/json\r\n\r\n")[1].split(b"\r\n--")[0])
        types = [b["type"] for b in payload["content"]]
        self.assertEqual(types[:4], ["text", "text", "video", "link"])
        self.assertEqual(payload["content"][0]["subtype"], "heading2")  # keyword-rich title
        self.assertEqual(payload["content"][2]["media"]["identifier"], "media0")


class NaverTest(unittest.TestCase):
    def test_card_upload_then_new_post(self):
        def rpc(url, data, headers):
            params, method = xmlrpc.client.loads(data)
            seen.append((method, params))
            answer = {"url": "https://blogfiles.naver.net/c.jpg"} if method == "metaWeblog.newMediaObject" else "2234"
            return (200, {}, xmlrpc.client.dumps((answer,), methodresponse=True).encode())
        seen = []
        fake = Fake([("POST", "api.blog.naver.com/xmlrpc", rpc)])
        with mock.patch.dict(os.environ, {"NAVER_ID": "lumi", "NAVER_BLOG_API_PASSWORD": "pw"}, clear=True), \
                mock.patch.object(S, "http", fake), mock.patch.object(S, "fetch_bytes", return_value=b"jpg"):
            res = S.post_naver(item("card", "ko"))
        self.assertEqual(res["link"], "https://blog.naver.com/lumi/2234")
        self.assertEqual([m for m, _ in seen], ["metaWeblog.newMediaObject", "metaWeblog.newPost"])
        post = seen[1][1][3]
        self.assertIn('<img src="https://blogfiles.naver.net/c.jpg"', post["description"])
        self.assertIn("apps.apple.com", post["description"])
        self.assertIs(seen[1][1][4], True)

    def test_fault_is_reported(self):
        fault = xmlrpc.client.dumps(xmlrpc.client.Fault(4, "bad password"), methodresponse=True).encode()
        with mock.patch.object(S, "http", Fake([("POST", "xmlrpc", (200, {}, fault))])):
            with self.assertRaisesRegex(RuntimeError, "bad password"):
                S.naver_call("blogger.getUsersBlogs", "", "u", "p")


class PlurkTest(unittest.TestCase):
    def test_card_upload_then_plurk_within_360_chars(self):
        fake = Fake([("POST", "/Timeline/uploadPicture", {"full": "https://images.plurk.com/x.jpg"}),
                     ("POST", "/Timeline/plurkAdd", {"plurk_id": 1295})])
        it = dict(item("card", "zh-Hant"), caption="倒數" * 300)
        with mock.patch.dict(os.environ, {k: "v" for k in S.SECRETS["plurk"]}, clear=True), \
                mock.patch.object(S, "http", fake), mock.patch.object(S, "fetch_bytes", return_value=b"jpg"):
            res = S.post_plurk(it)
        self.assertEqual(res["link"], "https://www.plurk.com/p/zz")
        add = fake.find("plurkAdd")[0]
        fields = dict(__import__("urllib.parse").parse.parse_qsl(add["data"].decode()))
        self.assertLessEqual(len(fields["content"]), 360)
        self.assertIn("https://images.plurk.com/x.jpg", fields["content"])
        self.assertEqual(fields["lang"], "tr_ch")
        self.assertIn("oauth_signature", add["headers"]["Authorization"])


class DailymotionTest(unittest.TestCase):
    def test_password_grant_then_url_upload(self):
        fake = Fake([("POST", "/oauth/token", {"access_token": "dm"}), ("POST", "/me/videos", {"id": "x9"})])
        with mock.patch.dict(os.environ, {k: "v" for k in S.SECRETS["dailymotion"]}, clear=True), \
                mock.patch.object(S, "http", fake):
            res = S.post_dailymotion(item())
        self.assertEqual(res["link"], "https://www.dailymotion.com/video/x9")
        self.assertIn("grant_type=password", fake.calls[0]["data"].decode())
        sent = fake.calls[1]["data"].decode()
        self.assertIn("channel=tech", sent)
        self.assertIn("published=true", sent)
        self.assertIn("files.catbox.moe", __import__("urllib.parse").parse.unquote(sent))




class PageTest(unittest.TestCase):
    def test_extra_platforms_show_unset_until_their_first_post(self):
        clips = {"clips": {"a/en": clip("a", "en")}, "schedule": []}
        now = dt.datetime(2026, 10, 15, 2, tzinfo=dt.timezone.utc)
        section = P.build_section(clips, [], {}, now)
        self.assertIn("| Facebook | 未設定 | — | — |", section)
        self.assertIn("| Instagram 圖文輪播 | 未設定 | — | — |", section)
        self.assertIn("| Bluesky | 自動（threads-autopilot，媒體每天 2→5 則爬坡） | — | — |", section)
        self.assertIn("| Mastodon | 停權冷卻（鎖定） | — | — |", section)
        self.assertIn("| YouTube Shorts | 自動（Mac，每天 2→4 支爬坡） |", section)
        posts = [{"channel": "bluesky", "clip": "a/en", "link": "https://bsky.app/p/1", "posted_at": "2026-10-15T01:50:00Z"}]
        section = P.build_section(clips, posts, {}, now)
        self.assertIn("| Bluesky | 自動 | 1 | — |", section)
        self.assertIn("[Bs](https://bsky.app/p/1)", section)
        cards = [{"channel": "pinterest", "clip": "utility/word/aim990/w1/en", "link": "https://www.pinterest.com/pin/1/",
                  "posted_at": "2026-10-15T15:50:00Z"}]
        self.assertIn("| Pinterest | 自動 | 1 | — |", P.build_section(clips, cards, {}, now))

    def test_record_post_keeps_the_media_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(P, "POSTS", Path(tmp) / "posts.json"), mock.patch.object(P, "update"):
                P.record_post("plurk", "a/zh-Hant", "https://www.plurk.com/p/zz", media_id=1295)
                log = json.loads((Path(tmp) / "posts.json").read_text())
        self.assertEqual(log["posts"][0]["channel"], "plurk")
        self.assertEqual(log["posts"][0]["id"], "1295")


def pair_clip(locale="ko", hook="작업 중에 또 AI 한도 초과?"):
    """A UsageNow clip (key claudeusagemini) in a review_links.json pair locale."""
    return dict(search_clip("claudeusagemini", locale, hook),
                store_url="https://apps.apple.com/us/app/id6818607603?pt=118326163&ct=h7_claudeusagemini&mt=8")


REVIEW_URL = "https://apps.apple.com/app/id6818607603?action=write-review"


class ReviewLinkFeedTest(unittest.TestCase):
    """The existing-user review link (review_links.json pairs only) reaches the feed and the link lines."""

    def test_pair_clip_items_carry_the_review_and_others_do_not(self):
        it = S.clip_item("claudeusagemini/ko", pair_clip(), "youtube", DAY)
        self.assertEqual(it["review"]["url"], REVIEW_URL)
        self.assertEqual(it["review"]["label"], S.review_links.config()["labels"]["ko"])
        self.assertNotIn("review", S.clip_item("claudeusagemini/ja", pair_clip("ja", "また上限？"), "youtube", DAY))
        self.assertNotIn("review", S.clip_item("a/ko", clip("a", "ko"), "youtube", DAY))
        self.assertEqual(S.public(it, "youtube")["review"], it["review"])  # feed.json keeps it

    def test_feed_export_keeps_the_review_for_bluesky_and_youtube(self):
        data = {"clips": {"claudeusagemini/en": pair_clip("en", "Hit your AI limit mid-task again?"),
                          "a/en": clip("a", "en")},
                "schedule": [{"date": DAY.isoformat(), "slot": 1, "channel": "instagram",
                              "clip": "claudeusagemini/en"}]}
        feed = S.export(DAY, check=False, data=data, perf={})
        day_items = {i["key"]: i for i in feed["items"]["bluesky"]}
        self.assertEqual(day_items["claudeusagemini/en"]["review"]["url"], REVIEW_URL)
        pool = {i["key"]: i for i in feed["pool"]["youtube"]}
        self.assertEqual(pool["claudeusagemini/en"]["review"]["url"], REVIEW_URL)
        self.assertIn(REVIEW_URL, pool["claudeusagemini/en"]["youtube"]["description"])
        self.assertNotIn("review", pool["a/en"])
        self.assertNotIn("write-review", pool["a/en"]["youtube"]["description"])

    def test_youtube_description_puts_it_after_the_store_links(self):
        it = S.clip_item("claudeusagemini/ko", pair_clip(), "youtube", DAY)
        _, desc, _ = S.yt_meta(it)
        lines = desc.splitlines()
        store = next(i for i, line in enumerate(lines) if line.startswith("App Store: "))
        self.assertEqual(lines[store + 1:store + 3], [it["review"]["label"], REVIEW_URL])
        self.assertNotIn("ct=", lines[store + 2])

    def test_link_lines_naver_and_plurk_carry_it(self):
        it = S.clip_item("claudeusagemini/ko", pair_clip(), "naver", DAY)
        self.assertEqual(S.link_lines(it)[-2:], [it["review"]["label"], REVIEW_URL])
        seen = []

        def rpc(url, data, headers):
            params, method = xmlrpc.client.loads(data)
            seen.append((method, params))
            return (200, {}, xmlrpc.client.dumps(("2234",), methodresponse=True).encode())
        with mock.patch.dict(os.environ, {"NAVER_ID": "lumi", "NAVER_BLOG_API_PASSWORD": "pw"}, clear=True), \
                mock.patch.object(S, "http", Fake([("POST", "api.blog.naver.com/xmlrpc", rpc)])):
            S.post_naver(it)
        self.assertIn(f'<a href="{REVIEW_URL}" rel="nofollow">', seen[0][1][3]["description"])
        tw = dict(pair_clip("zh-Hant", "落落長的筆記 變成一頁簡報"),
                  store_url="https://apps.apple.com/us/app/id6798814385?pt=118326163&ct=h7_onepageppt&mt=8")
        pk = S.clip_item("onepageppt/zh-Hant", tw, "plurk", DAY)
        # OnePage PPT is on Android: both download links come first, the rating link goes if 360 cannot hold it.
        fake = Fake([("POST", "/Timeline/plurkAdd", {"plurk_id": 1295})])
        with mock.patch.dict(os.environ, {k: "v" for k in S.SECRETS["plurk"]}, clear=True), \
                mock.patch.object(S, "http", fake):
            S.post_plurk(pk)
        fields = dict(urllib.parse.parse_qsl(fake.find("plurkAdd")[0]["data"].decode()))
        self.assertIn("6798814385", DL.store_ids_in(fields["content"]))
        self.assertIn("com.alice51849.OnePagePPT", DL.play_packages_in(fields["content"]))
        self.assertLessEqual(len(fields["content"]), 360)
        # An app that is not on Android has room for the rating link as well (the original intent of this check).
        fake = Fake([("POST", "/Timeline/plurkAdd", {"plurk_id": 1295})])
        with mock.patch.dict(os.environ, {k: "v" for k in S.SECRETS["plurk"]}, clear=True), \
                mock.patch.object(S, "http", fake), mock.patch.object(S, "play_store_url", return_value=None):
            S.post_plurk(dict(pk, play=None))
        fields = dict(urllib.parse.parse_qsl(fake.find("plurkAdd")[0]["data"].decode()))
        self.assertIn("https://apps.apple.com/app/id6798814385?action=write-review", fields["content"])
        self.assertIn("6798814385", DL.store_ids_in(fields["content"]))
        self.assertLessEqual(len(fields["content"]), 360)


# ------------------------------------------------------------------ the download link in every post
# Owner rule (2026-10-17): every promo text carries the app's direct App Store link, plus Google Play when the
# app is on Android. Each test checks the payload the platform really receives (http mocked).

MOCHI_ID, MOCHI_PKG = "6785004775", "com.alice51849.MochiTodo"  # Mochi is on Android (android_live_snapshot.json)
MOCHI_STORE = f"https://apps.apple.com/us/app/id{MOCHI_ID}?pt=118326163&ct=h7_mochi_en&mt=8"
RATING_ONLY = f"https://apps.apple.com/app/id{MOCHI_ID}?action=write-review"


def mochi_item(channel, locale="en", **over):
    """An Android app's clip item (Mochi): has an App Store and a Google Play link."""
    return dict(S.clip_item(f"mochi/{locale}", dict(clip("mochi", locale), store_url=MOCHI_STORE), channel, DAY), **over)


def mochi_card(locale="en", **over):
    """An Android app's image card (Mochi)."""
    store = f"https://apps.apple.com/us/app/id{MOCHI_ID}?pt=118326163&ct=ut_mochi_tb&mt=8"
    return {**item("card", locale), "store": store, "play": S.play_store_url(MOCHI_ID, "ut_mochi_tb"), "name": "Mochi", **over}


def ios_item(channel, locale="en", **over):
    """An iOS-only app's clip item (fixture app id1): an App Store link and no Google Play."""
    return dict(S.clip_item(f"a/{locale}", clip("a", locale), channel, DAY), **over)


class LinkAsserts:
    def assertAndroidLinks(self, text, store_id=MOCHI_ID, pkg=MOCHI_PKG):
        self.assertIn(store_id, DL.store_ids_in(text), f"no App Store link in {text!r}")
        self.assertIn(pkg, DL.play_packages_in(text), f"no Google Play link in {text!r}")

    def assertIosLinks(self, text, store_id="1"):
        self.assertIn(store_id, DL.store_ids_in(text))
        self.assertEqual(DL.play_packages_in(text), set())


def sent_form(fake, part):
    return dict(urllib.parse.parse_qsl(fake.find(part)[0]["data"].decode()))


class SentPayloadLinksTest(LinkAsserts, unittest.TestCase):
    """The payload each poster really sends carries the download links (Android app: both)."""

    def test_facebook_first_comment_carries_both_links_and_so_does_the_link_post(self):
        def run(comment_answer):
            fake = Fake([("POST", "rupload.facebook.com", {"success": True}),
                         ("POST", "/123/video_reels", lambda u, d, h: {"video_id": "v1"} if b"start" in d else {"success": True}),
                         ("POST", "/v1/comments", comment_answer), ("POST", "/123/feed", {"id": "f1"})])
            with mock.patch.dict(os.environ, {"FB_PAGE_ID": "123", "FB_PAGE_TOKEN": "pt"}, clear=True), \
                    mock.patch.object(S, "http", fake), mock.patch("sys.stdout", new_callable=io.StringIO):
                S.post_facebook(mochi_item("facebook"))
            return fake
        fake = run({"id": "c1"})
        self.assertAndroidLinks(sent_form(fake, "/v1/comments")["message"])
        finish = [c for c in fake.calls if c["data"] and b"video_state=PUBLISHED" in c["data"]]
        self.assertAndroidLinks(urllib.parse.parse_qs(finish[0]["data"].decode())["description"][0])  # the Reel's own text too
        self.assertEqual(fake.find("/123/feed"), [])
        fake = run(RuntimeError("HTTP 400 comments closed"))  # commenting refused: the link post has both links too
        feed = sent_form(fake, "/123/feed")
        self.assertAndroidLinks(feed["message"])
        self.assertIn(MOCHI_ID, DL.store_ids_in(feed["link"]))
        fake = Fake([("POST", "rupload.facebook.com", {"success": True}),
                     ("POST", "/123/video_reels", lambda u, d, h: {"video_id": "v1"} if b"start" in d else {"success": True}),
                     ("POST", "/v1/comments", {"id": "c1"})])
        with mock.patch.dict(os.environ, {"FB_PAGE_ID": "123", "FB_PAGE_TOKEN": "pt"}, clear=True), mock.patch.object(S, "http", fake):
            S.post_facebook(ios_item("facebook"))
        self.assertIosLinks(sent_form(fake, "/v1/comments")["message"])

    def test_bluesky_link_facets_point_at_both_stores_within_300_characters(self):
        session = ("POST", "createSession", {"accessJwt": "jwt", "did": "did:plc:me", "handle": "h.bsky.social"})
        for caption in (None, "寫到一半的待辦清單 " * 40):  # a caption far over 300 characters keeps its links
            fake = Fake([session, ("GET", "getServiceAuth", RuntimeError("HTTP 403 no video quota")),
                         ("POST", "createRecord", {"uri": "at://did:plc:me/app.bsky.feed.post/3x"})])
            it = mochi_item("bluesky") if caption is None else mochi_item("bluesky", caption=caption)
            with mock.patch.dict(os.environ, {"BSKY_HANDLE": "h", "BSKY_APP_PASSWORD": "p"}, clear=True), \
                    mock.patch.object(S, "http", fake), mock.patch.object(S, "fetch_bytes", return_value=b"mp4"), \
                    mock.patch("sys.stdout", new_callable=io.StringIO):
                S.post_bluesky(it)
            record = json.loads(fake.find("createRecord")[0]["data"])["record"]
            uris = "\n".join(f["features"][0]["uri"] for f in record["facets"] if f["features"][0]["$type"].endswith("#link"))
            self.assertAndroidLinks(uris)
            self.assertLessEqual(len(record["text"]), 300)
            raw = record["text"].encode()
            for f in record["facets"]:
                if f["features"][0]["$type"].endswith("#link"):
                    self.assertIn(raw[f["index"]["byteStart"]:f["index"]["byteEnd"]].decode(), ("App Store", "Google Play"))

    def test_youtube_description_carries_both_links(self):
        fake = Fake([("POST", "oauth2.googleapis.com/token", {"access_token": "at"}),
                     ("POST", "upload/youtube/v3/videos", (200, {"location": "https://upload.example/s1"}, b"")),
                     ("PUT", "upload.example/s1", {"id": "yt1"})])
        env = {"YT_CLIENT_ID": "c", "YT_CLIENT_SECRET": "s", "YT_REFRESH_TOKEN": "r"}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(S, "http", fake), \
                mock.patch.object(S, "fetch_bytes", return_value=b"mp4"), mock.patch("sys.stdout", new_callable=io.StringIO):
            S.post_youtube(mochi_item("youtube"), {"clips": {}})
        body = json.loads(fake.find("uploadType=resumable")[0]["data"])
        self.assertAndroidLinks(body["snippet"]["description"])

    def test_pinterest_description_holds_google_play_and_the_link_field_the_app_store(self):
        for caption, kind in (("Plan your day", "clip"), ("Plan your day\n" * 200, "clip"), ("Plan your day", "card")):
            fake = Fake([("GET", "/boards", {"items": [{"id": "b1", "name": "Lumi Apps"}]}),
                         ("POST", "/v5/media", {"media_id": "m1", "upload_url": "https://s3.example/up", "upload_parameters": {}}),
                         ("POST", "s3.example", {}), ("GET", "/media/m1", {"status": "succeeded"}), ("POST", "/pins", {"id": "p1"})])
            it = mochi_item("pinterest", caption=caption) if kind == "clip" else mochi_card(caption=caption)
            with mock.patch.dict(os.environ, {"PINTEREST_TOKEN": "t"}, clear=True), mock.patch.object(S, "http", fake), \
                    mock.patch.object(S, "fetch_bytes", return_value=b"mp4"):
                S.post_pinterest(it)
            pin = json.loads(fake.find("/pins")[0]["data"])
            self.assertAndroidLinks(pin["description"])
            self.assertLessEqual(len(pin["description"]), 800)
            self.assertEqual(pin["link"], it["store"])  # the link field holds one URL: the App Store page
            self.assertEqual(len(DL.store_ids_in(pin["link"])) + len(DL.play_packages_in(pin["link"])), 1)

    def test_pinterest_without_android_has_the_app_store_link_only(self):
        fake = Fake([("GET", "/boards", {"items": [{"id": "b1", "name": "Lumi Apps"}]}), ("POST", "/pins", {"id": "p1"})])
        with mock.patch.dict(os.environ, {"PINTEREST_TOKEN": "t"}, clear=True), mock.patch.object(S, "http", fake), \
                without_android("6807079789"):
            S.post_pinterest(item("card"))
        self.assertIosLinks(json.loads(fake.find("/pins")[0]["data"])["description"], "6807079789")

    def test_item_without_a_play_link_gets_it_from_the_android_snapshot(self):
        fake = Fake([("GET", "/boards", {"items": [{"id": "b1", "name": "Lumi Apps"}]}), ("POST", "/pins", {"id": "p1"})])
        with mock.patch.dict(os.environ, {"PINTEREST_TOKEN": "t"}, clear=True), mock.patch.object(S, "http", fake):
            S.post_pinterest(mochi_card(play=None))
        self.assertAndroidLinks(json.loads(fake.find("/pins")[0]["data"])["description"])

    def test_an_unreadable_android_snapshot_refuses_the_item_instead_of_dropping_its_play_link(self):
        import social_post_common as common
        card = mochi_card(play=None)
        with mock.patch.object(common, "android_apps", return_value={}):
            with self.assertRaises(DL.MissingDownloadLink):
                S.play_of(card)
            with self.assertRaises(DL.MissingDownloadLink):
                S.link_lines(card)
            problems = S.qa_problems(card, "bluesky")   # a refusal of this item, not a crash of the whole run
            self.assertTrue(problems and "Google Play" in problems[0], problems)
        self.assertIn(MOCHI_PKG, DL.play_packages_in(S.play_of(card)))   # the snapshot is back: fine again

    def test_an_android_app_whose_play_link_cannot_be_built_is_refused_not_sent_iphone_only(self):
        bad = mochi_card(play=None)
        bad["store"] = MOCHI_STORE.replace("ct=h7_mochi_en", "ct=bad%20token")
        with self.assertRaises(DL.MissingDownloadLink):
            S.play_of(bad)
        self.assertTrue(S.qa_problems(bad, "bluesky"))
        with without_android("6807079789"):
            self.assertIsNone(S.play_of(item("card")))   # an app that is not on Android still has no Play link

    def test_tumblr_link_block_is_the_app_store_and_the_google_play_text_links_it(self):
        for it in (mochi_item("tumblr"), mochi_card()):
            fake = Fake([("POST", "/blog/lumiapps.tumblr.com/posts", {"response": {"id": 77, "id_string": "77"}})])
            env = {k: "v" for k in S.SECRETS["tumblr"]}
            env["TUMBLR_BLOG"] = "lumiapps"
            with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(S, "http", fake), \
                    mock.patch.object(S, "fetch_bytes", return_value=b"bytes"):
                S.post_tumblr(it)
            data = fake.calls[0]["data"]
            payload = json.loads(data.split(b"application/json\r\n\r\n")[1].split(b"\r\n--")[0])
            link = next(b for b in payload["content"] if b["type"] == "link")
            self.assertIn(MOCHI_ID, DL.store_ids_in(link["url"]))
            play = payload["content"][-1]
            self.assertEqual(play["text"], "Google Play")
            self.assertIn(MOCHI_PKG, DL.play_packages_in(play["formatting"][0]["url"]))
            self.assertAndroidLinks(S.npf_text(payload["content"]))

    def test_naver_html_has_both_download_anchors(self):
        seen = []

        def rpc(url, data, headers):
            params, method = xmlrpc.client.loads(data)
            seen.append((method, params))
            return (200, {}, xmlrpc.client.dumps(("2234",), methodresponse=True).encode())
        with mock.patch.dict(os.environ, {"NAVER_ID": "lumi", "NAVER_BLOG_API_PASSWORD": "pw"}, clear=True), \
                mock.patch.object(S, "http", Fake([("POST", "api.blog.naver.com/xmlrpc", rpc)])):
            S.post_naver(mochi_item("naver", "ko"))
        self.assertAndroidLinks(seen[0][1][3]["description"])

    def test_plurk_keeps_both_links_whatever_the_caption_length(self):
        for caption in ("倒數" * 300, "短短的一句話", "倒數\n" * 40 + "#標籤一 #標籤二 #標籤三"):
            fake = Fake([("POST", "/Timeline/plurkAdd", {"plurk_id": 1295})])
            it = mochi_item("plurk", "zh-Hant", caption=caption)
            with mock.patch.dict(os.environ, {k: "v" for k in S.SECRETS["plurk"]}, clear=True), mock.patch.object(S, "http", fake):
                S.post_plurk(it)
            content = sent_form(fake, "plurkAdd")["content"]
            self.assertAndroidLinks(content)
            self.assertLessEqual(len(content), 360)
            self.assertIn(it["video"], content)

    def test_plurk_card_content_after_the_picture_upload_keeps_both_links(self):
        fake = Fake([("POST", "/Timeline/uploadPicture", {"full": "https://images.plurk.com/x.jpg"}),
                     ("POST", "/Timeline/plurkAdd", {"plurk_id": 1295})])
        with mock.patch.dict(os.environ, {k: "v" for k in S.SECRETS["plurk"]}, clear=True), mock.patch.object(S, "http", fake), \
                mock.patch.object(S, "fetch_bytes", return_value=b"jpg"):
            S.post_plurk(mochi_card(caption="倒數" * 300, locale="zh-Hant"))
        content = sent_form(fake, "plurkAdd")["content"]
        self.assertAndroidLinks(content)
        self.assertLessEqual(len(content), 360)
        self.assertIn("https://images.plurk.com/x.jpg", content)

    def test_dailymotion_description_carries_both_links_even_for_a_huge_caption(self):
        for caption in (None, "x " * 3000):
            fake = Fake([("POST", "/oauth/token", {"access_token": "dm"}), ("POST", "/me/videos", {"id": "x9"})])
            it = mochi_item("dailymotion") if caption is None else mochi_item("dailymotion", caption=caption)
            with mock.patch.dict(os.environ, {k: "v" for k in S.SECRETS["dailymotion"]}, clear=True), mock.patch.object(S, "http", fake):
                S.post_dailymotion(it)
            desc = sent_form(fake, "/me/videos")["description"]
            self.assertAndroidLinks(desc)
            self.assertLessEqual(len(desc), 3000)

    def test_mastodon_text_for_the_feed_consumer_counts_links_the_mastodon_way(self):
        for caption in (None, "Plan your day\nTap to check it off\n" * 40 + "#Todo #List"):
            it = mochi_item("mastodon") if caption is None else mochi_item("mastodon", caption=caption)
            text = S.final_text(it, "mastodon")
            self.assertAndroidLinks(text)
            self.assertLessEqual(S.fedi_len(text), 500)
            self.assertEqual(S.qa_problems(it, "mastodon", online=False), [])


class FinalTextTest(LinkAsserts, unittest.TestCase):
    """final_text() is the whole text a platform receives; the QA gate checks exactly that."""

    def test_every_platform_final_text_carries_the_links_and_passes_qa(self):
        for channel in S.RENDER:
            loc = {"naver": "ko", "plurk": "zh-Hant"}.get(channel, "en")  # the locale each platform takes
            with self.subTest(channel=channel, app="mochi"):
                it = mochi_item(channel, loc)
                self.assertAndroidLinks(S.final_text(it, channel))
                self.assertEqual(S.qa_problems(it, channel, online=False), [])
            with self.subTest(channel=channel, app="ios only"):
                it = ios_item(channel, loc)
                self.assertIosLinks(S.final_text(it, channel))
                self.assertEqual(S.qa_problems(it, channel, online=False), [])

    def test_final_text_starts_with_the_caption_and_includes_the_link_fields(self):
        fb = S.final_text(mochi_item("facebook"), "facebook")  # description + first comment
        self.assertTrue(fb.startswith(mochi_item("facebook")["caption"]))
        self.assertIn("Google Play: https://play.google.com", fb)
        tb = S.final_text(mochi_item("tumblr"), "tumblr")  # the link block and the linked "Google Play" text
        self.assertTrue(tb.startswith(mochi_item("tumblr")["caption"]))
        self.assertIn("https://play.google.com", tb)
        bs = S.final_text(mochi_item("bluesky"), "bluesky")  # the link facets' URIs
        self.assertIn("https://apps.apple.com", bs.split("\n")[-2])
        pin = S.final_text(mochi_item("pinterest"), "pinterest")  # description + the pin's link field
        self.assertTrue(pin.endswith(mochi_item("pinterest")["store"]))

    def test_the_rating_link_is_no_download_link(self):
        review = S.clip_item("claudeusagemini/ko", pair_clip(), "dailymotion", DAY)  # a rating-link pair, not on Android
        self.assertTrue(review["review"])
        rating_only = f"{review['caption']}\n{REVIEW_URL}"  # the same app id, but only the rating link
        self.assertFalse(DL.has_app_store_link(rating_only, review["store"]))  # the shared check ignores a rating link too
        self.assertTrue(any("App Store" in p for p in S.link_problems(rating_only, review, "x")))
        text = S.final_text(review, "dailymotion")
        self.assertEqual(S.link_problems(text, review, "x"), [])
        self.assertIn("write-review", text)  # the rating link follows the download links
        self.assertLess(text.index("apps.apple.com/us/"), text.index("write-review"))

    def test_the_gate_refuses_a_text_with_no_usable_link(self):
        for channel in S.RENDER:
            for store in ("", "https://example.com/app", RATING_ONLY):
                with self.subTest(channel=channel, store=store):
                    loc = {"naver": "ko", "plurk": "zh-Hant"}.get(channel, "en")
                    problems = S.qa_problems(mochi_item(channel, loc, store=store), channel, online=False)
                    self.assertTrue(problems, "a post without its download link must not pass QA")
                    self.assertTrue(any("App Store" in p for p in problems))


class MissingLinkRefusedTest(unittest.TestCase):
    """An app with no usable App Store link is refused at the send call: ::error::, no http, no download."""

    POSTERS = {"facebook": "post_facebook", "bluesky": "post_bluesky", "youtube": "post_youtube", "pinterest": "post_pinterest",
               "tumblr": "post_tumblr", "naver": "post_naver", "plurk": "post_plurk", "dailymotion": "post_dailymotion"}

    CARD_CHANNELS = ("bluesky", "pinterest", "tumblr", "naver", "plurk")  # the platforms that take cards (PLAN)

    def test_every_poster_refuses_before_any_request(self):
        for channel, name in self.POSTERS.items():
            loc = {"naver": "ko", "plurk": "zh-Hant"}.get(channel, "en")
            items = {"clip": mochi_item(channel, loc)}
            if channel in self.CARD_CHANNELS:
                items["card"] = mochi_card(loc)
            for kind, base in items.items():
                for store in ("", "https://example.com/app", RATING_ONLY):
                    with self.subTest(channel=channel, kind=kind, store=store):
                        it = dict(base, store=store)
                        fake = Fake([])
                        fetch = mock.Mock(return_value=b"bytes")
                        with mock.patch.dict(os.environ, ENV_ALL, clear=True), mock.patch.object(S, "http", fake), \
                                mock.patch.object(S, "fetch_bytes", fetch), mock.patch("sys.stdout", new_callable=io.StringIO) as out:
                            res = getattr(S, name)(it, {"clips": {}}) if channel == "youtube" else getattr(S, name)(it)
                        self.assertIsNone(res)
                        self.assertEqual(fake.calls, [], "nothing may be sent")
                        fetch.assert_not_called()
                        self.assertIn("::error::", out.getvalue())
                        self.assertIn("download link", out.getvalue())

    def test_run_refuses_the_item_and_never_calls_the_poster(self):
        broken = {"clips": {"a/en": dict(clip("a", "en"), store_url="")},
                  "schedule": [{"date": "2026-10-15", "slot": 1, "channel": "instagram", "clip": "a/en"}]}
        posted = mock.Mock(return_value={"id": "9", "link": "l"})
        with mock.patch.dict(os.environ, ENV_ALL, clear=True), mock.patch.dict(S.POSTERS, {"dailymotion": posted}), \
                mock.patch.object(S, "load_posts", return_value=[]), mock.patch.object(P, "record_post") as rec, \
                mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            S.run(("dailymotion",), DAY, 1, data=broken)
        posted.assert_not_called()
        rec.assert_not_called()
        self.assertIn("QA refused", out.getvalue())

    def test_run_sends_what_the_gate_approved(self):
        posted = mock.Mock(return_value={"id": "9", "link": "l"})
        with mock.patch.dict(os.environ, ENV_ALL, clear=True), mock.patch.dict(S.POSTERS, {"dailymotion": posted}), \
                mock.patch.object(S, "load_posts", return_value=[]), mock.patch.object(P, "record_post"), \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            S.run(("dailymotion",), DAY, 1, data=DATA)
        posted.assert_called_once()

    def test_dry_run_shows_the_text_with_its_links(self):
        with mock.patch.dict(os.environ, ENV_ALL, clear=True), mock.patch.object(S, "http") as h, \
                mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            S.run(("dailymotion",), DAY, 1, dry_run=True, data=DATA)
        h.assert_not_called()
        self.assertIn("Get it on the App Store: https://apps.apple.com/us/app/id1", out.getvalue())

    def test_youtube_localization_without_a_link_is_left_out_but_the_post_goes(self):
        data = {"clips": {"a/en": clip("a", "en"), "a/ko": clip("a", "ko")}}
        data["clips"]["a/ko"]["store_url"] = "https://example.com/not-a-store"
        it = S.clip_item("a/en", data["clips"]["a/en"], "youtube")
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            body = S.yt_body(it, data)
        self.assertNotIn("localizations", body)
        self.assertIn("download link guard refused", out.getvalue())
        self.assertIn("apps.apple.com", body["snippet"]["description"])


class FeedLinksTest(LinkAsserts, unittest.TestCase):
    """export(): the feed is not emptied by the link gate, and every item has store, play and button."""

    def feed(self, data=None):
        data = data or {"clips": DATA["clips"], "schedule": DATA["schedule"]}
        with mock.patch.object(S, "exists", return_value=True), mock.patch("sys.stdout", new_callable=io.StringIO):
            return S.export(DAY, check=False, data=data, perf={})

    def test_feed_keeps_its_items_and_each_has_store_play_and_button(self):
        feed = self.feed()
        for ch in S.EXPORT_CHANNELS:
            self.assertTrue(feed["items"][ch], f"{ch} feed must not be emptied by the link gate")
            for it in feed["items"][ch] + (feed["pool"].get(ch) or []):
                with self.subTest(channel=ch, key=it["key"]):
                    self.assertTrue(DL.app_store_id(it["store"]))
                    self.assertIn("play", it)
                    self.assertTrue(it["button"])
                    self.assertIn("caption", it)  # the existing fields stay
        self.assertEqual([i["key"] for i in feed["items"]["bluesky"] if i["kind"] == "clip"], ["a/en", "a/zh-Hant", "b/en"])

    def test_android_apps_in_the_feed_carry_their_google_play_link(self):
        data = {"clips": {"mochi/en": dict(clip("mochi", "en"), store_url=MOCHI_STORE),
                          "a/en": clip("a", "en")},
                "schedule": [{"date": DAY.isoformat(), "slot": 1, "channel": "instagram", "clip": "mochi/en"},
                             {"date": DAY.isoformat(), "slot": 15, "channel": "instagram", "clip": "a/en"}]}
        feed = self.feed(data)
        for ch in S.EXPORT_CHANNELS:
            by_key = {i["key"]: i for i in feed["items"][ch]}
            self.assertIn(MOCHI_PKG, DL.play_packages_in(by_key["mochi/en"]["play"]))
            self.assertIsNone(by_key["a/en"]["play"])
            self.assertIn(MOCHI_ID, DL.store_ids_in(by_key["mochi/en"]["store"]))
            self.assertTrue(by_key["mochi/en"]["button"])

    def test_cards_in_the_feed_have_the_three_fields_too(self):
        with mock.patch.object(S, "exists", return_value=True), mock.patch("sys.stdout", new_callable=io.StringIO):
            feed = S.export(dt.date(2026, 11, 1), check=False, data={"clips": {}, "schedule": []}, perf={})
        cards = [i for i in feed["items"]["bluesky"] if i["kind"] == "card"]
        self.assertTrue(cards)
        for c in cards:
            self.assertTrue(c["store"] and c["button"])
            self.assertIn("play", c)

    def test_a_clip_without_a_store_link_is_dropped_alone(self):
        bad = dict(DATA["clips"]["b/en"], store_url="https://example.com/not-a-store")
        data = {"clips": dict(DATA["clips"], **{"b/en": bad}), "schedule": DATA["schedule"]}
        with mock.patch.object(S, "exists", return_value=True), mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            feed = S.export(DAY, check=False, data=data, perf={})
        for ch in S.EXPORT_CHANNELS:
            keys = [i["key"] for i in feed["items"][ch]]
            self.assertNotIn("b/en", keys)
            self.assertIn("a/en", keys)
        self.assertNotIn("b/en", [i["key"] for i in feed["pool"]["bluesky"]])
        self.assertIn("a/en", [i["key"] for i in feed["pool"]["youtube"]])
        self.assertIn("download link", out.getvalue())
        json.dumps(feed)


class VideoComplianceFeedTest(unittest.TestCase):
    """A clip without its real-recording record never reaches the pool, the backlog or the feed."""

    def test_pool_and_backlog_drop_a_clip_without_the_record(self):
        bad = {k: v for k, v in clip("b", "en").items() if k != "compliance"}
        data = {"clips": {"a/en": clip("a", "en"), "b/en": bad},
                "schedule": [{"date": DAY.isoformat(), "slot": 1, "channel": "instagram", "clip": "b/en"},
                             {"date": DAY.isoformat(), "slot": 1, "channel": "telegram", "clip": "a/en"}]}
        with mock.patch.object(S, "outgoing", lambda item, channel: True):
            keys = [i["key"] for i in S.pool(data, "bluesky", DAY)]
        self.assertEqual(keys, ["a/en"])
        self.assertEqual([i["key"] for i in S.todays_clips(data, [], "facebook", DAY, 1)], ["a/en"])

    def test_feed_items_carry_the_record_for_the_other_posters(self):
        item = S.clip_item("a/en", clip("a", "en"), "bluesky", DAY)
        self.assertEqual(S.public(item, "bluesky")["compliance"], COMPLIANT)


if __name__ == "__main__":
    unittest.main()
