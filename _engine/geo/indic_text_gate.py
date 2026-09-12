"""Read-only script and paid-copy checks; never rewrites Indic code points."""
from __future__ import annotations

import re
import unicodedata

SCRIPT_RANGES = {
    "bn-BD": (0x0980, 0x09FF), "gu-IN": (0x0A80, 0x0AFF),
    "hi": (0x0900, 0x097F), "kn-IN": (0x0C80, 0x0CFF),
    "ml-IN": (0x0D00, 0x0D7F), "mr-IN": (0x0900, 0x097F),
    "or-IN": (0x0B00, 0x0B7F), "pa-IN": (0x0A00, 0x0A7F),
    "ta-IN": (0x0B80, 0x0BFF), "te-IN": (0x0C00, 0x0C7F),
}
TECHNICAL = (
    "Trip Planet: Kids Quest", "Lumi Mission Planet Pro", "Lumi Bopomofo Pro",
    "Lumi Letters Pro", "Lumi Math Pro", "AI Brief Pack", "Lumi Studio",
    "Lumi Bopomofo", "Lumi Letters", "PicClear Pro", "LockHour Pro",
    "TAR.GZIP", "TAR.BZIP2", "TAR.XZ", "Face ID", "App Store",
    "Aim990", "PicClear", "ScanTo", "Zipbox", "Hourstag", "LockHour",
    "TOEIC", "ETS", "Zhuyin", "Bopomofo", "Montessori", "Pomodoro",
    "iCloud", "iPhone", "iPad", "Safari", "Apple", "Lumi",
    "RAR5", "BZIP2", "GZIP", "LZMA", "LZ4", "ISO", "ZIP", "RAR",
    "TAR", "XZ", "AES", "PDF", "OCR", "WMI", "ABC", "GB", "AI", "Pro", "Plus", "Lite",
)
TECHNICAL_RE = re.compile(
    r"(?<![A-Za-z])(?:" + "|".join(map(re.escape, sorted(TECHNICAL, key=len, reverse=True))) + r")(?![A-Za-z])",
    re.I,
)
ENGLISH_FALLBACK = re.compile(
    r"Pro edition (?:unlocks|includes)|Full Pro edition|Unlock your potential|"
    r"Master Your TOEIC|ABC phonics, letter sounds and tracing for ages",
    re.I,
)
PAID_TRIAL_CLAIMS = {
    "bn-BD": ("বিনামূল্যে চেষ্টা করুন", "ফ্রি ট্রায়াল শুরু"),
    "gu-IN": ("મફત અજમાવો", "મફતમાં અજમાવો"),
    "hi": ("मुफ़्त आज़माएँ", "मुफ्त आजमाएँ", "मुफ्त आज़माएं"),
    "kn-IN": ("ಉಚಿತವಾಗಿ ಪ್ರಯತ್ನಿಸಿ",),
    "ml-IN": ("സൗജന്യമായി പരീക്ഷിക്കുക",),
    "mr-IN": ("मोफत वापरून पहा",),
    "or-IN": ("ମାଗଣାରେ ଚେଷ୍ଟା କରନ୍ତୁ",),
    "pa-IN": ("ਮੁਫ਼ਤ ਅਜ਼ਮਾਓ",),
    "ta-IN": ("இலவசமாக முயற்சிக்கவும்",),
    "te-IN": ("ఉచితంగా ప్రయత్నించండి",),
}


def native_ratio(text: str, locale: str) -> float:
    low, high = SCRIPT_RANGES[locale]
    letters = [char for char in TECHNICAL_RE.sub("", text) if char.isalpha()]
    return sum(low <= ord(char) <= high for char in letters) / max(1, len(letters))


def foreign_letters(text: str, locale: str) -> set[str]:
    low, high = SCRIPT_RANGES[locale]
    return {
        char for char in text
        if not low <= ord(char) <= high and (
            char.isalpha() and "LATIN" not in unicodedata.name(char, "")
            or unicodedata.category(char).startswith("M")
            and any(start <= ord(char) <= end for start, end in SCRIPT_RANGES.values())
        )
    }


def shaping_issues(text: str, locale: str) -> list[str]:
    low, high = SCRIPT_RANGES[locale]
    issues = []
    has_base = False
    for char in text:
        if char in "\ufffd\u25cc":
            issues.append("replacement_or_dotted_circle")
        category = unicodedata.category(char)
        if low <= ord(char) <= high and category.startswith("M"):
            if not has_base:
                issues.append("orphan_combining_mark")
        elif category.startswith(("L", "N")):
            has_base = True
        elif char not in "\u200c\u200d":
            has_base = False
    return issues


def validate(text: str, locale: str, *, purchase_model=None, minimum_ratio=None):
    if locale not in SCRIPT_RANGES or not isinstance(text, str) or not text.strip():
        raise ValueError("Indic content requires an explicit supported locale and nonempty text")
    if foreign_letters(text, locale):
        raise ValueError(f"Cross-script Indic contamination: {locale}")
    if shaping_issues(text, locale):
        raise ValueError(f"Invalid Indic combining-mark sequence: {locale}")
    if ENGLISH_FALLBACK.search(text):
        raise ValueError(f"English fallback in Indic content: {locale}")
    if purchase_model == "paid_upfront" and any(value in text for value in PAID_TRIAL_CLAIMS[locale]):
        raise ValueError(f"Paid-upfront app advertised as free trial: {locale}")
    if minimum_ratio is not None and native_ratio(text, locale) < minimum_ratio:
        raise ValueError(f"Insufficient native script ratio: {locale}")
