"""Unit tests for guide_release.py and guide_auto_release.py (scripted gh/git, no network)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import guide_auto_release as ar  # noqa: E402
import guide_release as gr  # noqa: E402
from test_line_watchdog import NOW, H, ScriptedGh  # noqa: E402
import line_watchdog as wd  # noqa: E402

LIVE = "a" * 40
GUIDE = "b" * 40
GROWTH = "c" * 40


def deployment(sha: str = LIVE):
    return lambda url: json.dumps({"source_commit": sha}).encode()


def compare(*commits):
    return {"status": "ahead", "commits": [
        {"sha": sha, "commit": {"committer": {"date": wd.iso(NOW - hours * H)}}} for sha, hours in commits
    ]}


def paired(status="completed", conclusion="success", sha=GUIDE):
    return {"display_title": ar.paired_title(sha), "status": status, "conclusion": conclusion}


class LagTests(unittest.TestCase):
    def test_automation_and_engine_paths_are_not_site_content(self):
        for path in (".github/growth/clips.json", ".claude/settings.json", "_engine/geo/x.py"):
            self.assertFalse(gr.is_deployable(path))
        for path in ("answers/a.html", "sitemap.xml", "CLAUDE.md", "feeds/owned-apps.json"):
            self.assertTrue(gr.is_deployable(path))

    def test_identical_is_up_to_date_and_diverged_is_an_error(self):
        self.assertEqual([], gr.undeployed(lambda p: {"status": "identical"}, "o/r", LIVE))
        with self.assertRaises(gr.ReleaseError):
            gr.undeployed(lambda p: {"status": "diverged"}, "o/r", LIVE)

    def test_live_commit_must_be_a_full_sha(self):
        with self.assertRaises(gr.ReleaseError):
            gr.live_source_commit(lambda url: b'{"source_commit": "abc"}', "https://x")

    def test_lag_counts_from_the_oldest_content_commit(self):
        gh = ScriptedGh({
            f"compare/{LIVE}...main": compare(("c1", 30), ("c2", 8)),
            "commits/c1": {"files": [{"filename": ".github/growth/clips.json"}]},
            "commits/c2": {"files": [{"filename": "answers/x.html"}]},
        })
        pending = gr.undeployed(gh.api, gh.repo, LIVE)
        self.assertEqual(["c2"], [item.sha for item in pending])
        self.assertAlmostEqual(8.0, gr.lag_hours(pending, NOW))


class DecideTests(unittest.TestCase):
    pending = [gr.Pending("c2", NOW - 8 * H)]

    def test_nothing_waiting_is_up_to_date(self):
        self.assertEqual("up_to_date", ar.decide([], [], GUIDE, trigger_ok=True))

    def test_never_two_paired_releases_at_once(self):
        self.assertTrue(ar.decide(self.pending, [paired(status="in_progress")], GUIDE, trigger_ok=True)
                        .startswith("hold"))

    def test_retries_once_then_holds_for_the_same_guide_sha(self):
        one_failure = [paired(conclusion="failure")]
        self.assertEqual("dispatch", ar.decide(self.pending, one_failure, GUIDE, trigger_ok=True))
        two_failures = one_failure + [paired(conclusion="cancelled")]
        self.assertIn("already failed", ar.decide(self.pending, two_failures, GUIDE, trigger_ok=True))
        other_sha = [paired(conclusion="failure", sha="d" * 40)] * 2
        self.assertEqual("dispatch", ar.decide(self.pending, other_sha, GUIDE, trigger_ok=True))

    def test_failed_preflight_trigger_does_not_dispatch(self):
        self.assertIn("preflight", ar.decide(self.pending, [], GUIDE, trigger_ok=False))


class RunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "_engine/geo").mkdir(parents=True)
        (root / "_engine/geo/notification_policy.json").write_text('{"notification_release_hold": false}')
        self.root = root
        self.git_calls: list[list[str]] = []

    def tearDown(self):
        self.tmp.cleanup()

    def fake_git(self, argv):
        self.git_calls.append(argv)
        if "ls-tree" in argv:
            return f"160000 commit {LIVE}\tgeo/pages"
        if "rev-parse" in argv:
            return GROWTH
        return ""

    def gh(self, *, waiting_hours=8, runs=None, open_issue=None):
        return ScriptedGh({
            f"compare/{LIVE}...main": compare(("c2", waiting_hours)) if waiting_hours else {"status": "identical"},
            "commits/c2": {"files": [{"filename": "answers/x.html"}]},
            "workflows/pages.yml/runs": {"workflow_runs": runs or []},
            "issue list": open_issue or [],
        })

    def run_once(self, gh, **kwargs):
        options = dict(gh=gh, fetch=deployment(), site="https://x/g", guide_root=self.root, guide_sha=GUIDE,
                       engine=self.root, now=NOW, stale_hours=6, trigger_ok=True, dry_run=False,
                       git_runner=self.fake_git)
        options.update(kwargs)
        return ar.run(**options)

    def test_lagging_site_binds_the_gitlink_dispatches_once_and_raises_the_alarm(self):
        gh = self.gh()
        result = self.run_once(gh)
        self.assertEqual("dispatched", result["action"])
        self.assertIn(["git", "-C", str(self.root), "update-index", "--cacheinfo",
                       f"160000,{GUIDE},geo/pages"], self.git_calls)
        runs = [argv for argv in gh.calls if argv[:3] == ["gh", "workflow", "run"]]
        self.assertEqual(1, len(runs))
        joined = " ".join(runs[0])
        for expected in (f"expected_guide_sha={GUIDE}", f"expected_growth_sha={GROWTH}",
                         f"previous_guide_revision={LIVE}", "notification_release_hold=false",
                         "owned_feed_release=true", "incremental_high_intent=true"):
            self.assertIn(expected, joined)
        created = [argv for argv in gh.calls if argv[:3] == ["gh", "issue", "create"]]
        self.assertEqual(1, len(created))
        self.assertIn(ar.OWNER_MENTION, created[0][-1])
        self.assertEqual("issue_created", result["issue"])

    def test_read_only_gitlink_credential_holds_and_still_alarms(self):
        def read_only_git(argv):
            self.git_calls.append(argv)
            if "push" in argv:
                raise gr.ReleaseError("git push failed: key is read only")
            if "ls-tree" in argv:
                return f"160000 commit {LIVE}\tgeo/pages"
            return GROWTH if "rev-parse" in argv else ""
        gh = self.gh()
        result = self.run_once(gh, git_runner=read_only_git)
        self.assertTrue(result["action"].startswith("hold: gitlink bind failed"))
        self.assertFalse([argv for argv in gh.calls if argv[:3] == ["gh", "workflow", "run"]])
        self.assertEqual("issue_created", result["issue"])

    def test_fresh_lag_dispatches_without_an_alarm(self):
        gh = self.gh(waiting_hours=2)
        result = self.run_once(gh)
        self.assertEqual("dispatched", result["action"])
        self.assertEqual("no_issue", result["issue"])

    def test_gitlink_already_bound_is_not_recommitted(self):
        def bound_git(argv):
            self.git_calls.append(argv)
            if "ls-tree" in argv:
                return f"160000 commit {GUIDE}\tgeo/pages"
            return GROWTH if "rev-parse" in argv else ""
        self.run_once(self.gh(waiting_hours=2), git_runner=bound_git)
        self.assertFalse([argv for argv in self.git_calls if "commit" in argv or "push" in argv])

    def test_caught_up_site_closes_the_open_alarm(self):
        gh = self.gh(waiting_hours=0, open_issue=[{"number": 9, "title": ar.STALE_TITLE}])
        result = self.run_once(gh)
        self.assertEqual("up_to_date", result["action"])
        self.assertEqual("issue_closed", result["issue"])
        self.assertTrue([argv for argv in gh.calls if argv[:3] == ["gh", "issue", "close"]])
        self.assertFalse([argv for argv in gh.calls if argv[:3] == ["gh", "workflow", "run"]])

    def test_dry_run_touches_nothing(self):
        gh = self.gh()
        result = self.run_once(gh, dry_run=True)
        self.assertEqual("dispatch (dry run)", result["action"])
        self.assertEqual([], self.git_calls)
        self.assertFalse([argv for argv in gh.calls if argv[:2] in (["gh", "workflow"], ["gh", "issue"])])


if __name__ == "__main__":
    unittest.main()
