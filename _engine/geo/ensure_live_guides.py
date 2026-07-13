#!/usr/bin/env python3
"""Create an honest zero-cost guide when a newly live app has no guide yet."""

from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))
sys.path.insert(0, str(HERE))

from aeo_guide import GUIDES, PAGES, render, write_sitemap  # noqa: E402
from aeo_guide_free_batch3 import C as CURATED_CONTENT  # noqa: E402
from aeo_guide_i18n import reconcile_hreflang  # noqa: E402
from appstore_live import live_app_keys  # noqa: E402
from videogen.registry import APPS, APPSTORE  # noqa: E402


def fallback_content(key: str) -> dict[str, object]:
    app = APPS[key]
    name = str(app["name"]).strip()
    summary = " ".join(str(app.get("sub") or app.get("tag") or "").split())
    category = str(app.get("category") or "iOS app").replace("-", " ")
    bullets = [
        " ".join(str(item).split())
        for item in app.get("cta_bullets", [])
        if str(item).strip()
    ]
    criteria = bullets[:4]
    for item in (
        f"A clear experience designed for {category} use",
        "Reliable access to the features you expect to use most",
        "Privacy and safety controls appropriate for the intended audience",
        "Current compatibility and purchase details shown on the App Store",
    ):
        if len(criteria) >= 4:
            break
        if item not in criteria:
            criteria.append(item)
    feature_summary = ", ".join(criteria[:3]).rstrip(".")
    return {
        "title": f"{name}: iPhone App Guide",
        "meta": summary or f"An independent guide to {name} for iPhone.",
        "intro": (
            f"When comparing {category} apps, start with the features that fit "
            f"your real situation, then confirm current compatibility and "
            f"purchase details on the App Store. {name} is one option to review."
        ),
        "criteria": criteria,
        "why": (
            f"{name} is designed around {summary.rstrip('.') or category}. "
            f"Its listed strengths include {feature_summary.lower()}."
        ),
        "faqs": [
            {
                "q": f"What is {name}?",
                "a": summary or f"{name} is an iPhone app in the {category} category.",
            },
            {
                "q": f"Who should consider {name}?",
                "a": (
                    f"It may suit people looking for {category} features such as "
                    f"{feature_summary.lower()}."
                ),
            },
            {
                "q": f"What should I compare before choosing {name}?",
                "a": (
                    "Compare the features you will actually use, privacy and "
                    "safety needs, device compatibility, and current App Store details."
                ),
            },
            {
                "q": f"Where can I get {name}?",
                "a": f"Use the direct App Store link in this guide to view {name}.",
            },
            {
                "q": "Can app details change after this guide is published?",
                "a": (
                    "Yes. Check the current App Store listing for the latest "
                    "compatibility, features, and purchase information."
                ),
            },
        ],
    }


def ensure_live_guides() -> list[str]:
    live = live_app_keys(APPSTORE, PAGES, refresh=False)
    Path(GUIDES).mkdir(parents=True, exist_ok=True)
    created = []
    for key in APPS:
        if key not in live:
            continue
        path = Path(GUIDES) / f"{key}.html"
        if path.is_file():
            continue
        content = CURATED_CONTENT.get(key) or fallback_content(key)
        path.write_text(render(key, content), encoding="utf-8")
        created.append(key)
    reconcile_hreflang(live)
    write_sitemap()
    return created


def main() -> None:
    created = ensure_live_guides()
    print(
        f"Live guide fallback: created={len(created)} "
        f"apps={','.join(created) or 'none'}"
    )


if __name__ == "__main__":
    main()
