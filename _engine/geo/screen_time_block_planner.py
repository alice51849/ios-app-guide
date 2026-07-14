#!/usr/bin/env python3
"""Generate a bilingual, private screen-time and block planning tool."""

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
SLUG = "screen-time-calculator"
APP_KEY = "lockhour"
APP_ID = "6780107485"
CONTENT_DATE = "2026-07-15"
APPLE_SCREEN_TIME = (
    "https://support.apple.com/guide/iphone/"
    "get-started-with-screen-time-iphbfa595995/ios"
)
APPLE_SCREEN_TIME_SCHEDULES = (
    "https://support.apple.com/guide/iphone/"
    "set-schedules-with-screen-time-iphb0c7313c9/ios"
)
APPLE_FOCUS = (
    "https://support.apple.com/guide/iphone/"
    "set-up-a-focus-iphd6288a67f/ios"
)
WEBMCP_SOURCE = "https://developer.chrome.com/docs/ai/webmcp/imperative-api"

MEASUREMENTS = (
    "total-device",
    "social-media",
    "video",
    "games",
    "news-shopping",
)
BLOCK_MINUTES = (0, 15, 25, 30, 45, 60, 90, 120)
BLOCK_WINDOWS = ("custom", "morning", "work-study", "evening")
ALT_LOCALES = (
    "en",
    "es-ES",
    "pt-BR",
    "de-DE",
    "fr-FR",
    "ja",
    "ko",
    "zh-Hant",
    "zh-Hans",
)

COPY = {
    "en": {
        "title": "Private Screen Time & App Block Planner | Transparent Math",
        "description": (
            "Convert a self-entered screen-time pattern into transparent annual-equivalent "
            "math and a separate reversible app-block schedule without accessing device data."
        ),
        "tools": "Free tools",
        "switch": "繁體中文",
        "eyebrow": "Free · local math · no device access",
        "heading": "Private screen time and app block planner",
        "lead": (
            "Enter a pattern you already know and separately plan a protected window. "
            "Scheduled block time is never presented as saved time or guaranteed focus."
        ),
        "badges": (
            "No Screen Time or app access",
            "No account or contact access",
            "No saved-time claim",
            "No focus or health promise",
        ),
        "planner": "Compare the observed pattern and planned blocks",
        "planner_intro": (
            "The first calculation annualizes your entered pattern. The second totals scheduled "
            "blocks. It does not subtract one from the other or predict behavior."
        ),
        "measurement_label": "What are you measuring?",
        "measurement_options": {
            "total-device": "Total device use",
            "social-media": "Social media",
            "video": "Video",
            "games": "Games",
            "news-shopping": "News or shopping",
        },
        "daily_label": "Observed minutes per active day",
        "days_label": "Observed days per week",
        "block_minutes_label": "Planned block length",
        "block_minutes_options": {
            0: "No block selected",
            15: "15 minutes",
            25: "25 minutes",
            30: "30 minutes",
            45: "45 minutes",
            60: "60 minutes",
            90: "90 minutes",
            120: "120 minutes",
        },
        "block_days_label": "Planned block days per week",
        "window_label": "Block window",
        "window_options": {
            "custom": "Custom",
            "morning": "Morning",
            "work-study": "Work or study",
            "evening": "Evening",
        },
        "essential_label": "I reviewed essential access before blocking",
        "update": "Update transparent plan",
        "result_observed_hours": "Annual-equivalent observed hours",
        "result_observed_days": "Annual-equivalent 24-hour days",
        "result_block_week": "Scheduled block minutes per week",
        "result_block_year": "Scheduled block hours across 52 weeks",
        "result_measurement": "Selected measurement",
        "result_plan": "Reversible preflight",
        "observed_boundary": (
            "Observed annual-equivalent uses daily minutes × active days ÷ 7 × 365. "
            "It represents only the pattern entered here, not a direct Screen Time reading."
        ),
        "block_boundary": (
            "Scheduled block hours use block length × block days × 52. They are calendar "
            "intent only—not screen time saved, attention recovered, focus gained or work completed."
        ),
        "window_steps": {
            "morning": (
                "Choose an exact morning start and end, then confirm alarms, transport, "
                "authentication and essential communication remain reachable.",
                "Prepare one allowed first action before the block begins.",
            ),
            "work-study": (
                "Define the work or study outcome before selecting apps to block.",
                "Keep required communication, authentication, accessibility and reference tools available.",
            ),
            "evening": (
                "Choose an exact evening end point and preserve urgent communication and care access.",
                "Prepare an allowed wind-down activity rather than relying on an empty restriction.",
            ),
            "custom": (
                "Name the real situation outside this page, then set a clear start, end and exit path.",
                "Block only apps unrelated to that situation and keep essential tools reachable.",
            ),
        },
        "essential_yes": (
            "Re-check the allowed list before the first session and use the shortest practical "
            "test block so the setup remains reversible."
        ),
        "essential_no": (
            "Before blocking anything, identify essential communication, navigation, authentication, "
            "accessibility and care tools, plus a reliable exit or recovery path."
        ),
        "preflight_title": "Five checks before an app-block session",
        "preflight": (
            "Use Settings > Screen Time to verify the source pattern instead of guessing when possible.",
            "Select only apps unrelated to the specific protected window.",
            "Keep essential communication, navigation, authentication, accessibility and care access available.",
            "Define the allowed replacement action and a clear way to end or recover the session.",
            "Test the shortest practical block, review what actually happened, then adjust without claiming saved time.",
        ),
        "scope_title": "What this planner does not know",
        "scope_text": (
            "It cannot read your Screen Time report, installed apps, notifications, contacts, "
            "device settings or session results. It is for personal planning, not child safety, "
            "emergency access, medical care, employment monitoring or treatment."
        ),
        "sources_title": "Official feature context, not outcome evidence",
        "sources_intro": (
            "Apple documents viewing Screen Time activity, setting schedules and limits, and "
            "using Focus to minimize distractions. Those features do not prove a planned block "
            "will reduce use or improve focus."
        ),
        "source_labels": (
            "Apple: get started with Screen Time on iPhone",
            "Apple: set schedules with Screen Time on iPhone",
            "Apple: set up a Focus on iPhone",
        ),
        "webmcp_source": "Chrome WebMCP imperative API preview (subject to change)",
        "webmcp_description": (
            "Calculate transparent annual-equivalent screen-time math from bounded self-entered "
            "minutes and days, plus a separate reversible app-block schedule. Never access Screen "
            "Time, installed apps, accounts, contacts or device data, and never present planned "
            "blocks as saved time, focus, health or productivity outcomes."
        ),
        "app_title": "Want an optional on-device blocking workflow?",
        "app_text": (
            "LockHour Pro is optional. Its current App Store listing describes timed blocking "
            "for selected apps with automatic unlock, Quick Focus, Deep Work, Study, Sleep Wind "
            "Down, Morning Reset and Custom modes, plus widgets and Live Activity. The listing "
            "also says no account, ads or tracking, on-device data and a one-time unlock. Check "
            "the current listing for exact availability and features. This planner works without the app."
        ),
        "app_cta": "View LockHour Pro on the App Store",
        "faq_title": "Screen time planning questions",
        "faq": (
            (
                "Does this page read my iPhone Screen Time?",
                "No. You manually enter bounded numbers; the page has no device, app or account access.",
            ),
            (
                "Are scheduled block hours the same as time saved?",
                "No. A schedule is intent. This page never assumes the block ran or changed behavior.",
            ),
            (
                "Is all screen time harmful?",
                "No. The calculation does not label work, communication, navigation, reading or any other use as good or bad.",
            ),
            (
                "Should essential apps be blocked?",
                "No. Review communication, navigation, authentication, accessibility and care access before any restriction.",
            ),
        ),
        "footer": "Private planning math only · no device access · scheduled is not saved",
        "index_title": "Private Screen Time & App Block Planner",
        "index_description": (
            "Annualize a self-entered usage pattern and plan separate reversible blocks "
            "without accessing Screen Time or claiming saved hours."
        ),
    },
    "zh-Hant": {
        "title": "私密螢幕時間與 App 封鎖規劃器｜透明算式",
        "description": "把自行輸入的螢幕使用模式換算為透明年度等值，並另行規劃可逆封鎖時段；完全不存取裝置資料。",
        "tools": "免費工具",
        "switch": "English",
        "eyebrow": "免費 · 本機運算 · 不存取裝置",
        "heading": "私密螢幕時間與 App 封鎖規劃器",
        "lead": "輸入你已知道的使用模式，再分開規劃保護時段；排定封鎖時間不會被宣稱為省下時間或保證專注。",
        "badges": (
            "不讀取螢幕使用時間或 App",
            "不存取帳號或聯絡人",
            "不宣稱省下時間",
            "不保證專注或健康成果",
        ),
        "planner": "分開比較已觀察模式與規劃封鎖",
        "planner_intro": "第一組算式把輸入模式換算成年等值；第二組只加總排定封鎖，兩者不相減，也不預測行為。",
        "measurement_label": "你要衡量什麼？",
        "measurement_options": {
            "total-device": "整體裝置使用",
            "social-media": "社群媒體",
            "video": "影音",
            "games": "遊戲",
            "news-shopping": "新聞或購物",
        },
        "daily_label": "每個使用日觀察到的分鐘",
        "days_label": "每週觀察到的使用日數",
        "block_minutes_label": "規劃封鎖長度",
        "block_minutes_options": {
            0: "尚未選擇封鎖",
            15: "15 分鐘",
            25: "25 分鐘",
            30: "30 分鐘",
            45: "45 分鐘",
            60: "60 分鐘",
            90: "90 分鐘",
            120: "120 分鐘",
        },
        "block_days_label": "每週規劃封鎖日數",
        "window_label": "封鎖時段",
        "window_options": {
            "custom": "自訂",
            "morning": "早晨",
            "work-study": "工作或學習",
            "evening": "晚間",
        },
        "essential_label": "封鎖前已檢查必要存取",
        "update": "更新透明規劃",
        "result_observed_hours": "觀察模式年度等值小時",
        "result_observed_days": "觀察模式年度等值 24 小時天數",
        "result_block_week": "每週排定封鎖分鐘",
        "result_block_year": "52 週排定封鎖小時",
        "result_measurement": "選定衡量項目",
        "result_plan": "可逆啟動前檢查",
        "observed_boundary": (
            "觀察模式年度等值使用「每日分鐘 × 每週使用日 ÷ 7 × 365」；它只代表本頁輸入，"
            "不是直接讀取 iPhone 螢幕使用時間。"
        ),
        "block_boundary": (
            "排定封鎖小時使用「封鎖長度 × 每週封鎖日 × 52」；它只是行事曆意圖，不是省下的"
            "螢幕時間、找回的注意力、增加的專注或完成的工作。"
        ),
        "window_steps": {
            "morning": (
                "設定明確的早晨開始及結束時間，確認鬧鐘、交通、驗證與必要聯絡仍可使用。",
                "封鎖開始前，先準備一個允許使用的第一步。",
            ),
            "work-study": (
                "選擇要封鎖的 App 前，先在本頁以外定義工作或學習成果。",
                "保留必要聯絡、驗證、無障礙及參考工具。",
            ),
            "evening": (
                "設定明確的晚間結束點，保留緊急聯絡與照護存取。",
                "準備允許使用的晚間活動，不要只留下空白限制。",
            ),
            "custom": (
                "在本頁以外說清楚真實情境，再設定開始、結束與退出方式。",
                "只封鎖和該情境無關的 App，並保留必要工具。",
            ),
        },
        "essential_yes": "第一次執行前重新核對允許清單，並使用最短且實際的測試時段，確保設定可逆。",
        "essential_no": (
            "封鎖前先找出必要聯絡、導航、驗證、無障礙與照護工具，並準備可靠的退出或復原方式。"
        ),
        "preflight_title": "App 封鎖前先確認五件事",
        "preflight": (
            "可以的話先用「設定 > 螢幕使用時間」核對來源模式，不要只靠猜測。",
            "只選擇和特定保護時段無關的 App。",
            "保留必要聯絡、導航、驗證、無障礙與照護存取。",
            "先定義允許的替代行動，以及明確結束或復原方式。",
            "先測試最短且實際的封鎖，檢查真實結果後再調整，不宣稱省下時間。",
        ),
        "scope_title": "這個規劃器不知道什麼",
        "scope_text": (
            "它無法讀取螢幕使用時間報告、已安裝 App、通知、聯絡人、裝置設定或執行結果。"
            "本工具只供個人規劃，不適用於兒童安全、緊急存取、醫療照護、員工監控或治療。"
        ),
        "sources_title": "官方功能背景，不是成果證據",
        "sources_intro": (
            "Apple 說明查看螢幕使用時間、設定排程與限制，以及用「專注模式」減少干擾；"
            "這些功能不會證明規劃封鎖一定能減少使用或提升專注。"
        ),
        "source_labels": (
            "Apple：開始使用 iPhone 螢幕使用時間",
            "Apple：在 iPhone 設定螢幕使用時間排程",
            "Apple：在 iPhone 設定專注模式",
        ),
        "webmcp_source": "Chrome WebMCP 命令式 API 預覽（規格可能變動）",
        "webmcp_description": (
            "只用有界、自行輸入的分鐘與日數計算透明螢幕時間年度等值，並另行建立可逆 App 封鎖排程；"
            "不存取螢幕使用時間、已安裝 App、帳號、聯絡人或裝置資料，也不把規劃封鎖宣稱為省下時間、"
            "專注、健康或效率成果。"
        ),
        "app_title": "需要選用的裝置端封鎖流程？",
        "app_text": (
            "LockHour Pro 是選用工具；目前 App Store 頁面說明包含選定 App 的定時封鎖與自動解鎖，"
            "以及 Quick Focus、Deep Work、Study、Sleep Wind Down、Morning Reset、Custom、"
            "小工具及 Live Activity。商店頁也標示免帳號、無廣告、無追蹤、資料留在裝置，以及一次性解鎖。"
            "供應地區與確切功能請以目前商店頁為準；本規劃器不需 App 也能使用。"
        ),
        "app_cta": "在 App Store 查看 LockHour Pro",
        "faq_title": "螢幕時間規劃常見問題",
        "faq": (
            (
                "這個網頁會讀取我的 iPhone 螢幕使用時間嗎？",
                "不會。你只會手動輸入有界數值；本頁無法存取裝置、App 或帳號。",
            ),
            (
                "排定封鎖小時等於省下時間嗎？",
                "不等於。排程只是意圖；本頁不會假設封鎖真的執行或改變行為。",
            ),
            (
                "所有螢幕使用時間都不好嗎？",
                "不是。本算式不會把工作、聯絡、導航、閱讀或任何用途評為好壞。",
            ),
            (
                "必要 App 應該一起封鎖嗎？",
                "不應該。任何限制前都要檢查聯絡、導航、驗證、無障礙與照護存取。",
            ),
        ),
        "footer": "只做私密規劃算式 · 不存取裝置 · 排定不等於省下",
        "index_title": "私密螢幕時間與 App 封鎖規劃器",
        "index_description": "換算自行輸入的使用模式並另行規劃可逆封鎖，不存取螢幕使用時間，也不宣稱省下小時。",
    },
}

STYLE = r"""
:root{--ink:#17243a;--muted:#627087;--line:#dce3ee;--paper:#fff;--bg:#eef4fb;--navy:#23466f;--blue:#4b7fb8;--soft:#e8f1fc;--warn:#fff6d9;--shadow:0 22px 60px rgba(31,61,95,.12)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 90% 0,#fff 0,var(--bg) 55%,#e0e9f4 100%);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Noto Sans TC",sans-serif;line-height:1.62}
a{color:#315f93}.wrap{width:min(1120px,calc(100% - 30px));margin:auto}.top{position:sticky;top:0;z-index:8;background:#fffffff2;border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:850;white-space:nowrap}.links{display:flex;gap:15px;overflow-x:auto}
.hero{padding:64px 0 30px}.eyebrow,.badge{display:inline-flex;border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 12px;font-size:13px;font-weight:850;color:var(--navy);white-space:nowrap}.hero h1,h2{font-family:ui-serif,Georgia,"Noto Serif TC",serif}.hero h1{font-size:clamp(34px,6vw,62px);line-height:1.04;letter-spacing:-.035em;margin:.3em 0 .22em;white-space:nowrap;overflow-x:auto}.lead{font-size:clamp(17px,2.2vw,21px);color:var(--muted);margin:0;white-space:nowrap;overflow-x:auto}.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:22px}
.planner,.card,.app-card{background:rgba(255,255,255,.97);border:1px solid var(--line);border-radius:26px;box-shadow:var(--shadow)}.planner{padding:clamp(20px,4vw,36px);margin:16px auto 30px}.planner h2,.card h2,.app-card h2{font-size:clamp(24px,3.6vw,34px);line-height:1.14;margin:0;white-space:nowrap;overflow-x:auto}.intro{color:var(--muted);white-space:nowrap;overflow-x:auto}
.controls{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:22px}.field{min-width:0}.field label{display:block;font-size:13px;font-weight:850;color:var(--navy);margin-bottom:6px;white-space:nowrap;overflow-x:auto}select,input,button{font:inherit}select,input[type=number]{width:100%;min-height:46px;border:1px solid #cbd6e3;border-radius:13px;background:#fff;color:var(--ink);padding:9px 11px}.toggle{display:flex;align-items:center;gap:10px;border:1px solid var(--line);border-radius:14px;padding:11px 13px;background:#fff;font-weight:760;white-space:nowrap;overflow-x:auto}.toggle input{inline-size:20px;block-size:20px;flex:0 0 auto}.button{border:0;border-radius:999px;background:linear-gradient(135deg,var(--navy),var(--blue));color:#fff;text-decoration:none;font-weight:850;padding:11px 17px;cursor:pointer;white-space:nowrap;box-shadow:0 9px 22px rgba(35,70,111,.2)}
.results{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:11px;margin-top:22px}.result{background:var(--soft);border:1px solid #cbdcf0;border-radius:17px;padding:14px;min-width:0}.result strong,.result span{display:block;white-space:nowrap;overflow-x:auto}.result strong{font-size:12px;color:#456788;text-transform:uppercase;letter-spacing:.04em}.result span{font-size:15px;color:#2e4b68;font-weight:760;margin-top:5px}.note{background:var(--warn);border:1px solid #ead9a7;border-radius:16px;padding:13px 15px;margin:14px 0 0;white-space:nowrap;overflow-x:auto}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:30px}.card,.app-card{padding:clamp(20px,3.5vw,30px)}.card.wide{grid-column:1/-1}.card p,.card li,.app-card p,.faq details p,.faq summary{white-space:nowrap;overflow-x:auto}.card ul,.card ol{padding-left:22px}.card li{margin:8px 0}.source-list a{overflow-wrap:anywhere}.app-card{margin:0 auto 38px;background:linear-gradient(135deg,#fbfdff,#e7f0fa)}.app-card .button{display:inline-flex;margin-top:5px}.faq{margin-bottom:30px}.faq details{border:1px solid var(--line);border-radius:15px;background:#fff;padding:11px 14px;margin-top:9px}.faq summary{font-weight:830;cursor:pointer}.faq details p{color:var(--muted)}
.footer{background:var(--navy);color:#eef4fb;text-align:center;padding:27px 0;white-space:nowrap;overflow-x:auto}
@media(max-width:960px){.controls{grid-template-columns:repeat(2,minmax(0,1fr))}.results{grid-template-columns:repeat(2,minmax(0,1fr))}.grid{grid-template-columns:1fr}.card.wide{grid-column:auto}}
@media(max-width:560px){.controls,.results{grid-template-columns:1fr}.wrap{width:min(100% - 22px,1120px)}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
@media print{.top,.hero,.controls,.button,.app-card,.footer{display:none!important}body{background:#fff}.planner,.card{box-shadow:none;break-inside:avoid}}
"""

SCRIPT = r"""
(() => {
  const config = JSON.parse(document.getElementById("screen-config").textContent);
  const form = document.getElementById("screen-planner");
  const fields = {
    measurement: document.getElementById("measurement"),
    daily_minutes: document.getElementById("daily-minutes"),
    days_per_week: document.getElementById("days-per-week"),
    block_minutes: document.getElementById("block-minutes"),
    block_days_per_week: document.getElementById("block-days"),
    block_window: document.getElementById("block-window"),
    essential_access_reviewed: document.getElementById("essential-reviewed")
  };
  const output = {
    observedHours: document.getElementById("result-observed-hours"),
    observedDays: document.getElementById("result-observed-days"),
    blockWeek: document.getElementById("result-block-week"),
    blockYear: document.getElementById("result-block-year"),
    measurement: document.getElementById("result-measurement"),
    plan: document.getElementById("result-plan")
  };

  function round(value, digits = 1) {
    const factor = 10 ** digits;
    return Math.round(value * factor) / factor;
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

  function integerValue(input, name) {
    if (!Object.prototype.hasOwnProperty.call(input, name)) {
      throw new TypeError(`${name} is required.`);
    }
    const value = input[name];
    const schema = config.inputSchema.properties[name];
    if (!Number.isInteger(value)) {
      throw new TypeError(`${name} must be an integer.`);
    }
    if (schema.enum && !schema.enum.includes(value)) {
      throw new RangeError(`${name} is not a supported value.`);
    }
    if ((schema.minimum !== undefined && value < schema.minimum) ||
        (schema.maximum !== undefined && value > schema.maximum)) {
      throw new RangeError(`${name} is outside the supported range.`);
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
    const measurement = enumValue(input, "measurement");
    const dailyMinutes = integerValue(input, "daily_minutes");
    const daysPerWeek = integerValue(input, "days_per_week");
    const blockMinutes = integerValue(input, "block_minutes");
    const blockDays = integerValue(input, "block_days_per_week");
    const blockWindow = enumValue(input, "block_window");
    const essentialReviewed = booleanValue(input, "essential_access_reviewed");
    if ((blockMinutes === 0) !== (blockDays === 0)) {
      throw new RangeError(
        "block_minutes and block_days_per_week must both be zero or both be positive.");
    }
    const annualObservedMinutes = dailyMinutes * daysPerWeek / 7 * 365;
    const weeklyScheduledBlockMinutes = blockMinutes * blockDays;
    const annualScheduledBlockMinutes = weeklyScheduledBlockMinutes * 52;
    return {
      selected_inputs: {
        measurement,
        measurement_label: config.labels.measurement[measurement],
        daily_minutes: dailyMinutes,
        days_per_week: daysPerWeek,
        block_minutes: blockMinutes,
        block_days_per_week: blockDays,
        block_window: blockWindow,
        block_window_label: config.labels.block_window[blockWindow],
        essential_access_reviewed: essentialReviewed
      },
      observed_pattern_annual_equivalent: {
        formula: "daily_minutes * days_per_week / 7 * 365",
        minutes: round(annualObservedMinutes, 2),
        hours: round(annualObservedMinutes / 60),
        full_24_hour_days: round(annualObservedMinutes / 1440),
        source_is_self_entered_not_device_reading: true
      },
      scheduled_block_plan: {
        formula: "block_minutes * block_days_per_week * 52",
        minutes_per_week: weeklyScheduledBlockMinutes,
        minutes_across_52_weeks: annualScheduledBlockMinutes,
        hours_across_52_weeks: round(annualScheduledBlockMinutes / 60),
        is_not_a_saved_time_or_outcome_claim: true
      },
      reversible_preflight: [
        essentialReviewed ? config.essentialYes : config.essentialNo,
        ...config.windowSteps[blockWindow]
      ],
      observed_pattern_boundary: config.observedBoundary,
      scheduled_block_boundary: config.blockBoundary,
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

  function render() {
    const result = plan({
      measurement: fields.measurement.value,
      daily_minutes: Number(fields.daily_minutes.value),
      days_per_week: Number(fields.days_per_week.value),
      block_minutes: Number(fields.block_minutes.value),
      block_days_per_week: Number(fields.block_days_per_week.value),
      block_window: fields.block_window.value,
      essential_access_reviewed: fields.essential_access_reviewed.checked
    });
    output.observedHours.textContent =
      String(result.observed_pattern_annual_equivalent.hours);
    output.observedDays.textContent =
      String(result.observed_pattern_annual_equivalent.full_24_hour_days);
    output.blockWeek.textContent =
      String(result.scheduled_block_plan.minutes_per_week);
    output.blockYear.textContent =
      String(result.scheduled_block_plan.hours_across_52_weeks);
    output.measurement.textContent =
      result.selected_inputs.measurement_label;
    output.plan.textContent = result.reversible_preflight.join(" ");
  }

  async function registerWebMcp() {
    if (!document.modelContext?.registerTool) return;
    await document.modelContext.registerTool({
      name: "plan_private_screen_time_block",
      description: config.toolDescription,
      inputSchema: config.inputSchema,
      annotations: {readOnlyHint: true, untrustedContentHint: false},
      execute: async (input) => {
        const plan = validateInput(input);
        const result = {
          result_type: "private_screen_time_and_block_plan",
          screen_time_apps_accounts_contacts_not_accessed: true,
          scheduled_block_is_not_saved_time: true,
          no_focus_health_or_productivity_prediction: true,
          plan,
          preflight_checklist: config.preflightChecklist,
          optional_free_planner: config.freePlanner,
          official_sources: config.officialSources,
          webmcp_preview_source: config.webmcpSource
        };
        if (config.optionalApp) {
          result.optional_lockhour_pro = config.optionalApp;
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


def options(values: dict[object, str]) -> str:
    return "".join(
        f'<option value="{html.escape(str(key), quote=True)}">{html.escape(label)}</option>'
        for key, label in values.items()
    )


def webmcp_input_schema(locale: str) -> dict[str, object]:
    if locale not in COPY:
        raise ValueError(f"unsupported locale: {locale}")
    return {
        "type": "object",
        "properties": {
            "measurement": {
                "type": "string",
                "enum": list(MEASUREMENTS),
            },
            "daily_minutes": {
                "type": "integer",
                "minimum": 0,
                "maximum": 1440,
            },
            "days_per_week": {
                "type": "integer",
                "minimum": 1,
                "maximum": 7,
            },
            "block_minutes": {
                "type": "integer",
                "enum": list(BLOCK_MINUTES),
            },
            "block_days_per_week": {
                "type": "integer",
                "minimum": 0,
                "maximum": 7,
            },
            "block_window": {
                "type": "string",
                "enum": list(BLOCK_WINDOWS),
            },
            "essential_access_reviewed": {"type": "boolean"},
        },
        "required": [
            "measurement",
            "daily_minutes",
            "days_per_week",
            "block_minutes",
            "block_days_per_week",
            "block_window",
            "essential_access_reviewed",
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
    alternate_links = "\n".join(
        f'<link rel="alternate" hreflang="{html.escape(alt, quote=True)}" '
        f'href="{html.escape(canonical(alt), quote=True)}">'
        for alt in ALT_LOCALES
    )
    sources = (
        APPLE_SCREEN_TIME,
        APPLE_SCREEN_TIME_SCHEDULES,
        APPLE_FOCUS,
    )
    source_items = "".join(
        f'<li><a href="{html.escape(source, quote=True)}" rel="noopener">'
        f"{html.escape(label)}</a></li>"
        for label, source in zip(t["source_labels"], sources, strict=True)
    )
    preflight_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in t["preflight"]
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
        appstore_url(APP_KEY, f"iag_screen_plan_{locale.lower()}")
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
            "measurement": t["measurement_options"],
            "block_window": t["window_options"],
        },
        "windowSteps": t["window_steps"],
        "essentialYes": t["essential_yes"],
        "essentialNo": t["essential_no"],
        "observedBoundary": t["observed_boundary"],
        "blockBoundary": t["block_boundary"],
        "scopeBoundary": t["scope_text"],
        "preflightChecklist": t["preflight"],
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
        "applicationCategory": "ProductivityApplication",
        "operatingSystem": "Any",
        "isAccessibleForFree": True,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "featureList": [
            "No Screen Time or installed-app access",
            "Transparent annual-equivalent observed-pattern math",
            "Separate scheduled-block math",
            "Essential-access preflight",
            "No saved-time, focus, health or productivity prediction",
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
{alternate_links}
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
<form id="screen-planner"><div class="controls">
<div class="field"><label for="measurement">{html.escape(t["measurement_label"])}</label><select id="measurement">{options(t["measurement_options"])}</select></div>
<div class="field"><label for="daily-minutes">{html.escape(t["daily_label"])}</label><input id="daily-minutes" type="number" min="0" max="1440" step="1" value="0"></div>
<div class="field"><label for="days-per-week">{html.escape(t["days_label"])}</label><input id="days-per-week" type="number" min="1" max="7" step="1" value="1"></div>
<div class="field"><label for="block-minutes">{html.escape(t["block_minutes_label"])}</label><select id="block-minutes">{options(t["block_minutes_options"])}</select></div>
<div class="field"><label for="block-days">{html.escape(t["block_days_label"])}</label><input id="block-days" type="number" min="0" max="7" step="1" value="0"></div>
<div class="field"><label for="block-window">{html.escape(t["window_label"])}</label><select id="block-window">{options(t["window_options"])}</select></div>
<label class="toggle"><input id="essential-reviewed" type="checkbox">{html.escape(t["essential_label"])}</label>
</div><p><button class="button" type="submit">{html.escape(t["update"])}</button></p></form>
<div class="results"><div class="result"><strong>{html.escape(t["result_observed_hours"])}</strong><span id="result-observed-hours"></span></div><div class="result"><strong>{html.escape(t["result_observed_days"])}</strong><span id="result-observed-days"></span></div><div class="result"><strong>{html.escape(t["result_block_week"])}</strong><span id="result-block-week"></span></div><div class="result"><strong>{html.escape(t["result_block_year"])}</strong><span id="result-block-year"></span></div><div class="result"><strong>{html.escape(t["result_measurement"])}</strong><span id="result-measurement"></span></div></div>
<p class="note">{html.escape(t["observed_boundary"])}</p><p class="note">{html.escape(t["block_boundary"])}</p><p class="note"><strong>{html.escape(t["result_plan"])}:</strong> <span id="result-plan"></span></p></section>
<section class="wrap grid"><article class="card"><h2>{html.escape(t["preflight_title"])}</h2><ol>{preflight_items}</ol></article><article class="card"><h2>{html.escape(t["scope_title"])}</h2><p>{html.escape(t["scope_text"])}</p></article><article class="card wide"><h2>{html.escape(t["sources_title"])}</h2><p>{html.escape(t["sources_intro"])}</p><ul class="source-list">{source_items}</ul><p><a href="{WEBMCP_SOURCE}" rel="noopener">{html.escape(t["webmcp_source"])}</a></p></article></section>
<section class="wrap card faq"><h2>{html.escape(t["faq_title"])}</h2>{faq}</section>
{app_card}
</main>
<footer class="footer"><div class="wrap">{html.escape(t["footer"])}</div></footer>
<script type="application/json" id="screen-config">{config_json}</script>
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
        r'private-daily-checklist-planner">.*?</article>)',
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
        print(f"screen time block planner -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
