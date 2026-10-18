"""Unit tests for line_watchdog.py with a scripted ``gh`` runner (no network)."""
from __future__ import annotations

import contextlib
import io
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
        # On main with nothing deployable waiting: fresh now, whatever the deploy's age.
        on_main = ScriptedGh({"compare/abcdef1234...main": {"status": "ahead"}})
        stamp, note = wd.guide_deployment(on_main, lambda url: json.dumps(payload).encode(), "https://x/g/", NOW)
        self.assertEqual(NOW, stamp)
        self.assertIn("on main", note)
        diverged = ScriptedGh({"compare/abcdef1234...main": {"status": "diverged"}})
        stamp, note = wd.guide_deployment(diverged, lambda url: json.dumps(payload).encode(), "https://x/g")
        self.assertIsNone(stamp)
        self.assertIn("not an ancestor", note)

    def test_undeployed_content_on_main_is_dated_by_its_oldest_commit(self):
        # 2026-10-13..16: the deploy was young but main was days ahead.
        payload = {"source_commit": "abcdef1234", "generated_at": wd.iso(NOW - 1 * H)}
        gh = ScriptedGh({
            "compare/abcdef1234...main": {"status": "ahead", "commits": [
                {"sha": "c1", "commit": {"committer": {"date": wd.iso(NOW - 30 * H)}}},
                {"sha": "c2", "commit": {"committer": {"date": wd.iso(NOW - 20 * H)}}},
            ]},
            "commits/c1": {"files": [{"filename": ".github/growth/clips.json"}]},
            "commits/c2": {"files": [{"filename": "answers/new-page.html"}]},
        })
        stamp, note = wd.guide_deployment(gh, lambda url: json.dumps(payload).encode(), "https://x/g", NOW)
        self.assertEqual(NOW - 20 * H, stamp)
        self.assertIn("lacks 1 content commit", note)
        self.assertFalse(wd.judge_evidence("guide_deployment", stamp, note, NOW)["fresh"])
        self.assertTrue(wd.judge_evidence("guide_deployment", NOW - 5 * H, note, NOW)["fresh"])

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

    def test_idempotent_slot_skip_does_not_hide_a_delivering_line(self):
        """The line runs more often than it posts; a run that finds its slot
        already served is healthy. Judging only the newest run reported a
        delivering line as dead (2026-09-07, message_id 253 was already out)."""
        gh = ScriptedGh({
            "workflows/telegram-daily.yml/runs": {"workflow_runs": [
                run_at(1, run_id=91), run_at(3, run_id=90),
            ]},
            "run view 91": "cloud social slot 2026-09-07T09:00:00+00:00: already completed; skip",
            "run view 90": "posted ok, message_id: 253 | lang: en-US",
        })
        stamp, note = wd.telegram_message_id(gh)
        self.assertEqual(NOW - 3 * H, stamp)
        self.assertIn("message_id", note)
        self.assertIn("1 newer run(s) skipped", note)

    def test_a_line_that_only_ever_skips_is_still_red(self):
        gh = ScriptedGh({
            "workflows/telegram-daily.yml/runs": {"workflow_runs": [
                run_at(1, run_id=93), run_at(2, run_id=92),
            ]},
            "run view 93": "already completed; skip",
            "run view 92": "already completed; skip",
        })
        stamp, note = wd.telegram_message_id(gh)
        self.assertIsNone(stamp)
        self.assertIn("without ever delivering", note)

    def test_a_silent_run_behind_a_skip_is_still_red(self):
        gh = ScriptedGh({
            "workflows/telegram-daily.yml/runs": {"workflow_runs": [
                run_at(1, run_id=95), run_at(2, run_id=94),
            ]},
            "run view 95": "already completed; skip",
            "run view 94": "posted nothing at all",
        })
        self.assertIsNone(wd.telegram_message_id(gh)[0])


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
        calls = []

        def api(token, method, payload):
            calls.append((method, payload))
            return {"id": 123456789, "type": "private"} if method == "getChat" else {"message_id": 7}

        self.assertFalse(wd.telegram_alert(self.rows(False), NOW, "t", "123456789", api))
        self.assertFalse(wd.telegram_alert(self.rows(True), NOW, "", "123456789", api))
        self.assertTrue(wd.telegram_alert(self.rows(True), NOW, "tok", "123456789", api))
        sent = [payload for method, payload in calls if method == "sendMessage"]
        self.assertEqual("123456789", sent[0]["chat_id"])
        self.assertIn("post.yml", sent[0]["text"])
        self.assertNotIn("tok", sent[0]["text"])

    def test_telegram_alert_never_reaches_a_public_chat(self):
        calls = []

        def api(token, method, payload):
            calls.append(method)
            return {"type": "channel", "username": "LumiApps2026"} if method == "getChat" else {"message_id": 7}

        with contextlib.redirect_stderr(io.StringIO()):
            self.assertFalse(wd.telegram_alert(self.rows(True), NOW, "tok", "@LumiApps2026", api))
            self.assertFalse(wd.telegram_alert(self.rows(True), NOW, "tok", "-1001234", api,
                                               public_chat_ids=("-1001234",)))
            self.assertFalse(wd.telegram_alert(self.rows(True), NOW, "tok", "-1005678", api))  # getChat: public
        self.assertNotIn("sendMessage", calls)

    def test_telegram_flag_reads_only_the_alert_chat(self):
        source = Path(wd.__file__).read_text(encoding="utf-8")
        main_source = source[source.index("def main("):]
        self.assertIn('"TELEGRAM_ALERT_CHAT_ID"', main_source)
        self.assertNotIn('os.environ.get("TELEGRAM_CHAT_ID"', main_source)
        self.assertNotIn("api.telegram.org", source)

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


def at(text: str) -> float:
    return wd.parse_time(text)


def slot_run(created: str, title: str, *, conclusion="success", status="completed",
             run_id=1, actor="github-actions[bot]"):
    return {"id": run_id, "conclusion": conclusion, "status": status, "created_at": created,
            "updated_at": created, "display_title": title, "actor": {"login": actor}}


def threads_title(cron: str) -> str:
    return f"Threads posts · cron {cron}"


GUIDE_SLOTS = wd.SLOT_WORKFLOWS["ios-app-guide"]
WORKFLOW_DIR = HERE.parent / "workflows"


class SlotPolicyTests(unittest.TestCase):
    """2026-10-15 the 13:00 UTC threads-post run never came and nothing went red:
    every promotion line with daily slots must be judged slot by slot."""

    def test_every_social_promotion_line_is_watched(self):
        for name in ("reels-daily.yml", "threads-post.yml", "utility-daily.yml",
                     "countdown-daily.yml", "clip-backup.yml"):
            self.assertIn(name, GUIDE_SLOTS, name)
            self.assertTrue((WORKFLOW_DIR / name).is_file(), name)
            window = GUIDE_SLOTS[name]["max_age_hours"]
            self.assertGreaterEqual(window, 26, name)
            self.assertLessEqual(window, 30, name)
        wd.validate_slot_policy("ios-app-guide")
        wd.validate_slot_policy("threads-autopilot")

    def test_heal_policy_per_line(self):
        self.assertEqual("inputs", GUIDE_SLOTS["threads-post.yml"]["heal"])
        self.assertEqual({"mode": "post", "slot": "{hour}", "date": "{date}"},
                         GUIDE_SLOTS["threads-post.yml"]["inputs"])
        self.assertEqual("plain", GUIDE_SLOTS["utility-daily.yml"]["heal"])
        self.assertEqual("inputs", GUIDE_SLOTS["clip-backup.yml"]["heal"])
        # Dispatch bypasses the reels slot gate; countdown has no gate or dedupe.
        self.assertEqual("monitor", GUIDE_SLOTS["reels-daily.yml"]["heal"])
        self.assertEqual("monitor", GUIDE_SLOTS["countdown-daily.yml"]["heal"])

    def test_slots_match_the_workflow_crons(self):
        import re
        for name, spec in GUIDE_SLOTS.items():
            text = (WORKFLOW_DIR / name).read_text(encoding="utf-8")
            crons = set()
            for minute, hours in re.findall(r"cron:\s*['\"](\d{1,2}) ([\d,]+) \* \* \*['\"]", text):
                for hour in hours.split(","):
                    crons.add((int(hour), int(minute)))
            self.assertEqual(crons, set(spec["slots"].items()), name)

    def test_threads_post_dispatch_inputs_match_the_workflow(self):
        text = (WORKFLOW_DIR / "threads-post.yml").read_text(encoding="utf-8")
        for key in ("mode:", "slot:", "date:", "- post", '- "13"'):
            self.assertIn(key, text)

    def test_a_slot_line_is_never_also_a_workflow_line(self):
        for profile, lines in wd.SLOT_WORKFLOWS.items():
            self.assertFalse(set(lines) & set(wd.PROFILES[profile]["workflows"]), profile)

    def test_broken_policy_is_rejected(self):
        original = dict(GUIDE_SLOTS["countdown-daily.yml"])
        try:
            GUIDE_SLOTS["countdown-daily.yml"]["heal"] = "yolo"
            with self.assertRaises(wd.WatchdogError):
                wd.validate_slot_policy("ios-app-guide")
        finally:
            GUIDE_SLOTS["countdown-daily.yml"].clear()
            GUIDE_SLOTS["countdown-daily.yml"].update(original)


class ThreadsSlotTests(unittest.TestCase):
    SPEC = GUIDE_SLOTS["threads-post.yml"]

    def judge(self, runs, now, dispatch_runs=(), dispatch=True):
        gh = ScriptedGh({
            "workflows/threads-post.yml/runs?per_page=30&event": {"workflow_runs": list(dispatch_runs)},
            "workflows/threads-post.yml/runs?per_page=30": {"workflow_runs": runs},
        })
        rows = wd.judge_slots(gh, "threads-post.yml", self.SPEC, now, dispatch=dispatch)
        return {row["line"]: row for row in rows}, gh

    def test_the_dropped_1015_evening_slot_turns_red_at_the_next_watchdog(self):
        runs = [
            slot_run("2026-10-15T03:05:00Z", threads_title("0 3 * * *"), run_id=5),
            slot_run("2026-10-15T01:45:00Z", threads_title("40 1 * * *"), run_id=4),
            slot_run("2026-10-14T13:04:00Z", threads_title("0 13 * * *"), run_id=3),
        ]
        rows, gh = self.judge(runs, at("2026-10-16T00:41:00Z"))
        evening = rows["threads-post.yml 13:00Z"]
        self.assertFalse(evening["fresh"])
        self.assertEqual("2026-10-15T13:00:00Z", evening["missed_slot"])
        # 08:41 in Taiwan: yesterday's evening slot would take today's room.
        self.assertEqual("outside_taiwan_day", evening["action"])
        self.assertTrue(rows["threads-post.yml 01:40Z"]["fresh"])
        self.assertTrue(rows["threads-post.yml 03:00Z"]["fresh"])
        self.assertEqual([], gh.dispatched())

    def test_a_missed_slot_of_today_is_refilled_with_mode_post_inputs(self):
        runs = [
            slot_run("2026-10-16T01:50:00Z", threads_title("40 1 * * *"), run_id=7),
            slot_run("2026-10-15T13:02:00Z", threads_title("0 13 * * *"), run_id=6),
            slot_run("2026-10-15T03:01:00Z", threads_title("0 3 * * *"), run_id=5),
        ]
        rows, gh = self.judge(runs, at("2026-10-16T12:41:00Z"))
        picture = rows["threads-post.yml 03:00Z"]
        self.assertFalse(picture["fresh"])
        self.assertEqual("retriggered", picture["action"])
        self.assertEqual({"mode": "post", "slot": "3", "date": "2026-10-16"}, picture["dispatch_inputs"])
        calls = [argv for argv in gh.calls if argv[:3] == ["gh", "workflow", "run"]]
        self.assertEqual(1, len(calls))
        self.assertEqual(["-f", "mode=post", "-f", "slot=3", "-f", "date=2026-10-16"], calls[0][-6:])
        self.assertTrue(rows["threads-post.yml 13:00Z"]["fresh"])

    def test_a_backfill_dispatch_serves_its_slot(self):
        runs = [
            slot_run("2026-10-16T06:30:00Z", "Threads posts · post slot 3 2026-10-16", run_id=8),
            slot_run("2026-10-16T01:50:00Z", threads_title("40 1 * * *"), run_id=7),
            slot_run("2026-10-15T13:02:00Z", threads_title("0 13 * * *"), run_id=6),
        ]
        rows, gh = self.judge(runs, at("2026-10-16T12:41:00Z"))
        self.assertTrue(all(row["fresh"] for row in rows.values()), rows)
        self.assertEqual([], gh.dispatched())

    def test_whoami_and_failed_runs_never_serve_a_slot(self):
        runs = [
            slot_run("2026-10-16T05:00:00Z", "Threads posts · whoami slot 3 ", run_id=9),
            slot_run("2026-10-16T03:02:00Z", threads_title("0 3 * * *"), conclusion="failure", run_id=8),
            slot_run("2026-10-16T01:50:00Z", threads_title("40 1 * * *"), run_id=7),
            slot_run("2026-10-15T13:02:00Z", threads_title("0 13 * * *"), run_id=6),
        ]
        rows, _ = self.judge(runs, at("2026-10-16T12:41:00Z"), dispatch=False)
        self.assertFalse(rows["threads-post.yml 03:00Z"]["fresh"])
        self.assertEqual("would_retrigger", rows["threads-post.yml 03:00Z"]["action"])

    def test_a_running_run_for_the_missed_slot_is_awaited(self):
        runs = [
            slot_run("2026-10-16T12:30:00Z", "Threads posts · post slot 3 2026-10-16",
                     conclusion=None, status="queued", run_id=9),
            slot_run("2026-10-16T01:50:00Z", threads_title("40 1 * * *"), run_id=7),
            slot_run("2026-10-15T13:02:00Z", threads_title("0 13 * * *"), run_id=6),
        ]
        rows, gh = self.judge(runs, at("2026-10-16T12:41:00Z"))
        self.assertEqual("wait_in_progress", rows["threads-post.yml 03:00Z"]["action"])
        self.assertEqual([], gh.dispatched())

    def test_bot_dispatch_budget_caps_slot_refills(self):
        runs = [slot_run("2026-10-15T13:02:00Z", threads_title("0 13 * * *"), run_id=6)]
        bots = [slot_run("2026-10-16T04:00:00Z", "x", run_id=11),
                slot_run("2026-10-16T05:00:00Z", "y", run_id=12)]
        rows, gh = self.judge(runs, at("2026-10-16T12:41:00Z"), dispatch_runs=bots)
        self.assertEqual("retrigger_budget_exhausted", rows["threads-post.yml 01:40Z"]["action"])
        self.assertEqual("retrigger_budget_exhausted", rows["threads-post.yml 03:00Z"]["action"])
        self.assertEqual([], gh.dispatched())

    def test_two_missed_slots_share_one_budget(self):
        runs = [slot_run("2026-10-15T13:02:00Z", threads_title("0 13 * * *"), run_id=6)]
        bots = [slot_run("2026-10-16T04:00:00Z", "x", run_id=11)]
        rows, gh = self.judge(runs, at("2026-10-16T12:41:00Z"), dispatch_runs=bots)
        self.assertEqual("retriggered", rows["threads-post.yml 01:40Z"]["action"])
        self.assertEqual("retrigger_budget_exhausted", rows["threads-post.yml 03:00Z"]["action"])
        self.assertEqual(["threads-post.yml"], gh.dispatched())


class OtherSlotLineTests(unittest.TestCase):
    def judge(self, workflow, runs, now, dispatch=True):
        gh = ScriptedGh({
            f"workflows/{workflow}/runs?per_page=30&event": {"workflow_runs": []},
            f"workflows/{workflow}/runs?per_page=30": {"workflow_runs": runs},
        })
        rows = wd.judge_slots(gh, workflow, GUIDE_SLOTS[workflow], now, dispatch=dispatch)
        return {row["line"]: row for row in rows}, gh

    def test_reels_missed_slot_is_red_but_never_dispatched(self):
        runs = [slot_run("2026-10-16T09:22:00Z", "Instagram Reels daily clip", run_id=3),
                slot_run("2026-10-15T15:21:00Z", "Instagram Reels daily clip", run_id=2),
                slot_run("2026-10-15T01:21:00Z", "Instagram Reels daily clip", run_id=1)]
        rows, gh = self.judge("reels-daily.yml", runs, at("2026-10-16T12:41:00Z"))
        self.assertFalse(rows["reels-daily.yml 01:20Z"]["fresh"])
        self.assertEqual("monitor_only", rows["reels-daily.yml 01:20Z"]["action"])
        self.assertTrue(rows["reels-daily.yml 09:20Z"]["fresh"])
        self.assertTrue(rows["reels-daily.yml 15:20Z"]["fresh"])
        self.assertEqual([], gh.dispatched())

    def test_countdown_green_run_without_a_post_is_fresh_and_a_miss_is_watch_only(self):
        rows, _ = self.judge("countdown-daily.yml",
                             [slot_run("2026-10-16T03:12:00Z", "Countdown card daily")],
                             at("2026-10-16T12:41:00Z"))
        self.assertTrue(rows["countdown-daily.yml 03:10Z"]["fresh"])
        rows, gh = self.judge("countdown-daily.yml",
                              [slot_run("2026-10-15T03:12:00Z", "Countdown card daily")],
                              at("2026-10-16T12:41:00Z"))
        self.assertFalse(rows["countdown-daily.yml 03:10Z"]["fresh"])
        self.assertEqual("monitor_only", rows["countdown-daily.yml 03:10Z"]["action"])
        self.assertEqual([], gh.dispatched())

    def test_utility_miss_of_today_gets_a_plain_dispatch(self):
        rows, gh = self.judge("utility-daily.yml",
                              [slot_run("2026-10-15T05:12:00Z", "Utility card daily")],
                              at("2026-10-16T12:41:00Z"))
        self.assertEqual("retriggered", rows["utility-daily.yml 05:10Z"]["action"])
        calls = [argv for argv in gh.calls if argv[:3] == ["gh", "workflow", "run"]]
        self.assertEqual([["gh", "workflow", "run", "utility-daily.yml", "--repo", "owner/repo"]], calls)

    def test_utility_miss_of_yesterday_is_not_refilled_after_taiwan_midnight(self):
        rows, gh = self.judge("utility-daily.yml",
                              [slot_run("2026-10-14T05:12:00Z", "Utility card daily")],
                              at("2026-10-16T00:41:00Z"))
        self.assertFalse(rows["utility-daily.yml 05:10Z"]["fresh"])
        self.assertEqual("outside_taiwan_day", rows["utility-daily.yml 05:10Z"]["action"])
        self.assertEqual([], gh.dispatched())

    def test_clip_backup_missed_americas_backup_is_refilled_with_its_slot(self):
        runs = [slot_run("2026-10-15T14:49:00Z", "Hook clip backup posts", run_id=3),
                slot_run("2026-10-15T03:49:00Z", "Hook clip backup posts", run_id=2),
                slot_run("2026-10-14T17:49:00Z", "Hook clip backup posts", run_id=1)]
        rows, gh = self.judge("clip-backup.yml", runs, at("2026-10-16T00:41:00Z"))
        row = rows["clip-backup.yml 17:47Z"]
        self.assertEqual("retriggered", row["action"])
        self.assertEqual({"slot": "15", "date": "2026-10-15"}, row["dispatch_inputs"])
        self.assertTrue(rows["clip-backup.yml 03:47Z"]["fresh"])
        self.assertTrue(rows["clip-backup.yml 14:47Z"]["fresh"])

    def test_clip_backup_missed_threads_evening_backup_is_not_rerun_next_taiwan_day(self):
        runs = [slot_run("2026-10-15T20:49:00Z", "Hook clip backup posts", run_id=6),
                slot_run("2026-10-15T17:49:00Z", "Hook clip backup posts", run_id=3),
                slot_run("2026-10-15T11:49:00Z", "Hook clip backup posts", run_id=5),
                slot_run("2026-10-15T03:49:00Z", "Hook clip backup posts", run_id=2),
                slot_run("2026-10-15T00:49:00Z", "Hook clip backup posts", run_id=4),
                slot_run("2026-10-14T14:49:00Z", "Hook clip backup posts", run_id=1)]
        rows, gh = self.judge("clip-backup.yml", runs, at("2026-10-16T00:41:00Z"))
        self.assertFalse(rows["clip-backup.yml 14:47Z"]["fresh"])
        self.assertEqual("outside_taiwan_day", rows["clip-backup.yml 14:47Z"]["action"])
        self.assertEqual([], gh.dispatched())

    def test_clip_backup_missed_asia_backup_uses_clip_slot_1(self):
        runs = [slot_run("2026-10-15T17:49:00Z", "Hook clip backup posts", run_id=3),
                slot_run("2026-10-15T14:49:00Z", "Hook clip backup posts", run_id=2),
                slot_run("2026-10-15T03:49:00Z", "Hook clip backup posts", run_id=1)]
        rows, _ = self.judge("clip-backup.yml", runs, at("2026-10-16T12:41:00Z"), dispatch=False)
        row = rows["clip-backup.yml 03:47Z"]
        self.assertEqual("would_retrigger", row["action"])
        self.assertEqual({"slot": "1", "date": "2026-10-16"}, row["dispatch_inputs"])


class GuideProfileSlotRunTests(unittest.TestCase):
    def test_guide_profile_judges_every_slot_line(self):
        names = list(wd.PROFILES["ios-app-guide"]["workflows"]) + list(GUIDE_SLOTS)
        now = at("2026-10-16T12:41:00Z")
        table = {
            "actions/workflows?per_page=100": {"workflows": [
                {"path": f".github/workflows/{name}", "id": i, "state": "active", "name": name}
                for i, name in enumerate(names, start=1)
            ]},
            "workflows/telegram-daily.yml/runs": {"workflow_runs": [
                slot_run("2026-10-16T09:01:00Z", "Telegram", run_id=77)]},
            "run view 77": "message_id: 300",
            "compare/abcdef1234...main": {"status": "ahead"},
            "workflows/reels-daily.yml/runs": {"workflow_runs": []},
            "/runs?": {"workflow_runs": [slot_run("2026-10-16T12:00:00Z", "generic")]},
        }
        payload = json.dumps({"source_commit": "abcdef1234", "generated_at": "2026-10-16T10:00:00Z"}).encode()
        gh = ScriptedGh(table)
        rows = wd.run("ios-app-guide", "owner/repo", Path("."), now=now, gh=gh, dispatch=True,
                      fetch=lambda url: payload)
        slot_rows = [row for row in rows if row["kind"] == "slot"]
        lines = {row["line"].split(" ")[0] for row in slot_rows}
        self.assertEqual(set(GUIDE_SLOTS), lines)
        reels = [row for row in slot_rows if row["line"].startswith("reels-daily.yml")]
        self.assertEqual(len(GUIDE_SLOTS["reels-daily.yml"]["slots"]), len(reels))  # one row per ramp slot
        self.assertTrue(all(not row["fresh"] and row["action"] == "monitor_only" for row in reels))
        self.assertNotIn("reels-daily.yml", gh.dispatched())

    def test_disabled_or_missing_slot_line_is_skipped_not_judged(self):
        names = list(wd.PROFILES["ios-app-guide"]["workflows"])
        workflows = [
            {"path": f".github/workflows/{name}", "id": i, "state": "active", "name": name}
            for i, name in enumerate(names, start=1)
        ] + [{"path": ".github/workflows/countdown-daily.yml", "id": 99,
              "state": "disabled_manually", "name": "c"}]
        table = {
            "actions/workflows?per_page=100": {"workflows": workflows},
            "workflows/telegram-daily.yml/runs": {"workflow_runs": [
                slot_run("2026-10-16T09:01:00Z", "Telegram", run_id=77)]},
            "run view 77": "message_id: 300",
            "compare/abcdef1234...main": {"status": "ahead"},
            "/runs?": {"workflow_runs": [slot_run("2026-10-16T12:00:00Z", "generic")]},
        }
        payload = json.dumps({"source_commit": "abcdef1234", "generated_at": "2026-10-16T10:00:00Z"}).encode()
        gh = ScriptedGh(table)
        rows = wd.run("ios-app-guide", "owner/repo", Path("."), now=at("2026-10-16T12:41:00Z"),
                      gh=gh, dispatch=True, fetch=lambda url: payload)
        by_line = {row["line"]: row for row in rows if row["kind"] == "slot"}
        self.assertEqual("skipped", by_line["countdown-daily.yml"]["action"])
        self.assertIn("disabled_manually", by_line["countdown-daily.yml"]["note"])
        self.assertIn("missing", by_line["threads-post.yml"]["note"])
        self.assertEqual([], gh.dispatched())


class IgBioHubLineTests(unittest.TestCase):
    """ig-bio-hub.yml rebuilds the Instagram profile-link hub (cron 41 3 * * *) and reads it back live. It is a
    daily workflow line: judged by a 30h window, re-dispatched with no inputs when it goes quiet."""

    NAME = "ig-bio-hub.yml"
    TITLE = "Instagram profile-link hub · all"

    def runs(self, *runs):
        # The specific key first: ScriptedGh answers with the first key found in the call.
        return ScriptedGh({
            f"workflows/{self.NAME}/runs?per_page=30&event": {"workflow_runs": []},
            f"workflows/{self.NAME}/runs?per_page=30": {"workflow_runs": list(runs)},
        })

    def test_is_a_watched_daily_workflow_line_and_not_a_slot_line(self):
        self.assertEqual(30, wd.PROFILES["ios-app-guide"]["workflows"][self.NAME])
        self.assertNotIn(self.NAME, GUIDE_SLOTS)
        self.assertTrue((WORKFLOW_DIR / self.NAME).is_file())
        wd.validate_slot_policy("ios-app-guide")

    def test_window_covers_the_workflows_own_daily_cron_and_it_accepts_a_bare_dispatch(self):
        import re
        text = (WORKFLOW_DIR / self.NAME).read_text(encoding="utf-8")
        self.assertEqual(["41 3 * * *"], re.findall(r"cron:\s*['\"]([^'\"]+)['\"]", text))
        window = wd.PROFILES["ios-app-guide"]["workflows"][self.NAME]
        self.assertGreaterEqual(window, 24)  # a daily cron: never red between two runs
        self.assertLessEqual(window, 30)  # a missed day is red at the first watchdog pass after it
        # The healer dispatches with no inputs, so the workflow must run on its defaults.
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("required: true", text)

    def test_the_two_daily_watchdog_passes_judge_the_run_by_its_age(self):
        for now, last_success, fresh in (
            ("2026-10-17T00:41:00Z", "2026-10-16T03:44:00Z", True),   # 21h: today's 03:41 run is not due yet
            ("2026-10-17T12:41:00Z", "2026-10-17T03:44:00Z", True),   # 9h
            ("2026-10-17T12:41:00Z", "2026-10-16T03:44:00Z", False),  # the 03:41 run never came: 33h
        ):
            row = wd.judge_workflow(self.runs(slot_run(last_success, self.TITLE)), self.NAME, 30,
                                    at(now), dispatch=False)
            self.assertEqual(fresh, row["fresh"], (now, last_success))

    def test_a_quiet_day_is_redispatched_with_no_inputs(self):
        gh = self.runs(slot_run("2026-10-16T03:44:00Z", self.TITLE))
        row = wd.judge_workflow(gh, self.NAME, 30, at("2026-10-17T12:41:00Z"), dispatch=True)
        self.assertEqual("retriggered", row["action"])
        self.assertEqual([self.NAME], gh.dispatched())
        dispatch = next(argv for argv in gh.calls if argv[:3] == ["gh", "workflow", "run"])
        self.assertNotIn("-f", dispatch)  # defaults: mode=all (rebuild, account read, live read-back)

    def test_a_failed_live_read_back_never_counts_as_a_success(self):
        gh = self.runs(slot_run("2026-10-17T11:00:00Z", self.TITLE, conclusion="failure"))
        row = wd.judge_workflow(gh, self.NAME, 30, at("2026-10-17T12:41:00Z"), dispatch=False)
        self.assertFalse(row["fresh"])
        self.assertEqual("never", row["last_success"])


if __name__ == "__main__":
    unittest.main()
