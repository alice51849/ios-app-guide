#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Generate a lightweight localized tools/index.html hub for locales that lack one.
Scans <locale>/tools/*.html, extracts each page's <title> and meta description,
and renders a card grid re-using the English index's stylesheet. Idempotent; rerun
after adding tools. Usage: python gen_tools_index_lite.py vi th id tr"""
import html
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(HERE, "pages")
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide")

UI = {
    "vi": ("Công cụ web tương tác miễn phí", "Các công cụ riêng tư chạy ngay trong trình duyệt — không tài khoản, không tải lên.", "Công cụ miễn phí", "Mở công cụ →"),
    "th": ("เครื่องมือเว็บอินเทอร์แอ็กทีฟฟรี", "เครื่องมือส่วนตัวที่ทำงานในเบราว์เซอร์ — ไม่มีบัญชี ไม่อัปโหลด", "เครื่องมือฟรี", "เปิดเครื่องมือ →"),
    "id": ("Alat Web Interaktif Gratis", "Alat privat yang berjalan langsung di peramban — tanpa akun, tanpa unggahan.", "Alat gratis", "Buka alat →"),
    "tr": ("Ücretsiz Etkileşimli Web Araçları", "Doğrudan tarayıcıda çalışan gizli araçlar — hesap yok, yükleme yok.", "Ücretsiz araçlar", "Aracı aç →"),
}


def extract(path):
    src = open(path, encoding="utf-8").read()
    t = re.search(r"<title>(.*?)</title>", src, re.S)
    d = re.search(r'<meta name="description" content="([^"]*)"', src)
    title = html.unescape(t.group(1)).split("|")[0].strip() if t else os.path.basename(path)
    desc = html.unescape(d.group(1)).strip() if d else ""
    return title, desc


def build(locale):
    tdir = os.path.join(PAGES, locale, "tools")
    if not os.path.isdir(tdir):
        return 0
    en_index = open(os.path.join(PAGES, "tools", "index.html"), encoding="utf-8").read()
    style = re.search(r"<style.*?</style>", en_index, re.S).group(0)
    page_title, lead, nav_label, open_label = UI[locale]
    cards = []
    for name in sorted(os.listdir(tdir)):
        if not name.endswith(".html") or name == "index.html":
            continue
        title, desc = extract(os.path.join(tdir, name))
        cards.append(
            f'<article class="card"><h2><a href="{html.escape(name)}">{html.escape(title)}</a></h2>'
            f"<p>{html.escape(desc)}</p>"
            f'<p><a href="{html.escape(name)}">{html.escape(open_label)}</a></p></article>'
        )
    if not cards:
        return 0
    canon = f"{SITE}/{locale}/tools/index.html"
    doc = (
        f'<!DOCTYPE html><html lang="{locale}"><head><meta charset="utf-8">'
        f'<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{html.escape(page_title)}</title>"
        f'<meta name="description" content="{html.escape(lead)}">'
        f'<link rel="canonical" href="{canon}">'
        f'<link rel="alternate" hreflang="en" href="{SITE}/tools/index.html">'
        f'<link rel="alternate" hreflang="{locale}" href="{canon}">'
        f"{style}</head><body>"
        f'<header class="top"><div class="wrap nav"><a href="{SITE}/{locale}/index.html">iOS App Guide</a>'
        f'<nav><a href="{canon}">{html.escape(nav_label)}</a></nav></div></header>'
        f'<main class="wrap"><h1>{html.escape(page_title)}</h1><p>{html.escape(lead)}</p>'
        f'<div class="grid">{"".join(cards)}</div></main>'
        f'<footer class="footer"><div class="wrap">Lumi Studio · <a href="{SITE}/tools/index.html">English</a></div></footer>'
        f"</body></html>"
    )
    open(os.path.join(tdir, "index.html"), "w", encoding="utf-8").write(doc)
    return len(cards)


def main():
    locales = sys.argv[1:] or list(UI)
    for locale in locales:
        if locale not in UI:
            print(f"skip {locale}: no UI strings")
            continue
        n = build(locale)
        print(f"{locale}: {n} tool cards -> {locale}/tools/index.html")


if __name__ == "__main__":
    main()
