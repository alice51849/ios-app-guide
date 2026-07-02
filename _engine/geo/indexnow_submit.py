#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IndexNow 提交器 — 把 GEO 頁 URL 主動推送給 Bing/Yandex(=ChatGPT/Copilot 的索引來源)。

讀 geo/pages/sitemap.xml 的所有 URL,分批 POST 到 IndexNow API。
key 檔需先部署在 SITE 根可存取(geo/pages/<key>.txt)。

    python geo/indexnow_submit.py            # 提交全部
    python geo/indexnow_submit.py --limit 50 # 只提交前 50(測試)
"""
import os
import re
import sys
import json
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(HERE, "pages")
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide").rstrip("/")
HOST = re.sub(r"^https?://", "", SITE).split("/")[0]

ENDPOINTS = [
    "https://api.indexnow.org/indexnow",
    "https://www.bing.com/indexnow",
]


def read_key():
    kf = os.path.join(HERE, "indexnow_key.txt")
    with open(kf) as f:
        return f.read().strip()


def read_urls():
    """Collect URLs from every sub-sitemap listed in sitemap_index.xml.

    Falls back to sitemap.xml alone if the index is missing. This ensures
    answer/alternatives/guide pages (not just landing pages) get pinged.
    """
    urls, seen = [], set()
    idx = os.path.join(PAGES, "sitemap_index.xml")
    sitemaps = []
    if os.path.exists(idx):
        with open(idx, encoding="utf-8") as f:
            for loc in re.findall(r"<loc>([^<]+)</loc>", f.read()):
                name = loc.rstrip("/").split("/")[-1]
                if name.endswith(".xml"):
                    sitemaps.append(os.path.join(PAGES, name))
    if not sitemaps:
        sitemaps = [os.path.join(PAGES, "sitemap.xml")]
    for sm in sitemaps:
        if not os.path.exists(sm):
            continue
        with open(sm, encoding="utf-8") as f:
            for u in re.findall(r"<loc>([^<]+)</loc>", f.read()):
                if u not in seen:
                    seen.add(u)
                    urls.append(u)
    return urls


def submit(urls, key):
    payload = {
        "host": HOST,
        "key": key,
        "keyLocation": f"{SITE}/{key}.txt",
        "urlList": urls,
    }
    data = json.dumps(payload).encode()
    ok = False
    for ep in ENDPOINTS:
        try:
            req = urllib.request.Request(
                ep, data=data,
                headers={"Content-Type": "application/json; charset=utf-8"})
            with urllib.request.urlopen(req, timeout=30) as r:
                print(f"  {ep} -> HTTP {r.status}")
                if r.status in (200, 202):
                    ok = True
        except urllib.error.HTTPError as e:
            print(f"  {ep} -> HTTP {e.code} {e.reason}")
        except Exception as e:
            print(f"  {ep} -> ERR {e}")
    return ok


if __name__ == "__main__":
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])
    key = read_key()
    urls = read_urls()
    if limit:
        urls = urls[:limit]
    print(f"host={HOST}  key={key[:8]}…  urls={len(urls)}")
    # IndexNow 單次上限 10000
    BATCH = 10000
    okc = 0
    for i in range(0, len(urls), BATCH):
        chunk = urls[i:i + BATCH]
        print(f"batch {i // BATCH + 1}: {len(chunk)} urls")
        if submit(chunk, key):
            okc += len(chunk)
    print(f"\n✅ 已提交 {okc}/{len(urls)} URLs 給 IndexNow(Bing/Yandex)")
