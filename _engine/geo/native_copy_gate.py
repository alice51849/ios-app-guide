#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""外宣文案的母語品質閘門(Indic 優先,邏輯與語言無關)。

這個模組是 `geo/` 與 `threads-autopilot/` 共用的**單一事實來源**:兩邊的
gate/測試都必須引用同一份規則,任何一邊被改動而另一邊沒同步,checksum 測試
就會失敗。

它檢查四件在 2026-09-11 的 47 App × 10 Indic locale 稽核裡實際造成 FAIL 的事:

1. `script_ratio` —— 價值訴求是不是真的用當地文字寫的(整段英文 fallback)。
2. `shaping_defects` —— 機器翻譯把英文字塞進 Indic 詞中間、孤兒 matra、
   跨 script 混排、dotted circle。
3. `purchase_model_defects` —— paid_upfront 的 App 不可寫「免費試用」;
   freemium 不可完全沒有免費訊號。
4. `price_literal_defects` —— 文案不可寫死 ₹599 這類幣別金額(價格會變、
   各 storefront 不同)。

**刻意不判為錯誤**(這些在稽核時被逐一反證過,誤改會破壞正確的正字法):
* 字尾 virama/halant(`ಸ್ಕ್ಯಾನ್`、`ୱିଜେଟ୍` 這類借詞轉寫是對的)。
* U+0964/U+0965 danda —— Unicode 只編在 Devanagari block,孟加拉/歐里亞/
  旁遮普共用,不算跨 script 混排。
* `स्क्रीन-फ्री`、`ad-free` 這種以連字號結尾的「-free」複合詞,不是價格訴求。
* `iOS`、`App Store`、`TOEIC`、`Zhuyin` 等產品專有名詞以拉丁字呈現。
"""
from __future__ import annotations

import re
import unicodedata

# locale -> (script 名稱, 起, 迄, virama)
INDIC_SCRIPTS = {
    "bn-BD": ("Bengali", 0x0980, 0x09FF, 0x09CD),
    "gu-IN": ("Gujarati", 0x0A80, 0x0AFF, 0x0ACD),
    "hi": ("Devanagari", 0x0900, 0x097F, 0x094D),
    "kn-IN": ("Kannada", 0x0C80, 0x0CFF, 0x0CCD),
    "ml-IN": ("Malayalam", 0x0D00, 0x0D7F, 0x0D4D),
    "mr-IN": ("Devanagari", 0x0900, 0x097F, 0x094D),
    "or-IN": ("Oriya", 0x0B00, 0x0B7F, 0x0B4D),
    "pa-IN": ("Gurmukhi", 0x0A00, 0x0A7F, 0x0A4D),
    "ta-IN": ("Tamil", 0x0B80, 0x0BFF, 0x0BCD),
    "te-IN": ("Telugu", 0x0C00, 0x0C7F, 0x0C4D),
}
INDIC_LOCALES = tuple(INDIC_SCRIPTS)

# danda / double danda / 縮寫號:Unicode 只編在 Devanagari,其他 Indic script 共用。
SHARED_PUNCTUATION = frozenset({0x0964, 0x0965, 0x0970, 0x0971})
DOTTED_CIRCLE = "\u25CC"
REPLACEMENT_CHARS = ("\ufffd", "\u25a1")

# 母語文案裡「本來就該是拉丁字」的產品/平台詞彙。只要落在這份名單就不算
# 機器翻譯殘留;名單之外的英文單字若卡在 Indic 詞中間,就是壞 token。
LATIN_PRODUCT_TERMS = frozenset(
    term.casefold()
    for term in (
        "iOS", "iPhone", "iPad", "iPadOS", "macOS", "watchOS", "visionOS",
        "Apple", "App", "Store", "AppStore", "iCloud", "Siri", "Face", "ID",
        "Touch", "Widget", "Widgets", "Live", "Photos", "Files", "Shortcuts",
        "AirDrop", "HomeKit", "CarPlay", "Safari", "Wi", "Fi", "WiFi",
        "Bluetooth", "QR", "PDF", "OCR", "AI", "HD", "RAW", "HEIC", "JPEG",
        "PNG", "GIF", "ZIP", "RAR", "CSV", "URL", "GPS", "USB", "SD", "NFC",
        "TOEIC", "ETS", "IELTS", "TOEFL", "ABC", "CV", "PPT", "PDFs",
        "Zhuyin", "Bopomofo", "Pinyin", "Mandarin", "Montessori",
        "Listening", "Reading", "Speaking", "Writing", "Pro", "Plus", "Lite",
        "Premium", "Lumi", "Aim990", "Mochi", "Sereno", "Zodira", "Snapport",
        "Unblurry", "PhotoCream", "Zipbox", "ScanTo", "PicClear", "CVDesk",
        "LockHour", "HoursTag", "DailyMate", "Wordmate", "TripBee",
        "SaveTag", "CalDaily", "GMoney", "Cyca", "Sono", "Note", "Planet",
        "Letters", "Math", "Mission", "Weather", "Trip", "Brief", "Pack",
    )
)


def base_language(locale: str) -> str:
    return str(locale or "").split("-")[0]


def _tokens(text: str) -> list[str]:
    return [token for token in re.split(r"\s+", text) if token]


def _strip_noise(text: str, brand: str = "") -> str:
    cleaned = re.sub(r"https?://\S+", " ", str(text or ""))
    cleaned = re.sub(r"#\S+", " ", cleaned)
    if brand:
        variants = {brand, brand.split(":")[0].strip()}
        for variant in sorted((v for v in variants if v), key=len, reverse=True):
            cleaned = cleaned.replace(variant, " ")
    return cleaned


def script_ratio(text: str, locale: str, brand: str = "") -> tuple[float, int, int]:
    """母語字母 / (母語字母 + 拉丁字母)。連結、hashtag 與品牌名不列入計算。

    品牌名是拉丁字是正確的(Apple 商店上就長那樣),把它算進分母會逼出
    錯誤的音譯;連結與 hashtag 同理。
    """
    if locale not in INDIC_SCRIPTS:
        raise KeyError(f"unsupported locale for script_ratio: {locale}")
    cleaned = _strip_noise(text, brand)
    _, low, high, _ = INDIC_SCRIPTS[locale]
    native = sum(1 for ch in cleaned if low <= ord(ch) <= high and ch.isalpha())
    latin = sum(1 for ch in cleaned if ch.isalpha() and ord(ch) < 0x250)
    total = native + latin
    return (native / total if total else 0.0), native, latin


def _is_native_letter(ch: str, low: int, high: int) -> bool:
    return low <= ord(ch) <= high and ch.isalpha()


def _combining(ch: str) -> bool:
    return unicodedata.category(ch) in {"Mn", "Mc", "Me"}


def _letters_in(token: str, low: int, high: int) -> list[str]:
    return [ch for ch in token if _is_native_letter(ch, low, high)]


# 這些語言裡真的存在的單字母詞。少了這份名單,`goals व खर्च`(馬拉地語的
# 「和」)會被誤判成機器翻譯殘留。
SINGLE_LETTER_WORDS = {
    "Devanagari": {"व", "न", "ऊ", "ए"},
    "Gujarati": {"જ", "ન", "ય"},
    "Bengali": {"ও", "এ"},
    "Gurmukhi": {"ਤ"},
    "Oriya": {"ଓ"},
}

TOKEN_TRIM = "().,:;!?\"'[]{}|/\u0964\u0965\u2022\u2013\u2014-"


def _fragment_kind(token: str, script: str, low: int, high: int, virama: int):
    """這個 token 是不是被切斷的詞素,而不是一個完整的詞。

    只保留**高精準**的三個訊號。刻意不把「字尾 virama」當缺陷:
    `ಸ್ಕ್ಯಾನ್`、`ୱିଜେଟ୍`、`உங்கள்` 都以 virama 結尾而且完全正確,
    2026-09-11 的稽核就是被這條規則誤報了 330 個 cell。
    """
    core = token.strip(TOKEN_TRIM)
    if not core or not any(_is_native_letter(ch, low, high) for ch in core):
        return None
    if _combining(core[0]):
        return "orphan_combining_mark"
    if len(core) == 2 and ord(core[1]) == virama:
        return "consonant_halant_only"
    if (
        len(core) == 1
        and not _is_independent_vowel(core[0], low)
        and core not in SINGLE_LETTER_WORDS.get(script, ())
    ):
        return "lone_consonant"
    return None


def _is_independent_vowel(ch: str, low: int) -> bool:
    """Indic block 的排列:獨立母音固定排在子音之前。"""
    offset = ord(ch) - low
    if low == 0x0B80:  # Tamil
        return offset <= 0x14
    return 0x04 <= offset <= 0x14


def latin_intrusions(text: str, locale: str) -> list[str]:
    """英文單字被塞進母語詞中間(機器翻譯殘留)。

    只有在「英文 token 兩側都是母語文字、且至少一側是被切斷的詞素」時才算數,
    所以 `ଏକ iOS ଆପ୍`(正確)與 `goals व खर्च`(合法的 code-switching)不會被
    誤判,`କ ads ଣସି`、`ଦ୍ SA ାରା`(壞掉)會被抓到。
    """
    script, low, high, virama = INDIC_SCRIPTS[locale]
    tokens = _tokens(_strip_noise(text))
    found = []
    for index, token in enumerate(tokens):
        core = token.strip(TOKEN_TRIM)
        if not core or not re.fullmatch(r"[A-Za-z]+", core):
            continue
        if core.casefold() in LATIN_PRODUCT_TERMS:
            continue
        left = tokens[index - 1] if index else ""
        right = tokens[index + 1] if index + 1 < len(tokens) else ""
        if not _letters_in(left, low, high) or not _letters_in(right, low, high):
            continue
        if _fragment_kind(left, script, low, high, virama) or _fragment_kind(
            right, script, low, high, virama
        ):
            found.append(f"{left} {core} {right}")
    return found


def fragment_defects(text: str, locale: str) -> list[str]:
    """文字裡出現不可能單獨存在的詞素(孤兒 matra、只有子音+halant)。"""
    script, low, high, virama = INDIC_SCRIPTS[locale]
    defects = []
    for token in _tokens(_strip_noise(text)):
        kind = _fragment_kind(token, script, low, high, virama)
        if kind in {"orphan_combining_mark", "consonant_halant_only"}:
            defects.append(f"{kind}:{token}")
    return defects


def shaping_defects(text: str, locale: str) -> list[str]:
    """會在真機上渲染成破字的缺陷。"""
    name, low, high, _virama = INDIC_SCRIPTS[locale]
    text = str(text or "")
    defects = []
    if DOTTED_CIRCLE in text:
        defects.append("dotted_circle")
    if any(ch in text for ch in REPLACEMENT_CHARS):
        defects.append("replacement_char")
    for other, (other_name, other_low, other_high, _v) in INDIC_SCRIPTS.items():
        if other_name == name:
            continue
        if any(
            other_low <= ord(ch) <= other_high
            and ord(ch) not in SHARED_PUNCTUATION
            for ch in text
        ):
            defects.append(f"foreign_script:{other_name}")
            break
    defects.extend(fragment_defects(text, locale))
    for intrusion in latin_intrusions(text, locale):
        defects.append(f"latin_inside_word:{intrusion}")
    return sorted(set(defects))


# 逐語「免費」與「訂閱」用字,以及否定詞。paid_upfront 的 App 寫「免費試用」
# 會直接違反 Guideline 2.1(b)/3.1.2,也讓買家點進去才發現要付錢。
FREE_WORDS = {
    "bn-BD": ("ফ্রি", "বিনামূল্যে"),
    "gu-IN": ("મફત", "ફ્રી"),
    "hi": ("मुफ़्त", "मुफ्त", "फ्री", "निःशुल्क"),
    "kn-IN": ("ಉಚಿತ", "ಫ್ರೀ"),
    "ml-IN": ("സൗജന്യ", "ഫ്രീ"),
    "mr-IN": ("मोफत", "फुकट", "फ्री"),
    "or-IN": ("ମାଗଣା", "ମୁକ୍ତ"),
    "pa-IN": ("ਮੁਫ਼ਤ", "ਮੁਫਤ"),
    "ta-IN": ("இலவச",),
    "te-IN": ("ఉచిత", "ఫ్రీ"),
}
ENGLISH_FREE_WORDS = ("free download", "free trial", "free to start", "try free")
SUBSCRIPTION_WORDS = {
    "bn-BD": ("সাবস্ক্রিপশন", "সদস্যতা"),
    "gu-IN": ("સબસ્ક્રિપ્શન",),
    "hi": ("सदस्यता", "सब्सक्रिप्शन", "सब्स्क्रिप्शन"),
    "kn-IN": ("ಸಬ್ಸ್ಕ್ರಿಪ್ಶನ್", "ಚಂದಾ"),
    "ml-IN": ("സബ്സ്ക്രിപ്ഷൻ", "വരിസംഖ്യ"),
    "mr-IN": ("सदस्यता", "सबस्क्रिप्शन", "वर्गणी"),
    "or-IN": ("ସବସ୍କ୍ରିପସନ", "ଚାନ୍ଦା"),
    "pa-IN": ("ਸਬਸਕ੍ਰਿਪਸ਼ਨ", "ਮੈਂਬਰਸ਼ਿਪ"),
    "ta-IN": ("சந்தா", "சப்ஸ்கிரிப்ஷன்"),
    "te-IN": ("సబ్‌స్క్రిప్షన్", "సబ్స్క్రిప్షన్", "చందా"),
}
NEGATION_MARKERS = (
    "नहीं", "बिना", "नाही", "নেই", "না", "ছাড়া", "இல்லை", "இன்றி", "ಇಲ್ಲ",
    "ഇല്ല", "ഇല്ലാതെ", "లేదు", "లేకుండా", "ਨਹੀਂ", "ਬਿਨਾਂ", "નથી", "વગર",
    "ନାହିଁ", "ବିନା", "no ", "without", "-free",
)
HYPHENS = "-\u2010\u2011\u2012\u2013\u2014"
PAID_UPFRONT_MODELS = frozenset({"paid_upfront", "paid"})
FREE_TO_START_MODELS = frozenset(
    {"free_with_lifetime_unlock", "freemium", "free_with_iap", "free"}
)


def free_claim_spans(text: str, locale: str) -> list[tuple[int, int, str]]:
    """真正在宣稱「免費」的位置(排除 `-free` 複合詞與被否定詞包住的用法)。"""
    text = str(text or "")
    words = list(FREE_WORDS.get(locale, ())) + list(ENGLISH_FREE_WORDS)
    spans = []
    for word in words:
        start = text.find(word)
        while start != -1:
            end = start + len(word)
            preceded_by_hyphen = start > 0 and text[start - 1] in HYPHENS
            window = text[max(0, start - 45): end + 45]
            negated = any(marker in window for marker in NEGATION_MARKERS)
            if not preceded_by_hyphen and not negated:
                spans.append((start, end, word))
            start = text.find(word, end)
    return sorted(spans)


def purchase_model_defects(
    text: str,
    locale: str,
    purchase_model: str,
    *,
    require_free_signal: bool = False,
) -> tuple[list[str], list[str]]:
    """付費模型與文案必須一致,買家看到的價格語意才不會是謊話。

    回傳 `(hard, soft)`。硬錯誤是「付費上架卻寫免費」——那是 Guideline
    2.1(b)/3.1.2 等級的問題;軟警告是「免費開始的 App 沒寫出免費訊號」,
    在只看單一欄位(例如描述,而定價句由 render 層另外加上)時本來就會發生,
    所以只有在檢查整個已組好的頁面/貼文時才把它打開。
    """
    text = str(text or "")
    hard, soft = [], []
    if purchase_model in PAID_UPFRONT_MODELS:
        for _start, _end, word in free_claim_spans(text, locale):
            hard.append(f"paid_upfront_implies_free:{word}")
        for word in SUBSCRIPTION_WORDS.get(locale, ()):
            index = text.find(word)
            while index != -1:
                window = text[max(0, index - 45): index + len(word) + 45]
                if not any(marker in window for marker in NEGATION_MARKERS):
                    soft.append(f"ambiguous_subscription_mention:{word}")
                    break
                index = text.find(word, index + len(word))
    elif purchase_model in FREE_TO_START_MODELS and require_free_signal:
        native_free = FREE_WORDS.get(locale, ())
        if not any(word in text for word in native_free):
            soft.append("free_to_start_without_free_signal")
    return sorted(set(hard)), sorted(set(soft))


# 幣別金額寫死在文案裡 = 只要 Apple 改價或換 storefront 就變成假資訊。
PRICE_LITERAL_RE = re.compile(
    r"(?:[₹$€£¥₩฿]|Rs\.?|INR|USD|EUR|GBP|JPY)\s?\d"
    r"|\d[\d,.]*\s?(?:₹|Rs\.?|INR|USD|EUR)",
    re.IGNORECASE,
)


def price_literal_defects(text: str) -> list[str]:
    return sorted({match.group(0).strip() for match in PRICE_LITERAL_RE.finditer(str(text or ""))})


NATIVE_RATIO_FLOOR = 0.70


def evaluate(
    text: str,
    locale: str,
    *,
    brand: str = "",
    purchase_model: str = "",
    ratio_floor: float = NATIVE_RATIO_FLOOR,
    require_free_signal: bool = False,
    check_price_literals: bool = False,
) -> dict:
    """一個 cell 的完整判定。回傳 dict 方便測試與報表共用。"""
    ratio, native, latin = script_ratio(text, locale, brand)
    failures = []
    warnings = []
    if ratio < ratio_floor:
        failures.append(f"latin_fallback(ratio={ratio:.2f})")
    failures.extend(shaping_defects(text, locale))
    if purchase_model:
        hard, soft = purchase_model_defects(
            text, locale, purchase_model, require_free_signal=require_free_signal
        )
        failures.extend(hard)
        warnings.extend(soft)
    if check_price_literals:
        # 產品描述本來就可能談到金額(HoursTag 會拿「$129 的鞋子」舉例),
        # 所以只有在檢查我們自己寫的文案包與定價句時才把它當錯誤。
        failures.extend(
            f"price_literal:{literal}" for literal in price_literal_defects(text)
        )
    return {
        "locale": locale,
        "ratio": round(ratio, 4),
        "native_letters": native,
        "latin_letters": latin,
        "failures": failures,
        "warnings": warnings,
        "ok": not failures,
    }
