#!/usr/bin/env python3
"""Build locale-scoped Atom, RSS and JSON install-decision feeds."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
import email.utils
import hashlib
import html
import json
import os
from pathlib import Path
import re
from typing import Any
import xml.etree.ElementTree as ET

from family_travel_dataset import write_text_if_changed
from official_locales import OFFICIAL_LOCALES


SITE = os.environ.get(
    "GEO_SITE",
    "https://alice51849.github.io/ios-app-guide",
).rstrip("/")
FEED_DIR = Path("data") / "app-install-decision-routes" / "feeds"
FORMATS = ("atom", "rss", "json_feed")
FORMAT_SUFFIXES = {
    "atom": "atom.xml",
    "rss": "rss.xml",
    "json_feed": "feed.json",
}
FORMAT_MIME_TYPES = {
    "atom": "application/atom+xml",
    "rss": "application/rss+xml",
    "json_feed": "application/feed+json",
}
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
TIMESTAMP_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"
)


def feed_relative(locale: str, feed_format: str) -> Path:
    if locale not in OFFICIAL_LOCALES:
        raise ValueError(f"Unsupported install-decision feed locale: {locale}")
    if feed_format not in FORMATS:
        raise ValueError(
            f"Unsupported install-decision feed format: {feed_format}"
        )
    return FEED_DIR / f"{locale}.{FORMAT_SUFFIXES[feed_format]}"


def feed_url(locale: str, feed_format: str) -> str:
    return f"{SITE}/{feed_relative(locale, feed_format).as_posix()}"


def feed_urls(locale: str) -> dict[str, str]:
    return {
        feed_format: feed_url(locale, feed_format)
        for feed_format in FORMATS
    }


def all_feed_urls() -> list[str]:
    return [
        feed_url(locale, feed_format)
        for locale in OFFICIAL_LOCALES
        for feed_format in FORMATS
    ]


def syndication_payload() -> dict[str, Any]:
    return {
        "formats": list(FORMATS),
        "locale_feeds": {
            locale: feed_urls(locale) for locale in OFFICIAL_LOCALES
        },
    }


def discovery_links(locale: str, title: str) -> str:
    safe_title = html.escape(_single_line(title, "feed title"), quote=True)
    labels = {
        "atom": "Atom",
        "rss": "RSS 2.0",
        "json_feed": "JSON Feed 1.1",
    }
    return "\n".join(
        (
            f'<link rel="alternate" '
            f'type="{FORMAT_MIME_TYPES[feed_format]}" '
            f'title="{safe_title} ({labels[feed_format]})" '
            f'href="{feed_url(locale, feed_format)}">'
        )
        for feed_format in FORMATS
    )


def _single_line(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"Install-decision feed {field} must be text")
    text = value.strip()
    if not text or "\n" in text or "\r" in text:
        raise ValueError(f"Install-decision feed {field} must be one line")
    return text


def _timestamp(modified: str) -> str:
    if not DATE_RE.fullmatch(modified):
        raise ValueError(f"Invalid install-decision feed date: {modified}")
    date.fromisoformat(modified)
    return f"{modified}T00:00:00Z"


def _validated_timestamp(value: object) -> str:
    if not isinstance(value, str) or not TIMESTAMP_RE.fullmatch(value):
        raise ValueError(f"Invalid install-decision item timestamp: {value}")
    datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


def _rss_item_timestamp(value: str) -> str:
    instant = datetime.fromisoformat(
        _validated_timestamp(value).replace("Z", "+00:00")
    )
    return email.utils.format_datetime(instant, usegmt=True)


def _timestamp_after(candidate: str, previous: str) -> str:
    candidate_instant = datetime.fromisoformat(
        _validated_timestamp(candidate).replace("Z", "+00:00")
    )
    previous_instant = datetime.fromisoformat(
        _validated_timestamp(previous).replace("Z", "+00:00")
    )
    if candidate_instant <= previous_instant:
        candidate_instant = previous_instant + timedelta(seconds=1)
    return (
        candidate_instant.replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _record_digest(record: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            record,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _existing_items(path: Path) -> dict[str, dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(payload, dict) or not isinstance(
        payload.get("items"),
        list,
    ):
        raise ValueError(f"Invalid existing install-decision feed: {path}")
    items: dict[str, dict[str, Any]] = {}
    for item in payload["items"]:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise ValueError(
                f"Invalid existing install-decision feed item: {path}"
            )
        if item["id"] in items:
            raise ValueError(
                f"Duplicate existing install-decision feed item: {item['id']}"
            )
        items[item["id"]] = item
    return items


def _item_state(
    existing_json_feed: Path,
    records: list[dict[str, Any]],
    modified: str,
    changed_timestamp: str,
) -> dict[str, dict[str, str]]:
    baseline = _timestamp(modified)
    changed = max(
        baseline,
        _validated_timestamp(changed_timestamp),
    )
    existing = _existing_items(existing_json_feed)
    state: dict[str, dict[str, str]] = {}
    for record in records:
        record_id = str(record["record_id"])
        digest = _record_digest(record)
        previous = existing.get(record_id)
        previous_meta = previous.get("_meta") if previous else None
        previous_digest = (
            previous_meta.get("content_digest")
            if isinstance(previous_meta, dict)
            else None
        )
        if previous is not None:
            previous_modified = _validated_timestamp(
                previous.get("date_modified")
            )
            if previous_digest is None or previous_digest == digest:
                item_modified = previous_modified
            else:
                item_modified = _timestamp_after(
                    changed,
                    previous_modified,
                )
        else:
            item_modified = changed
        state[record_id] = {
            "content_digest": digest,
            "date_modified": item_modified,
        }
    return state


def _home_url(locale: str) -> str:
    return f"{SITE}/{locale}/index.html"


def _content_html(record: dict[str, Any]) -> str:
    context = html.escape(
        _single_line(record["decision_context"], "decision context")
    )
    store_url = html.escape(
        _single_line(record["app_store_url"], "App Store URL"),
        quote=True,
    )
    cta = html.escape(
        _single_line(record["app_store_cta_label"], "App Store CTA")
    )
    storefront = ""
    storefront_facts = record.get("storefront_facts")
    if isinstance(storefront_facts, dict):
        labels = [
            "App Store",
            html.escape(
                _single_line(
                    storefront_facts["formatted_price"],
                    "formatted App Store price",
                )
            ),
        ]
        if (
            "rating_value" in storefront_facts
            and "rating_count" in storefront_facts
        ):
            labels.append(
                "\u2605 "
                f"{float(storefront_facts['rating_value']):.1f}/5 "
                "\u00b7 "
                f"{int(storefront_facts['rating_count'])}"
            )
        storefront = f"<p>{' \u00b7 '.join(labels)}</p>"
    return (
        f"<p>{context}</p>{storefront}"
        f'<p><a href="{store_url}">{cta}</a></p>'
    )


def _content_text(record: dict[str, Any]) -> str:
    parts = [str(record["decision_context"])]
    storefront_facts = record.get("storefront_facts")
    if isinstance(storefront_facts, dict):
        parts.extend(
            (
                "App Store",
                _single_line(
                    storefront_facts["formatted_price"],
                    "formatted App Store price",
                ),
            )
        )
        if (
            "rating_value" in storefront_facts
            and "rating_count" in storefront_facts
        ):
            parts.append(
                "\u2605 "
                f"{float(storefront_facts['rating_value']):.1f}/5 "
                "\u00b7 "
                f"{int(storefront_facts['rating_count'])}"
            )
    parts.append(
        f"{record['app_store_cta_label']}: {record['app_store_url']}"
    )
    return " \u00b7 ".join(parts)


def _group_records(
    records: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    record_ids: set[str] = set()
    page_urls: set[str] = set()
    for record in records:
        locale = _single_line(record.get("locale"), "locale")
        if locale not in OFFICIAL_LOCALES:
            raise ValueError(f"Unexpected install-decision feed locale: {locale}")
        record_id = _single_line(record.get("record_id"), "record ID")
        page_url = _single_line(
            record.get("decision_page_url"),
            "decision page URL",
        )
        if record_id in record_ids or page_url in page_urls:
            raise ValueError(
                f"Duplicate install-decision feed record: {record_id}"
            )
        record_ids.add(record_id)
        page_urls.add(page_url)
        app_id = _single_line(record.get("app_store_id"), "App Store ID")
        app_store_url = _single_line(
            record.get("app_store_url"),
            "App Store URL",
        )
        if (
            not app_id.isdigit()
            or not app_store_url.startswith("https://apps.apple.com/")
            or f"id{app_id}" not in app_store_url
            or record.get("verified_live") is not True
            or record.get("is_ranking") is not False
            or record.get("measured_search_volume") is not False
        ):
            raise ValueError(
                f"Unsafe install-decision feed record: {record_id}"
            )
        for field in (
            "app_name",
            "publisher_query",
            "decision_context",
            "app_store_cta_label",
            "publisher_disclosure",
        ):
            _single_line(record.get(field), field)
        grouped[locale].append(record)

    if set(grouped) != set(OFFICIAL_LOCALES):
        raise ValueError("Install-decision feeds must cover all Apple locales")
    expected_apps = {
        str(record["app_key"]) for record in grouped[OFFICIAL_LOCALES[0]]
    }
    if not expected_apps:
        raise ValueError("Install-decision feeds require at least one app")
    for locale in OFFICIAL_LOCALES:
        locale_apps = {str(record["app_key"]) for record in grouped[locale]}
        if locale_apps != expected_apps or len(grouped[locale]) != len(
            expected_apps
        ):
            raise ValueError(
                f"Install-decision feed app coverage mismatch: {locale}"
            )
    return dict(grouped)


def _context(
    contexts: dict[str, dict[str, str]],
    locale: str,
) -> dict[str, str]:
    if set(contexts) != set(OFFICIAL_LOCALES):
        raise ValueError("Install-decision feed contexts must cover all locales")
    values = contexts[locale]
    return {
        "title": _single_line(values.get("title"), "title"),
        "description": _single_line(
            values.get("description"),
            "description",
        ),
        "publisher_disclosure": _single_line(
            values.get("publisher_disclosure"),
            "publisher disclosure",
        ),
    }


def render_atom(
    locale: str,
    records: list[dict[str, Any]],
    modified: str,
    context: dict[str, str],
    item_state: dict[str, dict[str, str]],
) -> str:
    e = html.escape
    updated = max(
        _timestamp(modified),
        *(state["date_modified"] for state in item_state.values()),
    )
    urls = feed_urls(locale)
    entries = []
    for record in records:
        content = e(_content_html(record), quote=False)
        item_updated = item_state[str(record["record_id"])][
            "date_modified"
        ]
        entries.append(
            "  <entry>\n"
            f"    <title>{e(str(record['publisher_query']))}</title>\n"
            f"    <id>{e(str(record['decision_page_url']))}</id>\n"
            f'    <link rel="alternate" type="text/html" '
            f'href="{e(str(record["decision_page_url"]), quote=True)}"/>\n'
            f'    <link rel="related" type="text/html" '
            f'href="{e(str(record["app_store_url"]), quote=True)}" '
            f'title="{e(str(record["app_store_cta_label"]), quote=True)}"/>\n'
            f"    <updated>{item_updated}</updated>\n"
            f"    <summary>{e(str(record['decision_context']))}</summary>\n"
            f'    <content type="html">{content}</content>\n'
            f'    <category term="{e(str(record["category"]), quote=True)}" '
            f'label="{e(str(record["category_label"]), quote=True)}"/>\n'
            "  </entry>"
        )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        f'<feed xmlns="http://www.w3.org/2005/Atom" '
        f'xml:lang="{e(locale, quote=True)}">\n'
        f"  <title>{e(context['title'])}</title>\n"
        f"  <subtitle>{e(context['description'])}</subtitle>\n"
        f"  <id>{e(urls['atom'])}</id>\n"
        f'  <link rel="self" type="application/atom+xml" '
        f'href="{e(urls["atom"], quote=True)}"/>\n'
        f'  <link rel="alternate" type="text/html" '
        f'href="{e(_home_url(locale), quote=True)}"/>\n'
        f'  <link rel="alternate" type="application/rss+xml" '
        f'href="{e(urls["rss"], quote=True)}"/>\n'
        f'  <link rel="alternate" type="application/feed+json" '
        f'href="{e(urls["json_feed"], quote=True)}"/>\n'
        f"  <updated>{updated}</updated>\n"
        "  <author><name>Lumi Studio</name></author>\n"
        + "\n".join(entries)
        + "\n</feed>\n"
    )


def render_rss(
    locale: str,
    records: list[dict[str, Any]],
    modified: str,
    context: dict[str, str],
    item_state: dict[str, dict[str, str]],
) -> str:
    e = html.escape
    feed_updated = max(
        _timestamp(modified),
        *(state["date_modified"] for state in item_state.values()),
    )
    published = _rss_item_timestamp(feed_updated)
    urls = feed_urls(locale)
    items = []
    for record in records:
        description = e(_content_html(record), quote=False)
        item_published = _rss_item_timestamp(
            item_state[str(record["record_id"])]["date_modified"]
        )
        items.append(
            "    <item>\n"
            f"      <title>{e(str(record['publisher_query']))}</title>\n"
            f"      <link>{e(str(record['decision_page_url']))}</link>\n"
            f'      <guid isPermaLink="true">'
            f"{e(str(record['decision_page_url']))}</guid>\n"
            f"      <pubDate>{item_published}</pubDate>\n"
            f"      <description>{description}</description>\n"
            f'      <atom:link rel="related" type="text/html" '
            f'href="{e(str(record["app_store_url"]), quote=True)}" '
            f'title="{e(str(record["app_store_cta_label"]), quote=True)}"/>\n'
            "    </item>"
        )
    return (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<rss version="2.0" '
        'xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        f"    <title>{e(context['title'])}</title>\n"
        f"    <link>{e(_home_url(locale))}</link>\n"
        f"    <description>{e(context['description'])}</description>\n"
        f"    <language>{e(locale)}</language>\n"
        f"    <lastBuildDate>{published}</lastBuildDate>\n"
        "    <generator>iOS App Guide install-decision feeds</generator>\n"
        f'    <atom:link rel="self" type="application/rss+xml" '
        f'href="{e(urls["rss"], quote=True)}"/>\n'
        f'    <atom:link rel="alternate" type="application/atom+xml" '
        f'href="{e(urls["atom"], quote=True)}"/>\n'
        f'    <atom:link rel="alternate" type="application/feed+json" '
        f'href="{e(urls["json_feed"], quote=True)}"/>\n'
        + "\n".join(items)
        + "\n  </channel>\n</rss>\n"
    )


def render_json_feed(
    locale: str,
    records: list[dict[str, Any]],
    modified: str,
    context: dict[str, str],
    item_state: dict[str, dict[str, str]],
) -> str:
    urls = feed_urls(locale)
    items = []
    for record in records:
        state = item_state[str(record["record_id"])]
        items.append(
            {
                "id": str(record["record_id"]),
                "url": str(record["decision_page_url"]),
                "external_url": str(record["app_store_url"]),
                "title": str(record["publisher_query"]),
                "content_html": _content_html(record),
                "content_text": _content_text(record),
                "summary": str(record["decision_context"]),
                "date_modified": state["date_modified"],
                "tags": list(
                    dict.fromkeys(
                        [
                            str(record["category_label"]),
                            str(record["purchase_label"]),
                            *[str(label) for label in record["badge_labels"]],
                        ]
                    )
                ),
                "_meta": {
                    "app_store_id": str(record["app_store_id"]),
                    "content_digest": state["content_digest"],
                    "verified_live": True,
                    "is_ranking": False,
                    "measured_search_volume": False,
                },
            }
        )
    return (
        json.dumps(
            {
                "version": "https://jsonfeed.org/version/1.1",
                "title": context["title"],
                "home_page_url": _home_url(locale),
                "feed_url": urls["json_feed"],
                "description": context["description"],
                "language": locale,
                "authors": [
                    {
                        "name": "Lumi Studio",
                        "url": f"{SITE}/about.html",
                    }
                ],
                "_meta": {
                    "publisher_disclosure": context[
                        "publisher_disclosure"
                    ],
                    "record_count": len(records),
                    "is_ranking": False,
                    "measured_search_volume": False,
                    "alternate_feeds": {
                        "atom": urls["atom"],
                        "rss": urls["rss"],
                    },
                },
                "items": items,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )


def build(
    pages: Path,
    records: list[dict[str, Any]],
    modified: str,
    contexts: dict[str, dict[str, str]],
) -> list[str]:
    grouped = _group_records(records)
    output_urls: list[str] = []
    changed_timestamp = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    for locale in OFFICIAL_LOCALES:
        context = _context(contexts, locale)
        state = _item_state(
            pages / feed_relative(locale, "json_feed"),
            grouped[locale],
            modified,
            changed_timestamp,
        )
        rendered = {
            "atom": render_atom(
                locale,
                grouped[locale],
                modified,
                context,
                state,
            ),
            "rss": render_rss(
                locale,
                grouped[locale],
                modified,
                context,
                state,
            ),
            "json_feed": render_json_feed(
                locale,
                grouped[locale],
                modified,
                context,
                state,
            ),
        }
        ET.fromstring(rendered["atom"])
        ET.fromstring(rendered["rss"])
        json.loads(rendered["json_feed"])
        for feed_format in FORMATS:
            path = pages / feed_relative(locale, feed_format)
            path.parent.mkdir(parents=True, exist_ok=True)
            write_text_if_changed(path, rendered[feed_format])
            output_urls.append(feed_url(locale, feed_format))
    return output_urls
