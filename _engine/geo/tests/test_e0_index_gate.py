from pathlib import Path
import sys
import unittest

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))
import e0_index_gate as gate

class E0FailClosedTest(unittest.TestCase):
    def _sitemap(self, pending=False, downloaded="2026-09-10T00:00:00Z", known=True):
        return gate.SitemapStatus(path="s.xml", is_pending=pending,
                                  last_downloaded=downloaded, known=known)

    def _page(self, coverage, verdict="PASS", known=True, crawl="2026-09-08T00:00:00Z"):
        return gate.DeepPageStatus(path="guides/x.html", coverage_state=coverage,
                                   last_crawl_time=crawl, verdict=verdict, known=known)

    def test_indexed_and_processed_sitemap_passes(self) -> None:
        result = gate.evaluate_gate("https://x/", [self._page("Submitted and indexed")], self._sitemap())
        self.assertEqual(result.status, gate.GATE_PASS)
        self.assertTrue(result.allows_e1_e2)

    def test_crawled_but_not_indexed_must_not_pass(self) -> None:
        """'Crawled - currently not indexed' 含子字串 indexed,不可被誤判。"""
        page = self._page("Crawled - currently not indexed", verdict="NEUTRAL")
        self.assertFalse(page.indexed)
        result = gate.evaluate_gate("https://x/", [page], self._sitemap())
        self.assertEqual(result.status, gate.GATE_BLOCKED)
        self.assertFalse(result.allows_e1_e2)

    def test_discovered_not_indexed_must_not_pass(self) -> None:
        page = self._page("Discovered - currently not indexed", verdict="NEUTRAL")
        self.assertFalse(page.indexed)

    def test_unknown_to_google_must_not_pass(self) -> None:
        result = gate.evaluate_gate("https://x/",
                                    [self._page("URL is unknown to Google", verdict="NEUTRAL")],
                                    self._sitemap())
        self.assertEqual(result.status, gate.GATE_BLOCKED)

    def test_pending_sitemap_blocks_even_when_indexed(self) -> None:
        result = gate.evaluate_gate("https://x/", [self._page("Submitted and indexed")],
                                    self._sitemap(pending=True, downloaded=None))
        self.assertEqual(result.status, gate.GATE_BLOCKED)

    def test_no_sitemap_data_is_unknown_not_pass(self) -> None:
        result = gate.evaluate_gate("https://x/", [self._page("Submitted and indexed")],
                                    self._sitemap(known=False))
        self.assertEqual(result.status, gate.GATE_UNKNOWN)
        self.assertFalse(result.allows_e1_e2)
        self.assertIn("sitemap", result.unknown_fields)

    def test_no_deep_pages_is_unknown_not_pass(self) -> None:
        result = gate.evaluate_gate("https://x/", [], self._sitemap())
        self.assertEqual(result.status, gate.GATE_UNKNOWN)
        self.assertFalse(result.allows_e1_e2)

    def test_unknown_page_keeps_gate_closed_even_if_another_is_indexed(self) -> None:
        pages = [self._page("Submitted and indexed"),
                 gate.DeepPageStatus(path="b.html", coverage_state=None, last_crawl_time=None,
                                     verdict=None, known=False)]
        result = gate.evaluate_gate("https://x/", pages, self._sitemap())
        self.assertEqual(result.status, gate.GATE_UNKNOWN)
        self.assertFalse(result.allows_e1_e2)

    def test_unknown_is_never_filled_with_zero(self) -> None:
        page = gate.DeepPageStatus(path="b.html", coverage_state=None, last_crawl_time=None,
                                   verdict=None, known=False)
        self.assertIsNone(page.coverage_state)
        self.assertIsNone(page.last_crawl_time)
        payload = gate.evaluate_gate("https://x/", [page], self._sitemap()).to_dict()
        self.assertIsNone(payload["deep_pages"][0]["coverage_state"])

    def test_mutation_ops_are_refused(self) -> None:
        for op in ("sitemaps.submit", "sites.add", "sitemaps.delete"):
            with self.assertRaises(gate.MutationAttempted):
                gate.assert_read_only(op)

    def test_collect_gate_never_calls_mutation(self) -> None:
        seen: list[str] = []

        def query(op, params):
            seen.append(op)
            if op == "sitemaps.list":
                return {"sitemap": [{"path": "s.xml", "isPending": True, "lastDownloaded": None}]}
            return {"inspectionResult": {"indexStatusResult": {
                "verdict": "NEUTRAL", "coverageState": "URL is unknown to Google"}}}

        result = gate.collect_gate(query, "https://x/", ["a.html"])
        self.assertTrue(set(seen).issubset(gate.READ_ONLY_OPS))
        self.assertFalse(result.allows_e1_e2)

    def test_backoff_is_monotonic_and_capped(self) -> None:
        values = [gate.next_backoff_minutes(i) for i in range(8)]
        self.assertEqual(values, sorted(values))
        self.assertEqual(values[-1], gate.BACKOFF_MINUTES[-1])
        with self.assertRaises(ValueError):
            gate.next_backoff_minutes(-1)

class CanarySelectionTest(unittest.TestCase):
    def test_count_must_stay_between_6_and_12(self) -> None:
        for bad in (5, 13):
            with self.assertRaises(ValueError):
                gate.select_canaries(Path("/nonexistent"), [], count=bad)

    def test_only_existing_pages_are_selected(self, ) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i in range(8):
                (root / f"p{i}.html").write_text("<p>" + ("word " * (100 + i * 10)) + "</p>",
                                                 encoding="utf-8")
            picked = gate.select_canaries(root, [f"p{i}.html" for i in range(8)] + ["ghost.html"], 6)
            self.assertEqual(len(picked), 6)
            self.assertNotIn("ghost.html", {p["path"] for p in picked})
            self.assertEqual(picked[0]["path"], "p7.html")

    def test_proposal_forbids_doorways_and_submission(self) -> None:
        proposal = gate.discovery_proposal([{"path": "a.html"}])
        self.assertEqual(proposal["kind"], "internal_discovery_only")
        blob = " ".join(proposal["forbidden"])
        self.assertIn("doorway", blob)
        self.assertIn("IndexNow", blob)
        self.assertIn("部署", blob)
        self.assertTrue(proposal["reversible"])


class ExactReadOnlyE0Test(unittest.TestCase):
    def page(self, coverage="Submitted and indexed", verdict="PASS", path="answers/example.html"):
        return gate.DeepPageStatus(path, coverage, None, verdict, True)

    def sitemap(self, pending=False, downloaded="2026-09-10T00:00:00Z"):
        return gate.SitemapStatus("https://x/sitemap_index.xml", pending, downloaded, True)

    def test_homepage_verdict_pass_cannot_open_deep_entry_gate(self):
        self.assertFalse(self.page(path="index.html").indexed)
        self.assertFalse(gate.evaluate_gate("https://x/", [self.page(path="index.html")], self.sitemap()).allows_e1_e2)

    def test_crawled_not_indexed_is_blocked_even_with_inconsistent_pass_verdict(self):
        page = self.page(coverage="Crawled - currently not indexed")
        self.assertFalse(page.indexed)
        self.assertEqual("BLOCKED", gate.evaluate_gate("https://x/", [page], self.sitemap()).status)

    def test_unindexed_substring_is_not_a_positive_coverage_status(self):
        self.assertFalse(self.page(coverage="Unindexed").indexed)
        self.assertTrue(self.page(coverage="Indexed, not submitted in sitemap").indexed)

    def test_missing_required_fields_stay_unknown_not_zero(self):
        result = gate.evaluate_gate("https://x/", [self.page(coverage=None)], self.sitemap())
        self.assertEqual("UNKNOWN", result.status)
        self.assertIsNone(result.to_dict()["indexed_deep_pages"])
        self.assertFalse(result.allows_e1_e2)

    def test_sitemap_pending_must_be_actual_false_not_numeric_zero(self):
        result = gate.evaluate_gate("https://x/", [self.page()], self.sitemap(pending=0))
        self.assertEqual("UNKNOWN", result.status)
        self.assertFalse(result.allows_e1_e2)

    def test_sitemap_last_downloaded_must_not_be_empty(self):
        for value in (None, "", "  "):
            with self.subTest(value=value):
                self.assertFalse(gate.evaluate_gate("https://x/", [self.page()], self.sitemap(downloaded=value)).allows_e1_e2)

    def test_exact_sitemap_is_selected_not_an_arbitrary_processed_first_entry(self):
        def query(op, params):
            if op == "urlInspection.inspect":
                return {"inspectionResult": {"indexStatusResult": {"coverageState": "Submitted and indexed", "verdict": "PASS"}}}
            return {"sitemap": [
                {"path": "https://x/unrelated.xml", "isPending": False, "lastDownloaded": "2026-09-10"},
                {"path": "https://x/sitemap_index.xml", "isPending": True},
            ]}
        result = gate.collect_gate(query, "https://x/", ["answers/example.html"])
        self.assertEqual("BLOCKED", result.status)
        self.assertEqual("https://x/sitemap_index.xml", result.sitemap.path)

    def test_missing_exact_sitemap_does_not_fall_back_to_another_property(self):
        def query(op, params):
            if op == "urlInspection.inspect":
                return {"inspectionResult": {"indexStatusResult": {"coverageState": "Submitted and indexed", "verdict": "PASS"}}}
            return {"sitemap": [{"path": "https://other.example/sitemap_index.xml", "isPending": False, "lastDownloaded": "2026-09-10"}]}
        self.assertEqual("UNKNOWN", gate.collect_gate(query, "https://x/", ["answers/example.html"]).status)

    def test_only_status_and_inspection_operations_are_allowed(self):
        self.assertEqual({"sitemaps.list", "urlInspection.inspect"}, set(gate.READ_ONLY_OPS))
        for op in ("sites.add", "sitemaps.submit", "sitemaps.delete", "searchanalytics.query", "urlInspection.requestIndexing"):
            with self.subTest(op=op), self.assertRaises(gate.MutationAttempted):
                gate.assert_read_only(op)

    def test_unknown_api_and_empty_inspection_do_not_claim_indexed(self):
        def query(op, params):
            if op == "urlInspection.inspect":
                return {}
            return {"sitemap": [{"path": "https://x/sitemap_index.xml", "isPending": False, "lastDownloaded": "2026-09-10"}]}
        result = gate.collect_gate(query, "https://x/", ["answers/example.html"])
        self.assertEqual("UNKNOWN", result.status)
        self.assertIsNone(result.to_dict()["indexed_deep_pages"])

    def test_valid_deep_pass_plus_downloaded_sitemap_opens_gate_without_inferring_impact(self):
        self.assertEqual("PASS", gate.evaluate_gate("https://x/", [self.page()], self.sitemap()).status)


if __name__ == "__main__":
    unittest.main()
