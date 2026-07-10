#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO 機器可讀層生成器 — llms.txt + llms-full.txt + robots + sitemap index。

讓 LLM 爬蟲(GPTBot/ClaudeBot/PerplexityBot/Google-Extended…)最容易「讀懂並引用」你:
  • llms.txt:AI 爬蟲索引 — 已公開 app 一句話價值 + App Store 連結。
  • llms-full.txt:從真實頁面與 registry 重建的完整 crawler map,不再手動過期。
  • robots.txt:明確歡迎各 AI bot,並列出全部 sitemap(含 alternatives/answers)。
  • sitemap_index.xml:把三張 sitemap 串成索引,讓爬蟲一次抓全。

不碰 app code。沿用 registry + aeo_sov.json。

    python geo/gen_llms.py            # 產檔(不部署)
    python geo/gen_llms.py --publish  # 並 git push + IndexNow
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))
from videogen.registry import APPS, APPSTORE, appstore_url  # noqa: E402
from appstore_live import live_app_keys  # noqa: E402
try:
    from aeo_pages import disp  # 競品顯示名
except Exception:  # noqa: BLE001
    def disp(x):
        return " ".join(w.capitalize() for w in (x or "").split())

PAGES = os.path.join(HERE, "pages")
ALT = os.path.join(PAGES, "alternatives")
GUIDES = os.path.join(PAGES, "guides")
DATA_DIR = os.path.join(PAGES, "data")
TOOLS = os.path.join(PAGES, "tools")
STORIES = os.path.join(PAGES, "stories")
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide").rstrip("/")
SOV = os.path.join(HERE, "reports", "aeo_sov.json")

AI_BOTS = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "anthropic-ai",
           "Claude-Web", "PerplexityBot", "Perplexity-User", "Google-Extended",
           "Googlebot", "Bingbot", "Applebot", "Applebot-Extended", "CCBot",
           "Amazonbot", "Bytespider", "Meta-ExternalAgent", "DuckDuckBot",
           "cohere-ai", "YandexBot", "PetalBot"]

EXTERNAL_REPOS = [
    ("awesome-zhuyin-bopomofo-apps", "Zhuyin/Bopomofo learning apps for Taiwanese parents (Chinese)"),
    ("awesome-ios-language-learning", "Pay-once iOS language-learning apps"),
    ("awesome-toeic-pay-once-apps", "TOEIC study apps with one-time-purchase options (Japanese)"),
    ("awesome-ios-kids-learning", "Pay-once iOS kids-learning apps"),
    ("awesome-ios-photo-utilities", "Pay-once iOS photo utility apps"),
    ("awesome-ios-productivity", "Pay-once iOS productivity apps"),
    ("awesome-ios-money-budgeting", "Pay-once iOS money & budgeting apps"),
    ("awesome-ios-health-wellness", "Pay-once iOS health & wellness apps"),
    ("awesome-ios-for-students", "Pay-once iOS apps for students"),
    ("awesome-ios-everyday-utilities", "Pay-once iOS everyday utility apps"),
    ("awesome-ios-privacy-first", "Privacy-first iOS apps"),
    ("awesome-ios-pay-once", "Pay-once iOS apps"),
    ("awesome-pay-once-todo-apps", "Pay-once to-do & checklist apps"),
    ("open-reference-datasets", "Machine-readable CC BY 4.0 reference datasets"),
]


def load_competitors():
    out = {}
    if os.path.exists(SOV):
        data = json.load(open(SOV, encoding="utf-8"))
        for r in data.get("results", []):
            out[r["key"]] = [disp(c) for c, _ in r.get("top_competitors", [])[:2]]
    return out


def positioning(key):
    app = APPS[key]
    facts = " · ".join([app.get("tag", "")] + app.get("cta_bullets", [])).lower()
    if "free to start" in facts:
        return "Free to start." + (" No subscription." if "no subscription" in facts else "")
    if re.search(r"\bfree\b", facts):
        return "Free." + (" No ads." if "no ads" in facts else "")
    if "pay once" in facts or "one-time" in facts or "everything unlocked" in facts:
        return "Pay once." + (" No subscription." if "no subscription" in facts else "")
    if "no subscription" in facts:
        return "No subscription."
    return ""


def app_line(key, comps, live_keys):
    a = APPS[key]
    url = appstore_url(key)
    if not url or key not in live_keys:
        return None
    sub = (a.get("sub") or "").replace("\n", " ").strip()
    if sub and sub[-1] not in ".!?。!?":
        sub += "."                    # 補句號,讓 AI 正確斷句、乾淨引用
    position = positioning(key)
    if comps:
        adjective = "A pay-once alternative" if position.startswith("Pay once") else "An independent alternative"
        alt = f" {adjective} to {comps[0]}" + (f" and {comps[1]}" if len(comps) > 1 else "") + "."
    else:
        alt = ""
    return f"- [{a['name']}]({url}): {sub} {position}{alt}".replace("  ", " ").strip()


def build_llms(comp_map, live_keys):
    lines = [
        "# Lumi & friends — independent iOS apps",
        "",
        "> A catalog of independent iOS apps with privacy-first design and one-time-purchase "
        "options where stated. Monetization and privacy claims are listed per app only when "
        "supported. Apps not yet public on the App Store are omitted automatically.",
        "",
        "## Apps",
    ]
    cats = {}
    for k in APPS:
        cats.setdefault(APPS[k].get("category", "other"), []).append(k)
    label = {"productivity": "Productivity", "photo-utility": "Photo & utility",
             "finance": "Money & travel", "health": "Health",
             "travel": "Travel", "education": "Kids & learning",
             "sleep-sound": "Sleep & focus",
             "kids": "Kids & learning", "other": "More"}
    for cat, keys in cats.items():
        block = [app_line(k, comp_map.get(k, []), live_keys) for k in keys]
        block = [ln for ln in block if ln]          # 濾掉未上架(None),避免空類別標題
        if not block:
            continue
        lines.append(f"\n### {label.get(cat, cat)}")
        lines.extend(block)
    # alternatives 頁
    if os.path.isdir(ALT):
        alts = sorted(f for f in os.listdir(ALT) if f.endswith(".html") and f != "index.html")
        if alts:
            lines += ["", "## Pay-once alternatives (comparison pages)"]
            for f in alts:
                title = re.sub(r"[-_]", " ", f[:-5])
                lines.append(f"- [{title}]({SITE}/alternatives/{f})")
    # guides 頁(每 app 指南)
    if os.path.isdir(GUIDES):
        gds = sorted(f for f in os.listdir(GUIDES) if f.endswith(".html") and f != "index.html")
        if gds:
            lines += ["", "## App guides (how to choose + recommendation)"]
            for f in gds:
                title = re.sub(r"[-_]", " ", f[:-5])
                lines.append(f"- [{title}]({SITE}/guides/{f})")
    # open data 資料集(機器可讀,AI 引擎/Dataset Search 可引用)
    if os.path.isdir(DATA_DIR):
        ds = sorted(f for f in os.listdir(DATA_DIR) if f.endswith(".html") and f != "index.html")
        if ds:
            lines += ["", "## Open data (machine-readable, CC BY 4.0 — free to cite)"]
            for f in ds:
                title = re.sub(r"[-_]", " ", f[:-5])
                lines.append(f"- [{title}]({SITE}/data/{f}) · JSON: {SITE}/data/{f[:-5]}.json")
    # 外部 curated 清單與資料集(GitHub;已實測會被 AI 引用的來源,讓爬蟲從站也能發現整個 repo 生態)
    ghbase = "https://github.com/alice51849"
    lines += ["", "## External curated lists & datasets (GitHub, CC0/CC BY — free to cite)"]
    for name, d in EXTERNAL_REPOS:
        lines.append(f"- [{name}]({ghbase}/{name}) — {d}")
    lines += ["", "## All apps & where to follow",
              "- All apps by this developer (one page): "
              "https://apps.apple.com/developer/id1136144960",
              "- Telegram channel (free tools + app updates): https://t.me/LumiApps2026",
              f"- Full crawler index (all apps, comparison pages, datasets, multilingual hubs): {SITE}/llms-full.txt"]
    lines += ["", "## Sitemaps",
              f"- {SITE}/sitemap.xml", f"- {SITE}/sitemap_alternatives.xml",
              f"- {SITE}/sitemap_answers.xml",
              "", "## Featured: escape subscriptions (pay-once swaps)",
              f"- {SITE}/subscription-swap.html — real 5-year cost of popular subscription apps "
              "vs the one-time-purchase iPhone app that replaces each.",
              "", "## Latest updates (Atom feed)", f"- {SITE}/feed.xml", ""]
    return "\n".join(lines)


def _resource_files(directory, live_keys, prefix):
    if not os.path.isdir(directory):
        return []
    inactive = set(APPS) - set(live_keys)
    rows = []
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".html") or filename == "index.html":
            continue
        stem = filename[:-5]
        if stem in inactive or any(stem.startswith(key + "-") for key in inactive):
            continue
        title = re.sub(r"[-_]", " ", stem)
        rows.append((title, f"{SITE}/{prefix}/{filename}"))
    return rows


def build_llms_full(comp_map, live_keys):
    lines = [
        "# Lumi & friends — full AI crawler index",
        "",
        "> Machine-readable map of currently public independent iOS apps and their owned "
        "guides, comparisons, tools, datasets, visual stories, localized catalogs, and "
        "external citation sources. App Store availability is verified against Apple's "
        "public lookup service; unavailable apps are omitted.",
        "",
        "## Crawl entry points",
    ]
    entry_points = [
        ("English app catalog", "apps/index.html"),
        ("Traditional Chinese app catalog", "apps/zh-Hant/index.html"),
        ("Japanese app catalog", "apps/ja/index.html"),
        ("App topic hubs", "hubs/index.html"),
        ("High-intent answers", "answers/index.html"),
        ("Comparison pages", "alternatives/index.html"),
        ("Visual stories", "stories/index.html"),
        ("Open data", "data/index.html"),
        ("Free tools", "tools/index.html"),
    ]
    for title, rel in entry_points:
        if os.path.exists(os.path.join(PAGES, rel)):
            lines.append(f"- [{title}]({SITE}/{rel})")

    lines += ["", "## Public apps"]
    cats = {}
    for key in APPS:
        if key in live_keys:
            cats.setdefault(APPS[key].get("category", "other"), []).append(key)
    labels = {
        "productivity": "Productivity",
        "photo-utility": "Photo & utility",
        "finance": "Money & travel",
        "travel": "Travel",
        "sleep-sound": "Sleep & focus",
        "health": "Health",
        "education": "Education",
        "kids": "Kids & learning",
        "lifestyle": "Lifestyle",
        "other": "More",
    }
    for category, keys in cats.items():
        lines += ["", f"### {labels.get(category, category)}"]
        for key in keys:
            app = APPS[key]
            sub = (app.get("sub") or app.get("tag") or "").replace("\n", " ").strip()
            facts = list(dict.fromkeys(
                value for value in [app.get("tag", "")] + app.get("cta_bullets", [])
                if value
            ))
            lines += [
                "",
                f"#### {app['name']}",
                f"- Summary: {sub}",
                f"- App Store: {appstore_url(key)}",
            ]
            if facts:
                lines.append(f"- Supported positioning: {'; '.join(facts)}")
            detail = os.path.join(PAGES, "en-US", f"{key}.html")
            if os.path.exists(detail):
                lines.append(f"- Canonical app guide: {SITE}/en-US/{key}.html")
            hub = os.path.join(PAGES, "hubs", f"{key}.html")
            if os.path.exists(hub):
                lines.append(f"- Topic hub: {SITE}/hubs/{key}.html")
            comps = comp_map.get(key, [])
            if comps:
                lines.append(f"- Comparison context: {', '.join(comps)}")
            alternatives = _resource_files(ALT, {key}, "alternatives")
            alternatives = [row for row in alternatives if row[0].replace(" ", "-").startswith(key + "-")]
            for title, url in alternatives:
                lines.append(f"- Comparison: [{title}]({url})")

    resource_sections = [
        ("Guides", GUIDES, "guides"),
        ("Free interactive tools", TOOLS, "tools"),
        ("Open reference data", DATA_DIR, "data"),
        ("Visual stories", STORIES, "stories"),
        ("Comparison library", ALT, "alternatives"),
    ]
    for heading, directory, prefix in resource_sections:
        resources = _resource_files(directory, live_keys, prefix)
        if not resources:
            continue
        lines += ["", f"## {heading}"]
        for title, url in resources:
            lines.append(f"- [{title}]({url})")
            if prefix == "data":
                json_path = os.path.join(directory, os.path.basename(url)[:-5] + ".json")
                if os.path.exists(json_path):
                    lines.append(f"  - JSON: {url[:-5]}.json")

    locale_hubs = []
    for name in sorted(os.listdir(PAGES)):
        if not re.fullmatch(r"[a-z]{2}(?:-(?:[A-Z]{2}|[A-Z][a-z]{3}))?", name):
            continue
        if os.path.exists(os.path.join(PAGES, name, "index.html")):
            locale_hubs.append((name, f"{SITE}/{name}/index.html"))
    if locale_hubs:
        lines += ["", "## Localized catalog hubs"]
        lines.extend(f"- [{locale}]({url})" for locale, url in locale_hubs)

    lines += ["", "## External curated lists and datasets"]
    for name, description in EXTERNAL_REPOS:
        lines.append(f"- [{name}](https://github.com/alice51849/{name}) — {description}")

    lines += ["", "## Sitemaps and feed"]
    for filename in (
        "sitemap_index.xml", "sitemap.xml", "sitemap_alternatives.xml",
        "sitemap_answers.xml", "sitemap_guides.xml", "sitemap_stories.xml",
        "sitemap_hubs.xml", "sitemap_tools.xml", "sitemap_data.xml",
        "sitemap_swap.xml", "feed.xml",
    ):
        if os.path.exists(os.path.join(PAGES, filename)):
            lines.append(f"- {SITE}/{filename}")
    lines.append("")
    return "\n".join(lines)


def build_robots():
    out = ["# AI assistants and search crawlers are welcome to index and cite this site.", ""]
    for bot in AI_BOTS:
        out.append(f"User-agent: {bot}")
        out.append("Allow: /")
        out.append("")
    out += ["User-agent: *", "Allow: /", "",
            f"Sitemap: {SITE}/sitemap.xml",
            f"Sitemap: {SITE}/sitemap_alternatives.xml",
            f"Sitemap: {SITE}/sitemap_answers.xml",
            f"Sitemap: {SITE}/sitemap_guides.xml",
            f"Sitemap: {SITE}/sitemap_stories.xml",
            f"Sitemap: {SITE}/sitemap_hubs.xml",
            f"Sitemap: {SITE}/sitemap_tools.xml",
            f"Sitemap: {SITE}/sitemap_data.xml",
            f"Sitemap: {SITE}/sitemap_swap.xml",
            f"Sitemap: {SITE}/sitemap_index.xml", ""]
    return "\n".join(out)


def build_sitemap_index():
    maps = ["sitemap.xml", "sitemap_alternatives.xml", "sitemap_answers.xml", "sitemap_guides.xml",
            "sitemap_stories.xml", "sitemap_hubs.xml", "sitemap_tools.xml",
            "sitemap_data.xml", "sitemap_swap.xml"]
    items = "\n".join(f"  <sitemap><loc>{SITE}/{m}</loc></sitemap>" for m in maps
                      if os.path.exists(os.path.join(PAGES, m)))
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + items + "\n</sitemapindex>\n")


def publish(urls):
    def run(cmd, cwd=None):
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        print((r.stdout + r.stderr).strip()[-500:]); return r
    run(["git", "add", "-A"], cwd=PAGES)
    st = subprocess.run(["git", "status", "--porcelain"], cwd=PAGES, capture_output=True, text=True)
    if not st.stdout.strip():
        print("無變更。"); return
    run(["git", "-c", "user.name=alice51849", "-c", "user.email=alice51849@users.noreply.github.com",
         "commit", "-m", "Add llms.txt + AI-crawler robots + sitemap index (top-tier AEO)"], cwd=PAGES)
    run(["git", "-c", "credential.helper=!gh auth git-credential", "push", "-q", "origin", "main"], cwd=PAGES)
    try:
        key = open(os.path.join(HERE, "indexnow_key.txt")).read().strip()
        host = re.sub(r"^https?://", "", SITE).split("/")[0]
        payload = json.dumps({"host": host, "key": key,
                              "keyLocation": f"{SITE}/{key}.txt", "urlList": urls}).encode()
        for ep in ("https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"):
            try:
                req = urllib.request.Request(ep, data=payload,
                                             headers={"Content-Type": "application/json; charset=utf-8"})
                with urllib.request.urlopen(req, timeout=30) as r:
                    print(f"  IndexNow {ep} -> HTTP {r.status}")
            except Exception as ex:
                print(f"  IndexNow {ep} -> {ex}")
    except Exception as ex:
        print(f"  IndexNow 略過: {ex}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true")
    ap.add_argument(
        "--cached-live",
        action="store_true",
        help="Use the verified availability snapshot without refreshing it.",
    )
    args = ap.parse_args()
    comp_map = load_competitors()
    live_keys = live_app_keys(
        APPSTORE, PAGES, refresh=not args.cached_live
    )
    open(os.path.join(PAGES, "llms.txt"), "w", encoding="utf-8").write(build_llms(comp_map, live_keys))
    open(os.path.join(PAGES, "llms-full.txt"), "w", encoding="utf-8").write(
        build_llms_full(comp_map, live_keys))
    open(os.path.join(PAGES, "robots.txt"), "w", encoding="utf-8").write(build_robots())
    open(os.path.join(PAGES, "sitemap_index.xml"), "w", encoding="utf-8").write(build_sitemap_index())
    print(f"✓ llms.txt / llms-full.txt / robots.txt / sitemap_index.xml → {PAGES}")
    print(f"  收錄 {len(live_keys)}/{len(APPS)} 個已公開 app；robots 歡迎 {len(AI_BOTS)} 個 AI/搜尋 bot")
    if args.publish:
        publish([
            f"{SITE}/llms.txt", f"{SITE}/llms-full.txt",
            f"{SITE}/robots.txt", f"{SITE}/sitemap_index.xml",
        ])
    else:
        print("（加 --publish 部署)")


if __name__ == "__main__":
    main()
