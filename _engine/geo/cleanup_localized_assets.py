#!/usr/bin/env python3
"""Remove stale localized outreach pages and repair canonical alternative links."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

from videogen.registry import APPS, APPSTORE  # noqa: E402

from aeo_pages import pricing_profile  # noqa: E402
from appstore_live import live_app_keys  # noqa: E402
from build_pages_i18n import pricing_text_for  # noqa: E402
from gen_roundups import TOPICS, legacy_slug, redirect_page  # noqa: E402

PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
LOCALE_RE = re.compile(r"^[a-z]{2,3}(?:-[A-Za-z]{2,4})?$")
RESERVED_TOP_LEVEL_DIRS = {"api"}
URL_BLOCK_RE = re.compile(r"\s*<url>.*?</url>", re.DOTALL)
SITEMAP_ALT_LINK_RE = re.compile(
    r'\s*<xhtml:link\b[^>]*\bhref="([^"]+)"[^>]*/>',
    re.IGNORECASE,
)
HTML_HREFLANG_BLOCK_RE = re.compile(
    r'(?:\s*<link\b[^>]*\brel="alternate"[^>]*\bhreflang="[^"]+"[^>]*>)+',
    re.IGNORECASE,
)
INDEX_ITEM_RE = re.compile(
    r'\s*<li>\s*<a href="([^"]+\.html)">.*?</li>', re.DOTALL
)
JSON_LD_SCRIPT_RE = re.compile(
    r'<script\b[^>]*type=["\']application/ld\+json["\'][^>]*>.*?</script>',
    re.IGNORECASE | re.DOTALL,
)
PROMO_BLOCK_RE = re.compile(
    r"<(?P<tag>p|li|aside|article)\b[^>]*>.*?</(?P=tag)>",
    re.IGNORECASE | re.DOTALL,
)
LINK_LIST_ITEM_RE = re.compile(
    r"<li\b[^>]*>.*?</li>", re.IGNORECASE | re.DOTALL
)
LINK_ARTICLE_RE = re.compile(
    r"<article\b[^>]*>.*?</article>", re.IGNORECASE | re.DOTALL
)
ANCHOR_RE = re.compile(
    r'<a\b(?P<attrs>[^>]*\bhref="(?P<href>[^"]*)"[^>]*)>'
    r"(?P<body>.*?)</a>",
    re.IGNORECASE | re.DOTALL,
)
ZERO_PRICE_OFFER_RE = re.compile(
    r'\s*"offers"\s*:\s*\{(?=[^{}]*"price"\s*:\s*"0")[^{}]*\}\s*,',
    re.DOTALL,
)
ZERO_PRICE_LAST_OFFER_RE = re.compile(
    r',\s*"offers"\s*:\s*\{(?=[^{}]*"price"\s*:\s*"0")[^{}]*\}\s*(?=\})',
    re.DOTALL,
)
_HUB_SUFFIX_BY_PROFILE = {
    "pay_once": "no-subscription",
    "free_to_start": "free-to-start",
    "free": "free-no-ads",
    "flexible": "flexible-unlock",
    "neutral": "private-alternative",
}
_LEGACY_HUB_SUFFIXES = {
    "no-subscription",
    "pay-once",
    "free-to-start",
    "free-no-ads",
    "flexible-unlock",
    "private-alternative",
}
LEGACY_ALT_SLUGS = {}
for _key in APPS:
    _current = f"{_key}-{_HUB_SUFFIX_BY_PROFILE[pricing_profile(_key)]}"
    for _suffix in _LEGACY_HUB_SUFFIXES:
        _legacy = f"{_key}-{_suffix}"
        if _legacy != _current:
            LEGACY_ALT_SLUGS[_legacy] = _current
RETIRED_ANSWER_REDIRECTS = {
    "app-to-convert-a-shopping-price-into-hours-of-work-before-buying-pay-once-no-subscription":
        "best-app-to-track-where-my-money-goes-and-save-more",
    "app-that-converts-a-price-to-hours-of-work-before-buying":
        "best-app-to-track-where-my-money-goes-and-save-more",
    "app-to-see-how-many-hours-of-work-a-purchase-costs-before-buying-in-taiwan-or-korea":
        "best-app-to-track-where-my-money-goes-and-save-more",
    "best-mindful-spending-app-to-stop-impulse-buying-iphone":
        "best-app-to-track-where-my-money-goes-and-save-more",
    "best-work-hours-tracker-app-for-freelancers":
        "best-app-to-track-where-my-money-goes-and-save-more",
    "how-do-i-calculate-my-real-hourly-wage-to-judge-whether-something-is-worth-buying":
        "best-app-to-track-where-my-money-goes-and-save-more",
    "how-to-decide-if-a-big-purchase-like-a-new-phone-or-a-vacation-is-worth-the-work-hours":
        "best-app-to-track-where-my-money-goes-and-save-more",
    "how-to-do-a-no-spend-challenge-and-actually-stick-to-it":
        "best-app-to-track-where-my-money-goes-and-save-more",
    "impulse-shopping-blocker-that-shows-the-time-cost-of-a-purchase-pay-once-private":
        "best-app-to-track-where-my-money-goes-and-save-more",
    "simple-timesheet-app-to-log-work-hours":
        "best-app-to-track-where-my-money-goes-and-save-more",
    "what-is-the-true-cost-of-a-purchase-in-hours-of-work":
        "best-app-to-track-where-my-money-goes-and-save-more",
}
HOURSTAG_GUIDE_PATH = Path("guides") / "hourstag.html"
RETIRED_ANSWER_PATH_RE = re.compile(
    r"/(?:(?P<locale>[a-z]{2,3}(?:-[A-Za-z]{2,4})?)/)?answers/"
    r"(?P<slug>"
    + "|".join(re.escape(slug) for slug in RETIRED_ANSWER_REDIRECTS)
    + r")\.html"
)
PUBLIC_TEXT_SUFFIXES = {
    ".csv",
    ".html",
    ".json",
    ".jsonl",
    ".jsonld",
    ".md",
    ".xml",
}
ACCURATE_LEGACY_PROFILES = {"pay_once"}
PAID_UPFRONT_KEYS = {
    key
    for key, app in APPS.items()
    if app.get("purchase_model") == "paid_upfront"
}
STALE_LOCALIZED_ROUNDUP_SLUGS = {
    legacy_slug(topic)
    for key, topic in TOPICS.items()
    if pricing_profile(key) != "pay_once"
}
AIM990_FALSE_COPY = {
    "en-US": (
        "Aim990 is a pay-once app with no subscriptions or ads, allowing for an uninterrupted learning experience.",
    ),
    "ar-SA": (
        "نعم، Aim990 هو تطبيق مدفوع لمرة واحدة بدون اشتراكات.",
    ),
    "da": (
        "Nej, du betaler kun én gang for at få livslang adgang til alle funktioner i Aim990.",
        "Ingen abonnementer - betal én gang for livslang adgang",
    ),
    "de-DE": (
        "Aim990 bietet keine Testversion, jedoch eine einmalige Zahlung ohne Abonnements oder versteckte Gebühren.",
        "Keine Werbung, keine Abonnements – einmalige Zahlung",
    ),
    "es-ES": (
        "No, Aim990 es una aplicación de pago único sin suscripciones.",
    ),
    "fr-FR": (
        "Pas d'abonnement, paiement unique",
        "Aim990 se distingue par sa capacité à personnaliser votre apprentissage du TOEIC grâce à des drills ciblés et un suivi des performances. C'est un excellent choix pour ceux qui souhaitent maximiser leur score sans se soucier des abonnements mensuels.",
        "Améliorez votre score TOEIC avec Aim990 ! Un coach d'étude de 30 jours, sans abonnements ni publicités, pour des résulta",
        "Améliorez votre score TOEIC avec Aim990 ! Un coach d'étude de 30 jours, sans abonnements ni publicités, pour des résultats optimaux.",
    ),
    "hi": (
        "Aim990 एक पे-वन ऐप है, जिसमें कोई सब्सक्रिप्शन शुल्क नहीं है।",
    ),
    "id": (
        "Aim990 adalah aplikasi berbayar dengan pembelian satu kali, tanpa biaya langganan.",
    ),
    "it": (
        "Aim990 è un'app a pagamento una tantum, senza abbonamenti mensili.",
        "Nessuna pubblicità o abbonamento",
    ),
    "ko": (
        "Aim990은 일회성 결제 앱으로, 추가 구독료가 없습니다.",
    ),
    "nl-NL": (
        "Aim990 is een eenmalige aankoop zonder abonnementen, dus er is geen proefperiode, maar je krijgt wel volledige toegang na aankoop.",
        "Geen advertenties of abonnementen",
    ),
    "no": (
        "Nei, Aim990 er en engangskjøp-app uten skjulte kostnader eller abonnementer.",
        "Ingen annonser eller abonnement",
    ),
    "pl": (
        "Brak subskrypcji – jednorazowy zakup",
    ),
    "pt-BR": (
        "O Aim990 é um aplicativo pago, mas não possui assinaturas, permitindo que você pague uma única vez.",
        "Recursos sem anúncios e sem assinatura",
    ),
    "pa-IN": (
        "ਇੱਕ ਵਾਰੀ ਖੋਲ੍ਹਣ ਦਾ ਵਿਕਲਪ ਅਤੇ ਸਬਸਕ੍ਰਿਪਸ਼ਨ ਵਿਕਲਪ",
        "ਲਚਕੀਲੇ ਭੁਗਤਾਨ ਦੇ ਵਿਕਲਪ, ਜਿਸ ਵਿੱਚ ਇੱਕ ਵਾਰੀ ਖੋਲ੍ਹਣ ਅਤੇ ਸਬਸਕ੍ਰਿਪਸ਼ਨ ਸ਼ਾਮਲ ਹਨ",
    ),
    "ro": (
        "Aim990 este o aplicație cu plată unică, fără abonamente sau reclame.",
    ),
    "sk": (
        "Aim990 je aplikácia s jednorazovým nákupom, bez predplatného alebo reklám.",
    ),
    "sv": (
        "Aim990 är en betald app med engångsköp, vilket innebär att det inte finns några prenumerationsavgifter.",
        "Ingen prenumeration, engångsköp",
    ),
    "th": (
        "Aim990 เป็นแอปที่จ่ายครั้งเดียว ไม่มีการสมัครสมาชิก.",
    ),
    "tr": (
        "Aim990, tek seferlik bir ödeme ile kullanılabilir, abonelik gerektirmez.",
    ),
    "vi": (
        "Aim990 yêu cầu một khoản phí một lần để tải xuống, không có phí đăng ký hàng tháng.",
    ),
    "zh-Hans": (
        "Aim990是一款一次性付费的应用，不需要订阅，购买后可无限使用。",
    ),
    "zh-Hant": (
        "Aim990是一款一次性購買的應用程式，無需訂閱。",
    ),
}


def locale_dirs(pages: Path) -> list[Path]:
    return sorted(
        child
        for child in pages.iterdir()
        if (
            child.is_dir()
            and child.name not in RESERVED_TOP_LEVEL_DIRS
            and LOCALE_RE.fullmatch(child.name)
        )
    )


def app_key_for_alternative(filename: str) -> str | None:
    return next(
        (
            key
            for key in sorted(APPS, key=len, reverse=True)
            if filename.startswith(f"{key}-")
        ),
        None,
    )


def replace_retired_answer_slugs(text: str, pages: Path = PAGES) -> str:
    def repl(match: re.Match[str]) -> str:
        locale = match.group("locale")
        replacement = RETIRED_ANSWER_REDIRECTS[match.group("slug")]
        if locale:
            locale_dir = pages / locale
            localized_answer = (
                locale_dir / "answers" / f"{replacement}.html"
            )
            if localized_answer.exists():
                return f"/{locale}/answers/{replacement}.html"
            if (locale_dir / "hourstag.html").exists():
                return f"/{locale}/hourstag.html"
        return f"/answers/{replacement}.html"

    return RETIRED_ANSWER_PATH_RE.sub(repl, text)


def dedupe_json_ld_item_lists(text: str) -> str:
    def sanitize_script(match: re.Match[str]) -> str:
        block = match.group(0)
        start = block.find(">") + 1
        end = block.rfind("</script>")
        try:
            payload = json.loads(block[start:end])
        except (TypeError, ValueError, json.JSONDecodeError):
            return block
        changed = False

        def identity(item: object) -> str | None:
            if not isinstance(item, dict):
                return None
            target = item.get("url")
            nested = item.get("item")
            if not target and isinstance(nested, str):
                target = nested
            elif not target and isinstance(nested, dict):
                target = nested.get("@id") or nested.get("url")
            return str(target) if target else None

        def visit(value: object) -> None:
            nonlocal changed
            if isinstance(value, dict):
                elements = value.get("itemListElement")
                if isinstance(elements, list):
                    seen: set[str] = set()
                    kept = []
                    for item in elements:
                        key = identity(item)
                        if key and key in seen:
                            changed = True
                            continue
                        if key:
                            seen.add(key)
                        kept.append(item)
                    if len(kept) != len(elements):
                        value["itemListElement"] = kept
                        if "numberOfItems" in value:
                            value["numberOfItems"] = len(kept)
                        for position, item in enumerate(kept, 1):
                            if isinstance(item, dict) and "position" in item:
                                item["position"] = position
                for item in value.values():
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        visit(payload)
        if not changed:
            return block
        return (
            block[:start]
            + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            + block[end:]
        )

    return JSON_LD_SCRIPT_RE.sub(sanitize_script, text)


def replace_legacy_slugs(text: str, pages: Path = PAGES) -> str:
    for old, new in LEGACY_ALT_SLUGS.items():
        text = text.replace(f"/alternatives/{old}.html", f"/alternatives/{new}.html")
    return replace_retired_answer_slugs(text, pages)


def reconcile_retired_answer_references(pages: Path) -> int:
    changed = 0
    for path in pages.rglob("*"):
        if not path.is_file() or path.suffix not in PUBLIC_TEXT_SUFFIXES:
            continue
        relative = path.relative_to(pages)
        if relative.parts[0] in {".git", "_engine"}:
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        updated = replace_retired_answer_slugs(original, pages)
        if updated != original and path.suffix == ".html":
            updated = dedupe_json_ld_item_lists(updated)
        if updated == original:
            continue
        path.write_text(updated, encoding="utf-8")
        changed += 1
    return changed


def reconcile_retired_answer_redirects(
    pages: Path,
    locales: list[Path],
) -> int:
    root_answers = pages / "answers"
    changed = 0
    for old, new in RETIRED_ANSWER_REDIRECTS.items():
        root_target = root_answers / f"{new}.html"
        if not root_target.exists():
            continue
        roots = [(root_answers, f"{SITE}/answers/{new}.html")]
        for locale_dir in locales:
            localized_target = locale_dir / "answers" / f"{new}.html"
            localized_app = locale_dir / "hourstag.html"
            if localized_target.exists():
                destination = (
                    f"{SITE}/{locale_dir.name}/answers/{new}.html"
                )
            elif localized_app.exists():
                destination = f"{SITE}/{locale_dir.name}/hourstag.html"
            else:
                destination = f"{SITE}/answers/{new}.html"
            roots.append((locale_dir / "answers", destination))
        for answers, destination in roots:
            old_page = answers / f"{old}.html"
            if not old_page.exists():
                continue
            rendered = redirect_page(destination)
            if old_page.read_text(encoding="utf-8") == rendered:
                continue
            old_page.write_text(rendered, encoding="utf-8")
            changed += 1
    return changed


def reconcile_hourstag_guide_redirects(
    pages: Path,
    locales: list[Path],
) -> int:
    destination = f"{SITE}/{HOURSTAG_GUIDE_PATH.as_posix()}"
    changed = 0
    for locale_dir in locales:
        guide = locale_dir / HOURSTAG_GUIDE_PATH
        if not guide.exists():
            continue
        rendered = redirect_page(destination)
        if guide.read_text(encoding="utf-8") == rendered:
            continue
        guide.write_text(rendered, encoding="utf-8")
        changed += 1
    return changed


def sanitize_known_aim990_claims(text: str, locale: str) -> tuple[str, int]:
    replacements = AIM990_FALSE_COPY.get(locale, ())
    if not replacements or "Aim990" not in html.unescape(text):
        return text, 0
    safe = pricing_text_for("aim990", locale)
    count = 0
    for old in sorted(replacements, key=len, reverse=True):
        candidates = {
            old: safe,
            html.escape(old): html.escape(safe),
        }
        for candidate, replacement in candidates.items():
            occurrences = text.count(candidate)
            if occurrences:
                text = text.replace(candidate, replacement)
                count += occurrences
    return text, count


def aim990_bad_translations(locale: str) -> set[str]:
    path = HERE / "i18n_trans" / f"{locale}.json"
    try:
        translations = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return set()
    markers = re.compile(
        r"optional subscriptions?"
        r"|one-time unlock(?: option)? and subscription "
        r"(?:options?|plans?|models?)"
        r"|flexible payment options including one-time purchase and subscriptions",
        re.IGNORECASE,
    )
    return {
        str(value)
        for source, value in translations.items()
        if markers.search(str(source))
    }


def sanitize_aim990_optional_claims(
    text: str, locale: str
) -> tuple[str, int]:
    if "Aim990" not in html.unescape(text):
        return text, 0
    safe = pricing_text_for("aim990", locale)
    count = 0
    bad_values = sorted(aim990_bad_translations(locale), key=len)
    for bad in bad_values:
        for candidate, replacement in (
            (bad, safe),
            (html.escape(bad), html.escape(safe)),
        ):
            occurrences = text.count(candidate)
            if occurrences:
                text = text.replace(candidate, replacement)
                count += occurrences

    patterns = (
        re.compile(
            r"(?:both\s+)?(?:a\s+)?one-time unlock(?: option)?"
            r"(?:\s+and|\s+or|\s+plus|\s+alongside)\s+"
            r"(?:optional\s+)?subscription (?:options?|plans?|models?)",
            re.IGNORECASE,
        ),
        re.compile(
            r"one-time or subscription options",
            re.IGNORECASE,
        ),
        re.compile(
            r"flexible payment options including one-time purchase and subscriptions",
            re.IGNORECASE,
        ),
    )
    for pattern in patterns:
        text, replacements = pattern.subn(
            "a one-time unlock with no subscription", text
        )
        count += replacements
    return text, count


def repair_root_alternative_urls(text: str, root_alternatives: Path) -> str:
    root_pattern = re.compile(
        re.escape(f"{SITE}/alternatives/") + r"([^\"'#?]+\.html)"
    )

    def repl(match: re.Match[str]) -> str:
        target = root_alternatives / match.group(1)
        return match.group(0) if target.exists() else f"{SITE}/alternatives/index.html"

    return root_pattern.sub(
        repl,
        replace_legacy_slugs(text, root_alternatives.parent),
    )


def repair_localized_internal_urls(text: str, locale_dir: Path) -> str:
    prefix = f"{SITE}/{locale_dir.name}/"
    pattern = re.compile(re.escape(prefix) + r'([^"\'<>\s]+)')
    pages = locale_dir.parent

    def repl(match: re.Match[str]) -> str:
        suffix = match.group(1)
        parsed = urlsplit(suffix)
        relative = parsed.path
        localized = locale_dir / relative
        if relative.endswith("/"):
            localized /= "index.html"
        if localized.exists():
            return match.group(0)
        fallback = pages / relative
        if relative.endswith("/"):
            fallback /= "index.html"
        if not fallback.exists():
            return match.group(0)
        result = f"{SITE}/{relative}"
        if parsed.query:
            result += f"?{parsed.query}"
        if parsed.fragment:
            result += f"#{parsed.fragment}"
        return result

    return pattern.sub(repl, text)


def repair_html_hreflang(
    path: Path, text: str, pages: Path, locale_names: set[str]
) -> str:
    head = text[:4096].lower()
    if (
        'http-equiv="refresh"' in head
        and 'name="robots" content="noindex' in head
    ):
        return HTML_HREFLANG_BLOCK_RE.sub("", text, count=1)
    try:
        relative = path.relative_to(pages)
    except ValueError:
        return text
    parts = relative.parts
    if not parts:
        return text
    suffix = parts[1:] if parts[0] in locale_names else parts
    if not suffix:
        return text

    candidates: list[tuple[str, Path, str]] = []
    is_directory_index = suffix == ("index.html",)
    if not is_directory_index and suffix[0] not in {
        "answers",
        "guides",
        "stories",
        "alternatives",
    }:
        return text
    if not is_directory_index:
        english = pages.joinpath(*suffix)
        if english.exists():
            english_url = indexable_canonical_url(
                english, f"{SITE}/{'/'.join(suffix)}"
            )
            if english_url:
                candidates.append(("en", english, english_url))
    for locale in sorted(locale_names):
        target = pages / locale
        target = target.joinpath(*suffix)
        if target.exists():
            target_url = indexable_canonical_url(
                target, f"{SITE}/{locale}/{'/'.join(suffix)}"
            )
            if target_url:
                candidates.append(
                    (
                        locale,
                        target,
                        target_url,
                    )
                )
    if not candidates:
        return text
    default_url = (
        f"{SITE}/index.html"
        if is_directory_index
        else next(
            (url for code, _target, url in candidates if code == "en"),
            next(
                (
                    url
                    for code, _target, url in candidates
                    if code == "en-US"
                ),
                candidates[0][2],
            ),
        )
    )
    lines = [
        f'<link rel="alternate" hreflang="{code}" href="{url}">'
        for code, _target, url in candidates
    ]
    lines.append(
        f'<link rel="alternate" hreflang="x-default" href="{default_url}">'
    )
    replacement = "\n" + "\n".join(lines)
    if HTML_HREFLANG_BLOCK_RE.search(text):
        return HTML_HREFLANG_BLOCK_RE.sub(replacement, text, count=1)
    canonical = re.search(r'<link rel="canonical" href="[^"]+">', text)
    if not canonical:
        return text
    return text[: canonical.end()] + replacement + text[canonical.end() :]


def indexable_canonical_url(path: Path, fallback: str) -> str | None:
    head = path.read_text(encoding="utf-8", errors="replace")[:4096]
    if 'name="robots" content="noindex' in head.lower():
        return None
    canonical = re.search(
        r'<link\b[^>]*\brel="canonical"[^>]*\bhref="([^"]+)"[^>]*>',
        head,
        re.IGNORECASE,
    )
    return html.unescape(canonical.group(1)) if canonical else fallback


def scrub_inaccurate_paid_app_offers(text: str) -> str:
    paid_names = {
        str(APPS[key].get("name", "")).casefold()
        for key in PAID_UPFRONT_KEYS
    }
    paid_ids = {
        str(APPSTORE[key]) for key in PAID_UPFRONT_KEYS if key in APPSTORE
    }

    def sanitize_schema(match: re.Match[str]) -> str:
        block = match.group(0)
        start = block.find(">") + 1
        end = block.rfind("</script>")
        try:
            payload = json.loads(block[start:end])
        except (TypeError, ValueError, json.JSONDecodeError):
            return block
        changed = False

        def visit(value: object) -> None:
            nonlocal changed
            if isinstance(value, dict):
                app_type = value.get("@type")
                app_types = (
                    app_type if isinstance(app_type, list) else [app_type]
                )
                serialized = json.dumps(value, ensure_ascii=False).casefold()
                name = str(value.get("name", "")).casefold()
                is_paid_app = any(
                    paid_name and paid_name in name
                    for paid_name in paid_names
                ) or any(f"id{app_id}" in serialized for app_id in paid_ids)
                offers = value.get("offers")
                offer_list = offers if isinstance(offers, list) else [offers]
                has_zero_offer = any(
                    isinstance(offer, dict)
                    and str(offer.get("price", "")).strip()
                    in {"0", "0.0", "0.00"}
                    for offer in offer_list
                )
                if (
                    "SoftwareApplication" in app_types
                    and is_paid_app
                    and has_zero_offer
                ):
                    value.pop("offers", None)
                    changed = True
                for item in value.values():
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        visit(payload)
        if not changed:
            return block
        return (
            block[:start]
            + json.dumps(payload, ensure_ascii=False, indent=2)
            + block[end:]
        )

    return JSON_LD_SCRIPT_RE.sub(sanitize_schema, text)


def internal_link_target(
    href: str, path: Path, pages: Path
) -> Path | None:
    parsed = urlsplit(html.unescape(href))
    if parsed.scheme in {"mailto", "tel", "javascript", "data"}:
        return None
    site = urlsplit(SITE)
    if parsed.scheme or parsed.netloc:
        if parsed.netloc != site.netloc:
            return None
        site_path = site.path.rstrip("/")
        if parsed.path == site_path:
            target = pages / "index.html"
        elif not parsed.path.startswith(f"{site_path}/"):
            return None
        else:
            relative = parsed.path[len(site_path) + 1 :]
            target = pages / relative
    elif parsed.path.startswith("/"):
        site_path = site.path.rstrip("/")
        if parsed.path == site_path:
            target = pages / "index.html"
        elif not parsed.path.startswith(f"{site_path}/"):
            return pages / "__missing_root_path__"
        else:
            target = pages / parsed.path[len(site_path) + 1 :]
    elif parsed.path:
        target = path.parent / parsed.path
    else:
        return None
    if parsed.path.endswith("/"):
        target /= "index.html"
    return target


def remove_missing_html_links(path: Path, text: str, pages: Path) -> str:
    def container_repl(match: re.Match[str]) -> str:
        fragment = match.group(0)
        links = ANCHOR_RE.findall(fragment)
        for _attrs, href, _body in links:
            target = internal_link_target(href, path, pages)
            if target is not None and not target.exists():
                return ""
        return fragment

    updated = LINK_LIST_ITEM_RE.sub(container_repl, text)
    updated = LINK_ARTICLE_RE.sub(container_repl, updated)

    def anchor_repl(match: re.Match[str]) -> str:
        target = internal_link_target(match.group("href"), path, pages)
        if target is not None and not target.exists():
            return match.group("body")
        return match.group(0)

    return ANCHOR_RE.sub(anchor_repl, updated)


def rewrite_html_links(
    path: Path,
    locale: str,
    pages: Path,
    locale_names: set[str],
) -> bool:
    original = path.read_text(encoding="utf-8")
    updated = replace_legacy_slugs(original, pages)
    updated, _ = sanitize_known_aim990_claims(updated, locale)
    updated, _ = sanitize_aim990_optional_claims(updated, locale)
    updated = scrub_inaccurate_paid_app_offers(updated)
    if path.parent.name in {"answers", "guides"}:
        updated = ZERO_PRICE_OFFER_RE.sub("", updated)
        updated = ZERO_PRICE_LAST_OFFER_RE.sub("", updated)
    locale_dir = next(parent for parent in path.parents if parent.name == locale)
    if path.parent.name != "alternatives":
        prefix = f"{SITE}/{locale}/alternatives/"
        pattern = re.compile(re.escape(prefix) + r"([^\"'#?]+)")

        def repl(match: re.Match[str]) -> str:
            target = locale_dir / "alternatives" / match.group(1)
            return match.group(0) if target.exists() else (
                f"{SITE}/alternatives/{match.group(1)}"
            )

        updated = pattern.sub(
            repl,
            updated,
        )
    updated = repair_root_alternative_urls(
        updated, locale_dir.parent / "alternatives"
    )
    updated = repair_localized_internal_urls(updated, locale_dir)
    updated = repair_html_hreflang(
        path, updated, pages, locale_names
    )
    updated = remove_missing_html_links(path, updated, pages)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def rewrite_root_html_links(
    path: Path, pages: Path, locale_names: set[str]
) -> bool:
    original = path.read_text(encoding="utf-8")
    updated = replace_legacy_slugs(original, pages)
    updated = repair_root_alternative_urls(updated, pages / "alternatives")
    updated, _ = sanitize_known_aim990_claims(updated, "en-US")
    updated, _ = sanitize_aim990_optional_claims(updated, "en-US")
    updated = scrub_inaccurate_paid_app_offers(updated)
    if path.parent.name in {"answers", "guides"}:
        updated = ZERO_PRICE_OFFER_RE.sub("", updated)
        updated = ZERO_PRICE_LAST_OFFER_RE.sub("", updated)
    updated = repair_html_hreflang(path, updated, pages, locale_names)
    updated = remove_missing_html_links(path, updated, pages)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def remove_missing_index_items(index_path: Path) -> bool:
    if not index_path.exists():
        return False
    original = index_path.read_text(encoding="utf-8")

    def repl(match: re.Match[str]) -> str:
        href = html.unescape(match.group(1))
        if "://" in href or href.startswith(("/", "#")):
            return match.group(0)
        target = index_path.parent / href.split("?", 1)[0]
        return match.group(0) if target.exists() else ""

    updated = INDEX_ITEM_RE.sub(repl, original)
    if updated == original:
        return False
    index_path.write_text(updated, encoding="utf-8")
    return True


def sitemap_target(pages: Path, url: str, locales: set[str]) -> Path | None:
    parsed = urlsplit(html.unescape(url))
    site = urlsplit(SITE)
    if parsed.netloc != site.netloc:
        return None
    site_path = site.path.rstrip("/")
    if parsed.path == site_path:
        relative = ""
    elif parsed.path.startswith(f"{site_path}/"):
        relative = parsed.path[len(site_path) + 1 :]
    else:
        return None
    if not relative or relative.endswith("/"):
        relative += "index.html"
    return pages / relative


def remove_missing_sitemap_urls(
    sitemap: Path, pages: Path, locales: set[str]
) -> int:
    if not sitemap.exists():
        return 0
    original = sitemap.read_text(encoding="utf-8")
    removed = 0

    def repl(match: re.Match[str]) -> str:
        nonlocal removed
        block = match.group(0)
        loc = re.search(r"<loc>(.*?)</loc>", block, re.DOTALL)
        if not loc:
            return block
        target = sitemap_target(pages, loc.group(1).strip(), locales)
        if target is not None and not target.exists():
            removed += 1
            return ""

        def prune_alternate(alternate: re.Match[str]) -> str:
            nonlocal removed
            alternate_target = sitemap_target(
                pages, alternate.group(1).strip(), locales
            )
            if alternate_target is None or alternate_target.exists():
                return alternate.group(0)
            removed += 1
            return ""

        return SITEMAP_ALT_LINK_RE.sub(prune_alternate, block)

    updated = URL_BLOCK_RE.sub(repl, original)
    if updated != original:
        sitemap.write_text(updated, encoding="utf-8")
    return removed


def owns_unlisted_app(
    path: Path, app_ids: set[str], app_names: set[str] | None = None
) -> bool:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if any(text.count(f"/id{app_id}") >= 2 for app_id in app_ids):
        return True
    names = {name.casefold() for name in (app_names or set())}
    if not names:
        return False

    def contains_unlisted_app(value: object) -> bool:
        if isinstance(value, dict):
            if (
                value.get("@type") == "SoftwareApplication"
                and str(value.get("name", "")).casefold() in names
            ):
                return True
            return any(contains_unlisted_app(item) for item in value.values())
        if isinstance(value, list):
            return any(contains_unlisted_app(item) for item in value)
        return False

    for match in JSON_LD_SCRIPT_RE.finditer(text):
        block = match.group(0)
        start = block.find(">") + 1
        end = block.rfind("</script>")
        try:
            payload = json.loads(block[start:end])
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if contains_unlisted_app(payload):
            return True
    return False


def scrub_unlisted_tool_promotions(
    path: Path, app_ids: set[str], app_names: set[str]
) -> bool:
    original = path.read_text(encoding="utf-8")
    id_markers = {f"/id{app_id}".lower() for app_id in app_ids}
    name_markers = {name.lower() for name in app_names}

    def has_inactive_app(fragment: str) -> bool:
        lowered = html.unescape(fragment).lower()
        return any(marker in lowered for marker in id_markers) or any(
            marker in lowered for marker in name_markers
        )

    updated = JSON_LD_SCRIPT_RE.sub(
        lambda match: "" if has_inactive_app(match.group(0)) else match.group(0),
        original,
    )
    updated = PROMO_BLOCK_RE.sub(
        lambda match: "" if has_inactive_app(match.group(0)) else match.group(0),
        updated,
    )
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def prune_apps_json(path: Path, inactive_ids: set[str]) -> bool:
    if not path.exists():
        return False
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return False
    if not isinstance(records, list):
        return False
    markers = {f"/id{app_id}" for app_id in inactive_ids}
    def rewrite(value: object) -> object:
        if isinstance(value, str):
            return replace_legacy_slugs(value, path.parent)
        if isinstance(value, list):
            return [rewrite(item) for item in value]
        if isinstance(value, dict):
            return {key: rewrite(item) for key, item in value.items()}
        return value

    kept = [
        rewrite(record)
        for record in records
        if not any(marker in json.dumps(record) for marker in markers)
    ]
    if kept == records:
        return False
    path.write_text(
        json.dumps(kept, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return True


def prune_find_app(
    path: Path, inactive_keys: set[str], inactive_names: set[str]
) -> bool:
    if not path.exists():
        return False
    original = path.read_text(encoding="utf-8")

    def sanitize_schema(match: re.Match[str]) -> str:
        block = match.group(0)
        start = block.find(">") + 1
        end = block.rfind("</script>")
        try:
            payload = json.loads(block[start:end])
        except (TypeError, ValueError, json.JSONDecodeError):
            return block
        if payload.get("@type") != "ItemList":
            return block
        items = payload.get("itemListElement")
        if not isinstance(items, list):
            return block
        kept = [
            item
            for item in items
            if not any(
                f"/{key}.html" in json.dumps(item) for key in inactive_keys
            )
        ]
        for position, item in enumerate(kept, 1):
            if isinstance(item, dict):
                item["position"] = position
        payload["itemListElement"] = kept
        return (
            block[:start]
            + json.dumps(payload, ensure_ascii=False, indent=2)
            + block[end:]
        )

    updated = JSON_LD_SCRIPT_RE.sub(sanitize_schema, original)
    for key in inactive_keys:
        updated = re.sub(
            rf'<article\b[^>]*\bid=["\']{re.escape(key)}["\'][^>]*>.*?</article>',
            "",
            updated,
            flags=re.IGNORECASE | re.DOTALL,
        )
        updated = re.sub(
            rf'<a\b[^>]*href=["\']#{re.escape(key)}["\'][^>]*>.*?</a>',
            "",
            updated,
            flags=re.IGNORECASE | re.DOTALL,
        )
    for name in inactive_names:
        updated = re.sub(
            rf"<strong>[^<]+:</strong>\s*{re.escape(name)}\.\s*",
            "",
            updated,
            flags=re.IGNORECASE,
        )
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def cleanup(pages: Path, live_keys: set[str]) -> dict[str, int]:
    locales = locale_dirs(pages)
    locale_names = {path.name for path in locales}
    root_alt = pages / "alternatives"
    unsafe_keys = {
        key
        for key in APPS
        if pricing_profile(key) not in ACCURATE_LEGACY_PROFILES
    }
    unlisted_keys = set(APPSTORE) - live_keys
    inactive_keys = unlisted_keys
    stats = {
        "removed_alternatives": 0,
        "removed_unlisted_pages": 0,
        "removed_unlisted_answers": 0,
        "removed_orphan_answers": 0,
        "removed_stale_roundups": 0,
        "redirected_retired_answers": 0,
        "redirected_hourstag_guides": 0,
        "rewritten_retired_references": 0,
        "rewritten_html": 0,
        "updated_indexes": 0,
        "removed_sitemap_urls": 0,
    }

    unlisted_ids = {APPSTORE[key] for key in unlisted_keys}
    inactive_names = {
        APPS[key]["name"] for key in unlisted_keys if key in APPS
    }

    for key in inactive_keys:
        for exact in (
            pages / f"{key}.html",
            pages / "guides" / f"{key}.html",
            pages / "hubs" / f"{key}.html",
            pages / "stories" / f"{key}.html",
            pages / "stories" / "img" / f"{key}-poster.jpg",
        ):
            if exact.exists():
                exact.unlink()
                stats["removed_unlisted_pages"] += 1
        for alternative in root_alt.glob(f"{key}-*.html"):
            alternative.unlink()
            stats["removed_alternatives"] += 1

    if root_alt.is_dir():
        for legacy_dir in root_alt.iterdir():
            if legacy_dir.is_dir() and LOCALE_RE.fullmatch(legacy_dir.name):
                stats["removed_alternatives"] += sum(
                    1 for _ in legacy_dir.rglob("*.html")
                )
                shutil.rmtree(legacy_dir)

    valid_alternatives = {
        path.name for path in root_alt.glob("*.html") if path.name != "index.html"
    }
    root_answers = pages / "answers"
    if root_answers.is_dir():
        for page in root_answers.glob("*.html"):
            if page.name != "index.html" and owns_unlisted_app(
                page, unlisted_ids, inactive_names
            ):
                page.unlink()
                stats["removed_unlisted_answers"] += 1
    stats["redirected_retired_answers"] = (
        reconcile_retired_answer_redirects(pages, locales)
    )
    stats["redirected_hourstag_guides"] = (
        reconcile_hourstag_guide_redirects(pages, locales)
    )

    for locale_dir in locales:
        alt_dir = locale_dir / "alternatives"
        if alt_dir.is_dir():
            for page in alt_dir.glob("*.html"):
                if page.name == "index.html":
                    continue
                key = app_key_for_alternative(page.name)
                if page.name not in valid_alternatives or key in unsafe_keys:
                    page.unlink()
                    stats["removed_alternatives"] += 1

        for key in inactive_keys:
            app_page = locale_dir / f"{key}.html"
            if app_page.exists():
                app_page.unlink()
                stats["removed_unlisted_pages"] += 1
            guide_page = locale_dir / "guides" / f"{key}.html"
            if guide_page.exists():
                guide_page.unlink()
                stats["removed_unlisted_pages"] += 1
            story_page = locale_dir / "stories" / f"{key}.html"
            if story_page.exists():
                story_page.unlink()
                stats["removed_unlisted_pages"] += 1

        answers = locale_dir / "answers"
        if answers.is_dir():
            for page in answers.glob("*.html"):
                if page.stem in STALE_LOCALIZED_ROUNDUP_SLUGS:
                    page.unlink()
                    stats["removed_stale_roundups"] += 1
                elif page.name != "index.html" and not (
                    pages / "answers" / page.name
                ).exists():
                    page.unlink()
                    stats["removed_orphan_answers"] += 1

        for page in locale_dir.rglob("*.html"):
            if rewrite_html_links(
                page, locale_dir.name, pages, locale_names
            ):
                stats["rewritten_html"] += 1

    for tools_dir in [pages / "tools", *(path / "tools" for path in locales)]:
        if not tools_dir.is_dir():
            continue
        for tool_page in tools_dir.glob("*.html"):
            if scrub_unlisted_tool_promotions(
                tool_page, unlisted_ids, inactive_names
            ):
                stats["rewritten_html"] += 1

    if prune_apps_json(pages / "apps.json", unlisted_ids):
        stats["rewritten_html"] += 1
    if prune_find_app(pages / "find-app.html", inactive_keys, inactive_names):
        stats["rewritten_html"] += 1

    for page in pages.rglob("*.html"):
        relative = page.relative_to(pages)
        if relative.parts and relative.parts[0] in locale_names:
            continue
        if rewrite_root_html_links(page, pages, locale_names):
            stats["rewritten_html"] += 1

    for index_path in pages.rglob("index.html"):
        if "_engine" in index_path.relative_to(pages).parts:
            continue
        if remove_missing_index_items(index_path):
            stats["updated_indexes"] += 1

    for sitemap in pages.glob("sitemap*.xml"):
        stats["removed_sitemap_urls"] += remove_missing_sitemap_urls(
            sitemap, pages, locale_names
        )
    for locale_dir in locales:
        for sitemap in locale_dir.glob("sitemap*.xml"):
            stats["removed_sitemap_urls"] += remove_missing_sitemap_urls(
                sitemap, pages, locale_names
            )
    stats["rewritten_retired_references"] = (
        reconcile_retired_answer_references(pages)
    )
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prune stale localized outreach assets without touching git."
    )
    parser.add_argument(
        "--cached-live",
        action="store_true",
        help="Use the last verified App Store snapshot without a network refresh.",
    )
    args = parser.parse_args()
    live = live_app_keys(APPSTORE, str(PAGES), refresh=not args.cached_live)
    print(json.dumps(cleanup(PAGES, live), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
