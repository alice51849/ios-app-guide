#!/usr/bin/env python3
"""Shared helpers for reading OUR OWN Instagram / Threads posts.

Used by comment_replies.py (template replies under our posts) and
post_performance.py (insights ranking). Only the token owner's media is ever
listed, so nothing here can touch a stranger's post.

- InstagramClient / ThreadsClient: tiny Graph API wrappers (urllib, no deps).
- ApiError.permission: the token lacks a scope (insights, comments) -> callers
  log and skip instead of failing the workflow.
- Catalog.resolve(): which app / locale / hook a post promotes, from
  clips.json + clip-posts.json (clip posts) or the app names on the
  promotion page (picture posts).
- detect_language(): script-based guess (zh-Hant, ja, ko, th, vi, en).
"""
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
GROWTH = HERE.parent / "growth"
UA = "lumi-social-loop/1.0"
IG_GRAPH = "https://graph.instagram.com/v21.0"
THREADS_GRAPH = "https://graph.threads.net/v1.0"


class ApiError(Exception):
    def __init__(self, status, code, message):
        super().__init__(f"HTTP {status} code {code}: {message}")
        self.status, self.code, self.message = status, code, message or ""

    @property
    def permission(self):
        """Missing scope / app review / expired token: skip, never crash."""
        msg = self.message.lower()
        return (self.code in (10, 190, 200, 3) or self.status in (401, 403)
                or "permission" in msg or "scope" in msg or "not authorized" in msg)


def _open(req, timeout):
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as exc:
        try:
            err = json.loads(exc.read() or b"{}").get("error", {})
        except ValueError:
            err = {}
        raise ApiError(exc.code, err.get("code"), err.get("message", exc.reason)) from None


def http_get(url, params, timeout=30):
    return _open(urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}",
                                        headers={"User-Agent": UA}), timeout)


def http_post(url, fields, timeout=30):
    return _open(urllib.request.Request(url, data=urllib.parse.urlencode(fields).encode(),
                                        headers={"User-Agent": UA}), timeout)


class _Client:
    base = ""
    get = staticmethod(http_get)
    post = staticmethod(http_post)

    def __init__(self, token):
        self.token = token
        self.user_id = self.username = None

    def _get(self, path, **params):
        return self.get(f"{self.base}/{path}", dict(params, access_token=self.token))

    def _post(self, path, **fields):
        return self.post(f"{self.base}/{path}", dict(fields, access_token=self.token))

    @staticmethod
    def metrics(resp):
        """{name: int} from an insights response (values[] or total_value)."""
        out = {}
        for row in resp.get("data", []):
            if "total_value" in row:
                value = row["total_value"].get("value", 0)
            else:
                values = row.get("values") or [{}]
                value = values[-1].get("value", 0)
            out[row.get("name")] = value if isinstance(value, (int, float)) else 0
        return out


class InstagramClient(_Client):
    base = IG_GRAPH
    channel = "instagram"
    # "views" replaced "plays" in 2025; older tokens/versions may still want plays.
    METRIC_SETS = ("views,reach,likes,saved,shares,comments", "plays,reach,likes,saved,shares,comments")

    def me(self):
        me = self._get("me", fields="user_id,username")
        self.user_id, self.username = str(me.get("user_id") or me.get("id")), me.get("username")
        return self

    def media(self, limit=25):
        return self._get(f"{self.user_id}/media", fields="id,caption,permalink,timestamp,media_type",
                         limit=limit).get("data", [])

    def comments(self, media_id, limit=50):
        rows = self._get(f"{media_id}/comments", fields="id,text,username,timestamp,from,replies{username}",
                         limit=limit).get("data", [])
        out = []
        for c in rows:
            replied = [r.get("username") for r in (c.get("replies") or {}).get("data", [])]
            user = c.get("username") or (c.get("from") or {}).get("username")
            out.append({"id": c["id"], "text": c.get("text", ""), "user": user,
                        "timestamp": c.get("timestamp", ""), "we_replied": self.username in replied})
        return out

    def reply(self, comment_id, text):
        return self._post(f"{comment_id}/replies", message=text).get("id")

    def insights(self, media_id):
        last = None
        for metric in self.METRIC_SETS:
            try:
                m = self.metrics(self._get(f"{media_id}/insights", metric=metric))
            except ApiError as exc:
                if exc.permission:
                    raise
                last = exc
                continue
            return {"views": m.get("views", m.get("plays", 0)), "reach": m.get("reach", 0),
                    "likes": m.get("likes", 0), "saves": m.get("saved", 0), "shares": m.get("shares", 0),
                    "replies": m.get("comments", 0)}
        raise last


class ThreadsClient(_Client):
    base = THREADS_GRAPH
    channel = "threads"

    def me(self):
        # The token's own account (the THREADS_USER_ID secret once pointed at an old one).
        me = self._get("me", fields="id,username")
        self.user_id, self.username = str(me.get("id")), me.get("username")
        return self

    def media(self, limit=25):
        rows = self._get(f"{self.user_id}/threads", fields="id,text,permalink,timestamp,media_type",
                         limit=limit).get("data", [])
        return [dict(r, caption=r.get("text", "")) for r in rows]

    def comments(self, media_id, limit=50):
        # Top-level replies to our post only (never replies deeper in other threads).
        rows = self._get(f"{media_id}/replies", fields="id,text,username,timestamp,is_reply_owned_by_me",
                         limit=limit).get("data", [])
        return [{"id": r["id"], "text": r.get("text", ""), "user": r.get("username"),
                 "timestamp": r.get("timestamp", ""), "own": bool(r.get("is_reply_owned_by_me")),
                 "we_replied": False} for r in rows]

    def reply(self, comment_id, text):
        container = self._post(f"{self.user_id}/threads", media_type="TEXT", text=text,
                               reply_to_id=comment_id)["id"]
        return self._post(f"{self.user_id}/threads_publish", creation_id=container).get("id")

    def insights(self, media_id):
        m = self.metrics(self._get(f"{media_id}/insights", metric="views,likes,replies,reposts,quotes"))
        return {"views": m.get("views", 0), "likes": m.get("likes", 0), "replies": m.get("replies", 0),
                "reposts": m.get("reposts", 0) + m.get("quotes", 0)}


# ---------------------------------------------------------------- language

HANGUL = re.compile(r"[가-힯ᄀ-ᇿ㄰-㆏]")
KANA = re.compile(r"[぀-ヿ]")
CJK = re.compile(r"[一-鿿㐀-䶿]")
THAI = re.compile(r"[฀-๿]")
VIET = re.compile(r"[ăâđêôơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹĂÂĐÊÔƠƯ]")
OTHER_LATIN = re.compile(r"[¡¿À-ÖØ-öø-ÿ]")
LETTER = re.compile(r"[A-Za-z]")


def detect_language(text):
    """zh-Hant / ja / ko / th / vi / en, "other" for a Latin language we have
    no templates for (é, ñ, ü...), None when there are no letters at all."""
    if HANGUL.search(text):
        return "ko"
    if KANA.search(text):
        return "ja"
    if CJK.search(text):
        return "zh-Hant"
    if THAI.search(text):
        return "th"
    if VIET.search(text):
        return "vi"
    if OTHER_LATIN.search(text):
        return "other"
    if LETTER.search(text):
        return "en"
    return None


# ---------------------------------------------------------------- catalog

def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def ios_id_of(url):
    m = re.search(r"/id(\d+)", url or "")
    return m.group(1) if m else ""


class Catalog:
    """Maps one of our posts to the app / locale / hook it promotes."""

    def __init__(self, clips=None, posts=None, improvements=None):
        clips = load_json(GROWTH / "clips.json", {}) if clips is None else clips
        posts = load_json(GROWTH / "clip-posts.json", {}).get("posts", []) if posts is None else posts
        improvements = load_json(GROWTH / "app-improvements.json", {}) if improvements is None else improvements
        self.clips = clips.get("clips", {})
        self.logged = {}
        for p in posts:
            for k in (p.get("id"), p.get("link")):
                if k:
                    self.logged[(p["channel"], str(k).rstrip("/"))] = p
        self.apps = [(a["name"], a["key"], str(a.get("app_store_id", "")))
                     for a in improvements.get("apps", []) if a.get("name")]
        self.apps.sort(key=lambda a: -len(a[0]))

    def _clip(self, key, kind="clip"):
        if key.startswith("utility/"):  # utility_cards.py: utility/<type>/<app>/<item>/<locale>
            parts = key.split("/")
            return {"app": parts[2], "locale": parts[-1], "hook": "", "ios_id": "", "kind": "utility", "clip": key}
        c = self.clips.get(key)
        if not c:
            app, _, locale = key.partition("/")
            return {"app": app, "locale": locale, "hook": "", "ios_id": "", "kind": kind, "clip": key}
        return {"app": c["app"], "locale": c["locale"], "hook": c.get("hook", ""),
                "ios_id": ios_id_of(c.get("store_url")), "kind": kind, "clip": key}

    def resolve(self, channel, media):
        for k in (media.get("id"), media.get("permalink")):
            p = self.logged.get((channel, str(k or "").rstrip("/")))
            if p:
                return dict(self._clip(p["clip"]), posted_at=p.get("posted_at"))
        text = media.get("caption") or ""
        for key, c in self.clips.items():
            if c.get("hook") and c["hook"] in text:
                return self._clip(key)
        low = text.lower()
        for name, key, ios in self.apps:
            if name.lower() in low:
                first = next((line for line in text.splitlines() if line.strip()), "")
                return {"app": key, "locale": detect_language(text) or "en", "hook": first[:60],
                        "ios_id": ios, "kind": "image", "clip": None}
        return None
