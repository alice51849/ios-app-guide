#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Keep localized copies that add nothing beyond the English page out of the index.

Google's spam policy lists "automated transformations like ... translating" and
"multiple pages targeted at specific regions ... that funnel users to one page"
as scaled content abuse / doorway examples.  The Guide ships tens of thousands
of localized pages, so a localized URL only stays indexable when it is more than
a second address for content that already has an indexable English URL.

Three conservative rules, each requiring an indexable English counterpart (so
the content never leaves the index entirely, it only stops competing with
itself):

``same-storefront-copy``
    A same-language regional variant that serves the *same* App Store
    storefront as its base (``en-US`` vs the English root, both ``us``) and
    whose visible text is at least ``same_storefront_min_identity`` verbatim
    the base.  Same content, same users, two URLs.  Regional variants with
    their own storefront (en-GB, en-AU, ...) are left alone: Google documents
    that as acceptable when annotated with hreflang.
``untranslated-core``
    Only the template chrome is translated: of the page-specific text (the
    segments that are not boilerplate repeated across the locale) at least
    ``untranslated_min_identity`` is verbatim the English page.
``thin-stub``
    A localized stub with at most ``thin_max_segments`` text blocks and less
    than ``thin_max_ratio`` of the English page's blocks.

Pages are never gated when they have no indexable English counterpart, are a
locale home page, are an index-entry canary, have Search Console
impressions/clicks in the optional evidence file, or are not one of
``gated_page_types`` (answers only today: hubs and localized alternatives are
re-rendered by the Pages deploy after this gate, and data/visuals landings carry
sealed 50-locale contracts, so those need a generator-level gate).  Gated pages get
``noindex,follow`` (pages and links stay), leave every sitemap, and are removed
from every other page's hreflang cluster.  ``gen_locale_indexation`` applies the
verdicts, so every publish path (publish.py, geo-daily, close_sitemap_graph)
re-evaluates them; a page that later passes is re-indexed automatically and
gets its original robots directive back.

    python3 scaled_content_gate.py --report out.json   # audit, writes nothing
"""
from __future__ import annotations

import argparse
from array import array
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
from typing import Iterable, Mapping

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from official_locales import OFFICIAL_LOCALES  # noqa: E402
import parallel_pages  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402
from site_tree_index import SiteTreeIndex  # noqa: E402

PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = os.environ.get("GEO_SITE", PUBLIC_SITE).rstrip("/")
POLICY_PATH = HERE / "scaled_content_policy.json"
CANARY_MANIFEST = HERE / "index_entry_canary_manifest.json"
STOREFRONTS_PATH = HERE / "locale_storefronts.json"
QUERY_TOPICS_PATH = HERE / "i18n_query_topics.json"
SCHEMA = "lumi.scaled-content-gate/v1"
ENGLISH_ROOT_STOREFRONT = "us"

MARK = "<!-- scaled-content-gate -->"
PRIOR_RE = re.compile(r'<!-- scaled-content-gate prior="([^"<>]*)" -->')
GATE_META_RE = re.compile(
    r'(?:<!-- scaled-content-gate prior="[^"<>]*" -->)?'
    + re.escape(MARK)
    + r'<meta name="robots" content="noindex,follow">'
)
ROBOTS_META_RE = re.compile(r"<meta\b[^>]*\bname\s*=\s*[\"']robots[\"'][^>]*>", re.I)
CONTENT_ATTR_RE = re.compile(r"\bcontent\s*=\s*[\"']([^\"']*)[\"']", re.I)
HEAD_CLOSE_RE = re.compile(r"</head>", re.I)
ALTERNATE_LINK_RE = re.compile(r"[ \t]*<link\b[^>]*\brel=[\"']alternate[\"'][^>]*>[ \t]*\n?", re.I)
HREFLANG_ATTR_RE = re.compile(r"\bhreflang=[\"']([^\"']+)[\"']", re.I)
HREF_ATTR_RE = re.compile(r"\bhref=[\"']([^\"']+)[\"']", re.I)
HREFLANG_HREF_RE = re.compile(
    r"<link\b[^>]*\bhreflang=[\"'][^\"']+[\"'][^>]*\bhref=[\"']([^\"']+)[\"']"
    r"|<link\b[^>]*\bhref=[\"']([^\"']+)[\"'][^>]*\bhreflang=[\"']",
    re.I,
)
SITEMAP_XHTML_RE = re.compile(r"[ \t]*<xhtml:link\b[^>]*/>[ \t]*\n?", re.I)

MAIN_RE = re.compile(r"<main\b[^>]*>(.*)</main>", re.S | re.I)
BODY_RE = re.compile(r"<body\b[^>]*>(.*)</body>", re.S | re.I)
DROP_RE = re.compile(
    r"<(script|style|nav|header|footer|aside|noscript|template|svg)\b.*?</\1\s*>",
    re.S | re.I,
)
BLOCK_RE = re.compile(
    r"</?(?:p|li|h[1-6]|td|th|dt|dd|figcaption|blockquote|div|section|article"
    r"|summary|details|tr|br|option|label|button|a)\b[^>]*>",
    re.I,
)
TAG_RE = re.compile(r"<[^>]+>")
SPACE_RE = re.compile(r"\s+")
WORD_RE = re.compile(r"\w")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
H1_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.S | re.I)
LATIN_RE = re.compile(r"[A-Za-zÀ-ɏ]")
SCRIPT_RANGES = {
    "ja": "぀-ヿ一-鿿",
    "zh-Hans": "一-鿿",
    "zh-Hant": "一-鿿",
    "ko": "가-힯ᄀ-ᇿ",
    "th": "฀-๿",
    "ru": "Ѐ-ӿ",
    "uk": "Ѐ-ӿ",
    "el": "Ͱ-Ͽ",
    "ar-SA": "؀-ۿ",
    "ur-PK": "؀-ۿ",
    "he": "֐-׿",
    "hi": "ऀ-ॿ",
    "mr-IN": "ऀ-ॿ",
    "bn-BD": "ঀ-৿",
    "gu-IN": "઀-૿",
    "kn-IN": "ಀ-೿",
    "ml-IN": "ഀ-ൿ",
    "or-IN": "଀-୿",
    "pa-IN": "਀-੿",
    "ta-IN": "஀-௿",
    "te-IN": "ఀ-౿",
}
SCRIPT_RES = {locale: re.compile(f"[{chars}]") for locale, chars in SCRIPT_RANGES.items()}

REASONS = ("same-storefront-copy", "untranslated-core", "thin-stub")


# ------------------------------------------------------------------ policy
@dataclass(frozen=True)
class Policy:
    boilerplate_min_pages: int
    same_storefront_copies: Mapping[str, str]
    same_storefront_min_identity: float
    untranslated_min_core_chars: int
    untranslated_min_identity: float
    thin_max_segments: int
    thin_max_ratio: float
    regional_variants: Mapping[str, str]
    search_evidence_path: str | None
    protected_paths: frozenset[str]
    gated_page_types: frozenset[str] = frozenset()


def _storefront(locale: str, storefronts: Mapping[str, str]) -> str:
    if locale == "":
        return ENGLISH_ROOT_STOREFRONT
    return storefronts[locale]


def load_policy(path: Path = POLICY_PATH, storefronts_path: Path = STOREFRONTS_PATH) -> Policy:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema") != SCHEMA:
        raise ValueError(f"{path}: schema must be {SCHEMA}")
    storefronts = json.loads(storefronts_path.read_text(encoding="utf-8"))
    official = set(OFFICIAL_LOCALES)
    copies = dict(raw["same_storefront_copies"])
    for variant, base in copies.items():
        if variant not in official or (base and base not in official):
            raise ValueError(f"same_storefront_copies: unknown locale {variant}->{base}")
        if variant.split("-")[0] != (base.split("-")[0] if base else "en"):
            raise ValueError(f"same_storefront_copies: {variant} and {base or 'en'} differ in language")
        if _storefront(variant, storefronts) != _storefront(base, storefronts):
            # Different storefronts serve different users; Google treats such
            # hreflang-annotated regional variants as legitimate.
            raise ValueError(
                f"same_storefront_copies: {variant} and {base or 'en'} use different storefronts"
            )
    regional = dict(raw.get("regional_variants", {}))
    for variant, base in regional.items():
        if variant not in official or (base and base not in official):
            raise ValueError(f"regional_variants: unknown locale {variant}->{base}")
    policy = Policy(
        boilerplate_min_pages=int(raw["boilerplate_min_pages"]),
        same_storefront_copies=copies,
        same_storefront_min_identity=float(raw["same_storefront_min_identity"]),
        untranslated_min_core_chars=int(raw["untranslated_min_core_chars"]),
        untranslated_min_identity=float(raw["untranslated_min_identity"]),
        thin_max_segments=int(raw["thin_max_segments"]),
        thin_max_ratio=float(raw["thin_max_ratio"]),
        regional_variants=regional,
        search_evidence_path=raw.get("search_evidence_path") or None,
        protected_paths=frozenset(raw.get("protected_paths", [])),
        gated_page_types=frozenset(raw["gated_page_types"]),
    )
    # Conservative floors: loosening below these needs a reviewed code change,
    # not a JSON edit.
    if policy.same_storefront_min_identity < 0.9 or policy.untranslated_min_identity < 0.8:
        raise ValueError("scaled-content identity thresholds may not go below 0.9 / 0.8")
    if policy.thin_max_ratio > 0.25 or policy.thin_max_segments > 12:
        raise ValueError("thin-stub thresholds may not exceed 12 segments / 0.25 ratio")
    if not policy.gated_page_types:
        raise ValueError("gated_page_types must name at least one page type")
    if policy.untranslated_min_core_chars < 200 or policy.boilerplate_min_pages < 5:
        raise ValueError("untranslated core floor is 200 chars; boilerplate floor is 5 pages")
    return policy


def canary_slugs(path: Path = CANARY_MANIFEST) -> frozenset[str]:
    if not path.is_file():
        return frozenset()
    return frozenset(json.loads(path.read_text(encoding="utf-8")).get("canaries", []))


def load_search_evidence(policy: Policy, site: str = SITE) -> tuple[frozenset[str], bool]:
    """Relative paths with Search Console impressions or clicks, and whether the file exists."""
    if not policy.search_evidence_path:
        return frozenset(), False
    path = HERE / policy.search_evidence_path
    if not path.is_file():
        return frozenset(), False
    raw = json.loads(path.read_text(encoding="utf-8"))
    pages = raw.get("pages", {})
    out: set[str] = set()
    prefix = site + "/"
    for key, value in pages.items():
        if not isinstance(value, Mapping):
            continue
        if (value.get("impressions") or 0) <= 0 and (value.get("clicks") or 0) <= 0:
            continue
        relative = key[len(prefix):] if key.startswith(prefix) else key.lstrip("/")
        if not relative or relative.endswith("/"):
            relative += "index.html"
        out.add(relative)
    return frozenset(out), True


# ------------------------------------------------------------------ text model
@dataclass(frozen=True)
class Signature:
    """Visible main-content text blocks of one page, as compact arrays."""

    digests: array
    chars: array
    native: array
    latin: array
    title: str
    noindex: bool = False
    gate_marked: bool = False

    @property
    def total_chars(self) -> int:
        return sum(self.chars)

    def __len__(self) -> int:
        return len(self.digests)


def text_segments(source: str) -> list[str]:
    match = MAIN_RE.search(source) or BODY_RE.search(source)
    body = match.group(1) if match else source
    body = DROP_RE.sub(" ", body)
    body = BLOCK_RE.sub("\n", body)
    body = html.unescape(TAG_RE.sub(" ", body))
    segments = []
    for line in body.split("\n"):
        segment = SPACE_RE.sub(" ", line).strip()
        if len(segment) >= 2 and WORD_RE.search(segment):
            segments.append(segment)
    return segments


def signature_of(source: str, locale: str) -> Signature:
    script = SCRIPT_RES.get(locale)
    digests, chars, native, latin = array("Q"), array("I"), array("I"), array("I")
    for segment in text_segments(source):
        digests.append(
            int.from_bytes(hashlib.blake2b(segment.encode("utf-8"), digest_size=8).digest(), "big")
        )
        chars.append(len(segment))
        native.append(len(script.findall(segment)) if script else 0)
        latin.append(len(LATIN_RE.findall(segment)))
    title_match = TITLE_RE.search(source) or H1_RE.search(source)
    title = ""
    if title_match:
        title = SPACE_RE.sub(" ", html.unescape(TAG_RE.sub(" ", title_match.group(1)))).strip()
    robots = head_robots(source)
    return Signature(
        digests, chars, native, latin, title,
        noindex=bool(robots and "noindex" in robots.lower()),
        gate_marked=MARK in source,
    )


def _scan(item: tuple[str, str]) -> Signature:
    path, locale = item
    with open(path, encoding="utf-8", errors="ignore") as handle:
        return signature_of(handle.read(), locale)


def head_robots(source: str) -> str | None:
    close = HEAD_CLOSE_RE.search(source)
    head = source[: close.start()] if close else source[:262144]
    match = ROBOTS_META_RE.search(head)
    return match.group(0) if match else None


# ------------------------------------------------------------------ verdicts
@dataclass
class Verdict:
    relative: str
    locale: str
    page_type: str
    reason: str | None = None
    exempt: str | None = None
    category: str = ""
    main_chars: int = 0
    core_chars: int = 0
    segments: int = 0
    en_segments: int = 0
    identity: float | None = None
    base_identity: float | None = None
    native_ratio: float | None = None
    local_query: bool = False


@dataclass
class GateResult:
    verdicts: dict[str, Verdict] = field(default_factory=dict)
    gated: frozenset[str] = frozenset()
    evidence_loaded: bool = False

    def counts(self) -> Counter:
        return Counter(v.reason or v.exempt or "kept" for v in self.verdicts.values())


def page_type(rest: str) -> str:
    return rest.split("/", 1)[0] if "/" in rest else "(root)"


def _local_queries(path: Path = QUERY_TOPICS_PATH) -> dict[str, list[str]]:
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = defaultdict(list)
    for variants in raw.values():
        if isinstance(variants, Mapping):
            for locale, phrase in variants.items():
                if isinstance(phrase, str) and len(phrase) >= 4:
                    out[locale].append(phrase.lower())
    return out


def evaluate(
    pages: Path,
    tree: SiteTreeIndex | None = None,
    *,
    policy: Policy | None = None,
    site: str = SITE,
    with_signals: bool = False,
) -> GateResult:
    pages = pages.resolve()
    tree = tree or SiteTreeIndex.scan(pages)
    policy = policy or load_policy()
    canaries = canary_slugs()
    evidence, evidence_loaded = load_search_evidence(policy, site)
    locales = sorted(set(OFFICIAL_LOCALES))

    localized: list[tuple[str, str]] = []
    for locale in locales:
        for relative in tree.html_relatives_under(locale):
            localized.append((relative, locale))
    needed_bases: set[str] = set()
    for relative, locale in localized:
        rest = relative.split("/", 1)[1]
        needed_bases.add(rest)
        base = policy.same_storefront_copies.get(locale) or policy.regional_variants.get(locale)
        if base:
            needed_bases.add(f"{base}/{rest}")
    english = sorted(rel for rel in needed_bases if tree.contains(rel))
    items = [(str(tree.path(rel)), locale) for rel, locale in localized]
    items += [(str(tree.path(rel)), rel.split("/", 1)[0] if "/" in rel else "") for rel in english]
    keys = [rel for rel, _ in localized] + english
    signatures = dict(zip(keys, parallel_pages.ordered_map(_scan, items)))

    frequency: dict[str, Counter] = defaultdict(Counter)
    for relative, locale in localized:
        frequency[locale].update(set(signatures[relative].digests))

    queries = _local_queries() if with_signals else {}
    result = GateResult(evidence_loaded=evidence_loaded)
    gated: set[str] = set()
    for relative, locale in localized:
        rest = relative.split("/", 1)[1]
        verdict = Verdict(relative=relative, locale=locale, page_type=page_type(rest))
        signature = signatures[relative]
        verdict.segments = len(signature)
        verdict.main_chars = signature.total_chars
        boiler = frequency[locale]
        core = [
            index for index, digest in enumerate(signature.digests)
            if boiler[digest] < policy.boilerplate_min_pages
        ]
        verdict.core_chars = sum(signature.chars[index] for index in core)
        if locale in SCRIPT_RES:
            native = sum(signature.native[index] for index in core)
            latin = sum(signature.latin[index] for index in core)
            verdict.native_ratio = round(native / (native + latin), 3) if native + latin else None
        if queries.get(locale):
            title = signature.title.lower()
            verdict.local_query = any(phrase in title for phrase in queries[locale])
        result.verdicts[relative] = verdict

        if signature.noindex and not signature.gate_marked:
            # Another process (non-store locale, metadata dedupe, consolidation)
            # owns this noindex; it is not ours to judge or undo.
            verdict.exempt = "already-noindex"
            verdict.category = "already-noindex"
            continue
        english_signature = signatures.get(rest)
        if english_signature is None:
            verdict.exempt = "no-english-counterpart"
            verdict.category = "locale-only"
            continue
        if english_signature.noindex:
            verdict.exempt = "english-counterpart-noindex"
            verdict.category = "english-counterpart-noindex"
            continue
        english_digests = set(english_signature.digests)
        verdict.en_segments = len(english_signature)
        if verdict.core_chars:
            same = sum(
                signature.chars[index] for index in core
                if signature.digests[index] in english_digests
            )
            verdict.identity = round(same / verdict.core_chars, 3)

        variant_base = policy.same_storefront_copies.get(locale)
        regional_base = policy.regional_variants.get(locale)
        reason = None
        if locale in policy.same_storefront_copies:
            base_rel = f"{variant_base}/{rest}" if variant_base else rest
            base_signature = signatures.get(base_rel)
            if base_signature is not None and signature.total_chars:
                base_digests = set(base_signature.digests)
                same = sum(
                    chars for digest, chars in zip(signature.digests, signature.chars)
                    if digest in base_digests
                )
                verdict.base_identity = round(same / signature.total_chars, 3)
                if verdict.base_identity >= policy.same_storefront_min_identity:
                    reason = "same-storefront-copy"
        elif regional_base is not None:
            base_rel = f"{regional_base}/{rest}" if regional_base else rest
            base_signature = signatures.get(base_rel)
            if base_signature is not None and signature.total_chars:
                base_digests = set(base_signature.digests)
                same = sum(
                    chars for digest, chars in zip(signature.digests, signature.chars)
                    if digest in base_digests
                )
                verdict.base_identity = round(same / signature.total_chars, 3)
        if reason is None and not locale.startswith("en-"):
            if (
                verdict.core_chars >= policy.untranslated_min_core_chars
                and verdict.identity is not None
                and verdict.identity >= policy.untranslated_min_identity
            ):
                reason = "untranslated-core"
            elif (
                verdict.segments <= policy.thin_max_segments
                and verdict.en_segments
                and verdict.segments / verdict.en_segments < policy.thin_max_ratio
            ):
                reason = "thin-stub"
        verdict.category = reason or _kept_category(verdict, policy)

        slug = rest.rsplit("/", 1)[-1][:-5]
        exempt = None
        if rest == "index.html":
            exempt = "locale-home"
        elif rest.startswith("answers/") and slug in canaries:
            exempt = "index-entry-canary"
        elif relative in evidence:
            exempt = "search-console-evidence"
        elif relative in policy.protected_paths:
            exempt = "protected"
        elif verdict.page_type not in policy.gated_page_types:
            # Only page types whose final bytes this pipeline owns.  hubs and
            # localized alternatives are re-rendered by pages.yml (gen_hubs.py,
            # alternatives_i18n.py) after this gate, and data/visuals landings
            # carry sealed 50-locale contracts; a stamp there would not reach
            # the live site or would break the contract, so those need a
            # generator-level gate instead.
            exempt = "page-type-not-gated"
        if reason and exempt:
            verdict.exempt = exempt
            continue
        verdict.reason = reason
        if reason:
            gated.add(relative)
    result.gated = frozenset(gated)
    return result


def _kept_category(verdict: Verdict, policy: Policy) -> str:
    if verdict.base_identity is not None and verdict.base_identity >= policy.same_storefront_min_identity:
        return "regional-copy-own-storefront"
    if verdict.locale.startswith("en-"):
        return "english-variant"
    identity = verdict.identity or 0.0
    native = verdict.native_ratio
    if identity >= 0.3 or (native is not None and native < 0.5):
        return "partial-translation"
    if verdict.local_query:
        return "translated+local-query"
    return "translated-only"


# ------------------------------------------------------------------ rewriting
def apply_noindex(text: str) -> str:
    if MARK in text:
        return text
    robots = head_robots(text)
    if robots is not None:
        prior = CONTENT_ATTR_RE.search(robots)
        prior_value = prior.group(1) if prior else ""
        stamp = f'<!-- scaled-content-gate prior="{html.escape(prior_value, quote=True)}" -->'
        replacement = f'{stamp}{MARK}<meta name="robots" content="noindex,follow">'
        return text.replace(robots, replacement, 1)
    stamp = f'{MARK}<meta name="robots" content="noindex,follow">'
    match = HEAD_CLOSE_RE.search(text)
    if match:
        return text[: match.start()] + stamp + text[match.start():]
    return stamp + text


def remove_noindex(text: str) -> str:
    """Undo our own stamp, restoring the robots directive it replaced."""
    if MARK not in text:
        return text
    match = GATE_META_RE.search(text)
    if not match:
        return text.replace(MARK, "")
    prior = PRIOR_RE.match(match.group(0))
    restored = ""
    if prior:
        value = html.unescape(prior.group(1))
        restored = f'<meta name="robots" content="{html.escape(value, quote=True)}">'
    return text[: match.start()] + restored + text[match.end():]


def url_to_relative(url: str, site: str = SITE) -> str | None:
    prefix = site + "/"
    if not url.startswith(prefix):
        return None
    relative = url[len(prefix):].split("#", 1)[0].split("?", 1)[0]
    if not relative or relative.endswith("/"):
        relative += "index.html"
    return relative


@lru_cache(maxsize=4)
def gated_urls(gated: frozenset[str], site: str = SITE) -> frozenset[str]:
    """Every public spelling of the gated pages (directory form for index.html)."""
    out: set[str] = set()
    for relative in gated:
        out.add(f"{site}/{relative}")
        if relative == "index.html" or relative.endswith("/index.html"):
            out.add(f"{site}/{relative[: -len('index.html')]}")
    return frozenset(out)


def strip_gated_alternates(text: str, gated: frozenset[str], site: str = SITE) -> str:
    """Drop hreflang alternates that point at gated (noindex) pages."""
    if not gated:
        return text
    close = text.find("</head>")
    head = text if close < 0 else text[:close]
    targets = gated_urls(frozenset(gated), site)
    if not any(
        (first or second) in targets for first, second in HREFLANG_HREF_RE.findall(head)
    ):
        return text

    def drop(match: re.Match[str]) -> str:
        tag = match.group(0)
        if not HREFLANG_ATTR_RE.search(tag):
            return tag
        href = HREF_ATTR_RE.search(tag)
        if href and href.group(1) in targets:
            return ""
        return tag

    return ALTERNATE_LINK_RE.sub(drop, head) + ("" if close < 0 else text[close:])


def strip_gated_sitemap_alternates(text: str, gated: frozenset[str], site: str = SITE) -> str:
    if not gated or "xhtml:link" not in text:
        return text
    targets = gated_urls(frozenset(gated), site)

    def drop(match: re.Match[str]) -> str:
        href = HREF_ATTR_RE.search(match.group(0))
        if href and href.group(1) in targets:
            return ""
        return match.group(0)

    return SITEMAP_XHTML_RE.sub(drop, text)


# ------------------------------------------------------------------ report
def report(result: GateResult) -> dict:
    by_locale: dict[str, Counter] = defaultdict(Counter)
    by_type: dict[str, Counter] = defaultdict(Counter)
    for verdict in result.verdicts.values():
        label = verdict.reason or verdict.category or verdict.exempt or "kept"
        if verdict.reason is None and verdict.exempt and verdict.category in REASONS:
            label = f"{verdict.category} (exempt: {verdict.exempt})"
        by_locale[verdict.locale][label] += 1
        by_type[verdict.page_type][label] += 1
    samples: dict[str, list[str]] = defaultdict(list)
    for relative in sorted(result.verdicts):
        verdict = result.verdicts[relative]
        label = verdict.reason or verdict.category
        if len(samples[label]) < 2000:
            samples[label].append(relative)
    return {
        "schema": SCHEMA + "#report",
        "pages_evaluated": len(result.verdicts),
        "gated": len(result.gated),
        "gated_by_reason": dict(Counter(result.verdicts[r].reason for r in result.gated)),
        "labels": dict(result.counts()),
        "categories": dict(Counter(v.category for v in result.verdicts.values())),
        "search_evidence_loaded": result.evidence_loaded,
        "by_locale": {k: dict(v) for k, v in sorted(by_locale.items())},
        "by_type": {k: dict(v) for k, v in sorted(by_type.items())},
        "samples": {k: v for k, v in sorted(samples.items())},
        "gated_paths": sorted(result.gated),
        "verdicts": {
            rel: {
                "reason": v.reason, "exempt": v.exempt, "category": v.category,
                "main_chars": v.main_chars, "core_chars": v.core_chars,
                "segments": v.segments, "en_segments": v.en_segments,
                "identity": v.identity, "base_identity": v.base_identity,
                "native_ratio": v.native_ratio, "local_query": v.local_query,
            }
            for rel, v in sorted(result.verdicts.items())
        },
    }


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages-dir", type=Path, default=PAGES)
    parser.add_argument("--report", type=Path, help="write the full audit JSON here")
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = evaluate(args.pages_dir, with_signals=bool(args.report))
    counts = Counter(result.verdicts[r].reason for r in result.gated)
    print(
        "scaled-content-gate: evaluated={} gated={} {}".format(
            len(result.verdicts),
            len(result.gated),
            " ".join(f"{k}={counts.get(k, 0)}" for k in REASONS),
        )
    )
    if args.report:
        args.report.write_text(
            json.dumps(report(result), ensure_ascii=False, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
