#!/usr/bin/env python3
"""Replace legacy independence claims with truthful publisher disclosures."""

from __future__ import annotations

import argparse
from collections import defaultdict
import html
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Iterable

from official_locales import OFFICIAL_LOCALES


HERE = Path(__file__).resolve().parent
PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
I18N_DIR = HERE / "i18n_trans"

OLD_NOTICE = "This page is an independent buying guide."
NEW_NOTICE = (
    "This is a publisher-authored buying guide from the app developer. "
    "App Store features and prices can change, so confirm details on the "
    "listing before purchase."
)
OLD_FOOTER = (
    "Independent guide. App names are trademarks of their owners and are "
    "used only for identification. For documents, health, school, and "
    "productivity decisions, verify official requirements where relevant."
)
NEW_FOOTER = (
    "Publisher-authored guide from Lumi Studio, the app developer. App names "
    "are trademarks of their owners and are used only for identification. "
    "For documents, health, school, and productivity decisions, verify "
    "official requirements where relevant."
)
OLD_GUIDE_FOOTER = (
    "Independent guide. App names are trademarks of their owners, used for "
    "identification only."
)
OLD_GENERIC_PREFIX = "Independent guide."
NEW_GENERIC_PREFIX = (
    "Publisher-authored guide from Lumi Studio, the app developer."
)
OLD_APP_GUIDE_PREFIX = "Independent guide by the developer of "
OLD_APP_GUIDE_SUFFIX = (
    ". App names are trademarks of their owners and are used only for "
    "identification. Pricing and features can change — confirm on the App "
    "Store listing."
)
NEW_AIM990_NOTICE = (
    f"{NEW_NOTICE} TOEIC is a registered trademark of ETS. Aim990 is an "
    "independent study aid and is not affiliated with or endorsed by ETS. "
    "No app can guarantee a TOEIC score."
)
AIM990_APP_IDS = frozenset({"6784974530", "6792483140"})
LEGACY_DOUBLED_AIM990_NOTICE = (
    f"{NEW_NOTICE} App Store features and prices can change, so confirm "
    "details on the listing before purchase. TOEIC is a registered trademark "
    "of ETS. Aim990 is an independent study aid and is not affiliated with or "
    "endorsed by ETS. No app can guarantee a TOEIC score."
)
DISCLOSURE_TRANSLATION_OVERRIDES = {
    "fr-CA": {
        NEW_NOTICE: (
            "Ce guide d'achat est rédigé par le développeur de l'app. Les "
            "fonctionnalités et les prix sur l'App Store peuvent changer; "
            "vérifiez les détails de la fiche avant d'acheter."
        ),
        NEW_FOOTER: (
            "Guide rédigé par Lumi Studio, le développeur de l'app. Les noms "
            "d'apps sont des marques de commerce de leurs propriétaires et "
            "servent uniquement à les identifier. Pour les décisions "
            "concernant les documents, la santé, l'école et la productivité, "
            "vérifiez les exigences officielles applicables."
        ),
        NEW_AIM990_NOTICE: (
            "Ce guide d'achat est rédigé par le développeur de l'app. Les "
            "fonctionnalités et les prix sur l'App Store peuvent changer; "
            "vérifiez les détails de la fiche avant d'acheter. TOEIC est une "
            "marque déposée d'ETS. Aim990 est un outil d'étude indépendant "
            "qui n'est ni affilié à ETS ni approuvé par ETS. Aucune app ne "
            "peut garantir un résultat au TOEIC."
        ),
    },
}
TARGETS = (
    (OLD_NOTICE, NEW_NOTICE),
    (OLD_FOOTER, NEW_FOOTER),
    (OLD_GUIDE_FOOTER, NEW_FOOTER),
    (OLD_GENERIC_PREFIX, NEW_GENERIC_PREFIX),
)
DISCLOSURE_NEEDLES = (
    OLD_NOTICE,
    NEW_NOTICE,
    OLD_FOOTER,
    NEW_FOOTER,
    OLD_GUIDE_FOOTER,
    OLD_GENERIC_PREFIX,
    OLD_APP_GUIDE_PREFIX,
)
CONTENT_PATHSPECS = (":(glob)**/*.html",)
ANSWER_ARTICLE_MARKER = '<article class="card two answer">'
PUBLISHER_MARKER = 'data-publisher-disclosure="true"'
NOTICE_RE = re.compile(r'<p class="notice">(?P<text>[^<]*)</p>')
FOOTER_RE = re.compile(
    r'<footer class="footer">.*?</footer>',
    re.DOTALL,
)
FOOTER_TEXT_RE = re.compile(
    r'<footer class="footer">.*?<div class="wrap"[^>]*>'
    r"(?P<text>.*?)</div>.*?</footer>",
    re.DOTALL,
)
TERMINAL_SMALL_RE = re.compile(
    r"<p(?:\s+[^>]*)?><small>[^<]*</small></p>\s*</main>",
    re.DOTALL,
)
PRE_MANAGED_GUIDE_DISCLOSURE_RE = re.compile(
    r'(?P<hr><hr(?:\s+[^>]*)?>\s*)'
    r'<p(?![^>]*\bdata-publisher-disclosure="true")[^>]*>'
    r"\s*<small>[^<]*</small>\s*</p>"
    r"(?=\s*<!--\s*app-store-qr:start\s*-->)",
    re.IGNORECASE | re.DOTALL,
)
AUTHOR_CARD = (
    '<data class="p-author h-card vcard" value="Lumi Studio">'
    '<data class="p-name p-org fn org" value="Lumi Studio"></data>'
    '<data class="u-url url" '
    'value="https://alice51849.github.io/ios-app-guide/about.html"></data>'
    "</data>"
)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?।。؟۔])\s+")
ENGLISH_APP_GUIDE_RE = re.compile(
    re.escape(OLD_APP_GUIDE_PREFIX)
    + r".+?"
    + re.escape(OLD_APP_GUIDE_SUFFIX)
)


def _locale_for(path: Path, pages: Path) -> str:
    first = path.relative_to(pages).parts[0]
    return first if first in OFFICIAL_LOCALES else "en-US"


def _section_for(path: Path, pages: Path) -> str:
    parts = path.relative_to(pages).parts
    if parts[0] in {"answers", "guides", "hubs"}:
        return parts[0]
    return parts[1] if len(parts) > 1 else ""


def _translations(locale: str, translations_dir: Path) -> dict[str, str]:
    if locale.startswith("en-"):
        return {}
    path = translations_dir / f"{locale}.json"
    payload = (
        json.loads(path.read_text(encoding="utf-8"))
        if path.is_file()
        else {}
    )
    if not isinstance(payload, dict):
        raise ValueError(f"Translation dictionary must be an object: {path}")
    payload.update(DISCLOSURE_TRANSLATION_OVERRIDES.get(locale, {}))
    doubled = payload.get(LEGACY_DOUBLED_AIM990_NOTICE)
    if (
        isinstance(doubled, str)
        and doubled.strip()
    ):
        sentences = SENTENCE_SPLIT_RE.split(doubled.strip())
        if len(sentences) >= 5 and sentences[1] == sentences[2]:
            corrected = {
                NEW_NOTICE: " ".join(sentences[:2]),
                NEW_AIM990_NOTICE: " ".join(
                    sentences[:2] + sentences[3:]
                ),
            }
            for key, value in corrected.items():
                current = payload.get(key)
                current_sentences = (
                    SENTENCE_SPLIT_RE.split(current.strip())
                    if isinstance(current, str) and current.strip()
                    else []
                )
                if (
                    current is None
                    or current == doubled
                    or (
                        len(current_sentences) >= 3
                        and current_sentences[1] == current_sentences[2]
                    )
                ):
                    payload[key] = value
    return payload


def _localized(
    source: str,
    locale: str,
    translations: dict[str, str],
) -> tuple[str, bool]:
    value = translations.get(source)
    if value is None:
        return source, not locale.startswith("en-")
    if not isinstance(value, str) or not value.strip() or "\n" in value:
        raise ValueError(f"Invalid one-line disclosure for {locale}: {source}")
    return value.strip(), False


def _section_pages(pages: Path, section: str) -> list[Path]:
    roots = [pages / section]
    roots.extend(pages / locale / section for locale in OFFICIAL_LOCALES)
    return sorted(
        path
        for root in roots
        if root.is_dir()
        for path in root.rglob("*.html")
    )


def _answer_pages(pages: Path) -> list[Path]:
    return _section_pages(pages, "answers")


def _content_pages(pages: Path) -> list[Path]:
    return sorted(pages.rglob("*.html"))


def _git_candidate_pages(
    pages: Path,
    all_pages: list[Path],
    *,
    needles: Iterable[str] = DISCLOSURE_NEEDLES,
) -> list[Path] | None:
    try:
        top_level = subprocess.run(
            ["git", "-C", str(pages), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    if Path(top_level).resolve() != pages.resolve():
        return None

    needle_list = sorted(set(needles))
    grep_command = [
        "git",
        "-C",
        str(pages),
        "grep",
        "-l",
        "-z",
        "-F",
    ]
    for needle in needle_list:
        grep_command.extend(("-e", needle))
    grep_command.extend(("--", *CONTENT_PATHSPECS))
    try:
        tracked = subprocess.run(
            grep_command,
            check=False,
            capture_output=True,
        )
        if tracked.returncode not in {0, 1}:
            return None
        untracked = subprocess.run(
            [
                "git",
                "-C",
                str(pages),
                "ls-files",
                "--others",
                "-z",
                "--",
                *CONTENT_PATHSPECS,
            ],
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    relative_paths = {
        value.decode("utf-8")
        for value in tracked.stdout.split(b"\0")
        if value
    }
    for value in untracked.stdout.split(b"\0"):
        if not value:
            continue
        relative = value.decode("utf-8")
        path = pages / relative
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None
        if any(needle in source for needle in needle_list):
            relative_paths.add(relative)

    known_pages = {path.relative_to(pages).as_posix(): path for path in all_pages}
    if not relative_paths.issubset(known_pages):
        return None
    return [known_pages[relative] for relative in sorted(relative_paths)]


def _publisher_footer(text: str) -> str:
    return (
        f'<footer class="footer">{AUTHOR_CARD}'
        f'<div class="wrap" {PUBLISHER_MARKER}>'
        f"{html.escape(text, quote=False)}</div></footer>"
    )


def _is_aim990_page(source: str) -> bool:
    return any(f"/id{app_id}" in source for app_id in AIM990_APP_IDS)


def _discover_structural_legacy(
    answer_pages: Iterable[Path],
    pages: Path,
    translations_dir: Path,
) -> dict[str, dict[str, set[str]]]:
    by_locale: dict[str, list[Path]] = defaultdict(list)
    for path in answer_pages:
        by_locale[_locale_for(path, pages)].append(path)

    discovered: dict[str, dict[str, set[str]]] = {}
    for locale, paths in by_locale.items():
        translations = _translations(locale, translations_dir)
        expected_notice, _ = _localized(NEW_NOTICE, locale, translations)
        expected_aim990, _ = _localized(
            NEW_AIM990_NOTICE,
            locale,
            translations,
        )
        expected_footer, _ = _localized(NEW_FOOTER, locale, translations)
        expected_notices = {
            html.escape(expected_notice, quote=False),
            html.escape(expected_aim990, quote=False),
        }
        expected_footer_html = html.escape(expected_footer, quote=False)
        notices: set[str] = set()
        footers: set[str] = set()
        index = next((path for path in paths if path.name == "index.html"), None)
        probes = ([index] if index is not None else [])
        probes.extend(path for path in paths if path != index)
        for path in probes:
            source = path.read_text(encoding="utf-8")
            footer_match = FOOTER_TEXT_RE.search(source)
            if footer_match:
                text = footer_match.group("text")
                if text != expected_footer_html:
                    footers.add(text)
            if ANSWER_ARTICLE_MARKER not in source:
                continue
            notice_match = NOTICE_RE.search(source)
            if notice_match:
                text = notice_match.group("text")
                if text not in expected_notices:
                    notices.add(text)
            break
        if notices or footers:
            discovered[locale] = {
                "notice": notices,
                "footer": footers,
            }
    return discovered


def _legacy_needles(
    translations_dir: Path,
    structural: dict[str, dict[str, set[str]]],
) -> set[str]:
    needles = {
        *(old for old, _ in TARGETS),
        "Independent guide",
        "independent guide",
    }
    for locale in OFFICIAL_LOCALES:
        translations = _translations(locale, translations_dir)
        for old, _ in TARGETS[:2]:
            translated = translations.get(old)
            if isinstance(translated, str) and translated.strip():
                needles.add(translated)
        for source, translated in translations.items():
            if (
                source.startswith(OLD_APP_GUIDE_PREFIX)
                and source.endswith(OLD_APP_GUIDE_SUFFIX)
            ):
                needles.add(source)
                if isinstance(translated, str) and translated.strip():
                    needles.add(translated)
    for values in structural.values():
        needles.update(values["notice"])
        needles.update(values["footer"])
    return needles


def _answer_disclosure_errors(
    answer_pages: Iterable[Path],
    pages: Path,
    translations_dir: Path,
) -> list[Path]:
    cache: dict[str, tuple[str, str, str]] = {}
    errors: list[Path] = []
    for path in answer_pages:
        locale = _locale_for(path, pages)
        if locale not in cache:
            translations = _translations(locale, translations_dir)
            notice, _ = _localized(NEW_NOTICE, locale, translations)
            aim990, _ = _localized(
                NEW_AIM990_NOTICE,
                locale,
                translations,
            )
            footer, _ = _localized(NEW_FOOTER, locale, translations)
            cache[locale] = (
                html.escape(notice, quote=False),
                html.escape(aim990, quote=False),
                html.escape(footer, quote=False),
            )
        expected_notice, expected_aim990, expected_footer = cache[locale]
        source = path.read_text(encoding="utf-8")
        if (
            ANSWER_ARTICLE_MARKER not in source
            and '<footer class="footer">' not in source
        ):
            continue
        footer_match = FOOTER_TEXT_RE.search(source)
        if (
            footer_match is None
            or footer_match.group("text") != expected_footer
        ):
            errors.append(path)
            continue
        if ANSWER_ARTICLE_MARKER not in source:
            continue
        notice_match = NOTICE_RE.search(source)
        expected = (
            expected_aim990 if _is_aim990_page(source) else expected_notice
        )
        if (
            notice_match is None
            or notice_match.group("text") != expected
        ):
            errors.append(path)
    return errors


def _targets_for_locale(
    locale: str,
    translations: dict[str, str],
    structural: dict[str, dict[str, set[str]]],
) -> list[tuple[str, str]]:
    targets = list(TARGETS)
    for old, new in TARGETS[:2]:
        localized_old = translations.get(old)
        if isinstance(localized_old, str) and localized_old.strip():
            targets.append((localized_old, new))
    if not locale.startswith("en-"):
        for current in (NEW_NOTICE, NEW_FOOTER, NEW_AIM990_NOTICE):
            if current in translations:
                targets.append((current, current))
    for source, translated in translations.items():
        if (
            source.startswith(OLD_APP_GUIDE_PREFIX)
            and source.endswith(OLD_APP_GUIDE_SUFFIX)
        ):
            targets.append((source, NEW_FOOTER))
            if isinstance(translated, str) and translated.strip():
                targets.append((translated, NEW_FOOTER))
    values = structural.get(locale, {})
    for old in values.get("notice", ()):
        target = (
            NEW_AIM990_NOTICE
            if "Aim990" in old and "TOEIC" in old
            else NEW_NOTICE
        )
        targets.append((old, target))
    targets.extend((old, NEW_FOOTER) for old in values.get("footer", ()))
    return list(dict.fromkeys(targets))


def _ensure_answer_disclosure(
    source: str,
    *,
    notice: str,
    aim990_notice: str,
    footer: str,
) -> tuple[str, int, bool]:
    replacements = 0
    used_aim990 = _is_aim990_page(source)
    updated = source
    if ANSWER_ARTICLE_MARKER in updated:
        match = NOTICE_RE.search(updated)
        if match:
            old = match.group("text")
            target = aim990_notice if used_aim990 else notice
            escaped = html.escape(target, quote=False)
            if old != escaped:
                count = updated.count(old)
                updated = updated.replace(old, escaped)
                replacements += count
    footer_updated, count = FOOTER_RE.subn(
        _publisher_footer(footer),
        updated,
        count=1,
    )
    if footer_updated != updated:
        replacements += count
    updated = footer_updated
    return updated, replacements, used_aim990


def _ensure_guide_disclosure(source: str, footer: str) -> tuple[str, int]:
    updated, removed = PRE_MANAGED_GUIDE_DISCLOSURE_RE.subn(
        r"\g<hr>",
        source,
        count=1,
    )
    if PUBLISHER_MARKER in updated:
        return updated, removed
    disclosure = (
        f'<p {PUBLISHER_MARKER}><small>'
        f"{html.escape(footer, quote=False)}</small></p>"
    )
    updated, count = TERMINAL_SMALL_RE.subn(
        f"{disclosure}\n</main>",
        updated,
        count=1,
    )
    if count:
        return updated, removed + count
    anchor = "</main>" if "</main>" in source else "</body>"
    if anchor not in source:
        raise RuntimeError("guide page has no disclosure insertion anchor")
    return updated.replace(anchor, f"{disclosure}{anchor}", 1), removed + 1


def _ensure_hub_disclosure(source: str, footer: str) -> tuple[str, int]:
    if PUBLISHER_MARKER in source:
        return source, 0
    anchor = "</main>" if "</main>" in source else "</body>"
    if anchor not in source:
        raise RuntimeError("hub page has no disclosure insertion anchor")
    disclosure = (
        f'<p class="publisher-disclosure" {PUBLISHER_MARKER}>'
        f"<small>{html.escape(footer, quote=False)}</small></p>"
    )
    return source.replace(anchor, f"{disclosure}{anchor}", 1), 1


def migrate(
    pages: Path = PAGES,
    *,
    translations_dir: Path = I18N_DIR,
) -> dict[str, object]:
    pages = pages.resolve()
    translations_dir = translations_dir.resolve()
    cache: dict[str, dict[str, str]] = {}
    changed_files = 0
    replacements = 0
    fallback_locales: set[str] = set()
    answer_pages = _answer_pages(pages)
    all_pages = _content_pages(pages)
    structural = _discover_structural_legacy(
        answer_pages,
        pages,
        translations_dir,
    )
    legacy_needles = _legacy_needles(translations_dir, structural)
    candidates = _git_candidate_pages(
        pages,
        all_pages,
        needles=legacy_needles | {NEW_NOTICE, NEW_FOOTER},
    )
    if candidates is None:
        candidates = all_pages
    candidate_set = set(candidates)
    candidate_set.update(answer_pages)
    candidate_set.update(
        path
        for path in all_pages
        if _section_for(path, pages) in {"guides", "hubs"}
        or (
            _section_for(path, pages) == "answers"
            and path.name == "index.html"
        )
    )

    for path in sorted(candidate_set):
        source = path.read_text(encoding="utf-8")
        updated = source
        locale = _locale_for(path, pages)
        translations = cache.setdefault(
            locale,
            _translations(locale, translations_dir),
        )
        for old, new in _targets_for_locale(
            locale,
            translations,
            structural,
        ):
            if old not in updated:
                continue
            localized, fallback = _localized(new, locale, translations)
            count = updated.count(old)
            updated = updated.replace(
                old,
                html.escape(localized, quote=False),
            )
            replacements += count
            if fallback:
                fallback_locales.add(locale)
        app_guide_replacement, app_guide_fallback = _localized(
            NEW_FOOTER,
            locale,
            translations,
        )
        app_guide_updated, count = ENGLISH_APP_GUIDE_RE.subn(
            html.escape(app_guide_replacement, quote=False),
            updated,
        )
        if app_guide_updated != updated:
            replacements += count
            updated = app_guide_updated
            if app_guide_fallback:
                fallback_locales.add(locale)

        section = _section_for(path, pages)
        localized_footer, footer_fallback = _localized(
            NEW_FOOTER,
            locale,
            translations,
        )
        if section == "answers":
            localized_notice, notice_fallback = _localized(
                NEW_NOTICE,
                locale,
                translations,
            )
            localized_aim990, aim990_fallback = _localized(
                NEW_AIM990_NOTICE,
                locale,
                translations,
            )
            updated, count, used_aim990 = _ensure_answer_disclosure(
                updated,
                notice=localized_notice,
                aim990_notice=localized_aim990,
                footer=localized_footer,
            )
            replacements += count
            if notice_fallback or footer_fallback:
                fallback_locales.add(locale)
            if used_aim990 and aim990_fallback:
                fallback_locales.add(locale)
        elif section == "guides":
            updated, count = _ensure_guide_disclosure(
                updated,
                localized_footer,
            )
            replacements += count
            if footer_fallback:
                fallback_locales.add(locale)
        elif section == "hubs":
            updated, count = _ensure_hub_disclosure(
                updated,
                localized_footer,
            )
            replacements += count
            if footer_fallback:
                fallback_locales.add(locale)

        if updated != source:
            path.write_text(updated, encoding="utf-8")
            changed_files += 1

    static_legacy_needles = _legacy_needles(translations_dir, {})
    remaining = _git_candidate_pages(
        pages,
        all_pages,
        needles=static_legacy_needles,
    )
    if remaining:
        sample = ", ".join(
            path.relative_to(pages).as_posix() for path in remaining[:5]
        )
        raise RuntimeError(f"Legacy publisher claims remain: {sample}")
    invalid_answers = _answer_disclosure_errors(
        answer_pages,
        pages,
        translations_dir,
    )
    if invalid_answers:
        sample = ", ".join(
            path.relative_to(pages).as_posix()
            for path in invalid_answers[:5]
        )
        raise RuntimeError(f"Answer disclosure is not localized: {sample}")
    invalid_markers = []
    for path in all_pages:
        section = _section_for(path, pages)
        if section not in {"guides", "hubs"}:
            continue
        source = path.read_text(encoding="utf-8")
        if (
            source.count(PUBLISHER_MARKER) != 1
            or (
                section == "guides"
                and PRE_MANAGED_GUIDE_DISCLOSURE_RE.search(source)
            )
        ):
            invalid_markers.append(path)
    if invalid_markers:
        sample = ", ".join(
            path.relative_to(pages).as_posix() for path in invalid_markers[:5]
        )
        raise RuntimeError(f"Publisher disclosure invalid: {sample}")

    return {
        "scanned_files": len(all_pages),
        "changed_files": changed_files,
        "replacements": replacements,
        "fallback_locales": sorted(fallback_locales),
        "legacy_claims": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=Path, default=PAGES)
    parser.add_argument("--translations", type=Path, default=I18N_DIR)
    args = parser.parse_args()
    stats = migrate(args.pages, translations_dir=args.translations)
    print(
        "Publisher disclosures: "
        + ", ".join(f"{key}={value}" for key, value in stats.items())
    )


if __name__ == "__main__":
    main()
