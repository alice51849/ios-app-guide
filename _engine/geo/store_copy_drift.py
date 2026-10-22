#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""倉儲商店文案（data/<款>_full.json）對線上商店頁的每日比對，與「商店已不列的宣稱」守門。

背景（2026-10-23 一億品質監督第 1 次報告 S7）：電池健康分數（battai）10-20 改版、睡眠音效（sereno）
10-18 改版後，倉儲文案沒同步；意圖頁與社群文照倉儲寫，宣稱了商店已經不列的功能（充放電回数、
データの書き出し、ADHD、耳鳴り…）。影片規則（a）、意圖頁、社群文都拿倉儲當事實來源，倉儲一舊，
不實宣稱就會一路擴散。

做三件事：
1. ``check``（每日）：用 iTunes Lookup（公開、免金鑰；一次查多款）讀前 10 大商店的線上描述，逐款逐語系
   和倉儲比對。描述不同的款標紅（status=red），列出「倉儲有、線上沒有」的條列（dropped）與
   「線上有、倉儲沒有」的條列（added），寫 JSON 與繁中 Markdown 報告。
2. 紅燈款的「已不列宣稱詞」（blocked_terms）＝倉儲有、線上全部語系都沒有的短條列，加上
   geo/data/store_claim_terms.json 人工補的詞（同樣要線上全部語系都沒有才生效）。
3. ``claim_problems``：新內容（意圖頁、社群文、短片字幕）裡，同一句同時出現該款品牌名與已不列宣稱詞
   ＝宣稱商店已不列的功能，擋下。只看同一句有品牌名的句子，一般知識（例如「iPhone 15 起設定裡看得到
   充放電回数」）不擋。

資料怎麼回到一致：倉儲要從 App Store Connect 重新拉（只有 Mac 有金鑰）→ 本機待辦；拉完的下一輪
check 就轉綠，守門自動解除。

本檔是 00_GrowthEngine geo/ 的正本，Guide ``_engine/geo/`` 是逐 byte 鏡像（Guide 的 post_qa.py 發文閘門也用它）。

    python3 geo/store_copy_drift.py check --data data --out reports/store_copy_drift/latest.json \\
        --md reports/store_copy_drift/latest.md [--fail-on-red]
    python3 geo/store_copy_drift.py scan --report R.json FILE...      # 掃既有內容檔，列出會被擋的句子
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import time
import unicodedata
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SCHEMA = "growth.store-copy-drift/v1"
CURATED = HERE / "data" / "store_claim_terms.json"
# 監督組建議的前 10 語系（商店國 → 倉儲語系）。Lookup 只帶 country，回的是該店的主要語言。
COUNTRY_LOCALES = (("us", "en-US"), ("jp", "ja"), ("tw", "zh-Hant"), ("kr", "ko"), ("de", "de-DE"),
                   ("br", "pt-BR"), ("fr", "fr-FR"), ("es", "es-ES"), ("cn", "zh-Hans"), ("gb", "en-GB"))
LOOKUP = "https://itunes.apple.com/lookup?id={ids}&country={cc}"
BATCH = 50
MAX_TERM = 40              # 比這長的條列是整句說明，新內容幾乎不會逐字出現，不當擋詞
MAX_AUTO_TERM = 24         # 自動擋詞只收短條列（功能名），長句只列在報告裡
MIN_LATIN_TERM = 4         # 太短的拉丁字（例如 "PDF"）不當擋詞，避免誤擋
BULLET_RE = re.compile(r"^[\s•●・\-–—*·]+")
SENTENCE_RE = re.compile(r"[^。．.!?！？\n]+[。．.!?！？]?")
BRAND_SPLIT_RE = re.compile(r"\s*[:：|｜–—]\s*|\s+-\s+")
UA = "Mozilla/5.0 (growth store-copy-drift)"


# ------------------------------------------------------------------ 文字處理

def norm(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text or "")).strip()


def lines(text: str) -> list[str]:
    out = []
    for raw in (text or "").splitlines():
        line = norm(BULLET_RE.sub("", raw))
        if line:
            out.append(line)
    return out


def _latin(term: str) -> bool:
    return bool(re.fullmatch(r"[\x00-\x7f]+", term))


def usable_term(term: str) -> bool:
    if not term or len(term) > MAX_TERM:
        return False
    return not (_latin(term) and len(term) < MIN_LATIN_TERM)


def stem(term: str) -> str:
    """條列的第一個詞取前段：拉丁字取前 5 個字母、中日韓取前 2 個字；用來認出線上只是改了說法。"""
    first = re.split(r"[\s,，、:：/]+", term.strip(), maxsplit=1)[0]
    return first[:5].casefold() if _latin(first) else first[:2]


def auto_term(line: str, live_same_locale: str) -> bool:
    """倉儲有、線上沒有的短條列能不能自動當擋詞：太長不收；同語系線上文案還有同字頭（只是改寫）不收。"""
    if not usable_term(line) or len(line) > MAX_AUTO_TERM:
        return False
    head = stem(line)
    return bool(head) and head not in live_same_locale


def brands(doc: dict) -> list[str]:
    """各語系商店名冒號前的品牌（BattAI、Sereno…），長的在前。"""
    out = set()
    for entry in doc.values() if isinstance(doc, dict) else []:
        name = norm((entry or {}).get("name") if isinstance(entry, dict) else "")
        if name:
            head = BRAND_SPLIT_RE.split(name, maxsplit=1)[0].strip()
            if len(head) >= 3:
                out.add(head)
    return sorted(out, key=lambda s: (-len(s), s))


def sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE_RE.findall(norm_keep_lines(text)) if s.strip()]


def norm_keep_lines(text: str) -> str:
    return "\n".join(norm(line) for line in unicodedata.normalize("NFKC", text or "").splitlines())


# ------------------------------------------------------------------ 比對

def compare_app(key: str, repo: dict, live: dict[str, dict], curated: dict | None = None) -> dict:
    """一款的比對結果。live＝{語系: Lookup 結果}；沒查到的語系不比。"""
    locales: dict[str, dict] = {}
    live_all = "\n".join(norm(rec.get("description", "")) for rec in live.values()).casefold()
    dropped_terms: set[str] = set()
    for locale, rec in sorted(live.items()):
        repo_desc = ((repo or {}).get(locale) or {}).get("description") if isinstance(repo, dict) else None
        if not repo_desc:
            locales[locale] = {"same": None, "reason": "倉儲沒有這個語系的描述"}
            continue
        live_desc = rec.get("description", "")
        same = norm(repo_desc) == norm(live_desc)
        live_lines = set(lines(live_desc))
        repo_lines = lines(repo_desc)
        dropped = [line for line in repo_lines if line not in live_lines]
        added = [line for line in lines(live_desc) if line not in set(repo_lines)]
        locales[locale] = {"same": same, "dropped": dropped if not same else [], "added": added if not same else [],
                           "live_version": rec.get("version"),
                           "live_updated": (rec.get("currentVersionReleaseDate") or "")[:10] or None}
        if not same:
            live_low = norm(live_desc).casefold()
            for line in dropped:
                if auto_term(line, live_low) and line.casefold() not in live_all:
                    dropped_terms.add(line)
    extra = [t for t in ((curated or {}).get(key) or {}).get("terms", []) if t.casefold() not in live_all]
    compared = [v for v in locales.values() if v.get("same") is not None]
    if not compared:
        status = "unknown"
    elif all(v["same"] for v in compared):
        status = "green"
    else:
        status = "red"
    return {
        "status": status,
        "locales": locales,
        "brands": brands(repo),
        "blocked_terms": sorted(dropped_terms | set(extra), key=lambda s: (s.casefold(), s)) if status == "red" else [],
        "live_version": next((v.get("live_version") for v in locales.values() if v.get("live_version")), None),
        "live_updated": max((v.get("live_updated") or "" for v in locales.values()), default="") or None,
    }


def term_hit(term: str, low: str) -> bool:
    """拉丁字要整個詞（可帶複數 s／es），避免 "Sereno Pro" 撞到 "Sereno promění"；中日韓照子字串。"""
    folded = term.casefold()
    if _latin(term):
        return re.search(r"(?<!\w)" + re.escape(folded) + r"(?:s|es)?(?!\w)", low) is not None
    return folded in low


def claim_problems(entry: dict | None, text: str, *, label: str = "", whole: bool = False) -> list[str]:
    """紅燈款：同一句同時有品牌名與已不列宣稱詞 → 擋。綠燈、未知、沒有擋詞的款一律放行。

    whole=True（單款的社群文、字幕：整則都在講這一款）時每一句都查，不要求同句有品牌名。
    """
    if not entry or entry.get("status") != "red" or not entry.get("blocked_terms"):
        return []
    marks = [b.casefold() for b in entry.get("brands") or []]
    terms = entry["blocked_terms"]
    out = []
    for sentence in sentences(text):
        low = sentence.casefold()
        if not whole and marks and not any(m in low for m in marks):
            continue
        hits = [t for t in terms if term_hit(t, low)]
        if hits:
            out.append(f"{label}「{sentence[:90]}」宣稱商店已不列的「{'、'.join(hits[:3])}」"
                       "（倉儲文案與線上商店不一致，見 store_copy_drift 報告）")
    return out


# ------------------------------------------------------------------ 讀檔、查線上

def _read_json(path: Path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def load_curated(path: Path = CURATED) -> dict:
    doc = _read_json(path) or {}
    return {k: v for k, v in doc.items() if isinstance(v, dict)}


def report_paths() -> list[Path]:
    """報告放哪：環境變數（設了就只看它）> Guide 工作樹的 .github/growth > 00_GrowthEngine reports/。"""
    if os.environ.get("STORE_COPY_DRIFT"):
        return [Path(os.environ["STORE_COPY_DRIFT"])]
    out = []
    pages = os.environ.get("GEO_PAGES")
    if pages:
        out.append(Path(pages) / ".github" / "growth" / "store_copy_drift.json")
    out.append(ROOT.parent / ".github" / "growth" / "store_copy_drift.json")   # 在 Guide 的 _engine/geo 時
    out.append(ROOT / "reports" / "store_copy_drift" / "latest.json")        # 在 00_GrowthEngine 時
    return out


def load_report(path: Path | None = None) -> dict | None:
    for candidate in ([path] if path else report_paths()):
        doc = _read_json(candidate) if candidate else None
        if isinstance(doc, dict) and doc.get("schema") == SCHEMA:
            return doc
    return None


def page_problems(text: str, keys, report: dict | None = None, *, label: str = "") -> list[str]:
    """產生器用：這頁出現的每一款都檢查。沒有報告（還沒跑過）＝不知道，放行。"""
    report = load_report() if report is None else report
    if not report:
        return []
    out = []
    for key in dict.fromkeys(keys):
        out += claim_problems((report.get("apps") or {}).get(key), text, label=f"{label}{key} ")
    return out


APP_LINK_RE = re.compile(r"apps\.apple\.com/(?:[a-z]{2}/)?app/(?:[^/\"'?#]+/)?id(\d{6,12})")
CONTENT_ATTR_RE = re.compile(r'<meta\b[^>]*\bcontent="([^"]*)"', re.I)
DROP_BLOCK_RE = re.compile(r"<(script|style)\b.*?</\1>", re.S | re.I)


def page_text(source: str) -> str:
    """HTML → 看得到的文字＋ meta 的 content（標題、描述也是宣稱）。"""
    import html as _html

    metas = "\n".join(CONTENT_ATTR_RE.findall(source or ""))
    body = re.sub(r"<[^>]+>", "\n", DROP_BLOCK_RE.sub("", source or ""))
    return _html.unescape(body + "\n" + metas)


def html_page_problems(source: str, report: dict | None = None, *, label: str = "") -> list[str]:
    """產生器用：這頁連到的每一款（App Store 連結的 id 對名冊）都檢查已不列宣稱。"""
    report = load_report() if report is None else report
    if not report:
        return []
    by_id = {v: k for k, v in roster_ids().items()}
    keys = [by_id[i] for i in APP_LINK_RE.findall(source or "") if i in by_id]
    return page_problems(page_text(source), keys, report, label=label)


def http_json(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read())


def fetch_live(ids: dict[str, str], fetch=http_json, pause: float = 1.0) -> tuple[dict[str, dict[str, dict]], list[str]]:
    """{款: {語系: Lookup 結果}}；一個商店國一批（最多 50 款一次）。查不到的國記在 errors。"""
    by_id = {str(v): k for k, v in ids.items()}
    live: dict[str, dict[str, dict]] = {k: {} for k in ids}
    errors = []
    id_list = sorted(by_id)
    for cc, locale in COUNTRY_LOCALES:
        for start in range(0, len(id_list), BATCH):
            chunk = id_list[start:start + BATCH]
            try:
                doc = fetch(LOOKUP.format(ids=",".join(chunk), cc=cc))
            except Exception as error:  # noqa: BLE001 — 一國查不到不影響其他國
                errors.append(f"{cc}: {type(error).__name__}: {error}")
                continue
            for rec in doc.get("results") or []:
                key = by_id.get(str(rec.get("trackId")))
                if key and rec.get("description"):
                    live[key][locale] = {k: rec.get(k) for k in ("description", "version", "currentVersionReleaseDate",
                                                                 "trackName")}
            if pause:
                time.sleep(pause)
    return live, errors


def roster_ids() -> dict[str, str]:
    from live_app_manifest import canonical_manifest

    return {key: str(entry["app_id"]) for key, entry in canonical_manifest()["apps"].items()}


def build_report(data_dir: Path, ids: dict[str, str], live: dict[str, dict[str, dict]], errors: list[str],
                 now: dt.datetime, curated: dict | None = None) -> dict:
    apps = {}
    for key in sorted(ids):
        repo = _read_json(Path(data_dir) / f"{key}_full.json")
        if not isinstance(repo, dict):
            apps[key] = {"status": "unknown", "reason": f"沒有 data/{key}_full.json", "locales": {}, "brands": [],
                         "blocked_terms": []}
            continue
        apps[key] = compare_app(key, repo, live.get(key) or {}, curated)
    counts = {s: sum(1 for a in apps.values() if a["status"] == s) for s in ("red", "green", "unknown")}
    return {"schema": SCHEMA, "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "countries": [cc for cc, _ in COUNTRY_LOCALES], "counts": counts, "errors": errors, "apps": apps}


def render_md(report: dict) -> str:
    c = report["counts"]
    out = [f"# 倉儲商店文案 × 線上商店頁 每日比對（{report['generated_at']}）", "",
           f"紅燈 **{c['red']}** 款、一致 {c['green']} 款、無法比對 {c['unknown']} 款；比對的商店：{'、'.join(report['countries'])}。",
           "紅燈＝倉儲（data/<款>_full.json）與線上描述不同；紅燈款的「已不列宣稱」會在意圖頁產生器與發文閘門擋下，"
           "倉儲重新從 App Store Connect 拉齊後自動轉綠。", ""]
    if report.get("errors"):
        out += ["查詢失敗：" + "；".join(report["errors"][:5]), ""]
    red = {k: a for k, a in report["apps"].items() if a["status"] == "red"}
    if not red:
        out.append("目前沒有紅燈款。")
    for key, app in red.items():
        diff = [loc for loc, v in app["locales"].items() if v.get("same") is False]
        out += [f"## 🔴 {key}（線上 {app.get('live_version') or '?'}，{app.get('live_updated') or '?'} 更新）", "",
                f"- 不一致語系：{'、'.join(diff)}",
                f"- 擋下的已不列宣稱：{'、'.join(app['blocked_terms'][:20]) or '（無短條列；只標紅）'}"]
        sample = next((app["locales"][loc] for loc in ("en-US", *diff) if loc in app["locales"]
                       and app["locales"][loc].get("same") is False), None)
        if sample:
            out.append(f"- 倉儲有、線上沒有（例）：{'／'.join(sample['dropped'][:6])}")
            out.append(f"- 線上有、倉儲沒有（例）：{'／'.join(sample['added'][:6])}")
        out.append("")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    check = sub.add_parser("check")
    check.add_argument("--data", type=Path, default=ROOT / "data")
    check.add_argument("--out", type=Path, required=True)
    check.add_argument("--md", type=Path)
    check.add_argument("--fail-on-red", action="store_true")
    scan = sub.add_parser("scan")
    scan.add_argument("--report", type=Path)
    scan.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args(argv)
    if args.cmd == "scan":
        report = load_report(args.report)
        if not report:
            print("::warning::沒有比對報告", file=sys.stderr)
            return 0
        red = [k for k, a in report["apps"].items() if a["status"] == "red"]
        bad = 0
        for path in args.files:
            text = path.read_text(encoding="utf-8", errors="ignore")
            for problem in page_problems(text, red, report, label=f"{path}: "):
                print(problem)
                bad += 1
        return 1 if bad else 0
    ids = roster_ids()
    live, errors = fetch_live(ids)
    report = build_report(args.data, ids, live, errors, dt.datetime.now(dt.timezone.utc), load_curated())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        args.md.write_text(render_md(report), encoding="utf-8")
    for key, app in report["apps"].items():
        if app["status"] == "red":
            diff = [loc for loc, v in app["locales"].items() if v.get("same") is False]
            print(f"::error::倉儲文案與線上商店不一致：{key}（{'、'.join(diff)}）；已不列宣稱 {len(app['blocked_terms'])} 個詞擋在新內容外")
    print(json.dumps(report["counts"], ensure_ascii=False))
    return 1 if args.fail_on_red and report["counts"]["red"] else 0


if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    raise SystemExit(main())
