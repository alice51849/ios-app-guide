#!/usr/bin/env python3
"""Read-only canonical crawler eligibility gate; never submits or impersonates bots."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html import unescape
import ipaddress
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import quote, unquote, urljoin, urlsplit
import xml.etree.ElementTree as ET

from crawler_policy import (
    CRAWLER_SOURCES, OFFICIAL_FEED_REDIRECTS, PageSignals as PolicyPageSignals,
    RobotsPolicy, SEARCH_CRAWLERS,
    PRIVATE_PATHS, TRAINING_CRAWLERS, require_root_scope,
)
from official_locales import OFFICIAL_LOCALES
from site_config import PUBLIC_ROOT, PUBLIC_SITE


AUDIT_USER_AGENT = "LumiCrawlerEligibilityAudit/1.0"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024
MAX_SITEMAP_BYTES = 50 * 1024 * 1024
HEADER_NAMES = {
    "content-type", "x-robots-tag", "cache-control", "age", "etag",
    "last-modified", "server", "cf-cache-status", "cf-mitigated",
    "x-origin-cache", "via", "location",
}
DISCOVERY_PATHS = (
    "sitemap_index.xml", "sitemap.xml", "sitemap_llms.xml",
    "llms.txt", "llms/index.json", "data/verified-ios-app-finder-catalog.json",
)


def locale_page_urls(app_key: str) -> list[str]:
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", app_key):
        raise ValueError("Invalid app key")
    return [f"{PUBLIC_SITE}/{locale}/{app_key}.html"
            for locale in OFFICIAL_LOCALES]


def check_page(url: str, body: str, headers=(), app_key="") -> list[str]:
    signals = PageSignals(body)
    errors = []
    if signals.canonicals != [url]:
        errors.append("canonical_mismatch")
    if app_key:
        alternates = dict(signals.alternates)
        if len(alternates) != len(signals.alternates):
            errors.append("duplicate_hreflang")
        for locale in OFFICIAL_LOCALES:
            if alternates.get(locale) != f"{PUBLIC_SITE}/{locale}/{app_key}.html":
                errors.append(f"hreflang:{locale}")
    for bot in SEARCH_CRAWLERS:
        if "noindex" in signals.restrictions(bot, headers):
            errors.append(f"noindex:{bot}")
    return errors


def check_catalog_index(document: dict) -> list[str]:
    entries = document.get("locales", [])
    locales = [entry.get("locale") for entry in entries]
    errors = []
    if (len(locales) != 50 or set(locales) != set(OFFICIAL_LOCALES)
            or document.get("locale_count") != 50):
        errors.append("catalog_exact_50_locales")
    for entry in entries:
        locale = entry.get("locale", "")
        if entry.get("url") != f"{PUBLIC_SITE}/llms/{locale}.txt":
            errors.append(f"catalog_url:{locale}")
    return errors


def check_root_catalog(document: dict) -> list[str]:
    expected = {
        "robotsUrl": f"{PUBLIC_ROOT}/robots.txt",
        "sitemapUrl": f"{PUBLIC_SITE}/sitemap_index.xml",
        "llmsUrl": f"{PUBLIC_SITE}/llms.txt",
        "localizedCatalogUrl": f"{PUBLIC_SITE}/llms/index.json",
        "verifiedCatalogUrl": f"{PUBLIC_SITE}/data/verified-ios-app-finder-catalog.json",
    }
    errors = []
    if document.get("host", {}).get("documentationUrl") != f"{PUBLIC_SITE}/about.html":
        errors.append("root_catalog_noncanonical_documentation")
    entries = document.get("entries", [])
    if not entries:
        errors.append("root_catalog_empty")
    for entry in entries:
        if entry.get("url") != f"{PUBLIC_ROOT}/.well-known/lumi-app-finder.mcp.json":
            errors.append("root_catalog_noncanonical_resource")
        metadata = entry.get("metadata", {})
        errors.extend(f"root_catalog_link:{key}" for key, value in expected.items()
                      if metadata.get(key) != value)
    return errors


def _check_single_policy(policy: RobotsPolicy, urls: list[str], root_url: str) -> list[str]:
    errors = []
    for bot in (*SEARCH_CRAWLERS, "UnlistedSearchCrawler"):
        if policy.conflicts(bot):
            errors.append(f"conflicting_rules:{bot}")
        for url in urls:
            if not policy.allowed(bot, url, root_url):
                errors.append(f"disallowed:{bot}:{url}")
        for path in PRIVATE_PATHS:
            if policy.allowed(bot, PUBLIC_ROOT + path, root_url):
                errors.append(f"private_path_allowed:{bot}:{path}")
    for bot in TRAINING_CRAWLERS:
        if (policy.conflicts(bot)
                or any(rule.allow and rule.path for rule in policy.rules_for(bot))
                or any(policy.allowed(bot, url, root_url)
                       for url in (PUBLIC_ROOT + "/", PUBLIC_SITE + "/", *urls))):
            errors.append(f"training_opt_out_conflict:{bot}")
    if f"{PUBLIC_SITE}/sitemap_index.xml" not in policy.sitemaps:
        errors.append("root_missing_guide_sitemap_index")
    return errors


def check_policy(body: str, urls: list[str], root_url: str, *, child_body: str) -> list[str]:
    """Require a current child mirror without granting it independent authority."""
    root, child = RobotsPolicy(body), RobotsPolicy(child_body)
    errors = _check_single_policy(root, urls, root_url)
    errors.extend(f"child:{error}" for error in _check_single_policy(child, urls, root_url))
    for bot in (*SEARCH_CRAWLERS, *TRAINING_CRAWLERS, "UnlistedSearchCrawler"):
        root_rules = {(rule.allow, rule.path) for rule in root.rules_for(bot) if rule.path}
        child_rules = {(rule.allow, rule.path) for rule in child.rules_for(bot) if rule.path}
        if root_rules != child_rules:
            errors.append(f"root_child_policy_mismatch:{bot}")
    return errors


class PageSignals(PolicyPageSignals):
    """Audit rendering dependencies without changing the deployed root policy."""

    def __init__(self, text: str) -> None:
        self.base_href: str | None = None
        super().__init__(text)

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag == "base" and self.base_href is None and data.get("href"):
            self.base_href = data["href"]
        if tag == "link":
            rel = set((data.get("rel") or "").split())
            if rel & {"preload", "modulepreload", "manifest"} and not rel & {"stylesheet", "icon"}:
                self.assets.append(data.get("href") or "")
        super().handle_starttag(tag, attrs)


def scan_public_frontend(pages: Path, root_site: Path) -> dict:
    """Check published frontend literals before blocking the root tooling folder."""
    dependencies = []
    scripts = set()
    checked = 0
    for folder, site in ((pages, PUBLIC_SITE), (root_site, PUBLIC_ROOT)):
        for directory, names, files in os.walk(folder):
            names[:] = [name for name in names if name not in {
                ".git", ".github", "_engine", "node_modules",
            } and not (Path(directory) == root_site and name == "scripts")]
            for name in files:
                path = Path(directory) / name
                if path.suffix not in {".html", ".js", ".mjs", ".css"}:
                    continue
                checked += 1
                url = site + "/" + quote(path.relative_to(folder).as_posix())
                if path.suffix in {".js", ".mjs"}:
                    scripts.add(url)
                text = path.read_text(encoding="utf-8")
                normalized = unquote(unescape(text)).replace("\\/", "/")
                if "scripts/" not in normalized:
                    continue
                references = re.findall(r"""["'`(]\s*([^"'`()\s<>]+)""", normalized)
                base = url
                if path.suffix == ".html":
                    signals = PageSignals(text)
                    base = urljoin(url, signals.base_href or "")
                    references.extend(signals.assets)
                for literal in references:
                    target = urljoin(base, unquote(literal))
                    if (urlsplit(target).netloc == urlsplit(PUBLIC_ROOT).netloc
                            and unquote(urlsplit(target).path).startswith("/scripts/")):
                        dependency = {"source": url, "target": target}
                        if dependency not in dependencies:
                            dependencies.append(dependency)
    return {"files_checked": checked, "scripts_dependencies": dependencies,
            "public_js_urls": sorted(scripts)}


def _sitemap_locations(body: str) -> set[str]:
    tree = ET.fromstring(body)
    return {node.text or "" for node in tree.iter()
            if node.tag.rsplit("}", 1)[-1] == "loc"}


def local_audit(pages: Path, root_site: Path, app_key: str) -> dict:
    root_url = f"{PUBLIC_ROOT}/robots.txt"
    page_urls = locale_page_urls(app_key)
    urls = [f"{PUBLIC_SITE}/{path}" for path in DISCOVERY_PATHS]
    urls += [f"{PUBLIC_SITE}/llms/{locale}.txt" for locale in OFFICIAL_LOCALES]
    urls += page_urls
    urls += [f"{PUBLIC_ROOT}/.well-known/ai-catalog.json",
             f"{PUBLIC_ROOT}/.well-known/lumi-app-finder.mcp.json"]
    errors = []
    inventory = json.loads((pages / DISCOVERY_PATHS[-1]).read_text())
    if app_key not in {app["key"] for app in inventory["apps"]
                       if app.get("verified_live")}:
        errors.append("representative_app_not_verified_live")
    index = json.loads((pages / "llms/index.json").read_text())
    errors.extend(check_catalog_index(index))
    llms_map = _sitemap_locations((pages / "sitemap_llms.xml").read_text())
    if not {f"{PUBLIC_SITE}/llms/{loc}.txt" for loc in OFFICIAL_LOCALES} <= llms_map:
        errors.append("sitemap_missing_locale_catalogs")
    sitemap_index = _sitemap_locations((pages / "sitemap_index.xml").read_text())
    if f"{PUBLIC_SITE}/sitemap_llms.xml" not in sitemap_index:
        errors.append("sitemap_index_missing_llms")
    llms = (pages / "llms.txt").read_text()
    for path in ("llms/index.json", "data/verified-ios-app-finder-catalog.json"):
        if f"{PUBLIC_SITE}/{path}" not in llms:
            errors.append(f"llms_missing:{path}")
    assets = set()
    for url in page_urls:
        relative = url.removeprefix(PUBLIC_SITE + "/")
        source = pages / relative
        if not source.is_file():
            errors.append(f"missing_page:{relative}")
            continue
        text = source.read_text(encoding="utf-8")
        errors.extend(f"{relative}:{error}" for error in check_page(
            url, text, app_key=app_key))
        for asset in PageSignals(text).assets:
            target = urljoin(url, asset)
            if target.startswith(PUBLIC_SITE + "/"):
                assets.add(target)
    for url in assets:
        path = pages / urlsplit(url.removeprefix(PUBLIC_SITE + "/")).path
        if not path.is_file():
            errors.append(f"missing_asset:{url}")
    urls += sorted(assets)
    frontend = scan_public_frontend(pages, root_site)
    errors.extend(f"scripts_frontend_dependency:{item['source']}:{item['target']}"
                  for item in frontend["scripts_dependencies"])
    urls += frontend["public_js_urls"]
    root_robots = (root_site / "robots.txt").read_text()
    child_robots = (pages / "robots.txt").read_text()
    policy_errors = check_policy(root_robots, urls, root_url, child_body=child_robots)
    errors.extend(policy_errors)
    errors.extend(check_root_catalog(json.loads(
        (root_site / ".well-known/ai-catalog.json").read_text())))
    root_llms = (root_site / "llms.txt").read_text()
    for url in (root_url, f"{PUBLIC_ROOT}/sitemap-index.xml",
                f"{PUBLIC_SITE}/llms.txt", f"{PUBLIC_SITE}/llms/index.json",
                f"{PUBLIC_SITE}/data/verified-ios-app-finder-catalog.json"):
        if url not in root_llms:
            errors.append(f"root_llms_missing:{url}")
    return {
        "passed": not errors, "errors": errors, "locale_count": 50,
        "page_count": len(page_urls), "asset_count": len(assets),
        "app_key": app_key, "root_robots_url": root_url,
        "root_robots_sha256": hashlib.sha256(root_robots.encode()).hexdigest(),
        "child_robots_sha256": hashlib.sha256(child_robots.encode()).hexdigest(),
        "root_child_policy_parity": not policy_errors,
        "frontend_scan": frontend,
        "urls": list(dict.fromkeys(urls)),
        "evidence_type": "source_contract_not_crawler_receipt",
    }


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def public_get(url: str) -> dict:
    allowed = {entry["ip_ranges"] for entry in CRAWLER_SOURCES.values()}
    allowed.update(OFFICIAL_FEED_REDIRECTS.values())
    if not url.startswith(PUBLIC_ROOT + "/") and url not in allowed:
        raise ValueError("Readback is restricted to the canonical host and official IP feeds")
    request = urllib.request.Request(
        url, method="GET", headers={"User-Agent": AUDIT_USER_AGENT, "Accept": "*/*"})
    opener = urllib.request.build_opener(NoRedirect)
    for attempt in range(2):
        try:
            try:
                response = opener.open(request, timeout=30)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                limit = (MAX_SITEMAP_BYTES if urlsplit(url).path.endswith(".xml")
                         else MAX_RESPONSE_BYTES)
                body = response.read(limit + 1)
                if len(body) > limit:
                    raise ValueError("Public response exceeds readback limit")
                headers = [(name.casefold(), value) for name, value in response.headers.items()
                           if name.casefold() in HEADER_NAMES]
                result = {
                    "url": url, "method": "GET", "status": response.status,
                    "headers": headers, "bytes": len(body),
                    "sha256": hashlib.sha256(body).hexdigest(),
                    "body": body.decode("utf-8", errors="replace"),
                }
            target = OFFICIAL_FEED_REDIRECTS.get(url)
            if (target and result["status"] in {301, 302, 307, 308}
                    and dict(result["headers"]).get("location") == target):
                final = public_get(target)
                return {
                    **final, "url": url, "final_url": target,
                    "redirects": [{"url": url, "status": result["status"],
                                   "location": target, "method": "GET"}],
                }
            return result
        except (OSError, ValueError) as error:
            if attempt:
                return {"url": url, "method": "GET", "status": None, "error": str(error)}
            time.sleep(1)
    raise AssertionError("unreachable")


def live_audit(local: dict) -> dict:
    root_url = f"{PUBLIC_ROOT}/robots.txt"
    # Compare the mirror under root scope; the child URL itself is not authoritative.
    child_url = f"{PUBLIC_SITE}/robots.txt"
    urls = list(dict.fromkeys([
        root_url, child_url, f"{PUBLIC_ROOT}/llms.txt",
        f"{PUBLIC_ROOT}/sitemap-index.xml", *local["urls"],
        *(item["ip_ranges"] for item in CRAWLER_SOURCES.values()),
    ]))
    with ThreadPoolExecutor(max_workers=4) as executor:
        responses = list(executor.map(public_get, urls))
    by_url = {response["url"]: response for response in responses}
    errors = []
    for response in responses:
        if response["status"] != 200:
            errors.append(f"http:{response['status']}:{response['url']}")
        headers = dict(response.get("headers", []))
        if headers.get("cf-mitigated", "").casefold() == "challenge":
            errors.append(f"waf_challenge:{response['url']}")
    root = by_url[root_url]
    root_body = root.get("body", "")
    child = by_url[child_url]
    child_body = child.get("body", "")
    if "text/plain" not in dict(root.get("headers", [])).get("content-type", ""):
        errors.append("root_robots_not_text_plain")
    if "text/plain" not in dict(child.get("headers", [])).get("content-type", ""):
        errors.append("child_robots_not_text_plain")
    policy_errors = check_policy(root_body, local["urls"], root_url, child_body=child_body)
    errors.extend(policy_errors)
    if root["status"] == 200:
        # Cloudflare may prepend its managed section. The reviewed source must
        # still be present verbatim, not merely an older superficially valid file.
        marker = f"# Authoritative robots URL: {root_url}"
        start = root_body.find(marker)
        origin_body = root_body[start:] if start >= 0 else ""
        if hashlib.sha256(origin_body.encode()).hexdigest() != local["root_robots_sha256"]:
            errors.append("root_robots_source_digest_mismatch")
    app_key = local["app_key"]
    for url in locale_page_urls(app_key):
        response = by_url[url]
        errors.extend(f"{url}:{error}" for error in check_page(
            url, response.get("body", ""), response.get("headers", []), app_key))
    index_url = f"{PUBLIC_SITE}/llms/index.json"
    try:
        errors.extend(check_catalog_index(json.loads(by_url[index_url].get("body", ""))))
        errors.extend(check_root_catalog(json.loads(
            by_url[f"{PUBLIC_ROOT}/.well-known/ai-catalog.json"].get("body", ""))))
    except (ValueError, TypeError):
        errors.append("live_catalog_invalid_json")
    for path in ("sitemap_index.xml", "sitemap.xml", "sitemap_llms.xml"):
        try:
            locations = _sitemap_locations(by_url[f"{PUBLIC_SITE}/{path}"].get("body", ""))
            if not locations or any(not value.startswith(PUBLIC_ROOT + "/")
                                    for value in locations):
                errors.append(f"noncanonical_sitemap:{path}")
        except ET.ParseError:
            errors.append(f"invalid_sitemap:{path}")
    networks = {}
    for bot, source in CRAWLER_SOURCES.items():
        try:
            document = json.loads(by_url[source["ip_ranges"]].get("body", ""))
            prefixes = [value for item in document["prefixes"]
                        for key, value in item.items()
                        if key in {"ipv4Prefix", "ipv6Prefix"}]
            if not prefixes:
                raise ValueError("no official CIDRs")
            for prefix in prefixes:
                ipaddress.ip_network(prefix)
            networks[bot] = {
                **source, "official_prefix_count": len(prefixes),
                "waf_match": "product-token AND current official CIDR",
                "configuration_only": True, "actual_crawl_receipt": "unknown",
            }
        except (ValueError, KeyError, TypeError):
            errors.append(f"invalid_official_ip_feed:{bot}")
    return {
        "passed": not errors, "errors": errors,
        "root_scope": "origin_root_only", "child_robots_authoritative": False,
        "root_child_policy_parity": not policy_errors,
        "scripts_policy": (
            "blocked_or_unverified" if policy_errors else
            "allow" if RobotsPolicy(root_body).allowed(
                "UnlistedSearchCrawler", PUBLIC_ROOT + "/scripts/", root_url,
            ) else "disallow"
        ),
        "user_agent": AUDIT_USER_AGENT,
        "crawler_eligibility": {
            bot: "eligible_for_tested_public_urls" if not errors else "blocked_or_unverified"
            for bot in SEARCH_CRAWLERS
        },
        "verified_crawler_ip_waf_access": "unknown",
        "actual_crawl_receipt": "unknown", "actual_indexing": "unknown",
        "actual_citation": "unknown", "network_configuration": networks,
        "requests": [{key: value for key, value in response.items() if key != "body"}
                     for response in responses],
        "root_robots_body": root_body,
        "child_robots_body": child_body,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-dir", type=Path, required=True)
    parser.add_argument("--root-site-dir", type=Path, required=True)
    parser.add_argument("--app-key", default="notesstudio100")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    local = local_audit(args.pages_dir, args.root_site_dir, args.app_key)
    report = {
        "schema_version": 1, "observed_at": datetime.now(timezone.utc).isoformat(),
        "source": local, "actual_citation": "unknown",
    }
    if args.live and local["passed"]:
        report["public_http"] = live_audit(local)
    passed = local["passed"] and (not args.live or report["public_http"]["passed"])
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "passed": passed, "locales": local["locale_count"],
        "errors": local["errors"] + report.get("public_http", {}).get("errors", []),
        "actual_citation": "unknown",
    }, ensure_ascii=False))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
