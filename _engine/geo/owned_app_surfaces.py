#!/usr/bin/env python3
"""Discover existing first-party app/task records; never clone pages or publish posts."""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import parse_qs, unquote, urljoin, urlsplit
import xml.etree.ElementTree as ET

from live_app_manifest import roster_digest
from official_locales import OFFICIAL_LOCALES
from site_config import PUBLIC_SITE

HERE = Path(__file__).resolve().parent
LOCALES = ("cs", "hu", "pl", "ro", "ru", "sk", "sl-SI", "tr", "uk", "he")
COUNTRIES = dict(zip(LOCALES, ("cz", "hu", "pl", "ro", "ru", "sk", "si", "tr", "ua", "il")))
CATALOG = "data/lumi-studio-publisher-search-intent-catalog.json"
CATALOG_PAGE = "data/lumi-studio-publisher-search-intent-catalog.html"
API = "api/v1/ios-app-catalog/locales"
FINDER = "data/verified-ios-app-finder-catalog.json"
OUTPUT = "data/owned-app-surfaces-cee.json"
SCHEMA = "lumi.owned-app-surfaces/v1"
MODEL = "gpt-6-astra"
NAMESPACE = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
TEXT_FIELDS = ("publisher_query", "decision_context", "publisher_disclosure", "app_store_cta_label")
SKIP_TEXT = {"script", "style", "template"}
PROOF_RISK = re.compile(
    r"(?:100\s?%|(?:#|№)\s?1\b|guaranteed|гарантирован|гарантован|מובטח"
    r"|תוכל להשיג את המטרה שלך תוך 30 ימים|30 nap alatt biztos|garantat)",
    re.I,
)


class SurfaceError(ValueError):
    pass


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SurfaceError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_unique)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SurfaceError(f"Unavailable JSON source: {path}") from error


def load_roster(path=HERE / "live_app_manifest.json"):
    document = load_json(path)
    apps = document.get("apps")
    if (
        document.get("schema") != "lumi.live-app-roster/v1"
        or document.get("version") != 1
        or not isinstance(apps, dict)
        or len(apps) != 47
        or document.get("roster_digest") != roster_digest(apps)
    ):
        raise SurfaceError("CEE discovery requires the exact canonical47 roster and digest")
    return document


def _url_path(url, site):
    parsed = urlsplit(url)
    base = urlsplit(site.rstrip("/") + "/")
    if (
        parsed.scheme != "https"
        or parsed.netloc != base.netloc
        or parsed.username or parsed.password
        or not parsed.path.startswith(base.path)
        or parsed.query or parsed.fragment
    ):
        raise SurfaceError(f"Not a canonical first-party URL: {url}")
    relative = unquote(parsed.path[len(base.path):])
    if not relative or "\\" in relative or any(p in ("", ".", "..") for p in relative.split("/")):
        raise SurfaceError(f"Unsafe first-party path: {url}")
    return relative


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.lang = ""
        self.direction = ""
        self.canonicals = []
        self.alternates = {}
        self.links = []
        self.text = []
        self._skip = 0
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "html":
            self.lang = attrs.get("lang", "")
            self.direction = attrs.get("dir", "")
        if tag in SKIP_TEXT:
            self._skip += 1
        if tag == "link":
            rel = attrs.get("rel", "").split()
            if "canonical" in rel:
                self.canonicals.append(attrs.get("href", ""))
            if "alternate" in rel and "hreflang" in attrs:
                locale = attrs["hreflang"]
                self.alternates.setdefault(locale, []).append(attrs.get("href", ""))
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])
        if tag == "option" and attrs.get("value"):
            self.links.append(attrs["value"])

    def handle_endtag(self, tag):
        if tag in SKIP_TEXT:
            self._skip = max(0, self._skip - 1)

    def handle_data(self, data):
        if not self._skip:
            self.text.append(data)


def _words(text, names=()):
    value = unicodedata.normalize("NFKC", html.unescape(text)).casefold()
    for name in sorted((n for n in names if n), key=len, reverse=True):
        value = value.replace(unicodedata.normalize("NFKC", name).casefold(), " ")
    return re.findall(r"[^\W\d_]+", value, re.UNICODE)


def text_issues(text, english, locale, names=()):
    """Deterministic fallback checks are not a substitute for a native review."""
    issues = []
    if not isinstance(text, str) or not text.strip():
        return ["empty_native_text"]
    words = _words(text, names)
    base = _words(english or "", names)
    if len(words) >= 3 and words == base:
        issues.append("english_fallback")
    if len(words) >= 7 and len(base) >= 7:
        english_runs = {tuple(base[n:n + 7]) for n in range(len(base) - 6)}
        if any(tuple(words[n:n + 7]) in english_runs for n in range(len(words) - 6)):
            issues.append("english_sentence_leak")
    ranges = {"he": r"[\u0590-\u05ff]", "ru": r"[\u0400-\u052f]", "uk": r"[\u0400-\u052f]"}
    if locale in ranges and not re.search(ranges[locale], text):
        issues.append("missing_native_script")
    if PROOF_RISK.search(text):
        issues.append("unsupported_outcome_claim")
    return sorted(set(issues))


def _store_issues(record, app_id, locale):
    parsed = urlsplit(record.get("app_store_url", ""))
    query = parse_qs(parsed.query, keep_blank_values=True)
    issues = []
    if (
        parsed.scheme != "https" or parsed.netloc != "apps.apple.com"
        or parsed.path != f"/{COUNTRIES[locale]}/app/id{app_id}"
        or parsed.fragment
    ):
        issues.append("wrong_app_store_identity_or_market")
    if (
        len(query.get("pt", [])) != 1 or not query["pt"][0].isdigit()
        or len(query.get("ct", [])) != 1 or not 0 < len(query["ct"][0]) <= 30
    ):
        issues.append("missing_campaign_attribution")
    return issues


def _price_issues(record, model):
    try:
        price = Decimal(str(record["storefront_facts"]["price"]))
        if not price.is_finite() or price < 0 or (price > 0) != (model == "paid_upfront"):
            return ["apple_price_model_mismatch"]
    except (KeyError, ValueError, InvalidOperation):
        return ["missing_apple_price_evidence"]
    return []


def _record_issues(record, reference, app, locale, english, kind):
    issues = []
    app_id = app["app_id"]
    if str(record.get("app_store_id")) != app_id or record.get("verified_live") is not True:
        issues.append("unverified_or_wrong_app_identity")
    name = str(record.get("app_name", record.get("name", "")))
    for edition in ("Pro", "Lite"):
        if re.search(rf"\b{edition}\b", app["name"], re.I) and not re.search(rf"\b{edition}\b", name, re.I):
            issues.append("missing_edition_identity")
    model = record.get("purchase_model")
    if model not in {"paid_upfront", "free_with_lifetime_unlock"} or model != reference.get("purchase_model"):
        issues.append("purchase_model_mismatch")
    if record.get("one_time_option") is not True or reference.get("one_time_option") is not True:
        issues.append("missing_one_time_boundary")
    issues.extend(_store_issues(record, app_id, locale))
    fields = TEXT_FIELDS if kind == "publisher_task_record" else ("summary",)
    names = (name, app["name"], str(english.get("app_name", english.get("name", ""))))
    for field in fields:
        for issue in text_issues(record.get(field), english.get(field, ""), locale, names):
            issues.append(f"{field}:{issue}")
    core = record.get("decision_context" if kind == "publisher_task_record" else "summary", "")
    if len(core.strip()) < 20 or len(_words(core, names)) < 3:
        issues.append("insufficient_native_task_text")
    if kind == "publisher_task_record":
        if (
            record.get("locale") != locale
            or record.get("is_ranking") is not False
            or record.get("measured_search_volume") is not False
            or record.get("query_origin") != "publisher_authored_editorially_localized"
        ):
            issues.append("missing_first_party_proof_disclosure")
        context = record.get("decision_context", "").rstrip()
        if len(context) >= 135 and context[-1:] not in ".!?…\"”":
            issues.append("decision_context:possibly_clipped_sentence")
    else:
        issues.extend(_price_issues(record, model))
    return sorted(set(issues))


def _page_issues(pages, relative, locale, site, sitemaps):
    path = pages / relative
    if not path.is_file():
        return ["missing_page"]
    page = Page(path.read_text(encoding="utf-8"))
    issues = []
    canonical = f"{site}/{relative}"
    if page.lang != locale:
        issues.append("wrong_html_lang")
    if locale == "he" and page.direction.lower() != "rtl":
        issues.append("missing_hebrew_rtl")
    if page.canonicals != [canonical]:
        issues.append("wrong_canonical")
    for alternate in LOCALES:
        expected = f"{site}/{alternate}/{CATALOG_PAGE}"
        if page.alternates.get(alternate) != [expected]:
            issues.append(f"missing_or_wrong_hreflang:{alternate}")
    if canonical not in sitemaps:
        issues.append("missing_sitemap_entry")
    links = {urljoin(canonical, link) for link in page.links}
    if f"{site}/{CATALOG}" not in links:
        issues.append("missing_catalog_download_link")
    return sorted(set(issues))


def _sitemap_urls(pages, site):
    root = pages / "sitemap.xml"
    if not root.is_file():
        raise SurfaceError("Production sitemap.xml is missing")
    seen = set()
    urls = set()
    pending = [root]
    robots = pages / "robots.txt"
    if robots.is_file():
        for line in robots.read_text(encoding="utf-8").splitlines():
            if line.lower().startswith("sitemap:"):
                pending.append(pages / _url_path(line.split(":", 1)[1].strip(), site))
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        try:
            tree = ET.fromstring(path.read_bytes())
        except (OSError, ET.ParseError) as error:
            raise SurfaceError(f"Invalid or missing sitemap: {path.relative_to(pages)}") from error
        if tree.tag == f"{{{NAMESPACE['s']}}}sitemapindex":
            for node in tree.findall("s:sitemap/s:loc", NAMESPACE):
                pending.append(pages / _url_path(node.text or "", site))
        elif tree.tag == f"{{{NAMESPACE['s']}}}urlset":
            urls.update(node.text for node in tree.findall("s:url/s:loc", NAMESPACE))
        else:
            raise SurfaceError(f"Unrecognized sitemap root: {path.name}")
    return urls


def _indexed_records(document, keys, locale, kind):
    field = "records" if kind == "publisher_task_record" else "apps"
    rows = document.get(field)
    if not isinstance(rows, list):
        raise SurfaceError(f"Missing {kind} rows")
    selected = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise SurfaceError(f"Invalid {kind} row")
        if kind == "publisher_task_record" and row.get("locale") != locale:
            continue
        key = row.get("app_key" if kind == "publisher_task_record" else "key")
        if key in selected:
            raise SurfaceError(f"Duplicate {kind} identity: {locale}/{key}")
        selected[key] = (index, row)
    if set(selected) != set(keys):
        raise SurfaceError(f"{kind} must cover canonical47 exactly: {locale}")
    return selected


def discover(pages, *, roster=None, site=PUBLIC_SITE, review=None):
    pages, site = Path(pages), site.rstrip("/")
    roster = roster or load_roster()
    if len(roster["apps"]) != 47 or roster_digest(roster["apps"]) != roster["roster_digest"]:
        raise SurfaceError("Invalid canonical47 roster")
    if not set(LOCALES) <= set(OFFICIAL_LOCALES):
        raise SurfaceError("CEE scope is not an official locale subset")
    keys = sorted(roster["apps"])
    catalog = load_json(pages / CATALOG)
    finder = load_json(pages / FINDER)
    api_index_path = "api/v1/ios-app-catalog/index.json"
    api_index = load_json(pages / api_index_path)
    api_links = {
        entry.get("locale"): entry.get("url")
        for entry in api_index.get("locales", []) if isinstance(entry, dict)
    }
    if set(api_links) != set(OFFICIAL_LOCALES) or api_index.get("record_count") != 47:
        raise SurfaceError("API discovery index must retain exact-50 canonical47 links")
    reference = {row["key"]: row for row in finder.get("apps", [])}
    if set(reference) != set(keys) or len(finder.get("apps", [])) != 47:
        raise SurfaceError("Finder contract does not match canonical47")
    for key, row in reference.items():
        if str(row.get("app_store_id")) != roster["apps"][key]["app_id"]:
            raise SurfaceError(f"Finder App Store ID mismatch: {key}")
    if (
        catalog.get("app_count") != 47 or catalog.get("locale_count") != 50
        or catalog.get("record_count") != 2350 or len(catalog.get("records", [])) != 2350
        or not catalog.get("publisher_disclosure") or catalog.get("is_ranking") is not False
        or catalog.get("measured_search_volume") is not False
    ):
        raise SurfaceError("Existing publisher task catalog lacks its exact-50 first-party contract")
    if {
        (row.get("locale"), row.get("app_key"), str(row.get("app_store_id")))
        for row in catalog["records"]
    } != {
        (locale, key, app["app_id"])
        for locale in OFFICIAL_LOCALES for key, app in roster["apps"].items()
    }:
        raise SurfaceError("Publisher task records do not match canonical47 × official50")
    sitemaps = _sitemap_urls(pages, site)
    english_tasks = _indexed_records(catalog, keys, "en-US", "publisher_task_record")
    english_api = _indexed_records(load_json(pages / API / "en-US.json"), keys, "en-US", "app_catalog_record")
    sources = {
        path: hashlib.sha256((pages / path).read_bytes()).hexdigest()
        for path in (CATALOG, FINDER, api_index_path, f"{API}/en-US.json")
    }
    cells, packet = [], []
    for locale in LOCALES:
        tasks = _indexed_records(catalog, keys, locale, "publisher_task_record")
        api_path = f"{API}/{locale}.json"
        api_document = load_json(pages / api_path)
        if api_document.get("locale") != locale or api_document.get("record_count") != 47:
            raise SurfaceError(f"Wrong locale API catalog: {locale}")
        api = _indexed_records(api_document, keys, locale, "app_catalog_record")
        sources[api_path] = hashlib.sha256((pages / api_path).read_bytes()).hexdigest()
        relative = f"{locale}/{CATALOG_PAGE}"
        page_issues = _page_issues(pages, relative, locale, site, sitemaps)
        sources[relative] = hashlib.sha256((pages / relative).read_bytes()).hexdigest() if (pages / relative).is_file() else None
        task_links = {
            urljoin(f"{site}/{relative}", link)
            for link in Page((pages / relative).read_text()).links
        } if (pages / relative).is_file() else set()
        for key in keys:
            app = roster["apps"][key]
            candidates = []
            for kind, records, english, path, field in (
                ("publisher_task_record", tasks, english_tasks, CATALOG, "records"),
                ("app_catalog_record", api, english_api, api_path, "apps"),
            ):
                index, record = records[key]
                issues = _record_issues(record, reference[key], app, locale, english[key][1], kind)
                issues.extend(_price_issues(api[key][1], reference[key]["purchase_model"]))
                issues.extend(f"catalog_page:{issue}" for issue in page_issues)
                guide_url = record.get("canonical_guide_url", record.get("guide_url", ""))
                if kind == "publisher_task_record" and guide_url not in task_links:
                    issues.append("missing_internal_task_link")
                if kind == "app_catalog_record":
                    if api_links.get(locale) != f"{site}/{api_path}":
                        issues.append("missing_internal_api_link")
                    issues.extend(
                        f"publisher_disclosure:{issue}" for issue in text_issues(
                            tasks[key][1].get("publisher_disclosure"),
                            english_tasks[key][1].get("publisher_disclosure"), locale,
                        )
                    )
                try:
                    guide = _url_path(guide_url, site)
                    if not guide.startswith(f"{locale}/") or not (pages / guide).is_file():
                        issues.append("missing_localized_task_page")
                    if guide_url not in sitemaps:
                        issues.append("missing_task_sitemap_entry")
                except SurfaceError:
                    issues.append("wrong_first_party_task_url")
                candidates.append({
                    "kind": kind, "url": f"{site}/{path}", "json_pointer": f"/{field}/{index}",
                    "record_sha256": digest(record), "issues": sorted(set(issues)),
                    "task_page_url": guide_url,
                    "disclosure_reference": {
                        "url": f"{site}/{CATALOG}",
                        "json_pointer": f"/records/{tasks[key][0]}/publisher_disclosure",
                    },
                })
            selected = next((c for c in candidates if not c["issues"]), None)
            cell = {
                "app_key": key, "app_id": app["app_id"], "locale": locale,
                "owned_locale_asset": "PRESENT",
                "owned_source_checks": "PASS" if selected else "BLOCKED",
                "owned_native": "NOT_REVIEWED",
                "owned_public_readback": "NOT_VERIFIED",
                "catalog_page_url": f"{site}/{relative}",
                "catalog_page_checks": "PASS" if not page_issues else "BLOCKED",
                "catalog_page_issues": page_issues,
                "selected_asset": selected,
                "candidates": candidates,
                "devto_applicability": "N/A",
                "devto_native_receipt": "N/A",
                "devto_reason": "English-only third-party channel; excluded from the CEE owned denominator.",
            }
            cells.append(cell)
            if selected:
                chosen = tasks[key][1] if selected["kind"] == "publisher_task_record" else api[key][1]
                fields = TEXT_FIELDS if selected["kind"] == "publisher_task_record" else ("summary",)
                packet.append({
                    "app_key": key, "app_id": app["app_id"], "locale": locale,
                    "name": chosen.get("app_name", chosen.get("name")),
                    "purchase_model": chosen["purchase_model"],
                    "source_record_sha256": selected["record_sha256"],
                    "native_text": {field: chosen[field] for field in fields},
                    "publisher_disclosure": tasks[key][1]["publisher_disclosure"],
                })
    packet_digest = digest(packet)
    reviewed = (
        isinstance(review, dict) and review.get("schema") == "lumi.owned-native-review/v1"
        and review.get("model") == MODEL and review.get("reasoning_effort") == "max"
        and review.get("roster_digest") == roster["roster_digest"]
        and review.get("packet_digest") == packet_digest
        and review.get("reviewed_cells") == 470 and len(packet) == 470
        and review.get("verdict") == "PASS" and review.get("findings") == []
    )
    if reviewed:
        for cell in cells:
            cell["owned_native"] = "PASS_REVIEWED"
    counts = Counter(cell["owned_source_checks"] for cell in cells)
    result = {
        "schema": SCHEMA, "roster_digest": roster["roster_digest"],
        "definition": "Existing first-party publisher task records or locale API app records, identified by canonical App Store ID and locale. Discovery references existing production assets; it does not clone content.",
        "scope": {"apps": 47, "locales": list(LOCALES), "eligible_cells": 470},
        "source_sha256": dict(sorted(sources.items())),
        "native_review_packet_digest": packet_digest,
        "coverage": {
            "present_cells": len(cells), "source_checks_passed": counts["PASS"],
            "source_checks_blocked": counts["BLOCKED"],
            "native_reviewed_cells": 470 if reviewed else 0,
            "public_readback_verified_cells": 0,
            "devto_eligible_cells": 0, "devto_na_cells": len(cells),
            "new_task_pages": 0, "new_native_catalogs": 0,
        },
        "cells": cells,
    }
    return result, packet


def update_audit(original, discovery):
    """Change owned/dev.to fields only; preserve historical RSS/social/GEO findings."""
    document = json.loads(json.dumps(original))
    rows = document.get("rows")
    if not isinstance(rows, list):
        raise SurfaceError("Audit input must contain rows")
    by_cell = {(c["app_key"], c["locale"]): c for c in discovery["cells"]}
    if len(rows) != 470 or {(r["app_key"], r["locale"]) for r in rows} != set(by_cell):
        raise SurfaceError("Audit and discovery scopes differ")
    for row in rows:
        cell = by_cell[(row["app_key"], row["locale"])]
        if str(row["app_id"]) != cell["app_id"]:
            raise SurfaceError("Audit App Store identity differs")
        for field in ("owned_locale_asset", "owned_native", "owned_source_checks",
                      "owned_public_readback", "devto_applicability", "devto_native_receipt"):
            row[field] = cell[field]
        row["owned_note"] = "Existing first-party catalog record; support/privacy-only discovery was incomplete."
        row["owned_evidence"] = cell["selected_asset"] or cell["candidates"]
    document["owned_discovery"] = {
        "schema": discovery["schema"], "roster_digest": discovery["roster_digest"],
        "coverage": discovery["coverage"],
        "native_review_model": f"{MODEL}/max" if discovery["coverage"]["native_reviewed_cells"] == 470 else None,
        "native_review_packet_digest": discovery["native_review_packet_digest"],
        "historical_other_surfaces_preserved": True,
    }
    return document


def normalize_public_html(body):
    """Undo only Cloudflare's observed email protection, not arbitrary HTML drift."""
    source = body.decode("utf-8")

    def email(encoded):
        value = bytes.fromhex(encoded)
        decoded = bytes(byte ^ value[0] for byte in value[1:]).decode("utf-8")
        # Cloudflare also misidentifies the published versioned skill name as email.
        if not re.fullmatch(r"(?:[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|lumi-app-finder@v\d+\.\d+\.\d+|skills@\d+\.\d+\.\d+)", decoded):
            raise SurfaceError("Invalid Cloudflare email protection")
        return html.escape(decoded, quote=True)

    source = re.sub(
        r'<a href="/cdn-cgi/l/email-protection" class="__cf_email__" data-cfemail="([0-9a-f]+)">\[email&#160;protected\]</a>',
        lambda match: email(match[1]), source,
    )
    source = re.sub(
        r'<span class="__cf_email__" data-cfemail="([0-9a-f]+)">\[email&#160;protected\]</span>',
        lambda match: email(match[1]), source,
    )
    source = re.sub(
        r'href="/cdn-cgi/l/email-protection#([0-9a-f]+)"',
        lambda match: f'href="mailto:{email(match[1])}"', source,
    )
    source = re.sub(
        r'<script data-cfasync="false" src="/cdn-cgi/scripts/[0-9a-f]{8}/cloudflare-static/email-decode\.min\.js"></script>',
        "", source,
    )
    return source.encode("utf-8")


def readback(discovery, *, fetch=None):
    """Read-only, bounded public receipts, separate from source/native validation."""
    from concurrent.futures import ThreadPoolExecutor
    from datetime import datetime, timezone
    import time
    import urllib.error
    if fetch is None:
        from owned_delivery import get
        fetch = get
    site = urlsplit(discovery["cells"][0]["catalog_page_url"])
    prefix = site.path.split(f"/{discovery['cells'][0]['locale']}/", 1)[0]
    base = f"{site.scheme}://{site.netloc}{prefix}"

    def verify(item):
        relative, expected = item
        url = f"{base}/{relative}"
        result = {"url": url, "expected_sha256": expected, "status": "BLOCKED"}
        if not expected:
            return relative, {**result, "reason": "missing_source_asset"}
        for attempt in range(3):
            try:
                response = fetch(url)
                body = response["body"]
                actual = hashlib.sha256(body).hexdigest()
                result.update({
                    "http_status": response["http_status"], "actual_sha256": actual,
                    "final_url": response["final_url"],
                })
                normalized = actual
                if relative.endswith(".html") and actual != expected:
                    normalized = hashlib.sha256(normalize_public_html(body)).hexdigest()
                    result["normalized_sha256"] = normalized
                    result["normalization"] = "cloudflare_email_protection_only"
                if response["http_status"] == 200 and response["final_url"] == url and normalized == expected:
                    result["status"] = "VERIFIED"
                    result.pop("reason", None)
                else:
                    result["reason"] = "public_response_does_not_match_source"
                break
            except (OSError, ValueError, KeyError) as error:
                result["reason"] = type(error).__name__
                if isinstance(error, urllib.error.HTTPError) and error.code not in (429, 500, 502, 503, 504):
                    break
                if attempt < 2:
                    time.sleep(attempt + 1)
        return relative, result

    with ThreadPoolExecutor(max_workers=4) as pool:
        assets = dict(pool.map(verify, discovery["source_sha256"].items()))
    cells = []
    for cell in discovery["cells"]:
        selected = cell["selected_asset"]
        required = [
            CATALOG, FINDER, "api/v1/ios-app-catalog/index.json",
        ]
        if selected:
            required.append(_url_path(selected["url"], base))
        verified = bool(selected) and all(assets[path]["status"] == "VERIFIED" for path in required)
        cells.append({
            "app_key": cell["app_key"], "app_id": cell["app_id"], "locale": cell["locale"],
            "owned_public_readback": "VERIFIED" if verified else "BLOCKED",
            "catalog_page_public_readback": assets[f"{cell['locale']}/{CATALOG_PAGE}"]["status"],
            "devto_applicability": "N/A",
        })
    return {
        "schema": "lumi.owned-app-surfaces-readback/v1",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "discovery_digest": digest(discovery), "assets": dict(sorted(assets.items())),
        "verified_cells": sum(cell["owned_public_readback"] == "VERIFIED" for cell in cells),
        "verified_catalog_pages": sum(
            assets[f"{locale}/{CATALOG_PAGE}"]["status"] == "VERIFIED" for locale in LOCALES
        ),
        "eligible_cells": 470, "devto_eligible_cells": 0, "cells": cells,
    }


def write_json(path, value):
    path = Path(path)
    text = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if not path.is_file() or path.read_text(encoding="utf-8") != text:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=Path, default=HERE / "pages")
    parser.add_argument("--roster", type=Path, default=HERE / "live_app_manifest.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--review-packet", type=Path)
    parser.add_argument("--audit-source", type=Path)
    parser.add_argument("--audit-output", type=Path)
    parser.add_argument("--readback-output", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if bool(args.audit_source) != bool(args.audit_output):
        parser.error("--audit-source and --audit-output must be used together")
    result, packet = discover(
        args.pages, roster=load_roster(args.roster),
        review=load_json(args.review) if args.review else None,
    )
    if args.review and result["coverage"]["native_reviewed_cells"] != 470:
        raise SurfaceError("Native review receipt is stale, incomplete or not a PASS")
    if args.check:
        if load_json(args.output) != result:
            raise SurfaceError("Owned discovery is stale; regenerate from the current source tree")
    else:
        write_json(args.output, result)
    if args.review_packet:
        write_json(args.review_packet, {"packet_digest": digest(packet), "records": packet})
    if args.audit_source:
        write_json(args.audit_output, update_audit(load_json(args.audit_source), result))
    if args.readback_output:
        receipt = readback(result)
        write_json(args.readback_output, receipt)
        print(json.dumps({
            "public_readback_verified_cells": receipt["verified_cells"],
            "byte_verified_catalog_pages": receipt["verified_catalog_pages"],
        }))
        if receipt["verified_cells"] != 470:
            return 1
    print(json.dumps(result["coverage"], sort_keys=True))
    return 1 if result["coverage"]["source_checks_blocked"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
