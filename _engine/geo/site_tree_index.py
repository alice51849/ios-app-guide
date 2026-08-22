#!/usr/bin/env python3
"""One-pass HTML and sitemap inventory for publication-closing generators."""

from __future__ import annotations

from dataclasses import dataclass
import html
import os
from pathlib import Path
import re

from canonical_urls import declared_canonical


HEAD_BYTES = 262144
DEFAULT_SKIP_DIRS = frozenset({".git", "_engine", "node_modules"})
HTML_LANG_RE = re.compile(r'<html[^>]*\blang=["\']([^"\']+)["\']', re.I)
ROBOTS_META_RE = re.compile(
    r"<meta\b[^>]*\bname\s*=\s*[\"']robots[\"'][^>]*>",
    re.I,
)
HEAD_CLOSE_RE = re.compile(r"</head>", re.I)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
BROWSE_MARKER = "<!--iag-link-hub-browse-->"


@dataclass(frozen=True)
class HtmlFacts:
    lang: str | None
    noindex: bool
    title: str | None
    canonical: str | None
    managed_browse: bool


def extract_html_facts(
    source: str,
    *,
    include_canonical: bool = False,
) -> HtmlFacts:
    sample = source[:HEAD_BYTES]
    close = HEAD_CLOSE_RE.search(sample)
    head = sample[: close.start()] if close else sample
    robots = ROBOTS_META_RE.search(head)
    title: str | None = None
    for regex in (TITLE_RE, H1_RE):
        match = regex.search(sample)
        if not match:
            continue
        candidate = html.unescape(TAG_RE.sub("", match.group(1))).strip()
        candidate = re.sub(r"\s+", " ", candidate)
        candidate = re.split(r"\s+[|\uFF5C]\s+", candidate)[0].strip()
        if candidate:
            title = candidate[:140]
            break
    lang_match = HTML_LANG_RE.search(head)
    return HtmlFacts(
        lang=lang_match.group(1).strip() if lang_match else None,
        noindex=bool(robots and "noindex" in robots.group(0).lower()),
        title=title,
        canonical=declared_canonical(head) if include_canonical else None,
        managed_browse=BROWSE_MARKER in sample[:4096],
    )


class SiteTreeIndex:
    """Compact, mutable inventory shared by closure passes in one process."""

    def __init__(
        self,
        root: Path,
        html_paths: dict[str, Path],
        sitemap_paths: dict[str, Path],
    ) -> None:
        self.root = root.resolve()
        self._html_paths = html_paths
        self._sitemap_paths = sitemap_paths
        self._facts: dict[str, HtmlFacts] = {}
        self._canonical_known: set[str] = set()

    @classmethod
    def scan(
        cls,
        root: Path,
        *,
        skip_dirs: frozenset[str] = DEFAULT_SKIP_DIRS,
    ) -> "SiteTreeIndex":
        resolved = root.resolve()
        html_paths: dict[str, Path] = {}
        sitemap_paths: dict[str, Path] = {}
        for directory, dirnames, filenames in os.walk(resolved):
            dirnames[:] = sorted(
                name
                for name in dirnames
                if name not in skip_dirs
            )
            base = Path(directory)
            for name in sorted(filenames):
                path = base / name
                relative = path.relative_to(resolved).as_posix()
                if name.endswith(".html"):
                    html_paths[relative] = path
                elif name.startswith("sitemap") and name.endswith(".xml"):
                    sitemap_paths[relative] = path
        return cls(resolved, html_paths, sitemap_paths)

    def html_relatives(self) -> tuple[str, ...]:
        return tuple(sorted(self._html_paths))

    def html_relatives_under(self, top_level: str) -> tuple[str, ...]:
        prefix = f"{top_level}/"
        return tuple(
            rel for rel in sorted(self._html_paths) if rel.startswith(prefix)
        )

    def sitemap_paths(self) -> tuple[Path, ...]:
        return tuple(
            self._sitemap_paths[rel] for rel in sorted(self._sitemap_paths)
        )

    def path(self, relative: str) -> Path:
        return self._html_paths.get(relative, self.root / relative)

    def relative(self, path: Path | str) -> str:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = self.root / candidate
        try:
            return candidate.relative_to(self.root).as_posix()
        except ValueError:
            return Path(os.path.relpath(candidate, self.root)).as_posix()

    def contains(self, relative: str) -> bool:
        return relative in self._html_paths

    def facts(
        self,
        relative: str,
        *,
        include_canonical: bool = True,
    ) -> HtmlFacts:
        cached = self._facts.get(relative)
        if cached is not None and (
            not include_canonical or relative in self._canonical_known
        ):
            return cached
        path = self._html_paths[relative]
        try:
            with path.open(encoding="utf-8", errors="ignore") as handle:
                source = handle.read(HEAD_BYTES)
        except OSError as error:
            raise ValueError(f"Cannot read indexed HTML file: {path}") from error
        facts = extract_html_facts(
            source,
            include_canonical=include_canonical,
        )
        self._facts[relative] = facts
        if include_canonical:
            self._canonical_known.add(relative)
        return facts

    def basic_facts(self, relative: str) -> HtmlFacts:
        return self.facts(relative, include_canonical=False)

    def canonical(self, relative: str) -> str | None:
        if relative not in self._canonical_known:
            self.facts(relative, include_canonical=True)
        return self._facts[relative].canonical

    def update_source(self, relative: str, source: str) -> None:
        self._html_paths[relative] = self.root / relative
        self._facts[relative] = extract_html_facts(
            source,
            include_canonical=True,
        )
        self._canonical_known.add(relative)

    def remove(self, relative: str) -> None:
        self._html_paths.pop(relative, None)
        self._facts.pop(relative, None)
        self._canonical_known.discard(relative)
