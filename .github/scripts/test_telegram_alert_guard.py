"""Unit tests for telegram_alert_guard.py (no network): internal messages never reach a public chat."""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import telegram_alert_guard as guard  # noqa: E402

PUBLIC = "-1002233445566"
PRIVATE = "123456789"


class FakeApi:
    def __init__(self, chat: dict | None = None, fail: str | None = None):
        self.chat = {"id": int(PRIVATE), "type": "private"} if chat is None else chat
        self.fail, self.calls = fail, []

    def __call__(self, token, method, payload):
        self.calls.append((method, dict(payload)))
        if self.fail == method:
            raise RuntimeError("Bad Request: chat not found")
        if method == "getChat":
            return self.chat
        return {"message_id": 42}

    @property
    def methods(self):
        return [method for method, _ in self.calls]


class TargetTests(unittest.TestCase):
    def test_missing_public_invalid_and_private_targets(self):
        self.assertEqual(guard.MISSING, guard.alert_target_problem(""))
        self.assertEqual(guard.MISSING, guard.alert_target_problem("   "))
        self.assertEqual(guard.PUBLIC, guard.alert_target_problem("@LumiApps2026"))
        self.assertEqual(guard.PUBLIC, guard.alert_target_problem("@any_private_looking_name"))
        self.assertEqual(guard.PUBLIC, guard.alert_target_problem(PUBLIC, ("", PUBLIC)))
        self.assertEqual(guard.PUBLIC, guard.alert_target_problem(" -4001 ", ("-4001",)))  # any id equal to public
        self.assertEqual(guard.INVALID, guard.alert_target_problem("LumiApps2026"))
        self.assertEqual(guard.INVALID, guard.alert_target_problem("t.me/LumiApps2026"))
        self.assertEqual(guard.INVALID, guard.alert_target_problem("--100"))
        for chat in (PRIVATE, "-4001234", "-1009988776655"):
            self.assertIsNone(guard.alert_target_problem(chat, ("", PUBLIC)), chat)

    def test_public_ids_come_from_both_public_env_names_only(self):
        env = {"TELEGRAM_PUBLIC_CHAT_ID": " -1001 ", "TELEGRAM_CHAT_ID": "-1002", "TELEGRAM_ALERT_CHAT_ID": "5"}
        self.assertEqual(("-1001", "-1002"), guard.public_chat_ids_from_env(env))
        self.assertEqual((), guard.public_chat_ids_from_env({}))

    def test_get_chat_answer_with_a_public_username_is_refused(self):
        self.assertEqual(guard.PUBLIC, guard.chat_info_problem({"type": "channel", "username": "LumiApps2026"}))
        self.assertEqual(guard.PUBLIC, guard.chat_info_problem({"type": "supergroup", "username": "somegroup"}))
        self.assertEqual(guard.PUBLIC, guard.chat_info_problem({"type": "private", "username": "lumiapps2026"}))
        self.assertIsNone(guard.chat_info_problem({"type": "private", "username": "owner_handle"}))
        self.assertIsNone(guard.chat_info_problem({"type": "channel", "title": "private alerts"}))
        self.assertIsNone(guard.chat_info_problem({"type": "group"}))


class SendTests(unittest.TestCase):
    def test_private_chat_gets_the_message(self):
        api = FakeApi()
        out = guard.send_internal_alert("🔴 test", token="tok", chat_id=PRIVATE, public_chat_ids=(PUBLIC,), api=api)
        self.assertEqual({"status": "sent", "sent": True, "message_id": 42}, out)
        self.assertEqual(["getChat", "sendMessage"], api.methods)
        self.assertEqual({"chat_id": PRIVATE, "text": "🔴 test", "disable_web_page_preview": True}, api.calls[1][1])

    def test_never_falls_back_to_the_public_chat_id(self):
        api = FakeApi()
        env = {"TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_CHAT_ID": PUBLIC}
        out = guard.send_internal_alert("🔴 test", env=env, api=api)
        self.assertEqual(guard.MISSING, out["status"])
        self.assertEqual([], api.calls)

    def test_public_targets_are_refused_before_any_api_call(self):
        for chat, public in (("@LumiApps2026", ()), (PUBLIC, (PUBLIC,))):
            api = FakeApi()
            out = guard.send_internal_alert("x", token="tok", chat_id=chat, public_chat_ids=public, api=api)
            self.assertEqual(guard.PUBLIC, out["status"])
            self.assertEqual([], api.calls)

    def test_alert_chat_equal_to_the_public_env_chat_is_refused(self):
        api = FakeApi()
        env = {"TELEGRAM_BOT_TOKEN": "tok", "TELEGRAM_ALERT_CHAT_ID": PUBLIC, "TELEGRAM_PUBLIC_CHAT_ID": PUBLIC}
        self.assertEqual(guard.PUBLIC, guard.send_internal_alert("x", env=env, api=api)["status"])
        self.assertEqual([], api.calls)

    def test_a_chat_that_turns_out_public_gets_nothing(self):
        api = FakeApi(chat={"type": "channel", "username": "LumiApps2026"})
        out = guard.send_internal_alert("x", token="tok", chat_id="-1005556667778", api=api)
        self.assertEqual(guard.PUBLIC, out["status"])
        self.assertEqual(["getChat"], api.methods)

    def test_unverifiable_chat_or_failed_send_is_a_failure_not_a_send(self):
        api = FakeApi(fail="getChat")
        self.assertEqual(guard.SEND_FAILED, guard.send_internal_alert("x", token="tok", chat_id=PRIVATE, api=api)["status"])
        self.assertEqual(["getChat"], api.methods)
        api = FakeApi(fail="sendMessage")
        self.assertEqual(guard.SEND_FAILED, guard.send_internal_alert("x", token="tok", chat_id=PRIVATE, api=api)["status"])

    def test_missing_token_or_text_sends_nothing(self):
        api = FakeApi()
        self.assertEqual(guard.SECRETS_MISSING,
                         guard.send_internal_alert("x", token="", chat_id=PRIVATE, api=api)["status"])
        self.assertEqual("nothing_to_send", guard.send_internal_alert("  ", token="t", chat_id=PRIVATE, api=api)["status"])
        self.assertEqual([], api.calls)

    def test_long_text_is_cut(self):
        api = FakeApi()
        guard.send_internal_alert("a" * 5000, token="tok", chat_id=PRIVATE, api=api)
        self.assertEqual(guard.MAX_TEXT, len(api.calls[1][1]["text"]))

    def test_post_alert_raises_refusals(self):
        with self.assertRaises(guard.AlertRefused) as caught:
            guard.post_alert("tok", "@LumiApps2026", "x", api=FakeApi())
        self.assertEqual(guard.PUBLIC, caught.exception.status)


class CliTests(unittest.TestCase):
    def cli(self, env: dict, text: str = "🔴 conversion broke") -> tuple[int, str, list]:
        path = Path(tempfile.mkdtemp()) / "alert.txt"
        path.write_text(text, encoding="utf-8")
        api = FakeApi()
        buffer = io.StringIO()
        with mock.patch.dict("os.environ", {**env, "GITHUB_STEP_SUMMARY": ""}, clear=True), \
                mock.patch.object(guard, "bot_api", api), redirect_stdout(buffer):
            code = guard.main(["--text-file", str(path), "--label", "conversion-guard"])
        return code, buffer.getvalue(), api.calls

    def test_cli_without_alert_chat_says_alert_chat_missing_and_sends_nothing(self):
        code, out, calls = self.cli({"TELEGRAM_BOT_TOKEN": "SECRET-TOKEN", "TELEGRAM_CHAT_ID": "-100999",
                                     "TELEGRAM_PUBLIC_CHAT_ID": "-100999"})
        self.assertEqual(0, code)
        self.assertIn("alert_chat_missing", out)
        self.assertEqual([], calls)
        self.assertNotIn("SECRET", out)
        self.assertNotIn("-100999", out)

    def test_cli_refuses_the_public_chat_loudly(self):
        code, out, calls = self.cli({"TELEGRAM_BOT_TOKEN": "SECRET-TOKEN", "TELEGRAM_ALERT_CHAT_ID": "-100999",
                                     "TELEGRAM_PUBLIC_CHAT_ID": "-100999"})
        self.assertEqual(1, code)
        self.assertIn("::error::", out)
        self.assertEqual([], calls)
        self.assertNotIn("SECRET", out)

    def test_cli_sends_to_the_private_alert_chat(self):
        code, out, calls = self.cli({"TELEGRAM_BOT_TOKEN": "SECRET-TOKEN", "TELEGRAM_ALERT_CHAT_ID": PRIVATE,
                                     "TELEGRAM_PUBLIC_CHAT_ID": "-100999"})
        self.assertEqual(0, code)
        self.assertEqual(["getChat", "sendMessage"], [method for method, _ in calls])
        self.assertEqual(PRIVATE, calls[1][1]["chat_id"])
        self.assertNotIn("SECRET", out)
        self.assertNotIn(PRIVATE, out)


if __name__ == "__main__":
    unittest.main()
