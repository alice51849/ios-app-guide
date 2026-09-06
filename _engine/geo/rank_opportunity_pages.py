#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Surface the phrases shoppers actually search on the existing localized pages.

``agent/rank_opportunity_topics.py`` turns the daily iTunes Search proxy
readings into ``geo/data/rank_opportunity_topics.json``: per app and site
locale, the native-language terms where the app already ranks 4-30 in that
storefront ("opportunity") or 1-3 ("defend").  This module does *not* mint
URLs for them -- a page per phrase with the same body is a doorway page.  It
enriches the pages that already exist and already carry the app's native
copy: the localized app page ``<locale>/<app>.html`` (``build_pages_i18n``)
and the localized hub ``<locale>/hubs/<app>.html`` (``gen_hubs``) get one
prose line -- a purpose-written native label (:data:`SEARCHED_AS_LABELS`)
followed by up to three phrases verbatim, comma/、-separated, no links --
and the app page's existing ``<meta name="keywords">`` gains the same
phrases.  ``<title>``, canonical and hreflang never change.

Fail-closed and idempotent by construction:

* only locales with a label written for this purpose get the line; there is
  deliberately no fallback to another UI string or to English;
* an absent or unreadable topics file is a logged no-op -- every page renders
  exactly as it did before, nothing is removed;
* ordering is fixed (defend first, then by proxy rank, then by term); phrases
  that repeat an already-listed head word ("toeic hören" after "toeic lesen")
  or differ only in case/whitespace/punctuation are dropped; the list is
  capped at :data:`MAX_PHRASES`, so a rerun over the same inputs is
  byte-identical.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import re
import unicodedata
from pathlib import Path
from typing import Any

import aso_evidence_contract as contract

HERE = Path(__file__).resolve().parent
TOPICS_PATH = HERE / "data" / "rank_opportunity_topics.json"
EXPECTED_SOURCE = "itunes_search_proxy"
MAX_PHRASES = 3
ROLE_ORDER = {"defend": 0, "opportunity": 1}
BLOCK_CLASS = "searched-as"
# Purpose-written labels, one per measured storefront language.  A locale
# whose base language is not here gets no line at all -- never a borrowed
# string.  Keyed by base language; zh-Hans / zh-Hant are their own keys.
SEARCHED_AS_LABELS = {
    "en": "People find this app by searching for",
    "zh-Hant": "大家這樣搜尋這款 App",
    "zh-Hans": "大家这样搜索这款 App",
    "ja": "このアプリはこんな検索で見つかっています",
    "ko": "이런 검색어로 이 앱을 찾습니다",
    "de": "So wird diese App gesucht",
    "fr": "On trouve cette app en cherchant",
    "pt": "As pessoas encontram este app buscando por",
    "ru": "Это приложение находят по запросам",
    "th": "คนค้นหาแอปนี้ด้วยคำว่า",
    "vi": "Mọi người tìm thấy ứng dụng này khi tìm kiếm",
}
# Full-width punctuation for the languages that set it that way.
_CJK_PUNCTUATION = {"zh-Hant": ("：", "、"), "zh-Hans": ("：", "、"), "ja": ("：", "、")}
CSS = (
    ".searched-as{margin:1.2em 0;font-size:.95em;line-height:1.6}"
    ".searched-as-label{font-weight:600;margin-right:.35em}"
)
CSS_TAG = f"<style>{CSS}</style>"
_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)

_INDEX_CACHE: dict[str, tuple[Any, ...]] = {}
_LOGGED: set[str] = set()


def _log_once(path: Path, message: str) -> None:
    key = f"{path}:{message}"
    if key in _LOGGED:
        return
    _LOGGED.add(key)
    print(f"rank-opportunity: {message} ({path}); pages render without the block")


def _index_topics(payload: Any, *, now=None) -> dict[tuple[str, str], list[dict[str, Any]]]:
    contract.validate_topics(payload, now=now)
    index: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for topic in payload["topics"]:
        if not isinstance(topic, dict):
            continue
        app = str(topic.get("app") or "")
        locale = str(topic.get("locale") or "")
        term = " ".join(str(topic.get("term") or "").split())
        rank = topic.get("rank")
        role = topic.get("role")
        if not app or not locale or not term:
            continue
        if role not in ROLE_ORDER or not isinstance(rank, int) or isinstance(rank, bool):
            continue
        index.setdefault((app, locale), []).append(
            {"term": term, "rank": rank, "role": role}
        )
    return index


def load_topics(path: Path | str | None = None, *, now=None) -> dict[tuple[str, str], list[dict[str, Any]]] | None:
    """Verify source bytes, exact roster and TTL even for an unchanged cached file."""
    path = Path(TOPICS_PATH if path is None else path)
    now = now or contract.utc_now()
    try:
        with path.open("rb") as handle:
            raw = handle.read(contract.MAX_DOCUMENT_BYTES + 1)
        signature = (hashlib.sha256(raw).hexdigest(), contract.roster_digest(contract.live_roster()))
        cached = _INDEX_CACHE.get(str(path))
        if cached is not None and cached[0] == signature:
            _, generated, expires, index = cached
            if generated <= now < expires:
                return index
            raise contract.ContractError("stale_or_future_evidence")
        payload = contract.decode_document(raw)
        index = _index_topics(payload, now=now)
        expires = contract.timestamp(payload["expires_at"])
        if payload["topics"]:
            earliest = min(dt.date.fromisoformat(row["reading_date"]) for row in payload["topics"])
            expires = min(expires, dt.datetime.combine(
                earliest + dt.timedelta(days=contract.READING_FRESH_DAYS + 1),
                dt.time.min, tzinfo=dt.timezone.utc,
            ))
        _INDEX_CACHE[str(path)] = (signature, contract.timestamp(payload["generated_at"]), expires, index)
        return index
    except (OSError, ValueError) as error:
        _log_once(path, f"unusable evidence: {error}")
        return None


_UNSET: Any = object()


def base_lang(locale: str) -> str:
    if locale in ("zh-Hans", "zh-Hant"):
        return locale
    return locale.split("-")[0]


def label_for(locale: str) -> str | None:
    """The curated label for ``locale``'s language, or ``None`` (no line)."""
    return SEARCHED_AS_LABELS.get(base_lang(locale))


def _fold(text: str) -> str:
    """Case, width, whitespace and punctuation-insensitive key."""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(_WORD_RE.findall(normalized))


def _head_word(text: str) -> str:
    words = _fold(text).split()
    return words[0] if words else ""


def phrases_for(
    key: str,
    locale: str,
    index: dict[tuple[str, str], list[dict[str, Any]]] | None = _UNSET,
    *,
    limit: int = MAX_PHRASES,
) -> list[str]:
    """Verbatim phrases for one page: defend first, then by proxy rank.

    ``index`` defaults to the committed topics file; pass ``None`` (what
    :func:`load_topics` returns for an unusable file) to get no phrases.
    Variants that fold to the same text, and phrases whose head word is
    already listed, are skipped so the line does not read "toeic, toeic,
    toeic".
    """
    if index is _UNSET:
        index = load_topics()
    if not index:
        return []
    entries = sorted(
        index.get((key, locale), ()),
        key=lambda t: (ROLE_ORDER[t["role"]], t["rank"], t["term"]),
    )
    seen: set[str] = set()
    heads: set[str] = set()
    out: list[str] = []
    for entry in entries:
        fold = _fold(entry["term"])
        head = _head_word(entry["term"])
        if not fold or fold in seen or head in heads:
            continue
        seen.add(fold)
        heads.add(head)
        out.append(entry["term"])
        if len(out) == limit:
            break
    return out


def searched_as_block(locale: str, phrases: list[str], *, compact: bool = False) -> str:
    """One prose line, or ``""`` when the locale has no label or no phrase.

    ``compact`` is the single-line form used inside hub cards; the default
    form matches the indented app-page template and starts with a blank
    line so it slots in after the feature list.  Callers add :data:`CSS_TAG`
    to ``<head>`` only when this returns something.
    """
    label = label_for(locale)
    if not label or not phrases:
        return ""
    e = html.escape
    colon, comma = _CJK_PUNCTUATION.get(base_lang(locale), (": ", ", "))
    line = (
        f'<p class="{BLOCK_CLASS}"><span class="{BLOCK_CLASS}-label">{e(label)}{colon}</span>'
        f"{comma.join(e(p) for p in phrases)}</p>"
    )
    if compact:
        return f'<section class="card">{line}</section>'
    return f"\n\n  {line}"


def merged_keywords(keywords: list[str], phrases: list[str]) -> list[str]:
    """Existing keywords followed by the phrases they do not already contain."""
    out = list(keywords)
    seen = {" ".join(str(k).split()).casefold() for k in keywords}
    for phrase in phrases:
        fold = phrase.casefold()
        if fold in seen:
            continue
        seen.add(fold)
        out.append(phrase)
    return out
