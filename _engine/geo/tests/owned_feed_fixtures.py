"""Offline, exact-roster fixtures; all scratch data stays under this checkout."""
from __future__ import annotations

from email.message import Message
import json
import os
from pathlib import Path
import re
import shutil
import sys
import unittest
from unittest.mock import patch
import uuid

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))
sys.path.insert(0, str(GEO.parent / "social"))

import build_pages_i18n
import deployment_generation
from app_store_storefronts import LOCALE_STOREFRONTS
from live_app_manifest import canonical_manifest
import market_availability as market
from official_locales import OFFICIAL_LOCALES
import owned_app_feeds as feeds
from videogen.registry import APPS

OLD = "2026-09-01T00:00:00Z"
NEW = "2026-09-02T00:00:00Z"
SOURCE = "a" * 40


def write_json(path: Path, document) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(feeds.json_bytes(document))


def reseal_catalog(pages: Path) -> None:
    catalogs = {
        locale: feeds.read_json(pages / feeds.CATALOG / "locales" / f"{locale}.json")
        for locale in OFFICIAL_LOCALES
    }
    content = feeds.digest({
        "api_version": "1.2.0",
        "localized": {locale: doc["apps"] for locale, doc in catalogs.items()},
    })
    write_json(pages / feeds.CATALOG / "index.json", {
        "api_version": "1.2.0", "locale_count": 50, "record_count": 47,
        "content_digest": content, "date_modified": OLD[:10],
    })
    copies = feeds.load_copy(GEO)
    for locale, catalog in catalogs.items():
        catalog["content_digest"] = content
        write_json(pages / feeds.CATALOG / "locales" / f"{locale}.json", catalog)
        write_json(pages / feeds.CATALOG / "feeds" / f"{locale}.json", {
            "language": locale, "title": copies[locale]["disclosure"],
            "_lumi_catalog": {"contentDigest": content},
        })


def make_catalog(pages: Path) -> None:
    roster = canonical_manifest()
    for locale in OFFICIAL_LOCALES:
        apps = []
        for key, app in roster["apps"].items():
            values = build_pages_i18n.external_localized_values(key, locale)
            summary = next(
                (" ".join(p.split()) for p in re.split(r"\n\s*\n", values["description"])
                 if len(" ".join(p.split())) >= 20), "",
            )
            direct = None if market.is_unavailable(locale, app["app_id"]) else (
                f"https://apps.apple.com/{LOCALE_STOREFRONTS[locale]}/app/id{app['app_id']}"
                "?pt=118326163&ct=owned_test&mt=8"
            )
            apps.append({
                "key": key, "app_store_id": app["app_id"],
                "name": build_pages_i18n._single_line(values["name"]), "summary": summary,
                "purchase_model": APPS[key]["purchase_model"], "one_time_option": True,
                "app_store_url": direct, "verified_live": True,
                "guide_url": feeds.url(f"{locale}/{key}.html"),
                **market.record_fields(locale, app["app_id"]),
            })
        write_json(pages / feeds.CATALOG / "locales" / f"{locale}.json", {
            "locale": locale, "record_count": 47, "apps": apps,
        })
        (pages / locale).mkdir(parents=True, exist_ok=True)
        (pages / locale / "index.html").write_text(
            f'<!doctype html><html lang="{locale}"><head>\n'
            '<title>Fixture</title></head><body>Fixture</body></html>\n', encoding="utf-8"
        )
    (pages / "sitemap_index.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<sitemapindex xmlns="{feeds.SITEMAP_NS}">'
        f'<sitemap><loc>{feeds.SITE}/sitemap_answers.xml</loc>'
        '<lastmod>2026-08-01</lastmod></sitemap></sitemapindex>\n', encoding="utf-8"
    )
    reseal_catalog(pages)


def make_deployment(pages: Path, source: str = SOURCE, run: str = "1") -> None:
    generation = {
        name: "b" * 64 for name in deployment_generation.LEGACY_GENERATION_FIELDS
    }
    generation.update({
        "schema_version": 1, "scope": "high_intent_route_closure",
        "source_sha": "c" * 40, "source_tree": "d" * 40,
        "pages_source_sha": source, "pages_source_tree": "e" * 40,
        "run_id": run, "run_attempt": "1",
    })
    generation["generation_id"] = deployment_generation.digest({
        k: v for k, v in generation.items() if k != "generation_id"
    })
    document = {
        "source_commit": source, "engine_source_revision": generation["source_sha"],
        "route_manifest_digest": generation["manifest_digest"], "generation": generation,
    }
    deployment_generation.validate_binding(document)
    write_json(pages / ".well-known/deployment.json", document)


class Response:
    def __init__(self, raw: bytes, content_type: str = "application/json; charset=utf-8"):
        self.raw, self.status = raw, 200
        self.headers = Message()
        self.headers["Content-Type"] = content_type

    def read(self, limit=-1):
        return self.raw if limit < 0 else self.raw[:limit]

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FeedFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = GEO / ".owned-feed-test-work" / uuid.uuid4().hex
        cls.seed = cls.workspace / "seed"
        cls.seed.mkdir(parents=True)
        cls.network = patch("urllib.request.urlopen", side_effect=AssertionError("Real network is forbidden"))
        cls.network.start()
        try:
            make_catalog(cls.seed)
            feeds.build(cls.seed, now=OLD)
            make_deployment(cls.seed)
        except BaseException:
            cls.network.stop()
            shutil.rmtree(cls.workspace)
            raise

    @classmethod
    def tearDownClass(cls):
        cls.network.stop()
        shutil.rmtree(cls.workspace)
        parent = cls.workspace.parent
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()

    def setUp(self):
        self.root = self.workspace / uuid.uuid4().hex
        self.pages = self.root / "site"
        shutil.copytree(self.seed, self.pages)
        self.state = self.root / "state.json"

    def tearDown(self):
        shutil.rmtree(self.root)

    def catalog_app(self, locale="en-US", key="lumimathpro"):
        path = self.pages / feeds.CATALOG / "locales" / f"{locale}.json"
        doc = feeds.read_json(path)
        return path, doc, next(a for a in doc["apps"] if a["key"] == key)

    def opener(self, request, timeout=0):
        from owned_feed_delivery import local_path
        if request.data is not None or request.get_method() != "GET":
            raise AssertionError("Real notifications are forbidden")
        path = local_path(self.pages, request.full_url)
        content_type = "application/json" if path.suffix == ".json" else "application/xml"
        return Response(path.read_bytes(), content_type + "; charset=utf-8")

    def fingerprints(self):
        return {
            str(p.relative_to(self.pages)): (feeds.sha256(p.read_bytes()), p.stat().st_mtime_ns)
            for p in self.pages.rglob("*") if p.is_file()
        }
