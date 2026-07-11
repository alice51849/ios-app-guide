#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""App registry for social promo videos: assets + viral hook copy (English / intl market).

Each entry: display name, App Store search term, icon, screenshots dir+locale, the 3-4
strongest screenshots (self-captioned framed shots), and the opening hook + CTA bullets.
Hooks are pain-point / savings / before-after angles — the virality lever.
"""
import os


VALID_PURCHASE_MODELS = frozenset(
    {
        "paid_upfront",
        "free_with_lifetime_unlock",
        "free",
        "flexible",
        "neutral",
    }
)


def classify_purchase_model(price, iap_types, has_subscriptions):
    """Return a conservative model from verified App Store purchase data."""
    try:
        price = float(price)
    except (TypeError, ValueError):
        return "neutral"
    types = {str(value).upper() for value in iap_types if value}
    if has_subscriptions:
        return "neutral"
    if price > 0 and not types:
        return "paid_upfront"
    if price == 0 and types == {"NON_CONSUMABLE"}:
        return "free_with_lifetime_unlock"
    if price == 0 and not types:
        return "free"
    return "neutral"


def H(p):
    return os.path.expanduser(p)


APPS = {
    "snapport": dict(
        name="Snapport", search="Snapport", category="photo-utility",
        icon="~/14_Snapport/Resources/Assets.xcassets/AppIcon.appiconset/icon-1024.png",
        shots_dir="~/14_Snapport/fastlane/screenshots", locale="en-US",
        shots=["02_templates", "04_background", "08_print"],
        kicker="TRAVEL HACK",
        title="Stop paying $15\nfor passport photos",
        sub="Make your own at home in 30 seconds",
        tag="Pay once · Private",
        cta_bullets=["Pay once", "No subscription", "On-device"],
        purchase_model="paid_upfront",
        keywords=["passport photo", "passport photo app", "id photo", "visa photo",
                  "travel hack", "iphone tips", "passportphoto"],
    ),
    "sononote": dict(
        name="Sono Note", search="Sono Note", category="productivity",
        icon="~/18_SonoNote/ClearNoteVoice/Assets.xcassets/AppIcon.appiconset/icon_1024.png",
        shots_dir="~/18_SonoNote/AppStore/screenshots", locale="en-US",
        shots=["69_01", "69_04", "69_06"],
        kicker="NOTE HACK",
        title="Never type your\nnotes again",
        sub="Just talk — get clean notes, a summary & to-dos",
        tag="Pay once · Private",
        cta_bullets=["Pay once", "No subscription", "On-device"],
        purchase_model="free_with_lifetime_unlock",
        keywords=["voice notes", "voice to text", "meeting notes", "transcribe",
                  "note taking app", "study hack", "productivity"],
    ),
    "cvdesk": dict(
        name="CV Desk", search="CV Desk", category="productivity",
        icon="~/16_CVDesk/Resuma/Resources/Assets.xcassets/AppIcon.appiconset/icon-1024.png",
        shots_dir="~/16_CVDesk/fastlane/screenshots", locale="en-US",
        shots=["APP_IPHONE_67_01", "APP_IPHONE_67_02", "APP_IPHONE_67_03"],
        kicker="JOB HUNT",
        title="Beat the resume\nrobots (ATS)",
        sub="Instant ATS score + recruiter-ready templates",
        tag="Export PDF · No watermark",
        cta_bullets=["Pay once", "No watermark", "PDF & Word"],
        purchase_model="free_with_lifetime_unlock",
        keywords=["resume builder", "cv maker", "ats resume", "resume template",
                  "job search", "career", "resume tips"],
    ),
    "picclear": dict(
        name="PicClear", search="PicClear", category="photo-utility",
        icon="~/12_PicClear/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png",
        shots_dir="~/12_PicClear/fastlane/screenshots", locale="en-US",
        shots=["iphone_01_home", "iphone_02_duplicates", "iphone_04_largevideos"],
        kicker="PHONE STORAGE",
        title="Your storage is\nfull of junk",
        sub="Find duplicates & huge videos in one scan",
        tag="Pay once · Private",
        cta_bullets=["Pay once", "No subscription", "On-device"],
        purchase_model="free_with_lifetime_unlock",
        keywords=["free up storage", "iphone storage full", "delete duplicates",
                  "clean storage", "iphone tips", "storage hack"],
    ),

    # ---- ASC-sourced screenshots (assets/<key>/NN.png, self-captioned, en) ----
    "scanto": dict(
        name="ScanTo Pro", search="ScanTo", category="productivity",
        icon="~/11_ScanToPro/OfflineScannerPro/Resources/Assets.xcassets/AppIcon.appiconset/icon-1024.png",
        shots_dir="~/00_GrowthEngine/social/assets/scanto", locale="",
        shots=["01", "05", "06"],
        kicker="PDF SCANNER",
        title="Your iPhone is already\na pro PDF scanner",
        sub="Scan, OCR-search & Face ID-lock docs — pay once",
        tag="Pay once · Private",
        cta_bullets=["Pay once", "No subscription", "On-device"],
        purchase_model="free_with_lifetime_unlock",
        keywords=["pdf scanner", "document scanner", "scan to pdf", "ocr app",
                  "scan documents", "paperless", "iphone tips"],
    ),
    "cyca": dict(
        name="Cyca", search="Cyca", category="health",
        icon="~/19_Cyca/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png",
        shots_dir="~/00_GrowthEngine/social/assets/cyca", locale="",
        shots=["01", "02", "06"],
        kicker="CYCLE SYNC",
        title="Stop guessing where\nyou are in your cycle",
        sub="See every phase, your best days & gentle days",
        tag="Pay once · Private",
        cta_bullets=["Pay once", "No subscription", "On-device"],
        purchase_model="free_with_lifetime_unlock",
        keywords=["period tracker", "cycle tracker", "menstrual", "ovulation",
                  "femtech", "women health", "pms"],
    ),
    "gmoney": dict(
        name="G+Money", search="G Money", category="finance",
        icon="~/15_GMoney/ios/GMoney/Images.xcassets/AppIcon.appiconset/App-Icon-1024x1024@1x.png",
        shots_dir="~/00_GrowthEngine/social/assets/gmoney", locale="",
        shots=["01", "02", "03"],
        kicker="TRAVEL MONEY",
        title="Know the real cost\nof everything abroad",
        sub="Convert + log every expense in one tap — offline",
        tag="Pay once · No account",
        cta_bullets=["Pay once", "Offline", "No account"],
        purchase_model="paid_upfront",
        keywords=["travel budget", "currency converter", "expense tracker",
                  "travel money", "trip budget", "travel hack"],
    ),
    "hourstag": dict(
        name="HoursTag", search="HoursTag", category="finance",
        icon="~/13_HoursTag/ios/HoursTag/Images.xcassets/AppIcon.appiconset/App-Icon-1024x1024@1x.png",
        shots_dir="~/00_GrowthEngine/social/assets/hourstag", locale="",
        shots=["01", "02", "03"],
        kicker="MONEY MINDSET",
        title="That $129 isn't $129.\nIt's 14 work hours.",
        sub="See what everything really costs — in hours of your life",
        tag="Pay once · 17 languages",
        cta_bullets=["Pay once", "Private", "No tracking"],
        purchase_model="paid_upfront",
        keywords=["money mindset", "budgeting", "spending tracker",
                  "financial freedom", "money tips", "personal finance"],
    ),
    "lockhour": dict(
        name="LockHour Pro", search="LockHour", category="productivity",
        icon="~/10_LockHourPro/Resources/Assets.xcassets/AppIcon.appiconset/icon-1024.png",
        shots_dir="~/00_GrowthEngine/social/assets/lockhour", locale="",
        shots=["01", "03", "04"],
        kicker="SCREEN TIME",
        title="You lose 4 hours a day\nto your phone",
        sub="Block the apps that steal your focus — one tap",
        tag="Pay once · Private",
        cta_bullets=["Pay once", "No ads", "On-device"],
        purchase_model="free_with_lifetime_unlock",
        keywords=["screen time", "app blocker", "focus app", "digital detox",
                  "study focus", "deep work", "productivity"],
    ),
    "unblurry": dict(
        name="Unblurry", search="Unblurry", category="photo-utility",
        icon="~/20_Unblurry/Unblurry/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png",
        shots_dir="~/00_GrowthEngine/social/assets/unblurry", locale="",
        shots=["01", "02", "03"],
        kicker="PHOTO RESCUE",
        title="Don't delete that\nblurry photo",
        sub="AI super-resolution makes it crisp — on your iPhone",
        tag="Pay once · On-device",
        cta_bullets=["Pay once", "Private", "On-device"],
        purchase_model="free_with_lifetime_unlock",
        keywords=["unblur photo", "photo enhancer", "ai upscale",
                  "fix blurry photo", "enhance photo", "photo quality"],
    ),
    "photocream": dict(
        name="PhotoCream", search="PhotoCream", category="photo-utility",
        icon="~/17_PhotoCream/Photocream/Resources/Assets.xcassets/AppIcon.appiconset/icon-1024.png",
        shots_dir="~/00_GrowthEngine/social/assets/photocream", locale="",
        shots=["01", "04", "06"],
        kicker="FILM LOOK",
        title="Make every photo\nlook like a film still",
        sub="100+ real film looks, grain, halation & light leaks",
        tag="Pay once · No watermark",
        cta_bullets=["Pay once", "No watermark", "Full-res"],
        purchase_model="free_with_lifetime_unlock",
        keywords=["film filter", "vintage filter", "photo editor", "aesthetic",
                  "film camera", "retro", "presets"],
    ),

    # ---- Lumi kids series (intl / English; free/Lite funnels) ----
    "lumiletters": dict(
        name="Lumi Letters", search="Lumi Letters", category="kids",
        icon="~/01_LumiLettersLite/ios/LumiLite/Images.xcassets/AppIcon.appiconset/App-Icon-1024x1024@1x.png",
        shots_dir="~/00_GrowthEngine/social/assets/lumiletters", locale="",
        shots=["01", "03", "05"],
        kicker="AGES 4–7",
        title="Your kid will beg to\npractice their ABCs",
        sub="Playful phonics, tracing & letter games",
        tag="Pay once · No ads ever",
        cta_bullets=["Pay once", "No ads", "Kid-safe"],
        purchase_model="free_with_lifetime_unlock",
        keywords=["abc for kids", "phonics", "learn letters", "kids learning",
                  "preschool", "toddler", "alphabet"],
    ),
    "lumimath": dict(
        name="Lumi Math Planet", search="Lumi Math", category="kids",
        icon="~/03_LumiMathPlanet/ios/Lumi/Images.xcassets/AppIcon.appiconset/App-Icon-1024x1024@1x.png",
        shots_dir="~/00_GrowthEngine/social/assets/lumimath", locale="",
        shots=["02", "05", "06"],
        kicker="AGES 4–10",
        title="The math game kids\nactually ask to play",
        sub="A whole galaxy of number adventures",
        tag="Pay once · No ads ever",
        cta_bullets=["Pay once", "No ads", "Kid-safe"],
        purchase_model="free_with_lifetime_unlock",
        keywords=["math for kids", "kids math game", "learn numbers",
                  "preschool math", "counting", "education", "kids learning"],
    ),
    "lumimission": dict(
        name="Lumi Mission Planet", search="Lumi Mission", category="kids",
        icon="~/07_LumiMissionPlanet/ios/Lumi/Images.xcassets/AppIcon.appiconset/App-Icon-1024x1024@1x.png",
        shots_dir="~/00_GrowthEngine/social/assets/lumimission", locale="",
        shots=["01", "03", "05"],
        kicker="AGES 3–8",
        title="Brush, sleep, tidy —\nwithout the nagging",
        sub="A daily habit & bedtime ritual kids love",
        tag="Pay once · No ads ever",
        cta_bullets=["Pay once", "No ads", "Kid-safe"],
        purchase_model="free_with_lifetime_unlock",
        keywords=["kids routine", "chore chart", "habit tracker for kids",
                  "bedtime", "parenting", "toddler", "kids learning"],
    ),
    "lumiweather": dict(
        name="Lumi Weather", search="Lumi Weather", category="kids",
        icon="~/09_LumiWeather/LumiWeather/Resources/Assets.xcassets/AppIcon.appiconset/icon.png",
        shots_dir="~/00_GrowthEngine/social/assets/lumiweather", locale="",
        shots=["03", "02", "08"],
        kicker="FOR PARENTS",
        title="Is it OK to take the\nkids out today?",
        sub="Weather + a kid-outing score, tuned to their age",
        tag="Pay once · No tracking",
        cta_bullets=["Pay once", "No ads", "Kid-safe"],
        purchase_model="free_with_lifetime_unlock",
        keywords=["weather for kids", "family weather", "what to wear",
                  "kids outing", "parenting", "weather app"],
    ),

    # ---- Lumi paid / Pro counterparts + Bopomofo (intl English; heritage angle) ----
    "lumiletterspro": dict(
        name="Lumi Letters Pro", search="Lumi Letters Pro", category="kids",
        icon="~/02_LumiLettersPro/ios/Lumi/Images.xcassets/AppIcon.appiconset/App-Icon-1024x1024@1x.png",
        shots_dir="~/00_GrowthEngine/social/assets/lumiletters", locale="",
        shots=["02", "06", "08"],
        kicker="COMPLETE EDITION",
        title="Your kid could read\nbefore kindergarten",
        sub="The complete phonics, tracing & word-building world",
        tag="Pay once · Everything unlocked",
        cta_bullets=["Pay once", "No ads", "Kid-safe"],
        purchase_model="paid_upfront",
        keywords=["learn to read", "phonics for kids", "abc for kids",
                  "sight words", "preschool reading", "kindergarten prep",
                  "kids learning"],
    ),
    "lumimathpro": dict(
        name="Lumi Math Pro", search="Lumi Math Pro", category="kids",
        icon="~/04_LumiMathPro/ios/Lumi/Images.xcassets/AppIcon.appiconset/App-Icon-1024x1024@1x.png",
        shots_dir="~/00_GrowthEngine/social/assets/lumimath", locale="",
        shots=["01", "03", "07"],
        kicker="COMPLETE EDITION",
        title="Raise a kid who\nloves numbers",
        sub="The whole number galaxy — every adventure unlocked",
        tag="Pay once · Everything unlocked",
        cta_bullets=["Pay once", "No ads", "Kid-safe"],
        purchase_model="paid_upfront",
        keywords=["math for kids", "kids math game", "learn numbers",
                  "addition for kids", "counting", "preschool math",
                  "kids learning"],
    ),
    "lumimissionpro": dict(
        name="Lumi Mission Planet Pro", search="Lumi Mission Planet Pro", category="kids",
        icon="~/08_LumiMissionPlanetPro/ios/LumiPro/Images.xcassets/AppIcon.appiconset/App-Icon-1024x1024@1x.png",
        shots_dir="~/00_GrowthEngine/social/assets/lumimission", locale="",
        shots=["02", "04", "06"],
        kicker="COMPLETE EDITION",
        title="The morning routine\nthat runs itself",
        sub="Habits, chores & bedtime kids actually want to do",
        tag="Pay once · Everything unlocked",
        cta_bullets=["Pay once", "No ads", "Kid-safe"],
        purchase_model="paid_upfront",
        keywords=["kids routine", "chore chart", "habit tracker for kids",
                  "bedtime routine", "morning routine", "parenting",
                  "kids learning"],
    ),
    "lumibopomofo": dict(
        name="Lumi Bopomofo", search="Lumi Bopomofo", category="kids",
        icon="~/05_LumiBopomofo/ios/Lumi/Images.xcassets/AppIcon.appiconset/App-Icon-1024x1024@1x.png",
        shots_dir="~/05_LumiBopomofo/ads/screenshots/final/iphone/en", locale="",
        shots=["02", "03", "05"],
        kicker="RAISE A CHINESE READER",
        title="The playful way kids\nlearn Bopomofo",
        sub="Zhuyin phonics, tracing & tone games — the first step to reading Chinese",
        tag="Free to start · No ads",
        cta_bullets=["No subscription", "No ads", "Kid-safe"],
        purchase_model="free_with_lifetime_unlock",
        keywords=["bopomofo", "zhuyin", "learn chinese for kids",
                  "mandarin for kids", "chinese phonics", "bilingual kids",
                  "heritage chinese"],
    ),
    "lumibopomofopro": dict(
        name="Lumi Bopomofo Pro", search="Lumi Bopomofo Pro", category="kids",
        icon="~/06_LumiBopomofoPro/ios/LumiPro/Images.xcassets/AppIcon.appiconset/App-Icon-1024x1024@1x.png",
        shots_dir="~/05_LumiBopomofo/ads/screenshots/final/iphone/en", locale="",
        shots=["01", "04", "06"],
        kicker="COMPLETE EDITION",
        title="Everything your kid\nneeds to read Chinese",
        sub="The complete Zhuyin (Bopomofo) world — every sound & game unlocked",
        tag="Pay once · Everything unlocked",
        cta_bullets=["Pay once", "No ads", "Kid-safe"],
        purchase_model="paid_upfront",
        keywords=["bopomofo", "zhuyin", "learn chinese for kids",
                  "mandarin for kids", "chinese phonics", "raising bilingual",
                  "heritage language"],
    ),
    "zodira": dict(
        name="Zodira", search="Zodira", category="lifestyle",
        icon="~/21_Astrea/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png",
        shots_dir="~/00_GrowthEngine/social/assets/zodira", locale="",
        shots=["01", "02", "03"],
        kicker="COSMIC CLARITY",
        title="East meets West\nfor daily insight",
        sub="AI astrology, tarot, horoscope, BaZi & Zi Wei — offline and private",
        tag="Pay once · Offline",
        cta_bullets=["Pay once", "No subscription", "Offline", "No ads", "No tracking"],
        purchase_model="free_with_lifetime_unlock",
        keywords=["astrology", "tarot", "horoscope", "birth chart",
                  "bazi", "zi wei", "daily horoscope"],
    ),
    "aim990": dict(
        name="Aim990", search="Aim990", category="education",
        icon="~/Aim990/Aim990/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon.png",
        shots_dir="~/00_GrowthEngine/social/assets/aim990", locale="",
        shots=["01", "02", "03"],
        kicker="TOEIC SPRINT",
        title="30 days to make\nTOEIC prep feel doable",
        sub="Daily L&R study plans, weak-spot drills & score tracking toward 990",
        tag="Pay once · Smart practice",
        cta_bullets=["Pay once", "No subscription", "Daily plan", "Weak-spot drills"],
        purchase_model="free_with_lifetime_unlock",
        keywords=["toeic", "toeic prep", "toeic lr", "english test",
                  "study plan", "score tracker", "business english"],
    ),
    "mochi": dict(
        name="Mochi", search="Mochi Checklist", category="productivity",
        icon="~/20_MochiTodo/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png", shots_dir="~/00_GrowthEngine/social/assets/mochi", locale="", shots=["01", "02", "03"],
        kicker="COZY TO-DO",
        title="The to-do list that\nfeels good to finish",
        sub="Cute, cozy checklists with a satisfying tap to complete — free, no ads",
        tag="Free to start · Pay once",
        cta_bullets=["Free to start", "Pay once", "No ads", "Simple"],
        purchase_model="free_with_lifetime_unlock",
        keywords=["to do list", "checklist app", "cute planner", "task manager",
                  "daily planner", "cozy productivity", "aesthetic to do"],
    ),
    "zafe": dict(
        name="Zafe", search="Zafe Photo Vault", category="photo-utility",
        icon="~/Zafe/Zafe/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon.png", shots_dir="~/00_GrowthEngine/social/assets/zafe", locale="", shots=["01", "02", "03"],
        kicker="PRIVATE VAULT",
        title="Hide your private\nphotos for good",
        sub="Lock private photos & videos behind Face ID — everything stays on your iPhone",
        tag="Pay once · On-device",
        cta_bullets=["Pay once", "On-device", "Private"],
        purchase_model="free_with_lifetime_unlock",
        keywords=["photo vault", "hide photos", "private album", "lock photos",
                  "secret photos", "face id vault", "hide pictures"],
    ),
    "tripplanet": dict(
        name="Lumi Trip Planet", search="Lumi Trip Planet", category="kids",
        icon="~/22_TripPlanet/Resources/Assets.xcassets/AppIcon.appiconset/AppIcon-1024.png", shots_dir="~/00_GrowthEngine/social/assets/tripplanet", locale="", shots=["01", "02", "03"],
        kicker="AGES 4–10",
        title="Turn every trip into\na kid's adventure",
        sub="Fun travel games, packing help & discovery for little explorers",
        tag="Pay once · No ads ever",
        cta_bullets=["Pay once", "No ads", "Kid-safe"],
        purchase_model="free_with_lifetime_unlock",
        keywords=["kids travel", "travel games for kids", "road trip games",
                  "family travel", "kids activities", "travel for kids", "preschool"],
    ),
}

# App Store numeric IDs (from ASC list_apps) -> used to build direct
# https://apps.apple.com/app/id… links in captions & YouTube descriptions.
APPSTORE = {
    "snapport": "6780575828",
    "sononote": "6782139553",
    "cvdesk": "6781337213",
    "picclear": "6780223070",
    "scanto": "6779977651",
    "cyca": "6782251621",
    "gmoney": "6755782939",
    "hourstag": "6754218117",
    "lockhour": "6780107485",
    "unblurry": "6782275018",
    "photocream": "6781808054",
    "lumiletters": "6778748533",
    "lumimath": "6778269699",
    "lumimission": "6779750237",
    "lumiweather": "6779552704",
    "lumiletterspro": "6778491147",
    "lumimathpro": "6776958488",
    "lumimissionpro": "6779745474",
    "lumibopomofo": "6773017109",
    "lumibopomofopro": "6775773117",
    "aim990": "6784974530",
    "zodira": "6783609555",
    "mochi": "6785004775",
    "zafe": "6787344033",
    "tripplanet": "6787193643",
}


def appstore_url(key, campaign=None):
    """Direct App Store link for an app key (empty string if unknown).

    campaign: optional App Store Connect campaign token (ct=) for attribution.
    """
    aid = APPSTORE.get(key)
    if not aid:
        return ""
    url = f"https://apps.apple.com/app/id{aid}"
    return f"{url}?ct={campaign}" if campaign else url


# --- 自動偵測的新 App(由 new_app_catchup.py 維護,免手動改碼即自動納入全部宣傳)---
_AUTO_PATH = os.path.join(os.path.dirname(__file__), "registry_auto.json")
if os.path.exists(_AUTO_PATH):
    try:
        import json as _json
        for _k, _v in _json.load(open(_AUTO_PATH, encoding="utf-8")).items():
            if _k in APPS:
                continue
            APPSTORE.setdefault(_k, _v["appstore_id"])
            APPS[_k] = dict(
                name=_v["name"], search=_v.get("search", _v["name"]),
                category=_v.get("category", "other"),
                icon="", shots_dir="", locale="", shots=[],
                kicker=_v.get("kicker", ""), title=_v.get("title", _v["name"]),
                sub=_v.get("sub", ""),
                tag=_v.get("tag", "See App Store for current details"),
                cta_bullets=_v.get("cta_bullets", []),
                purchase_model=_v.get("purchase_model", "neutral"),
                keywords=_v.get("keywords", []),
            )
    except (OSError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Invalid automatic app registry: {_AUTO_PATH}") from exc

for _key, _app in APPS.items():
    _model = _app.setdefault("purchase_model", "neutral")
    if _model not in VALID_PURCHASE_MODELS:
        raise ValueError(f"Invalid purchase model for {_key}: {_model}")
    if _model == "neutral":
        _pricing_markers = (
            "pay once",
            "one-time",
            "subscription",
            "free to start",
            "paid download",
        )
        if any(
            marker in _app.get("tag", "").lower()
            for marker in _pricing_markers
        ):
            _app["tag"] = "See App Store for current details"
        _app["cta_bullets"] = [
            bullet
            for bullet in _app.get("cta_bullets", [])
            if not any(marker in bullet.lower() for marker in _pricing_markers)
        ]
