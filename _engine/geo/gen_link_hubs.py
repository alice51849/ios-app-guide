#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 sitemap-only 的孤兒頁接回站內連結圖(目標:全站 ≤3 次點擊可達)。

背景:2026-08-08 用 `geo/audit_link_depth.py` 量到 5.7 萬頁裡有 2.6 萬頁
「只存在於 sitemap,從首頁一次也點不到」。孤兒頁拿不到內部連結權重,搜尋引擎
會大幅降權——這是自有站台一個月只換到 18 次下載的結構性主因之一。

這支做三件事(全部冪等,可重複跑):
  1. 每個「內容父目錄」(50 個官方語系 + 內容區塊如 apps/answers/guides)產一張
     `browse.html` 索引,把該子樹的**每一頁**依區塊分組列出。
  2. 把 browse 索引與各區塊索引注入父目錄的 index.html(受管理區塊,會被取代)。
  3. 既有的區塊索引若沒列全同層頁面(例:`ja/answers/index.html` 只列了 73 /
     1633 頁),補一個「完整索引」受管理區塊。
  4. 首頁補上所有內容區塊入口。

刻意不處理的範圍:990 個 App Store 沒有商店的微語言目錄。那些頁已由
`gen_locale_indexation.py` 設成 noindex(停損),把它們接回連結圖只會浪費
爬取預算。稽核報告會把它們單獨列為「刻意去索引」。

    python geo/gen_link_hubs.py            # 產生
    python geo/gen_link_hubs.py --check    # 只檢查有無變更(CI 用)
"""
import argparse
import html
import os
import re
import sys

from official_locales import OFFICIAL_LOCALES

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.environ.get("GEO_PAGES", os.path.join(HERE, "pages"))
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")

SKIP_DIRS = {".git", "_engine", "assets", "node_modules", ".github", ".well-known"}
# 這些目錄是機器可讀端點(JSON/XML/feed),不是給人瀏覽的內容區塊。
NON_BROWSE_PARENTS = {
    "llms", "oembed", "opds", "resourcesync", "iiif", "media", "social",
    "publications",
}
BROWSE_BASENAME = "browse"
MAX_LINKS_PER_PAGE = 1200
# 讀整個 head 區。曾經只讀 4096 bytes,結果 <title> 落在邊界附近的頁面會
# 因為 head 多一條 hreflang 就被切掉、退回別的標題,排序位置跟著翻,兩次
# 發布之間永遠有幾十個檔案在互相覆蓋。
HEAD_BYTES = 262144

TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
LANG_RE = re.compile(r"<html[^>]*\blang=\"([^\"]+)\"", re.I)
NOINDEX_RE = re.compile(
    r"<meta[^>]+name\s*=\s*[\"']robots[\"'][^>]*content\s*=\s*[\"'][^\"']*noindex",
    re.I,
)
TAG_RE = re.compile(r"<[^>]+>")
HREF_RE = re.compile(r"<a\b[^>]*?\bhref\s*=\s*\"([^\"]*)\"", re.I)

NAV_BLOCK = re.compile(
    r"\n?<!--iag-link-hub-nav-->.*?<!--/iag-link-hub-nav-->\n?", re.S
)
FULL_BLOCK = re.compile(
    r"\n?<!--iag-link-hub-full-->.*?<!--/iag-link-hub-full-->\n?", re.S
)

# 區塊標題:只有沒有自己 index.html 的區塊才用得到(有 index 的直接沿用它的
# <title>,那才是真正在地化過的字)。沒有翻譯的語言退回英文,不硬掰。
SECTION_LABELS = {
    "best-for": {
        "en": "Best app for each need", "zh-Hant": "各種需求的最佳 App",
        "zh-Hans": "各种需求的最佳 App", "ja": "目的別のおすすめアプリ",
        "ko": "목적별 추천 앱", "de": "Beste App je Bedarf",
        "fr": "Meilleure app par besoin", "es": "Mejor app por necesidad",
        "pt": "Melhor app por necessidade", "it": "App migliore per esigenza",
        "ru": "Лучшее приложение по задаче", "nl": "Beste app per behoefte",
        "th": "แอปที่ดีที่สุดตามความต้องการ", "vi": "Ứng dụng tốt nhất theo nhu cầu",
        "id": "Aplikasi terbaik per kebutuhan", "ms": "Apl terbaik ikut keperluan",
        "tr": "İhtiyaca göre en iyi uygulama", "pl": "Najlepsza aplikacja do zadania",
        "ar": "أفضل تطبيق لكل حاجة",
    },
    "reviews": {
        "en": "Reviews", "zh-Hant": "評測", "zh-Hans": "评测", "ja": "レビュー",
        "ko": "리뷰", "de": "Testberichte", "fr": "Tests", "es": "Análisis",
        "pt": "Análises", "it": "Recensioni", "ru": "Обзоры", "nl": "Reviews",
        "th": "รีวิว", "vi": "Đánh giá", "id": "Ulasan", "ms": "Ulasan",
        "tr": "İncelemeler", "pl": "Recenzje", "ar": "مراجعات",
    },
    "seasonal": {
        "en": "Seasonal picks", "zh-Hant": "季節主題精選", "zh-Hans": "季节主题精选",
        "ja": "季節のおすすめ", "ko": "시즌 추천", "de": "Saisonale Auswahl",
        "fr": "Sélections saisonnières", "es": "Selección de temporada",
        "pt": "Seleção sazonal", "it": "Scelte stagionali", "ru": "Сезонная подборка",
        "nl": "Seizoensselectie", "th": "แนะนำตามฤดูกาล", "vi": "Gợi ý theo mùa",
        "id": "Pilihan musiman", "ms": "Pilihan bermusim", "tr": "Sezonluk seçkiler",
        "pl": "Wybory sezonowe", "ar": "اختيارات موسمية",
    },
    "vs": {
        "en": "Comparisons", "zh-Hant": "比較", "zh-Hans": "对比", "ja": "比較",
        "ko": "비교", "de": "Vergleiche", "fr": "Comparatifs", "es": "Comparativas",
        "pt": "Comparações", "it": "Confronti", "ru": "Сравнения",
        "nl": "Vergelijkingen", "th": "เปรียบเทียบ", "vi": "So sánh",
        "id": "Perbandingan", "ms": "Perbandingan", "tr": "Karşılaştırmalar",
        "pl": "Porównania", "ar": "مقارنات",
    },
    "workflow": {
        "en": "Workflows", "zh-Hant": "工作流程", "zh-Hans": "工作流程",
        "ja": "ワークフロー", "ko": "워크플로", "de": "Workflows",
        "fr": "Flux de travail", "es": "Flujos de trabajo", "pt": "Fluxos de trabalho",
        "it": "Flussi di lavoro", "ru": "Рабочие процессы", "nl": "Workflows",
        "th": "เวิร์กโฟลว์", "vi": "Quy trình", "id": "Alur kerja",
        "ms": "Aliran kerja", "tr": "İş akışları", "pl": "Przepływy pracy",
        "ar": "تدفقات العمل",
    },
    "problems": {
        "en": "Problems solved", "zh-Hant": "問題解法", "zh-Hans": "问题解法",
        "ja": "困りごとの解決", "ko": "문제 해결", "de": "Problemlösungen",
        "fr": "Problèmes résolus", "es": "Problemas resueltos",
        "pt": "Problemas resolvidos", "it": "Problemi risolti",
        "ru": "Решение проблем", "nl": "Problemen oplossen",
        "th": "แก้ปัญหา", "vi": "Giải quyết vấn đề", "id": "Solusi masalah",
        "ms": "Penyelesaian masalah", "tr": "Sorun çözümleri",
        "pl": "Rozwiązania problemów", "ar": "حلول المشكلات",
    },
    "persona": {
        "en": "Picks by who you are", "zh-Hant": "依身分推薦", "zh-Hans": "按身份推荐",
        "ja": "使う人別のおすすめ", "ko": "사용자별 추천", "de": "Empfehlungen nach Nutzertyp",
        "fr": "Sélections par profil", "es": "Selección por perfil",
        "pt": "Seleção por perfil", "it": "Scelte per profilo",
        "ru": "Подборки по профилю", "nl": "Selectie per profiel",
        "th": "แนะนำตามผู้ใช้", "vi": "Gợi ý theo người dùng",
        "id": "Pilihan per profil", "ms": "Pilihan ikut profil",
        "tr": "Profile göre seçkiler", "pl": "Wybory według profilu",
        "ar": "اختيارات حسب الملف",
    },
    "tutorials": {
        "en": "Tutorials", "zh-Hant": "教學", "zh-Hans": "教程", "ja": "チュートリアル",
        "ko": "튜토리얼", "de": "Anleitungen", "fr": "Tutoriels", "es": "Tutoriales",
        "pt": "Tutoriais", "it": "Tutorial", "ru": "Руководства", "nl": "Handleidingen",
        "th": "บทแนะนำ", "vi": "Hướng dẫn", "id": "Tutorial", "ms": "Tutorial",
        "tr": "Eğitimler", "pl": "Poradniki", "ar": "دروس",
    },
    "choose": {
        "en": "How to choose", "zh-Hant": "怎麼選", "zh-Hans": "怎么选",
        "ja": "選び方", "ko": "고르는 법", "de": "Wie man wählt",
        "fr": "Comment choisir", "es": "Cómo elegir", "pt": "Como escolher",
        "it": "Come scegliere", "ru": "Как выбрать", "nl": "Hoe kiezen",
        "th": "วิธีเลือก", "vi": "Cách chọn", "id": "Cara memilih",
        "ms": "Cara memilih", "tr": "Nasıl seçilir", "pl": "Jak wybrać",
        "ar": "كيف تختار",
    },
    "family": {
        "en": "For families", "zh-Hant": "家庭適用", "zh-Hans": "家庭适用",
        "ja": "家族向け", "ko": "가족용", "de": "Für Familien", "fr": "Pour les familles",
        "es": "Para familias", "pt": "Para famílias", "it": "Per famiglie",
        "ru": "Для семьи", "nl": "Voor gezinnen", "th": "สำหรับครอบครัว",
        "vi": "Cho gia đình", "id": "Untuk keluarga", "ms": "Untuk keluarga",
        "tr": "Aileler için", "pl": "Dla rodzin", "ar": "للعائلات",
    },
    "gifting": {
        "en": "Gifting", "zh-Hant": "送禮", "zh-Hans": "送礼", "ja": "ギフト",
        "ko": "선물하기", "de": "Verschenken", "fr": "Offrir", "es": "Regalar",
        "pt": "Presentear", "it": "Regalare", "ru": "Подарки", "nl": "Cadeau geven",
        "th": "ของขวัญ", "vi": "Quà tặng", "id": "Hadiah", "ms": "Hadiah",
        "tr": "Hediye etme", "pl": "Prezenty", "ar": "الإهداء",
    },
    "no-account": {
        "en": "No account needed", "zh-Hant": "免註冊帳號", "zh-Hans": "免注册账号",
        "ja": "アカウント不要", "ko": "계정 없이 사용", "de": "Ohne Konto",
        "fr": "Sans compte", "es": "Sin cuenta", "pt": "Sem conta",
        "it": "Senza account", "ru": "Без аккаунта", "nl": "Zonder account",
        "th": "ไม่ต้องมีบัญชี", "vi": "Không cần tài khoản", "id": "Tanpa akun",
        "ms": "Tanpa akaun", "tr": "Hesapsız", "pl": "Bez konta",
        "ar": "بدون حساب",
    },
    "pay-once": {
        "en": "Pay once", "zh-Hant": "一次買斷", "zh-Hans": "一次买断",
        "ja": "買い切り", "ko": "한 번 결제", "de": "Einmalkauf",
        "fr": "Achat unique", "es": "Pago único", "pt": "Compra única",
        "it": "Acquisto unico", "ru": "Разовая покупка", "nl": "Eenmalige aankoop",
        "th": "จ่ายครั้งเดียว", "vi": "Trả một lần", "id": "Bayar sekali",
        "ms": "Bayar sekali", "tr": "Tek seferlik ödeme", "pl": "Jednorazowa płatność",
        "ar": "دفعة واحدة",
    },
    "switching": {
        "en": "Switching apps", "zh-Hant": "換 App 指南", "zh-Hans": "换 App 指南",
        "ja": "乗り換えガイド", "ko": "앱 갈아타기", "de": "App-Wechsel",
        "fr": "Changer d'app", "es": "Cambiar de app", "pt": "Trocar de app",
        "it": "Cambiare app", "ru": "Переход на другое приложение",
        "nl": "Overstappen", "th": "ย้ายแอป", "vi": "Chuyển ứng dụng",
        "id": "Pindah aplikasi", "ms": "Tukar apl", "tr": "Uygulama değiştirme",
        "pl": "Zmiana aplikacji", "ar": "تبديل التطبيقات",
    },
    "visuals": {
        "en": "Visual explainers", "zh-Hant": "圖解", "zh-Hans": "图解",
        "ja": "図解", "ko": "그림 설명", "de": "Visuelle Erklärungen",
        "fr": "Explications visuelles", "es": "Explicaciones visuales",
        "pt": "Explicações visuais", "it": "Spiegazioni visive",
        "ru": "Наглядные разборы", "nl": "Visuele uitleg", "th": "อินโฟกราฟิก",
        "vi": "Giải thích trực quan", "id": "Penjelasan visual",
        "ms": "Penjelasan visual", "tr": "Görsel anlatımlar",
        "pl": "Objaśnienia wizualne", "ar": "شروح مرئية",
    },
    "": {
        "en": "Main pages", "zh-Hant": "主要頁面", "zh-Hans": "主要页面",
        "ja": "主なページ", "ko": "주요 페이지", "de": "Hauptseiten",
        "fr": "Pages principales", "es": "Páginas principales",
        "pt": "Páginas principais", "it": "Pagine principali",
        "ru": "Основные страницы", "nl": "Hoofdpagina's", "th": "หน้าหลัก",
        "vi": "Trang chính", "id": "Halaman utama", "ms": "Halaman utama",
        "tr": "Ana sayfalar", "pl": "Strony główne", "ar": "الصفحات الرئيسية",
    },
}

UI = {
    "browse_title": {
        "en": "All pages", "zh-Hant": "全部頁面", "zh-Hans": "全部页面",
        "ja": "全ページ一覧", "ko": "전체 페이지", "de": "Alle Seiten",
        "fr": "Toutes les pages", "es": "Todas las páginas",
        "pt": "Todas as páginas", "it": "Tutte le pagine", "ru": "Все страницы",
        "nl": "Alle pagina's", "th": "ทุกหน้า", "vi": "Tất cả trang",
        "id": "Semua halaman", "ms": "Semua halaman", "tr": "Tüm sayfalar",
        "pl": "Wszystkie strony", "ar": "كل الصفحات",
    },
    "browse_lead": {
        "en": "Every page in this section, grouped by topic.",
        "zh-Hant": "本區所有頁面,依主題分組。",
        "zh-Hans": "本区所有页面,按主题分组。",
        "ja": "このセクションの全ページをテーマ別にまとめています。",
        "ko": "이 섹션의 모든 페이지를 주제별로 정리했습니다.",
        "de": "Alle Seiten dieses Bereichs, nach Thema gruppiert.",
        "fr": "Toutes les pages de cette section, regroupées par thème.",
        "es": "Todas las páginas de esta sección, agrupadas por tema.",
        "pt": "Todas as páginas desta secção, agrupadas por tema.",
        "it": "Tutte le pagine di questa sezione, raggruppate per tema.",
        "ru": "Все страницы этого раздела, сгруппированные по темам.",
        "nl": "Alle pagina's in dit onderdeel, gegroepeerd per thema.",
        "th": "ทุกหน้าในส่วนนี้ จัดกลุ่มตามหัวข้อ",
        "vi": "Tất cả trang trong mục này, nhóm theo chủ đề.",
        "id": "Semua halaman di bagian ini, dikelompokkan per topik.",
        "ms": "Semua halaman dalam bahagian ini, dikumpulkan mengikut topik.",
        "tr": "Bu bölümdeki tüm sayfalar, konuya göre gruplanmış.",
        "pl": "Wszystkie strony w tej sekcji, pogrupowane tematycznie.",
        "ar": "كل صفحات هذا القسم مُجمَّعة حسب الموضوع.",
    },
    "full_index": {
        "en": "Complete index", "zh-Hant": "完整索引", "zh-Hans": "完整索引",
        "ja": "全件インデックス", "ko": "전체 색인", "de": "Vollständiges Verzeichnis",
        "fr": "Index complet", "es": "Índice completo", "pt": "Índice completo",
        "it": "Indice completo", "ru": "Полный указатель", "nl": "Volledige index",
        "th": "ดัชนีทั้งหมด", "vi": "Mục lục đầy đủ", "id": "Indeks lengkap",
        "ms": "Indeks penuh", "tr": "Tam dizin", "pl": "Pełny indeks",
        "ar": "الفهرس الكامل",
    },
    "more_pages": {
        "en": "More pages", "zh-Hant": "更多頁面", "zh-Hans": "更多页面",
        "ja": "さらにページを見る", "ko": "더 많은 페이지", "de": "Weitere Seiten",
        "fr": "Plus de pages", "es": "Más páginas", "pt": "Mais páginas",
        "it": "Altre pagine", "ru": "Ещё страницы", "nl": "Meer pagina's",
        "th": "หน้าอื่น ๆ", "vi": "Thêm trang", "id": "Halaman lainnya",
        "ms": "Halaman lain", "tr": "Diğer sayfalar", "pl": "Więcej stron",
        "ar": "صفحات أخرى",
    },
}

RTL_LANGS = {"ar", "he", "fa", "ur"}

STYLE = (
    "<style>body{font:16px/1.6 -apple-system,BlinkMacSystemFont,'Segoe UI',"
    "Roboto,sans-serif;margin:0;background:#fbf9f4;color:#20242c}"
    "main{max-width:900px;margin:0 auto;padding:24px 18px 64px}"
    "h1{font-size:1.6rem;margin:.2em 0}h2{font-size:1.1rem;margin:1.8em 0 .4em;"
    "padding-top:.6em;border-top:1px solid #e6e0d4}"
    "p.lead{color:#5c6270}ul{margin:.2em 0 0;padding-left:1.1em}"
    "li{margin:.18em 0}a{color:#1f5fbf}nav.up{margin-bottom:1em;font-size:.95rem}"
    "</style>"
)


def base_lang(locale):
    return locale.split("-")[0]


def pick(table, locale):
    return (
        table.get(locale)
        or table.get(base_lang(locale))
        or table["en"]
    )


def section_label(section, locale):
    labels = SECTION_LABELS.get(section)
    if labels:
        return pick(labels, locale)
    return section.replace("-", " ").replace("_", " ").strip().capitalize()


def read_head(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read(HEAD_BYTES)
    except OSError:
        return ""


def page_title(path, fallback):
    head = read_head(path)
    for regex in (TITLE_RE, H1_RE):
        match = regex.search(head)
        if match:
            text = html.unescape(TAG_RE.sub("", match.group(1))).strip()
            text = re.sub(r"\s+", " ", text)
            text = re.split(r"\s+[|｜]\s+", text)[0].strip()
            if text:
                return text[:140]
    return fallback


def slug_title(rel):
    stem = os.path.splitext(os.path.basename(rel))[0]
    if stem == "index":
        stem = os.path.basename(os.path.dirname(rel)) or "index"
    return stem.replace("-", " ").replace("_", " ").strip()


def html_files(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(".html"):
                out.append(os.path.join(dirpath, name))
    return out


def is_noindex(path):
    return bool(NOINDEX_RE.search(read_head(path)))


def detect_lang(path, default="en"):
    match = LANG_RE.search(read_head(path))
    return match.group(1) if match else default


def parent_dirs():
    """回傳 [(dir_name, locale)],只含官方語系與內容區塊;微語言目錄跳過。"""
    official = set(OFFICIAL_LOCALES)
    out = []
    for name in sorted(os.listdir(PAGES)):
        path = os.path.join(PAGES, name)
        if not os.path.isdir(path) or name in SKIP_DIRS or name.startswith("."):
            continue
        if name in NON_BROWSE_PARENTS:
            continue
        # 一定要排序:os.walk 的檔名順序是不保證的,拿「第一個檔案」去判語言
        # 會讓同一份輸入每次產出不同結果,兩支產生器就會永遠互相翻頁。
        files = sorted(html_files(path))
        if len(files) < 2:
            continue
        if name in official:
            out.append((name, name))
            continue
        sample = files[: min(8, len(files))]
        index = os.path.join(path, "index.html")
        lang = detect_lang(index if os.path.exists(index) else sample[0])
        # 刻意 noindex 的微語言叢集不接回連結圖:那 990 個語言在 App Store 沒有
        # 商店,已由 gen_locale_indexation.py 停損,再花爬取預算反而有害。
        if sum(1 for p in sample if is_noindex(p)) >= max(1, len(sample) * 4 // 5):
            continue
        out.append((name, lang if lang else "en"))
    return out


def group_of(rel):
    parts = rel.split("/")
    return parts[0] if len(parts) > 1 else ""


def link_list(entries, base_dir):
    rows = []
    for rel, title in entries:
        href = f"{SITE}/{base_dir}/{rel}" if base_dir else f"{SITE}/{rel}"
        rows.append(
            f'    <li><a href="{html.escape(href, quote=True)}">'
            f"{html.escape(title)}</a></li>"
        )
    return "\n".join(rows)


def render_browse(parent, locale, groups, page_no, page_urls, parent_index_url):
    e = html.escape
    lang = locale or "en"
    dir_attr = ' dir="rtl"' if base_lang(lang) in RTL_LANGS else ""
    title = pick(UI["browse_title"], lang)
    lead = pick(UI["browse_lead"], lang)
    suffix = f" ({page_no})" if page_no > 1 else ""
    canonical = page_urls[page_no - 1]
    body = []
    for section, entries in groups:
        body.append(f"  <h2>{e(section_label(section, lang))}</h2>")
        body.append("  <ul>")
        body.append(link_list(entries, parent))
        body.append("  </ul>")
    pager = ""
    if len(page_urls) > 1:
        links = "\n".join(
            f'    <li><a href="{e(url, quote=True)}">{i + 1}</a></li>'
            for i, url in enumerate(page_urls)
            if i + 1 != page_no
        )
        pager = (
            f'  <h2>{e(pick(UI["more_pages"], lang))}</h2>\n'
            f"  <ul>\n{links}\n  </ul>\n"
        )
    up = (
        f'  <nav class="up"><a href="{e(parent_index_url, quote=True)}">'
        f"&larr; {e(title)}</a></nav>\n"
        if parent_index_url
        else ""
    )
    return (
        f'<!DOCTYPE html>\n<html lang="{e(lang)}"{dir_attr}><head>'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{e(title)}{e(suffix)} | iOS</title>\n"
        f'<meta name="description" content="{e(lead)}">\n'
        f'<link rel="canonical" href="{e(canonical, quote=True)}">\n'
        f"{STYLE}\n</head><body><main>\n"
        f"{up}"
        f"  <h1>{e(title)}{e(suffix)}</h1>\n"
        f'  <p class="lead">{e(lead)}</p>\n'
        + "\n".join(body)
        + f"\n{pager}</main></body></html>\n"
    )


def write_if_changed(path, content, state):
    old = None
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            old = fh.read()
    if old == content:
        return False
    state["changed"].append(os.path.relpath(path, PAGES))
    if not state["check"]:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
    return True


def splice(source, block):
    """把受管理區塊接在 </main> 正後方。

    兩個限制同時要滿足:
    1. **不能插進 <main> 裡面**——站上有 5 支以上的產生器拿
       "</section></main>" 這種完全比對字串當錨點(demand_tools.py 的
       tools/index.html grid marker),切開它整條發布管線就掛掉。
    2. **不能用「</body> 之前」當錨點**——gen_webmcp_install_tools /
       gen_mobile_store_ctas / gen_app_store_share_ctas / gen_store_reach
       都插在 </body> 前,而且跑在我們之後。用同一個錨點的話,每跑一次雙方
       的先後就對調一次,永遠不會收斂(2026-08-08 量到 597 個檔案在互相翻)。
    接在 </main> 後面則是固定位置:別人插在更後面,不影響我們的落點。
    """
    idx = source.rfind("</main>")
    if idx != -1:
        cut = idx + len("</main>")
        return source[:cut] + block + source[cut:]
    idx = source.rfind("</body>")
    if idx == -1:
        return source + block
    return source[:idx] + block + source[idx:]


def inject(path, block_re, block, state):
    """把受管理區塊塞在 </main>(或 </body>)之前,冪等取代。"""
    if not os.path.exists(path):
        return False
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        source = fh.read()
    cleaned = block_re.sub("", source)
    if not block:
        return write_if_changed(path, cleaned, state)
    return write_if_changed(path, splice(cleaned, block), state)


def nav_block(locale, links, extra=""):
    """父目錄 index 的受管理區塊。導覽與完整索引合成**同一塊**,不能拆成兩塊
    分別注入——兩塊都插在 </main> 前會每跑一次就互換順序,永遠不會收斂。"""
    e = html.escape
    rows = "\n".join(
        f'  <li><a href="{e(url, quote=True)}">{e(text)}</a></li>'
        for url, text in links
    )
    nav = (
        '<nav class="wrap link-hub-nav" aria-label="'
        f'{e(pick(UI["browse_title"], locale))}">\n'
        f"<ul>\n{rows}\n</ul>\n</nav>\n"
        if links
        else ""
    )
    if not nav and not extra:
        return ""
    return "\n<!--iag-link-hub-nav-->\n" + nav + extra + "<!--/iag-link-hub-nav-->\n"


def full_section(locale, entries, base_dir):
    e = html.escape
    return (
        '<section class="wrap link-hub-full">\n'
        f'<h2>{e(pick(UI["full_index"], locale))}</h2>\n'
        "<ul>\n" + link_list(entries, base_dir) + "\n</ul>\n"
        "</section>\n"
    )


def full_block(locale, entries, base_dir):
    return (
        "\n<!--iag-link-hub-full-->\n"
        + full_section(locale, entries, base_dir)
        + "<!--/iag-link-hub-full-->\n"
    )


def linked_targets(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        source = fh.read()
    # 一定要先拿掉自己上一輪注入的區塊,否則第二次跑會誤判「已經連過了」而把
    # 連結整批抽掉(2026-08-08 踩過:可達頁數從 52.9k 掉回 39.5k)。
    source = FULL_BLOCK.sub("", NAV_BLOCK.sub("", source))
    out = set()
    for raw in HREF_RE.findall(source):
        raw = html.unescape(raw)
        if raw.startswith(SITE + "/"):
            out.add(raw[len(SITE) + 1:])
        elif not raw.startswith(("http", "#", "mailto:", "/")):
            out.add(raw)
    return out


def process_parent(name, locale, state):
    root = os.path.join(PAGES, name)
    parent_index = os.path.join(root, "index.html")
    has_index = os.path.exists(parent_index)

    files = sorted(html_files(root))
    entries = []
    for path in files:
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        if rel == "index.html" or rel.startswith(BROWSE_BASENAME + "."):
            continue
        if re.fullmatch(rf"{BROWSE_BASENAME}-\d+\.html", rel):
            continue
        entries.append((rel, path))
    if not entries:
        return

    # 父目錄 index 已經直接列出幾乎全部子頁時(例:answers/index.html 列了
    # 1731 頁),再產一份 browse 只是重複內容,跳過。
    skip_browse = False
    if has_index:
        already_root = linked_targets(parent_index)
        hit = sum(
            1
            for rel, _ in entries
            if rel in already_root
            or f"{name}/{rel}" in already_root
            or rel.split("/")[-1] in already_root
        )
        skip_browse = hit * 20 >= len(entries) * 19

    groups = {}
    for rel, path in entries:
        groups.setdefault(group_of(rel), []).append(
            (rel, page_title(path, slug_title(rel)))
        )
    for values in groups.values():
        # 次要鍵一定要放 rel:站上有上百頁共用「Guide moved」這種標題,
        # 只用標題排序時同分項的先後不穩定。
        values.sort(key=lambda item: (item[1].lower(), item[0]))
    ordered = sorted(groups.items(), key=lambda kv: (kv[0] != "", kv[0]))

    # 分頁:確保每頁連結數可控,且每一頁都互相連結(全部維持深度 2)。
    flat = [(section, item) for section, items in ordered for item in items]
    pages_count = max(1, -(-len(flat) // MAX_LINKS_PER_PAGE))
    base_name = BROWSE_BASENAME if has_index else "index"
    page_urls = []
    for i in range(pages_count):
        fname = (
            f"{base_name}.html" if i == 0 else f"{BROWSE_BASENAME}-{i + 1}.html"
        )
        page_urls.append(f"{SITE}/{name}/{fname}")
    parent_index_url = f"{SITE}/{name}/index.html" if has_index else ""

    for i in range(pages_count if not skip_browse else 0):
        chunk = flat[i * MAX_LINKS_PER_PAGE:(i + 1) * MAX_LINKS_PER_PAGE]
        chunk_groups = []
        for section, item in chunk:
            if not chunk_groups or chunk_groups[-1][0] != section:
                chunk_groups.append((section, []))
            chunk_groups[-1][1].append(item)
        fname = (
            f"{base_name}.html" if i == 0 else f"{BROWSE_BASENAME}-{i + 1}.html"
        )
        write_if_changed(
            os.path.join(root, fname),
            render_browse(
                name, locale, chunk_groups, i + 1, page_urls, parent_index_url
            ),
            state,
        )

    # 父目錄 index.html:連到 browse 索引 + 每個區塊自己的 index。
    if has_index:
        links = []
        if not skip_browse:
            for i, url in enumerate(page_urls):
                label = pick(UI["browse_title"], locale)
                links.append((url, label if i == 0 else f"{label} ({i + 1})"))
        for section, _ in ordered:
            if not section:
                continue
            sec_index = os.path.join(root, section, "index.html")
            if os.path.exists(sec_index):
                links.append((
                    f"{SITE}/{name}/{section}/index.html",
                    page_title(sec_index, section_label(section, locale)),
                ))
        # 沒產 browse(index 已列近全部)時,把漏掉的那幾頁補進完整索引。
        extra = ""
        if skip_browse:
            missing = [
                (rel, title)
                for section, items in ordered
                for rel, title in items
                if rel not in already_root
                and f"{name}/{rel}" not in already_root
                and rel.split("/")[-1] not in already_root
            ]
            if missing:
                extra = full_section(locale, missing, name)
        inject(parent_index, FULL_BLOCK, "", state)  # 清掉舊版獨立區塊
        inject(parent_index, NAV_BLOCK, nav_block(locale, links, extra), state)

    # 區塊已有 index 但沒列全同層頁面時(例:ja/answers 只列 73/1633),補完整索引。
    for section, items in ordered:
        if not section or len(items) < 20:
            continue
        sec_index = os.path.join(root, section, "index.html")
        if not os.path.exists(sec_index):
            continue
        with open(sec_index, "r", encoding="utf-8", errors="ignore") as fh:
            body = FULL_BLOCK.sub("", fh.read())
        already = set()
        for raw in HREF_RE.findall(body):
            raw = html.unescape(raw)
            target = (
                raw[len(SITE) + 1:] if raw.startswith(SITE + "/") else raw
            )
            already.add(target)
            already.add(target.split("/")[-1])
        missing = [
            (rel, title)
            for rel, title in items
            if rel not in already
            and f"{name}/{rel}" not in already
            and rel.split("/")[-1] not in already
        ]
        if len(missing) * 5 < len(items):  # 已列出 ≥80%,不必再補
            inject(sec_index, FULL_BLOCK, "", state)
            continue
        inject(sec_index, FULL_BLOCK, full_block(locale, missing, name), state)


def process_root(parents, state):
    root_index = os.path.join(PAGES, "index.html")
    if not os.path.exists(root_index):
        return
    already = linked_targets(root_index)
    links = []
    for name, locale in parents:
        for candidate in ("index.html", "browse.html"):
            path = os.path.join(PAGES, name, candidate)
            if not os.path.exists(path):
                continue
            rel = f"{name}/{candidate}"
            if rel in already and candidate == "index.html":
                break
            links.append((
                f"{SITE}/{rel}",
                page_title(path, name.replace("-", " ")),
            ))
            break
    # 根目錄下的單頁(find-app.html 之類)也要有入口,否則永遠是孤兒。
    for name in sorted(os.listdir(PAGES)):
        if not name.endswith(".html") or name == "index.html":
            continue
        if name in already:
            continue
        path = os.path.join(PAGES, name)
        if is_noindex(path):
            continue
        links.append((f"{SITE}/{name}", page_title(path, slug_title(name))))
    if not links:
        inject(root_index, NAV_BLOCK, "", state)
        return
    inject(root_index, NAV_BLOCK, nav_block("en", links), state)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只回報會改什麼")
    args = parser.parse_args()
    state = {"check": args.check, "changed": []}

    parents = parent_dirs()
    for name, locale in parents:
        process_parent(name, locale, state)
    process_root(parents, state)

    print(
        f"link hubs: {len(parents)} 個父目錄, "
        f"{len(state['changed'])} 個檔案{'需更新' if args.check else '已更新'}"
    )
    if args.check and state["changed"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
