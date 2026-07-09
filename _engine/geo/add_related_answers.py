#!/usr/bin/env python3
"""Add a "Related answers" internal-linking section to EN answer pages.

Answer pages had no outbound sibling links (only the app hub links to them). This
injects up to 4 topically-closest same-app sibling links before </main>, improving
internal linking, topical clustering and on-site retention. Idempotent (replaces any
existing related-answers section). Reuses each page's CTA App Store id for grouping
and each sibling's <h1> for the link text.
"""
import os, re, glob, html, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages")
ANS = os.path.join(ROOT, "answers")
SITE = "https://alice51849.github.io/ios-app-guide"
MAXN = 4
STOP = set("a an the and or of to in for on at by as it this that these those you your with how do i my is are can app apps for iphone ios free best what when should choose vs".split())
SEC_RE = re.compile(r'<section class="wrap related-answers">.*?</section>', re.S)
# Localized "Related answers" heading per locale (fallback to English)
HEADINGS = {
    "": "Related answers", "zh-Hant": "\u5ef6\u4f38\u95b1\u8b80", "zh-Hans": "\u5ef6\u4f38\u9605\u8bfb",
    "ja": "\u95a2\u9023\u3059\u308b\u56de\u7b54", "ko": "\uad00\ub828 \ub2f5\ubcc0",
    "es-ES": "Respuestas relacionadas", "es-MX": "Respuestas relacionadas",
    "de-DE": "Verwandte Antworten", "fr-FR": "R\u00e9ponses associ\u00e9es",
    "pt-BR": "Respostas relacionadas", "pt-PT": "Respostas relacionadas",
    "it": "Risposte correlate", "ru": "\u041f\u043e\u0445\u043e\u0436\u0438\u0435 \u043e\u0442\u0432\u0435\u0442\u044b",
    "ms": "Jawapan berkaitan", "pl": "Powi\u0105zane odpowiedzi", "ar-SA": "\u0625\u062c\u0627\u0628\u0627\u062a \u0630\u0627\u062a \u0635\u0644\u0629",
}

def appid(h):
    m = re.search(r'apps\.apple\.com/app/id(\d+)', h)
    return m.group(1) if m else None

def get_h1(h):
    m = re.search(r'<h1[^>]*>(.*?)</h1>', h, re.S)
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', m.group(1))).strip() if m else None

def tokens(slug):
    return {t for t in slug.split('-') if t and t not in STOP and not t.isdigit()}

def main():
    dry = "--dry-run" in sys.argv
    locale = ""
    for i, a in enumerate(sys.argv):
        if a == "--locale" and i + 1 < len(sys.argv):
            locale = sys.argv[i + 1]
    ans_dir = os.path.join(ROOT, locale, "answers") if locale else ANS
    url_base = f"{SITE}/{locale}/answers" if locale else f"{SITE}/answers"
    heading = HEADINGS.get(locale, HEADINGS[""])
    pages = {}
    for f in sorted(glob.glob(os.path.join(ans_dir, "*.html"))):
        slug = os.path.basename(f)[:-5]
        if slug == "index":
            continue
        h = open(f, encoding="utf-8").read()
        a = appid(h)
        if not a:
            continue
        pages[slug] = {"app": a, "h1": get_h1(h) or slug, "tok": tokens(slug), "f": f, "html": h}
    # group by app
    by_app = {}
    for slug, p in pages.items():
        by_app.setdefault(p["app"], []).append(slug)
    changed = 0
    for slug, p in pages.items():
        sibs = [s for s in by_app[p["app"]] if s != slug]
        # rank by shared non-stopword slug tokens, then by title length (shorter=more canonical)
        ranked = sorted(sibs, key=lambda s: (-len(p["tok"] & pages[s]["tok"]), len(pages[s]["h1"])))
        top = ranked[:MAXN]
        if not top:
            continue
        items = "".join(
            f'<li><a href="{url_base}/{s}.html">{html.escape(pages[s]["h1"])}</a></li>'
            for s in top
        )
        section = f'<section class="wrap related-answers"><h2>{html.escape(heading)}</h2><ul>{items}</ul></section>'
        h = p["html"]
        h2 = SEC_RE.sub("", h)  # remove existing (idempotent)
        if "</main>" not in h2:
            continue
        h2 = h2.replace("</main>", section + "</main>", 1)
        if h2 != h:
            changed += 1
            if dry and changed <= 3:
                print(f"[{slug}] app={p['app']} -> related: {top}")
            if not dry:
                open(p["f"], "w", encoding="utf-8").write(h2)
    print(f"{'DRY ' if dry else ''}locale={locale or 'en'} changed={changed} / {len(pages)} pages")

if __name__ == "__main__":
    main()
