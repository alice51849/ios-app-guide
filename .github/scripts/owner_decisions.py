#!/usr/bin/env python3
"""Apply Caitlyn's 已完成／已拒絕／AI 自己做 button presses to app-improvements.json.

office.cait518.cc/outreach.html shows the owner_actions cards with three
buttons; the office server stores each press and serves them at
/api/owner-decision. This copies them into .github/growth/owner-decisions.json
(what the AI sessions read) and into the owner_actions rows:

  done      -> status done, done_at, resolution "done"
  declined  -> status done, done_at, resolution "declined"   (never do it)
  ai        -> status in_progress, resolution "ai"           (Claude does it)
  (pressed 改回待處理) -> back to todo if this script had closed it

Zero tokens: runs in owner-decisions.yml every 30 minutes.
"""
import argparse
import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

GROWTH = Path(__file__).resolve().parents[1] / "growth"
IMPROVEMENTS = GROWTH / "app-improvements.json"
LOG = GROWTH / "owner-decisions.json"
URL = "https://office.cait518.cc/api/owner-decision"
FIELDS = ("resolution", "decided_at")


def stamp(at):
    """Server ISO time (with milliseconds) -> the file's YYYY-MM-DDTHH:MM:SSZ."""
    try:
        return dt.datetime.fromisoformat(str(at).replace("Z", "+00:00")).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def apply(document, decisions):
    """Update owner_actions in place; return the ids that changed."""
    changed = []
    for row in document.get("owner_actions", []):
        dec = decisions.get(row.get("id"))
        before = json.dumps(row, sort_keys=True)
        if dec and dec.get("decision") in ("done", "declined", "ai"):
            at = stamp(dec.get("at"))
            row["resolution"] = dec["decision"]
            row["decided_at"] = at
            if dec["decision"] == "ai":
                row["status"] = "in_progress"
                row.pop("done_at", None)
            else:
                row["status"] = "done"
                row["done_at"] = at
        elif not dec and row.get("resolution"):
            for key in FIELDS + ("done_at",):
                row.pop(key, None)
            row["status"] = "todo"
        if json.dumps(row, sort_keys=True) != before:
            changed.append(row["id"])
    return changed


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=URL)
    a = ap.parse_args(argv)
    try:
        req = urllib.request.Request(a.url, headers={"User-Agent": "curl/8 lumi-owner-decisions"})
        with urllib.request.urlopen(req, timeout=30) as r:
            decisions = json.loads(r.read()).get("decisions") or {}
    except Exception as exc:  # office server asleep: try again next run
        print(f"::warning::{a.url} unavailable ({exc.__class__.__name__})")
        return 0
    document = json.loads(IMPROVEMENTS.read_text(encoding="utf-8"))
    changed = apply(document, decisions)
    log = {"source": URL, "decisions": decisions}
    LOG.write_text(json.dumps(log, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if changed:
        document["updated_at"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        IMPROVEMENTS.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{len(decisions)} decision(s); changed: {', '.join(changed) or 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
