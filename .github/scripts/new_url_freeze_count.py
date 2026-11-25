#!/usr/bin/env python3
"""把 geo-daily 每場的「被擋新網址數」落檔進倉儲（只寫日期與數字，不寫網址）。

來源：``_engine/geo/new_url_freeze.py`` 每場寫的計數檔（``$GEO_REPORTS/new_url_freeze.json``，
在 ``.growth-runtime/`` 底下、被 .gitignore 擋、每場重開）。本檔把它濃縮成
``.github/growth/new_url_freeze_count.json``：``.github/growth/`` 不進 Pages 成品、
推它也不觸發 Pages，geo-daily 既有的 ``git add -A`` 會一起帶上。

公開庫只放數字：不寫 ``blocked_paths``、``stripped_sitemap_urls``、例外頁清單。
同一天（台北日期，以守門判定那天為準）多場：``blocked_new_urls_max`` 取當天各場最大、``blocked_new_urls_last`` 為最後一場。
計數檔不存在（停新增網址關閉、或站台目錄不是儲存庫根目錄而略過）時記 ``status: no_log``。

源頭擋下、根本沒產出的新頁不進計數檔：``aeo_answers.py`` 印 ``FROZEN <slug>: ...``、
``aeo_pages.py`` 印 ``停新增網址：略過 N 個新比較頁``；geo-daily 把兩者輸出 tee 進
``$RUNNER_TEMP/frozen_answers.log``（``--frozen-log``），這裡只數行數與 N，不留 slug。
log 不存在時 ``frozen_*`` 記 null。``blocked_total``＝``blocked_new_urls``＋``frozen_new_pages``
（K1 讀 ``days[].blocked_total_max``）。

記帳日：以場次開始（``GEO_WORKFLOW_STARTED_AT``）的台北日期為準，跨午夜的場次不拆兩天。
供外宣放量 K1 名額轉移判讀讀取（照 00_GrowthEngine reports/outreach_scale/channel_ledger.md）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

TPE = timezone(timedelta(hours=8))
HISTORY_DAYS = 60
DEFAULT_OUTPUT = Path(".github/growth/new_url_freeze_count.json")


def default_source() -> Path:
    override = os.environ.get("GEO_NEW_URL_FREEZE_LOG")
    if override:
        return Path(override)
    base = os.environ.get("GEO_REPORTS")
    if not base:
        raise SystemExit("new-url-freeze-count: GEO_REPORTS 未設，找不到計數檔")
    return Path(base) / "new_url_freeze.json"


FROZEN_ANSWER_RE = re.compile(r"^FROZEN (\S+?):")
FROZEN_ALT_RE = re.compile(r"停新增網址：略過 (\d+) 個新比較頁")


def _int(value) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def count_frozen(log_path: Path | None) -> dict:
    """數源頭擋下的新頁；log 不存在記 null。答案頁同一場會跑兩次 aeo_answers，同 slug 只算一次。"""
    empty = {"frozen_answer_pages": None, "frozen_alternative_pages": None, "frozen_new_pages": None}
    if log_path is None:
        return empty
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return empty
    answers: set[str] = set()
    alternatives = 0
    for line in lines:
        match = FROZEN_ANSWER_RE.match(line.strip())
        if match:
            answers.add(match.group(1))
            continue
        match = FROZEN_ALT_RE.search(line)
        if match:
            # aeo_pages 每場跑一次；萬一多跑取最大，不重複加總。
            alternatives = max(alternatives, int(match.group(1)))
    return {
        "frozen_answer_pages": len(answers),
        "frozen_alternative_pages": alternatives,
        "frozen_new_pages": len(answers) + alternatives,
    }


def _sum(*values) -> int | None:
    present = [v for v in values if v is not None]
    return sum(present) if present else None


def _max(previous, value):
    if value is None:
        return previous
    return value if previous is None else max(previous, value)


def summarise(source: dict | None) -> dict:
    """只取數字欄位；讀不到就記 no_log。"""
    if not source or not isinstance(source.get("date"), str):
        return {"status": "no_log", "blocked_new_urls": None}
    stages = {}
    for name, counts in sorted((source.get("stages") or {}).items()):
        if isinstance(counts, dict):
            stages[str(name)] = {
                "blocked_new_urls": _int(counts.get("blocked_new_urls")),
                "stripped_sitemap_urls": _int(counts.get("stripped_sitemap_urls")),
            }
    return {
        "status": "frozen" if source.get("frozen") else "unknown",
        "blocked_new_urls": _int(source.get("blocked_new_urls")),
        "stripped_sitemap_url_count": _int(source.get("stripped_sitemap_url_count")),
        "allowed_exception_count": len(source.get("allowed_exceptions") or []),
        "stages": stages,
        "source_date": source["date"],
    }


def merge(document: dict, today: str, run: dict, run_at: str, run_id: str | None) -> dict:
    days = {d["date"]: d for d in document.get("days") or [] if isinstance(d, dict) and "date" in d}
    day = days.get(today) or {"date": today, "runs": 0, "blocked_new_urls_max": None}
    # geo-daily 每場只呼叫一次；同一場重跑（re-run 沿用同一 GITHUB_RUN_ID）不重算場數。
    if not run_id or run_id != day.get("last_run_id"):
        day["runs"] = int(day.get("runs") or 0) + 1
    blocked = run.get("blocked_new_urls")
    day["blocked_new_urls_max"] = _max(day.get("blocked_new_urls_max"), blocked)
    day["blocked_new_urls_last"] = blocked
    frozen = run.get("frozen_new_pages")
    day["frozen_new_pages_max"] = _max(day.get("frozen_new_pages_max"), frozen)
    day["frozen_new_pages_last"] = frozen
    total = run.get("blocked_total")
    day["blocked_total_max"] = _max(day.get("blocked_total_max"), total)
    day["blocked_total_last"] = total
    day["stripped_sitemap_url_count_last"] = run.get("stripped_sitemap_url_count")
    day["status_last"] = run["status"]
    day["last_run_at"] = run_at
    if run_id:
        day["last_run_id"] = run_id
    days[today] = day
    cutoff = (datetime.fromisoformat(today) - timedelta(days=HISTORY_DAYS - 1)).date().isoformat()
    kept = [days[k] for k in sorted(days) if k >= cutoff]
    return {
        "schema": 2,
        "note": ("geo-daily 停新增網址守門每場被擋新網址數（只有數字，不含網址）；來源 "
                 "_engine/geo/new_url_freeze.py＋aeo_answers/aeo_pages 的 FROZEN 輸出；"
                 "K1 讀 days[].blocked_total_max"),
        "updated_at": run_at,
        "latest": {"date": today, "run_at": run_at, **run},
        "days": kept,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--frozen-log", type=Path, default=None,
                        help="aeo_answers／aeo_pages 輸出 tee 的 log；不存在則 frozen_* 記 null")
    parser.add_argument("--today", default=None, help="台北日期 YYYY-MM-DD；預設場次開始的台北日期")
    parser.add_argument("--started-at", default=None,
                        help="場次開始 ISO 時間；預設環境變數 GEO_WORKFLOW_STARTED_AT，再退回現在")
    parser.add_argument("--now", default=None, help="ISO 時間；測試用")
    args = parser.parse_args(argv)

    now = datetime.fromisoformat(args.now) if args.now else datetime.now(timezone.utc)
    started_text = args.started_at or os.environ.get("GEO_WORKFLOW_STARTED_AT")
    try:
        started = datetime.fromisoformat(started_text.replace("Z", "+00:00")) if started_text else now
    except ValueError:
        started = now
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    # 跨午夜的場次（台北 21:23 開跑、跑到隔天）以場次開始那天記帳。
    today = args.today or started.astimezone(TPE).date().isoformat()
    source_path = args.source or default_source()
    try:
        source = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        source = None
    try:
        existing = json.loads(args.output.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        existing = {}
    run = summarise(source)
    run.update(count_frozen(args.frozen_log))
    if run["status"] == "no_log" and run["frozen_new_pages"]:
        run["status"] = "frozen"
    run["blocked_total"] = _sum(run.get("blocked_new_urls"), run.get("frozen_new_pages"))
    # 已知限制：new_url_freeze.py 的計數檔跨台北午夜會自行歸零，跨午夜場次的
    # blocked_new_urls 只含午夜後的部分；source_date 與記帳日不同時標出來。
    run["source_date_mismatch"] = bool(run.get("source_date")) and run.get("source_date") != today
    run_at = now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    document = merge(existing, today, run, run_at, os.environ.get("GITHUB_RUN_ID"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"new-url-freeze-count: {today} status={run['status']} "
          f"blocked_new_urls={run.get('blocked_new_urls')} frozen_new_pages={run.get('frozen_new_pages')} "
          f"blocked_total={run.get('blocked_total')} -> {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
