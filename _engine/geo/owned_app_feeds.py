#!/usr/bin/env python3
"""Exact-roster owned feeds, generated offline from one catalog generation."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from email.utils import format_datetime
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET

import market_availability as market
from official_locales import OFFICIAL_LOCALES, require_official_locale_coverage
from owned_feed_locale_gate import validate_summary, validate_text
from rsscloud_config import (
    RSSCLOUD_DOMAIN, RSSCLOUD_NOTIFY_PATH, RSSCLOUD_PORT, RSSCLOUD_PROTOCOL,
)
from site_config import PUBLIC_SITE
from websub_config import WEBSUB_HUBS

HERE = Path(__file__).resolve().parent
SITE = os.environ.get("GEO_SITE", PUBLIC_SITE).rstrip("/")
SCHEMA = "lumi.owned-app-feeds/v2"
INDEX = Path("feeds/owned-apps.json")
DIRECTORY = Path("feeds/index.html")
SITEMAP = Path("sitemap_owned_feeds.xml")
CATALOG = Path("api/v1/ios-app-catalog")
FORMATS = {
    "atom": ("feed.xml", "application/atom+xml"),
    "rss": ("rss.xml", "application/rss+xml"),
    "json_feed": ("feed.json", "application/feed+json"),
}
CONTENT_TYPES = {
    "atom": {"application/atom+xml", "application/xml", "text/xml"},
    "rss": {"application/rss+xml", "application/xml", "text/xml"},
    "json_feed": {"application/feed+json", "application/json"},
}
ATOM = "http://www.w3.org/2005/Atom"
CONTENT = "http://purl.org/rss/1.0/modules/content/"
LUMI = "https://open.cait518.cc/ns/owned-feed"
XML = "http://www.w3.org/XML/1998/namespace"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
SHA256 = re.compile(r"[0-9a-f]{64}")
MAX_BYTES = 1_000_000
HEAD_START = "<!-- owned-app-feeds:start -->"
HEAD_END = "<!-- owned-app-feeds:end -->"
DISCLOSURE = (
    "This is first-party material published by Lumi Studio, the developer of "
    "every listed app."
)
PURCHASE_LABELS = {
    "paid_upfront": "Paid download",
    "free_with_lifetime_unlock": "Free to start · one-time unlock",
}
SOURCE_FILES = (
    "owned_app_feeds.py", "owned_feed_locale_gate.py", "owned_feed_delivery.py",
    "owned_feed_receipts.py", "owned_feed_receipt.schema.json",
    "owned_feed_reconciliation.py",
    "owned_feed_public_capture.py",
    "owned_feed_release.py", "notification_release.py", "notification_policy.json",
    "notify_websub.py", "notify_rsscloud.py", "indexnow_submit.py",
    "deployment_generation.py", "gen_sitemap_lastmod.py",
    "portfolio_app_catalog_api.py", "build_pages_i18n.py", "external_app_locales.py",
    "gen_publisher_disclosures.py",
    "publisher_intent_catalog_i18n.json", "portfolio_app_finder_i18n.json",
    "live_app_manifest.json", "market_availability.py", "official_locales.py",
    "app_store_storefronts.py", "locale_storefronts.json",
    "websub_config.py", "rsscloud_config.py", "site_config.py",
    "../social/videogen/registry.py",
)


def digest(value) -> str:
    return sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8"))


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def decode(raw: bytes):
    return json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object)


def read_json(path: Path):
    return decode(path.read_bytes())


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode("utf-8")


def timestamp(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value
    ):
        raise ValueError(f"Invalid feed timestamp: {value!r}")
    datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def url(path: Path | str) -> str:
    return f"{SITE}/{path}"


def feed_path(locale: str, fmt: str) -> Path:
    if locale not in OFFICIAL_LOCALES or fmt not in FORMATS:
        raise ValueError("Unsupported owned feed")
    return Path(locale) / FORMATS[fmt][0]


def expected_feed_paths() -> set[Path]:
    return {feed_path(locale, fmt) for locale in OFFICIAL_LOCALES for fmt in FORMATS}


def present_feed_paths(pages: Path) -> set[Path]:
    return {
        folder.relative_to(pages) / filename
        for folder in pages.iterdir() if folder.is_dir() and not folder.name.startswith(".")
        for filename, _ in FORMATS.values() if (folder / filename).is_file()
    }


def item_id(app_id: str, locale: str) -> str:
    return f"urn:lumi:app-store:{app_id}:locale:{locale}"


def source_hashes(source: Path) -> dict:
    return {name: sha256((source / name).read_bytes()) for name in SOURCE_FILES}


def require_parity(source: Path, reference: Path) -> None:
    left, right = source_hashes(source), source_hashes(reference)
    drift = [name for name in left if left[name] != right[name]]
    if drift:
        raise ValueError(f"Paired source drift: {', '.join(drift)}")


def load_copy(source: Path) -> dict:
    publisher = read_json(source / "publisher_intent_catalog_i18n.json")
    finder = read_json(source / "portfolio_app_finder_i18n.json")
    for document in (publisher, finder):
        if document.get("schema_version") != 1:
            raise ValueError("Unexpected feed localization schema")
        require_official_locale_coverage("feed copy", document["localizations"])
    copies = {}
    for locale in OFFICIAL_LOCALES:
        p, f = publisher["localizations"][locale], finder["localizations"][locale]
        copy = {
            "disclosure": p[DISCLOSURE],
            "cta": f["View on the App Store"],
            **{model: p[label] for model, label in PURCHASE_LABELS.items()},
        }
        for field, value in copy.items():
            validate_text(locale, value, field)
            if not locale.startswith("en-") and value in {
                DISCLOSURE, "View on the App Store", *PURCHASE_LABELS.values()
            }:
                raise ValueError(f"English wrapper fallback: {locale}/{field}")
        copies[locale] = copy
    return copies


def load_sources(pages: Path, source: Path) -> tuple[dict, dict, dict]:
    from live_app_manifest import canonical_manifest
    from app_store_storefronts import validated_app_store_url
    import build_pages_i18n
    sys.path.insert(0, str(source.parent / "social"))
    from videogen.registry import APPS, APPSTORE

    roster = canonical_manifest()
    if read_json(source / "live_app_manifest.json") != roster:
        raise ValueError("Feed source roster differs from the loaded canonical roster")
    keys = set(roster["apps"])
    copies = load_copy(source)
    index = read_json(pages / CATALOG / "index.json")
    require_official_locale_coverage(
        "catalog inputs", {p.stem for p in (pages / CATALOG / "locales").glob("*.json")}
    )
    if index.get("record_count") != len(keys) or index.get("locale_count") != 50:
        raise ValueError("Catalog inventory differs from canonical roster")
    localized, channels = {}, {}
    for locale in OFFICIAL_LOCALES:
        catalog = read_json(pages / CATALOG / "locales" / f"{locale}.json")
        source_feed = read_json(pages / CATALOG / "feeds" / f"{locale}.json")
        apps = catalog.get("apps")
        if (
            catalog.get("locale") != locale
            or catalog.get("record_count") != len(keys)
            or catalog.get("content_digest") != index.get("content_digest")
            or not isinstance(apps, list) or len(apps) != len(keys)
            or source_feed.get("language") != locale
            or source_feed.get("_lumi_catalog", {}).get("contentDigest") != index.get("content_digest")
        ):
            raise ValueError(f"Mixed catalog generation: {locale}")
        localized[locale] = apps
        records = {}
        copy = copies[locale]
        for app in apps:
            key = app.get("key")
            if key not in keys or key in records:
                raise ValueError(f"Duplicate/non-roster App: {locale}/{key}")
            app_id = roster["apps"][key]["app_id"]
            model = app.get("purchase_model")
            if (
                app.get("app_store_id") != app_id
                or str(APPSTORE.get(key)) != app_id
                or model not in PURCHASE_LABELS
                or model != APPS[key].get("purchase_model")
                or app.get("one_time_option") is not True
                or app.get("verified_live") is not True
            ):
                raise ValueError(f"App identity/purchase drift: {locale}/{key}")
            canonical = url(f"{locale}/{key}.html")
            if app.get("guide_url") != canonical:
                raise ValueError(f"Canonical locale drift: {locale}/{key}")
            title, summary = app.get("name"), app.get("summary")
            validate_text(locale, title, f"{key}/name", require_native=False)
            validate_summary(locale, summary, model)
            native = build_pages_i18n.external_localized_values(key, locale)
            native_summary = next(
                (" ".join(p.split()) for p in re.split(r"\n\s*\n", native["description"])
                 if len(" ".join(p.split())) >= 20), "",
            )
            if title != build_pages_i18n._single_line(native["name"]) or summary != native_summary:
                raise ValueError(f"Stale catalog localization source: {locale}/{key}")
            available = market.validate_record(
                {**app, "locale": locale}, url_fields=("app_store_url",)
            )
            metadata = {
                "app_key": key, "app_store_id": app_id,
                "purchase_model": model, "purchase_label": copy[model],
                "one_time_option": True, "independent_ranking": False,
                "publisher_disclosure": copy["disclosure"],
                "source_locale": locale,
            }
            record = {
                "id": item_id(app_id, locale), "url": canonical,
                "title": title, "summary": summary, "language": locale,
                "_owned_app": metadata,
            }
            if available:
                direct = validated_app_store_url(
                    app["app_store_url"], expected_app_id=app_id,
                    expected_locale=locale, require_campaign=True,
                )
                record["external_url"] = direct
                metadata["app_store_cta_label"] = copy["cta"]
            else:
                if any(field in app for field in ("storefront_facts", "price", "currency")):
                    raise ValueError(f"Storefront facts in unavailable market: {locale}/{key}")
                metadata.update(market.record_fields(locale, app_id))
                metadata["availability_note"] = market.note(locale, app_id=app_id)
                validate_text(locale, metadata["availability_note"], "market notice")
            parts = [summary, copy[model]]
            markup = [f"<p>{html.escape(part)}</p>" for part in parts]
            if available:
                parts.append(f'{copy["cta"]}: {direct}')
                markup.append(
                    f'<p><a href="{html.escape(direct, quote=True)}">'
                    f'{html.escape(copy["cta"])}</a></p>'
                )
            else:
                parts.append(metadata["availability_note"])
                markup.append(f'<p>{html.escape(metadata["availability_note"])}</p>')
            parts.append(copy["disclosure"])
            markup.append(f'<p>{html.escape(copy["disclosure"])}</p>')
            record["content_text"] = "\n\n".join(parts)
            record["content_html"] = "".join(markup)
            records[key] = record
        if set(records) != keys:
            raise ValueError(f"Incomplete owned-feed roster: {locale}")
        title = source_feed.get("title")
        validate_text(locale, title, "channel title")
        channels[locale] = {
            "title": title, "disclosure": copy["disclosure"],
            "items": [records[key] for key in sorted(keys)],
        }
    actual_digest = digest({"api_version": index["api_version"], "localized": localized})
    if actual_digest != index.get("content_digest"):
        raise ValueError("Catalog content digest does not match source records")
    english = {a["_owned_app"]["app_key"]: a["summary"] for a in channels["en-US"]["items"]}
    for locale, channel in channels.items():
        if not locale.startswith("en-"):
            for item in channel["items"]:
                if item["summary"] == english[item["_owned_app"]["app_key"]]:
                    raise ValueError(f"English summary fallback: {locale}/{item['id']}")
    source_state = {
        "catalog_content_digest": actual_digest,
        "roster_digest": roster["roster_digest"],
        "source_files": source_hashes(source),
    }
    return roster, channels, source_state


def item_digest(item: dict) -> str:
    clean = {k: v for k, v in item.items() if k not in ("date_published", "date_modified")}
    clean["_owned_app"] = {k: v for k, v in clean["_owned_app"].items() if k != "content_digest"}
    return digest(clean)


def previous_items(pages: Path, locale: str) -> dict:
    path = pages / feed_path(locale, "json_feed")
    if not path.exists():
        return {}
    previous = read_json(path)
    if previous.get("_owned_feed", {}).get("schema") != SCHEMA or previous.get("language") != locale:
        raise ValueError(f"Refusing to overwrite an unowned feed: {path}")
    records = {}
    for item in previous["items"]:
        identifier = item["id"]
        if identifier in records:
            raise ValueError(f"Duplicate previous feed ID: {locale}")
        if timestamp(item["date_published"]) > timestamp(item["date_modified"]):
            raise ValueError("Reversed item dates")
        if item["_owned_app"].get("content_digest") != item_digest(item):
            raise ValueError(f"Previous content digest drift: {identifier}")
        records[identifier] = item
    return records


def json_feed(locale: str, channel: dict, previous: dict, now: str) -> dict:
    items = []
    for record in channel["items"]:
        item = decode(json_bytes(record))
        content_digest = item_digest(item)
        old = previous.get(item["id"], {})
        if old.get("date_modified", "") > now:
            raise ValueError("Refusing to move item dates backwards")
        same = old.get("_owned_app", {}).get("content_digest") == content_digest
        item["date_published"] = old.get("date_published", now)
        item["date_modified"] = old["date_modified"] if same else now
        item["_owned_app"]["content_digest"] = content_digest
        items.append(item)
    return {
        "version": "https://jsonfeed.org/version/1.1",
        "title": channel["title"], "description": channel["disclosure"],
        "home_page_url": url(f"{locale}/index.html"),
        "feed_url": url(feed_path(locale, "json_feed")), "language": locale,
        "authors": [{"name": "Lumi Studio", "url": url("about.html")}],
        "_owned_feed": {
            "schema": SCHEMA, "notification_eligible": not market.is_unavailable(locale),
            "date_modified": max(item["date_modified"] for item in items),
        },
        "items": items,
    }


def xml_bytes(root: ET.Element) -> bytes:
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def atom_feed(feed: dict) -> bytes:
    ET.register_namespace("atom", ATOM)
    ET.register_namespace("lumi", LUMI)
    root = ET.Element(f"{{{ATOM}}}feed", {f"{{{XML}}}lang": feed["language"]})
    def node(parent, name, value):
        ET.SubElement(parent, f"{{{ATOM}}}{name}").text = value
    node(root, "id", url(feed_path(feed["language"], "atom")))
    node(root, "title", feed["title"])
    node(root, "subtitle", feed["description"])
    node(root, "updated", feed["_owned_feed"]["date_modified"])
    author = ET.SubElement(root, f"{{{ATOM}}}author")
    node(author, "name", "Lumi Studio")
    ET.SubElement(root, f"{{{ATOM}}}link", {
        "rel": "self", "href": url(feed_path(feed["language"], "atom")),
        "type": FORMATS["atom"][1],
    })
    ET.SubElement(root, f"{{{ATOM}}}link", {"rel": "alternate", "href": feed["home_page_url"]})
    if feed["_owned_feed"]["notification_eligible"]:
        for hub in WEBSUB_HUBS:
            ET.SubElement(root, f"{{{ATOM}}}link", {"rel": "hub", "href": hub})
    for item in feed["items"]:
        entry = ET.SubElement(root, f"{{{ATOM}}}entry")
        for name, value in (
            ("id", item["id"]), ("title", item["title"]), ("summary", item["summary"]),
            ("published", item["date_published"]), ("updated", item["date_modified"]),
        ):
            node(entry, name, value)
        ET.SubElement(entry, f"{{{ATOM}}}link", {"rel": "alternate", "href": item["url"]})
        ET.SubElement(entry, f"{{{ATOM}}}content", {"type": "html"}).text = item["content_html"]
        ET.SubElement(entry, f"{{{LUMI}}}record").text = json.dumps(
            item["_owned_app"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    return xml_bytes(root)


def rss_date(value: str) -> str:
    return format_datetime(datetime.fromisoformat(value.replace("Z", "+00:00")), usegmt=True)


def rss_feed(feed: dict) -> bytes:
    ET.register_namespace("atom", ATOM)
    ET.register_namespace("content", CONTENT)
    ET.register_namespace("lumi", LUMI)
    root = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(root, "channel")
    for name, value in (
        ("title", feed["title"]), ("link", feed["home_page_url"]),
        ("description", feed["description"]), ("language", feed["language"]),
        ("lastBuildDate", rss_date(feed["_owned_feed"]["date_modified"])),
    ):
        ET.SubElement(channel, name).text = value
    ET.SubElement(channel, f"{{{ATOM}}}link", {
        "rel": "self", "type": FORMATS["rss"][1],
        "href": url(feed_path(feed["language"], "rss")),
    })
    if feed["_owned_feed"]["notification_eligible"]:
        ET.SubElement(channel, "cloud", {
            "domain": RSSCLOUD_DOMAIN, "port": str(RSSCLOUD_PORT),
            "path": RSSCLOUD_NOTIFY_PATH, "registerProcedure": "",
            "protocol": RSSCLOUD_PROTOCOL,
        })
        for hub in WEBSUB_HUBS:
            ET.SubElement(channel, f"{{{ATOM}}}link", {"rel": "hub", "href": hub})
    for item in feed["items"]:
        entry = ET.SubElement(channel, "item")
        for name, value in (
            ("title", item["title"]), ("link", item["url"]),
            ("description", item["summary"]), ("pubDate", rss_date(item["date_published"])),
            (f"{{{ATOM}}}updated", item["date_modified"]),
            (f"{{{CONTENT}}}encoded", item["content_html"]),
        ):
            ET.SubElement(entry, name).text = value
        ET.SubElement(entry, "guid", {"isPermaLink": "false"}).text = item["id"]
        ET.SubElement(entry, f"{{{LUMI}}}record").text = json.dumps(
            item["_owned_app"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    return xml_bytes(root)


def discovery(raw: bytes, locale: str, title: str) -> bytes:
    source = raw.decode("utf-8")
    if source.count(HEAD_START) != source.count(HEAD_END) or source.count(HEAD_START) > 1:
        raise ValueError(f"Invalid discovery ownership markers: {locale}")
    source = re.sub(
        re.escape(HEAD_START) + r".*?" + re.escape(HEAD_END) + r"\n?",
        "", source, flags=re.S,
    )
    links = "\n".join(
        f'<link rel="alternate" type="{mime}" '
        f'title="{html.escape(title, quote=True)} · {fmt}" href="{url(feed_path(locale, fmt))}">'
        for fmt, (_, mime) in FORMATS.items()
    )
    block = f"{HEAD_START}\n{links}\n{HEAD_END}\n"
    output, count = re.subn(r"(<head\b[^>]*>\s*)", lambda m: m[1] + block, source, count=1, flags=re.I)
    if count != 1:
        raise ValueError(f"Missing locale directory head: {locale}")
    return output.encode("utf-8")


def render_directory(feeds: dict) -> bytes:
    rows = []
    for locale, feed in feeds.items():
        links = " · ".join(
            f'<a href="{url(feed_path(locale, fmt))}">{label}</a>'
            for fmt, label in (("rss", "RSS"), ("atom", "Atom"), ("json_feed", "JSON Feed"))
        )
        rows.append(
            f'<li lang="{locale}"><b>{locale}</b> '
            f'{html.escape(feed["title"])} — {links}</li>'
        )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Lumi Studio · App feeds in 50 locales</title>'
        f'<link rel="canonical" href="{url(DIRECTORY)}"></head>'
        '<body><main><h1>App feeds in 50 locales</h1>'
        f'<p>{html.escape(DISCLOSURE)} This is not an independent ranking.</p>'
        '<p>Each locale retains the complete app roster. Bangladesh entries '
        'are informational only: no App Store link, price or availability claim.</p>'
        '<ul>' + "\n".join(rows) + '</ul></main></body></html>\n'
    ).encode("utf-8")


def sitemap_index(raw: bytes) -> bytes:
    source = raw.decode("utf-8")
    root = ET.fromstring(raw)
    if root.tag != f"{{{SITEMAP_NS}}}sitemapindex":
        raise ValueError("Expected sitemap index")
    target = url(SITEMAP)
    count = sum(
        node.findtext(f"{{{SITEMAP_NS}}}loc") == target for node in root
    )
    if count > 1:
        raise ValueError("Duplicate owned-feed sitemap")
    if count == 1:
        return raw
    return source.replace(
        "</sitemapindex>",
        f"  <sitemap><loc>{target}</loc></sitemap>\n</sitemapindex>",
    ).encode("utf-8")


def render(pages: Path, *, source: Path = HERE, now: str | None = None) -> tuple[dict, dict]:
    now = timestamp(now or now_utc())
    roster, channels, inputs = load_sources(pages, source)
    feeds, outputs, rows = {}, {}, {}
    for locale, channel in channels.items():
        feed = json_feed(locale, channel, previous_items(pages, locale), now)
        feeds[locale] = feed
        formats = {
            "atom": atom_feed(feed), "rss": rss_feed(feed), "json_feed": json_bytes(feed),
        }
        rows[locale] = {
            "language": locale, "record_count": len(feed["items"]),
            "notification_eligible": not market.is_unavailable(locale),
            "date_modified": feed["_owned_feed"]["date_modified"],
            "formats": {},
        }
        for fmt, raw in formats.items():
            if len(raw) > MAX_BYTES:
                raise ValueError(f"Owned feed exceeds byte budget: {locale}/{fmt}")
            path = feed_path(locale, fmt)
            outputs[path] = raw
            rows[locale]["formats"][fmt] = {
                "path": path.as_posix(), "url": url(path), "sha256": sha256(raw),
                "content_type": FORMATS[fmt][1],
                "accepted_content_types": sorted(CONTENT_TYPES[fmt]),
            }
        head = Path(locale) / "index.html"
        outputs[head] = discovery((pages / head).read_bytes(), locale, feed["title"])
    modified = max(row["date_modified"] for row in rows.values())
    outputs[DIRECTORY] = render_directory(feeds)
    sitemap = ET.Element("urlset", {"xmlns": SITEMAP_NS})
    locations = {url(DIRECTORY): modified}
    for row in rows.values():
        locations.update({spec["url"]: row["date_modified"] for spec in row["formats"].values()})
    for location, changed in sorted(locations.items()):
        entry = ET.SubElement(sitemap, "url")
        ET.SubElement(entry, "loc").text = location
        ET.SubElement(entry, "lastmod").text = changed[:10]
    outputs[SITEMAP] = xml_bytes(sitemap)
    global_index = Path("sitemap_index.xml")
    outputs[global_index] = sitemap_index((pages / global_index).read_bytes())
    manifest = {
        "schema": SCHEMA, "site": SITE, "app_count": len(roster["apps"]),
        "locale_count": len(OFFICIAL_LOCALES),
        "record_count": len(roster["apps"]) * len(OFFICIAL_LOCALES),
        "feed_count": len(FORMATS) * len(OFFICIAL_LOCALES),
        "notification_feed_count": sum(r["notification_eligible"] for r in rows.values()) * 3,
        "apps": roster["apps"], "source": inputs, "feeds": rows,
        "purchase_models": dict(Counter(
            i["_owned_app"]["purchase_model"] for i in feeds["en-US"]["items"]
        )),
        "directory_sha256": sha256(outputs[DIRECTORY]),
        "sitemap_sha256": sha256(outputs[SITEMAP]),
    }
    manifest["generation_digest"] = digest(manifest)
    outputs[INDEX] = json_bytes(manifest)
    return outputs, manifest


def write_if_changed(path: Path, raw: bytes) -> bool:
    if path.is_symlink():
        raise ValueError(f"Refusing symlink output: {path}")
    if path.exists() and path.read_bytes() == raw:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = path.with_name(f".{path.name}.writing-{os.getpid()}")
    try:
        with staged.open("xb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staged, path)
    finally:
        staged.unlink(missing_ok=True)
    return True


def read_manifest(pages: Path) -> dict:
    manifest = read_json(pages / INDEX)
    comparable = {k: v for k, v in manifest.items() if k != "generation_digest"}
    if (
        manifest.get("schema") != SCHEMA or manifest.get("site") != SITE
        or manifest.get("generation_digest") != digest(comparable)
        or manifest.get("locale_count") != len(OFFICIAL_LOCALES)
        or manifest.get("feed_count") != 150
        or manifest.get("app_count") != len(manifest.get("apps", {}))
        or manifest.get("record_count") != manifest.get("app_count", 0) * 50
    ):
        raise ValueError("Invalid owned-feed generation manifest")
    require_official_locale_coverage("owned feed manifest", manifest["feeds"])
    if present_feed_paths(pages) != expected_feed_paths():
        raise ValueError("Owned feeds must be the exact 150-path set")
    for locale, row in manifest["feeds"].items():
        if (
            row.get("language") != locale or set(row.get("formats", {})) != set(FORMATS)
            or row.get("record_count") != manifest["app_count"]
            or row.get("notification_eligible") is not (not market.is_unavailable(locale))
        ):
            raise ValueError(f"Invalid owned-feed inventory: {locale}")
        expected_ids = {item_id(a["app_id"], locale) for a in manifest["apps"].values()}
        document = read_json(pages / feed_path(locale, "json_feed"))
        if (
            document.get("language") != locale or len(document.get("items", [])) != len(expected_ids)
            or {item.get("id") for item in document["items"]} != expected_ids
            or document.get("feed_url") != url(feed_path(locale, "json_feed"))
        ):
            raise ValueError(f"Owned-feed identity drift: {locale}")
        expected_raw = {"atom": atom_feed(document), "rss": rss_feed(document)}
        for fmt, spec in row["formats"].items():
            path = feed_path(locale, fmt)
            raw = (pages / path).read_bytes()
            if (
                spec.get("path") != path.as_posix() or spec.get("url") != url(path)
                or spec.get("content_type") != FORMATS[fmt][1]
                or spec.get("accepted_content_types") != sorted(CONTENT_TYPES[fmt])
                or len(raw) > MAX_BYTES or sha256(raw) != spec.get("sha256")
                or (fmt in expected_raw and expected_raw[fmt] != raw)
            ):
                raise ValueError(f"Partial or mixed owned-feed generation: {locale}/{fmt}")
        for item in document["items"]:
            facts = item["_owned_app"]
            app = manifest["apps"].get(facts.get("app_key"), {})
            if (
                facts.get("content_digest") != item_digest(item)
                or facts.get("app_store_id") != app.get("app_id")
                or item["id"] != item_id(app.get("app_id"), locale)
                or timestamp(item["date_published"]) > timestamp(item["date_modified"])
                or item["url"] != url(f"{locale}/{facts['app_key']}.html")
                or item["language"] != locale or facts["source_locale"] != locale
            ):
                raise ValueError(f"Owned-feed record drift: {locale}/{item['id']}")
            validate_summary(locale, item["summary"], facts["purchase_model"])
            validate_text(locale, item["title"], "title", require_native=False)
            validate_text(locale, facts["publisher_disclosure"], "disclosure")
            validate_text(locale, facts["purchase_label"], "purchase label")
            if market.is_unavailable(locale, facts["app_store_id"]):
                if (
                    "apps.apple.com" in json.dumps(item, ensure_ascii=False).casefold()
                    or facts.get("market_availability") != market.record_fields(locale, facts["app_store_id"])["market_availability"]
                    or any(name in facts for name in ("price", "currency", "storefront_facts"))
                ):
                    raise ValueError("Unavailable-market feed contains store claims")
    for path, field in ((DIRECTORY, "directory_sha256"), (SITEMAP, "sitemap_sha256")):
        if sha256((pages / path).read_bytes()) != manifest.get(field):
            raise ValueError(f"Partial owned-feed generation: {path}")
    return manifest


def build(pages: Path, *, check: bool = False, source: Path = HERE,
          now: str | None = None, reference_source: Path | None = None) -> dict:
    if reference_source is not None:
        require_parity(source, reference_source)
    if present_feed_paths(pages) - expected_feed_paths():
        raise ValueError("Owned feeds must be the exact 150-path set")
    outputs, manifest = render(pages, source=source, now=now)
    changed = [path for path, raw in outputs.items()
               if not (pages / path).exists() or (pages / path).read_bytes() != raw]
    if check and changed:
        raise ValueError(f"Owned-feed source/output drift ({len(changed)} files): {changed[:5]}")
    if not check:
        # The manifest is the commit marker; partial writes fail every upload/readback gate.
        for path in changed:
            if path != INDEX:
                write_if_changed(pages / path, outputs[path])
        if INDEX in changed:
            write_if_changed(pages / INDEX, outputs[INDEX])
    read_manifest(pages)
    return {
        "app_count": manifest["app_count"], "locale_count": manifest["locale_count"],
        "record_count": manifest["record_count"], "feed_count": manifest["feed_count"],
        "notification_feed_count": manifest["notification_feed_count"],
        "changed_files": len(changed), "generation_digest": manifest["generation_digest"],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-dir", type=Path, default=Path(os.environ.get("GEO_PAGES", HERE / "pages")))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--refresh-catalog", action="store_true")
    parser.add_argument("--reference-source", type=Path)
    args = parser.parse_args(argv)
    if args.reference_source is not None:
        require_parity(HERE, args.reference_source)
    if args.refresh_catalog:
        if args.check:
            parser.error("--check must never regenerate catalog inputs")
        from live_app_manifest import canonical_manifest
        import portfolio_app_catalog_api
        portfolio_app_catalog_api.build(
            pages=args.pages_dir, live_keys=set(canonical_manifest()["apps"])
        )
    print(json.dumps(build(
        args.pages_dir, check=args.check, reference_source=args.reference_source,
    ), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
