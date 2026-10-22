#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把已由免費版誠實接管的 answer 頁,從付費門**重生**成免費門。

`queries.ALL` 已依 free_first_ownership 把免費版能誠實回答的品類問句掛到免費
key;但 `aeo_answers.create_page` 對已存在的頁面不會重寫,所以歷史上由付費 key
產生、只帶付費 App Store id 的 `answers/<slug>.html` 會一直停在付費門(頁→下載
0–2.7%)。這支腳本在產生器層補完最後一步:對每一條現在歸免費版的問句,若既有
英文頁只帶付費 id,就用免費 key 重新 render(事實從產生時就是免費版的,不是換
門後再改字)。

安全邊界:
  • 只處理免費版**目前公開**(live)的配對;免費版不公開就保留付費門並記錄。
  • 再驗一次 free_first_ownership.free_answers_honestly,免費版答不出來就不動。
  • `--check` 只列出、不寫檔,且有待處理頁時 exit 1 —— 這就是 fail-closed gate。
  • 在地化副本交給既有的 aeo_answers_i18n(雲端每日會以字典重新 render;
    缺譯必須補齊否則 require_complete_mapping 會擋),本腳本不碰。

用法:
  python3 reclaim_free_first_answers.py [--pages-dir DIR] [--check] [--refresh-live]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (str(HERE), str(ROOT / "social")):
    if path not in sys.path:
        sys.path.insert(0, path)

from app_pairs import paid_to_free  # noqa: E402
from appstore_live import live_app_keys  # noqa: E402
from free_first_ownership import free_answers_honestly  # noqa: E402
from publisher_intent_catalog import slugify  # noqa: E402
from videogen.registry import APPSTORE  # noqa: E402

DEFAULT_PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
REPORT = HERE / "reports" / "free_first_reclaim.json"


def is_english_question(question: str) -> bool:
    try:
        question.encode("ascii")
    except UnicodeEncodeError:
        return False
    slug = slugify(question)
    return slug not in {"app", "answer"} and len(slug) >= 8


def find_candidates(pages: Path, all_queries: dict, public: set[str]):
    """回 (可重生清單, 保留清單);兩者都是 dict 列表,只讀不寫。"""
    pairs = paid_to_free()
    reclaim, held = [], []
    answers = pages / "answers"
    for paid, free in sorted(pairs.items()):
        paid_id, free_id = APPSTORE.get(paid), APPSTORE.get(free)
        if not paid_id or not free_id:
            continue
        for question in all_queries.get(free, []):
            if not is_english_question(question):
                continue
            slug = slugify(question)
            path = answers / f"{slug}.html"
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if f"id{paid_id}" not in text or f"id{free_id}" in text:
                continue
            row = {"slug": slug, "paid": paid, "free": free, "question": question}
            if free not in public:
                row["reason"] = "free_app_not_public"
                held.append(row)
            elif not free_answers_honestly(question, free):
                row["reason"] = "free_facts_not_honest"
                held.append(row)
            else:
                reclaim.append(row)
    return reclaim, held


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-dir", type=Path, default=DEFAULT_PAGES)
    parser.add_argument("--check", action="store_true", help="只列出待重生頁,不寫檔;有待處理頁即 exit 1")
    parser.add_argument("--refresh-live", action="store_true", help="重新查 App Store 公開狀態(預設沿用快照)")
    parser.add_argument("--report", type=Path, default=REPORT)
    args = parser.parse_args(argv)

    import queries  # 匯入時已套用 free_first_ownership

    pages = args.pages_dir.resolve()
    public = set(live_app_keys(APPSTORE, str(pages), refresh=args.refresh_live))
    reclaim, held = find_candidates(pages, queries.ALL, public)
    regenerated = []
    if reclaim and not args.check:
        import aeo_answers

        for row in reclaim:
            slug = aeo_answers.create_page(
                row["free"], row["question"], force=True, pages_root=pages
            )
            if slug is None:
                row["reason"] = "render_failed"
                held.append(row)
            else:
                regenerated.append(row)
    report = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "pages_dir": str(pages),
        "check_only": args.check,
        "reclaimable": reclaim if args.check else regenerated,
        "held": held,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(
        f"free-first reclaim: {len(regenerated)} pages regenerated on the free door, "
        f"{len(reclaim) if args.check else 0} pending (check), {len(held)} held"
    )
    for row in held:
        print(f"  held {row['slug']}: {row['reason']}")
    if args.check and reclaim:
        for row in reclaim:
            print(f"  pending {row['slug']}: {row['paid']} -> {row['free']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
