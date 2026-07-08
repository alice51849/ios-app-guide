#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Open-data hub 生成器(新免費管道)— 把「可被 AI 引擎/Google Dataset Search 引用」的
機器可讀事實資料集發佈到 /data/。

GEO 下一層槓桿:除了 answer/guide/alternatives 這些「文章型」內容外,再提供
**結構化開放資料集**(JSON + schema.org/Dataset + DefinedTermSet)。AI 助理與
Google Dataset Search 特別偏好引用「乾淨、可機讀、標明授權與來源」的事實資料;
每個資料集都連回對應的 pay-once app,形成 data → citation → app 的漏斗。

首發:注音(Zhuyin/Bopomofo)37 符號完整資料集 — 綁營收第一的 Lumi Bopomofo。
CC-BY-4.0 授權(要求標註來源=最自然的反向連結/品牌曝光)。100% 自動、零成本、
無帳號、不碰 app code、不碰 App Store metadata。

    python geo/gen_data_hub.py            # 產檔(不部署)
    python geo/gen_data_hub.py --publish  # 並 git push + IndexNow
"""
import argparse
import datetime as _dt
import html
import json
import os
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(HERE, "pages")
DATA = os.path.join(PAGES, "data")
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide").rstrip("/")
TODAY = _dt.date.today().isoformat()

BOPOMOFO_APP = "https://apps.apple.com/app/id6773017109"      # Lumi Bopomofo
BOPOMOFO_PRO = "https://apps.apple.com/app/id6775773117"      # Lumi Bopomofo Pro
SNAPPORT_APP = "https://apps.apple.com/app/id6780575828"      # Snapport: Passport & ID Photos
CVDESK_APP = "https://apps.apple.com/app/id6781337213"        # CV Desk: ATS Resume Builder
GMONEY_APP = "https://apps.apple.com/app/id6755782939"        # G+Money: currency + expense

# ── 37 注音符號(21 聲母 + 3 介音 + 13 韻母)。pinyin 為漢語拼音對照,example 為常用字例。
ZHUYIN = [
    # initials (21)
    ("ㄅ", "b", "initial", "爸", "bà", "father"),
    ("ㄆ", "p", "initial", "怕", "pà", "afraid"),
    ("ㄇ", "m", "initial", "媽", "mā", "mother"),
    ("ㄈ", "f", "initial", "飛", "fēi", "to fly"),
    ("ㄉ", "d", "initial", "大", "dà", "big"),
    ("ㄊ", "t", "initial", "天", "tiān", "sky"),
    ("ㄋ", "n", "initial", "你", "nǐ", "you"),
    ("ㄌ", "l", "initial", "來", "lái", "to come"),
    ("ㄍ", "g", "initial", "狗", "gǒu", "dog"),
    ("ㄎ", "k", "initial", "看", "kàn", "to look"),
    ("ㄏ", "h", "initial", "好", "hǎo", "good"),
    ("ㄐ", "j", "initial", "家", "jiā", "home"),
    ("ㄑ", "q", "initial", "去", "qù", "to go"),
    ("ㄒ", "x", "initial", "小", "xiǎo", "small"),
    ("ㄓ", "zh", "initial", "中", "zhōng", "middle"),
    ("ㄔ", "ch", "initial", "吃", "chī", "to eat"),
    ("ㄕ", "sh", "initial", "是", "shì", "to be"),
    ("ㄖ", "r", "initial", "人", "rén", "person"),
    ("ㄗ", "z", "initial", "早", "zǎo", "early"),
    ("ㄘ", "c", "initial", "菜", "cài", "vegetable"),
    ("ㄙ", "s", "initial", "三", "sān", "three"),
    # medials / glides (3)
    ("ㄧ", "i / yi", "medial", "一", "yī", "one"),
    ("ㄨ", "u / wu", "medial", "五", "wǔ", "five"),
    ("ㄩ", "ü / yu", "medial", "魚", "yú", "fish"),
    # finals / vowels (13)
    ("ㄚ", "a", "final", "大", "dà", "big"),
    ("ㄛ", "o", "final", "波", "bō", "wave"),
    ("ㄜ", "e", "final", "喝", "hē", "to drink"),
    ("ㄝ", "ê", "final", "誒", "ê", "hey (interjection)"),
    ("ㄞ", "ai", "final", "愛", "ài", "love"),
    ("ㄟ", "ei", "final", "給", "gěi", "to give"),
    ("ㄠ", "ao", "final", "好", "hǎo", "good"),
    ("ㄡ", "ou", "final", "有", "yǒu", "to have"),
    ("ㄢ", "an", "final", "安", "ān", "peace"),
    ("ㄣ", "en", "final", "恩", "ēn", "grace"),
    ("ㄤ", "ang", "final", "忙", "máng", "busy"),
    ("ㄥ", "eng", "final", "冷", "lěng", "cold"),
    ("ㄦ", "er", "final", "二", "èr", "two"),
]
CAT_LABEL = {"initial": "Initials (consonants)", "medial": "Medials (glides)",
             "final": "Finals (vowels)"}


def zhuyin_records():
    out = []
    for sym, py, cat, ch, chpy, gloss in ZHUYIN:
        out.append({
            "symbol": sym,
            "unicode": "U+%04X" % ord(sym),
            "pinyin": py,
            "category": cat,
            "example": {"character": ch, "pinyin": chpy, "meaning": gloss},
        })
    return out


def zhuyin_json():
    recs = zhuyin_records()
    return {
        "name": "Zhuyin (Bopomofo) — 37 phonetic symbols",
        "description": ("The complete set of 37 Zhuyin Fuhao (Bopomofo) symbols used to teach "
                        "Mandarin pronunciation in Taiwan: 21 initials (consonants), 3 medials "
                        "(glides) and 13 finals (vowels), each with its Hanyu Pinyin equivalent, "
                        "Unicode code point and a common example word."),
        "identifier": f"{SITE}/data/zhuyin-bopomofo.json",
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "creator": "Lumi Apps",
        "isBasedOn": "https://en.wikipedia.org/wiki/Bopomofo",
        "relatedApp": BOPOMOFO_APP,
        "dateModified": TODAY,
        "counts": {"initials": 21, "medials": 3, "finals": 13, "total": 37},
        "symbols": recs,
    }


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="canonical" href="{site}/data/{slug}.html">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:type" content="website">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--ink:#1d2433;--sub:#5b6577;--line:#e7ebf2;--brand:#5b4bdb;--bg:#f7f8fb}}
*{{box-sizing:border-box}}
body{{margin:0;font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,"PingFang TC","Microsoft JhengHei",sans-serif;color:var(--ink);background:var(--bg)}}
.wrap{{max-width:860px;margin:0 auto;padding:28px 20px 64px}}
a{{color:var(--brand)}}
h1{{font-size:clamp(24px,5vw,34px);line-height:1.25;margin:.2em 0 .1em}}
.lead{{color:var(--sub);font-size:clamp(15px,3.4vw,18px);margin:.4em 0 1.2em}}
.crumb{{font-size:13px;color:var(--sub);margin-bottom:6px}}
.meta{{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 20px}}
.pill{{background:#fff;border:1px solid var(--line);border-radius:999px;padding:5px 12px;font-size:13px;color:var(--sub);white-space:nowrap}}
.card{{background:#fff;border:1px solid var(--line);border-radius:16px;padding:18px 18px 6px;margin:0 0 22px}}
h2{{font-size:20px;margin:20px 0 10px}}
table{{width:100%;border-collapse:collapse;font-size:15px}}
th,td{{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:middle}}
th{{color:var(--sub);font-weight:600;font-size:13px;text-transform:uppercase;letter-spacing:.03em}}
.sym{{font-size:26px;line-height:1;white-space:nowrap}}
.py{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;white-space:nowrap}}
.ex{{white-space:nowrap}}
.nw{{white-space:nowrap}}
.cta{{display:block;background:linear-gradient(135deg,#6a5be6,#5b4bdb);color:#fff;text-decoration:none;border-radius:14px;padding:16px 18px;font-weight:600;text-align:center;margin:8px 0 6px}}
.dl{{display:inline-block;border:1px solid var(--line);background:#fff;border-radius:12px;padding:10px 14px;text-decoration:none;font-weight:600;font-size:14px}}
.foot{{color:var(--sub);font-size:13px;margin-top:26px}}
.related{{background:#fff;border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin:18px 0 0}}
.related h2{{font-size:16px;margin:0 0 8px}}
.related a{{display:inline-block;margin:0 14px 6px 0;font-size:14px;font-weight:600}}
</style>
</head>
<body>
<div class="wrap">
<div class="crumb"><a href="{site}/data/">Open data</a> › {crumb}</div>
<h1>{h1}</h1>
<p class="lead">{lead}</p>
<div class="meta">
{pills}<span class="pill">CC-BY 4.0 — free to reuse with credit</span><span class="pill">Updated {today}</span>
</div>
<a class="dl" href="{site}/data/{slug}.json">⬇ Download JSON dataset</a>
{tables}
{cta}
{related}
<p class="foot">Data licensed under
<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>. You may reuse it freely —
please credit “Lumi Apps ({site})”. Machine-readable copy:
<a href="{site}/data/{slug}.json">{slug}.json</a>.</p>
</div>
</body>
</html>
"""


def related_block(links):
    if not links:
        return ""
    items = "".join(f'<a href="{SITE}/{p}">{html.escape(label)} →</a>' for label, p in links)
    return f'<div class="related"><h2>Related guides &amp; tools</h2>{items}</div>'


def _rows(cat):
    r = []
    for sym, py, c, ch, chpy, gloss in ZHUYIN:
        if c != cat:
            continue
        r.append(f'<tr><td class="sym">{sym}</td><td class="py">{html.escape(py)}</td>'
                 f'<td class="ex">{ch} <span class="py">{chpy}</span> — {html.escape(gloss)}</td></tr>')
    return "\n".join(r)


def build_zhuyin_page():
    slug = "zhuyin-bopomofo"
    title = "Zhuyin (Bopomofo) Chart — All 37 Symbols with Pinyin | Open Data"
    h1 = "Zhuyin (Bopomofo): all 37 symbols"
    desc = ("The complete list of the 37 Zhuyin (Bopomofo) symbols — 21 initials, 3 medials and "
            "13 finals — each with its Pinyin equivalent, Unicode point and an example word. "
            "Free, machine-readable open data (CC BY 4.0).")
    lead = ("Bopomofo (注音符號) is the phonetic system used to teach Mandarin pronunciation in "
            "Taiwan. Here is the full, citable reference — 37 symbols mapped to Hanyu Pinyin.")
    tables = ""
    for cat in ("initial", "medial", "final"):
        tables += (f'<div class="card"><h2>{CAT_LABEL[cat]}</h2><table>'
                   f'<tr><th>Symbol</th><th>Pinyin</th><th>Example</th></tr>'
                   f'{_rows(cat)}</table></div>')
    dj = zhuyin_json()
    terms = [{
        "@type": "DefinedTerm", "name": r["symbol"],
        "description": f'Pinyin {r["pinyin"]}; example {r["example"]["character"]} '
                       f'({r["example"]["pinyin"]}) — {r["example"]["meaning"]}',
        "inDefinedTermSet": f"{SITE}/data/{slug}.html",
    } for r in dj["symbols"]]
    schema = json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "Dataset", "name": dj["name"], "description": dj["description"],
             "url": f"{SITE}/data/{slug}.html", "identifier": dj["identifier"],
             "license": dj["license"], "creator": {"@type": "Organization", "name": "Lumi Apps"},
             "isBasedOn": dj["isBasedOn"], "dateModified": dj["dateModified"],
             "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json",
                               "contentUrl": dj["identifier"]}],
             "keywords": ["Bopomofo", "Zhuyin", "注音符號", "Mandarin", "Pinyin", "phonetics"]},
            {"@type": "DefinedTermSet", "name": "Zhuyin (Bopomofo) symbols",
             "url": f"{SITE}/data/{slug}.html", "hasDefinedTerm": terms},
        ],
    }, ensure_ascii=False)
    pills = ('<span class="pill">37 symbols</span>'
             '<span class="pill">21 initials · 3 medials · 13 finals</span>')
    cta = ('<h2>Learn these with a game — pay once, no subscription</h2>\n'
           '<p>The fastest way for a child to master all 37 symbols is playful, repeated practice. '
           '<strong>Lumi Bopomofo</strong> teaches every symbol above through games — a one-time '
           'purchase, no ads, no subscription, everything stays on the device.</p>\n'
           f'<a class="cta" href="{BOPOMOFO_APP}">Get Lumi Bopomofo on the App Store →</a>\n'
           f'<p style="font-size:14px"><a href="{SITE}/tools/zhuyin-bopomofo-chart.html">'
           'Printable Bopomofo chart →</a> &nbsp;·&nbsp; '
           f'<a href="{SITE}/data/">More open datasets →</a></p>')
    page = PAGE.format(title=html.escape(title), desc=html.escape(desc), h1=html.escape(h1),
                       lead=html.escape(lead), site=SITE, slug=slug, today=TODAY,
                       crumb="Zhuyin (Bopomofo)", pills=pills, tables=tables, schema=schema, cta=cta,
                       related=related_block([
                           ("Kids learning apps", "kids-learning.html"),
                           ("Printable Bopomofo chart", "tools/zhuyin-bopomofo-chart.html"),
                           ("Lumi Bopomofo guide", "guides/lumibopomofo.html")]))
    os.makedirs(DATA, exist_ok=True)
    open(os.path.join(DATA, f"{slug}.json"), "w", encoding="utf-8").write(
        json.dumps(dj, ensure_ascii=False, indent=2))
    open(os.path.join(DATA, f"{slug}.html"), "w", encoding="utf-8").write(page)
    return slug


PASSPORT = [
    # (country, ISO code, width_mm, height_mm, size_label, head_min_mm, head_max_mm, background)
    ("United States", "US", 51, 51, "51 × 51 mm (2 × 2 in)", 25, 35, "white"),
    ("United Kingdom", "GB", 35, 45, "35 × 45 mm", 29, 34, "light grey / cream"),
    ("Canada", "CA", 50, 70, "50 × 70 mm", 31, 36, "white"),
    ("Australia", "AU", 35, 45, "35–40 × 45–50 mm (35 × 45 accepted)", 32, 36, "white"),
    ("India", "IN", 35, 45, "35 × 45 mm", 25, 35, "white"),
    ("China", "CN", 33, 48, "33 × 48 mm", 28, 33, "white"),
    ("Japan", "JP", 35, 45, "35 × 45 mm", 32, 36, "white"),
    ("Schengen / EU", "EU", 35, 45, "35 × 45 mm", 32, 36, "light grey"),
    ("Germany", "DE", 35, 45, "35 × 45 mm", 32, 36, "light grey"),
    ("France", "FR", 35, 45, "35 × 45 mm", 32, 36, "light grey"),
    ("Taiwan", "TW", 35, 45, "35 × 45 mm", 32, 36, "white"),
    ("South Korea", "KR", 35, 45, "35 × 45 mm", 32, 36, "white"),
    ("Brazil", "BR", 35, 45, "35 × 45 mm", 32, 36, "white"),
]


def passport_records():
    out = []
    for c, code, w, h, label, hmin, hmax, bg in PASSPORT:
        out.append({
            "country": c, "countryCode": code,
            "width_mm": w, "height_mm": h, "size_label": label,
            "head_height_mm": {"min": hmin, "max": hmax}, "background": bg,
        })
    return out


def passport_json():
    return {
        "name": "Passport & ID photo size requirements by country",
        "description": ("Official passport / ID photo dimensions (width × height in millimetres), "
                        "required head height and background colour for major countries, for "
                        "checking and cropping compliant photos."),
        "identifier": f"{SITE}/data/passport-photo-sizes.json",
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "creator": "Lumi Apps",
        "dateModified": TODAY,
        "disclaimer": ("Requirements change; always confirm with the issuing authority before "
                       "submitting. Ranges reflect commonly accepted specifications."),
        "countries": passport_records(),
    }


def build_passport_page():
    slug = "passport-photo-sizes"
    title = "Passport Photo Size by Country (mm) — Free Open Data | Lumi Apps"
    h1 = "Passport & ID photo sizes by country"
    desc = ("Official passport / ID photo dimensions in millimetres, head-height requirement and "
            "background colour for major countries. Free, machine-readable open data (CC BY 4.0).")
    lead = ("How big should a passport photo be? Here is a citable reference of official photo "
            "sizes (in mm), head-height requirements and background colour by country.")
    rows = ""
    for c, code, w, h, label, hmin, hmax, bg in PASSPORT:
        rows += (f'<tr><td><strong>{html.escape(c)}</strong></td>'
                 f'<td class="nw">{html.escape(label)}</td>'
                 f'<td class="nw">{hmin}–{hmax} mm</td>'
                 f'<td>{html.escape(bg)}</td></tr>')
    tables = ('<div class="card"><table>'
              '<tr><th>Country</th><th>Photo size</th><th>Head height</th><th>Background</th></tr>'
              f'{rows}</table></div>')
    dj = passport_json()
    schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "Dataset", "name": dj["name"], "description": dj["description"],
        "url": f"{SITE}/data/{slug}.html", "identifier": dj["identifier"],
        "license": dj["license"], "creator": {"@type": "Organization", "name": "Lumi Apps"},
        "dateModified": dj["dateModified"],
        "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json",
                          "contentUrl": dj["identifier"]}],
        "keywords": ["passport photo size", "ID photo", "photo dimensions", "mm", "by country"],
    }, ensure_ascii=False)
    pills = (f'<span class="pill">{len(PASSPORT)} countries</span>'
             '<span class="pill">sizes in mm</span>')
    cta = ('<h2>Make a compliant photo at home — pay once, no subscription</h2>\n'
           '<p>You don’t need a photo booth. <strong>Snapport</strong> crops your photo to the exact '
           'size for any country above, checks the head position and prints or exports a ready-to-use '
           'sheet — a one-time purchase, no subscription, everything on your iPhone.</p>\n'
           f'<a class="cta" href="{SNAPPORT_APP}">Get Snapport on the App Store →</a>\n'
           f'<p style="font-size:14px"><a href="{SITE}/data/">More open datasets →</a></p>')
    page = PAGE.format(title=html.escape(title), desc=html.escape(desc), h1=html.escape(h1),
                       lead=html.escape(lead), site=SITE, slug=slug, today=TODAY,
                       crumb="Passport photo sizes", pills=pills, tables=tables,
                       schema=schema, cta=cta,
                       related=related_block([
                           ("Passport photos by country", "passport-photos.html"),
                           ("Passport photo size guide", "tools/passport-photo-size-guide.html"),
                           ("Snapport guide", "guides/snapport.html")]))
    os.makedirs(DATA, exist_ok=True)
    open(os.path.join(DATA, f"{slug}.json"), "w", encoding="utf-8").write(
        json.dumps(dj, ensure_ascii=False, indent=2))
    open(os.path.join(DATA, f"{slug}.html"), "w", encoding="utf-8").write(page)
    return slug


# ── Chinese script + Mandarin phonetic system by region (ties to Lumi Bopomofo) ──
CN_REGIONS = [
    # (region, code, script, phonetic, notes)
    ("Taiwan", "TW", "Traditional", "Zhuyin (Bopomofo)",
     "Children learn Zhuyin (注音) first to read; Hanyu Pinyin is taught later as secondary."),
    ("Mainland China", "CN", "Simplified", "Hanyu Pinyin",
     "Hanyu Pinyin is universal in education, dictionaries and input methods."),
    ("Hong Kong", "HK", "Traditional", "Pinyin for Mandarin classes",
     "Cantonese is the daily classroom language; no standard phonetic aid, Pinyin used in Mandarin lessons."),
    ("Macau", "MO", "Traditional", "Pinyin for Mandarin classes",
     "Similar to Hong Kong; Portuguese is also official. Mandarin taught as a subject, often with Pinyin."),
    ("Singapore", "SG", "Simplified", "Hanyu Pinyin",
     "Mandarin is the 'Mother Tongue' subject, taught with Simplified characters and Pinyin."),
    ("Malaysia", "MY", "Simplified", "Hanyu Pinyin",
     "Chinese-medium schools mostly use Simplified since the 1980s, with Hanyu Pinyin."),
    ("Overseas heritage schools", "—", "Traditional or Simplified", "Zhuyin or Pinyin",
     "Taiwan-oriented weekend schools often teach Traditional + Zhuyin; Mainland-oriented ones teach Simplified + Pinyin."),
]


def cn_regions_json():
    return {
        "name": "Chinese script & Mandarin phonetic system by region",
        "description": ("Which Chinese script (Traditional or Simplified) and which Mandarin "
                        "pronunciation system (Zhuyin/Bopomofo or Hanyu Pinyin) is standard in "
                        "schools across Taiwan, Mainland China, Hong Kong, Macau, Singapore, "
                        "Malaysia and overseas heritage communities."),
        "identifier": f"{SITE}/data/chinese-script-phonetics-by-region.json",
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "creator": "Lumi Apps",
        "dateModified": TODAY,
        "regions": [{"region": r, "code": c, "script": s, "mandarinPhonetic": p, "notes": n}
                    for r, c, s, p, n in CN_REGIONS],
    }


def build_cn_regions_page():
    slug = "chinese-script-phonetics-by-region"
    title = "Traditional vs Simplified, Zhuyin vs Pinyin — by Region | Open Data"
    h1 = "Chinese script & phonetics by region"
    desc = ("Does Taiwan use Zhuyin or Pinyin? Traditional or Simplified in Hong Kong? A citable "
            "reference of the standard Chinese script and Mandarin phonetic system by region. "
            "Free open data (CC BY 4.0).")
    lead = ("Taiwan uses Traditional characters and Zhuyin (Bopomofo); the Mainland uses Simplified "
            "and Pinyin. Here is the full, citable breakdown by region.")
    rows = ""
    for r, c, s, p, n in CN_REGIONS:
        rows += (f'<tr><td><strong>{html.escape(r)}</strong></td>'
                 f'<td class="nw">{html.escape(s)}</td>'
                 f'<td class="nw">{html.escape(p)}</td>'
                 f'<td>{html.escape(n)}</td></tr>')
    tables = ('<div class="card"><table>'
              '<tr><th>Region</th><th>Script</th><th>Mandarin phonetic</th><th>Notes</th></tr>'
              f'{rows}</table></div>')
    dj = cn_regions_json()
    schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "Dataset", "name": dj["name"], "description": dj["description"],
        "url": f"{SITE}/data/{slug}.html", "identifier": dj["identifier"],
        "license": dj["license"], "creator": {"@type": "Organization", "name": "Lumi Apps"},
        "dateModified": dj["dateModified"],
        "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json",
                          "contentUrl": dj["identifier"]}],
        "keywords": ["Traditional Chinese", "Simplified Chinese", "Zhuyin", "Bopomofo",
                     "Hanyu Pinyin", "Taiwan", "Mandarin"],
    }, ensure_ascii=False)
    pills = ('<span class="pill">7 regions</span>'
             '<span class="pill">script + phonetics</span>')
    cta = ('<h2>Learning the Taiwan way — Traditional + Zhuyin</h2>\n'
           '<p>If your family follows the Taiwanese system (Traditional characters, Zhuyin first), '
           '<strong>Lumi Bopomofo</strong> teaches all 37 Zhuyin symbols through games — a one-time '
           'purchase, no ads, no subscription, everything on the device.</p>\n'
           f'<a class="cta" href="{BOPOMOFO_APP}">Get Lumi Bopomofo on the App Store →</a>\n'
           f'<p style="font-size:14px"><a href="{SITE}/data/zhuyin-bopomofo.html">'
           'See the full Zhuyin dataset →</a> &nbsp;·&nbsp; '
           f'<a href="{SITE}/data/">More open datasets →</a></p>')
    page = PAGE.format(title=html.escape(title), desc=html.escape(desc), h1=html.escape(h1),
                       lead=html.escape(lead), site=SITE, slug=slug, today=TODAY,
                       crumb="Chinese script & phonetics", pills=pills, tables=tables,
                       schema=schema, cta=cta,
                       related=related_block([
                           ("Kids learning apps", "kids-learning.html"),
                           ("Zhuyin (Bopomofo) dataset", "data/zhuyin-bopomofo.html"),
                           ("Printable Bopomofo chart", "tools/zhuyin-bopomofo-chart.html")]))
    os.makedirs(DATA, exist_ok=True)
    open(os.path.join(DATA, f"{slug}.json"), "w", encoding="utf-8").write(
        json.dumps(dj, ensure_ascii=False, indent=2))
    open(os.path.join(DATA, f"{slug}.html"), "w", encoding="utf-8").write(page)
    return slug


# ── Résumé / CV conventions by country (ties to CV Desk) ──
RESUME = [
    # (country, code, local_term, photo, length, personal_details)
    ("United States", "US", "Résumé", "No", "1 page", "No — omit age, DOB, marital status"),
    ("United Kingdom", "GB", "CV", "No", "2 pages", "No — no DOB, gender or marital status"),
    ("Canada", "CA", "Résumé / CV", "No", "1–2 pages", "No — no DOB, gender or marital status"),
    ("Australia", "AU", "Résumé / CV", "No", "1–2 pages", "No — personal details not expected"),
    ("Germany", "DE", "Lebenslauf", "Yes", "1–2 pages", "Yes — DOB common, sometimes nationality"),
    ("France", "FR", "CV", "Yes", "1 page", "Yes — DOB, sometimes marital status"),
    ("Japan", "JP", "Rirekisho (履歴書)", "Yes (required)", "Standard form", "Yes — DOB, gender, address"),
    ("China", "CN", "简历", "Yes", "1–2 pages", "Yes — DOB, gender, marital status"),
    ("Netherlands", "NL", "CV", "Sometimes", "1–2 pages", "Sometimes — DOB often included"),
    ("Spain", "ES", "CV", "Yes", "1–2 pages", "Yes — DOB, marital status often included"),
    ("Brazil", "BR", "Currículo", "Yes", "1–2 pages", "Yes — DOB, marital status common"),
    ("India", "IN", "Résumé / CV", "Sometimes", "1–2 pages", "Yes — DOB, gender often included"),
]


def resume_json():
    return {
        "name": "Résumé / CV conventions by country",
        "description": ("Whether to include a photo, the typical length, and whether to add "
                        "personal details (date of birth, marital status) on a résumé or CV in "
                        "major countries — plus the local term used."),
        "identifier": f"{SITE}/data/resume-cv-conventions-by-country.json",
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "creator": "Lumi Apps",
        "dateModified": TODAY,
        "disclaimer": ("General conventions that vary by industry and employer; always tailor to "
                       "the specific role. Anti-discrimination norms drive the 'no photo / no "
                       "personal details' practice in the US, UK, Canada and Australia."),
        "countries": [{"country": c, "code": code, "localTerm": term, "photo": photo,
                       "typicalLength": length, "personalDetails": pd}
                      for c, code, term, photo, length, pd in RESUME],
    }


def build_resume_page():
    slug = "resume-cv-conventions-by-country"
    title = "Resume Photo, Length & CV Rules by Country — Open Data"
    h1 = "Résumé / CV conventions by country"
    desc = ("Should a resume have a photo? How long should a CV be? A citable reference of resume/CV "
            "conventions — photo, length and personal details — by country. Free open data (CC BY 4.0).")
    lead = ("Resume rules differ sharply by country: a photo is expected in Germany but can be a "
            "liability in the US. Here is a citable summary of photo, length and personal-detail "
            "conventions by country.")
    rows = ""
    for c, code, term, photo, length, pd in RESUME:
        rows += (f'<tr><td><strong>{html.escape(c)}</strong></td>'
                 f'<td class="nw">{html.escape(term)}</td>'
                 f'<td class="nw">{html.escape(photo)}</td>'
                 f'<td class="nw">{html.escape(length)}</td>'
                 f'<td>{html.escape(pd)}</td></tr>')
    tables = ('<div class="card"><table>'
              '<tr><th>Country</th><th>Local term</th><th>Photo</th><th>Length</th>'
              '<th>Personal details</th></tr>'
              f'{rows}</table></div>')
    dj = resume_json()
    schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "Dataset", "name": dj["name"], "description": dj["description"],
        "url": f"{SITE}/data/{slug}.html", "identifier": dj["identifier"],
        "license": dj["license"], "creator": {"@type": "Organization", "name": "Lumi Apps"},
        "dateModified": dj["dateModified"],
        "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json",
                          "contentUrl": dj["identifier"]}],
        "keywords": ["resume", "CV", "resume photo", "resume length", "by country", "job application"],
    }, ensure_ascii=False)
    pills = (f'<span class="pill">{len(RESUME)} countries</span>'
             '<span class="pill">photo · length · details</span>')
    cta = ('<h2>Build a country-ready résumé — pay once, no subscription</h2>\n'
           '<p>Once you know the local rules, <strong>CV Desk</strong> helps you build an '
           'ATS-friendly résumé with recruiter-ready templates and an instant ATS score — a '
           'one-time purchase, no subscription.</p>\n'
           f'<a class="cta" href="{CVDESK_APP}">Get CV Desk on the App Store →</a>\n'
           f'<p style="font-size:14px"><a href="{SITE}/data/">More open datasets →</a></p>')
    page = PAGE.format(title=html.escape(title), desc=html.escape(desc), h1=html.escape(h1),
                       lead=html.escape(lead), site=SITE, slug=slug, today=TODAY,
                       crumb="Résumé / CV conventions", pills=pills, tables=tables,
                       schema=schema, cta=cta,
                       related=related_block([
                           ("Resume & CV formats by country", "resume-formats.html"),
                           ("CV Desk guide", "guides/cvdesk.html")]))
    os.makedirs(DATA, exist_ok=True)
    open(os.path.join(DATA, f"{slug}.json"), "w", encoding="utf-8").write(
        json.dumps(dj, ensure_ascii=False, indent=2))
    open(os.path.join(DATA, f"{slug}.html"), "w", encoding="utf-8").write(page)
    return slug


# ── Currency formatting by country (ties to G+Money) ──
CURRENCY = [
    # (country, iso, symbol, position, decimal_sep, thousands_sep, example)
    ("United States", "USD", "$", "before", ".", ",", "$1,234,567.89"),
    ("United Kingdom", "GBP", "£", "before", ".", ",", "£1,234,567.89"),
    ("Germany", "EUR", "€", "after", ",", ".", "1.234.567,89 €"),
    ("France", "EUR", "€", "after", ",", " (space)", "1 234 567,89 €"),
    ("Ireland", "EUR", "€", "before", ".", ",", "€1,234,567.89"),
    ("Japan", "JPY", "¥", "before", "— (no minor unit)", ",", "¥1,234,567"),
    ("Switzerland", "CHF", "CHF", "before", ".", "’ (apostrophe)", "CHF 1’234’567.89"),
    ("India", "INR", "₹", "before", ".", ", (2-2-3 grouping)", "₹12,34,567.89"),
    ("Brazil", "BRL", "R$", "before", ",", ".", "R$ 1.234.567,89"),
    ("China", "CNY", "¥", "before", ".", ",", "¥1,234,567.89"),
    ("Canada", "CAD", "$", "before", ".", ",", "$1,234,567.89"),
    ("Australia", "AUD", "$", "before", ".", ",", "$1,234,567.89"),
    ("South Korea", "KRW", "₩", "before", "— (no minor unit)", ",", "₩1,234,567"),
    ("Taiwan", "TWD", "NT$", "before", ".", ",", "NT$1,234,567"),
]


def currency_json():
    return {
        "name": "Currency formatting by country",
        "description": ("How money is written in each country: the currency symbol, whether the "
                        "symbol goes before or after the amount, the decimal separator, the "
                        "thousands separator and a worked example of 1234567.89."),
        "identifier": f"{SITE}/data/currency-format-by-country.json",
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "creator": "Lumi Apps",
        "dateModified": TODAY,
        "currencies": [{"country": c, "currencyCode": iso, "symbol": sym, "symbolPosition": pos,
                        "decimalSeparator": dsep, "thousandsSeparator": tsep, "example": ex}
                       for c, iso, sym, pos, dsep, tsep, ex in CURRENCY],
    }


def build_currency_page():
    slug = "currency-format-by-country"
    title = "Currency Format by Country — Symbol, Separators | Open Data"
    h1 = "Currency formatting by country"
    desc = ("How is currency written in each country? Symbol position, decimal and thousands "
            "separators with a worked example, by country. Free, machine-readable open data (CC BY 4.0).")
    lead = ("$1,234.56 in the US is 1.234,56 € in Germany and CHF 1’234.56 in Switzerland. Here is "
            "a citable reference of currency symbols, separators and formatting by country.")
    rows = ""
    for c, iso, sym, pos, dsep, tsep, ex in CURRENCY:
        rows += (f'<tr><td><strong>{html.escape(c)}</strong></td>'
                 f'<td class="nw">{html.escape(iso)} {html.escape(sym)}</td>'
                 f'<td class="nw">{html.escape(pos)}</td>'
                 f'<td class="nw">{html.escape(dsep)} / {html.escape(tsep)}</td>'
                 f'<td class="nw">{html.escape(ex)}</td></tr>')
    tables = ('<div class="card"><table>'
              '<tr><th>Country</th><th>Currency</th><th>Symbol</th>'
              '<th>Decimal / thousands</th><th>Example</th></tr>'
              f'{rows}</table></div>')
    dj = currency_json()
    schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "Dataset", "name": dj["name"], "description": dj["description"],
        "url": f"{SITE}/data/{slug}.html", "identifier": dj["identifier"],
        "license": dj["license"], "creator": {"@type": "Organization", "name": "Lumi Apps"},
        "dateModified": dj["dateModified"],
        "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json",
                          "contentUrl": dj["identifier"]}],
        "keywords": ["currency format", "currency symbol", "decimal separator", "thousands separator",
                     "by country", "money formatting"],
    }, ensure_ascii=False)
    pills = (f'<span class="pill">{len(CURRENCY)} currencies</span>'
             '<span class="pill">symbol · separators · example</span>')
    cta = ('<h2>Convert and log money in any currency — pay once</h2>\n'
           '<p>Travelling or shopping across currencies? <strong>G+Money</strong> converts and logs '
           'every expense in one tap, offline — a one-time purchase, no subscription.</p>\n'
           f'<a class="cta" href="{GMONEY_APP}">Get G+Money on the App Store →</a>\n'
           f'<p style="font-size:14px"><a href="{SITE}/data/">More open datasets →</a></p>')
    page = PAGE.format(title=html.escape(title), desc=html.escape(desc), h1=html.escape(h1),
                       lead=html.escape(lead), site=SITE, slug=slug, today=TODAY,
                       crumb="Currency formatting", pills=pills, tables=tables,
                       schema=schema, cta=cta,
                       related=related_block([
                           ("Money & travel apps", "money-travel.html"),
                           ("G+Money guide", "guides/gmoney.html")]))
    os.makedirs(DATA, exist_ok=True)
    open(os.path.join(DATA, f"{slug}.json"), "w", encoding="utf-8").write(
        json.dumps(dj, ensure_ascii=False, indent=2))
    open(os.path.join(DATA, f"{slug}.html"), "w", encoding="utf-8").write(page)
    return slug


# ── Mandarin tones (ties to Lumi Bopomofo) ──
TONES = [
    # (tone, chao, description, zhuyin_mark, pinyin_ex, char, meaning)
    ("1st (high level)", "55", "High and level, like holding a steady high note",
     "(unmarked)", "mā", "媽", "mother"),
    ("2nd (rising)", "35", "Rises from mid to high, like a questioning 'eh?'",
     "ˊ", "má", "麻", "hemp"),
    ("3rd (dipping)", "214", "Dips low then rises; often just low in fast speech",
     "ˇ", "mǎ", "馬", "horse"),
    ("4th (falling)", "51", "Starts high and drops sharply, like a firm command",
     "ˋ", "mà", "罵", "scold"),
    ("Neutral (light)", "—", "Short, light, unstressed; pitch depends on the tone before",
     "˙", "ma", "嗎", "question particle"),
]


def tones_json():
    return {
        "name": "Mandarin Chinese tones (with Zhuyin & Pinyin marks)",
        "description": ("The four Mandarin tones plus the neutral tone, each with its Chao "
                        "pitch-contour number, description, Zhuyin (Bopomofo) tone mark, Pinyin "
                        "mark and the classic 'ma' example."),
        "identifier": f"{SITE}/data/mandarin-tones.json",
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "creator": "Lumi Apps",
        "dateModified": TODAY,
        "tones": [{"tone": t, "chaoContour": c, "description": d, "zhuyinMark": z,
                   "pinyinExample": p, "exampleCharacter": ch, "meaning": m}
                  for t, c, d, z, p, ch, m in TONES],
    }


def build_tones_page():
    slug = "mandarin-tones"
    title = "The 4 Mandarin Tones (+ Neutral) — Chart with Zhuyin & Pinyin | Open Data"
    h1 = "Mandarin Chinese tones"
    desc = ("How many tones does Mandarin have? The four tones plus the neutral tone, each with "
            "its pitch contour, Zhuyin (Bopomofo) & Pinyin marks and the classic 'ma' example. "
            "Free open data (CC BY 4.0).")
    lead = ("Mandarin is tonal: the same sound 'ma' means mother, hemp, horse or scold depending "
            "on the tone. Here is a citable reference of all five tones with their marks.")
    rows = ""
    for t, c, d, z, p, ch, m in TONES:
        rows += (f'<tr><td><strong>{html.escape(t)}</strong></td>'
                 f'<td class="nw">{html.escape(c)}</td>'
                 f'<td class="nw" style="font-size:20px">{html.escape(z)}</td>'
                 f'<td class="nw">{ch} <span class="py">{html.escape(p)}</span> — {html.escape(m)}</td>'
                 f'<td>{html.escape(d)}</td></tr>')
    tables = ('<div class="card"><table>'
              '<tr><th>Tone</th><th>Pitch (Chao)</th><th>Zhuyin mark</th>'
              '<th>Example</th><th>Description</th></tr>'
              f'{rows}</table></div>')
    dj = tones_json()
    schema = json.dumps({
        "@context": "https://schema.org",
        "@type": "Dataset", "name": dj["name"], "description": dj["description"],
        "url": f"{SITE}/data/{slug}.html", "identifier": dj["identifier"],
        "license": dj["license"], "creator": {"@type": "Organization", "name": "Lumi Apps"},
        "dateModified": dj["dateModified"],
        "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json",
                          "contentUrl": dj["identifier"]}],
        "keywords": ["Mandarin tones", "Chinese tones", "Zhuyin", "Bopomofo", "Pinyin",
                     "tone marks", "四聲"],
    }, ensure_ascii=False)
    pills = ('<span class="pill">4 tones + neutral</span>'
             '<span class="pill">Zhuyin & Pinyin marks</span>')
    cta = ('<h2>Learn tones and Zhuyin the Taiwan way</h2>\n'
           '<p>Tones make or break Mandarin pronunciation. <strong>Lumi Bopomofo</strong> teaches '
           'the 37 Zhuyin symbols and their tone marks through games — a one-time purchase, no ads, '
           'no subscription, on-device.</p>\n'
           f'<a class="cta" href="{BOPOMOFO_APP}">Get Lumi Bopomofo on the App Store →</a>\n'
           f'<p style="font-size:14px"><a href="{SITE}/data/zhuyin-bopomofo.html">Zhuyin symbols '
           'dataset →</a> &nbsp;·&nbsp; <a href="{S}/data/">More open datasets →</a></p>'
           .replace("{S}", SITE))
    page = PAGE.format(title=html.escape(title), desc=html.escape(desc), h1=html.escape(h1),
                       lead=html.escape(lead), site=SITE, slug=slug, today=TODAY,
                       crumb="Mandarin tones", pills=pills, tables=tables, schema=schema, cta=cta,
                       related=related_block([
                           ("Zhuyin (Bopomofo) symbols", "data/zhuyin-bopomofo.html"),
                           ("Kids learning apps", "kids-learning.html"),
                           ("Printable Bopomofo chart", "tools/zhuyin-bopomofo-chart.html")]))
    os.makedirs(DATA, exist_ok=True)
    open(os.path.join(DATA, f"{slug}.json"), "w", encoding="utf-8").write(
        json.dumps(dj, ensure_ascii=False, indent=2))
    open(os.path.join(DATA, f"{slug}.html"), "w", encoding="utf-8").write(page)
    return slug


INDEX = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Open Data — free, citable datasets for AI & researchers | Lumi Apps</title>
<meta name="description" content="Free, machine-readable open datasets (CC BY 4.0) you can cite and reuse — starting with the complete 37-symbol Zhuyin/Bopomofo chart.">
<link rel="canonical" href="{site}/data/">
<script type="application/ld+json">{schema}</script>
<style>
body{{margin:0;font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,"PingFang TC",sans-serif;color:#1d2433;background:#f7f8fb}}
.wrap{{max-width:820px;margin:0 auto;padding:32px 20px 64px}}
a{{color:#5b4bdb}}
h1{{font-size:clamp(26px,5vw,36px);margin:.1em 0}}
.lead{{color:#5b6577;font-size:clamp(15px,3.4vw,18px)}}
.item{{display:block;background:#fff;border:1px solid #e7ebf2;border-radius:16px;padding:18px 20px;margin:16px 0;text-decoration:none;color:inherit}}
.item h2{{margin:0 0 4px;font-size:19px}}
.item p{{margin:0;color:#5b6577;font-size:15px}}
.tag{{display:inline-block;background:#eef0fb;color:#5b4bdb;border-radius:999px;padding:3px 10px;font-size:12px;font-weight:600;margin-top:8px}}
.foot{{color:#5b6577;font-size:13px;margin-top:28px}}
</style>
</head>
<body>
<div class="wrap">
<h1>Open data</h1>
<p class="lead">Free, machine-readable reference datasets you can cite and reuse under
<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a> — built and maintained by
the makers of a family of pay-once iOS apps.</p>
{items}
<p class="foot">Building on the web with AI? These datasets are clean JSON with schema.org
metadata — free to ingest and cite. Please credit “Lumi Apps ({site})”.</p>
</div>
</body>
</html>
"""


def build_index(datasets):
    items = ""
    for d in datasets:
        items += (f'<a class="item" href="{SITE}/data/{d["slug"]}.html"><h2>{html.escape(d["name"])}</h2>'
                  f'<p>{html.escape(d["blurb"])}</p><span class="tag">{d["tag"]}</span></a>')
    schema = json.dumps({
        "@context": "https://schema.org", "@type": "DataCatalog",
        "name": "Open data — Lumi Apps",
        "description": "Free, machine-readable reference datasets (CC BY 4.0) for AI assistants, "
                       "researchers and developers, maintained by the makers of pay-once iOS apps.",
        "url": f"{SITE}/data/",
        "creator": {"@type": "Organization", "name": "Lumi Apps"},
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "dataset": [{"@type": "Dataset", "name": d["name"], "description": d["blurb"],
                     "url": f"{SITE}/data/{d['slug']}.html",
                     "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json",
                                       "contentUrl": f"{SITE}/data/{d['slug']}.json"}]}
                    for d in datasets],
    }, ensure_ascii=False)
    open(os.path.join(DATA, "index.html"), "w", encoding="utf-8").write(
        INDEX.format(site=SITE, items=items, schema=schema))


def build_sitemap(datasets):
    urls = [f"{SITE}/data/"] + [f"{SITE}/data/{d['slug']}.html" for d in datasets]
    body = "\n".join(
        f"  <url><loc>{u}</loc><lastmod>{TODAY}</lastmod></url>" for u in urls)
    sm = ('<?xml version="1.0" encoding="UTF-8"?>\n'
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
          f"{body}\n</urlset>\n")
    open(os.path.join(PAGES, "sitemap_data.xml"), "w", encoding="utf-8").write(sm)
    return urls


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)


def publish(urls):
    repo = os.path.join(PAGES)
    try:
        run(["git", "add", "-A"], cwd=repo)
        run(["git", "commit", "-m",
             "Open data hub update (CC-BY, AI-citable datasets)\n\n"
             "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"], cwd=repo)
        run(["git", "pull", "--rebase", "--autostash"], cwd=repo)
        run(["git", "push"], cwd=repo)
        print("pushed pages repo")
    except subprocess.CalledProcessError as e:
        print("git step skipped/failed:", (e.stderr or e.stdout or "")[-300:])
    key_path = os.path.join(HERE, "indexnow_key.txt")
    if os.path.exists(key_path):
        key = open(key_path).read().strip()
        host = SITE.split("//", 1)[-1].split("/", 1)[0]
        payload = json.dumps({"host": host, "key": key, "urlList": urls}).encode()
        try:
            req = urllib.request.Request("https://api.indexnow.org/indexnow", data=payload,
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=20)
            print("IndexNow pinged", len(urls), "urls")
        except Exception as e:  # noqa: BLE001
            print("IndexNow skipped:", e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true")
    args = ap.parse_args()
    slug = build_zhuyin_page()
    pslug = build_passport_page()
    rslug = build_cn_regions_page()
    cvslug = build_resume_page()
    curslug = build_currency_page()
    tslug = build_tones_page()
    datasets = [{
        "slug": slug,
        "name": "Zhuyin (Bopomofo): all 37 symbols",
        "blurb": "The complete 21 initials + 3 medials + 13 finals, each with Pinyin, "
                 "Unicode and an example word. JSON download included.",
        "tag": "Language · CC BY 4.0",
    }, {
        "slug": tslug,
        "name": "Mandarin tones (with Zhuyin & Pinyin marks)",
        "blurb": "The 4 tones + neutral, each with Chao pitch contour, Zhuyin/Pinyin marks and "
                 "the classic 'ma' example. JSON download included.",
        "tag": "Language · CC BY 4.0",
    }, {
        "slug": rslug,
        "name": "Chinese script & phonetics by region",
        "blurb": "Traditional vs Simplified and Zhuyin vs Pinyin across Taiwan, China, Hong Kong, "
                 "Singapore, Malaysia and overseas schools. JSON download included.",
        "tag": "Language · CC BY 4.0",
    }, {
        "slug": pslug,
        "name": "Passport & ID photo sizes by country",
        "blurb": "Official passport/ID photo dimensions (mm), head height and background "
                 "colour for 13 major countries. JSON download included.",
        "tag": "Reference · CC BY 4.0",
    }, {
        "slug": cvslug,
        "name": "Résumé / CV conventions by country",
        "blurb": "Photo or no photo, typical length and personal details on a résumé/CV across "
                 "12 countries, with the local term. JSON download included.",
        "tag": "Reference · CC BY 4.0",
    }, {
        "slug": curslug,
        "name": "Currency formatting by country",
        "blurb": "Currency symbol, symbol position, decimal and thousands separators with a "
                 "worked example across 14 countries. JSON download included.",
        "tag": "Reference · CC BY 4.0",
    }]
    build_index(datasets)
    urls = build_sitemap(datasets)
    print("generated /data/ hub:", len(datasets), "dataset(s);", len(urls), "urls")
    if args.publish:
        publish(urls)


if __name__ == "__main__":
    main()
