#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Topic hub / pillar pages — 每個 App 一頁,把它的所有內容內部串起來。

集中主題權威度 + 加速爬蟲索引全站(內部連結是排名/被引用的關鍵因子)。
純本機、無 OpenAI、無 App/App Store 變更。輸出 geo/pages/hubs/<key>.html + sitemap_hubs.xml。
"""
import html
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))
sys.path.insert(0, HERE)
from videogen.registry import APPS, appstore_url  # noqa: E402
import queries  # noqa: E402

PAGES = os.path.join(HERE, "pages")
HUBS = os.path.join(PAGES, "hubs")
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide").rstrip("/")


def slugify(q):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", q.lower())).strip("-")


def page_title(path, fallback):
    try:
        with open(path, encoding="utf-8") as f:
            m = re.search(r"<title>([^<]+)</title>", f.read(2000))
        if m:
            return html.unescape(m.group(1)).split(":")[0].split("|")[0].strip()
    except OSError:
        pass
    return fallback


def exists(rel):
    return os.path.exists(os.path.join(PAGES, rel))


STYLE = (":root{--bg:#f7f7fb;--card:#fff;--ink:#161622;--muted:#5d6370;--line:#e6e7ef;--brand:#5b5ff2}"
         "*{box-sizing:border-box}body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;"
         "background:linear-gradient(180deg,#fff,var(--bg));color:var(--ink);line-height:1.6}a{color:#3840d0}"
         ".wrap{width:min(1040px,100% - 32px);margin:auto}.top{padding:16px 0;border-bottom:1px solid var(--line);"
         "background:rgba(255,255,255,.86);backdrop-filter:blur(12px);position:sticky;top:0;z-index:3}.nav{display:flex;gap:16px}"
         ".nav a{text-decoration:none;font-weight:700}.hero{padding:40px 0 16px}h1{font-size:clamp(1.8rem,5vw,3rem);margin:.2em 0}"
         "h2{font-size:1.3rem;margin:1.4em 0 .5em}p.lead{font-size:1.12rem;color:var(--muted);max-width:760px}"
         ".card{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:20px;margin:14px 0;box-shadow:0 8px 30px rgba(31,34,78,.06)}"
         ".ll a{display:block;padding:9px 0;border-bottom:1px solid var(--line);text-decoration:none;font-weight:600}"
         ".cta{display:inline-block;border-radius:999px;background:linear-gradient(135deg,#5b5ff2,#8b5cf6);color:#fff!important;"
         "text-decoration:none;font-weight:800;padding:12px 20px;margin-top:8px}.pill{display:inline-block;border:1px solid var(--line);"
         "background:#fff;border-radius:999px;padding:6px 12px;margin:3px;font-weight:700;text-decoration:none}"
         ".footer{margin-top:36px;padding:24px 0;border-top:1px solid var(--line);color:var(--muted);font-size:.9rem}")


def build_hub(key):
    a = APPS[key]
    e = html.escape
    name = a["name"]
    sub = (a.get("sub") or a.get("tag") or "").strip()
    url = appstore_url(key, "iag_hub") or f"{SITE}/en-US/{key}.html"
    canon = f"{SITE}/hubs/{key}.html"

    # answer pages (this app), existing only, with titles
    ans = []
    for q in queries.ALL.get(key, []):
        s = slugify(q)
        rel = f"answers/{s}.html"
        if exists(rel):
            t = page_title(os.path.join(PAGES, rel), q)
            ans.append((f"{SITE}/{rel}", t))
    ans_html = "".join(f'<a href="{e(u)}">{e(t)}</a>' for u, t in dict((u, t) for u, t in ans).items()) or "<p>Coming soon.</p>"

    # other resources
    res = []
    if exists(f"en-US/{key}.html"):
        res.append((f"{SITE}/en-US/{key}.html", f"{name} — overview & FAQ"))
    if exists(f"guides/{key}.html"):
        res.append((f"{SITE}/guides/{key}.html", f"How to choose: {name} guide"))
    if exists(f"stories/{key}.html"):
        res.append((f"{SITE}/stories/{key}.html", f"{name} — visual story"))
    for f in sorted(os.listdir(os.path.join(PAGES, "alternatives"))) if os.path.isdir(os.path.join(PAGES, "alternatives")) else []:
        if f.startswith(key + "-") and f.endswith(".html"):
            res.append((f"{SITE}/alternatives/{f}", page_title(os.path.join(PAGES, "alternatives", f), f)))
    res_html = "".join(f'<a href="{e(u)}">{e(t)}</a>' for u, t in res) or ""

    # language pills (landing pages in many languages)
    langs = []
    for lc in sorted(os.listdir(PAGES)):
        if re.fullmatch(r"[a-z]{2}(-[A-Z]{2})?", lc) and exists(f"{lc}/{key}.html"):
            langs.append(f'<a class="pill" href="{SITE}/{lc}/{key}.html" hreflang="{lc}">{lc}</a>')
    langs_html = "".join(langs)

    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(name)}: guides, answers & alternatives | iOS App Guide</title>
<meta name="description" content="Everything about {e(name)} — {e(sub)}. Buying guides, answers to common questions, comparisons and the App Store link.">
<link rel="canonical" href="{canon}">
<style>{STYLE}</style>
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"CollectionPage","name":"{e(name)} resources","url":"{canon}","about":{{"@type":"SoftwareApplication","name":"{e(name)}","operatingSystem":"iOS","applicationCategory":"MobileApplication","offers":{{"@type":"Offer","price":"0","priceCurrency":"USD"}}}}}}</script>
</head><body>
<header class="top"><div class="wrap nav"><a href="{SITE}/index.html">iOS App Guide</a><a href="{SITE}/answers/">Answers</a><a href="{SITE}/stories/">Stories</a></div></header>
<main class="wrap">
<section class="hero"><h1>{e(name)}</h1><p class="lead">{e(sub)}</p><a class="cta" href="{e(url)}">Get {e(name)} on the App Store →</a></section>
<section class="card"><h2>Answers to common questions</h2><div class="ll">{ans_html}</div></section>
{"<section class='card'><h2>Guides, comparisons & more</h2><div class='ll'>" + res_html + "</div></section>" if res_html else ""}
{"<section class='card'><h2>Available in your language</h2>" + langs_html + "</section>" if langs_html else ""}
</main>
<footer class="footer"><div class="wrap">Independent iOS app guide. <a href="{e(url)}">{e(name)} on the App Store</a>.</div></footer>
</body></html>'''


def main():
    os.makedirs(HUBS, exist_ok=True)
    keys = [k for k in APPS if appstore_url(k)]
    for k in keys:
        open(os.path.join(HUBS, f"{k}.html"), "w", encoding="utf-8").write(build_hub(k))
    # index
    e = html.escape
    cards = "".join(f'<a class="pill" href="{SITE}/hubs/{k}.html">{e(APPS[k]["name"])}</a>' for k in keys)
    idx = (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           f'<title>iOS App Guides — topic hubs</title><link rel="canonical" href="{SITE}/hubs/">'
           f'<style>{STYLE}</style></head><body><main class="wrap"><h1 style="margin-top:30px">App topic hubs</h1>'
           f'<div style="margin-top:16px">{cards}</div></main></body></html>')
    open(os.path.join(HUBS, "index.html"), "w", encoding="utf-8").write(idx)
    # sitemap
    lm = time.strftime("%Y-%m-%d", time.gmtime())
    rows = [f'  <url><loc>{SITE}/hubs/{k}.html</loc><lastmod>{lm}</lastmod></url>' for k in keys]
    rows.append(f'  <url><loc>{SITE}/hubs/index.html</loc><lastmod>{lm}</lastmod></url>')
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(rows) + "\n</urlset>\n")
    open(os.path.join(PAGES, "sitemap_hubs.xml"), "w", encoding="utf-8").write(xml)
    print(f"\u2713 {len(keys)} topic hubs + index + sitemap_hubs.xml")


if __name__ == "__main__":
    main()
