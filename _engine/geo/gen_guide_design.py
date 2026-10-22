#!/usr/bin/env python3
"""Apply the shared premium design system to every public-app guide."""

from __future__ import annotations

import argparse
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
import gen_smart_app_banners  # noqa: E402
from videogen.registry import APPSTORE  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402


PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", PUBLIC_SITE
).rstrip("/")
ASSET_NAME = "guide-premium-v1.css"
ASSET_RELATIVE = Path("assets") / ASSET_NAME
BLOCK_START = "<!-- guide-design:start -->"
BLOCK_END = "<!-- guide-design:end -->"
BLOCK_RE = re.compile(
    rf"\s*{re.escape(BLOCK_START)}.*?{re.escape(BLOCK_END)}\s*",
    flags=re.DOTALL,
)
VIEWPORT_RE = re.compile(
    r'<meta\b(?=[^>]*\bname\s*=\s*["\']viewport["\'])[^>]*>',
    flags=re.IGNORECASE,
)
HEAD_END_RE = re.compile(r"</head\s*>", flags=re.IGNORECASE)

STYLESHEET = """\
:root {
  color-scheme: light dark;
  --guide-canvas: #f3f6fb;
  --guide-glow: rgba(37, 99, 235, 0.16);
  --guide-surface: rgba(255, 255, 255, 0.96);
  --guide-surface-muted: #f7f9fc;
  --guide-text: #172033;
  --guide-text-soft: #475467;
  --guide-heading: #0b1220;
  --guide-accent: #175cd3;
  --guide-accent-strong: #1849a9;
  --guide-border: rgba(15, 23, 42, 0.13);
  --guide-focus: #155eef;
  --guide-shadow: 0 28px 80px rgba(15, 23, 42, 0.12);
}

*,
*::before,
*::after {
  box-sizing: border-box;
}

html {
  min-inline-size: 0;
  background: var(--guide-canvas);
  -webkit-text-size-adjust: 100%;
  text-size-adjust: 100%;
}

body {
  min-block-size: 100vh;
  margin: 0;
  color: var(--guide-text);
  background:
    radial-gradient(circle at 50% -12rem, var(--guide-glow), transparent 36rem),
    var(--guide-canvas);
  font-family:
    Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "SF Pro Text",
    "Segoe UI", sans-serif;
  font-size: clamp(1rem, 0.96rem + 0.2vw, 1.08rem);
  font-synthesis: none;
  line-height: 1.72;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
}

main {
  inline-size: min(calc(100% - clamp(1rem, 5vw, 4rem)), 64rem);
  margin-block: clamp(0.75rem, 4vw, 3.5rem);
  margin-inline: auto;
  padding-block: clamp(1.5rem, 5vw, 4.5rem);
  padding-inline: clamp(1rem, 5vw, 4.75rem);
  overflow-wrap: anywhere;
  background: var(--guide-surface);
  border: 1px solid var(--guide-border);
  border-radius: clamp(1.25rem, 3vw, 2.25rem);
  box-shadow: var(--guide-shadow);
  text-align: start;
}

:where(h1, h2, h3) {
  margin-inline: 0;
  color: var(--guide-heading);
  font-weight: 780;
  letter-spacing: -0.025em;
  line-height: 1.14;
  overflow-wrap: anywhere;
  text-wrap: balance;
}

h1 {
  max-inline-size: 20ch;
  margin-block: 0 clamp(1.5rem, 4vw, 2.5rem);
  font-size: clamp(2rem, 1rem + 5vw, 4.25rem);
  letter-spacing: -0.045em;
}

h1::after {
  display: block;
  inline-size: clamp(3.5rem, 12vw, 7rem);
  block-size: 0.3rem;
  margin-block-start: clamp(1rem, 2.5vw, 1.5rem);
  border-radius: 999px;
  background: linear-gradient(90deg, #2563eb, #7c3aed);
  content: "";
}

h2 {
  margin-block: clamp(2.5rem, 7vw, 4.5rem) 1rem;
  padding-block-start: clamp(1.25rem, 3vw, 2rem);
  border-block-start: 1px solid var(--guide-border);
  font-size: clamp(1.45rem, 1.15rem + 1.5vw, 2.25rem);
}

h3 {
  margin-block: 0.25rem 0.7rem;
  font-size: clamp(1.08rem, 1rem + 0.45vw, 1.35rem);
}

:where(p, ul, ol, blockquote, pre, table) {
  max-inline-size: 48rem;
}

p {
  margin-block: 0 1.15rem;
  text-wrap: pretty;
}

main > p:first-of-type {
  color: var(--guide-text-soft);
  font-size: clamp(1.05rem, 1rem + 0.35vw, 1.22rem);
  line-height: 1.78;
}

:where(ul, ol) {
  margin-block: 1.2rem 1.75rem;
  padding-block: clamp(1rem, 2.5vw, 1.4rem);
  padding-inline-end: clamp(1rem, 3vw, 1.5rem);
  padding-inline-start: clamp(2.25rem, 6vw, 3.15rem);
  background: var(--guide-surface-muted);
  border: 1px solid var(--guide-border);
  border-radius: 1.15rem;
}

li {
  padding-inline-start: 0.3rem;
}

li + li {
  margin-block-start: 0.55rem;
}

li::marker {
  color: var(--guide-accent);
  font-weight: 800;
}

a {
  color: var(--guide-accent);
  text-decoration-thickness: 0.09em;
  text-underline-offset: 0.18em;
}

a:visited {
  color: var(--guide-accent-strong);
}

:where(a, button, [tabindex]):focus-visible {
  outline: 3px solid var(--guide-focus);
  outline-offset: 4px;
}

main p > a[href^="https://apps.apple.com/app/id"] {
  display: inline-flex;
  min-block-size: 3rem;
  max-inline-size: 100%;
  align-items: center;
  justify-content: center;
  padding-block: 0.78rem;
  padding-inline: clamp(1rem, 4vw, 1.5rem);
  overflow: hidden;
  color: #fff;
  background: linear-gradient(135deg, #1849a9, #6938c6);
  border: 1px solid rgba(255, 255, 255, 0.26);
  border-radius: 999px;
  box-shadow: 0 12px 28px rgba(55, 48, 163, 0.24);
  font-weight: 760;
  line-height: 1.2;
  text-align: center;
  text-decoration: none;
  text-overflow: ellipsis;
  unicode-bidi: isolate;
  vertical-align: middle;
  white-space: nowrap;
  transition:
    transform 160ms ease,
    box-shadow 160ms ease,
    filter 160ms ease;
}

main p > a[href^="https://apps.apple.com/app/id"]:visited {
  color: #fff;
}

main p > a[href^="https://apps.apple.com/app/id"] > strong {
  display: block;
  min-inline-size: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

main > div[itemscope][itemtype="https://schema.org/Question"] {
  max-inline-size: 48rem;
  margin-block: 1rem;
  padding-block: clamp(1.1rem, 3vw, 1.5rem);
  padding-inline: clamp(1rem, 3vw, 1.5rem);
  background: var(--guide-surface-muted);
  border: 1px solid var(--guide-border);
  border-radius: 1.15rem;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.045);
}

main > div[itemscope][itemtype="https://schema.org/Question"] p:last-child {
  margin-block-end: 0;
}

blockquote {
  margin-inline: 0;
  padding-block: 0.75rem;
  padding-inline-start: 1.25rem;
  color: var(--guide-text-soft);
  border-inline-start: 0.25rem solid var(--guide-accent);
}

:where(code, kbd, samp) {
  font-family: ui-monospace, "SFMono-Regular", Consolas, monospace;
}

code {
  padding-block: 0.12em;
  padding-inline: 0.35em;
  background: var(--guide-surface-muted);
  border-radius: 0.35rem;
  font-size: 0.9em;
}

:where(pre, table) {
  overflow-x: auto;
}

img,
svg,
video {
  max-inline-size: 100%;
}

hr {
  margin-block: clamp(2.5rem, 7vw, 4.5rem) 1.5rem;
  border: 0;
  border-block-start: 1px solid var(--guide-border);
}

small {
  color: var(--guide-text-soft);
  font-size: 0.78rem;
  line-height: 1.55;
}

main > p:last-child {
  unicode-bidi: plaintext;
}

@media (hover: hover) {
  main p > a[href^="https://apps.apple.com/app/id"]:hover {
    filter: saturate(1.08);
    box-shadow: 0 16px 34px rgba(55, 48, 163, 0.32);
    transform: translateY(-1px);
  }
}

@media (max-width: 40rem) {
  main {
    inline-size: calc(100% - 1rem);
    padding-inline: 1rem;
    border-radius: 1.25rem;
  }

  main p > a[href^="https://apps.apple.com/app/id"] {
    display: flex;
    inline-size: 100%;
  }
}

@media screen and (prefers-color-scheme: dark) {
  :root {
    --guide-canvas: #070b14;
    --guide-glow: rgba(76, 110, 245, 0.2);
    --guide-surface: rgba(15, 23, 42, 0.97);
    --guide-surface-muted: #151e31;
    --guide-text: #e7ecf5;
    --guide-text-soft: #b8c1d1;
    --guide-heading: #f8fafc;
    --guide-accent: #8ec5ff;
    --guide-accent-strong: #c4b5fd;
    --guide-border: rgba(226, 232, 240, 0.16);
    --guide-focus: #84adff;
    --guide-shadow: 0 30px 90px rgba(0, 0, 0, 0.42);
  }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
  }
}

@media (forced-colors: active) {
  main,
  :where(ul, ol),
  main > div[itemscope][itemtype="https://schema.org/Question"] {
    border: 1px solid CanvasText;
  }
}

@media print {
  :root {
    color-scheme: light;
  }

  body,
  main {
    color: #000;
    background: #fff;
  }

  main {
    inline-size: 100%;
    margin: 0;
    padding: 0;
    border: 0;
    box-shadow: none;
  }

  main p > a[href^="https://apps.apple.com/app/id"],
  main p > a[href^="https://apps.apple.com/app/id"]:visited {
    min-block-size: 0;
    padding-block: 0.25rem;
    color: #000;
    background: transparent;
    border-color: #000;
    box-shadow: none;
  }
}
"""


def stylesheet_href(site: str = SITE) -> str:
    parsed = urllib.parse.urlsplit(site)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f"Invalid guide design site URL: {site}")
    base_path = parsed.path.rstrip("/")
    return f"{base_path}/assets/{ASSET_NAME}"


def design_block(href: str) -> str:
    if not href.startswith("/") or any(char in href for char in "\"'<>"):
        raise ValueError(f"Invalid guide stylesheet href: {href}")
    return "\n".join(
        (
            BLOCK_START,
            f'<link rel="stylesheet" href="{href}">',
            BLOCK_END,
        )
    )


def _without_generated_block(source: str, path: Path) -> str:
    if source.count(BLOCK_START) != source.count(BLOCK_END):
        raise ValueError(f"Malformed guide design markers: {path}")
    cleaned = BLOCK_RE.sub("\n", source)
    if BLOCK_START in cleaned or BLOCK_END in cleaned:
        raise ValueError(f"Malformed guide design block: {path}")
    if ASSET_NAME in cleaned:
        raise ValueError(f"Conflicting guide design stylesheet: {path}")
    return cleaned


def ensure_design(path: Path, href: str) -> bool:
    source = path.read_text(encoding="utf-8")
    if not HEAD_END_RE.search(source):
        raise ValueError(f"Guide design target has no closing head: {path}")
    cleaned = _without_generated_block(source, path)
    viewports = list(VIEWPORT_RE.finditer(cleaned))
    if len(viewports) != 1:
        raise ValueError(
            f"Guide design target must have one viewport meta: "
            f"{path}: found {len(viewports)}"
        )
    insert_index = viewports[0].end()
    updated = (
        cleaned[:insert_index].rstrip()
        + "\n"
        + design_block(href)
        + "\n"
        + cleaned[insert_index:].lstrip()
    )
    return _write_if_changed(path, updated, previous=source)


def remove_design(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    cleaned = _without_generated_block(source, path)
    return _write_if_changed(path, cleaned, previous=source)


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
    href = stylesheet_href(site)
    changed = int(
        _write_if_changed(pages / ASSET_RELATIVE, STYLESHEET)
    )
    for path in sorted(targets):
        changed += int(ensure_design(path, href))

    all_guides = gen_smart_app_banners._guide_pages(pages)
    for path in sorted(all_guides - set(targets)):
        changed += int(remove_design(path))

    languages = {
        gen_smart_app_banners._page_language(path, pages)
        for path in targets
    }
    return {
        "apps": app_count,
        "guide_pages": len(targets),
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
        "Premium guide design: "
        f"{result['apps']} apps, {result['guide_pages']} guide pages, "
        f"{result['languages']} languages, "
        f"{result['changed_files']} files updated"
    )


if __name__ == "__main__":
    main()
