#!/usr/bin/env python3
"""Add direct App Store QR cards for desktop and printed buyer-intent pages."""

from __future__ import annotations

import argparse
import hashlib
import html
import io
from pathlib import Path
import re
import urllib.parse

import segno

from app_store_storefronts import (
    normalize_app_store_campaign_url,
    validated_app_store_url,
)
import gen_mobile_store_ctas
import gen_smart_app_banners
from appstore_live import live_app_keys
from videogen.registry import APPSTORE


PAGES = gen_smart_app_banners.PAGES
SITE = gen_smart_app_banners.SITE
HEAD_BLOCK_START = gen_smart_app_banners.APP_STORE_QR_STYLE_BLOCK_START
HEAD_BLOCK_END = gen_smart_app_banners.APP_STORE_QR_STYLE_BLOCK_END
DECISION_STYLE_ANCHOR = "<!-- app-decision-card-style:start -->"
FEED_DISCOVERY_ANCHOR = (
    '<link rel="alternate" type="application/atom+xml"'
)
HEAD_BLOCK_RE = re.compile(
    rf"\s*{re.escape(HEAD_BLOCK_START)}.*?"
    rf"{re.escape(HEAD_BLOCK_END)}\s*",
    flags=re.DOTALL,
)
CARD_BLOCK_START = gen_smart_app_banners.APP_STORE_QR_BLOCK_START
CARD_BLOCK_END = gen_smart_app_banners.APP_STORE_QR_BLOCK_END
CARD_BLOCK_RE = gen_smart_app_banners.APP_STORE_QR_BLOCK_RE
STYLESHEET_NAME = "app-store-qr-v1.css"
STYLESHEET_RELATIVE = Path("assets") / STYLESHEET_NAME
QR_RELATIVE = Path("assets") / "app-store-qr"
CSS = """\
.app-store-qr-card {
  display: none;
}

@media (min-width: 760px), print {
  .app-store-qr-card {
    display: flex !important;
    box-sizing: border-box;
    inline-size: min(100%, 48rem);
    margin: clamp(2rem, 6vw, 4.5rem) auto;
    padding: clamp(1rem, 2.6vw, 1.4rem);
    color: #101828;
    background:
      radial-gradient(circle at 14% 10%, rgba(99, 102, 241, 0.12), transparent 42%),
      rgba(255, 255, 255, 0.98);
    border: 1px solid rgba(15, 23, 42, 0.12);
    border-radius: 1.5rem;
    box-shadow: 0 18px 56px rgba(15, 23, 42, 0.12);
    break-inside: avoid;
  }

  .app-store-qr-card__link {
    display: flex;
    align-items: center;
    inline-size: 100%;
    min-inline-size: 0;
    gap: clamp(1rem, 3vw, 1.5rem);
    color: inherit !important;
    text-align: start;
    text-decoration: none;
  }

  .app-store-qr-card__image {
    flex: 0 0 auto;
    inline-size: clamp(7.5rem, 13vw, 9.5rem);
    block-size: clamp(7.5rem, 13vw, 9.5rem);
    padding: 0.45rem;
    background: #fff;
    border: 1px solid rgba(15, 23, 42, 0.1);
    border-radius: 1rem;
  }

  .app-store-qr-card__copy {
    display: grid;
    min-inline-size: 0;
    gap: 0.55rem;
  }

  .app-store-qr-card__label,
  .app-store-qr-card__url {
    display: block;
    max-inline-size: 100%;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }

  .app-store-qr-card__label {
    color: #172033;
    font-size: clamp(1rem, 1.6vw, 1.28rem);
    font-weight: 850;
    line-height: 1.2;
  }

  .app-store-qr-card__url {
    color: #667085;
    font-family: ui-monospace, "SFMono-Regular", Consolas, monospace;
    font-size: clamp(0.72rem, 1.2vw, 0.88rem);
    line-height: 1;
  }

  .app-store-qr-card__url::before {
    content: attr(data-store-url);
  }

  .app-store-qr-card__link:focus-visible {
    outline: 3px solid #4f55e8;
    outline-offset: 0.45rem;
    border-radius: 0.8rem;
  }
}

@media print {
  .app-store-qr-card {
    margin: 8mm auto;
    padding: 5mm;
    color: #000;
    background: #fff;
    border: 0.5pt solid #222;
    border-radius: 4mm;
    box-shadow: none;
  }

  .app-store-qr-card__link {
    color: #000 !important;
  }

  .app-store-qr-card__link::after {
    content: none !important;
  }

  .app-store-qr-card__image {
    inline-size: 32mm;
    block-size: 32mm;
    padding: 2mm;
    border-radius: 2mm;
  }

  .app-store-qr-card__label {
    color: #000;
    font-size: 12pt;
  }

  .app-store-qr-card__url {
    color: #333;
    font-size: 8pt;
  }
}
"""


def _site_asset_href(site: str, relative: Path) -> str:
    parsed = urllib.parse.urlsplit(site)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"Invalid App Store QR site URL: {site}")
    base_path = parsed.path.rstrip("/")
    return f"{base_path}/{relative.as_posix()}"


def store_url(app_id: str) -> str:
    if not re.fullmatch(r"\d+", app_id):
        raise ValueError(f"Invalid App Store QR app ID: {app_id}")
    return f"https://apps.apple.com/app/id{app_id}"


def qr_asset_relative(app_id: str, href: str) -> Path:
    store_url(app_id)
    url = normalize_app_store_campaign_url(href)
    validated_app_store_url(url, app_id)
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    return QR_RELATIVE / f"id{app_id}-{digest}.svg"


def qr_svg(app_id: str, href: str) -> str:
    store_url(app_id)
    url = normalize_app_store_campaign_url(href)
    validated_app_store_url(url, app_id)
    code = segno.make(url, error="m", micro=False)
    output = io.BytesIO()
    code.save(
        output,
        kind="svg",
        border=4,
        scale=1,
        xmldecl=False,
        svgns=True,
        omitsize=True,
        nl=True,
        svgid=f"app-store-qr-{app_id}",
        title="Direct App Store download",
        desc=url,
    )
    return output.getvalue().decode("utf-8")


def style_block(stylesheet_href: str) -> str:
    if not stylesheet_href.startswith("/") or any(
        char in stylesheet_href for char in "\"'<>"
    ):
        raise ValueError(
            f"Invalid App Store QR stylesheet URL: {stylesheet_href}"
        )
    return "\n".join(
        (
            HEAD_BLOCK_START,
            f'<link rel="stylesheet" href="{stylesheet_href}">',
            HEAD_BLOCK_END,
        )
    )


def card_block(
    app_id: str,
    href: str,
    label: str,
    image_href: str,
) -> str:
    store_url(app_id)
    direct_url = normalize_app_store_campaign_url(href)
    validated_app_store_url(direct_url, app_id)
    display_url = urllib.parse.urlunsplit(
        urllib.parse.urlsplit(direct_url)._replace(query="")
    )
    if not image_href.startswith("/") or any(
        char in image_href for char in "\"'<>"
    ):
        raise ValueError(f"Invalid App Store QR image URL: {image_href}")
    escaped_href = html.escape(direct_url, quote=True)
    escaped_label = html.escape(label)
    escaped_display_url = html.escape(display_url)
    return f"""{CARD_BLOCK_START}
<section class="app-store-qr-card" style="display:none" aria-label="{escaped_label}">
<a class="app-store-qr-card__link" href="{escaped_href}" rel="nofollow noopener">
<img class="app-store-qr-card__image" src="{image_href}" width="164" height="164" alt="" decoding="async">
<span class="app-store-qr-card__copy"><strong class="app-store-qr-card__label">{escaped_label}</strong><span class="app-store-qr-card__url" data-store-url="{escaped_display_url}" aria-hidden="true"></span></span>
</a>
</section>
{CARD_BLOCK_END}"""


def ensure_qr_card(
    path: Path,
    app_id: str,
    href: str,
    label: str,
    stylesheet_href: str,
    image_href: str,
) -> bool:
    source = path.read_text(encoding="utf-8")
    if "</head>" not in source or "</body>" not in source:
        raise ValueError(f"App Store QR page is missing head or body: {path}")
    cleaned = HEAD_BLOCK_RE.sub("\n", CARD_BLOCK_RE.sub("\n", source))
    head_index = cleaned.index("</head>")
    for anchor in (DECISION_STYLE_ANCHOR, FEED_DISCOVERY_ANCHOR):
        anchor_index = cleaned.find(anchor)
        if 0 <= anchor_index < head_index:
            head_index = anchor_index
    with_style = (
        cleaned[:head_index].rstrip()
        + "\n"
        + style_block(stylesheet_href)
        + "\n"
        + cleaned[head_index:].lstrip()
    )
    main_index = with_style.rfind("</main>")
    if main_index < 0:
        main_index = with_style.rfind('<div class="footer">')
    if main_index < 0:
        main_index = with_style.find(
            gen_mobile_store_ctas.BLOCK_START
        )
    if main_index < 0:
        main_index = with_style.index("</body>")
    updated = (
        with_style[:main_index].rstrip()
        + "\n"
        + card_block(app_id, href, label, image_href)
        + "\n"
        + with_style[main_index:].lstrip()
    )
    return _write_if_changed(path, updated)


def remove_qr_card(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    updated = HEAD_BLOCK_RE.sub("\n", CARD_BLOCK_RE.sub("\n", source))
    return _write_if_changed(path, updated)


def _write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def sync_assets(
    pages: Path,
    qr_targets: set[tuple[str, str]],
) -> int:
    changed = int(
        _write_if_changed(pages / STYLESHEET_RELATIVE, CSS)
    )
    qr_directory = pages / QR_RELATIVE
    qr_directory.mkdir(parents=True, exist_ok=True)
    assets: dict[Path, tuple[str, str]] = {}
    for app_id, href in sorted(qr_targets):
        relative = qr_asset_relative(app_id, href)
        previous = assets.get(relative)
        if previous is not None and previous != (app_id, href):
            raise ValueError(f"App Store QR asset collision: {relative}")
        assets[relative] = (app_id, href)
    expected = {pages / relative for relative in assets}
    for relative, (app_id, href) in sorted(
        assets.items(), key=lambda item: str(item[0])
    ):
        changed += int(
            _write_if_changed(
                pages / relative, qr_svg(app_id, href)
            )
        )
    for path in sorted(qr_directory.glob("id*.svg")):
        if path not in expected:
            path.unlink()
            changed += 1
    return changed


def generate(
    pages: Path = PAGES,
    live_keys: set[str] | None = None,
    site: str = SITE,
) -> dict[str, int]:
    if live_keys is None:
        live_keys = set(live_app_keys(APPSTORE, str(pages), refresh=False))
    targets, app_count = gen_smart_app_banners.build_install_targets(
        pages, set(live_keys), site
    )
    guide_pages = gen_smart_app_banners._guide_pages(pages)
    answer_pages = gen_smart_app_banners._answer_pages(pages)
    buyer_intent_pages = gen_smart_app_banners._buyer_intent_pages(pages)
    eligible_pages = guide_pages | buyer_intent_pages
    qr_targets = {
        path: app_id for path, app_id in targets.items() if path in eligible_pages
    }
    prepared: dict[Path, tuple[str, str, str]] = {}
    for path, app_id in sorted(qr_targets.items()):
        cta = gen_mobile_store_ctas.app_store_cta(
            path.read_text(encoding="utf-8"), app_id
        )
        if cta is None:
            raise ValueError(f"App Store QR page has no direct app link: {path}")
        prepared[path] = (app_id, *cta)

    app_ids = {app_id for app_id, _, _ in prepared.values()}
    if len(app_ids) != app_count:
        raise ValueError(
            f"App Store QR coverage mismatch: {len(app_ids)}/{app_count} apps"
        )
    stylesheet_href = _site_asset_href(site, STYLESHEET_RELATIVE)
    qr_assets = {
        (app_id, href) for app_id, href, _ in prepared.values()
    }
    changed = sync_assets(pages, qr_assets)
    installed: set[Path] = set()
    for path, (app_id, href, label) in sorted(prepared.items()):
        image_href = _site_asset_href(
            site, qr_asset_relative(app_id, href)
        )
        changed += int(
            ensure_qr_card(
                path,
                app_id,
                href,
                label,
                stylesheet_href,
                image_href,
            )
        )
        installed.add(path)

    for path in sorted(eligible_pages - set(qr_targets)):
        source = path.read_text(encoding="utf-8")
        if HEAD_BLOCK_RE.search(source) or CARD_BLOCK_RE.search(source):
            changed += int(remove_qr_card(path))

    return {
        "apps": len(app_ids),
        "qr_assets": len(qr_assets),
        "guide_pages": len(installed & guide_pages),
        "answer_pages": len(installed & answer_pages),
        "buyer_intent_pages": len(installed & buyer_intent_pages),
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
        "Direct App Store QR cards: "
        f"{result['apps']} apps, {result['qr_assets']} QR assets, "
        f"{result['guide_pages']} guide pages, "
        f"{result['buyer_intent_pages']} single-app buyer-intent pages, "
        f"{result['changed_files']} files updated"
    )


if __name__ == "__main__":
    main()
