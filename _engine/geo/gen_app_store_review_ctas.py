#!/usr/bin/env python3
"""Add a neutral existing-user "rate or review" link to focus-App pages.

BM-13 / BM-47 (reports/benchmark_top1_checklist_2026-10-15.md): every page
about one of the ten focus Apps carries Apple's direct review action,
``https://apps.apple.com/[cc/]app/id<N>?action=write-review``.

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

# The ten focus Apps of the 2026-10-15 benchmark checklist (registry keys),
# plus the rest of the A-group roster (coverage audit 2026-10-16): every
# live App's pages carry the same neutral existing-user review link, because
# the benchmark found review count is the one lever every category leader
# has and we lack (single-digit counts on every App).
REVIEW_APP_KEYS = (
    "claudeusagemini",  # UsageNow
    "mochi",
    "battai",
    "lumiweather",
    "cvdesk",
    "cyca",
    "aim990",
    "lumibopomofo",
    "dbhalo",
    "zipbox",
    # A-group additions (2026-10-16)
    "aibriefpack",
    "lumibopomofopro",
    "caldaily",
    "countdaysnow",
    "dailymate",
    "dailymatelite",
    "gmoney",
    "gmoneylite",
    "hourstag",
    "hourstaglite",
    "ledmovingtext",
)
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


def review_block(app_id: str, href: str, locale: str) -> str:
    """The managed block for one page. ``href`` is the final (stamped) link.

    A ``<div>``, not a ``<p>``: supplemental-resource placement
    (hero_task_html) treats top-level paragraphs as the page introduction.
    """
    if not is_review_app(app_id):
        raise ValueError(f"App is not a review-link focus App: {app_id}")
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
                f"{html.escape(review_label(locale))}</a></div>"
            ),
            BLOCK_END,
        )
    )


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
) -> str:
    """Place (or remove) the review block. ``href=None`` removes it."""
    cleaned = strip_review(source)
    if href is None or not is_review_app(app_id):
        return cleaned
    if "</body>" not in cleaned:
        raise ValueError(f"App Store review page has no closing body: {path}")
    block = review_block(app_id, href, locale)
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
    """Read-only census of review blocks per focus App in a built tree."""
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
