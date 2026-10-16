#!/usr/bin/env python3
"""Index-entry canary 的在地化版本實測紀錄：依實際站台推導，只增不減。

index_entry_canary_manifest.json 的 ``measured_2026_09_12`` 是 2026-09-12 的
歷史基準，寫死不動。現行紀錄放在 Guide 站台樹的
``_engine/geo/index_entry_canary_locales.json``（只存在 Guide，不是 geo 正本的
鏡像檔），由本程式依站台實際檔案重算：

* 某個 canary 答案頁多了語系版本 → 自動補進紀錄（geo-daily 每個測試關卡前都會
  跑一次，補語系的人不必手改任何數字）。
* 紀錄裡的語系版本不見了 → fail-closed，除非用 ``--allow-removal slug:locale``
  明確核准；所以 index entry 不會無聲變少。
* 英文頁的 hreflang 必須剛好宣告 en、x-default 與這些版本，而且每個 href 指向
  自己語系的路徑、母語頁 canonical 指回自己；``hreflang_problems`` 列出所有不符。

    python3 index_entry_canary_locales.py                 # 重算並寫回紀錄
    python3 index_entry_canary_locales.py --check         # 紀錄與站台不符就 exit 1
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
from typing import Iterable, Mapping


HERE = Path(__file__).resolve().parent
PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
MANIFEST_PATH = HERE / "index_entry_canary_manifest.json"
# Relative to the site root, so the record always lives in the Guide checkout
# (the GrowthEngine copy reaches it through geo/pages) and never in geo/.
STATE_RELATIVE = Path("_engine") / "geo" / "index_entry_canary_locales.json"
SCHEMA = "lumi.index-entry-canary-locales/v1"
LOCALE_DIR_RE = re.compile(r"[a-z]{2}(?:-[A-Za-z]{2,4})?")
ALTERNATE_RE = re.compile(
    r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)"'
)
CANONICAL_RE = re.compile(r'<link rel="canonical" href="([^"]+)"')


class CanaryLocaleRemoval(ValueError):
    """A recorded canary locale version disappeared without explicit approval."""


def default_site() -> str:
    sys.path.insert(0, str(HERE))
    from site_config import PUBLIC_SITE  # noqa: E402

    return os.environ.get("GEO_SITE", PUBLIC_SITE).rstrip("/")


def canary_slugs(manifest_path: Path = MANIFEST_PATH) -> tuple[str, ...]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    slugs = tuple(manifest["canaries"])
    if not slugs or len(set(slugs)) != len(slugs):
        raise ValueError("Index-entry canary manifest must list unique slugs")
    return slugs


def state_path(pages: Path) -> Path:
    return pages / STATE_RELATIVE


def locale_dirs(pages: Path) -> list[str]:
    return sorted(
        child.name
        for child in pages.iterdir()
        if child.is_dir() and LOCALE_DIR_RE.fullmatch(child.name)
    )


def measure(pages: Path, slugs: Iterable[str]) -> dict[str, object]:
    """The record as the live site shows it: every slug's existing locales."""
    locales = locale_dirs(pages)
    return {
        "schema": SCHEMA,
        "canaries": {
            slug: [
                locale
                for locale in locales
                if (pages / locale / "answers" / f"{slug}.html").is_file()
            ]
            for slug in slugs
        },
    }


def load_state(pages: Path) -> dict[str, object] | None:
    path = state_path(pages)
    if not path.is_file():
        return None
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("schema") != SCHEMA or not isinstance(state.get("canaries"), dict):
        raise ValueError(f"Invalid index-entry canary locale record: {path}")
    return state


def render(state: Mapping[str, object]) -> str:
    return json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def hreflang_problems(
    pages: Path,
    slug: str,
    locales: Iterable[str],
    site: str,
) -> list[str]:
    """Every way the English page's alternates differ from the real versions."""
    english = pages / "answers" / f"{slug}.html"
    if not english.is_file():
        return [f"{slug}: English canary page is missing"]
    english_url = f"{site}/answers/{slug}.html"
    expected = {"en": english_url, "x-default": english_url}
    expected.update(
        {locale: f"{site}/{locale}/answers/{slug}.html" for locale in locales}
    )
    declared: dict[str, str] = {}
    problems: list[str] = []
    for hreflang, href in ALTERNATE_RE.findall(
        english.read_text(encoding="utf-8", errors="ignore")
    ):
        if hreflang in declared and declared[hreflang] != href:
            problems.append(f"{slug}: hreflang {hreflang} declared twice")
        declared[hreflang] = href
    for hreflang in sorted(set(expected) - set(declared)):
        problems.append(f"{slug}: missing hreflang {hreflang}")
    for hreflang in sorted(set(declared) - set(expected)):
        problems.append(
            f"{slug}: hreflang {hreflang} has no localized page"
        )
    for hreflang in sorted(set(declared) & set(expected)):
        if declared[hreflang] != expected[hreflang]:
            problems.append(
                f"{slug}: hreflang {hreflang} points to {declared[hreflang]}"
            )
    for locale in locales:
        page = pages / locale / "answers" / f"{slug}.html"
        match = CANONICAL_RE.search(page.read_text(encoding="utf-8", errors="ignore"))
        if match is None or match.group(1) != expected[locale]:
            problems.append(f"{slug}: {locale} canonical is not its own URL")
    return problems


def _parse_removals(values: Iterable[str]) -> frozenset[tuple[str, str]]:
    removals = set()
    for value in values:
        slug, separator, locale = value.partition(":")
        if not separator or not slug or not locale:
            raise ValueError(f"--allow-removal expects slug:locale, got {value!r}")
        removals.add((slug, locale))
    return frozenset(removals)


def refresh(
    pages: Path = PAGES,
    *,
    slugs: Iterable[str] | None = None,
    allow_removals: Iterable[tuple[str, str]] = (),
    write: bool = True,
) -> dict[str, object]:
    """Recompute the record; additions are automatic, removals fail closed."""
    slugs = tuple(canary_slugs() if slugs is None else slugs)
    measured = measure(pages, slugs)
    previous = load_state(pages)
    allowed = frozenset(allow_removals)
    added: dict[str, list[str]] = {}
    removed: dict[str, list[str]] = {}
    if previous is not None:
        old = previous["canaries"]
        for slug in sorted(set(old) - set(slugs)):
            raise CanaryLocaleRemoval(
                f"Canary {slug} left the manifest but is still recorded"
            )
        for slug in slugs:
            now = measured["canaries"][slug]
            before = old.get(slug, [])
            gone = [locale for locale in before if locale not in now]
            refused = [locale for locale in gone if (slug, locale) not in allowed]
            if refused:
                raise CanaryLocaleRemoval(
                    f"Index-entry canary {slug} lost recorded locale versions "
                    f"{refused}; restore them or pass --allow-removal "
                    + " ".join(f"{slug}:{locale}" for locale in refused)
                )
            if gone:
                removed[slug] = gone
            new = [locale for locale in now if locale not in before]
            if new:
                added[slug] = new
    text = render(measured)
    path = state_path(pages)
    changed = not path.is_file() or path.read_text(encoding="utf-8") != text
    if changed and write:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    return {
        "changed": changed,
        "added": added,
        "removed": removed,
        "variants": {
            slug: len(locales)
            for slug, locales in measured["canaries"].items()
        },
    }


def check(pages: Path = PAGES, slugs: Iterable[str] | None = None) -> bool:
    slugs = tuple(canary_slugs() if slugs is None else slugs)
    return load_state(pages) == measure(pages, slugs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=Path, default=PAGES)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--allow-removal",
        action="append",
        default=[],
        metavar="SLUG:LOCALE",
        help="explicitly approve one recorded locale version going away",
    )
    args = parser.parse_args()
    pages = args.pages.resolve()
    if args.check:
        ok = check(pages)
        print(json.dumps({"index_entry_canary_locales": "match" if ok else "drift"}))
        return 0 if ok else 1
    summary = refresh(pages, allow_removals=_parse_removals(args.allow_removal))
    print("INDEX_ENTRY_CANARY_LOCALES " + json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
