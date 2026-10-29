#!/usr/bin/env python3
"""下載按鈕匿名點擊計數:支援站與指南站共用的唯一一份。

2026-10-20:蘋果不揭露「網站頁面 → 按下載」這一段,ASC 只看得到最後的下載。
每頁放一小段內嵌 JS:點到 App Store／Google Play 連結時用 sendBeacon 送
{p: 路徑, a: App id／key, ct: 連結的 ct, s: apple|play} 到自家伺服器
(office.cait518.cc/api/click,本機 AgentOffice)。字串 body 是 text/plain,
不觸發 CORS 預檢;不用 cookie、不送識別碼、伺服器不存 IP,只累計點擊數,
是第一方匿名計數。任何錯誤都吞掉,不 preventDefault,絕不擋導向;
下載連結本身(直連、ct)不動。

使用者
------
* 支援站:``support_network/gen_support_crosspromo.py``(``apply_click_beacon``)
  與 ``gen_support_help.py`` 匯入本模組的 ``click_beacon_block``。
* 指南站(2026-10-23 起):Guide ``.github/workflows/pages.yml`` 部署前執行
  ``python3 _engine/geo/click_beacon.py inject --pages .``,把同一塊放到每頁
  ``</head>`` 前(冪等;只在部署產物裡加,不改 repo 裡的頁面)。以下頁面不放:
  - 其他產生器按位元組釘選的頁面(hero 工具頁、高意圖決策頁、結果圖庫),
    放了會讓它們的 --check 與線上讀回失敗;
  - 有 Content-Security-Policy meta 的頁面(``script-src 'self'``、
    ``connect-src 'none'`` 會擋內嵌 JS 與 sendBeacon,而且這些是「只在本機
    運算」的工具頁);
  - AMP 網頁故事(AMP 不允許自訂 JS);
  - ``</head>`` 不是剛好一個的頁面(位置不明就不猜)。

人工智慧來源追蹤碼(2026-10-29 主動發現卡 5,只套雙螢幕桌布):``inject`` 同時在
``AICT_APPS`` 那幾款自己的頁面(路徑含該款 key、頁上有該款 App Store 連結)放第二塊
內嵌 JS。來源網址主機或網址 ``utm_source`` 是 ChatGPT／Perplexity／Gemini／Copilot 時,
把頁上該款 App Store 下載連結的 ct 換成 ``ai_<引擎>``、該款 Play 連結 referrer 的
utm_source 換成同一碼(utm_campaign 照舊是款 key);沒有人工智慧來源時完全不動。
repo 裡的頁面與靜態連結不變(只在部署產物執行時改),點擊計數在點擊當下讀 ct,
所以人工智慧來源的點擊也記成 ai_ 碼。判讀:蘋果活動報表各 ai_ 碼的瀏覽／首次下載,
11-26 仍 0 下載就收掉(``AICT_APPS`` 清空即全部移除)。

本檔是 00_GrowthEngine geo/ 的正本,Guide ``_engine/geo/`` 是逐 byte 鏡像。
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys


CLICK_BEACON_URL = "https://office.cait518.cc/api/click"
CLICK_START = "<!-- ls-clickbeacon:start -->"
CLICK_END = "<!-- ls-clickbeacon:end -->"
CLICK_RE = re.compile(
    re.escape(CLICK_START) + r".*?" + re.escape(CLICK_END) + r"\n?",
    re.S,
)
_CLICK_JS = (
    "(function(){var E='" + CLICK_BEACON_URL + "';"
    "function h(e){try{var t=e.target,l=t&&t.closest&&t.closest('a[href]');"
    "if(!l||!navigator.sendBeacon)return;"
    "var u=new URL(l.href,location.href),s,k,c,q=u.searchParams;"
    "if(u.hostname==='apps.apple.com'){s='apple';"
    "k=(u.pathname.match(/\\/id(\\d+)/)||[])[1]||'';c=q.get('ct')||''}"
    "else if(u.hostname==='play.google.com'){s='play';"
    "var r=new URLSearchParams(q.get('referrer')||'');"
    "k=r.get('utm_campaign')||q.get('id')||'';c=r.get('utm_source')||''}"
    "else return;"
    "navigator.sendBeacon(E,JSON.stringify({p:location.pathname.slice(0,200),"
    "a:k.slice(0,100),ct:c.slice(0,64),s:s}))}catch(_){}}"
    "document.addEventListener('click',h,true);"
    "document.addEventListener('auxclick',h,true)})();"
)


# ------------------------------------------------------------ 人工智慧來源追蹤碼
# 款 key → App Store id。只放進這裡的款才會帶這塊(11-26 判讀;0 下載就清空)。
AICT_APPS = {"duowallpaperstudio": "6824946559"}
# 來源主機(含子網域)→ ct;utm_source 也接受這些主機或第一段名稱(chatgpt、perplexity…)。
AICT_ENGINES = (
    ("chatgpt.com", "ai_chatgpt"),
    ("chat.openai.com", "ai_chatgpt"),
    ("perplexity.ai", "ai_perplexity"),
    ("gemini.google.com", "ai_gemini"),
    ("copilot.microsoft.com", "ai_copilot"),
    ("copilot.com", "ai_copilot"),
)
AICT_NAMES = {"chatgpt": "ai_chatgpt", "openai": "ai_chatgpt", "perplexity": "ai_perplexity",
              "gemini": "ai_gemini", "copilot": "ai_copilot"}
AICT_START = "<!-- ls-aict:start -->"
AICT_END = "<!-- ls-aict:end -->"
AICT_RE = re.compile(re.escape(AICT_START) + r".*?" + re.escape(AICT_END) + r"\n?", re.S)


def _aict_js() -> str:
    engines = json.dumps([list(row) for row in AICT_ENGINES], separators=(",", ":"))
    names = json.dumps(AICT_NAMES, separators=(",", ":"), sort_keys=True)
    ids = json.dumps({v: k for k, v in AICT_APPS.items()}, separators=(",", ":"), sort_keys=True)
    keys = json.dumps(sorted(AICT_APPS), separators=(",", ":"))
    return (
        "(function(){try{var M=" + engines + ",N=" + names + ",I=" + ids + ",K=" + keys + ";"
        "function m(h){h=String(h||'').toLowerCase().replace(/^\\s+|\\s+$/g,'').replace(/^www\\./,'');"
        "if(!h)return'';for(var i=0;i<M.length;i++){var d=M[i][0];"
        "if(h===d||h.slice(-d.length-1)==='.'+d)return M[i][1]}"
        "return Object.prototype.hasOwnProperty.call(N,h)?N[h]:''}"
        "var c='';try{c=m(new URLSearchParams(location.search).get('utm_source'))}catch(_){}"
        "if(!c&&document.referrer){try{c=m(new URL(document.referrer).hostname)}catch(_){}}"
        "if(!c)return;"
        "function f(){var a=document.querySelectorAll('a[href]');for(var i=0;i<a.length;i++){try{"
        "var u=new URL(a[i].href),q=u.searchParams,x=u.pathname.match(/\\/id(\\d+)/);"
        "if(u.hostname==='apps.apple.com'&&x&&I[x[1]]&&q.has('ct')&&!q.has('action')){"
        "q.set('ct',c);a[i].href=u.toString()}"
        "else if(u.hostname==='play.google.com'&&q.get('referrer')){"
        "var r=new URLSearchParams(q.get('referrer'));"
        "if(K.indexOf(r.get('utm_campaign'))>=0&&r.get('utm_source')){"
        "r.set('utm_source',c);q.set('referrer',r.toString());a[i].href=u.toString()}}"
        "}catch(_){}}}"
        "if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',f);else f()"
        "}catch(_){}})();"
    )


def ai_ct_block() -> str:
    """受管的人工智慧來源追蹤碼區塊(只放在 AICT_APPS 那幾款自己的頁面)。"""
    return f"{AICT_START}\n<script>{_aict_js()}</script>\n{AICT_END}"


def ai_ct_app(relative: str, source: str) -> str | None:
    """這頁屬於哪一款 AICT_APPS(路徑一段以款 key 開頭、頁上有該款 App Store 連結),否則 None。"""
    for key, app_id in AICT_APPS.items():
        if re.search(r"(?:^|/)" + re.escape(key) + r"(?:[./-]|$)", relative) and (
            f"/id{app_id}?" in source or f"/id{app_id}\"" in source
        ):
            return key
    return None


def inject_ai_ct_html(source: str, wanted: bool) -> tuple[str, str]:
    """與 inject_html 同一套規則放／移除人工智慧來源追蹤碼區塊;wanted=False 只移除。"""
    found = list(AICT_RE.finditer(source))
    if source.count(AICT_START) != len(found) or source.count(AICT_END) != len(found):
        return source, SKIP_MALFORMED
    block = ai_ct_block()
    stripped = AICT_RE.sub("", source) if found else source
    if not wanted:
        return stripped, (REMOVED if found else UNCHANGED)
    if _CSP_RE.search(stripped):
        return stripped, (REMOVED if found else SKIP_CSP)
    if _AMP_RE.search(stripped):
        return stripped, (REMOVED if found else SKIP_AMP)
    if len(found) == 1 and found[0].group(0).rstrip("\n") == block:
        return source, UNCHANGED
    closes = list(_HEAD_CLOSE_RE.finditer(stripped))
    if len(closes) != 1:
        return stripped, (REMOVED if found else SKIP_HEAD)
    at = closes[0].start()
    return stripped[:at] + block + "\n" + stripped[at:], ADDED


def click_beacon_block() -> str:
    """受管的點擊計數區塊(支援站、help 頁、指南站輸出同一塊,位元組一致)。"""
    return f"{CLICK_START}\n<script>{_CLICK_JS}</script>\n{CLICK_END}"


# ------------------------------------------------------------ 指南站部署前注入
PAGES = Path(os.environ.get("GEO_PAGES", Path(__file__).resolve().parent / "pages"))
# 引擎、CI 資料與相依套件不是網站頁面。
EXCLUDED_PARTS = frozenset({".git", ".github", "_engine", "node_modules"})
_CSP_RE = re.compile(r"<meta\b[^>]*\bhttp-equiv\s*=\s*[\"']?content-security-policy", re.I)
# AMP 文件:<html ⚡>／<html amp>(含 4email／4ads)與網頁故事 <amp-story>。
_AMP_RE = re.compile(
    r"<html\b[^>]*?\s(?:⚡|amp)(?:4email|4ads)?(?=[\s/>=])|<amp-story[\s>]", re.I
)
_HEAD_CLOSE_RE = re.compile(r"</head\s*>", re.I)

ADDED, UNCHANGED, REMOVED = "added", "unchanged", "removed"
SKIP_CSP, SKIP_AMP, SKIP_HEAD, SKIP_MALFORMED = "skip_csp", "skip_amp", "skip_head", "skip_malformed"


def _pinned_paths(pages: Path) -> set[str]:
    """其他產生器按位元組釘選的頁面(它們的 --check 與線上讀回比對整頁 sha256)。"""
    pinned: set[str] = set()

    def load(relative: str):
        try:
            return json.loads((pages / relative).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    hero = load("data/hero-tasks/manifest.json")
    if isinstance(hero, dict) and isinstance(hero.get("outputs"), dict):
        pinned.update(str(path) for path in hero["outputs"])
    routes = load("data/high-intent-decision-routes/expected-output-manifest.json")
    if isinstance(routes, dict) and isinstance(routes.get("expected_outputs"), list):
        pinned.update(str(row.get("relative_path")) for row in routes["expected_outputs"]
                      if isinstance(row, dict) and row.get("relative_path"))
    gallery = load("data/result-image-coverage.json")
    if isinstance(gallery, dict):
        for field in ("pages", "retired_pages"):
            if isinstance(gallery.get(field), dict):
                pinned.update(str(path) for path in gallery[field])
    return pinned


def inject_html(source: str) -> tuple[str, str]:
    """回傳 (新內容, 狀態)。冪等:已有一塊正確的就原樣不動;舊版或多餘的移除後
    在唯一的 ``</head>`` 前放一塊。不能放的頁面(CSP、AMP、``</head>`` 不唯一)
    只移除受管區塊、不新增;標記壞掉的頁面原樣不動。"""
    found = list(CLICK_RE.finditer(source))
    if source.count(CLICK_START) != len(found) or source.count(CLICK_END) != len(found):
        return source, SKIP_MALFORMED
    block = click_beacon_block()
    stripped = CLICK_RE.sub("", source) if found else source
    if _CSP_RE.search(stripped):
        return stripped, (REMOVED if found else SKIP_CSP)
    if _AMP_RE.search(stripped):
        return stripped, (REMOVED if found else SKIP_AMP)
    if len(found) == 1 and found[0].group(0).rstrip("\n") == block:
        return source, UNCHANGED
    closes = list(_HEAD_CLOSE_RE.finditer(stripped))
    if len(closes) != 1:
        return stripped, (REMOVED if found else SKIP_HEAD)
    at = closes[0].start()
    return stripped[:at] + block + "\n" + stripped[at:], ADDED


def site_pages(pages: Path):
    """部署產物裡的 HTML 頁(不進排除的資料夾、不碰符號連結與釘選頁)。"""
    pinned = _pinned_paths(pages)
    for directory, subdirs, files in os.walk(pages):
        subdirs[:] = sorted(d for d in subdirs if d not in EXCLUDED_PARTS)
        for name in sorted(files):
            if not name.endswith(".html"):
                continue
            path = Path(directory) / name
            if path.is_symlink():
                continue
            if path.relative_to(pages).as_posix() in pinned:
                continue
            yield path


def inject_tree(pages: Path = PAGES) -> dict[str, int]:
    pages = Path(pages)
    stats = {"scanned": 0, "with_beacon": 0, ADDED: 0, UNCHANGED: 0, REMOVED: 0,
             SKIP_CSP: 0, SKIP_AMP: 0, SKIP_HEAD: 0, SKIP_MALFORMED: 0,
             "pinned": len(_pinned_paths(pages)), "non_utf8": 0, "io_error": 0,
             "ai_ct_pages": 0, "ai_ct_skipped": 0}
    for path in site_pages(pages):
        stats["scanned"] += 1
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            stats["non_utf8"] += 1
            continue
        except OSError:
            stats["io_error"] += 1
            continue
        updated, status = inject_html(source)
        relative = path.relative_to(pages).as_posix()
        app = ai_ct_app(relative, updated)
        if app or AICT_START in updated:
            updated, ai_status = inject_ai_ct_html(updated, bool(app))
            if app and ai_status in (ADDED, UNCHANGED):
                stats["ai_ct_pages"] += 1
            elif app:
                stats["ai_ct_skipped"] += 1
        if updated != source:
            try:
                path.write_text(updated, encoding="utf-8")
            except OSError:
                stats["io_error"] += 1
                continue
        stats[status] += 1
        if status in (ADDED, UNCHANGED):
            stats["with_beacon"] += 1
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    inject = sub.add_parser("inject", help="在部署產物每頁 </head> 前放點擊計數區塊")
    inject.add_argument("--pages", type=Path, default=PAGES)
    sub.add_parser("block", help="印出點擊計數區塊")
    sub.add_parser("ai-block", help="印出人工智慧來源追蹤碼區塊")
    args = parser.parse_args(argv)
    if args.command == "block":
        print(click_beacon_block())
        return 0
    if args.command == "ai-block":
        print(ai_ct_block())
        return 0
    stats = inject_tree(args.pages)
    print("click beacon: " + json.dumps(stats, sort_keys=True))
    if stats["with_beacon"] == 0:
        # 計數失效不擋上線,但要紅字讓巡檢看得到。
        print("::warning::click beacon: no page carries the download-click counter",
              file=sys.stderr)
    for field in (SKIP_MALFORMED, "io_error"):
        if stats[field]:
            print(f"::warning::click beacon: {stats[field]} pages {field}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
