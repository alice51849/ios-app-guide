#!/usr/bin/env python3
"""Add truthful, localized App Store decision cards to high-intent pages."""

from __future__ import annotations

import argparse
import html
import os
from pathlib import Path
import re
import sys
import urllib.parse


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))
sys.path.insert(0, str(HERE))

from appstore_live import live_app_keys  # noqa: E402
from app_store_storefronts import (  # noqa: E402
    campaign_app_store_url,
    has_trusted_promotional_rating,
    load_storefront_availability,
    verified_app_store_url,
)
import gen_smart_app_banners  # noqa: E402
import gen_store_attribution  # noqa: E402
from official_locales import OFFICIAL_LOCALE_SET  # noqa: E402
from videogen.registry import APPS, APPSTORE  # noqa: E402


PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
ASSET_NAME = "app-decision-card-v1.css"
ASSET_RELATIVE = Path("assets") / ASSET_NAME
STYLE_START = "<!-- app-decision-card-style:start -->"
STYLE_END = "<!-- app-decision-card-style:end -->"
CARD_START = "<!-- app-decision-card:start -->"
CARD_END = "<!-- app-decision-card:end -->"
FEED_DISCOVERY_ANCHOR = (
    '<link rel="alternate" type="application/atom+xml"'
)
STYLE_RE = re.compile(
    rf"\s*{re.escape(STYLE_START)}.*?{re.escape(STYLE_END)}\s*",
    flags=re.DOTALL,
)
CARD_RE = re.compile(
    rf"\s*{re.escape(CARD_START)}.*?{re.escape(CARD_END)}\s*",
    flags=re.DOTALL,
)
STORE_FACT_RE = re.compile(
    r"<!-- app-store-facts:start -->"
    r"(?P<body>.*?)"
    r"<!-- app-store-facts:end -->",
    flags=re.DOTALL,
)
STORE_DATA_RE = re.compile(
    r'<data\s+value="(?P<value>[^"]+)">(?P<label>.*?)</data>',
    flags=re.DOTALL,
)
DECIMAL_RE = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")
HEAD_END_RE = re.compile(r"</head\s*>", flags=re.IGNORECASE)
H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", flags=re.IGNORECASE | re.DOTALL)
TAGLINE_RE = re.compile(
    r"<p\b[^>]*>\s*<strong\b[^>]*>(.*?)</strong>\s*</p>",
    flags=re.IGNORECASE | re.DOTALL,
)
LEAD_RE = re.compile(
    r'<p\b(?=[^>]*\bclass\s*=\s*["\'][^"\']*\blead\b[^"\']*["\'])'
    r"[^>]*>(.*?)</p>",
    flags=re.IGNORECASE | re.DOTALL,
)
PILL_RE = re.compile(
    r'<span\b(?=[^>]*\bclass\s*=\s*["\'][^"\']*\bpill\b[^"\']*["\'])'
    r"[^>]*>(.*?)</span>",
    flags=re.IGNORECASE | re.DOTALL,
)
UL_RE = re.compile(r"<ul\b[^>]*>(.*?)</ul>", flags=re.IGNORECASE | re.DOTALL)
LI_RE = re.compile(r"<li\b[^>]*>(.*?)</li>", flags=re.IGNORECASE | re.DOTALL)
SECTION_PARAGRAPH_RE = re.compile(
    r"<h2\b[^>]*>.*?</h2>\s*<p\b[^>]*>(.*?)</p>",
    flags=re.IGNORECASE | re.DOTALL,
)
ANCHOR_RE = re.compile(
    r"<a\b(?P<attrs>[^>]*)>(?P<label>.*?)</a>",
    flags=re.IGNORECASE | re.DOTALL,
)
HREF_RE = re.compile(
    r'\bhref\s*=\s*(?P<quote>["\'])(?P<href>.*?)(?P=quote)',
    flags=re.IGNORECASE | re.DOTALL,
)
ANSWER_HERO_RE = re.compile(
    r'<section\b(?=[^>]*\bclass\s*=\s*["\'][^"\']*\bhero\b[^"\']*["\'])'
    r"[^>]*>.*?</section>",
    flags=re.IGNORECASE | re.DOTALL,
)
TAG_RE = re.compile(r"<[^>]+>")


STYLESHEET = """\
.iag-decision-card {
  display: grid;
  grid-template-columns: clamp(5.25rem, 14vw, 7.5rem) minmax(0, 1fr);
  gap: clamp(0.9rem, 3vw, 1.5rem);
  inline-size: min(100%, 64rem);
  margin-block: clamp(0.75rem, 2.5vw, 1.5rem) clamp(1.5rem, 4vw, 2.5rem);
  margin-inline: auto;
  padding: clamp(0.9rem, 3vw, 1.4rem);
  overflow: visible;
  color: #f8fafc;
  background:
    radial-gradient(circle at 0 0, rgba(125, 211, 252, 0.22), transparent 42%),
    linear-gradient(135deg, #0f172a, #312e81 58%, #581c87);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: clamp(1.1rem, 3vw, 1.75rem);
  box-shadow: 0 22px 58px rgba(15, 23, 42, 0.24);
  text-align: start;
}

.iag-decision-card__icon {
  display: block;
  inline-size: 100%;
  block-size: auto;
  aspect-ratio: 1;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 22%;
  box-shadow: 0 14px 32px rgba(0, 0, 0, 0.3);
}

.iag-decision-card__body {
  display: grid;
  min-inline-size: 0;
  align-content: center;
  gap: 0.55rem;
}

.iag-decision-card__title,
.iag-decision-card__promise,
.iag-decision-card__terms,
.iag-decision-card__storefront,
.iag-decision-card__fact,
.iag-decision-card__cta {
  min-inline-size: 0;
  white-space: nowrap;
}

.iag-decision-card__title {
  color: #fff;
  font-size: clamp(1.2rem, 1rem + 1vw, 1.85rem);
  font-weight: 850;
  line-height: 1.1;
}

.iag-decision-card__promise,
.iag-decision-card__terms {
  margin: 0;
  color: rgba(248, 250, 252, 0.84);
  font-size: clamp(0.68rem, 0.62rem + 0.7vw, 1rem);
  line-height: 1.35;
}

.iag-decision-card__facts {
  display: flex;
  min-inline-size: 0;
  gap: 0.4rem;
  flex-wrap: wrap;
  overflow: visible;
}

.iag-decision-card__storefront {
  display: inline-flex;
  inline-size: fit-content;
  max-inline-size: 100%;
  align-items: center;
  gap: 0.35rem;
  padding: 0.32rem 0.58rem;
  color: #f5f3ff;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.iag-decision-card__storefront data {
  color: inherit;
}

.iag-decision-card__fact {
  flex: 0 0 auto;
  padding: 0.28rem 0.55rem;
  color: #eef2ff;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 999px;
  font-size: 0.76rem;
  font-weight: 720;
}

.iag-decision-card__cta {
  display: inline-flex;
  inline-size: fit-content;
  max-inline-size: 100%;
  min-block-size: 2.75rem;
  align-items: center;
  justify-content: center;
  padding: 0.68rem 1rem;
  color: #111827 !important;
  background: #fff;
  border-radius: 999px;
  box-shadow: 0 9px 24px rgba(0, 0, 0, 0.2);
  font-weight: 820;
  line-height: 1.2;
  text-decoration: none;
}

.iag-decision-card__cta:visited {
  color: #111827 !important;
}

.iag-decision-card__cta:focus-visible {
  outline: 3px solid #fde68a;
  outline-offset: 4px;
}

@media (max-width: 34rem) {
  .iag-decision-card {
    grid-template-columns: minmax(0, 1fr);
    gap: 0.8rem;
  }

  .iag-decision-card__icon {
    inline-size: 4.75rem;
  }

  .iag-decision-card__cta {
    inline-size: 100%;
    font-size: clamp(0.7rem, 3.5vw, 1rem);
  }
}

@media (hover: hover) {
  .iag-decision-card__cta:hover {
    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.28);
    transform: translateY(-1px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .iag-decision-card__cta {
    transition: none;
  }
}

@media print {
  .iag-decision-card {
    color: #000;
    background: #fff;
    border: 1px solid #000;
    box-shadow: none;
  }

  .iag-decision-card__title,
  .iag-decision-card__promise,
  .iag-decision-card__terms,
  .iag-decision-card__storefront {
    color: #000;
  }

  .iag-decision-card__cta {
    display: none;
  }
}
"""


def page_campaign(path: Path, pages: Path) -> str:
    """Campaign token for the page this card is being written into.

    The decision card used to mint a fixed ``iag_decision`` token.  Since the
    2026-08-20 taxonomy collapse ``gen_store_attribution`` rewrites every store
    anchor to ``geo_ask``/``geo_pick``/``geo_learn``, and it runs *after* the
    QR generator has already hashed the pre-rewrite URL into the QR image file
    name — so a stale constant here silently desynchronises the QR code from
    the link beside it.  Mint the final token here instead, from the same
    function the attribution pass uses, so the URL never changes underneath.
    """
    root = pages.resolve()
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root).as_posix()
    except ValueError:
        relative = path.name
    return gen_store_attribution.campaign_token(relative)


def _plain_text(fragment: str) -> str:
    return " ".join(html.unescape(TAG_RE.sub(" ", fragment)).split())


def _campaign_url(
    url: str,
    app_id: str,
    locale: str = "en-US",
    availability: dict[str, frozenset[str]] | None = None,
    campaign: str = gen_store_attribution.campaign_token(""),
) -> str:
    parsed = urllib.parse.urlsplit(html.unescape(url))
    path = re.fullmatch(r"/(?:[a-z]{2}/)?app/id(\d+)", parsed.path)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "apps.apple.com"
        or path is None
        or path.group(1) != app_id
        or parsed.fragment
        or locale not in OFFICIAL_LOCALE_SET
    ):
        raise ValueError(f"Invalid decision-card App Store URL: {url}")
    parameters = urllib.parse.parse_qs(
        parsed.query,
        keep_blank_values=True,
        strict_parsing=False,
    )
    provider_values = parameters.get("pt", [])
    if len(provider_values) > 1:
        raise ValueError(f"Invalid decision-card provider token: {url}")
    canonical = f"https://apps.apple.com/app/id{app_id}"
    destination = verified_app_store_url(
        canonical,
        locale,
        availability or {},
    )
    return campaign_app_store_url(
        destination,
        campaign,
        provider_token=provider_values[0] if provider_values else None,
    )


def _store_link(
    source: str,
    app_id: str,
    locale: str,
    availability: dict[str, frozenset[str]],
    campaign: str = gen_store_attribution.campaign_token(""),
) -> tuple[str, str]:
    for anchor in ANCHOR_RE.finditer(source):
        href_match = HREF_RE.search(anchor.group("attrs"))
        if not href_match:
            continue
        href = html.unescape(href_match.group("href"))
        try:
            store_url = _campaign_url(
                href, app_id, locale, availability, campaign
            )
        except ValueError:
            continue
        label = _plain_text(anchor.group("label"))
        if label:
            return store_url, label
    raise ValueError(f"No App Store CTA found for app ID {app_id}")


def _facts(source: str, answer: bool) -> list[str]:
    fragments: list[str]
    if answer:
        fragments = PILL_RE.findall(source)
    else:
        feature_list = UL_RE.search(source)
        fragments = LI_RE.findall(feature_list.group(1)) if feature_list else []
    values = [_plain_text(fragment) for fragment in fragments]
    return list(dict.fromkeys(value for value in values if value))[:4]


def _terms(source: str, answer: bool) -> str:
    if answer:
        return ""
    feature_list = UL_RE.search(source)
    if not feature_list:
        return ""
    section = SECTION_PARAGRAPH_RE.search(source, feature_list.end())
    return _plain_text(section.group(1)) if section else ""


def _storefront_fact(source: str, answer: bool) -> dict[str, object] | None:
    if answer:
        return None
    block = STORE_FACT_RE.search(source)
    if block is None:
        return None
    values = [
        (html.unescape(match.group("value")), _plain_text(match.group("label")))
        for match in STORE_DATA_RE.finditer(block.group("body"))
    ]
    if len(values) not in {1, 3}:
        raise ValueError("Malformed verified App Store facts")
    price_value, formatted_price = values[0]
    if (
        DECIMAL_RE.fullmatch(price_value) is None
        or not formatted_price
        or len(formatted_price) > 64
    ):
        raise ValueError("Invalid verified App Store price")
    result: dict[str, object] = {
        "price_value": price_value,
        "formatted_price": formatted_price,
    }
    if len(values) == 3:
        rating_value, rating_label = values[1]
        rating_count, count_label = values[2]
        if (
            DECIMAL_RE.fullmatch(rating_value) is None
            or not rating_count.isdigit()
            or rating_label != rating_value
            or count_label != rating_count
            or not 0 <= float(rating_value) <= 5
            or int(rating_count) <= 0
        ):
            raise ValueError("Invalid verified App Store rating")
        candidate = {
            "rating_value": float(rating_value),
            "rating_count": int(rating_count),
        }
        if has_trusted_promotional_rating(candidate):
            result.update(
                {
                    "rating_value": rating_value,
                    "rating_count": int(rating_count),
                }
            )
    return result


def _page_content(
    source: str,
    key: str,
    app_id: str,
    answer: bool,
    locale: str = "en-US",
    availability: dict[str, frozenset[str]] | None = None,
    campaign: str = gen_store_attribution.campaign_token(""),
) -> dict[str, object]:
    heading = H1_RE.search(source)
    promise_match = (
        LEAD_RE.search(source)
        if answer
        else TAGLINE_RE.search(source) or LEAD_RE.search(source)
    )
    if not heading or not promise_match:
        raise ValueError(f"Decision-card target has no usable heading/promise for {key}")
    store_url, cta = _store_link(
        source,
        app_id,
        locale,
        availability or {},
        campaign,
    )
    promise = _plain_text(promise_match.group(1))
    if answer and promise.lower().startswith("a practical buying guide for"):
        outcome = " ".join(str(APPS[key].get("sub", "")).split()).rstrip(".")
        access = " ".join(str(APPS[key].get("tag", "")).split()).rstrip(".")
        promise = f"{outcome}. {access}." if access else f"{outcome}."
    return {
        "name": APPS[key]["name"] if answer else _plain_text(heading.group(1)),
        "promise": promise,
        "facts": _facts(source, answer),
        "terms": _terms(source, answer),
        "storefront": _storefront_fact(source, answer),
        "store_url": store_url,
        "cta": cta,
    }


def style_block(site: str = SITE) -> str:
    parsed = urllib.parse.urlsplit(site)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"Invalid decision-card site URL: {site}")
    href = f"{parsed.path.rstrip('/')}/assets/{ASSET_NAME}"
    return "\n".join((
        STYLE_START,
        f'<link rel="stylesheet" href="{html.escape(href, quote=True)}">',
        STYLE_END,
    ))


def card_block(key: str, app_id: str, content: dict[str, object]) -> str:
    esc = lambda value: html.escape(str(value), quote=True)
    facts = "".join(
        f'<span class="iag-decision-card__fact" title="{esc(fact)}">'
        f"{esc(fact)}</span>"
        for fact in content["facts"]
    )
    terms = (
        f'<p class="iag-decision-card__terms" title="{esc(content["terms"])}">'
        f'{esc(content["terms"])}</p>'
        if content["terms"]
        else ""
    )
    storefront = ""
    if content["storefront"]:
        detail = content["storefront"]
        rating = ""
        if "rating_value" in detail and "rating_count" in detail:
            rating = (
                '<span aria-hidden="true"> · </span>'
                '<span><span aria-hidden="true">★</span> '
                f'<data value="{esc(detail["rating_value"])}">'
                f'{esc(detail["rating_value"])}</data>/5'
                '<span aria-hidden="true"> · </span>'
                f'<data value="{esc(detail["rating_count"])}">'
                f'{esc(detail["rating_count"])}</data></span>'
            )
        storefront = (
            '    <div class="iag-decision-card__storefront">'
            "<span>App Store</span>"
            '<span aria-hidden="true"> · </span>'
            f'<data value="{esc(detail["price_value"])}">'
            f'{esc(detail["formatted_price"])}</data>{rating}</div>'
        )
    return "\n".join((
        CARD_START,
        (
            f'<aside class="iag-decision-card" data-app-id="{app_id}" '
            f'aria-label="{esc(content["name"])}">'
        ),
        (
            f'  <img class="iag-decision-card__icon" '
            f'src="/ios-app-guide/stories/img/{esc(key)}-icon.jpg" alt="" '
            'width="256" height="256" loading="eager" decoding="async" '
            'fetchpriority="high">'
        ),
        '  <div class="iag-decision-card__body">',
        (
            f'    <strong class="iag-decision-card__title" '
            f'title="{esc(content["name"])}">{esc(content["name"])}</strong>'
        ),
        (
            f'    <p class="iag-decision-card__promise" '
            f'title="{esc(content["promise"])}">{esc(content["promise"])}</p>'
        ),
        f'    <div class="iag-decision-card__facts">{facts}</div>',
        *([storefront] if storefront else []),
        f"    {terms}" if terms else "",
        (
            f'    <a class="iag-decision-card__cta" '
            f'href="{esc(content["store_url"])}" rel="nofollow noopener" '
            f'aria-label="{esc(content["cta"])}" title="{esc(content["cta"])}">'
            f'{esc(content["cta"])}</a>'
        ),
        "  </div>",
        "</aside>",
        CARD_END,
    ))


def _inject_style(source: str, block: str) -> str:
    match = HEAD_END_RE.search(source)
    if not match:
        raise ValueError("Decision-card target has no closing head")
    anchor = source.find(FEED_DISCOVERY_ANCHOR)
    index = anchor if 0 <= anchor < match.start() else match.start()
    return source[:index].rstrip() + "\n" + block + "\n" + source[index:].lstrip()


def _inject_card(source: str, block: str, answer: bool) -> str:
    anchor = (
        ANSWER_HERO_RE.search(source)
        if answer
        else TAGLINE_RE.search(source) or LEAD_RE.search(source)
    )
    if not anchor:
        anchor = H1_RE.search(source)
    if not anchor:
        raise ValueError("Decision-card target has no insertion anchor")
    return source[:anchor.end()].rstrip() + "\n" + block + "\n" + source[anchor.end():].lstrip()


def ensure_card(
    path: Path,
    key: str,
    app_id: str,
    pages: Path,
    site: str = SITE,
    *,
    availability: dict[str, frozenset[str]] | None = None,
) -> bool:
    source = path.read_text(encoding="utf-8")
    cleaned = CARD_RE.sub("\n", STYLE_RE.sub("\n", source))
    answer = path.parent.name == "answers"
    icon = pages / "stories" / "img" / f"{key}-icon.jpg"
    if not icon.is_file():
        raise ValueError(f"Decision-card icon is missing: {icon}")
    locale = gen_smart_app_banners._page_language(path, pages)
    locale = "en-US" if locale == "en" else locale
    if locale not in OFFICIAL_LOCALE_SET:
        raise ValueError(f"Unsupported decision-card locale: {locale}")
    content = _page_content(
        cleaned,
        key,
        app_id,
        answer,
        locale,
        availability
        if availability is not None
        else load_storefront_availability(pages),
        page_campaign(path, pages),
    )
    updated = _inject_style(cleaned, style_block(site))
    updated = _inject_card(updated, card_block(key, app_id, content), answer)
    return _write_if_changed(path, updated, previous=source)


def remove_card(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    cleaned = CARD_RE.sub("\n", STYLE_RE.sub("\n", source))
    return source != cleaned and _write_if_changed(
        path, cleaned, previous=source
    )


def _write_if_changed(
    path: Path,
    content: str,
    *,
    previous: str | None = None,
) -> bool:
    if previous is None and path.exists():
        previous = path.read_text(encoding="utf-8")
    if previous == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def generate(
    pages: Path = PAGES,
    live_keys: set[str] | None = None,
    site: str = SITE,
) -> dict[str, int]:
    if live_keys is None:
        live_keys = set(live_app_keys(APPSTORE, str(pages), refresh=False))
    targets, app_count = gen_smart_app_banners.build_targets(
        pages, set(live_keys), site
    )
    id_to_key = {str(APPSTORE[key]): key for key in live_keys}
    if len(id_to_key) != len(live_keys):
        raise ValueError("Decision-card App Store IDs must be unique")

    answer_pages = gen_smart_app_banners._answer_pages(pages)
    localized_app_pages = gen_smart_app_banners._localized_app_pages(
        pages, set(live_keys)
    )
    eligible: dict[Path, tuple[str, str]] = {}
    for path, app_id in targets.items():
        key = id_to_key.get(str(app_id))
        if not key:
            continue
        if path in answer_pages or path in localized_app_pages:
            eligible[path] = (key, str(app_id))

    availability = load_storefront_availability(pages)
    changed = int(_write_if_changed(pages / ASSET_RELATIVE, STYLESHEET))
    for path, (key, app_id) in sorted(
        eligible.items(), key=lambda item: str(item[0])
    ):
        changed += int(
            ensure_card(
                path,
                key,
                app_id,
                pages,
                site,
                availability=availability,
            )
        )

    managed = (
        answer_pages
        | gen_smart_app_banners._localized_app_pages(pages, set(APPSTORE))
        | gen_smart_app_banners._guide_pages(pages)
    )
    for path in sorted(managed - set(eligible)):
        changed += int(remove_card(path))

    product_pages = sum(
        path.parent.name != "answers" for path in eligible
    )
    answer_pages = len(eligible) - product_pages
    languages = {
        gen_smart_app_banners._page_language(path, pages) for path in eligible
    }
    return {
        "apps": app_count,
        "product_pages": product_pages,
        "answer_pages": answer_pages,
        "languages": len(languages),
        "changed_files": changed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pages", type=Path, default=PAGES, help="Alternate Pages checkout."
    )
    args = parser.parse_args()
    result = generate(args.pages)
    print(
        "App decision cards: "
        f"{result['apps']} apps, {result['product_pages']} product pages, "
        f"{result['answer_pages']} buyer-intent answer pages, "
        f"{result['languages']} languages, "
        f"{result['changed_files']} files updated"
    )


if __name__ == "__main__":
    main()
