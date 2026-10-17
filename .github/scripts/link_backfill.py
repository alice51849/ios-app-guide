#!/usr/bin/env python3
"""Add the missing direct download link under OUR OWN Instagram / Threads posts (self-healing sweeper).

Owner rule (2026-10-17): every promo post carries the app's direct download link. Posts that went out
without one (Instagram Reels captions had "Link in bio" only; a Threads link reply that failed; the August
Threads listing posts) cannot be edited through the API, so the link goes in a comment / reply under our
own post:

- audit: list our posts, resolve the app each one promotes (clips.json + clip-posts.json, the App Store id
  in the text, then the app names in the text), and write a report of which posts have the link (caption,
  or our own comment / reply) and which do not. Writes nothing to the platforms.
- apply: add ONE comment (Instagram) or reply (Threads) per post that lacks it - "<Get it on the App
  Store>: <App Store URL>" plus the Google Play URL when the app is on Android; on Instagram, where a
  comment URL cannot be tapped either, first "📲 Link in bio → tap “<app>”" (ig_bio.py: the profile link
  is the hub https://open.cait518.cc/ig/) - then read the comments back and keep the receipt. A post is
  only ever done once (state + a look at our own comments first).

Safety, because the Threads account was limited once for posting many linked posts:
- the newest posts come first, at most --max-new writes per channel per run, GAP seconds between writes;
- every write attempt counts (a failing one too); the first write error stops the channel for the run, and
  a post that failed MAX_FAILS times is set aside so one bad post cannot block the rest;
- a rate-limit / block answer (volume_ramp.is_throttle_error) stops the channel, nothing is forced;
- reads are paced (READ_GAP) and capped per run (--max-reads); a post whose app cannot be told is listed,
  never guessed; no write happens when the Android snapshot is missing (the Play link could not be decided);
- each receipt is saved the moment the write succeeds (atomic file replace), before the read-back.

Only the token owner's media is ever listed or written to (own_posts.py clients). Tokens are read from the
environment and never printed or written.

    python3 link_backfill.py audit                          # report only
    python3 link_backfill.py apply --max-new 3 --only 17995101140842399
    python3 link_backfill.py apply --max-new 10 --channels instagram threads
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import clip_posts as CP
import download_links as DL
import ig_bio as IGB
import ig_bio_hub as HUB
import own_posts as OP
import volume_ramp
from social_post_common import android_apps, campaign_app_store_url, play_store_url

GROWTH = OP.GROWTH
STATE = GROWTH / "link-backfill.json"
REPORT = GROWTH / "link-backfill-report.json"
CT = {"instagram": "bf_ig", "threads": "bf_th"}   # reply-style attribution, one token per channel
GAP = 20          # seconds between two writes
READ_GAP = 1.0    # seconds between two comment reads
PAGES = 40        # 40 x 50 = the 2000 newest posts of a channel (the whole history of these accounts)
AUDIT_READS = 2000   # comment reads per channel in an audit run
APPLY_READS = 150    # ... and in an apply run (it stops at --max-new writes anyway)
MAX_FAILS = 2     # a post whose comment failed this often is set aside
SKIP_TYPES = {"REPOST_FACADE"}   # a repost shell is not our own post
DAILY_CAP = {"instagram": 6, "threads": 6}   # links added per channel in any 24 hours (a slow drip, never a burst)
# Threads limited the account once for posting many linked posts (30-48 a day). Every post and reply of the
# account that carries a store link counts, whoever wrote it (comment_replies, the series, this sweeper):
# the sweeper only adds what still fits under this ceiling.
LINK_BUDGET_24H = {"threads": 20}


def load_state(path=STATE):
    state = OP.load_json(path, {})
    for key in ("done", "checked", "failed"):
        state.setdefault(key, {})
    return state


def save_state(state, path=STATE):
    """Atomic: a crash in the middle never leaves half a receipt file."""
    path = Path(path)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def list_media(client, pages=PAGES, limit=50):
    """Our own newest posts (id, text/caption, permalink, timestamp), paged."""
    path = f"{client.user_id}/media" if client.channel == "instagram" else f"{client.user_id}/threads"
    fields = ("id,caption,permalink,timestamp,media_type" if client.channel == "instagram"
              else "id,text,permalink,timestamp,media_type")
    out, after = [], None
    for _ in range(pages):
        params = {"fields": fields, "limit": limit}
        if after:
            params["after"] = after
        resp = client._get(path, **params)
        for row in resp.get("data", []):
            if row.get("media_type") in SKIP_TYPES:
                continue
            out.append(dict(row, caption=row.get("caption") or row.get("text") or ""))
        after = ((resp.get("paging") or {}).get("cursors") or {}).get("after")
        if not after or not (resp.get("paging") or {}).get("next"):
            break
    return out


# ---------------------------------------------------------------- which app does a post promote

SPLIT = re.compile(r"[:：（）()\-–—・|／/·,，]")
PAREN = re.compile(r"[（(]([^）)]+)[）)]")
QUALIFIERS = {"pro", "plus", "lite", "max", "mini", "premium", "free", "ultra"}
LATIN_THEN_CJK = re.compile(r"(?<=[A-Za-z0-9])\s+(?=[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af])")


def squash(text):
    """Casefolded, without the blank between a Latin word and CJK text: "Lumi 數學星球" and "Lumi數學星球" are one name."""
    return LATIN_THEN_CJK.sub("", text.casefold())


def brands(name):
    """(exact, derived) names a post may use for the app. Exact: the store name, its main name (before the first
    delimiter), the main name's leading Latin run, and the same for the name in brackets ("Lumi Math Pro" in
    "...（Lumi Math Pro）"). Derived: the main name without a trailing Pro / Lite / Plus ("Unblurry Pro" ->
    "Unblurry"), which only counts while no other app has it as an exact name. Subtitle words are descriptive
    ("Face ID Lock", "Event Counter") and shared between apps, so they are not names."""
    name = name.strip()
    exact, derived = {name}, set()
    for part in [PAREN.sub("", name).strip()] + [m.strip() for m in PAREN.findall(name)]:
        if not part:
            continue
        exact.add(part)
        main = SPLIT.split(part, maxsplit=1)[0].strip()
        if len(main) >= 4:
            exact.add(main)
        lead = re.match(r"^[A-Za-z0-9+&' ]+", main)
        if lead and len(lead.group(0).strip()) >= 5:
            exact.add(lead.group(0).strip())
        words = main.split()
        if len(words) >= 2 and words[-1].casefold() in QUALIFIERS and len(" ".join(words[:-1])) >= 4:
            derived.add(" ".join(words[:-1]))
    return exact, derived


LEDGER_CHANNELS = {"instagram": ("instagram", "instagram_feed")}   # a feed carousel is logged under its own channel
MIN_LEAD = 10    # a hook line shorter than this proves nothing


class AppFinder:
    """Resolves the app a post promotes, and never guesses (a wrong app's link is worse than none).

    Evidence, strongest first: the post ledger (exact post id / link); the App Store id in the text; one of our
    brands in the text (the store names, in every language our captions use; a brand two apps share, a brand
    followed by Lite / Pro / Plus, and a brand inside a longer brand count for nothing); a hook line only one
    app uses. A text whose evidence points at two apps - or at an app we do not know ("<brand> Plus") - stays
    unknown: it is listed, not touched."""

    def __init__(self, catalog):
        self.catalog = catalog
        self.by_id = {str(ios): (key, name) for name, key, ios in catalog.apps if ios}   # iOS id -> (app key, name)
        exact, derived = {}, {}   # squashed brand -> {iOS id}: an app is told apart by its iOS id, whatever key a clip set uses
        for name, key, ios in catalog.apps:
            if not ios:
                continue
            e, d = brands(name)
            for b in e:
                exact.setdefault(squash(b), set()).add(str(ios))
            for b in d:
                derived.setdefault(squash(b), set()).add(str(ios))
        leads = {}    # squashed hook line -> {iOS id}
        for clip in catalog.clips.values():
            ios = OP.ios_id_of(clip.get("store_url"))
            if not ios:
                continue
            self.by_id.setdefault(ios, (re.sub(r"_[a-z]$", "", clip["app"]), clip.get("name", "")))
            for whole in (clip.get("name"), clip.get("search")):   # the exact names our captions carry, in every language
                if whole and len(whole.strip()) >= 5:
                    exact.setdefault(squash(whole.strip()), set()).add(ios)
            for lead in [clip.get("hook")] + [h.get("lead") for h in clip.get("hooks") or []]:
                if lead and len(lead.strip()) >= MIN_LEAD:
                    leads.setdefault(squash(lead.strip()), set()).add(ios)
        owners = dict(derived)
        owners.update(exact)      # an exact name beats the same word derived from another app's name
        self.brands = sorted(((b, next(iter(o))) for b, o in owners.items() if len(o) == 1), key=lambda x: -len(x[0]))
        self.leads = {l: next(iter(o)) for l, o in leads.items() if len(o) == 1}

    def _ledger(self, channel, media):
        for ch in LEDGER_CHANNELS.get(channel, (channel,)):
            for k in (media.get("id"), media.get("permalink")):
                p = self.catalog.logged.get((ch, str(k or "").rstrip("/")))
                if p and p["clip"].startswith("feed/"):   # feed/<app>/<locale>: a store-screenshot carousel
                    parts = p["clip"].split("/")
                    return {"app": parts[1], "locale": parts[-1], "hook": "", "ios_id": "", "kind": "feed",
                            "clip": p["clip"], "why": "ledger"}
                if p:
                    return dict(self.catalog._clip(p["clip"], variant=p.get("variant")), posted_at=p.get("posted_at"),
                                why="ledger")
        return None

    def resolve(self, channel, media):
        post = self._ledger(channel, media)
        if post and ios_id_for(self.catalog, post):
            return post
        text = media.get("caption") or ""
        found = [(why, e) for why, e in (("url", self._by_url(text)), ("brand", self._by_brand(text)),
                                         ("hook", self._by_lead(text))) if e is not None]
        evidence = [e for _why, e in found]
        if not evidence or False in evidence or len(set(evidence)) != 1:
            return None   # nothing to go on, two apps in one text, or the proofs disagree
        ios = evidence[0]
        first = next((line for line in text.splitlines() if line.strip()), "")
        return {"app": self.by_id[ios][0], "locale": OP.detect_language(text) or "en", "hook": first[:60],
                "ios_id": ios, "kind": "image", "clip": None, "why": "+".join(w for w, _e in found)}

    # Each _by_* answers None (no evidence), False (evidence for more than one app) or the app's iOS id.

    def _by_url(self, text):
        ids = DL.store_ids_in(text)
        if not ids:
            return None
        known = {i for i in ids if i in self.by_id}
        if len(known) != len(ids):   # it links an App Store page that is not one of ours: the text is about something else
            return False
        return next(iter(known)) if len(known) == 1 else False

    def _hits(self, text):
        """([(start, end, iOS id)], [(start, end)]): where a brand stands in the text, and where one stands
        directly before Pro / Lite / Plus (a product that name does not say)."""
        out, skipped = [], []
        for b, ios in self.brands:
            start = 0
            while True:
                i = text.find(b, start)
                if i < 0:
                    break
                j = i + len(b)
                before = i == 0 or not (b[0].isascii() and b[0].isalnum() and text[i - 1].isascii() and text[i - 1].isalnum())
                after = j >= len(text) or not (b[-1].isascii() and b[-1].isalnum() and text[j].isascii() and text[j].isalnum())
                if before and after:
                    rest = text[j:].lstrip(" :：-")
                    word = re.split(r"[\s:：,，.。]", rest, maxsplit=1)[0] if rest else ""
                    if word not in QUALIFIERS:
                        out.append((i, j, ios))
                    else:
                        skipped.append((i, j))
                start = i + 1
        return out, skipped

    def _by_brand(self, text):
        low = squash(re.sub(r"^[\W_]+", "", text.strip(), flags=re.U))
        hits, skipped = self._hits(low)
        # a brand inside a longer brand ("Mochi" in "Mochi DoneStamp") is not a second app
        keep = [h for h in hits if not any(o[0] <= h[0] and h[1] <= o[1] and (o[1] - o[0]) > (h[1] - h[0]) for o in hits)]
        # "<brand> Plus" that no longer name of ours covers is a product we do not know: the text is not about the
        # app that shares its first word, even when that word stands alone somewhere else in it
        if any(not any(o[0] <= s[0] and s[1] <= o[1] and (o[1] - o[0]) > (s[1] - s[0]) for o in hits) for s in skipped):
            return False
        found = {h[2] for h in keep}
        if not found:
            return None
        return next(iter(found)) if len(found) == 1 else False

    def _by_lead(self, text):
        low = squash(re.sub(r"^[\W_]+", "", text.strip(), flags=re.U))
        owners = {owner for lead, owner in self.leads.items() if low.startswith(lead)}
        if not owners:
            return None
        return next(iter(owners)) if len(owners) == 1 else False


def ios_id_for(catalog, post):
    """The iOS app id a resolved post promotes ('' when unknown)."""
    if not post:
        return ""
    if post.get("ios_id"):
        return str(post["ios_id"])
    key = post.get("app")
    for _name, app_key, ios in catalog.apps:
        if app_key == key and ios:
            return str(ios)
    return ""


# ---------------------------------------------------------------- links and comments

def links_for(channel, ios_id):
    ct = CT[channel]
    return campaign_app_store_url(f"https://apps.apple.com/app/id{ios_id}", ct), play_store_url(ios_id, ct)


def comment_text(locale, store, play, missing_store=True, channel=None, name=""):
    """The links under a post; on Instagram (where a comment URL cannot be tapped either) first the line that
    says where to tap: "📲 Link in bio → tap “<app>”" (ig_bio.py, the profile-link hub)."""
    t = CP.text_for(locale or "en")
    lines = []
    if channel == "instagram" and name:
        lines.append(IGB.bio_line(locale or "en", name, t["bio"]))
    if missing_store:
        lines.append(f"{t['button']}: {store}")
    if play:
        lines.append(f"{CP.PLAY_LINE.get(locale) or CP.PLAY_LINE.get((locale or 'en').split('-')[0]) or CP.PLAY_LINE['en']}: {play}")
    return "\n".join(lines)


def own_comments(client, media_id):
    rows = client.comments(media_id)
    me = (client.username or "").lower()
    return [r for r in rows if r.get("own") or (r.get("user") or "").lower() == me]


def is_throttle(exc):
    """The platform says slow down / blocked (also volume_ramp's wider list of words and codes)."""
    if isinstance(exc, OP.ApiError) and (exc.code in volume_ramp.THROTTLE_CODES or exc.status == 429):
        return True
    return volume_ramp.is_throttle_error(exc)


CHECK_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.0 Safari/605.1.15")
_URL_SEEN = {}


def url_ok(url, opener=None, timeout=20, seen=None):
    """(True, note) when a GET of `url` (redirects followed) answers HTTP 200, else (False, why). A store page
    that the store refuses to a script (403 / 429 / 5xx) is accepted when the iTunes lookup knows its app id;
    a 404 is never accepted, and trouble reaching the page is "not known to be fine", never a pass. The answer
    is kept for the run: a link is looked at once."""
    seen = _URL_SEEN if seen is None else seen
    if url in seen:
        return seen[url]
    opener = opener or urllib.request.urlopen
    status, note = None, ""
    try:
        request = urllib.request.Request(url, headers={"User-Agent": CHECK_UA, "Accept": "text/html,*/*"})
        with opener(request, timeout=timeout) as response:
            status = getattr(response, "status", None) or response.getcode()
    except urllib.error.HTTPError as exc:
        status = exc.code
        exc.close()
    except Exception as exc:   # network trouble: the class only (a URL can carry a token)
        note = exc.__class__.__name__
    if status == 200:
        out = (True, "HTTP 200")
    else:
        out = (False, f"HTTP {status}" if status else (note or "no answer"))
        found = re.search(r"apps\.apple\.com/(?:[^?#]*/)?id(\d+)", url)
        if found and status not in (404, 410):
            try:
                with opener(f"https://itunes.apple.com/lookup?id={found.group(1)}&country=us", timeout=timeout) as response:
                    if json.loads(response.read()).get("resultCount", 0) >= 1:
                        out = (True, f"{out[1]}, the app id is in the iTunes lookup")
            except Exception:   # noqa: BLE001 - the lookup is only a second opinion
                pass
    seen[url] = out
    return out


URL_CHECK = url_ok   # the tests replace it: nothing here may reach the network there


def write_link(client, media_id, text):
    if client.channel == "instagram":
        return client._post(f"{media_id}/comments", message=text).get("id")
    return client.reply(media_id, text)


def has_link_now(client, media, store, play):
    """(carries the link, text we looked at): the caption (Instagram) plus our own comments / replies."""
    mine = own_comments(client, media["id"])
    text = " ".join(c.get("text", "") for c in mine) + "\n" + (media.get("caption") or "")
    return DL.has_download_link(text, store, play), text


def comment_exists(client, comment_id):
    """True when the comment we wrote can be fetched by its own id. Instagram answers an empty object for the
    account's own comment (its text is not shown to us) and error 100 for an id that does not exist. Together with
    the post's count going up this rules out that somebody else's comment was taken for ours."""
    if not comment_id:
        return False
    try:
        client._get(str(comment_id), fields="id")
        return True
    except OP.ApiError as exc:
        if is_throttle(exc):
            raise
        return False


def comments_count(client, media_id):
    """How many comments the platform says an Instagram post has (None: unknown). The comments list of a post
    does not show the account's own comments, the count does - it is the read-back for a comment we wrote."""
    if client.channel != "instagram":
        return None
    try:
        return int(client._get(str(media_id), fields="comments_count").get("comments_count"))
    except (OP.ApiError, TypeError, ValueError) as exc:
        if isinstance(exc, OP.ApiError) and is_throttle(exc):
            raise
        return None


def _when(value):
    try:
        return dt.datetime.strptime(str(value), "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        return None


def writes_last_day(state, channel, now):
    """Links this sweeper tried to add (a failed try counts too) in the 24 hours before `now`."""
    cutoff, n = now - dt.timedelta(hours=24), 0
    for section in ("done", "failed"):
        for d in (state.get(section, {}).get(channel) or {}).values():
            ts = _when((d.get("at") or "").replace("Z", "+0000"))
            if ts and ts >= cutoff:
                n += 1
    return n


def link_writes_last_day(client, media, now):
    """Posts and replies of the account in the last 24 hours that carry a store link, whoever wrote them
    (None: could not be counted - the caller then writes nothing)."""
    cutoff = now - dt.timedelta(hours=24)

    def recent(rows):
        n = 0
        for r in rows:
            ts = _when(r.get("timestamp"))
            text = r.get("text") or r.get("caption") or ""
            if ts and ts >= cutoff and ("apps.apple.com" in text or "play.google.com" in text):
                n += 1
        return n
    try:
        replies = client._get(f"{client.user_id}/replies", fields="id,text,timestamp", limit=100).get("data", [])
    except Exception as exc:
        if is_throttle(exc):
            raise
        return None
    return recent(media) + recent(replies)


def _short(text, n):
    return " ".join((text or "").split())[:n]


def classify(client, media, finder, state, reads=None, read_gap=0, sleeper=time.sleep):
    """One audit row: what this post promotes and whether it already carries the link.
    `reads` = {"n": comment reads so far, "max": budget}; a read that would exceed it leaves the post unchecked."""
    channel, pid = client.channel, str(media["id"])
    text = media.get("caption") or ""
    row = {"channel": channel, "id": pid, "permalink": media.get("permalink", ""),
           "date": (media.get("timestamp") or "")[:10], "app": "", "status": "", "text": _short(text, 140)}
    post = finder.resolve(channel, media)
    ios = ios_id_for(finder.catalog, post)
    row["app"] = (post or {}).get("app", "")
    row["why"] = (post or {}).get("why", "")   # which evidence named the app (ledger / url / brand / hook)
    if not ios:
        row["status"] = "unknown_app"
        return row, None
    store, play = links_for(channel, ios)
    row["ios_id"] = ios
    row["locale"] = (post or {}).get("locale") or OP.detect_language(text) or "en"
    # Instagram carries the links in the caption; Threads keeps them in the first reply on purpose (but a
    # Threads text that holds them itself - older posts, autopilot posts - is complete too).
    if DL.has_download_link(text, store, play):
        row["status"] = "ok_caption"
        return row, None
    if DL.has_app_store_link(text, store):   # an older post: the App Store link is the direct download, no second round for Play
        row["status"] = "ok_store_only"
        return row, None
    done = state["done"].get(channel, {}).get(pid)
    cached = state["checked"].get(channel, {}).get(pid)
    if cached and not done:
        row["status"] = cached
        return row, None
    failed = state["failed"].get(channel, {}).get(pid) or {}
    if failed.get("n", 0) >= MAX_FAILS and not done:
        row["status"] = "write_failed_skipped"
        row["error"] = failed.get("last", "")
        return row, None
    if done and done.get("verified"):
        row["status"] = "ok_backfilled_earlier"
        return row, None
    if reads is not None and reads["n"] >= reads["max"]:
        row["status"] = "not_checked"
        return row, None
    if reads is not None:
        reads["n"] += 1
    listed = client.comments(media["id"])
    me = (client.username or "").lower()
    mine = [r for r in listed if r.get("own") or (r.get("user") or "").lower() == me]
    if read_gap:
        sleeper(read_gap)
    seen = " ".join(c.get("text", "") for c in mine) + "\n" + text
    foreign = DL.store_ids_in(seen) - {ios}
    if foreign:   # the post or our own comment already links another app (even one that is not in the catalog)
        row["status"] = "unknown_app"
        row["why"] = f"{row.get('why', '')} | conflict: id{', id'.join(sorted(foreign))} already linked under the post"
        state["checked"].setdefault(channel, {})[pid] = row["status"]
        return row, None
    if DL.has_download_link(seen, store, play):
        if done:  # the comment we wrote is there: verified now
            done["verified"] = True
            row["status"] = "ok_backfilled_earlier"
        else:
            row["status"] = "ok_comment" if channel == "instagram" else "ok_reply"
            state["checked"].setdefault(channel, {})[pid] = row["status"]  # never read this post again
        return row, None
    if not done and DL.has_app_store_link(seen, store):   # our own older reply has the App Store link: enough
        row["status"] = "ok_store_only"
        state["checked"].setdefault(channel, {})[pid] = row["status"]
        return row, None
    if done:  # written earlier but the list does not show it: the post's comment count is the proof, never write a second one
        count = comments_count(client, media["id"])
        if (count is not None and count >= int(done.get("count_before") or 0) + 1
                and comment_exists(client, done.get("comment_id"))):
            done["verified"] = True
            row["status"] = "ok_backfilled_earlier"
            return row, None
        row["status"] = "backfilled_unverified"
        return row, None
    if channel == "instagram":   # the list of an Instagram post hides the account's own comments, the count does not
        count = comments_count(client, media["id"])
        if count is None:   # cannot tell whether a comment of ours is hidden from the list: never write on a guess
            row["status"] = "read_failed:count"
            return row, None
        if count > len(listed):   # (replies under other people's comments count too: those posts wait, they are listed)
            row["status"] = "unlisted_comments"   # one of them may be a link we wrote earlier: never a second one
            return row, None
    row["status"] = "missing"
    row["own_replies"] = [_short(c.get("text", ""), 100) for c in mine][:3]
    return row, {"store": store, "play": play, "missing_store": not DL.has_app_store_link(seen, store),
                 "missing_play": bool(play) and not DL.has_play_link(seen, play)}


def run(client, catalog, state, *, apply=False, max_new=5, only=None, sleeper=time.sleep, gap=GAP, read_gap=0,
        log=print, pages=PAGES, now=None, max_reads=None, save=None):
    """Audit (and with apply=True fix) one channel. Returns the report rows."""
    channel = client.channel
    now = now or dt.datetime.now(dt.timezone.utc)
    finder = catalog if isinstance(catalog, AppFinder) else AppFinder(catalog)
    reads = {"n": 0, "max": max_reads if max_reads is not None else (APPLY_READS if apply else AUDIT_READS)}

    def persist():
        if save:
            save(state)

    try:
        client.me()
        media = list_media(client, pages=pages)
    except Exception as exc:
        log(f"::warning::{channel}: listing our posts failed, skipped ({exc})")
        return [{"channel": channel, "id": "", "status": f"list_failed:{getattr(exc, 'code', 'x')}"}]
    allowed = max_new
    if apply:   # a slow drip: the 24-hour caps first, the rest of the run's batch after
        allowed = min(max_new, max(DAILY_CAP.get(channel, max_new) - writes_last_day(state, channel, now), 0))
        if allowed and channel in LINK_BUDGET_24H:
            try:
                used = link_writes_last_day(client, media, now)
            except Exception as exc:
                log(f"::warning::{channel}: counting the account's links failed ({str(exc)[:100]}); nothing is added now")
                used = None
            if used is None:
                allowed = 0
            else:
                allowed = min(allowed, max(LINK_BUDGET_24H[channel] - used, 0))
        if allowed < max_new:
            log(f"{channel}: {allowed} of {max_new} link(s) fit under the 24-hour limits")
    rows, attempts = [], 0
    for m in media:
        if only and str(m["id"]) not in only:
            continue
        if apply and attempts >= allowed:
            break  # the batch is used up: the rest keeps its previous status
        try:
            row, todo = classify(client, m, finder, state, reads, read_gap=read_gap, sleeper=sleeper)
        except Exception as exc:
            if is_throttle(exc):
                log(f"::warning::{channel}: the platform says slow down ({exc}); stopping here")
                rows.append({"channel": channel, "id": str(m.get("id")), "status": "throttled"})
                break
            row, todo = {"channel": channel, "id": str(m.get("id")), "status": f"read_failed:{getattr(exc, 'code', 'x')}"}, None
            if isinstance(exc, OP.ApiError) and exc.permission:
                log(f"::warning::{channel}: cannot read comments ({exc}); stopping here")
                rows.append(row)
                break
        rows.append(row)
        if not todo or not apply:
            continue
        if not android_apps():  # the Play link could not be decided: never write half a link
            row["status"] = "snapshot_missing"
            log(f"::error::{channel}: the Android snapshot is empty; nothing is written")
            break
        needed = ([todo["store"]] if todo["missing_store"] else []) + \
            ([todo["play"]] if todo["missing_play"] and todo["play"] else [])
        dead = []
        for link in needed:   # a link goes under a post only while its page answers HTTP 200
            good, why = URL_CHECK(link)
            if not good:
                dead.append(f"{link.split('?')[0]} ({why})")
        if dead:
            row["status"] = "link_unreachable"
            row["error"] = "; ".join(dead)[:200]
            log(f"::warning::{channel}: nothing written under {row['id']}: {row['error']} does not answer HTTP 200 "
                "now; the next sweep looks again")
            continue
        attempts += 1
        name = ""
        if channel == "instagram":   # the app as the profile-link hub shows it in the post's language
            name = HUB.display_name(row.get("ios_id"), row.get("locale")) or \
                (finder.by_id.get(str(row.get("ios_id") or "")) or ("", ""))[1]
        text = comment_text(row.get("locale"), todo["store"], todo["play"] if todo["missing_play"] else None,
                            todo["missing_store"], channel=channel, name=name)
        try:
            before = comments_count(client, row["id"])   # the read-back of an Instagram comment is the count going up
            if channel == "instagram" and before is None:   # without the count nothing can be read back: write nothing
                row["status"] = "read_failed:count"
                attempts -= 1
                continue
            new_id = write_link(client, row["id"], text)
        except Exception as exc:
            row["status"] = f"write_failed:{getattr(exc, 'code', 'x')}"
            row["error"] = str(exc)[:160]
            fail = state["failed"].setdefault(channel, {}).setdefault(row["id"], {"n": 0})
            fail["n"] += 1
            fail["last"] = row["status"]
            fail["at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
            persist()
            log(f"::warning::{channel}: writing under {row['id']} failed ({str(exc)[:120]}); stopping this channel for now")
            break
        at = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        receipt = state["done"].setdefault(channel, {})[row["id"]] = {
            "at": at, "comment_id": str(new_id or ""), "app": row["app"], "verified": False, "count_before": before}
        persist()  # the receipt is safe on disk before the read-back
        verified, via = False, ""
        try:
            for _ in range(3):  # read it back: the link must really be under the post
                sleeper(5)
                verified, _seen = has_link_now(client, m, todo["store"], todo["play"])
                via = "list" if verified else ""
                if not verified and before is not None:
                    count = comments_count(client, row["id"])
                    verified = count is not None and count >= before + 1 and comment_exists(client, new_id)
                    via = "count" if verified else ""
                if verified:
                    break
        except Exception as exc:
            log(f"::warning::{channel}: read-back of {row['id']} failed ({str(exc)[:100]}); checked again on the next sweep")
        receipt["verified"], receipt["via"] = verified, via
        persist()
        row.update(status="backfilled" if verified else "backfilled_unverified", comment_id=receipt["comment_id"],
                   at=at, verified=verified, via=via)
        log(f"{channel}: link added under {row['id']} ({row['app']}) verified={verified}")
        sleeper(gap)
    persist()
    return rows


def diag(client, state, only, finder=None, out=print):
    """Read-only: what the platform answers about the given posts and about the comments we wrote under them,
    and which app the finder takes each post for. Prints public text and ids only (never a token)."""
    channel = client.channel
    out(f"diag {channel}: token owner = {client.username}")
    for pid in only:
        pid = str(pid)
        fields = ("id,caption,permalink,comments_count,is_comment_enabled" if channel == "instagram"
                  else "id,text,permalink,has_replies")
        try:
            info = client._get(pid, fields=fields)
        except Exception as exc:
            info = {"error": str(exc)[:160]}
        text = info.get("caption") or info.get("text") or ""
        out(f"diag {channel} {pid}: {_short(json.dumps({k: v for k, v in info.items() if k not in ('caption', 'text')}, sort_keys=True), 200)}")
        out(f"diag {channel} {pid}: text = {_short(text, 500)}")
        if finder is not None and text:
            post = finder.resolve(channel, {"id": pid, "permalink": info.get("permalink", ""), "caption": text})
            out(f"diag {channel} {pid}: the finder says app={(post or {}).get('app', '-')} why={(post or {}).get('why', '-')}")
        try:
            raw = client._get(f"{pid}/comments" if channel == "instagram" else f"{pid}/replies",
                              fields="id,text,username,timestamp", limit=50).get("data", [])
        except Exception as exc:
            out(f"diag {channel} {pid}: the list failed ({str(exc)[:160]})")
            raw = []
        out(f"diag {channel} {pid}: the list shows {len(raw)} comments")
        for c in raw[:12]:
            out(f"  {c.get('id')} user={c.get('username')} text={_short(c.get('text'), 100)}")
        cid = ((state["done"].get(channel) or {}).get(pid) or {}).get("comment_id")
        if cid:   # an id of ours, then the same id with the last digit changed (an object that does not exist)
            for label, probe, fields in (("ours", cid, "id"), ("ours", cid, "id,text"), ("ours", cid, "id,text,username,timestamp,hidden"),
                                         ("not ours", cid[:-1] + str((int(cid[-1]) + 1) % 10), "id")):
                try:
                    one = client._get(probe, fields=fields)
                    out(f"diag {channel} {pid}: {label} comment {probe} fields={fields} -> {_short(json.dumps(one, ensure_ascii=False, sort_keys=True), 300)}")
                except Exception as exc:
                    out(f"diag {channel} {pid}: {label} comment {probe} fields={fields} failed ({str(exc)[:160]})")
    if channel == "instagram":   # does the list work at all for this token? look at posts that report comments
        try:
            rows = client._get(f"{client.user_id}/media", fields="id,comments_count,timestamp", limit=50).get("data", [])
            with_comments = [r for r in rows if (r.get("comments_count") or 0) > 0][:4]
            out(f"diag instagram: {len(rows)} newest posts, {len(with_comments)} shown that report comments")
            for r in with_comments:
                seen = client._get(f"{r['id']}/comments", fields="id,username", limit=50).get("data", [])
                out(f"  {r['id']} comments_count={r.get('comments_count')} the list shows {len(seen)} "
                    f"users={[c.get('username') for c in seen][:5]}")
        except Exception as exc:
            out(f"diag instagram: the sanity look failed ({str(exc)[:160]})")


def merge_state(saved_path, path=STATE):
    """Fold a run's state into the current file (the workflow resets to origin/main before it commits)."""
    saved, state = OP.load_json(saved_path, {}), load_state(path)
    for section in ("done", "checked", "failed"):
        for channel, rows in (saved.get(section) or {}).items():
            have = state[section].setdefault(channel, {})
            for pid, entry in rows.items():
                old = have.get(pid)
                if old is None or section == "checked":
                    have[pid] = entry
                elif section == "failed":   # the higher failure count, then the later try, wins
                    have[pid] = entry if (entry.get("n", 0), entry.get("at", "")) >= (old.get("n", 0), old.get("at", "")) else old
                else:   # done: a verified receipt stays verified; otherwise the later write wins
                    keep_new = (bool(entry.get("verified")), entry.get("at", "")) >= (bool(old.get("verified")), old.get("at", ""))
                    have[pid] = entry if keep_new else old
    save_state(state, path)


def merge_rows(previous, new):
    """The newest status of every post: this run's rows over the previous report's."""
    merged = {(r.get("channel"), r.get("id")): r for r in previous if r.get("id")}
    for r in new:
        if r.get("id"):
            merged[(r["channel"], r["id"])] = r
    markers = [r for r in new if not r.get("id")]  # list_failed markers
    return sorted(merged.values(), key=lambda r: (r["channel"], r.get("date", ""), r["id"]), reverse=True) + markers


def summarize(rows):
    counts = {}
    for r in rows:
        key = r["status"].split(":")[0]
        counts[key] = counts.get(key, 0) + 1
    return counts


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["audit", "apply", "merge", "diag"])
    ap.add_argument("--state-from", help="merge: the state file a run saved")
    ap.add_argument("--channels", nargs="+", default=["instagram", "threads"], choices=["instagram", "threads"])
    ap.add_argument("--max-new", type=int, default=5, help="links added per channel per run")
    ap.add_argument("--max-reads", type=int, default=None, help="comment reads per channel per run")
    ap.add_argument("--only", nargs="*", default=None, help="only these post ids (a small first batch)")
    ap.add_argument("--pages", type=int, default=PAGES)
    ap.add_argument("--report", default=str(REPORT))
    args = ap.parse_args(argv)
    if args.cmd == "merge":
        merge_state(args.state_from)
        return 0
    if not android_apps():
        print("::error::link_backfill: the Android snapshot is empty or unreadable; the Play link cannot be decided, stopping")
        return 1
    apply = args.cmd == "apply"
    finder = AppFinder(OP.Catalog())
    state = load_state()
    tokens = {"instagram": os.environ.get("IG_ACCESS_TOKEN", "").strip(), "threads": os.environ.get("THREADS_TOKEN", "").strip()}
    clients = {"instagram": OP.InstagramClient, "threads": OP.ThreadsClient}
    if args.cmd == "diag":   # read-only: what the platform answers about the given posts and our comments (public text only)
        for channel in args.channels:
            if tokens[channel]:
                diag(clients[channel](tokens[channel]).me(), state, args.only or [], finder=finder)
        return 0
    rows = []
    for channel in args.channels:
        if not tokens[channel]:
            print(f"link_backfill: {channel} token not set, skipped")
            continue
        rows += run(clients[channel](tokens[channel]), finder, state, apply=apply, max_new=args.max_new,
                    only=set(args.only) if args.only else None, pages=args.pages, max_reads=args.max_reads,
                    read_gap=READ_GAP, save=save_state if apply else None)
    full_scan = not apply and not args.only and set(args.channels) == {"instagram", "threads"}
    previous = (OP.load_json(args.report, {}) or {}).get("rows", [])
    merged = rows if full_scan else merge_rows(previous, rows)
    counts = summarize(merged)
    if full_scan or merged != previous:   # a sweep that found nothing new leaves the report (and git) alone
        report = {"generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "mode": args.cmd,
                  "counts": counts, "rows": merged}
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    save_state(state)   # receipts, plus the posts an audit found already linked (never read again)
    print(f"link_backfill {args.cmd}: {counts}")
    todo = [r for r in rows if r["status"] in ("missing", "unknown_app", "not_checked", "unlisted_comments",
                                              "link_unreachable")
            or r["status"].startswith(("write_failed", "backfilled_unverified"))]
    for r in todo[:40]:
        print(f"  {r['channel']} {r['id']} {r.get('date', '')} {r.get('app', '')} {r['status']}")
    failed = [r for r in rows if r["status"].startswith("write_failed:") or r["status"] == "snapshot_missing"]
    return 1 if failed else 0   # a write error is an alert (the sweeper itself is the auto-fix); a throttle is not


if __name__ == "__main__":
    sys.exit(main())
