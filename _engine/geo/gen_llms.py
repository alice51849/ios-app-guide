#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO 機器可讀層生成器 — llms.txt + llms-full.txt + robots + sitemap index。

讓 LLM 爬蟲(GPTBot/ClaudeBot/PerplexityBot/Google-Extended…)最容易「讀懂並引用」你:
  • llms.txt:AI 爬蟲索引 — 已公開 app 一句話價值 + App Store 連結。
  • llms-full.txt:從真實頁面與 registry 重建的完整 crawler map,不再手動過期。
  • robots.txt:明確歡迎各 AI bot,並列出全部 sitemap(含 alternatives/answers)。
  • sitemap_index.xml:把三張 sitemap 串成索引,讓爬蟲一次抓全。

不碰 app code。沿用 registry + aeo_sov.json。

    python geo/gen_llms.py            # 產檔(不部署)
    python geo/gen_llms.py --publish  # 並 git push + IndexNow
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))
from videogen.registry import APPS, APPSTORE, appstore_url  # noqa: E402
from appstore_live import live_app_keys  # noqa: E402
from aeo_pages import disp, pricing_profile  # noqa: E402
from rsscloud_config import (  # noqa: E402
    RSSCLOUD_NOTIFY_URL,
    RSSCLOUD_WEBSUB_HUB,
)
from static_api_catalog import API_DESCRIPTORS  # noqa: E402
from websub_config import WEBSUB_HUBS  # noqa: E402

PAGES = os.path.join(HERE, "pages")
ALT = os.path.join(PAGES, "alternatives")
GUIDES = os.path.join(PAGES, "guides")
DATA_DIR = os.path.join(PAGES, "data")
API_DIR = os.path.join(PAGES, "api")
TOOLS = os.path.join(PAGES, "tools")
STORIES = os.path.join(PAGES, "stories")
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide").rstrip("/")
SOV = os.path.join(HERE, "reports", "aeo_sov.json")
FAMILY_TRAVEL_OER = "family-travel-observation-passport"
FAMILY_TRAVEL_RO_CRATE = "family-travel-missions-ro-crate-metadata.json"
ZHUYIN_ANKI_DECK = "zhuyin-bopomofo-anki-deck"
ZHUYIN_SKOS_VOCABULARY = "zhuyin-bopomofo-vocabulary"
ZHUYIN_CROISSANT_DATASET = "zhuyin-bopomofo-ml-dataset"
ZHUYIN_DATA_PACKAGE = "zhuyin-bopomofo"
ZHUYIN_CSVW_PACKAGE = "zhuyin-bopomofo-csvw"
ZHUYIN_BAGIT_PACKAGE = "zhuyin-bopomofo-bagit"
ZHUYIN_OCFL_OBJECT = "zhuyin-bopomofo-ocfl"
ZHUYIN_IIIF_RESOURCE = "zhuyin-bopomofo-iiif-presentation-3"
ZHUYIN_RO_CRATE = "zhuyin-bopomofo-ro-crate"
ZHUYIN_METS_PREMIS = "zhuyin-bopomofo-mets2-premis3"
ZHUYIN_ORE = "zhuyin-bopomofo-oai-ore"
ZHUYIN_LDES = "zhuyin-bopomofo-ldes"
ZHUYIN_RESOURCE_SYNC = "zhuyin-bopomofo-resourcesync"
ZHUYIN_LMS_BANK = "zhuyin-bopomofo-lms-question-bank"
ZHUYIN_EPUB = "zhuyin-bopomofo-epub-reference"
ZHUYIN_LIBRARY_CATALOG = "zhuyin-bopomofo-library-catalog-records"
ZHUYIN_OER_METADATA = "zhuyin-bopomofo-oer-repository-metadata"
ZHUYIN_DCAT_CATALOG = "zhuyin-bopomofo-dcat3-open-data-catalog"
WORDMATE_LANGUAGE_DATASET = "wordmate-language-support"
WORDMATE_LANGUAGE_TOOL = "wordmate-44-language-support-checker"
PORTFOLIO_FINDER_DATASET = "verified-ios-app-finder-catalog"
PORTFOLIO_FINDER_TOOL = "private-pay-once-iphone-app-finder"
RESOURCE_SYNC_SOURCE = "https://alice51849.github.io/.well-known/resourcesync"

AI_BOTS = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "anthropic-ai",
           "Claude-Web", "PerplexityBot", "Perplexity-User", "Google-Extended",
           "Googlebot", "Bingbot", "Applebot", "Applebot-Extended", "CCBot",
           "Amazonbot", "Bytespider", "Meta-ExternalAgent", "DuckDuckBot",
           "cohere-ai", "YandexBot", "PetalBot"]

EXTERNAL_REPOS = [
    ("awesome-zhuyin-bopomofo-apps", "Zhuyin/Bopomofo learning apps for Taiwanese parents (Chinese)"),
    ("awesome-ios-language-learning", "Pay-once iOS language-learning apps"),
    ("awesome-toeic-pay-once-apps", "TOEIC study apps with one-time-purchase options (Japanese)"),
    ("awesome-ios-kids-learning", "Pay-once iOS kids-learning apps"),
    ("awesome-ios-photo-utilities", "Pay-once iOS photo utility apps"),
    ("awesome-ios-productivity", "Pay-once iOS productivity apps"),
    ("awesome-ios-money-budgeting", "Pay-once iOS money & budgeting apps"),
    ("awesome-ios-health-wellness", "Pay-once iOS health & wellness apps"),
    ("awesome-ios-for-students", "Pay-once iOS apps for students"),
    ("awesome-ios-everyday-utilities", "Pay-once iOS everyday utility apps"),
    ("awesome-ios-privacy-first", "Privacy-first iOS apps"),
    ("awesome-ios-pay-once", "Pay-once iOS apps"),
    ("awesome-pay-once-todo-apps", "Pay-once to-do & checklist apps"),
    ("open-reference-datasets", "Machine-readable CC BY 4.0 reference datasets"),
]


def wordmate_language_support_lines(*, full):
    """Describe the checker only after its canonical dataset exists."""
    if not os.path.exists(
        os.path.join(DATA_DIR, f"{WORDMATE_LANGUAGE_DATASET}.json")
    ):
        return []
    if full:
        return [
            "",
            "## Wordmate 44-language support dataset",
            f"- [Bilingual purchase-readiness checker]({SITE}/tools/{WORDMATE_LANGUAGE_TOOL}.html)",
            f"  - Traditional Chinese: {SITE}/zh-Hant/tools/{WORDMATE_LANGUAGE_TOOL}.html",
            f"  - JSON dataset: {SITE}/data/{WORDMATE_LANGUAGE_DATASET}.json",
            f"  - UTF-8 CSV: {SITE}/data/{WORDMATE_LANGUAGE_DATASET}.csv",
            f"  - W3C CSVW metadata: {SITE}/data/{WORDMATE_LANGUAGE_DATASET}.csv-metadata.json",
            f"  - JSON Schema: {SITE}/data/{WORDMATE_LANGUAGE_DATASET}.schema.json",
        ]
    return [
        "",
        "## Wordmate 44-language support dataset (CC BY 4.0)",
        f"- Bilingual purchase-readiness checker: {SITE}/tools/{WORDMATE_LANGUAGE_TOOL}.html",
        f"- Traditional Chinese edition: {SITE}/zh-Hant/tools/{WORDMATE_LANGUAGE_TOOL}.html",
        f"- JSON dataset: {SITE}/data/{WORDMATE_LANGUAGE_DATASET}.json",
        f"- UTF-8 CSV: {SITE}/data/{WORDMATE_LANGUAGE_DATASET}.csv",
        f"- W3C CSVW metadata: {SITE}/data/{WORDMATE_LANGUAGE_DATASET}.csv-metadata.json",
        f"- JSON Schema: {SITE}/data/{WORDMATE_LANGUAGE_DATASET}.schema.json",
    ]


def portfolio_finder_lines(*, full):
    """Describe the finder only after its verified catalogue exists."""
    if not os.path.exists(
        os.path.join(DATA_DIR, f"{PORTFOLIO_FINDER_DATASET}.json")
    ):
        return []
    if full:
        return [
            "",
            "## Verified independent iOS app finder",
            f"- [English private and pay-once finder]({SITE}/tools/{PORTFOLIO_FINDER_TOOL}.html)",
            f"- [Traditional Chinese finder]({SITE}/zh-Hant/tools/{PORTFOLIO_FINDER_TOOL}.html)",
            f"  - Agent-readable JSON: {SITE}/data/{PORTFOLIO_FINDER_DATASET}.json",
            f"  - JSON Schema: {SITE}/data/{PORTFOLIO_FINDER_DATASET}.schema.json",
            "  - Ordering: alphabetical; no paid, popularity or quality ranking",
        ]
    return [
        "",
        "## Verified independent iOS app finder (alphabetical, not ranked)",
        f"- English finder: {SITE}/tools/{PORTFOLIO_FINDER_TOOL}.html",
        f"- Traditional Chinese finder: {SITE}/zh-Hant/tools/{PORTFOLIO_FINDER_TOOL}.html",
        f"- Agent-readable JSON: {SITE}/data/{PORTFOLIO_FINDER_DATASET}.json",
        f"- JSON Schema: {SITE}/data/{PORTFOLIO_FINDER_DATASET}.schema.json",
    ]


def load_competitors():
    out = {}
    if os.path.exists(SOV):
        data = json.load(open(SOV, encoding="utf-8"))
        for r in data.get("results", []):
            out[r["key"]] = [disp(c) for c, _ in r.get("top_competitors", [])[:2]]
    return out


def positioning(key):
    profile = pricing_profile(key)
    bullets = " · ".join(APPS[key].get("cta_bullets", [])).lower()
    if profile == "free_to_start":
        return "Free to start. One-time unlock. No subscription."
    if profile == "free":
        return "Free." + (" No ads." if "no ads" in bullets else "")
    if profile == "pay_once":
        return "Paid once. No subscription."
    if profile == "flexible":
        return "Free to start. One-time and subscription options."
    return ""


def app_line(key, comps, live_keys):
    a = APPS[key]
    url = appstore_url(key)
    if not url or key not in live_keys:
        return None
    sub = (a.get("sub") or "").replace("\n", " ").strip()
    if sub and sub[-1] not in ".!?。!?":
        sub += "."                    # 補句號,讓 AI 正確斷句、乾淨引用
    position = positioning(key)
    if comps:
        adjective = (
            "A pay-once alternative"
            if pricing_profile(key) in {"pay_once", "free_to_start"}
            else "An independent alternative"
        )
        alt = f" {adjective} to {comps[0]}" + (f" and {comps[1]}" if len(comps) > 1 else "") + "."
    else:
        alt = ""
    return f"- [{a['name']}]({url}): {sub} {position}{alt}".replace("  ", " ").strip()


def build_llms(comp_map, live_keys):
    lines = [
        "# Lumi & friends — independent iOS apps",
        "",
        "> A catalog of independent iOS apps with privacy-first design and one-time-purchase "
        "options where stated. Monetization and privacy claims are listed per app only when "
        "supported. Apps not yet public on the App Store are omitted automatically.",
        "",
        "## Apps",
    ]
    cats = {}
    for k in APPS:
        cats.setdefault(APPS[k].get("category", "other"), []).append(k)
    label = {"productivity": "Productivity", "photo-utility": "Photo & utility",
             "finance": "Money & travel", "health": "Health",
             "travel": "Travel", "education": "Kids & learning",
             "sleep-sound": "Sleep & focus",
             "kids": "Kids & learning", "other": "More"}
    for cat, keys in cats.items():
        block = [app_line(k, comp_map.get(k, []), live_keys) for k in keys]
        block = [ln for ln in block if ln]          # 濾掉未上架(None),避免空類別標題
        if not block:
            continue
        lines.append(f"\n### {label.get(cat, cat)}")
        lines.extend(block)
    # alternatives 頁
    if os.path.isdir(ALT):
        alts = sorted(f for f in os.listdir(ALT) if f.endswith(".html") and f != "index.html")
        if alts:
            lines += ["", "## App alternatives (comparison pages)"]
            for f in alts:
                title = re.sub(r"[-_]", " ", f[:-5])
                lines.append(f"- [{title}]({SITE}/alternatives/{f})")
    # guides 頁(每 app 指南)
    if os.path.isdir(GUIDES):
        gds = sorted(f for f in os.listdir(GUIDES) if f.endswith(".html") and f != "index.html")
        if gds:
            lines += ["", "## App guides (how to choose + recommendation)"]
            for f in gds:
                title = re.sub(r"[-_]", " ", f[:-5])
                lines.append(f"- [{title}]({SITE}/guides/{f})")
    # open data 資料集(機器可讀,AI 引擎/Dataset Search 可引用)
    if os.path.isdir(DATA_DIR):
        ds = sorted(f for f in os.listdir(DATA_DIR) if f.endswith(".html") and f != "index.html")
        if ds:
            lines += ["", "## Open data (machine-readable, CC BY 4.0 — free to cite)"]
            for f in ds:
                title = re.sub(r"[-_]", " ", f[:-5])
                line = f"- [{title}]({SITE}/data/{f})"
                json_path = os.path.join(DATA_DIR, f"{f[:-5]}.json")
                if os.path.exists(json_path):
                    line += f" · JSON: {SITE}/data/{f[:-5]}.json"
                lines.append(line)
    lines += wordmate_language_support_lines(full=False)
    lines += portfolio_finder_lines(full=False)
    static_apis = [
        descriptor
        for descriptor in API_DESCRIPTORS
        if os.path.exists(
            os.path.join(
                API_DIR, "v1", descriptor["slug"], "openapi.json"
            )
        )
    ]
    if static_apis:
        lines += [
            "",
            "## Open static APIs (versioned, read-only, no API key)",
        ]
        for descriptor in static_apis:
            base = f"{SITE}/api/v1/{descriptor['slug']}"
            lines += [
                f"- {descriptor['title']}: {base}/",
                f"  - OpenAPI 3.1: {base}/openapi.json",
                f"  - API index: {base}/index.json",
            ]
    if os.path.exists(os.path.join(TOOLS, f"{FAMILY_TRAVEL_OER}.metadata.json")):
        opds2 = f"{SITE}/opds/{FAMILY_TRAVEL_OER}.json"
        opds1 = f"{SITE}/opds/{FAMILY_TRAVEL_OER}.xml"
        opds_lines = []
        if os.path.exists(os.path.join(PAGES, "opds", f"{FAMILY_TRAVEL_OER}.json")):
            opds_lines = [
                f"- OPDS 2.0 catalog: {opds2}",
                f"- OPDS 1.2 catalog: {opds1}",
            ]
        ro_crate_lines = []
        if os.path.exists(os.path.join(DATA_DIR, FAMILY_TRAVEL_RO_CRATE)):
            ro_crate_lines = [
                f"- RO-Crate 1.3 research object: {SITE}/data/{FAMILY_TRAVEL_RO_CRATE}"
            ]
        lines += [
            "",
            "## Open educational resources (CC BY 4.0)",
            f"- Family Travel Observation Passport: {SITE}/tools/{FAMILY_TRAVEL_OER}.html",
            f"- Traditional Chinese edition: {SITE}/zh-Hant/tools/{FAMILY_TRAVEL_OER}.html",
            f"- Machine-readable OER metadata: {SITE}/tools/{FAMILY_TRAVEL_OER}.metadata.json",
            f"- English A4 PDF: {SITE}/tools/{FAMILY_TRAVEL_OER}-en-a4.pdf",
            f"- Traditional Chinese A4 PDF: {SITE}/tools/{FAMILY_TRAVEL_OER}-zh-hant-a4.pdf",
            *ro_crate_lines,
            *opds_lines,
        ]
    if os.path.exists(os.path.join(TOOLS, f"{ZHUYIN_ANKI_DECK}.metadata.json")):
        lines += [
            "",
            "## Open Bopomofo flashcard imports (CC BY 4.0)",
            f"- English 37-symbol Anki deck: {SITE}/tools/{ZHUYIN_ANKI_DECK}.html",
            f"- Traditional Chinese edition: {SITE}/zh-Hant/tools/{ZHUYIN_ANKI_DECK}.html",
            f"- English UTF-8 TSV: {SITE}/tools/{ZHUYIN_ANKI_DECK}-en.tsv",
            f"- Traditional Chinese UTF-8 TSV: {SITE}/tools/{ZHUYIN_ANKI_DECK}-zh-hant.tsv",
            f"- LRMI / Schema.org metadata: {SITE}/tools/{ZHUYIN_ANKI_DECK}.metadata.json",
        ]
    if os.path.exists(
        os.path.join(DATA_DIR, f"{ZHUYIN_SKOS_VOCABULARY}.metadata.jsonld")
    ):
        lines += [
            "",
            "## Bopomofo linked open vocabulary (SKOS, CC BY 4.0)",
            f"- English landing page: {SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.html",
            f"- Traditional Chinese landing page: {SITE}/zh-Hant/data/{ZHUYIN_SKOS_VOCABULARY}.html",
            f"- JSON-LD 1.1: {SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.jsonld",
            f"- Turtle: {SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.ttl",
            f"- N-Triples: {SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.nt",
            f"- SHACL shapes: {SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.shacl.ttl",
            f"- DCAT 3 / VoID metadata: {SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(DATA_DIR, f"{ZHUYIN_CROISSANT_DATASET}.croissant.jsonld")
    ):
        lines += [
            "",
            "## Bopomofo AI/ML dataset (MLCommons Croissant 1.1, CC BY 4.0)",
            f"- English data card: {SITE}/data/{ZHUYIN_CROISSANT_DATASET}.html",
            f"- Traditional Chinese data card: {SITE}/zh-Hant/data/{ZHUYIN_CROISSANT_DATASET}.html",
            f"- UTF-8 CSV: {SITE}/data/{ZHUYIN_CROISSANT_DATASET}.csv",
            f"- JSON Lines: {SITE}/data/{ZHUYIN_CROISSANT_DATASET}.jsonl",
            f"- Croissant 1.1 JSON-LD: {SITE}/data/{ZHUYIN_CROISSANT_DATASET}.croissant.jsonld",
        ]
    if os.path.exists(
        os.path.join(DATA_DIR, "zhuyin-bopomofo-ml-dataset.csv-metadata.json")
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_CSVW_PACKAGE}"
        lines += [
            "",
            "## Bopomofo CSVW table metadata (W3C Recommendations)",
            f"- English guide: {package}/",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/packages/{ZHUYIN_CSVW_PACKAGE}/",
            f"- Canonical UTF-8 CSV: {SITE}/data/zhuyin-bopomofo-ml-dataset.csv",
            f"- Discoverable CSVW metadata: {SITE}/data/zhuyin-bopomofo-ml-dataset.csv-metadata.json",
            f"- Deterministic offline bundle: {package}/bopomofo-37-symbols-csvw-bundle.zip",
            f"- SHA-256 checksums: {package}/checksums-sha256.txt",
            f"- Dataset manifest: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_LDES,
            "bopomofo-event-stream.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_LDES}"
        lines += [
            "",
            "## Bopomofo LDES 1.0 + TREE event stream",
            f"- English guide: {package}/",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/packages/{ZHUYIN_LDES}/",
            f"- Canonical JSON-LD entry point: {package}/bopomofo-event-stream.jsonld",
            f"- Turtle discovery overview: {package}/bopomofo-event-stream.ttl",
            f"- SHACL member shape: {package}/bopomofo-event-member.shacl.ttl",
            f"- Deterministic bundle: {package}/bopomofo-37-symbols-ldes-tree.zip",
            f"- SHA-256 checksums: {package}/checksums-sha256.txt",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_BAGIT_PACKAGE,
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_BAGIT_PACKAGE}"
        lines += [
            "",
            "## Bopomofo digital-preservation package (RFC 8493 BagIt 1.0)",
            f"- English guide: {package}/",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/packages/{ZHUYIN_BAGIT_PACKAGE}/",
            f"- Deterministic BagIt ZIP: {package}/bopomofo-37-symbols-bagit-rfc8493.zip",
            f"- Outer SHA-256 checksum: {package}/checksums-sha256.txt",
            f"- Preservation package metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_OCFL_OBJECT,
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_OCFL_OBJECT}"
        lines += [
            "",
            "## Bopomofo version-aware preservation object (OCFL 1.1)",
            f"- English guide: {package}/",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/packages/{ZHUYIN_OCFL_OBJECT}/",
            f"- Deterministic OCFL object ZIP: {package}/bopomofo-37-symbols-ocfl-1.1.zip",
            f"- Outer SHA-256 checksum: {package}/checksums-sha256.txt",
            f"- Preservation object metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(PAGES, "iiif", "3", "bopomofo", "manifest.json")
    ):
        resource = f"{SITE}/iiif/3/bopomofo"
        lines += [
            "",
            "## Complete Bopomofo visual resource (IIIF Presentation API 3.0)",
            f"- English guide: {SITE}/data/{ZHUYIN_IIIF_RESOURCE}.html",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/{ZHUYIN_IIIF_RESOURCE}.html",
            f"- IIIF Collection: {resource}/collection.json",
            f"- IIIF Manifest with 37 ordered Canvases: {resource}/manifest.json",
            f"- Deterministic complete ZIP: {resource}/bopomofo-37-symbols-iiif-presentation-3.zip",
            f"- SHA-256 checksums: {resource}/checksums-sha256.txt",
            f"- App-independent metadata: {resource}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_RO_CRATE,
            "ro-crate-metadata.json",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_RO_CRATE}"
        lines += [
            "",
            "## Bopomofo RO-Crate 1.3 research object",
            f"- English guide: {package}/",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/packages/{ZHUYIN_RO_CRATE}/",
            f"- Attached deterministic ZIP: {package}/bopomofo-37-symbols-ro-crate-1.3.zip",
            f"- RO-Crate metadata: {package}/ro-crate-metadata.json",
            f"- Static crate preview: {package}/ro-crate-preview.html",
            f"- SHA-256 checksums: {package}/checksums-sha256.txt",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_METS_PREMIS,
            "mets.xml",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_METS_PREMIS}"
        lines += [
            "",
            "## Bopomofo METS 2.0 + PREMIS 3.0 preservation package",
            f"- English guide: {package}/",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/packages/{ZHUYIN_METS_PREMIS}/",
            f"- Deterministic transfer ZIP: {package}/bopomofo-37-symbols-mets2-premis3.zip",
            f"- METS 2.0 record: {package}/mets.xml",
            f"- PREMIS 3.0 record: {package}/premis.xml",
            f"- SHA-256 checksums: {package}/checksums-sha256.txt",
            f"- Package metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_ORE,
            "bopomofo-resource-map.ore.rdf",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_ORE}"
        lines += [
            "",
            "## Bopomofo OAI-ORE 1.0 compound-object Resource Map",
            f"- English guide: {package}/",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/packages/{ZHUYIN_ORE}/",
            f"- Authoritative RDF/XML Resource Map: {package}/bopomofo-resource-map.ore.rdf",
            f"- Aggregation hash URI: {package}/bopomofo-resource-map.ore.rdf#aggregation",
            f"- Turtle Resource Map: {package}/bopomofo-resource-map.ore.ttl",
            f"- JSON-LD Resource Map: {package}/bopomofo-resource-map.ore.jsonld",
            f"- Deterministic bundle: {package}/bopomofo-37-symbols-oai-ore-bundle.zip",
            f"- SHA-256 checksums: {package}/checksums-sha256.txt",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_DATA_PACKAGE,
            "datapackage.json",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_DATA_PACKAGE}"
        lines += [
            "",
            "## Bopomofo portable Data Package (Data Package 2.0, CC BY 4.0)",
            f"- English package guide: {package}/",
            f"- Traditional Chinese package guide: {SITE}/zh-Hant/data/packages/{ZHUYIN_DATA_PACKAGE}/",
            f"- Data Package descriptor: {package}/datapackage.json",
            f"- Table Schema 2.0: {package}/table-schema.json",
            f"- UTF-8 CSV: {package}/symbols.csv",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            "zhuyin-bopomofo-lms",
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/zhuyin-bopomofo-lms"
        lines += [
            "",
            "## Bopomofo LMS question bank (QTI 2.1 + Moodle XML, CC BY 4.0)",
            f"- English guide: {SITE}/data/{ZHUYIN_LMS_BANK}.html",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/{ZHUYIN_LMS_BANK}.html",
            f"- QTI 2.1 English package: {package}/bopomofo-qti-2.1-en.zip",
            f"- QTI 2.1 Traditional Chinese package: {package}/bopomofo-qti-2.1-zh-hant.zip",
            f"- Moodle XML English: {package}/bopomofo-moodle-en.xml",
            f"- Moodle XML Traditional Chinese: {package}/bopomofo-moodle-zh-hant.xml",
            f"- Answer key: {package}/answer-key.csv",
            f"- JSON-LD metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            "zhuyin-bopomofo-epub",
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/zhuyin-bopomofo-epub"
        publication = f"{SITE}/publications/bopomofo-37-symbol-reference"
        lines += [
            "",
            "## Accessible Bopomofo EPUB 3.3 reference (CC BY 4.0)",
            f"- English guide: {SITE}/data/{ZHUYIN_EPUB}.html",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/{ZHUYIN_EPUB}.html",
            f"- English EPUB 3.3: {package}/bopomofo-37-symbol-reference-en.epub",
            f"- Traditional Chinese EPUB 3.3: {package}/bopomofo-37-symbol-reference-zh-hant.epub",
            f"- English Readium manifest JSON file: {publication}/en/manifest.json",
            f"- Traditional Chinese Readium manifest JSON file: {publication}/zh-Hant/manifest.json",
            f"- OPDS 2.0 catalog JSON file: {SITE}/opds/bopomofo-37-symbol-reference.json",
            f"- OPDS 1.2 catalog Atom file: {SITE}/opds/bopomofo-37-symbol-reference.xml",
            f"- JSON-LD metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            "zhuyin-bopomofo-library",
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/zhuyin-bopomofo-library"
        lines += [
            "",
            "## Bopomofo EPUB library catalog records",
            f"- English guide: {SITE}/data/{ZHUYIN_LIBRARY_CATALOG}.html",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/{ZHUYIN_LIBRARY_CATALOG}.html",
            f"- Complete ZIP bundle: {package}/bopomofo-37-symbol-library-catalog-bundle.zip",
            f"- MARCXML: {package}/bopomofo-37-symbol-reference.marcxml.xml",
            f"- MODS 3.8: {package}/bopomofo-37-symbol-reference.mods.xml",
            f"- BIBFRAME 2.0 JSON-LD: {package}/bopomofo-37-symbol-reference.bibframe.jsonld",
            f"- BIBFRAME 2.0 Turtle: {package}/bopomofo-37-symbol-reference.bibframe.ttl",
            f"- Checksums and metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            "zhuyin-bopomofo-dcat3",
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/zhuyin-bopomofo-dcat3"
        lines += [
            "",
            "## Bopomofo DCAT 3 open-data catalog",
            f"- English guide: {SITE}/data/{ZHUYIN_DCAT_CATALOG}.html",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/{ZHUYIN_DCAT_CATALOG}.html",
            f"- Complete ZIP bundle: {package}/bopomofo-open-data-catalog-dcat3-bundle.zip",
            f"- DCAT 3 JSON-LD: {package}/bopomofo-open-data-catalog.dcat.jsonld",
            f"- DCAT 3 Turtle: {package}/bopomofo-open-data-catalog.dcat.ttl",
            f"- Checksums and metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            "zhuyin-bopomofo-oer",
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/zhuyin-bopomofo-oer"
        lines += [
            "",
            "## Bopomofo OER repository metadata (DCMI + LRMI)",
            f"- English guide: {SITE}/data/{ZHUYIN_OER_METADATA}.html",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/{ZHUYIN_OER_METADATA}.html",
            f"- Complete ZIP bundle: {package}/bopomofo-37-symbol-oer-metadata-bundle.zip",
            f"- English OAI-DC XML: {package}/bopomofo-37-symbol-reference-en.oai-dc.xml",
            f"- Traditional Chinese OAI-DC XML: {package}/bopomofo-37-symbol-reference-zh-hant.oai-dc.xml",
            f"- DCMI Terms JSON-LD: {package}/bopomofo-37-symbol-reference.dcmi-terms.jsonld",
            f"- LRMI JSON-LD: {package}/bopomofo-37-symbol-reference.lrmi.jsonld",
            f"- Checksums and metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(PAGES, "resourcesync", "resourcelist.xml")
    ):
        lines += [
            "",
            "## Bopomofo ResourceSync harvest feed (OAI ResourceSync 1.1)",
            f"- English guide: {SITE}/data/{ZHUYIN_RESOURCE_SYNC}.html",
            f"- Traditional Chinese guide: {SITE}/zh-Hant/data/{ZHUYIN_RESOURCE_SYNC}.html",
            f"- Well-known Source Description: {RESOURCE_SYNC_SOURCE}",
            f"- Capability List: {SITE}/resourcesync/capabilitylist.xml",
            f"- Complete Resource List with SHA-256: {SITE}/resourcesync/resourcelist.xml",
            f"- Collection JSON-LD: {SITE}/resourcesync/bopomofo-collection.jsonld",
        ]
    # 外部 curated 清單與資料集(GitHub;已實測會被 AI 引用的來源,讓爬蟲從站也能發現整個 repo 生態)
    ghbase = "https://github.com/alice51849"
    lines += ["", "## External curated lists & datasets (GitHub, CC0/CC BY — free to cite)"]
    for name, d in EXTERNAL_REPOS:
        lines.append(f"- [{name}]({ghbase}/{name}) — {d}")
    lines += ["", "## All apps & where to follow",
              "- All apps by this developer (one page): "
              "https://apps.apple.com/developer/id1136144960",
              "- Telegram channel (free tools + app updates): https://t.me/LumiApps2026",
              f"- Full crawler index (all apps, comparison pages, datasets, multilingual hubs): {SITE}/llms-full.txt"]
    lines += ["", "## RFC 9264 Web Linkset",
              f"- App relationship graph: {SITE}/linkset.json",
              f"- Linkset sitemap: {SITE}/sitemap_linkset.xml",
              "", "## Social preview and oEmbed discovery",
              f"- oEmbed endpoint sitemap: {SITE}/sitemap_oembed.xml",
              "", "## Sitemaps",
              f"- {SITE}/sitemap.xml", f"- {SITE}/sitemap_alternatives.xml",
              f"- {SITE}/sitemap_answers.xml",
              "", "## Featured: escape subscriptions (pay-once swaps)",
              f"- {SITE}/subscription-swap.html — real 5-year cost of popular subscription apps "
              "vs the one-time-purchase iPhone app that replaces each.",
              "", "## Latest updates (syndication feeds)",
              f"- Atom: {SITE}/feed.xml",
              f"- RSS 2.0: {SITE}/rss.xml",
              f"- JSON Feed 1.1: {SITE}/feed.json",
              "- Real-time updates: independent WebSub hubs advertised inside "
              "every feed:"]
    lines.extend(f"  - {hub}" for hub in WEBSUB_HUBS)
    lines += [
        "- RSS real-time updates: rssCloud discovery is advertised in RSS 2.0:",
        f"  - {RSSCLOUD_NOTIFY_URL}",
        f"  - {RSSCLOUD_WEBSUB_HUB}",
    ]
    lines.append("")
    return "\n".join(lines)


def _resource_files(directory, live_keys, prefix):
    if not os.path.isdir(directory):
        return []
    inactive = set(APPS) - set(live_keys)
    rows = []
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".html") or filename == "index.html":
            continue
        stem = filename[:-5]
        if stem in inactive or any(stem.startswith(key + "-") for key in inactive):
            continue
        title = re.sub(r"[-_]", " ", stem)
        rows.append((title, f"{SITE}/{prefix}/{filename}"))
    return rows


def _localized_app_guides(key):
    if not os.path.isdir(PAGES):
        return []
    rows = []
    for locale in sorted(os.listdir(PAGES)):
        if locale == "en-US" or not re.fullmatch(
            r"[a-z]{2}(?:-(?:[A-Z]{2}|[A-Z][a-z]{3}))?", locale
        ):
            continue
        if os.path.isfile(os.path.join(PAGES, locale, f"{key}.html")):
            rows.append((locale, f"{SITE}/{locale}/{key}.html"))
    return rows


def build_llms_full(comp_map, live_keys):
    lines = [
        "# Lumi & friends — full AI crawler index",
        "",
        "> Machine-readable map of currently public independent iOS apps and their owned "
        "guides, comparisons, tools, datasets, visual stories, localized catalogs, and "
        "external citation sources. App Store availability is verified against Apple's "
        "public lookup service; unavailable apps are omitted.",
        "",
        "## Crawl entry points",
    ]
    entry_points = [
        ("English app catalog", "apps/index.html"),
        ("Traditional Chinese app catalog", "apps/zh-Hant/index.html"),
        ("Japanese app catalog", "apps/ja/index.html"),
        ("App topic hubs", "hubs/index.html"),
        ("High-intent answers", "answers/index.html"),
        ("Comparison pages", "alternatives/index.html"),
        ("Visual stories", "stories/index.html"),
        ("Open data", "data/index.html"),
        ("Open static APIs", "api/index.html"),
        (
            "Bopomofo ResourceSync feed",
            f"data/{ZHUYIN_RESOURCE_SYNC}.html",
        ),
        (
            "Bopomofo IIIF Presentation API 3 visual resource",
            f"data/{ZHUYIN_IIIF_RESOURCE}.html",
        ),
        (
            "Bopomofo RO-Crate 1.3 research object",
            f"data/packages/{ZHUYIN_RO_CRATE}/",
        ),
        (
            "Bopomofo METS 2.0 and PREMIS 3.0 preservation package",
            f"data/packages/{ZHUYIN_METS_PREMIS}/",
        ),
        (
            "Bopomofo LDES 1.0 and TREE event stream",
            f"data/packages/{ZHUYIN_LDES}/",
        ),
        (
            "Bopomofo OAI-ORE 1.0 compound-object Resource Map",
            f"data/packages/{ZHUYIN_ORE}/",
        ),
        (
            "Bopomofo LMS question bank",
            f"data/{ZHUYIN_LMS_BANK}.html",
        ),
        (
            "Accessible Bopomofo EPUB and downloadable catalog files",
            f"data/{ZHUYIN_EPUB}.html",
        ),
        (
            "Bopomofo EPUB library catalog records",
            f"data/{ZHUYIN_LIBRARY_CATALOG}.html",
        ),
        (
            "Bopomofo OER repository metadata",
            f"data/{ZHUYIN_OER_METADATA}.html",
        ),
        (
            "Bopomofo DCAT 3 open-data catalog",
            f"data/{ZHUYIN_DCAT_CATALOG}.html",
        ),
        ("Free tools", "tools/index.html"),
    ]
    for title, rel in entry_points:
        if os.path.exists(os.path.join(PAGES, rel)):
            lines.append(f"- [{title}]({SITE}/{rel})")

    lines += ["", "## Public apps"]
    cats = {}
    for key in APPS:
        if key in live_keys:
            cats.setdefault(APPS[key].get("category", "other"), []).append(key)
    labels = {
        "productivity": "Productivity",
        "photo-utility": "Photo & utility",
        "finance": "Money & travel",
        "travel": "Travel",
        "sleep-sound": "Sleep & focus",
        "health": "Health",
        "education": "Education",
        "kids": "Kids & learning",
        "lifestyle": "Lifestyle",
        "other": "More",
    }
    for category, keys in cats.items():
        lines += ["", f"### {labels.get(category, category)}"]
        for key in keys:
            app = APPS[key]
            sub = (app.get("sub") or app.get("tag") or "").replace("\n", " ").strip()
            facts = list(dict.fromkeys(
                value for value in [app.get("tag", "")] + app.get("cta_bullets", [])
                if value
            ))
            lines += [
                "",
                f"#### {app['name']}",
                f"- Summary: {sub}",
                f"- App Store: {appstore_url(key)}",
            ]
            if facts:
                lines.append(f"- Supported positioning: {'; '.join(facts)}")
            detail = os.path.join(PAGES, "en-US", f"{key}.html")
            if os.path.exists(detail):
                lines.append(f"- Canonical app guide: {SITE}/en-US/{key}.html")
            localized_guides = _localized_app_guides(key)
            if localized_guides:
                lines.append("- Localized app guides:")
                lines.extend(
                    f"  - [{locale}]({url})"
                    for locale, url in localized_guides
                )
            hub = os.path.join(PAGES, "hubs", f"{key}.html")
            if os.path.exists(hub):
                lines.append(f"- Topic hub: {SITE}/hubs/{key}.html")
            comps = comp_map.get(key, [])
            if comps:
                lines.append(f"- Comparison context: {', '.join(comps)}")
            alternatives = _resource_files(ALT, {key}, "alternatives")
            alternatives = [row for row in alternatives if row[0].replace(" ", "-").startswith(key + "-")]
            for title, url in alternatives:
                lines.append(f"- Comparison: [{title}]({url})")

    resource_sections = [
        ("Guides", GUIDES, "guides"),
        ("Free interactive tools", TOOLS, "tools"),
        ("Open reference data", DATA_DIR, "data"),
        ("Visual stories", STORIES, "stories"),
        ("Comparison library", ALT, "alternatives"),
    ]
    for heading, directory, prefix in resource_sections:
        resources = _resource_files(directory, live_keys, prefix)
        if not resources:
            continue
        lines += ["", f"## {heading}"]
        for title, url in resources:
            lines.append(f"- [{title}]({url})")
            if prefix == "data":
                json_path = os.path.join(directory, os.path.basename(url)[:-5] + ".json")
                if os.path.exists(json_path):
                    lines.append(f"  - JSON: {url[:-5]}.json")

    static_apis = [
        descriptor
        for descriptor in API_DESCRIPTORS
        if os.path.exists(
            os.path.join(
                API_DIR, "v1", descriptor["slug"], "openapi.json"
            )
        )
    ]
    if static_apis:
        lines += [
            "",
            "## Open static APIs",
        ]
        for descriptor in static_apis:
            api_directory = os.path.join(
                API_DIR, "v1", descriptor["slug"]
            )
            base = f"{SITE}/api/v1/{descriptor['slug']}"
            lines += [
                f"- [{descriptor['title']}]({base}/)",
                f"  - OpenAPI 3.1: {base}/openapi.json",
                f"  - API index: {base}/index.json",
            ]
            for filename in sorted(
                name
                for name in os.listdir(api_directory)
                if name.endswith(".schema.json")
            ):
                lines.append(f"  - JSON Schema: {base}/{filename}")
    lines += wordmate_language_support_lines(full=True)
    lines += portfolio_finder_lines(full=True)
    if os.path.exists(os.path.join(TOOLS, f"{FAMILY_TRAVEL_OER}.metadata.json")):
        opds2 = f"{SITE}/opds/{FAMILY_TRAVEL_OER}.json"
        opds1 = f"{SITE}/opds/{FAMILY_TRAVEL_OER}.xml"
        opds_lines = []
        if os.path.exists(os.path.join(PAGES, "opds", f"{FAMILY_TRAVEL_OER}.json")):
            opds_lines = [
                f"  - OPDS 2.0 catalog: {opds2}",
                f"  - OPDS 1.2 catalog: {opds1}",
            ]
        ro_crate_lines = []
        if os.path.exists(os.path.join(DATA_DIR, FAMILY_TRAVEL_RO_CRATE)):
            ro_crate_lines = [
                f"  - RO-Crate 1.3 research object: {SITE}/data/{FAMILY_TRAVEL_RO_CRATE}"
            ]
        lines += [
            "",
            "## Open educational resources",
            f"- [Family Travel Observation Passport]({SITE}/tools/{FAMILY_TRAVEL_OER}.html)",
            f"  - Traditional Chinese: {SITE}/zh-Hant/tools/{FAMILY_TRAVEL_OER}.html",
            f"  - OER metadata: {SITE}/tools/{FAMILY_TRAVEL_OER}.metadata.json",
            f"  - English A4 PDF: {SITE}/tools/{FAMILY_TRAVEL_OER}-en-a4.pdf",
            f"  - English US Letter PDF: {SITE}/tools/{FAMILY_TRAVEL_OER}-en-letter.pdf",
            f"  - Traditional Chinese A4 PDF: {SITE}/tools/{FAMILY_TRAVEL_OER}-zh-hant-a4.pdf",
            f"  - Traditional Chinese US Letter PDF: {SITE}/tools/{FAMILY_TRAVEL_OER}-zh-hant-letter.pdf",
            *ro_crate_lines,
            *opds_lines,
        ]
    if os.path.exists(os.path.join(TOOLS, f"{ZHUYIN_ANKI_DECK}.metadata.json")):
        lines += [
            "",
            "## Open Bopomofo flashcard imports",
            f"- [English 37-symbol Anki deck]({SITE}/tools/{ZHUYIN_ANKI_DECK}.html)",
            f"  - English UTF-8 TSV: {SITE}/tools/{ZHUYIN_ANKI_DECK}-en.tsv",
            f"- [Traditional Chinese edition]({SITE}/zh-Hant/tools/{ZHUYIN_ANKI_DECK}.html)",
            f"  - Traditional Chinese UTF-8 TSV: {SITE}/tools/{ZHUYIN_ANKI_DECK}-zh-hant.tsv",
            f"- LRMI / Schema.org metadata: {SITE}/tools/{ZHUYIN_ANKI_DECK}.metadata.json",
        ]
    if os.path.exists(
        os.path.join(DATA_DIR, f"{ZHUYIN_SKOS_VOCABULARY}.metadata.jsonld")
    ):
        lines += [
            "",
            "## Bopomofo linked open vocabulary",
            f"- [English SKOS vocabulary]({SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.html)",
            f"- [Traditional Chinese edition]({SITE}/zh-Hant/data/{ZHUYIN_SKOS_VOCABULARY}.html)",
            f"  - JSON-LD 1.1: {SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.jsonld",
            f"  - Turtle: {SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.ttl",
            f"  - N-Triples: {SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.nt",
            f"  - SHACL: {SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.shacl.ttl",
            f"  - DCAT 3 / VoID: {SITE}/data/{ZHUYIN_SKOS_VOCABULARY}.metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(DATA_DIR, f"{ZHUYIN_CROISSANT_DATASET}.croissant.jsonld")
    ):
        lines += [
            "",
            "## Bopomofo AI/ML dataset",
            f"- [English Croissant data card]({SITE}/data/{ZHUYIN_CROISSANT_DATASET}.html)",
            f"- [Traditional Chinese data card]({SITE}/zh-Hant/data/{ZHUYIN_CROISSANT_DATASET}.html)",
            f"  - UTF-8 CSV: {SITE}/data/{ZHUYIN_CROISSANT_DATASET}.csv",
            f"  - JSON Lines: {SITE}/data/{ZHUYIN_CROISSANT_DATASET}.jsonl",
            f"  - MLCommons Croissant 1.1: {SITE}/data/{ZHUYIN_CROISSANT_DATASET}.croissant.jsonld",
        ]
    if os.path.exists(
        os.path.join(DATA_DIR, "zhuyin-bopomofo-ml-dataset.csv-metadata.json")
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_CSVW_PACKAGE}"
        lines += [
            "",
            "## Bopomofo CSVW table metadata",
            f"- [English guide]({package}/)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/packages/{ZHUYIN_CSVW_PACKAGE}/)",
            f"  - Canonical UTF-8 CSV: {SITE}/data/zhuyin-bopomofo-ml-dataset.csv",
            f"  - Discoverable CSVW metadata: {SITE}/data/zhuyin-bopomofo-ml-dataset.csv-metadata.json",
            f"  - Deterministic offline bundle: {package}/bopomofo-37-symbols-csvw-bundle.zip",
            f"  - SHA-256 checksums: {package}/checksums-sha256.txt",
            f"  - Dataset manifest: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_LDES,
            "bopomofo-event-stream.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_LDES}"
        lines += [
            "",
            "## Bopomofo LDES 1.0 + TREE event stream",
            f"- [English guide]({package}/)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/packages/{ZHUYIN_LDES}/)",
            f"  - Canonical JSON-LD entry point: {package}/bopomofo-event-stream.jsonld",
            f"  - Turtle discovery overview: {package}/bopomofo-event-stream.ttl",
            f"  - SHACL member shape: {package}/bopomofo-event-member.shacl.ttl",
            f"  - Deterministic bundle: {package}/bopomofo-37-symbols-ldes-tree.zip",
            f"  - SHA-256 checksums: {package}/checksums-sha256.txt",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_BAGIT_PACKAGE,
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_BAGIT_PACKAGE}"
        lines += [
            "",
            "## Bopomofo RFC 8493 BagIt preservation package",
            f"- [English guide]({package}/)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/packages/{ZHUYIN_BAGIT_PACKAGE}/)",
            f"  - Deterministic BagIt ZIP: {package}/bopomofo-37-symbols-bagit-rfc8493.zip",
            f"  - Outer SHA-256 checksum: {package}/checksums-sha256.txt",
            f"  - Preservation package metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_OCFL_OBJECT,
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_OCFL_OBJECT}"
        lines += [
            "",
            "## Bopomofo OCFL 1.1 preservation object",
            f"- [English guide]({package}/)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/packages/{ZHUYIN_OCFL_OBJECT}/)",
            f"  - Deterministic OCFL object ZIP: {package}/bopomofo-37-symbols-ocfl-1.1.zip",
            f"  - Outer SHA-256 checksum: {package}/checksums-sha256.txt",
            f"  - Preservation object metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(PAGES, "iiif", "3", "bopomofo", "manifest.json")
    ):
        resource = f"{SITE}/iiif/3/bopomofo"
        lines += [
            "",
            "## Complete Bopomofo IIIF Presentation API 3 visual resource",
            f"- [English guide]({SITE}/data/{ZHUYIN_IIIF_RESOURCE}.html)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/{ZHUYIN_IIIF_RESOURCE}.html)",
            f"  - IIIF Collection: {resource}/collection.json",
            f"  - IIIF Manifest with 37 ordered Canvases: {resource}/manifest.json",
            f"  - Deterministic complete ZIP: {resource}/bopomofo-37-symbols-iiif-presentation-3.zip",
            f"  - SHA-256 checksums: {resource}/checksums-sha256.txt",
            f"  - App-independent metadata: {resource}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_RO_CRATE,
            "ro-crate-metadata.json",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_RO_CRATE}"
        lines += [
            "",
            "## Bopomofo RO-Crate 1.3 research object",
            f"- [English guide]({package}/)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/packages/{ZHUYIN_RO_CRATE}/)",
            f"  - Attached deterministic ZIP: {package}/bopomofo-37-symbols-ro-crate-1.3.zip",
            f"  - RO-Crate metadata: {package}/ro-crate-metadata.json",
            f"  - Static crate preview: {package}/ro-crate-preview.html",
            f"  - SHA-256 checksums: {package}/checksums-sha256.txt",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_METS_PREMIS,
            "mets.xml",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_METS_PREMIS}"
        lines += [
            "",
            "## Bopomofo METS 2.0 + PREMIS 3.0 preservation package",
            f"- [English guide]({package}/)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/packages/{ZHUYIN_METS_PREMIS}/)",
            f"  - Deterministic transfer ZIP: {package}/bopomofo-37-symbols-mets2-premis3.zip",
            f"  - METS 2.0 record: {package}/mets.xml",
            f"  - PREMIS 3.0 record: {package}/premis.xml",
            f"  - SHA-256 checksums: {package}/checksums-sha256.txt",
            f"  - Package metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_ORE,
            "bopomofo-resource-map.ore.rdf",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_ORE}"
        lines += [
            "",
            "## Bopomofo OAI-ORE 1.0 compound-object Resource Map",
            f"- [English guide]({package}/)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/packages/{ZHUYIN_ORE}/)",
            f"  - Authoritative RDF/XML Resource Map: {package}/bopomofo-resource-map.ore.rdf",
            f"  - Aggregation hash URI: {package}/bopomofo-resource-map.ore.rdf#aggregation",
            f"  - Turtle Resource Map: {package}/bopomofo-resource-map.ore.ttl",
            f"  - JSON-LD Resource Map: {package}/bopomofo-resource-map.ore.jsonld",
            f"  - Deterministic bundle: {package}/bopomofo-37-symbols-oai-ore-bundle.zip",
            f"  - SHA-256 checksums: {package}/checksums-sha256.txt",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            ZHUYIN_DATA_PACKAGE,
            "datapackage.json",
        )
    ):
        package = f"{SITE}/data/packages/{ZHUYIN_DATA_PACKAGE}"
        lines += [
            "",
            "## Bopomofo portable Data Package",
            f"- [English Data Package guide]({package}/)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/packages/{ZHUYIN_DATA_PACKAGE}/)",
            f"  - Data Package 2.0 descriptor: {package}/datapackage.json",
            f"  - Table Schema 2.0: {package}/table-schema.json",
            f"  - UTF-8 CSV: {package}/symbols.csv",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            "zhuyin-bopomofo-lms",
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/zhuyin-bopomofo-lms"
        lines += [
            "",
            "## Bopomofo LMS question bank",
            f"- [English guide]({SITE}/data/{ZHUYIN_LMS_BANK}.html)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/{ZHUYIN_LMS_BANK}.html)",
            f"  - QTI 2.1 English: {package}/bopomofo-qti-2.1-en.zip",
            f"  - QTI 2.1 Traditional Chinese: {package}/bopomofo-qti-2.1-zh-hant.zip",
            f"  - Moodle XML English: {package}/bopomofo-moodle-en.xml",
            f"  - Moodle XML Traditional Chinese: {package}/bopomofo-moodle-zh-hant.xml",
            f"  - CSV answer key: {package}/answer-key.csv",
            f"  - JSON-LD metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            "zhuyin-bopomofo-epub",
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/zhuyin-bopomofo-epub"
        publication = f"{SITE}/publications/bopomofo-37-symbol-reference"
        lines += [
            "",
            "## Accessible Bopomofo EPUB and downloadable catalog files",
            f"- [English guide]({SITE}/data/{ZHUYIN_EPUB}.html)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/{ZHUYIN_EPUB}.html)",
            f"  - English EPUB 3.3: {package}/bopomofo-37-symbol-reference-en.epub",
            f"  - Traditional Chinese EPUB 3.3: {package}/bopomofo-37-symbol-reference-zh-hant.epub",
            f"  - English Readium manifest JSON file: {publication}/en/manifest.json",
            f"  - Traditional Chinese Readium manifest JSON file: {publication}/zh-Hant/manifest.json",
            f"  - OPDS 2.0 catalog JSON file: {SITE}/opds/bopomofo-37-symbol-reference.json",
            f"  - OPDS 1.2 catalog Atom file: {SITE}/opds/bopomofo-37-symbol-reference.xml",
            f"  - JSON-LD metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            "zhuyin-bopomofo-library",
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/zhuyin-bopomofo-library"
        lines += [
            "",
            "## Bopomofo EPUB library catalog records",
            f"- [English guide]({SITE}/data/{ZHUYIN_LIBRARY_CATALOG}.html)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/{ZHUYIN_LIBRARY_CATALOG}.html)",
            f"  - Complete ZIP bundle: {package}/bopomofo-37-symbol-library-catalog-bundle.zip",
            f"  - MARCXML: {package}/bopomofo-37-symbol-reference.marcxml.xml",
            f"  - MODS 3.8: {package}/bopomofo-37-symbol-reference.mods.xml",
            f"  - BIBFRAME 2.0 JSON-LD: {package}/bopomofo-37-symbol-reference.bibframe.jsonld",
            f"  - BIBFRAME 2.0 Turtle: {package}/bopomofo-37-symbol-reference.bibframe.ttl",
            f"  - Checksums and metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            "zhuyin-bopomofo-dcat3",
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/zhuyin-bopomofo-dcat3"
        lines += [
            "",
            "## Bopomofo DCAT 3 open-data catalog",
            f"- [English guide]({SITE}/data/{ZHUYIN_DCAT_CATALOG}.html)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/{ZHUYIN_DCAT_CATALOG}.html)",
            f"  - Complete ZIP bundle: {package}/bopomofo-open-data-catalog-dcat3-bundle.zip",
            f"  - DCAT 3 JSON-LD: {package}/bopomofo-open-data-catalog.dcat.jsonld",
            f"  - DCAT 3 Turtle: {package}/bopomofo-open-data-catalog.dcat.ttl",
            f"  - Checksums and metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(
            DATA_DIR,
            "packages",
            "zhuyin-bopomofo-oer",
            "metadata.jsonld",
        )
    ):
        package = f"{SITE}/data/packages/zhuyin-bopomofo-oer"
        lines += [
            "",
            "## Bopomofo OER repository metadata",
            f"- [English guide]({SITE}/data/{ZHUYIN_OER_METADATA}.html)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/{ZHUYIN_OER_METADATA}.html)",
            f"  - Complete ZIP bundle: {package}/bopomofo-37-symbol-oer-metadata-bundle.zip",
            f"  - English OAI-DC XML: {package}/bopomofo-37-symbol-reference-en.oai-dc.xml",
            f"  - Traditional Chinese OAI-DC XML: {package}/bopomofo-37-symbol-reference-zh-hant.oai-dc.xml",
            f"  - DCMI Terms JSON-LD: {package}/bopomofo-37-symbol-reference.dcmi-terms.jsonld",
            f"  - LRMI JSON-LD: {package}/bopomofo-37-symbol-reference.lrmi.jsonld",
            f"  - Checksums and metadata: {package}/metadata.jsonld",
        ]
    if os.path.exists(
        os.path.join(PAGES, "resourcesync", "resourcelist.xml")
    ):
        lines += [
            "",
            "## Bopomofo ResourceSync harvest feed",
            f"- [English guide]({SITE}/data/{ZHUYIN_RESOURCE_SYNC}.html)",
            f"- [Traditional Chinese guide]({SITE}/zh-Hant/data/{ZHUYIN_RESOURCE_SYNC}.html)",
            f"- Source Description: {RESOURCE_SYNC_SOURCE}",
            f"- Capability List: {SITE}/resourcesync/capabilitylist.xml",
            f"- Resource List: {SITE}/resourcesync/resourcelist.xml",
            f"- Collection JSON-LD: {SITE}/resourcesync/bopomofo-collection.jsonld",
        ]

    locale_hubs = []
    for name in sorted(os.listdir(PAGES)):
        if not re.fullmatch(r"[a-z]{2}(?:-(?:[A-Z]{2}|[A-Z][a-z]{3}))?", name):
            continue
        if os.path.exists(os.path.join(PAGES, name, "index.html")):
            locale_hubs.append((name, f"{SITE}/{name}/index.html"))
    if locale_hubs:
        lines += ["", "## Localized catalog hubs"]
        lines.extend(f"- [{locale}]({url})" for locale, url in locale_hubs)

    lines += ["", "## External curated lists and datasets"]
    for name, description in EXTERNAL_REPOS:
        lines.append(f"- [{name}](https://github.com/alice51849/{name}) — {description}")

    lines += ["", "## Sitemaps and feed"]
    for filename in (
        "sitemap_index.xml", "sitemap.xml", "sitemap_alternatives.xml",
        "sitemap_answers.xml", "sitemap_guides.xml", "sitemap_apps.xml",
        "sitemap_stories.xml",
        "sitemap_images.xml", "sitemap_linkset.xml", "sitemap_oembed.xml",
        "linkset.json",
        "sitemap_hubs.xml", "sitemap_tools.xml", "sitemap_data.xml",
        "sitemap_api.xml", "sitemap_swap.xml", "feed.xml", "rss.xml", "feed.json",
        "sitemap_opds.xml", "sitemap_ro_crate.xml",
        "sitemap_anki.xml",
        "sitemap_vocab.xml",
        "sitemap_croissant.xml",
        "sitemap_datapackage.xml",
        "sitemap_csvw.xml",
        "sitemap_bagit.xml",
        "sitemap_ocfl.xml",
        "sitemap_iiif.xml",
        "sitemap_ro_crate_bopomofo.xml",
        "sitemap_mets_premis.xml",
        "sitemap_ldes.xml",
        "sitemap_ore.xml",
        "sitemap_lms.xml",
        "sitemap_epub.xml",
        "sitemap_library_catalog.xml",
        "sitemap_oer_metadata.xml",
        "sitemap_dcat.xml",
        "sitemap_resourcesync.xml",
        "resourcesync/resourcelist.xml",
    ):
        if os.path.exists(os.path.join(PAGES, filename)):
            lines.append(f"- {SITE}/{filename}")
    lines.extend(
        f"- WebSub real-time hub: {hub} "
        "(topic URLs are advertised inside all three feeds)"
        for hub in WEBSUB_HUBS
    )
    lines += [
        f"- rssCloud subscriber registration: {RSSCLOUD_NOTIFY_URL}",
        f"- rssCloud WebSub hub: {RSSCLOUD_WEBSUB_HUB}",
    ]
    lines.append("")
    return "\n".join(lines)


def build_robots():
    out = ["# AI assistants and search crawlers are welcome to index and cite this site.", ""]
    for bot in AI_BOTS:
        out.append(f"User-agent: {bot}")
        out.append("Allow: /")
        out.append("")
    out += ["User-agent: *", "Allow: /", "",
            f"Sitemap: {SITE}/sitemap.xml",
            f"Sitemap: {SITE}/sitemap_alternatives.xml",
            f"Sitemap: {SITE}/sitemap_answers.xml",
            f"Sitemap: {SITE}/sitemap_guides.xml",
            f"Sitemap: {SITE}/sitemap_apps.xml",
            f"Sitemap: {SITE}/sitemap_stories.xml",
            f"Sitemap: {SITE}/sitemap_images.xml",
            f"Sitemap: {SITE}/sitemap_linkset.xml",
            f"Sitemap: {SITE}/sitemap_oembed.xml",
            f"Sitemap: {SITE}/sitemap_hubs.xml",
            f"Sitemap: {SITE}/sitemap_tools.xml",
            f"Sitemap: {SITE}/sitemap_data.xml",
            f"Sitemap: {SITE}/sitemap_api.xml",
            f"Sitemap: {SITE}/sitemap_swap.xml",
            f"Sitemap: {SITE}/sitemap_opds.xml",
            f"Sitemap: {SITE}/sitemap_ro_crate.xml",
            f"Sitemap: {SITE}/sitemap_anki.xml",
            f"Sitemap: {SITE}/sitemap_vocab.xml",
            f"Sitemap: {SITE}/sitemap_croissant.xml",
            f"Sitemap: {SITE}/sitemap_datapackage.xml",
            f"Sitemap: {SITE}/sitemap_csvw.xml",
            f"Sitemap: {SITE}/sitemap_bagit.xml",
            f"Sitemap: {SITE}/sitemap_ocfl.xml",
            f"Sitemap: {SITE}/sitemap_iiif.xml",
            f"Sitemap: {SITE}/sitemap_ro_crate_bopomofo.xml",
            f"Sitemap: {SITE}/sitemap_mets_premis.xml",
            f"Sitemap: {SITE}/sitemap_ldes.xml",
            f"Sitemap: {SITE}/sitemap_ore.xml",
            f"Sitemap: {SITE}/sitemap_lms.xml",
            f"Sitemap: {SITE}/sitemap_epub.xml",
            f"Sitemap: {SITE}/sitemap_library_catalog.xml",
            f"Sitemap: {SITE}/sitemap_oer_metadata.xml",
            f"Sitemap: {SITE}/sitemap_dcat.xml",
            f"Sitemap: {SITE}/sitemap_resourcesync.xml",
            f"Sitemap: {SITE}/resourcesync/resourcelist.xml",
            f"Sitemap: {SITE}/sitemap_index.xml", ""]
    return "\n".join(out)


def build_sitemap_index():
    maps = ["sitemap.xml", "sitemap_alternatives.xml", "sitemap_answers.xml",
            "sitemap_guides.xml", "sitemap_apps.xml",
            "sitemap_stories.xml", "sitemap_images.xml", "sitemap_linkset.xml",
            "sitemap_oembed.xml",
            "sitemap_hubs.xml", "sitemap_tools.xml",
            "sitemap_data.xml", "sitemap_api.xml", "sitemap_swap.xml"]
    maps.extend([
        "sitemap_opds.xml",
        "sitemap_ro_crate.xml",
        "sitemap_anki.xml",
        "sitemap_vocab.xml",
        "sitemap_croissant.xml",
        "sitemap_datapackage.xml",
        "sitemap_csvw.xml",
        "sitemap_bagit.xml",
        "sitemap_ocfl.xml",
        "sitemap_iiif.xml",
        "sitemap_ro_crate_bopomofo.xml",
        "sitemap_mets_premis.xml",
        "sitemap_ldes.xml",
        "sitemap_ore.xml",
        "sitemap_lms.xml",
        "sitemap_epub.xml",
        "sitemap_library_catalog.xml",
        "sitemap_oer_metadata.xml",
        "sitemap_dcat.xml",
        "sitemap_resourcesync.xml",
        "resourcesync/resourcelist.xml",
    ])
    items = "\n".join(f"  <sitemap><loc>{SITE}/{m}</loc></sitemap>" for m in maps
                      if os.path.exists(os.path.join(PAGES, m)))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + items + "\n</sitemapindex>\n")


def publish(urls):
    def run(cmd, cwd=None):
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        print((r.stdout + r.stderr).strip()[-500:]); return r
    run(["git", "add", "-A"], cwd=PAGES)
    st = subprocess.run(["git", "status", "--porcelain"], cwd=PAGES, capture_output=True, text=True)
    if not st.stdout.strip():
        print("無變更。"); return
    run(["git", "-c", "user.name=alice51849", "-c", "user.email=alice51849@users.noreply.github.com",
         "commit", "-m", "Add llms.txt + AI-crawler robots + sitemap index (top-tier AEO)"], cwd=PAGES)
    run(["git", "-c", "credential.helper=!gh auth git-credential", "push", "-q", "origin", "main"], cwd=PAGES)
    try:
        key = open(os.path.join(HERE, "indexnow_key.txt")).read().strip()
        host = re.sub(r"^https?://", "", SITE).split("/")[0]
        payload = json.dumps({"host": host, "key": key,
                              "keyLocation": f"{SITE}/{key}.txt", "urlList": urls}).encode()
        for ep in ("https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"):
            try:
                req = urllib.request.Request(ep, data=payload,
                                             headers={"Content-Type": "application/json; charset=utf-8"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    print(f"  IndexNow {ep} -> HTTP {r.status}")
            except Exception as ex:
                print(f"  IndexNow {ep} -> {ex}")
    except Exception as ex:
        print(f"  IndexNow 略過: {ex}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true")
    ap.add_argument(
        "--cached-live",
        action="store_true",
        help="Use the verified availability snapshot without refreshing it.",
    )
    args = ap.parse_args()
    comp_map = load_competitors()
    live_keys = live_app_keys(
        APPSTORE, PAGES, refresh=not args.cached_live
    )
    open(os.path.join(PAGES, "llms.txt"), "w", encoding="utf-8").write(build_llms(comp_map, live_keys))
    open(os.path.join(PAGES, "llms-full.txt"), "w", encoding="utf-8").write(
        build_llms_full(comp_map, live_keys))
    open(os.path.join(PAGES, "robots.txt"), "w", encoding="utf-8").write(build_robots())
    open(os.path.join(PAGES, "sitemap_index.xml"), "w", encoding="utf-8").write(build_sitemap_index())
    print(f"✓ llms.txt / llms-full.txt / robots.txt / sitemap_index.xml → {PAGES}")
    print(f"  收錄 {len(live_keys)}/{len(APPS)} 個已公開 app；robots 歡迎 {len(AI_BOTS)} 個 AI/搜尋 bot")
    if args.publish:
        publish([
            f"{SITE}/llms.txt", f"{SITE}/llms-full.txt",
            f"{SITE}/robots.txt", f"{SITE}/sitemap_index.xml",
        ])
    else:
        print("（加 --publish 部署)")


if __name__ == "__main__":
    main()
