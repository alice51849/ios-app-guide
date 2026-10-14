#!/usr/bin/env python3
"""Daily countdown cards for the big dates people count down to (zero token).

One card a day for the nearest active event (수능, 學測, 共通テスト, Christmas,
New Year, Lunar New Year), in that event's language, branded CountDaysNow.
Students and parents check and share these every day, and each card is new
content, so it never reads as a repeated post.

    python3 countdown_cards.py make --out card.jpg   # writes card.jpg + card.json
    python3 countdown_cards.py active                 # exit 0 if a card is due today
    python3 countdown_cards.py post --card card.jpg --url <public jpg url>

Posting: Telegram (photo upload + App Store button), Threads (image, store
links in the first reply) and Instagram (image) with the existing secrets.
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from social_post_common import play_store_url  # noqa: E402

APP_ID = "6807079789"  # CountDaysNow
STORE = {"ko": "kr", "zh-Hant": "tw", "ja": "jp", "en": "us"}
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
ASSETS = HERE.parent / "growth" / "assets" / "countdown"  # localized App Store screenshots
FONT_INDEX = {"ja": 0, "ko": 1, "zh-Hans": 2, "zh-Hant": 3, "en": 0}
TW = dt.timezone(dt.timedelta(hours=8))

# Dates checked 2026-10-14: 수능 2026-11-19 (교육부), 學測 2027-01-22~24
# (大考中心 116 學年度簡章), 共通テスト 2027-01-16~17 (大学入試センター).
EVENTS = [
    {"id": "suneung2027", "date": "2026-11-19", "locale": "ko", "window": 60,
     "title": "2027학년도 수능", "count": "D-{n}", "today": "오늘 수능,\n모두 응원해요", "when": "11월 19일 (목)",
     "lines": ["남은 날을 계획으로", "오늘도 한 걸음", "끝까지 페이스 유지", "할 수 있어요"],
     "colors": ("#1d2b64", "#4b6cb7", "#ffd166")},
    {"id": "gsat2027", "date": "2027-01-22", "locale": "zh-Hant", "window": 100,
     "title": "116 學測", "count": "倒數 {n} 天", "today": "學測加油！", "when": "1/22（五）～1/24（日）",
     "lines": ["把剩下的天數變成計畫", "今天也前進一步", "穩住節奏到最後", "一起撐過去"],
     "colors": ("#3a1c71", "#d76d77", "#ffaf7b")},
    {"id": "kyotsu2027", "date": "2027-01-16", "locale": "ja", "window": 60,
     "title": "大学入学共通テスト", "count": "あと{n}日", "today": "共通テスト当日、\n応援しています", "when": "2027年1月16日(土)・17日(日)",
     "lines": ["残りの日数を計画に", "今日も一歩ずつ", "最後までペースを守って", "応援しています"],
     "colors": ("#0f2027", "#2c5364", "#7ee8fa")},
    {"id": "christmas2026", "date": "2026-12-25", "locale": "en", "window": 30,
     "title": "Christmas", "count": "{n} days to go", "today": "Merry Christmas!", "when": "December 25",
     "lines": ["Plan the gifts backwards", "Order early, relax later", "Cards, cake, travel: on track"],
     "colors": ("#7f1d1d", "#b91c1c", "#fde68a")},
    {"id": "lunar2027", "date": "2027-02-06", "locale": "zh-Hant", "window": 30,
     "title": "農曆新年", "count": "倒數 {n} 天", "today": "新年快樂！", "when": "2027/2/6（除夕 2/5）",
     "lines": ["年貨、車票、紅包，一項項排好", "回家的路倒數中", "提前準備，過個好年"],
     "colors": ("#7a0a0a", "#c0392b", "#f5c542")},
]
TEXT = {
    "ko": {"by": "CountDaysNow 카운트다운", "search": "App Store에서 'CountDaysNow' 검색", "both": "App Store · Google Play에서 'CountDaysNow' 검색",
           "button": "App Store에서 받기"},
    "zh-Hant": {"by": "CountDaysNow 倒數", "search": "App Store 搜尋「CountDaysNow」", "both": "App Store／Google Play 搜尋「CountDaysNow」",
                "button": "在 App Store 下載"},
    "ja": {"by": "CountDaysNow カウントダウン", "search": "App Storeで「CountDaysNow」を検索", "both": "App Store・Google Playで「CountDaysNow」を検索",
           "button": "App Storeで入手"},
    "en": {"by": "CountDaysNow countdown", "search": "Search “CountDaysNow” on the App Store", "both": "Search “CountDaysNow” on App Store or Google Play",
           "button": "Get it on the App Store"},
}


WHITE = (255, 255, 255)
MIN_TEXT = 34  # px on the 1080-wide card: ~12pt once the feed shows it at phone width
AA = 4.5  # WCAG AA contrast for normal text


def _lum(rgb):
    def ch(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    """WCAG contrast ratio of two RGB colours (1-21)."""
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def legible(bg, ink=WHITE, ratio=AA):
    """The background colour, darkened just enough (same hue) that `ink` text on it reaches `ratio`."""
    bg = tuple(int(c) for c in bg)
    k = 1.0
    while contrast(ink, tuple(int(c * k) for c in bg)) < ratio and k > 0:
        k -= 0.005
    return tuple(int(c * max(k, 0)) for c in bg)


def gradient(draw, w, h, top, bottom):
    """Vertical card gradient whose every row keeps white text at AA contrast."""
    for y in range(h):
        k = y / h
        draw.line([(0, y), (w, y)], fill=legible(tuple(top[i] + (bottom[i] - top[i]) * k for i in range(3))))


def wrap(draw, text, font_for, size, max_w, min_size=MIN_TEXT):
    """(lines, size): shrink to `min_size` at most, then wrap (by word, or by character for CJK)."""
    while size > min_size and draw.textlength(text, font=font_for(size)) > max_w:
        size -= 2
    font = font_for(size)
    if draw.textlength(text, font=font) <= max_w:
        return [text], size
    # CJK sentence: break after the punctuation nearest the middle when both halves fit (no orphaned tail).
    cuts = [i + 1 for i, ch in enumerate(text[:-1]) if ch in "。、，．！？；：,"]
    for i in sorted(cuts, key=lambda i: abs(i - len(text) / 2)):
        halves = [text[:i].strip(), text[i:].strip()]
        if all(draw.textlength(h, font=font) <= max_w for h in halves):
            return halves, size
    units = text.split(" ") if " " in text.strip() else list(text)
    sep = " " if " " in text.strip() else ""
    lines, line = [], ""
    for u in units:
        trial = (line + sep + u) if line else u
        if line and draw.textlength(trial, font=font) > max_w:
            lines.append(line)
            line = u
        else:
            line = trial
    lines.append(line)
    return lines, size


def footer_band(img, top_rgb_bottom, h=330):
    """Fade the phone's lower part into a darkened band so the store pill and the line under it read."""
    from PIL import Image, ImageDraw
    W, H = img.size
    band = legible(top_rgb_bottom, WHITE, 7.0)
    fade = Image.new("RGBA", (W, h), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fade)
    for i in range(h):
        fd.line([(0, i), (W, i)], fill=band + (int(255 * min(1, i / 200)),))
    img.paste(fade, (0, H - h), fade)
    return band


def today_tw():
    return dt.datetime.now(TW).date()


def due(day):
    """Today's event: events in their final 10 days come first (nearest wins);
    otherwise the active events take turns day by day. None if nothing is active."""
    active = sorted(((e, (dt.date.fromisoformat(e["date"]) - day).days) for e in EVENTS),
                    key=lambda x: x[1])
    active = [(e, n) for e, n in active if 0 <= n <= e["window"]]
    if not active:
        return None
    if active[0][1] <= 10:
        return active[0]
    return active[day.toordinal() % len(active)]


def store_url(e, channel):
    query = urllib.parse.urlencode({"pt": "118326163", "ct": f"cd_{e['id']}_{channel}"[:40], "mt": "8"})
    return f"https://apps.apple.com/{STORE[e['locale']]}/app/id{APP_ID}?{query}"


def caption(e, n, day):
    t = TEXT[e["locale"]]
    head = e["today"].replace("\n", " ") if n == 0 else f"{e['title']} {e['count'].format(n=n)}"
    line = e["lines"][day.toordinal() % len(e["lines"])]
    store = t["both"] if play_store_url(APP_ID, "cd") else t["search"]
    return f"{head}\n{line}\n\n{store}"


def make(out, day):
    from PIL import Image, ImageDraw, ImageFont
    hit = due(day)
    if not hit:
        return None
    e, n = hit
    W, H = 1080, 1350
    top, bottom, accent = (tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) for c in e["colors"])
    img = Image.new("RGB", (W, H))
    gradient(ImageDraw.Draw(img), W, H, top, bottom)
    draw = ImageDraw.Draw(img)
    idx = FONT_INDEX.get(e["locale"], 0)
    f = lambda size: ImageFont.truetype(FONT, size, index=idx)

    def center(text, y, size, fill):
        font = f(size)
        for line in text.split("\n"):
            w = draw.textlength(line, font=font)
            while w > W - 120 and size > 30:
                size -= 6
                font = f(size)
                w = draw.textlength(line, font=font)
            draw.text(((W - w) / 2, y), line, font=font, fill=fill)
            y += int(size * 1.25)
        return y

    t = TEXT[e["locale"]]
    center(e["title"], 80, 64, (255, 255, 255))
    big = e["today"] if n == 0 else e["count"].format(n=n)
    y = center(big, 175, 190 if n else 104, accent)
    y = center(e["when"], max(y + 20, 430), 46, (255, 255, 255))
    center(e["lines"][day.toordinal() % len(e["lines"])], y + 14, 50, (255, 255, 255))
    # The real app screen (localized App Store screenshot) rising from the bottom.
    shot = ASSETS / f"countdaysnow_{e['locale']}.png"
    if not shot.exists():
        shot = ASSETS / "countdaysnow_en.png"
    phone = Image.open(shot).convert("RGBA")
    pw = 540
    phone = phone.resize((pw, int(phone.height * pw / phone.width)), Image.LANCZOS)
    shadow = Image.new("RGBA", (pw + 80, phone.height + 80), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([40, 50, pw + 40, phone.height + 40], radius=70, fill=(0, 0, 0, 110))
    from PIL import ImageFilter
    shadow = shadow.filter(ImageFilter.GaussianBlur(24))
    top_y = 640
    img.paste(shadow, ((W - pw) // 2 - 40, top_y - 40), shadow)
    img.paste(phone, ((W - pw) // 2, top_y), phone)
    # Fade the phone's lower part into a darkened band so the store pill and the brand line read.
    footer_band(img, bottom)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([90, 1160, W - 90, 1260], radius=50, fill=(255, 255, 255))
    store = t["both"] if play_store_url(APP_ID, "cd") else t["search"]
    font = f(40)
    size = 40
    while draw.textlength(store, font=font) > W - 240 and size > MIN_TEXT - 4:
        size -= 2
        font = f(size)
    draw.text(((W - draw.textlength(store, font=font)) / 2, 1210 - size * 0.62), store, font=font,
              fill=legible(top, WHITE) if contrast(top, WHITE) < AA else top)
    center(t["by"], 1278, 36, (255, 255, 255))
    img.save(out, "JPEG", quality=90)
    meta = {"event": e["id"], "locale": e["locale"], "days": n, "date": day.isoformat(),
            "caption": caption(e, n, day)}
    Path(out).with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta


def _post(url, fields, timeout=60):
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(url, data=data, headers={"User-Agent": "lumi-countdown/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as exc:  # surface the API's reason, never the token
        raise RuntimeError(f"HTTP {exc.code}: {exc.read().decode(errors='replace')[:300]}") from None


def _get(url, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "lumi-countdown/1.0"}), timeout=timeout) as r:
        return json.loads(r.read())


def send_photo(card, caption, row, label="countdown"):
    """Upload the card to the Telegram channel with a row of link buttons; the API result or None."""
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN", ""), os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat:
        print(f"{label}: Telegram secrets missing")
        return None
    boundary = "lumicountdown"
    parts = []
    for k, v in {"chat_id": chat, "caption": caption, "reply_markup": json.dumps({"inline_keyboard": [row]})}.items():
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"card.jpg\"\r\n"
                 "Content-Type: image/jpeg\r\n\r\n".encode() + Path(card).read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendPhoto", data=b"".join(parts),
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        result = json.loads(r.read())
    print(f"{label}: telegram", result.get("ok"))
    return result


def threads_image(url, text, links, label="countdown"):
    """Image post on Threads, store links in the first reply; the media id or None."""
    token, user = os.environ.get("THREADS_TOKEN", ""), os.environ.get("THREADS_USER_ID", "")
    if not token or not user:
        print(f"{label}: Threads secrets missing")
        return None
    api = "https://graph.threads.net/v1.0"
    user = _get(f"{api}/me?fields=id&access_token={token}").get("id") or user  # secret may be stale
    c = _post(f"{api}/{user}/threads", {"media_type": "IMAGE", "image_url": url, "text": text, "access_token": token})["id"]
    time.sleep(30)
    media = _post(f"{api}/{user}/threads_publish", {"creation_id": c, "access_token": token})["id"]
    try:
        r = _post(f"{api}/{user}/threads", {"media_type": "TEXT", "text": "\n".join(links), "reply_to_id": media, "access_token": token})["id"]
        time.sleep(5)
        _post(f"{api}/{user}/threads_publish", {"creation_id": r, "access_token": token})
    except Exception as exc:
        print(f"{label}: Threads reply skipped ({exc.__class__.__name__})")
    print(f"{label}: threads", media)
    return media


def instagram_image(url, text, label="countdown", alt=None):
    """Image post on Instagram (with alt text when given: accessibility + search); the media id or None."""
    token = os.environ.get("IG_ACCESS_TOKEN", "")
    if not token:
        print(f"{label}: IG_ACCESS_TOKEN missing")
        return None
    api = "https://graph.instagram.com/v21.0"
    me = _get(f"{api}/me?fields=user_id&access_token={token}")
    user = me.get("user_id") or me.get("id")
    fields = {"image_url": url, "caption": text, "access_token": token}
    if alt:
        fields["alt_text"] = alt[:1000]
    c = _post(f"{api}/{user}/media", fields)["id"]
    time.sleep(10)
    media = _post(f"{api}/{user}/media_publish", {"creation_id": c, "access_token": token}).get("id")
    print(f"{label}: instagram", media)
    return media


def post_telegram(card, meta, e):
    row = [{"text": TEXT[e["locale"]]["button"], "url": store_url(e, "tg")}]
    play = play_store_url(APP_ID, f"cd_{e['id']}_tg"[:40])
    if play:
        row.append({"text": "Google Play", "url": play})
    send_photo(card, meta["caption"], row)


def post_threads(url, meta, e):
    from threads_post import queued_today
    if queued_today():
        return print("countdown: a queued Threads post has today's slot; Threads skipped")
    links = [f"App Store: {store_url(e, 'th')}"]
    play = play_store_url(APP_ID, f"cd_{e['id']}_th"[:40])
    if play:
        links.append(f"Google Play: {play}")
    threads_image(url, meta["caption"], links)


def instagram_text(meta):
    import search_caption as SC
    text = meta["caption"] + "\n" + {"ko": "링크는 프로필에", "zh-Hant": "下載連結在個人檔案", "ja": "リンクはプロフィールから"}.get(meta["locale"], "Link in bio")
    tags = SC.card_tags("countdaysnow", meta["locale"])  # keyword hashtags from the planner's seo table
    if tags:
        text += "\n\n" + " ".join(tags)
    return text


def qa_problems(meta, e, channel, image=None, online=True):
    """Pre-post QA (post_qa.py): the exact text this channel gets, the image, the live store link."""
    import post_qa
    text = instagram_text(meta) if channel == "instagram" else meta["caption"]
    return post_qa.card_problems(text, e["locale"], channel, store_url=store_url(e, "qa"), name="CountDaysNow",
                                 image=image, online=online)


def post_instagram(url, meta):
    import search_caption as SC
    text = instagram_text(meta)
    instagram_image(url, text, alt=SC.card_alt("CountDaysNow", meta["caption"], "countdaysnow", meta["locale"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["make", "active", "post"])
    ap.add_argument("--out", default="card.jpg")
    ap.add_argument("--card", default="card.jpg")
    ap.add_argument("--url", help="public URL of the card (Threads and Instagram fetch it)")
    ap.add_argument("--date", help="YYYY-MM-DD (Taiwan date), default today")
    ap.add_argument("--only", help="post to this channel only (telegram, threads or instagram)")
    args = ap.parse_args()
    day = dt.date.fromisoformat(args.date) if args.date else today_tw()
    if args.cmd == "active":
        return 0 if due(day) else 1
    if args.cmd == "make":
        meta = make(args.out, day)
        print(json.dumps(meta, ensure_ascii=False) if meta else "countdown: no event today")
        return 0
    meta = json.loads(Path(args.card).with_suffix(".json").read_text(encoding="utf-8"))
    e = next(x for x in EVENTS if x["id"] == meta["event"])
    for name, fn in (("telegram", lambda: post_telegram(args.card, meta, e)),
                     ("threads", lambda: post_threads(args.url, meta, e)),
                     ("instagram", lambda: post_instagram(args.url, meta))):
        if args.only and name != args.only:
            continue
        import post_qa
        if not post_qa.gate(qa_problems(meta, e, name, image=args.card), f"countdown {name}"):
            continue  # a broken card or caption never goes out
        try:
            fn()
        except Exception as exc:  # one channel failing never blocks the others
            print(f"countdown: {name} failed ({exc})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
