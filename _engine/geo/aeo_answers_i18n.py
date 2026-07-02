#!/usr/bin/env python3
"""Localize AEO/GEO answer pages without touching git."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent / "pages"
ANSWERS = ROOT / "answers"
BASE_URL = "https://alice51849.github.io/ios-app-guide"
ALL_LANGS = ["de-DE", "es-ES", "fr-FR", "ja", "ko", "pt-BR", "zh-Hans", "zh-Hant"]
HREFLANG_ORDER = ["en", "es-ES", "pt-BR", "de-DE", "fr-FR", "ja", "ko", "zh-Hant", "zh-Hans", "x-default"]
BASE_LANG = {
    "de-DE": "de-DE",
    "es-ES": "es-ES",
    "fr-FR": "fr-FR",
    "ja": "ja",
    "ko": "ko",
    "pt-BR": "pt-BR",
    "zh-Hans": "zh-Hans",
    "zh-Hant": "zh-Hant",
}
LANG_NAMES = {
    "de-DE": "German for Germany",
    "es-ES": "Spanish for Spain",
    "fr-FR": "French for France",
    "ja": "Japanese",
    "ko": "Korean",
    "pt-BR": "Brazilian Portuguese",
    "zh-Hans": "Simplified Chinese",
    "zh-Hant": "Traditional Chinese",
}
BRANDS = [
    "Aim990",
    "TOEIC",
    "TOEIC L&R",
    "ETS",
    "App Store",
    "iPhone",
    "iOS",
    "ScanTo Pro",
]
NO_TRANSLATE_JSON_KEYS = {
    "@context",
    "@type",
    "@id",
    "url",
    "installUrl",
    "item",
    "operatingSystem",
    "applicationCategory",
    "price",
    "priceCurrency",
}


def read_key() -> str:
    key_path = Path.home() / ".openai_key"
    return key_path.read_text(encoding="utf-8").strip()


def page_url(slug: str, lang: str | None = None) -> str:
    if lang:
        return f"{BASE_URL}/{lang}/answers/{slug}.html"
    return f"{BASE_URL}/answers/{slug}.html"


def localize_url(url: str, lang: str) -> str:
    if not url.startswith(BASE_URL + "/"):
        return url
    suffix = url[len(BASE_URL) + 1 :]
    if suffix.startswith(tuple(x + "/" for x in ALL_LANGS)):
        return url
    if suffix.startswith("#"):
        return url
    return f"{BASE_URL}/{lang}/{suffix}"


def discover_slugs(limit: int | None = None) -> list[str]:
    english = {p.name for p in ANSWERS.glob("*.html")}
    es = {p.name for p in (ROOT / "es-ES" / "answers").glob("*.html")}
    new_files = sorted(english - es)
    aim = [x for x in new_files if re.search(r"(toeic|990)", x)]
    other = [x for x in new_files if x not in set(aim)]
    ordered = [Path(x).stem for x in aim + other]
    return ordered[:limit] if limit else ordered


def parse_langs(raw: str | None) -> list[str]:
    if not raw:
        return ALL_LANGS
    langs = [x.strip() for x in raw.replace(",", " ").split() if x.strip()]
    bad = [x for x in langs if x not in ALL_LANGS]
    if bad:
        raise SystemExit(f"Unsupported --langs values: {', '.join(bad)}")
    return langs


def should_translate_json(key: str | None, value: str) -> bool:
    if not value.strip():
        return False
    if key in NO_TRANSLATE_JSON_KEYS:
        return False
    if value.startswith(("http://", "https://", "#")):
        return False
    if value in {"USD", "0", "iOS", "BusinessApplication", "EducationalApplication", "ProductivityApplication"}:
        return False
    return True


def collect_json_strings(obj: Any, out: list[str], key: str | None = None) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            collect_json_strings(v, out, k)
    elif isinstance(obj, list):
        for v in obj:
            collect_json_strings(v, out, key)
    elif isinstance(obj, str) and should_translate_json(key, obj):
        out.append(obj)


def apply_json_mapping(obj: Any, mapping: dict[str, str], key: str | None = None) -> Any:
    if isinstance(obj, dict):
        return {k: apply_json_mapping(v, mapping, k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [apply_json_mapping(v, mapping, key) for v in obj]
    if isinstance(obj, str) and should_translate_json(key, obj):
        return mapping.get(obj, obj)
    return obj


def update_breadcrumb_urls(obj: Any, lang: str, slug: str) -> Any:
    if isinstance(obj, dict):
        if obj.get("@type") == "BreadcrumbList":
            for item in obj.get("itemListElement", []):
                if isinstance(item, dict) and isinstance(item.get("item"), str):
                    item["item"] = localize_url(item["item"], lang)
            return obj
        if obj.get("@type") == "ListItem" and isinstance(obj.get("item"), str):
            obj["item"] = localize_url(obj["item"], lang)
        for v in obj.values():
            update_breadcrumb_urls(v, lang, slug)
    elif isinstance(obj, list):
        for v in obj:
            update_breadcrumb_urls(v, lang, slug)
    return obj


def extract_strings(source: str) -> tuple[list[str], list[tuple[int, int, str, str]], list[tuple[int, int, str]]]:
    strings: list[str] = []
    attr_spans: list[tuple[int, int, str, str]] = []
    json_spans: list[tuple[int, int, str]] = []

    script_style_ranges: list[tuple[int, int]] = []
    for m in re.finditer(r"<(script|style)\b[^>]*>.*?</\1>", source, flags=re.I | re.S):
        script_style_ranges.append((m.start(), m.end()))
        if re.search(r"<script\b[^>]*application/ld\+json", m.group(0), flags=re.I):
            open_end = source.find(">", m.start()) + 1
            close_start = source.rfind("</script>", m.start(), m.end())
            raw = source[open_end:close_start].strip()
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            collect_json_strings(obj, strings)
            json_spans.append((open_end, close_start, raw))

    def in_block(pos: int) -> bool:
        return any(start <= pos < end for start, end in script_style_ranges)

    for m in re.finditer(r"<meta\b[^>]*(?:name|property)=[\"'](?:description|og:title|og:description)[\"'][^>]*>", source, flags=re.I):
        if in_block(m.start()):
            continue
        tag = m.group(0)
        cm = re.search(r"content=(['\"])(.*?)\1", tag, flags=re.I | re.S)
        if cm and cm.group(2).strip():
            start = m.start() + cm.start(2)
            end = m.start() + cm.end(2)
            text = html.unescape(cm.group(2))
            strings.append(text)
            attr_spans.append((start, end, text, "content"))

    text_spans: list[tuple[int, int, str, str]] = []
    pos = 0
    for m in re.finditer(r"<[^>]+>", source):
        if m.start() > pos and not in_block(pos):
            raw = source[pos : m.start()]
            if raw.strip():
                text = html.unescape(raw)
                if text.strip():
                    strings.append(text.strip())
                    text_spans.append((pos, m.start(), text.strip(), "text"))
        pos = m.end()
    if pos < len(source) and not in_block(pos):
        raw = source[pos:]
        if raw.strip():
            text = html.unescape(raw)
            strings.append(text.strip())
            text_spans.append((pos, len(source), text.strip(), "text"))

    spans = attr_spans + text_spans
    unique = list(dict.fromkeys(s for s in strings if s.strip()))
    return unique, spans, json_spans


def call_openai(strings: list[str], lang: str, slug: str, api_key: str) -> dict[str, str]:
    if not strings:
        return {}
    prompt = {
        "target_locale": lang,
        "target_language": LANG_NAMES[lang],
        "slug": slug,
        "strings": strings,
    }
    system = (
        "You localize external promotional iOS answer pages for AEO/GEO. "
        "Return strict JSON with one object key 'translations' mapping every source string exactly to a native translation. "
        "Preserve HTML entities conceptually but output plain Unicode text. Preserve brand names and URLs. "
        f"Do not translate these brand/platform names: {', '.join(BRANDS)}. "
        "For Aim990/TOEIC content: never claim 'no subscription'; Aim990 has both a one-time unlock option and subscription plans. "
        "Never promise or guarantee a TOEIC score or improvement. Keep the disclaimer that Aim990 is an independent study aid, "
        "is not affiliated with or endorsed by ETS, and TOEIC is a trademark of ETS. "
        "Do not fabricate ratings, downloads, awards, or claims."
    )
    payload = {
        "model": "gpt-4o-mini",
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        "temperature": 0.2,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=data,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                raw = resp.read().decode("utf-8")
            content = json.loads(raw)["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            translations = parsed.get("translations", {})
            if not isinstance(translations, dict):
                raise ValueError("translations is not an object")
            return {str(k): str(v) for k, v in translations.items()}
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as exc:
            last_error = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"OpenAI translation failed for {slug} {lang}: {last_error}")


def replace_spans(source: str, replacements: list[tuple[int, int, str]]) -> str:
    out = []
    last = 0
    for start, end, repl in sorted(replacements, key=lambda x: x[0]):
        out.append(source[last:start])
        out.append(repl)
        last = end
    out.append(source[last:])
    return "".join(out)


def alternates_html(slug: str) -> str:
    lines = []
    for code in HREFLANG_ORDER:
        if code == "en" or code == "x-default":
            href = page_url(slug)
        else:
            href = page_url(slug, code)
        lines.append(f'<link rel="alternate" hreflang="{code}" href="{href}">')
    return "\n".join(lines)


def localize_body_links(source: str, lang: str) -> str:
    def repl(m: re.Match[str]) -> str:
        return f'{m.group(1)}{localize_url(m.group(2), lang)}{m.group(3)}'

    return re.sub(r'(<a\b[^>]*\bhref=")(https://alice51849\.github\.io/ios-app-guide/[^"]+)(")', repl, source)


def finalize_html(source: str, lang: str, slug: str) -> str:
    source = re.sub(r'<html\s+lang="[^"]+"', f'<html lang="{BASE_LANG[lang]}"', source, count=1)
    source = re.sub(
        r'<link rel="canonical" href="[^"]+">',
        f'<link rel="canonical" href="{page_url(slug, lang)}">',
        source,
        count=1,
    )
    source = re.sub(
        r'(<link rel="alternate" hreflang="[^"]+" href="[^"]+">\s*)+',
        alternates_html(slug) + "\n",
        source,
        count=1,
    )
    source = re.sub(
        r'(<meta property="og:url" content=")[^"]+(")',
        rf'\1{page_url(slug, lang)}\2',
        source,
        count=1,
    )
    return localize_body_links(source, lang)


def render_localized(source: str, lang: str, slug: str, api_key: str) -> str:
    strings, spans, json_spans = extract_strings(source)
    mapping = call_openai(strings, lang, slug, api_key)

    replacements: list[tuple[int, int, str]] = []
    for start, end, original, kind in spans:
        translated = mapping.get(original, original)
        escaped = html.escape(translated, quote=(kind == "content"))
        if kind == "text":
            raw = source[start:end]
            leading = re.match(r"\s*", raw).group(0)
            trailing = re.search(r"\s*$", raw).group(0)
            escaped = f"{leading}{escaped}{trailing}"
        replacements.append((start, end, escaped))

    for start, end, raw in json_spans:
        obj = json.loads(raw)
        obj = apply_json_mapping(obj, mapping)
        obj = update_breadcrumb_urls(obj, lang, slug)
        replacements.append((start, end, "\n" + json.dumps(obj, ensure_ascii=False, indent=2) + "\n"))

    localized = replace_spans(source, replacements)
    return finalize_html(localized, lang, slug)


def main() -> int:
    parser = argparse.ArgumentParser(description="Localize new AEO/GEO answer pages. Writes HTML only; never uses git.")
    parser.add_argument("slugs", nargs="*", help="Optional answer slugs, with or without .html")
    parser.add_argument("--langs", help="Locales to generate (comma or space separated)")
    parser.add_argument("--limit", type=int, help="Limit number of discovered slugs when no positional slugs are provided")
    args = parser.parse_args()

    langs = parse_langs(args.langs)
    slugs = [Path(s).stem for s in args.slugs] if args.slugs else discover_slugs(args.limit)
    api_key = read_key()
    created = skipped = failed = 0

    print("Slugs:")
    for slug in slugs:
        print(f"  {slug}")

    for slug in slugs:
        src_path = ANSWERS / f"{slug}.html"
        if not src_path.exists():
            print(f"missing source: {slug}", file=sys.stderr)
            failed += len(langs)
            continue
        source = src_path.read_text(encoding="utf-8")
        for lang in langs:
            target = ROOT / lang / "answers" / f"{slug}.html"
            if target.exists():
                skipped += 1
                print(f"skip existing {lang}/{slug}.html")
                continue
            try:
                localized = render_localized(source, lang, slug, api_key)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(localized, encoding="utf-8")
                created += 1
                print(f"created {lang}/{slug}.html")
            except Exception as exc:
                failed += 1
                print(f"failed {lang}/{slug}.html: {exc}", file=sys.stderr)
                continue

    print(json.dumps({"created": created, "skipped": skipped, "failed": failed}, ensure_ascii=False))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
