from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from owned_feed_fixtures import FeedFixture, Response, feeds
import owned_feed_release as release


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

    def test_sealed_manifest_is_generation_bound_and_idempotent(self):
        path = self.pages / release.MANIFEST
        before = path.read_bytes(), path.stat().st_mtime_ns
        manifest = release.seal(self.pages)
        self.assertEqual(before, (path.read_bytes(), path.stat().st_mtime_ns))
        self.assertTrue(manifest["notification_release_hold"])
        self.assertEqual(150, manifest["feed_count"])
        self.assertEqual(2350, manifest["record_count"])
        self.assertEqual(0, manifest["provider_requests"])

    def test_both_hosts_require_all_150_exact_feeds_without_authorizing_notifications(self):
        result = release.verify(self.pages, opener=self.opener, attempts=1)
        self.assertEqual([150, 150], [row["valid"] for row in result["hosts"].values()])
        self.assertFalse(result["next_notification_release_eligibility"]["dispatch_authorized"])
        self.assertTrue(result["notification_release_hold"])
        self.assertEqual(0, result["provider_intents"])
        self.assertEqual(0, result["provider_requests"])

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
            with self.subTest(error=error), self.assertRaises(ValueError):
                release.verify(self.pages, opener=bad, attempts=1)
            self.assertTrue(feeds.read_json(self.pages / release.MANIFEST)["notification_release_hold"])

    def test_seal_refuses_unheld_policy(self):
        with patch.object(release, "read_policy", return_value={"notification_release_hold": False}):
            with self.assertRaisesRegex(ValueError, "hold=true"):
                release.seal(self.pages)
