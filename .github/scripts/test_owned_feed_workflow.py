from pathlib import Path
import subprocess
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]


class OwnedFeedWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
        cls.workflow = yaml.safe_load(cls.source)
        cls.steps = cls.workflow["jobs"]["deploy"]["steps"]
        cls.by_name = {step["name"]: step for step in cls.steps if "name" in step}

    def position(self, name):
        return self.steps.index(self.by_name[name])

    def test_workflow_step_ids_and_execution_modes_are_unambiguous(self):
        ids = [step["id"] for step in self.steps if "id" in step]
        self.assertEqual(len(ids), len(set(ids)))
        for step in self.steps:
            self.assertFalse("uses" in step and "run" in step)
            if "run" in step:
                subprocess.run(["bash", "-n"], input=step["run"], text=True,
                               capture_output=True, check=True)

    def test_source_contract_and_outbox_precede_pruning_and_upload(self):
        for before, after in (
            ("Build and validate source-bound owned feeds", "Prepare content-change-only syndication"),
            ("Restore durable syndication outbox", "Prepare content-change-only syndication"),
            ("Prepare content-change-only syndication", "Checkpoint pending syndication before deployment"),
            ("Checkpoint pending syndication before deployment", "Preserve syndication notifiers and prune engine/tooling"),
            ("Preserve syndication notifiers and prune engine/tooling", "Upload artifact"),
        ):
            self.assertLess(self.position(before), self.position(after))
        build = self.by_name["Build and validate source-bound owned feeds"]["run"]
        self.assertIn("owned_app_feeds.py --pages-dir . --check", build)
        prepare = self.by_name["Prepare content-change-only syndication"]["run"]
        self.assertIn('--source-sha "$(git rev-parse HEAD)"', prepare)
        self.assertIn("--include-legacy", prepare)

    def test_private_outbox_has_a_predeploy_checkpoint_and_always_saved_receipts(self):
        restore = self.by_name["Restore durable syndication outbox"]
        pending = self.by_name["Checkpoint pending syndication before deployment"]
        final = self.by_name["Persist acknowledged and pending syndication"]
        self.assertEqual("actions/cache/restore@v4", restore["uses"])
        self.assertEqual("actions/cache/save@v4", pending["uses"])
        self.assertEqual("actions/cache/save@v4", final["uses"])
        self.assertEqual(restore["with"]["key"], final["with"]["key"])
        self.assertNotEqual(pending["with"]["key"], final["with"]["key"])
        self.assertEqual("owned-feed-delivery-v1-", restore["with"]["restore-keys"])
        self.assertIn("always()", final["if"])
        for step in (restore, pending, final):
            self.assertEqual(".github/owned-feed-runtime/state.json", step["with"]["path"])
            self.assertIn("github.run_attempt", step["with"]["key"])
        self.assertIn(".github/owned-feed-runtime/", (ROOT / ".gitignore").read_text())

    def test_notifications_use_only_source_bound_outbox_after_full_readback(self):
        for name, protocol in (
            ("Notify WebSub subscribers", "websub"),
            ("Notify rssCloud subscribers", "rsscloud"),
        ):
            step = self.by_name[name]
            self.assertIn("steps.verify_owned_feeds.outcome == 'success'", step["if"])
            self.assertIn("steps.verify_live.outcome == 'success'", step["if"])
            self.assertIn("steps.verify_hero.outcome == 'success'", step["if"])
            self.assertIn("owned_feed_delivery.py notify", step["run"])
            self.assertIn("--protocol " + protocol, step["run"])
            self.assertIn('--source-sha "$(git rev-parse HEAD)"', step["run"])
            self.assertNotIn("--feed-dir", step["run"])

    def test_delivery_runtime_dependencies_survive_engine_pruning_outside_public_files(self):
        prune = self.by_name["Preserve syndication notifiers and prune engine/tooling"]["run"]
        for filename in (
            "owned_feed_delivery.py", "notify_websub.py", "notify_rsscloud.py",
            "websub_config.py", "rsscloud_config.py", "official_locales.py",
        ):
            self.assertIn(filename, prune)
        self.assertIn('".github/owned-feed-runtime/$source"', prune)
        self.assertLess(prune.index("cp "), prune.index("rm -rf _engine"))


if __name__ == "__main__":
    unittest.main()
