#!/usr/bin/env python3
"""Build a first-party long-form Standard.site manifest from verified GEO data.

The default mode validates and reports only. Use ``--write`` to persist the
manifest; this script never publishes records or authenticates to AT Protocol.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time
from typing import Any, Iterable, Mapping, Sequence
import urllib.error
import urllib.request
from urllib.parse import parse_qs, unquote, urlsplit


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ENGINE_ROOT = Path(os.environ.get("STANDARD_SITE_ENGINE_ROOT", ROOT)).resolve()
GEO = ENGINE_ROOT / "geo"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(GEO))
sys.path.insert(0, str(ENGINE_ROOT / "social"))

from answer_deep import DEEP_ITEMS  # noqa: E402
from standard_site_attribution import (  # noqa: E402
    AttributionError,
    MAX_CAMPAIGN_TOKEN_LENGTH,
    MEDIA_TYPE,
    PROVIDER_TOKEN,
    document_content_hash,
    ensure_primary_app_store_url,
    legacy_text_content,
    validate_primary_app_store_url,
)
from videogen.registry import APPS, APPSTORE  # noqa: E402
from official_locales import OFFICIAL_LOCALES  # noqa: E402


MANIFEST_VERSION = 1
PUBLIC_GET_PLAN_VERSION = 1
EXPECTED_LIVE_APP_COUNT = 46
EXPECTED_LOCALE_COUNT = 50
MAX_PUBLIC_GET_BYTES = 20 * 1024 * 1024
DEFAULT_PUBLIC_GET_ATTEMPTS = 3
DEFAULT_PUBLIC_GET_TIMEOUT = 20.0
DEFAULT_PUBLIC_GET_WORKERS = 8
DEFAULT_SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
DEFAULT_PAGES = Path(os.environ.get("GEO_PAGES", GEO / "pages"))
PRIVATE_DIR = Path(
    os.environ.get("GROWTH_PRIVATE_DIR", "~/.growth-private")
).expanduser()
DEFAULT_OUTPUT = PRIVATE_DIR / "standard-site-manifest.json"
LIVE_STATE_NAME = ".appstore_live_state.json"
REVIEWED_CATALOG_NAME = "apps.json"
ROBOTS_NAME = "robots.txt"
SITEMAP_NAME = "sitemap.xml"
SCHEMA_SOURCES = {
    "publication": "https://standard.site/docs/lexicons/publication/",
    "document": "https://standard.site/docs/lexicons/document/",
    "verification": "https://standard.site/docs/verification/",
    "tid": "https://atproto.com/specs/tid",
    "put_record": (
        "https://github.com/bluesky-social/atproto/blob/main/"
        "lexicons/com/atproto/repo/putRecord.json"
    ),
}
DISCLOSURE_TEMPLATE = (
    "Publisher disclosure: This first-party article is written and published "
    "by Lumi Studio, the developer of {name}. It is commercial "
    "publisher-authored guidance, not an independent review, ranking, or paid "
    "placement."
)
AVAILABILITY_NOTE = (
    "App Store availability, compatibility, features, and local pricing can "
    "change. Check the current App Store listing before downloading or buying."
)


class ManifestError(ValueError):
    """The live catalog or generated Standard.site manifest is unsafe."""


class _SurfaceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canonicals: list[str] = []
        self.hreflangs: dict[str, str] = {}
        self.links: list[str] = []
        self.robots: list[str] = []
        self.duplicate_hreflangs: set[str] = set()

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = {
            str(key).casefold(): value
            for key, value in attrs
            if key and value is not None
        }
        name = tag.casefold()
        relations = set(str(values.get("rel") or "").casefold().split())
        if name == "link" and "canonical" in relations and values.get("href"):
            self.canonicals.append(str(values["href"]))
        if (
            name == "link"
            and "alternate" in relations
            and values.get("hreflang")
        ):
            locale = str(values["hreflang"])
            if locale in self.hreflangs:
                self.duplicate_hreflangs.add(locale)
            self.hreflangs[locale] = str(values.get("href") or "")
        if name == "a" and values.get("href"):
            self.links.append(str(values["href"]))
        if (
            name == "meta"
            and str(values.get("name") or "").casefold() == "robots"
        ):
            self.robots.append(str(values.get("content") or ""))


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args: object, **kwargs: object) -> None:
        return None


_SURFACE_VALIDATION_CACHE: dict[
    tuple[object, ...], dict[str, dict[str, object]]
] = {}


def _utc(value: datetime | None = None) -> str:
    current = value or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    return (
        current.astimezone(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _compact(value: object) -> str:
    return " ".join(str(value or "").split())


def slugify(question: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", question.lower())
    return re.sub(r"-+", "-", value).strip("-") or "answer"


def _substitute(value: object, name: str) -> str:
    return str(value or "").replace("{name}", name).strip()


def _hash_json(value: object) -> str:
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def atomic_write_text(path: Path, content: str, mode: int = 0o600) -> None:
    """Replace ``path`` only after a durable sibling-file write."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.name}.{os.getpid()}.{secrets.token_hex(6)}.tmp"
    )
    descriptor = None
    try:
        descriptor = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            mode,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            descriptor = None
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def load_live_app_keys(
    pages: Path,
    appstore: Mapping[str, object],
    apps: Mapping[str, Mapping[str, object]],
) -> tuple[list[str], str]:
    """Read the last verified App Store snapshot without making a network call."""
    state_path = Path(pages) / LIVE_STATE_NAME
    try:
        raw = state_path.read_bytes()
        payload = json.loads(raw)
    except FileNotFoundError as error:
        raise ManifestError(
            f"Verified live-app catalog is missing: {state_path}"
        ) from error
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ManifestError(
            f"Verified live-app catalog is unreadable: {state_path}"
        ) from error
    live_ids = payload.get("live_ids")
    if not isinstance(live_ids, list) or not live_ids:
        raise ManifestError("Verified live-app catalog has no live_ids")
    normalized_ids = [str(value).strip() for value in live_ids]
    if (
        any(re.fullmatch(r"[0-9]+", value) is None for value in normalized_ids)
        or len(normalized_ids) != len(set(normalized_ids))
    ):
        raise ManifestError(
            "Verified live-app catalog has invalid or duplicate App IDs"
        )
    wanted = set(normalized_ids)
    reverse: dict[str, str] = {}
    for key, app_id in appstore.items():
        normalized = str(app_id).strip()
        if normalized in reverse:
            raise ManifestError(
                f"Maintained registry repeats App Store ID {normalized}"
            )
        reverse[normalized] = str(key)
    missing_ids = sorted(wanted - set(reverse))
    if missing_ids:
        raise ManifestError(
            "Verified live-app catalog contains unknown App IDs: "
            + ", ".join(missing_ids)
        )
    live = sorted(
        reverse[app_id]
        for app_id in wanted
        if reverse[app_id] in apps
    )
    missing_apps = sorted(
        reverse[app_id]
        for app_id in wanted
        if reverse[app_id] not in apps
    )
    if missing_apps:
        raise ManifestError(
            "Verified live-app catalog lacks maintained App identities: "
            + ", ".join(missing_apps)
        )
    if len(live) != len(wanted):
        raise ManifestError(
            "Verified live-app catalog does not match the maintained registry"
        )
    return live, hashlib.sha256(raw).hexdigest()


def _app_store_id(url: object, *, label: str) -> str:
    value = str(url or "").strip()
    parsed = urlsplit(value)
    match = re.fullmatch(
        r"/(?:[a-z]{2}/)?app/(?:[^/?#]+/)?id([0-9]+)",
        parsed.path,
    )
    if (
        parsed.scheme != "https"
        or parsed.hostname != "apps.apple.com"
        or parsed.port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or match is None
    ):
        raise ManifestError(f"{label} is not a canonical App Store URL")
    return match.group(1)


def load_reviewed_catalog(
    pages: Path,
    *,
    site: str,
    live_keys: Sequence[str],
    appstore: Mapping[str, object],
    apps: Mapping[str, Mapping[str, object]],
    expected_app_count: int,
    rows: Sequence[Mapping[str, object]] | None = None,
) -> tuple[dict[str, dict[str, str]], str]:
    path = Path(pages) / REVIEWED_CATALOG_NAME
    if rows is None:
        try:
            raw = path.read_bytes()
            payload = json.loads(raw)
        except FileNotFoundError as error:
            raise ManifestError(
                f"Reviewed exact-App catalog is missing: {path}"
            ) from error
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ManifestError(
                f"Reviewed exact-App catalog is unreadable: {path}"
            ) from error
    else:
        payload = list(rows)
        raw = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    if not isinstance(payload, list) or len(payload) != expected_app_count:
        raise ManifestError(
            "Reviewed catalog must contain exactly "
            f"{expected_app_count} Apps"
        )
    reverse: dict[str, str] = {}
    for key, value in appstore.items():
        app_id = str(value).strip()
        if app_id in reverse:
            raise ManifestError(
                f"Maintained registry repeats App Store ID {app_id}"
            )
        reverse[app_id] = str(key)
    reviewed: dict[str, dict[str, str]] = {}
    seen_urls: set[str] = set()
    for index, value in enumerate(payload):
        if not isinstance(value, Mapping):
            raise ManifestError(
                f"Reviewed catalog row {index} must be an object"
            )
        app_id = _app_store_id(
            value.get("appStoreUrl"),
            label=f"Reviewed catalog row {index} appStoreUrl",
        )
        key = reverse.get(app_id)
        if key is None or key not in apps:
            raise ManifestError(
                f"Reviewed catalog contains unknown App Store ID {app_id}"
            )
        name = _compact(value.get("name"))
        expected_name = _compact(apps[key].get("name"))
        if not name or name != expected_name:
            raise ManifestError(
                f"Reviewed catalog identity drift for {key}: {name!r}"
            )
        guide_url = str(value.get("guideUrl") or "").strip()
        expected_guide_url = f"{site}/en-US/{key}.html"
        if guide_url != expected_guide_url:
            raise ManifestError(
                f"Reviewed catalog Guide URL drift for {key}: {guide_url!r}"
            )
        if key in reviewed or guide_url in seen_urls:
            raise ManifestError(
                f"Reviewed catalog repeats App identity: {key}"
            )
        reviewed[key] = {
            "app_key": key,
            "app_store_id": app_id,
            "name": name,
            "guide_url": guide_url,
        }
        seen_urls.add(guide_url)
    expected_keys = set(map(str, live_keys))
    actual_keys = set(reviewed)
    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        unexpected = sorted(actual_keys - expected_keys)
        raise ManifestError(
            "Reviewed catalog/live catalog source drift: "
            f"missing={missing}; unexpected={unexpected}"
        )
    return reviewed, hashlib.sha256(raw).hexdigest()


def canonical_path(canonical_url: str, site: str) -> str:
    site_parts = urlsplit(site)
    url_parts = urlsplit(canonical_url)
    if (
        site_parts.scheme != "https"
        or url_parts.scheme != "https"
        or site_parts.netloc != url_parts.netloc
        or url_parts.query
        or url_parts.fragment
    ):
        raise ManifestError(f"Invalid canonical URL: {canonical_url}")
    base_path = site_parts.path.rstrip("/")
    if not (
        url_parts.path.startswith(base_path + "/")
        and url_parts.path != base_path + "/"
    ):
        raise ManifestError(
            f"Canonical URL is outside publication: {canonical_url}"
        )
    relative = url_parts.path[len(base_path) :]
    if not relative.startswith("/") or ".." in relative.split("/"):
        raise ManifestError(f"Invalid canonical path: {relative}")
    return unquote(relative)


def _canonical_is_deployed(pages: Path, canonical_url: str, site: str) -> bool:
    try:
        relative = canonical_path(canonical_url, site).lstrip("/")
    except ManifestError:
        return False
    target = Path(pages) / relative
    if target.suffix == "":
        target /= "index.html"
    try:
        with target.open(encoding="utf-8") as handle:
            head = handle.read(131_072)
    except (OSError, UnicodeDecodeError):
        return False
    return (
        f'href="{canonical_url}"' in head
        or f"href='{canonical_url}'" in head
    )


def _canonical_source(
    pages: Path, canonical_url: str, site: str
) -> tuple[Path, bytes]:
    relative = canonical_path(canonical_url, site).lstrip("/")
    target = Path(pages) / relative
    if target.suffix == "":
        target /= "index.html"
    try:
        return target, target.read_bytes()
    except OSError as error:
        raise ManifestError(
            f"Canonical source is not deployed locally: {canonical_url}"
        ) from error


def _surface_parser(
    payload: bytes, *, canonical_url: str
) -> _SurfaceParser:
    try:
        source = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ManifestError(
            f"Canonical source is not UTF-8: {canonical_url}"
        ) from error
    parser = _SurfaceParser()
    try:
        parser.feed(source)
        parser.close()
    except Exception as error:
        raise ManifestError(
            f"Canonical source HTML is invalid: {canonical_url}"
        ) from error
    return parser


def _has_campaign_link(parser: _SurfaceParser, app_id: str) -> bool:
    for link in parser.links:
        parsed = urlsplit(link)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "apps.apple.com"
            or parsed.port is not None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
            or re.search(rf"/id{re.escape(app_id)}$", parsed.path) is None
        ):
            continue
        try:
            query = parse_qs(
                parsed.query,
                keep_blank_values=True,
                strict_parsing=True,
            )
        except ValueError:
            continue
        campaign = query.get("ct", [])
        if (
            query.get("pt") == [PROVIDER_TOKEN]
            and query.get("mt") == [MEDIA_TYPE]
            and len(campaign) == 1
            and campaign[0]
            and len(campaign[0]) <= MAX_CAMPAIGN_TOKEN_LENGTH
        ):
            return True
    return False


def _validate_robots(robots: bytes, *, site: str) -> None:
    try:
        lines = [
            line.strip()
            for line in robots.decode("utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    except UnicodeDecodeError as error:
        raise ManifestError("robots.txt is not UTF-8") from error
    wildcard = False
    wildcard_allows_root = False
    wildcard_disallows: list[str] = []
    for line in lines:
        field, separator, value = line.partition(":")
        if not separator:
            continue
        field = field.strip().casefold()
        value = value.strip()
        if field == "user-agent":
            wildcard = value == "*"
            continue
        if not wildcard:
            continue
        if field == "allow" and value == "/":
            wildcard_allows_root = True
        if field == "disallow" and value:
            wildcard_disallows.append(value)
    if not wildcard_allows_root or wildcard_disallows:
        raise ManifestError(
            "robots.txt must allow the full Guide for the wildcard crawler"
        )
    expected_sitemap = f"Sitemap: {site}/{SITEMAP_NAME}"
    if expected_sitemap not in robots.decode("utf-8"):
        raise ManifestError("robots.txt does not advertise the canonical sitemap")


def validate_reviewed_surfaces(
    pages: Path,
    *,
    site: str,
    reviewed: Mapping[str, Mapping[str, str]],
    official_locales: Sequence[str],
) -> dict[str, dict[str, object]]:
    locales = tuple(map(str, official_locales))
    if (
        not locales
        or len(locales) != len(set(locales))
        or any(not locale for locale in locales)
    ):
        raise ManifestError("Official locale authority is invalid")
    robots_path = Path(pages) / ROBOTS_NAME
    sitemap_path = Path(pages) / SITEMAP_NAME
    source_paths = [robots_path, sitemap_path]
    source_paths.extend(
        Path(pages) / locale / f"{key}.html"
        for key in sorted(reviewed)
        for locale in locales
    )
    try:
        fingerprints = tuple(
            (
                str(path.relative_to(pages)),
                path.stat().st_size,
                path.stat().st_mtime_ns,
            )
            for path in source_paths
        )
    except OSError as error:
        raise ManifestError(
            "A reviewed locale surface is not deployed locally"
        ) from error
    cache_key: tuple[object, ...] = (
        str(Path(pages).resolve()),
        site,
        tuple(
            (
                key,
                reviewed[key]["app_store_id"],
                reviewed[key]["guide_url"],
            )
            for key in sorted(reviewed)
        ),
        locales,
        fingerprints,
    )
    cached = _SURFACE_VALIDATION_CACHE.get(cache_key)
    if cached is not None:
        return {
            key: dict(value)
            for key, value in cached.items()
        }
    try:
        robots = robots_path.read_bytes()
        sitemap = sitemap_path.read_bytes()
    except OSError as error:
        raise ManifestError(
            "Canonical robots.txt or sitemap.xml is unavailable"
        ) from error
    _validate_robots(robots, site=site)
    surfaces: dict[str, dict[str, object]] = {}
    for key in sorted(reviewed):
        row = reviewed[key]
        app_id = row["app_store_id"]
        expected_hreflangs = {
            locale: f"{site}/{locale}/{key}.html"
            for locale in locales
        }
        expected_hreflangs["x-default"] = (
            f"{site}/en-US/{key}.html"
        )
        locale_hashes: dict[str, str] = {}
        source_hash = ""
        for locale in locales:
            canonical = f"{site}/{locale}/{key}.html"
            _, payload = _canonical_source(pages, canonical, site)
            parser = _surface_parser(payload, canonical_url=canonical)
            if parser.canonicals != [canonical]:
                raise ManifestError(
                    f"Canonical identity is incomplete for {key}/{locale}"
                )
            if (
                parser.duplicate_hreflangs
                or parser.hreflangs != expected_hreflangs
            ):
                raise ManifestError(
                    f"Hreflang coverage is not exact for {key}/{locale}"
                )
            if any(
                token in directive.casefold()
                for directive in parser.robots
                for token in ("noindex", "nofollow")
            ):
                raise ManifestError(
                    f"Canonical surface is not indexable: {key}/{locale}"
                )
            if canonical.encode("utf-8") not in sitemap:
                raise ManifestError(
                    f"Canonical surface is absent from sitemap.xml: "
                    f"{key}/{locale}"
                )
            if not _has_campaign_link(parser, app_id):
                raise ManifestError(
                    f"Canonical surface lacks reviewed App campaign identity: "
                    f"{key}/{locale}"
                )
            digest = hashlib.sha256(payload).hexdigest()
            locale_hashes[locale] = digest
            if locale == "en-US":
                source_hash = digest
        if not source_hash:
            raise ManifestError(f"Reviewed catalog lacks en-US for {key}")
        surfaces[key] = {
            "app_key": key,
            "canonical_url": row["guide_url"],
            "locale_count": len(locales),
            "locale_tree_sha256": _hash_json(locale_hashes),
            "source_page_sha256": source_hash,
        }
    _SURFACE_VALIDATION_CACHE[cache_key] = {
        key: dict(value)
        for key, value in surfaces.items()
    }
    return surfaces


def _purchase_copy(model: object) -> str:
    if model == "paid_upfront":
        return (
            "The maintained publisher catalog describes it as a paid download "
            "with no recurring subscription."
        )
    if model == "free_with_lifetime_unlock":
        return (
            "The maintained publisher catalog describes it as free to start "
            "with an optional one-time lifetime unlock and no subscription."
        )
    if model == "free":
        return (
            "The maintained publisher catalog describes it as free; confirm "
            "the current offer in the App Store."
        )
    return (
        "The purchase model is not asserted here; use the current App Store "
        "listing as the final source."
    )


def _where_app_fits(
    name: str, app: Mapping[str, object], app_store_url: str
) -> str:
    purpose = _compact(app.get("sub"))
    facts = [
        _compact(value)
        for value in app.get("cta_bullets", [])
        if _compact(value)
    ]
    details = (
        f"The maintained first-party catalog describes {name} as: {purpose}."
        if purpose
        else f"{name} is listed as an iOS app in the maintained catalog."
    )
    if facts:
        details += " Published decision facts include " + ", ".join(facts) + "."
    details += " " + _purchase_copy(app.get("purchase_model"))
    if app_store_url:
        details += f" Current listing: {app_store_url}"
    return details


def _tags(key: str, app: Mapping[str, object]) -> list[str]:
    values = [
        key,
        _compact(app.get("name")),
        _compact(app.get("category") or "iOS"),
        "iOS",
        "publisher-authored",
        "first-party",
    ]
    output: list[str] = []
    for value in values:
        value = value.lstrip("#")
        if value and value.casefold() not in {item.casefold() for item in output}:
            output.append(value[:128])
    return output


def _deep_document(
    *,
    key: str,
    app: Mapping[str, object],
    app_store_id: str,
    app_store_url: str,
    item: Mapping[str, object],
    canonical_url: str,
    site: str,
) -> dict[str, object]:
    name = _compact(app["name"])
    disclosure = DISCLOSURE_TEMPLATE.format(name=name)
    title = _substitute(
        item.get("page_title") or item.get("query"), name
    )
    lead = _substitute(item.get("lead"), name)
    detail = _substitute(item.get("detail"), name)
    if not title or not lead or not detail:
        raise ManifestError(f"Incomplete deep editorial item for {key}")

    sections = [
        disclosure,
        title,
        "Context",
        lead,
        detail,
        "What to check",
    ]
    bullets = [
        _substitute(value, name)
        for value in item.get("bullets", [])
        if _substitute(value, name)
    ]
    sections.extend(f"• {value}" for value in bullets)

    decision_steps = [
        _substitute(value, name)
        for value in item.get("decision_steps", [])
        if _substitute(value, name)
    ]
    if decision_steps:
        sections.append("A practical decision process")
        sections.extend(
            f"{index}. {value}"
            for index, value in enumerate(decision_steps, start=1)
        )

    sections.extend(
        [
            "Where the app fits",
            _substitute(
                item.get("where_app_fits")
                or _where_app_fits(name, app, app_store_url),
                name,
            ),
            "Questions to ask before deciding",
        ]
    )
    for faq in item.get("faq", []):
        if not isinstance(faq, Mapping):
            continue
        question = _substitute(faq.get("q"), name)
        answer = _substitute(faq.get("a"), name)
        if question and answer:
            sections.extend((f"Question: {question}", f"Answer: {answer}"))

    sources = item.get("sources", [])
    if isinstance(sources, Sequence) and sources:
        sections.append("Sources named in the maintained editorial record")
        for source in sources:
            if isinstance(source, Mapping):
                label = _substitute(source.get("title"), name)
                url = _compact(source.get("url"))
                if label and url:
                    sections.append(f"{label}: {url}")

    sections.extend(("Limits and availability", AVAILABILITY_NOTE))
    text = "\n\n".join(value for value in sections if value)
    try:
        text, primary_app_store_url, legacy_app_store_link = (
            ensure_primary_app_store_url(
                text,
                app_id=app_store_id,
                fallback_route=app_store_url,
            )
        )
    except AttributionError as error:
        raise ManifestError(
            f"Invalid primary App Store URL for {key}: {error}"
        ) from error
    description = _compact(
        item.get("meta_description") or lead
    )[:3000]
    document = {
        "app_key": key,
        "canonical_url": canonical_url,
        "path": canonical_path(canonical_url, site),
        "title": title,
        "description": description,
        "text_content": text,
        "app_store_id": app_store_id,
        "primary_app_store_url": primary_app_store_url,
        "legacy_app_store_link": legacy_app_store_link,
        "tags": _tags(key, app),
        "source_query": _substitute(item.get("query"), name),
        "editorial_kind": _compact(item.get("kind") or "guide"),
    }
    document["content_hash"] = document_content_hash(document)
    return document


def _fallback_document(
    *,
    key: str,
    app: Mapping[str, object],
    app_store_id: str,
    app_store_url: str,
    canonical_url: str,
    site: str,
) -> dict[str, object]:
    name = _compact(app["name"])
    purpose = _compact(app.get("sub")) or "complete a specific iPhone task"
    category = _compact(app.get("category") or "iOS utility")
    published_facts = [
        _compact(value)
        for value in app.get("cta_bullets", [])
        if _compact(value)
    ]
    facts = (
        "\n\n".join(f"• {value}" for value in published_facts)
        or "• Compare the current feature list with the exact task you need."
    )
    title = f"{name}: a first-party guide to deciding whether it fits"
    disclosure = DISCLOSURE_TEMPLATE.format(name=name)
    text = "\n\n".join(
        [
            disclosure,
            title,
            "Start with the job, not a ranking",
            (
                f"{name} appears in the verified live-app catalog under "
                f"{category}. The maintained product description says it is "
                f"designed to {purpose.rstrip('.').lower()}. This guide does "
                "not compare invented scores, ratings, download counts, or "
                "popularity. It gives you a transparent first-party checklist "
                "for deciding whether the published workflow matches yours."
            ),
            "Published decision facts",
            facts,
            "How to evaluate the fit",
            (
                "Write down the outcome you need, the Apple devices you expect "
                "to use, whether offline access matters, and which export or "
                "sharing step is essential. Compare those requirements with "
                "the current listing rather than assuming that a category name "
                "guarantees a feature. Try the smallest real task available "
                "before moving important data or relying on the app in a "
                "time-sensitive situation."
            ),
            "Cost and privacy questions",
            (
                _purchase_copy(app.get("purchase_model"))
                + " Also check whether your intended workflow needs an "
                "account, cloud transfer, analytics, or external services. "
                "Only rely on privacy or offline claims that are stated in the "
                "current product materials."
            ),
            "Where the app fits",
            _where_app_fits(name, app, app_store_url),
            "Questions to ask before deciding",
            (
                f"Question: Is this an independent recommendation of {name}?\n\n"
                "Answer: No. Lumi Studio publishes this first-party guide and "
                "develops the app. No independent rank or comparative score is "
                "claimed."
            ),
            (
                "Question: What should I verify before buying or downloading?\n\n"
                "Answer: Confirm the current regional price, compatibility, "
                "feature list, privacy disclosure, and purchase model in the "
                "App Store, then test the workflow on a non-critical example."
            ),
            "Limits and availability",
            AVAILABILITY_NOTE,
        ]
    )
    try:
        text, primary_app_store_url, legacy_app_store_link = (
            ensure_primary_app_store_url(
                text,
                app_id=app_store_id,
                fallback_route=app_store_url,
            )
        )
    except AttributionError as error:
        raise ManifestError(
            f"Invalid primary App Store URL for {key}: {error}"
        ) from error
    document = {
        "app_key": key,
        "canonical_url": canonical_url,
        "path": canonical_path(canonical_url, site),
        "title": title,
        "description": (
            f"A transparent first-party guide to evaluating {name} for "
            f"{purpose.rstrip('.').lower()}, without an independent ranking."
        ),
        "text_content": text,
        "app_store_id": app_store_id,
        "primary_app_store_url": primary_app_store_url,
        "legacy_app_store_link": legacy_app_store_link,
        "tags": _tags(key, app),
        "source_query": f"How should I evaluate {name} before downloading?",
        "editorial_kind": "publisher-guide",
    }
    document["content_hash"] = document_content_hash(document)
    return document


def _store_url(app_id: object) -> str:
    value = str(app_id or "").strip()
    if not re.fullmatch(r"[0-9]+", value):
        raise ManifestError(f"Invalid App Store identifier: {app_id!r}")
    return f"https://apps.apple.com/app/id{value}"


def _fallback_canonical(
    pages: Path, site: str, key: str
) -> str | None:
    for relative in (
        f"/en-US/{key}.html",
        f"/hubs/{key}.html",
        f"/{key}.html",
    ):
        canonical = site + relative
        if _canonical_is_deployed(pages, canonical, site):
            return canonical
    return None


def _deep_candidates(
    items: Iterable[Mapping[str, object]], key: str
) -> Iterable[Mapping[str, object]]:
    for item in items:
        if item.get("app_key") != key:
            continue
        if all(
            item.get(field)
            for field in ("query", "lead", "detail", "bullets", "faq")
        ):
            yield item


def load_lifecycle_state(path: Path) -> tuple[dict[str, object], str]:
    try:
        raw = Path(path).read_bytes()
        payload = json.loads(raw)
    except FileNotFoundError as error:
        raise ManifestError(
            f"Standard.site lifecycle state is missing: {path}"
        ) from error
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ManifestError(
            f"Standard.site lifecycle state is unreadable: {path}"
        ) from error
    if not isinstance(payload, dict):
        raise ManifestError("Standard.site lifecycle state must be an object")
    return payload, hashlib.sha256(raw).hexdigest()


def _state_timestamp(
    state: Mapping[str, object] | None,
    explicit: datetime | None,
) -> str:
    if explicit is not None:
        return _utc(explicit)
    candidates: list[str] = []
    if isinstance(state, Mapping):
        publication = state.get("publication")
        if isinstance(publication, Mapping):
            candidates.extend(
                str(publication.get(field) or "")
                for field in ("last_verified_at", "published_at")
            )
        daily = state.get("daily")
        if isinstance(daily, Mapping):
            for entry in daily.values():
                if isinstance(entry, Mapping):
                    candidates.append(str(entry.get("created_at") or ""))
        documents = state.get("documents")
        if isinstance(documents, Mapping):
            for entry in documents.values():
                if not isinstance(entry, Mapping):
                    continue
                candidates.extend(
                    str(entry.get(field) or "")
                    for field in (
                        "last_verified_at",
                        "updated_at",
                        "published_at",
                    )
                )
    parsed: list[datetime] = []
    for value in candidates:
        if not value:
            continue
        try:
            timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            parsed.append(timestamp)
        except ValueError as error:
            raise ManifestError(
                f"Lifecycle state contains an invalid timestamp: {value}"
            ) from error
    if parsed:
        return _utc(max(parsed))
    return "1970-01-01T00:00:00.000Z"


def _lifecycle_manifest(
    *,
    documents: Sequence[Mapping[str, object]],
    live_keys: Sequence[str],
    state: Mapping[str, object] | None,
    state_sha256: str | None,
    today: str,
) -> dict[str, object]:
    active = {
        str(document["canonical_url"]): str(document["app_key"])
        for document in documents
    }
    if state is None:
        return {
            "state_loaded": False,
            "state_sha256": None,
            "state_document_count": None,
            "active_state_document_count": None,
            "published_document_count": None,
            "published_app_keys": None,
            "missing_published_app_keys": None,
            "publication": None,
            "tombstones": [],
            "policy": (
                "No lifecycle claim is made without a durable state snapshot."
            ),
        }
    if state.get("version") != 1:
        raise ManifestError("Unsupported Standard.site lifecycle state version")
    state_documents = state.get("documents")
    publication = state.get("publication")
    daily = state.get("daily")
    if (
        not isinstance(state_documents, Mapping)
        or not isinstance(publication, Mapping)
        or not isinstance(daily, Mapping)
    ):
        raise ManifestError("Standard.site lifecycle state is incomplete")
    selected_today: set[str] = set()
    daily_entry = daily.get(today)
    if daily_entry is not None:
        if (
            not isinstance(daily_entry, Mapping)
            or not isinstance(daily_entry.get("selected_urls"), list)
        ):
            raise ManifestError("Current lifecycle daily reservation is invalid")
        selected_today = {
            str(value) for value in daily_entry["selected_urls"]
        }
    live = set(map(str, live_keys))
    published_apps: set[str] = set()
    published_documents = 0
    active_state_documents = 0
    tombstones: list[dict[str, object]] = []
    for canonical, raw_entry in sorted(state_documents.items()):
        if not isinstance(canonical, str) or not isinstance(
            raw_entry, Mapping
        ):
            raise ManifestError("Lifecycle document state is invalid")
        entry = dict(raw_entry)
        app_key = str(entry.get("app_key") or "")
        if app_key not in live:
            raise ManifestError(
                f"Lifecycle state contains an unknown App identity: {app_key!r}"
            )
        rkey = str(entry.get("rkey") or "")
        if rkey and re.fullmatch(
            r"[234567abcdefghij][234567abcdefghijklmnopqrstuvwxyz]{12}",
            rkey,
        ) is None:
            raise ManifestError(
                f"Lifecycle state contains an invalid rkey: {canonical}"
            )
        tombstone_state = entry.get("tombstone")
        if tombstone_state is not None and (
            not isinstance(tombstone_state, Mapping)
            or tombstone_state.get("version") != 1
            or tombstone_state.get("state")
            not in {"pending_delete", "confirmed_absent"}
            or not tombstone_state.get("transition_at")
        ):
            raise ManifestError(
                f"Lifecycle state contains an invalid tombstone: {canonical}"
            )
        if canonical in active:
            if tombstone_state is not None:
                raise ManifestError(
                    f"Active canonical is also tombstoned: {canonical}"
                )
            active_state_documents += 1
            if active[canonical] != app_key:
                raise ManifestError(
                    f"Lifecycle canonical moved between Apps: {canonical}"
                )
            if entry.get("published") is True:
                published_documents += 1
                published_apps.add(app_key)
            continue
        if canonical in selected_today:
            raise ManifestError(
                "A currently reserved lifecycle document disappeared from "
                f"the manifest: {canonical}"
            )
        if not rkey:
            raise ManifestError(
                f"Lifecycle tombstone has no stable rkey: {canonical}"
            )
        confirmed_absent = (
            isinstance(tombstone_state, Mapping)
            and tombstone_state.get("version") == 1
            and tombstone_state.get("state") == "confirmed_absent"
        )
        tombstones.append(
            {
                "canonical_url": canonical,
                "app_key": app_key,
                "rkey": rkey,
                "state_entry_sha256": _hash_json(entry),
                "remote_record_expected": (
                    not confirmed_absent
                    and bool(
                        entry.get("published")
                        or entry.get("at_uri")
                        or entry.get("cid")
                        or entry.get("published_at")
                    )
                ),
            }
        )
    missing = sorted(live - published_apps)
    publication_summary: dict[str, str] | None = None
    if publication.get("published") is True:
        at_uri = str(publication.get("at_uri") or "")
        canonical_url = str(publication.get("canonical_url") or "")
        parsed = urlsplit(canonical_url)
        if (
            re.fullmatch(
                r"at://did:[a-z0-9:%._-]+/site\.standard\.publication/"
                r"[234567abcdefghij][234567abcdefghijklmnopqrstuvwxyz]{12}",
                at_uri,
            )
            is None
            or parsed.scheme != "https"
            or not parsed.netloc
            or parsed.query
            or parsed.fragment
        ):
            raise ManifestError(
                "Published lifecycle state has invalid publication identity"
            )
        publication_path = parsed.path.rstrip("/")
        publication_summary = {
            "at_uri": at_uri,
            "well_known_url": (
                f"{parsed.scheme}://{parsed.netloc}"
                "/.well-known/site.standard.publication"
                f"{publication_path}"
            ),
        }
    return {
        "state_loaded": True,
        "state_sha256": state_sha256,
        "state_document_count": len(state_documents),
        "active_state_document_count": active_state_documents,
        "published_document_count": published_documents,
        "published_app_keys": sorted(published_apps),
        "missing_published_app_keys": missing,
        "publication": publication_summary,
        "tombstones": tombstones,
        "policy": (
            "Only remotely confirmed active records count as published; "
            "manifest removals become fingerprinted tombstones and must be "
            "confirmed absent or deleted with compare-and-swap."
        ),
    }


def _plan_item(
    *,
    kind: str,
    url: str,
    payload: bytes,
    app_key: str | None = None,
) -> dict[str, object]:
    item: dict[str, object] = {
        "kind": kind,
        "url": url,
        "expected_status": 200,
        "expected_final_url": url,
        "expected_bytes": len(payload),
        "expected_sha256": hashlib.sha256(payload).hexdigest(),
        "max_bytes": max(len(payload) + 1, 1024),
    }
    if app_key is not None:
        item["app_key"] = app_key
    return item


def build_public_get_plan(
    *,
    pages: Path,
    site: str,
    documents: Sequence[Mapping[str, object]],
    lifecycle: Mapping[str, object],
) -> dict[str, object]:
    requests: list[dict[str, object]] = []
    for relative, kind, url in (
        ("index.html", "publication", site + "/"),
        (REVIEWED_CATALOG_NAME, "reviewed-catalog", site + "/apps.json"),
        (ROBOTS_NAME, "robots", site + "/robots.txt"),
        (SITEMAP_NAME, "sitemap", site + "/sitemap.xml"),
    ):
        try:
            payload = (Path(pages) / relative).read_bytes()
        except OSError as error:
            raise ManifestError(
                f"Public GET source is unavailable: {relative}"
            ) from error
        requests.append(_plan_item(kind=kind, url=url, payload=payload))
    for document in documents:
        canonical = str(document["canonical_url"])
        _, payload = _canonical_source(pages, canonical, site)
        requests.append(
            _plan_item(
                kind="document",
                url=canonical,
                payload=payload,
                app_key=str(document["app_key"]),
            )
        )
    if lifecycle.get("state_loaded") is True:
        publication = lifecycle.get("publication")
        if isinstance(publication, Mapping):
            at_uri = str(publication.get("at_uri") or "")
            request_url = str(publication.get("well_known_url") or "")
            if at_uri and request_url:
                requests.append(
                    _plan_item(
                        kind="publication-verification",
                        url=request_url,
                        payload=(at_uri + "\n").encode("utf-8"),
                    )
                )
    requests.sort(key=lambda item: (str(item["url"]), str(item["kind"])))
    urls = [str(item["url"]) for item in requests]
    if len(urls) != len(set(urls)):
        raise ManifestError("Public GET plan contains duplicate URLs")
    return {
        "version": PUBLIC_GET_PLAN_VERSION,
        "request_count": len(requests),
        "requests": requests,
        "policy": (
            "Anonymous GET only; HTTP 404, redirects, byte drift, oversized "
            "responses, and untrusted final URLs fail closed."
        ),
    }


def build_manifest(
    *,
    pages: Path = DEFAULT_PAGES,
    site: str = DEFAULT_SITE,
    apps: Mapping[str, Mapping[str, object]] = APPS,
    appstore: Mapping[str, object] = APPSTORE,
    deep_items: Iterable[Mapping[str, object]] = DEEP_ITEMS,
    max_per_app: int = 3,
    now: datetime | None = None,
    today: str | None = None,
    expected_app_count: int = EXPECTED_LIVE_APP_COUNT,
    official_locales: Sequence[str] = OFFICIAL_LOCALES,
    reviewed_catalog: Sequence[Mapping[str, object]] | None = None,
    lifecycle_state: Mapping[str, object] | None = None,
    lifecycle_state_sha256: str | None = None,
) -> dict[str, object]:
    if not 1 <= max_per_app <= 4:
        raise ManifestError("max_per_app must be between 1 and 4")
    if type(expected_app_count) is not int or expected_app_count < 1:
        raise ManifestError("expected_app_count must be a positive integer")
    site = site.rstrip("/")
    live_keys, live_state_sha256 = load_live_app_keys(
        pages, appstore, apps
    )
    if len(live_keys) != expected_app_count:
        raise ManifestError(
            "Verified live-app catalog must contain exactly "
            f"{expected_app_count} Apps, found {len(live_keys)}"
        )
    locales = tuple(map(str, official_locales))
    if len(locales) != EXPECTED_LOCALE_COUNT and (
        expected_app_count == EXPECTED_LIVE_APP_COUNT
    ):
        raise ManifestError(
            "Production Standard.site coverage requires exactly "
            f"{EXPECTED_LOCALE_COUNT} official locales"
        )
    reviewed, reviewed_catalog_sha256 = load_reviewed_catalog(
        pages,
        site=site,
        live_keys=live_keys,
        appstore=appstore,
        apps=apps,
        expected_app_count=expected_app_count,
        rows=reviewed_catalog,
    )
    reviewed_surfaces = validate_reviewed_surfaces(
        pages,
        site=site,
        reviewed=reviewed,
        official_locales=locales,
    )
    documents: list[dict[str, object]] = []
    seen_urls: set[str] = set()

    for key in live_keys:
        app = apps[key]
        if not _compact(app.get("name")):
            raise ManifestError(f"Live app has no name: {key}")
        app_store_id = str(appstore[key]).strip()
        app_store_url = _store_url(app_store_id)
        primary_canonical = reviewed[key]["guide_url"]
        primary = _fallback_document(
            key=key,
            app=app,
            app_store_id=app_store_id,
            app_store_url=app_store_url,
            canonical_url=primary_canonical,
            site=site,
        )
        primary["coverage_role"] = "app-primary"
        primary["source_page_sha256"] = reviewed_surfaces[key][
            "source_page_sha256"
        ]
        primary["locale_tree_sha256"] = reviewed_surfaces[key][
            "locale_tree_sha256"
        ]
        documents.append(primary)
        seen_urls.add(primary_canonical)
        added = 0
        for item in _deep_candidates(deep_items, key):
            canonical = (
                f"{site}/answers/{slugify(str(item['query']))}.html"
            )
            if canonical in seen_urls or not _canonical_is_deployed(
                pages, canonical, site
            ):
                continue
            document = _deep_document(
                key=key,
                app=app,
                app_store_id=app_store_id,
                app_store_url=app_store_url,
                item=item,
                canonical_url=canonical,
                site=site,
            )
            _, source_payload = _canonical_source(pages, canonical, site)
            document["coverage_role"] = "supporting-editorial"
            document["source_page_sha256"] = hashlib.sha256(
                source_payload
            ).hexdigest()
            documents.append(document)
            seen_urls.add(canonical)
            added += 1
            if added >= max_per_app:
                break

    documents.sort(key=lambda value: (
        str(value["app_key"]),
        str(value["canonical_url"]),
    ))
    lifecycle = _lifecycle_manifest(
        documents=documents,
        live_keys=live_keys,
        state=lifecycle_state,
        state_sha256=lifecycle_state_sha256,
        today=today or datetime.now(timezone.utc).date().isoformat(),
    )
    generated_at = _state_timestamp(lifecycle_state, now)
    primary_documents = [
        {
            "app_key": key,
            "canonical_url": reviewed[key]["guide_url"],
            "app_store_id": reviewed[key]["app_store_id"],
            "locale_tree_sha256": reviewed_surfaces[key][
                "locale_tree_sha256"
            ],
        }
        for key in live_keys
    ]
    manifest: dict[str, object] = {
        "schema_version": MANIFEST_VERSION,
        "generated_at": generated_at,
        "source": {
            "app_registry": "social/videogen/registry.py",
            "live_catalog": f"geo/pages/{LIVE_STATE_NAME}",
            "live_catalog_sha256": live_state_sha256,
            "reviewed_catalog": f"geo/pages/{REVIEWED_CATALOG_NAME}",
            "reviewed_catalog_sha256": reviewed_catalog_sha256,
            "editorial_catalog": "geo/answer_deep.py + geo/deep_items/*.json",
            "schema_sources": SCHEMA_SOURCES,
            "live_app_keys": live_keys,
            "live_app_count": len(live_keys),
            "official_locales": list(locales),
            "official_locale_count": len(locales),
            "official_locales_sha256": _hash_json(list(locales)),
            "policy": (
                "First-party, publisher-authored commercial guidance; "
                "not an independent ranking."
            ),
        },
        "coverage": {
            "required_app_count": expected_app_count,
            "eligible_app_count": len(primary_documents),
            "locale_count": len(locales),
            "primary_documents": primary_documents,
            "policy": (
                "Only exact-catalog App landing pages with exact official "
                "locale, identity, campaign, canonical, sitemap, and robots "
                "evidence count toward App coverage."
            ),
        },
        "lifecycle": lifecycle,
        "publication": {
            "url": site,
            "name": "Lumi Studio App Guides",
            "description": (
                "First-party long-form guidance from Lumi Studio about its "
                "verified live iOS apps. Commercial publisher-authored "
                "material; not an independent review or ranking."
            ),
            "preferences": {"showInDiscover": True},
        },
        "documents": documents,
    }
    manifest["public_get_plan"] = build_public_get_plan(
        pages=pages,
        site=site,
        documents=documents,
        lifecycle=lifecycle,
    )
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest: Mapping[str, object]) -> None:
    if manifest.get("schema_version") != MANIFEST_VERSION:
        raise ManifestError("Unsupported Standard.site manifest version")
    publication = manifest.get("publication")
    documents = manifest.get("documents")
    source = manifest.get("source")
    coverage = manifest.get("coverage")
    lifecycle = manifest.get("lifecycle")
    public_get_plan = manifest.get("public_get_plan")
    if not isinstance(publication, Mapping):
        raise ManifestError("Manifest publication must be an object")
    if not isinstance(documents, list) or not documents:
        raise ManifestError("Manifest must contain documents")
    if not isinstance(source, Mapping):
        raise ManifestError("Manifest source must be an object")
    if not isinstance(coverage, Mapping):
        raise ManifestError("Manifest coverage must be an object")
    if not isinstance(lifecycle, Mapping):
        raise ManifestError("Manifest lifecycle must be an object")
    if not isinstance(public_get_plan, Mapping):
        raise ManifestError("Manifest public_get_plan must be an object")
    site = str(publication.get("url") or "")
    if (
        not site.startswith("https://")
        or site.endswith("/")
        or not publication.get("name")
    ):
        raise ManifestError("Publication requires an HTTPS url and name")
    publication_name = str(publication["name"])
    if (
        len(publication_name) > 500
        or len(publication_name.encode("utf-8")) > 5000
    ):
        raise ManifestError("Publication name exceeds the lexicon limit")
    publication_description = str(publication.get("description") or "")
    if (
        len(publication_description) > 3000
        or len(publication_description.encode("utf-8")) > 30000
    ):
        raise ManifestError(
            "Publication description exceeds the lexicon limit"
        )
    preferences = publication.get("preferences")
    if not isinstance(preferences, Mapping) or not isinstance(
        preferences.get("showInDiscover"), bool
    ):
        raise ManifestError("Publication preferences are invalid")

    urls: set[str] = set()
    covered: set[str] = set()
    primary: dict[str, Mapping[str, object]] = {}
    for value in documents:
        if not isinstance(value, Mapping):
            raise ManifestError("Manifest document must be an object")
        missing = {
            field
            for field in (
                "app_key",
                "canonical_url",
                "path",
                "title",
                "description",
                "text_content",
                "app_store_id",
                "primary_app_store_url",
                "legacy_app_store_link",
                "tags",
                "content_hash",
                "coverage_role",
                "source_page_sha256",
            )
            if field not in value
        }
        if missing:
            raise ManifestError(
                f"Manifest document is missing: {sorted(missing)}"
            )
        canonical = str(value["canonical_url"])
        if canonical in urls:
            raise ManifestError(f"Duplicate canonical URL: {canonical}")
        urls.add(canonical)
        expected_path = canonical_path(canonical, site)
        if value["path"] != expected_path:
            raise ManifestError(
                f"Canonical path mismatch for {canonical}"
            )
        title = str(value["title"])
        description = str(value["description"])
        text = str(value["text_content"])
        if (
            not title
            or len(title) > 500
            or len(title.encode("utf-8")) > 5000
        ):
            raise ManifestError(f"Invalid title for {canonical}")
        if (
            len(description) > 3000
            or len(description.encode("utf-8")) > 30000
        ):
            raise ManifestError(f"Description is too long for {canonical}")
        if len(text) < 800:
            raise ManifestError(
                f"Document is not substantive long-form text: {canonical}"
            )
        app_store_id = str(value["app_store_id"])
        if re.fullmatch(r"[0-9]+", app_store_id) is None:
            raise ManifestError(
                f"Invalid App Store identifier for {canonical}"
            )
        try:
            validate_primary_app_store_url(
                text,
                app_id=app_store_id,
                expected_url=str(value["primary_app_store_url"]),
            )
            legacy_text_content(
                text,
                app_id=app_store_id,
                mode=str(value["legacy_app_store_link"]),
            )
        except AttributionError as error:
            raise ManifestError(
                f"Invalid primary App Store attribution for {canonical}: "
                f"{error}"
            ) from error
        lowered = text.casefold()
        if (
            "publisher disclosure:" not in lowered
            or "not an independent review" not in lowered
            or "developer of" not in lowered
        ):
            raise ManifestError(
                f"Publisher/commercial disclosure is incomplete: {canonical}"
            )
        tags = value["tags"]
        if (
            not isinstance(tags, list)
            or not tags
            or any(
                not isinstance(tag, str)
                or not tag
                or tag.startswith("#")
                or len(tag) > 128
                or len(tag.encode("utf-8")) > 1280
                for tag in tags
            )
        ):
            raise ManifestError(f"Invalid tags for {canonical}")
        if value["content_hash"] != document_content_hash(value):
            raise ManifestError(f"Content hash mismatch for {canonical}")
        source_page_sha256 = str(value["source_page_sha256"])
        if re.fullmatch(r"[0-9a-f]{64}", source_page_sha256) is None:
            raise ManifestError(
                f"Invalid source page digest for {canonical}"
            )
        app_key = str(value["app_key"])
        role = str(value["coverage_role"])
        if role not in {"app-primary", "supporting-editorial"}:
            raise ManifestError(
                f"Invalid coverage role for {canonical}: {role}"
            )
        if role == "app-primary":
            if app_key in primary:
                raise ManifestError(
                    f"App has multiple primary coverage documents: {app_key}"
                )
            locale_tree_sha256 = str(value.get("locale_tree_sha256") or "")
            if re.fullmatch(r"[0-9a-f]{64}", locale_tree_sha256) is None:
                raise ManifestError(
                    f"Primary document lacks locale-tree evidence: {canonical}"
                )
            primary[app_key] = value
        covered.add(app_key)

    live_keys = source.get("live_app_keys")
    if (
        not isinstance(live_keys, list)
        or len(live_keys) != len(set(map(str, live_keys)))
        or list(map(str, live_keys)) != sorted(map(str, live_keys))
        or set(map(str, live_keys)) != covered
    ):
        raise ManifestError(
            "Manifest does not fairly cover every verified live app"
        )
    live = set(map(str, live_keys))
    live_count = source.get("live_app_count")
    if type(live_count) is not int or live_count != len(live):
        raise ManifestError("Manifest live App denominator is inconsistent")
    for field in ("live_catalog_sha256", "reviewed_catalog_sha256"):
        if re.fullmatch(r"[0-9a-f]{64}", str(source.get(field) or "")) is None:
            raise ManifestError(f"Manifest source digest is invalid: {field}")
    locales = source.get("official_locales")
    locale_count = source.get("official_locale_count")
    if (
        not isinstance(locales, list)
        or len(locales) != len(set(map(str, locales)))
        or type(locale_count) is not int
        or locale_count != len(locales)
        or source.get("official_locales_sha256")
        != _hash_json(list(map(str, locales)))
    ):
        raise ManifestError("Manifest official locale authority is inconsistent")
    if (
        live_count == EXPECTED_LIVE_APP_COUNT
        and locale_count != EXPECTED_LOCALE_COUNT
    ):
        raise ManifestError(
            "Production manifest is not exact46 × exact50"
        )

    required_app_count = coverage.get("required_app_count")
    eligible_app_count = coverage.get("eligible_app_count")
    primary_rows = coverage.get("primary_documents")
    if (
        type(required_app_count) is not int
        or required_app_count != len(live)
        or type(eligible_app_count) is not int
        or eligible_app_count != len(live)
        or coverage.get("locale_count") != locale_count
        or not isinstance(primary_rows, list)
        or len(primary_rows) != len(live)
        or set(primary) != live
    ):
        raise ManifestError("Manifest exact-App coverage is inconsistent")
    reviewed_primary: dict[str, Mapping[str, object]] = {}
    for row in primary_rows:
        if not isinstance(row, Mapping):
            raise ManifestError("Manifest primary coverage row is invalid")
        app_key = str(row.get("app_key") or "")
        if app_key in reviewed_primary:
            raise ManifestError(
                f"Manifest repeats primary coverage row: {app_key}"
            )
        document = primary.get(app_key)
        if (
            document is None
            or row.get("canonical_url") != document["canonical_url"]
            or (
                required_app_count == EXPECTED_LIVE_APP_COUNT
                and document["path"] != f"/en-US/{app_key}.html"
            )
            or str(row.get("app_store_id") or "")
            != str(document["app_store_id"])
            or row.get("locale_tree_sha256")
            != document.get("locale_tree_sha256")
        ):
            raise ManifestError(
                f"Manifest primary coverage evidence drifted: {app_key}"
            )
        reviewed_primary[app_key] = row
    if set(reviewed_primary) != live:
        raise ManifestError("Manifest primary coverage omits a live App")

    state_loaded = lifecycle.get("state_loaded")
    if not isinstance(state_loaded, bool):
        raise ManifestError("Manifest lifecycle state_loaded must be boolean")
    tombstones = lifecycle.get("tombstones")
    if not isinstance(tombstones, list):
        raise ManifestError("Manifest lifecycle tombstones must be an array")
    tombstone_urls: set[str] = set()
    for tombstone in tombstones:
        if not isinstance(tombstone, Mapping):
            raise ManifestError("Manifest tombstone must be an object")
        canonical = str(tombstone.get("canonical_url") or "")
        app_key = str(tombstone.get("app_key") or "")
        rkey = str(tombstone.get("rkey") or "")
        fingerprint = str(tombstone.get("state_entry_sha256") or "")
        if (
            canonical in urls
            or canonical in tombstone_urls
            or app_key not in live
            or re.fullmatch(
                r"[234567abcdefghij][234567abcdefghijklmnopqrstuvwxyz]{12}",
                rkey,
            )
            is None
            or re.fullmatch(r"[0-9a-f]{64}", fingerprint) is None
            or not isinstance(
                tombstone.get("remote_record_expected"), bool
            )
        ):
            raise ManifestError(
                f"Manifest lifecycle tombstone is invalid: {canonical}"
            )
        tombstone_urls.add(canonical)
    if state_loaded:
        if (
            re.fullmatch(
                r"[0-9a-f]{64}",
                str(lifecycle.get("state_sha256") or ""),
            )
            is None
            or type(lifecycle.get("state_document_count")) is not int
            or type(lifecycle.get("active_state_document_count")) is not int
            or lifecycle.get("state_document_count")
            != lifecycle.get("active_state_document_count") + len(tombstones)
        ):
            raise ManifestError(
                "Manifest lifecycle state snapshot is inconsistent"
            )
        published_apps = lifecycle.get("published_app_keys")
        missing_published = lifecycle.get("missing_published_app_keys")
        publication_state = lifecycle.get("publication")
        if (
            not isinstance(published_apps, list)
            or not isinstance(missing_published, list)
            or set(map(str, published_apps))
            | set(map(str, missing_published))
            != live
            or set(map(str, published_apps))
            & set(map(str, missing_published))
        ):
            raise ManifestError(
                "Manifest lifecycle App publication denominator is inconsistent"
            )
        if lifecycle.get("published_document_count", 0):
            if (
                not isinstance(publication_state, Mapping)
                or re.fullmatch(
                    r"at://did:[a-z0-9:%._-]+/"
                    r"site\.standard\.publication/"
                    r"[234567abcdefghij]"
                    r"[234567abcdefghijklmnopqrstuvwxyz]{12}",
                    str(publication_state.get("at_uri") or ""),
                )
                is None
                or not str(
                    publication_state.get("well_known_url") or ""
                ).startswith("https://")
            ):
                raise ManifestError(
                    "Published lifecycle state lacks verification identity"
                )
    elif tombstones or lifecycle.get("state_sha256") is not None:
        raise ManifestError(
            "Manifest cannot claim tombstones without lifecycle state"
        )

    requests = public_get_plan.get("requests")
    if (
        public_get_plan.get("version") != PUBLIC_GET_PLAN_VERSION
        or not isinstance(requests, list)
        or public_get_plan.get("request_count") != len(requests)
    ):
        raise ManifestError("Manifest public GET plan is inconsistent")
    request_urls: set[str] = set()
    planned_documents: set[str] = set()
    planned_document_apps: dict[str, str] = {}
    kinds: dict[str, int] = {}
    for request in requests:
        if not isinstance(request, Mapping):
            raise ManifestError("Manifest public GET request is invalid")
        url = str(request.get("url") or "")
        if (
            not url
            or url in request_urls
            or request.get("expected_status") != 200
            or request.get("expected_final_url") != url
            or type(request.get("expected_bytes")) is not int
            or type(request.get("max_bytes")) is not int
            or int(request["max_bytes"]) <= int(request["expected_bytes"])
            or int(request["max_bytes"]) > MAX_PUBLIC_GET_BYTES + 1
            or re.fullmatch(
                r"[0-9a-f]{64}",
                str(request.get("expected_sha256") or ""),
            )
            is None
        ):
            raise ManifestError(f"Manifest public GET request is unsafe: {url}")
        request_urls.add(url)
        kind = str(request.get("kind") or "")
        kinds[kind] = kinds.get(kind, 0) + 1
        if kind == "document":
            planned_documents.add(url)
            planned_document_apps[url] = str(
                request.get("app_key") or ""
            )
    if planned_documents != urls:
        raise ManifestError(
            "Manifest public GET plan does not cover every active document"
        )
    document_apps = {
        str(document["canonical_url"]): str(document["app_key"])
        for document in documents
    }
    if planned_document_apps != document_apps:
        raise ManifestError(
            "Manifest public GET plan has inconsistent App identities"
        )
    for kind in ("publication", "reviewed-catalog", "robots", "sitemap"):
        if kinds.get(kind) != 1:
            raise ManifestError(
                f"Manifest public GET plan lacks one {kind} request"
            )
    lifecycle_publication = lifecycle.get("publication")
    if isinstance(lifecycle_publication, Mapping):
        if kinds.get("publication-verification") != 1:
            raise ManifestError(
                "Manifest public GET plan lacks publication verification"
            )
    elif kinds.get("publication-verification", 0):
        raise ManifestError(
            "Manifest public GET plan invents publication verification"
        )


def _trusted_public_get_url(url: str, *, site: str) -> None:
    base = urlsplit(site)
    parsed = urlsplit(url)
    publication_path = base.path.rstrip("/")
    allowed_prefix = publication_path + "/"
    well_known = (
        "/.well-known/site.standard.publication" + publication_path
    )
    if (
        parsed.scheme != "https"
        or parsed.hostname != base.hostname
        or parsed.port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or not (
            parsed.path.startswith(allowed_prefix)
            or parsed.path == well_known
        )
    ):
        raise ManifestError(f"Public GET URL is outside trusted origins: {url}")


def fetch_public_get(
    url: str,
    *,
    timeout: float,
    max_bytes: int,
) -> tuple[int, str, bytes, str]:
    opener = urllib.request.build_opener(_NoRedirect())
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/html,application/json,text/plain,*/*;q=0.1",
            "User-Agent": "lumi-standard-site-deploy-gate/1",
        },
    )
    try:
        with opener.open(request, timeout=timeout) as response:
            payload = response.read(max_bytes + 1)
            return (
                int(response.status),
                str(response.geturl()),
                payload,
                "",
            )
    except urllib.error.HTTPError as error:
        try:
            payload = error.read(max_bytes + 1)
            location = str(error.headers.get("Location") or "")
            return int(error.code), str(error.geturl()), payload, location
        finally:
            error.close()


def verify_public_get_plan(
    manifest: Mapping[str, object],
    *,
    timeout: float = DEFAULT_PUBLIC_GET_TIMEOUT,
    attempts: int = DEFAULT_PUBLIC_GET_ATTEMPTS,
    workers: int = DEFAULT_PUBLIC_GET_WORKERS,
    fetcher: Any = fetch_public_get,
    sleeper: Any = time.sleep,
) -> list[dict[str, object]]:
    validate_manifest(manifest)
    if timeout <= 0 or not 1 <= attempts <= 6 or not 1 <= workers <= 16:
        raise ManifestError("Public GET execution bounds are invalid")
    site = str(manifest["publication"]["url"])
    requests = list(manifest["public_get_plan"]["requests"])

    def verify_one(request: Mapping[str, object]) -> dict[str, object]:
        url = str(request["url"])
        _trusted_public_get_url(url, site=site)
        last_error = ""
        for attempt in range(attempts):
            try:
                status, final_url, payload, location = fetcher(
                    url,
                    timeout=timeout,
                    max_bytes=int(request["max_bytes"]),
                )
                if len(payload) > int(request["max_bytes"]):
                    raise ManifestError("response exceeded the bounded read")
                digest = hashlib.sha256(payload).hexdigest()
                problems: list[str] = []
                if status != request["expected_status"]:
                    problems.append(f"status={status}")
                if final_url != request["expected_final_url"]:
                    problems.append(f"final_url={final_url}")
                if location:
                    problems.append(f"redirect={location}")
                if len(payload) != request["expected_bytes"]:
                    problems.append(f"bytes={len(payload)}")
                if digest != request["expected_sha256"]:
                    problems.append(f"sha256={digest}")
                if not problems:
                    return {
                        "url": url,
                        "status": status,
                        "bytes": len(payload),
                        "sha256": digest,
                    }
                last_error = ", ".join(problems)
            except (
                ManifestError,
                OSError,
                UnicodeError,
                urllib.error.URLError,
            ) as error:
                last_error = f"{type(error).__name__}: {error}"
            if attempt + 1 < attempts:
                sleeper(float(2**attempt))
        raise ManifestError(f"Public GET failed closed for {url}: {last_error}")

    receipts: list[dict[str, object]] = []
    failures: list[str] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(verify_one, request): request
            for request in requests
        }
        for future in as_completed(futures):
            try:
                receipts.append(future.result())
            except Exception as error:
                failures.append(str(error))
    if failures:
        raise ManifestError(
            "Public GET deployment gate failed: "
            + " | ".join(sorted(failures)[:5])
        )
    receipts.sort(key=lambda value: str(value["url"]))
    return receipts


def _default_lifecycle_state() -> Path | None:
    root = os.environ.get("THREADS_AUTOPILOT_DIR", "").strip()
    if not root:
        return None
    return Path(root) / "standard_site_state.json"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate or write the Standard.site long-form manifest. "
            "Default: check-only with no filesystem changes."
        )
    )
    parser.add_argument("--pages", type=Path, default=DEFAULT_PAGES)
    parser.add_argument("--site", default=DEFAULT_SITE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--max-per-app", type=int, default=3)
    parser.add_argument(
        "--public-get-timeout",
        type=float,
        default=DEFAULT_PUBLIC_GET_TIMEOUT,
    )
    parser.add_argument(
        "--public-get-attempts",
        type=int,
        default=DEFAULT_PUBLIC_GET_ATTEMPTS,
    )
    parser.add_argument(
        "--public-get-workers",
        type=int,
        default=DEFAULT_PUBLIC_GET_WORKERS,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--write",
        action="store_true",
        help="atomically write the validated manifest",
    )
    mode.add_argument(
        "--check-only",
        action="store_true",
        help="validate only (the default)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    state_path = args.state or _default_lifecycle_state()
    lifecycle_state = None
    lifecycle_state_sha256 = None
    if state_path is not None:
        lifecycle_state, lifecycle_state_sha256 = load_lifecycle_state(
            state_path
        )
    elif args.write:
        raise ManifestError(
            "--write requires --state or THREADS_AUTOPILOT_DIR so lifecycle "
            "deletions cannot be guessed"
        )
    manifest = build_manifest(
        pages=args.pages,
        site=args.site,
        max_per_app=args.max_per_app,
        lifecycle_state=lifecycle_state,
        lifecycle_state_sha256=lifecycle_state_sha256,
    )
    documents = manifest["documents"]
    if args.write:
        receipts = verify_public_get_plan(
            manifest,
            timeout=args.public_get_timeout,
            attempts=args.public_get_attempts,
            workers=args.public_get_workers,
        )
        atomic_write_text(
            args.output,
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        )
        action = (
            f"verified {len(receipts)} public GETs; wrote {args.output}"
        )
    else:
        action = "check-only; wrote nothing"
    print(
        f"Standard.site manifest valid: "
        f"{manifest['source']['live_app_count']} apps, "
        f"{len(documents)} long-form documents; {action}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
