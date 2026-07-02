#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每-app 指南頁「在地化」生成器(做到極致 · 多語)— 母語生成,非直譯。

把每個 app 的「怎麼選 + 推薦」指南,用各語言『母語、在地』生成(含本地化標題/FAQ/標籤),
放在 /<locale>/guides/<key>.html 並用 hreflang 互連 → 讓各語言的 ChatGPT/Google 都有可引用來源。
利基在各語言放大(注音→zh、護照照→多語、相片→多語)。

可續跑(state 檔)、分批部署(每 N 頁 push+IndexNow)。適合 detached 背景長跑。
不碰 app code。沿用 ~/.openai_key 與 aeo_guide 的 app 事實。

    python geo/aeo_guide_i18n.py                      # 全部 app × 全部語言(續跑)
    python geo/aeo_guide_i18n.py scanto --langs ja,ko # 指定
    python geo/aeo_guide_i18n.py --batch 40 --publish # 每 40 頁部署一次
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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))
sys.path.insert(0, HERE)
from videogen.registry import APPS, appstore_url  # noqa: E402
from aeo_guide import en_desc, competitors, gaps, SCHEMA_CAT, OPENAI_MODEL  # noqa: E402

PAGES = os.path.join(HERE, "pages")
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide").rstrip("/")
STATE = os.path.join(HERE, "reports", ".guide_i18n_state.json")
OPENAI_KEY = open(os.path.expanduser("~/.openai_key")).read().strip()
e = html.escape

# locale -> (語言名稱, 是否 RTL)
LANGS = {
    "ar-SA": ("Arabic", True), "ca": ("Catalan", False), "zh-Hans": ("Simplified Chinese", False),
    "zh-Hant": ("Traditional Chinese (Taiwan)", False), "hr": ("Croatian", False),
    "cs": ("Czech", False), "da": ("Danish", False), "nl-NL": ("Dutch", False),
    "fi": ("Finnish", False), "fr-FR": ("French", False), "de-DE": ("German", False),
    "el": ("Greek", False), "he": ("Hebrew", True), "hi": ("Hindi", False), "hu": ("Hungarian", False),
    "id": ("Indonesian", False), "it": ("Italian", False), "ja": ("Japanese", False),
    "ko": ("Korean", False), "ms": ("Malay", False), "no": ("Norwegian", False),
    "pl": ("Polish", False), "pt-BR": ("Brazilian Portuguese", False), "ro": ("Romanian", False),
    "ru": ("Russian", False), "sk": ("Slovak", False), "es-ES": ("Spanish", False),
    "sv": ("Swedish", False), "th": ("Thai", False), "tr": ("Turkish", False),
    "uk": ("Ukrainian", False), "vi": ("Vietnamese", False),
}
ALL_LOCALES = list(LANGS.keys())


def load_state():
    return set(tuple(x) for x in json.load(open(STATE))) if os.path.exists(STATE) else set()


def save_state(done):
    json.dump([list(x) for x in done], open(STATE, "w"))


def openai_json(system, user, max_tokens=1100, retries=3):
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
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(json.loads(r.read().decode())["choices"][0]["message"]["content"])
        except Exception as ex:  # noqa: BLE001
            last = ex
            time.sleep(1.5 * (attempt + 1))
    raise last


SYS = ("You are a native-speaking app reviewer writing a genuinely useful 'how to choose + "
       "recommendation' guide IN THE TARGET LANGUAGE (localize naturally, do NOT translate "
       "literally). Be honest and specific; never invent ratings/stats; mention competitors only "
       "neutrally. Only claim pay-once/no-subscription/on-device/no-ads if the app facts say so. "
       "Output strict JSON with ALL text fields written in the target language.")


def gen(key, locale):
    a = APPS[key]
    lang = LANGS[locale][0]
    user = (f"TARGET LANGUAGE: {lang} (locale {locale}).\n"
            f"APP: {a['name']}\nOne-liner: {(a.get('sub') or '').replace(chr(10),' ')}\n"
            f"Category: {a.get('category')}\nTrue facts: {', '.join(a.get('cta_bullets', []))}\n"
            f"App Store description (English, for grounding): {en_desc(key)}\n"
            f"Competitors AI names: {', '.join(competitors(key)) or 'n/a'}\n"
            f"High-intent questions (English, localize them): {', '.join(gaps(key)) or 'n/a'}\n\n"
            'Return JSON (ALL values in the target language): {"title":"<=60 chars","meta":"<=155",'
            '"intro":"2-3 sentences","criteria":["4-6 items"],"why":"2-3 sentences naming the app",'
            '"faqs":[{"q":"...","a":"..."}],"labels":{"look":"What to look for",'
            '"recommended":"Recommended","faq":"FAQ","cta":"Get it on the App Store"}}. '
            "Exactly 5 faqs. Natural, useful, citation-worthy.")
    return openai_json(SYS, user)


def hreflang_block(key):
    out = [f'<link rel="alternate" hreflang="en" href="{SITE}/guides/{key}.html">']
    for lc in ALL_LOCALES:
        out.append(f'<link rel="alternate" hreflang="{lc.split("-")[0]}" href="{SITE}/{lc}/guides/{key}.html">')
    out.append(f'<link rel="alternate" hreflang="x-default" href="{SITE}/guides/{key}.html">')
    return "\n".join(out)


def render(key, locale, c):
    a = APPS[key]
    url = appstore_url(key)
    scat = SCHEMA_CAT.get(a.get("category", ""), "MobileApplication")
    rtl = LANGS[locale][1]
    lb = c.get("labels", {}) or {}
    look = lb.get("look", "What to look for")
    rec = lb.get("recommended", "Recommended")
    faql = lb.get("faq", "FAQ")
    cta = lb.get("cta", "Get it on the App Store")
    title = (c.get("title") or a["name"])[:70]
    meta = (c.get("meta") or "")[:155]
    criteria = c.get("criteria", []) or []
    faqs = [(f.get("q", ""), f.get("a", "")) for f in (c.get("faqs") or []) if f.get("q")]

    app_schema = {"@context": "https://schema.org", "@type": "SoftwareApplication", "name": a["name"],
                  "operatingSystem": "iOS", "applicationCategory": scat, "inLanguage": locale,
                  "url": url, "installUrl": url, "description": meta,
                  "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}}
    faq_schema = {"@context": "https://schema.org", "@type": "FAQPage", "inLanguage": locale,
                  "mainEntity": [{"@type": "Question", "name": q,
                                  "acceptedAnswer": {"@type": "Answer", "text": ans}} for q, ans in faqs]}
    ld = "\n".join(f'<script type="application/ld+json">\n{json.dumps(s, ensure_ascii=False, indent=2)}\n</script>'
                   for s in ([app_schema, faq_schema] if faqs else [app_schema]))
    crit = "\n".join(f"    <li>{e(x)}</li>" for x in criteria) or "    <li>—</li>"
    faq_html = "\n".join(
        f'    <div itemscope itemtype="https://schema.org/Question">\n'
        f'      <h3 itemprop="name">{e(q)}</h3>\n'
        f'      <div itemprop="acceptedAnswer" itemscope itemtype="https://schema.org/Answer">\n'
        f'        <p itemprop="text">{e(ans)}</p>\n      </div>\n    </div>' for q, ans in faqs)
    dir_attr = ' dir="rtl"' if rtl else ""
    return f"""<!DOCTYPE html>
<html lang="{locale}"{dir_attr}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(meta)}">
<link rel="canonical" href="{SITE}/{locale}/guides/{key}.html">
{hreflang_block(key)}
{ld}
</head>
<body>
<main>
  <h1>{e(c.get('title') or a['name'])}</h1>
  <p>{e(c.get('intro',''))}</p>
  <h2>{e(look)}</h2>
  <ul>
{crit}
  </ul>
  <h2>{e(rec)}: {e(a['name'])}</h2>
  <p>{e(c.get('why',''))}</p>
  <p><a href="{e(url)}"><strong>{e(cta)} →</strong></a></p>
  <h2>{e(faql)}</h2>
{faq_html}
<hr>
<p><small>Independent guide. App names are trademarks of their owners, used for identification only.</small></p>
</main>
</body>
</html>
"""


def git_publish(n):
    def run(cmd):
        subprocess.run(cmd, cwd=PAGES, capture_output=True, text=True)
    run(["git", "add", "-A"])
    st = subprocess.run(["git", "status", "--porcelain"], cwd=PAGES, capture_output=True, text=True)
    if not st.stdout.strip():
        return
    run(["git", "-c", "user.name=alice51849", "-c", "user.email=alice51849@users.noreply.github.com",
         "commit", "-m", f"Localize app guide pages (+{n}) [AEO i18n]"])
    run(["git", "-c", "credential.helper=!gh auth git-credential", "push", "-q", "origin", "main"])
    print(f"  ⬆ 已部署一批(+{n} 頁)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("apps", nargs="*")
    ap.add_argument("--langs", default="", help="逗號分隔 locale(預設全部)")
    ap.add_argument("--batch", type=int, default=40, help="每 N 頁 commit+push 一次")
    ap.add_argument("--publish", action="store_true", help="邊跑邊部署(預設只寫檔)")
    args = ap.parse_args()

    keys = [k for k in (args.apps or APPS.keys()) if k in APPS]
    locales = [l for l in (args.langs.split(",") if args.langs else ALL_LOCALES) if l in LANGS]
    done = load_state()
    todo = [(k, lc) for k in keys for lc in locales if (k, lc) not in done]
    print(f"待生成 {len(todo)} 頁(已完成 {len(done)});語言 {len(locales)}、app {len(keys)}")
    n_since = 0
    for i, (k, lc) in enumerate(todo, 1):
        try:
            c = gen(k, lc)
        except Exception as ex:  # noqa: BLE001
            print(f"  ! {k}/{lc}: {str(ex)[:60]}"); continue
        d = os.path.join(PAGES, lc, "guides")
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, f"{k}.html"), "w", encoding="utf-8").write(render(k, lc, c))
        done.add((k, lc)); save_state(done); n_since += 1
        if i % 10 == 0 or i == len(todo):
            print(f"  [{i}/{len(todo)}] {k}/{lc} ✓")
        if args.publish and n_since >= args.batch:
            git_publish(n_since); n_since = 0
    if args.publish and n_since:
        git_publish(n_since)
    print(f"完成。state → {STATE}")


if __name__ == "__main__":
    main()
