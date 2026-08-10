#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""站內連結深度稽核 — 從首頁 BFS,量出每頁距離首頁幾次點擊。

為什麼要這支:sitemap 收錄 ≠ 可被爬到。只存在於 sitemap、從首頁點不到的
「孤兒頁」會被搜尋引擎大幅降權。2026-08-08 首次量測發現 5.6 萬頁裡絕大多數
都是孤兒,這是「一個月只帶 18 次下載」的結構性主因。

    python geo/audit_link_depth.py                 # 全站稽核
    python geo/audit_link_depth.py --tag before    # 存成基準線快照
    python geo/audit_link_depth.py --compare before

輸出:
    geo/reports/link_depth.json   # 機器可讀(每個區塊的深度分佈與孤兒清單)
    geo/reports/link_depth.md     # 人看的摘要
"""
import argparse
import collections
import html
import json
import os
import re
import sys
from urllib.parse import unquote, urljoin, urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.environ.get("GEO_PAGES", os.path.join(HERE, "pages"))
REPORTS = os.path.join(HERE, "reports")
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
ROOT_URL = f"{SITE}/index.html"

# 只跟 <a href>。head 裡的 canonical/hreflang/stylesheet 不是導航連結,
# 爬蟲的連結圖與 PageRank 傳遞看的是 anchor。
ANCHOR_RE = re.compile(
    r"<a\b[^>]*?\bhref\s*=\s*(\"([^\"]*)\"|'([^']*)'|([^\s\"'>]+))",
    re.IGNORECASE,
)
NOINDEX_RE = re.compile(
    r"<meta[^>]+name\s*=\s*[\"']robots[\"'][^>]*content\s*=\s*[\"'][^\"']*"
    r"noindex",
    re.IGNORECASE,
)
SKIP_DIRS = {".git", "_engine", "node_modules", "assets"}
MAX_SAMPLE = 40


def iter_html_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(".html"):
                yield os.path.join(dirpath, name)


def rel_url(path):
    """檔案路徑 → 正規化站內 URL(一律含 index.html,不留尾斜線)。"""
    rel = os.path.relpath(path, PAGES).replace(os.sep, "/")
    return f"{SITE}/{rel}"


def normalize(url):
    """站內 URL 正規化;非站內或非 html 回 None。"""
    split = urlsplit(url)
    if split.scheme and split.scheme not in ("http", "https"):
        return None
    base = f"{split.scheme}://{split.netloc}" if split.netloc else ""
    if base and not url.startswith(SITE):
        return None
    path = unquote(split.path)
    if not path.startswith("/"):
        return None
    prefix = urlsplit(SITE).path
    if prefix and not path.startswith(prefix + "/") and path != prefix:
        return None
    if path.endswith("/"):
        path += "index.html"
    if not path.endswith(".html"):
        return None
    return f"{urlsplit(SITE).scheme}://{urlsplit(SITE).netloc}{path}"


def extract_links(text, page_url):
    out = set()
    for match in ANCHOR_RE.finditer(text):
        raw = match.group(2) or match.group(3) or match.group(4) or ""
        raw = html.unescape(raw.strip())
        if not raw or raw.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        target = normalize(urljoin(page_url, raw))
        if target:
            out.add(target)
    return out


def section_of(url):
    """把 URL 歸類到一個區塊,例如 answers / <locale>:answers / apps。"""
    rel = url[len(SITE) + 1:]
    parts = rel.split("/")
    if len(parts) == 1:
        return "root"
    if len(parts) == 2:
        head = parts[0]
        # 語系首層的 App 頁(ja/aim990.html)
        return f"{head}:app-or-page"
    return f"{parts[0]}:{parts[1]}"


def top_section(url):
    rel = url[len(SITE) + 1:]
    parts = rel.split("/")
    return "root" if len(parts) == 1 else parts[0]


def crawl():
    all_files = sorted(iter_html_files(PAGES))
    url_to_path = {rel_url(p): p for p in all_files}
    known = set(url_to_path)

    depth = {}
    noindex = set()
    broken = collections.Counter()
    broken_samples = collections.defaultdict(set)

    if ROOT_URL not in known:
        raise SystemExit(f"找不到首頁:{ROOT_URL}")

    depth[ROOT_URL] = 0
    queue = collections.deque([ROOT_URL])
    read_bytes = 0
    while queue:
        url = queue.popleft()
        d = depth[url]
        try:
            with open(url_to_path[url], "r", encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
        except OSError:
            continue
        read_bytes += len(text)
        if NOINDEX_RE.search(text):
            noindex.add(url)
        for target in extract_links(text, url):
            if target not in known:
                broken[top_section(url)] += 1
                if len(broken_samples[top_section(url)]) < 5:
                    broken_samples[top_section(url)].add(target)
                continue
            if target not in depth:
                depth[target] = d + 1
                queue.append(target)

    return {
        "all_files": all_files,
        "url_to_path": url_to_path,
        "depth": depth,
        "noindex": noindex,
        "broken": broken,
        "broken_samples": broken_samples,
        "read_mb": round(read_bytes / 1048576, 1),
    }


def summarize(result):
    depth = result["depth"]
    known = set(result["url_to_path"])
    unreachable = known - set(depth)

    # 孤兒頁要分兩種:真的該修的(可索引),與刻意 noindex 停損的微語言叢集。
    # 混在一起看會把「已經處理過的決策」誤判成待辦。
    orphan_noindex = 0
    for url in unreachable:
        try:
            with open(
                result["url_to_path"][url], "r", encoding="utf-8", errors="ignore"
            ) as fh:
                head = fh.read(4096)
        except OSError:
            continue
        if NOINDEX_RE.search(head):
            orphan_noindex += 1
    orphan_indexable = len(unreachable) - orphan_noindex

    dist = collections.Counter(depth.values())
    by_section = collections.defaultdict(
        lambda: {"total": 0, "reachable": 0, "unreachable": 0, "depths": collections.Counter()}
    )
    for url in known:
        sec = by_section[section_of(url)]
        sec["total"] += 1
        if url in depth:
            sec["reachable"] += 1
            sec["depths"][depth[url]] += 1
        else:
            sec["unreachable"] += 1

    top = collections.defaultdict(
        lambda: {"total": 0, "reachable": 0, "unreachable": 0, "depth_sum": 0}
    )
    for url in known:
        t = top[top_section(url)]
        t["total"] += 1
        if url in depth:
            t["reachable"] += 1
            t["depth_sum"] += depth[url]
        else:
            t["unreachable"] += 1

    fully_orphan = sorted(
        (
            name
            for name, s in by_section.items()
            if s["total"] >= 20 and s["reachable"] == 0
        )
    )
    deep = sorted(
        (
            name
            for name, s in by_section.items()
            if s["reachable"]
            and min(s["depths"]) > 3
        )
    )

    reachable_depths = list(depth.values())
    avg = (
        round(sum(reachable_depths) / len(reachable_depths), 3)
        if reachable_depths
        else 0
    )
    within3 = sum(v for k, v in dist.items() if k <= 3)

    return {
        "site": SITE,
        "total_pages": len(known),
        "reachable": len(depth),
        "unreachable": len(unreachable),
        "unreachable_indexable": orphan_indexable,
        "unreachable_noindex_by_design": orphan_noindex,
        "reachable_pct": round(100 * len(depth) / max(1, len(known)), 2),
        "within_3_clicks": within3,
        "within_3_clicks_pct": round(100 * within3 / max(1, len(known)), 2),
        "avg_depth_reachable": avg,
        "max_depth": max(reachable_depths) if reachable_depths else 0,
        "depth_distribution": {str(k): dist[k] for k in sorted(dist)},
        "noindex_reachable": len(result["noindex"]),
        "broken_links_by_section": dict(result["broken"]),
        "broken_samples": {
            k: sorted(v) for k, v in result["broken_samples"].items()
        },
        "top_level": {
            k: {
                "total": v["total"],
                "reachable": v["reachable"],
                "unreachable": v["unreachable"],
                "avg_depth": (
                    round(v["depth_sum"] / v["reachable"], 2)
                    if v["reachable"]
                    else None
                ),
            }
            for k, v in sorted(top.items(), key=lambda kv: -kv[1]["total"])
        },
        "fully_orphaned_sections": fully_orphan,
        "fully_orphaned_section_count": len(fully_orphan),
        "sections_min_depth_over_3": deep[:200],
        "unreachable_samples": sorted(unreachable)[:MAX_SAMPLE],
        "read_mb": result["read_mb"],
    }


def write_markdown(summary, path):
    lines = [
        "# 站內連結深度稽核",
        "",
        f"站台:{summary['site']}",
        "",
        "| 指標 | 值 |",
        "|---|---:|",
        f"| HTML 總頁數 | {summary['total_pages']:,} |",
        f"| 從首頁可達 | {summary['reachable']:,} ({summary['reachable_pct']}%) |",
        f"| **不可達(孤兒頁)** | **{summary['unreachable']:,}** |",
        f"| └ 其中可索引(真的要修) | {summary['unreachable_indexable']:,} |",
        f"| └ 其中刻意 noindex(微語言停損) | "
        f"{summary['unreachable_noindex_by_design']:,} |",
        f"| 3 次點擊內可達 | {summary['within_3_clicks']:,} "
        f"({summary['within_3_clicks_pct']}%) |",
        f"| 可達頁平均深度 | {summary['avg_depth_reachable']} |",
        f"| 最大深度 | {summary['max_depth']} |",
        f"| 整批孤立的區塊數(≥20 頁且 0 可達) | "
        f"{summary['fully_orphaned_section_count']} |",
        "",
        "## 深度分佈",
        "",
        "| 深度(點擊數) | 頁數 |",
        "|---:|---:|",
    ]
    for k, v in summary["depth_distribution"].items():
        lines.append(f"| {k} | {v:,} |")
    lines += [
        "",
        "## 各頂層區塊",
        "",
        "| 區塊 | 總頁 | 可達 | 不可達 | 平均深度 |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, v in list(summary["top_level"].items())[:40]:
        lines.append(
            f"| {name} | {v['total']:,} | {v['reachable']:,} | "
            f"{v['unreachable']:,} | {v['avg_depth'] if v['avg_depth'] is not None else '—'} |"
        )
    if summary["fully_orphaned_sections"]:
        lines += [
            "",
            "## 整批孤立的區塊(前 60)",
            "",
            "```",
            "\n".join(summary["fully_orphaned_sections"][:60]),
            "```",
        ]
    if summary["unreachable_samples"]:
        lines += [
            "",
            "## 孤兒頁樣本",
            "",
            "```",
            "\n".join(summary["unreachable_samples"][:20]),
            "```",
        ]
    if summary["broken_links_by_section"]:
        lines += [
            "",
            "## 站內死鏈(連到不存在的檔案)",
            "",
            "| 來源區塊 | 次數 |",
            "|---|---:|",
        ]
        for k, v in sorted(
            summary["broken_links_by_section"].items(), key=lambda kv: -kv[1]
        )[:20]:
            lines.append(f"| {k} | {v:,} |")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", help="另存一份快照 link_depth_<tag>.json")
    ap.add_argument("--compare", help="與 link_depth_<tag>.json 對比")
    args = ap.parse_args()

    os.makedirs(REPORTS, exist_ok=True)
    summary = summarize(crawl())

    with open(os.path.join(REPORTS, "link_depth.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    write_markdown(summary, os.path.join(REPORTS, "link_depth.md"))

    if args.tag:
        snap = os.path.join(REPORTS, f"link_depth_{args.tag}.json")
        with open(snap, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, ensure_ascii=False, indent=2)

    print(
        f"總頁 {summary['total_pages']:,} / 可達 {summary['reachable']:,} "
        f"({summary['reachable_pct']}%) / 孤兒 {summary['unreachable']:,} / "
        f"3 click 內 {summary['within_3_clicks_pct']}% / "
        f"平均深度 {summary['avg_depth_reachable']} / 最大 {summary['max_depth']}"
    )
    print(
        f"孤兒頁拆解:可索引 {summary['unreachable_indexable']:,} / "
        f"刻意 noindex {summary['unreachable_noindex_by_design']:,}"
    )
    print("深度分佈:" + ", ".join(
        f"{k}:{v:,}" for k, v in summary["depth_distribution"].items()
    ))

    if args.compare:
        snap = os.path.join(REPORTS, f"link_depth_{args.compare}.json")
        if not os.path.exists(snap):
            print(f"(找不到快照 {snap})")
            return
        with open(snap, encoding="utf-8") as fh:
            old = json.load(fh)
        print(
            f"\n對比 {args.compare}:"
            f"\n  不可達 {old['unreachable']:,} → {summary['unreachable']:,}"
            f" ({summary['unreachable'] - old['unreachable']:+,})"
            f"\n  其中可索引 {old.get('unreachable_indexable', '?')} → "
            f"{summary['unreachable_indexable']:,}"
            f"\n  3 click 內 {old['within_3_clicks']:,} → "
            f"{summary['within_3_clicks']:,}"
            f" ({summary['within_3_clicks'] - old['within_3_clicks']:+,})"
            f"\n  平均深度 {old['avg_depth_reachable']} → "
            f"{summary['avg_depth_reachable']}"
        )


if __name__ == "__main__":
    sys.exit(main())
