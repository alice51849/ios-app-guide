#!/usr/bin/env python3
"""Tests for the fixed exact-50 alternatives producer."""

from __future__ import annotations

import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from urllib.parse import parse_qsl, urlsplit


GEO = Path(__file__).resolve().parents[1]
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import alternatives_i18n as alternatives  # noqa: E402
from official_locales import OFFICIAL_LOCALES  # noqa: E402
from market_contract_assertions import assert_blocked_page


FIXTURE = GEO / "tests" / "fixtures" / "alternatives_exact50"


class AlternativesExact50Tests(unittest.TestCase):
    def setUp(self) -> None:
        scratch = tempfile.TemporaryDirectory(
            prefix=".alternatives-exact50-test-",
            dir=GEO / "tests",
        )
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.pages = self.root / "pages"
        self.pages.mkdir()
        self.catalog = FIXTURE / "catalog.json"
        self.inventory = FIXTURE / "inventory.json"
        self.manifest = FIXTURE / "manifest.json"
        self._write_source_pages()

    def _write_source_pages(self) -> None:
        catalog = json.loads(self.catalog.read_text(encoding="utf-8"))
        labels = json.loads(
            (FIXTURE / "native_labels.json").read_text(encoding="utf-8")
        )["labels"]
        self.assertEqual(set(OFFICIAL_LOCALES), set(labels))
        for record in catalog["records"]:
            relative = record["canonical_guide_url"].split(
                alternatives.PUBLIC_SITE.rstrip("/") + "/", 1
            )[1]
            path = self.pages / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                (
                    "<!doctype html><html><body>"
                    f'<a href="{alternatives.PUBLIC_SITE}/alternatives/">'
                    f"{html.escape(labels[record['locale']])}</a>"
                    "</body></html>\n"
                ),
                encoding="utf-8",
            )
        legacy = self.pages / "alternatives" / "scanto-vs-adobe-scan.html"
        legacy.parent.mkdir(parents=True, exist_ok=True)
        legacy.write_text(
            (
                "<!doctype html><head>"
                f'<link rel="canonical" href="{alternatives.PUBLIC_SITE}/'
                'alternatives/scanto-vs-adobe-scan.html">'
                "</head><body>Adobe Scan · ScanTo Pro · "
                '<a href="https://apps.apple.com/app/id6779977651">'
                "App Store</a></body></html>\n"
            ),
            encoding="utf-8",
        )

    def _build(
        self,
        *,
        catalog: Path | None = None,
        inventory: Path | None = None,
        check: bool = False,
    ) -> dict[str, int]:
        return alternatives.build(
            pages=self.pages,
            manifest_path=self.manifest,
            catalog_path=catalog or self.catalog,
            inventory_path=inventory or self.inventory,
            ui_i18n_path=alternatives.DEFAULT_UI_I18N,
            site=alternatives.PUBLIC_SITE,
            check=check,
        )

    def _mutated_json(
        self,
        source: Path,
        name: str,
        mutate,
    ) -> Path:
        payload = json.loads(source.read_text(encoding="utf-8"))
        mutate(payload)
        path = self.root / name
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    @staticmethod
    def _production_guide() -> Path:
        """解析出要驗的 Guide checkout;**絕不**默默退回一棵沒人綁定的工作樹。

        原本最後會退回 `~/00_GrowthEngine/geo/pages`。那是多個 session 共用的巢狀
        checkout,實測可以落後遠端數百個 commit(2026-09-12 當下落後 291 個),
        於是這裡會拿**過期內容**去驗「production」:canonical 還停在遷移前的
        github.io、geo-daily.yml 還沒有 producer 區塊,測試失敗指向的卻是早就修好的
        東西。沉默地驗錯一棵樹,比不驗還糟。

        現在:repo 內找得到就用;否則必須由 `ALTERNATIVES_GUIDE_REPOSITORY` 明確
        綁定;都沒有就回 None,由呼叫端 skip 並講清楚原因。
        """
        repository_or_worktrees = Path(__file__).resolve().parents[3]
        for candidate in (
            repository_or_worktrees,
            repository_or_worktrees / "guide-alternatives-a",
        ):
            if (candidate / "data" / "verified-ios-app-finder-catalog.json").is_file():
                return candidate
        override = os.environ.get("ALTERNATIVES_GUIDE_REPOSITORY", "").strip()
        if override:
            return Path(override).expanduser()
        return None

    def _require_production_guide(self) -> Path:
        """取得 Guide checkout,並確認它不是過期的樹。"""
        guide = self._production_guide()
        if guide is None:
            self.skipTest(
                "沒有綁定 Guide checkout:請設 ALTERNATIVES_GUIDE_REPOSITORY 指向"
                "目前的 ios-app-guide 工作樹。刻意不再默默退回共用的 geo/pages,"
                "那棵樹可能落後遠端數百個 commit,會驗出假的失敗。"
            )
        stale = self._guide_commits_behind(guide)
        if stale:
            reference = os.environ.get("ALTERNATIVES_GUIDE_BASE_REF", "origin/main")
            self.fail(
                f"Guide checkout 落後其 {reference} {stale} 個 commit({guide});"
                "用過期內容驗 production 只會產生假結果。請先更新該 checkout,"
                "或用 ALTERNATIVES_GUIDE_REPOSITORY 指向最新的工作樹。"
            )
        return guide

    @staticmethod
    def _guide_commits_behind(guide: Path) -> int:
        """Default to main; an explicitly requested paired stack can pin a full SHA."""
        pinned = os.environ.get("ALTERNATIVES_GUIDE_BASE_REF", "").strip()
        if pinned and re.fullmatch(r"[0-9a-f]{40}", pinned) is None:
            raise AssertionError("Pinned Guide base must be an exact full commit SHA")
        reference = pinned or "origin/main"
        try:
            result = subprocess.run(
                ["git", "-C", str(guide), "rev-list", "--count", f"HEAD..{reference}"],
                capture_output=True, text=True, timeout=60, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            if pinned:
                raise AssertionError("Cannot verify pinned Guide ancestry")
            return 0
        if result.returncode != 0:
            if pinned:
                raise AssertionError("Unknown pinned Guide commit")
            return 0
        try:
            return int(result.stdout.strip() or "0")
        except ValueError:
            if pinned:
                raise AssertionError("Invalid pinned Guide ancestry result")
            return 0

    def test_explicit_stack_binding_rejects_mutable_or_unknown_base(self):
        guide = self._require_production_guide()
        for reference in ("main", "origin/main", "337ce28e7f8", "0" * 40):
            with self.subTest(reference=reference):
                with mock.patch.dict(os.environ, {"ALTERNATIVES_GUIDE_BASE_REF": reference}):
                    with self.assertRaises(AssertionError):
                        self._guide_commits_behind(guide)

    def test_production_manifest_is_fixed_by_ranked_and_curated_evidence(self) -> None:
        manifest = alternatives.load_manifest(alternatives.DEFAULT_MANIFEST)
        self.assertEqual(41, manifest["selection"]["route_count"])
        self.assertEqual(50, manifest["selection"]["locale_count"])
        self.assertEqual(2050, manifest["selection"]["expected_page_count"])
        self.assertEqual(
            2,
            sum(
                route["evidence_kind"] == "curated_fallback"
                for route in manifest["routes"]
            ),
        )
        self.assertEqual(
            len(manifest["routes"]),
            len({route["route_id"] for route in manifest["routes"]}),
        )
        self.assertEqual(
            len(manifest["routes"]),
            len({route["slug"] for route in manifest["routes"]}),
        )

    def test_generation_is_exact50_native_owned_and_attributed(self) -> None:
        stats = self._build()
        self.assertEqual(
            {
                "routes": 1,
                "locales": 50,
                "pages": 50,
                "changed": 52,
                "pruned": 0,
            },
            stats,
        )
        catalog = json.loads(self.catalog.read_text(encoding="utf-8"))
        records = {record["locale"]: record for record in catalog["records"]}
        expected_hreflang = {*OFFICIAL_LOCALES, "x-default"}
        for locale in OFFICIAL_LOCALES:
            path = (
                self.pages
                / locale
                / "alternatives"
                / "scanto-vs-adobe-scan.html"
            )
            document = path.read_text(encoding="utf-8")
            record = records[locale]
            self.assertIn(f'<html lang="{locale}"', document)
            self.assertIn(alternatives.OWNER_MARKER, document)
            self.assertIn(
                f'<link rel="canonical" href="{alternatives.PUBLIC_SITE}/'
                f'{locale}/alternatives/scanto-vs-adobe-scan.html">',
                document,
            )
            hreflang = set(
                re.findall(r'rel="alternate" hreflang="([^"]+)"', document)
            )
            self.assertEqual(expected_hreflang, hreflang)
            self.assertIn(html.escape(record["publisher_query"]), document)
            self.assertIn(html.escape(record["decision_context"]), document)
            if locale == "bn-BD":
                assert_blocked_page(self, document)
                continue
            self.assertIn(html.escape(record["app_store_cta_label"]), document)
            store_links = re.findall(
                r'href="(https://apps\.apple\.com/[^"]+)"', document
            )
            self.assertEqual(1, len(store_links))
            pairs = parse_qsl(
                urlsplit(html.unescape(store_links[0])).query,
                keep_blank_values=True,
            )
            self.assertEqual(["pt", "ct", "mt"], [key for key, _ in pairs])
            self.assertEqual("8", pairs[-1][1])

        english = records["en-US"]
        for locale in set(OFFICIAL_LOCALES) - alternatives.ENGLISH_LOCALES:
            document = (
                self.pages
                / locale
                / "alternatives"
                / "scanto-vs-adobe-scan.html"
            ).read_text(encoding="utf-8")
            self.assertNotIn(
                html.escape(english["publisher_query"]),
                document,
            )
            self.assertNotIn(
                html.escape(english["decision_context"]),
                document,
            )

    def test_production_render_has_exact_urls_attribution_and_no_fallback(self) -> None:
        guide = self._require_production_guide()
        catalog = guide / alternatives.DEFAULT_CATALOG_RELATIVE
        inventory = guide / alternatives.DEFAULT_INVENTORY_RELATIVE
        if not catalog.is_file() or not inventory.is_file():
            self.skipTest("Production Guide catalog is not available")
        rendered, sitemap, _state, stats = alternatives.prepare_generation(
            pages=guide,
            manifest_path=alternatives.DEFAULT_MANIFEST,
            catalog_path=catalog,
            inventory_path=inventory,
            ui_i18n_path=alternatives.DEFAULT_UI_I18N,
            site=alternatives.PUBLIC_SITE,
        )
        self.assertEqual(41, stats["routes"])
        self.assertEqual(50, stats["locales"])
        self.assertEqual(2050, stats["pages"])
        self.assertEqual(2050, len(rendered))
        actual_urls = set(re.findall(r"<loc>([^<]+)</loc>", sitemap))
        expected_urls = {
            f"{alternatives.PUBLIC_SITE}/{locale}/alternatives/"
            f"{route['slug']}.html"
            for route in alternatives.load_manifest()["routes"]
            for locale in OFFICIAL_LOCALES
        }
        self.assertEqual(expected_urls, actual_urls)
        blocked = 0
        available = 0
        for relative, document in rendered.items():
            if relative.parts[0] == "bn-BD":
                assert_blocked_page(self, document)
                blocked += 1
                continue
            available += 1
            store_links = re.findall(
                r'href="(https://apps\.apple\.com/[^"]+)"', document
            )
            self.assertEqual(1, len(store_links), relative.as_posix())
            pairs = parse_qsl(
                urlsplit(html.unescape(store_links[0])).query,
                keep_blank_values=True,
            )
            self.assertEqual(
                ["pt", "ct", "mt"],
                [key for key, _ in pairs],
                relative.as_posix(),
            )
            self.assertEqual("8", pairs[-1][1], relative.as_posix())
        self.assertEqual(blocked, 41)
        self.assertEqual(available, 41 * 49)

    def test_geo_daily_wires_producer_before_sitemap_closure(self) -> None:
        workflow = (
            self._require_production_guide()
            / ".github"
            / "workflows"
            / "geo-daily.yml"
        )
        if not workflow.is_file():
            self.skipTest("Production geo-daily workflow is not available")
        document = workflow.read_text(encoding="utf-8")
        blocks = re.findall(
            r"python3 alternatives_i18n\.py --pages-dir "
            r"\"\$GITHUB_WORKSPACE\""
            r"[\s\S]{0,700}?"
            r"python3 close_sitemap_graph\.py",
            document,
        )
        self.assertEqual(2, len(blocks))

    def test_missing_locale_and_english_fallback_fail_closed(self) -> None:
        missing = self._mutated_json(
            self.catalog,
            "missing-locale.json",
            lambda payload: payload["records"].pop(),
        )
        with self.assertRaisesRegex(ValueError, "not exact route-app"):
            self._build(catalog=missing)
        self.assertFalse((self.pages / alternatives.STATE_RELATIVE).exists())

        def inject_fallback(payload: dict) -> None:
            records = {
                record["locale"]: record
                for record in payload["records"]
            }
            records["bn-BD"]["publisher_query"] = records["en-US"][
                "publisher_query"
            ]

        fallback = self._mutated_json(
            self.catalog,
            "english-fallback.json",
            inject_fallback,
        )
        with self.assertRaisesRegex(ValueError, "English fallback"):
            self._build(catalog=fallback)
        self.assertFalse((self.pages / alternatives.STATE_RELATIVE).exists())

    def test_route_ownership_and_truth_contracts_fail_closed(self) -> None:
        legacy = self.pages / "alternatives" / "scanto-vs-adobe-scan.html"
        legacy.write_text(
            legacy.read_text(encoding="utf-8").replace(
                "id6779977651", "id1111111111"
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "ownership differs"):
            self._build()

        self._write_source_pages()

        def wrong_purchase(payload: dict) -> None:
            payload["apps"][0]["purchase_model"] = "paid_upfront"

        inventory = self._mutated_json(
            self.inventory,
            "wrong-purchase.json",
            wrong_purchase,
        )
        with self.assertRaisesRegex(ValueError, "Untruthful publisher intent"):
            self._build(inventory=inventory)

        def wrong_owner(payload: dict) -> None:
            payload["apps"][0]["app_store_id"] = "1111111111"

        owner = self._mutated_json(
            self.inventory,
            "wrong-owner.json",
            wrong_owner,
        )
        with self.assertRaisesRegex(ValueError, "Verified inventory owner"):
            self._build(inventory=owner)

    def test_sitemap_exact_set_second_run_zero_diff_and_stale_prune(self) -> None:
        self._build()
        first = {
            path.relative_to(self.pages).as_posix(): path.read_bytes()
            for path in sorted(self.pages.rglob("*"))
            if path.is_file()
        }
        second = self._build()
        self.assertEqual(0, second["changed"])
        self.assertEqual(0, second["pruned"])
        self.assertEqual(
            first,
            {
                path.relative_to(self.pages).as_posix(): path.read_bytes()
                for path in sorted(self.pages.rglob("*"))
                if path.is_file()
            },
        )

        sitemap = (self.pages / alternatives.SITEMAP_RELATIVE).read_text(
            encoding="utf-8"
        )
        actual = set(re.findall(r"<loc>([^<]+)</loc>", sitemap))
        expected = {
            f"{alternatives.PUBLIC_SITE}/{locale}/alternatives/"
            "scanto-vs-adobe-scan.html"
            for locale in OFFICIAL_LOCALES
        }
        self.assertEqual(expected, actual)

        stale_relative = (
            Path("fr-FR") / "alternatives" / "removed-route.html"
        )
        stale = self.pages / stale_relative
        stale.write_text(
            f"<main {alternatives.OWNER_MARKER}>stale</main>\n",
            encoding="utf-8",
        )
        state_path = self.pages / alternatives.STATE_RELATIVE
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["pages"].append(stale_relative.as_posix())
        state["pages"].sort()
        state["page_count"] += 1
        state_path.write_text(
            json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2)
            + "\n",
            encoding="utf-8",
        )
        result = self._build()
        self.assertEqual(1, result["pruned"])
        self.assertFalse(stale.exists())
        self.assertEqual(0, self._build(check=True)["changed"])
        self.assertEqual(
            [],
            [
                path
                for path in self.pages.rglob("*.tmp")
                if path.is_file()
            ],
        )

    def test_pricing_and_privacy_are_source_bound_without_fake_prices(self) -> None:
        self._build()
        inventory = json.loads(self.inventory.read_text(encoding="utf-8"))[
            "apps"
        ][0]
        record = next(
            record
            for record in json.loads(
                self.catalog.read_text(encoding="utf-8")
            )["records"]
            if record["locale"] == "zh-Hant"
        )
        document = (
            self.pages
            / "zh-Hant"
            / "alternatives"
            / "scanto-vs-adobe-scan.html"
        ).read_text(encoding="utf-8")
        self.assertIn(
            f'data-purchase-model="{inventory["purchase_model"]}"',
            document,
        )
        self.assertIn(
            f'data-one-time-option="{str(inventory["one_time_option"]).lower()}"',
            document,
        )
        capabilities_text = re.search(
            r"<script type=\"application/json\" "
            r"data-lumi-verified-capabilities>(.*?)</script>",
            document,
        )
        self.assertIsNotNone(capabilities_text)
        self.assertEqual(
            {
                key: bool(value)
                for key, value in sorted(inventory["capabilities"].items())
            },
            json.loads(capabilities_text.group(1)),
        )
        self.assertIn(html.escape(record["decision_context"]), document)
        self.assertNotRegex(document, r"[$€£¥₹]\s*\d|\d+[.,]\d{2}\s*[$€£¥₹]")


if __name__ == "__main__":
    unittest.main()
