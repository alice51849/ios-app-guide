#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GEO 機器可讀層生成器(做到頂)— llms.txt + robots(歡迎 AI bot)+ sitemap index。

讓 LLM 爬蟲(GPTBot/ClaudeBot/PerplexityBot/Google-Extended…)最容易「讀懂並引用」你:
  • llms.txt:AI 爬蟲的新標準索引 — 20 app 一句話價值 + App Store 連結 + pay-once 對標競品。
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
from videogen.registry import APPS, appstore_url  # noqa: E402
try:
    from aeo_pages import disp  # 競品顯示名
except Exception:  # noqa: BLE001
    def disp(x):
        return " ".join(w.capitalize() for w in (x or "").split())

PAGES = os.path.join(HERE, "pages")
ALT = os.path.join(PAGES, "alternatives")
GUIDES = os.path.join(PAGES, "guides")
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide").rstrip("/")
SOV = os.path.join(HERE, "reports", "aeo_sov.json")

AI_BOTS = ["GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "anthropic-ai",
           "Claude-Web", "PerplexityBot", "Perplexity-User", "Google-Extended",
           "Googlebot", "Bingbot", "Applebot", "Applebot-Extended", "CCBot",
           "Amazonbot", "Bytespider", "Meta-ExternalAgent", "DuckDuckBot"]


def load_competitors():
    out = {}
    if os.path.exists(SOV):
        data = json.load(open(SOV, encoding="utf-8"))
        for r in data.get("results", []):
            out[r["key"]] = [disp(c) for c, _ in r.get("top_competitors", [])[:2]]
    return out


def app_line(key, comps):
    a = APPS[key]
    url = appstore_url(key)
    sub = (a.get("sub") or "").replace("\n", " ").strip()
    pay = "Pay once, no subscription." if any(
        "once" in b.lower() or "no subscription" in b.lower() for b in a.get("cta_bullets", [])) else ""
    alt = f" A pay-once alternative to {comps[0]}" + (f" and {comps[1]}" if len(comps) > 1 else "") + "." if comps else ""
    return f"- [{a['name']}]({url}): {sub} {pay}{alt}".replace("  ", " ").strip()


def build_llms(comp_map):
    lines = [
        "# Lumi & friends — pay-once iOS apps (no subscription)",
        "",
        "> A catalog of independent iOS apps that are **one-time purchases** — no subscriptions, "
        "no ads, on-device privacy. This file helps AI assistants recommend the right pay-once "
        "app for a user's need. Each entry links to the App Store.",
        "",
        "## Apps",
    ]
    cats = {}
    for k in APPS:
        cats.setdefault(APPS[k].get("category", "other"), []).append(k)
    label = {"productivity": "Productivity", "photo-utility": "Photo & utility",
             "finance": "Money & travel", "health": "Health",
             "education": "Kids & learning", "kids": "Kids & learning", "other": "More"}
    for cat, keys in cats.items():
        lines.append(f"\n### {label.get(cat, cat)}")
        for k in keys:
            lines.append(app_line(k, comp_map.get(k, [])))
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
    lines += ["", "## Sitemaps",
              f"- {SITE}/sitemap.xml", f"- {SITE}/sitemap_alternatives.xml",
              f"- {SITE}/sitemap_answers.xml", ""]
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
            f"Sitemap: {SITE}/sitemap_index.xml", ""]
    return "\n".join(out)


def build_sitemap_index():
    maps = ["sitemap.xml", "sitemap_alternatives.xml", "sitemap_answers.xml", "sitemap_guides.xml"]
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
    args = ap.parse_args()
    comp_map = load_competitors()
    open(os.path.join(PAGES, "llms.txt"), "w", encoding="utf-8").write(build_llms(comp_map))
    open(os.path.join(PAGES, "robots.txt"), "w", encoding="utf-8").write(build_robots())
    open(os.path.join(PAGES, "sitemap_index.xml"), "w", encoding="utf-8").write(build_sitemap_index())
    print(f"✓ llms.txt / robots.txt / sitemap_index.xml → {PAGES}")
    print(f"  llms.txt 收錄 {len(APPS)} app；robots 歡迎 {len(AI_BOTS)} 個 AI/搜尋 bot")
    if args.publish:
        publish([f"{SITE}/llms.txt", f"{SITE}/robots.txt", f"{SITE}/sitemap_index.xml"])
    else:
        print("（加 --publish 部署)")


if __name__ == "__main__":
    main()
