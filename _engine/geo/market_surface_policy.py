"""The final owned-surface boundary for evidence-backed unavailable markets."""
from __future__ import annotations

import html
import json
from pathlib import Path
import re

import market_availability as market


STORE = re.compile(r"https?://(?:apps|itunes)\.apple\.com/[^\s<>\"'\\)]*", re.I)
SCRIPT = re.compile(
    r'(<script\b[^>]*\btype=["\']application/(?:ld\+json|json)["\'][^>]*>)(.*?)(</script>)',
    re.I | re.S,
)
NOTE = re.compile(r'<p\b[^>]*class=["\']market-availability["\'][^>]*>.*?</p>', re.I | re.S)
MANAGED = re.compile(
    r"<!-- (app-store-facts(?:-style)?|app-store-qr(?:-card|-head|-style)?|mobile-store-cta|smart-app-banner):start -->"
    r".*?<!-- \1:end -->", re.S,
)
APP_TYPES = {"MobileApplication", "SoftwareApplication"}


def document_locale(source: str, path=None) -> str | None:
    found = re.search(r'<html\b[^>]*\blang=["\']([^"\']+)["\']', source, re.I)
    return found[1] if found else market.locale_from_path(path)


def application_ids(source: str) -> set[str]:
    result = set()
    for match in SCRIPT.finditer(source):
        try:
            payload = json.loads(match[2])
        except ValueError:
            continue
        def visit(value):
            if isinstance(value, dict):
                types = value.get("@type", [])
                types = [types] if isinstance(types, str) else types
                if isinstance(types, list) and APP_TYPES.intersection(types):
                    identity = value.get("identifier", {})
                    if isinstance(identity, dict) and identity.get("propertyID") in {"Apple App Store ID", "App Store ID"}:
                        app_id = str(identity.get("value", ""))
                        if app_id.isdigit():
                            result.add(app_id)
                    result.update(re.findall(r"urn:apple:app:id(\d+)", str(value.get("@id", ""))))
                    for field in ("@id", "url", "installUrl", "downloadUrl"):
                        result.update(re.findall(
                            r"https://(?:apps|itunes)\.apple\.com/(?:[a-z]{2}/)?app/(?:[^/?#]+/)?id(\d+)",
                            str(value.get(field, "")),
                        ))
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)
        visit(payload)
    return result


def unavailable_json(value, locale: str, app_id=None):
    if not market.is_unavailable(locale, app_id):
        return value
    if isinstance(value, list):
        return [unavailable_json(item, locale, app_id) for item in value]
    if not isinstance(value, dict):
        if isinstance(value, str) and ("apps.apple.com" in value or "itunes.apple.com" in value):
            if value == market.record_fields(locale, app_id)["market_availability"]["evidence"]["source_url"]:
                return value
            return None
        return value
    result = {}
    types = value.get("@type", [])
    types = [types] if isinstance(types, str) else types
    application = isinstance(types, list) and bool(APP_TYPES.intersection(types))
    destinations = [value.get(key) for key in ("@id", "url", "sameAs", "installUrl", "downloadUrl")]
    app_ids = re.findall(r"(?:apps|itunes)\.apple\.com/[^\"\s]*?/id(\d+)", json.dumps(destinations, ensure_ascii=False)) if application else []
    identifier = value.get("identifier")
    apple_identity = (
        isinstance(identifier, dict) and identifier.get("propertyID") in {"Apple App Store ID", "App Store ID"}
    ) or str(value.get("@id", "")).startswith("urn:apple:app:id")
    application = application and bool(app_ids or apple_identity)
    for key, child in value.items():
        if (application and key in {"offers", "aggregateRating"}) or (
            key in {"storefront_facts", "app_store_facts"} and child is not None
        ):
            continue
        if application and key in {"installUrl", "downloadUrl", "potentialAction"}:
            continue
        if isinstance(child, dict) and child.get("@type") in ("InstallAction", "BuyAction") and (
            application or "apps.apple.com" in json.dumps(child) or "itunes.apple.com" in json.dumps(child)
        ):
            continue
        identity_ids = re.findall(r"/id(\d+)", child) if key == "@id" and isinstance(child, str) else []
        if identity_ids and "apple.com" in child:
            result[key] = f"urn:apple:app:id{identity_ids[0]}"
        else:
            result[key] = unavailable_json(child, locale, app_id)
    if application:
        if app_ids:
            result["identifier"] = {
                "@type": "PropertyValue", "propertyID": "Apple App Store ID", "value": app_ids[0],
            }
        result.update(market.record_fields(locale, app_id))
    return result


def enforce_html(source: str, locale: str | None, *, app_id=None, name=None) -> str:
    if app_id is None and locale in market.UNAVAILABLE_APP_MARKETS:
        ids = application_ids(source)
        if len(ids) == 1:
            app_id = next(iter(ids))
    if not market.is_unavailable(locale, app_id):
        return source
    original = source
    source = MANAGED.sub("", source)
    source = re.sub(
        r'<meta\b[^>]*name=["\']apple-itunes-app["\'][^>]*>', "", source, flags=re.I
    )
    source = re.sub(
        r'<(?:aside|div)\b[^>]*class=["\'][^"\']*(?:iag-store-facts|app-store-qr-card)[^"\']*["\'][^>]*>.*?</(?:aside|div)>',
        "", source, flags=re.I | re.S,
    )
    def script(match):
        payload = json.loads(match[2])
        payload = unavailable_json(payload, locale, app_id)
        return match[1] + json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + match[3]
    source = SCRIPT.sub(script, source)
    needs_note = NOTE.search(source) is None
    def store_anchor(match):
        nonlocal needs_note
        if needs_note:
            needs_note = False
            return match[1] + market.note_html(locale, name, app_id)
        return match[1]
    source = re.sub(
        r'<a\b[^>]*\bhref=["\']https?://(?:apps|itunes)\.apple\.com/[^"\']*["\'][^>]*>(.*?)</a>',
        store_anchor, source, flags=re.I | re.S,
    )
    source = re.sub(
        r'<a\b[^>]*\bhref=["\'](?:None|null|)["\'][^>]*>.*?</a>',
        "", source, flags=re.I | re.S,
    )
    source = re.sub(
        r'<(?:img|link)\b[^>]*(?:app-store-qr|app-store-facts)[^>]*>', "", source, flags=re.I
    )
    source = re.sub(
        r'\s[\w:-]+=["\'][^"\']*(?:apps|itunes)\.apple\.com[^"\']*["\']', "", source, flags=re.I
    )
    evidence_url = market.record_fields(locale, app_id)["market_availability"]["evidence"]["source_url"]
    evidence_urls = {evidence_url, html.escape(evidence_url, quote=True)}
    source = STORE.sub(lambda match: match[0] if match[0] in evidence_urls else "", source)
    unchecked = source
    for evidence in evidence_urls:
        unchecked = unchecked.replace(evidence, "")
    if "apps.apple.com" in unchecked or "itunes.apple.com" in unchecked:
        raise ValueError("Unprocessed App Store reference in unavailable-market HTML")
    if app_id and str(app_id) not in application_ids(source):
        schema = {
            "@context": "https://schema.org", "@type": "SoftwareApplication",
            "@id": f"urn:apple:app:id{app_id}", "name": name,
            "identifier": {"@type": "PropertyValue", "propertyID": "Apple App Store ID", "value": str(app_id)},
            **market.record_fields(locale, app_id),
        }
        source = source.replace("</head>", '<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False) + "</script></head>", 1)
    existing = NOTE.search(source)
    if existing:
        # Keep the already-localized app name, but upgrade the evidence contract.
        old_text = html.unescape(re.sub("<[^>]+>", "", existing[0]))
        replacement = market.note_html(locale, name, app_id)
        if name is None and len(NOTE.findall(source)) == 1 and old_text.startswith("Apple App Store এখনো বাংলাদেশে"):
            replacement = replacement.replace(html.escape(market.note(locale, app_id=app_id)), html.escape(old_text))
        if len(NOTE.findall(source)) == 1:
            return NOTE.sub(lambda _: replacement, source)
        source = NOTE.sub("", source)
    else:
        replacement = market.note_html(locale, name, app_id)
    if "<amp-story" in source:
        anchor = "</amp-story-grid-layer>"
        source = source.replace(anchor, replacement + anchor, 1)
    else:
        if "</main>" in source:
            position = source.rfind("</main>")
            source = source[:position] + replacement + source[position:]
        else:
            source = source.replace("</body>", replacement + "</body>", 1)
    return original if source == original else source
