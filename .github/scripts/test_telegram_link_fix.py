#!/usr/bin/env python3
"""Tests for telegram_link_fix.py: offline, no token, nothing is sent anywhere."""
import contextlib
import io
import json
import os
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import link_backfill as B  # noqa: E402
import own_posts as OP  # noqa: E402
import telegram_link_fix as T  # noqa: E402

IOS = "6773017109"   # lumibopomofo
CATALOG = OP.Catalog()
FIXES = {"9": ("lumibopomofo", "zh-Hant"), "3": ("lumibopomofo", "zh-Hant")}
PLAY = "https://play.google.com/store/apps/details?id=com.example.bopomofo&referrer=utm_source%3Dbf_tg%26utm_campaign%3Dbopomofo"


def reader(pages):
    return lambda mid: pages[mid]


class Bot:
    """Stands in for the Bot API: remembers every call, answers like editMessageReplyMarkup does."""

    def __init__(self, fail=None):
        self.calls, self.fail = [], fail

    def __call__(self, token, method, payload):
        self.calls.append((token, method, payload))
        if self.fail:
            raise RuntimeError(self.fail)
        return {"ok": True, "result": {"message_id": payload["message_id"], "reply_markup": payload["reply_markup"]}}


def fresh_state():
    return {"done": {}, "checked": {}, "failed": {}}


class TelegramLinkFixTest(unittest.TestCase):
    def setUp(self):
        self.pages = {"9": (["https://alice51849.github.io/ios-app-guide/x/"], "free zhuyin sheets"),
                      "3": (["https://alice51849.github.io/ios-app-guide/y/"], "channel test")}
        self.saved = []
        patcher = mock.patch.object(T, "android_apps", return_value={IOS: {"key": "bopomofo"}})
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(T, "play_store_url", return_value=PLAY)
        patcher.start()
        self.addCleanup(patcher.stop)

    def go(self, state=None, bot=None, apply=True, **kw):
        state = state or fresh_state()
        bot = bot or Bot()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rows = T.run("SECRET-TOKEN", "-100123", state, CATALOG, apply=apply, fixes=FIXES, read=reader(self.pages),
                         call=bot, sleeper=lambda s: None, save=lambda st: self.saved.append(json.dumps(st)), **kw)
        return rows, state, bot, out.getvalue()

    def test_audit_only_reads(self):
        rows, state, bot, _ = self.go(apply=False)
        self.assertEqual(["missing", "missing"], [r["status"] for r in rows])
        self.assertEqual([], bot.calls)
        self.assertEqual({}, state["done"])

    def test_apply_adds_the_app_store_and_play_buttons_and_reads_them_back(self):
        rows, state, bot, _ = self.go()
        self.assertEqual(["backfilled", "backfilled"], [r["status"] for r in rows])
        self.assertEqual(2, len(bot.calls))
        _token, method, payload = bot.calls[0]
        self.assertEqual("editMessageReplyMarkup", method)
        self.assertEqual({"chat_id", "message_id", "reply_markup"}, set(payload))   # the text is never sent
        row = payload["reply_markup"]["inline_keyboard"][0]
        self.assertEqual(2, len(row))
        self.assertIn(f"apps.apple.com/app/id{IOS}", row[0]["url"])
        self.assertIn("ct=telegram&", row[0]["url"])
        self.assertEqual(PLAY, row[1]["url"])  # play_store_url is mocked here
        for button in row:
            self.assertNotRegex(button["text"], r"(?i)free|pro\b|\$|價|免費|買斷|試用")
        self.assertTrue(all(v["verified"] for v in state["done"]["telegram"].values()))
        self.assertEqual({"3", "9"}, set(state["done"]["telegram"]))

    def test_iphone_only_app_gets_one_button(self):
        with mock.patch.object(T, "play_store_url", return_value=None):
            _rows, _state, bot, _ = self.go()
        row = bot.calls[0][2]["reply_markup"]["inline_keyboard"][0]
        self.assertEqual(1, len(row))

    def test_a_message_that_has_the_link_is_left_alone(self):
        self.pages["9"] = ([f"https://apps.apple.com/app/id{IOS}?pt=1&ct=x&mt=8"], "already")
        rows, _state, bot, _ = self.go()
        by_id = {r["id"]: r["status"] for r in rows}
        self.assertEqual("ok_caption", by_id["9"])
        self.assertEqual(["3"], [str(c[2]["message_id"]) for c in bot.calls])

    def test_only_once_per_message(self):
        _rows, state, _bot, _ = self.go()
        rows, _state, bot, _ = self.go(state=state)
        self.assertEqual(["ok_backfilled_earlier", "ok_backfilled_earlier"], [r["status"] for r in rows])
        self.assertEqual([], bot.calls)

    def test_same_buttons_already_there_counts_as_done(self):
        rows, state, _bot, _ = self.go(bot=Bot(fail="HTTP 400 Bad Request: message is not modified"))
        self.assertEqual(["backfilled", "backfilled"], [r["status"] for r in rows])
        self.assertTrue(all(v["verified"] for v in state["done"]["telegram"].values()))

    def test_a_failed_edit_stops_and_keeps_no_receipt(self):
        rows, state, bot, text = self.go(bot=Bot(fail="HTTP 403 bot was kicked"))
        self.assertEqual("write_failed", rows[0]["status"])
        self.assertEqual(1, len(bot.calls))   # stops at the first failure
        self.assertEqual({}, state["done"])
        self.assertNotIn("SECRET-TOKEN", text + json.dumps(rows))

    def test_nothing_is_edited_without_the_android_snapshot(self):
        with mock.patch.object(T, "android_apps", return_value={}):
            rows, state, bot, text = self.go()
        self.assertEqual("snapshot_missing", rows[0]["status"])
        self.assertEqual([], bot.calls)
        self.assertEqual({}, state["done"])
        self.assertIn("::error::", text)

    def test_only_listed_messages_are_ever_touched(self):
        rows, _state, bot, _ = self.go()
        self.assertEqual({"3", "9"}, {str(c[2]["message_id"]) for c in bot.calls})
        self.assertEqual({"3", "9"}, set(T.FIXES))

    def test_unreadable_preview_is_reported_not_edited(self):
        def broken(mid):
            raise LookupError("not on the page")
        out = io.StringIO()
        bot = Bot()
        with contextlib.redirect_stdout(out):
            rows = T.run("T", "c", fresh_state(), CATALOG, apply=True, fixes=FIXES, read=broken, call=bot,
                         sleeper=lambda s: None)
        self.assertTrue(all(r["status"].startswith("read_failed") for r in rows))
        self.assertEqual([], bot.calls)


class ApiErrorTest(unittest.TestCase):
    def test_http_error_never_carries_the_token(self):
        def opener(req, timeout=0):
            raise urllib.error.HTTPError(req.full_url, 403, "Forbidden", {}, io.BytesIO(b'{"description": "Forbidden: bot is not a member"}'))
        with self.assertRaises(RuntimeError) as ctx:
            T.api("SECRET-TOKEN", "editMessageReplyMarkup", {}, opener=opener)
        self.assertNotIn("SECRET-TOKEN", str(ctx.exception))
        self.assertIn("403", str(ctx.exception))

    def test_buttons_in_reads_the_answer(self):
        result = {"reply_markup": {"inline_keyboard": [[{"text": "a", "url": "https://x/1"}, {"text": "b", "url": "https://x/2"}]]}}
        self.assertEqual(["https://x/1", "https://x/2"], T.buttons_in(result))
        self.assertEqual([], T.buttons_in(None))

    def test_preview_finds_the_message_and_its_buttons(self):
        page = ('<div class="tgme_widget_message_wrap js-widget_message_wrap"><div class="tgme_widget_message" data-post="LumiApps2026/8">'
                '<div class="tgme_widget_message_text js-message_text">other</div></div></div>'
                '<div class="tgme_widget_message_wrap js-widget_message_wrap"><div class="tgme_widget_message" data-post="LumiApps2026/9">'
                '<div class="tgme_widget_message_text js-message_text">hello<br/>world <a href="https://example.org/a?x=1&amp;y=2">link</a></div>'
                '<a class="tgme_widget_message_inline_button url_button" href="https://apps.apple.com/app/id6773017109?pt=1&amp;ct=bf_tg&amp;mt=8">App Store</a>'
                '</div></div>')

        class Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return page.encode()
        hrefs, text = T.preview("9", opener=lambda req, timeout=0: Resp())
        self.assertIn("https://apps.apple.com/app/id6773017109?pt=1&ct=bf_tg&mt=8", hrefs)
        self.assertIn("hello world", text)
        with self.assertRaises(LookupError):
            T.preview("12", opener=lambda req, timeout=0: Resp())


class MainTest(unittest.TestCase):
    def test_apply_without_secrets_edits_nothing(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("TELEGRAM_")}
        out = io.StringIO()
        with mock.patch.dict(os.environ, env, clear=True), contextlib.redirect_stdout(out):
            self.assertEqual(0, T.main(["apply", "--report", os.devnull]))
        self.assertIn("nothing edited", out.getvalue())


if __name__ == "__main__":
    unittest.main()
