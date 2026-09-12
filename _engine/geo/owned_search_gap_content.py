#!/usr/bin/env python3
"""Enrich only explicitly pinned existing owned pages. No network or publishing."""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
from html.parser import HTMLParser
import io
import json
import os
from pathlib import Path
import re
import subprocess
import unicodedata
from urllib.parse import parse_qs, urlsplit, urlunsplit
from uuid import uuid4

import segno


SCHEMA = "lumi.owned-search-gap-enrichment/v1"
CLASSES = {"OWNED_CONTENT_MATCH", "ASC_ONLY_NOT_ACTIONABLE", "NO_PRODUCT_FIT"}
APPS = {"aim990": "6784974530", "cyca": "6782251621", "lumibopomofo": "6773017109", "mochi": "6785004775"}
MARKETS = {"ja": "jp", "de-DE": "de", "zh-Hant": "tw", "en-US": "us"}
MARKER = "<!-- owned-search-gap:v1:start -->"
END_MARKER = "<!-- owned-search-gap:v1:end -->"
FORBIDDEN = re.compile(
    r"(?:(?:US\$|NT\$|\$|€|¥)\s*\d|(?:USD|EUR|TWD|JPY)\s*\d|"
    r"(?<!\w)[1-5](?:\.\d)?\s*(?:stars?|星)|#\s*1\b|top[- ]ranked|"
    r"guaranteed\s+(?:score|ranking|results)|順位を保証|必ず高得点|"
    r"保證(?:分數|排名|療效)|garantierte\s+(?:Ergebnisse|Punktzahl))", re.I
)


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def normalized(text):
    return " ".join(unicodedata.normalize("NFKC", html.unescape(text)).casefold().split())


def decode(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON fields are not evidence")
            result[key] = value
        return result
    value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Non-JSON constant")))
    if not isinstance(value, dict):
        raise ValueError("A JSON object is required")
    return value


def pinned(path: Path, expected: str):
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("An explicit SHA-256 is required")
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError("Evidence must be a bounded regular file")
    raw = path.read_bytes()
    if sha(raw) != expected:
        raise ValueError("Evidence digest changed")
    return raw


def git(repo, *args):
    result = subprocess.run(
        ["git", "--no-optional-locks", "--no-pager", "-C", str(repo), *args],
        capture_output=True, timeout=45,
        env={**os.environ, "GIT_OPTIONAL_LOCKS": "0", "GIT_NO_LAZY_FETCH": "1", "GIT_TERMINAL_PROMPT": "0"},
    )
    if result.returncode:
        raise ValueError("Required committed page/source is unavailable")
    return result.stdout


def safe_path(value):
    if (not isinstance(value, str) or not value or "\\" in value
            or Path(value).is_absolute() or ".." in Path(value).parts):
        raise ValueError("Page paths must stay inside the existing Guide owner")
    return value


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.words, self.links, self.canonicals, self.scripts = [], [], [], []
        self.language = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"style", "script"}:
            self.skip += 1
        if tag == "html":
            self.language = attrs.get("lang")
        if tag == "a":
            self.links.append(attrs.get("href", ""))
        if tag == "link" and attrs.get("rel") == "canonical":
            self.canonicals.append(attrs.get("href"))

    def handle_endtag(self, tag):
        if tag in {"style", "script"}:
            self.skip = max(0, self.skip - 1)

    def handle_data(self, text):
        if not self.skip and text.strip():
            self.words.append(text.strip())

    @property
    def visible(self):
        return "\n".join(self.words)


def strings(page):
    return [page["heading"], page["disclosure"], *page["paragraphs"],
            *[value for item in page["faqs"] for value in (item["q"], item["a"])], page["limitations"]]


def shingle(text, locale):
    normalized_text = normalized(text)
    tokens = list(re.sub(r"\s+", "", normalized_text)) if locale in {"ja", "zh-Hant"} else re.findall(r"\w+", normalized_text)
    width = 7 if locale in {"ja", "zh-Hant"} else 5
    return {tuple(tokens[i:i + width]) for i in range(max(0, len(tokens) - width + 1))}


def validate_copy(page, queries):
    text = "\n".join(strings(page))
    if FORBIDDEN.search(text):
        raise ValueError("Fixed prices, ratings, rank or outcome guarantees are forbidden")
    if re.search(r"https?://|<[^>]*>|javascript:", text, re.I):
        raise ValueError("Copy must be text only; do not introduce URLs or markup")
    if page["app_id"] != APPS.get(page["app_key"]) or MARKETS.get(page["locale"]) != page["country"]:
        raise ValueError("Product, language or storefront mismatch")
    if not 3 <= len(page["paragraphs"]) <= 4 or not 3 <= len(page["faqs"]) <= 4:
        raise ValueError("Each selected page needs substantive scenarios and distinct FAQs")
    if len(set(page["information_gain"])) < 3:
        raise ValueError("Information gain must name three different practical decisions")
    if len({normalized(value) for value in strings(page)}) != len(strings(page)):
        raise ValueError("Repeated copy is not information gain")
    if page["locale"] == "ja":
        if len(re.findall(r"[\u3040-\u30ff]", text)) < 100:
            raise ValueError("Japanese paragraphs must be native script, not English placeholders")
    elif page["locale"] == "zh-Hant":
        if len(re.findall(r"[\u4e00-\u9fff]", text)) < 250 or re.search(r"[\u3040-\u30ff]", text):
            raise ValueError("Traditional Chinese content must use the correct native script")
    elif page["locale"] == "de-DE":
        if len(re.findall(r"[äöüßÄÖÜ]", text)) < 5 or re.search(r"[\u3040-\u9fff]", text):
            raise ValueError("German paragraphs must be native prose")
    elif re.search(r"[\u3040-\u9fff]", text) or len(text.split()) < 200:
        raise ValueError("English paragraphs must be substantive native prose")
    if "Lumi Studio" not in page["disclosure"]:
        raise ValueError("First-party publisher disclosure is required")
    terms = []
    for identity in page["query_ids"]:
        query = queries[identity]
        if query["app_id"] != page["app_id"] or query["country"].lower() != page["country"]:
            raise ValueError("An enrichment cannot target another App/storefront's query")
        term = normalized(query["term"])
        count = normalized(text).count(term)
        if count > 2:
            raise ValueError("Query repetition is keyword stuffing, not a natural answer")
        terms.append({"query_id": identity, "exact_phrase_occurrences": count})
    if page["app_key"] == "aim990":
        if "ETS" not in text or not any(token in text for token in ("original", "独自")):
            raise ValueError("Aim990 needs original-practice and ETS limitations")
        if re.search(r"auto(?:matic|matically).{0,30}diagnos|自動.{0,12}診断", text, re.I):
            if "という意味ではありません" not in text:
                raise ValueError("Do not invent automatic diagnostic behaviour")
    if page["app_key"] == "cyca" and not all(token in text for token in ("Schätzung", "Verhütung", "keine Diagnose")):
        raise ValueError("Cycle content must distinguish estimates, contraception and diagnosis")
    if page["app_key"] == "mochi" and not all(token in text for token in ("Basic checklists", "Home Screen check-offs are free", "optional", "Premium")):
        raise ValueError("Do not recast free check-offs as a paid-only feature")
    if page["app_key"] == "lumibopomofo" and not all(token in text for token in ("台灣", "漢語拼音", "家長閘門", "免費")):
        raise ValueError("Zhuyin, free access and parental decision boundaries must remain explicit")
    return terms


def validate_plan(plan, snapshot, corpus, source_repo):
    if plan.get("schema") != SCHEMA:
        raise ValueError("Unsupported owned-content contract")
    if not re.fullmatch(r"[0-9a-f]{40}", plan["guide_base"]):
        raise ValueError("The Guide baseline must be a full immutable commit")
    if snapshot.get("metric") != "PUBLIC_ITUNES_SEARCH_SAMPLE_ONLY":
        raise ValueError("An App Store download or rank-repair claim is not an owned-content signal")
    gaps = {item["evidence_query_id"] for item in snapshot["recommendations"]}
    queries = {item["id"]: item for item in snapshot["queries"]}
    records = plan["classifications"]
    if len(records) != 19 or {item["query_id"] for item in records} != gaps:
        raise ValueError("All and only the 19 observed gaps must be classified once")
    selected = []
    for item in records:
        query = queries[item["query_id"]]
        if (item["classification"] not in CLASSES or not isinstance(item["selected"], bool)
                or query["group"] != "NON_BRAND" or query["visibility"] != "ABSENT_IN_SAMPLE"
                or not query["high_intent"] or not query["fresh"]):
            raise ValueError("Classification must come from a genuine non-brand sample gap")
        if item["selected"]:
            if item["classification"] != "OWNED_CONTENT_MATCH" or not item.get("page"):
                raise ValueError("Only product-matching owned content may modify a page")
            selected.append(item["query_id"])
        elif "page" in item:
            raise ValueError("Unselected gaps receive briefs only")
    if not 4 <= len(selected) <= 8:
        raise ValueError("Only four to eight highest-fit gaps may be selected")
    mapped = [identity for page in plan["pages"] for identity in page["query_ids"]]
    if len(mapped) != len(set(mapped)) or set(selected) != set(mapped):
        raise ValueError("Selected gaps and page changes differ")
    paths = [safe_path(page["path"]) for page in plan["pages"]]
    if len(paths) != len(set(paths)) or any(not path.endswith(".html") for path in paths):
        raise ValueError("Each existing URL gets only one enrichment")
    for item in records:
        if item["selected"]:
            if not any(item["page"] == page["path"] and item["query_id"] in page["query_ids"] for page in plan["pages"]):
                raise ValueError("Selected gap points outside its exact reviewed page")
    source = plan["product_source"]
    if not re.fullmatch(r"[0-9a-f]{40}", source["commit"]):
        raise ValueError("Product evidence must use a full immutable commit")
    raw = git(source_repo, "show", f"{source['commit']}:{safe_path(source['path'])}")
    if sha(raw) != source["sha256"]:
        raise ValueError("Committed product evidence changed")
    facts = decode(raw)["apps"]
    if any(facts[page["app_key"]]["app_id"] != page["app_id"] for page in plan["pages"]):
        raise ValueError("Product facts do not bind the intended App ID")
    assertions = {
        "aim990": ("Practise offline with original TOEIC-style exercises.", "Original practice, not official"),
        "cyca": ("Forecasts are estimates, not contraception.", "without creating an account"),
        "lumibopomofo": ("Try the sound and tracing activities for ㄅ.", "not Latin-letter Hanyu Pinyin"),
        "mochi": ("Checklists and Home Screen check-offs are free.", "Premium skins are optional"),
    }
    for key, phrases in assertions.items():
        proof = json.dumps(facts[key]["localized"]["en-US"], ensure_ascii=False)
        if any(phrase not in proof for phrase in phrases):
            raise ValueError("A material feature/limitation claim is not supported by its committed proof")
    if corpus["guide_commit"] != plan["guide_base"]:
        raise ValueError("Dedupe corpus must be bound to the same Guide generation")
    corpus_paths = {item["path"] for item in corpus["pages"]}
    if not set(paths) <= corpus_paths:
        raise ValueError("Every modified page must be in the reviewed existing corpus")
    return queries


def block(page, queries, corpus):
    phrase_counts = validate_copy(page, queries)
    relevant = []
    for entry in corpus["pages"]:
        parts = entry["path"].split("/")
        locale = parts[0] if parts[0] in MARKETS else "en-US"
        if locale == page["locale"]:
            relevant.append(entry["visible_text"])
    existing = "\n".join(relevant)
    old = set().union(*(shingle(text, page["locale"]) for text in relevant))
    paragraphs = [*page["paragraphs"], *[faq["a"] for faq in page["faqs"]]]
    if any(normalized(value) in normalized(existing) for value in paragraphs):
        raise ValueError("An existing answer is being duplicated instead of enriched")
    units = set().union(*(shingle(text, page["locale"]) for text in paragraphs))
    novelty = len(units - old) / max(1, len(units))
    if novelty < 0.35:
        raise ValueError("Too little new textual information relative to the existing locale corpus")
    escaped = html.escape
    out = [
        MARKER, '<section class="card" data-owned-gap-enrichment="v1">',
        "<h2>" + escaped(page["heading"]) + "</h2>",
        '<p class="small muted">' + escaped(page["disclosure"]) + "</p>",
        *["<p>" + escaped(value) + "</p>" for value in page["paragraphs"]],
    ]
    for item in page["faqs"]:
        out.extend(["<h3>" + escaped(item["q"]) + "</h3>", "<p>" + escaped(item["a"]) + "</p>"])
    out.extend(['<p class="small">' + escaped(page["limitations"]) + "</p>", "</section>", END_MARKER])
    return "\n".join(out) + "\n", {
        "locale_corpus_pages": len(relevant), "new_shingle_count": len(units - old),
        "shingle_novelty_fraction": round(novelty, 5), "query_density": phrase_counts,
        "reviewed_information_gain": page["information_gain"],
        "metric_limit": "Textual novelty plus reviewed practical decisions, not a prediction of search traffic.",
    }


def localize_ctas(source, app_id, country):
    changes = []
    def anchor(match):
        tag = match.group()
        attr = re.search(r'\bhref=(["\'])(.*?)\1', tag, re.S | re.I)
        if not attr:
            return tag
        url = html.unescape(attr.group(2))
        parsed = urlsplit(url)
        if parsed.hostname != "apps.apple.com":
            return tag
        if not re.search(rf"/id{app_id}(?:[/?#]|$)", url):
            return tag
        query = parse_qs(parsed.query)
        if query.get("pt") != ["118326163"] or query.get("ct") != ["geo_ask"] or query.get("mt") != ["8"]:
            raise ValueError("Existing attribution is unexpected; do not overwrite it")
        final = urlunsplit(("https", "apps.apple.com", f"/{country}/app/id{app_id}", parsed.query, parsed.fragment))
        changes.append((url, final))
        return tag[:attr.start(2)] + html.escape(final, quote=True) + tag[attr.end(2):]
    output = re.sub(r"<a\b[^>]*>", anchor, source, flags=re.I)
    if not changes or len({final for _, final in changes}) != 1:
        raise ValueError("One unambiguous attributed App Store destination is required")
    return output, changes, changes[0][1]


def inline_qr(source, destination, app_id):
    code = segno.make(destination, error="m", micro=False)
    buffer = io.BytesIO()
    code.save(buffer, kind="svg", border=4, scale=1, xmldecl=False, svgns=True,
              omitsize=True, nl=True, svgid=f"owned-gap-qr-{app_id}",
              title="App Store", desc=destination)
    value = "data:image/svg+xml;base64," + base64.b64encode(buffer.getvalue()).decode()
    count = 0
    def image(match):
        nonlocal count
        tag = match.group()
        if "app-store-qr-card__image" not in tag:
            return tag
        attr = re.search(r'\bsrc=(["\'])(.*?)\1', tag, re.S | re.I)
        if not attr:
            raise ValueError("Existing QR image has no source")
        count += 1
        return tag[:attr.start(2)] + value + tag[attr.end(2):]
    output = re.sub(r"<img\b[^>]*>", image, source, flags=re.I)
    if count != 1:
        raise ValueError("Expected exactly one existing QR; no new asset or QR route is created")
    return output


def render(source: bytes, page: dict, queries: dict, corpus: dict):
    if sha(source) != page["base_sha256"]:
        raise ValueError("Page baseline changed; rebase and repeat the content review")
    text = source.decode("utf-8")
    before = Page(text)
    if len(before.canonicals) != 1 or not before.canonicals[0].endswith("/" + page["path"]):
        raise ValueError("An existing exact canonical URL is required")
    if MARKER in text or text.count("</main>") != 1:
        raise ValueError("Do not duplicate enrichment or guess the existing page structure")
    insertion = None
    for heading in re.finditer(r"<h2\b[^>]*>(.*?)</h2>", text, re.S | re.I):
        if normalized(re.sub("<[^>]+>", "", heading.group(1))) == normalized(page["before_heading"]):
            start = text.rfind("<section", 0, heading.start())
            if start < 0 or "</section>" in text[start:heading.start()]:
                raise ValueError("FAQ heading has no exact enclosing section")
            if insertion is not None:
                raise ValueError("Ambiguous FAQ insertion point")
            insertion = start
    if insertion is None:
        raise ValueError("The reviewed existing FAQ section is missing")
    content, metrics = block(page, queries, corpus)
    output = text[:insertion] + content + text[insertion:]
    output, ctas, destination = localize_ctas(output, page["app_id"], page["country"])
    output = inline_qr(output, destination, page["app_id"])
    after = Page(output)
    head = lambda value: re.search(r"<head\b[^>]*>[\s\S]*?</head>", value, re.I).group()
    if head(text) != head(output) or before.canonicals != after.canonicals:
        raise ValueError("Page metadata/canonical must remain byte-identical")
    if before.language != after.language:
        raise ValueError("Page locale changed")
    expected = [next((new for old, new in ctas if url == old), url) for url in before.links]
    if expected != after.links:
        raise ValueError("No new links/URLs or unrelated CTA changes are allowed")
    return output.encode(), {**metrics, "path": page["path"], "before_sha256": sha(source),
                              "after_sha256": sha(output.encode()), "canonical_unchanged": before.canonicals[0],
                              "head_byte_identical": True, "cta_count": len(ctas),
                              "storefront": page["country"], "attribution": parse_qs(urlsplit(destination).query),
                              "qr_payload": destination, "qr_is_inline_no_new_asset_url": True}


def atomic(path, raw):
    staged = path.with_name(path.name + ".owned-gap-stage-" + uuid4().hex)
    fd = os.open(staged, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(staged, path.stat().st_mode & 0o777)
        os.replace(staged, path)
    finally:
        staged.unlink(missing_ok=True)


def apply_changes(changes):
    completed = []
    try:
        for path, original, updated in changes:
            if path.read_bytes() != original:
                raise ValueError("Another writer changed the page; refuse to overwrite WIP")
            if original != updated:
                atomic(path, updated)
                completed.append((path, original, updated))
    except BaseException:
        for path, original, updated in reversed(completed):
            if path.read_bytes() == updated:
                atomic(path, original)
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--source-repo", type=Path, required=True)
    parser.add_argument("--pages", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    if (args.report.suffix != ".json"
            or not args.report.resolve().is_relative_to((Path.home() / ".copilot/session-state").resolve())):
        raise ValueError("Reports belong only in explicit Session artifacts, not App/metadata trees")
    plan = decode(pinned(args.plan, args.plan_sha256))
    snapshot = decode(pinned(args.snapshot, plan["search_snapshot_sha256"]))
    corpus = decode(pinned(args.corpus, plan["dedupe_corpus_sha256"]))
    queries = validate_plan(plan, snapshot, corpus, args.source_repo)
    if args.report.exists():
        raise ValueError("Use a new report path; evidence is not overwritten")
    if args.apply:
        branch = git(args.pages, "branch", "--show-current").decode().strip()
        remote = git(args.pages, "remote", "get-url", "origin").decode().strip()
        if not branch.startswith(("feature/", "feat/")) or not remote.endswith("/ios-app-guide.git"):
            raise ValueError("Only an isolated Guide feature may be modified; main/App writes are forbidden")
    prepared, records = [], []
    for page in plan["pages"]:
        path = args.pages / safe_path(page["path"])
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(args.pages.resolve()):
            raise ValueError("Do not create a new page or modify an outside-owner path")
        original = git(args.pages, "show", f"{plan['guide_base']}:{page['path']}")
        updated, record = render(original, page, queries, corpus)
        current = path.read_bytes()
        if current not in {original, updated}:
            raise ValueError("Target page contains unrelated WIP")
        prepared.append((path, current, updated))
        records.append(record)
    if args.apply:
        apply_changes(prepared)
    result = {
        "schema": "lumi.owned-search-gap-candidate-report/v1", "plan_sha256": args.plan_sha256,
        "guide_base": plan["guide_base"],
        "classifications": {label: sum(x["classification"] == label for x in plan["classifications"]) for label in sorted(CLASSES)},
        "selected_query_count": sum(x["selected"] for x in plan["classifications"]),
        "target_page_count": len(records), "applied": args.apply, "pages": records,
        "network_calls": 0, "asc_mutations": 0, "social_posts": 0, "new_page_urls": 0,
        "head_metadata_changes": 0, "publication_authorized": False,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with args.report.open("x") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    print(json.dumps({key: result[key] for key in ("classifications", "selected_query_count", "target_page_count", "applied", "new_page_urls")}))


if __name__ == "__main__":
    main()
