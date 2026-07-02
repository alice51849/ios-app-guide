#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每-app「可被 AI 引用」指南頁生成器(做到極致 · 全 20 app)。

為每個 app 產一個獨特、誠實、有用、schema 豐富的「怎麼選 X app + 推薦」頁,
鎖定最高購買意圖查詢,讓 ChatGPT/Google/Perplexity 有可引用的來源並點名你的 app。
內容由 OpenAI 依「真實功能(registry+ASO 描述)+ AI 實際推的競品(aeo_sov.json)」生成,
誠實、不灌詞、不對競品做不實宣稱、不捏造評分。

不碰 app code。

    python geo/aeo_guide.py                 # 全部 app(英文)
    python geo/aeo_guide.py scanto cyca     # 指定
    python geo/aeo_guide.py --publish       # 並 git push + IndexNow
"""
import argparse
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))
from videogen.registry import APPS, appstore_url  # noqa: E402

PAGES = os.path.join(HERE, "pages")
GUIDES = os.path.join(PAGES, "guides")
DATA = os.path.join(ROOT, "data")
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide").rstrip("/")
SOV = os.path.join(HERE, "reports", "aeo_sov.json")
OPENAI_KEY = open(os.path.expanduser("~/.openai_key")).read().strip()
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
e = html.escape

KEY2DATA = {
    "snapport": "snapport_full.json", "sononote": "sono_full.json", "cvdesk": "cv_full.json",
    "picclear": "picclear_full.json", "scanto": "scanto_full.json", "cyca": "cyca_full.json",
    "gmoney": "gmoney_full.json", "hourstag": "hourstag_full.json", "lockhour": "lockhour_full.json",
    "unblurry": "unblurry_full.json", "photocream": "photocream_full.json",
    "lumiletters": "letters_lite_full.json", "lumimath": "math_planet_full.json",
    "lumimission": "mission_routines_full.json", "lumiweather": "weather_full.json",
    "lumiletterspro": "letters_pro_full.json", "lumimathpro": "math_pro_full.json",
    "lumimissionpro": "mission_pro_full.json", "lumibopomofo": "bopomofo_full.json",
    "lumibopomofopro": "bopomofo_pro_full.json",
}
SCHEMA_CAT = {"photo-utility": "MultimediaApplication", "productivity": "BusinessApplication",
              "finance": "FinanceApplication", "health": "HealthApplication",
              "education": "EducationalApplication", "kids": "EducationalApplication"}


def en_desc(key):
    fn = KEY2DATA.get(key)
    if not fn or not os.path.exists(os.path.join(DATA, fn)):
        return ""
    d = json.load(open(os.path.join(DATA, fn), encoding="utf-8"))
    return (d.get("en-US", {}).get("description") or "")[:700]


def competitors(key):
    if not os.path.exists(SOV):
        return []
    data = json.load(open(SOV, encoding="utf-8"))
    for r in data.get("results", []):
        if r["key"] == key:
            return [c for c, _ in r.get("top_competitors", [])][:5]
    return []


def gaps(key):
    if not os.path.exists(SOV):
        return []
    data = json.load(open(SOV, encoding="utf-8"))
    for r in data.get("results", []):
        if r["key"] == key:
            return r.get("gap_queries", [])[:5]
    return []


def openai_json(system, user, max_tokens=900, retries=3):
    body = json.dumps({"model": OPENAI_MODEL,
                       "messages": [{"role": "system", "content": system},
                                    {"role": "user", "content": user}],
                       "response_format": {"type": "json_object"},
                       "temperature": 0.5, "max_tokens": max_tokens}).encode()
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request("https://api.openai.com/v1/chat/completions", data=body,
                                         headers={"Authorization": f"Bearer {OPENAI_KEY}",
                                                  "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(json.loads(r.read().decode())["choices"][0]["message"]["content"])
        except Exception as ex:  # noqa: BLE001
            last = ex
            time.sleep(1.5 * (attempt + 1))
    raise last


SYS = ("You write honest, genuinely useful 'how to choose + recommendation' guide content for "
       "iOS apps, the kind that AI assistants and Google would cite. Be specific and truthful. "
       "Do NOT invent ratings/stats. Do NOT make false claims about competitors (mention them "
       "neutrally as reference points only). Only claim 'pay once / no subscription / on-device / "
       "no ads' if the provided app facts support it. Output strict JSON.")


def gen_content(key):
    a = APPS[key]
    comps = competitors(key)
    g = gaps(key)
    user = (f"APP: {a['name']}\nOne-liner: {(a.get('sub') or '').replace(chr(10),' ')}\n"
            f"Category: {a.get('category')}\nKey facts (true): {', '.join(a.get('cta_bullets', []))}\n"
            f"Keywords: {', '.join(a.get('keywords', [])[:8])}\n"
            f"App Store description (excerpt): {en_desc(key)}\n"
            f"Competitors AI currently names: {', '.join(comps) or 'n/a'}\n"
            f"High-intent user questions to answer: {', '.join(g) or 'n/a'}\n\n"
            'Return JSON: {"title": "<=60 chars, includes the category + iPhone", '
            '"meta": "<=155 chars", "intro": "2-3 sentences on the problem and who it is for", '
            '"criteria": ["4-6 honest things to look for in this kind of app"], '
            '"why": "2-3 sentences honestly positioning THIS app and why it fits the criteria", '
            '"faqs": [{"q":"high-intent question","a":"answer that names the app, 1-3 sentences"}] }. '
            "Provide exactly 5 faqs. Natural, useful, citation-worthy. No hype, no fake numbers.")
    return openai_json(SYS, user)


def render(key, c):
    a = APPS[key]
    url = appstore_url(key)
    scat = SCHEMA_CAT.get(a.get("category", ""), "MobileApplication")
    title = (c.get("title") or f"{a['name']} — iPhone app guide")[:65]
    meta = (c.get("meta") or (a.get("sub") or "").replace("\n", " "))[:155]
    intro = c.get("intro", "")
    criteria = c.get("criteria", []) or []
    why = c.get("why", "")
    faqs = [(f.get("q", ""), f.get("a", "")) for f in (c.get("faqs") or []) if f.get("q")]

    app_schema = {"@context": "https://schema.org", "@type": "SoftwareApplication",
                  "name": a["name"], "operatingSystem": "iOS", "applicationCategory": scat,
                  "url": url, "installUrl": url, "description": meta,
                  "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD",
                             "description": "Free to download; one-time in-app purchase to unlock. No subscription."
                             if any("once" in b.lower() or "subscription" in b.lower()
                                    for b in a.get("cta_bullets", [])) else "Free to download."},
                  "featureList": a.get("cta_bullets", []) + a.get("keywords", [])[:5]}
    faq_schema = {"@context": "https://schema.org", "@type": "FAQPage",
                  "mainEntity": [{"@type": "Question", "name": q,
                                  "acceptedAnswer": {"@type": "Answer", "text": ans}} for q, ans in faqs]}
    ld = "\n".join(f'<script type="application/ld+json">\n{json.dumps(s, ensure_ascii=False, indent=2)}\n</script>'
                   for s in ([app_schema, faq_schema] if faqs else [app_schema]))
    crit_html = "\n".join(f"    <li>{e(x)}</li>" for x in criteria) or "    <li>Easy to use</li>"
    faq_html = "\n".join(
        f'    <div itemscope itemtype="https://schema.org/Question">\n'
        f'      <h3 itemprop="name">{e(q)}</h3>\n'
        f'      <div itemprop="acceptedAnswer" itemscope itemtype="https://schema.org/Answer">\n'
        f'        <p itemprop="text">{e(ans)}</p>\n      </div>\n    </div>'
        for q, ans in faqs)
    body = f"""  <h1>{e(c.get('title') or a['name'])}</h1>
  <p>{e(intro)}</p>

  <h2>What to look for</h2>
  <ul>
{crit_html}
  </ul>

  <h2>Recommended: {e(a['name'])}</h2>
  <p>{e(why)}</p>
  <p><a href="{e(url)}"><strong>Get {e(a['name'])} on the App Store →</strong></a></p>

  <h2>FAQ</h2>
{faq_html}

  <p style="margin-top:1.5em"><a href="{e(url)}"><strong>Try {e(a['name'])} →</strong></a></p>"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(meta)}">
<link rel="canonical" href="{SITE}/guides/{key}.html">
{ld}
</head>
<body>
<main>
{body}
<hr>
<p><small>Independent guide. App names are trademarks of their owners, used for identification only.</small></p>
</main>
</body>
</html>
"""


def write_sitemap():
    files = sorted(f for f in os.listdir(GUIDES) if f.endswith(".html"))
    sm = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          + "\n".join(f"  <url><loc>{SITE}/guides/{f}</loc></url>" for f in files)
          + "\n</urlset>\n")
    open(os.path.join(PAGES, "sitemap_guides.xml"), "w", encoding="utf-8").write(sm)


def publish(urls):
    def run(cmd, cwd=None):
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        print((r.stdout + r.stderr).strip()[-500:]); return r
    run(["git", "add", "-A"], cwd=PAGES)
    st = subprocess.run(["git", "status", "--porcelain"], cwd=PAGES, capture_output=True, text=True)
    if not st.stdout.strip():
        print("無變更。"); return
    run(["git", "-c", "user.name=alice51849", "-c", "user.email=alice51849@users.noreply.github.com",
         "commit", "-m", "Add per-app AI-citable guide pages (AEO max)"], cwd=PAGES)
    run(["git", "-c", "credential.helper=!gh auth git-credential", "push", "-q", "origin", "main"], cwd=PAGES)
    try:
        key = open(os.path.join(HERE, "indexnow_key.txt")).read().strip()
        host = re.sub(r"^https?://", "", SITE).split("/")[0]
        payload = json.dumps({"host": host, "key": key, "keyLocation": f"{SITE}/{key}.txt",
                              "urlList": urls}).encode()
        for ep in ("https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"):
            try:
                req = urllib.request.Request(ep, data=payload,
                                             headers={"Content-Type": "application/json; charset=utf-8"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    print(f"  IndexNow {ep} -> HTTP {r.status}")
            except Exception as ex:
                print(f"  IndexNow {ep} -> {ex}")
    except Exception as ex:
        print(f"  IndexNow 略過: {ex}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("apps", nargs="*")
    ap.add_argument("--publish", action="store_true")
    args = ap.parse_args()
    keys = [k for k in (args.apps or APPS.keys()) if k in APPS]
    os.makedirs(GUIDES, exist_ok=True)
    urls = []
    for k in keys:
        try:
            c = gen_content(k)
        except Exception as ex:  # noqa: BLE001
            print(f"  ! {k}: {str(ex)[:70]}"); continue
        open(os.path.join(GUIDES, f"{k}.html"), "w", encoding="utf-8").write(render(k, c))
        urls.append(f"{SITE}/guides/{k}.html")
        print(f"  ✓ {APPS[k]['name']}: {c.get('title','')[:50]}")
    write_sitemap()
    print(f"\n共 {len(urls)} 個指南頁 → {GUIDES}")
    if args.publish:
        publish(urls + [f"{SITE}/sitemap_guides.xml"])
    else:
        print("（加 --publish 部署)")


if __name__ == "__main__":
    main()
