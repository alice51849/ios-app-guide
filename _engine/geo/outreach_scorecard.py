#!/usr/bin/env python3
"""Build a zero-cost, factual outreach coverage scorecard for every app."""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))
sys.path.insert(0, HERE)

from appstore_live import live_app_keys  # noqa: E402
from videogen.registry import APPS, APPSTORE, appstore_url  # noqa: E402
import queries  # noqa: E402

PAGES = os.environ.get("GEO_PAGES", os.path.join(HERE, "pages"))
REPORTS = os.environ.get("GEO_REPORTS", os.path.join(HERE, "reports"))
JSON_OUT = os.path.join(REPORTS, "outreach_coverage.json")
MD_OUT = os.path.join(REPORTS, "outreach_coverage.md")


def slugify(question):
    return re.sub(
        r"-+", "-", re.sub(r"[^a-z0-9]+", "-", question.lower())
    ).strip("-")


def _portfolio_social_posts(public_keys):
    catalog_path = os.path.join(PAGES, "apps.json")
    required_assets = (
        os.path.join(PAGES, ".github", "scripts", "portfolio_daily.py"),
        os.path.join(PAGES, ".github", "workflows", "portfolio-daily.yml"),
        catalog_path,
    )
    if not all(os.path.exists(path) for path in required_assets):
        return []
    try:
        with open(catalog_path, encoding="utf-8") as handle:
            catalog = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(catalog, list):
        raise ValueError("Portfolio app catalog must be an array")
    public_ids = {
        str(APPSTORE[key])
        for key in public_keys
        if key in APPSTORE and APPSTORE[key]
    }
    catalog_ids = set()
    for item in catalog:
        if not isinstance(item, dict):
            raise ValueError("Portfolio app catalog entries must be objects")
        match = re.fullmatch(
            r"https://apps\.apple\.com/app/id(\d+)",
            str(item.get("appStoreUrl", "")),
        )
        if match:
            catalog_ids.add(match.group(1))
    return [
        {
            "app": app_id,
            "lang": "zh-Hant",
            "source": "portfolio-daily",
        }
        for app_id in sorted(public_ids & catalog_ids)
    ]


def _social_posts(public_keys):
    path = os.path.join(
        PAGES, ".github", "scripts", "telegram_posts.json"
    )
    try:
        with open(path, encoding="utf-8") as handle:
            posts = json.load(handle)
    except (OSError, json.JSONDecodeError):
        posts = []
    if not isinstance(posts, list):
        raise ValueError("Telegram post pool must be an array")
    return posts + _portfolio_social_posts(public_keys)


def _exists(relative):
    return os.path.exists(os.path.join(PAGES, relative))


def build_rows(public_keys):
    posts = _social_posts(public_keys)
    alternatives = os.path.join(PAGES, "alternatives")
    alt_files = os.listdir(alternatives) if os.path.isdir(alternatives) else []
    rows = []
    for key, app in APPS.items():
        public = key in public_keys
        app_id = APPSTORE.get(key, "")
        app_posts = [
            item for item in posts if str(item.get("app", "")) == str(app_id)
        ]
        languages = sorted({
            item.get("lang") for item in app_posts if item.get("lang")
        })
        planned = {
            slugify(question)
            for question in queries.ALL.get(key, queries.CURATED.get(key, []))
            if slugify(question)
        }
        answers = sum(
            _exists(f"answers/{slug}.html") for slug in planned
        )
        answer_ratio = answers / len(planned) if planned else 0.0
        alt_count = sum(
            name.startswith(key + "-") and name.endswith(".html")
            for name in alt_files
        )
        assets = {
            "detail": _exists(f"en-US/{key}.html"),
            "hub": _exists(f"hubs/{key}.html"),
            "guide": _exists(f"guides/{key}.html"),
            "story": _exists(f"stories/{key}.html"),
            "catalog": public and _exists("apps/index.html"),
        }
        score = (
            min(answer_ratio, 1.0) * 0.35
            + min(len(languages) / 3, 1.0) * 0.20
            + float(assets["detail"]) * 0.10
            + float(assets["hub"]) * 0.10
            + min(alt_count / 2, 1.0) * 0.10
            + float(assets["guide"]) * 0.05
            + float(assets["story"]) * 0.05
            + float(assets["catalog"]) * 0.05
        ) if public else 0.0
        rows.append({
            "key": key,
            "name": app["name"],
            "public": public,
            "appstore": appstore_url(key) if public else "",
            "coverage_score": round(score, 3),
            "answers": answers,
            "planned_answers": len(planned),
            "social_posts": len(app_posts),
            "social_languages": languages,
            "alternatives": alt_count,
            **assets,
        })
    return rows


def write_reports(rows):
    os.makedirs(REPORTS, exist_ok=True)
    public = [row for row in rows if row["public"]]
    average = (
        round(sum(row["coverage_score"] for row in public) / len(public), 3)
        if public else 0.0
    )
    payload = {
        "generated_on": date.today().isoformat(),
        "metric": "owned outreach asset coverage (not AI recommendation share-of-voice)",
        "public_apps": len(public),
        "average_public_coverage": average,
        "rows": rows,
    }
    with open(JSON_OUT, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    ranked = sorted(
        public,
        key=lambda row: (row["coverage_score"], row["name"].lower()),
    )
    lines = [
        f"# Zero-cost outreach coverage — {payload['generated_on']}",
        "",
        "> Factual owned-asset coverage only. This does not pretend to measure live AI recommendations.",
        "",
        f"Public apps: **{len(public)}** · Average coverage: **{average:.1%}**",
        "",
        "| App | Coverage | Answers | Social languages | Alternatives | Hub / guide / story |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in ranked:
        status = " / ".join(
            name for name in ("hub", "guide", "story") if row[name]
        ) or "—"
        lines.append(
            f"| {row['name']} | {row['coverage_score']:.1%} | "
            f"{row['answers']}/{row['planned_answers']} | "
            f"{len(row['social_languages'])} | {row['alternatives']} | {status} |"
        )
    unavailable = [row["name"] for row in rows if not row["public"]]
    if unavailable:
        lines += [
            "",
            "## Excluded until publicly available",
            "",
            ", ".join(unavailable),
        ]
    with open(MD_OUT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return payload


def main():
    public = live_app_keys(APPSTORE, PAGES, refresh=False)
    payload = write_reports(build_rows(public))
    print(
        f"✓ outreach coverage: {payload['public_apps']} public apps · "
        f"{payload['average_public_coverage']:.1%} average"
    )


if __name__ == "__main__":
    main()
