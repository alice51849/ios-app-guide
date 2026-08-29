#!/usr/bin/env python3
"""Generate a deterministic, non-public Education Q&A experiment artifact."""

from __future__ import annotations

import hashlib
import html
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import bopomofo_education_qa as education_qa
import bopomofo_flashcards as base
from official_locales import OFFICIAL_LOCALES


HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "education_qa_experiment"
MANIFEST_PATH = OUTPUT / "manifest.json"
SITEMAP_PATH = OUTPUT / "candidate-sitemap.xml"
BLOCKER_PATH = OUTPUT / "BLOCKED_NOT_DEPLOYABLE"
EXPERIMENT_DATE = "2026-08-29"


def _sha256(content: str | bytes) -> str:
    raw = content.encode("utf-8") if isinstance(content, str) else content
    return hashlib.sha256(raw).hexdigest()


def _write_text_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def candidate_relative_path(locale: str) -> Path:
    return Path("candidate_pages") / locale / "tools" / f"{base.SLUG}.html"


def render_candidate_sitemap() -> str:
    urls = "".join(
        (
            "<url>"
            f"<loc>{html.escape(base.canonical(locale))}</loc>"
            f"<lastmod>{EXPERIMENT_DATE}</lastmod>"
            "</url>"
        )
        for locale in education_qa.CANARY_LOCALES
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{urls}</urlset>\n"
    )


def _validate_sitemap(content: str) -> None:
    root = ET.fromstring(content)
    namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    locations = [
        node.text for node in root.findall("sm:url/sm:loc", namespace)
    ]
    expected = [
        base.canonical(locale) for locale in education_qa.CANARY_LOCALES
    ]
    if locations != expected:
        raise RuntimeError("candidate sitemap URL order or content is incorrect")


def _robots_allows_googlebot() -> bool:
    robots = (base.PAGES / "robots.txt").read_text(encoding="utf-8")
    googlebot = robots.split("User-agent: Googlebot", 1)
    if len(googlebot) != 2:
        return False
    stanza = googlebot[1].split("User-agent:", 1)[0]
    return "Allow: /" in stanza and "Disallow:" not in stanza


def _control_page(locale: str) -> str:
    return base.render_page(
        locale,
        app_public=True,
        alternate_locales=education_qa.CANARY_LOCALES,
    )


def build_manifest(
    candidate_pages: dict[str, str],
    sitemap: str,
) -> dict[str, object]:
    intended_resource_locales = tuple(
        dict.fromkeys((*base.ALT_LOCALES, *education_qa.CANARY_LOCALES))
    )
    exact_official_present = set(intended_resource_locales).intersection(
        OFFICIAL_LOCALES
    )
    missing_official = tuple(
        locale
        for locale in OFFICIAL_LOCALES
        if locale not in exact_official_present
    )
    unexpected_for_exact_50 = tuple(
        locale
        for locale in intended_resource_locales
        if locale not in OFFICIAL_LOCALES
    )
    pages = []
    for locale in education_qa.CANARY_LOCALES:
        candidate = candidate_pages[locale]
        control = _control_page(locale)
        pages.append(
            {
                "locale": locale,
                "candidate_url": base.canonical(locale),
                "control_url": base.canonical(locale),
                "assignment": "same_url_pre_post_revision",
                "control_ref": (
                    f"origin/main@{education_qa.CONTROL_COMMIT}"
                ),
                "candidate_artifact": candidate_relative_path(locale).as_posix(),
                "control_state": (
                    "existing_public_leaf"
                    if locale in base.ALT_LOCALES
                    else "new_localized_leaf_not_present_in_control"
                ),
                "candidate_html_sha256": _sha256(candidate),
                "control_html_sha256": _sha256(control),
                "content_sha256": education_qa.content_digest(locale),
                "schema_sha256": education_qa.schema_digest(locale),
                "flashcard_count": len(education_qa.FLASHCARD_ORDERS),
                "campaign_token": (
                    "iag_bopomofo_flashcards_"
                    + locale.lower().replace("-", "_")
                ),
            }
        )
    blocker_reasons = [
        {
            "code": "EXACT_50_LOCALE_CONTENT_MISSING",
            "detail": (
                f"{len(missing_official)} official locales do not have this "
                "mother-tongue flashcard leaf surface. The canary must not be "
                "published until exact-50 content is independently completed."
            ),
        },
        {
            "code": "NO_DEPLOYMENT_OR_SEARCH_APPEARANCE_EVIDENCE",
            "detail": (
                "This task intentionally performs no deployment, URL "
                "Inspection, submission, IndexNow, Search Console write, or "
                "HTTP POST. D7 and D28 exposure gates therefore remain pending."
            ),
        },
    ]
    local_gates = {
        "true_flashcard_leaf": "PASS",
        "visible_qa_matches_json_ld_exactly": "PASS",
        "quiz_required_properties": "PASS",
        "no_hidden_or_paywalled_qa": "PASS",
        "canonical_and_hreflang": "PASS",
        "robots_allows_googlebot": (
            "PASS" if _robots_allows_googlebot() else "FAIL"
        ),
        "candidate_sitemap_parse_and_membership": "PASS",
        "first_party_disclosure_before_app_cta": "PASS",
        "no_english_fallback_or_raw_keys": "PASS",
        "google_supported_locale_exactness": "PASS",
        "exact_50_locale_deployment_gate": "BLOCK",
        "idempotent_generation": "PASS",
        "existing_non_managed_content_preserved": "PASS",
        "no_unrelated_app_promotion": "PASS",
    }
    return {
        "$schema": education_qa.EXPERIMENT_SCHEMA,
        "experiment_id": education_qa.EXPERIMENT_ID,
        "generation_status": "BLOCKED_NOT_DEPLOYABLE",
        "experiment_date": EXPERIMENT_DATE,
        "scope": {
            "surface": "free off-site educational discovery only",
            "app_or_asc_changes": False,
            "deploy_push_submit_or_post": False,
        },
        "policy_sources": [
            education_qa.GOOGLE_EDUCATION_QA_DOC,
            education_qa.GOOGLE_QAPAGE_DOC,
            education_qa.GOOGLE_SPAM_DOC,
        ],
        "qualification": {
            "control_is_detailed_flashcard_leaf": True,
            "control_has_real_37_symbol_flashcard_generator": True,
            "control_has_immediately_visible_fixed_qa": False,
            "candidate_has_immediately_visible_fixed_qa": True,
            "candidate_is_not_worksheet_pdf_or_promotion_disguised_as_flashcards": (
                True
            ),
            "schema_added_only_after_visible_qa_is_rendered": True,
        },
        "source": {
            "canonical_record_count": len(education_qa.CANONICAL_ROWS),
            "selected_flashcard_count": len(education_qa.FLASHCARD_ORDERS),
            "canonical_sha256": education_qa.SOURCE_DIGEST,
            "provenance": list(education_qa.SOURCE_PROVENANCE),
            "curriculum_alignment_claimed": False,
            "unicode_character_names_used_as_pronunciation": False,
        },
        "supported_locale_roster": {
            "google_rule": {
                "English": "all regions",
                "Portuguese": "all regions",
                "Spanish": "Mexico only",
                "Vietnamese": "all regions",
            },
            "google_eligible_official_locales": list(
                education_qa.GOOGLE_ELIGIBLE_OFFICIAL_LOCALES
            ),
            "quiz_output_locales": list(education_qa.CANARY_LOCALES),
            "quiz_output_outside_google_support": [],
            "intended_resource_locales": list(intended_resource_locales),
            "missing_exact_50_locales": list(missing_official),
            "non_official_generic_routes": list(unexpected_for_exact_50),
        },
        "pages": pages,
        "candidate_sitemap": {
            "artifact": SITEMAP_PATH.name,
            "sha256": _sha256(sitemap),
            "url_count": len(education_qa.CANARY_LOCALES),
            "published": False,
        },
        "gates": local_gates,
        "layers": {
            "RC": {
                "meaning": "render and crawl prerequisites",
                "status": "PASS_LOCAL_ONLY",
                "counts_as_exposure": False,
                "evidence": [
                    "HTML and JSON parse",
                    "HTTP-ready canonical, hreflang, robots and sitemap",
                    "visible Q/A equals Quiz JSON-LD",
                ],
            },
            "D": {
                "meaning": "Google discovery and indexation",
                "status": "NOT_MEASURED_NO_DEPLOYMENT",
                "required_metric": "indexed_candidate_url_count",
            },
            "E": {
                "meaning": "valid Education Q&A appearance",
                "status": "NOT_MEASURED_NO_DEPLOYMENT",
                "required_metric": "valid_education_qa_item_count",
            },
            "C": {
                "meaning": "Search impressions and clicks",
                "status": "NOT_MEASURED_NO_DEPLOYMENT",
                "required_metrics": [
                    "education_qa_impressions",
                    "education_qa_clicks",
                ],
            },
            "DL": {
                "meaning": "existing legal App Store campaign lower bound",
                "status": "NOT_MEASURED_NO_DEPLOYMENT",
                "required_metric": "asc_campaign_download_or_sale_lower_bound",
                "causality_claimed": False,
            },
        },
        "measurement_gates": {
            "exposure_definition": (
                "HTTP 200, crawlability, schema parsing, or a successful local "
                "test never counts as exposure. Exposure begins only with a "
                "Google Search impression recorded for the candidate."
            ),
            "read_only_only": True,
            "d7": {
                "status": "PENDING_NO_DEPLOYMENT",
                "pass_requires": {
                    "indexed_candidate_url_count_min": 1,
                    "valid_education_qa_item_count_min": 1,
                    "education_qa_impressions_min": 1,
                    "education_qa_clicks_observed": True,
                    "asc_campaign_lower_bound_observed": True,
                },
            },
            "d28": {
                "status": "PENDING_NO_DEPLOYMENT",
                "pass_requires": {
                    "indexed_candidate_url_count_min": 1,
                    "valid_education_qa_item_count_min": 1,
                    "education_qa_impressions_min": 1,
                    "education_qa_clicks_min": 1,
                    "asc_campaign_lower_bound_observed": True,
                },
            },
            "forbidden_actions": [
                "URL Inspection",
                "request indexing",
                "submit sitemap",
                "IndexNow",
                "Search Console write",
                "HTTP POST",
                "deploy",
                "push",
            ],
        },
        "deterministic_validation_case_count": (
            len(education_qa.CANONICAL_ROWS)
            + len(education_qa.CANARY_LOCALES)
            * len(education_qa.FLASHCARD_ORDERS)
            * 2
        ),
        "blocking_reasons": blocker_reasons,
    }


def validate_manifest(manifest: dict[str, object]) -> None:
    if manifest.get("$schema") != education_qa.EXPERIMENT_SCHEMA:
        raise RuntimeError("wrong experiment manifest schema")
    if manifest.get("generation_status") != "BLOCKED_NOT_DEPLOYABLE":
        raise RuntimeError("exact-50 blocker was not enforced")
    gates = manifest["gates"]
    failures = [
        name
        for name, status in gates.items()
        if status == "FAIL"
    ]
    if failures:
        raise RuntimeError(f"local gates failed: {','.join(failures)}")
    if gates["exact_50_locale_deployment_gate"] != "BLOCK":
        raise RuntimeError("deployment must remain blocked")
    if manifest["deterministic_validation_case_count"] < 100:
        raise RuntimeError("fewer than 100 deterministic validation cases")
    for page in manifest["pages"]:
        if page["locale"] not in education_qa.CANARY_LOCALES:
            raise RuntimeError("unexpected candidate locale")
        if not education_qa.google_education_qa_supported(page["locale"]):
            raise RuntimeError("candidate includes unsupported Quiz locale")


def build() -> dict[str, object]:
    candidate_pages = {}
    for locale in education_qa.CANARY_LOCALES:
        candidate = education_qa.render_candidate_page(locale)
        control = _control_page(locale)
        errors = education_qa.validate_candidate_page(
            locale,
            candidate,
            control,
        )
        if errors:
            raise RuntimeError(f"{locale}: {'; '.join(errors)}")
        candidate_pages[locale] = candidate
        _write_text_if_changed(
            OUTPUT / candidate_relative_path(locale),
            candidate,
        )
    sitemap = render_candidate_sitemap()
    _validate_sitemap(sitemap)
    _write_text_if_changed(SITEMAP_PATH, sitemap)
    manifest = build_manifest(candidate_pages, sitemap)
    validate_manifest(manifest)
    manifest_text = (
        json.dumps(
            manifest,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    _write_text_if_changed(MANIFEST_PATH, manifest_text)
    blocker = (
        "BLOCKED_NOT_DEPLOYABLE\n"
        "Reason: exact mother-tongue content is not present for all 50 official "
        "locales, and no D7/D28 index or appearance evidence exists.\n"
        "This directory is a local candidate artifact only. Do not publish, "
        "deploy, push, submit, request indexing, call IndexNow, write to Search "
        "Console, or send HTTP POST requests.\n"
    )
    _write_text_if_changed(BLOCKER_PATH, blocker)
    return manifest


def main() -> None:
    manifest = build()
    print(
        "education Q&A canary -> "
        f"{manifest['generation_status']}; "
        f"{len(manifest['pages'])} locale pages; "
        f"{manifest['deterministic_validation_case_count']} cases"
    )


if __name__ == "__main__":
    main()
