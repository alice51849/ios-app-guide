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
ALL_LANGS = ["de-DE", "es-ES", "fr-FR", "ja", "ko", "pt-BR", "zh-Hans", "zh-Hant",
             "it", "ru", "tr", "id", "vi", "th", "ar-SA", "hi", "nl-NL", "pl", "sv", "uk",
             "ca", "hr", "cs", "da", "fi", "el", "he", "hu", "ms", "no", "pt-PT", "ro",
             "sk", "es-MX", "bn-BD", "gu-IN", "kn-IN", "ml-IN", "mr-IN", "or-IN", "pa-IN",
             "sl-SI", "ta-IN", "te-IN", "ur-PK"]
HREFLANG_ORDER = ["en"] + [lc for lc in ALL_LANGS] + ["x-default"]
BASE_LANG = {
    "de-DE": "de-DE", "es-ES": "es-ES", "fr-FR": "fr-FR", "ja": "ja", "ko": "ko",
    "pt-BR": "pt-BR", "zh-Hans": "zh-Hans", "zh-Hant": "zh-Hant", "it": "it", "ru": "ru",
    "tr": "tr", "id": "id", "vi": "vi", "th": "th", "ar-SA": "ar", "hi": "hi", "nl-NL": "nl",
    "pl": "pl", "sv": "sv", "uk": "uk", "ca": "ca", "hr": "hr", "cs": "cs", "da": "da",
    "fi": "fi", "el": "el", "he": "he", "hu": "hu", "ms": "ms", "no": "no", "pt-PT": "pt-PT",
    "ro": "ro", "sk": "sk", "es-MX": "es-MX", "bn-BD": "bn", "gu-IN": "gu", "kn-IN": "kn",
    "ml-IN": "ml", "mr-IN": "mr", "or-IN": "or", "pa-IN": "pa", "sl-SI": "sl", "ta-IN": "ta",
    "te-IN": "te", "ur-PK": "ur",
}
LANG_NAMES = {
    "de-DE": "German for Germany", "es-ES": "Spanish for Spain", "fr-FR": "French for France",
    "ja": "Japanese", "ko": "Korean", "pt-BR": "Brazilian Portuguese", "zh-Hans": "Simplified Chinese",
    "zh-Hant": "Traditional Chinese", "it": "Italian", "ru": "Russian", "tr": "Turkish",
    "id": "Indonesian", "vi": "Vietnamese", "th": "Thai", "ar-SA": "Arabic", "hi": "Hindi",
    "nl-NL": "Dutch", "pl": "Polish", "sv": "Swedish", "uk": "Ukrainian", "ca": "Catalan",
    "hr": "Croatian", "cs": "Czech", "da": "Danish", "fi": "Finnish", "el": "Greek",
    "he": "Hebrew", "hu": "Hungarian", "ms": "Malay", "no": "Norwegian", "pt-PT": "European Portuguese",
    "ro": "Romanian", "sk": "Slovak", "es-MX": "Mexican Spanish", "bn-BD": "Bengali",
    "gu-IN": "Gujarati", "kn-IN": "Kannada", "ml-IN": "Malayalam", "mr-IN": "Marathi",
    "or-IN": "Odia", "pa-IN": "Punjabi", "sl-SI": "Slovenian", "ta-IN": "Tamil",
    "te-IN": "Telugu", "ur-PK": "Urdu",
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
    english = {p.name for p in ANSWERS.glob("*.html") if p.name != "index.html"}

    def missing_any_lang(name: str) -> bool:
        return any(not (ROOT / lang / "answers" / name).exists() for lang in ALL_LANGS)

    todo = sorted(n for n in english if missing_any_lang(n))
    aim = [x for x in todo if re.search(r"(toeic|990)", x)]
    other = [x for x in todo if x not in set(aim)]
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


RTL_LANGS = {"ar-SA", "he", "ur-PK", "fa"}


def finalize_html(source: str, lang: str, slug: str) -> str:
    dir_attr = ' dir="rtl"' if lang in RTL_LANGS else ""
    source = re.sub(r'<html\s+lang="[^"]+"(?:\s+dir="[^"]+")?',
                    f'<html lang="{BASE_LANG[lang]}"{dir_attr}', source, count=1)
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


def render_localized(source: str, lang: str, slug: str, mapping: dict[str, str]) -> str:
    strings, spans, json_spans = extract_strings(source)

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
    parser.add_argument("--dump", metavar="DIR", help="不翻譯,僅把每個 slug 的待譯字串輸出成 DIR/<slug>.json,供 agent 自行在地化(不用 OpenAI key)。")
    parser.add_argument("--trans", metavar="DIR", help="從全域 DIR/<lang>.json {原文:譯文}(agent 自產)組 mapping,免用 OpenAI key。字串全覆蓋才生成;缺漏寫到 DIR/_missing.<lang>.json 供補譯。")
    parser.add_argument("--allow-partial", action="store_true", help="搭配 --trans:即使有字串未譯也生成(未譯者維持原文)。預設關閉以免英文 fallback。")
    parser.add_argument("--openai", action="store_true", help="Explicitly opt in to OpenAI translation. Default requires --trans or --dump.")
    args = parser.parse_args()
    if args.openai and args.trans:
        parser.error("--openai and --trans are mutually exclusive")
    if not args.dump and not args.trans and not args.openai:
        parser.error("zero-cost default: use --trans DIR or --dump DIR (or explicitly pass --openai)")

    langs = parse_langs(args.langs)
    slugs = [Path(s).stem for s in args.slugs] if args.slugs else discover_slugs(args.limit)

    # --dump:輸出待譯字串(語言無關,strings 對所有語言相同),供 agent 自行翻譯。
    if args.dump:
        dump_dir = Path(args.dump)
        dump_dir.mkdir(parents=True, exist_ok=True)
        n = 0
        for slug in slugs:
            src_path = ANSWERS / f"{slug}.html"
            if not src_path.exists():
                print(f"missing source: {slug}", file=sys.stderr, flush=True)
                continue
            strings, _, _ = extract_strings(src_path.read_text(encoding="utf-8"))
            (dump_dir / f"{slug}.json").write_text(
                json.dumps({"slug": slug, "strings": strings}, ensure_ascii=False, indent=1),
                encoding="utf-8")
            n += 1
            print(f"dumped {slug} ({len(strings)} strings)", flush=True)
        print(json.dumps({"dumped": n}, ensure_ascii=False), flush=True)
        return 0

    api_key = read_key() if args.openai else ""
    created = skipped = failed = 0
    # --trans:每語言載入全域字典 + 累積缺漏(供 agent 下次補譯)。
    global_maps: dict[str, dict[str, str]] = {}
    missing_acc: dict[str, dict[str, int]] = {}
    if args.trans:
        for lang in langs:
            gp = Path(args.trans) / f"{lang}.json"
            global_maps[lang] = json.loads(gp.read_text(encoding="utf-8")) if gp.exists() else {}
            missing_acc[lang] = {}

    print("Slugs:", flush=True)
    for slug in slugs:
        print(f"  {slug}", flush=True)

    for slug in slugs:
        src_path = ANSWERS / f"{slug}.html"
        if not src_path.exists():
            print(f"missing source: {slug}", file=sys.stderr, flush=True)
            failed += len(langs)
            continue
        source = src_path.read_text(encoding="utf-8")
        for lang in langs:
            target = ROOT / lang / "answers" / f"{slug}.html"
            if target.exists():
                skipped += 1
                print(f"skip existing {lang}/{slug}.html", flush=True)
                continue
            try:
                if args.trans:
                    strings, _, _ = extract_strings(source)
                    gm = global_maps[lang]
                    mapping = {s: gm[s] for s in strings if s in gm}
                    miss = [s for s in strings if s not in gm]
                    if miss and not args.allow_partial:
                        for s in miss:
                            missing_acc[lang][s] = missing_acc[lang].get(s, 0) + 1
                        skipped += 1
                        print(f"incomplete {lang}/{slug}.html — 缺 {len(miss)} 字串,略過", flush=True)
                        continue
                else:
                    strings, _, _ = extract_strings(source)
                    mapping = call_openai(strings, lang, slug, api_key)
                localized = render_localized(source, lang, slug, mapping)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(localized, encoding="utf-8")
                created += 1
                print(f"created {lang}/{slug}.html", flush=True)
            except Exception as exc:
                failed += 1
                print(f"failed {lang}/{slug}.html: {exc}", file=sys.stderr, flush=True)
                continue

    # 寫出各語言累積缺漏(依出現頁數排序,優先補高頻共用字串)。
    if args.trans:
        for lang, miss in missing_acc.items():
            if not miss:
                continue
            ordered = dict(sorted(miss.items(), key=lambda kv: -kv[1]))
            (Path(args.trans) / f"_missing.{lang}.json").write_text(
                json.dumps(ordered, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"[{lang}] 待補譯字串 {len(ordered)} → _missing.{lang}.json", flush=True)

    print(json.dumps({"created": created, "skipped": skipped, "failed": failed}, ensure_ascii=False), flush=True)
    # 產生新 i18n 頁後自動刷新答案 sitemap(涵蓋所有 */answers/*.html),避免漏索引。
    if created:
        try:
            import aeo_answers  # noqa
            aeo_answers.write_sitemap()
        except Exception as exc:
            print(f"sitemap refresh skipped: {exc}", file=sys.stderr, flush=True)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
