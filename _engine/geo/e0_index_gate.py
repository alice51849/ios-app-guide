#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""E0 索引入口 Gate(fail-closed)、唯讀 GSC 觀測與既有 canary 選取。

為什麼存在:
  實測(2026-09-12)顯示 Guide 的深層頁在 Search Console 上全部是
  ``URL is unknown to Google``、``lastCrawlTime = null``。在沒有進索引的頁面上
  做 schema(E1)或 image alt(E2)實驗,index/click 階段不可能有任何可觀測變化。
  所以 E1/E2 必須被一道 Gate 擋住,直到索引入口真的打開。

Gate 通過條件(兩個都要成立,缺一不可):
  1. 至少 1 個**代表性深層頁**的 URL Inspection 回報 verdict=PASS 且正向 indexed coverage。
  2. 提交過的 sitemap ``isPending == False`` 且 ``lastDownloaded`` 非空。

誠實規則(寫死在程式裡):
  • **fail-closed**:任何一項拿不到資料(API 失敗、憑證缺、欄位缺)一律視為
    未通過,回 ``UNKNOWN`` 而不是 ``PASS``。
  • **未知不補 0**:拿不到的數值記成 ``None`` 並標 ``unknown``,絕不寫成 0
    再拿去算平均或宣稱「沒有成效」。
  • 只允許 sitemap list 與 URL inspection。後者的 API transport 是 POST，
    但操作語意仍是唯讀；不提交 sitemap、不改 property、不送 IndexNow。
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Sequence

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import site_config  # noqa: E402

INDEXED_MARKER = "indexed"
# 「Crawled - currently not indexed」「Discovered - currently not indexed」都含有
# 子字串 "indexed",天真的 substring 比對會把**沒有被索引**誤判成已索引。
# 這裡列出否定標記,並要求 verdict 必須是 PASS,雙重把關。
NOT_INDEXED_MARKERS = (
    "not indexed",
    "unknown to google",
    "excluded",
    "blocked",
    "not found",
    "redirect",
    "alternative page",
    "duplicate",
)
INDEXED_VERDICT = "PASS"
GATE_PASS = "PASS"
GATE_BLOCKED = "BLOCKED"
GATE_UNKNOWN = "UNKNOWN"

# 只允許這些唯讀 Search Console 操作;submit / verify 一律拒絕。
READ_ONLY_OPS = frozenset({"sitemaps.list", "urlInspection.inspect"})
FORBIDDEN_OPS = frozenset({"sitemaps.submit", "sitemaps.delete", "sites.add", "sites.delete"})

# 退避:分鐘。GET-only,永遠不會因為等待而去「推」任何東西。
BACKOFF_MINUTES = (60, 120, 240, 480, 960, 1440)


class MutationAttempted(RuntimeError):
    """有人想從 Gate/watcher 發出會改變遠端狀態的呼叫。"""


def assert_read_only(op: str) -> str:
    if op in FORBIDDEN_OPS or op not in READ_ONLY_OPS:
        raise MutationAttempted(f"E0 Gate 只允許唯讀操作,拒絕:{op}")
    return op


@dataclass
class DeepPageStatus:
    path: str
    coverage_state: str | None
    last_crawl_time: str | None
    verdict: str | None
    known: bool

    @property
    def indexed(self) -> bool:
        """只有 verdict=PASS 且 coverageState 不含任何否定標記才算已索引。

        Google 的 'Crawled - currently not indexed' 含子字串 'indexed',
        單純 substring 比對會產生假陽性 —— 那正是這個 Gate 最不能犯的錯。
        """
        path = PurePosixPath(self.path)
        if (not self.known or not self.coverage_state or path.is_absolute()
                or ".." in path.parts or len(path.parts) < 2 or self.path.endswith("/")):
            return False
        state = self.coverage_state.lower()
        if any(marker in state for marker in NOT_INDEXED_MARKERS):
            return False
        if self.verdict != INDEXED_VERDICT:
            return False
        return bool(re.search(r"\bindexed\b", state))


@dataclass
class SitemapStatus:
    path: str | None
    is_pending: bool | None
    last_downloaded: str | None
    known: bool

    @property
    def processed(self) -> bool:
        return self.known and self.is_pending is False and isinstance(self.last_downloaded, str) and bool(self.last_downloaded.strip())


@dataclass
class GateResult:
    status: str
    property_url: str
    deep_pages: list[DeepPageStatus] = field(default_factory=list)
    sitemap: SitemapStatus | None = None
    reasons: list[str] = field(default_factory=list)
    unknown_fields: list[str] = field(default_factory=list)

    @property
    def allows_e1_e2(self) -> bool:
        return self.status == GATE_PASS

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "allows_e1_e2": self.allows_e1_e2,
            "property_url": self.property_url,
            "indexed_deep_pages": sum(1 for p in self.deep_pages if p.indexed)
            if all(p.known and p.coverage_state and p.verdict for p in self.deep_pages) else None,
            "confirmed_indexed_deep_pages": sum(1 for p in self.deep_pages if p.indexed),
            "deep_pages_checked": len(self.deep_pages),
            "deep_pages": [vars(p) for p in self.deep_pages],
            "sitemap": vars(self.sitemap) if self.sitemap else None,
            "reasons": self.reasons,
            "unknown_fields": self.unknown_fields,
            "honesty": "未知一律記 null 並列入 unknown_fields,絕不補 0;任何未知都讓 Gate fail-closed。",
        }


def evaluate_gate(property_url: str, deep_pages: Sequence[DeepPageStatus],
                  sitemap: SitemapStatus | None) -> GateResult:
    result = GateResult(status=GATE_UNKNOWN, property_url=property_url,
                        deep_pages=list(deep_pages), sitemap=sitemap)

    if not deep_pages:
        result.unknown_fields.append("deep_pages")
        result.reasons.append("沒有取得任何深層頁狀態 → fail-closed")
        return result
    for page in deep_pages:
        if not page.known or not page.coverage_state or not page.verdict:
            result.unknown_fields.append(f"deep_page:{page.path}")
    if sitemap is None or not sitemap.known:
        result.unknown_fields.append("sitemap")
        result.reasons.append("沒有取得 sitemap 狀態 → fail-closed")
        return result
    if not isinstance(sitemap.is_pending, bool):
        result.unknown_fields.append("sitemap.isPending")
    if sitemap.is_pending is False and not sitemap.last_downloaded:
        result.unknown_fields.append("sitemap.lastDownloaded")
    if result.unknown_fields:
        result.reasons.append("必要的觀測欄位缺失 → UNKNOWN，不把未取得的狀態補成零")
        return result

    indexed = [p for p in deep_pages if p.indexed]
    if not indexed:
        result.status = GATE_BLOCKED
        result.reasons.append(
            f"0/{len(deep_pages)} 個代表性深層頁被索引(全部為 "
            f"{deep_pages[0].coverage_state!r} 之類狀態)→ E1/E2 不得起算")
    if not sitemap.processed:
        result.status = GATE_BLOCKED
        result.reasons.append(
            f"sitemap 尚未被處理(isPending={sitemap.is_pending}, "
            f"lastDownloaded={sitemap.last_downloaded!r})→ E1/E2 不得起算")

    if indexed and sitemap.processed:
        if result.unknown_fields:
            result.status = GATE_UNKNOWN
            result.reasons.append("條件看似成立,但仍有未知欄位 → 保守 fail-closed")
        else:
            result.status = GATE_PASS
            result.reasons.append(
                f"{len(indexed)}/{len(deep_pages)} 深層頁已索引且 sitemap 已處理 → 允許 E1/E2 起算")
    return result


def collect_gate(query: Callable[[str, dict], Any], property_url: str,
                 deep_paths: Sequence[str], sitemap_url: str | None = None) -> GateResult:
    """query(op, params) 由呼叫端注入;只會被要求唯讀操作。"""
    pages: list[DeepPageStatus] = []
    property_url = property_url.rstrip("/") + "/"
    expected_sitemap = sitemap_url or property_url + "sitemap_index.xml"
    for path in deep_paths:
        relative = PurePosixPath(path)
        if relative.is_absolute() or ".." in relative.parts or len(relative.parts) < 2 or path.endswith("/"):
            pages.append(DeepPageStatus(path=path, coverage_state=None, last_crawl_time=None, verdict=None, known=False))
            continue
        try:
            raw = query(assert_read_only("urlInspection.inspect"),
                        {"siteUrl": property_url, "inspectionUrl": property_url + path})
            status = raw.get("inspectionResult", {}).get("indexStatusResult", {})
            pages.append(DeepPageStatus(path=path,
                                        coverage_state=status.get("coverageState"),
                                        last_crawl_time=status.get("lastCrawlTime"),
                                        verdict=status.get("verdict"),
                                        known=bool(status.get("coverageState") and status.get("verdict"))))
        except MutationAttempted:
            raise
        except Exception:  # noqa: BLE001 - 取不到就是未知,不補值
            pages.append(DeepPageStatus(path=path, coverage_state=None, last_crawl_time=None,
                                        verdict=None, known=False))
    try:
        entries = query(assert_read_only("sitemaps.list"), {"siteUrl": property_url}).get("sitemap", [])
        matches = [entry for entry in entries if entry.get("path") == expected_sitemap]
        if len(matches) == 1:
            first = matches[0]
            sitemap = SitemapStatus(path=first.get("path"), is_pending=first.get("isPending"),
                                    last_downloaded=first.get("lastDownloaded"),
                                    known=isinstance(first.get("isPending"), bool))
        else:
            sitemap = SitemapStatus(path=None, is_pending=None, last_downloaded=None, known=False)
    except MutationAttempted:
        raise
    except Exception:  # noqa: BLE001
        sitemap = SitemapStatus(path=None, is_pending=None, last_downloaded=None, known=False)
    return evaluate_gate(property_url, pages, sitemap)


def next_backoff_minutes(attempt: int) -> int:
    """唯讀 watcher 的退避間隔，不會因等待而推送任何東西。"""
    if attempt < 0:
        raise ValueError("attempt 不可為負")
    return BACKOFF_MINUTES[min(attempt, len(BACKOFF_MINUTES) - 1)]


# ------------------------------------------------------------ canary 選取

_TEXT_RE = re.compile(r"<[^>]+>")
_FAQ_RE = re.compile(r'"@type"\s*:\s*"(FAQPage|HowTo)"')


def information_score(html: str) -> dict:
    """只用頁面既有內容評分,不新增任何頁面。"""
    body = re.sub(r"<(script|style).*?</\1>", " ", html, flags=re.S | re.I)
    text = _TEXT_RE.sub(" ", body)
    words = len(text.split())
    return {
        "word_count": words,
        "structured_blocks": len(_FAQ_RE.findall(html)),
        "internal_links": len(re.findall(r'href="(?!https?://)[^"#][^"]*"', html)),
        "score": words + 200 * len(_FAQ_RE.findall(html)),
    }


def select_canaries(pages_root: Path, candidates: Sequence[str], count: int = 8) -> list[dict]:
    """從**已存在**的深層頁挑資訊量最高的 6–12 個;不建立新頁、不改內容。"""
    if not 6 <= count <= 12:
        raise ValueError("canary 數量必須在 6–12 之間")
    scored: list[dict] = []
    for rel in candidates:
        path = pages_root / rel
        if not path.is_file():
            continue
        metrics = information_score(path.read_text(encoding="utf-8", errors="ignore"))
        scored.append({"path": rel, **metrics})
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:count]


def discovery_proposal(canaries: Sequence[dict], hub_path: str = "index.html") -> dict:
    """只提議在首頁/hub 增加指向既有深層頁的內鏈,不新增任何頁面。"""
    return {
        "kind": "internal_discovery_only",
        "hub": hub_path,
        "add_links_to": [c["path"] for c in canaries],
        "forbidden": [
            "新增 doorway 或薄頁",
            "提交 sitemap 或送 IndexNow",
            "改動深層頁本身的內容",
            "任何部署或 workflow 觸發",
        ],
        "rationale": "深層頁全部 'URL is unknown to Google';Google 官方建議以站內連結讓內容可被發現。"
                     "先只動 hub 的內鏈,是最小且可逆的索引入口實驗。",
        "reversible": "移除新增的內鏈即可完全還原,不影響任何既有頁面。",
    }


def main(argv: Sequence[str] | None = None) -> int:  # pragma: no cover
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--property", default=f"{site_config.PUBLIC_SITE}/")
    parser.add_argument("--credentials", default=str(Path.home() / ".growth-private" / "gsc_oauth.json"))
    parser.add_argument("--deep-path", action="append", default=None)
    parser.add_argument("--sitemap")
    parser.add_argument("--out", default=None)
    parser.add_argument("--evidence-dir", type=Path)
    args = parser.parse_args(argv)

    deep_paths = args.deep_path or [
        "answers/" + slug + ".html"
        for slug in json.loads((HERE / "index_entry_canary_manifest.json").read_text())["canaries"]
    ]
    audit = []
    if args.evidence_dir:
        args.evidence_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    creds = Path(args.credentials).expanduser()
    if not creds.exists():
        result = GateResult(status=GATE_UNKNOWN, property_url=args.property,
                            reasons=["找不到 Search Console 憑證 → fail-closed"],
                            unknown_fields=["credentials"])
    else:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        import google_auth_httplib2
        import httplib2

        info = json.loads(creds.read_text(encoding="utf-8"))
        credentials = Credentials(token=info.get("token"), refresh_token=info.get("refresh_token"),
                                  token_uri=info["token_uri"], client_id=info["client_id"],
                                  client_secret=info["client_secret"], scopes=info.get("scopes"))
        if not credentials.valid:
            request = Request()
            def refresh_request(*values, **kwargs):
                kwargs.setdefault("timeout", 30)
                return request(*values, **kwargs)
            credentials.refresh(refresh_request)
        transport = google_auth_httplib2.AuthorizedHttp(credentials, http=httplib2.Http(timeout=30))
        service = build("searchconsole", "v1", http=transport, cache_discovery=False)

        def query(op: str, params: dict):
            assert_read_only(op)
            record = {"operation": op, "semantic_read_only": True,
                      "method": "GET" if op == "sitemaps.list" else "POST",
                      "observed_at": datetime.now(timezone.utc).isoformat(), "params": params}
            try:
                if op == "sitemaps.list":
                    response = service.sitemaps().list(siteUrl=params["siteUrl"]).execute(num_retries=0)
                else:
                    response = service.urlInspection().index().inspect(body={
                        "inspectionUrl": params["inspectionUrl"], "siteUrl": params["siteUrl"],
                        "languageCode": "en-US"}).execute(num_retries=0)
                raw = json.dumps(response, ensure_ascii=False, sort_keys=True).encode()
                record.update(status=200, response_sha256=hashlib.sha256(raw).hexdigest())
                if args.evidence_dir:
                    path = args.evidence_dir / f"{len(audit) + 1:02d}-{op.replace('.', '-')}.json"
                    path.write_bytes(raw)
                    path.chmod(0o600)
                    record["body"] = path.name
                return response
            except Exception as error:
                record.update(status=getattr(getattr(error, "resp", None), "status", None),
                              error=type(error).__name__)
                raise
            finally:
                audit.append(record)

        result = collect_gate(query, args.property, deep_paths, args.sitemap)

    payload = result.to_dict()
    payload.update(observed_at=datetime.now(timezone.utc).isoformat(), operations=audit,
                   mutations=0, sitemap_submissions=0, indexnow=0, indexed_effect_not_proven=True)
    print(json.dumps(payload, ensure_ascii=False, indent=2)[:2200])
    if args.out:
        path = Path(args.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        path.chmod(0o600)
    return 0 if result.allows_e1_e2 else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
