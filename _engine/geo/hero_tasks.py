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
from hero_task_html import (
    generated_index, insert_resource, require_retirable_index,
    useful_navigation, without_resource,
)
from official_locales import OFFICIAL_LOCALES
from site_config import PUBLIC_SITE
from sync_standard_site import preserve_managed_links

HERE = Path(__file__).resolve().parent
DEFAULT_PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
DEFAULT_SITE = os.environ.get("GEO_SITE", PUBLIC_SITE).rstrip("/")
REGISTRY = HERE / "hero_tasks.json"
I18N = HERE / "hero_tasks_i18n.json"
CORE = HERE / "assets" / "hero-task-core.js"
UI = HERE / "assets" / "hero-task-ui.js"
CSS = HERE / "assets" / "hero-task.css"
MAINTENANCE_CORE = HERE / "assets" / "hero-task-maintenance-core.js"
MAINTENANCE_UI = HERE / "assets" / "hero-task-maintenance-ui.js"
MAINTENANCE_CSS = HERE / "assets" / "hero-task-maintenance.css"
PROFIT_CORE = HERE / "assets" / "hero-task-profit-core.js"
PROFIT_UI = HERE / "assets" / "hero-task-profit-ui.js"
PROFIT_CSS = HERE / "assets" / "hero-task-profit.css"
BATTERY_CORE = HERE / "assets" / "hero-task-battery-core.js"
BATTERY_UI = HERE / "assets" / "hero-task-battery-ui.js"
BATTERY_CSS = HERE / "assets" / "hero-task-battery.css"
MANIFEST = "data/hero-tasks/manifest.json"
SCHEMA = "data/hero-tasks/manifest.schema.json"
SITEMAP = "sitemap_hero_tasks.xml"
INTENTS = "data/lumi-studio-publisher-search-intent-catalog.json"
FINDER = "data/verified-ios-app-finder-catalog.json"
FEED_NAME = "hero-tasks.feed.json"
MARKER = "hero-task-resources-v1"
CARD_START = "<!-- app-decision-card:start -->"
CARD_END = "<!-- app-decision-card:end -->"
# Second-tier reach: other answer pages about the same App in the same locale
# that already carry the App's verified decision card. Zero new URLs.
SECONDARY_LIMIT = 3
DATA_LICENSE = "https://creativecommons.org/licenses/by/4.0/"
RTL = {"ar-SA", "he", "ur-PK"}
TOKEN = "geo_learn"
SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
JSON_KEYS = (
    "title intro income day item quantity price total hours days add remove "
    "download reset example example_note formula limits privacy optional "
    "optional_note error row_limit tools method sources result disclosure "
    "download_example feed"
).split()
TASK_KEYS = {
    # Task-scoped native copy layered over the shared keys above; the first task
    # keeps using the shared copy unchanged so its published bytes never move.
    "maintenance-next-due": (
        "title intro today item last_done interval interval_value unit_day unit_week "
        "unit_month next_due days_left status status_ok status_due_soon status_overdue add "
        "example example_note formula limits error row_limit result download_example"
    ).split(),
    "project-profit": (
        "title intro project hours hours_hint kind income expense item amount add_income add_expense "
        "income_total expense_total profit margin hourly_net example example_note formula limits "
        "error row_limit result download_example"
    ).split(),
    "battery-wear": (
        "title intro today item purchase_month capacity cycles cycles_hint age wear_rate months_to_80 "
        "cycles_per_month low high range_note marker_provided marker_estimated source_marker "
        "at_or_below_80 no_wear_yet add example example_note formula limits error row_limit result "
        "download_example"
    ).split(),
}
NAMESPACE = "http://www.sitemaps.org/schemas/sitemap/0.9"
REVIEWED_ADAPTERS = frozenset({
    "purchase-worktime-v1", "maintenance-next-due-v1", "project-profit-v1", "battery-wear-range-v1",
})
# Each adapter ships its own pure-JS core and browser UI; the shared stylesheet is
# reused and an adapter may add one stylesheet of its own.
ADAPTER_ASSETS = {
    "purchase-worktime-v1": {"core": CORE, "ui": UI, "css": CSS},
    "maintenance-next-due-v1": {
        "core": MAINTENANCE_CORE, "ui": MAINTENANCE_UI, "css": CSS, "extra_css": MAINTENANCE_CSS,
    },
    "project-profit-v1": {"core": PROFIT_CORE, "ui": PROFIT_UI, "css": CSS, "extra_css": PROFIT_CSS},
    "battery-wear-range-v1": {"core": BATTERY_CORE, "ui": BATTERY_UI, "css": CSS, "extra_css": BATTERY_CSS},
}
ASSET_FILES = (
    CORE, UI, CSS, MAINTENANCE_CORE, MAINTENANCE_UI, MAINTENANCE_CSS,
    PROFIT_CORE, PROFIT_UI, PROFIT_CSS, BATTERY_CORE, BATTERY_UI, BATTERY_CSS,
)
UNITS = ("day", "week", "month")


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


def _native_rows(values: dict, keys: list[str], label: str) -> dict[str, dict[str, str]]:
    if set(values) != set(OFFICIAL_LOCALES):
        raise ValueError(f"All 50 official locales are required; no partial publication: {label}")
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
                raise ValueError(f"Unreviewed locale alias: {label}/{locale}")
            row = values[target]
        if (
            not isinstance(row, list) or len(row) != len(keys)
            or any(not isinstance(text, str) or not text.strip() for text in row)
        ):
            raise ValueError(f"Incomplete native copy: {label}/{locale}")
        if not locale.startswith("en-") and row[0] == values["en-US"][0]:
            raise ValueError(f"English fallback is forbidden: {label}/{locale}")
        result[locale] = dict(zip(keys, row, strict=True))
    return result


def load_task_i18n(path: Path = I18N) -> dict[str, dict[str, dict[str, str]]]:
    """Task-scoped copy keyed by task id, then locale; tasks without a section get {}."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    sections = payload.get("tasks", {})
    if not isinstance(sections, dict) or set(sections) - set(TASK_KEYS):
        raise ValueError("Unexpected task-scoped localization sections")
    result = {}
    for task_id, keys in TASK_KEYS.items():
        section = sections.get(task_id)
        if section is None:
            raise ValueError(f"Missing native copy for task: {task_id}")
        if section.get("keys") != keys:
            raise ValueError(f"Unexpected localization keys: {task_id}")
        result[task_id] = _native_rows(section.get("locales", {}), keys, task_id)
    return result


def task_copy(copy: dict, task_copies: dict | None, task: dict, locale: str) -> dict[str, str]:
    """Shared copy layered with the task's own native copy (identity for the first task)."""
    overlay = (task_copies or {}).get(task["id"], {}).get(locale)
    if not overlay:
        return copy[locale]
    return {**copy[locale], **overlay}


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


def examples(tasks: list[dict], copy: dict, task_copies: dict | None = None) -> dict:
    if task_copies is None:
        task_copies = load_task_i18n()
    batches: dict[str, list] = {}
    pairs = []
    for task in tasks:
        for locale in OFFICIAL_LOCALES:
            labels = task_copy(copy, task_copies, task, locale)
            sample = dict(task["example"])
            sample["items"] = [
                {**item, "name": f"{labels['item']} {index + 1}"}
                for index, item in enumerate(sample["items"])
            ]
            batches.setdefault(task["adapter"], []).append(
                {"adapter": task["adapter"], "input": sample, "labels": labels}
            )
            pairs.append((task["id"], locale, sample, task["adapter"], len(batches[task["adapter"]]) - 1))
    values: dict[str, list] = {}
    for adapter, requests in batches.items():
        core = ADAPTER_ASSETS[adapter]["core"]
        for offset in range(0, len(requests), 200):
            run = subprocess.run(
                ["node", str(core)], input=json.dumps(requests[offset:offset + 200], ensure_ascii=False),
                capture_output=True, text=True, timeout=30, check=False,
            )
            if run.returncode:
                raise ValueError(f"Shared adapter failed closed: {run.stderr.strip()}")
            values.setdefault(adapter, []).extend(json.loads(run.stdout))
        if len(values[adapter]) != len(requests):
            raise ValueError("Incomplete adapter output")
    return {
        (task, locale): {"input": sample, **values[adapter][position]}
        for task, locale, sample, adapter, position in pairs
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
                modified: str, site: str, assets: dict, navigation: dict | None = None) -> str:
    if task["adapter"] == "maintenance-next-due-v1":
        return render_maintenance_page(task, locale, copy, sample, apps, modified, site, assets, navigation)
    if task["adapter"] == "project-profit-v1":
        return render_profit_page(task, locale, copy, sample, apps, modified, site, assets, navigation)
    if task["adapter"] == "battery-wear-range-v1":
        return render_battery_page(task, locale, copy, sample, apps, modified, site, assets, navigation)
    if task["adapter"] != "purchase-worktime-v1":
        raise ValueError(f"No reviewed renderer for adapter: {task['adapter']}")
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
    back_link = (
        f'<a href="{esc(site + "/" + navigation["path"], quote=True)}">{esc(navigation["label"])}</a>'
        if navigation else ""
    )
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
<script type="application/ld+json">{script_json(guidance_schema(task, locale, copy, site, modified))}</script>
<script type="application/json" id="hero-config">{script_json(config)}</script>
<script src="{asset['core']}" defer></script>
<script src="{asset['ui']}" defer></script>
</head>
<body><main>
<nav>{back_link}<span>Lumi Studio</span></nav>
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


def unit_label(copy: dict, unit: str, value: int) -> str:
    """Mirror of the adapter's singular|plural label rule so static and live text agree."""
    forms = str(copy[f"unit_{unit}"]).split("|")
    return forms[0] if value == 1 else forms[-1]


def interval_text(copy: dict, item: dict) -> str:
    return f"{item['interval_value']} {unit_label(copy, item['interval_unit'], item['interval_value'])}"


def maintenance_row(copy: dict, item: dict, index: int, result: dict | None = None) -> str:
    esc = html.escape
    fields = []
    for key, label in (("name", "item"), ("last_done", "last_done"), ("interval_value", "interval_value")):
        ident = f"task-{index}-{key}"
        if key == "last_done":
            control = (
                f'<input id="{ident}" data-field="{key}" type="date" min="1900-01-01" max="2999-12-31" '
                f'value="{esc(str(item.get(key, "")), quote=True)}" required autocomplete="off">'
            )
        else:
            constraints = 'maxlength="120"' if key == "name" else 'inputmode="numeric" maxlength="4"'
            control = (
                f'<input id="{ident}" data-field="{key}" type="text" {constraints} '
                f'value="{esc(str(item.get(key, "")), quote=True)}" required autocomplete="off">'
            )
        fields.append(
            f'<div class="{key.replace("_", "-")}-field"><label data-label="{key}" for="{ident}">{esc(copy[label])}</label>{control}</div>'
        )
    unit = item.get("interval_unit", "month")
    options = "".join(
        f'<option value="{candidate}"{" selected" if candidate == unit else ""}>{esc(copy[f"unit_{candidate}"].split("|")[-1])}</option>'
        for candidate in UNITS
    )
    fields.append(
        f'<div class="interval-unit-field"><label data-label="interval_unit" for="task-{index}-interval_unit">{esc(copy["interval"])}</label>'
        f'<select id="task-{index}-interval_unit" data-field="interval_unit" required>{options}</select></div>'
    )
    next_due = result["next_due"] if result else "—"
    days_left = str(result["days_left"]) if result else "—"
    status_key = result["status"] if result else ""
    status_text = copy[f"status_{status_key}"] if result else "—"
    return (
        '<div class="maintenance-row">' + "".join(fields)
        + f'<div><p class="output-label">{esc(copy["next_due"])}</p><output data-output="next_due" dir="ltr">{esc(next_due)}</output></div>'
        + f'<div><p class="output-label">{esc(copy["days_left"])}</p><output data-output="days_left">{esc(days_left)}</output></div>'
        + f'<div><p class="output-label">{esc(copy["status"])}</p><output class="status-badge" data-output="status" data-status="{status_key}">{esc(status_text)}</output></div>'
        + f'<button type="button" data-remove aria-label="{esc(copy["remove"] + " · " + str(item.get("name", "")), quote=True)}">'
        + esc(copy["remove"]) + "</button></div>"
    )


def maintenance_table(copy: dict, result: dict) -> str:
    esc = html.escape
    keys = ("item", "last_done", "interval", "next_due", "days_left", "status")
    headings = "".join(f"<th scope=\"col\">{esc(copy[key])}</th>" for key in keys)
    rows = []
    for index in result["order"]:
        item = result["items"][index]
        values = (
            item["name"], item["last_done"], interval_text(copy, item), item["next_due"],
            str(item["days_left"]), copy[f"status_{item['status']}"],
        )
        rows.append("<tr>" + "".join(f"<td>{esc(value)}</td>" for value in values) + "</tr>")
    footer = (copy["today"], result["today"], "", "", "", "")
    return (
        '<div class="table-scroll"><table><thead><tr>' + headings + "</tr></thead><tbody>"
        + "".join(rows) + '</tbody><tfoot><tr class="example-total">'
        + "".join(f"<td>{esc(value)}</td>" for value in footer)
        + "</tr></tfoot></table></div>"
    )


def render_maintenance_page(task: dict, locale: str, copy: dict, sample: dict, apps: list[dict],
                            modified: str, site: str, assets: dict, navigation: dict | None = None) -> str:
    esc = html.escape
    url = f"{site}/{resource_path(task, locale)}"
    csv_url = f"{site}/{example_path(task, locale)}"
    result = sample["result"]
    rows = "".join(
        maintenance_row(copy, item, index + 1, result["items"][index])
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
        "applicationCategory": "UtilitiesApplication", "dateModified": modified,
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
    back_link = (
        f'<a href="{esc(site + "/" + navigation["path"], quote=True)}">{esc(navigation["label"])}</a>'
        if navigation else ""
    )
    calculation = "\n".join(
        f"{item['last_done']} + {interval_text(copy, item)} = {item['next_due']}; "
        f"{item['next_due']} − {result['today']} = {item['days_left']}"
        for item in result["items"]
    )
    global_feeds = "\n".join(
        f'<link rel="alternate" type="{mime}" href="{site}/{filename}" title="{esc(copy["feed"], quote=True)}">'
        for filename, mime in (
            ("feed.xml", "application/atom+xml"), ("rss.xml", "application/rss+xml"),
            ("feed.json", "application/feed+json"),
        )
    )
    template_item = {"name": "", "last_done": sample["input"]["today"], "interval_value": 1, "interval_unit": "month"}
    counts = "".join(
        f'<div><p>{esc(copy[f"status_{key}"])}</p><output class="total-value" id="count-{key}">{result["counts"][key]}</output></div>'
        for key in ("overdue", "due_soon", "ok")
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
<link rel="stylesheet" href="{asset['extra_css']}">
<script type="application/ld+json">{script_json(schema)}</script>
<script type="application/ld+json">{script_json(guidance_schema(task, locale, copy, site, modified))}</script>
<script type="application/json" id="hero-config">{script_json(config)}</script>
<script src="{asset['core']}" defer></script>
<script src="{asset['ui']}" defer></script>
</head>
<body><main>
<nav>{back_link}<span>Lumi Studio</span></nav>
<h1>{esc(copy['item'])} · {esc(copy['next_due'])}</h1><p>{esc(copy['intro'])}</p>
<section class="panel" aria-label="{esc(copy['title'], quote=True)}">
<form id="hero-form" autocomplete="off">
<fieldset id="hero-fields" disabled>
<div class="fields">
<div><label for="today-date">{esc(copy['today'])}</label><input id="today-date" type="date" min="1900-01-01" max="2999-12-31" value="{sample['input']['today']}" required autocomplete="off"></div>
</div>
<div id="maintenance-rows">{rows}</div>
<template id="maintenance-template">{maintenance_row(copy, template_item, 0)}</template>
<div class="actions"><button type="button" id="add-task">{esc(copy['add'])}</button><span class="small">{esc(copy['row_limit'])}</span></div>
<div class="totals" aria-label="{esc(copy['result'], quote=True)}">
{counts}
</div>
<p id="hero-status" role="status" aria-live="polite"></p>
<div class="actions"><button type="button" class="primary" id="download-csv" disabled>{esc(copy['download'])}</button><button type="button" id="reset-example">{esc(copy['reset'])}</button></div>
</fieldset></form><p class="small">{esc(copy['privacy'])}</p>
</section>
<section class="panel" id="worked-example">
<h2>{esc(copy['example'])}</h2><p>{esc(copy['example_note'])}</p>
{maintenance_table(copy, result)}
<a class="button" href="{csv_url}" download>{esc(copy['download_example'])}</a>
<h2>{esc(copy['method'])}</h2><p>{esc(copy['formula'])}</p>
<pre class="formula">{esc(calculation)}</pre>
<p>{esc(copy['limits'])}</p>
<ul class="small">
<li>{esc(copy['interval_value'])}: <bdi dir="ltr">1 ≤ x ≤ 3650</bdi></li>
<li>{esc(copy['last_done'])}: <bdi dir="ltr">1900-01-01 ≤ x ≤ 2999-12-31</bdi></li>
<li>{esc(copy['item'])}: <bdi dir="ltr">1 ≤ n ≤ 30</bdi></li>
</ul>
</section>
<section class="panel optional-apps"><h2>{esc(copy['optional'])}</h2><p>{esc(copy['optional_note'])}</p><div class="actions">{buttons}</div></section>
<footer><p>{esc(copy['disclosure'])}</p><a href="{site}/{INTENTS}">{esc(copy['sources'])}</a> · <a href="{site}/{feed_path(locale)}">{esc(copy['feed'])}</a></footer>
</main></body></html>
"""


def money_text(minor: float) -> str:
    negative = minor < 0
    absolute = abs(round(minor))
    text = f"{absolute // 100}.{absolute % 100:02d}"
    return f"-{text}" if negative else text


def percent_text(ratio: float | None) -> str:
    return "—" if ratio is None else f"{ratio * 100:.1f}%"


def page_head(task: dict, locale: str, copy: dict, site: str, assets: dict, modified: str,
              schema: dict, config: dict) -> str:
    """Shared <head> for the second-wave renderers; the first two adapters keep their own bytes."""
    esc = html.escape
    url = f"{site}/{resource_path(task, locale)}"
    alternates = "\n".join(
        f'<link rel="alternate" hreflang="{other}" href="{site}/{resource_path(task, other)}">'
        for other in OFFICIAL_LOCALES
    )
    prefix = urlsplit(site).path.rstrip("/")
    asset = {key: f"{prefix}/{value}" for key, value in assets.items()}
    global_feeds = "\n".join(
        f'<link rel="alternate" type="{mime}" href="{site}/{filename}" title="{esc(copy["feed"], quote=True)}">'
        for filename, mime in (
            ("feed.xml", "application/atom+xml"), ("rss.xml", "application/rss+xml"),
            ("feed.json", "application/feed+json"),
        )
    )
    return f"""<head>
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
<link rel="stylesheet" href="{asset['extra_css']}">
<script type="application/ld+json">{script_json(schema)}</script>
<script type="application/ld+json">{script_json(guidance_schema(task, locale, copy, site, modified))}</script>
<script type="application/json" id="hero-config">{script_json(config)}</script>
<script src="{asset['core']}" defer></script>
<script src="{asset['ui']}" defer></script>
</head>"""


def guidance_schema(task: dict, locale: str, copy: dict, site: str, modified: str) -> list[dict]:
    """HowTo + Dataset JSON-LD for AI assistants. Steps are the page's own
    formula/limits copy; the Dataset is the public CSV example. Ratings and
    reviews are deliberately never emitted."""
    url = f"{site}/{resource_path(task, locale)}"
    example = f"{site}/{example_path(task, locale)}"
    publisher = {"@type": "Organization", "name": "Lumi Studio", "url": site}
    steps = [
        {"@type": "HowToStep", "position": position, "text": copy[key]}
        for position, key in enumerate(("formula", "limits"), start=1)
    ]
    return [
        {
            "@context": "https://schema.org", "@type": "HowTo", "@id": url + "#howto",
            "name": copy["title"], "description": copy["intro"], "inLanguage": locale,
            "isAccessibleForFree": True, "dateModified": modified,
            "tool": {"@type": "HowToTool", "name": copy["title"], "url": url},
            "step": steps, "publisher": publisher,
        },
        {
            "@context": "https://schema.org", "@type": "Dataset", "@id": url + "#example-dataset",
            "name": copy["example"], "description": copy["intro"], "inLanguage": locale,
            "isAccessibleForFree": True, "license": DATA_LICENSE, "dateModified": modified,
            "creator": publisher, "isPartOf": {"@type": "WebApplication", "@id": url + "#tool"},
            "includedInDataCatalog": {"@type": "DataCatalog", "url": f"{site}/data/"},
            "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": example}],
        },
    ]


def tool_schema(task: dict, locale: str, copy: dict, site: str, modified: str) -> dict:
    url = f"{site}/{resource_path(task, locale)}"
    return {
        "@context": "https://schema.org", "@type": "WebApplication", "@id": url + "#tool",
        "url": url, "name": copy["title"], "description": copy["intro"],
        "inLanguage": locale, "isAccessibleForFree": True, "operatingSystem": "Any",
        "applicationCategory": "UtilitiesApplication", "dateModified": modified,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "hasPart": {
            "@type": "CreativeWork", "@id": url + "#worked-example", "name": copy["example"],
            "encoding": {"@type": "MediaObject", "contentUrl": f"{site}/{example_path(task, locale)}",
                         "encodingFormat": "text/csv"},
        },
        "publisher": {"@type": "Organization", "name": "Lumi Studio", "url": site},
    }


def app_buttons(apps: list[dict]) -> str:
    return "".join(
        f'<a class="button" href="{html.escape(app["app_store_url"], quote=True)}" rel="nofollow noopener">{html.escape(app["cta"])}</a>'
        for app in apps
    )


def profit_row(copy: dict, item: dict, index: int) -> str:
    esc = html.escape
    kind = item.get("kind", "income")
    ident_name, ident_amount = f"row-{index}-name", f"row-{index}-amount"
    return (
        f'<div class="profit-row" data-kind="{esc(kind)}">'
        f'<div class="kind-field"><p class="output-label">{esc(copy["kind"])}</p><output class="kind-badge" data-output="kind">{esc(copy[kind])}</output></div>'
        f'<div class="name-field"><label data-label="name" for="{ident_name}">{esc(copy["item"])}</label>'
        f'<input id="{ident_name}" data-field="name" type="text" maxlength="120" value="{esc(str(item.get("name", "")), quote=True)}" required autocomplete="off"></div>'
        f'<div class="amount-field"><label data-label="amount" for="{ident_amount}">{esc(copy["amount"])}</label>'
        f'<input id="{ident_amount}" data-field="amount" type="text" inputmode="decimal" maxlength="12" value="{esc(str(item.get("amount", "")), quote=True)}" required autocomplete="off"></div>'
        f'<button type="button" data-remove aria-label="{esc(copy["remove"] + " · " + str(item.get("name", "")), quote=True)}">{esc(copy["remove"])}</button>'
        "</div>"
    )


def profit_table(copy: dict, result: dict) -> str:
    esc = html.escape
    headings = "".join(f'<th scope="col">{esc(copy[key])}</th>' for key in ("kind", "item", "amount"))
    rows = "".join(
        f"<tr><td>{esc(copy[item['kind']])}</td><td>{esc(item['name'])}</td><td>{money_text(item['amount_minor'])}</td></tr>"
        for item in result["items"]
    )
    hourly = "—" if result["hourly_net_minor"] is None else money_text(result["hourly_net_minor"])
    footer = "".join(
        f'<tr class="example-total"><td>{esc(label)}</td><td></td><td>{value}</td></tr>'
        for label, value in (
            (copy["income_total"], money_text(result["income_total_minor"])),
            (copy["expense_total"], money_text(result["expense_total_minor"])),
            (copy["profit"], money_text(result["profit_minor"])),
            (copy["margin"], percent_text(result["margin"])),
            (copy["hourly_net"], hourly),
        )
    )
    return (
        '<div class="table-scroll"><table><thead><tr>' + headings + "</tr></thead><tbody>"
        + rows + "</tbody><tfoot>" + footer + "</tfoot></table></div>"
    )


def render_profit_page(task: dict, locale: str, copy: dict, sample: dict, apps: list[dict],
                       modified: str, site: str, assets: dict, navigation: dict | None = None) -> str:
    esc = html.escape
    csv_url = f"{site}/{example_path(task, locale)}"
    result = sample["result"]
    rows = "".join(profit_row(copy, item, index + 1) for index, item in enumerate(sample["input"]["items"]))
    config = {"adapter": task["adapter"], "slug": task["slug"], "locale": locale, "copy": copy, "example": sample["input"]}
    head = page_head(task, locale, copy, site, assets, modified, tool_schema(task, locale, copy, site, modified), config)
    direction = "rtl" if locale in RTL else "ltr"
    back_link = (
        f'<a href="{esc(site + "/" + navigation["path"], quote=True)}">{esc(navigation["label"])}</a>'
        if navigation else ""
    )
    hourly = "—" if result["hourly_net_minor"] is None else money_text(result["hourly_net_minor"])
    hours = "" if result["hours_spent"] is None else f"{result['hours_spent']:g}"
    calculation = (
        f"{copy['income_total']} = {money_text(result['income_total_minor'])}\n"
        f"{copy['expense_total']} = {money_text(result['expense_total_minor'])}\n"
        f"{copy['profit']} = {money_text(result['income_total_minor'])} − {money_text(result['expense_total_minor'])} = {money_text(result['profit_minor'])}\n"
        f"{copy['margin']} = {money_text(result['profit_minor'])} ÷ {money_text(result['income_total_minor'])} = {percent_text(result['margin'])}\n"
        f"{copy['hourly_net']} = {money_text(result['profit_minor'])} ÷ {hours or '—'} = {hourly}"
    )
    totals = "".join(
        f'<div><p>{esc(copy[key])}</p><output class="total-value" id="{ident}">{value}</output></div>'
        for key, ident, value in (
            ("income_total", "income-total", money_text(result["income_total_minor"])),
            ("expense_total", "expense-total", money_text(result["expense_total_minor"])),
            ("profit", "profit-total", money_text(result["profit_minor"])),
            ("margin", "margin-total", percent_text(result["margin"])),
            ("hourly_net", "hourly-net", hourly),
        )
    )
    template_item = {"name": "", "kind": "income", "amount": "0"}
    return f"""<!doctype html>
<html lang="{locale}" dir="{direction}">
{head}
<body><main>
<nav>{back_link}<span>Lumi Studio</span></nav>
<h1>{esc(copy['title'])}</h1><p>{esc(copy['intro'])}</p>
<section class="panel" aria-label="{esc(copy['title'], quote=True)}">
<form id="hero-form" autocomplete="off">
<fieldset id="hero-fields" disabled>
<div class="fields">
<div><label for="project-name">{esc(copy['project'])}</label><input id="project-name" type="text" maxlength="120" value="{esc(sample['input']['project_name'], quote=True)}" required autocomplete="off"></div>
<div><label for="hours-spent">{esc(copy['hours'])}</label><input id="hours-spent" type="text" inputmode="decimal" maxlength="8" value="{esc(sample['input']['hours_spent'], quote=True)}" autocomplete="off"><p class="small">{esc(copy['hours_hint'])}</p></div>
</div>
<div id="profit-rows">{rows}</div>
<template id="profit-template">{profit_row(copy, template_item, 0)}</template>
<div class="actions"><button type="button" id="add-income">{esc(copy['add_income'])}</button><button type="button" id="add-expense">{esc(copy['add_expense'])}</button><span class="small">{esc(copy['row_limit'])}</span></div>
<div class="totals profit-totals" aria-label="{esc(copy['result'], quote=True)}">
{totals}
</div>
<p id="hero-status" role="status" aria-live="polite"></p>
<div class="actions"><button type="button" class="primary" id="download-csv" disabled>{esc(copy['download'])}</button><button type="button" id="reset-example">{esc(copy['reset'])}</button></div>
</fieldset></form><p class="small">{esc(copy['privacy'])}</p>
</section>
<section class="panel" id="worked-example">
<h2>{esc(copy['example'])}</h2><p>{esc(copy['example_note'])}</p>
{profit_table(copy, result)}
<a class="button" href="{csv_url}" download>{esc(copy['download_example'])}</a>
<h2>{esc(copy['method'])}</h2><p>{esc(copy['formula'])}</p>
<pre class="formula">{esc(calculation)}</pre>
<p>{esc(copy['limits'])}</p>
<ul class="small">
<li>{esc(copy['amount'])}: <bdi dir="ltr">0 ≤ x ≤ 100,000,000</bdi></li>
<li>{esc(copy['hours'])}: <bdi dir="ltr">0.25 ≤ h ≤ 2000</bdi></li>
<li>{esc(copy['income'])} / {esc(copy['expense'])}: <bdi dir="ltr">1 ≤ n ≤ 20</bdi></li>
</ul>
</section>
<section class="panel optional-apps"><h2>{esc(copy['optional'])}</h2><p>{esc(copy['optional_note'])}</p><div class="actions">{app_buttons(apps)}</div></section>
<footer><p>{esc(copy['disclosure'])}</p><a href="{site}/{INTENTS}">{esc(copy['sources'])}</a> · <a href="{site}/{feed_path(locale)}">{esc(copy['feed'])}</a></footer>
</main></body></html>
"""


def battery_months(copy: dict, item: dict) -> str:
    if item["status"] == "no_wear_yet":
        return copy["no_wear_yet"]
    if item["status"] == "at_or_below_80":
        return copy["at_or_below_80"]
    return f"{item['months_to_80_low']}–{item['months_to_80_high']}"


def battery_summary_text(copy: dict, summary: dict) -> str:
    if summary["soonest_status"] == "at_or_below_80":
        return copy["at_or_below_80"]
    if summary["soonest_status"] == "no_wear_yet":
        return copy["no_wear_yet"]
    return f"{summary['soonest_low']}–{summary['soonest_high']}"


def battery_totals(copy: dict, result: dict) -> str:
    esc = html.escape
    summary = result["summary"]
    estimate = f'<span class="estimate">{esc(copy["marker_estimated"])}</span>'
    provided = f'<span class="estimate">{esc(copy["marker_provided"])}</span>'
    return (
        f'<div class="totals battery-totals" aria-label="{esc(copy["result"], quote=True)}">'
        f'<div><p>{esc(copy["item"])}</p><output class="total-value" id="device-count">{summary["devices"]}</output></div>'
        f'<div><p>{esc(copy["capacity"])}{provided}</p><output class="total-value" id="lowest-capacity">{summary["min_capacity_pct"]}</output></div>'
        f'<div><p>{esc(copy["months_to_80"])}{estimate}</p><output class="total-value" id="soonest-80" dir="ltr">{esc(battery_summary_text(copy, summary))}</output></div>'
        "</div>"
    )


def battery_row(copy: dict, item: dict, index: int, result: dict | None = None) -> str:
    esc = html.escape
    fields = []
    for key, label, mode, length in (
        ("name", "item", "text", 120), ("purchase_month", "purchase_month", "numeric", 7),
        ("max_capacity_pct", "capacity", "numeric", 3), ("cycle_count", "cycles", "numeric", 4),
    ):
        ident = f"device-{index}-{key}"
        required = "" if key == "cycle_count" else " required"
        fields.append(
            f'<div class="{key.replace("_", "-")}-field"><label data-label="{key}" for="{ident}">{esc(copy[label])}</label>'
            f'<input id="{ident}" data-field="{key}" type="text" inputmode="{mode}" maxlength="{length}" '
            f'value="{esc(str(item.get(key, "")), quote=True)}"{required} autocomplete="off"></div>'
        )
    age = str(result["age_months"]) if result else "—"
    wear = f"{result['wear_low']:.2f}–{result['wear_high']:.2f}" if result else "—"
    months = battery_months(copy, result) if result else "—"
    cycles = ("—" if result["cycles_per_month"] is None else f"{result['cycles_per_month']:.1f}") if result else "—"
    estimate = f'<span class="estimate">{esc(copy["marker_estimated"])}</span>'
    return (
        '<div class="battery-row">' + "".join(fields)
        + f'<div><p class="output-label">{esc(copy["age"])}{estimate}</p><output data-output="age">{age}</output></div>'
        + f'<div><p class="output-label">{esc(copy["wear_rate"])}{estimate}</p><output data-output="wear" dir="ltr">{wear}</output></div>'
        + f'<div><p class="output-label">{esc(copy["months_to_80"])}{estimate}</p><output data-output="months" dir="ltr">{esc(months)}</output></div>'
        + f'<div><p class="output-label">{esc(copy["cycles_per_month"])}{estimate}</p><output data-output="cycles">{cycles}</output></div>'
        + f'<button type="button" data-remove aria-label="{esc(copy["remove"] + " · " + str(item.get("name", "")), quote=True)}">'
        + esc(copy["remove"]) + "</button></div>"
    )


def battery_table(copy: dict, result: dict) -> str:
    esc = html.escape
    headings = "".join(
        f'<th scope="col">{esc(text)}</th>'
        for text in (
            copy["item"], copy["purchase_month"], copy["capacity"], copy["cycles"], copy["age"],
            f"{copy['wear_rate']} ({copy['low']})", f"{copy['wear_rate']} ({copy['high']})",
            f"{copy['months_to_80']} ({copy['low']})", f"{copy['months_to_80']} ({copy['high']})",
            copy["source_marker"],
        )
    )
    rows = []
    for item in result["items"]:
        text = None if item["status"] == "estimated" else battery_months(copy, item)
        provided = [copy["purchase_month"], copy["capacity"]] + ([copy["cycles"]] if item["cycle_count"] is not None else [])
        marker = (
            f"{copy['marker_provided']}: {', '.join(provided)}; "
            f"{copy['marker_estimated']}: {copy['age']}, {copy['wear_rate']}, {copy['months_to_80']}"
        )
        values = (
            item["name"], item["purchase_month"], str(item["max_capacity_pct"]),
            "" if item["cycle_count"] is None else str(item["cycle_count"]), str(item["age_months"]),
            f"{item['wear_low']:.2f}", f"{item['wear_high']:.2f}",
            text if text is not None else str(item["months_to_80_low"]),
            text if text is not None else str(item["months_to_80_high"]),
            marker,
        )
        rows.append("<tr>" + "".join(f"<td>{esc(value)}</td>" for value in values) + "</tr>")
    footer = (copy["today"], result["today"]) + ("",) * 8
    return (
        '<div class="table-scroll"><table><thead><tr>' + headings + "</tr></thead><tbody>"
        + "".join(rows) + '</tbody><tfoot><tr class="example-total">'
        + "".join(f"<td>{esc(value)}</td>" for value in footer)
        + "</tr></tfoot></table></div>"
    )


def render_battery_page(task: dict, locale: str, copy: dict, sample: dict, apps: list[dict],
                        modified: str, site: str, assets: dict, navigation: dict | None = None) -> str:
    esc = html.escape
    csv_url = f"{site}/{example_path(task, locale)}"
    result = sample["result"]
    rows = "".join(
        battery_row(copy, item, index + 1, result["items"][index])
        for index, item in enumerate(sample["input"]["items"])
    )
    config = {"adapter": task["adapter"], "slug": task["slug"], "locale": locale, "copy": copy, "example": sample["input"]}
    head = page_head(task, locale, copy, site, assets, modified, tool_schema(task, locale, copy, site, modified), config)
    direction = "rtl" if locale in RTL else "ltr"
    back_link = (
        f'<a href="{esc(site + "/" + navigation["path"], quote=True)}">{esc(navigation["label"])}</a>'
        if navigation else ""
    )
    calculation = "\n".join(
        f"{item['name']}: (100 − {item['max_capacity_pct']}) ÷ {item['age_months']} = "
        f"{(100 - item['max_capacity_pct']) / item['age_months']:.2f} %/{copy['age']} → ±25% → "
        f"{item['wear_low']:.2f}–{item['wear_high']:.2f}; ({item['max_capacity_pct']} − 80) ÷ {copy['wear_rate']} → "
        f"{battery_months(copy, item)}"
        for item in result["items"]
    )
    template_item = {"name": "", "purchase_month": sample["input"]["items"][0]["purchase_month"],
                     "max_capacity_pct": "100", "cycle_count": ""}
    legend = (
        f'<p class="marker-legend"><span>{esc(copy["marker_provided"])}: {esc(copy["purchase_month"])}, {esc(copy["capacity"])}, {esc(copy["cycles"])}</span>'
        f'<span>{esc(copy["marker_estimated"])}: {esc(copy["age"])}, {esc(copy["wear_rate"])}, {esc(copy["months_to_80"])}, {esc(copy["cycles_per_month"])}</span></p>'
    )
    return f"""<!doctype html>
<html lang="{locale}" dir="{direction}">
{head}
<body><main>
<nav>{back_link}<span>Lumi Studio</span></nav>
<h1>{esc(copy['title'])}</h1><p>{esc(copy['intro'])}</p>
<section class="panel" aria-label="{esc(copy['title'], quote=True)}">
<form id="hero-form" autocomplete="off">
<fieldset id="hero-fields" disabled>
<div class="fields">
<div><label for="today-month">{esc(copy['today'])}</label><input id="today-month" type="text" inputmode="numeric" maxlength="7" value="{sample['input']['today']}" required autocomplete="off"></div>
<div><p class="output-label">{esc(copy['range_note'])}</p>{legend}</div>
</div>
<div id="battery-rows">{rows}</div>
<template id="battery-template">{battery_row(copy, template_item, 0)}</template>
<div class="actions"><button type="button" id="add-device">{esc(copy['add'])}</button><span class="small">{esc(copy['row_limit'])}</span><span class="small">{esc(copy['cycles_hint'])}</span></div>
{battery_totals(copy, result)}
<p id="hero-status" role="status" aria-live="polite"></p>
<div class="actions"><button type="button" class="primary" id="download-csv" disabled>{esc(copy['download'])}</button><button type="button" id="reset-example">{esc(copy['reset'])}</button></div>
</fieldset></form><p class="small">{esc(copy['privacy'])}</p>
</section>
<section class="panel" id="worked-example">
<h2>{esc(copy['example'])}</h2><p>{esc(copy['example_note'])}</p>
{battery_table(copy, result)}
<a class="button" href="{csv_url}" download>{esc(copy['download_example'])}</a>
<h2>{esc(copy['method'])}</h2><p>{esc(copy['formula'])}</p>
<pre class="formula">{esc(calculation)}</pre>
<p>{esc(copy['limits'])}</p>
<ul class="small">
<li>{esc(copy['capacity'])}: <bdi dir="ltr">60 ≤ x ≤ 100</bdi></li>
<li>{esc(copy['cycles'])}: <bdi dir="ltr">0 ≤ x ≤ 3000</bdi></li>
<li>{esc(copy['age'])}: <bdi dir="ltr">1 ≤ m ≤ 240</bdi></li>
<li>{esc(copy['item'])}: <bdi dir="ltr">1 ≤ n ≤ 10</bdi></li>
</ul>
</section>
<section class="panel optional-apps"><h2>{esc(copy['optional'])}</h2><p>{esc(copy['optional_note'])}</p><div class="actions">{app_buttons(apps)}</div></section>
<footer><p>{esc(copy['disclosure'])}</p><a href="{site}/{INTENTS}">{esc(copy['sources'])}</a> · <a href="{site}/{feed_path(locale)}">{esc(copy['feed'])}</a></footer>
</main></body></html>
"""


def resource_block(locale: str, tasks: list[dict], copy: dict, site: str,
                   task_copies: dict | None = None) -> str:
    def own(task: dict) -> dict:
        overlay = (task_copies or {}).get(task["id"], {}).get(locale)
        return {**copy, **overlay} if overlay else copy
    cards = "".join(
        f'<article><h2>{html.escape(own(task)["title"])}</h2><p>{html.escape(own(task)["intro"])}</p>'
        f'<a class="button" href="{site}/{resource_path(task, locale)}">{html.escape(own(task)["result"])}</a> '
        f'<a href="{site}/{example_path(task, locale)}" download>{html.escape(own(task)["download_example"])}</a>'
        f'<p>{html.escape(own(task)["formula"])}</p></article>'
        for task in tasks
    )
    return f'<!-- {MARKER}:start --><section class="hero-resource" data-primary-resource="hero-task">{cards}</section><!-- {MARKER}:end -->'


def insert_block(document: str, block: str, *, index: bool = False, label: str = "") -> str:
    return insert_resource(document, block, MARKER, index=index, label=label)


def retired_indexes(pages: Path, previous: dict, site: str) -> list[str]:
    allowed = {f"{locale}/tools/index.html" for locale in OFFICIAL_LOCALES}
    retired = set(previous.get("retired_indexes", []))
    if not retired <= allowed:
        raise ValueError("Invalid retired hero-task index path")
    for locale in OFFICIAL_LOCALES:
        relative = f"{locale}/tools/index.html"
        path = safe_path(pages, relative)
        if not path.is_file():
            continue
        source = path.read_text(encoding="utf-8")
        if generated_index(source):
            require_retirable_index(source, MARKER, label=relative)
            retired.add(relative)
        elif useful_navigation(source, locale, f"{site}/{relative}", MARKER, tools=True):
            retired.discard(relative)
        elif relative in retired:
            raise ValueError(f"Retired index reappeared without verified ownership or useful content: {relative}")
    return sorted(retired)


def navigation_target(pages: Path, locale: str, copy: dict, site: str) -> dict | None:
    for relative, tools in (
        (f"{locale}/tools/index.html", True),
        (f"{locale}/index.html", False),
        (f"{locale}/hubs/index.html", False),
    ):
        path = safe_path(pages, relative)
        if path.is_file() and useful_navigation(
            path.read_text(encoding="utf-8"), locale, f"{site}/{relative}", MARKER, tools=tools
        ):
            return {"path": relative, "label": copy["tools"] if tools else "iOS App Guide"}
    return None


def answer_card_index(pages: Path, locale: str) -> dict[str, list[str]]:
    """Answer pages per App Store ID whose decision card names that App.

    gen_app_decision_cards only emits a card for a verified live App, so the
    card is the closure evidence; nothing here is inferred from prose."""
    folder = safe_path(pages, f"{locale}/answers")
    index: dict[str, list[str]] = {}
    if not folder.is_dir():
        return index
    for path in sorted(folder.glob("*.html")):
        source = path.read_text(encoding="utf-8")
        start = source.find(CARD_START)
        if start < 0:
            continue
        end = source.find(CARD_END, start)
        if end < 0:
            continue
        for app_id in sorted(set(re.findall(r"/id(\d{9,12})(?:[?\"'&]|$)", source[start:end]))):
            index.setdefault(app_id, []).append(f"{locale}/answers/{path.name}")
    return index


def secondary_answers(index: dict[str, list[str]], app_id: str, primary: str) -> list[str]:
    return [relative for relative in index.get(app_id, []) if relative != primary][:SECONDARY_LIMIT]


def integrate(pages: Path, tasks: list[dict], copy: dict, apps: dict, site: str,
              task_copies: dict | None = None, secondary: dict[str, list[str]] | None = None) -> dict[str, str]:
    changes = {}
    for locale in OFFICIAL_LOCALES:
        index = f"{locale}/tools/index.html"
        path = safe_path(pages, index)
        if path.is_file():
            source = path.read_text(encoding="utf-8")
            if not generated_index(source):
                block = resource_block(locale, tasks, copy[locale], site, task_copies)
                changes[index] = (
                    insert_block(source, block, index=True, label=index)
                    if useful_navigation(source, locale, f"{site}/{index}", MARKER, tools=True)
                    else without_resource(source, MARKER)
                )
        card_index = answer_card_index(pages, locale)
        for task in tasks:
            own_block = resource_block(locale, [task], copy[locale], site, task_copies)
            for key in task["apps"]:
                answer = apps[(locale, key)]["answer_path"]
                source = changes.get(answer) or safe_path(pages, answer).read_text(encoding="utf-8")
                changes[answer] = insert_block(source, own_block, label=answer)
                for relative in secondary_answers(card_index, apps[(locale, key)]["app_store_id"], answer):
                    if relative in changes:
                        continue
                    source = safe_path(pages, relative).read_text(encoding="utf-8")
                    try:
                        changes[relative] = insert_block(source, own_block, label=relative)
                    except ValueError:
                        # A second-tier page without a real primary heading/CTA
                        # boundary is left untouched; the primary answer above
                        # is the one that must always integrate.
                        continue
                    if secondary is not None:
                        secondary.setdefault(f"{locale}/{key}", []).append(relative)
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
            "retired_indexes": {"type": "array", "uniqueItems": True, "items": {"type": "string"}},
            "secondary_integrations": {"type": "object", "additionalProperties": {
                "type": "array", "uniqueItems": True, "maxItems": SECONDARY_LIMIT, "items": {"type": "string"},
            }},
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
    task_copies = load_task_i18n(i18n)
    inventory, apps = catalogs(pages, tasks, site, provider)
    previous_path = safe_path(pages, MANIFEST)
    previous = json.loads(previous_path.read_text()) if previous_path.is_file() else {}
    retired = retired_indexes(pages, previous, site)
    navigation = {locale: navigation_target(pages, locale, copy[locale], site) for locale in OFFICIAL_LOCALES}
    calculated = examples(tasks, copy, task_copies)
    used_assets = [
        path for adapter in sorted({task["adapter"] for task in tasks})
        for path in ADAPTER_ASSETS[adapter].values()
    ]
    asset_paths = {
        path: f"assets/hero-tasks/{digest(path.read_bytes())[:16]}-{path.name}"
        for path in ASSET_FILES if path in used_assets
    }
    source_digest = digest(json_text({
        "sources": {
            str(path.name): digest(path.read_bytes())
            for path in (Path(__file__), registry, i18n, *ASSET_FILES,
                         HERE / "hero_task_html.py", HERE / "sync_standard_site.py")
        },
        "inventory": sorted(inventory), "bindings": list(apps.values()),
        "site": site, "provider": provider, "navigation": navigation, "retired_indexes": retired,
    }).encode())
    modified = today
    if previous.get("content_digest") == source_digest:
        previous_date = previous["date_modified"]
        if date.fromisoformat(previous_date).isoformat() != previous_date or previous_date > today:
            raise ValueError("Invalid previous semantic date")
        modified = previous_date
    outputs = {relative: path.read_bytes() for path, relative in asset_paths.items()}
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
            own = task_copy(copy, task_copies, task, locale)
            assets = {key: asset_paths[path] for key, path in ADAPTER_ASSETS[task["adapter"]].items()}
            page = render_page(task, locale, own, sample, optional, modified, site, assets, navigation[locale])
            existing_path = safe_path(pages, relative)
            existing = existing_path.read_text(encoding="utf-8") if existing_path.is_file() else ""
            page = preserve_managed_links(existing, page, label=relative)
            outputs[relative] = page.encode()
            csv_path = example_path(task, locale)
            outputs[csv_path] = sample["csv"].encode()
            record = {
                "task_id": task["id"], "adapter": task["adapter"], "locale": locale,
                "url": f"{site}/{relative}", "path": relative,
                "example_url": f"{site}/{csv_path}",
                "navigation_url": f"{site}/{navigation[locale]['path']}" if navigation[locale] else None,
                "apps": [{"key": app["key"], "app_store_url": app["app_store_url"]} for app in optional],
            }
            records.append(record)
            feed_items.append({
                "id": record["url"], "url": record["url"], "title": own["title"],
                "content_text": own["intro"] + " " + own["formula"] + " " + own["limits"],
                "language": locale, "date_modified": f"{modified}T00:00:00Z",
                "attachments": [{"url": record["example_url"], "mime_type": "text/csv",
                                 "title": own["download_example"], "size_in_bytes": len(outputs[csv_path])}],
                "_hero_task": {"adapter": task["adapter"], "optional_apps": record["apps"]},
            })
        outputs[feed_path(locale)] = json_text({
            "version": "https://jsonfeed.org/version/1.1", "title": copy[locale]["feed"],
            "home_page_url": (
                f"{site}/{navigation[locale]['path']}" if navigation[locale]
                else f"{site}/{resource_path(tasks[0], locale)}"
            ),
            "feed_url": f"{site}/{feed_path(locale)}",
            "language": locale, "authors": [{"name": "Lumi Studio", "url": site}], "items": feed_items,
        }).encode()
    outputs[SITEMAP] = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="{NAMESPACE}">\n'
        + "".join(f'<url><loc>{html.escape(row["url"])}</loc><lastmod>{modified}</lastmod></url>\n' for row in records)
        + "</urlset>\n"
    ).encode()
    outputs[SCHEMA] = json_text(manifest_schema()).encode()
    secondary: dict[str, list[str]] = {}
    integrations = integrate(pages, tasks, copy, apps, site, task_copies, secondary)
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
        "integrations": sorted(integrations), "retired_indexes": retired,
        "secondary_integrations": {key: sorted(paths) for key, paths in sorted(secondary.items())},
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
    retiring = {}
    for relative in manifest["retired_indexes"]:
        path = safe_path(pages, relative)
        if path.is_file():
            original = path.read_bytes()
            require_retirable_index(original.decode("utf-8"), MARKER, label=relative)
            retiring[relative] = digest(original)
    stale = sorted(set(previous.get("outputs", {})) - set(outputs))
    for relative in stale:
        path = safe_path(pages, relative)
        if path.exists() and digest(path.read_bytes()) != previous["outputs"][relative]:
            raise ValueError(f"Refusing to delete modified stale output: {relative}")
    changed = [relative for relative, content in outputs.items()
               if not safe_path(pages, relative).is_file() or safe_path(pages, relative).read_bytes() != content]
    if check and (changed or stale or retiring):
        raise ValueError(f"Hero-task output gate failed ({len(changed)}, retiring {len(retiring)}): {', '.join(changed[:8])}")
    if not check:
        for relative in changed:
            path = safe_path(pages, relative)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(outputs[relative])
        for relative in stale:
            safe_path(pages, relative).unlink(missing_ok=True)
        for relative, expected in retiring.items():
            path = safe_path(pages, relative)
            if digest(path.read_bytes()) != expected:
                raise ValueError(f"Retiring index changed concurrently: {relative}")
            path.unlink()
    return {
        "tasks": manifest["task_count"], "locales": 50,
        "supported_apps": len(manifest["supported_app_keys"]),
        "unserved_apps": len(manifest["unserved_app_keys"]),
        "pages": len(manifest["records"]), "changed": len(changed),
        "removed": len(stale) + len(retiring),
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
