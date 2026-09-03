#!/usr/bin/env python3
"""Build a first-party long-form Standard.site manifest from verified GEO data.

The default mode validates and reports only. Use ``--write`` to persist the
manifest; this script never publishes records or authenticates to AT Protocol.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import unquote, urlsplit


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
    document_content_hash,
    ensure_primary_app_store_url,
    legacy_text_content,
    validate_primary_app_store_url,
)
from videogen.registry import APPS, APPSTORE  # noqa: E402


MANIFEST_VERSION = 1
def _default_public_site() -> str:
    """The Guide's public host, shared with the GEO generators.

    ``GEO_SITE`` still wins so the cloud workflows can pin a host; otherwise
    the single source in geo/site_config decides, and the old Pages origin
    is only the last-resort fallback for an isolated copy.
    """
    pinned = os.environ.get("GEO_SITE", "").strip()
    if pinned:
        return pinned.rstrip("/")
    try:
        import sys as _sys

        _geo = Path(__file__).resolve().parents[1] / "geo"
        if str(_geo) not in _sys.path:
            _sys.path.insert(0, str(_geo))
        from site_config import PUBLIC_SITE  # noqa: E402

        return PUBLIC_SITE.rstrip("/")
    except Exception:  # noqa: BLE001 - isolated copies have no geo/ beside them
        return "https://alice51849.github.io/ios-app-guide"


DEFAULT_SITE = _default_public_site()
DEFAULT_PAGES = Path(os.environ.get("GEO_PAGES", GEO / "pages"))
PRIVATE_DIR = Path(
    os.environ.get("GROWTH_PRIVATE_DIR", "~/.growth-private")
).expanduser()
DEFAULT_OUTPUT = PRIVATE_DIR / "standard-site-manifest.json"
LIVE_STATE_NAME = ".appstore_live_state.json"
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
    wanted = {str(value) for value in live_ids if str(value).strip()}
    live = sorted(
        key
        for key, app_id in appstore.items()
        if key in apps and str(app_id) in wanted
    )
    if not live:
        raise ManifestError(
            "Verified live-app catalog does not match the maintained registry"
        )
    return live, hashlib.sha256(raw).hexdigest()


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


def build_manifest(
    *,
    pages: Path = DEFAULT_PAGES,
    site: str = DEFAULT_SITE,
    apps: Mapping[str, Mapping[str, object]] = APPS,
    appstore: Mapping[str, object] = APPSTORE,
    deep_items: Iterable[Mapping[str, object]] = DEEP_ITEMS,
    max_per_app: int = 3,
    now: datetime | None = None,
) -> dict[str, object]:
    if not 1 <= max_per_app <= 4:
        raise ManifestError("max_per_app must be between 1 and 4")
    site = site.rstrip("/")
    live_keys, live_state_sha256 = load_live_app_keys(
        pages, appstore, apps
    )
    documents: list[dict[str, object]] = []
    seen_urls: set[str] = set()

    for key in live_keys:
        app = apps[key]
        if not _compact(app.get("name")):
            raise ManifestError(f"Live app has no name: {key}")
        app_store_id = str(appstore[key]).strip()
        app_store_url = _store_url(app_store_id)
        added = 0
        for item in _deep_candidates(deep_items, key):
            canonical = (
                f"{site}/answers/{slugify(str(item['query']))}.html"
            )
            if canonical in seen_urls or not _canonical_is_deployed(
                pages, canonical, site
            ):
                continue
            documents.append(
                _deep_document(
                    key=key,
                    app=app,
                    app_store_id=app_store_id,
                    app_store_url=app_store_url,
                    item=item,
                    canonical_url=canonical,
                    site=site,
                )
            )
            seen_urls.add(canonical)
            added += 1
            if added >= max_per_app:
                break
        if added == 0:
            canonical = _fallback_canonical(pages, site, key)
            if not canonical:
                raise ManifestError(
                    f"No deployed canonical GEO page for live app: {key}"
                )
            if canonical in seen_urls:
                raise ManifestError(
                    f"Duplicate fallback canonical URL: {canonical}"
                )
            documents.append(
                _fallback_document(
                    key=key,
                    app=app,
                    app_store_id=app_store_id,
                    app_store_url=app_store_url,
                    canonical_url=canonical,
                    site=site,
                )
            )
            seen_urls.add(canonical)

    documents.sort(key=lambda value: (
        str(value["app_key"]),
        str(value["canonical_url"]),
    ))
    generated_at = _utc(now)
    manifest: dict[str, object] = {
        "schema_version": MANIFEST_VERSION,
        "generated_at": generated_at,
        "source": {
            "app_registry": "social/videogen/registry.py",
            "live_catalog": f"geo/pages/{LIVE_STATE_NAME}",
            "live_catalog_sha256": live_state_sha256,
            "editorial_catalog": "geo/answer_deep.py + geo/deep_items/*.json",
            "schema_sources": SCHEMA_SOURCES,
            "live_app_keys": live_keys,
            "live_app_count": len(live_keys),
            "policy": (
                "First-party, publisher-authored commercial guidance; "
                "not an independent ranking."
            ),
        },
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
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest: Mapping[str, object]) -> None:
    if manifest.get("schema_version") != MANIFEST_VERSION:
        raise ManifestError("Unsupported Standard.site manifest version")
    publication = manifest.get("publication")
    documents = manifest.get("documents")
    source = manifest.get("source")
    if not isinstance(publication, Mapping):
        raise ManifestError("Manifest publication must be an object")
    if not isinstance(documents, list) or not documents:
        raise ManifestError("Manifest must contain documents")
    if not isinstance(source, Mapping):
        raise ManifestError("Manifest source must be an object")
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
        covered.add(str(value["app_key"]))

    live_keys = source.get("live_app_keys")
    if not isinstance(live_keys, list) or set(map(str, live_keys)) != covered:
        raise ManifestError(
            "Manifest does not fairly cover every verified live app"
        )


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
    parser.add_argument("--max-per-app", type=int, default=3)
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
    manifest = build_manifest(
        pages=args.pages,
        site=args.site,
        max_per_app=args.max_per_app,
    )
    documents = manifest["documents"]
    if args.write:
        atomic_write_text(
            args.output,
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        )
        action = f"wrote {args.output}"
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
