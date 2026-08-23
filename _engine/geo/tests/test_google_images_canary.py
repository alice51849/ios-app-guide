from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import urllib.parse
import xml.etree.ElementTree as ET


GEO = Path(__file__).resolve().parents[1]
ROOT = GEO.parent
sys.path.insert(0, str(GEO))

import audit_link_depth  # noqa: E402
import gen_link_hubs  # noqa: E402
import google_images_canary as canary  # noqa: E402
from google_images_canary_spec import SPEC  # noqa: E402


SITE = "https://example.test/guide"
TOKEN = "123456789"


class GoogleImagesCanaryTests(unittest.TestCase):
    @staticmethod
    def source_for(asset: dict[str, object]) -> Path:
        source = ROOT / Path(*Path(str(asset["source_path"])).parts[1:])
        if not source.is_file():
            deployed_pages = Path(
                os.environ.get("GEO_PAGES", GEO / "pages")
            )
            source = deployed_pages / str(asset["public_path"])
        return source

    def setUp(self) -> None:
        self.workspace = tempfile.TemporaryDirectory(dir=ROOT)
        self.root = Path(self.workspace.name)
        self.pages = self.root / "pages"
        self.reports = self.root / "reports"
        self.pages.mkdir()
        self.ledger = self.reports / canary.LEDGER_NAME
        catalog = [
            {
                "name": app["name"],
                "category": app["category"],
                "appStoreUrl": app["app_store_url"],
                "guideUrl": app["guide_url"],
            }
            for app in SPEC["apps"]
        ]
        (self.pages / "apps.json").write_text(
            json.dumps(catalog),
            encoding="utf-8",
        )
        for app in SPEC["apps"]:
            for asset in app["assets"]:
                source = self.source_for(asset)
                if not source.is_file():
                    self.fail(f"Missing authentic canary test asset: {source}")
                destination = self.pages / asset["public_path"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.link(source, destination)

    def tearDown(self) -> None:
        self.workspace.cleanup()

    def build(self) -> dict[str, int]:
        return canary.build(
            self.pages,
            SITE,
            provider_token=TOKEN,
            reports=self.reports,
        )

    def test_build_is_complete_balanced_and_idempotent(self) -> None:
        first = self.build()
        self.assertEqual(7, first["apps"])
        self.assertEqual(100, first["pages"])
        self.assertEqual(50, first["treatment"])
        self.assertEqual(50, first["holdout"])
        self.assertGreater(first["changed_files"], 100)

        second = self.build()
        self.assertEqual(0, second["changed_files"])
        ledger = json.loads(
            self.ledger.read_text(encoding="utf-8")
        )
        self.assertEqual(50, ledger["treatment_urls"])
        self.assertEqual(50, ledger["holdout_urls"])
        self.assertIsNone(
            ledger["interpretation"]["unknown_or_pending_metrics"]
        )
        self.assertEqual([], ledger["abstained_apps"])

        coverage = json.loads(
            (self.reports / canary.COVERAGE_JSON).read_text(encoding="utf-8")
        )
        self.assertEqual(7, coverage["qualified"])
        self.assertEqual(0, coverage["abstained"])
        self.assertEqual(7, coverage["categories"])
        self.assertEqual(
            sum(len(app["assets"]) for app in SPEC["apps"]),
            coverage["authentic_assets"],
        )
        self.assertEqual(38, coverage["authentic_assets"])
        self.assertEqual(100, coverage["pages"])

    def test_pages_have_real_images_schema_and_aggregated_campaigns(self) -> None:
        self.build()
        ledger = json.loads(
            self.ledger.read_text(encoding="utf-8")
        )
        campaigns: dict[str, set[str]] = {}
        for record in ledger["records"]:
            page = (
                self.pages
                / canary.ROOT_RELATIVE
                / f"{record['creative_id']}.html"
            )
            source = page.read_text(encoding="utf-8")
            self.assertIn("<img src=", source)
            self.assertIn("max-image-preview:large", source)
            self.assertIn('"@type":"ImageObject"', source)
            self.assertIn('"@type":"SoftwareApplication"', source)
            self.assertNotIn("aggregateRating", source)
            parser = canary._CanaryParser()
            parser.feed(source)
            cta = next(
                anchor
                for anchor in parser.anchors
                if anchor.get("id") == "app-store-cta"
            )
            query = urllib.parse.parse_qs(
                urllib.parse.urlsplit(cta["href"]).query
            )
            self.assertEqual({"pt", "ct", "mt"}, set(query))
            self.assertEqual(["8"], query["mt"])
            self.assertEqual(record["creative_id"], cta["data-creative-id"])
            campaigns.setdefault(record["app_key"], set()).add(query["ct"][0])
        self.assertTrue(all(len(tokens) == 1 for tokens in campaigns.values()))
        self.assertEqual(7, len(campaigns))

    def test_sitemap_only_holdouts_stay_out_of_link_hubs(self) -> None:
        self.build()
        (self.pages / "index.html").write_text(
            f'<a href="{SITE}/google-images-canary/">canary</a>',
            encoding="utf-8",
        )
        old_site = gen_link_hubs.SITE
        old_audit_pages = audit_link_depth.PAGES
        old_audit_reports = audit_link_depth.REPORTS
        old_audit_site = audit_link_depth.SITE
        old_root_url = audit_link_depth.ROOT_URL
        try:
            gen_link_hubs.SITE = SITE
            gen_link_hubs.run_link_hubs(self.pages)
            audit_link_depth.PAGES = str(self.pages)
            audit_link_depth.REPORTS = str(self.reports)
            audit_link_depth.SITE = SITE
            audit_link_depth.ROOT_URL = f"{SITE}/index.html"
            summary = audit_link_depth.summarize(audit_link_depth.crawl())
        finally:
            gen_link_hubs.SITE = old_site
            audit_link_depth.PAGES = old_audit_pages
            audit_link_depth.REPORTS = old_audit_reports
            audit_link_depth.SITE = old_audit_site
            audit_link_depth.ROOT_URL = old_root_url
        self.assertEqual(50, summary["sitemap_only_experiment_holdouts"])
        self.assertEqual(
            50, summary["sitemap_only_experiment_holdouts_unreachable"]
        )
        self.assertEqual([], summary["experiment_contract_errors"])
        self.assertEqual(0, summary["indexable_orphans"])

    def test_image_sitemap_has_every_page_and_treatment_sitemap_only_half(
        self,
    ) -> None:
        self.build()
        image_urls = canary._xml_page_urls(
            self.pages / canary.IMAGE_SITEMAP_RELATIVE
        )
        treatment_urls = canary._xml_page_urls(
            self.pages / canary.TREATMENT_SITEMAP_RELATIVE
        )
        self.assertEqual(100, len(image_urls))
        self.assertEqual(50, len(treatment_urls))
        tree = ET.parse(self.pages / canary.IMAGE_SITEMAP_RELATIVE)
        image_nodes = tree.findall(
            f".//{{{canary.gen_image_sitemap.IMAGE_NS}}}loc"
        )
        self.assertEqual(100, len(image_nodes))
        ledger = json.loads(
            self.ledger.read_text(encoding="utf-8")
        )
        holdout = next(
            row["page_url"]
            for row in ledger["records"]
            if row["arm"] == "holdout"
        )
        (self.pages / "sitemap_accidental.xml").write_text(
            canary._render_url_sitemap([holdout]),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "non-image sitemap"):
            canary.audit_generated(
                self.pages,
                SITE,
                ledger_path=self.ledger,
            )

    def test_tampered_asset_and_catalog_fail_closed(self) -> None:
        self.build()
        asset = SPEC["apps"][0]["assets"][0]
        target = self.pages / asset["public_path"]
        target.unlink()
        target.write_bytes(b"not a png")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            canary.audit_generated(
                self.pages,
                SITE,
                ledger_path=self.ledger,
            )

        os.unlink(self.pages / asset["public_path"])
        source = self.source_for(asset)
        os.link(source, self.pages / asset["public_path"])
        catalog = json.loads((self.pages / "apps.json").read_text())
        catalog[0]["name"] = "Wrong app"
        (self.pages / "apps.json").write_text(json.dumps(catalog))
        with self.assertRaisesRegex(ValueError, "catalog mismatch"):
            canary.audit_generated(
                self.pages,
                SITE,
                ledger_path=self.ledger,
            )

    def test_spec_rejects_duplicate_task_value_and_incomplete_asset(self) -> None:
        invalid = copy.deepcopy(SPEC)
        invalid["pairs"][0]["variants"][1]["problem"] = (
            invalid["pairs"][0]["variants"][0]["problem"]
        )
        invalid["pairs"][0]["variants"][1]["steps"] = list(
            invalid["pairs"][0]["variants"][0]["steps"]
        )
        invalid["pairs"][0]["variants"][1]["result"] = (
            invalid["pairs"][0]["variants"][0]["result"]
        )
        with self.assertRaisesRegex(ValueError, "Duplicate task value"):
            canary.validate_spec(invalid)

        invalid = copy.deepcopy(SPEC)
        invalid["apps"][0]["assets"][0]["width"] = 1199
        with self.assertRaisesRegex(ValueError, "below 1200px"):
            canary.validate_spec(invalid)

    def test_build_honors_cancellation_before_writing(self) -> None:
        previous = canary._CANCELLED
        canary._CANCELLED = True
        try:
            with self.assertRaises(InterruptedError):
                self.build()
        finally:
            canary._CANCELLED = previous
        self.assertFalse(self.ledger.exists())

    def test_publish_workflow_and_attribution_preserve_the_canary(self) -> None:
        publish = (GEO / "publish.py").read_text(encoding="utf-8")
        self.assertIn("google_images_canary.py", publish)
        self.assertLess(
            publish.index("google_images_canary.py"),
            publish.index("gen_link_hubs.py"),
        )
        attribution = (GEO / "gen_store_attribution.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('"google-images-canary"', attribution)
        workflow = (
            GEO / "pages" / ".github" / "workflows" / "geo-daily.yml"
        ).read_text(encoding="utf-8")
        self.assertEqual(3, workflow.count("python3 google_images_canary.py"))
        self.assertEqual(
            3,
            workflow.count("python3 gen_store_attribution.py"),
        )
        for block in workflow.split("python3 google_images_canary.py")[1:]:
            self.assertLess(
                block.index("python3 gen_store_attribution.py"),
                block.find("\n      - name:")
                if "\n      - name:" in block
                else len(block),
            )


if __name__ == "__main__":
    unittest.main()
