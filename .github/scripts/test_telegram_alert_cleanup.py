"""Unit tests for telegram_alert_cleanup.py (no network): only reviewed, still-internal alerts are deleted."""
from __future__ import annotations

import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import telegram_alert_cleanup as tc  # noqa: E402

LIST = HERE.parent / "growth" / "telegram_alert_cleanup_2026-10-18.json"
NEW_RED = "🔴 外宣線變紅（ios-app-guide）：新增 5 條\n\n• geo-daily.yml（workflow）：已 51.7 小時沒有新鮮成功"
OLD = "line-health 🔴 2026-09-07T05:09:55Z\n- geo-daily.yml: last 2026-09-06T04:19:25Z (retriggered)"
PROMO = "✨ 每日全 App 精選｜4 款\nhttps://apps.apple.com/app/id6754218117?ct=telegram"


def page(text: str | None) -> str:
    if text is None:
        return '<div class="tgme_widget_message_error" dir="auto">Post not found</div>'
    body = text.replace("🔴", '<i class="emoji"><b>🔴</b></i>').replace("\n", "<br/>")
    return f'<div class="tgme_widget_message_text js-message_text" dir="auto">{body}</div>'


def doc(*items):
    items = [{"id": i, "time": "2026-10-17T00:00:00+00:00", "template": "x", "text_60": t[:60]} for i, t in items]
    return {"schema": tc.SCHEMA, "count": len(items), "ids": [i["id"] for i in items], "items": items}


def write(d: dict) -> tuple[Path, str]:
    path = Path(tempfile.mkdtemp()) / "list.json"
    path.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


class Fake:
    def __init__(self, live: dict[int, str | None], refuse: set[int] = frozenset()):
        self.live, self.refuse, self.deleted = dict(live), set(refuse), []

    def preview(self, message_id):
        return tc.parse_preview(page(self.live.get(message_id)))

    def delete(self, token, chat_id, message_id):
        if message_id in self.refuse:
            return False, "Bad Request: message can't be deleted"
        self.deleted.append(message_id)
        self.live[message_id] = None
        return True, "ok"


class FakeEdit(Fake):
    def __init__(self, live, refuse=frozenset(), stale_reads: int = 0):
        super().__init__(live, refuse)
        self.edited, self.stale_reads = [], stale_reads
        self.old = {}

    def preview(self, message_id):
        if message_id in self.old and self.stale_reads > 0:
            self.stale_reads -= 1  # the public preview is still cached
            return tc.parse_preview(page(self.old[message_id]))
        return tc.parse_preview(page(self.live.get(message_id)))

    def edit(self, token, chat_id, message_id):
        if message_id in self.refuse:
            return False, "Bad Request: message can't be edited"
        self.edited.append(message_id)
        self.old[message_id] = self.live[message_id]
        self.live[message_id] = tc.NEUTRAL_TEXT
        return True, "ok"


class TemplateTests(unittest.TestCase):
    def test_internal_templates_match_and_promo_does_not(self):
        self.assertEqual("line_alert.py:new_red", tc.template_of(NEW_RED))
        self.assertEqual("line_watchdog.py:telegram_alert", tc.template_of(OLD))
        self.assertEqual("line_alert.py:recovered", tc.template_of("🟢 外宣線全部恢復新鮮（00_GrowthEngine）\n\n恢復：post.yml"))
        self.assertIsNone(tc.template_of(PROMO))
        self.assertIsNone(tc.template_of("best app to track line-health 🔴 habits"))

    def test_preview_parsing_reads_text_and_missing_posts(self):
        self.assertEqual({"state": "present", "text": NEW_RED}, tc.parse_preview(page(NEW_RED)))
        self.assertEqual("missing", tc.parse_preview(page(None))["state"])
        self.assertEqual("unreadable", tc.parse_preview("<html>rate limited</html>")["state"])


class ListTests(unittest.TestCase):
    def test_committed_list_is_well_formed_and_alert_only(self):
        d = tc.load_list(LIST, hashlib.sha256(LIST.read_bytes()).hexdigest())
        self.assertEqual(d["count"], len(d["ids"]))
        self.assertTrue(all(tc.template_of(i["text_60"], tc.TEMPLATES_60) for i in d["items"]))

    def test_wrong_digest_is_refused(self):
        path, _ = write(doc((5, NEW_RED)))
        with self.assertRaises(SystemExit):
            tc.load_list(path, "0" * 64)

    def test_a_promo_item_in_the_list_refuses_the_whole_list(self):
        path, digest = write(doc((5, NEW_RED), (6, PROMO)))
        with self.assertRaises(SystemExit) as caught:
            tc.load_list(path, digest)
        self.assertIn("6", str(caught.exception))

    def test_ids_count_mismatch_is_refused(self):
        d = doc((5, NEW_RED))
        d["ids"] = [5, 6]
        path, digest = write(d)
        with self.assertRaises(SystemExit):
            tc.load_list(path, digest)


class RunTests(unittest.TestCase):
    def test_plan_deletes_nothing(self):
        fake = Fake({5: NEW_RED})
        out = tc.run(doc((5, NEW_RED)), token="t", chat_id="c", apply=False, preview=fake.preview,
                     delete=fake.delete, settle=0)
        self.assertEqual({"would_delete": 1}, out["counts"])
        self.assertEqual([], fake.deleted)

    def test_apply_deletes_alerts_and_reads_them_back(self):
        fake = Fake({5: NEW_RED, 6: OLD})
        out = tc.run(doc((5, NEW_RED), (6, OLD)), token="t", chat_id="c", apply=True, preview=fake.preview,
                     delete=fake.delete, settle=0)
        self.assertEqual({"deleted": 2}, out["counts"])
        self.assertEqual([5, 6], fake.deleted)
        self.assertEqual(["missing", "missing"], [r["after"] for r in out["results"]])

    def test_live_text_that_is_not_an_alert_is_never_deleted(self):
        fake = Fake({5: PROMO})
        out = tc.run(doc((5, NEW_RED)), token="t", chat_id="c", apply=True, preview=fake.preview,
                     delete=fake.delete, settle=0)
        self.assertEqual({"refused_not_alert": 1}, out["counts"])
        self.assertEqual([], fake.deleted)

    def test_unreadable_preview_is_not_deleted_and_gone_posts_are_skipped(self):
        fake = Fake({6: None})
        fake.preview = lambda i: {"state": "unreadable", "text": ""} if i == 5 else tc.parse_preview(page(None))
        out = tc.run(doc((5, NEW_RED), (6, OLD)), token="t", chat_id="c", apply=True, preview=fake.preview,
                     delete=fake.delete, settle=0)
        self.assertEqual({"refused_unreadable": 1, "already_gone": 1}, out["counts"])
        self.assertEqual([], fake.deleted)

    def test_bot_refusal_is_reported_with_telegrams_reason(self):
        fake = Fake({5: OLD}, refuse={5})
        out = tc.run(doc((5, OLD)), token="t", chat_id="c", apply=True, preview=fake.preview,
                     delete=fake.delete, settle=0)
        self.assertEqual("delete_failed", out["results"][0]["result"])
        self.assertIn("can't be deleted", out["results"][0]["detail"])

    def test_edit_neutralises_alerts_and_reads_them_back(self):
        fake = FakeEdit({5: NEW_RED, 6: OLD})
        out = tc.run(doc((5, NEW_RED), (6, OLD)), token="t", chat_id="c", apply=False, edit=True,
                     preview=fake.preview, delete=fake.delete, edit_fn=fake.edit, settle=0, pace=0)
        self.assertEqual({"edited": 2}, out["counts"])
        self.assertEqual([5, 6], fake.edited)
        self.assertEqual([], fake.deleted)
        self.assertEqual(["neutral", "neutral"], [r["after"] for r in out["results"]])
        self.assertEqual({5: tc.NEUTRAL_TEXT, 6: tc.NEUTRAL_TEXT}, fake.live)

    def test_edit_never_touches_promo_or_gone_or_already_neutral_posts(self):
        fake = FakeEdit({5: PROMO, 6: None, 7: tc.NEUTRAL_TEXT})
        out = tc.run(doc((5, NEW_RED), (6, OLD), (7, OLD)), token="t", chat_id="c", apply=False, edit=True,
                     preview=fake.preview, delete=fake.delete, edit_fn=fake.edit, settle=0, pace=0)
        self.assertEqual({"refused_not_alert": 1, "already_gone": 1, "already_neutral": 1}, out["counts"])
        self.assertEqual([], fake.edited)
        self.assertEqual(PROMO, fake.live[5])

    def test_edit_waits_out_a_cached_preview_and_flags_one_that_never_updates(self):
        fake = FakeEdit({5: OLD}, stale_reads=2)
        out = tc.run(doc((5, OLD)), token="t", chat_id="c", apply=False, edit=True, preview=fake.preview,
                     delete=fake.delete, edit_fn=fake.edit, settle=0, pace=0, readback_rounds=4)
        self.assertEqual({"edited": 1}, out["counts"])
        fake = FakeEdit({5: OLD}, stale_reads=99)
        out = tc.run(doc((5, OLD)), token="t", chat_id="c", apply=False, edit=True, preview=fake.preview,
                     delete=fake.delete, edit_fn=fake.edit, settle=0, pace=0, readback_rounds=3)
        self.assertEqual({"edited_but_not_read_back": 1}, out["counts"])

    def test_edit_refusal_is_reported(self):
        fake = FakeEdit({5: OLD}, refuse={5})
        out = tc.run(doc((5, OLD)), token="t", chat_id="c", apply=False, edit=True, preview=fake.preview,
                     delete=fake.delete, edit_fn=fake.edit, settle=0, pace=0)
        self.assertEqual("edit_failed", out["results"][0]["result"])
        self.assertIn("can't be edited", out["results"][0]["detail"])

    def test_edit_message_sends_only_the_neutral_text_and_waits_out_flood_control(self):
        bodies, replies = [], [
            {"ok": False, "error_code": 429, "description": "Too Many Requests: retry after 3",
             "parameters": {"retry_after": 3}},
            {"ok": True, "result": {"message_id": 5, "text": tc.NEUTRAL_TEXT}},
        ]

        class Response(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        def fake_urlopen(request, timeout=20):
            bodies.append((request.full_url, request.data.decode()))
            return Response(json.dumps(replies.pop(0)).encode())

        slept = []
        with mock.patch.object(tc.urllib.request, "urlopen", fake_urlopen):
            ok, detail = tc.edit_message("tok", "-100123", 5, sleep=slept.append)
        self.assertEqual((True, "ok"), (ok, detail))
        self.assertEqual([4.0], slept)
        self.assertEqual(2, len(bodies))
        for url, body in bodies:
            self.assertTrue(url.endswith("/editMessageText"))
            fields = dict(tc.urllib.parse.parse_qsl(body))
            self.assertEqual({"chat_id": "-100123", "message_id": "5", "text": tc.NEUTRAL_TEXT,
                              "disable_web_page_preview": "true"}, fields)

    def test_edit_message_treats_not_modified_as_done_and_unconfirmed_text_as_failure(self):
        class Response(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

        for reply, expected in (
            ({"ok": False, "error_code": 400, "description": "Bad Request: message is not modified"},
             (True, "not_modified")),
            ({"ok": True, "result": {"message_id": 5, "text": "something else"}},
             (False, "edited text not confirmed")),
        ):
            with mock.patch.object(tc.urllib.request, "urlopen",
                                   lambda request, timeout=20, r=reply: Response(json.dumps(r).encode())):
                self.assertEqual(expected, tc.edit_message("tok", "-100123", 5, sleep=lambda s: None))

    def test_neutral_text_is_not_promo_copy(self):
        self.assertEqual("（此訊息已移除）", tc.NEUTRAL_TEXT)
        self.assertNotIn("http", tc.NEUTRAL_TEXT)
        self.assertIsNone(tc.template_of(tc.NEUTRAL_TEXT))

    def test_cli_edit_mode_never_prints_the_secrets(self):
        path, digest = write(doc((5, OLD)))
        fake = FakeEdit({5: OLD})
        buffer = io.StringIO()
        env = {"TELEGRAM_BOT_TOKEN": "SECRET-TOKEN", "TELEGRAM_CHAT_ID": "SECRET-CHAT", "GITHUB_STEP_SUMMARY": ""}
        with mock.patch.dict("os.environ", env), mock.patch.object(tc, "fetch_preview", fake.preview), \
                mock.patch.object(tc, "edit_message", fake.edit), mock.patch.object(tc, "delete_message", fake.delete), \
                mock.patch.object(tc.time, "sleep"), redirect_stdout(buffer):
            rc = tc.main(["--list", str(path), "--confirm", digest, "--mode", "edit"])
        self.assertEqual(0, rc)
        self.assertNotIn("SECRET", buffer.getvalue())
        self.assertIn("id 5: edited", buffer.getvalue())
        self.assertEqual([5], fake.edited)
        self.assertEqual([], fake.deleted)

    def test_cli_never_prints_the_secrets(self):
        path, digest = write(doc((5, OLD)))
        fake = Fake({5: OLD}, refuse={5})
        buffer = io.StringIO()
        env = {"TELEGRAM_BOT_TOKEN": "SECRET-TOKEN", "TELEGRAM_CHAT_ID": "SECRET-CHAT", "GITHUB_STEP_SUMMARY": ""}
        with mock.patch.dict("os.environ", env), mock.patch.object(tc, "fetch_preview", fake.preview), \
                mock.patch.object(tc, "delete_message", fake.delete), mock.patch.object(tc.time, "sleep"), \
                redirect_stdout(buffer):
            tc.main(["--list", str(path), "--confirm", digest, "--mode", "apply"])
        self.assertNotIn("SECRET", buffer.getvalue())
        self.assertIn("delete_failed", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
