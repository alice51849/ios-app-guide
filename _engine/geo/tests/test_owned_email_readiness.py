import copy
from datetime import timedelta
import html
import io
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest import mock
import uuid

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))
sys.path.insert(0, str(GEO / "tests"))

import gen_owned_email_capture as capture
import gen_tool_email_capture as legacy
import owned_email_contract as c
import owned_email_readiness as ready
from test_owned_email import NOW, PROVIDER, availability, sources


class ReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clock = mock.patch.object(c, "utcnow", return_value=NOW)
        cls.clock.start()
        cls.git = mock.patch.object(c, "committed_source_files", return_value=c.source_files())
        cls.git.start()
        cls.availability = availability()
        cls.inventory, cls.outputs = capture.build(PROVIDER, sources(), cls.availability, now=NOW)
        cls.row = c.inventory_row(cls.inventory, "aibriefpack", "zh-Hant")
        cls.bn = c.inventory_row(cls.inventory, "aibriefpack", "bn-BD")
        cls.pages = GEO / "tests" / (".owned-email-readiness-" + uuid.uuid4().hex)
        capture.write(cls.pages, cls.inventory, cls.availability, cls.outputs)
        cls.report = cls.geometry_report()
        cls.dependencies = cls.layout_report()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.pages)
        cls.git.stop()
        cls.clock.stop()

    @classmethod
    def geometry_report(cls):
        inactive, active, rows, longest = {}, {}, [], {}
        copies = c.load_copy()
        for row in cls.inventory["rows"]:
            path = row["capture_path"]
            inactive[path] = row["content_sha256"]
            active[path] = c.digest(capture.render_capture(row, copies, active=True))
            if row["locale"] not in longest or len(row["app_name"]) > len(longest[row["locale"]]["app_name"]):
                longest[row["locale"]] = row
            for width, height in ready.VIEWPORTS:
                primary = None if row["locale"] == "bn-BD" else {
                    "x": 20, "y": 40, "width": 180, "height": 48, "bottom": 88,
                }
                rows.append({
                    "app_id": row["app_id"], "app_key": row["app_key"], "locale": row["locale"],
                    "width": width, "height": height, "errors": [], "no_js": True,
                    "native_form": True, "rollback": True, "targets_ok": True, "cls": 0,
                    "overflow": 0, "primary": primary, "active_primary": primary,
                    "rollback_primary": primary, "inactive_sha256": inactive[path], "active_sha256": active[path],
                })
        audits = [
            {"key": f"{row['app_id']}/{locale}/{width}/{mode}", "violations": [], "incomplete": []}
            for locale, row in longest.items() for width, _ in ready.VIEWPORTS
            for mode in ("inactive", "active")
        ]
        return {
            "schema": "lumi.owned-email-geometry/v1", "observed_at": NOW.isoformat(),
            "source_digest": c.digest(c.source_files()), "viewports": [list(v) for v in ready.VIEWPORTS],
            "locales": list(c.OFFICIAL_LOCALES), "app_count": 47, "cases": 11750,
            "no_js_cases": 11750, "active_preview_cases": 11750, "rollback_cases": 11750,
            "cls_cases": 23500, "a11y_cases": 500, "a11y": audits, "rows": rows,
            "failures": [], "network_requests": [], "page_scripts": 0, "max_cls": 0,
            "max_overflow": 0, "inactive_hashes": inactive, "active_hashes": active,
            "playwright_version": "1.63.0", "axe_version": "4.13.0",
            "browser": "chromium", "browser_version": "unit-test-fixture",
        }

    @classmethod
    def layout_report(cls):
        root, prefix = c.git_context(str(GEO))
        owner = "growth" if prefix == "geo" else "guide"
        revision = subprocess.check_output(["git", "-C", str(root), "rev-parse", "origin/main"], text=True).strip()
        revisions = {"growth": "a" * 40, "guide": "b" * 40, owner: revision}
        files = {}
        for side, base in (("growth", "geo"), ("guide", "_engine/geo")):
            for name in ("publish.py", "hero_task_html.py", "deployment_generation.py"):
                value = "a" * 64
                if side == owner:
                    value = c.digest(subprocess.check_output(["git", "-C", str(root), "show", f"{revision}:{base}/{name}"]))
                files[f"{side}/{base}/{name}"] = value
        return {
            "schema": "lumi.owned-email-layout-dependencies/v1", "observed_at": NOW.isoformat(),
            "main_revisions": revisions, "source_digest": c.digest(c.source_files()),
            "shared_feature_merged": False, "dependency_files": files,
            "compatibility_cases": 250, "non_capture_preserved": True, "non_interference_failures": 0,
            "active_preview_non_interference_failures": 0, "baseline_primary_offscreen": 51,
            "rows": [{"locale": locale, "width": width, "height": height, "inactive_preserved": True}
                     for locale in c.OFFICIAL_LOCALES for width, height in ready.VIEWPORTS],
        }

    def health(self):
        class Response(io.BytesIO):
            def __init__(self, url):
                super().__init__(b"public content only")
                self.code, self.headers, self.url = 200, {}, url

            def geturl(self):
                return self.url

        calls = []

        def get(request, **_kwargs):
            self.assertEqual(request.get_method(), "GET")
            self.assertIsNone(request.data)
            calls.append(request.full_url)
            return Response(request.full_url)

        result = ready.endpoint_health(open_url=get, now=NOW)
        self.assertEqual(calls, [c.ENDPOINT, "https://buttondown.com/hourstag/archive/"])
        return result

    def manifest(self, *, report=None, health=None, dependencies=None):
        return ready.release_manifest(
            self.inventory, self.pages, report or self.report, health or self.health(),
            dependencies=dependencies or self.dependencies,
        )

    def test_all_2350_default_inactive_without_dead_controls(self):
        result = ready.inspect_inventory(self.inventory, self.pages)
        self.assertEqual(result["capture_count"], 2350)
        self.assertEqual(result["active_capture_count"], 0)
        self.assertEqual(self.inventory["rollout"]["stage"], "inactive")
        for row in self.inventory["rows"]:
            body = self.outputs[row["capture_path"]]
            self.assertNotIn(b"<form", body)
            self.assertNotIn(b"<input", body)
            self.assertNotIn(b"<button", body)

    def test_fair_predeclared_cohorts_never_choose_apps_by_results(self):
        policy = ready.load_policy()
        for stage, expected in (("inactive", 0), ("pilot", 1), ("expanded", 4), ("all", 50)):
            with mock.patch.object(ready, "load_policy", return_value={**policy, "stage": stage}):
                result = ready.rollout()
                self.assertEqual(result["active_capture_count"], 47 * expected)
                self.assertEqual(set(result["per_app_active_count"].values()), {expected})
                self.assertEqual(len(result["per_app_active_count"]), 47)

    def test_rollout_rejects_result_based_selection_and_active_default(self):
        policy = ready.load_policy()
        for changes in ({"app_selection": "top_converters"}, {"default_active": True}, {"selected_apps": ["aibriefpack"]}):
            with mock.patch.object(Path, "read_bytes", return_value=c.json_bytes({**policy, **changes})):
                with self.assertRaises(c.ContractError):
                    ready.load_policy()

    def test_optional_copy_exact50_and_no_language_fallback(self):
        for locale in c.OFFICIAL_LOCALES:
            self.assertTrue(ready.localized(locale)["optional"])
            self.assertTrue(ready.localized(locale)["inactive"])
        with self.assertRaises(KeyError):
            ready.localized("xx")

    def test_active_preview_after_core_and_rollback_preserves_core_exactly(self):
        for row in self.inventory["rows"]:
            inactive = self.outputs[row["capture_path"]]
            active = capture.render_capture(row, active=True)
            ready.inspect_html(row, active, active=True)
            self.assertEqual(ready.core_digest(active.decode()), ready.core_digest(inactive.decode()))
            self.assertEqual(capture.render_capture(row, active=False), inactive)

    def test_bn_information_capture_has_no_store_cta_in_either_mode(self):
        for active in (False, True):
            body = capture.render_capture(self.bn, active=active)
            ready.inspect_html(self.bn, body, active=active)
            self.assertNotIn(b"apps.apple.com", body)
            self.assertNotIn(b"data-primary-app-store-cta", body)
            self.assertIn(b"market-availability", body)
        self.assertEqual(self.bn["conversion_campaign"], "N/A")

    def test_prechecked_autofocus_modal_tracking_and_js_are_blocked(self):
        original = capture.render_capture(self.row, active=True).decode()
        mutations = (
            original.replace('type="checkbox"', 'type="checkbox" checked'),
            original.replace('type="email"', 'type="email" autofocus'),
            original.replace("<details>", "<details open>"),
            original.replace("<details>", '<details role="dialog">'),
            original.replace("<details>", '<details style="position:fixed">'),
            original.replace("</main>", '<img src="https://tracker.invalid/pixel"></main>'),
            original.replace("</main>", "<script>localStorage.x=1</script></main>"),
            original.replace("<details>", '<details onclick="capture()">'),
        )
        for changed in mutations:
            with self.subTest(mutation=changed[-100:]), self.assertRaises(c.ContractError):
                ready.inspect_html(self.row, changed, active=True)

    def test_early_form_and_changed_store_cta_are_blocked(self):
        original = capture.render_capture(self.row, active=True).decode()
        start, end = original.index('<header class="oe-core"'), original.index("</header>") + len("</header>")
        changed = original[:start] + original[end:]
        changed = changed.replace("</main>", original[start:end] + "</main>")
        with self.assertRaises(c.ContractError):
            ready.inspect_html(self.row, changed, active=True)
        changed = original.replace(html.escape(self.row["app_store_url"], quote=True), "https://apps.apple.com/us/app/id1")
        with self.assertRaises(c.ContractError):
            ready.inspect_html(self.row, changed, active=True)

    def test_legacy_inactive_is_byte_identical_and_preview_preserves_answer(self):
        original = '<html lang="zh-Hant"><body><main><h1>Answer</h1><a href="https://apps.apple.com/tw/app/id1234567890">Store</a></main></body></html>'
        self.assertEqual(legacy.apply_capture(original, legacy._load_config()), original)
        preview = legacy.apply_capture(original, legacy._load_config(), preview=True)
        ready.legacy_non_interference(original, preview)
        self.assertEqual(legacy.apply_capture(preview, legacy._load_config()), original)
        with self.assertRaises(c.ContractError):
            ready.legacy_non_interference(original, preview.replace("Answer", "Removed"))

    def test_legacy_preview_goes_after_store_cta_outside_main(self):
        source = '<html lang="en-US"><body><main>Answer</main><a href="https://apps.apple.com/us/app/id1234567890">Store</a></body></html>'
        result = legacy.apply_capture(source, legacy._load_config(), preview=True)
        self.assertGreater(result.index("tool-email-capture"), result.index(">Store</a>"))
        with self.assertRaises(ValueError):
            legacy.apply_capture('<html lang="en-US">Answer', legacy._load_config(), preview=True)

    def test_endpoint_get_health_never_claims_subscriber_or_native(self):
        health = self.health()
        self.assertEqual(health["subscriber_total"], "UNKNOWN")
        self.assertEqual(health["verified_subscribers"], 0)
        self.assertEqual(health["native_count"], 0)
        self.assertEqual(health["post_requests"], 0)

    def test_full_evidence_yields_inactive_ready_not_activation_authorization(self):
        manifest = self.manifest()
        self.assertTrue(manifest["inactive_release_ready"])
        self.assertFalse(manifest["activation_ready"])
        self.assertEqual(manifest["rollout"]["active_capture_count"], 0)
        self.assertTrue(manifest["rollback"]["geometry_roundtrip_verified"])
        self.assertFalse(manifest["rollback"]["deletes_consent_records"])
        self.assertTrue(any("shared_layout" in value for value in manifest["integration_blockers"]))

    def test_geometry_rejects_forged_counts_missing_cases_and_duplicate_identity(self):
        for change in ("count", "missing", "duplicate", "source"):
            report = copy.deepcopy(self.report)
            if change == "count":
                report["no_js_cases"] = 0
            elif change == "missing":
                report["rows"].pop()
            elif change == "duplicate":
                report["rows"][1] = report["rows"][0]
            else:
                report["source_digest"] = "0" * 64
            with self.assertRaises(c.ContractError):
                ready.validate_geometry(report, self.inventory)

    def test_geometry_rejects_offscreen_overflow_cls_targets_and_a11y_unknown(self):
        for change in ("primary", "overflow", "cls", "target", "a11y", "request"):
            report = copy.deepcopy(self.report)
            row = next(value for value in report["rows"] if value["locale"] != "bn-BD")
            if change == "primary":
                row["primary"] = {**row["primary"], "bottom": 9999}
            elif change == "overflow":
                row["overflow"] = 10
            elif change == "cls":
                row["cls"] = 0.01
            elif change == "target":
                row["targets_ok"] = False
            elif change == "a11y":
                report["a11y"][0]["incomplete"] = [{"id": "color-contrast"}]
            else:
                report["network_requests"] = [{"method": "GET", "url": "https://tracking.invalid"}]
            with self.assertRaises(c.ContractError):
                ready.validate_geometry(report, self.inventory)

    def test_geometry_stale_or_wrong_output_hash_is_blocked(self):
        for change in ("stale", "hash"):
            report = copy.deepcopy(self.report)
            if change == "stale":
                report["observed_at"] = (NOW - timedelta(days=2)).isoformat()
            else:
                report["inactive_hashes"][self.row["capture_path"]] = "0" * 64
            with self.assertRaises(c.ContractError):
                ready.validate_geometry(report, self.inventory)

    def test_health_stale_post_or_fake_subscriber_count_is_blocked(self):
        for change in ("post", "stale", "subscriber"):
            health = self.health()
            if change == "post":
                health["results"][0]["method"] = "POST"
            elif change == "stale":
                health["results"][0]["observed_at"] = (NOW - timedelta(minutes=6)).isoformat()
            else:
                health["verified_subscribers"] = 1
            with self.assertRaises(c.ContractError):
                self.manifest(health=health)

    def test_shared_layout_missing_cases_changed_source_and_rebase_are_blocked(self):
        for change in ("rows", "digest", "main"):
            dependency = copy.deepcopy(self.dependencies)
            if change == "rows":
                dependency["rows"].pop()
            else:
                _, prefix = c.git_context(str(GEO))
                owner = "growth" if prefix == "geo" else "guide"
                if change == "digest":
                    dependency["dependency_files"][f"{owner}/{prefix}/publish.py"] = "0" * 64
                else:
                    dependency["main_revisions"][owner] = "0" * 40
            with self.assertRaises(c.ContractError):
                self.manifest(dependencies=dependency)

    def test_shared_layout_work_in_progress_is_not_silently_adopted(self):
        dependency = copy.deepcopy(self.dependencies)
        dependency["shared_feature_merged"] = True
        with self.assertRaises(c.ContractError):
            self.manifest(dependencies=dependency)


if __name__ == "__main__":
    unittest.main()
