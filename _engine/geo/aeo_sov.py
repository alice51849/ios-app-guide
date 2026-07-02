#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AEO Share-of-Voice 監測器 — 量測「當有人問 AI 要用哪個 app」時,你被推薦了沒。

為什麼這是「能觸發購買」而非「散播資訊」:
  使用者問 ChatGPT / Gemini / Perplexity / Siri / Google AI Overview
  「X 用哪個 iPhone app 好?」時,本身就是「正要買」的最高意圖時刻。
  被 AI 點名 = 零 CAC 的高意圖安裝。這支工具先「量測現況」,再吐出
  「攻擊清單」:AI 現在都推哪些競品(= 你要寫 [競品] alternative 頁的對象)、
  你在哪些問句完全缺席(= 優先補的購買意圖落地頁)。

流程:
  讀 geo/queries.py 的購買意圖問句 → 模擬「真實使用者問 AI」(不餵你的 app 名,
  避免污染)→ 解析回答點名了哪些 app、你排第幾 → 彙總每個 app 的曝光率/平均名次/
  競品 share-of-voice → 寫 JSON + Markdown 攻擊清單。

用法:
  python geo/aeo_sov.py                 # 全部 app(預設 gpt-4o-mini,便宜)
  python geo/aeo_sov.py scanto cvdesk   # 指定 app
  python geo/aeo_sov.py --limit 3       # 只跑前 3 個 app(驗證用)
  python geo/aeo_sov.py --per-query 1   # 每問句只問 1 次(預設 1;>1 可平均更穩)
  OPENAI_MODEL=gpt-4o python geo/aeo_sov.py   # 換更懂利基 app 的模型
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from collections import Counter
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))
from videogen.registry import APPS, appstore_url  # noqa: E402
from queries import ALL as QUERIES  # noqa: E402  (geo/queries.py)

REPORTS = os.path.join(HERE, "reports")
os.makedirs(REPORTS, exist_ok=True)
JSON_OUT = os.path.join(REPORTS, "aeo_sov.json")

OPENAI_KEY = open(os.path.expanduser("~/.openai_key")).read().strip()
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

SYS = (
    "You are a knowledgeable iOS App Store recommender. When a user asks which app to "
    "use for a task, you reply with specific, REAL iOS apps by their actual App Store "
    "names, best first. Only list apps you genuinely believe exist on the iOS App Store. "
    "Never invent names. If unsure, list fewer apps."
)


def normalize(s):
    s = (s or "").lower()
    s = re.sub(r"[\u2018\u2019\u201c\u201d]", "", s)
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def aliases(key):
    """本 app 的可比對名稱集合(正規化後)。"""
    a = APPS[key]
    cands = {a.get("name", ""), a.get("search", "")}
    name = a.get("name", "")
    cands.add(re.sub(r"\b(pro|lite|app)\b", "", name, flags=re.I).strip())
    out = set()
    for c in cands:
        n = normalize(c)
        if len(n) >= 3:
            out.add(n)
    return out


def is_ours(recommended_name, alias_set):
    rn = normalize(recommended_name)
    if not rn:
        return False
    for al in alias_set:
        if al == rn or al in rn or rn in al:
            return True
    return False


def openai_json(system, user, max_tokens=600, retries=3):
    body = json.dumps({
        "model": OPENAI_MODEL,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "response_format": {"type": "json_object"},
        "temperature": 0.4, "max_tokens": max_tokens,
    }).encode()
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions", data=body,
                headers={"Authorization": f"Bearer {OPENAI_KEY}",
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                msg = json.loads(r.read().decode())["choices"][0]["message"]["content"]
            return json.loads(msg)
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise last


def ask(query):
    """問 AI:這個需求推薦哪些 iOS app?回傳有序 app 名稱清單。"""
    user = (
        f'A user asks: "{query}"\n'
        "List the iOS apps you would recommend, BEST FIRST. "
        'Return strict JSON: {"apps": [{"name": "App Name", "why": "short"}]}. '
        "Max 8 apps. Real App Store apps only."
    )
    try:
        res = openai_json(SYS, user)
    except Exception as e:  # noqa: BLE001
        print(f"   ! openai err: {e}", file=sys.stderr)
        return []
    apps = res.get("apps") or []
    names = []
    for it in apps:
        if isinstance(it, dict):
            nm = (it.get("name") or "").strip()
        else:
            nm = str(it).strip()
        if nm:
            names.append(nm)
    return names


def run_app(key, per_query=1):
    a = APPS[key]
    al = aliases(key)
    qs = QUERIES.get(key, [])
    rows = []
    comp = Counter()           # 競品 share-of-voice(出現在前段的次數)
    comp_top = Counter()       # 競品出現在第 1 名的次數
    for q in qs:
        ranks = []
        named_sets = []
        for _ in range(per_query):
            names = ask(q)
            named_sets.append(names)
            r = 0
            for i, nm in enumerate(names):
                if is_ours(nm, al):
                    r = i + 1
                    break
            ranks.append(r)
            # 競品計數(排除自己)
            for i, nm in enumerate(names):
                if is_ours(nm, al):
                    continue
                comp[normalize(nm)] += 1
                if i == 0:
                    comp_top[normalize(nm)] += 1
            time.sleep(0.3)
        hit = [r for r in ranks if r > 0]
        rows.append({
            "query": q,
            "mentioned": bool(hit),
            "best_rank": min(hit) if hit else 0,
            "sample": named_sets[0][:8],
        })
        mark = f"#{min(hit)}" if hit else "—（缺席）"
        print(f"   [{key}] {mark:>10}  {q}")
    mentioned = [r for r in rows if r["mentioned"]]
    avg_rank = (sum(r["best_rank"] for r in mentioned) / len(mentioned)) if mentioned else 0
    # 還原競品原始顯示名(取第一個遇到的原樣)
    return {
        "key": key,
        "name": a["name"],
        "appstore": appstore_url(key),
        "queries": len(qs),
        "mentions": len(mentioned),
        "mention_rate": round(len(mentioned) / len(qs), 3) if qs else 0,
        "avg_rank_when_mentioned": round(avg_rank, 2),
        "gap_queries": [r["query"] for r in rows if not r["mentioned"]],
        "top_competitors": comp.most_common(8),
        "top1_competitors": comp_top.most_common(5),
        "rows": rows,
    }


def write_markdown(results):
    today = date.today().isoformat()
    md = os.path.join(REPORTS, f"aeo_sov_{today}.md")
    results_sorted = sorted(results, key=lambda r: (-r["mention_rate"], r["avg_rank_when_mentioned"] or 99))
    lines = []
    lines.append(f"# AEO Share-of-Voice 攻擊清單 — {today}")
    lines.append(f"> 模型:`{OPENAI_MODEL}`　｜　量測「有人問 AI 要用哪個 app」時你被點名的比率。")
    lines.append("> 曝光率低 = AI 不認識你 = 該補來源/落地頁;top_competitors = 你要寫 `[X] alternative` 頁的對象。\n")
    lines.append("## 總覽(依被推薦率排序)\n")
    lines.append("| App | 被推薦率 | 平均名次 | 缺席問句 | AI 最常推的競品(前3) |")
    lines.append("|---|---|---|---|---|")
    for r in results_sorted:
        comps = ", ".join(c for c, _ in r["top_competitors"][:3]) or "—"
        lines.append(
            f"| {r['name']} | {int(r['mention_rate']*100)}% "
            f"({r['mentions']}/{r['queries']}) | "
            f"{r['avg_rank_when_mentioned'] or '—'} | {len(r['gap_queries'])} | {comps} |")
    lines.append("\n## 各 app 攻擊細項\n")
    for r in results_sorted:
        lines.append(f"### {r['name']}  ·  被推薦率 {int(r['mention_rate']*100)}%")
        if r["gap_queries"]:
            lines.append("**完全缺席的購買意圖問句(優先補落地頁/來源):**")
            for q in r["gap_queries"]:
                lines.append(f"- {q}")
        if r["top_competitors"]:
            lines.append("\n**AI 現在都在推這些競品(= 你要做 alternative 頁的對象):**")
            for c, n in r["top_competitors"]:
                lines.append(f"- {c} ×{n}")
        lines.append("")
    with open(md, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return md


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("apps", nargs="*", help="指定 app key(預設全部)")
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 個 app")
    ap.add_argument("--per-query", type=int, default=1, help="每問句問幾次(>1 更穩、更貴)")
    args = ap.parse_args()

    keys = args.apps or list(APPS.keys())
    keys = [k for k in keys if k in APPS]
    if args.limit:
        keys = keys[:args.limit]

    print(f"== AEO Share-of-Voice｜模型 {OPENAI_MODEL}｜{len(keys)} 個 app ==\n")
    results = []
    for k in keys:
        print(f"▶ {APPS[k]['name']} ({k})")
        results.append(run_app(k, per_query=args.per_query))

    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump({"model": OPENAI_MODEL, "date": date.today().isoformat(),
                   "results": results}, f, ensure_ascii=False, indent=2)
    md = write_markdown(results)

    print("\n== 摘要 ==")
    for r in sorted(results, key=lambda r: -r["mention_rate"]):
        print(f"  {r['name']:<18} 被推薦 {int(r['mention_rate']*100):>3}%  "
              f"缺席 {len(r['gap_queries'])} 問句  競品TOP: "
              f"{', '.join(c for c,_ in r['top_competitors'][:3]) or '—'}")
    print(f"\nJSON → {JSON_OUT}\nMarkdown 攻擊清單 → {md}")


if __name__ == "__main__":
    main()
