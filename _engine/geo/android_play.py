#!/usr/bin/env python3
"""Google Play counterparts for live iOS apps (zero-token, rule based).

Data flow
---------
``~/AndroidPlay/bin/android_live_scan.py`` (local, every 30 minutes) writes
``android_live.json``: Android folders whose Play page is publicly live.
The cloud geo-daily run cannot read that local file, so
``geo/android_live_sync.py`` turns it into the committed, verified snapshot
``geo/data/android_live_snapshot.json`` (mirrored to the Guide's
``_engine/geo/data/``) only when its content changes.

Mapping Android -> iOS roster key is mechanical and recorded per app:

1. ``bundle_id_exact``     Play package == iOS bundleId (iTunes Lookup)
2. ``bundle_id_casefold``  same, ignoring case (unique match only)
3. ``store_title_exact``   normalized Play title == iOS roster name (unique)

Anything else stays in ``unmapped`` and never gets a link.  Retired apps
(``RETIRED_KEYS``) are never listed.

Consumers
---------
* ``inject_tree``      adds a Google Play link next to the first App Store
  CTA of each mapped app on every public HTML page of the site (answer,
  intent, comparison, tool, localized, guide and hub pages; idempotent,
  marker ``data-android-play``; stale markers are removed, so an app that
  leaves the snapshot loses its links on the next pass).  AMP Web Stories
  (``<amp-story>``) never get one: their CTA layer holds exactly the one
  direct App Store CTA (``validate_webstories``), so a pass only strips stale
  Play markers there.  The link carries
  the install referrer ``utm_source=<ct of that App Store CTA>&utm_campaign=
  <app key>`` (``tracked_play_url``, the same shape as 00_GrowthEngine
  ``agent/ct_codes.play_referrer_url``), so Play installs land on the same
  channel row as App Store downloads.
* ``llms_line``        one llms.txt sub-bullet per mapped app.
* ``injected_spans``   where the injected links sit, so ``aeo_answers_i18n``
  never treats them as translatable page copy.

Copy rule: the Android sentence only names Google Play and quotes the app's
own Play short description; it never claims iOS-only features (widgets,
Apple Watch, Live Activities, iCloud, ...).  ``ios_only_claim`` enforces it.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import html
import json
import os
from pathlib import Path
import re
import sys
import unicodedata
import urllib.parse


HERE = Path(__file__).resolve().parent
SNAPSHOT_PATH = HERE / "data" / "android_live_snapshot.json"
MANIFEST_PATH = HERE / "live_app_manifest.json"
PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SCHEMA = "lumi.android-live-snapshot/v1"
PLAY_PREFIX = "https://play.google.com/store/apps/details?id="
RETIRED_KEYS = frozenset({"aim990plus"})
MATCH_METHODS = ("bundle_id_exact", "bundle_id_casefold", "store_title_exact")
LAUNCH_WAVES = ("baseline", "new")
COPY_LOCALES = ("en-US", "zh-TW")
MAX_SHORT_DESCRIPTION = 80
PACKAGE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+$")
APP_ID_RE = re.compile(r"^\d{9,12}$")
MARKER = "data-android-play"
# Every published HTML page; the engine, CI data and dependencies are not site pages.
EXCLUDED_PARTS = frozenset({".git", ".github", "_engine", "node_modules"})
CT_RE = re.compile(r"^[A-Za-z0-9_-]{1,40}$")
APP_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9_]{0,39}$")
# Generators that pin each output page by digest (hero_tasks); their pages are
# theirs byte for byte, so a Play link there would fail their --check gate.
DIGEST_PINNED_MANIFESTS = ("data/hero-tasks/manifest.json",)
# Pages whose App Store CTA has no ct of its own (channel geo_pages in agent/ct_codes.py).
DEFAULT_CT = "iag_play"
IOS_ONLY_RE = re.compile(
    r"widget|apple\s*watch|watch\s*os|live\s*activit|dynamic\s*island|icloud|"
    r"\bsiri\b|iphone|ipad|\bios\b|app\s*store|airdrop|face\s*id|touch\s*id|"
    r"healthkit|apple\s*health|imessage|carplay|\bmacos\b|"
    r"小工具|小組件|即時動態|動態島|靈動島|捷徑",
    re.IGNORECASE,
)
_APP_STORE_ANCHOR_RE = re.compile(
    r'<a\b(?:(?!<a\b)[^>])*?\bhref="https://apps\.apple\.com/'
    r'[^"]*?/id(?P<app_id>\d{9,12})[^"]*"[^>]*>.*?</a>',
    re.IGNORECASE | re.DOTALL,
)
_INJECTED_RE = re.compile(
    r'\s*<(?P<tag>p|a) class="android-play" ' + MARKER
    + r'="[^"]*"[^>]*>.*?</(?P=tag)>',
    re.DOTALL,
)
_HTML_LANG_RE = re.compile(r'<html\b[^>]*\blang="([^"]+)"', re.IGNORECASE)
# AMP Web Stories: the story's CTA layer is a single-action App Store surface
# gated by validate_webstories (exactly one direct App Store CTA per story).
_AMP_STORY_RE = re.compile(r"<amp-story[\s>]", re.IGNORECASE)
_MANAGED_BLOCK_RE = re.compile(
    r"<!--\s*(?P<name>[\w.-]+):start\s*-->.*?<!--\s*(?P=name):end\s*-->",
    re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")


# Markers that only wrap a page's own content (aeo_answers microformats); what is
# inside them is ordinary page copy, not a block another generator rewrites.
WRAPPER_BLOCKS = frozenset({"answer-microformat", "answer-content"})
# Blocks that float over the page (fixed bottom bar); a CTA there is the last resort.
FLOATING_BLOCKS = frozenset({"mobile-store-cta"})
_BLOCK_START_RE = re.compile(r"<!--\s*(?P<name>[\w.-]+):start\s*-->")


def _managed_spans(source: str) -> list[tuple[int, int, str]]:
    """Regions owned by other generators (``<!-- x:start -->`` .. ``:end``), nested ones included."""
    spans = []
    for start in _BLOCK_START_RE.finditer(source):
        name = start.group("name")
        if name in WRAPPER_BLOCKS:
            continue
        end = re.compile(r"<!--\s*" + re.escape(name) + r":end\s*-->").search(source, start.end())
        if end:
            spans.append((start.start(), end.end(), name))
    return spans


def _owning_block(spans: list[tuple[int, int, str]], position: int) -> tuple[int, int, str] | None:
    """The outermost generator-owned block around ``position``."""
    containing = [span for span in spans if span[0] <= position < span[1]]
    return max(containing, key=lambda span: span[1] - span[0]) if containing else None


def _is_text_cta(anchor: str) -> bool:
    """Visible-text CTA (not an image-only preview link)."""
    return bool(html.unescape(_TAG_RE.sub("", anchor)).strip())


class SnapshotError(ValueError):
    """The snapshot cannot be trusted; consumers then publish nothing."""


def parse_time(value: object) -> datetime:
    """ISO-8601 with offset; accepts the scanner's ``+0800`` on Python < 3.11."""
    text = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", str(value).replace("Z", "+00:00"))
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        raise SnapshotError(f"timestamp without offset: {value!r}")
    return parsed


def play_url(package: str) -> str:
    if not isinstance(package, str) or not PACKAGE_RE.match(package):
        raise SnapshotError(f"invalid Android package: {package!r}")
    return PLAY_PREFIX + package


def tracked_play_url(play: str, ct: str, app: str) -> str:
    """Play link with the install referrer utm_source=<ct>&utm_campaign=<app key>."""
    if not str(play or "").startswith(PLAY_PREFIX) or not PACKAGE_RE.match(play[len(PLAY_PREFIX):]):
        raise SnapshotError(f"not a bare Google Play details URL: {play!r}")
    if not CT_RE.match(ct or "") or not APP_KEY_RE.match(app or ""):
        raise SnapshotError(f"invalid Play referrer ct/app: {ct!r} {app!r}")
    referrer = urllib.parse.quote(f"utm_source={ct}&utm_campaign={app}", safe="")
    return f"{play}&referrer={referrer}"


def _anchor_ct(anchor: str) -> str:
    """The ct of an App Store anchor's href, or DEFAULT_CT."""
    href = re.search(r'\bhref="([^"]*)"', anchor)
    query = urllib.parse.urlsplit(html.unescape(href.group(1))).query if href else ""
    ct = (urllib.parse.parse_qs(query).get("ct") or [""])[0]
    return ct if CT_RE.match(ct) else DEFAULT_CT


def ios_only_claim(text: str) -> bool:
    return bool(IOS_ONLY_RE.search(text or ""))


def normalize_title(value: str) -> str:
    """Store title without subtitle/punctuation, for exact name matching."""
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = re.split(r"\s*[:：|｜]\s*|\s+[-–—]\s+", text, maxsplit=1)[0]
    return re.sub(r"[^0-9a-z㐀-鿿]+", "", text)


def load_manifest_apps(path: Path = MANIFEST_PATH) -> dict[str, dict]:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    apps = document.get("apps") if isinstance(document, dict) else None
    if not isinstance(apps, dict) or not apps:
        raise SnapshotError("live_app_manifest has no apps")
    return apps


def _digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _clean_copy(value: object) -> str | None:
    text = " ".join(str(value or "").split())
    if not text or len(text) > MAX_SHORT_DESCRIPTION or ios_only_claim(text):
        return None
    return text


def build_snapshot(
    android_live: dict,
    manifest_apps: dict[str, dict],
    bundle_ids: dict[str, str],
    listings: dict[str, dict[str, dict[str, str]]],
) -> dict:
    """Mechanically map live Android folders to iOS roster keys.

    ``bundle_ids``: iOS app_id -> bundleId.  ``listings``: package ->
    locale -> {"title", "short_description"} from the Play listing source.
    """
    live = android_live.get("apps") if isinstance(android_live, dict) else None
    if not isinstance(live, dict):
        raise SnapshotError("android_live.json has no apps")
    roster = {
        key: value for key, value in manifest_apps.items()
        if key not in RETIRED_KEYS
    }
    by_bundle: dict[str, list[str]] = {}
    by_fold: dict[str, list[str]] = {}
    by_title: dict[str, list[str]] = {}
    for key, value in roster.items():
        bundle = bundle_ids.get(str(value.get("app_id")))
        if bundle:
            by_bundle.setdefault(bundle, []).append(key)
            by_fold.setdefault(bundle.casefold(), []).append(key)
        title = normalize_title(value.get("name", ""))
        if title:
            by_title.setdefault(title, []).append(key)
    first_values = sorted(
        str(entry.get("first_seen")) for entry in live.values()
        if isinstance(entry, dict) and entry.get("first_seen")
    )
    baseline = first_values[0] if first_values else None
    mapped: dict[str, dict] = {}
    unmapped: list[dict] = []
    for folder in sorted(live):
        entry = live[folder]
        package = entry.get("package") if isinstance(entry, dict) else None
        if not isinstance(package, str) or not PACKAGE_RE.match(package):
            unmapped.append({"folder": folder, "package": package,
                             "reason": "invalid_package"})
            continue
        listing = listings.get(package) or {}
        play_title = (listing.get("en-US") or {}).get("title") or ""
        key = method = None
        for candidates, name in (
            (by_bundle.get(package, []), "bundle_id_exact"),
            (by_fold.get(package.casefold(), []), "bundle_id_casefold"),
            (by_title.get(normalize_title(play_title), [])
             if normalize_title(play_title) else [], "store_title_exact"),
        ):
            if len(candidates) == 1:
                key, method = candidates[0], name
                break
            if len(candidates) > 1:
                break
        if key is None:
            unmapped.append({"folder": folder, "package": package,
                             "reason": "no_unique_ios_match"})
            continue
        if key in mapped:
            other = mapped.pop(key)
            unmapped += [
                {"folder": other["android_folder"], "package": other["package"],
                 "reason": f"duplicate_ios_key:{key}"},
                {"folder": folder, "package": package,
                 "reason": f"duplicate_ios_key:{key}"},
            ]
            continue
        copy = {}
        for locale in COPY_LOCALES:
            row = listing.get(locale) or {}
            short = _clean_copy(row.get("short_description"))
            title = " ".join(str(row.get("title") or "").split())
            if title and not ios_only_claim(title):
                copy[locale] = {"title": title, **({"short_description": short} if short else {})}
        first_seen = str(entry.get("first_seen") or "")
        mapped[key] = {
            "ios_app_id": str(roster[key]["app_id"]),
            "ios_name": roster[key]["name"],
            "android_folder": folder,
            "package": package,
            "play_url": play_url(package),
            "paid": bool(entry.get("paid")),
            "first_seen": first_seen,
            "launch_wave": "baseline" if first_seen == baseline else "new",
            "match": method,
            "copy": copy,
        }
    unmapped.sort(key=lambda row: (row["folder"], row["reason"]))
    body = {"apps": dict(sorted(mapped.items())), "unmapped": unmapped,
            "baseline_first_seen": baseline}
    return {
        "schema": SCHEMA,
        "source": "AndroidPlay android_live_scan (Play page HTTP 200 + publish LIVE)",
        "source_generated": android_live.get("generated"),
        "count": len(mapped),
        "content_sha256": _digest(body),
        **body,
    }


def validate_snapshot(
    document: dict, manifest_apps: dict[str, dict], *, strict: bool = True
) -> dict[str, dict]:
    """Integrity is always enforced; roster drift drops the app unless strict.

    The Guide mirrors ``live_app_manifest.json`` on its own cadence, so a
    consumer there may briefly see a key or App ID it does not know yet.  That
    one app then gets no link (``strict=False``); tests use ``strict=True``.
    """
    if not isinstance(document, dict) or document.get("schema") != SCHEMA:
        raise SnapshotError("unexpected android snapshot schema")
    apps = document.get("apps")
    unmapped = document.get("unmapped")
    if not isinstance(apps, dict) or not isinstance(unmapped, list):
        raise SnapshotError("android snapshot apps/unmapped missing")
    body = {"apps": apps, "unmapped": unmapped,
            "baseline_first_seen": document.get("baseline_first_seen")}
    if document.get("content_sha256") != _digest(body):
        raise SnapshotError("android snapshot content_sha256 mismatch")
    if document.get("count") != len(apps):
        raise SnapshotError("android snapshot count mismatch")
    packages: set[str] = set()
    usable: dict[str, dict] = {}
    for key, entry in apps.items():
        if key in RETIRED_KEYS:
            raise SnapshotError(f"retired app listed: {key}")
        roster = manifest_apps.get(key)
        drift = None
        if not isinstance(roster, dict):
            drift = f"android snapshot key not in live roster: {key}"
        elif str(entry.get("ios_app_id")) != str(roster.get("app_id")):
            drift = f"iOS app_id drift for {key}"
        package = entry.get("package")
        if entry.get("play_url") != play_url(package):
            raise SnapshotError(f"play_url does not match package for {key}")
        if package in packages:
            raise SnapshotError(f"duplicate package {package}")
        packages.add(package)
        if entry.get("match") not in MATCH_METHODS:
            raise SnapshotError(f"unknown match method for {key}")
        if entry.get("launch_wave") not in LAUNCH_WAVES:
            raise SnapshotError(f"unknown launch wave for {key}")
        parse_time(entry.get("first_seen"))
        for locale, row in (entry.get("copy") or {}).items():
            for field in ("title", "short_description"):
                if field in row and ios_only_claim(row[field]):
                    raise SnapshotError(f"iOS-only claim in {key} {locale} {field}")
        if drift and strict:
            raise SnapshotError(drift)
        if drift:
            print(f"android_play: skip {key} ({drift})", file=sys.stderr)
            continue
        usable[key] = entry
    return usable


def load_snapshot(
    path: Path = SNAPSHOT_PATH, manifest_path: Path = MANIFEST_PATH
) -> dict[str, dict]:
    """Mapped apps keyed by iOS roster key; {} when no snapshot exists."""
    path = Path(path)
    if not path.exists():
        return {}
    document = json.loads(path.read_text(encoding="utf-8"))
    return validate_snapshot(
        document, load_manifest_apps(manifest_path), strict=False
    )


def _copy(entry: dict, locale: str = "en-US") -> dict:
    return (entry.get("copy") or {}).get(locale) or {}


def display_name(key: str, entry: dict) -> str:
    """Play title without its store subtitle ("ScanTo Pro: Offline PDF" -> "ScanTo Pro")."""
    title = _copy(entry).get("title") or entry.get("ios_name") or key
    return re.split(r"\s*[:：|｜]\s*|\s+[-–—]\s+", title, maxsplit=1)[0].strip() or title


def android_sentence(key: str, entry: dict) -> str:
    """Plain English sentence for the Android edition (no feature claims)."""
    name = display_name(key, entry)
    short = _copy(entry).get("short_description")
    sentence = f"{name} is also available for Android on Google Play"
    return f"{sentence}: {short.rstrip('.')}." if short else f"{sentence}."


def llms_line(key: str, apps: dict[str, dict] | None = None) -> str | None:
    apps = _cached_apps() if apps is None else apps
    entry = apps.get(key)
    if not entry:
        return None
    return (f"  - Android: [Google Play]({entry['play_url']}) — "
            f"{android_sentence(key, entry)}")


_CACHE: dict[str, dict] | None = None


def _cached_apps() -> dict[str, dict]:
    global _CACHE
    if _CACHE is None:
        try:
            _CACHE = load_snapshot()
        except (OSError, ValueError) as error:
            print(f"android_play: snapshot ignored ({error})", file=sys.stderr)
            _CACHE = {}
    return _CACHE


_P_OPEN_RE = re.compile(r"<p[\s>]", re.IGNORECASE)
_P_CLOSE_RE = re.compile(r"</p>", re.IGNORECASE)


def _last(pattern: re.Pattern, source: str, end: int) -> int:
    found = -1
    for match in pattern.finditer(source, 0, end):
        found = match.start()
    return found


def _inside_paragraph(source: str, start: int) -> bool:
    # Offsets stay in ``source`` coordinates: str.lower() changes the length of
    # some characters (Turkish "İ"), which would shift every later position.
    return _last(_P_OPEN_RE, source, start) > _last(_P_CLOSE_RE, source, start)


def _paragraph_close(source: str, start: int) -> int:
    match = _P_CLOSE_RE.search(source, start)
    return match.start() if match else -1


def is_web_story(source: str) -> bool:
    """AMP Web Story document (``<amp-story>``); never gets a Play link."""
    return bool(_AMP_STORY_RE.search(source))


def injected_spans(source: str) -> list[tuple[int, int]]:
    """Offsets of the Play links this module injected into ``source``.

    They are this module's own markup, re-rendered in each page's language on
    every pass, so localizers skip them instead of treating them as page copy.
    """
    return [match.span() for match in _INJECTED_RE.finditer(source)]


def inject_html(source: str, apps: dict[str, dict]) -> str:
    """Add one Google Play link after the first App Store CTA per mapped app.

    AMP Web Stories are left without one (stale Play markers are still
    stripped): ``validate_webstories`` requires their CTA layer to hold exactly
    the direct App Store CTA.

    Only visible-text CTAs count, and blocks managed by other generators
    (``<!-- x:start -->`` .. ``:end``) stay byte-identical: a CTA that only
    exists inside such a block gets its Play paragraph right after the block.
    """
    text = _INJECTED_RE.sub("", source)
    if is_web_story(text):
        return text
    by_id = {str(entry["ios_app_id"]): (key, entry) for key, entry in apps.items()}
    lang = (_HTML_LANG_RE.search(text) or [None, ""])[1].lower()
    english = lang == "en" or lang.startswith("en-")
    seen: set[str] = set()
    inserts: list[tuple[int, str]] = []
    managed = _managed_spans(text)
    candidates = []
    for match in _APP_STORE_ANCHOR_RE.finditer(text):
        if match.group("app_id") in by_id and _is_text_cta(match.group(0)):
            block = _owning_block(managed, match.start())
            # Page copy first; then generator-owned body blocks; the floating
            # mobile bar last.  A CTA in a block gets its Play paragraph right
            # after that block, so the block's own generator keeps its bytes.
            rank = 0 if block is None else 2 if block[2] in FLOATING_BLOCKS else 1
            candidates.append((rank, match.start(), match, block))
    for _rank, _start, match, block in sorted(candidates, key=lambda c: c[:2]):
        app_id = match.group("app_id")
        if app_id in seen:
            continue
        seen.add(app_id)
        key, entry = by_id[app_id]
        url = html.escape(
            tracked_play_url(entry["play_url"], _anchor_ct(match.group(0)), key), quote=True
        )
        package = html.escape(entry["package"], quote=True)
        if block is not None or _inside_paragraph(text, match.start()):
            if block is not None and not _inside_paragraph(text, block[1]):
                position = block[1]
            else:
                close = _paragraph_close(text, block[1] if block else match.end())
                if close < 0:
                    continue
                position = close + 4
            if english:
                name = display_name(key, entry)
                short = _copy(entry).get("short_description")
                body = (f'Also on Android: <a href="{url}" rel="noopener">'
                        f"Get {html.escape(name)} on Google Play →</a>"
                        + (f" — {html.escape(short)}" if short else ""))
            else:
                body = f'Android: <a href="{url}" rel="noopener">Google Play</a>'
            inserts.append((position,
                            f'\n  <p class="android-play" {MARKER}="{package}">'
                            f"{body}</p>"))
        else:
            inserts.append((match.end(),
                            f'\n      <a class="android-play" {MARKER}="{package}" '
                            f'href="{url}" rel="noopener">Google Play</a>'))
    for position, snippet in sorted(inserts, reverse=True):
        text = text[:position] + snippet + text[position:]
    return text


def _digest_pinned(pages: Path) -> set[str]:
    pinned: set[str] = set()
    for relative in DIGEST_PINNED_MANIFESTS:
        try:
            outputs = json.loads((pages / relative).read_text(encoding="utf-8")).get("outputs") or {}
        except (OSError, ValueError, AttributeError):
            continue
        pinned.update(str(path) for path in outputs)
    return pinned


def _site_pages(pages: Path):
    """Published HTML pages, without descending into the excluded directories
    or touching pages another generator pins by digest."""
    pinned = _digest_pinned(pages)
    for directory, subdirs, files in os.walk(pages):
        subdirs[:] = sorted(d for d in subdirs if d not in EXCLUDED_PARTS)
        for name in sorted(files):
            if name.endswith(".html"):
                path = Path(directory) / name
                if not path.is_symlink() and path.relative_to(pages).as_posix() not in pinned:
                    yield path


def inject_tree(pages: Path = PAGES, apps: dict[str, dict] | None = None) -> dict[str, int]:
    pages = Path(pages)
    if apps is None:
        try:
            apps = load_snapshot()
        except (OSError, ValueError) as error:
            print(f"android_play: snapshot invalid, pages untouched ({error})",
                  file=sys.stderr)
            return {"scanned": 0, "changed_files": 0, "apps": 0}
    scanned = changed = 0
    for path in _site_pages(pages):
        scanned += 1
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if MARKER not in source and "apps.apple.com/" not in source:
            continue
        updated = inject_html(source, apps)
        if updated != source:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    return {"scanned": scanned, "changed_files": changed, "apps": len(apps)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="validate the committed snapshot")
    check.add_argument("--snapshot", type=Path, default=SNAPSHOT_PATH)
    inject = sub.add_parser("inject", help="add Play links next to App Store CTAs on site pages")
    inject.add_argument("--pages", type=Path, default=PAGES)
    args = parser.parse_args(argv)
    if args.command == "check":
        document = json.loads(args.snapshot.read_text(encoding="utf-8"))
        apps = validate_snapshot(document, load_manifest_apps(), strict=True)
        print(f"android snapshot OK: {len(apps)} mapped apps")
        return 0
    stats = inject_tree(args.pages)
    print("Google Play links: " + ", ".join(f"{k}={v}" for k, v in stats.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
