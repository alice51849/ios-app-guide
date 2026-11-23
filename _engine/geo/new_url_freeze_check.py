#!/usr/bin/env python3
"""停新增網址推後驗收（審核員退回 11-23 第 2 條）：不接進流程，人工或推後讀回時跑。

給站台目錄（指南站儲存庫根目錄），檢查 ``answers/index.html`` 與 ``llms*.txt``
（``llms.txt``、``llms-full.txt``、``llms/*.txt``）是否連到 git ``HEAD``（或 ``--ref``）
沒有的 ``answers/*.html``（含 ``<語系>/answers/*.html``）。有就列出並非零退出。

    python3 geo/new_url_freeze_check.py /path/to/ios-app-guide
    python3 geo/new_url_freeze_check.py /path/to/ios-app-guide --ref origin/main
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("site", help="指南站儲存庫根目錄")
    parser.add_argument("--ref", default="HEAD", help="比對基準（預設 HEAD）")
    args = parser.parse_args(argv)
    site = Path(args.site)
    if not scanned_files(site):
        print(f"new-url-freeze-check: {site} 找不到 answers/index.html 或 llms*.txt（稀疏 checkout？）",
              file=sys.stderr)
        return 2
    try:
        problems = check(site, args.ref)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"new-url-freeze-check: 無法讀取 {site} 的 git {args.ref}: {error}", file=sys.stderr)
        return 2
    if not problems:
        print(f"new-url-freeze-check: OK（answers/index.html 與 llms*.txt 無 {args.ref} 沒有的答案頁連結）")
        return 0
    total = sum(len(v) for v in problems.values())
    print(f"new-url-freeze-check: FAIL {total} 個連結指向 {args.ref} 沒有的答案頁")
    for name, links in problems.items():
        for link in links[:20]:
            print(f"  {name}: {link}")
        if len(links) > 20:
            print(f"  {name}: …另 {len(links) - 20} 個")
    return 1


if __name__ == "__main__":
    sys.exit(main())
