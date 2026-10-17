#!/usr/bin/env python3
"""各 App 支援站（https://open.cait518.cc/<app>-support/）的頁面送 IndexNow。

為什麼要這支：本 repo 的 IndexNow 只送 /ios-app-guide/ 底下，因為 keyLocation 放在
/ios-app-guide/；IndexNow 規格寫明「key 檔的位置決定這把 key 能送哪些網址」
（https://www.indexnow.org/documentation，Option 2），所以支援站從來沒有送過。
同一把 key 也放在網域根目錄（https://open.cait518.cc/<key>.txt），依規格可涵蓋整個 host，
這裡就用根目錄那份 key 送支援站的說明頁、各語言意圖頁（bm-sitemap.xml）。
實驗紀錄：00_GrowthEngine reports/growth_experiments.md EXP-03。

每一步都 fail-closed：
1. 讀線上根目錄 robots.txt 的 Sitemap 行，只取 ``<site>/<dir>-support/sitemap.xml``；另外用
   ``--extra-site`` 補上根目錄 robots 漏列、但站上確實有 sitemap 的支援站。每站同時讀同目錄的
   ``bm-sitemap.xml``（意圖頁）。已放棄的 App 一律略過。
2. 只收該站目錄底下、副檔名 .html 或以 / 結尾的網址，去重排序。
3. 逐一 GET：HTTP 200、沒有轉到別的網址、沒有 noindex、canonical（若有）指回自己，才送。
4. 用可見文字的 sha256 跟上次 state 比，只送新的或內容有變的網址（``--all`` 全送）。
5. 每個 endpoint 都要 200／202，否則 exit 1；收據寫網址數、網址集合 digest、各 endpoint 狀態。
   IndexNow 收下通知不等於已收錄；成效看各頁 ct 碼帶來的 App Store 下載。
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import html
import json
from pathlib import Path
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
GEO = ROOT / "_engine" / "geo"
if str(GEO) not in sys.path:
    sys.path.insert(0, str(GEO))

import indexnow_submit as indexnow  # noqa: E402

DEFAULT_SITE = "https://open.cait518.cc"
STATE_VERSION = 1
STATE_KIND = "indexnow_support_sites"
RECEIPT_SCHEMA = "lumi.indexnow-support-sites/v1"
USER_AGENT = "LumiSupportIndexNow/1.0 (+https://open.cait518.cc/)"
MAX_URLS = 10_000
TIMEOUT = 30
# 業主已放棄的 App：即使站還在也絕不送。
ABANDONED_MARKERS = ("lensafe",)
SUPPORT_DIR_RE = re.compile(r"[a-z0-9][a-z0-9-]*-support")
_LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)
_CANONICAL_RE = re.compile(
    r"""<link\b[^>]*\brel\s*=\s*["']canonical["'][^>]*\bhref\s*=\s*["']([^"']+)["']""", re.I)
_CANONICAL_REV_RE = re.compile(
    r"""<link\b[^>]*\bhref\s*=\s*["']([^"']+)["'][^>]*\brel\s*=\s*["']canonical["']""", re.I)
_NOINDEX_RE = re.compile(
    r"""<meta\b[^>]*\bname\s*=\s*["'](?:robots|googlebot|bingbot)["'][^>]*\bcontent\s*=\s*["'][^"']*noindex""", re.I)
_DROP_RE = re.compile(r"(?is)<(script|style|template|noscript)\b[^>]*>.*?</\1\s*>")
_TAG_RE = re.compile(r"(?s)<[^>]+>")
_WS_RE = re.compile(r"\s+")


class SupportIndexNowError(RuntimeError):
    """Raised when the run cannot prove what it would submit."""


def fetch(url: str, *, opener=None) -> tuple[int, str, str]:
    """(HTTP 狀態, 最終網址, 內容)。網路錯誤回 (0, url, "")。"""
    opener = urllib.request.urlopen if opener is None else opener
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with opener(request, timeout=TIMEOUT) as response:
            body = response.read(4_000_000).decode("utf-8", "replace")
            return response.status, response.geturl(), body
    except urllib.error.HTTPError as error:
        return error.code, url, ""
    except (urllib.error.URLError, TimeoutError, OSError):
        return 0, url, ""


def support_dirs_from_robots(robots: str, site: str) -> list[str]:
    """根目錄 robots.txt 列出的 ``<site>/<dir>-support/sitemap.xml`` → dir 清單。"""
    prefix = site.rstrip("/") + "/"
    dirs = []
    for line in robots.splitlines():
        field, _, value = line.partition(":")
        if field.strip().lower() != "sitemap":
            continue
        url = value.strip()
        if not url.startswith(prefix) or not url.endswith("/sitemap.xml"):
            continue
        name = url[len(prefix):-len("/sitemap.xml")]
        if SUPPORT_DIR_RE.fullmatch(name) and name not in dirs:
            dirs.append(name)
    return dirs


def sitemap_locs(text: str) -> list[str]:
    return [html.unescape(x) for x in _LOC_RE.findall(text or "")]


def in_scope(url: str, site: str, support_dir: str) -> bool:
    prefix = f"{site.rstrip('/')}/{support_dir}/"
    parts = urllib.parse.urlsplit(url)
    if parts.query or parts.fragment or not url.startswith(prefix):
        return False
    path = parts.path
    return path.endswith(".html") or path.endswith("/")


def abandoned(support_dir: str) -> bool:
    return any(marker in support_dir for marker in ABANDONED_MARKERS)


SITEMAP_SETS = {"all": ("sitemap.xml", "bm-sitemap.xml"), "bm": ("bm-sitemap.xml",)}


def candidate_urls(site: str, support_dirs: list[str], fetcher=fetch,
                   sitemaps: tuple[str, ...] = SITEMAP_SETS["all"]) -> tuple[list[str], dict]:
    """各站 sitemap.xml＋bm-sitemap.xml 裡、該站範圍內的網址；第二個值是每站的讀取紀錄。

    ``sitemaps=("bm-sitemap.xml",)`` 只讀意圖頁；沒有 bm-sitemap 的站在這個模式下直接略過。"""
    urls: list[str] = []
    seen = set()
    report = {}
    for support_dir in support_dirs:
        if abandoned(support_dir):
            report[support_dir] = {"skipped": "abandoned"}
            continue
        row = {}
        for name in sitemaps:
            status, final, body = fetcher(f"{site.rstrip('/')}/{support_dir}/{name}")
            row[name] = status
            if status != 200:
                continue
            locs = sitemap_locs(body)
            if "<sitemapindex" in body:
                # 子 sitemap 也要在同一站底下才讀。
                nested = []
                for child in locs:
                    if child.startswith(f"{site.rstrip('/')}/{support_dir}/") and child.endswith(".xml"):
                        child_status, _, child_body = fetcher(child)
                        if child_status == 200:
                            nested += sitemap_locs(child_body)
                locs = nested
            for url in locs:
                if in_scope(url, site, support_dir) and url not in seen:
                    seen.add(url)
                    urls.append(url)
        if not any(code == 200 for code in row.values()):
            if "sitemap.xml" in sitemaps:
                raise SupportIndexNowError(f"{support_dir}: no readable sitemap ({row})")
            row["skipped"] = "no_bm_sitemap"
        report[support_dir] = row
    return sorted(urls), report


def canonical_of(body: str) -> str | None:
    match = _CANONICAL_RE.search(body) or _CANONICAL_REV_RE.search(body)
    return html.unescape(match.group(1)).strip() if match else None


def visible_digest(body: str) -> str:
    text = _TAG_RE.sub(" ", _DROP_RE.sub(" ", body))
    text = _WS_RE.sub(" ", html.unescape(text)).strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def check_live(url: str, fetcher=fetch) -> tuple[bool, str, str]:
    """(可送?, 原因, 可見文字 digest)。"""
    status, final, body = fetcher(url)
    if status != 200:
        return False, f"http_{status}", ""
    if final.rstrip("/") != url.rstrip("/"):
        return False, "redirected", ""
    if _NOINDEX_RE.search(body):
        return False, "noindex", ""
    canonical = canonical_of(body)
    if canonical and canonical != url:
        return False, "canonical_elsewhere", ""
    return True, "ok", visible_digest(body)


def read_state(path: Path | None) -> dict[str, str]:
    if not path or not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != STATE_VERSION or payload.get("kind") != STATE_KIND:
        return {}
    digests = payload.get("digests")
    return {str(k): str(v) for k, v in digests.items()} if isinstance(digests, dict) else {}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def run(args, *, fetcher=fetch, sender=indexnow.submit_endpoint, now=None) -> dict:
    site = args.site.rstrip("/")
    key = indexnow.read_key(Path(args.key_file))
    key_location = indexnow.key_location_for(site, key, args.key_location)
    status, _, robots = fetcher(f"{site}/robots.txt")
    if status != 200 or "Sitemap:" not in robots:
        raise SupportIndexNowError(f"root robots.txt unreadable (HTTP {status})")
    support_dirs = support_dirs_from_robots(robots, site)
    for extra in args.extra_site or []:
        if not SUPPORT_DIR_RE.fullmatch(extra):
            raise SupportIndexNowError(f"--extra-site must look like <app>-support: {extra!r}")
        if extra not in support_dirs:
            support_dirs.append(extra)
    if not support_dirs:
        raise SupportIndexNowError("root robots.txt lists no support-site sitemaps")
    urls, site_report = candidate_urls(site, support_dirs, fetcher, SITEMAP_SETS[getattr(args, "sitemaps", "all")])
    if not urls:
        raise SupportIndexNowError("support sitemaps contain no in-scope URLs")
    if len(urls) > MAX_URLS:
        raise SupportIndexNowError(f"{len(urls)} URLs exceeds the {MAX_URLS} cap")

    live: dict[str, str] = {}
    skipped: dict[str, int] = {}
    with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for url, (ok, reason, digest) in zip(urls, pool.map(lambda u: check_live(u, fetcher), urls)):
            if ok:
                live[url] = digest
            else:
                skipped[reason] = skipped.get(reason, 0) + 1
    if not live:
        raise SupportIndexNowError("no support URL passed the live check")

    state_path = Path(args.state_file) if args.state_file else None
    previous = {} if args.all else read_state(state_path)
    selected = sorted(u for u, d in live.items() if previous.get(u) != d)
    now = now or dt.datetime.now(dt.timezone.utc)
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "site": site,
        "key_location": key_location,
        "support_sites": len(support_dirs),
        "sitemaps": getattr(args, "sitemaps", "all"),
        "sitemap_reads": site_report,
        "candidates": len(urls),
        "live": len(live),
        "skipped": skipped,
        "selected": len(selected),
        "url_set_sha256": indexnow.url_set_digest(selected) if selected else "",
        "endpoints": {},
        "dry_run": bool(args.dry_run),
        "note": "accepted means the notification was received, not that any URL is indexed",
    }
    if selected and not args.dry_run:
        def record(endpoint, batch, count, code):
            receipt["endpoints"].setdefault(endpoint, []).append({"batch": batch, "urls": count, "status": code})

        indexnow.submit_all(selected, key, site, batch_size=10_000, sender=sender,
                            acceptance_recorder=record, key_location=key_location)
        for endpoint in indexnow.ENDPOINTS:
            codes = [row["status"] for row in receipt["endpoints"].get(endpoint, [])]
            if not codes or any(code not in indexnow.ACCEPTED_STATUSES for code in codes):
                raise SupportIndexNowError(f"{endpoint} did not accept every batch: {codes}")
    if state_path and not args.dry_run:
        merged = {} if args.all else dict(previous)
        merged.update(live)
        write_json(state_path, {"version": STATE_VERSION, "kind": STATE_KIND,
                                "updated_at": receipt["generated_at"], "digests": merged})
    if args.receipt_file:
        write_json(Path(args.receipt_file), receipt)
    return receipt


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--site", default=DEFAULT_SITE)
    ap.add_argument("--key-file", required=True)
    ap.add_argument("--key-location", default=None,
                    help="key 檔網址；預設 <site>/<key>.txt（網域根目錄，涵蓋整個 host）")
    ap.add_argument("--extra-site", action="append", default=[],
                    help="根目錄 robots.txt 漏列、但站上有 sitemap 的支援站目錄（可重複）")
    ap.add_argument("--state-file")
    ap.add_argument("--receipt-file")
    ap.add_argument("--all", action="store_true", help="忽略 state，全部送")
    ap.add_argument("--sitemaps", choices=sorted(SITEMAP_SETS), default="all",
                    help="all＝sitemap.xml＋bm-sitemap.xml；bm＝只送意圖頁（bm-sitemap.xml）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        receipt = run(args)
    except (SupportIndexNowError, indexnow.SubmissionError, ValueError) as error:
        print(f"::error::support IndexNow: {error}")
        return 1
    print(json.dumps({k: receipt[k] for k in ("support_sites", "candidates", "live", "skipped", "selected",
                                              "dry_run")}, ensure_ascii=False))
    for endpoint, rows in receipt["endpoints"].items():
        print(f"  {endpoint}: {[row['status'] for row in rows]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
