#!/usr/bin/env python3
"""Build the measured Google Images unique-asset real-task canary.

The canary intentionally uses only checksum-pinned, existing App Store
screenshots.  It never synthesizes UI, results, reviews, or before/after
evidence.  Every one of the 38 authentic images owns exactly one page and is
assigned within its App stratum into:

* treatment: linked from a human-readable hub and a regular sitemap;
* holdout: discoverable only through the image sitemap.

Both arms receive the same technical image treatment, but different authentic
screens are heterogeneous randomized units rather than falsely matched copies.
The public ledger is immutable experiment design; observations live in the
private measurement state maintained by
``reports/google_images_canary_measure.py``.
"""

from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import html
import json
import os
from pathlib import Path
import re
import signal
import tempfile
from typing import Any, Iterable
import urllib.parse
import xml.etree.ElementTree as ET

from PIL import Image

from app_store_storefronts import (
    campaign_app_store_url,
    resolve_provider_token,
    validated_app_store_url,
)
import gen_image_sitemap
from google_images_canary_contract import (
    DIGEST_SCHEMA,
    canonical_value,
    content_attestation,
    design_digest,
    stratified_assignment,
)
from google_images_canary_spec import SPEC
from publisher_intent_catalog import write_text_if_changed_atomic


HERE = Path(__file__).resolve().parent
PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
REPORTS = Path(os.environ.get("GEO_REPORTS", HERE / "reports"))

ROOT_RELATIVE = Path("google-images-canary")
LEDGER_NAME = "google_images_canary_experiment.json"
IMAGE_SITEMAP_RELATIVE = Path("sitemap_google_images_canary.xml")
TREATMENT_SITEMAP_RELATIVE = Path("sitemap_google_images_treatment.xml")
COVERAGE_JSON = "google_images_canary_coverage.json"
COVERAGE_MD = "google_images_canary_coverage.md"
HOLDOUT_MARKER = (
    '<meta name="iag-experiment-arm" content="sitemap-only-holdout">'
)
TREATMENT_MARKER = '<meta name="iag-experiment-arm" content="treatment">'
MANAGED_MARKER = "<!--iag-google-images-canary:v2-->"
LEGACY_MANAGED_MARKER = "<!--iag-google-images-canary:v1-->"
EXPERIMENT_SCHEMA = "lumi.google-images-canary-experiment/v2"
MIN_IMAGE_WIDTH = 1200
CAMPAIGN_RE = re.compile(r"[A-Za-z0-9_/]{1,30}")
PAGE_ID_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
SHA256_RE = re.compile(r"[a-f0-9]{64}")
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
_CANCELLED = False


def _request_cancel(_signum: int, _frame: object) -> None:
    global _CANCELLED
    _CANCELLED = True


def _check_cancelled() -> None:
    if _CANCELLED:
        raise InterruptedError("Google Images canary build cancelled")


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest_json(value: object) -> str:
    return _digest_bytes(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def _object_without_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"Duplicate JSON key: {key}")
        value[key] = item
    return value


def _json_loads_strict(payload: str) -> Any:
    return json.loads(
        payload,
        object_pairs_hook=_object_without_duplicate_keys,
    )


def _single_line(value: object, label: str) -> str:
    result = " ".join(str(value).split())
    if not result:
        raise ValueError(f"Empty canary field: {label}")
    return result


def _apps(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(app["key"]): app for app in spec["apps"]}


def validate_spec(spec: dict[str, Any] = SPEC) -> dict[str, int]:
    if spec.get("schema") != EXPERIMENT_SCHEMA:
        raise ValueError("Unexpected Google Images canary schema")
    if spec.get("observation_window_days") != {"minimum": 42, "maximum": 56}:
        raise ValueError("Canary observation window must be 6–8 weeks")
    if not _single_line(spec.get("assignment_salt"), "assignment_salt"):
        raise ValueError("Missing assignment salt")
    if (
        not _single_line(
            spec.get("supersedes_experiment_id"),
            "supersedes_experiment_id",
        )
        or spec["supersedes_experiment_id"] == spec.get("experiment_id")
    ):
        raise ValueError("Canary must supersede a different archived design")

    apps = _apps(spec)
    if len(apps) != 7 or len(apps) != len(spec["apps"]):
        raise ValueError("Canary must contain exactly seven unique apps")
    categories = {str(app["category"]) for app in apps.values()}
    if len(categories) != 7:
        raise ValueError("Canary apps must represent seven distinct categories")

    app_store_ids: set[str] = set()
    app_store_urls: set[str] = set()
    asset_ids: set[str] = set()
    public_paths: set[str] = set()
    source_paths: set[str] = set()
    source_digests: set[str] = set()
    pixel_digests: set[str] = set()
    assets_by_app: dict[str, set[str]] = {}
    for key, app in apps.items():
        if PAGE_ID_RE.fullmatch(key) is None:
            raise ValueError(f"Invalid canary app key: {key}")
        app_id = str(app["app_store_id"])
        if app_id in app_store_ids:
            raise ValueError(f"Duplicate canary App Store ID: {app_id}")
        app_store_ids.add(app_id)
        store_url = validated_app_store_url(
            str(app["app_store_url"]), expected_app_id=app_id
        )
        if urllib.parse.urlsplit(store_url).query:
            raise ValueError(f"Canary source URL must be clean: {store_url}")
        if store_url in app_store_urls:
            raise ValueError(f"Duplicate canary App Store URL: {store_url}")
        app_store_urls.add(store_url)
        campaign = str(app["campaign_token"])
        if CAMPAIGN_RE.fullmatch(campaign) is None:
            raise ValueError(f"Invalid canary campaign token: {campaign}")
        if len(app.get("assets", [])) < 2:
            raise ValueError(f"{key} must provide at least two authentic images")
        assets_by_app[key] = set()
        for asset in app["assets"]:
            asset_id = str(asset["id"])
            if asset_id in asset_ids:
                raise ValueError(f"Duplicate canary asset ID: {asset_id}")
            asset_ids.add(asset_id)
            assets_by_app[key].add(asset_id)
            public_path = str(asset.get("public_path", ""))
            source_path = str(asset.get("source_path", ""))
            source_digest = str(asset.get("sha256", ""))
            pixel_digest = str(asset.get("pixel_sha256", ""))
            if (
                not public_path
                or public_path in public_paths
                or not source_path
                or source_path in source_paths
                or SHA256_RE.fullmatch(source_digest) is None
                or source_digest in source_digests
                or SHA256_RE.fullmatch(pixel_digest) is None
                or pixel_digest in pixel_digests
            ):
                raise ValueError(
                    f"Duplicate or invalid canary asset ownership: {asset_id}"
                )
            public_paths.add(public_path)
            source_paths.add(source_path)
            source_digests.add(source_digest)
            pixel_digests.add(pixel_digest)
            if SHA256_RE.fullmatch(str(asset["sha256"])) is None:
                raise ValueError(f"Invalid canary asset digest: {asset_id}")
            width, height = int(asset["width"]), int(asset["height"])
            if width < MIN_IMAGE_WIDTH or height <= 0:
                raise ValueError(
                    f"Canary image is below {MIN_IMAGE_WIDTH}px: {asset_id}"
                )
            if asset.get("locale") != "en-US":
                raise ValueError(f"Unverified canary asset locale: {asset_id}")
            if asset.get("source_type") != "app_store_screenshot":
                raise ValueError(f"Unverified canary asset type: {asset_id}")

    if len(asset_ids) != 38:
        raise ValueError("Canary must pin exactly 38 unique authentic assets")
    units = spec.get("units")
    if not isinstance(units, list) or len(units) != 38:
        raise ValueError("Canary must define exactly 38 unique asset-page units")
    assignments = stratified_assignment(spec)
    page_ids: set[str] = set()
    used_assets: set[str] = set()
    signatures: set[str] = set()
    app_unit_counts = {key: 0 for key in apps}
    app_arm_counts = {
        key: {"treatment": 0, "holdout": 0}
        for key in apps
    }
    treatment = holdout = 0
    for task in units:
        if not isinstance(task, dict):
            raise ValueError("Canary unit is not an object")
        page_id = str(task["id"])
        app_key = str(task["app"])
        asset_id = str(task.get("asset", ""))
        if PAGE_ID_RE.fullmatch(page_id) is None or page_id in page_ids:
            raise ValueError(f"Invalid or duplicate canary page ID: {page_id}")
        page_ids.add(page_id)
        if app_key not in apps:
            raise ValueError(f"Unknown canary app: {app_key}")
        app_unit_counts[app_key] += 1
        if asset_id not in assets_by_app[app_key] or asset_id in used_assets:
            raise ValueError(
                f"{page_id} does not own one unique asset from {app_key}"
            )
        used_assets.add(asset_id)
        for field in ("title", "problem", "result", "image_context"):
            _single_line(task.get(field), f"{page_id}.{field}")
        steps = task.get("steps")
        if not isinstance(steps, list) or len(steps) != 3:
            raise ValueError(f"{page_id} must contain exactly three steps")
        if any(not _single_line(step, f"{page_id}.steps") for step in steps):
            raise ValueError(f"{page_id} has an empty step")
        signature = _digest_json(
            {
                "problem": task["problem"],
                "steps": steps,
                "result": task["result"],
            }
        )
        if signature in signatures:
            raise ValueError(f"Duplicate task value in canary: {page_id}")
        signatures.add(signature)
        assignment = assignments[page_id]
        arm = str(assignment["arm"])
        app_arm_counts[app_key][arm] += 1
        treatment += int(arm == "treatment")
        holdout += int(arm == "holdout")

    if used_assets != asset_ids:
        raise ValueError("Canary does not use every authentic asset exactly once")
    if app_unit_counts != {
        key: len(app["assets"])
        for key, app in apps.items()
    }:
        raise ValueError(
            f"Canary unit distribution does not match assets: {app_unit_counts}"
        )
    if any(
        abs(counts["treatment"] - counts["holdout"]) > 1
        for counts in app_arm_counts.values()
    ):
        raise ValueError(
            f"Canary app strata are not balanced: {app_arm_counts}"
        )
    if treatment != 19 or holdout != 19:
        raise ValueError(
            f"Canary assignment must be 19/19, got {treatment}/{holdout}"
        )
    return {
        "apps": len(apps),
        "categories": len(categories),
        "units": len(units),
        "pages": len(page_ids),
        "treatment": treatment,
        "holdout": holdout,
    }


def _catalog_records(pages: Path) -> list[dict[str, Any]]:
    path = pages / "apps.json"
    try:
        value = _json_loads_strict(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise ValueError(f"Cannot read verified live app catalog: {path}") from error
    if not isinstance(value, list):
        raise ValueError(f"Verified live app catalog is not a list: {path}")
    return [record for record in value if isinstance(record, dict)]


def verify_live_apps(
    pages: Path,
    spec: dict[str, Any] = SPEC,
) -> None:
    by_id = {
        str(record.get("appStoreUrl", "")).rsplit("id", 1)[-1]: record
        for record in _catalog_records(pages)
        if re.fullmatch(
            r"https://apps\.apple\.com/app/id\d{9,12}",
            str(record.get("appStoreUrl", "")),
        )
    }
    for app in spec["apps"]:
        app_id = str(app["app_store_id"])
        record = by_id.get(app_id)
        if record is None:
            raise ValueError(
                f"Canary app is not in the verified live catalog: {app['key']}"
            )
        expected = {
            "name": app["name"],
            "category": app["category"],
            "appStoreUrl": app["app_store_url"],
            "guideUrl": app["guide_url"],
        }
        mismatches = {
            key: (record.get(key), value)
            for key, value in expected.items()
            if record.get(key) != value
        }
        if mismatches:
            raise ValueError(
                f"Canary app catalog mismatch for {app['key']}: {mismatches}"
            )


def _asset_path(pages: Path, asset: dict[str, Any]) -> Path:
    relative = Path(str(asset["public_path"]))
    target = (pages / relative).resolve()
    try:
        target.relative_to(pages.resolve())
    except ValueError as error:
        raise ValueError(f"Canary asset escapes Pages: {relative}") from error
    return target


def _pixel_digest(path: Path) -> str:
    try:
        with Image.open(path) as image:
            rgba = image.convert("RGBA")
            material = (
                f"{rgba.width}x{rgba.height}:RGBA\0".encode("ascii")
                + rgba.tobytes()
            )
    except (OSError, SyntaxError) as error:
        raise ValueError(f"Invalid canary image pixels: {path}") from error
    return _digest_bytes(material)


def verify_asset(
    pages: Path,
    asset: dict[str, Any],
) -> Path:
    target = _asset_path(pages, asset)
    try:
        payload = target.read_bytes()
    except OSError as error:
        raise FileNotFoundError(f"Missing canary source image: {target}") from error
    actual_digest = _digest_bytes(payload)
    if actual_digest != asset["sha256"]:
        raise ValueError(
            f"Canary image digest mismatch for {asset['id']}: {actual_digest}"
        )
    try:
        with Image.open(target) as image:
            image_format = image.format
            size = image.size
            image.verify()
    except (OSError, SyntaxError) as error:
        raise ValueError(f"Invalid canary image: {target}") from error
    expected_size = (int(asset["width"]), int(asset["height"]))
    if image_format != "PNG" or size != expected_size:
        raise ValueError(
            f"Canary image format/size mismatch for {asset['id']}: "
            f"{image_format} {size}, expected PNG {expected_size}"
        )
    if size[0] < MIN_IMAGE_WIDTH:
        raise ValueError(f"Canary image is below {MIN_IMAGE_WIDTH}px: {target}")
    if _pixel_digest(target) != asset["pixel_sha256"]:
        raise ValueError(
            f"Canary image pixel digest mismatch for {asset['id']}"
        )
    return target


def _copy_atomic(source: Path, destination: Path) -> bool:
    source_payload = source.read_bytes()
    try:
        if destination.read_bytes() == source_payload:
            return False
    except OSError:
        pass
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".pending",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(source_payload)
            handle.flush()
            os.fchmod(handle.fileno(), 0o644)
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
        temporary = None
        directory = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return True


def materialize_assets(
    pages: Path,
    source_home: Path,
    spec: dict[str, Any] = SPEC,
) -> int:
    """Copy the pinned existing screenshots; never render or alter image pixels."""
    changed = 0
    for app in spec["apps"]:
        for asset in app["assets"]:
            _check_cancelled()
            source_relative = Path(str(asset["source_path"]))
            if (
                source_relative.parts
                and source_relative.parts[0] == "00_GrowthEngine"
            ):
                source = (
                    HERE.parent / Path(*source_relative.parts[1:])
                ).resolve()
            else:
                source = (source_home / source_relative).resolve()
            if not source.is_file():
                raise FileNotFoundError(
                    f"Pinned authentic screenshot is unavailable: {source}"
                )
            payload = source.read_bytes()
            if _digest_bytes(payload) != asset["sha256"]:
                raise ValueError(
                    f"Pinned screenshot changed for {asset['id']}: {source}"
                )
            try:
                with Image.open(source) as image:
                    size, image_format = image.size, image.format
                    image.verify()
            except (OSError, SyntaxError) as error:
                raise ValueError(f"Invalid source screenshot: {source}") from error
            if image_format != "PNG" or size != (
                int(asset["width"]),
                int(asset["height"]),
            ):
                raise ValueError(
                    f"Source screenshot dimensions changed for {asset['id']}"
                )
            if _pixel_digest(source) != asset["pixel_sha256"]:
                raise ValueError(
                    f"Pinned screenshot pixels changed for {asset['id']}"
                )
            changed += int(_copy_atomic(source, _asset_path(pages, asset)))
    return changed


def records(
    spec: dict[str, Any] = SPEC,
    site: str = SITE,
    *,
    provider_token: str,
) -> list[dict[str, Any]]:
    if not provider_token:
        raise ValueError(
            "APP_STORE_PROVIDER_TOKEN is required: canary CTA cannot be partial"
        )
    apps = _apps(spec)
    assignments = stratified_assignment(spec)
    output: list[dict[str, Any]] = []
    for task in spec["units"]:
        app = apps[str(task["app"])]
        app_assets = {
            str(asset["id"]): asset for asset in app["assets"]
        }
        store_url = campaign_app_store_url(
            str(app["app_store_url"]),
            str(app["campaign_token"]),
            provider_token=provider_token,
        )
        validated_app_store_url(
            store_url,
            expected_app_id=str(app["app_store_id"]),
        )
        asset = app_assets[str(task["asset"])]
        creative_id = str(task["id"])
        assignment = assignments[creative_id]
        page_relative = ROOT_RELATIVE / f"{creative_id}.html"
        page_url = f"{site}/{page_relative.as_posix()}"
        image_url = f"{site}/{asset['public_path']}"
        output.append(
            {
                "unit_id": creative_id,
                "creative_id": creative_id,
                "arm": assignment["arm"],
                "stratum": assignment["stratum"],
                "assignment_rank": assignment["assignment_rank"],
                "stratum_size": assignment["stratum_size"],
                "stratum_treatment_slots": assignment[
                    "stratum_treatment_slots"
                ],
                "page_relative": page_relative.as_posix(),
                "page_url": page_url,
                "image_url": image_url,
                "asset": asset,
                "app": app,
                "task": task,
                "store_url": store_url,
                "experiment_id": spec["experiment_id"],
            }
        )
    return sorted(output, key=lambda item: str(item["creative_id"]))


def _schema(record: dict[str, Any], site: str) -> dict[str, Any]:
    app = record["app"]
    task = record["task"]
    asset = record["asset"]
    image_id = f"{record['page_url']}#primary-image"
    app_id = f"{site}/apps/{app['key']}#software"
    return {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "ImageObject",
                "@id": image_id,
                "contentUrl": record["image_url"],
                "url": record["image_url"],
                "encodingFormat": "image/png",
                "width": int(asset["width"]),
                "height": int(asset["height"]),
                "caption": (
                    f"Real {app['name']} App Store screenshot used for "
                    f"{task['image_context']}."
                ),
                "inLanguage": "en-US",
                "representativeOfPage": True,
                "creditText": "Lumi Studio",
                "creator": {
                    "@type": "Organization",
                    "name": "Lumi Studio",
                    "url": site,
                },
            },
            {
                "@type": "SoftwareApplication",
                "@id": app_id,
                "name": app["name"],
                "operatingSystem": "iOS",
                "applicationCategory": app["schema_category"],
                "description": app["value_prop"],
                "url": app["guide_url"],
                "downloadUrl": record["store_url"],
                "image": {"@id": image_id},
            },
            {
                "@type": "HowTo",
                "@id": f"{record['page_url']}#workflow",
                "name": task["title"],
                "description": task["problem"],
                "image": {"@id": image_id},
                "step": [
                    {
                        "@type": "HowToStep",
                        "position": position,
                        "name": f"Step {position}",
                        "text": step,
                    }
                    for position, step in enumerate(task["steps"], start=1)
                ],
            },
            {
                "@type": "WebPage",
                "@id": record["page_url"],
                "url": record["page_url"],
                "name": task["title"],
                "description": task["problem"],
                "inLanguage": "en-US",
                "isPartOf": {"@id": f"{site}/#website"},
                "primaryImageOfPage": {"@id": image_id},
                "about": {"@id": app_id},
            },
        ],
    }


STYLE = """
:root{color-scheme:light;--ink:#17202a;--muted:#52606d;--paper:#fffdf8;
--line:#e7dfd2;--accent:#5b3fd4;--soft:#f4f0ff}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);
font:17px/1.62 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
a{color:#4931b8}.wrap{width:min(1120px,94vw);margin:auto}.top{padding:18px 0;
display:flex;justify-content:space-between;gap:20px;align-items:center}
.brand{font-weight:800;text-decoration:none}.crumb{color:var(--muted);font-size:14px}
.hero{padding:44px 0 28px;display:grid;grid-template-columns:minmax(0,1.08fr)
minmax(320px,.92fr);gap:44px;align-items:start}.eyebrow{text-transform:uppercase;
letter-spacing:.12em;font-weight:800;color:var(--accent);font-size:13px}
h1{font-size:clamp(36px,5vw,68px);line-height:1.04;letter-spacing:-.035em;
margin:.18em 0}.answer{font-size:clamp(19px,2.1vw,25px);color:#354052}
.cta{display:inline-flex;min-height:50px;align-items:center;padding:0 22px;
border-radius:999px;color:white;background:var(--accent);font-weight:800;
text-decoration:none;margin-top:12px}.creative{font-size:12px;color:var(--muted);
margin-top:8px}figure{margin:0;background:white;border:1px solid var(--line);
border-radius:28px;padding:16px;box-shadow:0 18px 60px #25145a1a}
figure img{display:block;width:100%;height:auto;max-height:72vh;object-fit:contain}
figcaption{font-size:14px;color:var(--muted);padding:12px 4px 2px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:22px;padding:16px 0 58px}
.card{background:white;border:1px solid var(--line);border-radius:22px;padding:24px}
.card.wide{grid-column:1/-1}.steps{padding-left:1.35em}.steps li{margin:.8em 0}
.truth{background:var(--soft)}footer{border-top:1px solid var(--line);
padding:24px 0 42px;color:var(--muted);font-size:14px}
@media(max-width:760px){.hero,.grid{grid-template-columns:1fr}.hero{padding-top:25px}
.hero figure{order:2}.card.wide{grid-column:auto}h1{font-size:40px}}
""".strip()


def render_page(record: dict[str, Any], site: str = SITE) -> str:
    e = html.escape
    app = record["app"]
    task = record["task"]
    asset = record["asset"]
    marker = (
        TREATMENT_MARKER
        if record["arm"] == "treatment"
        else HOLDOUT_MARKER
    )
    schema = json.dumps(
        _schema(record, site),
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")
    alt = (
        f"{app['name']} {asset['screen_description']} for "
        f"{task['image_context']}"
    )
    caption = (
        f"Authentic {asset['locale']} App Store screenshot of "
        f"{app['name']}: {asset['screen_description']}. "
        "No simulated UI, review, or result is added."
    )
    direct_answer = (
        f"Use the real {app['name']} workflow shown here: "
        f"{task['result']}"
    )
    steps = "".join(f"<li>{e(step)}</li>" for step in task["steps"])
    home_link = (
        f'<a class="brand" href="{e(site)}/">iOS App Guide</a>'
        if record["arm"] == "treatment"
        else '<span class="brand">iOS App Guide</span>'
    )
    return f"""<!doctype html>
<html lang="en-US">
<head>
{MANAGED_MARKER}
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(task["title"])} · {e(app["name"])}</title>
<meta name="description" content="{e(task["problem"], quote=True)}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">
{marker}
<meta name="iag-experiment-id" content="{e(record["experiment_id"], quote=True)}">
<meta name="iag-creative-id" content="{e(record["creative_id"], quote=True)}">
<link rel="canonical" href="{e(record["page_url"], quote=True)}">
<link rel="image_src" href="{e(record["image_url"], quote=True)}">
<meta property="og:type" content="article">
<meta property="og:title" content="{e(task["title"], quote=True)}">
<meta property="og:description" content="{e(task["problem"], quote=True)}">
<meta property="og:url" content="{e(record["page_url"], quote=True)}">
<meta property="og:image" content="{e(record["image_url"], quote=True)}">
<meta property="og:image:width" content="{int(asset["width"])}">
<meta property="og:image:height" content="{int(asset["height"])}">
<meta property="og:image:alt" content="{e(alt, quote=True)}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{schema}</script>
<style>{STYLE}</style>
</head>
<body>
<header class="wrap top">{home_link}<span class="crumb">{e(app["category"])}</span></header>
<main class="wrap">
  <section class="hero">
    <div>
      <p class="eyebrow">Real iPhone workflow · {e(app["name"])}</p>
      <h1>{e(task["title"])}</h1>
      <p class="answer">{e(direct_answer)}</p>
      <a id="app-store-cta" class="cta"
         href="{e(record["store_url"], quote=True)}"
         data-channel="google-images"
         data-campaign="{e(app["campaign_token"], quote=True)}"
         data-creative-id="{e(record["creative_id"], quote=True)}"
         rel="noopener">View {e(app["name"])} on the App Store</a>
      <p class="creative">Creative: {e(record["creative_id"])}</p>
    </div>
    <figure>
      <img src="{e(record["image_url"], quote=True)}"
           width="{int(asset["width"])}" height="{int(asset["height"])}"
           alt="{e(alt, quote=True)}" loading="eager" fetchpriority="high"
           decoding="async">
      <figcaption>{e(caption)}</figcaption>
    </figure>
  </section>
  <section class="grid">
    <article class="card">
      <h2>The problem</h2>
      <p>{e(task["problem"])}</p>
    </article>
    <article class="card">
      <h2>The useful result</h2>
      <p>{e(task["result"])}</p>
      <p>{e(app["value_prop"])}</p>
    </article>
    <article class="card wide">
      <h2>A practical three-step flow</h2>
      <ol class="steps">{steps}</ol>
    </article>
    <article class="card wide truth">
      <h2>What this page does not claim</h2>
      <p>{e(app["limitation"])}</p>
      <p>The screenshot is a checksum-pinned, existing {e(asset["locale"])}
      App Store image for {e(app["name"])}. It is not generated UI and this
      page does not invent a testimonial, rating, or outcome.</p>
    </article>
  </section>
</main>
<footer><div class="wrap">Lumi Studio · Real product evidence ·
Measurement window: 6–8 weeks after verified deployment.</div></footer>
</body>
</html>
"""


def render_hub(
    treatment_records: list[dict[str, Any]],
    spec: dict[str, Any] = SPEC,
    site: str = SITE,
    *,
    assignment_digest: str,
    content: dict[str, object],
) -> str:
    cards = "\n".join(
        (
            '<li><a href="'
            + html.escape(record["page_url"], quote=True)
            + '">'
            + html.escape(record["task"]["title"])
            + "</a><span>"
            + html.escape(record["app"]["name"])
            + "</span></li>"
        )
        for record in treatment_records
    )
    return f"""<!doctype html>
<html lang="en-US"><head>
{MANAGED_MARKER}
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Real iPhone task images · Google Images canary</title>
<meta name="description" content="Unique real App Store screenshots randomized with practical, verifiable iPhone task workflows across seven product categories.">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1">
<meta name="iag-experiment-id" content="{html.escape(str(spec["experiment_id"]), quote=True)}">
<meta name="iag-design-digest" content="{assignment_digest}">
<meta name="iag-assignment-digest" content="{assignment_digest}">
<meta name="iag-page-count" content="{content["page_count"]}">
<meta name="iag-page-manifest-digest" content="{content["page_manifest_digest"]}">
<meta name="iag-asset-count" content="{content["asset_count"]}">
<meta name="iag-asset-manifest-digest" content="{content["asset_manifest_digest"]}">
<meta name="iag-ownership-manifest-digest" content="{content["ownership_manifest_digest"]}">
<link rel="canonical" href="{site}/{ROOT_RELATIVE.as_posix()}/">
<style>{STYLE}
ul{{list-style:none;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}}
li{{border:1px solid var(--line);background:white;border-radius:18px;padding:18px;display:grid;gap:5px}}
li a{{font-weight:800}}li span{{color:var(--muted);font-size:14px}}</style>
</head><body><header class="wrap top"><a class="brand" href="{site}/">iOS App Guide</a></header>
<main class="wrap"><section class="hero" style="display:block">
<p class="eyebrow">Google Images canary</p>
<h1>Real screens for real iPhone tasks</h1>
<p class="answer">Every linked page uses a verified, existing App Store screenshot.
Each image belongs to one page and one arm; no generated UI, fake comparison,
or invented review is used.</p></section>
<ul>{cards}</ul></main>
<footer><div class="wrap">Seven App strata · {len(treatment_records)} linked
treatment pages · {len(spec["units"]) - len(treatment_records)} sitemap-only
holdouts measured separately.</div></footer></body></html>
"""


def _render_url_sitemap(urls: Iterable[str]) -> str:
    ET.register_namespace("", SITEMAP_NS)
    root = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    for value in sorted(urls):
        url = ET.SubElement(root, f"{{{SITEMAP_NS}}}url")
        ET.SubElement(url, f"{{{SITEMAP_NS}}}loc").text = value
    ET.indent(root, space="  ")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f"{ET.tostring(root, encoding='unicode')}\n"
    )


def _ledger(
    built_records: list[dict[str, Any]],
    spec: dict[str, Any],
    page_hashes: dict[str, str],
) -> dict[str, Any]:
    assignment_rows = [
        {
            "unit_id": record["unit_id"],
            "creative_id": record["creative_id"],
            "arm": record["arm"],
            "stratum": record["stratum"],
            "assignment_rank": record["assignment_rank"],
            "stratum_size": record["stratum_size"],
            "stratum_treatment_slots": record[
                "stratum_treatment_slots"
            ],
            "page_url": record["page_url"],
            "image_url": record["image_url"],
            "app_key": record["app"]["key"],
            "app_store_id": record["app"]["app_store_id"],
            "category": record["app"]["category"],
            "campaign_token": record["app"]["campaign_token"],
            "asset_id": record["asset"]["id"],
            "source_path": record["asset"]["source_path"],
            "source_locale": record["asset"]["locale"],
            "source_sha256": record["asset"]["sha256"],
            "pixel_sha256": record["asset"]["pixel_sha256"],
            "source_type": record["asset"]["source_type"],
            "width": int(record["asset"]["width"]),
            "height": int(record["asset"]["height"]),
            "page_sha256": page_hashes[str(record["creative_id"])],
        }
        for record in built_records
    ]
    assignment_rows.sort(key=lambda row: str(row["creative_id"]))
    content = content_attestation(assignment_rows)
    immutable_digest = design_digest(spec, assignment_rows)
    return {
        "schema": EXPERIMENT_SCHEMA,
        "digest_schema": DIGEST_SCHEMA,
        "experiment_id": spec["experiment_id"],
        "supersedes_experiment_id": spec["supersedes_experiment_id"],
        "created_at": spec["created_at"],
        "experiment_spec": canonical_value(spec),
        "spec_digest": _digest_json(spec),
        "activation": {
            "status": "pending_deployment",
            "verified_live_at": None,
        },
        "hypothesis": (
            "Internal discovery plus a regular sitemap improves crawl, index, "
            "Google Images impressions, and clicks versus image-sitemap-only "
            "discovery across preregistered unique image-page units."
        ),
        "design": {
            "unit": "unique_image_page",
            "unit_count": len(spec["units"]),
            "asset_ownership": "one image URL belongs to one page and one arm",
            "strata": "app_key",
            "assignment": (
                "preregistered SHA-256 ranked complete randomization "
                "within App strata"
            ),
            "assignment_salt": spec["assignment_salt"],
            "treatment": "linked hub + regular sitemap + image sitemap",
            "holdout": "image sitemap only; no internal inbound link",
            "analysis": (
                "stratified randomization inference with App-stratum "
                "differences weighted by stratum size"
            ),
            "pairing_claim": (
                "none; heterogeneous authentic screenshots are randomized "
                "units, not same-image or pure-page matched pairs"
            ),
            "technical_parity": (
                "Both arms have a standard img, natural alt/caption, "
                "max-image-preview:large, ImageObject, SoftwareApplication, "
                "and the same App×Google Images Apple campaign policy. "
                "Creative heterogeneity is handled by stratification and "
                "randomization inference."
            ),
        },
        "observation_window_days": spec["observation_window_days"],
        "interpretation": {
            "unknown_or_pending_metrics": None,
            "not_indexed": "technical_failure",
            "market_result_requires": (
                "indexed URL and at least 42 completed days after activation"
            ),
            "maximum_window": (
                "freeze the primary read at 56 days; later data is follow-up"
            ),
        },
        "campaign_policy": {
            "scope": "App×channel",
            "channel": "google-images",
            "required_parameters": ["pt", "ct", "mt=8"],
            "creative_dimension": "creative_id (page ID), never ct",
        },
        "qualified_apps": len(spec["apps"]),
        "abstained_apps": [],
        "treatment_urls": sum(
            record["arm"] == "treatment" for record in built_records
        ),
        "holdout_urls": sum(
            record["arm"] == "holdout" for record in built_records
        ),
        "design_digest": immutable_digest,
        "assignment_digest": immutable_digest,
        "content_attestation": content,
        "records": assignment_rows,
    }


def _expected_ledger_rows(
    spec: dict[str, Any],
    site: str,
    page_hashes: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    apps = _apps(spec)
    assignments = stratified_assignment(spec)
    rows = []
    for task in spec["units"]:
        app = apps[str(task["app"])]
        assets = {str(asset["id"]): asset for asset in app["assets"]}
        asset = assets[str(task["asset"])]
        creative_id = str(task["id"])
        assignment = assignments[creative_id]
        rows.append(
            {
                "unit_id": creative_id,
                "creative_id": creative_id,
                "arm": assignment["arm"],
                "stratum": assignment["stratum"],
                "assignment_rank": assignment["assignment_rank"],
                "stratum_size": assignment["stratum_size"],
                "stratum_treatment_slots": assignment[
                    "stratum_treatment_slots"
                ],
                "page_url": (
                    f"{site}/{ROOT_RELATIVE.as_posix()}/{creative_id}.html"
                ),
                "image_url": f"{site}/{asset['public_path']}",
                "app_key": app["key"],
                "app_store_id": app["app_store_id"],
                "category": app["category"],
                "campaign_token": app["campaign_token"],
                "asset_id": asset["id"],
                "source_path": asset["source_path"],
                "source_locale": asset["locale"],
                "source_sha256": asset["sha256"],
                "pixel_sha256": asset["pixel_sha256"],
                "source_type": asset["source_type"],
                "width": int(asset["width"]),
                "height": int(asset["height"]),
                **(
                    {"page_sha256": page_hashes[creative_id]}
                    if page_hashes is not None
                    else {}
                ),
            }
        )
    return sorted(rows, key=lambda row: str(row["creative_id"]))


def _coverage(
    built_records: list[dict[str, Any]],
    spec: dict[str, Any],
) -> dict[str, Any]:
    rows = []
    for app in spec["apps"]:
        app_records = [
            record
            for record in built_records
            if record["app"]["key"] == app["key"]
        ]
        rows.append(
            {
                "app_key": app["key"],
                "app_name": app["name"],
                "category": app["category"],
                "units": len(app_records),
                "treatment_urls": sum(
                    item["arm"] == "treatment" for item in app_records
                ),
                "holdout_urls": sum(
                    item["arm"] == "holdout" for item in app_records
                ),
                "authentic_assets": len(app["assets"]),
                "minimum_asset_width": min(
                    int(asset["width"]) for asset in app["assets"]
                ),
                "campaign_token": app["campaign_token"],
            }
        )
    return {
        "schema": "lumi.google-images-canary-coverage/v1",
        "experiment_id": spec["experiment_id"],
        "qualified": len(spec["apps"]),
        "abstained": 0,
        "abstentions": [],
        "categories": len({app["category"] for app in spec["apps"]}),
        "units": len(spec["units"]),
        "pages": len(built_records),
        "treatment_urls": sum(
            item["arm"] == "treatment" for item in built_records
        ),
        "holdout_urls": sum(
            item["arm"] == "holdout" for item in built_records
        ),
        "authentic_assets": sum(len(app["assets"]) for app in spec["apps"]),
        "requirements": {
            "standard_img": True,
            "natural_alt_and_caption": True,
            "minimum_image_width": MIN_IMAGE_WIDTH,
            "max_image_preview_large": True,
            "image_object": True,
            "software_application": True,
            "image_sitemap": True,
            "complete_apple_campaign_url": True,
            "fake_ui_or_reviews": False,
        },
        "apps": rows,
    }


def render_coverage_markdown(coverage: dict[str, Any]) -> str:
    lines = [
        "# Google Images canary coverage",
        "",
        f"- Experiment: `{coverage['experiment_id']}`",
        f"- Qualified / abstained apps: **{coverage['qualified']} / "
        f"{coverage['abstained']}**",
        f"- Categories: **{coverage['categories']}**",
        f"- Randomized unique assets / pages: **{coverage['units']} / "
        f"{coverage['pages']}**",
        f"- Treatment / sitemap-only holdout: **{coverage['treatment_urls']} / "
        f"{coverage['holdout_urls']}**",
        f"- Checksum-pinned authentic images: **{coverage['authentic_assets']}**",
        "",
        "| Category | App | Units | Treatment | Holdout | Images | Min width | ct |",
        "|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in coverage["apps"]:
        lines.append(
            f"| {row['category']} | {row['app_name']} | {row['units']} | "
            f"{row['treatment_urls']} | {row['holdout_urls']} | "
            f"{row['authentic_assets']} | {row['minimum_asset_width']}px | "
            f"`{row['campaign_token']}` |"
        )
    lines.extend(
        [
            "",
            "Every page has a distinct problem/workflow/result record. Images are "
            "exact copies of pre-existing, checksum-pinned en-US App Store "
            "screenshots; no generated UI, fake before/after, rating, or review "
            "is present.",
            "",
            "Each image URL is owned by exactly one page and one arm. The design "
            "uses preregistered complete randomization within App strata and "
            "stratified randomization inference; it makes no same-image matched-"
            "pair or pure page-treatment claim.",
            "",
            "Unknown and pending observations remain `null`. A URL that is still "
            "not indexed after 42 days is a technical failure, not a market zero.",
            "",
        ]
    )
    return "\n".join(lines)


class _CanaryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.images: list[dict[str, str]] = []
        self.metas: list[dict[str, str]] = []
        self.links: list[dict[str, str]] = []
        self.anchors: list[dict[str, str]] = []
        self.schemas: list[dict[str, Any]] = []
        self._schema = False
        self._schema_parts: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = {
            key.lower(): value or ""
            for key, value in attrs
            if key.lower() not in {"style"}
        }
        tag = tag.lower()
        if tag == "img":
            self.images.append(values)
        elif tag == "meta":
            self.metas.append(values)
        elif tag == "link":
            self.links.append(values)
        elif tag == "a":
            self.anchors.append(values)
        elif (
            tag == "script"
            and values.get("type", "").lower() == "application/ld+json"
        ):
            self._schema = True
            self._schema_parts = []

    def handle_data(self, data: str) -> None:
        if self._schema:
            self._schema_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._schema:
            self._schema = False
            self.schemas.append(json.loads("".join(self._schema_parts)))


def _xml_page_urls(path: Path) -> list[str]:
    root = ET.parse(path).getroot()
    namespace = {"sm": SITEMAP_NS}
    return [
        str(node.text)
        for node in root.findall("sm:url/sm:loc", namespace)
        if node.text
    ]


def _contains_canary_page(path: Path) -> bool:
    marker = b"/google-images-canary/"
    tail = b""
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(65536):
                source = tail + chunk
                if marker in source:
                    return True
                tail = source[-len(marker) :]
    except OSError:
        return False
    return False


def audit_generated(
    pages: Path = PAGES,
    site: str = SITE,
    spec: dict[str, Any] = SPEC,
    ledger_path: Path | None = None,
) -> dict[str, int]:
    expected = validate_spec(spec)
    verify_live_apps(pages, spec)
    apps = _apps(spec)
    all_assets = {
        str(asset["id"]): asset
        for app in spec["apps"]
        for asset in app["assets"]
    }
    for asset in all_assets.values():
        verify_asset(pages, asset)

    ledger_path = ledger_path or (REPORTS / LEDGER_NAME)
    try:
        ledger = _json_loads_strict(
            ledger_path.read_text(encoding="utf-8")
        )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid canary ledger: {ledger_path}") from error
    if ledger.get("schema") != EXPERIMENT_SCHEMA:
        raise ValueError("Published canary ledger schema mismatch")
    if ledger.get("digest_schema") != DIGEST_SCHEMA:
        raise ValueError("Published canary digest schema mismatch")
    if ledger.get("experiment_spec") != canonical_value(spec):
        raise ValueError("Published canary experiment spec mismatch")
    if ledger.get("spec_digest") != _digest_json(spec):
        raise ValueError("Published canary spec digest mismatch")
    ledger_records = ledger.get("records")
    if (
        not isinstance(ledger_records, list)
        or len(ledger_records) != expected["pages"]
    ):
        raise ValueError(
            "Published canary ledger must contain every unique asset-page unit"
        )
    if (
        ledger.get("treatment_urls") != expected["treatment"]
        or ledger.get("holdout_urls") != expected["holdout"]
    ):
        raise ValueError("Published canary ledger is not 19/19")

    expected_ledger_rows = _expected_ledger_rows(spec, site)
    for actual, expected_row in zip(ledger_records, expected_ledger_rows):
        if not isinstance(actual, dict):
            raise ValueError("Published canary ledger record is not an object")
        actual_without_page_hash = {
            key: value for key, value in actual.items() if key != "page_sha256"
        }
        if actual_without_page_hash != expected_row:
            raise ValueError(
                "Published canary ledger differs from the frozen design"
            )
        if SHA256_RE.fullmatch(str(actual.get("page_sha256", ""))) is None:
            raise ValueError("Published canary ledger page digest is invalid")
    immutable_digest = design_digest(spec, ledger_records)
    if (
        ledger.get("design_digest") != immutable_digest
        or ledger.get("assignment_digest") != immutable_digest
    ):
        raise ValueError("Published canary assignment digest mismatch")
    expected_content = content_attestation(ledger_records)
    if ledger.get("content_attestation") != expected_content:
        raise ValueError("Published canary content attestation mismatch")
    ledger_by_id = {
        str(record["creative_id"]): record for record in ledger_records
    }
    if len(ledger_by_id) != expected["pages"]:
        raise ValueError("Published canary ledger has duplicate creative IDs")
    campaign_by_app: dict[str, set[str]] = {}
    page_urls: set[str] = set()
    image_pairs: list[tuple[str, str]] = []
    image_owners: dict[str, tuple[str, str]] = {}
    for creative_id, record in sorted(ledger_by_id.items()):
        _check_cancelled()
        page = pages / ROOT_RELATIVE / f"{creative_id}.html"
        page_payload = page.read_bytes()
        if _digest_bytes(page_payload) != record["page_sha256"]:
            raise ValueError(f"{page} content digest mismatch")
        source = page_payload.decode("utf-8")
        parser = _CanaryParser()
        parser.feed(source)
        if len(parser.images) != 1:
            raise ValueError(f"{page} must contain exactly one standard img")
        image = parser.images[0]
        if not image.get("src") or not image.get("alt"):
            raise ValueError(f"{page} has an incomplete standard img")
        if image["src"] != record["image_url"]:
            raise ValueError(f"{page} does not own its ledger image URL")
        if int(image.get("width", "0")) < MIN_IMAGE_WIDTH:
            raise ValueError(f"{page} image is below {MIN_IMAGE_WIDTH}px")
        robots = [
            meta.get("content", "")
            for meta in parser.metas
            if meta.get("name", "").casefold() == "robots"
        ]
        if len(robots) != 1 or "max-image-preview:large" not in robots[0]:
            raise ValueError(f"{page} lacks max-image-preview:large")
        arm_values = [
            meta.get("content")
            for meta in parser.metas
            if meta.get("name") == "iag-experiment-arm"
        ]
        expected_arm_meta = (
            "treatment"
            if record["arm"] == "treatment"
            else "sitemap-only-holdout"
        )
        if arm_values != [expected_arm_meta]:
            raise ValueError(f"{page} experiment arm marker mismatch")
        schema_types = {
            item.get("@type")
            for schema in parser.schemas
            for item in schema.get("@graph", [])
            if isinstance(item, dict)
        }
        if not {"ImageObject", "SoftwareApplication"}.issubset(schema_types):
            raise ValueError(f"{page} lacks required image/app schema")
        ctas = [
            anchor
            for anchor in parser.anchors
            if anchor.get("id") == "app-store-cta"
        ]
        if len(ctas) != 1:
            raise ValueError(f"{page} must contain exactly one App Store CTA")
        cta = ctas[0]
        app = apps[str(record["app_key"])]
        validated_app_store_url(
            cta.get("href", ""),
            expected_app_id=str(app["app_store_id"]),
        )
        query = urllib.parse.parse_qs(
            urllib.parse.urlsplit(cta["href"]).query,
            strict_parsing=True,
        )
        if (
            set(query) != {"pt", "ct", "mt"}
            or query.get("ct") != [app["campaign_token"]]
            or query.get("mt") != ["8"]
            or not query.get("pt", [""])[0].isdigit()
        ):
            raise ValueError(f"{page} has an incomplete App Store campaign URL")
        if cta.get("data-creative-id") != creative_id:
            raise ValueError(f"{page} does not expose creative page ID")
        campaign_by_app.setdefault(str(record["app_key"]), set()).add(
            query["ct"][0]
        )
        page_urls.add(str(record["page_url"]))
        owner = (str(record["page_url"]), str(record["arm"]))
        if str(record["image_url"]) in image_owners:
            raise ValueError("Canary image URL is shared across pages or arms")
        image_owners[str(record["image_url"])] = owner
        image_pairs.append((str(record["page_url"]), str(record["image_url"])))

    if any(len(tokens) != 1 for tokens in campaign_by_app.values()):
        raise ValueError("Canary ct is fragmented below App×channel")
    if len(image_owners) != len(ledger_records):
        raise ValueError("Canary image ownership is not one-to-one")
    treatment_urls = {
        str(record["page_url"])
        for record in ledger_records
        if record["arm"] == "treatment"
    }
    holdout_urls = page_urls - treatment_urls
    treatment_sitemap = set(
        _xml_page_urls(pages / TREATMENT_SITEMAP_RELATIVE)
    )
    image_sitemap = set(_xml_page_urls(pages / IMAGE_SITEMAP_RELATIVE))
    if treatment_sitemap != treatment_urls:
        raise ValueError("Treatment sitemap does not match the ledger")
    if image_sitemap != page_urls:
        raise ValueError("Image sitemap does not cover every canary URL")
    for sitemap in pages.glob("sitemap*.xml"):
        if sitemap == pages / IMAGE_SITEMAP_RELATIVE:
            continue
        if not _contains_canary_page(sitemap):
            continue
        leaked = holdout_urls & set(_xml_page_urls(sitemap))
        if leaked:
            raise ValueError(
                f"Canary holdout leaked into non-image sitemap {sitemap.name}: "
                f"{len(leaked)} URL(s)"
            )

    hub = (pages / ROOT_RELATIVE / "index.html").read_text(encoding="utf-8")
    hub_parser = _CanaryParser()
    hub_parser.feed(hub)
    hub_values: dict[str, list[str]] = {}
    for meta in hub_parser.metas:
        name = meta.get("name", "")
        if name.startswith("iag-"):
            hub_values.setdefault(name, []).append(meta.get("content", ""))
    expected_hub_values = {
        "iag-experiment-id": [str(spec["experiment_id"])],
        "iag-design-digest": [immutable_digest],
        "iag-assignment-digest": [immutable_digest],
        "iag-page-count": [str(expected_content["page_count"])],
        "iag-page-manifest-digest": [
            str(expected_content["page_manifest_digest"])
        ],
        "iag-asset-count": [str(expected_content["asset_count"])],
        "iag-asset-manifest-digest": [
            str(expected_content["asset_manifest_digest"])
        ],
        "iag-ownership-manifest-digest": [
            str(expected_content["ownership_manifest_digest"])
        ],
    }
    if any(
        hub_values.get(name) != value
        for name, value in expected_hub_values.items()
    ):
        raise ValueError("Canary hub design attestation mismatch")
    hub_links = {
        anchor["href"]
        for anchor in hub_parser.anchors
        if anchor.get("href", "").startswith(f"{site}/{ROOT_RELATIVE}/")
    }
    if hub_links != treatment_urls:
        raise ValueError("Canary hub must link treatment and no holdout URLs")
    if hub_links & holdout_urls:
        raise ValueError("Canary holdout leaked into the linked hub")
    if gen_image_sitemap.render(sorted(image_pairs)) != (
        pages / IMAGE_SITEMAP_RELATIVE
    ).read_text(encoding="utf-8"):
        raise ValueError("Canary image sitemap is not deterministic")
    return expected


def _remove_stale_pages(
    pages: Path,
    expected: set[Path],
    *,
    check: bool,
) -> int:
    root = pages / ROOT_RELATIVE
    if not root.is_dir():
        return 0
    stale = []
    for path in root.glob("*.html"):
        if path in expected:
            continue
        try:
            source = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if MANAGED_MARKER in source or LEGACY_MANAGED_MARKER in source:
            stale.append(path)
    if stale and check:
        raise ValueError(
            "Stale managed canary pages: "
            + ", ".join(path.name for path in stale[:8])
        )
    for path in stale:
        path.unlink()
    return len(stale)


def build(
    pages: Path = PAGES,
    site: str = SITE,
    *,
    provider_token: str,
    spec: dict[str, Any] = SPEC,
    reports: Path = REPORTS,
    check: bool = False,
) -> dict[str, int]:
    validate_spec(spec)
    verify_live_apps(pages, spec)
    for app in spec["apps"]:
        for asset in app["assets"]:
            verify_asset(pages, asset)
    built_records = records(spec, site, provider_token=provider_token)
    expected_paths: set[Path] = set()
    outputs: dict[Path, str] = {}
    for record in built_records:
        _check_cancelled()
        path = pages / str(record["page_relative"])
        expected_paths.add(path)
        outputs[path] = render_page(record, site)
    page_hashes = {
        str(record["creative_id"]): _digest_bytes(
            outputs[pages / str(record["page_relative"])].encode("utf-8")
        )
        for record in built_records
    }
    ledger = _ledger(built_records, spec, page_hashes)
    treatment = [
        record for record in built_records if record["arm"] == "treatment"
    ]
    expected_paths.add(pages / ROOT_RELATIVE / "index.html")
    outputs[pages / ROOT_RELATIVE / "index.html"] = render_hub(
        treatment,
        spec,
        site,
        assignment_digest=str(ledger["assignment_digest"]),
        content=ledger["content_attestation"],
    )
    outputs[pages / IMAGE_SITEMAP_RELATIVE] = gen_image_sitemap.render(
        [(record["page_url"], record["image_url"]) for record in built_records]
    )
    outputs[pages / TREATMENT_SITEMAP_RELATIVE] = _render_url_sitemap(
        record["page_url"] for record in treatment
    )
    outputs[reports / LEDGER_NAME] = (
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n"
    )
    coverage = _coverage(built_records, spec)
    outputs[reports / COVERAGE_JSON] = (
        json.dumps(coverage, ensure_ascii=False, indent=2) + "\n"
    )
    outputs[reports / COVERAGE_MD] = render_coverage_markdown(coverage)

    changed = 0
    for path, content in sorted(outputs.items(), key=lambda item: str(item[0])):
        _check_cancelled()
        if check:
            try:
                existing = path.read_text(encoding="utf-8")
            except OSError as error:
                raise ValueError(f"Missing canary output in check mode: {path}") from error
            if existing != content:
                raise ValueError(f"Stale canary output: {path}")
        else:
            changed += int(write_text_if_changed_atomic(path, content))
    changed += _remove_stale_pages(pages, expected_paths, check=check)
    summary = audit_generated(
        pages,
        site,
        spec,
        ledger_path=reports / LEDGER_NAME,
    )
    return {**summary, "changed_files": changed}


def main() -> None:
    for name in (signal.SIGINT, signal.SIGTERM):
        signal.signal(name, _request_cancel)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=Path, default=PAGES)
    parser.add_argument("--site", default=SITE)
    parser.add_argument("--reports", type=Path, default=REPORTS)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--materialize-assets",
        action="store_true",
        help="Copy exact pinned source screenshots from --source-home.",
    )
    parser.add_argument(
        "--source-home",
        type=Path,
        default=Path.home(),
        help="Root used only by --materialize-assets.",
    )
    args = parser.parse_args()
    validate_spec()
    changed_assets = 0
    if args.materialize_assets:
        changed_assets = materialize_assets(
            args.pages.resolve(),
            args.source_home.resolve(),
        )
    if args.check and not resolve_provider_token():
        result = audit_generated(
            args.pages.resolve(),
            args.site.rstrip("/"),
            ledger_path=args.reports.resolve() / LEDGER_NAME,
        )
        result["changed_files"] = 0
    else:
        result = build(
            args.pages.resolve(),
            args.site.rstrip("/"),
            provider_token=resolve_provider_token(),
            reports=args.reports.resolve(),
            check=args.check,
        )
    print(
        "GOOGLE_IMAGES_CANARY "
        f"qualified={result['apps']} abstained=0 "
        f"treatment={result['treatment']} holdout={result['holdout']} "
        f"pages={result['pages']} assets_changed={changed_assets} "
        f"changed={result['changed_files']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
