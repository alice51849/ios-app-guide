#!/usr/bin/env python3
"""Publish the bilingual family-travel taxonomy and its machine-readable files."""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "social"))

from appstore_live import live_app_keys  # noqa: E402
from videogen.registry import APPSTORE, appstore_url  # noqa: E402


SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
PAGES = HERE / "pages"
SOURCE_DIR = HERE / "reference_datasets"
SLUG = "family-travel-missions"
APP_KEY = "tripplanet"
APP_ID = "6787193643"
APP_NAME = "Lumi Trip Planet: World Travel"
APP_SHORT_NAME = "Lumi Trip Planet"
TODAY = dt.date.today().isoformat()
FILES = (
    f"{SLUG}.json",
    f"{SLUG}.csv",
    f"{SLUG}.schema.json",
    f"{SLUG}.csv-metadata.json",
    f"{SLUG}.dcat.jsonld",
)
DICTIONARY_URL = (
    "https://github.com/alice51849/open-reference-datasets/blob/master/"
    "DATA_DICTIONARY.md"
)
API_DOCS_URL = f"{SITE}/api/v1/family-travel-missions/"
PASSPORT_URL = f"{SITE}/tools/family-travel-observation-passport.html"
RO_CRATE_FILENAME = f"{SLUG}-ro-crate-metadata.json"
RO_CRATE_URL = f"{SITE}/data/{RO_CRATE_FILENAME}"
CONTENT_MODIFIED_RE = re.compile(
    r'<meta name="content-modified" content="([0-9]{4}-[0-9]{2}-[0-9]{2})">'
)

COPY = {
    "en": {
        "lang": "en",
        "locale_path": "",
        "title": "Family Travel Mission Taxonomy — Bilingual Open Data",
        "description": (
            "Download 252 privacy-first family travel prompts across 12 settings in "
            "English and Traditional Chinese as JSON, CSV, JSON Schema and CSVW."
        ),
        "eyebrow": "Open data · English + Traditional Chinese",
        "open_data": "Open data",
        "language": "繁體中文",
        "lead": (
            "A reusable taxonomy of 84 original observation targets and three flexible "
            "participation modes for common family-travel settings."
        ),
        "badges": (
            "12 settings",
            "84 observation targets",
            "252 flat records",
            "CC BY 4.0",
        ),
        "download": "Download the data",
        "download_intro": (
            "JSON preserves the nested taxonomy; CSV expands every scenario, target and "
            "participation-mode combination into one record."
        ),
        "json": "Canonical JSON",
        "csv": "Flat CSV",
        "schema": "JSON Schema",
        "csvw": "CSVW metadata",
        "dcat": "DCAT 3 JSON-LD",
        "ro_crate": "RO-Crate research object",
        "dictionary": "Data dictionary",
        "design": "Privacy and safety by design",
        "design_text": (
            "Every prompt is optional, adult-supervised and restricted to a safely "
            "stationary or seated setting. The taxonomy contains no photo task, score, "
            "age band, ability level or completion tracking."
        ),
        "excluded": (
            "No name, age, destination, precise location, photo, itinerary or completion "
            "record is requested."
        ),
        "modes": "Three participation choices — not levels",
        "mode_note": (
            "These are interchangeable ways to participate, never developmental or "
            "ability rankings."
        ),
        "scenarios": "Browse all 12 settings",
        "targets": "observation targets",
        "safety": "Safety boundary",
        "references": "Official safety references",
        "references_note": (
            "These sources support selected safety boundaries. They do not endorse the "
            "dataset, and current local, venue, carrier, crew, ranger and supervising-adult "
            "instructions always take precedence."
        ),
        "limitations": "Scope and limitations",
        "method": "Method",
        "cite": "How to cite",
        "cite_note": (
            "Free to reuse under CC BY 4.0 with attribution. Suggested citation:"
        ),
        "related": "Free companion resources",
        "passport": "Print the family travel observation passport",
        "generator": "Make printable mission cards",
        "curated": "Compare trusted family-travel resources",
        "api": "Use the versioned static API",
        "app_title": "Optional digital travel layer",
        "app_text": (
            "Lumi Trip Planet adds an optional on-device way to continue world-travel "
            "activities. The open dataset and card generator remain free and independent."
        ),
        "app_cta": "View Lumi Trip Planet on the App Store",
        "footer": (
            "Original bilingual taxonomy maintained by Lumi Apps. Official agencies named "
            "here do not endorse this dataset."
        ),
    },
    "zh-Hant": {
        "lang": "zh-Hant",
        "locale_path": "zh-Hant/",
        "title": "親子旅行任務分類資料集 — 英繁雙語開放資料",
        "description": (
            "下載涵蓋 12 種情境、共 252 筆的隱私優先親子旅行提示，提供英繁雙語 "
            "JSON、CSV、JSON Schema 與 CSVW。"
        ),
        "eyebrow": "開放資料 · 英文＋繁體中文",
        "open_data": "開放資料",
        "language": "English",
        "lead": (
            "涵蓋常見親子旅行情境的可再利用分類資料，包含 84 個原創觀察目標與"
            "三種彈性參與方式。"
        ),
        "badges": (
            "12 種情境",
            "84 個觀察目標",
            "252 筆扁平資料",
            "CC BY 4.0",
        ),
        "download": "下載資料",
        "download_intro": (
            "JSON 保留巢狀分類結構；CSV 則將每個情境、觀察目標與參與方式組合"
            "展開成一筆資料。"
        ),
        "json": "標準 JSON",
        "csv": "扁平 CSV",
        "schema": "JSON Schema",
        "csvw": "CSVW 中繼資料",
        "dcat": "DCAT 3 JSON-LD",
        "ro_crate": "RO-Crate 研究物件",
        "dictionary": "資料字典",
        "design": "從資料設計落實隱私與安全",
        "design_text": (
            "每個提示都可自由跳過、需由大人陪同，且只能在安全原地或坐好時使用。"
            "分類資料不含拍照任務、評分、年齡層、能力等級或完成追蹤。"
        ),
        "excluded": (
            "不要求姓名、年齡、目的地、精確位置、照片、行程或完成紀錄。"
        ),
        "modes": "三種參與選擇，不是分級",
        "mode_note": "三種方式可自由替換，絕不是發展階段或能力排名。",
        "scenarios": "瀏覽全部 12 種情境",
        "targets": "個觀察目標",
        "safety": "安全界線",
        "references": "官方安全參考",
        "references_note": (
            "這些來源只支援部分安全界線，不代表官方認可本資料集；當下當地、場館、"
            "運輸業者、機組員、巡護員與陪同大人的指示永遠優先。"
        ),
        "limitations": "範圍與限制",
        "method": "方法",
        "cite": "引用方式",
        "cite_note": "依 CC BY 4.0 授權，可在標示來源後自由再利用。建議引用：",
        "related": "免費搭配資源",
        "passport": "列印親子旅行觀察護照",
        "generator": "製作可列印任務卡",
        "curated": "比較可信親子旅行資源",
        "api": "使用版本化靜態 API",
        "app_title": "選用數位旅行層",
        "app_text": (
            "Lumi Trip Planet 提供選用的裝置端世界旅行活動；開放資料與任務卡"
            "產生器仍維持免費且獨立。"
        ),
        "app_cta": "在 App Store 查看 Lumi Trip Planet",
        "footer": (
            "由 Lumi Apps 維護的原創英繁雙語分類資料；所列官方機構不為本資料集背書。"
        ),
    },
}


def load_dataset() -> dict:
    return json.loads((SOURCE_DIR / f"{SLUG}.json").read_text(encoding="utf-8"))


def write_text_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def copy_if_changed(source: Path, target: Path) -> bool:
    if target.exists() and target.read_bytes() == source.read_bytes():
        return False
    shutil.copyfile(source, target)
    return True


def render_versioned_page(
    path: Path,
    renderer,
    initial_date: str,
    current_date: str = TODAY,
) -> str:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    match = CONTENT_MODIFIED_RE.search(existing)
    prior_date = match.group(1) if match else initial_date
    candidate = renderer(prior_date)
    if candidate == existing:
        return prior_date
    modified = current_date
    write_text_if_changed(path, renderer(modified))
    return modified


def is_app_public(pages: Path = PAGES) -> bool:
    return APP_KEY in live_app_keys(APPSTORE, pages, refresh=False)


def page_url(locale: str) -> str:
    prefix = "" if locale == "en" else f"{locale}/"
    return f"{SITE}/{prefix}data/{SLUG}.html"


def _dataset_schema(
    dataset: dict, locale: str, app_public: bool, page_modified: str
) -> dict:
    locale_copy = COPY[locale]
    canonical = page_url(locale)
    distributions = []
    formats = {
        f"{SLUG}.json": "application/json",
        f"{SLUG}.csv": "text/csv",
        f"{SLUG}.schema.json": "application/schema+json",
        f"{SLUG}.csv-metadata.json": "application/csvm+json",
        f"{SLUG}.dcat.jsonld": "application/ld+json",
    }
    for filename, encoding in formats.items():
        distributions.append(
            {
                "@type": "DataDownload",
                "name": filename,
                "encodingFormat": encoding,
                "contentUrl": f"{SITE}/data/{filename}",
                "contentSize": f"{(SOURCE_DIR / filename).stat().st_size} bytes",
            }
        )
    graph: list[dict] = [
        {
            "@type": "WebPage",
            "@id": canonical,
            "name": locale_copy["title"],
            "description": locale_copy["description"],
            "url": canonical,
            "inLanguage": locale_copy["lang"],
            "dateModified": page_modified,
            "mainEntity": {"@id": f"{canonical}#dataset"},
        },
        {
            "@type": "Dataset",
            "@id": f"{canonical}#dataset",
            "name": dataset["nameLocalized"][locale],
            "description": dataset["descriptionLocalized"][locale],
            "url": canonical,
            "identifier": dataset["identifier"],
            "license": dataset["license"],
            "creator": {"@type": "Organization", "name": dataset["creator"]},
            "version": dataset["version"],
            "dateCreated": dataset["dateCreated"],
            "dateModified": dataset["dateModified"],
            "inLanguage": dataset["languages"],
            "isAccessibleForFree": True,
            "keywords": dataset["keywords"],
            "measurementTechnique": dataset["methodology"][locale],
            "isBasedOn": [item["url"] for item in dataset["officialReferences"]],
            "distribution": distributions,
            "includedInDataCatalog": {
                "@type": "DataCatalog",
                "name": "Lumi Apps Open Data",
                "url": f"{SITE}/data/",
            },
            "subjectOf": [
                {
                    "@type": "WebApplication",
                    "name": dataset["relatedResources"][0]["name"][locale],
                    "url": (
                        dataset["relatedResources"][0]["url"]
                        if locale == "en"
                        else dataset["relatedResources"][0]["url"].replace(
                            f"{SITE}/", f"{SITE}/zh-Hant/"
                        )
                    ),
                },
                {
                    "@type": "TechArticle",
                    "name": COPY[locale]["api"],
                    "url": (
                        API_DOCS_URL
                        if locale == "en"
                        else f"{SITE}/zh-Hant/api/v1/{SLUG}/"
                    ),
                },
                {
                    "@type": "CreativeWork",
                    "name": COPY[locale]["ro_crate"],
                    "url": RO_CRATE_URL,
                    "encodingFormat": "application/ld+json",
                    "conformsTo": "https://w3id.org/ro/crate/1.3",
                },
            ],
            "usageInfo": DICTIONARY_URL,
            "citation": (
                f"Lumi Apps ({dataset['dateModified']}). "
                f"{dataset['nameLocalized'][locale]}. CC BY 4.0. {canonical}"
            ),
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": locale_copy["open_data"],
                    "item": f"{SITE}/data/",
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": dataset["nameLocalized"][locale],
                    "item": canonical,
                },
            ],
        },
    ]
    if app_public:
        graph.append(
            {
                "@type": "SoftwareApplication",
                "name": APP_NAME,
                "applicationCategory": "TravelApplication",
                "operatingSystem": "iOS",
                "url": appstore_url(APP_KEY, f"iag_dataset_{locale.lower()}"),
            }
        )
    return {"@context": "https://schema.org", "@graph": graph}


def _download_cards(copy: dict) -> str:
    downloads = (
        (copy["json"], f"{SLUG}.json", "JSON"),
        (copy["csv"], f"{SLUG}.csv", "CSV"),
        (copy["schema"], f"{SLUG}.schema.json", "Schema"),
        (copy["csvw"], f"{SLUG}.csv-metadata.json", "CSVW"),
        (copy["dcat"], f"{SLUG}.dcat.jsonld", "DCAT"),
        (copy["ro_crate"], RO_CRATE_FILENAME, "RO-Crate 1.3"),
    )
    cards = "".join(
        '<a class="download" href="{url}"><strong>{label}</strong>'
        '<span>{kind}</span></a>'.format(
            url=html.escape(f"{SITE}/data/{filename}", quote=True),
            label=html.escape(label),
            kind=html.escape(kind),
        )
        for label, filename, kind in downloads
    )
    cards += (
        '<a class="download" href="{url}"><strong>{label}</strong>'
        "<span>Markdown</span></a>"
    ).format(
        url=html.escape(DICTIONARY_URL, quote=True),
        label=html.escape(copy["dictionary"]),
    )
    return cards


def _mode_cards(dataset: dict, locale: str) -> str:
    cards = []
    for mode in dataset["participationModes"]:
        cards.append(
            '<article class="mode"><h3>{name}</h3><p>{template}</p></article>'.format(
                name=html.escape(mode["name"][locale]),
                template=html.escape(
                    mode["promptTemplate"][locale].replace("{target}", "…")
                ),
            )
        )
    return "".join(cards)


def _scenario_cards(dataset: dict, locale: str, copy: dict) -> str:
    cards = []
    for scenario in dataset["scenarios"]:
        targets = "".join(
            f"<li>{html.escape(target['text'][locale])}</li>"
            for target in scenario["targets"]
        )
        cards.append(
            '<details class="scenario"><summary><strong>{name}</strong>'
            '<span>7 {targets_label}</span></summary>'
            '<div class="scenario-body"><p class="boundary"><strong>{safety}:</strong> '
            "{boundary}</p><ol>{targets}</ol></div></details>".format(
                name=html.escape(scenario["name"][locale]),
                targets_label=html.escape(copy["targets"]),
                safety=html.escape(copy["safety"]),
                boundary=html.escape(scenario["safetyBoundary"][locale]),
                targets=targets,
            )
        )
    return "".join(cards)


def _reference_list(dataset: dict) -> str:
    return "".join(
        '<li><a href="{url}">{title}</a><span>{publisher}</span></li>'.format(
            url=html.escape(reference["url"], quote=True),
            title=html.escape(reference["title"]),
            publisher=html.escape(reference["publisher"]),
        )
        for reference in dataset["officialReferences"]
    )


def render_page(
    dataset: dict,
    locale: str,
    app_public: bool = False,
    page_modified: str | None = None,
) -> str:
    copy = COPY[locale]
    modified = page_modified or dataset["dateModified"]
    other_locale = "zh-Hant" if locale == "en" else "en"
    passport_url = PASSPORT_URL
    generator_url = dataset["relatedResources"][0]["url"]
    curated_url = dataset["relatedResources"][1]["url"]
    api_docs_url = (
        API_DOCS_URL if locale == "en" else f"{SITE}/zh-Hant/api/v1/{SLUG}/"
    )
    if locale == "zh-Hant":
        passport_url = passport_url.replace(f"{SITE}/", f"{SITE}/zh-Hant/")
        generator_url = generator_url.replace(f"{SITE}/", f"{SITE}/zh-Hant/")
        curated_url = curated_url.rstrip("/") + "/zh-Hant/"
    badges = "".join(f"<span>{html.escape(item)}</span>" for item in copy["badges"])
    app_block = ""
    if app_public:
        app_block = (
            '<section class="app"><p class="kicker">{title}</p><p>{text}</p>'
            '<a href="{url}">{cta} →</a></section>'
        ).format(
            title=html.escape(copy["app_title"]),
            text=html.escape(copy["app_text"]),
            url=html.escape(
                appstore_url(APP_KEY, f"iag_dataset_{locale.lower()}"), quote=True
            ),
            cta=html.escape(copy["app_cta"]),
        )
    citation = (
        f"Lumi Apps ({dataset['dateModified']}). "
        f"{dataset['nameLocalized'][locale]}. Version {dataset['version']}. "
        f"CC BY 4.0. {page_url(locale)}"
    )
    schema = json.dumps(
        _dataset_schema(dataset, locale, app_public, modified),
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="{html.escape(copy['lang'], quote=True)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(copy['title'])}</title>
<meta name="description" content="{html.escape(copy['description'], quote=True)}">
<meta name="content-modified" content="{html.escape(modified, quote=True)}">
<link rel="canonical" href="{html.escape(page_url(locale), quote=True)}">
<link rel="alternate" hreflang="en" href="{html.escape(page_url('en'), quote=True)}">
<link rel="alternate" hreflang="zh-Hant" href="{html.escape(page_url('zh-Hant'), quote=True)}">
<link rel="alternate" hreflang="x-default" href="{html.escape(page_url('en'), quote=True)}">
<link rel="describedby" type="application/ld+json" href="{html.escape(RO_CRATE_URL, quote=True)}" title="RO-Crate 1.3 metadata">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(copy['title'], quote=True)}">
<meta property="og:description" content="{html.escape(copy['description'], quote=True)}">
<script type="application/ld+json">{schema}</script>
<style>
:root{{--ink:#172033;--sub:#59657a;--line:#dde4ef;--paper:#fff;--wash:#f4f7fb;--brand:#3c5bca;--mint:#dff6ef}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--wash);color:var(--ink);font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,"PingFang TC","Microsoft JhengHei",sans-serif}}
a{{color:var(--brand)}}.wrap{{max-width:940px;margin:auto;padding:24px 20px 72px}}
.top{{display:flex;justify-content:space-between;gap:16px;align-items:center;font-size:14px}}
.top a{{font-weight:700;text-decoration:none}}.hero{{padding:54px 0 30px}}
.eyebrow,.kicker{{color:var(--brand);font-size:13px;font-weight:800;letter-spacing:.08em;text-transform:uppercase}}
h1{{font-size:clamp(31px,7vw,55px);line-height:1.08;letter-spacing:-.035em;max-width:820px;margin:10px 0 16px}}
.lead{{font-size:clamp(17px,3vw,21px);color:var(--sub);max-width:760px}}
.badges{{display:flex;gap:8px;flex-wrap:wrap;margin-top:24px}}.badges span{{background:var(--paper);border:1px solid var(--line);border-radius:999px;padding:6px 12px;font-size:13px;font-weight:700;white-space:nowrap}}
section{{margin-top:34px}}h2{{font-size:clamp(24px,4vw,32px);line-height:1.2;margin:0 0 10px}}h3{{margin:0 0 7px;font-size:18px}}p{{margin:8px 0;color:var(--sub)}}
.panel,.mode,.scenario,.app{{background:var(--paper);border:1px solid var(--line);box-shadow:0 12px 32px rgba(28,42,78,.05)}}
.panel{{border-radius:22px;padding:24px}}.downloads,.modes{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-top:18px}}
.download{{display:flex;flex-direction:column;gap:3px;padding:15px;border:1px solid var(--line);border-radius:14px;text-decoration:none;background:#fbfcff}}
.download span{{color:var(--sub);font-size:12px}}.privacy{{background:linear-gradient(135deg,var(--mint),#f7fffc)}}
.modes{{grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}}.mode{{border-radius:16px;padding:18px}}.mode p{{font-size:14px}}
.scenario{{border-radius:15px;margin:10px 0;overflow:hidden}}summary{{cursor:pointer;padding:17px 19px;display:flex;justify-content:space-between;align-items:center;gap:16px}}
summary span{{color:var(--sub);font-size:13px;white-space:nowrap}}.scenario-body{{border-top:1px solid var(--line);padding:8px 20px 18px}}
.boundary{{background:#f5f7fd;border-radius:12px;padding:12px 14px;font-size:14px}}ol{{columns:2;column-gap:34px;padding-left:24px}}li{{break-inside:avoid;margin:7px 0}}
.references li{{margin:12px 0}}.references li span{{display:block;color:var(--sub);font-size:13px}}
.citation{{background:#111827;color:#e9eefb;padding:16px 18px;border-radius:14px;overflow-wrap:anywhere;font:13px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace}}
.related{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}}.related a{{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:16px;text-decoration:none;font-weight:750}}
.app{{border-radius:20px;padding:22px;margin-top:34px}}.app a{{display:inline-block;margin-top:9px;font-weight:800;text-decoration:none}}footer{{margin-top:42px;padding-top:22px;border-top:1px solid var(--line);color:var(--sub);font-size:13px}}
@media(max-width:620px){{.hero{{padding-top:38px}}ol{{columns:1}}summary{{align-items:flex-start}}}}
</style>
</head>
<body>
<main class="wrap">
<nav class="top"><a href="{SITE}/data/">← {html.escape(copy['open_data'])}</a><a href="{html.escape(page_url(other_locale), quote=True)}">{html.escape(copy['language'])}</a></nav>
<header class="hero">
<p class="eyebrow">{html.escape(copy['eyebrow'])}</p>
<h1>{html.escape(dataset['nameLocalized'][locale])}</h1>
<p class="lead">{html.escape(copy['lead'])}</p>
<div class="badges">{badges}</div>
</header>
<section class="panel">
<h2>{html.escape(copy['download'])}</h2>
<p>{html.escape(copy['download_intro'])}</p>
<div class="downloads">{_download_cards(copy)}</div>
</section>
<section class="panel privacy">
<h2>{html.escape(copy['design'])}</h2>
<p>{html.escape(copy['design_text'])}</p><p><strong>{html.escape(copy['excluded'])}</strong></p>
</section>
<section>
<h2>{html.escape(copy['modes'])}</h2><p>{html.escape(copy['mode_note'])}</p>
<div class="modes">{_mode_cards(dataset, locale)}</div>
</section>
<section>
<h2>{html.escape(copy['scenarios'])}</h2>
{_scenario_cards(dataset, locale, copy)}
</section>
<section class="panel">
<h2>{html.escape(copy['references'])}</h2><p>{html.escape(copy['references_note'])}</p>
<ul class="references">{_reference_list(dataset)}</ul>
</section>
<section class="panel">
<h2>{html.escape(copy['limitations'])}</h2>
<p><strong>{html.escape(copy['method'])}:</strong> {html.escape(dataset['methodology'][locale])}</p>
<p>{html.escape(dataset['limitations'][locale])}</p>
</section>
<section>
<h2>{html.escape(copy['cite'])}</h2><p>{html.escape(copy['cite_note'])}</p>
<div class="citation">{html.escape(citation)}</div>
</section>
<section>
<h2>{html.escape(copy['related'])}</h2>
<div class="related"><a href="{html.escape(passport_url, quote=True)}">{html.escape(copy['passport'])} →</a><a href="{html.escape(generator_url, quote=True)}">{html.escape(copy['generator'])} →</a><a href="{html.escape(curated_url, quote=True)}">{html.escape(copy['curated'])} →</a><a href="{html.escape(api_docs_url, quote=True)}">{html.escape(copy['api'])} →</a></div>
</section>
{app_block}
<footer>{html.escape(copy['footer'])}</footer>
</main>
</body>
</html>
"""


def build(pages: Path = PAGES, app_public: bool | None = None) -> str:
    dataset = load_dataset()
    data_dir = pages / "data"
    zh_data_dir = pages / "zh-Hant" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    zh_data_dir.mkdir(parents=True, exist_ok=True)
    for filename in FILES:
        copy_if_changed(SOURCE_DIR / filename, data_dir / filename)
    public = is_app_public(pages) if app_public is None else app_public
    render_versioned_page(
        data_dir / f"{SLUG}.html",
        lambda modified: render_page(dataset, "en", public, modified),
        dataset["dateModified"],
        TODAY,
    )
    render_versioned_page(
        zh_data_dir / f"{SLUG}.html",
        lambda modified: render_page(dataset, "zh-Hant", public, modified),
        dataset["dateModified"],
        TODAY,
    )
    return SLUG


if __name__ == "__main__":
    build()
