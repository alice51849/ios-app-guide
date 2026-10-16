#!/usr/bin/env python3
"""Template + data series for the Threads evening slot (zero token).

One post a day at 13:00 UTC (Taiwan 21:00, US Eastern 9:00), in the slot the
Americas hook clip used to take, so the account stays at 3 posts a day:

- BM-11 UsageNow: on the day Claude's usage limits change (events in the data
  file), an explainer. UsageNow stays in threads-autopilot's
  PENDING_ONBOARDING, so this slot is its only Threads text route.
- BM-22 Lumi Weather: "明天○○度穿什麼" for Taipei, Taichung and Kaohsiung,
  from the MET Norway forecast.
- BM-17 Mochi: "Today's #MochiChecklist", a 4-task list.

Order: UsageNow event > a UsageNow hook clip planned for the slot > weather on
a cold, hot, rainy or big-swing day > the daily rotation > the planned clip.
Everything comes from .github/growth/threads-series.json; the store link with
the series ct goes in the first reply.

    python3 threads_series.py preview [--date YYYY-MM-DD] [--offline]
    python3 threads_series.py evening        # post, or print fallback=clip
    python3 threads_series.py room           # exit 0 under the daily cap, 1 at the cap, 2 count unknown
"""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

SERIES = HERE.parent / "growth" / "threads-series.json"
CLIPS = HERE.parent / "growth" / "clips.json"
# Dated conversion posts for audiences awake at 13:00 UTC (US / BR morning, EU afternoon):
# one post per date, native language, a bm_<app>_<cc>_th token; the rotation keeps every other day.
EVENING_QUEUE = HERE.parent / "growth" / "threads-evening-queue.json"
TW = dt.timezone(dt.timedelta(hours=8))
EVENING_CLIP_SLOT = 15  # clips.json slot id of the clip this slot replaces
UA = "LumiApps-threads-series/1.0 hourstag.app@gmail.com"
WEEKDAYS = "一二三四五六日"
MAX_POST_CHARS = 500


def load(path=SERIES):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def today_tw(now=None):
    return (now or dt.datetime.now(dt.timezone.utc)).astimezone(TW).date()


def load_evening_queue(path=EVENING_QUEUE):
    """Posts of growth/threads-evening-queue.json; a missing or broken file is an empty queue."""
    try:
        posts = json.loads(Path(path).read_text(encoding="utf-8")).get("posts", [])
    except (OSError, ValueError):
        return []
    return [p for p in posts if isinstance(p, dict)]


def evening_queued(day, queue):
    """The conversion post queued for `day` (Taiwan date), or None."""
    for p in queue:
        if p.get("date") == day.isoformat():
            return p
    return None


def queue_post(p):
    return {"series": "CONV", "app": p["app"], "app_id": p["app_id"], "ct": p["ct"],
            "locale": p.get("locale", ""), "text": p["text"], "image_url": p.get("image_url")}


def planned_clip(day, clips_path=CLIPS):
    """The Threads hook clip clips.json plans for the evening slot, or None."""
    try:
        data = json.loads(Path(clips_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    for e in data.get("schedule", []):
        if e.get("channel") == "threads" and e.get("slot") == EVENING_CLIP_SLOT and e.get("date") == day.isoformat():
            return e.get("clip")
    return None


# ---- forecast -------------------------------------------------------------

def fetch_forecast(lat, lon, opener=urllib.request.urlopen):
    url = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat:.2f}&lon={lon:.2f}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with opener(req, timeout=30) as r:
        return json.loads(r.read())


def summarize(forecast, day):
    """Min/max temperature and rain (mm) for a Taiwan calendar day."""
    temps, rain = [], 0.0
    for step in forecast.get("properties", {}).get("timeseries", []):
        t = dt.datetime.fromisoformat(step["time"].replace("Z", "+00:00")).astimezone(TW)
        if t.date() != day:
            continue
        data = step.get("data", {})
        temp = data.get("instant", {}).get("details", {}).get("air_temperature")
        if temp is not None:
            temps.append(float(temp))
        hour = data.get("next_1_hours", {}).get("details", {}).get("precipitation_amount")
        if hour is not None:
            rain += float(hour)
    if len(temps) < 12:  # not enough hourly data for a whole day
        return None
    return {"min": round(min(temps)), "max": round(max(temps)), "rain": round(rain, 1)}


def tomorrow_weather(series, day, fetch=fetch_forecast):
    """{city name: summary} for the day after `day`, or None if any city fails."""
    target = day + dt.timedelta(days=1)
    out = {}
    for city in series["cities"]:
        try:
            s = summarize(fetch(city["lat"], city["lon"]), target)
        except Exception as error:  # network, JSON: the slot falls back
            print(f"series: forecast for {city['name']} failed ({error.__class__.__name__})", file=sys.stderr)
            return None
        if s is None:
            return None
        out[city["name"]] = s
    return out


def weather_triggered(series, weather):
    tr = series["triggers"]
    first = weather[series["cities"][0]["name"]]
    return (
        first["min"] <= tr["min_le"]
        or first["max"] >= tr["max_ge"]
        or first["max"] - first["min"] >= tr["range_ge"]
        or any(w["rain"] >= tr["rain_mm_ge"] for w in weather.values())
    )


# ---- composing ------------------------------------------------------------

def compose_weather(series, weather, day):
    target = day + dt.timedelta(days=1)
    names = [c["name"] for c in series["cities"]]
    first = weather[names[0]]
    mean = (first["min"] + first["max"]) / 2
    outfit = next(b["text"] for b in series["bands"] if mean <= b["mean_le"])
    extra = []
    swing = first["max"] - first["min"]
    if swing >= series["range_line_ge"]:
        extra.append(series["range_line"].format(range=swing))
    wet = [n for n in names if weather[n]["rain"] >= series["triggers"]["rain_mm_ge"]]
    if wet:
        extra.append(series["rain_line"].format(cities="、".join(wet)))
    return series["template"].format(
        date=f"{target.month}/{target.day} 週{WEEKDAYS[target.weekday()]}",
        city_lines="\n".join(f"{n} {weather[n]['min']}–{weather[n]['max']}°C" for n in names),
        outfit=outfit,
        extra="".join("\n" + line for line in extra),
        source=series["forecast_source"],
    )


def compose_mochi(series, day):
    lists = series["lists"]
    # Mochi takes every other evening (rotation), so step by two days to use every list.
    row = lists[(day.toordinal() // 2) % len(lists)]
    fields = {"title": row["title"], "tip": row["tip"]}
    fields.update({f"item_{i + 1}": item for i, item in enumerate(row["items"])})
    return series["template"].format(**fields)


def usagenow_event(series, day):
    if series.get("status") != "live":
        return None
    for event in series.get("events", []):
        if event.get("date") != day.isoformat():
            continue
        if all(event.get(k) and len(str(event[k])) <= series["field_max"][k] for k in series["event_fields"]):
            return event
        print(f"series: UsageNow event {event.get('date')} is incomplete or too long; skipped", file=sys.stderr)
    return None


def post(series, text, image_url=None):
    return {"series": series["bm"], "app": series["app"], "app_id": series["app_id"],
            "ct": series["ct"], "locale": series["locale"], "text": text, "image_url": image_url}


def plan(day, data=None, weather=None, clip=None, queue=None):
    """What the evening slot posts on `day`: a series post dict, or None for
    the planned hook clip. `weather` is tomorrow_weather() (None = unknown).
    Order: UsageNow event > UsageNow clip > weather alert > dated conversion
    post (`queue`, growth/threads-evening-queue.json) > rotation > clip."""
    data = data or load()
    queue = load_evening_queue() if queue is None else queue
    s = data["series"]
    event = usagenow_event(s["usagenow_policy"], day)
    if event:
        fields = {k: event[k] for k in s["usagenow_policy"]["event_fields"]}
        return post(s["usagenow_policy"], s["usagenow_policy"]["template"].format(**fields), event.get("image_url"))
    if clip and clip.split("/")[0] in data.get("priority_clip_apps", []):
        return None
    wx = s["lumiweather_tomorrow"]
    weather_ok = wx.get("status") == "live" and weather is not None
    if weather_ok and weather_triggered(wx, weather):
        return post(wx, compose_weather(wx, weather, day))
    queued = evening_queued(day, queue)
    if queued and not evening_queue_problems([queued]):
        return queue_post(queued)
    rotation = [k for k in data["rotation"] if s[k].get("status") == "live"]
    if rotation:
        key = rotation[day.toordinal() % len(rotation)]
        if key == "lumiweather_tomorrow" and not weather_ok:
            key = next((k for k in rotation if k != "lumiweather_tomorrow"), None)
        if key == "lumiweather_tomorrow":
            return post(wx, compose_weather(wx, weather, day))
        if key == "mochi_checklist":
            return post(s[key], compose_mochi(s[key], day))
    return None


BANNED = ("best", "#1", "No.1", "最強", "最好", "第一", "最佳", "free forever", "price", "$")
QUEUE_FIELDS = ("date", "app", "app_id", "ct", "locale", "text")


def evening_queue_problems(queue):
    """Why a conversion post cannot take the slot: missing fields, a token that is not a
    pre-registered bm_<app>_<cc>_th series token, an overlong body, a link, a banned word,
    or two posts on one date."""
    from social_post_common import APP_STORE_CAMPAIGN_RE
    problems, dates = [], set()
    for p in queue:
        where = f"evening queue {p.get('date')} {p.get('app')}"
        missing = [k for k in QUEUE_FIELDS if not p.get(k)]
        if missing:
            problems.append(f"{where}: missing {missing}")
            continue
        try:
            dt.date.fromisoformat(p["date"])
        except ValueError:
            problems.append(f"{where}: bad date")
        if p["date"] in dates:
            problems.append(f"{where}: two posts on one date")
        dates.add(p["date"])
        if APP_STORE_CAMPAIGN_RE.fullmatch(p["ct"]) is None or not p["ct"].startswith("bm_") or not p["ct"].endswith("_th"):
            problems.append(f"{where}: ct must be bm_<app>_<cc>_th, not {p['ct']!r}")
        text = p["text"]
        if len(text) > MAX_POST_CHARS:
            problems.append(f"{where}: {len(text)} chars")
        if "http" in text:
            problems.append(f"{where}: link in body")
        low = text.lower()
        problems += [f"{where}: banned {w!r}" for w in BANNED if w.lower() in low]
    return problems


def validate(data=None, queue=None):
    """Problems with the data files: lengths, ct tokens, banned words."""
    from social_post_common import APP_STORE_CAMPAIGN_RE
    data = data or load()
    problems = evening_queue_problems(load_evening_queue() if queue is None else queue)
    banned = BANNED
    day = dt.date(2026, 1, 5)
    sample = {c["name"]: {"min": 9, "max": 19, "rain": 3.0} for c in data["series"]["lumiweather_tomorrow"]["cities"]}
    texts = [compose_weather(data["series"]["lumiweather_tomorrow"], sample, day)]
    mochi = data["series"]["mochi_checklist"]
    texts += [compose_mochi(mochi, day + dt.timedelta(days=2 * i)) for i in range(len(mochi["lists"]))]
    un = data["series"]["usagenow_policy"]
    texts.append(un["template"].format(**{k: "x" * un["field_max"][k] for k in un["event_fields"]}))
    for key, s in data["series"].items():
        if APP_STORE_CAMPAIGN_RE.fullmatch(s["ct"]) is None:
            problems.append(f"{key}: bad ct {s['ct']!r}")
        if s.get("status") not in ("live", "held"):
            problems.append(f"{key}: status must be live or held")
    for text in texts:
        if len(text) > MAX_POST_CHARS:
            problems.append(f"{len(text)} chars: {text[:40]!r}")
        if "http" in text:
            problems.append(f"link in body: {text[:40]!r}")
        low = text.lower()
        problems += [f"banned {w!r}: {text[:40]!r}" for w in banned if w.lower() in low]
    return problems


# ---- account cap ----------------------------------------------------------

def posts_today(token, now=None, opener=urllib.request.urlopen):
    """Top-level posts the token's Threads account published since Taiwan
    midnight (replies, such as the link replies, are not counted)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    start = dt.datetime.combine(today_tw(now), dt.time(), TW)
    query = urllib.parse.urlencode({"fields": "id,timestamp", "since": int(start.timestamp()),
                                    "limit": 50, "access_token": token})
    with opener(f"https://graph.threads.net/v1.0/me/threads?{query}", timeout=30) as r:
        rows = json.loads(r.read()).get("data", [])
    count = 0
    for row in rows:
        stamp = row.get("timestamp", "")
        try:
            when = dt.datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%S%z")
        except ValueError:
            continue
        if when >= start:
            count += 1
    return count


def room_status(token, cap, now=None, opener=urllib.request.urlopen):
    """"room" under the cap, "full" at it, "unknown" when the count failed."""
    try:
        n = posts_today(token, now, opener)
    except Exception as error:
        print(f"series: could not count today's Threads posts ({error.__class__.__name__}); holding", file=sys.stderr)
        return "unknown"
    print(f"series: {n} Threads posts today (cap {cap})")
    return "room" if n < cap else "full"


def has_room(token, cap, now=None, opener=urllib.request.urlopen):
    """True when the account is under the cap. Unknown counts as full."""
    return room_status(token, cap, now, opener) == "room"


# ---- CLI ------------------------------------------------------------------

def _output(key, value):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")
    print(f"{key}={value}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["preview", "evening", "room", "validate"])
    ap.add_argument("--date", help="Taiwan date YYYY-MM-DD, default today")
    ap.add_argument("--offline", action="store_true", help="preview without the forecast")
    args = ap.parse_args(argv)
    data = load()
    day = dt.date.fromisoformat(args.date) if args.date else today_tw()
    if args.command == "validate":
        problems = validate(data)
        print("\n".join(problems) or "series: data ok")
        return 1 if problems else 0
    token = os.environ.get("THREADS_TOKEN", "").strip()
    if args.command == "room":
        # Every Threads post path (threads-post.yml slots, its backfills and
        # threads-autopilot on the same account) counts against this one cap.
        if not token:
            return 2
        return {"room": 0, "full": 1}.get(room_status(token, data["daily_cap"]), 2)
    weather = None if args.offline else tomorrow_weather(data["series"]["lumiweather_tomorrow"], day)
    chosen = plan(day, data, weather, planned_clip(day))
    if args.command == "preview":
        print(json.dumps(chosen, ensure_ascii=False, indent=1) if chosen else "fallback: planned hook clip")
        return 0
    if not token:
        print("missing THREADS_TOKEN", file=sys.stderr)
        return 1
    if not has_room(token, data["daily_cap"]):
        _output("fallback", "none")
        return 0
    if chosen is None:
        _output("fallback", "clip")
        return 0
    import threads_post
    uid = os.environ.get("THREADS_USER_ID", "").strip()
    try:
        with urllib.request.urlopen(f"https://graph.threads.net/v1.0/me?fields=id&access_token={token}", timeout=30) as r:
            uid = json.loads(r.read()).get("id") or uid
    except Exception as error:
        print(f"series: could not resolve the token's account ({error.__class__.__name__})", file=sys.stderr)
    post_id = threads_post.publish_post(token, uid, chosen["text"], image_url=chosen.get("image_url"))
    print(f"series: posted {chosen['series']} {chosen['app']} id {post_id}")
    try:
        threads_post.publish_post(token, uid, threads_post.queued_links(chosen), reply_to=post_id)
    except Exception as error:  # the post is out; only the link reply failed
        print(f"series: link reply failed: {error}", file=sys.stderr)
    _output("fallback", "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
