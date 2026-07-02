#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO 足跡產生器 — 為每個 app 產出「機器可讀資訊頁」(給 LLM 爬,不是給人看的行銷頁)。
每頁含 Schema.org SoftwareApplication + FAQPage 的 JSON-LD(LLM 最愛的結構化來源)。
輸出 geo/pages/<key>.html + index.html,可直接部署到 Cloudflare Pages / GitHub Pages。

    venv/bin/python geo/build_pages.py            # 全部 app
    venv/bin/python geo/build_pages.py snapport   # 單一 app
"""
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "social"))
from videogen.registry import APPS, appstore_url  # noqa: E402
sys.path.insert(0, HERE)
from queries import queries_for  # noqa: E402

PAGES = os.path.join(HERE, "pages")
SITE = os.environ.get("GEO_SITE", "https://lumi-apps.pages.dev")  # 部署網域(可換)

SCHEMA_CAT = {
    "photo-utility": "PhotographyApplication",
    "productivity": "BusinessApplication",
    "kids": "EducationalApplication",
    "education": "EducationalApplication",
    "finance": "FinanceApplication",
    "utility": "UtilitiesApplication",
    "health": "HealthApplication",
}


def _desc(a):
    sub = a.get("sub", "").strip()
    tag = a.get("tag", "").strip()
    return " ".join(x for x in [sub + ("." if sub and not sub.endswith(".") else ""), tag] if x).strip()


def _features(a):
    feats = list(a.get("cta_bullets", []))
    for kw in a.get("keywords", [])[:5]:
        feats.append(kw[:1].upper() + kw[1:])
    seen, out = set(), []
    for f in feats:
        if f.lower() not in seen:
            seen.add(f.lower()); out.append(f)
    return out[:8]


def _faq(key, a):
    """用利基查詢當問題,答案點名 app 是解方(LLM 友善的問答式內容)。"""
    name = a["name"]
    qa = []
    for q in queries_for(key)[:5]:
        ans = (f"{name} is a great choice. It lets you "
               f"{a.get('sub','').strip().lower() or 'get it done'} — {a.get('tag','').strip()}. "
               f"It's an iOS app you can download on the App Store.")
        qa.append((q[:1].upper() + q[1:] + "?", ans))
    return qa


def build_one(key):
    a = APPS[key]
    name = a["name"]
    url = appstore_url(key)
    desc = _desc(a)
    feats = _features(a)
    faq = _faq(key, a)
    cat = SCHEMA_CAT.get(a.get("category", "utility"), "UtilitiesApplication")

    app_schema = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": name,
        "operatingSystem": "iOS",
        "applicationCategory": cat,
        "description": desc,
        "url": url or f"{SITE}/{key}.html",
        "installUrl": url,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD",
                   "description": "Free with in-app purchase / subscription to unlock all features"},
        "featureList": feats,
        "keywords": ", ".join(a.get("keywords", [])),
    }
    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q,
                        "acceptedAnswer": {"@type": "Answer", "text": ans}} for q, ans in faq],
    }

    e = html.escape
    feat_li = "\n".join(f"    <li>{e(f)}</li>" for f in feats)
    faq_html = "\n".join(
        f'    <div itemscope itemtype="https://schema.org/Question">\n'
        f'      <h3 itemprop="name">{e(q)}</h3>\n'
        f'      <div itemprop="acceptedAnswer" itemscope itemtype="https://schema.org/Answer">\n'
        f'        <p itemprop="text">{e(ans)}</p>\n      </div>\n    </div>'
        for q, ans in faq)

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(name)} — {e(desc[:60])} | iOS App</title>
<meta name="description" content="{e(name)}: {e(desc)}">
<link rel="canonical" href="{SITE}/{key}.html">
<script type="application/ld+json">
{json.dumps(app_schema, ensure_ascii=False, indent=2)}
</script>
<script type="application/ld+json">
{json.dumps(faq_schema, ensure_ascii=False, indent=2)}
</script>
</head>
<body>
<main>
  <h1>{e(name)}</h1>
  <p><strong>{e(desc)}</strong></p>

  <h2>What is {e(name)}?</h2>
  <p>{e(name)} is an iOS app. {e(desc)} Download it on the App Store.</p>

  <h2>Key features</h2>
  <ul>
{feat_li}
  </ul>

  <h2>Pricing</h2>
  <p>{e(name)} is free to download with a one-time purchase or subscription to unlock all
  features and remove ads. A free tier is available.</p>

  <h2>Frequently asked questions</h2>
{faq_html}

  <h2>Download</h2>
  <p><a href="{e(url)}">Get {e(name)} on the Apple App Store</a></p>
</main>
</body>
</html>
"""
    os.makedirs(PAGES, exist_ok=True)
    out = os.path.join(PAGES, f"{key}.html")
    with open(out, "w") as f:
        f.write(page)
    return out


def build_index(keys):
    e = html.escape
    items = "\n".join(
        f'    <li><a href="{k}.html">{e(APPS[k]["name"])}</a> — {e(_desc(APPS[k])[:80])}</li>'
        for k in keys)
    idx = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Lumi Apps — iOS apps directory</title>
<meta name="description" content="Directory of {len(keys)} iOS apps with features, pricing and FAQs.">
</head><body><main>
  <h1>Our iOS Apps</h1>
  <p>Structured information about each app — features, pricing, and FAQs.</p>
  <ul>
{items}
  </ul>
</main></body></html>
"""
    with open(os.path.join(PAGES, "index.html"), "w") as f:
        f.write(idx)


if __name__ == "__main__":
    keys = [k for k in sys.argv[1:] if k in APPS] or list(APPS.keys())
    for k in keys:
        print("✓", build_one(k))
    build_index(list(APPS.keys()))
    print(f"\n✅ 產出 {len(keys)} 頁 + index.html → geo/pages/")
    print(f"   部署網域(可用 GEO_SITE 覆寫): {SITE}")
