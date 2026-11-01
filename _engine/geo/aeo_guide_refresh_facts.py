#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 aeo_guide.py 的 real_offer_and_rating() 真實 price 補進『既有』
geo/pages/guides/*.html 的 SoftwareApplication JSON-LD,不必整頁用 OpenAI 重生。

為什麼要有這支獨立小工具(2026-09-23,AI 助理引用率優化的一部分):
aeo_guide.py 的 main() 只有兩條路——
  1) 預設路徑:gen_content() 呼叫 OpenAI 整頁重寫(貴,且今天帳號 billing_not_active 打不通)
  2) --missing:deterministic_content(),但只補「還沒有檔案」的 app,既有頁面整段跳過
兩條路都沒辦法「只加兩個 JSON-LD 欄位、其餘一個字不動」。這支工具做第三條路:
只重寫第一個 <script type="application/ld+json"> 區塊裡的 App 物件本身(補
offers、拿掉自我評分 aggregateRating、把舊版殘留的 "@type":"MobileApplication" 正規化成當前
生成器用的 "SoftwareApplication" —— MobileApplication 是它的合法子型別,改型別
不影響任何既有語意),其餘 HTML(標題/intro/FAQ/CTA 文案)逐 byte 不動。

真實性:offers 只認 ~/.growth-private/app_store_facts_cache.json
(itunes.apple.com/lookup 的真實回應),經 aeo_guide.real_offer_and_rating() 同一套
「缺就不寫、絕不捏造、超過 60 天視為過期」邏輯把關,這支工具本身不解讀任何數字。

用法:
  .venv/bin/python geo/aeo_guide_refresh_facts.py --dry-run   # 只印會改什麼
  .venv/bin/python geo/aeo_guide_refresh_facts.py             # 真的寫檔
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from aeo_guide import GUIDES, real_offer_and_rating  # noqa: E402
from videogen.registry import APPS  # noqa: E402  (social/ 已由上一行 import 加進 sys.path)

LD_BLOCK_RE = re.compile(r'(<script type="application/ld\+json">)(.*?)(</script>)', re.DOTALL)


def patch_file(path, key, dry_run):
    src = open(path, encoding="utf-8").read()
    target_span = target_obj = None
    for m in LD_BLOCK_RE.finditer(src):
        inner = m.group(2)
        try:
            obj = json.loads(inner.strip())
        except json.JSONDecodeError:
            continue
        if obj.get("@type") in ("SoftwareApplication", "MobileApplication"):
            target_span, target_obj = m, obj
            break
    if target_span is None:
        return "no-app-schema-block"
    obj = target_obj
    offers, _ = real_offer_and_rating(key)
    changed = False
    if obj.get("@type") == "MobileApplication":
        obj["@type"] = "SoftwareApplication"
        changed = True
    if offers and obj.get("offers") != offers:
        obj["offers"] = offers
        changed = True
    # 評分不寫、舊頁殘留的一併拿掉:發行者替自家 App 標 aggregateRating 屬於
    # Google 評論摘要規範禁止的自我評論標記(同 gen_app_store_facts.py)。
    if obj.pop("aggregateRating", None) is not None:
        changed = True
    # 2026-09-23 觀察到的既有 bug(不是本工具造成、也順手清掉):某次自動合併把
    # potentialAction 炸成幾十筆一模一樣的 InstallAction。既然這個物件已經要重寫,
    # 順手把它收斂回單一筆,不新開一支工具去追查合併腳本的根因。
    pa = obj.get("potentialAction")
    if isinstance(pa, list) and len(pa) > 1:
        seen, deduped = set(), []
        for item in pa:
            sig = json.dumps(item, sort_keys=True)
            if sig not in seen:
                seen.add(sig)
                deduped.append(item)
        if len(deduped) != len(pa):
            obj["potentialAction"] = deduped[0] if len(deduped) == 1 else deduped
            changed = True
    if not changed:
        return "no-change-needed"
    # 保留原本的格式風格(有些頁 minify、有些 pretty-print indent=2),讓 diff 最小。
    was_minified = "\n" not in target_span.group(2).strip()
    new_block = (json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
                 if was_minified else json.dumps(obj, ensure_ascii=False, indent=2))
    new_src = (src[:target_span.start()] + target_span.group(1) + new_block
               + target_span.group(3) + src[target_span.end():])
    # 安全氣囊:確認整份檔案所有 ld+json 區塊在寫回前都還能重新解析成合法 JSON,
    # 避免處理極端內容時切壞了鄰近區塊。
    for ld_match in LD_BLOCK_RE.finditer(new_src):
        json.loads(ld_match.group(2).strip())
    if not dry_run:
        open(path, "w", encoding="utf-8").write(new_src)
    return "patched"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    counts = {}
    errors = []
    for fn in sorted(os.listdir(GUIDES)):
        if not fn.endswith(".html"):
            continue
        key = fn[:-5]
        if key not in APPS:
            continue
        try:
            status = patch_file(os.path.join(GUIDES, fn), key, args.dry_run)
        except Exception as exc:  # noqa: BLE001
            status = "error"
            errors.append(f"{key}: {type(exc).__name__}: {exc}")
        counts[status] = counts.get(status, 0) + 1
        if status in ("patched", "error"):
            print(f"  {'✓' if status == 'patched' else '!'} {key}: {status}")
    tag = "(dry-run) " if args.dry_run else ""
    print(f"\n{tag}總計:" + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    if errors:
        print("錯誤明細:\n" + "\n".join(errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
