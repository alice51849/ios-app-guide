"""Reviewed conversion messages, public evidence and observational route records.

This is editorial source, not a purchase tracker. Unknown exposure, attribution
and sales stay unknown; publishing a message does not authorize experiment scale.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import html
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit


HERE = Path(__file__).resolve().parent
SOURCE_PATH = HERE / "data" / "high_intent_conversion_contracts_v1.json"
OUTPUT_RELATIVE = Path("data/high-intent-decision-routes/conversion-contracts.json")
SCHEMA_RELATIVE = Path("data/high-intent-decision-routes/conversion-contracts.schema.json")
TARGETS = {
    "mochi": ("6785004775", "en-US"),
    "lumibopomofo": ("6773017109", "zh-Hant"),
    "scanto": ("6779977651", "en-US"),
    "aim990": ("6784974530", "fr-FR"),
    "lumiweather": ("6779552704", "ja"),
    "mochidonestamp": ("6790800323", "en-US"),
    "cyca": ("6782251621", "en-US"),
    "unblurry": ("6782275018", "en-US"),
    "battai": ("6802423998", "en-US"),
    "notesstudio100": ("6798813048", "en-US"),
    "onepageppt": ("6798814385", "en-US"),
}
COPY_FIELDS = {
    "task", "result", "free", "paid", "limitations", "proof_note", "asset_captions", "queries",
}
CONTRACT_FIELDS = {
    "app_id", "route_slug", "primary_locale", "creative_version",
    "effective_at_utc", "live_app_version", "live_readback_at",
    "offer_readback_at", "offer_readback", "experiment_id",
    "free_feature_ids", "paid_feature_ids", "paid_scope_status",
    "exclude_intents", "published_claim_ids", "proofs", "localized",
}
VERIFIED = {"VERIFIED_PUBLIC_ASSET", "VERIFIED_SHIPPING_DESCRIPTION"}
UNKNOWN = "unknown"
QUERY_EVIDENCE = {
    "status": "candidate",
    "verification_status": "unverified",
    "search_volume": UNKNOWN,
    "ranking": UNKNOWN,
    "published_source": UNKNOWN,
}
UI = {
    "en-US": {
        "free": "Free to start", "paid": "One-time purchase",
        "price": "Local price is shown in the App Store.",
        "limits": "Honest limits", "proof": "What the published evidence shows",
        "source": "Published screenshot",
    },
    "zh-Hant": {
        "free": "免費開始", "paid": "一次性購買",
        "price": "當地售價以 App Store 顯示為準。",
        "limits": "使用限制", "proof": "已核對的公開成果",
        "source": "已發布的商店截圖",
    },
    "fr-FR": {
        "free": "Pour commencer", "paid": "Achat unique",
        "price": "Le prix local est indiqué sur l’App Store.",
        "limits": "Les limites à connaître", "proof": "Ce que montrent les éléments vérifiés",
        "source": "Capture publiée",
    },
    "ja": {
        "free": "無料で試せる範囲", "paid": "一度の購入で解除",
        "price": "お住まいの地域の価格は App Store でご確認ください。",
        "limits": "ご利用前に知っておきたいこと", "proof": "確認できた公開資料",
        "source": "公開済みのスクリーンショット",
    },
    "de-DE": {
        "free": "Kostenlos starten", "paid": "Einmaliger Kauf",
        "price": "Den lokalen Preis finden Sie im App Store.",
        "limits": "Wichtige Grenzen", "proof": "Was die veröffentlichten Nachweise zeigen",
        "source": "Veröffentlichte Bildschirmaufnahme",
    },
}
PRICE_RE = re.compile(r"(?:[$＄€£¥￥]|\b(?:USD|TWD|EUR|JPY)\b)\s*\d|\d[.,]\d{2}\s*(?:dollars?|euros?)", re.I)
UNSAFE_MESSAGES = re.compile(
    r"guaranteed|rescue every|restore every|clinical accuracy|"
    r"official TOEIC|licensed TOEIC|real exam questions|"
    r"battery temperature|per.app battery drain|repair your battery|"
    r"unlimited free (?:PPTX|exports?)|"
    r"garanti.{0,20}990|questions officielles|"
    r"保證.{0,10}(?:990|安全|修復)|必ず.{0,12}(?:直る|安全)|"
    r"既知のない細部を復元",
    re.I,
)


def _timestamp(value: object, *, unknown: bool = False) -> None:
    if unknown and value == UNKNOWN:
        return
    if not isinstance(value, str):
        raise ValueError("Conversion timestamp must be explicit")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("Invalid conversion timestamp") from error
    if parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("Conversion timestamps must use UTC")


def _strings(values: object, label: str, *, minimum: int = 1) -> list[str]:
    if (
        not isinstance(values, list) or len(values) < minimum
        or any(not isinstance(value, str) or not value.strip() for value in values)
        or len(set(values)) != len(values)
    ):
        raise ValueError(f"{label}: distinct nonempty strings required")
    return values


def load_contracts(path: Path = SOURCE_PATH) -> dict[str, dict[str, Any]]:
    source = json.loads(path.read_text(encoding="utf-8"))
    if (
        source.get("schema_version") != 1
        or source.get("scope") != "first_party_outreach_only"
        or set(source.get("apps", {})) != set(TARGETS)
    ):
        raise ValueError("Conversion source must contain the eleven reviewed stable Apps")
    return source["apps"]


def validate(
    route: dict[str, Any],
    app: dict[str, Any],
    contracts: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    key = str(route["app_key"])
    reference = route.get("conversion_contract")
    if key not in TARGETS:
        if reference is not None:
            raise ValueError(f"{key}: unreviewed conversion contract")
        return None
    if reference != key:
        raise ValueError(f"{key}: reviewed conversion source reference is required")
    contract = contracts[key]
    if set(contract) != CONTRACT_FIELDS:
        raise ValueError(f"{key}: conversion fields differ from schema")
    app_id, primary_locale = TARGETS[key]
    if (
        contract["app_id"] != app_id or str(app["app_store_id"]) != app_id
        or contract["route_slug"] != route["route_slug"]
        or contract["primary_locale"] != primary_locale
        or primary_locale not in route["locales"]
        or set(contract["localized"]) != set(route["locales"])
        or app["purchase_model"] != "free_with_lifetime_unlock"
        or app["one_time_option"] is not True
    ):
        raise ValueError(f"{key}: App identity, native locale or purchase model drift")
    for field in ("creative_version", "experiment_id", "live_app_version"):
        if not isinstance(contract[field], str) or not contract[field].strip():
            raise ValueError(f"{key}: missing {field}")
    if key == "aim990" and contract["live_app_version"] != "1.4.2":
        raise ValueError("Aim990 evidence is pinned to shipping 1.4.2, not pending 1.4.3")
    for field in ("live_readback_at", "offer_readback_at"):
        _timestamp(contract[field])
    _timestamp(contract["effective_at_utc"], unknown=True)
    free = _strings(contract["free_feature_ids"], f"{key}.free_feature_ids")
    paid = _strings(contract["paid_feature_ids"], f"{key}.paid_feature_ids", minimum=0)
    if set(free) & set(paid):
        raise ValueError(f"{key}: free and paid capabilities overlap")
    if contract["paid_scope_status"] not in {"VERIFIED", "BLOCKED_EVIDENCE"}:
        raise ValueError(f"{key}: unknown paid scope must be blocked")
    if not paid and contract["paid_scope_status"] != "BLOCKED_EVIDENCE":
        raise ValueError(f"{key}: an unverified paid scope cannot pass")
    _strings(contract["exclude_intents"], f"{key}.exclude_intents", minimum=3)
    claims = _strings(contract["published_claim_ids"], f"{key}.published_claim_ids")
    offer = contract["offer_readback"]
    if (
        not isinstance(offer, dict)
        or set(offer) != {"product_id", "type", "status", "storefronts", "runtime_purchase"}
        or offer["type"] != "NON_CONSUMABLE" or offer["status"] != "APPROVED"
        or offer["runtime_purchase"] != UNKNOWN
        or not offer["product_id"]
    ):
        raise ValueError(f"{key}: invalid observed one-time offer")
    for territory, price in offer["storefronts"].items():
        if territory not in {"USA", "TWN"} or set(price) != {"currency", "amount", "readback_at"}:
            raise ValueError(f"{key}: unreviewed storefront offer")
        if not re.fullmatch(r"\d+(?:\.\d+)?", str(price["amount"])):
            raise ValueError(f"{key}: invalid observed price")
        if price["currency"] != {"USA": "USD", "TWN": "TWD"}[territory]:
            raise ValueError(f"{key}: storefront currency mismatch")
        _timestamp(price["readback_at"])
    proofs = contract["proofs"]
    if not isinstance(proofs, list) or not proofs:
        raise ValueError(f"{key}: proof ledger is required")
    proof_ids: set[str] = set()
    supported: set[str] = set()
    blocked: set[str] = set()
    asset_ids: set[str] = set()
    for proof in proofs:
        if not isinstance(proof, dict) or set(proof) != {
            "id", "status", "claim_ids", "live_app_version", "observed_at",
            "source_url", "source_sha256", "asset", "reason",
        }:
            raise ValueError(f"{key}: proof fields differ from schema")
        if proof["id"] in proof_ids:
            raise ValueError(f"{key}: duplicate proof")
        proof_ids.add(proof["id"])
        if proof["live_app_version"] != contract["live_app_version"]:
            raise ValueError(f"{key}: cross-version proof is forbidden")
        _timestamp(proof["observed_at"])
        _strings(proof["claim_ids"], f"{key}.proof.claim_ids")
        if proof["status"] == "BLOCKED_EVIDENCE":
            blocked.update(proof["claim_ids"])
            if proof["asset"] is not None or not proof["reason"]:
                raise ValueError(f"{key}: blocked evidence cannot provide an output")
        elif proof["status"] in VERIFIED:
            supported.update(proof["claim_ids"])
            source = urlsplit(proof["source_url"])
            if source.scheme != "https" or not (
                source.hostname == "apps.apple.com"
                or re.fullmatch(r"is\d+-ssl\.mzstatic\.com", source.hostname or "")
            ):
                raise ValueError(f"{key}: proof is not an approved public source")
            if not re.fullmatch(r"[0-9a-f]{64}", proof["source_sha256"]):
                raise ValueError(f"{key}: proof digest is missing")
            if proof["status"] == "VERIFIED_PUBLIC_ASSET":
                if not re.fullmatch(r"is\d+-ssl\.mzstatic\.com", source.hostname or ""):
                    raise ValueError(f"{key}: screenshot source must be the reviewed Apple CDN")
                asset = proof["asset"]
                if not isinstance(asset, dict) or set(asset) != {
                    "locale", "width", "height", "reviewed_thumbnail_sha256", "normalization",
                }:
                    raise ValueError(f"{key}: verified asset metadata is missing")
                if asset["locale"] not in UI or min(asset["width"], asset["height"]) <= 0:
                    raise ValueError(f"{key}: invalid localized asset")
                if (
                    asset["normalization"] != "rgb-thumbnail-640-jpeg90"
                    or not re.fullmatch(r"[0-9a-f]{64}", asset["reviewed_thumbnail_sha256"])
                ):
                    raise ValueError(f"{key}: reviewed thumbnail binding is missing")
                asset_ids.add(proof["id"])
            elif (
                proof["asset"] is not None or source.hostname != "apps.apple.com"
                or re.search(rf"/id{app_id}(?:/|$)", source.path) is None
            ):
                raise ValueError(f"{key}: shipping description must name the same stable App")
        else:
            raise ValueError(f"{key}: unsupported proof status")
    declared = set(claims) | set(free) | set(paid)
    if declared - supported or declared & blocked:
        raise ValueError(f"{key}: BLOCKED_EVIDENCE claims cannot be published")
    for locale, copy in contract["localized"].items():
        if locale not in UI or not isinstance(copy, dict) or set(copy) != COPY_FIELDS:
            raise ValueError(f"{key}/{locale}: complete native conversion copy is required")
        for field in ("task", "result", "free", "paid", "proof_note"):
            text = copy[field]
            if not isinstance(text, str) or not text.strip() or "\n" in text:
                raise ValueError(f"{key}/{locale}: incomplete {field}")
        _strings(copy["limitations"], f"{key}/{locale}.limitations")
        _strings(copy["queries"], f"{key}/{locale}.queries")
        visible = " ".join(
            [copy[field] for field in ("task", "result", "free", "paid", "proof_note")]
            + copy["limitations"] + copy["queries"] + list(copy["asset_captions"].values())
        )
        if PRICE_RE.search(visible):
            raise ValueError(f"{key}/{locale}: global hardcoded price is forbidden")
        if UNSAFE_MESSAGES.search(" ".join(copy[field] for field in ("task", "result", "free", "paid"))):
            raise ValueError(f"{key}/{locale}: unsupported result guarantee")
        if key == "onepageppt":
            message = " ".join(copy[field] for field in ("task", "result", "free", "paid")).casefold()
            if "16:9" not in message or re.search(r"whole (?:pitch )?deck", message.replace("not a whole deck", "")):
                raise ValueError("OnePage must describe one 16:9 slide, not a deck")
        if locale == "zh-Hant" and len(re.findall(r"[\u3400-\u9fff]", visible)) < 60:
            raise ValueError(f"{key}/{locale}: English fallback is forbidden")
        if locale == "ja" and len(re.findall(r"[\u3040-\u30ff]", visible)) < 60:
            raise ValueError(f"{key}/{locale}: English fallback is forbidden")
        if locale == "fr-FR" and len(re.findall(r"\b(?:les|des|une|pour|sans|avec|vous|votre|vos|de|un)\b", visible, re.I)) < 12:
            raise ValueError(f"{key}/{locale}: English fallback is forbidden")
        if locale == "de-DE" and len(re.findall(r"\b(?:der|die|das|ein|eine|und|mit|für|ohne|Sie|sich|den|ist|werden|kann)\b", visible, re.I)) < 12:
            raise ValueError(f"{key}/{locale}: English fallback is forbidden")
        expected_assets = {
            proof["id"] for proof in proofs
            if proof["id"] in asset_ids and proof["asset"]["locale"] == locale
        }
        if set(copy["asset_captions"]) != expected_assets:
            raise ValueError(f"{key}/{locale}: localized image captions must match verified assets")
        rule = route["locales"][locale]["decision_rule"]
        if copy["free"] not in rule or copy["paid"] not in rule:
            raise ValueError(f"{key}/{locale}: hero and body free/paid boundary disagree")
    return contract


def materialize(contract: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    locale = record["locale"]
    prices = contract["offer_readback"]["storefronts"]
    territory = {"en-US": "USA", "zh-Hant": "TWN", "fr-FR": "FRA", "ja": "JPN", "de-DE": "DEU"}[locale]
    proof_rows = deepcopy(contract["proofs"])
    has_native_asset = any(
        proof["asset"] and proof["asset"]["locale"] == locale for proof in proof_rows
    )
    return {
        "app_id": contract["app_id"],
        "route_id": record["route_id"],
        "locale": locale,
        "primary_locale": contract["primary_locale"],
        "creative_version": contract["creative_version"],
        "effective_at_utc": contract["effective_at_utc"],
        "live_app_version": contract["live_app_version"],
        "live_readback_at": contract["live_readback_at"],
        "offer_readback_at": contract["offer_readback_at"],
        "offer_readback": {
            "type": contract["offer_readback"]["type"],
            "product_id": contract["offer_readback"]["product_id"],
            "status": contract["offer_readback"]["status"],
            "territory": territory,
            "observed_price": deepcopy(prices.get(territory, UNKNOWN)),
            "runtime_purchase": UNKNOWN,
        },
        "experiment_id": contract["experiment_id"],
        "experiment_type": "directional_observation",
        "attribution": {"source": UNKNOWN, "campaign": UNKNOWN, "purchases": UNKNOWN},
        "outcome": UNKNOWN,
        "scaling_allowed": False,
        "diagnostic_window_days": 14,
        "app_store_url": record["app_store_url"],
        "canonical_url": record["canonical_url"],
        "free_feature_ids": list(contract["free_feature_ids"]),
        "paid_feature_ids": list(contract["paid_feature_ids"]),
        "paid_scope_status": contract["paid_scope_status"],
        "exclude_intents": list(contract["exclude_intents"]),
        "published_claim_ids": list(contract["published_claim_ids"]),
        "query_evidence": deepcopy(QUERY_EVIDENCE),
        "proofs": proof_rows,
        "localized_visual_status": "VERIFIED_PUBLIC_ASSET" if has_native_asset else "BLOCKED_EVIDENCE",
        "copy": deepcopy(contract["localized"][locale]),
    }


def render_sections(record: dict[str, Any]) -> tuple[str, str, str]:
    contract = record.get("conversion_contract")
    if contract is None:
        return "", "", ""
    copy = contract["copy"]
    ui = UI[record["locale"]]
    escape = html.escape
    cta = escape(record["app_store_url"], quote=True)
    # The same two source statements are the hero, body and CTA's accessible
    # offer. There is no separate, drift-prone "free" CTA promise.
    hero = f"""<section class="conversion-hero" data-conversion-hero="true">
<h1>{escape(copy['task'])}</h1>
<p data-conversion-result="true">{escape(copy['result'])}</p>
<div id="conversion-offer" class="conversion-offer">
<p data-offer-free="true"><strong>{escape(ui['free'])}:</strong> {escape(copy['free'])}</p>
<p data-offer-paid="true"><strong>{escape(ui['paid'])}:</strong> {escape(copy['paid'])}</p>
</div>
<a class="cta" data-app-store-cta="true" aria-describedby="conversion-offer" rel="noopener" href="{cta}">{escape(record['store_label'])}</a>
<p class="price-note">{escape(ui['price'])}</p>
</section>"""
    assets = []
    for proof in contract["proofs"]:
        if not proof["asset"] or proof["asset"]["locale"] != record["locale"]:
            continue
        caption = escape(copy["asset_captions"][proof["id"]])
        asset = proof["asset"]
        assets.append(
            f'<figure data-proof-id="{escape(proof["id"], quote=True)}">'
            f'<img loading="lazy" src="{escape(proof["source_url"], quote=True)}" '
            f'width="{asset["width"]}" height="{asset["height"]}" alt="{caption}">'
            f'<figcaption>{caption}</figcaption></figure>'
        )
    blocked = [p["id"] for p in contract["proofs"] if p["status"] == "BLOCKED_EVIDENCE"]
    status = "BLOCKED_EVIDENCE" if blocked or contract["localized_visual_status"] == "BLOCKED_EVIDENCE" else "VERIFIED_PUBLIC_ASSET"
    details = (
        f'<section class="conversion-proof" data-evidence-status="{status}">'
        f'<h2>{escape(ui["limits"])}</h2><ul>'
        + "".join(f"<li>{escape(value)}</li>" for value in copy["limitations"])
        + f'</ul><h2>{escape(ui["proof"])}</h2><p>{escape(copy["proof_note"])}</p>'
        + "".join(assets) + "</section>"
    )
    payload = json.dumps(contract, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    metadata = f'<script type="application/json" id="conversion-route-contract">{payload}</script>'
    return hero, details, metadata


def render_document(records: list[dict[str, Any]], site: str) -> str:
    contracts = [
        record["conversion_contract"]
        for record in sorted(records, key=lambda row: row["route_id"])
        if record.get("conversion_contract")
    ]
    document = {
        "$schema": f"{site}/{SCHEMA_RELATIVE.as_posix()}",
        "schema_version": 1,
        "state": "generated_not_deployed",
        "effective_at_policy": "unknown_until_exact_production_get",
        "measurement_policy": {
            "unknown_is_not_zero": True,
            "baseline_apps": 47,
            "baseline_locales": 50,
            "preserve_existing_cooling_and_hysteresis": True,
            "causal_win_requires": "authorized_randomized_day_30_power_and_multiplicity_gates",
            "automatic_scale": False,
        },
        "routes": contracts,
    }
    return json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_schema() -> str:
    properties = {
        field: {"type": "string", "minLength": 1}
        for field in (
            "app_id", "route_id", "locale", "creative_version", "effective_at_utc",
            "live_app_version", "offer_readback_at", "experiment_id",
        )
    }
    properties.update({
        "app_id": {"enum": [row[0] for row in TARGETS.values()]},
        "outcome": {"const": UNKNOWN},
        "scaling_allowed": {"const": False},
        "experiment_type": {"const": "directional_observation"},
        "offer_readback": {"type": "object"},
        "exclude_intents": {"type": "array", "minItems": 3, "items": {"type": "string"}},
        "proofs": {"type": "array", "minItems": 1},
        "query_evidence": {"type": "object", "const": deepcopy(QUERY_EVIDENCE)},
        "copy": {
            "type": "object", "required": sorted(COPY_FIELDS),
            "additionalProperties": False,
            "properties": {
                **{key: {"type": "string", "minLength": 1} for key in COPY_FIELDS - {"limitations", "asset_captions", "queries"}},
                "limitations": {"type": "array", "minItems": 1, "items": {"type": "string"}},
                "queries": {
                    "type": "array", "minItems": 1, "items": {"type": "string"},
                    "description": (
                        "Unverified candidate task search phrases, not published catalog "
                        "keywords or evidence of search volume, rankings or published sources."
                    ),
                },
                "asset_captions": {"type": "object", "additionalProperties": {"type": "string"}},
            },
        },
    })
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "First-party conversion route observation contract",
        "type": "object",
        "required": ["schema_version", "state", "routes", "measurement_policy"],
        "properties": {
            "schema_version": {"const": 1},
            "state": {"const": "generated_not_deployed"},
            "routes": {
                "type": "array",
                "items": {"type": "object", "required": sorted(properties), "properties": properties},
            },
            "measurement_policy": {"type": "object"},
        },
    }
    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
