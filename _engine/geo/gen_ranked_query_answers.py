#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在榜詞的母語答案頁 — 把 App Store 已有的名次接到一個真的能回答問題的到達點。

背景:``agent/rank_opportunity_topics.py`` 每天把 iTunes Search proxy 讀數整理成
「這支 App 在這個 storefront 的這個母語詞已經排 1-30 名」。``rank_opportunity_pages.py``
只把這些詞當成一行文字補進既有頁面,刻意不開新 URL —— 因為「一個詞一頁、內文都一樣」
就是 doorway page。

這支腳本補的是另一半:**少數幾個名次最好、市場價值最高的詞,各寫一頁真的在回答那個
問題的內容**。內容由 ``data/ranked_query_answers.json`` 逐頁手寫(母語直接寫,不是英翻),
每頁的 短答/檢查清單/步驟/比較表/FAQ 都不一樣;英文版是同一個問題的英文說法,存在的
理由是 ``cleanup_localized_assets.py`` 會刪掉沒有英文母本的在地化 answers 頁。

版面不重造:每頁以「同一支 App、同一個語系」的既有 answers 頁為結構供體,只換內容與
URL。這樣 QR 雜湊、decision card、smart app banner、歸因 ct、免責聲明、微格式全部沿用
已經過稽核的那一份,不會因為手寫模板而漂移。

不做 git 操作;只寫自己這批的檔案。
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

from site_config import PUBLIC_SITE  # noqa: E402
from videogen.registry import APPS, APPSTORE  # noqa: E402
from app_pairs import free_first_key  # noqa: E402

PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages")).resolve()
DATA = HERE / "data" / "ranked_query_answers.json"
SITE = PUBLIC_SITE.rstrip("/")

# 每個語系的區塊標題與表頭。刻意寫死在這裡而不是從供體頁抓:供體頁的標題是逐頁翻譯的
# 產物,同一個語系裡就有好幾種寫法,抓來會讓這批頁面彼此不一致。
LABELS = {
    "en": {
        "look": "What to check before you choose",
        "steps": "The steps that actually work",
        "table": "Quick comparison",
        "cols": ("Need", "What to check", "Why it matters"),
        "fits": "Where {name} fits",
        "faq": "FAQ",
    },
    "zh-Hant": {
        "look": "選之前先確認這幾件事",
        "steps": "照著做的步驟",
        "table": "快速比較",
        "cols": ("需求", "要檢查什麼", "為什麼重要"),
        "fits": "{name} 適合的情況",
        "faq": "常見問題",
    },
    "fr-FR": {
        "look": "À vérifier avant de choisir",
        "steps": "La marche à suivre",
        "table": "Comparatif rapide",
        "cols": ("Besoin", "À vérifier", "Pourquoi c'est important"),
        "fits": "Où se situe {name}",
        "faq": "Questions fréquentes",
    },
    "pt-BR": {
        "look": "O que conferir antes de escolher",
        "steps": "O passo a passo",
        "table": "Comparação rápida",
        "cols": ("Necessidade", "O que conferir", "Por que importa"),
        "fits": "Onde o {name} se encaixa",
        "faq": "Perguntas frequentes",
    },
    "zh-Hans": {
        "look": "选之前先确认这几件事",
        "steps": "照着做的步骤",
        "table": "快速比较",
        "cols": ("需求", "要检查什么", "为什么重要"),
        "fits": "{name} 适合的情况",
        "faq": "常见问题",
    },
    "uk": {
        "look": "Що перевірити перед вибором",
        "steps": "Кроки, які справді працюють",
        "table": "Швидке порівняння",
        "cols": ("Потреба", "Що перевірити", "Чому це важливо"),
        "fits": "Де {name} підходить",
        "faq": "Поширені запитання",
    },
    "ko": {
        "look": "고르기 전에 확인할 것",
        "steps": "실제로 해볼 순서",
        "table": "빠른 비교",
        "cols": ("필요한 것", "확인할 부분", "왜 중요한가"),
        "fits": "{name}: 어떤 경우에 맞나",
        "faq": "자주 묻는 질문",
    },
    "ja": {
        "look": "選ぶ前に確認すること",
        "steps": "実際に行う手順",
        "table": "かんたん比較",
        "cols": ("必要なこと", "確認するポイント", "なぜ大事か"),
        "fits": "{name} が向いている場面",
        "faq": "よくある質問",
    },
    "de-DE": {
        "look": "Vor der Wahl prüfen",
        "steps": "So gehen Sie vor",
        "table": "Schneller Vergleich",
        "cols": ("Bedarf", "Was zu prüfen ist", "Warum es zählt"),
        "fits": "Wo {name} passt",
        "faq": "Häufige Fragen",
    },
}

LD_RE = re.compile(
    r'(<script type="application/ld\+json"[^>]*>)(.*?)(</script>)', re.S
)
ALTERNATE_RUN_RE = re.compile(
    r'(?:<link rel="alternate" hreflang="[^"]+" href="[^"]+">\n?)+'
)
PUBLICATION_LINK_RE = re.compile(
    r'<link rel="site\.standard\.publication" href="[^"]+">\n?'
)
ARTICLE_RE = re.compile(
    r'(<article class="card two answer"[^>]*>)(.*?)(</article>)', re.S
)
FAQ_SECTION_RE = re.compile(
    r'(<section class="wrap card">)(.*?)(</section>)', re.S
)
NOINDEX_RE = re.compile(
    r'<meta\b[^>]*\bname\s*=\s*"robots"[^>]*\bcontent\s*=\s*"[^"]*\bnoindex\b',
    re.I,
)
NOTICE_RE = re.compile(r'<p class="notice">.*?</p>', re.S)
PILLS_RE = re.compile(r'<p>(?:<span class="pill">[^<]*</span>)+</p>')
H1_RE = re.compile(r'(<h1[^>]*>)(.*?)(</h1>)', re.S)
LEAD_RE = re.compile(r'(<p class="lead[^"]*"[^>]*>)(.*?)(</p>)', re.S)
TITLE_RE = re.compile(r'(<title>)(.*?)(</title>)', re.S)
PROMISE_RE = re.compile(
    r'(<p class="iag-decision-card__promise" title=")([^"]*)(">)(.*?)(</p>)', re.S
)


def e(text: str) -> str:
    return html.escape(str(text), quote=False)


def a(text: str) -> str:
    """屬性值用的逸出。"""
    return html.escape(str(text), quote=True)


def page_url(locale: str, slug: str) -> str:
    if locale == "en":
        return f"{SITE}/answers/{slug}.html"
    return f"{SITE}/{locale}/answers/{slug}.html"


def answers_dir(locale: str) -> Path:
    return PAGES / "answers" if locale == "en" else PAGES / locale / "answers"


def donor_for(locale: str, key: str) -> Path:
    """同 App 同語系的既有 answers 頁,當成結構供體。"""
    app_id = APPSTORE[key]
    directory = answers_dir(locale)
    marker = f'data-app-id="{app_id}"'
    best = None
    for path in sorted(directory.glob("*.html")):
        if path.name == "index.html":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if marker not in text:
            continue
        if "LearningResource" in text or "iag-free-resource-first" in text:
            continue
        # noindex 的頁面照抄會讓新頁也帶 noindex,而 sitemap 又收錄它 ——
        # tests/test_sitemap_hygiene.py 的 closed-union 檢查會直接紅。
        if NOINDEX_RE.search(text):
            continue
        if not ARTICLE_RE.search(text) or not FAQ_SECTION_RE.search(text):
            continue
        if "app-store-qr:start" not in text or "app-decision-card:start" not in text:
            continue
        best = path
        break
    if best is None:
        raise SystemExit(f"no structural donor for {key} in {locale}")
    return best


def sub_once(pattern: re.Pattern, repl, text: str, what: str) -> str:
    out, count = pattern.subn(repl, text, count=1)
    if count != 1:
        raise SystemExit(f"expected exactly one {what}, replaced {count}")
    return out


def article_html(body: dict, labels: dict, name: str, notice: str, pills: str) -> str:
    parts = [f"<h2>{e(body['answer'])}</h2>"]
    parts += [f"<p>{e(p)}</p>" for p in body["paras"]]
    parts.append(f"<h2>{e(labels['look'])}</h2><ul class=\"checklist\">")
    parts.append("".join(f"<li>{e(x)}</li>" for x in body["look"]))
    parts.append("</ul>")
    parts.append(f"<h2>{e(labels['steps'])}</h2><ol class=\"checklist\">")
    parts.append("".join(f"<li>{e(x)}</li>" for x in body["steps"]))
    parts.append("</ol>")
    cols = labels["cols"]
    parts.append(
        f"<h2>{e(labels['table'])}</h2><table><thead><tr>"
        f"<th>{e(cols[0])}</th><th>{e(cols[1])}</th><th>{e(cols[2])}</th>"
        "</tr></thead><tbody>"
    )
    parts.append(
        "".join(
            f"<tr><td>{e(r[0])}</td><td>{e(r[1])}</td><td>{e(r[2])}</td></tr>"
            for r in body["rows"]
        )
    )
    parts.append("</tbody></table>")
    parts.append(f"<h2>{e(labels['fits'].format(name=name))}</h2>")
    parts.append(f"<p>{e(body['fits'])}</p>")
    if pills:
        parts.append(pills)
    if notice:
        parts.append(notice)
    return "".join(parts)


def faq_section_html(body: dict, labels: dict) -> str:
    items = "".join(
        '<div itemscope itemtype="https://schema.org/Question">'
        f'<h3 itemprop="name">{e(q)}</h3>'
        '<div itemprop="acceptedAnswer" itemscope itemtype="https://schema.org/Answer">'
        f'<p itemprop="text">{e(ans)}</p></div></div>'
        for q, ans in body["faq"]
    )
    return f"<h2>{e(labels['faq'])}</h2>{items}"


def rewrite_json_ld(text: str, body: dict, labels: dict, canonical: str) -> str:
    def replace(match: re.Match) -> str:
        open_tag, payload, close_tag = match.groups()
        stripped = payload.strip()
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError:
            return match.group(0)
        kind = data.get("@type")
        compact = "\n" not in stripped
        if kind == "BreadcrumbList":
            items = data.get("itemListElement", [])
            if items:
                items[-1]["name"] = body["h1"]
                items[-1]["item"] = canonical
        elif kind == "FAQPage":
            data["mainEntity"] = [
                {
                    "@type": "Question",
                    "name": q,
                    "acceptedAnswer": {"@type": "Answer", "text": ans},
                }
                for q, ans in body["faq"]
            ]
        elif kind == "HowTo":
            # 標題本身就是問句,再套「如何選擇：」會變成雙冒號。
            data["name"] = body["h1"]
            data["step"] = [
                {
                    "@type": "HowToStep",
                    "position": i + 1,
                    "name": step.split("：")[0].split(":")[0][:80],
                    "text": step,
                }
                for i, step in enumerate(body["steps"])
            ]
        elif kind in {"SoftwareApplication", "MobileApplication"}:
            data["description"] = body["meta"]
        elif kind == "WebPage":
            data["@id"] = f"{canonical}#webpage"
            data["url"] = canonical
        else:
            return match.group(0)
        if compact:
            rendered = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        else:
            rendered = "\n" + json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        return f"{open_tag}{rendered}{close_tag}"

    return LD_RE.sub(replace, text)


def render(entry: dict, locale: str) -> str:
    key = entry["key"]
    name = APPS[key]["name"]
    body = entry["en"] if locale == "en" else entry["loc"]
    labels = LABELS[locale]
    slug = entry["slug"]
    canonical = page_url(locale, slug)
    donor_path = donor_for(locale, key)
    text = donor_path.read_text(encoding="utf-8")

    donor_slug = donor_path.stem
    notice_match = NOTICE_RE.search(text)
    notice = notice_match.group(0) if notice_match else ""
    pills_match = PILLS_RE.search(text)
    pills = pills_match.group(0) if pills_match else ""

    # --- head identity -----------------------------------------------------
    text = sub_once(
        TITLE_RE, lambda m: m.group(1) + e(body["title"]) + m.group(3), text, "<title>"
    )
    text = sub_once(
        re.compile(r'(<meta name="description" content=")([^"]*)(">)'),
        lambda m: m.group(1) + a(body["meta"]) + m.group(3),
        text,
        "meta description",
    )
    text = sub_once(
        re.compile(r'(<link rel="canonical" href=")([^"]*)(">)'),
        lambda m: m.group(1) + a(canonical) + m.group(3),
        text,
        "canonical",
    )
    text = sub_once(
        re.compile(r'(<meta property="og:title" content=")([^"]*)(">)'),
        lambda m: m.group(1) + a(body["title"]) + m.group(3),
        text,
        "og:title",
    )
    text = sub_once(
        re.compile(r'(<meta property="og:description" content=")([^"]*)(">)'),
        lambda m: m.group(1) + a(body["meta"]) + m.group(3),
        text,
        "og:description",
    )
    text = sub_once(
        re.compile(r'(<meta property="og:url" content=")([^"]*)(">)'),
        lambda m: m.group(1) + a(canonical) + m.group(3),
        text,
        "og:url",
    )
    alternates = (
        f'<link rel="alternate" hreflang="en" href="{page_url("en", slug)}">\n'
        f'<link rel="alternate" hreflang="{entry["locale"]}"'
        f' href="{page_url(entry["locale"], slug)}">\n'
        f'<link rel="alternate" hreflang="x-default" href="{page_url("en", slug)}">\n'
    )
    text = sub_once(ALTERNATE_RUN_RE, lambda _m: alternates, text, "hreflang block")
    # 這條是 sync_standard_site.py 為那一頁登記的 AT Protocol 紀錄,不可沿用。
    text = PUBLICATION_LINK_RE.sub("", text)
    text = rewrite_json_ld(text, body, labels, canonical)

    # --- body --------------------------------------------------------------
    text = text.replace(
        f'value="{page_url(locale, donor_slug)}"', f'value="{canonical}"'
    )
    text = sub_once(H1_RE, lambda m: m.group(1) + e(body["h1"]) + m.group(3), text, "h1")
    text = sub_once(
        LEAD_RE, lambda m: m.group(1) + e(body["lead"]) + m.group(3), text, "lead"
    )
    if PROMISE_RE.search(text):
        text = sub_once(
            PROMISE_RE,
            lambda m: m.group(1) + a(body["lead"]) + m.group(3) + e(body["lead"]) + m.group(5),
            text,
            "decision card promise",
        )
    text = sub_once(
        ARTICLE_RE,
        lambda m: m.group(1)
        + article_html(body, labels, name, notice, pills)
        + m.group(3),
        text,
        "answer article",
    )
    text = sub_once(
        FAQ_SECTION_RE,
        lambda m: m.group(1) + faq_section_html(body, labels) + m.group(3),
        text,
        "faq section",
    )
    if page_url(locale, donor_slug) in text:
        raise SystemExit(f"donor slug leaked into {locale}/{slug}")
    return text



# --------------------------------------------------------------------------- #
# 索引與 sitemap 的最小增修
#
# answers 的索引頁與 sitemap 都有現成的產生器,但它們是「整棵樹重寫」型:
# aeo_answers.regenerate_index() 會把 gen_link_hubs / gen_store_reach 後續注入的
# 受管理區塊整段刪掉,gen_answer_hubs 與 gen_link_hubs 會掃全站。這批只新增 32 個
# slug,所以這裡只做插入:既有列表項目、既有 lastmod 一個都不動。
# --------------------------------------------------------------------------- #

CARD_RE = re.compile(
    r'<article class="card third h-entry hentry">.*?</article>', re.S
)
CARD_HREF_RE = re.compile(r'href="[^"]*/answers/([^"/]+)\.html"')
FULL_HUB_RE = re.compile(
    r'(<!--iag-link-hub-full-->.*?<ul>)(.*?)(</ul>)', re.S
)
# 縮排可有可無:每日 GEO 重建的 sitemap_answers.xml 已改成不縮排,新列沿用檔內既有縮排。
SITEMAP_URL_RE = re.compile(r'^( *)<url><loc>([^<]+)</loc><lastmod>([^<]+)</lastmod></url>', re.M)


def english_card(slug: str, title: str, app_name: str) -> str:
    return (
        '<article class="card third h-entry hentry">'
        '<h2 class="p-name entry-title">'
        f'<a class="u-url u-uid" rel="bookmark" '
        f'href="{SITE}/answers/{slug}.html">{e(title)}</a></h2>'
        f'<p class="muted p-summary entry-summary">Funnels to {e(app_name)}</p>'
        "</article>"
    )


def update_english_index(entries: list[dict]) -> bool:
    path = PAGES / "answers" / "index.html"
    text = path.read_text(encoding="utf-8")
    cards = list(CARD_RE.finditer(text))
    if not cards:
        raise SystemExit("English answers index has no cards to insert beside")
    existing = {CARD_HREF_RE.search(m.group(0)).group(1) for m in cards}
    todo = [entry for entry in entries if entry["slug"] not in existing]
    if not todo:
        return False
    # 由後往前插入,前面的比對位置才不會位移。
    for entry in sorted(todo, key=lambda x: x["slug"], reverse=True):
        cards = list(CARD_RE.finditer(text))
        card = english_card(
            entry["slug"], entry["en"]["h1"], APPS[entry["key"]]["name"]
        )
        after = None
        for match in cards:
            slug = CARD_HREF_RE.search(match.group(0)).group(1)
            if slug > entry["slug"]:
                after = match.start()
                break
        if after is None:
            after = cards[-1].end()
        text = text[:after] + card + text[after:]
    path.write_text(text, encoding="utf-8")
    return True


def update_locale_index(locale: str, entries: list[dict]) -> bool:
    path = PAGES / locale / "answers" / "index.html"
    if not path.is_file():
        raise SystemExit(f"missing localized answers index: {locale}")
    text = path.read_text(encoding="utf-8")
    match = FULL_HUB_RE.search(text)
    if match is None:
        raise SystemExit(f"no managed link-hub list in {locale}/answers/index.html")
    body = match.group(2)
    additions = []
    for entry in entries:
        url = page_url(locale, entry["slug"])
        if f'href="{url}"' in body:
            continue
        additions.append(f'<li><a href="{a(url)}">{e(entry["loc"]["title"])}</a></li>')
    if not additions:
        return False
    text = (
        text[: match.start(2)]
        + body
        + "".join(additions)
        + text[match.end(2) :]
    )
    path.write_text(text, encoding="utf-8")
    return True


def update_sitemap(entries: list[dict]) -> int:
    """只把這批的網址插進 sitemap_answers.xml,其他每一列原樣不動。

    整檔重建(aeo_answers.write_sitemap)會順手補進另外 610 個別人尚未登錄的
    網址,並把它們的 lastmod 一律改成今天 —— 那不是這批的工作,也會撞到別的
    worker,所以這裡只做插入。
    """
    import datetime as _dt

    path = PAGES / "sitemap_answers.xml"
    text = path.read_text(encoding="utf-8")
    rows = list(SITEMAP_URL_RE.finditer(text))
    if not rows:
        raise SystemExit("sitemap_answers.xml has no url rows")
    today = _dt.date.today().isoformat()
    indent = rows[0].group(1)
    wanted = []
    for entry in entries:
        wanted.append(page_url("en", entry["slug"]))
        wanted.append(page_url(entry["locale"], entry["slug"]))
    added = 0
    for url in sorted(set(wanted), reverse=True):
        rows = list(SITEMAP_URL_RE.finditer(text))
        if any(row.group(2) == url for row in rows):
            continue
        row = (
            f"{indent}<url><loc>{html.escape(url)}</loc>"
            f"<lastmod>{today}</lastmod></url>\n"
        )
        # sitemap 的順序是「英文區塊,再各語系目錄」,和產生器的兩次 glob 一致。
        key = _sitemap_key(url)
        at = None
        for candidate in rows:
            if _sitemap_key(candidate.group(2)) > key:
                at = candidate.start()
                break
        if at is None:
            at = rows[-1].end() + 1
        text = text[:at] + row + text[at:]
        added += 1
    path.write_text(text, encoding="utf-8")
    return added


def _sitemap_key(url: str) -> tuple[int, str]:
    rest = url[len(SITE) + 1 :]
    return (0, rest) if rest.startswith("answers/") else (1, rest)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DATA)
    parser.add_argument("--only", help="只做這個 slug")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    entries = json.loads(args.data.read_text(encoding="utf-8"))
    written = 0
    for entry in entries:
        if args.only and entry["slug"] != args.only:
            continue
        if entry["key"] != free_first_key(entry["key"]):
            raise SystemExit(
                f"{entry['slug']}: 品類語境必須導免費門 "
                f"({entry['key']} -> {free_first_key(entry['key'])})"
            )
        for locale in ("en", entry["locale"]):
            rendered = render(entry, locale)
            target = answers_dir(locale) / f"{entry['slug']}.html"
            if args.dry_run:
                print(f"DRY {target.relative_to(PAGES)} {len(rendered)}b", flush=True)
                continue
            if target.exists() and target.read_text(encoding="utf-8") == rendered:
                print(f"SAME {target.relative_to(PAGES)}", flush=True)
                continue
            target.write_text(rendered, encoding="utf-8")
            written += 1
            print(f"WROTE {target.relative_to(PAGES)}", flush=True)
    print(f"ranked-query answers: {written} files", flush=True)
    if args.dry_run or args.only:
        return 0
    if update_english_index(entries):
        print("INDEX answers/index.html updated", flush=True)
    for locale in sorted({entry["locale"] for entry in entries}):
        rows = [entry for entry in entries if entry["locale"] == locale]
        if update_locale_index(locale, rows):
            print(f"INDEX {locale}/answers/index.html updated", flush=True)
    print(f"SITEMAP sitemap_answers.xml +{update_sitemap(entries)} urls", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
