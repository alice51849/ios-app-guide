#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""App 頁 → 該 App 的 answers / guides 內部連結(每頁 3–8 條)。

問題:`<locale>/<app>.html` 只連到自己的其他語系版本,是死路一條。全站
2.5 萬頁 answers 拿不到任何來自 App 頁的連結權重,App 頁也沒有把讀者導向
「回答他真正問題」的那一頁。

歸屬判定不用猜:answers/guides 頁的 CTA 已經帶著該 App 的 App Store ID,
直接用 ID 對應,不會把 B App 的內容掛到 A App 頁上。

**只加站內連結,絕不加 apps.apple.com 連結** —— gen_smart_app_banners 與
publisher_intent_catalog 都靠「一頁只有一個 App Store ID」判定頁面身份,
多塞一個商店連結會讓那些頁掉出 Smart App Banner。

    python geo/gen_app_page_related.py
    python geo/gen_app_page_related.py --check
"""
import argparse
import html
import os
import re
import sys

from official_locales import OFFICIAL_LOCALES
from site_config import PUBLIC_SITE  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.environ.get("GEO_PAGES", os.path.join(HERE, "pages"))
SITE = os.environ.get(
    "GEO_SITE", PUBLIC_SITE
).rstrip("/")

MAX_LINKS = 8
MIN_LINKS = 3
BLOCK = re.compile(
    r"\n?<!--iag-app-related-->.*?<!--/iag-app-related-->\n?", re.S
)
APP_ID_RE = re.compile(r"apps\.apple\.com/(?:[a-z]{2}/)?app/(?:[^/]+/)?id(\d+)")
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
H1_RE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
HREF_RE = re.compile(r"<a\b[^>]*?\bhref\s*=\s*\"([^\"]*)\"", re.I)
WORD_RE = re.compile(r"[0-9a-z]+", re.I)

STOP = set(
    "a an the and or of to in for on at by as it this that with your you my is "
    "are can app apps iphone ios free best what when should how do i vs no not "
    "without pay once app-store".split()
)

# App 頁 → 該款支援頁(外宣十倍令第 5 條;表的正本是 support_network/support_xlinks.py
# GUIDE_APPS/TARGETS,兩邊一起改)。檔名 → (App Store ID, 支援頁, {語系: 支援頁});
# 連結帶 ?ct=sup_<款>_xlink(agent/ct_codes.py sup_ 家族),只放站內支援頁、不放商店連結。
SUPPORT_HOST = "https://open.cait518.cc"
SUPPORT_PAGES = {
    "mochi": ("6785004775", "mochi", "/mochitodo-support/",
              {"zh-Hant": "/mochitodo-support/zh-Hant/", "id": "/mochitodo-support/id/"}),
    "lumiweather": ("6779552704", "lumiweather", "/lumi-weather-support/",
                    {"zh-Hant": "/lumi-weather-support/zh-Hant/"}),
    "battai": ("6802423998", "battai", "/battai-support/", {}),
    "cyca": ("6782251621", "cyca", "/cyca-support/", {}),
    "dailymate": ("6790418321", "dailymate", "/dailymate-support/", {}),
    "lockhour": ("6780107485", "lockhour", "/lockhour-support/", {}),
    "moneytag": ("6801956402", "moneytag", "/moneytag-support/", {}),
    "hourstag": ("6754218117", "hourstag", "/hourstag-support/", {}),
    "gmoney": ("6755782939", "gmoney", "/gmoney-support/", {}),
    "claudeusagemini": ("6818607603", "usagenow", "/usagenow-support/",
                        {"ja": "/usagenow-support/ja/support.html"}),
}
SUPPORT_BLOCK = re.compile(
    r"\n?<!--iag-app-support-->.*?<!--/iag-app-support-->\n?", re.S
)
SUPPORT_LABEL = {
    "en": "Help & FAQ for this app",
    "zh-Hant": "這款 App 的說明與常見問題",
    "zh-Hans": "这款 App 的说明与常见问题",
    "ja": "このアプリのサポートとよくある質問",
    "ko": "이 앱의 도움말 및 자주 묻는 질문",
    "de": "Hilfe und FAQ zu dieser App",
    "fr": "Aide et FAQ de cette app",
    "es": "Ayuda y preguntas frecuentes de esta app",
    "pt": "Ajuda e perguntas frequentes desta app",
    "it": "Assistenza e FAQ di questa app",
    "ru": "Справка и вопросы об этом приложении",
    "nl": "Hulp en veelgestelde vragen over deze app",
    "th": "ความช่วยเหลือและคำถามที่พบบ่อยของแอปนี้",
    "vi": "Trợ giúp và câu hỏi thường gặp của ứng dụng này",
    "id": "Bantuan dan FAQ aplikasi ini",
    "ms": "Bantuan dan soalan lazim apl ini",
    "tr": "Bu uygulama için yardım ve SSS",
    "pl": "Pomoc i FAQ tej aplikacji",
    "ar": "المساعدة والأسئلة الشائعة لهذا التطبيق",
}

HEADING = {
    "en": "Answers about this app",
    "zh-Hant": "關於這款 App 的問答",
    "zh-Hans": "关于这款 App 的问答",
    "ja": "このアプリに関する疑問と答え",
    "ko": "이 앱에 대한 질문과 답",
    "de": "Antworten zu dieser App",
    "fr": "Questions fréquentes sur cette app",
    "es": "Respuestas sobre esta app",
    "pt": "Respostas sobre esta app",
    "it": "Risposte su questa app",
    "ru": "Ответы об этом приложении",
    "nl": "Antwoorden over deze app",
    "th": "คำถามที่พบบ่อยเกี่ยวกับแอปนี้",
    "vi": "Giải đáp về ứng dụng này",
    "id": "Jawaban seputar aplikasi ini",
    "ms": "Jawapan tentang apl ini",
    "tr": "Bu uygulama hakkında yanıtlar",
    "pl": "Odpowiedzi o tej aplikacji",
    "ar": "أسئلة وأجوبة عن هذا التطبيق",
}


def read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return ""


def text_of(source, regex):
    match = regex.search(source)
    if not match:
        return ""
    value = html.unescape(TAG_RE.sub("", match.group(1))).strip()
    value = re.sub(r"\s+", " ", value)
    return re.split(r"\s+[|｜]\s+", value)[0].strip()


def tokens(text):
    return {w.lower() for w in WORD_RE.findall(text) if w.lower() not in STOP}


def app_ids(source):
    return set(APP_ID_RE.findall(source))


def primary_app_id(source):
    """頁面的主 App = 出現次數最多的 App Store ID(平手取小的)。

    不能用「剛好只有一個 ID 才算數」:gen_store_reach / gen_store_attribution
    跑在後面,會替某些頁補上第二個商店連結,那條規則會讓同一頁在兩次發布之間
    一下算數、一下不算數,產出的相關連結就跟著加了又刪(2026-08-08 量到 7 頁
    在互翻)。取最高票的 ID 對「多一條次要連結」免疫。
    """
    ids = APP_ID_RE.findall(source)
    if not ids:
        return None
    counts = {}
    for value in ids:
        counts[value] = counts.get(value, 0) + 1
    return min(counts, key=lambda k: (-counts[k], int(k)))


def base_lang(locale):
    return locale.split("-")[0]


def heading_for(locale):
    return (
        HEADING.get(locale) or HEADING.get(base_lang(locale)) or HEADING["en"]
    )


def collect(locale):
    """回傳 {app_id: [(url, title, tokens)]},來源是該語系的 answers 與 guides。"""
    out = {}
    for section in ("answers", "guides"):
        folder = os.path.join(PAGES, locale, section)
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            if not name.endswith(".html") or name == "index.html":
                continue
            path = os.path.join(folder, name)
            source = read(path)
            app_id = primary_app_id(source)
            if not app_id:
                continue
            title = text_of(source, H1_RE) or text_of(source, TITLE_RE)
            if not title:
                continue
            url = f"{SITE}/{locale}/{section}/{name}"
            out.setdefault(app_id, []).append((url, title, tokens(title)))
    return out


def build_block(locale, entries):
    e = html.escape
    rows = "\n".join(
        f'  <li><a href="{e(url, quote=True)}">{e(title)}</a></li>'
        for url, title in entries
    )
    return (
        "\n<!--iag-app-related-->\n"
        '<section class="wrap app-related">\n'
        f"<h2>{e(heading_for(locale))}</h2>\n"
        f"<ul>\n{rows}\n</ul>\n</section>\n"
        "<!--/iag-app-related-->\n"
    )


def write_block(path, block, state):
    source = read(path)
    if not source:
        return
    cleaned = BLOCK.sub("", source)
    merged = cleaned
    if block:
        # 錨點必須是「</main> 正後方」。插進 main 內部會切斷別的產生器用來
        # 定位的 "</section></main>" 字串;插在 </body> 前又會跟同樣插在
        # </body> 前、而且跑在我們之後的 gen_webmcp_install_tools /
        # gen_mobile_store_ctas / gen_app_store_share_ctas 每輪互換順序,
        # 造成 597 個檔案永遠在翻(2026-08-08 量到)。
        idx = cleaned.rfind("</main>")
        if idx != -1:
            cut = idx + len("</main>")
            merged = cleaned[:cut] + block + cleaned[cut:]
        else:
            idx = cleaned.rfind("</body>")
            merged = (
                cleaned[:idx] + block + cleaned[idx:]
                if idx != -1
                else cleaned + block
            )
    if merged == source:
        return
    state["changed"].append(os.path.relpath(path, PAGES))
    if not state["check"]:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(merged)


def support_block(locale, name, source):
    """<語系>/<款>.html 的支援頁連結;不在表上、或頁面主 App 不是那一款就回空字串(清掉舊的)。"""
    row = SUPPORT_PAGES.get(name[: -len(".html")])
    if not row or primary_app_id(source) != row[0]:
        return ""
    _app_id, key, path, by_locale = row
    path = by_locale.get(locale) or path
    url = f"{SUPPORT_HOST}{path}?ct=sup_{key}_xlink"
    label = (
        SUPPORT_LABEL.get(locale)
        or SUPPORT_LABEL.get(base_lang(locale))
        or SUPPORT_LABEL["en"]
    )
    rtl = ' dir="rtl"' if base_lang(locale) in ("ar", "he", "fa", "ur") else ""
    e = html.escape
    return (
        "\n<!--iag-app-support-->\n"
        f'<p class="wrap app-support"{rtl}><a href="{e(url, quote=True)}" '
        f'data-ls-xlink="{key}">{e(label)}</a></p>\n'
        "<!--/iag-app-support-->\n"
    )


def write_support(path, block, state):
    """支援頁連結放在相關問答區塊正後方(沒有就 </main> 正後方)。

    跟 write_block 同一個錨點家族、固定在它後面:write_block 拿掉自己的區塊再插回 </main>
    後方時,本區塊仍在它後面,兩支每輪輸出一致,不會互翻。
    """
    source = read(path)
    if not source:
        return
    cleaned = SUPPORT_BLOCK.sub("", source)
    merged = cleaned
    if block:
        end = cleaned.rfind("<!--/iag-app-related-->")
        if end != -1:
            cut = end + len("<!--/iag-app-related-->")
            if cleaned[cut:cut + 1] == "\n":
                cut += 1
        else:
            idx = cleaned.rfind("</main>")
            cut = idx + len("</main>") if idx != -1 else -1
        if cut == -1:
            idx = cleaned.rfind("</body>")
            cut = idx if idx != -1 else len(cleaned)
        merged = cleaned[:cut] + block + cleaned[cut:]
    if merged == source:
        return
    rel = os.path.relpath(path, PAGES)
    if rel not in state["changed"]:
        state["changed"].append(rel)
    if not state["check"]:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(merged)


def pick_related(source, url_self, pool, limit):
    seed = tokens(
        text_of(source, TITLE_RE) + " " + text_of(source, H1_RE)
    )
    # 刻意**不**排除「頁面上已經連過的 URL」:那個集合會被跑在後面的
    # gen_store_reach / gen_store_attribution 等產生器改動,拿它當輸入會讓
    # 這裡每輪選出不同的 3–8 條,兩支產生器互相翻頁永遠不收斂。多一條重複
    # 連結沒有壞處,不穩定才有。
    scored = []
    for url, title, toks in pool:
        if url == url_self:
            continue
        scored.append((len(seed & toks), -len(title), url, title))
    scored.sort(reverse=True)
    return [(url, title) for _, _, url, title in scored[:limit]]


def process_locale(locale, state):
    folder = os.path.join(PAGES, locale)
    if not os.path.isdir(folder):
        return
    pool_by_app = collect(locale)
    if not pool_by_app:
        return
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".html") or name == "index.html":
            continue
        if name.endswith(("-privacy.html", "-support.html")):
            continue
        path = os.path.join(folder, name)
        source = read(path)
        app_id = primary_app_id(source)
        if not app_id:
            continue
        pool = pool_by_app.get(app_id, [])
        url_self = f"{SITE}/{locale}/{name}"
        related = pick_related(source, url_self, pool, MAX_LINKS)
        if len(related) < MIN_LINKS:
            write_block(path, "", state)
        else:
            write_block(path, build_block(locale, related), state)
        write_support(path, support_block(locale, name, source), state)


def process_hubs(state):
    """英文 hubs 頁補上該 App 還沒被連到的 answers(拓展主題叢集覆蓋率)。"""
    folder = os.path.join(PAGES, "hubs")
    if not os.path.isdir(folder):
        return
    pool_by_app = collect_root_answers()
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".html") or name == "index.html":
            continue
        path = os.path.join(folder, name)
        source = read(path)
        app_id = primary_app_id(source)
        if not app_id:
            continue
        pool = pool_by_app.get(app_id, [])
        linked = {
            html.unescape(h) for h in HREF_RE.findall(BLOCK.sub("", source))
        }
        missing = [
            (url, title)
            for url, title, _ in pool
            if url not in linked and url.rsplit("/", 1)[-1] not in linked
        ]
        write_block(
            path,
            build_block("en", missing) if missing else "",
            state,
        )


def collect_root_answers():
    out = {}
    folder = os.path.join(PAGES, "answers")
    if not os.path.isdir(folder):
        return out
    for name in sorted(os.listdir(folder)):
        if not name.endswith(".html") or name == "index.html":
            continue
        source = read(os.path.join(folder, name))
        app_id = primary_app_id(source)
        if not app_id:
            continue
        title = text_of(source, H1_RE) or text_of(source, TITLE_RE)
        if not title:
            continue
        out.setdefault(app_id, []).append(
            (f"{SITE}/answers/{name}", title, tokens(title))
        )
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--locale", action="append", help="只跑指定語系")
    args = parser.parse_args()
    state = {"check": args.check, "changed": []}

    locales = args.locale or list(OFFICIAL_LOCALES)
    for locale in locales:
        process_locale(locale, state)
    if not args.locale:
        process_hubs(state)

    print(
        f"app-page related links: {len(state['changed'])} 個檔案"
        f"{'需更新' if args.check else '已更新'}"
    )
    return 1 if args.check and state["changed"] else 0


if __name__ == "__main__":
    sys.exit(main())
