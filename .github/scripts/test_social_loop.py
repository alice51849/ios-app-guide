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
