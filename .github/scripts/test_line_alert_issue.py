"""Tests for line_alert_issue.py (GitHub issue fallback when no private Telegram alert chat exists)."""
from __future__ import annotations

import json
import unittest

import line_alert_issue as lai

NOW = 1_760_000_000.0
REPO = "owner/repo"


def row(line, fresh=False, kind="evidence"):
    return {"line": line, "kind": kind, "fresh": fresh, "last_success": None, "max_age_hours": 4,
            "action": "none", "note": "n"}


def report(*rows):
    return {"judged_at": "2026-10-18T00:00:00Z", "rows": list(rows)}


class FakeGh:
    def __init__(self, issue=None):
        self.issue = issue
        self.calls: list[list[str]] = []

    def __call__(self, argv):
        self.calls.append(argv)
        if argv[:3] == ["gh", "issue", "list"]:
            return json.dumps([self.issue] if self.issue else [])
        return ""

    def verbs(self):
        return [" ".join(argv[1:3]) for argv in self.calls if argv[1:3] != ["issue", "list"]]


def open_issue(lines, title=lai.ISSUE_TITLE):
    return {"number": 5, "title": title, "body": "x\n" + lai.marker(lines)}


class AlertIssueTests(unittest.TestCase):
    def reconcile(self, gh, rep, *, active=True, scope=()):
        return lai.reconcile(rep, repo=REPO, label="00_GrowthEngine", run_url="u", now=NOW,
                             active=active, scope=scope, run=gh)

    def test_red_lines_open_one_labelled_issue(self):
        gh = FakeGh()
        self.assertEqual(self.reconcile(gh, report(row("self_hosted_queue"), row("ok", True))), "created")
        self.assertEqual(gh.verbs(), ["label create", "issue create"])
        create = gh.calls[-1]
        self.assertEqual(create[create.index("--title") + 1], "外宣線紅燈警報")
        self.assertEqual(create[create.index("--label") + 1], "alert")
        body = create[create.index("--body") + 1]
        self.assertEqual(lai.listed_lines(body), ["self_hosted_queue"])
        self.assertIn("建議", body)

    def test_the_same_red_lines_do_not_comment_again(self):
        gh = FakeGh(open_issue(["self_hosted_queue"]))
        self.assertEqual(self.reconcile(gh, report(row("self_hosted_queue"))), "unchanged")
        self.assertEqual(gh.verbs(), [])

    def test_a_new_red_line_comments_only_the_new_one(self):
        gh = FakeGh(open_issue(["self_hosted_queue"]))
        self.assertEqual(self.reconcile(gh, report(row("self_hosted_queue"), row("promo_domain_http"))),
                         "commented")
        self.assertEqual(gh.verbs(), ["issue edit", "issue comment"])
        comment = gh.calls[-1][gh.calls[-1].index("--body") + 1]
        self.assertIn("promo_domain_http", comment)
        self.assertNotIn("self_hosted_queue", comment)

    def test_a_partial_recovery_edits_quietly(self):
        gh = FakeGh(open_issue(["a", "b"]))
        self.assertEqual(self.reconcile(gh, report(row("a"), row("b", True))), "updated")
        self.assertEqual(gh.verbs(), ["issue edit"])

    def test_all_green_closes_with_one_comment(self):
        gh = FakeGh(open_issue(["a"]))
        self.assertEqual(self.reconcile(gh, report(row("a", True))), "closed")
        self.assertEqual(gh.verbs(), ["issue comment", "issue close"])

    def test_all_green_without_issue_does_nothing(self):
        gh = FakeGh()
        self.assertEqual(self.reconcile(gh, report(row("a", True))), "all_fresh")
        self.assertEqual(gh.verbs(), [])

    def test_a_missing_report_is_a_red_watchdog(self):
        gh = FakeGh()
        self.assertEqual(self.reconcile(gh, None), "created")
        body = gh.calls[-1][gh.calls[-1].index("--body") + 1]
        self.assertIn("line-watchdog", body)

    def test_a_scoped_probe_keeps_other_red_lines(self):
        gh = FakeGh(open_issue(["coverage_floor", "self_hosted_queue"]))
        status = self.reconcile(gh, report(row("self_hosted_queue", True), row("promo_domain_http", True)),
                                scope=("self_hosted_queue", "promo_domain_http"))
        self.assertEqual(status, "updated")
        body = gh.calls[-1][gh.calls[-1].index("--body") + 1]
        self.assertEqual(lai.listed_lines(body), ["coverage_floor"])
        self.assertIn("沒有重新判定", body)

    def test_a_scoped_probe_closes_when_its_lines_were_the_last_red(self):
        gh = FakeGh(open_issue(["promo_domain_http"]))
        status = self.reconcile(gh, report(row("self_hosted_queue", True), row("promo_domain_http", True)),
                                scope=("self_hosted_queue", "promo_domain_http"))
        self.assertEqual(status, "closed")

    def test_a_full_judge_replaces_the_list(self):
        gh = FakeGh(open_issue(["gone_line", "a"]))
        self.assertEqual(self.reconcile(gh, report(row("a"))), "updated")

    def test_with_a_private_telegram_chat_no_issue_is_opened(self):
        gh = FakeGh()
        self.assertEqual(self.reconcile(gh, report(row("a")), active=False), "telegram_configured")
        self.assertEqual(gh.verbs(), [])

    def test_with_a_private_telegram_chat_an_old_issue_still_closes_when_green(self):
        gh = FakeGh(open_issue(["a"]))
        self.assertEqual(self.reconcile(gh, report(row("a", True)), active=False), "closed")

    def test_fallback_is_active_while_the_alert_chat_is_missing_invalid_or_public(self):
        self.assertTrue(lai.fallback_active("", ()))
        self.assertTrue(lai.fallback_active("@lumiapps2026", ()))
        self.assertTrue(lai.fallback_active("-1001234", ("-1001234",)))
        self.assertFalse(lai.fallback_active("123456789", ("-1001234",)))

    def test_other_titles_are_left_alone(self):
        gh = FakeGh({"number": 9, "title": "line-health", "body": ""})
        self.assertEqual(self.reconcile(gh, report(row("a"))), "created")


if __name__ == "__main__":
    unittest.main()
