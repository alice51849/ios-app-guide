#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AEO 購買意圖落地頁生成器 — 把 aeo_sov.py 的「攻擊清單」變成會被 Google/AI 引用的頁。

策略(打購買當下、非散播):
  aeo_sov.py 量到「有人問 AI 要用哪個 app」時,AI 都推哪些競品、你在哪些問句缺席。
  這支就針對那些競品 + 缺口問句,自動產「pay-once / no-subscription 替代方案」比較頁:
    • <app>-vs-<competitor>.html  → 鎖定「[競品] alternative」這種最高購買意圖的搜尋/AI 問句
    • <app>-no-subscription.html  → 鎖定「免訂閱的 X app」hub 頁
  每頁含 SoftwareApplication + FAQPage JSON-LD(LLM/Google 最愛的結構化來源)+ 誠實比較表
  (只主張「你的 app」可驗證屬性:一次付費/離線/無廣告/無浮水印;競品欄用「typical apps」中性敘述)。

  誠信原則:不對具名競品做不實宣稱;競品僅作為使用者搜尋的參照點(nominative use)。

用法:
  python geo/aeo_pages.py                 # 依 reports/aeo_sov.json 產頁(不部署)
  python geo/aeo_pages.py --publish       # 並 git push + IndexNow 推送
  python geo/aeo_pages.py scanto cvdesk   # 只產指定 app
  python geo/aeo_pages.py --top 4         # 每 app 取前 N 個競品(預設 4)
"""
import argparse
import html
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "social"))
from videogen.registry import APPS, appstore_url  # noqa: E402

PAGES = os.path.join(HERE, "pages")
ALT = os.path.join(PAGES, "alternatives")
REPORTS = os.path.join(HERE, "reports")
SOV = os.path.join(REPORTS, "aeo_sov.json")
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide").rstrip("/")

# 有訂閱制(非純買斷)的 app —— 不可套用「pay-once / 免訂閱」比較頁,否則不實宣稱。
NO_SUB_EXCLUDE = {"aim990"}

# 類別 → 給人看的名詞 + schema 類別
CAT_NOUN = {
    "photo-utility": ("photo app", "PhotoApplication"),
    "productivity": ("productivity app", "BusinessApplication"),
    "finance": ("finance app", "FinanceApplication"),
    "health": ("health app", "HealthApplication"),
    "education": ("English test-prep app", "EducationalApplication"),
    "kids": ("kids learning app", "EducationalApplication"),
    "lifestyle": ("astrology app", "LifestyleApplication"),
}

# 常見競品正規化名 → 正式顯示名(其餘自動 Title Case)
BRAND = {
    "camscanner pdf scanner app": "CamScanner", "adobe scan pdf scanner ocr": "Adobe Scan",
    "scanbot pdf document scanner": "Scanbot", "genius scan": "Genius Scan",
    "microsoft lens": "Microsoft Lens", "tiny scanner": "Tiny Scanner",
    "visualcv resume builder": "VisualCV", "zety resume builder": "Zety",
    "resume builder cv maker": "Resume Builder", "canva": "Canva", "indeed": "Indeed",
    "snapseed": "Snapseed", "fotor photo editor": "Fotor", "remini ai photo enhancer": "Remini",
    "remini": "Remini", "lightroom": "Lightroom", "vsco": "VSCO", "picsart": "PicsArt",
    "flo period ovulation tracker": "Flo", "ovia fertility cycle tracker": "Ovia",
    "my calendar period tracker": "My Calendar", "clue period cycle tracker": "Clue",
    "flo": "Flo", "clue": "Clue", "natural cycles": "Natural Cycles",
    # 從 20-app 全掃補進的常見競品
    "microsoft office lens": "Microsoft Office Lens", "microsoft onenote": "Microsoft OneNote",
    "otter transcribe voice notes": "Otter", "google keep": "Google Keep",
    "passport photo maker": "Passport Photo Maker", "passport photo booth": "Passport Photo Booth",
    "id photo passport photo": "ID Photo", "resume star pro cv maker": "Resume Star Pro",
    "gemini photos gallery cleaner": "Gemini Photos", "duplicate photos fixer": "Duplicate Photos Fixer",
    "smart cleaner clean storage": "Smart Cleaner", "ynab you need a budget": "YNAB",
    "currency converter plus": "Currency Converter Plus", "spendee budget expense tracker": "Spendee",
    "everydollar budgeting app": "EveryDollar", "forest stay focused": "Forest",
    "focus will": "Focus@Will", "stay focused app blocker": "Stay Focused",
    "adobe lightroom": "Adobe Lightroom", "endless alphabet": "Endless Alphabet",
    "abcmouse com": "ABCmouse", "starfall abcs": "Starfall", "reading eggs": "Reading Eggs",
    "endless numbers": "Endless Numbers", "todo math": "Todo Math",
    "math kids add subtract count and learn": "Math Kids", "prodigy math game": "Prodigy",
    "ourhome": "OurHome", "choremonster": "ChoreMonster", "cozi family organizer": "Cozi",
    "the weather channel": "The Weather Channel", "weather wiz kids": "Weather Wiz Kids",
    "kid weather": "Kid Weather", "hellochinese": "HelloChinese",
    "hellochinese learn chinese": "HelloChinese", "chineseskill": "ChineseSkill",
    "chineseskill learn chinese": "ChineseSkill", "fun chinese by studycat": "Fun Chinese by Studycat",
}

ATTRS = [  # (顯示, cta_bullets 命中關鍵詞)
    ("Pay once (no subscription)", ("pay once", "no subscription")),
    ("Works offline / on-device", ("on-device", "offline", "on device")),
    ("No ads", ("no ads",)),
    ("No watermark", ("no watermark",)),
    ("Private (no account)", ("private", "no account", "no tracking")),
]


def e(s):
    return html.escape(str(s or ""))


def disp(norm):
    if norm in BRAND:
        return BRAND[norm]
    return " ".join(w.capitalize() for w in norm.split())


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:70] or "x"


def app_attrs(key):
    b = [x.lower() for x in APPS[key].get("cta_bullets", [])]
    out = {}
    for label, keys in ATTRS:
        out[label] = any(any(k in bb for bb in b) for k in keys)
    return out


def cat_noun(key):
    return CAT_NOUN.get(APPS[key].get("category", "productivity"), ("app", "MobileApplication"))


def landing_url(key):
    """Use the live App Store URL when known; otherwise link to the generated web page."""
    return appstore_url(key) or f"{SITE}/alternatives/{key}-no-subscription.html"


def page_shell(title, desc, canonical, schemas, body):
    ld = "\n".join(
        f'<script type="application/ld+json">\n{json.dumps(s, ensure_ascii=False, indent=2)}\n</script>'
        for s in schemas)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title[:65])}</title>
<meta name="description" content="{e(desc[:155])}">
<link rel="canonical" href="{canonical}">
{ld}
</head>
<body>
<main>
{body}
<hr>
<p><small>Independent comparison. App names are trademarks of their owners and are used
for identification only.</small></p>
</main>
</body>
</html>
"""


def comparison_table(key, comp_name):
    a = APPS[key]
    attrs = app_attrs(key)
    rows = []
    for label, _ in ATTRS:
        yours = "✅ Yes" if attrs[label] else "—"
        # 競品欄:中性、可辯護(對「typical apps」而非具名不實宣稱)
        typical = "Often subscription" if "Pay once" in label else "Varies"
        rows.append(f"    <tr><td>{e(label)}</td><td><strong>{yours}</strong></td>"
                    f"<td>{e(typical)}</td></tr>")
    return (f'  <table>\n    <thead><tr><th>Feature</th><th>{e(a["name"])}</th>'
            f'<th>Typical {e(comp_name)}-style apps</th></tr></thead>\n    <tbody>\n'
            + "\n".join(rows) + "\n    </tbody>\n  </table>")


def faq_for(key, comp_name, gap_queries):
    a = APPS[key]
    noun, _ = cat_noun(key)
    url = landing_url(key)
    qa = [
        (f"What is a good pay-once alternative to {comp_name} on iPhone?",
         f"{a['name']} is a one-time-purchase {noun} for iPhone — {a.get('sub','').replace(chr(10),' ')}. "
         f"You unlock everything with a single payment, with no recurring subscription."),
        (f"Is there a {noun} with no subscription?",
         f"Yes. {a['name']} is a pay-once {noun}: buy it once and keep it. "
         f"Get it on the App Store: {url}"),
    ]
    if app_attrs(key).get("Works offline / on-device"):
        qa.append((f"Does {a['name']} work offline / on device?",
                   f"Yes, {a['name']} runs on your iPhone and processes your data on-device for privacy."))
    for q in (gap_queries or [])[:3]:
        qa.append((q[0].upper() + q[1:] + ("" if q.endswith("?") else "?"),
                   f"{a['name']} is a strong pay-once option. Learn more on the App Store: {url}"))
    # 去重
    seen, out = set(), []
    for q, ans in qa:
        if q.lower() in seen:
            continue
        seen.add(q.lower()); out.append((q, ans))
    return out


def app_schema(key, desc):
    a = APPS[key]
    _, scat = cat_noun(key)
    url = landing_url(key)
    return {"@context": "https://schema.org", "@type": "SoftwareApplication",
            "name": a["name"], "operatingSystem": "iOS", "applicationCategory": scat,
            "url": url, "installUrl": url, "description": desc,
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD",
                       "description": "Free to download; one-time in-app purchase to unlock everything. No subscription."},
            "featureList": [l for l, ok in app_attrs(key).items() if ok] or a.get("keywords", [])[:5]}


def faq_schema(faq):
    return {"@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": q,
                            "acceptedAnswer": {"@type": "Answer", "text": ans}} for q, ans in faq]}


def alt_page(key, comp_norm, gap_queries):
    a = APPS[key]
    comp = disp(comp_norm)
    noun, _ = cat_noun(key)
    url = landing_url(key)
    title = f"{comp} alternative for iPhone — {a['name']} (pay once, no subscription)"
    desc = (f"Looking for a {comp} alternative on iPhone? {a['name']} is a pay-once {noun} — "
            f"{a.get('sub','').splitlines()[0] if a.get('sub') else ''}")
    faq = faq_for(key, comp, gap_queries)
    schemas = [app_schema(key, desc), faq_schema(faq)]
    feat_li = "\n".join(f"    <li>{e(b)}</li>" for b in a.get("cta_bullets", [])) or "    <li>iOS app</li>"
    faq_html = "\n".join(
        f'    <div itemscope itemtype="https://schema.org/Question">\n'
        f'      <h3 itemprop="name">{e(q)}</h3>\n'
        f'      <div itemprop="acceptedAnswer" itemscope itemtype="https://schema.org/Answer">\n'
        f'        <p itemprop="text">{e(ans)}</p>\n      </div>\n    </div>'
        for q, ans in faq)
    body = f"""  <h1>{e(comp)} alternative for iPhone: {e(a['name'])}</h1>
  <p>{e(comp)} is a well-known {e(noun)}. If you'd rather <strong>pay once</strong> than
  subscribe, <strong>{e(a['name'])}</strong> is a one-time-purchase {e(noun)} for iPhone:
  {e((a.get('sub') or '').replace(chr(10),' '))}</p>
  <p><a href="{e(url)}"><strong>Get {e(a['name'])} on the App Store →</strong></a></p>

  <h2>Why people choose a pay-once {e(comp)} alternative</h2>
  <ul>
{feat_li}
  </ul>

  <h2>{e(a['name'])} vs typical {e(comp)}-style apps</h2>
{comparison_table(key, comp)}

  <h2>Frequently asked questions</h2>
{faq_html}

  <p><a href="{e(url)}"><strong>Try {e(a['name'])} — one-time purchase on the App Store →</strong></a></p>"""
    slug = f"{key}-vs-{slugify(comp)}"
    canonical = f"{SITE}/alternatives/{slug}.html"
    return slug, page_shell(title, desc, canonical, schemas, body)


def hub_page(key, gap_queries):
    a = APPS[key]
    noun, _ = cat_noun(key)
    url = landing_url(key)
    title = f"Best no-subscription {noun} for iPhone — {a['name']} (pay once)"
    desc = f"{a['name']} is a pay-once {noun} for iPhone. No subscription, no recurring fees."
    faq = faq_for(key, noun.split()[0], gap_queries)
    schemas = [app_schema(key, desc), faq_schema(faq)]
    feat_li = "\n".join(f"    <li>{e(b)}</li>" for b in a.get("cta_bullets", [])) or "    <li>iOS app</li>"
    faq_html = "\n".join(
        f'    <div itemscope itemtype="https://schema.org/Question">\n'
        f'      <h3 itemprop="name">{e(q)}</h3>\n'
        f'      <div itemprop="acceptedAnswer" itemscope itemtype="https://schema.org/Answer">\n'
        f'        <p itemprop="text">{e(ans)}</p>\n      </div>\n    </div>'
        for q, ans in faq)
    body = f"""  <h1>The pay-once {e(noun)} for iPhone: {e(a['name'])}</h1>
  <p><strong>{e(a['name'])}</strong> — {e((a.get('sub') or '').replace(chr(10),' '))}.
  Most {e(noun)}s charge a monthly subscription; {e(a['name'])} is a <strong>one-time
  purchase</strong>.</p>
  <p><a href="{e(url)}"><strong>Get {e(a['name'])} on the App Store →</strong></a></p>

  <h2>What you get (no subscription)</h2>
  <ul>
{feat_li}
  </ul>

  <h2>Frequently asked questions</h2>
{faq_html}

  <p><a href="{e(url)}"><strong>Download {e(a['name'])} — pay once →</strong></a></p>"""
    slug = f"{key}-no-subscription"
    canonical = f"{SITE}/alternatives/{slug}.html"
    return slug, page_shell(title, desc, canonical, schemas, body)


def build_index(files):
    items = []
    for f in sorted(files):
        m = re.search(r"<h1>([^<]+)</h1>", open(os.path.join(ALT, f), encoding="utf-8").read())
        items.append(f'    <li><a href="{f}">{e(m.group(1) if m else f)}</a></li>')
    idx = (f'<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">\n'
           f'<meta name="viewport" content="width=device-width, initial-scale=1">\n'
           f'<title>Pay-once iPhone app alternatives — no subscription</title>\n'
           f'<meta name="description" content="Pay-once, no-subscription iPhone app alternatives.">\n'
           f'<link rel="canonical" href="{SITE}/alternatives/index.html"></head><body><main>\n'
           f'  <h1>Pay-once iPhone apps (no subscription)</h1>\n  <ul>\n'
           + "\n".join(items) + "\n  </ul>\n</main></body></html>\n")
    open(os.path.join(ALT, "index.html"), "w", encoding="utf-8").write(idx)


def write_sitemap(files):
    urls = [f"  <url><loc>{SITE}/alternatives/index.html</loc></url>"]
    urls += [f"  <url><loc>{SITE}/alternatives/{f}</loc></url>" for f in sorted(files)]
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(urls) + "\n</urlset>\n")
    open(os.path.join(PAGES, "sitemap_alternatives.xml"), "w", encoding="utf-8").write(xml)


def publish(new_urls):
    def run(cmd, cwd=None):
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        print((r.stdout + r.stderr).strip()[-600:]); return r
    run(["git", "add", "-A"], cwd=PAGES)
    st = subprocess.run(["git", "status", "--porcelain"], cwd=PAGES, capture_output=True, text=True)
    if not st.stdout.strip():
        print("無變更,略過部署。"); return
    run(["git", "-c", "user.name=alice51849", "-c", "user.email=alice51849@users.noreply.github.com",
         "commit", "-m", "Add pay-once alternative landing pages (AEO)"], cwd=PAGES)
    run(["git", "-c", "credential.helper=!gh auth git-credential", "push", "-q", "origin", "main"], cwd=PAGES)
    try:
        key = open(os.path.join(HERE, "indexnow_key.txt")).read().strip()
        host = re.sub(r"^https?://", "", SITE).split("/")[0]
        payload = json.dumps({"host": host, "key": key,
                              "keyLocation": f"{SITE}/{key}.txt", "urlList": new_urls}).encode()
        for ep in ("https://api.indexnow.org/indexnow", "https://www.bing.com/indexnow"):
            req = urllib.request.Request(ep, data=payload,
                                         headers={"Content-Type": "application/json; charset=utf-8"})
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    print(f"  IndexNow {ep} -> HTTP {r.status}")
            except Exception as ex:
                print(f"  IndexNow {ep} -> {ex}")
    except Exception as ex:
        print(f"  IndexNow 略過: {ex}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("apps", nargs="*")
    ap.add_argument("--top", type=int, default=4, help="每 app 取前 N 個競品")
    ap.add_argument("--publish", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(SOV):
        print(f"找不到 {SOV},請先跑 python geo/aeo_sov.py", file=sys.stderr); sys.exit(1)
    data = json.load(open(SOV, encoding="utf-8"))
    by_key = {r["key"]: r for r in data["results"]}

    keys = [k for k in (args.apps or by_key.keys()) if k in by_key and k in APPS]
    # 這些頁的整體主張是「pay-once / 免訂閱替代方案」。有訂閱制的 app 不可套用
    # (否則產生不實宣稱),一律排除。
    keys = [k for k in keys if k not in NO_SUB_EXCLUDE]
    os.makedirs(ALT, exist_ok=True)
    written, urls = [], []
    for k in keys:
        r = by_key[k]
        gaps = r.get("gap_queries", [])
        comps = [c for c, _ in r.get("top_competitors", [])][:args.top]
        for c in comps:
            slug, html_doc = alt_page(k, c, gaps)
            open(os.path.join(ALT, f"{slug}.html"), "w", encoding="utf-8").write(html_doc)
            written.append(f"{slug}.html"); urls.append(f"{SITE}/alternatives/{slug}.html")
        slug, html_doc = hub_page(k, gaps)
        open(os.path.join(ALT, f"{slug}.html"), "w", encoding="utf-8").write(html_doc)
        written.append(f"{slug}.html"); urls.append(f"{SITE}/alternatives/{slug}.html")
        print(f"  ✓ {APPS[k]['name']}: {len(comps)} 競品頁 + 1 hub")

    all_files = [f for f in os.listdir(ALT) if f.endswith(".html") and f != "index.html"]
    build_index(all_files)
    write_sitemap(all_files)
    urls.append(f"{SITE}/alternatives/index.html")
    print(f"\n共產出 {len(written)} 頁 → {ALT}")
    print(f"index + sitemap_alternatives.xml 已更新")
    if args.publish:
        publish(urls)
    else:
        print("（加 --publish 可 git push + IndexNow 推送)")


if __name__ == "__main__":
    main()
