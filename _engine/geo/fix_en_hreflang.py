#!/usr/bin/env python3
"""Fix EN answer-page hreflang reciprocity: EN pages hardcode only en+x-default,
so EN->locale hreflang is missing while locale pages point back to en (non-reciprocal).
For each EN answer page, rewrite its hreflang block to declare en + every EXISTING
locale version + x-default. Idempotent; only rewrites when the set changes.
Reuses aeo_answers_i18n.page_url/ALL_LANGS for exact URL format."""
import os, re, sys, glob
import aeo_answers_i18n as I

ROOT = I.ROOT  # pages dir
ANS = os.path.join(ROOT, "answers")
ALT_RE = re.compile(r'(?:<link rel="alternate" hreflang="[^"]+" href="[^"]+">\s*)+')

def existing_locales(slug: str):
    return [lc for lc in I.ALL_LANGS if os.path.exists(os.path.join(ROOT, lc, "answers", f"{slug}.html"))]

def build_block(slug: str, locales) -> str:
    lines = [f'<link rel="alternate" hreflang="en" href="{I.page_url(slug)}">']
    for lc in locales:
        lines.append(f'<link rel="alternate" hreflang="{lc}" href="{I.page_url(slug, lc)}">')
    lines.append(f'<link rel="alternate" hreflang="x-default" href="{I.page_url(slug)}">')
    return "\n".join(lines)

def main():
    dry = "--dry-run" in sys.argv
    changed = skipped = noloc = 0
    for f in sorted(glob.glob(os.path.join(ANS, "*.html"))):
        slug = os.path.basename(f)[:-5]
        if slug == "index":
            continue
        locales = existing_locales(slug)
        if not locales:
            noloc += 1
            continue
        h = open(f, encoding="utf-8").read()
        m = ALT_RE.search(h)
        if not m:
            continue
        new_block = build_block(slug, locales) + "\n"
        # count current alternates
        cur = m.group(0)
        cur_codes = re.findall(r'hreflang="([^"]+)"', cur)
        want_codes = ["en"] + locales + ["x-default"]
        if cur_codes == want_codes:
            skipped += 1
            continue
        if not dry:
            h2 = h[:m.start()] + new_block + h[m.end():]
            open(f, "w", encoding="utf-8").write(h2)
        changed += 1
        if dry and changed <= 3:
            print(f"[{slug}] {len(cur_codes)} -> {len(want_codes)} hreflang")
    print(f"{'DRY ' if dry else ''}changed={changed} already_ok={skipped} no_locale={noloc}")

if __name__ == "__main__":
    main()
