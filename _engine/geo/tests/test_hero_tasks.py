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
from unittest import mock
import uuid
import xml.etree.ElementTree as ET

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import hero_tasks as hero  # noqa: E402
import hero_tasks_readback as readback  # noqa: E402
import sync_standard_site as sync  # noqa: E402
from hero_task_html import Document, without_resource  # noqa: E402


class HeroTaskTests(unittest.TestCase):
    def setUp(self):
        self.folder = GEO / ".hero-validation" / f"fixture-{uuid.uuid4().hex}"
        self.folder.mkdir(parents=True)
        self.pages = self.folder / "site"
        self.pages.mkdir()
        self.tasks = hero.load_registry()
        self.copy = hero.load_i18n()
        self.task_copies = hero.load_task_i18n()
        self.site = hero.DEFAULT_SITE
        apps = [
            {"key": key, "app_store_id": app_id, "name": key, "verified_live": True,
             "purchase_model": "paid_upfront" if key == "hourstag" else "free_with_lifetime_unlock"}
            for task in self.tasks for key, app_id in task["apps"].items()
        ]
        self.served = len(apps)
        apps.append({"key": "unserved", "app_store_id": "99999999", "verified_live": True})
        self.write(hero.FINDER, {"record_count": len(apps), "apps": apps})
        self.write(".appstore_live_state.json", {"live_ids": [app["app_store_id"] for app in apps]})
        records = []
        self.original_pages = {}
        for locale in hero.OFFICIAL_LOCALES:
            home_links = []
            for app in apps[:self.served]:
                key = app["key"]
                relative = (
                    f"{locale}/{key}.html" if locale == "bn-BD"
                    else f"{locale}/answers/{key}-purchase.html"
                )
                path = self.pages / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                heading = f'<h1 class="p-name" id="primary-heading">{key}</h1>'
                summary = f'<p class="lead p-summary" id="primary-summary">{locale} original summary.</p>'
                cta = (
                    f'<a class="cta" id="primary-cta" href="https://apps.apple.com/app/id{app["app_store_id"]}">'
                    f'{key} on the App Store</a>'
                )
                if locale == "bn-BD":
                    introduction = (
                        heading + summary + '<!-- app-decision-card:start -->'
                        '<aside class="iag-decision-card"><div>' + cta + "</div></aside>"
                        '<!-- app-decision-card:end -->'
                    )
                else:
                    introduction = '<section class="hero wrap">' + heading + summary + '<div>' + cta + "</div></section>"
                source = (
                    '<!doctype html><html><head><meta name="description" content="Original app page"></head>'
                    '<body><div class="h-entry"><div class="e-content"><main>\n    '
                    + introduction + '<section><h2>Original details</h2>'
                    f'<p>Preserve this original page: {locale}/{key}.</p></section>\n'
                    '</main></div></div></body></html>'
                )
                path.write_text(source, encoding="utf-8")
                self.original_pages[relative] = source
                home_links.append(f'<a href="{self.site}/{relative}">{key}</a>')
                records.append({
                    "locale": locale, "app_key": key, "app_store_id": app["app_store_id"],
                    "app_name": key, "verified_live": True,
                    "source_persona_query": hero.task_for_app(self.tasks, key)["evidence"]["intent_queries"][key],
                    "canonical_guide_url": f"{self.site}/{relative}",
                    "app_store_url": f"https://apps.apple.com/us/app/id{app['app_store_id']}",
                    "app_store_cta_label": f"App Store · {key}",
                })
            self.navigation_page(
                f"{locale}/index.html", locale, "".join(home_links), title="Existing app catalogue"
            )
        self.original_indexes = {}
        for locale in hero.OFFICIAL_LOCALES[:10]:
            relative = f"{locale}/tools/index.html"
            for slug in ("one", "two"):
                self.navigation_page(f"{locale}/tools/{slug}.html", locale, "<p>Working tool fixture.</p>", title=slug)
            self.navigation_page(
                relative, locale,
                '<section><h2>Existing tools</h2><article><a href="one.html">First working tool</a></article>'
                '<article><a href="two.html">Second working tool</a></article></section>',
                title="Existing full tools hub",
            )
            self.original_indexes[relative] = (self.pages / relative).read_text()
        self.write(hero.INTENTS, {"records": records})
        self.options = {"provider": "118326163", "today": "2026-09-05", "site": self.site}

    def tearDown(self):
        shutil.rmtree(self.folder)

    def write(self, relative, payload):
        target = self.pages / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return target

    def navigation_page(self, relative, locale, content, *, title):
        path = self.pages / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f'<!doctype html><html lang="{locale}"><head><title>{title}</title>'
            f'<meta name="description" content="{title} with useful resources">'
            f'<link rel="canonical" href="{self.site}/{relative}">'
            f'<link rel="alternate" hreflang="{locale}" href="{self.site}/{relative}">'
            '<script type="application/ld+json">{"@type":"ItemList","numberOfItems":2}</script>'
            '</head><body><header class="hero">'
            f'<h1>{title}</h1><p class="lead">Original introductory context.</p></header>'
            f'<main>{content}</main></body></html>',
            encoding="utf-8",
        )
        return path

    def add_legacy_thin_indexes(self):
        paths = []
        for locale in hero.OFFICIAL_LOCALES[10:]:
            relative = f"{locale}/tools/index.html"
            path = self.pages / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                f'<!doctype html><html lang="{locale}"><head><title>Free tools</title>'
                '<meta name="hero-tools-index" content="v1">'
                f'<link rel="canonical" href="{self.site}/{relative}">'
                '</head><body><main>'
                + hero.resource_block(locale, self.tasks, self.copy[locale], self.site)
                + '<h1>Free tools</h1></main></body></html>',
                encoding="utf-8",
            )
            paths.append(relative)
        return paths

    def standard_site_contract(self):
        uri = "at://did:plc:kboucnzkxzmqmatvhes4xlt4/site.standard.publication/3mabcde234567"
        body = uri + "\n"
        return json.dumps({
            "contract_version": 1, "generated_at": "2026-07-28T00:00:00.000Z",
            "publication": {
                "url": sync.PUBLICATION_URL, "at_uri": uri,
                "discovery_link_tag": f'<link rel="{sync.PUBLICATION_COLLECTION}" href="{uri}">',
                "well_known": {
                    "request_url": sync.WELL_KNOWN_URL, "request_path": sync.WELL_KNOWN_PATH,
                    "content_type": "text/plain; charset=utf-8", "body": body,
                    "sha256": hero.digest(body.encode()), "deploy_at_origin_root": True,
                },
            },
            "documents": [],
        }).encode()

    def test_standard_site_links_survive_fifty_pages_and_repeated_sync(self):
        hero.build(self.pages, **self.options)
        payload = self.standard_site_contract()
        synced = sync.synchronize_payload(payload, site_root=self.pages)
        self.assertGreater(synced.html_changed, 0)
        synchronized = {
            locale: (self.pages / hero.resource_path(self.tasks[0], locale)).read_bytes()
            for locale in hero.OFFICIAL_LOCALES
        }
        hero.build(self.pages, **self.options)
        manifest = json.loads((self.pages / hero.MANIFEST).read_text())
        for locale in hero.OFFICIAL_LOCALES:
            relative = hero.resource_path(self.tasks[0], locale)
            content = (self.pages / relative).read_bytes()
            with self.subTest(locale=locale):
                self.assertEqual(synchronized[locale], content)
                self.assertEqual(1, content.count(b'rel="site.standard.publication"'))
                self.assertEqual(hero.digest(content), manifest["outputs"][relative])
        stable = {relative: (self.pages / relative).read_bytes() for relative in manifest["outputs"]}
        stable[hero.MANIFEST] = (self.pages / hero.MANIFEST).read_bytes()
        for _ in range(3):
            self.assertEqual(0, sync.synchronize_payload(payload, site_root=self.pages).html_changed)
            self.assertEqual(0, hero.build(self.pages, **self.options)["changed"])
            for relative, content in stable.items():
                self.assertEqual(content, (self.pages / relative).read_bytes(), relative)

    def test_standard_site_document_link_and_malformed_link_fail_closed(self):
        hero.build(self.pages, **self.options)
        path = self.pages / hero.resource_path(self.tasks[0], "en-US")
        publication = json.loads(self.standard_site_contract())["publication"]["discovery_link_tag"]
        document = '<link rel="site.standard.document" href="at://did:plc:kboucnzkxzmqmatvhes4xlt4/site.standard.document/3mabcdef23456">'
        synchronized = sync.render_html(path.read_text(), publication_link_tag=publication,
                                        document_link_tag=document, label=str(path))
        path.write_text(synchronized)
        hero.build(self.pages, **self.options)
        self.assertEqual(synchronized, path.read_text())
        broken = synchronized.replace(publication, "")
        path.write_text(broken)
        before = (self.pages / hero.MANIFEST).read_bytes()
        with self.assertRaises(sync.SyncError):
            hero.build(self.pages, **self.options)
        self.assertEqual(broken, path.read_text())
        self.assertEqual(before, (self.pages / hero.MANIFEST).read_bytes())

    def test_forty_legacy_thin_indexes_are_retired_not_recreated(self):
        hero.build(self.pages, **self.options)
        legacy = self.add_legacy_thin_indexes()
        self.assertEqual(40, len(legacy))
        manifest_path = self.pages / hero.MANIFEST
        old = json.loads(manifest_path.read_text())
        old.pop("retired_indexes", None)
        old["integrations"] = sorted(set(old["integrations"]) | set(legacy))
        manifest_path.write_text(hero.json_text(old))
        with self.assertRaisesRegex(ValueError, "retiring 40"):
            hero.build(self.pages, check=True, **self.options)
        report = hero.build(self.pages, **self.options)
        self.assertEqual(40, report["removed"])
        manifest = json.loads(manifest_path.read_text())
        self.assertEqual(sorted(legacy), manifest["retired_indexes"])
        self.assertEqual(10, len(list(self.pages.glob("*/tools/index.html"))))
        for relative in legacy:
            self.assertFalse((self.pages / relative).exists(), relative)
            self.assertNotIn(relative, manifest["integrations"])
        for record in manifest["records"]:
            locale = record["locale"]
            expected = f"{locale}/tools/index.html" if locale in hero.OFFICIAL_LOCALES[:10] else f"{locale}/index.html"
            self.assertEqual(f"{self.site}/{expected}", record["navigation_url"])
            feed = json.loads((self.pages / hero.feed_path(locale)).read_text())
            self.assertEqual(f"{self.site}/{expected}", feed["home_page_url"])
            self.assertIn(f'href="{self.site}/{expected}"', (self.pages / record["path"]).read_text())
        stable = manifest_path.read_bytes()
        self.assertEqual(0, hero.build(self.pages, **self.options)["changed"])
        self.assertEqual(stable, manifest_path.read_bytes())
        self.assertEqual(10, len(list(self.pages.glob("*/tools/index.html"))))
        hero.build(self.pages, check=True, **self.options)

    def test_ten_existing_hubs_preserve_metadata_hreflang_and_original_cards(self):
        hero.build(self.pages, **self.options)
        self.assertEqual(10, len(self.original_indexes))
        for relative, original in self.original_indexes.items():
            updated = (self.pages / relative).read_text()
            with self.subTest(relative=relative):
                self.assertEqual(original, without_resource(updated, hero.MARKER))
                self.assertEqual(original.split("</head>")[0], updated.split("</head>")[0])
                self.assertEqual(1, updated.count(f"<!-- {hero.MARKER}:start -->"))
                self.assertLess(updated.index("</h1>"), updated.index(f"<!-- {hero.MARKER}:start -->"))
                self.assertLess(updated.index("Original introductory context."), updated.index(f"<!-- {hero.MARKER}:start -->"))
                self.assertIn("First working tool", updated)
                self.assertIn("Second working tool", updated)

    def test_missing_or_ineligible_navigation_does_not_manufacture_a_landing_page(self):
        locale = hero.OFFICIAL_LOCALES[-1]
        (self.pages / f"{locale}/index.html").unlink()
        hero.build(self.pages, **self.options)
        document = (self.pages / hero.resource_path(self.tasks[0], locale)).read_text()
        nav = re.search(r"<nav>(.*?)</nav>", document, re.S).group(1)
        self.assertNotIn("<a", nav)
        self.assertFalse((self.pages / f"{locale}/tools/index.html").exists())
        feed = json.loads((self.pages / hero.feed_path(locale)).read_text())
        self.assertEqual(f"{self.site}/{hero.resource_path(self.tasks[0], locale)}", feed["home_page_url"])

    def test_retirement_refuses_foreign_content_and_accepts_a_real_replacement_hub(self):
        legacy = self.add_legacy_thin_indexes()
        changed = self.pages / legacy[0]
        changed.write_text(changed.read_text().replace("</main>", "<article>Other owner's work</article></main>"))
        with self.assertRaisesRegex(ValueError, "other content"):
            hero.build(self.pages, **self.options)
        self.assertFalse((self.pages / hero.MANIFEST).exists())
        self.assertTrue(all((self.pages / relative).exists() for relative in legacy))
        self.add_legacy_thin_indexes()
        hero.build(self.pages, **self.options)
        locale = hero.OFFICIAL_LOCALES[10]
        self.navigation_page(f"{locale}/tools/index.html", locale,
                             '<a href="one.html">One useful tool</a><a href="two.html">Another useful tool</a>',
                             title="Reviewed replacement catalogue")
        hero.build(self.pages, **self.options)
        manifest = json.loads((self.pages / hero.MANIFEST).read_text())
        self.assertNotIn(f"{locale}/tools/index.html", manifest["retired_indexes"])
        self.assertIn("Reviewed replacement catalogue", (self.pages / f"{locale}/tools/index.html").read_text())

    def test_one_hundred_pages_keep_heading_summary_cta_and_microformat_order(self):
        hero.build(self.pages, **self.options)
        self.assertEqual(50 * self.served, len(self.original_pages))
        for relative, original in self.original_pages.items():
            updated = (self.pages / relative).read_text()
            marker = updated.index(f"<!-- {hero.MARKER}:start -->")
            with self.subTest(relative=relative):
                self.assertEqual(original, without_resource(updated, hero.MARKER))
                self.assertLess(updated.index('id="primary-heading"'), marker)
                self.assertLess(updated.index('id="primary-summary"'), marker)
                self.assertLess(updated.index("</a>", updated.index('id="primary-cta"')), marker)
                if "<!-- app-decision-card:end -->" in updated:
                    self.assertLess(updated.index("<!-- app-decision-card:end -->"), marker)
                tree = Document(updated)
                resource = next(node for node in tree.nodes if node.attrs.get("data-primary-resource") == "hero-task")
                content = next(node for node in tree.nodes if "e-content" in node.classes)
                self.assertTrue(resource.within(content))
                self.assertNotEqual("a", resource.parent.tag)
                self.assertNotEqual("p", resource.parent.tag)
                self.assertEqual(1, len([node for node in tree.nodes if "h-entry" in node.classes]))
                self.assertLess(updated.index("<h1"), updated.index("<h2"))
                own_block = updated[marker:updated.index(f"<!-- {hero.MARKER}:end -->", marker) + len(f"<!-- {hero.MARKER}:end -->")]
                self.assertEqual(updated, hero.insert_block(updated, own_block, label=relative))

    def test_semantic_insertion_preserves_inner_microformat_content_and_skips_ghost_cta(self):
        source = (
            '<html><body><main><article class="h-entry"><h1 class="p-name">Original question</h1>'
            '<p class="p-summary">Original summary</p><a class="cta ghost" href="#preview">Preview</a>'
            '<div class="actions"><a class="cta" id="real-cta" href="https://apps.apple.com/app/id6754218117">Install</a></div>'
            '<div class="e-content"><h2>Answer</h2><p>Original answer text.</p></div></article></main></body></html>'
        )
        block = hero.resource_block("en-US", self.tasks, self.copy["en-US"], self.site)
        updated = hero.insert_block(source, block)
        self.assertEqual(source, without_resource(updated, hero.MARKER))
        self.assertLess(updated.index('id="real-cta"'), updated.index(f"<!-- {hero.MARKER}:start -->"))
        self.assertIn('<div class="e-content"><h2>Answer</h2><p>Original answer text.</p></div>', updated)
        tree = Document(updated)
        resource = next(node for node in tree.nodes if node.attrs.get("data-primary-resource") == "hero-task")
        content = next(node for node in tree.nodes if "e-content" in node.classes)
        self.assertFalse(resource.within(content))
        self.assertEqual(updated, hero.insert_block(updated, block))
        with self.assertRaisesRegex(ValueError, "primary h1"):
            hero.insert_block("<html><body><main><p>No heading</p></main></body></html>", block)

    def test_published_one_hundred_introductions_keep_their_original_priority(self):
        tasks = hero.load_registry()
        _, bindings = hero.catalogs(hero.DEFAULT_PAGES, tasks, hero.DEFAULT_SITE, "118326163")
        self.assertEqual(50 * sum(len(task["apps"]) for task in tasks), len(bindings))
        for binding in bindings.values():
            relative = binding["answer_path"]
            source = (hero.DEFAULT_PAGES / relative).read_text()
            tree = Document(source)
            heading = tree.first("h1")
            resources = [node for node in tree.nodes if node.attrs.get("data-primary-resource") == "hero-task"]
            with self.subTest(relative=relative):
                self.assertEqual(1, len(resources))
                resource = resources[0]
                self.assertLess(heading.end, resource.start)
                store = next(node for node in tree.nodes if node.tag == "a" and node.start > heading.end
                             and (node.attrs.get("href") or "").startswith("https://apps.apple.com/"))
                self.assertLess(store.end, resource.start)
                for node in tree.nodes:
                    if "p-summary" in node.classes and node.start < store.start:
                        self.assertLess(node.end, resource.start)
                marker_start = source.index(f"<!-- {hero.MARKER}:start -->")
                marker_end = source.index(f"<!-- {hero.MARKER}:end -->") + len(f"<!-- {hero.MARKER}:end -->")
                block = source[marker_start:marker_end]
                self.assertEqual(source, hero.insert_block(source, block, label=relative))

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

    def maintenance_node(self, script, payload):
        process = subprocess.run(
            ["node", "-e", script, str(hero.MAINTENANCE_CORE)],
            input=json.dumps(payload, ensure_ascii=False),
            text=True, capture_output=True, timeout=30, check=False,
        )
        self.assertEqual(0, process.returncode, process.stderr)
        return json.loads(process.stdout)

    def test_task_copy_layers_only_the_tasks_own_keys_over_the_shared_copy(self):
        self.assertEqual({"maintenance-next-due", "project-profit", "battery-wear"}, set(self.task_copies))
        self.assertEqual(["purchase-worktime", "maintenance-next-due", "project-profit", "battery-wear"],
                         [task["id"] for task in self.tasks])
        for locale in hero.OFFICIAL_LOCALES:
            with self.subTest(locale=locale):
                self.assertIs(self.copy[locale], hero.task_copy(self.copy, self.task_copies, self.tasks[0], locale))
                titles = {self.copy[locale]["title"]}
                for task in self.tasks[1:]:
                    own = hero.task_copy(self.copy, self.task_copies, task, locale)
                    self.assertEqual(set(hero.JSON_KEYS) | set(hero.TASK_KEYS[task["id"]]), set(own))
                    self.assertEqual(self.copy[locale]["remove"], own["remove"])
                    self.assertNotIn(own["title"], titles)
                    titles.add(own["title"])
                    self.assertTrue(all(value.strip() for value in own.values()))
                    if not locale.startswith("en-"):
                        self.assertNotEqual(self.task_copies[task["id"]]["en-US"]["title"], own["title"])
                maintenance = hero.task_copy(self.copy, self.task_copies, self.tasks[1], locale)
                for unit in hero.UNITS:
                    self.assertTrue(all(form.strip() for form in maintenance[f"unit_{unit}"].split("|")))
                battery = hero.task_copy(self.copy, self.task_copies, self.tasks[3], locale)
                # BattAI contract: estimates are labelled and reported as a band, never a score.
                self.assertNotEqual(battery["marker_provided"], battery["marker_estimated"])
                self.assertNotEqual(battery["low"], battery["high"])
        raw = json.loads(hero.I18N.read_text())
        raw["tasks"]["maintenance-next-due"]["locales"]["ja"][0] = raw["tasks"]["maintenance-next-due"]["locales"]["en-US"][0]
        broken = self.folder / "english-fallback.json"
        broken.write_text(json.dumps(raw))
        with self.assertRaisesRegex(ValueError, "English fallback"):
            hero.load_task_i18n(broken)
        raw["tasks"]["maintenance-next-due"]["keys"].append("extra")
        broken.write_text(json.dumps(raw))
        with self.assertRaisesRegex(ValueError, "Unexpected localization keys"):
            hero.load_task_i18n(broken)

    def test_maintenance_table_driven_month_end_leap_year_and_status(self):
        cases = [
            ({"name": "Quarter", "last_done": "2026-06-01", "interval_value": 3, "interval_unit": "month"},
             "2026-09-01", -4, "overdue"),
            ({"name": "Week", "last_done": "2026-08-31", "interval_value": 1, "interval_unit": "week"},
             "2026-09-07", 2, "due_soon"),
            ({"name": "Today", "last_done": "2026-08-29", "interval_value": 7, "interval_unit": "day"},
             "2026-09-05", 0, "due_soon"),
            ({"name": "Edge", "last_done": "2026-08-29", "interval_value": 14, "interval_unit": "day"},
             "2026-09-12", 7, "due_soon"),
            ({"name": "Ok", "last_done": "2026-08-29", "interval_value": 15, "interval_unit": "day"},
             "2026-09-13", 8, "ok"),
            ({"name": "Jan31", "last_done": "2024-01-31", "interval_value": 1, "interval_unit": "month"},
             "2024-02-29", -919, "overdue"),
            ({"name": "Jan31 non-leap", "last_done": "2025-01-31", "interval_value": 1, "interval_unit": "month"},
             "2025-02-28", -554, "overdue"),
            ({"name": "Leap day yearly", "last_done": "2024-02-29", "interval_value": 12, "interval_unit": "month"},
             "2025-02-28", -554, "overdue"),
            ({"name": "Leap to leap", "last_done": "2024-02-29", "interval_value": 48, "interval_unit": "month"},
             "2028-02-29", 542, "ok"),
            ({"name": "Year wrap", "last_done": "2026-11-30", "interval_value": 3, "interval_unit": "month"},
             "2027-02-28", 176, "ok"),
            ({"name": "Max", "last_done": "2026-09-05", "interval_value": 3650, "interval_unit": "day"},
             "2036-09-02", 3650, "ok"),
        ]
        output = self.maintenance_node(
            'const core=require(process.argv[1]);const data=JSON.parse(require("node:fs").readFileSync(0,"utf8"));'
            'console.log(JSON.stringify(core.run("maintenance-next-due-v1",data)));',
            {"today": "2026-09-05", "items": [case[0] for case in cases]},
        )
        for case, item in zip(cases, output["items"], strict=True):
            with self.subTest(name=case[0]["name"]):
                self.assertEqual(case[1:], (item["next_due"], item["days_left"], item["status"]))
        self.assertEqual([5, 6, 7, 0, 2, 1, 3, 4, 9, 8, 10], output["order"])
        self.assertEqual({"overdue": 4, "due_soon": 3, "ok": 4}, output["counts"])
        self.assertEqual("2026-09-05", output["today"])

    def test_maintenance_invalid_inputs_and_unknown_adapter_fail_closed(self):
        valid = {"today": "2026-09-05",
                 "items": [{"name": "A", "last_done": "2026-06-01", "interval_value": 3, "interval_unit": "month"}]}
        invalid = []
        for value in ["2026-9-5", "2026/09/05", "2026-02-30", "2025-02-29", "1899-12-31", "3000-01-01", "", None, 20260905]:
            invalid.append({**valid, "today": value})
        for field, values in (
            ("last_done", ["2026-13-01", "2026-04-31", "05-09-2026", "2026-09-05T00:00", "", None]),
            ("interval_value", [0, -1, 3651, 1.5, "3", True, None]),
            ("interval_unit", ["year", "days", "", None, 1]),
            ("name", ["", " ", "line\nbreak", "\x00", "a" * 121]),
        ):
            for value in values:
                item = copy.deepcopy(valid)
                item["items"][0][field] = value
                invalid.append(item)
        invalid += [
            {**valid, "items": []},
            {**valid, "items": valid["items"] * 31},
            {**valid, "reminder": "not accepted"},
            {**valid, "items": [{**valid["items"][0], "notes": "not accepted"}]},
            {"today": "2999-12-31", "items": [{"name": "Beyond", "last_done": "2999-12-31", "interval_value": 1, "interval_unit": "month"}]},
        ]
        errors = self.maintenance_node(
            'const core=require(process.argv[1]);const data=JSON.parse(require("node:fs").readFileSync(0,"utf8"));'
            'const out=data.map(input=>{try{core.run("maintenance-next-due-v1",input);return false}'
            'catch(e){return e instanceof TypeError||e instanceof RangeError}});'
            'try{core.run("purchase-worktime-v1",{});out.push(false)}catch(e){out.push(e instanceof RangeError)}'
            'console.log(JSON.stringify(out));',
            invalid,
        )
        self.assertEqual([True] * (len(invalid) + 1), errors)

    def test_maintenance_csv_is_localized_sorted_singular_plural_and_formula_safe(self):
        labels = hero.task_copy(self.copy, self.task_copies, self.tasks[1], "de-DE")
        data = {"today": "2026-09-05", "items": [
            {"name": "=1+1", "last_done": "2026-08-01", "interval_value": 1, "interval_unit": "month"},
            {"name": "+SUM(A1)", "last_done": "2026-09-01", "interval_value": 2, "interval_unit": "week"},
            {"name": "\u200f=1+1", "last_done": "2026-09-04", "interval_value": 1, "interval_unit": "day"},
            {"name": 'Komma, "Zitat"', "last_done": "2026-06-01", "interval_value": 3, "interval_unit": "month"},
        ]}
        result = self.maintenance_node(
            'const core=require(process.argv[1]);const data=JSON.parse(require("node:fs").readFileSync(0,"utf8"));'
            'console.log(JSON.stringify(core.csv("maintenance-next-due-v1",data.input,data.labels)));',
            {"input": data, "labels": labels},
        )
        self.assertTrue(result.startswith("\ufeff"))
        self.assertIn("\r\n", result)
        rows = list(csv.reader(io.StringIO(result.removeprefix("\ufeff"))))
        self.assertEqual(["Aufgabe", "Zuletzt erledigt", "Wiederholung alle", "Nächste Fälligkeit", "Resttage", "Status"], rows[0])
        self.assertEqual(["-4", "-4", "0", "10"], [row[4] for row in rows[1:5]])
        self.assertEqual({"'=1+1", "'+SUM(A1)", "'\u200f=1+1", 'Komma, "Zitat"'}, {row[0] for row in rows[1:5]})
        self.assertEqual({"1 Monat", "3 Monate", "2 Wochen", "1 Tag"}, {row[2] for row in rows[1:5]})
        self.assertEqual("Überfällig", rows[1][5])
        self.assertEqual(["Heute", "2026-09-05", "", "", "", ""], rows[5])
        with self.assertRaises(AssertionError):
            self.maintenance_node(
                'const core=require(process.argv[1]);const data=JSON.parse(require("node:fs").readFileSync(0,"utf8"));'
                'console.log(JSON.stringify(core.csv("maintenance-next-due-v1",data.input,data.labels)));',
                {"input": data, "labels": self.copy["de-DE"]},
            )

    def adapter_node(self, core, script, payload):
        process = subprocess.run(
            ["node", "-e", script, str(core)],
            input=json.dumps(payload, ensure_ascii=False),
            text=True, capture_output=True, timeout=30, check=False,
        )
        self.assertEqual(0, process.returncode, process.stderr)
        return json.loads(process.stdout)

    RUN = ('const core=require(process.argv[1]);const data=JSON.parse(require("node:fs").readFileSync(0,"utf8"));'
           'console.log(JSON.stringify(data.map(input=>core.run(process.env.ADAPTER,input))));')
    CSV = ('const core=require(process.argv[1]);const data=JSON.parse(require("node:fs").readFileSync(0,"utf8"));'
           'console.log(JSON.stringify(core.csv(process.env.ADAPTER,data.input,data.labels)));')
    FAIL_CLOSED = (
        'const core=require(process.argv[1]);const data=JSON.parse(require("node:fs").readFileSync(0,"utf8"));'
        'const out=data.map(input=>{try{core.run(process.env.ADAPTER,input);return false}'
        'catch(e){return e instanceof TypeError||e instanceof RangeError}});'
        'try{core.run("purchase-worktime-v1",{});out.push(false)}catch(e){out.push(e instanceof RangeError)}'
        'console.log(JSON.stringify(out));'
    )

    def profit_node(self, script, payload):
        with mock.patch.dict(os.environ, {"ADAPTER": "project-profit-v1"}):
            return self.adapter_node(hero.PROFIT_CORE, script, payload)

    def battery_node(self, script, payload):
        with mock.patch.dict(os.environ, {"ADAPTER": "battery-wear-range-v1"}):
            return self.adapter_node(hero.BATTERY_CORE, script, payload)

    def test_profit_table_driven_exact_minor_units_margin_and_hourly_net(self):
        rows = lambda *pairs: [{"name": f"{kind} {index}", "kind": kind, "amount": amount}
                               for index, (kind, amount) in enumerate(pairs)]
        cases = [
            ({"project_name": "Landing page", "hours_spent": "12.5",
              "items": rows(("income", "1500"), ("expense", "320.40"), ("expense", "79.99"))},
             150000, 40039, 109961, 109961 / 150000, 8796.88),
            ({"project_name": "Loss", "hours_spent": "0.25", "items": rows(("income", "10"), ("expense", "25.5"))},
             1000, 2550, -1550, -1.55, -6200.0),
            ({"project_name": "No income", "hours_spent": "", "items": rows(("expense", "0.10"), ("expense", "0.20"))},
             0, 30, -30, None, None),
            ({"project_name": "No hours", "hours_spent": "", "items": rows(("income", "0.01"))},
             1, 0, 1, 1.0, None),
            ({"project_name": "Float trap", "hours_spent": "2000",
              "items": rows(*[("income", "0.10")] * 20, *[("expense", "0.30")] * 3)},
             200, 90, 110, 0.55, 0.055),
            ({"project_name": "Max", "hours_spent": "1", "items": rows(("income", "100000000"), ("expense", "0"))},
             10000000000, 0, 10000000000, 1.0, 10000000000.0),
        ]
        outputs = self.profit_node(self.RUN, [case[0] for case in cases])
        for case, output in zip(cases, outputs, strict=True):
            with self.subTest(project=case[0]["project_name"]):
                self.assertEqual(case[1:4], (output["income_total_minor"], output["expense_total_minor"], output["profit_minor"]))
                if case[4] is None:
                    self.assertIsNone(output["margin"])
                else:
                    self.assertAlmostEqual(case[4], output["margin"])
                if case[5] is None:
                    self.assertIsNone(output["hourly_net_minor"])
                    self.assertIsNone(output["hours_spent"])
                else:
                    self.assertAlmostEqual(case[5], output["hourly_net_minor"])
                self.assertTrue(all(isinstance(item["amount_minor"], int) for item in output["items"]))
        self.assertEqual("87.97", hero.money_text(outputs[0]["hourly_net_minor"]))
        self.assertEqual("-15.50", hero.money_text(outputs[1]["profit_minor"]))
        self.assertEqual(("73.3%", "—"), (hero.percent_text(outputs[0]["margin"]), hero.percent_text(None)))

    def test_profit_invalid_inputs_and_unknown_adapter_fail_closed(self):
        valid = {"project_name": "Landing page", "hours_spent": "12.5",
                 "items": [{"name": "Fee", "kind": "income", "amount": "1500"}]}
        invalid = []
        for value in ["", " ", "line\nbreak", "\x00", "a" * 121, None, 5]:
            invalid.append({**valid, "project_name": value})
        for value in ["0", "0.1", "12.3", "2000.25", "-1", "1e3", "NaN", 12.5, None]:
            invalid.append({**valid, "hours_spent": value})
        for field, values in (
            ("amount", ["-0.01", "", "1,50", " 2", "2.123", "100000000.01", "1e3", 1500, None]),
            ("kind", ["profit", "", None, 1]),
            ("name", ["", " ", "line\nbreak", "\x00", "a" * 121]),
        ):
            for value in values:
                item = copy.deepcopy(valid)
                item["items"][0][field] = value
                invalid.append(item)
        invalid += [
            {**valid, "items": []},
            {**valid, "items": valid["items"] * 21},
            {**valid, "items": [{**valid["items"][0], "kind": "expense"}] * 21},
            {**valid, "currency": "not accepted"},
            {**valid, "items": [{**valid["items"][0], "tax": "not accepted"}]},
        ]
        errors = self.profit_node(self.FAIL_CLOSED, invalid)
        self.assertEqual([True] * (len(invalid) + 1), errors)

    def test_profit_csv_is_localized_formula_safe_and_keeps_negative_profit_numeric(self):
        labels = hero.task_copy(self.copy, self.task_copies, self.tasks[2], "ja")
        data = {"project_name": "=HYPERLINK()", "hours_spent": "2", "items": [
            {"name": "=1+1", "kind": "income", "amount": "10"},
            {"name": "+SUM(A1)", "kind": "expense", "amount": "25.5"},
            {"name": "\u200f@cmd", "kind": "expense", "amount": "0.05"},
            {"name": 'Comma, "quote"', "kind": "income", "amount": "0.01"},
        ]}
        result = self.profit_node(self.CSV, {"input": data, "labels": labels})
        self.assertTrue(result.startswith("\ufeff"))
        self.assertIn("\r\n", result)
        rows = list(csv.reader(io.StringIO(result.removeprefix("\ufeff"))))
        self.assertEqual([labels["kind"], labels["item"], labels["amount"]], rows[0])
        self.assertEqual({"'=1+1", "'+SUM(A1)", "'\u200f@cmd", 'Comma, "quote"'}, {row[1] for row in rows[1:5]})
        self.assertEqual({labels["income"], labels["expense"]}, {row[0] for row in rows[1:5]})
        self.assertEqual([labels["project"], "'=HYPERLINK()", ""], rows[5])
        self.assertEqual([labels["hours"], "", "2"], rows[6])
        self.assertEqual([labels["profit"], "", "-15.54"], rows[9])
        self.assertEqual([labels["margin"], "", "-155.2%"], rows[10])
        self.assertEqual([labels["hourly_net"], "", "-7.77"], rows[11])
        with self.assertRaises(AssertionError):
            self.profit_node(self.CSV, {"input": data, "labels": self.copy["ja"]})

    def test_battery_table_driven_ranges_never_collapse_to_one_number(self):
        cases = [
            ({"name": "Two years", "purchase_month": "2024-09", "max_capacity_pct": "88", "cycle_count": "412"},
             24, 0.38, 0.63, 12, 22, 17.2, "estimated"),
            ({"name": "New", "purchase_month": "2026-08", "max_capacity_pct": "100", "cycle_count": ""},
             1, 0.0, 0.0, None, None, None, "no_wear_yet"),
            ({"name": "Old", "purchase_month": "2021-03", "max_capacity_pct": "79", "cycle_count": ""},
             66, 0.24, 0.4, 0, 0, None, "at_or_below_80"),
            ({"name": "Exactly 80", "purchase_month": "2025-09", "max_capacity_pct": "80", "cycle_count": "0"},
             12, 1.25, 2.08, 0, 0, 0.0, "at_or_below_80"),
            ({"name": "One month", "purchase_month": "2026-08", "max_capacity_pct": "99", "cycle_count": "30"},
             1, 0.75, 1.25, 15, 26, 30.0, "estimated"),
            ({"name": "Nineteen years", "purchase_month": "2007-09", "max_capacity_pct": "60", "cycle_count": "3000"},
             228, 0.13, 0.22, 0, 0, 13.2, "at_or_below_80"),
        ]
        output = self.battery_node(self.RUN, [{"today": "2026-09", "items": [case[0] for case in cases]}])[0]
        self.assertEqual((0.25, 80, "2026-09"), (output["band"], output["target_capacity"], output["today"]))
        for case, item in zip(cases, output["items"], strict=True):
            with self.subTest(name=case[0]["name"]):
                self.assertEqual(case[1:], (
                    item["age_months"], item["wear_low"], item["wear_high"], item["months_to_80_low"],
                    item["months_to_80_high"], item["cycles_per_month"], item["status"],
                ))
                if item["status"] == "estimated":
                    self.assertLess(item["wear_low"], item["wear_high"])
                    self.assertLess(item["months_to_80_low"], item["months_to_80_high"])
                self.assertNotIn("score", json.dumps(item))
        self.assertEqual(
            {"devices": 6, "min_capacity_pct": 60, "soonest_status": "at_or_below_80", "soonest_low": 12, "soonest_high": 22},
            output["summary"],
        )
        estimated_only = self.battery_node(self.RUN, [{"today": "2026-09", "items": [cases[0][0], cases[4][0]]}])[0]
        self.assertEqual(("estimated", 12, 22, 88), (
            estimated_only["summary"]["soonest_status"], estimated_only["summary"]["soonest_low"],
            estimated_only["summary"]["soonest_high"], estimated_only["summary"]["min_capacity_pct"],
        ))
        fresh_only = self.battery_node(self.RUN, [{"today": "2026-09", "items": [cases[1][0]]}])[0]
        self.assertEqual(("no_wear_yet", None, None), (
            fresh_only["summary"]["soonest_status"], fresh_only["summary"]["soonest_low"], fresh_only["summary"]["soonest_high"],
        ))
        copy_en = hero.task_copy(self.copy, self.task_copies, self.tasks[3], "en-US")
        self.assertEqual(copy_en["at_or_below_80"], hero.battery_summary_text(copy_en, output["summary"]))
        self.assertEqual("12–22", hero.battery_summary_text(copy_en, estimated_only["summary"]))
        self.assertEqual(copy_en["no_wear_yet"], hero.battery_summary_text(copy_en, fresh_only["summary"]))
        self.assertEqual("12–22", hero.battery_months(copy_en, output["items"][0]))
        self.assertEqual(copy_en["no_wear_yet"], hero.battery_months(copy_en, output["items"][1]))
        self.assertEqual(copy_en["at_or_below_80"], hero.battery_months(copy_en, output["items"][2]))

    def test_battery_invalid_inputs_and_unknown_adapter_fail_closed(self):
        valid = {"today": "2026-09",
                 "items": [{"name": "A", "purchase_month": "2024-09", "max_capacity_pct": "88", "cycle_count": "412"}]}
        invalid = []
        for value in ["2026-9", "2026/09", "2026-13", "2026-09-05", "2006-12", "2100-01", "", None, 202609]:
            invalid.append({**valid, "today": value})
        for field, values in (
            ("purchase_month", ["2026-09", "2026-10", "2006-08", "1999-01", "2024-9", "", None]),
            ("max_capacity_pct", ["59", "101", "88.5", "", " 88", "-1", 88, None]),
            ("cycle_count", ["-1", "3001", "12.5", " 12", 412, None]),
            ("name", ["", " ", "line\nbreak", "\x00", "a" * 121]),
        ):
            for value in values:
                item = copy.deepcopy(valid)
                item["items"][0][field] = value
                invalid.append(item)
        invalid += [
            {**valid, "items": []},
            {**valid, "items": valid["items"] * 11},
            {**valid, "serial_number": "not accepted"},
            {**valid, "items": [{**valid["items"][0], "health_score": "not accepted"}]},
            {"today": "2026-09", "items": [{"name": "Old", "purchase_month": "2006-08", "max_capacity_pct": "70", "cycle_count": ""}]},
        ]
        errors = self.battery_node(self.FAIL_CLOSED, invalid)
        self.assertEqual([True] * (len(invalid) + 1), errors)

    def test_battery_csv_marks_every_estimate_and_is_formula_safe(self):
        labels = hero.task_copy(self.copy, self.task_copies, self.tasks[3], "de-DE")
        data = {"today": "2026-09", "items": [
            {"name": "=1+1", "purchase_month": "2024-09", "max_capacity_pct": "88", "cycle_count": "412"},
            {"name": "+SUM(A1)", "purchase_month": "2026-08", "max_capacity_pct": "100", "cycle_count": ""},
            {"name": "\u200f-cmd", "purchase_month": "2021-03", "max_capacity_pct": "79", "cycle_count": ""},
            {"name": 'Komma, "Zitat"', "purchase_month": "2025-09", "max_capacity_pct": "90", "cycle_count": "0"},
        ]}
        result = self.battery_node(self.CSV, {"input": data, "labels": labels})
        self.assertTrue(result.startswith("\ufeff"))
        self.assertIn("\r\n", result)
        rows = list(csv.reader(io.StringIO(result.removeprefix("\ufeff"))))
        self.assertEqual(10, len(rows[0]))
        self.assertEqual(labels["source_marker"], rows[0][9])
        self.assertEqual({"'=1+1", "'+SUM(A1)", "'\u200f-cmd", 'Komma, "Zitat"'}, {row[0] for row in rows[1:5]})
        self.assertEqual(["0.38", "0.63", "12", "22"], rows[1][5:9])
        self.assertEqual([labels["no_wear_yet"]] * 2, rows[2][7:9])
        self.assertEqual([labels["at_or_below_80"]] * 2, rows[3][7:9])
        for row in rows[1:5]:
            self.assertIn(labels["marker_provided"], row[9])
            self.assertIn(labels["marker_estimated"], row[9])
            self.assertNotIn("score", row[9].lower())
        self.assertIn(labels["cycles"], rows[1][9])
        self.assertNotIn(labels["cycles"], rows[2][9])
        self.assertEqual([labels["today"], "2026-09"] + [""] * 8, rows[5])
        with self.assertRaises(AssertionError):
            self.battery_node(self.CSV, {"input": data, "labels": self.copy["de-DE"]})

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
        self.assertEqual((200, 5, 1), (report["pages"], report["supported_apps"], report["unserved_apps"]))
        manifest = json.loads((self.pages / hero.MANIFEST).read_text())
        self.assertEqual(200, len({row["url"] for row in manifest["records"]}))
        self.assertEqual(250, manifest["app_locale_pairs"])
        self.assertEqual(["unserved"], manifest["unserved_app_keys"])
        maintenance, profit, battery = self.tasks[1], self.tasks[2], self.tasks[3]
        for record in manifest["records"]:
            locale = record["locale"]
            with self.subTest(locale=locale, task=record["task_id"]):
                document = (self.pages / record["path"]).read_text()
                self.assertIn(f'lang="{locale}"', document)
                self.assertIn(f'href="{record["url"]}"', document)
                self.assertEqual(51, document.count('hreflang="'))
                self.assertIn("connect-src 'none'", document)
                self.assertIn('data-field="name"', document)
                self.assertNotIn("noindex", document)
                feed = json.loads((self.pages / hero.feed_path(locale)).read_text())
                self.assertEqual(locale, feed["language"])
                self.assertIn("pt=118326163&ct=geo_learn&mt=8", json.dumps(feed))
                if record["task_id"] == "purchase-worktime":
                    self.assertIn(self.copy[locale]["formula"], document)
                    self.assertIn("300.00", document)
                    self.assertIn("15.00", document)
                    self.assertIn("1.88", document)
                    self.assertEqual(2, document.count("&amp;ct=geo_learn&amp;mt=8"))
                    example = (self.pages / hero.example_path(self.tasks[0], locale)).read_text()
                    self.assertIn(self.copy[locale]["item"], example)
                    self.assertEqual(record["url"], feed["items"][0]["id"])
                    self.assertEqual(2, len(feed["items"][0]["_hero_task"]["optional_apps"]))
                elif record["task_id"] == "project-profit":
                    own = hero.task_copy(self.copy, self.task_copies, profit, locale)
                    self.assertIn(own["formula"], document)
                    self.assertNotIn(self.copy[locale]["formula"], document)
                    for value in ("1500.00", "400.39", "1099.61", "73.3%", "87.97"):
                        self.assertIn(value, document)
                    self.assertIn('id="profit-rows"', document)
                    self.assertEqual(1, document.count("&amp;ct=geo_learn&amp;mt=8"))
                    self.assertIn("id6801956402", document)
                    example = (self.pages / hero.example_path(profit, locale)).read_text()
                    self.assertIn(own["profit"], example)
                    self.assertIn("1099.61", example)
                    self.assertEqual(record["url"], feed["items"][2]["id"])
                    self.assertEqual(own["title"], feed["items"][2]["title"])
                    self.assertEqual(1, len(feed["items"][2]["_hero_task"]["optional_apps"]))
                elif record["task_id"] == "battery-wear":
                    own = hero.task_copy(self.copy, self.task_copies, battery, locale)
                    self.assertIn(own["formula"], document)
                    self.assertNotIn(self.copy[locale]["formula"], document)
                    for value in ("0.38", "0.63", "12", "22", "17.2", own["no_wear_yet"], own["at_or_below_80"],
                                  own["marker_provided"], own["marker_estimated"]):
                        self.assertIn(value, document)
                    self.assertIn('id="today-month"', document)
                    self.assertIn('id="soonest-80" dir="ltr">' + own["at_or_below_80"], document)
                    self.assertIn('id="lowest-capacity">79<', document)
                    self.assertIn('id="device-count">3<', document)
                    self.assertEqual(1, document.count("&amp;ct=geo_learn&amp;mt=8"))
                    self.assertIn("id6802423998", document)
                    example = (self.pages / hero.example_path(battery, locale)).read_text()
                    self.assertIn(own["marker_provided"], example)
                    self.assertIn(own["marker_estimated"], example)
                    self.assertIn("0.38", example)
                    self.assertIn(own["at_or_below_80"], example)
                    if locale == "en-US":
                        self.assertNotIn("score", example.lower())
                    self.assertEqual(record["url"], feed["items"][3]["id"])
                    self.assertEqual(own["title"], feed["items"][3]["title"])
                    self.assertEqual(1, len(feed["items"][3]["_hero_task"]["optional_apps"]))
                else:
                    self.assertEqual("maintenance-next-due", record["task_id"])
                    own = hero.task_copy(self.copy, self.task_copies, maintenance, locale)
                    self.assertIn(own["formula"], document)
                    self.assertNotIn(self.copy[locale]["formula"], document)
                    self.assertIn("2026-09-01", document)
                    self.assertIn("2026-11-30", document)
                    self.assertIn('id="today-date"', document)
                    self.assertEqual(1, document.count("&amp;ct=geo_learn&amp;mt=8"))
                    self.assertIn("id6790800323", document)
                    example = (self.pages / hero.example_path(maintenance, locale)).read_text()
                    self.assertIn(own["status_overdue"], example)
                    self.assertIn("-4", example)
                    self.assertEqual(record["url"], feed["items"][1]["id"])
                    self.assertEqual(own["title"], feed["items"][1]["title"])
                    self.assertEqual(1, len(feed["items"][1]["_hero_task"]["optional_apps"]))
        sitemap = ET.parse(self.pages / hero.SITEMAP)
        self.assertEqual(200, len(sitemap.getroot()))
        index = (self.pages / "sitemap_index.xml").read_text()
        self.assertEqual(1, index.count(hero.SITEMAP))
        self.assertEqual(4, len(hero.english_feed_entries(self.pages)))
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
        self.assertEqual(465, result["verified_artifacts"])
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
            capture_output=True, text=True,
            timeout=int(os.environ.get("HERO_BROWSER_TIMEOUT", "360")), check=False,
            env={**os.environ, "TMPDIR": str(self.folder)},
        )
        self.assertEqual(0, process.returncode, process.stdout + process.stderr)
        self.assertIn('"locales":50', process.stdout)
        self.assertIn('"records":200', process.stdout)
        self.assertIn('"downloads":4', process.stdout)


if __name__ == "__main__":
    unittest.main()
