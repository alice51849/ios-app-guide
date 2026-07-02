#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AEO Pro 監測器(頂級版)— web 接地 + 引用來源圖譜。

v1(aeo_sov.py)只問模型「腦內知識」。真實世界裡 ChatGPT/Google/Perplexity 是「邊搜尋邊答」,
答案來自它「引用的網頁」。本版用 gpt-4o-search-preview(web 接地)問購買意圖問句,擷取:
  • 你被點名了沒 + AI 推了哪些競品(真實搜尋條件下)
  • ⭐ AI 實際「引用的網域」(url_citation)→ 這就是你要去卡位/投放/被收錄的精準清單
    (例:某 listicle 評測站、AlternativeTo、Reddit 串、競品商店頁…誰被引用,誰就贏)

輸出每個 app 的:web 被推薦率 + 引用來源圖譜(off-page 攻擊清單)。
不碰 app code。沿用 ~/.openai_key。

    python geo/aeo_pro.py scanto cyca unblurry      # 指定 app(建議小批,web 較慢/貴)
    python geo/aeo_pro.py --max-q 4                  # 每 app 取前 N 條問句(預設 4)
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))
from videogen.registry import APPS, APPSTORE, appstore_url  # noqa: E402
from queries import ALL as QUERIES  # noqa: E402
from aeo_sov import aliases, is_ours, normalize  # noqa: E402  (重用 v1 比對邏輯)

REPORTS = os.path.join(HERE, "reports")
os.makedirs(REPORTS, exist_ok=True)
JSON_OUT = os.path.join(REPORTS, "aeo_pro.json")
OPENAI_KEY = open(os.path.expanduser("~/.openai_key")).read().strip()
SEARCH_MODEL = os.environ.get("AEO_SEARCH_MODEL", "gpt-4o-search-preview")
EXTRACT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

OWN_DOMAINS = {"apps.apple.com", "alice51849.github.io"}


def _post(body, timeout=90, retries=3):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions", data=json.dumps(body).encode(),
                headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode())
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise last


def domain(url):
    try:
        net = urllib.parse.urlparse(url).netloc.lower()
        return net[4:] if net.startswith("www.") else net
    except Exception:  # noqa: BLE001
        return ""


def ask_web(query):
    """web 接地問句 → (回答文字, 引用網址清單)。"""
    body = {"model": SEARCH_MODEL,
            "messages": [{"role": "user",
                          "content": f'A user asks: "{query}". Recommend the best iOS apps, '
                                     f"best first, and say why."}],
            "max_tokens": 600}
    r = _post(body)
    msg = r["choices"][0]["message"]
    text = msg.get("content", "") or ""
    cites = []
    for an in (msg.get("annotations") or []):
        uc = an.get("url_citation") or {}
        if uc.get("url"):
            cites.append(uc["url"])
    return text, cites


def extract_apps(answer_text):
    """從 web 回答抽出有序 app 名稱(便宜模型,JSON)。"""
    body = {"model": EXTRACT_MODEL,
            "messages": [{"role": "system", "content": "Extract iOS app names mentioned as "
                          "recommendations, in the order they appear. JSON only."},
                         {"role": "user", "content": f'Answer:\n{answer_text[:1500]}\n\n'
                          'Return {"apps": ["Name1","Name2"]}. Only real app names.'}],
            "response_format": {"type": "json_object"}, "temperature": 0, "max_tokens": 300}
    try:
        r = _post(body, timeout=40)
        d = json.loads(r["choices"][0]["message"]["content"])
        return [a for a in (d.get("apps") or []) if isinstance(a, str) and a.strip()]
    except Exception:  # noqa: BLE001
        return []


def run_app(key, max_q):
    a = APPS[key]
    al = aliases(key)
    own_id = APPSTORE.get(key, "")
    qs = QUERIES.get(key, [])[:max_q]
    rows, comp = [], Counter()
    cited = Counter()          # AI 引用的網域(off-page 攻擊清單)
    own_cited = 0
    for q in qs:
        text, cites = ask_web(q)
        apps = extract_apps(text)
        rank = 0
        for i, nm in enumerate(apps):
            if is_ours(nm, al):
                rank = i + 1
                break
        for nm in apps:
            if not is_ours(nm, al):
                comp[normalize(nm)] += 1
        for u in cites:
            d = domain(u)
            if not d:
                continue
            if own_id and own_id in u:
                own_cited += 1
            if d not in OWN_DOMAINS:
                cited[d] += 1
        rows.append({"query": q, "mentioned": bool(rank), "rank": rank,
                     "apps": apps[:8], "cited": [domain(u) for u in cites]})
        mark = f"#{rank}" if rank else "—"
        print(f"   [{key}] {mark:>4}  cites:{len(cites):>2}  {q}")
        time.sleep(0.4)
    men = [r for r in rows if r["mentioned"]]
    return {"key": key, "name": a["name"], "appstore": appstore_url(key),
            "queries": len(qs), "mentions": len(men),
            "mention_rate": round(len(men) / len(qs), 3) if qs else 0,
            "own_store_cited": own_cited,
            "top_competitors": comp.most_common(8),
            "cited_domains": cited.most_common(12), "rows": rows}


def write_md(results):
    today = date.today().isoformat()
    md = os.path.join(REPORTS, f"aeo_pro_{today}.md")
    rs = sorted(results, key=lambda r: -r["mention_rate"])
    L = [f"# AEO Pro(web 接地)攻擊清單 — {today}",
         f"> 模型:`{SEARCH_MODEL}`(真實搜尋條件)。cited_domains = AI 實際引用來源 = 你要卡位的地方。\n",
         "## 總覽\n", "| App | web 被推薦率 | 你的商店頁被引用 | AI 最常引用的來源(前3) |", "|---|---|---|---|"]
    for r in rs:
        dd = ", ".join(d for d, _ in r["cited_domains"][:3]) or "—"
        L.append(f"| {r['name']} | {int(r['mention_rate']*100)}% ({r['mentions']}/{r['queries']}) "
                 f"| {r['own_store_cited']}x | {dd} |")
    L.append("\n## 各 app:off-page 卡位清單(AI 引用來源)\n")
    for r in rs:
        L.append(f"### {r['name']} — web 被推薦 {int(r['mention_rate']*100)}%")
        if r["cited_domains"]:
            L.append("**AI 都引用這些網頁(去這裡卡位/被收錄/投稿/評測):**")
            for d, n in r["cited_domains"]:
                L.append(f"- {d} ×{n}")
        if r["top_competitors"]:
            L.append("\n**web 條件下 AI 推的競品:** " +
                     ", ".join(c for c, _ in r["top_competitors"][:6]))
        L.append("")
    open(md, "w", encoding="utf-8").write("\n".join(L))
    return md


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("apps", nargs="*")
    ap.add_argument("--max-q", type=int, default=4, help="每 app 取前 N 條問句(web 較慢/貴)")
    args = ap.parse_args()
    keys = [k for k in (args.apps or APPS.keys()) if k in APPS]
    print(f"== AEO Pro(web 接地)｜{SEARCH_MODEL}｜{len(keys)} app ==\n")
    results = []
    for k in keys:
        print(f"▶ {APPS[k]['name']} ({k})")
        results.append(run_app(k, args.max_q))
    json.dump({"model": SEARCH_MODEL, "date": date.today().isoformat(), "results": results},
              open(JSON_OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    md = write_md(results)
    print("\n== 引用來源攻擊清單(摘要)==")
    for r in sorted(results, key=lambda r: -r["mention_rate"]):
        print(f"  {r['name']:<18} web {int(r['mention_rate']*100):>3}%  "
              f"引用源: {', '.join(d for d,_ in r['cited_domains'][:3]) or '—'}")
    print(f"\nJSON → {JSON_OUT}\nMarkdown → {md}")


if __name__ == "__main__":
    main()
