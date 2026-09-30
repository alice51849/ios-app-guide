import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch
import uuid

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))
import notification_release as release
import owned_feed_delivery
import notify_websub
import notify_rsscloud
import indexnow_submit


class NotificationReleaseTests(unittest.TestCase):
    def setUp(self):
        self.root = GEO / ".owned-feed-test-work" / uuid.uuid4().hex
        self.root.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.root)
        if not any(self.root.parent.iterdir()):
            self.root.parent.rmdir()

    @staticmethod
    def pages_job():
        import yaml
        guide = Path(os.environ.get("OWNED_FEED_GUIDE_ROOT", os.environ.get(
            "GEO_PAGES", str(GEO.parents[1] if GEO.parent.name == "_engine" else GEO / "pages")
        )))
        return yaml.safe_load((guide / ".github/workflows/pages.yml").read_text())["jobs"]["deploy"]

    @staticmethod
    def step(job, step_id):
        return next(step for step in job["steps"] if step.get("id") == step_id)

    def held_policy(self):
        return {**release.read_policy(), "notification_release_hold": True}

    def test_policy_is_explicitly_released_by_caitlyn_for_all_three_providers(self):
        # 2026-09-30: Caitlyn explicitly authorized the separate notification
        # release that geo/owned_app_feeds.md (round 4) required.
        policy = release.read_policy()
        self.assertIs(policy["notification_release_hold"], False)
        self.assertEqual({"websub", "rsscloud", "indexnow"}, set(policy["providers"]))
        self.assertIn("2026-09-30 Caitlyn 明確授權放行", policy["reason"])
        for protocol in ("websub", "rsscloud", "indexnow", "owned-feeds"):
            self.assertIsNone(release.held_result(protocol))
        job = self.pages_job()
        self.assertEqual("118326163", job["env"]["APP_STORE_PROVIDER_TOKEN"])
        self.assertEqual("https://open.cait518.cc/ios-app-guide", job["env"]["GEO_SITE"])
        self.assertEqual("${{ github.workspace }}", job["env"]["GEO_PAGES"])
        # Paired deploys stay single-attempt: no blind second deployment.
        self.assertEqual("true", job["env"]["NOTIFICATION_RELEASE_HOLD"])

    def run_policy_step(self, policy, *, paired, dispatch_hold):
        """Execute the workflow's policy step against a checked-out policy."""
        job = self.pages_job()
        script = self.step(job, "release_policy")["run"]
        body = script.split("<<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
        checkout = self.root / "checkout"
        engine = checkout / "_engine" / "geo"
        engine.mkdir(parents=True, exist_ok=True)
        shutil.copy2(GEO / "notification_release.py", engine / "notification_release.py")
        (engine / "notification_policy.json").write_text(json.dumps(policy), encoding="utf-8")
        output = self.root / "github_output"
        output.write_text("", encoding="utf-8")
        env = {
            "PATH": os.environ.get("PATH", ""), "GITHUB_OUTPUT": str(output),
            "PYTHONPATH": "_engine/geo", "PYTHONDONTWRITEBYTECODE": "1",
            "PAIRED_RELEASE": "true" if paired else "false",
            "DISPATCH_NOTIFICATION_RELEASE_HOLD": dispatch_hold,
        }
        result = subprocess.run(
            [sys.executable, "-"], input=body, text=True, cwd=checkout, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        return result, output.read_text(encoding="utf-8")

    def test_pages_policy_step_requires_the_dispatch_to_match_the_checked_out_policy(self):
        env = self.step(self.pages_job(), "release_policy")["env"]
        self.assertNotIn("inputs.notification_release_hold == true", env["PAIRED_RELEASE"])
        self.assertEqual("${{ inputs.notification_release_hold }}", env["DISPATCH_NOTIFICATION_RELEASE_HOLD"])
        released = release.read_policy()
        held = self.held_policy()
        cases = (
            (released, True, "false", 0, "allow_upload=true"),
            (released, True, "true", 1, None),
            (held, True, "true", 0, "allow_upload=true"),
            (held, True, "false", 1, None),
            (released, False, "", 0, "allow_upload=false"),
            (held, False, "", 0, "allow_upload=false"),
        )
        for policy, paired, dispatch_hold, returncode, upload in cases:
            with self.subTest(hold=policy["notification_release_hold"], paired=paired, dispatch=dispatch_hold):
                result, output = self.run_policy_step(policy, paired=paired, dispatch_hold=dispatch_hold)
                self.assertEqual(returncode, result.returncode, result.stderr)
                if upload:
                    self.assertIn(upload, output.splitlines())
                    self.assertIs(policy["notification_release_hold"],
                                  json.loads(result.stdout)["notification_release_hold"])
                else:
                    self.assertNotIn("allow_upload=true", output)
        broken = {**released, "notification_release_hold": "false"}
        result, output = self.run_policy_step(broken, paired=True, dispatch_hold="false")
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn("allow_upload=true", output)

    def test_pages_only_prepares_the_feed_outbox_for_a_run_that_uploads(self):
        job = self.pages_job()
        for step_name in ("Restore durable feed acknowledgement state",
                          "Prepare content-addressed feed notifications"):
            step = next(step for step in job["steps"] if step.get("name") == step_name)
            with self.subTest(step=step_name):
                self.assertIn("steps.release_policy.outputs.allow_upload == 'true'", step["if"])
                self.assertIn("inputs.incremental_high_intent != true", step["if"])
        readback = self.step(job, "verify_owned_feeds")["run"]
        self.assertIn('read_policy()["notification_release_hold"]', readback)
        self.assertIn("assert result is None", readback)

    def test_all_notification_cli_entrypoints_return_zero_without_network_or_inventory(self):
        # The hold mechanism stays intact for any future re-hold.
        cases = (
            (owned_feed_delivery.main, ["tool", "prepare", "--pages-dir", str(self.root),
                                       "--state", str(self.root / "state.json"), "--source-sha", "a" * 40]),
            (owned_feed_delivery.main, ["tool", "notify", "--pages-dir", str(self.root),
                                       "--state", str(self.root / "state.json"), "--source-sha", "a" * 40,
                                       "--protocol", "websub", "--execute"]),
            (notify_websub.main, ["tool", "--feed-dir", str(self.root)]),
            (notify_rsscloud.main, ["tool", "--feed-dir", str(self.root)]),
            (indexnow_submit.main, ["tool", "--pages-dir", str(self.root),
                                    "--receipt-file", str(self.root / "indexnow.json")]),
        )
        with patch("urllib.request.urlopen", side_effect=AssertionError("No network")) as network, \
             patch("socket.create_connection", side_effect=AssertionError("No sockets")) as sockets, \
             patch.object(release, "read_policy", return_value=self.held_policy()):
            for main, argv in cases:
                output = io.StringIO()
                with self.subTest(argv=argv), patch.object(sys, "argv", argv), contextlib.redirect_stdout(output):
                    main()
                result = json.loads(output.getvalue())
                self.assertTrue(result["notification_release_hold"])
                self.assertEqual(0, result["provider_intents"])
                self.assertEqual(0, result["provider_requests"])
                self.assertEqual(0, result["accepted_ack"])
                self.assertFalse(result["indexing_verified"])
        network.assert_not_called()
        sockets.assert_not_called()
        self.assertFalse((self.root / "state.json").exists())
        self.assertEqual(0o600, (self.root / "indexnow.json").stat().st_mode & 0o777)

    def test_missing_or_malformed_policy_fails_closed(self):
        with self.assertRaises(OSError):
            release.read_policy(self.root / "missing.json")
        path = self.root / "invalid.json"
        path.write_text('{"notification_release_hold":"true"}')
        with self.assertRaises(ValueError):
            release.read_policy(path)

    def test_false_policy_is_not_an_implicit_notification(self):
        path = self.root / "policy.json"
        policy = release.read_policy()
        policy["notification_release_hold"] = False
        path.write_text(json.dumps(policy))
        self.assertIsNone(release.held_result("websub", policy_path=path))
        policy["notification_release_hold"] = True
        path.write_text(json.dumps(policy))
        held = release.held_result("indexnow", policy_path=path)
        self.assertEqual((0, 0, 0), (held["provider_intents"], held["provider_requests"], held["accepted_ack"]))

    def test_released_policy_still_sends_nothing_from_unbound_or_unreconciled_entrypoints(self):
        # Local callers (agent tactic, publish.py, promo burst) never carry the
        # durable IndexNow bindings, and the WebSub/rssCloud outbox still needs a
        # reconciled durable state: neither may turn the release into requests.
        receipt = self.root / "indexnow.json"
        with patch("urllib.request.urlopen", side_effect=AssertionError("No network")) as network, \
             patch("socket.create_connection", side_effect=AssertionError("No sockets")) as sockets, \
             patch.object(indexnow_submit, "run", side_effect=AssertionError("unbound run")) as run:
            for extra in ([], ["--git-since", "25 hours ago"], ["--receipt-file", str(receipt)]):
                argv = ["tool", "--pages-dir", str(self.root), *extra]
                output = io.StringIO()
                with self.subTest(argv=argv), patch.object(sys, "argv", argv), contextlib.redirect_stdout(output):
                    indexnow_submit.main()
                result = json.loads(output.getvalue())
                self.assertEqual("lumi.indexnow-unbound-run/v1", result["schema"])
                self.assertEqual((0, 0, 0), (result["provider_intents"], result["provider_requests"],
                                             result["accepted_ack"]))
            for argv in (
                ["prepare", "--pages-dir", str(self.root), "--state", str(self.root / "state.json"),
                 "--source-sha", "a" * 40],
                ["notify", "--pages-dir", str(self.root), "--state", str(self.root / "state.json"),
                 "--source-sha", "a" * 40, "--protocol", "websub", "--execute"],
            ):
                with self.subTest(argv=argv), contextlib.redirect_stderr(io.StringIO()), \
                     self.assertRaises(SystemExit):
                    owned_feed_delivery.main(argv)
        network.assert_not_called()
        sockets.assert_not_called()
        run.assert_not_called()
        self.assertFalse(receipt.exists())
        self.assertFalse((self.root / "state.json").exists())

    def test_released_policy_submits_only_through_the_durable_state_workflow(self):
        argv = [
            "tool", "--pages-dir", str(self.root), "--git-since", "25 hours ago",
            "--state-file", str(self.root / "last-submitted-sha"),
            "--receipt-file", str(self.root / "accepted-receipt.json"),
            "--content-state", str(self.root / "content-digests.json"),
        ]
        with patch.object(sys, "argv", argv), patch.object(indexnow_submit, "run", return_value=0) as run:
            indexnow_submit.main()
        run.assert_called_once()
        self.assertEqual(self.root / "content-digests.json", run.call_args.kwargs["content_state_file"])


if __name__ == "__main__":
    unittest.main()
