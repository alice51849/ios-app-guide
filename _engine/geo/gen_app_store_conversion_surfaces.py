#!/usr/bin/env python3
"""Generate App Store conversion surfaces from one shared page inventory."""

from __future__ import annotations

import argparse
from functools import partial
import json
import market_availability as market
import market_surface_policy
import os
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

import gen_app_store_qr_ctas  # noqa: E402
from gen_store_attribution import final_store_url, page_token  # noqa: E402
from app_store_storefronts import load_storefront_availability, resolve_provider_token  # noqa: E402
import gen_app_store_share_ctas  # noqa: E402
import gen_mobile_store_ctas  # noqa: E402
import gen_smart_app_banners  # noqa: E402
from appstore_live import live_app_keys  # noqa: E402
from videogen.registry import APPSTORE  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402
import parallel_pages  # noqa: E402


PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = os.environ.get(
    "GEO_SITE", PUBLIC_SITE
).rstrip("/")


def _render_target(
    item: tuple[Path, str],
    *,
    pages: Path,
    conversion_targets: frozenset[Path],
    mobile_script_href: str,
    qr_stylesheet_href: str,
    share_script_href: str,
    site: str,
    provider: str | None,
    availability,
):
    """Render one target page without writing it.

    Returns ``(kind, updated, smart, mobile, qr, share, qr_asset)`` where
    ``updated`` is ``None`` when the page is unchanged and the counters are the
    per-page increments of the serial loop.
    """
    path, app_id = item
    source = path.read_text(encoding="utf-8")
    locale = gen_app_store_qr_ctas.page_locale(path, pages)
    if market.is_unavailable(locale, app_id):
        cleaned = market_surface_policy.enforce_html(source, locale, app_id=app_id)
        changed = cleaned != source
        return "blocked", cleaned if changed else None, int(changed), 0, 0, 0, None
    current = gen_smart_app_banners.render_banner(
        path,
        source,
        app_id,
    )
    smart_changed = int(current != source)

    if path not in conversion_targets:
        return (
            "banner", current if current != source else None,
            smart_changed, 0, 0, 0, None,
        )

    rendered = gen_mobile_store_ctas.render_mobile_cta(
        path,
        current,
        app_id,
        mobile_script_href,
    )
    mobile_changed = int(rendered != current)
    current = rendered
    if not gen_mobile_store_ctas.BLOCK_RE.search(current):
        raise ValueError(f"Pages have no direct mobile App Store CTA: {path}")

    cta = gen_mobile_store_ctas.app_store_cta(current, app_id)
    if cta is None:
        raise ValueError(f"App Store QR page has no direct app link: {path}")
    href, label = cta
    # Hash the exact link the attribution stamper will leave on the page
    # (storefront aligned to the page locale, page campaign applied) so the
    # combined pass stays byte-equivalent with gen_app_store_qr_ctas.
    relative = path.resolve().relative_to(pages.resolve()).as_posix()
    qr_href = final_store_url(
        href, page_token(relative, current), provider,
        locale=gen_app_store_qr_ctas.page_locale(path, pages),
        availability=availability, app_id=app_id,
    )
    image_href = gen_app_store_qr_ctas._site_asset_href(
        site,
        gen_app_store_qr_ctas.qr_asset_relative(app_id, qr_href),
    )
    rendered = gen_app_store_qr_ctas.render_qr_card(
        path,
        current,
        app_id,
        qr_href,
        label,
        qr_stylesheet_href,
        image_href,
        gen_app_store_qr_ctas.page_locale(path, pages),
    )
    qr_changed = int(rendered != current)
    current = rendered

    rendered = gen_app_store_share_ctas.render_share(
        path,
        current,
        app_id,
        share_script_href,
        store_url=href,
    )
    share_changed = int(rendered != current)
    current = rendered
    expected_share = gen_app_store_share_ctas.share_block(
        app_id,
        share_script_href,
        store_url=href,
    )
    block = gen_app_store_share_ctas.BLOCK_RE.search(current)
    if not block or block.group(0).strip() != expected_share:
        raise ValueError(f"Pages have no native App Store share action: {path}")

    return (
        "conversion", current if current != source else None,
        smart_changed, mobile_changed, qr_changed, share_changed,
        (app_id, qr_href),
    )


def _strip_surfaces(path: Path):
    """Remove every managed conversion block from a non-target page."""
    source = path.read_text(encoding="utf-8")
    current = gen_smart_app_banners.BLOCK_RE.sub("\n", source)
    smart_changed = int(current != source)
    rendered = gen_mobile_store_ctas.BLOCK_RE.sub("\n", current)
    mobile_changed = int(rendered != current)
    current = rendered
    rendered = gen_app_store_qr_ctas.HEAD_BLOCK_RE.sub(
        "\n",
        gen_app_store_qr_ctas.CARD_BLOCK_RE.sub("\n", current),
    )
    qr_changed = int(rendered != current)
    current = rendered
    rendered = gen_app_store_share_ctas.BLOCK_RE.sub("\n", current)
    share_changed = int(rendered != current)
    current = rendered
    return (
        current if current != source else None,
        smart_changed, mobile_changed, qr_changed, share_changed,
    )


def generate(
    pages: Path = PAGES,
    live_keys: set[str] | None = None,
    site: str = SITE,
) -> dict[str, dict[str, int]]:
    if live_keys is None:
        live_keys = set(live_app_keys(APPSTORE, str(pages), refresh=False))
    inventory = gen_smart_app_banners.build_surface_inventory(
        pages,
        set(live_keys),
        site,
    )
    targets = inventory.targets
    guide_pages = set(inventory.guide_pages)
    answer_pages = set(inventory.answer_pages)
    buyer_intent_pages = set(inventory.buyer_intent_pages)
    eligible_pages = guide_pages | buyer_intent_pages
    conversion_targets = {
        path: app_id
        for path, app_id in targets.items()
        if path in eligible_pages
    }

    mobile_script_href = gen_mobile_store_ctas.asset_href(site)
    qr_stylesheet_href = gen_app_store_qr_ctas._site_asset_href(
        site,
        gen_app_store_qr_ctas.STYLESHEET_RELATIVE,
    )
    share_script_href = gen_app_store_share_ctas.asset_href(site)
    smart_changed = 0
    mobile_changed = int(
        gen_mobile_store_ctas._write_if_changed(
            pages / gen_mobile_store_ctas.ASSET_RELATIVE,
            gen_mobile_store_ctas.SCRIPT,
        )
    )
    qr_changed = 0
    provider = resolve_provider_token() or None
    availability = load_storefront_availability(pages) or None
    share_changed = int(
        gen_app_store_share_ctas._write_if_changed(
            pages / gen_app_store_share_ctas.ASSET_RELATIVE,
            gen_app_store_share_ctas.SCRIPT,
        )
    )
    smart_installed: set[Path] = set()
    conversion_installed: set[Path] = set()
    installed_ids: set[str] = set()
    qr_assets: set[tuple[str, str]] = set()

    # Rendering is per page and side-effect free; pages are written here, in
    # the original order, so a failure leaves exactly the serial state behind.
    target_items = sorted(targets.items())
    rendered_targets = parallel_pages.ordered_map(
        partial(
            _render_target,
            pages=pages,
            conversion_targets=frozenset(conversion_targets),
            mobile_script_href=mobile_script_href,
            qr_stylesheet_href=qr_stylesheet_href,
            share_script_href=share_script_href,
            site=site,
            provider=provider,
            availability=availability,
        ),
        target_items,
    )
    for (path, app_id), result in zip(target_items, rendered_targets, strict=True):
        kind, updated, smart, mobile, qr, share, qr_asset = result
        smart_changed += smart
        mobile_changed += mobile
        qr_changed += qr
        share_changed += share
        if updated is not None:
            path.write_text(updated, encoding="utf-8")
        if kind == "blocked":
            continue
        smart_installed.add(path)
        if kind == "banner":
            continue
        qr_assets.add(qr_asset)
        conversion_installed.add(path)
        installed_ids.add(app_id)

    stripped_items = sorted(eligible_pages - set(targets))
    for path, result in zip(
        stripped_items,
        parallel_pages.ordered_map(_strip_surfaces, stripped_items),
        strict=True,
    ):
        updated, smart, mobile, qr, share = result
        smart_changed += smart
        mobile_changed += mobile
        qr_changed += qr
        share_changed += share
        if updated is not None:
            path.write_text(updated, encoding="utf-8")

    expected_ids = {
        app_id
        for path, app_id in conversion_targets.items()
        if path in guide_pages and not market.is_unavailable(gen_app_store_qr_ctas.page_locale(path, pages))
    }
    if installed_ids != expected_ids:
        missing = ", ".join(sorted(expected_ids - installed_ids)) or "unknown"
        raise ValueError(f"Live apps have no conversion surface: {missing}")
    qr_changed += gen_app_store_qr_ctas.sync_assets(pages, qr_assets)

    languages = {
        gen_smart_app_banners._page_language(path, pages)
        for path in smart_installed
    }
    share_languages = {
        gen_smart_app_banners._page_language(path, pages)
        for path in conversion_installed
    }
    return {
        "smart_app_banners": {
            "apps": inventory.app_count,
            "guide_pages": len(smart_installed & guide_pages),
            "answer_pages": len(smart_installed & answer_pages),
            "buyer_intent_pages": len(
                smart_installed & buyer_intent_pages
            ),
            "languages": len(languages),
            "changed_files": smart_changed,
        },
        "mobile_store_ctas": {
            "apps": len(installed_ids),
            "guide_pages": len(conversion_installed & guide_pages),
            "answer_pages": len(conversion_installed & answer_pages),
            "buyer_intent_pages": len(
                conversion_installed & buyer_intent_pages
            ),
            "changed_files": mobile_changed,
        },
        "app_store_qr_ctas": {
            "apps": len(installed_ids),
            "qr_assets": len(qr_assets),
            "guide_pages": len(conversion_installed & guide_pages),
            "answer_pages": len(conversion_installed & answer_pages),
            "buyer_intent_pages": len(
                conversion_installed & buyer_intent_pages
            ),
            "changed_files": qr_changed,
        },
        "app_store_share_ctas": {
            "apps": len(installed_ids),
            "guide_pages": len(conversion_installed & guide_pages),
            "answer_pages": len(conversion_installed & answer_pages),
            "buyer_intent_pages": len(
                conversion_installed & buyer_intent_pages
            ),
            "languages": len(share_languages),
            "changed_files": share_changed,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pages",
        type=Path,
        default=PAGES,
        help="Alternate Pages checkout.",
    )
    args = parser.parse_args()
    print(json.dumps(generate(args.pages), sort_keys=True))


if __name__ == "__main__":
    main()
