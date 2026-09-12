#!/usr/bin/env python3
"""Regenerate shared external layout assets without regenerating content.

App UI single-line rules do not apply to publisher CTA/caption text. This
layout-only entry point retains every text value, price, claim and URL, and
uses the same asset constants and direction transform as the normal producers.
"""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path

import gen_app_decision_cards
import gen_app_store_facts
import gen_app_store_qr_ctas
import gen_guide_design
import gen_mobile_store_ctas
import gen_hubs
import app_install_decision_routes
from outreach_bidi import isolate_document


class _Content(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text = []
        self.links = []
        self.copy_attributes = []
        self.scripts = []
        self.skip = 0
        self.in_script = False

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag in {"style", "script"}:
            self.skip += 1
        if tag == "script":
            self.in_script = True
        for field in ("href", "src"):
            if field in values:
                self.links.append((tag, field, values[field]))
        for field in ("title", "aria-label", "alt", "value"):
            if field in values:
                self.copy_attributes.append((tag, field, values[field]))
        if tag == "meta":
            self.copy_attributes.append((tag, values.get("name", values.get("property")), values.get("content")))

    def handle_endtag(self, tag):
        if tag in {"style", "script"}:
            self.skip -= 1
        if tag == "script":
            self.in_script = False

    def handle_data(self, data):
        if not self.skip:
            self.text.append(data)
        elif self.in_script:
            self.scripts.append(data)


def content_signature(source):
    parser = _Content()
    parser.feed(source)
    return "".join(parser.text), parser.links, parser.copy_attributes, parser.scripts


def generate(pages, paths):
    pages = Path(pages).resolve()
    assets = {
        gen_guide_design.ASSET_RELATIVE: gen_guide_design.STYLESHEET,
        gen_app_decision_cards.ASSET_RELATIVE: gen_app_decision_cards.STYLESHEET,
        gen_mobile_store_ctas.ASSET_RELATIVE: gen_mobile_store_ctas.SCRIPT,
        Path("assets") / gen_app_store_facts.ASSET_NAME: gen_app_store_facts.ASSET_SOURCE,
        gen_app_store_qr_ctas.STYLESHEET_RELATIVE: gen_app_store_qr_ctas.CSS,
    }
    changed = sum(gen_guide_design._write_if_changed(pages / relative, source) for relative, source in assets.items())
    checked = 0
    for relative in paths:
        path = (pages / relative).resolve()
        if pages not in path.parents or path.suffix != ".html":
            raise ValueError(f"Layout target escaped its pages owner: {relative}")
        source = path.read_text(encoding="utf-8")
        updated = gen_hubs.regenerate_layout(source)
        updated = app_install_decision_routes.regenerate_layout(updated)
        updated = isolate_document(updated)
        if content_signature(source) != content_signature(updated):
            raise ValueError(f"Layout-only pass changed content: {relative}")
        changed += gen_guide_design._write_if_changed(path, updated, previous=source)
        checked += 1
    return {"pages": checked, "assets": len(assets), "changed_files": changed, "copy_changes": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=Path, required=True)
    parser.add_argument("paths", nargs="+")
    args = parser.parse_args()
    print(generate(args.pages, args.paths))


if __name__ == "__main__":
    main()
