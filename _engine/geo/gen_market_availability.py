"""Materialize the unavailable-market contract without removing owned content."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import market_availability as market
import market_surface_policy as policy


URL_FIELDS = {
    "app_store_url", "canonical_app_store_url", "_lumi_app_store_url",
    "storefront_url", "installUrl", "downloadUrl",
}


def rewrite_document(value, locale=None):
    if isinstance(value, list):
        return [rewrite_document(child, locale) for child in value]
    if not isinstance(value, dict):
        return policy.unavailable_json(value, locale) if market.is_unavailable(locale) else value
    declared = next((
        value.get(field) for field in ("locale", "lang", "language", "inLanguage", "_lumi_locale")
        if isinstance(value.get(field), str)
    ), None)
    local = declared or locale
    app_id = value.get("app_store_id", value.get("app_id"))
    result = {
        key: rewrite_document(child, key if key in market.UNAVAILABLE_MARKETS else local)
        for key, child in value.items()
    }
    if market.is_unavailable(local, app_id):
        result = policy.unavailable_json(result, local, app_id)
        if URL_FIELDS.intersection(value):
            for field in URL_FIELDS.intersection(value):
                result[field] = None
            result.update(market.record_fields(local, app_id))
        if market.is_unavailable(local) and isinstance(value.get("version"), str) and "jsonfeed.org" in value["version"]:
            result["items"] = []
            if "_lumi_catalog" in result:
                result["_lumi_catalog"].update(market.record_fields(local))
            else:
                result["_market_availability"] = market.record_fields(local)["market_availability"]
    if result.get("records") != value.get("records") and "content_digest" in value:
        result["content_digest"] = hashlib.sha256(json.dumps(
            result["records"], ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()).hexdigest()
    return result


def _paths(pages):
    for directory, dirs, files in os.walk(pages):
        dirs[:] = sorted(name for name in dirs if not name.startswith((".", "_")))
        for name in sorted(files):
            path = Path(directory) / name
            if not path.is_symlink() and not name.startswith("."):
                yield path


def generate(pages: Path, *, check=False, paths=None):
    changed = []
    checked = 0
    candidates_to_check = [pages / path for path in paths] if paths is not None else _paths(pages)
    for path in candidates_to_check:
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(pages.resolve()):
            raise ValueError(f"Not an existing owned file: {path}")
        relative = path.relative_to(pages)
        locale = market.locale_from_path(relative)
        if path.suffix not in {".html", ".json", ".jsonld", ".xml", ".md", ".txt", ".csv"}:
            continue
        if locale is None and path.suffix not in {".json", ".jsonld", ".csv"}:
            continue
        source = path.read_text(encoding="utf-8")
        if locale is None and "bn-BD" not in source and not (
            "zh-Hans" in source and any(
                app_id in source for app_id in market.UNAVAILABLE_APP_MARKETS["zh-Hans"]
            )
        ):
            continue
        checked += 1
        updated = source
        if path.suffix == ".html":
            updated = policy.enforce_html(source, locale)
        elif path.suffix in {".json", ".jsonld"}:
            original = json.loads(source)
            document = rewrite_document(original, locale)
            if document != original:
                indent = 2 if "\n  " in source else 4 if "\n    " in source else None
                updated = json.dumps(document, ensure_ascii=False, indent=indent) + ("\n" if source.endswith("\n") else "")
        elif path.suffix == ".csv":
            reader = csv.DictReader(io.StringIO(source))
            fields = reader.fieldnames or []
            rows = list(reader)
            if "locale" in fields and any(market.is_unavailable(row["locale"]) for row in rows):
                if "market_availability" not in fields:
                    fields = [*fields, "market_availability"]
                for row in rows:
                    if not market.is_unavailable(row["locale"]):
                        continue
                    for field in URL_FIELDS.intersection(row):
                        row[field] = ""
                    row["market_availability"] = json.dumps(
                        market.record_fields(row["locale"])["market_availability"], ensure_ascii=False
                    )
                output = io.StringIO(newline="")
                writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
                updated = output.getvalue()
        elif market.is_unavailable(locale):
            if path.suffix == ".xml":
                root = ET.fromstring(source)
                for node in root.iter():
                    for key, value in list(node.attrib.items()):
                        if "apps.apple.com" in value or "itunes.apple.com" in value:
                            del node.attrib[key]
                    if node.text and ("apps.apple.com" in node.text or "itunes.apple.com" in node.text):
                        if "<" in node.text:
                            wrapped = policy.enforce_html("<html><head></head><body>" + node.text + "</body></html>", locale)
                            node.text = wrapped.split("<body>", 1)[1].rsplit("</body>", 1)[0]
                        else:
                            node.text = policy.STORE.sub("", node.text)
                updated = ET.tostring(root, encoding="unicode") + "\n"
                if "apps.apple.com" not in source and "itunes.apple.com" not in source:
                    updated = source
            else:
                updated = policy.STORE.sub("", source)
        if updated != source:
            changed.append(relative.as_posix())
            if not check:
                path.write_text(updated, encoding="utf-8")
    candidates = {
        path.name: path for path in (pages / "assets/app-store-qr").glob("*.svg")
        if "apps.apple.com/bd/" in path.read_text(encoding="utf-8")
    }
    references = {}
    if candidates:
        for path in _paths(pages):
            if path.suffix not in {".html", ".json", ".jsonl", ".xml", ".md", ".txt", ".csv"}:
                continue
            source = path.read_text(encoding="utf-8")
            for name in set(re.findall(r"id\d+-[a-f0-9]+\.svg", source)).intersection(candidates):
                references.setdefault(name, []).append(str(path.relative_to(pages)))
        if references:
            raise ValueError(f"Unavailable QR still referenced: {references}")
        for path in candidates.values():
            changed.append(path.relative_to(pages).as_posix())
            if not check:
                path.unlink()
    return {"checked": checked, "changed": len(changed), "paths": changed}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--path", action="append", help="Only refresh these existing relative paths.")
    args = parser.parse_args()
    report = generate(args.pages, check=args.check, paths=args.path)
    print(json.dumps(report, ensure_ascii=False))
    return int(args.check and report["changed"] > 0)


if __name__ == "__main__":
    raise SystemExit(main())
