#!/usr/bin/env python3
"""Non-interference, accessibility, privacy and inactive-first rollout contracts."""
from __future__ import annotations

import argparse
import html
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request

import owned_email_contract as c

POLICY = c.HERE / "owned_email_rollout.json"
COPY = c.HERE / "owned_email_readiness_i18n.json"
MANIFEST = "data/owned-email/rollout-manifest.json"
VIEWPORTS = ((320, 568), (375, 667), (390, 844), (768, 1024), (1024, 768))
STAGES = {
    "inactive": [], "pilot": ["en-US"],
    "expanded": ["en-US", "zh-Hant", "ja", "ar-SA"], "all": "official_50",
}
CORE = re.compile(r'<header class="oe-core" data-primary-answer="true">.*?</header>', re.S)


def load_policy():
    policy = c.parse_json(POLICY.read_bytes())
    expected = {
        "schema": "lumi.owned-email-rollout-policy/v1", "stage": policy.get("stage"),
        "default_active": False, "app_selection": "all_canonical_47_equally",
        "selection_basis": "predeclared_locale_cohorts_not_conversion_results",
        "bn_newsletter": "information_only_explicit_consent_no_download_claim",
        "sender_enabled": False, "stages": STAGES,
    }
    if policy != expected or policy["stage"] not in STAGES:
        raise c.ContractError("rollout must use inactive-first, equal-App, predeclared locale cohorts")
    return policy


def localized(locale):
    data = c.parse_json(COPY.read_bytes())
    c.require_official_locale_coverage("readiness copy", data)
    if any(
        not isinstance(value, list) or len(value) != 2
        or any(not isinstance(text, str) or not text.strip() for text in value)
        for value in data.values()
    ):
        raise c.ContractError("readiness copy must include native optional/inactive labels")
    return dict(zip(("optional", "inactive"), data[locale]))


def active_locales(policy=None):
    policy = policy or load_policy()
    selected = policy["stages"][policy["stage"]]
    return list(c.OFFICIAL_LOCALES) if selected == "official_50" else selected


def is_active(locale):
    return locale in active_locales()


def rollout():
    policy = load_policy()
    locales = active_locales(policy)
    return {
        "schema": "lumi.owned-email-rollout/v1", "policy_digest": c.digest(policy),
        "stage": policy["stage"], "default_active": False,
        "active_locales": locales, "active_capture_count": 47 * len(locales),
        "per_app_active_count": {key: len(locales) for key in c.roster()["apps"]},
        "sender_enabled": False, "bn_newsletter": policy["bn_newsletter"],
    }


class Elements(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.nodes = []
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))

    def find(self, tag):
        return [(index, attrs) for index, (name, attrs) in enumerate(self.nodes) if name == tag]


def core_digest(source):
    matches = CORE.findall(source)
    if len(matches) != 1:
        raise c.ContractError("capture requires one immutable primary-answer region")
    return c.digest(matches[0].encode())


def legacy_non_interference(before, after):
    from gen_tool_email_capture import BLOCK_RE
    if BLOCK_RE.sub("", before) != BLOCK_RE.sub("", after):
        raise c.ContractError("capture changed existing answers, CTA order or shared layout")
    blocks = BLOCK_RE.findall(after)
    if len(blocks) > 1:
        raise c.ContractError("duplicate capture blocks")
    if blocks:
        elements = Elements(blocks[0])
        if any(tag in {"script", "style", "iframe", "img", "dialog"} for tag, _ in elements.nodes):
            raise c.ContractError("legacy capture cannot add shared CSS, script, tracking or modal UI")
        if re.search(r"position\s*:\s*(?:fixed|sticky)|autofocus", blocks[0], re.I):
            raise c.ContractError("legacy capture is intrusive")
        ids = [attrs["id"] for _, attrs in Elements(after).nodes if attrs.get("id")]
        added_ids = [attrs["id"] for _, attrs in elements.nodes if attrs.get("id")]
        if any(ids.count(value) != 1 for value in added_ids):
            raise c.ContractError("capture IDs conflict with existing shared layout")
    return {"non_capture_sha256": c.digest(BLOCK_RE.sub("", before).encode()), "capture_blocks": len(blocks)}


def inspect_html(row, body, *, active=None):
    source = body.decode("utf-8") if isinstance(body, bytes) else body
    nodes = Elements(source)
    active = is_active(row["locale"]) if active is None else active
    forbidden = {"script", "iframe", "img", "video", "audio", "object", "embed", "dialog", "base"}
    for tag, attrs in nodes.nodes:
        if (
            tag in forbidden or any(key.startswith("on") for key in attrs)
            or "autofocus" in attrs or "ping" in attrs
            or attrs.get("role") in {"dialog", "alertdialog"} or attrs.get("aria-modal") == "true"
            or attrs.get("tabindex", "0") not in {"-1", "0"}
            or tag == "meta" and attrs.get("http-equiv", "").lower() == "refresh"
        ):
            raise c.ContractError("capture must have no JS, tracking, autofocus or interruptive UI")
    if re.search(r"position\s*:\s*(?:fixed|sticky)|(?:localStorage|sessionStorage|sendBeacon)", source, re.I):
        raise c.ContractError("sticky capture and tracking/storage are forbidden")
    slots = [(i, a) for i, (_, a) in enumerate(nodes.nodes) if "data-owned-email-slot" in a]
    if len(slots) != 1:
        raise c.ContractError("exactly one owned capture slot is required")
    primaries = [(i, a) for i, a in nodes.find("a") if a.get("data-primary-app-store-cta") == "true"]
    apple = [(i, a) for i, a in nodes.find("a")
             if "apps.apple.com" in a.get("href", "") or "itunes.apple.com" in a.get("href", "")]
    if row["locale"] == "bn-BD":
        if primaries or apple or row["app_store_url"] is not None or row["conversion_campaign"] != "N/A":
            raise c.ContractError("bn-BD has no store CTA or conversion campaign")
        if "market-availability" not in source:
            raise c.ContractError("bn-BD newsletter must retain the truthful unavailable-market notice")
    elif (
        len(primaries) != 1 or len(apple) != 1
        or primaries[0][1].get("href") != row["app_store_url"]
        or primaries[0][0] >= slots[0][0]
    ):
        raise c.ContractError("primary App Store CTA must precede capture without changing its URL")
    forms = nodes.find("form")
    inputs = nodes.find("input")
    if not active:
        if forms or inputs or nodes.find("button") or nodes.find("details"):
            raise c.ContractError("inactive rollout cannot expose a subscription form or dead control")
        if localized(row["locale"])["inactive"] not in html.unescape(source):
            raise c.ContractError("inactive state needs a native explanation, never implied consent")
    else:
        details = nodes.find("details")
        if len(details) != 1 or "open" in details[0][1] or len(nodes.find("summary")) != 1:
            raise c.ContractError("active capture must be optional, native and collapsed by default")
        if len(forms) != 1 or forms[0][1].get("action") != c.ENDPOINT or forms[0][1].get("method") != "post":
            raise c.ContractError("one explicit Buttondown HTML form is required")
        if forms[0][0] <= slots[0][0] or primaries and forms[0][0] <= primaries[0][0]:
            raise c.ContractError("capture form must follow the primary answer and CTA")
        fields = {attrs.get("name"): attrs for _, attrs in inputs}
        if len(fields) != len(inputs):
            raise c.ContractError("duplicate form fields")
        expected = {"email", "embed"} | {"metadata__" + key for key in c.capture_metadata(row)}
        if set(fields) != expected:
            raise c.ContractError("extra tracking or unscoped form fields")
        consent = fields["metadata__owned_consent"]
        if (
            consent.get("type") != "checkbox" or "required" not in consent
            or "checked" in consent or consent.get("value") != "yes"
            or fields["email"].get("type") != "email" or "required" not in fields["email"]
            or fields["email"].get("value")
        ):
            raise c.ContractError("consent and email cannot be prefilled or bypassed")
        for key, value in c.capture_metadata(row).items():
            if fields["metadata__" + key].get("value") != value:
                raise c.ContractError("consent scope mismatch")
        for _, attrs in inputs:
            if attrs.get("type") != "hidden" and not any(
                label.get("for") == attrs.get("id") for _, label in nodes.find("label")
            ):
                raise c.ContractError("every input needs a native accessible label")
    return {"core_digest": core_digest(source), "active": active, "no_js": True, "no_tracking": True}


def inspect_inventory(inventory, pages):
    core_hashes, active_count = {}, 0
    for row in inventory["rows"]:
        result = inspect_html(row, (Path(pages) / row["capture_path"]).read_bytes())
        core_hashes[row["capture_path"]] = result["core_digest"]
        active_count += result["active"]
    if active_count != rollout()["active_capture_count"]:
        raise c.ContractError("active capture count differs from fair rollout")
    return {
        "capture_count": len(core_hashes), "active_capture_count": active_count,
        "core_digest": c.digest(core_hashes), "non_interference": "PASS",
        "accessibility_structure": "PASS", "privacy": "PASS", "no_js": "PASS",
    }


def prepare_geometry(directory):
    from app_store_storefronts import resolve_provider_token
    from gen_owned_email_capture import render_capture
    directory = Path(directory)
    records, copies = c.rows(resolve_provider_token()), c.load_copy()
    hashes = {"inactive": {}, "active": {}}
    for row in records:
        for mode in hashes:
            body = render_capture(row, copies, active=mode == "active")
            inspect_html(row, body, active=mode == "active")
            target = directory / mode / row["capture_path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            hashes[mode][row["capture_path"]] = c.digest(body)
    fixture = {
        "schema": "lumi.owned-email-geometry-fixtures/v1",
        "source_digest": c.digest(c.source_files()), "rows": records,
        "inactive_hashes": hashes["inactive"], "active_hashes": hashes["active"],
    }
    (directory / "fixtures.json").write_bytes(c.json_bytes(fixture))
    return fixture


def prepare_compatibility(directory, growth, guide):
    from gen_tool_email_capture import BLOCK_RE, _load_config, apply_capture
    directory, growth, guide = Path(directory), Path(growth), Path(guide)
    revisions = {
        name: subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "origin/main"], text=True,
        ).strip()
        for name, repo in (("growth", growth), ("guide", guide))
    }
    app_key, app = max(c.roster()["apps"].items(), key=lambda pair: (len(pair[1]["name"]), pair[0]))
    records = []
    for locale in c.OFFICIAL_LOCALES:
        relative = f"{locale}/{app_key}.html"
        body = subprocess.check_output(["git", "-C", str(guide), "show", f"{revisions['guide']}:{relative}"])
        original = body.decode("utf-8")
        baseline = BLOCK_RE.sub("", original)
        inactive = apply_capture(original, _load_config())
        active = apply_capture(original, _load_config(), preview=True)
        legacy_non_interference(baseline, inactive)
        legacy_non_interference(baseline, active)
        for mode, content in (("main", baseline), ("inactive", inactive), ("active", active)):
            target = directory / mode / f"{locale}.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        records.append({
            "locale": locale, "app_key": app_key, "app_id": app["app_id"],
            "main_path": relative, "main_sha256": c.digest(body), "core_sha256": c.digest(baseline.encode()),
        })
    source_files = {}
    for name in ("publish.py", "hero_task_html.py", "deployment_generation.py"):
        for owner, repo, prefix in (("growth", growth, "geo"), ("guide", guide, "_engine/geo")):
            relative = f"{prefix}/{name}"
            body = subprocess.check_output(["git", "-C", str(repo), "show", f"{revisions[owner]}:{relative}"])
            source_files[f"{owner}/{relative}"] = c.digest(body)
    fixture = {
        "schema": "lumi.owned-email-layout-fixtures/v1", "main_revisions": revisions,
        "source_digest": c.digest(c.source_files()), "shared_feature_merged": False,
        "dependency_files": source_files, "rows": records,
    }
    (directory / "fixtures.json").write_bytes(c.json_bytes(fixture))
    return fixture


def endpoint_health(*, open_url=None, now=None):
    """GET only. A form endpoint may reject GET; that never authorizes a POST probe."""
    from owned_email_readback import _NoRedirect
    opener = open_url or urllib.request.build_opener(_NoRedirect()).open
    results = []
    for url in (c.ENDPOINT, "https://buttondown.com/hourstag/archive/"):
        request = urllib.request.Request(url, method="GET", headers={"User-Agent": "OwnedEmail-Readiness/1"})
        try:
            response = opener(request, timeout=20)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            body = response.read(2 * 1024 * 1024 + 1)
            if len(body) > 2 * 1024 * 1024:
                raise c.ContractError("endpoint health body is oversized")
            results.append({
                "method": "GET", "url": url, "final_url": response.geturl(),
                "http_status": response.code, "allow": response.headers.get("Allow"),
                "location": response.headers.get("Location"),
                "body_sha256": c.digest(body), "observed_at": (now or c.utcnow()).isoformat(),
                "evidence_level": "endpoint_health_only_not_subscription_or_native",
            })
        location = results[-1]["location"]
        if results[-1]["http_status"] in {301, 302, 303, 307, 308} and location in {
            "/hourstag", "/hourstag/", "https://buttondown.com/hourstag", "https://buttondown.com/hourstag/",
        }:
            target = "https://buttondown.com" + location if location.startswith("/") else location
            request = urllib.request.Request(target, method="GET", headers={"User-Agent": "OwnedEmail-Readiness/1"})
            with opener(request, timeout=20) as redirected:
                body = redirected.read(2 * 1024 * 1024 + 1)
                if len(body) > 2 * 1024 * 1024:
                    raise c.ContractError("redirect health body is oversized")
                results[-1]["redirect_get"] = {
                    "method": "GET", "url": target, "final_url": redirected.geturl(),
                    "http_status": redirected.code, "body_sha256": c.digest(body),
                    "observed_at": (now or c.utcnow()).isoformat(),
                }
    return {"schema": "lumi.owned-email-endpoint-health/v1", "results": results,
            "verified_subscribers": 0, "subscriber_total": "UNKNOWN", "native_count": 0, "post_requests": 0}


def validate_geometry(report, inventory):
    if (
        not isinstance(report, dict) or report.get("schema") != "lumi.owned-email-geometry/v1"
        or report.get("source_digest") != c.digest(c.source_files())
        or report.get("viewports") != [list(pair) for pair in VIEWPORTS]
        or set(report.get("locales", [])) != set(c.OFFICIAL_LOCALES)
        or report.get("app_count") != 47 or report.get("cases") != 11750
        or report.get("no_js_cases") != 11750 or report.get("active_preview_cases") != 11750
        or report.get("a11y_cases") != 500 or report.get("cls_cases") != 23500
        or report.get("failures") != [] or report.get("network_requests") != [] or report.get("page_scripts") != 0
        or report.get("max_cls") != 0 or report.get("max_overflow", 999) > 1
        or report.get("rollback_cases") != 11750
        or report.get("playwright_version") != "1.63.0" or report.get("axe_version") != "4.13.0"
        or report.get("browser") != "chromium"
        or not isinstance(report.get("browser_version"), str) or not report["browser_version"]
    ):
        raise c.ContractError("fresh, full five-viewport geometry/a11y/no-JS evidence is required")
    c.fresh(report.get("observed_at"), c.utcnow())
    expected = {(row["app_id"], row["locale"], width): (row, height)
                for row in inventory["rows"] for width, height in VIEWPORTS}
    enabled = set(active_locales())
    records = report.get("rows")
    if not isinstance(records, list) or len(records) != len(expected):
        raise c.ContractError("geometry case evidence is incomplete")
    seen = set()
    for result in records:
        if not isinstance(result, dict):
            raise c.ContractError("invalid geometry case")
        key = (result.get("app_id"), result.get("locale"), result.get("width"))
        if key not in expected or key in seen:
            raise c.ContractError("geometry case identity is duplicated or spoofed")
        seen.add(key)
        row, height = expected[key]
        wanted = report.get("active_hashes" if row["locale"] in enabled else "inactive_hashes", {}).get(row["capture_path"])
        if (
            result.get("height") != height or result.get("app_key") != row["app_key"]
            or result.get("errors") != [] or result.get("no_js") is not True
            or result.get("native_form") is not True or result.get("rollback") is not True
            or result.get("targets_ok") is not True or result.get("cls") != 0
            or not isinstance(result.get("overflow"), (int, float)) or result["overflow"] > 1
            or wanted != row["content_sha256"]
            or result.get("inactive_sha256") != report["inactive_hashes"].get(row["capture_path"])
            or result.get("active_sha256") != report["active_hashes"].get(row["capture_path"])
            or result.get("primary") != result.get("active_primary")
            or result.get("primary") != result.get("rollback_primary")
        ):
            raise c.ContractError("geometry/source/no-JS/rollback evidence mismatch")
        primary = result.get("primary")
        if row["locale"] == "bn-BD":
            if primary is not None:
                raise c.ContractError("bn-BD geometry cannot contain a store CTA")
        elif (
            not isinstance(primary, dict) or primary.get("y", -1) < 0
            or primary.get("bottom", height + 1) > height
            or primary.get("height", 0) < 44 or primary.get("width", 0) < 44
        ):
            raise c.ContractError("primary CTA is not visible/reachable in the first screen")
    audits = report.get("a11y")
    longest = {}
    for row in inventory["rows"]:
        if row["locale"] not in longest or len(row["app_name"]) > len(longest[row["locale"]]["app_name"]):
            longest[row["locale"]] = row
    expected_audits = {
        f"{row['app_id']}/{locale}/{width}/{mode}"
        for locale, row in longest.items() for width, _ in VIEWPORTS for mode in ("inactive", "active")
    }
    if (
        not isinstance(audits, list) or len(audits) != 500
        or any(not isinstance(row, dict) for row in audits)
        or {row.get("key") for row in audits} != expected_audits
        or any(row.get("violations") != [] or row.get("incomplete") != [] for row in audits)
    ):
        raise c.ContractError("accessibility violations or unreviewed results are blocking")
    return report


def release_manifest(inventory, pages, geometry, health, *, dependencies):
    validate_geometry(geometry, inventory)
    static = inspect_inventory(inventory, pages)
    if static["active_capture_count"] != 0:
        raise c.ContractError("this readiness release must remain inactive until activation is authorized")
    if (
        health.get("schema") != "lumi.owned-email-endpoint-health/v1"
        or len(health.get("results", [])) != 2 or health.get("post_requests") != 0
        or health.get("verified_subscribers") != 0 or health.get("subscriber_total") != "UNKNOWN"
        or health.get("native_count") != 0
    ):
        raise c.ContractError("GET-only Buttondown endpoint health is missing")
    for row, url in zip(health["results"], (c.ENDPOINT, "https://buttondown.com/hourstag/archive/")):
        if (
            row.get("method") != "GET" or row.get("url") != url
            or row.get("final_url") != url or type(row.get("http_status")) is not int
            or not isinstance(row.get("body_sha256"), str) or not c.HEX.fullmatch(row["body_sha256"])
            or row.get("evidence_level") != "endpoint_health_only_not_subscription_or_native"
        ):
            raise c.ContractError("invalid endpoint health scope")
        c.fresh(row.get("observed_at"), c.utcnow(), 300)
        redirect = row.get("redirect_get")
        if redirect:
            if (
                redirect.get("method") != "GET"
                or redirect.get("url") not in {"https://buttondown.com/hourstag", "https://buttondown.com/hourstag/"}
                or redirect.get("final_url") != redirect.get("url")
                or redirect.get("http_status") != 200
                or not isinstance(redirect.get("body_sha256"), str) or not c.HEX.fullmatch(redirect["body_sha256"])
            ):
                raise c.ContractError("unsafe endpoint redirect evidence")
            c.fresh(redirect.get("observed_at"), c.utcnow(), 300)
    if (
        not isinstance(dependencies, dict)
        or dependencies.get("schema") != "lumi.owned-email-layout-dependencies/v1"
        or dependencies.get("shared_feature_merged") is not False
        or dependencies.get("non_capture_preserved") is not True
        or not isinstance(dependencies.get("main_revisions"), dict)
        or set(dependencies["main_revisions"]) != {"growth", "guide"}
        or any(not isinstance(value, str) or not c.SHA.fullmatch(value)
               for value in dependencies["main_revisions"].values())
        or dependencies.get("compatibility_cases") != 250
        or dependencies.get("non_interference_failures") != 0
        or dependencies.get("source_digest") != c.digest(c.source_files())
    ):
        raise c.ContractError("shared-layout compatibility/dependency evidence is missing")
    cases = dependencies.get("rows")
    if (
        not isinstance(cases, list) or len(cases) != 250
        or {(row.get("locale"), row.get("width"), row.get("height")) for row in cases}
        != {(locale, width, height) for locale in c.OFFICIAL_LOCALES for width, height in VIEWPORTS}
        or any(row.get("inactive_preserved") is not True for row in cases)
    ):
        raise c.ContractError("shared-layout five-viewport/50-locale evidence is incomplete")
    c.fresh(dependencies.get("observed_at"), c.utcnow())
    root, prefix = c.git_context(str(c.HERE))
    owner = "growth" if prefix == "geo" else "guide"
    current_main = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "origin/main"], text=True,
    ).strip()
    if dependencies["main_revisions"][owner] != current_main:
        raise c.ContractError("shared-layout dependency main advanced; compatibility evidence is stale")
    declared = dependencies.get("dependency_files")
    names = ("publish.py", "hero_task_html.py", "deployment_generation.py")
    keys = {f"{name}/{base}/{file}" for name, base in (("growth", "geo"), ("guide", "_engine/geo")) for file in names}
    if (
        not isinstance(declared, dict) or set(declared) != keys
        or any(not isinstance(value, str) or not c.HEX.fullmatch(value) for value in declared.values())
    ):
        raise c.ContractError("shared-layout dependency digests are missing")
    for name in names:
        relative = f"{prefix}/{name}"
        body = subprocess.check_output(["git", "-C", str(root), "show", f"{current_main}:{relative}"])
        if c.digest(body) != declared[f"{owner}/{relative}"]:
            raise c.ContractError("shared-layout dependency source digest mismatch")
    blockers = [
        "shared_layout_candidate_not_merged_or_authorized; rerun compatibility on its final main SHA",
        "provider_scope_persistence_and_signed_confirmation_pipeline_unverified",
        "no_deployment_or_capture_activation_authorization",
    ]
    if dependencies.get("active_preview_non_interference_failures"):
        blockers.append("active_capture_interferes_with_current_shared_layout; entire_cohort_stays_inactive")
    if dependencies.get("baseline_primary_offscreen"):
        blockers.append("existing_main_primary_CTA_geometry_requires_shared_layout_owner_integration")
    return {
        "schema": "lumi.owned-email-production-readiness/v1",
        "created_at": c.utcnow().isoformat(), "sources": inventory["sources"],
        "inventory_digest": inventory["content_digest"], "rollout": rollout(),
        "gates": static, "geometry_sha256": c.digest(geometry), "endpoint_health": health,
        "dependencies": dependencies, "inactive_release_ready": True, "activation_ready": False,
        "integration_blockers": blockers,
        "rollback": {
            "method": "commit_inactive_policy_then_regenerate_owned_outputs",
            "core_digest_preserved": static["core_digest"], "deletes_consent_records": False,
            "deploys_or_sends": False, "geometry_roundtrip_verified": geometry.get("rollback_cases") == 11750,
        },
        "subscriber_total": "UNKNOWN", "verified_subscribers": 0, "native_count": 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-dir", type=Path)
    parser.add_argument("--geometry", type=Path)
    parser.add_argument("--health", type=Path)
    parser.add_argument("--dependencies", type=Path)
    parser.add_argument("--health-only", action="store_true")
    parser.add_argument("--prepare-geometry", type=Path)
    parser.add_argument("--prepare-compatibility", type=Path)
    parser.add_argument("--growth-root", type=Path)
    parser.add_argument("--guide-root", type=Path)
    args = parser.parse_args(argv)
    if args.prepare_geometry:
        fixture = prepare_geometry(args.prepare_geometry)
        print(f"PASS geometry fixtures={len(fixture['rows'])} active_default=false")
        return 0
    if args.prepare_compatibility:
        if not args.growth_root or not args.guide_root:
            parser.error("compatibility preparation requires both isolated repo roots")
        fixture = prepare_compatibility(args.prepare_compatibility, args.growth_root, args.guide_root)
        print(f"PASS compatibility fixtures={len(fixture['rows'])} shared_feature_merged=false")
        return 0
    if args.health_only:
        print(c.json_bytes(endpoint_health()).decode())
        return 0
    if not all((args.pages_dir, args.geometry, args.health, args.dependencies)):
        parser.error("readiness requires pages, geometry, GET health and dependency evidence")
    from gen_owned_email_capture import check
    inventory = check(args.pages_dir)
    manifest = release_manifest(
        inventory, args.pages_dir, c.parse_json(args.geometry.read_bytes()),
        c.parse_json(args.health.read_bytes()), dependencies=c.parse_json(args.dependencies.read_bytes()),
    )
    target = args.pages_dir / MANIFEST
    target.write_bytes(c.json_bytes(manifest) + b"\n")
    print(f"PASS readiness capture=2350 active={manifest['rollout']['active_capture_count']} "
          "activation=BLOCKED sender=false subscriber=UNKNOWN/0 native=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
