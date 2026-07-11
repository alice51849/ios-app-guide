#!/usr/bin/env python3
"""Build shared discovery pages for all versioned static APIs."""

from __future__ import annotations

import html
import json
import os
import re
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

from family_travel_dataset import write_text_if_changed


HERE = Path(__file__).resolve().parent
PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
CONTENT_MODIFIED_RE = re.compile(
    r'<meta name="content-modified" content="(\d{4}-\d{2}-\d{2})">'
)

API_DESCRIPTORS = (
    {
        "slug": "family-travel-missions",
        "title": "Family Travel Missions API v1",
        "dataset": "Privacy-first family travel mission taxonomy",
        "description": (
            "12 bilingual, privacy-first mission settings with OpenAPI 3.1 "
            "and JSON Schema 2020-12."
        ),
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "modified_source": "data/family-travel-missions.json",
        "initial_date": "2026-07-11",
    },
    {
        "slug": "bopomofo-symbols",
        "title": "Bopomofo Symbols API v1",
        "dataset": "Complete 37-symbol Zhuyin (Bopomofo) inventory",
        "description": (
            "All 37 Zhuyin symbols with Unicode, Pinyin, IPA, categories and "
            "examples through a no-key OpenAPI 3.1 interface."
        ),
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "modified_source": (
            "data/zhuyin-bopomofo-ml-dataset.croissant.jsonld"
        ),
        "initial_date": "2026-07-11",
    },
)


def _api_path(pages: Path, descriptor: dict) -> Path:
    return pages / "api" / "v1" / descriptor["slug"]


def discovered_apis(pages: Path = PAGES) -> list[dict]:
    return [
        descriptor
        for descriptor in API_DESCRIPTORS
        if (_api_path(pages, descriptor) / "openapi.json").exists()
    ]


def _page_modified(path: Path, fallback: str) -> str:
    if not path.exists():
        return fallback
    match = CONTENT_MODIFIED_RE.search(path.read_text(encoding="utf-8"))
    return match.group(1) if match else fallback


def _dataset_modified(pages: Path, descriptor: dict) -> str:
    source = pages / descriptor["modified_source"]
    if source.exists():
        value = json.loads(source.read_text(encoding="utf-8")).get(
            "dateModified"
        )
        if not isinstance(value, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}", value
        ):
            raise ValueError(f"Invalid dateModified in {source}")
        return value
    return descriptor["initial_date"]


def render_api_catalog(pages: Path = PAGES) -> str:
    descriptors = discovered_apis(pages)
    modified_dates = []
    datasets = []
    cards = []
    for descriptor in descriptors:
        api_path = _api_path(pages, descriptor)
        docs_url = f"{SITE}/api/v1/{descriptor['slug']}/"
        docs_modified = _page_modified(
            api_path / "index.html", descriptor["initial_date"]
        )
        modified_dates.append(docs_modified)
        datasets.append(
            {
                "@type": "Dataset",
                "name": descriptor["dataset"],
                "description": descriptor["description"],
                "url": docs_url,
                "license": descriptor["license"],
                "distribution": {
                    "@type": "DataDownload",
                    "encodingFormat": (
                        "application/vnd.oai.openapi+json;version=3.1"
                    ),
                    "contentUrl": f"{docs_url}openapi.json",
                },
            }
        )
        cards.append(
            "<article><h2>{title}</h2><p>{description}</p>"
            '<div class="links"><a href="{docs}">Documentation &rarr;</a>'
            '<a href="{openapi}">OpenAPI JSON &rarr;</a></div></article>'.format(
                title=html.escape(descriptor["title"]),
                description=html.escape(descriptor["description"]),
                docs=html.escape(docs_url, quote=True),
                openapi=html.escape(f"{docs_url}openapi.json", quote=True),
            )
        )
    modified = max(modified_dates, default="2026-07-11")
    schema = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "DataCatalog",
            "name": "Lumi Apps Open APIs",
            "description": (
                "Free, versioned, read-only APIs generated from citable "
                "open datasets."
            ),
            "url": f"{SITE}/api/",
            "dateModified": modified,
            "dataset": datasets,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Open APIs - free, versioned static data | Lumi Apps</title>
<meta name="description" content="Free, versioned, read-only static APIs generated from citable open datasets.">
<meta name="content-modified" content="{modified}">
<link rel="canonical" href="{SITE}/api/"><script type="application/ld+json">{schema}</script>
<style>body{{margin:0;background:#f5f8fc;color:#142036;font:16px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif}}main{{max-width:820px;margin:auto;padding:52px 20px}}a{{color:#315fc4;font-weight:750;text-decoration:none}}article{{background:#fff;border:1px solid #dce4ef;border-radius:18px;padding:22px;margin-top:24px;box-shadow:0 12px 30px rgba(27,44,79,.05)}}h1{{font-size:clamp(30px,6vw,48px);line-height:1.1}}p{{color:#5b687d}}.tag{{font-size:13px;font-weight:700}}.links{{display:flex;flex-wrap:wrap;gap:16px}}</style></head>
<body><main><p class="tag">OPEN DATA &middot; NO API KEYS</p><h1>Open APIs</h1><p>Stable, cacheable JSON interfaces for free reference datasets.</p>
{''.join(cards)}</main></body></html>
"""


def build_api_discovery(pages: Path = PAGES) -> list[str]:
    api_root = pages / "api"
    api_root.mkdir(parents=True, exist_ok=True)
    write_text_if_changed(api_root / "index.html", render_api_catalog(pages))

    entries = []
    descriptors = discovered_apis(pages)
    root_dates = []
    for descriptor in descriptors:
        api_path = _api_path(pages, descriptor)
        en_modified = _page_modified(
            api_path / "index.html", descriptor["initial_date"]
        )
        zh_path = pages / "zh-Hant" / "api" / "v1" / descriptor["slug"]
        zh_modified = _page_modified(
            zh_path / "index.html", descriptor["initial_date"]
        )
        data_modified = _dataset_modified(pages, descriptor)
        root_dates.extend((en_modified, zh_modified))
        entries.extend(
            (
                (f"{SITE}/api/v1/{descriptor['slug']}/", en_modified),
                (
                    f"{SITE}/zh-Hant/api/v1/{descriptor['slug']}/",
                    zh_modified,
                ),
            )
        )
        for path in sorted(api_path.rglob("*.json")):
            relative = path.relative_to(pages).as_posix()
            entries.append((f"{SITE}/{relative}", data_modified))

    root_modified = max(root_dates, default="2026-07-11")
    entries.insert(0, (f"{SITE}/api/", root_modified))
    body = "\n".join(
        "  <url><loc>{url}</loc><lastmod>{modified}</lastmod></url>".format(
            url=xml_escape(url),
            modified=modified,
        )
        for url, modified in entries
    )
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n</urlset>\n"
    )
    write_text_if_changed(pages / "sitemap_api.xml", sitemap)
    return [url for url, _ in entries]
