#!/usr/bin/env python3
"""Add a "Related answers" internal-linking section to EN answer pages.

Answer pages had no outbound sibling links (only the app hub links to them). This
injects up to 4 topically-closest same-app sibling links before </main>, improving
internal linking, topical clustering and on-site retention. Idempotent (replaces any
existing related-answers section). Reuses each page's CTA App Store id for grouping
and each sibling's <h1> for the link text.
"""
import os, re, glob, html, sys
from site_config import PUBLIC_SITE  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages")
ANS = os.path.join(ROOT, "answers")
SITE = PUBLIC_SITE
MAXN = 4
STOP = set("a an the and or of to in for on at by as it this that these those you your with how do i my is are can app apps for iphone ios free best what when should choose vs".split())
SEC_RE = re.compile(r'<section class="wrap related-answers">.*?</section>', re.S)
RELATED_OVERRIDES = {
    "app-to-check-my-resume-ats-score": (
        "what-is-an-ats-and-how-to-make-a-resume-ats-friendly",
        "should-i-send-my-resume-as-pdf-or-word",
        "how-to-make-an-ats-friendly-resume-on-iphone-without-a-subscription",
        "app-to-export-my-cv-as-a-clean-pdf",
    ),
    "how-to-build-an-aesthetic-weekly-reset-checklist-on-iphone": (
        "how-to-make-a-daily-planning-routine-you-actually-enjoy-and-stick-to",
        "best-aesthetic-to-do-list-app-iphone-no-subscription",
        "iphone-lock-screen-widget-to-check-off-tasks-without-opening-app",
        "what-do-you-get-for-free-in-mochi-to-do",
    ),
}
# Localized "Related answers" heading per locale (fallback to English)
HEADINGS = {
    "": "Related answers", "zh-Hant": "\u5ef6\u4f38\u95b1\u8b80", "zh-Hans": "\u5ef6\u4f38\u9605\u8bfb",
    "ja": "\u95a2\u9023\u3059\u308b\u56de\u7b54", "ko": "\uad00\ub828 \ub2f5\ubcc0",
    "es-ES": "Respuestas relacionadas", "es-MX": "Respuestas relacionadas",
    "de-DE": "Verwandte Antworten", "fr-FR": "R\u00e9ponses associ\u00e9es",
    "pt-BR": "Respostas relacionadas", "pt-PT": "Respostas relacionadas",
    "it": "Risposte correlate", "ru": "\u041f\u043e\u0445\u043e\u0436\u0438\u0435 \u043e\u0442\u0432\u0435\u0442\u044b",
    "ms": "Jawapan berkaitan", "pl": "Powi\u0105zane odpowiedzi", "ar-SA": "\u0625\u062c\u0627\u0628\u0627\u062a \u0630\u0627\u062a \u0635\u0644\u0629",
    # \u5176\u9918\u5b98\u65b9\u8a9e\u7cfb:\u5c11\u4e86\u9019\u4e9b\u5b57,\u8a72\u8a9e\u7cfb\u7684\u9801\u9762\u6703\u639b\u4e00\u500b\u82f1\u6587\u6a19\u984c(\u7ad9\u4e0a\u5df2\u7d93\u6709
    # 41.8% \u7684\u9801\u662f\u300c\u7ffb\u8b6f\u904e\u4f46\u5176\u5be6\u9084\u662f\u82f1\u6587\u300d,\u5225\u518d\u591a\u88fd\u9020\u4e00\u6279)\u3002
    "th": "\u0e04\u0e33\u0e16\u0e32\u0e21\u0e17\u0e35\u0e48\u0e40\u0e01\u0e35\u0e48\u0e22\u0e27\u0e02\u0e49\u0e2d\u0e07",
    "vi": "C\u00e2u tr\u1ea3 l\u1eddi li\u00ean quan",
    "id": "Jawaban terkait", "tr": "\u0130lgili yan\u0131tlar",
    "nl-NL": "Gerelateerde antwoorden", "sv": "Relaterade svar",
    "da": "Relaterede svar", "no": "Relaterte svar", "fi": "Aiheeseen liittyv\u00e4t vastaukset",
    "cs": "Souvisej\u00edc\u00ed odpov\u011bdi", "sk": "S\u00favisiace odpovede",
    "hu": "Kapcsol\u00f3d\u00f3 v\u00e1laszok", "ro": "R\u0103spunsuri conexe",
    "hr": "Povezani odgovori", "sl-SI": "Sorodni odgovori",
    "uk": "\u041f\u043e\u0432'\u044f\u0437\u0430\u043d\u0456 \u0432\u0456\u0434\u043f\u043e\u0432\u0456\u0434\u0456",
    "el": "\u03a3\u03c7\u03b5\u03c4\u03b9\u03ba\u03ad\u03c2 \u03b1\u03c0\u03b1\u03bd\u03c4\u03ae\u03c3\u03b5\u03b9\u03c2",
    "he": "\u05ea\u05e9\u05d5\u05d1\u05d5\u05ea \u05e7\u05e9\u05d5\u05e8\u05d5\u05ea",
    "ca": "Respostes relacionades",
    "hi": "\u0938\u0902\u092c\u0902\u0927\u093f\u0924 \u0909\u0924\u094d\u0924\u0930",
    "fr-CA": "R\u00e9ponses associ\u00e9es",
}

def appid(h):
    m = re.search(r'apps\.apple\.com/app/id(\d+)', h)
    return m.group(1) if m else None

def get_h1(h):
    m = re.search(r'<h1[^>]*>(.*?)</h1>', h, re.S)
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', m.group(1))).strip() if m else None

def tokens(slug):
    return {t for t in slug.split('-') if t and t not in STOP and not t.isdigit()}


def related_slugs(slug, page, pages, by_app):
    siblings = [s for s in by_app[page["app"]] if s != slug]
    preferred = [
        sibling
        for sibling in RELATED_OVERRIDES.get(slug, ())
        if sibling in pages and pages[sibling]["app"] == page["app"]
    ]
    if preferred:
        return preferred[:MAXN]
    return sorted(
        siblings,
        key=lambda sibling: (
            -len(page["tok"] & pages[sibling]["tok"]),
            len(pages[sibling]["h1"]),
        ),
    )[:MAXN]


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
        top = related_slugs(slug, p, pages, by_app)
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
