#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regenerate topic-matched answer pages with fresh, specific facts.

Fully automatic (no OpenAI key). For every (app, query) whose question maps to a
known topic (per-country passport specs, per-country resume formats, task
scenarios), (re)write the page using answer_facts — upgrading the earlier
generic-boilerplate pages into pages that actually answer the question, and
filling any missing topic pages. Never touches git.

Usage:
    python3 regen_facts.py            # upgrade all topic-matched pages
    python3 regen_facts.py --dry-run  # report what would change, write nothing
"""
from __future__ import annotations

import argparse
import json

import aeo_answers as A
import answer_facts


def run(dry_run: bool = False) -> dict:
    upgraded: list[str] = []
    created: list[str] = []
    failed: list[str] = []
    seen: set[str] = set()
    for key, qlist in A.queries.ALL.items():
        if key not in A.APPS:
            continue
        app = A.APPS[key]
        for q in qlist:
            if not A.is_english_answer_question(q):
                continue
            slug = A.slugify(q)
            if slug in seen:
                continue
            seen.add(slug)
            if answer_facts.topic_facts(q, key, app) is None:
                continue  # only touch topic-matched pages
            path = A.ANSWERS_DIR / f"{slug}.html"
            existed = path.exists()
            if dry_run:
                (upgraded if existed else created).append(slug)
                continue
            try:
                content = A.normalized_content(A.default_content(q, key), q, key)
                path.write_text(A.render_page(q, key, content), encoding="utf-8")
                (upgraded if existed else created).append(slug)
            except Exception as exc:  # noqa: BLE001
                failed.append(f"{slug}: {exc}")
    if not dry_run:
        A.regenerate_index()
        A.write_sitemap()
    summary = {
        "upgraded": len(upgraded),
        "created": len(created),
        "failed": len(failed),
        "sample_new": created[:6],
        "sample_upgraded": upgraded[:6],
        "failures": failed[:5],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Regenerate topic-matched answer pages with fresh facts.")
    ap.add_argument("--dry-run", action="store_true", help="Report only; write nothing.")
    run(dry_run=ap.parse_args().dry_run)
