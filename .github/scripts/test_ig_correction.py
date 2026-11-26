#!/usr/bin/env python3
"""Tests for ig_correction.py (no network): one correction comment per own post, only after review, read back."""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("POST_QA_OFFLINE", "1")

import ig_correction as C  # noqa: E402
import own_posts as OP  # noqa: E402

NOW = dt.datetime(2026, 11, 26, 6, 0, tzinfo=dt.timezone.utc)
EN = "📝 Correction: the dates in these screenshots are sample data from the app's demo screens.\n📲 Download via the link in bio"


def item(mid="18137507671738061", sc="Dfxiwb0H-lr", text=EN, loc="en", status="pass"):
    return {"media_id": mid, "shortcode": sc, "locale": loc, "text": text, "card": "c", "review": {"status": status}}


class Fake:
    channel = "instagram"

    def __init__(self, owner="aiviews.co", permalink=None, fail_write=None, hide=False):
        self.username, self.owner, self.permalink = "aiviews.co", owner, permalink
        self.counts, self.comments, self.posts = {}, set(), []
        self.fail_write, self.hide = fail_write, hide

    def _get(self, path, **params):
        if path in self.comments:
            return {}
        if path.startswith("c_"):
            raise OP.ApiError(400, 100, "does not exist")
        if params.get("fields") == "comments_count":
            return {"comments_count": self.counts.get(path, 0)}
        return {"id": path, "username": self.owner, "comments_count": self.counts.get(path, 0),
                "permalink": self.permalink or f"https://www.instagram.com/p/{self.sc_of[path]}/"}

    def _post(self, path, **fields):
        if self.fail_write:
            raise self.fail_write
        mid = path.split("/")[0]
        cid = f"c_{len(self.posts)}"
        self.posts.append((mid, fields["message"]))
        if not self.hide:
            self.counts[mid] = self.counts.get(mid, 0) + 1
            self.comments.add(cid)
        return {"id": cid}


def fake_for(items, **kw):
    f = Fake(**kw)
    f.sc_of = {i["media_id"]: i["shortcode"] for i in items}
    return f


class TextTest(unittest.TestCase):
    def test_a_clean_reviewed_text_passes(self):
        self.assertEqual(C.text_problems(item()), [])

    def test_unreviewed_url_or_missing_bio_line_is_refused(self):
        self.assertIn("in-locale review not passed", C.text_problems(item(status="pending")))
        self.assertTrue(any("URL" in p for p in C.text_problems(item(text=EN + "\nhttps://apps.apple.com/app/id1"))))
        self.assertTrue(any("URL" in p for p in C.text_problems(item(text=EN + " open.cait518.cc/ig/"))))
        self.assertTrue(any("line for en" in p for p in C.text_problems(item(text="📝 Correction only."))))
        self.assertTrue(C.text_problems(item(mid="abc")))
        self.assertTrue(C.text_problems(item(text=EN + " @someone")))

    def test_the_1126_batch_from_00_is_well_formed(self):
        batch = Path(os.environ.get("IG_CORRECTION_BATCH", Path(__file__).resolve().parents[1] / "growth" / "ig-correction-1126.json"))
        if not batch.exists():
            self.skipTest("batch file not copied in yet")   # only after the README step 1
        name, items = C.load_batch(batch)
        self.assertEqual(len(items), 8)
        for it in items:
            bad = [p for p in C.text_problems(it) if p != "in-locale review not passed"]
            self.assertEqual(bad, [], it["shortcode"])


class RunTest(unittest.TestCase):
    def setUp(self):
        self.state = {"done": {}, "failed": {}}
        self.saved = []

    def go(self, items, client, **kw):
        kw.setdefault("apply", True)
        return C.run(client, "b", items, self.state, sleeper=lambda s: None, save=lambda s: self.saved.append(json.dumps(s)),
                     log=lambda m: None, now=lambda: NOW, **kw)

    def test_check_writes_nothing(self):
        items = [item()]
        f = fake_for(items)
        rows = self.go(items, f, apply=False)
        self.assertEqual(rows[0]["status"], "ready")
        self.assertEqual(f.posts, [])

    def test_apply_comments_once_and_reads_back(self):
        items = [item(), item(mid="18095495306264824", sc="De3me3hFYyh")]
        f = fake_for(items)
        rows = self.go(items, f)
        self.assertEqual([r["status"] for r in rows], ["commented", "commented"])
        self.assertTrue(all(r["verified"] for r in self.state["done"].values()))
        self.assertTrue(self.saved)   # receipt saved
        again = self.go(items, f)
        self.assertEqual([r["status"] for r in again], ["done_before", "done_before"])
        self.assertEqual(len(f.posts), 2)

    def test_not_our_post_or_wrong_permalink_is_refused(self):
        items = [item()]
        self.assertTrue(self.go(items, fake_for(items, owner="someone"))[0]["status"].startswith("refused"))
        wrong = fake_for(items, permalink="https://www.instagram.com/p/OTHER123/")
        self.assertTrue(self.go(items, wrong)[0]["status"].startswith("refused"))
        self.assertEqual(self.state["done"], {})

    def test_unverified_when_the_count_does_not_move(self):
        items = [item()]
        rows = self.go(items, fake_for(items, hide=True))
        self.assertEqual(rows[0]["status"], "commented_unverified")
        self.assertIn(items[0]["media_id"], self.state["done"])   # never written a second time

    def test_a_write_error_stops_the_run(self):
        items = [item(), item(mid="18095495306264824", sc="De3me3hFYyh")]
        f = fake_for(items, fail_write=OP.ApiError(400, 1, "oops"))
        rows = self.go(items, f)
        self.assertTrue(rows[0]["status"].startswith("write_failed"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(self.state["failed"][items[0]["media_id"]]["n"], 1)

    def test_max_new_and_daily_cap(self):
        items = [item(mid=str(10 ** 8 + i), sc=f"Short{i}xx") for i in range(3)]
        rows = self.go(items, fake_for(items), max_new=2)
        self.assertEqual([r["status"] for r in rows][-1], "waits: max_new reached")
        self.state["done"] = {str(i): {"at": "2026-11-26T05:00:00Z"} for i in range(C.DAILY_CAP)}
        items2 = [item(mid="999999999", sc="Later999")]
        self.assertEqual(self.go(items2, fake_for(items2))[0]["status"], "waits: daily cap")

    def test_unknown_token_owner_fails_closed(self):
        items = [item()]
        f = fake_for(items, owner=None)
        f.username = None
        self.assertIn("unknown", self.go(items, f)[0]["status"])
        self.assertEqual(f.posts, [])

    def test_a_lost_write_answer_is_never_posted_again(self):
        items = [item(), item(mid="18095495306264824", sc="De3me3hFYyh")]
        f = fake_for(items, fail_write=TimeoutError("timed out"))
        rows = self.go(items, f)
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["status"].startswith("commented_unverified"))
        self.assertTrue(self.state["done"][items[0]["media_id"]]["uncertain"])
        f.fail_write = None
        self.assertEqual(self.go(items[:1], f)[0]["status"], "done_before")

    def test_batch_file_rejects_duplicates(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "b.json"
            p.write_text(json.dumps({"items": [item(), item()]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                C.load_batch(p)
            p.write_text(json.dumps({"items": [item(), item(mid="18095495306264824")]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                C.load_batch(p)


if __name__ == "__main__":
    unittest.main()
