#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""off-page 卡位包生成器(做到極致)— 把 AI 引用來源變成每-app「可提交」清單。

AEO 真正的關鍵是「進到 AI 引用的來源」。本工具讀 aeo_pro.json(web 接地引用圖譜)
+ registry,為每個 app 產一份可直接複製提交的卡位包:
  • AI 實際引用的網域(優先卡位順序)
  • AlternativeTo / Product Hunt 可貼文案
  • 通用高權重 app 目錄清單(LLM 常引用)
  • 誠實的社群/論壇角度(揭露開發者身分,非 spam)
你親自提交=合規。不自動發文、不碰 app code。

    python geo/aeo_offpage.py            # 全部 app
    python geo/aeo_offpage.py scanto     # 指定
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))
from videogen.registry import APPS, appstore_url  # noqa: E402
try:
    from aeo_pages import disp
except Exception:  # noqa: BLE001
    def disp(x):
        return " ".join(w.capitalize() for w in (x or "").split())

OUT = os.path.join(ROOT, "reports", "aeo_offpage")
PRO = os.path.join(HERE, "reports", "aeo_pro.json")
SOV = os.path.join(HERE, "reports", "aeo_sov.json")

# LLM 高頻引用的通用目錄/評測站(都送一遍)
DIRECTORIES = [
    "AlternativeTo — https://alternativeto.net/manage-app/ (提交/認領你的 app)",
    "Product Hunt — https://www.producthunt.com/posts/new (發佈)",
    "SaaSHub — https://www.saashub.com/submit-software",
    "Slant — https://www.slant.co (在相關問題加入你的 app 作為選項)",
    "There's An App For That — https://theresanaiforthat.com / taft.io",
    "apprecs — https://apprecs.com (自動索引;確保分類/關鍵字正確、衝評價)",
    "Uptodown — https://en.uptodown.com (iOS app 目錄)",
    "AppAdvice — https://appadvice.com (投稿 app tip)",
]
CAT_HINT = {"photo-utility": "Photo & Video / Graphics", "productivity": "Productivity / Office",
            "finance": "Finance / Budgeting", "health": "Health & Fitness",
            "education": "Education / Kids", "kids": "Education / Kids"}


def load(path):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}


def cited_for(key, pro):
    for r in pro.get("results", []):
        if r["key"] == key:
            return r.get("cited_domains", []), r.get("top_competitors", [])
    return [], []


def comps_for(key, sov):
    for r in sov.get("results", []):
        if r["key"] == key:
            return [disp(c) for c, _ in r.get("top_competitors", [])[:4]]
    return []


def build(key, pro, sov):
    a = APPS[key]
    url = appstore_url(key)
    sub = (a.get("sub") or "").replace("\n", " ").strip()
    cited, web_comps = cited_for(key, pro)
    comps = [disp(c) for c, _ in web_comps[:4]] or comps_for(key, sov)
    alt_to = ", ".join(comps) or "(see App Store category)"
    bullets = " · ".join(a.get("cta_bullets", []))
    cat = CAT_HINT.get(a.get("category", ""), "Utilities")
    one_liner = f"{a['name']} — {sub} {('(' + bullets + ')') if bullets else ''}".strip()

    L = [f"# {a['name']} — AI 推薦卡位包", f"App Store: {url}", ""]
    L.append("## AI 實際引用的來源(優先去這裡被收錄/評測/提及)")
    if cited:
        for d, n in cited:
            L.append(f"- {d}  ×{n}")
    else:
        L.append("- (尚無 web 掃描資料,先送下方通用目錄)")
    L += ["", "## 立即可提交(複製即用)", "", "### AlternativeTo",
          f"- Name: {a['name']}", f"- Category: {cat}",
          f"- Short description: {sub}. {bullets}.",
          f"- Mark as alternative to: {alt_to}", "",
          "### Product Hunt",
          f"- Tagline (<=60): {sub[:60]}",
          f"- Description: {one_liner}. Pay once, no subscription. Link: {url}", "",
          "### 通用高權重目錄(LLM 常引用,逐一提交)"]
    for d in DIRECTORIES:
        L.append(f"- {d}")
    L += ["", "## 最有效的 3 件事(只有你能做)",
          "1. 衝 5–10 則真實 App Store 評價(朋友/社團/既有用戶)。",
          "2. 把上面 AlternativeTo / Product Hunt / 目錄逐一提交(文案已備)。",
          f"3. 在相關社群以開發者身分誠實揭露分享(Reddit/Dcard/FB 社團),附 {url} 並徵求回饋。",
          "", "> 原則:全部合規揭露,不買假評、不洗版。AI 引用誰你就出現在誰那裡。"]
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("apps", nargs="*")
    args = ap.parse_args()
    pro, sov = load(PRO), load(SOV)
    keys = [k for k in (args.apps or APPS.keys()) if k in APPS]
    os.makedirs(OUT, exist_ok=True)
    idx = ["# AI 推薦卡位包 — 20 app 索引", ""]
    for k in keys:
        open(os.path.join(OUT, f"{k}.md"), "w", encoding="utf-8").write(build(k, pro, sov))
        idx.append(f"- {APPS[k]['name']}: reports/aeo_offpage/{k}.md")
        print(f"  ✓ {APPS[k]['name']}")
    open(os.path.join(OUT, "INDEX.md"), "w", encoding="utf-8").write("\n".join(idx))
    print(f"\n共 {len(keys)} 份卡位包 → {OUT}")


if __name__ == "__main__":
    main()
