#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多語 GEO 足跡產生器 — 為每個 app × 每個語言產出「機器可讀資訊頁」(給 LLM 爬)。

重用 data/<app>_full.json 內已策展的 50 語文案(name/subtitle/description/
keywords/promotionalText),不重譯。每頁含 Schema.org SoftwareApplication + FAQPage
的 JSON-LD(LLM 最愛的結構化來源),並用 hreflang 互連各語版本。

輸出:
    geo/pages/<locale>/<key>.html   每 app 每語一頁
    geo/pages/<locale>/index.html   每語 app 目錄
    geo/pages/index.html            根語言中樞(hreflang x-default)

用法:
    venv/bin/python geo/build_pages_i18n.py                 # 全部 app 全部語
    venv/bin/python geo/build_pages_i18n.py cvdesk          # 單一 app 全部語
    venv/bin/python geo/build_pages_i18n.py cvdesk ja de-DE # 單 app 指定語
"""
import html
import json
import os
import re
import sys
import unicodedata
from functools import lru_cache

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))
from videogen.registry import APPS, APPSTORE, appstore_url  # noqa: E402
from aeo_pages import pricing_profile  # noqa: E402
from app_store_storefronts import (  # noqa: E402
    LOCALE_STOREFRONTS,
    load_storefront_availability,
    load_storefront_details,
    localized_storefront_detail,
    verified_app_store_url,
)
from appstore_live import live_app_keys  # noqa: E402
from external_app_locales import (  # noqa: E402
    EXTERNAL_APP_LOCALES,
    EXTERNAL_APP_LOCALE_OVERRIDES,
)
from gen_feed import feed_discovery_links  # noqa: E402
from official_locales import (  # noqa: E402
    OFFICIAL_LOCALES,
    require_official_locale_coverage,
)

PAGES = os.environ.get("GEO_PAGES", os.path.join(HERE, "pages"))
DATA = os.path.join(ROOT, "data")
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")


# registry key -> data/<file>_full.json
KEY2DATA = {
    "snapport": "snapport_full.json",
    "sononote": "sono_full.json",
    "cvdesk": "cv_full.json",
    "picclear": "picclear_full.json",
    "scanto": "scanto_full.json",
    "cyca": "cyca_full.json",
    "gmoney": "gmoney_full.json",
    "hourstag": "hourstag_full.json",
    "lockhour": "lockhour_full.json",
    "unblurry": "unblurry_full.json",
    "photocream": "photocream_full.json",
    "lumiletters": "letters_lite_full.json",
    "lumimath": "math_planet_full.json",
    "lumimission": "mission_routines_full.json",
    "lumiweather": "weather_full.json",
    "lumiletterspro": "letters_pro_full.json",
    "lumimathpro": "math_pro_full.json",
    "lumimissionpro": "mission_pro_full.json",
    "lumibopomofo": "bopomofo_full.json",
    "lumibopomofopro": "bopomofo_pro_full.json",
    "zodira": "zodira_full.json",
    "aim990": "aim990_full.json",
    "wordmate": "wordmate_full.json",
    "mochi": "mochi_full.json",
    "tripbeelite": "tripbeelite_full.json",
    "dailymate": "dailymate_full.json",
    "sereno": "sereno_full.json",
    "tripbee": "tripbee_full.json",
    "tripplanet": "tripplanet_full.json",
}

SCHEMA_CAT = {
    "photo-utility": "PhotographyApplication",
    "productivity": "BusinessApplication",
    "kids": "EducationalApplication",
    "education": "EducationalApplication",
    "finance": "FinanceApplication",
    "utility": "UtilitiesApplication",
    "health": "HealthApplication",
    "lifestyle": "LifestyleApplication",
    "sleep-sound": "LifestyleApplication",
    "travel": "TravelApplication",
}

RTL = {"ar", "he", "ur"}
NATIVE_SCRIPT_PATTERNS = {
    "ar-SA": r"[\u0600-\u06ff]",
    "bn-BD": r"[\u0980-\u09ff]",
    "el": r"[\u0370-\u03ff]",
    "gu-IN": r"[\u0a80-\u0aff]",
    "he": r"[\u0590-\u05ff]",
    "hi": r"[\u0900-\u097f]",
    "ja": r"[\u3040-\u30ff\u3400-\u9fff]",
    "kn-IN": r"[\u0c80-\u0cff]",
    "ko": r"[\uac00-\ud7af]",
    "ml-IN": r"[\u0d00-\u0d7f]",
    "mr-IN": r"[\u0900-\u097f]",
    "or-IN": r"[\u0b00-\u0b7f]",
    "pa-IN": r"[\u0a00-\u0a7f]",
    "ru": r"[\u0400-\u04ff]",
    "ta-IN": r"[\u0b80-\u0bff]",
    "te-IN": r"[\u0c00-\u0c7f]",
    "th": r"[\u0e00-\u0e7f]",
    "uk": r"[\u0400-\u04ff]",
    "ur-PK": r"[\u0600-\u06ff]",
    "zh-Hans": r"[\u3400-\u9fff]",
    "zh-Hant": r"[\u3400-\u9fff]",
}

PORTFOLIO_CATALOG_PATHS = {
    "en-US": "apps/index.html",
    "zh-Hant": "apps/zh-Hant/index.html",
    "zh-Hans": "apps/zh-Hans/index.html",
    "ja": "apps/ja/index.html",
    "ko": "apps/ko/index.html",
    "de-DE": "apps/de-DE/index.html",
    "fr-FR": "apps/fr-FR/index.html",
    "es-ES": "apps/es-ES/index.html",
    "es-MX": "apps/es-MX/index.html",
    "pt-BR": "apps/pt-BR/index.html",
    "ar-SA": "apps/ar-SA/index.html",
    "hi": "apps/hi/index.html",
}


def base_lang(locale):
    """locale (zh-Hans, pt-BR, en-GB) -> base language key for UI/templates."""
    if locale in ("zh-Hans", "zh-Hant"):
        return locale
    return locale.split("-")[0]


# ── 各語 UI 字串(章節標題等)。缺的語言 fallback 到 en ──────────────────
UI = {
    "en": {"what": "What is {name}?", "feat": "Key features", "price": "Pricing",
           "faq": "Frequently asked questions", "dl": "Download", "get": "Get {name} on the App Store",
           "is": "{name} is an iOS app.", "ptxt": "Free to download with a one-time purchase to unlock everything. No subscription traps.",
           "dir_dir": "Apps directory", "dir_lead": "Structured information about each iOS app — features, pricing and FAQs.",
           "catalog": "Browse all verified apps"},
    "zh-Hant": {"what": "{name} 是什麼?", "feat": "主要功能", "price": "價格",
                "faq": "常見問題", "dl": "下載", "get": "在 App Store 取得 {name}",
                "is": "{name} 是一款 iOS App。", "ptxt": "免費下載,一次性購買即可解鎖全部功能,沒有訂閱陷阱。",
                "dir_dir": "App 目錄", "dir_lead": "每個 iOS App 的結構化資訊 — 功能、價格與常見問題。",
                "catalog": "瀏覽所有已驗證 App"},
    "zh-Hans": {"what": "{name} 是什么?", "feat": "主要功能", "price": "价格",
                "faq": "常见问题", "dl": "下载", "get": "在 App Store 获取 {name}",
                "is": "{name} 是一款 iOS App。", "ptxt": "免费下载,一次性购买即可解锁全部功能,没有订阅陷阱。",
                "dir_dir": "App 目录", "dir_lead": "每个 iOS App 的结构化信息 — 功能、价格与常见问题。",
                "catalog": "浏览所有已验证 App"},
    "ja": {"what": "{name} とは?", "feat": "主な機能", "price": "価格",
           "faq": "よくある質問", "dl": "ダウンロード", "get": "App Store で {name} を入手",
           "is": "{name} は iOS アプリです。", "ptxt": "無料ダウンロード。1回限りの購入で全機能を永久に解除でき、定期課金はありません。",
           "dir_dir": "アプリ一覧", "dir_lead": "各 iOS アプリの構造化情報 — 機能・価格・FAQ。",
           "catalog": "検証済みアプリをすべて見る"},
    "ko": {"what": "{name}이란?", "feat": "주요 기능", "price": "가격",
           "faq": "자주 묻는 질문", "dl": "다운로드", "get": "App Store에서 {name} 받기",
           "is": "{name}은(는) iOS 앱입니다.", "ptxt": "무료 다운로드, 일회성 구매로 모든 기능 잠금 해제. 구독 함정 없음.",
           "dir_dir": "앱 목록", "dir_lead": "각 iOS 앱의 구조화된 정보 — 기능, 가격, FAQ.",
           "catalog": "검증된 앱 모두 보기"},
    "de": {"what": "Was ist {name}?", "feat": "Hauptfunktionen", "price": "Preis",
           "faq": "Häufige Fragen", "dl": "Download", "get": "{name} im App Store laden",
           "is": "{name} ist eine iOS-App.", "ptxt": "Kostenloser Download, mit Einmalkauf alles freischalten. Keine Abo-Falle.",
           "dir_dir": "App-Verzeichnis", "dir_lead": "Strukturierte Infos zu jeder iOS-App — Funktionen, Preis und FAQ.",
           "catalog": "Alle geprüften Apps ansehen"},
    "fr": {"what": "Qu'est-ce que {name} ?", "feat": "Fonctions clés", "price": "Tarif",
           "faq": "Questions fréquentes", "dl": "Télécharger", "get": "Obtenir {name} sur l'App Store",
           "is": "{name} est une app iOS.", "ptxt": "Téléchargement gratuit, achat unique pour tout débloquer. Sans abonnement.",
           "dir_dir": "Répertoire d'apps", "dir_lead": "Infos structurées sur chaque app iOS — fonctions, prix et FAQ.",
           "catalog": "Voir toutes les apps vérifiées"},
    "es": {"what": "¿Qué es {name}?", "feat": "Funciones clave", "price": "Precio",
           "faq": "Preguntas frecuentes", "dl": "Descargar", "get": "Consigue {name} en el App Store",
           "is": "{name} es una app de iOS.", "ptxt": "Descarga gratis, con una compra única desbloqueas todo. Sin suscripciones.",
           "dir_dir": "Directorio de apps", "dir_lead": "Información estructurada de cada app iOS — funciones, precio y FAQ.",
           "catalog": "Ver todas las apps verificadas"},
    "pt": {"what": "O que é {name}?", "feat": "Recursos principais", "price": "Preço",
           "faq": "Perguntas frequentes", "dl": "Baixar", "get": "Baixe {name} na App Store",
           "is": "{name} é um app iOS.", "ptxt": "Download grátis, compra única para desbloquear tudo. Sem assinatura.",
           "dir_dir": "Diretório de apps", "dir_lead": "Informações estruturadas de cada app iOS — recursos, preço e FAQ.",
           "catalog": "Ver todos os apps verificados"},
    "it": {"what": "Cos'è {name}?", "feat": "Funzioni principali", "price": "Prezzo",
           "faq": "Domande frequenti", "dl": "Scarica", "get": "Scarica {name} sull'App Store",
           "is": "{name} è un'app iOS.", "ptxt": "Download gratuito, con un acquisto singolo sblocchi tutto. Niente abbonamenti.",
           "dir_dir": "Elenco app", "dir_lead": "Informazioni strutturate su ogni app iOS — funzioni, prezzo e FAQ."},
    "ru": {"what": "Что такое {name}?", "feat": "Ключевые функции", "price": "Цена",
           "faq": "Частые вопросы", "dl": "Скачать", "get": "Установить {name} в App Store",
           "is": "{name} — приложение для iOS.", "ptxt": "Бесплатная загрузка, разовая покупка открывает всё. Без подписок.",
           "dir_dir": "Каталог приложений", "dir_lead": "Структурированная информация о каждом приложении iOS — функции, цена и FAQ."},
    "ar": {"what": "ما هو {name}؟", "feat": "الميزات الرئيسية", "price": "السعر",
           "faq": "الأسئلة الشائعة", "dl": "تنزيل", "get": "احصل على {name} من App Store",
           "is": "{name} تطبيق iOS.", "ptxt": "تنزيل مجاني، وعملية شراء واحدة لفتح كل المزايا. بلا اشتراكات.",
           "dir_dir": "دليل التطبيقات", "dir_lead": "معلومات منظمة عن كل تطبيق iOS — الميزات والسعر والأسئلة الشائعة.",
           "catalog": "عرض جميع التطبيقات الموثّقة"},
    "id": {"what": "Apa itu {name}?", "feat": "Fitur utama", "price": "Harga",
           "faq": "Pertanyaan umum", "dl": "Unduh", "get": "Dapatkan {name} di App Store",
           "is": "{name} adalah aplikasi iOS.", "ptxt": "Unduh gratis, beli sekali untuk membuka semua fitur. Tanpa langganan.",
           "dir_dir": "Direktori aplikasi", "dir_lead": "Informasi terstruktur tiap aplikasi iOS — fitur, harga, dan FAQ."},
    "ms": {"what": "Apakah {name}?", "feat": "Ciri utama", "price": "Harga",
           "faq": "Soalan lazim", "dl": "Muat turun", "get": "Dapatkan {name} di App Store",
           "is": "{name} ialah aplikasi iOS.", "ptxt": "Muat turun percuma, beli sekali untuk buka semua. Tiada langganan.",
           "dir_dir": "Direktori aplikasi", "dir_lead": "Maklumat berstruktur setiap aplikasi iOS — ciri, harga dan FAQ."},
    "th": {"what": "{name} คืออะไร?", "feat": "ฟีเจอร์หลัก", "price": "ราคา",
           "faq": "คำถามที่พบบ่อย", "dl": "ดาวน์โหลด", "get": "ดาวน์โหลด {name} บน App Store",
           "is": "{name} เป็นแอป iOS", "ptxt": "ดาวน์โหลดฟรี ซื้อครั้งเดียวปลดล็อกทุกฟีเจอร์ ไม่มีกับดักสมัครสมาชิก",
           "dir_dir": "ไดเรกทอรีแอป", "dir_lead": "ข้อมูลแบบโครงสร้างของแต่ละแอป iOS — ฟีเจอร์ ราคา และ FAQ"},
    "vi": {"what": "{name} là gì?", "feat": "Tính năng chính", "price": "Giá",
           "faq": "Câu hỏi thường gặp", "dl": "Tải xuống", "get": "Tải {name} trên App Store",
           "is": "{name} là ứng dụng iOS.", "ptxt": "Tải miễn phí, mua một lần để mở khóa tất cả. Không bẫy đăng ký.",
           "dir_dir": "Danh mục ứng dụng", "dir_lead": "Thông tin có cấu trúc cho từng ứng dụng iOS — tính năng, giá và FAQ."},
    "tr": {"what": "{name} nedir?", "feat": "Temel özellikler", "price": "Fiyat",
           "faq": "Sık sorulan sorular", "dl": "İndir", "get": "{name} uygulamasını App Store'dan al",
           "is": "{name} bir iOS uygulamasıdır.", "ptxt": "Ücretsiz indir, tek seferlik satın alımla her şeyi aç. Abonelik tuzağı yok.",
           "dir_dir": "Uygulama dizini", "dir_lead": "Her iOS uygulaması için yapılandırılmış bilgi — özellikler, fiyat ve SSS."},
    "nl": {"what": "Wat is {name}?", "feat": "Belangrijkste functies", "price": "Prijs",
           "faq": "Veelgestelde vragen", "dl": "Downloaden", "get": "Download {name} in de App Store",
           "is": "{name} is een iOS-app.", "ptxt": "Gratis download, met een eenmalige aankoop ontgrendel je alles. Geen abonnement.",
           "dir_dir": "App-overzicht", "dir_lead": "Gestructureerde info over elke iOS-app — functies, prijs en FAQ."},
    "pl": {"what": "Czym jest {name}?", "feat": "Główne funkcje", "price": "Cena",
           "faq": "Najczęstsze pytania", "dl": "Pobierz", "get": "Pobierz {name} z App Store",
           "is": "{name} to aplikacja na iOS.", "ptxt": "Darmowe pobranie, jednorazowy zakup odblokowuje wszystko. Bez subskrypcji.",
           "dir_dir": "Katalog aplikacji", "dir_lead": "Uporządkowane informacje o każdej aplikacji iOS — funkcje, cena i FAQ."},
    "sv": {"what": "Vad är {name}?", "feat": "Huvudfunktioner", "price": "Pris",
           "faq": "Vanliga frågor", "dl": "Ladda ner", "get": "Hämta {name} i App Store",
           "is": "{name} är en iOS-app.", "ptxt": "Gratis nedladdning, ett engångsköp låser upp allt. Inga prenumerationsfällor.",
           "dir_dir": "Appkatalog", "dir_lead": "Strukturerad info om varje iOS-app — funktioner, pris och FAQ."},
    "hi": {"what": "{name} क्या है?", "feat": "मुख्य विशेषताएँ", "price": "कीमत",
           "faq": "अक्सर पूछे जाने वाले सवाल", "dl": "डाउनलोड", "get": "App Store पर {name} पाएँ",
           "is": "{name} एक iOS ऐप है.", "ptxt": "मुफ़्त डाउनलोड, एक बार की खरीद से सब कुछ अनलॉक। कोई सब्सक्रिप्शन नहीं।",
           "dir_dir": "ऐप निर्देशिका", "dir_lead": "हर iOS ऐप की संरचित जानकारी — फ़ीचर, कीमत और FAQ।",
           "catalog": "सभी सत्यापित ऐप देखें"},
    "sk": {"what": "Čo je {name}?", "feat": "Hlavné funkcie", "price": "Cena",
           "faq": "Časté otázky", "dl": "Stiahnuť", "get": "Stiahnuť {name} v App Store",
           "is": "{name} je aplikácia pre iOS.",
           "ptxt": "Bezplatné stiahnutie; všetky funkcie odomknete jednorazovým nákupom. Bez predplatného.",
           "dir_dir": "Katalóg aplikácií",
           "dir_lead": "Prehľadné informácie o každej aplikácii pre iOS — funkcie, cena a časté otázky.",
           "catalog": "Zobraziť všetky overené aplikácie"},
    "ca": {"what": "Què és {name}?", "feat": "Funcions principals", "price": "Preu",
           "faq": "Preguntes freqüents", "dl": "Descarrega", "get": "Descarrega {name} a l’App Store",
           "is": "{name} és una app per a iOS.",
           "ptxt": "Descàrrega gratuïta. Amb una compra única desbloqueges totes les funcions per sempre, sense subscripció.",
           "dir_dir": "Directori d’apps",
           "dir_lead": "Informació estructurada sobre les funcions, el preu i les preguntes freqüents de cada app per a iOS.",
           "catalog": "Consulta totes les apps verificades"},
    "cs": {"what": "Co je {name}?", "feat": "Hlavní funkce", "price": "Cena",
           "faq": "Časté dotazy", "dl": "Stáhnout", "get": "Stáhněte si {name} v App Storu",
           "is": "{name} je aplikace pro iOS.",
           "ptxt": "Stáhněte zdarma. Jednorázovým nákupem trvale odemknete všechny funkce—bez předplatného.",
           "dir_dir": "Katalog aplikací",
           "dir_lead": "Přehledné informace o funkcích, cenách a častých dotazech ke každé aplikaci pro iOS.",
           "catalog": "Zobrazit všechny ověřené aplikace"},
    "da": {"what": "Hvad er {name}?", "feat": "Vigtigste funktioner", "price": "Pris",
           "faq": "Ofte stillede spørgsmål", "dl": "Download", "get": "Hent {name} i App Store",
           "is": "{name} er en iOS-app.",
           "ptxt": "Download gratis. Et engangskøb låser alle funktioner op permanent—uden abonnement.",
           "dir_dir": "Appoversigt",
           "dir_lead": "Strukturerede oplysninger om funktioner, priser og ofte stillede spørgsmål for hver iOS-app.",
           "catalog": "Se alle verificerede apps"},
    "el": {"what": "Τι είναι το {name};", "feat": "Βασικές λειτουργίες", "price": "Τιμή",
           "faq": "Συχνές ερωτήσεις", "dl": "Λήψη", "get": "Αποκτήστε το {name} από το App Store",
           "is": "Το {name} είναι εφαρμογή iOS.",
           "ptxt": "Κατεβάστε δωρεάν. Με μία μόνο αγορά ξεκλειδώνετε μόνιμα όλες τις λειτουργίες—χωρίς συνδρομή.",
           "dir_dir": "Κατάλογος εφαρμογών",
           "dir_lead": "Οργανωμένες πληροφορίες για τις λειτουργίες, την τιμή και τις συχνές ερωτήσεις κάθε εφαρμογής iOS.",
           "catalog": "Δείτε όλες τις επαληθευμένες εφαρμογές"},
    "fi": {"what": "Mikä {name} on?", "feat": "Tärkeimmät ominaisuudet", "price": "Hinta",
           "faq": "Usein kysytyt kysymykset", "dl": "Lataa", "get": "Lataa {name} App Storesta",
           "is": "{name} on iOS-sovellus.",
           "ptxt": "Lataa ilmaiseksi. Kertaostoksella avaat kaikki ominaisuudet pysyvästi—ei tilausta.",
           "dir_dir": "Sovellushakemisto",
           "dir_lead": "Jäsennellyt tiedot jokaisen iOS-sovelluksen ominaisuuksista, hinnasta ja usein kysytyistä kysymyksistä.",
           "catalog": "Katso kaikki vahvistetut sovellukset"},
    "he": {"what": "מהו {name}?", "feat": "תכונות עיקריות", "price": "מחיר",
           "faq": "שאלות נפוצות", "dl": "הורדה", "get": "הורידו את {name} מה-App Store",
           "is": "{name} היא אפליקציית iOS.",
           "ptxt": "הורדה בחינם. רכישה חד-פעמית פותחת את כל התכונות לצמיתות—ללא מינוי.",
           "dir_dir": "מדריך אפליקציות",
           "dir_lead": "מידע מסודר על התכונות, המחיר והשאלות הנפוצות של כל אפליקציית iOS.",
           "catalog": "הצגת כל האפליקציות המאומתות"},
    "hr": {"what": "Što je {name}?", "feat": "Glavne značajke", "price": "Cijena",
           "faq": "Česta pitanja", "dl": "Preuzimanje", "get": "Preuzmite {name} u App Storeu",
           "is": "{name} je aplikacija za iOS.",
           "ptxt": "Preuzmite besplatno. Jednokratnom kupnjom trajno otključavate sve značajke—bez pretplate.",
           "dir_dir": "Imenik aplikacija",
           "dir_lead": "Pregledne informacije o značajkama, cijeni i čestim pitanjima za svaku aplikaciju za iOS.",
           "catalog": "Pogledajte sve provjerene aplikacije"},
    "hu": {"what": "Mi az a {name}?", "feat": "Fő funkciók", "price": "Ár",
           "faq": "Gyakori kérdések", "dl": "Letöltés", "get": "Töltse le a(z) {name} appot az App Store-ból",
           "is": "A(z) {name} egy iOS-alkalmazás.",
           "ptxt": "Töltse le ingyen. Egyetlen vásárlással végleg feloldhat minden funkciót—előfizetés nélkül.",
           "dir_dir": "Alkalmazáskatalógus",
           "dir_lead": "Áttekinthető információk minden iOS-alkalmazás funkcióiról, áráról és gyakori kérdéseiről.",
           "catalog": "Az összes ellenőrzött alkalmazás megtekintése"},
    "no": {"what": "Hva er {name}?", "feat": "Viktige funksjoner", "price": "Pris",
           "faq": "Vanlige spørsmål", "dl": "Last ned", "get": "Last ned {name} fra App Store",
           "is": "{name} er en iOS-app.",
           "ptxt": "Last ned gratis. Ett engangskjøp låser opp alle funksjoner permanent—uten abonnement.",
           "dir_dir": "Appkatalog",
           "dir_lead": "Strukturert informasjon om funksjoner, priser og vanlige spørsmål for hver iOS-app.",
           "catalog": "Se alle verifiserte apper"},
    "ro": {"what": "Ce este {name}?", "feat": "Funcții principale", "price": "Preț",
           "faq": "Întrebări frecvente", "dl": "Descarcă", "get": "Descarcă {name} din App Store",
           "is": "{name} este o aplicație pentru iOS.",
           "ptxt": "Descarcă gratuit. O singură achiziție deblochează permanent toate funcțiile—fără abonament.",
           "dir_dir": "Catalog de aplicații",
           "dir_lead": "Informații structurate despre funcțiile, prețul și întrebările frecvente ale fiecărei aplicații iOS.",
           "catalog": "Vezi toate aplicațiile verificate"},
    "uk": {"what": "Що таке {name}?", "feat": "Основні функції", "price": "Ціна",
           "faq": "Поширені запитання", "dl": "Завантажити", "get": "Завантажте {name} з App Store",
           "is": "{name} — це застосунок для iOS.",
           "ptxt": "Завантажуйте безкоштовно. Одна покупка назавжди відкриває всі функції—без передплати.",
           "dir_dir": "Каталог застосунків",
           "dir_lead": "Структурована інформація про функції, ціну та поширені запитання для кожного застосунку iOS.",
           "catalog": "Переглянути всі перевірені застосунки"},
    "bn": {"what": "{name} কী?", "feat": "মূল বৈশিষ্ট্য", "price": "মূল্য",
           "faq": "সাধারণ প্রশ্ন", "dl": "ডাউনলোড", "get": "App Store থেকে {name} ডাউনলোড করুন",
           "is": "{name} একটি iOS অ্যাপ।",
           "ptxt": "বিনামূল্যে ডাউনলোড করুন। একবার কিনলেই সব ফিচার স্থায়ীভাবে আনলক হবে—কোনো সাবস্ক্রিপশন নেই।",
           "dir_dir": "অ্যাপ ডিরেক্টরি",
           "dir_lead": "প্রতিটি iOS অ্যাপের ফিচার, মূল্য ও সাধারণ প্রশ্নের সাজানো তথ্য।",
           "catalog": "সব যাচাইকৃত অ্যাপ দেখুন"},
    "gu": {"what": "{name} શું છે?", "feat": "મુખ્ય સુવિધાઓ", "price": "કિંમત",
           "faq": "વારંવાર પૂછાતા પ્રશ્નો", "dl": "ડાઉનલોડ", "get": "App Store પરથી {name} મેળવો",
           "is": "{name} એક iOS ઍપ છે.",
           "ptxt": "મફતમાં ડાઉનલોડ કરો. એક વખતની ખરીદીથી તમામ સુવિધાઓ કાયમ માટે અનલૉક કરો—કોઈ સબ્સ્ક્રિપ્શન નહીં.",
           "dir_dir": "ઍપ ડિરેક્ટરી",
           "dir_lead": "દરેક iOS ઍપની સુવિધાઓ, કિંમત અને વારંવાર પૂછાતા પ્રશ્નોની સુવ્યવસ્થિત માહિતી.",
           "catalog": "બધી ચકાસેલી ઍપ જુઓ"},
    "kn": {"what": "{name} ಎಂದರೇನು?", "feat": "ಪ್ರಮುಖ ವೈಶಿಷ್ಟ್ಯಗಳು", "price": "ಬೆಲೆ",
           "faq": "ಪದೇ ಪದೇ ಕೇಳಲಾಗುವ ಪ್ರಶ್ನೆಗಳು", "dl": "ಡೌನ್‌ಲೋಡ್", "get": "App Store ನಲ್ಲಿ {name} ಪಡೆಯಿರಿ",
           "is": "{name} ಒಂದು iOS ಆ್ಯಪ್.",
           "ptxt": "ಉಚಿತವಾಗಿ ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ. ಒಂದೇ ಬಾರಿಯ ಖರೀದಿಯಿಂದ ಎಲ್ಲ ವೈಶಿಷ್ಟ್ಯಗಳನ್ನು ಶಾಶ್ವತವಾಗಿ ಅನ್‌ಲಾಕ್ ಮಾಡಿ—ಚಂದಾದಾರಿಕೆ ಇಲ್ಲ.",
           "dir_dir": "ಆ್ಯಪ್ ಡೈರೆಕ್ಟರಿ",
           "dir_lead": "ಪ್ರತಿ iOS ಆ್ಯಪ್‌ನ ವೈಶಿಷ್ಟ್ಯಗಳು, ಬೆಲೆ ಮತ್ತು ಪದೇ ಪದೇ ಕೇಳಲಾಗುವ ಪ್ರಶ್ನೆಗಳ ಸಂರಚಿತ ಮಾಹಿತಿ.",
           "catalog": "ಪರಿಶೀಲಿಸಿದ ಎಲ್ಲ ಆ್ಯಪ್‌ಗಳನ್ನು ನೋಡಿ"},
    "ml": {"what": "{name} എന്താണ്?", "feat": "പ്രധാന സവിശേഷതകൾ", "price": "വില",
           "faq": "പതിവ് ചോദ്യങ്ങൾ", "dl": "ഡൗൺലോഡ്", "get": "App Store-ൽ നിന്ന് {name} നേടൂ",
           "is": "{name} ഒരു iOS ആപ്പാണ്.",
           "ptxt": "സൗജന്യമായി ഡൗൺലോഡ് ചെയ്യൂ. ഒറ്റത്തവണ വാങ്ങിയാൽ എല്ലാ ഫീച്ചറുകളും എന്നേക്കുമായി അൺലോക്ക് ചെയ്യാം—സബ്സ്ക്രിപ്ഷൻ ഇല്ല.",
           "dir_dir": "ആപ്പ് ഡയറക്ടറി",
           "dir_lead": "ഓരോ iOS ആപ്പിന്റെയും ഫീച്ചറുകൾ, വില, പതിവ് ചോദ്യങ്ങൾ എന്നിവയുടെ ക്രമീകരിച്ച വിവരങ്ങൾ.",
           "catalog": "പരിശോധിച്ച എല്ലാ ആപ്പുകളും കാണൂ"},
    "mr": {"what": "{name} म्हणजे काय?", "feat": "मुख्य वैशिष्ट्ये", "price": "किंमत",
           "faq": "वारंवार विचारले जाणारे प्रश्न", "dl": "डाउनलोड", "get": "App Store वरून {name} मिळवा",
           "is": "{name} हे iOS अॅप आहे.",
           "ptxt": "मोफत डाउनलोड करा. एकदाच खरेदी करून सर्व वैशिष्ट्ये कायमची अनलॉक करा—सबस्क्रिप्शन नाही.",
           "dir_dir": "अॅप निर्देशिका",
           "dir_lead": "प्रत्येक iOS अॅपची वैशिष्ट्ये, किंमत आणि वारंवार विचारले जाणारे प्रश्न यांची रचनाबद्ध माहिती.",
           "catalog": "सर्व पडताळलेली अॅप्स पाहा"},
    "or": {"what": "{name} କ’ଣ?", "feat": "ମୁଖ୍ୟ ବୈଶିଷ୍ଟ୍ୟ", "price": "ମୂଲ୍ୟ",
           "faq": "ବାରମ୍ବାର ପଚରାଯାଉଥିବା ପ୍ରଶ୍ନ", "dl": "ଡାଉନଲୋଡ୍", "get": "App Store ରୁ {name} ପାଆନ୍ତୁ",
           "is": "{name} ଏକ iOS ଆପ୍।",
           "ptxt": "ମାଗଣାରେ ଡାଉନଲୋଡ୍ କରନ୍ତୁ। ଥରେ କିଣି ସମସ୍ତ ବୈଶିଷ୍ଟ୍ୟକୁ ସବୁଦିନ ପାଇଁ ଅନଲକ୍ କରନ୍ତୁ—କୌଣସି ସବସ୍କ୍ରିପସନ୍ ନାହିଁ।",
           "dir_dir": "ଆପ୍ ଡିରେକ୍ଟୋରି",
           "dir_lead": "ପ୍ରତ୍ୟେକ iOS ଆପ୍‌ର ବୈଶିଷ୍ଟ୍ୟ, ମୂଲ୍ୟ ଓ ବାରମ୍ବାର ପଚରାଯାଉଥିବା ପ୍ରଶ୍ନର ସୁସଂଗଠିତ ସୂଚନା।",
           "catalog": "ସମସ୍ତ ଯାଞ୍ଚ ହୋଇଥିବା ଆପ୍ ଦେଖନ୍ତୁ"},
    "pa": {"what": "{name} ਕੀ ਹੈ?", "feat": "ਮੁੱਖ ਵਿਸ਼ੇਸ਼ਤਾਵਾਂ", "price": "ਕੀਮਤ",
           "faq": "ਅਕਸਰ ਪੁੱਛੇ ਜਾਣ ਵਾਲੇ ਸਵਾਲ", "dl": "ਡਾਊਨਲੋਡ", "get": "App Store ਤੋਂ {name} ਪ੍ਰਾਪਤ ਕਰੋ",
           "is": "{name} ਇੱਕ iOS ਐਪ ਹੈ।",
           "ptxt": "ਮੁਫ਼ਤ ਡਾਊਨਲੋਡ ਕਰੋ। ਇੱਕ ਵਾਰ ਖਰੀਦ ਕੇ ਸਾਰੀਆਂ ਵਿਸ਼ੇਸ਼ਤਾਵਾਂ ਹਮੇਸ਼ਾਂ ਲਈ ਅਨਲੌਕ ਕਰੋ—ਕੋਈ ਸਬਸਕ੍ਰਿਪਸ਼ਨ ਨਹੀਂ।",
           "dir_dir": "ਐਪ ਡਾਇਰੈਕਟਰੀ",
           "dir_lead": "ਹਰੇਕ iOS ਐਪ ਦੀਆਂ ਵਿਸ਼ੇਸ਼ਤਾਵਾਂ, ਕੀਮਤ ਅਤੇ ਆਮ ਸਵਾਲਾਂ ਬਾਰੇ ਵਿਵਸਥਿਤ ਜਾਣਕਾਰੀ।",
           "catalog": "ਸਾਰੀਆਂ ਤਸਦੀਕਸ਼ੁਦਾ ਐਪਾਂ ਵੇਖੋ"},
    "sl": {"what": "Kaj je {name}?", "feat": "Glavne funkcije", "price": "Cena",
           "faq": "Pogosta vprašanja", "dl": "Prenos", "get": "Prenesite {name} iz trgovine App Store",
           "is": "{name} je aplikacija za iOS.",
           "ptxt": "Prenesite brezplačno. Z enkratnim nakupom trajno odklenete vse funkcije—brez naročnine.",
           "dir_dir": "Imenik aplikacij",
           "dir_lead": "Pregledne informacije o funkcijah, cenah in pogostih vprašanjih za vsako aplikacijo iOS.",
           "catalog": "Oglejte si vse preverjene aplikacije"},
    "ta": {"what": "{name} என்றால் என்ன?", "feat": "முக்கிய அம்சங்கள்", "price": "விலை",
           "faq": "அடிக்கடி கேட்கப்படும் கேள்விகள்", "dl": "பதிவிறக்கம்", "get": "App Store-இல் {name}-ஐப் பெறுங்கள்",
           "is": "{name} ஒரு iOS செயலி.",
           "ptxt": "இலவசமாகப் பதிவிறக்குங்கள். ஒருமுறை வாங்கி அனைத்து அம்சங்களையும் நிரந்தரமாகத் திறக்கலாம்—சந்தா இல்லை.",
           "dir_dir": "செயலி அடைவு",
           "dir_lead": "ஒவ்வொரு iOS செயலியின் அம்சங்கள், விலை மற்றும் அடிக்கடி கேட்கப்படும் கேள்விகள் பற்றிய ஒழுங்கமைக்கப்பட்ட தகவல்.",
           "catalog": "சரிபார்க்கப்பட்ட அனைத்து செயலிகளையும் பார்க்கவும்"},
    "te": {"what": "{name} అంటే ఏమిటి?", "feat": "ముఖ్య ఫీచర్లు", "price": "ధర",
           "faq": "తరచుగా అడిగే ప్రశ్నలు", "dl": "డౌన్‌లోడ్", "get": "App Store నుంచి {name} పొందండి",
           "is": "{name} ఒక iOS యాప్.",
           "ptxt": "ఉచితంగా డౌన్‌లోడ్ చేసుకోండి. ఒకసారి కొనుగోలుతో అన్ని ఫీచర్లను శాశ్వతంగా అన్‌లాక్ చేసుకోండి—సబ్‌స్క్రిప్షన్ లేదు.",
           "dir_dir": "యాప్ డైరెక్టరీ",
           "dir_lead": "ప్రతి iOS యాప్ ఫీచర్లు, ధరలు మరియు తరచుగా అడిగే ప్రశ్నలపై క్రమబద్ధమైన సమాచారం.",
           "catalog": "ధృవీకరించిన అన్ని యాప్‌లను చూడండి"},
    "ur": {"what": "{name} کیا ہے؟", "feat": "اہم خصوصیات", "price": "قیمت",
           "faq": "اکثر پوچھے جانے والے سوالات", "dl": "ڈاؤن لوڈ", "get": "App Store سے {name} حاصل کریں",
           "is": "{name} ایک iOS ایپ ہے۔",
           "ptxt": "مفت ڈاؤن لوڈ کریں۔ ایک بار خرید کر تمام خصوصیات ہمیشہ کے لیے اَن لاک کریں—کوئی سبسکرپشن نہیں۔",
           "dir_dir": "ایپس کی فہرست",
           "dir_lead": "ہر iOS ایپ کی خصوصیات، قیمت اور اکثر پوچھے جانے والے سوالات کی منظم معلومات۔",
           "catalog": "تمام تصدیق شدہ ایپس دیکھیں"},
}

# Storefront variants use their own wording rather than a base-language fallback.
FINDER_UI = {
    "ar-SA": {
        "find": "ماذا تريد أن تنجز؟",
        "no_match": "لا نتائج. جرّب كلمات أخرى.",
    },
    "bn-BD": {
        "find": "কী খুঁজছেন?",
        "no_match": "কোনো ফল নেই। অন্য শব্দে খুঁজুন।",
    },
    "ca": {
        "find": "Què necessites?",
        "no_match": "Sense resultats. Prova amb altres paraules.",
    },
    "cs": {
        "find": "Co hledáte?",
        "no_match": "Žádné výsledky. Zkuste jiná klíčová slova.",
    },
    "da": {
        "find": "Hvad leder du efter?",
        "no_match": "Ingen resultater. Prøv andre søgeord.",
    },
    "de-DE": {
        "find": "Was suchen Sie?",
        "no_match": "Keine Ergebnisse. Bitte andere Begriffe versuchen.",
    },
    "el": {
        "find": "Τι αναζητάτε;",
        "no_match": "Δεν βρέθηκαν αποτελέσματα. Δοκιμάστε άλλες λέξεις.",
    },
    "en-AU": {
        "find": "What do you need to get done?",
        "no_match": "No matches. Try different words.",
    },
    "en-CA": {
        "find": "What do you need to do?",
        "no_match": "No matches. Try different words.",
    },
    "en-GB": {
        "find": "What would you like to do?",
        "no_match": "No matches. Try different words.",
    },
    "en-US": {
        "find": "What do you need to get done?",
        "no_match": "No matches. Try different words.",
    },
    "es-ES": {
        "find": "¿Qué necesitas?",
        "no_match": "Sin resultados. Prueba con otras palabras.",
    },
    "es-MX": {
        "find": "¿Qué buscas?",
        "no_match": "Sin resultados. Intenta con otras palabras.",
    },
    "fi": {
        "find": "Mitä haet?",
        "no_match": "Ei tuloksia. Kokeile muita hakusanoja.",
    },
    "fr-CA": {
        "find": "Qu'est-ce que tu cherches ?",
        "no_match": "Aucun résultat. Essaie d'autres mots-clés.",
    },
    "fr-FR": {
        "find": "Que recherchez-vous ?",
        "no_match": "Aucun résultat. Essayez d'autres termes.",
    },
    "gu-IN": {
        "find": "શું શોધી રહ્યા છો?",
        "no_match": "કોઈ પરિણામ નથી. બીજા શબ્દો અજમાવો.",
    },
    "he": {
        "find": "מה מחפשים?",
        "no_match": "לא נמצאו תוצאות. נסו מילים אחרות.",
    },
    "hi": {
        "find": "आप क्या खोज रहे हैं?",
        "no_match": "कोई परिणाम नहीं। दूसरे शब्द आज़माएँ।",
    },
    "hr": {
        "find": "Što tražite?",
        "no_match": "Nema rezultata. Pokušajte s drugim ključnim riječima.",
    },
    "hu": {
        "find": "Mit keres?",
        "no_match": "Nincs találat. Próbáljon más kulcsszavakat.",
    },
    "id": {
        "find": "Apa yang Anda cari?",
        "no_match": "Tidak ada hasil. Coba kata lain.",
    },
    "it": {
        "find": "Cosa cerca?",
        "no_match": "Nessun risultato. Provi con altre parole chiave.",
    },
    "ja": {
        "find": "何をお探しですか？",
        "no_match": "見つかりません。別の言葉で検索してください。",
    },
    "kn-IN": {
        "find": "ನೀವು ಏನನ್ನು ಹುಡುಕುತ್ತಿದ್ದೀರಿ?",
        "no_match": "ಫಲಿತಾಂಶಗಳಿಲ್ಲ. ಬೇರೆ ಪದ ಬಳಸಿ.",
    },
    "ko": {
        "find": "무엇을 찾고 계신가요?",
        "no_match": "검색 결과가 없어요. 다른 단어로 찾아보세요.",
    },
    "ml-IN": {
        "find": "എന്താണ് തിരയുന്നത്?",
        "no_match": "ഫലങ്ങളില്ല. മറ്റൊരു വാക്ക് പരീക്ഷിക്കൂ.",
    },
    "mr-IN": {
        "find": "तुम्ही काय शोधत आहात?",
        "no_match": "निकाल नाहीत. दुसरे शब्द वापरून पाहा.",
    },
    "ms": {
        "find": "Apa yang anda cari?",
        "no_match": "Tiada hasil. Cuba kata kunci lain.",
    },
    "nl-NL": {
        "find": "Wat zoekt u?",
        "no_match": "Geen resultaten. Probeer andere zoektermen.",
    },
    "no": {
        "find": "Hva leter du etter?",
        "no_match": "Ingen resultater. Prøv andre søkeord.",
    },
    "or-IN": {
        "find": "ଆପଣ କ’ଣ ଖୋଜୁଛନ୍ତି?",
        "no_match": "କୌଣସି ଫଳ ନାହିଁ। ଅନ୍ୟ ଶବ୍ଦ ଚେଷ୍ଟା କରନ୍ତୁ।",
    },
    "pa-IN": {
        "find": "ਤੁਸੀਂ ਕੀ ਲੱਭ ਰਹੇ ਹੋ?",
        "no_match": "ਕੋਈ ਨਤੀਜਾ ਨਹੀਂ। ਹੋਰ ਸ਼ਬਦ ਅਜ਼ਮਾਓ।",
    },
    "pl": {
        "find": "Czego szukasz?",
        "no_match": "Brak wyników. Spróbuj innych słów kluczowych.",
    },
    "pt-BR": {
        "find": "O que você busca?",
        "no_match": "Nenhum resultado encontrado. Tente outras palavras.",
    },
    "pt-PT": {
        "find": "O que procura?",
        "no_match": "Sem resultados. Experimente outras palavras.",
    },
    "ro": {
        "find": "Ce căutați?",
        "no_match": "Niciun rezultat. Încercați alte cuvinte.",
    },
    "ru": {
        "find": "Что вас интересует?",
        "no_match": "Ничего не найдено. Попробуйте другие слова.",
    },
    "sk": {
        "find": "Čo hľadáte?",
        "no_match": "Žiadne výsledky. Skúste iné kľúčové slová.",
    },
    "sl-SI": {
        "find": "Kaj iščete?",
        "no_match": "Ni rezultatov. Poskusite z drugimi besedami.",
    },
    "sv": {
        "find": "Vad letar du efter?",
        "no_match": "Inga resultat. Prova andra sökord.",
    },
    "ta-IN": {
        "find": "எதைத் தேடுகிறீர்கள்?",
        "no_match": "முடிவுகள் இல்லை. வேறு சொல் முயலுங்கள்.",
    },
    "te-IN": {
        "find": "మీరు ఏమి వెతుకుతున్నారు?",
        "no_match": "ఫలితాలు లేవు. మరో పదాన్ని ప్రయత్నించండి.",
    },
    "th": {
        "find": "กำลังมองหาอะไร?",
        "no_match": "ไม่พบผลลัพธ์ ลองใช้คำอื่น",
    },
    "tr": {
        "find": "Ne arıyorsunuz?",
        "no_match": "Sonuç bulunamadı. Farklı arama terimleri deneyin.",
    },
    "uk": {
        "find": "Що ви шукаєте?",
        "no_match": "Нічого не знайдено. Спробуйте інші слова.",
    },
    "ur-PK": {
        "find": "آپ کیا تلاش کر رہے ہیں؟",
        "no_match": "کوئی نتیجہ نہیں۔ دوسرے الفاظ آزمائیں۔",
    },
    "vi": {
        "find": "Bạn đang tìm gì?",
        "no_match": "Không có kết quả. Hãy thử từ khác.",
    },
    "zh-Hans": {
        "find": "想完成什么？",
        "no_match": "没有符合的结果，换个关键词试试。",
    },
    "zh-Hant": {
        "find": "想完成什麼？",
        "no_match": "找不到符合的結果，換個關鍵字試試。",
    },
}
require_official_locale_coverage("localized-app-finder-copy", FINDER_UI)


PROFILE_PRICING = {
    "en": {
        "free_to_start": "Free to start with no recurring subscription; check the App Store for currently available content.",
        "free": "Free to use with no ads; check the App Store listing for current availability.",
        "flexible": "Free to download with in-app purchases: choose a one-time unlock or an optional subscription.",
        "neutral": "Pricing and unlock options may vary by App Store region; see the current listing for details.",
    },
    "zh-Hant": {
        "free_to_start": "可免費開始使用，無需定期訂閱；請至 App Store 確認目前可用內容。",
        "flexible": "免費下載，提供 App 內購買：可選一次性解鎖，也有可選訂閱方案。",
        "neutral": "定價與解鎖選項可能因 App Store 地區而異；請查看目前上架資訊。",
    },
    "zh-Hans": {
        "free_to_start": "可免费开始使用，无需定期订阅；请在 App Store 查看当前可用内容。",
        "flexible": "免费下载，提供应用内购买：可选一次性解锁，也有可选订阅方案。",
        "neutral": "定价与解锁选项可能因 App Store 地区而异；请查看当前上架信息。",
    },
    "ja": {
        "free_to_start": "無料で始められ、定期課金はありません。現在利用できる内容は App Store でご確認ください。",
        "flexible": "無料でダウンロードでき、アプリ内購入として一度限りの解除と任意のサブスクリプションを選べます。",
        "neutral": "価格と解除オプションは App Store の地域によって異なる場合があります。現在の掲載情報をご確認ください。",
    },
    "ko": {
        "free_to_start": "정기 구독 없이 무료로 시작할 수 있습니다. 현재 이용 가능한 콘텐츠는 App Store에서 확인하세요.",
        "flexible": "무료 다운로드이며 앱 내 구매로 일회성 잠금 해제 또는 선택적 구독을 선택할 수 있습니다.",
        "neutral": "가격 및 잠금 해제 옵션은 App Store 지역에 따라 다를 수 있습니다. 현재 등록 정보를 확인해 주세요.",
    },
    "de": {
        "free_to_start": "Kostenlos starten, ohne wiederkehrendes Abo; aktuelle Inhalte im App Store prüfen.",
        "flexible": "Kostenlos laden mit In-App-Käufen: einmalige Freischaltung oder optionales Abonnement wählbar.",
        "neutral": "Preise und Freischaltoptionen können je nach App Store-Region variieren; aktuelle Informationen im Listing einsehen.",
    },
    "fr": {
        "free_to_start": "Commencez gratuitement sans abonnement récurrent ; vérifiez les contenus disponibles sur l'App Store.",
        "flexible": "Téléchargement gratuit avec achats intégrés : choisissez un déverrouillage unique ou un abonnement optionnel.",
        "neutral": "Les prix et options de déverrouillage peuvent varier selon la région de l'App Store ; consultez la fiche actuelle.",
    },
    "es": {
        "free_to_start": "Comienza gratis sin suscripción recurrente; consulta el contenido disponible en el App Store.",
        "flexible": "Descarga gratuita con compras integradas: elige un desbloqueo único o una suscripción opcional.",
        "neutral": "Los precios y opciones de desbloqueo pueden variar según la región del App Store; consulta la ficha actual.",
    },
    "pt": {
        "free_to_start": "Comece gratuitamente sem assinatura recorrente; confira o conteúdo disponível no App Store.",
        "flexible": "Download gratuito com compras no app: escolha desbloqueio único ou assinatura opcional.",
        "neutral": "Os preços e opções de desbloqueio podem variar por região do App Store; consulte a listagem atual.",
    },
    "it": {
        "free_to_start": "Inizia gratuitamente senza abbonamento ricorrente; verifica i contenuti disponibili sull'App Store.",
        "flexible": "Download gratuito con acquisti in-app: scegli tra sblocco una tantum o abbonamento opzionale.",
        "neutral": "Prezzi e opzioni di sblocco possono variare in base alla regione dell'App Store; consulta la scheda attuale.",
    },
    "ru": {
        "free_to_start": "Начните бесплатно без повторяющейся подписки; актуальный контент проверьте в App Store.",
        "flexible": "Бесплатная загрузка с покупками внутри приложения: выберите разовую разблокировку или необязательную подписку.",
        "neutral": "Цены и варианты разблокировки могут различаться в зависимости от региона App Store; смотрите актуальный листинг.",
    },
    "ar": {
        "free_to_start": "ابدأ مجانًا دون اشتراك دوري؛ تحقق من المحتوى المتاح حاليًا على App Store.",
        "flexible": "تنزيل مجاني مع مشتريات داخل التطبيق: اختر فتح الميزات مرة واحدة أو اشتراكًا اختياريًا.",
        "neutral": "قد تختلف الأسعار وخيارات الفتح حسب منطقة App Store؛ راجع القائمة الحالية للتفاصيل.",
    },
    "id": {
        "free_to_start": "Mulai gratis tanpa langganan berulang; periksa konten yang tersedia saat ini di App Store.",
        "flexible": "Unduh gratis dengan pembelian dalam aplikasi: pilih buka kunci sekali atau langganan opsional.",
        "neutral": "Harga dan opsi buka kunci dapat bervariasi menurut wilayah App Store; lihat listing saat ini.",
    },
    "ms": {
        "free_to_start": "Mulakan secara percuma tanpa langganan berulang; semak kandungan semasa di App Store.",
        "flexible": "Muat turun percuma dengan pembelian dalam apl: pilih buka kunci sekali atau langganan pilihan.",
        "neutral": "Harga dan pilihan buka kunci mungkin berbeza mengikut rantau App Store; lihat penyenaraian semasa.",
    },
    "th": {
        "free_to_start": "เริ่มใช้งานฟรีโดยไม่มีการสมัครสมาชิกแบบต่ออายุ ตรวจสอบเนื้อหาปัจจุบันได้ที่ App Store",
        "flexible": "ดาวน์โหลดฟรีพร้อมการซื้อภายในแอป โดยเลือกปลดล็อกครั้งเดียวหรือสมัครสมาชิกแบบไม่บังคับได้",
        "neutral": "ราคาและตัวเลือกการปลดล็อกอาจแตกต่างกันตามภูมิภาค App Store โปรดดูข้อมูลรายการปัจจุบัน",
    },
    "vi": {
        "free_to_start": "Bắt đầu miễn phí mà không cần đăng ký định kỳ; kiểm tra nội dung hiện có trên App Store.",
        "flexible": "Tải xuống miễn phí với giao dịch mua trong ứng dụng: chọn mở khóa một lần hoặc đăng ký tùy chọn.",
        "neutral": "Giá và tùy chọn mở khóa có thể khác nhau tùy theo khu vực App Store; xem thông tin hiện tại.",
    },
    "tr": {
        "free_to_start": "Yinelenen abonelik olmadan ücretsiz başlayın; mevcut içerikler için App Store'a bakın.",
        "flexible": "Uygulama içi satın almalarla ücretsiz indirin: tek seferlik kilit açma veya isteğe bağlı abonelik seçin.",
        "neutral": "Fiyatlar ve kilit açma seçenekleri App Store bölgesine göre değişebilir; güncel listeyi kontrol edin.",
    },
    "nl": {
        "free_to_start": "Begin gratis zonder terugkerend abonnement; controleer de beschikbare inhoud in de App Store.",
        "flexible": "Gratis downloaden met in-app aankopen: kies eenmalige ontgrendeling of een optioneel abonnement.",
        "neutral": "Prijzen en ontgrendelingsopties kunnen per App Store-regio verschillen; raadpleeg de huidige listing.",
    },
    "pl": {
        "free_to_start": "Zacznij bezpłatnie bez cyklicznej subskrypcji; sprawdź dostępne treści w App Store.",
        "flexible": "Bezpłatne pobieranie z zakupami w aplikacji: wybierz jednorazowe odblokowanie lub opcjonalną subskrypcję.",
        "neutral": "Ceny i opcje odblokowania mogą się różnić zależnie od regionu App Store; sprawdź aktualny listing.",
    },
    "sv": {
        "free_to_start": "Börja gratis utan återkommande prenumeration; kontrollera tillgängligt innehåll i App Store.",
        "flexible": "Gratis nedladdning med köp i appen: välj engångsupplåsning eller en valfri prenumeration.",
        "neutral": "Priser och upplåsningsalternativ kan variera beroende på App Store-region; se aktuell listning.",
    },
    "hi": {
        "free_to_start": "बिना आवर्ती सदस्यता के मुफ़्त में शुरू करें; वर्तमान सामग्री के लिए App Store देखें।",
        "flexible": "इन-ऐप खरीदारी के साथ मुफ़्त डाउनलोड करें: एकमुश्त अनलॉक या वैकल्पिक सदस्यता चुनें।",
        "neutral": "मूल्य और अनलॉक विकल्प App Store क्षेत्र के अनुसार भिन्न हो सकते हैं; वर्तमान लिस्टिंग देखें।",
    },
    "ca": {
        "free_to_start": "Comença gratis sense cap subscripció recurrent; consulta el contingut disponible a l’App Store.",
        "free": "Ús gratuït i sense anuncis; consulta la disponibilitat actual a l’App Store.",
        "flexible": "Descàrrega gratuïta amb compres dins de l’app: tria un desbloqueig únic o una subscripció opcional.",
        "neutral": "Els preus i les opcions de desbloqueig poden variar segons la regió de l’App Store; consulta la fitxa actual.",
    },
    "hr": {
        "free_to_start": "Započnite besplatno bez ponavljajuće pretplate; trenutačno dostupan sadržaj provjerite u App Storeu.",
        "free": "Koristite besplatno i bez oglasa; trenutačnu dostupnost provjerite u App Storeu.",
        "flexible": "Besplatno preuzimanje uz kupnje unutar aplikacije: odaberite jednokratno otključavanje ili opcionalnu pretplatu.",
        "neutral": "Cijene i mogućnosti otključavanja mogu se razlikovati ovisno o regiji App Storea; provjerite trenutačnu ponudu.",
    },
    "da": {
        "free_to_start": "Start gratis uden et tilbagevendende abonnement; se det aktuelle indhold i App Store.",
        "free": "Brug gratis og uden reklamer; se den aktuelle tilgængelighed i App Store.",
        "flexible": "Gratis download med køb i appen: vælg en engangsoplåsning eller et valgfrit abonnement.",
        "neutral": "Priser og oplåsningsmuligheder kan variere efter App Store-område; se den aktuelle produktside.",
    },
    "no": {
        "free_to_start": "Start gratis uten et løpende abonnement; se tilgjengelig innhold i App Store.",
        "free": "Bruk gratis og uten annonser; se gjeldende tilgjengelighet i App Store.",
        "flexible": "Gratis nedlasting med kjøp i appen: velg engangsopplåsing eller et valgfritt abonnement.",
        "neutral": "Priser og opplåsingsalternativer kan variere etter App Store-region; se den gjeldende oppføringen.",
    },
    "ro": {
        "free_to_start": "Începe gratuit, fără abonament recurent; verifică în App Store conținutul disponibil în prezent.",
        "free": "Folosește gratuit și fără reclame; verifică disponibilitatea actuală în App Store.",
        "flexible": "Descărcare gratuită cu achiziții în aplicație: alege o deblocare unică sau un abonament opțional.",
        "neutral": "Prețurile și opțiunile de deblocare pot varia în funcție de regiunea App Store; consultă pagina actuală.",
    },
    "sk": {
        "free_to_start": "Začnite bezplatne bez opakovaného predplatného; aktuálne dostupný obsah nájdete v App Store.",
        "free": "Používajte bezplatne a bez reklám; aktuálnu dostupnosť overte v App Store.",
        "flexible": "Bezplatné stiahnutie s nákupmi v aplikácii: vyberte si jednorazové odomknutie alebo voliteľné predplatné.",
        "neutral": "Ceny a možnosti odomknutia sa môžu líšiť podľa regiónu App Store; pozrite si aktuálnu ponuku.",
    },
    "cs": {
        "free_to_start": "Začněte zdarma bez opakovaného předplatného; aktuálně dostupný obsah najdete v App Storu.",
        "free": "Používejte zdarma a bez reklam; aktuální dostupnost ověřte v App Storu.",
        "flexible": "Stáhněte zdarma s nákupy v aplikaci: vyberte jednorázové odemknutí nebo volitelné předplatné.",
        "neutral": "Ceny a možnosti odemknutí se mohou lišit podle oblasti App Storu; podrobnosti najdete v aktuální nabídce.",
    },
    "el": {
        "free_to_start": "Ξεκινήστε δωρεάν χωρίς επαναλαμβανόμενη συνδρομή· δείτε το διαθέσιμο περιεχόμενο στο App Store.",
        "free": "Χρησιμοποιήστε δωρεάν και χωρίς διαφημίσεις· ελέγξτε την τρέχουσα διαθεσιμότητα στο App Store.",
        "flexible": "Δωρεάν λήψη με αγορές εντός εφαρμογής: επιλέξτε εφάπαξ ξεκλείδωμα ή προαιρετική συνδρομή.",
        "neutral": "Οι τιμές και οι επιλογές ξεκλειδώματος ενδέχεται να διαφέρουν ανά περιοχή App Store· δείτε την τρέχουσα καταχώριση.",
    },
    "fi": {
        "free_to_start": "Aloita ilmaiseksi ilman jatkuvaa tilausta; tarkista saatavilla oleva sisältö App Storesta.",
        "free": "Käytä ilmaiseksi ja ilman mainoksia; tarkista tämänhetkinen saatavuus App Storesta.",
        "flexible": "Lataa ilmaiseksi sovelluksen sisäisillä ostoilla: valitse kerta-avaus tai valinnainen tilaus.",
        "neutral": "Hinnat ja avausvaihtoehdot voivat vaihdella App Store -alueen mukaan; katso ajantasainen tuotesivu.",
    },
    "he": {
        "free_to_start": "התחילו בחינם וללא מינוי מתחדש; בדקו ב-App Store איזה תוכן זמין כעת.",
        "free": "שימוש בחינם וללא פרסומות; בדקו את הזמינות הנוכחית ב-App Store.",
        "flexible": "הורדה בחינם עם רכישות בתוך האפליקציה: בחרו פתיחה חד-פעמית או מינוי אופציונלי.",
        "neutral": "המחירים ואפשרויות הפתיחה עשויים להשתנות לפי אזור ה-App Store; עיינו ברישום הנוכחי.",
    },
    "hu": {
        "free_to_start": "Kezdje ingyen, ismétlődő előfizetés nélkül; az aktuális tartalmat az App Store-ban ellenőrizheti.",
        "free": "Használja ingyen és hirdetések nélkül; az aktuális elérhetőséget az App Store-ban ellenőrizheti.",
        "flexible": "Ingyenes letöltés alkalmazáson belüli vásárlásokkal: válasszon egyszeri feloldást vagy opcionális előfizetést.",
        "neutral": "Az árak és a feloldási lehetőségek App Store-régiónként eltérhetnek; tekintse meg az aktuális adatlapot.",
    },
    "uk": {
        "free_to_start": "Почніть безкоштовно без регулярної передплати; актуальний доступний вміст перевірте в App Store.",
        "free": "Користуйтеся безкоштовно й без реклами; актуальну доступність перевірте в App Store.",
        "flexible": "Безкоштовне завантаження з покупками в застосунку: виберіть одноразове розблокування або необов’язкову передплату.",
        "neutral": "Ціни й варіанти розблокування можуть відрізнятися залежно від регіону App Store; перегляньте актуальну сторінку.",
    },
    "bn": {
        "free_to_start": "পুনরাবৃত্ত সাবস্ক্রিপশন ছাড়াই বিনামূল্যে শুরু করুন; বর্তমানে কী কী কনটেন্ট পাওয়া যাচ্ছে তা App Store-এ দেখুন।",
        "free": "বিজ্ঞাপন ছাড়াই বিনামূল্যে ব্যবহার করুন; বর্তমান উপলভ্যতা জানতে App Store তালিকা দেখুন।",
        "flexible": "অ্যাপ-মধ্যস্থ কেনাকাটাসহ বিনামূল্যে ডাউনলোড করুন: একবারের আনলক বা ঐচ্ছিক সাবস্ক্রিপশন বেছে নিন।",
        "neutral": "App Store অঞ্চলের ভিত্তিতে মূল্য ও আনলক বিকল্প বদলাতে পারে; বিস্তারিত জানতে বর্তমান তালিকা দেখুন।",
    },
    "gu": {
        "free_to_start": "આવર્તક સબ્સ્ક્રિપ્શન વિના મફતમાં શરૂ કરો; હાલ ઉપલબ્ધ સામગ્રી માટે App Store જુઓ.",
        "free": "જાહેરાત વિના મફતમાં વાપરો; હાલની ઉપલબ્ધતા માટે App Store લિસ્ટિંગ જુઓ.",
        "flexible": "ઍપમાં ખરીદી સાથે મફતમાં ડાઉનલોડ કરો: એક વખતનું અનલૉક અથવા વૈકલ્પિક સબ્સ્ક્રિપ્શન પસંદ કરો.",
        "neutral": "App Store પ્રદેશ પ્રમાણે કિંમત અને અનલૉક વિકલ્પો બદલાઈ શકે છે; હાલનું લિસ્ટિંગ જુઓ.",
    },
    "kn": {
        "free_to_start": "ಮರುಕಳಿಸುವ ಚಂದಾದಾರಿಕೆ ಇಲ್ಲದೆ ಉಚಿತವಾಗಿ ಪ್ರಾರಂಭಿಸಿ; ಈಗ ಲಭ್ಯವಿರುವ ವಿಷಯಕ್ಕಾಗಿ App Store ನೋಡಿ.",
        "free": "ಜಾಹೀರಾತುಗಳಿಲ್ಲದೆ ಉಚಿತವಾಗಿ ಬಳಸಿ; ಪ್ರಸ್ತುತ ಲಭ್ಯತೆಗಾಗಿ App Store ಪಟ್ಟಿಯನ್ನು ನೋಡಿ.",
        "flexible": "ಆ್ಯಪ್‌ನಲ್ಲಿನ ಖರೀದಿಗಳೊಂದಿಗೆ ಉಚಿತವಾಗಿ ಡೌನ್‌ಲೋಡ್ ಮಾಡಿ: ಒಂದು ಬಾರಿಯ ಅನ್‌ಲಾಕ್ ಅಥವಾ ಐಚ್ಛಿಕ ಚಂದಾದಾರಿಕೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ.",
        "neutral": "App Store ಪ್ರದೇಶಕ್ಕೆ ಅನುಗುಣವಾಗಿ ಬೆಲೆ ಮತ್ತು ಅನ್‌ಲಾಕ್ ಆಯ್ಕೆಗಳು ಬದಲಾಗಬಹುದು; ಪ್ರಸ್ತುತ ಪಟ್ಟಿಯನ್ನು ನೋಡಿ.",
    },
    "ml": {
        "free_to_start": "ആവർത്തിച്ചുള്ള സബ്സ്ക്രിപ്ഷനില്ലാതെ സൗജന്യമായി തുടങ്ങൂ; നിലവിൽ ലഭ്യമായ ഉള്ളടക്കത്തിന് App Store പരിശോധിക്കൂ.",
        "free": "പരസ്യങ്ങളില്ലാതെ സൗജന്യമായി ഉപയോഗിക്കൂ; നിലവിലെ ലഭ്യതയ്ക്ക് App Store ലിസ്റ്റിംഗ് കാണൂ.",
        "flexible": "ഇൻ-ആപ്പ് പർച്ചേസുകളോടെ സൗജന്യമായി ഡൗൺലോഡ് ചെയ്യൂ: ഒറ്റത്തവണ അൺലോക്കോ ഐച്ഛിക സബ്സ്ക്രിപ്ഷനോ തിരഞ്ഞെടുക്കൂ.",
        "neutral": "App Store പ്രദേശമനുസരിച്ച് വിലയും അൺലോക്ക് ഓപ്ഷനുകളും മാറാം; നിലവിലെ ലിസ്റ്റിംഗ് കാണൂ.",
    },
    "mr": {
        "free_to_start": "आवर्ती सबस्क्रिप्शनशिवाय मोफत सुरुवात करा; सध्या उपलब्ध मजकुरासाठी App Store पाहा.",
        "free": "जाहिरातींशिवाय मोफत वापरा; सध्याच्या उपलब्धतेसाठी App Store सूची पाहा.",
        "flexible": "अॅपमधील खरेदीसह मोफत डाउनलोड करा: एकदाचे अनलॉक किंवा पर्यायी सबस्क्रिप्शन निवडा.",
        "neutral": "App Store प्रदेशानुसार किंमत आणि अनलॉक पर्याय बदलू शकतात; सध्याची सूची पाहा.",
    },
    "or": {
        "free_to_start": "ବାରମ୍ବାର ସବସ୍କ୍ରିପସନ୍ ବିନା ମାଗଣାରେ ଆରମ୍ଭ କରନ୍ତୁ; ବର୍ତ୍ତମାନର ଉପଲବ୍ଧ ବିଷୟବସ୍ତୁ ପାଇଁ App Store ଦେଖନ୍ତୁ।",
        "free": "ବିଜ୍ଞାପନ ବିନା ମାଗଣାରେ ବ୍ୟବହାର କରନ୍ତୁ; ବର୍ତ୍ତମାନର ଉପଲବ୍ଧତା ପାଇଁ App Store ତାଲିକା ଦେଖନ୍ତୁ।",
        "flexible": "ଆପ୍ ଭିତରେ କ୍ରୟ ସହ ମାଗଣାରେ ଡାଉନଲୋଡ୍ କରନ୍ତୁ: ଥରେ ଅନଲକ୍ କିମ୍ବା ଇଚ୍ଛାଧୀନ ସବସ୍କ୍ରିପସନ୍ ବାଛନ୍ତୁ।",
        "neutral": "App Store ଅଞ୍ଚଳ ଅନୁଯାୟୀ ମୂଲ୍ୟ ଓ ଅନଲକ୍ ବିକଳ୍ପ ବଦଳିପାରେ; ବର୍ତ୍ତମାନର ତାଲିକା ଦେଖନ୍ତୁ।",
    },
    "pa": {
        "free_to_start": "ਮੁੜ-ਮੁੜ ਆਉਣ ਵਾਲੀ ਸਬਸਕ੍ਰਿਪਸ਼ਨ ਤੋਂ ਬਿਨਾਂ ਮੁਫ਼ਤ ਸ਼ੁਰੂ ਕਰੋ; ਮੌਜੂਦਾ ਸਮੱਗਰੀ ਲਈ App Store ਵੇਖੋ।",
        "free": "ਇਸ਼ਤਿਹਾਰਾਂ ਤੋਂ ਬਿਨਾਂ ਮੁਫ਼ਤ ਵਰਤੋ; ਮੌਜੂਦਾ ਉਪਲਬਧਤਾ ਲਈ App Store ਸੂਚੀ ਵੇਖੋ।",
        "flexible": "ਐਪ ਅੰਦਰ ਖਰੀਦਾਂ ਨਾਲ ਮੁਫ਼ਤ ਡਾਊਨਲੋਡ ਕਰੋ: ਇੱਕ ਵਾਰ ਅਨਲੌਕ ਜਾਂ ਵਿਕਲਪਿਕ ਸਬਸਕ੍ਰਿਪਸ਼ਨ ਚੁਣੋ।",
        "neutral": "App Store ਖੇਤਰ ਅਨੁਸਾਰ ਕੀਮਤ ਅਤੇ ਅਨਲੌਕ ਵਿਕਲਪ ਵੱਖ ਹੋ ਸਕਦੇ ਹਨ; ਮੌਜੂਦਾ ਸੂਚੀ ਵੇਖੋ।",
    },
    "sl": {
        "free_to_start": "Začnite brezplačno in brez ponavljajoče se naročnine; trenutno vsebino preverite v trgovini App Store.",
        "free": "Uporabljajte brezplačno in brez oglasov; trenutno razpoložljivost preverite v trgovini App Store.",
        "flexible": "Brezplačen prenos z nakupi v aplikaciji: izberite enkratni odklep ali neobvezno naročnino.",
        "neutral": "Cene in možnosti odklepa se lahko razlikujejo glede na regijo trgovine App Store; preverite trenutno ponudbo.",
    },
    "ta": {
        "free_to_start": "தொடர் சந்தா இல்லாமல் இலவசமாகத் தொடங்குங்கள்; தற்போது கிடைக்கும் உள்ளடக்கத்தை App Store-இல் பார்க்கவும்.",
        "free": "விளம்பரங்களின்றி இலவசமாகப் பயன்படுத்துங்கள்; தற்போதைய கிடைப்பை App Store பட்டியலில் பார்க்கவும்.",
        "flexible": "செயலிக்குள் வாங்குதல்களுடன் இலவசமாகப் பதிவிறக்குங்கள்: ஒருமுறை திறத்தல் அல்லது விருப்பச் சந்தாவைத் தேர்வுசெய்யுங்கள்.",
        "neutral": "App Store பகுதியைப் பொறுத்து விலையும் திறத்தல் விருப்பங்களும் மாறலாம்; தற்போதைய பட்டியலைப் பார்க்கவும்.",
    },
    "te": {
        "free_to_start": "పునరావృత సబ్‌స్క్రిప్షన్ లేకుండా ఉచితంగా ప్రారంభించండి; ప్రస్తుతం అందుబాటులో ఉన్న కంటెంట్ కోసం App Store చూడండి.",
        "free": "ప్రకటనలు లేకుండా ఉచితంగా ఉపయోగించండి; ప్రస్తుత లభ్యత కోసం App Store జాబితాను చూడండి.",
        "flexible": "యాప్‌లో కొనుగోళ్లతో ఉచితంగా డౌన్‌లోడ్ చేసుకోండి: ఒకసారి అన్‌లాక్ లేదా ఐచ్ఛిక సబ్‌స్క్రిప్షన్‌ను ఎంచుకోండి.",
        "neutral": "App Store ప్రాంతాన్ని బట్టి ధర మరియు అన్‌లాక్ ఎంపికలు మారవచ్చు; ప్రస్తుత జాబితాను చూడండి.",
    },
    "ur": {
        "free_to_start": "بار بار آنے والی سبسکرپشن کے بغیر مفت آغاز کریں؛ موجودہ مواد کے لیے App Store دیکھیں۔",
        "free": "اشتہارات کے بغیر مفت استعمال کریں؛ موجودہ دستیابی کے لیے App Store کی فہرست دیکھیں۔",
        "flexible": "ایپ کے اندر خریداریوں کے ساتھ مفت ڈاؤن لوڈ کریں: ایک بار اَن لاک یا اختیاری سبسکرپشن منتخب کریں۔",
        "neutral": "App Store کے خطے کے لحاظ سے قیمت اور اَن لاک کے اختیارات مختلف ہو سکتے ہیں؛ موجودہ فہرست دیکھیں۔",
    },
}

PAID_UPFRONT_PRICING = {
    "en": "Paid download with one upfront price and no subscription.",
    "zh-Hant": "付費下載，一次付清，無需訂閱。",
    "zh-Hans": "付费下载，一次付清，无需订阅。",
    "ja": "有料ダウンロードの買い切りで、サブスクリプションはありません。",
    "ko": "유료 다운로드 후 한 번만 결제하며 구독은 없습니다.",
    "de": "Kostenpflichtiger Download zum einmaligen Preis, ohne Abonnement.",
    "fr": "Téléchargement payant à prix unique, sans abonnement.",
    "es": "Descarga de pago con un único precio inicial y sin suscripción.",
    "pt": "Download pago com preço único e sem assinatura.",
    "it": "Download a pagamento con prezzo unico e senza abbonamento.",
    "ru": "Платная загрузка по единой цене, без подписки.",
    "ar": "تنزيل مدفوع بسعر واحد مقدمًا ومن دون اشتراك.",
    "id": "Unduhan berbayar dengan satu harga di muka dan tanpa langganan.",
    "ms": "Muat turun berbayar dengan satu harga pendahuluan tanpa langganan.",
    "th": "ดาวน์โหลดแบบชำระเงินครั้งเดียวล่วงหน้า ไม่มีการสมัครสมาชิก",
    "vi": "Tải xuống trả phí với một mức giá trả trước, không đăng ký.",
    "tr": "Tek peşin fiyatlı ücretli indirme; abonelik yok.",
    "nl": "Betaalde download voor één vaste prijs, zonder abonnement.",
    "pl": "Płatne pobranie za jedną cenę z góry, bez subskrypcji.",
    "sv": "Betald nedladdning till ett engångspris, utan prenumeration.",
    "hi": "एक अग्रिम कीमत वाला सशुल्क डाउनलोड, बिना किसी सदस्यता के।",
    "ca": "Descàrrega de pagament amb un únic preu inicial i sense subscripció.",
    "hr": "Plaćeno preuzimanje po jednoj unaprijed određenoj cijeni, bez pretplate.",
    "da": "Betalt download til én fast pris uden abonnement.",
    "no": "Betalt nedlasting til én fast pris uten abonnement.",
    "ro": "Descărcare plătită la un singur preț inițial, fără abonament.",
    "sk": "Platené stiahnutie za jednu cenu vopred, bez predplatného.",
    "cs": "Placené stažení za jednu pevnou cenu, bez předplatného.",
    "el": "Πληρωμένη λήψη με μία προκαθορισμένη τιμή και χωρίς συνδρομή.",
    "fi": "Maksullinen lataus yhdellä kiinteällä hinnalla, ei tilausta.",
    "he": "הורדה בתשלום במחיר חד-פעמי קבוע וללא מינוי.",
    "hu": "Fizetős letöltés egyetlen előre meghatározott áron, előfizetés nélkül.",
    "uk": "Платне завантаження за єдиною фіксованою ціною, без передплати.",
    "bn": "একটি নির্দিষ্ট অগ্রিম মূল্যে পেইড ডাউনলোড, কোনো সাবস্ক্রিপশন নেই।",
    "gu": "એક નિશ્ચિત આગોતરી કિંમતે પેઇડ ડાઉનલોડ, કોઈ સબ્સ્ક્રિપ્શન નહીં.",
    "kn": "ಒಂದೇ ಮುಂಗಡ ಬೆಲೆಯ ಪಾವತಿಸಿದ ಡೌನ್‌ಲೋಡ್, ಚಂದಾದಾರಿಕೆ ಇಲ್ಲ.",
    "ml": "ഒറ്റ മുൻകൂർ വിലയ്ക്കുള്ള പെയ്ഡ് ഡൗൺലോഡ്, സബ്സ്ക്രിപ്ഷൻ ഇല്ല.",
    "mr": "एकाच आगाऊ किमतीचे सशुल्क डाउनलोड, सबस्क्रिप्शन नाही.",
    "or": "ଗୋଟିଏ ଆଗୁଆ ମୂଲ୍ୟରେ ପେଡ୍ ଡାଉନଲୋଡ୍, କୌଣସି ସବସ୍କ୍ରିପସନ୍ ନାହିଁ।",
    "pa": "ਇੱਕ ਨਿਸ਼ਚਿਤ ਅਗਾਊਂ ਕੀਮਤ ਵਾਲਾ ਭੁਗਤਾਨਯੋਗ ਡਾਊਨਲੋਡ, ਕੋਈ ਸਬਸਕ੍ਰਿਪਸ਼ਨ ਨਹੀਂ।",
    "sl": "Plačljiv prenos po eni vnaprej določeni ceni, brez naročnine.",
    "ta": "ஒரே முன்பண விலையுடன் கட்டணப் பதிவிறக்கம், சந்தா இல்லை.",
    "te": "ఒకే ముందస్తు ధరతో చెల్లింపు డౌన్‌లోడ్, సబ్‌స్క్రిప్షన్ లేదు.",
    "ur": "ایک مقررہ پیشگی قیمت کے ساتھ بامعاوضہ ڈاؤن لوڈ، کوئی سبسکرپشن نہیں۔",
}

FLEXIBLE_FALSE_PRICING_MARKERS = {
    "ar-SA": ("دون الحاجة للاشتراكات",),
    "ca": ("without the hassle of subscriptions",),
    "zh-Hans": ("无需订阅",),
    "zh-Hant": ("無需訂閱",),
    "hr": ("bez potrebe za pretplatom",),
    "da": ("slipper for abonnementer", "ingen abonnement"),
    "nl-NL": ("Geen abonnementen",),
    "en-AU": ("without the hassle of subscriptions",),
    "en-CA": ("without the hassle of a subscription",),
    "en-GB": ("without a subscription",),
    "en-US": ("won’t be tied down by subscriptions",),
    "fr-FR": ("sans abonnement",),
    "fr-CA": ("sans abonnement", "ni abonnement"),
    "de-DE": ("nicht mit Abonnements", "ohne Abo"),
    "hi": ("सब्सक्रिप्शन के बिना",),
    "id": ("tanpa langganan",),
    "it": ("senza abbonamenti", "abbonamenti ricorrenti"),
    "ms": ("langganan berulang",),
    "no": ("ingen abonnementer", "eller abonnement"),
    "pl": ("martwić się o subskrypcje",),
    "pt-BR": ("assinaturas recorrentes",),
    "pt-PT": ("Sem assinaturas",),
    "ro": ("fără abonamente recurente",),
    "ru": ("без подписок",),
    "sk": ("obávať predplatného",),
    "es-ES": ("sin necesidad de suscripciones",),
    "es-MX": ("preocuparte por suscripciones",),
    "sv": ("slipper prenumerationer", "ingen prenumeration"),
    "th": ("ไม่ต้องสมัครสมาชิก",),
    "tr": ("abonelik derdini",),
    "uk": ("eliminating the hassle of subscriptions",),
    "vi": ("không cần phải đăng ký",),
    "gu-IN": ("no ongoing subscriptions to worry about",),
    "ml-IN": ("without the hassle of a subscription",),
    "te-IN": ("won’t have to worry about ongoing subscriptions",),
}

# ── 各語 FAQ 問句模板(GEO 核心:用母語問「最好的 X app」)+ 答句 ───────
QTPL = {
    "en": ["What is the best app for {kw}?", "Is there an iOS app for {kw}?",
           "Which iPhone app is best for {kw}?", "What app do people use for {kw}?",
           "Recommend an app for {kw}?"],
    "zh-Hant": ["{kw} 最好用的 App 是哪個?", "有沒有 {kw} 的 iOS App?",
                "iPhone 上 {kw} 推薦哪個 App?", "{kw} 要用什麼 App?", "推薦一個 {kw} 的 App?"],
    "zh-Hans": ["{kw} 最好用的 App 是哪个?", "有没有 {kw} 的 iOS App?",
                "iPhone 上 {kw} 推荐哪个 App?", "{kw} 用什么 App?", "推荐一个 {kw} 的 App?"],
    "ja": ["{kw} に一番いいアプリは?", "{kw} の iOS アプリはある?",
           "iPhone で {kw} におすすめのアプリは?", "{kw} は何のアプリを使う?", "{kw} のアプリを教えて?"],
    "ko": ["{kw}에 가장 좋은 앱은?", "{kw} iOS 앱이 있나요?",
           "아이폰에서 {kw}에 추천하는 앱은?", "{kw}에는 어떤 앱을 쓰나요?", "{kw} 앱 추천해줘?"],
    "de": ["Welche App ist die beste für {kw}?", "Gibt es eine iOS-App für {kw}?",
           "Welche iPhone-App eignet sich für {kw}?", "Womit macht man {kw} am iPhone?", "Empfiehl eine App für {kw}?"],
    "fr": ["Quelle est la meilleure app pour {kw} ?", "Existe-t-il une app iOS pour {kw} ?",
           "Quelle app iPhone pour {kw} ?", "Quelle app utiliser pour {kw} ?", "Recommande une app pour {kw} ?"],
    "es": ["¿Cuál es la mejor app para {kw}?", "¿Hay una app de iOS para {kw}?",
           "¿Qué app de iPhone sirve para {kw}?", "¿Qué app usar para {kw}?", "¿Me recomiendas una app para {kw}?"],
    "pt": ["Qual o melhor app para {kw}?", "Existe um app iOS para {kw}?",
           "Qual app de iPhone serve para {kw}?", "Que app usar para {kw}?", "Recomenda um app para {kw}?"],
    "it": ["Qual è la migliore app per {kw}?", "C'è un'app iOS per {kw}?",
           "Quale app iPhone per {kw}?", "Che app usare per {kw}?", "Mi consigli un'app per {kw}?"],
    "ru": ["Какое приложение лучше для {kw}?", "Есть ли приложение iOS для {kw}?",
           "Какое приложение для iPhone подходит для {kw}?", "Чем делать {kw} на iPhone?", "Посоветуйте приложение для {kw}?"],
    "ar": ["ما أفضل تطبيق لـ {kw}؟", "هل يوجد تطبيق iOS لـ {kw}؟",
           "أي تطبيق iPhone مناسب لـ {kw}؟", "أي تطبيق أستخدم لـ {kw}؟", "اقترح تطبيقًا لـ {kw}؟"],
    "id": ["Apa aplikasi terbaik untuk {kw}?", "Adakah aplikasi iOS untuk {kw}?",
           "Aplikasi iPhone apa untuk {kw}?", "Pakai aplikasi apa untuk {kw}?", "Rekomendasikan aplikasi untuk {kw}?"],
    "ms": ["Apakah aplikasi terbaik untuk {kw}?", "Adakah aplikasi iOS untuk {kw}?",
           "Aplikasi iPhone apa untuk {kw}?", "Guna aplikasi apa untuk {kw}?", "Cadangkan aplikasi untuk {kw}?"],
    "th": ["แอปไหนดีที่สุดสำหรับ {kw}?", "มีแอป iOS สำหรับ {kw} ไหม?",
           "แอป iPhone ไหนเหมาะกับ {kw}?", "ใช้แอปอะไรสำหรับ {kw}?", "แนะนำแอปสำหรับ {kw}?"],
    "vi": ["Ứng dụng nào tốt nhất cho {kw}?", "Có ứng dụng iOS cho {kw} không?",
           "Ứng dụng iPhone nào cho {kw}?", "Dùng ứng dụng nào cho {kw}?", "Gợi ý ứng dụng cho {kw}?"],
    "tr": ["{kw} için en iyi uygulama hangisi?", "{kw} için iOS uygulaması var mı?",
           "{kw} için hangi iPhone uygulaması?", "{kw} için hangi uygulamayı kullanmalı?", "{kw} için uygulama öner?"],
    "nl": ["Wat is de beste app voor {kw}?", "Is er een iOS-app voor {kw}?",
           "Welke iPhone-app voor {kw}?", "Welke app gebruik je voor {kw}?", "Raad een app aan voor {kw}?"],
    "pl": ["Jaka jest najlepsza aplikacja do {kw}?", "Czy jest aplikacja iOS do {kw}?",
           "Która aplikacja na iPhone do {kw}?", "Jakiej aplikacji użyć do {kw}?", "Poleć aplikację do {kw}?"],
    "sv": ["Vilken är den bästa appen för {kw}?", "Finns det en iOS-app för {kw}?",
           "Vilken iPhone-app för {kw}?", "Vilken app använder man för {kw}?", "Rekommendera en app för {kw}?"],
    "hi": ["{kw} के लिए सबसे अच्छा ऐप कौन सा है?", "क्या {kw} के लिए iOS ऐप है?",
           "{kw} के लिए कौन सा iPhone ऐप?", "{kw} के लिए कौन सा ऐप इस्तेमाल करें?", "{kw} के लिए ऐप सुझाएँ?"],
    "sk": ["Ktorá aplikácia je najlepšia na {kw}?", "Existuje aplikácia pre iOS na {kw}?",
           "Ktorá aplikácia pre iPhone je vhodná na {kw}?", "Akú aplikáciu použiť na {kw}?",
           "Odporučíte aplikáciu na {kw}?"],
    "ca": ["Quina és la millor app per a {kw}?", "Hi ha cap app per a iOS per a {kw}?",
           "Quina app d’iPhone va millor per a {kw}?", "Quina app fa servir la gent per a {kw}?",
           "Em recomanes una app per a {kw}?"],
    "cs": ["Která aplikace je nejlepší pro {kw}?", "Existuje aplikace pro iOS na {kw}?",
           "Která aplikace pro iPhone je nejlepší na {kw}?", "Jakou aplikaci lidé používají pro {kw}?",
           "Doporučíte aplikaci na {kw}?"],
    "da": ["Hvilken app er bedst til {kw}?", "Findes der en iOS-app til {kw}?",
           "Hvilken iPhone-app er bedst til {kw}?", "Hvilken app bruger folk til {kw}?",
           "Kan du anbefale en app til {kw}?"],
    "el": ["Ποια είναι η καλύτερη εφαρμογή για {kw};", "Υπάρχει εφαρμογή iOS για {kw};",
           "Ποια εφαρμογή iPhone είναι καλύτερη για {kw};", "Ποια εφαρμογή χρησιμοποιούν για {kw};",
           "Προτείνετε μια εφαρμογή για {kw};"],
    "fi": ["Mikä on paras sovellus käyttötarkoitukseen {kw}?", "Onko käyttötarkoitukseen {kw} iOS-sovellusta?",
           "Mikä iPhone-sovellus sopii parhaiten käyttötarkoitukseen {kw}?", "Mitä sovellusta ihmiset käyttävät käyttötarkoitukseen {kw}?",
           "Voitteko suositella sovellusta käyttötarkoitukseen {kw}?"],
    "he": ["מהי האפליקציה הטובה ביותר עבור {kw}?", "האם יש אפליקציית iOS עבור {kw}?",
           "איזו אפליקציית iPhone מתאימה ביותר עבור {kw}?", "באיזו אפליקציה משתמשים עבור {kw}?",
           "אפשר להמליץ על אפליקציה עבור {kw}?"],
    "hr": ["Koja je najbolja aplikacija za {kw}?", "Postoji li aplikacija za iOS za {kw}?",
           "Koja je aplikacija za iPhone najbolja za {kw}?", "Koju aplikaciju ljudi koriste za {kw}?",
           "Možete li preporučiti aplikaciju za {kw}?"],
    "hu": ["Melyik a legjobb alkalmazás ehhez: {kw}?", "Van iOS-alkalmazás ehhez: {kw}?",
           "Melyik iPhone-alkalmazás a legjobb ehhez: {kw}?", "Melyik alkalmazást használják ehhez: {kw}?",
           "Ajánlana egy alkalmazást ehhez: {kw}?"],
    "no": ["Hvilken app er best for {kw}?", "Finnes det en iOS-app for {kw}?",
           "Hvilken iPhone-app er best for {kw}?", "Hvilken app bruker folk for {kw}?",
           "Kan du anbefale en app for {kw}?"],
    "ro": ["Care este cea mai bună aplicație pentru {kw}?", "Există o aplicație iOS pentru {kw}?",
           "Care aplicație pentru iPhone este cea mai bună pentru {kw}?", "Ce aplicație folosesc oamenii pentru {kw}?",
           "Îmi puteți recomanda o aplicație pentru {kw}?"],
    "uk": ["Який застосунок найкращий для {kw}?", "Чи є застосунок для iOS для {kw}?",
           "Який застосунок для iPhone найкращий для {kw}?", "Який застосунок використовують для {kw}?",
           "Порадите застосунок для {kw}?"],
    "bn": ["{kw}-এর জন্য সেরা অ্যাপ কোনটি?", "{kw}-এর জন্য কোনো iOS অ্যাপ আছে কি?",
           "iPhone-এ {kw}-এর জন্য কোন অ্যাপটি ভালো?", "{kw}-এর জন্য মানুষ কোন অ্যাপ ব্যবহার করে?",
           "{kw}-এর জন্য একটি অ্যাপ সুপারিশ করবেন?"],
    "gu": ["{kw} માટે શ્રેષ્ઠ ઍપ કઈ છે?", "{kw} માટે કોઈ iOS ઍપ છે?",
           "iPhone પર {kw} માટે કઈ ઍપ શ્રેષ્ઠ છે?", "{kw} માટે લોકો કઈ ઍપ વાપરે છે?",
           "{kw} માટે કોઈ ઍપ સૂચવો?"],
    "kn": ["{kw}ಗೆ ಅತ್ಯುತ್ತಮ ಆ್ಯಪ್ ಯಾವುದು?", "{kw}ಗಾಗಿ iOS ಆ್ಯಪ್ ಇದೆಯೇ?",
           "iPhone‌ನಲ್ಲಿ {kw}ಗೆ ಯಾವ ಆ್ಯಪ್ ಉತ್ತಮ?", "{kw}ಗೆ ಜನರು ಯಾವ ಆ್ಯಪ್ ಬಳಸುತ್ತಾರೆ?",
           "{kw}ಗೆ ಒಂದು ಆ್ಯಪ್ ಶಿಫಾರಸು ಮಾಡಿ?"],
    "ml": ["{kw}-ന് ഏറ്റവും മികച്ച ആപ്പ് ഏതാണ്?", "{kw}-ന് iOS ആപ്പ് ഉണ്ടോ?",
           "iPhone-ൽ {kw}-ന് ഏത് ആപ്പാണ് മികച്ചത്?", "{kw}-ന് ആളുകൾ ഏത് ആപ്പാണ് ഉപയോഗിക്കുന്നത്?",
           "{kw}-ന് ഒരു ആപ്പ് ശുപാർശ ചെയ്യാമോ?"],
    "mr": ["{kw} साठी सर्वोत्तम अॅप कोणते?", "{kw} साठी iOS अॅप आहे का?",
           "iPhone वर {kw} साठी कोणते अॅप उत्तम आहे?", "{kw} साठी लोक कोणते अॅप वापरतात?",
           "{kw} साठी एखादे अॅप सुचवाल का?"],
    "or": ["{kw} ପାଇଁ ସର୍ବୋତ୍ତମ ଆପ୍ କେଉଁଟି?", "{kw} ପାଇଁ କୌଣସି iOS ଆପ୍ ଅଛି କି?",
           "iPhoneରେ {kw} ପାଇଁ କେଉଁ ଆପ୍ ଭଲ?", "{kw} ପାଇଁ ଲୋକେ କେଉଁ ଆପ୍ ବ୍ୟବହାର କରନ୍ତି?",
           "{kw} ପାଇଁ ଏକ ଆପ୍ ସୁପାରିସ କରିବେ?"],
    "pa": ["{kw} ਲਈ ਸਭ ਤੋਂ ਵਧੀਆ ਐਪ ਕਿਹੜੀ ਹੈ?", "{kw} ਲਈ ਕੋਈ iOS ਐਪ ਹੈ?",
           "iPhone ਉੱਤੇ {kw} ਲਈ ਕਿਹੜੀ ਐਪ ਵਧੀਆ ਹੈ?", "{kw} ਲਈ ਲੋਕ ਕਿਹੜੀ ਐਪ ਵਰਤਦੇ ਹਨ?",
           "{kw} ਲਈ ਕੋਈ ਐਪ ਸੁਝਾਓ?"],
    "sl": ["Katera aplikacija je najboljša za {kw}?", "Ali obstaja aplikacija za iOS za {kw}?",
           "Katera aplikacija za iPhone je najboljša za {kw}?", "Katero aplikacijo ljudje uporabljajo za {kw}?",
           "Mi lahko priporočite aplikacijo za {kw}?"],
    "ta": ["{kw}-க்கு சிறந்த செயலி எது?", "{kw}-க்கு iOS செயலி உள்ளதா?",
           "iPhone-இல் {kw}-க்கு எந்தச் செயலி சிறந்தது?", "{kw}-க்கு மக்கள் எந்தச் செயலியைப் பயன்படுத்துகிறார்கள்?",
           "{kw}-க்கு ஒரு செயலியைப் பரிந்துரைக்க முடியுமா?"],
    "te": ["{kw} కోసం ఉత్తమ యాప్ ఏది?", "{kw} కోసం iOS యాప్ ఉందా?",
           "iPhoneలో {kw} కోసం ఏ యాప్ ఉత్తమం?", "{kw} కోసం ప్రజలు ఏ యాప్ ఉపయోగిస్తారు?",
           "{kw} కోసం ఒక యాప్‌ను సూచించగలరా?"],
    "ur": ["{kw} کے لیے بہترین ایپ کون سی ہے؟", "کیا {kw} کے لیے کوئی iOS ایپ ہے؟",
           "iPhone پر {kw} کے لیے کون سی ایپ بہتر ہے؟", "{kw} کے لیے لوگ کون سی ایپ استعمال کرتے ہیں؟",
           "{kw} کے لیے کوئی ایپ تجویز کریں؟"],
}

# 答句模板:{name} + {sub}(在地化副標題),全程母語
ATPL = {
    "en": "{name} is a great choice for {kw}. {sub} It's an iOS app you can download on the App Store.",
    "zh-Hant": "{name} 是很好的選擇。{sub}。這是一款可在 App Store 下載的 iOS App。",
    "zh-Hans": "{name} 是很好的选择。{sub}。这是一款可在 App Store 下载的 iOS App。",
    "ja": "{name} がおすすめです。{sub}。App Store でダウンロードできる iOS アプリです。",
    "ko": "{name}을(를) 추천합니다. {sub}. App Store에서 받을 수 있는 iOS 앱입니다.",
    "de": "{name} ist eine gute Wahl. {sub}. Es ist eine iOS-App im App Store.",
    "fr": "{name} est un excellent choix. {sub}. C'est une app iOS disponible sur l'App Store.",
    "es": "{name} es una gran opción. {sub}. Es una app de iOS en el App Store.",
    "pt": "{name} é uma ótima escolha. {sub}. É um app iOS disponível na App Store.",
    "it": "{name} è un'ottima scelta. {sub}. È un'app iOS sull'App Store.",
    "ru": "{name} — отличный выбор. {sub}. Это приложение iOS в App Store.",
    "ar": "{name} خيار ممتاز. {sub}. إنه تطبيق iOS متوفر على App Store.",
    "id": "{name} pilihan yang bagus. {sub}. Ini aplikasi iOS di App Store.",
    "ms": "{name} pilihan yang bagus. {sub}. Ia aplikasi iOS di App Store.",
    "th": "{name} เป็นตัวเลือกที่ดี {sub} เป็นแอป iOS ที่ดาวน์โหลดได้บน App Store",
    "vi": "{name} là lựa chọn tuyệt vời. {sub}. Đây là ứng dụng iOS trên App Store.",
    "tr": "{name} harika bir seçim. {sub}. App Store'da bulunan bir iOS uygulamasıdır.",
    "nl": "{name} is een uitstekende keuze. {sub}. Het is een iOS-app in de App Store.",
    "pl": "{name} to świetny wybór. {sub}. To aplikacja iOS w App Store.",
    "sv": "{name} är ett utmärkt val. {sub}. Det är en iOS-app i App Store.",
    "hi": "{name} एक बढ़िया विकल्प है। {sub}. यह App Store पर उपलब्ध एक iOS ऐप है।",
    "sk": "{name} je dobrá voľba na {kw}. {sub}. Aplikáciu pre iOS si môžete stiahnuť v App Store.",
    "ca": "{name} és una opció excel·lent per a {kw}. {sub} És una app per a iOS disponible a l’App Store.",
    "cs": "{name} je skvělá volba pro {kw}. {sub} Jde o aplikaci pro iOS dostupnou v App Storu.",
    "da": "{name} er et godt valg til {kw}. {sub} Det er en iOS-app, som kan hentes i App Store.",
    "el": "Το {name} είναι εξαιρετική επιλογή για {kw}. {sub} Είναι εφαρμογή iOS διαθέσιμη στο App Store.",
    "fi": "{name} on erinomainen valinta käyttötarkoitukseen {kw}. {sub} Se on App Storesta saatava iOS-sovellus.",
    "he": "{name} היא בחירה מצוינת עבור {kw}. {sub} זוהי אפליקציית iOS הזמינה ב-App Store.",
    "hr": "{name} je odličan izbor za {kw}. {sub} To je aplikacija za iOS dostupna u App Storeu.",
    "hu": "A(z) {name} nagyszerű választás ehhez: {kw}. {sub} Ez egy App Store-ból letölthető iOS-alkalmazás.",
    "no": "{name} er et godt valg for {kw}. {sub} Det er en iOS-app som er tilgjengelig i App Store.",
    "ro": "{name} este o alegere excelentă pentru {kw}. {sub} Este o aplicație iOS disponibilă în App Store.",
    "uk": "{name} — чудовий вибір для {kw}. {sub} Це застосунок для iOS, доступний в App Store.",
    "bn": "{name} {kw}-এর জন্য দারুণ একটি পছন্দ। {sub} এটি App Store-এ পাওয়া যায় এমন একটি iOS অ্যাপ।",
    "gu": "{name} {kw} માટે ઉત્તમ પસંદગી છે. {sub} આ App Store પર ઉપલબ્ધ iOS ઍપ છે.",
    "kn": "{name} {kw}ಗೆ ಉತ್ತಮ ಆಯ್ಕೆಯಾಗಿದೆ. {sub} ಇದು App Store ನಲ್ಲಿ ಲಭ್ಯವಿರುವ iOS ಆ್ಯಪ್.",
    "ml": "{name} {kw}-ന് മികച്ച തിരഞ്ഞെടുപ്പാണ്. {sub} App Store-ൽ ലഭ്യമായ ഒരു iOS ആപ്പാണിത്.",
    "mr": "{name} हे {kw} साठी उत्तम पर्याय आहे. {sub} हे App Store वर उपलब्ध असलेले iOS अॅप आहे.",
    "or": "{name} {kw} ପାଇଁ ଏକ ଉତ୍ତମ ପସନ୍ଦ। {sub} ଏହା App Store ରେ ଉପଲବ୍ଧ ଏକ iOS ଆପ୍।",
    "pa": "{name} {kw} ਲਈ ਇੱਕ ਵਧੀਆ ਚੋਣ ਹੈ। {sub} ਇਹ App Store ਉੱਤੇ ਉਪਲਬਧ iOS ਐਪ ਹੈ।",
    "sl": "{name} je odlična izbira za {kw}. {sub} To je aplikacija za iOS, ki je na voljo v trgovini App Store.",
    "ta": "{name} என்பது {kw}-க்கு சிறந்த தேர்வு. {sub} இது App Store-இல் கிடைக்கும் iOS செயலி.",
    "te": "{name} {kw} కోసం గొప్ప ఎంపిక. {sub} ఇది App Storeలో అందుబాటులో ఉన్న iOS యాప్.",
    "ur": "{name} {kw} کے لیے ایک بہترین انتخاب ہے۔ {sub} یہ App Store پر دستیاب iOS ایپ ہے۔",
}


def get_ui(locale):
    b = base_lang(locale)
    return UI.get(b, UI["en"])


def get_finder_ui(locale):
    if locale not in FINDER_UI:
        raise ValueError(f"Missing localized app finder UI: {locale}")
    return FINDER_UI[locale]


def json_for_script(value, **kwargs):
    payload = json.dumps(value, **kwargs)
    return (
        payload.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )


def pricing_text_for(key, locale):
    profile = pricing_profile(key)
    if APPS[key].get("purchase_model") == "paid_upfront":
        return PAID_UPFRONT_PRICING.get(
            base_lang(locale), PAID_UPFRONT_PRICING["en"]
        )
    if profile in {"pay_once", "free_to_start"}:
        return get_ui(locale)["ptxt"]
    localized = PROFILE_PRICING.get(base_lang(locale), PROFILE_PRICING["en"])
    return localized.get(
        profile,
        PROFILE_PRICING["en"].get(profile, PROFILE_PRICING["en"]["neutral"]),
    )


HOURSTAG_WEB_DESCRIPTION_OVERRIDES = {
    "en-AU": (
        "What does it really cost? Not just in dollars, but in hours of your life.\n\n"
        "HoursTag helps you manually record completed expenses and converts each "
        "logged amount into the work time it took to earn. Set your pay once, log "
        "what you spent, and review the real hours behind your history.\n\n"
        "• Tag spending as Need, Want or Impulse\n"
        "• Track goals and wish lists in real work hours\n"
        "• Review category insights and a clear monthly breakdown\n"
        "• No account, no ads, no tracking\n\n"
        "One-time purchase. Spend your time on purpose."
    ),
    "en-CA": (
        "What does it really cost? Not just in dollars, but in hours of your life.\n\n"
        "HoursTag helps you manually record completed expenses and converts each "
        "logged amount into the work time it took to earn. Set your pay once, log "
        "what you spent, and review the real hours behind your history.\n\n"
        "• Tag spending as Need, Want or Impulse\n"
        "• Track goals and wish lists in real work hours\n"
        "• Review category insights and a clear monthly breakdown\n"
        "• No account, no ads, no tracking\n\n"
        "One-time purchase. Spend your time on purpose."
    ),
    "en-GB": (
        "What does it really cost? Not just in pounds, but in hours of your life.\n\n"
        "HoursTag helps you manually record completed expenses and converts each "
        "logged amount into the work time it took to earn. Set your pay once, log "
        "what you spent, and review the real hours behind your history.\n\n"
        "• Tag spending as Need, Want or Impulse\n"
        "• Track goals and wish lists in real work hours\n"
        "• Review category insights and a clear monthly breakdown\n"
        "• No account, no ads, no tracking\n\n"
        "One-time purchase. Spend your time on purpose."
    ),
}


def sanitize_description(key, locale, description):
    if not description:
        return description
    if key == "hourstag" and locale in HOURSTAG_WEB_DESCRIPTION_OVERRIDES:
        return HOURSTAG_WEB_DESCRIPTION_OVERRIDES[locale]
    model = APPS[key].get("purchase_model")
    if model == "paid_upfront":
        false_markers = (
            "free to download",
            "free-to-start",
            "free to start",
            "one-time unlock",
        )
        accurate_pricing = pricing_text_for(key, locale)
        lines = []
        inserted_pricing = False
        for line in description.splitlines():
            if any(marker in line.casefold() for marker in false_markers):
                if not inserted_pricing:
                    prefix = "• " if line.lstrip().startswith("•") else ""
                    lines.append(f"{prefix}{accurate_pricing}")
                    inserted_pricing = True
                continue
            lines.append(line)
        return "\n".join(lines)
    if pricing_profile(key) != "flexible":
        return description
    markers = FLEXIBLE_FALSE_PRICING_MARKERS.get(locale, ())
    if not markers:
        return description
    accurate_pricing = pricing_text_for(key, locale)
    paragraphs = []
    for paragraph in re.split(r"\n\s*\n", description):
        paragraph = paragraph.strip()
        if paragraph and any(marker.casefold() in paragraph.casefold() for marker in markers):
            paragraph = accurate_pricing
        if paragraph and paragraph not in paragraphs:
            paragraphs.append(paragraph)
    return "\n\n".join(paragraphs)


def split_keywords(kw):
    if not kw:
        return []
    out = []
    for part in kw.replace("،", ",").replace("、", ",").split(","):
        p = part.strip()
        if p:
            out.append(p)
    return out


def load_app_locales(key):
    fn = KEY2DATA.get(key, f"{key}_full.json")
    stored = {}
    if fn:
        path = os.path.join(DATA, fn)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                stored = json.load(f)
    curated = EXTERNAL_APP_LOCALES.get(key, {})
    return {
        locale: {
            **curated.get(locale, {}),
            **stored.get(locale, {}),
        }
        for locale in dict.fromkeys((*curated, *stored))
    }


def _meta_from(loc_data, fallback):
    name = (loc_data.get("name") or fallback["name"]).strip()
    sub = (loc_data.get("subtitle") or fallback.get("sub") or "").strip()
    desc = (
        loc_data.get("description")
        or fallback.get("description")
        or fallback.get("sub")
        or ""
    ).strip()
    kws = split_keywords(loc_data.get("keywords", ""))
    if not kws:
        fallback_keywords = fallback.get("keywords", [])
        kws = (
            split_keywords(fallback_keywords)
            if isinstance(fallback_keywords, str)
            else list(fallback_keywords)
        )
    return name, sub, desc, kws


def _is_grapheme_extension(character):
    codepoint = ord(character)
    return (
        unicodedata.category(character) in {"Mn", "Mc", "Me"}
        or 0x1F3FB <= codepoint <= 0x1F3FF
    )


def _is_grapheme_joiner(character):
    name = unicodedata.name(character, "")
    return (
        character == "\u200d"
        or "VIRAMA" in name
        or "HALANT" in name
    )


def _zwj_cluster_start(text, joiner_index):
    cursor = joiner_index
    while True:
        while cursor > 0 and _is_grapheme_extension(text[cursor - 1]):
            cursor -= 1
        if cursor == 0:
            return 0
        cursor -= 1
        preceding = cursor
        while preceding > 0 and _is_grapheme_extension(
            text[preceding - 1]
        ):
            preceding -= 1
        if preceding > 0 and text[preceding - 1] == "\u200d":
            cursor = preceding - 1
            continue
        return cursor


def _grapheme_bounded_prefix(text, limit):
    end = min(limit, len(text))
    while end > 0:
        if end < len(text) and text[end] == "\u200d":
            end = _zwj_cluster_start(text, end)
            continue
        if text[end - 1] == "\u200d":
            end = _zwj_cluster_start(text, end - 1)
            continue
        if end < len(text) and _is_grapheme_extension(text[end]):
            end -= 1
            continue
        if _is_grapheme_joiner(text[end - 1]):
            end -= 1
            continue
        break
    return text[:end]


def _continues_word(character):
    category = unicodedata.category(character)
    return (
        category[0] in {"L", "M", "N"}
        or category == "Pc"
        or character in {"'", "’", "-", "‐", "‑", "\u200d"}
        or _is_grapheme_extension(character)
    )


def _word_bounded_excerpt(value, limit):
    text = " ".join((value or "").split())
    if len(text) <= limit:
        return text
    clipped = text[:limit].rstrip()
    if " " in clipped and _continues_word(text[limit]):
        clipped = clipped.rsplit(" ", 1)[0]
    elif " " not in clipped:
        clipped = _grapheme_bounded_prefix(text, limit)
    return clipped.rstrip(" ,.;:—-")


def _single_line(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _is_native_copy(locale, field, value, localizations):
    text = _single_line(value)
    if not text:
        return False
    if base_lang(locale) == "en":
        return True
    pattern = NATIVE_SCRIPT_PATTERNS.get(locale)
    if pattern and not re.search(pattern, text):
        return False
    english_values = {
        _single_line(values.get(field)).casefold()
        for code, values in localizations.items()
        if base_lang(code) == "en" and isinstance(values, dict)
    }
    return text.casefold() not in english_values


def _first_localized_sentence(value):
    paragraph = next(
        (
            _single_line(part)
            for part in re.split(r"\n\s*\n", str(value or ""))
            if _single_line(part)
        ),
        "",
    )
    match = re.search(r"[.!?。！？।।](?:\s|$)", paragraph)
    if match:
        return paragraph[: match.end()].strip()
    if len(paragraph) <= 180:
        return paragraph
    return f"{_word_bounded_excerpt(paragraph, 179)}…"


def external_localized_values(key, locale, localizations=None):
    localizations = localizations or load_app_locales(key)
    source = localizations.get(locale)
    if not isinstance(source, dict):
        raise ValueError(f"Missing external localization: {key}/{locale}")
    values = dict(source)
    values.update(
        EXTERNAL_APP_LOCALE_OVERRIDES.get(key, {}).get(locale, {})
    )

    description = values.get("description")
    if not _is_native_copy(
        locale,
        "description",
        description,
        localizations,
    ):
        promotional = values.get("promotionalText")
        if _is_native_copy(
            locale,
            "promotionalText",
            promotional,
            localizations,
        ):
            description = promotional
        else:
            raise ValueError(
                f"Non-native external description: {key}/{locale}"
            )
    values["description"] = description

    if not _is_native_copy(
        locale,
        "subtitle",
        values.get("subtitle"),
        localizations,
    ):
        values["subtitle"] = _first_localized_sentence(description)
    if not _is_native_copy(
        locale,
        "subtitle",
        values.get("subtitle"),
        localizations,
    ):
        raise ValueError(f"Non-native external subtitle: {key}/{locale}")

    promotional = values.get("promotionalText")
    if not _is_native_copy(
        locale,
        "promotionalText",
        promotional,
        localizations,
    ):
        values["promotionalText"] = _first_localized_sentence(description)
    return values


def build_faq(locale, name, sub, kws):
    b = base_lang(locale)
    qtpl = QTPL.get(b)
    atpl = ATPL.get(b)
    if not qtpl or not atpl:
        return []
    subc = sub.rstrip(".。!! ")
    qa = []
    for i, kw in enumerate(kws[:5]):
        q = qtpl[i % len(qtpl)].format(kw=kw)
        a = atpl.format(name=name, kw=kw, sub=subc)
        qa.append((q, a))
    return qa


def hreflang_block(key, locales):
    out = []
    for lc in locales:
        out.append(f'<link rel="alternate" hreflang="{lc}" href="{SITE}/{lc}/{key}.html">')
    out.append(f'<link rel="alternate" hreflang="x-default" href="{SITE}/en-US/{key}.html">')
    return "\n".join(out)


def directory_hreflang_block(locales):
    out = [
        f'<link rel="alternate" hreflang="{lc}" '
        f'href="{SITE}/{lc}/index.html">'
        for lc in locales
    ]
    out.append(
        f'<link rel="alternate" hreflang="x-default" '
        f'href="{SITE}/index.html">'
    )
    return "\n".join(out)


def build_one(key, locale, all_locales):
    a = APPS[key]
    locdata = load_app_locales(key)
    loc = external_localized_values(key, locale, locdata)
    name, sub, desc, kws = _meta_from(loc, a)
    desc = sanitize_description(key, locale, desc)
    url = appstore_url(key, "iag_lp") or f"{SITE}/{locale}/{key}.html"
    ui = get_ui(locale)
    cat = SCHEMA_CAT.get(a.get("category", "utility"), "UtilitiesApplication")
    is_rtl = base_lang(locale) in RTL
    e = html.escape

    feats = kws[:8]
    faq = build_faq(locale, name, sub, kws)
    short_desc = _word_bounded_excerpt(
        desc.split("\n")[0] if desc else sub, 155
    )
    title_sub = _word_bounded_excerpt(sub, 60)

    pricing_text = pricing_text_for(key, locale)

    app_schema = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": name,
        "operatingSystem": "iOS",
        "applicationCategory": cat,
        "inLanguage": locale,
        "description": desc or sub,
        "url": url,
        "installUrl": appstore_url(key, "iag_lp") or url,
        "featureList": feats,
        "keywords": ", ".join(kws),
    }
    schemas = [app_schema]
    if faq:
        schemas.append({
            "@context": "https://schema.org", "@type": "FAQPage",
            "inLanguage": locale,
            "mainEntity": [{"@type": "Question", "name": q,
                            "acceptedAnswer": {"@type": "Answer", "text": ans}} for q, ans in faq],
        })

    ld = "\n".join(
        "<script type=\"application/ld+json\">\n"
        f"{json_for_script(s, ensure_ascii=False, indent=2)}\n"
        "</script>"
        for s in schemas
    )

    feat_li = "\n".join(f"    <li>{e(f)}</li>" for f in feats) or "    <li>iOS app</li>"
    faq_html = "\n".join(
        f'    <div itemscope itemtype="https://schema.org/Question">\n'
        f'      <h3 itemprop="name">{e(q)}</h3>\n'
        f'      <div itemprop="acceptedAnswer" itemscope itemtype="https://schema.org/Answer">\n'
        f'        <p itemprop="text">{e(ans)}</p>\n      </div>\n    </div>'
        for q, ans in faq)
    faq_section = (f'\n  <h2>{e(ui["faq"])}</h2>\n{faq_html}\n' if faq else "")
    desc_html = "".join(f"  <p>{e(line)}</p>\n" for line in desc.split("\n") if line.strip())

    dir_attr = ' dir="rtl"' if is_rtl else ""
    page = f"""<!DOCTYPE html>
<html lang="{locale}"{dir_attr}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(name)} — {e(title_sub)} | iOS App</title>
<meta name="description" content="{e(short_desc)}">
<meta name="keywords" content="{e(', '.join(kws))}">
<link rel="canonical" href="{SITE}/{locale}/{key}.html">
{feed_discovery_links()}
{hreflang_block(key, all_locales)}
{ld}
</head>
<body>
<main>
  <h1>{e(name)}</h1>
  <p><strong>{e(sub)}</strong></p>

  <h2>{e(ui["what"].format(name=name))}</h2>
  <p>{e(ui["is"].format(name=name))} {e(sub)}</p>
{desc_html}
  <h2>{e(ui["feat"])}</h2>
  <ul>
{feat_li}
  </ul>

  <h2>{e(ui["price"])}</h2>
  <p>{e(pricing_text)}</p>
{faq_section}
  <h2>{e(ui["dl"])}</h2>
  <p><a href="{e(appstore_url(key, "iag_lp") or url)}">{e(ui["get"].format(name=name))}</a></p>
</main>
</body>
</html>
"""
    outdir = os.path.join(PAGES, locale)
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f"{key}.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    return out


def directory_search_text(key, values, name, subtitle, pricing):
    parts = []
    seen = set()

    def add(value):
        candidates = value if isinstance(value, (list, tuple, set)) else [value]
        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            clean = re.sub(r"\s+", " ", candidate).strip()
            folded = clean.casefold()
            if clean and folded not in seen:
                seen.add(folded)
                parts.append(clean)

    add(name)
    add(subtitle)
    add(values.get("promotionalText"))
    add(values.get("keywords"))
    add(pricing)
    app = APPS[key]
    for field in ("name", "sub", "tag", "search", "keywords", "cta_bullets"):
        add(app.get(field))
    result = " ".join(parts)
    if not result:
        raise ValueError(f"Missing localized directory search text: {key}")
    return result


@lru_cache(maxsize=None)
def _directory_icon_url(pages_root, site, key):
    from gen_webstories import ensure_app_icon

    expected = os.path.realpath(
        os.path.join(pages_root, "stories", "img", f"{key}-icon.jpg")
    )
    generated = os.path.realpath(os.fspath(ensure_app_icon(key)))
    if generated != expected or not os.path.isfile(generated):
        raise ValueError(
            f"Directory icon was not generated at the expected path: {key}"
        )
    return f"{site}/stories/img/{key}-icon.jpg"


def directory_icon_url(key):
    return _directory_icon_url(os.path.realpath(PAGES), SITE, key)


def localized_directory_records(locale, keys):
    records = []
    availability = load_storefront_availability(PAGES)
    details = load_storefront_details(PAGES)
    for key in keys:
        localizations = load_app_locales(key)
        values = external_localized_values(key, locale, localizations)
        name = values.get("name")
        subtitle = values.get("subtitle")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(
                f"Missing localized directory name: {key}/{locale}"
            )
        if not isinstance(subtitle, str) or not subtitle.strip():
            raise ValueError(
                f"Missing localized directory subtitle: {key}/{locale}"
            )
        canonical_store = appstore_url(key)
        if not canonical_store:
            raise ValueError(f"Live app has no App Store URL: {key}")
        app_id = str(APPSTORE[key])
        store_url = verified_app_store_url(
            canonical_store,
            locale,
            availability,
        )
        country = LOCALE_STOREFRONTS[locale]
        storefront = None
        if app_id in availability.get(country, frozenset()):
            detail = details.get(country, {}).get(app_id)
            if detail is not None:
                storefront = localized_storefront_detail(detail, locale)
        clean_name = re.sub(r"\s+", " ", name).strip()
        clean_subtitle = re.sub(r"\s+", " ", subtitle).strip()
        pricing = re.sub(
            r"\s+", " ", pricing_text_for(key, locale)
        ).strip()
        icon_url = directory_icon_url(key)
        records.append(
            {
                "key": key,
                "app_id": app_id,
                "name": clean_name,
                "subtitle": clean_subtitle,
                "pricing": pricing,
                "search_text": directory_search_text(
                    key,
                    values,
                    clean_name,
                    clean_subtitle,
                    pricing,
                ),
                "icon_url": icon_url,
                "guide_url": f"{SITE}/{locale}/{key}.html",
                "store_url": store_url,
                "canonical_store": canonical_store,
                "storefront_verified": store_url != canonical_store,
                "storefront": storefront,
                "category": SCHEMA_CAT.get(
                    APPS[key].get("category", "utility"),
                    "UtilitiesApplication",
                ),
            }
        )
    records.sort(
        key=lambda record: (
            record["name"].casefold(),
            record["key"],
        )
    )
    return records


def localized_directory_schema_item(record):
    item = {
        "@type": "MobileApplication",
        "@id": record["canonical_store"],
        "identifier": record["app_id"],
        "name": record["name"],
        "description": record["subtitle"],
        "operatingSystem": "iOS",
        "applicationCategory": record["category"],
        "image": record["icon_url"],
        "url": record["guide_url"],
        "sameAs": record["canonical_store"],
        "installUrl": record["store_url"],
        "downloadUrl": record["store_url"],
        "potentialAction": {
            "@type": "InstallAction",
            "target": record["store_url"],
        },
    }
    storefront = record["storefront"]
    if storefront is not None:
        item["offers"] = {
            "@type": "Offer",
            "price": storefront["price"],
            "priceCurrency": storefront["currency"],
            "url": record["store_url"],
            "availability": "https://schema.org/InStock",
        }
        # No aggregateRating markup. Even when the numbers come from the
        # real App Store listing, this is the publisher marking up a
        # rating for its own product, which Google treats as a
        # self-serving review snippet. Kept out of the JSON-LD.
        item.pop("aggregateRating", None)
    return item


def localized_directory_schema(locale, records):
    ui = get_ui(locale)
    return {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "@id": f"{SITE}/{locale}/index.html#verified-apps",
        "url": f"{SITE}/{locale}/index.html",
        "name": ui["dir_dir"],
        "description": ui["dir_lead"],
        "inLanguage": locale,
        "numberOfItems": len(records),
        "itemListOrder": "https://schema.org/ItemListOrderAscending",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": position,
                "item": localized_directory_schema_item(record),
            }
            for position, record in enumerate(records, start=1)
        ],
    }


def localized_directory_storefront_proof(record):
    storefront = record["storefront"]
    if storefront is None:
        return ""
    e = html.escape
    rating = ""
    if "rating_value" in storefront and "rating_count" in storefront:
        rating_value = f"{float(storefront['rating_value']):.1f}"
        rating_count = int(storefront["rating_count"])
        rating = (
            '<span aria-hidden="true"> · </span>'
            '<span class="app-rating">'
            '<span aria-hidden="true">★</span> '
            f'<data value="{rating_value}">{rating_value}</data>/5'
            '<span aria-hidden="true"> · </span>'
            f'<data value="{rating_count}">{rating_count}</data>'
            "</span>"
        )
    return (
        '<p class="app-store-proof"><span>App Store</span>'
        '<span aria-hidden="true"> · </span>'
        f'<data value="{e(str(storefront["price"]), quote=True)}">'
        f'{e(str(storefront["formatted_price"]))}</data>{rating}</p>'
    )


DIRECTORY_STYLE = """<style>
:root{color-scheme:light;--ink:#15211d;--muted:#5a6862;--line:#dce8e2;--paper:#fff;--mint:#e8f7f0;--teal:#116a56;--shadow:0 18px 54px rgba(21,70,57,.11);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
*{box-sizing:border-box}
body{margin:0;background:linear-gradient(180deg,#f2fbf7 0,#fff 36rem);color:var(--ink)}
main{width:min(96%,980px);margin:0 auto;padding:clamp(28px,5vw,64px) 0 72px}
h1{margin:0;font-size:clamp(2rem,6vw,4.4rem);letter-spacing:-.045em;line-height:1.02}
h1,.intro,.catalog-link,.finder-field,.no-match,.app-name,.app-sub,.app-price,.app-store-proof,.store-cta{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.intro{margin:16px 0 0;color:var(--muted);font-size:clamp(1rem,2vw,1.16rem)}
.catalog-link{margin:18px 0}.catalog-link a{color:var(--teal);font-weight:800}
.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
.finder-shell{margin:clamp(22px,4vw,34px) 0 18px;padding:8px;border:1px solid rgba(17,106,86,.2);border-radius:26px;background:rgba(255,255,255,.9);box-shadow:0 20px 58px rgba(21,70,57,.13);backdrop-filter:blur(18px)}
.finder-field{display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:center;gap:12px;min-height:58px;padding:0 16px;border-radius:19px;background:linear-gradient(135deg,#f8fffb,#edf9f3)}
.finder-icon{width:22px;height:22px;color:var(--teal)}
.finder-field input{min-width:0;width:100%;height:54px;padding:0;border:0;outline:0;background:transparent;color:var(--ink);font:inherit;font-size:1rem;font-weight:750;text-align:start}
.finder-field input::placeholder{color:#687771;opacity:1}
.finder-field input:focus-visible{border-radius:12px;box-shadow:0 0 0 3px rgba(125,92,255,.42)}
.finder-count{min-width:58px;color:var(--teal);font-size:.88rem;font-variant-numeric:tabular-nums;text-align:end}
.no-match{margin:0 0 18px;padding:14px 18px;border:1px solid #eadfd1;border-radius:18px;background:#fff9ef;color:#75532d;font-weight:750}
.app-list{display:grid;grid-template-columns:1fr;gap:12px;margin:0;padding:0;list-style:none}
.app-card{display:grid;grid-template-columns:72px minmax(0,1fr) auto;align-items:center;gap:clamp(14px,3vw,24px);min-height:132px;padding:clamp(16px,3vw,24px);border:1px solid var(--line);border-radius:24px;background:rgba(255,255,255,.94);box-shadow:var(--shadow)}
.app-icon{display:block;width:72px;height:72px;border:1px solid rgba(21,33,29,.08);border-radius:19px;object-fit:cover;box-shadow:0 10px 26px rgba(21,70,57,.14)}
.app-copy{min-width:0}.app-name{display:block;color:var(--ink);font-size:clamp(1.08rem,2.4vw,1.35rem);font-weight:900;text-decoration:none}.app-name:hover{text-decoration:underline}
.app-sub,.app-price,.app-store-proof{margin:7px 0 0;color:var(--muted)}.app-price{font-size:.92rem}.app-price strong{color:var(--ink)}.app-store-proof{color:#54458d;font-size:.82rem;font-weight:800;font-variant-numeric:tabular-nums}.app-store-proof data{color:inherit}
.store-cta{display:inline-flex;align-items:center;justify-content:center;max-width:42vw;min-height:48px;padding:0 20px;border-radius:999px;background:var(--teal);color:#fff;font-weight:900;text-decoration:none;box-shadow:0 10px 24px rgba(17,106,86,.22)}
.store-cta:focus-visible,.app-name:focus-visible{outline:3px solid #7d5cff;outline-offset:4px}
[hidden]{display:none!important}
@media(max-width:560px){main{width:min(94%,760px)}.finder-shell{border-radius:22px}.finder-field{gap:9px;padding:0 12px}.finder-count{min-width:50px}.app-card{grid-template-columns:58px minmax(0,1fr) auto;gap:12px;min-height:120px;border-radius:20px}.app-icon{width:58px;height:58px;border-radius:16px}.store-cta{max-width:32vw;padding:0 14px}.app-price{font-size:.84rem}.app-store-proof{font-size:.76rem}}
@media(max-width:380px){.app-card{grid-template-columns:48px minmax(0,1fr) auto;gap:9px;padding:14px 12px}.app-icon{width:48px;height:48px;border-radius:14px}.store-cta{min-height:44px;padding:0 11px}.finder-count{min-width:44px;font-size:.8rem}}
@media(prefers-reduced-motion:no-preference){.app-card,.store-cta{transition:transform .18s ease,box-shadow .18s ease}.app-card:hover{transform:translateY(-2px);box-shadow:0 22px 62px rgba(21,70,57,.15)}.store-cta:hover{transform:translateY(-1px)}}
</style>"""

DIRECTORY_SCRIPT = r"""<script>
(() => {
  const form = document.querySelector("[data-local-app-finder]");
  const input = document.getElementById("app-search");
  const list = document.getElementById("app-list");
  const status = document.getElementById("app-search-status");
  const noMatch = document.getElementById("no-app-match");
  if (!form || !input || !list || !status || !noMatch) return;

  const locale = document.documentElement.lang;
  const cards = Array.from(list.querySelectorAll(".app-card"));
  const substitutions = new Map([
    ["ß", "ss"], ["ς", "σ"], ["æ", "ae"], ["œ", "oe"],
    ["ø", "o"], ["ł", "l"], ["đ", "d"], ["ð", "d"], ["þ", "th"]
  ]);
  const fold = value => {
    let result = String(value)
      .toLocaleLowerCase(locale)
      .normalize("NFKD")
      .replace(/[\u0300-\u036f\u0591-\u05c7\u0640\u064b-\u065f\u0670]/g, "");
    substitutions.forEach((replacement, source) => {
      result = result.split(source).join(replacement);
    });
    return result.replace(/[^\p{L}\p{N}]+/gu, " ").trim();
  };
  const index = new Map(cards.map(card => [card, fold(card.dataset.search)]));

  const score = (text, query) => {
    if (!query) return 0;
    const phrase = text.indexOf(query);
    if (phrase >= 0) return 10000 - Math.min(phrase, 999);
    const tokens = [...new Set(query.split(" ").filter(Boolean))];
    let total = 0;
    for (const token of tokens) {
      const position = text.indexOf(token);
      if (position < 0) return -1;
      total += 100 - Math.min(position, 99);
    }
    return total;
  };

  const render = updateURL => {
    const raw = input.value.trim().slice(0, input.maxLength);
    const query = fold(raw);
    const ranked = cards.map((card, order) => ({
      card,
      order,
      score: score(index.get(card), query)
    }));
    ranked.sort((left, right) => {
      const leftVisible = left.score >= 0;
      const rightVisible = right.score >= 0;
      if (leftVisible !== rightVisible) return leftVisible ? -1 : 1;
      if (leftVisible && left.score !== right.score) return right.score - left.score;
      return left.order - right.order;
    });
    let shown = 0;
    ranked.forEach(item => {
      item.card.hidden = item.score < 0;
      if (!item.card.hidden) shown += 1;
      list.appendChild(item.card);
    });
    status.textContent = `${shown} / ${cards.length}`;
    noMatch.hidden = shown !== 0;
    if (updateURL) {
      const url = new URL(window.location.href);
      if (query) url.searchParams.set("q", raw);
      else url.searchParams.delete("q");
      window.history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
    }
  };

  const initial = new URL(window.location.href).searchParams.get("q") || "";
  input.value = initial.slice(0, input.maxLength);
  form.addEventListener("submit", event => {
    event.preventDefault();
    render(true);
  });
  input.addEventListener("input", () => render(true));
  render(false);
  form.hidden = false;
})();
</script>"""


# 各語系首頁通往內容區的導覽。在此之前 answers / tools / alternatives 等
# 兩萬多頁只出現在 sitemap,從首頁完全點不到 —— 搜尋引擎對這種「孤兒頁」
# 會大幅降權,這正是站台頁數龐大卻幾乎沒有自然流量的結構性原因。
SECTION_NAV_LABELS = {
    "answers": {
        "en": "Answers", "zh-Hant": "問題解答", "zh-Hans": "问题解答",
        "ja": "回答", "ko": "답변", "de": "Antworten", "fr": "Réponses",
        "es": "Respuestas", "pt": "Respostas", "it": "Risposte",
        "ru": "Ответы", "ar": "إجابات", "th": "คำตอบ", "vi": "Giải đáp",
        "id": "Jawaban", "ms": "Jawapan", "tr": "Yanıtlar", "pl": "Odpowiedzi",
    },
    "tools": {
        "en": "Free tools", "zh-Hant": "免費工具", "zh-Hans": "免费工具",
        "ja": "無料ツール", "ko": "무료 도구", "de": "Kostenlose Tools",
        "fr": "Outils gratuits", "es": "Herramientas gratis",
        "pt": "Ferramentas gratuitas", "it": "Strumenti gratuiti",
        "ru": "Бесплатные инструменты", "ar": "أدوات مجانية",
        "th": "เครื่องมือฟรี", "vi": "Công cụ miễn phí",
        "id": "Alat gratis", "ms": "Alat percuma", "tr": "Ücretsiz araçlar",
        "pl": "Darmowe narzędzia",
    },
    "alternatives": {
        "en": "Alternatives", "zh-Hant": "替代方案", "zh-Hans": "替代方案",
        "ja": "代替アプリ", "ko": "대안 앱", "de": "Alternativen",
        "fr": "Alternatives", "es": "Alternativas", "pt": "Alternativas",
        "it": "Alternative", "ru": "Альтернативы", "ar": "بدائل",
        "th": "ทางเลือก", "vi": "Lựa chọn thay thế", "id": "Alternatif",
        "ms": "Alternatif", "tr": "Alternatifler", "pl": "Alternatywy",
    },
}


def locale_section_nav(locale):
    """只連該語系實際存在的區塊索引,避免產生 404。"""
    e = html.escape
    lang = base_lang(locale)
    items = []
    for section, labels in SECTION_NAV_LABELS.items():
        if not os.path.exists(os.path.join(PAGES, locale, section, "index.html")):
            continue
        label = labels.get(locale) or labels.get(lang) or labels["en"]
        items.append(
            f'      <li><a href="{SITE}/{locale}/{section}/index.html">'
            f'{e(label)}</a></li>'
        )
    if not items:
        return ""
    rows = "\n".join(items)
    return (
        '  <nav class="section-nav" aria-label="Sections">\n'
        f'    <ul>\n{rows}\n    </ul>\n'
        '  </nav>\n'
    )


def build_locale_index(locale, keys, locales):
    ui = get_ui(locale)
    finder_ui = get_finder_ui(locale)
    e = html.escape
    is_rtl = base_lang(locale) in RTL
    records = localized_directory_records(locale, keys)
    rows = [
        (
            f'    <li class="app-card" data-app-id="{e(record["app_id"])}" '
            f'data-search="{e(record["search_text"], quote=True)}">'
            f'<img class="app-icon" src="{e(record["icon_url"], quote=True)}" '
            f'alt="" width="72" height="72" loading="lazy" decoding="async">'
            '<div class="app-copy">'
            f'<a class="app-name" href="{e(record["key"])}.html">'
            f'{e(record["name"])}</a>'
            f'<p class="app-sub">{e(record["subtitle"])}</p>'
            f'<p class="app-price"><strong>{e(ui["price"])}:</strong> '
            f'{e(record["pricing"])}</p>'
            f'{localized_directory_storefront_proof(record)}</div>'
            f'<a class="store-cta" href="{e(record["store_url"])}" '
            'referrerpolicy="no-referrer" '
            f'aria-label="{e(ui["get"].format(name=record["name"]))}">'
            f'{e(ui["dl"])}</a></li>'
        )
        for record in records
    ]
    items = "\n".join(rows)
    dir_attr = ' dir="rtl"' if is_rtl else ""
    schema = json_for_script(
        localized_directory_schema(locale, records),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    catalog_path = PORTFOLIO_CATALOG_PATHS.get(locale)
    catalog_link = (
        f'  <p class="catalog-link"><a href="{SITE}/{catalog_path}">'
        f'{e(ui["catalog"])}</a></p>\n'
        if catalog_path
        else ""
    )
    idx = f"""<!DOCTYPE html>
<html lang="{locale}"{dir_attr}><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(ui["dir_dir"])} | iOS</title>
<meta name="description" content="{e(ui["dir_lead"])}">
<link rel="canonical" href="{SITE}/{locale}/index.html">
{feed_discovery_links()}
{directory_hreflang_block(locales)}
<script type="application/ld+json" data-iag="localized-install-directory">{schema}</script>
{DIRECTORY_STYLE}
</head><body><main>
  <h1>{e(ui["dir_dir"])}</h1>
  <p class="intro">{e(ui["dir_lead"])}</p>
{catalog_link}{locale_section_nav(locale)}  <form class="finder-shell" role="search" data-local-app-finder hidden>
    <label class="sr-only" for="app-search">{e(finder_ui["find"])}</label>
    <div class="finder-field">
      <svg class="finder-icon" viewBox="0 0 24 24" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-linecap="round" stroke-width="2.2" d="m20 20-4.4-4.4m2.4-5.1a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0Z"/></svg>
      <input id="app-search" name="q" type="search" maxlength="120" autocomplete="off" enterkeyhint="search" placeholder="{e(finder_ui["find"], quote=True)}" aria-controls="app-list" aria-describedby="app-search-status no-app-match">
      <output class="finder-count" id="app-search-status" for="app-search" aria-live="polite" aria-atomic="true" dir="ltr">{len(records)} / {len(records)}</output>
    </div>
  </form>
  <p class="no-match" id="no-app-match" role="status" hidden>{e(finder_ui["no_match"])}</p>
  <ul class="app-list" id="app-list">
{items}
  </ul>
</main>{DIRECTORY_SCRIPT}</body></html>
"""
    outdir = os.path.join(PAGES, locale)
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8") as f:
        f.write(idx)


def build_root_index(locales):
    e = html.escape
    lang_links = "\n".join(
        f'    <li><a href="{lc}/index.html" hreflang="{lc}">{lc}</a></li>' for lc in locales)
    idx = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>iOS Apps — multilingual directory</title>
<meta name="description" content="Multilingual directory of iOS apps with features, pricing and FAQs in {len(locales)} languages.">
<link rel="canonical" href="{SITE}/index.html">
{directory_hreflang_block(locales)}
</head><body><main>
  <h1>iOS Apps — choose your language</h1>
  <p><a href="{SITE}/apps/index.html">Browse all verified apps by category</a></p>
  <nav aria-label="Sections">
    <ul>
      <li><a href="{SITE}/answers/index.html">Answers — buying guides by question</a></li>
      <li><a href="{SITE}/hubs/index.html">Topic hubs</a></li>
      <li><a href="{SITE}/tools/index.html">Free browser tools</a></li>
      <li><a href="{SITE}/alternatives/index.html">App alternatives</a></li>
      <li><a href="{SITE}/about.html">About this site</a></li>
    </ul>
  </nav>
  <ul>
{lang_links}
  </ul>
</main></body></html>
"""
    os.makedirs(PAGES, exist_ok=True)
    with open(os.path.join(PAGES, "index.html"), "w", encoding="utf-8") as f:
        f.write(idx)


def build_sitemap(keys, locales):
    """多語 sitemap:每個 URL 附 hreflang alternates(爬蟲/LLM 發現全部頁面)。"""
    def alts(maker, available_locales):
        default_locale = (
            "en-US" if "en-US" in available_locales else available_locales[0]
        )
        return "".join(
            f'    <xhtml:link rel="alternate" hreflang="{lc}" href="{maker(lc)}"/>\n'
            for lc in available_locales
        ) + (
            f'    <xhtml:link rel="alternate" hreflang="x-default" '
            f'href="{maker(default_locale)}"/>\n'
        )
    urls = []
    # 根中樞
    urls.append(f"  <url><loc>{SITE}/index.html</loc></url>")
    # 各語 index
    for lc in locales:
        urls.append(
            f"  <url>\n    <loc>{SITE}/{lc}/index.html</loc>\n"
            f'{alts(lambda x: f"{SITE}/{x}/index.html", locales)}  </url>')
    # 各 app 各語
    for k in keys:
        app_locales = [
            lc
            for lc in locales
            if os.path.exists(os.path.join(PAGES, lc, f"{k}.html"))
        ]
        for lc in app_locales:
            urls.append(
                f"  <url>\n    <loc>{SITE}/{lc}/{k}.html</loc>\n"
                f'{alts(lambda x, kk=k: f"{SITE}/{x}/{kk}.html", app_locales)}'
                "  </url>"
            )
    body = "\n".join(urls)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
           'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
           f"{body}\n</urlset>\n")
    with open(os.path.join(PAGES, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(xml)
    return len(urls)


def build_robots():
    # 明確歡迎各大 AI/搜尋爬蟲(GEO/AEO 核心)+ 列出全部 sitemap + 指向 llms.txt。
    ai_bots = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "anthropic-ai",
               "Claude-Web", "PerplexityBot", "Perplexity-User", "Google-Extended",
               "Googlebot", "Bingbot", "Applebot", "Applebot-Extended", "CCBot",
               "Amazonbot", "Bytespider", "Meta-ExternalAgent", "DuckDuckBot",
               "cohere-ai", "YandexBot", "PetalBot"]
    out = ["# AI assistants and search crawlers are welcome to index and cite this site.",
           f"# AI index: {SITE}/llms.txt", ""]
    for bot in ai_bots:
        out += [f"User-agent: {bot}", "Allow: /", ""]
    out += ["User-agent: *", "Allow: /", ""]
    for sm in ("sitemap.xml", "sitemap_alternatives.xml", "sitemap_answers.xml",
               "sitemap_guides.xml", "sitemap_stories.xml", "sitemap_images.xml",
               "sitemap_linkset.xml", "sitemap_oembed.xml", "sitemap_hubs.xml",
               "sitemap_tools.xml", "sitemap_apps.xml", "sitemap_index.xml"):
        out.append(f"Sitemap: {SITE}/{sm}")
    txt = "\n".join(out) + "\n"
    with open(os.path.join(PAGES, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    # .nojekyll:GitHub Pages 原樣提供所有檔案(不跑 Jekyll)
    open(os.path.join(PAGES, ".nojekyll"), "w").close()


def all_locales_for(key):
    locales = load_app_locales(key)
    require_official_locale_coverage(key, locales)
    return [locale for locale in OFFICIAL_LOCALES if locale in locales]


def master_locales_for(keys):
    for key in keys:
        all_locales_for(key)
    return list(OFFICIAL_LOCALES)


if __name__ == "__main__":
    cached_live = "--cached-live" in sys.argv[1:]
    args = [x for x in sys.argv[1:] if x != "--cached-live"]
    requested_keys = [a for a in args if a in APPS]
    want_locales = [a for a in args if a not in APPS]
    public_keys = live_app_keys(
        APPSTORE, PAGES, refresh=not cached_live
    )
    available_keys = [key for key in APPS if key in public_keys]
    keys = [key for key in requested_keys if key in available_keys] or (
        available_keys if not requested_keys else []
    )
    if not keys:
        raise SystemExit("No publicly available app pages matched the request.")

    master_locales = master_locales_for(keys)
    locales = [lc for lc in master_locales if (not want_locales or lc in want_locales)]

    n = 0
    for k in keys:
        app_locales = sorted(all_locales_for(k) or ["en-US"])
        use = [lc for lc in app_locales if (not want_locales or lc in want_locales)]
        for lc in use:
            build_one(k, lc, app_locales)
            n += 1
        # 每語 index 只在做全部 app 時重建
    if set(keys) == set(available_keys):
        public_page_keys = [key for key in APPS if key in public_keys]
        for lc in locales:
            locale_keys = [
                key
                for key in public_page_keys
                if os.path.exists(os.path.join(PAGES, lc, f"{key}.html"))
            ]
            build_locale_index(lc, locale_keys, locales)
        build_root_index(locales)
        nurls = build_sitemap(public_page_keys, locales)
        build_robots()
        print(
            f"✅ 多語 GEO:{len(available_keys)} app = {n} 頁 + "
            f"{len(locales)} 語 index + 根中樞"
        )
        print(f"   sitemap.xml({nurls} URLs)+ robots.txt + .nojekyll 已產出")
    else:
        print(f"✅ 產出 {n} 頁({len(keys)} app)。(未重建 index — 非全量)")
    print(f"   部署網域(GEO_SITE 可覆寫): {SITE}")
    print(f"   輸出: geo/pages/<locale>/<key>.html")
