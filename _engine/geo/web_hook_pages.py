#!/usr/bin/env python3
"""Browser-only "web hook" pages: a page that is useful on its own in a desktop
browser and points, once, to the App that does the same job on the phone
(yi30 route 47, yi_review 2026-11-08 conditions).

Reusable template: each entry in ``HOOKS`` carries its slug, App key, campaign
family, its own locale list and copy; the shared parts (head, hreflang,
breadcrumb, CSP, the two App placements, tools-index cards, build) live here so
the next page (countdown, pair preview, ...) only adds a dict and a body
renderer.

First page: ``flip-clock`` -- a full screen flip clock (12/24 hour, seconds on
or off, dark / light / dim red night themes, Fullscreen API, screen kept awake
with the Wake Lock API where the browser allows it).

App placements, both visible, never a pop-up, each with its own campaign so the
two report separately (``web_flipclock_<locale>_<position>``):

* ``fs``: one sentence beside the full screen button (page copy; the Google
  Play link is added by ``android_play.inject_html`` with the same referrer).
* ``bottom``: one fixed sentence at the end of the page, in its own managed
  block carrying its own Google Play link.

Copy only restates the App's store description (``data/stayclock_full.json``):
no price, no free / Pro / trial wording, no other brand's name.  The page code
makes no network call; the only one is the site-wide anonymous download-click
counter (``click_beacon``), allowed by the page's CSP exactly like
``web_tools_pilot``.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "social"))
sys.path.insert(0, str(HERE))

import android_play  # noqa: E402
from appstore_live import live_app_keys  # noqa: E402
from click_beacon import click_beacon_block  # noqa: E402
from gen_calculator import write_tools_sitemap  # noqa: E402
from gen_feed import feed_discovery_links  # noqa: E402
from gen_store_attribution import APP_BOUND_CAMPAIGNS, WEB_HOOK_CAMPAIGNS, final_store_url  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402
from videogen.registry import APPSTORE, appstore_url  # noqa: E402
from web_tools_pilot import (  # noqa: E402
    _e,
    content_security_policy,
    js_value,
    json_script,
    load_android_apps,
    write_text_if_changed,
)

PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = os.environ.get("GEO_SITE", PUBLIC_SITE).rstrip("/")
CONTENT_DATE = "2026-11-09"
LANGUAGE_NAMES = {"en": "English", "zh-Hant": "繁體中文", "zh-Hans": "简体中文", "ja": "日本語"}
# Storefront locale the site-wide stamper resolves each page tree to.
STAMP_LOCALE = {"en": "en-US", "zh-Hant": "zh-Hant", "zh-Hans": "zh-Hans", "ja": "ja"}
POSITIONS = ("fs", "bottom")
BOTTOM_BLOCK = "web-hook-bottom-cta"

FLIPCLOCK = {
    "slug": "flip-clock",
    "app": "stayclock",
    "campaign": "web_flipclock",
    # 2026-11-09 read-back of the four searches (route 47 condition c): English
    # results are small personal tool sites, Japanese has one web tool, the two
    # Chinese searches return App Store pages only -- no big site anywhere.
    "locales": ("en", "ja", "zh-Hant", "zh-Hans"),
    "copy": {
        "en": {
            "title": "Online Flip Clock | Full Screen, 12/24 Hour, Seconds",
            "description": (
                "A full screen flip clock that runs in your browser: 12 or 24 hour time, "
                "seconds on or off, dark, light and dim red night themes. Nothing to install."
            ),
            "tools": "Tools",
            "heading": "Full screen flip clock",
            "answer": [
                "This flip clock runs in your browser tab: press Full screen and the whole "
                "display becomes a large clock you can read from across the room.",
                "Choose 12 or 24 hour time, show or hide seconds, and switch between a dark, "
                "a light and a dim red night theme. Nothing is installed and no account is needed.",
            ],
            "privacy": "Runs in your browser; only download-button clicks are counted",
            "scope": "Shows your device's local time",
            "fullscreen": "Full screen",
            "exit": "Exit full screen",
            "hour24": "24-hour time",
            "seconds": "Show seconds",
            "theme": "Theme",
            "themes": {"dark": "Dark", "light": "Light", "night": "Dim red night"},
            "am": "AM",
            "pm": "PM",
            "no_fullscreen": "This browser cannot show a web page in full screen; turn the phone sideways for a larger clock.",
            "keys": "Shortcut: press F for full screen, Esc to leave.",
            "awake": "While in full screen, the page asks the browser to keep the screen awake.",
            "how_title": "How to use it",
            "how": [
                "Open this page on a computer or tablet and press Full screen.",
                "Set 12 or 24 hour time and seconds; the page remembers your choice in this browser.",
                "At night, the dim red theme keeps a dark room dark.",
            ],
            "fs_text": (
                "On iPhone or iPad? Stay Clock: Flip Desk Clock is a full screen clock that "
                "stays on while charging, with a dim red night face on true black and gentle "
                "pixel shifting for OLED screens."
            ),
            "fs_cta": "View Stay Clock on the App Store",
            "bottom_text": (
                "Want the same flip clock on your nightstand? Stay Clock: Flip Desk Clock turns "
                "your iPhone or iPad into an always-on desk clock you can read from across the room, "
                "and the face you pick also appears in StandBy, on the Lock Screen and on Apple Watch."
            ),
            "bottom_cta": "Get Stay Clock on the App Store",
            "index_title": "Full Screen Flip Clock",
            "index_description": "A large flip clock for your browser: full screen, 12/24 hour, seconds, night theme.",
        },
        "ja": {
            "title": "フリップ時計 オンライン｜全画面・12/24時間・秒表示",
            "description": "ブラウザで動く全画面のフリップ時計（パタパタ時計）。12時間制と24時間制、秒の表示切り替え、ダーク・ライト・赤いナイトテーマ。インストール不要です。",
            "tools": "ツール",
            "heading": "全画面フリップ時計",
            "answer": [
                "このフリップ時計（パタパタ時計）はブラウザのタブの中で動きます。「全画面」を押すと、画面いっぱいに部屋の向こうからでも読める大きな時計になります。",
                "12時間制か24時間制、秒の表示・非表示、ダーク・ライト・控えめな赤のナイトテーマを選べます。インストールもアカウントも不要です。",
            ],
            "privacy": "ブラウザ内で動作。ダウンロードボタンのクリック数だけを数えます",
            "scope": "端末の現地時刻を表示します",
            "fullscreen": "全画面",
            "exit": "全画面を終了",
            "hour24": "24時間制",
            "seconds": "秒を表示",
            "theme": "テーマ",
            "themes": {"dark": "ダーク", "light": "ライト", "night": "赤いナイト"},
            "am": "午前",
            "pm": "午後",
            "no_fullscreen": "このブラウザはWebページを全画面表示できません。スマホを横向きにすると時計が大きくなります。",
            "keys": "ショートカット：F キーで全画面、Esc で終了。",
            "awake": "全画面のあいだは、画面がスリープしないようブラウザに求めます。",
            "how_title": "使い方",
            "how": [
                "パソコンやタブレットでこのページを開き、「全画面」を押します。",
                "12時間制・24時間制と秒表示を選びます。設定はこのブラウザに保存されます。",
                "夜は赤いナイトテーマにすると、暗い部屋でもまぶしくありません。",
            ],
            "fs_text": "iPhone・iPadなら「Stay Clock:パタパタ卓上時計」。充電中は画面が点いたままの全画面時計になり、夜は真っ黒な背景に控えめな赤い文字盤、OLED向けのピクセルシフトも備えています。",
            "fs_cta": "App Store で Stay Clock を見る",
            "bottom_text": "同じパタパタ時計を枕元にも。「Stay Clock:パタパタ卓上時計」はiPhoneやiPadを部屋の隅からでも読める常時点灯のデスク時計に変え、選んだ文字盤はStandBy、ロック画面、Apple Watchにも表示されます。",
            "bottom_cta": "App Store で Stay Clock を入手",
            "index_title": "全画面フリップ時計",
            "index_description": "ブラウザで使える大きなパタパタ時計。全画面・12/24時間・秒表示・ナイトテーマ。",
        },
        "zh-Hant": {
            "title": "線上翻頁時鐘｜全螢幕、12/24 小時、顯示秒數",
            "description": "在瀏覽器裡執行的全螢幕翻頁時鐘：12 或 24 小時制、秒數開關，深色、淺色與柔和紅色夜間主題，不用安裝。",
            "tools": "工具",
            "heading": "全螢幕翻頁時鐘",
            "answer": [
                "這個翻頁時鐘直接在瀏覽器分頁裡執行：按下「全螢幕」，整個畫面就變成隔著房間也看得清楚的大時鐘。",
                "可選 12 或 24 小時制、顯示或隱藏秒數，並在深色、淺色與柔和紅色夜間主題之間切換；不用安裝，也不用帳號。",
            ],
            "privacy": "在瀏覽器裡執行；只計算下載鈕點擊次數",
            "scope": "顯示你裝置上的當地時間",
            "fullscreen": "全螢幕",
            "exit": "離開全螢幕",
            "hour24": "24 小時制",
            "seconds": "顯示秒數",
            "theme": "主題",
            "themes": {"dark": "深色", "light": "淺色", "night": "柔和紅色夜間"},
            "am": "上午",
            "pm": "下午",
            "no_fullscreen": "這個瀏覽器無法把網頁切成全螢幕；把手機轉成橫向，時鐘會變大。",
            "keys": "快速鍵：按 F 進入全螢幕，按 Esc 離開。",
            "awake": "全螢幕期間，網頁會請瀏覽器保持螢幕不休眠。",
            "how_title": "使用方式",
            "how": [
                "在電腦或平板打開這一頁，按「全螢幕」。",
                "選擇 12 或 24 小時制與是否顯示秒數；設定會記在這個瀏覽器裡。",
                "夜裡改用柔和紅色主題，暗暗的房間也不刺眼。",
            ],
            "fs_text": "用 iPhone 或 iPad？「Stay Clock:翻頁桌鐘」是充電時保持恆亮的全螢幕時鐘，夜裡可改成純黑底柔和紅字，並有為 OLED 螢幕設計的像素偏移。",
            "fs_cta": "到 App Store 查看翻頁桌鐘",
            "bottom_text": "想把同樣的翻頁鐘放到床頭？「Stay Clock:翻頁桌鐘」把 iPhone 或 iPad 變成隔著房間也看得清楚的全天候桌鐘，你選的錶面也會出現在 StandBy、鎖定畫面與 Apple Watch。",
            "bottom_cta": "到 App Store 下載翻頁桌鐘",
            "index_title": "全螢幕翻頁時鐘",
            "index_description": "在瀏覽器裡使用的大型翻頁時鐘：全螢幕、12/24 小時、秒數、夜間主題。",
        },
        "zh-Hans": {
            "title": "在线翻页时钟｜全屏、12/24 小时、显示秒数",
            "description": "在浏览器中运行的全屏翻页时钟：12 或 24 小时制、秒数开关，深色、浅色与柔和红色夜间主题，无需安装。",
            "tools": "工具",
            "heading": "全屏翻页时钟",
            "answer": [
                "这个翻页时钟直接在浏览器标签页中运行：点击“全屏”，整个屏幕就变成隔着房间也能看清的大时钟。",
                "可选 12 或 24 小时制、显示或隐藏秒数，并在深色、浅色与柔和红色夜间主题之间切换；无需安装，也不用账户。",
            ],
            "privacy": "在浏览器中运行；只统计下载按钮点击次数",
            "scope": "显示你设备上的当地时间",
            "fullscreen": "全屏",
            "exit": "退出全屏",
            "hour24": "24 小时制",
            "seconds": "显示秒数",
            "theme": "主题",
            "themes": {"dark": "深色", "light": "浅色", "night": "柔和红色夜间"},
            "am": "上午",
            "pm": "下午",
            "no_fullscreen": "这个浏览器无法把网页切换为全屏；把手机横过来，时钟会变大。",
            "keys": "快捷键：按 F 进入全屏，按 Esc 退出。",
            "awake": "全屏期间，网页会请求浏览器保持屏幕不休眠。",
            "how_title": "使用方法",
            "how": [
                "在电脑或平板上打开本页，点击“全屏”。",
                "选择 12 或 24 小时制以及是否显示秒数；设置会保存在这个浏览器里。",
                "夜里换成柔和红色主题，昏暗的房间也不刺眼。",
            ],
            "fs_text": "用 iPhone 或 iPad？“Stay Clock:翻页桌面时钟”是充电时保持常亮的全屏时钟，夜里可切换为纯黑底柔和红字，并有为 OLED 屏幕设计的像素偏移。",
            "fs_cta": "在 App Store 查看翻页桌面时钟",
            "bottom_text": "想把同样的翻页时钟放到床头？“Stay Clock:翻页桌面时钟”把 iPhone 或 iPad 变成隔着房间也能看清的常亮桌面时钟，你选择的表盘也会出现在 StandBy、锁定屏幕与 Apple Watch 上。",
            "bottom_cta": "在 App Store 下载翻页桌面时钟",
            "index_title": "全屏翻页时钟",
            "index_description": "在浏览器中使用的大号翻页时钟：全屏、12/24 小时、秒数、夜间主题。",
        },
    },
}

HOOKS = (FLIPCLOCK,)

STYLE = r"""
:root{--ink:#171b24;--muted:#5d6574;--line:#dce1eb;--bg:#eef3f8;--navy:#18365f}
*{box-sizing:border-box}body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","PingFang SC","Hiragino Sans","Noto Sans TC","Noto Sans SC","Noto Sans JP",sans-serif;background:var(--bg);color:var(--ink);line-height:1.6}
a{color:#18558b}.wrap{width:min(1120px,100% - 32px);margin:auto}.top{background:#fff;border-bottom:1px solid var(--line)}
.nav{min-height:58px;display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap}.nav a{text-decoration:none;font-weight:800}.nav-links{display:flex;gap:14px;flex-wrap:wrap}.nav-links a{color:var(--muted);font-size:14px}
.hero{padding:30px 0 6px}h1{font-size:clamp(28px,5vw,44px);line-height:1.12;margin:.2em 0}.lead{color:var(--muted);font-size:17px;margin:0}.trust{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}.badge{border:1px solid var(--line);background:#fff;border-radius:999px;padding:6px 12px;font-size:13px;font-weight:800;color:var(--navy)}
.card{background:#fff;border:1px solid var(--line);border-radius:22px;padding:clamp(16px,3vw,28px);margin:18px auto}.card h2{margin:0 0 10px;font-size:clamp(20px,3vw,26px)}
.button{border:0;border-radius:999px;background:var(--navy);color:#fff;text-decoration:none;font-weight:800;padding:10px 18px;cursor:pointer;display:inline-flex;font:inherit;font-weight:800}.row{display:flex;flex-wrap:wrap;gap:12px;align-items:center}
.help{color:var(--muted);font-size:13px;margin:6px 0 0}select{font:inherit;min-height:40px;border:1px solid #cbd3df;border-radius:10px;padding:4px 8px;background:#fff}label{font-weight:700;font-size:14px}
.stage{--face:#1b1d22;--digit:#f2f2ee;--seam:#0b0c0f;--back:#0f1013;background:var(--back);border-radius:18px;padding:clamp(14px,4vw,40px);display:flex;align-items:center;justify-content:center;min-height:280px;user-select:none}
.stage[data-theme=light]{--face:#fbfaf6;--digit:#20232a;--seam:#c9ccd3;--back:#e3e6ec}.stage[data-theme=night]{--face:#000;--digit:#a3241b;--seam:#160604;--back:#000}
.clock{display:flex;align-items:center;gap:clamp(4px,1.2vw,14px);font-variant-numeric:tabular-nums;font-weight:700;line-height:1}
.group{display:flex;gap:clamp(3px,.6vw,8px)}.digit{position:relative;width:.78em;height:1.18em;display:flex;align-items:center;justify-content:center;background:var(--face);color:var(--digit);border-radius:.09em;font-size:clamp(48px,13vw,190px);perspective:4em;box-shadow:0 .03em .06em rgba(0,0,0,.35)}
.digit::after{content:"";position:absolute;left:0;right:0;top:50%;height:max(2px,.02em);background:var(--seam)}.digit span{display:block;transform-origin:50% 50%}.digit.turn span{animation:turn .42s ease-out}
.small .digit{font-size:clamp(28px,7vw,100px)}.sep{color:var(--digit);font-size:clamp(36px,9vw,130px);opacity:.75}.ampm{color:var(--digit);font-size:clamp(14px,2.4vw,34px);align-self:flex-end;opacity:.85}
@keyframes turn{0%{transform:rotateX(85deg);opacity:.25}100%{transform:rotateX(0);opacity:1}}
@media(prefers-reduced-motion:reduce){.digit.turn span{animation:none}}
.stage:fullscreen{border-radius:0;width:100vw;height:100vh}.stage:fullscreen .digit{font-size:min(20vw,36vh)}.stage:fullscreen .small .digit{font-size:min(11vw,20vh)}.stage:fullscreen .sep{font-size:min(14vw,26vh)}
.stage:-webkit-full-screen{border-radius:0;width:100vw;height:100vh}
.cta{background:linear-gradient(135deg,#f9fbff,#e8f1f8)}ul{padding-left:20px}li{margin:6px 0}
"""


def page_path(slug: str, locale: str) -> Path:
    prefix = Path() if locale == "en" else Path(locale)
    return prefix / "tools" / f"{slug}.html"


def canonical(slug: str, locale: str) -> str:
    return f"{SITE}/{page_path(slug, locale).as_posix()}"


def campaign(hook: dict, locale: str, position: str) -> str:
    token = f"{hook['campaign']}_{locale.replace('-', '_').lower()}_{position}"
    if token not in APP_BOUND_CAMPAIGNS or token not in WEB_HOOK_CAMPAIGNS:
        raise ValueError(f"campaign {token} is not app-bound in gen_store_attribution")
    return token


def store_link(hook: dict, locale: str, position: str) -> str:
    """Final App Store link: storefront aligned, app-bound campaign kept."""
    token = campaign(hook, locale, position)
    raw = appstore_url(hook["app"], token)
    provider = os.environ.get("APP_STORE_PROVIDER_TOKEN", "").strip()
    if not provider:
        return raw
    final = final_store_url(raw, token, provider, locale=STAMP_LOCALE[locale],
                            app_id=APPSTORE[hook["app"]])
    return final or ""


def _language_links(hook: dict, locale: str) -> str:
    return "".join(
        f'<a href="{canonical(hook["slug"], code)}" hreflang="{code}" lang="{code}">{LANGUAGE_NAMES[code]}</a>'
        for code in hook["locales"] if code != locale
    )


def _head(hook: dict, locale: str) -> str:
    t = hook["copy"][locale]
    slug = hook["slug"]
    url = canonical(slug, locale)
    alternates = "".join(
        f'<link rel="alternate" hreflang="{code}" href="{canonical(slug, code)}">\n'
        for code in hook["locales"]
    )
    home = "" if locale == "en" else f"{locale}/"
    schema = {
        "@context": "https://schema.org", "@type": "WebApplication",
        "name": t["heading"], "description": t["description"], "url": url,
        "inLanguage": locale, "datePublished": CONTENT_DATE,
        "applicationCategory": "UtilitiesApplication", "operatingSystem": "Any",
        "browserRequirements": "JavaScript; no download or account is used",
    }
    breadcrumb = {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "iOS App Guide", "item": f"{SITE}/{home}index.html"},
            {"@type": "ListItem", "position": 2, "name": t["tools"], "item": f"{SITE}/{home}tools/index.html"},
            {"@type": "ListItem", "position": 3, "name": t["heading"], "item": url},
        ],
    }
    return f"""<!DOCTYPE html>
<html lang="{locale}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_e(t["title"])}</title>
<meta name="description" content="{_e(t["description"])}">
<meta http-equiv="Content-Security-Policy" content="{{CSP_PLACEHOLDER}}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{url}">
{alternates}<link rel="alternate" hreflang="x-default" href="{canonical(slug, "en")}">
<meta property="og:type" content="website">
<meta property="og:title" content="{_e(t["heading"])}">
<meta property="og:description" content="{_e(t["description"])}">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary">
<style>{STYLE}</style>
{json_script(schema)}
{json_script(breadcrumb)}
{feed_discovery_links()}
{click_beacon_block()}
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{SITE}/{home}index.html">iOS App Guide</a><nav class="nav-links"><a href="{SITE}/{home}tools/index.html">{_e(t["tools"])}</a>{_language_links(hook, locale)}</nav></div></header>
<main>
<section class="hero wrap"><h1>{_e(t["heading"])}</h1><p class="lead">{_e(" ".join(t["answer"]))}</p><div class="trust"><span class="badge">{_e(t["privacy"])}</span><span class="badge">{_e(t["scope"])}</span></div></section>
"""


def _fs_cta(hook: dict, locale: str, show_cta: bool) -> str:
    """The sentence beside the full screen button (page copy; Play is injected)."""
    if not show_cta:
        return ""
    link = store_link(hook, locale, "fs")
    if not link:
        return ""
    t = hook["copy"][locale]
    return (f'<p class="help" id="app-fs">{_e(t["fs_text"])} '
            f'<a href="{_e(link)}" rel="noopener">{_e(t["fs_cta"])}</a></p>')


def _bottom_cta(hook: dict, locale: str, show_cta: bool, android_apps: dict | None) -> str:
    """The fixed sentence at the end of the page, with its own Play link."""
    if not show_cta:
        return ""
    link = store_link(hook, locale, "bottom")
    if not link:
        return ""
    t = hook["copy"][locale]
    play = ""
    entry = (android_apps or {}).get(hook["app"])
    if entry:
        url = android_play.tracked_play_url(entry["play_url"], campaign(hook, locale, "bottom"), hook["app"])
        label = (f"Get {android_play.display_name(hook['app'], entry)} on Google Play"
                 if locale == "en" else "Google Play")
        play = f'<p class="help">Android: <a href="{_e(url)}" rel="noopener">{_e(label)}</a></p>'
    return (f'<!-- {BOTTOM_BLOCK}:start --><section class="card cta wrap" id="get-app">'
            f'<p>{_e(t["bottom_text"])}</p><p><a class="button" href="{_e(link)}" rel="noopener">'
            f'{_e(t["bottom_cta"])}</a></p>{play}</section><!-- {BOTTOM_BLOCK}:end -->\n')


def render_flipclock(locale: str, show_cta: bool, android_apps: dict | None = None) -> str:
    hook = FLIPCLOCK
    t = hook["copy"][locale]
    options = "".join(f'<option value="{key}">{_e(label)}</option>' for key, label in t["themes"].items())
    how = "".join(f"<li>{_e(item)}</li>" for item in t["how"])
    copy = {key: t[key] for key in ("fullscreen", "exit", "am", "pm")}
    hour24_default = "false" if locale == "en" else "true"
    return _head(hook, locale) + f"""<section class="card wrap" id="tool">
<div class="stage" id="stage" data-theme="dark" role="timer" aria-label="{_e(t["heading"])}"><div class="clock" id="clock"></div></div>
<div class="row" style="margin-top:14px"><button class="button" id="fs" type="button">{_e(t["fullscreen"])}</button>
<label><input id="h24" type="checkbox"> {_e(t["hour24"])}</label>
<label><input id="sec" type="checkbox" checked> {_e(t["seconds"])}</label>
<label for="theme">{_e(t["theme"])}</label><select id="theme">{options}</select></div>
<p class="help" id="nofs" hidden>{_e(t["no_fullscreen"])}</p>
<p class="help">{_e(t["keys"])} {_e(t["awake"])}</p>
{_fs_cta(hook, locale, show_cta)}
</section>
<section class="card wrap"><h2>{_e(t["how_title"])}</h2><ul>{how}</ul></section>
{_bottom_cta(hook, locale, show_cta, android_apps)}</main>
<script>
const COPY={js_value(copy)};
const $=id=>document.getElementById(id);
const stage=$("stage"),clock=$("clock"),fsButton=$("fs");
const store={{get(k){{try{{return localStorage.getItem("flipclock."+k);}}catch(e){{return null;}}}},set(k,v){{try{{localStorage.setItem("flipclock."+k,v);}}catch(e){{}}}}}};
const saved={{h24:store.get("h24"),sec:store.get("sec"),theme:store.get("theme")}};
$("h24").checked=saved.h24===null?{hour24_default}:saved.h24==="1";
if(saved.sec!==null)$("sec").checked=saved.sec==="1";
if(saved.theme&&["dark","light","night"].includes(saved.theme))$("theme").value=saved.theme;
stage.dataset.theme=$("theme").value;
let shown="",lock=null;
function pad(n){{return String(n).padStart(2,"0");}}
function build(text,suffix){{clock.textContent="";const parts=text.split(":");parts.forEach((part,i)=>{{if(i){{const s=document.createElement("span");s.className="sep";s.textContent=":";clock.appendChild(s);}}const g=document.createElement("div");g.className="group"+(i===2?" small":"");for(const ch of part){{const d=document.createElement("div");d.className="digit";const v=document.createElement("span");v.textContent=ch;d.appendChild(v);g.appendChild(d);}}clock.appendChild(g);}});if(suffix){{const a=document.createElement("span");a.className="ampm";a.textContent=suffix;clock.appendChild(a);}}}}
function tick(){{const now=new Date();let h=now.getHours(),suffix="";if(!$("h24").checked){{suffix=h<12?COPY.am:COPY.pm;h=h%12||12;}}let text=pad(h)+":"+pad(now.getMinutes());if($("sec").checked)text+=":"+pad(now.getSeconds());const key=text+suffix;if(key.length!==shown.length||!clock.querySelector(".digit")){{build(text,suffix);}}else{{const cells=clock.querySelectorAll(".digit span");let n=0;for(const ch of text.replace(/:/g,"")){{const cell=cells[n++];if(cell&&cell.textContent!==ch){{cell.textContent=ch;const d=cell.parentNode;d.classList.remove("turn");void d.offsetWidth;d.classList.add("turn");}}}}const a=clock.querySelector(".ampm");if(a)a.textContent=suffix;}}shown=key;setTimeout(tick,1000-now.getMilliseconds()+5);}}
const canFull=!!(document.fullscreenEnabled||document.webkitFullscreenEnabled);
if(!canFull){{fsButton.hidden=true;$("nofs").hidden=false;}}
function isFull(){{return !!(document.fullscreenElement||document.webkitFullscreenElement);}}
async function keepAwake(on){{try{{if(on&&"wakeLock" in navigator){{lock=await navigator.wakeLock.request("screen");}}else if(lock){{await lock.release();lock=null;}}}}catch(e){{lock=null;}}}}
function toggle(){{if(!canFull)return;if(isFull()){{(document.exitFullscreen||document.webkitExitFullscreen).call(document);}}else{{(stage.requestFullscreen||stage.webkitRequestFullscreen).call(stage);}}}}
function onFull(){{const on=isFull();fsButton.textContent=on?COPY.exit:COPY.fullscreen;keepAwake(on);}}
document.addEventListener("fullscreenchange",onFull);document.addEventListener("webkitfullscreenchange",onFull);
document.addEventListener("visibilitychange",()=>{{if(document.visibilityState==="visible"&&isFull())keepAwake(true);}});
fsButton.addEventListener("click",toggle);stage.addEventListener("dblclick",toggle);
document.addEventListener("keydown",e=>{{if((e.key==="f"||e.key==="F")&&!e.metaKey&&!e.ctrlKey&&!e.altKey&&e.target.tagName!=="SELECT"&&e.target.tagName!=="INPUT")toggle();}});
$("h24").addEventListener("change",()=>{{store.set("h24",$("h24").checked?"1":"0");shown="";}});
$("sec").addEventListener("change",()=>{{store.set("sec",$("sec").checked?"1":"0");shown="";}});
$("theme").addEventListener("change",()=>{{stage.dataset.theme=$("theme").value;store.set("theme",$("theme").value);}});
tick();
</script>
</body>
</html>
"""


RENDERERS = {FLIPCLOCK["slug"]: render_flipclock}


def render_page(hook: dict, locale: str, show_cta: bool, android_apps: dict | None = None) -> str:
    page = RENDERERS[hook["slug"]](locale, show_cta, android_apps)
    if android_apps:
        page = android_play.inject_html(page, android_apps)
    return page.replace("{CSP_PLACEHOLDER}", content_security_policy(page), 1)


def _index_card(hook: dict, locale: str) -> str:
    t = hook["copy"][locale]
    return (f'<article class="card third"><h2><a href="{hook["slug"]}.html">'
            f'{_e(t["index_title"])}</a></h2><p>{_e(t["index_description"])}</p></article>')


def update_index(index: Path, locale: str) -> bool:
    if not index.exists():
        return False
    text = index.read_text(encoding="utf-8")
    updated = text
    hooks = [hook for hook in HOOKS if locale in hook["locales"]]
    for hook in hooks:
        updated = re.sub(
            r'<article class="card third"><h2><a href="' + re.escape(f'{hook["slug"]}.html')
            + r'">.*?</article>', "", updated, flags=re.S)
    marker = '<section class="wrap grid">'
    if marker not in updated:
        raise RuntimeError(f"{index} is missing its tools grid")
    updated = updated.replace(marker, marker + "".join(_index_card(h, locale) for h in hooks), 1)
    if updated == text:
        return False
    index.write_text(updated, encoding="utf-8")
    return True


def build(pages: Path = PAGES, *, live_keys, android_apps: dict | None = None) -> list[str]:
    outputs = []
    locales: set[str] = set()
    for hook in HOOKS:
        show_cta = hook["app"] in live_keys
        for locale in hook["locales"]:
            write_text_if_changed(pages / page_path(hook["slug"], locale),
                                  render_page(hook, locale, show_cta, android_apps))
            outputs.append(canonical(hook["slug"], locale))
            locales.add(locale)
    for locale in sorted(locales):
        prefix = Path() if locale == "en" else Path(locale)
        update_index(pages / prefix / "tools" / "index.html", locale)
    return outputs


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    live_keys = set(live_app_keys(APPSTORE, str(PAGES), refresh=False))
    for output in build(PAGES, live_keys=live_keys, android_apps=load_android_apps()):
        print(f"web hook page -> {output}")
    if "--no-sitemap" not in args:
        print(f"tools sitemap -> {write_tools_sitemap()} urls")


if __name__ == "__main__":
    main()
