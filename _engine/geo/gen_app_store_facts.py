#!/usr/bin/env python3
"""Publish verified storefront price and rating facts on localized app pages."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import re
from typing import Any

from app_store_storefronts import (
    LOCALE_STOREFRONTS,
    load_storefront_availability,
    load_storefront_details,
    localized_storefront_detail,
    verified_app_store_url,
)
from appstore_live import live_app_keys
import gen_mobile_app_identity
import gen_smart_app_banners
from official_locales import OFFICIAL_LOCALES, OFFICIAL_LOCALE_SET
from videogen.registry import APPS, APPSTORE


HERE = Path(__file__).resolve().parent
PAGES = HERE / "pages"
ASSET_NAME = "app-store-facts-v1.css"
STYLE_START = "<!-- app-store-facts-style:start -->"
STYLE_END = "<!-- app-store-facts-style:end -->"
FACT_START = "<!-- app-store-facts:start -->"
FACT_END = "<!-- app-store-facts:end -->"
STYLE_RE = re.compile(
    rf"{re.escape(STYLE_START)}.*?{re.escape(STYLE_END)}",
    flags=re.DOTALL,
)
FACT_RE = re.compile(
    rf"{re.escape(FACT_START)}.*?{re.escape(FACT_END)}",
    flags=re.DOTALL,
)
HEAD_END_RE = re.compile(r"</head\s*>", flags=re.IGNORECASE)
MAIN_END_RE = re.compile(r"</main\s*>", flags=re.IGNORECASE)

ASSET_SOURCE = """.iag-store-facts{margin:1rem 0 0;max-width:100%;overflow-x:auto;scrollbar-width:none;-webkit-overflow-scrolling:touch}
.iag-store-facts::-webkit-scrollbar{display:none}
.iag-store-facts__link{display:inline-flex;align-items:center;gap:.45rem;min-height:44px;padding:.7rem .9rem;border:1px solid rgba(148,163,184,.32);border-radius:999px;background:rgba(255,255,255,.72);box-shadow:0 10px 28px rgba(15,23,42,.08);color:#0f172a;font-size:.9rem;font-weight:700;line-height:1;text-decoration:none;white-space:nowrap}
.iag-store-facts__link:focus-visible{outline:3px solid #2563eb;outline-offset:3px}
@media(hover:hover){.iag-store-facts__link:hover{border-color:rgba(37,99,235,.55);box-shadow:0 12px 32px rgba(15,23,42,.13)}}
@media(prefers-color-scheme:dark){.iag-store-facts__link{background:rgba(15,23,42,.82);border-color:rgba(148,163,184,.38);color:#f8fafc}}
"""


def _style_block(site: str) -> str:
    return (
        f"{STYLE_START}\n"
        f'<link rel="stylesheet" '
        f'href="{site.rstrip("/")}/assets/{ASSET_NAME}">\n'
        f"{STYLE_END}"
    )


def _fact_block(detail: dict[str, object], store_url: str) -> str:
    price = html.escape(str(detail["price"]), quote=True)
    formatted_price = html.escape(
        str(detail["formatted_price"]),
        quote=True,
    )
    store_url = html.escape(store_url, quote=True)
    rating = ""
    if "rating_value" in detail and "rating_count" in detail:
        rating_value = f"{float(detail['rating_value']):.1f}"
        rating_count = int(detail["rating_count"])
        rating = (
            '<span aria-hidden="true">&middot;</span>'
            '<span class="iag-store-facts__rating">'
            '<span aria-hidden="true">&#9733;</span> '
            f'<data value="{rating_value}">{rating_value}</data>/5 '
            '<span aria-hidden="true">&middot;</span> '
            f'<data value="{rating_count}">{rating_count}</data>'
            "</span>"
        )
    return (
        f"{FACT_START}\n"
        '<aside class="iag-store-facts" aria-label="App Store">\n'
        f'<a class="iag-store-facts__link" href="{store_url}" '
        'rel="nofollow noopener">\n'
        "<span>App Store</span>"
        '<span aria-hidden="true">&middot;</span>'
        f'<data value="{price}">{formatted_price}</data>'
        f"{rating}\n"
        "</a>\n"
        "</aside>\n"
        f"{FACT_END}"
    )


def _offer(detail: dict[str, object], store_url: str) -> dict[str, object]:
    return {
        "@type": "Offer",
        "price": str(detail["price"]),
        "priceCurrency": str(detail["currency"]),
        "url": store_url,
        "availability": "https://schema.org/InStock",
    }


def _aggregate_rating(
    detail: dict[str, object],
) -> dict[str, object] | None:
    if "rating_value" not in detail or "rating_count" not in detail:
        return None
    return {
        "@type": "AggregateRating",
        "ratingValue": float(detail["rating_value"]),
        "ratingCount": int(detail["rating_count"]),
        "bestRating": 5,
        "worstRating": 1,
    }


def _update_schema(
    source: str,
    path: Path,
    app_id: str,
    detail: dict[str, object] | None,
    store_url: str,
    *,
    managed: bool,
) -> str:
    if detail is None and not managed:
        return source
    records: list[tuple[re.Match[str], Any, list[dict[str, Any]]]] = []
    matches: list[dict[str, Any]] = []
    for match in gen_mobile_app_identity.JSON_LD_RE.finditer(source):
        try:
            document = json.loads(match.group("body"))
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid JSON-LD in {path}: {error}") from error
        nodes = list(gen_mobile_app_identity._iter_nodes(document))
        for node in nodes:
            if (
                "MobileApplication"
                in gen_mobile_app_identity._schema_types(node)
                and app_id
                in gen_mobile_app_identity._node_app_store_ids(node)
            ):
                matches.append(node)
        records.append((match, document, nodes))
    if len(matches) != 1:
        raise ValueError(
            f"Expected one MobileApplication for {app_id} in {path}: "
            f"{len(matches)}"
        )
    target = matches[0]
    before = json.dumps(target, ensure_ascii=False, sort_keys=True)
    if detail is None:
        target.pop("offers", None)
        target.pop("aggregateRating", None)
    else:
        target["offers"] = _offer(detail, store_url)
        rating = _aggregate_rating(detail)
        if rating is None:
            target.pop("aggregateRating", None)
        else:
            target["aggregateRating"] = rating
    after = json.dumps(target, ensure_ascii=False, sort_keys=True)
    if before == after:
        return source

    parts: list[str] = []
    cursor = 0
    for match, document, nodes in records:
        parts.append(source[cursor : match.start()])
        if any(node is target for node in nodes):
            parts.extend(
                (
                    match.group("open"),
                    "\n",
                    json.dumps(document, ensure_ascii=False, indent=2),
                    "\n",
                    match.group("close"),
                )
            )
        else:
            parts.append(match.group(0))
        cursor = match.end()
    parts.append(source[cursor:])
    return "".join(parts)


def ensure_page_facts(
    path: Path,
    app_id: str,
    locale: str,
    detail: dict[str, object] | None,
    store_url: str,
    *,
    site: str,
) -> bool:
    source = path.read_text(encoding="utf-8")
    for start, end, label in (
        (STYLE_START, STYLE_END, "style"),
        (FACT_START, FACT_END, "facts"),
    ):
        start_count = source.count(start)
        end_count = source.count(end)
        if start_count != end_count or start_count > 1:
            raise ValueError(
                f"Malformed App Store {label} block in {path}"
            )
    page_url, language = gen_mobile_app_identity._page_metadata(
        source,
        path,
        site,
    )
    expected_url = f"{site.rstrip('/')}/{locale}/{path.name}"
    if page_url != expected_url or language != locale:
        raise ValueError(
            f"Unexpected localized app page identity in {path}: "
            f"{language} {page_url}"
        )
    managed = FACT_START in source
    updated = _update_schema(
        source,
        path,
        app_id,
        detail,
        store_url,
        managed=managed,
    )
    if detail is None:
        updated = STYLE_RE.sub("", updated, count=1)
        updated = FACT_RE.sub("", updated, count=1)
    else:
        style = _style_block(site)
        facts = _fact_block(detail, store_url)
        if STYLE_START in updated:
            updated = STYLE_RE.sub(style, updated, count=1)
        else:
            matches = list(HEAD_END_RE.finditer(updated))
            if len(matches) != 1:
                raise ValueError(
                    f"Localized app page must have one closing head: {path}"
                )
            match = matches[0]
            updated = (
                updated[: match.start()]
                + style
                + "\n"
                + updated[match.start() :]
            )
        if FACT_START in updated:
            updated = FACT_RE.sub(facts, updated, count=1)
        else:
            matches = list(MAIN_END_RE.finditer(updated))
            if len(matches) != 1:
                raise ValueError(
                    f"Localized app page must have one closing main: {path}"
                )
            match = matches[0]
            updated = (
                updated[: match.start()]
                + facts
                + "\n"
                + updated[match.start() :]
            )
    if updated == source:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def write_asset(pages: Path) -> bool:
    path = pages / "assets" / ASSET_NAME
    if path.is_file() and path.read_text(encoding="utf-8") == ASSET_SOURCE:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(ASSET_SOURCE, encoding="utf-8")
    return True


def generate(
    pages: Path = PAGES,
    *,
    live_keys: set[str] | None = None,
    locales: tuple[str, ...] = OFFICIAL_LOCALES,
    site: str = gen_smart_app_banners.SITE,
) -> dict[str, int]:
    site = site.rstrip("/")
    if live_keys is None:
        live_keys = set(
            live_app_keys(APPSTORE, str(pages), refresh=False)
        )
    if not live_keys:
        raise ValueError("App Store facts require verified live apps")
    unknown = set(live_keys) - (set(APPSTORE) & set(APPS))
    if unknown:
        raise ValueError(f"Unknown live apps: {sorted(unknown)}")
    if (
        not locales
        or len(locales) != len(set(locales))
        or not set(locales).issubset(OFFICIAL_LOCALE_SET)
    ):
        raise ValueError(
            "App Store fact locales must be unique official locales"
        )

    availability = load_storefront_availability(pages)
    details = load_storefront_details(pages)
    changed = 0
    facts = 0
    rated = 0
    for locale in locales:
        country = LOCALE_STOREFRONTS[locale]
        for key in sorted(live_keys):
            app_id = str(APPSTORE[key])
            path = pages / locale / f"{key}.html"
            if not path.is_file():
                raise FileNotFoundError(
                    f"Missing localized app page: {path}"
                )
            canonical_store = (
                gen_mobile_app_identity.canonical_store_url(app_id)
            )
            store_url = verified_app_store_url(
                canonical_store,
                locale,
                availability,
            )
            detail = None
            if app_id in availability.get(country, frozenset()):
                detail = details.get(country, {}).get(app_id)
            if detail is not None:
                detail = localized_storefront_detail(detail, locale)
                if store_url == canonical_store:
                    raise ValueError(
                        f"Verified facts require a storefront URL: "
                        f"{locale}/{key}"
                    )
                facts += 1
                rated += int("rating_value" in detail)
            changed += int(
                ensure_page_facts(
                    path,
                    app_id,
                    locale,
                    detail,
                    store_url,
                    site=site,
                )
            )
    return {
        "apps": len(live_keys),
        "locales": len(locales),
        "pages": len(live_keys) * len(locales),
        "facts": facts,
        "rated": rated,
        "without_facts": len(live_keys) * len(locales) - facts,
        "changed": changed,
        "asset_changed": int(write_asset(pages)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=Path, default=PAGES)
    parser.add_argument("--site", default=gen_smart_app_banners.SITE)
    args = parser.parse_args()
    stats = generate(args.pages, site=args.site)
    print(
        "Verified App Store facts: "
        + ", ".join(f"{key}={value}" for key, value in stats.items())
    )


if __name__ == "__main__":
    main()
