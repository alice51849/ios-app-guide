#!/usr/bin/env python3
"""Generate a bilingual, private blurry-photo next-step guide."""

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
SLUG = "blurry-photo-diagnostic"
APP_KEY = "unblurry"
APP_ID = "6782275018"
CONTENT_DATE = "2026-07-15"
APPLE_SHOT = (
    "https://support.apple.com/guide/iphone/"
    "set-up-your-shot-iph3dc593597/ios"
)
APPLE_CAMERA_HELP = "https://support.apple.com/en-us/102514"
APPLE_SHARED_ALBUMS = "https://support.apple.com/en-us/108916"
ADOBE_ENHANCE = "https://helpx.adobe.com/camera-raw/using/enhance.html"
WEBMCP_SOURCE = "https://developer.chrome.com/docs/ai/webmcp/imperative-api"

ISSUES = (
    "motion",
    "missed-focus",
    "low-light-noise",
    "low-resolution-crop",
    "compressed-copy",
)
INTENDED_USES = ("casual-memory", "print", "work-profile")
IMPORTANT_DETAILS = ("overall-scene", "face", "text")

COPY = {
    "en": {
        "title": "Private Blurry Photo Next-Step Guide | No Photo Upload",
        "description": (
            "Choose visible symptoms to get conservative next steps for motion, missed "
            "focus, low-light noise, a heavy crop or a compressed copy without uploading "
            "a photo."
        ),
        "tools": "Free tools",
        "switch": "繁體中文",
        "eyebrow": "Free · no photo input · no recovery score",
        "heading": "Private blurry photo next-step guide",
        "lead": (
            "Describe what you already observe. The page suggests a cautious sequence, "
            "but it never receives a photo and cannot diagnose or promise restoration."
        ),
        "badges": (
            "No image or file input",
            "No upload or cloud request",
            "No recovery percentage",
            "No guarantee of restored detail",
        ),
        "planner": "Describe the visible problem",
        "planner_intro": (
            "Use the closest observation. A real image can contain several causes, so "
            "treat the result as a starting checklist rather than a diagnosis."
        ),
        "issue_label": "Main visible issue",
        "issue_options": {
            "motion": "Subject or camera moved",
            "missed-focus": "The wrong area is sharp",
            "low-light-noise": "Low light, grain or colour noise",
            "low-resolution-crop": "Small image or heavy crop",
            "compressed-copy": "Copy from chat, social or shared album",
        },
        "use_label": "Intended use",
        "use_options": {
            "casual-memory": "Personal or family memory",
            "print": "Print or enlargement",
            "work-profile": "Work, listing or profile",
        },
        "detail_label": "Most important detail",
        "detail_options": {
            "overall-scene": "Overall scene",
            "face": "Face",
            "text": "Text or lettering",
        },
        "zoom_label": "Digital zoom or heavy crop was used",
        "smudge_label": "The lens may have been dirty or obstructed",
        "update": "Build conservative next steps",
        "issue_guidance": {
            "motion": {
                "limitation": (
                    "Movement can spread detail across pixels. This page cannot tell how "
                    "severe it is without receiving the image."
                ),
                "first_action": (
                    "Look for a less-blurred frame, Live Photo frame or original sequence "
                    "before enhancing this copy."
                ),
                "steps": (
                    "Start from the least-blurred untouched original you can find.",
                    "Try gentle denoise only if noise is present, then moderate sharpening.",
                    "Stop if edges split, faces change or halos become more visible than the subject.",
                ),
            },
            "missed-focus": {
                "limitation": (
                    "Sharpening cannot move captured focus. If the important area never "
                    "received detail, it may remain soft."
                ),
                "first_action": (
                    "Check nearby frames for one where the intended face, text or subject "
                    "is actually in focus."
                ),
                "steps": (
                    "Use the sharpest original frame as the source.",
                    "Apply restrained sharpening and compare at 100% zoom.",
                    "Do not treat invented-looking eyes, letters or textures as recovered fact.",
                ),
            },
            "low-light-noise": {
                "limitation": (
                    "Noise reduction can remove real fine texture, while strong sharpening "
                    "can exaggerate grain."
                ),
                "first_action": (
                    "Find the original file and inspect whether blur, noise or both are the "
                    "main problem."
                ),
                "steps": (
                    "Reduce noise conservatively before adding sharpening.",
                    "Compare skin, hair, fabric and flat shadows for waxy or blotchy artifacts.",
                    "Keep the version that preserves believable texture, not merely the sharpest edge.",
                ),
            },
            "low-resolution-crop": {
                "limitation": (
                    "Upscaling adds pixels, but it cannot prove what physical detail was "
                    "outside the captured resolution."
                ),
                "first_action": (
                    "Find the uncropped original or the largest export before enlarging a "
                    "small derivative."
                ),
                "steps": (
                    "Start from the highest-resolution original available.",
                    "Upscale once for the intended output instead of repeatedly resizing.",
                    "Inspect the result at its actual screen or print size and at 100% zoom.",
                ),
            },
            "compressed-copy": {
                "limitation": (
                    "A shared or re-saved copy may have fewer pixels or compression artifacts "
                    "that sharpening can make more obvious."
                ),
                "first_action": (
                    "Ask for the original file or least-compressed copy before trying to "
                    "repair a messaging or social-media derivative."
                ),
                "steps": (
                    "Compare dimensions and file source with the original if available.",
                    "Avoid repeated save-and-share cycles before enhancement.",
                    "Use mild artifact reduction, then inspect edges and small text carefully.",
                ),
            },
        },
        "use_checks": {
            "casual-memory": (
                "Prefer a natural-looking memory over aggressive detail that changes the scene."
            ),
            "print": (
                "Judge at the intended print dimensions and viewing distance before exporting."
            ),
            "work-profile": (
                "Keep identity, products, logos and lettering truthful; never rely on ambiguous "
                "enhanced detail for a material claim."
            ),
        },
        "detail_checks": {
            "overall-scene": (
                "Check straight edges, foliage, fabric and repeated patterns for halos or false texture."
            ),
            "face": (
                "Compare eyes, teeth, hairlines and facial proportions with the untouched original."
            ),
            "text": (
                "Compare every important character with a known source; unclear text must remain unverified."
            ),
        },
        "zoom_note": (
            "Heavy cropping or digital zoom reduces the captured detail available. Return to "
            "the uncropped original when possible."
        ),
        "smudge_note": (
            "Cleaning the lens helps future captures, but cannot restore past optical detail. "
            "Apple recommends a microfiber cloth when photos are blurry."
        ),
        "preserve_original": (
            "Duplicate or preserve the untouched original before any enhancement or export."
        ),
        "output_boundary": (
            "Choose the least aggressive result that helps at the intended size. Enhancement "
            "can improve appearance, but this guide does not verify historical, forensic, "
            "legal, medical or identification detail."
        ),
        "source_boundary": (
            "If the image came from a Shared Album, chat or social service, look for the "
            "original first. Apple's 2048-pixel figure below applies specifically to Shared "
            "Albums, not automatically to every sharing service."
        ),
        "result_issue": "Selected observation",
        "result_first": "First action",
        "result_limit": "Important limitation",
        "result_steps": "Ordered next steps",
        "result_inspect": "Inspect before keeping",
        "prevention_title": "Five capture habits for next time",
        "prevention": (
            "Clean the front and back lenses with a microfiber cloth when images look blurry.",
            "Tap the intended subject to set focus and exposure before taking the photo.",
            "Use more light and steady the phone when movement or low light is likely.",
            "Move closer instead of relying on heavy digital zoom when practical.",
            "Keep an untouched original before cropping, editing or sharing.",
        ),
        "sources_title": "Official context, not a restoration guarantee",
        "sources_intro": (
            "Apple documents focus and exposure controls, lens checks and Shared Album limits. "
            "Adobe documents what its Enhance features do. None of these sources certifies a "
            "specific photo as recoverable."
        ),
        "source_labels": (
            "Apple: use iPhone camera tools to set up your shot",
            "Apple: steps to try when a photo is blurry",
            "Apple: Shared Albums upload a copy and reduce photos",
            "Adobe: Denoise, Raw Details and Super Resolution",
        ),
        "webmcp_source": "Chrome WebMCP imperative API preview (subject to change)",
        "webmcp_description": (
            "Return conservative blurry-photo next steps from bounded, self-reported visible "
            "observations. Never receive, inspect, upload, store or process a photo; never "
            "diagnose the image, calculate a recovery percentage or guarantee restored detail."
        ),
        "app_title": "Want to test a copy privately on iPhone?",
        "app_text": (
            "Unblurry Pro is optional. Its current App Store listing describes on-device "
            "Auto Clear, Sharpen, Denoise, Low Light, Document, Super Resolution, 4× Upscale "
            "and Portrait & Restore modes, with a free daily save and a one-time unlock. "
            "Check the current listing for exact availability and features. This guide works "
            "without the app."
        ),
        "app_cta": "View Unblurry Pro on the App Store",
        "faq_title": "Questions before enhancing",
        "faq": (
            (
                "Does this page see or upload my photo?",
                "No. It has no image or file input and only uses bounded observations you select.",
            ),
            (
                "Is this a diagnosis or recovery prediction?",
                "No. It returns a cautious checklist, not a percentage, diagnosis or promise.",
            ),
            (
                "Can upscaling prove what was originally in a blurry area?",
                "No. More pixels can improve appearance, but ambiguous detail remains unverified.",
            ),
            (
                "Why should I find the original first?",
                "A crop, shared copy or repeated export can contain fewer pixels or more artifacts than the source.",
            ),
        ),
        "footer": "Private guidance only · no photo input · preserve the original",
        "index_title": "Private Blurry Photo Next-Step Guide",
        "index_description": (
            "Choose visible symptoms and get conservative next steps without uploading a "
            "photo or receiving a recovery score."
        ),
    },
    "zh-Hant": {
        "title": "私密模糊照片下一步指南｜不上傳照片",
        "description": (
            "不用上傳照片，只選擇可見狀況，即可取得針對晃動、失焦、低光雜訊、重度裁切或壓縮副本的保守處理順序。"
        ),
        "tools": "免費工具",
        "switch": "English",
        "eyebrow": "免費 · 不輸入照片 · 不評恢復百分比",
        "heading": "私密模糊照片下一步指南",
        "lead": (
            "只描述你已看見的狀況；網頁會提出保守處理順序，但完全不接收照片，也無法診斷或保證修復。"
        ),
        "badges": (
            "不輸入影像或檔案",
            "不上傳或呼叫雲端",
            "不計算恢復百分比",
            "不保證找回細節",
        ),
        "planner": "描述可見問題",
        "planner_intro": (
            "選擇最接近的觀察；同一張照片可能同時有多種成因，因此結果只是起始檢查表，不是診斷。"
        ),
        "issue_label": "主要可見問題",
        "issue_options": {
            "motion": "人物、物體或相機移動",
            "missed-focus": "清楚的部位不是主體",
            "low-light-noise": "低光、顆粒或彩色雜訊",
            "low-resolution-crop": "圖片太小或重度裁切",
            "compressed-copy": "來自聊天、社群或共享相簿的副本",
        },
        "use_label": "預計用途",
        "use_options": {
            "casual-memory": "個人或家庭回憶",
            "print": "列印或放大",
            "work-profile": "工作、商品或個人檔案",
        },
        "detail_label": "最重要的細節",
        "detail_options": {
            "overall-scene": "整體場景",
            "face": "人臉",
            "text": "文字或字樣",
        },
        "zoom_label": "曾使用數位變焦或重度裁切",
        "smudge_label": "鏡頭可能髒污或被配件遮擋",
        "update": "建立保守下一步",
        "issue_guidance": {
            "motion": {
                "limitation": "移動會讓細節分散到多個像素；本頁不接收影像，因此無法判斷嚴重程度。",
                "first_action": "增強這張副本前，先找晃動較少的照片、Live Photo 影格或原始連拍。",
                "steps": (
                    "從能找到且晃動最少的未修改原檔開始。",
                    "只有出現雜訊時才先輕度降噪，再進行適量銳化。",
                    "若邊緣分裂、人臉改變或光暈比主體更明顯，就停止加強。",
                ),
            },
            "missed-focus": {
                "limitation": "銳化無法移動拍攝時的焦點；重要區域若未捕捉到細節，可能仍會模糊。",
                "first_action": "檢查前後影格，尋找目標人臉、文字或主體真正合焦的版本。",
                "steps": (
                    "使用主體最清楚的原始影格。",
                    "適量銳化後，以 100% 比例和原檔比較。",
                    "不要把看似生成的眼睛、文字或紋理當成已找回的事實。",
                ),
            },
            "low-light-noise": {
                "limitation": "降噪可能刪除真實細節，強力銳化也可能把顆粒放得更明顯。",
                "first_action": "找到原始檔，先判斷主要問題是模糊、雜訊，還是兩者都有。",
                "steps": (
                    "先保守降低雜訊，再加上少量銳化。",
                    "檢查皮膚、頭髮、布料與暗部是否變得蠟化或斑駁。",
                    "保留紋理較可信的版本，不要只選邊緣最銳利的結果。",
                ),
            },
            "low-resolution-crop": {
                "limitation": "放大會增加像素，但無法證明原始解析度之外曾存在什麼真實細節。",
                "first_action": "放大小型副本前，先尋找未裁切原檔或尺寸最大的匯出版本。",
                "steps": (
                    "從能取得的最高解析度原檔開始。",
                    "依目標輸出只放大一次，不要重複縮放。",
                    "以實際螢幕或列印尺寸及 100% 比例檢查結果。",
                ),
            },
            "compressed-copy": {
                "limitation": "分享或重存的副本可能像素更少，也可能有壓縮瑕疵；銳化會讓瑕疵更明顯。",
                "first_action": "處理通訊軟體或社群副本前，先索取原始檔或壓縮最少的版本。",
                "steps": (
                    "如有原檔，先比較圖片尺寸與檔案來源。",
                    "增強前避免反覆儲存及轉傳。",
                    "輕度降低壓縮瑕疵，再仔細檢查邊緣與小字。",
                ),
            },
        },
        "use_checks": {
            "casual-memory": "家庭回憶應以自然為優先，不要為了銳利而改變場景。",
            "print": "匯出前，以預計列印尺寸及觀看距離檢查結果。",
            "work-profile": "身分、商品、標誌與文字都必須真實；不可用模糊的增強細節支持重要主張。",
        },
        "detail_checks": {
            "overall-scene": "檢查直線、樹葉、布料與重複圖案是否出現光暈或假紋理。",
            "face": "把眼睛、牙齒、髮際線與臉部比例和未修改原檔比較。",
            "text": "每個重要字元都要和已知來源核對；不清楚的文字仍視為未確認。",
        },
        "zoom_note": "重度裁切或數位變焦會減少已捕捉的細節；可以的話回到未裁切原檔。",
        "smudge_note": "清潔鏡頭只會幫助未來拍攝，不能恢復過去的光學細節；Apple 建議照片模糊時用超細纖維布清潔鏡頭。",
        "preserve_original": "任何增強或匯出前，先複製或保存完全未修改的原檔。",
        "output_boundary": (
            "只保留在目標尺寸下確實有幫助且處理最少的版本。增強能改善外觀，但本指南不驗證歷史、"
            "鑑識、法律、醫療或身分辨識細節。"
        ),
        "source_boundary": (
            "影像若來自共享相簿、聊天或社群服務，先尋找原檔。下方 Apple 的 2048 像素說明只適用"
            "於共享相簿，不能自動套用到所有分享服務。"
        ),
        "result_issue": "選定觀察",
        "result_first": "第一步",
        "result_limit": "重要限制",
        "result_steps": "依序處理",
        "result_inspect": "保留前檢查",
        "prevention_title": "下次拍攝前養成五個習慣",
        "prevention": (
            "影像模糊時，以超細纖維布清潔前後鏡頭。",
            "拍照前點選目標主體，設定焦點與曝光。",
            "可能移動或光線不足時，增加光線並穩住手機。",
            "實際可行時靠近主體，避免依賴重度數位變焦。",
            "裁切、編輯或分享前，保留一份未修改原檔。",
        ),
        "sources_title": "官方背景資料，不代表修復保證",
        "sources_intro": (
            "Apple 說明焦點與曝光控制、鏡頭檢查及共享相簿限制；Adobe 說明 Enhance 功能。"
            "這些來源都不會證明某張照片一定能修復。"
        ),
        "source_labels": (
            "Apple：使用 iPhone 相機工具設定拍攝畫面",
            "Apple：照片模糊時可嘗試的處理步驟",
            "Apple：共享相簿會上傳副本並縮小照片",
            "Adobe：Denoise、Raw Details 與 Super Resolution",
        ),
        "webmcp_source": "Chrome WebMCP 命令式 API 預覽（規格可能變動）",
        "webmcp_description": (
            "只根據有界、自行選擇的可見觀察，回傳保守的模糊照片下一步；不接收、檢查、上傳、"
            "儲存或處理照片，也不診斷影像、計算恢復百分比或保證找回細節。"
        ),
        "app_title": "想在 iPhone 上私密測試副本？",
        "app_text": (
            "Unblurry Pro 是選用工具；目前 App Store 頁面說明包含裝置端 Auto Clear、Sharpen、"
            "Denoise、Low Light、Document、Super Resolution、4× Upscale 及 Portrait & Restore，"
            "每天可免費儲存一次，並提供一次性解鎖。供應地區與確切功能請以目前商店頁為準；"
            "這份指南不需 App 也能使用。"
        ),
        "app_cta": "在 App Store 查看 Unblurry Pro",
        "faq_title": "增強前常見問題",
        "faq": (
            (
                "這個網頁會看到或上傳我的照片嗎？",
                "不會。它沒有影像或檔案輸入，只使用你選擇的有界觀察。",
            ),
            (
                "這是診斷或恢復預測嗎？",
                "不是。它只提供保守檢查表，不計算百分比、不診斷，也不承諾結果。",
            ),
            (
                "放大能證明模糊區域原本是什麼嗎？",
                "不能。增加像素可能改善外觀，但不清楚的細節仍然未經確認。",
            ),
            (
                "為什麼要先找原檔？",
                "裁切、分享副本或反覆匯出可能比來源像素更少、瑕疵更多。",
            ),
        ),
        "footer": "只提供私密指引 · 不輸入照片 · 保留原始檔",
        "index_title": "私密模糊照片下一步指南",
        "index_description": "只選可見狀況，不上傳照片、不評恢復分數，即可取得保守處理順序。",
    },
}

STYLE = r"""
:root{--ink:#202034;--muted:#636476;--line:#e4e0ec;--paper:#fff;--bg:#f7f3f7;--plum:#613d69;--rose:#b36377;--soft:#f6eaf0;--warn:#fff6d9;--shadow:0 22px 60px rgba(65,42,69,.12)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 90% 0,#fff 0,var(--bg) 52%,#eee5ed 100%);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Noto Sans TC",sans-serif;line-height:1.62}
a{color:#78436f}.wrap{width:min(1120px,calc(100% - 30px));margin:auto}.top{position:sticky;top:0;z-index:8;background:#fffffff2;border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:850;white-space:nowrap}.links{display:flex;gap:15px;overflow-x:auto}
.hero{padding:64px 0 30px}.eyebrow,.badge{display:inline-flex;border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 12px;font-size:13px;font-weight:850;color:var(--plum);white-space:nowrap}.hero h1,h2{font-family:ui-serif,Georgia,"Noto Serif TC",serif}.hero h1{font-size:clamp(34px,6vw,62px);line-height:1.04;letter-spacing:-.035em;margin:.3em 0 .22em;white-space:nowrap;overflow-x:auto}.lead{font-size:clamp(17px,2.2vw,21px);color:var(--muted);margin:0;white-space:nowrap;overflow-x:auto}.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:22px}
.planner,.card,.app-card{background:rgba(255,255,255,.97);border:1px solid var(--line);border-radius:26px;box-shadow:var(--shadow)}.planner{padding:clamp(20px,4vw,36px);margin:16px auto 30px}.planner h2,.card h2,.app-card h2{font-size:clamp(24px,3.6vw,34px);line-height:1.14;margin:0;white-space:nowrap;overflow-x:auto}.intro{color:var(--muted);white-space:nowrap;overflow-x:auto}
.controls{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:22px}.field{min-width:0}.field label{display:block;font-size:13px;font-weight:850;color:var(--plum);margin-bottom:6px;white-space:nowrap;overflow-x:auto}select,button{font:inherit}select{width:100%;min-height:46px;border:1px solid #d3c9d6;border-radius:13px;background:#fff;color:var(--ink);padding:9px 11px}.toggles{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:14px 0}.toggle{display:flex;align-items:center;gap:10px;border:1px solid var(--line);border-radius:14px;padding:11px 13px;background:#fff;font-weight:760;white-space:nowrap;overflow-x:auto}.toggle input{inline-size:20px;block-size:20px;flex:0 0 auto}.button{border:0;border-radius:999px;background:linear-gradient(135deg,var(--plum),var(--rose));color:#fff;text-decoration:none;font-weight:850;padding:11px 17px;cursor:pointer;white-space:nowrap;box-shadow:0 9px 22px rgba(97,61,105,.2)}
.results{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:11px;margin-top:22px}.result{background:var(--soft);border:1px solid #e6cad7;border-radius:17px;padding:14px;min-width:0}.result strong,.result span{display:block;white-space:nowrap;overflow-x:auto}.result strong{font-size:12px;color:#704c67;text-transform:uppercase;letter-spacing:.04em}.result span{font-size:15px;color:#3f3340;font-weight:760;margin-top:5px}.note{background:var(--warn);border:1px solid #ead9a7;border-radius:16px;padding:13px 15px;margin:14px 0 0;white-space:nowrap;overflow-x:auto}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:30px}.card,.app-card{padding:clamp(20px,3.5vw,30px)}.card.wide{grid-column:1/-1}.card p,.card li,.app-card p,.faq details p,.faq summary{white-space:nowrap;overflow-x:auto}.card ul,.card ol{padding-left:22px}.card li{margin:8px 0}.source-list a{overflow-wrap:anywhere}.app-card{margin:0 auto 38px;background:linear-gradient(135deg,#fffafb,#f2e7ef)}.app-card .button{display:inline-flex;margin-top:5px}.faq{margin-bottom:30px}.faq details{border:1px solid var(--line);border-radius:15px;background:#fff;padding:11px 14px;margin-top:9px}.faq summary{font-weight:830;cursor:pointer}.faq details p{color:var(--muted)}
.footer{background:var(--plum);color:#f8eef5;text-align:center;padding:27px 0;white-space:nowrap;overflow-x:auto}
@media(max-width:900px){.controls,.results{grid-template-columns:1fr}.grid{grid-template-columns:1fr}.card.wide{grid-column:auto}}
@media(max-width:560px){.toggles{grid-template-columns:1fr}.wrap{width:min(100% - 22px,1120px)}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
@media print{.top,.hero,.controls,.toggles,.button,.app-card,.footer{display:none!important}body{background:#fff}.planner,.card{box-shadow:none;break-inside:avoid}}
"""

SCRIPT = r"""
(() => {
  const config = JSON.parse(document.getElementById("blur-config").textContent);
  const form = document.getElementById("blur-guide");
  const fields = {
    issue: document.getElementById("issue"),
    intended_use: document.getElementById("intended-use"),
    important_detail: document.getElementById("important-detail"),
    digital_zoom_or_heavy_crop: document.getElementById("used-zoom"),
    possible_lens_smudge: document.getElementById("lens-smudge")
  };
  const output = {
    issue: document.getElementById("result-issue"),
    first: document.getElementById("result-first"),
    limit: document.getElementById("result-limit"),
    steps: document.getElementById("result-steps"),
    inspect: document.getElementById("result-inspect")
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

  function booleanValue(input, name) {
    if (!Object.prototype.hasOwnProperty.call(input, name)) {
      throw new TypeError(`${name} is required.`);
    }
    if (typeof input[name] !== "boolean") {
      throw new TypeError(`${name} must be a boolean.`);
    }
    return input[name];
  }

  function unique(values) {
    return [...new Set(values)];
  }

  function plan(input) {
    const issue = enumValue(input, "issue");
    const intendedUse = enumValue(input, "intended_use");
    const importantDetail = enumValue(input, "important_detail");
    const usedZoom = booleanValue(input, "digital_zoom_or_heavy_crop");
    const lensSmudge = booleanValue(input, "possible_lens_smudge");
    const guidance = config.issueGuidance[issue];
    const steps = [config.preserveOriginal, guidance.first_action, ...guidance.steps];
    if (usedZoom) steps.push(config.zoomNote);
    if (lensSmudge) steps.push(config.smudgeNote);
    return {
      selected_observations: {
        issue,
        issue_label: config.labels.issue[issue],
        intended_use: intendedUse,
        intended_use_label: config.labels.intended_use[intendedUse],
        important_detail: importantDetail,
        important_detail_label: config.labels.important_detail[importantDetail],
        digital_zoom_or_heavy_crop: usedZoom,
        possible_lens_smudge: lensSmudge
      },
      first_action: guidance.first_action,
      likely_limitations: guidance.limitation,
      ordered_next_steps: unique(steps),
      output_inspection_checklist: [
        config.detailChecks[importantDetail],
        config.useChecks[intendedUse],
        config.outputBoundary
      ],
      source_preservation_boundary: config.sourceBoundary
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
      issue: fields.issue.value,
      intended_use: fields.intended_use.value,
      important_detail: fields.important_detail.value,
      digital_zoom_or_heavy_crop: fields.digital_zoom_or_heavy_crop.checked,
      possible_lens_smudge: fields.possible_lens_smudge.checked
    });
    output.issue.textContent = result.selected_observations.issue_label;
    output.first.textContent = result.first_action;
    output.limit.textContent = result.likely_limitations;
    output.steps.textContent = result.ordered_next_steps
      .map((step, index) => `${index + 1}. ${step}`).join(" ");
    output.inspect.textContent = result.output_inspection_checklist.join(" ");
  }

  async function registerWebMcp() {
    if (!document.modelContext?.registerTool) return;
    await document.modelContext.registerTool({
      name: "plan_private_blurry_photo_next_steps",
      description: config.toolDescription,
      inputSchema: config.inputSchema,
      annotations: {readOnlyHint: true, untrustedContentHint: false},
      execute: async (input) => {
        const guide = validateInput(input);
        const result = {
          result_type: "private_blurry_photo_next_steps",
          photo_not_received_or_processed: true,
          not_a_diagnosis_or_restoration_guarantee: true,
          no_recovery_percentage: true,
          guide,
          prevention_checklist: config.preventionChecklist,
          optional_free_guide: config.freeGuide,
          official_sources: config.officialSources,
          webmcp_preview_source: config.webmcpSource
        };
        if (config.optionalApp) {
          result.optional_unblurry_pro = config.optionalApp;
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


def options(values: dict[str, str]) -> str:
    return "".join(
        f'<option value="{html.escape(key, quote=True)}">{html.escape(label)}</option>'
        for key, label in values.items()
    )


def webmcp_input_schema(locale: str) -> dict[str, object]:
    if locale not in COPY:
        raise ValueError(f"unsupported locale: {locale}")
    return {
        "type": "object",
        "properties": {
            "issue": {"type": "string", "enum": list(ISSUES)},
            "intended_use": {
                "type": "string",
                "enum": list(INTENDED_USES),
            },
            "important_detail": {
                "type": "string",
                "enum": list(IMPORTANT_DETAILS),
            },
            "digital_zoom_or_heavy_crop": {"type": "boolean"},
            "possible_lens_smudge": {"type": "boolean"},
        },
        "required": [
            "issue",
            "intended_use",
            "important_detail",
            "digital_zoom_or_heavy_crop",
            "possible_lens_smudge",
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
        APPLE_SHOT,
        APPLE_CAMERA_HELP,
        APPLE_SHARED_ALBUMS,
        ADOBE_ENHANCE,
    )
    source_items = "".join(
        f'<li><a href="{html.escape(source, quote=True)}" rel="noopener">'
        f"{html.escape(label)}</a></li>"
        for label, source in zip(t["source_labels"], sources, strict=True)
    )
    prevention_items = "".join(
        f"<li>{html.escape(item)}</li>" for item in t["prevention"]
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
        appstore_url(APP_KEY, f"iag_blur_guide_{locale.lower()}")
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
            "issue": t["issue_options"],
            "intended_use": t["use_options"],
            "important_detail": t["detail_options"],
        },
        "issueGuidance": t["issue_guidance"],
        "useChecks": t["use_checks"],
        "detailChecks": t["detail_checks"],
        "zoomNote": t["zoom_note"],
        "smudgeNote": t["smudge_note"],
        "preserveOriginal": t["preserve_original"],
        "outputBoundary": t["output_boundary"],
        "sourceBoundary": t["source_boundary"],
        "preventionChecklist": t["prevention"],
        "toolDescription": t["webmcp_description"],
        "freeGuide": {
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
        "applicationCategory": "PhotographyApplication",
        "operatingSystem": "Any",
        "isAccessibleForFree": True,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "featureList": [
            "No image or file input",
            "No upload, storage or analytics",
            "No recovery percentage",
            "Conservative source-preservation and inspection checklist",
            "No diagnosis or restoration guarantee",
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
<form id="blur-guide"><div class="controls">
<div class="field"><label for="issue">{html.escape(t["issue_label"])}</label><select id="issue">{options(t["issue_options"])}</select></div>
<div class="field"><label for="intended-use">{html.escape(t["use_label"])}</label><select id="intended-use">{options(t["use_options"])}</select></div>
<div class="field"><label for="important-detail">{html.escape(t["detail_label"])}</label><select id="important-detail">{options(t["detail_options"])}</select></div>
</div><div class="toggles"><label class="toggle"><input id="used-zoom" type="checkbox">{html.escape(t["zoom_label"])}</label><label class="toggle"><input id="lens-smudge" type="checkbox">{html.escape(t["smudge_label"])}</label></div><button class="button" type="submit">{html.escape(t["update"])}</button></form>
<div class="results"><div class="result"><strong>{html.escape(t["result_issue"])}</strong><span id="result-issue"></span></div><div class="result"><strong>{html.escape(t["result_first"])}</strong><span id="result-first"></span></div><div class="result"><strong>{html.escape(t["result_limit"])}</strong><span id="result-limit"></span></div></div>
<p class="note"><strong>{html.escape(t["result_steps"])}:</strong> <span id="result-steps"></span></p><p class="note"><strong>{html.escape(t["result_inspect"])}:</strong> <span id="result-inspect"></span></p></section>
<section class="wrap grid"><article class="card"><h2>{html.escape(t["prevention_title"])}</h2><ol>{prevention_items}</ol></article><article class="card"><h2>{html.escape(t["sources_title"])}</h2><p>{html.escape(t["sources_intro"])}</p><ul class="source-list">{source_items}</ul><p><a href="{WEBMCP_SOURCE}" rel="noopener">{html.escape(t["webmcp_source"])}</a></p></article></section>
<section class="wrap card faq"><h2>{html.escape(t["faq_title"])}</h2>{faq}</section>
{app_card}
</main>
<footer class="footer"><div class="wrap">{html.escape(t["footer"])}</div></footer>
<script type="application/json" id="blur-config">{config_json}</script>
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
        r'image-to-pdf-iphone\.html">.*?</article>)',
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
        print(f"blurry photo guide -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
