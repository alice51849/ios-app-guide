#!/usr/bin/env python3
"""Tests for link_backfill.py (no network): the download link goes under our own posts that lack it, once."""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("POST_QA_OFFLINE", "1")

import link_backfill as B  # noqa: E402
import own_posts as OP  # noqa: E402

MOCHI = "6785004775"   # on Google Play in the Android snapshot
PLAIN = "6818607603"   # iOS only here (not in the snapshot)


class FakeClient:
    def __init__(self, channel, media, comments=None, username="brand", fail_on_write=None):
        self.channel, self.media_rows, self.by_post = channel, media, comments or {}
        self.user_id, self.username = "u1", username
        self.writes, self.fail_on_write = [], fail_on_write

    def me(self):
        return self

    def _get(self, path, **params):
        return {"data": self.media_rows, "paging": {}}

    def comments(self, media_id, limit=50):
        return list(self.by_post.get(str(media_id), []))

    def _post(self, path, **fields):
        return {"id": self._write(path.split("/")[0], fields["message"])}

    def reply(self, post_id, text):
        return self._write(post_id, text)

    def _write(self, post_id, text):
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


class BackfillTest(unittest.TestCase):
    def run_channel(self, client, state=None, **kw):
        kw.setdefault("sleeper", lambda s: None)
        kw.setdefault("log", lambda *a: None)
        return B.run(client, catalog(), state if state is not None else B.load_state(Path("/nonexistent")), **kw)

    def test_audit_lists_the_post_without_a_link_and_writes_nothing(self):
        client = ig([reel()])
        rows = self.run_channel(client)
        self.assertEqual([r["status"] for r in rows], ["missing"])
        self.assertEqual(rows[0]["app"], "mochi")
        self.assertEqual(client.writes, [])

    def test_a_caption_that_has_both_links_is_fine(self):
        store, play = B.links_for("instagram", MOCHI)
        client = ig([reel(caption=f"Hook\nApp Store: {store}\nGoogle Play: {play}")])
        self.assertEqual([r["status"] for r in self.run_channel(client, apply=True)], ["ok_caption"])
        self.assertEqual(client.writes, [])

    def test_apply_comments_the_links_once_and_reads_them_back(self):
        client = ig([reel()])
        state = B.load_state(Path("/nonexistent"))
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
        rows3 = self.run_channel(client, B.load_state(Path("/nonexistent")), apply=True)  # state lost: the comment itself is found
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
        self.assertEqual([r["status"] for r in rows], ["backfilled", "missing_queued", "missing_queued"])
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

    def test_threads_reply_is_the_link_home_and_our_reply_counts(self):
        store, play = B.links_for("threads", MOCHI)
        threads = {"id": "200", "text": "Task list too boring?", "permalink": "https://www.threads.com/@b/post/BBB", "timestamp": "2026-10-15T06:00:00+0000"}
        client = FakeClient("threads", [threads], {"200": [{"id": "r1", "text": f"App Store: {store}\nGoogle Play: {play}", "user": "brand", "own": True}]})
        self.assertEqual([r["status"] for r in self.run_channel(client, apply=True)], ["ok_reply"])
        client = FakeClient("threads", [threads])
        rows = self.run_channel(client, apply=True)
        self.assertEqual(rows[0]["status"], "backfilled")
        self.assertEqual(client.writes[0][0], "200")
        self.assertIn("ct=bf_th", client.writes[0][1])

    def test_summary_counts(self):
        self.assertEqual(B.summarize([{"status": "missing"}, {"status": "missing"}, {"status": "write_failed:4"}]),
                         {"missing": 2, "write_failed": 1})


if __name__ == "__main__":
    unittest.main()
