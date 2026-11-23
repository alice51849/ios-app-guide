#!/usr/bin/env python3
"""停新增網址推後驗收（審核員退回 11-23 第 2 條；改 true 前擴全站）：不接進流程，人工或推後讀回時跑。

給站台目錄（指南站儲存庫根目錄，git checkout），做兩項檢查，任一有問題退出碼 1：

1. 答案頁（原檢查）：``answers/index.html`` 與 ``llms*.txt`` 是否連到 git ``HEAD``（或 ``--ref``）
   沒有的 ``answers/*.html``（含 ``<語系>/answers/*.html``）。
2. 全站死連結：本輪改動或新增的 ``.html``／``.xml``／``.txt``／``.json``
   （``git diff --name-only <ref>`` 加未追蹤檔；``--all`` 改掃全站）裡指向同站的連結
   （相對路徑、``/ios-app-guide/`` 開頭、站台公開網址開頭；來源為 href、src、sitemap ``<loc>``、
   markdown 連結，json 只取站台公開網址字串），去 ``#``／``?`` 後、目錄補 ``index.html``，
   目標既不在工作樹也不在 ``<ref>`` → 死連結。外站、mailto 等、``_engine/`` 與點開頭路徑不計。

輸出一行 JSON 摘要（每檔前 ``--max-per-file`` 條）。

    python3 geo/new_url_freeze_check.py /path/to/ios-app-guide
    python3 geo/new_url_freeze_check.py /path/to/ios-app-guide --ref origin/main
    python3 geo/new_url_freeze_check.py /path/to/ios-app-guide --all

推後驗收（K1 開 true 後）固定用 ``--all``，或 ``--ref <推前 commit>``：推後工作樹等於 HEAD，
增量模式掃 0 檔、必定通過，不可當驗收（2.7 反方 11-23 必改 2）。
稀疏 checkout（core.sparseCheckout）或答案頁檔缺漏時退出碼 2、不判通過（必改 1）。
"""
from __future__ import annotations

import argparse
import json
import os
import posixpath
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

# 「答案頁連結」：可帶語系前綴（en-GB/answers/x.html），前面可有任何網址前綴。
ANSWER_LINK_RE = re.compile(
    r"(?:(?<=/)|(?<![A-Za-z0-9_.\-]))"
    r"(?:(?P<locale>[a-z]{2}(?:-(?:[A-Z]{2}|[A-Z][a-z]{3}))?)/)?"
    r"answers/(?P<slug>[A-Za-z0-9_\-]+)\.html"
)


def tracked_files(site: Path, ref: str) -> set[str]:
    raw = subprocess.run(
        ["git", "ls-tree", "-r", "-z", "--name-only", ref],
        cwd=site, capture_output=True, text=True, check=True,
    ).stdout
    return {p for p in raw.split("\0") if p}


def scanned_files(site: Path) -> list[Path]:
    files = [site / "answers" / "index.html", site / "llms.txt", site / "llms-full.txt"]
    files += sorted((site / "llms").glob("*.txt")) if (site / "llms").is_dir() else []
    files += sorted(p for p in site.glob("llms*.txt") if p not in files)
    return [p for p in files if p.is_file()]


def answer_links(text: str) -> set[str]:
    out = set()
    for match in ANSWER_LINK_RE.finditer(text):
        if match.group("slug") == "index":
            continue
        locale = match.group("locale")
        rel = f"answers/{match.group('slug')}.html"
        out.add(f"{locale}/{rel}" if locale else rel)
    return out


def check(site: Path, ref: str = "HEAD") -> dict[str, list[str]]:
    tracked = tracked_files(site, ref)
    problems: dict[str, list[str]] = {}
    for path in scanned_files(site):
        missing = sorted(
            link for link in answer_links(path.read_text(encoding="utf-8", errors="replace"))
            if link not in tracked
        )
        if missing:
            problems[path.relative_to(site).as_posix()] = missing
    return problems



# ---- 全站死連結（改 true 前擴充）----
SITE_URL = "https://open.cait518.cc/ios-app-guide/"
SITE_PATH_PREFIX = "/ios-app-guide/"
SCAN_SUFFIXES = (".html", ".xml", ".txt", ".json")
HREF_RE = re.compile(r"""\b(?:href|src)\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.I)
LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)
MD_LINK_RE = re.compile(r"\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
SKIP_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:")


def _excluded(rel: str) -> bool:
    return rel.startswith("_engine/") or any(part.startswith(".") for part in rel.split("/"))


def _site_url_re(site_url: str) -> re.Pattern:
    return re.compile(re.escape(site_url) + r"""[^\s"'<>)\]\\]*""")


def raw_links(rel: str, text: str, site_url: str = SITE_URL) -> list[str]:
    """依副檔名取出候選連結字串（未正規化）。"""
    suffix = posixpath.splitext(rel)[1].lower()
    if suffix == ".html":
        return [a or b for a, b in HREF_RE.findall(text)] + _site_url_re(site_url).findall(text)
    if suffix == ".xml":
        return LOC_RE.findall(text) + [a or b for a, b in HREF_RE.findall(text)]
    if suffix == ".txt":
        return MD_LINK_RE.findall(text)
    if suffix == ".json":
        return _site_url_re(site_url).findall(text)
    return []


def resolve_link(source_rel: str, link: str, site_url: str = SITE_URL) -> str | None:
    """同站連結 → 站台根相對路徑（未決定 index／.html 變體）；外站或不計者回 None。"""
    link = link.strip().replace("&amp;", "&")
    if not link or link.startswith("#") or "{{" in link or "${" in link or "{%" in link:
        return None
    link = link.split("#", 1)[0].split("?", 1)[0]
    site_root = site_url.split("://", 1)[-1]
    if link.startswith(site_url) or link.startswith("http://" + site_root) or link.startswith("//" + site_root):
        path = link.split(site_root, 1)[1]
    elif link.rstrip("/") + "/" == site_url or link.rstrip("/") == "//" + site_root.rstrip("/"):
        path = ""
    elif link.startswith("//") or SKIP_SCHEME_RE.match(link):
        return None  # 外站、mailto、tel、javascript、data、CDN
    elif link.startswith(SITE_PATH_PREFIX):
        path = link[len(SITE_PATH_PREFIX):]
    elif link.startswith("/"):
        return None  # 同網域但不在站台底下
    else:
        base = posixpath.dirname(source_rel)
        joined = posixpath.normpath(posixpath.join(base, link)) if link not in ("", ".") else base
        if joined == ".":
            joined = ""
        elif link.endswith("/") and not joined.endswith("/"):
            joined += "/"
        if joined.startswith("../") or joined == "..":
            return None
        path = joined
    path = unquote(path)
    if path.startswith("/") or "/../" in "/" + path + "/":
        return None
    if path == "" or path.endswith("/"):
        path += "index.html"
    if _excluded(path):
        return None
    return path


def _target_exists(path: str, existing: set[str]) -> bool:
    if path in existing:
        return True
    if not posixpath.splitext(path)[1]:  # 無副檔名：GitHub Pages 也接 x.html 與 x/index.html
        return f"{path}.html" in existing or f"{path}/index.html" in existing
    return False


def worktree_files(site: Path) -> set[str]:
    out: set[str] = set()
    root = str(site)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        rel_dir = os.path.relpath(dirpath, root)
        prefix = "" if rel_dir == "." else rel_dir.replace(os.sep, "/") + "/"
        out.update(prefix + name for name in filenames)
    return out


def _git_lines(site: Path, *args: str) -> list[str]:
    raw = subprocess.run(["git", *args], cwd=site, capture_output=True, text=True, check=True).stdout
    return [p for p in raw.split("\0") if p]


def changed_files(site: Path, ref: str = "HEAD") -> list[str]:
    names = set(_git_lines(site, "diff", "--name-only", "-z", ref, "--"))
    names |= set(_git_lines(site, "ls-files", "-z", "--others", "--exclude-standard"))
    return sorted(n for n in names if n.lower().endswith(SCAN_SUFFIXES) and not _excluded(n))


def dead_links(site: Path, ref: str = "HEAD", scan_all: bool = False,
               site_url: str = SITE_URL) -> tuple[dict[str, list[str]], dict[str, int]]:
    """回傳（{來源檔: [死連結目標…]}, 統計）。"""
    worktree = worktree_files(site)
    existing = worktree | tracked_files(site, ref)
    if scan_all:
        sources = sorted(n for n in worktree if n.lower().endswith(SCAN_SUFFIXES) and not _excluded(n))
    else:
        sources = changed_files(site, ref)
    problems: dict[str, list[str]] = {}
    stats = {"scanned_files": 0, "links_checked": 0}
    for rel in sources:
        path = site / rel
        if not path.is_file():
            continue  # 本輪刪掉的檔
        stats["scanned_files"] += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        missing = set()
        for link in raw_links(rel, text, site_url):
            target = resolve_link(rel, link, site_url)
            if target is None:
                continue
            stats["links_checked"] += 1
            if not _target_exists(target, existing):
                missing.add(target)
        if missing:
            problems[rel] = sorted(missing)
    return problems, stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("site", help="指南站儲存庫根目錄")
    parser.add_argument("--ref", default="HEAD", help="比對基準（預設 HEAD）")
    parser.add_argument("--all", action="store_true", help="全站死連結（預設只掃本輪改動與新增檔）")
    parser.add_argument("--max-per-file", type=int, default=20, help="摘要每檔列出幾條（預設 20）")
    parser.add_argument("--site-url", default=SITE_URL, help=f"站台公開網址（預設 {SITE_URL}）")
    args = parser.parse_args(argv)
    site = Path(args.site)
    limit = max(args.max_per_file, 0)
    summary: dict = {"mode": "all" if args.all else "incremental", "ref": args.ref}
    try:
        sparse = subprocess.run(["git", "-C", str(site), "config", "--bool", "core.sparseCheckout"],
                                capture_output=True, text=True).stdout.strip() == "true"
        if sparse:
            print(f"new-url-freeze-check: {site} 是稀疏 checkout，工作樹不完整，不判定（退出 2）", file=sys.stderr)
            return 2
        if scanned_files(site):
            answer_problems = check(site, args.ref)
            summary["answers_llms"] = {
                "dead_total": sum(len(v) for v in answer_problems.values()),
                "files": {k: v[:limit] for k, v in answer_problems.items()},
            }
        else:
            answer_problems = {}
            summary["answers_llms"] = {"skipped": "找不到 answers/index.html 或 llms*.txt"}
            print(json.dumps(summary, ensure_ascii=False, indent=1))
            print(f"new-url-freeze-check: {site} 缺答案頁索引或 llms 檔，不判定（退出 2）", file=sys.stderr)
            return 2
        dead, stats = dead_links(site, args.ref, args.all, args.site_url)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"new-url-freeze-check: 無法讀取 {site} 的 git {args.ref}: {error}", file=sys.stderr)
        return 2
    summary["site_links"] = {
        **stats,
        "dead_total": sum(len(v) for v in dead.values()),
        "files_with_dead": len(dead),
        "files": {k: v[:limit] for k, v in dead.items()},
    }
    failed = bool(answer_problems or dead)
    summary["ok"] = not failed
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
