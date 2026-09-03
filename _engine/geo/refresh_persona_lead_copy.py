#!/usr/bin/env python3
"""Retire the '— <App> is built for this.' lead tail from published guides.

`persona_closers` fixes the generator, but the 50 localized answer pages were
rendered before that change and still carry the old formula.  The publisher
intent catalog scrapes those pages, so until they are rewritten the catalog --
and every social post derived from it -- keeps the AI cadence.

This tool rewrites exactly one paragraph per page:

    <p class="lead">…problem… — <App> is built for this.</p>
        becomes
    <p class="lead">…problem… <native closing sentence></p>

It never touches identity: canonical URLs, App Store links, App Store IDs,
CTA labels, titles, H1s, JSON-LD and the footer disclosure are all left byte
for byte as they are, so `record_id`, `app_store_id` and `canonical_guide_url`
cannot move.

Only records whose English source lead actually carried the legacy tail are
considered.  A page whose lead was already rewritten by hand, or which never
used the persona template, is skipped and reported rather than guessed at.

The English-source translation memory (`i18n_trans/<locale>.json`) is updated
in the same pass, so a future full re-render reproduces the same sentences
instead of resurrecting the template.

Usage:
    python3 refresh_persona_lead_copy.py --pages <pages root> [--apply]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

import persona_closers
from answer_personas import PERSONAS
from official_locales import OFFICIAL_LOCALES


HERE = Path(__file__).resolve().parent
TRANS_DIR = HERE / "i18n_trans"

DASHES = "\u2014\u2015\u2013\u2012\u2010\u2011-"
# Dashes that bridge two clauses.  Em dash and horizontal bar may hug their
# neighbours (CJK writes "\u2014\u2014" with no spaces); every other dash has to be
# spaced, otherwise "One-time unlock" and "offline-first" split mid-word and
# the head is cut off in the middle of a phrase.
HUGGING_DASHES = "\u2014\u2015"
SPACED_DASHES = "\u2013\u2012\u2010\u2011-"
CLAUSE_RE = re.compile(
    r"(?:\s*[" + HUGGING_DASHES + r"]+\s*)"
    r"|(?:\s+[" + SPACED_DASHES + r"]+\s+)"
    r"|(?<=[.!?\u3002\uff01\uff1f\u0964\u06d4\u061f])\s+"
    r"|(?<=[\u3002\uff01\uff1f])"
    r"|(?<=[\u3001\uff0c\uff1a\uff1b])"
)
LEGACY_EN_RE = re.compile(r"\bis built for this\.?$")
# App-page marketing leads ("Free to start \u00b7 One-time unlock \u00b7 No subscription.")
# are not persona leads and must never receive a persona closer.
STORE_BOILERPLATE_RE = re.compile(r"\s\u00b7\s")

# The three translators that folded the tail into the surrounding sentence
# left nothing to cut.  Those leads are rewritten whole, natively.
MANUAL_REWRITES: dict[tuple[str, str], str] = {
    ("lumibopomofo", "ko"): (
        "주음을 처음 배우는 아이에게는 37개 기호를 모두 따라 그리기와 놀이로 다루는 앱이"
        " 맞습니다. 광고도, 데이터 수집도 없이 4~7세 첫 학습 시기에 맞춘 앱입니다."
    ),
    ("lumiletterspro", "ko"): (
        "취학을 준비하는 가정에는 글자 소리, 쓰기, 단어 만들기가 하나로 이어지는 초기 읽기"
        " 과정이 필요합니다. 서로 따로 노는 알파벳 게임 모음으로는 그 흐름이 생기지 않습니다."
    ),
    ("tripplanet", "ko"): (
        "어린 자녀와 여행하는 부모에게는 짐 싸기와 기다리는 시간, 낯선 장소 탐험까지"
        " 모험의 일부로 만들어 주는 활동이 필요합니다. 또 하나의 스트레스가 되어서는 곤란합니다."
    ),
    ("mochi", "ko"): (
        "대부분의 할 일 앱이 무겁게 느껴진다면, 알림과 반복 규칙, Apple Watch 컴플리케이션만"
        " 갖춘 깔끔한 체크리스트가 맞습니다. 프로젝트 관리 기능은 일부러 넣지 않았습니다."
    ),
    ("lumibopomofo", "ml-IN"): (
        "ആദ്യമായി ചൈനീസ് ഉച്ചാരണചിഹ്നങ്ങൾ പഠിക്കുന്ന കുട്ടിക്ക്, 37 ചിഹ്നങ്ങളും"
        " ട്രേസിംഗിലൂടെയും കളിയിലൂടെയും പരിചയപ്പെടുത്തുന്ന ആപ്പാണ് വേണ്ടത്."
        " 4–7 വയസ്സിലെ ആദ്യ പഠനഘട്ടത്തിന്, പരസ്യമില്ലാതെ, ഡാറ്റ ശേഖരിക്കാതെ."
    ),
    ("tripbee", "zh-Hant"): (
        "好的行程 App 會把散亂的旅程整理成一天一頁的時間軸，航班、飯店、活動、餐廳、交通"
        "各有清楚的圖示，一眼就看得出今天要做什麼。"
    ),
    ("tripbee", "zh-Hans"): (
        "好的行程 App 会把零散的行程整理成一天一页的时间轴，航班、酒店、活动、餐厅、交通"
        "各有清楚的图示，一眼就看得出今天要做什么。"
    ),
    ("wordmate", "zh-Hant"): (
        "通勤族要的是零碎時間就能背幾個字，不必上完整課程、不必註冊帳號，也不必每次都得"
        "把手機拿出來複習。"
    ),
    ("wordmate", "zh-Hans"): (
        "通勤族要的是零碎时间就能背几个词，不必上完整课程、不必注册账号，也不必每次都得"
        "把手机拿出来复习。"
    ),
}


def _name_forms(name: str) -> list[str]:
    out = {name}
    for sep in (":", "\uff1a", "\u2014", "\u2013", "|", "\uff5c", " - ", ",", "\u00b7"):
        if sep in name:
            out.add(name.split(sep)[0].strip())
    return sorted({x for x in out if len(x) >= 3}, key=len, reverse=True)


def split_legacy_tail(text: str, app_name: str) -> tuple[str | None, str]:
    """Return (head, tail) with the legacy closing clause removed, or (None, reason)."""
    text = " ".join(text.split())
    parts: list[tuple[str, str]] = []
    last = 0
    for match in CLAUSE_RE.finditer(text):
        parts.append((text[last:match.start()], text[match.start():match.end()]))
        last = match.end()
    parts.append((text[last:], ""))
    parts = [p for p in parts if p[0].strip() or p[1]]
    if len(parts) < 2:
        return None, "single-clause"
    tail = parts[-1][0].strip()
    if not tail:
        return None, "empty-tail"
    bridge = parts[-2][1]
    dash_bridged = bool(re.search("[" + DASHES + "]", bridge))
    if not (any(n in tail for n in _name_forms(app_name)) or dash_bridged):
        return None, "no-app-name-and-no-dash"
    if len(tail) > 110:
        return None, f"tail-too-long:{len(tail)}"
    if len(tail) > 0.5 * len(text):
        return None, "tail-dominates"
    head = text[: len(text) - len(parts[-1][0]) - len(bridge)].strip()
    head = head.rstrip(DASHES + " \u3001\uff0c,;\uff1b:\uff1a")
    cjk = sum(
        1
        for ch in text
        if "\u2e80" <= ch <= "\u9fff"
        or "\u3040" <= ch <= "\u30ff"
        or "\uac00" <= ch <= "\ud7af"
        or "\u0e00" <= ch <= "\u0e7f"
    )
    if len(head) < (10 if cjk > len(text) * 0.2 else 25):
        return None, f"head-too-short:{len(head)}"
    return head, tail


def legacy_apps() -> set[str]:
    """Apps whose English persona lead carried the retired tail."""
    return {
        key
        for key, entries in PERSONAS.items()
        if entries and entries[0].get("lead")
    }


def _slug(key: str) -> str:
    from publisher_intent_catalog import slugify

    return slugify(str(PERSONAS[key][0]["query"]))


LEAD_RE = re.compile(r'(<p class="lead[^"]*">)(.*?)(</p>)', re.S)


def _english_leads(pages: Path, apps: dict[str, Any], catalog: Any) -> dict[str, str]:
    """The en-US lead per app, used to recognise pages that were never localized."""
    leads: dict[str, str] = {}
    for key in apps:
        if key not in PERSONAS:
            continue
        path = pages / "en-US" / "answers" / f"{_slug(key)}.html"
        if not path.is_file():
            continue
        match = LEAD_RE.search(path.read_text(encoding="utf-8"))
        if match:
            leads[key] = catalog.single_line(match.group(2))
    return leads


def plan(pages: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Compute every lead rewrite without writing anything."""
    import publisher_intent_catalog as catalog

    changes: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    apps = catalog._finder_records(pages)
    english = _english_leads(pages, apps, catalog)
    for locale in OFFICIAL_LOCALES:
        for key in sorted(apps):
            if key not in PERSONAS:
                continue
            slug = _slug(key)
            path = pages / locale / "answers" / f"{slug}.html"
            if not path.is_file():
                continue  # app-page record: its context is a store description
            source = path.read_text(encoding="utf-8")
            match = LEAD_RE.search(source)
            if not match:
                skipped.append({"app": key, "locale": locale, "why": "no-lead"})
                continue
            raw_lead = match.group(2)
            current = catalog.single_line(raw_lead)
            name = catalog._localized_app_name(source, str(apps[key]["app_store_id"]))
            if STORE_BOILERPLATE_RE.search(current):
                skipped.append(
                    {"app": key, "locale": locale, "why": "store-boilerplate-lead",
                     "text": current}
                )
                continue
            # A handful of pages were never localized and still show the
            # English lead.  Rewrite those in English rather than bolting a
            # native closing sentence onto an English paragraph -- the page
            # stays monolingual, and the template still goes away.
            copy_locale = (
                "en-US"
                if not locale.startswith("en") and current == english.get(key)
                else locale
            )
            override = MANUAL_REWRITES.get((key, locale))
            if override is not None:
                head, tail = " ".join(override.split()), "(manual rewrite)"
            else:
                head, tail = split_legacy_tail(current, name)
                if head is None:
                    skipped.append(
                        {"app": key, "locale": locale, "why": tail, "text": current}
                    )
                    continue
                if not _looks_like_legacy(current, tail, name, copy_locale):
                    skipped.append(
                        {"app": key, "locale": locale, "why": "not-legacy-tail",
                         "text": current}
                    )
                    continue
            new = persona_closers.close_lead(copy_locale, head, key, name)
            if new == current:
                continue
            changes.append(
                {
                    "app": key,
                    "locale": locale,
                    "path": path,
                    "name": name,
                    "shape": persona_closers.shape_for(key),
                    "copy_locale": copy_locale,
                    "old": current,
                    "new": new,
                    "raw_lead": raw_lead,
                    "tail": tail,
                }
            )
    return changes, skipped


def _looks_like_legacy(current: str, tail: str, name: str, locale: str) -> bool:
    """Guard against rewriting a lead that never used the template."""
    if locale.startswith("en"):
        return bool(LEGACY_EN_RE.search(current))
    # A translated tail is short, names the app, and closes the paragraph.
    if any(n in tail for n in _name_forms(name)):
        return True
    # Some scripts transliterate the name; then the dash bridge plus a short
    # trailing clause is the signature.
    return len(tail) <= 80


def apply(changes: list[dict[str, Any]]) -> int:
    written = 0
    for change in changes:
        path: Path = change["path"]
        source = path.read_text(encoding="utf-8")
        match = LEAD_RE.search(source)
        if not match or match.group(2) != change["raw_lead"]:
            raise RuntimeError(f"lead moved under us: {path}")
        patched = source[: match.start(2)] + change["new"] + source[match.end(2):]
        if patched == source:
            continue
        path.write_text(patched, encoding="utf-8")
        written += 1
    return written


def refresh_translation_memory(changes: list[dict[str, Any]]) -> int:
    """Teach i18n_trans the new sentence so a re-render keeps it."""
    from answer_personas import persona_facts

    updated = 0
    by_locale: dict[str, list[dict[str, Any]]] = {}
    for change in changes:
        by_locale.setdefault(change["locale"], []).append(change)
    english = {
        change["app"]: change["new"]
        for change in changes
        if change["locale"] == "en-US"
    }
    for locale, rows in by_locale.items():
        if locale == "en-US":
            continue
        path = TRANS_DIR / f"{locale}.json"
        if not path.is_file():
            continue
        memory = json.loads(path.read_text(encoding="utf-8"))
        dirty = False
        for row in rows:
            if row.get("copy_locale", locale) != locale:
                # An English paragraph left on a localized page: do not pin
                # it into the translation memory as if it were a translation.
                continue
            source_key = english.get(row["app"])
            if not source_key or memory.get(source_key) == row["new"]:
                continue
            memory[source_key] = row["new"]
            dirty = True
            updated += 1
        if dirty:
            # Keep the file's own shape: two-space indent, insertion order,
            # trailing newline.  Re-sorting would rewrite every line of a
            # 4,700-entry file and collide with anyone else's edits.
            path.write_text(
                json.dumps(memory, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    pages = args.pages.resolve()
    changes, skipped = plan(pages)
    print(f"leads to rewrite: {len(changes)}   skipped: {len(skipped)}")
    locales = {c["locale"] for c in changes}
    print(f"locales touched: {len(locales)}")
    if args.report:
        args.report.write_text(
            json.dumps(
                {
                    "changes": [
                        {k: (str(v) if k == "path" else v) for k, v in c.items()}
                        for c in changes
                    ],
                    "skipped": skipped,
                },
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
    if args.apply:
        print(f"pages rewritten: {apply(changes)}")
        print(f"translation-memory entries refreshed: {refresh_translation_memory(changes)}")
    else:
        print("dry run; pass --apply to write")
    return 0


if __name__ == "__main__":
    sys.exit(main())
