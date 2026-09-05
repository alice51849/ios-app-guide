#!/usr/bin/env python3
"""Build exact-50, local-only task results; no network, deployment or model calls."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

from app_store_storefronts import campaign_app_store_url
from official_locales import OFFICIAL_LOCALES
from site_config import PUBLIC_SITE

HERE = Path(__file__).resolve().parent
DEFAULT_PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
DEFAULT_SITE = os.environ.get("GEO_SITE", PUBLIC_SITE).rstrip("/")
REGISTRY = HERE / "hero_tasks.json"
I18N = HERE / "hero_tasks_i18n.json"
CORE = HERE / "assets" / "hero-task-core.js"
UI = HERE / "assets" / "hero-task-ui.js"
CSS = HERE / "assets" / "hero-task.css"
MANIFEST = "data/hero-tasks/manifest.json"
SCHEMA = "data/hero-tasks/manifest.schema.json"
SITEMAP = "sitemap_hero_tasks.xml"
INTENTS = "data/lumi-studio-publisher-search-intent-catalog.json"
FINDER = "data/verified-ios-app-finder-catalog.json"
FEED_NAME = "hero-tasks.feed.json"
MARKER = "hero-task-resources-v1"
RTL = {"ar-SA", "he", "ur-PK"}
TOKEN = "geo_learn"
SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
JSON_KEYS = (
    "title intro income day item quantity price total hours days add remove "
    "download reset example example_note formula limits privacy optional "
    "optional_note error row_limit tools method sources result disclosure "
    "download_example feed"
).split()
NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
REVIEWED_ADAPTERS = frozenset({"purchase-worktime-v1"})


def json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def script_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace(
        "<", "\\u003c"
    ).replace(">", "\\u003e").replace("&", "\\u0026").replace(
        "\u2028", "\\u2028"
    ).replace("\u2029", "\\u2029")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def safe_path(pages: Path, relative: str) -> Path:
    part = PurePosixPath(relative)
    if part.is_absolute() or ".." in part.parts or "\\" in relative:
        raise ValueError(f"Unsafe output path: {relative}")
    target = pages / relative
    if not target.resolve().is_relative_to(pages.resolve()) or target.is_symlink():
        raise ValueError(f"Output escapes site root: {relative}")
    return target


def load_i18n(path: Path = I18N) -> dict[str, dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("keys") != JSON_KEYS:
        raise ValueError("Unexpected localization keys")
    values = payload.get("locales", {})
    if set(values) != set(OFFICIAL_LOCALES):
        raise ValueError("All 50 official locales are required; no partial publication")
    result = {}
    for locale in OFFICIAL_LOCALES:
        row = values[locale]
        if isinstance(row, dict):
            target = row.get("same_language_as")
            if (
                set(row) != {"same_language_as"}
                or locale not in {"en-AU", "en-CA", "en-GB"}
                or target != "en-US"
            ):
                raise ValueError(f"Unreviewed locale alias: {locale}")
            row = values[target]
        if (
            not isinstance(row, list) or len(row) != len(JSON_KEYS)
            or any(not isinstance(text, str) or not text.strip() for text in row)
        ):
            raise ValueError(f"Incomplete native copy: {locale}")
        if not locale.startswith("en-") and row[0] == values["en-US"][0]:
            raise ValueError(f"English fallback is forbidden: {locale}")
        result[locale] = dict(zip(JSON_KEYS, row, strict=True))
    return result


def load_registry(path: Path = REGISTRY) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1 or not payload.get("tasks"):
        raise ValueError("Missing reviewed task registry")
    tasks = payload["tasks"]
    for field in ("id", "slug", "adapter"):
        values = [task.get(field) for task in tasks]
        if any(not isinstance(value, str) or not SLUG_RE.fullmatch(value) for value in values):
            raise ValueError(f"Invalid task {field}")
        if len(values) != len(set(values)):
            raise ValueError(f"Equivalent tasks must share one canonical: duplicate {field}")
    app_keys = set()
    for task in tasks:
        if task["adapter"] not in REVIEWED_ADAPTERS:
            raise ValueError(f"No reviewed renderer for adapter: {task['adapter']}")
        apps = task.get("apps")
        if not isinstance(apps, dict) or not apps:
            raise ValueError("Each task needs explicit verified App bindings")
        for key, app_id in apps.items():
            if key in app_keys or not re.fullmatch(r"[a-z0-9]+", key):
                raise ValueError("Each App must have exactly one hero task")
            if not isinstance(app_id, str) or not app_id.isdigit():
                raise ValueError("Invalid App Store ID")
            app_keys.add(key)
        evidence = task.get("evidence", {})
        if (
            evidence.get("measured_search_volume") is not False
            or set(evidence.get("intent_queries", {})) != set(apps)
        ):
            raise ValueError("A truthful, exact-scope evidence record is required")
    return tasks


def task_for_app(tasks: list[dict], key: str) -> dict:
    matches = [task for task in tasks if key in task["apps"]]
    if len(matches) != 1:
        raise ValueError(f"No reviewed hero-task adapter for {key}")
    return matches[0]


def catalogs(pages: Path, tasks: list[dict], site: str, provider: str) -> tuple[dict, dict]:
    if not re.fullmatch(r"\d+", provider):
        raise ValueError("APP_STORE_PROVIDER_TOKEN is required; partial attribution is forbidden")
    finder = json.loads(safe_path(pages, FINDER).read_text(encoding="utf-8"))
    inventory = {app["key"]: app for app in finder["apps"]}
    if len(inventory) != len(finder["apps"]):
        raise ValueError("Duplicate inventory Apps")
    state = json.loads(safe_path(pages, ".appstore_live_state.json").read_text(encoding="utf-8"))
    if {str(app["app_store_id"]) for app in inventory.values()} != set(state["live_ids"]):
        raise ValueError("Cached-live and Finder inventories disagree")
    intents = json.loads(safe_path(pages, INTENTS).read_text(encoding="utf-8"))
    records = {}
    for record in intents["records"]:
        pair = (record["locale"], record["app_key"])
        if pair in records:
            raise ValueError(f"Duplicate publisher intent: {pair}")
        records[pair] = record
    selected = {}
    for task in tasks:
        for key, app_id in task["apps"].items():
            app = inventory.get(key)
            if not app or not app.get("verified_live") or str(app["app_store_id"]) != app_id:
                raise ValueError(f"App is not verified live: {key}")
            for locale in OFFICIAL_LOCALES:
                source = records.get((locale, key))
                if (
                    not source or str(source["app_store_id"]) != app_id
                    or source.get("verified_live") is not True
                    or source.get("source_persona_query") != task["evidence"]["intent_queries"][key]
                ):
                    raise ValueError(f"Missing verified native intent: {key}/{locale}")
                link = campaign_app_store_url(source["app_store_url"], TOKEN, provider_token=provider)
                if not re.search(rf"/id{app_id}(?:\?|$)", link):
                    raise ValueError("App Store link has the wrong owner")
                parsed = urlsplit(source["canonical_guide_url"])
                prefix = urlsplit(site).path.rstrip("/") + "/"
                if not parsed.path.startswith(prefix) or parsed.query or parsed.fragment:
                    raise ValueError("Invalid primary-answer source path")
                answer = parsed.path[len(prefix):]
                is_answer = answer.startswith(f"{locale}/answers/") and answer.endswith(".html")
                if not is_answer and answer != f"{locale}/{key}.html":
                    raise ValueError(f"No verified native source page for {key}/{locale}")
                if not safe_path(pages, answer).is_file():
                    raise ValueError(f"Primary answer is missing: {answer}")
                selected[(locale, key)] = {
                    "key": key, "name": source["app_name"], "app_store_id": app_id,
                    "app_store_url": link, "cta": source["app_store_cta_label"],
                    "answer_path": answer, "purchase_model": app["purchase_model"],
                    "source_kind": "answer" if is_answer else "app_guide",
                }
    return inventory, selected


def examples(tasks: list[dict], copy: dict) -> dict:
    requests = []
    pairs = []
    for task in tasks:
        for locale in OFFICIAL_LOCALES:
            sample = dict(task["example"])
            sample["items"] = [
                {**item, "name": f"{copy[locale]['item']} {index + 1}"}
                for index, item in enumerate(sample["items"])
            ]
            requests.append({"adapter": task["adapter"], "input": sample, "labels": copy[locale]})
            pairs.append((task["id"], locale, sample))
    values = []
    for offset in range(0, len(requests), 200):
        run = subprocess.run(
            ["node", str(CORE)], input=json.dumps(requests[offset:offset + 200], ensure_ascii=False),
            capture_output=True, text=True, timeout=30, check=False,
        )
        if run.returncode:
            raise ValueError(f"Shared adapter failed closed: {run.stderr.strip()}")
        values.extend(json.loads(run.stdout))
    if len(values) != len(pairs):
        raise ValueError("Incomplete adapter output")
    return {
        (task, locale): {"input": sample, **output}
        for (task, locale, sample), output in zip(pairs, values, strict=True)
    }


def resource_path(task: dict, locale: str) -> str:
    return f"{locale}/tools/{task['slug']}.html"


def example_path(task: dict, locale: str) -> str:
    return f"{locale}/tools/results/{task['slug']}.csv"


def feed_path(locale: str) -> str:
    return f"{locale}/tools/{FEED_NAME}"


def number(value: float) -> str:
    return f"{value:.2f}"


def sample_table(copy: dict, result: dict) -> str:
    esc = html.escape
    keys = ("item", "quantity", "price", "total", "hours", "days")
    headings = "".join(f"<th scope=\"col\">{esc(copy[key])}</th>" for key in keys)
    rows = []
    for item in result["items"]:
        values = (
            item["name"], str(item["quantity"]), number(item["price_minor"] / 100),
            number(item["total_minor"] / 100), number(item["work_hours"]), number(item["workdays"]),
        )
        rows.append("<tr>" + "".join(f"<td>{esc(value)}</td>" for value in values) + "</tr>")
    totals = (
        copy["total"], "", "", number(result["total_minor"] / 100),
        number(result["work_hours"]), number(result["workdays"]),
    )
    return (
        '<div class="table-scroll"><table><thead><tr>' + headings + "</tr></thead><tbody>"
        + "".join(rows) + '</tbody><tfoot><tr class="example-total">'
        + "".join(f"<td>{esc(value)}</td>" for value in totals)
        + "</tr></tfoot></table></div>"
    )


def purchase_row(copy: dict, item: dict, index: int, result: dict | None = None) -> str:
    esc = html.escape
    fields = []
    for key, label, mode in (("name", "item", "text"), ("quantity", "quantity", "numeric"), ("price", "price", "decimal")):
        ident = f"purchase-{index}-{key}"
        constraints = 'maxlength="120"' if key == "name" else 'maxlength="12"'
        fields.append(
            f'<div class="{key}-field"><label data-label="{key}" for="{ident}">{esc(copy[label])}</label>'
            f'<input id="{ident}" data-field="{key}" type="text" inputmode="{mode}" '
            f'value="{esc(str(item.get(key, "")), quote=True)}" {constraints} required autocomplete="off"></div>'
        )
    amount = number(result["total_minor"] / 100) if result else "0.00"
    hours = number(result["work_hours"]) if result else "0.00"
    return (
        '<div class="purchase-row">' + "".join(fields)
        + f'<div><p class="output-label">{esc(copy["total"])}</p><output data-output="amount">{amount}</output></div>'
        + f'<div><p class="output-label">{esc(copy["hours"])}</p><output data-output="hours">{hours}</output></div>'
        + f'<button type="button" data-remove aria-label="{esc(copy["remove"] + " · " + str(item.get("name", "")), quote=True)}">'
        + esc(copy["remove"]) + "</button></div>"
    )


def render_page(task: dict, locale: str, copy: dict, sample: dict, apps: list[dict],
                modified: str, site: str, assets: dict) -> str:
    esc = html.escape
    url = f"{site}/{resource_path(task, locale)}"
    csv_url = f"{site}/{example_path(task, locale)}"
    result = sample["result"]
    rows = "".join(
        purchase_row(copy, item, index + 1, result["items"][index])
        for index, item in enumerate(sample["input"]["items"])
    )
    alternates = "\n".join(
        f'<link rel="alternate" hreflang="{other}" href="{site}/{resource_path(task, other)}">'
        for other in OFFICIAL_LOCALES
    )
    config = {
        "adapter": task["adapter"], "slug": task["slug"], "locale": locale,
        "copy": copy, "example": sample["input"],
    }
    schema = {
        "@context": "https://schema.org", "@type": "WebApplication", "@id": url + "#tool",
        "url": url, "name": copy["title"], "description": copy["intro"],
        "inLanguage": locale, "isAccessibleForFree": True, "operatingSystem": "Any",
        "applicationCategory": "FinanceApplication", "dateModified": modified,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "hasPart": {
            "@type": "CreativeWork", "@id": url + "#worked-example", "name": copy["example"],
            "encoding": {"@type": "MediaObject", "contentUrl": csv_url, "encodingFormat": "text/csv"},
        },
        "publisher": {"@type": "Organization", "name": "Lumi Studio", "url": site},
    }
    buttons = "".join(
        f'<a class="button" href="{esc(app["app_store_url"], quote=True)}" rel="nofollow noopener">{esc(app["cta"])}</a>'
        for app in apps
    )
    prefix = urlsplit(site).path.rstrip("/")
    asset = {key: f"{prefix}/{value}" for key, value in assets.items()}
    direction = "rtl" if locale in RTL else "ltr"
    calculation = (
        " + ".join(f"{item['quantity']} × {item['price']}" for item in sample["input"]["items"])
        + f" = {number(result['total_minor'] / 100)}\n"
        + f"{number(result['total_minor'] / 100)} ÷ {sample['input']['hourly_income']} = {number(result['work_hours'])}\n"
        + f"{number(result['work_hours'])} ÷ {sample['input']['workday_hours']} ≈ {number(result['workdays'])}"
    )
    global_feeds = "\n".join(
        f'<link rel="alternate" type="{mime}" href="{site}/{filename}" title="{esc(copy["feed"], quote=True)}">'
        for filename, mime in (
            ("feed.xml", "application/atom+xml"), ("rss.xml", "application/rss+xml"),
            ("feed.json", "application/feed+json"),
        )
    )
    return f"""<!doctype html>
<html lang="{locale}" dir="{direction}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'none'; img-src 'self' data:; base-uri 'none'; form-action 'none'; object-src 'none'">
<meta name="referrer" content="no-referrer">
<meta name="description" content="{esc(copy['intro'], quote=True)}">
<meta name="content-modified" content="{modified}">
<meta name="hero-task" content="{task['id']}">
<title>{esc(copy['title'])}</title>
<link rel="canonical" href="{url}">
{alternates}
<link rel="alternate" hreflang="x-default" href="{site}/{resource_path(task, 'en-US')}">
{global_feeds}
<link rel="alternate" type="application/feed+json" href="{site}/{feed_path(locale)}" title="{esc(copy['feed'], quote=True)}">
<link rel="stylesheet" href="{asset['css']}">
<script type="application/ld+json">{script_json(schema)}</script>
<script type="application/json" id="hero-config">{script_json(config)}</script>
<script src="{asset['core']}" defer></script>
<script src="{asset['ui']}" defer></script>
</head>
<body><main>
<nav><a href="{site}/{locale}/tools/index.html">{esc(copy['tools'])}</a><span>Lumi Studio</span></nav>
<h1>{esc(copy['item'])} · {esc(copy['hours'])}</h1><p>{esc(copy['intro'])}</p>
<section class="panel" aria-label="{esc(copy['title'], quote=True)}">
<form id="hero-form" autocomplete="off">
<fieldset id="hero-fields" disabled>
<div class="fields">
<div><label for="hourly-income">{esc(copy['income'])}</label><input id="hourly-income" type="text" inputmode="decimal" value="{sample['input']['hourly_income']}" maxlength="12" required autocomplete="off"></div>
<div><label for="workday-hours">{esc(copy['day'])}</label><input id="workday-hours" type="text" inputmode="decimal" value="{sample['input']['workday_hours']}" maxlength="5" required autocomplete="off"></div>
</div>
<div id="purchase-rows">{rows}</div>
<template id="purchase-template">{purchase_row(copy, {'name': '', 'quantity': 1, 'price': '0'}, 0)}</template>
<div class="actions"><button type="button" id="add-purchase">{esc(copy['add'])}</button><span class="small">{esc(copy['row_limit'])}</span></div>
<div class="totals" aria-label="{esc(copy['result'], quote=True)}">
<div><p>{esc(copy['total'])}</p><output class="total-value" id="total-amount">{number(result['total_minor'] / 100)}</output></div>
<div><p>{esc(copy['hours'])}</p><output class="total-value" id="total-hours">{number(result['work_hours'])}</output></div>
<div><p>{esc(copy['days'])}</p><output class="total-value" id="total-days">{number(result['workdays'])}</output></div>
</div>
<p id="hero-status" role="status" aria-live="polite"></p>
<div class="actions"><button type="button" class="primary" id="download-csv" disabled>{esc(copy['download'])}</button><button type="button" id="reset-example">{esc(copy['reset'])}</button></div>
</fieldset></form><p class="small">{esc(copy['privacy'])}</p>
</section>
<section class="panel" id="worked-example">
<h2>{esc(copy['example'])}</h2><p>{esc(copy['example_note'])}</p>
{sample_table(copy, result)}
<a class="button" href="{csv_url}" download>{esc(copy['download_example'])}</a>
<h2>{esc(copy['method'])}</h2><p>{esc(copy['formula'])}</p>
<pre class="formula">{esc(calculation)}</pre>
<p>{esc(copy['limits'])}</p>
<ul class="small">
<li>{esc(copy['income'])}: <bdi dir="ltr">0 &lt; x ≤ 100000000</bdi></li>
<li>{esc(copy['price'])}: <bdi dir="ltr">0 ≤ x ≤ 100000000</bdi></li>
<li>{esc(copy['day'])}: <bdi dir="ltr">0 &lt; x ≤ 24</bdi></li>
<li>{esc(copy['quantity'])}: <bdi dir="ltr">1 ≤ x ≤ 999</bdi></li>
</ul>
</section>
<section class="panel optional-apps"><h2>{esc(copy['optional'])}</h2><p>{esc(copy['optional_note'])}</p><div class="actions">{buttons}</div></section>
<footer><p>{esc(copy['disclosure'])}</p><a href="{site}/{INTENTS}">{esc(copy['sources'])}</a> · <a href="{site}/{feed_path(locale)}">{esc(copy['feed'])}</a></footer>
</main></body></html>
"""


def resource_block(locale: str, tasks: list[dict], copy: dict, site: str) -> str:
    cards = "".join(
        f'<article><h2>{html.escape(copy["title"])}</h2><p>{html.escape(copy["intro"])}</p>'
        f'<a class="button" href="{site}/{resource_path(task, locale)}">{html.escape(copy["result"])}</a> '
        f'<a href="{site}/{example_path(task, locale)}" download>{html.escape(copy["download_example"])}</a>'
        f'<p>{html.escape(copy["formula"])}</p></article>'
        for task in tasks
    )
    return f'<!-- {MARKER}:start --><section class="hero-resource" data-primary-resource="hero-task">{cards}</section><!-- {MARKER}:end -->'


def insert_block(document: str, block: str) -> str:
    document = re.sub(
        rf"<!-- {MARKER}:start -->.*?<!-- {MARKER}:end -->(?:\r?\n)?",
        "", document, flags=re.S,
    )
    match = re.search(r"<main\b[^>]*>", document, re.I)
    if match is None:
        match = re.search(r"<body\b[^>]*>", document, re.I)
    if match is None:
        raise ValueError("No safe main/body insertion point")
    return document[:match.end()] + "\n" + block + "\n" + document[match.end():].lstrip("\n")


def integrate(pages: Path, tasks: list[dict], copy: dict, apps: dict, site: str, assets: dict) -> dict[str, str]:
    changes = {}
    for locale in OFFICIAL_LOCALES:
        index = f"{locale}/tools/index.html"
        path = safe_path(pages, index)
        source = path.read_text(encoding="utf-8") if path.exists() else (
            f'<!doctype html><html lang="{locale}" dir="{"rtl" if locale in RTL else "ltr"}">'
            '<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="hero-tools-index" content="v1">'
            f'<title>{html.escape(copy[locale]["tools"])}</title><link rel="canonical" href="{site}/{index}">'
            f'<link rel="alternate" type="application/feed+json" href="{site}/{feed_path(locale)}">'
            f'<link rel="stylesheet" href="{urlsplit(site).path.rstrip("/")}/{assets["css"]}">'
            '</head><body><main>'
            f'<h1>{html.escape(copy[locale]["tools"])}</h1></main></body></html>'
        )
        if '<meta name="hero-tools-index" content="v1">' in source:
            source = re.sub(
                r'<link rel="stylesheet" href="[^"]+/assets/hero-tasks/[^"]+">',
                f'<link rel="stylesheet" href="{urlsplit(site).path.rstrip("/")}/{assets["css"]}">',
                source,
            )
        block = resource_block(locale, tasks, copy[locale], site)
        changes[index] = insert_block(source, block)
        for task in tasks:
            own_block = resource_block(locale, [task], copy[locale], site)
            for key in task["apps"]:
                answer = apps[(locale, key)]["answer_path"]
                source = changes.get(answer) or safe_path(pages, answer).read_text(encoding="utf-8")
                changes[answer] = insert_block(source, own_block)
    return changes


def manifest_schema() -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "required": ["schema_version", "content_digest", "date_modified", "locale_count",
                     "portfolio_app_count", "supported_app_keys", "unserved_app_keys",
                     "records", "outputs", "integrations"],
        "properties": {
            "schema_version": {"const": 1},
            "locale_count": {"const": 50},
            "content_digest": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "date_modified": {"type": "string", "format": "date"},
            "portfolio_app_count": {"type": "integer", "minimum": 1},
            "supported_app_keys": {"type": "array", "uniqueItems": True, "minItems": 1, "items": {"type": "string"}},
            "unserved_app_keys": {"type": "array", "uniqueItems": True, "items": {"type": "string"}},
            "records": {"type": "array", "minItems": 50, "items": {
                "type": "object", "required": ["task_id", "locale", "url", "path", "example_url", "apps"],
                "properties": {"locale": {"enum": list(OFFICIAL_LOCALES)}},
            }},
            "outputs": {"type": "object", "minProperties": 1, "additionalProperties": {
                "type": "string", "pattern": "^[0-9a-f]{64}$",
            }},
            "integrations": {"type": "array", "uniqueItems": True, "items": {"type": "string"}},
        },
    }


def sitemap_index(document: str, site: str, modified: str) -> str:
    root = ET.fromstring(document)
    if root.tag != f"{{{NAMESPACE}}}sitemapindex":
        raise ValueError("The root sitemap must be a sitemap index")
    entry = f"<sitemap><loc>{site}/{SITEMAP}</loc><lastmod>{modified}</lastmod></sitemap>"
    pattern = rf"<sitemap>\s*<loc>[^<]*/{re.escape(SITEMAP)}</loc>.*?</sitemap>"
    matches = list(re.finditer(pattern, document, flags=re.S))
    if len(matches) > 1:
        raise ValueError("Duplicate hero-task sitemap entries")
    if matches:
        match = matches[0]
        return document[:match.start()] + entry + document[match.end():]
    return document.replace("</sitemapindex>", entry + "\n</sitemapindex>")


def plan(pages: Path, *, site: str = DEFAULT_SITE, provider: str,
         today: str | None = None, registry: Path = REGISTRY, i18n: Path = I18N) -> tuple[dict, dict[str, bytes]]:
    site = site.rstrip("/")
    parsed = urlsplit(site)
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError("A canonical HTTPS site is required")
    today = today or datetime.now(timezone.utc).date().isoformat()
    if date.fromisoformat(today).isoformat() != today:
        raise ValueError("Invalid build date")
    tasks, copy = load_registry(registry), load_i18n(i18n)
    inventory, apps = catalogs(pages, tasks, site, provider)
    calculated = examples(tasks, copy)
    assets = {
        key: f"assets/hero-tasks/{digest(path.read_bytes())[:16]}-{path.name}"
        for key, path in (("core", CORE), ("ui", UI), ("css", CSS))
    }
    source_digest = digest(json_text({
        "sources": {
            str(path.name): digest(path.read_bytes())
            for path in (Path(__file__), registry, i18n, CORE, UI, CSS)
        },
        "inventory": sorted(inventory), "bindings": list(apps.values()),
        "site": site, "provider": provider,
    }).encode())
    previous_path = safe_path(pages, MANIFEST)
    previous = json.loads(previous_path.read_text()) if previous_path.is_file() else {}
    modified = today
    if previous.get("content_digest") == source_digest:
        previous_date = previous["date_modified"]
        if date.fromisoformat(previous_date).isoformat() != previous_date or previous_date > today:
            raise ValueError("Invalid previous semantic date")
        modified = previous_date
    outputs = {assets[key]: path.read_bytes() for key, path in (("core", CORE), ("ui", UI), ("css", CSS))}
    records = []
    for locale in OFFICIAL_LOCALES:
        feed_items = []
        for task in tasks:
            sample = calculated[(task["id"], locale)]
            optional = sorted(
                [apps[(locale, key)] for key in task["apps"]],
                key=lambda app: (app["purchase_model"] != "free_with_lifetime_unlock", app["key"]),
            )
            relative = resource_path(task, locale)
            page = render_page(task, locale, copy[locale], sample, optional, modified, site, assets)
            outputs[relative] = page.encode()
            csv_path = example_path(task, locale)
            outputs[csv_path] = sample["csv"].encode()
            record = {
                "task_id": task["id"], "adapter": task["adapter"], "locale": locale,
                "url": f"{site}/{relative}", "path": relative,
                "example_url": f"{site}/{csv_path}",
                "apps": [{"key": app["key"], "app_store_url": app["app_store_url"]} for app in optional],
            }
            records.append(record)
            feed_items.append({
                "id": record["url"], "url": record["url"], "title": copy[locale]["title"],
                "content_text": copy[locale]["intro"] + " " + copy[locale]["formula"] + " " + copy[locale]["limits"],
                "language": locale, "date_modified": f"{modified}T00:00:00Z",
                "attachments": [{"url": record["example_url"], "mime_type": "text/csv",
                                 "title": copy[locale]["download_example"], "size_in_bytes": len(outputs[csv_path])}],
                "_hero_task": {"adapter": task["adapter"], "optional_apps": record["apps"]},
            })
        outputs[feed_path(locale)] = json_text({
            "version": "https://jsonfeed.org/version/1.1", "title": copy[locale]["feed"],
            "home_page_url": f"{site}/{locale}/tools/index.html", "feed_url": f"{site}/{feed_path(locale)}",
            "language": locale, "authors": [{"name": "Lumi Studio", "url": site}], "items": feed_items,
        }).encode()
    outputs[SITEMAP] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="{NAMESPACE}">\n'
        + "".join(f'<url><loc>{html.escape(row["url"])}</loc><lastmod>{modified}</lastmod></url>\n' for row in records)
        + "</urlset>\n"
    ).encode()
    outputs[SCHEMA] = json_text(manifest_schema()).encode()
    integrations = integrate(pages, tasks, copy, apps, site, assets)
    root_path = safe_path(pages, "sitemap_index.xml")
    root_xml = root_path.read_text() if root_path.exists() else f'<sitemapindex xmlns="{NAMESPACE}"></sitemapindex>'
    integrations["sitemap_index.xml"] = sitemap_index(root_xml, site, modified)
    supported = sorted({key for task in tasks for key in task["apps"]})
    manifest = {
        "$schema": f"{site}/{SCHEMA}", "schema_version": 1,
        "content_digest": source_digest, "date_modified": modified, "locale_count": 50,
        "portfolio_app_count": len(inventory), "supported_app_keys": supported,
        "unserved_app_keys": sorted(set(inventory) - set(supported)),
        "scope": "reviewed_adapters_only", "measured_search_volume": False,
        "task_count": len(tasks), "app_locale_pairs": len(supported) * 50,
        "records": records, "outputs": {path: digest(content) for path, content in sorted(outputs.items())},
        "integrations": sorted(integrations),
    }
    outputs[MANIFEST] = json_text(manifest).encode()
    outputs.update({path: text.encode() for path, text in integrations.items()})
    for relative in outputs:
        safe_path(pages, relative)
    return manifest, outputs


def build(pages: Path = DEFAULT_PAGES, *, check: bool = False, **kwargs) -> dict:
    previous_path = safe_path(pages, MANIFEST)
    previous = json.loads(previous_path.read_text()) if previous_path.is_file() else {}
    manifest, outputs = plan(pages, **kwargs)
    stale = sorted(set(previous.get("outputs", {})) - set(outputs))
    for relative in stale:
        path = safe_path(pages, relative)
        if path.exists() and digest(path.read_bytes()) != previous["outputs"][relative]:
            raise ValueError(f"Refusing to delete modified stale output: {relative}")
    changed = [relative for relative, content in outputs.items()
               if not safe_path(pages, relative).is_file() or safe_path(pages, relative).read_bytes() != content]
    if check and (changed or stale):
        raise ValueError(f"Hero-task output gate failed ({len(changed)}): {', '.join(changed[:8])}")
    if not check:
        for relative in changed:
            path = safe_path(pages, relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(outputs[relative])
        for relative in stale:
            safe_path(pages, relative).unlink(missing_ok=True)
    return {
        "tasks": manifest["task_count"], "locales": 50,
        "supported_apps": len(manifest["supported_app_keys"]),
        "unserved_apps": len(manifest["unserved_app_keys"]),
        "pages": len(manifest["records"]), "changed": len(changed),
        "removed": len(stale),
        "content_digest": manifest["content_digest"], "check": check,
    }


def english_feed_entries(pages: Path) -> list[tuple[str, str]]:
    path = safe_path(pages, MANIFEST)
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("locale_count") != 50:
        raise ValueError("Cannot syndicate partial hero-task locale coverage")
    result = []
    for record in payload["records"]:
        if record["locale"] == "en-US":
            target = safe_path(pages, record["path"])
            if not target.is_file() or digest(target.read_bytes()) != payload["outputs"][record["path"]]:
                raise ValueError("Cannot syndicate unverified hero-task content")
            result.append((record["path"], record["url"]))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-dir", type=Path, default=DEFAULT_PAGES)
    parser.add_argument("--site", default=DEFAULT_SITE)
    parser.add_argument("--today")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = build(args.pages_dir, site=args.site, today=args.today, check=args.check,
                   provider=os.environ.get("APP_STORE_PROVIDER_TOKEN", "").strip())
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
