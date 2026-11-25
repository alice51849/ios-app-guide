#!/usr/bin/env python3
"""K9 前 50 頁首屏修錯＋共用批次追蹤碼（部署產物上執行，不改 repo 裡的頁面）。

來源：reports/yi_review/log.md 2026-11-20 17:xx 件 B「K9」（審核員改後通過）、
ops/handoff/rulings/2026-11-21_rescue.md 第 78 項。只修錯、不加頁：
* 清單裡每一頁的 App Store 連結 ct 換成同一個批次碼 ``BATCH_CT``（agent/ct_codes.py 登記），
  Google Play 下載連結 referrer 的 utm_source 換成同一碼（utm_campaign 照舊是款 key）；
  評分連結（action=write-review、showAllReviews）不是下載連結，不動。
* 首屏文字（H1、導言、按鈕字）照 ``geo/data/k9_first_screen_pages.json`` 逐頁替換；
  原字串在頁上找不到（產生器已改寫）就跳過那一條，不猜、不硬塞。
* 逐頁站內點擊計數沿用 click_beacon（它送 {p: 路徑, ct}），本步要排在 click_beacon inject 之前。
* 按位元組釘選的頁（hero、決策頁、結果圖庫，click_beacon._pinned_paths）一律不碰。

任何錯誤都不讓部署失敗：只印統計，回傳 0。
用法：k9_first_screen.py apply --pages <部署根目錄> [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA_PATH = HERE / "data" / "k9_first_screen_pages.json"
BATCH_CT = "k9top50_1121"

_APPLE_HREF_RE = re.compile(r'https://apps\.apple\.com/[^"\'<>\s]*')
_CT_RE = re.compile(r"(?<=[?&;])ct=[A-Za-z0-9_-]+")
# Safari 智慧型 App 橫幅（首屏最上方）：<meta name="apple-itunes-app" content="…affiliate-data=pt=…&amp;ct=…">
_BANNER_RE = re.compile(r'affiliate-data=[^"\'<>]*')
_PLAY_SOURCE_RE = re.compile(
    r'(https://play\.google\.com/store/apps/details\?id=[\w.]+&(?:amp;)?referrer=utm_source%3D)[A-Za-z0-9_-]+')


def load_spec(path: Path = DATA_PATH) -> dict:
    try:
        spec = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return spec if isinstance(spec, dict) and isinstance(spec.get("pages"), dict) else {}


def _swap_apple_ct(match: re.Match, ct: str) -> str:
    url = match.group(0)
    if "action=write-review" in url:
        return url
    return _CT_RE.sub("ct=" + ct, url)


def apply_html(source: str, page: dict, ct: str = BATCH_CT) -> tuple[str, dict]:
    """回傳 (新內容, 統計)。冪等：已換過的頁再跑一次不變。"""
    stats = {"text_applied": 0, "text_missing": 0, "ct_links": 0}
    out = source
    for row in page.get("replace") or []:
        old, new = row.get("old"), row.get("new")
        if not old or new is None:
            continue
        count = out.count(old)
        if count == 0:
            stats["text_missing"] += 0 if new and new in out else 1  # a re-run finds only the new text
            continue
        if old in new and out.count(new) >= count:  # the new text contains the old one: already applied
            continue
        if count > 1 and not row.get("all"):
            stats["text_missing"] += 1
            continue
        out = out.replace(old, new)
        stats["text_applied"] += 1
    before = out
    out = _APPLE_HREF_RE.sub(lambda m: _swap_apple_ct(m, ct), out)
    out = _BANNER_RE.sub(lambda m: _CT_RE.sub("ct=" + ct, m.group(0)), out)
    out = _PLAY_SOURCE_RE.sub(lambda m: m.group(1) + ct, out)
    stats["ct_links"] = int(out != before)
    return out, stats


def _pinned(pages: Path) -> set[str]:
    try:
        sys.path.insert(0, str(HERE))
        import click_beacon  # noqa: E402  same folder (geo/ and the Guide's _engine/geo mirror)
        return click_beacon._pinned_paths(pages)
    except Exception:  # pinned list unknown: touch nothing rather than break a pinned page
        return {"*"}


def apply_tree(pages: Path, spec: dict | None = None, dry_run: bool = False) -> dict:
    spec = load_spec() if spec is None else spec
    ct = spec.get("batch_ct") or BATCH_CT
    stats = {"listed": 0, "changed": 0, "missing_page": 0, "pinned": 0, "text_applied": 0,
             "text_missing": 0, "error": 0}
    pinned = _pinned(Path(pages))
    for relative, page in sorted((spec.get("pages") or {}).items()):
        stats["listed"] += 1
        if "*" in pinned or relative in pinned:
            stats["pinned"] += 1
            continue
        path = Path(pages) / relative
        if not path.is_file() or path.is_symlink():
            stats["missing_page"] += 1
            continue
        try:
            source = path.read_text(encoding="utf-8")
            updated, row = apply_html(source, page if isinstance(page, dict) else {}, ct)
            stats["text_applied"] += row["text_applied"]
            stats["text_missing"] += row["text_missing"]
            if updated != source:
                stats["changed"] += 1
                if not dry_run:
                    path.write_text(updated, encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            stats["error"] += 1
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    apply = sub.add_parser("apply")
    apply.add_argument("--pages", type=Path, required=True)
    apply.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(apply_tree(args.pages, dry_run=args.dry_run), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
