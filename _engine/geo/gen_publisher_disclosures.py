#!/usr/bin/env python3
"""Replace legacy independent-guide claims with truthful publisher disclosure."""

from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import subprocess

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
DISCLOSURE_NEEDLES = (
    OLD_NOTICE,
    NEW_NOTICE,
    OLD_FOOTER,
    NEW_FOOTER,
)
ANSWER_PATHSPECS = (
    "answers/*.html",
    "answers/**/*.html",
    "*/answers/*.html",
    "*/answers/**/*.html",
)


def _locale_for(path: Path, pages: Path) -> str:
    first = path.relative_to(pages).parts[0]
    return first if first in OFFICIAL_LOCALES else "en-US"


def _translations(locale: str, translations_dir: Path) -> dict[str, str]:
    if locale.startswith("en-"):
        return {}
    path = translations_dir / f"{locale}.json"
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Translation dictionary must be an object: {path}")
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


def _answer_pages(pages: Path) -> list[Path]:
    roots = [pages / "answers"]
    roots.extend(pages / locale / "answers" for locale in OFFICIAL_LOCALES)
    return sorted(
        path
        for root in roots
        if root.is_dir()
        for path in root.rglob("*.html")
    )


def _git_candidate_pages(
    pages: Path,
    all_pages: list[Path],
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

    grep_command = [
        "git",
        "-C",
        str(pages),
        "grep",
        "-l",
        "-z",
        "-F",
    ]
    for needle in DISCLOSURE_NEEDLES:
        grep_command.extend(("-e", needle))
    grep_command.extend(("--", *ANSWER_PATHSPECS))
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
                *ANSWER_PATHSPECS,
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
        if any(needle in source for needle in DISCLOSURE_NEEDLES):
            relative_paths.add(relative)

    known_pages = {path.relative_to(pages).as_posix(): path for path in all_pages}
    if not relative_paths.issubset(known_pages):
        return None
    return [known_pages[relative] for relative in sorted(relative_paths)]


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
    targets = (
        (OLD_NOTICE, NEW_NOTICE),
        (OLD_FOOTER, NEW_FOOTER),
    )
    all_pages = _answer_pages(pages)
    candidates = _git_candidate_pages(pages, all_pages)
    if candidates is None:
        candidates = all_pages
    for path in candidates:
        source = path.read_text(encoding="utf-8")
        updated = source
        locale = _locale_for(path, pages)
        translations = cache.setdefault(
            locale,
            _translations(locale, translations_dir),
        )
        for old, new in targets:
            if old in updated:
                localized, fallback = _localized(new, locale, translations)
                count = updated.count(old)
                updated = updated.replace(
                    old,
                    html.escape(localized, quote=False),
                )
                replacements += count
                if fallback:
                    fallback_locales.add(locale)
            if (
                not locale.startswith("en-")
                and new in updated
                and new in translations
            ):
                localized, _ = _localized(new, locale, translations)
                count = updated.count(new)
                updated = updated.replace(
                    new,
                    html.escape(localized, quote=False),
                )
                replacements += count
        if OLD_NOTICE in updated or OLD_FOOTER in updated:
            raise RuntimeError(f"Legacy disclosure remains in {path}")
        if updated != source:
            path.write_text(updated, encoding="utf-8")
            changed_files += 1
    return {
        "scanned_files": len(all_pages),
        "changed_files": changed_files,
        "replacements": replacements,
        "fallback_locales": sorted(fallback_locales),
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
