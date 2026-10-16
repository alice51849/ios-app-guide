#!/usr/bin/env python3
"""Add the app's direct download link (inline buttons) under our early Telegram posts that carry none.

Owner rule (2026-10-17): every promo post carries the app's direct download link. The public channel's text
posts carry the links in the text; two of the first posts (the channel's own test message and the free
printable zhuyin-sheet web tool) only link to a web page. A bot can edit its own messages, so the inline
buttons "App Store" (and "Google Play" when the app is on Android) are added with editMessageReplyMarkup;
the text is not touched. Only the message ids listed in FIXES are ever edited.

- audit: read each listed message from the public preview page (t.me/s/<channel>, no token) and report
  whether it already has the App Store link of its app.
- apply: add the buttons to the ones that lack it, then read the answer back (the edited message's own
  reply_markup) and keep a receipt. A message is only ever edited once.

The bot token is read from the environment and never printed.

    python3 telegram_link_fix.py audit
    python3 telegram_link_fix.py apply
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

import clip_posts as CP
import download_links as DL
import link_backfill as B
import own_posts as OP
from social_post_common import android_apps, campaign_app_store_url, play_store_url

CHANNEL = "LumiApps2026"
STATE = OP.GROWTH / "telegram-link-fix.json"
REPORT = OP.GROWTH / "telegram-link-fix-report.json"
CT = "bf_tg"
GAP = 3  # seconds between two edits
UA = "Mozilla/5.0 (compatible; lumi-telegram-links/1.0)"
# message id -> (app key, locale of the button labels)
FIXES = {"3": ("lumibopomofo", "zh-Hant"), "9": ("lumibopomofo", "zh-Hant")}
NOT_MODIFIED = "message is not modified"


def api(token, method, payload, opener=urllib.request.urlopen, timeout=30):
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": UA})
    try:
        with opener(req, timeout=timeout) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as exc:   # the reason only: the request URL carries the token
        try:
            description = json.loads(exc.read() or b"{}").get("description", "")
        except ValueError:
            description = ""
        finally:
            exc.close()
        raise RuntimeError(f"HTTP {exc.code} {description or exc.reason}"[:160]) from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"network error {str(exc.reason)[:80]}") from None


def preview(post_id, opener=urllib.request.urlopen):
    """(hrefs, text) of one message of the public channel, from the public preview page (read only)."""
    req = urllib.request.Request(f"https://t.me/s/{CHANNEL}?before={int(post_id) + 1}", headers={"User-Agent": UA})
    with opener(req, timeout=30) as r:
        page = r.read().decode("utf-8", "replace")
    for blk in re.split(r'(?=<div class="tgme_widget_message_wrap)', page)[1:]:
        m = re.search(r'data-post="([^"]+)"', blk)
        if m and m.group(1) == f"{CHANNEL}/{post_id}":
            hrefs = [html.unescape(h) for h in re.findall(r'href="([^"]+)"', blk)]
            tm = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', blk, re.S)
            text = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<br\s*/?>", "\n", tm.group(1)))) if tm else ""
            return hrefs, " ".join(text.split())
    raise LookupError(f"message {post_id} is not on the public preview page")


def keyboard(locale, store, play):
    row = [{"text": CP.text_for(locale)["button"], "url": store}]
    if play:
        label = CP.PLAY_LINE.get(locale) or CP.PLAY_LINE.get(locale.split("-")[0]) or CP.PLAY_LINE["en"]
        row.append({"text": label, "url": play})
    return {"inline_keyboard": [row]}


def buttons_in(result):
    """The button URLs of a Message object as the Bot API answers it."""
    markup = (result or {}).get("reply_markup") or {}
    return [b.get("url", "") for row in markup.get("inline_keyboard", []) for b in row if isinstance(b, dict)]


def run(token, chat, state, catalog, *, apply=False, fixes=None, read=preview, call=api, sleeper=time.sleep,
        gap=GAP, log=print, save=None, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    rows = []
    for mid, (app, locale) in sorted((fixes or FIXES).items(), key=lambda kv: int(kv[0]), reverse=True):
        row = {"channel": "telegram", "id": mid, "permalink": f"https://t.me/{CHANNEL}/{mid}", "date": "",
               "app": app, "status": "", "text": "", "why": "message id listed in FIXES"}
        rows.append(row)
        try:
            hrefs, text = read(mid)
        except Exception as exc:
            row["status"] = f"read_failed:{str(exc)[:40]}"
            continue
        row["text"] = text[:140]
        ios = B.ios_id_for(catalog, {"app": app})
        if not ios:
            row["status"] = "unknown_app"
            continue
        if ios in DL.store_ids_in(" ".join(hrefs) + " " + text):
            row["status"] = "ok_caption"
            continue
        if state["done"].get("telegram", {}).get(mid):
            row["status"] = "ok_backfilled_earlier"
            continue
        row["status"] = "missing"
        if not apply:
            continue
        if not android_apps():   # the Play link could not be decided: never write half a link
            row["status"] = "snapshot_missing"
            log("::error::telegram: the Android snapshot is empty; nothing is edited")
            break
        store = campaign_app_store_url(f"https://apps.apple.com/app/id{ios}", CT)
        play = play_store_url(ios, CT)
        markup = keyboard(locale, store, play)
        try:
            answer = call(token, "editMessageReplyMarkup",
                          {"chat_id": chat, "message_id": int(mid), "reply_markup": markup})
            urls = buttons_in(answer.get("result"))
        except Exception as exc:
            if NOT_MODIFIED in str(exc).lower():   # the very same buttons are already there
                urls = [b["url"] for b in markup["inline_keyboard"][0]]
            else:
                row["status"] = "write_failed"
                row["error"] = str(exc)[:160]
                log(f"::warning::telegram: editing message {mid} failed ({str(exc)[:100]}); stopping")
                break
        receipt = state["done"].setdefault("telegram", {})[mid] = {
            "at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "app": app,
            "verified": DL.has_download_link(" ".join(urls), store, play)}
        if save:
            save(state)
        row["status"] = "backfilled" if receipt["verified"] else "backfilled_unverified"
        log(f"telegram: buttons added under message {mid} ({app}) verified={receipt['verified']}")
        sleeper(gap)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["audit", "apply"])
    ap.add_argument("--report", default=str(REPORT))
    args = ap.parse_args(argv)
    apply = args.cmd == "apply"
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if apply and not (token and chat):
        print("telegram_link_fix: TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set, nothing edited")
        return 0
    if apply and not android_apps():
        print("::error::telegram_link_fix: the Android snapshot is empty or unreadable; the Play link cannot be decided, stopping")
        return 1
    state = B.load_state(STATE)
    rows = run(token, chat, state, OP.Catalog(), apply=apply, save=lambda st: B.save_state(st, STATE))
    counts = B.summarize(rows)
    report = {"generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "mode": args.cmd,
              "counts": counts, "rows": rows}
    with open(args.report, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    B.save_state(state, STATE)
    print(f"telegram_link_fix {args.cmd}: {counts}")
    for r in rows:
        print(f"  telegram {r['id']} {r['app']} {r['status']} {r.get('text', '')[:60]}")
    return 1 if any(r["status"].startswith(("write_failed", "read_failed")) or r["status"] == "snapshot_missing"
                    for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
