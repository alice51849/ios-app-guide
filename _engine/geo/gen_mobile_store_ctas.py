#!/usr/bin/env python3
"""Add mobile App Store CTAs to app guides and single-app buyer pages."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
import urllib.parse

from app_store_storefronts import (
    normalize_app_store_campaign_url,
    validated_app_store_url,
)
from answer_app_store_links import canonical_app_store_url
import gen_smart_app_banners
from appstore_live import live_app_keys
from videogen.registry import APPSTORE


PAGES = gen_smart_app_banners.PAGES
SITE = gen_smart_app_banners.SITE
BLOCK_START = gen_smart_app_banners.MOBILE_CTA_BLOCK_START
BLOCK_END = gen_smart_app_banners.MOBILE_CTA_BLOCK_END
BLOCK_RE = gen_smart_app_banners.MOBILE_CTA_BLOCK_RE
ANCHOR_RE = re.compile(
    r"<a\b(?P<attrs>[^>]*)>(?P<label>.*?)</a>",
    flags=re.IGNORECASE | re.DOTALL,
)
ATTRIBUTE_RE = re.compile(
    r"""(?P<name>[\w:-]+)\s*=\s*(?P<quote>["'])(?P<value>.*?)(?P=quote)""",
    flags=re.DOTALL,
)
ASSET_NAME = "mobile-store-cta-v1.js"
ASSET_RELATIVE = Path("assets") / ASSET_NAME
SCRIPT = """\
(() => {
  "use strict";

  const bar = document.querySelector("[data-mobile-store-cta]");
  if (!bar || !("IntersectionObserver" in window)) return;
  const link = bar.querySelector("a");
  const source =
    document.querySelector(
    '.hero a[href^="https://apps.apple.com/"][href*="/app/"][href*="/id"]'
    ) ||
    document.querySelector(
    'main a[href^="https://apps.apple.com/"][href*="/app/"][href*="/id"]'
    );
  if (!link || !source) return;

  if (!document.getElementById("mobile-store-cta-style")) {
    const style = document.createElement("style");
    style.id = "mobile-store-cta-style";
    style.textContent = `
.mobile-store-cta{position:fixed;z-index:2147483000;left:12px;left:max(12px,env(safe-area-inset-left));right:12px;right:max(12px,env(safe-area-inset-right));bottom:10px;bottom:max(10px,env(safe-area-inset-bottom));display:flex;box-sizing:border-box;padding:6px;border:1px solid rgba(255,255,255,.72);border-radius:20px;background:rgba(255,255,255,.9);box-shadow:0 14px 44px rgba(20,22,45,.2);-webkit-backdrop-filter:blur(18px) saturate(1.35);backdrop-filter:blur(18px) saturate(1.35);opacity:0;transform:translateY(calc(100% + 28px));pointer-events:none;transition:opacity .22s ease,transform .28s cubic-bezier(.22,1,.36,1)}
.mobile-store-cta.is-visible{opacity:1;transform:translateY(0);pointer-events:auto}
.mobile-store-cta__link{display:flex;align-items:center;justify-content:flex-start;width:100%;min-height:48px;padding:0 18px;border-radius:14px;background:linear-gradient(135deg,#4f55e8,#8057d9);box-shadow:0 7px 18px rgba(79,85,232,.28);color:#fff!important;text-decoration:none;font-size:clamp(.72rem,3.2vw,1rem);font-weight:850;letter-spacing:-.01em;line-height:1;white-space:nowrap;overflow-x:auto;scrollbar-width:none;-webkit-tap-highlight-color:transparent}
.mobile-store-cta__label{margin-inline:auto}
.mobile-store-cta__link::-webkit-scrollbar{display:none}
.mobile-store-cta__link:focus-visible{outline:3px solid #fff;outline-offset:-5px}
@media(min-width:760px),print{.mobile-store-cta{display:none!important}}
@media(max-width:759px){body.mobile-store-cta-active{padding-bottom:calc(82px + env(safe-area-inset-bottom))}}
@media(prefers-reduced-motion:reduce){.mobile-store-cta{transition:none}}
`;
    document.head.appendChild(style);
  }

  let sourceVisible = true;
  let ticking = false;
  const update = () => {
    ticking = false;
    const threshold = Math.min(320, window.innerHeight * 0.4);
    const visible = window.scrollY >= threshold && !sourceVisible;
    bar.classList.toggle("is-visible", visible);
    bar.setAttribute("aria-hidden", String(!visible));
    link.tabIndex = visible ? 0 : -1;
    document.body.classList.toggle("mobile-store-cta-active", visible);
  };
  const requestUpdate = () => {
    if (!ticking) {
      ticking = true;
      requestAnimationFrame(update);
    }
  };

  bar.hidden = false;
  new IntersectionObserver(
    (entries) => {
      sourceVisible = entries[0].isIntersecting;
      requestUpdate();
    },
    { threshold: 0.01 }
  ).observe(source);
  window.addEventListener("scroll", requestUpdate, { passive: true });
  window.addEventListener("resize", requestUpdate, { passive: true });
  update();
})();
"""


def _attributes(source: str) -> dict[str, str]:
    return {
        match.group("name").lower(): html.unescape(match.group("value"))
        for match in ATTRIBUTE_RE.finditer(source)
    }


def _plain_label(source: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", source)
    return " ".join(html.unescape(without_tags).split())


def app_store_cta(source: str, app_id: str) -> tuple[str, str] | None:
    cleaned = gen_smart_app_banners.APP_STORE_SHARE_BLOCK_RE.sub(
        "\n",
        gen_smart_app_banners.APP_STORE_QR_BLOCK_RE.sub(
            "\n", BLOCK_RE.sub("\n", source)
        ),
    )
    candidates: list[tuple[int, str, str]] = []
    for match in ANCHOR_RE.finditer(cleaned):
        attributes = _attributes(match.group("attrs"))
        href = attributes.get("href", "")
        try:
            href = canonical_app_store_url(href)
        except ValueError:
            continue
        linked_id = gen_smart_app_banners.APP_STORE_LINK_RE.match(href)
        if not linked_id or linked_id.group(1) != app_id:
            continue
        href = normalize_app_store_campaign_url(href)
        validated_app_store_url(href, app_id)
        label = _plain_label(match.group("label"))
        if not label:
            continue
        classes = set(attributes.get("class", "").split())
        if "iag-decision-card__cta" in classes:
            priority = -1
        elif "cta" in classes and "ghost" not in classes:
            priority = 0
        elif "cta" in classes:
            priority = 1
        else:
            priority = 2
        candidates.append((priority, href, label))
    if not candidates:
        return None
    _, href, label = min(candidates, key=lambda item: item[0])
    return href, label


def asset_href(site: str = SITE) -> str:
    parsed = urllib.parse.urlsplit(site)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"Invalid mobile CTA site URL: {site}")
    base_path = parsed.path.rstrip("/")
    return f"{base_path}/assets/{ASSET_NAME}"


def mobile_cta_block(
    href: str, label: str, script_href: str | None = None
) -> str:
    href = normalize_app_store_campaign_url(html.unescape(href))
    validated_app_store_url(href)
    if script_href is None:
        script_href = asset_href()
    if not script_href.startswith("/") or any(
        char in script_href for char in "\"'<>"
    ):
        raise ValueError(f"Invalid mobile CTA asset URL: {script_href}")
    escaped_href = html.escape(href, quote=True)
    escaped_label = html.escape(label)
    return f"""{BLOCK_START}
<div class="mobile-store-cta" data-mobile-store-cta hidden aria-hidden="true">
<a class="mobile-store-cta__link" href="{escaped_href}" rel="nofollow noopener" tabindex="-1"><span class="mobile-store-cta__label">{escaped_label}</span></a>
</div>
<script src="{script_href}" defer></script>
{BLOCK_END}"""


def ensure_mobile_cta(
    path: Path, app_id: str, script_href: str | None = None
) -> bool:
    source = path.read_text(encoding="utf-8")
    if "</body>" not in source:
        raise ValueError(f"Mobile App Store CTA page has no closing body: {path}")
    cleaned = BLOCK_RE.sub("\n", source)
    if gen_smart_app_banners.FREE_RESOURCE_FIRST_META in cleaned:
        return _write_if_changed(path, cleaned)
    cta = app_store_cta(cleaned, app_id)
    if cta is None:
        return _write_if_changed(path, cleaned)
    href, label = cta
    body_index = cleaned.index("</body>")
    share_index = cleaned.find(
        gen_smart_app_banners.APP_STORE_SHARE_BLOCK_START
    )
    insert_index = (
        share_index if 0 <= share_index < body_index else body_index
    )
    updated = (
        cleaned[:insert_index].rstrip()
        + "\n"
        + mobile_cta_block(href, label, script_href)
        + "\n"
        + cleaned[insert_index:].lstrip()
    )
    return _write_if_changed(path, updated)


def _write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
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
    targets, app_count = gen_smart_app_banners.build_install_targets(
        pages, set(live_keys), site
    )
    guide_pages = gen_smart_app_banners._guide_pages(pages)
    answer_pages = gen_smart_app_banners._answer_pages(pages)
    buyer_intent_pages = gen_smart_app_banners._buyer_intent_pages(pages)
    eligible_pages = guide_pages | buyer_intent_pages
    mobile_targets = {
        path: app_id for path, app_id in targets.items() if path in eligible_pages
    }
    script_href = asset_href(site)
    changed = int(_write_if_changed(pages / ASSET_RELATIVE, SCRIPT))
    installed: set[Path] = set()
    installed_ids: set[str] = set()
    for path, app_id in sorted(mobile_targets.items()):
        changed += int(ensure_mobile_cta(path, app_id, script_href))
        if BLOCK_RE.search(path.read_text(encoding="utf-8")):
            installed.add(path)
            installed_ids.add(app_id)

    for path in sorted(eligible_pages - set(mobile_targets)):
        source = path.read_text(encoding="utf-8")
        if BLOCK_RE.search(source):
            changed += int(_write_if_changed(path, BLOCK_RE.sub("\n", source)))

    expected_ids = {
        app_id for path, app_id in mobile_targets.items() if path in guide_pages
    }
    missing_pages = set(mobile_targets) - installed
    if missing_pages:
        sample = ", ".join(str(path) for path in sorted(missing_pages)[:5])
        raise ValueError(f"Pages have no direct mobile App Store CTA: {sample}")
    if installed_ids != expected_ids or len(installed_ids) != app_count:
        missing = ", ".join(sorted(expected_ids - installed_ids)) or "unknown"
        raise ValueError(f"Live apps have no mobile App Store CTA: {missing}")

    return {
        "apps": len(installed_ids),
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
        "Mobile direct App Store CTAs: "
        f"{result['apps']} apps, {result['guide_pages']} guide pages, "
        f"{result['buyer_intent_pages']} single-app buyer-intent pages, "
        f"{result['changed_files']} files updated"
    )


if __name__ == "__main__":
    main()
