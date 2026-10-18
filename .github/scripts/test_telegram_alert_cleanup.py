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
