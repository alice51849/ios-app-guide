#!/usr/bin/env python3
"""Repair stale Answer metadata and fail closed on cross-topic pollution."""

from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import re

import aeo_answers
import aeo_answers_i18n
import sync_standard_site
from answer_app_store_links import (
    direct_app_store_ids,
    unmanaged_app_store_source,
)
from answer_text import (
    concise_meta,
    is_malformed_meta,
    is_malformed_localized_meta,
)
from videogen.registry import APPS, APPSTORE


HERE = Path(__file__).resolve().parent
PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages")).resolve()
META_TAG_RE = re.compile(r"<meta\b[^>]*>", flags=re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>", flags=re.DOTALL)
ANSWER_CONTENT_RE = re.compile(
    r"<!-- answer-content:start -->(.*?)<!-- answer-content:end -->",
    flags=re.IGNORECASE | re.DOTALL,
)
DOCUMENT_PHOTO_TITLE_RE = re.compile(
    r"(?:passport|visa|id(?:entity)? photo|photo id|"
    r"citizenship photo|naturalization photo|driver licen[cs]e photo|"
    r"residence permit photo|settlement.{0,20}photo|brp photo|"
    r"green card photo|oci (?:card )?photo|pan card photo|"
    r"rirekisho photo|resume.{0,20}photo|"
    r"photo.{0,30}(?:print sheet|cut guide))",
    flags=re.IGNORECASE,
)
PASSPORT_SIGNAL_RES = tuple(
    re.compile(pattern, flags=re.IGNORECASE)
    for pattern in (
        r"\bpassport\b",
        r"\bvisa\b",
        r"51(?:\u00d7|x)51",
        r"plain white background",
        r"head (?:height|size)",
        r"print sheet",
        r"\bid photo\b",
        r"photo crop",
    )
)


def _attribute(tag: str, name: str) -> str | None:
    match = re.search(
        rf"\b{re.escape(name)}\s*=\s*([\"'])(.*?)\1",
        tag,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return html.unescape(match.group(2)) if match else None


def _replace_content_attribute(tag: str, value: str) -> str:
    escaped = html.escape(value, quote=True)
    pattern = re.compile(
        r"(\bcontent\s*=\s*)([\"'])(.*?)\2",
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not pattern.search(tag):
        raise ValueError(f"Description meta tag has no content attribute: {tag}")
    return pattern.sub(
        lambda match: (
            f"{match.group(1)}{match.group(2)}"
            f"{escaped}{match.group(2)}"
        ),
        tag,
        count=1,
    )


def meta_description(source: str) -> str:
    values = [
        _attribute(tag, "content")
        for tag in META_TAG_RE.findall(source)
        if (_attribute(tag, "name") or "").casefold() == "description"
    ]
    if len(values) != 1 or values[0] is None:
        raise ValueError(
            f"Answer must have exactly one meta description; found {len(values)}"
        )
    return values[0]


def canonical_url(source: str) -> str:
    values = [
        _attribute(tag, "href")
        for tag in re.findall(
            r"<link\b[^>]*>",
            source,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if "canonical" in (_attribute(tag, "rel") or "").casefold().split()
    ]
    if len(values) != 1 or values[0] is None:
        raise ValueError(
            f"Answer must have exactly one canonical URL; found {len(values)}"
        )
    return values[0]


def _json_dicts(value: object):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _json_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _json_dicts(child)


def localized_structured_data_url_issues(source: str) -> list[str]:
    """Validate page-owned JSON-LD URLs directly against the canonical."""
    canonical = canonical_url(source)
    issues: list[str] = []
    for index, match in enumerate(
        aeo_answers_i18n.JSON_LD_SCRIPT_RE.finditer(source),
        start=1,
    ):
        try:
            document = json.loads(match.group("body"))
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid Answer JSON-LD script {index}: {exc}"
            ) from exc
        for node in _json_dicts(document):
            schema_type = node.get("@type")
            schema_types = set(
                schema_type if isinstance(schema_type, list) else [schema_type]
            )
            if "WebPage" in schema_types:
                if node.get("@id") != f"{canonical}#webpage":
                    issues.append(f"WebPage @id in script {index}")
                if node.get("url") != canonical:
                    issues.append(f"WebPage url in script {index}")
            if "Article" not in schema_types or "mainEntityOfPage" not in node:
                continue
            main_page = node["mainEntityOfPage"]
            if isinstance(main_page, str):
                if main_page != canonical:
                    issues.append(
                        f"Article mainEntityOfPage in script {index}"
                    )
            elif isinstance(main_page, dict):
                if main_page.get("@id") != f"{canonical}#webpage":
                    issues.append(
                        f"Article mainEntityOfPage @id in script {index}"
                    )
                if "url" in main_page and main_page.get("url") != canonical:
                    issues.append(
                        f"Article mainEntityOfPage url in script {index}"
                    )
            else:
                issues.append(f"Article mainEntityOfPage type in script {index}")
    return issues


def _plain_text(fragment: str) -> str:
    return " ".join(html.unescape(TAG_RE.sub(" ", fragment)).split())


def _element_text(source: str, tag_name: str) -> str:
    match = re.search(
        rf"<{tag_name}\b[^>]*>(.*?)</{tag_name}>",
        source,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not match:
        raise ValueError(f"Answer has no {tag_name} element")
    return _plain_text(match.group(1))


def answer_lead(source: str) -> str:
    for match in re.finditer(
        r"<p\b[^>]*>(.*?)</p>",
        source,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        start_tag = source[match.start() : source.find(">", match.start()) + 1]
        classes = (_attribute(start_tag, "class") or "").split()
        if "lead" in classes:
            lead = _plain_text(match.group(1))
            if lead:
                return lead
    raise ValueError("Answer has no non-empty lead paragraph")


def answer_content_text(source: str) -> str:
    match = ANSWER_CONTENT_RE.search(source)
    return _plain_text(match.group(1) if match else source)


def has_cross_topic_passport_content(source: str) -> bool:
    title = _element_text(source, "h1")
    if DOCUMENT_PHOTO_TITLE_RE.search(title):
        return False
    body = answer_content_text(source)
    return sum(bool(pattern.search(body)) for pattern in PASSPORT_SIGNAL_RES) >= 3


def unexpected_portfolio_apps_in_lead(
    source: str,
    path: Path | str | None = None,
) -> list[str]:
    ids = direct_app_store_ids(unmanaged_app_store_source(source), path)
    if len(ids) != 1:
        return []
    id_to_key = {str(app_id): key for key, app_id in APPSTORE.items()}
    key = id_to_key.get(next(iter(ids)))
    if key is None:
        return []
    expected_name = APPS[key]["name"].casefold()
    lead = answer_lead(source)
    unexpected: list[str] = []
    for other_key, app in APPS.items():
        name = app["name"]
        if (
            other_key == key
            or name.casefold() in expected_name
            or len(name) < 4
        ):
            continue
        if re.search(
            rf"(?<![\w]){re.escape(name)}(?![\w])",
            lead,
            flags=re.IGNORECASE,
        ):
            unexpected.append(name)
    return sorted(
        name
        for name in unexpected
        if not any(
            name != other and name.casefold() in other.casefold()
            for other in unexpected
        )
    )


def _replace_description_metadata(
    source: str,
    old_description: str,
    new_description: str,
) -> str:
    base_count = 0

    def replace_meta(match: re.Match[str]) -> str:
        nonlocal base_count
        tag = match.group(0)
        name = (_attribute(tag, "name") or "").casefold()
        property_name = (_attribute(tag, "property") or "").casefold()
        if name == "description":
            base_count += 1
            return _replace_content_attribute(tag, new_description)
        if property_name == "og:description" or name == "twitter:description":
            return _replace_content_attribute(tag, new_description)
        return tag

    updated = META_TAG_RE.sub(replace_meta, source)
    if base_count != 1:
        raise ValueError(
            f"Answer must update exactly one meta description; found {base_count}"
        )

    old_json = json.dumps(old_description, ensure_ascii=False)
    new_json = json.dumps(new_description, ensure_ascii=False)
    updated = re.sub(
        r'("description"\s*:\s*)' + re.escape(old_json),
        lambda match: match.group(1) + new_json,
        updated,
    )
    return updated


def planned_page_metadata_repair(
    path: Path,
    force: bool = False,
    english: bool = True,
    source: str | None = None,
) -> str | None:
    if source is None:
        source = path.read_text(encoding="utf-8")
    if aeo_answers.is_redirect_html(source):
        return None
    old_description = meta_description(source)
    lead = answer_lead(source)
    locale = path.parent.parent.name if not english else "en"
    malformed = (
        is_malformed_meta(old_description)
        if english
        else is_malformed_localized_meta(old_description, locale, lead)
    )
    if not force and not malformed:
        return None
    replacement = concise_meta(lead, hard_limit=320)
    replacement_is_malformed = (
        is_malformed_meta(replacement)
        if english
        else is_malformed_localized_meta(replacement, locale, lead)
    )
    if replacement_is_malformed:
        raise ValueError(f"Repair still leaves malformed metadata: {path}")
    updated = _replace_description_metadata(
        source,
        old_description,
        replacement,
    )
    return updated if updated != source else None


def repair_page_metadata(
    path: Path,
    force: bool = False,
    english: bool = True,
) -> bool:
    updated = planned_page_metadata_repair(path, force, english)
    if updated is None:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def _english_answer_paths(pages: Path) -> list[Path]:
    answers = pages / "answers"
    return sorted(
        path
        for path in answers.glob("*.html")
        if path.name != "index.html"
    )


def _localized_answer_dirs(pages: Path) -> list[Path]:
    return sorted(
        path / "answers"
        for path in pages.iterdir()
        if path.is_dir() and (path / "answers").is_dir()
    )


def _app_key(source: str, path: Path) -> str:
    ids = direct_app_store_ids(unmanaged_app_store_source(source), path)
    if len(ids) != 1:
        raise ValueError(
            f"Cross-topic Answer must resolve to one App Store ID: {path}: "
            f"{sorted(ids)}"
        )
    id_to_key = {str(app_id): key for key, app_id in APPSTORE.items()}
    if len(id_to_key) != len(APPSTORE):
        raise ValueError("Answer App Store IDs must be unique")
    app_id = next(iter(ids))
    if app_id not in id_to_key:
        raise ValueError(f"Unknown App Store ID in {path}: {app_id}")
    return id_to_key[app_id]


def _localized_copies(pages: Path, slug: str) -> list[Path]:
    return [
        directory / f"{slug}.html"
        for directory in _localized_answer_dirs(pages)
        if (directory / f"{slug}.html").is_file()
    ]


def refresh_cross_topic_page(
    path: Path,
    pages: Path,
    source: str | None = None,
) -> bool:
    if source is None:
        source = path.read_text(encoding="utf-8")
    if not has_cross_topic_passport_content(source):
        return False
    localized = _localized_copies(pages, path.stem)
    if localized:
        raise ValueError(
            "Cross-topic Answer has localized copies that require curated "
            f"translation: {path.stem}: "
            + ", ".join(str(item) for item in localized)
        )
    question = _element_text(source, "h1")
    if aeo_answers.slugify(question) != path.stem:
        raise ValueError(f"Answer H1 does not match its slug: {path}")
    key = _app_key(source, path)
    content = aeo_answers.normalized_content(
        aeo_answers.default_content(question, key),
        question,
        key,
    )
    rendered = aeo_answers.render_page(
        question,
        key,
        content,
        pages_root=pages,
    )
    rendered = sync_standard_site.preserve_managed_links(
        source,
        rendered,
        label=str(path),
    )
    path.write_text(rendered, encoding="utf-8")
    return True


def _audit_english_source(
    issues: list[dict[str, str]],
    path: Path,
    source: str,
) -> None:
    if aeo_answers.is_redirect_html(source):
        return
    try:
        description = meta_description(source)
        if is_malformed_meta(description):
            issues.append(
                {
                    "path": str(path),
                    "code": "malformed-meta",
                    "detail": description,
                }
            )
        if has_cross_topic_passport_content(source):
            issues.append(
                {
                    "path": str(path),
                    "code": "cross-topic-passport",
                    "detail": _element_text(source, "h1"),
                }
            )
        unexpected_apps = unexpected_portfolio_apps_in_lead(source, path)
        if unexpected_apps:
            issues.append(
                {
                    "path": str(path),
                    "code": "cross-app-lead",
                    "detail": ", ".join(unexpected_apps),
                }
            )
    except ValueError as exc:
        issues.append(
            {
                "path": str(path),
                "code": "invalid-answer",
                "detail": str(exc),
            }
        )


def _audit_localized_source(
    issues: list[dict[str, str]],
    path: Path,
    source: str,
    locale: str,
) -> None:
    if aeo_answers.is_redirect_html(source):
        return
    try:
        description = meta_description(source)
        if is_malformed_localized_meta(
            description,
            locale,
            answer_lead(source),
        ):
            issues.append(
                {
                    "path": str(path),
                    "code": "malformed-localized-meta",
                    "detail": description,
                }
            )
        expected_microformat = aeo_answers_i18n.reconcile_microformat_url(
            source,
            locale,
            path.stem,
        )
        if expected_microformat != source:
            issues.append(
                {
                    "path": str(path),
                    "code": "localized-microformat-url",
                    "detail": aeo_answers_i18n.page_url(
                        path.stem,
                        locale,
                    ),
                }
            )
        structured_data_issues = localized_structured_data_url_issues(source)
        if structured_data_issues:
            issues.append(
                {
                    "path": str(path),
                    "code": "localized-structured-data-url",
                    "detail": ", ".join(structured_data_issues),
                }
            )
        unexpected_apps = unexpected_portfolio_apps_in_lead(source, path)
        if unexpected_apps:
            issues.append(
                {
                    "path": str(path),
                    "code": "cross-app-localized-lead",
                    "detail": ", ".join(unexpected_apps),
                }
            )
    except ValueError as exc:
        issues.append(
            {
                "path": str(path),
                "code": "invalid-localized-answer",
                "detail": str(exc),
            }
        )


def audit_pages(pages: Path = PAGES) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for path in _english_answer_paths(pages):
        _audit_english_source(
            issues,
            path,
            path.read_text(encoding="utf-8"),
        )
    for directory in _localized_answer_dirs(pages):
        locale = directory.parent.name
        for path in sorted(directory.glob("*.html")):
            if path.name != "index.html":
                _audit_localized_source(
                    issues,
                    path,
                    path.read_text(encoding="utf-8"),
                    locale,
                )
    return issues


def repair(pages: Path = PAGES) -> dict[str, int]:
    english_paths = _english_answer_paths(pages)
    refreshed = 0
    operations: list[tuple[Path, str, bool]] = []
    issues: list[dict[str, str]] = []
    for path in english_paths:
        source = path.read_text(encoding="utf-8")
        if refresh_cross_topic_page(path, pages, source):
            refreshed += 1
            source = path.read_text(encoding="utf-8")
        updated = planned_page_metadata_repair(path, source=source)
        if updated is not None:
            operations.append((path, updated, True))
        _audit_english_source(issues, path, updated or source)
    localized_metadata = 0
    localized_microformats = 0
    localized_structured_data = 0
    for directory in _localized_answer_dirs(pages):
        locale = directory.parent.name
        for path in sorted(directory.glob("*.html")):
            if path.name == "index.html":
                continue
            source = path.read_text(encoding="utf-8")
            updated = planned_page_metadata_repair(
                path,
                english=False,
                source=source,
            )
            metadata_source = updated if updated is not None else source
            reconciled = aeo_answers_i18n.reconcile_microformat_url(
                metadata_source,
                locale,
                path.stem,
            )
            structured = aeo_answers_i18n.reconcile_structured_data_urls(
                reconciled,
                locale,
                path.stem,
            )
            if updated is not None:
                localized_metadata += 1
            if reconciled != metadata_source:
                localized_microformats += 1
            if structured != reconciled:
                localized_structured_data += 1
            if updated is not None or structured != source:
                operations.append((path, structured, False))
            _audit_localized_source(issues, path, structured, locale)
    for path, updated, _ in operations:
        path.write_text(updated, encoding="utf-8")
    english_metadata = sum(int(english) for _, _, english in operations)
    if refreshed:
        aeo_answers.regenerate_index(pages)
        aeo_answers.write_sitemap(pages)
    if issues:
        sample = json.dumps(issues[:10], ensure_ascii=False, indent=2)
        raise RuntimeError(
            f"Answer semantic integrity gate failed ({len(issues)}):\n{sample}"
        )
    return {
        "refreshed_cross_topic": refreshed,
        "repaired_english_metadata": english_metadata,
        "repaired_localized_metadata": localized_metadata,
        "repaired_localized_microformats": localized_microformats,
        "repaired_localized_structured_data": localized_structured_data,
        "remaining_issues": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pages",
        type=Path,
        default=PAGES,
        help="Alternate Pages checkout.",
    )
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Repair safe deterministic defects before enforcing the gate.",
    )
    args = parser.parse_args()
    pages = args.pages.resolve()
    if args.repair:
        print(json.dumps(repair(pages), sort_keys=True))
        return 0
    issues = audit_pages(pages)
    if issues:
        print(json.dumps(issues, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps({"issues": 0}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
