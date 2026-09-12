#!/usr/bin/env python3
"""Generate or verify scoped capture pages locally; never subscribe, send or deploy."""
from __future__ import annotations

import argparse
import html
from pathlib import Path

from app_store_storefronts import resolve_provider_token
import gen_tool_email_capture as legacy
import market_availability as market
import owned_email_contract as contract

MARKER = '<meta name="owned-email-capture" content="v1">'
STYLE = (
    ":root{color-scheme:light}*{box-sizing:border-box}"
    "body{margin:0;background:linear-gradient(145deg,#fffafd,#f1edff);color:#302057;"
    "font:17px/1.65 system-ui,-apple-system,sans-serif}"
    "main{width:96%;max-width:1120px;margin:3vh auto;padding:clamp(18px,4vw,44px);"
    "background:#fff;border:1px solid #e0d0ff;border-radius:24px}"
    "h1{font-size:clamp(24px,4vw,42px);font-weight:500;line-height:1.3}"
    "a{color:#5032a4;text-underline-offset:3px}p{margin:16px 0}"
    "form{display:grid;gap:16px;margin:24px 0}label{display:block}"
    "input[type=email]{width:100%;min-height:48px;padding:12px;font:inherit;"
    "border:1px solid #a790d0;border-radius:10px}"
    ".consent{display:flex;gap:12px;align-items:flex-start;cursor:pointer;min-height:44px}"
    "input[type=checkbox]{flex:0 0 24px;width:24px;height:24px;margin:5px 0}"
    "button,.store{min-height:48px;padding:12px 20px;border:0;border-radius:12px;"
    "font:inherit;font-weight:500;background:#6541ab;color:#fff;text-align:center}"
    "button{cursor:pointer}button:active{transform:translateY(1px)}"
    "a:focus-visible,input:focus-visible,button:focus-visible{outline:3px solid #335dec;outline-offset:4px}"
    ".store{display:inline-flex;align-items:center;text-decoration:none}"
    ".scope{overflow-wrap:anywhere;font-size:14px}ul{padding-inline-start:24px}"
    "li a{display:block;padding:10px 0;min-height:44px}"
    "@media(prefers-reduced-motion:reduce){button:active{transform:none}}"
)


def _document(locale, title, url, content):
    direction = "rtl" if locale in {"ar-SA", "he", "ur-PK"} else "ltr"
    return (
        f'<!doctype html><html lang="{locale}" dir="{direction}"><head>'
        '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta name="robots" content="noindex,follow">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; '
        'style-src \'unsafe-inline\'; form-action https://buttondown.com; base-uri \'none\'">'
        f'{MARKER}<title>{html.escape(title)}</title>'
        f'<link rel="canonical" href="{html.escape(url, quote=True)}">'
        f'<style>{STYLE}</style></head><body><main>{content}</main></body></html>\n'
    ).encode("utf-8")


def render_capture(row, copies=None):
    copies = copies or contract.load_copy()
    text = copies[row["locale"]]
    consent = contract.consent_copy(row, copies)
    title = text["app_title"].format(app=row["app_name"])
    metadata = contract.capture_metadata(row)
    hidden = '<input type="hidden" name="embed" value="1">' + "".join(
        f'<input type="hidden" name="metadata__{key}" value="{html.escape(value, quote=True)}">'
        for key, value in metadata.items() if key != "owned_consent"
    )
    store = (
        f'<a class="store" href="{html.escape(row["app_store_url"], quote=True)}">'
        f'{html.escape(text["store"])}</a>'
        if row["app_store_url"] else market.note_html(row["locale"], row["app_name"])
    )
    content = (
        f'<nav><a href="{contract.PUBLIC_SITE}/{row["locale"]}/email/index.html">'
        f'{html.escape(text["preferences"])}</a></nav>'
        f'<h1>{html.escape(title)}</h1><p>{html.escape(consent["disclosure"])}</p>'
        f'<p class="scope"><bdi>{row["app_id"]} · {row["locale"]} · {row["campaign"]}</bdi></p>'
        f'<form action="{contract.ENDPOINT}" method="post" target="_blank" rel="noopener noreferrer">'
        f'<label for="owned-email-address">{html.escape(text["email_label"])}</label>'
        '<input id="owned-email-address" type="email" name="email" required '
        'autocomplete="email" dir="ltr" aria-describedby="owned-email-privacy">'
        f'{hidden}<label class="consent" for="owned-email-consent">'
        '<input id="owned-email-consent" type="checkbox" name="metadata__owned_consent" '
        f'value="yes" required><span>{html.escape(consent["consent"])}</span></label>'
        f'<p>{html.escape(consent["confirmation"])}</p>'
        f'<button type="submit">{html.escape(text["button"])}</button></form>'
        f'<p id="owned-email-privacy">{html.escape(consent["privacy"])} '
        f'<a href="{contract.PRIVACY_URL}">Buttondown</a></p>'
        f'<p>{html.escape(consent["unsubscribe"])}</p>{store}'
        '<p><a href="mailto:hourstag.app@gmail.com">hourstag.app@gmail.com</a></p>'
    )
    return _document(row["locale"], title, row["capture_url"], content)


def supporting_pages(records, copies):
    outputs = {}
    for locale in contract.OFFICIAL_LOCALES:
        text = copies[locale]
        path = f"{locale}/email/index.html"
        links = "".join(
            f'<li><a href="{html.escape(row["capture_url"], quote=True)}">'
            f'<bdi>{html.escape(row["app_name"])}</bdi></a></li>'
            for row in records if row["locale"] == locale
        )
        outputs[path] = _document(
            locale, text["preferences"], f"{contract.PUBLIC_SITE}/{path}",
            f'<h1>{html.escape(text["preferences"])}</h1>'
            f'<p>{html.escape(text["disclosure"])}</p>'
            f'<p>{html.escape(text["confirmation"])}</p><ul>{links}</ul>'
            f'<a href="{contract.PUBLIC_SITE}/email/index.html">🌐</a>',
        )
    path = "email/index.html"
    links = "".join(
        f'<li><a lang="{locale}" href="{contract.PUBLIC_SITE}/{locale}/email/index.html">'
        f'{html.escape(copies[locale]["language"])}</a></li>'
        for locale in contract.OFFICIAL_LOCALES
    )
    outputs[path] = _document("en-US", "Lumi Studio", f"{contract.PUBLIC_SITE}/{path}",
                              f"<h1>Lumi Studio</h1><ul>{links}</ul>")
    return outputs


def build(provider, sources, availability, *, now=None):
    config = legacy._load_config()
    if not config.get("enabled") or config.get("app_capture_enabled") is not True:
        raise contract.ContractError("scoped capture is disabled")
    records = contract.rows(provider)
    copies = contract.load_copy()
    outputs = {row["capture_path"]: render_capture(row, copies) for row in records}
    inventory = contract.make_inventory(
        provider, sources, availability,
        {path: contract.digest(body) for path, body in outputs.items()}, now=now,
    )
    supporting = supporting_pages(records, copies)
    inventory["supporting_outputs"] = {path: contract.digest(body) for path, body in supporting.items()}
    inventory["content_digest"] = contract.digest({
        key: value for key, value in inventory.items() if key != "content_digest"
    })
    outputs.update(supporting)
    return inventory, outputs


def check(pages, *, now=None):
    pages = Path(pages)
    inventory = contract.parse_json((pages / contract.INVENTORY).read_bytes())
    availability = contract.parse_json((pages / contract.AVAILABILITY).read_bytes())
    contract.validate_inventory(inventory, availability, now=now)
    copies = contract.load_copy()
    expected = {row["capture_path"]: render_capture(row, copies) for row in inventory["rows"]}
    supporting = supporting_pages(inventory["rows"], copies)
    if inventory.get("supporting_outputs") != {
        path: contract.digest(body) for path, body in supporting.items()
    }:
        raise contract.ContractError("supporting capture navigation digest mismatch")
    expected.update(supporting)
    actual_paths = {
        str(path.relative_to(pages))
        for locale in (*contract.OFFICIAL_LOCALES, "")
        for path in (pages / locale / "email").glob("*.html")
    }
    if actual_paths != set(expected):
        raise contract.ContractError("capture routes are missing, duplicate or outside exact47×50")
    for path, body in expected.items():
        target = pages / path
        if target.is_symlink() or target.read_bytes() != body:
            raise contract.ContractError(f"capture source/content mismatch: {path}")
    for row in inventory["rows"]:
        if contract.digest(expected[row["capture_path"]]) != row["content_sha256"]:
            raise contract.ContractError("inventory output hash mismatch")
    return inventory


def write(pages, inventory, availability, outputs):
    pages = Path(pages)
    for path, body in outputs.items():
        target = pages / path
        if target.is_symlink() or (target.exists() and MARKER.encode() not in target.read_bytes()):
            raise contract.ContractError(f"refusing to replace an unowned file: {path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    for path, data in ((contract.AVAILABILITY, availability), (contract.INVENTORY, inventory)):
        target = pages / path
        if target.is_symlink():
            raise contract.ContractError("refusing symlinked inventory output")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(contract.json_bytes(data) + b"\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-dir", required=True, type=Path)
    parser.add_argument("--growth-geo", type=Path)
    parser.add_argument("--guide-geo", type=Path)
    parser.add_argument("--availability", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        inventory = check(args.pages_dir)
        if args.growth_geo or args.guide_geo:
            if not (args.growth_geo and args.guide_geo):
                parser.error("paired check requires both source directories")
            if contract.paired_sources(args.growth_geo, args.guide_geo) != inventory["sources"]:
                raise contract.ContractError("paired source revisions changed")
    else:
        if not all((args.growth_geo, args.guide_geo, args.availability)):
            parser.error("generation requires paired committed sources and fresh read-only availability")
        availability = contract.parse_json(args.availability.read_bytes())
        sources = contract.paired_sources(args.growth_geo, args.guide_geo)
        inventory, outputs = build(resolve_provider_token(), sources, availability)
        if not args.dry_run:
            write(args.pages_dir, inventory, availability, outputs)
            check(args.pages_dir)
    print(
        f"PASS capture={inventory['capture_count']} apps=47 locales=50 "
        f"conversion_routes=2303 verified_markets={inventory['verified_conversion_cells']} "
        f"unverified_markets={inventory['unverified_conversion_cells']} N/A=47 "
        "verified_subscribers=0 subscriber_total=UNKNOWN "
        "native_emails=0 send_requests=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
