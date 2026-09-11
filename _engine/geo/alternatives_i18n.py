#!/usr/bin/env python3
"""Materialize the reviewed high-intent alternatives manifest in exact 50 locales.

The route manifest is intentionally small and fixed.  Public copy is never
translated here: every visible sentence comes from the localized publisher
intent catalog or from the matching localized guide's reviewed navigation.
"""

from __future__ import annotations

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
import market_availability as market
import market_surface_policy
import os
from pathlib import Path, PurePosixPath
import re
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlsplit
from uuid import uuid4

import app_store_storefronts
from xml.sax.saxutils import escape as xml_escape

from official_locales import OFFICIAL_LOCALES
from site_config import PUBLIC_SITE


HERE = Path(__file__).resolve().parent
DEFAULT_PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
DEFAULT_MANIFEST = HERE / "alternatives_route_manifest_v1.json"
DEFAULT_UI_I18N = HERE / "publisher_intent_catalog_i18n.json"
DEFAULT_CATALOG_RELATIVE = (
    Path("data") / "lumi-studio-publisher-search-intent-catalog.json"
)
DEFAULT_INVENTORY_RELATIVE = Path("data") / "verified-ios-app-finder-catalog.json"
SITEMAP_RELATIVE = Path("sitemap-alternatives-exact50.xml")
STATE_RELATIVE = Path("data") / "alternatives-exact50" / "owned.json"
OWNER = "lumi-alternatives-exact50-v1"
MANIFEST_SCHEMA = "lumi.alternatives-route-manifest/v1"
STATE_SCHEMA = "lumi.alternatives-owned-output/v1"
QUERY_FAMILY_SUFFIX = " alternative for iphone"
ENGLISH_LOCALES = frozenset({"en-AU", "en-CA", "en-GB", "en-US"})
RTL_LOCALES = frozenset({"ar-SA", "he", "ur-PK"})
PURCHASE_LABEL_SOURCES = {
    "paid_upfront": "Paid download",
    "free_with_lifetime_unlock": "Free to start · one-time unlock",
    "free": "Free",
    "flexible": "Flexible · check listing",
    "neutral": "Check current listing",
}
UI_SOURCES = (
    "Purchase model",
    "Guide",
)
SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
APP_ID_RE = re.compile(r"(?:^|/)id(\d{8,12})(?:$|[/?#])")
OWNER_MARKER = f'data-alternatives-owner="{OWNER}"'


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _json_digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _single_line(value: object, field: str, minimum: int = 1) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be text")
    cleaned = " ".join(value.split())
    if (
        len(cleaned) < minimum
        or "\n" in value
        or "\r" in value
        or "{" in cleaned
        or "}" in cleaned
    ):
        raise ValueError(f"{field} must be substantive single-line text")
    return cleaned


def _safe_relative(value: object, field: str) -> Path:
    text = _single_line(value, field)
    pure = PurePosixPath(text)
    if pure.is_absolute() or ".." in pure.parts or "." in pure.parts:
        raise ValueError(f"{field} must be a safe relative path")
    return Path(*pure.parts)


def _resolve_manifest_source(manifest_path: Path, value: object, field: str) -> Path:
    relative = _safe_relative(value, field)
    return manifest_path.parent / relative


def _expected_selected_pairs(
    evidence: dict[str, Any],
    authority: dict[str, Any],
    minimum_mentions: int,
) -> set[tuple[str, str, int, int | None, str]]:
    apps = authority.get("apps")
    results = evidence.get("results")
    if not isinstance(apps, dict) or not isinstance(results, list):
        raise ValueError("Alternatives evidence or live authority is malformed")
    selected: set[tuple[str, str, int, int | None, str]] = set()
    for result in results:
        if not isinstance(result, dict) or result.get("key") not in apps:
            continue
        key = _single_line(result["key"], "evidence app key")
        query_count = result.get("queries")
        competitors = result.get("top_competitors")
        if type(query_count) is int:
            evidence_kind = "ranked_snapshot"
            if query_count < 1:
                raise ValueError(f"{key}: invalid evidence query count")
        elif (
            query_count is None
            and result.get("gap_queries_note") == "agent-provided (no key)"
            and isinstance(result.get("gap_queries"), list)
            and result["gap_queries"]
        ):
            evidence_kind = "curated_fallback"
        else:
            raise ValueError(f"{key}: invalid evidence provenance")
        if not isinstance(competitors, list):
            raise ValueError(f"{key}: competitor evidence is missing")
        for pair in competitors:
            if (
                not isinstance(pair, list)
                or len(pair) != 2
                or type(pair[1]) is not int
            ):
                raise ValueError(f"{key}: malformed competitor evidence")
            competitor = _single_line(pair[0], f"{key}.competitor")
            mentions = pair[1]
            if mentions >= minimum_mentions:
                selected.add(
                    (
                        key,
                        competitor,
                        mentions,
                        query_count,
                        evidence_kind,
                    )
                )
    return selected


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    document = _read_json(path)
    if document.get("schema") != MANIFEST_SCHEMA or document.get("version") != 1:
        raise ValueError("Alternatives route manifest schema/version differs")

    locales = document.get("official_locales")
    if locales != list(OFFICIAL_LOCALES):
        raise ValueError("Alternatives manifest must use exact OFFICIAL_LOCALES order")
    if document.get("official_locales_sha256") != _json_digest(locales):
        raise ValueError("Alternatives manifest locale digest is invalid")

    evidence_meta = document.get("evidence")
    authority_meta = document.get("authority")
    selection = document.get("selection")
    routes = document.get("routes")
    if not all(
        isinstance(value, dict)
        for value in (evidence_meta, authority_meta, selection)
    ) or not isinstance(routes, list):
        raise ValueError("Alternatives manifest sections are incomplete")

    evidence_path = _resolve_manifest_source(
        path, evidence_meta.get("relative_path"), "evidence.relative_path"
    )
    authority_path = _resolve_manifest_source(
        path, authority_meta.get("relative_path"), "authority.relative_path"
    )
    if (
        not evidence_path.is_file()
        or _file_digest(evidence_path) != evidence_meta.get("sha256")
    ):
        raise ValueError("Alternatives evidence snapshot digest differs")
    if (
        not authority_path.is_file()
        or _file_digest(authority_path) != authority_meta.get("sha256")
    ):
        raise ValueError("Alternatives live authority digest differs")

    evidence = _read_json(evidence_path)
    authority = _read_json(authority_path)
    if (
        evidence.get("date") != evidence_meta.get("snapshot_date")
        or evidence.get("model") != evidence_meta.get("snapshot_model")
        or authority.get("roster_digest") != authority_meta.get("roster_digest")
        or authority_meta.get("roster_count") != len(authority.get("apps", {}))
        or document.get("localized_content_source")
        != DEFAULT_CATALOG_RELATIVE.as_posix()
    ):
        raise ValueError("Alternatives evidence metadata differs")

    minimum_mentions = selection.get("minimum_competitor_mentions")
    if (
        selection.get("policy")
        != "all_authority_live_ranked_or_curated_competitors_at_or_above_historical_score"
        or type(minimum_mentions) is not int
        or minimum_mentions < 1
        or selection.get("route_count") != len(routes)
        or selection.get("locale_count") != len(OFFICIAL_LOCALES)
        or selection.get("expected_page_count")
        != len(routes) * len(OFFICIAL_LOCALES)
    ):
        raise ValueError("Alternatives selection contract differs")

    authority_apps = authority["apps"]
    actual_pairs: set[tuple[str, str, int, int | None, str]] = set()
    route_ids: set[str] = set()
    slugs: set[str] = set()
    previous_route_id = ""
    for route in routes:
        if not isinstance(route, dict):
            raise ValueError("Alternatives route must be an object")
        required = {
            "route_id",
            "app_key",
            "app_store_id",
            "query_family",
            "competitor_key",
            "competitor_name",
            "slug",
            "legacy_source_path",
            "evidence_kind",
            "evidence_mentions",
            "evidence_query_count",
        }
        if set(route) != required:
            raise ValueError("Alternatives route fields differ from contract")
        route_id = _single_line(route["route_id"], "route_id")
        app_key = _single_line(route["app_key"], f"{route_id}.app_key")
        app_id = _single_line(route["app_store_id"], f"{route_id}.app_store_id")
        competitor_key = _single_line(
            route["competitor_key"], f"{route_id}.competitor_key"
        )
        _single_line(route["competitor_name"], f"{route_id}.competitor_name")
        slug = _single_line(route["slug"], f"{route_id}.slug")
        legacy_path = _safe_relative(
            route["legacy_source_path"], f"{route_id}.legacy_source_path"
        )
        mentions = route["evidence_mentions"]
        query_count = route["evidence_query_count"]
        evidence_kind = route["evidence_kind"]
        if (
            route_id != f"alternative:{app_key}:{slug}"
            or route["query_family"] != competitor_key + QUERY_FAMILY_SUFFIX
            or SLUG_RE.fullmatch(slug) is None
            or not slug.startswith(f"{app_key}-vs-")
            or legacy_path != Path("alternatives") / f"{slug}.html"
            or type(mentions) is not int
            or mentions < minimum_mentions
            or evidence_kind not in {"ranked_snapshot", "curated_fallback"}
            or (
                evidence_kind == "ranked_snapshot"
                and (
                    type(query_count) is not int
                    or query_count < 1
                )
            )
            or (
                evidence_kind == "curated_fallback"
                and query_count is not None
            )
        ):
            raise ValueError(f"Invalid alternatives route identity: {route_id}")
        authority_app = authority_apps.get(app_key)
        if (
            not isinstance(authority_app, dict)
            or str(authority_app.get("app_id")) != app_id
        ):
            raise ValueError(f"Wrong authority owner for {route_id}")
        if route_id <= previous_route_id:
            raise ValueError("Alternatives routes must be sorted by route_id")
        previous_route_id = route_id
        if route_id in route_ids or slug in slugs:
            raise ValueError("Alternatives manifest repeats a route or slug")
        route_ids.add(route_id)
        slugs.add(slug)
        actual_pairs.add(
            (
                app_key,
                competitor_key,
                mentions,
                query_count,
                evidence_kind,
            )
        )

    expected_pairs = _expected_selected_pairs(
        evidence, authority, minimum_mentions
    )
    if actual_pairs != expected_pairs:
        missing = sorted(expected_pairs - actual_pairs)
        extra = sorted(actual_pairs - expected_pairs)
        raise ValueError(
            "Alternatives manifest differs from fixed evidence selection: "
            f"missing={missing[:5]} extra={extra[:5]}"
        )
    return document


def load_inventory(path: Path, manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    payload = _read_json(path)
    raw_apps = payload.get("apps")
    if not isinstance(raw_apps, list):
        raise ValueError(f"Verified app inventory is malformed: {path}")
    apps: dict[str, dict[str, Any]] = {}
    for raw in raw_apps:
        if not isinstance(raw, dict) or not raw.get("key"):
            raise ValueError(f"Verified app inventory has an invalid record: {path}")
        key = str(raw["key"])
        if key in apps:
            raise ValueError(f"Verified app inventory repeats {key}")
        apps[key] = raw

    for route in manifest["routes"]:
        key = route["app_key"]
        app = apps.get(key)
        if (
            not isinstance(app, dict)
            or app.get("verified_live") is not True
            or str(app.get("app_store_id")) != route["app_store_id"]
            or not isinstance(app.get("capabilities"), dict)
            or not isinstance(app.get("one_time_option"), bool)
            or app.get("purchase_model") not in PURCHASE_LABEL_SOURCES
        ):
            raise ValueError(f"Verified inventory owner differs for {key}")
    return apps


def _validated_campaign_url(value: object, app_id: str) -> str:
    url = _single_line(value, "app_store_url")
    parsed = urlsplit(url)
    match = APP_ID_RE.search(parsed.path)
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "apps.apple.com"
        or match is None
        or match.group(1) != app_id
        or parsed.fragment
        or len(pairs) != 3
        or [key for key, _ in pairs] != ["pt", "ct", "mt"]
        or not pairs[0][1].isdigit()
        or not pairs[1][1]
        or len(pairs[1][1]) > 30
        or pairs[2][1] != "8"
    ):
        raise ValueError(f"Incomplete or wrong App Store attribution: {url}")
    return url


def load_catalog(
    path: Path,
    manifest: dict[str, Any],
    inventory: dict[str, dict[str, Any]],
    site: str,
) -> dict[tuple[str, str], dict[str, Any]]:
    payload = _read_json(path)
    if (
        payload.get("locale_count") != len(OFFICIAL_LOCALES)
        or payload.get("locales") != list(OFFICIAL_LOCALES)
        or not isinstance(payload.get("records"), list)
    ):
        raise ValueError("Publisher intent catalog locale coverage differs")

    selected_keys = {route["app_key"] for route in manifest["routes"]}
    records: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in payload["records"]:
        if not isinstance(raw, dict) or raw.get("app_key") not in selected_keys:
            continue
        key = str(raw["app_key"])
        locale = str(raw.get("locale", ""))
        identity = (key, locale)
        if locale not in OFFICIAL_LOCALES or identity in records:
            raise ValueError(f"Invalid publisher intent identity: {identity}")
        route_owner = inventory[key]
        app_id = str(route_owner["app_store_id"])
        for field in (
            "app_name",
            "publisher_query",
            "decision_context",
            "source_persona_query",
            "canonical_guide_url",
            "app_store_cta_label",
            "publisher_disclosure",
        ):
            _single_line(raw.get(field), f"{key}/{locale}.{field}", 2)
        if (
            str(raw.get("app_store_id")) != app_id
            or raw.get("purchase_model") != route_owner["purchase_model"]
            or raw.get("one_time_option") is not route_owner["one_time_option"]
            or raw.get("query_origin")
            != "publisher_authored_editorially_localized"
            or raw.get("measured_search_volume") is not False
            or raw.get("is_ranking") is not False
            or raw.get("verified_live") is not True
            or raw.get("canonical_app_store_url")
            != app_store_storefronts.canonical_app_store_url_for(app_id, locale)
            # 沒有可驗證市場時權威回 None,紀錄也必須是 null:寧可沒有連結,
            # 也不可放一個會把讀者送去別國商店的 URL。
        ):
            raise ValueError(f"Untruthful publisher intent record: {identity}")
        guide_prefix = f"{site}/{locale}/"
        if not str(raw["canonical_guide_url"]).startswith(guide_prefix):
            raise ValueError(f"Wrong localized guide canonical: {identity}")
        if market.validate_record(raw):
            _validated_campaign_url(raw["app_store_url"], app_id)
        records[identity] = raw

    expected = {
        (key, locale)
        for key in selected_keys
        for locale in OFFICIAL_LOCALES
    }
    if set(records) != expected:
        missing = sorted(expected - set(records))
        extra = sorted(set(records) - expected)
        raise ValueError(
            "Publisher intent records are not exact route-app × locale coverage: "
            f"missing={missing[:5]} extra={extra[:5]}"
        )

    for key in selected_keys:
        english = records[(key, "en-US")]
        for locale in OFFICIAL_LOCALES:
            if locale in ENGLISH_LOCALES:
                continue
            record = records[(key, locale)]
            for field in (
                "publisher_query",
                "decision_context",
                "app_store_cta_label",
                "publisher_disclosure",
            ):
                if record[field].strip() == english[field].strip():
                    raise ValueError(
                        f"English fallback in {key}/{locale}.{field}"
                    )
    return records


def load_ui_i18n(path: Path = DEFAULT_UI_I18N) -> dict[str, dict[str, str]]:
    payload = _read_json(path)
    localizations = payload.get("localizations")
    if not isinstance(localizations, dict) or set(localizations) != set(
        OFFICIAL_LOCALES
    ):
        raise ValueError("Publisher intent UI locale coverage differs")
    required = {*UI_SOURCES, *PURCHASE_LABEL_SOURCES.values()}
    output: dict[str, dict[str, str]] = {}
    for locale in OFFICIAL_LOCALES:
        mapping = localizations.get(locale)
        if not isinstance(mapping, dict) or not required.issubset(mapping):
            raise ValueError(f"Publisher intent UI strings are missing: {locale}")
        output[locale] = {
            source: _single_line(
                mapping[source], f"publisher UI {locale}/{source}", 2
            )
            for source in required
        }
    return output


def _relative_site_path(url: str, site: str) -> Path:
    prefix = site.rstrip("/") + "/"
    if not url.startswith(prefix):
        raise ValueError(f"URL is outside the public site: {url}")
    return _safe_relative(url[len(prefix) :], "canonical_guide_url")


class _AlternativesLabelParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.capture = False
        self.depth = 0
        self.parts: list[str] = []
        self.labels: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if self.capture:
            self.depth += 1
            return
        if tag != "a":
            return
        href = dict(attrs).get("href") or ""
        path = urlsplit(href).path.rstrip("/")
        if path.endswith("/alternatives") or path.endswith(
            "/alternatives/index.html"
        ):
            self.capture = True
            self.depth = 1
            self.parts = []

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self.capture:
            return
        self.depth -= 1
        if self.depth == 0:
            label = " ".join("".join(self.parts).split())
            if label:
                self.labels.append(label)
            self.capture = False
            self.parts = []


def localized_alternatives_labels(
    pages: Path,
    manifest: dict[str, Any],
    records: dict[tuple[str, str], dict[str, Any]],
    site: str,
) -> dict[str, str]:
    first_key = min(route["app_key"] for route in manifest["routes"])
    labels: dict[str, str] = {}
    for locale in OFFICIAL_LOCALES:
        record = records[(first_key, locale)]
        guide = pages / _relative_site_path(record["canonical_guide_url"], site)
        if not guide.is_file():
            raise ValueError(f"Localized guide is missing: {guide}")
        parser = _AlternativesLabelParser()
        parser.feed(guide.read_text(encoding="utf-8"))
        unique = sorted(set(parser.labels))
        if len(unique) != 1:
            raise ValueError(
                f"Localized alternatives label is ambiguous: {locale}={unique}"
            )
        labels[locale] = _single_line(
            unique[0], f"{locale}.alternatives_label", 2
        )
    return labels


def validate_legacy_routes(
    pages: Path,
    manifest: dict[str, Any],
    inventory: dict[str, dict[str, Any]],
    site: str,
) -> None:
    for route in manifest["routes"]:
        source = pages / _safe_relative(
            route["legacy_source_path"],
            f"{route['route_id']}.legacy_source_path",
        )
        if not source.is_file():
            raise ValueError(f"Curated root alternative is missing: {source}")
        document = source.read_text(encoding="utf-8")
        canonical = (
            f'<link rel="canonical" '
            f'href="{site}/alternatives/{route["slug"]}.html">'
        )
        if (
            canonical not in document
            or f"id{route['app_store_id']}" not in document
            or route["competitor_name"].casefold()
            not in html.unescape(re.sub(r"<[^>]+>", " ", document)).casefold()
            or str(inventory[route["app_key"]]["name"]).casefold()
            not in html.unescape(re.sub(r"<[^>]+>", " ", document)).casefold()
        ):
            raise ValueError(
                f"Curated root alternative ownership differs: {source}"
            )


def _hreflang(route: dict[str, Any], site: str) -> str:
    links = [
        (
            f'<link rel="alternate" hreflang="{html.escape(locale)}" '
            f'href="{html.escape(site)}/{html.escape(locale)}/alternatives/'
            f'{html.escape(route["slug"])}.html">'
        )
        for locale in OFFICIAL_LOCALES
    ]
    links.append(
        f'<link rel="alternate" hreflang="x-default" '
        f'href="{html.escape(site)}/en-US/alternatives/'
        f'{html.escape(route["slug"])}.html">'
    )
    return "\n".join(links)


def _capabilities_json(app: dict[str, Any]) -> str:
    capabilities = app["capabilities"]
    normalized = {
        str(key): bool(value)
        for key, value in sorted(capabilities.items())
    }
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).replace("</", "<\\/")


def render_page(
    route: dict[str, Any],
    locale: str,
    record: dict[str, Any],
    app: dict[str, Any],
    ui: dict[str, str],
    alternatives_label: str,
    site: str,
) -> str:
    available = market.validate_record(record)
    canonical = f"{site}/{locale}/alternatives/{route['slug']}.html"
    title = (
        f"{route['competitor_name']} · {alternatives_label}: "
        f"{record['publisher_query']}"
    )
    purchase_label = ui[PURCHASE_LABEL_SOURCES[record["purchase_model"]]]
    capabilities = _capabilities_json(app)
    schema = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": record["app_name"],
        "identifier": {
            "@type": "PropertyValue",
            "propertyID": "Apple App Store ID",
            "value": record["app_store_id"],
        },
        "url": canonical,
        "sameAs": record["canonical_app_store_url"],
        "installUrl": record["app_store_url"],
        "description": record["decision_context"],
        "inLanguage": locale,
    }
    schema_text = json.dumps(
        schema,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    direction = ' dir="rtl"' if locale in RTL_LOCALES else ""
    if not available:
        schema.pop("sameAs")
        schema.pop("installUrl")
        schema.update(market.record_fields(locale))
        schema_text = json.dumps(schema, ensure_ascii=False, sort_keys=True, separators=(",", ":")).replace("</", "<\\/")
    store_block = (
        f'<p><a class="cta" href="{html.escape(record["app_store_url"], quote=True)}" '
        f'rel="nofollow noopener">{html.escape(record["app_store_cta_label"])}</a></p>'
        if available else market.note_html(locale, record["app_name"])
    )
    document = f"""<!DOCTYPE html>
<html lang="{html.escape(locale)}"{direction}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="{OWNER}">
<meta name="lumi-query-family" content="{html.escape(route["query_family"])}">
<meta name="lumi-privacy-source" content="verified-ios-app-finder-catalog">
<title>{html.escape(title)}</title>
<meta name="description" content="{html.escape(record["decision_context"])}">
<link rel="canonical" href="{html.escape(canonical)}">
{_hreflang(route, site)}
<script type="application/ld+json">{schema_text}</script>
<style>
body{{margin:0;font:17px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#171526;background:#fffafd}}
main{{width:min(760px,calc(100% - 40px));margin:0 auto;padding:64px 0 80px}}
.eyebrow{{font-weight:700;color:#7d42ba;letter-spacing:.02em}}
h1{{font-size:clamp(2rem,6vw,3.75rem);line-height:1.08;margin:.25em 0 .55em}}
.lead{{font-size:1.18rem}}
.facts{{display:grid;gap:12px;margin:28px 0}}
.fact{{padding:16px 18px;border:1px solid #eadff2;border-radius:18px;background:#fff}}
.fact strong{{display:block;margin-bottom:4px}}
.cta{{display:inline-block;padding:13px 19px;border-radius:999px;color:#fff;background:linear-gradient(135deg,#ce5fe8,#5a9efa);text-decoration:none;font-weight:700}}
.disclosure{{margin-top:36px;font-size:.9rem;color:#5e5968}}
</style>
</head>
<body>
<main {OWNER_MARKER}
 data-route-id="{html.escape(route["route_id"])}"
 data-app-key="{html.escape(route["app_key"])}"
 data-app-store-id="{html.escape(route["app_store_id"])}"
 data-query-family="{html.escape(route["query_family"])}"
 data-purchase-model="{html.escape(record["purchase_model"])}"
 data-one-time-option="{str(record["one_time_option"]).lower()}">
<p class="eyebrow">{html.escape(alternatives_label)}</p>
<h1>{html.escape(route["competitor_name"])} · {html.escape(record["publisher_query"])}</h1>
<p class="lead">{html.escape(record["decision_context"])}</p>
<div class="facts">
<div class="fact"><strong>{html.escape(ui["Purchase model"])}</strong>{html.escape(purchase_label)}</div>
</div>
{store_block}
<p><a href="{html.escape(record["canonical_guide_url"], quote=True)}">{html.escape(ui["Guide"])}</a></p>
<p class="disclosure">{html.escape(record["publisher_disclosure"])}</p>
<script type="application/json" data-lumi-verified-capabilities>{capabilities}</script>
</main>
</body>
</html>
"""
    return market_surface_policy.enforce_html(document, locale)


def render_sitemap(urls: Iterable[str]) -> str:
    entries = "\n".join(
        f"  <url><loc>{xml_escape(url)}</loc></url>"
        for url in sorted(urls)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{entries}\n"
        "</urlset>\n"
    )


def _state_text(
    manifest_path: Path,
    page_paths: Iterable[Path],
) -> str:
    paths = tuple(page_paths)
    document = {
        "schema": STATE_SCHEMA,
        "owner": OWNER,
        "manifest_sha256": _file_digest(manifest_path),
        "page_count": len(paths),
        "pages": sorted(path.as_posix() for path in paths),
        "sitemap": SITEMAP_RELATIVE.as_posix(),
    }
    return json.dumps(
        document,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    ) + "\n"


def _atomic_write_text(path: Path, text: str) -> bool:
    encoded = text.encode("utf-8")
    if path.is_file() and path.read_bytes() == encoded:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return True


def _load_previous_owned(pages: Path) -> set[Path]:
    state_path = pages / STATE_RELATIVE
    if state_path.is_file():
        state = _read_json(state_path)
        if (
            state.get("schema") != STATE_SCHEMA
            or state.get("owner") != OWNER
            or not isinstance(state.get("pages"), list)
        ):
            raise ValueError(f"Alternatives owned-output state is invalid: {state_path}")
        return {
            _safe_relative(value, "owned page")
            for value in state["pages"]
        }

    discovered: set[Path] = set()
    for path in pages.glob("*/alternatives/*.html"):
        try:
            document = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        if OWNER_MARKER in document:
            discovered.add(path.relative_to(pages))
    return discovered


def prepare_generation(
    *,
    pages: Path,
    manifest_path: Path,
    catalog_path: Path,
    inventory_path: Path,
    ui_i18n_path: Path,
    site: str,
) -> tuple[
    dict[Path, str],
    str,
    str,
    dict[str, int],
]:
    site = site.rstrip("/")
    manifest = load_manifest(manifest_path)
    inventory = load_inventory(inventory_path, manifest)
    records = load_catalog(catalog_path, manifest, inventory, site)
    ui_i18n = load_ui_i18n(ui_i18n_path)
    validate_legacy_routes(pages, manifest, inventory, site)
    alternatives_labels = localized_alternatives_labels(
        pages, manifest, records, site
    )

    rendered: dict[Path, str] = {}
    urls: list[str] = []
    for route in manifest["routes"]:
        app = inventory[route["app_key"]]
        for locale in OFFICIAL_LOCALES:
            relative = (
                Path(locale) / "alternatives" / f"{route['slug']}.html"
            )
            rendered[relative] = render_page(
                route,
                locale,
                records[(route["app_key"], locale)],
                app,
                ui_i18n[locale],
                alternatives_labels[locale],
                site,
            )
            urls.append(
                f"{site}/{locale}/alternatives/{route['slug']}.html"
            )

    sitemap = render_sitemap(urls)
    state = _state_text(manifest_path, rendered)
    stats = {
        "routes": len(manifest["routes"]),
        "locales": len(OFFICIAL_LOCALES),
        "pages": len(rendered),
    }
    return rendered, sitemap, state, stats


def build(
    *,
    pages: Path = DEFAULT_PAGES,
    manifest_path: Path = DEFAULT_MANIFEST,
    catalog_path: Path | None = None,
    inventory_path: Path | None = None,
    ui_i18n_path: Path = DEFAULT_UI_I18N,
    site: str = PUBLIC_SITE,
    check: bool = False,
    validate_only: bool = False,
) -> dict[str, int]:
    pages = pages.resolve()
    catalog_path = catalog_path or pages / DEFAULT_CATALOG_RELATIVE
    inventory_path = inventory_path or pages / DEFAULT_INVENTORY_RELATIVE
    rendered, sitemap, state, stats = prepare_generation(
        pages=pages,
        manifest_path=manifest_path,
        catalog_path=catalog_path,
        inventory_path=inventory_path,
        ui_i18n_path=ui_i18n_path,
        site=site,
    )
    expected_paths = set(rendered)
    previous_owned = _load_previous_owned(pages)
    stale = previous_owned - expected_paths
    if validate_only:
        return {**stats, "changed": 0, "pruned": len(stale)}

    expected_bytes = {
        relative: text.encode("utf-8")
        for relative, text in rendered.items()
    }
    if check:
        drifted = [
            relative.as_posix()
            for relative, content in expected_bytes.items()
            if not (pages / relative).is_file()
            or (pages / relative).read_bytes() != content
        ]
        if (
            drifted
            or not (pages / SITEMAP_RELATIVE).is_file()
            or (pages / SITEMAP_RELATIVE).read_text(encoding="utf-8")
            != sitemap
            or not (pages / STATE_RELATIVE).is_file()
            or (pages / STATE_RELATIVE).read_text(encoding="utf-8") != state
            or stale
        ):
            raise ValueError(
                "Alternatives exact-50 output drift: "
                f"pages={drifted[:5]} stale={sorted(map(str, stale))[:5]}"
            )
        return {**stats, "changed": 0, "pruned": 0}

    changed = 0
    for relative in sorted(rendered, key=lambda item: item.as_posix()):
        changed += int(_atomic_write_text(pages / relative, rendered[relative]))
    changed += int(_atomic_write_text(pages / SITEMAP_RELATIVE, sitemap))

    pruned = 0
    for relative in sorted(stale, key=lambda item: item.as_posix()):
        target = pages / relative
        if not target.is_file():
            continue
        document = target.read_text(encoding="utf-8")
        if OWNER_MARKER not in document:
            raise ValueError(f"Refusing to prune unowned page: {target}")
        target.unlink()
        pruned += 1
    changed += int(_atomic_write_text(pages / STATE_RELATIVE, state))
    return {**stats, "changed": changed, "pruned": pruned}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-dir", type=Path, default=DEFAULT_PAGES)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--ui-i18n", type=Path, default=DEFAULT_UI_I18N)
    parser.add_argument("--site", default=PUBLIC_SITE)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    if args.check and args.validate_only:
        parser.error("--check and --validate-only are mutually exclusive")
    stats = build(
        pages=args.pages_dir,
        manifest_path=args.manifest,
        catalog_path=args.catalog,
        inventory_path=args.inventory,
        ui_i18n_path=args.ui_i18n,
        site=args.site,
        check=args.check,
        validate_only=args.validate_only,
    )
    print(
        "alternatives-exact50: "
        + " ".join(f"{key}={value}" for key, value in stats.items())
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
