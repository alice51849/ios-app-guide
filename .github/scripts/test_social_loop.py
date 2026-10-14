#!/usr/bin/env python3
"""Tests for comment_replies.py, post_performance.py and the 成效排行 table (no network)."""
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import clip_progress as P  # noqa: E402
import comment_replies as R  # noqa: E402
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

    def test_link_only_for_link_intents_and_language_matches(self):
        s = state()
        with mock.patch.object(R, "play_store_url", return_value=None), mock.patch.object(R, "is_free", return_value=True):
            price = R.decide(c("1", "is it free?"), self.post, "instagram", "lumi", s, "M", NOW)
            thanks = R.decide(c("2", "謝謝！好用"), self.post, "instagram", "lumi", s, "M", NOW)
            android = R.decide(c("3", "android?"), self.post, "instagram", "lumi", s, "M", NOW)
        self.assertIn("https://apps.apple.com/app/id111?pt=118326163&ct=rp_ig&mt=8", price["text"])
        self.assertIn(price["text"].splitlines()[0], [t.split("\n")[0] for t in R.T["en"]["price_free"]])
        self.assertEqual(thanks["lang"], "zh-Hant")
        self.assertNotIn("http", thanks["text"])
        self.assertEqual(android["key"], "android_none")
        self.assertNotIn("http", android["text"])

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


if __name__ == "__main__":
    unittest.main()
