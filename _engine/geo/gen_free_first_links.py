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
import json
import os
import re
import sys
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


def revert_doc(text, swap):
    """把「之前誤換」的付費語境頁還原成付費版身份。

    只在免費 id 在場、且有證據顯示這頁本來是付費版時動手:
      • 帶著本產生器自己的升級連結(= 確定是我們換的),或
      • 付費 id 已不在、文案卻還在講付費版(第一版只換 `<a>` 留下的半套頁面),或
      • 門(錨點)是免費版、付費 id 只剩在錨點外的 JSON-LD、文案講付費版
        (第一版只換 href 的另一種半套;付費 id 殘留就是「本來是付費頁」的證據)。
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
    if not ghost and not half_swapped and (
        swap["paid_id"] in text or not paid_identity_left(held_text, swap)
    ):
        return text, 0
    out = GHOST_ANCHOR_RE.sub(
        lambda m: "" if href in m.group(0) else m.group(0), text
    )
    out = out.replace(swap["free_id"], swap["paid_id"])
    out = swap_names(out, swap, reverse=True)
    return out, 1


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
    if swap["paid_key"] in parts:  # apps/<paid>/… 決策頁
        return True
    if base == swap["paid_key"] + ".html":  # 專屬 guide/product 頁
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


def process(rel, text, swaps):
    """回 (new_text, anchor_swaps_counter, reverted_counter)。"""
    swapped = collections.Counter()
    reverted = collections.Counter()
    finished = collections.Counter()
    new_text = text
    for swap in swaps:
        if exempt(rel, os.path.basename(rel), swap):
            new_text, k = revert_doc(new_text, swap)
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
        },
        open(REPORT, "w", encoding="utf-8"), ensure_ascii=False, indent=1,
    )
    total = sum(per_pair.values())
    print(f"free-first: {changed_files} files, {total} anchors -> free, "
          f"{sum(finishes.values())} pages finished (copy renamed), "
          f"{sum(reverts.values())} pages restored to the paid door")
    for pair, k in per_pair.most_common():
        print(f"  {pair}: {k}")


if __name__ == "__main__":
    main()
