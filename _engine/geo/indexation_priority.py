#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路線 99 指南站 Google 收錄修復：優先集合、對照組與網站地圖索引規則（單一正本）。

審後定案：reports/yi_review/log.md 2026-11-20 17:xx「件 B」與
reports/strategy_debate/ten_panel_2026-11-20_route98w_route99.md 第 12～40 行。

* 優先集合（約 356 頁）＝ reports/yi30/breakthrough_strategy_2026-11-20_pm.md 第 43 行的定義：
  「約 61 款 × en-US、ja、zh-Hant、de-DE、fr-FR ≈305 頁＋51 語系首頁」。
  實際展開＝60 款 App 頁 × 5 語系（300 頁）＋站首＋50 個商店語系首頁（51 頁）＝351 頁；
  原算式的 61 把每語系的 index.html 也算成一款，與 51 個語系首頁重複 5 頁，所以去重後是 351。
* 對照組：固定規則用網址雜湊，從「同款、同版型（語系目錄下的 App 頁 <語系>/<款>.html）」
  抽同量級一組（每款 5 頁，共 300 頁），名單存 data/route99_control_group.json。
  對照組不進優先網站地圖、不加站內連結（gen_link_hubs 只連優先頁）。
  語系首頁 51 頁全部在優先集合裡，沒有同版型可抽，不列對照、不進兩組收錄率比較。
* 網站地圖索引：oembed／api 子地圖移出索引（檔案保留）；優先網站地圖排第一條。
* 不加頁、不刪頁、不 noindex；英、澳、加三國版留在原網站地圖，只是不抽進對照組。

    python3 geo/indexation_priority.py --write-control   # 重產對照組名單
    python3 geo/indexation_priority.py --check-control   # 驗證名單可重現（CI 用）
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from official_locales import OFFICIAL_LOCALES  # noqa: E402

# ------------------------------------------------------------------ 常數
PRIORITY_SITEMAP = "sitemap_priority.xml"
# 資料格式子地圖：不是網頁，灌大網址存量、稀釋爬取（拆解 11-20 第二節）。檔案照留。
INDEX_EXCLUDED_SITEMAPS = frozenset({"sitemap_oembed.xml", "sitemap_api.xml"})
PRIORITY_APP_LOCALES = ("en-US", "ja", "zh-Hant", "de-DE", "fr-FR")
# 英、澳、加三國版：暫不移出網站地圖（十人會審第 3 點），但與 en-US 近乎同一頁，
# 抽進對照組會被「重複／Google 另選標準網址」拉低收錄率，故不抽。
CONTROL_EXCLUDED_LOCALES = frozenset({"en-GB", "en-AU", "en-CA"})
CONTROL_PER_APP = len(PRIORITY_APP_LOCALES)
CONTROL_SEED = "route99-indexation-1121"
CONTROL_SCHEMA = "route99_control_group/v1"
# 優先總表頁：首頁只連這一頁，不直接掛 351 條（十人會審件 B）。
PRIORITY_HUB_RELATIVE = "priority.html"
# 各款入口頁＝各款在優先語系的 App 專題頁 <語系>/hubs/<款>.html；只連自己那款的優先頁。
APP_ENTRY_TEMPLATE = "{locale}/hubs/{app}.html"

APP_MANIFEST_PATH = HERE / "live_app_manifest.json"
CONTROL_PATH = HERE / "data" / "route99_control_group.json"
# 網站不會對外提供的路徑（GitHub Pages 不送點開頭目錄；.well-known 例外）。
SERVED_DOT_DIRS = frozenset({".well-known"})


# ------------------------------------------------------------------ 路徑規則
def is_unpublished_relative(relative: str) -> bool:
    """`.github/growth/drafts/...` 之類點開頭目錄的頁線上 404，不可進網站地圖。"""
    parts = [part for part in relative.split("/") if part]
    return any(
        part.startswith(".") and part not in SERVED_DOT_DIRS
        for part in parts
    )


def sitemap_index_order(relatives: list[str] | tuple[str, ...]) -> list[str]:
    """移出排除的子地圖、去重，優先網站地圖排第一，其餘維持原順序。"""
    seen: set[str] = set()
    ordered: list[str] = []
    for rel in relatives:
        if rel in seen or rel in INDEX_EXCLUDED_SITEMAPS:
            continue
        seen.add(rel)
        ordered.append(rel)
    if PRIORITY_SITEMAP in seen:
        ordered.remove(PRIORITY_SITEMAP)
        ordered.insert(0, PRIORITY_SITEMAP)
    return ordered


# ------------------------------------------------------------------ 優先集合
def load_app_keys(manifest_path: Path = APP_MANIFEST_PATH) -> tuple[str, ...]:
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    apps = document.get("apps")
    if not isinstance(apps, dict) or not apps:
        raise ValueError("live_app_manifest.json 沒有 apps")
    return tuple(sorted(apps))


def app_page(locale: str, app: str) -> str:
    return f"{locale}/{app}.html"


def locale_homepages() -> tuple[str, ...]:
    return ("index.html", *(f"{locale}/index.html" for locale in OFFICIAL_LOCALES))


def priority_app_pages(apps: tuple[str, ...]) -> dict[str, tuple[str, ...]]:
    """款 → 該款在 5 個優先語系的 App 頁（固定語系順序）。"""
    return {
        app: tuple(app_page(locale, app) for locale in PRIORITY_APP_LOCALES)
        for app in apps
    }


def priority_rule_relatives(apps: tuple[str, ...] | None = None) -> tuple[str, ...]:
    """規則展開的優先集合（不看站上有沒有這頁）：351 頁。"""
    apps = apps if apps is not None else load_app_keys()
    out: list[str] = list(locale_homepages())
    for pages in priority_app_pages(apps).values():
        out.extend(pages)
    return tuple(dict.fromkeys(out))


def priority_relatives(
    indexable: set[str] | frozenset[str],
    apps: tuple[str, ...] | None = None,
    control: frozenset[str] | None = None,
) -> list[str]:
    """站上實際可索引、且不在對照組的優先頁（保持規則順序）。"""
    control = control if control is not None else load_control_relatives()
    return [
        rel
        for rel in priority_rule_relatives(apps)
        if rel in indexable and rel not in control
    ]


def app_entry_page(locale: str, app: str) -> str:
    return APP_ENTRY_TEMPLATE.format(locale=locale, app=app)


# ------------------------------------------------------------------ 對照組
def url_hash(relative: str, seed: str = CONTROL_SEED) -> str:
    return hashlib.sha256(f"{seed}:{relative}".encode("utf-8")).hexdigest()


def control_candidates(app: str) -> list[str]:
    """同款、同版型（<語系>/<款>.html）、非優先語系、非英澳加。"""
    return [
        app_page(locale, app)
        for locale in OFFICIAL_LOCALES
        if locale not in PRIORITY_APP_LOCALES
        and locale not in CONTROL_EXCLUDED_LOCALES
    ]


def build_control_group(
    apps: tuple[str, ...] | None = None,
    *,
    roster_digest: str | None = None,
) -> dict:
    apps = apps if apps is not None else load_app_keys()
    if roster_digest is None:
        manifest = json.loads(APP_MANIFEST_PATH.read_text(encoding="utf-8"))
        roster_digest = str(manifest.get("roster_digest", ""))
    by_app: dict[str, list[str]] = {}
    for app in apps:
        ranked = sorted(control_candidates(app), key=lambda rel: (url_hash(rel), rel))
        by_app[app] = sorted(ranked[:CONTROL_PER_APP])
    priority = set(priority_rule_relatives(apps))
    flat = sorted(rel for pages in by_app.values() for rel in pages)
    overlap = priority.intersection(flat)
    if overlap:
        raise ValueError(f"對照組與優先集合重疊：{sorted(overlap)[:5]}")
    return {
        "schema": CONTROL_SCHEMA,
        "rule": (
            "每款從同款同版型 <語系>/<款>.html、排除優先 5 語系與 en-GB/en-AU/en-CA 的"
            " 42 個商店語系中，依 sha256(seed:相對路徑) 由小到大取前 5 頁"
        ),
        "seed": CONTROL_SEED,
        "priority_app_locales": list(PRIORITY_APP_LOCALES),
        "excluded_locales": sorted(CONTROL_EXCLUDED_LOCALES),
        "per_app": CONTROL_PER_APP,
        "source_roster_digest": roster_digest,
        "priority_rule_count": len(priority),
        "priority_app_page_count": len(apps) * len(PRIORITY_APP_LOCALES),
        "control_count": len(flat),
        "not_compared": (
            "51 個語系首頁全在優先集合、沒有同版型可抽，不進兩組收錄率比較；"
            "K9 前 50 頁與優先集合重疊者也自收錄率比較剔除另列"
        ),
        "treatment": "對照組不進優先網站地圖、不加站內連結、不要求建立索引、不做 K9",
        "apps": by_app,
    }


def reproduce_control_text(document: dict) -> str:
    """用名單自己記的款與名冊摘要重產：名單定稿後不隨新款漂移（新款不補進對照組）。"""
    apps = tuple(sorted(document.get("apps", {})))
    return render_control(
        build_control_group(apps, roster_digest=document.get("source_roster_digest", ""))
    )


def render_control(document: dict) -> str:
    return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def load_control_relatives(path: Path = CONTROL_PATH) -> frozenset[str]:
    if not path.is_file():
        return frozenset()
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != CONTROL_SCHEMA:
        raise ValueError(f"對照組名單格式不符：{path}")
    return frozenset(
        rel for pages in document.get("apps", {}).values() for rel in pages
    )


# ------------------------------------------------------------------ 優先網站地圖
def render_urlset(urls: list[str]) -> str:
    body = "".join(f"  <url><loc>{url}</loc></url>\n" for url in urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}</urlset>\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write-control", action="store_true")
    group.add_argument("--check-control", action="store_true")
    args = parser.parse_args()
    if args.write_control:
        CONTROL_PATH.write_text(render_control(build_control_group()), encoding="utf-8")
        print(f"對照組已寫入 {CONTROL_PATH}")
        return 0
    if not CONTROL_PATH.is_file():
        print("找不到對照組名單", file=sys.stderr)
        return 1
    actual = CONTROL_PATH.read_text(encoding="utf-8")
    if actual != reproduce_control_text(json.loads(actual)):
        print("對照組名單與規則重產結果不同", file=sys.stderr)
        return 1
    print("對照組名單可重現")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
