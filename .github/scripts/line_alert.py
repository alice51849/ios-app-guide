#!/usr/bin/env python3
"""Telegram alert for the line watchdog, sent only when the line-health state changes.

The watchdog judges every line twice a day and keeps one ``line-health`` issue
up to date; this script adds a phone notification without the noise of a
message per run. A message goes out only when

* a line turns red that was not red (notified) before, or
* every line is fresh again after at least one notified red line.

Lines that stay red, partial recoveries and all-green runs send nothing. The
dedupe memory is a small JSON state file (restored and saved by the workflow
with ``actions/cache``); it is advanced only after Telegram accepted the
message, so a failed send or missing secrets is retried on the next run
instead of being silently marked as notified. A missing or unreadable watchdog
report is itself treated as a red line (the watchdog went dark).

Internal alerts go only to ``TELEGRAM_ALERT_CHAT_ID`` (2026-10-18). The
repository's ``TELEGRAM_CHAT_ID`` is the public promo channel (ios-app-guide's
is t.me/LumiApps2026), and about 52 internal alerts leaked there while this
script sent to it. So:

* without ``TELEGRAM_ALERT_CHAT_ID`` nothing is sent (status
  ``alert_chat_missing``, not a failure) and there is never a fallback to
  ``TELEGRAM_CHAT_ID``;
* a target that looks public is refused: an ``@username`` (only public
  channels/groups have one), or a ``-100…`` id equal to the public promo chat
  (``TELEGRAM_PUBLIC_CHAT_ID``, or ``TELEGRAM_CHAT_ID`` if a workflow still
  exports it; both are read only for this comparison, never as a target);
* anything that is not a numeric chat id is refused as invalid.

The checks and the send itself live in ``telegram_alert_guard.py`` (the one
gate every internal Telegram message goes through; it also refuses a chat that
``getChat`` reports as public). This script only decides when to send.

Secrets come only from the environment (``TELEGRAM_BOT_TOKEN`` /
``TELEGRAM_ALERT_CHAT_ID`` / ``TELEGRAM_PUBLIC_CHAT_ID``, referenced as
``${{ secrets.X }}`` in the workflow) and are never printed. The same file is
committed to 00_GrowthEngine, ios-app-guide and threads-autopilot.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

import telegram_alert_guard as guard  # noqa: E402

STATE_SCHEMA = "line-watchdog.alert-state/v1"
SELF_LINE = "line-watchdog（看門狗本身）"
MAX_TEXT = 3900
HOUR = 3600.0

# Suggested next step per watchdog ``action`` (workflow / slot rows).
ACTION_ADVICE = {
    "retriggered": "看門狗已自動重派一次；下一輪（約 12 小時後）仍紅就打開該線最新一輪 run log 找根因。",
    "would_retrigger": "可以安全重派（這一輪只判不派）：手動 dispatch 一次，再看下一輪是否恢復。",
    "wait_in_progress": "有一輪正在跑，先等它結束；下一輪仍紅再查 log。",
    "circuit_open": "同一版本連續失敗，自動重派已熔斷：看最新失敗 run 的 log 修根因，修好推上 main 後才會再自動重派。",
    "retrigger_budget_exhausted": "24 小時內已自動重派 2 次仍沒恢復：看最新 run log 修根因，不要再手動狂派。",
    "recovery_forbidden": "這一類（非外宣）不自動重派：交統籌人工判斷。",
}

# Suggested next step per evidence line (rows whose action is "none").
EVIDENCE_ADVICE = {
    "growth_runner_online": "本機 Mac 的 macpro-growth runner 離線：請在 Mac 上重啟 GitHub Actions runner（launchd 服務），雲端無法代做。",
    "threads_runner_online": "threads-autopilot 用的本機 runner 離線：請在 Mac 上重啟 runner，雲端無法代做。",
    "guide_deployment": "Guide 站沒有新的部署：確認配對發布（00_GrowthEngine geo/pages gitlink 綁新 main 再 dispatch），讀回 /.well-known/deployment.json。",
    "telegram_message_id": "Telegram 每日貼文沒有新的 message_id：看 telegram-daily 最近一輪 log。",
    "threads_receipts": "Threads 沒有新的發文收據：workflow 綠燈不算數，查 post.yml 最近一輪的平台回應與 state 檔。",
    "bluesky_receipts": "Bluesky 沒有新的 uri+cid 收據：查 multi.yml 最近一輪的平台回應與 state 檔。",
    "nostr_receipts": "Nostr 沒有新的 relay 確認：查 nostr.yml 最近一輪 log 與 relay 回應。",
    "bluesky_text_posts": "Bluesky 帳號上沒有新的文字貼文：查 multi.yml 最近一輪與帳號狀態。",
    "crosspromo_audit_remote": "互推遠端稽核沒有通過：看 support-crosspromo 最近一輪 log 的 fail-closed 標記。",
    "coverage_floor": "外宣覆蓋率低於底線：看 reports/coverage_floor_latest.json 缺哪幾款，補上對應通路。",
    "self_hosted_queue": "自架執行器卡住：有 job 排隊超過 45 分鐘，或 4 小時內沒有任何 job 在 Mac 上跑完。請在 Mac 上確認 runner（launchd 服務）在線、沒有過載；雲端無法代做。",
    "promo_domain_http": "外宣主網域 open.cait518.cc 打不開（/robots.txt 沒有回 200）：本機 Mac 的通道服務可能停了，請在 Mac 上重啟通道；下載總頁、IG 個人檔案連結頁、指南站都受影響。",
}
DEFAULT_ADVICE = "看 line-health issue 的表格與該線最近一輪 run log。"
SLOT_ADVICE = "這條只監看、不自動重派：看那個排程時段是否被 GitHub 丟掉或失敗，必要時手動 dispatch 一次。"
SELF_ADVICE = "看門狗本身沒有產出判定（自測失敗或 API 錯誤）：打開這一輪 run 的 Self-test／Judge 步驟 log 修好它，否則所有線的警報都靜音。"


def parse_time(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in {"never", "n/a"}:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.timestamp()


def iso(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def load_state(path: Path) -> dict:
    data = load_json(path)
    if not data or data.get("schema") != STATE_SCHEMA or not isinstance(data.get("red"), dict):
        return {"schema": STATE_SCHEMA, "red": {}}
    return data


def red_rows(report: dict | None) -> list[dict]:
    """Red rows of a watchdog report; no usable report means the watchdog itself is red."""
    rows = (report or {}).get("rows")
    if not isinstance(rows, list):
        return [{"line": SELF_LINE, "kind": "self", "fresh": False, "last_success": None,
                 "max_age_hours": None, "action": "none", "note": "沒有 line-health.json 判定報告"}]
    return [row for row in rows if isinstance(row, dict) and row.get("line") and not row.get("fresh")]


def advice(row: dict) -> str:
    if row.get("kind") == "self":
        return SELF_ADVICE
    action = row.get("action") or "none"
    if action in ACTION_ADVICE:
        return ACTION_ADVICE[action]
    if row.get("kind") == "slot":
        return SLOT_ADVICE
    return EVIDENCE_ADVICE.get(str(row.get("line")), DEFAULT_ADVICE)


def staleness(row: dict, now: float) -> str:
    window = row.get("max_age_hours")
    allowed = f"（容許 {window:g} 小時）" if isinstance(window, (int, float)) else ""
    last = parse_time(row.get("last_success"))
    if last is None:
        return f"查不到任何新鮮的成功紀錄{allowed}"
    hours = max(0.0, (now - last) / HOUR)
    return f"已 {hours:.1f} 小時沒有新鮮成功{allowed}，最後一次 {iso(last)}"


def describe(row: dict, now: float) -> str:
    kind = {"workflow": "workflow", "evidence": "交付證據", "slot": "排程時段", "self": "看門狗"}.get(
        str(row.get("kind")), str(row.get("kind")))
    text = f"• {row['line']}（{kind}）：{staleness(row, now)}"
    note = str(row.get("note") or "").strip()
    if note and row.get("kind") != "self":
        text += f"\n  狀態：{note[:160]}"
    return text + f"\n  建議：{advice(row)}"


def plan(report: dict | None, state: dict, now: float, *, label: str, run_url: str = "") -> dict:
    """Decide whether this run is a state change worth a message, and the state to keep if it is sent."""
    current = {str(row["line"]): row for row in red_rows(report)}
    previous = dict(state.get("red") or {})
    new = [line for line in current if line not in previous]
    still = [line for line in current if line in previous]
    recovered = [line for line in previous if line not in current]
    stamp = iso(now)
    next_state = {
        "schema": STATE_SCHEMA, "label": label, "updated_at": stamp,
        "red": {line: {"since": (previous.get(line) or {}).get("since") or stamp,
                       "notified_at": (previous.get(line) or {}).get("notified_at") or stamp}
                for line in current},
    }
    judged = (report or {}).get("judged_at") or stamp
    footer = f"判定時間 {judged}（UTC）" + (f"\nrun：{run_url}" if run_url else "")
    if new:
        lines = [f"🔴 外宣線變紅（{label}）：新增 {len(new)} 條", ""]
        lines += [describe(current[line], now) for line in new]
        if still:
            lines += ["", "仍紅（之前已通知）：" + "、".join(still)]
        lines += ["", "同一條紅線不會重複通知；全部恢復時會再發一則。", footer]
        kind = "new_red"
    elif not current and previous:
        lines = [f"🟢 外宣線全部恢復新鮮（{label}）", "", "恢復：" + "、".join(recovered), "", footer]
        kind = "recovered"
    else:
        lines, kind = [], "none"
    message = "\n".join(lines)
    if len(message) > MAX_TEXT:
        message = message[: MAX_TEXT - 1] + "…"
    return {"kind": kind, "message": message or None, "new_red": new, "still_red": still,
            "recovered": recovered, "next_state": next_state}


# Shared gate (telegram_alert_guard.py): the target checks and the only internal send.
alert_target_problem = guard.alert_target_problem


def telegram_post(token: str, chat_id: str, text: str) -> int | None:
    """Send through the shared gate (which re-checks the target and refuses a public chat)."""
    return guard.post_alert(token, chat_id, text, public_chat_ids=guard.public_chat_ids_from_env())


def write_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def run(report_path: Path, state_path: Path, *, label: str, run_url: str, now: float,
        token: str, chat_id: str, public_chat_ids: tuple[str, ...] = (),
        post: Callable[[str, str, str], int | None] | None = None) -> dict:
    """Plan, send when the state changed, and advance the state only when nothing is left unsent.

    ``chat_id`` is the internal alert chat (TELEGRAM_ALERT_CHAT_ID) and nothing
    else; ``public_chat_ids`` are only compared against it so a public target is
    refused.
    """
    post = post or telegram_post  # looked up at call time so a patched telegram_post is honoured
    state = load_state(state_path)
    decision = plan(load_json(report_path), state, now, label=label, run_url=run_url)
    outcome = {"kind": decision["kind"], "new_red": decision["new_red"], "still_red": decision["still_red"],
               "recovered": decision["recovered"], "sent": False, "state_advanced": False}
    if decision["message"] is None:
        write_state(state_path, decision["next_state"])
        outcome.update(state_advanced=True, status="no_state_change")
        return outcome
    problem = alert_target_problem(chat_id, public_chat_ids)
    if problem:
        write_state(state_path, state)  # keep the old memory so the change is sent once a private chat is set
        outcome.update(status=problem)
        return outcome
    if not token:
        write_state(state_path, state)  # keep the old memory so the change is sent once secrets exist
        outcome.update(status="secrets_missing")
        return outcome
    try:
        message_id = post(token, chat_id, decision["message"])
    except guard.AlertRefused as refused:  # e.g. getChat says the chat is public
        write_state(state_path, state)
        outcome.update(status=refused.status)
        return outcome
    except Exception as error:  # noqa: BLE001 - a failed send is retried next run, never marked as notified
        write_state(state_path, state)
        outcome.update(status="send_failed", error=type(error).__name__)
        return outcome
    write_state(state_path, decision["next_state"])
    outcome.update(sent=True, state_advanced=True, status="sent", message_id=message_id)
    return outcome


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--report", type=Path, required=True, help="line-health.json written by line_watchdog.py")
    parser.add_argument("--state", type=Path, required=True, help="dedupe state file (persisted by actions/cache)")
    parser.add_argument("--label", required=True, help="repository label shown in the message")
    parser.add_argument("--run-url", default="")
    parser.add_argument("--outcome", type=Path, help="optional JSON copy of the outcome (no message text)")
    args = parser.parse_args(argv)
    outcome = run(args.report, args.state, label=args.label, run_url=args.run_url,
                  now=dt.datetime.now(dt.timezone.utc).timestamp(),
                  token=os.environ.get(guard.TOKEN_ENV, "").strip(),
                  chat_id=os.environ.get(guard.ALERT_CHAT_ENV, "").strip(),
                  public_chat_ids=guard.public_chat_ids_from_env())
    summary = (f"line alert: {outcome['status']} (change={outcome['kind']}, new red={len(outcome['new_red'])}, "
               f"still red={len(outcome['still_red'])}, recovered={len(outcome['recovered'])}, "
               f"state advanced={outcome['state_advanced']})")
    print(summary)
    if outcome["status"] == "alert_chat_missing":
        print("alert_chat_missing: repository secret TELEGRAM_ALERT_CHAT_ID is not set, so no internal alert "
              "is sent (never to the public TELEGRAM_CHAT_ID); the change stays pending until a private alert "
              "chat is configured. The line-health issue is unaffected.")
    if outcome["status"] == "alert_chat_public_refused":
        print("::error::TELEGRAM_ALERT_CHAT_ID points at a public channel (@username, or the public promo chat); "
              "internal alert refused. Set it to a private chat id.")
    if outcome["status"] == "alert_chat_invalid":
        print("::error::TELEGRAM_ALERT_CHAT_ID is not a numeric Telegram chat id; internal alert refused.")
    if outcome["status"] == "secrets_missing":
        print("Telegram skipped: repository secret TELEGRAM_BOT_TOKEN is not set; "
              "the change stays pending and is sent on the first run after it is added.")
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as handle:
            handle.write(f"\n{summary}\n")
    if args.outcome:
        args.outcome.write_text(json.dumps(outcome, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if outcome["status"] in {"alert_chat_public_refused", "alert_chat_invalid"}:
        return 1
    if outcome["status"] == "send_failed":
        print(f"::warning::Telegram send failed ({outcome.get('error')}); will retry on the next run")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
