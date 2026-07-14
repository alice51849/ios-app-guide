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
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))
from videogen.registry import APPS, APPSTORE, appstore_url  # noqa: E402
from aeo_pages import pricing_profile  # noqa: E402
from appstore_live import live_app_keys  # noqa: E402
from external_app_locales import EXTERNAL_APP_LOCALES  # noqa: E402
from gen_feed import feed_discovery_links  # noqa: E402

PAGES = os.path.join(HERE, "pages")
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

RTL = {"ar", "he"}

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
           "is": "{name} は iOS アプリです。", "ptxt": "無料ダウンロード。1回限りの購入で全機能を永久に解除でき、定期課金はありません。",
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
        "flexible": "Descàrrega gratuïta amb compres dins de l’app: tria un desbloqueig únic o una subscripció opcional.",
    },
    "hr": {
        "flexible": "Besplatno preuzimanje uz kupnje unutar aplikacije: odaberite jednokratno otključavanje ili opcionalnu pretplatu.",
    },
    "da": {
        "flexible": "Gratis download med køb i appen: vælg en engangsoplåsning eller et valgfrit abonnement.",
    },
    "no": {
        "flexible": "Gratis nedlasting med kjøp i appen: velg engangsopplåsing eller et valgfritt abonnement.",
    },
    "ro": {
        "flexible": "Descărcare gratuită cu achiziții în aplicație: alege o deblocare unică sau un abonament opțional.",
    },
    "sk": {
        "flexible": "Bezplatné stiahnutie s nákupmi v aplikácii: vyberte si jednorazové odomknutie alebo voliteľné predplatné.",
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


def sanitize_description(key, locale, description):
    if not description:
        return description
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
    fn = KEY2DATA.get(key)
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
    loc = locdata.get(locale, {})
    name, sub, desc, kws = _meta_from(loc, a)
    desc = sanitize_description(key, locale, desc)
    url = appstore_url(key, "iag_lp") or f"{SITE}/{locale}/{key}.html"
    ui = get_ui(locale)
    cat = SCHEMA_CAT.get(a.get("category", "utility"), "UtilitiesApplication")
    is_rtl = base_lang(locale) in RTL
    e = html.escape

    feats = kws[:8]
    faq = build_faq(locale, name, sub, kws)
    short_desc = (desc.split("\n")[0] if desc else sub)[:155]

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


def build_locale_index(locale, keys, locales):
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
{feed_discovery_links()}
{directory_hreflang_block(locales)}
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
    return list(load_app_locales(key).keys()) or ["en-US"]


def master_locales_for(keys):
    return sorted(
        {
            locale
            for key in keys
            for locale in all_locales_for(key)
        }
    ) or ["en-US"]


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
