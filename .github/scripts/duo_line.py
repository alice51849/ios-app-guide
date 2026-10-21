#!/usr/bin/env python3
"""iPhone Duo 一句（社群貼文、短片說明欄共用）：可宣稱的款＋該語系 social_line，不合就回傳空字串。

正本：00_GrowthEngine aso/duo/duo_line.py。逐 byte 副本：ios-app-guide .github/scripts/duo_line.py、
threads-autopilot duo_line.py（aso/duo/sync_duo_copies.py 複製並記錄雜湊，各 repo 的 test_duo_line.py 核對）。
規則正本 ops/company/duo_claim_rules.md：
  * 款只取 aso/duo/duo_list.py 的 load()（不另抄清單）；句子只取 aso/duo/claim_lines.json 的 social_line，
    且 aso/duo/review_second_model.json 該語系 social_line 複審 PASS、句子一字不差；
  * 公開查詢（iTunes Lookup）讀到的線上版本號要等於清單的 live_version，查不到或不同就不加；
  * 加上去會超過平台字數上限就不加（寧可不加，也不讓發文失敗或擠掉下載連結）；文字已含 iPhone Duo 也不加。
資料位置（找第一個有 aso/duo/duo_list.py 的）：本檔旁的 duo_source/（threads-autopilot）、
repo 根的 _engine/（ios-app-guide）、repo 根（00_GrowthEngine）；環境變數 DUO_DATA_ROOT 可指定。
"""
from __future__ import annotations

import functools
import importlib.util
import json
import os
import re
import urllib.request
from pathlib import Path

NAME = "iPhone Duo"
_FILE = Path(__file__).resolve()
# 語系別名：貼文用的語系碼 -> claim_lines.json 的語系碼。
ALIASES = {"zh-TW": "zh-Hant", "zh-HK": "zh-Hant", "zh-MO": "zh-Hant", "zh-CN": "zh-Hans", "zh-SG": "zh-Hans",
           "nb": "no", "nn": "no", "iw": "he", "in": "id", "en-IE": "en-GB", "en-NZ": "en-AU"}
LOOKUP_URL = "https://itunes.apple.com/lookup?id={id}&country={cc}"
LOOKUP_COUNTRIES = ("us", "tw")


def data_root():
    env = os.environ.get("DUO_DATA_ROOT", "").strip()
    candidates = [Path(env)] if env else [_FILE.parent / "duo_source", _FILE.parents[2] / "_engine", _FILE.parents[2]]
    for root in candidates:
        if (root / "aso" / "duo" / "duo_list.py").is_file():
            return root
    return None


@functools.lru_cache(maxsize=1)
def _state():
    """({app_id: app, slug: app}, {locale: line}, {已複審 PASS 的 locale: line})；任何一份讀不了就是空的（不宣稱）。"""
    root = data_root()
    if root is None:
        return {}, {}, {}
    try:
        spec = importlib.util.spec_from_file_location("duo_list_for_duo_line", root / "aso" / "duo" / "duo_list.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        apps, _rejected, error = module.load()
        lines = json.loads((root / "aso" / "duo" / "claim_lines.json").read_text(encoding="utf-8")).get("social_line")
        review = json.loads((root / "aso" / "duo" / "review_second_model.json").read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - 讀不了就不宣稱
        return {}, {}, {}
    if error or not isinstance(lines, dict):
        return {}, {}, {}
    passed = {}
    for it in review.get("items") or []:
        if not isinstance(it, dict) or (it.get("field") or it.get("kind")) != "social_line":
            continue
        loc = it.get("locale")
        line = lines.get(loc)
        if str(it.get("verdict") or "").upper() != "PASS" or not isinstance(line, str) or not line.strip():
            continue
        if "text" in it and it["text"] != line:
            continue
        passed[loc] = line.strip()
    by = {}
    for app in apps:
        by[str(app["app_id"])] = app
        by[str(app["slug"])] = app
    return by, {k: v for k, v in lines.items() if isinstance(v, str)}, passed


def reset():
    _state.cache_clear()
    _live_versions.cache_clear()


def locale_of(lang, lines):
    """貼文語系碼對到 claim_lines.json 的語系碼（對不到＝None）。"""
    lang = str(lang or "").strip().replace("_", "-")
    if not lang:
        return None
    if lang in lines:
        return lang
    alias = ALIASES.get(lang)
    if alias in lines:
        return alias
    base, _, region = lang.partition("-")
    base = base.lower()
    if base == "zh":
        return None   # 繁簡不明就不加
    if base == "es" and region and region.upper() != "ES" and "es-MX" in lines:
        return "es-MX"
    return next((loc for loc in lines if loc.split("-")[0].lower() == base), None)


@functools.lru_cache(maxsize=1)
def _live_versions():
    """{app_id: 線上版本號}：所有可宣稱款一次批次查（iTunes Lookup 一個請求可帶多個 id，避免連發被 Apple 限流），
    美國商店查不到的款再查台灣商店；請求失敗就停（查不到的款不宣稱）。"""
    ids = sorted({str(a["app_id"]) for a in _state()[0].values()})
    out = {}
    for cc in LOOKUP_COUNTRIES:
        todo = [i for i in ids if i not in out]
        if not todo:
            break
        try:
            with urllib.request.urlopen(LOOKUP_URL.format(id=",".join(todo), cc=cc), timeout=15) as r:
                rows = json.loads(r.read().decode("utf-8")).get("results") or []
        except Exception:  # noqa: BLE001 - 查不到就不宣稱
            break
        for row in rows:
            if str(row.get("trackId")) in todo and row.get("version"):
                out[str(row["trackId"])] = str(row["version"])
    return out


def _live_version(app_id):
    """iTunes Lookup 讀到的線上版本號；查不到＝None。"""
    return _live_versions().get(str(app_id))


def app_key(app):
    """款的代號：App Store id（數字）、名冊 key，或 App Store 連結（取 id）。"""
    text = str(app or "").strip()
    m = re.search(r"/id(\d{6,})", text)
    return m.group(1) if m else text


def line(app, lang, lookup=None):
    """該款該語系的 iPhone Duo 一句；款不可宣稱、語系沒有已複審的句子、線上版本對不上＝空字串。"""
    by, lines, passed = _state()
    entry = by.get(app_key(app))
    loc = locale_of(lang, lines) if entry else None   # 先對全部語系，再要求那一個語系已複審（不借用鄰近語系）
    if not entry or loc not in passed:
        return ""
    live = (lookup or _live_version)(str(entry["app_id"]))
    if not live or str(live) != str(entry["live_version"]):
        return ""
    return passed[loc]


def known_lines(lang):
    """claim_lines.json 裡這個語系的 social_line（不看清單、複審、線上版本）：只給「已發過沒」的比對用，
    讓一則帶句發出的貼文在之後查不到線上版本時仍認得出來（不重發）；不可拿來發文。"""
    _by, lines, _passed = _state()
    loc = locale_of(lang, lines)
    return [lines[loc].strip()] if loc and lines[loc].strip() else []


def fits(text, duo, limit, sep="\n\n"):
    return bool(duo) and NAME not in (text or "") and (limit is None or len(text or "") + len(sep) + len(duo) <= limit)


def append(text, app, lang, limit=None, sep="\n\n", lookup=None):
    """text 後加一句（加了會超過 limit 就原文不動）。"""
    duo = line(app, lang, lookup)
    return f"{text}{sep}{duo}" if fits(text, duo, limit, sep) else text


if __name__ == "__main__":
    import sys
    print(json.dumps({"data_root": str(data_root()), "claimable": len({a["app_id"] for a in _state()[0].values()}),
                      "locales": len(_state()[2]),
                      "sample": line(sys.argv[1], sys.argv[2]) if len(sys.argv) == 3 else None},
                     ensure_ascii=False))
