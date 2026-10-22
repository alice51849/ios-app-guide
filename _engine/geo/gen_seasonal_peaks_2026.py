#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""檔期意圖頁（2026-10-23 預製：萬聖節、雙 11、韓國修能、感恩節＋黑色星期五）→ <Guide>/<lang>/seasonal/<slug>.html。

背景：業主 2026-10-22 深夜「多派人手可以做更快你就派 全速前進 我要用最快的方式做所有的宣傳」；
一個月一億（11-21 期限）期間的大檔期先把頁做好上線，不等檔期前才趕。每頁手寫，標題與網址用使用者
在檔期會搜的字（例：「halloween photo filter app」「雙11 購物清單」「수능 공부 앱」），內文回答他們
搜這個詞時真正想解決的事。

規則（CLAUDE.md）：
- 功能句只取 data/<key>_full.json 該語系商店文案；不寫價格、免費、Free、Pro（商店名本身含 Pro 的不算）。
- 每頁一張主卡（＋同系列或互補的第二張），附該國商店 App Store 直連（pt＋ct＋mt）；
  ct＝ln_<key>_<檔期碼>_<國碼>_gw_<MMDD>（hw 萬聖節、sd 雙 11、sn 修能、tg 感恩節、bf 黑色星期五、gf 送禮），
  超過 30 字元時省略日期（agent/ct_codes.LN_RE 允許）。Google Play 連結由 android_play.inject_html 依已發布快照補上。
- 每頁專屬內容：中日文 ≥450 個漢字／假名、韓文 ≥600 個音節、泰文 ≥1200 個泰文字母、
  英文／印尼文／巴西葡文 ≥450 個詞。
- 只寫這些頁與各語系 sitemap_seasonal_<lang>.xml 的這幾列；不做 git 操作。

    GEO_PAGES=<Guide 工作樹> python3 geo/gen_seasonal_peaks_2026.py           # 產生
    GEO_PAGES=<Guide 工作樹> python3 geo/gen_seasonal_peaks_2026.py --check   # 只檢查，有差異回 1
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for entry in (HERE, ROOT / "social"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import android_play  # noqa: E402
import first_party_disclosure  # noqa: E402
from app_store_storefronts import validated_app_store_url  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402

PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages")).resolve()
SITE = os.environ.get("GEO_SITE", PUBLIC_SITE).rstrip("/")
SECTION = "seasonal"
UPDATED = "2026-10-23"
CAMPAIGN_DATE = "1023"
PROVIDER_TOKEN = "118326163"  # 公開值：站上每個 App Store 連結的 pt= 都是它
MAX_CT = 30                   # app_store_storefronts.CAMPAIGN_TOKEN_RE 的上限
SEGS = {"halloween": "hw", "singles_day": "sd", "suneung": "sn", "thanksgiving": "tg",
        "black_friday": "bf", "gifts": "gf"}
FLOORS = {"zh-Hant": 450, "zh-Hans": 450, "ja": 450, "ko": 600, "th": 1200,
          "en": 450, "id": 450, "pt-BR": 450}
BANNED = re.compile(
    r"免費|免费|無料|무료|ฟรี|\bgratis\b|grátis|\bgrátis\b|\bfree\b|\bpro\b|NT\$|US\$|R\$|\$\s?\d|¥\s?\d|￥|"
    r"\d\s?円|\d\s?元|\d\s?원|\d\s?บาท|\bRp\s?\d",
    re.IGNORECASE,
)
CJK = re.compile(r"[぀-ヿ㐀-鿿]")
HANGUL = re.compile(r"[가-힣]")
THAI = re.compile(r"[฀-๿]")
WORD = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)*")

# 頁面語系 → 商店語系（data/<key>_full.json）、App 介紹頁目錄、商店國碼、介面字。
LANGS = {
    "en": {"store": "en-US", "dir": "en-US", "cc": "us", "og": "en_US", "html": "en",
           "home": "iOS App Guide", "answers": "Answers", "about": "About", "crumb": "Seasonal guides",
           "updated": "Updated", "cta": "Download on the App Store →", "more": "Full app overview",
           "faq": "FAQ", "related": "Related pages", "toc": "On this page", "home_label": "Home"},
    "zh-Hant": {"store": "zh-Hant", "dir": "zh-Hant", "cc": "tw", "og": "zh_TW", "html": "zh-Hant",
                "home": "iOS App 指南", "answers": "答案", "about": "關於", "crumb": "檔期推薦",
                "updated": "更新日期", "cta": "在 App Store 下載 →", "more": "看完整介紹",
                "faq": "常見問題", "related": "相關頁面", "toc": "本頁目錄", "home_label": "首頁"},
    "zh-Hans": {"store": "zh-Hans", "dir": "zh-Hans", "cc": "cn", "og": "zh_CN", "html": "zh-Hans",
                "home": "iOS App 指南", "answers": "答案", "about": "关于", "crumb": "节日推荐",
                "updated": "更新日期", "cta": "在 App Store 下载 →", "more": "查看完整介绍",
                "faq": "常见问题", "related": "相关页面", "toc": "本页目录", "home_label": "首页"},
    "ja": {"store": "ja", "dir": "ja", "cc": "jp", "og": "ja_JP", "html": "ja",
           "home": "iOS アプリガイド", "answers": "回答", "about": "概要", "crumb": "季節のおすすめ",
           "updated": "更新日", "cta": "App Store でダウンロード →", "more": "アプリの詳しい紹介",
           "faq": "よくある質問", "related": "関連ページ", "toc": "目次", "home_label": "ホーム"},
    "ko": {"store": "ko", "dir": "ko", "cc": "kr", "og": "ko_KR", "html": "ko",
           "home": "iOS 앱 가이드", "answers": "답변", "about": "소개", "crumb": "시즌 추천",
           "updated": "업데이트", "cta": "App Store에서 다운로드 →", "more": "앱 자세히 보기",
           "faq": "자주 묻는 질문", "related": "관련 페이지", "toc": "이 페이지", "home_label": "홈"},
    "th": {"store": "th", "dir": "th", "cc": "th", "og": "th_TH", "html": "th",
           "home": "คู่มือแอป iOS", "answers": "คำตอบ", "about": "เกี่ยวกับ", "crumb": "แนะนำตามเทศกาล",
           "updated": "อัปเดต", "cta": "ดาวน์โหลดบน App Store →", "more": "ดูรายละเอียดแอป",
           "faq": "คำถามที่พบบ่อย", "related": "หน้าที่เกี่ยวข้อง", "toc": "ในหน้านี้", "home_label": "หน้าแรก"},
    "id": {"store": "id", "dir": "id", "cc": "id", "og": "id_ID", "html": "id",
           "home": "Panduan Aplikasi iOS", "answers": "Jawaban", "about": "Tentang", "crumb": "Panduan musiman",
           "updated": "Diperbarui", "cta": "Unduh di App Store →", "more": "Lihat ulasan lengkap",
           "faq": "Pertanyaan umum", "related": "Halaman terkait", "toc": "Di halaman ini", "home_label": "Beranda"},
    "pt-BR": {"store": "pt-BR", "dir": "pt-BR", "cc": "br", "og": "pt_BR", "html": "pt-BR",
              "home": "Guia de Apps iOS", "answers": "Respostas", "about": "Sobre", "crumb": "Guias da temporada",
              "updated": "Atualizado", "cta": "Baixar na App Store →", "more": "Ver o app completo",
              "faq": "Perguntas frequentes", "related": "Páginas relacionadas", "toc": "Nesta página",
              "home_label": "Início"},
}

APP_IDS = {
    "photocream": "6781808054", "unblurry": "6782275018", "countdaysnow": "6807079789", "mochi": "6785004775",
    "hourstag": "6754218117", "hourstaglite": "6794039979", "shotinbox": "6802166527", "gmoney": "6755782939",
    "studydown": "6807335593", "lockhour": "6780107485", "wordmate": "6789917808", "dailymate": "6790418321",
    "tripbee": "6787754435", "tripbeelite": "6791299610", "savetag": "6802505528",
}

CSS = """
:root{--bg:#f7f7fb;--card:#fff;--ink:#161622;--muted:#5d6370;--line:#e6e7ef;--brand:#5b5ff2;--ok:#0f8f5f}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"PingFang TC","Hiragino Sans","Apple SD Gothic Neo","Noto Sans TC","Noto Sans JP","Noto Sans KR","Noto Sans Thai","Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--ink);line-height:1.75}
a{color:var(--brand)}
.wrap{max-width:860px;margin:0 auto;padding:0 16px}
header.top{background:#fff;border-bottom:1px solid var(--line)}
.nav{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;padding:12px 16px}
.nav a{text-decoration:none;font-weight:600}
.breadcrumb{font-size:.85rem;color:var(--muted);margin:18px 0 4px}
h1{font-size:1.6rem;line-height:1.35;margin:.3rem 0 .6rem}
h2{font-size:1.2rem;margin:2rem 0 .8rem}
h3{font-size:1.02rem;margin:0 0 .35rem}
.lead{font-size:1.05rem;color:#30323d}
.updated{font-size:.82rem;color:var(--muted)}
.toc{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 14px;font-size:.92rem;margin:1rem 0}
.points{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px 18px 12px 34px}
.points li{margin:.4rem 0}
.steps{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 18px 14px 36px}
.steps li{margin:.35rem 0}
.cards{display:grid;gap:12px}
.app{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.app p{margin:.3rem 0}
.cta{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-top:.5rem}
.dl{display:inline-block;background:var(--brand);color:#fff;padding:.45rem 1rem;border-radius:10px;text-decoration:none;font-weight:600;font-size:.92rem}
.android-play{font-size:.85rem;margin:.2rem 0 0}
.more{font-size:.88rem}
details.faq{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:.7rem 1rem;margin:.6rem 0}
details.faq summary{cursor:pointer;font-weight:600}
.related ul{padding-left:1.2rem}
.legal{font-size:.78rem;color:var(--muted);margin:2rem 0 2.5rem}
@media (prefers-color-scheme:dark){:root{--bg:#121218;--card:#1c1c24;--ink:#ececf3;--muted:#a3a7b3;--line:#2c2d38;--brand:#8f93ff;--ok:#5fd3a0}
header.top{background:#16161d}.lead{color:#d6d8e0}}
""".strip()


class GenerationError(RuntimeError):
    """The pages cannot be published as written; nothing is written."""


# --------------------------------------------------------------------------------------------
# 頁面內容（每頁手寫；功能句對照 data/<key>_full.json 該語系商店文案）
# sections：(h2, 段落清單, 條列清單)；cards：(key, 卡片文字)；第一張是主卡。
# --------------------------------------------------------------------------------------------
from seasonal_peaks_2026_pages import PAGE_SPECS  # noqa: E402


# --------------------------------------------------------------------------------------------
def esc(value: str) -> str:
    return html.escape(value, quote=True)


def url_for(relative: str) -> str:
    return f"{SITE}/{relative}"


def page_relative(spec: dict) -> str:
    return f"{spec['lang']}/{SECTION}/{spec['slug']}.html"


def sitemap_name(lang: str) -> str:
    return f"sitemap_{SECTION}_{lang}.xml"


def campaign(key: str, event: str, cc: str) -> str:
    """ln_<key>_<檔期碼>_<cc>_gw_<MMDD>；超過 30 字元就省略日期。"""
    seg = SEGS[event]
    token = f"ln_{key}_{seg}_{cc}_gw_{CAMPAIGN_DATE}"
    if len(token) > MAX_CT:
        token = f"ln_{key}_{seg}_{cc}_gw"
    if len(token) > MAX_CT or not re.fullmatch(r"ln_[a-z0-9]+_[a-z]+_[a-z]{2}_gw(?:_\d{4})?", token):
        raise GenerationError(f"campaign token does not fit: {token!r}")
    return token


def store_url(key: str, lang: str, event: str) -> str:
    info = LANGS[lang]
    app_id = APP_IDS[key]
    url = (f"https://apps.apple.com/{info['cc']}/app/id{app_id}"
           f"?pt={PROVIDER_TOKEN}&ct={campaign(key, event, info['cc'])}&mt=8")
    return validated_app_store_url(url, app_id, expected_locale=info["store"], require_campaign=True,
                                   provider_token=PROVIDER_TOKEN)


def store_names(data_dir: Path = ROOT / "data") -> dict[tuple[str, str], str]:
    """(key, page lang) → 該國商店名（data/<key>_full.json）。"""
    out = {}
    for spec in PAGE_SPECS:
        store = LANGS[spec["lang"]]["store"]
        for key, _ in spec["cards"]:
            path = data_dir / f"{key}_full.json"
            if not path.exists():
                raise GenerationError(f"{key}: missing {path.name}")
            name = (json.loads(path.read_text(encoding="utf-8")).get(store) or {}).get("name")
            if not name:
                raise GenerationError(f"{key}: no {store} store name")
            out[(key, spec["lang"])] = name
    return out


def _card(key: str, text: str, spec: dict, names: dict) -> str:
    lang = spec["lang"]
    info = LANGS[lang]
    name = names[(key, lang)]
    cta = f'<a class="dl" href="{esc(store_url(key, lang, spec["event"]))}" rel="noopener">{esc(info["cta"])}</a>'
    cta += f' <a class="more" href="{esc(url_for(f"{info["dir"]}/{key}.html"))}">{esc(info["more"])}</a>'
    return "\n".join([f'<article class="app" id="app-{esc(key)}">', f"<h3>{esc(name)}</h3>",
                      f"<p>{esc(text)}</p>", f'<p class="cta">{cta}</p>', "</article>"])


def render(spec: dict, names: dict) -> str:
    lang = spec["lang"]
    info = LANGS[lang]
    relative = page_relative(spec)
    canonical = url_for(relative)
    home = url_for(f"{info['dir']}/index.html")
    blocks, toc = [], []
    for number, (title, paras, points) in enumerate(spec["sections"], 1):
        anchor = f"s{number}"
        toc.append(f'<a href="#{anchor}">{esc(title)}</a>')
        body = "".join(f"<p>{esc(p)}</p>" for p in paras)
        if points:
            body += '<ul class="points">' + "".join(f"<li>{esc(p)}</li>" for p in points) + "</ul>"
        blocks.append(f'<section id="{anchor}"><h2>{esc(title)}</h2>{body}</section>')
    steps = "".join(f"<li>{esc(step)}</li>" for step in spec["steps"])
    blocks.append(f'<section id="steps"><h2>{esc(spec["steps_title"])}</h2><ol class="steps">{steps}</ol></section>')
    toc.append(f'<a href="#steps">{esc(spec["steps_title"])}</a>')
    cards = "\n".join(_card(key, text, spec, names) for key, text in spec["cards"])
    blocks.append(f'<section id="apps"><div class="cards">\n{cards}\n</div></section>')
    faqs = "".join(f'<details class="faq"><summary>{esc(q)}</summary><p>{esc(a)}</p></details>'
                   for q, a in spec["faqs"])
    related = "".join(f'<li><a href="{esc(url_for(rel))}">{esc(label)}</a></li>' for rel, label in spec["related"])
    main_key = spec["cards"][0][0]
    ld = [
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": info["home"], "item": home},
            {"@type": "ListItem", "position": 2, "name": spec["h1"], "item": canonical},
        ]},
        {"@context": "https://schema.org", "@type": "Article", "headline": spec["h1"], "inLanguage": info["html"],
         "dateModified": UPDATED, "mainEntityOfPage": canonical, "keywords": ", ".join(spec["terms"]),
         "about": {"@type": "SoftwareApplication", "name": names[(main_key, lang)], "operatingSystem": "iOS",
                   "applicationCategory": "MobileApplication", "url": url_for(f"{info['dir']}/{main_key}.html")}},
        {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in spec["faqs"]
        ]},
    ]
    ld_json = json.dumps(ld, ensure_ascii=False, indent=1).replace("</", "<\\/")
    return f"""<!DOCTYPE html>
<html lang="{info['html']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(spec['title'])}</title>
<meta name="description" content="{esc(spec['desc'])}">
<meta name="robots" content="index,follow,max-image-preview:large">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="article">
<meta property="og:locale" content="{info['og']}">
<meta property="og:title" content="{esc(spec['title'])}">
<meta property="og:description" content="{esc(spec['desc'])}">
<meta property="og:url" content="{esc(canonical)}">
<meta property="article:modified_time" content="{UPDATED}">
<meta name="apple-itunes-app" content="app-id={APP_IDS[main_key]}">
<style>
{CSS}
</style>
<script type="application/ld+json">
{ld_json}
</script>
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{esc(home)}">{esc(info['home'])}</a><nav><a href="{esc(url_for(f"{info['dir']}/answers/index.html"))}">{esc(info['answers'])}</a> · <a href="{esc(url_for('about.html'))}">{esc(info['about'])}</a></nav></div></header>
<main class="wrap">
<div class="breadcrumb"><a href="{esc(home)}">{esc(info['home_label'])}</a> / {esc(info['crumb'])}</div>
<h1>{esc(spec['h1'])}</h1>
<p class="lead">{esc(spec['lead'])}</p>
<p class="updated">{esc(info['updated'])}: {UPDATED}</p>
{''.join(f'<p>{esc(p)}</p>' for p in spec['intro'])}
<nav class="toc" aria-label="{esc(info['toc'])}">{' · '.join(toc)}</nav>
{chr(10).join(blocks)}
<section><h2>{esc(info['faq'])}</h2>{faqs}</section>
<section class="related"><h2>{esc(info['related'])}</h2><ul>{related}</ul></section>
</main>
</body>
</html>
"""


def visible_text(source: str) -> str:
    main = re.search(r"<main\b.*?</main>", source, re.S)
    text = re.sub(r"<[^>]+>", " ", main.group(0) if main else "")
    return html.unescape(text)


def dedicated_size(lang: str, text: str) -> int:
    if lang in ("zh-Hant", "zh-Hans", "ja"):
        return len(CJK.findall(text))
    if lang == "ko":
        return len(HANGUL.findall(text))
    if lang == "th":
        return len(THAI.findall(text))
    return len(WORD.findall(text))


def without_store_names(text: str, spec: dict, names: dict) -> str:
    """商店名（例：PhotoCream Pro: Film Filters）是商店原名，不算宣稱；掃禁用字前先拿掉。"""
    for key, _ in spec["cards"]:
        text = text.replace(names.get((key, spec["lang"]), "\0"), " ")
    return text


def page_problems(spec: dict, source: str, pages: Path | None = None, names: dict | None = None) -> list[str]:
    names = names if names is not None else store_names()
    relative = page_relative(spec)
    problems = []
    text = visible_text(source)
    size = dedicated_size(spec["lang"], text)
    # 共用注入器補的 Google Play 列用 Play 上架原名（可能含 Pro），不是本頁的宣稱。
    text = visible_text(re.sub(r'<p class="android-play"[^>]*>.*?</p>', " ", source, flags=re.S))
    floor = FLOORS[spec["lang"]]
    if size < floor:
        problems.append(f"{relative}: dedicated text {size} under {floor}")
    head = source.split("</head>", 1)[0]
    head_text = re.sub(r"<script\b.*?</script>", "", head, flags=re.S)
    scan = without_store_names(html.unescape(text + head_text), spec, names)
    for found in BANNED.finditer(scan):
        problems.append(f"{relative}: banned price/free/pro wording {found.group(0)!r}")
    info = LANGS[spec["lang"]]
    for href in re.findall(r'href="(https://apps\.apple\.com/[^"]+)"', source):
        url = html.unescape(href)
        try:
            validated_app_store_url(url, expected_locale=info["store"], require_campaign=True)
        except ValueError as error:
            problems.append(f"{relative}: {error}")
    cards = re.findall(r'<article class="app"[^>]*>.*?</article>', source, re.S)
    if not cards:
        problems.append(f"{relative}: no app cards")
    for card in cards:
        if f"https://apps.apple.com/{info['cc']}/app/id" not in card:
            problems.append(f"{relative}: card without a direct App Store link")
    if pages is not None:
        for href in set(re.findall(r'href="(' + re.escape(SITE) + r'/[^"#]+)"', source)):
            target = href[len(SITE) + 1:]
            if target == relative:
                continue
            path = pages / target
            if not path.is_file():
                problems.append(f"{relative}: internal link target missing {target}")
            elif re.search(r'<meta[^>]+name="robots"[^>]+noindex', path.read_text(encoding="utf-8", errors="ignore")):
                problems.append(f"{relative}: internal link target is noindex {target}")
    return problems


def finalize(source: str, relative: str, android_apps: dict) -> str:
    source = android_play.inject_html(source, android_apps)
    return first_party_disclosure.finalize_page(source, relative)


def build(android_apps: dict, *, pages: Path | None = None, names: dict | None = None) -> dict[str, str]:
    names = names if names is not None else store_names()
    out, problems, slugs = {}, [], set()
    for spec in PAGE_SPECS:
        relative = page_relative(spec)
        if relative in slugs:
            problems.append(f"duplicate page {relative}")
        slugs.add(relative)
        if spec["event"] not in SEGS:
            problems.append(f"{relative}: unknown event {spec['event']}")
            continue
        out[relative] = finalize(render(spec, names), relative, android_apps)
        problems += page_problems(spec, out[relative], pages, names)
    if problems:
        raise GenerationError("\n".join(problems))
    return out


def merge_sitemap(source: str, urls: list[str], lastmod: str = UPDATED) -> str:
    """Add the missing <url> rows before </urlset>; rows already present are left as they are."""
    rows = [f"<url><loc>{esc(url)}</loc><lastmod>{lastmod}</lastmod></url>"
            for url in urls if f"<loc>{esc(url)}</loc>" not in source]
    if not rows:
        return source
    if "</urlset>" not in source:
        raise GenerationError("sitemap has no </urlset>")
    head, tail = source.rsplit("</urlset>", 1)
    return head + "\n".join(rows) + "\n</urlset>" + tail


def launches() -> list[dict]:
    """aso/search_reality/seasonal_launches.jsonl 的列（每頁每張卡一列：app_key、country、url）。"""
    rows = []
    for spec in PAGE_SPECS:
        info = LANGS[spec["lang"]]
        for key, _ in spec["cards"]:
            rows.append({"app_key": key, "country": info["cc"], "event": spec["event"],
                         "url": url_for(page_relative(spec)), "store_url": store_url(key, spec["lang"], spec["event"])})
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="只檢查，不寫檔")
    parser.add_argument("--pages", type=Path, default=PAGES)
    args = parser.parse_args(argv)
    pages = args.pages.resolve()
    try:
        android_apps = android_play.load_snapshot()
    except (OSError, ValueError) as error:  # an untrusted snapshot publishes no Play link
        print(f"android snapshot ignored: {error}", file=sys.stderr)
        android_apps = {}
    out = build(android_apps, pages=pages)
    writes = dict(out)
    for lang in sorted({spec["lang"] for spec in PAGE_SPECS}):
        name = sitemap_name(lang)
        urls = [url_for(page_relative(s)) for s in PAGE_SPECS if s["lang"] == lang]
        writes[name] = merge_sitemap((pages / name).read_text(encoding="utf-8"), urls)
    changed = []
    for relative, source in writes.items():
        path = pages / relative
        if not path.exists() or path.read_text(encoding="utf-8") != source:
            changed.append(relative)
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(source, encoding="utf-8")
    print(json.dumps({"pages": sorted(out), "changed": changed, "android_apps": len(android_apps),
                      "sizes": {page_relative(s): dedicated_size(s["lang"], visible_text(out[page_relative(s)]))
                                for s in PAGE_SPECS}}, ensure_ascii=False, indent=1))
    return 1 if args.check and changed else 0


if __name__ == "__main__":
    sys.exit(main())
