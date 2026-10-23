#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""指南站意圖頁的追蹤碼：款 × 國家 × 詞群，依流量分層開格（gw 階梯碼）。

為什麼（2026-10-23 一億品質監督第 1 次報告 3.1）：意圖頁的 App Store 連結原本由每日改寫統一蓋成
geo_ask／geo_pick，蘋果報表分不出哪一群詞、哪一國帶來下載；第 3 組改成一頁一碼
（ln_<款>_sr_<國>_gw_1023），但蘋果一個追蹤碼要 5 次首次下載才顯示，一頁一國一天永遠達不到。

形狀：ln_<款>_<詞群>_<國>_gw（agent/ct_codes.LN_RE 讀成 geo_pages 通路；最長 28 字元，上限 30）
  款    live_app_manifest 的 key（太長的款用 APP_CODES 短代號）。蘋果本來就逐款出報表，放進碼裡不會多切一刀，只是讓點擊紀錄看得懂。
  詞群  sr 品類主詞（該國使用者真的會搜的詞）／alt 比較與替代（競品名、vs）／
        ss 檔期（節日、連假、季節）／use 情境與問題長尾（怎麼做、壞了怎麼辦）；all＝詞群合併。
  國    兩碼商店國家；ww＝國家合併。
  不帶日期：日期只會把同一批流量切成過不了門檻的小碼；時間由點擊計數的時間戳負責。

階梯（geo/data/gw_campaign_plan.json 決定哪些格子開；沒開的往上併）：
  1. (詞群, 國) 開了 → ln_<款>_<詞群>_<國>_gw
  2. (all, 國) 開了  → ln_<款>_all_<國>_gw          國家優先於詞群
  3. (詞群, ww) 開了 → ln_<款>_<詞群>_ww_gw
  4. 其他            → ln_<款>_all_ww_gw            預設：每款一個碼
開格規則（``plan`` 指令，每週最多改一次）：一格只有在「該款網頁轉介每週首次下載的期望值
（ASC 分國分來源）× 該格在點擊計數裡的占比 ≥ 5」時才開，所以每個碼每週都有機會過門檻；
開了以後剩下的流量仍歸合併碼，合併碼＝該款網頁轉介總數 − 已顯示的格子，可以用減法讀出。
每頁的細節（哪一頁、哪個詞）一律看點擊計數的 p（頁面路徑），不進追蹤碼。

頁面怎麼宣告詞群：產生器在 <head> 放 ``<meta name="growth-attribution-group" content="sr">``。
每日改寫（gen_store_attribution.page_token／final_store_url）看到這個標記，就逐連結用本模組
算碼（連結的款、連結的商店國家、頁面的詞群），不再蓋成 geo_*；QR 卡也走同一個 final_store_url，
所以 QR 圖與連結永遠一致。沒有標記但已帶合格 gw 碼的連結（款對、國是連結的國或 ww）原樣保留，
稽核（audit_store_attribution.validate_reference）只放行這種合格碼。

本檔是 00_GrowthEngine geo/ 的正本，Guide ``_engine/geo/`` 是逐 byte 鏡像。

    python3 geo/gw_campaign.py plan --asc-feedback ~/.growth-private/asc-acquisition-feedback.json \\
        --clicks reports/clicks/daily.csv --pages <Guide 工作樹> [--out geo/data/gw_campaign_plan.json] [--force]
    python3 geo/gw_campaign.py show mochi sr us     # 印出這一格現在用哪個碼
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import functools
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse

HERE = Path(__file__).resolve().parent
PLAN = HERE / "data" / "gw_campaign_plan.json"
SCHEMA = "growth.gw-campaign-plan/v1"

GROUPS = ("sr", "alt", "ss", "use")
GROUP_ZH = {"sr": "品類主詞", "alt": "比較與替代", "ss": "檔期", "use": "情境長尾", "all": "詞群合併"}
ALL = "all"
WW = "ww"
CHANNEL = "gw"
MAX_TOKEN = 30                 # app_store_storefronts.CAMPAIGN_TOKEN_RE
MIN_WEEKLY = 5.0               # 蘋果顯示一個追蹤碼要 5 次首次下載
PLAN_MIN_AGE_DAYS = 7          # 碼每週最多改一次，報表才接得起來
SITE_PREFIX = "/ios-app-guide/"

APP_RE = re.compile(r"^[a-z0-9]+$")
CC_RE = re.compile(r"^[a-z]{2}$")
GW_RE = re.compile(r"^ln_(?P<app>[a-z0-9]+)_(?P<grp>sr|alt|ss|use|all)_(?P<mk>[a-z]{2})_gw$")
META_NAME = "growth-attribution-group"
META_RE = re.compile(
    r'<meta\s+name="growth-attribution-group"\s+content="(?P<grp>[a-z]+)"\s*/?>', re.I)
MARKER_PREFIX = "gw:"
# 名冊 key 太長、放進碼會超過 30 字元的款，碼裡改用短代號（解析時換回名冊 key，比對與報表照舊用 key）。
# 2026-10-23 雙螢幕桌布上架：ln_duowallpaperstudio_alt_ww_gw 是 31 字元。
APP_CODES = {"duowallpaperstudio": "duowallpaper"}
_KEYS_BY_CODE = {code: key for key, code in APP_CODES.items()}
STOREFRONT_RE = re.compile(r"^/(?P<cc>[a-z]{2})/app/")


class GwCampaignError(ValueError):
    pass


# ------------------------------------------------------------------ 頁面標記

def meta_tag(group: str) -> str:
    if group not in GROUPS:
        raise GwCampaignError(f"unknown keyword group: {group!r}")
    return f'<meta name="{META_NAME}" content="{group}">'


def page_group(text: str | None) -> str | None:
    """頁面宣告的詞群；沒有標記回 None，標記不合格直接報錯（不猜）。"""
    if not text:
        return None
    match = META_RE.search(text)
    if match is None:
        return None
    group = match["grp"].lower()
    if group not in GROUPS:
        raise GwCampaignError(f"unknown {META_NAME}: {group!r}")
    return group


def page_marker(group: str, fallback: str) -> str:
    """gen_store_attribution.page_token 用的頁面記號；final_store_url 逐連結換成真正的碼。"""
    if group not in GROUPS:
        raise GwCampaignError(f"unknown keyword group: {group!r}")
    return f"{MARKER_PREFIX}{group}:{fallback}"


def parse_marker(token: str | None) -> tuple[str, str] | None:
    if not token or not token.startswith(MARKER_PREFIX):
        return None
    group, _, fallback = token[len(MARKER_PREFIX):].partition(":")
    if group not in GROUPS or not fallback:
        raise GwCampaignError(f"malformed gw page marker: {token!r}")
    return group, fallback


# ------------------------------------------------------------------ 計畫與碼

def _empty_plan() -> dict:
    return {"schema": SCHEMA, "generated_at": None, "min_weekly_downloads": MIN_WEEKLY, "apps": {}}


@functools.lru_cache(maxsize=8)
def _load_plan_cached(path: str, mtime: float) -> dict:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_plan(doc)
    return doc


def load_plan(path: Path | str = PLAN) -> dict:
    path = Path(os.environ.get("GW_CAMPAIGN_PLAN", path))
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return _empty_plan()
    return _load_plan_cached(str(path), mtime)


def validate_plan(doc: dict) -> None:
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA or not isinstance(doc.get("apps"), dict):
        raise GwCampaignError("gw campaign plan has the wrong shape")
    for app, entry in doc["apps"].items():
        if not APP_RE.fullmatch(app) or not isinstance(entry, dict):
            raise GwCampaignError(f"gw campaign plan: bad app entry {app!r}")
        for cell in entry.get("cells") or []:
            if (not isinstance(cell, list) or len(cell) != 2 or cell[0] not in GROUPS + (ALL,)
                    or not (CC_RE.fullmatch(cell[1]) or cell[1] == WW) or cell == [ALL, WW]):
                raise GwCampaignError(f"gw campaign plan: bad cell {cell!r} for {app}")


def open_cells(app: str, plan: dict | None = None) -> set[tuple[str, str]]:
    plan = load_plan() if plan is None else plan
    entry = (plan.get("apps") or {}).get(app) or {}
    return {(grp, cc) for grp, cc in entry.get("cells") or []}


def token(app: str, group: str, market: str) -> str:
    value = f"ln_{APP_CODES.get(app, app)}_{group}_{market}_{CHANNEL}"
    if len(value) > MAX_TOKEN or not GW_RE.fullmatch(value):
        raise GwCampaignError(f"gw campaign does not fit: {value!r}")
    return value


def campaign(app: str, group: str, cc: str | None, plan: dict | None = None) -> str:
    """這一款、這一個詞群、這一個商店國家的連結現在該帶的碼（照計畫的階梯往上併）。"""
    if not APP_RE.fullmatch(app or ""):
        raise GwCampaignError(f"bad app key: {app!r}")
    if group not in GROUPS:
        raise GwCampaignError(f"unknown keyword group: {group!r}")
    cc = (cc or WW).lower()
    if not (CC_RE.fullmatch(cc)):
        raise GwCampaignError(f"bad storefront country: {cc!r}")
    cells = open_cells(app, plan)
    for cell in ((group, cc), (ALL, cc), (group, WW)):
        if cell in cells:
            return token(app, *cell)
    return token(app, ALL, WW)


def parse(value: str | None) -> dict | None:
    match = GW_RE.fullmatch(value or "")
    if not match:
        return None
    parsed = match.groupdict()
    parsed["app"] = _KEYS_BY_CODE.get(parsed["app"], parsed["app"])
    return parsed


def is_gw(value: str | None) -> bool:
    return parse(value) is not None


def storefront_of(url: str) -> str | None:
    path = urllib.parse.urlsplit(url).path
    match = STOREFRONT_RE.match(path)
    return match["cc"] if match else None


@functools.lru_cache(maxsize=1)
def _keys_by_app_id() -> dict[str, str]:
    from live_app_manifest import canonical_manifest

    return {str(entry["app_id"]): key for key, entry in canonical_manifest()["apps"].items()}


def app_key_for_id(app_id: str | None) -> str | None:
    if not app_id:
        return None
    return _keys_by_app_id().get(str(app_id))


def link_problems(value: str | None, *, app_key: str | None, storefront: str | None) -> list[str]:
    """一個 gw 碼放在這條連結上合不合格：形狀、款要等於連結的款、國要是連結的國或 ww。"""
    parsed = parse(value)
    if parsed is None:
        return [f"not a gw campaign: {value!r}"]
    problems = []
    if app_key is None or parsed["app"] != app_key:
        problems.append(f"{value}: app {parsed['app']!r} is not the linked app {app_key!r}")
    if parsed["mk"] != WW and parsed["mk"] != (storefront or ""):
        problems.append(f"{value}: market {parsed['mk']!r} is not the link storefront {storefront!r}")
    return problems


def stamp_campaign(page_token: str, existing: str | None, url: str, app_id: str | None) -> str | None:
    """每日改寫對一條連結該寫的碼；None＝不是 gw 的情況，呼叫端照原本規則（頁面的 geo_* 碼）。

    * 頁面有詞群標記（page_token 是 gw:<詞群>:<備援>）→ 逐連結重算（款、商店國家、詞群、計畫）；
      連結的 App 不在名冊時用備援碼（原本那個 geo_* 碼）。
    * 沒有標記但連結已帶合格 gw 碼（保護清單）→ 原樣保留。
    """
    key = app_key_for_id(app_id)
    cc = storefront_of(url)
    marker = parse_marker(page_token)
    if marker is not None:
        group, fallback = marker
        if key is None:
            return fallback
        return campaign(key, group, cc)
    if existing and is_gw(existing) and not link_problems(existing, app_key=key, storefront=cc):
        return existing
    return None


# ------------------------------------------------------------------ 每週開格

def _norm_source(name: str) -> str:
    return re.sub(r"[\s_]+", " ", str(name or "")).strip().lower()


def web_referrer_weekly(feedback: dict | None, keys_by_id: dict[str, str] | None = None) -> dict[str, dict[str, float]]:
    """ASC 私有回饋檔 → {款: {國(小寫)或 "*": 每週網頁轉介首次下載}}。"""
    keys_by_id = _keys_by_app_id() if keys_by_id is None else keys_by_id
    days = (feedback or {}).get("window_days") or 30
    try:
        weeks = max(float(days), 1.0) / 7.0
    except (TypeError, ValueError):
        weeks = 30 / 7.0
    out: dict[str, dict[str, float]] = {}
    for entry in (feedback or {}).get("apps") or []:
        if not isinstance(entry, dict):
            continue
        key = keys_by_id.get(str(entry.get("app_id")))
        if not key:
            continue
        row: dict[str, float] = {}
        for source in entry.get("by_source") or []:
            if isinstance(source, dict) and _norm_source(source.get("name")) == "web referrer":
                value = source.get("first_time_downloads")
                if isinstance(value, (int, float)):
                    row["*"] = float(value) / weeks
        for cell in entry.get("by_territory_source") or []:
            if not isinstance(cell, dict) or _norm_source(cell.get("source")) != "web referrer":
                continue
            value = cell.get("first_time_downloads")
            cc = str(cell.get("territory") or "").lower()
            if isinstance(value, (int, float)) and CC_RE.fullmatch(cc):
                row[cc] = row.get(cc, 0.0) + float(value) / weeks
        if row:
            out[key] = row
    return out


def locale_storefront(page: str) -> str | None:
    """點擊紀錄的 p（/ios-app-guide/<語系>/...）→ 那個語系頁連的商店國家；根目錄英文頁＝us。"""
    from app_store_storefronts import LOCALE_STOREFRONTS

    rest = page[len(SITE_PREFIX):] if page.startswith(SITE_PREFIX) else page.lstrip("/")
    first = rest.split("/", 1)[0]
    return LOCALE_STOREFRONTS.get(first) or LOCALE_STOREFRONTS.get("en-US", "us")


def page_groups(pages_dir: Path | None, paths: set[str]) -> dict[str, str]:
    """只讀點擊紀錄出現過的頁面，取它宣告的詞群（沒有標記的頁不是 gw 頁）。"""
    out: dict[str, str] = {}
    if pages_dir is None:
        return out
    for page in paths:
        rest = page[len(SITE_PREFIX):] if page.startswith(SITE_PREFIX) else None
        if rest is None:
            continue
        target = pages_dir / (rest + "index.html" if rest.endswith("/") or not rest else rest)
        try:
            text = target.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            group = page_group(text)
        except GwCampaignError:
            group = None
        if group:
            out[page] = group
    return out


def click_cells(rows, groups: dict[str, str], keys_by_id: dict[str, str] | None = None,
                today: dt.date | None = None, days: int = 28) -> dict[str, collections.Counter]:
    """reports/clicks/daily.csv 的列 → {款: Counter((詞群, 國))}，只算有詞群標記的 App Store 點擊。"""
    keys_by_id = _keys_by_app_id() if keys_by_id is None else keys_by_id
    start = (today - dt.timedelta(days=days - 1)).isoformat() if today else ""
    out: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for row in rows:
        if row.get("store") != "apple" or (start and row.get("date", "") < start):
            continue
        group = groups.get(row.get("page") or "")
        key = keys_by_id.get(str(row.get("app") or ""))
        if not group or not key:
            continue
        parsed = parse(row.get("ct"))
        cc = parsed["mk"] if parsed and parsed["mk"] != WW else locale_storefront(row.get("page") or "")
        try:
            clicks = int(float(row.get("clicks") or 0))
        except ValueError:
            continue
        out[key][(group, cc or WW)] += clicks
    return out


def build_plan(web: dict[str, dict[str, float]], clicks: dict[str, collections.Counter],
               now: dt.datetime, min_weekly: float = MIN_WEEKLY) -> dict:
    """每格期望每週下載 ≥ min_weekly 才開；其他併回合併碼。"""
    apps: dict[str, dict] = {}
    for app in sorted(set(web) | set(clicks)):
        totals = web.get(app) or {}
        by_cc = {cc: v for cc, v in totals.items() if cc != "*"}
        total = totals.get("*", sum(by_cc.values()))
        counter = clicks.get(app) or collections.Counter()
        all_clicks = sum(counter.values())
        cells: set[tuple[str, str]] = set()
        evidence = {}
        for cc, weekly in by_cc.items():
            if weekly >= min_weekly:
                cells.add((ALL, cc))
                evidence[f"{ALL}_{cc}"] = round(weekly, 2)
            cc_clicks = sum(n for (g, c), n in counter.items() if c == cc)
            for group in GROUPS:
                share = counter[(group, cc)] / cc_clicks if cc_clicks else 0.0
                if weekly * share >= min_weekly:
                    cells.add((group, cc))
                    evidence[f"{group}_{cc}"] = round(weekly * share, 2)
        for group in GROUPS:
            share = sum(n for (g, _), n in counter.items() if g == group) / all_clicks if all_clicks else 0.0
            if total * share >= min_weekly:
                cells.add((group, WW))
                evidence[f"{group}_{WW}"] = round(total * share, 2)
        if cells:
            apps[app] = {"cells": [list(cell) for cell in sorted(cells)], "expected_weekly": evidence,
                         "web_referrer_weekly": round(total, 2)}
    doc = {"schema": SCHEMA, "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
           "min_weekly_downloads": min_weekly, "apps": apps}
    validate_plan(doc)
    return doc


def _read_json(path: Path | None):
    if path is None:
        return None
    try:
        return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _read_csv(path: Path | None) -> list[dict]:
    if path is None:
        return []
    try:
        with Path(path).open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    except OSError:
        return []


def plan_due(existing: dict, now: dt.datetime) -> bool:
    stamp = existing.get("generated_at")
    if not stamp:
        return True
    try:
        last = dt.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return True
    return now - last >= dt.timedelta(days=PLAN_MIN_AGE_DAYS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan", help="每週依 ASC 網頁轉介與點擊占比重算開格")
    p.add_argument("--asc-feedback", type=Path)
    p.add_argument("--clicks", type=Path)
    p.add_argument("--pages", type=Path, help="Guide 工作樹（讀點擊頁的詞群標記）")
    p.add_argument("--out", type=Path, default=PLAN)
    p.add_argument("--force", action="store_true", help="不到 7 天也重算")
    p.add_argument("--now")
    s = sub.add_parser("show", help="印出一格現在的碼")
    s.add_argument("app")
    s.add_argument("group")
    s.add_argument("cc")
    args = parser.parse_args(argv)
    if args.cmd == "show":
        print(campaign(args.app, args.group, args.cc))
        return 0
    now = (dt.datetime.fromisoformat(args.now.replace("Z", "+00:00")) if args.now
           else dt.datetime.now(dt.timezone.utc))
    existing = _read_json(args.out) or _empty_plan()
    if not args.force and not plan_due(existing, now):
        print(f"gw plan: 上次 {existing.get('generated_at')}，未滿 {PLAN_MIN_AGE_DAYS} 天，不改")
        return 0
    feedback = _read_json(args.asc_feedback)
    if feedback is None:
        print("::warning::gw plan: 沒有 ASC 回饋檔，計畫不改（不知道就不開格）")
        return 0
    rows = _read_csv(args.clicks)
    groups = page_groups(args.pages, {row.get("page") or "" for row in rows})
    doc = build_plan(web_referrer_weekly(feedback), click_cells(rows, groups, today=now.date()), now)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    opened = sum(len(entry["cells"]) for entry in doc["apps"].values())
    print(f"gw plan: {len(doc['apps'])} 款有開格，共 {opened} 格；其他款每款一個合併碼 ln_<款>_all_ww_gw")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    raise SystemExit(main())
