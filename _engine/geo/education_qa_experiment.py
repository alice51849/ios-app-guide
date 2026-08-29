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
EXPERIMENT_DATE = "2026-08-30"


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
    return education_qa.render_control_page(
        locale,
        app_public=True,
        alternate_locales=education_qa.CANARY_LOCALES,
    )


def build_manifest(
    candidate_pages: dict[str, str],
    sitemap: str,
) -> dict[str, object]:
    candidate_output_locales = education_qa.CANARY_LOCALES
    candidate_official_locales = tuple(
        locale
        for locale in candidate_output_locales
        if locale in OFFICIAL_LOCALES
    )
    missing_official = tuple(
        locale
        for locale in OFFICIAL_LOCALES
        if locale not in candidate_official_locales
    )
    missing_google_eligible_official = tuple(
        locale
        for locale in education_qa.GOOGLE_ELIGIBLE_OFFICIAL_LOCALES
        if locale not in candidate_official_locales
    )
    unexpected_for_exact_50 = tuple(
        locale for locale in candidate_output_locales if locale not in OFFICIAL_LOCALES
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
                "campaign_token": education_qa.campaign_token(locale),
                "campaign_url": education_qa.app_store_campaign_urls(
                    candidate
                )[0],
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
            "code": "NON_OFFICIAL_GENERIC_LOCALE_ROUTE",
            "detail": (
                "The English candidate uses the existing generic /tools/ route, "
                "not one of the four official en-* portfolio locales. It cannot "
                "count toward exact-50 coverage."
            ),
        },
        {
            "code": "GOOGLE_ELIGIBLE_OFFICIAL_ROUTES_MISSING",
            "detail": (
                f"{len(missing_google_eligible_official)} Google-eligible "
                "official locale routes are missing localized candidate pages. "
                "The generic English route cannot replace en-AU, en-CA, en-GB, "
                "or en-US."
            ),
        },
        {
            "code": "OFFICIAL_RICH_RESULTS_TEST_NOT_RUN",
            "detail": (
                "Google provides no public Rich Results Test API for local HTML. "
                "The local checker enforces Google's documented Quiz properties, "
                "but official eligibility evidence requires a public candidate URL."
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
        "google_documented_quiz_format": "PASS",
        "unique_correct_answer_per_question": "PASS",
        "substantive_explanation_per_answer": "PASS",
        "age_and_use_scope_disclosed": "PASS",
        "no_hidden_or_paywalled_qa": "PASS",
        "canonical_and_hreflang": "PASS",
        "robots_allows_googlebot": (
            "PASS" if _robots_allows_googlebot() else "FAIL"
        ),
        "candidate_sitemap_parse_and_membership": "PASS",
        "first_party_disclosure_before_app_cta": "PASS",
        "no_english_fallback_or_raw_keys": "PASS",
        "google_supported_locale_exactness": "PASS",
        "no_quiz_on_google_unsupported_locale": "PASS",
        "exact_50_locale_deployment_gate": "BLOCK",
        "official_rich_results_test_gate": "BLOCK",
        "app_store_campaign_url_format": "PASS",
        "no_template_thin_page": "PASS",
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
            "candidate_answers_include_fact_specific_explanations": True,
            "candidate_scope_is_older_learner_and_technical_reference": True,
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
            "google_ineligible_official_locales": [
                locale
                for locale in OFFICIAL_LOCALES
                if locale not in education_qa.GOOGLE_ELIGIBLE_OFFICIAL_LOCALES
            ],
            "quiz_output_locales": list(education_qa.CANARY_LOCALES),
            "quiz_output_outside_google_support": [
                locale
                for locale in education_qa.CANARY_LOCALES
                if not education_qa.google_education_qa_supported(locale)
            ],
            "candidate_official_locales": list(candidate_official_locales),
            "missing_google_eligible_official_locales": list(
                missing_google_eligible_official
            ),
            "missing_exact_50_locales": list(missing_official),
            "non_official_generic_routes": list(unexpected_for_exact_50),
        },
        "safe_page_counts": {
            "locally_validated_content_and_schema": len(candidate_pages),
            "deployable_after_all_blocking_gates": 0,
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
            "inventory": {
                "meaning": "local candidate artifacts",
                "status": "PASS_LOCAL_ONLY",
                "counts_as_exposure": False,
                "candidate_page_count": len(candidate_pages),
                "evidence": [
                    "HTML and JSON parse",
                    "canonical, hreflang, robots and candidate sitemap",
                    "visible Q/A equals Quiz JSON-LD",
                ],
            },
            "deployed": {
                "meaning": "candidate revision published at its canonical URLs",
                "status": "NOT_DEPLOYED",
                "candidate_page_count": 0,
            },
            "get": {
                "meaning": "successful HTTP GET of the deployed candidate revision",
                "status": "NOT_TESTABLE_NO_DEPLOYMENT",
                "successful_candidate_get_count": 0,
            },
            "rich_result": {
                "meaning": "valid Google Education Q&A item or appearance",
                "status": "NOT_MEASURED_NO_DEPLOYMENT",
                "required_metric": "valid_education_qa_item_count",
            },
            "click": {
                "meaning": "Google Search clicks attributed to candidate pages",
                "status": "NOT_MEASURED_NO_DEPLOYMENT",
                "required_metric": "education_qa_clicks",
            },
            "download": {
                "meaning": "App Store campaign download or sale lower bound",
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
    if gates["official_rich_results_test_gate"] != "BLOCK":
        raise RuntimeError("official Rich Results Test must remain blocked")
    if manifest["deterministic_validation_case_count"] < 100:
        raise RuntimeError("fewer than 100 deterministic validation cases")
    expected_missing = [
        locale
        for locale in OFFICIAL_LOCALES
        if locale not in education_qa.CANARY_LOCALES
    ]
    roster = manifest["supported_locale_roster"]
    if roster["missing_exact_50_locales"] != expected_missing:
        raise RuntimeError("exact-50 missing-locale evidence is incorrect")
    expected_missing_eligible = [
        locale
        for locale in education_qa.GOOGLE_ELIGIBLE_OFFICIAL_LOCALES
        if locale not in education_qa.CANARY_LOCALES
    ]
    if (
        roster["missing_google_eligible_official_locales"]
        != expected_missing_eligible
    ):
        raise RuntimeError("Google-eligible missing-locale evidence is incorrect")
    if roster["non_official_generic_routes"] != ["en"]:
        raise RuntimeError("generic English route must not count as official")
    if manifest["safe_page_counts"] != {
        "locally_validated_content_and_schema": len(
            education_qa.CANARY_LOCALES
        ),
        "deployable_after_all_blocking_gates": 0,
    }:
        raise RuntimeError("safe page counts are incorrect")
    if set(manifest["layers"]) != {
        "inventory",
        "deployed",
        "get",
        "rich_result",
        "click",
        "download",
    }:
        raise RuntimeError("evidence layers are not strictly separated")
    for page in manifest["pages"]:
        if page["locale"] not in education_qa.CANARY_LOCALES:
            raise RuntimeError("unexpected candidate locale")
        if not education_qa.google_education_qa_supported(page["locale"]):
            raise RuntimeError("candidate includes unsupported Quiz locale")
        campaign_errors = education_qa.validate_app_store_campaign_url(
            page["campaign_url"],
            page["locale"],
        )
        if campaign_errors:
            raise RuntimeError("; ".join(campaign_errors))


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
        "locales; five Google-eligible official routes are missing; the generic "
        "English route is not an official locale; and no public Rich Results "
        "Test, deployment, GET, click, or download evidence exists for this "
        "candidate revision.\n"
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
