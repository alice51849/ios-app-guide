#!/usr/bin/env python3
"""Tests for comment_replies.py, post_performance.py and the 成效排行 table (no network)."""
import datetime as dt
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import clip_progress as P  # noqa: E402
import comment_replies as R  # noqa: E402
import download_links as DL  # noqa: E402
import own_posts as O  # noqa: E402
import post_performance as F  # noqa: E402

NOW = dt.datetime(2026, 10, 14, 12, 0, tzinfo=dt.timezone.utc)
TS = "2026-10-14T10:00:00+0000"
CLIPS = {"clips": {"a/en": {"app": "a", "locale": "en", "hook": "Hit your limit again?", "name": "A App",
                            "store_url": "https://apps.apple.com/us/app/id111?ct=h7_a_en"},
                   "b/ja": {"app": "b", "locale": "ja", "hook": "毎日忘れる？", "name": "B",
                            "store_url": "https://apps.apple.com/us/app/id222?ct=h7_b_ja"}}}
CATALOG = O.Catalog(CLIPS, [{"channel": "threads", "clip": "b/ja", "id": "T1", "link": "https://threads.net/p/x"}],
                    {"apps": [{"key": "c", "name": "Cee Planner", "app_store_id": "333"}]})


class FakeClient:
    channel = "instagram"

    def __init__(self, media, comments, insights=None, deny=None):
        self.media_rows, self.comment_rows, self.insight_rows = media, comments, insights or {}
        self.deny, self.sent, self.username = deny, [], "lumi"

    def me(self):
        return self

    def media(self, limit=25):
        return self.media_rows

    def comments(self, media_id, limit=50):
        if self.deny == "comments":
            raise O.ApiError(403, 10, "Application does not have permission for this action")
        return self.comment_rows.get(media_id, [])

    def reply(self, comment_id, text):
        self.sent.append((comment_id, text))
        return "r" + comment_id

    def insights(self, media_id):
        if self.deny == "insights":
            raise O.ApiError(400, 10, "(#10) Application does not have permission for this action")
        return self.insight_rows[media_id]


def c(cid, text, user="fan", ts=TS):
    return {"id": cid, "text": text, "user": user, "timestamp": ts, "we_replied": False}


def state():
    return R.load_state(Path("/nonexistent/state.json"))


class Language(unittest.TestCase):
    def test_scripts(self):
        cases = {"好用耶": "zh-Hant", "これ無料？": "ja", "무료인가요": "ko", "ราคาเท่าไหร่": "th",
                 "cảm ơn bạn": "vi", "is it free": "en", "¿es gratis?": "other", "🔥🔥": None}
        for text, lang in cases.items():
            self.assertEqual(O.detect_language(text), lang, text)


class Classify(unittest.TestCase):
    def test_intents(self):
        cases = {"Is it free?": "price", "多少錢？": "price", "Android版ありますか": "android",
                 "where can I download it": "download", "支援中文嗎": "language", "How does the widget work?": "howto",
                 "Love this!": "praise", "謝謝分享": "praise", "不錯欸": "praise", "❤️❤️": "praise"}
        for text, intent in cases.items():
            self.assertEqual(R.classify(text)[0], intent, text)

    def test_spam_complaints_and_ambiguous_are_skipped(self):
        for text, why in {"check my page www.x.com": "spam", "DM me for promo": "spam", "加我賺錢": "spam",
                          "it keeps crashing": "complaint", "閃退了": "complaint", "@bob": "ambiguous",
                          "not great": "ambiguous", "ok": "ambiguous"}.items():
            self.assertEqual(R.classify(text), ("skip", why), text)


class Decide(unittest.TestCase):
    post = {"app": "a", "locale": "en", "ios_id": "111"}

    def test_every_reply_carries_the_link_and_the_language_matches(self):
        # Threads: the direct link; Instagram (owner 2026-10-17, a URL cannot be tapped there): no URL, the
        # profile-link line in the commenter's language where the link would be.
        for channel, ct in (("threads", "rp_th"), ("instagram", None)):
            s = state()
            with mock.patch.object(R, "play_store_url", return_value=None), mock.patch.object(R, "is_free", return_value=True):
                price = R.decide(c("1", "is it free?"), self.post, channel, "lumi", s, "M", NOW)
                thanks = R.decide(c("2", "謝謝！好用"), self.post, channel, "lumi", s, "M", NOW)
                android = R.decide(c("3", "android?"), self.post, channel, "lumi", s, "M", NOW)
            if ct:
                app_store = f"https://apps.apple.com/app/id111?pt=118326163&ct={ct}&mt=8"
                self.assertIn(app_store, price["text"])
                ends = ("App Store: " + app_store,) * 2
            else:
                for d in (price, thanks, android):
                    self.assertEqual([], DL.instagram_url_problems(d["text"]), d["text"])
                self.assertIn(DL.instagram_cta_line("en"), price["text"])
                ends = (DL.instagram_cta_line("zh-Hant"), DL.instagram_cta_line("en"))
            self.assertIn(price["text"].splitlines()[0], [t.split("\n")[0] for t in R.T["en"]["price_free"]])
            self.assertEqual(thanks["lang"], "zh-Hant")  # still answered in the commenter's language ...
            self.assertIn(thanks["text"].splitlines()[0], R.T["zh-Hant"]["praise"])
            self.assertTrue(thanks["text"].endswith(ends[0]), channel)  # ... with the link line at the end
            self.assertEqual(android["key"], "android_none")
            self.assertIn(android["text"].splitlines()[0], R.T["en"]["android_none"])
            self.assertTrue(android["text"].endswith(ends[1]), channel)  # iOS-only: the App Store link (Threads)
            self.assertNotIn("play.google.com", android["text"])

    def test_android_live_gets_google_play(self):
        with mock.patch.object(R, "play_store_url", return_value="https://play.google.com/store/apps/details?id=x"):
            d = R.decide(c("1", "Android版は？"), self.post, "threads", "lumi", state(), "M", NOW)
        self.assertEqual((d["lang"], d["key"]), ("ja", "android_live"))
        self.assertIn("Google Play: https://play.google.com", d["text"])

    def test_skips(self):
        s = state()
        s["replied"]["instagram"]["9"] = {"media": "M", "user": "fan2", "at": NOW.isoformat()}
        old = (NOW - dt.timedelta(days=8)).strftime("%Y-%m-%dT%H:%M:%S+0000")
        cases = [(c("1", "love it", user="Lumi"), "own"), (c("9", "love it"), "replied"),
                 (c("8", "thanks!", user="fan2"), "commenter-once"), (c("7", "love it", ts=old), "old"),
                 (c("6", "génial, love it"), "language"), (c("5", "is it free?"), None)]
        for comment, why in cases:
            d = R.decide(comment, None if why is None else self.post, "instagram", "lumi", s, "M", NOW)
            self.assertEqual(d.get("skip"), why or "no-app", comment["text"])

    def test_variants_rotate(self):
        s = state()
        fc = FakeClient([{"id": "M", "timestamp": TS, "caption": "Hit your limit again?"}],
                        {"M": [c(str(i), "love this", user=f"u{i}") for i in range(3)]})
        R.run_platform(fc, CATALOG, s, NOW, sleeper=lambda _: None, log=lambda _: None)
        self.assertEqual(len({t for _, t in fc.sent}), 3)
        self.assertGreaterEqual(len(R.T["en"]["praise"]), 3)
        for lang in R.T.values():
            for key, variants in lang.items():
                self.assertGreaterEqual(len(variants), 3, key)
                self.assertEqual(all("{links}" in v for v in variants), key[:5] in ("price", "downl", "andro")
                                 and key != "android_none", key)


PLAY = "https://play.google.com/store/apps/details?id=com.example.app&referrer=utm_source%3Drp_ig%26utm_campaign%3Dapp"
ENGLISH = {"praise": "Love this!", "price": "How much is it?", "download": "Where can I download it?",
           "android": "Is there an Android version?", "language": "Does it support Spanish?",
           "howto": "How does the widget work?"}
OTHER_LANGS = {"zh-Hant": "好用耶", "ja": "ありがとう", "ko": "감사합니다", "th": "ขอบคุณ", "vi": "cảm ơn bạn"}


class DownloadLinkOnEveryReply(unittest.TestCase):
    """Owner rule 2026-10-17: every Threads reply to a comment on a post that maps to an app carries that app's
    direct download link - the App Store link, plus Google Play when the app is on Android - whatever the
    intent (praise, language and how-to included), and a reply that cannot carry it is not sent. An Instagram
    reply (owner, the same day: a URL cannot be tapped there) carries no URL and says "📲 Download via the link
    in bio" in the reply's language instead; one that breaks that rule is not sent either."""

    def assertInstagramReply(self, text, lang="en"):
        self.assertEqual([], DL.instagram_problems(text, locale=lang, brand=False), text)
        self.assertNotIn("apps.apple.com", text)
        self.assertNotIn("play.google.com", text)

    post = {"app": "a", "locale": "en", "ios_id": "111"}
    MAPPED = object()  # decide(): "use the mapped post" (None means a post we cannot map to an app)

    def setUp(self):
        handle, self.log_path = tempfile.mkstemp(suffix=".jsonl")
        os.close(handle)
        self.addCleanup(os.unlink, self.log_path)
        env = mock.patch.dict(os.environ, {"LINK_GUARD_LOG": self.log_path})
        env.start()
        self.addCleanup(env.stop)
        out = mock.patch("sys.stdout", new_callable=io.StringIO)
        self.out = out.start()
        self.addCleanup(out.stop)

    def decide(self, text, channel="instagram", post=MAPPED, s=None, play=None):
        with mock.patch.object(R, "play_store_url", return_value=play):
            return R.decide(c("1", text), self.post if post is self.MAPPED else post, channel, "lumi",
                            s or state(), "M", NOW)

    def test_all_intents_get_the_app_store_link_and_ios_only_apps_no_play(self):
        for channel, ct in (("instagram", None), ("threads", "rp_th")):
            for intent, text in ENGLISH.items():
                with self.subTest(channel=channel, intent=intent):
                    d = self.decide(text, channel)
                    self.assertEqual(intent, d["intent"])
                    self.assertNotIn("play.google.com", d["text"])
                    if not ct:   # Instagram: the profile-link line instead of the URL
                        self.assertInstagramReply(d["text"])
                        continue
                    self.assertTrue(DL.has_download_link(d["text"], "https://apps.apple.com/app/id111"))
                    self.assertIn(f"ct={ct}", d["text"])
                    self.assertEqual([], DL.link_problems(d["text"], "https://apps.apple.com/app/id111"))

    def test_android_apps_get_google_play_on_every_intent(self):
        for intent, text in ENGLISH.items():
            for channel in ("instagram", "threads"):
                with self.subTest(intent=intent, channel=channel):
                    d = self.decide(text, channel, play=PLAY)
                    if channel == "instagram":   # no URL there, the Android answer still says it is on Android
                        self.assertInstagramReply(d["text"])
                        continue
                    self.assertTrue(DL.has_download_link(d["text"], "https://apps.apple.com/app/id111", PLAY))
                    self.assertIn("Google Play: " + PLAY, d["text"])
        for channel in ("instagram", "threads"):
            self.assertEqual("android_live", self.decide(ENGLISH["android"], channel, play=PLAY)["key"])

    def test_every_template_of_every_language_carries_the_link_within_the_platform_limit(self):
        # Force each rotation slot of each (language, intent) template through decide().
        samples = {"en": ENGLISH, **{lang: {"praise": t} for lang, t in OTHER_LANGS.items()}}
        seen = 0
        for lang, texts in samples.items():
            for intent, text in texts.items():
                for play in (None, PLAY):
                    for channel, limit in (("instagram", 2200), ("threads", 500)):
                        keys = {"android": ("android_live" if play else "android_none",), "price": ("price", "price_free")}
                        for key in keys.get(intent, (intent,)):
                            for variant in range(len(R.T[lang][key])):
                                s = state()
                                s["rotation"] = {f"{lang}/{key}": variant}
                                with mock.patch.object(R, "is_free", return_value=key == "price_free"):
                                    d = self.decide(text, channel, s=s, play=play)
                                with self.subTest(lang=lang, key=key, variant=variant, play=bool(play), channel=channel):
                                    self.assertEqual((lang, key, variant), (d["lang"], d["key"], d["variant"]))
                                    if channel == "instagram":
                                        self.assertInstagramReply(d["text"], lang)
                                    else:
                                        self.assertEqual([], DL.link_problems(d["text"], "https://apps.apple.com/app/id111", play))
                                    self.assertLessEqual(len(d["text"]), limit)
                                    seen += 1
        self.assertGreater(seen, 100)

    def test_posts_that_map_to_no_app_get_no_reply_whatever_the_comment_says(self):
        for intent, text in ENGLISH.items():
            if intent in ("price", "download", "android", "praise", "howto", "language"):
                with self.subTest(intent=intent):
                    self.assertEqual({"skip": "no-app"}, self.decide(text, post={"app": "z", "locale": "en"}))
                    self.assertEqual({"skip": "no-app"}, self.decide(text, post=None))

    def test_a_post_with_no_app_is_reported_once_and_nothing_is_sent(self):
        media = [{"id": "M", "timestamp": TS, "caption": "A parenting thought with no app in it"}]
        comments = {"M": [c("1", "love it"), c("2", "Where can I download it?", user="u2")]}
        fc = FakeClient(media, comments)
        sent = R.run_platform(fc, CATALOG, state(), NOW, sleeper=lambda _: None, log=lambda _: None)
        self.assertEqual([], sent)
        self.assertEqual([], fc.sent)
        self.assertEqual(1, len(self.refusals()))   # one report per post, not one per comment
        self.assertIn("::error::", self.out.getvalue())

    def test_a_post_with_no_app_is_reported_once_across_runs_not_every_two_hours(self):
        media = [{"id": "M", "timestamp": TS, "caption": "A parenting thought with no app in it"}]
        comments = {"M": [c("2", "Where can I download it?", user="u2")]}
        s = state()
        for run in range(3):   # the workflow runs every 2 hours and keeps the state file between runs
            R.run_platform(FakeClient(media, comments), CATALOG, s, NOW, sleeper=lambda _: None, log=lambda _: None)
        self.assertEqual(1, len(self.refusals()))
        self.assertEqual(["M"], list(s["no_app"]["instagram"]))
        # the report survives a state file saved before `git reset` and merged back
        with tempfile.TemporaryDirectory() as d:
            saved, current = Path(d, "saved.json"), Path(d, "current.json")
            R.save_state(s, saved)
            R.save_state(state(), current)
            R.merge_state(saved, current)
            self.assertEqual(["M"], list(json.loads(current.read_text())["no_app"]["instagram"]))
        # a month later the entry is pruned together with the replies it belongs to
        R.prune(s, NOW + R.KEEP_STATE + dt.timedelta(days=1))
        self.assertEqual({}, s["no_app"]["instagram"])
        # a different post is still reported
        media2 = [{"id": "N", "timestamp": TS, "caption": "Another thought without an app"}]
        R.run_platform(FakeClient(media2, {"N": comments["M"]}), CATALOG, s, NOW, sleeper=lambda _: None, log=lambda _: None)
        self.assertEqual(2, len(self.refusals()))

    def test_an_unreadable_android_snapshot_stops_the_platform_with_an_error_not_a_bare_line(self):
        class Boom:
            channel, username = "threads", "lumi"

            def __init__(self, _token):
                pass

        def stop(*_args, **_kwargs):
            raise R.SnapshotMissing("the Android snapshot is empty or unreadable; the Google Play link cannot be decided")

        fresh = state()
        with mock.patch.dict(os.environ, {"THREADS_TOKEN": "t"}), mock.patch.object(R, "ThreadsClient", Boom), \
                mock.patch.object(R, "Catalog", lambda: object()), mock.patch.object(R, "run_platform", stop), \
                mock.patch.object(R, "load_state", lambda *_a: fresh):
            self.assertEqual(0, R.main(["--platform", "threads", "--dry-run"]))   # still never fails the workflow
        self.assertIn("::error::", self.out.getvalue())
        self.assertIn("Google Play link cannot be decided", self.out.getvalue())
        self.assertEqual(1, len(self.refusals()))

    def test_other_skip_rules_and_the_daily_cap_are_untouched(self):
        self.assertEqual({"skip": "spam"}, self.decide("check my page www.x.com"))
        self.assertEqual({"skip": "complaint"}, self.decide("it keeps crashing"))
        self.assertEqual({"skip": "ambiguous"}, self.decide("ok"))
        self.assertEqual({"skip": "language"}, self.decide("génial, love it"))
        self.assertEqual((20, 5), (R.DAILY_CAP, R.RUN_CAP))

    def test_a_reply_that_cannot_carry_the_link_is_refused_loudly_and_never_sent(self):
        media = [{"id": "M", "timestamp": TS, "caption": "Hit your limit again?"}]
        comments = {"M": [c("1", "Where can I download it?"), c("2", "love it", user="u2")]}
        fc = FakeClient(media, comments)
        with mock.patch.object(R, "MAX_REPLY_CHARS", {"instagram": 40, "threads": 40}):  # no room for the links
            sent = R.run_platform(fc, CATALOG, state(), NOW, sleeper=lambda _: None, log=lambda _: None)
        self.assertEqual([], sent)
        self.assertEqual([], fc.sent)
        self.assertIn("::error::", self.out.getvalue())
        self.assertEqual(2, len(self.refusals()))
        self.assertIn("over the 40 limit", self.refusals()[0]["problems"][0])
        # A text that lost its link (Threads), or breaks the Instagram rule, is refused the same way.
        with mock.patch.object(R.DL, "link_problems", return_value=["reply: no direct App Store download link"]):
            self.assertEqual({"skip": "link-guard"}, self.decide(ENGLISH["praise"], "threads"))
        with mock.patch.object(R.IGB, "reply_problems", return_value=["instagram reply: no profile-link line"]):
            self.assertEqual({"skip": "link-guard"}, self.decide(ENGLISH["praise"], "instagram"))
        with mock.patch.dict(R.T["en"], {"praise": ["See https://example.com/x"] * 3}):   # a URL never reaches Instagram
            self.assertEqual({"skip": "link-guard"}, self.decide(ENGLISH["praise"], "instagram"))

    def refusals(self):
        with open(self.log_path, encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def test_run_platform_sends_every_reply_to_a_mapped_post_with_the_link(self):
        media = [{"id": "M", "timestamp": TS, "caption": "Hit your limit again?"},
                 {"id": "N", "timestamp": TS, "caption": "unrelated post"}]
        comments = {"M": [c("1", "love this", user="a"), c("2", "支援中文嗎", user="b"),
                          c("3", "How does the widget work?", user="d"), c("4", "is it free?", user="e")],
                    "N": [c("5", "love this", user="f")]}
        fc = FakeClient(media, comments)
        with mock.patch.object(R, "play_store_url", return_value=None):
            sent = R.run_platform(fc, CATALOG, state(), NOW, sleeper=lambda _: None, log=lambda _: None)
        self.assertEqual(4, len(sent))
        for comment_id, text in fc.sent:  # the four comments under the post that maps to app 111 (Instagram:
            with self.subTest(comment=comment_id):   # the profile-link line, no URL)
                self.assertTrue(DL.has_instagram_cta(text), text)
                self.assertEqual([], DL.instagram_url_problems(text), text)
        # A thank-you under a post we cannot map to an app has no link to give, so it is not sent at all.
        self.assertNotIn("5", [comment_id for comment_id, _text in fc.sent])


class Run(unittest.TestCase):
    def test_caps_dry_run_and_state(self):
        s = state()
        s["replied"]["instagram"] = {f"old{i}": {"media": "X", "user": f"x{i}", "intent": "praise",
                                                 "at": NOW.strftime("%Y-%m-%dT%H:%M:%SZ")} for i in range(18)}
        comments = {"M": [c(str(i), "thank you!", user=f"u{i}") for i in range(6)]}
        media = [{"id": "M", "timestamp": TS, "caption": "Hit your limit again?"}]
        dry = FakeClient(media, comments)
        R.run_platform(dry, CATALOG, s, NOW, dry_run=True, log=lambda _: None)
        self.assertEqual(dry.sent, [])
        live = FakeClient(media, comments)
        sent = R.run_platform(live, CATALOG, s, NOW, sleeper=lambda _: None, log=lambda _: None)
        self.assertEqual(len(sent), 2)  # 18 already today, cap 20
        self.assertEqual(R.replies_today(s, "instagram", NOW), 20)
        self.assertEqual(R.run_platform(FakeClient(media, comments), CATALOG, s, NOW, log=lambda _: None), [])

    def test_a_taken_down_post_gets_no_reply_and_its_comments_are_not_read(self):
        # video_takedown.py marks a non-compliant clip post (deleted, or waiting to be archived on the Mac).
        catalog = O.Catalog(CLIPS, [
            {"channel": "instagram", "clip": "a/en", "id": "GONE", "link": "https://www.instagram.com/reel/G/",
             "taken_down": {"status": "pending_local_archive"}},
            {"channel": "instagram", "clip": "a/en", "id": "LIVE", "link": "https://www.instagram.com/reel/L/"}],
            {"apps": [{"key": "a", "name": "A App", "app_store_id": "111"}]})
        media = [{"id": "GONE", "timestamp": TS, "caption": "Hit your limit again?"},
                 {"id": "LIVE", "timestamp": TS, "caption": "Hit your limit again?"}]
        client = FakeClient(media, {"GONE": [c("g1", "love it!")], "LIVE": [c("l1", "love it!")]})
        read = []
        original = client.comments
        client.comments = lambda media_id, limit=50: read.append(media_id) or original(media_id, limit)
        with mock.patch.object(R, "store_links", return_value=(
                "https://apps.apple.com/app/id111?pt=1&ct=x&mt=8", None)):
            R.run_platform(client, catalog, state(), NOW, sleeper=lambda _: None, log=lambda _: None)
        self.assertEqual(["LIVE"], read)
        self.assertEqual(["l1"], [cid for cid, _ in client.sent])
        self.assertEqual({"status": "pending_local_archive"},
                         catalog.taken_down("instagram", {"id": "GONE"}, ("instagram", "instagram_feed")))
        self.assertIsNone(catalog.taken_down("instagram", {"id": "LIVE"}))

    def test_missing_comment_permission_is_logged_not_raised(self):
        logs = []
        fc = FakeClient([{"id": "M", "timestamp": TS}], {}, deny="comments")
        self.assertEqual(R.run_platform(fc, CATALOG, state(), NOW, log=logs.append), [])
        self.assertTrue(any("permission" in line for line in logs))

    def test_merge_state(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d, "a.json"), Path(d, "b.json")
            sa, sb = state(), state()
            sa["replied"]["threads"]["1"] = {"at": "x"}
            sa["rotation"]["en/praise"] = 3
            sb["replied"]["threads"]["2"] = {"at": "y"}
            R.save_state(sa, a)
            R.save_state(sb, b)
            R.merge_state(a, b)
            merged = json.loads(b.read_text())
        self.assertEqual(set(merged["replied"]["threads"]), {"1", "2"})
        self.assertEqual(merged["rotation"]["en/praise"], 3)


class Performance(unittest.TestCase):
    def test_resolve_clip_image_and_unknown(self):
        self.assertEqual(CATALOG.resolve("threads", {"id": "T1"})["clip"], "b/ja")
        self.assertEqual(CATALOG.resolve("instagram", {"id": "Z", "caption": "Hit your limit again?\nA"})["clip"], "a/en")
        img = CATALOG.resolve("threads", {"id": "Q", "caption": "排行程好累\nCee Planner 幫你"})
        self.assertEqual((img["app"], img["kind"], img["locale"], img["ios_id"]), ("c", "image", "zh-Hant", "333"))
        self.assertIsNone(CATALOG.resolve("threads", {"id": "N", "caption": "hello"}))

    def test_ranking_and_boost(self):
        media = [{"id": "1", "caption": "Hit your limit again?"}, {"id": "T1", "caption": "毎日忘れる？"},
                 {"id": "3", "caption": "Cee Planner"}, {"id": "4", "caption": "unrelated"}]
        ins = {"1": {"views": 900, "likes": 10, "saves": 5}, "T1": {"views": 100},
               "3": {"views": 300, "likes": 2}}
        rows, status = F.collect(FakeClient(media, {}, ins), CATALOG, log=lambda _: None)
        self.assertEqual((len(rows), status), (3, "ok: 3 posts"))
        data = F.build({}, rows, {"instagram": status}, NOW)
        self.assertEqual([a["key"] for a in data["ranking"]["apps"]], ["a", "c", "b"])
        self.assertEqual((data["boost"], data["demote"]), (["a"], ["b"]))
        self.assertEqual(data["ranking"]["apps"][0]["avg_score"], 900 + 30 + 40)

    def test_boost_needs_three_apps_and_history_is_kept(self):
        self.assertEqual(F.boost_lists([{"key": "a"}, {"key": "b"}]), ([], []))
        old = {"channel": "threads", "id": "OLD", "metrics": {"views": 5}, "score": 5, "app": "z",
               "locale": "en", "hook": "h", "posted_at": "2026-09-01"}
        self.assertEqual(len(F.merge([old], [dict(old, id="NEW")])), 2)

    def test_missing_insights_permission_skips(self):
        rows, status = F.collect(FakeClient([{"id": "1", "caption": "Hit your limit again?"}], {}, deny="insights"),
                                 CATALOG, log=lambda _: None)
        self.assertEqual((rows, status), ([], "skipped: no insights permission"))

    def test_page_table_is_compact(self):
        hooks = [{"app": f"app{i}", "locale": "en", "hook": "A very long hook line that goes on", "views": 100 - i,
                  "avg_score": 100 - i} for i in range(12)]
        perf = {"updated_at": "2026-10-14T00:00:00Z", "ranking": {"hooks": hooks}, "boost": ["app0"],
                "sources": {"threads": "skipped: no insights permission"}}
        table = P.build_performance(perf, {"app0": "Zero"})
        rows = [line for line in table.splitlines() if line.startswith("| ") and line[2].isdigit()]
        self.assertEqual([r.split(" | ")[0] for r in rows], [f"| {i}" for i in (1, 2, 3, 4, 5, 8, 9, 10, 11, 12)])
        self.assertIn("加碼排程：Zero", table)
        self.assertIn("Threads no insights permission", table)
        self.assertIn("…", table)
        self.assertEqual(P.build_performance({}, {}), "")


def row(ch, views, ts, locale="en", variant=None, app="a", kind="clip"):
    return {"channel": ch, "id": f"{ch}{ts}{views}", "posted_at": ts, "app": app, "locale": locale, "hook": "h",
            "clip": f"{app}/{locale}", "kind": kind, "variant": variant, "metrics": {"views": views}, "score": views}


def series(ch, views, n, hour=1, start=1, **kw):
    return [row(ch, views, f"2026-10-{start + i // 2:02d}T{hour:02d}:2{i % 2}:00", **kw) for i in range(n)]


class SearchLoop(unittest.TestCase):
    def test_variant_posts_resolve_to_their_lead(self):
        clips = {"clips": {"a/en": dict(CLIPS["clips"]["a/en"], hooks=[
            {"id": "a", "lead": "Hit your limit again?", "benefit": "See what's left"},
            {"id": "b", "lead": "See what's left", "benefit": "Alerts"}])}}
        cat = O.Catalog(clips, [{"channel": "instagram", "clip": "a/en", "id": "M1", "variant": "b"}], {})
        self.assertEqual((cat.resolve("instagram", {"id": "M1"})["hook"], cat.resolve("instagram", {"id": "M1"})["variant"]),
                         ("See what's left", "b"))
        self.assertEqual(cat.resolve("threads", {"id": "Z", "caption": "See what's left\nAlerts"})["variant"], "b")
        self.assertEqual(cat.resolve("threads", {"id": "Y", "caption": "Hit your limit again?\nx"})["variant"], "a")

    def test_hook_winners_need_two_variants_with_data(self):
        rows = series("instagram", 50, 5, variant="a") + series("threads", 10, 5, variant="b")
        wins = F.hook_winners(rows)
        self.assertEqual((wins["global"], wins["locales"].get("en"), wins["apps"].get("a/en")), ("a", "a", "a"))
        self.assertEqual(F.hook_winners(series("instagram", 50, 9, variant="a"))["global"], None)
        data = F.build({}, rows, {}, NOW)
        self.assertEqual([v["key"] for v in data["ranking"]["variants"]], ["a", "b"])

    def test_low_median_channel_drops_to_one_a_day_and_frees_a_slot(self):
        rows = series("threads", 8, 10, hour=1) + series("threads", 12, 4, hour=15, start=10)
        rows += series("instagram", 40, 14)
        alloc = F.allocation(rows, limit=20)
        self.assertEqual((alloc["reduced"], alloc["best"]), (["threads"], "instagram"))
        self.assertEqual((alloc["channels"]["threads"]["daily"], alloc["channels"]["threads"]["keep_slot"]), (1, 15))
        self.assertIn("Threads 近 14 則觀看中位數 8＜20 → 每天 1 則，空出的時段給 Instagram", alloc["decision"])
        self.assertNotIn("\n", alloc["decision"])
        # Under 14 posts nothing changes; a strong channel is never reduced.
        self.assertEqual(F.allocation(series("threads", 1, 13) + series("instagram", 40, 14), limit=20)["reduced"], [])
        with mock.patch.dict("os.environ", {"PERF_MIN_MEDIAN_VIEWS": "5"}):
            self.assertEqual(F.allocation(rows)["reduced"], [])
        weak_ig = F.allocation(series("instagram", 3, 14) + series("threads", 40, 14), limit=20)
        self.assertIn("沒有空檔時段", weak_ig["decision"])

    def test_best_hours_wait_for_twenty_posts_and_two_hours(self):
        few = series("instagram", 10, 19)
        self.assertEqual(F.best_hours(few), ({}, {"instagram": "19/20 則"}))
        rows = series("instagram", 10, 12, hour=1) + series("instagram", 30, 10, hour=15, start=10)
        hours, status = F.best_hours(rows)
        self.assertEqual(hours["instagram"]["en"]["hour"], 15)
        self.assertEqual(status, {})
        one_hour, why = F.best_hours(series("threads", 10, 22))
        self.assertEqual((one_hour, list(why)), ({}, ["threads"]))

    def test_page_shows_decision_hours_and_variants_in_one_line_each(self):
        hooks = [{"app": "a", "locale": "en", "hook": "h", "views": 9, "avg_score": 9}]
        perf = {"updated_at": "2026-10-14T00:00:00Z", "ranking": {"hooks": hooks, "variants": [
                    {"key": "a", "avg_score": 12.5, "posts": 6}, {"key": "b", "avg_score": 4, "posts": 5}]},
                "hook_winners": {"global": "a"},
                "allocation": {"decision": "Threads 近 14 則觀看中位數 8＜20 → 每天 1 則，空出的時段給 Instagram",
                               "channels": {"threads": {"daily": 1}}},
                "best_hours": {"instagram": {"en": {"hour": 15}}}}
        table = P.build_performance(perf, {})
        self.assertIn("\n通路調整：Threads 近 14 則觀看中位數 8＜20", table)
        self.assertIn("建議時段（台灣）：Instagram en 23:00", table)
        self.assertIn("鉤子版本：a 問題開頭 12.5（6 則） · b 好處開頭 4（5 則）；目前優先 a", table)
        waiting = P.build_performance(dict(perf, best_hours={}, best_hours_status={"instagram": "3/20 則"}), {})
        self.assertIn("建議時段：Instagram 3/20 則", waiting)
        section = P.build_section({"clips": {}, "schedule": [{"date": "2099-01-01", "slot": 1, "channel": "threads",
                                                             "clip": "x/en"}]}, [], {}, NOW,
                                  allocation=perf["allocation"])
        self.assertIn("| Threads | 自動 1 支／天 |", section)


if __name__ == "__main__":
    unittest.main()
