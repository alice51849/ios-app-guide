#!/usr/bin/env python3
"""The Instagram profile-link hub, https://open.cait518.cc/ig/ (ig_bio.HUB_URL).

Instagram only links from the profile, so the profile link has to lead straight to the app people just saw
(owner 2026-10-17: 「你IG貼文的留言 都沒有成功變成連結耶 沒辦法直接點」). This builds that one page from data
already in the repo:

- top: the apps of the newest Instagram posts (clip-posts.json, channels instagram and instagram_feed), newest
  first, up to RECENT apps, each one a big button straight to the App Store in the post's own storefront, plus
  Google Play when the app is live on Android (the Android snapshot; unreadable = no page, never a guess);
- below: every verified live app (data/verified-ios-app-finder-catalog.json) by category, the focus app first.

Every button carries pt=118326163 and ct=ig_bio_<app> (00_GrowthEngine agent/ct_codes.py reads it as the
instagram row: the downloads the Instagram posts bring in through the profile). The words (headings,
categories, app names) follow the visitor's phone language through a few lines of inline script - no
tracking, no external script, nothing sent anywhere; without script the page reads in English. Captions
carry no URL: they say "📲 Download via the link in bio" and name the app in its brand hashtag (#Mochi,
ig_bio.py), and that name is on this page in every case: the latest-posts block shows the post's own name,
the full list the localized store name (clips.json, the utility-card names, else the catalog name).

The page goes to .github/growth/ig-hub/index.html every time an Instagram post is recorded (the "Record the
post link" steps) and once a day (ig-bio-hub.yml); the root site (alice51849.github.io, its ig-hub.yml)
mirrors it to /ig/ every ~10 minutes. App icons are the App Store artwork, cached in
.github/growth/ig-hub/artwork.json (a missing one is looked up once, best effort; no icon is no problem).

    python3 ig_bio_hub.py build [--offline]   # write the page (and refresh missing icons unless --offline)
    python3 ig_bio_hub.py check               # exit 1 when the committed page is not what build writes now
    python3 ig_bio_hub.py live                # read the hub URL back: 200, the page marker, the newest app
    python3 ig_bio_hub.py whoami              # IG_ACCESS_TOKEN: print the account's username and website only
"""
import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import ig_bio as IGB
from social_post_common import android_apps, play_store_url

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
GROWTH = HERE.parent / "growth"
CLIPS = GROWTH / "clips.json"
POSTS = GROWTH / "clip-posts.json"
FOCUS = GROWTH / "focus.json"
CATALOG = ROOT / "data" / "verified-ios-app-finder-catalog.json"
OUT_DIR = GROWTH / "ig-hub"
OUT = OUT_DIR / "index.html"
ARTWORK = OUT_DIR / "artwork.json"

RECENT = 6                                   # apps in the latest-posts block
IG_CHANNELS = ("instagram", "instagram_feed")
PROVIDER = "118326163"
MARKER = "lumi-ig-hub"                       # <meta name=...>: the root-site mirror refuses a page without it
GRAPH = "https://graph.instagram.com/v21.0"
UA = "lumi-ig-hub/1.0"
APP_ID_RE = re.compile(r"/id(\d+)")
APP_KEY_RE = re.compile(r"^[a-z0-9]{1,23}$")   # ig_bio_<key> stays inside the 30-character App Store ct
CATEGORY_ORDER = ("productivity", "photo-utility", "kids", "education", "finance", "travel", "health",
                  "lifestyle", "sleep-sound", "utility")

# Page words per caption locale (clip_posts.TEXT). "c_<category>" = the catalog's category headings.
WORDS = {
    "en": {"title": "Lumi Studio · Apps", "h1": "Lumi Studio apps",
           "lead": "Tap the app you saw in our post. It opens right in the App Store.",
           "latest": "From our latest posts", "all": "All apps", "home": "More about Lumi Studio",
           "c_productivity": "Productivity", "c_photo-utility": "Photo & utility", "c_kids": "Kids & learning",
           "c_education": "Education", "c_finance": "Money & travel", "c_travel": "Travel", "c_health": "Health",
           "c_lifestyle": "Lifestyle", "c_sleep-sound": "Sleep & focus", "c_utility": "More"},
    "zh-Hant": {"title": "Lumi Studio · App 下載", "h1": "Lumi Studio 的 App",
                "lead": "點一下你在貼文裡看到的 App，直接在 App Store 打開。",
                "latest": "最新貼文", "all": "全部 App", "home": "更多 Lumi Studio",
                "c_productivity": "效率工具", "c_photo-utility": "照片與實用工具", "c_kids": "兒童與學習",
                "c_education": "學習", "c_finance": "理財與旅行", "c_travel": "旅行", "c_health": "健康",
                "c_lifestyle": "生活", "c_sleep-sound": "睡眠與專注", "c_utility": "更多"},
    "zh-Hans": {"title": "Lumi Studio · App 下载", "h1": "Lumi Studio 的 App",
                "lead": "点一下你在帖子里看到的 App，直接在 App Store 打开。",
                "latest": "最新帖子", "all": "全部 App", "home": "更多 Lumi Studio",
                "c_productivity": "效率工具", "c_photo-utility": "照片与实用工具", "c_kids": "儿童与学习",
                "c_education": "学习", "c_finance": "理财与旅行", "c_travel": "旅行", "c_health": "健康",
                "c_lifestyle": "生活", "c_sleep-sound": "睡眠与专注", "c_utility": "更多"},
    "ja": {"title": "Lumi Studio · アプリ", "h1": "Lumi Studio のアプリ",
           "lead": "投稿で見たアプリをタップすると、App Storeがすぐ開きます。",
           "latest": "最新の投稿から", "all": "すべてのアプリ", "home": "Lumi Studio について",
           "c_productivity": "仕事効率化", "c_photo-utility": "写真・ツール", "c_kids": "子ども・学び",
           "c_education": "教育", "c_finance": "お金・旅行", "c_travel": "旅行", "c_health": "ヘルスケア",
           "c_lifestyle": "ライフスタイル", "c_sleep-sound": "睡眠・集中", "c_utility": "その他"},
    "ko": {"title": "Lumi Studio · 앱", "h1": "Lumi Studio 앱",
           "lead": "게시물에서 본 앱을 누르면 App Store가 바로 열려요.",
           "latest": "최신 게시물", "all": "모든 앱", "home": "Lumi Studio 더 보기",
           "c_productivity": "생산성", "c_photo-utility": "사진·유틸리티", "c_kids": "어린이 학습",
           "c_education": "교육", "c_finance": "돈·여행", "c_travel": "여행", "c_health": "건강",
           "c_lifestyle": "라이프스타일", "c_sleep-sound": "수면·집중", "c_utility": "더 보기"},
    "de": {"title": "Lumi Studio · Apps", "h1": "Apps von Lumi Studio",
           "lead": "Tippe auf die App aus unserem Beitrag – sie öffnet sich direkt im App Store.",
           "latest": "Aus unseren neuesten Beiträgen", "all": "Alle Apps", "home": "Mehr über Lumi Studio",
           "c_productivity": "Produktivität", "c_photo-utility": "Foto & Werkzeuge", "c_kids": "Kinder & Lernen",
           "c_education": "Bildung", "c_finance": "Geld & Reisen", "c_travel": "Reisen", "c_health": "Gesundheit",
           "c_lifestyle": "Lifestyle", "c_sleep-sound": "Schlaf & Fokus", "c_utility": "Weitere"},
    "fr": {"title": "Lumi Studio · Apps", "h1": "Les apps Lumi Studio",
           "lead": "Touchez l’app vue dans notre publication : elle s’ouvre directement dans l’App Store.",
           "latest": "Nos dernières publications", "all": "Toutes les apps", "home": "En savoir plus sur Lumi Studio",
           "c_productivity": "Productivité", "c_photo-utility": "Photo et outils", "c_kids": "Enfants et apprentissage",
           "c_education": "Éducation", "c_finance": "Argent et voyage", "c_travel": "Voyage", "c_health": "Santé",
           "c_lifestyle": "Style de vie", "c_sleep-sound": "Sommeil et concentration", "c_utility": "Autres"},
    "es": {"title": "Lumi Studio · Apps", "h1": "Apps de Lumi Studio",
           "lead": "Toca la app que viste en nuestra publicación: se abre directamente en el App Store.",
           "latest": "De nuestras últimas publicaciones", "all": "Todas las apps", "home": "Más sobre Lumi Studio",
           "c_productivity": "Productividad", "c_photo-utility": "Foto y utilidades", "c_kids": "Niños y aprendizaje",
           "c_education": "Educación", "c_finance": "Dinero y viajes", "c_travel": "Viajes", "c_health": "Salud",
           "c_lifestyle": "Estilo de vida", "c_sleep-sound": "Sueño y concentración", "c_utility": "Más"},
    "id": {"title": "Lumi Studio · Aplikasi", "h1": "Aplikasi Lumi Studio",
           "lead": "Ketuk aplikasi yang kamu lihat di postingan kami, langsung terbuka di App Store.",
           "latest": "Dari postingan terbaru", "all": "Semua aplikasi", "home": "Tentang Lumi Studio",
           "c_productivity": "Produktivitas", "c_photo-utility": "Foto & utilitas", "c_kids": "Anak & belajar",
           "c_education": "Pendidikan", "c_finance": "Keuangan & perjalanan", "c_travel": "Perjalanan",
           "c_health": "Kesehatan", "c_lifestyle": "Gaya hidup", "c_sleep-sound": "Tidur & fokus",
           "c_utility": "Lainnya"},
    "vi": {"title": "Lumi Studio · Ứng dụng", "h1": "Ứng dụng của Lumi Studio",
           "lead": "Chạm vào ứng dụng bạn thấy trong bài đăng, App Store sẽ mở ngay.",
           "latest": "Từ bài đăng mới nhất", "all": "Tất cả ứng dụng", "home": "Thêm về Lumi Studio",
           "c_productivity": "Năng suất", "c_photo-utility": "Ảnh & tiện ích", "c_kids": "Trẻ em & học tập",
           "c_education": "Giáo dục", "c_finance": "Tiền & du lịch", "c_travel": "Du lịch", "c_health": "Sức khỏe",
           "c_lifestyle": "Phong cách sống", "c_sleep-sound": "Ngủ & tập trung", "c_utility": "Khác"},
    "th": {"title": "Lumi Studio · แอป", "h1": "แอปของ Lumi Studio",
           "lead": "แตะแอปที่คุณเห็นในโพสต์ของเรา แล้ว App Store จะเปิดขึ้นทันที",
           "latest": "จากโพสต์ล่าสุด", "all": "แอปทั้งหมด", "home": "เกี่ยวกับ Lumi Studio",
           "c_productivity": "ประสิทธิภาพการทำงาน", "c_photo-utility": "รูปภาพและเครื่องมือ",
           "c_kids": "เด็กและการเรียนรู้", "c_education": "การศึกษา", "c_finance": "การเงินและการเดินทาง",
           "c_travel": "การเดินทาง", "c_health": "สุขภาพ", "c_lifestyle": "ไลฟ์สไตล์",
           "c_sleep-sound": "การนอนและสมาธิ", "c_utility": "อื่น ๆ"},
    "pt-BR": {"title": "Lumi Studio · Apps", "h1": "Apps da Lumi Studio",
              "lead": "Toque no app que você viu no nosso post: ele abre direto na App Store.",
              "latest": "Dos nossos posts mais recentes", "all": "Todos os apps", "home": "Mais sobre a Lumi Studio",
              "c_productivity": "Produtividade", "c_photo-utility": "Foto e utilitários",
              "c_kids": "Crianças e aprendizado", "c_education": "Educação", "c_finance": "Dinheiro e viagem",
              "c_travel": "Viagem", "c_health": "Saúde", "c_lifestyle": "Estilo de vida",
              "c_sleep-sound": "Sono e foco", "c_utility": "Mais"},
    "cs": {"title": "Lumi Studio · Aplikace", "h1": "Aplikace od Lumi Studio",
           "lead": "Klepněte na aplikaci z našeho příspěvku – otevře se rovnou v App Storu.",
           "latest": "Z našich nejnovějších příspěvků", "all": "Všechny aplikace", "home": "Více o Lumi Studio",
           "c_productivity": "Produktivita", "c_photo-utility": "Fotky a nástroje", "c_kids": "Děti a učení",
           "c_education": "Vzdělávání", "c_finance": "Peníze a cestování", "c_travel": "Cestování",
           "c_health": "Zdraví", "c_lifestyle": "Životní styl", "c_sleep-sound": "Spánek a soustředění",
           "c_utility": "Další"},
    "pl": {"title": "Lumi Studio · Aplikacje", "h1": "Aplikacje Lumi Studio",
           "lead": "Stuknij aplikację z naszego posta – otworzy się od razu w App Store.",
           "latest": "Z naszych najnowszych postów", "all": "Wszystkie aplikacje", "home": "Więcej o Lumi Studio",
           "c_productivity": "Produktywność", "c_photo-utility": "Zdjęcia i narzędzia", "c_kids": "Dzieci i nauka",
           "c_education": "Edukacja", "c_finance": "Pieniądze i podróże", "c_travel": "Podróże",
           "c_health": "Zdrowie", "c_lifestyle": "Styl życia", "c_sleep-sound": "Sen i skupienie",
           "c_utility": "Więcej"},
    "nl": {"title": "Lumi Studio · Apps", "h1": "Apps van Lumi Studio",
           "lead": "Tik op de app uit onze post: hij opent meteen in de App Store.",
           "latest": "Uit onze nieuwste posts", "all": "Alle apps", "home": "Meer over Lumi Studio",
           "c_productivity": "Productiviteit", "c_photo-utility": "Foto & hulpmiddelen", "c_kids": "Kinderen & leren",
           "c_education": "Onderwijs", "c_finance": "Geld & reizen", "c_travel": "Reizen", "c_health": "Gezondheid",
           "c_lifestyle": "Lifestyle", "c_sleep-sound": "Slaap & focus", "c_utility": "Meer"},
    "da": {"title": "Lumi Studio · Apps", "h1": "Apps fra Lumi Studio",
           "lead": "Tryk på appen fra vores opslag – den åbner direkte i App Store.",
           "latest": "Fra vores nyeste opslag", "all": "Alle apps", "home": "Mere om Lumi Studio",
           "c_productivity": "Produktivitet", "c_photo-utility": "Foto og værktøjer", "c_kids": "Børn og læring",
           "c_education": "Uddannelse", "c_finance": "Penge og rejser", "c_travel": "Rejser", "c_health": "Sundhed",
           "c_lifestyle": "Livsstil", "c_sleep-sound": "Søvn og fokus", "c_utility": "Flere"},
    "nb": {"title": "Lumi Studio · Apper", "h1": "Apper fra Lumi Studio",
           "lead": "Trykk på appen fra innlegget vårt – den åpnes rett i App Store.",
           "latest": "Fra de nyeste innleggene våre", "all": "Alle apper", "home": "Mer om Lumi Studio",
           "c_productivity": "Produktivitet", "c_photo-utility": "Foto og verktøy", "c_kids": "Barn og læring",
           "c_education": "Utdanning", "c_finance": "Penger og reise", "c_travel": "Reise", "c_health": "Helse",
           "c_lifestyle": "Livsstil", "c_sleep-sound": "Søvn og fokus", "c_utility": "Flere"},
    "el": {"title": "Lumi Studio · Εφαρμογές", "h1": "Οι εφαρμογές της Lumi Studio",
           "lead": "Πατήστε την εφαρμογή από την ανάρτησή μας και ανοίγει αμέσως στο App Store.",
           "latest": "Από τις πιο πρόσφατες αναρτήσεις", "all": "Όλες οι εφαρμογές",
           "home": "Περισσότερα για τη Lumi Studio",
           "c_productivity": "Παραγωγικότητα", "c_photo-utility": "Φωτογραφίες και εργαλεία",
           "c_kids": "Παιδιά και μάθηση", "c_education": "Εκπαίδευση", "c_finance": "Χρήματα και ταξίδια",
           "c_travel": "Ταξίδια", "c_health": "Υγεία", "c_lifestyle": "Τρόπος ζωής",
           "c_sleep-sound": "Ύπνος και συγκέντρωση", "c_utility": "Περισσότερα"},
    "ar": {"title": "Lumi Studio · التطبيقات", "h1": "تطبيقات Lumi Studio",
           "lead": "اضغط على التطبيق الذي رأيته في منشورنا ليفتح مباشرة في App Store.",
           "latest": "من أحدث منشوراتنا", "all": "كل التطبيقات", "home": "المزيد عن Lumi Studio",
           "c_productivity": "الإنتاجية", "c_photo-utility": "الصور والأدوات", "c_kids": "الأطفال والتعلّم",
           "c_education": "التعليم", "c_finance": "المال والسفر", "c_travel": "السفر", "c_health": "الصحة",
           "c_lifestyle": "نمط الحياة", "c_sleep-sound": "النوم والتركيز", "c_utility": "المزيد"},
    # 2026-10-22: clip_posts.TEXT gained ru / sk captions (10-21 small-country push); without their words the
    # page test failed and ig-bio-hub.yml stopped rebuilding the page (it kept serving the 10-20 build).
    "ru": {"title": "Lumi Studio · Приложения", "h1": "Приложения Lumi Studio",
           "lead": "Нажмите на приложение из нашего поста — оно сразу откроется в App Store.",
           "latest": "Из наших последних постов", "all": "Все приложения", "home": "Подробнее о Lumi Studio",
           "c_productivity": "Продуктивность", "c_photo-utility": "Фото и инструменты", "c_kids": "Дети и обучение",
           "c_education": "Образование", "c_finance": "Деньги и путешествия", "c_travel": "Путешествия",
           "c_health": "Здоровье", "c_lifestyle": "Образ жизни", "c_sleep-sound": "Сон и концентрация",
           "c_utility": "Ещё"},
    "sk": {"title": "Lumi Studio · Aplikácie", "h1": "Aplikácie od Lumi Studio",
           "lead": "Ťuknite na aplikáciu z nášho príspevku – otvorí sa priamo v App Store.",
           "latest": "Z našich najnovších príspevkov", "all": "Všetky aplikácie", "home": "Viac o Lumi Studio",
           "c_productivity": "Produktivita", "c_photo-utility": "Fotky a nástroje", "c_kids": "Deti a učenie",
           "c_education": "Vzdelávanie", "c_finance": "Peniaze a cestovanie", "c_travel": "Cestovanie",
           "c_health": "Zdravie", "c_lifestyle": "Životný štýl", "c_sleep-sound": "Spánok a sústredenie",
           "c_utility": "Ďalšie"},
}


def load_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        if default is not None:
            return default
        raise


def norm_key(app):
    """clips.json uses <app>_b for the second clip set of one app; the hub has one row per app."""
    return re.sub(r"_[a-z]$", "", str(app or ""))


def ios_id_of(url):
    m = APP_ID_RE.search(str(url or ""))
    return m.group(1) if m else ""


def storefront_of(url):
    """'tw' in https://apps.apple.com/tw/app/id1 (None without one)."""
    parts = urllib.parse.urlsplit(str(url or "")).path.strip("/").split("/")
    return parts[0] if len(parts) >= 3 and parts[1] == "app" and re.fullmatch(r"[a-z]{2}", parts[0]) else None


def campaign(app):
    if not APP_KEY_RE.fullmatch(app):
        raise ValueError(f"app key {app!r} does not fit the ig_bio_<app> campaign")
    return f"{IGB.CT_PREFIX}{app}"


def app_store_url(ios_id, app, storefront=None):
    query = urllib.parse.urlencode({"pt": PROVIDER, "ct": campaign(app), "mt": "8"})
    country = f"{storefront}/" if storefront else ""
    return f"https://apps.apple.com/{country}app/id{ios_id}?{query}"


class Data:
    """Everything the page needs, read once: the verified catalog, clips, the post log, focus apps, names."""

    def __init__(self, catalog=None, clips=None, posts=None, focus=None, utility_apps=None, artwork=None):
        catalog = load_json(CATALOG) if catalog is None else catalog
        self.apps = {}
        for a in catalog.get("apps", []):
            if a.get("verified_live") and a.get("key") and a.get("app_store_id"):
                self.apps[a["key"]] = a
        if not self.apps:
            raise ValueError("the verified app catalog is empty: no hub without the app list")
        self.by_ios = {str(a["app_store_id"]): k for k, a in self.apps.items()}
        data = load_json(CLIPS, {}) if clips is None else clips
        self.clips = data.get("clips", {})
        self.posts = (load_json(POSTS, {}) if posts is None else posts).get("posts", [])
        focus = load_json(FOCUS, {}) if focus is None else focus
        self.focus = [f.get("key") for f in focus.get("apps", []) if f.get("key")]
        if utility_apps is None:
            import utility_cards
            utility_apps = utility_cards.APPS
        self.utility = utility_apps
        self.artwork = load_json(ARTWORK, {}) if artwork is None else artwork
        # Localized store names: the clip names (the plain clip before its _b set), then the utility-card names.
        self.names = {}
        for _k, c in sorted(self.clips.items(), key=lambda kv: (str(kv[1].get("app", "")).endswith("_b"), kv[0])):
            key = self._app_of_ios(ios_id_of(c.get("store_url"))) or norm_key(c.get("app"))
            if key in self.apps and c.get("name") and c.get("locale"):
                self.names.setdefault(key, {}).setdefault(c["locale"], " ".join(c["name"].split()))
        for key, u in utility_apps.items():
            key = self._app_of_ios(u.get("id")) or key
            for loc, name in (u.get("names") or {}).items():
                if key in self.apps:
                    self.names.setdefault(key, {}).setdefault(loc, name)

    def _app_of_ios(self, ios):
        return self.by_ios.get(str(ios or ""))

    def name(self, key, locale):
        """The app's store name in that locale (what a caption quotes), else the catalog name."""
        names = self.names.get(key, {})
        return names.get(locale) or names.get((locale or "").split("-")[0]) or self.apps[key]["name"]

    def post_item(self, post):
        """(app key, locale, name, storefront, hook) of one logged Instagram post, or None (unknown app)."""
        clip_key = str(post.get("clip") or "")
        parts = clip_key.split("/")
        clip, locale, key = None, parts[-1] if parts else "en", ""
        if parts[0] == "utility" and len(parts) >= 5:          # utility/<type>/<app>/<item>/<locale>
            u = self.utility.get(parts[2]) or {}
            key = norm_key(self._app_of_ios(u.get("id")) or parts[2])
            # The card caption quotes the utility name (utility_cards.app_name: "Aim990"); the fuller store name
            # of that locale is shown when it still holds those words.
            quoted = (u.get("names") or {}).get(locale) or u.get("name") or ""
            full = self.name(key, locale) if key in self.apps else ""
            name = full if quoted and IGB.short_name(quoted) in full else (quoted or full)
            store = {"zh-Hant": "tw", "ja": "jp", "ko": "kr", "en": "us"}.get(locale)
        else:
            if parts[0] == "feed" and len(parts) >= 3:          # feed/<app>/<locale>: store-screenshot carousel
                clip = self.clips.get(f"{parts[1]}/{parts[-1]}")
                key = parts[1]
            else:                                              # <app>[_b]/<locale>: a hook clip
                clip = self.clips.get(clip_key)
                key = parts[0]
            if clip:
                key = self._app_of_ios(ios_id_of(clip.get("store_url"))) or norm_key(clip.get("app"))
                locale = clip.get("locale") or locale
            name = (clip or {}).get("name") or ""
            store = storefront_of((clip or {}).get("store_url"))
        key = norm_key(key)
        if key not in self.apps:
            return None
        hooks = (clip or {}).get("hooks") or []
        hook = next((h.get("lead") for h in hooks if h.get("id") == post.get("variant") and h.get("lead")), None)
        hook = hook or (hooks[0].get("lead") if hooks else (clip or {}).get("hook")) or ""
        return {"key": key, "locale": locale, "name": " ".join((name or self.name(key, locale)).split()),
                "storefront": store, "hook": hook, "posted_at": post.get("posted_at", "")}

    def recent(self, n=RECENT):
        """The apps of the newest Instagram posts, newest first, one row per app."""
        out, seen = [], set()
        rows = [p for p in self.posts if p.get("channel") in IG_CHANNELS and p.get("posted_at")]
        for post in sorted(rows, key=lambda p: (p["posted_at"], p.get("clip", "")), reverse=True):
            item = self.post_item(post)
            if not item or item["key"] in seen:
                continue
            seen.add(item["key"])
            out.append(item)
            if len(out) >= n:
                break
        return out

    def groups(self):
        """[(category, [app key, ...])]: the fixed category order, the focus app first, then by name."""
        cats = {}
        for key, a in self.apps.items():
            cats.setdefault(a.get("category") or "utility", []).append(key)
        order = list(CATEGORY_ORDER) + sorted(c for c in cats if c not in CATEGORY_ORDER)
        rank = {k: i for i, k in enumerate(self.focus)}
        return [(c, sorted(cats[c], key=lambda k: (rank.get(k, len(rank)), self.apps[k]["name"].casefold(), k)))
                for c in order if c in cats]


_DATA = None


def display_name(ios_id, locale):
    """The name the hub shows for this app to a visitor in that locale - what an Instagram comment or reply
    tells people to tap ('' when the app is not on the hub or the data cannot be read)."""
    global _DATA
    try:
        if _DATA is None:
            _DATA = Data()
        key = _DATA.by_ios.get(str(ios_id or ""))
        return _DATA.name(key, locale) if key else ""
    except (OSError, ValueError, KeyError):
        return ""


def play_link(ios_id, key):
    """The Google Play button with utm_source=ig_bio_<app>, the same token as the page's App Store ct (the hub keeps
    its own per-app row, like the App Store buttons, and the root-site mirror ig_hub_sync.py refuses any other
    referrer: the coarse "social" token sent since 10-17 kept the live page stuck on the 10-17 build).
    None when not on Android; SnapshotMissing when unreadable."""
    return play_store_url(ios_id, campaign(key), channel_level=False)


def fetch_artwork(ids, opener=urllib.request.urlopen, countries=("us", "tw", "jp")):
    """{iOS id: 100 px App Store icon URL} for the ids the cache lacks (one lookup per storefront tried)."""
    found, left = {}, [str(i) for i in ids]
    for country in countries:
        if not left:
            break
        url = f"https://itunes.apple.com/lookup?id={','.join(left)}&country={country}&entity=software"
        try:
            with opener(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=15) as r:
                rows = json.loads(r.read()).get("results", [])
        except (OSError, ValueError) as exc:
            print(f"ig_bio_hub: icon lookup skipped ({exc.__class__.__name__})")
            break
        for row in rows:
            art = str(row.get("artworkUrl100") or "")
            if row.get("trackId") and art.startswith("https://") and "mzstatic.com/" in art:
                found[str(row["trackId"])] = art
        left = [i for i in left if i not in found]
    return found


def _esc(text):
    return html.escape(str(text or ""), quote=True)


def _json_script(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).replace("</", "<\\/")


def _icon(data, ios_id, size):
    art = data.artwork.get(str(ios_id))
    if not art:
        return f'<span class="ic ph" style="width:{size}px;height:{size}px" aria-hidden="true"></span>'
    return (f'<img class="ic" src="{_esc(art)}" alt="" width="{size}" height="{size}" loading="lazy" '
            f'decoding="async" referrerpolicy="no-referrer">')


def _row(data, key, name, sub, storefront, size, lang=None, localize=False):
    a = data.apps[key]
    ios = str(a["app_store_id"])
    store = app_store_url(ios, key, storefront)
    play = play_link(ios, key)
    lang_attr = f' lang="{_esc(lang)}"' if lang else ""
    name_attr = f' data-n="{_esc(key)}"' if localize else ""
    sub_html = f'<span class="sb">{_esc(sub)}</span>' if sub else '<span class="sb" hidden></span>'
    out = [f'<li class="app"{lang_attr} data-app="{_esc(key)}">',
           f'<a class="main" href="{_esc(store)}">{_icon(data, ios, size)}'
           f'<span class="tx"><span class="nm"{name_attr}>{_esc(name)}</span>{sub_html}</span>'
           f'<span class="go">App Store</span></a>']
    if play:
        out.append(f'<a class="gp" href="{_esc(play)}">Google Play</a>')
    out.append("</li>")
    return "".join(out)


CSS = """
:root{--bg:#fffaf0;--fg:#1d1a16;--mute:#6b6257;--card:#fff;--line:#eadfcd;--go:#0a66ff;--gofg:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#14120f;--fg:#f4efe7;--mute:#b3a998;--card:#211e1a;--line:#3a342c;--go:#3d8bff;--gofg:#fff}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Noto Sans","PingFang TC","Hiragino Sans","Apple SD Gothic Neo",sans-serif}
main{max-width:560px;margin:0 auto;padding:20px 16px 40px}
.brand{font-weight:700;letter-spacing:.02em;color:var(--mute);font-size:.9rem;margin:0}
h1{font-size:1.5rem;margin:.2rem 0 .3rem}.lead{margin:0 0 1rem;color:var(--mute)}
h2{font-size:1.05rem;margin:1.6rem 0 .6rem}h3{font-size:.95rem;color:var(--mute);margin:1.2rem 0 .5rem;font-weight:600}
ul{list-style:none;margin:0;padding:0;display:grid;gap:10px}
.app{display:flex;flex-direction:column}
.main{display:flex;align-items:center;gap:12px;min-height:64px;padding:10px 12px;border:1px solid var(--line);border-radius:16px;background:var(--card);color:inherit;text-decoration:none}
.main:active{transform:scale(.99)}
.ic{flex:none;border-radius:22%;background:var(--line);object-fit:cover}
.tx{flex:1;min-width:0;display:flex;flex-direction:column}
.nm{font-weight:650;overflow-wrap:anywhere}.sb{font-size:.85rem;color:var(--mute);overflow-wrap:anywhere}
.go{flex:none;background:var(--go);color:var(--gofg);border-radius:999px;padding:8px 14px;font-weight:650;font-size:.9rem}
.gp{align-self:flex-end;margin:6px 4px 0;padding:6px 14px;border:1px solid var(--line);border-radius:999px;background:var(--card);font-size:.85rem;color:var(--go);text-decoration:none;font-weight:600}
.latest .main{min-height:80px;border-width:2px}
footer{margin-top:2rem;font-size:.85rem;color:var(--mute)}footer a{color:inherit}
"""

# Swaps the words for the visitor's phone language; reads nothing else and sends nothing.
JS = """(function(){try{
var T=JSON.parse(document.getElementById('hub-t').textContent),N=JSON.parse(document.getElementById('hub-n').textContent);
function pick(t){t=String(t||'').toLowerCase();if(t.indexOf('zh')===0)return /hant|tw|hk|mo/.test(t)?'zh-Hant':'zh-Hans';
if(t.indexOf('pt')===0)return 'pt-BR';var p=t.split('-')[0];if(p==='no'||p==='nn')p='nb';return T[p]?p:null;}
var ls=navigator.languages&&navigator.languages.length?navigator.languages:[navigator.language||'en'],l=null,i;
for(i=0;i<ls.length&&!l;i++)l=pick(ls[i]);if(!l||l==='en')return;
var d=T[l],r=document.documentElement;r.lang=l;if(l==='ar')r.dir='rtl';if(d.title)document.title=d.title;
var e=document.querySelectorAll('[data-t]');for(i=0;i<e.length;i++){var k=e[i].getAttribute('data-t');if(d[k])e[i].textContent=d[k];}
e=document.querySelectorAll('[data-n]');for(i=0;i<e.length;i++){var a=e[i].getAttribute('data-n'),m=N[a]&&N[a][l],b=e[i].textContent;
if(m&&m!==b){e[i].textContent=m;e[i].parentNode.parentNode.parentNode.lang=l;var s=e[i].nextElementSibling;
if(s&&m.indexOf(b)<0){s.textContent=b;s.hidden=false;}}}
}catch(x){}})();"""


def render(data):
    """The whole page (deterministic: the same data gives the same bytes)."""
    w = WORDS["en"]
    recent = data.recent()
    stamp = recent[0]["posted_at"] if recent else ""
    parts = ["<!doctype html>", '<html lang="en">', "<head>", '<meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">',
             f"<title>{_esc(w['title'])}</title>",
             '<meta name="description" content="Lumi Studio iPhone apps: one tap to the App Store (and Google Play).">',
             '<meta name="robots" content="noindex, follow">',
             f'<link rel="canonical" href="{_esc(IGB.HUB_URL)}">',
             '<meta name="theme-color" content="#fffaf0">',
             f'<meta name="{MARKER}" content="1">',
             f'<meta name="{MARKER}-latest" content="{_esc(stamp)}">',
             f"<style>{' '.join(CSS.split())}</style>", "</head>", "<body>", "<main>",
             '<p class="brand">Lumi Studio</p>',
             f'<h1 data-t="h1">{_esc(w["h1"])}</h1>', f'<p class="lead" data-t="lead">{_esc(w["lead"])}</p>']
    if recent:
        parts += ['<section class="latest">', f'<h2 data-t="latest">{_esc(w["latest"])}</h2>', "<ul>"]
        parts += [_row(data, it["key"], it["name"], it["hook"], it["storefront"], 64, lang=it["locale"])
                  for it in recent]
        parts += ["</ul>", "</section>"]
    parts += ['<section class="all">', f'<h2 data-t="all">{_esc(w["all"])}</h2>']
    for cat, keys in data.groups():
        label = w.get(f"c_{cat}") or data.apps[keys[0]].get("category_labels", {}).get("en") or cat
        parts += [f'<h3 data-t="c_{_esc(cat)}">{_esc(label)}</h3>', "<ul>"]
        parts += [_row(data, k, data.apps[k]["name"], "", None, 48, localize=True) for k in keys]
        parts.append("</ul>")
    parts += ["</section>",
              f'<footer><a href="https://open.cait518.cc/" data-t="home">{_esc(w["home"])}</a></footer>',
              "</main>",
              f'<script type="application/json" id="hub-t">{_json_script(WORDS)}</script>',
              f'<script type="application/json" id="hub-n">{_json_script(data.names)}</script>',
              f"<script>{JS}</script>", "</body>", "</html>"]
    return "\n".join(parts) + "\n"


def problems(page, min_links=10):
    """The checks the page must pass before it is written (the root-site mirror repeats them)."""
    out = []
    if f'<meta name="{MARKER}" content="1">' not in page:
        out.append("the page marker is missing")
    links = re.findall(r'href="(https://apps\.apple\.com/[^"]+)"', page)
    bad = [u for u in links if not re.fullmatch(r"https://apps\.apple\.com/(?:[a-z]{2}/)?app/id\d+\?pt=118326163"
                                               r"&amp;ct=ig_bio_[a-z0-9]{1,23}&amp;mt=8", u)]
    if len(links) < min_links:
        out.append(f"only {len(links)} App Store buttons")
    if bad:
        out.append(f"App Store links without pt / ct=ig_bio_<app>: {bad[:3]}")
    plays = re.findall(r'href="(https://play\.google\.com/[^"]+)"', page)
    bad = [u for u in plays if not re.fullmatch(r"https://play\.google\.com/store/apps/details\?id=[A-Za-z0-9_.]+"
                                                r"&amp;referrer=utm_source%3Dig_bio_[a-z0-9]{1,23}%26utm_campaign%3D[a-z0-9_]+", u)]
    if bad:
        out.append(f"Google Play links without the ig_bio referrer: {bad[:3]}")
    if re.search(r"<script[^>]+src=|<iframe|<form|javascript:", page, re.I):
        out.append("external script, frame or form in the page")
    if re.search(r"""href=["']http://""", page):
        out.append("plain http link")
    return out


def build(offline=False, data=None, out=OUT, artwork_path=ARTWORK):
    data = data or Data()
    if not android_apps():
        raise ValueError("the Android snapshot is missing: the Google Play buttons cannot be decided")
    missing = sorted({str(a["app_store_id"]) for a in data.apps.values()} - set(data.artwork))
    if missing and not offline:
        found = fetch_artwork(missing)
        if found:
            data.artwork.update(found)
            Path(artwork_path).parent.mkdir(parents=True, exist_ok=True)
            Path(artwork_path).write_text(json.dumps(data.artwork, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    page = render(data)
    bad = problems(page)
    if bad:
        raise ValueError("; ".join(bad))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    changed = not out.exists() or out.read_text(encoding="utf-8") != page
    if changed:
        out.write_text(page, encoding="utf-8")
    recent = ", ".join(f"{it['key']}/{it['locale']}" for it in data.recent()) or "none"
    print(f"ig_bio_hub: {'wrote' if changed else 'unchanged'} {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out} "
          f"({len(page)} bytes, {len(data.apps)} apps; latest posts: {recent})")
    return page


def check():
    page = render(Data())
    current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    if current != page:
        print("::error::ig_bio_hub: .github/growth/ig-hub/index.html is not what the post log gives now "
              "(run python3 .github/scripts/ig_bio_hub.py build)")
        return 1
    print("ig_bio_hub: the committed hub page is current")
    return 0


def _get(url, opener=urllib.request.urlopen, timeout=30):
    with opener(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "replace")


def live(url=IGB.HUB_URL, opener=urllib.request.urlopen, data=None):
    """Read the hub back: HTTP 200, the page marker, and the newest Instagram post's app on it."""
    data = data or Data()
    try:
        status, page = _get(url, opener)
    except urllib.error.HTTPError as exc:
        print(f"::error::ig_bio_hub: {url} answers HTTP {exc.code}")
        return 1
    except OSError as exc:
        print(f"::error::ig_bio_hub: {url} cannot be read ({exc.__class__.__name__})")
        return 1
    recent = data.recent(1)
    newest = recent[0]["key"] if recent else None
    ok = status == 200 and f'<meta name="{MARKER}" content="1">' in page
    has_newest = newest is None or f'data-app="{newest}"' in page.split('<section class="all">')[0]
    print(f"ig_bio_hub: {url} HTTP {status}, marker {'ok' if ok else 'MISSING'}, "
          f"newest post app {newest or '-'} {'on top' if has_newest else 'NOT on top yet'}, "
          f"{len(re.findall(r'ct=ig_bio_', page))} tracked buttons")
    if not ok:
        print(f"::error::ig_bio_hub: {url} is not the hub page")
        return 1
    if not has_newest:
        print(f"::warning::ig_bio_hub: the live hub does not show {newest} in the latest-posts block yet "
              "(the root-site mirror runs every ~10 minutes)")
    return 0


def same_page(a, b):
    """'open.cait518.cc/ig', 'https://open.cait518.cc/ig/' and 'http://www.open.cait518.cc/IG' are one page."""
    norm = lambda u: re.sub(r"^(?:https?://)?(?:www\.)?", "", str(u or "").strip(), flags=re.I).rstrip("/").lower()
    return bool(norm(a)) and norm(a) == norm(b)


TOKEN_RE = re.compile(r"(access_token=)[^&\s\"']+|\bIG[A-Za-z0-9_-]{20,}")


def _redact(text):
    return TOKEN_RE.sub(lambda m: (m.group(1) or "") + "***", str(text or ""))[:200]


def whoami(opener=urllib.request.urlopen, token=None):
    """The Instagram account's username and profile website (the bio link), and nothing else - the token
    is read from the environment and never printed. Answers (username, website or None, note)."""
    token = (token if token is not None else os.environ.get("IG_ACCESS_TOKEN", "")).strip()
    if not token:
        print("ig_bio_hub: IG_ACCESS_TOKEN is not set; nothing to look up")
        return None, None, "no token"

    def ask(fields):
        q = urllib.parse.urlencode({"fields": fields, "access_token": token})
        try:
            _status, body = _get(f"{GRAPH}/me?{q}", opener)
            return json.loads(body), None
        except urllib.error.HTTPError as exc:
            try:
                err = json.loads(exc.read().decode("utf-8", "replace")).get("error", {})
                why = f"HTTP {exc.code}: {err.get('message') or err}"
            except (OSError, ValueError):
                why = f"HTTP {exc.code}"
            return None, _redact(why)
        except (OSError, ValueError) as exc:
            return None, exc.__class__.__name__

    me, why = ask("username,website")
    note = ""
    if me is None:
        me, why2 = ask("username")
        note = f"the Instagram API does not give the profile website to this token ({why})"
        if me is None:
            print(f"::error::ig_bio_hub: the account cannot be read ({why2})")
            return None, None, why2
    username = me.get("username") or ""
    website = me.get("website") if "website" in me else None
    if website is None and not note:
        note = "the Instagram API answered without a website field (none set, or not shared with this token)"
    print(f"username: {username}")
    print(f"website: {website if website is not None else '(not readable: ' + note + ')'}")
    if website is not None:
        points = same_page(website, IGB.HUB_URL)
        print(f"bio link points to the hub {IGB.HUB_URL}: {'yes' if points else 'NO'}")
        if not points:
            print(f"::warning::ig_bio_hub: the Instagram profile link is {website or '(empty)'}, not {IGB.HUB_URL}")
    return username, website, note


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["build", "check", "live", "whoami"])
    ap.add_argument("--offline", action="store_true", help="build: no icon lookup")
    ap.add_argument("--url", default=IGB.HUB_URL, help="live: the URL to read back")
    args = ap.parse_args(argv)
    if args.cmd == "build":
        build(offline=args.offline)
        return 0
    if args.cmd == "check":
        return check()
    if args.cmd == "live":
        return live(args.url)
    username, _website, _note = whoami()
    return 0 if username else 1


if __name__ == "__main__":
    sys.exit(main())
