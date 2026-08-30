#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""在免費工具頁加一個誠實的「新工具上線通知」訂閱區塊。

為什麼:站上 26+ 個免費工具頁是**唯一有真實使用者**的自有資產,但使用者
用完就走,我們手上什麼都沒留下。一個只承諾「有新免費工具時通知你」的訂閱,
是把一次性流量變成可以再觸及的名單、而且不必說任何不實的話。

誠實鐵則(寫死在程式裡,不可設定):
  * 沒有預設勾選的同意框(整個表單就只有一個 email 欄位 + 一顆按鈕)。
  * 旁邊直接寫清楚用途、不會轉給第三方、可一鍵取消。
  * 不用「輸入 email 才能下載」這種誘餌 — 工具本來就是免費直接用。

停用時(`enabled:false` 或 `endpoint` 空白)會把先前注入的區塊**移除**,
所以絕不會有壞掉的表單留在線上。

這支必須註冊在 `geo/publish.py` 的管線裡(產生器之後、sitemap 之前):
直接改 `geo/pages` 的 HTML 會在下一次發布時被重新產生的頁面覆蓋掉。

用法:
    python3 gen_tool_email_capture.py [--dry]
"""
import argparse
import glob
import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(HERE, "pages")
CONFIG = os.path.join(HERE, "tool_email_capture.json")
MARKER = "tool-email-capture"
BLOCK_RE = re.compile(
    r'<section class="wrap tool-email-capture".*?</section>', re.S
)
LANG_RE = re.compile(r'<html[^>]*\blang="([^"]+)"', re.I)
STYLE = (
    "border:1px solid rgba(120,100,70,.25);border-radius:14px;"
    "padding:18px 20px;margin:28px 0;background:rgba(255,250,240,.55)"
)


def _load_config():
    with open(CONFIG, encoding="utf-8") as handle:
        return json.load(handle)


def _copy_for(config, lang):
    copy = config.get("copy") or {}
    for candidate in (lang, lang.split("-")[0],
                      {"zh": "zh-Hant", "en": "en-US"}.get(
                          lang.split("-")[0], ""), "en-US"):
        if candidate and candidate in copy:
            return copy[candidate]
    return copy.get("en-US", {})


def _block(config, lang):
    text = _copy_for(config, lang)
    if not text:
        return ""
    hidden = "".join(
        f'<input type="hidden" name="{html.escape(str(name))}" '
        f'value="{html.escape(str(value))}">'
        for name, value in (
            (config.get("extra_fields") or {}).get(
                config.get("provider", "custom"), {}) or {}
        ).items()
    )
    manage = config.get("manage_url") or ""
    manage_link = (
        f' <a href="{html.escape(manage)}">'
        f'{html.escape(text.get("button", "Manage"))}</a>' if manage else ""
    )
    return (
        f'<section class="wrap {MARKER}" style="{STYLE}">'
        f'<h2>{html.escape(text.get("heading", ""))}</h2>'
        f'<p>{html.escape(text.get("body", ""))}</p>'
        f'<form action="{html.escape(config["endpoint"])}" method="post" '
        f'target="_blank" style="display:flex;gap:8px;flex-wrap:wrap">'
        f'<label for="tec-email" class="visually-hidden" '
        f'style="position:absolute;left:-9999px">'
        f'{html.escape(text.get("placeholder", "email"))}</label>'
        f'<input id="tec-email" type="email" required '
        f'name="{html.escape(config.get("email_field", "email"))}" '
        f'placeholder="{html.escape(text.get("placeholder", ""))}" '
        f'style="flex:1 1 220px;padding:10px 12px;border-radius:10px;'
        f'border:1px solid rgba(120,100,70,.35)">'
        f'{hidden}'
        f'<button type="submit" style="padding:10px 18px;border-radius:10px;'
        f'border:0;background:#7a5c2e;color:#fff;cursor:pointer">'
        f'{html.escape(text.get("button", ""))}</button>'
        f'</form>'
        f'<p><small>{html.escape(text.get("promise", ""))}{manage_link}'
        f'</small></p>'
        f'</section>'
    )


def _tool_pages():
    """英文工具頁 + 各語系工具頁(pages/<locale>/tools/*.html)。

    2026-08-12:demand_tools.py 開始產出 ja / ko / de-DE / zh-Hant 的工具頁,
    這裡原本只掃英文目錄,那些頁面永遠拿不到訂閱區塊。`_block()` 已經會依
    `<html lang>` 挑對應語言的文案,所以直接把語系目錄納入即可。
    """
    return sorted(
        set(glob.glob(os.path.join(PAGES, "tools", "*.html")))
        | set(glob.glob(os.path.join(PAGES, "*", "tools", "*.html")))
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry", action="store_true")
    args = parser.parse_args()

    config = _load_config()
    active = bool(config.get("enabled")) and bool(config.get("endpoint"))
    changed = removed = 0
    pages = _tool_pages()

    for path in pages:
        with open(path, encoding="utf-8") as handle:
            page = handle.read()
        stripped = BLOCK_RE.sub("", page)          # 先移除舊區塊 = 冪等
        if active:
            match = LANG_RE.search(page)
            block = _block(config, match.group(1) if match else "en-US")
            if "</main>" in stripped:
                updated = stripped.replace("</main>", block + "</main>", 1)
            elif "</body>" in stripped:
                updated = stripped.replace("</body>", block + "</body>", 1)
            else:
                continue
        else:
            updated = stripped
            if updated != page:
                removed += 1
        if updated != page:
            changed += 1
            if not args.dry:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(updated)

    state = "on" if active else "off(待一次性設定 endpoint)"
    print(f"{'DRY ' if args.dry else ''}tool-email-capture {state}: "
          f"{changed} / {len(pages)} 頁更新"
          + (f",移除舊區塊 {removed}" if removed else ""))
    if not active:
        print("  → 啟用方式:在 geo/tool_email_capture.json 填 endpoint 並把 "
              "enabled 設為 true(見 geo/TOOL_EMAIL_CAPTURE_SETUP.md)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
