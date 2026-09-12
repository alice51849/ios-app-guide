"""Independent reproduction of Cloudflare's observed non-email @version rewrite."""
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shlex
import sys
import tempfile
import unittest

GEO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(GEO))
import deployment_generation as generation
import public_email as email
import publisher_intent_catalog as publisher
from official_locales import OFFICIAL_LOCALES

PINS = ("lumi-app-finder@v1.3.0", "skills@1.5.19")
EXCLUDED = re.compile(
    r"(<!--email_off-->.*?<!--/email_off-->|"
    r"<(?:head|script|noscript|textarea|xmp)\b.*?</(?:head|script|noscript|textarea|xmp)>)",
    re.S | re.I,
)


def simulate_observed_edge(source):
    sections = []
    changed = False
    for section in EXCLUDED.split(source):
        if section.startswith("<!--email_off-->"):
            sections.append(section.removeprefix("<!--email_off-->").removesuffix("<!--/email_off-->"))
        elif EXCLUDED.fullmatch(section):
            sections.append(section)
        else:
            output = []
            for token in re.split(r"(<[^>]*>)", section):
                if not token.startswith("<"):
                    for value in PINS:
                        if value in token:
                            key = 0x89
                            encoded = bytes([key, *(byte ^ key for byte in value.encode())]).hex()
                            token = token.replace(
                                value,
                                f'<a href="/cdn-cgi/l/email-protection" class="__cf_email__" '
                                f'data-cfemail="{encoded}">[email&#160;protected]</a>',
                            )
                            changed = True
                output.append(token)
            sections.append("".join(output))
    result = "".join(sections)
    if changed:
        result = result.replace(
            "</body>",
            '<script data-cfasync="false" src="/cdn-cgi/scripts/5c5dd728/cloudflare-static/email-decode.min.js"></script></body>',
        )
    return result


class CodeText(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.active = None
        self.commands = []
        self.visible = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        if tag == "code":
            self.active = []

    def handle_endtag(self, tag):
        if tag == "code" and self.active is not None:
            self.commands.append("".join(self.active))
            self.active = None

    def handle_data(self, data):
        self.visible.append(data)
        if self.active is not None:
            self.active.append(data)


class PackagePinProtectionTests(unittest.TestCase):
    def setUp(self):
        self.command = publisher.AGENT_SKILL_INSTALL_COMMANDS["github_copilot"]
        self.source = "<html><head></head><body><code>" + html.escape(self.command) + "</code></body></html>"

    def test_required_cli_pin_is_not_an_email_and_remains_copyable_without_js(self):
        self.assertIn("lumi-app-finder@v", self.command)
        self.assertIsNone(email.EMAIL.search(self.command))
        rendered = "<html><head></head><body><code>" + email.code_text(self.command) + "</code></body></html>"
        self.assertEqual(CodeText(rendered).commands, [self.command])
        self.assertEqual(shlex.split(CodeText(rendered).commands[0]), shlex.split(self.command))
        self.assertEqual(email.canonical_html(rendered), self.source)
        self.assertNotIn("<script", rendered)
        self.assertIn("<!--email_off-->", rendered)
        self.assertFalse(email.EmailMarkup(rendered).issues)

    def test_observed_cloudflare_rewrite_fails_raw_hash_before_and_passes_after(self):
        broken = simulate_observed_edge(self.source)
        self.assertIn("data-cfemail", broken)
        expected = hashlib.sha256(self.source.encode()).hexdigest()
        with self.assertRaises(generation.GenerationError):
            generation.verify_output_bytes(
                broken.encode(), site=generation.EDGE_SITE,
                relative="bn-BD/data/lumi-studio-publisher-search-intent-catalog.html",
                expected_sha256=expected,
            )
        rendered = email.render_html(self.source)
        response = simulate_observed_edge(rendered)
        self.assertEqual(response.encode(), self.source.encode())
        self.assertEqual(CodeText(response).commands, [self.command])
        self.assertNotIn("/cdn-cgi/", response)
        generation.verify_output_bytes(
            response.encode(), site=generation.EDGE_SITE,
            relative="bn-BD/data/lumi-studio-publisher-search-intent-catalog.html",
            expected_sha256=email.source_record(rendered)["canonical_sha256"],
        )

    def test_unknown_content_or_token_changes_still_fail_the_unmodified_gate(self):
        rendered = email.render_html(self.source)
        body = simulate_observed_edge(rendered)
        expected = email.source_record(rendered)["canonical_sha256"]
        for mutated in (body.replace("@v1.3.0", "@v1.3.1"), body + " ", body.replace("--scope user", "--scope global")):
            with self.assertRaises(generation.GenerationError):
                generation.verify_output_bytes(
                    mutated.encode(), site=generation.EDGE_SITE, relative="bn-BD/data/catalog.html",
                    expected_sha256=expected,
                )

    def test_only_visible_code_semver_can_justify_a_non_email_directive(self):
        for invalid in (
            "<body><!--email_off-->unrelated<!--/email_off--></body>",
            "<body><!--email_off-->lumi-app-finder@v1.3.0<!--/email_off--></body>",
            "<body><code><!--email_off-->package@latest<!--/email_off--></code></body>",
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                email.render_html(invalid)
        rendered = email.render_html(self.source)
        self.assertEqual(rendered, email.render_html(rendered))
        self.assertEqual(email.EmailMarkup(self.source).issues[0]["kind"], "unprotected_package_pin")

    def test_real_contact_email_is_not_replaced_or_hidden_by_package_support(self):
        source = self.source.replace("</body>", '<p>hourstag.app@gmail.com</p></body>')
        rendered = email.render_html(source)
        self.assertEqual(CodeText(source).visible, CodeText(rendered).visible)
        self.assertEqual(email.canonical_html(rendered), source)
        self.assertEqual(email.PUBLIC_CONTACT, "hourstag.app@gmail.com")
        self.assertIn(email.PUBLIC_CONTACT, "".join(CodeText(rendered).visible))

    def test_all_publisher_landings_have_six_source_protected_commands(self):
        pages = Path(os.environ.get("GEO_PAGES", GEO / "pages"))
        paths = [Path("data") / f"{publisher.SLUG}.html", *(
            Path(locale) / "data" / f"{publisher.SLUG}.html" for locale in OFFICIAL_LOCALES
        )]
        self.assertEqual(len(paths), 51)
        for relative in paths:
            with self.subTest(page=str(relative)):
                source = (pages / relative).read_text()
                parsed = email.EmailMarkup(source)
                self.assertFalse(parsed.issues)
                pins = [pin for region in parsed.regions for pin in region["package_pins"]]
                self.assertEqual(len(pins), 6)
                self.assertEqual(set(pins), set(PINS))
                response = simulate_observed_edge(source)
                self.assertNotIn("data-cfemail", response)
                self.assertEqual(email.canonical_html(source).encode(), response.encode())
                self.assertEqual(CodeText(source).commands, CodeText(response).commands)

    def test_normal_refresh_preserves_every_non_directive_byte_and_is_idempotent(self):
        pages = Path(os.environ.get("GEO_PAGES", GEO / "pages"))
        paths = [Path("data") / f"{publisher.SLUG}.html", *(
            Path(locale) / "data" / f"{publisher.SLUG}.html" for locale in OFFICIAL_LOCALES
        )]
        with tempfile.TemporaryDirectory(prefix=".package-pin-", dir=GEO / "tests") as scratch:
            root = Path(scratch)
            before = {}
            for relative in paths:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                source = (pages / relative).read_text()
                unprotected = re.sub(
                    r"<code><!--email_off-->(.*?)<!--/email_off--></code>",
                    r"<code>\1</code>", source, flags=re.S,
                )
                before[relative] = unprotected
                path.write_text(unprotected)
            result = publisher.refresh_install_command_protection(root)
            self.assertEqual(len(result["changed"]), 51)
            self.assertEqual(publisher.refresh_install_command_protection(root)["changed"], [])
            for relative, original in before.items():
                rendered = (root / relative).read_text()
                self.assertEqual(email.canonical_html(rendered), email.canonical_html_unchecked(original))
                self.assertEqual(CodeText(rendered).commands, CodeText(original).commands)


if __name__ == "__main__":
    unittest.main()
