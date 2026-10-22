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
from videogen.registry import APPS, APPSTORE, appstore_url  # noqa: E402
from aeo_guide import en_desc, competitors, gaps, SCHEMA_CAT, OPENAI_MODEL  # noqa: E402
from appstore_live import live_app_keys  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402

PAGES = os.environ.get("GEO_PAGES", os.path.join(HERE, "pages"))
SITE = os.environ.get("GEO_SITE", PUBLIC_SITE).rstrip("/")
STATE = os.path.join(HERE, "reports", ".guide_i18n_state.json")
try:
    OPENAI_KEY = open(os.path.expanduser("~/.openai_key")).read().strip()
except OSError:
    OPENAI_KEY = ""
e = html.escape
HREFLANG_BLOCK_RE = re.compile(
    r'(?:\s*<link\b[^>]*\brel="alternate"[^>]*'
    r'\bhreflang="[^"]+"[^>]*>)+',
    re.IGNORECASE,
)

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
    if not OPENAI_KEY:
        raise RuntimeError("~/.openai_key is required to generate guide content")
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


def hreflang_block(key, current_locale=None):
    out = []
    english = os.path.join(PAGES, "guides", f"{key}.html")
    if os.path.exists(english):
        out.append(
            f'<link rel="alternate" hreflang="en" '
            f'href="{SITE}/guides/{key}.html">'
        )
    for lc in ALL_LOCALES:
        target = os.path.join(PAGES, lc, "guides", f"{key}.html")
        if lc == current_locale or os.path.exists(target):
            out.append(
                f'<link rel="alternate" hreflang="{lc}" '
                f'href="{SITE}/{lc}/guides/{key}.html">'
            )
    default = (
        f"{SITE}/guides/{key}.html"
        if os.path.exists(english)
        else f"{SITE}/{current_locale}/guides/{key}.html"
    )
    out.append(
        f'<link rel="alternate" hreflang="x-default" href="{default}">'
    )
    return "\n".join(out)


def reconcile_hreflang(keys):
    changed = 0
    for key in keys:
        targets = [
            (os.path.join(PAGES, "guides", f"{key}.html"), None)
        ]
        targets.extend(
            (
                os.path.join(PAGES, locale, "guides", f"{key}.html"),
                locale,
            )
            for locale in ALL_LOCALES
        )
        for path, locale in targets:
            if not os.path.exists(path):
                continue
            with open(path, encoding="utf-8") as handle:
                original = handle.read()
            block = hreflang_block(key, locale)
            if HREFLANG_BLOCK_RE.search(original):
                updated = HREFLANG_BLOCK_RE.sub(
                    "\n" + block, original, count=1
                )
            else:
                canonical = re.search(
                    r'<link rel="canonical" href="[^"]+">', original
                )
                if not canonical:
                    raise ValueError(f"Missing canonical link in {path}")
                updated = (
                    original[: canonical.end()]
                    + "\n"
                    + block
                    + original[canonical.end() :]
                )
            if updated != original:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(updated)
                changed += 1
    return changed


FOOTER_DISCLAIMER = {
    "zh-Hant": "由 App 開發團隊 Lumi Studio 親自撰寫的指南。App 名稱為其各自所有權人的商標，僅供識別使用。若涉及文件、健康、學校及生產力相關的決定，請視情況核對相關單位的正式規定。",
    "zh-Hans": "由 App 开发团队 Lumi Studio 亲自撰写的指南。App 名称为其各自所有权人的商标，仅供识别使用。若涉及文档、健康、学校及生产力相关的决定，请视情况核对相关单位的正式规定。",
    "ja": "アプリ開発者であるLumi Studioが自ら作成したガイドです。アプリ名は各所有者の商標であり、識別目的でのみ使用されています。文書、健康、学校、生産性に関する決定を下す際は、必要に応じて関連機関の正式な要件をご確認ください。",
    "ko": "앱 개발자인 Lumi Studio에서 직접 작성한 가이드입니다. 앱 이름은 해당 소유자의 상표이며 식별 목적으로만 사용됩니다. 문서, 건강, 학교 및 생산성과 관련된 결정을 내릴 때는 필요에 따라 관련 기관의 공식 요건을 확인하시기 바랍니다.",
    "de-DE": "Ein vom App-Entwickler Lumi Studio selbst verfasster Ratgeber. App-Namen sind Marken ihrer jeweiligen Eigentümer und werden nur zur Identifikation verwendet. Bei Entscheidungen zu Dokumenten, Gesundheit, Schule und Produktivität prüfen Sie bitte gegebenenfalls die offiziellen Vorgaben.",
    "fr-FR": "Guide rédigé et publié par Lumi Studio, le développeur de l'app. Les noms d'apps sont des marques déposées de leurs propriétaires respectifs et sont utilisés uniquement à des fins d'identification. Pour les décisions relatives aux documents, à la santé, à l'école et à la productivité, veuillez vérifier les exigences officielles applicables.",
    "es-ES": "Guía publicada por Lumi Studio, el desarrollador de la app. Los nombres de las apps son marcas comerciales de sus respectivos propietarios y se utilizan únicamente con fines de identificación. Para decisiones relacionadas con documentos, salud, escuela y productividad, verifica los requisitos oficiales correspondientes cuando sea necesario.",
    "es-MX": "Guía escrita por Lumi Studio, el desarrollador de la app. Los nombres de las apps son marcas de sus dueños y se usan solo para identificarlas. Para decisiones sobre documentos, salud, escuela y productividad, revisa los requisitos oficiales cuando aplique.",
    "pt-BR": "Guia publicado pela Lumi Studio, desenvolvedora do app. Os nomes dos apps são marcas registradas de seus respectivos proprietários e são usados apenas para fins de identificação. Para decisões sobre documentos, saúde, escola e produtividade, verifique os requisitos oficiais correspondentes quando aplicável.",
    "it": "Guida redatta dall'editore Lumi Studio, lo sviluppatore dell'app. I nomi delle app sono marchi dei rispettivi proprietari e sono usati solo a scopo identificativo. Per decisioni che riguardano documenti, salute, scuola e produttività, verifica i requisiti ufficiali quando è rilevante.",
}
DEFAULT_FOOTER_DISCLAIMER = (
    "Publisher-authored guide from Lumi Studio, the app developer. App names "
    "are trademarks of their owners and are used only for identification. "
    "For documents, health, school, and productivity decisions, verify "
    "official requirements where relevant."
)


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
                  "url": url, "installUrl": url, "description": meta}
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
{hreflang_block(key, locale)}
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
<p data-publisher-disclosure="true"><small>{e(FOOTER_DISCLAIMER.get(locale, DEFAULT_FOOTER_DISCLAIMER))}</small></p>
</main>
</body>
</html>
"""


def git_publish(n):
    def run(cmd):
        return subprocess.run(
            cmd, cwd=PAGES, capture_output=True, text=True, check=True
        )
    run(["git", "add", "-A"])
    st = run(["git", "status", "--porcelain"])
    if not st.stdout.strip():
        return
    run(["git", "-c", "user.name=alice51849", "-c", "user.email=alice51849@users.noreply.github.com",
         "commit", "-m", f"Localize app guide pages (+{n}) [AEO i18n]"])
    run(["git", "pull", "--rebase", "--autostash", "-X", "theirs"])
    run(["git", "-c", "credential.helper=!gh auth git-credential", "push", "-q", "origin", "main"])
    print(f"  ⬆ 已部署一批(+{n} 頁)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("apps", nargs="*")
    ap.add_argument("--langs", default="", help="逗號分隔 locale(預設全部)")
    ap.add_argument("--batch", type=int, default=40, help="每 N 頁 commit+push 一次")
    ap.add_argument("--publish", action="store_true", help="邊跑邊部署(預設只寫檔)")
    ap.add_argument(
        "--cached-live",
        action="store_true",
        help="Use the verified availability snapshot without refreshing it.",
    )
    args = ap.parse_args()

    public = live_app_keys(
        APPSTORE, PAGES, refresh=not args.cached_live
    )
    unavailable = [key for key in args.apps if key not in public]
    if unavailable:
        raise SystemExit(
            "App Store not public; outreach skipped: "
            + ", ".join(unavailable)
        )
    keys = [
        key
        for key in (args.apps or APPS.keys())
        if key in APPS and key in public
    ]
    locales = [l for l in (args.langs.split(",") if args.langs else ALL_LOCALES) if l in LANGS]
    done = load_state()
    for key in set(APPS) - public:
        for locale in ALL_LOCALES:
            stale = os.path.join(PAGES, locale, "guides", f"{key}.html")
            if os.path.exists(stale):
                os.remove(stale)
    done = {
        (key, locale)
        for key, locale in done
        if key in public
        and os.path.exists(
            os.path.join(PAGES, locale, "guides", f"{key}.html")
        )
    }
    save_state(done)
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
            reconciled = reconcile_hreflang(keys)
            git_publish(n_since + reconciled)
            n_since = 0
    reconciled = reconcile_hreflang(keys)
    if args.publish and (n_since or reconciled):
        git_publish(n_since + reconciled)
    print(f"完成。state → {STATE}")


if __name__ == "__main__":
    main()
