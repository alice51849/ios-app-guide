#!/usr/bin/env python3
"""Generate localized portfolio catalogs from verified public App Store entries."""
from __future__ import annotations

from datetime import date
import html
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))
sys.path.insert(0, HERE)

from appstore_live import live_app_keys  # noqa: E402
import gen_feed  # noqa: E402
import gen_mobile_app_identity  # noqa: E402
from videogen.registry import APPS, APPSTORE  # noqa: E402

PAGES = os.environ.get("GEO_PAGES", os.path.join(HERE, "pages"))
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide").rstrip("/")
SITEMAP_NAME = "sitemap_apps.xml"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")

L10N = {
    "en": {
        "path": "apps/index.html", "locale": "en-US", "lang": "en",
        "title": "Independent iOS Apps by Alice — privacy-first choices",
        "description": "Browse public iOS apps for learning, productivity, photos, money, health and everyday life. Each card links directly to the App Store.",
        "h1": "Independent iOS apps for real everyday needs",
        "lead": "Choose by task, read the detailed guide, then open the verified App Store page directly.",
        "guide": "App guide", "hub": "All resources", "store": "App Store",
        "categories": {
            "kids": "Kids & learning", "education": "Education", "productivity": "Productivity",
            "photo-utility": "Photo & utility", "finance": "Money & travel",
            "travel": "Travel", "health": "Health", "lifestyle": "Lifestyle",
            "sleep-sound": "Sleep & focus", "other": "More",
        },
    },
    "zh-Hant": {
        "path": "apps/zh-Hant/index.html", "locale": "zh-Hant", "lang": "zh-Hant",
        "title": "Alice 的 iOS App 總覽｜隱私優先、直接下載",
        "description": "瀏覽已公開的學習、效率、照片、理財、健康與生活 iOS App；每張卡片都提供正確 App Store 直連。",
        "h1": "依照真正需求挑選 iOS App",
        "lead": "先看完整中文指南，再從已驗證的 App Store 連結直接下載。",
        "guide": "App 詳細指南", "hub": "所有相關資源", "store": "App Store",
        "categories": {
            "kids": "兒童與學習", "education": "學習", "productivity": "效率工具",
            "photo-utility": "照片與實用工具", "finance": "理財與旅行",
            "travel": "旅行", "health": "健康", "lifestyle": "生活",
            "sleep-sound": "睡眠與專注", "other": "更多",
        },
    },
    "zh-Hans": {
        "path": "apps/zh-Hans/index.html", "locale": "zh-Hans", "lang": "zh-Hans",
        "title": "Alice 的 iOS App 一览｜注重隐私，直达下载",
        "description": "浏览已公开的学习、效率、照片、理财、健康和生活类 iOS App；每张卡片都提供已验证的 App Store 直达链接。",
        "h1": "按实际需求选择 iOS App",
        "lead": "先查看简体中文指南，再通过已验证的 App Store 链接直接下载。",
        "guide": "App 详细指南", "hub": "全部相关资源", "store": "App Store",
        "categories": {
            "kids": "儿童与学习", "education": "教育", "productivity": "效率工具",
            "photo-utility": "照片与实用工具", "finance": "理财与旅行",
            "travel": "旅行", "health": "健康", "lifestyle": "生活",
            "sleep-sound": "睡眠与专注", "other": "更多",
        },
    },
    "ja": {
        "path": "apps/ja/index.html", "locale": "ja", "lang": "ja",
        "title": "Alice の iOS アプリ一覧｜目的別に選べる公式ガイド",
        "description": "学習、仕事効率化、写真、お金、健康、暮らしに役立つ公開中の iOS アプリを紹介。各カードから App Store へ直接移動できます。",
        "h1": "目的に合う iOS アプリを見つける",
        "lead": "詳しい日本語ガイドを確認し、検証済みの App Store リンクから直接ダウンロードできます。",
        "guide": "アプリ詳細", "hub": "関連ガイド一覧", "store": "App Store",
        "categories": {
            "kids": "子ども・学習", "education": "学習", "productivity": "仕事効率化",
            "photo-utility": "写真・ユーティリティ", "finance": "お金・旅行",
            "travel": "旅行", "health": "健康", "lifestyle": "ライフスタイル",
            "sleep-sound": "睡眠・集中", "other": "その他",
        },
    },
    "ko": {
        "path": "apps/ko/index.html", "locale": "ko", "lang": "ko",
        "title": "Alice의 iOS 앱 모음｜목적별 선택 가이드",
        "description": "학습, 생산성, 사진, 금융, 건강과 일상에 유용한 공개 iOS 앱을 살펴보세요. 각 카드에서 검증된 App Store 페이지로 바로 이동합니다.",
        "h1": "필요한 일에 맞는 iOS 앱 찾기",
        "lead": "한국어 상세 가이드를 확인한 뒤 검증된 App Store 링크에서 바로 다운로드하세요.",
        "guide": "앱 상세 가이드", "hub": "관련 자료 전체", "store": "App Store",
        "categories": {
            "kids": "어린이·학습", "education": "교육", "productivity": "생산성",
            "photo-utility": "사진·유틸리티", "finance": "금융·여행",
            "travel": "여행", "health": "건강", "lifestyle": "라이프스타일",
            "sleep-sound": "수면·집중", "other": "기타",
        },
    },
    "de-DE": {
        "path": "apps/de-DE/index.html", "locale": "de-DE", "lang": "de-DE",
        "title": "iOS-Apps von Alice｜Nach Bedarf auswählen",
        "description": "Entdecke veröffentlichte iOS-Apps für Lernen, Produktivität, Fotos, Finanzen, Gesundheit und Alltag. Jede Karte führt direkt zum geprüften App-Store-Eintrag.",
        "h1": "Die passende iOS-App für deinen Alltag",
        "lead": "Lies den deutschen Ratgeber und öffne anschließend direkt den geprüften App-Store-Eintrag.",
        "guide": "App-Ratgeber", "hub": "Alle Ressourcen", "store": "App Store",
        "categories": {
            "kids": "Kinder & Lernen", "education": "Bildung", "productivity": "Produktivität",
            "photo-utility": "Foto & Dienstprogramme", "finance": "Finanzen & Reisen",
            "travel": "Reisen", "health": "Gesundheit", "lifestyle": "Lifestyle",
            "sleep-sound": "Schlaf & Fokus", "other": "Mehr",
        },
    },
    "fr-FR": {
        "path": "apps/fr-FR/index.html", "locale": "fr-FR", "lang": "fr-FR",
        "title": "Apps iOS d’Alice｜Le guide pour bien choisir",
        "description": "Découvrez des apps iOS publiées pour apprendre, s’organiser, gérer ses photos, son budget, sa santé et son quotidien. Chaque carte mène directement à la fiche App Store vérifiée.",
        "h1": "Trouvez l’app iOS adaptée à votre besoin",
        "lead": "Consultez le guide en français, puis ouvrez directement la fiche App Store vérifiée.",
        "guide": "Guide de l’app", "hub": "Toutes les ressources", "store": "App Store",
        "categories": {
            "kids": "Enfants et apprentissage", "education": "Éducation", "productivity": "Productivité",
            "photo-utility": "Photo et utilitaires", "finance": "Budget et voyages",
            "travel": "Voyages", "health": "Santé", "lifestyle": "Art de vivre",
            "sleep-sound": "Sommeil et concentration", "other": "Autres",
        },
    },
    "es-ES": {
        "path": "apps/es-ES/index.html", "locale": "es-ES", "lang": "es-ES",
        "title": "Apps para iPhone de Alice｜Guía para elegir",
        "description": "Descubre apps publicadas para aprender, organizarte, editar fotos, gestionar dinero, cuidar tu bienestar y resolver tareas diarias. Cada tarjeta abre la ficha verificada del App Store.",
        "h1": "Encuentra la app adecuada para lo que necesitas",
        "lead": "Consulta la guía en español y abre directamente la ficha verificada del App Store.",
        "guide": "Guía de la app", "hub": "Todos los recursos", "store": "App Store",
        "categories": {
            "kids": "Niños y aprendizaje", "education": "Educación", "productivity": "Productividad",
            "photo-utility": "Foto y utilidades", "finance": "Finanzas y viajes",
            "travel": "Viajes", "health": "Salud", "lifestyle": "Estilo de vida",
            "sleep-sound": "Sueño y concentración", "other": "Más",
        },
    },
    "es-MX": {
        "path": "apps/es-MX/index.html", "locale": "es-MX", "lang": "es-MX",
        "title": "Apps para iPhone de Alice｜Guía para elegir",
        "description": "Descubre apps publicadas para aprender, organizarte, editar fotos, gestionar dinero, cuidar tu bienestar y resolver tareas diarias. Cada tarjeta abre la ficha verificada del App Store.",
        "h1": "Encuentra la app adecuada para lo que necesitas",
        "lead": "Consulta la guía en español y abre directamente la ficha verificada del App Store.",
        "guide": "Guía de la app", "hub": "Todos los recursos", "store": "App Store",
        "categories": {
            "kids": "Niños y aprendizaje", "education": "Educación", "productivity": "Productividad",
            "photo-utility": "Foto y utilidades", "finance": "Finanzas y viajes",
            "travel": "Viajes", "health": "Salud", "lifestyle": "Estilo de vida",
            "sleep-sound": "Sueño y concentración", "other": "Más",
        },
    },
    "pt-BR": {
        "path": "apps/pt-BR/index.html", "locale": "pt-BR", "lang": "pt-BR",
        "title": "Apps para iPhone da Alice｜Guia para escolher",
        "description": "Conheça apps publicados para aprender, se organizar, cuidar de fotos, dinheiro, bem-estar e tarefas do dia a dia. Cada cartão abre diretamente a página verificada na App Store.",
        "h1": "Encontre o app certo para cada necessidade",
        "lead": "Confira o guia em português e abra diretamente a página verificada na App Store.",
        "guide": "Guia do app", "hub": "Todos os recursos", "store": "App Store",
        "categories": {
            "kids": "Crianças e aprendizagem", "education": "Educação", "productivity": "Produtividade",
            "photo-utility": "Fotos e utilitários", "finance": "Finanças e viagens",
            "travel": "Viagens", "health": "Saúde", "lifestyle": "Estilo de vida",
            "sleep-sound": "Sono e foco", "other": "Mais",
        },
    },
    "ar-SA": {
        "path": "apps/ar-SA/index.html", "locale": "ar-SA", "lang": "ar-SA",
        "title": "تطبيقات Alice على iPhone｜دليل الاختيار حسب الحاجة",
        "description": "استعرض تطبيقات iOS المنشورة للتعلّم والإنتاجية والصور والمال والصحة والحياة اليومية. تفتح كل بطاقة صفحة App Store الموثّقة مباشرة.",
        "h1": "اختر تطبيق iOS المناسب لاحتياجك",
        "lead": "اطّلع على الدليل العربي ثم انتقل مباشرة إلى صفحة App Store الموثّقة.",
        "guide": "دليل التطبيق", "hub": "كل الموارد", "store": "App Store",
        "categories": {
            "kids": "الأطفال والتعلّم", "education": "التعليم", "productivity": "الإنتاجية",
            "photo-utility": "الصور والأدوات", "finance": "المال والسفر",
            "travel": "السفر", "health": "الصحة", "lifestyle": "نمط الحياة",
            "sleep-sound": "النوم والتركيز", "other": "المزيد",
        },
    },
    "hi": {
        "path": "apps/hi/index.html", "locale": "hi", "lang": "hi",
        "title": "Alice के iPhone ऐप｜ज़रूरत के अनुसार चुनें",
        "description": "सीखने, उत्पादकता, फ़ोटो, पैसे, सेहत और रोज़मर्रा के कामों के लिए उपलब्ध iOS ऐप देखें। हर कार्ड सत्यापित App Store पेज पर सीधे ले जाता है।",
        "h1": "अपनी ज़रूरत के लिए सही iOS ऐप चुनें",
        "lead": "हिंदी गाइड पढ़ें, फिर सत्यापित App Store लिंक से सीधे डाउनलोड करें।",
        "guide": "ऐप गाइड", "hub": "सभी संसाधन", "store": "App Store",
        "categories": {
            "kids": "बच्चे और सीखना", "education": "शिक्षा", "productivity": "उत्पादकता",
            "photo-utility": "फ़ोटो और उपयोगी टूल", "finance": "पैसे और यात्रा",
            "travel": "यात्रा", "health": "स्वास्थ्य", "lifestyle": "जीवनशैली",
            "sleep-sound": "नींद और एकाग्रता", "other": "अन्य",
        },
    },
}

SUMMARY_FALLBACKS = {
    "zh-Hant": {
        "mochi": "用可愛、療癒的清單整理每天待辦，完成時輕點一下就有滿足感；無廣告。",
        "tripbee": "把航班、飯店、餐廳與活動排成每日行程，並依天數、季節與孩子年齡產生全家打包清單；離線、免帳號、一次買斷。",
        "sereno": "用高質感的白噪音與自然聲陪你入睡、專注與放鬆；離線可用、一次買斷。",
    },
    "ja": {
        "mochi": "かわいく心地よいチェックリストで毎日のタスクを整理。広告なしで、完了するたびに達成感を味わえます。",
        "tripbee": "フライト、ホテル、レストラン、予定を日ごとの旅程に整理し、日数・季節・子どもの年齢に合わせた家族の持ち物リストも作成。オフライン、アカウント不要、買い切りです。",
        "sereno": "上質なホワイトノイズと自然音で、睡眠・集中・リラックスをサポート。オフライン対応の買い切りアプリです。",
        "tripplanet": "旅行ゲーム、持ち物準備、発見アクティビティで、4〜10歳の子どもの旅を冒険に変えます。オフライン対応、第三者広告なし。",
    },
    "zh-Hans": {
        "mochi": "用可爱、舒心的清单整理每日待办，轻点完成时更有成就感；无广告，支持一次性解锁。",
        "tripbee": "按天整理航班、酒店、餐厅和活动，并根据行程天数、季节和孩子年龄生成全家行李清单；可离线使用、无需账户、一次买断。",
        "sereno": "用高品质白噪音和自然声音帮助睡眠、专注与放松；支持离线使用，一次解锁，无广告。",
        "tripplanet": "把每次旅行变成孩子的探索冒险：旅行游戏、行李准备和沿途发现；适合 4–10 岁，可离线使用，无第三方广告。",
    },
    "ko": {
        "tripbee": "항공편·숙소·식당·일정을 날짜별 여행 계획으로 정리하고, 여행 기간·계절·아이 나이에 맞는 가족 짐 목록도 만드세요. 오프라인, 계정 불필요, 일회성 구매입니다.",
        "sereno": "고품질 백색소음과 자연의 소리로 수면·집중·휴식을 돕습니다. 오프라인으로 사용할 수 있고, 한 번만 잠금 해제하면 되며 광고가 없습니다.",
        "tripplanet": "여행 게임, 짐 챙기기와 발견 활동으로 모든 여행을 아이의 탐험으로 바꿔 보세요. 4~10세용, 오프라인 지원, 제3자 광고 없음.",
    },
    "de": {
        "mochi": "Organisiere tägliche Aufgaben in niedlichen, ruhigen Checklisten und hake sie mit einem angenehmen Tippen ab – werbefrei und mit einmaliger Freischaltung.",
        "tripbee": "Ordne Flüge, Hotels, Restaurants und Aktivitäten zu einem Tagesplan und erstelle Familien-Packlisten nach Reisedauer, Jahreszeit und Alter der Kinder – offline, ohne Konto und als Einmalkauf.",
        "sereno": "Hochwertiges weißes Rauschen und Naturklänge für Schlaf, Konzentration und Entspannung – offline, werbefrei und mit einmaliger Freischaltung.",
        "tripplanet": "Mach jede Reise mit Spielen, Packhilfe und Entdeckeraufgaben zum Abenteuer für Kinder von 4 bis 10 Jahren – offline und ohne Drittanbieterwerbung.",
    },
    "fr": {
        "mochi": "Organisez vos tâches quotidiennes dans des listes douces et agréables, puis cochez-les d’un geste satisfaisant ; sans publicité, avec déblocage définitif.",
        "tripbee": "Regroupez vols, hôtels, restaurants et activités dans un itinéraire jour par jour, avec des listes de bagages familiales adaptées à la durée, à la saison et à l’âge des enfants ; hors ligne, sans compte et en achat unique.",
        "sereno": "Des bruits blancs et sons de la nature de haute qualité pour dormir, se concentrer et se détendre ; hors ligne, sans publicité, avec déblocage définitif.",
        "tripplanet": "Transformez chaque voyage en aventure grâce à des jeux, une aide aux bagages et des découvertes pour les enfants de 4 à 10 ans ; hors ligne et sans publicité tierce.",
    },
    "es": {
        "mochi": "Organiza las tareas diarias con listas bonitas y agradables, y disfruta al marcarlas con un toque; sin anuncios y con desbloqueo de pago único.",
        "tripbee": "Organiza vuelos, hoteles, restaurantes y actividades en un itinerario diario, y crea listas de equipaje familiares según la duración, la temporada y la edad de los niños; funciona sin conexión, sin cuenta y con pago único.",
        "sereno": "Ruido blanco y sonidos de la naturaleza de alta calidad para dormir, concentrarte y relajarte; funciona sin conexión, sin anuncios y con desbloqueo de pago único.",
        "tripplanet": "Convierte cada viaje en una aventura con juegos, ayuda para preparar el equipaje y actividades de descubrimiento para niños de 4 a 10 años; sin conexión y sin anuncios de terceros.",
    },
    "pt": {
        "mochi": "Organize as tarefas do dia em listas bonitas e acolhedoras e conclua cada item com um toque satisfatório; sem anúncios e com desbloqueio único.",
        "tripbee": "Organize voos, hotéis, restaurantes e atividades em um roteiro diário e crie listas de bagagem da família conforme a duração, a estação e a idade das crianças; funciona offline, sem conta e com compra única.",
        "sereno": "Ruído branco e sons da natureza de alta qualidade para dormir, focar e relaxar; funciona offline, sem anúncios e com desbloqueio único.",
        "tripplanet": "Transforme cada viagem em uma aventura com jogos, ajuda para arrumar a mala e atividades de descoberta para crianças de 4 a 10 anos; offline e sem anúncios de terceiros.",
    },
    "ar": {
        "mochi": "نظّم مهامك اليومية في قوائم لطيفة ومريحة، وأنهِ كل مهمة بلمسة مُرضية؛ بلا إعلانات مع فتح كامل لمرة واحدة.",
        "tripbee": "رتّب الرحلات الجوية والفنادق والمطاعم والأنشطة في خطة يومية، وأنشئ قوائم أمتعة للعائلة حسب مدة الرحلة والموسم وأعمار الأطفال؛ يعمل بلا إنترنت ومن دون حساب وبشراء لمرة واحدة.",
        "sereno": "ضوضاء بيضاء وأصوات طبيعية عالية الجودة للنوم والتركيز والاسترخاء؛ يعمل بلا إنترنت ومن دون إعلانات مع فتح كامل لمرة واحدة.",
        "tripplanet": "حوّل كل رحلة إلى مغامرة للأطفال من 4 إلى 10 سنوات عبر ألعاب السفر والمساعدة في تجهيز الأمتعة وأنشطة الاستكشاف؛ يعمل بلا إنترنت ومن دون إعلانات خارجية.",
    },
    "hi": {
        "tripbee": "उड़ान, होटल, रेस्तरां और गतिविधियों को दिनवार यात्रा योजना में रखें, और यात्रा की अवधि, मौसम व बच्चों की उम्र के अनुसार परिवार की पैकिंग सूची बनाएँ; ऑफ़लाइन, बिना खाते और एकमुश्त खरीद।",
        "sereno": "बेहतर नींद, एकाग्रता और सुकून के लिए उच्च-गुणवत्ता वाला व्हाइट नॉइज़ व प्रकृति की आवाज़ें; ऑफ़लाइन, बिना विज्ञापन और एक बार अनलॉक।",
        "tripplanet": "यात्रा खेलों, पैकिंग सहायता और खोज गतिविधियों से 4–10 वर्ष के बच्चों की हर यात्रा को रोमांच बनाएँ; ऑफ़लाइन और बिना तृतीय-पक्ष विज्ञापन।",
    },
}

CSS = """:root{--bg:#f6f7fb;--card:#fff;--ink:#151a2b;--muted:#616a7c;--line:#e2e6ef;--accent:#4f46e5}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(180deg,#fff,var(--bg));color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.55}
a{color:var(--accent);text-decoration:none}.wrap{width:min(1120px,100% - 32px);margin:auto}.hero{padding:48px 0 22px}.eyebrow{font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);font-size:.78rem}
h1{font-size:clamp(2rem,6vw,4rem);line-height:1.04;margin:.18em 0}.lead{max-width:780px;color:var(--muted);font-size:1.14rem}
h2{margin:34px 0 14px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:16px}
.card{display:flex;flex-direction:column;gap:10px;padding:20px;background:var(--card);border:1px solid var(--line);border-radius:20px;box-shadow:0 12px 34px rgba(30,38,72,.06)}
.card h3{margin:0;font-size:1.17rem}.card p{margin:0;color:var(--muted)}.links{display:flex;flex-wrap:wrap;gap:9px;margin-top:auto;padding-top:8px}
.links a{padding:9px 12px;border:1px solid var(--line);border-radius:999px;font-weight:750;white-space:nowrap}.links a.store{color:#fff;background:var(--accent);border-color:var(--accent)}
.footer{margin-top:42px;padding:26px 0;border-top:1px solid var(--line);color:var(--muted)}"""


def localized_summary(key, locale, pages=None):
    root = PAGES if pages is None else os.fspath(pages)
    path = os.path.join(root, locale, f"{key}.html")
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read(12000)
    except OSError:
        fallback = (
            SUMMARY_FALLBACKS.get(locale, {}).get(key)
            or SUMMARY_FALLBACKS.get(locale.split("-")[0], {}).get(key)
        )
        if fallback:
            return fallback.strip()
        if locale != "en-US":
            raise ValueError(
                f"Missing localized catalog summary: {locale}/{key}"
            )
        return (APPS[key].get("sub") or APPS[key].get("tag") or "").strip()
    match = re.search(
        r'<meta\s+name=["\']description["\']\s+content=(["\'])(.*?)\1',
        text,
        flags=re.I | re.S,
    )
    if not match:
        raise ValueError(f"Missing localized meta description: {locale}/{key}")
    return html.unescape(match.group(2)).strip()


def detail_url(key, locale):
    localized = os.path.join(PAGES, locale, f"{key}.html")
    if not os.path.exists(localized):
        return None
    return f"{SITE}/{locale}/{key}.html"


def catalog_urls():
    return [f"{SITE}/{config['path']}" for config in L10N.values()]


def sitemap_lastmods(path):
    if not os.path.isfile(path):
        return {}
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as error:
        raise ValueError(f"Invalid app catalog sitemap: {error}") from error
    if root.tag != f"{{{SITEMAP_NS}}}urlset":
        raise ValueError("App catalog sitemap must use a urlset root")
    lastmods = {}
    seen = set()
    expected = set(catalog_urls())
    for entry in root:
        if entry.tag.rsplit("}", 1)[-1] != "url":
            continue
        locs = [
            child
            for child in entry
            if child.tag.rsplit("}", 1)[-1] == "loc"
        ]
        dates = [
            child
            for child in entry
            if child.tag.rsplit("}", 1)[-1] == "lastmod"
        ]
        if len(locs) != 1 or len(dates) > 1:
            raise ValueError("Invalid app catalog sitemap entry")
        location = (locs[0].text or "").strip()
        if not location or location in seen:
            raise ValueError("Duplicate or empty app catalog sitemap URL")
        if location not in expected:
            raise ValueError(f"Unexpected app catalog sitemap URL: {location}")
        seen.add(location)
        if dates:
            value = (dates[0].text or "").strip()
            try:
                if not DATE_RE.fullmatch(value):
                    raise ValueError
                date.fromisoformat(value)
            except ValueError as error:
                raise ValueError(
                    f"Invalid app catalog sitemap lastmod: {value}"
                ) from error
            lastmods[location] = value
    return lastmods


def render_sitemap(lastmods):
    unknown = set(lastmods) - set(catalog_urls())
    if unknown:
        raise ValueError(f"Unexpected app catalog lastmod URLs: {sorted(unknown)}")
    rows = []
    for location in catalog_urls():
        lastmod = lastmods.get(location)
        suffix = f"<lastmod>{lastmod}</lastmod>" if lastmod else ""
        rows.append(f"  <url><loc>{location}</loc>{suffix}</url>")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<urlset xmlns="{SITEMAP_NS}">\n'
        + "\n".join(rows)
        + "\n</urlset>\n"
    )


def write_if_changed(path, content):
    try:
        with open(path, encoding="utf-8") as handle:
            if handle.read() == content:
                return False
    except OSError:
        pass
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return True


def render_catalog(code, live_keys):
    t = L10N[code]
    canonical = f"{SITE}/{t['path']}"
    page_id = f"{canonical}#webpage"
    item_list_id = f"{canonical}#apps"
    live_keys = set(live_keys)
    unknown = live_keys - set(APPS)
    if unknown:
        raise ValueError(f"Unknown live app keys: {sorted(unknown)}")
    groups = {}
    for key in APPS:
        if key in live_keys:
            groups.setdefault(APPS[key].get("category", "other"), []).append(key)

    sections = []
    item_list = []
    entity_ids = set()
    position = 0
    for category, keys in groups.items():
        cards = []
        for key in keys:
            position += 1
            app = APPS[key]
            app_id = APPSTORE[key]
            store = gen_mobile_app_identity.canonical_store_url(app_id)
            if store in entity_ids:
                raise ValueError(f"Duplicate catalog App Store identity: {store}")
            entity_ids.add(store)
            guide = detail_url(key, t["locale"])
            hub = f"{SITE}/hubs/{key}.html"
            summary = localized_summary(key, t["locale"])
            card_links = []
            if guide:
                card_links.append(
                    f'<a href="{html.escape(guide)}">'
                    f'{html.escape(t["guide"])}</a>'
                )
            if code == "en":
                card_links.append(
                    f'<a href="{html.escape(hub)}">'
                    f'{html.escape(t["hub"])}</a>'
                )
            card_links.append(
                f'<a class="store" href="{html.escape(store)}">'
                f'{html.escape(t["store"])}</a>'
            )
            cards.append(
                f'<article class="card" id="{html.escape(key)}"><h3>{html.escape(app["name"])}</h3>'
                f'<p>{html.escape(summary)}</p><div class="links">'
                f'{"".join(card_links)}'
                f'</div></article>'
            )
            app_entity = gen_mobile_app_identity.mobile_app_schema(
                app_id,
                app["name"],
                app.get("category", "other"),
            )
            app_entity.pop("@context")
            app_entity["isPartOf"] = {"@id": page_id}
            item_list.append({
                "@type": "ListItem",
                "@id": f"{canonical}#app-{key}",
                "position": position,
                "url": guide or store,
                "item": app_entity,
            })
        label = t["categories"].get(category, t["categories"]["other"])
        sections.append(f'<section><h2>{html.escape(label)}</h2><div class="grid">{"".join(cards)}</div></section>')

    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "@id": page_id,
        "name": t["title"],
        "url": canonical,
        "inLanguage": t["lang"],
        "mainEntity": {
            "@type": "ItemList",
            "@id": item_list_id,
            "numberOfItems": len(item_list),
            "itemListElement": item_list,
        },
    }
    alternates = "\n".join(
        f'<link rel="alternate" hreflang="{lang}" href="{SITE}/{data["path"]}">'
        for lang, data in L10N.items()
    )
    feed_discovery = (
        f"\n{gen_feed.feed_discovery_links()}" if code == "en" else ""
    )
    dir_attr = ' dir="rtl"' if t["lang"].startswith("ar") else ""
    return f'''<!DOCTYPE html>
<html lang="{t["lang"]}"{dir_attr}><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(t["title"])}</title><meta name="description" content="{html.escape(t["description"])}">
<link rel="canonical" href="{canonical}">
{alternates}
<link rel="alternate" hreflang="x-default" href="{SITE}/{L10N["en"]["path"]}">
<meta property="og:type" content="website"><meta property="og:title" content="{html.escape(t["title"])}">
<meta property="og:description" content="{html.escape(t["description"])}"><meta property="og:url" content="{canonical}">
<style>{CSS}</style><script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>{feed_discovery}
</head><body><main class="wrap"><header class="hero"><div class="eyebrow">Lumi Apps</div>
<h1>{html.escape(t["h1"])}</h1><p class="lead">{html.escape(t["lead"])}</p></header>
{"".join(sections)}</main><footer class="footer"><div class="wrap">{html.escape(t["description"])}</div></footer></body></html>'''


def main():
    live_keys = live_app_keys(APPSTORE, PAGES, refresh=False)
    changed = 0
    for code, config in L10N.items():
        path = os.path.join(PAGES, config["path"])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        content = render_catalog(code, live_keys)
        changed += int(write_if_changed(path, content))
    sitemap_path = os.path.join(PAGES, SITEMAP_NAME)
    changed += int(
        write_if_changed(
            sitemap_path,
            render_sitemap(sitemap_lastmods(sitemap_path)),
        )
    )
    print(
        f"✓ {len(L10N)} localized app catalogs · "
        f"{len(live_keys)} public apps · {changed} resources updated"
    )


if __name__ == "__main__":
    main()
