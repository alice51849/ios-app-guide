#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The shipped hand-written queue (telegram-manual-queue.json) row by row. Run it before every push that
touches the queue:

    POST_QA_OFFLINE=1 python3 -m pytest -q test_telegram_manual_queue.py

It is strict on purpose and is not part of the posting workflows: there a refused row is skipped with
::error:: and the automatic rotation posts (telegram_post.manual_queue), so a bad row never stops the line.
The mechanism itself is tested in test_social_posting.py (TelegramManualQueueTests) and in
telegram_post.py --self-test, which the posting workflows do run.
"""
import datetime as dt
import json
import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import social_post_common as common
import telegram_post

JELLYDAY = "6835673714"   # iOS still in review: no social post before its public page answers 200
METRO = "6819061896"   # iOS went free 2026-11-24 while rotation copy still says paid: held until re-sealed
SNAPPORT_APPS = {"6780575828", "6792856304"}
CLAIM_NEEDS_PAGE = "is not on the product page"   # read from the live page at send time, not offline


class ShippedManualQueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(telegram_post.MANUAL_QUEUE_PATH, encoding="utf-8") as handle:
            cls.data = json.load(handle)
        cls.pool = telegram_post.load_pool()
        cls.items, cls.refused = telegram_post.load_manual_queue(cls.pool)

    def test_every_shipped_row_is_postable(self):
        self.assertEqual({}, self.refused)
        self.assertEqual(len(self.data["posts"]), len(self.items))
        self.assertEqual(len(self.items), len({item["manual_id"] for item in self.items}))
        for item in self.items:
            with self.subTest(row=item["manual_id"]):
                self.assertIn(item["lang"], common.OFFICIAL_SOCIAL_LOCALES)
                self.assertIn(item["app"], telegram_post.CURRENT_ROSTER_APP_IDS)
                self.assertEqual(telegram_post._digest(item["text"]), item["review"]["text_sha256"])
                text = telegram_post.compose_text(item)
                if item.get("bundle"):  # a bundle row: its bundle link with the row token, no App / Play link
                    self.assertRegex(item["manual_id"], r"^bundle_(lumi|lang|travel)_tg_[a-z]{2,4}_d[0-9]{1,2}$")
                    self.assertIn(item["app"], telegram_post._bundle_members(item["bundle"]))
                    self.assertRegex(text, r"/app-bundle/id[0-9]+\?pt=118326163&ct=" + item["manual_id"] + "&mt=8")
                    self.assertNotIn(f"/app/id{item['app']}", text)
                    self.assertNotIn("play.google.com", text)
                else:
                    self.assertRegex(item["manual_id"], r"^tg_[a-z0-9_]{1,27}$")
                    self.assertIn(f"/id{item['app']}?pt=118326163&ct={item['manual_id']}&mt=8", text)
                self.assertEqual([], telegram_post.download_link_problems(item, text))
                self.assertLessEqual(len(text), telegram_post.TG_CAPTION_MAX)

    def test_the_words_pass_post_qa(self):
        with mock.patch.dict(os.environ, {"POST_QA_OFFLINE": "1"}):
            for item in self.items:
                problems = [p for p in telegram_post.manual_qa_problems(item) if CLAIM_NEEDS_PAGE not in p]
                with self.subTest(row=item["manual_id"]):
                    self.assertEqual([], problems)

    def test_jellyday_stays_out_until_its_ios_page_is_public(self):
        # JellyDay is in the verified live roster (61 Apps) but stays held until a coordinator ruling lifts it:
        # the queue carries no JellyDay row and no row names it.
        self.assertIn(JELLYDAY, telegram_post.CURRENT_ROSTER_APP_IDS)
        self.assertIn(JELLYDAY, self.data["hold_apps"])
        self.assertIn(JELLYDAY, telegram_post.held_apps())
        self.assertFalse([item for item in self.items if item["app"] == JELLYDAY])
        self.assertFalse([row for row in self.data["posts"] if str(row.get("app")) == JELLYDAY])
        self.assertFalse([item for item in self.items if "jellyday" in item["text"].lower()])

    def test_metro_is_held_even_when_the_hold_file_is_unreadable(self):
        # Metro Time Helper copy still says paid / buy once while iOS is free: held from the rotation and the
        # manual queue, and an unreadable hold file still holds it (fail closed); other Apps are not held by it.
        self.assertIn(METRO, self.data["hold_apps"])
        self.assertIn(METRO, telegram_post.held_apps())
        self.assertIn(METRO, telegram_post.UNREADABLE_HOLD_FALLBACK)
        self.assertEqual({JELLYDAY, METRO}, set(telegram_post.UNREADABLE_HOLD_FALLBACK))

    def test_snapport_rows_name_no_removed_feature(self):
        for item in self.items:
            if item["app"] in SNAPPORT_APPS:
                with self.subTest(row=item["manual_id"]):
                    self.assertIsNone(telegram_post.MANUAL_BANNED_COPY[item["app"]].search(item["text"]))
        self.assertEqual(SNAPPORT_APPS, set(telegram_post.MANUAL_BANNED_COPY))

    def test_thirty_days_never_exceed_one_row_a_day_and_never_repeat_a_row(self):
        ledger, sends = {"receipts": {}, "intents": {}}, []
        start = dt.date(2026, 11, 22)
        for offset in range(30):
            for hour in telegram_post.SLOT_HOURS:
                slot = dt.datetime.combine(start + dt.timedelta(days=offset), dt.time(hour), tzinfo=dt.timezone.utc)
                now = slot + dt.timedelta(minutes=14)
                item = telegram_post.choose_manual(self.items, self.pool, ledger, now, qa=lambda _item: [])
                if item is None:
                    continue
                self.assertIn(item["lang"], telegram_post.TZ_LANGS[telegram_post._zone(hour)])
                digest = telegram_post._digest(telegram_post.compose_text(item))
                ledger["intents"][slot.isoformat()] = {
                    "slot": slot.isoformat(), "status": "confirmed", "app_store_id": item["app"],
                    "payload_digest": digest, "manual_id": item["manual_id"],
                }
                ledger["receipts"][f"LumiApps2026/{len(sends) + 1}"] = {
                    "app_store_id": item["app"], "payload_digest": digest, "timestamp": now.isoformat(),
                    "manual_id": item["manual_id"],
                }
                sends.append((slot.date(), item["manual_id"]))
        days = [day for day, _row in sends]
        self.assertEqual(len(days), len(set(days)), "more than one hand-written row in a UTC day")
        bundle_days = [day for day, row in sends if row.startswith("bundle_")]
        self.assertEqual(len(bundle_days), len(set(bundle_days)), "more than one bundle row in a UTC day")
        for item in self.items:
            if item.get("not_before"):
                day = next(day for day, row in sends if row == item["manual_id"])
                self.assertGreaterEqual(day.isoformat(), item["not_before"])
        self.assertEqual(sorted(item["manual_id"] for item in self.items), sorted(row for _day, row in sends))


if __name__ == "__main__":
    unittest.main()
