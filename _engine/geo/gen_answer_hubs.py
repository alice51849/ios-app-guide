#!/usr/bin/env python3
"""每語言「答案 hub」索引頁生成器(2026-07-07 新方法)。
為何:低競爭語言(ms/vi/th/id/tr…)的在地化答案頁已存在,但沒有語言專屬的索引入口,
AI 爬蟲與搜尋引擎難以整批發現。此工具為每個有答案頁的語言產生 <lang>/answers/index.html:
  - 在地化標題/描述(agent 自產,不用任何付費 API)
  - 列出該語言全部答案頁(內部連結 → 可爬性)
  - ItemList JSON-LD(讓 AI/搜尋理解這是一個問答集合)
  - hreflang(en + 該語言)+ canonical
產完自動刷新 answers sitemap。純本機、免 key。
用法:python3 gen_answer_hubs.py [--langs ms,vi,...]
"""
import os, re, sys, html, json, argparse
from pathlib import Path

HERE = Path(os.path.dirname(os.path.abspath(__file__)))
PAGES = HERE / "pages"
SITE = os.environ.get("GEO_SITE", "https://alice51849.github.io/ios-app-guide").rstrip("/")

# 各語言 hub 的在地化文案(agent 母語自產;繁中用台灣用語)。
L10N = {
    "ms": {"lang": "ms", "title": "Panduan Memilih Aplikasi iPhone — Jawapan Jujur",
           "desc": "Panduan jujur untuk memilih aplikasi iPhone: privasi, guna luar talian, dan bayar sekali tanpa langganan.",
           "h1": "Panduan memilih aplikasi iPhone", "all": "Semua panduan jawapan",
           "lead": "Panduan ringkas dan jujur untuk soalan sebenar sebelum anda memasang sesebuah aplikasi."},
    "vi": {"lang": "vi", "title": "Hướng dẫn chọn ứng dụng iPhone — Câu trả lời trung thực",
           "desc": "Hướng dẫn trung thực để chọn ứng dụng iPhone: riêng tư, dùng ngoại tuyến, trả một lần không thuê bao.",
           "h1": "Hướng dẫn chọn ứng dụng iPhone", "all": "Tất cả hướng dẫn trả lời",
           "lead": "Hướng dẫn ngắn gọn, trung thực cho những câu hỏi thực tế trước khi bạn cài đặt một ứng dụng."},
    "th": {"lang": "th", "title": "คู่มือเลือกแอป iPhone — คำตอบที่ตรงไปตรงมา",
           "desc": "คู่มือเลือกแอป iPhone อย่างซื่อสัตย์: ความเป็นส่วนตัว ใช้งานออฟไลน์ และจ่ายครั้งเดียวไม่มีค่าสมาชิก",
           "h1": "คู่มือเลือกแอป iPhone", "all": "คู่มือคำตอบทั้งหมด",
           "lead": "คู่มือสั้น ๆ ที่ซื่อสัตย์สำหรับคำถามจริงก่อนที่คุณจะติดตั้งแอป"},
    "id": {"lang": "id", "title": "Panduan Memilih Aplikasi iPhone — Jawaban Jujur",
           "desc": "Panduan jujur untuk memilih aplikasi iPhone: privasi, penggunaan offline, dan bayar sekali tanpa langganan.",
           "h1": "Panduan memilih aplikasi iPhone", "all": "Semua panduan jawaban",
           "lead": "Panduan singkat dan jujur untuk pertanyaan nyata sebelum Anda memasang sebuah aplikasi."},
    "tr": {"lang": "tr", "title": "iPhone Uygulaması Seçme Rehberleri — Dürüst Yanıtlar",
           "desc": "iPhone uygulaması seçmek için dürüst rehberler: gizlilik, çevrimdışı kullanım ve abonelik olmadan tek seferlik ödeme.",
           "h1": "iPhone uygulaması seçme rehberleri", "all": "Tüm yanıt rehberleri",
           "lead": "Bir uygulamayı yüklemeden önce gerçek sorular için kısa ve dürüst rehberler."},
}

CSS = ("body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;"
       "background:linear-gradient(180deg,#fff,#f7f7fb);color:#161622;line-height:1.6}a{color:#3840d0}"
       ".wrap{width:min(1040px,100% - 32px);margin:auto}.hero{padding:40px 0 10px}"
       ".eyebrow{color:#5b5ff2;font-weight:800;text-transform:uppercase;letter-spacing:.08em;font-size:.78rem}"
       "h1{font-size:clamp(1.8rem,5vw,3rem);line-height:1.06;margin:.2em 0}p.lead{font-size:1.12rem;color:#5d6370;max-width:780px}"
       "ul.list{list-style:none;padding:0;margin:18px 0 40px;columns:2;column-gap:26px}@media(max-width:640px){ul.list{columns:1}}"
       "ul.list li{break-inside:avoid;margin:.4em 0;padding:10px 12px;background:#fff;border:1px solid #e6e7ef;border-radius:12px}"
       ".footer{margin-top:24px;padding:24px 0;border-top:1px solid #e6e7ef;color:#5d6370;font-size:.92rem}")


def page_title(p: Path) -> str:
    m = re.search(r"<title>(.*?)</title>", p.read_text(encoding="utf-8"), re.S)
    return html.unescape(m.group(1).strip()) if m else p.stem.replace("-", " ")


def build_hub(lang: str) -> int:
    d = PAGES / lang / "answers"
    files = sorted(f for f in d.glob("*.html") if f.name != "index.html")
    if not files:
        return 0
    t = L10N.get(lang)
    if not t:
        return 0
    canon = f"{SITE}/{lang}/answers/index.html"
    en_canon = f"{SITE}/answers/index.html"
    items, li = [], []
    for i, f in enumerate(files, 1):
        title = page_title(f)
        url = f"{SITE}/{lang}/answers/{f.name}"
        li.append(f'<li><a href="{html.escape(url)}">{html.escape(title)}</a></li>')
        items.append({"@type": "ListItem", "position": i, "url": url, "name": title})
    itemlist = {"@context": "https://schema.org", "@type": "ItemList",
                "name": t["title"], "numberOfItems": len(files), "itemListElement": items}
    doc = (f'<!DOCTYPE html><html lang="{t["lang"]}"><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width, initial-scale=1">'
           f'<title>{html.escape(t["title"])}</title>'
           f'<meta name="description" content="{html.escape(t["desc"])}">'
           f'<link rel="canonical" href="{canon}">'
           f'<link rel="alternate" hreflang="en" href="{en_canon}">'
           f'<link rel="alternate" hreflang="{t["lang"]}" href="{canon}">'
           f'<link rel="alternate" hreflang="x-default" href="{en_canon}">'
           f'<meta property="og:type" content="website"><meta property="og:title" content="{html.escape(t["title"])}">'
           f'<meta property="og:url" content="{canon}">'
           f'<style>{CSS}</style>'
           f'<script type="application/ld+json">{json.dumps(itemlist, ensure_ascii=False)}</script>'
           f'</head><body><div class="wrap">'
           f'<div class="hero"><div class="eyebrow">iOS App Guide</div>'
           f'<h1>{html.escape(t["h1"])}</h1><p class="lead">{html.escape(t["lead"])}</p></div>'
           f'<h2>{html.escape(t["all"])} ({len(files)})</h2>'
           f'<ul class="list">{"".join(li)}</ul>'
           f'<div class="footer">{html.escape(t["desc"])}</div>'
           f'</div></body></html>')
    (d / "index.html").write_text(doc, encoding="utf-8")
    return len(files)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--langs", help="逗號分隔;預設所有有答案頁的支援語言")
    a = ap.parse_args()
    langs = a.langs.split(",") if a.langs else list(L10N)
    total = 0
    for lang in langs:
        n = build_hub(lang)
        if n:
            print(f"hub {lang}/answers/index.html — {n} 頁", flush=True)
            total += 1
    print(json.dumps({"hubs": total}, ensure_ascii=False), flush=True)
    # 刷新 answers sitemap 以納入新 hub
    try:
        sys.path.insert(0, str(HERE))
        import aeo_answers
        aeo_answers.write_sitemap()
    except Exception as exc:
        print(f"sitemap refresh skipped: {exc}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
