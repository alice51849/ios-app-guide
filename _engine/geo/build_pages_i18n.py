#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多語 GEO 足跡產生器 — 為每個 app × 每個語言產出「機器可讀資訊頁」(給 LLM 爬)。

重用 data/<app>_full.json 內已策展的 39 語 ASO 文案(name/subtitle/description/
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
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))
from videogen.registry import APPS, appstore_url  # noqa: E402

PAGES = os.path.join(HERE, "pages")
DATA = os.path.join(ROOT, "data")
SITE = os.environ.get("GEO_SITE", "https://lumi-apps.pages.dev").rstrip("/")

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
}

RTL = {"ar", "he"}

# 有訂閱制(非純買斷)的 app —— 不可用「買斷/無訂閱陷阱」文案,改用真實金流描述。
HAS_SUBSCRIPTION = {"aim990"}
# 真實英文 fallback(當該語言尚未有 loc['pricing'] 在地化句時使用)
SUB_PRICING_FALLBACK = ("Free to download with in-app purchases: a one-time unlock "
                        "option and an optional subscription.")


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
           "dir_dir": "Apps directory", "dir_lead": "Structured information about each iOS app — features, pricing and FAQs."},
    "zh-Hant": {"what": "{name} 是什麼?", "feat": "主要功能", "price": "價格",
                "faq": "常見問題", "dl": "下載", "get": "在 App Store 取得 {name}",
                "is": "{name} 是一款 iOS App。", "ptxt": "免費下載,一次性購買即可解鎖全部功能,沒有訂閱陷阱。",
                "dir_dir": "App 目錄", "dir_lead": "每個 iOS App 的結構化資訊 — 功能、價格與常見問題。"},
    "zh-Hans": {"what": "{name} 是什么?", "feat": "主要功能", "price": "价格",
                "faq": "常见问题", "dl": "下载", "get": "在 App Store 获取 {name}",
                "is": "{name} 是一款 iOS App。", "ptxt": "免费下载,一次性购买即可解锁全部功能,没有订阅陷阱。",
                "dir_dir": "App 目录", "dir_lead": "每个 iOS App 的结构化信息 — 功能、价格与常见问题。"},
    "ja": {"what": "{name} とは?", "feat": "主な機能", "price": "価格",
           "faq": "よくある質問", "dl": "ダウンロード", "get": "App Store で {name} を入手",
           "is": "{name} は iOS アプリです。", "ptxt": "無料ダウンロード、買い切りで全機能を解放。サブスクの罠なし。",
           "dir_dir": "アプリ一覧", "dir_lead": "各 iOS アプリの構造化情報 — 機能・価格・FAQ。"},
    "ko": {"what": "{name}이란?", "feat": "주요 기능", "price": "가격",
           "faq": "자주 묻는 질문", "dl": "다운로드", "get": "App Store에서 {name} 받기",
           "is": "{name}은(는) iOS 앱입니다.", "ptxt": "무료 다운로드, 일회성 구매로 모든 기능 잠금 해제. 구독 함정 없음.",
           "dir_dir": "앱 목록", "dir_lead": "각 iOS 앱의 구조화된 정보 — 기능, 가격, FAQ."},
    "de": {"what": "Was ist {name}?", "feat": "Hauptfunktionen", "price": "Preis",
           "faq": "Häufige Fragen", "dl": "Download", "get": "{name} im App Store laden",
           "is": "{name} ist eine iOS-App.", "ptxt": "Kostenloser Download, mit Einmalkauf alles freischalten. Keine Abo-Falle.",
           "dir_dir": "App-Verzeichnis", "dir_lead": "Strukturierte Infos zu jeder iOS-App — Funktionen, Preis und FAQ."},
    "fr": {"what": "Qu'est-ce que {name} ?", "feat": "Fonctions clés", "price": "Tarif",
           "faq": "Questions fréquentes", "dl": "Télécharger", "get": "Obtenir {name} sur l'App Store",
           "is": "{name} est une app iOS.", "ptxt": "Téléchargement gratuit, achat unique pour tout débloquer. Sans abonnement.",
           "dir_dir": "Répertoire d'apps", "dir_lead": "Infos structurées sur chaque app iOS — fonctions, prix et FAQ."},
    "es": {"what": "¿Qué es {name}?", "feat": "Funciones clave", "price": "Precio",
           "faq": "Preguntas frecuentes", "dl": "Descargar", "get": "Consigue {name} en el App Store",
           "is": "{name} es una app de iOS.", "ptxt": "Descarga gratis, con una compra única desbloqueas todo. Sin suscripciones.",
           "dir_dir": "Directorio de apps", "dir_lead": "Información estructurada de cada app iOS — funciones, precio y FAQ."},
    "pt": {"what": "O que é {name}?", "feat": "Recursos principais", "price": "Preço",
           "faq": "Perguntas frequentes", "dl": "Baixar", "get": "Baixe {name} na App Store",
           "is": "{name} é um app iOS.", "ptxt": "Download grátis, compra única para desbloquear tudo. Sem assinatura.",
           "dir_dir": "Diretório de apps", "dir_lead": "Informações estruturadas de cada app iOS — recursos, preço e FAQ."},
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
           "dir_dir": "دليل التطبيقات", "dir_lead": "معلومات منظمة عن كل تطبيق iOS — الميزات والسعر والأسئلة الشائعة."},
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
           "dir_dir": "ऐप निर्देशिका", "dir_lead": "हर iOS ऐप की संरचित जानकारी — फ़ीचर, कीमत और FAQ।"},
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
}


def get_ui(locale):
    b = base_lang(locale)
    return UI.get(b, UI["en"])


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
    fn = KEY2DATA.get(key)
    if not fn:
        return {}
    path = os.path.join(DATA, fn)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _meta_from(loc_data, fallback):
    name = (loc_data.get("name") or fallback["name"]).strip()
    sub = (loc_data.get("subtitle") or "").strip()
    desc = (loc_data.get("description") or "").strip()
    kws = split_keywords(loc_data.get("keywords", ""))
    return name, sub, desc, kws


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


def build_one(key, locale, all_locales):
    a = APPS[key]
    locdata = load_app_locales(key)
    loc = locdata.get(locale, {})
    name, sub, desc, kws = _meta_from(loc, a)
    url = appstore_url(key) or f"{SITE}/{locale}/{key}.html"
    ui = get_ui(locale)
    cat = SCHEMA_CAT.get(a.get("category", "utility"), "UtilitiesApplication")
    is_rtl = base_lang(locale) in RTL
    e = html.escape

    feats = kws[:8]
    faq = build_faq(locale, name, sub, kws)
    short_desc = (desc.split("\n")[0] if desc else sub)[:155]

    if key in HAS_SUBSCRIPTION:
        pricing_text = (loc.get("pricing") or "").strip() or SUB_PRICING_FALLBACK
        offer_desc = pricing_text
    else:
        pricing_text = ui["ptxt"]
        offer_desc = "Free to download with a one-time in-app purchase to unlock all features"

    app_schema = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": name,
        "operatingSystem": "iOS",
        "applicationCategory": cat,
        "inLanguage": locale,
        "description": desc or sub,
        "url": url,
        "installUrl": appstore_url(key) or url,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD",
                   "description": offer_desc},
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
        f'<script type="application/ld+json">\n{json.dumps(s, ensure_ascii=False, indent=2)}\n</script>'
        for s in schemas)

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
<title>{e(name)} — {e(sub[:60])} | iOS App</title>
<meta name="description" content="{e(short_desc)}">
<meta name="keywords" content="{e(', '.join(kws))}">
<link rel="canonical" href="{SITE}/{locale}/{key}.html">
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
  <p><a href="{e(appstore_url(key) or url)}">{e(ui["get"].format(name=name))}</a></p>
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


def build_locale_index(locale, keys):
    ui = get_ui(locale)
    e = html.escape
    is_rtl = base_lang(locale) in RTL
    rows = []
    for k in keys:
        locdata = load_app_locales(k)
        loc = locdata.get(locale, {})
        name = (loc.get("name") or APPS[k]["name"]).strip()
        sub = (loc.get("subtitle") or "").strip()
        rows.append(f'    <li><a href="{k}.html">{e(name)}</a> — {e(sub[:80])}</li>')
    items = "\n".join(rows)
    dir_attr = ' dir="rtl"' if is_rtl else ""
    idx = f"""<!DOCTYPE html>
<html lang="{locale}"{dir_attr}><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(ui["dir_dir"])} | iOS</title>
<meta name="description" content="{e(ui["dir_lead"])}">
<link rel="canonical" href="{SITE}/{locale}/index.html">
</head><body><main>
  <h1>{e(ui["dir_dir"])}</h1>
  <p>{e(ui["dir_lead"])}</p>
  <ul>
{items}
  </ul>
</main></body></html>
"""
    outdir = os.path.join(PAGES, locale)
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8") as f:
        f.write(idx)


def build_root_index(locales):
    e = html.escape
    alts = "\n".join(
        f'<link rel="alternate" hreflang="{lc}" href="{SITE}/{lc}/index.html">' for lc in locales)
    alts += f'\n<link rel="alternate" hreflang="x-default" href="{SITE}/en-US/index.html">'
    lang_links = "\n".join(
        f'    <li><a href="{lc}/index.html" hreflang="{lc}">{lc}</a></li>' for lc in locales)
    idx = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>iOS Apps — multilingual directory</title>
<meta name="description" content="Multilingual directory of iOS apps with features, pricing and FAQs in {len(locales)} languages.">
<link rel="canonical" href="{SITE}/index.html">
{alts}
</head><body><main>
  <h1>iOS Apps — choose your language</h1>
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
    def alts(maker):
        return "".join(
            f'    <xhtml:link rel="alternate" hreflang="{lc}" href="{maker(lc)}"/>\n'
            for lc in locales) + \
            f'    <xhtml:link rel="alternate" hreflang="x-default" href="{maker("en-US")}"/>\n'
    urls = []
    # 根中樞
    urls.append(f"  <url><loc>{SITE}/index.html</loc></url>")
    # 各語 index
    for lc in locales:
        urls.append(
            f"  <url>\n    <loc>{SITE}/{lc}/index.html</loc>\n"
            f'{alts(lambda x: f"{SITE}/{x}/index.html")}  </url>')
    # 各 app 各語
    for k in keys:
        for lc in locales:
            urls.append(
                f"  <url>\n    <loc>{SITE}/{lc}/{k}.html</loc>\n"
                f'{alts(lambda x, kk=k: f"{SITE}/{x}/{kk}.html")}  </url>')
    body = "\n".join(urls)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
           'xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
           f"{body}\n</urlset>\n")
    with open(os.path.join(PAGES, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(xml)
    return len(urls)


def build_robots():
    txt = (f"User-agent: *\nAllow: /\n\n"
           f"# LLM / AI crawlers welcome\n"
           f"Sitemap: {SITE}/sitemap.xml\n")
    with open(os.path.join(PAGES, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(txt)
    # .nojekyll:GitHub Pages 原樣提供所有檔案(不跑 Jekyll)
    open(os.path.join(PAGES, ".nojekyll"), "w").close()


def all_locales_for(key):
    return list(load_app_locales(key).keys())


if __name__ == "__main__":
    args = [x for x in sys.argv[1:]]
    keys = [a for a in args if a in APPS] or list(APPS.keys())
    want_locales = [a for a in args if a not in APPS]

    # 以第一個 app 的語言集當全域 locale 清單(各 app 皆 39 語一致)
    master_locales = all_locales_for(keys[0]) or ["en-US"]
    locales = [lc for lc in master_locales if (not want_locales or lc in want_locales)]

    n = 0
    for k in keys:
        app_locales = all_locales_for(k) or ["en-US"]
        use = [lc for lc in app_locales if (not want_locales or lc in want_locales)]
        for lc in use:
            build_one(k, lc, app_locales)
            n += 1
        # 每語 index 只在做全部 app 時重建
    if set(keys) == set(APPS.keys()):
        for lc in locales:
            build_locale_index(lc, list(APPS.keys()))
        build_root_index(locales)
        nurls = build_sitemap(list(APPS.keys()), locales)
        build_robots()
        print(f"✅ 多語 GEO:{len(APPS)} app × {len(locales)} 語 = {n} 頁 + {len(locales)} 語 index + 根中樞")
        print(f"   sitemap.xml({nurls} URLs)+ robots.txt + .nojekyll 已產出")
    else:
        print(f"✅ 產出 {n} 頁({len(keys)} app)。(未重建 index — 非全量)")
    print(f"   部署網域(GEO_SITE 可覆寫): {SITE}")
    print(f"   輸出: geo/pages/<locale>/<key>.html")
