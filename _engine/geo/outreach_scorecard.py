#!/usr/bin/env python3
"""Build a zero-cost, factual outreach coverage scorecard for every app."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date, datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))
sys.path.insert(0, HERE)

from live_app_manifest import (  # noqa: E402
    ManifestError, app_statuses, load_manifest, runtime_manifest_path,
    validate_manifest,
)
from videogen.registry import APPS, APPSTORE, appstore_url  # noqa: E402
import queries  # noqa: E402
from aeo_answers import is_english_answer_question  # noqa: E402

PAGES = os.environ.get("GEO_PAGES", os.path.join(HERE, "pages"))
REPORTS = os.environ.get("GEO_REPORTS", str(runtime_manifest_path().parent / "outreach"))
JSON_OUT = os.path.join(REPORTS, "outreach_coverage.json")
MD_OUT = os.path.join(REPORTS, "outreach_coverage.md")


def validate_public_inventory(
    public_keys, baseline_path=None, appstore=APPSTORE, *,
    now=None, require_fresh=True,
):
    """Validate the shared contract, not a possibly shrunken apps.json array."""
    try:
        manifest = load_manifest(
            baseline_path, now=now, require_fresh=require_fresh,
        )
    except ManifestError as error:
        raise RuntimeError(str(error)) from error
    drift = [
        key for key, app in manifest["apps"].items()
        if str(appstore.get(key, "")) != app["app_id"]
    ]
    if drift:
        raise RuntimeError(
            "Live manifest registry roster drift: " + ", ".join(sorted(drift))
        )
    if public_keys is None:
        return manifest
    unknown_keys = set(public_keys) - set(manifest["apps"])
    if unknown_keys:
        raise RuntimeError(
            "Live App inventory roster drift; unregistered keys: "
            + ", ".join(sorted(unknown_keys))
        )
    missing = set(manifest["apps"]) - set(public_keys)
    if missing:
        raise RuntimeError(
            "Live App inventory unexpectedly shrank; missing Apps: "
            + ", ".join(sorted(missing))
        )
    return manifest


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


def build_rows(public_keys=None, *, manifest=None, now=None):
    manifest = (
        load_manifest(require_fresh=False, now=now)
        if manifest is None else validate_manifest(manifest, require_fresh=False, now=now)
    )
    states = app_statuses(manifest, now=now)
    pending = {entry["key"]: entry for entry in manifest.get("pending_adoptions", [])}
    if public_keys is None:
        public_keys = {
            key for key, state in states.items()
            if state["public_eligible"]
        }
    else:
        public_keys = set(public_keys)
    posts = _social_posts(public_keys)
    alternatives = os.path.join(PAGES, "alternatives")
    alt_files = os.listdir(alternatives) if os.path.isdir(alternatives) else []
    rows = []
    apps = {**APPS, **manifest["apps"]}
    for key, app in apps.items():
        expected = key in manifest["apps"]
        state = dict(states.get(key, {
            "inventory_status": "unknown" if key in pending else "not_in_live_roster",
            "inventory_reason": (
                "Registered App observed; awaiting safe automatic roster adoption"
                if key in pending else "Not in the versioned live roster"
            ),
            "inventory_observed_at": None,
            "public_eligible": False,
        }))
        if expected and key not in public_keys and state["inventory_status"] == "live":
            state["inventory_status"] = "unknown"
            state["inventory_reason"] = "Missing from supplied live keys; roster retained"
        public = expected and key in public_keys and state["public_eligible"]
        app_id = app.get("app_id", APPSTORE.get(key, ""))
        app_posts = [
            item for item in posts if str(item.get("app", "")) == str(app_id)
        ]
        languages = sorted({
            item.get("lang") for item in app_posts if item.get("lang")
        })
        # Only English questions produce a page under answers/. CJK-only queries
        # (e.g. "教小孩注音的 app") collapse to a degenerate slug and are served by
        # the localized pipeline under <locale>/answers/, so counting them here
        # invented a permanent gap that could never be closed.
        planned = {
            slugify(question)
            for question in queries.ALL.get(key, queries.CURATED.get(key, []))
            if slugify(question) and is_english_answer_question(question)
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
            "catalog": expected and _exists("apps/index.html"),
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
        ) if expected else 0.0
        rows.append({
            "key": key,
            "name": app["name"],
            "app_id": str(app_id),
            "in_live_roster": expected,
            **state,
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


def write_reports(rows, manifest=None):
    os.makedirs(REPORTS, exist_ok=True)
    public = [row for row in rows if row["public"]]
    roster = [row for row in rows if row.get("in_live_roster", row["public"])]
    inventory_gaps = [
        row["key"] for row in roster if row.get("inventory_status") != "live"
    ]
    verified = [row for row in public if row.get("inventory_status") == "live"]
    average = (
        round(sum(row["coverage_score"] for row in public) / len(public), 3)
        if public else 0.0
    )
    payload = {
        "schema": "lumi.outreach-scorecard/v2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_on": date.today().isoformat(),
        "metric": "owned outreach asset coverage (not AI recommendation share-of-voice)",
        "live_app_count": len(roster),
        "public_apps": len(public),
        "verified_public_apps": len(verified),
        "inventory_gaps": inventory_gaps,
        "inventory_complete": (
            manifest is not None and {row["key"] for row in roster} == set(manifest["apps"])
        ),
        "availability_complete": not inventory_gaps,
        "average_public_coverage": average,
        "rows": rows,
    }
    if manifest is not None:
        payload["live_inventory"] = manifest
    with open(JSON_OUT, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    ranked = sorted(
        roster,
        key=lambda row: (row["coverage_score"], row["name"].lower()),
    )
    lines = [
        f"# Zero-cost outreach coverage — {payload['generated_on']}",
        "",
        "> Factual owned-asset coverage only. This does not pretend to measure live AI recommendations.",
        "",
        f"Live roster: **{len(roster)}** · Eligible: **{len(public)}** · Freshly verified: **{len(verified)}** · Average roster coverage: **{average:.1%}**",
        "",
        "| App | Inventory | Coverage | Answers | Social languages | Alternatives | Hub / guide / story | Reason |",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    for row in ranked:
        status = " / ".join(
            name for name in ("hub", "guide", "story") if row[name]
        ) or "—"
        lines.append(
            f"| {row['name']} | {row.get('inventory_status', 'unknown')} | {row['coverage_score']:.1%} | "
            f"{row['answers']}/{row['planned_answers']} | "
            f"{len(row['social_languages'])} | {row['alternatives']} | {status} | "
            f"{row.get('inventory_reason', '')} |"
        )
    unavailable = [row for row in rows if not row.get("in_live_roster", row["public"])]
    if unavailable:
        lines += [
            "",
            "## Registered Apps outside the verified live roster",
            "",
            "| App | Inventory | Reason |",
            "|---|---|---|",
            *[
                f"| {row['name']} | {row.get('inventory_status', 'unknown')} | {row.get('inventory_reason', '')} |"
                for row in unavailable
            ],
        ]
    with open(MD_OUT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return payload


def incomplete_public_rows(rows):
    return [
        row
        for row in rows
        if row["public"] and row["coverage_score"] < 1.0
    ]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        default=os.environ.get("GROWTH_LIVE_MANIFEST"),
        help="Explicit v2 availability snapshot; a missing snapshot is advisory, not a missing roster.",
    )
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="Exit non-zero when any public App has less than full coverage.",
    )
    args = parser.parse_args(argv)
    try:
        manifest = validate_public_inventory(
            None, args.manifest, require_fresh=False,
        )
        rows = build_rows(manifest=manifest)
    except (RuntimeError, ManifestError) as error:
        print(f"outreach inventory invalid: {error}", file=sys.stderr)
        return 1
    payload = write_reports(rows, manifest)
    print(
        f"outreach coverage: {payload['live_app_count']} roster apps · "
        f"{payload['public_apps']} eligible · {payload['verified_public_apps']} freshly verified · "
        f"{payload['average_public_coverage']:.1%} average"
    )
    if not payload["inventory_complete"]:
        print("outreach inventory incomplete", file=sys.stderr)
        return 1
    if not payload["availability_complete"]:
        print(
            "outreach availability advisory (roster retained): "
            + ", ".join(payload["inventory_gaps"]),
            file=sys.stderr,
        )
    incomplete = incomplete_public_rows(rows)
    if args.require_complete and incomplete:
        summary = ", ".join(
            f"{row['key']}={row['coverage_score']:.1%}"
            for row in incomplete
        )
        print(f"outreach coverage incomplete: {summary}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
