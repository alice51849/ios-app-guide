#!/usr/bin/env python3
"""Template replies to comments on OUR OWN Instagram and Threads posts.

Owner request: answer people who comment under our posts, nothing else -
never a stranger's post, never a DM. No LLM: the language comes from the
script the comment is written in, the intent from keywords, and the reply from
a few short hand-written variants per language and intent, rotated so replies
don't read like a bot.

Every reply carries the direct download link of the app its post promotes (owner
rule 2026-10-17): the App Store link, plus the Google Play link when the app is on
Android - praise, language and how-to answers included. On Instagram a reply URL cannot be
tapped, so the reply also says where to tap: "📲 Link in bio → tap “<app>”" (ig_bio.py). A reply is checked before it
goes out (download_links.py); one that does not carry the link, or does not fit the
platform's length limit, is not sent and is reported with ::error::. A post that maps
to no app of ours (link_backfill.AppFinder: several proofs must agree) gets no reply
at all, whatever the comment says: there is no link to give.

Skipped (no reply): our own account, comments we already answered
(.github/growth/replied-comments.json, plus a live check), links / spam /
offensive words, complaints (a human should answer those), and anything
ambiguous - no intent match, a language without templates, or a post we can't
map to an app.

Caps: <= 20 replies a day and <= 5 a run per platform, <= 1 reply per
commenter per post, comments younger than 7 days on posts younger than 30.

    python3 comment_replies.py --dry-run        # print what would be sent
    python3 comment_replies.py                  # IG_ACCESS_TOKEN / THREADS_TOKEN
    python3 comment_replies.py --merge-state saved.json   # after a rebase
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path

import download_links as DL
import ig_bio as IGB
import ig_bio_hub as HUB
from link_backfill import LEDGER_CHANNELS, AppFinder, ios_id_for
from own_posts import (GROWTH, HERE, ApiError, Catalog, InstagramClient, ThreadsClient,
                       detect_language, load_json)
from social_post_common import SnapshotMissing, campaign_app_store_url, play_store_url

STATE = GROWTH / "replied-comments.json"
APPS = HERE.parent.parent / "apps.json"
DAILY_CAP = 20
RUN_CAP = 5
MAX_COMMENT_AGE = dt.timedelta(days=7)
MAX_POST_AGE = dt.timedelta(days=30)
KEEP_STATE = dt.timedelta(days=120)
LINK_INTENTS = ("price", "download", "android")   # these also name the link in their own template
MAX_REPLY_CHARS = {"instagram": 2200, "threads": 500}

# ------------------------------------------------------------------ filters

SPAM = re.compile(
    r"https?://|www\.|\.(com|net|io|ly|me|xyz|shop)\b|t\.me/|wa\.me/"
    r"|\b(dm me|dm us|check my|follow (me|back)|promo(te|tion)?|collab|crypto|bitcoin|btc|forex|invest(ment)?"
    r"|earn \$|onlyfans|telegram|whatsapp|sugar ?daddy|giveaway|nude|sex|porn|fuck|shit|bitch|cunt|nigg)"
    r"|加我|私訊我|私信|賺錢|赚钱|兼職|兼职|代購|博彩|色情|幹你|干你|操你|傻逼|白痴|垃圾"
    r"|副業|稼げる|出会い|死ね|부업|토토|카지노|시발|씨발|병신|รายได้เสริม|พนัน|เว็บพนัน|kiếm tiền|cá cược",
    re.I)
COMPLAINT = re.compile(
    r"\b(bug|crash(es|ed|ing)?|broken|refund|scam|doesn'?t work|not working|won'?t open|terrible|worst|useless|waste)\b"
    r"|閃退|闪退|不能用|沒反應|没反应|退款|退費|騙|骗|爛|烂|難用|难用|壞了|坏了"
    r"|バグ|落ちる|返金|使えない|最悪|詐欺"
    r"|오류|버그|환불|안돼요|안 돼요|최악|사기"
    r"|ใช้ไม่ได้|ค้าง|คืนเงิน|ห่วย|หลอก"
    r"|lỗi|không dùng được|hoàn tiền|lừa đảo|tệ", re.I)


def _kw(en=(), zh=(), ja=(), ko=(), th=(), vi=()):
    # Latin-script words need word boundaries ("giá" must not match "giáo").
    # Boundaries are Latin letters only, so "Android版" still matches.
    lat = "A-Za-z\u00c0-\u024f\u1e00-\u1eff"
    words = r"|".join(rf"(?<![{lat}])" + re.escape(w).replace(r"\ ", r"\s+") + rf"(?![{lat}])" for w in (*en, *vi))
    other = r"|".join(re.escape(w) for w in (*zh, *ja, *ko, *th))
    return re.compile("|".join(p for p in (words, other) if p), re.I)


# Checked in this order; the first match wins.
INTENTS = [
    ("android", _kw(en=("android", "google play", "play store", "galaxy", "samsung", "pixel"),
                    zh=("安卓", "安卓版"), ja=("アンドロイド",), ko=("안드로이드", "갤럭시"),
                    th=("แอนดรอยด์",))),
    ("price", _kw(en=("price", "cost", "costs", "free", "how much", "paid", "subscription", "pricing"),
                  zh=("多少錢", "多少钱", "免費", "免费", "價格", "价格", "收費", "收费", "要錢", "要钱", "付費", "付费", "訂閱", "订阅"),
                  ja=("無料", "値段", "価格", "いくら", "有料", "課金", "サブスク"),
                  ko=("무료", "가격", "얼마", "유료", "결제", "구독"),
                  th=("ฟรี", "ราคา", "เท่าไหร่", "เสียเงิน"),
                  vi=("miễn phí", "giá", "bao nhiêu", "trả phí", "mất phí"))),
    ("download", _kw(en=("download", "where can i get", "where do i get", "what app", "which app", "app name",
                         "name of the app", "what's the app", "what is the app", "link"),
                     zh=("下載", "下载", "連結", "链接", "哪裡載", "哪里下", "叫什麼", "叫什么", "app名", "哪個app", "哪个app"),
                     ja=("ダウンロード", "どこで", "アプリ名", "何のアプリ", "なんてアプリ", "リンク"),
                     ko=("다운", "어디서", "앱 이름", "무슨 앱", "링크"),
                     th=("ดาวน์โหลด", "โหลดที่ไหน", "ชื่อแอป", "แอปอะไร", "ลิงก์"),
                     vi=("tải", "ở đâu", "tên app", "app gì", "app nào"))),
    ("language", _kw(en=("language", "languages", "english", "chinese", "japanese", "korean", "spanish",
                         "translate", "translation", "localized"),
                     zh=("語言", "语言", "中文", "英文", "日文", "韓文", "韩文", "繁體", "繁体", "簡體", "简体"),
                     ja=("日本語", "言語", "英語", "中国語", "韓国語"),
                     ko=("한국어", "언어", "영어", "한글"),
                     th=("ภาษา",), vi=("tiếng việt", "ngôn ngữ", "tiếng anh"))),
    ("howto", _kw(en=("how do", "how does", "how to", "how can", "can it", "does it", "is there", "can i",
                      "can you", "will it", "feature", "features", "ipad", "widget", "offline"),
                  zh=("怎麼", "怎么", "如何", "可以嗎", "可以吗", "能不能", "功能", "支援", "支持", "有沒有", "有没有"),
                  ja=("どうやって", "使い方", "できますか", "できる？", "機能", "対応"),
                  ko=("어떻게", "사용법", "기능", "되나요", "가능한가요", "지원"),
                  th=("ยังไง", "ใช้ยังไง", "ได้ไหม", "ได้มั้ย", "ฟีเจอร์", "รองรับ"),
                  vi=("làm sao", "làm thế nào", "cách dùng", "có thể", "tính năng", "hỗ trợ", "được không"))),
    ("praise", _kw(en=("love", "loving", "great", "awesome", "amazing", "nice", "cool", "thanks", "thank you",
                       "thx", "useful", "helpful", "perfect", "brilliant", "genius", "wow", "need this", "neat"),
                   zh=("好用", "讚", "赞", "謝謝", "谢谢", "感謝", "感谢", "太棒", "厲害", "厉害", "實用", "实用", "喜歡", "喜欢", "不錯", "不错"),
                   ja=("ありがとう", "最高", "便利", "すごい", "いいね", "好き", "素敵", "助かる"),
                   ko=("감사", "고마워", "좋아요", "좋네요", "최고", "대박", "유용", "짱"),
                   th=("ขอบคุณ", "ดีมาก", "เยี่ยม", "ชอบ", "สุดยอด", "ปัง"),
                   vi=("cảm ơn", "tuyệt", "hay quá", "thích", "xịn", "hữu ích"))),
]
PRAISE_EMOJI = re.compile(r"[❤♥😍🥰🔥👍👏🙌💯✨💕💖😊]")
# Praise words next to a negation ("not great", "沒用") are ambiguous.
NEGATION = re.compile(r"\b(not|never|no)\b|n't|沒|没|不好|不行|じゃない|ない|안 |않|ไม่|không|chẳng", re.I)
POSITIVE_WITH_NEGATION = re.compile(r"不錯|不错|不賴|不赖|没毛病")

# ------------------------------------------------------------------ templates
# {links} only appears in price / download / android templates; decide() appends the link lines to the
# other templates (praise, language, howto, android_none), so every reply carries them. A comment under a post
# that maps to no app gets no reply at all (there is no link to give).

T = {
    "en": {
        "praise": ["Thank you so much! Glad it's useful 🙌", "Really appreciate it, thanks for watching!",
                   "Thanks! Comments like this make our day 😊"],
        "price_free": ["It's free to download 🙌\n{links}", "Free to download, here you go:\n{links}",
                       "You can grab it for free:\n{links}"],
        "price": ["Pricing and details are on the store page:\n{links}", "All the details, including price, are here:\n{links}",
                  "Here's the store page with the price info:\n{links}"],
        "download": ["Here you go!\n{links}", "Here's the link 👇\n{links}", "You can find it here:\n{links}"],
        "android_live": ["Yes, it's on Android too!\n{links}", "It's on Google Play as well 🙌\n{links}",
                         "Android version is out:\n{links}"],
        "android_none": ["Not on Android yet, sorry! It's iPhone-only for now.",
                         "iPhone only at the moment, Android isn't out yet.",
                         "No Android version yet, thanks for asking though!"],
        "language": ["Supported languages are listed on the App Store page under \"Languages\".",
                     "Good question! The App Store page shows every language it supports.",
                     "You'll find the full language list on the App Store page."],
        "howto": ["Good question! The App Store screenshots walk through it step by step.",
                  "The App Store page shows how it works, and its support link reaches us directly.",
                  "Great question! The store page screenshots show exactly how it works."],
    },
    "zh-Hant": {
        "praise": ["謝謝你！很高興對你有幫助 🙌", "感謝支持，謝謝你看完！", "謝謝～看到這種留言超開心 😊"],
        "price_free": ["可以免費下載喔 🙌\n{links}", "免費下載，連結在這：\n{links}", "免費就能用，這裡下載：\n{links}"],
        "price": ["價格和詳細資訊都在商店頁：\n{links}", "詳細價格請看這裡：\n{links}", "商店頁有完整價格說明：\n{links}"],
        "download": ["連結在這裡！\n{links}", "這裡下載 👇\n{links}", "給你連結：\n{links}"],
        "android_live": ["有喔，Android 也有！\n{links}", "Google Play 也上架了 🙌\n{links}", "Android 版在這：\n{links}"],
        "android_none": ["目前還沒有 Android 版，抱歉！暫時只有 iPhone。", "現在只有 iPhone 版，Android 還沒推出。",
                         "還沒有 Android 版喔，謝謝你問！"],
        "language": ["支援的語言都列在 App Store 頁面的「語言」欄。", "好問題！App Store 頁面有列出所有支援的語言。",
                     "完整的語言清單在 App Store 頁面上可以看到。"],
        "howto": ["好問題！App Store 的截圖有一步步的說明。", "App Store 頁面有使用方式，頁面上的支援連結也能直接找到我們。",
                  "問得好！商店頁的截圖就是實際操作畫面。"],
    },
    "ja": {
        "praise": ["ありがとうございます！お役に立てて嬉しいです 🙌", "見てくれてありがとうございます！",
                   "ありがとうございます、励みになります 😊"],
        "price_free": ["無料でダウンロードできます 🙌\n{links}", "無料です、こちらからどうぞ：\n{links}",
                       "無料で使えます：\n{links}"],
        "price": ["価格と詳細はストアページにあります：\n{links}", "料金の詳細はこちら：\n{links}",
                  "ストアページで価格を確認できます：\n{links}"],
        "download": ["こちらからどうぞ！\n{links}", "リンクはこちら 👇\n{links}", "ここから入手できます：\n{links}"],
        "android_live": ["はい、Androidもあります！\n{links}", "Google Playにもあります 🙌\n{links}",
                         "Android版はこちら：\n{links}"],
        "android_none": ["ごめんなさい、Android版はまだありません。今はiPhoneのみです。",
                         "現在はiPhone版のみで、Android版はまだです。", "Android版はまだないんです、質問ありがとうございます！"],
        "language": ["対応言語はApp Storeページの「言語」欄に載っています。", "いい質問です！App Storeページに対応言語がすべて載っています。",
                     "対応言語の一覧はApp Storeページで確認できます。"],
        "howto": ["いい質問です！App Storeのスクリーンショットで手順を紹介しています。",
                  "使い方はApp Storeページにあり、サポートリンクから直接連絡もできます。",
                  "ストアページのスクリーンショットが実際の画面です。"],
    },
    "ko": {
        "praise": ["감사합니다! 도움이 됐다니 기뻐요 🙌", "봐주셔서 정말 감사해요!", "감사합니다, 큰 힘이 돼요 😊"],
        "price_free": ["무료로 다운로드할 수 있어요 🙌\n{links}", "무료예요, 여기서 받으세요:\n{links}",
                       "무료로 쓸 수 있어요:\n{links}"],
        "price": ["가격과 자세한 내용은 스토어 페이지에 있어요:\n{links}", "가격 정보는 여기서 확인하세요:\n{links}",
                  "스토어 페이지에 가격이 나와 있어요:\n{links}"],
        "download": ["여기 있어요!\n{links}", "링크는 여기 👇\n{links}", "여기서 받을 수 있어요:\n{links}"],
        "android_live": ["네, 안드로이드도 있어요!\n{links}", "Google Play에도 있어요 🙌\n{links}",
                         "안드로이드 버전은 여기:\n{links}"],
        "android_none": ["죄송해요, 아직 안드로이드 버전은 없어요. 지금은 iPhone 전용이에요.",
                         "현재는 iPhone만 지원하고 안드로이드는 아직이에요.", "아직 안드로이드 버전은 없어요, 물어봐 주셔서 감사해요!"],
        "language": ["지원 언어는 App Store 페이지의 '언어' 항목에 나와 있어요.", "좋은 질문이에요! App Store 페이지에 지원 언어가 모두 나와 있어요.",
                     "전체 언어 목록은 App Store 페이지에서 볼 수 있어요."],
        "howto": ["좋은 질문이에요! App Store 스크린샷에 단계별로 나와 있어요.",
                  "사용법은 App Store 페이지에 있고, 지원 링크로 저희에게 바로 연락할 수 있어요.",
                  "스토어 페이지 스크린샷이 실제 화면이에요."],
    },
    "th": {
        "praise": ["ขอบคุณมากครับ! ดีใจที่มีประโยชน์ 🙌", "ขอบคุณที่ดูนะครับ!", "ขอบคุณครับ เป็นกำลังใจมาก 😊"],
        "price_free": ["ดาวน์โหลดฟรีครับ 🙌\n{links}", "ฟรีครับ โหลดได้ที่นี่:\n{links}", "ใช้ได้ฟรีครับ:\n{links}"],
        "price": ["ราคาและรายละเอียดอยู่ในหน้าสโตร์ครับ:\n{links}", "ดูราคาได้ที่นี่ครับ:\n{links}",
                  "หน้าสโตร์มีข้อมูลราคาครับ:\n{links}"],
        "download": ["นี่เลยครับ!\n{links}", "ลิงก์อยู่นี่ครับ 👇\n{links}", "โหลดได้ที่นี่ครับ:\n{links}"],
        "android_live": ["มีบน Android ด้วยครับ!\n{links}", "มีใน Google Play แล้วครับ 🙌\n{links}",
                         "เวอร์ชัน Android อยู่นี่ครับ:\n{links}"],
        "android_none": ["ขอโทษครับ ยังไม่มีเวอร์ชัน Android ตอนนี้มีแค่ iPhone", "ตอนนี้มีแค่ iPhone ครับ Android ยังไม่ออก",
                         "ยังไม่มี Android ครับ ขอบคุณที่ถามนะครับ!"],
        "language": ["ภาษาที่รองรับอยู่ในหัวข้อ \"ภาษา\" ในหน้า App Store ครับ", "คำถามดีครับ! หน้า App Store มีรายชื่อภาษาที่รองรับทั้งหมด",
                     "ดูรายการภาษาทั้งหมดได้ในหน้า App Store ครับ"],
        "howto": ["คำถามดีครับ! ภาพหน้าจอใน App Store อธิบายทีละขั้นตอน",
                  "วิธีใช้อยู่ในหน้า App Store และติดต่อเราได้ทางลิงก์ซัพพอร์ตในหน้านั้นครับ",
                  "ภาพหน้าจอในหน้าสโตร์คือหน้าจอจริงเลยครับ"],
    },
    "vi": {
        "praise": ["Cảm ơn bạn nhiều! Rất vui vì app hữu ích 🙌", "Cảm ơn bạn đã xem nha!", "Cảm ơn bạn, đọc mà vui ghê 😊"],
        "price_free": ["Tải miễn phí nha 🙌\n{links}", "Miễn phí đó, tải ở đây:\n{links}", "Dùng miễn phí nha:\n{links}"],
        "price": ["Giá và chi tiết có trên trang store:\n{links}", "Xem giá ở đây nha:\n{links}",
                  "Trang store có đủ thông tin giá:\n{links}"],
        "download": ["Đây nha!\n{links}", "Link ở đây 👇\n{links}", "Tải ở đây nha:\n{links}"],
        "android_live": ["Có cả Android nha!\n{links}", "Có trên Google Play rồi 🙌\n{links}", "Bản Android ở đây:\n{links}"],
        "android_none": ["Xin lỗi, chưa có bản Android, hiện chỉ có iPhone thôi.", "Hiện chỉ có bản iPhone, Android chưa ra.",
                         "Chưa có bản Android nha, cảm ơn bạn đã hỏi!"],
        "language": ["Các ngôn ngữ hỗ trợ có ở mục \"Ngôn ngữ\" trên trang App Store.",
                     "Câu hỏi hay! Trang App Store liệt kê đủ các ngôn ngữ hỗ trợ.",
                     "Bạn xem danh sách ngôn ngữ đầy đủ trên trang App Store nha."],
        "howto": ["Câu hỏi hay! Ảnh chụp trên App Store hướng dẫn từng bước.",
                  "Cách dùng có trên trang App Store, link hỗ trợ ở đó liên hệ thẳng với tụi mình.",
                  "Ảnh trên trang store chính là màn hình thật nha."],
    },
}

# ------------------------------------------------------------------ decisions

_FREE = None


def is_free(ios_id):
    """True when the app's listing says it's free to download / start."""
    global _FREE
    if _FREE is None:
        _FREE = set()
        apps = load_json(APPS, [])
        for a in apps if isinstance(apps, list) else []:
            m = re.search(r"/id(\d+)", a.get("appStoreUrl", ""))
            if m and any("free" in str(x).lower() for x in a.get("attributes", [])):
                _FREE.add(m.group(1))
    return str(ios_id) in _FREE


def classify(text):
    """("skip", reason) or (intent, None)."""
    if SPAM.search(text):
        return "skip", "spam"
    if COMPLAINT.search(text):
        return "skip", "complaint"
    for intent, pattern in INTENTS:
        if pattern.search(text):
            if intent == "praise" and NEGATION.search(POSITIVE_WITH_NEGATION.sub("", text)):
                return "skip", "ambiguous"
            return intent, None
    if PRAISE_EMOJI.search(text) and not re.search(r"\w", re.sub(r"[_\d]", "", text)):
        return "praise", None
    return "skip", "ambiguous"


def store_links(post, channel):
    ios = (post or {}).get("ios_id")
    if not ios:
        return None, None
    ct = "rp_ig" if channel == "instagram" else "rp_th"
    return (campaign_app_store_url(f"https://apps.apple.com/app/id{ios}", ct), play_store_url(ios, ct))


def decide(comment, post, channel, own_username, state, media_id, now):
    """{"skip": reason} or {"text", "intent", "lang", "variant"} (state is not changed)."""
    text = (comment.get("text") or "").strip()
    user = comment.get("user") or ""
    replied = state.setdefault("replied", {}).setdefault(channel, {})
    if comment.get("own") or (own_username and user.lower() == own_username.lower()):
        return {"skip": "own"}
    if comment["id"] in replied or comment.get("we_replied"):
        return {"skip": "replied"}
    if any(r.get("media") == media_id and r.get("user") == user for r in replied.values()):
        return {"skip": "commenter-once"}
    ts = parse_time(comment.get("timestamp"))
    if ts and now - ts > MAX_COMMENT_AGE:
        return {"skip": "old"}
    if not text:
        return {"skip": "ambiguous"}
    intent, reason = classify(text)
    if intent == "skip":
        return {"skip": reason}
    lang = detect_language(text)
    if lang is None and intent == "praise":  # emoji-only: answer in the post's language
        lang = (post or {}).get("locale")
    if lang not in T:
        return {"skip": "language"}
    app, play = store_links(post, channel)
    if not app:   # no app, no download link to give: a reply without it is not sent, whatever the intent
        return {"skip": "no-app"}
    key = intent
    links = f"App Store: {app}" + (f"\nGoogle Play: {play}" if play else "")
    if intent == "android":
        key = "android_live" if play else "android_none"
        links = f"Google Play: {play}\nApp Store: {app}" if play else links
    elif intent in LINK_INTENTS:
        key = "price_free" if intent == "price" and is_free(post["ios_id"]) else intent
    variants = T[lang][key]
    # Rotate per language+intent so two replies in a row never read the same.
    variant = state.setdefault("rotation", {}).get(f"{lang}/{key}", 0) % len(variants)
    template = variants[variant]
    reply = template.format(links=links).strip()
    if "{links}" not in template:  # praise / language / howto / android_none: link lines at the end
        reply = f"{reply}\n{links}"
    if channel == "instagram":   # an Instagram reply URL cannot be tapped: say where to tap (ig_bio.py)
        name = HUB.display_name(post["ios_id"], lang) or post.get("name") or ""
        if name:
            reply = f"{reply}\n{IGB.bio_line(lang, name)}"
    problems = DL.link_problems(reply, app, play, label=f"{channel} reply to comment {comment['id']}")
    limit = MAX_REPLY_CHARS.get(channel, 500)
    if len(reply) > limit:
        problems.append(f"{channel} reply to comment {comment['id']}: {len(reply)} chars is over the {limit} limit")
    if problems:  # never send a reply without the link: report it, do not stay silent
        DL.refuse(f"{channel} comment reply", problems)
        return {"skip": "link-guard"}
    return {"text": reply, "intent": intent, "lang": lang, "key": key, "variant": variant}


def parse_time(value):
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00").replace("+0000", "+00:00"))
    except ValueError:
        return None


def replies_today(state, channel, now):
    day = now.date().isoformat()
    return sum(1 for r in state.get("replied", {}).get(channel, {}).values() if r.get("at", "")[:10] == day and r.get("intent") != "manual")


# ------------------------------------------------------------------ run

def run_platform(client, catalog, state, now, dry_run=False, sleeper=time.sleep, gap=20,
                 save=lambda: None, log=print):
    channel = client.channel
    finder = catalog if isinstance(catalog, AppFinder) else AppFinder(catalog)
    try:
        client.me()
    except ApiError as exc:
        log(f"{channel}: account lookup failed, skipped ({exc})")
        return []
    budget = min(RUN_CAP, DAILY_CAP - replies_today(state, channel, now))
    if budget <= 0:
        log(f"{channel}: daily cap of {DAILY_CAP} reached")
        return []
    sent, no_app = [], set()
    noted = state.setdefault("no_app", {}).setdefault(channel, {})
    try:
        media = client.media()
    except ApiError as exc:
        log(f"{channel}: cannot list our posts, skipped ({exc})")
        return []
    for m in media:
        ts = parse_time(m.get("timestamp"))
        if ts and now - ts > MAX_POST_AGE:
            continue
        if finder.catalog.taken_down(channel, m, LEDGER_CHANNELS.get(channel, (channel,))):
            continue   # a taken-down (non-compliant) clip post, or one waiting to be archived: no replies under it
        try:
            comments = client.comments(m["id"])
        except ApiError as exc:
            if exc.permission:
                log(f"{channel}: no permission to read comments, skipped ({exc})")
                return sent
            log(f"{channel}: comments of {m['id']} skipped ({exc})")
            continue
        post = finder.resolve(channel, m)   # several proofs must agree on the app (link_backfill.AppFinder), else no link
        if post and not post.get("ios_id"):  # a ledger post knows the app, not always its store id
            post = dict(post, ios_id=ios_id_for(finder.catalog, post))
        for c in sorted(comments, key=lambda c: c.get("timestamp", "")):
            d = decide(c, post, channel, client.username, state, m["id"], now)
            if "skip" in d:
                if d["skip"] == "no-app" and m["id"] not in no_app:   # once per post (not per run): ::error:: + guard log
                    no_app.add(m["id"])
                    if m["id"] not in noted:
                        noted[m["id"]] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
                        DL.refuse(f"{channel} comment replies", [
                            f"post {m['id']} maps to no app of ours, so no reply with a download link can be written; "
                            "its comments get no reply (reported once; link_backfill.py keeps listing the post)"])
                        save()
                if d["skip"] not in ("own", "replied", "old"):
                    log(f"{channel}: skip {c['id']} ({d['skip']})")
                continue
            log(f"{channel}: {'[dry-run] ' if dry_run else ''}reply {c['id']} {d['lang']}/{d['intent']}: "
                f"{d['text'].splitlines()[0]}")
            if not dry_run:
                if hasattr(client, "answered") and client.answered(c["id"]):
                    state["replied"][channel][c["id"]] = {"media": m["id"], "user": c.get("user"), "intent": "manual",
                                                          "lang": d["lang"], "at": now.strftime("%Y-%m-%dT%H:%M:%SZ")}
                    continue
                if sent:
                    sleeper(gap)
                try:
                    client.reply(c["id"], d["text"])
                except ApiError as exc:
                    log(f"{channel}: reply failed ({exc})")
                    if exc.permission:
                        return sent
                    continue
                state["replied"][channel][c["id"]] = {
                    "media": m["id"], "user": c.get("user"), "intent": d["intent"], "lang": d["lang"],
                    "at": now.strftime("%Y-%m-%dT%H:%M:%SZ")}
                rot = state.setdefault("rotation", {})
                rot[f"{d['lang']}/{d['key']}"] = rot.get(f"{d['lang']}/{d['key']}", 0) + 1
                save()
            sent.append(d)
            if len(sent) >= budget:
                log(f"{channel}: cap reached for this run")
                return sent
    return sent


def _threads_answered(self, comment_id):
    """Live guard against double replies on Threads (the state file can lag)."""
    try:
        rows = self._get(f"{comment_id}/replies", fields="username").get("data", [])
    except ApiError:
        return False
    return any(r.get("username") == self.username for r in rows)


ThreadsClient.answered = _threads_answered


def load_state(path=STATE):
    state = load_json(path, {})
    state.setdefault("note", "Comments answered by .github/scripts/comment_replies.py (own posts only).")
    state.setdefault("replied", {}).setdefault("instagram", {})
    state["replied"].setdefault("threads", {})
    state.setdefault("rotation", {})
    state.setdefault("no_app", {})   # posts already reported as "maps to no app": one ::error:: per post, not one per run
    return state


def prune(state, now):
    cutoff = (now - KEEP_STATE).strftime("%Y-%m-%dT%H:%M:%SZ")
    for channel, rows in state["replied"].items():
        state["replied"][channel] = {k: v for k, v in rows.items() if not v.get("at") or v["at"] >= cutoff}
    for channel, rows in state.get("no_app", {}).items():
        state["no_app"][channel] = {k: v for k, v in rows.items() if not v or v >= cutoff}


def save_state(state, path=STATE):
    Path(path).write_text(json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def merge_state(saved_path, path=STATE):
    """Fold a state file saved before `git reset` into the current one."""
    mine, cur = load_state(saved_path), load_state(path)
    for channel, rows in mine["replied"].items():
        cur["replied"].setdefault(channel, {}).update(rows)
    for channel, rows in mine.get("no_app", {}).items():
        cur.setdefault("no_app", {}).setdefault(channel, {}).update(rows)
    for k, v in mine["rotation"].items():
        cur["rotation"][k] = max(v, cur["rotation"].get(k, 0))
    save_state(cur, path)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print replies, send nothing, keep the state file")
    ap.add_argument("--merge-state", help="replied-comments.json saved before resetting to origin/main")
    ap.add_argument("--platform", choices=["instagram", "threads", "all"], default="all")
    args = ap.parse_args(argv)
    if args.merge_state:
        merge_state(args.merge_state)
        return 0
    dry = args.dry_run or os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")
    now = dt.datetime.now(dt.timezone.utc)
    state = load_state()
    prune(state, now)
    catalog = Catalog()
    clients = []
    ig, th = os.environ.get("IG_ACCESS_TOKEN", "").strip(), os.environ.get("THREADS_TOKEN", "").strip()
    if args.platform in ("instagram", "all"):
        if ig:
            clients.append(InstagramClient(ig))
        else:
            print("instagram: no token, skipped")
    if args.platform in ("threads", "all"):
        if th:
            clients.append(ThreadsClient(th))
        else:
            print("threads: no token, skipped")
    total = 0
    for client in clients:
        try:
            total += len(run_platform(client, catalog, state, now, dry_run=dry,
                                      save=(lambda: None) if dry else (lambda: save_state(state))))
        except SnapshotMissing as exc:   # the Google Play link cannot be decided: no reply is written, and it is loud
            DL.refuse(f"{client.channel} comment replies", [f"stopped, no reply was written: {exc}"])
        except (ApiError, OSError, ValueError, KeyError) as exc:  # never fail the workflow
            print(f"{client.channel}: stopped ({exc.__class__.__name__}: {exc})")
    if not dry:
        save_state(state)
    print(f"replies {'planned' if dry else 'sent'}: {total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
