#!/usr/bin/env python3
"""Generate a bilingual, private photo-storage cleanup planning tool."""

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

from appstore_live import live_app_keys  # noqa: E402
from gen_calculator import write_tools_sitemap  # noqa: E402
from gen_feed import feed_discovery_links  # noqa: E402
from videogen.registry import APPSTORE, appstore_url  # noqa: E402

PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", "https://alice51849.github.io/ios-app-guide"
).rstrip("/")
SLUG = "photo-storage-calculator"
APP_KEY = "picclear"
APP_ID = "6780223070"
CONTENT_DATE = "2026-07-15"
APPLE_STORAGE = "https://support.apple.com/en-us/108429"
APPLE_ICLOUD_PHOTOS = (
    "https://support.apple.com/guide/iphone/"
    "sync-photos-videos-icloud-iph961b96c4d/ios"
)
APPLE_DUPLICATES = (
    "https://support.apple.com/guide/iphone/"
    "merge-duplicate-photos-and-videos-iph1978d9c23/ios"
)
APPLE_DELETE_RECOVER = (
    "https://support.apple.com/guide/iphone/"
    "delete-or-hide-photos-and-videos-iphb4defbde9/ios"
)
WEBMCP_SOURCE = "https://developer.chrome.com/docs/ai/webmcp/imperative-api"

ICLOUD_STATUSES = (
    "unknown",
    "on-synced",
    "on-syncing-or-paused",
    "off",
)
PRIORITIES = ("general", "duplicates", "large-videos", "screenshots")

COPY = {
    "en": {
        "title": "Private iPhone Photo Storage Cleanup Planner | No Upload",
        "description": (
            "Calculate only the free-space gap from storage numbers you enter, then build "
            "a reversible photo-review plan without uploading, scanning or estimating your library."
        ),
        "tools": "Free tools",
        "switch": "繁體中文",
        "eyebrow": "Free · no photo access · no recovery estimate",
        "heading": "Private iPhone photo storage cleanup planner",
        "lead": (
            "Measure the gap between current and target free space. This page never guesses "
            "average file size, duplicate rate or how much a cleanup will recover."
        ),
        "badges": (
            "No photos, files or metadata",
            "No iCloud or device access",
            "No deletion or classification",
            "No recoverable-space prediction",
        ),
        "planner": "Calculate a known storage gap",
        "planner_intro": (
            "Copy numbers you can already see in Settings. Photos storage is reported separately "
            "and is never treated as deletable or recoverable."
        ),
        "current_label": "Current free space (GB)",
        "target_label": "Target free space (GB)",
        "photos_label": "Photos storage shown by iPhone (GB)",
        "icloud_label": "iCloud Photos status",
        "icloud_options": {
            "unknown": "Not checked",
            "on-synced": "On — sync appears complete",
            "on-syncing-or-paused": "On — syncing, paused or warning",
            "off": "Off",
        },
        "priority_label": "First review area",
        "priority_options": {
            "general": "General storage review",
            "duplicates": "Apple Duplicates collection",
            "large-videos": "Large videos",
            "screenshots": "Screenshots",
        },
        "copy_label": "I verified an independent copy of irreplaceable originals",
        "deleted_label": "I reviewed Recently Deleted",
        "update": "Update private plan",
        "invalid_input": "Enter all three storage numbers from 0 to 2,048 GB.",
        "result_gap": "Additional free-space gap",
        "result_current": "Current free space",
        "result_target": "Target free space",
        "result_photos": "Reported Photos storage",
        "result_status": "Target status",
        "met": "Target already met",
        "not_met": "Gap remains",
        "result_plan": "Reversible review plan",
        "gap_boundary": (
            "Gap formula: max(0, target free GB − current free GB). Values use the same GB "
            "unit you enter. The result is not a prediction of what Photos or PicClear can recover."
        ),
        "photos_boundary": (
            "Reported Photos storage is context only. Some items may be important, synced, "
            "optimized, shared, edited or already represented differently on device."
        ),
        "icloud_steps": {
            "unknown": (
                "Check Photos sync status before changing irreplaceable originals; if iCloud Photos "
                "is on, edits and deletions can sync across devices."
            ),
            "on-synced": (
                "Even when iCloud Photos appears synced, changes and deletions sync across devices. "
                "Treat sync as synchronization, not the only independent copy."
            ),
            "on-syncing-or-paused": (
                "Resolve the iCloud Photos syncing, paused or storage warning before destructive "
                "changes, and verify what has actually synced."
            ),
            "off": (
                "With iCloud Photos reported off, verify another independent copy of irreplaceable "
                "originals before destructive changes."
            ),
        },
        "priority_steps": {
            "general": (
                "Start with Settings > General > iPhone Storage recommendations, then review "
                "Apple's Duplicates collection, videos and screenshots in small groups."
            ),
            "duplicates": (
                "Open Photos > Collections > Utilities > Duplicates and review each merge; "
                "the collection may not appear when Photos has not found duplicates."
            ),
            "large-videos": (
                "Review videos individually for importance and whether an independent original "
                "can be opened; duration or category does not prove a video is disposable."
            ),
            "screenshots": (
                "Review the Screenshots collection in small groups and keep anything needed for "
                "records, authentication, travel, work or accessibility."
            ),
        },
        "copy_yes": (
            "Open a sample from the independent copy before permanent deletion; iCloud Photos "
            "sync alone is not treated here as an independent archive."
        ),
        "copy_no": (
            "Stop before permanent deletion and create a verifiable independent copy of "
            "irreplaceable originals; iCloud Photos changes can propagate."
        ),
        "deleted_yes": (
            "Recheck Recently Deleted before permanently removing anything; permanent removal "
            "ends the normal recovery window."
        ),
        "deleted_no": (
            "Review Recently Deleted. Apple says deleted items normally remain there for 30 days; "
            "do not empty it until you are sure and any essential originals are independently verified."
        ),
        "final_step": (
            "After one small reviewed batch, recheck iPhone Storage. Measure the actual change "
            "instead of assuming the calculated gap equals deletable content."
        ),
        "checklist_title": "Safety-first cleanup sequence",
        "checklist": (
            "Confirm current free space and Photos storage in Settings > General > iPhone Storage.",
            "Verify an independent, openable copy of irreplaceable originals before permanent deletion.",
            "Check iCloud Photos sync status and remember changes can propagate across devices.",
            "Review one category in a small batch; never treat a category as proof an item is disposable.",
            "Recheck Recently Deleted and device storage before deciding on another batch.",
        ),
        "scope_title": "What this planner cannot know",
        "scope_text": (
            "It cannot read your Photos library, storage, iCloud, albums, files, metadata, favorites, "
            "duplicates, blur, video sizes or deletion results. It never identifies anything as safe "
            "to delete and cannot predict recovered capacity."
        ),
        "sources_title": "Official Apple steps before any optional cleaner",
        "sources_intro": (
            "Apple documents iPhone Storage, iCloud Photos synchronization and optimization, "
            "the Duplicates collection, and the 30-day Recently Deleted window. Verify the current "
            "instructions for your iOS version."
        ),
        "source_labels": (
            "Apple: check storage on iPhone and iPad",
            "Apple: back up and sync photos and videos with iCloud",
            "Apple: merge duplicate photos and videos on iPhone",
            "Apple: delete, recover or permanently remove photos and videos",
        ),
        "webmcp_source": "Chrome WebMCP imperative API preview (subject to change)",
        "webmcp_description": (
            "Calculate only max(0, target free GB minus current free GB) from bounded self-entered "
            "numbers, report Photos storage separately, and return a reversible review plan. Never "
            "access photos, files, metadata, iCloud, accounts or device storage; never estimate "
            "recoverable capacity, classify media or delete anything."
        ),
        "app_title": "Want an optional on-device library review workflow?",
        "app_text": (
            "PicClear Pro is optional. Its current App Store listing says scanning and previews are "
            "free, with a one-time unlock for cleaning; it groups duplicates, similar photos, "
            "screenshots, blurry photos, large videos and large photos on device for review. The "
            "listing says nothing is deleted until confirmation, Favorites can be protected, and "
            "the app works offline with no account, ads or tracking. Check the current listing for "
            "exact availability and features. This planner works without the app."
        ),
        "app_cta": "View PicClear Pro on the App Store",
        "faq_title": "Photo storage cleanup questions",
        "faq": (
            (
                "Does this page scan my photo library?",
                "No. It accepts only storage numbers and status choices you enter.",
            ),
            (
                "Does the gap equal space I can recover?",
                "No. It is only target free space minus current free space, never an estimate of deletable media.",
            ),
            (
                "Is iCloud Photos an independent backup?",
                "This planner does not treat sync alone as independent because changes and deletions can propagate across devices.",
            ),
            (
                "Does Recently Deleted free space immediately?",
                "Do not assume it does. Apple documents a 30-day recovery window; measure storage after reviewed changes.",
            ),
        ),
        "footer": "Private arithmetic only · no photo access · no deletion · no recovery estimate",
        "index_title": "Private Photo Storage Cleanup Planner",
        "index_description": (
            "Calculate a known free-space gap and build a reversible review plan without "
            "uploading photos or guessing recoverable storage."
        ),
    },
    "zh-Hant": {
        "title": "私密 iPhone 照片儲存空間清理規劃器｜不上傳",
        "description": "只用自行輸入的儲存數字計算可用空間差距，再建立可逆檢查順序；不上傳、不掃描、不估算相簿。",
        "tools": "免費工具",
        "switch": "English",
        "eyebrow": "免費 · 不存取照片 · 不估可清容量",
        "heading": "私密 iPhone 照片儲存空間清理規劃器",
        "lead": "量出目前與目標可用空間的差距；本頁不猜平均檔案大小、重複率或清理後能找回多少容量。",
        "badges": (
            "不接收照片、檔案或中繼資料",
            "不存取 iCloud 或裝置",
            "不刪除也不分類",
            "不預測可清容量",
        ),
        "planner": "計算已知的儲存空間差距",
        "planner_intro": "輸入你已能在「設定」看到的數字；照片用量會分開顯示，絕不視為可刪除或可找回容量。",
        "current_label": "目前可用空間（GB）",
        "target_label": "目標可用空間（GB）",
        "photos_label": "iPhone 顯示的照片用量（GB）",
        "icloud_label": "iCloud 照片狀態",
        "icloud_options": {
            "unknown": "尚未檢查",
            "on-synced": "已開啟，顯示同步完成",
            "on-syncing-or-paused": "已開啟，正在同步、暫停或有警告",
            "off": "已關閉",
        },
        "priority_label": "第一個檢查區域",
        "priority_options": {
            "general": "一般儲存檢查",
            "duplicates": "Apple「重複項目」",
            "large-videos": "大型影片",
            "screenshots": "截圖",
        },
        "copy_label": "我已驗證無法取代原檔的獨立副本",
        "deleted_label": "我已檢查「最近刪除」",
        "update": "更新私密規劃",
        "invalid_input": "請完整輸入三個 0 到 2,048 GB 的儲存數字。",
        "result_gap": "仍需增加的可用空間",
        "result_current": "目前可用空間",
        "result_target": "目標可用空間",
        "result_photos": "回報的照片用量",
        "result_status": "目標狀態",
        "met": "已達目標",
        "not_met": "仍有差距",
        "result_plan": "可逆檢查順序",
        "gap_boundary": (
            "差距算式：max（0，目標可用 GB − 目前可用 GB）。結果沿用輸入的 GB 單位，"
            "不是照片或 PicClear 能找回多少容量的預測。"
        ),
        "photos_boundary": (
            "照片用量只供背景參考；內容可能重要、已同步、經過最佳化、共享、編輯，或在裝置上以不同方式計算。"
        ),
        "icloud_steps": {
            "unknown": "更動無法取代的原檔前，先檢查照片同步狀態；iCloud 照片開啟時，編輯與刪除可能同步到其他裝置。",
            "on-synced": "即使 iCloud 照片顯示同步完成，更動與刪除仍會跨裝置同步；不要把同步當成唯一獨立副本。",
            "on-syncing-or-paused": "破壞性更動前先處理 iCloud 照片同步、暫停或空間警告，並確認實際完成同步的內容。",
            "off": "iCloud 照片回報為關閉；破壞性更動前，請驗證無法取代原檔另有獨立副本。",
        },
        "priority_steps": {
            "general": "先看「設定 > 一般 > iPhone 儲存空間」建議，再分批檢查 Apple「重複項目」、影片及截圖。",
            "duplicates": "開啟「照片 > 選集 > 工具程式 > 重複項目」並逐組檢查合併；照片未找到重複項目時，該選集可能不會出現。",
            "large-videos": "逐一確認影片的重要性及獨立原檔是否能開啟；片長或分類不代表影片可以丟棄。",
            "screenshots": "小批量檢查「截圖」選集，保留記錄、驗證、旅行、工作或無障礙用途所需內容。",
        },
        "copy_yes": "永久刪除前先實際開啟獨立副本的抽樣檔案；本工具不把 iCloud 照片同步單獨視為獨立封存。",
        "copy_no": "先停止永久刪除，為無法取代的原檔建立可驗證獨立副本；iCloud 照片更動可能同步到其他裝置。",
        "deleted_yes": "永久移除任何項目前重新檢查「最近刪除」；永久移除會結束一般復原期限。",
        "deleted_no": "先檢查「最近刪除」。Apple 說明刪除項目通常保留 30 天；確認無誤且重要原檔已獨立驗證前，不要清空。",
        "final_step": "完成一小批檢查後，重新查看 iPhone 儲存空間；量測真實變化，不假設計算差距就是可刪內容。",
        "checklist_title": "安全優先的清理順序",
        "checklist": (
            "到「設定 > 一般 > iPhone 儲存空間」核對目前可用空間與照片用量。",
            "永久刪除前，驗證無法取代的原檔另有可開啟的獨立副本。",
            "檢查 iCloud 照片同步狀態，並記得更動可能跨裝置同步。",
            "每次只檢查一小批；不可因為分類就判定內容可以丟棄。",
            "決定下一批前，重新檢查「最近刪除」與裝置空間。",
        ),
        "scope_title": "這個規劃器無法知道什麼",
        "scope_text": (
            "它無法讀取照片圖庫、儲存空間、iCloud、相簿、檔案、中繼資料、喜好項目、重複、模糊、"
            "影片大小或刪除結果；不會把任何內容標成可安全刪除，也無法預測可找回容量。"
        ),
        "sources_title": "任何選用清理工具之前，先看 Apple 官方步驟",
        "sources_intro": (
            "Apple 說明 iPhone 儲存空間、iCloud 照片同步與最佳化、「重複項目」以及「最近刪除」30 天期限；"
            "請依目前 iOS 版本核對最新步驟。"
        ),
        "source_labels": (
            "Apple：查看 iPhone 與 iPad 儲存空間",
            "Apple：使用 iCloud 備份與同步照片和影片",
            "Apple：在 iPhone 合併重複照片與影片",
            "Apple：刪除、復原或永久移除照片與影片",
        ),
        "webmcp_source": "Chrome WebMCP 命令式 API 預覽（規格可能變動）",
        "webmcp_description": (
            "只用有界、自行輸入的數字計算 max（0，目標可用 GB 減目前可用 GB），分開回報照片用量，"
            "再提供可逆檢查順序；不存取照片、檔案、中繼資料、iCloud、帳號或裝置空間，不估算可找回容量、"
            "不分類媒體，也不刪除任何內容。"
        ),
        "app_title": "需要選用的裝置端圖庫檢查流程？",
        "app_text": (
            "PicClear Pro 是選用工具；目前 App Store 頁面說明可免費掃描與預覽，一次性解鎖清理，"
            "並在裝置端把重複、相似照片、截圖、模糊照片、大型影片與大型照片分組供使用者檢查。"
            "商店頁說明確認前不會刪除、可保護「喜好項目」，並可離線使用，免帳號、無廣告、無追蹤。"
            "供應地區與確切功能請以目前商店頁為準；本規劃器不需 App 也能使用。"
        ),
        "app_cta": "在 App Store 查看 PicClear Pro",
        "faq_title": "照片儲存空間清理常見問題",
        "faq": (
            ("這個網頁會掃描我的照片圖庫嗎？", "不會。它只接收你自行輸入的儲存數字與狀態選項。"),
            ("計算差距等於能找回的空間嗎？", "不等於。它只是目標可用空間減目前可用空間，絕不估算可刪媒體。"),
            ("iCloud 照片是獨立備份嗎？", "本工具不把同步單獨視為獨立副本，因為更動與刪除可能跨裝置同步。"),
            ("「最近刪除」會立刻釋放空間嗎？", "不要自行假設。Apple 說明有 30 天復原期限；完成檢查後重新量測空間。"),
        ),
        "footer": "只做私密算式 · 不存取照片 · 不刪除 · 不估可清容量",
        "index_title": "私密照片儲存空間清理規劃器",
        "index_description": "計算已知可用空間差距並建立可逆檢查順序，不上傳照片，也不猜可清容量。",
    },
}

STYLE = r"""
:root{--ink:#18343a;--muted:#607479;--line:#d9e6e5;--paper:#fff;--bg:#eef7f5;--deep:#176c65;--mint:#4aa89a;--soft:#e6f5f1;--warn:#fff6da;--shadow:0 22px 60px rgba(23,76,72,.12)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 90% 0,#fff 0,var(--bg) 55%,#e0efec 100%);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Noto Sans TC",sans-serif;line-height:1.62}
a{color:#176c65}.wrap{width:min(1120px,calc(100% - 30px));margin:auto}.top{position:sticky;top:0;z-index:8;background:#fffffff2;border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:850;white-space:nowrap}.links{display:flex;gap:15px;overflow-x:auto}
.hero{padding:64px 0 30px}.eyebrow,.badge{display:inline-flex;border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 12px;font-size:13px;font-weight:850;color:var(--deep);white-space:nowrap}.hero h1,h2{font-family:ui-serif,Georgia,"Noto Serif TC",serif}.hero h1{font-size:clamp(34px,6vw,60px);line-height:1.04;letter-spacing:-.035em;margin:.3em 0 .22em;white-space:nowrap;overflow-x:auto}.lead{font-size:clamp(17px,2.2vw,21px);color:var(--muted);margin:0;white-space:nowrap;overflow-x:auto}.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:22px}
.planner,.card,.app-card{background:rgba(255,255,255,.97);border:1px solid var(--line);border-radius:26px;box-shadow:var(--shadow)}.planner{padding:clamp(20px,4vw,36px);margin:16px auto 30px}.planner h2,.card h2,.app-card h2{font-size:clamp(24px,3.6vw,34px);line-height:1.14;margin:0;white-space:nowrap;overflow-x:auto}.intro{color:var(--muted);white-space:nowrap;overflow-x:auto}
.controls{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:22px}.field{min-width:0}.field label{display:block;font-size:13px;font-weight:850;color:var(--deep);margin-bottom:6px;white-space:nowrap;overflow-x:auto}select,input,button{font:inherit}select,input[type=number]{width:100%;min-height:46px;border:1px solid #c7d9d6;border-radius:13px;background:#fff;color:var(--ink);padding:9px 11px}.toggle{display:flex;align-items:center;gap:10px;border:1px solid var(--line);border-radius:14px;padding:11px 13px;background:#fff;font-weight:760;white-space:nowrap;overflow-x:auto}.toggle input{inline-size:20px;block-size:20px;flex:0 0 auto}.button{border:0;border-radius:999px;background:linear-gradient(135deg,var(--deep),var(--mint));color:#fff;text-decoration:none;font-weight:850;padding:11px 17px;cursor:pointer;white-space:nowrap;box-shadow:0 9px 22px rgba(23,108,101,.2)}
.results{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:11px;margin-top:22px}.result{background:var(--soft);border:1px solid #c4e0da;border-radius:17px;padding:14px;min-width:0}.result strong,.result span{display:block;white-space:nowrap;overflow-x:auto}.result strong{font-size:12px;color:#39736d;text-transform:uppercase;letter-spacing:.04em}.result span{font-size:15px;color:#28534f;font-weight:760;margin-top:5px}.note{background:var(--warn);border:1px solid #ead9a7;border-radius:16px;padding:13px 15px;margin:14px 0 0;white-space:nowrap;overflow-x:auto}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:30px}.card,.app-card{padding:clamp(20px,3.5vw,30px)}.card.wide{grid-column:1/-1}.card p,.card li,.app-card p,.faq details p,.faq summary{white-space:nowrap;overflow-x:auto}.card ul,.card ol{padding-left:22px}.card li{margin:8px 0}.source-list a{overflow-wrap:anywhere}.app-card{margin:0 auto 38px;background:linear-gradient(135deg,#fbfffe,#e3f3ef)}.app-card .button{display:inline-flex;margin-top:5px}.faq{margin-bottom:30px}.faq details{border:1px solid var(--line);border-radius:15px;background:#fff;padding:11px 14px;margin-top:9px}.faq summary{font-weight:830;cursor:pointer}.faq details p{color:var(--muted)}
.footer{background:var(--deep);color:#effcf9;text-align:center;padding:27px 0;white-space:nowrap;overflow-x:auto}
@media(max-width:960px){.controls{grid-template-columns:repeat(2,minmax(0,1fr))}.results{grid-template-columns:repeat(2,minmax(0,1fr))}.grid{grid-template-columns:1fr}.card.wide{grid-column:auto}}
@media(max-width:560px){.controls,.results{grid-template-columns:1fr}.wrap{width:min(100% - 22px,1120px)}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
@media print{.top,.hero,.controls,.button,.app-card,.footer{display:none!important}body{background:#fff}.planner,.card{box-shadow:none;break-inside:avoid}}
"""

SCRIPT = r"""
(() => {
  const config = JSON.parse(document.getElementById("storage-config").textContent);
  const form = document.getElementById("storage-planner");
  const fields = {
    current_free_gb: document.getElementById("current-free"),
    target_free_gb: document.getElementById("target-free"),
    photos_storage_gb: document.getElementById("photos-storage"),
    icloud_photos_status: document.getElementById("icloud-status"),
    independent_copy_verified: document.getElementById("copy-verified"),
    recently_deleted_reviewed: document.getElementById("deleted-reviewed"),
    priority: document.getElementById("priority")
  };
  const output = {
    gap: document.getElementById("result-gap"),
    current: document.getElementById("result-current"),
    target: document.getElementById("result-target"),
    photos: document.getElementById("result-photos"),
    status: document.getElementById("result-status"),
    plan: document.getElementById("result-plan")
  };

  function round(value, digits = 2) {
    const factor = 10 ** digits;
    return Math.round((value + Number.EPSILON) * factor) / factor;
  }

  function numberValue(input, name) {
    if (!Object.prototype.hasOwnProperty.call(input, name)) {
      throw new TypeError(`${name} is required.`);
    }
    const value = input[name];
    const schema = config.inputSchema.properties[name];
    if (typeof value !== "number" || !Number.isFinite(value)) {
      throw new TypeError(`${name} must be a finite number.`);
    }
    if (value < schema.minimum || value > schema.maximum) {
      throw new RangeError(`${name} is outside the supported range.`);
    }
    return value;
  }

  function enumValue(input, name) {
    if (!Object.prototype.hasOwnProperty.call(input, name)) {
      throw new TypeError(`${name} is required.`);
    }
    const value = input[name];
    const values = config.inputSchema.properties[name].enum;
    if (typeof value !== "string" || !values.includes(value)) {
      throw new RangeError(`${name} is not a supported value.`);
    }
    return value;
  }

  function booleanValue(input, name) {
    if (!Object.prototype.hasOwnProperty.call(input, name)) {
      throw new TypeError(`${name} is required.`);
    }
    if (typeof input[name] !== "boolean") {
      throw new TypeError(`${name} must be a boolean.`);
    }
    return input[name];
  }

  function plan(input) {
    const current = numberValue(input, "current_free_gb");
    const target = numberValue(input, "target_free_gb");
    const photos = numberValue(input, "photos_storage_gb");
    const icloud = enumValue(input, "icloud_photos_status");
    const independentCopy = booleanValue(input, "independent_copy_verified");
    const recentlyDeleted = booleanValue(input, "recently_deleted_reviewed");
    const priority = enumValue(input, "priority");
    const gap = Math.max(0, target - current);
    return {
      selected_inputs: {
        current_free_gb: current,
        target_free_gb: target,
        photos_storage_gb: photos,
        icloud_photos_status: icloud,
        icloud_photos_status_label: config.labels.icloud[icloud],
        independent_copy_verified: independentCopy,
        recently_deleted_reviewed: recentlyDeleted,
        priority,
        priority_label: config.labels.priority[priority]
      },
      free_space_gap: {
        formula: "max(0, target_free_gb - current_free_gb)",
        additional_free_space_gap_gb: gap,
        target_already_met: target <= current,
        same_gb_unit_as_entered: true,
        is_not_recoverable_space_prediction: true
      },
      reported_photos_storage: {
        photos_storage_gb: photos,
        is_context_not_deletable_or_recoverable_capacity: true
      },
      reversible_review_plan: [
        independentCopy ? config.copyYes : config.copyNo,
        config.icloudSteps[icloud],
        config.prioritySteps[priority],
        recentlyDeleted ? config.deletedYes : config.deletedNo,
        config.finalStep
      ],
      gap_boundary: config.gapBoundary,
      photos_boundary: config.photosBoundary,
      scope_boundary: config.scopeBoundary
    };
  }

  function validateInput(input) {
    if (input === null || typeof input !== "object" || Array.isArray(input)) {
      throw new TypeError("WebMCP input must be an object.");
    }
    const allowed = new Set(Object.keys(config.inputSchema.properties));
    for (const name of Object.keys(input)) {
      if (!allowed.has(name)) {
        throw new RangeError(`${name} is not a supported input.`);
      }
    }
    return plan(input);
  }

  function formatGb(value) {
    if (value > 0 && value < 0.01) return "<0.01 GB";
    return `${round(value)} GB`;
  }

  function humanNumber(field, name) {
    const raw = String(field.value).trim();
    const value = raw === "" ? Number.NaN : Number(raw);
    const schema = config.inputSchema.properties[name];
    if (!Number.isFinite(value) ||
        value < schema.minimum ||
        value > schema.maximum) {
      throw new RangeError(`${name} is outside the supported range.`);
    }
    return value;
  }

  function renderInvalid() {
    output.gap.textContent = "—";
    output.current.textContent = "—";
    output.target.textContent = "—";
    output.photos.textContent = "—";
    output.status.textContent = "—";
    output.plan.textContent = config.invalidInput;
  }

  function render() {
    let result;
    try {
      result = plan({
        current_free_gb: humanNumber(
          fields.current_free_gb, "current_free_gb"),
        target_free_gb: humanNumber(
          fields.target_free_gb, "target_free_gb"),
        photos_storage_gb: humanNumber(
          fields.photos_storage_gb, "photos_storage_gb"),
        icloud_photos_status: fields.icloud_photos_status.value,
        independent_copy_verified: fields.independent_copy_verified.checked,
        recently_deleted_reviewed: fields.recently_deleted_reviewed.checked,
        priority: fields.priority.value
      });
    } catch (error) {
      if (error instanceof TypeError || error instanceof RangeError) {
        renderInvalid();
        return;
      }
      throw error;
    }
    output.gap.textContent =
      formatGb(result.free_space_gap.additional_free_space_gap_gb);
    output.current.textContent =
      formatGb(result.selected_inputs.current_free_gb);
    output.target.textContent =
      formatGb(result.selected_inputs.target_free_gb);
    output.photos.textContent =
      formatGb(result.reported_photos_storage.photos_storage_gb);
    output.status.textContent =
      result.free_space_gap.target_already_met ? config.met : config.notMet;
    output.plan.textContent =
      result.reversible_review_plan.join(" ");
  }

  async function registerWebMcp() {
    if (!document.modelContext?.registerTool) return;
    await document.modelContext.registerTool({
      name: "plan_private_photo_storage_cleanup",
      description: config.toolDescription,
      inputSchema: config.inputSchema,
      annotations: {readOnlyHint: true, untrustedContentHint: false},
      execute: async (input) => {
        const plan = validateInput(input);
        const result = {
          result_type: "private_photo_storage_cleanup_plan",
          photos_files_metadata_icloud_device_not_accessed: true,
          no_media_classification_or_deletion: true,
          no_recoverable_space_prediction: true,
          plan,
          safety_first_checklist: config.checklist,
          optional_free_planner: config.freePlanner,
          official_sources: config.officialSources,
          webmcp_preview_source: config.webmcpSource
        };
        if (config.optionalApp) {
          result.optional_picclear_pro = config.optionalApp;
        }
        return JSON.stringify(result);
      }
    });
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    render();
  });
  for (const field of Object.values(fields)) {
    field.addEventListener("change", render);
  }
  render();
  registerWebMcp().catch((error) =>
    console.error("WebMCP tool registration failed.", error));
})();
"""


def canonical(locale: str) -> str:
    prefix = "" if locale == "en" else f"{locale}/"
    return f"{SITE}/{prefix}tools/{SLUG}.html"


def json_script(value: dict[str, object]) -> str:
    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return (
        '<script type="application/ld+json">'
        + payload.replace("</", "<\\/")
        + "</script>"
    )


def options(values: dict[str, str]) -> str:
    return "".join(
        f'<option value="{html.escape(key, quote=True)}">{html.escape(label)}</option>'
        for key, label in values.items()
    )


def webmcp_input_schema(locale: str) -> dict[str, object]:
    if locale not in COPY:
        raise ValueError(f"unsupported locale: {locale}")
    number = {
        "type": "number",
        "minimum": 0,
        "maximum": 2048,
    }
    return {
        "type": "object",
        "properties": {
            "current_free_gb": {
                **number,
                "description": "Current free storage shown by the device, in GB.",
            },
            "target_free_gb": {
                **number,
                "description": "User-selected target free storage, in the same GB unit.",
            },
            "photos_storage_gb": {
                **number,
                "description": "Photos storage shown by the device, for context only.",
            },
            "icloud_photos_status": {
                "type": "string",
                "enum": list(ICLOUD_STATUSES),
            },
            "independent_copy_verified": {"type": "boolean"},
            "recently_deleted_reviewed": {"type": "boolean"},
            "priority": {
                "type": "string",
                "enum": list(PRIORITIES),
            },
        },
        "required": [
            "current_free_gb",
            "target_free_gb",
            "photos_storage_gb",
            "icloud_photos_status",
            "independent_copy_verified",
            "recently_deleted_reviewed",
            "priority",
        ],
        "additionalProperties": False,
    }


def render_page(locale: str, app_public: bool) -> str:
    if locale not in COPY:
        raise ValueError(f"unsupported locale: {locale}")
    t = COPY[locale]
    other = "zh-Hant" if locale == "en" else "en"
    url = canonical(locale)
    alternate = canonical(other)
    prefix = "" if locale == "en" else f"{locale}/"
    home = f"{SITE}/{prefix}index.html"
    tools = f"{SITE}/{prefix}tools/index.html"
    sources = (
        APPLE_STORAGE,
        APPLE_ICLOUD_PHOTOS,
        APPLE_DUPLICATES,
        APPLE_DELETE_RECOVER,
    )
    source_items = "".join(
        f'<li><a href="{html.escape(source, quote=True)}" rel="noopener">'
        f"{html.escape(label)}</a></li>"
        for label, source in zip(t["source_labels"], sources, strict=True)
    )
    checklist_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in t["checklist"]
    )
    badges = "".join(
        f'<span class="badge">{html.escape(item)}</span>' for item in t["badges"]
    )
    faq = "".join(
        f"<details><summary>{html.escape(question)}</summary>"
        f"<p>{html.escape(answer)}</p></details>"
        for question, answer in t["faq"]
    )
    tracked_app_url = (
        appstore_url(APP_KEY, f"iag_photo_storage_{locale.lower()}")
        if app_public
        else ""
    )
    app_card = ""
    if tracked_app_url:
        app_card = (
            '<section class="app-card wrap"><h2>'
            f'{html.escape(t["app_title"])}</h2><p>{html.escape(t["app_text"])}</p>'
            f'<a class="button" href="{html.escape(tracked_app_url, quote=True)}" '
            f'rel="nofollow noopener">{html.escape(t["app_cta"])}</a></section>'
        )
    config = {
        "inputSchema": webmcp_input_schema(locale),
        "labels": {
            "icloud": t["icloud_options"],
            "priority": t["priority_options"],
        },
        "icloudSteps": t["icloud_steps"],
        "prioritySteps": t["priority_steps"],
        "copyYes": t["copy_yes"],
        "copyNo": t["copy_no"],
        "deletedYes": t["deleted_yes"],
        "deletedNo": t["deleted_no"],
        "finalStep": t["final_step"],
        "gapBoundary": t["gap_boundary"],
        "photosBoundary": t["photos_boundary"],
        "scopeBoundary": t["scope_text"],
        "met": t["met"],
        "notMet": t["not_met"],
        "invalidInput": t["invalid_input"],
        "checklist": t["checklist"],
        "toolDescription": t["webmcp_description"],
        "freePlanner": {
            "label": t["heading"],
            "url": url,
            "boundary": t["planner_intro"],
        },
        "officialSources": [
            {"label": label, "url": source}
            for label, source in zip(t["source_labels"], sources, strict=True)
        ],
        "webmcpSource": WEBMCP_SOURCE,
        "optionalApp": (
            {
                "label": t["app_cta"],
                "boundary": t["app_text"],
                "app_store_url": tracked_app_url,
            }
            if tracked_app_url
            else None
        ),
    }
    config_json = json.dumps(
        config, ensure_ascii=False, separators=(",", ":")
    ).replace("</", "<\\/")
    schema = {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": t["heading"],
        "description": t["description"],
        "url": url,
        "inLanguage": locale,
        "datePublished": CONTENT_DATE,
        "dateModified": CONTENT_DATE,
        "applicationCategory": "UtilitiesApplication",
        "operatingSystem": "Any",
        "isAccessibleForFree": True,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "featureList": [
            "No photo, file, metadata, iCloud or device access",
            "Transparent target-minus-current free-space gap",
            "Photos storage reported separately as context",
            "Reversible review sequence",
            "No recoverable-space prediction, classification or deletion",
        ],
        "citation": list(sources),
    }
    faq_schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "inLanguage": locale,
        "mainEntity": [
            {
                "@type": "Question",
                "name": question,
                "acceptedAnswer": {"@type": "Answer", "text": answer},
            }
            for question, answer in t["faq"]
        ],
    }
    return f"""<!DOCTYPE html>
<html lang="{locale}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(t["title"])}</title>
<meta name="description" content="{html.escape(t["description"])}">
<link rel="canonical" href="{url}">
<link rel="alternate" hreflang="en" href="{canonical("en")}">
<link rel="alternate" hreflang="zh-Hant" href="{canonical("zh-Hant")}">
<link rel="alternate" hreflang="x-default" href="{canonical("en")}">
<meta property="og:type" content="website">
<meta property="og:title" content="{html.escape(t["heading"])}">
<meta property="og:description" content="{html.escape(t["description"])}">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary">
<style>{STYLE}</style>
{json_script(schema)}
{json_script(faq_schema)}
{feed_discovery_links()}
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{home}">iOS App Guide</a><nav class="links"><a href="{tools}">{html.escape(t["tools"])}</a><a href="{alternate}">{html.escape(t["switch"])}</a></nav></div></header>
<main>
<section class="hero wrap"><div class="eyebrow">{html.escape(t["eyebrow"])}</div><h1>{html.escape(t["heading"])}</h1><p class="lead">{html.escape(t["lead"])}</p><div class="badges">{badges}</div></section>
<section class="planner wrap"><h2>{html.escape(t["planner"])}</h2><p class="intro">{html.escape(t["planner_intro"])}</p>
<form id="storage-planner"><div class="controls">
<div class="field"><label for="current-free">{html.escape(t["current_label"])}</label><input id="current-free" type="number" min="0" max="2048" step="0.1" value="0" required></div>
<div class="field"><label for="target-free">{html.escape(t["target_label"])}</label><input id="target-free" type="number" min="0" max="2048" step="0.1" value="0" required></div>
<div class="field"><label for="photos-storage">{html.escape(t["photos_label"])}</label><input id="photos-storage" type="number" min="0" max="2048" step="0.1" value="0" required></div>
<div class="field"><label for="icloud-status">{html.escape(t["icloud_label"])}</label><select id="icloud-status">{options(t["icloud_options"])}</select></div>
<div class="field"><label for="priority">{html.escape(t["priority_label"])}</label><select id="priority">{options(t["priority_options"])}</select></div>
<label class="toggle"><input id="copy-verified" type="checkbox">{html.escape(t["copy_label"])}</label>
<label class="toggle"><input id="deleted-reviewed" type="checkbox">{html.escape(t["deleted_label"])}</label>
</div><p><button class="button" type="submit">{html.escape(t["update"])}</button></p></form>
<div class="results"><div class="result"><strong>{html.escape(t["result_gap"])}</strong><span id="result-gap"></span></div><div class="result"><strong>{html.escape(t["result_current"])}</strong><span id="result-current"></span></div><div class="result"><strong>{html.escape(t["result_target"])}</strong><span id="result-target"></span></div><div class="result"><strong>{html.escape(t["result_photos"])}</strong><span id="result-photos"></span></div><div class="result"><strong>{html.escape(t["result_status"])}</strong><span id="result-status"></span></div></div>
<p class="note">{html.escape(t["gap_boundary"])}</p><p class="note">{html.escape(t["photos_boundary"])}</p><p class="note"><strong>{html.escape(t["result_plan"])}:</strong> <span id="result-plan"></span></p></section>
<section class="wrap grid"><article class="card"><h2>{html.escape(t["checklist_title"])}</h2><ol>{checklist_items}</ol></article><article class="card"><h2>{html.escape(t["scope_title"])}</h2><p>{html.escape(t["scope_text"])}</p></article><article class="card wide"><h2>{html.escape(t["sources_title"])}</h2><p>{html.escape(t["sources_intro"])}</p><ul class="source-list">{source_items}</ul><p><a href="{WEBMCP_SOURCE}" rel="noopener">{html.escape(t["webmcp_source"])}</a></p></article></section>
<section class="wrap card faq"><h2>{html.escape(t["faq_title"])}</h2>{faq}</section>
{app_card}
</main>
<footer class="footer"><div class="wrap">{html.escape(t["footer"])}</div></footer>
<script type="application/json" id="storage-config">{config_json}</script>
<script>{SCRIPT}</script>
</body>
</html>
"""


def index_card(locale: str) -> str:
    t = COPY[locale]
    return (
        f'<article class="card third" data-tool="{SLUG}"><h2><a href="'
        f'{SLUG}.html">{html.escape(t["index_title"])}</a></h2>'
        f'<p>{html.escape(t["index_description"])}</p></article>'
    )


def update_one_index(path: Path, locale: str) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    card = index_card(locale)
    existing = re.compile(
        rf'<article class="card third"(?: data-tool="{re.escape(SLUG)}")?>'
        rf'<h2><a href="{re.escape(SLUG)}\.html">.*?</article>',
        re.S,
    )
    updated = existing.sub("", text)
    anchor = re.compile(
        r'(<article class="card third" data-tool="'
        r'screen-time-calculator">.*?</article>)',
        re.S,
    )
    if anchor.search(updated):
        updated = anchor.sub(r"\1" + card, updated, count=1)
    else:
        marker = '<section class="wrap grid">'
        if marker not in updated:
            raise RuntimeError(f"{path} is missing its tools grid")
        updated = updated.replace(marker, marker + card, 1)
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def write_text_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def build(pages: Path = PAGES, app_public: bool | None = None) -> list[str]:
    if app_public is None:
        app_public = APP_KEY in live_app_keys(APPSTORE, pages, refresh=False)
    outputs = []
    for locale in COPY:
        relative = Path("tools") / f"{SLUG}.html"
        if locale != "en":
            relative = Path(locale) / relative
        write_text_if_changed(
            pages / relative,
            render_page(locale, app_public),
        )
        outputs.append(canonical(locale))
    update_one_index(pages / "tools" / "index.html", "en")
    update_one_index(
        pages / "zh-Hant" / "tools" / "index.html",
        "zh-Hant",
    )
    return outputs


def main() -> None:
    outputs = build()
    sitemap_count = write_tools_sitemap()
    for output in outputs:
        print(f"photo storage cleanup planner -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
