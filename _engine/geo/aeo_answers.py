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
ANSWERS_DIR = ROOT / "pages" / "answers"
SITE = "https://alice51849.github.io/ios-app-guide"
MODEL = "gpt-4o-mini"
OPENAI_ENDPOINT = "https://api.openai.com/v1/chat/completions"

sys.path.insert(0, str(ROOT / ".." / "social"))
from videogen.registry import APPS, appstore_url  # noqa: E402
import queries  # noqa: E402

TEMPLATE = ANSWERS_DIR / "best-offline-document-scanner-app-for-iphone.html"


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


def extract_style() -> str:
    text = TEMPLATE.read_text(encoding="utf-8")
    m = re.search(r"<style>\n(.*?)\n</style>", text, re.S)
    if not m:
        raise RuntimeError("Could not extract template CSS")
    return m.group(1)


STYLE = extract_style()


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
            "Aim990 has BOTH a one-time unlock option AND subscription options; never claim no subscription.",
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
        "app_store_url": appstore_url(key),
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
            "lead": "one sentence",
            "short_answer_paragraphs": "2 paragraphs, total about 130-180 words; start with buying criteria, then recommend the app as a strong option",
            "what_to_look_for": "5 bullets",
            "decision_steps": "5 short steps",
            "where_app_fits": "1 paragraph",
            "faq": "3 Q&A items, concise answers",
        },
        "app_facts": facts,
        "tone": "helpful, practical, independent, non-hype",
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
    return {
        "meta_description": f"{question}: what to check before choosing an iPhone app, and where {name} may fit as a practical option.",
        "lead": f"A practical buying guide for {question}, with criteria to check before you install.",
        "short_answer_paragraphs": [
            "The best choice depends on your real use case: privacy, offline access, export options, ease of use, and whether the pricing model still makes sense after a few months. Before installing, test the app with a realistic task rather than judging only by screenshots.",
            f"{name} is worth considering if its App Store listing matches your needs. It focuses on {app.get('sub', '').rstrip('.')}, and its listed strengths include {', '.join(app.get('cta_bullets', [])[:3])}.",
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
        "where_app_fits": f"{name} is a strong fit when you want a focused iPhone tool rather than a broad, complicated suite.",
        "faq": [
            {"q": f"Is {name} a good option?", "a": f"{name} can be a good option if its current App Store features match your needs and budget."},
            {"q": "What should I verify first?", "a": "Check current pricing, privacy labels, export limits, and the exact features included in the version you plan to use."},
            {"q": "Is this page independent?", "a": "Yes. It is a buying guide; app names and trademarks belong to their respective owners."},
        ],
    }


def normalized_content(raw: dict[str, Any], question: str, key: str) -> dict[str, Any]:
    base = default_content(question, key)
    content = {
        "meta_description": safe_text(raw.get("meta_description"), base["meta_description"]),
        "lead": safe_text(raw.get("lead"), base["lead"]),
        "short_answer_paragraphs": safe_list(raw.get("short_answer_paragraphs"), 2, base["short_answer_paragraphs"]),
        "what_to_look_for": safe_list(raw.get("what_to_look_for"), 5, base["what_to_look_for"]),
        "decision_steps": safe_list(raw.get("decision_steps"), 5, base["decision_steps"]),
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

    if key == "aim990":
        disclaimer = " TOEIC is a registered trademark of ETS; Aim990 is an independent study aid and is not affiliated with or endorsed by ETS. It does not guarantee any score."
        if "ETS" not in content["where_app_fits"]:
            content["where_app_fits"] = content["where_app_fits"].rstrip(".") + "." + disclaimer
        joined = json.dumps(content, ensure_ascii=False).lower()
        if "no subscription" in joined or "subscription-free" in joined:
            raise ValueError("Unsafe Aim990 subscription claim detected")
    return content


def j(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def e(s: str) -> str:
    return html.escape(s, quote=True)


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
        features.append("One-time unlock option and subscription options")
        features.append("Independent TOEIC L&R study aid")
    return features[:6]


def render_page(question: str, key: str, content: dict[str, Any]) -> str:
    app = APPS[key]
    name = app["name"]
    url = appstore_url(key)
    slug = slugify(question)
    canonical = f"{SITE}/answers/{slug}.html"
    title = f"{question}: honest iPhone app buying guide"
    meta = content["meta_description"][:220]
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
        "description": meta,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD", "description": "Free to download; check the App Store for current pricing and unlock details."},
        "featureList": feature_list(key),
    }
    org = {"@context": "https://schema.org", "@graph": [
        {"@type": "Organization", "@id": f"{SITE}/#organization", "name": "iOS App Guide", "url": SITE},
        {"@type": "WebSite", "@id": f"{SITE}/#website", "url": SITE, "name": "iOS App Guide", "publisher": {"@id": f"{SITE}/#organization"}},
    ]}
    pills = "".join(f'<span class="pill">{e(x)}</span>' for x in feature_list(key))
    look = "".join(f"<li>{e(x)}</li>" for x in content["what_to_look_for"])
    steps = "".join(f"<li>{e(x)}</li>" for x in content["decision_steps"])
    paras = "".join(f"<p>{e(x)}</p>" for x in content["short_answer_paragraphs"])
    faq_html = "".join(
        f'<div itemscope itemtype="https://schema.org/Question"><h3 itemprop="name">{e(item["q"])}</h3><div itemprop="acceptedAnswer" itemscope itemtype="https://schema.org/Answer"><p itemprop="text">{e(item["a"])}</p></div></div>'
        for item in faq
    )
    guide_link = f"{SITE}/guides/{key}.html"
    alt_link = f"{SITE}/alternatives/{key}-no-subscription.html"
    special_notice = ""
    if key == "aim990":
        special_notice = " TOEIC is a registered trademark of ETS. Aim990 is an independent study aid and is not affiliated with or endorsed by ETS. No app can guarantee a TOEIC score."
        alt_link = f"{SITE}/guides/{key}.html"
    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(meta)}"><link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="en" href="{canonical}">
<link rel="alternate" hreflang="x-default" href="{canonical}">
<meta property="og:type" content="article"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(meta)}"><meta property="og:url" content="{canonical}"><meta name="twitter:card" content="summary"><style>
{STYLE}
</style><script type="application/ld+json">
{j(breadcrumb)}
</script>
<script type="application/ld+json">
{j(faq_schema)}
</script>
<script type="application/ld+json">
{j(howto)}
</script>
<script type="application/ld+json">
{j(software)}
</script><script type="application/ld+json">
{j(org)}
</script>
</head>
<body><header class="top"><div class="wrap nav"><a href="{SITE}/index.html">iOS App Guide</a><nav><a href="{SITE}/answers/index.html">Answers</a> · <a href="{SITE}/tools/">Free tools</a> · <a href="{SITE}/alternatives/">Alternatives</a></nav></div></header>
<main><section class="hero wrap"><div class="breadcrumb"><a href="{SITE}/index.html">Home</a> / <a href="{SITE}/answers/index.html">Answers</a></div><div class="eyebrow">High-intent answer</div><h1>{e(question)}</h1><p class="lead">{e(content["lead"])}</p><p><a class="cta" href="{url}" rel="nofollow noopener">Get {e(name)} on the App Store →</a> <a class="cta ghost" href="{SITE}/tools/index.html">free tool →</a></p></section>
<section class="wrap grid"><article class="card two answer"><h2>Short answer</h2>{paras}<h2>What to look for before choosing</h2><ul class="checklist">{look}</ul><h2>A practical decision process</h2><ol class="checklist">{steps}</ol><h2>Quick comparison</h2><table><thead><tr><th>Need</th><th>What to check</th><th>Why it matters</th></tr></thead><tbody><tr><td>Pricing model</td><td>Check whether useful features require a subscription, a one-time unlock, or neither.</td><td>The cheapest app on day one may not be cheapest after a year.</td></tr><tr><td>Privacy model</td><td>Prefer on-device work when the content is sensitive.</td><td>Private documents, resumes, study data, and family content deserve careful handling.</td></tr><tr><td>Export / lock-in</td><td>Confirm file formats, sharing, backup, and deletion controls.</td><td>A good app should help you finish the task, not trap your work.</td></tr></tbody></table><h2>Where {e(name)} fits</h2><p>{e(content["where_app_fits"])}</p><p>{pills}</p><p class="notice">This page is an independent buying guide. App Store features and prices can change, so confirm details on the listing before purchase.{e(special_notice)}</p></article><aside class="card side"><h2>Helpful links</h2><div class="toc"><a href="{url}" rel="nofollow noopener">Get {e(name)} on the App Store</a><a href="{guide_link}">{e(name)} app guide</a><a href="{alt_link}">{e(name)} alternatives / guide</a><a href="{SITE}/tools/index.html">free tool</a></div><h2>Best for</h2><p class="muted">{e('; '.join(feature_list(key)))}</p></aside></section>
<section class="wrap card"><h2>FAQ</h2>{faq_html}</section></main><footer class="footer"><div class="wrap">Independent guide. App names are trademarks of their owners and are used only for identification. For documents, health, school, and productivity decisions, verify official requirements where relevant.</div></footer></body></html>'''


def question_plan(keys: list[str] | None) -> list[tuple[str, str]]:
    selected = keys or list(APPS.keys())
    unknown = [k for k in selected if k not in APPS]
    if unknown:
        raise SystemExit(f"Unknown app key(s): {', '.join(unknown)}")
    ordered = []
    if "aim990" in selected:
        ordered.append("aim990")
    ordered.extend([k for k in selected if k != "aim990"])
    plan: list[tuple[str, str]] = []
    seen_slugs: set[str] = set()
    for key in ordered:
        for q in queries.ALL.get(key, queries.CURATED.get(key, [])):
            if not is_english_answer_question(q):
                continue
            slug = slugify(q)
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)
            plan.append((key, q))
    return plan


def create_page(key: str, question: str) -> str | None:
    slug = slugify(question)
    path = ANSWERS_DIR / f"{slug}.html"
    if path.exists():
        return None
    try:
        raw = call_openai(prompt_for(question, key))
        content = normalized_content(raw, question, key)
    except Exception as exc:
        print(f"SKIP {slug}: {exc}", flush=True)
        return None
    path.write_text(render_page(question, key, content), encoding="utf-8")
    print(f"CREATED {slug}", flush=True)
    return slug


def parse_page_info(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    hm = re.search(r"<h1>(.*?)</h1>", text, re.S)
    title = re.sub(r"<.*?>", "", hm.group(1)).strip() if hm else path.stem.replace("-", " ")
    sm = re.search(r'"@type"\s*:\s*"SoftwareApplication".*?"name"\s*:\s*"([^"]+)"', text, re.S)
    app = sm.group(1) if sm else "iOS app"
    return html.unescape(title), html.unescape(app)


def regenerate_index() -> None:
    pages = [p for p in ANSWERS_DIR.glob("*.html") if p.name != "index.html"]
    cards = []
    for p in sorted(pages, key=lambda x: x.stem):
        title, app = parse_page_info(p)
        cards.append(f'<article class="card third"><h2><a href="{SITE}/answers/{p.name}">{e(title)}</a></h2><p class="muted">Funnels to {e(app)}</p></article>')
    canonical = f"{SITE}/answers/index.html"
    breadcrumb = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "iOS App Guide", "item": f"{SITE}/index.html"},
        {"@type": "ListItem", "position": 2, "name": "Answers", "item": canonical},
    ]}
    org = {"@context": "https://schema.org", "@graph": [
        {"@type": "Organization", "@id": f"{SITE}/#organization", "name": "iOS App Guide", "url": SITE},
        {"@type": "WebSite", "@id": f"{SITE}/#website", "url": SITE, "name": "iOS App Guide", "publisher": {"@id": f"{SITE}/#organization"}},
    ]}
    html_doc = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>iOS App Answer Guides — High-Intent Buying Help</title><meta name="description" content="Substantive iPhone app buying guides for high-intent questions across productivity, education, finance, photo utilities, health, lifestyle, and kids apps."><link rel="canonical" href="{canonical}">
<link rel="alternate" hreflang="en" href="{canonical}">
<link rel="alternate" hreflang="x-default" href="{canonical}"><meta property="og:type" content="website"><meta property="og:title" content="iOS App Answer Guides"><meta property="og:description" content="Honest buying guides and answer pages for iPhone apps."><meta property="og:url" content="{canonical}"><meta name="twitter:card" content="summary"><style>
{STYLE}
</style><script type="application/ld+json">
{j(breadcrumb)}
</script><script type="application/ld+json">
{j(org)}
</script>
</head><body><header class="top"><div class="wrap nav"><a href="{SITE}/index.html">iOS App Guide</a><nav><a href="{SITE}/tools/">Free tools</a> · <a href="{SITE}/alternatives/">Alternatives</a></nav></div></header><main><section class="hero wrap"><div class="eyebrow">Answer hub</div><h1>iOS app answer guides</h1><p class="lead">Practical, honest pages for high-intent questions: what to check, when a dedicated app helps, and which Alice iOS app fits the job.</p></section><section class="wrap grid">{''.join(cards)}</section></main><footer class="footer"><div class="wrap">Independent iOS app guide.</div></footer></body></html>'''
    (ANSWERS_DIR / "index.html").write_text(html_doc, encoding="utf-8")
    print(f"INDEX {len(pages)} pages", flush=True)


def write_sitemap() -> None:
    """Rebuild sitemap_answers.xml from files that actually exist (EN + localized)."""
    pages_dir = ROOT / "pages"
    locs: list[str] = []
    for p in sorted(pages_dir.glob("answers/*.html")):
        locs.append(f"{SITE}/answers/{p.name}")
    for p in sorted(pages_dir.glob("*/answers/*.html")):
        rel = p.relative_to(pages_dir).as_posix()
        locs.append(f"{SITE}/{rel}")
    body = "\n".join(f"  <url><loc>{html.escape(u)}</loc></url>" for u in locs)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           f"{body}\n</urlset>\n")
    (pages_dir / "sitemap_answers.xml").write_text(xml, encoding="utf-8")
    print(f"SITEMAP sitemap_answers.xml {len(locs)} urls", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate AEO/GEO answer pages.")
    parser.add_argument("apps", nargs="*", help="Optional app keys. Defaults to all apps.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of new pages to create.")
    args = parser.parse_args()
    ANSWERS_DIR.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    for key, question in question_plan(args.apps or None):
        if args.limit is not None and len(created) >= args.limit:
            break
        slug = create_page(key, question)
        if slug:
            created.append(slug)
    regenerate_index()
    write_sitemap()
    print(json.dumps({"created_count": len(created), "created_slugs": created}, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
