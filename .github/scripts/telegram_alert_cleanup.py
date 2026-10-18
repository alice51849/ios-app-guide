#!/usr/bin/env python3
"""Delete the internal watchdog alerts that leaked into the public promo channel, and nothing else.

Until 2026-10-18 the line watchdog posted internal alerts with this repository's
``TELEGRAM_CHAT_ID``, which is the public promo channel t.me/LumiApps2026
(``line_watchdog.py --telegram`` from 2026-09-07, then ``line_alert.py``).
00_GrowthEngine reports/ops/telegram_alert_cleanup_2026-10-18.json lists those
posts by message id; a byte-identical copy lives in .github/growth/ and was
reviewed post by post by a second, different model before this ran.

Safety, in order:

1. the list must be the reviewed file: ``--confirm`` must equal its sha256;
2. every listed item must carry an internal-alert template in its recorded text;
3. right before deleting, the post's live public text is read again
   (t.me/<channel>/<id>?embed=1) and must still start with an internal-alert
   template; a post that reads as anything else is refused, never deleted;
4. only ``deleteMessage`` on the listed ids is called, one id at a time, and
   each deletion is read back on the public preview ("Post not found").

Ids the Bot API refuses (e.g. its 48-hour deletion window) are reported with
Telegram's error description. The token and chat id come only from the
environment and are never printed.

``--mode edit`` is for the posts the Bot API can no longer delete (older than
48 hours): the same list, digest and live-text checks apply, and each such post
gets ``editMessageText`` with the fixed neutral text ``（此訊息已移除）`` (never
promo copy, so the channel does not suddenly show dozens of ads). The text is
a constant of this module, not an input; a post that already reads neutral is
skipped; each edit is confirmed by the API's returned text and read back on the
public preview.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable

CHANNEL = "LumiApps2026"
SCHEMA = "telegram-alert-cleanup/v1"
TEMPLATES = (
    ("line_alert.py:new_red", re.compile(r"^🔴 外宣線變紅（[^）]+）：新增 \d+ 條")),
    ("line_alert.py:recovered", re.compile(r"^🟢 外宣線全部恢復新鮮（[^）]+）")),
    ("line_watchdog.py:telegram_alert", re.compile(r"^line-health 🔴 \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ\n- ")),
)
# text_60 is cut at 60 characters, so the old template's "\n- " may be all that is left after the stamp.
TEMPLATES_60 = TEMPLATES[:2] + (
    ("line_watchdog.py:telegram_alert", re.compile(r"^line-health 🔴 \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ(\n|$)")),
)
NOT_FOUND = "Post not found"
# The only text --mode edit ever writes. Neutral on purpose: not promo copy.
NEUTRAL_TEXT = "（此訊息已移除）"


def template_of(text: str, templates=TEMPLATES) -> str | None:
    for name, pattern in templates:
        if pattern.search(text or ""):
            return name
    return None


class _MessageText(HTMLParser):
    """Text of the first tgme_widget_message_text block, and whether the post is missing."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text = ""
        self.found = False
        self.missing = False
        self._depth = 0
        self._in_error = False

    def handle_starttag(self, tag, attrs):
        classes = (dict(attrs).get("class") or "").split()
        if tag == "div" and "tgme_widget_message_error" in classes:
            self._in_error = True
        if self._depth:
            if tag == "div":
                self._depth += 1
            elif tag == "br":
                self.text += "\n"
            return
        if tag == "div" and "tgme_widget_message_text" in classes and not self.found:
            self.found = True
            self._depth = 1

    def handle_startendtag(self, tag, attrs):
        if self._depth and tag == "br":
            self.text += "\n"

    def handle_endtag(self, tag):
        if self._depth and tag == "div":
            self._depth -= 1
        if self._in_error and tag == "div":
            self._in_error = False

    def handle_data(self, data):
        if self._depth:
            self.text += data
        if self._in_error and NOT_FOUND in data:
            self.missing = True


def parse_preview(html: str) -> dict:
    parser = _MessageText()
    parser.feed(html)
    if parser.found:
        return {"state": "present", "text": parser.text}
    if parser.missing:
        return {"state": "missing", "text": ""}
    return {"state": "unreadable", "text": ""}


def fetch_preview(message_id: int, *, attempts: int = 3) -> dict:
    url = f"https://t.me/{CHANNEL}/{message_id}?embed=1&mode=tme"
    last = "unreadable"
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "telegram-alert-cleanup",
                                                           "Cache-Control": "no-cache"})
            with urllib.request.urlopen(request, timeout=20) as response:
                return parse_preview(response.read(1_000_000).decode("utf-8", "replace"))
        except (OSError, urllib.error.URLError) as error:
            last = type(error).__name__
            time.sleep(1 + attempt)
    return {"state": "unreadable", "text": "", "error": last}


def delete_message(token: str, chat_id: str, message_id: int) -> tuple[bool, str]:
    body = urllib.parse.urlencode({"chat_id": chat_id, "message_id": message_id}).encode()
    request = urllib.request.Request(f"https://api.telegram.org/bot{token}/deleteMessage", data=body)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        try:
            payload = json.loads(error.read().decode("utf-8", "replace"))
        except ValueError:
            payload = {"ok": False, "description": f"HTTP {error.code}"}
    except OSError as error:
        return False, type(error).__name__
    if payload.get("ok") and payload.get("result") is True:
        return True, "ok"
    return False, str(payload.get("description") or "rejected")[:200]


def edit_message(token: str, chat_id: str, message_id: int, *, attempts: int = 4,
                 sleep: Callable[[float], None] = time.sleep) -> tuple[bool, str]:
    """Replace one post's text with NEUTRAL_TEXT; (ok, detail). Waits out 429 flood control."""
    body = urllib.parse.urlencode({"chat_id": chat_id, "message_id": message_id, "text": NEUTRAL_TEXT,
                                   "disable_web_page_preview": "true"}).encode()
    detail = "rejected"
    for _ in range(attempts):
        request = urllib.request.Request(f"https://api.telegram.org/bot{token}/editMessageText", data=body)
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.load(response)
        except urllib.error.HTTPError as error:
            try:
                payload = json.loads(error.read().decode("utf-8", "replace"))
            except ValueError:
                payload = {"ok": False, "description": f"HTTP {error.code}"}
        except OSError as error:
            return False, type(error).__name__
        if payload.get("ok"):
            text = (payload.get("result") or {}).get("text") if isinstance(payload.get("result"), dict) else None
            return (True, "ok") if text == NEUTRAL_TEXT else (False, "edited text not confirmed")
        detail = str(payload.get("description") or "rejected")[:200]
        if "message is not modified" in detail:
            return True, "not_modified"
        retry_after = (payload.get("parameters") or {}).get("retry_after")
        if payload.get("error_code") == 429 and isinstance(retry_after, (int, float)) and retry_after <= 120:
            sleep(float(retry_after) + 1)
            continue
        return False, detail
    return False, detail


def load_list(path: Path, confirm: str) -> dict:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if confirm.strip().lower() != digest:
        raise SystemExit(f"refused: --confirm does not match the reviewed list (sha256 {digest})")
    doc = json.loads(raw.decode("utf-8"))
    if doc.get("schema") != SCHEMA:
        raise SystemExit("refused: unexpected list schema")
    items = doc.get("items")
    if not isinstance(items, list) or not items:
        raise SystemExit("refused: the list has no items")
    ids = [item.get("id") for item in items]
    if any(not isinstance(i, int) or isinstance(i, bool) or i <= 0 for i in ids):
        raise SystemExit("refused: every id must be a positive integer")
    if len(set(ids)) != len(ids) or ids != doc.get("ids") or doc.get("count") != len(ids):
        raise SystemExit("refused: ids / count / items disagree")
    for item in items:
        if template_of(str(item.get("text_60") or ""), TEMPLATES_60) is None:
            raise SystemExit(f"refused: listed id {item['id']} does not carry an internal-alert template")
    return doc


def _is_neutral(text: str) -> bool:
    return (text or "").strip() == NEUTRAL_TEXT


def run(doc: dict, *, token: str, chat_id: str, apply: bool,
        preview: Callable[[int], dict] | None = None,
        delete: Callable[[str, str, int], tuple[bool, str]] | None = None,
        settle: float = 2.0, edit: bool = False,
        edit_fn: Callable[[str, str, int], tuple[bool, str]] | None = None,
        pace: float = 1.5, readback_rounds: int = 4) -> dict:
    preview = preview or fetch_preview  # looked up at call time so tests can never reach the network
    delete = delete or delete_message
    edit_fn = edit_fn or edit_message
    if edit:
        return _run_edit(doc, token=token, chat_id=chat_id, preview=preview, edit_fn=edit_fn,
                         settle=settle, pace=pace, readback_rounds=readback_rounds)
    results = []
    for item in doc["items"]:
        message_id = item["id"]
        before = preview(message_id)
        row = {"id": message_id, "before": before["state"]}
        if before["state"] == "missing":
            row["result"] = "already_gone"
        elif before["state"] != "present":
            row["result"] = "refused_unreadable"
        elif template_of(before["text"]) is None:
            row["result"] = "refused_not_alert"
        elif not apply:
            row["result"] = "would_delete"
        else:
            ok, detail = delete(token, chat_id, message_id)
            row["result"] = "deleted" if ok else "delete_failed"
            row["detail"] = detail
        results.append(row)
    if apply and any(row["result"] == "deleted" for row in results):
        time.sleep(settle)
        for row in results:
            if row["result"] == "deleted":
                after = preview(row["id"])
                row["after"] = after["state"]
                if after["state"] == "present" and template_of(after["text"]) is not None:
                    row["result"] = "deleted_but_still_public"
    counts: dict[str, int] = {}
    for row in results:
        counts[row["result"]] = counts.get(row["result"], 0) + 1
    return {"listed": len(results), "counts": counts, "results": results}


def _run_edit(doc: dict, *, token: str, chat_id: str, preview: Callable[[int], dict],
              edit_fn: Callable[[str, str, int], tuple[bool, str]], settle: float, pace: float,
              readback_rounds: int) -> dict:
    """editMessageText(NEUTRAL_TEXT) on listed posts whose live text is still an internal alert."""
    results = []
    for item in doc["items"]:
        message_id = item["id"]
        before = preview(message_id)
        row = {"id": message_id, "before": before["state"]}
        if before["state"] == "missing":
            row["result"] = "already_gone"
        elif before["state"] != "present":
            row["result"] = "refused_unreadable"
        elif _is_neutral(before["text"]):
            row["result"] = "already_neutral"
        elif template_of(before["text"]) is None:
            row["result"] = "refused_not_alert"
        else:
            ok, detail = edit_fn(token, chat_id, message_id)
            row["result"] = "edited" if ok else "edit_failed"
            row["detail"] = detail
            if pace:
                time.sleep(pace)
        results.append(row)
    pending = [row for row in results if row["result"] == "edited"]
    for round_index in range(max(1, readback_rounds)):
        if not pending:
            break
        if settle:
            time.sleep(settle * (round_index + 1))
        still = []
        for row in pending:
            after = preview(row["id"])
            row["after"] = "neutral" if after["state"] == "present" and _is_neutral(after["text"]) else after["state"]
            if row["after"] != "neutral":
                still.append(row)
        pending = still
    for row in pending:
        row["result"] = "edited_but_not_read_back"
    counts: dict[str, int] = {}
    for row in results:
        counts[row["result"]] = counts.get(row["result"], 0) + 1
    return {"listed": len(results), "counts": counts, "results": results, "neutral_text": NEUTRAL_TEXT}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", type=Path, required=True)
    parser.add_argument("--confirm", required=True, help="sha256 of the reviewed list file")
    parser.add_argument("--mode", choices=("plan", "apply", "edit"), default="plan",
                        help="plan: read only; apply: deleteMessage; edit: editMessageText to the neutral text")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    doc = load_list(args.list, args.confirm)
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if args.mode in ("apply", "edit") and (not token or not chat_id):
        print("::error::TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID are not set; nothing was changed")
        return 1
    outcome = run(doc, token=token, chat_id=chat_id, apply=args.mode == "apply", edit=args.mode == "edit",
                  settle=5.0 if args.mode == "edit" else 2.0)
    for row in outcome["results"]:
        extra = f" ({row['detail']})" if row.get("detail") and row["detail"] != "ok" else ""
        after = f" after={row['after']}" if "after" in row else ""
        print(f"id {row['id']}: {row['result']} before={row['before']}{after}{extra}")
    print("summary:", json.dumps(outcome["counts"], ensure_ascii=False, sort_keys=True))
    if args.report:
        args.report.write_text(json.dumps(outcome, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as handle:
            handle.write("telegram alert cleanup: " + json.dumps(outcome["counts"], sort_keys=True) + "\n")
    bad = {"refused_unreadable", "refused_not_alert", "deleted_but_still_public",
           "edit_failed", "edited_but_not_read_back"}
    return 1 if any(row["result"] in bad for row in outcome["results"]) else 0


if __name__ == "__main__":
    sys.exit(main())
