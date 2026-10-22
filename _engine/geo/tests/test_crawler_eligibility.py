#!/usr/bin/env python3
"""Offline regression tests: eligibility is not indexing or a crawler receipt."""

from email.message import Message
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import crawler_eligibility as audit
from crawler_policy import (
    CRAWLER_SOURCES, PRIVATE_PATHS, PageSignals, RobotsPolicy, SEARCH_CRAWLERS,
    TRAINING_CRAWLERS, render_robots, require_root_scope,
)
from official_locales import OFFICIAL_LOCALES
from site_config import PUBLIC_ROOT, PUBLIC_SITE


ROOT_ROBOTS = f"{PUBLIC_ROOT}/robots.txt"
PAGE = f"{PUBLIC_SITE}/en-US/notesstudio100.html"


def policy():
    return render_robots([f"{PUBLIC_SITE}/sitemap_index.xml"], PUBLIC_SITE)


def index():
    return {
        "locale_count": 50,
        "locales": [{"locale": locale, "url": f"{PUBLIC_SITE}/llms/{locale}.txt"}
                    for locale in OFFICIAL_LOCALES],
    }


def page(url=PAGE, extra=""):
    alternates = "".join(
        f'<link rel="alternate" hreflang="{locale}" '
        f'href="{PUBLIC_SITE}/{locale}/notesstudio100.html">'
        for locale in OFFICIAL_LOCALES)
    return f'<head><link rel="canonical" href="{url}">{alternates}{extra}</head>'


class RootAndPrecedenceTests(unittest.TestCase):
    def test_only_origin_root_is_authoritative(self):
        require_root_scope(ROOT_ROBOTS, PAGE)
        for url in (f"{PUBLIC_SITE}/robots.txt", ROOT_ROBOTS + "?preview=1",
                    ROOT_ROBOTS + "#fragment",
                    ROOT_ROBOTS.replace("https:", "http:"),
                    "https://alice51849.github.io/robots.txt",
                    ROOT_ROBOTS.replace(".cc/", ".cc:8443/")):
            with self.subTest(url=url), self.assertRaises(ValueError):
                require_root_scope(url, PAGE)

    def test_default_https_port_is_same_authority(self):
        require_root_scope(ROOT_ROBOTS.replace(".cc/", ".cc:443/"), PAGE)

    def test_specific_search_group_ignores_wildcard_block(self):
        parsed = RobotsPolicy("User-agent: *\nDisallow: /\n"
                              "User-agent: OAI-SearchBot\nAllow: /\n")
        self.assertTrue(parsed.allowed("OAI-SearchBot", PAGE, ROOT_ROBOTS))
        self.assertFalse(parsed.allowed("GPTBot", PAGE, ROOT_ROBOTS))

    def test_specific_training_group_does_not_affect_search(self):
        parsed = RobotsPolicy(policy())
        for bot in SEARCH_CRAWLERS:
            self.assertTrue(parsed.allowed(bot, PAGE, ROOT_ROBOTS), bot)
        for bot in TRAINING_CRAWLERS:
            self.assertFalse(parsed.allowed(bot, PAGE, ROOT_ROBOTS), bot)
        self.assertTrue(parsed.allowed("AnotherSearchCrawler", PAGE, ROOT_ROBOTS))

    def test_extra_allowed_list_cannot_reenable_training(self):
        parsed = RobotsPolicy(render_robots(
            [], PUBLIC_SITE, extra_allowed=("gptbot", "Applebot-Extended")))
        self.assertFalse(parsed.allowed("GPTBot", PAGE, ROOT_ROBOTS))
        self.assertTrue(parsed.allowed("Applebot", PAGE, ROOT_ROBOTS))

    def test_applebot_follows_googlebot_only_when_not_explicit(self):
        text = "User-agent: *\nAllow: /\nUser-agent: Googlebot\nDisallow: /\n"
        self.assertFalse(RobotsPolicy(text).allowed("Applebot", PAGE, ROOT_ROBOTS))
        text += "User-agent: Applebot\nAllow: /\n"
        self.assertTrue(RobotsPolicy(text).allowed("Applebot", PAGE, ROOT_ROBOTS))

    def test_specific_training_allow_on_a_public_page_fails_gate(self):
        text = policy() + "\nUser-agent: GPTBot\nAllow: /ios-app-guide/en-US/\n"
        self.assertIn("training_opt_out_conflict:GPTBot",
                      audit.check_policy(text, [PAGE], ROOT_ROBOTS, child_body=policy()))

    def test_duplicate_specific_groups_merge_and_specific_path_wins(self):
        parsed = RobotsPolicy("User-agent: bingbot\nAllow: /\n"
                              "User-agent: Bingbot\nDisallow: /ios-app-guide/\n")
        self.assertFalse(parsed.allowed("Bingbot", PAGE, ROOT_ROBOTS))

    def test_equal_length_allow_wins_but_conflict_is_a_gate_failure(self):
        parsed = RobotsPolicy("User-agent: GPTBot\nDisallow: /\n"
                              "User-agent: GPTBot\nAllow: /\n")
        self.assertTrue(parsed.allowed("GPTBot", PAGE, ROOT_ROBOTS))
        self.assertEqual(parsed.conflicts("GPTBot"), ["/"])
        self.assertIn("training_opt_out_conflict:GPTBot", audit.check_policy(
            policy() + "\nUser-agent: GPTBot\nAllow: /\n", [PAGE], ROOT_ROBOTS,
            child_body=policy()))

    def test_cloudflare_training_prefix_cannot_block_search(self):
        managed = ("User-agent: *\nContent-Signal: search=yes,ai-train=no\nAllow: /\n"
                   "User-agent: GPTBot\nDisallow: /\n"
                   "User-agent: Applebot-Extended\nDisallow: /\n")
        self.assertEqual(audit.check_policy(
            managed + policy(), [PAGE], ROOT_ROBOTS, child_body=policy()), [])

    def test_conflicting_search_disallow_fails_gate(self):
        text = policy() + "\nUser-agent: PerplexityBot\nDisallow: /ios-app-guide/\n"
        self.assertTrue(any("disallowed:PerplexityBot" in error
                            for error in audit.check_policy(
                                text, [PAGE], ROOT_ROBOTS, child_body=policy())))

    def test_private_tooling_block_does_not_block_assets_or_catalogs(self):
        parsed = RobotsPolicy(policy())
        for bot in SEARCH_CRAWLERS:
            for path in ("assets/icon.png", "assets/app-store-share-v1.js",
                         "llms/index.json", "sitemap.xml",
                         "bn-BD/notesstudio100.html"):
                self.assertTrue(parsed.allowed(bot, f"{PUBLIC_SITE}/{path}", ROOT_ROBOTS))
            self.assertFalse(parsed.allowed(bot, f"{PUBLIC_SITE}/_engine/source.py", ROOT_ROBOTS))
            self.assertTrue(parsed.allowed(
                bot, f"{PUBLIC_ROOT}/scripts/crawler_policy.py", ROOT_ROBOTS))
            self.assertTrue(parsed.allowed(
                bot, f"{PUBLIC_ROOT}/.well-known/ai-catalog.json", ROOT_ROBOTS))

    def test_wildcards_end_anchor_queries_and_utf8(self):
        text = ("User-agent: *\nDisallow: /ios-app-guide/*\n"
                "Allow: /ios-app-guide/llms.txt$\nAllow: /ios-app-guide/文/\n")
        parsed = RobotsPolicy(text)
        self.assertTrue(parsed.allowed("Googlebot", f"{PUBLIC_SITE}/llms.txt", ROOT_ROBOTS))
        self.assertFalse(parsed.allowed("Googlebot", f"{PUBLIC_SITE}/llms.txt?q=1", ROOT_ROBOTS))
        self.assertTrue(parsed.allowed("Googlebot", f"{PUBLIC_SITE}/%E6%96%87/a", ROOT_ROBOTS))
        self.assertFalse(parsed.allowed("Googlebot", f"{PUBLIC_SITE}/%2Fllms.txt", ROOT_ROBOTS))

    def test_google_documented_rule_length_precedence(self):
        cases = (
            ("/x", "/x$", "/x", False),
            ("/x", "/x$", "/x?query=1", True),
            ("/", "/$", "/", False),
            ("/p", "/", "/page", True),
            ("/folder", "/folder", "/folder/page", True),
            ("/page", "/*.htm", "/page.htm", False),
            ("/page", "/*.ph", "/page.php5", True),
            ("/$", "/", "/", True),
            ("/$", "/", "/page.htm", False),
            ("/page*", "/page$", "/page", True),
        )
        for allow, deny, path, expected in cases:
            with self.subTest(allow=allow, deny=deny, path=path):
                parsed = RobotsPolicy(
                    f"User-agent: Googlebot\nAllow: {allow}\nDisallow: {deny}\n")
                self.assertEqual(parsed.allowed(
                    "Googlebot", PUBLIC_ROOT + path, ROOT_ROBOTS), expected)

    def test_terminal_disallow_cannot_receive_an_eligibility_pass(self):
        url = f"{PUBLIC_SITE}/x"
        text = policy() + (
            "\nUser-agent: Googlebot\nAllow: /ios-app-guide/x\n"
            "Disallow: /ios-app-guide/x$\n")
        self.assertIn(f"disallowed:Googlebot:{url}",
                      audit.check_policy(text, [url], ROOT_ROBOTS, child_body=policy()))

    def test_sitemap_and_blank_lines_do_not_split_unfinished_agent_group(self):
        parsed = RobotsPolicy("User-agent: Applebot\n\nSitemap: https://example.test/s.xml\n"
                              "User-agent: Googlebot\nDisallow: /\n")
        self.assertFalse(parsed.allowed("Applebot", PAGE, ROOT_ROBOTS))


class DiscoveryAndNoindexTests(unittest.TestCase):
    def test_exact_50_canonical_locale_urls_and_hreflang(self):
        urls = audit.locale_page_urls("notesstudio100")
        self.assertEqual(len(set(urls)), 50)
        self.assertEqual(audit.check_catalog_index(index()), [])
        for url in urls:
            self.assertEqual(audit.check_page(url, page(url), app_key="notesstudio100"), [])

    def test_missing_duplicate_and_origin_locale_urls_fail(self):
        broken = index()
        broken["locales"][-1] = broken["locales"][0]
        self.assertIn("catalog_exact_50_locales", audit.check_catalog_index(broken))
        broken = index()
        broken["locales"][0]["url"] = broken["locales"][0]["url"].replace(
            PUBLIC_ROOT, "https://alice51849.github.io")
        self.assertTrue(audit.check_catalog_index(broken))

    def test_noindex_none_and_bot_specific_noindex_fail(self):
        for meta in ('<META NAME="ROBOTS" CONTENT="noindex, follow">',
                     '<meta name="applebot" content="none">',
                     '<meta name="robots" content="NOINDEX NOFOLLOW">',
                     '<meta content="noindex" name="googlebot">'):
            self.assertTrue(any("noindex:" in error
                                for error in audit.check_page(PAGE, page(extra=meta))))

    def test_headers_preserve_bot_scope_and_duplicate_values(self):
        headers = [("X-Robots-Tag", "googlebot: noindex, nofollow"),
                   ("X-Robots-Tag", "applebot: nosnippet"),
                   ("X-Robots-Tag", "max-snippet:0")]
        signals = PageSignals(page())
        self.assertIn("noindex", signals.restrictions("Googlebot", headers))
        self.assertNotIn("noindex", signals.restrictions("Bingbot", headers))
        self.assertIn("nosnippet", signals.restrictions("Applebot", headers))
        self.assertIn("max-snippet:0", signals.restrictions("Applebot", headers))
        self.assertIn("noindex:Googlebot", audit.check_page(PAGE, page(), headers))

    def test_generic_header_noindex_is_not_overridden_by_index_meta(self):
        errors = audit.check_page(PAGE, page(extra='<meta name="robots" content="index">'),
                                  [("X-Robots-Tag", "noindex")])
        self.assertEqual(len([error for error in errors if error.startswith("noindex:")]), 5)

    def test_allow_does_not_cancel_noindex(self):
        self.assertEqual(audit.check_policy(
            policy(), [PAGE], ROOT_ROBOTS, child_body=policy()), [])
        self.assertTrue(audit.check_page(PAGE, page(extra='<meta name="robots" content="noindex">')))

    def test_canonical_and_hreflang_mismatch_are_not_eligible(self):
        source = page().replace(f'{PUBLIC_SITE}/bn-BD/', 'https://wrong.example/bn-BD/')
        self.assertIn("hreflang:bn-BD", audit.check_page(PAGE, source, app_key="notesstudio100"))
        self.assertIn("canonical_mismatch", audit.check_page(PAGE, page(PAGE + "?duplicate=1")))


class RootChildParityTests(unittest.TestCase):
    def test_child_body_cannot_be_omitted(self):
        with self.assertRaises(TypeError):
            audit.check_policy(policy(), [PAGE], ROOT_ROBOTS)

    def test_stale_child_training_opt_ins_fail_for_every_training_bot(self):
        stale = "User-agent: *\nAllow: /\n"
        stale += "".join(f"\nUser-agent: {bot}\nAllow: /\n" for bot in TRAINING_CRAWLERS)
        stale += f"\nSitemap: {PUBLIC_SITE}/sitemap_index.xml\n"
        errors = audit.check_policy(policy(), [PAGE], ROOT_ROBOTS, child_body=stale)
        for bot in TRAINING_CRAWLERS:
            self.assertIn(f"child:training_opt_out_conflict:{bot}", errors)
            self.assertIn(f"root_child_policy_mismatch:{bot}", errors)

    def test_child_search_disallow_fails_for_every_search_bot(self):
        for bot in SEARCH_CRAWLERS:
            with self.subTest(bot=bot):
                stale = policy() + f"\nUser-agent: {bot}\nDisallow: /ios-app-guide/\n"
                errors = audit.check_policy(policy(), [PAGE], ROOT_ROBOTS, child_body=stale)
                self.assertIn(f"child:disallowed:{bot}:{PAGE}", errors)
                self.assertIn(f"root_child_policy_mismatch:{bot}", errors)

    def test_identically_bad_copies_do_not_pass_merely_because_they_match(self):
        bad = policy() + "\nUser-agent: GPTBot\nAllow: /unlisted/\n"
        errors = audit.check_policy(bad, [PAGE], ROOT_ROBOTS, child_body=bad)
        self.assertIn("training_opt_out_conflict:GPTBot", errors)
        self.assertIn("child:training_opt_out_conflict:GPTBot", errors)

    def test_rule_parity_covers_paths_outside_the_http_sample(self):
        stale = policy() + "\nUser-agent: Applebot\nDisallow: /unlisted/\n"
        errors = audit.check_policy(policy(), [PAGE], ROOT_ROBOTS, child_body=stale)
        self.assertIn("root_child_policy_mismatch:Applebot", errors)

    def test_private_paths_must_be_blocked_in_both_copies(self):
        for path in PRIVATE_PATHS:
            stale = policy().replace(f"Disallow: {path}\n", "")
            errors = audit.check_policy(policy(), [PAGE], ROOT_ROBOTS, child_body=stale)
            for bot in SEARCH_CRAWLERS:
                with self.subTest(path=path, bot=bot):
                    self.assertIn(f"child:private_path_allowed:{bot}:{path}", errors)

    def test_live_readback_does_not_ignore_a_stale_child_response(self):
        import hashlib

        local = {
            "urls": audit.locale_page_urls("notesstudio100") + [
                f"{PUBLIC_SITE}/{path}" for path in audit.DISCOVERY_PATHS
            ] + [f"{PUBLIC_ROOT}/.well-known/ai-catalog.json"],
            "app_key": "notesstudio100",
            "root_robots_sha256": hashlib.sha256(policy().encode()).hexdigest(),
        }

        def get(url):
            body = "{}"
            if url == ROOT_ROBOTS:
                body = policy()
            elif url == f"{PUBLIC_SITE}/robots.txt":
                body = "User-agent: *\nAllow: /\n"
            return {"url": url, "method": "GET", "status": 200, "body": body,
                    "headers": [("content-type", "text/plain")]}

        with patch.object(audit, "public_get", side_effect=get):
            result = audit.live_audit(local)
        self.assertFalse(result["root_child_policy_parity"])
        self.assertFalse(result["passed"])
        self.assertIn("child:training_opt_out_conflict:GPTBot", result["errors"])
        self.assertFalse(result["child_robots_authoritative"])
        self.assertEqual(result["actual_crawl_receipt"], "unknown")


class ScriptsDependencyTests(unittest.TestCase):
    def test_functional_html_and_js_scripts_dependencies_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as work:
            root, guide = Path(work) / "root", Path(work) / "guide"
            root.mkdir()
            guide.mkdir()
            (root / "index.html").write_text('<script src=/scripts/app.js></script>')
            (guide / "app.js").write_text('import(`/scripts/shared.js`);')
            report = audit.scan_public_frontend(guide, root)
        self.assertEqual({item["target"] for item in report["scripts_dependencies"]},
                         {f"{PUBLIC_ROOT}/scripts/app.js", f"{PUBLIC_ROOT}/scripts/shared.js"})

    def test_public_assets_remain_checked_and_tooling_is_not_a_frontend(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as work:
            root, guide = Path(work) / "root", Path(work) / "guide"
            (root / "scripts").mkdir(parents=True)
            (guide / "assets").mkdir(parents=True)
            (root / "scripts" / "build.mjs").write_text('import "/scripts/helper.mjs";')
            (guide / "assets" / "app.js").write_text('console.log("public");')
            (guide / "index.html").write_text('<script src="assets/app.js"></script>')
            report = audit.scan_public_frontend(guide, root)
        self.assertEqual(report["scripts_dependencies"], [])
        self.assertEqual(report["public_js_urls"], [f"{PUBLIC_SITE}/assets/app.js"])
        self.assertEqual(report["files_checked"], 2)

    def test_html_base_entities_and_unquoted_modulepreload_are_not_missed(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as work:
            root, guide = Path(work) / "root", Path(work) / "guide"
            root.mkdir()
            guide.mkdir()
            (root / "index.html").write_text(
                '<base href=/scripts/><script src=app.js></script>'
                '<link rel=modulepreload href=/scripts/module.js>'
                '<script src="&#47;&#115;cripts/entity.js"></script>')
            report = audit.scan_public_frontend(guide, root)
        targets = {item["target"] for item in report["scripts_dependencies"]}
        self.assertTrue({f"{PUBLIC_ROOT}/scripts/{name}" for name in
                         ("app.js", "module.js", "entity.js")} <= targets)

    def test_escaped_js_slashes_are_not_missed(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as work:
            root, guide = Path(work) / "root", Path(work) / "guide"
            root.mkdir()
            guide.mkdir()
            (guide / "app.js").write_text(r'import("\/scripts\/shared.js");')
            report = audit.scan_public_frontend(guide, root)
        self.assertEqual(report["scripts_dependencies"],
                         [{"source": f"{PUBLIC_SITE}/app.js",
                           "target": f"{PUBLIC_ROOT}/scripts/shared.js"}])

    def test_percent_encoded_base_is_not_missed(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as work:
            root, guide = Path(work) / "root", Path(work) / "guide"
            root.mkdir()
            guide.mkdir()
            (root / "index.html").write_text(
                '<base href=/%73cripts/><script src=a.js></script>')
            report = audit.scan_public_frontend(guide, root)
        self.assertEqual(report["scripts_dependencies"],
                         [{"source": f"{PUBLIC_ROOT}/index.html",
                           "target": f"{PUBLIC_ROOT}/%73cripts/a.js"}])


class PublicReadbackTests(unittest.TestCase):
    def test_official_search_ips_are_not_training_ips(self):
        self.assertEqual(set(CRAWLER_SOURCES), set(SEARCH_CRAWLERS))
        self.assertEqual(CRAWLER_SOURCES["OAI-SearchBot"]["ip_ranges"],
                         "https://openai.com/searchbot.json")

    def test_only_public_get_with_an_honest_audit_user_agent(self):
        class Response:
            status = 200
            headers = Message()

            def read(self, limit):
                return b"User-agent: *\nAllow: /\n"

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

        seen = []

        class Opener:
            def open(self, request, timeout):
                seen.append(request)
                return Response()

        with patch.object(audit.urllib.request, "build_opener", return_value=Opener()):
            result = audit.public_get(ROOT_ROBOTS)
        self.assertEqual(result["status"], 200)
        self.assertEqual(seen[0].get_method(), "GET")
        self.assertEqual(seen[0].get_header("User-agent"), audit.AUDIT_USER_AGENT)
        self.assertFalse(any(bot in audit.AUDIT_USER_AGENT for bot in SEARCH_CRAWLERS))

    def test_paid_apis_asc_and_unrelated_hosts_cannot_be_fetched(self):
        for url in ("https://api.openai.com/v1/responses", "https://api.perplexity.ai/chat/completions",
                    "https://api.appstoreconnect.apple.com/v1/apps",
                    "https://open.cait518.cc.attacker.example/robots.txt"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                audit.public_get(url)

    def test_only_the_observed_official_ip_redirect_is_followed(self):
        class Response:
            def __init__(self, status, location=""):
                self.status = status
                self.headers = Message()
                if location:
                    self.headers["Location"] = location

            def read(self, limit):
                return b'{"prefixes":[{"ipv4Prefix":"192.0.2.0/24"}]}'

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

        seen = []

        class Opener:
            def open(self, request, timeout):
                seen.append(request.full_url)
                if request.full_url.endswith(".com/perplexitybot.json"):
                    return Response(302, "https://www.perplexity.ai/perplexitybot.json")
                return Response(200)

        with patch.object(audit.urllib.request, "build_opener", return_value=Opener()):
            result = audit.public_get("https://www.perplexity.com/perplexitybot.json")
        self.assertEqual(result["status"], 200)
        self.assertEqual(result["redirects"][0]["status"], 302)
        self.assertEqual(len(seen), 2)
        self.assertEqual(result["final_url"], "https://www.perplexity.ai/perplexitybot.json")

    def test_canonical_root_redirect_is_not_silently_followed(self):
        class Response:
            status = 302
            headers = Message()
            headers["Location"] = f"{PUBLIC_SITE}/robots.txt"

            def read(self, limit):
                return b""

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

        with patch.object(audit.urllib.request, "build_opener") as factory:
            factory.return_value.open.return_value = Response()
            result = audit.public_get(ROOT_ROBOTS)
        self.assertEqual(result["status"], 302)
        self.assertEqual(factory.return_value.open.call_count, 1)

    def test_xml_gets_the_standard_sitemap_size_budget(self):
        class Response:
            status = 200
            headers = Message()

            def read(self, limit):
                self.limit = limit
                return b"<urlset/>"

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

        response = Response()
        with patch.object(audit.urllib.request, "build_opener") as factory:
            factory.return_value.open.return_value = response
            audit.public_get(f"{PUBLIC_SITE}/sitemap.xml")
        self.assertEqual(response.limit, 50 * 1024 * 1024 + 1)


class GeneratorWiringTests(unittest.TestCase):
    def test_llms_generator_cannot_opt_search_out_or_training_in(self):
        import gen_llms

        self.assertEqual(audit.check_policy(
            policy(), [PAGE], ROOT_ROBOTS, child_body=gen_llms.build_robots()), [])

    def test_locale_generator_uses_the_same_policy(self):
        import build_pages_i18n

        with patch.object(build_pages_i18n, "write_text_if_changed") as writer:
            with patch.object(build_pages_i18n.os.path, "exists", return_value=True):
                build_pages_i18n.build_robots()
        self.assertEqual(audit.check_policy(
            policy(), [PAGE], ROOT_ROBOTS, child_body=writer.call_args.args[1]), [])


if __name__ == "__main__":
    unittest.main()
