#!/usr/bin/env python3
"""Tests for social_extra.py (mocked HTTP, no network)."""
import datetime as dt
import io
import json
import os
import sys
import tempfile
import unittest
import xmlrpc.client
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("POST_QA_OFFLINE", "1")  # the pre-post QA gate makes no network calls in tests

import clip_progress as P  # noqa: E402
import social_extra as S  # noqa: E402

S.PAUSE = 0
S.STAGGER = 0
DAY = dt.date(2026, 10, 15)


def clip(app, locale):
    return {"app": app, "locale": locale, "url": f"https://files.catbox.moe/{app}_{locale}.mp4",
            "store_url": f"https://apps.apple.com/us/app/id1?pt=118326163&ct=h7_{app}_{locale}&mt=8",
            "hook": f"{app} {HOOK.get(locale, 'hook')} {locale}", "name": f"{app} name", "search": app,
            "tags": ["#a", "#b", "#c"]}


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
        self.assertIn("ct=h7_a_zh-Hant_pk", it["store"])
        self.assertIn("a 鉤子 zh-Hant", it["caption"])

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
        self.assertEqual(set(feed["pool"]), {"bluesky", "youtube"})
        self.assertEqual([i["key"] for i in feed["pool"]["youtube"]], ["b/en", "b/ja", "a/en"])  # c has no video
        top = feed["pool"]["youtube"][0]
        self.assertEqual(top["boost_rank"], 1)
        self.assertEqual(top["youtube"]["title"], "Hit your AI limit mid-task again? | UsageNow #Shorts")  # problem first
        self.assertEqual(top["variant"], "a")
        self.assertLessEqual(len(top["youtube"]["title"]), 100)
        self.assertIn("ct=h7_b_en_yt", top["store"])
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
        self.assertEqual(set(feed["items"]), {"bluesky", "mastodon", "youtube"})
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
        self.assertIn("| Bluesky | 自動（threads-autopilot，精選每天 ≤5 則） | — | — |", section)
        self.assertIn("| Mastodon | 停權冷卻（鎖定） | — | — |", section)
        self.assertIn("| YouTube Shorts | 自動（Mac，每天 ≤2 支） |", section)
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


if __name__ == "__main__":
    unittest.main()
