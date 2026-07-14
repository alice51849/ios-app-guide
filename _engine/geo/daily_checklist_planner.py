#!/usr/bin/env python3
"""Generate a bilingual, private daily checklist planning tool."""

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
SLUG = "private-daily-checklist-planner"
APP_KEY = "mochi"
APP_ID = "6785004775"
CONTENT_DATE = "2026-07-15"
APPLE_REMINDERS = (
    "https://support.apple.com/guide/iphone/"
    "get-started-with-reminders-iphc7880ecd6/ios"
)
APPLE_CREATE_REMINDERS = (
    "https://support.apple.com/guide/iphone/"
    "create-reminders-iph88463e18/ios"
)
APPLE_WATCH_REMINDERS = (
    "https://support.apple.com/guide/watch/"
    "make-and-view-lists-apdf10efb1bf/watchos"
)
WEBMCP_SOURCE = "https://developer.chrome.com/docs/ai/webmcp/imperative-api"

CONTEXTS = ("mixed-day", "work-study", "home", "errands", "routine")
AVAILABLE_MINUTES = (15, 30, 60, 120)
STARTING_STYLES = ("priority-first", "shortest-first", "due-time-first")
REPEAT_PATTERNS = ("none", "daily", "weekdays", "weekly")

COPY = {
    "en": {
        "title": "Private Daily Checklist Planner | No Task Text Required",
        "description": (
            "Turn a task count and available time into transparent checklist structure "
            "without entering task text, names, dates, accounts or calendar data."
        ),
        "tools": "Free tools",
        "switch": "繁體中文",
        "eyebrow": "Free · local math · no task text",
        "heading": "Private daily checklist planner",
        "lead": (
            "Choose only counts and planning preferences. The browser divides the available "
            "window transparently and returns a blank structure you can fill elsewhere."
        ),
        "badges": (
            "No task names or notes",
            "No account or calendar access",
            "No upload or storage",
            "No productivity promise",
        ),
        "planner": "Shape today's checklist",
        "planner_intro": (
            "The equal-share calculation is planning math, not a prediction of how long "
            "any real task will take."
        ),
        "context_label": "List context",
        "context_options": {
            "mixed-day": "Mixed day",
            "work-study": "Work or study",
            "home": "Home",
            "errands": "Errands",
            "routine": "Routine",
        },
        "minutes_label": "Available window",
        "minutes_options": {
            15: "15 minutes",
            30: "30 minutes",
            60: "60 minutes",
            120: "120 minutes",
        },
        "count_label": "Number of items",
        "style_label": "Starting style",
        "style_options": {
            "priority-first": "Most important first",
            "shortest-first": "Genuinely short items first",
            "due-time-first": "Real due times first",
        },
        "repeat_label": "Repeat pattern",
        "repeat_options": {
            "none": "No repeat",
            "daily": "Daily",
            "weekdays": "Weekdays",
            "weekly": "Weekly",
        },
        "carryover_label": "One or more items are carried over",
        "update": "Build blank checklist plan",
        "context_notes": {
            "mixed-day": (
                "Add a short context label when you transfer each item, so unrelated work "
                "does not look like one continuous block."
            ),
            "work-study": (
                "Separate outcome work from messages, filing and other administration when "
                "you fill the blank slots."
            ),
            "home": (
                "Separate items that must happen today from maintenance that can move without harm."
            ),
            "errands": (
                "When you fill the plan, group real stops by location or route before choosing order."
            ),
            "routine": (
                "Keep genuinely repeating actions separate from one-off items before setting a cadence."
            ),
        },
        "style_steps": {
            "priority-first": (
                "Choose one item that matters most inside this planning window and place it in the first slot.",
                "Place up to two next items after it, then keep every remaining item visibly later.",
            ),
            "shortest-first": (
                "Identify up to two items that are genuinely short; do not guess from the title alone.",
                "Place those first, then keep one important item visible before the later group.",
            ),
            "due-time-first": (
                "Verify actual external due times and place only truly time-bound items first.",
                "If no real due time exists, choose one important item rather than inventing urgency.",
            ),
        },
        "repeat_notes": {
            "none": "Leave repeat off; review the item again only when it is genuinely needed.",
            "daily": "Use a daily repeat only for an action that truly belongs every day.",
            "weekdays": "Use a weekday repeat only when weekends are intentionally excluded.",
            "weekly": "Choose a specific weekly review point rather than silently duplicating the item.",
        },
        "carryover_yes": (
            "Review each carried item: keep it today, move it with a reason, or remove it. "
            "Do not roll everything forward automatically."
        ),
        "carryover_no": (
            "Start with today's blank structure; do not prefill old items that are no longer relevant."
        ),
        "load_notes": {
            "tight": (
                "The equal share is under 5 minutes per item. Treat this as a capture list "
                "and move unrealistic items to the later group."
            ),
            "brief": (
                "The equal share is 5–14 minutes per item. Verify each real item before "
                "assuming it fits."
            ),
            "open": (
                "The equal share is at least 15 minutes per item. Real tasks can still vary "
                "widely, so revise the count when needed."
            ),
        },
        "structure_labels": {
            "first": "Start-here slots",
            "next": "Next slots",
            "later": "Later or optional slots",
        },
        "result_per_item": "Equal-share minutes per item",
        "result_remainder": "Unallocated minutes",
        "result_structure": "Blank list structure",
        "result_setup": "Setup sequence",
        "result_repeat": "Repeat decision",
        "result_carryover": "Carryover decision",
        "result_boundary": (
            "This plan uses only integer division of the selected window. It does not know "
            "task difficulty, interruptions, deadlines, accessibility needs or actual duration."
        ),
        "review_title": "Five checks before transferring real tasks",
        "review_checks": (
            "Keep task text in the checklist system you choose, not in this planning page.",
            "Confirm real deadlines before ordering anything as urgent.",
            "Break a large item elsewhere if it cannot fit the selected window.",
            "Use repeat only when the action truly recurs at that cadence.",
            "At the end of the window, review unfinished items instead of silently carrying all of them forward.",
        ),
        "sources_title": "Official feature context, not productivity evidence",
        "sources_intro": (
            "Apple documents creating checklists and reminders on iPhone and marking list "
            "items complete on Apple Watch. These product guides do not prove that a specific "
            "list structure improves productivity."
        ),
        "source_labels": (
            "Apple: get started with Reminders on iPhone",
            "Apple: create reminders on iPhone",
            "Apple: make and view Reminders lists on Apple Watch",
        ),
        "webmcp_source": "Chrome WebMCP imperative API preview (subject to change)",
        "webmcp_description": (
            "Build a private blank daily checklist plan from bounded context, available-time, "
            "item-count, starting-style, repeat-pattern and carryover inputs. Return transparent "
            "equal-share math and structure without accepting task text, names, dates, accounts "
            "or calendar data, and without predicting duration or productivity."
        ),
        "app_title": "Want a cozy place to keep the real list?",
        "app_text": (
            "Mochi is optional. Its current App Store listing describes simple checklists, "
            "reminders, daily planning, habits, routines, notes, grocery lists, Home Screen "
            "widgets, Apple Watch access and 100 skins, and says it is free with no ads. "
            "Check the current listing for exact availability and features. This planner "
            "works without the app."
        ),
        "app_cta": "View Mochi on the App Store",
        "faq_title": "Checklist planning questions",
        "faq": (
            (
                "Does this page receive my task names?",
                "No. It accepts only bounded counts and planning choices, never task text, dates or calendar contents.",
            ),
            (
                "Are equal-share minutes a task-duration estimate?",
                "No. They are transparent division of the chosen window and item count.",
            ),
            (
                "Why separate later items?",
                "The blank groups keep every captured item visible without pretending all items fit the active window.",
            ),
            (
                "Does this guarantee I will finish the list?",
                "No. It makes no productivity, health or performance promise.",
            ),
        ),
        "footer": "Private planning math only · no task text · revise with real constraints",
        "index_title": "Private Daily Checklist Planner",
        "index_description": (
            "Turn available minutes and an item count into a blank daily structure without "
            "entering tasks, dates or account data."
        ),
    },
    "zh-Hant": {
        "title": "私密每日清單規劃器｜不用輸入任務內容",
        "description": "只用項目數與可用時間建立透明清單結構，不輸入任務文字、姓名、日期、帳號或行事曆資料。",
        "tools": "免費工具",
        "switch": "English",
        "eyebrow": "免費 · 本機運算 · 不輸入任務文字",
        "heading": "私密每日清單規劃器",
        "lead": "只選擇數量與規劃偏好；瀏覽器會透明分配可用時間，回傳可在其他地方填寫的空白結構。",
        "badges": (
            "不輸入任務名稱或筆記",
            "不存取帳號或行事曆",
            "不上傳或儲存",
            "不保證提升效率",
        ),
        "planner": "安排今天的清單結構",
        "planner_intro": "平均分配只是規劃算式，不是任何真實任務的時間預測。",
        "context_label": "清單情境",
        "context_options": {
            "mixed-day": "混合的一天",
            "work-study": "工作或學習",
            "home": "居家",
            "errands": "外出辦事",
            "routine": "固定流程",
        },
        "minutes_label": "可用時段",
        "minutes_options": {
            15: "15 分鐘",
            30: "30 分鐘",
            60: "60 分鐘",
            120: "120 分鐘",
        },
        "count_label": "項目數",
        "style_label": "起始方式",
        "style_options": {
            "priority-first": "最重要項目優先",
            "shortest-first": "真正較短的項目優先",
            "due-time-first": "真實到期時間優先",
        },
        "repeat_label": "重複週期",
        "repeat_options": {
            "none": "不重複",
            "daily": "每天",
            "weekdays": "平日",
            "weekly": "每週",
        },
        "carryover_label": "有一項以上從前一天延續",
        "update": "建立空白清單規劃",
        "context_notes": {
            "mixed-day": "轉移每個項目時加上簡短情境標記，避免把無關工作看成一個連續區塊。",
            "work-study": "填寫空白位置時，把成果型工作和訊息、歸檔等行政項目分開。",
            "home": "把今天必須完成的項目，和不影響結果、可以移動的維護項目分開。",
            "errands": "填入清單後，先依真實地點或路線分組，再決定順序。",
            "routine": "設定週期前，把真正會重複的行動和一次性項目分開。",
        },
        "style_steps": {
            "priority-first": (
                "選一個在這段時間內最重要的項目，放進第一個位置。",
                "後面最多放兩個下一步，其餘項目清楚保留在稍後群組。",
            ),
            "shortest-first": (
                "找出最多兩個確實較短的項目，不可只看標題猜測。",
                "先放這些短項目，再讓一個重要項目保持可見，最後才是稍後群組。",
            ),
            "due-time-first": (
                "核對真實的外部到期時間，只把確實有時限的項目排在前面。",
                "若沒有真實期限，就選一個重要項目，不要自行製造急迫感。",
            ),
        },
        "repeat_notes": {
            "none": "關閉重複；只有真的再次需要時才重新檢視。",
            "daily": "只有確實每天都要做的行動才設定每天重複。",
            "weekdays": "只有刻意排除週末時，才設定平日重複。",
            "weekly": "選一個明確的每週檢視時間，不要默默複製項目。",
        },
        "carryover_yes": "逐項檢查延續項目：今天保留、附理由改期，或直接移除；不要全部自動滾動。",
        "carryover_no": "從今天的空白結構開始，不要預先填入已經不相關的舊項目。",
        "load_notes": {
            "tight": "每項平均不到 5 分鐘；請把它視為收集清單，並把不實際的項目移到稍後群組。",
            "brief": "每項平均為 5–14 分鐘；請先核對真實項目，不要直接假設一定放得下。",
            "open": "每項平均至少 15 分鐘；真實任務仍可能差異很大，需要時就調整項目數。",
        },
        "structure_labels": {
            "first": "立即開始位置",
            "next": "下一步位置",
            "later": "稍後或選做位置",
        },
        "result_per_item": "每項平均分配分鐘",
        "result_remainder": "未分配分鐘",
        "result_structure": "空白清單結構",
        "result_setup": "設定順序",
        "result_repeat": "重複決策",
        "result_carryover": "延續項目決策",
        "result_boundary": (
            "本規劃只對選定時段做整數除法；它不知道任務難度、中斷、期限、無障礙需求或真實所需時間。"
        ),
        "review_title": "轉入真實任務前先確認五件事",
        "review_checks": (
            "把任務文字留在你選擇的清單系統，不要輸入這個規劃頁。",
            "把任何項目標成急迫之前，先確認真實期限。",
            "大型項目若無法放進選定時段，請在其他地方拆分。",
            "只有行動真的依該週期重複時才設定重複。",
            "時段結束後逐項檢查未完成內容，不要全部默默延續。",
        ),
        "sources_title": "官方功能背景，不是效率證據",
        "sources_intro": (
            "Apple 說明如何在 iPhone 建立檢查清單與提醒事項，以及如何在 Apple Watch 完成清單項目；"
            "這些產品指南並未證明某種清單結構能提升效率。"
        ),
        "source_labels": (
            "Apple：開始使用 iPhone 提醒事項",
            "Apple：在 iPhone 建立提醒事項",
            "Apple：在 Apple Watch 建立及查看提醒事項清單",
        ),
        "webmcp_source": "Chrome WebMCP 命令式 API 預覽（規格可能變動）",
        "webmcp_description": (
            "只用有界的情境、可用時間、項目數、起始方式、重複週期及延續選項建立私密每日空白清單；"
            "回傳透明平均分配與結構，不接收任務文字、姓名、日期、帳號或行事曆資料，也不預測時間或效率。"
        ),
        "app_title": "想用療癒的地方保存真實清單？",
        "app_text": (
            "Mochi 是選用工具；目前 App Store 頁面說明包含簡易清單、提醒事項、每日規劃、習慣、"
            "固定流程、筆記、購物清單、主畫面小工具、Apple Watch 與 100 款外觀，並標示免費、"
            "無廣告。供應地區與確切功能請以目前商店頁為準；這個規劃器不需 App 也能使用。"
        ),
        "app_cta": "在 App Store 查看 Mochi",
        "faq_title": "清單規劃常見問題",
        "faq": (
            (
                "這個網頁會收到我的任務名稱嗎？",
                "不會。它只接受有界的數量與規劃選項，不接收任務文字、日期或行事曆內容。",
            ),
            (
                "平均分鐘是任務時間估算嗎？",
                "不是。它只是把選定時段除以項目數的透明算式。",
            ),
            (
                "為什麼要分出稍後項目？",
                "空白分組會保留所有已收集項目，但不假裝每個項目都放得進目前時段。",
            ),
            (
                "這能保證完成清單嗎？",
                "不能。本工具不承諾效率、健康或表現結果。",
            ),
        ),
        "footer": "只做私密規劃算式 · 不輸入任務文字 · 依真實限制調整",
        "index_title": "私密每日清單規劃器",
        "index_description": "只用可用分鐘與項目數建立空白每日結構，不輸入任務、日期或帳號資料。",
    },
}

STYLE = r"""
:root{--ink:#263126;--muted:#667066;--line:#dfe7dc;--paper:#fff;--bg:#f4f8ef;--green:#426443;--leaf:#729d62;--peach:#f8e6d3;--soft:#ebf4e6;--warn:#fff6d9;--shadow:0 22px 60px rgba(53,78,48,.12)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 90% 0,#fff 0,var(--bg) 55%,#e5eedc 100%);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Noto Sans TC",sans-serif;line-height:1.62}
a{color:#46723f}.wrap{width:min(1120px,calc(100% - 30px));margin:auto}.top{position:sticky;top:0;z-index:8;background:#fffffff2;border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:850;white-space:nowrap}.links{display:flex;gap:15px;overflow-x:auto}
.hero{padding:64px 0 30px}.eyebrow,.badge{display:inline-flex;border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 12px;font-size:13px;font-weight:850;color:var(--green);white-space:nowrap}.hero h1,h2{font-family:ui-serif,Georgia,"Noto Serif TC",serif}.hero h1{font-size:clamp(34px,6vw,62px);line-height:1.04;letter-spacing:-.035em;margin:.3em 0 .22em;white-space:nowrap;overflow-x:auto}.lead{font-size:clamp(17px,2.2vw,21px);color:var(--muted);margin:0;white-space:nowrap;overflow-x:auto}.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:22px}
.planner,.card,.app-card{background:rgba(255,255,255,.97);border:1px solid var(--line);border-radius:26px;box-shadow:var(--shadow)}.planner{padding:clamp(20px,4vw,36px);margin:16px auto 30px}.planner h2,.card h2,.app-card h2{font-size:clamp(24px,3.6vw,34px);line-height:1.14;margin:0;white-space:nowrap;overflow-x:auto}.intro{color:var(--muted);white-space:nowrap;overflow-x:auto}
.controls{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:22px}.field{min-width:0}.field label{display:block;font-size:13px;font-weight:850;color:var(--green);margin-bottom:6px;white-space:nowrap;overflow-x:auto}select,input,button{font:inherit}select,input[type=number]{width:100%;min-height:46px;border:1px solid #cddac8;border-radius:13px;background:#fff;color:var(--ink);padding:9px 11px}.toggle{display:flex;align-items:center;gap:10px;border:1px solid var(--line);border-radius:14px;padding:11px 13px;background:#fff;font-weight:760;white-space:nowrap;overflow-x:auto}.toggle input{inline-size:20px;block-size:20px;flex:0 0 auto}.button{border:0;border-radius:999px;background:linear-gradient(135deg,var(--green),var(--leaf));color:#fff;text-decoration:none;font-weight:850;padding:11px 17px;cursor:pointer;white-space:nowrap;box-shadow:0 9px 22px rgba(66,100,67,.2)}
.results{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:11px;margin-top:22px}.result{background:var(--soft);border:1px solid #cfe1c8;border-radius:17px;padding:14px;min-width:0}.result strong,.result span{display:block;white-space:nowrap;overflow-x:auto}.result strong{font-size:12px;color:#4f704b;text-transform:uppercase;letter-spacing:.04em}.result span{font-size:15px;color:#334732;font-weight:760;margin-top:5px}.note{background:var(--warn);border:1px solid #ead9a7;border-radius:16px;padding:13px 15px;margin:14px 0 0;white-space:nowrap;overflow-x:auto}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:30px}.card,.app-card{padding:clamp(20px,3.5vw,30px)}.card p,.card li,.app-card p,.faq details p,.faq summary{white-space:nowrap;overflow-x:auto}.card ul,.card ol{padding-left:22px}.card li{margin:8px 0}.source-list a{overflow-wrap:anywhere}.app-card{margin:0 auto 38px;background:linear-gradient(135deg,#fffdf9,var(--peach))}.app-card .button{display:inline-flex;margin-top:5px}.faq{margin-bottom:30px}.faq details{border:1px solid var(--line);border-radius:15px;background:#fff;padding:11px 14px;margin-top:9px}.faq summary{font-weight:830;cursor:pointer}.faq details p{color:var(--muted)}
.footer{background:var(--green);color:#f2f8ef;text-align:center;padding:27px 0;white-space:nowrap;overflow-x:auto}
@media(max-width:900px){.controls,.results{grid-template-columns:1fr}.grid{grid-template-columns:1fr}}
@media(max-width:560px){.wrap{width:min(100% - 22px,1120px)}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
@media print{.top,.hero,.controls,.button,.app-card,.footer{display:none!important}body{background:#fff}.planner,.card{box-shadow:none;break-inside:avoid}}
"""

SCRIPT = r"""
(() => {
  const config = JSON.parse(document.getElementById("checklist-config").textContent);
  const form = document.getElementById("checklist-planner");
  const fields = {
    context: document.getElementById("context"),
    available_minutes: document.getElementById("available-minutes"),
    item_count: document.getElementById("item-count"),
    starting_style: document.getElementById("starting-style"),
    repeat_pattern: document.getElementById("repeat-pattern"),
    has_carryover: document.getElementById("has-carryover")
  };
  const output = {
    perItem: document.getElementById("result-per-item"),
    remainder: document.getElementById("result-remainder"),
    structure: document.getElementById("result-structure"),
    setup: document.getElementById("result-setup"),
    repeat: document.getElementById("result-repeat"),
    carryover: document.getElementById("result-carryover"),
    load: document.getElementById("result-load")
  };

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
    if ((schema.minimum && value < schema.minimum) ||
        (schema.maximum && value > schema.maximum)) {
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
    const context = enumValue(input, "context");
    const availableMinutes = integerValue(input, "available_minutes");
    const itemCount = integerValue(input, "item_count");
    const startingStyle = enumValue(input, "starting_style");
    const repeatPattern = enumValue(input, "repeat_pattern");
    const hasCarryover = booleanValue(input, "has_carryover");
    const minutesPerItem = Math.floor(availableMinutes / itemCount);
    const unallocatedMinutes = availableMinutes - minutesPerItem * itemCount;
    const firstSlots = 1;
    const nextSlots = Math.min(2, Math.max(0, itemCount - firstSlots));
    const laterSlots = Math.max(0, itemCount - firstSlots - nextSlots);
    const loadKey = minutesPerItem < 5 ? "tight" :
      (minutesPerItem < 15 ? "brief" : "open");
    return {
      selected_inputs: {
        context,
        context_label: config.labels.context[context],
        available_minutes: availableMinutes,
        item_count: itemCount,
        starting_style: startingStyle,
        starting_style_label: config.labels.starting_style[startingStyle],
        repeat_pattern: repeatPattern,
        repeat_pattern_label: config.labels.repeat_pattern[repeatPattern],
        has_carryover: hasCarryover
      },
      transparent_time_math: {
        formula: "floor(available_minutes / item_count)",
        equal_share_minutes_per_item: minutesPerItem,
        unallocated_minutes: unallocatedMinutes,
        is_duration_prediction: false
      },
      blank_list_structure: {
        start_here_slots: firstSlots,
        next_slots: nextSlots,
        later_or_optional_slots: laterSlots
      },
      setup_sequence: [
        config.contextNotes[context],
        ...config.styleSteps[startingStyle]
      ],
      repeat_decision: config.repeatNotes[repeatPattern],
      carryover_decision: hasCarryover ?
        config.carryoverYes : config.carryoverNo,
      load_boundary: config.loadNotes[loadKey],
      planning_boundary: config.resultBoundary
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
      context: fields.context.value,
      available_minutes: Number(fields.available_minutes.value),
      item_count: Number(fields.item_count.value),
      starting_style: fields.starting_style.value,
      repeat_pattern: fields.repeat_pattern.value,
      has_carryover: fields.has_carryover.checked
    });
    output.perItem.textContent =
      String(result.transparent_time_math.equal_share_minutes_per_item);
    output.remainder.textContent =
      String(result.transparent_time_math.unallocated_minutes);
    const slots = result.blank_list_structure;
    output.structure.textContent =
      `${config.structureLabels.first}: ${slots.start_here_slots}. ` +
      `${config.structureLabels.next}: ${slots.next_slots}. ` +
      `${config.structureLabels.later}: ${slots.later_or_optional_slots}.`;
    output.setup.textContent = result.setup_sequence.join(" ");
    output.repeat.textContent = result.repeat_decision;
    output.carryover.textContent = result.carryover_decision;
    output.load.textContent = `${result.load_boundary} ${result.planning_boundary}`;
  }

  async function registerWebMcp() {
    if (!document.modelContext?.registerTool) return;
    await document.modelContext.registerTool({
      name: "plan_private_daily_checklist",
      description: config.toolDescription,
      inputSchema: config.inputSchema,
      annotations: {readOnlyHint: true, untrustedContentHint: false},
      execute: async (input) => {
        const checklist = validateInput(input);
        const result = {
          result_type: "private_daily_checklist_plan",
          task_text_not_received_or_processed: true,
          no_account_calendar_or_storage_access: true,
          not_a_duration_or_productivity_prediction: true,
          checklist,
          transfer_review_checklist: config.reviewChecklist,
          optional_free_planner: config.freePlanner,
          official_sources: config.officialSources,
          webmcp_preview_source: config.webmcpSource
        };
        if (config.optionalApp) {
          result.optional_mochi = config.optionalApp;
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
    prefix = "zh-Hant/" if locale == "zh-Hant" else ""
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
            "context": {"type": "string", "enum": list(CONTEXTS)},
            "available_minutes": {
                "type": "integer",
                "enum": list(AVAILABLE_MINUTES),
            },
            "item_count": {
                "type": "integer",
                "minimum": 1,
                "maximum": 12,
            },
            "starting_style": {
                "type": "string",
                "enum": list(STARTING_STYLES),
            },
            "repeat_pattern": {
                "type": "string",
                "enum": list(REPEAT_PATTERNS),
            },
            "has_carryover": {"type": "boolean"},
        },
        "required": [
            "context",
            "available_minutes",
            "item_count",
            "starting_style",
            "repeat_pattern",
            "has_carryover",
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
    prefix = "zh-Hant/" if locale == "zh-Hant" else ""
    home = f"{SITE}/{prefix}index.html"
    tools = f"{SITE}/{prefix}tools/index.html"
    sources = (
        APPLE_REMINDERS,
        APPLE_CREATE_REMINDERS,
        APPLE_WATCH_REMINDERS,
    )
    source_items = "".join(
        f'<li><a href="{html.escape(source, quote=True)}" rel="noopener">'
        f"{html.escape(label)}</a></li>"
        for label, source in zip(t["source_labels"], sources, strict=True)
    )
    review_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in t["review_checks"]
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
        appstore_url(APP_KEY, f"iag_checklist_plan_{locale.lower()}")
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
            "context": t["context_options"],
            "starting_style": t["style_options"],
            "repeat_pattern": t["repeat_options"],
        },
        "contextNotes": t["context_notes"],
        "styleSteps": t["style_steps"],
        "repeatNotes": t["repeat_notes"],
        "carryoverYes": t["carryover_yes"],
        "carryoverNo": t["carryover_no"],
        "loadNotes": t["load_notes"],
        "structureLabels": t["structure_labels"],
        "resultBoundary": t["result_boundary"],
        "reviewChecklist": t["review_checks"],
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
            "No task text, names or dates",
            "No account or calendar access",
            "Transparent equal-share time math",
            "Blank checklist structure",
            "No productivity or duration prediction",
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
<link rel="alternate" hreflang="{locale}" href="{url}">
<link rel="alternate" hreflang="{other}" href="{alternate}">
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
<form id="checklist-planner"><div class="controls">
<div class="field"><label for="context">{html.escape(t["context_label"])}</label><select id="context">{options(t["context_options"])}</select></div>
<div class="field"><label for="available-minutes">{html.escape(t["minutes_label"])}</label><select id="available-minutes">{options(t["minutes_options"])}</select></div>
<div class="field"><label for="item-count">{html.escape(t["count_label"])}</label><input id="item-count" type="number" min="1" max="12" step="1" value="5"></div>
<div class="field"><label for="starting-style">{html.escape(t["style_label"])}</label><select id="starting-style">{options(t["style_options"])}</select></div>
<div class="field"><label for="repeat-pattern">{html.escape(t["repeat_label"])}</label><select id="repeat-pattern">{options(t["repeat_options"])}</select></div>
<label class="toggle"><input id="has-carryover" type="checkbox">{html.escape(t["carryover_label"])}</label>
</div><p><button class="button" type="submit">{html.escape(t["update"])}</button></p></form>
<div class="results"><div class="result"><strong>{html.escape(t["result_per_item"])}</strong><span id="result-per-item"></span></div><div class="result"><strong>{html.escape(t["result_remainder"])}</strong><span id="result-remainder"></span></div><div class="result"><strong>{html.escape(t["result_structure"])}</strong><span id="result-structure"></span></div></div>
<p class="note"><strong>{html.escape(t["result_setup"])}:</strong> <span id="result-setup"></span></p><p class="note"><strong>{html.escape(t["result_repeat"])}:</strong> <span id="result-repeat"></span></p><p class="note"><strong>{html.escape(t["result_carryover"])}:</strong> <span id="result-carryover"></span></p><p class="note" id="result-load"></p></section>
<section class="wrap grid"><article class="card"><h2>{html.escape(t["review_title"])}</h2><ol>{review_items}</ol></article><article class="card"><h2>{html.escape(t["sources_title"])}</h2><p>{html.escape(t["sources_intro"])}</p><ul class="source-list">{source_items}</ul><p><a href="{WEBMCP_SOURCE}" rel="noopener">{html.escape(t["webmcp_source"])}</a></p></article></section>
<section class="wrap card faq"><h2>{html.escape(t["faq_title"])}</h2>{faq}</section>
{app_card}
</main>
<footer class="footer"><div class="wrap">{html.escape(t["footer"])}</div></footer>
<script type="application/json" id="checklist-config">{config_json}</script>
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
        r'(<article class="card third"><h2><a href="'
        r'screen-time-calculator\.html">.*?</article>)',
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
        if locale == "zh-Hant":
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
        print(f"daily checklist planner -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
