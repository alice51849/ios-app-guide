#!/usr/bin/env python3
"""Two browser-only tool pages, three locales each (yi_review 2026-11-04 pilot).

* ``foldable-wallpaper-pair-preview``: pick a cover-screen and an inner-screen
  image (or one of three licensed sample pairs) and preview them on a foldable's
  two screens at the proportions Foldable Wallpaper Studio exports.
* ``passport-photo-crop``: crop a local photo to a U.S. 2x2 in, Taiwan
  35x45 mm or Japan 35x45 mm frame and save a 300 DPI JPEG.

Both run entirely in the tab: images are decoded from the local file picker
(or same-site sample files) and never sent anywhere.  The tool code itself
makes no network call; the only one on the page is the site-wide anonymous
download-button click counter (``click_beacon.click_beacon_block``: page path,
app, ct and store only, no cookie, no IP kept).  A Content-Security-Policy meta
allows exactly that endpoint (``connect-src``) and exactly the page's own
inline scripts by hash; the tests enforce both (2026-11-05, 二十角度 13-1).
App Store CTAs carry one app-bound campaign per tool and locale
(gen_store_attribution.WEB_TOOL_PILOT_CAMPAIGNS); the Google Play link is
added through android_play.inject_html, the same pass the deploy runs.
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "social"))
sys.path.insert(0, str(HERE))

import android_play  # noqa: E402
import base64  # noqa: E402
import hashlib  # noqa: E402
from click_beacon import CLICK_BEACON_URL, click_beacon_block  # noqa: E402
from appstore_live import live_app_keys  # noqa: E402
from gen_calculator import write_tools_sitemap  # noqa: E402
from gen_feed import feed_discovery_links  # noqa: E402
from gen_store_attribution import APP_BOUND_CAMPAIGNS, final_store_url  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402
from videogen.registry import APPSTORE, appstore_url  # noqa: E402

PAGES = Path(os.environ.get("GEO_PAGES", HERE / "pages"))
SITE = os.environ.get("GEO_SITE", PUBLIC_SITE).rstrip("/")
LOCALES = ("en", "zh-Hant", "ja")
# Storefront locale the site-wide stamper resolves each page tree to.
STAMP_LOCALE = {"en": "en-US", "zh-Hant": "zh-Hant", "ja": "ja"}
CONTENT_DATE = "2026-11-04"
SAMPLE_DIR = "assets/tools/duo-pair-preview"
SAMPLES = ("pair1", "pair2", "pair3")
US_SOURCE = "https://travel.state.gov/en/passports/apply/help/photos.html"
TW_SOURCE = "https://www.boca.gov.tw/"
JP_SOURCE = "https://www.mofa.go.jp/mofaj/toko/passport/"

# Final print sizes and head-height ranges (top of head to chin), millimetres.
PASSPORT_PRESETS = {
    "us": {"w": 50.8, "h": 50.8, "top": 6.0, "head_min": 25.4, "head_max": 34.9},
    "tw": {"w": 35.0, "h": 45.0, "top": 4.0, "head_min": 32.0, "head_max": 36.0},
    "jp": {"w": 35.0, "h": 45.0, "top": 4.0, "head_min": 32.0, "head_max": 36.0},
}
# Pixel proportions of the two screens Foldable Wallpaper Studio exports
# (outreach/press/duo_pairs_pack: cover 1398x2034, inner 2853x2007).
DUO_SCREENS = {"outer": [1398, 2034], "inner": [2853, 2007]}

# Official size table (13-2): photo size and head height (chin to top of head),
# each row with its official source.  Same numbers as PASSPORT_PRESETS.
PASSPORT_SIZE_SOURCES = {"us": US_SOURCE, "tw": TW_SOURCE, "jp": JP_SOURCE}
# Questions with measured search demand only (geo/SEARCH_DEMAND_AUDIT.md §3:
# "can you wear glasses / smile in a passport photo", "why do passport photos
# get rejected"); answers restate the U.S. Department of State photo rules.
FAQ_SOURCE_NOTE_DATE = "2026-10-16"

DUO = {
    "slug": "foldable-wallpaper-pair-preview",
    "app": "duowallpaperstudio",
    "campaign": "tool_duo_pair",
    "copy": {
        "en": {
            "title": "Cover Screen Wallpaper Preview | Foldable Cover & Inner Screen Pair",
            "description": (
                "Cover screen wallpaper preview: see two images on a foldable phone's cover "
                "screen and inner screen side by side. Runs in your browser; images are not uploaded."
            ),
            "tools": "Tools",
            "heading": "Foldable wallpaper pair preview",
            "lead": "See a cover-screen image and an inner-screen image together before you set them.",
            "answer": [
                "This cover screen wallpaper preview puts a tall cover-screen image and a wide "
                "inner-screen image side by side in your browser, so you can check both before you set them.",
                "Foldable Wallpaper Studio makes wallpapers in pairs: a close-up for the cover screen "
                "and the full scene for the inner screen, cut from the same original artwork.",
            ],
            "sizes_title": "Screen sizes Foldable Wallpaper Studio saves",
            "sizes_head": ["Screen", "Pixels (width x height)"],
            "sizes_source": "Source: Foldable Wallpaper Studio App Store description",
            "privacy": "Images are not uploaded; only download-button clicks are counted",
            "scope": "Preview only; proportions are approximate",
            "outer_label": "Cover screen image (closed)",
            "inner_label": "Inner screen image (open)",
            "one_help": "Choose only one image and it fills both screens.",
            "samples": "Or try a sample pair",
            "sample_names": ["Summer railway", "Glacier aurora", "Clay puppy"],
            "outer_title": "Cover screen",
            "inner_title": "Inner screen",
            "zoom": "Cover screen zoom",
            "pos_x": "Cover screen horizontal position",
            "pos_y": "Cover screen vertical position",
            "inner_x": "Inner screen horizontal position",
            "swap": "Swap images",
            "status_empty": "Choose an image or a sample pair.",
            "status_ok": "Preview updated.",
            "status_bad": "This file could not be opened as an image.",
            "how_title": "How to use it",
            "how": [
                "A cover screen is tall and narrow; an inner screen is wide, so one photo rarely fits both.",
                "A close-up usually works on the cover screen, and the whole scene on the inner screen.",
                "Move and zoom each screen until the subject stays clear of the clock and the fold line.",
            ],
            "app_title": "Made-for-foldable wallpaper pairs",
            "app_text": (
                "Foldable Wallpaper Studio makes wallpapers in pairs: a close-up for the "
                "cover screen and the full scene for the inner screen, cut from the same "
                "original artwork, with closed and open previews before you save."
            ),
            "app_cta": "View Foldable Wallpaper Studio on the App Store",
            "credit": "Sample pairs: Foldable Wallpaper Studio press pack.",
            "index_title": "Foldable Wallpaper Pair Preview",
            "index_description": "Preview a cover-screen and inner-screen wallpaper pair in your browser.",
        },
        "zh-Hant": {
            "title": "外螢幕桌布預覽｜摺疊手機外螢幕＋內螢幕配對",
            "description": "外螢幕桌布預覽：把兩張圖片同時放到摺疊手機的外螢幕與內螢幕上。在瀏覽器裡處理，圖片不會上傳。",
            "tools": "工具",
            "heading": "摺疊手機雙螢幕桌布配對預覽",
            "lead": "設定之前，先看外螢幕和內螢幕兩張桌布放在一起的樣子。",
            "answer": [
                "這個外螢幕桌布預覽把瘦長的外螢幕圖和偏寬的內螢幕圖並排放在瀏覽器裡，設定前兩邊都能先確認。",
                "「摺疊手機桌布 - 雙螢幕成對桌布」的桌布成對製作：合上，外螢幕是特寫；展開，內螢幕是整片全景，兩張出自同一幅原創畫面。",
            ],
            "sizes_title": "摺疊手機桌布儲存的螢幕尺寸",
            "sizes_head": ["螢幕", "像素（寬 x 高）"],
            "sizes_source": "出處：摺疊手機桌布 App Store 商店說明",
            "privacy": "圖片不會上傳；只計算下載鈕點擊次數",
            "scope": "僅供預覽；比例為近似值",
            "outer_label": "外螢幕圖片（闔上時）",
            "inner_label": "內螢幕圖片（打開時）",
            "one_help": "只選一張圖片時，兩個螢幕都會用這張。",
            "samples": "或試試範例配對",
            "sample_names": ["夏日鐵道", "冰河極光", "黏土小狗"],
            "outer_title": "外螢幕",
            "inner_title": "內螢幕",
            "zoom": "外螢幕縮放",
            "pos_x": "外螢幕水平位置",
            "pos_y": "外螢幕垂直位置",
            "inner_x": "內螢幕水平位置",
            "swap": "交換兩張圖",
            "status_empty": "請選擇圖片或範例配對。",
            "status_ok": "預覽已更新。",
            "status_bad": "這個檔案無法當成圖片開啟。",
            "how_title": "使用方式",
            "how": [
                "外螢幕又高又窄、內螢幕偏寬，同一張照片很難兩邊都剛好。",
                "外螢幕通常適合放特寫，內螢幕放完整場景。",
                "分別移動、縮放，讓主角避開時鐘與摺痕。",
            ],
            "app_title": "為摺疊手機成對設計的桌布",
            "app_text": "「摺疊手機桌布 - 雙螢幕成對桌布」的桌布成對製作：外螢幕放特寫、內螢幕放完整場景，取自同一張原創作品，儲存前可先看闔上與打開的預覽。",
            "app_cta": "到 App Store 查看摺疊手機桌布",
            "credit": "範例配對：Foldable Wallpaper Studio 媒體素材包。",
            "index_title": "摺疊手機雙螢幕桌布配對預覽",
            "index_description": "在瀏覽器裡預覽外螢幕與內螢幕的桌布配對。",
        },
        "ja": {
            "title": "外画面 壁紙プレビュー｜折りたたみスマホのカバー画面とメイン画面",
            "description": "外画面の壁紙プレビュー：2枚の画像を折りたたみスマホのカバー画面とメイン画面に並べて確認。ブラウザ内で処理し、画像はアップロードされません。",
            "tools": "ツール",
            "heading": "折りたたみスマホ 壁紙ペアプレビュー",
            "lead": "設定する前に、カバー画面とメイン画面の壁紙を並べて確認できます。",
            "answer": [
                "この外画面の壁紙プレビューでは、縦長のカバー画面の画像と横長のメイン画面の画像をブラウザ内で並べ、設定前に両方を確認できます。",
                "「折りたたみ壁紙 - 外画面と内画面」の壁紙はペアで作られ、閉じれば外画面にクローズアップ、開けば内画面に全景。2枚は同じオリジナル作品から切り出しています。",
            ],
            "sizes_title": "「折りたたみ壁紙」が保存する画面サイズ",
            "sizes_head": ["画面", "ピクセル（幅 x 高さ）"],
            "sizes_source": "出典：「折りたたみ壁紙」App Store の説明",
            "privacy": "画像はアップロードされません。ダウンロードボタンのクリック数だけを数えます",
            "scope": "プレビュー専用・比率は目安です",
            "outer_label": "カバー画面の画像（閉じたとき）",
            "inner_label": "メイン画面の画像（開いたとき）",
            "one_help": "1枚だけ選ぶと、両方の画面に同じ画像を使います。",
            "samples": "サンプルのペアで試す",
            "sample_names": ["夏の線路", "氷河とオーロラ", "ねんどの子犬"],
            "outer_title": "カバー画面",
            "inner_title": "メイン画面",
            "zoom": "カバー画面のズーム",
            "pos_x": "カバー画面の左右位置",
            "pos_y": "カバー画面の上下位置",
            "inner_x": "メイン画面の左右位置",
            "swap": "画像を入れ替える",
            "status_empty": "画像かサンプルのペアを選んでください。",
            "status_ok": "プレビューを更新しました。",
            "status_bad": "このファイルは画像として開けませんでした。",
            "how_title": "使い方",
            "how": [
                "カバー画面は縦長、メイン画面は横長なので、1枚の写真で両方を合わせるのは難しいです。",
                "カバー画面にはアップ、メイン画面には全体の景色が向いています。",
                "時計や折り目に主役がかからないよう、画面ごとに位置とズームを調整します。",
            ],
            "app_title": "折りたたみ用にペアで作られた壁紙",
            "app_text": "「折りたたみ壁紙 - 外画面と内画面」の壁紙はペアで作られています。カバー画面にはアップ、メイン画面には全体の景色を、同じオリジナル作品から切り出し、保存前に閉じた状態と開いた状態をプレビューできます。",
            "app_cta": "App Store で「折りたたみ壁紙」を見る",
            "credit": "サンプル：Foldable Wallpaper Studio プレスキット。",
            "index_title": "折りたたみスマホ 壁紙ペアプレビュー",
            "index_description": "カバー画面とメイン画面の壁紙ペアをブラウザでプレビュー。",
        },
    },
}

PASSPORT = {
    "slug": "passport-photo-crop",
    "app": "snapport",
    "campaign": "tool_passport_crop",
    "copy": {
        "en": {
            "title": "Passport Photo Crop Tool | US 2x2 in, Taiwan & Japan 35x45 mm",
            "description": (
                "Crop a photo to US 2x2 inch or Taiwan / Japan 35x45 mm passport size "
                "and save a 300 DPI JPEG. Processed in your browser; photos are not uploaded."
            ),
            "tools": "Tools",
            "heading": "Passport photo crop tool",
            "lead": "Crop to the final print size with head-height guides, then save a JPEG.",
            "answer": [
                "This tool crops a photo you already have to U.S. 2 x 2 inch or Taiwan / Japan "
                "35 x 45 mm passport size with head-height guides and saves a 300 DPI JPEG, all in "
                "your browser; photos are not uploaded.",
                "For more countries and documents, Snapport on iPhone gives you photo size templates "
                "for passport, visa, ID card, student ID, resume, and work-badge photos in many regions.",
            ],
            "privacy": "Photos are not uploaded; only download-button clicks are counted",
            "sizes_title": "Official passport photo sizes",
            "sizes_head": ["Country", "Photo size", "Head height (chin to top of head)", "Official source"],
            "size_rows": {
                "us": ["United States", "2 x 2 in (51 x 51 mm)", "1 to 1 3/8 in (25 to 35 mm)"],
                "tw": ["Taiwan", "35 x 45 mm", "32 to 36 mm"],
                "jp": ["Japan", "35 x 45 mm", "32 to 36 mm (34 mm, plus or minus 2 mm)"],
            },
            "faq_title": "Common questions",
            "faq": [
                ("Can you wear glasses in a passport photo?",
                 "Not for a U.S. passport: glasses are not allowed unless you cannot remove them "
                 "for medical reasons, in which case a signed statement from your doctor is needed."),
                ("Can you smile in a passport photo?",
                 "Yes, within limits: face the camera directly with both eyes open and a neutral "
                 "expression or a natural smile."),
                ("Why do passport photos get rejected?",
                 "Usually because one rule is broken: the wrong photo or head size, shadows or a "
                 "patterned background, glasses, a blurry, grainy or out-of-date photo (it must be "
                 "taken in the last 6 months), a selfie, or any filter or digital edit."),
            ],
            "faq_source": "Source: U.S. Department of State, passport photo requirements (rules as recorded on "
            + FAQ_SOURCE_NOTE_DATE + "). Check the official page before you apply.",
            "scope": "Prepares the photo only; the passport is issued by the authority",
            "photo_label": "Photo",
            "preset_label": "Size",
            "presets": {
                "us": "United States: 2 x 2 in (51 x 51 mm)",
                "tw": "Taiwan: 35 x 45 mm",
                "jp": "Japan: 35 x 45 mm",
            },
            "zoom": "Zoom",
            "pos_x": "Horizontal position",
            "pos_y": "Vertical position",
            "guides": "Show head-height guides",
            "download": "Save JPEG",
            "status_empty": "Choose a photo to start.",
            "status_ok": "Line up the top of the head with the upper line and the chin between the lower lines.",
            "status_bad": "This file could not be opened as an image.",
            "status_saved": "JPEG saved to your device.",
            "drag_help": "You can also drag the photo inside the frame.",
            "rules_title": "Before you print",
            "rules": [
                "Use a recent photo with a plain light background, even lighting and a neutral expression.",
                "The guides show the head-height range for the chosen size; they are not an acceptance check.",
                "Requirements change; confirm the current rules on the official website before you apply.",
            ],
            "disclaimer": (
                "This tool only prepares the photo. Passports and other documents are "
                "issued by the relevant government authority, which decides whether a photo is accepted."
            ),
            "sources": "Official requirements",
            "source_labels": ["U.S. Department of State: passport photos", "Taiwan Bureau of Consular Affairs", "Japan Ministry of Foreign Affairs: passports"],
            "app_title": "Prepare passport photos on iPhone",
            "app_text": (
                "Snapport offers size templates for many regions, face-alignment guides, "
                "background tools and print-ready layouts, processed on your iPhone. "
                "It prepares the photo only; the document is issued by the relevant authority."
            ),
            "app_cta": "View Snapport on the App Store",
            "related": "Passport photo size guide",
            "index_title": "Passport Photo Crop Tool",
            "index_description": "Crop a local photo to US 2x2 in or 35x45 mm and save a 300 DPI JPEG.",
        },
        "zh-Hant": {
            "title": "護照照片裁切工具｜台灣、日本 35x45 公釐、美國 2x2 英吋",
            "description": "把照片裁成台灣或日本 35x45 公釐、美國 2x2 英吋的護照尺寸，存成 300 DPI 的 JPEG。在瀏覽器裡處理，照片不會上傳。",
            "tools": "工具",
            "heading": "護照照片裁切工具",
            "lead": "依最終列印尺寸裁切，搭配頭部高度參考線，再存成 JPEG。",
            "answer": [
                "這個工具把你手上的照片裁成台灣或日本 35x45 公釐、美國 2x2 英吋的護照尺寸，搭配頭部高度參考線，存成 300 DPI 的 JPEG，全部在瀏覽器裡處理，照片不會上傳。",
                "需要更多國家與證件時，iPhone 上的 Snapport 提供多地區常用的護照、簽證、證件、學生證、履歷與工作證照片尺寸範本。",
            ],
            "privacy": "照片不會上傳；只計算下載鈕點擊次數",
            "sizes_title": "官方護照照片尺寸",
            "sizes_head": ["國家", "照片尺寸", "頭部高度（下巴到頭頂）", "官方出處"],
            "size_rows": {
                "us": ["美國", "2 x 2 英吋（51 x 51 公釐）", "1 至 1 3/8 英吋（25 至 35 公釐）"],
                "tw": ["台灣", "35 x 45 公釐", "3.2 至 3.6 公分"],
                "jp": ["日本", "35 x 45 公釐", "32 至 36 公釐（34 公釐 ±2 公釐）"],
            },
            "scope": "只準備照片；證件由主管機關核發",
            "photo_label": "照片",
            "preset_label": "尺寸",
            "presets": {
                "us": "美國：2 x 2 英吋（51 x 51 公釐）",
                "tw": "台灣：35 x 45 公釐",
                "jp": "日本：35 x 45 公釐",
            },
            "zoom": "縮放",
            "pos_x": "水平位置",
            "pos_y": "垂直位置",
            "guides": "顯示頭部高度參考線",
            "download": "儲存 JPEG",
            "status_empty": "請先選擇照片。",
            "status_ok": "頭頂對齊上方的線，下巴落在下方兩條線之間。",
            "status_bad": "這個檔案無法當成圖片開啟。",
            "status_saved": "JPEG 已存到你的裝置。",
            "drag_help": "也可以直接在框內拖曳照片。",
            "rules_title": "列印之前",
            "rules": [
                "使用近期拍攝、素色淺底、光線均勻、表情自然的照片。",
                "參考線只標出所選尺寸的頭部高度範圍，不代表一定會被接受。",
                "規定可能更新，申請前請到官方網站確認最新規定。",
            ],
            "disclaimer": "本工具只協助準備照片；護照等證件由主管機關核發，照片是否合格由主管機關認定。",
            "sources": "官方規定",
            "source_labels": ["美國國務院：護照照片", "中華民國外交部領事事務局", "日本外務省：護照"],
            "app_title": "在 iPhone 上準備證件照",
            "app_text": "Snapport 提供多個地區的尺寸範本、臉部對齊參考線、背景工具與可直接列印的排版，全部在 iPhone 上處理。它只準備照片，證件由主管機關核發。",
            "app_cta": "到 App Store 查看 Snapport",
            "related": "護照照片尺寸指南",
            "index_title": "護照照片裁切工具",
            "index_description": "把照片裁成 35x45 公釐或美國 2x2 英吋，存成 300 DPI JPEG。",
        },
        "ja": {
            "title": "パスポート写真 トリミングツール｜35x45mm・米国 2x2インチ",
            "description": "写真を日本・台湾の 35x45mm や米国の 2x2 インチのパスポートサイズに切り抜き、300 DPI の JPEG で保存。ブラウザ内で処理し、写真はアップロードしません。",
            "tools": "ツール",
            "heading": "パスポート写真 トリミングツール",
            "lead": "仕上がりサイズに合わせて頭の高さのガイド付きで切り抜き、JPEG で保存します。",
            "answer": [
                "このツールは手元の写真を日本・台湾の 35x45mm や米国の 2x2 インチのパスポートサイズに、頭の高さのガイド付きで切り抜き、300 DPI の JPEG で保存します。すべてブラウザ内で処理し、写真はアップロードされません。",
                "ほかの国や書類には、iPhone の Snapport が多くの地域に対応したパスポート・ビザ・身分証・学生証・履歴書・社員証用の写真サイズテンプレートを備えています。",
            ],
            "privacy": "写真はアップロードされません。ダウンロードボタンのクリック数だけを数えます",
            "sizes_title": "公式のパスポート写真サイズ",
            "sizes_head": ["国・地域", "写真のサイズ", "顔の縦の長さ（あごから頭頂）", "公式の出典"],
            "size_rows": {
                "jp": ["日本", "縦 45 x 横 35 mm", "34 mm ±2 mm（32〜36 mm）"],
                "tw": ["台湾", "縦 45 x 横 35 mm", "32〜36 mm"],
                "us": ["米国", "2 x 2 インチ（51 x 51 mm）", "1〜1 3/8 インチ（25〜35 mm）"],
            },
            "scope": "写真の準備のみ。旅券は発給機関が交付します",
            "photo_label": "写真",
            "preset_label": "サイズ",
            "presets": {
                "jp": "日本：35 x 45 mm",
                "tw": "台湾：35 x 45 mm",
                "us": "米国：2 x 2 インチ（51 x 51 mm）",
            },
            "zoom": "ズーム",
            "pos_x": "左右の位置",
            "pos_y": "上下の位置",
            "guides": "頭の高さのガイドを表示",
            "download": "JPEG を保存",
            "status_empty": "写真を選んでください。",
            "status_ok": "頭頂を上の線に合わせ、あごを下の2本の線の間に置いてください。",
            "status_bad": "このファイルは画像として開けませんでした。",
            "status_saved": "JPEG を端末に保存しました。",
            "drag_help": "枠の中で写真をドラッグして動かすこともできます。",
            "rules_title": "印刷する前に",
            "rules": [
                "最近撮影した、無地の明るい背景・均一な光・無表情の写真を使ってください。",
                "ガイドは選んだサイズの頭の高さの範囲を示すもので、受理を保証するものではありません。",
                "規格は変わることがあります。申請前に公式サイトで最新の規格を確認してください。",
            ],
            "disclaimer": "このツールは写真の準備だけを行います。旅券などの証明書は発給機関が交付し、写真が受理されるかどうかも発給機関が判断します。",
            "sources": "公式の規格",
            "source_labels": ["米国国務省：パスポート写真", "台湾 外交部領事事務局", "外務省：パスポート"],
            "app_title": "iPhone で証明写真を準備",
            "app_text": "Snapport は多くの地域のサイズテンプレート、顔の位置合わせガイド、背景ツール、印刷用レイアウトを備え、すべて iPhone 上で処理します。写真の準備のみを行い、証明書は発給機関が交付します。",
            "app_cta": "App Store で Snapport を見る",
            "related": "パスポート写真サイズガイド",
            "index_title": "パスポート写真 トリミングツール",
            "index_description": "写真を 35x45mm や 2x2 インチに切り抜き、300 DPI の JPEG で保存。",
        },
    },
}

TOOLS = (DUO, PASSPORT)

STYLE = r"""
:root{--ink:#171b24;--muted:#5d6574;--line:#dce1eb;--bg:#eef3f8;--navy:#18365f;--blue:#2d6da3;--mint:#dff4ec;--warn:#fff4d8}
*{box-sizing:border-box}body{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Hiragino Sans","Noto Sans TC","Noto Sans JP",sans-serif;background:var(--bg);color:var(--ink);line-height:1.6}
a{color:#18558b}.wrap{width:min(1120px,100% - 32px);margin:auto}.top{background:#fff;border-bottom:1px solid var(--line)}
.nav{min-height:58px;display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap}.nav a{text-decoration:none;font-weight:800}.nav-links{display:flex;gap:14px;flex-wrap:wrap}.nav-links a{color:var(--muted);font-size:14px}
.hero{padding:36px 0 10px}h1{font-size:clamp(28px,5vw,46px);line-height:1.12;margin:.2em 0}.lead{color:var(--muted);font-size:18px;margin:0}.trust{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}.badge{border:1px solid var(--line);background:#fff;border-radius:999px;padding:6px 12px;font-size:13px;font-weight:800;color:var(--navy)}.badge.scope{background:#fff9ea;color:#684c1d}
.card{background:#fff;border:1px solid var(--line);border-radius:22px;padding:clamp(16px,3vw,28px);margin:18px auto}.card h2{margin:0 0 10px;font-size:clamp(20px,3vw,28px)}
.grid{display:grid;grid-template-columns:minmax(240px,340px) minmax(0,1fr);gap:22px}.controls{display:grid;gap:12px;align-content:start}.field{border:1px solid var(--line);background:#f8fafc;border-radius:16px;padding:12px}.field label{display:block;color:var(--navy);font-size:13px;font-weight:800;margin-bottom:6px}
input,select,button{font:inherit}input[type=file],select{width:100%;min-height:44px;border:1px solid #cbd3df;border-radius:12px;background:#fff;padding:8px 10px}input[type=range]{width:100%;accent-color:var(--blue)}
.help,.status{color:var(--muted);font-size:13px;margin:6px 0 0}.status{min-height:1.5em}.button{border:0;border-radius:999px;background:var(--navy);color:#fff;text-decoration:none;font-weight:800;padding:10px 16px;cursor:pointer;display:inline-flex}.button.secondary{background:#fff;color:var(--navy);border:1px solid var(--line)}.button:disabled{opacity:.45;cursor:not-allowed}.row{display:flex;flex-wrap:wrap;gap:8px}
.stage{display:flex;flex-wrap:wrap;gap:22px;align-items:flex-end;justify-content:center;padding:18px;border-radius:18px;background:#1d2330;min-height:320px}.device{display:grid;gap:8px;justify-items:center;color:#d8deea;font-size:13px;font-weight:700}.device canvas{display:block;border:8px solid #0b0d12;border-radius:26px;background:#2a3140;box-shadow:0 10px 30px rgba(0,0,0,.35);max-width:100%;height:auto}.device.outer canvas{width:150px}.device.inner canvas{width:min(420px,72vw);border-radius:22px}
.crop-shell{position:relative;display:inline-block;touch-action:none;cursor:grab;background:repeating-linear-gradient(45deg,#e7ebf0,#e7ebf0 10px,#f3f5f8 10px,#f3f5f8 20px);padding:12px;border-radius:16px}.crop-shell canvas{display:block;max-width:100%;height:auto;box-shadow:0 6px 20px rgba(20,34,52,.2)}#guide{position:absolute;left:12px;top:12px;pointer-events:none}
.tbl{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:15px}th,td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}th{background:#f3f6fa}
.note{background:var(--warn);border-color:#ead49d}.cta{background:linear-gradient(135deg,#f9fbff,#e8f1f8)}ul{padding-left:20px}li{margin:6px 0}
@media(max-width:780px){.grid{grid-template-columns:1fr}}
"""


def page_path(slug: str, locale: str) -> Path:
    prefix = Path() if locale == "en" else Path(locale)
    return prefix / "tools" / f"{slug}.html"


def canonical(slug: str, locale: str) -> str:
    return f"{SITE}/{page_path(slug, locale).as_posix()}"


def campaign(tool: dict, locale: str, suffix: str = "") -> str:
    token = f"{tool['campaign']}_{locale.replace('-', '_').lower()}{suffix}"
    if token not in APP_BOUND_CAMPAIGNS:
        raise ValueError(f"campaign {token} is not app-bound in gen_store_attribution")
    return token


def store_link(tool: dict, locale: str, suffix: str = "") -> str:
    """The final App Store CTA: storefront aligned, app-bound campaign kept."""
    token = campaign(tool, locale, suffix)
    raw = appstore_url(tool["app"], token)
    provider = os.environ.get("APP_STORE_PROVIDER_TOKEN", "").strip()
    if not provider:
        return raw
    app_id = APPSTORE[tool["app"]]
    final = final_store_url(
        raw, token, provider, locale=STAMP_LOCALE[locale], app_id=app_id
    )
    return final or ""


def json_script(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/ld+json">{payload}</script>'


def js_value(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")


def _e(value: str) -> str:
    return html.escape(value, quote=True)


def _head(tool: dict, locale: str) -> str:
    t = tool["copy"][locale]
    slug = tool["slug"]
    url = canonical(slug, locale)
    alternates = "".join(
        f'<link rel="alternate" hreflang="{code}" href="{canonical(slug, code)}">\n'
        for code in LOCALES
    )
    home_prefix = "" if locale == "en" else f"{locale}/"
    schema = {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": t["heading"],
        "description": t["description"],
        "url": url,
        "inLanguage": locale,
        "datePublished": CONTENT_DATE,
        "applicationCategory": "MultimediaApplication",
        "operatingSystem": "Any",
        "browserRequirements": "JavaScript and local image decoding; no upload is used",
    }
    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "iOS App Guide",
             "item": f"{SITE}/{home_prefix}index.html"},
            {"@type": "ListItem", "position": 2, "name": t["tools"],
             "item": f"{SITE}/{home_prefix}tools/index.html"},
            {"@type": "ListItem", "position": 3, "name": t["heading"], "item": url},
        ],
    }
    faq_schema = ""
    if t.get("faq"):
        faq_schema = json_script({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": q,
                 "acceptedAnswer": {"@type": "Answer", "text": a}}
                for q, a in t["faq"]
            ],
        }) + "\n"
    opening = " ".join(t["answer"]) if t.get("answer") else t["lead"]
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
{faq_schema}{click_beacon_block()}
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{SITE}/{home_prefix}index.html">iOS App Guide</a><nav class="nav-links"><a href="{SITE}/{home_prefix}tools/index.html">{_e(t["tools"])}</a>{_language_links(slug, locale)}</nav></div></header>
<main>
<section class="hero wrap"><h1>{_e(t["heading"])}</h1><p class="lead">{_e(opening)}</p><div class="trust"><span class="badge">{_e(t["privacy"])}</span><span class="badge scope">{_e(t["scope"])}</span></div></section>
"""


LANGUAGE_NAMES = {"en": "English", "zh-Hant": "繁體中文", "ja": "日本語"}


def _language_links(slug: str, locale: str) -> str:
    return "".join(
        f'<a href="{canonical(slug, code)}" hreflang="{code}" lang="{code}">{LANGUAGE_NAMES[code]}</a>'
        for code in LOCALES
        if code != locale
    )


def _cta(tool: dict, locale: str, show_cta: bool) -> str:
    if not show_cta:
        return ""
    link = store_link(tool, locale)
    if not link:
        return ""
    t = tool["copy"][locale]
    return (
        f'<section class="card cta wrap"><h2>{_e(t["app_title"])}</h2>'
        f'<p>{_e(t["app_text"])}</p><p><a class="button" href="{_e(link)}" '
        f'rel="noopener">{_e(t["app_cta"])}</a></p></section>\n'
    )


# Page-top download button (DUO only).  It sits in its own managed block so
# android_play.inject_html (here and in the deploy pass) keeps adding its Play
# link to the result CTA below, exactly as before; the block carries its own
# Play link with the _top referrer.
TOP_CTA_SUFFIX = "_top"
TOP_CTA_BLOCK = "tool-top-cta"


def _top_cta(tool: dict, locale: str, show_cta: bool, android_apps: dict | None) -> str:
    if not show_cta:
        return ""
    link = store_link(tool, locale, TOP_CTA_SUFFIX)
    if not link:
        return ""
    t = tool["copy"][locale]
    play = ""
    entry = (android_apps or {}).get(tool["app"])
    if entry:
        url = android_play.tracked_play_url(
            entry["play_url"], campaign(tool, locale, TOP_CTA_SUFFIX), tool["app"]
        )
        label = (f"Get {android_play.display_name(tool['app'], entry)} on Google Play"
                 if locale == "en" else "Google Play")
        play = f'<p class="help">Android: <a href="{_e(url)}" rel="noopener">{_e(label)}</a></p>'
    return (
        f'<!-- {TOP_CTA_BLOCK}:start --><section class="card cta wrap" id="get-app">'
        f'<p><a class="button" href="{_e(link)}" rel="noopener">{_e(t["app_cta"])}</a></p>'
        f'{play}</section><!-- {TOP_CTA_BLOCK}:end -->\n'
    )


def _table(head: list[str], rows: list[list[str]]) -> str:
    header = "".join(f"<th>{_e(cell)}</th>" for cell in head)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f'<div class="tbl"><table><tr>{header}</tr>{body}</table></div>'


def _duo_sizes(locale: str) -> str:
    t = DUO["copy"][locale]
    names = (t["outer_title"], t["inner_title"])
    rows = [[_e(name), f"{w} x {h}"] for name, (w, h) in zip(names, DUO_SCREENS.values(), strict=True)]
    # Plain text: the page keeps only its tracked App Store CTAs.
    source = _e(t["sizes_source"])
    return (f'<section class="card wrap" id="sizes"><h2>{_e(t["sizes_title"])}</h2>'
            f'{_table(t["sizes_head"], rows)}<p class="help">{source}</p></section>\n')


def _passport_sizes(locale: str) -> str:
    t = PASSPORT["copy"][locale]
    rows = []
    for key, cells in t["size_rows"].items():
        url = PASSPORT_SIZE_SOURCES[key]
        rows.append([_e(cell) for cell in cells]
                    + [f'<a href="{url}" rel="noopener noreferrer">{_e(urlparse_host(url))}</a>'])
    return (f'<section class="card wrap" id="sizes"><h2>{_e(t["sizes_title"])}</h2>'
            f'{_table(t["sizes_head"], rows)}</section>\n')


def _passport_faq(locale: str) -> str:
    t = PASSPORT["copy"][locale]
    if not t.get("faq"):
        return ""
    items = "".join(f"<h3>{_e(q)}</h3><p>{_e(a)}</p>" for q, a in t["faq"])
    return (f'<section class="card wrap" id="faq"><h2>{_e(t["faq_title"])}</h2>{items}'
            f'<p class="help"><a href="{US_SOURCE}" rel="noopener noreferrer">{_e(t["faq_source"])}</a></p></section>\n')


def urlparse_host(url: str) -> str:
    return url.split("//", 1)[1].split("/", 1)[0]


def render_duo(locale: str, show_cta: bool, android_apps: dict | None = None) -> str:
    t = DUO["copy"][locale]
    depth = "../" if locale == "en" else "../../"
    samples = [
        {
            "name": name,
            "outer": f"{depth}{SAMPLE_DIR}/{key}-outer.jpg",
            "inner": f"{depth}{SAMPLE_DIR}/{key}-inner.jpg",
        }
        for key, name in zip(SAMPLES, t["sample_names"], strict=True)
    ]
    sample_buttons = "".join(
        f'<button class="button secondary" type="button" data-sample="{index}">{_e(item["name"])}</button>'
        for index, item in enumerate(samples)
    )
    how = "".join(f"<li>{_e(item)}</li>" for item in t["how"])
    copy = {key: t[key] for key in ("status_empty", "status_ok", "status_bad")}
    return _head(DUO, locale) + _top_cta(DUO, locale, show_cta, android_apps) + f"""<section class="card wrap" id="tool"><div class="grid"><div class="controls">
<div class="field"><label for="outer-file">{_e(t["outer_label"])}</label><input id="outer-file" type="file" accept="image/*"></div>
<div class="field"><label for="inner-file">{_e(t["inner_label"])}</label><input id="inner-file" type="file" accept="image/*"><p class="help">{_e(t["one_help"])}</p></div>
<div class="field"><label>{_e(t["samples"])}</label><div class="row">{sample_buttons}</div></div>
<div class="field"><label for="zoom">{_e(t["zoom"])}</label><input id="zoom" type="range" min="100" max="300" value="100"><label for="pos-x">{_e(t["pos_x"])}</label><input id="pos-x" type="range" min="0" max="100" value="50"><label for="pos-y">{_e(t["pos_y"])}</label><input id="pos-y" type="range" min="0" max="100" value="50"><label for="inner-x">{_e(t["inner_x"])}</label><input id="inner-x" type="range" min="0" max="100" value="50"></div>
<div class="row"><button class="button secondary" id="swap" type="button">{_e(t["swap"])}</button></div>
<p class="status" id="status" aria-live="polite">{_e(t["status_empty"])}</p>
</div><div class="stage" aria-label="{_e(t["heading"])}"><div class="device outer"><canvas id="outer" width="{DUO_SCREENS["outer"][0] // 3}" height="{DUO_SCREENS["outer"][1] // 3}"></canvas><span>{_e(t["outer_title"])}</span></div><div class="device inner"><canvas id="inner" width="{DUO_SCREENS["inner"][0] // 3}" height="{DUO_SCREENS["inner"][1] // 3}"></canvas><span>{_e(t["inner_title"])}</span></div></div></div></section>
<section class="card wrap"><h2>{_e(t["how_title"])}</h2><ul>{how}</ul><p class="help">{_e(t["credit"])}</p></section>
{_duo_sizes(locale)}{_cta(DUO, locale, show_cta)}</main>
<script>
const COPY={js_value(copy)};
const SAMPLES={js_value(samples)};
const state={{outer:null,inner:null}};
const $=id=>document.getElementById(id);
const status=$("status");
function load(src){{return new Promise((resolve,reject)=>{{const image=new Image();image.onload=()=>resolve(image);image.onerror=reject;image.src=src;}});}}
async function fromFile(file){{const url=URL.createObjectURL(file);try{{return await load(url);}}finally{{setTimeout(()=>URL.revokeObjectURL(url),0);}}}}
function cover(canvas,image,zoom,fx,fy){{const ctx=canvas.getContext("2d");ctx.fillStyle="#2a3140";ctx.fillRect(0,0,canvas.width,canvas.height);if(!image)return;const scale=Math.max(canvas.width/image.naturalWidth,canvas.height/image.naturalHeight)*zoom;const w=image.naturalWidth*scale,h=image.naturalHeight*scale;ctx.imageSmoothingQuality="high";ctx.drawImage(image,(canvas.width-w)*fx,(canvas.height-h)*fy,w,h);}}
function render(){{const outer=state.outer||state.inner,inner=state.inner||state.outer;cover($("outer"),outer,$("zoom").value/100,$("pos-x").value/100,$("pos-y").value/100);cover($("inner"),inner,1,$("inner-x").value/100,.5);status.textContent=outer?COPY.status_ok:COPY.status_empty;}}
async function pick(input,slot){{const file=input.files&&input.files[0];if(!file)return;try{{state[slot]=await fromFile(file);render();}}catch(error){{status.textContent=COPY.status_bad;}}}}
$("outer-file").addEventListener("change",event=>pick(event.target,"outer"));
$("inner-file").addEventListener("change",event=>pick(event.target,"inner"));
document.querySelectorAll("[data-sample]").forEach(button=>button.addEventListener("click",async()=>{{const item=SAMPLES[Number(button.dataset.sample)];try{{[state.outer,state.inner]=await Promise.all([load(item.outer),load(item.inner)]);render();}}catch(error){{status.textContent=COPY.status_bad;}}}}));
["zoom","pos-x","pos-y","inner-x"].forEach(id=>$(id).addEventListener("input",render));
$("swap").addEventListener("click",()=>{{[state.outer,state.inner]=[state.inner,state.outer];render();}});
render();
</script>
</body>
</html>
"""


def render_passport(locale: str, show_cta: bool) -> str:
    t = PASSPORT["copy"][locale]
    options = "".join(
        f'<option value="{key}">{_e(label)}</option>' for key, label in t["presets"].items()
    )
    rules = "".join(f"<li>{_e(item)}</li>" for item in t["rules"])
    sources = "".join(
        f'<li><a href="{url}" rel="noopener noreferrer">{_e(label)}</a></li>'
        for url, label in zip((US_SOURCE, TW_SOURCE, JP_SOURCE), t["source_labels"], strict=True)
    )
    copy = {
        key: t[key]
        for key in ("status_empty", "status_ok", "status_bad", "status_saved")
    }
    guide = f"{SITE}/{'' if locale == 'en' else locale + '/'}tools/passport-photo-size-guide.html"
    return _head(PASSPORT, locale) + f"""<section class="card wrap" id="tool"><div class="grid"><div class="controls">
<div class="field"><label for="photo">{_e(t["photo_label"])}</label><input id="photo" type="file" accept="image/*"><p class="help">{_e(t["drag_help"])}</p></div>
<div class="field"><label for="preset">{_e(t["preset_label"])}</label><select id="preset">{options}</select></div>
<div class="field"><label for="zoom">{_e(t["zoom"])}</label><input id="zoom" type="range" min="100" max="400" value="100"><label for="pos-x">{_e(t["pos_x"])}</label><input id="pos-x" type="range" min="0" max="100" value="50"><label for="pos-y">{_e(t["pos_y"])}</label><input id="pos-y" type="range" min="0" max="100" value="50"><label><input id="guides" type="checkbox" checked> {_e(t["guides"])}</label></div>
<div class="row"><button class="button" id="download" type="button" disabled>{_e(t["download"])}</button></div>
<p class="status" id="status" aria-live="polite">{_e(t["status_empty"])}</p>
</div><div><div class="crop-shell" id="shell"><canvas id="crop" width="413" height="531" aria-label="{_e(t["heading"])}"></canvas><canvas id="guide" width="413" height="531" aria-hidden="true"></canvas></div></div></div></section>
{_passport_sizes(locale)}{_passport_faq(locale)}<section class="card note wrap"><h2>{_e(t["rules_title"])}</h2><ul>{rules}</ul><p><strong>{_e(t["disclaimer"])}</strong></p><p><a href="{guide}">{_e(t["related"])}</a></p></section>
{_cta(PASSPORT, locale, show_cta)}<section class="card wrap"><h2>{_e(t["sources"])}</h2><ul>{sources}</ul></section>
</main>
<script>
const COPY={js_value(copy)};
const PRESETS={js_value(PASSPORT_PRESETS)};
const DPI=300,MM_PER_INCH=25.4;
const $=id=>document.getElementById(id);
const crop=$("crop"),guide=$("guide"),shell=$("shell"),status=$("status"),download=$("download");
let image=null,drag=null;
const px=mm=>Math.round(mm/MM_PER_INCH*DPI);
function preset(){{return PRESETS[$("preset").value];}}
function layout(){{const p=preset();const w=px(p.w),h=px(p.h);for(const canvas of [crop,guide]){{canvas.width=w;canvas.height=h;}}const shown=Math.min(w,420);for(const canvas of [crop,guide]){{canvas.style.width=shown+"px";}}}}
function geometry(){{const scale=Math.max(crop.width/image.naturalWidth,crop.height/image.naturalHeight)*$("zoom").value/100;const w=image.naturalWidth*scale,h=image.naturalHeight*scale;return{{w,h,x:(crop.width-w)*$("pos-x").value/100,y:(crop.height-h)*$("pos-y").value/100}};}}
function drawGuides(){{const ctx=guide.getContext("2d");ctx.clearRect(0,0,guide.width,guide.height);if(!$("guides").checked)return;const p=preset(),k=guide.height/p.h;ctx.setLineDash([8,6]);ctx.lineWidth=2;const line=(mm,color)=>{{ctx.strokeStyle=color;ctx.beginPath();ctx.moveTo(0,mm*k);ctx.lineTo(guide.width,mm*k);ctx.stroke();}};line(p.top,"#2d6da3");line(p.top+p.head_min,"#c0392b");line(p.top+p.head_max,"#c0392b");ctx.strokeStyle="rgba(45,109,163,.6)";ctx.beginPath();ctx.moveTo(guide.width/2,0);ctx.lineTo(guide.width/2,guide.height);ctx.stroke();}}
function render(){{const ctx=crop.getContext("2d");ctx.fillStyle="#fff";ctx.fillRect(0,0,crop.width,crop.height);if(image){{const g=geometry();ctx.imageSmoothingQuality="high";ctx.drawImage(image,g.x,g.y,g.w,g.h);}}drawGuides();download.disabled=!image;}}
function setDensity(bytes){{if(bytes[2]===0xFF&&bytes[3]===0xE0&&String.fromCharCode(...bytes.slice(6,10))==="JFIF"){{bytes[13]=1;bytes[14]=DPI>>8;bytes[15]=DPI&255;bytes[16]=DPI>>8;bytes[17]=DPI&255;}}return bytes;}}
$("photo").addEventListener("change",async event=>{{const file=event.target.files&&event.target.files[0];if(!file)return;const url=URL.createObjectURL(file);const next=new Image();next.onload=()=>{{image=next;URL.revokeObjectURL(url);render();status.textContent=COPY.status_ok;}};next.onerror=()=>{{URL.revokeObjectURL(url);status.textContent=COPY.status_bad;}};next.src=url;}});
$("preset").addEventListener("change",()=>{{layout();render();}});
["zoom","pos-x","pos-y","guides"].forEach(id=>$(id).addEventListener("input",render));
shell.addEventListener("pointerdown",event=>{{if(!image)return;drag={{x:event.clientX,y:event.clientY,px:+$("pos-x").value,py:+$("pos-y").value}};shell.setPointerCapture(event.pointerId);}});
shell.addEventListener("pointermove",event=>{{if(!drag||!image)return;const g=geometry(),ratio=crop.width/crop.getBoundingClientRect().width;const spanX=crop.width-g.w,spanY=crop.height-g.h;const clamp=v=>Math.max(0,Math.min(100,v));if(spanX)$("pos-x").value=clamp(drag.px+(event.clientX-drag.x)*ratio/spanX*100);if(spanY)$("pos-y").value=clamp(drag.py+(event.clientY-drag.y)*ratio/spanY*100);render();}});
shell.addEventListener("pointerup",()=>{{drag=null;}});
download.addEventListener("click",()=>{{if(!image)return;crop.toBlob(async blob=>{{const bytes=setDensity(new Uint8Array(await blob.arrayBuffer()));const p=preset();const link=document.createElement("a");link.href=URL.createObjectURL(new Blob([bytes],{{type:"image/jpeg"}}));link.download="passport-photo-"+$("preset").value+"-"+p.w+"x"+p.h+"mm.jpg";document.body.appendChild(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(link.href),1000);status.textContent=COPY.status_saved;}},"image/jpeg",0.95);}});
layout();render();
</script>
</body>
</html>
"""


RENDERERS = {DUO["slug"]: render_duo, PASSPORT["slug"]: render_passport}


_INLINE_SCRIPT_RE = re.compile(r"<script>(.*?)</script>", re.S)


def content_security_policy(page: str) -> str:
    """Only the page's own inline scripts (by hash) run; the only network call
    allowed is the shared download-click counter."""
    hashes = " ".join(
        "'sha256-" + base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode("ascii") + "'"
        for body in _INLINE_SCRIPT_RE.findall(page)
    )
    return (
        "default-src 'none'; "
        f"script-src {hashes}; "
        "style-src 'unsafe-inline'; "
        "img-src 'self' blob: data:; "
        f"connect-src {CLICK_BEACON_URL}; "
        "base-uri 'none'; form-action 'none'"
    )


def render_page(tool: dict, locale: str, show_cta: bool, android_apps: dict | None = None) -> str:
    renderer = RENDERERS[tool["slug"]]
    page = renderer(locale, show_cta, android_apps) if tool is DUO else renderer(locale, show_cta)
    if android_apps:
        page = android_play.inject_html(page, android_apps)
    return page.replace("{CSP_PLACEHOLDER}", content_security_policy(page), 1)


def _index_card(tool: dict, locale: str) -> str:
    t = tool["copy"][locale]
    return (
        f'<article class="card third"><h2><a href="{tool["slug"]}.html">'
        f'{html.escape(t["index_title"])}</a></h2>'
        f'<p>{html.escape(t["index_description"])}</p></article>'
    )


def update_index(index: Path, locale: str) -> bool:
    if not index.exists():
        return False
    text = index.read_text(encoding="utf-8")
    updated = text
    for tool in TOOLS:
        updated = re.sub(
            r'<article class="card third"><h2><a href="'
            + re.escape(f'{tool["slug"]}.html')
            + r'">.*?</article>',
            "",
            updated,
            flags=re.S,
        )
    marker = '<section class="wrap grid">'
    if marker not in updated:
        raise RuntimeError(f"{index} is missing its tools grid")
    cards = "".join(_index_card(tool, locale) for tool in TOOLS)
    updated = updated.replace(marker, marker + cards, 1)
    if updated == text:
        return False
    index.write_text(updated, encoding="utf-8")
    return True


def write_text_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def load_android_apps() -> dict:
    try:
        return android_play.load_snapshot()
    except (OSError, ValueError) as error:
        print(f"web_tools_pilot: Play snapshot ignored ({error})", file=sys.stderr)
        return {}


def build(pages: Path = PAGES, *, live_keys: set[str] | frozenset[str],
          android_apps: dict | None = None) -> list[str]:
    outputs = []
    for tool in TOOLS:
        show_cta = tool["app"] in live_keys
        for locale in LOCALES:
            write_text_if_changed(
                pages / page_path(tool["slug"], locale),
                render_page(tool, locale, show_cta, android_apps),
            )
            outputs.append(canonical(tool["slug"], locale))
    for locale in LOCALES:
        prefix = Path() if locale == "en" else Path(locale)
        update_index(pages / prefix / "tools" / "index.html", locale)
    return outputs


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    live_keys = set(live_app_keys(APPSTORE, str(PAGES), refresh=False))
    outputs = build(PAGES, live_keys=live_keys, android_apps=load_android_apps())
    for output in outputs:
        print(f"web tools pilot -> {output}")
    if "--no-sitemap" not in args:
        print(f"tools sitemap -> {write_tools_sitemap()} urls")


if __name__ == "__main__":
    main()
