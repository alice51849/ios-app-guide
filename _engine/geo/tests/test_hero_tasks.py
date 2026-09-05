from __future__ import annotations

import copy
import csv
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unittest
import uuid
import xml.etree.ElementTree as ET

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import hero_tasks as hero  # noqa: E402
import hero_tasks_readback as readback  # noqa: E402


class HeroTaskTests(unittest.TestCase):
    def setUp(self):
        self.folder = GEO / ".hero-validation" / f"fixture-{uuid.uuid4().hex}"
        self.folder.mkdir(parents=True)
        self.pages = self.folder / "site"
        self.pages.mkdir()
        self.tasks = hero.load_registry()
        self.copy = hero.load_i18n()
        self.site = hero.DEFAULT_SITE
        apps = [
            {"key": key, "app_store_id": app_id, "name": key, "verified_live": True,
             "purchase_model": "paid_upfront" if key == "hourstag" else "free_with_lifetime_unlock"}
            for key, app_id in self.tasks[0]["apps"].items()
        ]
        apps.append({"key": "unserved", "app_store_id": "99999999", "verified_live": True})
        self.write(hero.FINDER, {"record_count": len(apps), "apps": apps})
        self.write(".appstore_live_state.json", {"live_ids": [app["app_store_id"] for app in apps]})
        records = []
        for locale in hero.OFFICIAL_LOCALES:
            for app in apps[:2]:
                key = app["key"]
                relative = (
                    f"{locale}/{key}.html" if locale == "bn-BD"
                    else f"{locale}/answers/{key}-purchase.html"
                )
                path = self.pages / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    '<!doctype html><html><head></head><body><main>\n    '
                    f'<p>Preserve this original page: {locale}/{key}.</p>\n'
                    '</main></body></html>',
                    encoding="utf-8",
                )
                records.append({
                    "locale": locale, "app_key": key, "app_store_id": app["app_store_id"],
                    "app_name": key, "verified_live": True,
                    "source_persona_query": self.tasks[0]["evidence"]["intent_queries"][key],
                    "canonical_guide_url": f"{self.site}/{relative}",
                    "app_store_url": f"https://apps.apple.com/us/app/id{app['app_store_id']}",
                    "app_store_cta_label": f"App Store · {key}",
                })
        self.write(hero.INTENTS, {"records": records})
        self.options = {"provider": "118326163", "today": "2026-09-05", "site": self.site}

    def tearDown(self):
        shutil.rmtree(self.folder)

    def write(self, relative, payload):
        target = self.pages / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return target

    def node(self, script, payload):
        process = subprocess.run(
            ["node", "-e", script, str(hero.CORE)],
            input=json.dumps(payload, ensure_ascii=False),
            text=True, capture_output=True, timeout=30, check=False,
        )
        self.assertEqual(0, process.returncode, process.stderr)
        return json.loads(process.stdout)

    def test_exact_fifty_locales_and_reviewed_regional_aliases(self):
        self.assertEqual(set(hero.OFFICIAL_LOCALES), set(self.copy))
        self.assertEqual(50, len(self.copy))
        for locale, values in self.copy.items():
            with self.subTest(locale=locale):
                self.assertEqual(set(hero.JSON_KEYS), set(values))
                self.assertTrue(all(value.strip() for value in values.values()))
                if not locale.startswith("en-"):
                    self.assertNotEqual(self.copy["en-US"]["title"], values["title"])

    def test_table_driven_exact_money_and_unrounded_totals(self):
        cases = [
            ({"hourly_income": "20", "workday_hours": "8",
              "items": [{"name": "A", "quantity": 1, "price": "120"},
                        {"name": "B", "quantity": 2, "price": "45"},
                        {"name": "C", "quantity": 3, "price": "30"}]}, 30000, 15, 1.875),
            ({"hourly_income": "0.10", "workday_hours": "1",
              "items": [{"name": "A", "quantity": 3, "price": "0.10"}]}, 30, 3, 3),
            ({"hourly_income": "3", "workday_hours": "8",
              "items": [{"name": str(index), "quantity": 1, "price": "1"} for index in range(3)]},
             300, 1, .125),
            ({"hourly_income": "1", "workday_hours": "0.25",
              "items": [{"name": "Free", "quantity": 999, "price": "0"}]}, 0, 0, 0),
            ({"hourly_income": "100000", "workday_hours": "8",
              "items": [{"name": "VND example", "quantity": 1, "price": "22000000"}]},
             2200000000, 220, 27.5),
        ]
        outputs = self.node(
            'const core=require(process.argv[1]);const data=JSON.parse(require("node:fs").readFileSync(0,"utf8"));'
            'console.log(JSON.stringify(data.map(input=>core.run("purchase-worktime-v1",input))));',
            [case[0] for case in cases],
        )
        for case, output in zip(cases, outputs, strict=True):
            with self.subTest(input=case[0]):
                self.assertEqual(case[1], output["total_minor"])
                self.assertAlmostEqual(case[2], output["work_hours"])
                self.assertAlmostEqual(case[3], output["workdays"])

    def test_table_driven_invalid_inputs_and_unknown_adapter_fail_closed(self):
        valid = {"hourly_income": "20", "workday_hours": "8",
                 "items": [{"name": "A", "quantity": 1, "price": "2"}]}
        invalid = []
        for key, values in (
            ("hourly_income", ["0", "-1", "NaN", "Infinity", 20, "1e3", "1.001", "100000000.01"]),
            ("workday_hours", ["0", "24.01", "", None]),
        ):
            for value in values:
                item = copy.deepcopy(valid)
                item[key] = value
                invalid.append(item)
        for field, values in (
            ("quantity", [0, -1, 1.5, 1000, "2", True]),
            ("price", ["-0.01", "", "2,50", " 2", "2.123", None]),
            ("name", ["", " ", "line\nbreak", "\x00", "a" * 121]),
        ):
            for value in values:
                item = copy.deepcopy(valid)
                item["items"][0][field] = value
                invalid.append(item)
        invalid += [
            {**valid, "items": []},
            {**valid, "items": valid["items"] * 31},
            {**valid, "bank_account": "not accepted"},
            {**valid, "items": [{**valid["items"][0], "secret": "not accepted"}]},
        ]
        errors = self.node(
            'const core=require(process.argv[1]);const data=JSON.parse(require("node:fs").readFileSync(0,"utf8"));'
            'const out=data.map(input=>{try{core.run("purchase-worktime-v1",input);return false}'
            'catch(e){return e instanceof TypeError||e instanceof RangeError}});'
            'try{core.run("unknown",{});out.push(false)}catch(e){out.push(e instanceof RangeError)}'
            'console.log(JSON.stringify(out));',
            invalid,
        )
        self.assertEqual([True] * (len(invalid) + 1), errors)

    def test_csv_is_localized_self_contained_and_formula_safe(self):
        dangerous = ['=1+1', ' +SUM(A1)', '-1+2', '@SUM(A1)', '\u200f=1+1', 'Comma, "quote"']
        data = {
            "hourly_income": "18.50", "workday_hours": "7.50",
            "items": [{"name": name, "quantity": 2, "price": "0.10"} for name in dangerous],
        }
        result = self.node(
            'const core=require(process.argv[1]);const data=JSON.parse(require("node:fs").readFileSync(0,"utf8"));'
            'console.log(JSON.stringify(core.csv("purchase-worktime-v1",data.input,data.labels)));',
            {"input": data, "labels": self.copy["zh-Hant"]},
        )
        self.assertTrue(result.startswith("\ufeff"))
        self.assertIn("\r\n", result)
        rows = list(csv.reader(io.StringIO(result.removeprefix("\ufeff"))))
        self.assertEqual("購買項目", rows[0][0])
        for row in rows[1:6]:
            self.assertTrue(row[0].startswith("'"), row)
        self.assertEqual('Comma, "quote"', rows[6][0])
        self.assertEqual(["18.50", "7.50"], rows[1][4:6])
        self.assertEqual("1.20", rows[-1][3])

    def test_builds_fifty_real_results_not_per_app_doorways(self):
        report = hero.build(self.pages, **self.options)
        self.assertEqual((50, 2, 1), (report["pages"], report["supported_apps"], report["unserved_apps"]))
        manifest = json.loads((self.pages / hero.MANIFEST).read_text())
        self.assertEqual(50, len({row["url"] for row in manifest["records"]}))
        self.assertEqual(100, manifest["app_locale_pairs"])
        self.assertEqual(["unserved"], manifest["unserved_app_keys"])
        for record in manifest["records"]:
            locale = record["locale"]
            with self.subTest(locale=locale):
                document = (self.pages / record["path"]).read_text()
                self.assertIn(f'lang="{locale}"', document)
                self.assertIn(f'href="{record["url"]}"', document)
                self.assertIn(self.copy[locale]["formula"], document)
                self.assertIn("300.00", document)
                self.assertIn("15.00", document)
                self.assertIn("1.88", document)
                self.assertEqual(51, document.count('hreflang="'))
                self.assertEqual(2, document.count("&amp;ct=geo_learn&amp;mt=8"))
                self.assertIn("connect-src 'none'", document)
                self.assertIn('data-field="name"', document)
                self.assertNotIn("noindex", document)
                example = (self.pages / hero.example_path(self.tasks[0], locale)).read_text()
                self.assertIn(self.copy[locale]["item"], example)
                feed = json.loads((self.pages / hero.feed_path(locale)).read_text())
                self.assertEqual(locale, feed["language"])
                self.assertEqual(record["url"], feed["items"][0]["id"])
                self.assertEqual(2, len(feed["items"][0]["_hero_task"]["optional_apps"]))
                self.assertIn("pt=118326163&ct=geo_learn&mt=8", json.dumps(feed))
        sitemap = ET.parse(self.pages / hero.SITEMAP)
        self.assertEqual(50, len(sitemap.getroot()))
        index = (self.pages / "sitemap_index.xml").read_text()
        self.assertEqual(1, index.count(hero.SITEMAP))
        self.assertEqual(1, len(hero.english_feed_entries(self.pages)))
        with self.assertRaisesRegex(ValueError, "No reviewed"):
            hero.task_for_app(self.tasks, "unserved")

    def test_examples_match_same_javascript_used_in_browser(self):
        hero.build(self.pages, **self.options)
        expected = hero.examples(self.tasks, self.copy)
        for locale in hero.OFFICIAL_LOCALES:
            path = self.pages / hero.example_path(self.tasks[0], locale)
            self.assertEqual(expected[("purchase-worktime", locale)]["csv"].encode(), path.read_bytes())
        manifest = json.loads((self.pages / hero.MANIFEST).read_text())
        core_path = next(path for path in manifest["outputs"] if path.endswith("-hero-task-core.js"))
        self.assertEqual(hero.CORE.read_bytes(), (self.pages / core_path).read_bytes())

    def test_missing_copy_adapter_provider_or_live_binding_never_writes_outputs(self):
        before = sorted(str(path.relative_to(self.pages)) for path in self.pages.rglob("*"))
        raw = json.loads(hero.I18N.read_text())
        raw["locales"].pop("ar-SA")
        broken_copy = self.folder / "broken-copy.json"
        broken_copy.write_text(json.dumps(raw))
        bad_registry = self.folder / "bad-registry.json"
        config = json.loads(hero.REGISTRY.read_text())
        config["tasks"][0]["adapter"] = "unreviewed-v1"
        bad_registry.write_text(json.dumps(config))
        scenarios = [
            {"i18n": broken_copy}, {"registry": bad_registry},
            {"provider": ""}, {"provider": "not-a-token"},
        ]
        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                with self.assertRaises(ValueError):
                    hero.build(self.pages, **(self.options | scenario))
                self.assertEqual(before, sorted(str(path.relative_to(self.pages)) for path in self.pages.rglob("*")))
        state_path = self.pages / ".appstore_live_state.json"
        state_path.write_text('{"live_ids":[]}')
        with self.assertRaisesRegex(ValueError, "inventories disagree"):
            hero.build(self.pages, **self.options)
        self.assertFalse((self.pages / hero.MANIFEST).exists())

    def test_duplicate_adapter_cannot_make_near_identical_canonicals(self):
        payload = json.loads(hero.REGISTRY.read_text())
        duplicate = copy.deepcopy(payload["tasks"][0])
        duplicate.update({"id": "other-app", "slug": "other-app-sheet"})
        duplicate["apps"] = {"otherapp": "98765"}
        payload["tasks"].append(duplicate)
        path = self.folder / "duplicate.json"
        path.write_text(json.dumps(payload))
        with self.assertRaisesRegex(ValueError, "share one canonical"):
            hero.load_registry(path)

    def test_idempotency_semantic_dates_and_preserved_original_content(self):
        hero.build(self.pages, **self.options)
        original = {str(path.relative_to(self.pages)): (path.read_bytes(), path.stat().st_mtime_ns)
                    for path in self.pages.rglob("*") if path.is_file()}
        result = hero.build(self.pages, **(self.options | {"today": "2026-09-06"}))
        self.assertEqual(0, result["changed"])
        for relative, (content, mtime) in original.items():
            self.assertEqual(content, (self.pages / relative).read_bytes(), relative)
            self.assertEqual(mtime, (self.pages / relative).stat().st_mtime_ns, relative)
        hero.build(self.pages, check=True, **(self.options | {"today": "2026-09-06"}))
        for locale in hero.OFFICIAL_LOCALES:
            relative = f"{locale}/hourstag.html" if locale == "bn-BD" else f"{locale}/answers/hourstag-purchase.html"
            source = (self.pages / relative).read_text()
            self.assertEqual(1, source.count(f"<!-- {hero.MARKER}:start -->"))
            self.assertIn(f"Preserve this original page: {locale}/hourstag.", source)

    def test_readback_rejects_tampered_csv_and_symlink_escape(self):
        hero.build(self.pages, **self.options)
        result = self.pages / hero.example_path(self.tasks[0], "en-US")
        result.write_text("wrong result")
        with self.assertRaisesRegex(ValueError, "output gate failed"):
            hero.build(self.pages, check=True, **self.options)
        with self.assertRaises(ValueError):
            hero.safe_path(self.pages, "../outside")
        link = self.pages / "escape"
        link.symlink_to(self.folder)
        with self.assertRaises(ValueError):
            hero.safe_path(self.pages, "escape/file")

    def test_http_readback_checks_every_artifact_without_mutation(self):
        hero.build(self.pages, **self.options)
        base = "https://deployment.example/ios-app-guide"
        def fetcher(url):
            relative = url.removeprefix(base + "/")
            return (self.pages / relative).read_bytes()
        result = readback.verify(self.pages / hero.MANIFEST, base, fetcher=fetcher)
        self.assertEqual(156, result["verified_artifacts"])
        target = self.pages / hero.example_path(self.tasks[0], "ko")
        target.write_text("wrong CDN bytes")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            readback.verify(self.pages / hero.MANIFEST, base, fetcher=fetcher)
        self.assertEqual("wrong CDN bytes", target.read_text())

    def test_manifest_matches_published_json_schema(self):
        import jsonschema
        hero.build(self.pages, **self.options)
        payload = json.loads((self.pages / hero.MANIFEST).read_text())
        schema = json.loads((self.pages / hero.SCHEMA).read_text())
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
        validator.validate(payload)
        with self.assertRaises(jsonschema.ValidationError):
            validator.validate(payload | {"locale_count": 49})

    def test_only_unmodified_owned_stale_assets_are_removed(self):
        hero.build(self.pages, **self.options)
        path = self.pages / hero.MANIFEST
        manifest = json.loads(path.read_text())
        relative = "assets/hero-tasks/previous-hero-task.css"
        stale = self.pages / relative
        stale.write_bytes(b"old generated asset")
        manifest["outputs"][relative] = hero.digest(stale.read_bytes())
        path.write_text(hero.json_text(manifest))
        self.assertEqual(1, hero.build(self.pages, **self.options)["removed"])
        self.assertFalse(stale.exists())
        manifest = json.loads(path.read_text())
        stale.write_bytes(b"someone edited this")
        manifest["outputs"][relative] = hero.digest(b"old generated asset")
        path.write_text(hero.json_text(manifest))
        with self.assertRaisesRegex(ValueError, "Refusing to delete"):
            hero.build(self.pages, **self.options)
        self.assertEqual(b"someone edited this", stale.read_bytes())

    def test_publish_and_cloud_pipeline_cannot_upload_partial_results(self):
        import yaml
        source = (GEO / "publish.py").read_text()
        self.assertIn('"hero_tasks.py"), "--check"', source)
        self.assertLess(source.index('"hero_tasks.py"'), source.index('"gen_link_hubs.py"'))
        daily = (hero.DEFAULT_PAGES / ".github/workflows/geo-daily.yml").read_text()
        lines = daily.splitlines()
        for index, line in enumerate(lines):
            if line.strip() == "python3 gen_feed.py":
                self.assertIn("hero_tasks.py", lines[index - 1])
        self.assertIn("Seal complete local-only hero results", daily)
        self.assertIn('node-version: "22"', daily)
        deploy = (hero.DEFAULT_PAGES / ".github/workflows/pages.yml").read_text()
        self.assertIsInstance(yaml.safe_load(daily)["jobs"], dict)
        self.assertIsInstance(yaml.safe_load(deploy)["jobs"], dict)
        self.assertLess(deploy.index("hero_tasks.py --pages-dir . --check"), deploy.index("Upload artifact"))
        self.assertLess(deploy.index("Verify every hero result"), deploy.index("Notify WebSub subscribers"))
        self.assertEqual(3, deploy.count("steps.verify_hero.outcome == 'success'"))

    def test_private_inputs_cannot_become_public_urls_or_script(self):
        source = hero.CORE.read_text() + hero.UI.read_text()
        for forbidden in ("fetch(", "XMLHttpRequest", "localStorage", "sessionStorage",
                          "indexedDB", "sendBeacon", "location.search", "location.hash"):
            self.assertNotIn(forbidden, source)
        self.assertIn('window.addEventListener("pagehide", restore)', source)
        self.assertIn("URL.revokeObjectURL", source)
        self.assertNotIn("</script>", hero.script_json({"name": "</script><script>alert(1)</script>"}))

    def test_browser_downloads_private_result_and_all_fifty_locales_fit(self):
        hero.build(self.pages, **self.options)
        process = subprocess.run(
            ["node", str(GEO / "tests" / "hero_task_browser.cjs"), str(self.pages), str(self.folder)],
            capture_output=True, text=True, timeout=180, check=False,
            env={**os.environ, "TMPDIR": str(self.folder)},
        )
        self.assertEqual(0, process.returncode, process.stdout + process.stderr)
        self.assertIn('"locales":50', process.stdout)
        self.assertIn('"downloads":1', process.stdout)


if __name__ == "__main__":
    unittest.main()
