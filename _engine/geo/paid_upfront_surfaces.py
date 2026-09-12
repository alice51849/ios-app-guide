#!/usr/bin/env python3
"""Source-bound corrections for existing paid-upfront acquisition pages."""
from __future__ import annotations

import argparse
from functools import lru_cache
import html
import json
from pathlib import Path
import re

import app_store_storefronts as stores
from answer_text import concise_meta
import market_availability as market
from site_config import PUBLIC_SITE
from videogen.registry import APPS, APPSTORE


HERE = Path(__file__).resolve().parent
COPY_PATH = HERE / "data/paid_upfront_surface_repairs.json"
EXACT_IDS = {
    "aim990plus": "6792483140", "dailymate": "6790418321",
    "gmoney": "6755782939", "hourstag": "6754218117",
    "lumimathpro": "6776958488", "lumimissionpro": "6779745474",
    "snapport": "6780575828", "wifiaid": "6790467886",
    "wordmate": "6789917808",
}
ARTICLE_RE = re.compile(
    r'(<article\b[^>]*class="[^"]*\banswer\b[^"]*"[^>]*>)(.*?)(</article>)',
    re.S,
)
SECTION_RE = re.compile(r"<section\b[^>]*>.*?</section>", re.S)
JSON_RE = re.compile(
    r'(<script\b[^>]*type="application/ld\+json"[^>]*>)(.*?)(</script>)', re.S,
)
LEAD_RE = re.compile(r'<p\b[^>]*class="[^"]*\blead\b[^"]*"[^>]*>(.*?)</p>', re.S)
CLARIFY_RE = re.compile(
    r"<!-- paid-upfront-clarification:start -->.*?"
    r"<!-- paid-upfront-clarification:end -->", re.S,
)
INTRO_RE = re.compile(
    r"<!-- paid-upfront-intro:start -->.*?<!-- paid-upfront-intro:end -->", re.S,
)


@lru_cache(maxsize=1)
def contract():
    document = json.loads(COPY_PATH.read_text())
    if document["schema"] != "lumi.paid-upfront-existing-surfaces/v1":
        raise ValueError("Unknown paid-upfront surface contract")
    if {key: row["app_id"] for key, row in document["apps"].items()} != EXACT_IDS:
        raise ValueError("The paid-upfront repair must retain exact9 identities")
    for key, row in document["apps"].items():
        if APPSTORE.get(key) != row["app_id"] or APPS[key].get("purchase_model") != "paid_upfront":
            raise ValueError(f"Paid-upfront registry identity changed: {key}")
        if row["business_model"] != "paid_upfront" or not re.fullmatch(r"[0-9a-f]{64}", row["description_sha256"]):
            raise ValueError(f"Invalid public product evidence: {key}")
    return document


@lru_cache(maxsize=1)
def targets():
    document = contract()
    result = {
        path: {"key": key, "locale": "en-US", "kind": "review"}
        for path, key in document["reviews"].items()
    }
    for row in document["answers"]:
        result[f'{row["locale"]}/answers/{row["slug"]}.html'] = {**row, "kind": "answer"}
        if row.get("include_root"):
            result[f'answers/{row["slug"]}.html'] = {**row, "kind": "answer"}
    for row in document["landings"]:
        result[f'{row["locale"]}/{row["key"]}.html'] = {**row, "kind": "landing"}
    if len(result) != 13 or {row["key"] for row in result.values()} != set(EXACT_IDS):
        raise ValueError("Existing-surface repair scope changed")
    return result


def require_available(key, locale, pages, availability=None):
    contract()
    app_id = EXACT_IDS[key]
    country = stores.LOCALE_STOREFRONTS.get(locale)
    if availability is None:
        availability = stores.load_storefront_availability(pages)
    if market.is_unavailable(locale, app_id) or app_id not in availability.get(country, ()):
        raise ValueError(f"Unverified paid-app storefront: {key}/{locale}")
    return f"https://apps.apple.com/{country}/app/id{app_id}"


def localized_descriptions(key, values):
    """Override only owned copy, without changing the underlying ASC metadata."""
    result = dict(values)
    for row in contract()["landings"]:
        if row["key"] == key and row["locale"] in values:
            result[row["locale"]] = {
                **values[row["locale"]],
                "description": "\n\n".join([row["intro"], *row["description"]]),
            }
    return result


def _one(pattern, replacement, source, label):
    updated, count = re.subn(pattern, replacement, source, count=0, flags=re.S)
    if count != 1:
        raise ValueError(f"Expected one {label}, found {count}")
    return updated


def _faq(items):
    return "\n".join(
        '<div itemscope itemtype="https://schema.org/Question">'
        f'<h3 itemprop="name">{html.escape(question)}</h3>'
        '<div itemprop="acceptedAnswer" itemscope itemtype="https://schema.org/Answer">'
        f'<p itemprop="text">{html.escape(answer)}</p></div></div>'
        for question, answer in items
    )


def _faq_schema(items):
    return [
        {"@type": "Question", "name": question,
         "acceptedAnswer": {"@type": "Answer", "text": answer}}
        for question, answer in items
    ]


def _nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _nodes(child)


def _schemas(source, row):
    def replace(match):
        document = json.loads(match[2])
        before = json.dumps(document, ensure_ascii=False, sort_keys=True)
        for node in list(_nodes(document)):
            types = node.get("@type") or []
            types = {types} if isinstance(types, str) else set(types)
            if "FAQPage" in types:
                existing = node.get("mainEntity", [])
                if row.get("mode") == "clarify":
                    if not existing:
                        raise ValueError("Missing existing Wordmate FAQ schema")
                    node["mainEntity"] = _faq_schema(row["faq"]) + existing[1:]
                else:
                    node["mainEntity"] = _faq_schema(row["faq"])
            if "HowTo" in types and "steps" in row:
                node["name"] = contract()["labels"][row["locale"]]["steps"]
                node["step"] = [
                    {"@type": "HowToStep", "position": i + 1, "name": step, "text": step}
                    for i, step in enumerate(row["steps"])
                ]
            if "BreadcrumbList" in types and row.get("heading"):
                node["itemListElement"][-1]["name"] = row["heading"]
            if types & {"SoftwareApplication", "MobileApplication"} and (
                EXACT_IDS[row["key"]] in json.dumps(node)
            ):
                node["description"] = (
                    "\n\n".join([row["intro"], *row["description"]])
                    if row["kind"] == "landing" else row.get("fits", row["lead"])
                )
                node.pop("aggregateRating", None)
                node.pop("review", None)
            if types & {"WebPage", "Article"} and row.get("heading"):
                for field in ("name", "headline"):
                    if field in node:
                        node[field] = row["heading"]
                if "description" in node:
                    node["description"] = concise_meta(row["lead"], hard_limit=220)
        if before == json.dumps(document, ensure_ascii=False, sort_keys=True):
            return match[0]
        rendered = json.dumps(document, ensure_ascii=False, indent=2).replace("<", "\\u003c")
        return match[1] + "\n" + rendered + "\n" + match[3]
    return JSON_RE.sub(replace, source)


def _metadata(source, row):
    lead = row.get("lead", row.get("intro", ""))
    meta = concise_meta(lead, hard_limit=220)

    def replace(match):
        tag = match[0]
        if re.search(r'(?:name|property)="(?:description|og:description|twitter:description)"', tag):
            return re.sub(r'content="[^"]*"', lambda _: f'content="{html.escape(meta, quote=True)}"', tag)
        if row.get("heading") and re.search(r'(?:name|property)="(?:og:title|twitter:title)"', tag):
            return re.sub(r'content="[^"]*"', lambda _: f'content="{html.escape(row["heading"], quote=True)}"', tag)
        return tag

    source = re.sub(r"<meta\b[^>]*>", replace, source)
    if row.get("heading"):
        heading = html.escape(row["heading"])
        source = _one(r"(<h1\b[^>]*>).*?(</h1>)", lambda m: m[1] + heading + m[2], source, "heading")
        source = _one(r"(<title>).*?(</title>)", lambda m: m[1] + heading + " | iOS App Guide" + m[2], source, "title")
    return source


def _article(row):
    labels = contract()["labels"][row["locale"]]
    e = html.escape
    body = f'<h2>{e(labels["short"])}</h2>'
    body += "".join(f"<p>{e(text)}</p>" for text in row["paras"])
    for label, field, tag in (("look", "look", "ul"), ("steps", "steps", "ol")):
        body += f'<h2>{e(labels[label])}</h2><{tag} class="checklist">'
        body += "".join(f"<li>{e(text)}</li>" for text in row[field])
        body += f"</{tag}>"
    body += f'<h2>{e(labels["compare"])}</h2><table><thead><tr>'
    body += "".join(f"<th>{e(labels[key])}</th>" for key in ("need", "check", "why"))
    body += "</tr></thead><tbody>"
    body += "".join("<tr>" + "".join(f"<td>{e(text)}</td>" for text in cells) + "</tr>" for cells in row["rows"])
    body += f'</tbody></table><h2>{e(labels["fits"])}</h2><p>{e(row["fits"])}</p>'
    body += f'<p class="notice">{e(labels["disclosure"])}</p>'
    for title, url in row.get("sources", []):
        body += f'<p><a href="{e(url, quote=True)}" rel="noopener">{e(title)}</a></p>'
    return body


def _answer(source, row):
    leads = LEAD_RE.findall(source)
    if len(leads) != 1:
        raise ValueError("Expected one existing answer lead")
    source = LEAD_RE.sub(
        lambda m: m[0].replace(m[1], html.escape(row["lead"])), source
    )
    # Card promises may escape apostrophes differently from the source lead.
    def card_promise(match):
        opening = re.sub(
            r'title="[^"]*"', lambda _: f'title="{html.escape(row["lead"], quote=True)}"',
            match[1],
        )
        return opening + html.escape(row["lead"]) + match[3]
    source = re.sub(
        r'(<p\b[^>]*class="iag-decision-card__promise"[^>]*>)(.*?)(</p>)',
        card_promise, source, flags=re.S,
    )
    if row["mode"] == "clarify":
        source = CLARIFY_RE.sub("", source)
        addition = (
            '<!-- paid-upfront-clarification:start -->'
            f'<p>{html.escape(row["addition"])}</p>'
            '<!-- paid-upfront-clarification:end -->'
        )
        source, count = ARTICLE_RE.subn(
            lambda m: m[1] + re.sub(r"(</h2>)", lambda h: h[1] + addition, m[2], count=1) + m[3],
            source,
        )
    else:
        source, count = ARTICLE_RE.subn(lambda m: m[1] + _article(row) + m[3], source)
    if count != 1:
        raise ValueError("Expected one existing answer article")

    sections = [
        match for match in SECTION_RE.finditer(source)
        if 'itemtype="https://schema.org/Question"' in match[0]
    ]
    if len(sections) != 1:
        raise ValueError("Expected one existing visible FAQ section")
    match = sections[0]
    items = row["faq"]
    if row["mode"] == "clarify":
        faq_nodes = []
        for script in JSON_RE.finditer(source):
            for node in _nodes(json.loads(script[2])):
                if node.get("@type") == "FAQPage":
                    faq_nodes.append(node)
        if len(faq_nodes) != 1:
            raise ValueError("Expected one existing Wordmate FAQ")
        items = items + [
            [node["name"], node["acceptedAnswer"]["text"]]
            for node in faq_nodes[0]["mainEntity"][1:]
        ]
    label = contract()["labels"][row["locale"]]["faq"]
    replacement = f'<section class="wrap card"><h2>{html.escape(label)}</h2>{_faq(items)}</section>'
    return source[:match.start()] + replacement + source[match.end():]


def _landing(source, row):
    source = INTRO_RE.sub("", source)
    intro = (
        '<!-- paid-upfront-intro:start -->'
        f'<p class="paid-upfront-intro">{html.escape(row["intro"])}</p>'
        '<!-- paid-upfront-intro:end -->'
    )
    source = _one(r"(<h1\b[^>]*>.*?</h1>)", lambda m: m[1] + intro, source, "landing heading")
    before = rf"(<h2>{re.escape(html.escape(row['what']))}</h2>).*?(?=<h2>{re.escape(html.escape(row['features']))}</h2>)"
    description = "".join(f"<p>{html.escape(text)}</p>" for text in row["description"])
    source = _one(before, lambda m: m[1] + description, source, "landing description")
    before = rf"(<h2>{re.escape(html.escape(row['faq_label']))}</h2>).*?(?=<h2>{re.escape(html.escape(row['download_label']))}</h2>)"
    return _one(before, lambda m: m[1] + _faq(row["faq"]), source, "landing FAQ")


def _ctas(source, relative, row, availability):
    import gen_app_store_qr_ctas as qr
    import gen_store_attribution as attribution

    source, _ = attribution.rewrite(
        source, attribution.page_token(relative, source), "118326163",
        locale=row["locale"], availability=availability,
    )
    match = attribution.QR_CARD_LINK_RE.search(source)
    if match:
        href = html.unescape(match["href"])
        asset = qr.qr_asset_relative(EXACT_IDS[row["key"]], href)
        source = _one(
            r'(class="app-store-qr-card__image"\s+src=")[^"]+(")',
            lambda m: m[1] + f"{PUBLIC_SITE}/{asset.as_posix()}" + m[2],
            source, "existing QR image",
        )
        if attribution.qr_card_desync(source) is not None:
            raise ValueError(f"QR does not match the verified CTA: {relative}")
    return source


def rewrite(source, relative, pages, *, availability=None):
    row = targets().get(str(relative))
    if row is None or row["kind"] == "review":
        return source
    if availability is None:
        availability = stores.load_storefront_availability(pages)
    require_available(row["key"], row["locale"], pages, availability)
    canonical = f"{PUBLIC_SITE}/{relative}"
    if f'rel="canonical" href="{canonical}"' not in source:
        raise ValueError(f"Source canonical does not own {relative}")
    if f'id{EXACT_IDS[row["key"]]}' not in source:
        raise ValueError(f"Missing exact paid App ID in {relative}")
    source = _landing(source, row) if row["kind"] == "landing" else _answer(source, row)
    source = _schemas(_metadata(source, row), row)
    return _ctas(source, relative, row, availability)


def build(pages, *, check=False):
    pages = Path(pages).resolve()
    availability = stores.load_storefront_availability(pages)
    planned = {}
    assets = {}
    for relative, row in targets().items():
        path = pages / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Refusing to create or follow a new surface: {relative}")
        before = path.read_text()
        require_available(row["key"], row["locale"], pages, availability)
        if row["kind"] == "review":
            if (
                f'rel="canonical" href="{PUBLIC_SITE}/{relative}"' not in before
                or f'id{EXACT_IDS[row["key"]]}' not in before
            ):
                raise ValueError(f"Review source identity changed: {relative}")
            import gen_review_pages
            review = next(item for item in gen_review_pages.REVIEWS if item["key"] == row["key"])
            after = gen_review_pages.render(review, pages=pages)
        else:
            after = rewrite(before, relative, pages, availability=availability)
        if after != before:
            planned[relative] = after
        import gen_app_store_qr_ctas as qr
        import gen_store_attribution as attribution
        match = attribution.QR_CARD_LINK_RE.search(after)
        if match:
            href = html.unescape(match["href"])
            asset = qr.qr_asset_relative(EXACT_IDS[row["key"]], href)
            raw = qr.qr_svg(EXACT_IDS[row["key"]], href).encode()
            path = pages / asset
            if path.is_symlink():
                raise ValueError(f"Refusing a symlink QR asset: {asset}")
            if not path.exists() or path.read_bytes() != raw:
                assets[asset] = raw
    if check and (planned or assets):
        raise ValueError(f"Stale paid-upfront surfaces: {sorted(planned)}; QR assets: {len(assets)}")
    for relative, raw in assets.items():
        path = pages / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    for relative, source in planned.items():
        (pages / relative).write_text(source, encoding="utf-8")
    return {"apps": 9, "existing_surfaces": 13, "changed": sorted(planned),
            "qr_assets_changed": [p.as_posix() for p in sorted(assets)],
            "new_pages": 0, "provider_requests": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build(args.pages, check=args.check), ensure_ascii=False))


if __name__ == "__main__":
    main()
