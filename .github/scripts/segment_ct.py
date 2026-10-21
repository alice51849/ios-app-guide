"""Cute To-Do (可愛待辦清單) daily lead audience segment and its campaign token ln_mochi_<segment>_<channel>.

The table is .github/growth/mochi-daily-segment.json, a byte-for-byte copy of 00_GrowthEngine
ops/company/audience/mochi_daily_segment.json (from its ops/company/audience/mochi.md 90-day timeline); the code
below the paths is the same as 00_GrowthEngine lib/mochi_segment.py: change both in the same change.
clip_posts.with_campaign / play_url put the token on Mochi's Instagram, Telegram, Bluesky and YouTube Shorts links
(the table's "exits"); download_links._CAMPAIGN_KEEP sends ln_mochi_* as is.
"""
import datetime as dt
import functools
import json
import re
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[1] / "growth" / "mochi-daily-segment.json"
SCHEMA = "growth.mochi-daily-segment/v1"
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
TOKEN_RE = re.compile(r"^ln_mochi_[a-z]+_[a-z]{2}$")


@functools.lru_cache(maxsize=8)
def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load(path=None):
    """The daily segment table; {} when it cannot be read (the exits then keep their usual token)."""
    try:
        cfg = _load(str(path or CONFIG))
    except (OSError, ValueError):
        return {}
    return cfg if isinstance(cfg, dict) and cfg.get("schema") == SCHEMA else {}


def _pick(rule, day, start):
    if not isinstance(rule, dict):
        return None
    weekday = (rule.get("weekdays") or {}).get(WEEKDAYS[day.weekday()])
    if weekday:
        return weekday
    rotate = rule.get("rotate") or []
    return rotate[(day - start).days % len(rotate)] if rotate else None


def segment_for(day=None, cfg=None):
    """The day's lead audience segment (reset / host / adhd / kids / soft / exam) or None (no table)."""
    cfg = load() if cfg is None else cfg
    if not cfg:
        return None
    day = day or dt.datetime.now(dt.timezone.utc).date()
    iso = day.isoformat()
    seg = (cfg.get("dates") or {}).get(iso)
    if not seg:
        for window in cfg.get("windows") or []:
            if window.get("from", "") <= iso <= window.get("to", ""):
                seg = _pick(window, day, dt.date.fromisoformat(window["from"]))
                break
        else:
            seg = _pick(cfg.get("default"), day, dt.date.min)
    return seg if seg in (cfg.get("segments") or ()) else None


def segment_token(app_id, channel, day=None, cfg=None):
    """ln_mochi_<segment>_<channel> for the table's app on one of its exits that day; None for any other app,
    channel, or an unreadable table (the caller keeps its usual token then)."""
    cfg = load() if cfg is None else cfg
    if not cfg or str(app_id or "") != str(cfg.get("app_id")) or channel not in (cfg.get("exits") or ()):
        return None
    if channel not in (cfg.get("channels") or ()):
        return None
    seg = segment_for(day, cfg)
    if not seg:
        return None
    token = str(cfg.get("token") or "").format(segment=seg, channel=channel)
    return token if TOKEN_RE.fullmatch(token) else None
