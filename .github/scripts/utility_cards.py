#!/usr/bin/env python3
"""Daily utility cards: one genuinely useful image a day, branded with the app
that does the job (zero token).

Three card types take turns day by day, all from curated static lists in
.github/growth/utility-cards.json (no paid API, no model at runtime):

- word    TOEIC-style business English word of the day -> Aim990 / Wordmate Lite
- zhuyin  注音 of the day for kids (zh-Hant)            -> Lumi注音星球
- photo   passport / ID photo size of the day            -> Snapport Lite

Weather-style and currency cards are left out on purpose: the repo has no
free keyless data source for them.

    python3 utility_cards.py make --out card.jpg   # writes card.jpg + card.json
    python3 utility_cards.py post --card card.jpg --url <public jpg url>

Posting reuses the countdown card helpers: Telegram (photo + App Store /
Google Play buttons) and Instagram (image) every day; Threads only when the
account stays at its 3-posts-a-day cap (picture/queue/countdown slot + the
hook clips scheduled that day). Every post is recorded on the promotion page
through clip_progress.record_post.
"""
import argparse
import datetime as dt
import json
import sys
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import countdown_cards as cd  # noqa: E402
from social_post_common import play_store_url  # noqa: E402

GROWTH = HERE.parent / "growth"
DATA = GROWTH / "utility-cards.json"
CLIPS = GROWTH / "clips.json"
ASSETS = GROWTH / "assets" / "utility"  # localized App Store screenshots
STORE = {"ko": "kr", "zh-Hant": "tw", "ja": "jp", "en": "us"}
TYPES = ("word", "zhuyin", "photo")
LOCALES = {"word": ("zh-Hant", "ja", "ko", "en"), "zhuyin": ("zh-Hant",), "photo": ("en", "zh-Hant", "ja", "ko")}
EPOCH = dt.date(2026, 10, 15)  # day 0 of the rotation: first word, ㄅ, first photo size
THREADS_CAP = 3  # posts a day on the Threads account, everything included

APPS = {
    "aim990": {"id": "6784974530", "name": "Aim990", "colors": ("#0b1d3a", "#1e4e8c", "#ffd166"),
               "pitch": {"zh-Hant": "8 分鐘找出你的多益弱點", "ja": "8分でTOEIC®の弱点がわかる",
                         "ko": "8분이면 보이는 토익 약점", "en": "Find your TOEIC®-style weak spots in 8 minutes"}},
    "wordmatelite": {"id": "6797601720", "name": "Wordmate Lite", "colors": ("#1b2a4a", "#3d5a99", "#9ee6c9"),
                     "pitch": {"zh-Hant": "每天五個單字，一分鐘", "ja": "1日5単語、1分だけ",
                               "ko": "하루 다섯 단어, 1분", "en": "Five words a day, one minute"}},
    "lumibopomofo": {"id": "6773017109", "name": "Lumi注音星球", "colors": ("#5b3fa8", "#e58fb6", "#fff3a3"),
                     "pitch": {"zh-Hant": "37 個注音小夥伴陪孩子玩著學"}},
    "snapportlite": {"id": "6792856304", "name": "Snapport Lite", "colors": ("#3b2a6b", "#8a6fd1", "#ffe3f1"),
                     "pitch": {"zh-Hant": "在家拍證件照，35 種尺寸範本", "ja": "自宅で証明写真、35種類のサイズ",
                               "ko": "집에서 증명사진, 35가지 규격", "en": "ID photos at home, 35 size presets"}},
}
TEXT = {
    "en": {"word": "Business English word of the day", "photo": "Photo size of the day",
           "search": "Search “{s}” on the App Store", "both": "Search “{s}” on App Store or Google Play",
           "button": "Get it on the App Store", "bio": "Link in bio", "head": "Head (chin to crown): {h} mm",
           "check": "Rules change: check the official site before you apply.", "example": "Example"},
    "zh-Hant": {"word": "今日多益商務單字", "zhuyin": "今日注音", "photo": "今日證件照尺寸",
                "search": "App Store 搜尋「{s}」", "both": "App Store／Google Play 搜尋「{s}」",
                "button": "在 App Store 下載", "bio": "下載連結在個人檔案", "head": "頭部（下巴到頭頂）{h} mm",
                "check": "規定可能更新，送件前請先確認官方說明", "example": "例句"},
    "ja": {"word": "今日のTOEIC®ビジネス英単語", "photo": "今日の証明写真サイズ",
           "search": "App Storeで「{s}」を検索", "both": "App Store・Google Playで「{s}」を検索",
           "button": "App Storeで入手", "bio": "リンクはプロフィールから", "head": "頭の長さ（あご〜頭頂）{h} mm",
           "check": "規定は変わることがあります。申請前に公式情報をご確認ください", "example": "例文"},
    "ko": {"word": "오늘의 토익 비즈니스 영단어", "photo": "오늘의 증명사진 규격",
           "search": "App Store에서 '{s}' 검색", "both": "App Store · Google Play에서 '{s}' 검색",
           "button": "App Store에서 받기", "bio": "링크는 프로필에", "head": "머리 길이(턱~정수리) {h} mm",
           "check": "규정은 바뀔 수 있어요. 신청 전 공식 안내를 확인하세요", "example": "예문"},
}
BACKGROUND = {
    "white": {"en": "White background", "zh-Hant": "白色背景", "ja": "白い背景", "ko": "흰색 배경"},
    "white_or_off_white": {"en": "White or off-white background", "zh-Hant": "白色或米白色背景",
                           "ja": "白またはオフホワイトの背景", "ko": "흰색 또는 미색 배경"},
    "cream_or_grey": {"en": "Plain cream or light grey background", "zh-Hant": "素色米色或淺灰背景",
                      "ja": "無地のクリーム色か薄いグレーの背景", "ko": "무지 크림색 또는 연회색 배경"},
    "plain_light": {"en": "Plain, light-coloured background", "zh-Hant": "素色淺色背景",
                    "ja": "無地の淡い色の背景", "ko": "무지의 밝은 색 배경"},
    "white_or_light": {"en": "Plain white or light-coloured background", "zh-Hant": "素色白色或淺色背景",
                       "ja": "無地の白か淡い色の背景", "ko": "흰색 또는 밝은 색 무지 배경"},
    "white_or_light_grey": {"en": "Plain white or light grey background", "zh-Hant": "素色白色或淺灰背景",
                            "ja": "無地の白か薄いグレーの背景", "ko": "흰색 또는 연회색 무지 배경"},
    "light_not_white": {"en": "Light blue or light grey, not white", "zh-Hant": "淺藍或淺灰，不可用白色",
                        "ja": "薄い青か薄いグレー（白は不可）", "ko": "연한 파랑 또는 연회색 (흰색 불가)"},
}
ZHUYIN_TIPS = ["跟孩子一起大聲唸三次", "找找看家裡哪些東西有這個音", "用手指在空中寫一寫", "唸給爸爸媽媽聽"]
KIND_TIP = {"聲母": "聲母：放在最前面的音", "介音": "介音：夾在中間的音", "韻母": "韻母：放在後面的音"}


def load(path=DATA):
    return json.loads(path.read_text(encoding="utf-8"))


def pick(day, data=None):
    """Today's card: type, item, locale and app. Types rotate daily; within a
    type the items go in order and the locales shift once per full pass, so a
    word or size comes back in a different language."""
    data = data or load()
    n = day.toordinal() - EPOCH.toordinal()
    kind = TYPES[n % len(TYPES)]
    k = n // len(TYPES)
    items = data[{"word": "words", "zhuyin": "zhuyin", "photo": "photos"}[kind]]
    item = items[k % len(items)]
    locales = LOCALES[kind]
    locale = locales[(k + k // len(items)) % len(locales)]
    app = {"word": "aim990" if k % 2 == 0 else "wordmatelite", "zhuyin": "lumibopomofo", "photo": "snapportlite"}[kind]
    return {"type": kind, "item": item, "locale": locale, "app": app, "key": f"utility/{kind}/{item['id']}/{locale}"}


def campaign(card, channel):
    return f"ut_{card['type']}_{card['app']}_{channel}"[:40]


def store_url(card, channel):
    query = urllib.parse.urlencode({"pt": "118326163", "ct": campaign(card, channel), "mt": "8"})
    return f"https://apps.apple.com/{STORE[card['locale']]}/app/id{APPS[card['app']]['id']}?{query}"


def store_line(card):
    app = APPS[card["app"]]
    t = TEXT[card["locale"]]
    return (t["both"] if play_store_url(app["id"], "ut") else t["search"]).format(s=app["name"])


def lines(card):
    """Headline, body lines and the app line (shared by the card and the caption)."""
    item, loc, t = card["item"], card["locale"], TEXT[card["locale"]]
    if card["type"] == "word":
        meaning = item["meaning"][loc]
        return t["word"], f"{item['word']}  ({item['pos']})", [meaning, f"{t['example']}: {item['example']}"]
    if card["type"] == "zhuyin":
        return t["zhuyin"], item["symbol"], [f"{item['word']}  {' '.join(item['zhuyin'])}", KIND_TIP[item["kind"]]]
    size = item.get("size", {}).get(loc) or f"{item['w']} × {item['h']} mm"
    body = [size]
    if item.get("head"):
        body.append(t["head"].format(h=item["head"]))
    body.append(BACKGROUND[item["bg"]][loc])
    return t["photo"], item["doc"][loc], body


def caption(card, day):
    head, big, body = lines(card)
    app = APPS[card["app"]]
    extra = []
    if card["type"] == "zhuyin":
        extra.append(ZHUYIN_TIPS[day.toordinal() % len(ZHUYIN_TIPS)])
    if card["type"] == "photo":
        extra.append(TEXT[card["locale"]]["check"])
    return "\n".join([f"{head}：{big}" if card["locale"] in ("zh-Hant", "ja") else f"{head}: {big}", *body, *extra,
                      "", f"{app['name']}: {app['pitch'][card['locale']]}", store_line(card)])


def threads_planned(day, clips_path=CLIPS):
    """Threads posts already planned for the day: the 11:00 picture slot (a
    queued post, the countdown card or a picture post, always one) plus the
    hook clips scheduled for Threads."""
    try:
        schedule = json.loads(clips_path.read_text(encoding="utf-8")).get("schedule", [])
    except (OSError, ValueError):
        schedule = []
    return 1 + sum(1 for e in schedule if e.get("channel") == "threads" and e.get("date") == day.isoformat())


def threads_has_room(day, clips_path=CLIPS):
    return threads_planned(day, clips_path) < THREADS_CAP


def _rgb(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def make(out, day, data=None):
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
    card = pick(day, data)
    app = APPS[card["app"]]
    loc = card["locale"]
    W, H = 1080, 1350
    top, bottom, accent = (_rgb(c) for c in app["colors"])
    img = Image.new("RGB", (W, H))
    px = ImageDraw.Draw(img)
    for y in range(H):
        k = y / H
        px.line([(0, y), (W, y)], fill=tuple(int(top[i] + (bottom[i] - top[i]) * k) for i in range(3)))
    draw = ImageDraw.Draw(img)
    idx = cd.FONT_INDEX.get(loc, 0)
    f = lambda size, i=idx: ImageFont.truetype(cd.FONT, size, index=i)

    def center(text, y, size, fill, i=idx, gap=1.25):
        font = f(size, i)
        w = draw.textlength(text, font=font)
        while w > W - 120 and size > 26:
            size -= 4
            font = f(size, i)
            w = draw.textlength(text, font=font)
        draw.text(((W - w) / 2, y), text, font=font, fill=fill)
        return y + int(size * gap)

    white = (255, 255, 255)
    head, big, body = lines(card)
    y = center(head, 70, 54, accent)
    if card["type"] == "zhuyin":
        zi = cd.FONT_INDEX["zh-Hant"]
        y = center(big, y + 10, 230, white, zi, 1.15)
        # Example word: each character with its 注音 underneath.
        chars = list(card["item"]["word"])
        cw = 170
        x0 = (W - cw * len(chars)) / 2
        for j, (ch, zy) in enumerate(zip(chars, card["item"]["zhuyin"])):
            cx = x0 + cw * j + cw / 2
            fc = f(120, zi)
            draw.text((cx - draw.textlength(ch, font=fc) / 2, y), ch, font=fc, fill=white)
            fz = f(48, zi)
            draw.text((cx - draw.textlength(zy, font=fz) / 2, y + 150), zy, font=fz, fill=accent)
        y += 230
        y = center(body[1], y, 40, white)
        center(ZHUYIN_TIPS[day.toordinal() % len(ZHUYIN_TIPS)], y + 4, 40, white)
    elif card["type"] == "word":
        y = center(big, y + 20, 110, white, 0, 1.2)
        y = center(body[0], y + 30, 64, accent)
        y += 20
        font = f(36, 0)
        words, line, out_lines = body[1].split(" "), "", []
        for w_ in words:  # wrap the English example
            trial = (line + " " + w_).strip()
            if draw.textlength(trial, font=font) > W - 160 and line:
                out_lines.append(line)
                line = w_
            else:
                line = trial
        out_lines.append(line)
        for ln in out_lines[:3]:
            y = center(ln, y + 4, 36, white, 0)
    else:
        y = center(big, y + 16, 72, white, idx, 1.2)
        # The photo's real proportions with its size written beside it.
        item = card["item"]
        ph = 250
        pw = int(ph * item["w"] / item["h"])
        x = 140
        draw.rounded_rectangle([x, y + 20, x + pw, y + 20 + ph], radius=10, fill=(250, 250, 252), outline=accent, width=4)
        hx, hy = x + pw / 2, y + 20 + ph * 0.42
        draw.ellipse([hx - pw * 0.2, hy - ph * 0.2, hx + pw * 0.2, hy + ph * 0.2], fill=(200, 196, 220))
        draw.pieslice([hx - pw * 0.42, y + 20 + ph * 0.7, hx + pw * 0.42, y + 20 + ph * 1.3], 180, 360, fill=(200, 196, 220))
        ty = y + 30
        for k, ln in enumerate(body):
            size = 52 if k == 0 else 34
            font = f(size)
            while draw.textlength(ln, font=font) > W - (x + pw + 60) - 70 and size > 22:
                size -= 2
                font = f(size)
            draw.text((x + pw + 60, ty), ln, font=font, fill=accent if k == 0 else white)
            ty += int(size * 1.6)
        y += ph + 50
        center(TEXT[loc]["check"], y, 30, white)
    # The real app screen (localized App Store screenshot) rising from the bottom.
    shot = ASSETS / f"{card['app']}_{loc}.png"
    if not shot.exists():
        shot = ASSETS / f"{card['app']}_en.png"
    phone = Image.open(shot).convert("RGBA")
    pw = 400
    phone = phone.resize((pw, int(phone.height * pw / phone.width)), Image.LANCZOS)
    shadow = Image.new("RGBA", (pw + 80, phone.height + 80), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([40, 50, pw + 40, phone.height + 40], radius=50, fill=(0, 0, 0, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(24))
    top_y = 790
    img.paste(shadow, ((W - pw) // 2 - 40, top_y - 40), shadow)
    img.paste(phone, ((W - pw) // 2, top_y), phone)
    fade = Image.new("RGBA", (W, 300), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fade)
    for i in range(300):
        fd.line([(0, i), (W, i)], fill=bottom + (int(255 * min(1, i / 180)),))
    img.paste(fade, (0, H - 300), fade)
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([90, 1160, W - 90, 1260], radius=50, fill=white)
    store = store_line(card)
    size = 38
    font = f(size)
    while draw.textlength(store, font=font) > W - 240:
        size -= 2
        font = f(size)
    draw.text(((W - draw.textlength(store, font=font)) / 2, 1210 - size * 0.62), store, font=font, fill=top)
    center(app["pitch"][loc], 1280, 32, white)
    img.save(out, "JPEG", quality=90)
    meta = {"type": card["type"], "item": card["item"]["id"], "locale": loc, "app": card["app"],
            "key": card["key"], "date": day.isoformat(), "caption": caption(card, day)}
    Path(out).with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta


def card_from_meta(meta, data=None):
    data = data or load()
    items = data[{"word": "words", "zhuyin": "zhuyin", "photo": "photos"}[meta["type"]]]
    item = next(x for x in items if x["id"] == meta["item"])
    return {"type": meta["type"], "item": item, "locale": meta["locale"], "app": meta["app"], "key": meta["key"]}


def _permalink(api, media, token):
    try:
        return cd._get(f"{api}/{media}?fields=permalink&access_token={token}").get("permalink")
    except Exception as exc:  # the post is up; a missing link must not fail the run
        print(f"utility: permalink lookup skipped ({exc.__class__.__name__})")
        return None


def post_telegram(card_path, meta, card):
    app = APPS[card["app"]]
    row = [{"text": TEXT[card["locale"]]["button"], "url": store_url(card, "tg")}]
    play = play_store_url(app["id"], campaign(card, "tg"))
    if play:
        row.append({"text": "Google Play", "url": play})
    result = cd.send_photo(card_path, meta["caption"], row, label="utility")
    if not result or not result.get("ok"):
        return None
    message = result["result"]
    username = (message.get("chat") or {}).get("username")
    return f"https://t.me/{username}/{message['message_id']}" if username else ""


def post_threads(url, meta, card, day):
    if not threads_has_room(day):
        print(f"utility: Threads already has {threads_planned(day)} posts planned today (cap {THREADS_CAP}); skipped")
        return None
    import os
    links = [f"App Store: {store_url(card, 'th')}"]
    play = play_store_url(APPS[card["app"]]["id"], campaign(card, "th"))
    if play:
        links.append(f"Google Play: {play}")
    media = cd.threads_image(url, meta["caption"], links, label="utility")
    if not media:
        return None
    return _permalink("https://graph.threads.net/v1.0", media, os.environ.get("THREADS_TOKEN", "")) or ""


def post_instagram(url, meta, card):
    import os
    media = cd.instagram_image(url, meta["caption"] + "\n" + TEXT[card["locale"]]["bio"], label="utility")
    if not media:
        return None
    return _permalink("https://graph.instagram.com/v21.0", media, os.environ.get("IG_ACCESS_TOKEN", "")) or ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["make", "post"])
    ap.add_argument("--out", default="card.jpg")
    ap.add_argument("--card", default="card.jpg")
    ap.add_argument("--url", help="public URL of the card (Threads and Instagram fetch it)")
    ap.add_argument("--date", help="YYYY-MM-DD (Taiwan date), default today")
    ap.add_argument("--only", help="post to this channel only (telegram, threads or instagram)")
    args = ap.parse_args()
    day = dt.date.fromisoformat(args.date) if args.date else cd.today_tw()
    if args.cmd == "make":
        print(json.dumps(make(args.out, day), ensure_ascii=False))
        return 0
    import clip_progress
    meta = json.loads(Path(args.card).with_suffix(".json").read_text(encoding="utf-8"))
    card = card_from_meta(meta)
    for name, fn in (("telegram", lambda: post_telegram(args.card, meta, card)),
                     ("instagram", lambda: post_instagram(args.url, meta, card)),
                     ("threads", lambda: post_threads(args.url, meta, card, day))):
        if args.only and name != args.only:
            continue
        try:
            link = fn()
        except Exception as exc:  # one channel failing never blocks the others
            print(f"utility: {name} failed ({exc})")
            continue
        if link is not None:
            # The promotion page (office.cait518.cc) lists every post's link.
            clip_progress.record_post(name, meta["key"], link or None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
