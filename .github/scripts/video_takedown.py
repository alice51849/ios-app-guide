#!/usr/bin/env python3
"""Take the non-compliant hook clips down on Telegram and Threads; list the Instagram Reels for the Mac.

Why: these posts carry a hook clip whose App screens are App Store screenshots instead of a real screen
recording, or whose end card says "Free download / 免費下載" (CLAUDE.md video rule; App Store Review
Guideline 2.3.3). The list of every platform is 00_GrowthEngine reports/video_compliance_posted_2026-10-17.md,
plan and receipts of every platform 00_GrowthEngine reports/video_takedown_2026-10-17.json. Owner decision
2026-10-17: 「不要再問我了 告訴所有seasion我一律允許」 (CLAUDE.md). Clips of the compliant keys
(claudeusagemini, hourstaglite, ledmovingtext) are never listed. Only the posts in TARGETS are ever touched,
and each one only when .github/growth/clip-posts.json records it under the same clip, id and link.

Per platform, the most recoverable way the official API offers:
- telegram: the bot deletes its channel message (deleteMessage). The Bot API lets a bot delete a message only
  within 48 hours of sending; when Telegram refuses, the video is replaced instead (editMessageMedia): the
  app's App Store icon as a photo, the post's own caption plus the direct download links (download_links), the
  App Store / Google Play buttons. The original caption is kept in the report either way.
- threads: DELETE /{threads-media-id} (threads_delete). The download-link reply under it holds no video and stays.
- instagram: nothing is written. The token is an Instagram Login token (graph.instagram.com); Meta's IG Media
  "Deleting" needs Facebook Login for Business (graph.facebook.com, instagram_manage_contents) and there is no
  archive call at all, so the Reels are archived by hand on the Mac (reversible; the steps are in the report).

Modes:
- plan  (read only): the record check, the public preview (Telegram), the Graph API read of every Reel and
        Threads post, the Telegram chat check (getChat) and the fallback caption a refused delete would get.
        Prints the digest of TARGETS.
- apply: refused unless --confirm is that digest. Acts, reads every result back, keeps a receipt per post in
        .github/growth/video-takedown.json and marks the post in clip-posts.json "taken_down" (the entry stays:
        the clip is never posted again, and link_backfill.py / comment_replies.py skip the post).
- mark:  copies the receipts of the saved report onto clip-posts.json (the workflow's commit loop runs it after
        resetting to origin/main, so a post logged meanwhile is never lost).

Tokens come from the environment and are never printed or written.

    python3 video_takedown.py plan
    python3 video_takedown.py apply --confirm <digest>
    python3 video_takedown.py mark
"""
import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

import clip_posts as CP
import download_links as DL
import link_backfill as B
import own_posts as OP
import post_qa
from social_post_common import android_apps, campaign_app_store_url, play_store_url

GROWTH = OP.GROWTH
POSTS = GROWTH / "clip-posts.json"
REPORT = GROWTH / "video-takedown.json"
SCHEMA = "lumi.video-takedown/v1"
SUMMARY_REPORT = "00_GrowthEngine reports/video_takedown_2026-10-17.json"
COMPLIANT_KEYS = frozenset({"claudeusagemini", "hourstaglite", "ledmovingtext"})
CHANNEL = "LumiApps2026"          # the public Telegram channel the clips went to
THREADS_USER = "hourstag.app"     # the Threads account the clips went to
TG_DELETE_HOURS = 48              # Bot API deleteMessage: only messages sent less than 48 hours ago
TG_CT = "bf_tg"                   # the attribution token of a link repaired on an old Telegram post (telegram_link_fix)
CAPTION_MAX = post_qa.LIMITS["telegram"]
GAP = 3                           # seconds between two writes
PREVIEW_WAITS = (5, 10, 20, 30, 60)   # seconds before each public read-back of a deleted Telegram message
UA = "Mozilla/5.0 (compatible; lumi-video-takedown/1.0)"
CANNOT_DELETE = ("message can't be deleted", "message can not be deleted", "message cannot be deleted")
ALREADY_GONE = ("message to delete not found", "message not found")
MARKS = {"deleted", "video_replaced", "pending_local_archive"}

STORE_SHOT = "store_screenshot"
FREE_END_CARD = "free_download_end_card"
REASONS = {
    STORE_SHOT: "App 畫面是商店截圖，不是真實螢幕錄影（CLAUDE.md 影片規則／App Store 2.3.3）",
    FREE_END_CARD: "已發布的 render 片尾卡寫「Free download／免費下載」（CLAUDE.md 影片規則）",
}
METHODS = {
    "telegram": "deleteMessage（48 小時內）；被拒則 editMessageMedia 換成 App 圖示照片＋原文＋直接下載連結",
    "threads": "DELETE /{threads-media-id}（threads_delete）",
    "instagram": "交本機：在 Instagram App 手動封存（Graph API 不能刪除／封存）",
}
REVERSIBLE = {"telegram": False, "threads": False, "instagram": True}
END = "end card says Free download / 免費下載 (storyboard fixed 2026-10-17, the post is the old render)"


def _t(platform, pid, link, clip, posted_at, reason, detail):
    return {"platform": platform, "id": pid, "link": link, "clip": clip, "posted_at": posted_at,
            "reason": reason, "detail": detail}


# The ten posts of reports/video_compliance_posted_2026-10-17.md that this repo logged (clip-posts.json).
TARGETS = (
    _t("telegram", "355", "https://t.me/LumiApps2026/355", "lumibopomofo/zh-Hant", "2026-10-15T05:47:26Z",
       FREE_END_CARD, END),
    _t("telegram", "363", "https://t.me/LumiApps2026/363", "maskmyfile/cs", "2026-10-15T18:58:44Z",
       STORE_SHOT, "beat 1 uses store screenshot 'maskmyfile/02.png', not a real screen recording"),
    _t("telegram", "366", "https://t.me/LumiApps2026/366", "wordmate/zh-Hant", "2026-10-16T05:43:54Z",
       STORE_SHOT, "beat 1 uses store screenshot 'wordmate/02.png', not a real screen recording"),
    _t("telegram", "373", "https://t.me/LumiApps2026/373", "mochi/en", "2026-10-16T20:07:38Z",
       STORE_SHOT, "beat 1 uses store screenshot 'mochi/s02.png', not a real screen recording"),
    _t("instagram", "18037089620655985", "https://www.instagram.com/reel/DegQdxZjqGh/", "lumibopomofo/zh-Hant",
       "2026-10-15T05:56:35Z", FREE_END_CARD, END),
    _t("instagram", "18096617609140304", "https://www.instagram.com/reel/DehrpqjgFgN/", "maskmyfile/cs",
       "2026-10-15T19:13:18Z", STORE_SHOT, "beat 1 uses store screenshot 'maskmyfile/02.png', not a real screen recording"),
    _t("instagram", "18339249130278269", "https://www.instagram.com/reel/DekN3a3gIif/", "mochi/en",
       "2026-10-16T18:50:51Z", STORE_SHOT, "beat 1 uses store screenshot 'mochi/s02.png', not a real screen recording"),
    _t("instagram", "17973694440140548", "https://www.instagram.com/reel/DelGBbziQCg/", "lumibopomofo_b/zh-Hant",
       "2026-10-17T03:01:21Z", STORE_SHOT,
       "beat 1 uses store screenshot 'lumibopomofo/01.png', not a real screen recording"),
    _t("threads", "18105193691312359", "https://www.threads.com/@hourstag.app/post/DegUA20Dah4",
       "lumibopomofo/zh-Hant", "2026-10-15T06:28:04Z", FREE_END_CARD, END),
    _t("threads", "18110538290595393", "https://www.threads.com/@hourstag.app/post/Dek9_ySlB4l",
       "lumibopomofo_b/zh-Hant", "2026-10-17T01:52:23Z", STORE_SHOT,
       "beat 1 uses store screenshot 'lumibopomofo/01.png', not a real screen recording"),
)
LOCAL_STEPS = [
    "iPhone 開 Instagram App，確認登入的是發這些 Reels 的帳號（報告 rows[].live.username）。",
    "逐一打開報告 handoff_local 裡的每個連結（或個人檔案 → Reels 分頁找到同一支片）。",
    "點右上角「⋯」→「封存」（Archive）。不要按「刪除」：封存可以復原，刪除不行。",
    "全部封存後，用無痕視窗打開每個連結，看到「無法使用這個頁面」就是完成；把結果回報雲端，"
    "由雲端把 clip-posts.json 的 taken_down.status 從 pending_local_archive 改成 archived。",
    "要復原時：個人檔案 → 右上角選單 →「封存」→ 打開那支 Reel →「⋯」→「在個人檔案上顯示」。",
]


class Refused(RuntimeError):
    """The run must not write anything (wrong confirmation, a target list that breaks the rules)."""


def now_utc():
    return dt.datetime.now(dt.timezone.utc)


def stamp(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(value):
    try:
        return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except (TypeError, ValueError):
        return None


def digest(targets=TARGETS):
    canonical = json.dumps(list(targets), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def app_of(clip):
    return clip.split("/", 1)[0]


def listing_app(clip):
    """The app a clip promotes (a B storyboard of the same app: lumibopomofo_b -> lumibopomofo)."""
    app = app_of(clip)
    return app[:-2] if app.endswith("_b") else app


def locale_of(clip):
    return clip.rsplit("/", 1)[-1]


def shortcode(link):
    return [p for p in urllib.parse.urlsplit(link or "").path.split("/") if p][-1:] or [""]


def check_targets(targets=TARGETS):
    problems, seen = [], set()
    for t in targets:
        if app_of(t["clip"]) in COMPLIANT_KEYS:
            problems.append(f"{t['clip']}: {app_of(t['clip'])} is a compliant clip key and is never taken down")
        if (t["platform"], t["id"]) in seen:
            problems.append(f"{t['platform']} {t['id']} is listed twice")
        seen.add((t["platform"], t["id"]))
        if t["platform"] not in METHODS:
            problems.append(f"{t['platform']} {t['id']}: unknown platform")
        if t["reason"] not in REASONS:
            problems.append(f"{t['platform']} {t['id']}: unknown reason {t['reason']!r}")
        if t["platform"] == "telegram" and t["link"] != f"https://t.me/{CHANNEL}/{t['id']}":
            problems.append(f"telegram {t['id']}: the link is not the channel message")
        if parse_time(t["posted_at"]) is None:
            problems.append(f"{t['platform']} {t['id']}: posted_at is not a UTC stamp")
    return problems


def load_posts(path=POSTS):
    return OP.load_json(path, {"posts": [], "notes": []})


def save_posts(log, path=POSTS):
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")   # clip_progress's format
    os.replace(tmp, path)


def logged_entry(log, target):
    for p in log.get("posts", []):
        if p.get("channel") == target["platform"] and str(p.get("id") or "") == target["id"]:
            return p
    return None


def record_problem(log, target):
    p = logged_entry(log, target)
    if p is None:
        return f"clip-posts.json has no {target['platform']} post with id {target['id']}"
    if (p.get("clip"), p.get("link"), p.get("posted_at")) != (target["clip"], target["link"], target["posted_at"]):
        return f"clip-posts.json logs {target['platform']} {target['id']} with another clip / link / time"
    return None


# ---------------------------------------------------------------- Telegram

def tg_api(token, method, payload, opener=urllib.request.urlopen, timeout=30):
    """Bot API call; an error carries Telegram's description only (the URL holds the token)."""
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/{method}", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", "User-Agent": UA})
    try:
        with opener(req, timeout=timeout) as r:
            answer = json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as exc:
        try:
            description = json.loads(exc.read() or b"{}").get("description", "")
        except ValueError:
            description = ""
        finally:
            exc.close()
        raise RuntimeError(f"HTTP {exc.code} {description or exc.reason}"[:200]) from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"network error {str(exc.reason)[:80]}") from None
    if not answer.get("ok"):
        raise RuntimeError(f"{method} answered {str(answer.get('description') or answer)[:160]}")
    return answer.get("result")


def _text_of(block):
    m = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', block, re.S)
    if not m:
        return ""
    text = re.sub(r"<br\s*/?>", "\n", m.group(1))
    text = html.unescape(re.sub(r"<[^>]+>", "", text))
    return "\n".join(line.strip() for line in text.split("\n")).strip()


def tg_preview(post_id, opener=urllib.request.urlopen, tries=3, sleeper=time.sleep):
    """The public single-message widget (no token): {"state": present / missing / unknown, video, photo, text}."""
    url = f"https://t.me/{CHANNEL}/{post_id}?embed=1&mode=tme"
    last = ""
    for attempt in range(tries):
        try:
            with opener(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
                page = r.read().decode("utf-8", "replace")
        except (urllib.error.URLError, OSError) as exc:
            last = str(getattr(exc, "reason", exc))[:80]
            if attempt + 1 < tries:
                sleeper(3 * (attempt + 1))
            continue
        if "tgme_widget_message_error" in page:
            return {"state": "missing", "video": False, "photo": False, "text": ""}
        if f'data-post="{CHANNEL}/{post_id}"' not in page:
            last = "the widget shows another message"
            continue
        return {"state": "present", "video": "tgme_widget_message_video" in page,
                "photo": "tgme_widget_message_photo_wrap" in page, "text": _text_of(page)}
    return {"state": "unknown", "video": None, "photo": None, "text": "", "error": last or "unreadable"}


def itunes_icon(ios_id, opener=urllib.request.urlopen):
    """The app's own App Store icon (artworkUrl512), or None."""
    url = f"https://itunes.apple.com/lookup?id={ios_id}&country=us"
    try:
        with opener(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30) as r:
            results = json.loads(r.read() or b"{}").get("results") or []
    except (urllib.error.URLError, OSError, ValueError):
        return None
    for row in results:
        if str(row.get("trackId")) == str(ios_id) and str(row.get("artworkUrl512", "")).startswith("https://"):
            return row["artworkUrl512"]
    return None


def keyboard(locale, store, play):
    row = [{"text": CP.text_for(locale)["button"], "url": store}]
    if play:
        row.append({"text": CP.PLAY_LINE.get(locale) or CP.PLAY_LINE.get(locale.split("-")[0]) or CP.PLAY_LINE["en"],
                    "url": play})
    return {"inline_keyboard": [row]}


def tg_fallback(target, caption, catalog, icon=itunes_icon):
    """(the editMessageMedia payload without chat / message id, problems) for a refused delete."""
    app, locale = listing_app(target["clip"]), locale_of(target["clip"])
    ios = B.ios_id_for(catalog, {"app": app})
    if not ios:
        return None, [f"no App Store id known for {app}"]
    if not android_apps():
        return None, ["the Android snapshot is empty or unreadable: the Google Play link cannot be decided"]
    if not caption.strip():
        return None, ["the original caption could not be read from the public preview"]
    store = campaign_app_store_url(f"https://apps.apple.com/app/id{ios}", TG_CT)
    play = play_store_url(ios, TG_CT)
    label = f"{target['clip']} telegram (video replaced)"
    play_label = CP.PLAY_LINE.get(locale) or CP.PLAY_LINE.get(locale.split("-")[0]) or CP.PLAY_LINE["en"]
    try:
        text = DL.ensure_download_link(caption, store, play, max_len=CAPTION_MAX,
                                       app_store_label=CP.text_for(locale)["button"], play_label=play_label,
                                       label=label)
    except DL.MissingDownloadLink as exc:
        return None, [str(exc)]
    problems = post_qa.download_link_problems(text, store, "telegram", play) + DL.link_problems(text, store, play, label)
    if len(text) > CAPTION_MAX:
        problems.append(f"caption is {len(text)} characters; telegram takes {CAPTION_MAX}")
    photo = icon(ios)
    if not photo:
        problems.append(f"the App Store icon of id{ios} could not be read")
    if problems:
        return None, problems
    return {"media": {"type": "photo", "media": photo, "caption": text},
            "reply_markup": keyboard(locale, store, play)}, []


# ---------------------------------------------------------------- Graph API reads / Threads delete

def graph_delete(url, params, timeout=30):
    req = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}", method="DELETE",
                                 headers={"User-Agent": UA})
    return OP._open(req, timeout)


def gone_error(exc):
    """A Graph API answer that means the object no longer exists ("Object with ID ... does not exist", code 100).

    A plain code 100 is also "invalid parameter" (e.g. a field the API does not know), so the words are needed;
    the account itself is read first (Context.account), so a token that cannot read is never taken for "gone"."""
    return isinstance(exc, OP.ApiError) and exc.code == 100 and "does not exist" in exc.message.lower()


class Context:
    def __init__(self, *, env=None, opener=urllib.request.urlopen, get=OP.http_get, delete=graph_delete,
                 tg=tg_api, preview=tg_preview, icon=itunes_icon, catalog=None, sleeper=time.sleep, now=None,
                 log=print):
        env = os.environ if env is None else env
        self.tg_token = env.get("TELEGRAM_BOT_TOKEN", "").strip()
        self.tg_chat = env.get("TELEGRAM_CHAT_ID", "").strip()
        self.ig_token = env.get("IG_ACCESS_TOKEN", "").strip()
        self.th_token = env.get("THREADS_TOKEN", "").strip()
        self.opener, self.get, self.delete, self.tg = opener, get, delete, tg
        self.preview, self.icon = preview, icon
        self.catalog = catalog if catalog is not None else OP.Catalog()
        self.sleeper, self.log = sleeper, log
        self.now = now or now_utc()
        self.chat_problem = None
        self.chat_checked = False
        self.accounts = {}

    def account(self, platform):
        """(username, problem) of the token's own account (/me), read once per run."""
        if platform not in self.accounts:
            token = self.ig_token if platform == "instagram" else self.th_token
            base = OP.IG_GRAPH if platform == "instagram" else OP.THREADS_GRAPH
            try:
                me = self.get(f"{base}/me", {"fields": "id,username", "access_token": token})
                self.accounts[platform] = (me.get("username"), None)
            except (OP.ApiError, urllib.error.URLError, OSError) as exc:
                self.accounts[platform] = (None, f"the token cannot read its own account ({str(exc)[:100]})")
        return self.accounts[platform]

    def telegram_chat(self):
        """None when TELEGRAM_CHAT_ID is the public channel the clips went to, else why not."""
        if not self.chat_checked:
            self.chat_checked = True
            if not (self.tg_token and self.tg_chat):
                self.chat_problem = "TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set"
            else:
                try:
                    chat = self.tg(self.tg_token, "getChat", {"chat_id": self.tg_chat}) or {}
                    if (chat.get("username") or "").lower() != CHANNEL.lower():
                        self.chat_problem = f"TELEGRAM_CHAT_ID is @{chat.get('username')}, not @{CHANNEL}"
                except RuntimeError as exc:
                    self.chat_problem = f"getChat failed ({exc})"
        return self.chat_problem


def base_row(target):
    return {"platform": target["platform"], "id": target["id"], "link": target["link"], "clip": target["clip"],
            "app": app_of(target["clip"]), "posted_at": target["posted_at"], "reason": target["reason"],
            "reason_text": REASONS[target["reason"]], "detail": target["detail"],
            "record": "ios-app-guide .github/growth/clip-posts.json", "method": METHODS[target["platform"]],
            "reversible": REVERSIBLE[target["platform"]]}


def inspect_telegram(row, target, ctx):
    deadline = parse_time(target["posted_at"]) + dt.timedelta(hours=TG_DELETE_HOURS)
    row["delete_window_ends"] = stamp(deadline)
    seen = ctx.preview(target["id"])
    row["live"] = {k: seen.get(k) for k in ("state", "video", "photo")}
    if seen["state"] == "missing":
        row.update(action="none", gone=True, note="the public preview already says Post not found")
        return
    if seen["state"] != "present":
        row.update(action="blocked", problem=f"public preview unreadable ({seen.get('error')})")
        return
    row["caption"] = seen["text"]   # kept for the record: the message itself is deleted or edited
    if not seen["video"]:
        row["action"] = "none"
        row["note"] = "the message carries no video any more"
        return
    payload, problems = tg_fallback(target, seen["text"], ctx.catalog, ctx.icon)
    row["fallback"] = {"ready": payload is not None, "problems": problems,
                       "photo": payload["media"]["media"] if payload else None,
                       "caption": payload["media"]["caption"] if payload else None,
                       "buttons": [b["url"] for b in payload["reply_markup"]["inline_keyboard"][0]] if payload else []}
    row["_fallback"] = payload
    chat = ctx.telegram_chat()
    if chat:
        row.update(action="blocked", problem=chat)
        return
    in_window = ctx.now < deadline
    row["action"] = "delete" if in_window else "delete_or_replace_video"
    row["note"] = ("inside the 48 h delete window" if in_window
                   else "past the 48 h window: deleteMessage is tried, a refusal swaps the video for the icon photo")
    if not in_window and payload is None:
        row.update(action="blocked", problem="past the 48 h window and the fallback is not ready: "
                   + "; ".join(problems))


def inspect_graph(row, target, ctx):
    platform = target["platform"]
    token = ctx.ig_token if platform == "instagram" else ctx.th_token
    if not token:
        row.update(action="blocked", problem=f"{'IG_ACCESS_TOKEN' if platform == 'instagram' else 'THREADS_TOKEN'} not set")
        return
    username, problem = ctx.account(platform)
    if problem:
        row.update(action="blocked", problem=problem)
        return
    if platform == "threads" and (username or "").lower() != THREADS_USER:
        row.update(action="blocked", problem=f"THREADS_TOKEN is @{username}, not @{THREADS_USER}")
        return
    if platform == "instagram":
        url, fields = f"{OP.IG_GRAPH}/{target['id']}", "id,media_type,media_product_type,permalink,timestamp,username"
    else:
        url, fields = f"{OP.THREADS_GRAPH}/{target['id']}", "id,media_type,permalink,timestamp,username,shortcode"
    try:
        media = ctx.get(url, {"fields": fields, "access_token": token})
    except OP.ApiError as exc:
        if gone_error(exc):
            row.update(action="none", gone=True, note="the Graph API says the post no longer exists",
                       live={"state": "missing"})
        else:
            row.update(action="blocked", problem=f"Graph API read failed ({str(exc)[:120]})")
        return
    except (urllib.error.URLError, OSError) as exc:
        row.update(action="blocked", problem=f"Graph API read failed ({str(exc)[:80]})")
        return
    row["live"] = {"state": "present", **{k: media.get(k) for k in fields.split(",") if k != "id"}}
    if str(media.get("id")) != target["id"] or shortcode(media.get("permalink")) != shortcode(target["link"]):
        row.update(action="blocked", problem="the Graph API answer is another post than the listed link")
    elif media.get("media_type") != "VIDEO":
        row.update(action="blocked", problem=f"media_type is {media.get('media_type')}, not VIDEO")
    elif platform == "threads" and (media.get("username") or "").lower() != THREADS_USER:
        row.update(action="blocked", problem=f"posted by @{media.get('username')}, not @{THREADS_USER}")
    elif platform == "instagram":
        row["action"] = "local_archive"
        row["note"] = "Instagram Login token: no delete / archive call; archived by hand on the Mac"
    else:
        row["action"] = "delete"
        try:   # information only: our download-link reply holds no video and stays
            replies = ctx.get(f"{OP.THREADS_GRAPH}/{target['id']}/replies",
                              {"fields": "id,text,is_reply_owned_by_me", "access_token": token}).get("data") or []
        except Exception:  # noqa: BLE001
            replies = []
        own = [r for r in replies if r.get("is_reply_owned_by_me")]
        if own:
            row["own_replies_kept"] = [{"id": str(r.get("id")), "text": (r.get("text") or "")[:120]} for r in own]


def act_telegram(row, target, ctx, receipts):
    payload = row.get("_fallback")
    try:
        ctx.tg(ctx.tg_token, "deleteMessage", {"chat_id": ctx.tg_chat, "message_id": int(target["id"])})
        method = "deleted"
    except RuntimeError as exc:
        text = str(exc).lower()
        if any(s in text for s in ALREADY_GONE):
            method = "deleted"
        elif any(s in text for s in CANNOT_DELETE) and payload:
            row["delete_refused"] = str(exc)[:160]
            try:
                answer = ctx.tg(ctx.tg_token, "editMessageMedia",
                                {"chat_id": ctx.tg_chat, "message_id": int(target["id"]), **payload})
                answer = answer if isinstance(answer, dict) else {}
            except RuntimeError as exc2:
                row.update(action="failed", problem=f"delete refused and editMessageMedia failed ({str(exc2)[:120]})")
                return
            if "video" in answer or not answer.get("photo"):
                row.update(action="unverified", problem="editMessageMedia answered a message that still has a video")
                return
            method = "video_replaced"
        else:
            row.update(action="failed", problem=f"deleteMessage failed ({str(exc)[:120]})")
            return
    # Read-back: a deleted message must read "Post not found" on the public preview (the widget can lag a
    # little, so it is asked a few times). An edited one is read back from the Bot API answer itself (the
    # edited Message: a photo, no video); the preview is recorded next to it.
    seen = {"state": "unknown"}
    for wait in PREVIEW_WAITS:
        ctx.sleeper(wait)
        seen = ctx.preview(target["id"])
        if (method == "deleted" and seen["state"] == "missing") or (
                method == "video_replaced" and seen["state"] == "present" and seen["video"] is False):
            break
    verified = seen["state"] == "missing" if method == "deleted" else True
    row["readback"] = {k: seen.get(k) for k in ("state", "video", "photo")}
    row["action"] = "done" if verified else "unverified"
    if not verified:
        row["problem"] = "deleteMessage answered ok but the public preview still shows the message (re-run apply)"
    receipts.setdefault("telegram", {})[target["id"]] = {
        "at": stamp(ctx.now), "clip": target["clip"], "status": method, "verified": verified,
        "public_preview": row["readback"], "caption_before": row.get("caption", ""),
        **({"caption_after": payload["media"]["caption"], "photo": payload["media"]["media"],
            "delete_refused": row.get("delete_refused", "")} if method == "video_replaced" else {})}


def act_threads(row, target, ctx, receipts):
    try:
        answer = ctx.delete(f"{OP.THREADS_GRAPH}/{target['id']}", {"access_token": ctx.th_token})
    except OP.ApiError as exc:
        hint = " (the token lacks threads_delete: hand it to the Mac)" if exc.permission else ""
        row.update(action="failed", problem=f"DELETE failed ({str(exc)[:120]}){hint}")
        return
    except (urllib.error.URLError, OSError) as exc:
        row.update(action="failed", problem=f"DELETE failed ({str(exc)[:80]})")
        return
    row["answer"] = {k: answer.get(k) for k in ("success", "deleted_id")}
    gone = False
    for wait in (3, 10):
        ctx.sleeper(wait)
        try:
            ctx.get(f"{OP.THREADS_GRAPH}/{target['id']}", {"fields": "id", "access_token": ctx.th_token})
        except OP.ApiError as exc:
            gone = gone_error(exc)
            row["readback"] = str(exc)[:160]
            if gone:
                break
        except (urllib.error.URLError, OSError) as exc:
            row["readback"] = str(exc)[:80]
        else:
            row["readback"] = "the post still answers"
    row["action"] = "done" if gone else "unverified"
    receipts.setdefault("threads", {})[target["id"]] = {
        "at": stamp(ctx.now), "clip": target["clip"], "status": "deleted", "verified": gone,
        "answer": row["answer"], "readback": row["readback"]}


def run(mode, *, confirm="", ctx=None, posts_path=POSTS, report_path=REPORT, targets=TARGETS):
    """plan / apply -> (exit code, report document)."""
    problems = check_targets(targets)
    if problems:
        raise Refused("; ".join(problems))
    want = digest(targets)
    if mode == "apply" and confirm != want:
        raise Refused(f"apply needs --confirm {want} (the digest the plan printed); got {confirm or 'nothing'}")
    ctx = ctx or Context()
    log = load_posts(posts_path)
    previous = OP.load_json(report_path, {})
    receipts = previous.get("receipts") or {}
    rows = []
    for target in targets:
        row = base_row(target)
        rows.append(row)
        problem = record_problem(log, target)
        done = (receipts.get(target["platform"]) or {}).get(target["id"])
        if problem:
            row.update(action="blocked", problem=problem)
        elif done and done.get("verified") and done.get("status") in MARKS - {"pending_local_archive"}:
            row.update(action="none", note="done earlier", receipt=done)
        elif target["platform"] == "telegram":
            inspect_telegram(row, target, ctx)
        else:
            inspect_graph(row, target, ctx)
    if mode == "apply":
        first = True
        for row, target in zip(rows, targets):
            book = receipts.setdefault(target["platform"], {})
            if row.pop("gone", False) and not (book.get(target["id"]) or {}).get("verified"):
                # Already gone when apply looked (an earlier run's delete whose read-back lagged, or by hand):
                # the read-back is this look itself.
                book[target["id"]] = {"at": stamp(ctx.now), "clip": target["clip"], "status": "deleted",
                                      "verified": True, "note": row.get("note", "found gone")}
                row["action"] = "done"
                continue
            if row["action"] not in ("delete", "delete_or_replace_video", "local_archive"):
                continue
            if row["action"] == "local_archive":
                book = receipts.setdefault("instagram", {})
                book[target["id"]] = book.get(target["id"]) or {
                    "at": stamp(ctx.now), "clip": target["clip"], "status": "pending_local_archive",
                    "verified": None, "handoff": "Mac: archive in the Instagram app (steps: local_steps)"}
                row["action"] = "handed_to_local"
                continue
            if not first:
                ctx.sleeper(GAP)
            first = False
            if target["platform"] == "telegram":
                act_telegram(row, target, ctx, receipts)
            else:
                act_threads(row, target, ctx, receipts)
            ctx.log(f"{target['platform']} {target['id']} ({target['clip']}): {row['action']}"
                    f"{' — ' + row['problem'] if row.get('problem') else ''}")
    for row in rows:
        row.pop("_fallback", None)
        row.pop("gone", None)
    handoff = [{"platform": r["platform"], "id": r["id"], "link": r["link"], "clip": r["clip"],
                "username": (r.get("live") or {}).get("username"), "do": "archive (封存), not delete"}
               for r in rows if r["platform"] == "instagram" and r["action"] in ("local_archive", "handed_to_local")]
    doc = {"schema": SCHEMA, "mode": mode, "generated_at": stamp(ctx.now), "digest": want, "targets": len(targets),
           "summary_report": SUMMARY_REPORT, "rows": rows, "receipts": receipts, "handoff_local": handoff,
           "local_steps": LOCAL_STEPS}
    tmp = report_path.with_name(report_path.name + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, report_path)
    if mode == "apply":
        mark(posts_path, report_path, targets)
        ok = {"done", "none", "handed_to_local"}
    else:
        ok = {"delete", "delete_or_replace_video", "local_archive", "none"}
    return (0 if all(r["action"] in ok for r in rows) else 1), doc


def mark(posts_path=POSTS, report_path=REPORT, targets=TARGETS):
    """Copy the receipts onto clip-posts.json (idempotent). Returns how many entries changed."""
    report = OP.load_json(report_path, {})
    log = load_posts(posts_path)
    changed = 0
    for target in targets:
        receipt = ((report.get("receipts") or {}).get(target["platform"]) or {}).get(target["id"])
        if not receipt or receipt.get("status") not in MARKS:
            continue
        if receipt["status"] != "pending_local_archive" and not receipt.get("verified"):
            continue
        entry = logged_entry(log, target)
        if entry is None or record_problem(log, target):
            continue
        want = {"at": receipt["at"], "status": receipt["status"], "reversible": REVERSIBLE[target["platform"]],
                "reason": target["reason"], "report": SUMMARY_REPORT}
        if entry.get("taken_down") != want:
            entry["taken_down"] = want
            changed += 1
    if changed:
        save_posts(log, posts_path)
    return changed


def summary_lines(doc):
    lines = [f"### Hook clip takedown {doc['mode']} ({doc['generated_at']})", "",
             f"digest `{doc['digest']}` (apply: confirm={doc['digest']})", "",
             "| platform | post | clip | reason | action |", "|---|---|---|---|---|"]
    for r in doc["rows"]:
        lines.append(f"| {r['platform']} | [{r['id']}]({r['link']}) | {r['clip']} | {r['reason']} | {r['action']}"
                     f"{' — ' + r['problem'] if r.get('problem') else ''} |")
    return lines


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("mode", choices=["plan", "apply", "mark"])
    ap.add_argument("--confirm", default="", help="apply only: the digest the plan printed")
    args = ap.parse_args(argv)
    if args.mode == "mark":
        print(f"video-takedown mark: {mark()} clip-posts.json entr(y/ies) changed")
        return 0
    try:
        code, doc = run(args.mode, confirm=args.confirm.strip())
    except Refused as exc:
        print(f"::error::video-takedown: {exc}")
        return 2
    lines = summary_lines(doc)
    print("\n".join(lines))
    print(f"TARGETS_DIGEST={doc['digest']}")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    for r in doc["rows"]:
        if r["action"] in ("blocked", "failed", "unverified"):
            print(f"::error::{r['platform']} {r['id']} ({r['clip']}): {r['action']} {r.get('problem', '')}")
    return code


if __name__ == "__main__":
    sys.exit(main())
