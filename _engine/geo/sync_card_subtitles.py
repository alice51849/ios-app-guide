#!/usr/bin/env python3
"""互推／情境卡片（`<strong>App</strong><p class="sub">…</p>`）名稱下那一行改用商店副標。

persona／cross／seasonal／scenario 這幾批舊頁的產生器是一次性的，頁面後來又被
連結、揭露、noindex 等多道程序改寫過，不能整頁重產；這支只重寫卡片裡 App 名稱
正下方那一行，換成該頁語言的線上商店副標（data/<key>_full.json，與 App 頁的
<p><strong> 同一份），其餘內容一個字都不動。重跑結果相同（冪等）。

    python3 geo/sync_card_subtitles.py --pages <Guide repo>          # 改寫
    python3 geo/sync_card_subtitles.py --pages <Guide repo> --check  # 只檢查，有落差 exit 1
"""
from __future__ import annotations

import argparse
import html
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "social"))
sys.path.insert(0, str(HERE))

from official_locales import OFFICIAL_LOCALES, OFFICIAL_LOCALE_SET  # noqa: E402
from videogen.registry import APPS  # noqa: E402

# 同一語言有多個商店語系時，頁面只寫語言碼（例如 lang="de"）用哪一個。
_BASE_DEFAULT = {
    "en": "en-US", "es": "es-ES", "fr": "fr-FR", "pt": "pt-BR", "zh": "zh-Hans",
}
_HANT = {"zh-tw", "zh-hk", "zh-mo", "zh-hant"}
_LOWER = {locale.lower(): locale for locale in OFFICIAL_LOCALES}

CARD_RE = re.compile(
    r'(?P<head><strong>(?P<name>[^<]{1,80})</strong>\s*<p class="sub">)'
    r"(?P<sub>[^<]*)(?P<tail></p>)"
)
HTML_LANG_RE = re.compile(r'<html\b[^>]*\blang="(?P<lang>[^"]+)"', re.IGNORECASE)


def store_locale_for(lang: str) -> str:
    """頁面語言碼 → 商店語系；對不上就用 en-US（商店主語系）。"""
    code = (lang or "").strip().replace("_", "-")
    if code in OFFICIAL_LOCALE_SET:
        return code
    low = code.lower()
    if low in _LOWER:
        return _LOWER[low]
    if low in _HANT or low.startswith("zh-hant"):
        return "zh-Hant"
    base = low.split("-")[0]
    if base == "zh":
        return "zh-Hans"
    candidates = [loc for loc in OFFICIAL_LOCALES if loc.lower().split("-")[0] == base]
    if len(candidates) == 1:
        return candidates[0]
    if base in _BASE_DEFAULT and _BASE_DEFAULT[base] in candidates:
        return _BASE_DEFAULT[base]
    return "en-US"


def card_subtitle(key: str, lang: str = "en-US") -> str:
    """卡片名稱下那一行：該語言的商店副標 → en-US 商店副標 → registry sub。"""
    import build_pages_i18n

    for locale in dict.fromkeys((store_locale_for(lang), "en-US")):
        listed = build_pages_i18n.store_subtitle(key, locale)
        if listed:
            return listed
    return " ".join(str(APPS.get(key, {}).get("sub") or "").split())[:100]


def _name_index() -> dict[str, str]:
    """卡片上的 App 名稱（registry 名稱與各語系商店名稱）→ key；同名多款不收。"""
    import build_pages_i18n

    owners: dict[str, set[str]] = {}
    for key, app in APPS.items():
        names = {app.get("name", "")}
        for values in build_pages_i18n.load_app_locales(key).values():
            if isinstance(values, dict):
                names.add(values.get("name", ""))
        # 舊頁常只寫品牌名（例如 HoursTag），也收冒號前的品牌部分。
        names |= {str(name or "").replace("：", ":").split(":")[0] for name in names}
        for name in names:
            name = " ".join(str(name or "").split())
            if name:
                owners.setdefault(name, set()).add(key)
    return {name: next(iter(keys)) for name, keys in owners.items() if len(keys) == 1}


def rewrite(source: str, names: dict[str, str]) -> tuple[str, int]:
    match = HTML_LANG_RE.search(source)
    lang = match.group("lang") if match else "en-US"
    changed = 0

    def replace(card: re.Match) -> str:
        nonlocal changed
        key = names.get(" ".join(html.unescape(card.group("name")).split()))
        if key is None:
            return card.group(0)
        wanted = html.escape(card_subtitle(key, lang), quote=False)
        if card.group("sub") == wanted:
            return card.group(0)
        changed += 1
        return f'{card.group("head")}{wanted}{card.group("tail")}'

    return CARD_RE.sub(replace, source), changed


def _pages(root: Path):
    for directory, subdirs, files in os.walk(root):
        subdirs[:] = sorted(d for d in subdirs if not d.startswith((".", "_")))
        for name in sorted(files):
            if name.endswith(".html"):
                yield Path(directory) / name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pages", default=str(HERE / "pages"))
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.pages)
    names = _name_index()
    files = cards = 0
    for path in _pages(root):
        source = path.read_text(encoding="utf-8")
        if '<p class="sub">' not in source:
            continue
        updated, changed = rewrite(source, names)
        if not changed:
            continue
        files += 1
        cards += changed
        if not args.check:
            path.write_text(updated, encoding="utf-8")
    verb = "drift" if args.check else "rewrote"
    print(f"card subtitles: {verb} {cards} cards in {files} pages")
    return 1 if args.check and cards else 0


if __name__ == "__main__":
    raise SystemExit(main())
