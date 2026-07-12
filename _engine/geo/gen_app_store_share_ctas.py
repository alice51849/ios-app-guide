#!/usr/bin/env python3
"""Add native sharing of direct App Store links to high-intent app pages."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import re
import urllib.parse

import gen_smart_app_banners
from appstore_live import live_app_keys
from videogen.registry import APPSTORE


PAGES = gen_smart_app_banners.PAGES
SITE = gen_smart_app_banners.SITE
BLOCK_START = gen_smart_app_banners.APP_STORE_SHARE_BLOCK_START
BLOCK_END = gen_smart_app_banners.APP_STORE_SHARE_BLOCK_END
BLOCK_RE = gen_smart_app_banners.APP_STORE_SHARE_BLOCK_RE
ASSET_NAME = "app-store-share-v1.js"
ASSET_RELATIVE = Path("assets") / ASSET_NAME
SHARE_LABELS = {
    "ar-sa": "مشاركة",
    "bn-bd": "শেয়ার করুন",
    "ca": "Comparteix",
    "cs": "Sdílet",
    "da": "Del",
    "de-de": "Teilen",
    "el": "Κοινοποίηση",
    "en": "Share",
    "es-es": "Compartir",
    "es-mx": "Compartir",
    "fi": "Jaa",
    "fr-fr": "Partager",
    "gu-in": "શેર કરો",
    "he": "שיתוף",
    "hi": "साझा करें",
    "hr": "Podijeli",
    "hu": "Megosztás",
    "id": "Bagikan",
    "it": "Condividi",
    "ja": "共有",
    "kn-in": "ಹಂಚಿಕೊಳ್ಳಿ",
    "ko": "공유",
    "ml-in": "പങ്കിടുക",
    "mr-in": "शेअर करा",
    "ms": "Kongsi",
    "nl-nl": "Delen",
    "no": "Del",
    "or-in": "ସେୟାର କରନ୍ତୁ",
    "pa-in": "ਸਾਂਝਾ ਕਰੋ",
    "pl": "Udostępnij",
    "pt-br": "Compartilhar",
    "pt-pt": "Partilhar",
    "ro": "Distribuie",
    "ru": "Поделиться",
    "sk": "Zdieľať",
    "sl-si": "Deli",
    "sv": "Dela",
    "ta-in": "பகிர்",
    "te-in": "షేర్ చేయండి",
    "th": "แชร์",
    "tr": "Paylaş",
    "uk": "Поділитися",
    "ur-pk": "شیئر کریں",
    "vi": "Chia sẻ",
    "zh-hans": "分享",
    "zh-hant": "分享",
}
SCRIPT_TEMPLATE = """\
(() => {
  "use strict";

  const script = document.querySelector("script[data-app-store-share]");
  const appId = script && script.dataset.appStoreShare;
  if (!appId || !/^\\d+$/.test(appId)) return;
  if (typeof navigator.share !== "function") return;

  const url = `https://apps.apple.com/app/id${appId}`;
  const payload = { url };
  if (
    typeof navigator.canShare === "function" &&
    !navigator.canShare(payload)
  ) return;

  const shareLabels = Object.freeze(__SHARE_LABELS__);
  const language = (document.documentElement.lang || "en").toLowerCase();
  const label = shareLabels[language] || shareLabels.en;

  if (!document.getElementById("app-store-share-style")) {
    const style = document.createElement("style");
    style.id = "app-store-share-style";
    style.textContent = `
.app-store-share-button{appearance:none;-webkit-appearance:none;display:inline-grid;place-items:center;flex:0 0 48px;inline-size:48px;block-size:48px;min-inline-size:48px;margin:0;padding:0;border:1px solid rgba(79,85,232,.2);border-radius:14px;color:#4f55e8;background:rgba(79,85,232,.08);font:inherit;line-height:1;white-space:nowrap;cursor:pointer;touch-action:manipulation;-webkit-tap-highlight-color:transparent;transition:background-color .18s ease,transform .18s ease}
.app-store-share-button svg{inline-size:23px;block-size:23px;fill:none;stroke:currentColor;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round;pointer-events:none}
.app-store-share-button:focus-visible{outline:3px solid #4f55e8;outline-offset:3px}
.mobile-store-cta .mobile-store-cta__link{flex:1 1 auto;width:auto;min-width:0}
.mobile-store-cta>.app-store-share-button{margin-inline-start:6px;color:#fff;background:linear-gradient(135deg,#7378ee,#946ee1);border-color:rgba(255,255,255,.55);box-shadow:0 7px 18px rgba(79,85,232,.2)}
.app-store-qr-card>.app-store-share-button{align-self:center;margin-inline-start:.75rem}
@media(hover:hover){.app-store-share-button:hover{background:rgba(79,85,232,.15);transform:translateY(-1px)}.mobile-store-cta>.app-store-share-button:hover{background:linear-gradient(135deg,#686ee9,#895fdc)}}
@media print{.app-store-share-button{display:none!important}}
@media(prefers-reduced-motion:reduce){.app-store-share-button{transition:none}}
`;
    document.head.appendChild(style);
  }

  const icon = `
<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
  <path d="M12 15V3m0 0L7.5 7.5M12 3l4.5 4.5"></path>
  <path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7"></path>
</svg>`;

  const addButton = (container, modifier) => {
    if (!container || container.querySelector(".app-store-share-button")) {
      return null;
    }
    const button = document.createElement("button");
    button.type = "button";
    button.className = `app-store-share-button ${modifier}`;
    button.setAttribute("aria-label", label);
    button.title = label;
    button.dataset.appStoreUrl = url;
    button.innerHTML = icon;
    button.addEventListener("click", async () => {
      try {
        await navigator.share(payload);
      } catch (error) {
        if (!error || error.name !== "AbortError") {
          console.error("App Store share failed", error);
        }
      }
    });
    container.appendChild(button);
    return button;
  };

  const mobileBar = document.querySelector("[data-mobile-store-cta]");
  const mobileButton = addButton(mobileBar, "app-store-share-button--mobile");
  if (mobileButton) {
    const syncTabOrder = () => {
      mobileButton.tabIndex = mobileBar.classList.contains("is-visible") ? 0 : -1;
    };
    new MutationObserver(syncTabOrder).observe(mobileBar, {
      attributes: true,
      attributeFilter: ["class"],
    });
    syncTabOrder();
  }

  addButton(
    document.querySelector(".app-store-qr-card"),
    "app-store-share-button--desktop"
  );
})();
"""
SCRIPT = SCRIPT_TEMPLATE.replace(
    "__SHARE_LABELS__",
    json.dumps(
        SHARE_LABELS,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ),
)


def asset_href(site: str = SITE) -> str:
    parsed = urllib.parse.urlsplit(site)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"Invalid App Store share site URL: {site}")
    return f"{parsed.path.rstrip('/')}/assets/{ASSET_NAME}"


def share_block(app_id: str, script_href: str | None = None) -> str:
    if not re.fullmatch(r"\d+", app_id):
        raise ValueError(f"Invalid App Store share app ID: {app_id}")
    if script_href is None:
        script_href = asset_href()
    if not script_href.startswith("/") or any(
        char in script_href for char in "\"'<>"
    ):
        raise ValueError(f"Invalid App Store share asset URL: {script_href}")
    return "\n".join(
        (
            BLOCK_START,
            (
                f'<script src="{html.escape(script_href, quote=True)}" '
                f'data-app-store-share="{app_id}" defer></script>'
            ),
            BLOCK_END,
        )
    )


def ensure_share(path: Path, app_id: str, script_href: str | None = None) -> bool:
    source = path.read_text(encoding="utf-8")
    if "</body>" not in source:
        raise ValueError(f"App Store share page has no closing body: {path}")
    cleaned = BLOCK_RE.sub("\n", source)
    body_index = cleaned.index("</body>")
    updated = (
        cleaned[:body_index].rstrip()
        + "\n"
        + share_block(app_id, script_href)
        + "\n"
        + cleaned[body_index:].lstrip()
    )
    return _write_if_changed(path, updated)


def remove_share(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    return _write_if_changed(path, BLOCK_RE.sub("\n", source))


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
    targets, app_count = gen_smart_app_banners.build_targets(
        pages, set(live_keys), site
    )
    guide_pages = gen_smart_app_banners._guide_pages(pages)
    answer_pages = gen_smart_app_banners._answer_pages(pages)
    eligible_pages = guide_pages | answer_pages
    share_targets = {
        path: app_id for path, app_id in targets.items() if path in eligible_pages
    }
    script_href = asset_href(site)
    changed = int(_write_if_changed(pages / ASSET_RELATIVE, SCRIPT))
    installed: set[Path] = set()
    installed_ids: set[str] = set()
    for path, app_id in sorted(share_targets.items()):
        changed += int(ensure_share(path, app_id, script_href))
        block = BLOCK_RE.search(path.read_text(encoding="utf-8"))
        if block and f'data-app-store-share="{app_id}"' in block.group(0):
            installed.add(path)
            installed_ids.add(app_id)

    for path in sorted(eligible_pages - set(share_targets)):
        source = path.read_text(encoding="utf-8")
        if BLOCK_RE.search(source):
            changed += int(remove_share(path))

    expected_ids = {
        app_id for path, app_id in share_targets.items() if path in guide_pages
    }
    missing_pages = set(share_targets) - installed
    if missing_pages:
        sample = ", ".join(str(path) for path in sorted(missing_pages)[:5])
        raise ValueError(f"Pages have no native App Store share action: {sample}")
    if installed_ids != expected_ids or len(installed_ids) != app_count:
        missing = ", ".join(sorted(expected_ids - installed_ids)) or "unknown"
        raise ValueError(f"Live apps have no native App Store share action: {missing}")

    languages = {
        "en" if path.parent.parent == pages.resolve() else path.parent.parent.name
        for path in installed
    }
    return {
        "apps": len(installed_ids),
        "guide_pages": len(installed & guide_pages),
        "answer_pages": len(installed & answer_pages),
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
        "Native direct App Store sharing: "
        f"{result['apps']} apps, {result['guide_pages']} guide pages, "
        f"{result['answer_pages']} buyer-intent answer pages, "
        f"{result['languages']} languages, "
        f"{result['changed_files']} files updated"
    )


if __name__ == "__main__":
    main()
