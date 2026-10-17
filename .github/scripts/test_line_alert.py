"""Unit tests for line_alert.py: state-change Telegram alerts with a dedupe state file (no network)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import line_alert as la  # noqa: E402

NOW = 1_800_000_000.0  # 2027-01-15T08:00:00Z
H = la.HOUR


def row(line, fresh, *, kind="workflow", hours_ago=30.0, window=24, action="retriggered", note=""):
    return {"line": line, "kind": kind, "fresh": fresh, "last_success": la.iso(NOW - hours_ago * H),
            "max_age_hours": window, "action": action, "note": note}


def report(*rows):
    return {"judged_at": la.iso(NOW), "rows": list(rows)}


class Harness:
    def __init__(self):
        self.dir = Path(tempfile.mkdtemp())
        self.report = self.dir / "line-health.json"
        self.state = self.dir / "state" / "state.json"
        self.sent: list[str] = []
        self.fail = False

    def post(self, token, chat_id, text):
        if self.fail:
            raise OSError("network down")
        self.sent.append(text)
        return len(self.sent)

    def run(self, rep, *, token="tok", chat="chat", now=NOW):
        if rep is None:
            self.report.unlink(missing_ok=True)
        else:
            self.report.write_text(json.dumps(rep), encoding="utf-8")
        return la.run(self.report, self.state, label="00_GrowthEngine", run_url="https://x/runs/1",
                      now=now, token=token, chat_id=chat, post=self.post)


class StateChangeTests(unittest.TestCase):
    def test_new_red_line_is_sent_once_then_deduped(self):
        h = Harness()
        first = h.run(report(row("post.yml", False), row("nostr.yml", True)))
        self.assertEqual(("sent", "new_red", ["post.yml"]), (first["status"], first["kind"], first["new_red"]))
        self.assertEqual(1, len(h.sent))
        again = h.run(report(row("post.yml", False, hours_ago=42), row("nostr.yml", True)), now=NOW + 12 * H)
        self.assertEqual(("no_state_change", ["post.yml"]), (again["status"], again["still_red"]))
        self.assertEqual(1, len(h.sent), "the same red line must not be notified twice")

    def test_another_line_turning_red_sends_only_the_new_one(self):
        h = Harness()
        h.run(report(row("post.yml", False), row("nostr.yml", True)))
        out = h.run(report(row("post.yml", False), row("nostr.yml", False, action="circuit_open")))
        self.assertEqual((["nostr.yml"], ["post.yml"]), (out["new_red"], out["still_red"]))
        text = h.sent[-1]
        self.assertIn("nostr.yml", text.split("仍紅")[0])
        self.assertIn("仍紅（之前已通知）：post.yml", text)
        self.assertIn("熔斷", text)

    def test_all_green_again_sends_one_recovery_then_silence(self):
        h = Harness()
        h.run(report(row("post.yml", False)))
        out = h.run(report(row("post.yml", True)))
        self.assertEqual(("sent", "recovered", ["post.yml"]), (out["status"], out["kind"], out["recovered"]))
        self.assertIn("全部恢復", h.sent[-1])
        quiet = h.run(report(row("post.yml", True)))
        self.assertEqual("no_state_change", quiet["status"])
        self.assertEqual(2, len(h.sent))

    def test_partial_recovery_is_silent_but_forgets_the_healed_line(self):
        h = Harness()
        h.run(report(row("a.yml", False), row("b.yml", False)))
        out = h.run(report(row("a.yml", True), row("b.yml", False)))
        self.assertEqual(("no_state_change", ["a.yml"]), (out["status"], out["recovered"]))
        self.assertEqual(1, len(h.sent))
        relapse = h.run(report(row("a.yml", False), row("b.yml", False)))
        self.assertEqual(["a.yml"], relapse["new_red"], "a line that healed and broke again is news")

    def test_all_green_from_a_clean_state_sends_nothing(self):
        h = Harness()
        out = h.run(report(row("post.yml", True)))
        self.assertEqual(("no_state_change", "none"), (out["status"], out["kind"]))
        self.assertEqual([], h.sent)
        self.assertTrue(h.state.exists(), "the state file is always written so the cache can save it")


class DeliveryTests(unittest.TestCase):
    def test_missing_secrets_keep_the_change_pending(self):
        h = Harness()
        out = h.run(report(row("post.yml", False)), token="", chat="")
        self.assertEqual(("secrets_missing", False), (out["status"], out["state_advanced"]))
        self.assertEqual({}, la.load_state(h.state)["red"])
        later = h.run(report(row("post.yml", False)))
        self.assertEqual(("sent", ["post.yml"]), (later["status"], later["new_red"]))

    def test_failed_send_is_retried_next_run(self):
        h = Harness()
        h.fail = True
        out = h.run(report(row("post.yml", False)))
        self.assertEqual(("send_failed", False), (out["status"], out["state_advanced"]))
        h.fail = False
        self.assertEqual("sent", h.run(report(row("post.yml", False)))["status"])

    def test_missing_report_means_the_watchdog_itself_is_red(self):
        h = Harness()
        out = h.run(None)
        self.assertEqual([la.SELF_LINE], out["new_red"])
        self.assertIn("Self-test", h.sent[-1])
        healed = h.run(report(row("post.yml", True)))
        self.assertEqual(("recovered", [la.SELF_LINE]), (healed["kind"], healed["recovered"]))

    def test_corrupt_state_is_a_clean_slate_not_a_crash(self):
        h = Harness()
        h.state.parent.mkdir(parents=True)
        h.state.write_text("{not json", encoding="utf-8")
        self.assertEqual("sent", h.run(report(row("post.yml", False)))["status"])

    def test_cli_never_prints_the_secrets(self):
        h = Harness()
        h.report.write_text(json.dumps(report(row("post.yml", True))), encoding="utf-8")
        import io
        from contextlib import redirect_stdout
        from unittest import mock
        buffer = io.StringIO()
        with mock.patch.dict("os.environ", {"TELEGRAM_BOT_TOKEN": "SECRET-TOKEN", "TELEGRAM_CHAT_ID": "SECRET-CHAT",
                                            "GITHUB_STEP_SUMMARY": ""}), redirect_stdout(buffer):
            code = la.main(["--report", str(h.report), "--state", str(h.state), "--label", "x",
                            "--outcome", str(h.dir / "outcome.json")])
        self.assertEqual(0, code)
        output = buffer.getvalue() + (h.dir / "outcome.json").read_text(encoding="utf-8")
        self.assertNotIn("SECRET", output)
        self.assertIn("no_state_change", output)


class MessageTests(unittest.TestCase):
    def test_message_says_which_line_how_stale_and_what_to_do(self):
        text = la.plan(report(row("post.yml", False, hours_ago=31.5, window=24)), {"red": {}}, NOW,
                       label="threads-autopilot", run_url="https://x/runs/9")["message"]
        self.assertIn("post.yml", text)
        self.assertIn("31.5 小時沒有新鮮成功", text)
        self.assertIn("容許 24 小時", text)
        self.assertIn("建議：", text)
        self.assertIn("自動重派", text)
        self.assertIn("https://x/runs/9", text)
        self.assertIn("threads-autopilot", text)

    def test_runner_offline_points_to_the_local_mac(self):
        rep = report(row("growth_runner_online", False, kind="evidence", action="none", window=2))
        text = la.plan(rep, {"red": {}}, NOW, label="ge")["message"]
        self.assertIn("Mac", text)
        self.assertIn("runner", text)

    def test_never_seen_success_and_slot_rows_get_their_own_wording(self):
        never = row("hook-shorts.yml@00:30", False, kind="slot", action="none")
        never["last_success"] = "never"
        text = la.plan(report(never), {"red": {}}, NOW, label="ge")["message"]
        self.assertIn("查不到任何新鮮的成功紀錄", text)
        self.assertIn("只監看", text)

    def test_long_messages_are_capped_for_telegram(self):
        rows = [row(f"line-{i:03d}.yml", False, note="x" * 150) for i in range(80)]
        text = la.plan(report(*rows), {"red": {}}, NOW, label="ge")["message"]
        self.assertLessEqual(len(text), la.MAX_TEXT)

    def test_every_known_action_has_advice(self):
        for action in ("retriggered", "would_retrigger", "wait_in_progress", "circuit_open",
                       "retrigger_budget_exhausted", "recovery_forbidden"):
            self.assertIn(action, la.ACTION_ADVICE)


if __name__ == "__main__":
    unittest.main()
