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
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "social"))
sys.path.insert(0, str(HERE))

import android_play  # noqa: E402
from appstore_live import live_app_keys  # noqa: E402
from click_beacon import click_beacon_block  # noqa: E402
from gen_calculator import write_tools_sitemap  # noqa: E402
from gen_feed import feed_discovery_links  # noqa: E402
from gen_store_attribution import (  # noqa: E402
    APP_BOUND_CAMPAIGNS,
    WEB_GALLERY_CAMPAIGNS,
    WEB_HOOK_CAMPAIGNS,
    final_store_url,
)
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
LANGUAGE_NAMES = {"en": "English", "zh-Hant": "繁體中文", "zh-Hans": "简体中文", "ja": "日本語",
                  "ko": "한국어", "de-DE": "Deutsch", "fr-FR": "Français", "pt-BR": "Português (Brasil)"}
# Storefront locale the site-wide stamper resolves each page tree to.
STAMP_LOCALE = {"en": "en-US", "zh-Hant": "zh-Hant", "zh-Hans": "zh-Hans", "ja": "ja",
                "ko": "ko", "de-DE": "de-DE", "fr-FR": "fr-FR", "pt-BR": "pt-BR"}
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

# Wallpaper gallery (reports/outreach_scale/methods_2026-11-18.md item 5): an
# image-search entry page, not a tool.  Only the App's own artwork (the three
# in-app pairs already published by app_image_gallery.py, resized copies with
# keyword file names), one App-bound campaign for every link on every locale
# (os_wpgallery_web, so the downloads aggregate to one Apple campaign row), an
# App Store and a Google Play link under every pair.  Fail closed: no page is
# written when the App is not live, its storefront link is unavailable, the
# Play snapshot has no entry for it, or an image cannot be read.
GALLERY_ASSET_DIR = "assets/app-gallery/duowallpaperstudio"
GALLERY_WEB_DIR = f"{GALLERY_ASSET_DIR}/web"
GALLERY_WIDTH = {"cover": 600, "inner": 1200}
GALLERY_CTA_BLOCK = "wallpaper-gallery-cta"

WALLPAPER_GALLERY = {
    "slug": "foldable-wallpaper-gallery",
    "app": "duowallpaperstudio",
    "campaign": "os_wpgallery_web",
    "single_campaign": True,
    "content_date": "2026-11-18",
    "locales": ("en", "ja", "ko", "zh-Hant", "de-DE", "fr-FR", "pt-BR"),
    "pairs": (
        {"id": "summer-railway",
         "cover": "pair1_summer-railway_outer_1398x2034.jpg", "inner": "pair1_summer-railway_inner_2853x2007.jpg",
         "name": {"en": "Summer Railway", "ja": "夏の線路", "ko": "여름 철길", "zh-Hant": "夏日鐵道",
                  "de-DE": "Sommerbahn", "fr-FR": "Voie ferrée en été", "pt-BR": "Ferrovia de verão"}},
        {"id": "glacier-aurora",
         "cover": "pair2_glacier-aurora_outer_1398x2034.jpg", "inner": "pair2_glacier-aurora_inner_2853x2007.jpg",
         "name": {"en": "Glacier Aurora", "ja": "氷河のオーロラ", "ko": "빙하 오로라", "zh-Hant": "冰河極光",
                  "de-DE": "Gletscher-Polarlicht", "fr-FR": "Aurore sur le glacier", "pt-BR": "Aurora na geleira"}},
        {"id": "clay-puppy",
         "cover": "pair3_clay-puppy_outer_1398x2034.jpg", "inner": "pair3_clay-puppy_inner_2853x2007.jpg",
         "name": {"en": "Clay Puppy", "ja": "粘土の子犬", "ko": "점토 강아지", "zh-Hant": "黏土小狗",
                  "de-DE": "Knetwelpe", "fr-FR": "Chiot en pâte à modeler", "pt-BR": "Filhote de massinha"}},
    ),
    "copy": {
        "en": {
            "title": "Foldable Wallpapers: Cover & Inner Screen Pairs | Gallery",
            "description": (
                "Foldable phone wallpaper pairs from Foldable Wallpaper Studio: a close-up for the cover "
                "screen and the whole scene for the inner screen, cut from one original artwork."
            ),
            "tools": "Tools",
            "heading": "Foldable wallpaper gallery: cover and inner screen pairs",
            "answer": [
                "Each pair below comes from Foldable Wallpaper Studio and is cut from one original artwork: "
                "a close-up for the tall cover screen and the whole scene for the wide inner screen.",
                "In the iPhone app, pairs are saved at the exact pixel sizes of iPhone Duo: 1398 x 2034 for the "
                "cover screen and 2853 x 2007 for the inner screen.",
            ],
            "privacy": "Artwork from the app itself",
            "scope": "iPhone Duo: cover 1398 x 2034 · inner 2853 x 2007",
            "keyword": "foldable wallpaper",
            "cover": "cover screen, close-up",
            "inner": "inner screen, whole scene",
            "hero_text": (
                "On iPhone, Foldable Wallpaper Studio has 300+ original pairs like these, closed and open previews "
                "before you save, widgets in the same colors as your wallpaper, and pairs made from your own photos."
            ),
            "cta": "Get Foldable Wallpaper Studio on the App Store",
            "pair_cta": "Open Foldable Wallpaper Studio on the App Store",
            "play": "Get it on Google Play",
            "how_title": "How to use a pair",
            "how": [
                "On iPhone, the app saves each pair as two images to Photos, one for each screen.",
                "iOS does not let an app change your wallpaper, so the iPhone app's Settings tab shows how to set "
                "the cover screen and the inner screen in a few steps.",
            ],
            "note": "iPhone is a trademark of Apple Inc., registered in the U.S. and other countries. "
                    "This page is not made or endorsed by Apple.",
            "index_title": "Foldable Wallpaper Gallery",
            "index_description": "Cover and inner screen wallpaper pairs from Foldable Wallpaper Studio.",
        },
        "ja": {
            "title": "折りたたみスマホ 壁紙ギャラリー｜外画面と内画面のペア壁紙",
            "description": "折りたたみ壁紙アプリ「折りたたみ壁紙 - 外画面と内画面」のペア壁紙。閉じれば外画面にクローズアップ、開けば内画面に全景。2枚は同じオリジナル作品から切り出しています。",
            "tools": "ツール",
            "heading": "折りたたみスマホ 壁紙ギャラリー：外画面と内画面のペア",
            "answer": [
                "下のペアはどれもアプリ「折りたたみ壁紙 - 外画面と内画面」の作品で、同じオリジナル作品から外画面用のクローズアップと内画面用の全景を切り出しています。",
                "iPhone版アプリでは、iPhone Duoの外画面1398 x 2034、内画面2853 x 2007ピクセルで正確に保存します。",
            ],
            "privacy": "アプリ内の作品をそのまま掲載",
            "scope": "iPhone Duo：外画面 1398 x 2034・内画面 2853 x 2007",
            "keyword": "折りたたみ 壁紙",
            "cover": "外画面、クローズアップ",
            "inner": "内画面、全景",
            "hero_text": "iPhone版アプリには300組以上のオリジナルペア壁紙があり、閉じる・開くプレビュー、壁紙と同じ配色の5種類のウィジェット、写真からのペア作成も使えます。",
            "cta": "App Storeで「折りたたみ壁紙 - 外画面と内画面」を見る",
            "pair_cta": "App Storeで開く",
            "play": "Google Playで入手",
            "how_title": "ペア壁紙の使い方",
            "how": [
                "iPhone版アプリで保存すると、外画面用と内画面用の2枚が写真に保存されます。",
                "外画面にはクローズアップ、内画面には全景を設定します。",
            ],
            "note": "iPhoneは米国およびその他の国で登録されたApple Inc.の商標です。このページはAppleが作成・推奨したものではありません。",
            "index_title": "折りたたみスマホ 壁紙ギャラリー",
            "index_description": "外画面と内画面のペア壁紙をアプリの作品から紹介します。",
        },
        "ko": {
            "title": "폴더블 배경화면 갤러리 | 커버 화면·메인 화면 세트",
            "description": "폴더블 배경화면 - 커버·메인 세트 앱의 세트 배경화면. 접으면 커버 화면에 클로즈업, 펼치면 메인 화면에 같은 장면의 전경이 펼쳐집니다.",
            "tools": "도구",
            "heading": "폴더블 배경화면 갤러리: 커버 화면과 메인 화면 세트",
            "answer": [
                "아래 세트는 모두 「폴더블 배경화면 - 커버·메인 세트」 앱의 작품으로, 하나의 원본 작품에서 커버 화면용 클로즈업과 메인 화면용 전경을 잘라 냈습니다.",
                "iPhone 앱에서는 iPhone Duo의 커버 화면 1398 x 2034, 메인 화면 2853 x 2007 픽셀로 저장합니다.",
            ],
            "privacy": "앱 속 작품 그대로",
            "scope": "iPhone Duo: 커버 1398 x 2034 · 메인 2853 x 2007",
            "keyword": "폴더블 배경화면",
            "cover": "커버 화면, 클로즈업",
            "inner": "메인 화면, 전경",
            "hero_text": "iPhone 앱에는 이런 오리지널 세트가 300세트 이상 있고, 저장 전 접힘·펼침 미리보기, 배경화면과 색을 맞춘 위젯 5종, 내 사진으로 세트 만들기도 있습니다.",
            "cta": "App Store에서 폴더블 배경화면 - 커버·메인 세트 받기",
            "pair_cta": "App Store에서 열기",
            "play": "Google Play에서 받기",
            "how_title": "세트 배경화면 사용법",
            "how": [
                "iPhone 앱에서 저장하면 커버 화면용과 메인 화면용 두 장이 사진 앱에 저장됩니다.",
                "iOS에서는 앱이 배경화면을 자동으로 바꿀 수 없어서, iPhone 앱의 설정 탭에서 적용 방법을 짧게 안내합니다.",
            ],
            "note": "iPhone은 미국 및 기타 국가에 등록된 Apple Inc.의 상표입니다. 이 페이지는 Apple이 만들거나 보증하지 않았습니다.",
            "index_title": "폴더블 배경화면 갤러리",
            "index_description": "앱 속 커버 화면·메인 화면 세트 배경화면 모음.",
        },
        "zh-Hant": {
            "title": "摺疊手機桌布圖庫｜外螢幕＋內螢幕成對桌布",
            "description": "「摺疊手機桌布 - 雙螢幕成對桌布」的成對桌布：合上，外螢幕是特寫；展開，內螢幕是整片全景，兩張出自同一幅原創畫面。",
            "tools": "工具",
            "heading": "摺疊手機桌布圖庫：外螢幕與內螢幕成對桌布",
            "answer": [
                "下面每一組都出自「摺疊手機桌布 - 雙螢幕成對桌布」，從同一幅原創畫面切出外螢幕用的特寫與內螢幕用的全景。",
                "iPhone 版 App 依 iPhone Duo 精確像素存檔：外螢幕 1398 x 2034、內螢幕 2853 x 2007。",
            ],
            "privacy": "App 內原創作品",
            "scope": "iPhone Duo：外螢幕 1398 x 2034・內螢幕 2853 x 2007",
            "keyword": "摺疊手機桌布",
            "cover": "外螢幕，特寫",
            "inner": "內螢幕，全景",
            "hero_text": "iPhone 版 App 裡有 300+ 組這樣的原創成對桌布，儲存前可預覽合上與展開，5 款小工具與桌布同一幅畫，也能用自己的照片做成一對。",
            "cta": "在 App Store 下載摺疊手機桌布",
            "pair_cta": "在 App Store 開啟",
            "play": "在 Google Play 下載",
            "how_title": "成對桌布怎麼用",
            "how": [
                "在 iPhone 版 App 裡儲存，外螢幕與內螢幕各一張會存到「照片」。",
                "iOS 不允許 App 自動換桌布，儲存後在「設定」分頁有外螢幕與內螢幕的簡短教學。",
            ],
            "note": "iPhone 是 Apple Inc. 在美國及其他國家註冊的商標。本頁並非 Apple 製作或背書。",
            "index_title": "摺疊手機桌布圖庫",
            "index_description": "外螢幕＋內螢幕成對桌布，全部出自 App 內原創作品。",
        },
        "de-DE": {
            "title": "Foldable Hintergrundbilder: Paare für Außen- und Innendisplay | Galerie",
            "description": "Hintergrundbilder als Paar aus Foldable Hintergrundbilder: ein Ausschnitt für das Außendisplay und die ganze Szene für das Innendisplay, aus demselben Original.",
            "tools": "Tools",
            "heading": "Galerie: Foldable Hintergrundbilder für Außen- und Innendisplay",
            "answer": [
                "Jedes Paar unten stammt aus der App Foldable Hintergrundbilder und ist aus einem Originalmotiv geschnitten: ein Ausschnitt für das hohe Außendisplay und die ganze Szene für das breite Innendisplay.",
                "In der iPhone-App wird jedes Paar pixelgenau für das iPhone Duo gespeichert: 1398 x 2034 für das Außendisplay und 2853 x 2007 für das Innendisplay.",
            ],
            "privacy": "Motive aus der App selbst",
            "scope": "iPhone Duo: außen 1398 x 2034 · innen 2853 x 2007",
            "keyword": "Foldable Hintergrundbild",
            "cover": "Außendisplay, Ausschnitt",
            "inner": "Innendisplay, ganze Szene",
            "hero_text": "Die iPhone-App hat über 300 originale Paare wie diese, eine Vorschau zugeklappt und aufgeklappt vor dem Speichern, 5 Widgets mit deinem Hintergrund und Paare aus eigenen Fotos.",
            "cta": "Foldable Hintergrundbilder im App Store laden",
            "pair_cta": "Im App Store öffnen",
            "play": "Bei Google Play laden",
            "how_title": "So nutzt du ein Paar",
            "how": [
                "Die iPhone-App speichert jedes Paar als zwei Bilder, eines für jedes Display.",
                "Eine kurze Anleitung in den Einstellungen der iPhone-App zeigt, wie du Außen- und Innendisplay einrichtest.",
            ],
            "note": "iPhone ist eine Marke der Apple Inc., die in den USA und weiteren Ländern eingetragen ist. Diese Seite stammt nicht von Apple und wird nicht von Apple unterstützt.",
            "index_title": "Galerie: Foldable Hintergrundbilder",
            "index_description": "Hintergrundpaare für Außen- und Innendisplay aus der App.",
        },
        "fr-FR": {
            "title": "Fond d'écran pliable : paires écran externe et interne | Galerie",
            "description": "Des fonds d'écran en paires de l'app Fond d'écran pliable – paires : un gros plan pour l'écran externe et toute la scène pour l'écran interne, tirés de la même œuvre originale.",
            "tools": "Outils",
            "heading": "Galerie de fonds d'écran pliables : paires écran externe et interne",
            "answer": [
                "Chaque paire ci-dessous vient de l'app Fond d'écran pliable – paires et est tirée d'une même œuvre originale : un gros plan pour l'écran externe et toute la scène pour l'écran interne.",
                "Dans l'app iPhone, les paires sont enregistrées au pixel près pour l'iPhone Duo : écran externe 1398 x 2034, écran interne 2853 x 2007.",
            ],
            "privacy": "Œuvres de l'app elle-même",
            "scope": "iPhone Duo : externe 1398 x 2034 · interne 2853 x 2007",
            "keyword": "fond d'écran pliable",
            "cover": "écran externe, gros plan",
            "inner": "écran interne, toute la scène",
            "hero_text": "Sur iPhone, l'app propose plus de 300 paires originales comme celles-ci, un aperçu fermé et ouvert avant d'enregistrer, 5 widgets à l'image de votre fond et des paires faites avec vos photos.",
            "cta": "Télécharger Fond d'écran pliable – paires sur l'App Store",
            "pair_cta": "Ouvrir sur l'App Store",
            "play": "Disponible sur Google Play",
            "how_title": "Utiliser une paire",
            "how": [
                "Sur iPhone, l'app enregistre chaque paire en deux images dans Photos, une par écran.",
                "Réglez le gros plan sur l'écran externe et toute la scène sur l'écran interne.",
            ],
            "note": "iPhone est une marque d'Apple Inc., déposée aux États-Unis et dans d'autres pays. Cette page n'est ni créée ni approuvée par Apple.",
            "index_title": "Galerie de fonds d'écran pliables",
            "index_description": "Paires de fonds d'écran pour l'écran externe et l'écran interne, tirées de l'app.",
        },
        "pt-BR": {
            "title": "Papel de parede dobrável: pares para tela externa e interna | Galeria",
            "description": "Papéis de parede em pares do app Papel de parede dobrável: um close na tela externa e a cena inteira na tela interna, da mesma arte original.",
            "tools": "Ferramentas",
            "heading": "Galeria de papel de parede dobrável: pares para tela externa e interna",
            "answer": [
                "Cada par abaixo vem do app Papel de parede dobrável e foi cortado da mesma arte original: um close para a tela externa e a cena inteira para a tela interna.",
                "No app para iPhone, os pares são salvos em pixels exatos do iPhone Duo: 1398 x 2034 para a tela externa e 2853 x 2007 para a interna.",
            ],
            "privacy": "Artes do próprio app",
            "scope": "iPhone Duo: externa 1398 x 2034 · interna 2853 x 2007",
            "keyword": "papel de parede dobrável",
            "cover": "tela externa, close",
            "inner": "tela interna, cena inteira",
            "hero_text": "No iPhone, o app tem mais de 300 pares originais como estes, prévia do celular fechado e aberto antes de salvar, 5 widgets com o seu papel de parede e pares feitos com as suas fotos.",
            "cta": "Baixar Papel de parede dobrável na App Store",
            "pair_cta": "Abrir na App Store",
            "play": "Baixar no Google Play",
            "how_title": "Como usar um par",
            "how": [
                "No iPhone, o app salva cada par como duas imagens no app Fotos, uma para cada tela.",
                "Depois de salvar, a aba de ajustes do app para iPhone mostra um passo a passo curto para as duas telas.",
            ],
            "note": "iPhone é uma marca registrada da Apple Inc. nos EUA e em outros países. Esta página não foi criada nem endossada pela Apple.",
            "index_title": "Galeria de papel de parede dobrável",
            "index_description": "Pares para tela externa e interna, com artes do próprio app.",
        },
    },
}

GALLERY_STYLE = (
    ".pairgrid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,2fr);gap:12px;align-items:start}"
    ".pairgrid figure{margin:0}.pairgrid img{display:block;width:100%;height:auto;border-radius:12px;background:#111}"
    ".pairgrid figcaption{margin-top:4px;font-size:13px;color:var(--muted)}"
    "@media(max-width:640px){.pairgrid{grid-template-columns:1fr}}"
    ".note{font-size:13px;color:var(--muted)}"
)

HOOKS = (FLIPCLOCK, WALLPAPER_GALLERY)

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
    if hook.get("single_campaign"):
        token = hook["campaign"]
        if APP_BOUND_CAMPAIGNS.get(token) != APPSTORE[hook["app"]] or token not in WEB_GALLERY_CAMPAIGNS:
            raise ValueError(f"campaign {token} is not app-bound in gen_store_attribution")
        return token
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


def _head(hook: dict, locale: str, *, schema: dict | None = None, extra_head: str = "") -> str:
    t = hook["copy"][locale]
    slug = hook["slug"]
    url = canonical(slug, locale)
    alternates = "".join(
        f'<link rel="alternate" hreflang="{code}" href="{canonical(slug, code)}">\n'
        for code in hook["locales"]
    )
    home = "" if locale == "en" else f"{locale}/"
    schema = schema or {
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
{extra_head}<style>{STYLE}</style>
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


def gallery_images(pages: Path, hook: dict = WALLPAPER_GALLERY) -> list[dict] | None:
    """The gallery's resized, keyword-named copies of the App's own pairs
    (made once from the originals under ``GALLERY_ASSET_DIR``); None when an
    original or a copy cannot be read."""
    records = []
    for pair in hook["pairs"]:
        sides = {}
        for side in ("cover", "inner"):
            relative = f"{GALLERY_WEB_DIR}/{pair['id']}-foldable-wallpaper-{side}-screen.jpg"
            target = pages / relative
            try:
                from PIL import Image

                if not target.is_file() or target.stat().st_size == 0:
                    source = pages / GALLERY_ASSET_DIR / pair[side]
                    if not source.is_file() or source.stat().st_size == 0:
                        return None
                    with Image.open(source) as image:
                        width = GALLERY_WIDTH[side]
                        height = round(image.height * width / image.width)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        image.convert("RGB").resize((width, height), Image.LANCZOS).save(
                            target, "JPEG", quality=84, optimize=True, progressive=True)
                with Image.open(target) as image:
                    width, height = image.size
            except (ImportError, OSError):
                return None
            sides[side] = {"relative": relative, "width": width, "height": height}
        records.append({"id": pair["id"], "name": pair["name"], **sides})
    return records


def _gallery_alt(hook: dict, locale: str, pair: dict, side: str) -> str:
    t = hook["copy"][locale]
    return f'{pair["name"][locale]} – {t["keyword"]}, {t[side]}'


def _gallery_schema(hook: dict, locale: str, images: list[dict], site: str = None) -> dict:
    site = (site or SITE).rstrip("/")
    t = hook["copy"][locale]
    credit = "Foldable Wallpaper Studio"
    media = []
    for pair in images:
        for side in ("cover", "inner"):
            image = pair[side]
            media.append({
                "@type": "ImageObject",
                "contentUrl": f"{site}/{image['relative']}",
                "name": _gallery_alt(hook, locale, pair, side),
                "caption": _gallery_alt(hook, locale, pair, side),
                "width": image["width"], "height": image["height"],
                "encodingFormat": "image/jpeg",
                "creditText": credit,
                "creator": {"@type": "Organization", "name": credit},
                "copyrightNotice": credit,
            })
    return {
        "@context": "https://schema.org", "@type": "ImageGallery",
        "name": t["heading"], "description": t["description"],
        "url": f"{site}/{page_path(hook['slug'], locale).as_posix()}",
        "inLanguage": locale, "datePublished": hook["content_date"],
        "associatedMedia": media,
    }


def render_gallery(locale: str, show_cta: bool, android_apps: dict | None = None,
                   pages: Path | None = None) -> str | None:
    """The gallery page, or None when it must not be published (fail closed)."""
    hook = WALLPAPER_GALLERY
    entry = (android_apps or {}).get(hook["app"])
    if not show_cta or not entry:
        return None
    images = gallery_images(PAGES if pages is None else pages, hook)
    link = store_link(hook, locale, "page")
    if not images or not link:
        return None
    t = hook["copy"][locale]
    play = android_play.tracked_play_url(entry["play_url"], campaign(hook, locale, "page"), hook["app"])
    site_path = urllib.parse.urlsplit(SITE).path.rstrip("/")
    first = images[0]["cover"]
    extra_head = (
        f'<meta property="og:image" content="{SITE}/{first["relative"]}">\n'
        f'<meta property="og:image:width" content="{first["width"]}">\n'
        f'<meta property="og:image:height" content="{first["height"]}">\n'
        f'<meta property="og:image:alt" content="{_e(_gallery_alt(hook, locale, images[0], "cover"))}">\n'
        f"<style>{GALLERY_STYLE}</style>\n"
    )
    sections = []
    for pair in images:
        figures = "".join(
            f'<figure><img src="{_e(site_path + "/" + pair[side]["relative"])}" '
            f'alt="{_e(_gallery_alt(hook, locale, pair, side))}" width="{pair[side]["width"]}" '
            f'height="{pair[side]["height"]}" loading="lazy" decoding="async">'
            f'<figcaption>{_e(pair["name"][locale])}: {_e(t[side])}</figcaption></figure>'
            for side in ("cover", "inner")
        )
        sections.append(
            f'<section class="card wrap" id="{pair["id"]}"><h2>{_e(pair["name"][locale])}</h2>'
            f'<div class="pairgrid">{figures}</div>\n'
            f"<!-- {GALLERY_CTA_BLOCK}:start --><p>"
            f'<a class="button" href="{_e(link)}" rel="noopener">{_e(t["pair_cta"])}</a> '
            f'<a href="{_e(play)}" rel="noopener">{_e(t["play"])}</a>'
            f"</p><!-- {GALLERY_CTA_BLOCK}:end -->\n</section>\n"
        )
    how = "".join(f"<li>{_e(item)}</li>" for item in t["how"])
    head = _head(hook, locale, schema=_gallery_schema(hook, locale, images), extra_head=extra_head)
    head = head.replace(
        f'<section class="hero wrap"><h1>{_e(t["heading"])}</h1><p class="lead">{_e(" ".join(t["answer"]))}</p>',
        f'<section class="hero wrap"><h1>{_e(t["heading"])}</h1><p class="lead">{_e(" ".join(t["answer"]))}</p>'
        f'<p>{_e(t["hero_text"])} <a href="{_e(link)}" rel="noopener">{_e(t["cta"])}</a></p>', 1)
    return head + "".join(sections) + (
        f'<section class="card wrap"><h2>{_e(t["how_title"])}</h2><ul>{how}</ul>'
        f'<p class="note">{_e(t["note"])}</p></section>\n</main>\n</body>\n</html>\n'
    )


def image_sitemap_entries(pages: Path = PAGES, site: str = SITE) -> list[tuple[str, list[str]]]:
    """(page URL, image URLs) of every published gallery page, for gen_image_sitemap."""
    site = site.rstrip("/")
    hook = WALLPAPER_GALLERY
    entries = []
    for locale in hook["locales"]:
        relative = page_path(hook["slug"], locale).as_posix()
        if not (pages / relative).is_file():
            continue
        images = gallery_images(pages, hook)
        if not images:
            continue
        entries.append((f"{site}/{relative}", [
            f"{site}/{pair[side]['relative']}" for pair in images for side in ("cover", "inner")
        ]))
    return entries


RENDERERS = {FLIPCLOCK["slug"]: render_flipclock, WALLPAPER_GALLERY["slug"]: render_gallery}


def render_page(hook: dict, locale: str, show_cta: bool, android_apps: dict | None = None,
                pages: Path | None = None) -> str | None:
    if hook is WALLPAPER_GALLERY:
        page = render_gallery(locale, show_cta, android_apps, pages)
        if page is None:
            return None
    else:
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
    # Only pages that exist get a card (a fail-closed gallery leaves none).
    live = [h for h in hooks if (index.parent / f'{h["slug"]}.html').is_file()]
    updated = updated.replace(marker, marker + "".join(_index_card(h, locale) for h in live), 1)
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
            page = render_page(hook, locale, show_cta, android_apps, pages)
            if page is None:
                print(f"web hook page skipped (fail closed): {hook['slug']} {locale}", file=sys.stderr)
                continue
            write_text_if_changed(pages / page_path(hook["slug"], locale), page)
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
