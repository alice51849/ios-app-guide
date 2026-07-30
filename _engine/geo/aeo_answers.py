#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate English AEO/GEO answer pages for the promo site.

Writes only:
- geo/pages/answers/<slug>.html
- geo/pages/answers/index.html

Never performs git operations.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
PAGES_ROOT = Path(
    os.environ.get("GEO_PAGES", ROOT / "pages")
).resolve()
ANSWERS_DIR = PAGES_ROOT / "answers"
SITE = "https://alice51849.github.io/ios-app-guide"
MODEL = "gpt-4o-mini"
OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"

sys.path.insert(0, str(ROOT / ".." / "social"))
from videogen.registry import APPS, APPSTORE, appstore_url  # noqa: E402
from appstore_live import live_app_keys  # noqa: E402
import queries  # noqa: E402
import answer_facts  # noqa: E402
import sync_standard_site  # noqa: E402
from answer_text import concise_meta  # noqa: E402
from aeo_pages import alternative_hub_slug  # noqa: E402

TEMPLATE = ANSWERS_DIR / "best-offline-document-scanner-app-for-iphone.html"
FREE_RESOURCE_FIRST_META = (
    '<meta name="iag-free-resource-first" content="true">'
)

# Commercial focus first, then share-of-voice within each tier. Every public app
# remains eligible; this only prevents the daily limit from being spent on the
# least valuable broad-market queries before proven/narrow segments.
OUTREACH_TIER = {
    "lumibopomofo": 0,
    "lumibopomofopro": 0,
    "snapport": 1,
    "lumiletterspro": 1,
    "lumimathpro": 1,
    "lumimissionpro": 1,
    "gmoney": 1,
    "hourstag": 1,
    "aim990": 2,
    "mochi": 2,
    "scanto": 2,
    "cyca": 2,
    "cvdesk": 2,
    "lockhour": 2,
    "unblurry": 2,
}


def slugify(question: str) -> str:
    s = question.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "answer"


def is_english_answer_question(question: str) -> bool:
    """This promo batch creates English answer pages only."""
    try:
        question.encode("ascii")
    except UnicodeEncodeError:
        return False
    slug = slugify(question)
    return slug not in {"app", "answer"} and len(slug) >= 8


def read_key() -> str:
    key_path = Path(os.path.expanduser("~/.openai_key"))
    return key_path.read_text(encoding="utf-8").strip()


def key_available() -> bool:
    try:
        return bool(read_key())
    except Exception:  # noqa: BLE001
        return False


def extract_style(pages_root: Path | None = None) -> str:
    if pages_root is None:
        answers_dir = ANSWERS_DIR
        template = TEMPLATE
        fallback_dir = PAGES_ROOT / "answers"
    else:
        answers_dir = pages_root.resolve() / "answers"
        template = answers_dir / "best-offline-document-scanner-app-for-iphone.html"
        fallback_dir = answers_dir
    candidates = [template, *sorted(answers_dir.glob("*.html"))]
    if fallback_dir != answers_dir:
        candidates.extend(
            [
                fallback_dir
                / "best-offline-document-scanner-app-for-iphone.html",
                *sorted(fallback_dir.glob("*.html")),
            ]
        )
    for candidate in candidates:
        if not candidate.exists():
            continue
        text = candidate.read_text(encoding="utf-8")
        m = re.search(r"<style\b[^>]*>\s*(.*?)\s*</style>", text, re.S)
        if m:
            return m.group(1)
    raise RuntimeError(
        f"Could not extract template CSS from any answer page: {answers_dir}"
    )


def safe_text(value: Any, default: str = "") -> str:
    if not isinstance(value, str):
        return default
    return " ".join(value.strip().split())


def safe_list(value: Any, limit: int, default: list[str]) -> list[str]:
    if not isinstance(value, list):
        return default[:limit]
    out: list[str] = []
    for item in value:
        if isinstance(item, str):
            t = safe_text(item)
            if t:
                out.append(t)
        elif isinstance(item, dict):
            q = safe_text(item.get("q"))
            a = safe_text(item.get("a"))
            if q and a:
                out.append({"q": q, "a": a})  # type: ignore[arg-type]
        if len(out) >= limit:
            break
    return out or default[:limit]


def app_truth_notes(key: str, app: dict[str, Any]) -> list[str]:
    notes = [
        "Do not mention ratings, download counts, awards, or unsupported claims.",
        "Say users should verify current App Store pricing and features before purchase.",
    ]
    tag = app.get("tag", "")
    bullets = ", ".join(app.get("cta_bullets", []))
    if key == "aim990":
        notes.extend([
            "Aim990 has a one-time unlock and no subscription.",
            "Never promise or guarantee a TOEIC score or improvement.",
            "TOEIC is a registered trademark of ETS. Aim990 is an independent study aid, not affiliated with or endorsed by ETS.",
        ])
    elif "No subscription" in bullets or "No subscription" in tag or "Pay once" in bullets or "Pay once" in tag:
        notes.append("It is acceptable to describe the app as pay-once/no-subscription when supported by the facts.")
    return notes


def prompt_for(question: str, key: str) -> list[dict[str, str]]:
    app = APPS[key]
    facts = {
        "key": key,
        "name": app["name"],
        "category": app.get("category", "iOS app"),
        "search": app.get("search", ""),
        "tag": app.get("tag", ""),
        "sub": app.get("sub", ""),
        "cta_bullets": app.get("cta_bullets", []),
        "keywords": app.get("keywords", []),
        "app_store_url": appstore_url(key, "iag_ans"),
        "truth_notes": app_truth_notes(key, app),
    }
    system = (
        "You write honest English buyer-intent answer pages for iOS apps. "
        "Return only valid JSON. Avoid hype, guarantees, fabricated metrics, ratings, awards, or unverified claims."
    )
    user = {
        "task": "Generate concise page content for an AEO/GEO answer page.",
        "question": question,
        "required_structure": {
            "meta_description": "150-160 chars, truthful",
            "lead": "one outcome-specific sentence using verified app facts; never describe the page as a generic buying guide",
            "short_answer_paragraphs": "2 paragraphs, total about 130-180 words; start with buying criteria, then recommend the app as a strong option",
            "what_to_look_for": "5 bullets",
            "decision_steps": "5 short steps",
            "where_app_fits": "1 paragraph",
            "faq": "3 Q&A items, concise answers",
        },
        "app_facts": facts,
        "tone": "helpful, practical, transparent, evidence-based, non-hype",
        "output_json_shape": {
            "meta_description": "string",
            "lead": "string",
            "short_answer_paragraphs": ["string", "string"],
            "what_to_look_for": ["string"],
            "decision_steps": ["string"],
            "where_app_fits": "string",
            "faq": [{"q": "string", "a": "string"}],
        },
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
    ]


def call_openai(messages: list[dict[str, str]]) -> dict[str, Any]:
    payload = json.dumps({
        "model": MODEL,
        "messages": messages,
        "temperature": 0.35,
        "response_format": {"type": "json_object"},
    }).encode("utf-8")
    req = urllib.request.Request(
        OPENAI_ENDPOINT,
        data=payload,
        headers={
            "Authorization": f"Bearer {read_key()}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                raw = resp.read().decode("utf-8")
            data = json.loads(raw)
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as exc:
            last_err = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"OpenAI request failed after retries: {last_err}")


def default_content(question: str, key: str) -> dict[str, Any]:
    app = APPS[key]
    name = app["name"]
    outcome = safe_text(app.get("sub")).rstrip(".")
    access = safe_text(app.get("tag")).rstrip(".")
    lead = f"{name} — {outcome}."
    if access:
        lead += f" {access}."
    strengths = ", ".join(app.get("cta_bullets", [])[:3])
    base = {
        "meta_description": f"{question}: what to check before choosing an iPhone app, and where {name} may fit as a practical option.",
        "lead": lead,
        "short_answer_paragraphs": [
            "The best choice depends on your real use case: privacy, offline access, export options, ease of use, and whether the pricing model still makes sense after a few months. Before installing, test the app with a realistic task rather than judging only by screenshots.",
            f"{name} is worth considering if its App Store listing matches your needs. It focuses on {outcome}, and its listed strengths include {strengths}.",
        ],
        "what_to_look_for": [
            "Check whether the core feature works without unnecessary accounts or lock-in.",
            "Verify export, sharing, deletion, and privacy controls before relying on it.",
            "Compare one-time unlocks, subscriptions, and free limits based on your expected use.",
            "Try a realistic sample task before paying for advanced features.",
            "Read the current App Store listing because features and pricing can change.",
        ],
        "decision_steps": [
            "Define the job you need done most often.",
            "Test the app with real content or a realistic scenario.",
            "Check privacy labels and account requirements.",
            "Confirm export and backup options.",
            "Choose the pricing model you are comfortable maintaining.",
        ],
        "comparison_rows": [
            {
                "need": "Pricing model",
                "check": "Check whether useful features require a subscription, a one-time unlock, or neither.",
                "why": "The cheapest app on day one may not be cheapest after a year.",
            },
            {
                "need": "Privacy model",
                "check": "Prefer on-device work when the content is sensitive.",
                "why": "Private documents, resumes, study data, and family content deserve careful handling.",
            },
            {
                "need": "Export / lock-in",
                "check": "Confirm file formats, sharing, backup, and deletion controls.",
                "why": "A good app should help you finish the task, not trap your work.",
            },
        ],
        "sources": [],
        "page_title": "",
        "primary_resource_url": "",
        "primary_resource_label": "",
        "date_modified": "",
        "where_app_fits": (
            f"{name} is a focused option for people who value {strengths}. "
            f"Its core outcome is: {outcome}."
        ),
        "faq": [
            {"q": f"Is {name} a good option?", "a": f"{name} can be a good option if its current App Store features match your needs and budget."},
            {"q": "What should I verify first?", "a": "Check current pricing, privacy labels, export limits, and the exact features included in the version you plan to use."},
            {
                "q": "Who publishes this page?",
                "a": (
                    "This buying guide is published by Lumi Studio, the app "
                    "developer. Verify current App Store details before purchase."
                ),
            },
        ],
    }
    overlay = answer_facts.topic_facts(question, key, app)
    if overlay:
        base.update(overlay)
    return base


def normalized_content(raw: dict[str, Any], question: str, key: str) -> dict[str, Any]:
    base = default_content(question, key)
    content = {
        "meta_description": safe_text(raw.get("meta_description"), base["meta_description"]),
        "lead": safe_text(raw.get("lead"), base["lead"]),
        "short_answer_paragraphs": safe_list(raw.get("short_answer_paragraphs"), 2, base["short_answer_paragraphs"]),
        "what_to_look_for": safe_list(raw.get("what_to_look_for"), 5, base["what_to_look_for"]),
        "decision_steps": safe_list(raw.get("decision_steps"), 5, base["decision_steps"]),
        "comparison_rows": base["comparison_rows"],
        "sources": base["sources"],
        "page_title": safe_text(
            raw.get("page_title"), base.get("page_title", "")
        ),
        "primary_resource_url": safe_text(
            raw.get("primary_resource_url"),
            base.get("primary_resource_url", ""),
        ),
        "primary_resource_label": safe_text(
            raw.get("primary_resource_label"),
            base.get("primary_resource_label", ""),
        ),
        "date_modified": safe_text(
            raw.get("date_modified"),
            base.get("date_modified", ""),
        ),
        "where_app_fits": safe_text(raw.get("where_app_fits"), base["where_app_fits"]),
        "faq": raw.get("faq") if isinstance(raw.get("faq"), list) else base["faq"],
    }
    faqs = []
    for item in content["faq"]:
        if isinstance(item, dict):
            q = safe_text(item.get("q"))
            a = safe_text(item.get("a"))
            if q and a:
                faqs.append({"q": q, "a": a})
        if len(faqs) >= 3:
            break
    content["faq"] = faqs or base["faq"]
    if not content["primary_resource_url"].startswith(f"{SITE}/"):
        content["primary_resource_url"] = ""
        content["primary_resource_label"] = ""
    elif not content["primary_resource_label"]:
        content["primary_resource_label"] = "Open free resource"

    if key == "aim990":
        disclaimer = " TOEIC is a registered trademark of ETS; Aim990 is an independent study aid and is not affiliated with or endorsed by ETS. It does not guarantee any score."
        if "ETS" not in content["where_app_fits"]:
            content["where_app_fits"] = content["where_app_fits"].rstrip(".") + "." + disclaimer
        joined = json.dumps(content, ensure_ascii=False).lower()
        if re.search(
            r"optional subscriptions?|subscription options?|offers? subscriptions?",
            joined,
        ):
            raise ValueError("Unsafe Aim990 optional-subscription claim detected")
    return content


def j(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def e(s: str) -> str:
    return html.escape(s, quote=True)


def author_microformat() -> str:
    return (
        '<data class="p-author h-card vcard" value="Lumi Studio">'
        '<data class="p-name p-org fn org" value="Lumi Studio"></data>'
        f'<data class="u-url url" value="{SITE}/about.html"></data>'
        "</data>"
    )


def url_microformat(url: str, include_uid: bool = True) -> str:
    classes = "u-url u-uid" if include_uid else "u-url"
    return f'<data class="{classes}" value="{e(url)}"></data>'


def _add_classes_to_first_tag(
    document: str,
    pattern: str,
    classes: tuple[str, ...],
    label: str,
) -> str:
    match = re.search(pattern, document, re.IGNORECASE)
    if not match:
        raise ValueError(f"Missing {label} while adding microformats")
    tag = match.group(0)
    class_match = re.search(
        r"(\sclass=)([\"'])(.*?)\2",
        tag,
        re.IGNORECASE | re.DOTALL,
    )
    if class_match:
        existing = class_match.group(3).split()
        merged = existing + [name for name in classes if name not in existing]
        rewritten = (
            tag[:class_match.start(3)]
            + " ".join(merged)
            + tag[class_match.end(3):]
        )
    else:
        insert_at = tag.rfind("/>")
        if insert_at < 0:
            insert_at = tag.rfind(">")
        rewritten = (
            tag[:insert_at]
            + f' class="{" ".join(classes)}"'
            + tag[insert_at:]
        )
    return document[:match.start()] + rewritten + document[match.end():]


def _remove_classes_from_first_tag(
    document: str,
    pattern: str,
    classes: tuple[str, ...],
) -> str:
    match = re.search(pattern, document, re.IGNORECASE)
    if not match:
        return document
    tag = match.group(0)
    class_match = re.search(
        r"(\sclass=)([\"'])(.*?)\2",
        tag,
        re.IGNORECASE | re.DOTALL,
    )
    if not class_match:
        return document
    remaining = [
        name for name in class_match.group(3).split()
        if name not in classes
    ]
    if remaining:
        rewritten = (
            tag[:class_match.start(3)]
            + " ".join(remaining)
            + tag[class_match.end(3):]
        )
    else:
        rewritten = tag[:class_match.start()] + tag[class_match.end():]
    return document[:match.start()] + rewritten + document[match.end():]


def is_redirect_html(document: str) -> bool:
    head = document[:4096].lower()
    return (
        'http-equiv="refresh"' in head
        and 'name="robots" content="noindex' in head
    )


def microformat_answer_html(document: str) -> str:
    """Add a parser-compatible h-entry wrapper without changing visible copy."""
    if is_redirect_html(document):
        return document
    html_tag = re.search(r"<html\b[^>]*>", document, re.IGNORECASE)
    if not html_tag or not re.search(
        r"\slang=[\"']en[\"']",
        html_tag.group(0),
        re.IGNORECASE,
    ):
        raise ValueError("English answer page is missing html[lang=en]")

    canonical = re.search(
        r"<link\b[^>]*\srel=[\"']canonical[\"'][^>]*>",
        document,
        re.IGNORECASE,
    )
    if not canonical:
        raise ValueError("Missing canonical link while adding microformats")
    href = re.search(
        r"\shref=([\"'])(.*?)\1",
        canonical.group(0),
        re.IGNORECASE | re.DOTALL,
    )
    if not href:
        raise ValueError("Canonical link is missing href")
    canonical_url = html.unescape(href.group(2))

    old_author = (
        f'<a class="p-author h-card vcard u-url url" '
        f'href="{SITE}/about.html"><span class="p-name p-org fn org">'
        "Lumi Studio</span></a>"
    )
    document = document.replace(
        f"Publisher-authored guide from {old_author}, the app developer.",
        "Publisher-authored guide from Lumi Studio, the app developer.",
        1,
    )
    document = document.replace(f"Published by {old_author}. ", "", 1)
    document = document.replace(
        f'<link class="u-url url" href="{SITE}/about.html">',
        f'<data class="u-url url" value="{SITE}/about.html"></data>',
    )
    document = _remove_classes_from_first_tag(
        document,
        r"<title\b[^>]*>",
        ("p-name", "entry-title"),
    )
    document = _remove_classes_from_first_tag(
        document,
        r"<main\b[^>]*>",
        ("e-content", "entry-content"),
    )
    document = _remove_classes_from_first_tag(
        document,
        r"<body\b[^>]*>",
        ("h-entry", "hentry", "e-content", "entry-content"),
    )
    document = _remove_classes_from_first_tag(
        document,
        r"<html\b[^>]*>",
        ("h-entry", "hentry"),
    )
    document = _remove_classes_from_first_tag(
        document,
        r"<link\b[^>]*\srel=[\"']canonical[\"'][^>]*>",
        ("u-url", "u-uid"),
    )
    document = _add_classes_to_first_tag(
        document,
        r"<h1\b[^>]*>",
        ("p-name", "entry-title"),
        "answer heading",
    )
    document = _add_classes_to_first_tag(
        document,
        r"<p\b(?=[^>]*\sclass=[\"'][^\"']*\blead\b)[^>]*>",
        ("p-summary", "entry-summary"),
        "lead paragraph",
    )

    if "p-author" not in document:
        footer = re.search(
            r"<(?:div|footer)\b"
            r"(?=[^>]*\sclass=[\"'][^\"']*\bfooter\b)[^>]*>",
            document,
            re.IGNORECASE,
        )
        if not footer:
            raise ValueError("Missing answer footer while adding author")
        document = (
            document[:footer.end()]
            + author_microformat()
            + document[footer.end():]
        )

    root_start = "<!-- answer-microformat:start -->"
    root_end = "<!-- answer-microformat:end -->"
    content_start = "<!-- answer-content:start -->"
    content_end = "<!-- answer-content:end -->"
    if root_start not in document:
        body = re.search(r"<body\b[^>]*>", document, re.IGNORECASE)
        body_close = document.lower().rfind("</body>")
        if not body or body_close < body.end():
            raise ValueError("Missing body boundary while adding microformats")
        has_main = bool(re.search(r"<main\b[^>]*>", document, re.IGNORECASE))
        root_open = (
            f'{root_start}<div class="h-entry hentry">'
            f"{url_microformat(canonical_url)}"
        )
        root_close = f"</div>{root_end}"
        if has_main:
            document = (
                document[:body.end()]
                + root_open
                + document[body.end():body_close]
                + root_close
                + document[body_close:]
            )
            main = re.search(r"<main\b[^>]*>", document, re.IGNORECASE)
            main_close = re.search(
                r"</main>",
                document[main.end():] if main else "",
                re.IGNORECASE,
            )
            if not main or not main_close:
                raise ValueError("Missing main boundary while adding microformats")
            close_start = main.end() + main_close.start()
            close_end = main.end() + main_close.end()
            document = (
                document[:close_end]
                + f'</div>{content_end}'
                + document[close_end:]
            )
            document = (
                document[:main.start()]
                + f'{content_start}<div class="e-content entry-content">'
                + document[main.start():]
            )
        else:
            document = (
                document[:body.end()]
                + root_open
                + f'{content_start}<div class="e-content entry-content">'
                + document[body.end():body_close]
                + f"</div>{content_end}"
                + root_close
                + document[body_close:]
            )
    elif root_end not in document or content_start not in document:
        raise ValueError("Incomplete answer microformat wrapper")
    return document


def reconcile_answer_microformats(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    rendered = microformat_answer_html(source)
    if rendered == source:
        return False
    path.write_text(rendered, encoding="utf-8")
    return True


def application_category(key: str) -> str:
    cat = APPS[key].get("category", "")
    return {
        "education": "EducationalApplication",
        "kids": "EducationalApplication",
        "productivity": "ProductivityApplication",
        "finance": "FinanceApplication",
        "health": "HealthApplication",
        "lifestyle": "LifestyleApplication",
        "photo-utility": "UtilitiesApplication",
    }.get(cat, "UtilitiesApplication")


def feature_list(key: str) -> list[str]:
    app = APPS[key]
    features = list(app.get("cta_bullets", []))[:5]
    if key == "aim990":
        features.append("Independent TOEIC L&R study aid")
    return features[:6]


def render_page(
    question: str,
    key: str,
    content: dict[str, Any],
    pages_root: Path | None = None,
) -> str:
    effective_pages_root = (
        PAGES_ROOT if pages_root is None else pages_root.resolve()
    )
    app = APPS[key]
    name = app["name"]
    url = appstore_url(key, "iag_ans")
    slug = slugify(question)
    canonical = f"{SITE}/answers/{slug}.html"
    title = content.get("page_title") or f"{question}: honest iPhone app buying guide"
    meta = concise_meta(content["meta_description"], limit=220, hard_limit=220)
    style = extract_style(effective_pages_root)
    primary_resource_url = content.get("primary_resource_url", "")
    primary_resource_label = content.get("primary_resource_label", "")
    faq = content["faq"]
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "iOS App Guide", "item": f"{SITE}/index.html"},
            {"@type": "ListItem", "position": 2, "name": "Answers", "item": f"{SITE}/answers/index.html"},
            {"@type": "ListItem", "position": 3, "name": question, "item": canonical},
        ],
    }
    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": item["q"], "acceptedAnswer": {"@type": "Answer", "text": item["a"]}}
            for item in faq
        ],
    }
    howto = {
        "@context": "https://schema.org",
        "@type": "HowTo",
        "name": f"How to choose: {question}",
        "step": [
            {"@type": "HowToStep", "position": i + 1, "name": step.split(":")[0][:80], "text": step}
            for i, step in enumerate(content["decision_steps"])
        ],
    }
    software = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": name,
        "operatingSystem": "iOS",
        "applicationCategory": application_category(key),
        "url": url,
        "installUrl": url,
        "description": content["where_app_fits"],
        "featureList": feature_list(key),
    }
    resource_schema_html = ""
    if primary_resource_url:
        resource = {
            "@context": "https://schema.org",
            "@type": "LearningResource",
            "name": title,
            "description": meta,
            "url": primary_resource_url,
            "isAccessibleForFree": True,
        }
        if content.get("date_modified"):
            resource["dateModified"] = content["date_modified"]
        resource_schema_html = (
            '<script type="application/ld+json">\n'
            f"{j(resource)}\n"
            "</script>"
        )
    org = {"@context": "https://schema.org", "@graph": [
        {"@type": "Organization", "@id": f"{SITE}/#organization", "name": "Lumi Studio", "url": f"{SITE}/about.html"},
        {"@type": "WebSite", "@id": f"{SITE}/#website", "url": SITE, "name": "iOS App Guide", "publisher": {"@id": f"{SITE}/#organization"}},
    ]}
    pills = "".join(f'<span class="pill">{e(x)}</span>' for x in feature_list(key))
    look = "".join(f"<li>{e(x)}</li>" for x in content["what_to_look_for"])
    steps = "".join(f"<li>{e(x)}</li>" for x in content["decision_steps"])
    comparison_rows = "".join(
        f'<tr><td>{e(row["need"])}</td><td>{e(row["check"])}</td><td>{e(row["why"])}</td></tr>'
        for row in content["comparison_rows"]
    )
    sources = [
        source for source in content.get("sources", [])
        if source["url"].startswith("https://")
    ]
    sources_html = ""
    if sources:
        links = "".join(
            f'<li><a href="{e(source["url"])}" rel="noopener">{e(source["title"])}</a></li>'
            for source in sources
        )
        sources_html = f'<h2>Sources and resources</h2><ul class="checklist">{links}</ul>'
    paras = "".join(f"<p>{e(x)}</p>" for x in content["short_answer_paragraphs"])
    faq_html = "".join(
        f'<div itemscope itemtype="https://schema.org/Question"><h3 itemprop="name">{e(item["q"])}</h3><div itemprop="acceptedAnswer" itemscope itemtype="https://schema.org/Answer"><p itemprop="text">{e(item["a"])}</p></div></div>'
        for item in faq
    )
    guide_link = f"{SITE}/guides/{key}.html"
    alt_slug = alternative_hub_slug(key)
    alt_link = f"{SITE}/alternatives/{alt_slug}.html"
    if primary_resource_url:
        hero_actions = (
            f'<a class="cta" href="{e(primary_resource_url)}">'
            f'{e(primary_resource_label)} →</a>'
        )
        helpful_resource = (
            f'<a href="{e(primary_resource_url)}">{e(primary_resource_label)}</a>'
        )
        resource_first_meta = (
            '<meta name="iag-free-resource-first" content="true">'
        )
    else:
        hero_actions = (
            f'<a class="cta" href="{url}" rel="nofollow noopener">'
            f'Get {e(name)} on the App Store →</a> '
            f'<a class="cta ghost" href="{SITE}/tools/index.html">free tool →</a>'
        )
        helpful_resource = f'<a href="{SITE}/tools/index.html">free tool</a>'
        resource_first_meta = ""
    special_notice = ""
    if key == "aim990":
        special_notice = " TOEIC is a registered trademark of ETS. Aim990 is an independent study aid and is not affiliated with or endorsed by ETS. No app can guarantee a TOEIC score."
    alt_app_link = ""
    if (
        effective_pages_root / "alternatives" / f"{alt_slug}.html"
    ).is_file():
        alt_app_link = (
            f'<a href="{alt_link}">{e(name)} alternatives / guide</a>'
        )
    app_links = (
        f'<a href="{url}" rel="nofollow noopener">Get {e(name)} on the App Store</a>'
        f'<a href="{guide_link}">{e(name)} app guide</a>'
        f"{alt_app_link}"
    )
    app_fit = (
        f'<h2>Where {e(name)} fits</h2><p>{e(content["where_app_fits"])}</p>'
        f'<p>{pills}</p><p class="notice">This is a publisher-authored buying '
        "guide from the app developer. App Store features and prices can change, "
        "so confirm details on "
        f'the listing before purchase.{e(special_notice)}</p>'
    )
    if primary_resource_url:
        article_app_fit = ""
        sidebar_html = (
            '<h2>Helpful links</h2><div class="toc">'
            f"{helpful_resource}</div>"
        )
        deferred_app_fit = (
            f'<section class="wrap card">{app_fit}<div class="toc">'
            f"{app_links}</div></section>"
        )
    else:
        article_app_fit = app_fit
        sidebar_html = (
            '<h2>Helpful links</h2><div class="toc">'
            f"{helpful_resource}{app_links}</div><h2>Best for</h2>"
            f'<p class="muted">{e("; ".join(feature_list(key)))}</p>'
        )
        deferred_app_fit = ""
    social_metadata = (
        f'<meta property="og:type" content="article"><meta property="og:title" '
        f'content="{e(title)}"><meta property="og:description" content="{e(meta)}">'
        f'<meta property="og:url" content="{canonical}">'
        '<meta name="twitter:card" content="summary">'
    )
    rendered = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(meta)}"><link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="en" href="{canonical}">
<link rel="alternate" hreflang="x-default" href="{canonical}">
{social_metadata}{resource_first_meta}<style>
{style}
</style><script type="application/ld+json">
{j(breadcrumb)}
</script>
<script type="application/ld+json">
{j(faq_schema)}
</script>
<script type="application/ld+json">
{j(howto)}
</script>
{resource_schema_html}
<script type="application/ld+json">
{j(software)}
</script><script type="application/ld+json">
{j(org)}
</script>
</head>
<body><header class="top"><div class="wrap nav"><a href="{SITE}/index.html">iOS App Guide</a><nav><a href="{SITE}/answers/index.html">Answers</a> · <a href="{SITE}/tools/">Free tools</a> · <a href="{SITE}/alternatives/">Alternatives</a> · <a href="{SITE}/about.html">About</a></nav></div></header>
<main><section class="hero wrap"><div class="breadcrumb"><a href="{SITE}/index.html">Home</a> / <a href="{SITE}/answers/index.html">Answers</a></div><div class="eyebrow">High-intent answer</div><h1>{e(question)}</h1><p class="lead">{e(content["lead"])}</p><p>{hero_actions}</p></section>
<section class="wrap grid"><article class="card two answer"><h2>Short answer</h2>{paras}<h2>What to look for before choosing</h2><ul class="checklist">{look}</ul><h2>A practical decision process</h2><ol class="checklist">{steps}</ol><h2>Quick comparison</h2><table><thead><tr><th>Need</th><th>What to check</th><th>Why it matters</th></tr></thead><tbody>{comparison_rows}</tbody></table>{sources_html}{article_app_fit}</article><aside class="card side">{sidebar_html}</aside></section>
<section class="wrap card"><h2>FAQ</h2>{faq_html}</section>{deferred_app_fit}</main><footer class="footer"><div class="wrap">Publisher-authored guide from Lumi Studio, the app developer. App names are trademarks of their owners and are used only for identification. For documents, health, school, and productivity decisions, verify official requirements where relevant.</div></footer></body></html>'''
    return microformat_answer_html(rendered)


def _coverage_rates() -> dict:
    """Owned outreach coverage per app (lower = more neglected within its tier)."""
    path = ROOT / "reports" / "outreach_coverage.json"
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
        return {
            row["key"]: row.get("coverage_score", 0.0)
            for row in d.get("rows", [])
            if row.get("public")
        }
    except Exception:  # noqa: BLE001
        return {}


def question_plan(
    keys: list[str] | None, refresh_live: bool = True
) -> list[tuple[str, str]]:
    public = live_app_keys(APPSTORE, PAGES_ROOT, refresh=refresh_live)
    selected = keys or [key for key in APPS if key in public]
    unknown = [k for k in selected if k not in APPS]
    if unknown:
        raise SystemExit(f"Unknown app key(s): {', '.join(unknown)}")
    unavailable = [k for k in selected if k not in public]
    if unavailable:
        raise SystemExit(f"App Store not public; outreach skipped: {', '.join(unavailable)}")
    # 先守住商業優先層級，再用 AI 曝光率補同層級最弱處。
    rates = _coverage_rates()
    ordered = sorted(
        selected,
        key=lambda k: (OUTREACH_TIER.get(k, 3), rates.get(k, 0.0), k),
    )
    plan: list[tuple[str, str]] = []
    seen_slugs: set[str] = set()
    selected_keys = set(selected)
    for key in ordered:
        for q in queries.ALL.get(key, queries.CURATED.get(key, [])):
            if not is_english_answer_question(q):
                continue
            if queries.is_inherited_query(key, q, selected_keys):
                continue
            slug = slugify(q)
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)
            plan.append((key, q))
    return plan


def create_page(
    key: str,
    question: str,
    use_openai: bool = False,
    force: bool = False,
    pages_root: Path | None = None,
) -> str | None:
    answers_dir = (
        ANSWERS_DIR
        if pages_root is None
        else pages_root.resolve() / "answers"
    )
    slug = slugify(question)
    path = answers_dir / f"{slug}.html"
    if path.exists() and not force:
        return None
    try:
        if use_openai:
            raw = call_openai(prompt_for(question, key))
            content = normalized_content(raw, question, key)
        else:
            # 預設只用內建真實賣點，避免背景排程意外產生 API 成本。
            content = normalized_content(default_content(question, key), question, key)
    except Exception as exc:
        print(f"SKIP {slug}: {exc}", flush=True)
        return None
    rendered = render_page(question, key, content, pages_root=pages_root)
    if not path.exists() or path.read_text(encoding="utf-8") != rendered:
        path.write_text(rendered, encoding="utf-8")
    print(f"{'REFRESHED' if force else 'CREATED'} {slug}", flush=True)
    return slug


def parse_page_info(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    hm = re.search(r"<h1\b[^>]*>(.*?)</h1>", text, re.S | re.I)
    title = re.sub(r"<.*?>", "", hm.group(1)).strip() if hm else path.stem.replace("-", " ")
    sm = re.search(
        r'"@type"\s*:\s*"(?:SoftwareApplication|MobileApplication)"'
        r'.*?"name"\s*:\s*"([^"]+)"',
        text,
        re.S,
    )
    app = sm.group(1) if sm else "iOS app"
    return html.unescape(title), html.unescape(app)


def is_redirect_page(path: Path) -> bool:
    return is_redirect_html(path.read_text(encoding="utf-8", errors="replace"))


def feed_discovery_links() -> str:
    return "\n".join(
        (
            f'<link rel="alternate" type="application/atom+xml" '
            f'title="iOS App Guide — latest answers &amp; guides (Atom)" '
            f'href="{SITE}/feed.xml">',
            f'<link rel="alternate" type="application/rss+xml" '
            f'title="iOS App Guide — latest answers &amp; guides (RSS 2.0)" '
            f'href="{SITE}/rss.xml">',
            f'<link rel="alternate" type="application/feed+json" '
            f'title="iOS App Guide — latest answers &amp; guides '
            f'(JSON Feed 1.1)" href="{SITE}/feed.json">',
        )
    )


def regenerate_index(pages_root: Path | None = None) -> None:
    if pages_root is None:
        pages_root = PAGES_ROOT
        answers_dir = ANSWERS_DIR
    else:
        pages_root = pages_root.resolve()
        answers_dir = pages_root / "answers"
    pages = [
        p
        for p in answers_dir.glob("*.html")
        if p.name != "index.html" and not is_redirect_page(p)
    ]
    microformats_reconciled = sum(
        reconcile_answer_microformats(page) for page in pages
    )
    cards = []
    for p in sorted(pages, key=lambda x: x.stem):
        title, app = parse_page_info(p)
        cards.append(
            '<article class="card third h-entry hentry">'
            '<h2 class="p-name entry-title">'
            f'<a class="u-url u-uid" rel="bookmark" '
            f'href="{SITE}/answers/{p.name}">{e(title)}</a></h2>'
            f'<p class="muted p-summary entry-summary">Funnels to {e(app)}</p>'
            "</article>"
        )
    canonical = f"{SITE}/answers/index.html"
    style = extract_style(
        pages_root if answers_dir == pages_root / "answers" else None
    )
    breadcrumb = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "iOS App Guide", "item": f"{SITE}/index.html"},
        {"@type": "ListItem", "position": 2, "name": "Answers", "item": canonical},
    ]}
    org = {"@context": "https://schema.org", "@graph": [
        {"@type": "Organization", "@id": f"{SITE}/#organization", "name": "iOS App Guide", "url": SITE},
        {"@type": "WebSite", "@id": f"{SITE}/#website", "url": SITE, "name": "iOS App Guide", "publisher": {"@id": f"{SITE}/#organization"}},
    ]}
    alternate_links = [
        f'<link rel="alternate" hreflang="en" href="{canonical}">'
    ]
    locale_pattern = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z]{2,4})?$")
    for localized in sorted(pages_root.glob("*/answers/index.html")):
        locale = localized.parent.parent.name
        if locale_pattern.fullmatch(locale):
            alternate_links.append(
                '<link rel="alternate" '
                f'hreflang="{e(locale)}" '
                f'href="{SITE}/{e(locale)}/answers/index.html">'
            )
    alternate_links.append(
        f'<link rel="alternate" hreflang="x-default" href="{canonical}">'
    )
    alternates = "\n".join(alternate_links)
    html_doc = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>iOS App Answer Guides — High-Intent Buying Help</title><meta name="description" content="Substantive iPhone app buying guides for high-intent questions across productivity, education, finance, photo utilities, health, lifestyle, and kids apps."><link rel="canonical" href="{canonical}">
{alternates}
{feed_discovery_links()}
<meta property="og:type" content="website"><meta property="og:title" content="iOS App Answer Guides"><meta property="og:description" content="Honest buying guides and answer pages for iPhone apps."><meta property="og:url" content="{canonical}"><meta name="twitter:card" content="summary"><style>
{style}
</style><script type="application/ld+json">
{j(breadcrumb)}
</script><script type="application/ld+json">
{j(org)}
</script>
</head><body><div class="h-feed hfeed">{url_microformat(canonical, include_uid=False)}<header class="top"><div class="wrap nav"><a href="{SITE}/index.html">iOS App Guide</a><nav><a href="{SITE}/tools/">Free tools</a> · <a href="{SITE}/alternatives/">Alternatives</a> · <a href="{SITE}/about.html">About</a></nav></div></header><main><section class="hero wrap"><div class="eyebrow">Answer hub</div><h1 class="p-name site-title">iOS app answer guides</h1><p class="lead">Practical, honest pages for high-intent questions: what to check, when a dedicated app helps, and which Alice iOS app fits the job.</p></section><section class="wrap"><h2>Topic guides</h2><p class="muted"><a href="{SITE}/passport-photos.html">Passport &amp; ID photo sizes by country</a> · <a href="{SITE}/resume-formats.html">Resume &amp; CV formats by country</a> · <a href="{SITE}/kids-learning.html">Kids learning apps</a> · <a href="{SITE}/photo-tools.html">iPhone photo tools</a> · <a href="{SITE}/focus-productivity.html">Focus &amp; productivity</a> · <a href="{SITE}/money-travel.html">Money &amp; travel</a> · <a href="{SITE}/sleep-wellbeing.html">Sleep &amp; wellbeing</a> · <a href="{SITE}/data/">Free open data</a></p></section><section class="wrap grid">{''.join(cards)}</section></main><footer class="footer"><div class="wrap">{author_microformat()}First-party iOS app guides published by Lumi Studio, the developer of every listed app.</div></footer></div></body></html>'''
    index_path = answers_dir / "index.html"
    if index_path.exists():
        html_doc = sync_standard_site.preserve_managed_links(
            index_path.read_text(encoding="utf-8"),
            html_doc,
            label=str(index_path),
        )
    index_path.write_text(html_doc, encoding="utf-8")
    print(
        f"INDEX {len(pages)} pages; "
        f"{microformats_reconciled} microformats reconciled",
        flush=True,
    )


def write_sitemap(pages_root: Path | None = None) -> None:
    """Rebuild sitemap_answers.xml from files that actually exist (EN + localized)."""
    import time as _time
    pages_dir = (pages_root or PAGES_ROOT).resolve()
    entries: list[tuple[str, Path]] = []
    for p in sorted(pages_dir.glob("answers/*.html")):
        if not is_redirect_page(p):
            entries.append((f"{SITE}/answers/{p.name}", p))
    for p in sorted(pages_dir.glob("*/answers/*.html")):
        rel = p.relative_to(pages_dir).as_posix()
        if not is_redirect_page(p):
            entries.append((f"{SITE}/{rel}", p))

    def _lm(p: Path) -> str:
        return _time.strftime("%Y-%m-%d", _time.gmtime(p.stat().st_mtime))

    body = "\n".join(
        f"  <url><loc>{html.escape(u)}</loc><lastmod>{_lm(p)}</lastmod></url>"
        for u, p in entries)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           f"{body}\n</urlset>\n")
    (pages_dir / "sitemap_answers.xml").write_text(xml, encoding="utf-8")
    print(f"SITEMAP sitemap_answers.xml {len(entries)} urls", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate AEO/GEO answer pages.")
    parser.add_argument("apps", nargs="*", help="Optional app keys. Defaults to all apps.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of new pages to create.")
    parser.add_argument("--no-finalize", action="store_true", help="Skip index+sitemap rebuild (for parallel workers).")
    parser.add_argument("--use-openai", action="store_true", help="Explicitly opt in to OpenAI generation. Default is offline.")
    parser.add_argument(
        "--refresh-slug",
        action="append",
        default=[],
        help="Regenerate only this existing answer slug; may be repeated.",
    )
    parser.add_argument(
        "--cached-live",
        action="store_true",
        help="Use the verified availability snapshot without refreshing it.",
    )
    args = parser.parse_args()
    if args.use_openai and not key_available():
        parser.error("--use-openai requires ~/.openai_key")
    ANSWERS_DIR.mkdir(parents=True, exist_ok=True)
    plan = question_plan(args.apps or None, refresh_live=not args.cached_live)
    force = bool(args.refresh_slug)
    if force:
        by_slug = {slugify(question): (key, question) for key, question in plan}
        requested = [Path(value).stem for value in args.refresh_slug]
        missing = [slug for slug in requested if slug not in by_slug]
        if missing:
            parser.error(
                "unknown --refresh-slug value(s): " + ", ".join(missing)
            )
        plan = [by_slug[slug] for slug in requested]
    created: list[str] = []
    for key, question in plan:
        if args.limit is not None and len(created) >= args.limit:
            break
        slug = create_page(
            key,
            question,
            use_openai=args.use_openai,
            force=force,
        )
        if slug:
            created.append(slug)
    if not args.no_finalize:
        regenerate_index()
        write_sitemap()
    print(json.dumps({"created_count": len(created), "created_slugs": created}, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
