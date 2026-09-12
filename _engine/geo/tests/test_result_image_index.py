#!/usr/bin/env python3
"""Real-image evidence regression tests; mocked bytes never enter production data."""

from __future__ import annotations

import copy
from datetime import date, datetime, timedelta, timezone
from email.message import Message
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch
import uuid
import xml.etree.ElementTree as ET

from PIL import Image

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))

import result_image_index as images
import deployment_generation
import gen_sitemap_lastmod
import indexnow_submit


class ResultImagesTests(unittest.TestCase):
    def setUp(self):
        self.production = json.loads(images.MANIFEST.read_text())
        self.manifest = copy.deepcopy(self.production)
        self.root = GEO / "tests/.result-image-runs" / uuid.uuid4().hex
        self.root.mkdir(parents=True)
        self.addCleanup(shutil.rmtree, self.root)
        (self.root / "index.html").write_text(
            '<!doctype html><html lang="en-US"><head></head>'
            '<body><main>Existing app guide</main></body></html>\n'
        )
        (self.root / "robots.txt").write_text("User-agent: *\nAllow: /\n")
        (self.root / "sitemap.xml").write_text(
            f'<urlset xmlns="{images.SITEMAP_NS}"><url>'
            f'<loc>{images.PUBLIC_SITE}/</loc></url></urlset>\n'
        )
        (self.root / "sitemap_index.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<sitemapindex xmlns="{images.SITEMAP_NS}">\n'
            f'<sitemap><loc>{images.PUBLIC_SITE}/sitemap.xml</loc></sitemap>\n'
            '</sitemapindex>\n'
        )
        self.responses = {}
        self.requests = []
        self.today = date.today().isoformat()
        for number, asset in enumerate(self.manifest["images"]):
            stream = io.BytesIO()
            Image.new("RGB", (asset["width"], asset["height"]),
                      (30 + number * 50, 90, 150)).save(stream, format="JPEG")
            body = stream.getvalue()
            asset["sha256"] = images.digest(body)
            asset["evidence"]["source_sha256"] = asset["sha256"]
            asset["decoded_evidence"] = images.pixel_evidence(body)
            asset.pop("transport_reversal", None)
            self.responses[asset["canonical_asset_url"]] = images.Response(
                200, asset["canonical_asset_url"], {"content-type": "image/jpeg"}, body
            )
        self.verifier = images.PublicVerifier(self.transport)

    def transport(self, url, limit):
        self.requests.append((url, limit))
        if url in self.responses:
            return self.responses[url]
        if url.endswith("/robots.txt"):
            return images.Response(200, url, {"content-type": "text/plain"},
                                   b"User-agent: *\nAllow: /\n")
        raise AssertionError(f"Unexpected network request: {url}")

    def generate(self, **kwargs):
        return images.generate(self.root, self.manifest, verifier=self.verifier,
                               today=self.today, **kwargs)

    def rewrite_response(self, asset=None, **kwargs):
        asset = asset or self.manifest["images"][0]
        old = self.responses[asset["canonical_asset_url"]]
        self.responses[asset["canonical_asset_url"]] = images.Response(
            kwargs.get("status", old.status), kwargs.get("url", old.url),
            kwargs.get("headers", old.headers), kwargs.get("body", old.body),
        )

    def test_production_manifest_has_real_pinned_bytes_not_test_fixtures(self):
        images.validate_manifest(self.production)
        self.assertEqual(
            {
                "488476e5b43f72ec9c9742982aa6cc25b96065e174af7df2f1ada56686d6c7d7",
                "392778ef7c930ba55e2130667ca5aec941fce4bb5ab9d8553cee22a61d16b9c5",
            },
            {a["sha256"] for a in self.production["images"]},
        )
        self.assertTrue(all(
            "mzstatic.com/image/" in a["canonical_asset_url"]
            for a in self.production["images"]
        ))
        self.assertFalse(
            {a["sha256"] for a in self.production["images"]}
            & {a["sha256"] for a in self.manifest["images"]}
        )

    def test_exact50_coverage_is_honest_not_english_fallback(self):
        result = self.generate()
        self.assertEqual(2, result["indexable_unique_images"])
        self.assertEqual(1, result["indexable_pages"])
        self.assertEqual(1200, result["expected_app_locales"])
        self.assertEqual(2, result["verified_app_locales"])
        self.assertEqual(1198, result["blocked_app_locales"])
        self.assertEqual(8, result["blocked_candidate_images"])
        report = json.loads((self.root / images.COVERAGE).read_text())
        for app in self.manifest["apps"]:
            rows = [r for r in report["coverage"] if r["app_key"] == app["key"]]
            self.assertEqual(set(images.OFFICIAL_LOCALES), {r["locale"] for r in rows})
            self.assertEqual(50, len(rows))
        for locale in images.OFFICIAL_LOCALES:
            if locale != "en-US":
                self.assertFalse((self.root / images.gallery_path(locale)).exists())
                self.assertTrue(all(
                    row["status"] == images.BLOCKED
                    for row in report["coverage"] if row["locale"] == locale
                ))
        self.assertEqual("ELIGIBLE_IS_NOT_INDEXED", result["indexing_state"])

    def test_release_mode_rejects_approved_pixel_or_byte_drift_before_writes(self):
        before = (self.root / "index.html").read_bytes()
        self.rewrite_response(body=b"not the approved source")
        with self.assertRaisesRegex(ValueError, "blocks publication"):
            self.generate(require_approved=True)
        self.assertEqual(before, (self.root / "index.html").read_bytes())
        self.assertFalse((self.root / images.COVERAGE).exists())

    def test_real_img_src_caption_dimensions_and_canonical(self):
        self.generate()
        source = (self.root / images.gallery_path("en-US")).read_text()
        images.validate_gallery(source, "en-US", self.manifest["images"], images.PUBLIC_SITE)
        self.assertNotIn("application/ld+json", source)
        self.assertNotIn("background-image", source)
        self.assertIn("not customer testimonials", source)
        self.assertIn("does not prove an editable PPTX", source)
        self.assertNotIn("PENDING_COPY_DIGEST", source)
        for asset in self.manifest["images"]:
            self.assertIn(asset["canonical_asset_url"], source)
            self.assertIn('width="295" height="640"', source)

    def test_sitemap_only_lists_verified_existing_images_and_native_page(self):
        self.generate()
        root = ET.fromstring((self.root / images.SITEMAP).read_text())
        self.assertEqual(f"{{{images.SITEMAP_NS}}}urlset", root.tag)
        ns = {"s": images.SITEMAP_NS, "i": images.IMAGE_NS}
        self.assertEqual(
            [images.gallery_url("en-US", images.PUBLIC_SITE)],
            [node.text for node in root.findall("s:url/s:loc", ns)],
        )
        self.assertEqual(
            {a["canonical_asset_url"] for a in self.manifest["images"]},
            {node.text for node in root.findall("s:url/i:image/i:loc", ns)},
        )
        self.assertEqual(self.today, root.findtext("s:url/s:lastmod", namespaces=ns))
        self.assertFalse(root.findall(".//i:caption", ns))
        self.assertFalse(root.findall(".//i:title", ns))

    def test_idempotence_keeps_lastmod_and_file_mtime(self):
        self.today = (date.today() - timedelta(days=1)).isoformat()
        first = self.generate()
        paths = {relative: (self.root / relative).stat().st_mtime_ns
                 for relative in first["changed_files"]}
        previous = (self.root / images.COVERAGE).read_bytes()
        self.today = date.today().isoformat()
        second = self.generate(check=True)
        self.assertEqual([], second["changed_files"])
        self.assertEqual([], second["changed_pages"])
        self.assertEqual(previous, (self.root / images.COVERAGE).read_bytes())
        self.assertEqual(paths, {p: (self.root / p).stat().st_mtime_ns for p in paths})

    def test_real_copy_change_updates_only_affected_content_lastmod(self):
        self.today = (date.today() - timedelta(days=1)).isoformat()
        self.generate()
        self.today = date.today().isoformat()
        copy = self.manifest["images"][0]["localizations"]["en-US"]
        copy["caption"] += " The page is already filled."
        copy["native_review"]["copy_sha256"] = images.copy_digest(copy)
        result = self.generate()
        self.assertEqual([images.gallery_url("en-US", images.PUBLIC_SITE)], result["changed_pages"])
        report = json.loads((self.root / images.COVERAGE).read_text())
        self.assertEqual(self.today, report["pages"][images.gallery_path("en-US")]["lastmod"])
        self.assertNotIn("index.html", result["changed_files"])

    def test_missing_or_extra_official_locale_is_not_50_coverage(self):
        for locales in (list(images.OFFICIAL_LOCALES)[:-1],
                        list(images.OFFICIAL_LOCALES) + ["en"]):
            with self.subTest(locales=len(locales)):
                self.manifest["expected_locales"] = locales
                with self.assertRaisesRegex(ValueError, "exact official 50"):
                    self.generate()

    def test_cross_locale_text_image_reuse_is_blocked_even_for_english_regions(self):
        for locale in ("en-GB", "fr-FR"):
            with self.subTest(locale=locale):
                doc = copy.deepcopy(self.manifest)
                doc["labels"][locale] = copy.deepcopy(doc["labels"]["en-US"])
                doc["labels"][locale]["native_review"]["locale"] = locale
                asset = doc["images"][0]
                asset["localizations"][locale] = copy.deepcopy(asset["localizations"]["en-US"])
                asset["localizations"][locale]["native_review"]["locale"] = locale
                with self.assertRaisesRegex(ValueError, "Text-bearing"):
                    images.validate_manifest(doc)

    def test_textless_reuse_still_rejects_shared_english_caption(self):
        asset = self.manifest["images"][0]
        asset["contains_text"] = False
        asset["evidence"]["textless_review_ref"] = "test-only affirmative textless check"
        self.manifest["labels"]["fr-FR"] = copy.deepcopy(self.manifest["labels"]["en-US"])
        self.manifest["labels"]["fr-FR"]["native_review"]["locale"] = "fr-FR"
        asset["localizations"]["fr-FR"] = copy.deepcopy(asset["localizations"]["en-US"])
        asset["localizations"]["fr-FR"]["native_review"]["locale"] = "fr-FR"
        with self.assertRaisesRegex(ValueError, "Shared cross-locale copy"):
            images.validate_manifest(self.manifest)

    def test_missing_or_stale_native_review_is_blocked(self):
        copy = self.manifest["images"][0]["localizations"]["en-US"]
        copy["alt"] += " Changed after review."
        with self.assertRaisesRegex(ValueError, "missing or stale"):
            self.generate()

    def test_textless_image_can_reuse_one_canonical_url_with_reviewed_native_copy(self):
        labels = {
            "title": "Exemples publiés de notes et de diapositives",
            "intro": "Ces exemples sont publiés par l'éditeur, sans témoignage client ni résultat de test indépendant.",
            "source_label": "Source publiée sur l’App Store",
            "store_label": "Voir l’application sur l’App Store",
            "unavailable": "Aucune image publique vérifiée n’est disponible.",
            "home_label": "Retour au guide des applications",
        }
        labels["native_review"] = {
            "locale": "fr-FR", "copy_sha256": images.copy_digest(labels, images.LABEL_FIELDS),
            "review_ref": "test-only French copy review",
        }
        self.manifest["labels"]["fr-FR"] = labels
        asset = self.manifest["images"][0]
        asset["contains_text"] = False
        asset["evidence"]["textless_review_ref"] = "test-only solid JPEG has no text"
        translated = {
            "alt": "Une surface bleue unie sans inscription.",
            "caption": "Cette image ne contient aucun texte.",
            "nearby_text": "La même image sans texte est accompagnée d’une description française.",
            "limitation": "Ce contrôle porte sur la réutilisation de l’image, pas sur le fonctionnement d’une application.",
        }
        translated["native_review"] = {
            "locale": "fr-FR", "copy_sha256": images.copy_digest(translated),
            "review_ref": "test-only French image review",
        }
        asset["localizations"]["fr-FR"] = translated
        result = self.generate()
        self.assertEqual(2, result["indexable_unique_images"])
        self.assertEqual(2, result["indexable_pages"])
        self.assertEqual(3, result["verified_app_locales"])
        french = (self.root / images.gallery_path("fr-FR")).read_text()
        self.assertIn(translated["alt"], french)
        self.assertIn(asset["canonical_asset_url"], french)
        self.assertNotIn(asset["localizations"]["en-US"]["alt"], french)

    def test_native_script_guard_rejects_english_fixtures(self):
        doc = copy.deepcopy(self.manifest)
        doc["labels"]["ja"] = copy.deepcopy(doc["labels"]["en-US"])
        doc["labels"]["ja"]["native_review"]["locale"] = "ja"
        with self.assertRaisesRegex(ValueError, "native script"):
            images.validate_manifest(doc)

    def test_ambiguous_textless_claim_needs_affirmative_evidence(self):
        self.manifest["images"][0]["contains_text"] = False
        with self.assertRaisesRegex(ValueError, "textless review"):
            self.generate()

    def test_missing_rights_or_real_result_proof_blocks_publication(self):
        for field in ("rights_status", "rights_basis", "result_status", "review_ref"):
            with self.subTest(field=field):
                doc = copy.deepcopy(self.manifest)
                doc["images"][0]["evidence"].pop(field)
                with self.assertRaisesRegex(ValueError, "proof is missing"):
                    images.validate_manifest(doc)

    def test_wrong_app_approval_cannot_authorize_another_app(self):
        self.manifest["images"][0]["evidence"]["app_store_url"] = "https://apps.apple.com/us/app/id6798814385"
        with self.assertRaisesRegex(ValueError, "exact app"):
            self.generate()

    def test_blocked_image_cannot_be_promoted_by_reusing_id(self):
        self.manifest["rejected_candidates"][0]["id"] = "notes-handwriting"
        with self.assertRaisesRegex(ValueError, "blocked image"):
            self.generate()

    def test_unproven_exports_cannot_be_promoted_without_result_evidence(self):
        self.manifest["unproven_claims"][-1]["status"] = "VERIFIED_EXPORT"
        with self.assertRaisesRegex(ValueError, "Unproven result claims"):
            self.generate()

    def test_duplicate_hash_alias_and_duplicate_record_are_rejected(self):
        for same_url in (True, False):
            with self.subTest(same_url=same_url):
                doc = copy.deepcopy(self.manifest)
                alias = copy.deepcopy(doc["images"][0])
                alias["id"] = "duplicate-notes"
                if not same_url:
                    alias["canonical_asset_url"] = alias["canonical_asset_url"].replace("02-handwriting", "copy")
                doc["images"].append(alias)
                with self.assertRaisesRegex(ValueError, "Duplicate bytes or canonical"):
                    images.validate_manifest(doc)

    def test_duplicate_app_identity_is_rejected(self):
        self.manifest["apps"][0]["app_id"] = self.manifest["apps"][1]["app_id"]
        with self.assertRaisesRegex(ValueError, "Duplicate app"):
            self.generate()

    def test_rating_data_cannot_be_smuggled_in_evidence(self):
        for field in images.FORBIDDEN_FIELDS:
            with self.subTest(field=field):
                doc = copy.deepcopy(self.manifest)
                doc["images"][0]["evidence"][field] = {"ratingValue": "5"}
                with self.assertRaisesRegex(ValueError, "reviews and rating"):
                    images.validate_manifest(doc)

    def test_nonpublic_urls_and_unstable_aliases_are_rejected(self):
        for url in (
            "file:///private/image.jpg", "http://127.0.0.1/image.jpg",
            "https://is1-ssl.mzstatic.com/image.jpg?locale=fr",
            "https://is1-ssl.mzstatic.com/image.jpg#caption",
            "https://is1-ssl.mzstatic.com/../image.jpg",
            "https://is1-ssl.mzstatic.com/%2e%2e/image.jpg",
            "https://example.com/image.jpg",
        ):
            with self.subTest(url=url):
                doc = copy.deepcopy(self.manifest)
                doc["images"][0]["canonical_asset_url"] = url
                with self.assertRaises(ValueError):
                    images.validate_manifest(doc)

    def test_http_failure_hash_drift_and_undecodable_assets_stay_blocked(self):
        cases = (
            {"status": 404}, {"status": 403}, {"status": 500},
            {"status": 302}, {"url": "https://example.com/redirect.jpg"},
            {"body": b"not the reviewed image"},
            {"headers": {"content-type": "text/html"}},
        )
        original = copy.copy(self.responses)
        for case in cases:
            with self.subTest(case=case):
                self.responses = copy.copy(original)
                self.rewrite_response(**case)
                result = self.generate()
                self.assertEqual(1, result["indexable_unique_images"])
                self.assertIn("notes-handwriting", result["public_check_failures"])
                source = (self.root / images.SITEMAP).read_text()
                self.assertNotIn(self.manifest["images"][0]["canonical_asset_url"], source)

    def test_matching_hash_is_not_a_decoder_pass(self):
        bad = b"This is HTML, not a JPEG."
        asset = self.manifest["images"][0]
        asset["sha256"] = images.digest(bad)
        asset["evidence"]["source_sha256"] = asset["sha256"]
        self.rewrite_response(body=bad)
        result = self.generate()
        self.assertIn("cannot be decoded", result["public_check_failures"]["notes-handwriting"])

    def test_wrong_dimensions_and_mime_are_not_eligible(self):
        self.manifest["images"][0]["width"] = 296
        self.manifest["images"][0]["decoded_evidence"]["width"] = 296
        result = self.generate()
        self.assertIn("dimensions", result["public_check_failures"]["notes-handwriting"])
        self.manifest["images"][0]["width"] = 295
        self.manifest["images"][0]["decoded_evidence"]["width"] = 295
        self.rewrite_response(headers={"content-type": "image/png"})
        result = self.generate()
        self.assertIn("MIME", result["public_check_failures"]["notes-handwriting"])

    def test_image_x_robots_noindex_and_noimageindex_are_respected(self):
        for header in ("noindex", "noimageindex", "none", "Googlebot-Image: noindex"):
            with self.subTest(header=header):
                self.rewrite_response(headers={"content-type": "image/jpeg", "x-robots-tag": header})
                self.assertEqual(1, self.generate()["indexable_unique_images"])

    def test_unrelated_bot_header_does_not_block_google_images(self):
        self.rewrite_response(headers={"content-type": "image/jpeg", "x-robots-tag": "otherbot: noindex"})
        self.assertEqual(2, self.generate()["indexable_unique_images"])

    def test_parameterized_robots_directives_do_not_change_bot_scope(self):
        for header in (
            "max-image-preview:large, noindex",
            "noindex, max-image-preview:large",
            "max-snippet:0, noimageindex",
            "max-video-preview:-1, none",
            "Googlebot: max-image-preview:large, noindex",
            "max-image-preview:large, max-snippet:0, noindex",
            "max-image-preview: large, noindex nofollow",
            "noimageindex nofollow",
        ):
            with self.subTest(header=header):
                self.rewrite_response(headers={"content-type": "image/jpeg", "x-robots-tag": header})
                self.assertEqual(1, self.generate()["indexable_unique_images"])
                self.assertTrue(images._header_blocks(header, "Googlebot-Image"))
        self.assertFalse(images._header_blocks(
            "otherbot: max-image-preview:large, noindex", "Googlebot-Image",
        ))
        self.assertFalse(images._header_blocks("index, max-image-preview:large", "Googlebot-Image"))
        self.assertFalse(images._header_blocks("max-image-preview: none", "Googlebot-Image"))

    def test_independent_header_fields_reset_the_bot_scope_in_either_order(self):
        for fields in (("otherbot: noindex", "noindex"), ("noindex", "otherbot: noindex")):
            with self.subTest(fields=fields):
                self.rewrite_response(headers={"content-type": "image/jpeg", "x-robots-tag": fields})
                result = self.generate()
                self.assertEqual(1, result["indexable_unique_images"])
                self.assertIn("X-Robots-Tag", result["public_check_failures"]["notes-handwriting"])

    def test_fetch_preserves_repeated_x_robots_header_boundaries(self):
        headers = Message()
        headers.add_header("Content-Type", "image/jpeg")
        headers.add_header("X-Robots-Tag", "otherbot: noindex")
        headers.add_header("X-Robots-Tag", "noindex")
        response = MagicMock()
        response.status = 200
        response.headers = headers
        response.geturl.return_value = self.manifest["images"][0]["canonical_asset_url"]
        response.read.return_value = b"image bytes"
        opener = MagicMock()
        opener.open.return_value = response
        with patch.object(images, "build_opener", return_value=opener):
            result = images.fetch(response.geturl.return_value, images.MAX_IMAGE_BYTES)
        self.assertEqual(("otherbot: noindex", "noindex"), result.headers["x-robots-tag"])
        self.assertTrue(images._header_blocks(result.headers["x-robots-tag"], "Googlebot-Image"))
        self.assertEqual("GET", opener.open.call_args.args[0].get_method())

    def test_authoritative_origin_robots_not_project_path_controls_crawling(self):
        url = "https://is1-ssl.mzstatic.com/robots.txt"
        self.responses[url] = images.Response(
            200, url, {}, b"User-agent: Googlebot-Image\nDisallow: /image/\n"
        )
        self.assertEqual(0, self.generate()["indexable_unique_images"])
        self.assertNotIn(f"{images.PUBLIC_SITE}/robots.txt", [url for url, _ in self.requests])

    def test_landing_origin_robots_can_block_all_images(self):
        url = "https://open.cait518.cc/robots.txt"
        self.responses[url] = images.Response(
            200, url, {}, b"User-agent: Googlebot\nDisallow: /ios-app-guide/en-US/results/\n"
        )
        self.assertEqual(0, self.generate()["indexable_unique_images"])

    def test_robots_429_5xx_and_timeout_are_not_an_allow(self):
        for status in (429, 500, 503):
            with self.subTest(status=status):
                verifier = images.PublicVerifier(
                    lambda url, limit: images.Response(status, url, {}, b"")
                )
                with self.assertRaisesRegex(ValueError, "robots is unavailable"):
                    verifier.crawlable(self.manifest["images"][0]["canonical_asset_url"], "Googlebot-Image")

    def test_google_treats_robots_4xx_except_429_as_absent(self):
        for status in (403, 404, 410):
            with self.subTest(status=status):
                verifier = images.PublicVerifier(
                    lambda url, limit: images.Response(status, url, {}, b"")
                )
                verifier.crawlable(self.manifest["images"][0]["canonical_asset_url"], "Googlebot-Image")

    def test_robots_specific_group_longest_match_wildcards_and_allow_ties(self):
        robots = (
            "User-agent: *\nDisallow: /\n\n"
            "User-agent: Googlebot-Image\nDisallow: /image/*\n"
            "Allow: /image/public/\nDisallow: /image/public/private.jpg$\n"
        )
        self.assertTrue(images.robots_allowed(robots, "https://a/image/public/good.jpg", "Googlebot-Image"))
        self.assertFalse(images.robots_allowed(robots, "https://a/image/public/private.jpg", "Googlebot-Image"))
        self.assertFalse(images.robots_allowed(robots, "https://a/image/other.jpg", "Googlebot-Image"))
        self.assertFalse(images.robots_allowed(robots, "https://a/image/public/good.jpg", "OtherBot"))
        self.assertTrue(images.robots_allowed(
            "User-agent: *\nDisallow: /same\nAllow: /same\n",
            "https://a/same", "Googlebot-Image",
        ))

    def test_canonical_robots_length_counts_wildcards_and_end_anchors(self):
        cases = (
            ("/x", "/x$", "/x", False),
            ("/x", "/x$", "/x?query=1", True),
            ("/page", "/*.htm", "/page.htm", False),
            ("/page*", "/page$", "/page", True),
            ("/public/a", "/public/", "/public/%61", True),
        )
        for allow, deny, path, expected in cases:
            with self.subTest(allow=allow, deny=deny, path=path):
                self.assertEqual(expected, images.robots_allowed(
                    f"User-agent: Googlebot-Image\nAllow: {allow}\nDisallow: {deny}\n",
                    "https://example.com" + path, "Googlebot-Image",
                ))

    def test_no_assets_means_empty_sitemap_and_noindex_previous_gallery(self):
        self.generate()
        for asset in self.manifest["images"]:
            self.rewrite_response(asset, status=404)
        result = self.generate()
        self.assertEqual(0, result["indexable_unique_images"])
        self.assertEqual(1200, result["blocked_app_locales"])
        root = ET.fromstring((self.root / images.SITEMAP).read_text())
        self.assertEqual([], list(root))
        source = (self.root / images.gallery_path("en-US")).read_text()
        self.assertIn('content="noindex,follow"', source)
        self.assertNotIn("<img ", source)
        self.assertNotIn("result-image-links:start", (self.root / "index.html").read_text())
        self.assertNotIn(images.SITEMAP, (self.root / "sitemap_index.xml").read_text())
        self.assertNotIn(images.SITEMAP, (self.root / "robots.txt").read_text())

    def test_removing_locale_and_copy_retires_previously_indexable_images(self):
        self.generate()
        self.manifest["images"] = []
        self.manifest["labels"] = {}
        result = self.generate()
        relative = images.gallery_path("en-US")
        source = (self.root / relative).read_text()
        self.assertNotIn("<img ", source)
        self.assertIn('content="noindex,follow"', source)
        self.assertIn(self.production["labels"]["en-US"]["unavailable"], source)
        self.assertIn(images.gallery_url("en-US", images.PUBLIC_SITE), result["changed_pages"])
        report = json.loads((self.root / images.COVERAGE).read_text())
        self.assertEqual({}, report["pages"])
        self.assertEqual({relative}, set(report["retired_pages"]))
        self.assertEqual([], self.generate(check=True)["changed_files"])
        url = images.gallery_url("en-US", images.PUBLIC_SITE)
        self.responses[url] = images.Response(
            200, url, {"content-type": "text/html", "x-robots-tag": "noindex"}, source.encode()
        )
        self.verifier.landing(url, source, indexable=False)

    def test_retirement_recreates_a_missing_local_page_for_verified_deindex_readback(self):
        self.generate()
        relative = images.gallery_path("en-US")
        (self.root / relative).unlink()
        self.manifest["images"] = []
        self.manifest["labels"] = {}
        result = self.generate()
        self.assertIn(relative, result["changed_files"])
        self.assertIn('content="noindex,follow"', (self.root / relative).read_text())

    def test_global_lastmod_and_image_lastmod_converge_after_withdrawal(self):
        def global_lastmod():
            gen_sitemap_lastmod.generate(
                self.root, site=images.PUBLIC_SITE,
                state_path=self.root / ".global-lastmod-state.json",
                today=self.today, history_dates={},
                dirty_paths={p.relative_to(self.root).as_posix() for p in self.root.rglob("*") if p.is_file()},
            )

        utc_today = datetime.now(timezone.utc).date()
        self.today = (utc_today - timedelta(days=1)).isoformat()
        self.generate()
        global_lastmod()
        self.assertEqual([], self.generate(check=True)["changed_files"])
        self.today = utc_today.isoformat()
        self.manifest["images"] = []
        self.manifest["labels"] = {}
        self.generate()
        report = json.loads((self.root / images.COVERAGE).read_text())
        self.assertEqual(self.today, report["sitemap"]["lastmod"])
        global_lastmod()
        self.assertEqual([], self.generate(check=True)["changed_files"])
        global_lastmod()
        self.assertEqual([], self.generate(check=True)["changed_files"])


    def test_missing_production_proof_never_uses_synthetic_preview(self):
        self.manifest["images"] = []
        result = self.generate()
        self.assertEqual(0, result["indexable_unique_images"])
        self.assertEqual(1200, result["blocked_app_locales"])
        self.assertFalse((self.root / images.gallery_path("en-US")).exists())
        self.assertFalse(self.requests)

    def test_discovery_is_idempotent_and_repairs_downstream_regeneration(self):
        self.generate()
        self.assertEqual(1, (self.root / "index.html").read_text().count("result-image-links:start"))
        self.assertEqual(1, (self.root / "robots.txt").read_text().count(f"Sitemap: {images.PUBLIC_SITE}/{images.SITEMAP}"))
        (self.root / "robots.txt").write_text("User-agent: *\nAllow: /\n")
        index = (self.root / "sitemap_index.xml").read_text()
        index = index.replace("<!-- result-image-sitemap:start -->\n", "").replace(
            "<!-- result-image-sitemap:end -->\n", "")
        (self.root / "sitemap_index.xml").write_text(index)
        self.generate()
        root = ET.fromstring((self.root / "sitemap_index.xml").read_text())
        locs = [node.text for node in root.iter(f"{{{images.SITEMAP_NS}}}loc")]
        self.assertEqual(1, locs.count(f"{images.PUBLIC_SITE}/{images.SITEMAP}"))
        self.assertIn(f"{images.PUBLIC_SITE}/sitemap.xml", locs)
        self.assertEqual([], self.generate(check=True)["changed_files"])

    def test_check_refuses_stale_html_instead_of_calling_it_a_pass(self):
        self.generate()
        path = self.root / images.gallery_path("en-US")
        path.write_text(path.read_text().replace("<img ", "<div "))
        with self.assertRaisesRegex(ValueError, "Stale result-image outputs"):
            self.generate(check=True)

    def test_css_background_cannot_replace_img_src(self):
        self.generate()
        source = (self.root / images.gallery_path("en-US")).read_text().replace("<img ", "<div ")
        with self.assertRaisesRegex(ValueError, "real img src"):
            images.validate_gallery(source, "en-US", self.manifest["images"], images.PUBLIC_SITE)

    def test_gallery_meta_noimageindex_is_blocking(self):
        self.generate()
        source = (self.root / images.gallery_path("en-US")).read_text()
        source = source.replace("index,follow,max-image-preview:large", "noimageindex")
        with self.assertRaisesRegex(ValueError, "robots prevents"):
            images.validate_gallery(source, "en-US", self.manifest["images"], images.PUBLIC_SITE)

    def test_google_get_has_no_redirect_following_or_asc_mutation(self):
        self.generate()
        self.assertTrue(all(
            url.startswith(("https://is1-ssl.mzstatic.com/", "https://open.cait518.cc/"))
            for url, _ in self.requests
        ))
        self.assertIsNone(images._NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.test"))

    def test_generator_outputs_do_not_mutate_conversion_or_owned_feed_sources(self):
        changed = self.generate()["changed_files"]
        self.assertEqual(
            {images.COVERAGE, images.SITEMAP, "sitemap_index.xml",
             "robots.txt", "index.html", images.gallery_path("en-US")},
            set(changed),
        )
        source = (GEO / "publish.py").read_text()
        last_mile = source.index('os.path.join(HERE, "result_image_index.py")')
        self.assertLess(source.rindex('os.path.join(HERE, "gen_llms.py")'), last_mile)
        self.assertLess(source.rindex('os.path.join(HERE, "gen_feed.py")'), last_mile)
        self.assertLess(last_mile, source.rindex('os.path.join(HERE, "gen_sitemap_lastmod.py")'))

    def test_publish_hook_has_a_current_source_generated_sync_contract(self):
        from high_intent_decision_routes import build_sync_contract, validate_sync_contract

        contract = validate_sync_contract(
            GEO / "data/high_intent_guide_sync_contract.json", engine_root=GEO,
        )
        self.assertEqual(build_sync_contract(GEO), contract)

    def test_live_readback_checks_exact_html_and_headers(self):
        self.generate()
        url = images.gallery_url("en-US", images.PUBLIC_SITE)
        content = (self.root / images.gallery_path("en-US")).read_text()
        self.responses[url] = images.Response(200, url, {"content-type": "text/html"}, content.encode())
        self.verifier.landing(url, content)
        self.responses[url] = images.Response(
            200, url, {"content-type": "text/html", "x-robots-tag": "noimageindex"}, content.encode()
        )
        with self.assertRaisesRegex(ValueError, "prevents image indexing"):
            self.verifier.landing(url, content)
        self.responses[url] = images.Response(200, url, {"content-type": "text/html"}, b"old deploy")
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.verifier.landing(url, content)

    def test_landing_accepts_only_the_existing_pinned_cdn_transform(self):
        self.generate()
        url = images.gallery_url("en-US", images.PUBLIC_SITE)
        source = (self.root / images.gallery_path("en-US")).read_text()
        beacon = deployment_generation.EDGE_BEACON
        body = source.encode().replace(b"</body>", beacon + b"\n</body>")
        self.responses[url] = images.Response(200, url, {"content-type": "text/html"}, body)
        check = self.verifier.landing(url, source)
        self.assertEqual(deployment_generation.EDGE_TRANSFORM, check["edge_transform"])
        self.assertEqual(images.digest(source.encode()), check["sha256"])
        self.assertEqual(images.digest(body), check["response_sha256"])
        for bad in (
            body.replace(b'"spa":2', b'"spa":3'),
            body.replace(b"</main>", b"</main><script>alert(1)</script>"),
            body.replace(b"Neurology", b"Changed"),
            body.replace(beacon, beacon + b"\n" + beacon),
        ):
            with self.subTest(sha=images.digest(bad)):
                self.responses[url] = images.Response(200, url, {"content-type": "text/html"}, bad)
                with self.assertRaisesRegex(ValueError, "does not match"):
                    self.verifier.landing(url, source)

    def test_landing_mime_and_foreign_host_cannot_pass_exact_byte_readback(self):
        self.generate()
        url = images.gallery_url("en-US", images.PUBLIC_SITE)
        source = (self.root / images.gallery_path("en-US")).read_text()
        self.responses[url] = images.Response(200, url, {"content-type": "text/plain"}, source.encode())
        with self.assertRaisesRegex(ValueError, "not served as HTML"):
            self.verifier.landing(url, source)
        with self.assertRaisesRegex(ValueError, "outside the approved"):
            self.verifier.landing("https://example.com/en-US/results/", source)

    def test_post_prune_readback_runtime_has_all_required_dependencies(self):
        runtime = self.root / "readback-runtime"
        (runtime / "data").mkdir(parents=True)
        for relative in (
            "result_image_index.py", "deployment_generation.py",
            "image_transport_evidence.py",
            "crawler_policy.py", "official_locales.py", "site_config.py",
            "data/result_image_evidence_v1.json",
        ):
            shutil.copyfile(GEO / relative, runtime / relative)
        result = subprocess.run(
            [
                sys.executable, "-c",
                "import json, result_image_index as m; "
                "m.validate_manifest(json.loads(m.MANIFEST.read_text())); "
                "assert m._header_blocks('max-image-preview:large, noindex', 'Googlebot-Image'); "
                "print('readback runtime ready')",
            ],
            cwd=runtime, check=True, capture_output=True, text=True,
        )
        self.assertEqual("readback runtime ready", result.stdout.strip())

    def test_output_symlink_is_not_followed(self):
        target = self.root / "external-marker"
        target.write_text("keep")
        output = self.root / images.COVERAGE
        output.parent.mkdir()
        output.symlink_to(target)
        with self.assertRaises((ValueError, json.JSONDecodeError)):
            self.generate()
        self.assertEqual("keep", target.read_text())

    def test_changed_page_list_never_contains_assets_or_sitemaps(self):
        result = self.generate()
        self.assertEqual(
            {f"{images.PUBLIC_SITE}/", images.gallery_url("en-US", images.PUBLIC_SITE)},
            set(result["changed_pages"]),
        )
        self.assertFalse(any(".xml" in url or "mzstatic" in url for url in result["changed_pages"]))
        self.assertEqual([], self.generate()["changed_pages"])

    def test_actual_gallery_alt_and_same_url_pixel_changes_survive_indexnow_gate(self):
        self.generate()
        relative = images.gallery_path("en-US")
        path = self.root / relative
        baseline = indexnow_submit.indexable_content_digest(path)
        copy = self.manifest["images"][0]["localizations"]["en-US"]
        copy["alt"] = "A handwritten neurology note with checked items and a small drawing."
        copy["native_review"]["copy_sha256"] = images.copy_digest(copy)
        result = self.generate()
        selected, _ = indexnow_submit.select_content_changed_urls(
            self.root, images.PUBLIC_SITE, result["changed_pages"], {relative: baseline},
        )
        self.assertEqual([images.gallery_url("en-US", images.PUBLIC_SITE)], selected)
        baseline = indexnow_submit.indexable_content_digest(path)
        stream = io.BytesIO()
        Image.new("RGB", (295, 640), (70, 90, 200)).save(stream, format="JPEG")
        body = stream.getvalue()
        self.manifest["images"][0]["sha256"] = images.digest(body)
        self.manifest["images"][0]["evidence"]["source_sha256"] = images.digest(body)
        self.rewrite_response(body=body)
        result = self.generate()
        selected, _ = indexnow_submit.select_content_changed_urls(
            self.root, images.PUBLIC_SITE, result["changed_pages"], {relative: baseline},
        )
        self.assertEqual([images.gallery_url("en-US", images.PUBLIC_SITE)], selected)


if __name__ == "__main__":
    unittest.main()
