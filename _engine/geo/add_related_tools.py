#!/usr/bin/env python3
"""Add a "Free tools" section to answer pages, linking the same-app free tool(s).

Answer pages never linked to the site's free tools (e.g. Bopomofo answers -> Zhuyin
practice-sheet / flashcards / chart / bingo). This injects a localized "Free tools"
section (before the related-answers section) with links to same-app tools, driving
users to genuinely useful free utilities (which are link/share magnets) and adding
internal links. Idempotent; per-locale (same-locale tool pages + localized heading).
"""
import os, re, glob, html, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages")
SITE = "https://alice51849.github.io/ios-app-guide"
SEC_RE = re.compile(r'<section class="wrap related-tools">.*?</section>', re.S)
HEADINGS = {
    "": "Free tools", "zh-Hant": "\u514d\u8cbb\u5de5\u5177", "zh-Hans": "\u514d\u8d39\u5de5\u5177",
    "ja": "\u7121\u6599\u30c4\u30fc\u30eb", "ko": "\ubb34\ub8cc \ub3c4\uad6c",
    "es-ES": "Herramientas gratis", "es-MX": "Herramientas gratis",
    "de-DE": "Kostenlose Tools", "fr-FR": "Outils gratuits",
    "pt-BR": "Ferramentas gratuitas", "ms": "Alat percuma",
    "pl": "Darmowe narz\u0119dzia", "ar-SA": "\u0623\u062f\u0648\u0627\u062a \u0645\u062c\u0627\u0646\u064a\u0629",
}
BOPOMOFO_APP_IDS = ("6773017109", "6775773117")
BOPOMOFO_TOOL_PRIORITY = {
    "zhuyin-readiness-check.html": 0,
    "zhuyin-grade1-14-day-summer-calendar.html": 1,
    "zhuyin-blending-card-generator.html": 2,
    "zhuyin-short-sentence-reading-cards.html": 2.5,
    "zhuyin-decodable-mini-reader.html": 2.75,
    "zhuyin-library-storytime-kit.html": 3,
    "zhuyin-parent-teacher-handoff-kit.html": 4,
    "zhuyin-family-picture-book-club-kit.html": 5,
    "zhuyin-grandparent-video-call-kit.html": 6,
}
DEFAULT_TOOL_LIMIT = 5


def tool_sort_key(path):
    filename = os.path.basename(path)
    return (BOPOMOFO_TOOL_PRIORITY.get(filename, 4), filename)


def related_tool_limit(tools):
    if any(
        marker.removesuffix(".html") in url
        for url, _label in tools
        for marker in BOPOMOFO_TOOL_PRIORITY
    ):
        return len(tools)
    return DEFAULT_TOOL_LIMIT

def appid(h):
    m = re.search(r'apps\.apple\.com/app/id(\d+)', h)
    return m.group(1) if m else None

def get_h1(h):
    m = re.search(r'<h1[^>]*>(.*?)</h1>', h, re.S)
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', m.group(1))).strip() if m else None

def label(slug, h1, locale):
    # EN: avoid leaked CJK h1 -> title-case the slug; locales: use localized h1
    if not h1 or (locale == "" and re.search(r'[\u3040-\u9fff]', h1)):
        return slug.replace("-", " ").title()
    return h1


def related_app_ids(app_id, slug):
    if app_id in BOPOMOFO_APP_IDS and slug.startswith("zhuyin-"):
        return BOPOMOFO_APP_IDS
    return (app_id,)

def main():
    dry = "--dry-run" in sys.argv
    locale = ""
    for i, a in enumerate(sys.argv):
        if a == "--locale" and i + 1 < len(sys.argv):
            locale = sys.argv[i + 1]
    en_tools_dir = os.path.join(ROOT, "tools")
    ans_dir = os.path.join(ROOT, locale, "answers") if locale else os.path.join(ROOT, "answers")
    heading = HEADINGS.get(locale, HEADINGS[""])
    # group tools by app id from the canonical EN /tools/ set
    by_app = {}
    tool_files = glob.glob(os.path.join(en_tools_dir, "*.html"))
    tool_files.sort(key=tool_sort_key)
    for f in tool_files:
        slug = os.path.basename(f)[:-5]
        if slug == "index":
            continue
        h = open(f, encoding="utf-8").read()
        a = appid(h)
        if not a:
            continue
        # link to locale tool if it exists, else EN; label from locale h1 if exists, else EN label
        loc_tool = os.path.join(ROOT, locale, "tools", f"{slug}.html") if locale else ""
        if locale and os.path.exists(loc_tool):
            url = f"{SITE}/{locale}/tools/{slug}.html"
            lbl = get_h1(open(loc_tool, encoding="utf-8").read()) or label(slug, get_h1(h), locale)
        else:
            url = f"{SITE}/tools/{slug}.html"
            # EN page: clean English (CJK-fallback). Locale page linking an EN-only tool:
            # use the EN h1 as-is (zhuyin tool titles are Traditional Chinese, right for zh pages).
            lbl = label(slug, get_h1(h), "") if not locale else (get_h1(h) or label(slug, None, locale))
        for related_app_id in related_app_ids(a, slug):
            by_app.setdefault(related_app_id, []).append((url, lbl))
    changed = 0
    total = 0
    for f in sorted(glob.glob(os.path.join(ans_dir, "*.html"))):
        slug = os.path.basename(f)[:-5]
        if slug == "index":
            continue
        total += 1
        h = open(f, encoding="utf-8").read()
        a = appid(h)
        if not a or a not in by_app:
            continue
        limit = related_tool_limit(by_app[a])
        tools = by_app[a][:limit]
        items = "".join(
            f'<li><a href="{url}">{html.escape(lbl)}</a></li>' for url, lbl in tools
        )
        section = f'<section class="wrap related-tools"><h2>{html.escape(heading)}</h2><ul>{items}</ul></section>'
        h2 = SEC_RE.sub("", h)  # idempotent
        # insert before related-answers section if present, else before </main>
        if '<section class="wrap related-answers">' in h2:
            h2 = h2.replace('<section class="wrap related-answers">', section + '<section class="wrap related-answers">', 1)
        elif "</main>" in h2:
            h2 = h2.replace("</main>", section + "</main>", 1)
        else:
            continue
        if h2 != h:
            changed += 1
            if dry and changed <= 3:
                print(f"[{slug}] app={a} -> tools: {[u.rsplit('/',1)[1] for u, _ in tools]}")
            if not dry:
                open(f, "w", encoding="utf-8").write(h2)
    print(f"{'DRY ' if dry else ''}locale={locale or 'en'} changed={changed} / {total} pages")

if __name__ == "__main__":
    main()
