#!/usr/bin/env python3
"""組合包頁推指南站前的逐頁實跑（反方 11-20 條件①）：每頁走 gen_store_attribution.rewrite 與
audit_store_attribution.audit_source，組合包連結的 ct 不得被改、全部要過。
用法：python3 geo/check_bundle_pages.py <稿根目錄>   （例如 ops/handoff/support_push/ios-app-guide）
稿根目錄下的相對路徑當指南站路徑（<語系>/bundles/<頁>.html）。全過結束碼 0，否則 1。"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_store_attribution as A  # noqa: E402
import gen_store_attribution as G  # noqa: E402

PROVIDER = "118326163"
BUNDLE_CT_RE = re.compile(r"app-bundle/[^\"'\s<>]*?ct=(bundle_[a-z0-9_]+)")


def check(root: Path) -> int:
    pages = sorted(p for p in root.rglob("*.html") if "bundles" in p.relative_to(root).parts)
    if not pages:
        print(f"找不到 bundles/ 頁：{root}")
        return 1
    bad = 0
    for path in pages:
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        try:
            locale = rel.split("/", 1)[0]
            out, _ = G.rewrite(text, G.campaign_token(rel, text), PROVIDER, locale=locale)
            A.audit_source(out, rel, provider=PROVIDER)
            if BUNDLE_CT_RE.findall(text) != BUNDLE_CT_RE.findall(out):
                raise ValueError("組合包連結的 ct 被改寫")
            if not BUNDLE_CT_RE.findall(text):
                raise ValueError("頁上沒有完整的組合包連結（app-bundle＋bundle_ ct）")
            print(f"過  {rel}")
        except Exception as error:  # noqa: BLE001 - 逐頁回報原因
            bad += 1
            print(f"紅  {rel}：{error}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(check(Path(sys.argv[1] if len(sys.argv) > 1 else ".")))
