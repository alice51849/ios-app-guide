import contextlib
import io
import json
from pathlib import Path
import shutil
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

    def test_policy_is_explicit_true_for_all_three_providers(self):
        policy = release.read_policy()
        self.assertIs(policy["notification_release_hold"], True)
        self.assertEqual({"websub", "rsscloud", "indexnow"}, set(policy["providers"]))

    def test_all_notification_cli_entrypoints_return_zero_without_network_or_inventory(self):
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
             patch("socket.create_connection", side_effect=AssertionError("No sockets")) as sockets:
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


if __name__ == "__main__":
    unittest.main()
