"""Reject foreign-script contamination in each owned-feed locale."""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

from official_locales import OFFICIAL_LOCALES

NATIVE_SCRIPTS = {
    "ar-SA": {"ARABIC"}, "bn-BD": {"BENGALI"},
    "zh-Hans": {"CJK", "BOPOMOFO"}, "zh-Hant": {"CJK", "BOPOMOFO"},
    "el": {"GREEK"}, "gu-IN": {"GUJARATI"}, "he": {"HEBREW"},
    "hi": {"DEVANAGARI"}, "ja": {"CJK", "HIRAGANA", "KATAKANA"},
    "kn-IN": {"KANNADA"}, "ko": {"HANGUL"}, "ml-IN": {"MALAYALAM"},
    "mr-IN": {"DEVANAGARI"}, "or-IN": {"ORIYA"}, "pa-IN": {"GURMUKHI"},
    "ru": {"CYRILLIC"}, "ta-IN": {"TAMIL"}, "te-IN": {"TELUGU"},
    "th": {"THAI"}, "uk": {"CYRILLIC"}, "ur-PK": {"ARABIC"},
}
SCRIPTS = {
    locale: frozenset(NATIVE_SCRIPTS.get(locale, {"LATIN"}))
    for locale in OFFICIAL_LOCALES
}
KNOWN_SCRIPTS = frozenset().union(*SCRIPTS.values(), {"LATIN"})
PRICE = re.compile(
    r"[$€£¥￥₹₩₽₺₫₱৳₪฿₴]\s*\d|"
    r"\d[\d.,]*\s*[$€£¥￥₹₩₽₺₫₱৳₪฿₴]|"
    r"\b\d[\d.,]*\s*(?:USD|EUR|GBP|CAD|AUD|INR|BDT|TWD|JPY|CNY|HKD|"
    r"KRW|SGD|MYR|THB|VND|IDR|PHP|PKR|CHF|SEK|NOK|DKK|PLN|CZK|"
    r"HUF|RON|RUB|UAH|TRY|BRL|MXN|ILS|SAR|AED|TL|kr|zł|Kč|Ft)\b",
    re.I,
)
FREE_TERMS = {
    "ar": r"مجاني|مجانًا", "bn": r"বিনামূল্য|বিনা মূল্যে",
    "ca": r"\bgratuït", "cs": r"\bzdarma\b", "da": r"\bgratis\b",
    "de": r"\bkostenlos", "el": r"δωρεάν",
    "en": r"(?<![\w-])free(?![\w-])", "es": r"\bgratis\b|\bgratuit",
    "fi": r"\bilmais|\bilmainen\b", "fr": r"\bgratuit",
    "gu": r"મફત", "he": r"חינם", "hi": r"मुफ़्त|मुफ्त|निःशुल्क",
    "hr": r"\bbesplat", "hu": r"\bingyen", "id": r"\bgratis\b",
    "it": r"\bgratis\b|\bgratuit", "ja": r"無料", "kn": r"ಉಚಿತ",
    "ko": r"무료", "ml": r"സൗജന്യ", "mr": r"मोफत", "ms": r"\bpercuma\b",
    "nl": r"\bgratis\b", "no": r"\bgratis\b", "or": r"ମାଗଣା",
    "pa": r"ਮੁਫ਼ਤ|ਮੁਫਤ", "pl": r"\bbezpłat|\bdarmo\b",
    "pt": r"\bgrátis\b|\bgratuit", "ro": r"\bgratuit", "ru": r"бесплатн",
    "sk": r"\bzadarmo\b|\bbezplat", "sl": r"\bbrezplač",
    "sv": r"\bgratis\b|\bkostnadsfri", "ta": r"இலவச", "te": r"ఉచిత",
    "th": r"ฟรี", "tr": r"\bücretsiz", "uk": r"безкоштовн",
    "ur": r"مفت", "vi": r"miễn phí", "zh": r"免費|免费",
}


@lru_cache(maxsize=16384)
def script(character: str) -> str | None:
    if not character.isalpha():
        return None
    name = unicodedata.name(character, "")
    for value in sorted(KNOWN_SCRIPTS):
        if value in name:
            return value
    if name.startswith(("MODIFIER LETTER", "MATHEMATICAL", "LETTERLIKE")):
        return None
    return "UNKNOWN"


def validate_text(locale: str, value: str, field: str, *,
                  require_native: bool = True) -> None:
    if locale not in SCRIPTS:
        raise ValueError(f"Unsupported feed locale: {locale}")
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Empty localized text: {locale}/{field}")
    native = SCRIPTS[locale]
    observed = {s for c in value if (s := script(c)) is not None}
    foreign = observed - native - {"LATIN"}
    if foreign:
        raise ValueError(f"Cross-script contamination: {locale}/{field}: {sorted(foreign)}")
    if require_native and not observed.intersection(native):
        raise ValueError(f"Missing native script: {locale}/{field}")
    if PRICE.search(value):
        raise ValueError(f"Literal price in owned copy: {locale}/{field}")
    if any(
        (ord(c) < 32 and c not in "\t\n\r")
        or 0xD800 <= ord(c) <= 0xDFFF or ord(c) in (0xFFFE, 0xFFFF)
        for c in value
    ):
        raise ValueError(f"Invalid XML character: {locale}/{field}")


def validate_summary(locale: str, value: str, model: str) -> None:
    validate_text(locale, value, "summary")
    if model == "paid_upfront" and re.search(
        FREE_TERMS[locale.split("-")[0]], value, re.I
    ):
        raise ValueError(f"Free claim on paid download: {locale}")
