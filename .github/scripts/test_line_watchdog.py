"""Unit tests for line_watchdog.py with a scripted ``gh`` runner (no network)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import line_watchdog as wd  # noqa: E402

NOW = 1_800_000_000.0  # fixed clock
H = wd.HOUR


def run_at(offset_hours: float, conclusion="success", status="completed", run_id=1, actor="alice"):
    stamp = wd.iso(NOW - offset_hours * H)
    return {"id": run_id, "conclusion": conclusion, "status": status, "created_at": stamp,
            "updated_at": stamp, "actor": {"login": actor}}


class ScriptedGh(wd.Gh):
    """Answers gh calls from a table keyed by a recognisable argv fragment."""

    def __init__(self, table: dict[str, object]):
        super().__init__("owner/repo", runner=self._scripted)
        self.table = table
        self.calls: list[list[str]] = []

    def _scripted(self, argv: list[str]) -> str:
        self.calls.append(argv)
        joined = " ".join(argv)
        for key, value in self.table.items():
            if key in joined:
                return value if isinstance(value, str) else json.dumps(value)
        if argv[:2] in (["gh", "workflow"], ["gh", "label"]) or argv[:2] == ["gh", "issue"]:
            return "[]" if "list" in argv else ""
        raise AssertionError(f"unexpected gh call: {joined}")

    def dispatched(self) -> list[str]:
        return [argv[3] for argv in self.calls if argv[:3] == ["gh", "workflow", "run"]]


class WorkflowJudgementTests(unittest.TestCase):
    def test_recent_success_is_fresh_and_never_retriggers(self):
        gh = ScriptedGh({"workflows/post.yml/runs?per_page=30": {"workflow_runs": [run_at(2)]}})
        row = wd.judge_workflow(gh, "post.yml", 24, NOW, dispatch=True)
        self.assertTrue(row["fresh"])
        self.assertEqual([], gh.dispatched())

    def test_stale_workflow_is_retriggered_once_budget_allows(self):
        gh = ScriptedGh({
            "workflows/post.yml/runs?per_page=30&event": {"workflow_runs": [run_at(3, actor="github-actions[bot]")]},
            "workflows/post.yml/runs?per_page=30": {"workflow_runs": [run_at(30), run_at(40, conclusion="failure")]},
        })
        row = wd.judge_workflow(gh, "post.yml", 24, NOW, dispatch=True)
        self.assertFalse(row["fresh"])
        self.assertEqual("retriggered", row["action"])
        self.assertEqual(1, row["auto_retriggers_24h"])
        self.assertEqual(["post.yml"], gh.dispatched())

    def test_two_auto_retriggers_in_24h_exhaust_the_budget(self):
        bots = [run_at(3, actor="github-actions[bot]"), run_at(9, actor="github-actions[bot]"), run_at(5)]
        gh = ScriptedGh({
            "workflows/post.yml/runs?per_page=30&event": {"workflow_runs": bots},
            "workflows/post.yml/runs?per_page=30": {"workflow_runs": [run_at(30, conclusion="failure")]},
        })
        row = wd.judge_workflow(gh, "post.yml", 24, NOW, dispatch=True)
        self.assertEqual("retrigger_budget_exhausted", row["action"])
        self.assertEqual(2, row["auto_retriggers_24h"])
        self.assertEqual([], gh.dispatched())

    def test_in_progress_run_is_awaited_not_duplicated(self):
        gh = ScriptedGh({"workflows/post.yml/runs?per_page=30": {"workflow_runs": [
            run_at(0.2, conclusion=None, status="in_progress"), run_at(40)]}})
        row = wd.judge_workflow(gh, "post.yml", 24, NOW, dispatch=True)
        self.assertEqual("wait_in_progress", row["action"])
        self.assertEqual([], gh.dispatched())

    def test_failures_only_never_count_as_success(self):
        gh = ScriptedGh({
            "workflows/post.yml/runs?per_page=30&event": {"workflow_runs": []},
            "workflows/post.yml/runs?per_page=30": {"workflow_runs": [run_at(1, conclusion="failure")]},
        })
        row = wd.judge_workflow(gh, "post.yml", 24, NOW, dispatch=False)
        self.assertEqual("never", row["last_success"])
        self.assertEqual("would_retrigger", row["action"])


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, payload):
        (self.root / name).write_text(json.dumps(payload), encoding="utf-8")

    def test_threads_receipt_needs_post_id_permalink_and_timestamp(self):
        self.write("state.json", {"delivery_receipts": {
            "a": {"post_id": "1", "permalink": "https://t/1", "published_at": NOW - 2 * H},
            "queued": {"post_id": "", "permalink": "", "published_at": NOW},
            "nostamp": {"post_id": "2", "permalink": "https://t/2"},
        }, "outbox": {"x": {}}})
        stamp, count = wd.threads_receipts(self.root)
        self.assertEqual((NOW - 2 * H, 1), (stamp, count))

    def test_bluesky_receipt_needs_at_uri_and_cid(self):
        self.write("state_bluesky.json", {"delivery_receipts": {
            "ok": {"uri": "at://did/app.bsky.feed.post/1", "cid": "bafy", "published_at": NOW - 5 * H},
            "nocid": {"uri": "at://did/x", "published_at": NOW},
            "https": {"uri": "https://bsky.app/x", "cid": "bafy", "published_at": NOW},
        }})
        self.assertEqual((NOW - 5 * H, 1), wd.bluesky_receipts(self.root))

    def test_nostr_receipt_requires_relay_quorum_acknowledgement(self):
        event = "a" * 64
        self.write("state_nostr.json", {"relay_attempts": {
            "ok": {"status": "acknowledged", "event_id": event, "required_acknowledgements": 2,
                   "acknowledged_relays": ["wss://a", "wss://b"], "updated_at": NOW - 1 * H},
            "short": {"status": "acknowledged", "event_id": event, "required_acknowledgements": 2,
                      "acknowledged_relays": ["wss://a"], "updated_at": NOW},
            "prepared": {"status": "prepared", "event_id": event, "prepared_at": NOW},
        }, "outbox": {"many": {}}})
        self.assertEqual((NOW - 1 * H, 1), wd.nostr_receipts(self.root))

    def test_missing_state_is_a_hard_error_not_a_zero(self):
        with self.assertRaises(wd.WatchdogError):
            wd.threads_receipts(self.root)

    def test_evidence_judgement_uses_its_own_window(self):
        fresh = wd.judge_evidence("nostr_receipts", NOW - 23 * H, "n", NOW)
        stale = wd.judge_evidence("nostr_receipts", NOW - 25 * H, "n", NOW)
        self.assertTrue(fresh["fresh"])
        self.assertFalse(stale["fresh"])
        self.assertFalse(wd.judge_evidence("nostr_receipts", None, "n", NOW)["fresh"])


class GuideEvidenceTests(unittest.TestCase):
    def test_live_deployment_must_be_on_main(self):
        payload = {"source_commit": "abcdef1234", "generated_at": wd.iso(NOW - 3 * H)}
        on_main = ScriptedGh({"compare/abcdef1234...main": {"status": "ahead"}})
        stamp, note = wd.guide_deployment(on_main, lambda url: json.dumps(payload).encode(), "https://x/g/")
        self.assertEqual(NOW - 3 * H, stamp)
        self.assertIn("on main", note)
        diverged = ScriptedGh({"compare/abcdef1234...main": {"status": "diverged"}})
        stamp, note = wd.guide_deployment(diverged, lambda url: json.dumps(payload).encode(), "https://x/g")
        self.assertIsNone(stamp)
        self.assertIn("not an ancestor", note)

    def test_deployment_without_source_commit_is_an_error(self):
        with self.assertRaises(wd.WatchdogError):
            wd.guide_deployment(ScriptedGh({}), lambda url: b"{}", "https://x")

    def test_telegram_success_run_must_carry_message_id(self):
        gh = ScriptedGh({
            "workflows/telegram-daily.yml/runs": {"workflow_runs": [run_at(2, run_id=77)]},
            "run view 77": "posted ok, message_id: 240 ...",
        })
        stamp, note = wd.telegram_message_id(gh)
        self.assertEqual(NOW - 2 * H, stamp)
        silent = ScriptedGh({
            "workflows/telegram-daily.yml/runs": {"workflow_runs": [run_at(2, run_id=78)]},
            "run view 78": "posted nothing",
        })
        self.assertIsNone(wd.telegram_message_id(silent)[0])


class ReportingTests(unittest.TestCase):
    def rows(self, red: bool):
        return [{"line": "post.yml", "kind": "workflow", "fresh": not red, "last_success": "x",
                 "max_age_hours": 24, "in_progress": False, "action": "retriggered", "note": ""}]

    def test_red_creates_then_updates_a_single_issue(self):
        gh = ScriptedGh({"issue list": []})
        self.assertEqual("issue_created", wd.reconcile_issue(gh, self.rows(True), NOW))
        self.assertTrue(any(argv[:3] == ["gh", "issue", "create"] for argv in gh.calls))
        gh = ScriptedGh({"issue list": [{"number": 12, "title": "line-health"}]})
        self.assertEqual("issue_updated", wd.reconcile_issue(gh, self.rows(True), NOW))
        self.assertTrue(any(argv[:4] == ["gh", "issue", "edit", "12"] for argv in gh.calls))

    def test_green_closes_the_open_issue_with_a_healed_comment(self):
        gh = ScriptedGh({"issue list": [{"number": 12, "title": "line-health"}]})
        self.assertEqual("issue_closed", wd.reconcile_issue(gh, self.rows(False), NOW))
        self.assertTrue(any(argv[:4] == ["gh", "issue", "close", "12"] for argv in gh.calls))
        self.assertEqual("all_fresh", wd.reconcile_issue(ScriptedGh({"issue list": []}), self.rows(False), NOW))

    def test_telegram_alert_only_fires_on_red_with_credentials(self):
        sent = []
        post = lambda url, payload: sent.append((url, payload))  # noqa: E731
        self.assertFalse(wd.telegram_alert(self.rows(False), NOW, "t", "c", post))
        self.assertFalse(wd.telegram_alert(self.rows(True), NOW, "", "c", post))
        self.assertTrue(wd.telegram_alert(self.rows(True), NOW, "tok", "chat", post))
        self.assertIn("post.yml", sent[0][1]["text"])
        self.assertNotIn("tok", sent[0][1]["text"])

    def test_table_never_mentions_mastodon_as_a_line(self):
        table = wd.render_table(self.rows(True), NOW)
        self.assertIn("🔴 stale", table)
        self.assertIn("retired", table)
        for profile in wd.PROFILES.values():
            self.assertFalse(any("mastodon" in name.lower() for name in profile["workflows"]))


class ProfileRunTests(unittest.TestCase):
    def test_disabled_workflows_are_skipped_and_evidence_is_judged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("state.json", "state_bluesky.json", "state_nostr.json"):
                (root / name).write_text("{}", encoding="utf-8")
            table = {"actions/workflows?per_page=100": {"workflows": [
                {"path": ".github/workflows/post.yml", "id": 1, "state": "disabled_manually", "name": "p"},
            ]}}
            gh = ScriptedGh(table)
            rows = wd.run("threads-autopilot", "owner/repo", root, now=NOW, gh=gh, dispatch=False)
        by_line = {row["line"]: row for row in rows}
        self.assertEqual("skipped", by_line["post.yml"]["action"])
        self.assertIn("disabled_manually", by_line["post.yml"]["note"])
        self.assertIn("missing", by_line["multi.yml"]["note"])
        self.assertFalse(by_line["threads_receipts"]["fresh"])
        self.assertEqual([], gh.dispatched())


if __name__ == "__main__":
    unittest.main()
