#!/usr/bin/env python3
"""Merge agent-authored translation batches into geo/i18n_trans/<locale>.json.

Batch format (one JSON file per batch, keyed by priority index):

    {"12": {"ja": "…", "ko": "…"}, "13": {"ja": "…"}}

The priority file maps index -> English source string, so batches never have to
repeat the English text (cheap, and it removes any risk of a mistyped key).

Validation performed before a translation is accepted:
  * non-empty, and different from the English source for real sentences
  * zh-Hans must not contain Bopomofo, and must not contain characters that only
    exist in the traditional set (a curated blocklist)
  * zh-Hant must not contain Bopomofo
  * CJK/Korean locales must reach a minimum native-script letter ratio
  * no stray placeholder markers such as {app} left in the output
Rejected entries are reported and skipped -- never written.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRANS = ROOT / "i18n_trans"

BOPOMOFO = re.compile(r"[ㄅ-ㄯㆠ-ㆿ]")
# characters that exist only in Traditional Chinese usage and must never appear
# in a zh-Hans string
TRAD_ONLY = set(
    "們來個對後點開關證體專業說話讀寫學習練題價費務動幾機構樣觀檔應該電腦網絡"
    "選擇還實現內時間數據頁級圖標籤單導覽產訂閱錄類別畫質壓縮匯資訊軟檢視預於"
    "無線設備隱條購買錢處編輯刪尋範經驗顯轉換聲發這為從會兒東車馬長門問見語讓"
    "認識記讚製佈"
)

NATIVE_RANGES = {
    "ja": [(0x3040, 0x30FF), (0x3400, 0x4DBF), (0x4E00, 0x9FFF), (0x31F0, 0x31FF)],
    "ko": [(0xAC00, 0xD7AF), (0x1100, 0x11FF), (0x3130, 0x318F)],
    "zh-Hant": [(0x3400, 0x4DBF), (0x4E00, 0x9FFF)],
    "zh-Hans": [(0x3400, 0x4DBF), (0x4E00, 0x9FFF)],
}
MIN_NATIVE = 0.35  # brand-heavy strings legitimately carry a lot of Latin text


def native_ratio(text: str, locale: str) -> float:
    ranges = NATIVE_RANGES.get(locale)
    if not ranges:
        return 1.0
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 1.0
    hits = sum(1 for c in letters if any(lo <= ord(c) <= hi for lo, hi in ranges))
    return hits / len(letters)


def validate(en: str, locale: str, target: str) -> str | None:
    """Return an error message, or None when the translation is acceptable."""
    t = (target or "").strip()
    if not t:
        return "empty"
    if re.search(r"\{[a-z_]+\}", t):
        return "unfilled placeholder"
    words = re.findall(r"[A-Za-z]+", en)
    if t == en.strip() and len(en) >= 24 and len(words) >= 4:
        return "identical to English"
    if locale in {"zh-Hans", "zh-Hant"} and BOPOMOFO.search(t):
        # Bopomofo is legitimate only when the page is *about* Zhuyin in zh-Hant
        if locale == "zh-Hans" or not BOPOMOFO.search(en):
            return "contains Bopomofo"
    if locale == "zh-Hans":
        bad = sorted(set(t) & TRAD_ONLY)
        if bad:
            return f"traditional-only characters: {''.join(bad)}"
    # Short strings are usually CTAs or labels dominated by a brand name
    # ("Get Snapport Lite on the App Store"), where a low native-script ratio is
    # correct rather than a sign of an untranslated string.
    if len(en) >= 60:
        ratio = native_ratio(t, locale)
        if ratio < MIN_NATIVE:
            return f"native-script ratio {ratio:.2f} < {MIN_NATIVE}"
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prio", required=True, help="priority list JSON (list of {i, en})")
    ap.add_argument("--batches", required=True, help="directory of batch JSON files")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    prio = json.loads(Path(args.prio).read_text(encoding="utf-8"))
    by_index = {str(item["i"]): item["en"] for item in prio}

    pending: dict[str, dict[str, str]] = {}
    rejected: list[str] = []
    seen = 0
    for path in sorted(Path(args.batches).glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for idx, per_locale in data.items():
            en = by_index.get(str(idx))
            if en is None:
                rejected.append(f"{path.name}: unknown index {idx}")
                continue
            for locale, target in per_locale.items():
                seen += 1
                err = validate(en, locale, target)
                if err:
                    rejected.append(f"{path.name}[{idx}][{locale}]: {err} :: {str(target)[:60]}")
                    continue
                pending.setdefault(locale, {})[en] = target.strip()

    print(f"batches read: {seen} entries, {len(rejected)} rejected")
    for line in rejected[:40]:
        print("  REJECT", line)

    for locale, mapping in sorted(pending.items()):
        path = TRANS / f"{locale}.json"
        current = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        added = sum(1 for k in mapping if k not in current)
        updated = sum(1 for k, v in mapping.items() if k in current and current[k] != v)
        current.update(mapping)
        if not args.dry_run:
            path.write_text(
                json.dumps(current, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        print(f"{locale:<9} +{added} new, {updated} updated, total {len(current)}")
    return 1 if rejected else 0


if __name__ == "__main__":
    raise SystemExit(main())
