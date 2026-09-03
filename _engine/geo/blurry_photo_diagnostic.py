#!/usr/bin/env python3
"""Generate a nine-locale, private blurry-photo next-step guide."""

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
from bopomofo_flashcards import ALT_LOCALES  # noqa: E402
from gen_calculator import write_tools_sitemap  # noqa: E402
from gen_feed import feed_discovery_links  # noqa: E402
from videogen.registry import APPSTORE, appstore_url  # noqa: E402
from site_config import PUBLIC_SITE  # noqa: E402

PAGES = HERE / "pages"
SITE = os.environ.get(
    "GEO_SITE", PUBLIC_SITE
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

TARGET_ANSWER_SLUGS = (
    "app-to-fix-blurry-pictures-on-iphone.html",
    "best-app-to-unblur-photos.html",
)
INBOUND_LINK_CLASS = "blurry-photo-diagnostic-inline-link"
_APP_STORE_ANCHOR = re.compile(
    r'<a\b(?=[^>]*\bhref\s*=\s*(?P<q>["\'])https://apps\.apple\.com/'
    r'(?:[^"\'?#]*/)*id'
    + APP_ID
    + r'(?:[?#][^"\']*)?(?P=q))[^>]*>',
    re.IGNORECASE,
)

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
        "inline_link": "Try the private blurry photo next-step checklist",
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
        "inline_link": "使用私密模糊照片下一步檢查清單",
    },
    "zh-Hans": {
        "title": "私密模糊照片下一步指南｜不上传照片",
        "description": (
            "无需上传照片，只需选择可见状况，即可获得针对晃动、失焦、低光噪点、重度裁切或压缩副本的保守处理顺序。"
        ),
        "tools": "免费工具",
        "switch": "繁體中文",
        "eyebrow": "免费 · 不输入照片 · 不评估恢复百分比",
        "heading": "私密模糊照片下一步指南",
        "lead": (
            "只描述你已经看到的状况；网页会给出保守的处理顺序，但完全不接收照片，也无法诊断或保证修复。"
        ),
        "badges": (
            "不输入图像或文件",
            "不上传或调用云端",
            "不计算恢复百分比",
            "不保证找回细节",
        ),
        "planner": "描述可见问题",
        "planner_intro": (
            "选择最接近的观察；同一张照片可能同时有多种成因，因此结果只是起始检查清单，不是诊断。"
        ),
        "issue_label": "主要可见问题",
        "issue_options": {
            "motion": "人物、物体或相机移动",
            "missed-focus": "清晰的部位不是主体",
            "low-light-noise": "低光、颗粒或彩色噪点",
            "low-resolution-crop": "图片太小或重度裁切",
            "compressed-copy": "来自聊天、社交或共享相册的副本",
        },
        "use_label": "预计用途",
        "use_options": {
            "casual-memory": "个人或家庭回忆",
            "print": "打印或放大",
            "work-profile": "工作、商品或个人资料",
        },
        "detail_label": "最重要的细节",
        "detail_options": {
            "overall-scene": "整体场景",
            "face": "人脸",
            "text": "文字或字样",
        },
        "zoom_label": "曾使用数码变焦或重度裁切",
        "smudge_label": "镜头可能有污渍或被遮挡",
        "update": "生成保守下一步",
        "issue_guidance": {
            "motion": {
                "limitation": "移动会让细节分散到多个像素；本页不接收图像，因此无法判断严重程度。",
                "first_action": "增强这份副本前，先寻找晃动较少的照片、实况照片帧或原始连拍。",
                "steps": (
                    "从能找到且晃动最少的未修改原始文件开始。",
                    "只有出现噪点时才先轻度降噪，再进行适度锐化。",
                    "如果边缘出现分裂、人脸变形或光晕比主体更明显，就停止加强。",
                ),
            },
            "missed-focus": {
                "limitation": "锐化无法移动拍摄时的对焦点；重要区域若未捕捉到细节，可能仍然模糊。",
                "first_action": "检查前后帧，寻找目标人脸、文字或主体真正对焦的版本。",
                "steps": (
                    "使用主体最清晰的原始帧作为来源。",
                    "适度锐化后，以 100% 比例与原始文件比较。",
                    "不要把看似生成的眼睛、文字或纹理当成已找回的事实。",
                ),
            },
            "low-light-noise": {
                "limitation": "降噪可能删除真实的细腻纹理，强力锐化也可能让颗粒更明显。",
                "first_action": "找到原始文件，先判断主要问题是模糊、噪点，还是两者都有。",
                "steps": (
                    "先保守降低噪点，再加上少量锐化。",
                    "检查皮肤、头发、布料与暗部阴影是否出现蜡状或斑驳瑕疵。",
                    "保留纹理更可信的版本，不要只选边缘最锐利的结果。",
                ),
            },
            "low-resolution-crop": {
                "limitation": "放大会增加像素，但无法证明原始分辨率之外曾经存在什么真实细节。",
                "first_action": "放大小尺寸副本前，先寻找未裁切的原图或尺寸最大的导出版本。",
                "steps": (
                    "从能获取的最高分辨率原图开始。",
                    "按目标输出只放大一次，不要重复缩放。",
                    "以实际屏幕或打印尺寸及 100% 比例检查结果。",
                ),
            },
            "compressed-copy": {
                "limitation": "分享或重新保存的副本可能像素更少，也可能有压缩瑕疵；锐化会让瑕疵更明显。",
                "first_action": "处理聊天软件或社交媒体副本前，先索取原始文件或压缩最少的版本。",
                "steps": (
                    "如有原图，先比较图片尺寸与文件来源。",
                    "增强前避免反复保存与转发。",
                    "轻度降低压缩瑕疵，再仔细检查边缘与小字。",
                ),
            },
        },
        "use_checks": {
            "casual-memory": "家庭回忆应以自然为先，不要为了锐利而改变场景。",
            "print": "导出前，以预计打印尺寸和观看距离检查结果。",
            "work-profile": "身份、商品、标志与文字都必须真实；不可用模糊的增强细节支持重要主张。",
        },
        "detail_checks": {
            "overall-scene": "检查直线、树叶、布料与重复图案是否出现光晕或虚假纹理。",
            "face": "把眼睛、牙齿、发际线与脸部比例和未修改原图比较。",
            "text": "每个重要字符都要与已知来源核对；不清楚的文字仍视为未确认。",
        },
        "zoom_note": "重度裁切或数码变焦会减少已捕捉的细节；可以的话回到未裁切原图。",
        "smudge_note": "清洁镜头只会帮助未来拍摄，不能恢复过去的光学细节；照片模糊时 Apple 建议用超细纤维布清洁镜头。",
        "preserve_original": "任何增强或导出前，先复制或保存完全未修改的原始文件。",
        "output_boundary": (
            "只保留在目标尺寸下确实有帮助、处理最少的版本。增强能改善外观，但本指南不验证历史、"
            "鉴识、法律、医疗或身份识别细节。"
        ),
        "source_boundary": (
            "图像若来自共享相册、聊天或社交服务，请先寻找原图。下方 Apple 的 2048 像素说明仅适用"
            "于共享相册，不能自动套用到所有分享服务。"
        ),
        "result_issue": "已选观察",
        "result_first": "第一步",
        "result_limit": "重要限制",
        "result_steps": "按顺序处理",
        "result_inspect": "保留前检查",
        "prevention_title": "下次拍摄前养成五个习惯",
        "prevention": (
            "图像模糊时，用超细纤维布清洁前后镜头。",
            "拍照前点选目标主体，设定对焦与曝光。",
            "可能移动或光线不足时，增加光线并稳住手机。",
            "实际可行时靠近主体，避免依赖重度数码变焦。",
            "裁切、编辑或分享前，保留一份未修改原始文件。",
        ),
        "sources_title": "官方背景资料，不代表修复保证",
        "sources_intro": (
            "Apple 说明对焦与曝光控制、镜头检查及共享相册限制；Adobe 说明 Enhance 功能。"
            "这些来源都不会证明某张照片一定能修复。"
        ),
        "source_labels": (
            "Apple：使用 iPhone 相机工具设定拍摄画面",
            "Apple：照片模糊时可尝试的处理步骤",
            "Apple：共享相册会上传副本并缩小照片",
            "Adobe：Denoise、Raw Details 与 Super Resolution",
        ),
        "webmcp_source": "Chrome WebMCP 命令式 API 预览（规格可能变动）",
        "webmcp_description": (
            "只根据有界、自行选择的可见观察，返回保守的模糊照片下一步；不接收、检查、上传、"
            "存储或处理照片，也不诊断图像、计算恢复百分比或保证找回细节。"
        ),
        "app_title": "想在 iPhone 上私密测试副本？",
        "app_text": (
            "Unblurry Pro 是可选工具；目前 App Store 页面说明包含设备端 Auto Clear、Sharpen、"
            "Denoise、Low Light、Document、Super Resolution、4× Upscale 及 Portrait & Restore，"
            "每天可免费保存一次，并提供一次性解锁。供应地区与确切功能请以当前商店页面为准；"
            "这份指南不需要 App 也能使用。"
        ),
        "app_cta": "在 App Store 查看 Unblurry Pro",
        "faq_title": "增强前常见问题",
        "faq": (
            (
                "这个网页会看到或上传我的照片吗？",
                "不会。它没有图像或文件输入，只使用你选择的有界观察。",
            ),
            (
                "这是诊断或恢复预测吗？",
                "不是。它只提供保守检查清单，不计算百分比、不诊断，也不承诺结果。",
            ),
            (
                "放大能证明模糊区域原本是什么吗？",
                "不能。增加像素可能改善外观，但不清楚的细节仍然未经确认。",
            ),
            (
                "为什么要先找原图？",
                "裁切、分享副本或反复导出可能比来源像素更少、瑕疵更多。",
            ),
        ),
        "footer": "只提供私密指引 · 不输入照片 · 保留原始文件",
        "index_title": "私密模糊照片下一步指南",
        "index_description": "只选可见状况，不上传照片、不评恢复分数，即可获得保守处理顺序。",
        "inline_link": "使用私密模糊照片下一步检查清单",
    },
    "ja":     {
        "title": "写真をアップロードしないプライベートなブレ写真ネクストステップガイド",
        "description": (
            "写真をアップロードせず、目に見える症状を選ぶだけで、手ブレ、ピント外れ、暗所ノイズ、"
            "強いトリミング、圧縮コピーに対する慎重な次の一歩を確認できます。"
        ),
        "tools": "無料ツール",
        "switch": "繁體中文",
        "eyebrow": "無料 · 写真を入力しない · 復元スコアなし",
        "heading": "プライベートなブレ写真ネクストステップガイド",
        "lead": (
            "すでに見えている状態だけを選んでください。このページは慎重な手順を提案しますが、"
            "写真を一切受け取らず、診断や修復の保証もできません。"
        ),
        "badges": (
            "画像やファイルの入力なし",
            "アップロードやクラウド呼び出しなし",
            "復元率の算出なし",
            "細部が戻る保証なし",
        ),
        "planner": "見えている問題を選ぶ",
        "planner_intro": (
            "最も近い観察を選んでください。実際の写真には複数の原因が重なることがあるため、"
            "結果は診断ではなく最初のチェックリストとして扱ってください。"
        ),
        "issue_label": "主に見える問題",
        "issue_options": {
            "motion": "被写体またはカメラが動いた",
            "missed-focus": "ピントが合っている場所が違う",
            "low-light-noise": "暗所での粒状感や色ノイズ",
            "low-resolution-crop": "画像が小さい、または強くトリミングされている",
            "compressed-copy": "チャット・SNS・共有アルバムからのコピー",
        },
        "use_label": "想定する用途",
        "use_options": {
            "casual-memory": "個人や家族の思い出",
            "print": "プリントや拡大",
            "work-profile": "仕事、出品、プロフィール用",
        },
        "detail_label": "最も重要な部分",
        "detail_options": {
            "overall-scene": "シーン全体",
            "face": "顔",
            "text": "文字や表示",
        },
        "zoom_label": "デジタルズームまたは強いトリミングを使った",
        "smudge_label": "レンズが汚れている、または遮られている可能性",
        "update": "慎重な次の一歩を作成",
        "issue_guidance": {
            "motion": {
                "limitation": (
                    "動きがあると detail が複数のピクセルに広がります。画像を受け取らないため、"
                    "このページでは深刻度を判断できません。"
                ),
                "first_action": (
                    "このコピーを強調する前に、ブレの少ないフレーム、Live Photos のフレーム、"
                    "元の連写を探してください。"
                ),
                "steps": (
                    "見つけられる中で最もブレの少ない未加工のオリジナルから始める。",
                    "ノイズがある場合のみ軽いノイズ除去を行い、その後控えめにシャープ化する。",
                    "輪郭が割れる、顔が変わる、被写体よりハローが目立つ場合は止める。",
                ),
            },
            "missed-focus": {
                "limitation": (
                    "シャープ化では撮影時のピント位置は動かせません。重要な部分に detail が"
                    "写っていなければ、そのままぼやける可能性があります。"
                ),
                "first_action": (
                    "前後のフレームを確認し、目的の顔・文字・被写体に実際にピントが合っている"
                    "ものを探してください。"
                ),
                "steps": (
                    "被写体が最も鮮明な元のフレームを使用する。",
                    "控えめなシャープ化を行い、100% 表示で元画像と比較する。",
                    "生成されたように見える目・文字・質感を、復元された事実として扱わない。",
                ),
            },
            "low-light-noise": {
                "limitation": (
                    "ノイズ除去は本物の細かい質感まで消してしまうことがあり、強いシャープ化は"
                    "粒状感を強調することがあります。"
                ),
                "first_action": (
                    "元のファイルを見つけ、主な問題がブレなのかノイズなのか、両方なのかを確認"
                    "する。"
                ),
                "steps": (
                    "まず控えめにノイズを減らしてから、シャープ化を加える。",
                    "肌、髪、布地、暗い影の部分がロウのようになったり斑になったりしていないか"
                    "確認する。",
                    "最も鋭いエッジではなく、質感が信じられる仕上がりを残す。",
                ),
            },
            "low-resolution-crop": {
                "limitation": (
                    "アップスケールはピクセルを追加しますが、撮影解像度の外側に実際にどんな"
                    "detail があったかを証明することはできません。"
                ),
                "first_action": (
                    "小さいコピーを拡大する前に、トリミングされていない元画像や最大サイズの"
                    "書き出しを探す。"
                ),
                "steps": (
                    "入手できる最も高い解像度の元画像から始める。",
                    "目的の出力に合わせて一度だけ拡大し、繰り返しリサイズしない。",
                    "実際の画面や印刷サイズ、および 100% 表示で結果を確認する。",
                ),
            },
            "compressed-copy": {
                "limitation": (
                    "共有や再保存されたコピーはピクセル数が少なかったり圧縮ノイズが含まれて"
                    "いたりし、シャープ化でそれが目立つことがあります。"
                ),
                "first_action": (
                    "メッセージや SNS のコピーを修復する前に、元のファイルまたは圧縮が最も"
                    "少ないコピーを探す。"
                ),
                "steps": (
                    "元画像がある場合はサイズとファイルの出どころを比較する。",
                    "強調処理の前に、保存と共有を繰り返さない。",
                    "軽い圧縮ノイズ除去を行い、輪郭と小さな文字を注意深く確認する。",
                ),
            },
        },
        "use_checks": {
            "casual-memory": "場面を変えてしまう強すぎる detail より、自然に見える思い出を優先する。",
            "print": "書き出す前に、想定するプリントサイズと鑑賞距離で判断する。",
            "work-profile": (
                "人物・商品・ロゴ・文字は必ず正確に保ち、曖昧な強調結果を重要な主張の根拠に"
                "しない。"
            ),
        },
        "detail_checks": {
            "overall-scene": "直線、葉、布地、繰り返し模様にハローや偽の質感が出ていないか確認する。",
            "face": "目、歯、生え際、顔のバランスを未加工の元画像と比較する。",
            "text": "重要な文字はすべて既知の情報源と照合し、不明瞭な文字は未確認のまま扱う。",
        },
        "zoom_note": (
            "強いトリミングやデジタルズームは、撮影された detail を減らします。可能であれば"
            "トリミングされていない元画像に戻ってください。"
        ),
        "smudge_note": (
            "レンズの掃除は今後の撮影には役立ちますが、過去の光学的な detail は戻せません。"
            "写真がぼやける場合、Apple はマイクロファイバークロスの使用を推奨しています。"
        ),
        "preserve_original": "強調や書き出しの前に、未加工のオリジナルを複製または保管してください。",
        "output_boundary": (
            "目的のサイズで実際に役立つ、最も控えめな結果を選んでください。強調は見た目を"
            "改善できますが、このガイドは歴史的、鑑識、法的、医療的、本人確認に関わる detail "
            "を検証するものではありません。"
        ),
        "source_boundary": (
            "画像が共有アルバム、チャット、SNS から来た場合は、まず元画像を探してください。"
            "下記の Apple の 2048 ピクセルという数値は共有アルバムに特有のもので、すべての"
            "共有サービスに自動的に当てはまるわけではありません。"
        ),
        "result_issue": "選択した観察",
        "result_first": "最初の一歩",
        "result_limit": "重要な制限",
        "result_steps": "順序立てた次の手順",
        "result_inspect": "保持する前に確認",
        "prevention_title": "次回の撮影に役立つ5つの習慣",
        "prevention": (
            "写真がぼやけて見えるときは、前後のレンズをマイクロファイバークロスで掃除する。",
            "撮影前に被写体をタップしてピントと露出を設定する。",
            "動きや暗さが予想される場合は光を増やし、スマートフォンを安定させる。",
            "可能なときは強いデジタルズームに頼らず被写体に近づく。",
            "トリミング・編集・共有の前に、未加工のオリジナルを保管しておく。",
        ),
        "sources_title": "公式情報であり、修復の保証ではありません",
        "sources_intro": (
            "Apple はピント・露出のコントロール、レンズの確認、共有アルバムの制限について"
            "説明しています。Adobe は Enhance 機能の内容を説明しています。これらの情報源は"
            "特定の写真が修復できることを証明するものではありません。"
        ),
        "source_labels": (
            "Apple：iPhone のカメラ機能で撮影を準備する",
            "Apple：写真がぼやけているときに試す手順",
            "Apple：共有アルバムはコピーをアップロードし、写真を縮小する",
            "Adobe：Denoise、Raw Details、Super Resolution",
        ),
        "webmcp_source": "Chrome WebMCP 命令型 API プレビュー（仕様は変更される場合があります）",
        "webmcp_description": (
            "有界で自己申告された可視の観察のみから、慎重なブレ写真の次の一歩を返します。"
            "写真を受け取る、検査する、アップロードする、保存する、処理することは一切なく、"
            "画像を診断したり、復元率を算出したり、detail の復元を保証したりすることも"
            "ありません。"
        ),
        "app_title": "iPhone でコピーをプライベートに試してみたいですか？",
        "app_text": (
            "Unblurry Pro はオプションのアプリです。現在の App Store の掲載情報には、"
            "デバイス上で動作する Auto Clear、Sharpen、Denoise、Low Light、Document、"
            "Super Resolution、4× Upscale、Portrait & Restore の各モードが記載されており、"
            "1日1回の無料保存と一度限りの購入で全機能を解除できます。提供地域や正確な機能は"
            "現在の掲載情報でご確認ください。このガイドはアプリなしでも利用できます。"
        ),
        "app_cta": "App Store で Unblurry Pro を見る",
        "faq_title": "強調処理の前によくある質問",
        "faq": (
            (
                "このページは写真を見たりアップロードしたりしますか？",
                "いいえ。画像やファイルの入力欄はなく、あなたが選んだ有界な観察のみを使用します。",
            ),
            (
                "これは診断や復元予測ですか？",
                "いいえ。慎重なチェックリストを返すだけで、割合の算出も診断も約束もしません。",
            ),
            (
                "アップスケールでブレた部分の元の内容を証明できますか？",
                "できません。ピクセルを増やすと見た目は改善する場合がありますが、曖昧な detail "
                "は未確認のままです。",
            ),
            (
                "なぜ先に元画像を探す必要があるのですか？",
                "トリミング、共有コピー、繰り返しの書き出しは、元よりピクセル数が少なかったり"
                "ノイズが多かったりすることがあるためです。",
            ),
        ),
        "footer": "プライベートな案内のみ · 写真の入力なし · オリジナルを保管",
        "index_title": "プライベートなブレ写真ネクストステップガイド",
        "index_description": (
            "見えている症状を選ぶだけで、写真をアップロードせず、復元スコアも算出せずに"
            "慎重な次の一歩がわかります。"
        ),
        "inline_link": "プライベートなブレ写真ネクストステップ・チェックリストを試す",
    },
    "ko":     {
        "title": "사진을 업로드하지 않는 프라이빗 흐린 사진 다음 단계 가이드",
        "description": (
            "사진을 업로드하지 않고 눈에 보이는 증상만 선택하면 흔들림, 초점 실패, 저조도 노이즈, "
            "과도한 크롭, 압축된 사본에 대한 신중한 다음 단계를 확인할 수 있습니다."
        ),
        "tools": "무료 도구",
        "switch": "繁體中文",
        "eyebrow": "무료 · 사진 입력 없음 · 복구 점수 없음",
        "heading": "프라이빗 흐린 사진 다음 단계 가이드",
        "lead": (
            "이미 관찰한 상태만 선택하세요. 이 페이지는 신중한 순서를 제안하지만 사진을 전혀 "
            "받지 않으며 진단하거나 복구를 보장할 수 없습니다."
        ),
        "badges": (
            "이미지나 파일 입력 없음",
            "업로드나 클라우드 호출 없음",
            "복구 비율 계산 없음",
            "세부 정보 복원 보장 없음",
        ),
        "planner": "눈에 보이는 문제 설명",
        "planner_intro": (
            "가장 가까운 관찰을 선택하세요. 실제 사진에는 여러 원인이 겹칠 수 있으므로 결과는 "
            "진단이 아니라 시작용 점검표로 다뤄야 합니다."
        ),
        "issue_label": "주요 관찰 가능한 문제",
        "issue_options": {
            "motion": "피사체나 카메라가 움직였음",
            "missed-focus": "선명한 부분이 원하는 대상이 아님",
            "low-light-noise": "저조도, 입자감 또는 색상 노이즈",
            "low-resolution-crop": "이미지가 작거나 과도하게 크롭됨",
            "compressed-copy": "채팅, 소셜, 공유 앨범에서 받은 사본",
        },
        "use_label": "예상 용도",
        "use_options": {
            "casual-memory": "개인 또는 가족 추억",
            "print": "인쇄 또는 확대",
            "work-profile": "업무, 판매 등록, 프로필용",
        },
        "detail_label": "가장 중요한 세부 정보",
        "detail_options": {
            "overall-scene": "전체 장면",
            "face": "얼굴",
            "text": "글자나 문구",
        },
        "zoom_label": "디지털 줌이나 과도한 크롭을 사용함",
        "smudge_label": "렌즈에 얼룩이 있거나 가려졌을 가능성",
        "update": "신중한 다음 단계 생성",
        "issue_guidance": {
            "motion": {
                "limitation": (
                    "움직임이 있으면 세부 정보가 여러 픽셀에 흩어집니다. 이 페이지는 이미지를 "
                    "받지 않으므로 심각도를 판단할 수 없습니다."
                ),
                "first_action": (
                    "이 사본을 보정하기 전에 흔들림이 덜한 프레임, 라이브 포토 프레임 또는 원본 "
                    "연속 촬영을 먼저 찾아보세요."
                ),
                "steps": (
                    "찾을 수 있는 것 중 흔들림이 가장 적은 원본 파일에서 시작한다.",
                    "노이즈가 있을 때만 가벼운 노이즈 제거를 먼저 하고, 그 다음 적당히 선명하게 한다.",
                    "가장자리가 갈라지거나 얼굴이 달라지거나 후광이 피사체보다 두드러지면 멈춘다.",
                ),
            },
            "missed-focus": {
                "limitation": (
                    "선명화는 촬영 당시의 초점 위치를 옮길 수 없습니다. 중요한 부분에 세부 정보가 "
                    "담기지 않았다면 그대로 흐리게 남을 수 있습니다."
                ),
                "first_action": (
                    "앞뒤 프레임을 확인해 원하는 얼굴, 글자, 피사체가 실제로 초점이 맞은 버전을 "
                    "찾아보세요."
                ),
                "steps": (
                    "피사체가 가장 선명한 원본 프레임을 사용한다.",
                    "적당히 선명화한 뒤 100% 배율에서 원본과 비교한다.",
                    "생성된 것처럼 보이는 눈, 글자, 질감을 복원된 사실로 취급하지 않는다.",
                ),
            },
            "low-light-noise": {
                "limitation": (
                    "노이즈 제거는 실제 미세한 질감까지 지울 수 있고, 강한 선명화는 입자감을 "
                    "더 두드러지게 할 수 있습니다."
                ),
                "first_action": (
                    "원본 파일을 찾아 주요 문제가 흔들림인지 노이즈인지, 아니면 둘 다인지 먼저 "
                    "확인하세요."
                ),
                "steps": (
                    "먼저 노이즈를 보수적으로 줄인 뒤 선명화를 더한다.",
                    "피부, 머리카락, 옷감, 어두운 그림자 부분이 밀랍처럼 되거나 얼룩덜룩해지지 "
                    "않았는지 확인한다.",
                    "가장 날카로운 가장자리가 아니라 질감이 믿을 만한 결과를 남긴다.",
                ),
            },
            "low-resolution-crop": {
                "limitation": (
                    "업스케일은 픽셀을 추가하지만 촬영 해상도 밖에 실제로 어떤 세부 정보가 "
                    "있었는지는 증명할 수 없습니다."
                ),
                "first_action": (
                    "작은 사본을 확대하기 전에 크롭되지 않은 원본이나 가장 큰 내보내기본을 먼저 "
                    "찾아보세요."
                ),
                "steps": (
                    "구할 수 있는 가장 높은 해상도의 원본에서 시작한다.",
                    "목표 출력에 맞춰 한 번만 확대하고 반복해서 크기를 조정하지 않는다.",
                    "실제 화면이나 인쇄 크기, 그리고 100% 배율에서 결과를 확인한다.",
                ),
            },
            "compressed-copy": {
                "limitation": (
                    "공유되거나 다시 저장된 사본은 픽셀 수가 적거나 압축 손상이 있을 수 있으며 "
                    "선명화가 이를 더 두드러지게 할 수 있습니다."
                ),
                "first_action": (
                    "메시지나 소셜 미디어 사본을 보정하기 전에 원본이나 압축이 가장 적은 사본을 "
                    "먼저 요청하세요."
                ),
                "steps": (
                    "원본이 있다면 크기와 파일 출처를 비교한다.",
                    "보정 전에 저장과 공유를 반복하지 않는다.",
                    "가볍게 압축 손상을 줄인 뒤 가장자리와 작은 글자를 주의 깊게 확인한다.",
                ),
            },
        },
        "use_checks": {
            "casual-memory": "장면을 바꿔버리는 과도한 세부 정보보다 자연스러워 보이는 추억을 우선한다.",
            "print": "내보내기 전에 예상 인쇄 크기와 관람 거리를 기준으로 판단한다.",
            "work-profile": (
                "신원, 상품, 로고, 문구는 항상 사실대로 유지하고, 애매한 보정 결과를 중요한 "
                "주장의 근거로 삼지 않는다."
            ),
        },
        "detail_checks": {
            "overall-scene": "직선, 나뭇잎, 옷감, 반복 무늬에 후광이나 가짜 질감이 생기지 않았는지 확인한다.",
            "face": "눈, 치아, 헤어라인, 얼굴 비율을 손대지 않은 원본과 비교한다.",
            "text": "중요한 글자는 모두 알려진 출처와 대조하고, 불분명한 글자는 미확인 상태로 둔다.",
        },
        "zoom_note": (
            "과도한 크롭이나 디지털 줌은 촬영된 세부 정보를 줄입니다. 가능하다면 크롭되지 않은 "
            "원본으로 돌아가세요."
        ),
        "smudge_note": (
            "렌즈를 닦으면 앞으로의 촬영에는 도움이 되지만 과거의 광학적 세부 정보는 되살릴 수 "
            "없습니다. 사진이 흐릴 때 Apple은 극세사 천 사용을 권장합니다."
        ),
        "preserve_original": "보정하거나 내보내기 전에 손대지 않은 원본을 먼저 복제하거나 보관하세요.",
        "output_boundary": (
            "목표 크기에서 실제로 도움이 되는, 가장 절제된 결과를 선택하세요. 보정은 겉모습을 "
            "개선할 수 있지만 이 가이드는 역사적, 감식, 법적, 의료적, 신원 확인용 세부 정보를 "
            "검증하지 않습니다."
        ),
        "source_boundary": (
            "이미지가 공유 앨범, 채팅, 소셜 서비스에서 왔다면 먼저 원본을 찾아보세요. 아래 "
            "Apple의 2048픽셀 수치는 공유 앨범에 한정된 것이며 모든 공유 서비스에 자동으로 "
            "적용되지는 않습니다."
        ),
        "result_issue": "선택한 관찰",
        "result_first": "첫 번째 조치",
        "result_limit": "중요한 제한 사항",
        "result_steps": "순서대로 진행할 다음 단계",
        "result_inspect": "보관하기 전에 확인",
        "prevention_title": "다음 촬영을 위한 다섯 가지 습관",
        "prevention": (
            "사진이 흐리게 보일 때는 극세사 천으로 앞뒤 렌즈를 닦는다.",
            "촬영 전에 원하는 피사체를 탭해 초점과 노출을 설정한다.",
            "움직임이나 저조도가 예상되면 조명을 늘리고 휴대폰을 안정적으로 잡는다.",
            "가능하면 과도한 디지털 줌에 의존하지 말고 피사체에 더 가까이 다가간다.",
            "크롭, 편집, 공유 전에 손대지 않은 원본을 보관해 둔다.",
        ),
        "sources_title": "공식 참고 자료이며 복구를 보장하지 않습니다",
        "sources_intro": (
            "Apple은 초점 및 노출 제어, 렌즈 점검, 공유 앨범 제한을 설명합니다. Adobe는 Enhance "
            "기능이 하는 일을 설명합니다. 이 자료들 중 어느 것도 특정 사진이 복구 가능하다고 "
            "인증하지 않습니다."
        ),
        "source_labels": (
            "Apple: iPhone 카메라 도구로 촬영 준비하기",
            "Apple: 사진이 흐릴 때 시도할 수 있는 단계",
            "Apple: 공유 앨범은 사본을 업로드하고 사진을 축소함",
            "Adobe: Denoise, Raw Details 및 Super Resolution",
        ),
        "webmcp_source": "Chrome WebMCP 명령형 API 프리뷰(사양은 변경될 수 있음)",
        "webmcp_description": (
            "유한하고 스스로 선택한 관찰 값만으로 신중한 흐린 사진 다음 단계를 반환합니다. "
            "사진을 받거나 검사, 업로드, 저장, 처리하지 않으며 이미지를 진단하거나 복구 "
            "비율을 계산하거나 세부 정보 복원을 보장하지도 않습니다."
        ),
        "app_title": "iPhone에서 사본을 비공개로 테스트해 보고 싶으신가요?",
        "app_text": (
            "Unblurry Pro는 선택 사항입니다. 현재 App Store 등록 정보에는 기기 내에서 동작하는 "
            "Auto Clear, Sharpen, Denoise, Low Light, Document, Super Resolution, 4× Upscale, "
            "Portrait & Restore 모드가 설명되어 있으며, 하루 한 번 무료 저장과 일회성 잠금 해제를 "
            "제공합니다. 제공 지역과 정확한 기능은 현재 스토어 페이지를 확인하세요. 이 가이드는 "
            "앱 없이도 사용할 수 있습니다."
        ),
        "app_cta": "App Store에서 Unblurry Pro 보기",
        "faq_title": "보정 전에 자주 묻는 질문",
        "faq": (
            (
                "이 페이지가 제 사진을 보거나 업로드하나요?",
                "아니요. 이미지나 파일 입력란이 없으며 사용자가 선택한 유한한 관찰만 사용합니다.",
            ),
            (
                "이것은 진단이나 복구 예측인가요?",
                "아니요. 신중한 점검표만 반환하며 비율 계산, 진단, 결과 약속을 하지 않습니다.",
            ),
            (
                "업스케일로 흐린 부분에 원래 무엇이 있었는지 증명할 수 있나요?",
                "그럴 수 없습니다. 픽셀을 늘리면 겉모습이 개선될 수 있지만 애매한 세부 정보는 "
                "여전히 확인되지 않은 상태로 남습니다.",
            ),
            (
                "왜 원본을 먼저 찾아야 하나요?",
                "크롭, 공유 사본, 반복된 내보내기는 원본보다 픽셀 수가 적거나 손상이 더 많을 수 "
                "있기 때문입니다.",
            ),
        ),
        "footer": "프라이빗 안내만 제공 · 사진 입력 없음 · 원본 보관",
        "index_title": "프라이빗 흐린 사진 다음 단계 가이드",
        "index_description": (
            "눈에 보이는 증상만 선택하면 사진을 업로드하거나 복구 점수를 매기지 않고도 신중한 "
            "다음 단계를 확인할 수 있습니다."
        ),
        "inline_link": "프라이빗 흐린 사진 다음 단계 체크리스트 사용해 보기",
    },
    "es-ES":     {
        "title": "Guía privada de próximos pasos para fotos borrosas | Sin subir fotos",
        "description": (
            "Elige los síntomas visibles para obtener pasos conservadores ante movimiento, "
            "enfoque fallido, ruido con poca luz, un recorte fuerte o una copia comprimida, "
            "sin subir ninguna foto."
        ),
        "tools": "Herramientas gratuitas",
        "switch": "繁體中文",
        "eyebrow": "Gratis · sin subir fotos · sin puntuación de recuperación",
        "heading": "Guía privada de próximos pasos para fotos borrosas",
        "lead": (
            "Describe lo que ya observas. La página sugiere una secuencia prudente, pero "
            "nunca recibe una foto y no puede diagnosticar ni prometer una restauración."
        ),
        "badges": (
            "Sin entrada de imagen ni archivo",
            "Sin subida ni petición a la nube",
            "Sin porcentaje de recuperación",
            "Sin garantía de detalle restaurado",
        ),
        "planner": "Describe el problema visible",
        "planner_intro": (
            "Elige la observación más parecida. Una foto real puede tener varias causas a "
            "la vez, así que trata el resultado como una lista de comprobación inicial y "
            "no como un diagnóstico."
        ),
        "issue_label": "Problema visible principal",
        "issue_options": {
            "motion": "El sujeto o la cámara se movieron",
            "missed-focus": "La zona nítida no es la deseada",
            "low-light-noise": "Poca luz, grano o ruido de color",
            "low-resolution-crop": "Imagen pequeña o recorte fuerte",
            "compressed-copy": "Copia de un chat, red social o álbum compartido",
        },
        "use_label": "Uso previsto",
        "use_options": {
            "casual-memory": "Recuerdo personal o familiar",
            "print": "Impresión o ampliación",
            "work-profile": "Trabajo, anuncio o perfil",
        },
        "detail_label": "Detalle más importante",
        "detail_options": {
            "overall-scene": "Escena general",
            "face": "Rostro",
            "text": "Texto o rotulación",
        },
        "zoom_label": "Se usó zoom digital o un recorte fuerte",
        "smudge_label": "El objetivo podría estar sucio u obstruido",
        "update": "Generar próximos pasos conservadores",
        "issue_guidance": {
            "motion": {
                "limitation": (
                    "El movimiento puede repartir el detalle entre varios píxeles. Esta "
                    "página no puede saber qué tan grave es sin recibir la imagen."
                ),
                "first_action": (
                    "Busca un fotograma con menos movimiento, un fotograma de Live Photo o "
                    "la secuencia original antes de mejorar esta copia."
                ),
                "steps": (
                    "Empieza por el original sin tocar que tenga menos movimiento.",
                    "Prueba una reducción de ruido suave solo si hay ruido, y luego un "
                    "enfoque moderado.",
                    "Detente si los bordes se dividen, los rostros cambian o los halos se "
                    "notan más que el sujeto.",
                ),
            },
            "missed-focus": {
                "limitation": (
                    "El enfoque no se puede mover con el enfoque digital. Si la zona "
                    "importante nunca recibió detalle, puede seguir borrosa."
                ),
                "first_action": (
                    "Revisa los fotogramas cercanos y busca uno donde el rostro, el texto "
                    "o el sujeto deseado esté realmente enfocado."
                ),
                "steps": (
                    "Usa como fuente el fotograma original más nítido.",
                    "Aplica un enfoque moderado y compara al 100% de zoom.",
                    "No trates ojos, letras o texturas de aspecto generado como hechos "
                    "recuperados.",
                ),
            },
            "low-light-noise": {
                "limitation": (
                    "La reducción de ruido puede eliminar textura real, mientras que un "
                    "enfoque intenso puede exagerar el grano."
                ),
                "first_action": (
                    "Busca el archivo original y comprueba si el problema principal es el "
                    "desenfoque, el ruido o ambos."
                ),
                "steps": (
                    "Reduce el ruido de forma conservadora antes de añadir enfoque.",
                    "Compara piel, cabello, tela y sombras planas en busca de artefactos "
                    "cerosos o manchados.",
                    "Conserva la versión con textura más creíble, no solo el borde más "
                    "afilado.",
                ),
            },
            "low-resolution-crop": {
                "limitation": (
                    "El aumento de tamaño añade píxeles, pero no puede demostrar qué "
                    "detalle físico existía fuera de la resolución capturada."
                ),
                "first_action": (
                    "Busca el original sin recortar o la exportación más grande antes de "
                    "ampliar una copia pequeña."
                ),
                "steps": (
                    "Empieza por el original disponible de mayor resolución.",
                    "Amplía una sola vez para la salida deseada en lugar de redimensionar "
                    "varias veces.",
                    "Revisa el resultado en su tamaño real de pantalla o impresión y al "
                    "100% de zoom.",
                ),
            },
            "compressed-copy": {
                "limitation": (
                    "Una copia compartida o vuelta a guardar puede tener menos píxeles o "
                    "artefactos de compresión que el enfoque puede hacer más visibles."
                ),
                "first_action": (
                    "Pide el archivo original o la copia menos comprimida antes de intentar "
                    "arreglar una copia de mensajería o redes sociales."
                ),
                "steps": (
                    "Compara dimensiones y origen del archivo con el original si está "
                    "disponible.",
                    "Evita ciclos repetidos de guardar y compartir antes de mejorar la foto.",
                    "Usa una reducción de artefactos suave y revisa con cuidado bordes y "
                    "texto pequeño.",
                ),
            },
        },
        "use_checks": {
            "casual-memory": (
                "Prefiere un recuerdo de aspecto natural antes que un detalle agresivo que "
                "cambie la escena."
            ),
            "print": (
                "Evalúa al tamaño de impresión y distancia de visualización previstos antes "
                "de exportar."
            ),
            "work-profile": (
                "Mantén la identidad, los productos, los logotipos y el texto fieles a la "
                "realidad; nunca uses un detalle mejorado ambiguo para una afirmación "
                "importante."
            ),
        },
        "detail_checks": {
            "overall-scene": (
                "Revisa bordes rectos, follaje, telas y patrones repetidos en busca de "
                "halos o texturas falsas."
            ),
            "face": (
                "Compara ojos, dientes, línea del cabello y proporciones faciales con el "
                "original sin tocar."
            ),
            "text": (
                "Compara cada carácter importante con una fuente conocida; el texto poco "
                "claro debe seguir sin verificar."
            ),
        },
        "zoom_note": (
            "Un recorte fuerte o el zoom digital reducen el detalle capturado disponible. "
            "Vuelve al original sin recortar cuando sea posible."
        ),
        "smudge_note": (
            "Limpiar el objetivo ayuda en futuras fotos, pero no puede restaurar el detalle "
            "óptico ya perdido. Apple recomienda un paño de microfibra cuando las fotos "
            "salen borrosas."
        ),
        "preserve_original": (
            "Duplica o conserva el original sin tocar antes de cualquier mejora o "
            "exportación."
        ),
        "output_boundary": (
            "Elige el resultado menos agresivo que ayude al tamaño previsto. La mejora "
            "puede mejorar el aspecto, pero esta guía no verifica detalles históricos, "
            "forenses, legales, médicos o de identificación."
        ),
        "source_boundary": (
            "Si la imagen vino de un Álbum compartido, un chat o una red social, busca "
            "primero el original. La cifra de 2048 píxeles de Apple que se indica abajo se "
            "aplica específicamente a los Álbumes compartidos, no automáticamente a "
            "cualquier servicio para compartir."
        ),
        "result_issue": "Observación seleccionada",
        "result_first": "Primera acción",
        "result_limit": "Limitación importante",
        "result_steps": "Próximos pasos en orden",
        "result_inspect": "Revisar antes de conservar",
        "prevention_title": "Cinco hábitos de captura para la próxima vez",
        "prevention": (
            "Limpia el objetivo frontal y trasero con un paño de microfibra cuando las "
            "imágenes se vean borrosas.",
            "Toca el sujeto deseado para fijar el enfoque y la exposición antes de tomar "
            "la foto.",
            "Usa más luz y estabiliza el teléfono cuando sea probable el movimiento o la "
            "poca luz.",
            "Acércate en lugar de depender de un zoom digital fuerte cuando sea posible.",
            "Conserva un original sin tocar antes de recortar, editar o compartir.",
        ),
        "sources_title": "Contexto oficial, no una garantía de restauración",
        "sources_intro": (
            "Apple documenta los controles de enfoque y exposición, la comprobación del "
            "objetivo y los límites de los Álbumes compartidos. Adobe documenta lo que "
            "hacen sus funciones Enhance. Ninguna de estas fuentes certifica que una foto "
            "concreta se pueda recuperar."
        ),
        "source_labels": (
            "Apple: usa las herramientas de la cámara del iPhone para preparar tu toma",
            "Apple: pasos que probar cuando una foto sale borrosa",
            "Apple: los Álbumes compartidos suben una copia y reducen las fotos",
            "Adobe: Denoise, Raw Details y Super Resolution",
        ),
        "webmcp_source": "Vista previa de la API imperativa de Chrome WebMCP (sujeta a cambios)",
        "webmcp_description": (
            "Devuelve próximos pasos conservadores para fotos borrosas a partir de "
            "observaciones visibles limitadas y autoinformadas. Nunca recibe, inspecciona, "
            "sube, guarda ni procesa una foto; nunca diagnostica la imagen, calcula un "
            "porcentaje de recuperación ni garantiza el detalle restaurado."
        ),
        "app_title": "¿Quieres probar una copia en privado en el iPhone?",
        "app_text": (
            "Unblurry Pro es opcional. Su ficha actual en la App Store describe los modos "
            "Auto Clear, Sharpen, Denoise, Low Light, Document, Super Resolution, 4× "
            "Upscale y Portrait & Restore en el dispositivo, con un guardado gratuito al "
            "día y un desbloqueo único. Consulta la ficha actual para conocer la "
            "disponibilidad y las funciones exactas. Esta guía funciona sin la app."
        ),
        "app_cta": "Ver Unblurry Pro en la App Store",
        "faq_title": "Preguntas antes de mejorar la foto",
        "faq": (
            (
                "¿Esta página ve o sube mi foto?",
                "No. No tiene entrada de imagen ni de archivo y solo usa las observaciones "
                "limitadas que eliges.",
            ),
            (
                "¿Es un diagnóstico o una predicción de recuperación?",
                "No. Devuelve una lista de comprobación prudente, no un porcentaje, "
                "diagnóstico ni promesa.",
            ),
            (
                "¿Ampliar la imagen puede demostrar qué había originalmente en una zona "
                "borrosa?",
                "No. Más píxeles pueden mejorar el aspecto, pero el detalle ambiguo sigue "
                "sin verificarse.",
            ),
            (
                "¿Por qué debería buscar primero el original?",
                "Un recorte, una copia compartida o una exportación repetida pueden tener "
                "menos píxeles o más artefactos que la fuente.",
            ),
        ),
        "footer": "Solo orientación privada · sin entrada de fotos · conserva el original",
        "index_title": "Guía privada de próximos pasos para fotos borrosas",
        "index_description": (
            "Elige los síntomas visibles y obtén próximos pasos conservadores sin subir "
            "una foto ni recibir una puntuación de recuperación."
        ),
        "inline_link": "Prueba la lista de próximos pasos privada para fotos borrosas",
    },
    "pt-BR":     {
        "title": "Guia privado de próximos passos para fotos borradas | Sem enviar fotos",
        "description": (
            "Escolha os sintomas visíveis para obter próximos passos conservadores para "
            "movimento, foco errado, ruído com pouca luz, corte pesado ou cópia "
            "comprimida, sem enviar nenhuma foto."
        ),
        "tools": "Ferramentas gratuitas",
        "switch": "繁體中文",
        "eyebrow": "Grátis · sem entrada de foto · sem pontuação de recuperação",
        "heading": "Guia privado de próximos passos para fotos borradas",
        "lead": (
            "Descreva o que você já observa. A página sugere uma sequência cautelosa, mas "
            "nunca recebe uma foto e não pode diagnosticar ou prometer restauração."
        ),
        "badges": (
            "Sem entrada de imagem ou arquivo",
            "Sem envio ou chamada à nuvem",
            "Sem porcentagem de recuperação",
            "Sem garantia de detalhe restaurado",
        ),
        "planner": "Descreva o problema visível",
        "planner_intro": (
            "Use a observação mais próxima. Uma foto real pode ter várias causas ao mesmo "
            "tempo, então trate o resultado como uma lista inicial, não um diagnóstico."
        ),
        "issue_label": "Principal problema visível",
        "issue_options": {
            "motion": "O sujeito ou a câmera se moveram",
            "missed-focus": "A área nítida não é a desejada",
            "low-light-noise": "Pouca luz, granulação ou ruído de cor",
            "low-resolution-crop": "Imagem pequena ou corte pesado",
            "compressed-copy": "Cópia de chat, rede social ou álbum compartilhado",
        },
        "use_label": "Uso pretendido",
        "use_options": {
            "casual-memory": "Lembrança pessoal ou familiar",
            "print": "Impressão ou ampliação",
            "work-profile": "Trabalho, anúncio ou perfil",
        },
        "detail_label": "Detalhe mais importante",
        "detail_options": {
            "overall-scene": "Cena geral",
            "face": "Rosto",
            "text": "Texto ou letreiro",
        },
        "zoom_label": "Foi usado zoom digital ou corte pesado",
        "smudge_label": "A lente pode estar suja ou obstruída",
        "update": "Gerar próximos passos conservadores",
        "issue_guidance": {
            "motion": {
                "limitation": (
                    "O movimento pode espalhar o detalhe entre vários pixels. Esta página "
                    "não recebe a imagem, então não pode saber a gravidade."
                ),
                "first_action": (
                    "Procure um quadro com menos tremor, um quadro de Live Photo ou a "
                    "sequência original antes de melhorar esta cópia."
                ),
                "steps": (
                    "Comece pelo original sem edição com menos tremor que você conseguir "
                    "encontrar.",
                    "Tente uma redução de ruído leve apenas se houver ruído, depois "
                    "nitidez moderada.",
                    "Pare se as bordas se dividirem, os rostos mudarem ou os halos "
                    "ficarem mais visíveis que o sujeito.",
                ),
            },
            "missed-focus": {
                "limitation": (
                    "A nitidez não move o foco já capturado. Se a área importante nunca "
                    "recebeu detalhe, ela pode continuar borrada."
                ),
                "first_action": (
                    "Verifique os quadros próximos em busca de um em que o rosto, texto "
                    "ou sujeito desejado esteja realmente em foco."
                ),
                "steps": (
                    "Use o quadro original mais nítido como fonte.",
                    "Aplique nitidez moderada e compare em zoom de 100%.",
                    "Não trate olhos, letras ou texturas com aparência gerada como fatos "
                    "recuperados.",
                ),
            },
            "low-light-noise": {
                "limitation": (
                    "A redução de ruído pode remover textura fina real, enquanto a "
                    "nitidez forte pode exagerar a granulação."
                ),
                "first_action": (
                    "Encontre o arquivo original e verifique se o problema principal é "
                    "o desfoque, o ruído ou ambos."
                ),
                "steps": (
                    "Reduza o ruído de forma conservadora antes de adicionar nitidez.",
                    "Compare pele, cabelo, tecido e sombras planas em busca de "
                    "artefatos encerados ou manchados.",
                    "Mantenha a versão com textura mais confiável, não apenas a borda "
                    "mais nítida.",
                ),
            },
            "low-resolution-crop": {
                "limitation": (
                    "O aumento de escala adiciona pixels, mas não pode provar qual "
                    "detalhe físico existia fora da resolução capturada."
                ),
                "first_action": (
                    "Procure o original sem corte ou a exportação maior antes de "
                    "ampliar uma cópia pequena."
                ),
                "steps": (
                    "Comece pelo original disponível de maior resolução.",
                    "Amplie uma única vez para a saída pretendida, em vez de "
                    "redimensionar repetidamente.",
                    "Inspecione o resultado no tamanho real de tela ou impressão e em "
                    "zoom de 100%.",
                ),
            },
            "compressed-copy": {
                "limitation": (
                    "Uma cópia compartilhada ou salva novamente pode ter menos pixels "
                    "ou artefatos de compressão que a nitidez pode tornar mais visíveis."
                ),
                "first_action": (
                    "Peça o arquivo original ou a cópia menos comprimida antes de "
                    "tentar consertar uma cópia de mensagens ou rede social."
                ),
                "steps": (
                    "Compare as dimensões e a origem do arquivo com o original, se "
                    "disponível.",
                    "Evite ciclos repetidos de salvar e compartilhar antes de melhorar "
                    "a foto.",
                    "Use uma redução leve de artefatos e inspecione bordas e textos "
                    "pequenos com cuidado.",
                ),
            },
        },
        "use_checks": {
            "casual-memory": (
                "Prefira uma lembrança de aparência natural a um detalhe agressivo que "
                "muda a cena."
            ),
            "print": (
                "Avalie no tamanho de impressão e distância de visualização pretendidos "
                "antes de exportar."
            ),
            "work-profile": (
                "Mantenha identidade, produtos, logotipos e texto fiéis à realidade; "
                "nunca use um detalhe aprimorado ambíguo para uma alegação importante."
            ),
        },
        "detail_checks": {
            "overall-scene": (
                "Verifique bordas retas, folhagem, tecidos e padrões repetidos em busca "
                "de halos ou texturas falsas."
            ),
            "face": (
                "Compare olhos, dentes, linha do cabelo e proporções faciais com o "
                "original sem edição."
            ),
            "text": (
                "Compare cada caractere importante com uma fonte conhecida; texto pouco "
                "claro deve continuar não verificado."
            ),
        },
        "zoom_note": (
            "Corte pesado ou zoom digital reduz o detalhe capturado disponível. Volte ao "
            "original sem corte quando possível."
        ),
        "smudge_note": (
            "Limpar a lente ajuda em capturas futuras, mas não pode restaurar detalhes "
            "ópticos do passado. A Apple recomenda um pano de microfibra quando as fotos "
            "saem borradas."
        ),
        "preserve_original": (
            "Duplique ou preserve o original sem edição antes de qualquer melhoria ou "
            "exportação."
        ),
        "output_boundary": (
            "Escolha o resultado menos agressivo que ajude no tamanho pretendido. A "
            "melhoria pode melhorar a aparência, mas este guia não verifica detalhes "
            "históricos, forenses, legais, médicos ou de identificação."
        ),
        "source_boundary": (
            "Se a imagem veio de um Álbum Compartilhado, chat ou rede social, procure "
            "primeiro o original. O número de 2048 pixels da Apple abaixo se aplica "
            "especificamente a Álbuns Compartilhados, não automaticamente a qualquer "
            "serviço de compartilhamento."
        ),
        "result_issue": "Observação selecionada",
        "result_first": "Primeira ação",
        "result_limit": "Limitação importante",
        "result_steps": "Próximos passos em ordem",
        "result_inspect": "Inspecionar antes de manter",
        "prevention_title": "Cinco hábitos de captura para a próxima vez",
        "prevention": (
            "Limpe as lentes frontal e traseira com um pano de microfibra quando as "
            "imagens parecerem borradas.",
            "Toque no sujeito desejado para definir foco e exposição antes de tirar a "
            "foto.",
            "Use mais luz e estabilize o telefone quando movimento ou pouca luz forem "
            "prováveis.",
            "Aproxime-se em vez de depender de zoom digital pesado quando possível.",
            "Mantenha um original sem edição antes de cortar, editar ou compartilhar.",
        ),
        "sources_title": "Contexto oficial, não uma garantia de restauração",
        "sources_intro": (
            "A Apple documenta controles de foco e exposição, verificação de lente e "
            "limites de Álbuns Compartilhados. A Adobe documenta o que seus recursos "
            "Enhance fazem. Nenhuma dessas fontes certifica que uma foto específica "
            "pode ser recuperada."
        ),
        "source_labels": (
            "Apple: use as ferramentas da câmera do iPhone para preparar sua foto",
            "Apple: passos para tentar quando uma foto está borrada",
            "Apple: Álbuns Compartilhados enviam uma cópia e reduzem as fotos",
            "Adobe: Denoise, Raw Details e Super Resolution",
        ),
        "webmcp_source": "Prévia da API imperativa do Chrome WebMCP (sujeita a mudanças)",
        "webmcp_description": (
            "Retorna próximos passos conservadores para fotos borradas a partir de "
            "observações visíveis limitadas e autorrelatadas. Nunca recebe, inspeciona, "
            "envia, armazena ou processa uma foto; nunca diagnostica a imagem, calcula "
            "uma porcentagem de recuperação ou garante detalhe restaurado."
        ),
        "app_title": "Quer testar uma cópia de forma privada no iPhone?",
        "app_text": (
            "O Unblurry Pro é opcional. Sua ficha atual na App Store descreve os modos "
            "Auto Clear, Sharpen, Denoise, Low Light, Document, Super Resolution, 4× "
            "Upscale e Portrait & Restore no dispositivo, com um salvamento gratuito por "
            "dia e um desbloqueio único. Consulte a ficha atual para disponibilidade e "
            "recursos exatos. Este guia funciona sem o app."
        ),
        "app_cta": "Ver Unblurry Pro na App Store",
        "faq_title": "Perguntas antes de melhorar a foto",
        "faq": (
            (
                "Esta página vê ou envia minha foto?",
                "Não. Ela não tem entrada de imagem ou arquivo e usa apenas as "
                "observações limitadas que você escolhe.",
            ),
            (
                "Isso é um diagnóstico ou previsão de recuperação?",
                "Não. Ela retorna uma lista cautelosa, não uma porcentagem, diagnóstico "
                "ou promessa.",
            ),
            (
                "Ampliar a imagem pode provar o que havia originalmente em uma área "
                "borrada?",
                "Não. Mais pixels podem melhorar a aparência, mas o detalhe ambíguo "
                "permanece não verificado.",
            ),
            (
                "Por que devo procurar o original primeiro?",
                "Um corte, uma cópia compartilhada ou uma exportação repetida podem ter "
                "menos pixels ou mais artefatos do que a fonte.",
            ),
        ),
        "footer": "Apenas orientação privada · sem entrada de foto · preserve o original",
        "index_title": "Guia privado de próximos passos para fotos borradas",
        "index_description": (
            "Escolha os sintomas visíveis e obtenha próximos passos conservadores sem "
            "enviar uma foto ou receber uma pontuação de recuperação."
        ),
        "inline_link": "Experimente a lista de próximos passos privada para fotos borradas",
    },
    "de-DE":     {
        "title": "Privater Leitfaden für nächste Schritte bei unscharfen Fotos | Kein Foto-Upload",
        "description": (
            "Wähle sichtbare Symptome aus, um vorsichtige nächste Schritte bei Bewegung, "
            "verfehltem Fokus, Bildrauschen, starkem Zuschnitt oder einer komprimierten "
            "Kopie zu erhalten, ohne ein Foto hochzuladen."
        ),
        "tools": "Kostenlose Tools",
        "switch": "繁體中文",
        "eyebrow": "Kostenlos · kein Foto-Upload · keine Wiederherstellungs-Bewertung",
        "heading": "Privater Leitfaden für nächste Schritte bei unscharfen Fotos",
        "lead": (
            "Beschreibe nur, was du bereits beobachtest. Die Seite schlägt eine vorsichtige "
            "Reihenfolge vor, empfängt aber nie ein Foto und kann weder diagnostizieren "
            "noch eine Wiederherstellung versprechen."
        ),
        "badges": (
            "Keine Bild- oder Dateieingabe",
            "Kein Upload oder Cloud-Aufruf",
            "Keine Wiederherstellungs-Prozentangabe",
            "Keine Garantie für wiederhergestellte Details",
        ),
        "planner": "Sichtbares Problem beschreiben",
        "planner_intro": (
            "Wähle die naheliegendste Beobachtung. Ein echtes Foto kann mehrere Ursachen "
            "gleichzeitig haben, daher ist das Ergebnis eine erste Checkliste und keine "
            "Diagnose."
        ),
        "issue_label": "Wichtigstes sichtbares Problem",
        "issue_options": {
            "motion": "Motiv oder Kamera hat sich bewegt",
            "missed-focus": "Der scharfe Bereich ist nicht der gewünschte",
            "low-light-noise": "Schwaches Licht, Bildkörnung oder Farbrauschen",
            "low-resolution-crop": "Kleines Bild oder starker Zuschnitt",
            "compressed-copy": "Kopie aus Chat, sozialem Netzwerk oder geteiltem Album",
        },
        "use_label": "Vorgesehene Verwendung",
        "use_options": {
            "casual-memory": "Persönliche oder familiäre Erinnerung",
            "print": "Druck oder Vergrößerung",
            "work-profile": "Arbeit, Anzeige oder Profil",
        },
        "detail_label": "Wichtigstes Detail",
        "detail_options": {
            "overall-scene": "Gesamte Szene",
            "face": "Gesicht",
            "text": "Text oder Schriftzug",
        },
        "zoom_label": "Digitaler Zoom oder starker Zuschnitt wurde verwendet",
        "smudge_label": "Das Objektiv könnte verschmutzt oder verdeckt gewesen sein",
        "update": "Vorsichtige nächste Schritte erstellen",
        "issue_guidance": {
            "motion": {
                "limitation": (
                    "Bewegung kann Details über mehrere Pixel verteilen. Diese Seite kann "
                    "den Schweregrad ohne Empfang des Bildes nicht beurteilen."
                ),
                "first_action": (
                    "Suche vor der Bearbeitung dieser Kopie nach einem weniger verwackelten "
                    "Bild, einem Live Photo-Einzelbild oder der ursprünglichen Serie."
                ),
                "steps": (
                    "Beginne mit dem am wenigsten verwackelten unbearbeiteten Original, "
                    "das du finden kannst.",
                    "Versuche eine sanfte Rauschreduzierung nur bei vorhandenem Rauschen, "
                    "danach moderate Schärfung.",
                    "Höre auf, wenn Kanten aufreißen, Gesichter sich verändern oder Halos "
                    "stärker auffallen als das Motiv.",
                ),
            },
            "missed-focus": {
                "limitation": (
                    "Schärfung kann den beim Aufnehmen gesetzten Fokus nicht verschieben. "
                    "Wenn der wichtige Bereich nie Details erhalten hat, kann er unscharf "
                    "bleiben."
                ),
                "first_action": (
                    "Prüfe benachbarte Bilder auf eines, bei dem das gewünschte Gesicht, "
                    "der Text oder das Motiv tatsächlich scharf ist."
                ),
                "steps": (
                    "Verwende das schärfste Original-Einzelbild als Quelle.",
                    "Wende zurückhaltende Schärfung an und vergleiche bei 100 % Zoom.",
                    "Behandle generiert wirkende Augen, Buchstaben oder Texturen nicht "
                    "als wiederhergestellte Tatsache.",
                ),
            },
            "low-light-noise": {
                "limitation": (
                    "Rauschreduzierung kann echte feine Textur entfernen, während starke "
                    "Schärfung die Körnung übertreiben kann."
                ),
                "first_action": (
                    "Suche die Originaldatei und prüfe, ob das Hauptproblem Unschärfe, "
                    "Rauschen oder beides ist."
                ),
                "steps": (
                    "Reduziere Rauschen zunächst zurückhaltend, bevor du Schärfe "
                    "hinzufügst.",
                    "Prüfe Haut, Haare, Stoff und flache Schatten auf wachsartige oder "
                    "fleckige Artefakte.",
                    "Behalte die Version mit glaubwürdigerer Textur, nicht nur die "
                    "schärfste Kante.",
                ),
            },
            "low-resolution-crop": {
                "limitation": (
                    "Hochskalieren fügt Pixel hinzu, kann aber nicht beweisen, welches "
                    "physische Detail außerhalb der aufgenommenen Auflösung existierte."
                ),
                "first_action": (
                    "Suche das unbeschnittene Original oder den größten Export, bevor du "
                    "eine kleine Kopie vergrößerst."
                ),
                "steps": (
                    "Beginne mit dem verfügbaren Original mit der höchsten Auflösung.",
                    "Vergrößere einmal für die gewünschte Ausgabe, statt wiederholt die "
                    "Größe zu ändern.",
                    "Prüfe das Ergebnis in der tatsächlichen Bildschirm- oder Druckgröße "
                    "und bei 100 % Zoom.",
                ),
            },
            "compressed-copy": {
                "limitation": (
                    "Eine geteilte oder erneut gespeicherte Kopie kann weniger Pixel oder "
                    "Kompressionsartefakte haben, die Schärfung deutlicher machen kann."
                ),
                "first_action": (
                    "Bitte um die Originaldatei oder die am wenigsten komprimierte Kopie, "
                    "bevor du eine Nachrichten- oder Social-Media-Kopie reparierst."
                ),
                "steps": (
                    "Vergleiche Abmessungen und Dateiquelle mit dem Original, falls "
                    "verfügbar.",
                    "Vermeide wiederholtes Speichern und Teilen vor der Verbesserung.",
                    "Verwende eine milde Artefaktreduzierung und prüfe dann Kanten und "
                    "kleinen Text sorgfältig.",
                ),
            },
        },
        "use_checks": {
            "casual-memory": (
                "Bevorzuge eine natürlich wirkende Erinnerung gegenüber aggressiven "
                "Details, die die Szene verändern."
            ),
            "print": (
                "Beurteile das Ergebnis vor dem Export in der geplanten Druckgröße und "
                "dem Betrachtungsabstand."
            ),
            "work-profile": (
                "Halte Identität, Produkte, Logos und Schrift wahrheitsgetreu; verlasse "
                "dich nie auf mehrdeutige verbesserte Details für eine wichtige Aussage."
            ),
        },
        "detail_checks": {
            "overall-scene": (
                "Prüfe gerade Kanten, Laub, Stoff und wiederkehrende Muster auf Halos "
                "oder falsche Texturen."
            ),
            "face": (
                "Vergleiche Augen, Zähne, Haaransatz und Gesichtsproportionen mit dem "
                "unbearbeiteten Original."
            ),
            "text": (
                "Vergleiche jedes wichtige Zeichen mit einer bekannten Quelle; unklarer "
                "Text bleibt unbestätigt."
            ),
        },
        "zoom_note": (
            "Starker Zuschnitt oder digitaler Zoom verringert die verfügbaren "
            "aufgenommenen Details. Kehre nach Möglichkeit zum unbeschnittenen Original "
            "zurück."
        ),
        "smudge_note": (
            "Das Reinigen des Objektivs hilft bei künftigen Aufnahmen, kann aber "
            "vergangene optische Details nicht wiederherstellen. Apple empfiehlt ein "
            "Mikrofasertuch, wenn Fotos unscharf sind."
        ),
        "preserve_original": (
            "Dupliziere oder sichere das unbearbeitete Original vor jeder Verbesserung "
            "oder Exportierung."
        ),
        "output_boundary": (
            "Wähle das am wenigsten aggressive Ergebnis, das bei der gewünschten Größe "
            "hilft. Verbesserung kann das Erscheinungsbild verbessern, aber dieser "
            "Leitfaden überprüft keine historischen, forensischen, rechtlichen, "
            "medizinischen oder identifizierenden Details."
        ),
        "source_boundary": (
            "Wenn das Bild aus einem geteilten Album, einem Chat oder einem sozialen "
            "Dienst stammt, suche zuerst das Original. Die unten genannte 2048-Pixel-Zahl "
            "von Apple gilt speziell für geteilte Alben, nicht automatisch für jeden "
            "Freigabedienst."
        ),
        "result_issue": "Ausgewählte Beobachtung",
        "result_first": "Erster Schritt",
        "result_limit": "Wichtige Einschränkung",
        "result_steps": "Nächste Schritte in Reihenfolge",
        "result_inspect": "Vor dem Behalten prüfen",
        "prevention_title": "Fünf Aufnahmegewohnheiten für das nächste Mal",
        "prevention": (
            "Reinige Front- und Rückkamera-Objektiv mit einem Mikrofasertuch, wenn "
            "Bilder unscharf wirken.",
            "Tippe vor der Aufnahme auf das gewünschte Motiv, um Fokus und Belichtung "
            "festzulegen.",
            "Nutze mehr Licht und halte das Telefon ruhig, wenn Bewegung oder wenig "
            "Licht wahrscheinlich sind.",
            "Gehe näher heran, statt dich auf starken digitalen Zoom zu verlassen, wenn "
            "möglich.",
            "Bewahre ein unbearbeitetes Original auf, bevor du zuschneidest, bearbeitest "
            "oder teilst.",
        ),
        "sources_title": "Offizieller Kontext, keine Wiederherstellungsgarantie",
        "sources_intro": (
            "Apple dokumentiert Fokus- und Belichtungssteuerung, Objektivprüfungen und "
            "Grenzen geteilter Alben. Adobe dokumentiert, was seine Enhance-Funktionen "
            "tun. Keine dieser Quellen bestätigt, dass ein bestimmtes Foto "
            "wiederherstellbar ist."
        ),
        "source_labels": (
            "Apple: iPhone-Kamerawerkzeuge zur Vorbereitung deiner Aufnahme nutzen",
            "Apple: Schritte, die bei unscharfen Fotos versucht werden können",
            "Apple: Geteilte Alben laden eine Kopie hoch und verkleinern Fotos",
            "Adobe: Denoise, Raw Details und Super Resolution",
        ),
        "webmcp_source": "Vorschau der imperativen Chrome-WebMCP-API (kann sich ändern)",
        "webmcp_description": (
            "Liefert vorsichtige nächste Schritte bei unscharfen Fotos ausschließlich "
            "aus begrenzten, selbst angegebenen sichtbaren Beobachtungen. Empfängt, "
            "prüft, lädt hoch, speichert oder verarbeitet niemals ein Foto; "
            "diagnostiziert niemals das Bild, berechnet keinen Wiederherstellungs-"
            "Prozentsatz und garantiert kein wiederhergestelltes Detail."
        ),
        "app_title": "Möchtest du eine Kopie privat auf dem iPhone testen?",
        "app_text": (
            "Unblurry Pro ist optional. Der aktuelle App-Store-Eintrag beschreibt die "
            "geräteinternen Modi Auto Clear, Sharpen, Denoise, Low Light, Document, "
            "Super Resolution, 4× Upscale und Portrait & Restore, mit einem kostenlosen "
            "Speichern pro Tag und einer einmaligen Freischaltung. Prüfe den aktuellen "
            "Eintrag für genaue Verfügbarkeit und Funktionen. Dieser Leitfaden "
            "funktioniert auch ohne die App."
        ),
        "app_cta": "Unblurry Pro im App Store ansehen",
        "faq_title": "Fragen vor der Verbesserung",
        "faq": (
            (
                "Sieht oder lädt diese Seite mein Foto hoch?",
                "Nein. Es gibt keine Bild- oder Dateieingabe, nur die begrenzten "
                "Beobachtungen, die du auswählst.",
            ),
            (
                "Ist das eine Diagnose oder eine Wiederherstellungsprognose?",
                "Nein. Es liefert eine vorsichtige Checkliste, keinen Prozentsatz, keine "
                "Diagnose und kein Versprechen.",
            ),
            (
                "Kann Hochskalieren beweisen, was ursprünglich in einem unscharfen "
                "Bereich war?",
                "Nein. Mehr Pixel können das Erscheinungsbild verbessern, aber "
                "mehrdeutige Details bleiben unbestätigt.",
            ),
            (
                "Warum sollte ich zuerst das Original suchen?",
                "Ein Zuschnitt, eine geteilte Kopie oder ein wiederholter Export können "
                "weniger Pixel oder mehr Artefakte als die Quelle haben.",
            ),
        ),
        "footer": "Nur private Hinweise · kein Foto-Upload · Original bewahren",
        "index_title": "Privater Leitfaden für nächste Schritte bei unscharfen Fotos",
        "index_description": (
            "Wähle sichtbare Symptome aus und erhalte vorsichtige nächste Schritte, "
            "ohne ein Foto hochzuladen oder eine Wiederherstellungs-Bewertung zu "
            "erhalten."
        ),
        "inline_link": "Private Checkliste für die nächsten Schritte bei unscharfen Fotos ausprobieren",
    },
    "fr-FR":     {
        "title": "Guide privé des prochaines étapes pour photos floues | Aucune photo envoyée",
        "description": (
            "Choisissez les symptômes visibles pour obtenir des prochaines étapes "
            "prudentes en cas de flou de mouvement, de mise au point ratée, de bruit en "
            "faible lumière, de recadrage important ou de copie compressée, sans envoyer "
            "de photo."
        ),
        "tools": "Outils gratuits",
        "switch": "繁體中文",
        "eyebrow": "Gratuit · aucune photo envoyée · aucun score de récupération",
        "heading": "Guide privé des prochaines étapes pour photos floues",
        "lead": (
            "Décrivez uniquement ce que vous observez déjà. La page propose une "
            "séquence prudente, mais elle ne reçoit jamais de photo et ne peut ni "
            "diagnostiquer ni promettre une restauration."
        ),
        "badges": (
            "Aucune entrée d'image ou de fichier",
            "Aucun envoi ni appel au cloud",
            "Aucun pourcentage de récupération",
            "Aucune garantie de détail restauré",
        ),
        "planner": "Décrivez le problème visible",
        "planner_intro": (
            "Choisissez l'observation la plus proche. Une vraie photo peut avoir "
            "plusieurs causes à la fois, donc traitez le résultat comme une liste de "
            "vérification de départ, pas un diagnostic."
        ),
        "issue_label": "Principal problème visible",
        "issue_options": {
            "motion": "Le sujet ou l'appareil photo a bougé",
            "missed-focus": "La zone nette n'est pas la bonne",
            "low-light-noise": "Faible luminosité, grain ou bruit de couleur",
            "low-resolution-crop": "Image petite ou fortement recadrée",
            "compressed-copy": "Copie provenant d'un chat, d'un réseau social ou d'un "
            "album partagé",
        },
        "use_label": "Usage prévu",
        "use_options": {
            "casual-memory": "Souvenir personnel ou familial",
            "print": "Impression ou agrandissement",
            "work-profile": "Travail, annonce ou profil",
        },
        "detail_label": "Détail le plus important",
        "detail_options": {
            "overall-scene": "Scène générale",
            "face": "Visage",
            "text": "Texte ou lettrage",
        },
        "zoom_label": "Un zoom numérique ou un recadrage important a été utilisé",
        "smudge_label": "L'objectif pourrait être sale ou obstrué",
        "update": "Générer des prochaines étapes prudentes",
        "issue_guidance": {
            "motion": {
                "limitation": (
                    "Le mouvement peut répartir le détail sur plusieurs pixels. Cette "
                    "page ne peut pas juger de la gravité sans recevoir l'image."
                ),
                "first_action": (
                    "Cherchez une image moins floue, une image Live Photo ou la rafale "
                    "d'origine avant d'améliorer cette copie."
                ),
                "steps": (
                    "Partez de l'original non retouché le moins flou que vous puissiez "
                    "trouver.",
                    "Essayez une réduction de bruit légère seulement s'il y a du bruit, "
                    "puis une netteté modérée.",
                    "Arrêtez-vous si les contours se dédoublent, si les visages "
                    "changent ou si les halos deviennent plus visibles que le sujet.",
                ),
            },
            "missed-focus": {
                "limitation": (
                    "La netteté ne peut pas déplacer la mise au point déjà capturée. Si "
                    "la zone importante n'a jamais reçu de détail, elle peut rester "
                    "floue."
                ),
                "first_action": (
                    "Vérifiez les images voisines pour en trouver une où le visage, le "
                    "texte ou le sujet voulu est vraiment net."
                ),
                "steps": (
                    "Utilisez comme source l'image originale la plus nette.",
                    "Appliquez une netteté modérée et comparez à un zoom de 100 %.",
                    "Ne traitez pas les yeux, lettres ou textures d'apparence générée "
                    "comme des faits récupérés.",
                ),
            },
            "low-light-noise": {
                "limitation": (
                    "La réduction du bruit peut supprimer une texture fine réelle, "
                    "tandis qu'une netteté forte peut exagérer le grain."
                ),
                "first_action": (
                    "Trouvez le fichier original et vérifiez si le problème principal "
                    "est le flou, le bruit, ou les deux."
                ),
                "steps": (
                    "Réduisez le bruit de façon prudente avant d'ajouter de la netteté.",
                    "Comparez la peau, les cheveux, le tissu et les ombres plates pour "
                    "détecter des artefacts cireux ou tachetés.",
                    "Conservez la version dont la texture est la plus crédible, pas "
                    "seulement le contour le plus net.",
                ),
            },
            "low-resolution-crop": {
                "limitation": (
                    "L'agrandissement ajoute des pixels, mais ne peut pas prouver quel "
                    "détail physique existait en dehors de la résolution capturée."
                ),
                "first_action": (
                    "Cherchez l'original non recadré ou l'export le plus grand avant "
                    "d'agrandir une petite copie."
                ),
                "steps": (
                    "Partez de l'original disponible à la plus haute résolution.",
                    "Agrandissez une seule fois pour la sortie visée plutôt que de "
                    "redimensionner plusieurs fois.",
                    "Vérifiez le résultat à la taille réelle d'écran ou d'impression et "
                    "à un zoom de 100 %.",
                ),
            },
            "compressed-copy": {
                "limitation": (
                    "Une copie partagée ou réenregistrée peut avoir moins de pixels ou "
                    "des artefacts de compression que la netteté peut rendre plus "
                    "visibles."
                ),
                "first_action": (
                    "Demandez le fichier original ou la copie la moins compressée "
                    "avant d'essayer de réparer une copie issue d'une messagerie ou "
                    "d'un réseau social."
                ),
                "steps": (
                    "Comparez les dimensions et l'origine du fichier avec l'original "
                    "si disponible.",
                    "Évitez les cycles répétés d'enregistrement et de partage avant "
                    "l'amélioration.",
                    "Utilisez une réduction légère des artefacts, puis vérifiez "
                    "attentivement les contours et les petits textes.",
                ),
            },
        },
        "use_checks": {
            "casual-memory": (
                "Préférez un souvenir d'aspect naturel plutôt qu'un détail agressif qui "
                "change la scène."
            ),
            "print": (
                "Jugez à la taille d'impression et à la distance de visionnage prévues "
                "avant d'exporter."
            ),
            "work-profile": (
                "Gardez l'identité, les produits, les logos et le texte fidèles à la "
                "réalité ; ne vous fiez jamais à un détail amélioré ambigu pour une "
                "affirmation importante."
            ),
        },
        "detail_checks": {
            "overall-scene": (
                "Vérifiez les lignes droites, le feuillage, les tissus et les motifs "
                "répétés pour détecter des halos ou de fausses textures."
            ),
            "face": (
                "Comparez les yeux, les dents, la ligne des cheveux et les proportions "
                "du visage avec l'original non retouché."
            ),
            "text": (
                "Comparez chaque caractère important à une source connue ; un texte peu "
                "clair doit rester non vérifié."
            ),
        },
        "zoom_note": (
            "Un recadrage important ou un zoom numérique réduit le détail capturé "
            "disponible. Revenez à l'original non recadré si possible."
        ),
        "smudge_note": (
            "Nettoyer l'objectif aide pour les futures prises de vue, mais ne peut pas "
            "restaurer un détail optique déjà perdu. Apple recommande un chiffon en "
            "microfibre lorsque les photos sont floues."
        ),
        "preserve_original": (
            "Dupliquez ou conservez l'original non retouché avant toute amélioration "
            "ou exportation."
        ),
        "output_boundary": (
            "Choisissez le résultat le moins agressif qui aide à la taille prévue. "
            "L'amélioration peut améliorer l'apparence, mais ce guide ne vérifie pas "
            "les détails historiques, médico-légaux, juridiques, médicaux ou "
            "d'identification."
        ),
        "source_boundary": (
            "Si l'image provient d'un album partagé, d'un chat ou d'un service social, "
            "cherchez d'abord l'original. Le chiffre de 2048 pixels d'Apple ci-dessous "
            "s'applique spécifiquement aux albums partagés, pas automatiquement à tout "
            "service de partage."
        ),
        "result_issue": "Observation sélectionnée",
        "result_first": "Première action",
        "result_limit": "Limitation importante",
        "result_steps": "Prochaines étapes dans l'ordre",
        "result_inspect": "À vérifier avant de conserver",
        "prevention_title": "Cinq habitudes de prise de vue pour la prochaine fois",
        "prevention": (
            "Nettoyez les objectifs avant et arrière avec un chiffon en microfibre "
            "lorsque les images semblent floues.",
            "Touchez le sujet voulu pour régler la mise au point et l'exposition avant "
            "de prendre la photo.",
            "Utilisez plus de lumière et stabilisez le téléphone lorsque mouvement ou "
            "faible lumière sont probables.",
            "Rapprochez-vous plutôt que de dépendre d'un zoom numérique important quand "
            "c'est possible.",
            "Conservez un original non retouché avant de recadrer, modifier ou "
            "partager.",
        ),
        "sources_title": "Contexte officiel, pas une garantie de restauration",
        "sources_intro": (
            "Apple documente les réglages de mise au point et d'exposition, la "
            "vérification de l'objectif et les limites des albums partagés. Adobe "
            "documente ce que font ses fonctionnalités Enhance. Aucune de ces sources "
            "ne certifie qu'une photo précise peut être récupérée."
        ),
        "source_labels": (
            "Apple : utiliser les outils de l'appareil photo iPhone pour préparer "
            "votre prise de vue",
            "Apple : étapes à essayer quand une photo est floue",
            "Apple : les albums partagés téléversent une copie et réduisent les photos",
            "Adobe : Denoise, Raw Details et Super Resolution",
        ),
        "webmcp_source": "Aperçu de l'API impérative Chrome WebMCP (sujette à modification)",
        "webmcp_description": (
            "Renvoie des prochaines étapes prudentes pour les photos floues à partir "
            "d'observations visibles limitées et auto-déclarées. Ne reçoit, "
            "n'inspecte, n'envoie, ne stocke ni ne traite jamais une photo ; ne "
            "diagnostique jamais l'image, ne calcule pas de pourcentage de "
            "récupération et ne garantit pas de détail restauré."
        ),
        "app_title": "Vous voulez tester une copie en privé sur iPhone ?",
        "app_text": (
            "Unblurry Pro est facultatif. Sa fiche actuelle sur l'App Store décrit les "
            "modes Auto Clear, Sharpen, Denoise, Low Light, Document, Super Resolution, "
            "4× Upscale et Portrait & Restore fonctionnant sur l'appareil, avec un "
            "enregistrement gratuit par jour et un déverrouillage unique. Consultez la "
            "fiche actuelle pour la disponibilité et les fonctionnalités exactes. Ce "
            "guide fonctionne sans l'application."
        ),
        "app_cta": "Voir Unblurry Pro sur l'App Store",
        "faq_title": "Questions avant d'améliorer une photo",
        "faq": (
            (
                "Cette page voit-elle ou envoie-t-elle ma photo ?",
                "Non. Elle n'a aucune entrée d'image ou de fichier et n'utilise que les "
                "observations limitées que vous choisissez.",
            ),
            (
                "Est-ce un diagnostic ou une prédiction de récupération ?",
                "Non. Elle renvoie une liste de vérification prudente, pas un "
                "pourcentage, un diagnostic ou une promesse.",
            ),
            (
                "L'agrandissement peut-il prouver ce qu'il y avait à l'origine dans "
                "une zone floue ?",
                "Non. Plus de pixels peuvent améliorer l'apparence, mais un détail "
                "ambigu reste non vérifié.",
            ),
            (
                "Pourquoi devrais-je d'abord chercher l'original ?",
                "Un recadrage, une copie partagée ou un export répété peuvent avoir "
                "moins de pixels ou plus d'artefacts que la source.",
            ),
        ),
        "footer": (
            "Uniquement des conseils privés · aucune photo envoyée · conservez "
            "l'original"
        ),
        "index_title": "Guide privé des prochaines étapes pour photos floues",
        "index_description": (
            "Choisissez les symptômes visibles et obtenez des prochaines étapes "
            "prudentes sans envoyer de photo ni recevoir de score de récupération."
        ),
        "inline_link": "Essayez la liste de vérification privée des prochaines étapes pour photos floues",
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
    if locale not in ALT_LOCALES:
        raise ValueError(f"unsupported locale: {locale}")
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


def render_page(locale: str, app_public: bool = False) -> str:
    if locale not in COPY:
        raise ValueError(f"unsupported locale: {locale}")
    t = COPY[locale]
    other = "en" if locale == "zh-Hant" else "zh-Hant"
    url = canonical(locale)
    alternate = canonical(other)
    prefix = "" if locale == "en" else f"{locale}/"
    home = f"{SITE}/{prefix}index.html"
    tools = f"{SITE}/{prefix}tools/index.html"
    alternate_links = "\n".join(
        f'<link rel="alternate" hreflang="{alt}" href="{canonical(alt)}">'
        for alt in ALT_LOCALES
    )
    alternate_links += (
        f'\n<link rel="alternate" hreflang="x-default" href="{canonical("en")}">'
    )
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
        "featureList": [*t["badges"], t["source_boundary"]],
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


def insert_answer_links(pages: Path = PAGES) -> int:
    changed = 0
    for slug in TARGET_ANSWER_SLUGS:
        for locale in ALT_LOCALES:
            directory = (
                pages / "answers" if locale == "en" else pages / locale / "answers"
            )
            path = directory / slug
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            if INBOUND_LINK_CLASS in text:
                continue
            match = _APP_STORE_ANCHOR.search(text)
            if not match:
                continue
            link = (
                f'<a class="cta ghost {INBOUND_LINK_CLASS}" '
                f'data-blurry-photo-diagnostic-link="1" href="{canonical(locale)}" '
                f'rel="noopener">{html.escape(COPY[locale]["inline_link"])}</a> '
            )
            if write_text_if_changed(
                path,
                text[: match.start()] + link + text[match.start() :],
            ):
                changed += 1
    return changed


def build(pages: Path = PAGES, app_public: bool = False) -> list[str]:
    outputs = []
    for locale in ALT_LOCALES:
        relative = Path("tools") / f"{SLUG}.html"
        if locale != "en":
            relative = Path(locale) / relative
        write_text_if_changed(
            pages / relative,
            render_page(locale, app_public),
        )
        outputs.append(canonical(locale))
    for locale in ALT_LOCALES:
        index_path = (
            pages / "tools" / "index.html"
            if locale == "en"
            else pages / locale / "tools" / "index.html"
        )
        update_one_index(index_path, locale)
    insert_answer_links(pages)
    return outputs


def main() -> None:
    app_public = APP_KEY in live_app_keys(APPSTORE, PAGES, refresh=False)
    outputs = build(app_public=app_public)
    sitemap_count = write_tools_sitemap()
    for output in outputs:
        print(f"blurry photo guide -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
