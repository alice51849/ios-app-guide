#!/usr/bin/env python3
"""Daily utility cards: one genuinely useful image a day, branded with the app
that does the job (zero token).

Nine card types take turns day by day, all from curated static lists in
.github/growth/utility-cards.json (no paid API, no model at runtime):

- word    TOEIC-style business English word of the day -> Aim990 / Wordmate Lite
- zhuyin  注音 of the day for kids (zh-Hant)            -> Lumi注音星球
- photo   passport / ID photo size of the day            -> Snapport Lite
- letter  ABC letter of the day + a first word          -> Lumi Letters Lite
- count   number of the day, counted out on ten-frames  -> Lumi Math Planet
- bedtime five bedtime steps for small children         -> Lumi Mission Planet
- ledger  one project's income minus expenses, worked   -> MoneyTag
- chore   an easily forgotten recurring chore + a
          conservative suggested interval               -> Mochi DoneStamp
- checklist a short, ready-to-copy 4-task list for one
          situation (study session, Sunday reset…)      -> Mochi (added 2026-10-17, last in the
          rotation so the first eight keep their days until 10-23)

The app screen on every card is a real App Store screenshot of that app
(assets/utility/<app>_<locale>.png, taken from the public iTunes Lookup API).

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
import download_links as DL  # noqa: E402
import threads_cap  # noqa: E402
from social_post_common import play_store_url  # noqa: E402

GROWTH = HERE.parent / "growth"
DATA = GROWTH / "utility-cards.json"
CLIPS = GROWTH / "clips.json"
ASSETS = GROWTH / "assets" / "utility"  # localized App Store screenshots
STORE = {"ko": "kr", "zh-Hant": "tw", "ja": "jp", "en": "us"}
TYPES = ("word", "zhuyin", "photo", "letter", "count", "bedtime", "ledger", "chore", "checklist")
ALL4 = ("zh-Hant", "en", "ja", "ko")
LOCALES = {"word": ("zh-Hant", "ja", "ko", "en"), "zhuyin": ("zh-Hant",), "photo": ("en", "zh-Hant", "ja", "ko"),
           "letter": ALL4, "count": ALL4, "bedtime": ALL4, "ledger": ALL4, "chore": ALL4, "checklist": ALL4}
LISTS = {"word": "words", "zhuyin": "zhuyin", "photo": "photos", "letter": "letters", "count": "counting",
         "bedtime": "bedtime", "ledger": "ledger", "chore": "chores",
         "checklist": "checklists"}  # curated list per type in DATA
TYPE_APP = {"zhuyin": "lumibopomofo", "photo": "snapportlite", "letter": "lumiletters", "count": "lumimath",
            "bedtime": "lumimission", "ledger": "moneytag", "chore": "mochidonestamp",
            "checklist": "mochi"}  # word: Aim990 / Wordmate
EPOCH = dt.date(2026, 10, 15)  # day 0 of the rotation: first word, ㄅ, first photo size
THREADS_CAP = threads_cap.ACCOUNT_DAILY_CAP  # posts a day on the Threads account, everything included

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
    # Pitch lines below are taken from each app's own App Store description (iTunes Lookup, 2026-10-16);
    # "names" is the localized store name people search for in that storefront.
    "lumiletters": {"id": "6778748533", "name": "Lumi Letters Lite", "colors": ("#2a2366", "#6a4fc4", "#ffd76a"),
                    "names": {"zh-Hant": "Lumi 字母星球 Lite", "ja": "Lumi レター Lite", "ko": "Lumi 레터 Lite"},
                    "pitch": {"zh-Hant": "三到七歲，聽字母發音、描寫大寫與小寫",
                              "en": "Ages 3–7: hear each letter, trace big and small",
                              "ja": "3〜7歳。文字の音を聞いて、大文字・小文字をなぞり書き",
                              "ko": "3~7세, 글자 소리를 듣고 대문자와 소문자를 따라쓰기"}},
    "lumimath": {"id": "6778269699", "name": "Lumi Math Planet", "colors": ("#14264f", "#3a5fb0", "#ffe08a"),
                 "names": {"zh-Hant": "Lumi數學星球", "ja": "Lumi算数プラネット", "ko": "Lumi 수학 행성"},
                 "pitch": {"zh-Hant": "答對一題，小星球就亮起來", "en": "Solve a question and a little planet lights up",
                           "ja": "1問解くたびに、小さな星がひとつ灯ります", "ko": "문제를 맞힐 때마다 작은 행성에 불이 켜져요"}},
    "lumimission": {"id": "6779750237", "name": "Lumi Mission Planet", "colors": ("#231a4d", "#5a4a9e", "#ffc7e0"),
                    "names": {"zh-Hant": "Lumi 任務星球", "ja": "Lumi ミッション星", "ko": "Lumi 미션 별"},
                    "pitch": {"zh-Hant": "把每日生活常規變成溫柔的小任務", "en": "Turns daily routines into gentle missions",
                              "ja": "毎日のせいかつを小さなミッションに", "ko": "하루 일과를 다정한 미션으로"}},
    "moneytag": {"id": "6801956402", "name": "MoneyTag", "colors": ("#0f3b2e", "#2f7a5c", "#c8f5a0"),
                 "pitch": {"zh-Hant": "每個專案各自算淨額，同一標籤跨專案合計",
                           "en": "Projects with their own net result",
                           "ja": "プロジェクトごとの純額とタグ集計",
                           "ko": "프로젝트마다 따로 계산되는 순액"}},
    # Mochi (checklist type): the names are the store names people type into the search box in each storefront,
    # the pitch lines are the first sentence of each storefront's own description (iTunes Lookup, 2026-10-17).
    "mochi": {"id": "6785004775", "name": "Mochi Cute Checklist", "colors": ("#4f2346", "#9b4f77", "#ffd6e7"),
              "names": {"zh-Hant": "Mochi 可愛待辦清單", "ja": "Mochi かわいいToDo", "ko": "Mochi 귀여운 할 일 목록"},
              "pitch": {"en": "Add tasks, tap the little circle when you finish",
                        "zh-Hant": "寫下任務，輕點小圓圈完成打勾",
                        "ja": "タスクを書いて、終わったら小さな丸をタップ",
                        "ko": "할 일을 적고, 끝나면 작은 동그라미를 탭하세요"}},
    "mochidonestamp": {"id": "6790800323", "name": "Mochi DoneStamp", "colors": ("#4a2a3a", "#9a5a76", "#ffe6b8"),
                       "pitch": {"zh-Hant": "事情做完點一下，記住上次是什麼時候",
                                 "en": "Finish something, tap once, and the exact time is kept",
                                 "ja": "済ませたら一度タップ。正確な日時が履歴に残ります",
                                 "ko": "일을 마치고 한 번 탭하면 정확한 시간이 기록으로 남아요"}},
}
TEXT = {
    "en": {"word": "Business English word of the day", "photo": "Photo size of the day",
           "search": "Search “{s}” on the App Store", "both": "Search “{s}” on App Store or Google Play",
           "button": "Get it on the App Store", "head": "Head (chin to crown): {h} mm",
           "check": "Rules change: check the official site before you apply.", "example": "Example",
           "letter": "Letter of the day", "count": "Let's count", "bedtime": "Tonight's 5 bedtime steps",
           "ledger": "Project net, worked out", "chore": "When did you last do it?", "is_for": "{l} is for {w}",
           "net": "Net", "ledger_note": "Example numbers, just to show the math",
           "chore_note": "A general suggestion: follow the product manual", "last": "Last time: ___ days ago",
           "bedtime_note": "Change the order to suit your child",
           "fingers": "Hold up {n} on one hand", "five": "One hand of 5, then {r} more", "ten": "Both hands make 10",
           "teen": "Both hands make 10, then {r} more", "twenty": "Count both hands two times",
           "checklist": "Today's 4-task checklist"},
    "zh-Hant": {"word": "今日多益商務單字", "zhuyin": "今日注音", "photo": "今日證件照尺寸",
                "search": "App Store 搜尋「{s}」", "both": "App Store／Google Play 搜尋「{s}」",
                "button": "在 App Store 下載", "head": "頭部（下巴到頭頂）{h} mm",
                "check": "規定可能更新，送件前請先確認官方說明", "example": "例句",
                "letter": "今日字母", "count": "今日數一數", "bedtime": "今晚睡前 5 步", "ledger": "專案損益小算式",
                "chore": "上次做是幾天前？", "is_for": "{l} — {w}", "net": "淨額",
                "ledger_note": "示例數字，只示範算式", "chore_note": "週期為一般建議，請以產品說明書為準",
                "last": "上次：___ 天前", "bedtime_note": "順序可依孩子習慣調整",
                "fingers": "伸出 {n} 根手指", "five": "一隻手 5 根，再加 {r} 根", "ten": "兩隻手剛好 10 根",
                "teen": "兩隻手 10 根，再數 {r} 個", "twenty": "兩隻手各數兩次",
                "checklist": "今天的 4 件事"},
    "ja": {"word": "今日のTOEIC®ビジネス英単語", "photo": "今日の証明写真サイズ",
           "search": "App Storeで「{s}」を検索", "both": "App Store・Google Playで「{s}」を検索",
           "button": "App Storeで入手", "head": "頭の長さ（あご〜頭頂）{h} mm",
           "check": "規定は変わることがあります。申請前に公式情報をご確認ください", "example": "例文",
           "letter": "今日のアルファベット", "count": "今日のかぞえてみよう", "bedtime": "今夜のおやすみ5ステップ",
           "ledger": "プロジェクト収支の計算例", "chore": "最後にやったのは何日前？", "is_for": "{l} — {w}",
           "net": "純額", "ledger_note": "数字は計算の例です", "chore_note": "周期は一般的な目安です。取扱説明書に従ってください",
           "last": "前回：___ 日前", "bedtime_note": "順番はお子さまに合わせて変えてOK",
           "fingers": "ゆびを {n}本 たてよう", "five": "かた手で5、もうかた手で{r}", "ten": "りょう手で ちょうど10",
           "teen": "りょう手で10、あと{r}つ", "twenty": "りょう手を2かい かぞえよう",
           "checklist": "今日の4つのToDo"},
    "ko": {"word": "오늘의 토익 비즈니스 영단어", "photo": "오늘의 증명사진 규격",
           "search": "App Store에서 '{s}' 검색", "both": "App Store · Google Play에서 '{s}' 검색",
           "button": "App Store에서 받기", "head": "머리 길이(턱~정수리) {h} mm",
           "check": "규정은 바뀔 수 있어요. 신청 전 공식 안내를 확인하세요", "example": "예문",
           "letter": "오늘의 알파벳", "count": "오늘의 숫자 세기", "bedtime": "오늘 밤 잠자기 전 5단계",
           "ledger": "프로젝트 손익 계산 예시", "chore": "마지막으로 한 게 며칠 전?", "is_for": "{l} — {w}",
           "net": "순액", "ledger_note": "숫자는 계산 예시예요", "chore_note": "일반적인 권장 주기예요. 제품 설명서를 따르세요",
           "last": "마지막: ___일 전", "bedtime_note": "순서는 아이에게 맞게 바꿔도 돼요",
           "fingers": "손가락 {n}개를 펴 봐요", "five": "한 손 5개, 다른 손 {r}개", "ten": "두 손을 다 펴면 10",
           "teen": "두 손 10개, 그리고 {r}개 더", "twenty": "두 손을 두 번 세어 봐요",
           "checklist": "오늘의 할 일 4가지"},
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
LETTER_TIPS = {
    "zh-Hant": ["跟孩子一起大聲唸三次", "用手指在空中寫大寫和小寫", "找找家裡哪裡有這個字母", "想想還有哪個字也是這個音開頭"],
    "en": ["Say it out loud three times together", "Trace the big and small letter in the air",
           "Spot this letter around the house", "Think of another word that starts with it"],
    "ja": ["いっしょに3回、声に出して言おう", "ゆびで空中に大文字と小文字を書こう", "おうちの中でこの文字をさがそう",
           "同じ音ではじまることばをさがそう"],
    "ko": ["함께 소리 내어 세 번 읽어요", "손가락으로 허공에 대문자와 소문자를 써 봐요", "집 안에서 이 글자를 찾아봐요",
           "이 소리로 시작하는 다른 단어를 떠올려 봐요"],
}


def load(path=DATA):
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve(kind, item, data):
    """The item with the shared vocabulary it points at filled in (count objects, bedtime steps)."""
    if kind == "count":
        return dict(item, say=data["count_things"][item["thing"]])
    if kind == "bedtime":
        return dict(item, step_text=[data["bedtime_steps"][s] for s in item["steps"]])
    return item


def pick(day, data=None):
    """Today's card: type, item, locale and app. Types rotate daily; within a
    type the items go in order and the locales shift once per full pass, so a
    word or size comes back in a different language."""
    data = data or load()
    n = day.toordinal() - EPOCH.toordinal()
    kind = TYPES[n % len(TYPES)]
    k = n // len(TYPES)
    items = data[LISTS[kind]]
    item = _resolve(kind, items[k % len(items)], data)
    locales = LOCALES[kind]
    locale = locales[(k + k // len(items)) % len(locales)]
    app = ("aim990" if k % 2 == 0 else "wordmatelite") if kind == "word" else TYPE_APP[kind]
    return {"type": kind, "item": item, "locale": locale, "app": app,
            "key": f"utility/{kind}/{app}/{item['id']}/{locale}"}  # own_posts.Catalog reads app and locale from it


def campaign(card, channel):
    """ut_<app>_<platform>: the card type stays in the post log; per-type tokens split the same
    downloads into rows Apple never reveals (it shows a campaign only past 5 first-time downloads)."""
    return f"ut_{card['app']}_{channel}"[:40]


def store_url(card, channel):
    # Sent at channel level (download_links.coarse_campaign): ut_<app>_<platform> stays the post log's label.
    query = urllib.parse.urlencode({"pt": "118326163", "ct": DL.coarse_campaign(campaign(card, channel)), "mt": "8"})
    return f"https://apps.apple.com/{STORE[card['locale']]}/app/id{APPS[card['app']]['id']}?{query}"


CHANNEL_CT = {"instagram": "ig", "telegram": "tg", "threads": "th"}


def download_urls(card, channel):
    """(App Store URL, Google Play URL or None) for one channel."""
    ch = CHANNEL_CT.get(channel, channel)
    return store_url(card, ch), play_store_url(APPS[card["app"]]["id"], campaign(card, ch))


def link_lines(card, channel):
    """The "label: URL" lines that carry the direct download link(s) in the post text."""
    store, play = download_urls(card, channel)
    lines = [f"{TEXT[card['locale']]['button']}: {store}"]
    if play:
        lines.append(f"Google Play: {play}")
    return lines


def app_name(card):
    """The app's store name in the card's storefront (what people type into the search box)."""
    app = APPS[card["app"]]
    return app.get("names", {}).get(card["locale"], app["name"])


def store_line(card):
    app = APPS[card["app"]]
    t = TEXT[card["locale"]]
    if play_store_url(app["id"], "ut"):  # the rank data is App Store only: both stores get the store name
        return t["both"].format(s=app_name(card))
    import search_caption as SC
    return t["search"].format(s=SC.search_term(card["app"], card["locale"], fallback=app_name(card)))


def money(v):
    return f"{v:,}" if v >= 0 else f"−{-v:,}"


def ledger_net(item):
    return sum(e["amount"] for e in item["income"]) - sum(e["amount"] for e in item["expenses"])


def count_lines(n, loc):
    """(how many, the ten-frame sum or None, the finger tip) for the number of the day."""
    t = TEXT[loc]
    return (None if n <= 5 else f"5 + {n - 5} = {n}" if n <= 10 else f"10 + {n - 10} = {n}",
            t["fingers"].format(n=n) if n <= 5 else t["five"].format(r=n - 5) if n < 10 else t["ten"] if n == 10
            else t["teen"].format(r=n - 10) if n < 20 else t["twenty"])


def lines(card):
    """Headline, body lines and the app line (shared by the card and the caption)."""
    item, loc, t = card["item"], card["locale"], TEXT[card["locale"]]
    if card["type"] == "word":
        meaning = item["meaning"][loc]
        return t["word"], f"{item['word']}  ({item['pos']})", [meaning, f"{t['example']}: {item['example']}"]
    if card["type"] == "zhuyin":
        return t["zhuyin"], item["symbol"], [f"{item['word']}  {' '.join(item['zhuyin'])}", KIND_TIP[item["kind"]]]
    if card["type"] == "letter":
        return t["letter"], f"{item['letter']} {item['letter'].lower()}", [
            t["is_for"].format(l=item["letter"], w=item["word"]), item["meaning"][loc]]
    if card["type"] == "count":
        n, say = item["n"], item["say"][loc]
        how_many = f"{n} {say[0] if n == 1 else say[1]}" if loc == "en" else say.format(n=n)
        eq, tip = count_lines(n, loc)
        return t["count"], str(n), [how_many, *([eq] if eq else []), tip]
    if card["type"] == "bedtime":
        return t["bedtime"], item["theme"][loc], [f"{i}. {s[loc]}" for i, s in enumerate(item["step_text"], 1)]
    if card["type"] == "ledger":
        rows = [f"+ {e['label'][loc]} {money(e['amount'])}" for e in item["income"]]
        rows += [f"− {e['label'][loc]} {money(e['amount'])}" for e in item["expenses"]]
        return t["ledger"], item["project"][loc], rows + [f"= {t['net']} {money(ledger_net(item))}"]
    if card["type"] == "chore":
        return t["chore"], item["task"][loc], [item["every"][loc]]
    if card["type"] == "checklist":
        return t["checklist"], item["title"][loc], [f"○ {x}" for x in item["items"][loc]]
    size = item.get("size", {}).get(loc) or f"{item['w']} × {item['h']} mm"
    body = [size]
    if item.get("head"):
        body.append(t["head"].format(h=item["head"]))
    body.append(BACKGROUND[item["bg"]][loc])
    return t["photo"], item["doc"][loc], body


def caption(card, day):
    head, big, body = lines(card)
    app = APPS[card["app"]]
    t = TEXT[card["locale"]]
    extra = []
    if card["type"] == "zhuyin":
        extra.append(ZHUYIN_TIPS[day.toordinal() % len(ZHUYIN_TIPS)])
    if card["type"] == "letter":
        tips = LETTER_TIPS[card["locale"]]
        extra.append(tips[day.toordinal() % len(tips)])
    if card["type"] == "photo":
        extra.append(t["check"])
    if card["type"] == "checklist":
        extra.append(card["item"]["tip"][card["locale"]])
    extra += [t[n] for k, n in (("bedtime", "bedtime_note"), ("ledger", "ledger_note"), ("chore", "chore_note"))
              if card["type"] == k]
    if head.endswith(("?", "？")):
        lead = f"{head} {big}"
    else:
        lead = f"{head}：{big}" if card["locale"] in ("zh-Hant", "ja") else f"{head}: {big}"
    return "\n".join([lead, *body, *extra, "", f"{app_name(card)}: {app['pitch'][card['locale']]}", store_line(card)])


def threads_planned(day, clips_path=CLIPS):
    """Threads posts already planned for the day: the 11:00 picture slot (a
    queued post, the countdown card or a picture post, always one), the 21:00
    evening slot (a threads_series.py post or the slot-15 hook clip, always
    one) plus the other hook clips scheduled for Threads."""
    try:
        schedule = json.loads(clips_path.read_text(encoding="utf-8")).get("schedule", [])
    except (OSError, ValueError):
        schedule = []
    return 2 + sum(1 for e in schedule if e.get("channel") == "threads" and e.get("date") == day.isoformat()
                   and e.get("slot") != 15)


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
    cd.gradient(ImageDraw.Draw(img), W, H, top, bottom)  # every row keeps white text at AA contrast
    draw = ImageDraw.Draw(img)
    idx = cd.FONT_INDEX.get(loc, 0)
    f = lambda size, i=idx: ImageFont.truetype(cd.FONT, size, index=i)

    def center(text, y, size, fill, i=idx, gap=1.25):
        # Never below cd.MIN_TEXT: a line that does not fit wraps instead of shrinking into the unreadable.
        rows, size = cd.wrap(draw, text, lambda s: f(s, i), size, W - 120, min(size, cd.MIN_TEXT))
        font = f(size, i)
        for row in rows:
            draw.text(((W - draw.textlength(row, font=font)) / 2, y), row, font=font, fill=fill)
            y += int(size * gap)
        return y

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
        y = center(body[1], y, 42, white)
        center(ZHUYIN_TIPS[day.toordinal() % len(ZHUYIN_TIPS)], y + 4, 42, white)
    elif card["type"] == "word":
        y = center(big, y + 30, 130, white, 0, 1.2)
        y = center(body[0], y + 30, 72, accent)
        y += 30
        font = f(42, 0)
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
            y = center(ln, y + 6, 42, white, 0)
    elif card["type"] == "photo":
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
            rows, size = cd.wrap(draw, ln, f, 56 if k == 0 else 38, W - (x + pw + 60) - 70)
            for row in rows:
                draw.text((x + pw + 60, ty), row, font=f(size), fill=accent if k == 0 else white)
                ty += int(size * 1.3)
            ty += int(size * 0.3)
        y = max(y + ph + 50, ty + 20)
        center(TEXT[loc]["check"], y, 36, white)
    elif card["type"] == "letter":
        y = center(big, y + 6, 250, white, 0, 1.2)
        y = center(body[0], y + 10, 72, accent, 0 if loc == "en" else idx)
        y = center(body[1], y + 6, 52, white)
        tips = LETTER_TIPS[loc]
        center(tips[day.toordinal() % len(tips)], y + 14, 40, white)
    elif card["type"] == "count":
        n = card["item"]["n"]
        y = center(big, y, 150, white, 0, 1.15) + 46
        # Ten-frames: rows of five, filled dots for the number of the day.
        cell, gap = 62, 40
        frames = 1 if n <= 10 else 2
        fw = cell * 5
        x0 = (W - (fw * frames + gap * (frames - 1))) / 2
        for fr in range(frames):
            fx = x0 + fr * (fw + gap)
            draw.rounded_rectangle([fx - 8, y - 8, fx + fw + 8, y + cell * 2 + 8], radius=14, outline=accent, width=3)
            for c in range(10):
                cx, cy = fx + (c % 5) * cell + cell / 2, y + (c // 5) * cell + cell / 2
                r = cell * 0.36
                if fr * 10 + c < n:
                    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=accent)
                else:
                    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=white, width=2)
        y += cell * 2 + 34
        y = center(body[0], y, 56, accent)
        for ln in body[1:]:
            y = center(ln, y + 2, 44, white)
    elif card["type"] == "bedtime":
        y = center(big, y + 10, 64, white, idx, 1.2)
        y += 14
        fn = f(40)
        for i, step in enumerate(card["item"]["step_text"], 1):
            cx, cy, r = 190, y + 34, 30
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=accent)
            num = str(i)
            draw.text((cx - draw.textlength(num, font=fn) / 2, cy - 40 * 0.62), num, font=fn,
                      fill=top if cd.contrast(top, accent) >= cd.AA else (0, 0, 0))
            rows, size = cd.wrap(draw, step[loc], f, 46, W - 250 - 90)
            ry = cy - (len(rows) * size * 1.2) / 2
            for row in rows:
                draw.text((250, ry), row, font=f(size), fill=white)
                ry += size * 1.2
            y += max(80, int(len(rows) * size * 1.2) + 16)
        center(TEXT[loc]["bedtime_note"], y + 6, 36, white)
    elif card["type"] == "ledger":
        item = card["item"]
        y = center(big, y + 10, 68, white, idx, 1.2)
        y += 10
        left, right = 160, W - 160
        def row(sign, label, amount, size, fill):
            font = f(size)
            draw.text((left, y), f"{sign} {label}", font=font, fill=fill)
            draw.text((right - draw.textlength(amount, font=font), y), amount, font=font, fill=fill)
        for e in item["income"]:
            row("+", e["label"][loc], money(e["amount"]), 46, white)
            y += 64
        for e in item["expenses"]:
            row("−", e["label"][loc], money(e["amount"]), 46, white)
            y += 64
        draw.line([(left, y + 4), (right, y + 4)], fill=accent, width=4)
        y += 18
        row("=", TEXT[loc]["net"], money(ledger_net(item)), 58, accent)
        y += 82
        center(TEXT[loc]["ledger_note"], y, 36, white)
    elif card["type"] == "chore":
        y = center(big, y + 24, 84, white, idx, 1.2)
        y = center(body[0], y + 16, 48, accent)
        # A blank "days ago" stamp to fill in mentally.
        last = TEXT[loc]["last"]
        fl = f(52)
        lw = draw.textlength(last, font=fl)
        draw.rounded_rectangle([(W - lw) / 2 - 40, y + 20, (W + lw) / 2 + 40, y + 120], radius=24, outline=accent, width=4)
        draw.text(((W - lw) / 2, y + 70 - 52 * 0.62), last, font=fl, fill=white)
        center(TEXT[loc]["chore_note"], y + 146, 36, white)
    elif card["type"] == "checklist":
        y = center(big, y + 16, 72, white, idx, 1.2)
        y += 18
        for step in body:
            # An empty circle per task, like the one tapped in the app (the caption writes it as "○").
            cx, cy, r = 190, y + 34, 26
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=accent, width=5)
            rows, size = cd.wrap(draw, step.removeprefix("○ "), f, 46, W - 250 - 90)
            ry = cy - (len(rows) * size * 1.2) / 2
            for row in rows:
                draw.text((250, ry), row, font=f(size), fill=white)
                ry += size * 1.2
            y += max(84, int(len(rows) * size * 1.2) + 18)
        center(card["item"]["tip"][loc], y + 6, 36, accent)
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
    cd.footer_band(img, bottom, 300)  # darkened band: the pitch line under the pill stays readable
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([90, 1160, W - 90, 1260], radius=50, fill=white)
    store = store_line(card)
    size = 40
    font = f(size)
    while draw.textlength(store, font=font) > W - 240 and size > cd.MIN_TEXT - 4:
        size -= 2
        font = f(size)
    draw.text(((W - draw.textlength(store, font=font)) / 2, 1210 - size * 0.62), store, font=font,
              fill=top if cd.contrast(top, white) >= cd.AA else cd.legible(top))
    center(app["pitch"][loc], 1276, 36, white)
    img.save(out, "JPEG", quality=90)
    meta = {"type": card["type"], "item": card["item"]["id"], "locale": loc, "app": card["app"],
            "key": card["key"], "date": day.isoformat(), "caption": caption(card, day)}
    Path(out).with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    return meta


def card_from_meta(meta, data=None):
    data = data or load()
    items = data[LISTS[meta["type"]]]
    item = _resolve(meta["type"], next(x for x in items if x["id"] == meta["item"]), data)
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
    result = cd.send_photo(card_path, telegram_text(meta, card), row, label="utility",
                           guard=download_urls(card, "telegram"))
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
    media = cd.threads_image(url, meta["caption"], link_lines(card, "threads"), label="utility")
    if not media:
        return None
    return _permalink("https://graph.threads.net/v1.0", media, os.environ.get("THREADS_TOKEN", "")) or ""


def telegram_text(meta, card):
    """The Telegram caption: the card text plus the clickable download link(s)."""
    return meta["caption"] + "\n" + "\n".join(link_lines(card, "telegram"))


def instagram_text(meta, card):
    """The Instagram caption (owner 2026-10-17: no URL, Instagram cannot tap one): the card text, "📲 Download via
    the link in bio" in the card's language, then the hashtags led by the app's brand hashtag (ig_bio.py)."""
    import ig_bio
    import search_caption as SC
    name, ref = app_name(card), APPS[card["app"]]["id"]
    # keyword hashtags from the planner's seo table, after the brand hashtag
    tags = ig_bio.hashtags(lambda n: SC.card_tags(card["app"], card["locale"], n), name, ref)
    text = meta["caption"] + "\n" + ig_bio.bio_line(card["locale"]) + ("\n\n" + " ".join(tags) if tags else "")
    return ig_bio.caption(text, name, card["locale"], ref, tag_limit=SC.TAG_LIMIT.get("instagram", 5),
                          label=f"utility {card.get('key', card['app'])} instagram")


def qa_problems(meta, card, channel, image=None, online=True):
    """Pre-post QA (post_qa.py): the exact text this channel gets, the image, the live store link."""
    import post_qa
    text = {"instagram": instagram_text, "telegram": telegram_text}.get(channel, lambda m, c: m["caption"])(meta, card)
    return post_qa.card_problems(text, card["locale"], channel, store_url=store_url(card, "qa"),
                                 name=app_name(card), image=image, online=online, require_bio=True)


def post_instagram(url, meta, card):
    import os
    import search_caption as SC
    text = instagram_text(meta, card)
    alt = SC.card_alt(APPS[card["app"]]["name"], meta["caption"], card["app"], card["locale"])
    media = cd.instagram_image(url, text, label="utility", alt=alt,
                               app=(app_name(card), card["locale"], APPS[card["app"]]["id"]))
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
        import post_qa
        if not post_qa.gate(qa_problems(meta, card, name, image=args.card), f"utility {name}"):
            continue  # a broken card or caption never goes out
        try:
            link = fn()
        except Exception as exc:  # one channel failing never blocks the others
            print(f"utility: {name} failed ({exc})")
            continue
        if link is not None:
            # The promotion page (office.cait518.cc) lists every post's link.
            clip_progress.record_post(name, meta["key"], link or None)
    # A Threads post whose link reply failed is already out (the ::error:: is the alert). A red step would make the
    # watchdog re-dispatch the whole slot and post the card to Telegram and Instagram twice; link_backfill.py adds it.
    return 0


if __name__ == "__main__":
    sys.exit(main())
