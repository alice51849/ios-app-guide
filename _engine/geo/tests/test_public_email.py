"""Source renderers, full-site fail-closed coverage and independent edge counterexamples."""

from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))
import public_email as email
import build_pages_i18n as guides
import app_install_decision_routes as decisions
import deployment_generation as generation

PAGES = GEO.parents[1] if GEO.parent.name == "_engine" else GEO / "pages"
FOUR = (
    "en-US/savetag.html", "en-US/shotinbox.html", "en-US/zipbox.html",
    "apps/zipbox/decision/l/en-US/index.html",
)


def simulate_cloudflare(source):
    """Independent fixture: protected/source-excluded blocks bypass the email rewriter."""
    excluded = re.compile(
        r"(<!--email_off-->.*?<!--/email_off-->|"
        r"<(?:head|script|noscript|textarea|xmp)\b.*?</(?:head|script|noscript|textarea|xmp)>)",
        re.S | re.I,
    )
    result = []
    rewritten = False
    for section in excluded.split(source):
        if section.startswith("<!--email_off-->"):
            result.append(section[len("<!--email_off-->"):-len("<!--/email_off-->")])
        elif excluded.fullmatch(section):
            result.append(section)
        else:
            for token in re.split(r"(<[^>]*>)", section):
                if not token.startswith("<") or re.match(r"<a\b", token, re.I):
                    if email.PUBLIC_CONTACT in token:
                        rewritten = True
                        token = token.replace(email.PUBLIC_CONTACT, "[email protected]")
                result.append(token)
    body = "".join(result)
    return body.replace("</body>", '<script src="/cdn-cgi/email-decode.min.js"></script></body>') if rewritten else body


class Visible(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.text = []
        self.mailtos = []
        self.feed(source)

    def handle_data(self, value):
        self.text.append(value)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "a" and (values.get("href") or "").startswith("mailto:"):
            self.mailtos.append(values["href"])


class PublicEmailTests(unittest.TestCase):
    def test_text_and_mailto_are_preserved_without_javascript(self):
        source = '<body><p>Support: hourstag.app@gmail.com</p><a href="mailto:hourstag.app@gmail.com">hourstag.app@gmail.com</a></body>'
        rendered = email.render_html(source)
        self.assertEqual(source, email.canonical_html(rendered))
        self.assertEqual(Visible(source).text, Visible(rendered).text)
        self.assertEqual(Visible(source).mailtos, Visible(rendered).mailtos)
        self.assertEqual(source, simulate_cloudflare(rendered))
        self.assertNotEqual(source, simulate_cloudflare(source))
        self.assertEqual(rendered, email.render_html(rendered))

    def test_entity_encoded_visible_text_is_protected_not_hidden(self):
        source = '<body><p>hourstag.app&#64;gmail.com</p></body>'
        self.assertTrue(email.EmailMarkup(source).issues)
        rendered = email.render_html(source)
        self.assertFalse(email.EmailMarkup(rendered).issues)
        self.assertEqual(source, email.canonical_html(rendered))

    def test_head_json_and_non_link_attributes_are_not_rewritten(self):
        source = '<html><head><script type="application/ld+json">{"email":"hourstag.app@gmail.com"}</script></head><body><input placeholder="you@example.com"></body></html>'
        self.assertFalse(email.EmailMarkup(source).issues)
        self.assertEqual(source, email.render_html(source))

    def test_bad_or_empty_control_regions_fail_closed(self):
        for source in (
            '<body><!--email_off-->hourstag.app@gmail.com</body>',
            '<body><!--/email_off--></body>',
            '<body><!--email_off--><!--email_off-->hourstag.app@gmail.com<!--/email_off--></body>',
            '<body><!--email_off-->unrelated<!--/email_off--></body>',
        ):
            with self.subTest(source=source), self.assertRaises(ValueError):
                email.render_html(source)

    def test_every_production_html_is_checked_and_engine_fixtures_are_excluded(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as scratch:
            root = Path(scratch)
            (root / "_engine").mkdir()
            (root / "_engine/fixture.html").write_text("bad@example.com")
            (root / "good.html").write_text('<html><body>Public text</body></html>')
            (root / "bad.html").write_text('<html><body>hourstag.app@gmail.com</body></html>')
            before = email.scan(root)
            self.assertEqual(2, before["html_checked"])
            self.assertFalse(before["passed"])
            self.assertEqual("bad.html", before["failures"][0]["path"])
            repaired = email.scan(root, render=True)
            self.assertTrue(repaired["passed"])
            self.assertEqual(["bad.html"], repaired["changed_files"])
            self.assertTrue(email.scan(root)["passed"])

    def test_all_four_real_regressions_keep_full_canonical_content(self):
        for relative in FOUR:
            with self.subTest(page=relative):
                source = (PAGES / relative).read_text()
                unprotected = email.canonical_html_unchecked(source)
                self.assertIn(email.PUBLIC_CONTACT, "".join(Visible(unprotected).text))
                self.assertNotEqual(unprotected, simulate_cloudflare(unprotected))
                rendered = email.render_html(unprotected)
                self.assertFalse(email.EmailMarkup(rendered).issues)
                canonical = email.canonical_html(rendered)
                self.assertEqual(unprotected, canonical)
                self.assertEqual(canonical, simulate_cloudflare(rendered))
                record = email.source_record(rendered)
                self.assertEqual(email.digest(rendered.encode()), record["source_sha256"])
                self.assertEqual(email.digest(canonical.encode()), record["canonical_sha256"])

    def test_three_guide_generators_protect_the_real_description_at_source(self):
        with tempfile.TemporaryDirectory(dir=GEO / "tests") as scratch:
            with patch.object(guides, "PAGES", scratch):
                for key in ("savetag", "shotinbox", "zipbox"):
                    result = Path(guides.build_one(key, "en-US", ["en-US"]))
                    source = result.read_text()
                    self.assertIn(email.PUBLIC_CONTACT, "".join(Visible(source).text))
                    self.assertFalse(email.EmailMarkup(source).issues)
                    self.assertEqual(email.canonical_html(source), simulate_cloudflare(source))

    def test_zipbox_decision_template_protects_its_real_lead(self):
        data = json.loads((PAGES / "data/app-install-decision-routes.json").read_text())
        record = next(r for r in data["records"] if r["app_key"] == "zipbox" and r["locale"] == "en-US")
        source = decisions.render_page(record, data["dateModified"], "App decisions")
        self.assertIn(email.PUBLIC_CONTACT, "".join(Visible(source).text))
        self.assertFalse(email.EmailMarkup(source).issues)
        self.assertEqual(email.canonical_html(source), simulate_cloudflare(source))

    def test_unknown_rewrites_still_fail_the_original_hash_gate(self):
        source = email.render_html('<body>Support: hourstag.app@gmail.com</body>')
        expected = email.source_record(source)["canonical_sha256"]
        good = email.canonical_html(source).encode()
        generation.verify_output_bytes(good, site=generation.EDGE_SITE, relative="en-US/zipbox.html", expected_sha256=expected)
        for bad in (good.replace(b"Support", b"Changed"), good.replace(b"hourstag.app", b"other"), good+b"<script>bad()</script>"):
            with self.assertRaises(generation.GenerationError):
                generation.verify_output_bytes(bad, site=generation.EDGE_SITE, relative="en-US/zipbox.html", expected_sha256=expected)
        record = email.source_record(source)
        proof = email.verify_body(good, source, record, site=generation.EDGE_SITE,
                                  relative="en-US/zipbox.html")
        self.assertEqual("source_bound_email_off", proof["email_method"])
        forged = {**record, "canonical_sha256": email.digest(b"unreviewed")}
        with self.assertRaisesRegex(ValueError, "not bound"):
            email.verify_body(b"unreviewed", source, forged, site=generation.EDGE_SITE,
                              relative="en-US/zipbox.html")

    def test_release_runs_the_full_rendered_gate_after_image_generation(self):
        source = (PAGES / ".github/workflows/pages.yml").read_text()
        render = source.index("name: Render source-owned public email protection")
        seal = source.index("name: Prepare externally bound high-intent deployment")
        images = source.index("name: Gate evidenced native result images")
        gate = source.index("name: Require all production HTML email protection")
        upload = source.index("name: Upload artifact")
        self.assertLess(render, seal)
        self.assertLess(images, gate)
        self.assertLess(gate, upload)
        self.assertNotIn("--render", source[gate:upload])


if __name__ == "__main__":
    unittest.main()
