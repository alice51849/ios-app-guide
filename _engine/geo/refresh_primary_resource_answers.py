#!/usr/bin/env python3
"""Refresh every live answer that leads with a free first-party resource."""

from __future__ import annotations

import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

import aeo_answers  # noqa: E402
import aeo_answers_i18n  # noqa: E402
import answer_deep  # noqa: E402
from appstore_live import live_app_keys  # noqa: E402
from videogen.registry import APPSTORE  # noqa: E402


PAGES = HERE / "pages"
TRANSLATIONS = HERE / "i18n_trans" / "zh-Hant.json"


def primary_resource_plan() -> list[tuple[str, str, str]]:
    """Return unique `(app_key, question, slug)` entries with owned free resources."""
    plan: list[tuple[str, str, str]] = []
    owners: dict[str, str] = {}
    owned_prefix = f"{aeo_answers.SITE}/"
    for item in answer_deep.DEEP_ITEMS:
        resource_url = item.get("primary_resource_url")
        if not isinstance(resource_url, str) or not resource_url.startswith(
            owned_prefix
        ):
            continue
        app_key = item.get("app_key")
        question = item.get("query")
        if app_key not in APPSTORE or not isinstance(question, str):
            raise ValueError(f"Invalid primary-resource item: {item!r}")
        if not aeo_answers.is_english_answer_question(question):
            raise ValueError(f"Invalid primary-resource question: {question!r}")
        slug = aeo_answers.slugify(question)
        previous = owners.get(slug)
        if previous is not None:
            raise ValueError(
                f"Duplicate primary-resource answer slug {slug}: "
                f"{previous}, {app_key}"
            )
        owners[slug] = app_key
        plan.append((app_key, question, slug))
    return sorted(plan, key=lambda entry: entry[2])


def write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def localize_zh_hant(slugs: list[str]) -> int:
    translations = json.loads(TRANSLATIONS.read_text(encoding="utf-8"))
    changed = 0
    for slug in slugs:
        source_path = aeo_answers.ANSWERS_DIR / f"{slug}.html"
        source = source_path.read_text(encoding="utf-8")
        strings, _, _ = aeo_answers_i18n.extract_strings(source)
        missing = [value for value in strings if value not in translations]
        if missing:
            sample = ", ".join(repr(value) for value in missing[:5])
            raise RuntimeError(
                f"Traditional Chinese translations missing for {slug}: {sample}"
            )
        mapping = {value: translations[value] for value in strings}
        localized = aeo_answers_i18n.render_localized(
            source,
            "zh-Hant",
            slug,
            mapping,
        )
        target = (
            aeo_answers_i18n.ROOT
            / "zh-Hant"
            / "answers"
            / f"{slug}.html"
        )
        changed += int(write_if_changed(target, localized))
        aeo_answers_i18n.reconcile_english_alternates(slug)
    return changed


def refresh() -> dict[str, int]:
    live = set(live_app_keys(APPSTORE, str(PAGES), refresh=False))
    refreshed: list[str] = []
    skipped = 0
    for app_key, question, slug in primary_resource_plan():
        if app_key not in live:
            skipped += 1
            continue
        created_slug = aeo_answers.create_page(
            app_key,
            question,
            force=True,
        )
        if created_slug != slug:
            raise RuntimeError(f"Unable to refresh primary-resource answer: {slug}")
        refreshed.append(slug)
    localized = localize_zh_hant(refreshed)
    aeo_answers.regenerate_index()
    aeo_answers.write_sitemap()
    return {
        "refreshed": len(refreshed),
        "localized_changed": localized,
        "inactive_skipped": skipped,
    }


def main() -> None:
    print(json.dumps(refresh(), sort_keys=True))


if __name__ == "__main__":
    main()
