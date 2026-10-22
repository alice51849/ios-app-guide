#!/usr/bin/env python3
"""Generate a bilingual, local-only vocabulary habit planner."""

from __future__ import annotations

import html
import json
import os
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))

from appstore_live import live_app_keys  # noqa: E402
from bopomofo_flashcards import ALT_LOCALES  # noqa: E402
from gen_calculator import write_tools_sitemap  # noqa: E402
from gen_feed import feed_discovery_links  # noqa: E402
from videogen.registry import APPSTORE, appstore_url  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402

PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", PUBLIC_SITE
).rstrip("/")
SLUG = "private-vocabulary-habit-planner"
APP_KEY = "wordmate"
APP_ID = "6789917808"
CONTENT_DATE = "2026-07-14"
TOOL_DATE = "2026-07-15"
SPACING_SOURCE = "https://pubmed.ncbi.nlm.nih.gov/16719566/"
RETRIEVAL_SOURCE = "https://pubmed.ncbi.nlm.nih.gov/16507066/"
WEBMCP_SOURCE = "https://developer.chrome.com/docs/ai/webmcp/imperative-api"

TARGET_ANSWER_SLUGS = (
    "how-can-i-build-a-vocabulary-study-habit-without-uploading-my-learning-"
    "data.html",
)
INBOUND_LINK_CLASS = "vocabulary-habit-planner-inline-link"
_APP_STORE_ANCHOR = re.compile(
    r'<a\b(?=[^>]*\bhref\s*=\s*(?P<q>["\'])https://apps\.apple\.com/'
    r'(?:[^"\'?#]*/)*id'
    + APP_ID
    + r'(?:[?#][^"\']*)?(?P=q))[^>]*>',
    re.IGNORECASE,
)

LANGUAGES = [
    ("en", "English", "英文"),
    ("zh-Hant", "Traditional Chinese", "繁體中文"),
    ("zh-Hans", "Simplified Chinese", "簡體中文"),
    ("ja", "Japanese", "日文"),
    ("ko", "Korean", "韓文"),
    ("de", "German", "德文"),
    ("fr", "French", "法文"),
    ("es", "Spanish", "西班牙文"),
    ("it", "Italian", "義大利文"),
    ("pt", "Portuguese", "葡萄牙文"),
    ("nl", "Dutch", "荷蘭文"),
    ("ru", "Russian", "俄文"),
    ("pl", "Polish", "波蘭文"),
    ("tr", "Turkish", "土耳其文"),
    ("sv", "Swedish", "瑞典文"),
    ("da", "Danish", "丹麥文"),
    ("no", "Norwegian", "挪威文"),
    ("fi", "Finnish", "芬蘭文"),
    ("id", "Indonesian", "印尼文"),
    ("ms", "Malay", "馬來文"),
    ("vi", "Vietnamese", "越南文"),
    ("th", "Thai", "泰文"),
    ("hi", "Hindi", "印地文"),
    ("ar", "Arabic", "阿拉伯文"),
    ("he", "Hebrew", "希伯來文"),
    ("el", "Greek", "希臘文"),
    ("cs", "Czech", "捷克文"),
    ("sk", "Slovak", "斯洛伐克文"),
    ("hr", "Croatian", "克羅埃西亞文"),
    ("hu", "Hungarian", "匈牙利文"),
    ("ro", "Romanian", "羅馬尼亞文"),
    ("uk", "Ukrainian", "烏克蘭文"),
    ("ca", "Catalan", "加泰隆尼亞文"),
    ("bn", "Bengali", "孟加拉文"),
    ("gu", "Gujarati", "古吉拉特文"),
    ("kn", "Kannada", "康納達文"),
    ("ml", "Malayalam", "馬拉雅拉姆文"),
    ("mr", "Marathi", "馬拉地文"),
    ("or", "Odia", "歐利亞文"),
    ("pa", "Punjabi", "旁遮普文"),
    ("sl", "Slovenian", "斯洛維尼亞文"),
    ("ta", "Tamil", "坦米爾文"),
    ("te", "Telugu", "泰盧固文"),
    ("ur", "Urdu", "烏爾都文"),
]

_LANGUAGE_LOCALE_NAMES = {
    "zh-Hans": {
        "en": "英语",
        "zh-Hant": "繁体中文",
        "zh-Hans": "简体中文",
        "ja": "日语",
        "ko": "韩语",
        "de": "德语",
        "fr": "法语",
        "es": "西班牙语",
        "it": "意大利语",
        "pt": "葡萄牙语",
        "nl": "荷兰语",
        "ru": "俄语",
        "pl": "波兰语",
        "tr": "土耳其语",
        "sv": "瑞典语",
        "da": "丹麦语",
        "no": "挪威语",
        "fi": "芬兰语",
        "id": "印度尼西亚语",
        "ms": "马来语",
        "vi": "越南语",
        "th": "泰语",
        "hi": "印地语",
        "ar": "阿拉伯语",
        "he": "希伯来语",
        "el": "希腊语",
        "cs": "捷克语",
        "sk": "斯洛伐克语",
        "hr": "克罗地亚语",
        "hu": "匈牙利语",
        "ro": "罗马尼亚语",
        "uk": "乌克兰语",
        "ca": "加泰罗尼亚语",
        "bn": "孟加拉语",
        "gu": "古吉拉特语",
        "kn": "卡纳达语",
        "ml": "马拉雅拉姆语",
        "mr": "马拉地语",
        "or": "奥里亚语",
        "pa": "旁遮普语",
        "sl": "斯洛文尼亚语",
        "ta": "泰米尔语",
        "te": "泰卢固语",
        "ur": "乌尔都语",
    },
    "ja": {
        "en": "英語",
        "zh-Hant": "繁体字中国語",
        "zh-Hans": "簡体字中国語",
        "ja": "日本語",
        "ko": "韓国語",
        "de": "ドイツ語",
        "fr": "フランス語",
        "es": "スペイン語",
        "it": "イタリア語",
        "pt": "ポルトガル語",
        "nl": "オランダ語",
        "ru": "ロシア語",
        "pl": "ポーランド語",
        "tr": "トルコ語",
        "sv": "スウェーデン語",
        "da": "デンマーク語",
        "no": "ノルウェー語",
        "fi": "フィンランド語",
        "id": "インドネシア語",
        "ms": "マレー語",
        "vi": "ベトナム語",
        "th": "タイ語",
        "hi": "ヒンディー語",
        "ar": "アラビア語",
        "he": "ヘブライ語",
        "el": "ギリシャ語",
        "cs": "チェコ語",
        "sk": "スロバキア語",
        "hr": "クロアチア語",
        "hu": "ハンガリー語",
        "ro": "ルーマニア語",
        "uk": "ウクライナ語",
        "ca": "カタルーニャ語",
        "bn": "ベンガル語",
        "gu": "グジャラート語",
        "kn": "カンナダ語",
        "ml": "マラヤーラム語",
        "mr": "マラーティー語",
        "or": "オリヤー語",
        "pa": "パンジャブ語",
        "sl": "スロベニア語",
        "ta": "タミル語",
        "te": "テルグ語",
        "ur": "ウルドゥー語",
    },
    "ko": {
        "en": "영어",
        "zh-Hant": "번체 중국어",
        "zh-Hans": "간체 중국어",
        "ja": "일본어",
        "ko": "한국어",
        "de": "독일어",
        "fr": "프랑스어",
        "es": "스페인어",
        "it": "이탈리아어",
        "pt": "포르투갈어",
        "nl": "네덜란드어",
        "ru": "러시아어",
        "pl": "폴란드어",
        "tr": "터키어",
        "sv": "스웨덴어",
        "da": "덴마크어",
        "no": "노르웨이어",
        "fi": "핀란드어",
        "id": "인도네시아어",
        "ms": "말레이어",
        "vi": "베트남어",
        "th": "태국어",
        "hi": "힌디어",
        "ar": "아랍어",
        "he": "히브리어",
        "el": "그리스어",
        "cs": "체코어",
        "sk": "슬로바키아어",
        "hr": "크로아티아어",
        "hu": "헝가리어",
        "ro": "루마니아어",
        "uk": "우크라이나어",
        "ca": "카탈루냐어",
        "bn": "벵골어",
        "gu": "구자라트어",
        "kn": "칸나다어",
        "ml": "말라얄람어",
        "mr": "마라티어",
        "or": "오리야어",
        "pa": "펀자브어",
        "sl": "슬로베니아어",
        "ta": "타밀어",
        "te": "텔루구어",
        "ur": "우르두어",
    },
    "es-ES": {
        "en": "Inglés",
        "zh-Hant": "Chino tradicional",
        "zh-Hans": "Chino simplificado",
        "ja": "Japonés",
        "ko": "Coreano",
        "de": "Alemán",
        "fr": "Francés",
        "es": "Español",
        "it": "Italiano",
        "pt": "Portugués",
        "nl": "Neerlandés",
        "ru": "Ruso",
        "pl": "Polaco",
        "tr": "Turco",
        "sv": "Sueco",
        "da": "Danés",
        "no": "Noruego",
        "fi": "Finlandés",
        "id": "Indonesio",
        "ms": "Malayo",
        "vi": "Vietnamita",
        "th": "Tailandés",
        "hi": "Hindi",
        "ar": "Árabe",
        "he": "Hebreo",
        "el": "Griego",
        "cs": "Checo",
        "sk": "Eslovaco",
        "hr": "Croata",
        "hu": "Húngaro",
        "ro": "Rumano",
        "uk": "Ucraniano",
        "ca": "Catalán",
        "bn": "Bengalí",
        "gu": "Guyaratí",
        "kn": "Canarés",
        "ml": "Malabar",
        "mr": "Maratí",
        "or": "Oriya",
        "pa": "Punyabí",
        "sl": "Esloveno",
        "ta": "Tamil",
        "te": "Telugu",
        "ur": "Urdu",
    },
    "pt-BR": {
        "en": "Inglês",
        "zh-Hant": "Chinês tradicional",
        "zh-Hans": "Chinês simplificado",
        "ja": "Japonês",
        "ko": "Coreano",
        "de": "Alemão",
        "fr": "Francês",
        "es": "Espanhol",
        "it": "Italiano",
        "pt": "Português",
        "nl": "Holandês",
        "ru": "Russo",
        "pl": "Polonês",
        "tr": "Turco",
        "sv": "Sueco",
        "da": "Dinamarquês",
        "no": "Norueguês",
        "fi": "Finlandês",
        "id": "Indonésio",
        "ms": "Malaio",
        "vi": "Vietnamita",
        "th": "Tailandês",
        "hi": "Hindi",
        "ar": "Árabe",
        "he": "Hebraico",
        "el": "Grego",
        "cs": "Tcheco",
        "sk": "Eslovaco",
        "hr": "Croata",
        "hu": "Húngaro",
        "ro": "Romeno",
        "uk": "Ucraniano",
        "ca": "Catalão",
        "bn": "Bengali",
        "gu": "Guzerate",
        "kn": "Canarês",
        "ml": "Malaiala",
        "mr": "Marata",
        "or": "Oriá",
        "pa": "Panjabi",
        "sl": "Esloveno",
        "ta": "Tâmil",
        "te": "Telugo",
        "ur": "Urdu",
    },
    "de-DE": {
        "en": "Englisch",
        "zh-Hant": "Traditionelles Chinesisch",
        "zh-Hans": "Vereinfachtes Chinesisch",
        "ja": "Japanisch",
        "ko": "Koreanisch",
        "de": "Deutsch",
        "fr": "Französisch",
        "es": "Spanisch",
        "it": "Italienisch",
        "pt": "Portugiesisch",
        "nl": "Niederländisch",
        "ru": "Russisch",
        "pl": "Polnisch",
        "tr": "Türkisch",
        "sv": "Schwedisch",
        "da": "Dänisch",
        "no": "Norwegisch",
        "fi": "Finnisch",
        "id": "Indonesisch",
        "ms": "Malaiisch",
        "vi": "Vietnamesisch",
        "th": "Thailändisch",
        "hi": "Hindi",
        "ar": "Arabisch",
        "he": "Hebräisch",
        "el": "Griechisch",
        "cs": "Tschechisch",
        "sk": "Slowakisch",
        "hr": "Kroatisch",
        "hu": "Ungarisch",
        "ro": "Rumänisch",
        "uk": "Ukrainisch",
        "ca": "Katalanisch",
        "bn": "Bengalisch",
        "gu": "Gujarati",
        "kn": "Kannada",
        "ml": "Malayalam",
        "mr": "Marathi",
        "or": "Odia",
        "pa": "Punjabi",
        "sl": "Slowenisch",
        "ta": "Tamil",
        "te": "Telugu",
        "ur": "Urdu",
    },
    "fr-FR": {
        "en": "Anglais",
        "zh-Hant": "Chinois traditionnel",
        "zh-Hans": "Chinois simplifié",
        "ja": "Japonais",
        "ko": "Coréen",
        "de": "Allemand",
        "fr": "Français",
        "es": "Espagnol",
        "it": "Italien",
        "pt": "Portugais",
        "nl": "Néerlandais",
        "ru": "Russe",
        "pl": "Polonais",
        "tr": "Turc",
        "sv": "Suédois",
        "da": "Danois",
        "no": "Norvégien",
        "fi": "Finnois",
        "id": "Indonésien",
        "ms": "Malais",
        "vi": "Vietnamien",
        "th": "Thaï",
        "hi": "Hindi",
        "ar": "Arabe",
        "he": "Hébreu",
        "el": "Grec",
        "cs": "Tchèque",
        "sk": "Slovaque",
        "hr": "Croate",
        "hu": "Hongrois",
        "ro": "Roumain",
        "uk": "Ukrainien",
        "ca": "Catalan",
        "bn": "Bengali",
        "gu": "Gujarati",
        "kn": "Kannada",
        "ml": "Malayalam",
        "mr": "Marathi",
        "or": "Odia",
        "pa": "Pendjabi",
        "sl": "Slovène",
        "ta": "Tamoul",
        "te": "Télougou",
        "ur": "Ourdou",
    },
}


COPY = {
    "en": {
        "html_lang": "en",
        "title": "Private Vocabulary Habit Planner | Free & Local",
        "description": (
            "Build a realistic vocabulary routine from your available time. "
            "The complete plan runs locally with no account, upload, storage or analytics."
        ),
        "switch": "繁體中文",
        "switch_href": f"{SITE}/zh-Hant/tools/{SLUG}.html",
        "home": f"{SITE}/index.html",
        "tools": f"{SITE}/tools/",
        "tools_label": "Free tools",
        "inline_link": "Build a private vocabulary habit plan",
        "eyebrow": "Free · private · evidence-informed",
        "heading": "Private vocabulary habit planner",
        "lead": (
            "Turn the time you actually have into a repeatable plan for retrieval, "
            "words in context and correction. Nothing is uploaded or saved."
        ),
        "privacy": "Runs in this tab · no account · no storage · no analytics",
        "scope": "Planning aid, not a promise of words learned",
        "builder": "Build your routine",
        "language": "Learning language",
        "minutes": "Minutes per session",
        "sessions": "Sessions per week",
        "horizon": "Planning horizon",
        "mode": "Current study mode",
        "goal": "Primary use",
        "make": "Create my private plan",
        "minutes_unit": "minutes",
        "sessions_unit": "sessions",
        "weeks_unit": "weeks",
        "mode_options": {
            "starter": "Starting a language",
            "mixed": "Learning and reviewing",
            "review": "Rebuilding forgotten vocabulary",
        },
        "goal_options": {
            "daily": "Everyday understanding",
            "travel": "Travel",
            "work": "Work or study",
            "conversation": "Conversation",
        },
        "result_title": "Your repeatable plan",
        "result_intro": "This is a starting load. Adjust it using delayed recall.",
        "weekly_time": "Weekly practice time",
        "new_ceiling": "Starting new-card ceiling",
        "per_session": "per session",
        "not_target": "A ceiling, not a learning promise",
        "session_mix": "Session mix",
        "retrieve": "Closed-book retrieval",
        "context": "New words in context",
        "correct": "Correction and spoken replay",
        "sequence": "Weekly sequence",
        "session": "Session",
        "focus": "Focus",
        "steps": [
            "Recall older words before revealing answers.",
            "Study the small new set inside useful sentences.",
            "Correct every miss, then say or type the answer once.",
            "Check the material again next session and about one week later.",
            "If delayed recall is below 80%, reduce new cards by roughly one quarter.",
        ],
        "roles": [
            "Baseline retrieval + small context set",
            "Retrieve misses + add context",
            "Mixed recall + pronunciation",
            "Cumulative check without hints",
            "Useful phrases for the selected goal",
            "Flexible catch-up; add nothing if reviews are heavy",
            "Weekly delayed check + next-week adjustment",
        ],
        "repeat_note": (
            "Repeat this sequence for the selected horizon. Longer gaps may need "
            "longer review intervals; there is no universal perfect schedule."
        ),
        "copy": "Copy plan",
        "share": "Share plan",
        "print": "Print plan",
        "copied": "Plan copied.",
        "share_cancelled": "Sharing was cancelled.",
        "copy_failed": "Copy was unavailable. Select and copy the plan below.",
        "evidence_title": "Why the plan uses retrieval and spacing",
        "evidence": (
            "Retrieval practice can improve later retention, and distributed practice "
            "generally outperforms massed repetition. The useful spacing interval changes "
            "with the desired retention period, so this planner uses repeated checks and "
            "adjustment instead of claiming one magic interval."
        ),
        "source_one": "Cepeda et al. — distributed practice meta-analysis",
        "source_two": "Roediger & Karpicke — test-enhanced learning",
        "webmcp_source": "Chrome WebMCP imperative API",
        "webmcp_description": (
            "Build a private vocabulary routine from a supported language, available "
            "time, weekly frequency, horizon, study mode and goal. Return the same "
            "evidence-informed starting ceiling and sequence as the visible planner, "
            "without promising learning outcomes."
        ),
        "privacy_title": "Privacy by construction",
        "privacy_text": (
            "Selections and results stay in this browser tab. The page has no account, "
            "upload, cookies, local storage, analytics, advertising code or network request. "
            "Reloading or closing the page clears the plan."
        ),
        "app_title": "Want the routine on iPhone, Home Screen and Apple Watch?",
        "app_text": (
            "Wordmate is optional. Its paid download includes structured vocabulary in "
            "44 languages, natural examples, pronunciation on iPhone and iPad, an interactive "
            "Home Screen widget, Apple Watch and separate progress for every learning language. "
            "No subscription, in-app purchase, account, third-party ads or analytics."
        ),
        "app_cta": "View Wordmate on the App Store",
        "faq_title": "Questions",
        "faqs": [
            (
                "How many new words should I learn each day?",
                "There is no universal number. Start below the planner's ceiling, then lower or raise it according to delayed recall and available review time.",
            ),
            (
                "Does the planner save my choices?",
                "No. It does not use local storage, cookies, an account or an upload. Closing or reloading the page clears the choices.",
            ),
            (
                "Is an 80% recall check a scientific guarantee?",
                "No. It is a practical adjustment trigger, not a universal target or outcome guarantee. Lower the load whenever reviews feel unstable or too heavy.",
            ),
        ],
        "footer": (
            "Free client-side planning tool. No tracking, account or server upload. "
            "Learning outcomes vary; adjust the plan to your own delayed recall."
        ),
        "index_title": "Private Vocabulary Habit Planner",
        "index_description": (
            "Turn available time into a local-only retrieval and spaced-review routine; "
            "copy, share or print the complete plan."
        ),
    },
    "zh-Hant": {
        "html_lang": "zh-Hant",
        "title": "私密單字習慣規劃器｜免費、不上傳",
        "description": (
            "依照你真正有空的時間，建立可持續的單字複習計畫。完整結果只在瀏覽器運算，免帳號、不上傳、不儲存、無分析追蹤。"
        ),
        "switch": "English",
        "switch_href": f"{SITE}/tools/{SLUG}.html",
        "home": f"{SITE}/zh-Hant/index.html",
        "tools": f"{SITE}/zh-Hant/tools/",
        "tools_label": "免費工具",
        "inline_link": "建立私密單字習慣計畫",
        "eyebrow": "免費 · 私密 · 依研究原則設計",
        "heading": "私密單字習慣規劃器",
        "lead": "把你真正有空的時間，分配成主動回想、情境學習與訂正。所有內容都不會上傳或儲存。",
        "privacy": "只在目前分頁運算 · 免帳號 · 不儲存 · 無分析追蹤",
        "scope": "僅提供計畫，不保證學會固定字數",
        "builder": "建立你的學習節奏",
        "language": "學習語言",
        "minutes": "每次可用時間",
        "sessions": "每週練習次數",
        "horizon": "規劃週期",
        "mode": "目前學習狀態",
        "goal": "主要用途",
        "make": "建立我的私密計畫",
        "minutes_unit": "分鐘",
        "sessions_unit": "次",
        "weeks_unit": "週",
        "mode_options": {
            "starter": "剛開始學習",
            "mixed": "新字與複習並行",
            "review": "重新找回忘記的單字",
        },
        "goal_options": {
            "daily": "日常理解",
            "travel": "旅行",
            "work": "工作或課業",
            "conversation": "會話",
        },
        "result_title": "你的可持續計畫",
        "result_intro": "這是起始負荷，請依延遲回想結果調整。",
        "weekly_time": "每週練習時間",
        "new_ceiling": "每次新卡起始上限",
        "per_session": "每次",
        "not_target": "這是上限，不是學會保證",
        "session_mix": "每次時間分配",
        "retrieve": "不看答案主動回想",
        "context": "用情境接觸新字",
        "correct": "訂正與朗讀重播",
        "sequence": "每週順序",
        "session": "第",
        "focus": "重點",
        "steps": [
            "先不看答案，回想之前學過的字。",
            "只加入一小組新字，並放進實用例句。",
            "每個錯誤都立即訂正，再說出或打出一次答案。",
            "下次練習與約一週後，再次檢查同一批內容。",
            "若延遲回想低於 80%，新卡量先減少約四分之一。",
        ],
        "roles": [
            "基準回想＋少量情境新字",
            "回想錯題＋補充情境",
            "混合回想＋發音",
            "不給提示的累積檢查",
            "練習符合主要用途的實用詞句",
            "彈性補課；待複習太多時不加新字",
            "每週延遲檢查＋調整下週負荷",
        ],
        "repeat_note": "依照所選週期重複此順序。想記得越久，間隔通常也需調整；沒有適合所有人的唯一完美排程。",
        "copy": "複製計畫",
        "share": "分享計畫",
        "print": "列印計畫",
        "copied": "已複製計畫。",
        "share_cancelled": "已取消分享。",
        "copy_failed": "無法自動複製，請選取下方計畫後複製。",
        "evidence_title": "為什麼安排主動回想與間隔練習",
        "evidence": (
            "主動提取記憶有助於之後保留，分散練習通常也優於集中重複。合適的間隔會隨預計保留時間改變，因此本工具採用重複檢查與調整，不宣稱存在唯一神奇間隔。"
        ),
        "source_one": "Cepeda 等人：分散練習統合分析",
        "source_two": "Roediger 與 Karpicke：測驗促進學習",
        "webmcp_source": "Chrome WebMCP imperative API",
        "webmcp_description": (
            "依支援語言、可用時間、每週頻率、規劃週期、學習狀態與用途建立私密單字計畫；"
            "回傳與畫面相同、依研究原則設計的起始上限與流程，但不保證學習成果。"
        ),
        "privacy_title": "從設計上保護隱私",
        "privacy_text": (
            "所有選項與結果只留在目前瀏覽器分頁。本頁沒有帳號、上傳、Cookie、local storage、分析、廣告程式或網路請求；重新載入或關閉頁面就會清除計畫。"
        ),
        "app_title": "想在 iPhone、主畫面與 Apple Watch 延續習慣嗎？",
        "app_text": (
            "Wordmate 是選用工具。一次付費下載即包含 44 種語言、自然例句、iPhone 與 iPad 發音、主畫面互動小工具、Apple Watch，以及每種學習語言的獨立進度。無訂閱、無 App 內購、免帳號，也沒有第三方廣告或分析追蹤。"
        ),
        "app_cta": "前往 App Store 查看 Wordmate",
        "faq_title": "常見問題",
        "faqs": [
            (
                "每天應該學幾個新單字？",
                "沒有適合所有人的固定數字。先低於工具建議的上限，再依延遲回想與待複習量增加或降低。",
            ),
            (
                "規劃器會儲存我的選項嗎？",
                "不會。本頁不使用 local storage、Cookie、帳號或上傳；關閉或重新載入頁面就會清除選項。",
            ),
            (
                "80% 回想率是科學保證嗎？",
                "不是。它只是方便調整負荷的實用觸發點，不是通用目標或成效保證；只要複習開始不穩或太重，就應降低新字量。",
            ),
        ],
        "footer": "免費瀏覽器端規劃工具。無追蹤、免帳號、不上傳伺服器。學習結果因人而異，請依自己的延遲回想持續調整。",
        "index_title": "私密單字習慣規劃器",
        "index_description": "依可用時間建立主動回想與間隔複習節奏；完整計畫可複製、分享或列印，全程不上傳。",
    },
    "zh-Hans": {
        "html_lang": "zh-Hans",
        "title": "私密单字习惯规划器｜免费、不上传",
        "description": "依照你真正有空的时间，建立可持续的单字复习计划。完整结果只在浏览器运算，免账号、不上传、不储存、无分析追踪。",
        "switch": "繁體中文",
        "switch_href": f"{SITE}/zh-Hant/tools/{SLUG}.html",
        "home": f"{SITE}/zh-Hans/index.html",
        "tools": f"{SITE}/zh-Hans/tools/",
        "tools_label": "免费工具",
        "inline_link": "建立私密单字习惯计划",
        "eyebrow": "免费 · 私密 · 依研究原则设计",
        "heading": "私密单字习惯规划器",
        "lead": "把你真正有空的时间，分配成主动回想、情境学习与订正。所有内容都不会上传或储存。",
        "privacy": "只在当前分页运算 · 免账号 · 不储存 · 无分析追踪",
        "scope": "仅提供计划，不保证学会固定字数",
        "builder": "建立你的学习节奏",
        "language": "学习语言",
        "minutes": "每次可用时间",
        "sessions": "每周练习次数",
        "horizon": "规划周期",
        "mode": "目前学习状态",
        "goal": "主要用途",
        "make": "建立我的私密计划",
        "minutes_unit": "分钟",
        "sessions_unit": "次",
        "weeks_unit": "周",
        "mode_options": {
            "starter": "刚开始学习",
            "mixed": "新字与复习并行",
            "review": "重新找回忘记的单字",
        },
        "goal_options": {
            "daily": "日常理解",
            "travel": "旅行",
            "work": "工作或学业",
            "conversation": "会话",
        },
        "result_title": "你的可持续计划",
        "result_intro": "这是起始负荷，请依延迟回想结果调整。",
        "weekly_time": "每周练习时间",
        "new_ceiling": "每次新卡起始上限",
        "per_session": "每次",
        "not_target": "这是上限，不是学会保证",
        "session_mix": "每次时间分配",
        "retrieve": "不看答案主动回想",
        "context": "用情境接触新字",
        "correct": "订正与朗读重播",
        "sequence": "每周顺序",
        "session": "第",
        "focus": "重点",
        "steps": [
            "先不看答案，回想之前学过的字。",
            "只加入一小组新字，并放进实用例句。",
            "每个错误都立即订正，再说出或打出一次答案。",
            "下次练习与约一周后，再次检查同一批内容。",
            "若延迟回想低于 80%，新卡量先减少约四分之一。",
        ],
        "roles": [
            "基准回想＋少量情境新字",
            "回想错题＋补充情境",
            "混合回想＋发音",
            "不给提示的累积检查",
            "练习符合主要用途的实用词句",
            "弹性补课；待复习太多时不加新字",
            "每周延迟检查＋调整下周负荷",
        ],
        "repeat_note": "依照所选周期重复此顺序。想记得越久，间隔通常也需调整；没有适合所有人的唯一完美排程。",
        "copy": "复制计划",
        "share": "分享计划",
        "print": "打印计划",
        "copied": "已复制计划。",
        "share_cancelled": "已取消分享。",
        "copy_failed": "无法自动复制，请选取下方计划后复制。",
        "evidence_title": "为什么安排主动回想与间隔练习",
        "evidence": "主动提取记忆有助于之后保留，分散练习通常也优于集中重复。合适的间隔会随预计保留时间改变，因此本工具采用重复检查与调整，不宣称存在唯一神奇间隔。",
        "source_one": "Cepeda 等人：分散练习统合分析",
        "source_two": "Roediger 与 Karpicke：测验促进学习",
        "webmcp_source": "Chrome WebMCP imperative API",
        "webmcp_description": "依支持语言、可用时间、每周频率、规划周期、学习状态与用途建立私密单字计划；回传与画面相同、依研究原则设计的起始上限与流程，但不保证学习成果。",
        "privacy_title": "从设计上保护隐私",
        "privacy_text": "所有选项与结果只留在当前浏览器分页。本页没有账号、上传、Cookie、local storage、分析、广告程序或网络请求；重新载入或关闭页面就会清除计划。",
        "app_title": "想在 iPhone、主屏幕与 Apple Watch 延续习惯吗？",
        "app_text": "Wordmate 是选用工具。一次付费下载即包含 44 种语言、自然例句、iPhone 与 iPad 发音、主屏幕互动小工具、Apple Watch，以及每种学习语言的独立进度。无订阅、无 App 内购、免账号，也没有第三方广告或分析追踪。",
        "app_cta": "前往 App Store 查看 Wordmate",
        "faq_title": "常见问题",
        "faqs": [
            (
                "每天应该学几个新单字？",
                "没有适合所有人的固定数字。先低于工具建议的上限，再依延迟回想与待复习量增加或降低。",
            ),
            (
                "规划器会储存我的选项吗？",
                "不会。本页不使用 local storage、Cookie、账号或上传；关闭或重新载入页面就会清除选项。",
            ),
            (
                "80% 回想率是科学保证吗？",
                "不是。它只是方便调整负荷的实用触发点，不是通用目标或成效保证；只要复习开始不稳或太重，就应降低新字量。",
            ),
        ],
        "footer": "免费浏览器端规划工具。无追踪、免账号、不上传服务器。学习结果因人而异，请依自己的延迟回想持续调整。",
        "index_title": "私密单字习惯规划器",
        "index_description": "依可用时间建立主动回想与间隔复习节奏；完整计划可复制、分享或打印，全程不上传。",
    },
    "ja": {
        "html_lang": "ja",
        "title": "プライベート単語学習習慣プランナー｜無料・非アップロード",
        "description": "実際に使える時間から、無理のない単語学習ルーティンを作成します。計算はすべてブラウザ内で完結し、アカウント登録、アップロード、保存、解析はありません。",
        "switch": "繁體中文",
        "switch_href": f"{SITE}/zh-Hant/tools/{SLUG}.html",
        "home": f"{SITE}/ja/index.html",
        "tools": f"{SITE}/ja/tools/",
        "tools_label": "無料ツール",
        "inline_link": "プライベート単語学習プランを作成する",
        "eyebrow": "無料・プライベート・研究に基づく設計",
        "heading": "プライベート単語学習習慣プランナー",
        "lead": "実際に使える時間を、想起練習・文脈学習・訂正に配分します。内容はアップロードも保存もされません。",
        "privacy": "このタブ内のみで計算 · アカウント不要 · 保存なし · 解析なし",
        "scope": "計画の補助であり、単語数の習得を保証するものではありません",
        "builder": "学習リズムを作成",
        "language": "学習言語",
        "minutes": "1回あたりの時間",
        "sessions": "週の練習回数",
        "horizon": "計画期間",
        "mode": "現在の学習状況",
        "goal": "主な目的",
        "make": "プライベートプランを作成",
        "minutes_unit": "分",
        "sessions_unit": "回",
        "weeks_unit": "週",
        "mode_options": {
            "starter": "学習を始めたばかり",
            "mixed": "新出語と復習を並行",
            "review": "忘れた単語を取り戻す",
        },
        "goal_options": {
            "daily": "日常の理解",
            "travel": "旅行",
            "work": "仕事や学業",
            "conversation": "会話",
        },
        "result_title": "あなたの継続可能なプラン",
        "result_intro": "これは開始時の目安です。遅延再生の結果に応じて調整してください。",
        "weekly_time": "週の練習時間",
        "new_ceiling": "1回あたりの新規カード上限",
        "per_session": "1回あたり",
        "not_target": "上限であり、習得を保証するものではありません",
        "session_mix": "1回の時間配分",
        "retrieve": "答えを見ない想起練習",
        "context": "文脈の中で新出語に触れる",
        "correct": "訂正と音読の反復",
        "sequence": "週間スケジュール",
        "session": "第",
        "focus": "内容",
        "steps": [
            "答えを見る前に、これまで学んだ単語を思い出しましょう。",
            "少量の新出語だけを、実用的な例文の中で学びます。",
            "間違いはすぐに訂正し、答えを一度声に出すか書きます。",
            "次回の練習と約1週間後に、同じ内容をもう一度確認します。",
            "遅延再生率が80%を下回る場合は、新規カード数を約4分の1減らします。",
        ],
        "roles": [
            "基礎想起＋少量の文脈新出語",
            "間違いの想起＋文脈の追加",
            "混合想起＋発音練習",
            "ヒントなしの累積チェック",
            "目的に合った実用フレーズ",
            "柔軟な補習；復習が多い日は新出語を追加しない",
            "週次の遅延チェックと翌週の負荷調整",
        ],
        "repeat_note": "選んだ期間だけこの流れを繰り返します。長く覚えたいほど間隔の調整も必要です。万人に完璧な唯一の予定表はありません。",
        "copy": "プランをコピー",
        "share": "プランを共有",
        "print": "プランを印刷",
        "copied": "プランをコピーしました。",
        "share_cancelled": "共有はキャンセルされました。",
        "copy_failed": "自動コピーできませんでした。下のプランを選択してコピーしてください。",
        "evidence_title": "想起練習と間隔学習を採用する理由",
        "evidence": "想起練習はその後の記憶保持を高めることがあり、分散学習は集中学習より優れる傾向があります。適切な間隔は目標の保持期間によって変わるため、本ツールは唯一絶対の間隔を主張せず、繰り返しの確認と調整を採用しています。",
        "source_one": "Cepeda ら：分散学習のメタ分析",
        "source_two": "Roediger と Karpicke：テストによる学習促進効果",
        "webmcp_source": "Chrome WebMCP imperative API",
        "webmcp_description": "対応言語、使える時間、週の頻度、計画期間、学習状況、目的からプライベートな単語プランを作成します。画面表示と同じ、研究に基づく開始上限と流れを返しますが、学習成果を保証するものではありません。",
        "privacy_title": "設計によるプライバシー保護",
        "privacy_text": "選択内容と結果はこのブラウザタブ内にのみ残ります。このページにはアカウント、アップロード、Cookie、local storage、解析、広告コード、ネットワーク通信はありません。ページを再読み込みまたは閉じるとプランは消去されます。",
        "app_title": "iPhone、ホーム画面、Apple Watchでも続けたいですか？",
        "app_text": "Wordmateは任意のアプリです。一度の購入で、44言語の体系的な単語学習、自然な例文、iPhoneとiPadでの発音再生、インタラクティブなホーム画面ウィジェット、Apple Watch、学習言語ごとの独立した進捗が含まれます。サブスクリプション、App内課金、アカウント、第三者broadcast広告や解析はありません。",
        "app_cta": "App StoreでWordmateを見る",
        "faq_title": "よくある質問",
        "faqs": [
            (
                "1日に新しい単語をいくつ学ぶべきですか？",
                "万人に共通の数字はありません。プランナーの上限より少なく始め、遅延再生の結果と復習に使える時間に応じて増減してください。",
            ),
            (
                "プランナーは選択内容を保存しますか？",
                "いいえ。local storage、Cookie、アカウント、アップロードは使用しません。ページを閉じるか再読み込みすると選択内容は消去されます。",
            ),
            (
                "80%の再生率は科学的な保証ですか？",
                "いいえ。これは負荷を調整するための実用的な目安であり、普遍的な目標や成果の保証ではありません。復習が不安定または負担に感じたら新出語数を減らしてください。",
            ),
        ],
        "footer": "無料のブラウザ内プランニングツールです。追跡やアカウント登録、サーバーへのアップロードはありません。学習成果には個人差があるため、自身の遅延再生に合わせて調整してください。",
        "index_title": "プライベート単語学習習慣プランナー",
        "index_description": "使える時間から想起練習と間隔復習のリズムを作成。完全なプランはコピー・共有・印刷でき、アップロードは一切ありません。",
    },
    "ko": {
        "html_lang": "ko",
        "title": "개인 단어 학습 습관 플래너 | 무료·비업로드",
        "description": "실제로 낼 수 있는 시간을 기준으로 현실적인 단어 학습 루틴을 만듭니다. 모든 계산은 브라우저에서만 실행되며 계정, 업로드, 저장, 분석이 없습니다.",
        "switch": "繁體中文",
        "switch_href": f"{SITE}/zh-Hant/tools/{SLUG}.html",
        "home": f"{SITE}/ko/index.html",
        "tools": f"{SITE}/ko/tools/",
        "tools_label": "무료 도구",
        "inline_link": "개인 단어 학습 습관 계획 만들기",
        "eyebrow": "무료 · 비공개 · 연구 기반 설계",
        "heading": "개인 단어 학습 습관 플래너",
        "lead": "실제로 낼 수 있는 시간을 인출 연습, 문맥 학습, 교정으로 나눕니다. 어떤 내용도 업로드되거나 저장되지 않습니다.",
        "privacy": "이 탭에서만 계산 · 계정 불필요 · 저장 없음 · 분석 없음",
        "scope": "계획 보조 도구이며 단어 습득을 보장하지 않습니다",
        "builder": "학습 루틴 만들기",
        "language": "학습 언어",
        "minutes": "세션당 시간",
        "sessions": "주당 세션 수",
        "horizon": "계획 기간",
        "mode": "현재 학습 상태",
        "goal": "주요 목적",
        "make": "내 개인 계획 만들기",
        "minutes_unit": "분",
        "sessions_unit": "회",
        "weeks_unit": "주",
        "mode_options": {
            "starter": "학습 시작 단계",
            "mixed": "새 단어와 복습 병행",
            "review": "잊어버린 단어 복구",
        },
        "goal_options": {
            "daily": "일상 이해",
            "travel": "여행",
            "work": "업무 또는 학업",
            "conversation": "회화",
        },
        "result_title": "당신의 지속 가능한 계획",
        "result_intro": "이는 시작 부하이며, 지연 회상 결과에 따라 조정하세요.",
        "weekly_time": "주간 연습 시간",
        "new_ceiling": "세션당 새 카드 상한",
        "per_session": "세션당",
        "not_target": "이는 상한이며 학습 보장이 아닙니다",
        "session_mix": "세션 시간 배분",
        "retrieve": "답을 보지 않는 능동 회상",
        "context": "문맥 속에서 새 단어 접하기",
        "correct": "교정 및 발음 재생",
        "sequence": "주간 순서",
        "session": "세션",
        "focus": "중점",
        "steps": [
            "답을 보기 전에 이전에 배운 단어를 먼저 떠올리세요.",
            "적은 양의 새 단어만 실용적인 예문 속에서 학습하세요.",
            "틀린 것은 즉시 교정하고, 답을 한 번 말하거나 적어보세요.",
            "다음 세션과 약 1주일 후에 같은 내용을 다시 확인하세요.",
            "지연 회상률이 80% 미만이면 새 카드 수를 약 4분의 1 줄이세요.",
        ],
        "roles": [
            "기본 회상 + 소량의 문맥 새 단어",
            "오답 회상 + 문맥 보충",
            "혼합 회상 + 발음",
            "힌트 없는 누적 점검",
            "목적에 맞는 실용 표현",
            "유연한 보충; 복습이 많으면 새 단어 추가 안 함",
            "주간 지연 점검 + 다음 주 부하 조정",
        ],
        "repeat_note": "선택한 기간 동안 이 순서를 반복하세요. 더 오래 기억하고 싶을수록 간격 조정이 필요하며, 모두에게 완벽한 단일 일정은 없습니다.",
        "copy": "계획 복사",
        "share": "계획 공유",
        "print": "계획 인쇄",
        "copied": "계획이 복사되었습니다.",
        "share_cancelled": "공유가 취소되었습니다.",
        "copy_failed": "자동 복사를 사용할 수 없습니다. 아래 계획을 선택해 복사하세요.",
        "evidence_title": "능동 회상과 간격 학습을 사용하는 이유",
        "evidence": "능동 인출 연습은 이후 기억 유지에 도움이 될 수 있으며, 분산 학습은 대개 집중 반복보다 효과적입니다. 적절한 간격은 원하는 기억 유지 기간에 따라 달라지므로, 이 도구는 하나의 마법 같은 간격을 주장하지 않고 반복 점검과 조정을 사용합니다.",
        "source_one": "Cepeda 외 — 분산 학습 메타분석",
        "source_two": "Roediger와 Karpicke — 시험을 통한 학습 촉진",
        "webmcp_source": "Chrome WebMCP imperative API",
        "webmcp_description": "지원 언어, 가능한 시간, 주간 빈도, 계획 기간, 학습 상태, 목적을 바탕으로 개인 단어 계획을 만듭니다. 화면과 동일한, 연구 기반의 시작 상한과 순서를 반환하지만 학습 성과를 보장하지 않습니다.",
        "privacy_title": "설계 단계부터 지켜지는 개인정보 보호",
        "privacy_text": "선택 항목과 결과는 이 브라우저 탭에만 남습니다. 이 페이지에는 계정, 업로드, 쿠키, local storage, 분석, 광고 코드, 네트워크 요청이 없습니다. 페이지를 새로고침하거나 닫으면 계획이 지워집니다.",
        "app_title": "iPhone, 홈 화면, Apple Watch에서도 루틴을 이어가고 싶으신가요?",
        "app_text": "Wordmate는 선택 사항입니다. 한 번의 유료 다운로드로 44개 언어의 체계적인 단어 학습, 자연스러운 예문, iPhone과 iPad의 발음 재생, 인터랙티브 홈 화면 위젯, Apple Watch, 학습 언어별 독립적인 진행 상황이 포함됩니다. 구독, 앱 내 구매, 계정, 제3자 광고나 분석이 없습니다.",
        "app_cta": "App Store에서 Wordmate 보기",
        "faq_title": "자주 묻는 질문",
        "faqs": [
            (
                "하루에 새 단어를 몇 개 배워야 하나요?",
                "모두에게 맞는 고정된 숫자는 없습니다. 플래너가 제시하는 상한보다 낮게 시작한 뒤, 지연 회상과 복습에 쓸 수 있는 시간에 따라 늘리거나 줄이세요.",
            ),
            (
                "플래너가 제 선택을 저장하나요?",
                "아니요. 이 페이지는 local storage, 쿠키, 계정, 업로드를 사용하지 않습니다. 페이지를 닫거나 새로고침하면 선택 항목이 지워집니다.",
            ),
            (
                "80% 회상률은 과학적 보장인가요?",
                "아니요. 이는 부하를 조정하기 위한 실용적인 기준일 뿐, 보편적 목표나 성과 보장이 아닙니다. 복습이 불안정하거나 부담스러워지면 새 단어 수를 줄이세요.",
            ),
        ],
        "footer": "무료 브라우저 기반 계획 도구입니다. 추적, 계정, 서버 업로드가 없습니다. 학습 결과는 사람마다 다르므로 본인의 지연 회상에 맞춰 계속 조정하세요.",
        "index_title": "개인 단어 학습 습관 플래너",
        "index_description": "가능한 시간을 능동 회상과 간격 복습 루틴으로 전환합니다. 완전한 계획을 복사, 공유, 인쇄할 수 있으며 업로드는 전혀 없습니다.",
    },
    "es-ES": {
        "html_lang": "es-ES",
        "title": "Planificador privado de hábitos de vocabulario | Gratis y sin subir datos",
        "description": "Crea una rutina realista de vocabulario a partir del tiempo del que dispones. El plan completo se ejecuta localmente, sin cuenta, subida, almacenamiento ni análisis.",
        "switch": "繁體中文",
        "switch_href": f"{SITE}/zh-Hant/tools/{SLUG}.html",
        "home": f"{SITE}/es-ES/index.html",
        "tools": f"{SITE}/es-ES/tools/",
        "tools_label": "Herramientas gratuitas",
        "inline_link": "Crea un plan privado de hábitos de vocabulario",
        "eyebrow": "Gratis · privado · basado en evidencia",
        "heading": "Planificador privado de hábitos de vocabulario",
        "lead": "Convierte el tiempo real del que dispones en un plan repetible de recuperación, palabras en contexto y corrección. No se sube ni se guarda nada.",
        "privacy": "Se ejecuta en esta pestaña · sin cuenta · sin almacenamiento · sin análisis",
        "scope": "Ayuda de planificación, no una promesa de palabras aprendidas",
        "builder": "Crea tu rutina",
        "language": "Idioma que aprendes",
        "minutes": "Minutos por sesión",
        "sessions": "Sesiones por semana",
        "horizon": "Horizonte de planificación",
        "mode": "Situación de estudio actual",
        "goal": "Uso principal",
        "make": "Crear mi plan privado",
        "minutes_unit": "minutos",
        "sessions_unit": "sesiones",
        "weeks_unit": "semanas",
        "mode_options": {
            "starter": "Empezando un idioma",
            "mixed": "Aprendiendo y repasando",
            "review": "Recuperando vocabulario olvidado",
        },
        "goal_options": {
            "daily": "Comprensión diaria",
            "travel": "Viajes",
            "work": "Trabajo o estudios",
            "conversation": "Conversación",
        },
        "result_title": "Tu plan repetible",
        "result_intro": "Esta es una carga inicial. Ajústala según tu recuerdo diferido.",
        "weekly_time": "Tiempo de práctica semanal",
        "new_ceiling": "Límite inicial de palabras nuevas",
        "per_session": "por sesión",
        "not_target": "Un límite, no una promesa de aprendizaje",
        "session_mix": "Reparto de la sesión",
        "retrieve": "Recuperación a libro cerrado",
        "context": "Palabras nuevas en contexto",
        "correct": "Corrección y repetición oral",
        "sequence": "Secuencia semanal",
        "session": "Sesión",
        "focus": "Enfoque",
        "steps": [
            "Recuerda las palabras anteriores antes de revelar las respuestas.",
            "Estudia el pequeño grupo de palabras nuevas dentro de frases útiles.",
            "Corrige cada error y di o escribe la respuesta una vez.",
            "Repasa el mismo material en la próxima sesión y de nuevo una semana después.",
            "Si el recuerdo diferido baja del 80%, reduce las palabras nuevas en aproximadamente un cuarto.",
        ],
        "roles": [
            "Recuperación base + pequeño grupo en contexto",
            "Recuperar errores + añadir contexto",
            "Recuerdo mixto + pronunciación",
            "Repaso acumulado sin pistas",
            "Frases útiles según el objetivo elegido",
            "Repaso flexible; no añadir nada si hay muchos repasos pendientes",
            "Comprobación semanal diferida + ajuste para la semana siguiente",
        ],
        "repeat_note": "Repite esta secuencia durante el horizonte elegido. Los periodos más largos pueden necesitar intervalos de repaso más amplios; no existe un calendario perfecto universal.",
        "copy": "Copiar plan",
        "share": "Compartir plan",
        "print": "Imprimir plan",
        "copied": "Plan copiado.",
        "share_cancelled": "Se canceló la compartición.",
        "copy_failed": "La copia no está disponible. Selecciona y copia el plan de abajo.",
        "evidence_title": "Por qué el plan usa recuperación y espaciado",
        "evidence": "La práctica de recuperación puede mejorar la retención posterior, y la práctica distribuida generalmente supera a la repetición concentrada. El intervalo de espaciado útil cambia según el periodo de retención deseado, por lo que este planificador usa comprobaciones y ajustes repetidos en lugar de afirmar que existe un intervalo mágico único.",
        "source_one": "Cepeda et al. — metaanálisis de práctica distribuida",
        "source_two": "Roediger y Karpicke — aprendizaje potenciado por pruebas",
        "webmcp_source": "API imperativa Chrome WebMCP",
        "webmcp_description": "Crea una rutina privada de vocabulario a partir de un idioma compatible, el tiempo disponible, la frecuencia semanal, el horizonte, el modo de estudio y el objetivo. Devuelve el mismo límite inicial y la misma secuencia basados en evidencia que el planificador visible, sin prometer resultados de aprendizaje.",
        "privacy_title": "Privacidad por diseño",
        "privacy_text": "Las selecciones y resultados permanecen en esta pestaña del navegador. La página no tiene cuenta, subida, cookies, almacenamiento local, análisis, código publicitario ni solicitudes de red. Recargar o cerrar la página borra el plan.",
        "app_title": "¿Quieres continuar la rutina en iPhone, pantalla de inicio y Apple Watch?",
        "app_text": "Wordmate es opcional. Su descarga de pago único incluye vocabulario estructurado en 44 idiomas, ejemplos naturales, pronunciación en iPhone y iPad, un widget interactivo de pantalla de inicio, Apple Watch y progreso independiente para cada idioma que aprendas. Sin suscripción, sin compras integradas, sin cuenta, sin anuncios de terceros ni análisis.",
        "app_cta": "Ver Wordmate en la App Store",
        "faq_title": "Preguntas frecuentes",
        "faqs": [
            (
                "¿Cuántas palabras nuevas debo aprender cada día?",
                "No hay un número universal. Empieza por debajo del límite del planificador y luego súbelo o bájalo según el recuerdo diferido y el tiempo de repaso disponible.",
            ),
            (
                "¿El planificador guarda mis selecciones?",
                "No. No usa almacenamiento local, cookies, cuenta ni subida. Cerrar o recargar la página borra las selecciones.",
            ),
            (
                "¿Es una comprobación del 80% de recuerdo una garantía científica?",
                "No. Es un desencadenante práctico de ajuste, no un objetivo universal ni una garantía de resultados. Reduce la carga siempre que los repasos se sientan inestables o excesivos.",
            ),
        ],
        "footer": "Herramienta gratuita de planificación en el navegador. Sin seguimiento, cuenta ni subida al servidor. Los resultados de aprendizaje varían; ajusta el plan según tu propio recuerdo diferido.",
        "index_title": "Planificador privado de hábitos de vocabulario",
        "index_description": "Convierte el tiempo disponible en una rutina local de recuperación y repaso espaciado; copia, comparte o imprime el plan completo.",
    },
    "pt-BR": {
        "html_lang": "pt-BR",
        "title": "Planejador privado de hábitos de vocabulário | Grátis e sem envio de dados",
        "description": "Crie uma rotina realista de vocabulário a partir do tempo que você realmente tem. O plano completo roda localmente, sem conta, envio, armazenamento ou análise.",
        "switch": "繁體中文",
        "switch_href": f"{SITE}/zh-Hant/tools/{SLUG}.html",
        "home": f"{SITE}/pt-BR/index.html",
        "tools": f"{SITE}/pt-BR/tools/",
        "tools_label": "Ferramentas gratuitas",
        "inline_link": "Crie um plano privado de hábitos de vocabulário",
        "eyebrow": "Grátis · privado · baseado em evidências",
        "heading": "Planejador privado de hábitos de vocabulário",
        "lead": "Transforme o tempo que você realmente tem em um plano repetível de recuperação, palavras em contexto e correção. Nada é enviado ou salvo.",
        "privacy": "Roda nesta aba · sem conta · sem armazenamento · sem análise",
        "scope": "Auxílio de planejamento, não uma promessa de palavras aprendidas",
        "builder": "Crie sua rotina",
        "language": "Idioma que está aprendendo",
        "minutes": "Minutos por sessão",
        "sessions": "Sessões por semana",
        "horizon": "Horizonte de planejamento",
        "mode": "Situação de estudo atual",
        "goal": "Uso principal",
        "make": "Criar meu plano privado",
        "minutes_unit": "minutos",
        "sessions_unit": "sessões",
        "weeks_unit": "semanas",
        "mode_options": {
            "starter": "Começando um idioma",
            "mixed": "Aprendendo e revisando",
            "review": "Recuperando vocabulário esquecido",
        },
        "goal_options": {
            "daily": "Compreensão do dia a dia",
            "travel": "Viagem",
            "work": "Trabalho ou estudo",
            "conversation": "Conversação",
        },
        "result_title": "Seu plano repetível",
        "result_intro": "Esta é uma carga inicial. Ajuste-a de acordo com sua recordação tardia.",
        "weekly_time": "Tempo semanal de prática",
        "new_ceiling": "Limite inicial de cartões novos",
        "per_session": "por sessão",
        "not_target": "Um limite, não uma promessa de aprendizado",
        "session_mix": "Divisão da sessão",
        "retrieve": "Recuperação de livro fechado",
        "context": "Palavras novas em contexto",
        "correct": "Correção e repetição falada",
        "sequence": "Sequência semanal",
        "session": "Sessão",
        "focus": "Foco",
        "steps": [
            "Lembre as palavras antigas antes de revelar as respostas.",
            "Estude o pequeno grupo de palavras novas dentro de frases úteis.",
            "Corrija cada erro e diga ou digite a resposta uma vez.",
            "Revise o mesmo conteúdo na próxima sessão e novamente cerca de uma semana depois.",
            "Se a recordação tardia ficar abaixo de 80%, reduza as palavras novas em cerca de um quarto.",
        ],
        "roles": [
            "Recuperação de base + pequeno grupo em contexto",
            "Recuperar erros + adicionar contexto",
            "Recordação mista + pronúncia",
            "Verificação cumulativa sem dicas",
            "Frases úteis para o objetivo escolhido",
            "Reforço flexível; não adicione nada se houver muitas revisões pendentes",
            "Verificação semanal tardia + ajuste para a semana seguinte",
        ],
        "repeat_note": "Repita esta sequência durante o horizonte escolhido. Períodos mais longos podem precisar de intervalos de revisão maiores; não existe um cronograma perfeito universal.",
        "copy": "Copiar plano",
        "share": "Compartilhar plano",
        "print": "Imprimir plano",
        "copied": "Plano copiado.",
        "share_cancelled": "O compartilhamento foi cancelado.",
        "copy_failed": "A cópia não está disponível. Selecione e copie o plano abaixo.",
        "evidence_title": "Por que o plano usa recuperação e espaçamento",
        "evidence": "A prática de recuperação pode melhorar a retenção posterior, e a prática distribuída geralmente supera a repetição concentrada. O intervalo de espaçamento útil muda de acordo com o período de retenção desejado, então este planejador usa verificações e ajustes repetidos em vez de afirmar que existe um intervalo mágico único.",
        "source_one": "Cepeda et al. — metanálise de prática distribuída",
        "source_two": "Roediger e Karpicke — aprendizado potencializado por testes",
        "webmcp_source": "API imperativa Chrome WebMCP",
        "webmcp_description": "Crie uma rotina privada de vocabulário a partir de um idioma compatível, tempo disponível, frequência semanal, horizonte, modo de estudo e objetivo. Retorna o mesmo limite inicial e sequência baseados em evidências do planejador visível, sem prometer resultados de aprendizado.",
        "privacy_title": "Privacidade por design",
        "privacy_text": "As seleções e resultados permanecem nesta aba do navegador. A página não tem conta, envio, cookies, armazenamento local, análise, código de publicidade ou solicitações de rede. Recarregar ou fechar a página apaga o plano.",
        "app_title": "Quer continuar a rotina no iPhone, na Tela de Início e no Apple Watch?",
        "app_text": "O Wordmate é opcional. Seu download pago único inclui vocabulário estruturado em 44 idiomas, exemplos naturais, pronúncia no iPhone e iPad, um widget interativo na Tela de Início, Apple Watch e progresso separado para cada idioma aprendido. Sem assinatura, compra no app, conta, anúncios de terceiros ou análise.",
        "app_cta": "Ver o Wordmate na App Store",
        "faq_title": "Perguntas frequentes",
        "faqs": [
            (
                "Quantas palavras novas devo aprender por dia?",
                "Não há um número universal. Comece abaixo do limite sugerido pelo planejador e depois aumente ou diminua de acordo com a recordação tardia e o tempo disponível para revisão.",
            ),
            (
                "O planejador salva minhas escolhas?",
                "Não. Esta página não usa armazenamento local, cookies, conta ou envio. Fechar ou recarregar a página apaga as escolhas.",
            ),
            (
                "Uma verificação de 80% de recordação é uma garantia científica?",
                "Não. É um gatilho prático de ajuste, não uma meta universal ou garantia de resultado. Reduza a carga sempre que as revisões parecerem instáveis ou pesadas.",
            ),
        ],
        "footer": "Ferramenta gratuita de planejamento no navegador. Sem rastreamento, conta ou envio ao servidor. Os resultados de aprendizado variam; ajuste o plano de acordo com sua própria recordação tardia.",
        "index_title": "Planejador privado de hábitos de vocabulário",
        "index_description": "Transforme o tempo disponível em uma rotina local de recuperação e revisão espaçada; copie, compartilhe ou imprima o plano completo.",
    },
    "de-DE": {
        "html_lang": "de-DE",
        "title": "Privater Vokabel-Gewohnheitsplaner | Kostenlos & ohne Upload",
        "description": "Erstelle eine realistische Vokabelroutine aus der Zeit, die dir tatsächlich zur Verfügung steht. Der komplette Plan läuft lokal, ohne Konto, Upload, Speicherung oder Analyse.",
        "switch": "繁體中文",
        "switch_href": f"{SITE}/zh-Hant/tools/{SLUG}.html",
        "home": f"{SITE}/de-DE/index.html",
        "tools": f"{SITE}/de-DE/tools/",
        "tools_label": "Kostenlose Tools",
        "inline_link": "Privaten Vokabel-Gewohnheitsplan erstellen",
        "eyebrow": "Kostenlos · privat · evidenzbasiert",
        "heading": "Privater Vokabel-Gewohnheitsplaner",
        "lead": "Verwandle die Zeit, die dir wirklich zur Verfügung steht, in einen wiederholbaren Plan aus Abrufübung, Wörtern im Kontext und Korrektur. Nichts wird hochgeladen oder gespeichert.",
        "privacy": "Läuft nur in diesem Tab · kein Konto · keine Speicherung · keine Analyse",
        "scope": "Planungshilfe, kein Versprechen gelernter Wörter",
        "builder": "Erstelle deine Routine",
        "language": "Zu lernende Sprache",
        "minutes": "Minuten pro Einheit",
        "sessions": "Einheiten pro Woche",
        "horizon": "Planungshorizont",
        "mode": "Aktueller Lernstand",
        "goal": "Hauptzweck",
        "make": "Meinen privaten Plan erstellen",
        "minutes_unit": "Minuten",
        "sessions_unit": "Einheiten",
        "weeks_unit": "Wochen",
        "mode_options": {
            "starter": "Beginn einer Sprache",
            "mixed": "Lernen und Wiederholen",
            "review": "Vergessene Vokabeln zurückgewinnen",
        },
        "goal_options": {
            "daily": "Alltagsverständnis",
            "travel": "Reisen",
            "work": "Arbeit oder Studium",
            "conversation": "Konversation",
        },
        "result_title": "Dein wiederholbarer Plan",
        "result_intro": "Dies ist eine Startlast. Passe sie anhand des verzögerten Abrufs an.",
        "weekly_time": "Wöchentliche Übungszeit",
        "new_ceiling": "Anfängliche Obergrenze für neue Karten",
        "per_session": "pro Einheit",
        "not_target": "Eine Obergrenze, kein Lernversprechen",
        "session_mix": "Aufteilung der Einheit",
        "retrieve": "Abrufübung ohne Nachschlagen",
        "context": "Neue Wörter im Kontext",
        "correct": "Korrektur und mündliche Wiederholung",
        "sequence": "Wöchentlicher Ablauf",
        "session": "Einheit",
        "focus": "Schwerpunkt",
        "steps": [
            "Rufe zuerst ältere Wörter ab, bevor du die Antworten aufdeckst.",
            "Lerne die kleine Gruppe neuer Wörter in nützlichen Sätzen.",
            "Korrigiere jeden Fehler sofort und sage oder schreibe die Antwort einmal.",
            "Überprüfe denselben Stoff in der nächsten Einheit und noch einmal etwa eine Woche später.",
            "Liegt der verzögerte Abruf unter 80 %, reduziere die neuen Karten um etwa ein Viertel.",
        ],
        "roles": [
            "Basisabruf + kleine Kontextgruppe",
            "Fehler abrufen + Kontext ergänzen",
            "Gemischter Abruf + Aussprache",
            "Kumulative Prüfung ohne Hinweise",
            "Nützliche Sätze für das gewählte Ziel",
            "Flexible Nachholzeit; nichts hinzufügen, wenn viele Wiederholungen anstehen",
            "Wöchentliche verzögerte Prüfung + Anpassung für die nächste Woche",
        ],
        "repeat_note": "Wiederhole diesen Ablauf für den gewählten Horizont. Je länger du dir etwas merken willst, desto eher müssen die Abstände angepasst werden; es gibt keinen universell perfekten Zeitplan.",
        "copy": "Plan kopieren",
        "share": "Plan teilen",
        "print": "Plan drucken",
        "copied": "Plan kopiert.",
        "share_cancelled": "Das Teilen wurde abgebrochen.",
        "copy_failed": "Kopieren war nicht möglich. Markiere und kopiere den Plan unten.",
        "evidence_title": "Warum der Plan auf Abruf und Verteilung setzt",
        "evidence": "Abrufübung kann die spätere Behaltensleistung verbessern, und verteiltes Lernen übertrifft in der Regel massiertes Wiederholen. Der nützliche Abstand ändert sich je nach gewünschter Behaltensdauer, daher setzt dieser Planer auf wiederholte Prüfungen und Anpassungen, statt ein einziges magisches Intervall zu behaupten.",
        "source_one": "Cepeda et al. — Metaanalyse zu verteiltem Lernen",
        "source_two": "Roediger und Karpicke — testgestütztes Lernen",
        "webmcp_source": "Chrome WebMCP Imperative API",
        "webmcp_description": "Erstellt eine private Vokabelroutine aus einer unterstützten Sprache, verfügbarer Zeit, wöchentlicher Häufigkeit, Horizont, Lernmodus und Ziel. Gibt dieselbe evidenzbasierte Startobergrenze und Abfolge wie der sichtbare Planer zurück, ohne Lernergebnisse zu versprechen.",
        "privacy_title": "Datenschutz durch Design",
        "privacy_text": "Auswahl und Ergebnisse verbleiben in diesem Browser-Tab. Die Seite hat kein Konto, keinen Upload, keine Cookies, kein Local Storage, keine Analyse, keinen Werbecode und keine Netzwerkanfragen. Neuladen oder Schließen der Seite löscht den Plan.",
        "app_title": "Möchtest du die Routine auf iPhone, Home-Bildschirm und Apple Watch fortsetzen?",
        "app_text": "Wordmate ist optional. Der einmalige kostenpflichtige Download umfasst strukturierten Wortschatz in 44 Sprachen, natürliche Beispiele, Aussprache auf iPhone und iPad, ein interaktives Home-Bildschirm-Widget, Apple Watch und separaten Fortschritt für jede gelernte Sprache. Kein Abonnement, kein In-App-Kauf, kein Konto, keine Werbung oder Analyse von Drittanbietern.",
        "app_cta": "Wordmate im App Store ansehen",
        "faq_title": "Häufige Fragen",
        "faqs": [
            (
                "Wie viele neue Wörter sollte ich täglich lernen?",
                "Es gibt keine universelle Zahl. Beginne unterhalb der Obergrenze des Planers und erhöhe oder senke sie je nach verzögertem Abruf und verfügbarer Wiederholungszeit.",
            ),
            (
                "Speichert der Planer meine Auswahl?",
                "Nein. Diese Seite verwendet keinen Local Storage, keine Cookies, kein Konto und keinen Upload. Schließen oder Neuladen der Seite löscht die Auswahl.",
            ),
            (
                "Ist eine 80-%-Abrufprüfung eine wissenschaftliche Garantie?",
                "Nein. Es ist ein praktischer Auslöser zur Anpassung, kein universelles Ziel oder eine Erfolgsgarantie. Senke die Last, sobald sich Wiederholungen instabil oder zu umfangreich anfühlen.",
            ),
        ],
        "footer": "Kostenloses browserbasiertes Planungstool. Kein Tracking, kein Konto, kein Server-Upload. Lernergebnisse variieren; passe den Plan an deinen eigenen verzögerten Abruf an.",
        "index_title": "Privater Vokabel-Gewohnheitsplaner",
        "index_description": "Verwandelt verfügbare Zeit in eine lokale Routine aus Abrufübung und verteilter Wiederholung; kopiere, teile oder drucke den vollständigen Plan.",
    },
    "fr-FR": {
        "html_lang": "fr-FR",
        "title": "Planificateur privé d'habitudes de vocabulaire | Gratuit, sans envoi de données",
        "description": "Construisez une routine de vocabulaire réaliste à partir du temps dont vous disposez réellement. Le plan complet s'exécute localement, sans compte, envoi, stockage ni analyse.",
        "switch": "繁體中文",
        "switch_href": f"{SITE}/zh-Hant/tools/{SLUG}.html",
        "home": f"{SITE}/fr-FR/index.html",
        "tools": f"{SITE}/fr-FR/tools/",
        "tools_label": "Outils gratuits",
        "inline_link": "Créer un plan privé d'habitudes de vocabulaire",
        "eyebrow": "Gratuit · privé · fondé sur des données probantes",
        "heading": "Planificateur privé d'habitudes de vocabulaire",
        "lead": "Transformez le temps dont vous disposez réellement en un plan répétable de rappel, de mots en contexte et de correction. Rien n'est envoyé ni enregistré.",
        "privacy": "Fonctionne dans cet onglet · sans compte · sans stockage · sans analyse",
        "scope": "Aide à la planification, pas une promesse de mots appris",
        "builder": "Créez votre routine",
        "language": "Langue apprise",
        "minutes": "Minutes par séance",
        "sessions": "Séances par semaine",
        "horizon": "Horizon de planification",
        "mode": "Situation d'étude actuelle",
        "goal": "Usage principal",
        "make": "Créer mon plan privé",
        "minutes_unit": "minutes",
        "sessions_unit": "séances",
        "weeks_unit": "semaines",
        "mode_options": {
            "starter": "Débute une langue",
            "mixed": "Apprend et révise",
            "review": "Récupère un vocabulaire oublié",
        },
        "goal_options": {
            "daily": "Compréhension quotidienne",
            "travel": "Voyage",
            "work": "Travail ou études",
            "conversation": "Conversation",
        },
        "result_title": "Votre plan répétable",
        "result_intro": "Il s'agit d'une charge de départ. Ajustez-la selon votre rappel différé.",
        "weekly_time": "Temps de pratique hebdomadaire",
        "new_ceiling": "Plafond initial de nouvelles cartes",
        "per_session": "par séance",
        "not_target": "Un plafond, pas une promesse d'apprentissage",
        "session_mix": "Répartition de la séance",
        "retrieve": "Rappel livre fermé",
        "context": "Nouveaux mots en contexte",
        "correct": "Correction et répétition orale",
        "sequence": "Séquence hebdomadaire",
        "session": "Séance",
        "focus": "Objectif",
        "steps": [
            "Rappelez-vous les mots plus anciens avant de révéler les réponses.",
            "Étudiez le petit groupe de nouveaux mots dans des phrases utiles.",
            "Corrigez chaque erreur, puis dites ou écrivez la réponse une fois.",
            "Revoyez le même contenu à la prochaine séance et de nouveau environ une semaine plus tard.",
            "Si le rappel différé est inférieur à 80 %, réduisez les nouvelles cartes d'environ un quart.",
        ],
        "roles": [
            "Rappel de base + petit groupe en contexte",
            "Rappel des erreurs + ajout de contexte",
            "Rappel mixte + prononciation",
            "Vérification cumulative sans indice",
            "Phrases utiles selon l'objectif choisi",
            "Rattrapage flexible ; n'ajoutez rien si les révisions sont chargées",
            "Vérification hebdomadaire différée + ajustement pour la semaine suivante",
        ],
        "repeat_note": "Répétez cette séquence pendant l'horizon choisi. Plus vous souhaitez retenir longtemps, plus les intervalles doivent être ajustés ; il n'existe pas de calendrier parfait universel.",
        "copy": "Copier le plan",
        "share": "Partager le plan",
        "print": "Imprimer le plan",
        "copied": "Plan copié.",
        "share_cancelled": "Le partage a été annulé.",
        "copy_failed": "La copie n'est pas disponible. Sélectionnez et copiez le plan ci-dessous.",
        "evidence_title": "Pourquoi le plan utilise le rappel et l'espacement",
        "evidence": "La pratique du rappel peut améliorer la rétention ultérieure, et la pratique distribuée surpasse généralement la répétition massée. L'intervalle d'espacement utile change selon la durée de rétention souhaitée ; cet outil utilise donc des vérifications et des ajustements répétés plutôt que d'affirmer l'existence d'un intervalle magique unique.",
        "source_one": "Cepeda et al. — méta-analyse sur la pratique distribuée",
        "source_two": "Roediger et Karpicke — apprentissage renforcé par les tests",
        "webmcp_source": "API impérative Chrome WebMCP",
        "webmcp_description": "Crée une routine privée de vocabulaire à partir d'une langue prise en charge, du temps disponible, de la fréquence hebdomadaire, de l'horizon, du mode d'étude et de l'objectif. Renvoie le même plafond initial et la même séquence fondés sur des données probantes que le planificateur visible, sans promettre de résultats d'apprentissage.",
        "privacy_title": "Confidentialité dès la conception",
        "privacy_text": "Les sélections et résultats restent dans cet onglet du navigateur. La page n'a ni compte, ni envoi, ni cookies, ni stockage local, ni analyse, ni code publicitaire, ni requête réseau. Recharger ou fermer la page efface le plan.",
        "app_title": "Envie de poursuivre la routine sur iPhone, écran d'accueil et Apple Watch ?",
        "app_text": "Wordmate est optionnel. Son téléchargement payant unique inclut un vocabulaire structuré en 44 langues, des exemples naturels, la prononciation sur iPhone et iPad, un widget interactif d'écran d'accueil, Apple Watch et une progression distincte pour chaque langue apprise. Sans abonnement, sans achat intégré, sans compte, sans publicité tierce ni analyse.",
        "app_cta": "Voir Wordmate sur l'App Store",
        "faq_title": "Questions fréquentes",
        "faqs": [
            (
                "Combien de nouveaux mots dois-je apprendre chaque jour ?",
                "Il n'existe pas de nombre universel. Commencez en dessous du plafond proposé par le planificateur, puis ajustez-le à la hausse ou à la baisse selon le rappel différé et le temps de révision disponible.",
            ),
            (
                "Le planificateur enregistre-t-il mes choix ?",
                "Non. Cette page n'utilise ni stockage local, ni cookies, ni compte, ni envoi. Fermer ou recharger la page efface les choix.",
            ),
            (
                "Une vérification de rappel à 80 % est-elle une garantie scientifique ?",
                "Non. C'est un déclencheur pratique d'ajustement, pas un objectif universel ni une garantie de résultat. Réduisez la charge dès que les révisions semblent instables ou trop lourdes.",
            ),
        ],
        "footer": "Outil de planification gratuit côté navigateur. Aucun suivi, compte ni envoi au serveur. Les résultats d'apprentissage varient ; ajustez le plan selon votre propre rappel différé.",
        "index_title": "Planificateur privé d'habitudes de vocabulaire",
        "index_description": "Transforme le temps disponible en une routine locale de rappel et de révision espacée ; copiez, partagez ou imprimez le plan complet.",
    },
}


def canonical(locale: str) -> str:
    if locale not in ALT_LOCALES:
        raise ValueError(f"unsupported locale: {locale}")
    prefix = "" if locale == "en" else f"{locale}/"
    return f"{SITE}/{prefix}tools/{SLUG}.html"


def language_display_name(locale: str, code: str, english_name: str, zh_hant_name: str) -> str:
    if locale == "en":
        return english_name
    if locale == "zh-Hant":
        return zh_hant_name
    return _LANGUAGE_LOCALE_NAMES[locale][code]


def language_options(locale: str) -> str:
    selected = "es" if locale == "en" else "en"
    return "\n".join(
        f'<option value="{html.escape(code)}"'
        f'{" selected" if code == selected else ""}>'
        f"{html.escape(language_display_name(locale, code, english_name, zh_hant_name))}</option>"
        for code, english_name, zh_hant_name in LANGUAGES
    )


def select_options(values: list[int], unit: str, selected: int) -> str:
    return "\n".join(
        f'<option value="{value}"{" selected" if value == selected else ""}>'
        f"{value} {html.escape(unit)}</option>"
        for value in values
    )


def webmcp_languages(locale: str) -> list[dict[str, str]]:
    return [
        {
            "code": code,
            "name": language_display_name(locale, code, english_name, zh_hant_name),
        }
        for code, english_name, zh_hant_name in LANGUAGES
    ]


def webmcp_input_schema(locale: str) -> dict[str, object]:
    copy = COPY[locale]
    mode_values = list(copy["mode_options"])
    goal_values = list(copy["goal_options"])
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "language_code",
            "minutes_per_session",
            "sessions_per_week",
            "horizon_weeks",
            "study_mode",
            "primary_goal",
        ],
        "properties": {
            "language_code": {
                "type": "string",
                "enum": [code for code, _, _ in LANGUAGES],
                "description": copy["language"],
            },
            "minutes_per_session": {
                "type": "integer",
                "enum": [5, 10, 15, 20, 30, 45],
                "description": copy["minutes"],
            },
            "sessions_per_week": {
                "type": "integer",
                "enum": [2, 3, 4, 5, 6, 7],
                "description": copy["sessions"],
            },
            "horizon_weeks": {
                "type": "integer",
                "enum": [2, 4, 8, 12],
                "description": copy["horizon"],
            },
            "study_mode": {
                "type": "string",
                "enum": mode_values,
                "description": copy["mode"],
            },
            "primary_goal": {
                "type": "string",
                "enum": goal_values,
                "description": copy["goal"],
            },
        },
    }


def schema(locale: str, copy: dict[str, object]) -> str:
    faq = [
        {
            "@type": "Question",
            "name": question,
            "acceptedAnswer": {"@type": "Answer", "text": answer},
        }
        for question, answer in copy["faqs"]
    ]
    data = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebApplication",
                "name": copy["heading"],
                "url": canonical(locale),
                "applicationCategory": "EducationalApplication",
                "operatingSystem": "Any modern browser",
                "browserRequirements": "JavaScript",
                "isAccessibleForFree": True,
                "inLanguage": copy["html_lang"],
                "description": copy["description"],
                "dateModified": TOOL_DATE,
                "featureList": [
                    "Local-only calculation",
                    "Retrieval and spaced-review plan",
                    "Copy, share and print",
                    "No account, upload, storage or analytics",
                    "Progressive read-only WebMCP planning for supporting browsers",
                ],
            },
            {
                "@type": "FAQPage",
                "inLanguage": copy["html_lang"],
                "mainEntity": faq,
            },
        ],
    }
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def render_page(locale: str, *, show_app_cta: bool = False) -> str:
    if locale not in COPY:
        raise ValueError(f"unsupported locale: {locale}")
    copy = COPY[locale]
    esc = html.escape
    tracked_app_url = (
        appstore_url(APP_KEY, f"iag_vocab_planner_{locale.lower()}")
        if show_app_cta
        else ""
    )
    alternate_links = "\n".join(
        f'<link rel="alternate" hreflang="{alt}" href="{canonical(alt)}">'
        for alt in ALT_LOCALES
    )
    alternate_links += (
        f'\n<link rel="alternate" hreflang="x-default" href="{canonical("en")}">'
    )
    mode_options = "\n".join(
        f'<option value="{esc(key)}">{esc(value)}</option>'
        for key, value in copy["mode_options"].items()
    )
    goal_options = "\n".join(
        f'<option value="{esc(key)}">{esc(value)}</option>'
        for key, value in copy["goal_options"].items()
    )
    faq_html = "\n".join(
        f"<details><summary>{esc(question)}</summary><p>{esc(answer)}</p></details>"
        for question, answer in copy["faqs"]
    )
    app_card = ""
    if show_app_cta:
        app_card = f"""
<section class="card app-card no-print">
  <div>
    <p class="eyebrow">{esc(copy["app_title"])}</p>
    <p>{esc(copy["app_text"])}</p>
  </div>
  <a class="primary one-line" href="{esc(tracked_app_url)}">{esc(copy["app_cta"])}</a>
</section>"""
    js_copy = {
        key: copy[key]
        for key in (
            "weekly_time",
            "new_ceiling",
            "per_session",
            "not_target",
            "session_mix",
            "retrieve",
            "context",
            "correct",
            "sequence",
            "session",
            "focus",
            "steps",
            "roles",
            "repeat_note",
            "copied",
            "share_cancelled",
            "copy_failed",
            "minutes_unit",
            "sessions_unit",
            "weeks_unit",
            "privacy_text",
        )
    }
    page = r"""<!doctype html>
<html lang="__HTML_LANG__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<meta name="description" content="__DESCRIPTION__">
<link rel="canonical" href="__CANONICAL__">
__ALTERNATE_LINKS__
__FEEDS__
<meta property="og:type" content="website">
<meta property="og:title" content="__HEADING__">
<meta property="og:description" content="__DESCRIPTION__">
<meta property="og:url" content="__CANONICAL__">
<meta name="twitter:card" content="summary">
<script type="application/ld+json">__SCHEMA__</script>
<style>
:root{--ink:#17201d;--muted:#596763;--line:#dce6e1;--paper:#fff;--mint:#e9f7f0;--teal:#126b57;--violet:#6c4fd3;--shadow:0 22px 70px rgba(27,68,57,.11);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color-scheme:light}
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(circle at 8% 2%,#e4fff3 0,transparent 31%),radial-gradient(circle at 92% 12%,#eee9ff 0,transparent 34%),#f8fbf9;color:var(--ink);line-height:1.58}
a{color:var(--teal)}
.wrap{width:min(1080px,calc(100% - 30px));margin:auto}
.top{position:sticky;top:0;z-index:4;border-bottom:1px solid rgba(220,230,225,.82);background:rgba(248,251,249,.9);backdrop-filter:blur(18px)}
.nav{min-height:64px;display:flex;align-items:center;justify-content:space-between;gap:12px}
.nav a{font-weight:800;text-decoration:none;white-space:nowrap}
.hero{padding:64px 0 30px}
.eyebrow{margin:0 0 9px;color:var(--teal);font-size:.78rem;font-weight:900;letter-spacing:.1em;text-transform:uppercase;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
h1{margin:0;font-size:clamp(1.15rem,5.6vw,3.8rem);line-height:1.05;letter-spacing:-.045em;white-space:nowrap}
.lead{max-width:760px;margin:18px 0 0;color:var(--muted);font-size:clamp(1rem,2vw,1.2rem)}
.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:20px}
.badge{display:inline-flex;border:1px solid var(--line);border-radius:999px;padding:7px 11px;background:rgba(255,255,255,.82);font-size:.82rem;font-weight:800;white-space:nowrap}
.layout{display:grid;gap:20px;margin-bottom:24px}
@media(min-width:820px){.layout{grid-template-columns:minmax(300px,.8fr) minmax(430px,1.2fr);align-items:start}}
.card{border:1px solid var(--line);border-radius:28px;background:rgba(255,255,255,.93);box-shadow:var(--shadow);padding:clamp(20px,4vw,32px)}
.card h2{margin:0 0 8px;font-size:clamp(1.35rem,3vw,2rem);letter-spacing:-.025em}
.field-grid{display:grid;grid-template-columns:1fr;gap:14px;margin-top:24px}
@media(min-width:540px){.field-grid{grid-template-columns:1fr 1fr}}
label{display:block;margin:0 0 6px;font-weight:850;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
select{width:100%;min-height:48px;border:1px solid #cbd8d2;border-radius:14px;background:#fff;color:var(--ink);font:inherit;padding:10px 38px 10px 12px}
button,.primary{min-height:48px;border:0;border-radius:999px;padding:12px 18px;background:linear-gradient(135deg,var(--teal),#178c70);color:#fff!important;font:inherit;font-weight:900;text-decoration:none;box-shadow:0 10px 28px rgba(18,107,87,.22);cursor:pointer}
button:focus-visible,select:focus-visible,a:focus-visible{outline:3px solid rgba(108,79,211,.4);outline-offset:3px}
.build{width:100%;margin-top:20px}
.one-line{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.result-card{background:linear-gradient(160deg,#fff,#f0fbf6)}
.result-card[hidden]{display:none}
.result-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px}
.metric-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:20px 0}
.metric{border:1px solid var(--line);border-radius:18px;background:#fff;padding:14px}
.metric strong{display:block;font-size:clamp(1.3rem,4vw,2rem);line-height:1.1}
.metric span{display:block;color:var(--muted);font-size:.82rem;margin-top:5px}
.mix{display:grid;gap:9px;margin:14px 0 22px}
.mix-row{display:grid;grid-template-columns:minmax(130px,1fr) 2fr 40px;align-items:center;gap:9px;font-size:.9rem}
.mix-row span:first-child{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar{height:10px;border-radius:999px;background:#e5eee9;overflow:hidden}
.bar i{display:block;height:100%;border-radius:inherit;background:linear-gradient(90deg,var(--teal),var(--violet))}
table{width:100%;border-collapse:collapse;margin-top:10px}
th,td{padding:10px 8px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:.78rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);white-space:nowrap}
td:first-child{white-space:nowrap;font-weight:800}
.checklist{padding-left:1.25rem}
.checklist li{margin:.5rem 0}
.actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px}
.ghost{background:#fff;color:var(--teal)!important;border:1px solid #cbd8d2;box-shadow:none}
.status{min-height:1.4em;margin:12px 0 0;color:var(--teal);font-weight:800}
.wide{margin-bottom:24px}
.research{display:grid;gap:20px}
@media(min-width:760px){.research{grid-template-columns:1fr 1fr}}
.research a{font-weight:800}
.app-card{display:grid;gap:18px;align-items:center;margin-bottom:24px;background:linear-gradient(135deg,#f2edff,#e7fbf2)}
@media(min-width:760px){.app-card{grid-template-columns:1fr auto}}
.app-card p{margin:4px 0}
details{border-top:1px solid var(--line);padding:14px 0}
summary{font-weight:850;cursor:pointer}
footer{padding:30px 0 50px;color:var(--muted);font-size:.9rem}
@media(max-width:430px){.metric-grid{grid-template-columns:1fr}.mix-row{grid-template-columns:minmax(112px,1fr) 1.3fr 34px}.card{border-radius:22px}.nav{font-size:.88rem}}
@media print{body{background:#fff}.no-print,.top,.builder-card,.research,.app-card,footer{display:none!important}.layout{display:block}.result-card{display:block!important;border:0;box-shadow:none;padding:0}.wrap{width:100%}h1{white-space:normal}.result-card table{font-size:11pt}}
</style>
</head>
<body>
<header class="top no-print"><div class="wrap nav"><a href="__HOME__">iOS App Guide</a><nav><a href="__TOOLS__">__TOOLS_LABEL__</a> · <a href="__SWITCH_HREF__">__SWITCH__</a></nav></div></header>
<main>
<section class="hero wrap">
  <p class="eyebrow">__EYEBROW__</p>
  <h1>__HEADING__</h1>
  <p class="lead">__LEAD__</p>
  <div class="badges"><span class="badge">__PRIVACY__</span><span class="badge">__SCOPE__</span></div>
</section>
<section class="wrap layout">
  <form class="card builder-card no-print" id="planner">
    <h2 class="one-line">__BUILDER__</h2>
    <div class="field-grid">
      <div><label for="language">__LANGUAGE__</label><select id="language">__LANGUAGE_OPTIONS__</select></div>
      <div><label for="minutes">__MINUTES__</label><select id="minutes">__MINUTE_OPTIONS__</select></div>
      <div><label for="sessions">__SESSIONS__</label><select id="sessions">__SESSION_OPTIONS__</select></div>
      <div><label for="horizon">__HORIZON__</label><select id="horizon">__HORIZON_OPTIONS__</select></div>
      <div><label for="mode">__MODE__</label><select id="mode">__MODE_OPTIONS__</select></div>
      <div><label for="goal">__GOAL__</label><select id="goal">__GOAL_OPTIONS__</select></div>
    </div>
    <button class="build one-line" type="submit">__MAKE__</button>
  </form>
  <section class="card result-card printable" id="result" hidden aria-live="polite">
    <div class="result-head"><div><p class="eyebrow">__RESULT_TITLE__</p><p>__RESULT_INTRO__</p></div></div>
    <div class="metric-grid">
      <div class="metric"><strong id="weekly-time"></strong><span>__WEEKLY_TIME__</span></div>
      <div class="metric"><strong id="new-ceiling"></strong><span>__NEW_CEILING__ · __NOT_TARGET__</span></div>
    </div>
    <h2 class="one-line">__SESSION_MIX__</h2>
    <div class="mix" id="mix"></div>
    <h2 class="one-line">__SEQUENCE__</h2>
    <div class="table-wrap"><table><thead><tr><th>__SESSION__</th><th>__FOCUS__</th></tr></thead><tbody id="schedule"></tbody></table></div>
    <ol class="checklist" id="steps"></ol>
    <p id="repeat-note"></p>
    <div class="actions no-print">
      <button class="ghost one-line" id="copy-plan" type="button">__COPY__</button>
      <button class="ghost one-line" id="share-plan" type="button">__SHARE__</button>
      <button class="ghost one-line" id="print-plan" type="button">__PRINT__</button>
    </div>
    <p class="status no-print" id="status" role="status"></p>
  </section>
</section>
<section class="wrap card wide research">
  <div><p class="eyebrow">__EVIDENCE_TITLE__</p><p>__EVIDENCE__</p><p><a href="__SPACING_SOURCE__">__SOURCE_ONE__</a><br><a href="__RETRIEVAL_SOURCE__">__SOURCE_TWO__</a></p></div>
  <div><p class="eyebrow">__PRIVACY_TITLE__</p><p>__PRIVACY_TEXT__</p><p><a href="__WEBMCP_SOURCE_URL__">__WEBMCP_SOURCE__</a></p></div>
</section>
__APP_CARD__
<section class="wrap card wide"><h2 class="one-line">__FAQ_TITLE__</h2>__FAQ_HTML__</section>
</main>
<footer><div class="wrap">__FOOTER__</div></footer>
<script>
const I18N=__JS_COPY__;
const WEBMCP_INPUT_SCHEMA=__WEBMCP_INPUT_SCHEMA__;
const WEBMCP_LANGUAGES=__WEBMCP_LANGUAGES__;
const WEBMCP_MODE_LABELS=__WEBMCP_MODE_LABELS__;
const WEBMCP_GOAL_LABELS=__WEBMCP_GOAL_LABELS__;
const WEBMCP_TOOL_DESCRIPTION=__WEBMCP_DESCRIPTION__;
const WORDMATE_APP_STORE_URL=__APP_STORE_URL__;
const form=document.getElementById("planner");
const result=document.getElementById("result");
const statusNode=document.getElementById("status");
let plainPlan="";
function escapeHTML(value){return String(value).replace(/[&<>"']/g,ch=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[ch]));}
function selectedText(id){const node=document.getElementById(id);return node.options[node.selectedIndex].text;}
function weightsFor(mode){if(mode==="starter")return [30,45,25,.45];if(mode==="review")return [55,20,25,.32];return [45,30,25,.58];}
function toolValue(input,name){
  if(!Object.prototype.hasOwnProperty.call(input,name))throw new TypeError(`${name} is required.`);
  const value=input[name];
  if(!WEBMCP_INPUT_SCHEMA.properties[name].enum.includes(value))throw new RangeError(`${name} is not a supported value.`);
  return value;
}
async function registerWebMcp(){
  if(!document.modelContext?.registerTool)return;
  await document.modelContext.registerTool({
    name:"build_private_vocabulary_habit_plan",
    description:WEBMCP_TOOL_DESCRIPTION,
    inputSchema:WEBMCP_INPUT_SCHEMA,
    annotations:{readOnlyHint:true,untrustedContentHint:false},
    execute:async(input)=>{
      if(input===null||typeof input!=="object"||Array.isArray(input))throw new TypeError("WebMCP input must be an object.");
      const allowed=new Set(Object.keys(WEBMCP_INPUT_SCHEMA.properties));
      for(const name of Object.keys(input))if(!allowed.has(name))throw new RangeError(`${name} is not a supported input.`);
      const languageCode=toolValue(input,"language_code");
      const minutes=toolValue(input,"minutes_per_session");
      const sessions=toolValue(input,"sessions_per_week");
      const horizon=toolValue(input,"horizon_weeks");
      const mode=toolValue(input,"study_mode");
      const goal=toolValue(input,"primary_goal");
      const language=WEBMCP_LANGUAGES.find(item=>item.code===languageCode);
      const [retrieve,context,correct,factor]=weightsFor(mode);
      const ceiling=Math.max(2,Math.min(24,Math.round(minutes*factor)));
      return JSON.stringify({
        result_type:"private_vocabulary_habit_plan",
        language_code:languageCode,
        language_name:language.name,
        study_mode:mode,
        study_mode_label:WEBMCP_MODE_LABELS[mode],
        primary_goal:goal,
        primary_goal_label:WEBMCP_GOAL_LABELS[goal],
        weekly_practice_minutes:minutes*sessions,
        sessions_per_week:sessions,
        horizon_weeks:horizon,
        starting_new_card_ceiling_per_session:ceiling,
        ceiling_boundary:I18N.not_target,
        session_mix_percent:{
          closed_book_retrieval:retrieve,
          new_words_in_context:context,
          correction_and_spoken_replay:correct
        },
        weekly_sequence:Array.from({length:sessions},(_,index)=>({
          session:index+1,
          focus:I18N.roles[Math.min(index,I18N.roles.length-1)]
        })),
        practice_steps:I18N.steps,
        repeat_note:I18N.repeat_note,
        privacy_boundary:I18N.privacy_text,
        evidence_sources:["__SPACING_SOURCE__","__RETRIEVAL_SOURCE__"],
        wordmate_app_store_url:WORDMATE_APP_STORE_URL||null
      });
    }
  });
}
function buildPlan(event){
  if(event)event.preventDefault();
  const language=selectedText("language");
  const minutes=Number(document.getElementById("minutes").value);
  const sessions=Number(document.getElementById("sessions").value);
  const horizon=Number(document.getElementById("horizon").value);
  const mode=document.getElementById("mode").value;
  const goal=selectedText("goal");
  const [retrieve,context,correct,factor]=weightsFor(mode);
  const ceiling=Math.max(2,Math.min(24,Math.round(minutes*factor)));
  document.getElementById("weekly-time").textContent=`${minutes*sessions} ${I18N.minutes_unit}`;
  document.getElementById("new-ceiling").textContent=`${ceiling} ${I18N.per_session}`;
  const mixData=[[I18N.retrieve,retrieve],[I18N.context,context],[I18N.correct,correct]];
  document.getElementById("mix").innerHTML=mixData.map(([label,value])=>`<div class="mix-row"><span>${escapeHTML(label)}</span><span class="bar"><i style="width:${value}%"></i></span><strong>${value}%</strong></div>`).join("");
  const rows=[];
  for(let index=0;index<sessions;index++){
    const role=I18N.roles[Math.min(index,I18N.roles.length-1)];
    rows.push(`<tr><td>${escapeHTML(I18N.session)} ${index+1}</td><td>${escapeHTML(role)}</td></tr>`);
  }
  document.getElementById("schedule").innerHTML=rows.join("");
  document.getElementById("steps").innerHTML=I18N.steps.map(step=>`<li>${escapeHTML(step)}</li>`).join("");
  document.getElementById("repeat-note").textContent=`${horizon} ${I18N.weeks_unit} · ${I18N.repeat_note}`;
  plainPlan=[
    `${language} · ${goal}`,
    `${I18N.weekly_time}: ${minutes*sessions} ${I18N.minutes_unit} (${sessions} ${I18N.sessions_unit})`,
    `${I18N.new_ceiling}: ${ceiling} ${I18N.per_session} — ${I18N.not_target}`,
    `${I18N.session_mix}: ${I18N.retrieve} ${retrieve}% · ${I18N.context} ${context}% · ${I18N.correct} ${correct}%`,
    ...Array.from({length:sessions},(_,index)=>`${I18N.session} ${index+1}: ${I18N.roles[Math.min(index,I18N.roles.length-1)]}`),
    ...I18N.steps.map((step,index)=>`${index+1}. ${step}`),
    `${horizon} ${I18N.weeks_unit} · ${I18N.repeat_note}`,
    "__CANONICAL__"
  ].join("\n");
  result.hidden=false;
  statusNode.textContent="";
}
async function copyPlan(){
  try{await navigator.clipboard.writeText(plainPlan);statusNode.textContent=I18N.copied;}
  catch(error){statusNode.textContent=I18N.copy_failed;}
}
async function sharePlan(){
  if(navigator.share){
    try{await navigator.share({title:document.title,text:plainPlan,url:"__CANONICAL__"});return;}
    catch(error){if(error&&error.name==="AbortError"){statusNode.textContent=I18N.share_cancelled;return;}}
  }
  await copyPlan();
}
form.addEventListener("submit",buildPlan);
document.getElementById("copy-plan").addEventListener("click",copyPlan);
document.getElementById("share-plan").addEventListener("click",sharePlan);
document.getElementById("print-plan").addEventListener("click",()=>window.print());
buildPlan();
registerWebMcp().catch(error=>console.error("WebMCP tool registration failed.",error));
</script>
</body>
</html>
"""
    replacements = {
        "__HTML_LANG__": esc(copy["html_lang"]),
        "__TITLE__": esc(copy["title"]),
        "__DESCRIPTION__": esc(copy["description"]),
        "__CANONICAL__": canonical(locale),
        "__ALTERNATE_LINKS__": alternate_links,
        "__FEEDS__": feed_discovery_links(),
        "__HEADING__": esc(copy["heading"]),
        "__SCHEMA__": schema(locale, copy),
        "__HOME__": esc(copy["home"]),
        "__TOOLS__": esc(copy["tools"]),
        "__TOOLS_LABEL__": esc(copy["tools_label"]),
        "__SWITCH_HREF__": esc(copy["switch_href"]),
        "__SWITCH__": esc(copy["switch"]),
        "__EYEBROW__": esc(copy["eyebrow"]),
        "__LEAD__": esc(copy["lead"]),
        "__PRIVACY__": esc(copy["privacy"]),
        "__SCOPE__": esc(copy["scope"]),
        "__BUILDER__": esc(copy["builder"]),
        "__LANGUAGE__": esc(copy["language"]),
        "__MINUTES__": esc(copy["minutes"]),
        "__SESSIONS__": esc(copy["sessions"]),
        "__HORIZON__": esc(copy["horizon"]),
        "__MODE__": esc(copy["mode"]),
        "__GOAL__": esc(copy["goal"]),
        "__MAKE__": esc(copy["make"]),
        "__LANGUAGE_OPTIONS__": language_options(locale),
        "__MINUTE_OPTIONS__": select_options(
            [5, 10, 15, 20, 30, 45], copy["minutes_unit"], 15
        ),
        "__SESSION_OPTIONS__": select_options(
            [2, 3, 4, 5, 6, 7], copy["sessions_unit"], 4
        ),
        "__HORIZON_OPTIONS__": select_options(
            [2, 4, 8, 12], copy["weeks_unit"], 4
        ),
        "__MODE_OPTIONS__": mode_options,
        "__GOAL_OPTIONS__": goal_options,
        "__RESULT_TITLE__": esc(copy["result_title"]),
        "__RESULT_INTRO__": esc(copy["result_intro"]),
        "__WEEKLY_TIME__": esc(copy["weekly_time"]),
        "__NEW_CEILING__": esc(copy["new_ceiling"]),
        "__NOT_TARGET__": esc(copy["not_target"]),
        "__SESSION_MIX__": esc(copy["session_mix"]),
        "__SEQUENCE__": esc(copy["sequence"]),
        "__SESSION__": esc(copy["session"]),
        "__FOCUS__": esc(copy["focus"]),
        "__COPY__": esc(copy["copy"]),
        "__SHARE__": esc(copy["share"]),
        "__PRINT__": esc(copy["print"]),
        "__EVIDENCE_TITLE__": esc(copy["evidence_title"]),
        "__EVIDENCE__": esc(copy["evidence"]),
        "__SPACING_SOURCE__": SPACING_SOURCE,
        "__RETRIEVAL_SOURCE__": RETRIEVAL_SOURCE,
        "__SOURCE_ONE__": esc(copy["source_one"]),
        "__SOURCE_TWO__": esc(copy["source_two"]),
        "__WEBMCP_SOURCE_URL__": WEBMCP_SOURCE,
        "__WEBMCP_SOURCE__": esc(copy["webmcp_source"]),
        "__PRIVACY_TITLE__": esc(copy["privacy_title"]),
        "__PRIVACY_TEXT__": esc(copy["privacy_text"]),
        "__APP_CARD__": app_card,
        "__FAQ_TITLE__": esc(copy["faq_title"]),
        "__FAQ_HTML__": faq_html,
        "__FOOTER__": esc(copy["footer"]),
        "__JS_COPY__": json.dumps(js_copy, ensure_ascii=False, separators=(",", ":")),
        "__WEBMCP_INPUT_SCHEMA__": json.dumps(
            webmcp_input_schema(locale),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        "__WEBMCP_LANGUAGES__": json.dumps(
            webmcp_languages(locale),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        "__WEBMCP_MODE_LABELS__": json.dumps(
            copy["mode_options"],
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        "__WEBMCP_GOAL_LABELS__": json.dumps(
            copy["goal_options"],
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        "__WEBMCP_DESCRIPTION__": json.dumps(
            copy["webmcp_description"],
            ensure_ascii=False,
        ),
        "__APP_STORE_URL__": json.dumps(tracked_app_url),
    }
    for marker, value in replacements.items():
        page = page.replace(marker, value)
    unresolved = sorted(set(re.findall(r"__[A-Z][A-Z_]+__", page)))
    if unresolved:
        raise ValueError(f"Unresolved template markers: {unresolved}")
    return page


def write_text_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _index_card(locale: str) -> str:
    copy = COPY[locale]
    return (
        f'<article class="card third" data-tool="{SLUG}">'
        f'<h2><a href="{SLUG}.html">{html.escape(copy["index_title"])}</a></h2>'
        f'<p>{html.escape(copy["index_description"])}</p></article>'
    )


def _update_one_index(path: Path, locale: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    card = _index_card(locale)
    pattern = re.compile(
        rf'<article class="card third"(?: data-tool="{re.escape(SLUG)}")?>'
        rf'<h2><a href="{re.escape(SLUG)}\.html">.*?</article>',
        re.S,
    )
    if pattern.search(text):
        updated = pattern.sub(card, text, count=1)
    else:
        marker = '<section class="wrap grid">'
        if marker not in text:
            raise RuntimeError(f"{path} is missing its tools grid")
        updated = text.replace(marker, marker + card, 1)
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def update_tools_indexes(pages: Path = PAGES) -> int:
    return sum(
        int(
            _update_one_index(
                pages
                / ("tools" if locale == "en" else f"{locale}/tools")
                / "index.html",
                locale,
            )
        )
        for locale in ALT_LOCALES
    )


def insert_answer_links(pages: Path = PAGES) -> int:
    changed = 0
    for slug in TARGET_ANSWER_SLUGS:
        for locale in ALT_LOCALES:
            directory = (
                pages / "answers" if locale == "en" else pages / locale / "answers"
            )
            path = directory / slug
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            if INBOUND_LINK_CLASS in text:
                continue
            match = _APP_STORE_ANCHOR.search(text)
            if not match:
                continue
            link = (
                f'<a class="cta ghost {INBOUND_LINK_CLASS}" '
                f'data-vocabulary-habit-planner-link="1" href="{canonical(locale)}" '
                f'rel="noopener">{html.escape(COPY[locale]["inline_link"])}</a> '
            )
            if write_text_if_changed(
                path,
                text[: match.start()] + link + text[match.start() :],
            ):
                changed += 1
    return changed


def build(pages: Path = PAGES, *, show_app_cta: bool = False) -> list[str]:
    outputs = []
    for locale in ALT_LOCALES:
        relative = Path("tools") / f"{SLUG}.html"
        if locale != "en":
            relative = Path(locale) / relative
        write_text_if_changed(
            pages / relative,
            render_page(locale, show_app_cta=show_app_cta),
        )
        outputs.append(canonical(locale))
    update_tools_indexes(pages)
    insert_answer_links(pages)
    return outputs


def main() -> None:
    show_app_cta = APP_KEY in live_app_keys(
        APPSTORE,
        str(PAGES),
        refresh=False,
    )
    for output in build(show_app_cta=show_app_cta):
        print(f"vocabulary habit planner -> {output}")
    print(f"tools sitemap -> {write_tools_sitemap()} urls")


if __name__ == "__main__":
    main()
