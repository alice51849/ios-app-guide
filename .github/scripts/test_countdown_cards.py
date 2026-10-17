#!/usr/bin/env python3
"""Tests for countdown_cards.py (no network): every countdown post carries the download link."""
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ.setdefault("POST_QA_OFFLINE", "1")

import countdown_cards as C  # noqa: E402


def event(locale="zh-Hant"):
    return next(e for e in C.EVENTS if e["locale"] == locale)


def meta(e):
    return {"event": e["id"], "locale": e["locale"], "caption": "學測倒數\n每天一點點\n\n在 App Store 搜尋「CountDaysNow」"}


class CountdownLinksTest(unittest.TestCase):
    def test_instagram_and_telegram_texts_hold_the_full_urls(self):
        for locale in ("zh-Hant", "ko", "ja", "en"):
            e = event(locale)
            text = C.telegram_text(meta(e), e)
            store, _play = C.download_urls(e, "telegram")
            self.assertIn(store, text, locale)
            self.assertIn("ct=cd_tg", store)
            self.assertTrue(C.DL.has_download_link(text, store), locale)
            # Instagram (owner 2026-10-17): no URL; the profile-link line and #CountDaysNow instead.
            ig = C.instagram_text(meta(e), e)
            self.assertNotIn("https://", ig, locale)
            self.assertEqual(ig.splitlines()[-1].split()[0], "#CountDaysNow", locale)
            self.assertEqual([], C.DL.instagram_problems(ig, "CountDaysNow", locale=e["locale"]), locale)
        self.assertIn("📲 請到個人檔案（bio）的連結下載", C.instagram_text(meta(event()), event()))

    def test_qa_passes_the_real_texts_and_refuses_bare_ones(self):
        import post_qa
        e = event()
        for channel, missing in (("instagram", "profile-link line"), ("telegram", "download link")):
            self.assertFalse([p for p in C.qa_problems(meta(e), e, channel, online=False)
                              if "download link" in p or "profile-link" in p or "brand hashtag" in p], channel)
            bare = post_qa.card_problems("學測倒數\n連結在 bio", "zh-Hant", channel, store_url=C.store_url(e, "qa"),
                                         name="CountDaysNow", online=False)
            self.assertTrue(any(missing in p for p in bare), channel)

    def test_telegram_send_carries_the_link_in_the_caption_and_the_button(self):
        e = event()
        with mock.patch.object(C, "send_photo") as send:
            C.post_telegram("card.jpg", meta(e), e)
        self.assertIn(C.store_url(e, "tg"), send.call_args[0][1])
        self.assertIn("ct=cd_tg", send.call_args[0][2][0]["url"])
        self.assertEqual(send.call_args[1]["guard"][0], C.store_url(e, "tg"))

    def test_the_guard_adds_a_missing_link_and_refuses_when_none_is_known(self):
        e = event()
        text = C.guarded("bare", C.download_urls(e, "instagram"), 2200, "t")
        self.assertIn(C.store_url(e, "ig"), text)
        with self.assertRaises(C.DL.MissingDownloadLink):
            C.guarded("bare", ("", None), 2200, "t")
        self.assertEqual(C.guarded("bare", None, 2200, "t"), "bare")

    def test_a_threads_post_without_its_link_reply_does_not_make_the_run_repost(self):
        e = event()
        C.LINK_FAILURES.clear()
        C.LINK_FAILURES.append("m1")
        with mock.patch.object(sys, "argv", ["c", "post", "--card", "x.jpg"]), \
                mock.patch.object(C.Path, "read_text", return_value='{"event": "%s", "locale": "%s", "caption": "c"}' % (e["id"], e["locale"])), \
                mock.patch.object(C, "qa_problems", return_value=[]), mock.patch.object(C, "post_telegram"), \
                mock.patch.object(C, "post_threads"), mock.patch.object(C, "post_instagram"):
            self.assertEqual(C.main(), 0, "a red run is re-dispatched and posts the card twice")
        C.LINK_FAILURES.clear()


    def test_a_retry_does_not_double_a_reply_that_was_published_after_all(self):
        e = event()
        links = C.link_lines(e, "threads")
        calls = []

        def post(url, fields, timeout=60):
            calls.append(fields)
            if fields.get("reply_to_id") and len([c for c in calls if c.get("reply_to_id")]) == 1:
                raise RuntimeError("timeout")  # published on the platform, but the answer never came back
            return {"id": f"id{len(calls)}"}

        def get(url, timeout=60):
            if "/replies" in url:
                return {"data": [{"text": "\n".join(links), "is_reply_owned_by_me": True}]}
            return {"id": "u"}

        C.LINK_FAILURES.clear()
        with mock.patch.dict(os.environ, {"THREADS_TOKEN": "t", "THREADS_USER_ID": "u"}), mock.patch.object(C, "_get", side_effect=get), \
                mock.patch.object(C, "_post", side_effect=post), mock.patch.object(C.time, "sleep"), \
                mock.patch("threads_series.has_room", return_value=True):
            C.threads_image("https://x/card.jpg", "Head", links)
        self.assertEqual(len([c for c in calls if c.get("reply_to_id")]), 1, "no second reply once ours is found")
        self.assertEqual(C.LINK_FAILURES, [])

    def test_a_retry_that_cannot_look_does_not_post_a_second_reply(self):
        e = event()
        links = C.link_lines(e, "threads")
        calls = []

        def post(url, fields, timeout=60):
            calls.append(fields)
            if fields.get("reply_to_id"):
                raise RuntimeError("timeout")
            return {"id": f"id{len(calls)}"}

        def get(url, timeout=60):
            if "/replies" in url:
                raise RuntimeError("down")
            return {"id": "u"}

        C.LINK_FAILURES.clear()
        with mock.patch.dict(os.environ, {"THREADS_TOKEN": "t", "THREADS_USER_ID": "u"}), mock.patch.object(C, "_get", side_effect=get), \
                mock.patch.object(C, "_post", side_effect=post), mock.patch.object(C.time, "sleep"), \
                mock.patch("threads_series.has_room", return_value=True), mock.patch("sys.stdout"):
            C.threads_image("https://x/card.jpg", "Head", links)
        self.assertEqual(len([c for c in calls if c.get("reply_to_id")]), 1, "a second reply could double the first")
        self.assertEqual(len(C.LINK_FAILURES), 1, "and the missing link is flagged for the sweeper")
        C.LINK_FAILURES.clear()

    def test_a_failed_publish_publishes_the_same_container_again_after_the_wait(self):
        e = event()
        links = C.link_lines(e, "threads")
        calls, waits = [], []

        def post(url, fields, timeout=60):
            calls.append((url.rsplit("/", 1)[-1], dict(fields)))
            if url.endswith("threads_publish") and fields.get("creation_id") == "reply-1" and sum(
                    1 for u, f in calls if f.get("creation_id") == "reply-1") < 2:
                raise RuntimeError("HTTP 400 (#24) The requested resource does not exist")   # not ready yet
            return {"id": "reply-1" if "reply_to_id" in fields else f"id{len(calls)}"}

        def get(url, timeout=60):
            return {"data": []} if "/replies" in url else {"id": "u"}

        C.LINK_FAILURES.clear()
        with mock.patch.dict(os.environ, {"THREADS_TOKEN": "t", "THREADS_USER_ID": "u"}), mock.patch.object(C, "_get", side_effect=get), \
                mock.patch.object(C, "_post", side_effect=post), mock.patch.object(C.time, "sleep", side_effect=waits.append), \
                mock.patch("threads_series.has_room", return_value=True):
            C.threads_image("https://x/card.jpg", "Head", links)
        self.assertEqual(C.LINK_FAILURES, [])
        self.assertEqual(1, len([f for _u, f in calls if f.get("reply_to_id")]), "one container for the reply")
        self.assertEqual(2, len([f for _u, f in calls if f.get("creation_id") == "reply-1"]), "published again")
        self.assertIn(C.REPLY_WAIT, waits)

    def test_an_existing_reply_with_another_campaign_token_still_counts(self):
        e = event()
        links = C.link_lines(e, "threads")
        retargeted = [line.replace("ct=", "ct=other_") for line in links]
        with mock.patch.object(C, "_get", return_value={"data": [{"text": "\n".join(retargeted), "is_reply_owned_by_me": True}]}):
            self.assertTrue(C.own_link_reply_exists("api", "t", "m", links))


if __name__ == "__main__":
    unittest.main()
