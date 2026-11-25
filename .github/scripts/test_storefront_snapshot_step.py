"""geo-daily wiring of the snapshot-only commit (11-25 ruling 2307 item 1)."""

from __future__ import annotations

from pathlib import Path
import unittest

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "geo-daily.yml"
SCRIPT = ROOT / "_engine" / "geo" / "commit_storefront_snapshot.py"
STEP = "Commit re-fetched storefront snapshot alone (own checks only)"


class StorefrontSnapshotStepTests(unittest.TestCase):
    def setUp(self) -> None:
        workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        self.steps = workflow["jobs"]["generate"]["steps"]
        self.names = [step.get("name") for step in self.steps]

    def test_step_runs_right_after_the_single_refresh_and_before_any_generator(self):
        refresh = self.names.index("Refresh verified App Store availability once")
        step = self.names.index(STEP)
        materialize = self.names.index("Materialize newly live app surfaces")
        self.assertLess(refresh, step)
        self.assertLess(step, materialize)
        between = " ".join(
            self.steps[index].get("run", "") for index in range(refresh + 1, step)
        )
        self.assertNotIn("python3", between)

    def test_step_never_fails_the_run_and_sets_a_bot_identity(self):
        body = self.steps[self.names.index(STEP)]["run"]
        self.assertIn(
            'if ! python3 _engine/geo/commit_storefront_snapshot.py --root "$GITHUB_WORKSPACE"; then',
            body,
        )
        self.assertIn("::warning title=", body)
        self.assertIn('git config user.name "github-actions[bot]"', body)
        self.assertNotIn("git add", body)
        self.assertNotIn("git push", body)

    def test_script_commits_only_the_snapshot_and_skips_ci(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('_git(worktree, "add", "--", STATE_FILE)', source)
        self.assertNotIn('_git(root, "add"', source)
        self.assertNotIn('_git(root, "commit"', source)
        self.assertNotIn('"-A"', source)
        self.assertNotIn("--force\", remote", source)
        self.assertNotIn("push\", \"--force", source)
        self.assertIn("[skip ci]", source)
        self.assertIn('READBACK_TEST = "test_storefront_price_readback"', source)
        self.assertIn("check_storefront_snapshot.py", source)

    def test_route_and_derived_commits_still_wait_for_the_full_suite(self):
        english = self.steps[
            self.names.index("Commit English content first (fast, before slow localization)")
        ]["run"]
        self.assertIn("python3 _engine/geo/parallel_unittest.py --jobs 5", english)
        self.assertLess(
            english.index("python3 _engine/geo/parallel_unittest.py --jobs 5"),
            english.index("remote_first_publish reconcile_english_phase"),
        )
        verify = self.names.index("Verify localized output before commit")
        commit = self.names.index("Commit localized pages if any")
        self.assertLess(verify, commit)
        self.assertIn(
            "python3 _engine/geo/parallel_unittest.py --jobs 5",
            self.steps[verify]["run"],
        )


if __name__ == "__main__":
    unittest.main()
