#!/usr/bin/env python3
"""Tests for link_backfill.py (no network): the download link goes under our own posts that lack it, once."""
import contextlib
import copy
import datetime as dt
import io
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("POST_QA_OFFLINE", "1")

import link_backfill as B  # noqa: E402
import own_posts as OP  # noqa: E402

B.URL_CHECK = lambda url: (True, "test")   # no test reaches the network; UrlOkTest drives the real url_ok

MOCHI = "6785004775"   # on Google Play in the Android snapshot
PLAIN = "6818607603"   # iOS only here (not in the snapshot)


class FakeClient:
    def __init__(self, channel, media, comments=None, username="brand", fail_on_write=None, fail_comments=None,
                 hide_own=False, drop_writes=False, counts=None, account_replies=None, fail_replies=False,
                 fail_count=False):
        self.channel, self.media_rows, self.by_post = channel, media, comments or {}
        self.user_id, self.username = "u1", username
        self.writes, self.attempts, self.reads, self.known_comments = [], 0, 0, set()
        self.fail_on_write, self.fail_comments = fail_on_write, fail_comments
        # Instagram: the list of a post does not show the account's own comments, the post's count does
        self.hide_own, self.drop_writes, self.counts = hide_own, drop_writes, dict(counts or {})
        self.account_replies, self.fail_replies, self.fail_count = account_replies or [], fail_replies, fail_count

    def me(self):
        return self

    def _get(self, path, **params):
        if params.get("fields") == "comments_count":
            if self.fail_count:   # the platform answers, but not with a count
                raise OP.ApiError(400, 100, "Invalid parameter")
            return {"comments_count": self.counts.get(str(path), 0)}
        if str(path) in self.known_comments:   # a comment of the account, fetched by its id: an empty object
            return {}
        if str(path).startswith("c") and str(path)[1:].isdigit():   # an id that does not exist
            raise OP.ApiError(400, 100, "Object does not exist")
        if path.endswith("/replies"):   # all replies of the account
            if self.fail_replies:
                raise RuntimeError("network down")
            return {"data": self.account_replies}
        return {"data": self.media_rows, "paging": {}}

    def comments(self, media_id, limit=50):
        self.reads += 1
        if self.fail_comments and (self.fail_comments is not True or self.writes):
            raise self.fail_comments if self.fail_comments is not True else RuntimeError("network down")
        rows = list(self.by_post.get(str(media_id), []))
        return [r for r in rows if not (self.hide_own and r.get("own"))]

    def _post(self, path, **fields):
        return {"id": self._write(path.split("/")[0], fields["message"])}

    def reply(self, post_id, text):
        return self._write(post_id, text)

    def _write(self, post_id, text):
        self.attempts += 1
        if self.fail_on_write:
            raise self.fail_on_write
        self.writes.append((str(post_id), text))
        if not self.drop_writes:   # a dropped write: the platform answered with an id, nothing was added
            self.known_comments.add(f"c{len(self.writes)}")
            self.by_post.setdefault(str(post_id), []).append({"id": f"c{len(self.writes)}", "text": text,
                                                              "user": self.username, "own": True})
            self.counts[str(post_id)] = self.counts.get(str(post_id), 0) + 1
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

    def test_a_link_that_does_not_answer_is_not_written_and_does_not_use_up_the_batch(self):
        client = ig([reel("100"), reel("101")])
        # Mochi is on Android, so a post needs two links: the first post's store link is dead, all others answer
        answers = iter([(False, "HTTP 404"), (True, "HTTP 200"), (True, "HTTP 200"), (True, "HTTP 200")])
        with mock.patch.object(B, "URL_CHECK", lambda url: next(answers)):
            rows = self.run_channel(client, apply=True, max_new=1)
        by_id = {r["id"]: r for r in rows}
        self.assertEqual("link_unreachable", by_id["100"]["status"])
        self.assertIn("HTTP 404", by_id["100"]["error"])
        self.assertNotIn("?", by_id["100"]["error"])   # the page, never the tracking parameters
        self.assertEqual([("101", client.writes[0][1])], client.writes)   # the next post still got its link
        self.assertEqual("backfilled", by_id["101"]["status"])

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
            with contextlib.redirect_stdout(io.StringIO()):   # the ::error:: line is not a real alert here
                self.assertEqual(B.main(["audit"]), 1)

    def test_an_older_post_with_the_app_store_link_but_no_play_link_is_left_alone(self):
        store, _play = B.links_for("instagram", MOCHI)
        client = ig([reel(caption=f"Hook\nApp Store: {store}")])
        rows = self.run_channel(client, apply=True)
        self.assertEqual(rows[0]["status"], "ok_store_only")
        self.assertEqual((client.writes, client.reads), ([], 0))
        reply = {"id": "r1", "text": f"App Store: {store}", "user": "brand", "own": True}
        client = FakeClient("threads", [{"id": "200", "text": "Task list too boring?", "permalink": "https://www.threads.com/@b/post/BBB",
                                         "timestamp": "2026-10-15T06:00:00+0000"}], {"200": [reply]})
        state = fresh_state()
        self.assertEqual(self.run_channel(client, state, apply=True)[0]["status"], "ok_store_only")
        self.assertEqual(client.writes, [])
        self.assertEqual(state["checked"]["threads"]["200"], "ok_store_only", "never read again")

    # ---- the read-back of an Instagram comment (the list of a post hides the account's own comments) ...

    def test_instagram_hides_its_own_comments_so_the_count_going_up_is_the_proof(self):
        client = ig([reel()], hide_own=True)
        state = fresh_state()
        rows = self.run_channel(client, state, apply=True)
        self.assertEqual(rows[0]["status"], "backfilled")
        self.assertEqual(rows[0]["via"], "count")
        self.assertEqual(state["done"]["instagram"]["100"]["count_before"], 0)
        rows2 = self.run_channel(client, state, apply=True)
        self.assertEqual(rows2[0]["status"], "ok_backfilled_earlier")
        self.assertEqual(len(client.writes), 1)

    def test_a_write_the_platform_dropped_is_not_verified_and_never_repeated(self):
        client = ig([reel()], hide_own=True, drop_writes=True)
        state = fresh_state()
        self.assertEqual(self.run_channel(client, state, apply=True)[0]["status"], "backfilled_unverified")
        self.assertEqual(self.run_channel(client, state, apply=True)[0]["status"], "backfilled_unverified")
        self.assertEqual(len(client.writes), 1)

    def test_a_receipt_from_before_the_count_was_kept_is_proven_by_a_count_of_one(self):
        client = ig([reel()], hide_own=True, counts={"100": 1})
        client.known_comments.add("c9")   # the comment we wrote exists, fetched by its id
        state = fresh_state()
        state["done"] = {"instagram": {"100": {"at": "t", "comment_id": "c9", "app": "mochi", "verified": False}}}
        self.assertEqual(self.run_channel(client, state, apply=True)[0]["status"], "ok_backfilled_earlier")
        self.assertEqual(client.writes, [])

    def test_somebody_elses_comment_raising_the_count_is_not_proof_of_ours(self):
        client = ig([reel()], hide_own=True, counts={"100": 1})   # a count of one, but our comment id does not exist
        state = fresh_state()
        state["done"] = {"instagram": {"100": {"at": "t", "comment_id": "c9", "app": "mochi", "verified": False}}}
        self.assertEqual(self.run_channel(client, state, apply=True)[0]["status"], "backfilled_unverified")
        self.assertEqual(client.writes, [])   # and never a second comment either

    def test_comments_the_list_does_not_show_stop_a_second_comment_when_the_receipts_are_lost(self):
        client = ig([reel()], hide_own=True, counts={"100": 1})
        rows = self.run_channel(client, fresh_state(), apply=True)
        self.assertEqual(rows[0]["status"], "unlisted_comments")
        self.assertEqual(client.writes, [])

    # ... and the slow drip: caps per 24 hours

    NOW = dt.datetime(2026, 10, 17, 12, 0, tzinfo=dt.timezone.utc)

    def stamp(self, hours_ago, fmt="%Y-%m-%dT%H:%M:%SZ"):
        return (self.NOW - dt.timedelta(hours=hours_ago)).strftime(fmt)

    def test_the_daily_cap_keeps_the_drip_slow(self):
        media = [reel(str(100 + i), f"Hook {i} Mochi") for i in range(10)]
        cap = B.DAILY_CAP["instagram"]
        recent = {str(900 + i): {"at": self.stamp(2 + i), "comment_id": "x", "app": "mochi", "verified": True} for i in range(cap)}
        client, state = ig(media), fresh_state()
        state["done"] = {"instagram": dict(recent)}
        self.run_channel(client, state, apply=True, max_new=5, now=self.NOW)
        self.assertEqual(client.writes, [], "the cap is used up by the last 24 hours")
        client, state = ig(media), fresh_state()
        state["done"] = {"instagram": {k: dict(v, at=self.stamp(30)) for k, v in recent.items()}}
        self.run_channel(client, state, apply=True, max_new=2, now=self.NOW)
        self.assertEqual(len(client.writes), 2, "a day later the cap is free again")
        client, state = ig(media), fresh_state()   # a failed try counts as much as a written one
        state["failed"] = {"instagram": {str(900 + i): {"n": 1, "at": self.stamp(1)} for i in range(cap)}}
        self.run_channel(client, state, apply=True, max_new=5, now=self.NOW)
        self.assertEqual(client.writes, [])

    def test_threads_never_adds_more_links_than_the_account_limit_allows(self):
        post = {"id": "200", "text": "Task list too boring?", "permalink": "https://www.threads.com/@b/post/BBB",
                "timestamp": "2026-10-15T06:00:00+0000"}
        ceiling = B.LINK_BUDGET_24H["threads"]
        busy = [{"id": f"r{i}", "text": "Get it: https://apps.apple.com/app/id1", "timestamp": self.stamp(1 + i / 10, "%Y-%m-%dT%H:%M:%S+0000")}
                for i in range(ceiling)]
        client = FakeClient("threads", [post], account_replies=busy)
        self.run_channel(client, apply=True, now=self.NOW)
        self.assertEqual(client.writes, [], "the account already sent as many links as the ceiling in 24 hours")
        client = FakeClient("threads", [post], account_replies=busy[:-1])
        self.run_channel(client, apply=True, now=self.NOW)
        self.assertEqual(len(client.writes), 1, "one link fits under the ceiling")
        client = FakeClient("threads", [post], fail_replies=True)
        self.run_channel(client, apply=True, now=self.NOW)
        self.assertEqual(client.writes, [], "links that cannot be counted are not added")

    def test_diag_only_reads(self):
        client = ig([reel()], hide_own=True)
        state = fresh_state()
        self.run_channel(client, state, apply=True)
        lines, before = [], len(client.writes)
        B.diag(client, state, ["100"], finder=B.AppFinder(catalog()), out=lines.append)
        self.assertTrue(any("token owner" in line for line in lines))
        self.assertEqual(len(client.writes), before)


class UrlOkTest(unittest.TestCase):
    """Owner rule 2026-10-17: a link goes under a post only while its page answers HTTP 200."""

    class Resp:
        def __init__(self, status=200, body=b""):
            self.status, self.body = status, body

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

        def read(self):
            return self.body

        def getcode(self):
            return self.status

    def opener(self, handler):
        calls = []

        def op(request, timeout=0):
            url = getattr(request, "full_url", request)
            calls.append(url)
            return handler(url)
        op.calls = calls
        return op

    STORE = "https://apps.apple.com/app/id6785004775?pt=118326163&ct=bf_ig&mt=8"
    PLAY = "https://play.google.com/store/apps/details?id=com.alice51849.MochiTodo&referrer=utm_source%3Dbf_ig"

    def test_http_200_passes_and_a_link_is_looked_at_once_per_run(self):
        op, seen = self.opener(lambda url: self.Resp(200)), {}
        self.assertEqual((True, "HTTP 200"), B.url_ok(self.STORE, op, seen=seen))
        self.assertEqual((True, "HTTP 200"), B.url_ok(self.STORE, op, seen=seen))
        self.assertEqual([self.STORE], op.calls)

    def test_a_missing_page_is_never_accepted_and_never_second_guessed(self):
        def handler(url):
            raise B.urllib.error.HTTPError(url, 404, "Not Found", {}, None)
        op = self.opener(handler)
        self.assertEqual((False, "HTTP 404"), B.url_ok(self.STORE, op, seen={}))
        self.assertEqual(1, len(op.calls))   # no iTunes lookup after a 404

    def test_a_store_page_refused_to_a_script_passes_when_the_lookup_knows_the_app(self):
        def handler(url):
            if "itunes.apple.com/lookup" in url:
                return self.Resp(200, b'{"resultCount": 1}')
            raise B.urllib.error.HTTPError(url, 403, "Forbidden", {}, None)
        ok, why = B.url_ok(self.STORE, self.opener(handler), seen={})
        self.assertTrue(ok)
        self.assertIn("403", why)

        def unknown(url):
            if "itunes.apple.com/lookup" in url:
                return self.Resp(200, b'{"resultCount": 0}')
            raise B.urllib.error.HTTPError(url, 403, "Forbidden", {}, None)
        self.assertEqual((False, "HTTP 403"), B.url_ok(self.STORE, self.opener(unknown), seen={}))

    def test_a_play_page_that_does_not_answer_is_not_known_to_be_fine(self):
        def busy(url):
            raise B.urllib.error.HTTPError(url, 429, "Too Many Requests", {}, None)
        op = self.opener(busy)
        self.assertEqual((False, "HTTP 429"), B.url_ok(self.PLAY, op, seen={}))
        self.assertEqual(1, len(op.calls))   # the lookup is for App Store pages only

        def down(url):
            raise B.urllib.error.URLError("https://secret.example/?token=abc")
        ok, why = B.url_ok(self.PLAY, self.opener(down), seen={})
        self.assertFalse(ok)
        self.assertEqual("URLError", why)
        self.assertNotIn("token", why)


class ConflictAndCountTest(unittest.TestCase):
    """A link to another app already under the post, and a comment count that cannot be read, stop the write."""

    def run_channel(self, client, state=None, **kw):
        kw.setdefault("sleeper", lambda s: None)
        kw.setdefault("log", lambda *a: None)
        return B.run(client, catalog(), state if state is not None else fresh_state(), **kw)

    def test_a_text_that_links_an_app_we_do_not_know_is_not_taken_for_a_brand_mention(self):
        finder = B.AppFinder(catalog())
        text = "New: https://apps.apple.com/app/id9999999999 - works great next to Mochi"
        self.assertIsNone(finder.resolve("threads", {"id": "x", "caption": text, "permalink": ""}))
        known = f"Task list too boring? https://apps.apple.com/app/id{MOCHI}"
        self.assertEqual(MOCHI, finder.resolve("threads", {"id": "x", "caption": known, "permalink": ""})["ios_id"])

    def test_our_own_reply_that_links_another_app_stops_the_backfill(self):
        post = reel("200", caption="Task list too boring?\nMochi on the App Store")
        mine = {"id": "r1", "text": f"Get it on the App Store: https://apps.apple.com/app/id{PLAIN}?pt=1&ct=x&mt=8",
                "user": "brand", "own": True}
        client = FakeClient("threads", [post], {"200": [mine]})
        state = fresh_state()
        rows = self.run_channel(client, state, apply=True)
        self.assertEqual(["unknown_app"], [r["status"] for r in rows])
        self.assertIn("conflict", rows[0]["why"])
        self.assertEqual([], client.writes)
        self.assertEqual("unknown_app", state["checked"]["threads"]["200"])   # settled: never read again

    def test_an_instagram_post_whose_count_cannot_be_read_is_never_written(self):
        client = ig([reel()], fail_count=True)
        for apply in (False, True):
            rows = self.run_channel(client, apply=apply)
            self.assertEqual(["read_failed:count"], [r["status"] for r in rows])
        self.assertEqual([], client.writes)

    def test_the_count_lost_between_the_look_and_the_write_writes_nothing(self):
        client = ig([reel()])
        seen = iter([0, None])   # the look finds the count, the baseline right before the write does not
        with mock.patch.object(B, "comments_count", side_effect=lambda *_: next(seen)):
            rows = self.run_channel(client, apply=True)
        self.assertEqual(["read_failed:count"], [r["status"] for r in rows])
        self.assertEqual([], client.writes)

    def test_merge_state_never_lowers_a_failure_count_or_unverifies_a_receipt(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            current, saved = Path(tmp) / "current.json", Path(tmp) / "saved.json"
            current.write_text(json.dumps({"done": {"instagram": {"1": {"at": "2026-10-16T10:00:00Z", "verified": True},
                                                                  "2": {"at": "2026-10-16T10:00:00Z", "verified": False}}},
                                           "checked": {}, "failed": {"threads": {"9": {"n": 2, "at": "2026-10-16T09:00:00Z"}}}}),
                               encoding="utf-8")
            saved.write_text(json.dumps({"done": {"instagram": {"1": {"at": "2026-10-16T11:00:00Z", "verified": False},
                                                                "2": {"at": "2026-10-16T11:00:00Z", "verified": True},
                                                                "3": {"at": "2026-10-16T11:00:00Z", "verified": True}}},
                                         "checked": {"threads": {"5": "ok_reply"}},
                                         "failed": {"threads": {"9": {"n": 1, "at": "2026-10-16T08:00:00Z"},
                                                                "8": {"n": 1, "at": "2026-10-16T08:00:00Z"}}}}),
                             encoding="utf-8")
            B.merge_state(str(saved), str(current))
            merged = json.loads(current.read_text(encoding="utf-8"))
        self.assertTrue(merged["done"]["instagram"]["1"]["verified"])        # stays verified
        self.assertTrue(merged["done"]["instagram"]["2"]["verified"])        # becomes verified
        self.assertIn("3", merged["done"]["instagram"])
        self.assertEqual(2, merged["failed"]["threads"]["9"]["n"])           # not lowered by an older copy
        self.assertEqual(1, merged["failed"]["threads"]["8"]["n"])
        self.assertEqual("ok_reply", merged["checked"]["threads"]["5"])


class ThreadsPublishWaitTest(unittest.TestCase):
    """A Threads reply is a container plus a publish; the publish needs the container to be ready first."""

    def client(self, publish_answers, container_error=None):
        c = OP.ThreadsClient("secret-token")
        c.user_id = "42"
        c.calls, c.sleeps = [], []

        def post(url, fields):
            step = url.rsplit("/", 1)[-1]
            c.calls.append(step)
            if step == "threads":
                if container_error:
                    raise container_error
                return {"id": "container-1"}
            answer = publish_answers.pop(0)
            if isinstance(answer, Exception):
                raise answer
            return answer
        c.post = post
        return c

    def test_waits_then_publishes_the_same_container_again(self):
        c = self.client([OP.ApiError(400, 24, "The requested resource does not exist"),
                         OP.ApiError(400, 24, "The requested resource does not exist"), {"id": "reply-9"}])
        self.assertEqual("reply-9", c.reply("post-1", "text", sleeper=c.sleeps.append))
        self.assertEqual([35, 25, 25], c.sleeps)
        self.assertEqual(["threads", "threads_publish", "threads_publish", "threads_publish"], c.calls)

    def test_never_creates_a_second_container_when_it_keeps_failing(self):
        err = OP.ApiError(400, 24, "The requested resource does not exist")
        c = self.client([err, err, err])
        with self.assertRaises(OP.ApiError) as ctx:
            c.reply("post-1", "text", sleeper=c.sleeps.append)
        self.assertIn("publish:", str(ctx.exception))
        self.assertEqual(1, c.calls.count("threads"))
        self.assertEqual(3, c.calls.count("threads_publish"))

    def test_another_answer_is_not_retried(self):
        c = self.client([OP.ApiError(400, 4, "Application request limit reached")])
        with self.assertRaises(OP.ApiError) as ctx:
            c.reply("post-1", "text", sleeper=c.sleeps.append)
        self.assertEqual(4, ctx.exception.code)
        self.assertTrue(B.is_throttle(ctx.exception))
        self.assertEqual([35], c.sleeps)
        self.assertEqual(1, c.calls.count("threads_publish"))

    def test_a_failed_container_publishes_nothing(self):
        c = self.client([], container_error=OP.ApiError(400, 100, "Invalid parameter"))
        with self.assertRaises(OP.ApiError):
            c.reply("post-1", "text", sleeper=c.sleeps.append)
        self.assertEqual(["threads"], c.calls)
        self.assertEqual([], c.sleeps)


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

    def test_a_product_we_do_not_know_is_not_the_app_that_shares_its_first_word(self):
        self.assertIsNone(self.app("Aim990 Plus: practice offline. Aim990 keeps you on track"))
        self.assertEqual(self.app("Aim990 helps you. Learn more about it"), "aim990")
        self.assertEqual(self.app("TripBee Lite: Travel Plan, TripBee Lite is free"), "tripbeelite")

    def test_a_brand_inside_the_text_decides_only_when_it_is_the_only_one(self):
        self.assertEqual(self.app("一份你不想打開的待辦清單。放進 Mochi 清單就好。"), "mochi")
        self.assertEqual(self.app("眠りと集中のホワイトノイズ。Serenoは、あなたの電話を変えます。"), "sereno")
        self.assertIsNone(self.app("Mochi and Sereno together make a calm day"))
        self.assertIsNone(self.app("A photo of my cat"))
        self.assertIsNone(self.app("TripBee: Plánovač cest"), "no Pro / Lite word: not guessed")

    def test_the_app_store_id_in_the_text_decides(self):
        self.assertEqual(self.app("Leaving the link here: https://apps.apple.com/us/app/id3?mt=8"), "aim990")
        self.assertIsNone(self.app("Rate us https://apps.apple.com/us/app/id3?action=write-review"))


    def finder_for(self, names, clips=None, posts=None):
        cat = OP.Catalog(clips={"clips": clips or {}}, posts=posts or [],
                         improvements={"apps": [{"name": n, "key": k, "app_store_id": i} for n, k, i in names]})
        return B.AppFinder(cat)

    @staticmethod
    def app_of(finder, text, channel="threads", media_id="x"):
        return (finder.resolve(channel, {"id": media_id, "caption": text, "permalink": ""}) or {}).get("app")

    def test_a_word_from_a_subtitle_is_not_a_name(self):
        f = self.finder_for([("Studydown: Face-Down Timer", "studydown", "20")])
        self.assertIsNone(self.app_of(f, "Locked with Face ID. Scan to PDF"))
        self.assertEqual(self.app_of(f, "Studydown keeps the phone face down"), "studydown")

    def test_the_name_without_pro_counts_only_while_no_other_app_has_it(self):
        f = self.finder_for([("Unblurry Pro", "unblurry", "21"), ("TripBee Pro: Trip Planner", "tripbee", "22"),
                             ("TripBee Lite: Trip Planner", "tripbeelite", "23"), ("G+Money", "gmoney", "24"),
                             ("G+Money Lite", "gmoneylite", "25")])
        self.assertEqual(self.app_of(f, "Unblurry fixes blurry photos"), "unblurry")
        self.assertIsNone(self.app_of(f, "Unblurry Plus fixes blurry photos"), "a product we do not know")
        self.assertIsNone(self.app_of(f, "TripBee plans your trip"), "Pro or Lite: not guessed")
        self.assertEqual(self.app_of(f, "TripBee Lite plans your trip"), "tripbeelite")
        self.assertEqual(self.app_of(f, "G+Money tracks money"), "gmoney")
        self.assertEqual(self.app_of(f, "G+Money Lite tracks money"), "gmoneylite")

    def test_blanks_between_latin_and_cjk_do_not_matter(self):
        f = self.finder_for([("Lumi 數學星球：兒童數學（Lumi Math Pro）", "lumimathpro", "9"),
                             ("Lumi數學星球：探索版（Lumi Math Planet: Explorer）", "lumimath", "8")])
        self.assertIsNone(self.app_of(f, "Lumi數學星球 帶孩子玩數學"), "Explorer or Pro: the same words")
        self.assertEqual(self.app_of(f, "Lumi 數學星球：探索版 免費試玩"), "lumimath")
        self.assertEqual(self.app_of(f, "Lumi數學星球：兒童數學 免費試玩"), "lumimathpro")
        self.assertEqual(self.app_of(f, "Lumi Math Planet is out"), "lumimath")

    def test_a_hook_line_only_one_app_uses_can_name_the_app(self):
        clips = {"a/en": {"app": "a", "store_url": "https://apps.apple.com/us/app/id31?ct=x", "name": "Alpha: Notes",
                          "search": "Alpha Notes", "hook": "Zero friction note taking",
                          "hooks": [{"id": "a", "lead": "Capture ideas in one tap"}]},
                 "b/en": {"app": "b", "store_url": "https://apps.apple.com/us/app/id32?ct=x", "name": "Beta: Timer",
                          "search": "Beta Timer", "hook": "Capture ideas in one tap", "hooks": []}}
        f = self.finder_for([("Alpha: Notes", "a", "31"), ("Beta: Timer", "b", "32")], clips=clips)
        self.assertEqual(self.app_of(f, "Zero friction note taking, all day"), "a")
        self.assertIsNone(self.app_of(f, "Capture ideas in one tap. Easy."), "two apps use this line")
        self.assertEqual(self.app_of(f, "Capture ideas in one tap\nAlpha: Notes"), "a", "the name settles it")

    def test_the_proofs_must_agree(self):
        f = self.finder_for([("Alpha: Notes", "a", "31"), ("Beta: Timer", "b", "32")])
        self.assertEqual(self.app_of(f, "Alpha: Notes https://apps.apple.com/app/id31"), "a")
        self.assertIsNone(self.app_of(f, "Alpha: Notes https://apps.apple.com/app/id32"), "the link says Beta, the name says Alpha")
        self.assertIsNone(self.app_of(f, "https://apps.apple.com/app/id31 and https://apps.apple.com/app/id32"))

    def test_the_ledger_decides_first_and_a_carousel_is_an_instagram_post(self):
        posts = [{"channel": "instagram_feed", "clip": "feed/a/en", "id": "300", "link": "https://www.instagram.com/p/FFF/"},
                 {"channel": "threads", "clip": "b/en", "id": "301", "link": "https://www.threads.com/@x/post/GGG"}]
        clips = {"b/en": {"app": "b", "locale": "en", "store_url": "https://apps.apple.com/us/app/id32?ct=x", "name": "Beta: Timer",
                          "search": "Beta Timer", "hook": "Time it right", "hooks": []}}
        f = self.finder_for([("Alpha: Notes", "a", "31"), ("Beta: Timer", "b", "32")], clips=clips, posts=posts)
        post = f.resolve("instagram", {"id": "300", "caption": "Screens of the app", "permalink": ""})
        self.assertEqual((post["app"], post["why"]), ("a", "ledger"))
        self.assertEqual(self.app_of(f, "Alpha: Notes is here", media_id="301"), "b", "the ledger wins over the text")


class AppFinderRealDataTest(unittest.TestCase):
    def test_every_caption_we_can_generate_maps_to_its_own_app_or_to_none(self):
        """The old captions (no URL) of every clip, hook and channel - the finder must never name another app."""
        import clip_posts as CP
        import search_caption as SC
        catalog = OP.Catalog(posts=[])
        finder = B.AppFinder(catalog)
        total = unknown = 0
        for key, clip in catalog.clips.items():
            for variant in SC.variants(clip):
                for channel in ("instagram", "threads", "telegram"):
                    lines = CP.caption(dict(clip), channel, variant).splitlines()
                    text = "\n".join(line for line in lines if "http" not in line)
                    post = finder.resolve("instagram", {"id": "zz", "caption": text, "permalink": ""})
                    total += 1
                    if post is None:
                        unknown += 1
                    else:
                        self.assertEqual(post["ios_id"], CP.ios_id(clip), f"{key} {variant['id']} {channel}")
        # Not vacuous: every clip of the real clips.json (only real-recording cuts since the 2026-10-17 video
        # compliance gate, so far fewer than the 1000+ captions of the store-screenshot era), 3 channels each.
        self.assertGreater(total, 100)
        self.assertLess(unknown / total, 0.05, "the finder should still know almost every caption of our own")


if __name__ == "__main__":
    unittest.main()
