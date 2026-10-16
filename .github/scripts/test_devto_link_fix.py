#!/usr/bin/env python3
"""Tests for devto_link_fix.py (no network): an article without a download link gets one block, once."""
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("POST_QA_OFFLINE", "1")

import devto_link_fix as D  # noqa: E402
import link_backfill as B  # noqa: E402
import own_posts as OP  # noqa: E402
import download_links as DL  # noqa: E402

MOCHI = "6785004775"   # on Google Play in the Android snapshot
PLAIN = "6818607603"   # iOS only


class FakeDevto:
    def __init__(self, articles, fail_put=False):
        self.articles = {str(a["id"]): dict(a) for a in articles}
        self.puts, self.fail_put = [], fail_put

    def __call__(self, method, path, key, body=None, timeout=30):
        if method == "GET" and path.startswith("/articles/me/all"):
            return [{k: v for k, v in a.items() if k != "body_markdown"} for a in self.articles.values()]
        if method == "GET":
            return dict(self.articles[path.rsplit("/", 1)[1]])
        if method == "PUT":
            if self.fail_put:
                raise RuntimeError("HTTP 429 Too Many Requests")
            aid = path.rsplit("/", 1)[1]
            self.articles[aid]["body_markdown"] = body["article"]["body_markdown"]
            self.puts.append(aid)
            return {}
        raise AssertionError(path)


def finder():
    improvements = {"apps": [{"name": "Mochi: Cute Checklist", "key": "mochi", "app_store_id": MOCHI},
                             {"name": "UsageNow: AI Usage Tracker", "key": "usagenow", "app_store_id": PLAIN}]}
    return B.AppFinder(OP.Catalog(clips={}, posts=[], improvements=improvements))


def article(aid, title, body, published=True, date="2026-09-01"):
    return {"id": aid, "title": title, "description": "", "body_markdown": body, "published": published,
            "published_at": f"{date}T00:00:00Z", "url": f"https://dev.to/x/{aid}"}


class DevtoLinkFixTest(unittest.TestCase):
    def go(self, api, state=None, **kw):
        kw.setdefault("sleeper", lambda s: None)
        kw.setdefault("log", lambda *a: None)
        state = state if state is not None else B.load_state(Path("/nonexistent"))
        return D.run("key", finder(), state, call=api, **kw), state

    def test_an_article_without_the_link_gets_one_block_with_both_stores(self):
        api = FakeDevto([article(1, "Why I built Mochi", "Mochi: Cute Checklist is a calm to-do app.")])
        rows, state = self.go(api, apply=True)
        self.assertEqual(rows[0]["status"], "backfilled")
        body = api.articles["1"]["body_markdown"]
        self.assertTrue(body.startswith("Mochi: Cute Checklist is a calm to-do app."))
        self.assertTrue(DL.has_download_link(body, f"https://apps.apple.com/app/id{MOCHI}",
                                             "https://play.google.com/store/apps/details?id=com.alice51849.MochiTodo"))
        self.assertIn("ct=bf_dv", body)
        self.assertTrue(state["done"]["devto"]["1"]["verified"])
        rows2, _ = self.go(api, state, apply=True)   # a second sweep edits nothing
        self.assertEqual(api.puts, ["1"])
        self.assertEqual(rows2[0]["status"], "ok_caption")

    def test_an_article_that_links_its_store_page_is_left_alone(self):
        api = FakeDevto([article(2, "Mochi", f"Get it: https://apps.apple.com/app/id{MOCHI}")])
        rows, _ = self.go(api, apply=True)
        self.assertEqual(rows[0]["status"], "ok_caption")
        self.assertEqual(api.puts, [])

    def test_unknown_or_ambiguous_and_draft_articles_are_listed_not_touched(self):
        api = FakeDevto([article(3, "Notes on sleep", "No app named here."),
                         article(4, "Two apps", "Mochi: Cute Checklist and UsageNow: AI Usage Tracker side by side"),
                         article(5, "Mochi draft", "Mochi: Cute Checklist", published=False)])
        rows, _ = self.go(api, apply=True)
        self.assertEqual(sorted(r["status"] for r in rows), ["draft_skipped", "unknown_app", "unknown_app"])
        self.assertEqual(api.puts, [])

    def test_ios_only_app_gets_the_app_store_link_only(self):
        api = FakeDevto([article(6, "UsageNow", "UsageNow: AI Usage Tracker keeps your limits in view")])
        self.go(api, apply=True)
        body = api.articles["6"]["body_markdown"]
        self.assertIn(f"id{PLAIN}", body)
        self.assertNotIn("play.google.com", body)

    def test_max_new_and_a_failed_edit_stop_the_run(self):
        arts = [article(10 + i, f"Mochi {i}", "Mochi: Cute Checklist", date=f"2026-09-0{i + 1}") for i in range(4)]
        api = FakeDevto(arts)
        self.go(api, apply=True, max_new=2)
        self.assertEqual(len(api.puts), 2)
        self.assertEqual(api.puts, ["13", "12"], "newest first")
        api = FakeDevto(arts, fail_put=True)
        rows, _ = self.go(api, apply=True, max_new=4)
        self.assertEqual([r["status"] for r in rows][:1], ["write_failed"])
        self.assertEqual(len(rows), 1, "the first error stops the run")


if __name__ == "__main__":
    unittest.main()
