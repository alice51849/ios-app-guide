#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「當期檔期」的 App 放到自有站台的入口頁上。

檔期引擎(`agent/season_engine.py`)即時計算哪些 App 與目前市場情境相關
(開學季 → Lumi 注音/字母/數學;報稅季 → 掃描與文件;新年 → 專注與習慣)。
這支把當期清單注入站台的幾個入口頁,讓首頁曝光跟著檔期走,而不是一年到頭
都長一樣。

只列**已驗證的 live App**(有真實 App Store 連結),文字只寫檔期本身,
不寫任何排名、下載量或產品沒有的功能。

必須註冊在 `geo/publish.py`(產生器之後、sitemap 之前);直接改 pages 下的
HTML 會被下一次發布覆蓋。

用法:
    python3 gen_seasonal_spotlight.py [--dry] [--date YYYY-MM-DD]
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GE = os.path.dirname(HERE)
PAGES = os.path.join(HERE, "pages")
AGENT = os.path.join(GE, "agent")
sys.path.insert(0, AGENT)

MARKER = "seasonal-spotlight"
BLOCK_RE = re.compile(r'<section class="wrap seasonal-spotlight".*?</section>',
                      re.S)
LANG_RE = re.compile(r'<html[^>]*\blang="([^"]+)"', re.I)
TARGETS = ("index.html", os.path.join("tools", "index.html"),
           os.path.join("apps", "index.html"))
HEADING = {
    "en-AU": "In season right now",
    "en-CA": "In season right now",
    "en-GB": "In season right now",
    "en-US": "In season right now",
    "zh-Hans": "正值当季",
    "zh-Hant": "現在正是時候",
    "ja": "いまの季節に合うもの",
    "ko": "지금 계절에 맞는 것",
}
INTRO = {
    "en-AU": "Useful seasonal priorities for this market ({seasons}).",
    "en-CA": "Useful seasonal priorities for this market ({seasons}).",
    "en-GB": "Useful seasonal priorities for this market ({seasons}).",
    "en-US": "Useful seasonal priorities for this market ({seasons}).",
    "zh-Hans": "适合当前市场的季节性内容（{seasons}）。",
    "zh-Hant": "適合目前市場的季節性內容（{seasons}）。",
    "ja": "この市場の季節に合う内容（{seasons}）。",
    "ko": "이 시장의 계절에 맞는 콘텐츠({seasons}).",
}
MAX_ITEMS = 6


def _lang_of(page):
    match = LANG_RE.search(page)
    if not match:
        return "en-US"
    code = match.group(1)
    if code.startswith("zh-Hans") or code == "zh-CN":
        return "zh-Hans"
    if code.startswith("zh-Hant"):
        return "zh-Hant"
    for candidate in ("ja", "ko"):
        if code.startswith(candidate):
            return candidate
    if code in {"en", "en-US"}:
        return "en-US"
    if code in {"en-AU", "en-CA", "en-GB"}:
        return code
    return None


def _block(data, lang):
    if lang not in HEADING or lang not in INTRO:
        return ""
    import season_engine

    view = season_engine.locale_view(data, lang)
    metadata = {
        item["key"]: item for item in data.get("spotlight", [])
    }
    items = [
        metadata[key]
        for key in view["boosted"]
        if key in metadata
    ]
    if not items:
        return ""
    labels = [
        event["label"]
        for event in view["active_seasons"]
        if event.get("label")
    ]
    if not labels:
        return ""
    seasons = "、".join(labels)
    lines = []
    for item in items[:MAX_ITEMS]:
        target = item.get("guide_url") or item.get("store_url")
        if not target:
            continue
        lines.append(
            f'<li><a href="{html.escape(target)}">'
            f'{html.escape(item["name"])}</a></li>'
        )
    if not lines:
        return ""
    return (
        f'<section class="wrap {MARKER}">'
        f'<h2>{html.escape(HEADING[lang])}</h2>'
        f'<p>{html.escape(INTRO[lang].format(seasons=seasons))}'
        f'</p><ul>{"".join(lines)}</ul></section>'
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--date")
    args = parser.parse_args()

    import season_engine
    data = (
        season_engine.build_snapshot(dt.date.fromisoformat(args.date))
        if args.date
        else season_engine.build_snapshot()
    )

    changed = 0
    for relative in TARGETS:
        path = os.path.join(PAGES, relative)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as handle:
            page = handle.read()
        stripped = BLOCK_RE.sub("", page)         # 冪等:先移除舊的
        block = _block(data, _lang_of(page))
        if block and "<main>" in stripped:
            updated = stripped.replace("<main>", "<main>" + block, 1)
        elif block and "</main>" in stripped:
            updated = stripped.replace("</main>", block + "</main>", 1)
        else:
            updated = stripped
        if updated != page:
            changed += 1
            if not args.dry:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(updated)

    names = ", ".join(w["id"] for w in data.get("active_seasons", [])) or "無"
    print(f"{'DRY ' if args.dry else ''}seasonal-spotlight: {changed} 頁更新"
          f"(檔期:{names};清單 {len(data.get('spotlight', []))} 支)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
