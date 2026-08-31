#!/usr/bin/env python3
"""Localize AEO/GEO answer pages without touching git."""

from __future__ import annotations

import argparse
import functools
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit
from pathlib import Path
from typing import Any

from official_locales import OFFICIAL_LOCALES


ROOT = Path(
    os.environ.get(
        "GEO_PAGES",
        Path(__file__).resolve().parent / "pages",
    )
).resolve()
ANSWERS = ROOT / "answers"
BASE_URL = "https://alice51849.github.io/ios-app-guide"
OLLAMA_ENDPOINT = os.environ.get(
    "OLLAMA_ENDPOINT", "http://127.0.0.1:11434/api/chat"
)
OLLAMA_MODEL = os.environ.get("OLLAMA_TRANSLATION_MODEL", "qwen3.5:4b")
GITHUB_MODELS_ENDPOINT = (
    "https://models.github.ai/inference/chat/completions"
)
GITHUB_TRANSLATION_MODEL = os.environ.get(
    "GITHUB_TRANSLATION_MODEL", "openai/gpt-4.1"
)
ALL_LANGS = list(OFFICIAL_LOCALES)
ENGLISH_LOCALES = frozenset({"en-AU", "en-CA", "en-GB", "en-US"})
HREFLANG_ORDER = ["en"] + [lc for lc in ALL_LANGS] + ["x-default"]
BASE_LANG = {
    "en-AU": "en-AU", "en-CA": "en-CA", "en-GB": "en-GB", "en-US": "en-US",
    "de-DE": "de-DE", "es-ES": "es-ES", "fr-FR": "fr-FR", "ja": "ja", "ko": "ko",
    "fr-CA": "fr-CA",
    "pt-BR": "pt-BR", "zh-Hans": "zh-Hans", "zh-Hant": "zh-Hant", "it": "it", "ru": "ru",
    "tr": "tr", "id": "id", "vi": "vi", "th": "th", "ar-SA": "ar", "hi": "hi", "nl-NL": "nl",
    "pl": "pl", "sv": "sv", "uk": "uk", "ca": "ca", "hr": "hr", "cs": "cs", "da": "da",
    "fi": "fi", "el": "el", "he": "he", "hu": "hu", "ms": "ms", "no": "no", "pt-PT": "pt-PT",
    "ro": "ro", "sk": "sk", "es-MX": "es-MX", "bn-BD": "bn", "gu-IN": "gu", "kn-IN": "kn",
    "ml-IN": "ml", "mr-IN": "mr", "or-IN": "or", "pa-IN": "pa", "sl-SI": "sl", "ta-IN": "ta",
    "te-IN": "te", "ur-PK": "ur",
}
LANG_NAMES = {
    "en-AU": "Australian English", "en-CA": "Canadian English",
    "en-GB": "British English", "en-US": "US English",
    "de-DE": "German for Germany", "es-ES": "Spanish for Spain", "fr-FR": "French for France",
    "fr-CA": "Canadian French",
    "ja": "Japanese", "ko": "Korean", "pt-BR": "Brazilian Portuguese", "zh-Hans": "Simplified Chinese",
    "zh-Hant": "Traditional Chinese", "it": "Italian", "ru": "Russian", "tr": "Turkish",
    "id": "Indonesian", "vi": "Vietnamese", "th": "Thai", "ar-SA": "Arabic", "hi": "Hindi",
    "nl-NL": "Dutch", "pl": "Polish", "sv": "Swedish", "uk": "Ukrainian", "ca": "Catalan",
    "hr": "Croatian", "cs": "Czech", "da": "Danish", "fi": "Finnish", "el": "Greek",
    "he": "Hebrew", "hu": "Hungarian", "ms": "Malay", "no": "Norwegian", "pt-PT": "European Portuguese",
    "ro": "Romanian", "sk": "Slovak", "es-MX": "Mexican Spanish", "bn-BD": "Bengali",
    "gu-IN": "Gujarati", "kn-IN": "Kannada", "ml-IN": "Malayalam", "mr-IN": "Marathi",
    "or-IN": "Odia", "pa-IN": "Punjabi", "sl-SI": "Slovenian", "ta-IN": "Tamil",
    "te-IN": "Telugu", "ur-PK": "Urdu",
}
BRANDS = [
    "Lumi Studio",
    "Aim990",
    "TOEIC",
    "TOEIC L&R",
    "ETS",
    "App Store",
    "iPhone",
    "iPad",
    "iOS",
    "Apple Watch",
    "ScanTo Pro",
    "PhotoCream",
    "Lumi Mission Planet",
    "Lumi Mission Planet Pro",
    "Lumi Weather",
    "Lumi Letters Pro",
    "Lumi Math Pro",
    "Lumi Bopomofo Pro",
    "Lumi Trip Planet",
    "Wordmate",
    "DailyMate",
    "TripBee Lite",
]
NATIVE_SCRIPT_RANGES = {
    "ar-SA": ((0x0600, 0x06FF), (0x0750, 0x077F)),
    "ur-PK": ((0x0600, 0x06FF), (0x0750, 0x077F)),
    "bn-BD": ((0x0980, 0x09FF),),
    "el": ((0x0370, 0x03FF),),
    "he": ((0x0590, 0x05FF),),
    "hi": ((0x0900, 0x097F),),
    "mr-IN": ((0x0900, 0x097F),),
    "gu-IN": ((0x0A80, 0x0AFF),),
    "kn-IN": ((0x0C80, 0x0CFF),),
    "ml-IN": ((0x0D00, 0x0D7F),),
    "or-IN": ((0x0B00, 0x0B7F),),
    "pa-IN": ((0x0A00, 0x0A7F),),
    "ta-IN": ((0x0B80, 0x0BFF),),
    "te-IN": ((0x0C00, 0x0C7F),),
    "th": ((0x0E00, 0x0E7F),),
    "ru": ((0x0400, 0x052F),),
    "uk": ((0x0400, 0x052F),),
    "ja": ((0x3040, 0x30FF), (0x3400, 0x9FFF)),
    "ko": ((0xAC00, 0xD7AF),),
    "zh-Hans": ((0x3400, 0x9FFF),),
    "zh-Hant": ((0x3400, 0x9FFF),),
}
LOCALE_TEXT_OVERRIDES = {
    "ar-SA": {
        (
            "Travel creators need a repeatable film look that adds grain, "
            "halation and colour character without reducing every destination "
            "to the same flat… — PhotoCream."
        ): (
            "صناع السفر يحتاجون مظهر أفلام قابل للتكرار يضيف الحبيبات والتوهج "
            "وطابع اللون دون تحويل كل وجهة إلى نفس الفلتر المسطح… — PhotoCream."
        ),
        (
            "Travel creators need a repeatable film look that adds grain, "
            "halation and colour character without reducing every destination "
            "to the same flat filter — PhotoCream is built for this."
        ): (
            "صناع السفر يحتاجون مظهر أفلام قابل للتكرار يضيف الحبيبات والتوهج "
            "وطابع اللون دون تحويل كل وجهة إلى نفس الفلتر المسطح — PhotoCream "
            "مصمم لهذا."
        ),
        (
            "Parents planning outdoor time need more than a temperature: they "
            "need a quick, age-aware view of whether conditions suit a child "
            "and what… — Lumi Weather."
        ): (
            "الآباء الذين يخططون وقت الخارج يحتاجون أكثر من درجة الحرارة: "
            "يحتاجون نظرة سريعة حسب العمر لمعرفة إذا كانت الظروف مناسبة للطفل "
            "وما… — Lumi Weather."
        ),
        (
            "Parents planning outdoor time need more than a temperature: they "
            "need a quick, age-aware view of whether conditions suit a child "
            "and what clothing makes sense — Lumi Weather is built for this."
        ): (
            "الآباء الذين يخططون وقت الخارج يحتاجون أكثر من درجة الحرارة: "
            "يحتاجون نظرة سريعة حسب العمر لمعرفة إذا كانت الظروف مناسبة للطفل "
            "وما الملابس المناسبة — Lumi Weather مصمم لهذا."
        ),
        (
            "Parents travelling with young children need activities that turn "
            "packing, waiting and discovering a new place into part of the "
            "adventure… — Lumi Trip Planet."
        ): (
            "الآباء المسافرون مع أطفال صغار يحتاجون أنشطة تحول التجهيز، "
            "الانتظار واكتشاف مكان جديد إلى جزء من المغامرة… — Lumi Trip Planet."
        ),
        (
            "Parents travelling with young children need activities that turn "
            "packing, waiting and discovering a new place into part of the "
            "adventure instead of another source of stress — Lumi Trip Planet "
            "is built for this."
        ): (
            "الآباء المسافرون مع أطفال صغار يحتاجون أنشطة تحول التجهيز، "
            "الانتظار واكتشاف مكان جديد إلى جزء من المغامرة بدلاً من مصدر ضغط "
            "إضافي — Lumi Trip Planet مصمم لهذا."
        ),
    },
    "cs": {
        (
            "Travel creators need a repeatable film look that adds grain, "
            "halation and colour character without reducing every destination "
            "to the same flat… — PhotoCream."
        ): (
            "Tvůrci cestovatelského obsahu potřebují opakovatelný filmový vzhled, "
            "který přidává zrno, halaci a barevný charakter, aniž by každou "
            "destinaci sjednotil do stejného plochého… — PhotoCream."
        ),
        (
            "Travel creators need a repeatable film look that adds grain, "
            "halation and colour character without reducing every destination "
            "to the same flat filter — PhotoCream is built for this."
        ): (
            "Tvůrci cestovatelského obsahu potřebují opakovatelný filmový vzhled, "
            "který přidává zrno, halaci a barevný charakter, aniž by každou "
            "destinaci sjednotil do stejného plochého filtru — PhotoCream je pro "
            "toto vytvořen."
        ),
    },
    "de-DE": {
        (
            "best bedtime routine app for preschoolers with no ads"
        ): (
            "Beste Einschlafroutine-App für Vorschulkinder ohne Werbung"
        ),
        (
            "best bedtime routine app for preschoolers with no ads: "
            "honest iPhone app buying guide"
        ): (
            "Beste Einschlafroutine-App für Vorschulkinder ohne Werbung: "
            "ehrlicher iPhone-App-Kaufratgeber"
        ),
    },
    "kn-IN": {
        (
            "Travel creators need a repeatable film look that adds grain, "
            "halation and colour character without reducing every destination "
            "to the same flat filter — PhotoCream is built for this."
        ): (
            "ಪ್ರಯಾಣದ ವಿಷಯ ರಚಿಸುವವರಿಗೆ, ಪ್ರತಿಯೊಂದು ತಾಣವನ್ನೂ ಒಂದೇ ಸಪ್ಪೆ "
            "ಫಿಲ್ಟರ್‌ನಂತೆ ಮಾಡದೆ ಗ್ರೇನ್, ಹ್ಯಾಲೇಶನ್ ಮತ್ತು ವಿಶಿಷ್ಟ ಬಣ್ಣದ ಛಾಯೆ "
            "ನೀಡುವ, ಮತ್ತೆ ಮತ್ತೆ ಬಳಸಬಹುದಾದ ಫಿಲ್ಮ್ ಲುಕ್ ಬೇಕಾಗುತ್ತದೆ — "
            "PhotoCream ಇದಕ್ಕಾಗಿ ರೂಪಿಸಲಾಗಿದೆ."
        ),
        (
            "Bilingual children learning Zhuyin at home need a complete path "
            "through sounds, symbols, tones and blending, with enough playful "
            "repetition to make the system familiar — Lumi Bopomofo Pro is "
            "built for this."
        ): (
            "ಮನೆಯಲ್ಲಿ Zhuyin ಕಲಿಯುವ ದ್ವಿಭಾಷಾ ಮಕ್ಕಳಿಗೆ ಧ್ವನಿಗಳು, ಚಿಹ್ನೆಗಳು, "
            "ಸ್ವರಛಾಯೆಗಳು ಮತ್ತು ಧ್ವನಿಗಳನ್ನು ಜೋಡಿಸುವಿಕೆ ಒಳಗೊಂಡ ಸಂಪೂರ್ಣ ಕಲಿಕಾ "
            "ಮಾರ್ಗವೂ, ವ್ಯವಸ್ಥೆ ಪರಿಚಿತವಾಗಲು ಸಾಕಷ್ಟು ಆಟದ ಮರುಅಭ್ಯಾಸವೂ ಅಗತ್ಯ — "
            "Lumi Bopomofo Pro ಇದಕ್ಕಾಗಿ ರೂಪಿಸಲಾಗಿದೆ."
        ),
    },
    "ml-IN": {
        "TripBee Pro: Trip Planner": "TripBee Pro: യാത്രാ പ്ലാനർ",
        (
            "Travel creators need a repeatable film look that adds grain, "
            "halation and colour character without reducing every destination "
            "to the same flat filter — PhotoCream is built for this."
        ): (
            "യാത്രാ സൃഷ്ടാക്കൾക്ക് ആവർത്തിക്കാവുന്ന ഫിലിം ലുക്ക് ആവശ്യമാണ്; "
            "ഓരോ സ്ഥലത്തെയും ഒരേ ഫ്ലാറ്റ് ഫിൽട്ടറായി ചുരുക്കാതെ ഗ്രെയിൻ, "
            "ഹാലേഷൻ, നിറത്തിന്റെ സവിശേഷത എന്നിവ ചേർക്കണം — PhotoCream "
            "ഇതിനായി രൂപകൽപ്പന ചെയ്തിരിക്കുന്നു."
        ),
        (
            "Families preparing for kindergarten need a complete early-reading "
            "path that connects letter sounds, tracing and word building "
            "instead of a collection of unrelated alphabet games — Lumi "
            "Letters Pro is built for this."
        ): (
            "കിൻഡർഗാർട്ടനായി തയ്യാറെടുക്കുന്ന കുടുംബങ്ങൾക്ക് പരസ്പരബന്ധമില്ലാത്ത "
            "അക്ഷരമാലാ കളികളുടെ കൂട്ടത്തിന് പകരം അക്ഷരശബ്ദങ്ങൾ, എഴുത്തുപരിശീലനം, "
            "വാക്കുനിർമാണം എന്നിവ ബന്ധിപ്പിക്കുന്ന സമഗ്രമായ പ്രാരംഭ വായനാപാത "
            "ആവശ്യമാണ് — Lumi Letters Pro ഇതിനായി രൂപകൽപ്പന ചെയ്തിരിക്കുന്നു."
        ),
        (
            "A complete early-math app should make counting, number sense and "
            "first operations feel like one connected adventure rather than "
            "isolated drills — Lumi Math Pro is built for this."
        ): (
            "സമഗ്രമായ പ്രാരംഭ ഗണിത ആപ്പ് എണ്ണൽ, സംഖ്യാബോധം, ആദ്യ കണക്കുകൂട്ടലുകൾ "
            "എന്നിവയെ ഒറ്റപ്പെട്ട ആവർത്തന അഭ്യാസങ്ങൾക്ക് പകരം പരസ്പരം ബന്ധമുള്ള "
            "ഒരു സാഹസികയാത്രയായി അനുഭവപ്പെടുത്തണം — Lumi Math Pro ഇതിനായി "
            "രൂപകൽപ്പന ചെയ്തിരിക്കുന്നു."
        ),
        (
            "Bilingual children learning Zhuyin at home need a complete path "
            "through sounds, symbols, tones and blending, with enough playful "
            "repetition to make the system familiar — Lumi Bopomofo Pro is "
            "built for this."
        ): (
            "വീട്ടിൽ Zhuyin പഠിക്കുന്ന ദ്വിഭാഷാ കുട്ടികൾക്ക് ശബ്ദങ്ങൾ, ചിഹ്നങ്ങൾ, "
            "സ്വരഭേദങ്ങൾ, ശബ്ദസംയോജനം എന്നിവയിലൂടെ സമഗ്രമായ പഠനപാതയും, ഈ "
            "സംവിധാനം പരിചിതമാകാൻ മതിയായ കളിയോടെയുള്ള ആവർത്തനവും ആവശ്യമാണ് — "
            "Lumi Bopomofo Pro ഇതിനായി രൂപകൽപ്പന ചെയ്തിരിക്കുന്നു."
        ),
        (
            "Parents travelling with young children need activities that turn "
            "packing, waiting and discovering a new place into part of the "
            "adventure instead of another source of stress — Lumi Trip Planet "
            "is built for this."
        ): (
            "ചെറിയ കുട്ടികളുമായി യാത്ര ചെയ്യുന്ന മാതാപിതാക്കൾക്ക് പാക്കിംഗ്, "
            "കാത്തിരിപ്പ്, പുതിയ സ്ഥലം കണ്ടെത്തൽ എന്നിവയെ അധിക സമ്മർദമാക്കാതെ "
            "സാഹസികയാത്രയുടെ ഭാഗമാക്കുന്ന പ്രവർത്തനങ്ങൾ വേണം — Lumi Trip Planet "
            "ഇതിനായി രൂപകൽപ്പന ചെയ്തിരിക്കുന്നു."
        ),
        (
            "Busy commuters need vocabulary practice that fits into spare "
            "minutes without requiring a full lesson, a new account or a phone "
            "in hand for every review — Wordmate: Learn 44 Languages is built "
            "for this."
        ): (
            "തിരക്കുള്ള യാത്രക്കാർക്ക് പൂർണ്ണ പാഠമോ പുതിയ അക്കൗണ്ടോ ഓരോ "
            "ആവർത്തനത്തിനും ഫോൺ കൈയിൽ പിടിക്കേണ്ട ആവശ്യമോ ഇല്ലാതെ, "
            "ഒഴിഞ്ഞുകിട്ടുന്ന കുറച്ച് മിനിറ്റുകളിൽ ഒതുങ്ങുന്ന വാക്കുപരിശീലനം "
            "വേണം — Wordmate: Learn 44 Languages ഇതിനായി രൂപകൽപ്പന "
            "ചെയ്തിരിക്കുന്നു."
        ),
        (
            "Parents planning outdoor time need more than a temperature: they "
            "need a quick, age-aware view of whether conditions suit a child "
            "and what clothing makes sense — Lumi Weather is built for this."
        ): (
            "പുറത്തേക്കുള്ള സമയം ആസൂത്രണം ചെയ്യുന്ന മാതാപിതാക്കൾക്ക് താപനില "
            "മാത്രം പോരാ: കാലാവസ്ഥ കുട്ടിക്ക് അനുയോജ്യമാണോ, ഏത് വസ്ത്രമാണ് "
            "ചേരുന്നത് എന്നിവ പ്രായം കണക്കിലെടുത്ത് വേഗത്തിൽ മനസ്സിലാക്കണം — "
            "Lumi Weather ഇതിനായി രൂപകൽപ്പന ചെയ്തിരിക്കുന്നു."
        ),
    },
    "no": {
        (
            "Travel creators need a repeatable film look that adds grain, "
            "halation and colour character without reducing every destination "
            "to the same flat filter — PhotoCream is built for this."
        ): (
            "Reiseskapere trenger et gjentakbart filmutseende som gir korn, "
            "halering og fargepreg uten å redusere hver destinasjon til det samme "
            "flate filteret — PhotoCream er laget for dette."
        ),
        (
            "Bilingual children learning Zhuyin at home need a complete path "
            "through sounds, symbols, tones and blending, with enough playful… "
            "— Lumi Bopomofo Pro."
        ): (
            "Tospråklige barn som lærer Zhuyin hjemme trenger en komplett vei "
            "gjennom lyder, symboler, toner og sammensetting, med nok lekne… — "
            "Lumi Bopomofo Pro."
        ),
        (
            "Bilingual children learning Zhuyin at home need a complete path "
            "through sounds, symbols, tones and blending, with enough playful "
            "repetition to make the system familiar — Lumi Bopomofo Pro is "
            "built for this."
        ): (
            "Tospråklige barn som lærer Zhuyin hjemme trenger en komplett vei "
            "gjennom lyder, symboler, toner og sammensetting, med nok lekne "
            "repetisjoner til å gjøre systemet kjent — Lumi Bopomofo Pro er laget "
            "for dette."
        ),
    },
    "pt-PT": {
        (
            "Bilingual children learning Zhuyin at home need a complete path "
            "through sounds, symbols, tones and blending, with enough playful… "
            "— Lumi Bopomofo Pro."
        ): (
            "Crianças bilingues a aprender Zhuyin em casa precisam de um caminho "
            "completo por sons, símbolos, tons e combinação de sons, com repetição "
            "lúdica suficiente para tornar o sistema familiar… — Lumi Bopomofo Pro."
        ),
        (
            "Bilingual children learning Zhuyin at home need a complete path "
            "through sounds, symbols, tones and blending, with enough playful "
            "repetition to make the system familiar — Lumi Bopomofo Pro is "
            "built for this."
        ): (
            "Crianças bilingues a aprender Zhuyin em casa precisam de um caminho "
            "completo por sons, símbolos, tons e combinação de sons, com repetição "
            "lúdica suficiente para tornar o sistema familiar — Lumi Bopomofo Pro "
            "foi criado para isso."
        ),
    },
    "ro": {
        (
            "best pay once film photo editor for travel creators on iphone: "
            "honest iPhone app buying guide"
        ): (
            "cel mai bun editor foto cu aspect de film și plată unică pentru "
            "creatorii de conținut de călătorie pe iPhone: ghid onest pentru "
            "cumpărarea unei aplicații iPhone"
        ),
        (
            "For a preschooler, a bedtime routine works best when it is short, "
            "visual and predictable enough for the child to follow without "
            "another… — Lumi Mission Planet."
        ): (
            "Pentru un preșcolar, rutina de culcare funcționează cel mai bine "
            "când este scurtă, vizuală și suficient de previzibilă astfel încât "
            "copilul să o urmeze fără încă o… — Lumi Mission Planet."
        ),
        (
            "For a preschooler, a bedtime routine works best when it is short, "
            "visual and predictable enough for the child to follow without "
            "another round of reminders — Lumi Mission Planet is built for this."
        ): (
            "Pentru un preșcolar, rutina de culcare funcționează cel mai bine "
            "când este scurtă, vizuală și suficient de previzibilă astfel încât "
            "copilul să o urmeze fără încă o rundă de reamintiri — Lumi Mission "
            "Planet este creată pentru acest scop."
        ),
    },
    "sl-SI": {
        (
            "best pay once film photo editor for travel creators on iphone: "
            "honest iPhone app buying guide"
        ): (
            "najboljši urejevalnik fotografij s filmskim videzom in enkratnim "
            "plačilom za popotniške ustvarjalce na iPhonu: pošten vodnik za "
            "nakup aplikacije za iPhone"
        ),
        (
            "Busy commuters need vocabulary practice that fits into spare "
            "minutes without requiring a full lesson, a new account or a "
            "phone… — Wordmate: Learn 44 Languages."
        ): (
            "Zaposleni, ki se vsak dan vozijo na delo, potrebujejo učenje "
            "besedišča, ki ga lahko vključijo v proste minute, ne da bi "
            "potrebovali celo lekcijo, nov račun ali telefon v roki… — "
            "Wordmate: Learn 44 Languages."
        ),
    },
    "ta-IN": {
        (
            "Bilingual children learning Zhuyin at home need a complete path "
            "through sounds, symbols, tones and blending, with enough playful "
            "repetition to make the system familiar — Lumi Bopomofo Pro is "
            "built for this."
        ): (
            "வீட்டில் Zhuyin கற்கும் இருமொழிக் குழந்தைகளுக்கு ஒலிகள், "
            "குறியீடுகள், தொனிகள் மற்றும் ஒலிக்கலப்பு ஆகியவற்றை உள்ளடக்கிய "
            "முழுமையான கற்றல் பாதையும், இந்த முறையைப் பழகிக்கொள்ள போதுமான "
            "விளையாட்டுத்தனமான மீள்பயிற்சியும் தேவை — இதற்காகவே Lumi "
            "Bopomofo Pro உருவாக்கப்பட்டுள்ளது."
        ),
    },
    "el": {
        "TripBee Pro: Trip Planner": "TripBee Pro: Σχεδιασμός Ταξιδιού",
    },
    "id": {
        "TripBee Pro: Trip Planner": "TripBee Pro: Perencana Perjalanan",
    },
    "ja": {
        "TripBee Pro: Trip Planner": "TripBee Pro: 旅行プランナー",
        (
            "Publisher-authored guide from Lumi Studio, the app developer. App "
            "names are trademarks of their owners and are used only for "
            "identification. For documents, health, school, and productivity "
            "decisions, verify official requirements where relevant."
        ): (
            "アプリ開発者であるLumi Studioによる公式購入ガイドです。アプリ名は各"
            "所有者の商標であり、識別のためにのみ使用しています。書類、健康、学校、"
            "生産性に関する判断は、該当する公式要件を必ずご確認ください。"
        ),
        (
            "A good itinerary app turns a messy trip into a clear day-by-day "
            "timeline — flights, hotels, activities, restaurants and transport "
            "— with clear type icons so you can read your day at a glance — "
            "TripBee Pro: Trip Planner is built for this."
        ): (
            "優れた旅程アプリは、まとまりのない旅行計画を明確な日別タイムライン"
            "に整理し、フライト、ホテル、アクティビティ、レストラン、交通機関"
            "を種類別アイコンで一目で確認できるようにします — TripBee Pro: "
            "Trip Planner はこのために作られています。"
        ),
    },
    "mr-IN": {
        "TripBee Pro: Trip Planner": "TripBee Pro: प्रवास नियोजक",
    },
    "or-IN": {
        "TripBee Pro: Trip Planner": "TripBee Pro: ଯାତ୍ରା ଯୋଜନାକାରୀ",
    },
    "pa-IN": {
        "TripBee Pro: Trip Planner": "TripBee Pro: ਯਾਤਰਾ ਯੋਜਨਾਕਾਰ",
    },
    "th": {
        "TripBee Pro: Trip Planner": "TripBee Pro: วางแผนการเดินทาง",
    },
    "ur-PK": {
        "TripBee Pro: Trip Planner": "TripBee Pro: سفر کا منصوبہ ساز",
    },
}
_DAILYMATE_QUERY = (
    "best practical language phrase app for travelers with apple watch"
)
_TRIPBEE_LITE_QUERY = (
    "best simple trip planner app for one upcoming trip iphone"
)
_REVIEWED_NEW_APP_QUERIES = {
    "ca": {
        "daily": "millor app de frases útils per viatjar amb Apple Watch",
        "trip": "millor app senzilla per planificar un viatge a l'iPhone",
        "how": "Com triar: {query}",
        "title": "{query}: guia honesta per triar apps per a iPhone",
    },
    "es-ES": {
        "daily": "mejor app de frases útiles para viajar con Apple Watch",
        "trip": "mejor app sencilla para planificar un viaje en iPhone",
        "how": "Cómo elegir: {query}",
        "title": "{query}: guía honesta para elegir apps para iPhone",
    },
    "es-MX": {
        "daily": "mejor app de frases útiles para viajar con Apple Watch",
        "trip": "mejor app sencilla para planear un viaje en iPhone",
        "how": "Cómo elegir: {query}",
        "title": "{query}: guía honesta para elegir apps para iPhone",
    },
    "fr-CA": {
        "daily": (
            "meilleure application de phrases utiles en voyage avec Apple Watch"
        ),
        "trip": (
            "meilleure application simple pour planifier un voyage sur iPhone"
        ),
        "how": "Comment choisir : {query}",
        "title": "{query} : guide d’achat transparent pour iPhone",
    },
    "fr-FR": {
        "daily": (
            "meilleure application de phrases utiles en voyage avec Apple Watch"
        ),
        "trip": (
            "meilleure application simple pour planifier un voyage sur iPhone"
        ),
        "how": "Comment choisir : {query}",
        "title": "{query} : guide d’achat transparent pour iPhone",
    },
    "it": {
        "daily": (
            "migliore app di frasi utili in viaggio con Apple Watch"
        ),
        "trip": "migliore app semplice per organizzare un viaggio su iPhone",
        "how": "Come scegliere: {query}",
        "title": (
            "{query}: guida trasparente all'acquisto di app per iPhone"
        ),
    },
    "pt-BR": {
        "daily": (
            "melhor app de frases úteis para viagens com Apple Watch"
        ),
        "trip": "melhor app simples para planejar uma viagem no iPhone",
        "how": "Como escolher: {query}",
        "title": (
            "{query}: guia transparente para escolher apps para iPhone"
        ),
    },
    "pt-PT": {
        "daily": (
            "melhor aplicação de frases úteis para viajar com Apple Watch"
        ),
        "trip": (
            "melhor aplicação simples para planear uma viagem no iPhone"
        ),
        "how": "Como escolher: {query}",
        "title": (
            "{query}: guia transparente para escolher aplicações para iPhone"
        ),
    },
    "ro": {
        "daily": (
            "cea mai bună aplicație cu fraze utile pentru călătorii și Apple Watch"
        ),
        "trip": (
            "cea mai bună aplicație simplă pentru planificarea unei călătorii "
            "pe iPhone"
        ),
        "how": "Cum alegi: {query}",
        "title": (
            "{query}: ghid transparent pentru alegerea aplicațiilor iPhone"
        ),
    },
}
for _locale, _copy in _REVIEWED_NEW_APP_QUERIES.items():
    _overrides = LOCALE_TEXT_OVERRIDES.setdefault(_locale, {})
    for _source, _target_key in (
        (_DAILYMATE_QUERY, "daily"),
        (_TRIPBEE_LITE_QUERY, "trip"),
    ):
        _query = _copy[_target_key]
        _overrides[_source] = _query
        _overrides[f"How to choose: {_source}"] = _copy["how"].format(
            query=_query
        )
        _overrides[
            f"{_source}: honest iPhone app buying guide"
        ] = _copy["title"].format(query=_query)

LOCALE_TARGET_REPLACEMENTS = {
    "gu-IN": (("નિષ્ઠાવાન", "પ્રામાણિક"),),
    "id": (
        ("Pelacakan goresan", "Menebalkan goresan"),
        ("pelacakan goresan", "menebalkan goresan"),
        ("melalui pelacakan dan permainan", "melalui menelusuri dan permainan"),
        ("foto burst", "rentetan foto"),
        ("light-leak", "kebocoran cahaya"),
        ("light leak", "kebocoran cahaya"),
        ("watermark", "tanda air"),
        ("toolkit", "peralatan"),
        ("grain", "bintik film"),
        ("Tracing", "Menelusuri"),
        ("tracing", "menelusuri"),
        ("blending", "penggabungan"),
        ("packing", "berkemas"),
        ("setup", "persiapan"),
        ("Prompt", "Petunjuk"),
        ("prompt", "petunjuk"),
        ("setiap review", "setiap kali mengulang"),
        ("review singkat", "ulangan singkat"),
        ("Home Screen", "Layar Utama"),
        ("Widget", "Alat mini"),
        ("widget", "alat mini"),
        ("white noise", "derau putih"),
        ("brown noise", "derau cokelat"),
        ("sense angka", "pemahaman angka"),
        ("bilingual", "dwibahasa"),
        ("heritage", "bahasa warisan"),
        ("outing", "aktivitas di luar"),
        ("scene", "pemandangan"),
        ("timer", "pengatur waktu"),
        ("unlock", "buka kunci"),
    ),
    "it": (
        (
            "guida acquisto app iPhone",
            "guida onesta all'acquisto di app per iPhone",
        ),
        (
            "guida all’acquisto di app per iPhone",
            "guida onesta all’acquisto di app per iPhone",
        ),
        (
            "guida all'acquisto di app per iPhone",
            "guida onesta all'acquisto di app per iPhone",
        ),
    ),
    "ja": (
        (
            "Lumi Studioによる出版社公式ガイド。アプリ名は各所有者の商標であり、"
            "識別のためにのみ使用しています。書類、健康、学校、生産性に関する判断"
            "は、該当する公式要件を必ずご確認ください。",
            "アプリ開発者であるLumi Studioによる公式購入ガイドです。アプリ名は各"
            "所有者の商標であり、識別のためにのみ使用しています。書類、健康、学校、"
            "生産性に関する判断は、該当する公式要件を必ずご確認ください。",
        ),
    ),
    "kn-IN": (
        ("ಐಫೋನ್", "iPhone"),
        ("ನಿಷ್ಠ", "ಪ್ರಾಮಾಣಿಕ"),
    ),
    "ml-IN": (
        ("ഐഫോണിൽ", "iPhone-ൽ"),
        ("ഐഫോൺ", "iPhone"),
    ),
    "ms": (
        (
            "panduan beli aplikasi iPhone jujur",
            "panduan jujur membeli aplikasi iPhone",
        ),
        ("di iphone", "di iPhone"),
        ("apple watch", "Apple Watch"),
        ("Pencipta travel", "Pencipta kandungan pelancongan"),
        ("pencipta travel", "pencipta kandungan pelancongan"),
        ("yang travel", "yang melancong"),
        ("Aplikasi travel", "Aplikasi perjalanan"),
        ("aplikasi travel", "aplikasi perjalanan"),
        ("aktiviti travel", "aktiviti perjalanan"),
        ("trip keluarga", "percutian keluarga"),
        ("pra-trip", "sebelum perjalanan"),
        ("travel", "perjalanan"),
        ("trip", "perjalanan"),
        ("light-leak", "kebocoran cahaya"),
        ("light leak", "kebocoran cahaya"),
        ("watermark", "tanda air"),
        ("toolkit", "kit alat"),
        ("grain", "butiran filem"),
        ("halation", "halasi"),
        ("homeschool", "pendidikan di rumah"),
        ("Tracing", "Menekap"),
        ("tracing", "menekap"),
        ("packing", "mengemas barang"),
        ("Home Screen", "Skrin Utama"),
        ("commute", "berulang-alik"),
        ("Offline", "Luar talian"),
        ("offline", "luar talian"),
        ("peluru anda", "butiran anda"),
        ("gambar letusan", "gambar rentetan"),
        ("mata wang rumah", "mata wang negara asal"),
        # "widjet" is not a Malay word -- Malay borrows "widget" unchanged, and
        # this rule was silently misspelling it across the ms pages.
        ("Widjet", "Widget"),
        ("widjet", "widget"),
    ),
    "no": (
        ("Streksporing", "Skriveøving"),
        ("streksporing", "skriveøving"),
    ),
    "pa-IN": (("ਆਈਫੋਨ", "iPhone"),),
    "sl-SI": (("iphonu", "iPhonu"),),
    "sv": (
        ("Streckspårning", "Kalkering"),
        ("streckspårning", "kalkering"),
        ("genom spårning och lek", "genom kalkering och lek"),
        (
            "ljud, toner, spårning, blandning och spel",
            "ljud, toner, kalkering, blandning och spel",
        ),
    ),
    "ta-IN": (
        ("ஐபோனில்", "iPhone-ல்"),
        ("ஐபோன்", "iPhone"),
    ),
    "th": (
        (
            "โหมด Auto Clear และ Sharpen",
            "โหมดล้างภาพอัตโนมัติ (Auto Clear) และเพิ่มความคมชัด (Sharpen)",
        ),
        (
            "ลองใช้ Auto Clear แล้วตามด้วย Sharpen",
            "ลองใช้ล้างภาพอัตโนมัติ (Auto Clear) แล้วตามด้วยเพิ่มความคมชัด (Sharpen)",
        ),
        (
            "โหมด Auto Clear / Sharpen สำหรับภาพโฟกัสนุ่ม",
            "โหมดล้างภาพอัตโนมัติ (Auto Clear) / เพิ่มความคมชัด (Sharpen) "
            "สำหรับภาพโฟกัสนุ่ม",
        ),
        (
            "แอป bopomofo ที่ดีที่สุดสำหรับเด็กเรียน zhuyin บน iPhone",
            "แอปจู้ยิน (Bopomofo) ที่ดีที่สุดสำหรับเด็กบน iPhone",
        ),
        ("แอป Zhuyin", "แอปจู้ยิน (Zhuyin)"),
        ("เรียน Zhuyin", "เรียนจู้ยิน (Zhuyin)"),
    ),
    "te-IN": (
        ("ఐఫోన్‌ లో", "iPhone‌లో"),
        ("ఐఫోన్", "iPhone"),
    ),
    "ur-PK": (("آئی فون", "iPhone"),),
    "vi": (
        ("Không dấu watermark", "Không có hình mờ"),
        ("không dấu watermark", "không có hình mờ"),
        ("Không watermark", "Không có hình mờ"),
        ("không watermark", "không có hình mờ"),
        ("watermark", "hình mờ"),
        ("halation", "hiệu ứng hào quang"),
        ("profile", "cấu hình màu"),
        ("portfolio", "hồ sơ năng lực"),
        ("Widget", "Tiện ích"),
        ("widget", "tiện ích"),
        ("offline", "ngoại tuyến"),
        ("Theo dõi nét", "Tô nét chữ"),
        ("theo dõi nét", "tô nét chữ"),
        ("phonics", "đánh vần"),
        ("checklist", "danh sách kiểm tra"),
        ("cabin", "nhà gỗ"),
    ),
    "es-MX": (("móvil", "celular"),),
    "zh-Hans": (
        ("在无数据国家离线可用", "在无移动数据的国家也能离线可用"),
        ("无推送你使用云账户", "也不会迫使你注册云账户"),
        (
            "睡眠时，每月催促订阅恰恰相反",
            "为了获得良好睡眠，每月催促你订阅恰恰与放松的目的背道而驰",
        ),
        ("Home Screen", "主屏幕"),
    ),
    "zh-Hant": (
        ("Home Screen 小工具", "主畫面小工具"),
        ("Home Screen", "主畫面"),
        ("身份證", "身分證"),
        ("提前退出", "提前結束"),
        ("退出", "離開"),
        ("保存在", "儲存在"),
        ("保存", "儲存"),
        ("無數據", "沒有網路"),
        ("計劃", "計畫"),
    ),
}
_REVIEWED_TARGET_REPLACEMENTS = {
    "ar-SA": (
        ("ودجت شاشة البداية", "ودجت الشاشة الرئيسية"),
    ),
    "bn-BD": (
        ("আইফোনের", "iPhone-এর"),
        ("আইফোন", "iPhone"),
        ("ফ্রি-টু-স্টার্ট", "শুরুতে বিনামূল্যে"),
    ),
    "cs": (
        ("zdarma na zkoušku", "s bezplatným začátkem"),
    ),
    "da": (
        ("familiekontent", "familieindhold"),
        ("forudbetaling", "engangsbetaling"),
        ("Home Screen", "Hjemmeskærm"),
        ("gennem sporing og leg", "gennem skriveøvelser og leg"),
        (
            "bogstavlyde, sporing og ordbygning",
            "bogstavlyde, skriveøvelser og ordbygning",
        ),
    ),
    "de-DE": (
        ("Home Screen", "Home-Bildschirm"),
    ),
    "el": (
        (
            "8.400 πρακτικές φράσεις; 47 γλώσσες μάθησης; "
            "Widget + Apple Watch; Πληρώστε μία φορά; Χωρίς συνδρομή",
            "8.400 πρακτικές φράσεις, 47 γλώσσες μάθησης, "
            "Widget + Apple Watch, Πληρώστε μία φορά, Χωρίς συνδρομή",
        ),
        (
            "Ένα ολοκληρωμένο ταξίδι δωρεάν; "
            "Ξεκλείδωμα premium μίας φοράς; Χωρίς συνδρομή; "
            "Χωρίς λογαριασμό; Χωρίς διαφημίσεις ή παρακολούθηση",
            "Ένα ολοκληρωμένο ταξίδι δωρεάν, "
            "Ξεκλείδωμα premium μίας φοράς, Χωρίς συνδρομή, "
            "Χωρίς λογαριασμό, Χωρίς διαφημίσεις ή παρακολούθηση",
        ),
    ),
    "fi": (
        ("kertalukituksen", "kerta-avauksen"),
        ("kertalukitusta", "kerta-avausta"),
        ("kertalukitus", "kerta-avaus"),
    ),
    "fr-CA": (
        (
            "Meilleure application gratuite pour planifier un itinéraire de "
            "voyage unique sur iPhone (2026)",
            "Meilleure application de planification d'itinéraire de voyage "
            "unique gratuite pour commencer sur iPhone (2026)",
        ),
    ),
    "fr-FR": (
        (
            "Meilleure application gratuite pour commencer de planification "
            "d’itinéraire pour un voyage sur iPhone (2026)",
            "Meilleure application de planification d’itinéraire pour un voyage "
            "gratuite pour commencer sur iPhone (2026)",
        ),
    ),
    "he": (
        ("לאייפון", "ל-iPhone"),
        ("באייפון", "ב-iPhone"),
        ("אייפון", "iPhone"),
        ("אייפד", "iPad"),
        ("בחנות האפליקציות", "ב-App Store"),
        (
            "המוציא לאור מהמתכנת",
            "המוציא לאור מאת מפתח האפליקציה",
        ),
        ("לא צורכת", "שאינה מתכלה"),
    ),
    "hi": (
        ("आईफोन", "iPhone"),
        ("आईपैड", "iPad"),
        ("एप्पल वॉच", "Apple Watch"),
        ("ऐप स्टोर", "App Store"),
    ),
    "hr": (
        ("jednu aktivnu putovanje", "jedno aktivno putovanje"),
    ),
    "id": (
        ("Alat mini", "Widget"),
        ("alat mini", "widget"),
        ("non-konsumsi", "tidak habis pakai"),
    ),
    "ml-IN": (("ആവശ്യമാണ吗?", "ആവശ്യമാണോ?"),),
    "ms": (
        ("bukan penggunaan", "tidak habis guna"),
        ("Eksport / kunci masuk", "Eksport / pergantungan vendor"),
    ),
    "nl-NL": (
        ("gezinsinhoud", "familiegegevens"),
        ("via traceren en spel", "via overtrekken en spel"),
        (
            "klanken, traceren en woordbouw",
            "klanken, overtrekken en woordbouw",
        ),
    ),
    "no": (
        ("engangslåsen", "engangsopplåsingen"),
        ("engangslås", "engangsopplåsing"),
        ("forhåndsbetaling", "engangsbetaling"),
        ("gjennom sporing og lek", "gjennom skriveøvelser og lek"),
        (
            "bokstavlyder, sporing og ordbygging",
            "bokstavlyder, skriveøvelser og ordbygging",
        ),
    ),
    "or-IN": (
        ("ଆଇଫୋନ", "iPhone"),
        ("ଆଇପ୍ୟାଡ୍", "iPad"),
        ("ଆପ୍ଲ୍ ଓଉଉଚ୍", "Apple Watch"),
        ("ଆପ୍ ଷ୍ଟୋର", "App Store"),
        ("ଏପ୍ ଷ୍ଟୋର", "App Store"),
        ("କି subscription ଅଛି?", "କୌଣସି ସଦସ୍ୟତା ଅଛି କି?"),
        ("subscription", "ସଦସ୍ୟତା"),
    ),
    "pa-IN": (
        ("ਆਈਪੈਡ", "iPad"),
        ("ਐਪਲ ਵਾਚ", "Apple Watch"),
        ("ਐਪ ਸਟੋਰ", "App Store"),
    ),
    "sv": (
        ("köp i förväg", "engångsköp"),
        (
            "bokstavsljud, spårning och ordbyggande",
            "bokstavsljud, skrivövningar och ordbyggande",
        ),
    ),
    "te-IN": (
        ("Home Screen", "హోమ్ స్క్రీన్"),
    ),
    "uk": (
        ("віджеті Home Screen", "віджеті Головного екрана"),
    ),
    "zh-Hans": (
        ("最佳免费试用", "最佳免费起步"),
        ("支持免费试用", "支持免费起步"),
        ("免费试用推荐", "免费起步推荐"),
        ("免费试用，支持", "免费起步，支持"),
        ("免费试用访问模式", "免费起步使用模式"),
        ("可免费试用", "可免费起步使用"),
    ),
}
for _locale, _replacements in _REVIEWED_TARGET_REPLACEMENTS.items():
    LOCALE_TARGET_REPLACEMENTS[_locale] = (
        *LOCALE_TARGET_REPLACEMENTS.get(_locale, ()),
        *_replacements,
    )
NO_TRANSLATE_JSON_KEYS = {
    "@context",
    "@type",
    "@id",
    "url",
    "installUrl",
    "sameAs",
    "identifier",
    "propertyID",
    "value",
    "item",
    "operatingSystem",
    "applicationCategory",
    "inLanguage",
    "price",
    "priceCurrency",
    "dateModified",
    "datePublished",
}


def read_key() -> str:
    key_path = Path.home() / ".openai_key"
    return key_path.read_text(encoding="utf-8").strip()


def page_url(slug: str, lang: str | None = None) -> str:
    if lang:
        return f"{BASE_URL}/{lang}/answers/{slug}.html"
    return f"{BASE_URL}/answers/{slug}.html"


def localize_url(url: str, lang: str) -> str:
    parsed = urlsplit(url)
    base = urlsplit(BASE_URL)
    if (
        parsed.scheme != base.scheme
        or parsed.netloc != base.netloc
        or not parsed.path.startswith(base.path.rstrip("/") + "/")
    ):
        return url
    suffix = parsed.path[len(base.path.rstrip("/")) + 1 :]
    if suffix.startswith(tuple(x + "/" for x in ALL_LANGS)):
        return url
    localized = ROOT / lang / suffix
    if suffix.endswith("/"):
        localized /= "index.html"
    if not localized.exists():
        return url
    localized_path = f"{base.path.rstrip('/')}/{lang}/{suffix}"
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            localized_path,
            parsed.query,
            parsed.fragment,
        )
    )


def discover_slugs(
    limit: int | None = None,
    langs: list[str] | None = None,
) -> list[str]:
    english = {p.name for p in ANSWERS.glob("*.html") if p.name != "index.html"}
    target_langs = langs or ALL_LANGS

    def missing_target_lang(name: str) -> bool:
        return any(
            not (ROOT / lang / "answers" / name).exists()
            for lang in target_langs
        )

    todo = sorted(n for n in english if missing_target_lang(n))
    ordered = [Path(x).stem for x in todo]
    return ordered[:limit] if limit else ordered


def prioritize_translatable_slugs(
    slugs: list[str],
    langs: list[str],
    global_maps: dict[str, dict[str, str]],
) -> list[str]:
    progressable: list[str] = []
    blocked: list[str] = []
    for slug in slugs:
        source_path = ANSWERS / f"{slug}.html"
        if not source_path.exists():
            blocked.append(slug)
            continue
        strings, _, _ = extract_strings(
            source_path.read_text(encoding="utf-8")
        )
        can_progress = any(
            not (ROOT / lang / "answers" / f"{slug}.html").exists()
            and (
                lang in ENGLISH_LOCALES
                or all(
                    source in global_maps.get(lang, {})
                    for source in strings
                )
            )
            for lang in langs
        )
        (progressable if can_progress else blocked).append(slug)
    return progressable + blocked


def parse_langs(raw: str | None) -> list[str]:
    if not raw:
        return ALL_LANGS
    langs = [x.strip() for x in raw.replace(",", " ").split() if x.strip()]
    bad = [x for x in langs if x not in ALL_LANGS]
    if bad:
        raise SystemExit(f"Unsupported --langs values: {', '.join(bad)}")
    return langs


def should_translate_json(key: str | None, value: str) -> bool:
    if not value.strip():
        return False
    if key in NO_TRANSLATE_JSON_KEYS:
        return False
    if value.startswith(("http://", "https://", "#")):
        return False
    if value in {"USD", "0", "iOS", "BusinessApplication", "EducationalApplication", "ProductivityApplication"}:
        return False
    return True


def collect_json_strings(obj: Any, out: list[str], key: str | None = None) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            collect_json_strings(v, out, k)
    elif isinstance(obj, list):
        for v in obj:
            collect_json_strings(v, out, key)
    elif isinstance(obj, str) and should_translate_json(key, obj):
        out.append(obj)


def apply_json_mapping(obj: Any, mapping: dict[str, str], key: str | None = None) -> Any:
    if isinstance(obj, dict):
        return {k: apply_json_mapping(v, mapping, k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [apply_json_mapping(v, mapping, key) for v in obj]
    if isinstance(obj, str) and should_translate_json(key, obj):
        return mapping.get(obj, obj)
    return obj


def update_json_language(obj: Any, lang: str) -> Any:
    if isinstance(obj, dict):
        for key, value in obj.items():
            obj[key] = update_json_language(value, lang)
        if "inLanguage" in obj:
            obj["inLanguage"] = BASE_LANG[lang]
    elif isinstance(obj, list):
        return [update_json_language(value, lang) for value in obj]
    return obj


def update_breadcrumb_urls(obj: Any, lang: str, slug: str) -> Any:
    if isinstance(obj, dict):
        schema_type = obj.get("@type")
        schema_types = (
            set(schema_type)
            if isinstance(schema_type, list)
            else {schema_type}
        )
        if "WebPage" in schema_types:
            canonical = page_url(slug, lang)
            obj["@id"] = f"{canonical}#webpage"
            obj["url"] = canonical
        if "Article" in schema_types and "mainEntityOfPage" in obj:
            canonical = page_url(slug, lang)
            main_page = obj["mainEntityOfPage"]
            if isinstance(main_page, str):
                obj["mainEntityOfPage"] = canonical
            elif isinstance(main_page, dict):
                main_page["@id"] = f"{canonical}#webpage"
                if "url" in main_page:
                    main_page["url"] = canonical
        if obj.get("@type") == "BreadcrumbList":
            items = obj.get("itemListElement", [])
            for index, item in enumerate(items):
                if isinstance(item, dict) and isinstance(item.get("item"), str):
                    item["item"] = (
                        page_url(slug, lang)
                        if index == len(items) - 1
                        else localize_url(item["item"], lang)
                    )
            return obj
        if obj.get("@type") == "LearningResource" and isinstance(
            obj.get("url"), str
        ):
            obj["url"] = localize_url(obj["url"], lang)
        if obj.get("@type") == "ListItem" and isinstance(obj.get("item"), str):
            obj["item"] = localize_url(obj["item"], lang)
        for v in obj.values():
            update_breadcrumb_urls(v, lang, slug)
    elif isinstance(obj, list):
        for v in obj:
            update_breadcrumb_urls(v, lang, slug)
    return obj


JSON_LD_SCRIPT_RE = re.compile(
    r"(?P<open><script\b[^>]*application/ld\+json[^>]*>)"
    r"(?P<body>.*?)"
    r"(?P<close></script>)",
    flags=re.IGNORECASE | re.DOTALL,
)


def reconcile_structured_data_urls(
    source: str,
    lang: str,
    slug: str,
) -> str:
    """Align localized page-owned JSON-LD identities with the canonical URL."""
    def replace(match: re.Match[str]) -> str:
        raw = match.group("body").strip()
        try:
            document = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Invalid localized Answer JSON-LD: {lang}/{slug}: {exc}"
            ) from exc
        before = json.dumps(document, ensure_ascii=False, sort_keys=True)
        update_breadcrumb_urls(document, lang, slug)
        after = json.dumps(document, ensure_ascii=False, sort_keys=True)
        if before == after:
            return match.group(0)
        return (
            f"{match.group('open')}\n"
            f"{json.dumps(document, ensure_ascii=False, indent=2)}\n"
            f"{match.group('close')}"
        )

    return JSON_LD_SCRIPT_RE.sub(replace, source)


def extract_strings(source: str) -> tuple[list[str], list[tuple[int, int, str, str]], list[tuple[int, int, str]]]:
    strings: list[str] = []
    attr_spans: list[tuple[int, int, str, str]] = []
    json_spans: list[tuple[int, int, str]] = []

    script_style_ranges: list[tuple[int, int]] = []
    for m in re.finditer(r"<(script|style)\b[^>]*>.*?</\1>", source, flags=re.I | re.S):
        script_style_ranges.append((m.start(), m.end()))
        if re.search(r"<script\b[^>]*application/ld\+json", m.group(0), flags=re.I):
            open_end = source.find(">", m.start()) + 1
            close_start = source.rfind("</script>", m.start(), m.end())
            raw = source[open_end:close_start].strip()
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            collect_json_strings(obj, strings)
            json_spans.append((open_end, close_start, raw))

    def in_block(pos: int) -> bool:
        return any(start <= pos < end for start, end in script_style_ranges)

    for m in re.finditer(r"<meta\b[^>]*(?:name|property)=[\"'](?:description|og:title|og:description)[\"'][^>]*>", source, flags=re.I):
        if in_block(m.start()):
            continue
        tag = m.group(0)
        cm = re.search(r"content=(['\"])(.*?)\1", tag, flags=re.I | re.S)
        if cm and cm.group(2).strip():
            start = m.start() + cm.start(2)
            end = m.start() + cm.end(2)
            text = html.unescape(cm.group(2))
            strings.append(text)
            attr_spans.append((start, end, text, "content"))

    text_spans: list[tuple[int, int, str, str]] = []
    pos = 0
    for m in re.finditer(r"<[^>]+>", source):
        if m.start() > pos and not in_block(pos):
            raw = source[pos : m.start()]
            if raw.strip():
                text = html.unescape(raw)
                if text.strip():
                    strings.append(text.strip())
                    text_spans.append((pos, m.start(), text.strip(), "text"))
        pos = m.end()
    if pos < len(source) and not in_block(pos):
        raw = source[pos:]
        if raw.strip():
            text = html.unescape(raw)
            strings.append(text.strip())
            text_spans.append((pos, len(source), text.strip(), "text"))

    spans = attr_spans + text_spans
    unique = list(dict.fromkeys(s for s in strings if s.strip()))
    return unique, spans, json_spans


def call_openai(strings: list[str], lang: str, slug: str, api_key: str) -> dict[str, str]:
    if not strings:
        return {}
    prompt = {
        "target_locale": lang,
        "target_language": LANG_NAMES[lang],
        "slug": slug,
        "strings": strings,
    }
    system = (
        "You localize external promotional iOS answer pages for AEO/GEO. "
        "Return strict JSON with one object key 'translations' mapping every source string exactly to a native translation. "
        "Preserve HTML entities conceptually but output plain Unicode text. Preserve brand names and URLs. "
        f"Do not translate these brand/platform names: {', '.join(BRANDS)}. "
        "For Aim990/TOEIC content: preserve that Aim990 has a one-time unlock and no subscription. "
        "Never promise or guarantee a TOEIC score or improvement. Keep the disclaimer that Aim990 is an independent study aid, "
        "is not affiliated with or endorsed by ETS, and TOEIC is a trademark of ETS. "
        "Do not fabricate ratings, downloads, awards, or claims."
    )
    payload = {
        "model": "gpt-4o-mini",
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        "temperature": 0.2,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=data,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    last_error: Exception | None = None
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                raw = resp.read().decode("utf-8")
            content = json.loads(raw)["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            translations = parsed.get("translations", {})
            if not isinstance(translations, dict):
                raise ValueError("translations is not an object")
            return {str(k): str(v) for k, v in translations.items()}
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError) as exc:
            last_error = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"OpenAI translation failed for {slug} {lang}: {last_error}")


def string_batches(strings: list[str], max_chars: int = 900) -> list[list[str]]:
    batches: list[list[str]] = []
    current: list[str] = []
    size = 0
    for source in strings:
        if current and size + len(source) > max_chars:
            batches.append(current)
            current = []
            size = 0
        current.append(source)
        size += len(source)
    if current:
        batches.append(current)
    return batches


def call_ollama(
    strings: list[str], lang: str, slug: str, model: str = OLLAMA_MODEL
) -> dict[str, str]:
    translations: dict[str, str] = {}
    system = (
        "You are a native localization editor for external iOS app buying guides. "
        "Return one strict JSON object with a 'translations' object. Each input "
        "string must appear unchanged as a key, mapped to a fluent, culturally "
        f"natural {LANG_NAMES[lang]} translation. Preserve brand names, Apple "
        "product names, URLs, prices and factual caveats. Do not add claims, "
        "ratings, guarantees or commentary."
    )
    for batch_number, batch in enumerate(string_batches(strings), start=1):
        payload = {
            "model": model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "target_locale": lang,
                            "slug": slug,
                            "batch": batch_number,
                            "strings": batch,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "options": {"temperature": 0.1, "num_ctx": 8192},
        }
        request = urllib.request.Request(
            OLLAMA_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=300) as response:
                    raw = response.read().decode("utf-8")
                content = json.loads(raw)["message"]["content"]
                parsed = json.loads(content)
                mapped = parsed.get("translations", {})
                if not isinstance(mapped, dict):
                    raise ValueError("translations is not an object")
                exact = {source: str(mapped[source]) for source in batch}
                require_complete_mapping(batch, exact, slug, lang)
                translations.update(exact)
                break
            except (
                urllib.error.URLError,
                TimeoutError,
                json.JSONDecodeError,
                KeyError,
                ValueError,
            ) as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(2 * (attempt + 1))
        else:
            raise RuntimeError(
                f"Ollama translation failed for {slug} {lang} "
                f"batch {batch_number}: {last_error}"
            )
    return translations


APP_NAME_SUFFIXES = (" Pro", " Lite", " Plus")


@functools.cache
def portfolio_app_names() -> tuple[str, ...]:
    """Registry app names, longest first so "X Pro" wins over "X"."""
    social = str(Path(__file__).resolve().parent / ".." / "social")
    if social not in sys.path:
        sys.path.insert(0, social)
    from videogen.registry import APPS  # noqa: PLC0415 - optional dependency

    return tuple(
        sorted(
            {
                app["name"]
                for app in APPS.values()
                if len(app["name"]) >= 4
            },
            key=len,
            reverse=True,
        )
    )


def _app_name_base(name: str) -> str:
    changed = True
    while changed:
        changed = False
        for suffix in APP_NAME_SUFFIXES:
            if name.endswith(suffix):
                name = name[: -len(suffix)]
                changed = True
    return name


def portfolio_app_names_in(text: str) -> list[str]:
    """Names present in *text*, consuming each match so a longer name wins."""
    found: list[str] = []
    remaining = text
    for name in portfolio_app_names():
        # Case-sensitive on purpose: app names are proper nouns, and matching
        # loosely turns ordinary words into false hits (Spanish "sereno" is not
        # the Sereno app).
        pattern = re.compile(rf"(?<!\w){re.escape(name)}(?!\w)")
        if pattern.search(remaining):
            found.append(name)
            remaining = pattern.sub(" ", remaining)
    return found


def _same_app_family(name: str, bases: set[str]) -> bool:
    base = _app_name_base(name)
    return any(
        base == other
        or base.startswith(f"{other} ")
        or other.startswith(f"{base} ")
        for other in bases
    )


def cross_app_names_introduced(
    source: str,
    target: str,
    allowed_bases: set[str] | None = None,
) -> list[str]:
    """App names the translation adds that the English copy never names.

    A translation may legitimately keep, drop or reorder the app name it was
    given, and sibling editions (``X`` / ``X Pro``) count as the same family so
    a Pro/base slip is left to the publish-time answer gate.  What must never
    happen is an *unrelated* portfolio app appearing out of nowhere: that is a
    hallucinated recommendation, and it sends readers of one app's page to a
    different app.  Fail closed on it.

    ``allowed_bases`` carries the app families named anywhere in the English
    page, because a translator may name the page's own app in a sentence whose
    English original left it implicit -- that is a phrasing choice, not a
    hallucination.
    """
    bases = {_app_name_base(name) for name in portfolio_app_names_in(source)}
    if allowed_bases:
        bases |= allowed_bases
    return sorted(
        {
            name
            for name in portfolio_app_names_in(target)
            if not _same_app_family(name, bases)
        }
    )


def require_no_cross_app_translation(
    strings: list[str],
    mapping: dict[str, str],
    slug: str,
    lang: str,
) -> None:
    allowed_bases = {
        _app_name_base(name)
        for source in strings
        for name in portfolio_app_names_in(source)
    }
    injected = [
        (source, names)
        for source in strings
        for names in [
            cross_app_names_introduced(
                source,
                mapping.get(source, ""),
                allowed_bases,
            )
        ]
        if names
    ]
    if injected:
        raise ValueError(
            f"translation names an unrelated portfolio app in {slug} {lang}: "
            f"{injected[:3]}"
        )


def drop_cross_app_cache_poison(mapping: dict[str, str], origin: str) -> int:
    """Remove cached pairs whose translation names an app the source never named.

    One misaligned translation batch is enough to poison a shared dictionary
    forever (2026-08-30: ar-SA cached a CV Desk sentence under an unrelated
    English source), and every later run then dies in
    require_no_cross_app_translation before writing anything. Dropping the
    pair is always safe: the slot simply counts as untranslated again and a
    later pass re-translates it, while the page-level gate stays strict.
    """
    names = portfolio_app_names()
    if not names or not mapping:
        return 0
    quick = re.compile("|".join(re.escape(name) for name in names))
    poisoned = [
        source
        for source, target in mapping.items()
        if quick.search(target) and cross_app_names_introduced(source, target)
    ]
    for source in poisoned:
        del mapping[source]
    if poisoned:
        print(
            f"[i18n] {origin}: dropped {len(poisoned)} poisoned cached "
            "translation(s) naming an unrelated portfolio app",
            file=sys.stderr,
            flush=True,
        )
    return len(poisoned)


def require_complete_mapping(
    strings: list[str], mapping: dict[str, str], slug: str, lang: str
) -> None:
    missing = [source for source in strings if source not in mapping]
    empty = [source for source in strings if source in mapping and not mapping[source].strip()]
    if missing or empty:
        raise ValueError(
            f"incomplete translation for {slug} {lang}: "
            f"missing={len(missing)}, empty={len(empty)}"
        )


def require_translation_quality(
    strings: list[str],
    mapping: dict[str, str],
    slug: str,
    lang: str,
    allow_english: frozenset[str] | set[str] = frozenset(),
) -> None:
    """`allow_english`:--allow-partial 明確放行「維持原文」的字串(字典還沒有
    譯文,先照原文出頁、記進 _missing 待補)。品質檢查只管其餘字串,否則
    --allow-partial 永遠會在這裡炸掉,旗標形同虛設。"""
    require_no_cross_app_translation(strings, mapping, slug, lang)
    if lang in ENGLISH_LOCALES:
        return
    untranslated = []
    for source in strings:
        if source in allow_english:
            continue
        target = mapping.get(source, "").strip()
        if source.strip() != target:
            continue
        words = re.findall(r"[A-Za-z]+", source)
        protected_name = any(
            source == brand or source.startswith(f"{brand}:")
            for brand in BRANDS
        )
        if len(source) >= 24 and len(words) >= 4 and not protected_name:
            untranslated.append(source)
    if untranslated:
        raise ValueError(
            f"English fallback in {slug} {lang}: {untranslated[:3]}"
        )

    ranges = NATIVE_SCRIPT_RANGES.get(lang)
    if not ranges:
        return
    letters = [
        character
        for source in strings
        if source not in allow_english
        for character in mapping[source]
        if character.isalpha()
    ]
    native = sum(
        any(start <= ord(character) <= end for start, end in ranges)
        for character in letters
    )
    ratio = native / max(1, len(letters))
    if ratio < 0.70:
        raise ValueError(
            f"native-script ratio too low for {slug} {lang}: {ratio:.3f}"
        )


def apply_locale_text_overrides(
    mapping: dict[str, str],
    lang: str,
) -> dict[str, str]:
    overrides = LOCALE_TEXT_OVERRIDES.get(lang, {})
    out: dict[str, str] = {}
    for source, target in mapping.items():
        text = overrides.get(source, source if source in BRANDS else target)
        # The per-locale word table exists to nativise leftover English inside
        # an already translated sentence.  Running it over a sentence that is
        # still English yields half-translated copy ("One-time buka kunci"),
        # which reads worse than either language on its own -- so a string that
        # came back unchanged is left exactly as the English page had it.
        if text != source:
            text = apply_locale_target_replacements(text, lang)
        out[source] = text
    return out


def apply_locale_target_replacements(text: str, lang: str) -> str:
    for original, replacement in LOCALE_TARGET_REPLACEMENTS.get(lang, ()):
        text = text.replace(original, replacement)
    if lang == "th":
        text = re.sub(r"(?<!จู้ยิน \()Zhuyin", "จู้ยิน (Zhuyin)", text)
    if lang == "zh-Hant":
        text = re.sub(r"應用(?!程式|於|到)", "App", text)
    return text


def english_mapping(strings: list[str], locale: str) -> dict[str, str]:
    replacements = {
        "en-US": (
            ("practise", "practice"),
            ("recognise", "recognize"),
            ("recognising", "recognizing"),
            ("summarise", "summarize"),
            ("summarised", "summarized"),
            ("summarising", "summarizing"),
            ("colour", "color"),
            ("travelling", "traveling"),
        ),
        "en-CA": (
            ("practise", "practice"),
            ("recognise", "recognize"),
            ("recognising", "recognizing"),
            ("summarise", "summarize"),
            ("summarised", "summarized"),
            ("summarising", "summarizing"),
        ),
        "en-AU": (),
        "en-GB": (),
    }
    spelling = dict(replacements[locale])

    def replace(match: re.Match[str]) -> str:
        value = spelling[match.group(0).lower()]
        return value.capitalize() if match.group(0)[0].isupper() else value

    pattern = (
        r"\b(" + "|".join(map(re.escape, spelling)) + r")\b"
        if spelling
        else ""
    )
    return {
        source: re.sub(pattern, replace, source, flags=re.IGNORECASE)
        if pattern
        else source
        for source in strings
    }


def github_translation_batches(
    strings: list[str], max_chars: int = 24000
) -> list[list[str]]:
    return string_batches(strings, max_chars=max_chars)


class GithubModelsTranslator:
    def __init__(
        self,
        all_strings: list[str],
        model: str = GITHUB_TRANSLATION_MODEL,
        cache_dir: Path | None = None,
    ):
        token = subprocess.run(
            ["gh", "auth", "token"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if not token:
            raise RuntimeError("GitHub authentication token is unavailable")
        self.token = token
        self.model = model
        self.all_strings = list(dict.fromkeys(all_strings))
        self.cache: dict[str, dict[str, str]] = {}
        self.cache_dir = cache_dir
        if self.cache_dir is not None:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, locale: str) -> Path | None:
        if self.cache_dir is None:
            return None
        if locale not in ALL_LANGS:
            raise ValueError(f"Unsupported cache locale: {locale}")
        return self.cache_dir / f"{locale}.json"

    def _load_locale_cache(self, locale: str) -> dict[str, str]:
        path = self._cache_path(locale)
        if path is None or not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or any(
            not isinstance(source, str)
            or not isinstance(target, str)
            or not target.strip()
            for source, target in data.items()
        ):
            raise ValueError(f"Invalid GitHub Models cache: {path}")
        drop_cross_app_cache_poison(data, path.name)
        return data

    def _save_locale_cache(
        self,
        locale: str,
        mapping: dict[str, str],
    ) -> None:
        path = self._cache_path(locale)
        if path is None:
            return
        temporary = path.with_suffix(f".json.tmp.{os.getpid()}")
        temporary.write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)

    def _translate_batch(
        self,
        strings: list[str],
        locale: str,
        batch_number: str,
    ) -> dict[str, str]:
        items = [
            {"id": index, "text": source}
            for index, source in enumerate(strings)
        ]
        system = (
            "You are a senior native localization editor for external iOS app "
            "buying guides. Localize for the exact target locale, using that "
            "market's natural vocabulary and search phrasing rather than a "
            "literal translation. Preserve app brand names, iPhone, iOS, "
            "Home Screen, Apple Watch, App Store, URLs, prices, product facts "
            "and all factual caveats. Outside those exact protected names, "
            "write every ordinary word in the target language's native "
            "terminology and script; never code-switch or retain an English "
            "source phrase for convenience. Translate generic wording attached "
            "to a brand, including the words 'app guide' in '<brand> app "
            "guide'; only the brand itself is protected. Do not add claims, "
            "ratings, guarantees or commentary. Return strict JSON with one "
            "'translations' array. "
            "Each result must contain the same numeric id and one non-empty "
            "localized text. Return every id exactly once."
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "target_locale": locale,
                            "target_language": LANG_NAMES[locale],
                            "batch": batch_number,
                            "items": items,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "temperature": 0.1,
            "max_tokens": 32768,
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            GITHUB_MODELS_ENDPOINT,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2026-03-10",
            },
            method="POST",
        )
        last_error: Exception | None = None
        for attempt in range(5):
            try:
                with urllib.request.urlopen(request, timeout=300) as response:
                    raw = response.read().decode("utf-8")
            except (
                urllib.error.URLError,
                TimeoutError,
            ) as exc:
                last_error = exc
                headers = getattr(exc, "headers", None)
                retry_after = (
                    int(headers.get("Retry-After", "0") or 0)
                    if isinstance(exc, urllib.error.HTTPError)
                    and headers is not None
                    else 0
                )
                if attempt < 4:
                    time.sleep(max(retry_after, 4 * (attempt + 1)))
                continue
            try:
                content = json.loads(raw)["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                results = parsed.get("translations")
                if not isinstance(results, list):
                    raise ValueError("translations is not an array")
                by_id: dict[int, str] = {}
                for result in results:
                    if not isinstance(result, dict):
                        raise ValueError("translation result is not an object")
                    result_id = result.get("id")
                    if isinstance(result_id, str) and result_id.isdigit():
                        result_id = int(result_id)
                    text = next(
                        (
                            result.get(key)
                            for key in (
                                "text",
                                "localized_text",
                                "translation",
                            )
                            if isinstance(result.get(key), str)
                        ),
                        None,
                    )
                    if not isinstance(result_id, int) or not isinstance(text, str):
                        raise ValueError("translation result has invalid fields")
                    if result_id in by_id:
                        raise ValueError(f"duplicate translation id {result_id}")
                    by_id[result_id] = text.strip()
                expected = set(range(len(strings)))
                if set(by_id) != expected:
                    raise ValueError(
                        f"translation ids differ: expected={len(expected)}, "
                        f"actual={len(by_id)}"
                    )
                mapping = {
                    source: by_id[index]
                    for index, source in enumerate(strings)
                }
                require_complete_mapping(
                    strings,
                    mapping,
                    "persona-batch",
                    locale,
                )
                return mapping
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                last_error = exc
                break
        if len(strings) > 1:
            midpoint = len(strings) // 2
            left = self._translate_batch(
                strings[:midpoint],
                locale,
                f"{batch_number}a",
            )
            right = self._translate_batch(
                strings[midpoint:],
                locale,
                f"{batch_number}b",
            )
            return {**left, **right}
        raise RuntimeError(
            f"GitHub Models translation failed for {locale} "
            f"batch {batch_number}: {last_error}"
        )

    def translate(self, strings: list[str], locale: str) -> dict[str, str]:
        if locale not in self.cache:
            mapping = self._load_locale_cache(locale)
            missing = [
                source for source in self.all_strings if source not in mapping
            ]
            batches = github_translation_batches(missing)
            for batch_number, batch in enumerate(batches, start=1):
                print(
                    f"GitHub Models {locale}: batch {batch_number}/"
                    f"{len(batches)} ({len(batch)} strings)",
                    flush=True,
                )
                mapping.update(
                    self._translate_batch(
                        batch,
                        locale,
                        str(batch_number),
                    )
                )
                self._save_locale_cache(locale, mapping)
            require_complete_mapping(
                self.all_strings,
                mapping,
                "persona-pages",
                locale,
            )
            self.cache[locale] = mapping
        return {
            source: self.cache[locale][source]
            for source in strings
        }


def replace_spans(source: str, replacements: list[tuple[int, int, str]]) -> str:
    out = []
    last = 0
    for start, end, repl in sorted(replacements, key=lambda x: x[0]):
        out.append(source[last:start])
        out.append(repl)
        last = end
    out.append(source[last:])
    return "".join(out)


def alternates_html(slug: str, current_lang: str | None = None) -> str:
    lines = []
    english = ANSWERS / f"{slug}.html"
    if english.exists():
        lines.append(
            f'<link rel="alternate" hreflang="en" href="{page_url(slug)}">'
        )
    for code in ALL_LANGS:
        target = ROOT / code / "answers" / f"{slug}.html"
        if code == current_lang or target.exists():
            lines.append(
                f'<link rel="alternate" hreflang="{code}" '
                f'href="{page_url(slug, code)}">'
            )
    default = page_url(slug) if english.exists() else page_url(
        slug, current_lang
    )
    if default:
        lines.append(
            f'<link rel="alternate" hreflang="x-default" href="{default}">'
        )
    return "\n".join(lines)


def reconcile_alternates(
    path: Path,
    slug: str,
    current_lang: str | None = None,
) -> bool:
    if not path.exists():
        return False
    source = path.read_text(encoding="utf-8")
    updated = re.sub(
        r'(<link rel="alternate" hreflang="[^"]+" href="[^"]+">\s*)+',
        alternates_html(slug, current_lang) + "\n",
        source,
        count=1,
    )
    if updated == source:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def reconcile_english_alternates(slug: str) -> bool:
    return reconcile_alternates(ANSWERS / f"{slug}.html", slug)


def reconcile_all_alternates(slug: str) -> int:
    changed = int(reconcile_english_alternates(slug))
    for lang in ALL_LANGS:
        changed += int(
            reconcile_alternates(
                ROOT / lang / "answers" / f"{slug}.html",
                slug,
                lang,
            )
        )
    return changed


def localize_body_links(source: str, lang: str) -> str:
    def repl(m: re.Match[str]) -> str:
        return f'{m.group(1)}{localize_url(m.group(2), lang)}{m.group(3)}'

    source = re.sub(
        r'(<a\b[^>]*\bhref=")'
        r'(https://alice51849\.github\.io/ios-app-guide/[^"]+)(")',
        repl,
        source,
    )
    return re.sub(
        r'(<meta\b[^>]*\bhttp-equiv="refresh"[^>]*\bcontent="\d+;url=)'
        r'(https://alice51849\.github\.io/ios-app-guide/[^"]+)(")',
        repl,
        source,
        flags=re.I,
    )


RTL_LANGS = {"ar-SA", "he", "ur-PK", "fa"}


# --------------------------------------------------------------------------- #
# Locale-specific metadata frames (2026-08-17)
#
# Measurement (reports/geo_measure.py) found weighted duplicate_metadata_share
# ≈ 0.67: most localized answer pages still shipped a <title> and meta
# description byte-identical to the English original, because the translation
# cache never covered those strings and the renderer fell back to English.
# These frames guarantee every localized page gets locale-specific metadata
# that still carries the page-specific facts (the query and the recommended
# app), even when full body translation is unavailable. They intentionally
# describe only what the page really is — an answer plus honest app guidance —
# and never claim the body text is translated.
#
# ensure_locale_meta() is idempotent: it only rewrites pages whose <title>
# still matches the English answer-title pattern. It never touches robots
# meta, canonical/hreflang, body copy or JSON-LD.
# --------------------------------------------------------------------------- #
_EN_ANSWER_TITLE_RE = re.compile(
    r"^(?P<query>.+?):\s*honest iPhone app buying guide$", re.S
)
_TITLE_TAG_RE = re.compile(r"(<title>)(.*?)(</title>)", re.S)
_META_DESC_TAG_RE = re.compile(r'(<meta name="description" content=")(.*?)(")', re.S)
_OG_TITLE_TAG_RE = re.compile(r'(<meta property="og:title" content=")(.*?)(")', re.S)
_OG_DESC_TAG_RE = re.compile(
    r'(<meta property="og:description" content=")(.*?)(")', re.S
)
_OG_IMG_ALT_RE = re.compile(
    r'<meta property="og:image:alt" content="([^"]*?) iOS app preview"'
)

LOCALE_META_FRAMES: dict[str, dict[str, Any]] = {
    "ja": {
        "title": "{query}|iPhoneアプリの正直な購入ガイド",
        "desc_app": [
            "「{query}」への実践的な答え:{app} を例に、iPhoneでの解決手順と、"
            "誇張のないアプリの選び方をまとめた購入ガイドです。",
            "「{query}」で迷ったら:{app} を使った現実的な解決の流れと、"
            "支払う前に確認すべきポイントを正直に整理しました。",
        ],
        "desc": "「{query}」への実践的な答えと、iPhoneアプリの正直な選び方を"
        "まとめた購入ガイドです。",
    },
    "ko": {
        "title": "{query} | 정직한 iPhone 앱 구매 가이드",
        "desc_app": [
            "'{query}'에 대한 실용적인 답변: {app} 사례로 iPhone에서 해결하는 "
            "순서와 과장 없는 앱 선택 기준을 정리한 구매 가이드입니다.",
            "'{query}' 고민이라면: {app} 기반의 현실적인 해결 과정과 결제 전에 "
            "확인할 점을 정직하게 정리했습니다.",
        ],
        "desc": "'{query}'에 대한 실용적인 답변과 정직한 iPhone 앱 선택 "
        "기준을 정리한 구매 가이드입니다.",
    },
    "zh-Hant": {
        "title": "{query}|iPhone App 誠實選購指南",
        "desc_app": [
            "針對「{query}」的務實解法:以 {app} 為例,整理 iPhone 上的操作"
            "步驟,以及不誇大的 App 選購建議。",
            "「{query}」怎麼解?本頁以 {app} 示範實際流程,並誠實說明付費前"
            "該確認的重點。",
        ],
        "desc": "針對「{query}」的實用解答,以及不誇大的 iPhone App 選購"
        "建議。",
    },
    "zh-Hans": {
        "title": "{query}|iPhone 应用诚实选购指南",
        "desc_app": [
            "针对“{query}”的务实解法:以 {app} 为例,整理 iPhone 上的操作"
            "步骤,以及不夸大的应用选购建议。",
            "“{query}”怎么解决?本页以 {app} 演示实际流程,并诚实说明付费前"
            "该确认的要点。",
        ],
        "desc": "针对“{query}”的实用解答,以及不夸大的 iPhone 应用选购建议。",
    },
    "de-DE": {
        "title": "{query} – ehrlicher Kaufratgeber für iPhone-Apps",
        "desc_app": [
            "Praktische Antwort auf „{query}“: Schritt für Schritt auf dem "
            "iPhone gelöst – am Beispiel von {app}, ohne Übertreibung.",
            "„{query}“ – ein realistischer Lösungsweg mit {app} und ehrliche "
            "Hinweise, worauf Sie vor dem Kauf einer iPhone-App achten sollten.",
        ],
        "desc": "Praktische Antwort auf „{query}“ und ein ehrlicher Ratgeber "
        "für die Auswahl der passenden iPhone-App.",
    },
    "fr-FR": {
        "title": "{query} : guide d’achat transparent pour iPhone",
        "desc_app": [
            "Réponse concrète à « {query} » : la démarche pas à pas sur "
            "iPhone avec {app}, sans promesses exagérées.",
            "« {query} » : un parcours réaliste avec {app} et des conseils "
            "honnêtes sur ce qu’il faut vérifier avant de payer une app.",
        ],
        "desc": "Réponse concrète à « {query} » et conseils honnêtes pour "
        "choisir la bonne app iPhone.",
    },
    "fr-CA": {
        "title": "{query} : guide d’achat transparent pour iPhone",
        "desc_app": [
            "Réponse concrète à « {query} » : la démarche pas à pas sur "
            "iPhone avec {app}, sans promesses exagérées.",
        ],
        "desc": "Réponse concrète à « {query} » et conseils honnêtes pour "
        "choisir la bonne app iPhone.",
    },
    "es-ES": {
        "title": "{query}: guía honesta para elegir apps para iPhone",
        "desc_app": [
            "Respuesta práctica a «{query}»: cómo resolverlo en el iPhone con "
            "{app}, con consejos honestos y sin exageraciones.",
            "«{query}»: un recorrido realista con {app} y lo que conviene "
            "comprobar antes de pagar por una app.",
        ],
        "desc": "Respuesta práctica a «{query}» y consejos honestos para "
        "elegir la app de iPhone adecuada.",
    },
    "es-MX": {
        "title": "{query}: guía honesta para elegir apps de iPhone",
        "desc_app": [
            "Respuesta práctica a “{query}”: cómo resolverlo en el iPhone con "
            "{app}, con consejos honestos y sin exageraciones.",
        ],
        "desc": "Respuesta práctica a “{query}” y consejos honestos para "
        "elegir la app de iPhone adecuada.",
    },
    "pt-BR": {
        "title": "{query}: guia transparente para escolher apps para iPhone",
        "desc_app": [
            "Resposta prática para “{query}”: como resolver no iPhone com o "
            "{app}, com orientações honestas e sem exagero.",
            "“{query}” — um passo a passo realista com o {app} e o que "
            "conferir antes de pagar por um app.",
        ],
        "desc": "Resposta prática para “{query}” e orientações honestas para "
        "escolher o app de iPhone certo.",
    },
    "pt-PT": {
        "title": "{query}: guia transparente para escolher aplicações para iPhone",
        "desc_app": [
            "Resposta prática a “{query}”: como resolver no iPhone com a "
            "{app}, com conselhos honestos e sem exageros.",
            "“{query}” — um percurso realista com a {app} e o que confirmar "
            "antes de pagar por uma aplicação.",
        ],
        "desc": "Resposta prática a “{query}” e conselhos honestos para "
        "escolher a aplicação de iPhone certa.",
    },
    "it": {
        "title": "{query}: guida trasparente all’acquisto di app per iPhone",
        "desc_app": [
            "Risposta pratica a «{query}»: come risolvere su iPhone con "
            "{app}, con consigli onesti e senza esagerazioni.",
        ],
        "desc": "Risposta pratica a «{query}» e consigli onesti per scegliere "
        "l’app per iPhone giusta.",
    },
    "tr": {
        "title": "{query} – iPhone uygulamaları için dürüst satın alma rehberi",
        "desc_app": [
            "“{query}” için pratik yanıt: {app} örneğiyle iPhone’da adım adım "
            "çözüm ve abartısız, dürüst uygulama seçme önerileri.",
            "“{query}” sorusuna gerçekçi bir çözüm yolu: {app} ile uygulamalı "
            "adımlar ve ödeme yapmadan önce kontrol edilmesi gerekenler.",
        ],
        "desc": "“{query}” için pratik yanıt ve doğru iPhone uygulamasını "
        "seçmek için dürüst öneriler.",
    },
    "id": {
        "title": "{query} – panduan jujur memilih aplikasi iPhone",
        "desc_app": [
            "Jawaban praktis untuk “{query}”: langkah penyelesaian di iPhone "
            "dengan contoh {app}, plus saran jujur tanpa melebih-lebihkan.",
            "“{query}” — alur penyelesaian yang realistis dengan {app} dan "
            "hal yang perlu dicek sebelum membayar sebuah aplikasi.",
        ],
        "desc": "Jawaban praktis untuk “{query}” dan saran jujur memilih "
        "aplikasi iPhone yang tepat.",
    },
    "ms": {
        "title": "{query} – panduan jujur memilih aplikasi iPhone",
        "desc_app": [
            "Jawapan praktikal untuk “{query}”: langkah penyelesaian di "
            "iPhone dengan contoh {app}, serta panduan jujur tanpa "
            "berlebih-lebihan.",
            "“{query}” — laluan penyelesaian yang realistik dengan {app} dan "
            "perkara yang perlu disemak sebelum membayar sesebuah aplikasi.",
        ],
        "desc": "Jawapan praktikal untuk “{query}” dan panduan jujur memilih "
        "aplikasi iPhone yang sesuai.",
    },
    "vi": {
        "title": "{query} – cẩm nang chọn ứng dụng iPhone trung thực",
        "desc_app": [
            "Câu trả lời thiết thực cho “{query}”: cách xử lý trên iPhone với "
            "{app}, kèm lời khuyên trung thực, không phóng đại.",
            "“{query}” — quy trình giải quyết thực tế với {app} và những điều "
            "nên kiểm tra trước khi trả tiền cho một ứng dụng.",
        ],
        "desc": "Câu trả lời thiết thực cho “{query}” và lời khuyên trung "
        "thực để chọn đúng ứng dụng iPhone.",
    },
    "th": {
        "title": "{query} – คู่มือเลือกแอป iPhone อย่างตรงไปตรงมา",
        "desc_app": [
            "คำตอบที่ใช้ได้จริงสำหรับ “{query}”: วิธีจัดการบน iPhone โดยใช้ {app} "
            "พร้อมคำแนะนำแบบตรงไปตรงมา ไม่เกินจริง",
            "“{query}” — แนวทางแก้ปัญหาที่เป็นจริงด้วย {app} และสิ่งที่ควรตรวจสอบ"
            "ก่อนจ่ายเงินซื้อแอป",
        ],
        "desc": "คำตอบที่ใช้ได้จริงสำหรับ “{query}” พร้อมคำแนะนำเลือกแอป iPhone "
        "อย่างตรงไปตรงมา",
    },
    "ar-SA": {
        "title": "{query} – دليل صادق لاختيار تطبيقات iPhone",
        "desc_app": [
            "إجابة عملية عن «{query}»: خطوات الحل على iPhone بمثال {app}، مع "
            "نصائح صادقة من دون مبالغة.",
            "«{query}» — مسار حل واقعي مع {app} وما ينبغي التحقق منه قبل الدفع "
            "مقابل أي تطبيق.",
        ],
        "desc": "إجابة عملية عن «{query}» ونصائح صادقة لاختيار تطبيق iPhone "
        "المناسب.",
    },
    "ru": {
        "title": "{query} — честный гид по выбору приложений для iPhone",
        "desc_app": [
            "Практичный ответ на запрос «{query}»: как решить задачу на "
            "iPhone на примере {app}, с честными советами без преувеличений.",
        ],
        "desc": "Практичный ответ на запрос «{query}» и честные советы по "
        "выбору подходящего приложения для iPhone.",
    },
    "uk": {
        "title": "{query} — чесний гід із вибору застосунків для iPhone",
        "desc_app": [
            "Практична відповідь на «{query}»: як розв’язати задачу на iPhone "
            "на прикладі {app}, з чесними порадами без перебільшень.",
        ],
        "desc": "Практична відповідь на «{query}» та чесні поради з вибору "
        "застосунку для iPhone.",
    },
    "pl": {
        "title": "{query} — szczery przewodnik po wyborze aplikacji na iPhone’a",
        "desc_app": [
            "Praktyczna odpowiedź na „{query}”: jak rozwiązać to na iPhonie "
            "na przykładzie {app}, ze szczerymi wskazówkami bez przesady.",
        ],
        "desc": "Praktyczna odpowiedź na „{query}” i szczere wskazówki, jak "
        "wybrać właściwą aplikację na iPhone’a.",
    },
    "nl-NL": {
        "title": "{query} – eerlijke koopgids voor iPhone-apps",
        "desc_app": [
            "Praktisch antwoord op “{query}”: stap voor stap opgelost op de "
            "iPhone met {app}, met eerlijk advies zonder overdrijving.",
        ],
        "desc": "Praktisch antwoord op “{query}” en eerlijk advies om de "
        "juiste iPhone-app te kiezen.",
    },
    "sv": {
        "title": "{query} – ärlig guide för att välja iPhone-appar",
        "desc_app": [
            "Praktiskt svar på ”{query}”: så löser du det på iPhone med "
            "{app}, med ärliga råd utan överdrifter.",
        ],
        "desc": "Praktiskt svar på ”{query}” och ärliga råd för att välja "
        "rätt iPhone-app.",
    },
    "da": {
        "title": "{query} – ærlig guide til valg af iPhone-apps",
        "desc_app": [
            "Praktisk svar på “{query}”: sådan løser du det på iPhone med "
            "{app}, med ærlige råd uden overdrivelser.",
        ],
        "desc": "Praktisk svar på “{query}” og ærlige råd til at vælge den "
        "rigtige iPhone-app.",
    },
    "no": {
        "title": "{query} – ærlig guide til valg av iPhone-apper",
        "desc_app": [
            "Praktisk svar på «{query}»: slik løser du det på iPhone med "
            "{app}, med ærlige råd uten overdrivelser.",
        ],
        "desc": "Praktisk svar på «{query}» og ærlige råd for å velge riktig "
        "iPhone-app.",
    },
    "fi": {
        "title": "{query} – rehellinen opas iPhone-sovellusten valintaan",
        "desc_app": [
            "Käytännön vastaus kysymykseen ”{query}”: näin ratkaiset sen "
            "iPhonella {app}-sovelluksen avulla, rehellisin neuvoin.",
        ],
        "desc": "Käytännön vastaus kysymykseen ”{query}” ja rehelliset neuvot "
        "oikean iPhone-sovelluksen valintaan.",
    },
    "cs": {
        "title": "{query} – upřímný průvodce výběrem aplikací pro iPhone",
        "desc_app": [
            "Praktická odpověď na „{query}“: jak to vyřešit na iPhonu na "
            "příkladu aplikace {app}, s upřímnými radami bez přehánění.",
        ],
        "desc": "Praktická odpověď na „{query}“ a upřímné rady, jak vybrat "
        "správnou aplikaci pro iPhone.",
    },
    "sk": {
        "title": "{query} – úprimný sprievodca výberom aplikácií pre iPhone",
        "desc_app": [
            "Praktická odpoveď na „{query}“: ako to vyriešiť na iPhone na "
            "príklade aplikácie {app}, s úprimnými radami bez preháňania.",
        ],
        "desc": "Praktická odpoveď na „{query}“ a úprimné rady, ako vybrať "
        "správnu aplikáciu pre iPhone.",
    },
    "hu": {
        "title": "{query} – őszinte útmutató iPhone-alkalmazások kiválasztásához",
        "desc_app": [
            "Gyakorlati válasz erre: „{query}” – így oldható meg iPhone-on a "
            "{app} példáján, őszinte tanácsokkal, túlzások nélkül.",
        ],
        "desc": "Gyakorlati válasz erre: „{query}”, valamint őszinte tanácsok "
        "a megfelelő iPhone-alkalmazás kiválasztásához.",
    },
    "ro": {
        "title": "{query} – ghid onest pentru alegerea aplicațiilor de iPhone",
        "desc_app": [
            "Răspuns practic la „{query}”: cum rezolvi pe iPhone cu {app}, "
            "cu sfaturi oneste, fără exagerări.",
        ],
        "desc": "Răspuns practic la „{query}” și sfaturi oneste pentru a "
        "alege aplicația de iPhone potrivită.",
    },
    "el": {
        "title": "{query} – ειλικρινής οδηγός επιλογής εφαρμογών iPhone",
        "desc_app": [
            "Πρακτική απάντηση στο «{query}»: πώς να το λύσετε στο iPhone με "
            "το {app}, με ειλικρινείς συμβουλές χωρίς υπερβολές.",
        ],
        "desc": "Πρακτική απάντηση στο «{query}» και ειλικρινείς συμβουλές "
        "για να επιλέξετε τη σωστή εφαρμογή iPhone.",
    },
    "he": {
        "title": "{query} – מדריך כן לבחירת אפליקציות iPhone",
        "desc_app": [
            "תשובה מעשית ל‑“{query}”: איך פותרים זאת ב‑iPhone בעזרת {app}, עם "
            "עצות כנות וללא הגזמות.",
        ],
        "desc": "תשובה מעשית ל‑“{query}” ועצות כנות לבחירת אפליקציית iPhone "
        "מתאימה.",
    },
    "hr": {
        "title": "{query} – iskren vodič za odabir iPhone aplikacija",
        "desc_app": [
            "Praktičan odgovor na „{query}”: kako to riješiti na iPhoneu na "
            "primjeru aplikacije {app}, uz iskrene savjete bez pretjerivanja.",
        ],
        "desc": "Praktičan odgovor na „{query}” i iskreni savjeti za odabir "
        "prave iPhone aplikacije.",
    },
    "sl-SI": {
        "title": "{query} – iskren vodnik za izbiro aplikacij za iPhone",
        "desc_app": [
            "Praktičen odgovor na »{query}«: kako to rešiti na iPhonu na "
            "primeru aplikacije {app}, z iskrenimi nasveti brez pretiravanja.",
        ],
        "desc": "Praktičen odgovor na »{query}« in iskreni nasveti za izbiro "
        "prave aplikacije za iPhone.",
    },
    "ca": {
        "title": "{query}: guia honesta per triar apps per a iPhone",
        "desc_app": [
            "Resposta pràctica a «{query}»: com resoldre-ho a l’iPhone amb "
            "{app}, amb consells honestos i sense exageracions.",
        ],
        "desc": "Resposta pràctica a «{query}» i consells honestos per triar "
        "l’app d’iPhone adequada.",
    },
    "hi": {
        "title": "{query} – iPhone ऐप चुनने की ईमानदार गाइड",
        "desc_app": [
            "“{query}” का व्यावहारिक जवाब: {app} के उदाहरण से iPhone पर समाधान "
            "के चरण, बिना बढ़ा-चढ़ाकर ईमानदार सलाह के साथ।",
        ],
        "desc": "“{query}” का व्यावहारिक जवाब और सही iPhone ऐप चुनने की "
        "ईमानदार सलाह।",
    },
    "bn-BD": {
        "title": "{query} – iPhone অ্যাপ বাছাইয়ের সৎ গাইড",
        "desc_app": [
            "“{query}”-এর ব্যবহারিক উত্তর: {app}-এর উদাহরণে iPhone-এ সমাধানের "
            "ধাপ, অতিরঞ্জন ছাড়া সৎ পরামর্শসহ।",
        ],
        "desc": "“{query}”-এর ব্যবহারিক উত্তর এবং সঠিক iPhone অ্যাপ বাছাইয়ের "
        "সৎ পরামর্শ।",
    },
    "gu-IN": {
        "title": "{query} – iPhone એપ પસંદ કરવાની પ્રામાણિક માર્ગદર્શિકા",
        "desc_app": [
            "“{query}”નો વ્યવહારુ જવાબ: {app}ના ઉદાહરણ સાથે iPhone પર ઉકેલનાં "
            "પગલાં, અતિશયોક્તિ વિનાની પ્રામાણિક સલાહ સાથે.",
        ],
        "desc": "“{query}”નો વ્યવહારુ જવાબ અને યોગ્ય iPhone એપ પસંદ કરવાની "
        "પ્રામાણિક સલાહ.",
    },
    "kn-IN": {
        "title": "{query} – iPhone ಆ್ಯಪ್ ಆಯ್ಕೆಗೆ ಪ್ರಾಮಾಣಿಕ ಮಾರ್ಗದರ್ಶಿ",
        "desc_app": [
            "“{query}”ಗೆ ಪ್ರಾಯೋಗಿಕ ಉತ್ತರ: {app} ಉದಾಹರಣೆಯೊಂದಿಗೆ iPhone ನಲ್ಲಿ "
            "ಪರಿಹಾರದ ಹಂತಗಳು, ಉತ್ಪ್ರೇಕ್ಷೆ ಇಲ್ಲದ ಪ್ರಾಮಾಣಿಕ ಸಲಹೆಗಳೊಂದಿಗೆ.",
        ],
        "desc": "“{query}”ಗೆ ಪ್ರಾಯೋಗಿಕ ಉತ್ತರ ಮತ್ತು ಸರಿಯಾದ iPhone ಆ್ಯಪ್ "
        "ಆಯ್ಕೆಗೆ ಪ್ರಾಮಾಣಿಕ ಸಲಹೆ.",
    },
    "ml-IN": {
        "title": "{query} – iPhone ആപ്പ് തിരഞ്ഞെടുക്കാനുള്ള സത്യസന്ധമായ ഗൈഡ്",
        "desc_app": [
            "“{query}”-ന് പ്രായോഗിക ഉത്തരം: {app} ഉദാഹരണമാക്കി iPhone-ൽ "
            "പരിഹാരത്തിന്റെ ഘട്ടങ്ങൾ, അതിശയോക്തിയില്ലാത്ത സത്യസന്ധമായ നിർദേശങ്ങളോടെ.",
        ],
        "desc": "“{query}”-ന് പ്രായോഗിക ഉത്തരവും ശരിയായ iPhone ആപ്പ് "
        "തിരഞ്ഞെടുക്കാനുള്ള സത്യസന്ധമായ നിർദേശങ്ങളും.",
    },
    "mr-IN": {
        "title": "{query} – iPhone अ‍ॅप निवडीसाठी प्रामाणिक मार्गदर्शक",
        "desc_app": [
            "“{query}”चे व्यावहारिक उत्तर: {app}च्या उदाहरणासह iPhone वर "
            "समाधानाच्या पायऱ्या, अतिशयोक्तीशिवाय प्रामाणिक सल्ल्यांसह.",
        ],
        "desc": "“{query}”चे व्यावहारिक उत्तर आणि योग्य iPhone अ‍ॅप निवडण्यासाठी "
        "प्रामाणिक सल्ला.",
    },
    "or-IN": {
        "title": "{query} – iPhone ଆପ୍ ବାଛିବା ପାଇଁ ସଚ୍ଚୋଟ ଗାଇଡ୍",
        "desc_app": [
            "“{query}”ର ବ୍ୟାବହାରିକ ଉତ୍ତର: {app}ର ଉଦାହରଣ ସହିତ iPhoneରେ ସମାଧାନର "
            "ପଦକ୍ଷେପ, ଅତିରଞ୍ଜନ ବିନା ସଚ୍ଚୋଟ ପରାମର୍ଶ ସହିତ।",
        ],
        "desc": "“{query}”ର ବ୍ୟାବହାରିକ ଉତ୍ତର ଏବଂ ଠିକ୍ iPhone ଆପ୍ ବାଛିବା ପାଇଁ "
        "ସଚ୍ଚୋଟ ପରାମର୍ଶ।",
    },
    "pa-IN": {
        "title": "{query} – iPhone ਐਪ ਚੁਣਨ ਲਈ ਇਮਾਨਦਾਰ ਗਾਈਡ",
        "desc_app": [
            "“{query}” ਦਾ ਵਿਹਾਰਕ ਜਵਾਬ: {app} ਦੀ ਉਦਾਹਰਣ ਨਾਲ iPhone ’ਤੇ ਹੱਲ ਦੇ "
            "ਕਦਮ, ਬਿਨਾਂ ਵਧਾ-ਚੜ੍ਹਾਅ ਇਮਾਨਦਾਰ ਸਲਾਹ ਸਮੇਤ।",
        ],
        "desc": "“{query}” ਦਾ ਵਿਹਾਰਕ ਜਵਾਬ ਅਤੇ ਸਹੀ iPhone ਐਪ ਚੁਣਨ ਲਈ ਇਮਾਨਦਾਰ "
        "ਸਲਾਹ।",
    },
    "ta-IN": {
        "title": "{query} – iPhone ஆப் தேர்வுக்கான நேர்மையான வழிகாட்டி",
        "desc_app": [
            "“{query}”க்கு நடைமுறை பதில்: {app} உதாரணத்துடன் iPhone-இல் தீர்வு "
            "படிகள், மிகைப்படுத்தல் இல்லாத நேர்மையான அறிவுரையுடன்.",
        ],
        "desc": "“{query}”க்கு நடைமுறை பதிலும், சரியான iPhone ஆப்பைத் "
        "தேர்ந்தெடுக்க நேர்மையான அறிவுரையும்.",
    },
    "te-IN": {
        "title": "{query} – iPhone యాప్ ఎంపికకు నిజాయితీ గైడ్",
        "desc_app": [
            "“{query}”కి ఆచరణాత్మక సమాధానం: {app} ఉదాహరణతో iPhone లో పరిష్కార "
            "దశలు, అతిశయోక్తి లేని నిజాయితీ సూచనలతో.",
        ],
        "desc": "“{query}”కి ఆచరణాత్మక సమాధానం మరియు సరైన iPhone యాప్ "
        "ఎంపికకు నిజాయితీ సూచనలు.",
    },
    "ur-PK": {
        "title": "{query} – iPhone ایپ منتخب کرنے کی دیانت دار گائیڈ",
        "desc_app": [
            "”{query}“ کا عملی جواب: {app} کی مثال کے ساتھ iPhone پر حل کے "
            "مراحل، مبالغے کے بغیر دیانت دار مشوروں کے ساتھ۔",
        ],
        "desc": "”{query}“ کا عملی جواب اور درست iPhone ایپ منتخب کرنے کے "
        "لیے دیانت دار مشورے۔",
    },
    "bg": {
        "title": "{query} – честен наръчник за избор на iPhone приложения",
        "desc_app": [
            "Практичен отговор на „{query}“: как да го решите на iPhone с "
            "{app}, с честни съвети без преувеличения.",
        ],
        "desc": "Практичен отговор на „{query}“ и честни съвети за избор на "
        "подходящото iPhone приложение.",
    },
    # English storefront variants: keep the page-specific description and add
    # a truthful, region-specific frame so metadata is no longer byte-identical
    # to the base English page.
    "en-GB": {
        "title": "{query}: honest iPhone app buying guide for UK users",
        "desc_append": " For iPhone users in the UK.",
    },
    "en-AU": {
        "title": "{query}: honest iPhone app buying guide for Australian users",
        "desc_append": " For iPhone users in Australia.",
    },
    "en-CA": {
        "title": "{query}: honest iPhone app buying guide for Canadian users",
        "desc_append": " For iPhone users in Canada.",
    },
    "en-US": {
        "title": "{query}: honest iPhone app buying guide for US users",
        "desc_append": " For iPhone users in the United States.",
    },
}

# Directory aliases seen under pages/ that should reuse an existing frame.
_META_FRAME_ALIASES = {
    "zh-CN": "zh-Hans",
    "nb-NO": "no",
}
_META_FRAME_BASE_INDEX: dict[str, str] = {}
for _key in LOCALE_META_FRAMES:
    _META_FRAME_BASE_INDEX.setdefault(_key.split("-")[0], _key)


def resolve_meta_frames(lang: str) -> dict[str, Any] | None:
    frames = LOCALE_META_FRAMES.get(lang)
    if frames:
        return frames
    alias = _META_FRAME_ALIASES.get(lang)
    if alias:
        return LOCALE_META_FRAMES.get(alias)
    return LOCALE_META_FRAMES.get(
        _META_FRAME_BASE_INDEX.get(lang.split("-")[0], "")
    )


_H1_TAG_RE = re.compile(r"<h1\b[^>]*>(.*?)</h1>", re.S | re.I)


@functools.lru_cache(maxsize=None)
def english_meta_description(slug: str) -> str:
    """The meta description on the English source page for this slug."""
    path = ANSWERS / f"{slug}.html"
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    match = _META_DESC_TAG_RE.search(source)
    return html.unescape(match.group(2)).strip() if match else ""


def repair_locale_description(source: str, lang: str, slug: str) -> str:
    """Re-localize a description that fell back to English on a translated page.

    ``run_refresh`` rebuilds a page from the English source plus the current
    dictionary, which silently drops a description that the meta-only sweep had
    written earlier: the title and body come out localized while the
    description reverts to the English one.  This repairs exactly that case --
    the title is already localized (so ``ensure_locale_meta`` skips the page)
    but the description is still byte-identical to the English page's.  The
    localized ``<h1>`` supplies the query slot, so the rebuilt description is in
    the same words the reader already sees as the headline.
    """
    frames = resolve_meta_frames(lang)
    desc_match = _META_DESC_TAG_RE.search(source)
    if not frames or not desc_match:
        return source
    old_desc = html.unescape(desc_match.group(2)).strip()
    english = english_meta_description(slug)
    if not english or old_desc != english:
        return source
    h1_match = _H1_TAG_RE.search(source)
    if not h1_match:
        return source
    query = html.unescape(re.sub(r"<.*?>", "", h1_match.group(1))).strip()
    if not query:
        return source
    app_match = _OG_IMG_ALT_RE.search(source)
    app = html.unescape(app_match.group(1)).strip() if app_match else ""

    if "desc_append" in frames:
        new_desc = query + frames["desc_append"]
    else:
        variants = frames["desc_app"] if app else [frames["desc"]]
        digest = hashlib.sha1(slug.encode("utf-8")).hexdigest()
        new_desc = variants[int(digest[:8], 16) % len(variants)].format(
            query=query, app=app
        )
    desc_attr = html.escape(new_desc, quote=True)
    source = _META_DESC_TAG_RE.sub(
        lambda m: m.group(1) + desc_attr + m.group(3), source, count=1
    )
    source = _OG_DESC_TAG_RE.sub(
        lambda m: m.group(1) + desc_attr + m.group(3), source, count=1
    )
    return source


def ensure_locale_meta(source: str, lang: str, slug: str) -> str:
    """Give a localized page locale-specific <title>/description metadata.

    Only fires while the <title> still matches the English answer-title
    pattern (i.e. translation fell back to English), so a properly translated
    page is left untouched and the rewrite is idempotent.
    """
    frames = resolve_meta_frames(lang)
    if not frames:
        return source
    title_match = _TITLE_TAG_RE.search(source)
    if not title_match:
        return source
    title = html.unescape(title_match.group(2)).strip()
    query_match = _EN_ANSWER_TITLE_RE.match(title)
    if not query_match:
        return source
    query = query_match.group("query").strip()
    app_match = _OG_IMG_ALT_RE.search(source)
    app = html.unescape(app_match.group(1)).strip() if app_match else ""
    desc_match = _META_DESC_TAG_RE.search(source)
    old_desc = html.unescape(desc_match.group(2)).strip() if desc_match else ""

    new_title = frames["title"].format(query=query)
    if "desc_append" in frames:
        new_desc = (
            old_desc + frames["desc_append"] if old_desc else new_title
        )
    else:
        variants = frames["desc_app"] if app else [frames["desc"]]
        digest = hashlib.sha1(slug.encode("utf-8")).hexdigest()
        new_desc = variants[int(digest[:8], 16) % len(variants)].format(
            query=query, app=app
        )

    title_text = html.escape(new_title, quote=False)
    title_attr = html.escape(new_title, quote=True)
    desc_attr = html.escape(new_desc, quote=True)
    source = _TITLE_TAG_RE.sub(
        lambda m: m.group(1) + title_text + m.group(3), source, count=1
    )
    if desc_match:
        source = _META_DESC_TAG_RE.sub(
            lambda m: m.group(1) + desc_attr + m.group(3), source, count=1
        )
    source = _OG_TITLE_TAG_RE.sub(
        lambda m: m.group(1) + title_attr + m.group(3), source, count=1
    )
    source = _OG_DESC_TAG_RE.sub(
        lambda m: m.group(1) + desc_attr + m.group(3), source, count=1
    )
    return source


def run_meta_only(langs: list[str] | None = None) -> int:
    """Sweep existing localized answer pages, fixing English-fallback metadata.

    Never touches robots meta, body copy, canonical/hreflang or JSON-LD, and
    never rewrites a page whose metadata is already localized.
    """
    changed = scanned = 0
    locale_dirs = (
        [ROOT / lang for lang in langs]
        if langs
        else sorted(
            p
            for p in ROOT.iterdir()
            if p.is_dir()
            and re.fullmatch(r"[a-z]{2,3}(-[A-Za-z]{2,4})?", p.name)
            and p.name != "en"
        )
    )
    for locale_dir in locale_dirs:
        answers_dir = locale_dir / "answers"
        if not answers_dir.is_dir():
            continue
        lang = locale_dir.name
        if not resolve_meta_frames(lang):
            continue
        for path in sorted(answers_dir.glob("*.html")):
            scanned += 1
            source = path.read_text(encoding="utf-8")
            updated = ensure_locale_meta(source, lang, path.stem)
            updated = repair_locale_description(updated, lang, path.stem)
            if updated != source:
                path.write_text(updated, encoding="utf-8")
                changed += 1
    print(json.dumps({"scanned": scanned, "changed": changed}), flush=True)
    return 0


def reconcile_microformat_url(source: str, lang: str, slug: str) -> str:
    """Keep the hidden h-entry URL aligned with the localized canonical."""
    if "<!-- answer-microformat:start -->" not in source:
        return source
    expected = html.escape(page_url(slug, lang), quote=True)
    pattern = re.compile(
        r'(<data class="u-url u-uid" value=")[^"]+("></data>)'
    )
    updated, count = pattern.subn(
        lambda match: f"{match.group(1)}{expected}{match.group(2)}",
        source,
        count=1,
    )
    if count != 1:
        raise ValueError(
            f"Localized Answer microformat must contain one u-url/u-uid: "
            f"{lang}/{slug}"
        )
    return updated


def finalize_html(source: str, lang: str, slug: str) -> str:
    dir_attr = ' dir="rtl"' if lang in RTL_LANGS else ""
    source = re.sub(r'<html\s+lang="[^"]+"(?:\s+dir="[^"]+")?',
                    f'<html lang="{BASE_LANG[lang]}"{dir_attr}', source, count=1)
    source = re.sub(
        r'<link rel="canonical" href="[^"]+">',
        f'<link rel="canonical" href="{page_url(slug, lang)}">',
        source,
        count=1,
    )
    source = re.sub(
        r'(<link rel="alternate" hreflang="[^"]+" href="[^"]+">\s*)+',
        alternates_html(slug, lang) + "\n",
        source,
        count=1,
    )
    source = re.sub(
        r'(<meta property="og:url" content=")[^"]+(")',
        rf'\1{page_url(slug, lang)}\2',
        source,
        count=1,
    )
    source = reconcile_microformat_url(source, lang, slug)
    source = reconcile_structured_data_urls(source, lang, slug)
    if lang in RTL_LANGS:
        source = source.replace("→", "←")
    source = localize_body_links(source, lang)
    # Metadata must never fall back to the byte-identical English title/
    # description (duplicate_metadata_share); frames only fire when the
    # translation mapping left the English title in place.
    return ensure_locale_meta(source, lang, slug)


def render_localized(
    source: str,
    lang: str,
    slug: str,
    mapping: dict[str, str],
    *,
    strings: list[str] | None = None,
    spans: list[tuple[int, int, str, str]] | None = None,
    json_spans: list[tuple[int, int, str]] | None = None,
) -> str:
    parsed = (strings, spans, json_spans)
    if all(value is None for value in parsed):
        strings, spans, json_spans = extract_strings(source)
    elif any(value is None for value in parsed):
        raise ValueError(
            "render_localized requires strings, spans and json_spans together"
        )

    replacements: list[tuple[int, int, str]] = []
    for start, end, original, kind in spans:
        translated = mapping.get(original, original)
        escaped = html.escape(translated, quote=(kind == "content"))
        if kind == "text":
            raw = source[start:end]
            leading = re.match(r"\s*", raw).group(0)
            trailing = re.search(r"\s*$", raw).group(0)
            escaped = f"{leading}{escaped}{trailing}"
        replacements.append((start, end, escaped))

    for start, end, raw in json_spans:
        obj = json.loads(raw)
        obj = apply_json_mapping(obj, mapping)
        obj = update_json_language(obj, lang)
        obj = update_breadcrumb_urls(obj, lang, slug)
        replacements.append((start, end, "\n" + json.dumps(obj, ensure_ascii=False, indent=2) + "\n"))

    localized = replace_spans(source, replacements)
    return finalize_html(localized, lang, slug)


def _untranslated_ratio(strings: list[str], mapping: dict[str, str]) -> float:
    """Share of visible characters that are still byte-identical to English."""
    total = sum(len(x) for x in strings)
    if not total:
        return 0.0
    same = sum(
        len(x) for x in strings if mapping.get(x, x).strip() == x.strip()
    )
    return same / total


def _existing_untranslated_ratio(existing: str, english_strings: list[str]) -> float:
    """Same basis as _untranslated_ratio: share of the *English source* char
    mass that still shows up verbatim in the already-published localized page.
    Measuring both sides against the English strings keeps the comparison fair
    for languages whose translations are much shorter than English (CJK).
    """
    total = sum(len(x) for x in english_strings)
    if not total:
        return 1.0
    present = set(extract_strings(existing)[0])
    same = sum(len(x) for x in english_strings if x in present)
    return same / total


def run_refresh(
    langs: list[str],
    trans_dir: str,
    limit: int | None = None,
    min_gain: float = 0.01,
    slugs: list[str] | None = None,
) -> int:
    """Re-localize *already generated* answer pages after the dictionaries grew.

    discover_slugs() only ever finds slugs that have no localized page yet, so
    once a page exists it is frozen at whatever coverage the dictionary had on
    the day it was written -- which is why thousands of pages sit at ~25% body
    localization.  This mode walks the existing pages instead and rewrites one
    only when the current dictionary demonstrably localizes *more* of it
    (min_gain of the visible characters).  A page can therefore never be made
    worse, and the pass is safe to interrupt and resume.
    """
    global_maps: dict[str, dict[str, str]] = {}
    for lang in langs:
        gp = Path(trans_dir) / f"{lang}.json"
        global_maps[lang] = (
            json.loads(gp.read_text(encoding="utf-8")) if gp.exists() else {}
        )
        drop_cross_app_cache_poison(global_maps[lang], gp.name)

    if slugs:
        candidates = [Path(x).stem for x in slugs]
    else:
        candidates = sorted(
            q.stem for q in ANSWERS.glob("*.html") if q.name != "index.html"
        )

    improved = unchanged = failed = 0
    touched_slugs: list[str] = []
    for slug in candidates:
        src_path = ANSWERS / f"{slug}.html"
        if not src_path.exists():
            continue
        source = src_path.read_text(encoding="utf-8")
        strings, spans, json_spans = extract_strings(source)
        slug_touched = False
        for lang in langs:
            if lang in ENGLISH_LOCALES:
                continue
            target = ROOT / lang / "answers" / f"{slug}.html"
            if not target.exists():
                continue
            gm = global_maps[lang]
            mapping = {x: gm.get(x, x) for x in strings}
            mapping = apply_locale_text_overrides(mapping, lang)
            require_no_cross_app_translation(strings, mapping, slug, lang)
            new_ratio = _untranslated_ratio(strings, mapping)
            try:
                existing = target.read_text(encoding="utf-8")
            except OSError:
                continue
            old_ratio = _existing_untranslated_ratio(existing, strings)
            if new_ratio > old_ratio - min_gain:
                unchanged += 1
                continue
            try:
                localized = render_localized(
                    source,
                    lang,
                    slug,
                    mapping,
                    strings=strings,
                    spans=spans,
                    json_spans=json_spans,
                )
                target.write_text(localized, encoding="utf-8")
                improved += 1
                slug_touched = True
                print(
                    f"refreshed {lang}/{slug}.html "
                    f"{(1 - old_ratio) * 100:.0f}% -> {(1 - new_ratio) * 100:.0f}%",
                    flush=True,
                )
            except Exception as exc:  # noqa: BLE001 - report and continue
                failed += 1
                print(f"failed {lang}/{slug}.html: {exc}", file=sys.stderr, flush=True)
        if slug_touched:
            touched_slugs.append(slug)
        if limit and len(touched_slugs) >= limit:
            break

    print(
        json.dumps(
            {"refreshed": improved, "unchanged": unchanged, "failed": failed},
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Localize new AEO/GEO answer pages. Writes HTML only; never uses git.")
    parser.add_argument("slugs", nargs="*", help="Optional answer slugs, with or without .html")
    parser.add_argument("--langs", help="Locales to generate (comma or space separated)")
    parser.add_argument("--limit", type=int, help="Limit number of discovered slugs when no positional slugs are provided")
    parser.add_argument("--meta-only", action="store_true", help="只重寫既有在地化 answers 頁仍是英文 fallback 的 <title>/meta description/og:title/og:description(每語言句式+頁面特異 query/app),不翻譯內文、不動 robots/canonical/JSON-LD。--langs 可鎖定語言,預設掃全部 locale 目錄。")
    parser.add_argument("--dump", metavar="DIR", help="不翻譯,僅把每個 slug 的待譯字串輸出成 DIR/<slug>.json,供 agent 自行在地化(不用 OpenAI key)。")
    parser.add_argument("--trans", metavar="DIR", help="從全域 DIR/<lang>.json {原文:譯文}(agent 自產)組 mapping,免用 OpenAI key。字串全覆蓋才生成;缺漏寫到 DIR/_missing.<lang>.json 供補譯。")
    parser.add_argument(
        "--refresh",
        action="store_true",
        help=(
            "重新在地化『已存在』的 answers 頁"
            "（字典變大後補譯）；"
            "只有新字典能多譯出至少 --min-gain "
            "比例的可見字元才覆寫，"
            "絕不讓頁面倒退；可隨時中斷續跑。"
            "需搭配 --trans DIR。"
        ),
    )
    parser.add_argument(
        "--min-gain",
        type=float,
        default=0.01,
        help=(
            "--refresh 覆寫門檻：新版本至少要多"
            "在地化這個比例的可見字元"
            "（預設 0.01）。"
        ),
    )
    parser.add_argument("--allow-partial", action="store_true", help="搭配 --trans:即使有字串未譯也生成(未譯者維持原文)。預設關閉以免英文 fallback。")
    parser.add_argument("--openai", action="store_true", help="Explicitly opt in to OpenAI translation. Default requires --trans or --dump.")
    parser.add_argument("--ollama", action="store_true", help="Use the local Ollama service for zero-cost, on-device translation.")
    parser.add_argument("--ollama-model", default=OLLAMA_MODEL, help="Local Ollama model name.")
    parser.add_argument("--github-models", action="store_true", help="Use the authenticated GitHub Models inference API.")
    parser.add_argument("--github-model", default=GITHUB_TRANSLATION_MODEL, help="GitHub Models catalog model id.")
    parser.add_argument(
        "--github-cache-dir",
        type=Path,
        help=(
            "Persist completed GitHub Models translation batches by locale so "
            "interrupted runs can resume."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing localized pages after translations are complete.",
    )
    parser.add_argument(
        "--defer-shared-refresh",
        action="store_true",
        help=(
            "Defer shared hreflang and sitemap refresh so multiple locale "
            "workers can generate safely in parallel."
        ),
    )
    args = parser.parse_args()
    if args.meta_only:
        langs = (
            [x.strip() for x in args.langs.replace(",", " ").split() if x.strip()]
            if args.langs
            else None
        )
        return run_meta_only(langs)
    if args.refresh:
        if not args.trans:
            parser.error("--refresh 需搭配 --trans DIR")
        return run_refresh(
            parse_langs(args.langs),
            args.trans,
            limit=args.limit,
            min_gain=args.min_gain,
            slugs=args.slugs or None,
        )
    if sum(
        bool(value)
        for value in (
            args.openai,
            args.ollama,
            args.github_models,
            args.trans,
        )
    ) > 1:
        parser.error(
            "--openai, --ollama, --github-models and --trans "
            "are mutually exclusive"
        )
    if args.force and not args.slugs:
        parser.error("--force requires at least one explicit answer slug")
    if (
        not args.dump
        and not args.trans
        and not args.openai
        and not args.ollama
        and not args.github_models
    ):
        parser.error(
            "use --trans DIR, --github-models, --ollama "
            "or --dump DIR "
            "(or explicitly pass --openai)"
        )

    langs = parse_langs(args.langs)
    # --trans:每語言載入全域字典 + 累積缺漏(供 agent 下次補譯)。
    global_maps: dict[str, dict[str, str]] = {}
    missing_acc: dict[str, dict[str, int]] = {}
    if args.trans:
        for lang in langs:
            gp = Path(args.trans) / f"{lang}.json"
            global_maps[lang] = (
                json.loads(gp.read_text(encoding="utf-8"))
                if gp.exists()
                else {}
            )
            drop_cross_app_cache_poison(global_maps[lang], gp.name)
            missing_acc[lang] = {}

    if args.slugs:
        slugs = [Path(s).stem for s in args.slugs]
    else:
        slugs = discover_slugs(langs=langs)
        if args.trans:
            slugs = prioritize_translatable_slugs(
                slugs,
                langs,
                global_maps,
            )
        if args.limit:
            slugs = slugs[:args.limit]

    # --dump:輸出待譯字串(語言無關,strings 對所有語言相同),供 agent 自行翻譯。
    if args.dump:
        dump_dir = Path(args.dump)
        dump_dir.mkdir(parents=True, exist_ok=True)
        n = 0
        for slug in slugs:
            src_path = ANSWERS / f"{slug}.html"
            if not src_path.exists():
                print(f"missing source: {slug}", file=sys.stderr, flush=True)
                continue
            strings, _, _ = extract_strings(src_path.read_text(encoding="utf-8"))
            (dump_dir / f"{slug}.json").write_text(
                json.dumps({"slug": slug, "strings": strings}, ensure_ascii=False, indent=1),
                encoding="utf-8")
            n += 1
            print(f"dumped {slug} ({len(strings)} strings)", flush=True)
        print(json.dumps({"dumped": n}, ensure_ascii=False), flush=True)
        return 0

    api_key = read_key() if args.openai else ""
    source_strings: list[str] = []
    if args.github_models:
        for slug in slugs:
            source_path = ANSWERS / f"{slug}.html"
            if source_path.exists():
                strings, _, _ = extract_strings(
                    source_path.read_text(encoding="utf-8")
                )
                source_strings.extend(strings)
    github_models = (
        GithubModelsTranslator(
            source_strings,
            args.github_model,
            args.github_cache_dir,
        )
        if args.github_models
        else None
    )
    created = skipped = failed = 0
    print("Slugs:", flush=True)
    for slug in slugs:
        print(f"  {slug}", flush=True)

    for slug in slugs:
        src_path = ANSWERS / f"{slug}.html"
        if not src_path.exists():
            print(f"missing source: {slug}", file=sys.stderr, flush=True)
            failed += len(langs)
            continue
        source = src_path.read_text(encoding="utf-8")
        strings, spans, json_spans = extract_strings(source)
        for lang in langs:
            target = ROOT / lang / "answers" / f"{slug}.html"
            if target.exists() and not args.force:
                skipped += 1
                print(f"skip existing {lang}/{slug}.html", flush=True)
                continue
            try:
                partial_english: set[str] = set()
                if args.trans:
                    if lang in ENGLISH_LOCALES:
                        mapping = {s: s for s in strings}
                        miss = []
                    else:
                        gm = global_maps[lang]
                        mapping = {s: gm[s] for s in strings if s in gm}
                        miss = [s for s in strings if s not in gm]
                    if miss and not args.allow_partial:
                        for s in miss:
                            missing_acc[lang][s] = missing_acc[lang].get(s, 0) + 1
                        skipped += 1
                        print(f"incomplete {lang}/{slug}.html — 缺 {len(miss)} 字串,略過", flush=True)
                        continue
                    if miss:
                        # --allow-partial:未譯字串照原文出頁(與既有頁面的
                        # 英文 fallback 一致),同時記進 _missing.<lang>.json,
                        # 字典補譯後可用 --refresh 升級,頁面不會倒退。
                        for s in miss:
                            mapping[s] = s
                            missing_acc[lang][s] = missing_acc[lang].get(s, 0) + 1
                        partial_english = set(miss)
                else:
                    mapping = (
                        english_mapping(strings, lang)
                        if lang in ENGLISH_LOCALES
                        else (
                            github_models.translate(strings, lang)
                            if github_models is not None
                            else (
                                call_ollama(
                                    strings,
                                    lang,
                                    slug,
                                    model=args.ollama_model,
                                )
                                if args.ollama
                                else call_openai(
                                    strings,
                                    lang,
                                    slug,
                                    api_key,
                                )
                            )
                        )
                    )
                mapping = apply_locale_text_overrides(mapping, lang)
                require_complete_mapping(strings, mapping, slug, lang)
                require_translation_quality(
                    strings, mapping, slug, lang,
                    allow_english=partial_english,
                )
                localized = render_localized(
                    source,
                    lang,
                    slug,
                    mapping,
                    strings=strings,
                    spans=spans,
                    json_spans=json_spans,
                )
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(localized, encoding="utf-8")
                created += 1
                print(f"created {lang}/{slug}.html", flush=True)
            except Exception as exc:
                failed += 1
                print(f"failed {lang}/{slug}.html: {exc}", file=sys.stderr, flush=True)
                continue

    # 寫出各語言累積缺漏(依出現頁數排序,優先補高頻共用字串)。
    if args.trans:
        for lang, miss in missing_acc.items():
            if not miss:
                continue
            ordered = dict(sorted(miss.items(), key=lambda kv: -kv[1]))
            (Path(args.trans) / f"_missing.{lang}.json").write_text(
                json.dumps(ordered, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"[{lang}] 待補譯字串 {len(ordered)} → _missing.{lang}.json", flush=True)

    print(json.dumps({"created": created, "skipped": skipped, "failed": failed}, ensure_ascii=False), flush=True)
    # 產生新 i18n 頁後自動刷新答案 sitemap(涵蓋所有 */answers/*.html),避免漏索引。
    if created and not args.defer_shared_refresh:
        try:
            for slug in slugs:
                reconcile_all_alternates(slug)
            import aeo_answers  # noqa
            aeo_answers.write_sitemap()
        except Exception as exc:
            print(f"sitemap refresh skipped: {exc}", file=sys.stderr, flush=True)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
