#!/usr/bin/env python3
"""Generate localized portfolio catalogs from verified public App Store entries."""
from __future__ import annotations

import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))
sys.path.insert(0, HERE)

from appstore_live import live_app_keys  # noqa: E402
from videogen.registry import APPS, APPSTORE, appstore_url  # noqa: E402

PAGES = os.path.join(HERE, "pages")
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide").rstrip("/")

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
    },
}

CSS = """:root{--bg:#f6f7fb;--card:#fff;--ink:#151a2b;--muted:#616a7c;--line:#e2e6ef;--accent:#4f46e5}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(180deg,#fff,var(--bg));color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;line-height:1.55}
a{color:var(--accent);text-decoration:none}.wrap{width:min(1120px,100% - 32px);margin:auto}.hero{padding:48px 0 22px}.eyebrow{font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);font-size:.78rem}
h1{font-size:clamp(2rem,6vw,4rem);line-height:1.04;margin:.18em 0}.lead{max-width:780px;color:var(--muted);font-size:1.14rem}
h2{margin:34px 0 14px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:16px}
.card{display:flex;flex-direction:column;gap:10px;padding:20px;background:var(--card);border:1px solid var(--line);border-radius:20px;box-shadow:0 12px 34px rgba(30,38,72,.06)}
.card h3{margin:0;font-size:1.17rem}.card p{margin:0;color:var(--muted)}.links{display:flex;flex-wrap:wrap;gap:9px;margin-top:auto;padding-top:8px}
.links a{padding:9px 12px;border:1px solid var(--line);border-radius:999px;font-weight:750}.links a.store{color:#fff;background:var(--accent);border-color:var(--accent)}
.footer{margin-top:42px;padding:26px 0;border-top:1px solid var(--line);color:var(--muted)}"""


def localized_summary(key, locale):
    path = os.path.join(PAGES, locale, f"{key}.html")
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read(12000)
    except OSError:
        return (
            SUMMARY_FALLBACKS.get(locale, {}).get(key)
            or APPS[key].get("sub")
            or APPS[key].get("tag")
            or ""
        ).strip()
    match = re.search(
        r'<meta\s+name=["\']description["\']\s+content=(["\'])(.*?)\1',
        text,
        flags=re.I | re.S,
    )
    if not match:
        return (APPS[key].get("sub") or APPS[key].get("tag") or "").strip()
    return html.unescape(match.group(2)).strip()


def detail_url(key, locale):
    localized = os.path.join(PAGES, locale, f"{key}.html")
    chosen = locale if os.path.exists(localized) else "en-US"
    return f"{SITE}/{chosen}/{key}.html"


def render_catalog(code, live_keys):
    t = L10N[code]
    canonical = f"{SITE}/{t['path']}"
    groups = {}
    for key in APPS:
        if key in live_keys:
            groups.setdefault(APPS[key].get("category", "other"), []).append(key)

    sections = []
    item_list = []
    position = 0
    for category, keys in groups.items():
        cards = []
        for key in keys:
            position += 1
            app = APPS[key]
            store = appstore_url(key)
            guide = detail_url(key, t["locale"])
            hub = f"{SITE}/hubs/{key}.html"
            summary = localized_summary(key, t["locale"])
            cards.append(
                f'<article class="card" id="{html.escape(key)}"><h3>{html.escape(app["name"])}</h3>'
                f'<p>{html.escape(summary)}</p><div class="links">'
                f'<a href="{html.escape(guide)}">{html.escape(t["guide"])}</a>'
                f'<a href="{html.escape(hub)}">{html.escape(t["hub"])}</a>'
                f'<a class="store" href="{html.escape(store)}" rel="nofollow sponsored">{html.escape(t["store"])}</a>'
                f'</div></article>'
            )
            item_list.append({
                "@type": "ListItem",
                "position": position,
                "item": {
                    "@type": "SoftwareApplication",
                    "name": app["name"],
                    "operatingSystem": "iOS",
                    "applicationCategory": category,
                    "url": guide,
                    "installUrl": store,
                },
            })
        label = t["categories"].get(category, t["categories"]["other"])
        sections.append(f'<section><h2>{html.escape(label)}</h2><div class="grid">{"".join(cards)}</div></section>')

    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": t["title"],
        "url": canonical,
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(item_list),
            "itemListElement": item_list,
        },
    }
    alternates = "\n".join(
        f'<link rel="alternate" hreflang="{lang}" href="{SITE}/{data["path"]}">'
        for lang, data in L10N.items()
    )
    return f'''<!DOCTYPE html>
<html lang="{t["lang"]}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(t["title"])}</title><meta name="description" content="{html.escape(t["description"])}">
<link rel="canonical" href="{canonical}">
{alternates}
<link rel="alternate" hreflang="x-default" href="{SITE}/{L10N["en"]["path"]}">
<meta property="og:type" content="website"><meta property="og:title" content="{html.escape(t["title"])}">
<meta property="og:description" content="{html.escape(t["description"])}"><meta property="og:url" content="{canonical}">
<style>{CSS}</style><script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>
</head><body><main class="wrap"><header class="hero"><div class="eyebrow">Lumi Apps</div>
<h1>{html.escape(t["h1"])}</h1><p class="lead">{html.escape(t["lead"])}</p></header>
{"".join(sections)}</main><footer class="footer"><div class="wrap">{html.escape(t["description"])}</div></footer></body></html>'''


def main():
    live_keys = live_app_keys(APPSTORE, PAGES, refresh=False)
    for code, config in L10N.items():
        path = os.path.join(PAGES, config["path"])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(render_catalog(code, live_keys))
    print(f"✓ {len(L10N)} localized app catalogs · {len(live_keys)} public apps")


if __name__ == "__main__":
    main()
