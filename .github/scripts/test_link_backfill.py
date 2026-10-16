#!/usr/bin/env python3
"""Tests for link_backfill.py (no network): the download link goes under our own posts that lack it, once."""
import copy
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("POST_QA_OFFLINE", "1")

import link_backfill as B  # noqa: E402
import own_posts as OP  # noqa: E402

MOCHI = "6785004775"   # on Google Play in the Android snapshot
PLAIN = "6818607603"   # iOS only here (not in the snapshot)


class FakeClient:
    def __init__(self, channel, media, comments=None, username="brand", fail_on_write=None, fail_comments=None):
        self.channel, self.media_rows, self.by_post = channel, media, comments or {}
        self.user_id, self.username = "u1", username
        self.writes, self.attempts, self.reads = [], 0, 0
        self.fail_on_write, self.fail_comments = fail_on_write, fail_comments

    def me(self):
        return self

    def _get(self, path, **params):
        return {"data": self.media_rows, "paging": {}}

    def comments(self, media_id, limit=50):
        self.reads += 1
        if self.fail_comments and (self.fail_comments is not True or self.writes):
            raise self.fail_comments if self.fail_comments is not True else RuntimeError("network down")
        return list(self.by_post.get(str(media_id), []))

    def _post(self, path, **fields):
        return {"id": self._write(path.split("/")[0], fields["message"])}

    def reply(self, post_id, text):
        return self._write(post_id, text)

    def _write(self, post_id, text):
        self.attempts += 1
        if self.fail_on_write:
            raise self.fail_on_write
        self.writes.append((str(post_id), text))
        self.by_post.setdefault(str(post_id), []).append({"id": f"c{len(self.writes)}", "text": text, "user": self.username,
                                                          "own": True})
        return f"c{len(self.writes)}"


def catalog():
    clips = {"mochi/en": {"app": "mochi", "locale": "en", "url": "v", "name": "Mochi",
                          "store_url": f"https://apps.apple.com/us/app/id{MOCHI}?ct=h7_mochi_en",
                          "hooks": [{"id": "a", "lead": "Task list too boring?"}]}}
    posts = [{"channel": "instagram", "clip": "mochi/en", "id": "100", "link": "https://www.instagram.com/reel/AAA/", "variant": "a"},
             {"channel": "threads", "clip": "mochi/en", "id": "200", "link": "https://www.threads.com/@b/post/BBB", "variant": "a"}]
    improvements = {"apps": [{"name": "Plain Pro", "key": "plainpro", "app_store_id": PLAIN},
                             {"name": "Mochi", "key": "mochi", "app_store_id": MOCHI}]}
    return OP.Catalog(clips=clips, posts=posts, improvements=improvements)


def ig(media, comments=None, **kw):
    return FakeClient("instagram", media, comments, **kw)


def reel(post_id="100", caption="Task list too boring?\nSearch “Mochi” on the App Store\nLink in bio"):
    link = "https://www.instagram.com/reel/AAA/" if post_id == "100" else f"https://www.instagram.com/reel/X{post_id}/"
    return {"id": post_id, "caption": caption, "permalink": link, "timestamp": "2026-10-16T05:00:00+0000"}


def fresh_state():
    return B.load_state(Path("/nonexistent"))


class BackfillTest(unittest.TestCase):
    def run_channel(self, client, state=None, **kw):
        kw.setdefault("sleeper", lambda s: None)
        kw.setdefault("log", lambda *a: None)
        return B.run(client, catalog(), state if state is not None else fresh_state(), **kw)

    def test_audit_lists_the_post_without_a_link_and_writes_nothing(self):
        client = ig([reel()])
        rows = self.run_channel(client)
        self.assertEqual([r["status"] for r in rows], ["missing"])
        self.assertEqual(rows[0]["app"], "mochi")
        self.assertIn("Task list too boring?", rows[0]["text"])
        self.assertEqual(client.writes, [])

    def test_a_caption_that_has_both_links_is_fine(self):
        store, play = B.links_for("instagram", MOCHI)
        client = ig([reel(caption=f"Hook\nApp Store: {store}\nGoogle Play: {play}")])
        self.assertEqual([r["status"] for r in self.run_channel(client, apply=True)], ["ok_caption"])
        self.assertEqual(client.writes, [])

    def test_apply_comments_the_links_once_and_reads_them_back(self):
        client = ig([reel()])
        state = fresh_state()
        rows = self.run_channel(client, state, apply=True)
        self.assertEqual(rows[0]["status"], "backfilled")
        self.assertTrue(rows[0]["verified"])
        post, text = client.writes[0]
        self.assertEqual(post, "100")
        self.assertIn(f"https://apps.apple.com/app/id{MOCHI}?pt=118326163&ct=bf_ig&mt=8", text)
        self.assertIn("https://play.google.com/store/apps/details?id=com.alice51849.MochiTodo", text)  # Mochi is on Android
        self.assertIn("Get it on the App Store", text)
        # a second sweep: our own comment (and the state) mean nothing more is added
        rows2 = self.run_channel(client, state, apply=True)
        self.assertEqual(len(client.writes), 1)
        self.assertEqual(rows2[0]["status"], "ok_backfilled_earlier")
        rows3 = self.run_channel(client, fresh_state(), apply=True)  # state lost: the comment itself is found
        self.assertEqual(len(client.writes), 1)
        self.assertEqual(rows3[0]["status"], "ok_comment")

    def test_only_the_missing_store_is_added_when_the_caption_has_play_only(self):
        store, play = B.links_for("instagram", MOCHI)
        client = ig([reel(caption=f"Hook\nGoogle Play: {play}")])
        rows = self.run_channel(client, apply=True)
        self.assertEqual(rows[0]["status"], "backfilled")
        self.assertIn("apps.apple.com", client.writes[0][1])
        self.assertNotIn("play.google.com", client.writes[0][1])

    def test_max_new_and_only_limit_the_batch(self):
        media = [reel("100"), reel("101", "Hook 2 Mochi"), reel("102", "Hook 3 Mochi")]
        client = ig(media)
        rows = self.run_channel(client, apply=True, max_new=1)
        self.assertEqual(len(client.writes), 1)
        self.assertEqual([r["status"] for r in rows], ["backfilled"], "the used-up batch reads nothing more")
        self.assertEqual(client.reads, 2, "one read before the write, one for the read-back")
        client = ig(media)
        self.run_channel(client, apply=True, only={"102"})
        self.assertEqual([w[0] for w in client.writes], ["102"])

    def test_a_post_whose_app_is_unknown_is_listed_not_guessed(self):
        client = ig([reel("555", "A photo of my cat")])
        rows = self.run_channel(client, apply=True)
        self.assertEqual(rows[0]["status"], "unknown_app")
        self.assertEqual(client.writes, [])

    def test_app_found_by_name_in_the_text_gets_its_own_link(self):
        client = ig([reel("556", "Plain Pro makes it simple")])
        rows = self.run_channel(client, apply=True)
        self.assertEqual(rows[0]["status"], "backfilled")
        self.assertIn(f"id{PLAIN}", client.writes[0][1])
        self.assertNotIn("play.google.com", client.writes[0][1])  # iOS only

    def test_a_slow_down_answer_stops_the_run(self):
        err = OP.ApiError(400, 4, "Application request limit reached")
        client = ig([reel("100"), reel("101", "Hook Mochi")], fail_on_write=err)
        rows = self.run_channel(client, apply=True)
        self.assertTrue(rows[0]["status"].startswith("write_failed"))
        self.assertEqual(client.writes, [])
        self.assertEqual(client.attempts, 1, "the channel stops at the first answer")

    def test_every_write_attempt_counts_and_the_first_error_stops_the_channel(self):
        client = ig([reel("100"), reel("101", "Hook 2 Mochi"), reel("102", "Hook 3 Mochi")], fail_on_write=OP.ApiError(400, 100, "bad"))
        state = fresh_state()
        rows = self.run_channel(client, state, apply=True, max_new=3)
        self.assertEqual(client.attempts, 1, "a failing write is not retried against the next posts")
        self.assertEqual(rows[0]["status"], "write_failed:100")
        self.assertEqual(state["failed"]["instagram"]["100"]["n"], 1)

    def test_a_post_that_failed_twice_is_set_aside_and_the_next_one_is_done(self):
        client = ig([reel("100"), reel("101", "Hook 2 Mochi")])
        state = fresh_state()
        state["failed"] = {"instagram": {"100": {"n": B.MAX_FAILS, "last": "write_failed:100"}}}
        rows = self.run_channel(client, state, apply=True)
        self.assertEqual([r["status"] for r in rows], ["write_failed_skipped", "backfilled"])
        self.assertEqual([w[0] for w in client.writes], ["101"])

    def test_the_receipt_is_saved_before_the_read_back_and_survives_a_failing_read_back(self):
        client = ig([reel()], fail_comments=True)   # reads work until the first write, then the network drops
        snapshots = []
        state = fresh_state()
        rows = self.run_channel(client, state, apply=True, save=lambda st: snapshots.append(copy.deepcopy(st)))
        self.assertEqual(rows[0]["status"], "backfilled_unverified")
        self.assertEqual(len(client.writes), 1)
        first_with_receipt = next(s for s in snapshots if s["done"].get("instagram", {}).get("100"))
        self.assertFalse(first_with_receipt["done"]["instagram"]["100"]["verified"])
        self.assertIn("100", state["done"]["instagram"])

    def test_an_unverified_receipt_is_checked_again_and_never_written_twice(self):
        client = ig([reel()])
        state = fresh_state()
        state["done"] = {"instagram": {"100": {"at": "t", "comment_id": "c9", "app": "mochi", "verified": False}}}
        rows = self.run_channel(client, state, apply=True)
        self.assertEqual(rows[0]["status"], "backfilled_unverified")   # still not visible: no second write
        self.assertEqual(client.writes, [])
        store, play = B.links_for("instagram", MOCHI)
        client = ig([reel()], {"100": [{"id": "c9", "text": f"{store}\n{play}", "user": "brand", "own": True}]})
        rows = self.run_channel(client, state, apply=True)
        self.assertEqual(rows[0]["status"], "ok_backfilled_earlier")
        self.assertTrue(state["done"]["instagram"]["100"]["verified"])
        self.assertEqual(client.writes, [])

    def test_the_read_budget_leaves_the_rest_unchecked(self):
        client = ig([reel("100"), reel("101", "Hook 2 Mochi")])
        rows = self.run_channel(client, max_reads=1)
        self.assertEqual([r["status"] for r in rows], ["missing", "not_checked"])
        self.assertEqual(client.reads, 1)

    def test_a_read_that_is_throttled_stops_the_audit(self):
        client = ig([reel("100"), reel("101", "Hook 2 Mochi")], fail_comments=OP.ApiError(429, 0, "Too many requests"))
        rows = self.run_channel(client)
        self.assertEqual([r["status"] for r in rows], ["throttled"])
        self.assertEqual(client.reads, 1)

    def test_a_repost_shell_is_not_one_of_our_posts(self):
        shell = dict(reel("777", "Hook Mochi"), media_type="REPOST_FACADE")
        client = ig([shell, reel("100")])
        rows = self.run_channel(client)
        self.assertEqual([r["id"] for r in rows], ["100"])

    def test_threads_reply_is_the_link_home_and_our_reply_counts(self):
        store, play = B.links_for("threads", MOCHI)
        threads = {"id": "200", "text": "Task list too boring?", "permalink": "https://www.threads.com/@b/post/BBB", "timestamp": "2026-10-15T06:00:00+0000"}
        client = FakeClient("threads", [threads], {"200": [{"id": "r1", "text": f"App Store: {store}\nGoogle Play: {play}", "user": "brand", "own": True}]})
        state = fresh_state()
        self.assertEqual([r["status"] for r in self.run_channel(client, state, apply=True)], ["ok_reply"])
        self.assertEqual(state["checked"]["threads"]["200"], "ok_reply", "a post that is fine is never read again")
        client = FakeClient("threads", [threads])
        rows = self.run_channel(client, apply=True)
        self.assertEqual(rows[0]["status"], "backfilled")
        self.assertEqual(client.writes[0][0], "200")
        self.assertIn("ct=bf_th", client.writes[0][1])

    def test_summary_counts_and_merge(self):
        self.assertEqual(B.summarize([{"status": "missing"}, {"status": "missing"}, {"status": "write_failed:4"}]),
                         {"missing": 2, "write_failed": 1})
        old = [{"channel": "threads", "id": "1", "date": "2026-10-01", "status": "missing"},
               {"channel": "threads", "id": "2", "date": "2026-10-02", "status": "missing"}]
        new = [{"channel": "threads", "id": "2", "date": "2026-10-02", "status": "backfilled"}]
        merged = {r["id"]: r["status"] for r in B.merge_rows(old, new)}
        self.assertEqual(merged, {"1": "missing", "2": "backfilled"})

    def test_nothing_is_written_without_the_android_snapshot(self):
        client = ig([reel()])
        with mock.patch.object(B, "android_apps", return_value={}):
            rows = self.run_channel(client, apply=True)
            self.assertEqual(rows[0]["status"], "snapshot_missing")
            self.assertEqual(client.attempts, 0)
            self.assertEqual(B.main(["audit"]), 1)


class AppFinderTest(unittest.TestCase):
    def finder(self):
        names = [("Mochi: Cute Checklist", "mochi", "1"), ("Mochi DoneStamp: Last Time", "mochidonestamp", "2"),
                 ("Aim990：英文弱點教練", "aim990", "3"), ("Wordmate Lite 每天五個單字", "wordmatelite", "4"),
                 ("Wordmate：44 種語言背單字", "wordmate", "5"), ("Snapport Lite: Take ID Photos", "snapportlite", "6"),
                 ("Snapport: Passport & ID Photos", "snapport", "7"), ("Sereno: Sleep Sounds", "sereno", "8"),
                 ("Lumi 數學星球：兒童數學（Lumi Math Pro）", "lumimathpro", "9"),
                 ("TripBee Pro: Trip Planner", "tripbee", "10"), ("TripBee Lite: Trip Planner", "tripbeelite", "11")]
        cat = OP.Catalog(clips={}, posts=[], improvements={"apps": [{"name": n, "key": k, "app_store_id": i} for n, k, i in names]})
        return B.AppFinder(cat)

    def app(self, text):
        post = self.finder().resolve("threads", {"id": "x", "caption": text, "permalink": ""})
        return post["app"] if post else None

    def test_a_brand_at_the_start_decides_and_the_longest_brand_wins(self):
        self.assertEqual(self.app("Mochi: قائمة مهام لطيفة نظّمي يومك"), "mochi")
        self.assertEqual(self.app("Mochi DoneStamp: Zuletzt Merkt sich, wann es war"), "mochidonestamp")
        self.assertEqual(self.app("Wordmate Lite: Learn Words Five a day"), "wordmatelite")
        self.assertEqual(self.app("Wordmate: Learn 44 Languages"), "wordmate")
        self.assertEqual(self.app("Snapport Lite Lav ID-fotos derhjemme"), "snapportlite")
        self.assertEqual(self.app("Snapport: Passport Photos Passport ID Visa"), "snapport")
        self.assertEqual(self.app("Lumi Math Pro: Kids Numbers Early math"), "lumimathpro")
        self.assertEqual(self.app("TripBee Lite: Travel Plan"), "tripbeelite")

    def test_an_unknown_product_variant_is_not_mistaken_for_the_known_app(self):
        self.assertIsNone(self.app("Aim990 Plus: English Mock Test Offline English Test Practice"))
        self.assertEqual(self.app("Aim990 Your TOEIC Coach Unlock your potential"), "aim990")

    def test_a_brand_inside_the_text_decides_only_when_it_is_the_only_one(self):
        self.assertEqual(self.app("一份你不想打開的待辦清單。放進 Mochi 清單就好。"), "mochi")
        self.assertEqual(self.app("眠りと集中のホワイトノイズ。Serenoは、あなたの電話を変えます。"), "sereno")
        self.assertIsNone(self.app("Mochi and Sereno together make a calm day"))
        self.assertIsNone(self.app("A photo of my cat"))
        self.assertIsNone(self.app("TripBee: Plánovač cest"), "no Pro / Lite word: not guessed")

    def test_the_app_store_id_in_the_text_decides(self):
        self.assertEqual(self.app("Leaving the link here: https://apps.apple.com/us/app/id3?mt=8"), "aim990")
        self.assertIsNone(self.app("Rate us https://apps.apple.com/us/app/id3?action=write-review"))


if __name__ == "__main__":
    unittest.main()
