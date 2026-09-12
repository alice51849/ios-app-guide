#!/usr/bin/env python3
"""Exact-47 × official-50 owned-email content; never an audience or send receipt."""
from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import io
import json
from pathlib import Path
import re
import string
import subprocess
from urllib.parse import parse_qs, urlencode, urlsplit

from app_store_storefronts import LOCALE_STOREFRONTS, required_campaign_app_store_url
import live_app_manifest
import market_availability as market
from official_locales import OFFICIAL_LOCALES, require_official_locale_coverage
from site_config import PUBLIC_SITE

HERE = Path(__file__).resolve().parent
SCHEMA = "lumi.owned-email-capture/v1"
CAMPAIGN = "app_updates_v1"
CONSENT_VERSION = "owned-email-explicit-v1"
INVENTORY = "data/owned-email/capture-inventory.json"
AVAILABILITY = "data/owned-email/availability.json"
ENDPOINT = "https://buttondown.com/api/emails/embed-subscribe/hourstag"
NEWSLETTER = "hourstag"
PRIVACY_URL = "https://buttondown.com/legal/privacy"
MAX_AGE = 86400
FIELDS = (
    "language", "email_label", "button", "tools_title", "tools_consent",
    "app_title", "app_consent", "confirmation", "privacy", "unsubscribe",
    "disclosure", "preferences", "store",
)
SOURCE_FILES = (
    "owned_email_contract.py", "gen_owned_email_capture.py",
    "owned_email_sender.py", "owned_email_readback.py",
    "owned_email_copy.json", "gen_tool_email_capture.py", "tool_email_capture.json",
    "official_locales.py", "live_app_manifest.py", "live_app_manifest.json",
    "app_store_storefronts.py", "locale_storefronts.json",
    "market_availability.py", "site_config.py",
)
HEX = re.compile(r"[0-9a-f]{64}")
SHA = re.compile(r"[0-9a-f]{40}")


class ContractError(ValueError):
    pass


def utcnow():
    return datetime.now(timezone.utc)


def timestamp(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            raise ValueError("timezone required")
        return result.astimezone(timezone.utc)
    except (AttributeError, TypeError, ValueError) as error:
        raise ContractError("invalid evidence timestamp") from error


def fresh(value, now, maximum=MAX_AGE):
    age = (now - timestamp(value)).total_seconds()
    if not 0 <= age < maximum:
        raise ContractError("stale or future-dated evidence")


def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else json_bytes(value)).hexdigest()


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError("duplicate JSON key")
        result[key] = value
    return result


def parse_json(value):
    def invalid(_):
        raise ContractError("non-finite JSON value")

    try:
        return json.loads(value, object_pairs_hook=_unique, parse_constant=invalid)
    except (TypeError, ValueError, UnicodeError) as error:
        raise ContractError("invalid contract JSON") from error


def load_copy(path=None):
    data = parse_json(Path(path or HERE / "owned_email_copy.json").read_bytes())
    if data.get("schema") != "lumi.owned-email-copy/v1" or data.get("fields") != list(FIELDS):
        raise ContractError("owned email copy schema mismatch")
    locales = data.get("locales")
    if not isinstance(locales, dict):
        raise ContractError("copy locales are missing")
    require_official_locale_coverage("owned email copy", locales)
    result = {}
    for locale, values in locales.items():
        if not isinstance(values, list) or len(values) != len(FIELDS) or any(
            not isinstance(value, str) or not value.strip()
            or any(ord(c) < 32 for c in value) for value in values
        ):
            raise ContractError(f"invalid native copy: {locale}")
        row = dict(zip(FIELDS, values))
        for key, expected in (("app_title", {"app"}),
                              ("app_consent", {"app", "language", "campaign"})):
            actual = {field for _, field, _, _ in string.Formatter().parse(row[key]) if field}
            if actual != expected:
                raise ContractError(f"invalid copy scope fields: {locale}/{key}")
        if "Buttondown" not in row["privacy"] or "Lumi Studio" not in row["disclosure"]:
            raise ContractError(f"missing first-party/provider disclosure: {locale}")
        result[locale] = row
    return result


def roster():
    result = live_app_manifest.canonical_manifest()
    if len(result["apps"]) != 47:
        raise ContractError("owned email requires the exact canonical 47-app roster")
    return result


def scope(row):
    return {key: row[key] for key in ("app_key", "app_id", "locale", "campaign")}


def consent_copy(row, copies=None):
    text = (copies or load_copy())[row["locale"]]
    return {
        "consent": text["app_consent"].format(
            app=row["app_name"], language=text["language"], campaign=row["campaign"],
        ),
        **{key: text[key] for key in ("confirmation", "privacy", "unsubscribe", "disclosure")},
    }


def capture_metadata(row):
    return {
        "owned_app": row["app_key"], "owned_app_id": row["app_id"],
        "owned_locale": row["locale"], "owned_campaign": row["campaign"],
        "owned_consent_version": CONSENT_VERSION,
        "owned_consent_digest": row["consent_digest"],
        "owned_source": row["capture_url"], "owned_consent": "yes",
    }


def source_files(geo=HERE):
    return {name: digest((Path(geo) / name).read_bytes()) for name in SOURCE_FILES}


@lru_cache(maxsize=32)
def committed_source_files(root, revision, prefix):
    requests = "".join(f"{revision}:{prefix}/{name}\n" for name in SOURCE_FILES).encode()
    result = subprocess.run(
        ["git", "-C", str(root), "cat-file", "--batch"],
        input=requests, capture_output=True, check=False,
    )
    if result.returncode:
        raise ContractError("pinned source commit is unavailable")
    stream = io.BytesIO(result.stdout)
    files = {}
    for name in SOURCE_FILES:
        header = stream.readline().split()
        if len(header) != 3 or header[1] != b"blob" or not header[2].isdigit():
            raise ContractError("pinned source revision/file is unavailable")
        length = int(header[2])
        if length > 2 * 1024 * 1024:
            raise ContractError("pinned source file exceeds its size bound")
        body = stream.read(length)
        if len(body) != length or stream.read(1) != b"\n":
            raise ContractError("pinned source Git readback is incomplete")
        files[name] = digest(body)
    if stream.read():
        raise ContractError("unexpected pinned source Git readback")
    return files


@lru_cache(maxsize=8)
def git_context(geo):
    try:
        root = Path(subprocess.check_output(
            ["git", "-C", geo, "rev-parse", "--show-toplevel"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip())
        return root, str(Path(geo).relative_to(root))
    except (subprocess.CalledProcessError, ValueError) as error:
        raise ContractError("source validation requires its Git provenance") from error


def source_binding(geo, repository):
    geo = Path(geo).resolve()
    root, prefix = git_context(str(geo))
    paths = [str((geo / name).relative_to(root)) for name in SOURCE_FILES]
    revision = subprocess.check_output(
        ["git", "-C", str(root), "log", "-1", "--format=%H", "--", *paths], text=True,
    ).strip()
    files = source_files(geo)
    if committed_source_files(str(root), revision, prefix) != files:
        raise ContractError("uncommitted or mismatched source")
    return {"repository": repository, "revision": revision,
            "prefix": str(geo.relative_to(root)), "files": files, "digest": digest(files)}


def paired_sources(growth_geo, guide_geo):
    sources = {
        "growth": source_binding(growth_geo, "alice51849/00_GrowthEngine"),
        "guide": source_binding(guide_geo, "alice51849/ios-app-guide"),
    }
    validate_sources(sources)
    return sources


def validate_sources(sources, geo=HERE):
    if not isinstance(sources, dict) or set(sources) != {"growth", "guide"}:
        raise ContractError("paired Growth and Guide sources are required")
    files = source_files(geo)
    for key, repository, prefix in (
        ("growth", "alice51849/00_GrowthEngine", "geo"),
        ("guide", "alice51849/ios-app-guide", "_engine/geo"),
    ):
        entry = sources[key]
        if (
            not isinstance(entry, dict) or entry.get("repository") != repository
            or entry.get("prefix") != prefix
            or not isinstance(entry.get("revision"), str) or not SHA.fullmatch(entry["revision"])
            or entry.get("files") != files or entry.get("digest") != digest(files)
        ):
            raise ContractError(f"{key} source/digest mismatch")
    root, prefix = git_context(str(Path(geo).resolve()))
    local = sources["growth" if prefix == "geo" else "guide"]
    if prefix not in {"geo", "_engine/geo"} or committed_source_files(
        str(root), local["revision"], prefix,
    ) != files:
        raise ContractError("source Git SHA does not contain the declared content")
    return sources


def lookup_url(country):
    ids = sorted(app["app_id"] for app in roster()["apps"].values())
    return "https://itunes.apple.com/lookup?" + urlencode({
        "id": ",".join(ids), "country": country, "entity": "software", "limit": 200,
    })


def validate_availability(document, now):
    apps = roster()
    if (
        not isinstance(document, dict)
        or document.get("schema") != "lumi.owned-email-availability/v1"
        or document.get("source") != "Apple iTunes Lookup API"
        or document.get("roster_digest") != apps["roster_digest"]
        or type(document.get("ttl_seconds")) is not int
        or not 0 < document["ttl_seconds"] <= MAX_AGE
    ):
        raise ContractError("invalid availability source")
    fresh(document.get("generated_at"), now, document["ttl_seconds"])
    countries = document.get("countries")
    expected = {LOCALE_STOREFRONTS[locale] for locale in OFFICIAL_LOCALES
                if not market.is_unavailable(locale)}
    if not isinstance(countries, dict) or set(countries) != expected:
        raise ContractError("availability must cover every supported storefront")
    ids = sorted(app["app_id"] for app in apps["apps"].values())
    for country, observation in countries.items():
        if not isinstance(observation, dict):
            raise ContractError("invalid storefront observation")
        url = lookup_url(country)
        if (
            type(observation.get("http_status")) is not int
            or observation["http_status"] != 200 or observation.get("url") != url
            or observation.get("final_url") != url
            or not isinstance(observation.get("app_ids"), list)
            or any(not isinstance(app_id, str) or app_id not in ids for app_id in observation["app_ids"])
            or observation["app_ids"] != sorted(set(observation["app_ids"]))
            or not isinstance(observation.get("body_sha256"), str)
            or not HEX.fullmatch(observation["body_sha256"])
        ):
            raise ContractError(f"unverified exact47 storefront: {country}")
        fresh(observation.get("observed_at"), now, document["ttl_seconds"])
        if timestamp(observation["observed_at"]) > timestamp(document["generated_at"]):
            raise ContractError("observation is newer than availability snapshot")
    if countries["us"]["app_ids"] != ids:
        raise ContractError("the canonical 47-app roster is not currently verified sellable")
    return document


def _row(app_key, app, locale, provider, copies, site):
    path = f"{locale}/email/{app_key}.html"
    row = {
        "app_key": app_key, "app_id": app["app_id"], "app_name": app["name"],
        "locale": locale, "campaign": CAMPAIGN,
        "capture_path": path, "capture_url": f"{site}/{path}",
        "storefront": LOCALE_STOREFRONTS[locale],
        "app_store_url": None, "conversion_campaign": "N/A",
        **market.record_fields(locale),
    }
    row["scope_digest"] = digest(scope(row))
    row["consent_digest"] = digest(consent_copy(row, copies))
    if not market.is_unavailable(locale):
        token = f"em_{app['app_id']}_{locale.replace('-', '')}_{digest(CAMPAIGN)[:6]}"
        row["app_store_url"] = required_campaign_app_store_url(
            f"https://apps.apple.com/{row['storefront']}/app/id{app['app_id']}",
            token, provider_token=provider, expected_locale=locale,
            expected_app_id=app["app_id"],
        )
        row["conversion_campaign"] = token
    return row


def rows(provider, site=PUBLIC_SITE):
    if not isinstance(provider, str) or not re.fullmatch(r"[0-9]{1,20}", provider):
        raise ContractError("a real pt provider token is required; no untracked fallback")
    if site != PUBLIC_SITE:
        raise ContractError("capture URLs must use the first-party canonical site")
    copies = load_copy()
    result = []
    for app_key, app in roster()["apps"].items():
        for locale in OFFICIAL_LOCALES:
            result.append(_row(app_key, app, locale, provider, copies, site))
    return result


def verified_conversion_cells(availability):
    return sum(
        app["app_id"] in availability["countries"][LOCALE_STOREFRONTS[locale]]["app_ids"]
        for app in roster()["apps"].values() for locale in OFFICIAL_LOCALES
        if not market.is_unavailable(locale)
    )


def make_inventory(provider, sources, availability, content_hashes, *, now=None):
    now = now or utcnow()
    validate_sources(sources)
    validate_availability(availability, now)
    records = rows(provider)
    for row in records:
        row["content_sha256"] = content_hashes[row["capture_path"]]
    result = {
        "schema": SCHEMA, "generated_at": now.isoformat(), "ttl_seconds": MAX_AGE,
        "sources": sources, "availability_digest": digest(availability),
        "roster_digest": roster()["roster_digest"], "provider_token": provider,
        "app_count": 47, "locale_count": 50, "capture_count": 2350,
        "conversion_cells": 2303, "not_applicable_cells": 47,
        "verified_conversion_cells": verified_conversion_cells(availability),
        "unverified_conversion_cells": 2303 - verified_conversion_cells(availability),
        "evidence_level": "content_ready_not_subscriber_or_delivery",
        "verified_subscribers": 0, "subscriber_count": "UNKNOWN", "native_email_count": 0,
        "rows": records,
    }
    result["content_digest"] = digest(result)
    return result


def validate_inventory(document, availability, *, now=None, geo=HERE):
    now = now or utcnow()
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        raise ContractError("invalid capture inventory schema")
    claimed = document.get("content_digest")
    if not isinstance(claimed, str) or not HEX.fullmatch(claimed):
        raise ContractError("missing inventory digest")
    if digest({key: value for key, value in document.items() if key != "content_digest"}) != claimed:
        raise ContractError("inventory digest mismatch")
    validate_sources(document.get("sources"), geo)
    validate_availability(availability, now)
    if document.get("availability_digest") != digest(availability):
        raise ContractError("availability source digest mismatch")
    if type(document.get("ttl_seconds")) is not int or not 0 < document["ttl_seconds"] <= MAX_AGE:
        raise ContractError("invalid inventory TTL")
    fresh(document.get("generated_at"), now, document["ttl_seconds"])
    if timestamp(document["generated_at"]) < timestamp(availability["generated_at"]):
        raise ContractError("inventory predates its availability source")
    for field, value in {
        "app_count": 47, "locale_count": 50, "capture_count": 2350,
        "conversion_cells": 2303, "not_applicable_cells": 47,
        "verified_conversion_cells": verified_conversion_cells(availability),
        "unverified_conversion_cells": 2303 - verified_conversion_cells(availability),
        "verified_subscribers": 0, "subscriber_count": "UNKNOWN", "native_email_count": 0,
        "evidence_level": "content_ready_not_subscriber_or_delivery",
        "roster_digest": roster()["roster_digest"],
    }.items():
        if type(document.get(field)) is not type(value) or document[field] != value:
            raise ContractError(f"content counts cannot claim subscriber/native evidence: {field}")
    expected = rows(document.get("provider_token"))
    records = document.get("rows")
    if not isinstance(records, list) or len(records) != len(expected):
        raise ContractError("capture inventory must contain exactly 2350 rows")
    for wanted, actual in zip(expected, records):
        if (
            not isinstance(actual, dict)
            or {key: value for key, value in actual.items() if key != "content_sha256"} != wanted
            or not isinstance(actual.get("content_sha256"), str)
            or not HEX.fullmatch(actual["content_sha256"])
        ):
            raise ContractError("capture App/locale/campaign/content/CTA binding mismatch")
    return document


def inventory_row(inventory, app_key, locale, campaign=CAMPAIGN):
    matches = [row for row in inventory["rows"] if (
        row["app_key"], row["locale"], row["campaign"]
    ) == (app_key, locale, campaign)]
    if len(matches) != 1:
        raise ContractError("App/locale/campaign must identify exactly one capture")
    return matches[0]


def validate_row(row):
    try:
        provider = parse_qs(urlsplit(row["app_store_url"]).query)["pt"][0] \
            if row.get("app_store_url") else "1"
        expected = _row(
            row["app_key"], roster()["apps"][row["app_key"]], row["locale"],
            provider, load_copy(), PUBLIC_SITE,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ContractError("invalid scoped capture") from error
    if {key: value for key, value in row.items() if key != "content_sha256"} != expected:
        raise ContractError("capture scope or consent changed")
    return row
