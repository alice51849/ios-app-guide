import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest import mock
from urllib.error import URLError
from uuid import uuid4


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import devto_post


class Response:
    def __init__(self, body, url, status=200):
        self.body, self.url, self.status = body, url, status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def geturl(self):
        return self.url

    def read(self, limit):
        return self.body[:limit]


class BuyerGuideSyndicationTests(unittest.TestCase):
    URL = "https://open.cait518.cc/ios-app-guide/buyer-guides/en-US/maskmyfile-test.html"
    BODY = b"<main>Explicit unit-test fixture, not public evidence.</main>"

    def article(self):
        return {
            "title": "A verified-source unit-test article",
            "body": "First-party unit-test body",
            "canonical_url": self.URL,
            "source_sha256": hashlib.sha256(self.BODY).hexdigest(),
            "tags": ["privacy"],
        }

    def fixture(self, candidates=None):
        parent = HERE / ".buyer-guide-test-work"
        root = parent / uuid4().hex
        root.mkdir(parents=True)
        def cleanup():
            shutil.rmtree(root)
            try:
                parent.rmdir()
            except OSError:
                pass
        self.addCleanup(cleanup)
        (root / "devto_articles.json").write_text(json.dumps([{"title": "Existing", "body": "Keep"}]))
        if candidates is not None:
            (root / devto_post.BUYER_GUIDE_POOL).write_text(json.dumps(candidates))
        return root

    def test_missing_optional_queue_preserves_existing_pool(self):
        with mock.patch.object(devto_post, "HERE", str(self.fixture())):
            self.assertEqual([{"title": "Existing", "body": "Keep"}], devto_post.load_pool())

    def test_new_queue_is_additive_and_never_published_by_loading(self):
        with (
            mock.patch.object(devto_post, "HERE", str(self.fixture([self.article()]))),
            mock.patch.object(devto_post, "_publish") as publish,
            mock.patch.object(devto_post.urllib.request, "urlopen") as fetch,
        ):
            pool = devto_post.load_pool()
        self.assertEqual(["Existing", self.article()["title"]], [row["title"] for row in pool])
        publish.assert_not_called()
        fetch.assert_not_called()

    def test_new_queue_without_digest_is_rejected(self):
        article = self.article()
        del article["source_sha256"]
        with mock.patch.object(devto_post, "HERE", str(self.fixture([article]))):
            with self.assertRaises(ValueError):
                devto_post.load_pool()

    def test_non_list_queue_is_rejected(self):
        with mock.patch.object(devto_post, "HERE", str(self.fixture({"not": "a list"}))):
            with self.assertRaises(ValueError):
                devto_post.load_pool()

    def test_unowned_canonical_is_rejected_without_network(self):
        article = {**self.article(), "canonical_url": "https://example.com/fake.html"}
        with mock.patch.object(devto_post.urllib.request, "urlopen") as fetch:
            with self.assertRaises(ValueError):
                devto_post.buyer_guide_source_is_live(article)
            fetch.assert_not_called()

    def test_legacy_article_does_not_gain_a_network_probe(self):
        with mock.patch.object(devto_post.urllib.request, "urlopen") as fetch:
            self.assertTrue(devto_post.buyer_guide_source_is_live({"title": "Existing", "body": "Keep"}))
            fetch.assert_not_called()

    def test_exact_get_bytes_are_required_before_candidate_can_publish(self):
        article = self.article()
        response = Response(self.BODY, self.URL)
        with mock.patch.object(devto_post.urllib.request, "urlopen", return_value=response) as fetch:
            self.assertTrue(devto_post.buyer_guide_source_is_live(article))
        request = fetch.call_args.args[0]
        self.assertEqual("GET", request.get_method())
        self.assertEqual(self.URL, request.full_url)
        self.assertIsNone(request.get_header("Api-key"))
        self.assertEqual(25, fetch.call_args.kwargs["timeout"])

    def test_http_200_with_old_or_placeholder_body_is_not_live(self):
        with mock.patch.object(devto_post.urllib.request, "urlopen", return_value=Response(b"old body", self.URL)):
            self.assertFalse(devto_post.buyer_guide_source_is_live(self.article()))

    def test_redirect_does_not_count_as_the_exact_canonical(self):
        with mock.patch.object(devto_post.urllib.request, "urlopen", return_value=Response(self.BODY, self.URL + "/")):
            self.assertFalse(devto_post.buyer_guide_source_is_live(self.article()))

    def test_non_200_does_not_count_as_live(self):
        with mock.patch.object(devto_post.urllib.request, "urlopen", return_value=Response(self.BODY, self.URL, 404)):
            self.assertFalse(devto_post.buyer_guide_source_is_live(self.article()))

    def test_unavailable_source_stays_pending(self):
        with mock.patch.object(devto_post.urllib.request, "urlopen", side_effect=URLError("unavailable")):
            self.assertFalse(devto_post.buyer_guide_source_is_live(self.article()))

    def test_oversized_response_is_rejected(self):
        body = b"x" * 1_048_577
        article = {**self.article(), "source_sha256": hashlib.sha256(body).hexdigest()}
        with mock.patch.object(devto_post.urllib.request, "urlopen", return_value=Response(body, self.URL)):
            self.assertFalse(devto_post.buyer_guide_source_is_live(article))

    def test_unpublished_candidate_is_skipped_but_legacy_pool_can_continue(self):
        pool = [self.article(), {"title": "Existing", "body": "Keep"}]
        with (
            mock.patch.object(devto_post, "buyer_guide_source_is_live", side_effect=[False, True]),
            mock.patch.object(devto_post, "validate_url", return_value=True),
            mock.patch("sys.stderr", new_callable=io.StringIO),
        ):
            self.assertEqual("Existing", devto_post.next_publishable(pool, [])["title"])

    def test_title_change_does_not_duplicate_a_canonical_already_published(self):
        published = [{"title": "Previous title", "canonical_url": self.URL, "published_at": "2026-09-10T10:00:00Z"}]
        self.assertIsNone(devto_post.next_unpublished([self.article()], published))
        with mock.patch.object(devto_post, "buyer_guide_source_is_live") as fetch:
            self.assertIsNone(devto_post.next_publishable([self.article()], published))
            fetch.assert_not_called()

    def test_existing_title_still_deduplicates(self):
        self.assertIsNone(devto_post.next_unpublished([self.article()], [{"title": self.article()["title"]}]))

    def test_canonical_deduplication_preserves_72_hour_cadence(self):
        published = [{"title": "Previous title", "canonical_url": self.URL, "published_at": "2026-09-10T10:00:00Z"}]
        before = dt.datetime(2026, 9, 13, 9, 59, 59, tzinfo=dt.timezone.utc)
        boundary = dt.datetime(2026, 9, 13, 10, tzinfo=dt.timezone.utc)
        self.assertFalse(devto_post.publication_due([self.article()], published, before))
        self.assertTrue(devto_post.publication_due([self.article()], published, boundary))

    def test_publish_payload_keeps_first_party_canonical(self):
        with mock.patch.object(devto_post, "request_json", return_value={"url": "https://dev.to/example/unit-test"}) as send:
            devto_post._publish("unit-test-key", self.article())
        request = send.call_args.args[0]
        payload = json.loads(request.data)["article"]
        self.assertEqual(self.URL, payload["canonical_url"])
        self.assertEqual(self.article()["body"], payload["body_markdown"])
        self.assertNotIn("source_sha256", payload)

    def test_real_candidate_is_bound_to_existing_generated_html(self):
        candidates = json.loads((HERE / devto_post.BUYER_GUIDE_POOL).read_text())
        self.assertEqual(1, len(candidates))
        pages = HERE.parents[1]
        for article in candidates:
            devto_post._validate_buyer_guide(article)
            relative = article["canonical_url"].split("/ios-app-guide/", 1)[1]
            self.assertEqual(hashlib.sha256((pages / relative).read_bytes()).hexdigest(), article["source_sha256"])

    def test_cloud_seals_buyer_guides_in_initial_fast_localized_and_rebase_paths(self):
        workflow = (HERE.parent / "workflows/geo-daily.yml").read_text()
        self.assertEqual(5, workflow.count("python3 _engine/geo/buyer_job_guides.py --pages"))
        for name in ["reconcile_english_phase()", "reconcile_localized_phase()"]:
            start = workflow.index(name)
            end = workflow.index("export REMOTE_FIRST_RECONCILE_MESSAGE", start)
            function = workflow[start:end]
            self.assertIn("python3 _engine/geo/buyer_job_guides.py --pages", function)
            self.assertLess(function.index("buyer_job_guides.py"), function.index("parallel_unittest.py"))


if __name__ == "__main__":
    unittest.main()
