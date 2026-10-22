from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from owned_feed_fixtures import FeedFixture, Response, feeds
import notification_release
import owned_feed_release as release
from live_app_manifest import canonical_manifest

# The roster is the single source of truth for how many public Apps exist;
# spelling the count out here goes stale the day a new App ships.
ROSTER_APP_COUNT = len(canonical_manifest()["apps"])


class OwnedFeedReleaseTests(FeedFixture):
    def setUp(self):
        super().setUp()
        release.seal(self.pages)

    def opener(self, request, timeout=0):
        self.assertEqual("GET", request.get_method())
        host = next(host for host in release.HOSTS if request.full_url.startswith(host + "/"))
        relative = request.full_url[len(host) + 1:]
        raw = (self.pages / relative).read_bytes()
        response = Response(raw, "application/json" if relative.endswith(".json") else "application/xml")
        response.geturl = lambda: request.full_url
        return response

    def policy(self, hold: bool) -> dict:
        return {**notification_release.read_policy(), "notification_release_hold": hold}

    def test_sealed_manifest_is_generation_bound_and_idempotent(self):
        path = self.pages / release.MANIFEST
        before = path.read_bytes(), path.stat().st_mtime_ns
        manifest = release.seal(self.pages)
        self.assertEqual(before, (path.read_bytes(), path.stat().st_mtime_ns))
        self.assertIs(notification_release.read_policy()["notification_release_hold"],
                      manifest["notification_release_hold"])
        self.assertEqual(150, manifest["feed_count"])
        self.assertEqual(ROSTER_APP_COUNT * 50, manifest["record_count"])
        self.assertEqual(0, manifest["provider_intents"])
        self.assertEqual(0, manifest["provider_requests"])

    def test_both_hosts_require_all_150_exact_feeds_and_report_the_policy_in_force(self):
        for hold in (False, True):
            with self.subTest(hold=hold), patch.object(release, "read_policy", return_value=self.policy(hold)):
                release.seal(self.pages)
                result = release.verify(self.pages, opener=self.opener, attempts=1)
                self.assertEqual([150, 150], [row["valid"] for row in result["hosts"].values()])
                eligibility = result["next_notification_release_eligibility"]
                self.assertIs(not hold, eligibility["dispatch_authorized"])
                self.assertIs(hold, result["notification_release_hold"])
                # Sealing and readback never notify providers themselves.
                self.assertEqual(0, result["provider_intents"])
                self.assertEqual(0, result["provider_requests"])
                if not hold:
                    self.assertIn("2026-09-30 Caitlyn", eligibility["authorization"])
                    self.assertTrue(any("WebSub/rssCloud" in item for item in eligibility["requires"]))

    def test_partial_feed_redirect_or_html_mime_cannot_release_hold(self):
        for error in ("body", "redirect", "mime"):
            def bad(request, timeout=0):
                response = self.opener(request, timeout)
                if request.full_url.endswith("/bn-BD/feed.xml"):
                    if error == "body":
                        response.raw = b"<partial/>"
                    elif error == "redirect":
                        response.geturl = lambda: "https://example.org/redirect"
                    else:
                        response.headers.replace_header("Content-Type", "text/html")
                return response
            before = (self.pages / release.MANIFEST).read_bytes()
            with self.subTest(error=error), self.assertRaises(ValueError):
                release.verify(self.pages, opener=bad, attempts=1)
            self.assertEqual(before, (self.pages / release.MANIFEST).read_bytes())

    def test_verify_rejects_a_manifest_sealed_under_another_policy(self):
        for sealed, current in ((False, True), (True, False)):
            with self.subTest(sealed=sealed, current=current):
                with patch.object(release, "read_policy", return_value=self.policy(sealed)):
                    release.seal(self.pages)
                with patch.object(release, "read_policy", return_value=self.policy(current)), \
                     self.assertRaisesRegex(ValueError, "policy drift"):
                    release.verify(self.pages, opener=self.opener, attempts=1)

    def test_seal_fails_closed_on_a_malformed_policy(self):
        path = self.pages.parent / "malformed-policy.json"
        path.write_text('{"notification_release_hold":"false"}', encoding="utf-8")
        before = (self.pages / release.MANIFEST).read_bytes()
        with patch.object(release, "read_policy", lambda: notification_release.read_policy(path)), \
             self.assertRaises(ValueError):
            release.seal(self.pages)
        self.assertEqual(before, (self.pages / release.MANIFEST).read_bytes())
