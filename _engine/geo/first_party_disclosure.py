#!/usr/bin/env python3
"""Say who runs the site before the first recommendation, on every page.

Why: the Guide and the support sites recommend only Lumi Studio's own apps.
Japan's stealth-marketing rules (消費者庁「ステルスマーケティング」運用基準)
treat a business's own site that reads like an objective third-party review as
undisclosed advertising, and the US FTC consumer-review rule (16 CFR 465, in
force since 2024-10) bans company-controlled review sites presented as
independent. A footer line is not enough; the reader has to see who is talking
before the first recommendation.

What it does, idempotently, to each promotional page (one that links to the
App Store or Google Play):

* inserts one short, localized ``<p data-first-party-disclosure="banner">``
  line between the site header and ``<main>`` (or right after ``<body>``), so
  it is the first thing read and sits outside the answer-first ``<main>``;
* names the developer as publisher in structured data: the site
  ``#organization`` node becomes Lumi Studio, and a page with no publisher or
  author at all gets a ``#website`` node published by Lumi Studio;
* replaces the legacy "Is this page independent? Yes." FAQ answer and the
  legacy "Independent comparison." line with truthful localized copy.

Pages another generator pins byte for byte (hero tasks, high-intent decision
routes) are left to their owners; they already carry their own first-party
disclosure. AMP stories and redirect stubs are skipped. App claims, prices,
store copy and download links are never touched.

Usage: ``python3 first_party_disclosure.py --pages <site root> [--check]``.
"""

from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
import re
import sys
from types import MappingProxyType
from typing import Iterable, Mapping

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from official_locales import OFFICIAL_LOCALES  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402

PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
DEVELOPER = "Lumi Studio"
ABOUT_URL = f"{PUBLIC_SITE}/about.html"
ORGANIZATION_ID = f"{PUBLIC_SITE}/#organization"
WEBSITE_ID = f"{PUBLIC_SITE}/#website"
MARKER = "data-first-party-disclosure"
EXCLUDED_PARTS = frozenset({".git", ".github", "_engine", "node_modules"})
OWNED_SECTIONS = frozenset({"data", "api"})
# Generators that pin each output page by digest; their pages are theirs byte
# for byte and already open with their own first-party disclosure.
DIGEST_PINNED_MANIFESTS = (
    ("data/hero-tasks/manifest.json", "outputs"),
    ("data/high-intent-decision-routes/expected-output-manifest.json", "route_html"),
)

# One line, before the first recommendation. ja follows the 消費者庁 guidance
# wording (事業者自身の表示であることが明瞭に分かる表示).
BANNER = MappingProxyType({
    "en-US": "This site is run by Lumi Studio, the developer of the featured apps. The apps recommended here are our own.",
    "en-GB": "This site is run by Lumi Studio, the developer of the featured apps. The apps recommended here are our own.",
    "en-AU": "This site is run by Lumi Studio, the developer of the featured apps. The apps recommended here are our own.",
    "en-CA": "This site is run by Lumi Studio, the developer of the featured apps. The apps recommended here are our own.",
    "ja": "当サイトは掲載アプリの開発者であるLumi Studioが運営し、自社アプリを紹介しています。",
    "zh-Hant": "本站由這些 App 的開發者 Lumi Studio 營運，介紹的是我們自己的 App。",
    "zh-Hans": "本站由这些 App 的开发者 Lumi Studio 运营，介绍的是我们自己的 App。",
    "ko": "이 사이트는 소개된 앱의 개발사인 Lumi Studio가 운영하며, 여기서 추천하는 앱은 모두 자사 앱입니다.",
    "de-DE": "Diese Website wird von Lumi Studio betrieben, dem Entwickler der vorgestellten Apps. Die hier empfohlenen Apps sind unsere eigenen.",
    "fr-FR": "Ce site est géré par Lumi Studio, le développeur des apps présentées. Les apps recommandées ici sont les nôtres.",
    "fr-CA": "Ce site est exploité par Lumi Studio, le développeur des applications présentées. Les applications recommandées ici sont les nôtres.",
    "es-ES": "Este sitio lo gestiona Lumi Studio, el desarrollador de las apps que aparecen. Las apps que recomendamos aquí son nuestras.",
    "es-MX": "Este sitio lo opera Lumi Studio, el desarrollador de las apps que se presentan. Las apps que recomendamos aquí son nuestras.",
    "pt-BR": "Este site é mantido pela Lumi Studio, desenvolvedora dos apps apresentados. Os apps recomendados aqui são nossos.",
    "pt-PT": "Este site é gerido pela Lumi Studio, que desenvolve as apps apresentadas. As apps aqui recomendadas são nossas.",
    "it": "Questo sito è gestito da Lumi Studio, lo sviluppatore delle app presentate. Le app consigliate qui sono le nostre.",
    "nl-NL": "Deze site wordt beheerd door Lumi Studio, de ontwikkelaar van de getoonde apps. De apps die we hier aanbevelen, zijn van onszelf.",
    "sv": "Den här webbplatsen drivs av Lumi Studio, utvecklaren av apparna som presenteras. Apparna vi rekommenderar här är våra egna.",
    "da": "Dette websted drives af Lumi Studio, udvikleren af de viste apps. De apps, vi anbefaler her, er vores egne.",
    "no": "Dette nettstedet drives av Lumi Studio, utvikleren av appene som presenteres. Appene vi anbefaler her, er våre egne.",
    "fi": "Tätä sivustoa ylläpitää Lumi Studio, esiteltyjen sovellusten kehittäjä. Täällä suosittelemamme sovellukset ovat omiamme.",
    "pl": "Tę stronę prowadzi Lumi Studio – twórca prezentowanych aplikacji. Polecane tutaj aplikacje są nasze.",
    "cs": "Tento web provozuje Lumi Studio, vývojář představených aplikací. Aplikace, které zde doporučujeme, jsou naše vlastní.",
    "sk": "Túto stránku prevádzkuje Lumi Studio, vývojár predstavených aplikácií. Aplikácie, ktoré tu odporúčame, sú naše vlastné.",
    "sl-SI": "To spletno mesto upravlja Lumi Studio, razvijalec predstavljenih aplikacij. Aplikacije, ki jih priporočamo tukaj, so naše.",
    "hr": "Ovu stranicu vodi Lumi Studio, razvojni programer predstavljenih aplikacija. Aplikacije koje ovdje preporučujemo naše su vlastite.",
    "hu": "Ezt az oldalt a Lumi Studio, a bemutatott alkalmazások fejlesztője üzemelteti. Az itt ajánlott alkalmazások a sajátjaink.",
    "ro": "Acest site este administrat de Lumi Studio, dezvoltatorul aplicațiilor prezentate. Aplicațiile recomandate aici sunt ale noastre.",
    "ru": "Этот сайт ведёт Lumi Studio — разработчик представленных приложений. Приложения, которые мы здесь рекомендуем, — наши собственные.",
    "uk": "Цей сайт веде Lumi Studio — розробник представлених застосунків. Застосунки, які ми тут рекомендуємо, — наші власні.",
    "el": "Τον ιστότοπο διαχειρίζεται η Lumi Studio, η δημιουργός των εφαρμογών που παρουσιάζονται. Οι εφαρμογές που προτείνουμε εδώ είναι δικές μας.",
    "tr": "Bu site, tanıtılan uygulamaların geliştiricisi Lumi Studio tarafından işletilmektedir. Burada önerdiğimiz uygulamalar kendi uygulamalarımızdır.",
    "ar-SA": "يدير هذا الموقع Lumi Studio، مطوّر التطبيقات المعروضة، والتطبيقات التي نوصي بها هنا هي تطبيقاتنا.",
    "he": "האתר מופעל על ידי Lumi Studio, המפתחת של האפליקציות המוצגות. האפליקציות שאנחנו ממליצים עליהן כאן הן שלנו.",
    "hi": "यह साइट Lumi Studio चलाता है, जो यहाँ दिखाए गए ऐप्स का डेवलपर है। यहाँ सुझाए गए ऐप्स हमारे अपने हैं।",
    "bn-BD": "এই সাইটটি পরিচালনা করে Lumi Studio, এখানে দেখানো অ্যাপগুলোর ডেভেলপার। এখানে সুপারিশ করা অ্যাপগুলো আমাদের নিজেদের।",
    "gu-IN": "આ સાઇટ Lumi Studio ચલાવે છે, જે અહીં દર્શાવેલી ઍપ્સના ડેવલપર છે. અહીં ભલામણ કરેલી ઍપ્સ અમારી પોતાની છે.",
    "kn-IN": "ಈ ಸೈಟ್ ಅನ್ನು ಇಲ್ಲಿ ತೋರಿಸಿರುವ ಆ್ಯಪ್‌ಗಳ ಡೆವಲಪರ್ ಆದ Lumi Studio ನಡೆಸುತ್ತದೆ. ಇಲ್ಲಿ ಶಿಫಾರಸು ಮಾಡಿರುವ ಆ್ಯಪ್‌ಗಳು ನಮ್ಮದೇ.",
    "ml-IN": "ഇവിടെ കാണിക്കുന്ന ആപ്പുകളുടെ ഡെവലപ്പറായ Lumi Studio ആണ് ഈ സൈറ്റ് നടത്തുന്നത്. ഇവിടെ ശുപാർശ ചെയ്യുന്ന ആപ്പുകൾ ഞങ്ങളുടേതാണ്.",
    "mr-IN": "ही साइट Lumi Studio चालवते, जे येथे दाखवलेल्या ॲप्सचे डेव्हलपर आहेत. येथे सुचवलेले ॲप्स आमचेच आहेत.",
    "or-IN": "ଏହି ସାଇଟ୍‌ଟି ଏଠାରେ ଦେଖାଯାଇଥିବା ଆପ୍‌ର ଡେଭଲପର Lumi Studio ପରିଚାଳନା କରେ। ଏଠାରେ ସୁପାରିଶ କରାଯାଇଥିବା ଆପ୍‌ଗୁଡ଼ିକ ଆମର ନିଜର।",
    "pa-IN": "ਇਹ ਸਾਈਟ Lumi Studio ਚਲਾਉਂਦਾ ਹੈ, ਜੋ ਇੱਥੇ ਦਿਖਾਈਆਂ ਐਪਾਂ ਦਾ ਡਿਵੈਲਪਰ ਹੈ। ਇੱਥੇ ਸਿਫ਼ਾਰਸ਼ ਕੀਤੀਆਂ ਐਪਾਂ ਸਾਡੀਆਂ ਆਪਣੀਆਂ ਹਨ।",
    "ta-IN": "இங்கே காட்டப்படும் ஆப்களின் டெவலப்பரான Lumi Studio இந்தத் தளத்தை நடத்துகிறது. இங்கே பரிந்துரைக்கப்படும் ஆப்கள் எங்களுடையவை.",
    "te-IN": "ఇక్కడ చూపిన యాప్‌ల డెవలపర్ అయిన Lumi Studio ఈ సైట్‌ను నిర్వహిస్తోంది. ఇక్కడ సిఫార్సు చేసిన యాప్‌లు మా సొంతవి.",
    "ur-PK": "یہ سائٹ Lumi Studio چلاتا ہے، جو یہاں دکھائی گئی ایپس کا ڈویلپر ہے۔ یہاں تجویز کردہ ایپس ہماری اپنی ہیں۔",
    "th": "เว็บไซต์นี้ดำเนินการโดย Lumi Studio ผู้พัฒนาแอปที่แนะนำ แอปที่เราแนะนำที่นี่เป็นแอปของเราเอง",
    "vi": "Trang web này do Lumi Studio, nhà phát triển các ứng dụng được giới thiệu, điều hành. Các ứng dụng chúng tôi đề xuất ở đây là của chính chúng tôi.",
    "id": "Situs ini dikelola oleh Lumi Studio, pengembang aplikasi yang ditampilkan. Aplikasi yang kami rekomendasikan di sini adalah aplikasi kami sendiri.",
    "ms": "Laman ini dikendalikan oleh Lumi Studio, pembangun aplikasi yang dipaparkan. Aplikasi yang kami syorkan di sini ialah aplikasi kami sendiri.",
    "ca": "Aquest lloc el gestiona Lumi Studio, el desenvolupador de les apps que s'hi presenten. Les apps que recomanem aquí són nostres.",
})

# The legacy FAQ "Is this page independent?" was answered "Yes." That is false.
LEGACY_FAQ_ANSWER = (
    "Yes. It is a buying guide; app names and trademarks belong to their "
    "respective owners."
)
FAQ_ANSWER = MappingProxyType({
    "en-US": "No. It is published by Lumi Studio, the developer of the featured apps; app names and trademarks belong to their respective owners.",
    "ja": "いいえ。本ページは掲載アプリの開発者であるLumi Studioが公開する購入ガイドであり、各アプリ名や商標は、それぞれの所有者に帰属します。",
    "zh-Hant": "不是。這是由所介紹 App 的開發者 Lumi Studio 發布的選購指南；App 名稱與商標屬於各自所有者。",
    "zh-Hans": "不是。这是由所介绍 App 的开发者 Lumi Studio 发布的选购指南；App 名称与商标属于各自所有者。",
    "ko": "아니요. 이 페이지는 소개된 앱의 개발사인 Lumi Studio가 발행하는 구매 가이드이며, 각 앱 이름과 상표는 해당 소유자에게 있습니다.",
    "de-DE": "Nein. Dieser Kaufratgeber wird von Lumi Studio veröffentlicht, dem Entwickler der vorgestellten Apps; App-Namen und Marken gehören ihren jeweiligen Eigentümern.",
    "fr-FR": "Non. Ce guide d'achat est publié par Lumi Studio, le développeur des apps présentées ; les noms d'apps et les marques appartiennent à leurs propriétaires respectifs.",
    "fr-CA": "Non. Ce guide d'achat est publié par Lumi Studio, le développeur des applications présentées; les noms d'applications et les marques de commerce appartiennent à leurs propriétaires respectifs.",
    "es-ES": "No. Es una guía de compra publicada por Lumi Studio, el desarrollador de las apps que aparecen; los nombres de apps y las marcas pertenecen a sus respectivos propietarios.",
    "es-MX": "No. Es una guía de compra publicada por Lumi Studio, el desarrollador de las apps que se presentan; los nombres de las apps y las marcas pertenecen a sus respectivos dueños.",
    "pt-BR": "Não. Este é um guia de compra publicado pela Lumi Studio, desenvolvedora dos apps apresentados; nomes de apps e marcas pertencem aos seus respectivos donos.",
    "pt-PT": "Não. É um guia de compra publicado pela Lumi Studio, que desenvolve as apps apresentadas; os nomes das aplicações e as marcas pertencem aos respetivos proprietários.",
    "it": "No. È una guida all'acquisto pubblicata da Lumi Studio, lo sviluppatore delle app presentate; i nomi delle app e i marchi appartengono ai rispettivi proprietari.",
    "nl-NL": "Nee. Deze koopgids wordt gepubliceerd door Lumi Studio, de ontwikkelaar van de getoonde apps; app-namen en merken zijn eigendom van hun respectieve eigenaren.",
    "sv": "Nej. Det är en köpguide som publiceras av Lumi Studio, utvecklaren av apparna som presenteras; appnamn och varumärken tillhör sina respektive ägare.",
    "da": "Nej. Det er en købsguide, som udgives af Lumi Studio, udvikleren af de viste apps; appnavne og varemærker tilhører deres respektive ejere.",
    "no": "Nei. Dette er en kjøpsguide som publiseres av Lumi Studio, utvikleren av appene som presenteres; appnavn og varemerker tilhører sine respektive eiere.",
    "fi": "Ei. Tämä ostopas on esiteltyjen sovellusten kehittäjän Lumi Studion julkaisema; sovellusten nimet ja tavaramerkit kuuluvat omistajilleen.",
    "pl": "Nie. To poradnik zakupowy publikowany przez Lumi Studio – twórcę prezentowanych aplikacji; nazwy aplikacji i znaki towarowe należą do ich właścicieli.",
    "cs": "Ne. Jde o nákupního průvodce, kterého vydává Lumi Studio, vývojář představených aplikací; názvy aplikací a ochranné známky patří jejich vlastníkům.",
    "sk": "Nie. Ide o nákupného sprievodcu, ktorého vydáva Lumi Studio, vývojár predstavených aplikácií; názvy aplikácií a ochranné známky patria ich vlastníkom.",
    "sl-SI": "Ne. Gre za nakupni vodnik, ki ga objavlja Lumi Studio, razvijalec predstavljenih aplikacij; imena aplikacij in blagovne znamke pripadajo njihovim lastnikom.",
    "hr": "Ne. Riječ je o vodiču za kupnju koji objavljuje Lumi Studio, razvojni programer predstavljenih aplikacija; nazivi aplikacija i žigovi pripadaju njihovim vlasnicima.",
    "hu": "Nem. Ez egy vásárlási útmutató, amelyet a Lumi Studio, a bemutatott alkalmazások fejlesztője tesz közzé; az alkalmazásnevek és a védjegyek a tulajdonosaikat illetik.",
    "ro": "Nu. Este un ghid de cumpărare publicat de Lumi Studio, dezvoltatorul aplicațiilor prezentate; numele aplicațiilor și mărcile aparțin proprietarilor lor.",
    "ru": "Нет. Это руководство по выбору публикует Lumi Studio — разработчик представленных приложений; названия приложений и товарные знаки принадлежат их владельцам.",
    "uk": "Ні. Цей посібник із вибору публікує Lumi Studio — розробник представлених застосунків; назви застосунків і торговельні марки належать їхнім власникам.",
    "el": "Όχι. Είναι οδηγός αγοράς που δημοσιεύει η Lumi Studio, η δημιουργός των εφαρμογών που παρουσιάζονται· τα ονόματα εφαρμογών και τα εμπορικά σήματα ανήκουν στους κατόχους τους.",
    "tr": "Hayır. Bu satın alma rehberi, tanıtılan uygulamaların geliştiricisi Lumi Studio tarafından yayımlanır; uygulama adları ve ticari markalar ilgili sahiplerine aittir.",
    "ar-SA": "لا. هذا دليل شراء تنشره Lumi Studio، مطوّر التطبيقات المعروضة؛ وأسماء التطبيقات والعلامات التجارية تعود لأصحابها.",
    "he": "לא. זהו מדריך קנייה שמפרסמת Lumi Studio, המפתחת של האפליקציות המוצגות; שמות האפליקציות והסימנים המסחריים שייכים לבעליהם.",
    "hi": "नहीं। यह खरीदारी गाइड Lumi Studio प्रकाशित करता है, जो यहाँ दिखाए गए ऐप्स का डेवलपर है; ऐप के नाम और ट्रेडमार्क उनके अपने मालिकों के हैं।",
    "bn-BD": "না। এই কেনাকাটার গাইডটি প্রকাশ করে Lumi Studio, এখানে দেখানো অ্যাপগুলোর ডেভেলপার; অ্যাপের নাম ও ট্রেডমার্ক তাদের নিজ নিজ মালিকের।",
    "gu-IN": "ના. આ ખરીદી માર્ગદર્શિકા Lumi Studio પ્રકાશિત કરે છે, જે અહીં દર્શાવેલી ઍપ્સના ડેવલપર છે; ઍપનાં નામ અને ટ્રેડમાર્ક તેમના સંબંધિત માલિકોના છે.",
    "kn-IN": "ಇಲ್ಲ. ಈ ಖರೀದಿ ಮಾರ್ಗದರ್ಶಿಯನ್ನು ಇಲ್ಲಿ ತೋರಿಸಿರುವ ಆ್ಯಪ್‌ಗಳ ಡೆವಲಪರ್ ಆದ Lumi Studio ಪ್ರಕಟಿಸುತ್ತದೆ; ಆ್ಯಪ್ ಹೆಸರುಗಳು ಮತ್ತು ಟ್ರೇಡ್‌ಮಾರ್ಕ್‌ಗಳು ಅವುಗಳ ಮಾಲೀಕರಿಗೆ ಸೇರಿವೆ.",
    "ml-IN": "അല്ല. ഇവിടെ കാണിക്കുന്ന ആപ്പുകളുടെ ഡെവലപ്പറായ Lumi Studio പ്രസിദ്ധീകരിക്കുന്ന വാങ്ങൽ ഗൈഡാണിത്; ആപ്പ് പേരുകളും ട്രേഡ്‌മാർക്കുകളും അവയുടെ ഉടമകളുടേതാണ്.",
    "mr-IN": "नाही. हे खरेदी मार्गदर्शक Lumi Studio प्रकाशित करते, जे येथे दाखवलेल्या ॲप्सचे डेव्हलपर आहेत; ॲप्सची नावे आणि ट्रेडमार्क त्यांच्या संबंधित मालकांचे आहेत.",
    "or-IN": "ନା। ଏହି କ୍ରୟ ଗାଇଡ୍‌ଟି ଏଠାରେ ଦେଖାଯାଇଥିବା ଆପ୍‌ର ଡେଭଲପର Lumi Studio ପ୍ରକାଶ କରେ; ଆପ୍‌ର ନାମ ଓ ଟ୍ରେଡମାର୍କ ସେମାନଙ୍କ ମାଲିକଙ୍କର।",
    "pa-IN": "ਨਹੀਂ। ਇਹ ਖਰੀਦਦਾਰੀ ਗਾਈਡ Lumi Studio ਪ੍ਰਕਾਸ਼ਿਤ ਕਰਦਾ ਹੈ, ਜੋ ਇੱਥੇ ਦਿਖਾਈਆਂ ਐਪਾਂ ਦਾ ਡਿਵੈਲਪਰ ਹੈ; ਐਪਾਂ ਦੇ ਨਾਮ ਅਤੇ ਟ੍ਰੇਡਮਾਰਕ ਉਨ੍ਹਾਂ ਦੇ ਮਾਲਕਾਂ ਦੇ ਹਨ।",
    "ta-IN": "இல்லை. இந்த வாங்குதல் வழிகாட்டியை இங்கே காட்டப்படும் ஆப்களின் டெவலப்பரான Lumi Studio வெளியிடுகிறது; ஆப் பெயர்களும் வர்த்தக முத்திரைகளும் அவற்றின் உரிமையாளர்களுக்கே சொந்தம்.",
    "te-IN": "కాదు. ఈ కొనుగోలు గైడ్‌ను ఇక్కడ చూపిన యాప్‌ల డెవలపర్ అయిన Lumi Studio ప్రచురిస్తుంది; యాప్ పేర్లు, ట్రేడ్‌మార్క్‌లు వాటి యజమానులకే చెందుతాయి.",
    "ur-PK": "نہیں۔ یہ خریداری گائیڈ Lumi Studio شائع کرتا ہے، جو یہاں دکھائی گئی ایپس کا ڈویلپر ہے؛ ایپس کے نام اور ٹریڈ مارکس ان کے مالکان کی ملکیت ہیں۔",
    "th": "ไม่ใช่ นี่คือคู่มือการเลือกซื้อที่เผยแพร่โดย Lumi Studio ผู้พัฒนาแอปที่แนะนำ ชื่อแอปและเครื่องหมายการค้าทั้งหมดเป็นของเจ้าของแต่ละราย",
    "vi": "Không. Đây là hướng dẫn mua hàng do Lumi Studio, nhà phát triển các ứng dụng được giới thiệu, xuất bản; tên ứng dụng và thương hiệu thuộc về chủ sở hữu tương ứng.",
    "id": "Tidak. Ini adalah panduan pembelian yang diterbitkan oleh Lumi Studio, pengembang aplikasi yang ditampilkan; nama aplikasi dan merek dagang adalah milik pemiliknya masing-masing.",
    "ms": "Tidak. Ini panduan pembelian yang diterbitkan oleh Lumi Studio, pembangun aplikasi yang dipaparkan; nama aplikasi dan tanda dagangan milik pemilik masing-masing.",
    "ca": "No. És una guia de compra que publica Lumi Studio, el desenvolupador de les apps que s'hi presenten; els noms de les apps i les marques pertanyen als seus propietaris respectius.",
})

# Localized "Independent comparison." first sentence of the legacy
# alternatives disclaimer (in its <small> line and its footer) -> truthful
# replacement. Matched only when the trademark sentence follows, which the
# replacement keeps.
LEGACY_COMPARISON = MappingProxyType({
    "de-DE": ("Unabhängiger Vergleich.", "App-Namen sind Marken", "Vergleich von Lumi Studio, dem Entwickler der vorgestellten Apps."),
    "es-ES": ("Comparación independiente.", "Los nombres de apps", "Comparación publicada por Lumi Studio, el desarrollador de las apps que aparecen."),
    "pt-BR": ("Comparação independente.", "Nomes de apps", "Comparação publicada pela Lumi Studio, desenvolvedora dos apps apresentados."),
    "ja": ("独立した比較です。", "アプリ名は", "掲載アプリの開発者であるLumi Studioによる比較です。"),
    "ko": ("독립 비교입니다.", "앱 이름은", "소개된 앱의 개발사인 Lumi Studio가 작성한 비교입니다."),
    "zh-Hans": ("独立比较。", "App 名称", "由这些 App 的开发者 Lumi Studio 撰写的比较。"),
    "fr-FR": ("Comparaison indépendante.", "Les noms d", "Comparaison publiée par Lumi Studio, le développeur des apps présentées."),
    "zh-Hant": ("獨立比較。", "App 名稱", "由這些 App 的開發者 Lumi Studio 撰寫的比較。"),
})


STYLE = (
    "margin:0;padding:8px 16px;background:#f3f4f6;color:#1f2937;"
    "border-bottom:1px solid #d1d5db;font-size:13px;line-height:1.5;"
    "text-align:center"
)
BANNER_RE = re.compile(
    r'<p\b[^>]*\bdata-first-party-disclosure="banner"[^>]*>.*?</p>\n?',
    re.DOTALL,
)
PUBLISHER_BLOCK_RE = re.compile(
    r'<script\b[^>]*\bdata-first-party-disclosure="publisher"[^>]*>.*?</script>\n?',
    re.DOTALL,
)
JSONLD_RE = re.compile(
    r'(<script\b[^>]*type="application/ld\+json"[^>]*>)(.*?)(</script>)',
    re.DOTALL | re.IGNORECASE,
)
ORG_NAME_RE = re.compile(
    r'("@id"\s*:\s*"' + re.escape(ORGANIZATION_ID) + r'"\s*,\s*"name"\s*:\s*)"(?:[^"\\]|\\.)*"'
)
HTML_LANG_RE = re.compile(r"<html\b[^>]*?\blang=\"([^\"]+)\"", re.IGNORECASE)
CANONICAL_RE = re.compile(r'<link\b[^>]*rel="canonical"[^>]*href="([^"]+)"', re.IGNORECASE)
BODY_RE = re.compile(r"<body\b[^>]*>", re.IGNORECASE)
MAIN_RE = re.compile(r"<main\b", re.IGNORECASE)
H1_RE = re.compile(r"<h1\b", re.IGNORECASE)
HEADER_END_RE = re.compile(r"</header\s*>", re.IGNORECASE)
HEAD_END_RE = re.compile(r"</head\s*>", re.IGNORECASE)
STORE_LINK_RE = re.compile(r'href="https://(?:apps\.apple\.com|play\.google\.com)/', re.IGNORECASE)
REDIRECT_RE = re.compile(r'<meta\b[^>]*http-equiv="refresh"', re.IGNORECASE)
AMP_RE = re.compile(r"<html\b[^>]*(?:\bamp\b|⚡)|<amp-story\b", re.IGNORECASE)

_OFFICIAL_BY_LOWER = {locale.lower(): locale for locale in OFFICIAL_LOCALES}
_PRIMARY_ALIASES = {
    "en": "en-US", "de": "de-DE", "es": "es-MX", "fr": "fr-FR", "pt": "pt-BR",
    "nl": "nl-NL", "sl": "sl-SI", "bn": "bn-BD", "ur": "ur-PK", "ar": "ar-SA",
    "gu": "gu-IN", "kn": "kn-IN", "ml": "ml-IN", "mr": "mr-IN", "or": "or-IN",
    "pa": "pa-IN", "ta": "ta-IN", "te": "te-IN", "nb": "no", "nn": "no",
    "iw": "he", "in": "id",
}
_HANT_REGIONS = {"tw", "hk", "mo", "hant"}
# Pages in a regional variety whose readers use one of the 50 official written
# standards (ISO 639-3 members of the ar / zh / ms macrolanguages, Hindi-belt
# Devanagari languages, Indonesian regional languages). Anything else gets the
# English line, marked lang="en".
_MACRO_LOCALES = {
    **dict.fromkeys((
        "aao", "abh", "abv", "acm", "acq", "acw", "acx", "acy", "adf", "aeb",
        "aec", "afb", "ajp", "apc", "apd", "arb", "arq", "ars", "ary", "arz",
        "auz", "avl", "ayh", "ayl", "ayn", "ayp", "pga", "shu", "ssh",
    ), "ar-SA"),
    **dict.fromkeys(("cmn", "wuu", "gan", "hsn", "cjy", "czh", "czo", "mnp", "lzh"), "zh-Hans"),
    **dict.fromkeys(("yue", "nan", "hak", "cdo"), "zh-Hant"),
    **dict.fromkeys(("bho", "mag", "mai", "awa", "raj", "hne", "bgc", "mwr", "bra", "bjj"), "hi"),
    **dict.fromkeys(("zlm", "zsm"), "ms"),
    **dict.fromkeys(("jv", "jav", "su", "sun", "ace", "ban", "bjn", "bug", "mad", "min", "sas", "mak", "bew"), "id"),
    **dict.fromkeys(("bs", "sh", "hbs"), "hr"),
}


def resolve_locale(lang: str | None) -> str | None:
    """Map an html ``lang`` value to one of the 50 official locales, or None."""
    if not lang:
        return None
    value = lang.strip().replace("_", "-")
    exact = _OFFICIAL_BY_LOWER.get(value.lower())
    if exact:
        return exact
    parts = value.lower().split("-")
    primary = parts[0]
    if primary == "zh":
        return "zh-Hant" if _HANT_REGIONS.intersection(parts[1:]) else "zh-Hans"
    if primary == "es" and len(parts) > 1 and parts[1] == "es":
        return "es-ES"
    if primary == "pt" and len(parts) > 1 and parts[1] in {"pt", "ao", "mz"}:
        return "pt-PT"
    if primary == "fr" and len(parts) > 1 and parts[1] == "ca":
        return "fr-CA"
    if primary in _OFFICIAL_BY_LOWER:
        return _OFFICIAL_BY_LOWER[primary]
    return _PRIMARY_ALIASES.get(primary) or _MACRO_LOCALES.get(primary)


def _localized(table: Mapping[str, str], locale: str) -> str:
    if locale in table:
        return table[locale]
    if locale.startswith("en-"):
        return table["en-US"]
    raise KeyError(f"missing first-party copy for {locale}")


def banner_text(locale: str) -> str:
    return _localized(BANNER, locale)


def faq_answer(locale: str) -> str:
    return _localized(FAQ_ANSWER, locale)


def banner_html(locale: str, *, lang: str | None = None) -> str:
    """``lang`` marks the line's language when it differs from the page's."""
    lang_attr = f' lang="{html.escape(lang)}"' if lang else ""
    return (
        f'<p class="first-party-disclosure" {MARKER}="banner" role="note"'
        f'{lang_attr} style="{STYLE}">'
        f"{html.escape(banner_text(locale), quote=False)}</p>"
    )


def _insertion_offset(source: str) -> int | None:
    body = BODY_RE.search(source)
    if body is None:
        return None
    start = body.end()
    main = MAIN_RE.search(source, start)
    if main is not None:
        store = STORE_LINK_RE.search(source, start, main.start())
        h1 = H1_RE.search(source, start, main.start())
        if store is None and h1 is None:
            # Before <main>: right under the site header, outside the
            # answer-first content every page validator reads.
            return main.start()
        return start
    header = re.match(r"\s*<header\b", source[start:], re.IGNORECASE)
    if header:
        close = HEADER_END_RE.search(source, start)
        if close is not None:
            between = source[start:close.start()]
            if not STORE_LINK_RE.search(between) and not H1_RE.search(between):
                return close.end()
    return start


def ensure_banner(source: str, locale: str, *, lang: str | None = None) -> str:
    snippet = banner_html(locale, lang=lang) + "\n"
    existing = BANNER_RE.search(source)
    if existing:
        if existing.group(0) == snippet:
            return source
        return source[:existing.start()] + snippet + source[existing.end():]
    offset = _insertion_offset(source)
    if offset is None:
        return source
    return source[:offset] + snippet + source[offset:]


def _publisher_block(canonical: str | None) -> str:
    """A ``WebSite`` node (the same ``#website`` entity the site graph uses)
    published by the developer. Not a second ``WebPage``: pages keep exactly
    the page entities their own generator emits."""
    del canonical  # the site, not the page, is what the developer publishes
    site = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "@id": WEBSITE_ID,
        "url": PUBLIC_SITE,
        "publisher": {
            "@type": "Organization",
            "@id": ORGANIZATION_ID,
            "name": DEVELOPER,
            "url": ABOUT_URL,
            "description": "Developer of the featured apps and operator of this site.",
        },
    }
    payload = json.dumps(site, ensure_ascii=False, separators=(",", ":"))
    return (
        f'<script type="application/ld+json" {MARKER}="publisher">'
        f"{payload}</script>\n"
    )


def ensure_publisher(source: str) -> str:
    """Name the developer as publisher in the page's structured data."""
    def rename(match: re.Match) -> str:
        return match.group(1) + json.dumps(DEVELOPER)

    def fix_block(match: re.Match) -> str:
        opening, payload, closing = match.groups()
        if MARKER in opening:
            return match.group(0)
        return opening + ORG_NAME_RE.sub(rename, payload) + closing

    updated = JSONLD_RE.sub(fix_block, source)
    others = [
        payload for opening, payload, _ in JSONLD_RE.findall(updated)
        if MARKER not in opening
    ]
    has_publisher = any(
        '"publisher"' in payload or '"author"' in payload for payload in others
    )
    existing = PUBLISHER_BLOCK_RE.search(updated)
    if has_publisher:
        if existing:
            updated = updated[:existing.start()] + updated[existing.end():]
        return updated
    canonical = CANONICAL_RE.search(updated)
    block = _publisher_block(html.unescape(canonical.group(1)) if canonical else None)
    if existing:
        if existing.group(0) == block:
            return updated
        return updated[:existing.start()] + block + updated[existing.end():]
    # Offsets come from the original string: str.lower() changes the length
    # of text such as Turkish "İ", so never search a lowered copy.
    head_end = HEAD_END_RE.search(updated)
    if head_end is None:
        return updated
    return updated[:head_end.start()] + block + updated[head_end.start():]


_ENCODINGS = (
    lambda text: text,
    lambda text: html.escape(text, quote=False),
    lambda text: html.escape(text, quote=True),
    lambda text: json.dumps(text, ensure_ascii=True)[1:-1],
    lambda text: json.dumps(text, ensure_ascii=False)[1:-1],
)


def _replace_text(source: str, old: str, new: str) -> str:
    """Replace ``old`` with ``new`` in markup, attribute and JSON-LD encodings."""
    if old == new:
        return source
    seen: set[str] = set()
    for encode in _ENCODINGS:
        old_form = encode(old)
        if old_form in seen:
            continue
        seen.add(old_form)
        if old_form in source:
            source = source.replace(old_form, encode(new))
    return source


def load_legacy_faq_answers(translations_dir: Path = HERE / "i18n_trans") -> dict[str, str]:
    """Localized wording of the legacy "Yes." answer, per locale dictionary."""
    legacy: dict[str, str] = {}
    for locale in OFFICIAL_LOCALES:
        path = translations_dir / f"{locale}.json"
        if not path.is_file():
            continue
        value = json.loads(path.read_text(encoding="utf-8")).get(LEGACY_FAQ_ANSWER)
        if isinstance(value, str) and value.strip():
            legacy[locale] = value
    return legacy


def fix_legacy_claims(source: str, locale: str, legacy_faq: Mapping[str, str]) -> str:
    updated = _replace_text(source, LEGACY_FAQ_ANSWER, FAQ_ANSWER["en-US"])
    localized_old = legacy_faq.get(locale)
    if localized_old:
        updated = _replace_text(updated, localized_old, faq_answer(locale))
    legacy = LEGACY_COMPARISON.get(locale)
    if legacy:
        old, tail, new = legacy
        pattern = re.compile(re.escape(old) + r"(?=\s*" + re.escape(tail) + ")")
        updated = pattern.sub(lambda _match: new, updated)
    return updated


def page_locale(source: str, relative: str) -> tuple[str, bool]:
    """Return (locale, is_fallback). Unknown languages fall back to English."""
    lang = HTML_LANG_RE.search(source[:4000])
    locale = resolve_locale(lang.group(1)) if lang else None
    if locale is None:
        first = relative.split("/", 1)[0]
        if first in OFFICIAL_LOCALES:
            locale = first
    if locale is None:
        return "en-US", bool(lang) and not lang.group(1).lower().startswith("en")
    return locale, False


def is_promotional(source: str) -> bool:
    return (
        STORE_LINK_RE.search(source) is not None
        and REDIRECT_RE.search(source[:4000]) is None
        and AMP_RE.search(source[:4000]) is None
        and BODY_RE.search(source) is not None
    )


def transform(source: str, locale: str, legacy_faq: Mapping[str, str], *,
              fallback: bool = False) -> str:
    updated = fix_legacy_claims(source, locale, legacy_faq)
    updated = ensure_banner(updated, locale, lang="en" if fallback else None)
    return ensure_publisher(updated)


def apply_to_page(source: str, *, locale: str | None = None) -> str:
    """Banner + developer publisher for a page another generator builds (the
    support sites). ``locale`` defaults to the page's ``<html lang>``; a
    language outside the 50 gets the English line marked ``lang="en"``."""
    resolved = resolve_locale(locale) if locale else None
    fallback = False
    if resolved is None:
        resolved, fallback = page_locale(source, "")
    updated = ensure_banner(source, resolved, lang="en" if fallback else None)
    return ensure_publisher(updated)


def digest_pinned(pages: Path) -> set[str]:
    pinned: set[str] = set()
    for relative, kind in DIGEST_PINNED_MANIFESTS:
        try:
            document = json.loads((pages / relative).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if kind == "outputs":
            pinned.update(str(path) for path in (document.get("outputs") or {}))
            continue
        for entry in document.get("expected_outputs") or []:
            if isinstance(entry, dict) and entry.get("kind") == kind:
                pinned.add(str(entry.get("relative_path")))
        for route in document.get("routes") or []:
            if isinstance(route, dict) and route.get("relative_path"):
                pinned.add(str(route["relative_path"]))
    return pinned


def _owned_elsewhere(relative: str) -> bool:
    """Dataset catalogs and API docs: digest-listed distributions that already
    open with their own first-party publisher statement."""
    parts = relative.split("/")
    sections = parts[:2] if parts[0] in OFFICIAL_LOCALES else parts[:1]
    return bool(OWNED_SECTIONS.intersection(sections))


def site_pages(pages: Path) -> Iterable[Path]:
    for directory, subdirs, files in os.walk(pages):
        subdirs[:] = sorted(d for d in subdirs if d not in EXCLUDED_PARTS)
        for name in sorted(files):
            if name.endswith(".html"):
                path = Path(directory) / name
                if not path.is_symlink():
                    yield path


def run(pages: Path = PAGES, *, check: bool = False,
        translations_dir: Path = HERE / "i18n_trans") -> dict[str, object]:
    pages = Path(pages).resolve()
    pinned = digest_pinned(pages)
    legacy_faq = load_legacy_faq_answers(translations_dir)
    stats = {"scanned": 0, "promotional": 0, "pinned_skipped": 0,
             "changed": 0, "english_fallback": 0}
    pending: list[str] = []
    for path in site_pages(pages):
        stats["scanned"] += 1
        relative = path.relative_to(pages).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if not is_promotional(source):
            continue
        if relative in pinned or _owned_elsewhere(relative):
            stats["pinned_skipped"] += 1
            continue
        stats["promotional"] += 1
        locale, fallback = page_locale(source, relative)
        stats["english_fallback"] += int(fallback)
        updated = transform(source, locale, legacy_faq, fallback=fallback)
        if updated != source:
            stats["changed"] += 1
            if check:
                pending.append(relative)
            else:
                path.write_text(updated, encoding="utf-8")
    if check:
        stats["pending"] = pending[:20]
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--pages", type=Path, default=PAGES)
    parser.add_argument("--check", action="store_true",
                        help="fail when any promotional page lacks the disclosure")
    args = parser.parse_args(argv)
    stats = run(args.pages, check=args.check)
    print("First-party disclosure: " + json.dumps(stats, ensure_ascii=False))
    return 1 if args.check and stats["changed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
