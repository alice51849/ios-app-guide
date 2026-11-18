#!/usr/bin/env python3
"""Search-first captions, alt text and hook-variant choice (deterministic, no model calls).

Our accounts have few followers, so every post has to be found through search
and the platforms' topic / hashtag distribution. The Growth Engine planner
(shorts/scripts/schedule_posts.py + search_intent.py) puts the search fields
into .github/growth/clips.json, from the storyboards and the App Store
keyword data only:

- clip["hooks"]     2-3 variants {"id", "lead", "benefit"} from the storyboard
- clip["keyline"]   the localized subtitle / searchable name part
- clip["keywords"]  ASO keywords in the locale, priority order
- clip["tags"]      3-6 locale-native hashtags derived from those keywords
- clip["hook_best"] the variant post_performance.py ranks first (once data exists)
- data["seo"]       the same fields per app / locale for the daily cards

Every caption starts with the problem line, keeps a keyword phrase inside the
first 125 characters (what Instagram / Threads show and index before "more"),
and ends with at most a handful of tags. Old clips.json entries without these
fields still get a caption (hook + brand tag).
"""
import datetime as dt
import json
import re
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
GROWTH = HERE.parent / "growth"
CLIPS = GROWTH / "clips.json"
SEARCH_TERMS = GROWTH / "search-terms.json"  # build_search_terms.py, from the keyword rank history
PERFORMANCE = GROWTH / "performance.json"

FIRST = 125  # characters Instagram / Threads show before "more"
TAG_LIMIT = {"instagram": 5, "threads": 1, "telegram": 3, "bluesky": 3, "facebook": 3, "plurk": 3}
# Generic store / platform tags say nothing a searcher types for a problem.
GENERIC_TAGS = {"#app", "#apps", "#iphoneapps", "#appstore", "#iosapps", "#ios", "#iphone", "#app推薦", "#アプリ紹介",
                "#앱추천", "#아이폰어플", "#iphoneアプリ", "#aplikasiiphone", "#ungdungiphone", "#แอพไอโฟน",
                "#productivity", "#android", "#free",
                # Edition words say nothing a searcher types: they only repeat a part of the brand tag.
                "#探索版", "#完整版", "#免費版", "#lite", "#pro", "#エクスプローラー版", "#탐험판",
                # Split-out generic keyword words (2026-11-19 quality audit): say nothing on their own.
                "#記錄", "#紀錄", "#管理", "#記録", "#기록", "#관리", "#小工具", "#ウィジェット", "#위젯"}


def _load(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


FULLWIDTH_PUNCT = "、。，．！？：；」』）】〉》…"


CJK = "\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
CJK_COMMA = {"zh": "，", "ja": "、"}  # same table as GE shorts/scripts/search_intent.py


def tidy(line, locale=None):
    """One caption line as a native writer types it: single spaces, none after full-width punctuation
    ("照片拍糊了？ 秒變清晰" -> "照片拍糊了？秒變清晰", "証明写真、 おうちで" -> "証明写真、おうちで"). With a Chinese or
    Japanese locale a space left between two CJK characters (a video caption's line break) becomes "，" / "、";
    a space next to a Latin word or digit stays (2026-11-19 quality audit)."""
    line = re.sub(r"\s+", " ", (line or "").replace("*", "")).strip()
    line = re.sub(f"([{FULLWIDTH_PUNCT}]) ", r"\1", line)
    comma = CJK_COMMA.get((locale or "").split("-")[0])
    if comma:
        line = re.sub(f"(?<=[{CJK}]) (?=[{CJK}])", comma, line)
    return line


# Rule 1.9 (Kumo and every app): no drug, drug brand, injection, weight-loss outcome or cure/treatment word in a
# tag - the same list as GE shorts/scripts/search_intent.py MEDICAL (keep the two in step). Old clips.json entries
# carry such tags until the planner rewrites them, so the caption drops them here too.
MEDICAL = re.compile(
    r"glp[\s\-_]?1|ozempic|wegovy|mounjaro|zepbound|saxenda|rybelsus|victoza|trulicity|semaglutid|tirzepatid"
    r"|liraglutid|insulin|\binject|\binjeç|\binyecc|\biniez|piq[uû]re|spritze|caneta|\bjabs?\b|zastrzyk|enjeksiyon|\bsuntik"
    r"|\bshots?\s?(?:log|tracker|reminder)|\bpills?\b|\bdrugs?\b|\bmedicat|\bmedikament|\bweight\s?loss"
    r"|before\s?(?:and\s?|&\s?)?after|비포애프터|ビフォーアフター|\blose\s?weight|abnehm"
    r"|adelgaz|perder\s?peso|bajar\s?de\s?peso|p[ée]rdida\s?de\s?peso|emagrec|maigrir|perte\s?de\s?poids"
    r"|dimagr|afvallen|gewichtsverlies|odchudz|\bcure\b|\bcures\b|\bheal(?:s|ing)?\b|therap|treatment|behandlung"
    r"|tratamiento|traitement|gu[ée]rir|\bcurar"
    r"|注射|打針|施打|減脂|燃脂|脂肪燃焼|지방\s?연소|瘦瘦針|減重針|減肥針|瘦身針|減肥|減重|瘦身|減量|藥|薬|治療|治癒|療效|療法|醫療|医療|胰島素"
    r"|猛健樂|胰妥讚|週纖達|善纖達|オゼンピック|ウゴービ|マンジャロ|インスリン"
    r"|주사(?!위)|오젬픽|위고비|마운자로|인슐린|살빼|감량|치료|치유|ฉีด|ลดน้ำหนัก|ยา(?:ลด|รักษา)"
    # 11-19 review: every other Kumo store language (simplified Chinese, Italian, Nordic, Turkish, Vietnamese,
    # Slavic, Arabic, Hebrew, Greek, Indic, Malay / Indonesian...).
    r"|减肥|减重|减脂|瘦瘦针|减重针|打针|针剂|药物|治疗|医疗|疗效|slimming|\bslankekur|\bslanking|\bbanta\b"
    r"|viktminskning|viktnedgång|vekttap|vektnedgang|vægttab|gå\sner\si\svikt|spruta|sprøjte|sprøyte|\bpistos"
    r"|laihdut|painonpudotus|zayıfla|kilo\sverme|\biğne|giảm\scân|\btiêm\b|thuốc|похуд|снижени[ея]\sвеса|укол"
    r"|инъекц|лекарств|схуд|зниження\sваги|ін.єкц|تخسيس|تنحيف|حقن|[اإ]نقاص|خسارة\sالوزن|הרזיה|ירידה\sבמשקל"
    r"|זריק|αδυνάτ|απώλεια\sβάρους|ενέσ|schudn|utrata\swagi|chudnut|schudnúť|hubnut|zhubnout|hujšanj|shujšat"
    r"|mršavlj|fogyás|fogyókúr|slăbi|aprimar|\binjek|\binjec|turun\sberat|menurunkan\sberat|\bkurus\b"
    r"|वजन\sघट|वज़न\sघट|वजन\sकमी|इंजेक्शन|वेट\sलॉस|ఇంజెక్షన్|ఇన్జెక్షన్|వెయిట్\sలాస్|ઇન્જેક્શન|વજન\sઘટાડ"
    r"|ਇੰਜੈਕਸ਼ਨ|ਟੀਕਾ|ਭਾਰ\sਘਟਾ|ଇଞ୍ଜେକ୍ସନ|ଓଜନ\sକମା|ஊசி|எடை\sகுறை|ഇൻജക്ഷൻ|ഭാരം\sകുറയ്|ইনজেকশন|ওজন\sকমা"
    r"|ಇಂಜೆಕ್ಷನ್|ತೂಕ\sಇಳಿ|انجیکشن|ٹیکہ|وزن\sکم|బరువు\sతగ్గ",
    re.IGNORECASE)
# Words split out of the keyword field that say nothing as a hashtag on their own - the same list as GE
# shorts/scripts/search_intent.py FRAGMENTS (keep the two in step); old clips.json entries carry them until the
# planner rewrites the entry.
FRAGMENTS = {
    "gå ner", "painon", "berselang", "intermitterend", "pitný", "คุม", "เป็นช่วง", "闹钟", "间歇性", "计时器",
    "gbagbcgb", "down", "save", "create", "size", "sizes", "dual", "fold", "pairs", "moving", "screen", "quando",
    "saiba", "sair", "toca", "zweit", "erstellen", "zurücksetzen", "text", "scherpe", "hidup", "sono",
    "loss", "daily", "until", "since", "intermittent", "days", "day", "image", "picture", "clear", "rate", "star",
    "white", "print", "split", "bill", "maker", "score", "keywords", "template", "percent", "inner", "analyzer",
    "enhancer", "behavior", "exchange", "abroad", "body", "measurement", "reminder", "water", "diet",
    "mismo", "personas", "jugadores", "perder", "bajar", "pérdida", "perte", "perdre", "perda", "borrada",
    "melhorar", "qualidade", "parse", "traditional", "verbeteren", "onscherp", "contoh", "daftar", "riwayat", "nghe",
    "membaca", "間歇性", "計時器", "鬧鐘", "마시기", "타이머", "공복", "수분",
}
LATIN_TAG = re.compile(r"^[A-Za-z\u00c0-\u024f]+$")
FRAGMENTS_TIGHT = {"".join(f.split()) for f in FRAGMENTS}  # '#GåNer' is 'gå ner' written as a hashtag


def _spaced(text):
    """'#GewichtGLP1Tracker' -> 'Gewicht GLP 1 Tracker': words split at the case humps."""
    return re.sub(r"(?<=[a-zà-ÿ])(?=[A-Z])|(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", " ", text.lstrip("#"))


def medical(text):
    return bool(text) and bool(MEDICAL.search(text) or MEDICAL.search(_spaced(text)))


def phrase_tag(tag, locale=""):
    """False for a word split out of the ASO keyword field that says nothing alone (FRAGMENTS: #Loss, #Mismo,
    #Daily, #Intermittent, #間歇性, #타이머) and for a 1-3 letter Latin word (#Bil, #a); a single word that is a real
    term (#Decibel, #Bookkeeping) stays - the planner chooses tags from the app's own name and subtitle first."""
    body = tag.lstrip("#")
    if not any(ch.isalnum() for ch in body) or "".join(body.split()).casefold() in FRAGMENTS_TIGHT:
        return False
    return not (LATIN_TAG.match(body) and len(body) < 4)


def dedupe(lines):
    """Drop a line another line already contains (case-insensitive), keeping the longer one in place;
    blank lines are kept as separators."""
    out = []
    for i, line in enumerate(lines):
        low = line.strip().casefold()
        if low and any(low != o.strip().casefold() and low in o.casefold() for o in lines if o.strip()):
            continue
        if low and low in {o.strip().casefold() for o in out}:
            continue
        out.append(line)
    return out


def variants(clip):
    """The clip's hook variants (lines tidied); a clip without them has one: its hook."""
    loc = clip.get("locale")
    hooks = [dict(h, lead=tidy(h["lead"], loc), benefit=tidy(h.get("benefit", ""), loc))
             for h in clip.get("hooks") or [] if h.get("lead")]
    return hooks or [{"id": "a", "lead": tidy(clip.get("hook", ""), loc), "benefit": ""}]


def winners(path=PERFORMANCE):
    return _load(path, {}).get("hook_winners") or {}


def winner(wins, key, locale):
    wins = wins if isinstance(wins, dict) else {}
    return (wins.get("apps") or {}).get(key) or (wins.get("locales") or {}).get(locale) or wins.get("global")


def choose(clip, channel, day, wins=None):
    """Variant to post: rotates across platforms and days; once the performance loop has a winner for this
    clip (or its locale, or overall) the winner goes out two days in three, the rotation keeps testing."""
    hooks = variants(clip)
    if len(hooks) == 1:
        return hooks[0]
    wins = winners() if wins is None else wins
    best = clip.get("hook_best") or winner(wins, f"{clip.get('app')}/{clip.get('locale')}", clip.get("locale"))
    by_id = {h["id"]: h for h in hooks}
    if best in by_id and day.toordinal() % 3:
        return by_id[best]
    spread = sum(map(ord, f"{channel}/{clip.get('app')}/{clip.get('locale')}"))  # not one variant for a whole day
    return hooks[(day.toordinal() + spread) % len(hooks)]


def tags(clip, limit=5):
    """Keyword-derived tags without generic store tags, medical tags (rule 1.9) or single split-out keyword words;
    the brand tag when nothing else is known. At most 5 whatever the caller asks (2026-11-19 quality audit)."""
    limit = min(limit, 5)
    brand = "#" + "".join(ch for ch in clip.get("search", "") if ch.isalnum()) if clip.get("search") else ""
    out = []
    kumo_health = health_app(clip)
    for t in clip.get("tags") or []:
        t = t if t.startswith("#") else f"#{t}"
        if medical(t) or (kumo_health and t.lstrip("#").strip().casefold() in WEIGHT_WORDS) or (
                t.casefold() != brand.casefold() and not phrase_tag(t, clip.get("locale"))):
            continue
        if t.casefold() not in GENERIC_TAGS and t.casefold() not in {x.casefold() for x in out}:
            out.append(t)
    if brand and medical(brand):
        brand = ""
    if not out and brand:
        out = [brand]
    if len(out) > limit > 1 and brand.casefold() in {t.casefold() for t in out}:  # keep the brand tag
        out = [t for t in out if t.casefold() != brand.casefold()][:limit - 1] + [brand]
    return out[:limit]


def body(clip, variant, limit=FIRST):
    """Problem line, benefit, keyword line; the keyword line moves up if it would fall past `limit`."""
    lead, benefit, keyline = tidy(variant.get("lead", "")), tidy(variant.get("benefit", "")), clip.get("keyline", "")
    rest = [x for x in (benefit, keyline) if x and x != lead]
    if keyline and benefit and len("\n".join([lead, benefit, keyline])) > limit:
        rest = [keyline, benefit]
    return [lead, *rest]


def alt_text(clip, variant, limit=500):
    """Accessible description that also carries the search phrase."""
    parts = [clip.get("name", ""), variant.get("lead", ""), variant.get("benefit", ""), clip.get("keyline", "")]
    text = " — ".join(p for i, p in enumerate(parts) if p and not any(p in q for q in parts[:i]))
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


# Split-out weight-loss words: harmless alone, a weight-loss promise in a weight / GLP-1 app (same list as GE
# shorts/scripts/search_intent.py WEIGHT_WORDS).
WEIGHT_WORDS = {"loss", "lose", "perder", "perdere", "perte", "perdre", "perda", "pèrdua", "bajar", "pérdida",
                "maigrir", "adelgazar", "emagrecer", "emagrecedora", "abnehmen", "slim", "burn", "verliezen",
                "turun", "menurunkan", "kurangi", "susut", "utrata", "redukcja", "redukce", "redukcia", "gubitak",
                "snížení", "снижение", "зниження", "kiêng", "giảm", "خسارة", "نزول", "انقاص", "कम", "लॉस", "లాస్",
                "ലോസ്", "ಲಾಸ್", "ঘটাড়ো", "ઘટાડવા", "ઓછું", "ਘਟਾਓ", "ਘੱਟ", "ହ୍ରାସ", "କମ", "குறைக்க", "குறைய",
                "കുറയ്ക്കാൻ", "কমানোর", "ಇಳಿಸಲು", "ಕಡಿಮೆ", "करण्यासाठी", "करणे", "کرنا", "weight", "kilos", "kilo", "הורדת", "رشاقة",
                "shot", "shots"}


def health_app(clip):
    """A weight / GLP-1 app: Kumo always counts, even in a language whose store name carries no medical word
    (11-19 review); any other app counts when its name, search phrase, keyline or a keyword is medical."""
    words = [w for w in clip.get("keywords") or [] if isinstance(w, str)]
    return (clip.get("app") == "kumo" or medical(clip.get("name", "")) or medical(clip.get("search", ""))
            or medical(clip.get("keyline", "")) or any(medical(w) for w in words))


def safe_keywords(clip):
    """The clip's keywords for a YouTube description line and hidden tags (rule 1.9): no medical() word, and in an
    app whose name or keywords are medical (Kumo), no split-out weight-loss word either. Old clips.json entries
    still carry loss / injection / glp1 / 瘦瘦針 / abnehmspritze until the planner rewrites them."""
    words = [w for w in clip.get("keywords") or [] if isinstance(w, str)]
    health = health_app(clip)
    return [w for w in words if not medical(w) and not (health and w.strip().casefold() in WEIGHT_WORDS)]


def youtube(clip, variant, links, limit=100):
    """(title, description, tags) for a Short: problem phrase + app name + #Shorts in the title."""
    suffix = f" | {clip.get('search') or clip.get('name', '')} #Shorts"
    lead = variant.get("lead", "")
    room = limit - len(suffix)
    title = (lead if len(lead) <= room else lead[:room - 1].rstrip() + "…") + suffix
    hashtags = ["#Shorts", *tags(clip, 2)]
    lines = [*body(clip, variant, 10_000), "", clip.get("name", ""), *links]
    keywords = safe_keywords(clip)
    if keywords:
        lines += ["", " · ".join(keywords)]
    lines += ["", " ".join(hashtags)]
    words, total = [], 0
    for w in [*keywords, *(t.lstrip("#") for t in tags(clip, 6)), clip.get("search", "")]:
        if w and w.casefold() not in {x.casefold() for x in words} and total + len(w) + 1 <= 450:
            words.append(w)
            total += len(w) + 1
    return title, "\n".join(lines), words


def pin_title(clip, variant, limit=100):
    """Pinterest / Tumblr title: the problem line, then the searchable keyline, then the app."""
    parts = [variant.get("lead", ""), clip.get("keyline", ""), clip.get("search") or clip.get("name", "")]
    title = " | ".join(p for i, p in enumerate(parts) if p and p not in parts[:i])
    return title if len(title) <= limit else title[:limit - 1].rstrip() + "…"


@lru_cache(maxsize=1)
def _feed():
    return _load(CLIPS, {})


def seo_for(app, locale, data=None):
    """{"tags", "keywords", "keyline"} for a card's app and locale ({} when the planner has none)."""
    data = _feed() if data is None else data
    clip = (data.get("clips") or {}).get(f"{app}/{locale}")
    if clip and (clip.get("tags") or clip.get("keyline")):
        return {"tags": clip.get("tags") or [], "keywords": clip.get("keywords") or [],
                "keyline": clip.get("keyline", "")}
    return ((data.get("seo") or {}).get(app) or {}).get(locale) or {}


def card_tags(app, locale, limit=5, data=None):
    return tags({"tags": seo_for(app, locale, data).get("tags") or [], "locale": locale}, limit)


def card_alt(name, caption, app, locale, data=None, limit=500):
    """Alt text for a card image: what the card says, the app, and its search phrase."""
    lines = [line for line in caption.split("\n") if line.strip()][:3]
    keyline = seo_for(app, locale, data).get("keyline", "")
    text = " — ".join(p for p in [name, *lines, keyline] if p)
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


@lru_cache(maxsize=1)
def _terms():
    return _load(SEARCH_TERMS, {})


STOREFRONT = re.compile(r"apps\.apple\.com/([a-z]{2})/", re.I)
TERM_MAX_AGE = 21  # days: an older rank reading no longer says where the app stands
MAX_RANK = 10  # past #10 people rarely scroll down to the app: the caption keeps the brand name


def search_term(app, locale, store_url="", fallback="", data=None, day=None):
    """The App Store search term for the caption's search line: the term the app is closest to the top 3 on
    in the post's storefront (the clip's store link first, then the locale's other storefronts: paid there
    in the last 7 days first, then the bigger market), from search-terms.json. `fallback` (the clip's own
    search phrase / store name) when there is no fresh entry in that language."""
    data = _terms() if data is None else data
    app = str(app or "")
    per = ((data.get("apps") or {}).get(app[:-2] if app.endswith("_b") else app) or {})
    if not isinstance(per, dict) or not locale:
        return fallback
    m = STOREFRONT.search(store_url or "")
    others = sorted((sf for sf, e in per.items() if isinstance(e, dict) and e.get("locale") == locale),
                    key=lambda sf: (not per[sf].get("paid"), -float(per[sf].get("weight") or 0), sf))
    day = day or today()
    for sf in ([m.group(1).upper()] if m else []) + others:
        entry = per.get(sf)
        if not isinstance(entry, dict) or entry.get("locale") != locale:
            continue
        term = str(entry.get("term") or "").strip()
        try:
            age = (day - dt.date.fromisoformat(str(entry.get("date")))).days
        except ValueError:
            continue
        try:
            rank = int(entry.get("rank") or 0)
        except (TypeError, ValueError):
            continue
        if term and 1 <= rank <= MAX_RANK and -1 <= age <= TERM_MAX_AGE:
            return term
    return fallback


def clip_search(clip, data=None, day=None):
    """search_term() for a hook clip; its planner search phrase when the rank data has nothing."""
    return search_term(clip.get("app", ""), clip.get("locale", ""), clip.get("store_url", ""),
                       clip.get("search", ""), data=data, day=day)


def today():
    return dt.datetime.now(dt.timezone.utc).date()
