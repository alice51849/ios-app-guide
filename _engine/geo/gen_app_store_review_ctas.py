#!/usr/bin/env python3
"""Add a neutral existing-user "rate or review" link to live-App pages.

BM-13 / BM-47 (reports/benchmark_top1_checklist_2026-10-15.md) and lever 1
of reports/benchmark_top1_2026-10-15.md section 3: every page about a live
roster App carries Apple's direct review action,
``https://apps.apple.com/[cc/]app/id<N>?action=write-review`` (no reward).

Rules kept here on purpose:
  * No incentive, no star prompt, no "leave 5 stars": one neutral sentence per
    official locale asking people who already use the App to rate or review it.
  * The link is not a download CTA. It never carries pt/ct/mt; the attribution
    stamper (gen_store_attribution.final_review_url) only aligns its storefront
    and the read-only audit accepts exactly this shape for a live roster App.
  * Rendering is driven by gen_app_store_conversion_surfaces.py, which already
    runs right before every gen_store_attribution.py pass in geo-daily, on the
    same page inventory as the QR card and the share action. This module only
    owns the block markup, the copy and the placement.

  * Google Play (2026-10-23 emergency review: 15-country rating counts 0-3 on
    44 Apps): when the App is live on Android per the verified snapshot
    (android_play.load_snapshot; unreadable snapshot = no Play link), the same
    block also links Google Play's review list
    (``details?id=<package>&showAllReviews=true``, no referrer: not a download
    link). Same neutral sentence, no incentive.

    python geo/gen_app_store_review_ctas.py --report   # read-only coverage count
"""

from __future__ import annotations

import argparse
from collections import Counter
import html
import json
import os
from pathlib import Path
import re
import sys
import urllib.parse


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "social"))
sys.path.insert(0, str(HERE))

from app_store_storefronts import (  # noqa: E402
    APP_STORE_PATH_RE,
    app_store_review_url,
    is_app_store_review_url,
)
import gen_smart_app_banners  # noqa: E402
from official_locales import OFFICIAL_LOCALES  # noqa: E402
from videogen.registry import APPSTORE  # noqa: E402


PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
BLOCK_START = gen_smart_app_banners.APP_STORE_REVIEW_BLOCK_START
BLOCK_END = gen_smart_app_banners.APP_STORE_REVIEW_BLOCK_END
BLOCK_RE = gen_smart_app_banners.APP_STORE_REVIEW_BLOCK_RE
QR_BLOCK_END = gen_smart_app_banners.APP_STORE_QR_BLOCK_END
MOBILE_CTA_BLOCK_START = gen_smart_app_banners.MOBILE_CTA_BLOCK_START

# Every registry App (registry keys). Started 2026-10-15 as the ten focus
# Apps of the benchmark checklist, widened on 2026-10-16 (coverage audit:
# only 10 of 53 live Apps had the link) to the whole roster: every live App's
# pages carry the same neutral existing-user review link, because the
# benchmark found review count is the one lever every category leader has
# and we lack (single-digit counts on every App), and
# reports/benchmark_top1_2026-10-15.md section 3 (lever 1) puts the link on
# every page. reports/conversion_focus_2026-10-16.md also showed the Apps with
# paying units in the last 30 days (unblurry 6, onepageppt 4, wordmate 4,
# snapport 4, gmoney 3) had no link at all. Live gating stays upstream: only
# conversion targets of verified-live Apps get the block, and the read-only
# audit accepts a review link only for a live roster App.
REVIEW_APP_KEYS = tuple(sorted(APPSTORE))
REVIEW_APP_IDS = frozenset(str(APPSTORE[key]) for key in REVIEW_APP_KEYS)

# One neutral sentence per official locale. No reward, no rating value, no
# instruction about which rating to give.
REVIEW_LABELS = {
    "ar-SA": "هل تستخدم هذا التطبيق بالفعل؟ قيّمه أو اكتب مراجعة عنه في App Store",
    "bn-BD": "এই অ্যাপটি আগে থেকেই ব্যবহার করছেন? App Store-এ রেটিং দিন বা রিভিউ লিখুন",
    "ca": "Ja utilitzes aquesta app? Valora-la o escriu-ne una ressenya a l’App Store",
    "cs": "Už tuto aplikaci používáte? Ohodnoťte ji nebo napište recenzi v App Storu",
    "da": "Bruger du allerede denne app? Bedøm eller anmeld den i App Store",
    "de-DE": "Sie nutzen diese App bereits? Bewerten oder rezensieren Sie sie im App Store",
    "el": "Χρησιμοποιείτε ήδη αυτή την εφαρμογή; Βαθμολογήστε τη ή γράψτε μια κριτική στο App Store",
    "en-AU": "Already using this app? Rate or review it on the App Store",
    "en-CA": "Already using this app? Rate or review it on the App Store",
    "en-GB": "Already using this app? Rate or review it on the App Store",
    "en-US": "Already using this app? Rate or review it on the App Store",
    "es-ES": "¿Ya usas esta app? Valórala o escribe una reseña en el App Store",
    "es-MX": "¿Ya usas esta app? Califícala o escribe una reseña en el App Store",
    "fi": "Käytätkö jo tätä sovellusta? Arvioi se tai kirjoita arvostelu App Storessa",
    "fr-CA": "Vous utilisez déjà cette app? Notez-la ou rédigez un avis dans l’App Store",
    "fr-FR": "Vous utilisez déjà cette app ? Notez-la ou rédigez un avis sur l’App Store",
    "gu-IN": "આ ઍપ પહેલેથી વાપરો છો? App Store પર તેને રેટ કરો અથવા રિવ્યૂ લખો",
    "he": "כבר משתמשים באפליקציה הזו? דרגו אותה או כתבו ביקורת ב-App Store",
    "hi": "क्या आप यह ऐप पहले से इस्तेमाल कर रहे हैं? App Store पर इसे रेट करें या रिव्यू लिखें",
    "hr": "Već koristite ovu aplikaciju? Ocijenite je ili napišite recenziju u App Storeu",
    "hu": "Már használod ezt az appot? Értékeld, vagy írj róla véleményt az App Store-ban",
    "id": "Sudah memakai aplikasi ini? Beri nilai atau ulasan di App Store",
    "it": "Usi già questa app? Valutala o scrivi una recensione su App Store",
    "ja": "このアプリをお使いですか？App Store で評価・レビューできます",
    "kn-IN": "ಈ ಆ್ಯಪ್ ಅನ್ನು ಈಗಾಗಲೇ ಬಳಸುತ್ತಿದ್ದೀರಾ? App Store ನಲ್ಲಿ ರೇಟ್ ಮಾಡಿ ಅಥವಾ ವಿಮರ್ಶೆ ಬರೆಯಿರಿ",
    "ko": "이미 이 앱을 사용 중이신가요? App Store에서 평가하거나 리뷰를 작성할 수 있습니다",
    "ml-IN": "ഈ ആപ്പ് ഇതിനകം ഉപയോഗിക്കുന്നുണ്ടോ? App Store-ൽ റേറ്റ് ചെയ്യുകയോ റിവ്യൂ എഴുതുകയോ ചെയ്യാം",
    "mr-IN": "हे ॲप आधीपासून वापरता? App Store वर त्याला रेटिंग द्या किंवा परीक्षण लिहा",
    "ms": "Sudah menggunakan apl ini? Beri penilaian atau ulasan di App Store",
    "nl-NL": "Gebruik je deze app al? Beoordeel hem of schrijf een review in de App Store",
    "no": "Bruker du allerede denne appen? Gi den en vurdering eller skriv en anmeldelse i App Store",
    "or-IN": "ଏହି ଆପ୍ ପୂର୍ବରୁ ବ୍ୟବହାର କରୁଛନ୍ତି କି? App Store ରେ ରେଟିଂ ଦିଅନ୍ତୁ କିମ୍ବା ସମୀକ୍ଷା ଲେଖନ୍ତୁ",
    "pa-IN": "ਕੀ ਤੁਸੀਂ ਇਹ ਐਪ ਪਹਿਲਾਂ ਹੀ ਵਰਤਦੇ ਹੋ? App Store 'ਤੇ ਇਸਨੂੰ ਰੇਟ ਕਰੋ ਜਾਂ ਸਮੀਖਿਆ ਲਿਖੋ",
    "pl": "Już korzystasz z tej aplikacji? Oceń ją lub napisz recenzję w App Store",
    "pt-BR": "Já usa este app? Avalie ou escreva uma resenha na App Store",
    "pt-PT": "Já utiliza esta app? Classifique-a ou escreva uma crítica na App Store",
    "ro": "Folosești deja această aplicație? Evaluează-o sau scrie o recenzie în App Store",
    "ru": "Уже пользуетесь этим приложением? Оцените его или напишите отзыв в App Store",
    "sk": "Už túto aplikáciu používate? Ohodnoťte ju alebo napíšte recenziu v App Store",
    "sl-SI": "To aplikacijo že uporabljate? Ocenite jo ali napišite mnenje v App Store",
    "sv": "Använder du redan den här appen? Betygsätt eller recensera den i App Store",
    "ta-IN": "இந்த ஆப்பை ஏற்கனவே பயன்படுத்துகிறீர்களா? App Store-இல் மதிப்பிடுங்கள் அல்லது விமர்சனம் எழுதுங்கள்",
    "te-IN": "ఈ యాప్‌ను ఇప్పటికే ఉపయోగిస్తున్నారా? App Store లో రేటింగ్ ఇవ్వండి లేదా సమీక్ష రాయండి",
    "th": "ใช้แอปนี้อยู่แล้วใช่ไหม ให้คะแนนหรือเขียนรีวิวได้ใน App Store",
    "tr": "Bu uygulamayı zaten kullanıyor musunuz? App Store'da puan verin veya değerlendirme yazın",
    "uk": "Уже користуєтеся цим застосунком? Оцініть його або напишіть відгук в App Store",
    "ur-PK": "کیا آپ یہ ایپ پہلے سے استعمال کر رہے ہیں؟ App Store پر اسے ریٹ کریں یا ریویو لکھیں",
    "vi": "Bạn đang dùng ứng dụng này? Hãy xếp hạng hoặc viết đánh giá trên App Store",
    "zh-Hans": "已经在用这款 App？可以在 App Store 评分或撰写评论",
    "zh-Hant": "已經在用這款 App？可以到 App Store 評分或撰寫評論",
}
if set(REVIEW_LABELS) != set(OFFICIAL_LOCALES):
    raise RuntimeError("Review labels must cover exactly the 50 official locales")
# Copy guard: the sentence may ask for a rating, never promise or suggest one.
INCENTIVE_RE = re.compile(
    r"\b(?:5|five)[- ]?stars?\b|★|⭐|\breward|\bgift|\bfree\b|\bunlock|\bdiscount|\bcoupon|"
    r"\bprize|\bgiveaway|\bpro\b",
    re.IGNORECASE,
)
if any(INCENTIVE_RE.search(label) for label in REVIEW_LABELS.values()):
    raise RuntimeError("Review labels must stay neutral (no incentive or rating hint)")


def review_label(locale: str) -> str:
    try:
        return REVIEW_LABELS[locale]
    except KeyError as error:
        raise ValueError(f"Unsupported review-link locale: {locale!r}") from error


def is_review_app(app_id: str) -> bool:
    return str(app_id) in REVIEW_APP_IDS


PLAY_REVIEW_RE = re.compile(
    r"https://play\.google\.com/store/apps/details\?id="
    r"(?P<package>[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+)&showAllReviews=true"
)
_PLAY_PACKAGES: dict[str, str] | None = None


def play_review_url(package: str) -> str:
    """Google Play's review list for one package (no referrer: not a download link)."""
    url = f"https://play.google.com/store/apps/details?id={package}&showAllReviews=true"
    if not PLAY_REVIEW_RE.fullmatch(url):
        raise ValueError(f"Invalid Android package: {package!r}")
    return url


def play_packages() -> dict[str, str]:
    """{App Store id: Android package} from the verified Android snapshot.

    Any problem with the snapshot means "unknown": no Play review link at all
    (same rule as every Play link: a broken scan never adds or drops links)."""
    global _PLAY_PACKAGES
    if _PLAY_PACKAGES is None:
        try:
            import android_play  # noqa: PLC0415 - geo/android_play.py

            apps = android_play.load_snapshot()
            _PLAY_PACKAGES = {
                str(entry["ios_app_id"]): str(entry["package"])
                for entry in apps.values()
                if entry.get("ios_app_id") and entry.get("package")
            }
        except Exception:  # noqa: BLE001 - unknown Android status = no Play link
            _PLAY_PACKAGES = {}
    return _PLAY_PACKAGES


def play_review_href(app_id: str) -> str | None:
    package = play_packages().get(str(app_id))
    try:
        return play_review_url(package) if package else None
    except ValueError:
        return None


def review_block(app_id: str, href: str, locale: str, play_href: str | None = None) -> str:
    """The managed block for one page. ``href`` is the final (stamped) link;
    ``play_href`` (optional) is the App's Google Play review list.

    A ``<div>``, not a ``<p>``: supplemental-resource placement
    (hero_task_html) treats top-level paragraphs as the page introduction.
    """
    if play_href is not None and not PLAY_REVIEW_RE.fullmatch(play_href):
        raise ValueError(f"Invalid Google Play review URL: {play_href!r}")
    play = (
        ' · <a class="app-store-review__play" '
        f'data-play-review="{html.escape(PLAY_REVIEW_RE.fullmatch(play_href)["package"], quote=True)}" '
        f'href="{html.escape(play_href, quote=True)}" rel="nofollow noopener">Google Play</a>'
        if play_href else ""
    )
    if not is_review_app(app_id):
        raise ValueError(f"App is not a review-link roster App: {app_id}")
    if not is_app_store_review_url(href):
        raise ValueError(f"Invalid App Store review URL: {href!r}")
    path = APP_STORE_PATH_RE.fullmatch(urllib.parse.urlsplit(href).path)
    if path is None or path["app_id"] != app_id:
        raise ValueError(f"App Store review URL app mismatch: {href!r}")
    return "\n".join(
        (
            BLOCK_START,
            (
                f'<div class="app-store-review" data-app-store-review="{app_id}" '
                'style="margin:1rem 0;font-size:.9em;text-align:center">'
                f'<a class="app-store-review__link" href="{html.escape(href, quote=True)}" '
                'rel="nofollow noopener">'
                f"{html.escape(review_label(locale))}</a>{play}</div>"
            ),
            BLOCK_END,
        )
    )


# Review-only sections (2026-10-20 coverage sample: about 9% of indexable
# single-App pages had a download link but no review link, all in these
# families). They get the review link and nothing else: this list is
# deliberately separate from gen_smart_app_banners.BUYER_INTENT_SECTIONS so
# the Smart App Banner, sticky CTA, QR card and share action keep their
# current inventory. stories stays out: Web Stories are AMP documents whose
# body may only hold <amp-story> and whose single CTA validate_webstories.py
# pins, so a review block there would break the story.
REVIEW_ONLY_SECTIONS = ("tools", "data", "tutorials")
# apps/<key>/decision/l/<locale>/index.html (app_install_decision_routes.py).
DECISION_PAGE_GLOB = "apps/*/decision/l/*/index.html"
NOINDEX_RE = re.compile(
    r"<meta\b(?=[^>]*\bname=[\"']robots[\"'])"
    r"(?=[^>]*\bcontent=[\"'][^\"']*\bnoindex\b)[^>]*>",
    re.IGNORECASE,
)


def review_only_pages(pages: Path) -> set[Path]:
    """Candidate pages of the review-only families (root + official locales).

    Section index pages stay out like in the buyer-intent inventory; whether a
    candidate really gets the block (one live App, indexable, store locale) is
    decided per page by the caller.
    """
    paths: set[Path] = set()
    containers = [pages] + [
        pages / locale for locale in OFFICIAL_LOCALES if (pages / locale).is_dir()
    ]
    for container in containers:
        for section in REVIEW_ONLY_SECTIONS:
            directory = container / section
            if directory.is_dir():
                paths.update(
                    path.resolve()
                    for path in directory.glob("*.html")
                    if path.name != "index.html"
                )
    paths.update(
        path.resolve()
        for path in pages.glob(DECISION_PAGE_GLOB)
        if path.parent.name in OFFICIAL_LOCALES
    )
    return paths


def review_page_locale(path: Path, pages: Path) -> str | None:
    """Official locale of a review-only page; ``None`` when it has none."""
    parts = path.resolve().relative_to(pages.resolve()).parts
    if len(parts) == 6 and parts[0] == "apps" and parts[2:4] == ("decision", "l"):
        return parts[4] if parts[4] in OFFICIAL_LOCALES else None
    if len(parts) == 3 and parts[0] in OFFICIAL_LOCALES:
        return parts[0]
    if len(parts) == 2:
        return "en-US"
    return None


def is_noindex(source: str) -> bool:
    return bool(NOINDEX_RE.search(source))


def strip_review(source: str) -> str:
    return BLOCK_RE.sub("\n", source)


def managed_block(source: str) -> str | None:
    """The page's review block text (``None`` when absent), for counters."""
    match = BLOCK_RE.search(source)
    return match.group(0).strip() if match else None


def render_review(
    path: Path,
    source: str,
    app_id: str,
    href: str | None,
    locale: str,
    play_href: str | None | bool = True,
) -> str:
    """Place (or remove) the review block. ``href=None`` removes it.

    ``play_href=True`` (default) looks the App up in the Android snapshot;
    ``None``/``False`` leaves the Google Play review link out."""
    cleaned = strip_review(source)
    if href is None or not is_review_app(app_id):
        return cleaned
    if "</body>" not in cleaned:
        raise ValueError(f"App Store review page has no closing body: {path}")
    if play_href is True:
        play_href = play_review_href(app_id)
    block = review_block(app_id, href, locale, play_href or None)
    # Right under the QR card (the page's own install card), else at the end
    # of the main content, else before the mobile sticky CTA / </body>.
    qr_index = cleaned.find(QR_BLOCK_END)
    if qr_index >= 0:
        index = qr_index + len(QR_BLOCK_END)
    else:
        index = cleaned.rfind("</main>")
        if index < 0:
            index = cleaned.find(MOBILE_CTA_BLOCK_START)
        if index < 0:
            index = cleaned.index("</body>")
    return (
        cleaned[:index].rstrip()
        + "\n"
        + block
        + "\n"
        + cleaned[index:].lstrip()
    )


def review_target_url(app_id: str) -> str:
    """The clean link handed to the stamper (it aligns the storefront)."""
    return app_store_review_url(str(app_id))


def coverage(pages: Path = PAGES) -> dict[str, object]:
    """Read-only census of review blocks per roster App in a built tree."""
    by_app: Counter = Counter()
    pages_with_block = 0
    for path in pages.rglob("*.html"):
        relative = path.relative_to(pages).parts
        if relative and relative[0] in {"_engine", ".git", "node_modules"}:
            continue
        source = path.read_text(encoding="utf-8", errors="replace")
        if BLOCK_START not in source:
            continue
        pages_with_block += 1
        for match in re.finditer(r'data-app-store-review="(\d+)"', source):
            by_app[match.group(1)] += 1
    names = {str(APPSTORE[key]): key for key in REVIEW_APP_KEYS}
    return {
        "pages": pages_with_block,
        "by_app": {names.get(app_id, app_id): count for app_id, count in sorted(by_app.items())},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pages", type=Path, default=PAGES)
    parser.add_argument("--report", action="store_true", help="read-only coverage count")
    args = parser.parse_args()
    if not args.report:
        parser.error(
            "Rendering runs inside gen_app_store_conversion_surfaces.py; "
            "use --report for a read-only census."
        )
    print(json.dumps(coverage(args.pages), sort_keys=True))


if __name__ == "__main__":
    main()
