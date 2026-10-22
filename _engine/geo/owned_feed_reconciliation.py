#!/usr/bin/env python3
"""GET evidence reconciliation and held, one-shot receipt-state migration."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from email.message import Message
from email.utils import parsedate_to_datetime
import json
import os
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from deployment_generation import validate_binding
import market_availability as market
import owned_app_feeds as feeds
import owned_feed_delivery as delivery
import owned_feed_receipts as receipts
from owned_feed_locale_gate import validate_summary, validate_text

SCHEMA = "lumi.owned-feed-reconciliation/v1"
CLASSES = (
    "content_changed", "missing_ack", "stale_generation",
    "already_acked_current", "endpoint_not_live",
)
SEMANTIC_VERSION = "lumi.owned-feed-semantic-equivalence/v1"


def checked_body(root: Path, observation: dict, *, content_types=None) -> bytes:
    if observation.get("http_status") != 200:
        raise ValueError(f"HTTP {observation.get('http_status')}")
    if observation.get("final_url") != observation["url"] or observation.get("location"):
        raise ValueError("Redirected public endpoint")
    header = Message()
    header["Content-Type"] = observation.get("content_type", "")
    if content_types and header.get_content_type() not in content_types:
        raise ValueError("Wrong public Content-Type")
    charset = header.get_content_charset()
    if charset and charset.casefold() not in {"utf-8", "utf8"}:
        raise ValueError("Public endpoint is not UTF-8")
    path = (root / observation["body_path"]).resolve()
    if root.resolve() not in path.parents:
        raise ValueError("Captured body escapes evidence directory")
    raw = path.read_bytes()
    if len(raw) > feeds.MAX_BYTES or feeds.sha256(raw) != observation.get("body_sha256"):
        raise ValueError("Public body/hash mismatch")
    raw.decode("utf-8", errors="strict")
    return raw


def semantic_feed(locale: str, fmt: str, raw: bytes, roster: dict) -> dict:
    """Ignore only feed/item dates and computed item digests, never public content."""
    if fmt == "json_feed":
        doc = feeds.decode(raw)
        if doc.get("version") != "https://jsonfeed.org/version/1.1":
            raise ValueError("Not a JSON Feed 1.1 document")
        if (
            doc.get("language") != locale or doc.get("feed_url") != feeds.url(feeds.feed_path(locale, fmt))
            or doc.get("home_page_url") != feeds.url(f"{locale}/index.html")
        ):
            raise ValueError("Public feed locale/self URL mismatch")
        title, description = doc.get("title"), doc.get("description")
        items = doc.get("items", [])
        channel_semantics = {key: value for key, value in doc.items() if key != "items"}
        channel_semantics["_owned_feed"] = {
            key: value for key, value in doc.get("_owned_feed", {}).items() if key != "date_modified"
        }
    else:
        root = ET.fromstring(raw)
        items = []
        if fmt == "atom":
            if root.tag != f"{{{feeds.ATOM}}}feed" or root.get(f"{{{feeds.XML}}}lang") != locale:
                raise ValueError("Invalid Atom locale/root")
            def text(node, name):
                return node.findtext(f"{{{feeds.ATOM}}}{name}")
            title, description = text(root, "title"), text(root, "subtitle")
            if text(root, "id") != feeds.url(feeds.feed_path(locale, fmt)):
                raise ValueError("Atom self identity mismatch")
            home = root.find(f"{{{feeds.ATOM}}}link[@rel='alternate']")
            if home is None or home.get("href") != feeds.url(f"{locale}/index.html"):
                raise ValueError("Atom canonical home mismatch")
            feeds.timestamp(text(root, "updated"))
            for node in root.findall(f"{{{feeds.ATOM}}}entry"):
                link = node.find(f"{{{feeds.ATOM}}}link[@rel='alternate']")
                items.append({
                    "id": text(node, "id"), "title": text(node, "title"),
                    "url": link.get("href") if link is not None else None,
                    "summary": text(node, "summary"), "language": locale,
                    "content_html": text(node, "content"),
                    "date_published": text(node, "published"), "date_modified": text(node, "updated"),
                    "_owned_app": feeds.decode((node.findtext(f"{{{feeds.LUMI}}}record") or "").encode()),
                })
        else:
            channel = root.find("channel")
            if root.tag != "rss" or channel is None or channel.findtext("language") != locale:
                raise ValueError("Invalid RSS locale/root")
            title, description = channel.findtext("title"), channel.findtext("description")
            if channel.findtext("link") != feeds.url(f"{locale}/index.html"):
                raise ValueError("RSS canonical home mismatch")
            parsedate_to_datetime(channel.findtext("lastBuildDate"))
            link = channel.find(f"{{{feeds.ATOM}}}link[@rel='self']")
            if link is None or link.get("href") != feeds.url(feeds.feed_path(locale, fmt)):
                raise ValueError("RSS self identity mismatch")
            for node in channel.findall("item"):
                guid = node.find("guid")
                if guid is None or guid.get("isPermaLink") != "false":
                    raise ValueError("RSS GUID is not a stable non-link identity")
                items.append({
                    "id": guid.text, "title": node.findtext("title"), "url": node.findtext("link"),
                    "summary": node.findtext("description"), "language": locale,
                    "content_html": node.findtext(f"{{{feeds.CONTENT}}}encoded"),
                    "date_published": parsedate_to_datetime(node.findtext("pubDate")).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "date_modified": node.findtext(f"{{{feeds.ATOM}}}updated"),
                    "_owned_app": feeds.decode((node.findtext(f"{{{feeds.LUMI}}}record") or "").encode()),
                })
        date_tags = {f"{{{feeds.ATOM}}}updated", f"{{{feeds.ATOM}}}published", "pubDate", "lastBuildDate"}
        for parent in root.iter():
            for child in list(parent):
                if child.tag in date_tags:
                    parent.remove(child)
            if parent.tag == f"{{{feeds.LUMI}}}record":
                metadata = feeds.decode(parent.text.encode())
                parent.text = json.dumps({k: v for k, v in metadata.items() if k != "content_digest"},
                                         ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            elif parent.text is not None and not parent.text.strip():
                parent.text = None
            parent.tail = None
        channel_semantics = ET.canonicalize(ET.tostring(root, encoding="unicode"), rewrite_prefixes=True)
    validate_text(locale, title, "public title")
    validate_text(locale, description, "public disclosure")
    expected = {feeds.item_id(app["app_id"], locale): key for key, app in roster.items()}
    if len(items) != len(expected) or {item.get("id") for item in items} != set(expected):
        raise ValueError("Public GUID/roster coverage mismatch")
    projected = []
    for item in items:
        key = expected[item["id"]]
        if item.get("url") != feeds.url(f"{locale}/{key}.html") or item.get("language") != locale:
            raise ValueError("Public item canonical/locale mismatch")
        if feeds.timestamp(item["date_published"]) > feeds.timestamp(item["date_modified"]):
            raise ValueError("Public item dates are reversed")
        metadata = item.get("_owned_app", {})
        if metadata.get("app_key") != key or metadata.get("app_store_id") != roster[key]["app_id"]:
            raise ValueError("Public item App identity mismatch")
        validate_summary(locale, item["summary"], metadata["purchase_model"])
        validate_text(locale, metadata["publisher_disclosure"], "item disclosure")
        if not isinstance(item.get("content_html"), str) or not item["content_html"]:
            raise ValueError("Missing full public content")
        if market.is_unavailable(locale) and (
            "apps.apple.com" in json.dumps(item, ensure_ascii=False).casefold()
            or metadata.get("market_availability") != market.record_fields(locale)["market_availability"]
        ):
            raise ValueError("Public bn-BD content violates market contract")
        fields = {k: v for k, v in item.items() if k not in ("date_published", "date_modified")}
        fields["_owned_app"] = {k: v for k, v in metadata.items() if k != "content_digest"}
        projected.append(fields)
    return {
        "schema": SEMANTIC_VERSION, "locale": locale, "format": fmt,
        "title": title, "description": description, "channel_semantics": channel_semantics,
        "items": sorted(projected, key=lambda row: row["id"]),
    }


def public_evidence(root: Path, candidate: dict) -> tuple[dict, dict, dict | None]:
    capture = feeds.read_json(root / "capture.json")
    if (
        capture.get("schema") != "lumi.owned-feed-public-capture/v1"
        or capture.get("site") != feeds.SITE or capture.get("network_method") != "GET"
        or capture.get("notification_requests") != 0
        or capture.get("capture_digest") != feeds.digest({k: v for k, v in capture.items() if k != "capture_digest"})
    ):
        raise ValueError("Unverified public capture envelope")
    before = checked_body(root, capture["deployment_before"], content_types={"application/json"})
    after = checked_body(root, capture["deployment_after"], content_types={"application/json"})
    if before != after:
        raise ValueError("Production generation changed during capture")
    production = feeds.decode(before)
    generation = validate_binding(production)
    if capture.get("generation") != generation or capture.get("deployment") != production:
        raise ValueError("Captured production generation/aliases mismatch")
    expected = {
        spec["url"]: (locale, fmt)
        for locale, row in candidate["feeds"].items() for fmt, spec in row["formats"].items()
    }
    rows = capture["endpoints"]
    if len(rows) != 150 or {row["url"] for row in rows} != set(expected):
        raise ValueError("Public capture must cover the exact 150 endpoints")
    results = {}
    for row in rows:
        locale, fmt = expected[row["url"]]
        result = {
            "locale": locale, "format": fmt, "http_status": row.get("http_status"),
            "content_type": row.get("content_type"), "body_sha256": row.get("body_sha256"),
            "observed_at": row.get("observed_at"), "live": False,
        }
        try:
            if row.get("method") != "GET" or row.get("locale") != locale or row.get("format") != fmt:
                raise ValueError("Public observation context mismatch")
            raw = checked_body(root, row, content_types=feeds.CONTENT_TYPES[fmt])
            projection = semantic_feed(locale, fmt, raw, candidate["apps"])
            result.update(live=True, semantic_sha256=feeds.digest(projection), record_count=len(projection["items"]))
        except (ValueError, KeyError, TypeError, OSError, ET.ParseError) as error:
            result["reason"] = str(error)[:200]
        results[row["url"]] = result
    manifest = None
    try:
        raw = checked_body(root, capture["public_manifest"], content_types={"application/json"})
        manifest = feeds.decode(raw)
        if (
            manifest.get("schema") != feeds.SCHEMA
            or manifest.get("generation_digest") != feeds.digest({k: v for k, v in manifest.items() if k != "generation_digest"})
            or set(manifest.get("feeds", {})) != set(candidate["feeds"])
        ):
            raise ValueError("Invalid public exact manifest")
        for locale, row in manifest["feeds"].items():
            for fmt, spec in row["formats"].items():
                topic = feeds.url(feeds.feed_path(locale, fmt))
                if spec["url"] != topic or spec["sha256"] != results[topic]["body_sha256"]:
                    raise ValueError("Public manifest/body generation mismatch")
    except (ValueError, KeyError, TypeError, OSError):
        manifest = None
    context = {
        "generation_id": generation["generation_id"], "source_sha": generation["pages_source_sha"],
        "engine_source_sha": generation["source_sha"],
        "deployment_sha256": feeds.sha256(before),
    }
    if manifest is not None:
        topics = {
            spec["url"]: {
                "sha256": spec["sha256"], "format": fmt, "locale": locale,
                "notification_eligible": row["notification_eligible"], "rsscloud": fmt == "rss",
            }
            for locale, row in manifest["feeds"].items() for fmt, spec in row["formats"].items()
        }
        context["feed_generation_sha256"] = manifest["generation_digest"]
        context["inventory_sha256"] = feeds.digest({
            "generation_digest": manifest["generation_digest"],
            "manifest_sha256": capture["public_manifest"]["body_sha256"], "topics": topics,
        })
    return capture, results, context


def load_history(paths: list[Path]) -> tuple[dict, list, list]:
    records, sources, rejected = {}, [], []
    for path in paths:
        raw = path.read_bytes()
        descriptor = {"path": str(path.resolve()), "sha256": feeds.sha256(raw)}
        try:
            if path.is_symlink() or path.stat().st_mode & 0o777 != 0o600:
                raise ValueError("History must be a private durable state, not an arbitrary receipt")
            state = feeds.decode(raw)
            receipts.validate_state(state)
            if state.get("fixture"):
                raise ValueError("Mock history cannot authorize production")
            for record in state["records"].values():
                if record.get("fixture") or "MOCK_ONLY" in record["response"]["ack_body"]:
                    raise ValueError("Fixture/mock ACK cannot migrate")
            records.update(state["records"])
            sources.append({**descriptor, "records": len(state["records"])})
        except (ValueError, KeyError, TypeError):
            rejected.append({**descriptor, "reason": "unsealed, forged, legacy, or mock history"})
    return records, sources, rejected


def reconcile(pages: Path, capture_root: Path, history: list[Path] = ()) -> dict:
    candidate = feeds.read_manifest(pages)
    current = delivery.inventory(pages)
    capture, public, production = public_evidence(capture_root, candidate)
    records, sources, rejected = load_history(list(history))
    comparisons = {}
    for locale, row in candidate["feeds"].items():
        for fmt, spec in row["formats"].items():
            topic = spec["url"]
            raw = (pages / spec["path"]).read_bytes()
            semantic = feeds.digest(semantic_feed(locale, fmt, raw, candidate["apps"]))
            observed = public[topic]
            proof = {
                "schema": SEMANTIC_VERSION, "topic": topic,
                "production_generation_id": production["generation_id"],
                "production_body_sha256": observed.get("body_sha256"),
                "candidate_body_sha256": spec["sha256"],
                "production_semantic_sha256": observed.get("semantic_sha256"),
                "candidate_semantic_sha256": semantic,
                "equivalent": observed["live"] and observed["semantic_sha256"] == semantic,
                "provider_ack_proven": False,
            }
            proof["proof_digest"] = feeds.digest(proof)
            comparisons[topic] = proof
    entries = []
    for task_id, task in delivery.tasks(current).items():
        topic = task["topic"]
        evidence = public[topic]
        semantic = comparisons[topic]
        candidates = [
            record for record in records.values() if record["accepted_ack"]
            and all(record[name] == task[name] for name in ("protocol", "endpoint", "topic"))
        ]
        exact = []
        for record in candidates:
            prod_task = {**task, **production, "content_sha256": evidence.get("body_sha256")}
            if set(receipts.BINDING_FIELDS) <= production.keys() and receipts.is_current(record, prod_task):
                exact.append(record["receipt_id"])
        if not evidence["live"]:
            classification = "endpoint_not_live"
        elif not semantic["equivalent"]:
            classification = "content_changed"
        elif exact:
            classification = "already_acked_current"
        elif candidates:
            classification = "stale_generation"
        else:
            classification = "missing_ack"
        entries.append({
            "task_id": task_id, **task, "classification": classification,
            "current_receipt_id": exact[-1] if classification == "already_acked_current" else None,
            "historical_receipt_ids": [record["receipt_id"] for record in candidates],
            "semantic_proof_digest": semantic["proof_digest"],
            "release_hold": True,
        })
    counts = {name: sum(row["classification"] == name for row in entries) for name in CLASSES}
    plan = {
        "schema": SCHEMA, "candidate_generation_digest": candidate["generation_digest"],
        "candidate_inventory_sha256": feeds.digest(current),
        "production_binding": production, "capture_digest": capture["capture_digest"],
        "public_coverage": {"attempted": 150, "valid": sum(row["live"] for row in public.values()),
                            "http_statuses": dict(Counter(str(row["http_status"]) for row in public.values()))},
        "feed_count": 150, "record_count": candidate["record_count"], "provider_topic_count": len(entries),
        "classifications": counts, "pending_intents": sum(counts[k] for k in ("content_changed", "missing_ack", "stale_generation")),
        "new_content_intents": counts["content_changed"], "dispatchable_intents": 0,
        "release_hold": True, "public": public, "semantic_proofs": comparisons,
        "history_sources": sources, "rejected_history": rejected,
        "records": records, "entries": entries,
    }
    plan["migration_id"] = feeds.digest({
        "schema": SCHEMA, "candidate": plan["candidate_inventory_sha256"],
        "production": production,
        "public": {url: {k: v for k, v in row.items() if k != "observed_at"} for url, row in public.items()},
        "histories": sorted(row["sha256"] for row in sources + rejected),
    })
    plan["plan_digest"] = feeds.digest(plan)
    return plan


def import_state(pages: Path, capture_root: Path, history: list[Path], state_path: Path) -> dict:
    plan = reconcile(pages, capture_root, history)
    with delivery.locked_state(state_path) as state:
        existing = state.get("migration")
        if existing:
            if existing["migration_id"] != plan["migration_id"]:
                raise ValueError("A different migration needs a new isolated destination; history is preserved")
            return {"replayed": True, **existing}
        if state["pending"] or state["accepted"] or state["records"] or state["in_flight"]:
            raise ValueError("Migration destination must be fresh; supply prior state as history")
        state["records"].update(plan["records"])
        state["legacy_history"].extend(plan["rejected_history"])
        state["prepared"] = {**plan["production_binding"], "include_legacy": False}
        for entry in plan["entries"]:
            key = entry["task_id"]
            if entry["classification"] == "already_acked_current":
                state["accepted"][key] = entry["current_receipt_id"]
            elif entry["classification"] in {"content_changed", "missing_ack", "stale_generation"}:
                state["pending"][key] = {
                    **{name: entry[name] for name in ("protocol", "endpoint", "topic", "content_sha256")},
                    **plan["production_binding"], "attempt_count": 0,
                    "next_attempt_at": 0, "retryable": True, "release_hold": True,
                }
        state["migration"] = {
            "schema": SCHEMA, "migration_id": plan["migration_id"], "plan_digest": plan["plan_digest"],
            "release_hold": True, "hold_reason": "locale/layout release has not authorized dispatch",
            "classifications": plan["classifications"], "pending_intents": plan["pending_intents"],
            "dispatchable_intents": 0, "public_coverage": plan["public_coverage"],
            "semantic_proof_digests": {url: row["proof_digest"] for url, row in plan["semantic_proofs"].items()},
        }
        delivery.save_state(state_path, state)
    return {"replayed": False, **state["migration"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-dir", type=Path, required=True)
    parser.add_argument("--capture-dir", type=Path, required=True)
    parser.add_argument("--history-state", action="append", type=Path, default=[])
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--import-state", type=Path)
    args = parser.parse_args(argv)
    plan = reconcile(args.pages_dir, args.capture_dir, args.history_state)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_bytes(feeds.json_bytes(plan))
    os.chmod(args.report, 0o600)
    result = {k: plan[k] for k in (
        "public_coverage", "classifications", "pending_intents", "new_content_intents",
        "dispatchable_intents", "migration_id",
    )}
    if args.import_state:
        migration = import_state(args.pages_dir, args.capture_dir, args.history_state, args.import_state)
        result["migration"] = {key: migration[key] for key in (
            "migration_id", "replayed", "release_hold", "pending_intents", "dispatchable_intents",
        )}
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
