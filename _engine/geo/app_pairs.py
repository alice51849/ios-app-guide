#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""付費版↔免費版(Lite)配對登錄 — 「免費版優先」導流規則的唯一事實來源。

背景(2026-08-08 ASC 30 天驗證):11 對兄弟 App 中,付費版 ppv→下載 0–2.7%,
免費/Lite 版 10.9–64.3%,但外宣流量大多導向付費版 = 導錯門。

規則:
  • 品類需求語境(best/vs/tools/hubs/guides/answers 的通用問句)一律導免費版。
  • 付費版連結只出現在「升級/完整版」語境(免費版頁面的升級路徑、明確含
    pro/plus/full 的查詢)。

配對從 videogen registry(APPS/APPSTORE,含 registry_auto.json 自動 App)自動推導:
  • "<key>lite" 存在 → (key, keylite)
  • key 以 "pro"/"plus" 結尾且去掉字尾後存在 → (key, base)
未來新 pair(命名照慣例)自動適用,免改碼;例外走 _EXPLICIT。

用法:
  from app_pairs import free_first_key, upgrade_key, paid_to_free, free_id_for_paid_id
  from app_pairs import paid_name_re, paid_slug_re   # 頁面身份判定(誠實性)
"""
import functools
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if os.path.join(ROOT, "social") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "social"))
from videogen.registry import APPS, APPSTORE  # noqa: E402

# 手動例外(paid_key -> free_key);命名不合慣例的未來 pair 加這裡。
_EXPLICIT = {}

_SUFFIXES = ("pro", "plus")


def paid_to_free():
    """{paid_key: free_key},自動推導 + 例外;2026-08 應為 11 對。"""
    keys = set(APPSTORE) | set(APPS)
    pairs = dict(_EXPLICIT)
    for key in sorted(keys):
        if key + "lite" in keys:
            pairs.setdefault(key, key + "lite")
            continue
        for suffix in _SUFFIXES:
            base = key[: -len(suffix)] if key.endswith(suffix) else ""
            if base and base in keys:
                pairs.setdefault(key, base)
                break
    return pairs


def free_to_paid():
    return {free: paid for paid, free in paid_to_free().items()}


def free_first_key(key):
    """品類需求語境該用的 key:付費版換成免費版,其他原樣。"""
    return paid_to_free().get(key, key)


def upgrade_key(key):
    """免費版的升級目標(付費版 key),沒有配對回傳 ''。"""
    return free_to_paid().get(key, "")


def paid_id_to_free_id():
    """{paid_appstore_id: free_appstore_id},只含兩邊都有 ID 的 pair。"""
    out = {}
    for paid, free in paid_to_free().items():
        pid, fid = APPSTORE.get(paid), APPSTORE.get(free)
        if pid and fid:
            out[pid] = fid
    return out


def free_id_for_paid_id(app_id):
    return paid_id_to_free_id().get(str(app_id), "")


# --------------------------------------------------------------- 頁面身份判定
# 「頁面文案講哪一版,按鈕就開哪一版」— 判斷一頁的可見身份是不是付費版,
# 需要兩個一致的測試,兩個產生器(gen_free_first_links / gen_store_reach)共用。

@functools.lru_cache(maxsize=None)
def paid_name_aliases(paid_key):
    """付費版在文案裡會出現的寫法,長的排前面(先換長的才不會殘留)。

    registry 名稱常帶副標(`TripBee Pro: Trip Planner`),但頁面文案多半只寫
    `TripBee Pro`;只比對完整名稱會漏掉大半可見文字。
    """
    name = APPS.get(paid_key, {}).get("name", "")
    if not name:
        return []
    aliases = [name]
    short = name.split(":")[0].strip()
    if short and short != name:
        aliases.append(short)
    return sorted(set(aliases), key=len, reverse=True)


@functools.lru_cache(maxsize=None)
def paid_name_re(paid_key):
    """比對付費版名稱、但不會誤中免費版名稱的 regex。

    免費版名稱常以付費版名稱為前綴(`Snapport` / `Snapport Lite`),直接用
    `in` 判斷會把換好的頁面誤判成還沒換。
    """
    free_key = paid_to_free().get(paid_key, "")
    free_name = APPS.get(free_key, {}).get("name", "")
    parts = []
    for alias in paid_name_aliases(paid_key):
        pattern = re.escape(alias)
        if free_name.startswith(alias) and free_name != alias:
            pattern += "(?!" + re.escape(free_name[len(alias):]) + ")"
        parts.append(pattern)
    if not parts:
        return re.compile(r"(?!)")  # 永不匹配
    return re.compile("|".join(parts))


@functools.lru_cache(maxsize=None)
def paid_slug_re(paid_key):
    """slug 是否直接點名付費 App。

    slug 是 `lumimathpro-no-subscription`、`aim990plus-vs-…` 這種黏在一起的
    寫法,所以邊界要用「非英數字」而不是連字號,否則一律漏判。
    """
    return re.compile(r"(?<![a-z0-9])" + re.escape(paid_key) + r"(?![a-z0-9])")


_ANCHOR_RE = re.compile(r"<a\b[^>]*>.*?</a>", re.S | re.I)
_HREF_RE = re.compile(r'href="([^"]*)"', re.I)


def is_paid_nav_anchor(anchor_html, paid_key):
    """這個 `<a>` 是不是「站內指向付費版自己頁面」的導覽連結?

    這種連結的錨點文字寫付費版名稱是對的(目的地就是付費版的頁),所以判斷
    「這一頁的文案在講哪一版」時要把它排除,否則每個列出付費版 guide 的索引頁
    都會被判成付費頁。
    """
    match = _HREF_RE.search(anchor_html)
    if not match:
        return False
    url = match.group(1)
    return "apps.apple.com" not in url and bool(paid_slug_re(paid_key).search(url))


def strip_paid_nav_anchors(text, paid_key):
    """回傳把付費版導覽連結拿掉後的文字,用來判斷頁面文案講的是哪一版。"""
    return _ANCHOR_RE.sub(
        lambda m: " " if is_paid_nav_anchor(m.group(0), paid_key) else m.group(0),
        text,
    )


if __name__ == "__main__":
    pairs = paid_to_free()
    print(f"{len(pairs)} pairs:")
    for paid, free in sorted(pairs.items()):
        print(f"  {paid} ({APPSTORE.get(paid, '?')}) -> {free} ({APPSTORE.get(free, '?')})")
