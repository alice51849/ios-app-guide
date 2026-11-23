#!/usr/bin/env python3
"""指南站「停新增網址」守門（審核員 K1 11-23 定案）。

開關＝``geo/data/new_url_freeze.json`` 的 ``freeze_new_urls``（單一旗標；檔案缺漏
時視為開啟，照 K1 定案 fail closed）。開啟時：

* 既有網站上沒有的新頁（站台目錄 ``GEO_PAGES`` 的 git HEAD 沒追蹤的 ``*.html`` 與
  ``sitemap*.xml``）一律移除，不上線；既有頁照常重產、不受影響。
* 網站地圖只保留 HEAD 版網站地圖已有的 ``<loc>``；新增的 ``<url>``／``<sitemap>``
  條目剝除。
* 唯一例外：上架 14 天內新款的 App 頁，只限寫死語系 ``en-US``、``en-GB``、
  ``en-AU``（``<語系>/<key>.html``）。新款判定沿用 ``agent/rank_snapshot.new_apps``
  （指南站沒有 agent/ 時用同規則讀 ``geo/data/launch_blitz_apps.json``）。

被擋的新網址數印一行到 stdout，並累計到 json 計數檔（``GEO_NEW_URL_FREEZE_LOG``，
預設 ``$GEO_REPORTS/new_url_freeze.json``），供 K1 ③ 名額轉移讀。

接線：``gen_link_hubs.py``（所有頁面產生器之後、連結圖與網站地圖封閉之前）與
``gen_sitemap_lastmod.py``（最後一次實體化之後、發布前稽核之前）的 main 開頭各呼叫
一次 ``enforce``，冪等。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
FLAG_PATH = HERE / "data" / "new_url_freeze.json"
LAUNCH_LIST = HERE / "data" / "launch_blitz_apps.json"
EXCEPTION_LOCALES = ("en-US", "en-GB", "en-AU")  # K1 寫死，不擴大
NEW_DAYS = 14
TPE = timezone(timedelta(hours=8))
_LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>")
_ENTRY_RE = re.compile(r"\s*<(url|sitemap)>.*?</\1>", re.S)
_SITEMAP_NAME = re.compile(r"(^|/)sitemap[^/]*\.xml$")
BLOCKED_LIST_CAP = 500


def is_frozen(flag_path: Path = FLAG_PATH) -> bool:
    try:
        document = json.loads(Path(flag_path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return True
    except (OSError, ValueError) as error:
        raise RuntimeError(f"Invalid new URL freeze flag: {flag_path}") from error
    return document.get("freeze_new_urls", True) is not False


def today_tpe() -> date:
    return datetime.now(TPE).date()


def new_app_keys(today: date | None = None, launch_list: Path = LAUNCH_LIST) -> set[str]:
    """上架 14 天內（含第 14 天）的款；沿用 agent/rank_snapshot.new_apps。"""
    today = today or today_tpe()
    root = HERE.parent
    if (root / "agent" / "rank_snapshot.py").is_file():
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        from agent.rank_snapshot import new_apps  # 既有函式，同一條 14 天規則

        return new_apps(today, Path(launch_list))
    try:
        document = json.loads(Path(launch_list).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    out: set[str] = set()
    for app in document.get("apps") or []:
        try:
            launched = date.fromisoformat(str(app.get("上架", ""))[:10])
        except ValueError:
            continue
        if 0 <= (today - launched).days <= NEW_DAYS:
            for key in (app.get("key"), app.get("名冊key")):
                if key:
                    out.add(str(key).lower())
    return out


def exception_paths(today: date | None = None, launch_list: Path = LAUNCH_LIST) -> set[str]:
    return {
        f"{locale}/{key}.html"
        for key in new_app_keys(today, launch_list)
        for locale in EXCEPTION_LOCALES
    }


def _normalise(path: str) -> str:
    return path.replace(os.sep, "/").lstrip("/")


def allow_new_url(
    path: str,
    today: date | None = None,
    *,
    flag_path: Path = FLAG_PATH,
    launch_list: Path = LAUNCH_LIST,
) -> bool:
    """站台相對路徑或完整網址 ``path`` 若是新網址，可不可以產生。"""
    if not is_frozen(flag_path):
        return True
    relative = _normalise(urlsplit(path).path if "://" in path else path)
    allowed = exception_paths(today, launch_list)
    return relative in allowed or any(relative.endswith("/" + p) for p in allowed)


def _git(pages: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=pages, capture_output=True, text=True, check=True
    )
    return result.stdout


# gen_link_hubs 在關口之後才產生、且既有頁已注入連結的分頁結構頁（browse.html、browse-2.html…）：
# 刪了會留死連結（2.7 反方 K1 必改 1），一律保留、另記「結構頁」。
STRUCTURAL_RE = re.compile(r"^browse(-\d+)?\.html$")


def _structural(relative: str) -> bool:
    return bool(STRUCTURAL_RE.match(relative.rsplit("/", 1)[-1]))


def _skippable(relative: str) -> bool:
    parts = relative.split("/")
    return parts[0] == "_engine" or any(part.startswith(".") for part in parts)


def untracked_url_files(pages: Path) -> list[str]:
    """站台目錄裡 HEAD 沒有的新頁與新網站地圖（.gitignore 的不算）。"""
    raw = _git(pages, "status", "--porcelain", "--untracked-files=all", "-z")
    out = []
    for record in raw.split("\0"):
        if not record.startswith("?? "):
            continue
        relative = record[3:]
        if _skippable(relative):
            continue
        if relative.endswith(".html") or _SITEMAP_NAME.search(relative):
            out.append(relative)
    return sorted(out)


def tracked_sitemaps(pages: Path) -> list[str]:
    raw = _git(pages, "ls-files", "-z")
    return sorted(
        p for p in raw.split("\0") if p and _SITEMAP_NAME.search(p) and not _skippable(p)
    )


def baseline_sitemap_locs(pages: Path) -> set[str]:
    locs: set[str] = set()
    for relative in tracked_sitemaps(pages):
        try:
            text = _git(pages, "show", f"HEAD:{relative}")
        except subprocess.CalledProcessError:
            continue
        locs.update(_LOC_RE.findall(text))
    return locs


def strip_new_sitemap_entries(path: Path, baseline: set[str], allowed: set[str]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    stripped: list[str] = []

    def keep(match: re.Match) -> str:
        found = _LOC_RE.search(match.group(0))
        if not found:
            return match.group(0)
        loc = found.group(1)
        if loc in baseline:
            return match.group(0)
        loc_path = urlsplit(loc).path
        if _structural(loc_path) or any(loc_path.endswith("/" + p) for p in allowed):
            return match.group(0)
        stripped.append(loc)
        return ""

    updated = _ENTRY_RE.sub(keep, text)
    if updated != text:
        path.write_text(updated, encoding="utf-8")
    return stripped


def default_log_path() -> Path:
    override = os.environ.get("GEO_NEW_URL_FREEZE_LOG")
    if override:
        return Path(override)
    base = os.environ.get("GEO_REPORTS") or tempfile.gettempdir()
    return Path(base) / "new_url_freeze.json"


def _record(log_path: Path, today: date, stage: str, blocked: list[str],
            stripped: list[str], allowed: set[str]) -> dict:
    try:
        document = json.loads(log_path.read_text(encoding="utf-8"))
        if document.get("date") != today.isoformat():
            document = {}
    except (OSError, ValueError):
        document = {}
    paths = set(document.get("blocked_paths") or []) | set(blocked)
    locs = set(document.get("stripped_sitemap_urls") or []) | set(stripped)
    stages = document.get("stages") or {}
    stages[stage] = {"blocked_new_urls": len(blocked), "stripped_sitemap_urls": len(stripped)}
    document = {
        "date": today.isoformat(),
        "frozen": True,
        "blocked_new_urls": len(paths),
        "stripped_sitemap_url_count": len(locs),
        "blocked_paths": sorted(paths)[:BLOCKED_LIST_CAP],
        "stripped_sitemap_urls": sorted(locs)[:BLOCKED_LIST_CAP],
        "allowed_exceptions": sorted(allowed),
        "stages": stages,
    }
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
    except OSError as error:
        print(f"new-url-freeze: 計數檔寫不進 {log_path}: {error}", file=sys.stderr)
    return document


def enforce(
    pages,
    *,
    stage: str = "manual",
    today: date | None = None,
    flag_path: Path = FLAG_PATH,
    launch_list: Path = LAUNCH_LIST,
    log_path: Path | None = None,
) -> dict:
    """移除本輪才產生的新網址、剝除網站地圖新條目；既有頁不動。冪等。"""
    pages = Path(pages)
    if not is_frozen(flag_path):
        return {"frozen": False}
    # git status 給的是相對儲存庫根目錄的路徑；站台目錄不是根目錄就無法正確判定（2.7 反方 K1 必改 2）。
    try:
        toplevel = Path(_git(pages, "rev-parse", "--show-toplevel").strip()).resolve()
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"new-url-freeze[{stage}]: 站台目錄不是 git checkout，略過（{error}）")
        return {"frozen": True, "skipped": True}
    if toplevel != pages.resolve():
        print(f"new-url-freeze[{stage}]: 警告：站台目錄 {pages.resolve()} 不是儲存庫根目錄 {toplevel}，略過")
        return {"frozen": True, "skipped": True}
    today = today or today_tpe()
    try:
        new_files = untracked_url_files(pages)
        baseline = baseline_sitemap_locs(pages)
        sitemaps = tracked_sitemaps(pages)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"new-url-freeze[{stage}]: 站台目錄不是 git checkout，略過（{error}）")
        return {"frozen": True, "skipped": True}
    allowed = exception_paths(today, launch_list)
    blocked = []
    structural = []
    for relative in new_files:
        if relative in allowed:
            continue
        if _structural(relative):
            structural.append(relative)
            continue
        (pages / relative).unlink(missing_ok=True)
        blocked.append(relative)
    stripped: list[str] = []
    for relative in sitemaps:
        path = pages / relative
        if path.is_file():
            stripped += strip_new_sitemap_entries(path, baseline, allowed)
    document = _record(log_path or default_log_path(), today, stage, blocked, stripped, allowed)
    print(
        f"new-url-freeze[{stage}]: blocked_new_urls={len(blocked)} "
        f"stripped_sitemap_urls={len(stripped)} day_total={document['blocked_new_urls']} "
        f"exceptions={len(allowed)} structural_kept={len(structural)}"
    )
    return {"frozen": True, "blocked": blocked, "stripped": stripped,
            "structural_kept": structural, "document": document}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", default=os.environ.get("GEO_PAGES", str(HERE / "pages")))
    parser.add_argument("--stage", default="manual")
    args = parser.parse_args()
    enforce(args.pages, stage=args.stage)
