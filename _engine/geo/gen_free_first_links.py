#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""「免費版優先」導流 — 把品類需求頁的商店 CTA 從付費版換成免費/Lite 版。

根因(2026-08-08 ASC 30 天):11 對兄弟 App,付費版 ppv→下載 0–2.7%、
免費版 10.9–64.3%,但外宣連結大多指向付費版 = 導錯門。

鐵則(2026-08-10 稽核後收緊):**頁面文案講哪一版,按鈕就開哪一版。**
只換按鈕不換文案,就是拿買斷版的內容去騙讀者點免費版 —— 誠實性與轉換雙輸。
所以換門是「整頁換身份」而不是「只換 href」:

  • 換門頁(品類需求頁):App Store id、可見名稱(標題/H1/卡片/內文/JSON-LD)
    全部一起換成免費版,整頁只講一個 App。換完硬檢查一次:付費版名稱若還
    留在頁面上(非升級連結),整頁回滾成付費版 —— 寧可不換,不可自相矛盾。
  • 不換門(付費語境),整頁維持付費版:
      - slug 直接點名付費 App(`lumimathpro-no-subscription`、`snapport-vs-…`,
        邊界用非英數字判定,黏在一起的寫法也要抓到)
      - slug 含 pro/plus/premium/upgrade/full
      - apps/<paid>/ 決策頁、guides/<paid>.html 專屬頁、persona 首問頁
      - about.html:陳述「本站作者做的買斷制 App 有哪些」的事實,換名字會變成假話
      - 免費版錨點已 ≥ 付費版錨點的頁(本來就是升級語境)
  • 換門頁補一條升級連結:接在第一個被換的商店 CTA 之後(不限 class),
    連到付費版的**內部 guide 頁**(不可直連商店:一頁只能有一個 App Store
    身份,否則 gen_smart_app_banners / gen_mobile_app_identity 的單一 App
    檢查會判衝突 — 2026-08-09 publish 實際炸過)。文案與 guide 連結都跟著
    該頁語系走(50 語)。
  • 站內指向付費版自己頁面的連結(guides/apps/alternatives)保留付費名稱 ——
    那是導向付費產品的導覽,名稱與目的地一致才誠實;它們不算「頁面文案」。

配對來源:app_pairs.py(registry 自動推導,新 pair 自動適用)。
必須登錄在 geo/publish.py 的 normalize/decision-cards/QR 鏈之前 —— 直接改輸出
會被下一次 publish 覆蓋(見 geo-site-reality 教訓)。
"""
import collections
import functools
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))
from videogen.registry import APPS, APPSTORE  # noqa: E402
from app_pairs import (  # noqa: E402
    is_paid_nav_anchor, paid_name_aliases, paid_name_re, paid_slug_re,
    paid_to_free,
)
from gen_smart_app_banners import MOBILE_APP_IDENTITY_BLOCK_RE  # noqa: E402

PAGES = os.environ.get("GEO_PAGES", os.path.join(HERE, "pages"))
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
REPORT = os.path.join(HERE, "reports", "free_first_rewrite.json")
SKIP_DIRS = {"_engine", "assets", ".git"}
SLUG_EXEMPT = re.compile(r"(?:^|-)(pro|plus|premium|upgrade|full)(?:-|\.|$)")
# 陳述「本站作者的買斷制 App 有哪些」的頁:名稱是事實陳述的一部分,不能改寫。
PORTFOLIO_PAGES = {"about.html"}


def _persona_page_basenames():
    """每支付費 App 在 publisher intent catalog 裡「自己的」answers 頁檔名。"""
    try:
        from answer_personas import PERSONAS
        from publisher_intent_catalog import slugify
    except ImportError:  # 產生器可獨立執行時就跳過這層排除
        return {}
    result = {}
    for key, entries in PERSONAS.items():
        if entries and entries[0].get("query"):
            result[key] = slugify(str(entries[0]["query"])) + ".html"
    return result


PERSONA_PAGE_BASENAMES = _persona_page_basenames()
UPGRADE_CLASS = "free-first-upgrade"
GHOST_SLOT = "<!--free-first-upgrade-slot-->"
HOLD = "\x00ff{}\x00"
HOLD_RE = re.compile(r"\x00ff(\d+)\x00")
ANCHOR_ANY_RE = re.compile(r"<a\b[^>]*>.*?</a>", re.S | re.I)
# 舊版 ghost 曾直連商店;一律遷移為內部 guide 頁連結。
STORE_GHOST_RE = re.compile(
    r'(<a class="cta ghost ' + UPGRADE_CLASS + r'" href=")'
    r'https://apps\.apple\.com/app/id(\d+)(")'
)
GHOST_ANCHOR_RE = re.compile(
    r'<a class="cta ghost ' + UPGRADE_CLASS + r'"[^>]*>.*?</a>\s*', re.S
)

# 升級連結的「買斷制」說法。50 個官方語系都要有(見 localization-must-ship-with-string
# 鐵律:新字串必須跟語言一起出貨),以 base language 為鍵,zh 另外分繁簡。
UPGRADE_LABELS = {
    "en": "one-time purchase", "zh-Hant": "買斷制", "zh-Hans": "买断制",
    "ja": "買い切り", "ko": "1회 구매", "de": "Einmalkauf",
    "fr": "achat unique", "es": "pago único", "pt": "compra única",
    "it": "acquisto una tantum", "ru": "разовая покупка",
    "ar": "شراء لمرة واحدة", "th": "จ่ายครั้งเดียว", "vi": "mua một lần",
    "id": "beli sekali", "ms": "beli sekali", "tr": "tek seferlik satın alma",
    "pl": "jednorazowy zakup", "nl": "eenmalige aankoop", "sv": "engångsköp",
    "da": "engangskøb", "no": "engangskjøp", "fi": "kertaosto",
    "cs": "jednorázový nákup", "sk": "jednorazový nákup",
    "hu": "egyszeri vásárlás", "ro": "achiziție unică", "el": "εφάπαξ αγορά",
    "hr": "jednokratna kupnja", "sl": "enkratni nakup", "ca": "compra única",
    "uk": "разова покупка", "he": "רכישה חד-פעמית", "hi": "एक बार की खरीद",
    "bn": "এককালীন ক্রয়", "gu": "એક વખતની ખરીદી", "kn": "ಒಂದು ಬಾರಿಯ ಖರೀದಿ",
    "ml": "ഒറ്റത്തവണ വാങ്ങൽ", "mr": "एकवेळ खरेदी", "or": "ଏକ ଥର କ୍ରୟ",
    "pa": "ਇੱਕ ਵਾਰੀ ਖਰੀਦ", "ta": "ஒருமுறை கொள்முதல்", "te": "ఒకసారి కొనుగోలు",
    "ur": "ایک بار کی خریداری",
}
RTL_LANGS = {"ar", "he", "ur", "fa"}


def display_name(key):
    return APPS.get(key, {}).get("name", key)


def build_swaps():
    swaps = []
    for paid, free in sorted(paid_to_free().items()):
        pid, fid = APPSTORE.get(paid), APPSTORE.get(free)
        if pid and fid:
            swaps.append({
                "paid_key": paid, "free_key": free,
                "paid_id": pid, "free_id": fid,
                "paid_name": display_name(paid),
                "free_name": display_name(free),
                "paid_name_re": paid_name_re(paid),
                "paid_slug_re": paid_slug_re(paid),
            })
    return swaps


def anchor_re(app_id):
    return re.compile(
        r'<a\b[^>]*href="[^"]*id' + re.escape(app_id) + r'[^"]*"[^>]*>.*?</a>',
        re.S,
    )


def _sub_name(text, old, new):
    """old→new,可重跑(new 以 old 為前綴時不重複疊字)。"""
    if old == new or not old:
        return text
    if new.startswith(old):
        return re.sub(
            re.escape(old) + "(?!" + re.escape(new[len(old):]) + ")", new, text
        )
    return text.replace(old, new)


def swap_names(text, swap, reverse=False):
    """整頁把付費版名稱換成免費版(reverse=True 則反向)。

    registry 名稱與去掉副標的簡寫都要換,長的先換。
    """
    aliases = paid_name_aliases(swap["paid_key"]) or [swap["paid_name"]]
    if reverse:
        return _sub_name(text, swap["free_name"], swap["paid_name"])
    for alias in aliases:
        text = _sub_name(text, alias, swap["free_name"])
    return text


def base_lang(locale):
    if locale.startswith("zh"):
        return "zh-Hant" if "Hant" in locale or locale in {"zh-TW", "zh-HK"} else (
            "zh-Hans" if "Hans" in locale or locale in {"zh-CN", "zh"} else "zh-Hant"
        )
    return locale.split("-")[0]


def locale_of(rel):
    parts = rel.split(os.sep)
    return parts[0] if len(parts) > 1 else ""


def guide_url(key, locale):
    """該語系的 guide 頁,沒有就退回英文 root(不製造 404)。"""
    if locale:
        localized = os.path.join(PAGES, locale, "guides", key + ".html")
        if os.path.exists(localized):
            return f"{SITE}/{locale}/guides/{key}.html"
    return f"{SITE}/guides/{key}.html"


def upgrade_html(rel, swap):
    """升級連結:文案與 guide 目的地都跟著該頁語系走(缺該語系 guide 才退英文)。"""
    locale = locale_of(rel)
    lang = base_lang(locale) if locale else "en"
    label = UPGRADE_LABELS.get(locale) or UPGRADE_LABELS.get(lang) \
        or UPGRADE_LABELS["en"]
    arrow = "←" if lang.split("-")[0] in RTL_LANGS else "→"
    href = guide_url(swap["paid_key"], locale)
    return (
        f'<a class="cta ghost {UPGRADE_CLASS}" href="{href}">'
        f'{swap["paid_name"]} ({label}) {arrow}</a>'
    )


def upgrade_anchor(rel, swap):
    return " " + upgrade_html(rel, swap)


GHOST_HREF_RE = re.compile(
    r'<a class="cta ghost ' + UPGRADE_CLASS + r'" href="([^"]*)"[^>]*>.*?</a>',
    re.S,
)


def localize_ghosts(text, rel, swaps):
    """把既有的升級連結換成該頁語系的文案 / guide(舊版全站只出英文)。"""
    by_key = {s["paid_key"]: s for s in swaps}

    def sub(match):
        key = os.path.basename(match.group(1)).rsplit(".", 1)[0]
        swap = by_key.get(key)
        return upgrade_html(rel, swap) if swap else match.group(0)

    return GHOST_HREF_RE.sub(sub, text)


def hold_paid_nav_anchors(text, swap):
    """把「指向付費版自己頁面」的站內連結收起來,不參與整頁改名與誠實性檢查。

    這種連結的錨點文字寫付費版名稱是對的 —— 目的地就是付費版的頁。
    """
    held = []

    def sub(match):
        block = match.group(0)
        if not is_paid_nav_anchor(block, swap["paid_key"]):
            return block
        held.append(block)
        return HOLD.format(len(held) - 1)

    return ANCHOR_ANY_RE.sub(sub, text), held


def release_holds(text, held):
    return HOLD_RE.sub(lambda m: held[int(m.group(1))], text)


def paid_identity_left(text, swap):
    """換門後付費版名稱是否還留在頁面上(站內導覽連結已收起、不計入)。"""
    return bool(swap["paid_name_re"].search(text))


def rewrite_doc(text, swap, rel=""):
    """回 (new_text, n_anchor_swaps)。免費版錨點已佔優的頁不動(升級語境)。"""
    pid, fid = swap["paid_id"], swap["free_id"]
    paid_anchor_pat = anchor_re(pid)
    paid_anchors = len(paid_anchor_pat.findall(text))
    free_anchors = len(anchor_re(fid).findall(text))
    if not paid_anchors or free_anchors >= paid_anchors:
        return text, 0

    held_text, held = hold_paid_nav_anchors(text, swap)
    n = 0
    marked = [False]

    def sub(match):
        nonlocal n
        n += 1
        block = match.group(0)
        if marked[0]:
            return block
        marked[0] = True
        return block + GHOST_SLOT

    out = paid_anchor_pat.sub(sub, held_text)
    if not n:
        return text, 0

    # 整頁換身份:id 與可見名稱一起換(標題/H1/卡片/內文/JSON-LD 都涵蓋)。
    out = out.replace(pid, fid)
    out = swap_names(out, swap)

    # 誠實性硬檢查:付費名稱若還在,整頁回滾 —— 寧可不換也不要自相矛盾。
    if paid_identity_left(out, swap):
        return text, 0

    out = release_holds(out, held)
    # 升級連結每一對各放一條:它同時是「這一對是我們換的」的指紋,只放一條會
    # 讓同頁的第二對 App 失去指紋,之後補不了文案也還不了原。
    ghost = "" if swapped_by_us(out, swap) else upgrade_anchor(rel, swap)
    out = out.replace(GHOST_SLOT, ghost)
    return out, n


def swapped_by_us(text, swap):
    """這一頁帶著本產生器為這一對放的升級連結 = 我們換過門。"""
    href = f'/guides/{swap["paid_key"]}.html"'
    return any(href in m.group(0) for m in GHOST_ANCHOR_RE.finditer(text))


def _complete_half_swapped(text, swap):
    """第一版只換 `<a>` href 留下的另一種半套頁:門(錨點)已開免費版,付費
    id 只剩在錨點外的機器區塊(ItemList/HowTo JSON-LD 的 "url" 等),文案照舊
    講付費版。

    這種頁 rewrite_doc 碰不到(沒有付費**錨點**可觸發),舊收尾邏輯又因付費
    id 在場而跳過,會永遠卡在「按鈕開免費版、內容講付費版」(2026-08-31 稽核:
    snapport 3,291 頁、gmoney 141 頁、hourstag 98 頁)。比照 finish_doc 的
    鐵則收尾 —— 收得乾淨就整頁換成免費版身份,收不乾淨就整頁還原成付費門,
    不留半套。
    """
    pid, fid = swap["paid_id"], swap["free_id"]
    if anchor_re(pid).search(text) or not anchor_re(fid).search(text):
        return text, 0, 0
    held_text, held = hold_paid_nav_anchors(text, swap)
    out = held_text.replace(pid, fid)
    out = swap_names(out, swap)
    if paid_identity_left(out, swap):
        # 收不乾淨(名稱有本產生器換不動的寫法)→ 整頁還原成付費門。
        out = held_text.replace(fid, pid)
        out = swap_names(out, swap, reverse=True)
        return release_holds(out, held), 0, 1
    return release_holds(out, held), 1, 0


def _finish_without_fingerprint(text, swap):
    """沒有升級連結指紋、但門與文案對不上的頁面怎麼處理。

    第一版的升級連結只在錨點含 `class="cta"` 時才補,所以有一批換過門的頁面
    沒有指紋。這時要跟「本來就是免費版、只是在升級語境提到付費版」的頁面分開:

      • 免費版名稱只出現在錨點裡、文案通篇講付費版 → 是換了一半的頁。
        這種頁**還原成付費門**(不是改寫文案):文案的功能/價格主張是照付費版
        寫的,我們無法保證免費版都成立,寧可少一次導流也不要寫出可能不實的句子。
      • 免費版名稱也出現在文案裡 → 本來就是免費版的頁,提到付費版是升級語境,
        不動。
    """
    if swap["paid_id"] in text:
        return _complete_half_swapped(text, swap)
    held_text, _held = hold_paid_nav_anchors(text, swap)
    if not paid_identity_left(held_text, swap):
        return text, 0, 0
    if swap["free_name"] in ANCHOR_ANY_RE.sub(" ", held_text):
        return text, 0, 0
    out, k = revert_doc(text, swap)
    return out, 0, k


def finish_doc(text, swap, rel=""):
    """把「舊版只換了按鈕、沒換文案」的頁面補完成整頁換身份。

    2026-08-09 的第一版只在 `<a>` 內換名稱,留下 6,000+ 頁「標題/內文/卡片標題
    講付費版、唯一按鈕開免費版」,而且 ItemList 之類的 JSON-LD 還留著付費 id。
    這種頁已經沒有付費版**錨點**可觸發 rewrite_doc,必須另外收尾:收得乾淨就
    整頁換成免費版,收不乾淨就整頁還原成付費版 —— 不留半套。
    """
    if swap["free_id"] not in text:
        return text, 0, 0
    if not swapped_by_us(text, swap):
        return _finish_without_fingerprint(text, swap)
    held_text, held = hold_paid_nav_anchors(text, swap)
    if swap["paid_id"] not in held_text and not paid_identity_left(held_text, swap):
        return text, 0, 0  # 已經是乾淨的免費版身份
    out = held_text.replace(swap["paid_id"], swap["free_id"])
    out = swap_names(out, swap)
    if paid_identity_left(out, swap):
        out, k = revert_doc(text, swap)
        return out, 0, k
    return release_holds(out, held), 1, 0


def revert_doc(text, swap, owned=False):
    """把「之前誤換」的付費語境頁還原成付費版身份。

    只在免費 id 在場、且有證據顯示這頁本來是付費版時動手:
      • 帶著本產生器自己的升級連結(= 確定是我們換的),或
      • 付費 id 已不在、文案卻還在講付費版(第一版只換 `<a>` 留下的半套頁面),或
      • 門(錨點)是免費版、付費 id 只剩在錨點外的 JSON-LD、文案講付費版
        (第一版只換 href 的另一種半套;付費 id 殘留就是「本來是付費頁」的證據)。
      • `owned`(付費版自己的網站目錄 / 專屬 guide 頁)且整頁只剩免費版 id ——
        這種頁的身份由路徑定義,掛著兄弟免費版的 id 就是錯掛,不需要別的指紋。
        文案早被整頁改名、連付費版名稱都不剩時,上面三條都驗不到(2026-08-18
        `apps/wifi-aid/` 就是這樣被換掉又收不回來)。
    以上都不成立時不動,避免把本來就是免費版的頁面誤改。
    """
    if swap["free_id"] not in text:
        return text, 0
    href = f'/guides/{swap["paid_key"]}.html"'
    ghost = swapped_by_us(text, swap)
    held_text, _held = hold_paid_nav_anchors(text, swap)
    half_swapped = (
        swap["paid_id"] in text
        and not anchor_re(swap["paid_id"]).search(text)
        and bool(anchor_re(swap["free_id"]).search(text))
        and paid_identity_left(held_text, swap)
    )
    misfiled = owned and swap["paid_id"] not in text
    if not ghost and not half_swapped and not misfiled and (
        swap["paid_id"] in text or not paid_identity_left(held_text, swap)
    ):
        return text, 0
    return _reverse_identity(text, swap), 1


def _reverse_identity(text, swap):
    """機械性地把免費版身份換回付費版(升級連結一併拿掉)。"""
    href = f'/guides/{swap["paid_key"]}.html"'
    out = GHOST_ANCHOR_RE.sub(
        lambda m: "" if href in m.group(0) else m.group(0), text
    )
    out = out.replace(swap["free_id"], swap["paid_id"])
    return swap_names(out, swap, reverse=True)


def normalized_key(segment):
    """路徑片段 → registry app key 的寫法(`wifi-aid` → `wifiaid`)。

    站上同一支 App 的目錄有兩種歷史寫法(`apps/wifiaid/` 與更早手工建的
    `apps/wifi-aid/`)。只比對原字串會漏掉加了連字號的那種,付費版自己的
    官網就會被當成品類需求頁換門。
    """
    return re.sub(r"[^a-z0-9]+", "", segment.lower())


def owns_page(rel, swap):
    """這頁是不是付費版**自己的**頁(自己的網站目錄,或專屬 guide/product 頁)。"""
    parts = rel.split(os.sep)
    if swap["paid_key"] in parts[:-1]:
        return True
    if any(normalized_key(part) == swap["paid_key"] for part in parts[:-1]):
        return True
    base = os.path.basename(rel)
    stem = base[:-5] if base.endswith(".html") else base
    return normalized_key(stem) == swap["paid_key"]


def exempt(rel, name, swap):
    base = os.path.basename(rel)
    stem = base[:-5] if base.endswith(".html") else base
    if SLUG_EXEMPT.search(stem):
        return True
    # slug 直接點名付費 App(`lumimathpro-no-subscription`、`snapport-vs-…`)。
    # 這種頁的標題、內文、網址本身就是付費版的查詢,換門等於掛羊頭賣狗肉。
    if swap["paid_slug_re"].search(stem):
        return True
    parts = rel.split(os.sep)
    # apps/<paid>/… 決策頁、guides/<paid>.html 專屬頁(含 `wifi-aid` 這種
    # 加連字號的舊寫法)。
    if owns_page(rel, swap):
        return True
    if base in PORTFOLIO_PAGES and len(parts) == 1:
        return True
    # publisher intent catalog 把每支 App 的 persona 首問頁登記成「該 App 自己的
    # 頁」,並在多個下游驗證器要求頁面身份與該 App 一致(CTA 標籤、在地化名稱、
    # smart app banner)。換掉這種頁的門會讓 publish 連鎖失敗,而且語意上它本來
    # 就是付費版自己的頁,不是品類需求頁。
    if base == PERSONA_PAGE_BASENAMES.get(swap["paid_key"]):
        return True
    return False


def id_to_paid_key():
    return {APPSTORE[k]: k for k in paid_to_free() if k in APPSTORE}


def migrate_store_ghosts(text):
    """把舊版直連商店的 ghost 升級連結改成內部 guide 頁連結。"""
    mapping = id_to_paid_key()

    def sub(match):
        key = mapping.get(match.group(2))
        if not key:
            return match.group(0)
        return f"{match.group(1)}{SITE}/guides/{key}.html{match.group(3)}"

    return STORE_GHOST_RE.sub(sub, text)


def strip_stale_identity(text, swaps):
    """換門後移除仍綁付費版的機器身份區塊(下游會以免費身份重建)。

    self-guard:只動「同頁免費版 id 也在場」的付費身份區塊。
    """
    stale_ids = {
        "id" + s["paid_id"]
        for s in swaps
        if "id" + s["free_id"] in text
    }
    if not stale_ids:
        return text

    def sub(match):
        block = match.group(0)
        if any(tok in block for tok in stale_ids):
            return "\n"
        return block

    return MOBILE_APP_IDENTITY_BLOCK_RE.sub(sub, text)



# ---------------------------------------------------------------------------
# 價格敘述跟著「門」走(2026-08-31)
#
# 品類需求頁的 App 卡片(`<div class="item">`)裡,「why」那一句是各語系寫死在
# gen_full_coverage_*.py / auto_batch_runner 的當地幣別定價,例如
# 「Auto crop. Guarantee. ₹99.」。那句是照**付費版**寫的;換門之後卡片講的是
# 免費版(purchase_model=free_with_lifetime_unlock),旁邊卻還掛著付費版的固定
# 價格 —— 免費 App 標一個買斷價,是不準確的敘述,而且掛的還是另一支 App 的價。
#
# 規則:
#   • paid_upfront 的門 → 一次性價格寫法原封不動(那句是對的)。
#   • free_with_lifetime_unlock 的門 → 拿掉固定價格句,換成 repo **既有**的
#     在地化「免費開始 / 一次解鎖」說法(cluster_l10n.PRICING 與
#     build_pages_i18n.PROFILE_PRICING,兩者都是已出貨的 50-locale 用字)。
#   • 該語系沒有既有用字 → 只拿掉價格句,不補英文、不機翻、不新造字串。
#   • 不寫任何解鎖價:各頁的數字都是付費版的價,免費版的解鎖價本產生器無從得知,
#     寧可不寫也不可寫錯(誠實鐵律:不宣稱「永久擁有」「終身免費」)。
# ---------------------------------------------------------------------------
FREE_DOOR_MODEL = "free_with_lifetime_unlock"
ITEM_BLOCK_RE = re.compile(r'<div class="item">.*?</div>', re.S)
CARD_P_RE = re.compile(r"<p>(.*?)</p>", re.S)
# 句子切點;數字後面接數字的 `.`/`,` 是小數/千分位(₹3.99、Rp15.000),不是句點。
# 除了拉丁句點,還要含印度系 danda、烏爾都/阿拉伯、藏、緬、高棉、亞美尼亞句號
# —— 少一個,整段就併成一個長片段,定價句會被字母上限誤放行。
SENTENCE_SPLIT_RE = re.compile(
    "([.。!！?？;；:\u0964\u0965\u06d4\u061f\u1362\u17d4\u0f0d\u104a"
    "\u104b\u0589]+(?!\\d))"
)
# 幣別縮寫(非 ISO 4217 的當地寫法),來自站上實際出現過的定價句。
EXTRA_CURRENCY = {
    "FCFA", "CFA", "KSH", "TSH", "USH", "SH", "RS", "RP", "RM", "KR", "ZŁ",
    "KČ", "FT", "ЛВ", "СОМ", "SOM", "ТГ", "S/", "NU", "LE", "BS",
    "GS", "AF", "DA", "DT", "FC", "MK", "MT", "TL", "ТЕНГЕ", "ДИН", "ДЕН",
    "ЛЕЙ", "AR", "FBU", "FR", "NAIRA", "СОМОНӢ", "РУБ", "РУБ.",
    "तومान", "रू", "रु", "৳", "ብር", "ናቕፋ",
    "تومان", "تومن", "درهم", "جنيه", "ريال", "دينار", "دج", "افغانی",
    "ل", "ج", "ر", "د", "ك",
}
# `so'm`(烏茲別克)在 token 切分下會斷成 so + m,單獨列一條規則。
SOM_RE = re.compile("so['ʻ\u2019]m", re.I)
# 「數字 + k」的緬甸幣寫法(1000k)。只在片段裡沒有其他拉丁字母時才算幣別,
# 「Supports 4K video」這種解析度寫法不會中。
DIGITS_K_RE = re.compile(r"(?<![^\W\d_])\d[\d.,\u00a0]*[kK](?![^\W\d_])")
LATIN_RE = re.compile(r"[A-Za-z]")
# 單字母幣別(N500、R75、Q25、M79、K 3,000…)只在緊貼數字時才算幣別,
# 避免把「iPhone 15」「Plan B 2」這種寫法誤判成價格。
SINGLE_LETTER_CURRENCY_RE = re.compile(
    r"(?<![^\W\d_])[QRNMKPLBEGZDTS][\s.\u00a0]?\d", re.U
)
# 詞切分:字首必須是字母,其後吃到空白/數字/標點為止 —— 天城體等文字的
# 母音符號(Mn)不算 \\w,用 `[^\\W\\d_]+` 會把「रू」切成「र」而漏判。
CURRENCY_WORD_RE = re.compile(r"S/|[^\W\d_][^\s\d.,;:!?()\[\]/·]*", re.U)
# 片段裡的「字母量」上限:定價句頂多是「£14 unweyth」「₹99 one-time」這種
# 短限定語;字多就是正文(「Vocabulary in 44 languages…」),一律不動。
PRICE_FRAGMENT_MAX_LETTERS = 24
PRICE_FRAGMENT_MAX_CHARS = 48

ISO_4217 = {
    "AED", "AFN", "ALL", "AMD", "ANG", "AOA", "ARS", "AUD", "AWG", "AZN",
    "BAM", "BBD", "BDT", "BGN", "BHD", "BIF", "BMD", "BND", "BOB", "BRL",
    "BSD", "BTN", "BWP", "BYN", "BZD", "CAD", "CDF", "CHF", "CLP", "CNY",
    "COP", "CRC", "CUP", "CVE", "CZK", "DJF", "DKK", "DOP", "DZD", "EGP",
    "ERN", "ETB", "EUR", "FJD", "FKP", "GBP", "GEL", "GHS", "GIP", "GMD",
    "GNF", "GTQ", "GYD", "HKD", "HNL", "HRK", "HTG", "HUF", "IDR", "ILS",
    "INR", "IQD", "IRR", "ISK", "JMD", "JOD", "JPY", "KES", "KGS", "KHR",
    "KMF", "KPW", "KRW", "KWD", "KYD", "KZT", "LAK", "LBP", "LKR", "LRD",
    "LSL", "LYD", "MAD", "MDL", "MGA", "MKD", "MMK", "MNT", "MOP", "MRU",
    "MUR", "MVR", "MWK", "MXN", "MYR", "MZN", "NAD", "NGN", "NIO", "NOK",
    "NPR", "NZD", "OMR", "PAB", "PEN", "PGK", "PHP", "PKR", "PLN", "PYG",
    "QAR", "RON", "RSD", "RUB", "RWF", "SAR", "SBD", "SCR", "SDG", "SEK",
    "SGD", "SHP", "SLE", "SLL", "SOS", "SRD", "SSP", "STN", "SVC", "SYP",
    "SZL", "THB", "TJS", "TMT", "TND", "TOP", "TRY", "TTD", "TWD", "TZS",
    "UAH", "UGX", "USD", "UYU", "UZS", "VES", "VND", "VUV", "WST", "XAF",
    "XCD", "XOF", "XPF", "YER", "ZAR", "ZMW", "ZWL",
}


@functools.lru_cache(maxsize=1)
def free_door_ids():
    """換門後的免費門 id:配對免費版,且 registry 驗到的是 free_with_lifetime_unlock。

    只收**配對**的免費版(paid_to_free 的右邊)。這些卡片的文案原本是照付費版
    寫的,價格自然是付費版的價 —— 換門之後那個數字就是別支 App 的價格,一定錯。

    沒有配對的免費 App(zafe / scanto / maskmyfile 等)不在這裡:它們卡片上的
    「$3 USD one-time」是自己被寫上去的,很可能就是自己的解鎖價,本產生器沒有
    第一方解鎖價資料可以判它錯,寧可不動也不刪掉可能正確的資訊。
    """
    return frozenset(
        APPSTORE[free]
        for free in paid_to_free().values()
        if free in APPSTORE
        and APPS.get(free, {}).get("purchase_model") == FREE_DOOR_MODEL
    )


@functools.lru_cache(maxsize=1)
def paid_door_ids():
    """paid_upfront 的門:那句一次性價格是對的,原封不動。"""
    return frozenset(
        APPSTORE[key]
        for key, app in APPS.items()
        if app.get("purchase_model") == "paid_upfront" and key in APPSTORE
    )


@functools.lru_cache(maxsize=1)
def free_door_lines():
    """{locale/base lang: 既有在地化的免費門說法}。只沿用 repo 已出貨的字串。

    優先序:cluster_l10n.PRICING(直接寫 free_with_lifetime_unlock、句子短、
    最貼近卡片語氣)> build_pages_i18n.PROFILE_PRICING 的 free_to_start
    (官方 50 locale 覆蓋、aeo_pages 已經用它對應這個 purchase_model)。
    兩邊都沒有的語系一律留空 = 只刪價格句,不補字。
    """
    lines = {}
    try:
        from build_pages_i18n import PROFILE_PRICING
    except Exception:  # 產生器可獨立執行時就少一層來源
        PROFILE_PRICING = {}
    for lang, copy in PROFILE_PRICING.items():
        text = (copy or {}).get("free_to_start")
        if text:
            lines[lang] = text
    try:
        from cluster_l10n import PRICING
    except Exception:
        PRICING = {}
    for locale, copy in PRICING.items():
        text = (copy or {}).get(FREE_DOOR_MODEL)
        if not text:
            continue
        lines[locale] = text
        lines[base_lang(locale)] = text
    return lines


def free_door_line(locale):
    lines = free_door_lines()
    if locale and locale in lines:
        return lines[locale]
    return lines.get(base_lang(locale) if locale else "en", "")


def _currency_in(fragment):
    if any(unicodedata.category(ch) == "Sc" for ch in fragment):
        return True
    if SINGLE_LETTER_CURRENCY_RE.search(fragment):
        return True
    if SOM_RE.search(fragment):
        return True
    match = DIGITS_K_RE.search(fragment)
    if match and not LATIN_RE.search(fragment.replace(match.group(0), "")):
        return True
    for token in CURRENCY_WORD_RE.findall(fragment):
        if token == "S/" or token.upper() in ISO_4217 \
                or token.upper() in EXTRA_CURRENCY or token in EXTRA_CURRENCY:
            return True
    return False


def is_price_claim(fragment):
    """這個句子片段是不是「一個固定價格」的主張。

    要同時滿足:有數字、有幣別記號、而且短到只可能是定價句(字母量有上限,
    所以「Vocabulary in 44 languages…」「you're not saving $500, …」不會中)。
    """
    text = fragment.strip()
    if not text or len(text) > PRICE_FRAGMENT_MAX_CHARS:
        return False
    if not any(ch.isdigit() for ch in text):
        return False
    if "<" in text or ">" in text:  # 片段裡有標記就不碰
        return False
    letters = re.sub(r"[\d\s\W_]+", "", text, flags=re.U)
    if len(letters) > PRICE_FRAGMENT_MAX_LETTERS:
        return False
    return _currency_in(text)


def _is_currency_abbrev(fragment):
    """整段就是一個幣別縮寫(`Gs`、`Bs`、`Nu`、`S/`);它後面的數字才是價格。"""
    text = fragment.strip()
    if not text or len(text) > 5 or any(ch.isdigit() for ch in text):
        return False
    return _currency_in(text + "1")


def _merge_currency_abbrev(parts):
    """`Gs. 7,000.` 會被句點切成「Gs」「7,000」,先併回同一個片段再判定。"""
    merged = []
    index = 0
    while index < len(parts):
        fragment = parts[index]
        delimiter = parts[index + 1] if index + 1 < len(parts) else ""
        if (_is_currency_abbrev(fragment) and delimiter.strip(" ") in {".", "。"}
                and index + 2 < len(parts)):
            parts = list(parts)
            parts[index + 2] = fragment + delimiter + parts[index + 2]
            index += 2
            continue
        merged.extend([fragment, delimiter])
        index += 2
    return merged


def strip_price_claims(text):
    """回 (剩下的文字, 拿掉幾個定價句)。"""
    parts = _merge_currency_abbrev(SENTENCE_SPLIT_RE.split(text))
    kept = []
    removed = 0
    for index in range(0, len(parts), 2):
        fragment = parts[index]
        delimiter = parts[index + 1] if index + 1 < len(parts) else ""
        if is_price_claim(fragment):
            removed += 1
            continue
        kept.append(fragment + delimiter)
    return re.sub(r"\s+", " ", "".join(kept)).strip(), removed


def _rewrite_card_pricing(block, line):
    removed = [0]

    def sub(match):
        inner = match.group(1)
        stripped, count = strip_price_claims(inner)
        if not count:
            return match.group(0)
        if line:
            stripped = (stripped + " " + line).strip()
        elif not stripped:
            # 沒有既有在地化用字、拿掉價格後整句會空掉 → 整段描述移除,
            # 卡片仍有 App 名稱與 CTA;寧可少一句,也不要留下不準確的價格。
            removed[0] += count
            return ""
        removed[0] += count
        return "<p>" + stripped + "</p>"

    return CARD_P_RE.sub(sub, block), removed[0]


def enforce_free_door_pricing(text, rel=""):
    """免費門的 App 卡片不可掛付費版的固定價格。回 (new_text, 修掉幾句)。"""
    free_ids = free_door_ids()
    if not any(("id" + app_id) in text for app_id in free_ids):
        return text, 0
    paid_ids = paid_door_ids()
    line = free_door_line(locale_of(rel))
    fixed = [0]

    def sub(match):
        block = match.group(0)
        if not any(("id" + app_id) in block for app_id in free_ids):
            return block
        if any(("id" + app_id) in block for app_id in paid_ids):
            return block  # 同一張卡同時掛兩支 App = 判不準,不動
        new_block, count = _rewrite_card_pricing(block, line)
        fixed[0] += count
        return new_block

    return ITEM_BLOCK_RE.sub(sub, text), fixed[0]


# ---------------------------------------------------------------------------
# 購買模式的事實跟著「門」走(2026-08-31)
#
# 換門只換「身份」(名稱、store id、JSON-LD),沒有依免費版 registry 重算
# **購買模式**的事實。結果是換門後的頁面把免費 App 描述成付費下載:
#
#   • 卡片 pill / 決策卡 fact / JSON-LD featureList:`Paid download`、`付費下載`
#   • 商店標語句:`… Paid download · Pay once · No subscription.`
#   • 「最適合」欄:`Paid download; Pay once; No subscription`
#   • 定價敘述句:`Paid download with one upfront price and no subscription.`
#
# 這些字串都是**付費版 registry 的 tag / cta_bullets / purchase_model 標籤**被
# 寫進頁面的結果;換門後頁面講的是 free_with_lifetime_unlock 的免費版,「付費
# 下載」就是假話(canon 原生 0 頁,100% 是換門造成的)。
#
# 規則(與 enforce_free_door_pricing 同一套紀律):
#   • 只在**免費門**頁動手:頁面帶配對免費版的 id、而且整頁沒有任何
#     paid_upfront App 的 id(roundup 這種同頁列多支 App 的頁面判不準,不動)。
#   • 只沿用 repo **既有**的在地化字串:
#       - portfolio_app_finder.UI / high_intent_decision_routes.UI /
#         publisher_intent_catalog.PURCHASE_LABELS 的 purchase-model 標籤,
#         同一個 locale 的 paid_upfront ↔ free_with_lifetime_unlock 直接對映;
#       - build_pages_i18n.PAID_UPFRONT_PRICING ↔ PROFILE_PRICING.free_to_start;
#       - build_pages.pricing_copy(付費 key) ↔ pricing_copy(免費 key);
#       - 英文短標籤退回 registry 自己的 bullet 用字 `Free to start`。
#     不機翻、不新造、不補英文。
#   • 升級連結(ghost)與指向付費版自己頁面的導覽連結先收起來:那些字是對的。
#   • 換完再掃一次:只要還留著「明講付費下載 / 一次付清價格」的字樣(例如
#     gen_cost_compare 的 `Paid download · one upfront price · no subscription.`
#     與它的散文句,本模組沒有對應的免費寫法),**整頁還原成付費門** ——
#     本模組既有鐵則:寧可少一次導流,也不要留下錯誤描述。
# ---------------------------------------------------------------------------
# registry 自己的免費門 bullet 用字(11 支 Lite 的慣例)。英文短標籤用它,
# 比 finder 的「Free to start · one-time unlock」更貼近 pill / featureList 語氣。
REGISTRY_FREE_START_BULLET = "Free to start"
# 換門後仍代表「付費下載 / 一次付清價格」的殘留字樣(不分大小寫)。
PAID_MODEL_RESIDUE_RE = re.compile(
    r"paid[-\s]download|paid[-\s]upfront|upfront price", re.I
)


def _add_pair(pairs, locale, paid, free):
    if paid and free and paid != free:
        pairs.setdefault(locale, {})[paid] = free


@functools.lru_cache(maxsize=1)
def purchase_model_pairs():
    """{locale: {付費說法: 免費說法}}。全部取自 repo 既有的在地化字典。"""
    pairs = {}
    try:
        import portfolio_app_finder
        for locale, copy in portfolio_app_finder.UI.items():
            _add_pair(pairs, locale, copy.get("paid_upfront"),
                      copy.get(FREE_DOOR_MODEL))
            labels = copy.get("purchase_labels") or {}
            _add_pair(pairs, locale, labels.get("paid_upfront"),
                      labels.get(FREE_DOOR_MODEL))
    except Exception:  # 產生器可獨立執行時就少一層來源
        pass
    try:
        import high_intent_decision_routes
        for locale, copy in high_intent_decision_routes.UI.items():
            models = copy.get("purchase_model") or {}
            _add_pair(pairs, locale, models.get("paid_upfront"),
                      models.get(FREE_DOOR_MODEL))
    except Exception:
        pass
    try:
        from publisher_intent_catalog import PURCHASE_LABELS
        _add_pair(pairs, "en", PURCHASE_LABELS.get("paid_upfront"),
                  PURCHASE_LABELS.get(FREE_DOOR_MODEL))
    except Exception:
        pass
    try:
        from build_pages_i18n import PAID_UPFRONT_PRICING, PROFILE_PRICING
        for lang, sentence in PAID_UPFRONT_PRICING.items():
            _add_pair(pairs, lang, sentence,
                      (PROFILE_PRICING.get(lang) or {}).get("free_to_start"))
    except Exception:
        pass
    try:
        from build_pages import pricing_copy
        for paid, free in sorted(paid_to_free().items()):
            if APPS.get(free, {}).get("purchase_model") != FREE_DOOR_MODEL:
                continue
            _add_pair(pairs, "en", pricing_copy(paid), pricing_copy(free))
    except Exception:
        pass
    # 英文短標籤:頁面上的 pill / featureList 本來就是 registry bullet,用
    # 同一套 bullet 用字接回去(`Paid download` → `Free to start`)。
    for locale, mapping in pairs.items():
        if "Paid download" in mapping:
            mapping["Paid download"] = REGISTRY_FREE_START_BULLET
    return {locale: dict(mapping) for locale, mapping in pairs.items()}


def purchase_model_rewrites(locale):
    """該頁要套的 (付費說法, 免費說法),長的先套。

    一定含 `en`:在地化頁面上常留著沒翻的英文標籤(實測 zh-Hant 的
    「最適合」欄就是英文 `Paid download; Pay once; No subscription`)。
    """
    pairs = purchase_model_pairs()
    merged = {}
    for key in ("en", base_lang(locale) if locale else "", locale or ""):
        merged.update(pairs.get(key, {}))
    return sorted(merged.items(), key=lambda item: len(item[0]), reverse=True)


@functools.lru_cache(maxsize=1)
def free_door_pair_ids():
    """[(付費 id, 免費 id)] —— 只收 free_with_lifetime_unlock 的配對免費版。"""
    out = []
    for paid, free in sorted(paid_to_free().items()):
        pid, fid = APPSTORE.get(paid), APPSTORE.get(free)
        if pid and fid and APPS.get(free, {}).get("purchase_model") == FREE_DOOR_MODEL:
            out.append((pid, fid))
    return tuple(out)


def is_free_door_page(text):
    """這頁的門是不是**只有**免費版。

    同頁出現任何 paid_upfront App 的 id(roundup / 對比頁)就不算 —— 那些
    「付費下載」字樣可能屬於別支真的要付費的 App,改了會製造新的假話。
    """
    if any(("id" + app_id) in text for app_id in paid_door_ids()):
        return False
    return any(("id" + fid) in text and ("id" + pid) not in text
               for pid, fid in free_door_pair_ids())


def hold_protected_anchors(text, swaps):
    """升級連結(ghost)與所有付費版導覽連結一起收起來,不參與改寫。"""
    held = []

    def sub(match):
        block = match.group(0)
        if UPGRADE_CLASS in block or any(
                is_paid_nav_anchor(block, swap["paid_key"]) for swap in swaps):
            held.append(block)
            return HOLD.format(len(held) - 1)
        return block

    return ANCHOR_ANY_RE.sub(sub, text), held


def enforce_free_door_purchase_model(text, rel="", swaps=(), original=None,
                                     just_swapped=False):
    """免費門的頁面不可把 App 描述成付費下載。

    `original` = 這一輪 process() 之前的原文。收不乾淨時靠它分兩種處理,
    這樣才收斂(不會每跑一次就換門→還原地來回抖):
      • 原文完全沒有免費版 id(乾淨的付費門)→ 這一輪的換門整個作廢,
        原封退回,檔案不會被寫。
      • 原文已經帶著免費版 id(上一輪換過門、或換一半)→ 機械性還原成
        付費門;下一輪原文就是乾淨的付費門,走上面那條路,不再改動。
    本產生器沒碰過、也沒有換門證據的頁(canon 自己就把免費 App 寫成付費)
    一律不動,只記帳 —— 那是上游文案的問題,不該由換門模組偷改身份。

    回 (new_text, 改了幾處, 還原成付費門幾次, 收不乾淨幾頁)。
    """
    if not is_free_door_page(text):
        return text, 0, 0, 0
    rewrites = purchase_model_rewrites(locale_of(rel))
    if not rewrites:
        return text, 0, 0, 0
    held_text, held = hold_protected_anchors(text, swaps)
    out = held_text
    fixed = 0
    for paid_text, free_text in rewrites:
        count = out.count(paid_text)
        if count:
            fixed += count
            out = out.replace(paid_text, free_text)
    # 收尾檢查對**所有**免費門頁都要跑:有些付費主張是頁面自己的散文
    # (「these are paid downloads」「a paid-upfront app」),字典裡沒有
    # 對應的免費寫法,字典比對一個都不會命中,但它一樣是假話。
    if PAID_MODEL_RESIDUE_RE.search(out):  # 收起來的連結不參與判定
        # 沒有既有免費寫法可換 → 這頁不給免費門,不留錯誤描述。
        if original is not None and not any(
                swap["free_id"] in original for swap in swaps):
            return original, 0, 1, 0  # 原文是乾淨的付費門 → 這一輪的換門作廢
        back = text
        reverted = 0
        for swap in swaps:
            back, k = revert_doc(back, swap, owned=owns_page(rel, swap))
            reverted += k
        if not reverted and just_swapped:
            # 這一輪才換/收尾、但沒有升級連結指紋的頁(gifting hub),
            # 「剛換的門」本身就是還原依據,機械性換回付費版。
            back = text
            for swap in swaps:
                if swap["free_id"] in back and swap["paid_id"] not in back:
                    back = _reverse_identity(back, swap)
                    reverted += 1
        if reverted:
            return back, 0, reverted, 0
        return text, 0, 0, 1  # 沒有還原依據 → 記帳待查(多半是 canon 原生)
    if not fixed:
        return text, 0, 0, 0
    return release_holds(out, held), fixed, 0, 0


def process(rel, text, swaps):
    """回 (new_text, anchor_swaps_counter, reverted_counter)。"""
    swapped = collections.Counter()
    reverted = collections.Counter()
    finished = collections.Counter()
    new_text = text
    for swap in swaps:
        if exempt(rel, os.path.basename(rel), swap):
            new_text, k = revert_doc(
                new_text, swap, owned=owns_page(rel, swap)
            )
            if k:
                reverted[swap["paid_key"]] += 1
            continue
        k = 0
        if swap["paid_id"] in new_text:
            new_text, k = rewrite_doc(new_text, swap, rel)
        if k:
            swapped[swap["paid_key"] + "->" + swap["free_key"]] += k
            continue
        # rewrite 沒動(付費 id 只留在 JSON-LD、或這頁是舊版換一半的結果)
        new_text, done, back = finish_doc(new_text, swap, rel)
        if done:
            finished[swap["paid_key"]] += done
        if back:
            reverted[swap["paid_key"]] += back
    if UPGRADE_CLASS in new_text:
        new_text = migrate_store_ghosts(new_text)
        new_text = localize_ghosts(new_text, rel, swaps)
    if swapped:
        new_text = strip_stale_identity(new_text, swaps)
    return new_text, swapped, reverted, finished


def main():
    swaps = build_swaps()
    # 免費 id 也要進篩選:換過門的頁面已經沒有付費 id,但可能還要收尾(文案沒換)
    # 或還原(付費語境被誤換);只看付費 id 會把這兩種頁全部漏掉。
    tokens = [s["paid_id"] for s in swaps] + [s["free_id"] for s in swaps] \
        + [UPGRADE_CLASS]
    changed_files = 0
    per_pair = collections.Counter()
    reverts = collections.Counter()
    finishes = collections.Counter()
    price_fixes = 0
    price_pages = 0
    model_fixes = 0
    model_pages = 0
    model_reverted_pages = 0
    model_unresolved = 0
    for dirpath, dirnames, filenames in os.walk(PAGES):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            if not filename.endswith(".html"):
                continue
            path = os.path.join(dirpath, filename)
            try:
                text = open(path, encoding="utf-8", errors="strict").read()
            except (OSError, UnicodeDecodeError):
                continue
            if not any(tok in text for tok in tokens):
                continue
            rel = os.path.relpath(path, PAGES)
            new_text, swapped, reverted, finished = process(rel, text, swaps)
            # 換門/還原都定案後才跑:價格敘述要跟著**最後**那道門走。
            new_text, priced = enforce_free_door_pricing(new_text, rel)
            if priced:
                price_fixes += priced
                price_pages += 1
            # 購買模式的事實也要跟著**最後**那道門走(價格句定案之後再跑,
            # 這樣還原成付費門時還原的是同一份文字)。
            new_text, model_fixed, model_back, model_stuck = \
                enforce_free_door_purchase_model(
                    new_text, rel, swaps, original=text,
                    just_swapped=bool(swapped or finished),
                )
            if model_fixed:
                model_fixes += model_fixed
                model_pages += 1
            if model_back:
                reverts["paid_model_residue"] += model_back
                model_reverted_pages += 1
            if model_stuck:
                model_unresolved += 1
            per_pair.update(swapped)
            reverts.update(reverted)
            finishes.update(finished)
            if new_text != text:
                open(path, "w", encoding="utf-8").write(new_text)
                changed_files += 1
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    json.dump(
        {
            "generated": datetime.now(timezone.utc).isoformat(),
            "changed_files": changed_files,
            "anchor_swaps": dict(per_pair.most_common()),
            "reverted_to_paid": dict(reverts.most_common()),
            "copy_finished_to_free": dict(finishes.most_common()),
            "paid_price_claims_removed": price_fixes,
            "pages_with_price_claims_removed": price_pages,
            "paid_model_claims_rewritten": model_fixes,
            "pages_with_paid_model_claims_rewritten": model_pages,
            "pages_reverted_for_paid_model_residue": model_reverted_pages,
            "pages_with_unresolved_paid_model_residue": model_unresolved,
        },
        open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1,
    )
    total = sum(per_pair.values())
    print(f"free-first: {changed_files} files, {total} anchors -> free, "
          f"{sum(finishes.values())} pages finished (copy renamed), "
          f"{sum(reverts.values())} pages restored to the paid door, "
          f"{price_fixes} paid price claims removed from free doors "
          f"({price_pages} pages), "
          f"{model_fixes} paid purchase-model claims rewritten "
          f"({model_pages} pages), "
          f"{model_reverted_pages} pages reverted for paid-model residue, "
          f"{model_unresolved} pages left with unresolved paid-model residue")
    for pair, k in per_pair.most_common():
        print(f"  {pair}: {k}")


if __name__ == "__main__":
    main()
