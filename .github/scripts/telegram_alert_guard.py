#!/usr/bin/env python3
"""The one gate every internal Telegram message goes through.

"Internal" means anything written for the team, not for the public: watchdog
alerts, health checks, conversion-guard / regression / growth-effect summaries,
``line_watchdog.py --telegram``. "Promo" means posts written for the public
promo channel (t.me/LumiApps2026, the repositories' ``TELEGRAM_CHAT_ID``).

Until 2026-10-18 internal alerts used ``TELEGRAM_CHAT_ID`` and 65 of them were
posted to the public promo channel. From then on:

* an internal message goes only to ``TELEGRAM_ALERT_CHAT_ID``; without it nothing
  is sent (status ``alert_chat_missing``, not a failure) and there is never a
  fallback to ``TELEGRAM_CHAT_ID``;
* a target that is, or looks, public is refused (``alert_chat_public_refused``):
  an ``@username`` (only public chats have one), an id equal to the public promo
  chat (``TELEGRAM_PUBLIC_CHAT_ID`` or ``TELEGRAM_CHAT_ID``, both read only for
  this comparison, never as a target), or a chat that ``getChat`` reports as a
  group / channel with a public username;
* a target that is not a numeric chat id is refused (``alert_chat_invalid``).

``test_telegram_send_points.py`` scans the repository: a new file that calls
the Telegram Bot API without going through this module (and is not a reviewed
promo / public-channel maintenance send point) fails the test.

Workflows send an internal message with the CLI::

    python3 .github/scripts/telegram_alert_guard.py --text-file alert.txt --label conversion-guard

with ``TELEGRAM_BOT_TOKEN``, ``TELEGRAM_ALERT_CHAT_ID`` and (for the comparison
only) ``TELEGRAM_PUBLIC_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}`` in its env.
Secrets come only from the environment and are never printed. Standard library
only; the same file is committed to 00_GrowthEngine, ios-app-guide and
threads-autopilot.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Mapping

TOKEN_ENV = "TELEGRAM_BOT_TOKEN"
ALERT_CHAT_ENV = "TELEGRAM_ALERT_CHAT_ID"
PUBLIC_CHAT_ENVS = ("TELEGRAM_PUBLIC_CHAT_ID", "TELEGRAM_CHAT_ID")
# Public promo channels by username (lower case, no "@"); a getChat answer naming one is refused.
KNOWN_PUBLIC_USERNAMES = frozenset({"lumiapps2026"})
MAX_TEXT = 3900

MISSING = "alert_chat_missing"
PUBLIC = "alert_chat_public_refused"
INVALID = "alert_chat_invalid"
SECRETS_MISSING = "secrets_missing"
SEND_FAILED = "send_failed"
SENT = "sent"
REFUSALS = frozenset({PUBLIC, INVALID})

Api = Callable[[str, str, dict], dict]


class AlertRefused(RuntimeError):
    """The target must not receive an internal message; ``status`` says why."""

    def __init__(self, status: str):
        super().__init__(status)
        self.status = status


def public_chat_ids_from_env(env: Mapping[str, str] | None = None) -> tuple[str, ...]:
    env = os.environ if env is None else env
    return tuple(value.strip() for value in (env.get(name, "") for name in PUBLIC_CHAT_ENVS) if value and value.strip())


def alert_target_problem(chat_id: str, public_chat_ids: tuple[str, ...] = ()) -> str | None:
    """Why ``chat_id`` must not receive an internal message, or None when it may.

    An ``@username`` target is public by definition; an id equal to the public
    promo chat is the promo channel itself; anything that is not a numeric id is
    refused as invalid rather than guessed at.
    """
    target = (chat_id or "").strip()
    if not target:
        return MISSING
    if target.startswith("@"):
        return PUBLIC
    public = {value.strip() for value in public_chat_ids if value and value.strip()}
    if target in public:
        return PUBLIC
    if not target.lstrip("-").isdigit() or target.count("-") > 1:
        return INVALID
    return None


def chat_info_problem(info: Mapping) -> str | None:
    """Refuse a chat that getChat reports as public (a group / channel with a username)."""
    if not isinstance(info, Mapping):
        return INVALID
    username = str(info.get("username") or "").strip().lstrip("@").lower()
    kind = str(info.get("type") or "")
    if username and (kind != "private" or username in KNOWN_PUBLIC_USERNAMES):
        return PUBLIC
    return None


def bot_api(token: str, method: str, payload: dict) -> dict:
    """POST one Bot API call; the result object, or RuntimeError with Telegram's description."""
    request = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}",
                                     data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            answer = json.load(response)
    except urllib.error.HTTPError as error:
        try:
            answer = json.loads(error.read().decode("utf-8", "replace"))
        except ValueError:
            answer = {"ok": False, "description": f"HTTP {error.code}"}
    if not answer.get("ok"):
        raise RuntimeError(str(answer.get("description") or "telegram rejected the call")[:200])
    return answer.get("result") or {}


def post_alert(token: str, chat_id: str, text: str, *, public_chat_ids: tuple[str, ...] = (),
               api: Api | None = None) -> int | None:
    """Send one internal message after every check; the message id. Raises AlertRefused / RuntimeError."""
    problem = alert_target_problem(chat_id, public_chat_ids)
    if problem:
        raise AlertRefused(problem)
    if not token:
        raise AlertRefused(SECRETS_MISSING)
    api = api or bot_api
    target = chat_id.strip()
    problem = chat_info_problem(api(token, "getChat", {"chat_id": target}))
    if problem:
        raise AlertRefused(problem)
    if len(text) > MAX_TEXT:
        text = text[: MAX_TEXT - 1] + "…"
    result = api(token, "sendMessage", {"chat_id": target, "text": text, "disable_web_page_preview": True})
    return (result or {}).get("message_id")


def send_internal_alert(text: str, *, env: Mapping[str, str] | None = None, token: str | None = None,
                        chat_id: str | None = None, public_chat_ids: tuple[str, ...] | None = None,
                        api: Api | None = None) -> dict:
    """Send an internal message to TELEGRAM_ALERT_CHAT_ID only; an outcome dict, never raises.

    ``token`` / ``chat_id`` / ``public_chat_ids`` default to the environment
    (``TELEGRAM_BOT_TOKEN`` / ``TELEGRAM_ALERT_CHAT_ID`` / ``TELEGRAM_PUBLIC_CHAT_ID`` +
    ``TELEGRAM_CHAT_ID``). ``TELEGRAM_CHAT_ID`` is never a target.
    """
    env = os.environ if env is None else env
    token = (env.get(TOKEN_ENV, "") if token is None else token).strip()
    chat_id = (env.get(ALERT_CHAT_ENV, "") if chat_id is None else chat_id).strip()
    public = public_chat_ids_from_env(env) if public_chat_ids is None else tuple(public_chat_ids)
    if not (text or "").strip():
        return {"status": "nothing_to_send", "sent": False}
    try:
        message_id = post_alert(token, chat_id, text, public_chat_ids=public, api=api)
    except AlertRefused as refused:
        return {"status": refused.status, "sent": False}
    except Exception as error:  # noqa: BLE001 - the caller decides; the outcome says it failed
        return {"status": SEND_FAILED, "sent": False, "error": type(error).__name__}
    return {"status": SENT, "sent": True, "message_id": message_id}


def explain(outcome: dict, label: str = "") -> tuple[str, int]:
    """One log line for an outcome and the exit code a workflow step should use."""
    status = outcome["status"]
    where = f" ({label})" if label else ""
    if status == SENT:
        return f"internal alert{where}: sent to TELEGRAM_ALERT_CHAT_ID, message_id {outcome.get('message_id')}", 0
    if status == MISSING:
        return (f"alert_chat_missing{where}: repository secret TELEGRAM_ALERT_CHAT_ID is not set, so no internal "
                "message is sent (never to the public TELEGRAM_CHAT_ID)."), 0
    if status == SECRETS_MISSING:
        return f"internal alert{where} skipped: repository secret TELEGRAM_BOT_TOKEN is not set.", 0
    if status == "nothing_to_send":
        return f"internal alert{where}: empty message, nothing sent.", 0
    if status == PUBLIC:
        return (f"::error::TELEGRAM_ALERT_CHAT_ID{where} points at a public chat (@username, the public promo "
                "chat, or a chat with a public username); internal message refused. Set it to a private chat id."), 1
    if status == INVALID:
        return f"::error::TELEGRAM_ALERT_CHAT_ID{where} is not a numeric Telegram chat id; internal message refused.", 1
    return f"::warning::internal alert{where} failed ({outcome.get('error') or status}); nothing was sent.", 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--text-file", type=Path, required=True, help="message text (UTF-8)")
    parser.add_argument("--max-chars", type=int, default=MAX_TEXT)
    parser.add_argument("--label", default="", help="what is alerting, shown in the log line only")
    args = parser.parse_args(argv)
    try:
        text = args.text_file.read_text(encoding="utf-8").strip()
    except OSError:
        text = ""
    text = text[: max(1, min(args.max_chars, MAX_TEXT))]
    outcome = send_internal_alert(text)
    line, code = explain(outcome, args.label)
    print(line)
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as handle:
            handle.write(f"\n{line.replace('::error::', '').replace('::warning::', '')}\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
