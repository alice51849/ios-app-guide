#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Telegram 三時區輪播；原生憑證與送前保留存於獨立 Git ledger。"""
import argparse
import base64
import copy
import datetime as _dt
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import urllib.parse
import urllib.request

from social_post_common import (
    AMERICAS_LOCALES,
    ASIA_LOCALES,
    CHANNEL_ORDER,
    EUROPE_MIDDLE_EAST_LOCALES,
    HTTPStatusError,
    OFFICIAL_SOCIAL_LOCALES,
    RequestError,
    campaign_app_store_url,
    canonical_app_store_url,
    canonical_social_image_url,
    channel_candidates,
    item_footer,
    item_image_url,
    request_json,
)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = Path(HERE).parents[1]
INTENT_CATALOG_PATH = (
    REPO_ROOT
    / "data"
    / "lumi-studio-publisher-search-intent-catalog.json"
)
INTENT_I18N_PATH = (
    REPO_ROOT / "_engine" / "geo" / "publisher_intent_catalog_i18n.json"
)
SOCIAL_IMAGE_DIR = REPO_ROOT / "social" / "img"
SITE_URL = "https://open.cait518.cc/ios-app-guide"
PUBLISHER_LABEL = "First-party publisher catalog"

# 依 3 個排程時段(01/09/15 UTC)發對應時區的在地語言,讓各國看到自己語言的貼文。
TZ_LANGS = {
    "asia": list(ASIA_LOCALES),                    # 09:00 台灣 / 亞洲(21–05 UTC)
    "eu_me": list(EUROPE_MIDDLE_EAST_LOCALES),    # 歐洲早 / 中東(05–13 UTC)
    "americas": list(AMERICAS_LOCALES),           # 美洲(13–21 UTC)
}

REPOSITORY = "alice51849/ios-app-guide"
PUBLIC_CHANNEL = "LumiApps2026"
LEDGER_BRANCH = "telegram-native-ledger"
LEDGER_FILE = "telegram-ledger.json"
RUN_EVIDENCE = Path(".telegram-ledger-run")
SLOT_HOURS = (1, 9, 15)
SNAPSHOT_SHA256 = "ae8d6542ff37f77c8bb8f42e9c32daa596956d5a1a9f6d344b425b8dc7ca5242"

# Frozen official GET identities from platform-exact47-20260911. These are
# replay protection, not invented receipts: bootstrap must re-read every ID.
LEGACY_APP_MESSAGES = {
    "6754218117": (26, 40, 109, 177, 193, 229),
    "6755782939": (36, 43, 55, 75, 88, 133, 176),
    "6773017109": (84, 111, 135, 180, 196),
    "6775773117": (78, 92, 159, 230, 269),
    "6776958488": (17, 21, 61, 87, 138, 200, 232),
    "6778269699": (79, 113, 182),
    "6778491147": (46, 93, 160, 231),
    "6778748533": (85, 112, 136, 181, 197),
    "6779552704": (116, 140, 186, 202),
    "6779745474": (115, 139, 185, 201),
    "6779750237": (44, 80, 95, 120, 162),
    "6779977651": (67, 100, 187),
    "6780107485": (24, 56, 76, 91, 158, 267),
    "6780223070": (48, 119, 143, 207),
    "6780575828": (33, 50, 68, 101, 164, 190, 211),
    "6781337213": (19, 23, 53, 73, 107, 131, 224),
    "6781808054": (99, 121, 240, 274),
    "6782139553": (31, 37, 146, 191, 212),
    "6782251621": (32, 39, 154, 260),
    "6782275018": (28, 35, 41, 60, 148, 167, 213, 247),
    "6784974530": (27, 72, 129, 151, 171, 220, 255),
    "6785004775": (47, 117),
    "6787193643": (63, 96, 163, 235),
    "6787754435": (20, 51, 103, 192),
    "6788236641": (29, 57, 123, 144, 208, 244),
    "6789917808": (52, 128, 150, 217),
    "6790418321": (81, 108, 132, 175),
    "6790467886": (71, 104, 127),
    "6790800323": (65, 142, 203, 237),
    "6791299610": (59, 69, 125, 147, 166, 246),
    "6791658210": (105,),
    "6792850916": (64, 97, 236),
    "6792856304": (124, 245),
    "6793414462": (168, 216),
    "6793436548": (156, 226),
    "6794039979": (83, 89, 134, 266),
    "6794178671": (152, 172, 259),
    "6794725568": (155, 225, 262),
    "6797601720": (251,),
    "6798813048": (170, 253),
    "6798814385": (206,),
    "6801956402": (273,),
    "6802423998": (221,),
    "6802505528": (241, 276),
}
LEGACY_PRODUCTION_LOCALES = {
    211: ("en-US", 33320085183), 212: ("en-AU", 33348068683),
    213: ("en-GB", 33378416460), 216: ("en-CA", 33412272678),
    217: ("zh-Hant", 33458692581), 220: ("fr-FR", 33492789074),
    221: ("en-CA", 33526342634), 224: ("zh-Hant", 33580243465),
    225: ("de-DE", 33615839990), 226: ("en-CA", 33650091388),
    229: ("zh-Hant", 33703754179), 230: ("de-DE", 33739308085),
    231: ("en-CA", 33772510832), 232: ("vi", 33826641534),
    235: ("de-DE", 33859665816), 236: ("en-US", 33904282934),
    237: ("zh-Hant", 33936358707), 240: ("en-GB", 33961136636),
    241: ("en-US", 33974799922), 244: ("ja", 34004149150),
    245: ("ru", 34025212791), 246: ("en-US", 34042559731),
    247: ("ja", 34074512072), 251: ("fr-FR", 34107252025),
    253: ("en-US", 34153897626), 255: ("ko", 34177308333),
    259: ("fr-FR", 34210940476), 260: ("en-US", 34244731449),
    262: ("ms", 34310610556), 266: ("pl", 34334999157),
    267: ("en-CA", 34370151357), 269: ("en-AU", 34425767802),
    273: ("da", 34461015520), 274: ("en-US", 34497353888),
    276: ("en-AU", 34550919089),
}
LEGACY_IDENTITIES = {
    message_id: app_id
    for app_id, message_ids in LEGACY_APP_MESSAGES.items()
    for message_id in message_ids
}
EXACT47_APP_IDS = frozenset(LEGACY_APP_MESSAGES) | {
    "6792483140", "6802166527", "6806776579",
}


def _json_bytes(value):
    return (json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ) + "\n").encode("utf-8")


def _digest(text):
    # Identical caption/text is never replayed, even if the image/source changes.
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("missing evidence timestamp")
    result = _dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("evidence timestamp must include timezone")
    return result.astimezone(_dt.timezone.utc)


def _sha(value, length=40):
    if not isinstance(value, str) or not re.fullmatch(
        rf"[0-9a-f]{{{length}}}", value
    ):
        raise ValueError("invalid evidence digest")
    return value


def _delivery_id(message_id):
    if type(message_id) is not int or message_id <= 0:
        raise ValueError("invalid native message_id")
    return f"{PUBLIC_CHANNEL}/{message_id}"


def _app_ids(urls):
    result = set()
    for url in urls:
        parsed = urllib.parse.urlsplit(url)
        match = re.search(r"/id([0-9]+)$", parsed.path)
        if parsed.scheme == "https" and parsed.hostname == "apps.apple.com" and match:
            result.add(match.group(1))
    return result


class PublicMessages(HTMLParser):
    """Read only message bodies/IDs/times, never channel UI or storefront locale."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.messages = []
        self.depth = 0
        self.current = None
        self.text_depth = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "div":
            self.depth += 1
            native = re.fullmatch(
                rf"{PUBLIC_CHANNEL}/([1-9][0-9]*)", attrs.get("data-post", "")
            )
            if native:
                self.current = {
                    "message_id": int(native.group(1)), "depth": self.depth,
                    "parts": [], "urls": [],
                }
            if self.current and "tgme_widget_message_text" in attrs.get("class", "").split():
                self.text_depth = self.depth
        if not self.current:
            return
        if tag == "time" and attrs.get("datetime"):
            self.current["timestamp"] = _timestamp(attrs["datetime"]).isoformat()
        if self.text_depth is not None:
            if tag == "br":
                self.current["parts"].append("\n")
            if tag == "a" and attrs.get("href"):
                self.current["urls"].append(attrs["href"])

    def handle_data(self, data):
        if self.current and self.text_depth is not None:
            self.current["parts"].append(data)

    def handle_endtag(self, tag):
        if tag != "div":
            return
        if self.text_depth == self.depth:
            self.text_depth = None
        if self.current and self.current["depth"] == self.depth:
            record = self.current
            record["text"] = "".join(record.pop("parts")).strip()
            record["app_ids"] = sorted(_app_ids(record.pop("urls")))
            record.pop("depth")
            self.messages.append(record)
            self.current = None
        self.depth -= 1


def read_public_history(required_ids=(), since=None):
    required = set(required_ids)
    messages = {}
    before = None
    for _page in range(40):
        url = f"https://t.me/s/{PUBLIC_CHANNEL}"
        if before is not None:
            url += f"?before={before}"
        request = urllib.request.Request(
            url, headers={"User-Agent": "LumiStudio-Telegram-Receipt-Reader/1.0"}
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.geturl() != url:
                raise RequestError("Telegram public history redirected")
            raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise RequestError("Telegram public history exceeds read limit")
        parser = PublicMessages()
        parser.feed(raw.decode("utf-8"))
        if not parser.messages:
            break
        observed = _dt.datetime.now(_dt.timezone.utc).isoformat()
        for message in parser.messages:
            message["evidence"] = {
                "kind": "telegram_official_get", "url": url,
                "response_sha256": hashlib.sha256(raw).hexdigest(),
                "observed_at": observed,
            }
            messages.setdefault(message["message_id"], message)
        oldest = min(message["message_id"] for message in parser.messages)
        complete = required.issubset(messages)
        if complete and (
            since is None or any(
                _timestamp(message["timestamp"]) < since
                for message in parser.messages if message.get("timestamp")
            )
        ):
            return messages
        if before is not None and oldest >= before:
            raise RequestError("Telegram public history cursor did not advance")
        before = oldest
    if not required and messages:
        # Partial readback cannot release an unknown reservation, but it must
        # not stop unrelated Apps when an old uncertain send leaves the window.
        return messages
    raise RequestError("Telegram native history is incomplete; publication blocked")


class GitHubLedger:
    """CAS updates on an orphan data branch; never write the publisher branch."""

    def __init__(self, token):
        if not token:
            raise ValueError("GITHUB_TOKEN is required for durable receipts")
        self.token = token
        self.blob_sha = None

    def api(self, path, method="GET", body=None):
        request = urllib.request.Request(
            f"https://api.github.com/repos/{REPOSITORY}/{path}",
            data=None if body is None else _json_bytes(body),
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        return request_json(
            request, label="Telegram durable ledger", timeout=30,
            attempts=3 if method == "GET" else 1,
        )

    def assert_current_source(self, source_sha):
        current = self.api("git/ref/heads/main")
        if current.get("object", {}).get("sha") != _sha(source_sha):
            raise ValueError("publisher source drifted from current main; no send")

    def historical_source(self, run_id):
        try:
            run = self.api(f"actions/runs/{int(run_id)}")
        except HTTPStatusError as error:
            if error.status == 404:
                return None
            raise
        if (
            run.get("path") != ".github/workflows/telegram-daily.yml"
            or run.get("head_repository", {}).get("full_name") != REPOSITORY
            or run.get("head_branch") != "main"
        ):
            raise ValueError("historical production run identity mismatch")
        return _sha(run.get("head_sha"))

    def load(self):
        try:
            file = self.api(f"contents/{LEDGER_FILE}?ref={LEDGER_BRANCH}")
        except HTTPStatusError as error:
            if error.status != 404:
                raise
            try:
                self.api(f"git/ref/heads/{LEDGER_BRANCH}")
            except HTTPStatusError as branch_error:
                if branch_error.status == 404:
                    return None
                raise
            raise ValueError("existing ledger branch lost its state; no bootstrap")
        self.blob_sha = _sha(file.get("sha"))
        if file.get("encoding") != "base64":
            file = self.api(f"git/blobs/{self.blob_sha}")
        if file.get("encoding") != "base64":
            raise ValueError("ledger blob is not readable")
        raw = base64.b64decode(file["content"])
        if hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() != self.blob_sha:
            raise ValueError("ledger blob digest mismatch")
        ledger = json.loads(raw)
        validate_ledger(ledger)
        return ledger

    def save(self, ledger):
        validate_ledger(ledger)
        raw = _json_bytes(ledger)
        write_run_evidence("ledger.json", ledger)
        expected = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
        if self.blob_sha is None:
            blob = self.api("git/blobs", "POST", {
                "content": raw.decode("utf-8"), "encoding": "utf-8",
            })
            if blob.get("sha") != expected:
                raise ValueError("bootstrap blob digest mismatch")
            tree = self.api("git/trees", "POST", {"tree": [{
                "path": LEDGER_FILE, "mode": "100644",
                "type": "blob", "sha": expected,
            }]})
            commit = self.api("git/commits", "POST", {
                "message": "建立 Telegram 原生憑證台帳，保護已確認訊息",
                "tree": _sha(tree.get("sha")), "parents": [],
            })
            path, method, body = "git/refs", "POST", {
                "ref": f"refs/heads/{LEDGER_BRANCH}",
                "sha": _sha(commit.get("sha")),
            }
        else:
            path, method, body = f"contents/{LEDGER_FILE}", "PUT", {
                "message": "保存 Telegram 送前保留與原生回執，避免雙發",
                "branch": LEDGER_BRANCH, "sha": self.blob_sha,
                "content": base64.b64encode(raw).decode("ascii"),
            }
        try:
            self.api(path, method, body)
        except RequestError:
            # A lost GitHub response is reconciled by GET, never by another send.
            file = self.api(f"contents/{LEDGER_FILE}?ref={LEDGER_BRANCH}")
            if file.get("sha") != expected:
                raise RequestError("ledger CAS not confirmed; publication blocked")
        file = self.api(f"contents/{LEDGER_FILE}?ref={LEDGER_BRANCH}")
        if file.get("sha") != expected:
            raise RequestError("ledger durable readback mismatch; publication blocked")
        self.blob_sha = expected


def write_run_evidence(name, value):
    RUN_EVIDENCE.mkdir(parents=True, exist_ok=True)
    target = RUN_EVIDENCE / name
    staging = RUN_EVIDENCE / f"{name}.writing"
    with staging.open("wb") as output:
        os.chmod(staging, 0o600)
        output.write(_json_bytes(value))
        output.flush()
        os.fsync(output.fileno())
    os.replace(staging, target)


def validate_ledger(ledger):
    if (
        not isinstance(ledger, dict) or ledger.get("schema_version") != 1
        or ledger.get("channel") != PUBLIC_CHANNEL
        or ledger.get("protected_snapshot_sha256") != SNAPSHOT_SHA256
        or not isinstance(ledger.get("receipts"), dict)
        or not isinstance(ledger.get("intents"), dict)
    ):
        raise ValueError("invalid Telegram durable ledger")
    for key, receipt in ledger["receipts"].items():
        if (
            not isinstance(receipt, dict)
            or key != _delivery_id(receipt.get("message_id"))
            or receipt.get("channel") != PUBLIC_CHANNEL
            or not re.fullmatch(r"[0-9]+", str(receipt.get("app_store_id", "")))
            or receipt.get("official_locale") not in (None, *OFFICIAL_SOCIAL_LOCALES)
            or receipt.get("locale") != receipt.get("official_locale")
        ):
            raise ValueError("invalid Telegram native receipt")
        _sha(receipt.get("payload_digest"), 64)
        _timestamp(receipt.get("timestamp"))
        evidence = receipt.get("evidence", {})
        if evidence.get("kind") not in {
            "telegram_official_get", "telegram_production_response",
        }:
            raise ValueError("native receipt has no official evidence")
        _sha(evidence.get("response_sha256"), 64)
        _timestamp(evidence.get("observed_at"))
        if receipt.get("source_sha") is not None:
            _sha(receipt["source_sha"])
        if evidence["kind"] == "telegram_production_response" and (
            receipt.get("official_locale") not in OFFICIAL_SOCIAL_LOCALES
            or receipt.get("source_sha") is None
            or type(receipt.get("channel_id")) is not int
            or receipt["channel_id"] >= 0
        ):
            raise ValueError("production receipt is missing its locale/source/channel")
    for message_id, app_id in LEGACY_IDENTITIES.items():
        if ledger["receipts"].get(_delivery_id(message_id), {}).get("app_store_id") != app_id:
            raise ValueError("protected historical receipt was lost or changed")
    for slot, intent in ledger["intents"].items():
        stamp = _timestamp(slot)
        if (
            stamp.hour not in SLOT_HOURS or stamp.minute or stamp.second
            or intent.get("slot") != slot
            or intent.get("status") not in {
                "reserved", "unknown", "confirmed", "rejected", "not_sent",
            }
            or intent.get("official_locale") not in OFFICIAL_SOCIAL_LOCALES
            or intent.get("official_locale") not in TZ_LANGS[_zone(stamp.hour)]
            or intent.get("app_store_id") not in EXACT47_APP_IDS
            or intent.get("payload_digest") != _digest(intent.get("text", ""))
        ):
            raise ValueError("invalid Telegram send reservation")
        _sha(intent.get("source_sha"))
        _timestamp(intent.get("reserved_at"))
        if intent["status"] == "confirmed":
            receipt = ledger["receipts"].get(intent.get("delivery_id"), {})
            if any(
                receipt.get(field) != intent.get(field)
                for field in ("app_store_id", "official_locale", "source_sha", "payload_digest")
            ):
                raise ValueError("confirmed reservation lost its native receipt")


def bootstrap_ledger(messages, source_sha, historical_source):
    receipts = {}
    for message_id, expected_app in LEGACY_IDENTITIES.items():
        message = messages.get(message_id, {})
        if message.get("app_ids") != [expected_app] or not message.get("text"):
            raise ValueError(f"protected Telegram message {message_id} is not verified")
    for message_id, message in messages.items():
        app_ids = message.get("app_ids", [])
        if len(app_ids) != 1 or not message.get("text") or not message.get("timestamp"):
            continue
        locale, run_id = LEGACY_PRODUCTION_LOCALES.get(message_id, (None, None))
        receipt = {
            "channel": PUBLIC_CHANNEL, "message_id": message_id,
            "app_store_id": app_ids[0], "official_locale": locale, "locale": locale,
            "payload_digest": _digest(message["text"]),
            "payload_digest_kind": "sha256:utf8-caption-or-text",
            "source_sha": historical_source(run_id) if run_id else None,
            "timestamp": message["timestamp"],
            "evidence": message["evidence"],
            "readback_source_sha": source_sha,
            "locale_evidence": (
                {"production_run_id": run_id, "snapshot_sha256": SNAPSHOT_SHA256}
                if run_id else None
            ),
        }
        receipts[_delivery_id(message_id)] = receipt
    ledger = {
        "schema_version": 1, "channel": PUBLIC_CHANNEL,
        "protected_snapshot_sha256": SNAPSHOT_SHA256,
        "receipts": receipts, "intents": {},
    }
    validate_ledger(ledger)
    return ledger


def _zone(hour_utc):
    if 5 <= hour_utc < 13:
        return "eu_me"
    if 13 <= hour_utc < 21:
        return "americas"
    return "asia"  # 21–05 UTC(含 01:00 排程)


def _one_line(value, label):
    if (
        not isinstance(value, str)
        or not value.strip()
        or "\n" in value
        or "\r" in value
    ):
        raise ValueError(f"{label} must be a non-empty single line")
    return value.strip()


def _load_intent_pool(live_apps):
    with open(INTENT_CATALOG_PATH, encoding="utf-8") as catalog_file:
        catalog = json.load(catalog_file)
    with open(INTENT_I18N_PATH, encoding="utf-8") as i18n_file:
        i18n = json.load(i18n_file)

    locales = catalog.get("locales")
    records = catalog.get("records")
    localizations = i18n.get("localizations")
    if (
        not isinstance(locales, list)
        or len(locales) != 50
        or set(locales) != set(OFFICIAL_SOCIAL_LOCALES)
        or not isinstance(records, list)
        or not isinstance(localizations, dict)
    ):
        raise ValueError("publisher intent catalog does not cover 50 locales")

    expected = {
        (app_id, locale)
        for app_id in live_apps
        for locale in OFFICIAL_SOCIAL_LOCALES
    }
    observed = set()
    pool = []
    for record in records:
        if not isinstance(record, dict) or record.get("verified_live") is not True:
            raise ValueError("publisher intent record is not verified live")
        app_id = str(record.get("app_store_id") or "")
        locale = str(record.get("locale") or "")
        key = str(record.get("app_key") or "")
        pair = (app_id, locale)
        if (
            app_id not in live_apps
            or locale not in OFFICIAL_SOCIAL_LOCALES
            or pair in observed
            or re.fullmatch(r"[a-z0-9]+", key) is None
        ):
            raise ValueError(f"invalid publisher intent social record: {pair}")
        canonical = canonical_app_store_url(
            record.get("canonical_app_store_url")
        )
        if canonical != live_apps[app_id].appstore_url():
            raise ValueError(f"publisher intent App Store mismatch: {pair}")
        image_path = SOCIAL_IMAGE_DIR / f"{key}-share.jpg"
        if not image_path.is_file() or image_path.stat().st_size <= 0:
            raise ValueError(f"missing social image for {key}")
        image_url = canonical_social_image_url(
            f"{SITE_URL}/social/img/{key}-share.jpg"
        )
        translations = localizations.get(locale)
        if not isinstance(translations, dict):
            raise ValueError(f"missing publisher label localization: {locale}")
        publisher_label = _one_line(
            translations.get(PUBLISHER_LABEL),
            f"publisher label {locale}",
        )
        query = _one_line(record.get("publisher_query"), f"query {pair}")
        cta = _one_line(
            record.get("app_store_cta_label"),
            f"App Store CTA {pair}",
        )
        pool.append(
            {
                "lang": locale,
                "app": app_id,
                "app_key": key,
                "text": f"{query}\n{cta}",
                "url": canonical,
                "image_url": image_url,
                "footer": f"— Lumi Studio · {publisher_label}",
                "source": "publisher_intent_catalog",
            }
        )
        observed.add(pair)
    if observed != expected:
        missing = sorted(expected - observed)
        unexpected = sorted(observed - expected)
        raise ValueError(
            "publisher intent social coverage mismatch: "
            f"missing={missing[:5]}, unexpected={unexpected[:5]}"
        )
    return pool


def load_pool():
    with open(os.path.join(HERE, "telegram_posts.json"), encoding="utf-8") as f:
        static_pool = json.load(f)
    import portfolio_daily

    live_apps = {
        app.app_id: app for app in portfolio_daily.load_public_apps()
    }
    if set(live_apps) != EXACT47_APP_IDS:
        raise ValueError("Telegram current source must match the pinned exact47 App IDs")
    pool = _load_intent_pool(live_apps)
    for item in static_pool:
        app_id = str(item.get("app") or "")
        if app_id not in live_apps:
            continue
        normalized = dict(item)
        normalized["app"] = app_id
        normalized["url"] = canonical_app_store_url(
            f"https://apps.apple.com/app/id{app_id}"
        )
        pool.append(normalized)
    return pool


def candidates(pool, now=None):
    now = (
        _dt.datetime.now(_dt.timezone.utc)
        if now is None
        else now
    )
    zone = _zone(
        now.hour if now.tzinfo is None else now.astimezone(_dt.timezone.utc).hour
    )
    return channel_candidates(pool, f"telegram:{zone}", now)


def pick(pool, now=None):
    return candidates(pool, now)[0]


def compose_text(item):
    url = campaign_app_store_url(item.get("url"), "soc_tg_guide")
    return (
        f"{item['text']}\n\n👉 {url}\n\n"
        f"{item_footer(item)}"
    )


def pick_postable(pool, now=None):
    # load_pool() only contains apps from the verified live linkset. Avoid
    # probing the full portfolio again and tripping Apple's HTTP 429 limit.
    return candidates(pool, now)[0]


def _send_message(token, chat, text):
    data = urllib.parse.urlencode({
        "chat_id": chat,
        "text": text,
        "disable_web_page_preview": "false",
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=data,
        headers={"User-Agent": "Mozilla/5.0 (Lumi Apps poster)"},
    )
    return request_json(
        req,
        label="Telegram sendMessage",
        timeout=25,
        attempts=1,
    )


def _send_photo(token, chat, text, image_url):
    image_url = canonical_social_image_url(image_url)
    data = urllib.parse.urlencode({
        "chat_id": chat,
        "photo": image_url,
        "caption": text,
    }).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendPhoto",
        data=data,
        headers={"User-Agent": "Mozilla/5.0 (Lumi Apps poster)"},
    )
    return request_json(
        req,
        label="Telegram sendPhoto",
        timeout=30,
        attempts=1,
    )


def _local_image_path(image_url):
    image_url = canonical_social_image_url(image_url)
    image_path = SOCIAL_IMAGE_DIR / Path(
        urllib.parse.urlsplit(image_url).path
    ).name
    if not image_path.is_file() or image_path.stat().st_size <= 0:
        raise ValueError(f"Telegram local image is missing: {image_path.name}")
    return image_path


def _multipart_photo_body(chat, text, image_path, boundary):
    body = bytearray()
    for name, value in (("chat_id", chat), ("caption", text)):
        body.extend(f"--{boundary}\r\n".encode("ascii"))
        body.extend(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            .encode("ascii")
        )
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")
    body.extend(f"--{boundary}\r\n".encode("ascii"))
    body.extend(
        (
            'Content-Disposition: form-data; name="photo"; '
            f'filename="{image_path.name}"\r\n'
            "Content-Type: image/jpeg\r\n\r\n"
        ).encode("ascii")
    )
    body.extend(image_path.read_bytes())
    body.extend(f"\r\n--{boundary}--\r\n".encode("ascii"))
    return bytes(body)


def _send_photo_file(token, chat, text, image_path):
    image_path = Path(image_path)
    if not image_path.is_file() or image_path.stat().st_size <= 0:
        raise ValueError(f"Telegram local image is missing: {image_path.name}")
    boundary = f"LumiTelegram{secrets.token_hex(16)}"
    data = _multipart_photo_body(chat, text, image_path, boundary)
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendPhoto",
        data=data,
        headers={
            "User-Agent": "Mozilla/5.0 (Lumi Apps poster)",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    return request_json(
        req,
        label="Telegram local sendPhoto",
        timeout=30,
        attempts=1,
    )


def _publish_item(token, chat, text, item):
    image_url = item_image_url(item)
    if not image_url:
        return _send_message(token, chat, text)
    try:
        return _send_photo(token, chat, text, image_url)
    except HTTPStatusError as remote_error:
        if remote_error.status != 400:
            raise
        print(
            "Telegram remote image rejected; retrying the verified local JPEG: "
            f"{remote_error}",
            file=sys.stderr,
        )
    try:
        image_path = _local_image_path(image_url)
        return _send_photo_file(token, chat, text, image_path)
    except HTTPStatusError as local_error:
        if local_error.status != 400:
            raise
        print(
            "Telegram local image rejected; falling back to a text post: "
            f"{local_error}",
            file=sys.stderr,
        )
        return _send_message(token, chat, text)
    except (OSError, ValueError) as local_error:
        print(
            "Telegram local image unavailable; falling back to a text post: "
            f"{local_error}",
            file=sys.stderr,
        )
        return _send_message(token, chat, text)


def production_context(now=None):
    from social_slot_gate import slot_start

    now = now or _dt.datetime.now(_dt.timezone.utc)
    expected = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_EVENT_NAME": "schedule",
        "GITHUB_REPOSITORY": REPOSITORY,
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_WORKFLOW_REF": (
            f"{REPOSITORY}/.github/workflows/telegram-daily.yml@refs/heads/main"
        ),
    }
    if any(os.environ.get(key) != value for key, value in expected.items()):
        raise ValueError("only the production scheduled Telegram owner may publish")
    slot = _timestamp(os.environ.get("TELEGRAM_SLOT"))
    if (
        slot != slot_start(now, SLOT_HOURS)
        or os.environ.get("TELEGRAM_SCHEDULE") != f"0 {slot.hour} * * *"
    ):
        raise ValueError("delayed/wrong Telegram schedule cannot borrow another slot")
    source_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True,
    ).strip()
    if _sha(source_sha) != os.environ.get("GITHUB_SHA"):
        raise ValueError("checkout does not match the scheduled production source")
    subprocess.run(
        ["git", "diff", "--quiet", "HEAD"], cwd=REPO_ROOT, check=True,
    )
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
    if not re.fullmatch(r"[1-9][0-9]*", run_id) or not re.fullmatch(r"[1-9][0-9]*", attempt):
        raise ValueError("missing production workflow identity")
    with INTENT_CATALOG_PATH.open(encoding="utf-8") as source:
        catalog = json.load(source)
    if catalog.get("app_count") != 47 or catalog.get("record_count") != 2350:
        raise ValueError("current publisher catalog is not exact47 × exact50")
    return {
        "source_sha": source_sha, "slot": slot.isoformat(), "now": now,
        "run_id": run_id, "run_attempt": attempt,
        "generation_digest": _sha(catalog.get("generation_digest"), 64),
        "catalog_digest": hashlib.sha256(INTENT_CATALOG_PATH.read_bytes()).hexdigest(),
        "roster_digest": hashlib.sha256(_json_bytes(sorted(EXACT47_APP_IDS))).hexdigest(),
    }


def assert_current_slot(context):
    from social_slot_gate import slot_start

    if _timestamp(context["slot"]) != slot_start(
        _dt.datetime.now(_dt.timezone.utc), SLOT_HOURS
    ):
        raise ValueError("Telegram preflight crossed a slot boundary; no send")


def read_native_chat(token, configured_chat):
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/getChat?"
        + urllib.parse.urlencode({"chat_id": configured_chat}),
    )
    response = request_json(
        request, label="Telegram getChat", timeout=25, attempts=3,
    )
    if not isinstance(response, dict) or not isinstance(response.get("result"), dict):
        raise RequestError("Telegram getChat returned no native chat")
    chat = response.get("result", {})
    if (
        response.get("ok") is not True or chat.get("type") != "channel"
        or type(chat.get("id")) is not int or chat["id"] >= 0
        or str(chat.get("username", "")).lower() != PUBLIC_CHANNEL.lower()
    ):
        raise ValueError("official getChat did not confirm the production channel")
    return chat


def choose_unpublished(pool, ledger, now, slot=None):
    from social_slot_gate import slot_start

    now = now.astimezone(_dt.timezone.utc)
    scheduled = slot_start(now, SLOT_HOURS) if slot is None else _timestamp(slot)
    if scheduled != slot_start(now, SLOT_HOURS):
        raise ValueError("candidate selection must use the current authoritative slot")
    zone = _zone(scheduled.hour)
    channel = f"telegram:{zone}"
    other_channel_apps = {
        str(channel_candidates(pool, other, now)[0]["app"])
        for other in CHANNEL_ORDER if other != channel
    }
    receipts = list(ledger["receipts"].values())
    covered = {receipt["app_store_id"] for receipt in receipts}
    today_apps = {
        receipt["app_store_id"] for receipt in receipts
        if _timestamp(receipt["timestamp"]).date() == now.date()
    }
    unresolved = [
        intent for intent in ledger["intents"].values()
        if intent["status"] in {"reserved", "unknown"}
    ]
    blocked_apps = today_apps | other_channel_apps | {
        intent["app_store_id"] for intent in unresolved
    }
    used = {receipt["payload_digest"] for receipt in receipts} | {
        intent["payload_digest"] for intent in ledger["intents"].values()
        if intent["status"] in {"reserved", "unknown", "confirmed"}
    }
    eligible = [
        item for item in channel_candidates(pool, channel, now)
        if item.get("source") == "publisher_intent_catalog"
        and item.get("lang") in TZ_LANGS[zone]
        and str(item.get("app")) not in blocked_apps
        and _digest(compose_text(item)) not in used
    ]
    # Native gaps get the next eligible existing slot, never additional sends.
    return next(
        (item for item in eligible if str(item["app"]) not in covered),
        eligible[0] if eligible else None,
    )


def make_intent(item, context):
    if item["lang"] not in TZ_LANGS[_zone(_timestamp(context["slot"]).hour)]:
        raise ValueError("Telegram locale does not belong to the authoritative slot")
    text = compose_text(item)
    return {
        "slot": context["slot"], "status": "reserved",
        "app_store_id": str(item["app"]), "official_locale": item["lang"],
        "text": text, "payload_digest": _digest(text),
        "source_sha": context["source_sha"],
        "generation_digest": context["generation_digest"],
        "catalog_digest": context["catalog_digest"],
        "roster_digest": context["roster_digest"],
        "run_id": context["run_id"], "run_attempt": context["run_attempt"],
        "reserved_at": context["now"].isoformat(),
    }


def _receipt(intent, message_id, timestamp, evidence):
    return {
        "channel": PUBLIC_CHANNEL, "message_id": message_id,
        "app_store_id": intent["app_store_id"],
        "official_locale": intent["official_locale"],
        "locale": intent["official_locale"],
        "payload_digest": intent["payload_digest"],
        "payload_digest_kind": "sha256:utf8-caption-or-text",
        "source_sha": intent["source_sha"], "timestamp": timestamp,
        "generation_digest": intent["generation_digest"],
        "catalog_digest": intent["catalog_digest"],
        "roster_digest": intent["roster_digest"],
        "slot": intent["slot"], "evidence": evidence,
    }


def receipt_from_response(intent, response, chat):
    if not isinstance(response, dict) or not isinstance(response.get("result"), dict):
        raise RequestError("Telegram publication returned no native message")
    message = response.get("result", {})
    native_chat = message.get("chat", {})
    if not isinstance(native_chat, dict):
        raise RequestError("Telegram publication returned no native channel")
    message_id = message.get("message_id")
    _delivery_id(message_id)
    if (
        response.get("ok") is not True
        or native_chat.get("id") != chat["id"]
        or type(native_chat.get("id")) is not int
        or native_chat.get("type") != "channel"
        or (
            native_chat.get("username") is not None
            and str(native_chat["username"]).lower() != PUBLIC_CHANNEL.lower()
        )
        or type(message.get("date")) is not int
        or message.get("caption", message.get("text")) != intent["text"]
    ):
        raise RequestError("Telegram production response did not confirm the exact payload/channel")
    timestamp = _dt.datetime.fromtimestamp(message["date"], _dt.timezone.utc)
    if (
        timestamp < _timestamp(intent["reserved_at"]) - _dt.timedelta(seconds=5)
        or timestamp > _dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(seconds=60)
    ):
        raise RequestError("Telegram production response timestamp is not current")
    receipt = _receipt(intent, message_id, timestamp.isoformat(), {
        "kind": "telegram_production_response",
        "production_run_id": intent["run_id"],
        "run_attempt": intent["run_attempt"],
        "response_sha256": hashlib.sha256(_json_bytes(response)).hexdigest(),
        "observed_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
    })
    receipt["channel_id"] = native_chat["id"]
    return receipt


def confirm_intent(ledger, slot, receipt):
    key = _delivery_id(receipt["message_id"])
    previous = ledger["receipts"].get(key)
    if previous and any(
        previous.get(field) != receipt.get(field)
        for field in ("app_store_id", "payload_digest", "timestamp")
    ):
        raise ValueError("native message identity collision; receipt not overwritten")
    ledger["receipts"][key] = receipt
    ledger["intents"][slot]["status"] = "confirmed"
    ledger["intents"][slot]["delivery_id"] = key


def reconcile_pending(ledger, store):
    pending = [
        intent for intent in ledger["intents"].values()
        if intent["status"] in {"reserved", "unknown"}
    ]
    if not pending:
        return
    since = min(_timestamp(intent["reserved_at"]) for intent in pending)
    try:
        messages = read_public_history(since=since - _dt.timedelta(seconds=5))
    except (RequestError, OSError, ValueError):
        print(
            "Telegram official GET unavailable; uncertain App reservations remain blocked",
            file=sys.stderr,
        )
        return
    for intent in pending:
        matches = [
            message for message in messages.values()
            if message.get("app_ids") == [intent["app_store_id"]]
            and message.get("text") == intent["text"]
            and message.get("timestamp")
            and _timestamp(message["timestamp"]) >= (
                _timestamp(intent["reserved_at"]) - _dt.timedelta(seconds=5)
            )
        ]
        if len(matches) != 1:
            continue
        message = matches[0]
        receipt = _receipt(
            intent, message["message_id"], message["timestamp"], {
                **message["evidence"],
                "matched_reserved_run_id": intent["run_id"],
                "locale_source": "exact_reserved_production_payload",
            },
        )
        confirm_intent(ledger, intent["slot"], receipt)
        store.save(ledger)


def publish_once(pool, ledger, store, context, token, chat):
    slot = context["slot"]
    if slot in ledger["intents"]:
        print(f"Telegram slot {slot} already reserved; no resend")
        return
    item = choose_unpublished(pool, ledger, context["now"], slot=slot)
    if item is None:
        print("Telegram no eligible new payload in this slot; no send")
        return
    store.assert_current_source(context["source_sha"])
    intent = make_intent(item, context)
    ledger["intents"][slot] = intent
    store.save(ledger)
    attempted = False
    try:
        store.assert_current_source(context["source_sha"])
        assert_current_slot(context)
        attempted = True
        response = _publish_item(token, chat["id"], intent["text"], item)
        write_run_evidence(
            f"response-{context['run_id']}-{context['run_attempt']}.json",
            {"intent": intent, "production_response": response},
        )
        receipt = receipt_from_response(intent, response, chat)
        confirm_intent(ledger, slot, receipt)
        store.save(ledger)
        print("telegram_native_receipt:", json.dumps(receipt, ensure_ascii=False, sort_keys=True))
        print(
            "posted ok, message_id:", receipt["message_id"],
            "| lang:", receipt["official_locale"], "| app:", receipt["app_store_id"],
        )
    except (RequestError, ValueError, KeyError, TypeError, OSError) as error:
        if intent["status"] != "confirmed":
            # Unknown outcomes never expire into retries. Only official GET may
            # confirm them; other Apps may still use subsequent legal slots.
            rejected = isinstance(error, HTTPStatusError) and error.status in {
                400, 401, 403, 404, 413, 422, 429,
            }
            intent["status"] = (
                ("rejected" if rejected else "unknown") if attempted else "not_sent"
            )
            try:
                store.save(ledger)
            except (RequestError, ValueError, OSError):
                print("Telegram reservation retained; ACK persistence needs GET reconciliation", file=sys.stderr)
        raise


def self_test():
    """Keep regression fixtures in this owner's file, with all network denied."""
    import io
    import unittest
    from unittest import mock
    from social_slot_gate import slot_start

    module = sys.modules[__name__]

    class LedgerTests(unittest.TestCase):
        def setUp(self):
            self.now = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0)
            self.context = {
                "now": self.now, "slot": slot_start(self.now, SLOT_HOURS).isoformat(),
                "source_sha": "1" * 40, "generation_digest": "2" * 64,
                "catalog_digest": "3" * 64, "roster_digest": "4" * 64,
                "run_id": "1001", "run_attempt": "1",
            }
            self.item = {
                "app": "6792483140",
                "lang": TZ_LANGS[_zone(_timestamp(self.context["slot"]).hour)][0],
                "text": "Fixture, not a post",
                "source": "publisher_intent_catalog",
                "url": "https://apps.apple.com/app/id6792483140",
            }
            self.chat = {"id": -1001234567, "type": "channel", "username": PUBLIC_CHANNEL}
            self.messages = {
                mid: {
                    "message_id": mid, "app_ids": [app],
                    "text": f"Fixture {mid} https://apps.apple.com/app/id{app}",
                    "timestamp": "2026-07-16T01:00:00+00:00",
                    "evidence": {
                        "kind": "telegram_official_get",
                        "url": f"https://t.me/s/{PUBLIC_CHANNEL}?before={mid + 1}",
                        "response_sha256": "5" * 64,
                        "observed_at": self.now.isoformat(),
                    },
                }
                for mid, app in LEGACY_IDENTITIES.items()
            }
            self.ledger = bootstrap_ledger(
                self.messages, self.context["source_sha"], lambda _run: "6" * 40,
            )
            self.intent = make_intent(self.item, self.context)
            self.response = {"ok": True, "result": {
                "message_id": 900001, "chat": self.chat,
                "date": int(self.now.timestamp()), "text": self.intent["text"],
            }}
            self.store = mock.Mock(spec=GitHubLedger)
            self.saves = []
            self.store.save.side_effect = lambda ledger: self.saves.append(copy.deepcopy(ledger))

        def publish(self):
            with (
                mock.patch.object(module, "choose_unpublished", return_value=self.item),
                mock.patch.object(module, "_publish_item", return_value=self.response) as send,
                mock.patch.object(module, "write_run_evidence"),
            ):
                publish_once([], self.ledger, self.store, self.context, "fixture-token", self.chat)
            return send

        def pool(self):
            return [
                {
                    "app": app, "lang": locale,
                    "text": f"Fixture {app} {locale}",
                    "url": f"https://apps.apple.com/app/id{app}",
                    "source": "publisher_intent_catalog",
                }
                for app in sorted(EXACT47_APP_IDS) for locale in OFFICIAL_SOCIAL_LOCALES
            ]

        def test_frozen_175_native_ids_44_apps_and_35_proven_locales(self):
            self.assertEqual((175, 44, 47), (
                len(LEGACY_IDENTITIES), len(LEGACY_APP_MESSAGES), len(EXACT47_APP_IDS),
            ))
            self.assertEqual(175, len(self.ledger["receipts"]))
            self.assertEqual(35, sum(
                row["official_locale"] is not None
                for row in self.ledger["receipts"].values()
            ))
            self.assertEqual({"6792483140", "6802166527", "6806776579"}, EXACT47_APP_IDS - {
                row["app_store_id"] for row in self.ledger["receipts"].values()
            })

        def test_bootstrap_requires_every_protected_native_identity(self):
            for change in ("missing", "wrong_app", "no_text"):
                with self.subTest(change=change):
                    messages = copy.deepcopy(self.messages)
                    mid = min(messages)
                    if change == "missing":
                        del messages[mid]
                    elif change == "wrong_app":
                        messages[mid]["app_ids"] = ["6806776579"]
                    else:
                        messages[mid]["text"] = ""
                    with self.assertRaises(ValueError):
                        bootstrap_ledger(messages, "1" * 40, lambda _run: None)

        def test_html_never_infers_locale_from_ui_or_storefront(self):
            mid = min(LEGACY_IDENTITIES)
            app = LEGACY_IDENTITIES[mid]
            for storefront in ("us", "tw", "in"):
                parser = PublicMessages()
                parser.feed(
                    f'<html lang="ja"><div lang="de" data-post="{PUBLIC_CHANNEL}/{mid}">'
                    '<div class="tgme_widget_message_text js-message_text">Fixture<br/>'
                    f'<a href="https://apps.apple.com/{storefront}/app/id{app}?ct=shared">'
                    'App Store</a></div><time datetime="2026-07-16T01:00:00Z"></time></div></html>'
                )
                self.assertEqual([app], parser.messages[0]["app_ids"])
                self.assertNotIn("official_locale", parser.messages[0])
                self.assertEqual("Fixture\nApp Store", parser.messages[0]["text"])
                parser = PublicMessages()
                parser.feed('<div data-post="OtherChannel/17"><div class="tgme_widget_message_text">No</div></div>')
                self.assertEqual([], parser.messages)

        def test_official_get_paginates_without_mutation(self):
            def html(mid):
                return (
                    f'<div data-post="{PUBLIC_CHANNEL}/{mid}">'
                    '<div class="tgme_widget_message_text">Fixture</div>'
                    '<time datetime="2026-07-16T01:00:00Z"></time></div>'
                ).encode()

            def opener(request, timeout):
                self.assertEqual("GET", request.get_method())
                raw = html(26 if "before=" not in request.full_url else 17)
                response = mock.MagicMock()
                response.__enter__.return_value = response
                response.read.return_value = raw
                response.geturl.return_value = request.full_url
                return response

            with mock.patch.object(urllib.request, "urlopen", side_effect=opener) as get:
                messages = read_public_history({17, 26})
            self.assertEqual({17, 26}, set(messages))
            self.assertEqual(2, get.call_count)
            self.assertEqual("telegram_official_get", messages[17]["evidence"]["kind"])

        def test_lost_protected_receipt_and_lost_confirmed_receipt_fail_closed(self):
            del self.ledger["receipts"][_delivery_id(min(LEGACY_IDENTITIES))]
            with self.assertRaises(ValueError):
                validate_ledger(self.ledger)
            self.setUp()
            self.publish()
            del self.ledger["receipts"][_delivery_id(900001)]
            with self.assertRaises(ValueError):
                validate_ledger(self.ledger)

        def test_invalid_native_or_locale_evidence_fails_closed(self):
            for field, value in (
                ("message_id", True), ("official_locale", "en"),
                ("payload_digest", "not-a-digest"), ("timestamp", "2026-07-01"),
                ("source_sha", "***"), ("evidence", {"kind": "workflow_success"}),
            ):
                with self.subTest(field=field):
                    ledger = copy.deepcopy(self.ledger)
                    next(iter(ledger["receipts"].values()))[field] = value
                    with self.assertRaises(ValueError):
                        validate_ledger(ledger)

        def test_only_production_schedule_and_current_checkout_are_authorized(self):
            slot = _timestamp(self.context["slot"])
            env = {
                "GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "schedule",
                "GITHUB_REPOSITORY": REPOSITORY, "GITHUB_REF": "refs/heads/main",
                "GITHUB_WORKFLOW_REF": f"{REPOSITORY}/.github/workflows/telegram-daily.yml@refs/heads/main",
                "GITHUB_SHA": "1" * 40, "GITHUB_RUN_ID": "1001", "GITHUB_RUN_ATTEMPT": "1",
                "TELEGRAM_SLOT": slot.isoformat(), "TELEGRAM_SCHEDULE": f"0 {slot.hour} * * *",
            }
            with (
                mock.patch.dict(os.environ, env, clear=True),
                mock.patch.object(subprocess, "check_output", return_value="1" * 40),
                mock.patch.object(subprocess, "run"),
            ):
                self.assertEqual("1" * 40, production_context(self.now)["source_sha"])
                for key, value in (
                    ("GITHUB_EVENT_NAME", "workflow_dispatch"),
                    ("GITHUB_REF", "refs/heads/feature/test"),
                    ("GITHUB_SHA", "9" * 40),
                    ("TELEGRAM_SCHEDULE", "0 23 * * *"),
                    ("GITHUB_RUN_ATTEMPT", "0"),
                ):
                    with self.subTest(key=key), mock.patch.dict(os.environ, {key: value}):
                        with self.assertRaises(ValueError):
                            production_context(self.now)

        def test_official_chat_read_never_uses_masked_secret_as_identity(self):
            for result in (
                {"id": "***", "type": "channel", "username": PUBLIC_CHANNEL},
                {"id": -1001, "type": "channel", "username": "WrongChannel"},
            ):
                with mock.patch.object(module, "request_json", return_value={"ok": True, "result": result}):
                    with self.assertRaises(ValueError):
                        read_native_chat("fixture-token", "***")
            with mock.patch.object(module, "request_json", return_value={"ok": True, "result": self.chat}) as request:
                self.assertEqual(self.chat, read_native_chat("fixture-token", "@LumiApps2026"))
            self.assertEqual("GET", request.call_args.args[0].get_method())

        def test_success_has_all_native_fields_and_durable_reservation_first(self):
            send = self.publish()
            self.assertEqual(1, send.call_count)
            self.assertEqual("reserved", self.saves[0]["intents"][self.context["slot"]]["status"])
            receipt = self.saves[-1]["receipts"][_delivery_id(900001)]
            for field in (
                "channel", "message_id", "app_store_id", "official_locale",
                "payload_digest", "source_sha", "timestamp",
                "generation_digest", "catalog_digest", "roster_digest",
            ):
                self.assertTrue(receipt[field])
            self.assertEqual("1" * 40, receipt["source_sha"])
            self.assertEqual(_digest(self.intent["text"]), receipt["payload_digest"])
            validate_ledger(self.ledger)

        def test_same_slot_cannot_resend_a_confirmed_message(self):
            self.publish()
            send = self.publish()
            send.assert_not_called()
            self.assertEqual(176, len(self.ledger["receipts"]))

        def test_reservation_persistence_failure_prevents_send(self):
            self.store.save.side_effect = RequestError("CAS unavailable")
            with (
                mock.patch.object(module, "choose_unpublished", return_value=self.item),
                mock.patch.object(module, "_publish_item") as send,
            ):
                with self.assertRaises(RequestError):
                    publish_once([], self.ledger, self.store, self.context, "fixture", self.chat)
                send.assert_not_called()
            self.assertEqual(175, len(self.ledger["receipts"]))

        def test_source_drift_after_reservation_is_not_a_send(self):
            self.store.assert_current_source.side_effect = [None, ValueError("source drift")]
            with self.assertRaisesRegex(ValueError, "source drift"):
                self.publish()
            self.assertEqual("not_sent", self.ledger["intents"][self.context["slot"]]["status"])

        def test_slot_boundary_after_preflight_does_not_send_late(self):
            with mock.patch.object(module, "assert_current_slot", side_effect=ValueError("slot drift")):
                with self.assertRaisesRegex(ValueError, "slot drift"):
                    self.publish()
            self.assertEqual("not_sent", self.ledger["intents"][self.context["slot"]]["status"])
            with self.assertRaisesRegex(ValueError, "slot boundary"):
                assert_current_slot({**self.context, "slot": "2026-01-01T01:00:00+00:00"})

        def test_ambiguous_transport_is_one_attempt_and_never_replayed(self):
            with (
                mock.patch.object(module, "choose_unpublished", return_value=self.item),
                mock.patch.object(module, "_publish_item", side_effect=RequestError("response lost")) as send,
                mock.patch.object(module, "write_run_evidence"),
            ):
                with self.assertRaises(RequestError):
                    publish_once([], self.ledger, self.store, self.context, "fixture", self.chat)
                publish_once([], self.ledger, self.store, self.context, "fixture", self.chat)
            self.assertEqual(1, send.call_count)
            self.assertEqual("unknown", self.ledger["intents"][self.context["slot"]]["status"])
            self.assertEqual(175, len(self.ledger["receipts"]))

        def test_definite_rate_limit_consumes_slot_but_not_future_payload(self):
            with (
                mock.patch.object(module, "choose_unpublished", return_value=self.item),
                mock.patch.object(module, "_publish_item", side_effect=HTTPStatusError("Telegram", 429)) as send,
                mock.patch.object(module, "write_run_evidence"),
            ):
                with self.assertRaises(HTTPStatusError):
                    publish_once([], self.ledger, self.store, self.context, "fixture", self.chat)
                publish_once([], self.ledger, self.store, self.context, "fixture", self.chat)
            self.assertEqual(1, send.call_count)
            self.assertEqual("rejected", self.ledger["intents"][self.context["slot"]]["status"])

        def test_ack_commit_failure_keeps_original_reservation_and_response_artifact(self):
            self.store.save.side_effect = [None, RequestError("ack commit unavailable")]
            with (
                mock.patch.object(module, "choose_unpublished", return_value=self.item),
                mock.patch.object(module, "_publish_item", return_value=self.response) as send,
                mock.patch.object(module, "write_run_evidence") as evidence,
            ):
                with self.assertRaises(RequestError):
                    publish_once([], self.ledger, self.store, self.context, "fixture", self.chat)
            self.assertEqual(1, send.call_count)
            self.assertEqual(self.response, evidence.call_args.args[1]["production_response"])
            self.assertEqual("confirmed", self.ledger["intents"][self.context["slot"]]["status"])

        def test_ack_must_match_native_id_chat_text_and_date(self):
            for field, value in (
                ("message_id", True), ("message_id", None),
                ("chat", {"id": "***", "type": "channel"}),
                ("text", "Different payload"), ("date", 1),
            ):
                with self.subTest(field=field, value=value):
                    response = copy.deepcopy(self.response)
                    response["result"][field] = value
                    with self.assertRaises((ValueError, RequestError)):
                        receipt_from_response(self.intent, response, self.chat)
            for response in ([], {"ok": True}, {"ok": False, "result": self.response["result"]}):
                with self.assertRaises(RequestError):
                    receipt_from_response(self.intent, response, self.chat)

        def test_all_telegram_mutations_disable_blind_retries(self):
            with mock.patch.object(module, "request_json", return_value=self.response) as request:
                _send_message("fixture", "fixture", "Fixture")
                self.assertEqual(1, request.call_args.kwargs["attempts"])
                _send_photo("fixture", "fixture", "Fixture", f"{SITE_URL}/social/img/aim990-share.jpg")
                self.assertEqual(1, request.call_args.kwargs["attempts"])
                with (
                    mock.patch.object(Path, "is_file", return_value=True),
                    mock.patch.object(Path, "stat", return_value=mock.Mock(st_size=1)),
                    mock.patch.object(module, "_multipart_photo_body", return_value=b"fixture"),
                ):
                    _send_photo_file("fixture", "fixture", "Fixture", Path("fixture.jpg"))
                self.assertEqual(1, request.call_args.kwargs["attempts"])

        def test_uncertain_5xx_or_429_must_not_fallback_into_a_second_send(self):
            for status in (429, 500, 502, 503, 504):
                with (
                    self.subTest(status=status),
                    mock.patch.object(module, "_send_photo", side_effect=HTTPStatusError("Telegram", status)),
                    mock.patch.object(module, "_send_photo_file") as local,
                    mock.patch.object(module, "_send_message") as text,
                ):
                    with self.assertRaises(HTTPStatusError):
                        _publish_item("fixture", "fixture", "Fixture", {
                            "image_url": f"{SITE_URL}/social/img/aim990-share.jpg",
                        })
                    local.assert_not_called()
                    text.assert_not_called()

        def test_official_get_closes_unknown_without_sending_again(self):
            self.ledger["intents"][self.context["slot"]] = self.intent
            message = {
                "message_id": 900002, "app_ids": [self.intent["app_store_id"]],
                "text": self.intent["text"], "timestamp": self.now.isoformat(),
                "evidence": copy.deepcopy(next(iter(self.messages.values()))["evidence"]),
            }
            with (
                mock.patch.object(module, "read_public_history", return_value={900002: message}),
                mock.patch.object(module, "_publish_item") as send,
            ):
                reconcile_pending(self.ledger, self.store)
                reconcile_pending(self.ledger, self.store)
            send.assert_not_called()
            self.assertEqual(1, self.store.save.call_count)
            receipt = self.ledger["receipts"][_delivery_id(900002)]
            self.assertEqual(self.intent["official_locale"], receipt["official_locale"])
            self.assertEqual("1" * 40, receipt["source_sha"])
            validate_ledger(self.ledger)

        def test_missing_or_ambiguous_readback_does_not_release_reservation(self):
            self.ledger["intents"][self.context["slot"]] = self.intent
            for count in (0, 2):
                messages = {
                    900002 + n: {
                        "message_id": 900002 + n, "app_ids": [self.intent["app_store_id"]],
                        "text": self.intent["text"], "timestamp": self.now.isoformat(),
                    }
                    for n in range(count)
                }
                with mock.patch.object(module, "read_public_history", return_value=messages):
                    reconcile_pending(self.ledger, self.store)
                self.assertEqual("reserved", self.intent["status"])
            self.store.save.assert_not_called()

        def test_unavailable_readback_keeps_unknown_app_blocked_not_the_whole_channel(self):
            self.ledger["intents"][self.context["slot"]] = self.intent
            with mock.patch.object(module, "read_public_history", side_effect=RequestError("offline")):
                reconcile_pending(self.ledger, self.store)
            self.assertEqual("reserved", self.intent["status"])
            self.store.save.assert_not_called()
            item = choose_unpublished(self.pool(), self.ledger, self.now)
            self.assertNotEqual(self.intent["app_store_id"], item["app"])

        def test_native_gaps_use_only_current_region_and_safe_daily_channel_choices(self):
            pool = self.pool()
            for hour in SLOT_HOURS:
                now = self.now.replace(hour=hour)
                channel = f"telegram:{_zone(hour)}"
                other = {
                    str(channel_candidates(pool, name, now)[0]["app"])
                    for name in CHANNEL_ORDER if name != channel
                }
                item = choose_unpublished(pool, self.ledger, now)
                self.assertIn(item["lang"], TZ_LANGS[_zone(hour)])
                self.assertNotIn(item["app"], other)
                gaps = EXACT47_APP_IDS - set(LEGACY_APP_MESSAGES) - other
                if gaps:
                    self.assertIn(item["app"], gaps)

        def test_delayed_runs_keep_authoritative_slot_region_and_channel_plan(self):
            pool = self.pool()
            for hour, zone in ((6, "asia"), (14, "eu_me"), (22, "americas"), (0, "americas")):
                now = self.now.replace(hour=hour, minute=30)
                slot = slot_start(now, SLOT_HOURS).isoformat()
                with mock.patch.object(module, "channel_candidates", wraps=channel_candidates) as selector:
                    item = choose_unpublished(pool, self.ledger, now, slot=slot)
                self.assertIn(item["lang"], TZ_LANGS[zone])
                self.assertEqual(f"telegram:{zone}", selector.call_args.args[1])
            with self.assertRaises(ValueError):
                choose_unpublished(pool, self.ledger, self.now, slot="2026-01-01T01:00:00+00:00")

        def test_reservation_rejects_official_locale_from_another_slot_region(self):
            wrong = next(
                locale for locale in OFFICIAL_SOCIAL_LOCALES
                if locale not in TZ_LANGS[_zone(_timestamp(self.context["slot"]).hour)]
            )
            with self.assertRaisesRegex(ValueError, "authoritative slot"):
                make_intent({**self.item, "lang": wrong}, self.context)
            self.ledger["intents"][self.context["slot"]] = self.intent
            self.intent["official_locale"] = wrong
            with self.assertRaises(ValueError):
                validate_ledger(self.ledger)

        def test_confirmed_payload_and_unknown_app_are_excluded_even_after_source_change(self):
            pool = self.pool()
            item = choose_unpublished(pool, self.ledger, self.now)
            intent = make_intent(item, self.context)
            self.ledger["intents"][self.context["slot"]] = intent
            next_item = choose_unpublished(pool, self.ledger, self.now)
            self.assertNotEqual(item["app"], next_item["app"])
            intent["status"] = "confirmed"
            receipt = _receipt(intent, 900003, "2026-07-17T01:00:00+00:00",
                               next(iter(self.messages.values()))["evidence"])
            confirm_intent(self.ledger, self.context["slot"], receipt)
            item["source_sha"] = "9" * 40
            selected = choose_unpublished(pool, self.ledger, self.now)
            self.assertNotEqual(_digest(compose_text(item)), _digest(compose_text(selected)))

        def test_cas_load_validates_blob_and_preserves_all_receipts(self):
            raw = _json_bytes(self.ledger)
            sha = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
            store = GitHubLedger("fixture")
            store.api = mock.Mock(return_value={
                "sha": sha, "encoding": "base64", "content": base64.b64encode(raw).decode(),
            })
            self.assertEqual(self.ledger, store.load())
            self.assertEqual(sha, store.blob_sha)
            store.api.return_value["sha"] = "f" * 40
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                store.load()

        def test_large_ledger_reads_git_blob_without_truncating_history(self):
            raw = _json_bytes(self.ledger)
            sha = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
            store = GitHubLedger("fixture")
            store.api = mock.Mock(side_effect=[
                {"sha": sha, "encoding": "none", "content": ""},
                {"sha": sha, "encoding": "base64", "content": base64.b64encode(raw).decode()},
            ])
            self.assertEqual(self.ledger, store.load())
            self.assertEqual(f"git/blobs/{sha}", store.api.call_args.args[0])

        def test_missing_existing_state_never_reinitializes_history(self):
            store = GitHubLedger("fixture")
            store.api = mock.Mock(side_effect=[
                HTTPStatusError("GitHub", 404), {"object": {"sha": "1" * 40}},
            ])
            with self.assertRaisesRegex(ValueError, "lost its state"):
                store.load()
            store.api.side_effect = [HTTPStatusError("GitHub", 404), HTTPStatusError("GitHub", 404)]
            self.assertIsNone(store.load())

        def test_bootstrap_is_atomic_orphan_data_branch_not_main_mutation(self):
            raw = _json_bytes(self.ledger)
            sha = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
            store = GitHubLedger("fixture")
            store.api = mock.Mock(side_effect=[
                {"sha": sha}, {"sha": "b" * 40}, {"sha": "c" * 40},
                {}, {"sha": sha},
            ])
            with mock.patch.object(module, "write_run_evidence"):
                store.save(self.ledger)
            calls = store.api.call_args_list
            self.assertEqual([], calls[2].args[2]["parents"])
            self.assertEqual(f"refs/heads/{LEDGER_BRANCH}", calls[3].args[2]["ref"])
            self.assertEqual(sha, store.blob_sha)

        def test_lost_cas_response_is_get_reconciled_without_repeating_put(self):
            raw = _json_bytes(self.ledger)
            sha = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
            store = GitHubLedger("fixture")
            store.blob_sha = "a" * 40
            store.api = mock.Mock(side_effect=[
                RequestError("response lost"), {"sha": sha}, {"sha": sha},
            ])
            with mock.patch.object(module, "write_run_evidence"):
                store.save(self.ledger)
            calls = store.api.call_args_list
            self.assertEqual("PUT", calls[0].args[1])
            self.assertEqual(LEDGER_BRANCH, calls[0].args[2]["branch"])
            self.assertEqual("a" * 40, calls[0].args[2]["sha"])
            self.assertTrue(all(len(call.args) == 1 for call in calls[1:]))

        def test_cas_conflict_cannot_overwrite_a_different_ledger(self):
            store = GitHubLedger("fixture")
            store.blob_sha = "a" * 40
            store.api = mock.Mock(side_effect=[
                HTTPStatusError("GitHub", 409), {"sha": "b" * 40},
            ])
            with mock.patch.object(module, "write_run_evidence"):
                with self.assertRaisesRegex(RequestError, "CAS not confirmed"):
                    store.save(self.ledger)
            self.assertEqual(2, store.api.call_count)
            self.assertEqual("a" * 40, store.blob_sha)

        def test_artifact_snapshot_is_atomic_and_private_inside_project(self):
            directory = Path(".tel-test-work") / f"ledger-fixture-{secrets.token_hex(8)}"
            directory.mkdir(parents=True)
            try:
                with mock.patch.object(module, "RUN_EVIDENCE", directory):
                    write_run_evidence("fixture.json", self.ledger)
                self.assertEqual(self.ledger, json.loads((directory / "fixture.json").read_text()))
                self.assertEqual(0o600, (directory / "fixture.json").stat().st_mode & 0o777)
                self.assertFalse((directory / "fixture.json.writing").exists())
            finally:
                for path in directory.iterdir():
                    path.unlink()
                directory.rmdir()

        def test_nonproduction_main_cannot_send_even_with_credentials(self):
            with (
                mock.patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "fixture-token", "TELEGRAM_CHAT_ID": "***"}, clear=True),
                mock.patch.object(module, "_publish_item") as send,
            ):
                self.assertEqual(1, main([]))
            send.assert_not_called()

    with (
        mock.patch.object(urllib.request, "urlopen", side_effect=AssertionError("self-test forbids network")),
        mock.patch("sys.stdout", new_callable=io.StringIO),
    ):
        result = unittest.TextTestRunner(verbosity=1, buffer=True).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(LedgerTests)
        )
    return 0 if result.wasSuccessful() else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="fixtures/mock only; never publish")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not tok or not chat:
        print("missing TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID", file=sys.stderr)
        return 1
    try:
        context = production_context()
        pool = load_pool()
        store = GitHubLedger(os.environ.get("GITHUB_TOKEN", ""))
        store.assert_current_source(context["source_sha"])
        native_chat = read_native_chat(tok, chat)
        ledger = store.load()
        if ledger is None:
            ledger = bootstrap_ledger(
                read_public_history(LEGACY_IDENTITIES),
                context["source_sha"], store.historical_source,
            )
            store.save(ledger)
        reconcile_pending(ledger, store)
        gaps = sorted(EXACT47_APP_IDS - {
            receipt["app_store_id"] for receipt in ledger["receipts"].values()
        })
        print(f"Telegram native coverage {47 - len(gaps)}/47; gaps={','.join(gaps)}")
        publish_once(pool, ledger, store, context, tok, native_chat)
        return 0
    except (
        RequestError, ValueError, KeyError, TypeError, OSError,
        subprocess.CalledProcessError,
    ) as error:
        detail = str(error)
        for secret in (tok, chat, os.environ.get("GITHUB_TOKEN", "")):
            if secret:
                detail = detail.replace(secret, "[redacted]")
        print(f"Telegram post blocked/failed: {detail}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
