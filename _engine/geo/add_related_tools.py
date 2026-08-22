#!/usr/bin/env python3
"""Add a "Free tools" section to answer pages, linking the same-app free tool(s).

Answer pages never linked to the site's free tools (e.g. Bopomofo answers -> Zhuyin
practice-sheet / flashcards / chart / bingo). This injects a localized "Free tools"
section (before the related-answers section) with links to same-app tools, driving
users to genuinely useful free utilities (which are link/share magnets) and adding
internal links. Idempotent; per-locale (same-locale tool pages + localized heading).
"""
import os, re, glob, html, sys
from pathlib import Path

from official_locales import OFFICIAL_LOCALES, require_official_locale_coverage

ROOT = os.environ.get(
    "GEO_PAGES",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages"),
)
SITE = "https://alice51849.github.io/ios-app-guide"
SEC_RE = re.compile(r'<section class="wrap related-tools">.*?</section>', re.S)
APP_ID_RE = re.compile(
    r'apps\.apple\.com/(?:[^/"\s]+/)?app/(?:[^/"\s]+/)?id(\d+)'
)
HEADINGS = {
    "ar-SA": "\u0623\u062f\u0648\u0627\u062a \u0645\u062c\u0627\u0646\u064a\u0629",
    "bn-BD": "\u09ac\u09bf\u09a8\u09be\u09ae\u09c2\u09b2\u09cd\u09af\u09c7\u09b0 \u099f\u09c1\u09b2",
    "ca": "Eines gratu\xeftes",
    "cs": "Bezplatn\xe9 n\xe1stroje",
    "da": "Gratis v\xe6rkt\xf8jer",
    "de-DE": "Kostenlose Tools",
    "el": "\u0394\u03c9\u03c1\u03b5\u03ac\u03bd \u03b5\u03c1\u03b3\u03b1\u03bb\u03b5\u03af\u03b1",
    "en-AU": "Free tools",
    "en-CA": "Free tools",
    "en-GB": "Free tools",
    "en-US": "Free tools",
    "es-ES": "Herramientas gratuitas",
    "es-MX": "Herramientas gratuitas",
    "fi": "Ilmaiset ty\xf6kalut",
    "fr-CA": "Outils gratuits",
    "fr-FR": "Outils gratuits",
    "gu-IN": "\u0aae\u0aab\u0aa4 \u0ab8\u0abe\u0aa7\u0aa8\u0acb",
    "he": "\u05db\u05dc\u05d9\u05dd \u05d7\u05d9\u05e0\u05de\u05d9\u05d9\u05dd",
    "hi": "\u092e\u0941\u092b\u093c\u094d\u0924 \u091f\u0942\u0932",
    "hr": "Besplatni alati",
    "hu": "Ingyenes eszk\xf6z\xf6k",
    "id": "Alat gratis",
    "it": "Strumenti gratuiti",
    "ja": "\u7121\u6599\u30c4\u30fc\u30eb",
    "kn-IN": "\u0c89\u0c9a\u0cbf\u0ca4 \u0caa\u0cb0\u0cbf\u0c95\u0cb0\u0c97\u0cb3\u0cc1",
    "ko": "\ubb34\ub8cc \ub3c4\uad6c",
    "ml-IN": "\u0d38\u0d57\u0d1c\u0d28\u0d4d\u0d2f \u0d09\u0d2a\u0d15\u0d30\u0d23\u0d19\u0d4d\u0d19\u0d7e",
    "mr-IN": "\u092e\u094b\u092b\u0924 \u0938\u093e\u0927\u0928\u0947",
    "ms": "Alat percuma",
    "nl-NL": "Gratis tools",
    "no": "Gratis verkt\xf8y",
    "or-IN": "\u0b2e\u0b3e\u0b17\u0b23\u0b3e \u0b09\u0b2a\u0b15\u0b30\u0b23",
    "pa-IN": "\u0a2e\u0a41\u0a2b\u0a3c\u0a24 \u0a1f\u0a42\u0a32",
    "pl": "Bezp\u0142atne narz\u0119dzia",
    "pt-BR": "Ferramentas gratuitas",
    "pt-PT": "Ferramentas gratuitas",
    "ro": "Instrumente gratuite",
    "ru": "\u0411\u0435\u0441\u043f\u043b\u0430\u0442\u043d\u044b\u0435 \u0438\u043d\u0441\u0442\u0440\u0443\u043c\u0435\u043d\u0442\u044b",
    "sk": "Bezplatn\xe9 n\xe1stroje",
    "sl-SI": "Brezpla\u010dna orodja",
    "sv": "Gratisverktyg",
    "ta-IN": "\u0b87\u0bb2\u0bb5\u0b9a\u0b95\u0bcd \u0b95\u0bb0\u0bc1\u0bb5\u0bbf\u0b95\u0bb3\u0bcd",
    "te-IN": "\u0c09\u0c1a\u0c3f\u0c24 \u0c38\u0c3e\u0c27\u0c28\u0c3e\u0c32\u0c41",
    "th": "\u0e40\u0e04\u0e23\u0e37\u0e48\u0e2d\u0e07\u0e21\u0e37\u0e2d\u0e1f\u0e23\u0e35",
    "tr": "\xdccretsiz ara\xe7lar",
    "uk": "\u0411\u0435\u0437\u043a\u043e\u0448\u0442\u043e\u0432\u043d\u0456 \u0456\u043d\u0441\u0442\u0440\u0443\u043c\u0435\u043d\u0442\u0438",
    "ur-PK": "\u0645\u0641\u062a \u0679\u0648\u0644\u0632",
    "vi": "C\xf4ng c\u1ee5 mi\u1ec5n ph\xed",
    "zh-Hans": "\u514d\u8d39\u5de5\u5177",
    "zh-Hant": "\u514d\u8cbb\u5de5\u5177",
}
require_official_locale_coverage("related-tools headings", HEADINGS)
BOPOMOFO_APP_IDS = ("6773017109", "6775773117")
BOPOMOFO_TOOL_PRIORITY = {
    "zhuyin-readiness-check.html": 0,
    "zhuyin-grade1-14-day-summer-calendar.html": 1,
    "zhuyin-blending-card-generator.html": 2,
    "zhuyin-short-sentence-reading-cards.html": 2.5,
    "zhuyin-decodable-mini-reader.html": 2.75,
    "zhuyin-story-sequencing-cards.html": 2.875,
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
    ids = appids(h)
    return ids[0] if ids else None


def appids(h):
    return tuple(dict.fromkeys(APP_ID_RE.findall(h)))

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

def load_canonical_tools():
    en_tools_dir = os.path.join(ROOT, "tools")
    tools = []
    tool_files = glob.glob(os.path.join(en_tools_dir, "*.html"))
    tool_files.sort(key=tool_sort_key)
    for path in tool_files:
        slug = os.path.basename(path)[:-5]
        if slug == "index":
            continue
        source = Path(path).read_text(encoding="utf-8")
        app_ids = appids(source)
        if app_ids:
            tools.append((slug, source, app_ids, get_h1(source)))
    return tools


def apply_locale(locale, canonical_tools, dry=False):
    ans_dir = os.path.join(ROOT, locale, "answers") if locale else os.path.join(ROOT, "answers")
    heading = HEADINGS[locale] if locale else "Free tools"
    # group tools by app id from the canonical EN /tools/ set
    by_app = {}
    for slug, source, app_ids, en_h1 in canonical_tools:
        # link to locale tool if it exists, else EN; label from locale h1 if exists, else EN label
        loc_tool = os.path.join(ROOT, locale, "tools", f"{slug}.html") if locale else ""
        if locale and os.path.exists(loc_tool):
            url = f"{SITE}/{locale}/tools/{slug}.html"
            lbl = get_h1(Path(loc_tool).read_text(encoding="utf-8")) or label(
                slug, en_h1, locale
            )
        else:
            url = f"{SITE}/tools/{slug}.html"
            # EN page: clean English (CJK-fallback). Locale page linking an EN-only tool:
            # use the EN h1 as-is (zhuyin tool titles are Traditional Chinese, right for zh pages).
            lbl = label(slug, en_h1, "") if not locale else (
                en_h1 or label(slug, None, locale)
            )
        for app_id in app_ids:
            for related_app_id in related_app_ids(app_id, slug):
                by_app.setdefault(related_app_id, []).append((url, lbl))
    changed = 0
    total = 0
    for f in sorted(glob.glob(os.path.join(ans_dir, "*.html"))):
        slug = os.path.basename(f)[:-5]
        if slug == "index":
            continue
        total += 1
        h = Path(f).read_text(encoding="utf-8")
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
                Path(f).write_text(h2, encoding="utf-8")
    print(f"{'DRY ' if dry else ''}locale={locale or 'en'} changed={changed} / {total} pages")
    return changed, total


def main():
    dry = "--dry-run" in sys.argv
    all_official = "--all-official-locales" in sys.argv
    locale = ""
    for i, a in enumerate(sys.argv):
        if a == "--locale" and i + 1 < len(sys.argv):
            locale = sys.argv[i + 1]
    locales = ["", *OFFICIAL_LOCALES] if all_official else [locale]
    canonical_tools = load_canonical_tools()
    for current_locale in locales:
        apply_locale(current_locale, canonical_tools, dry=dry)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
