#!/usr/bin/env python3
"""Expose verified App Store links to browser agents on every localized app page."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re

from app_store_storefronts import (
    LOCALE_STOREFRONTS,
    load_storefront_availability,
    load_storefront_details,
    localized_storefront_detail,
    required_campaign_app_store_url,
    verified_app_store_url,
)
from appstore_live import live_app_keys
import gen_mobile_app_identity
import gen_smart_app_banners
from gen_store_attribution import campaign_token
from official_locales import OFFICIAL_LOCALES, OFFICIAL_LOCALE_SET
from videogen.registry import APPS, APPSTORE


HERE = Path(__file__).resolve().parent
PAGES = HERE / "pages"
ASSET_NAME = "webmcp-install-tool-v2.js"
DATA_ID = "iag-webmcp-install-data"
BLOCK_START = "<!-- webmcp-install-tool:start -->"
BLOCK_END = "<!-- webmcp-install-tool:end -->"
BLOCK_RE = re.compile(
    rf"{re.escape(BLOCK_START)}.*?{re.escape(BLOCK_END)}",
    flags=re.DOTALL,
)
BODY_END_RE = re.compile(r"</body\s*>", flags=re.IGNORECASE)
SENTENCE_END_RE = re.compile(
    r"[.!?\u3002\uff01\uff1f\u061f\u0964\u2026]"
    r"(?:[\"'\u2019\u201d\u00bb)\]]*)"
)
MIN_COMPLETE_SENTENCE_LENGTH = 24

ASSET_SOURCE = r"""(() => {
  "use strict";
  const script = document.currentScript;
  const dataId = script?.dataset.webmcpInstall;
  const node = dataId ? document.getElementById(dataId) : null;
  if (!node || !document.modelContext?.registerTool) return;
  let data;
  try {
    data = JSON.parse(node.textContent);
    const store = new URL(data.app_store_url);
    const facts = data.storefront_facts;
    const storefronts = __LOCALE_STOREFRONTS__;
    const country = storefronts[data.page_language];
    const campaign = [...store.searchParams];
    if (
      store.protocol !== "https:" ||
      store.host !== "apps.apple.com" ||
      store.username || store.password ||
      !country ||
      ![
        `/app/id${data.app_store_id}`,
        `/${country}/app/id${data.app_store_id}`
      ].includes(store.pathname) ||
      campaign.length !== 3 ||
      campaign.map(([key]) => key).join(",") !== "pt,ct,mt" ||
      !/^[0-9]{1,20}$/.test(store.searchParams.get("pt")) ||
      store.searchParams.get("ct") !== "geo_pick" ||
      store.searchParams.get("mt") !== "8" ||
      store.hash ||
      !/^[0-9]{9,12}$/.test(data.app_store_id)
    ) throw new TypeError("Invalid verified App Store payload.");
    if (
      facts !== undefined &&
      (
        facts === null ||
        typeof facts !== "object" ||
        Array.isArray(facts) ||
        typeof facts.price !== "string" ||
        !/^(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$/.test(facts.price) ||
        typeof facts.currency !== "string" ||
        !/^[A-Z]{3}$/.test(facts.currency) ||
        typeof facts.formatted_price !== "string" ||
        !facts.formatted_price ||
        (
          (facts.rating_value === undefined) !==
          (facts.rating_count === undefined)
        ) ||
        (
          facts.rating_value !== undefined &&
          (
            typeof facts.rating_value !== "number" ||
            facts.rating_value < 0 ||
            facts.rating_value > 5 ||
            !Number.isInteger(facts.rating_count) ||
            facts.rating_count <= 0
          )
        )
      )
    ) throw new TypeError("Invalid verified App Store facts.");
  } catch (error) {
    console.error("WebMCP install data is invalid.", error);
    return;
  }
  const emptyInput = {
    type: "object",
    additionalProperties: false,
    properties: {}
  };
  function validateInput(input) {
    if (
      input === null ||
      typeof input !== "object" ||
      Array.isArray(input) ||
      Object.keys(input).length
    ) throw new TypeError("This tool does not accept input fields.");
  }
  const result = {
    result_type: "verified_ios_app_install_link",
    app_store_id: data.app_store_id,
    app_name: data.app_name,
    page_language: data.page_language,
    page_url: data.page_url,
    app_store_url: data.app_store_url,
    availability_source: "Apple public storefront lookup snapshot"
  };
  if (data.storefront_facts) {
    result.storefront_facts = data.storefront_facts;
  }
  async function register() {
    await document.modelContext.registerTool({
      name: "get_verified_ios_app_install_link",
      description:
        `Return the verified direct App Store link for ${data.app_name}. ` +
        data.localized_description,
      inputSchema: emptyInput,
      annotations: {readOnlyHint: true, untrustedContentHint: false},
      execute: async (input = {}) => {
        validateInput(input);
        return {
          content: [{type: "text", text: JSON.stringify(result)}]
        };
      }
    });
    await document.modelContext.registerTool({
      name: "open_verified_ios_app_store_listing",
      description:
        `Open the verified App Store listing for ${data.app_name}. ` +
        data.localized_description,
      inputSchema: emptyInput,
      annotations: {readOnlyHint: false, untrustedContentHint: false},
      execute: async (input = {}) => {
        validateInput(input);
        window.location.assign(data.app_store_url);
        return null;
      }
    });
  }
  register().catch(error =>
    console.error("WebMCP install tool registration failed.", error)
  );
})();
""".replace("__LOCALE_STOREFRONTS__", json.dumps(LOCALE_STOREFRONTS, sort_keys=True))


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.languages: list[str] = []
        self.canonicals: list[str] = []
        self.descriptions: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        values = {
            name.casefold(): value.strip()
            for name, value in attrs
            if value is not None
        }
        tag = tag.casefold()
        if tag == "html" and values.get("lang"):
            self.languages.append(values["lang"])
        if tag == "link":
            relations = {
                value.casefold()
                for value in values.get("rel", "").split()
            }
            if "canonical" in relations and values.get("href"):
                self.canonicals.append(values["href"])
        if (
            tag == "meta"
            and values.get("name", "").casefold() == "description"
            and values.get("content")
        ):
            self.descriptions.append(values["content"])

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        self.handle_starttag(tag, attrs)


def _page_data(
    source: str,
    path: Path,
    *,
    locale: str,
    expected_url: str,
) -> tuple[str, str]:
    parser = _PageParser()
    parser.feed(source)
    languages = list(dict.fromkeys(parser.languages))
    canonicals = list(dict.fromkeys(parser.canonicals))
    descriptions = list(dict.fromkeys(parser.descriptions))
    if languages != [locale]:
        raise ValueError(f"Unexpected page language for {path}: {languages}")
    if canonicals != [expected_url]:
        raise ValueError(f"Unexpected canonical URL for {path}: {canonicals}")
    if len(descriptions) != 1:
        raise ValueError(
            f"Localized app page must have one description: "
            f"{path} ({len(descriptions)})"
        )
    return canonicals[0], descriptions[0]


def _json_for_html(value: dict[str, object]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", r"<\/")


def _localized_tool_description(description: str) -> str:
    description = " ".join(description.split())
    matches = list(SENTENCE_END_RE.finditer(description))
    if matches and matches[-1].end() == len(description):
        return description
    if matches and matches[-1].end() >= MIN_COMPLETE_SENTENCE_LENGTH:
        return description[: matches[-1].end()].rstrip()
    return description.rstrip(" ,;:\u060c\u061b-") + "\u2026"


def install_block(
    payload: dict[str, object],
    *,
    site: str,
) -> str:
    return (
        f"{BLOCK_START}\n"
        f'<script type="application/json" id="{DATA_ID}">'
        f"{_json_for_html(payload)}</script>\n"
        f'<script src="{site.rstrip("/")}/assets/{ASSET_NAME}" '
        f'data-webmcp-install="{DATA_ID}" defer></script>\n'
        f"{BLOCK_END}"
    )


def ensure_page_tool(
    path: Path,
    payload: dict[str, str],
    *,
    site: str,
) -> bool:
    source = path.read_text(encoding="utf-8")
    start_count = source.count(BLOCK_START)
    end_count = source.count(BLOCK_END)
    if start_count != end_count or start_count > 1:
        raise ValueError(f"Malformed WebMCP install block in {path}")
    block = install_block(payload, site=site)
    if start_count:
        updated = BLOCK_RE.sub(block, source, count=1)
    else:
        matches = list(BODY_END_RE.finditer(source))
        if len(matches) != 1:
            raise ValueError(
                f"Localized app page must have one closing body: "
                f"{path} ({len(matches)})"
            )
        match = matches[0]
        updated = source[: match.start()] + block + "\n" + source[match.start() :]
    if updated == source:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def write_asset(pages: Path) -> bool:
    path = pages / "assets" / ASSET_NAME
    if path.exists() and path.read_text(encoding="utf-8") == ASSET_SOURCE:
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
        raise ValueError("WebMCP install tools require verified live apps")
    unknown = set(live_keys) - (set(APPSTORE) & set(APPS))
    if unknown:
        raise ValueError(f"Unknown live apps: {sorted(unknown)}")
    if (
        not locales
        or len(locales) != len(set(locales))
        or not set(locales).issubset(OFFICIAL_LOCALE_SET)
    ):
        raise ValueError("WebMCP install locales must be unique official locales")

    availability = load_storefront_availability(pages)
    details = load_storefront_details(pages)
    changed = 0
    localized_storefronts = 0
    fallbacks = 0
    storefront_facts = 0
    rated = 0
    for locale in locales:
        for key in sorted(live_keys):
            app_id = str(APPSTORE[key])
            path = pages / locale / f"{key}.html"
            if not path.is_file():
                raise FileNotFoundError(
                    f"Missing localized app page: {path}"
                )
            expected_url = f"{site}/{locale}/{key}.html"
            source = path.read_text(encoding="utf-8")
            page_url, description = _page_data(
                source,
                path,
                locale=locale,
                expected_url=expected_url,
            )
            canonical_store = (
                gen_mobile_app_identity.canonical_store_url(app_id)
            )
            store_url = verified_app_store_url(
                canonical_store,
                locale,
                availability,
            )
            if store_url == canonical_store:
                fallbacks += 1
            else:
                localized_storefronts += 1
            store_url = required_campaign_app_store_url(
                store_url, campaign_token(f"{locale}/{key}.html"),
                expected_locale=locale, expected_app_id=app_id,
                availability=availability,
            )
            payload = {
                "app_store_id": app_id,
                "app_name": str(APPS[key]["name"]),
                "page_language": locale,
                "page_url": page_url,
                "app_store_url": store_url,
                "localized_description": _localized_tool_description(
                    description
                ),
            }
            country = LOCALE_STOREFRONTS[locale]
            detail = details.get(country, {}).get(app_id)
            if (
                detail is not None
                and app_id in availability.get(country, frozenset())
            ):
                detail = localized_storefront_detail(detail, locale)
                payload["storefront_facts"] = detail
                storefront_facts += 1
                rated += int("rating_value" in detail)
            changed += int(
                ensure_page_tool(path, payload, site=site)
            )

    return {
        "apps": len(live_keys),
        "locales": len(locales),
        "pages": len(live_keys) * len(locales),
        "localized_storefronts": localized_storefronts,
        "fallbacks": fallbacks,
        "storefront_facts": storefront_facts,
        "rated": rated,
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
        "WebMCP install tools: "
        + ", ".join(f"{key}={value}" for key, value in stats.items())
    )


if __name__ == "__main__":
    main()
