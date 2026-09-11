#!/usr/bin/env python3
"""Source-owned public email directives and a strict rendered HTML gate."""

from __future__ import annotations

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess


PUBLIC_CONTACT = "hourstag.app@gmail.com"
EMAIL = re.compile(
    r"(?<![A-Za-z0-9.!#$%&'*+/=?^_`{|}~-])"
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@[A-Za-z0-9.-]{1,253}\.[A-Za-z]{2,63}"
)
OPEN = "<!--email_off-->"
CLOSE = "<!--/email_off-->"
EXCLUDED = frozenset({"head", "script", "noscript", "textarea", "xmp"})


def digest(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def email_text(value: str) -> str:
    """Escape ordinary visible text, then protect its unchanged email addresses."""
    output, cursor = [], 0
    for match in EMAIL.finditer(value):
        output.extend((html.escape(value[cursor:match.start()]),
                       OPEN + html.escape(match.group()) + CLOSE))
        cursor = match.end()
    output.append(html.escape(value[cursor:]))
    return "".join(output)


class EmailMarkup(HTMLParser):
    def __init__(self, source: str):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.line_offsets = [0]
        for line in source.splitlines(keepends=True):
            self.line_offsets.append(self.line_offsets[-1] + len(line))
        self.excluded = []
        self.active = None
        self.regions = []
        self.issues = []
        self.visible_emails = []
        self.render_spans = []
        self.pending_text = None
        self.feed(source)
        self.close()
        self.finish_text(len(source))
        if self.active is not None:
            self.issues.append({"kind": "unclosed_email_off", "offset": self.active["start"]})

    def source_offset(self):
        line, column = self.getpos()
        return self.line_offsets[line - 1] + column

    def finish_text(self, end):
        if self.pending_text is not None:
            self.render_spans.append((self.pending_text, end))
            self.pending_text = None

    def inspect(self, value, context):
        for match in EMAIL.finditer(value):
            email = match.group()
            self.visible_emails.append(email)
            if self.active is None:
                self.issues.append({
                    "kind": "unprotected_public_email", "email": email,
                    "offset": self.source_offset(), "context": context,
                })
            else:
                self.active["emails"].append(email)

    def handle_starttag(self, tag, attrs):
        self.finish_text(self.source_offset())
        if tag in EXCLUDED:
            self.excluded.append(tag)
        if not self.excluded and tag == "a":
            hrefs = [value for key, value in attrs if key == "href"]
            if len(hrefs) > 1:
                self.issues.append({"kind": "duplicate_anchor_href", "offset": self.source_offset()})
            for href in hrefs:
                if self.active is None and EMAIL.search(href or ""):
                    start = self.source_offset()
                    self.render_spans.append((start, start + len(self.get_starttag_text())))
                self.inspect(href or "", "anchor_href")

    def handle_endtag(self, tag):
        self.finish_text(self.source_offset())
        if tag in self.excluded:
            index = len(self.excluded) - 1 - self.excluded[::-1].index(tag)
            self.excluded = self.excluded[:index]

    def handle_data(self, data):
        self.finish_text(self.source_offset())
        if not self.excluded:
            if self.active is None and EMAIL.search(data):
                self.pending_text = self.source_offset()
            self.inspect(data, "visible_text")

    def handle_comment(self, data):
        self.finish_text(self.source_offset())
        if data.strip() not in {"email_off", "/email_off"}:
            return
        offset = self.source_offset()
        marker = OPEN if data.strip() == "email_off" else CLOSE
        if self.excluded or not self.source.startswith(marker, offset):
            self.issues.append({"kind": "ambiguous_email_off", "offset": offset})
            return
        if marker == OPEN:
            if self.active is not None:
                self.issues.append({"kind": "nested_email_off", "offset": offset})
            else:
                self.active = {"start": offset, "open_end": offset + len(OPEN), "emails": []}
        elif self.active is None:
            self.issues.append({"kind": "unmatched_email_off_close", "offset": offset})
        else:
            region = {**self.active, "close_start": offset, "end": offset + len(CLOSE)}
            if not region["emails"]:
                self.issues.append({"kind": "email_off_without_visible_email", "offset": region["start"]})
            self.regions.append(region)
            self.active = None


def render_html(source: str) -> str:
    """The publisher's deterministic final rendering pass; it never changes content."""
    parsed = EmailMarkup(source)
    invalid = [issue for issue in parsed.issues if issue["kind"] != "unprotected_public_email"]
    if invalid:
        raise ValueError("Cannot render malformed email directives: " + json.dumps(invalid[:4]))
    result = source
    for start, end in sorted(set(parsed.render_spans), reverse=True):
        result = result[:start] + OPEN + result[start:end] + CLOSE + result[end:]
    checked = EmailMarkup(result)
    if checked.issues:
        raise ValueError("Public email rendering did not close every visible address")
    if canonical_html(result) != canonical_html_unchecked(source):
        raise ValueError("Public email rendering changed non-directive source bytes")
    return result


def canonical_html_unchecked(source: str) -> str:
    parsed = EmailMarkup(source)
    invalid = [issue for issue in parsed.issues if issue["kind"] != "unprotected_public_email"]
    if invalid:
        raise ValueError("Malformed source email directives")
    result = source
    for region in reversed(parsed.regions):
        result = (
            result[:region["start"]]
            + result[region["open_end"]:region["close_start"]]
            + result[region["end"]:]
        )
    return result


def canonical_html(source: str) -> str:
    """Consume only balanced source directives; hash every byte of their contents."""
    parsed = EmailMarkup(source)
    if parsed.issues:
        raise ValueError("Rendered public email is not safely source-protected: " + json.dumps(parsed.issues[:4]))
    result = source
    for region in reversed(parsed.regions):
        result = (
            result[:region["start"]]
            + result[region["open_end"]:region["close_start"]]
            + result[region["end"]:]
        )
    return result


def source_record(source: str) -> dict:
    canonical = canonical_html(source)
    return {
        "source_sha256": digest(source.encode()),
        "canonical_sha256": digest(canonical.encode()),
        "policy": "source-email-off-v1",
        "directive_count": source.count(OPEN),
    }


def verify_body(body: bytes, source: str, record: dict, *, site: str, relative: str) -> dict:
    from deployment_generation import EDGE_SITE, GenerationError, verify_output_bytes

    expected = source_record(source)
    if record != expected:
        raise ValueError("Email receipt is not bound to the exact source and canonical digests")
    try:
        proof = verify_output_bytes(
            body, site=site, relative=relative, expected_sha256=expected["source_sha256"],
        )
        method = "source_exact"
    except GenerationError:
        if site != EDGE_SITE or not expected["directive_count"]:
            raise
        proof = verify_output_bytes(
            body, site=site, relative=relative, expected_sha256=expected["canonical_sha256"],
        )
        method = "source_bound_email_off"
    return {
        **proof, "source_sha256": expected["source_sha256"],
        "canonical_sha256": expected["canonical_sha256"], "email_method": method,
    }


def scan(pages: Path, *, render: bool = False) -> dict:
    checked = 0
    failures = []
    protected = {}
    changed = []
    for directory, names, files in os.walk(pages):
        names[:] = [name for name in names if name not in {".git", ".github", "_engine", "node_modules"}]
        for name in files:
            if not name.endswith(".html"):
                continue
            path = Path(directory) / name
            relative = path.relative_to(pages).as_posix()
            checked += 1
            if path.is_symlink():
                failures.append({"path": relative, "issues": [{"kind": "symlink_html"}]})
                continue
            source = path.read_text(encoding="utf-8")
            if "email_off" not in source and EMAIL.search(html.unescape(source)) is None:
                continue
            parsed = EmailMarkup(source)
            if render and parsed.issues:
                updated = render_html(source)
                if updated != source:
                    path.write_text(updated, encoding="utf-8")
                    changed.append(relative)
                    source = updated
                    parsed = EmailMarkup(source)
            if parsed.issues:
                failures.append({"path": relative, "issues": parsed.issues})
            elif parsed.regions:
                protected[relative] = source_record(source)
    return {
        "schema_version": 1, "html_checked": checked,
        "protected_html": protected, "failures": failures, "passed": not failures,
        "policy": "source-email-off-v1",
        "changed_files": changed,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--render", action="store_true")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--generation-file", type=Path)
    args = parser.parse_args()
    report = scan(args.pages_dir, render=args.render)
    if report["passed"] and args.manifest:
        document = {
            "schema_version": 1, "policy": report["policy"],
            "html_checked": report["html_checked"],
            "protected_html": report["protected_html"],
        }
        serialized = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        document["manifest_sha256"] = digest(serialized.encode())
        text = json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        if args.render:
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            args.manifest.write_text(text)
        elif not args.manifest.is_file() or args.manifest.read_text() != text:
            raise ValueError("Rendered email manifest does not match the exact source bytes")
        report["output_manifest_sha256"] = digest(args.manifest.read_bytes())
    if args.generation_file:
        from deployment_generation import parse_json, validate_binding

        document = parse_json(args.generation_file.read_bytes())
        generation = validate_binding(document)
        revision = subprocess.check_output(
            ["git", "-C", str(args.pages_dir), "rev-parse", "HEAD"],
            text=True, timeout=20,
        ).strip()
        if generation["pages_source_sha"] != revision or document["source_commit"] != revision:
            raise ValueError("Rendered email report cannot reuse an older source generation")
        committed = subprocess.check_output(
            ["git", "-C", str(args.pages_dir), "show", f"{revision}:_engine/geo/public_email.py"],
            timeout=20,
        )
        if committed != Path(__file__).read_bytes():
            raise ValueError("Rendered email verifier differs from its source generation")
        report["deployment_generation"] = generation
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "html_checked": report["html_checked"],
                      "protected_html": len(report["protected_html"]),
                      "unprotected_html": len(report["failures"])}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
