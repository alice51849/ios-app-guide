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
    "vi",
    "th",
    "id",
    "tr",
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
    "vi": {
        "title": "Công cụ lập kế hoạch thời gian màn hình & chặn ứng dụng riêng tư | Phép tính minh bạch",
        "description": "Quy đổi thói quen thời gian màn hình bạn tự nhập thành phép tính tương đương theo năm và lịch chặn ứng dụng có thể đảo ngược, không truy cập dữ liệu thiết bị.",
        "tools": "Công cụ miễn phí",
        "switch": "English",
        "eyebrow": "Miễn phí · tính cục bộ · không truy cập thiết bị",
        "heading": "Công cụ lập kế hoạch thời gian màn hình và chặn ứng dụng riêng tư",
        "lead": "Nhập thói quen bạn đã biết và lên kế hoạch riêng cho một khung giờ được bảo vệ. Thời gian chặn theo lịch không bao giờ được trình bày như thời gian tiết kiệm hay sự tập trung được bảo đảm.",
        "badges": (
            "Không truy cập Screen Time hay ứng dụng",
            "Không cần tài khoản hay danh bạ",
            "Không tuyên bố tiết kiệm thời gian",
            "Không hứa hẹn tập trung hay sức khỏe",
        ),
        "planner": "So sánh thói quen quan sát được và các khối đã lên lịch",
        "planner_intro": "Phép tính đầu quy đổi thói quen bạn nhập theo năm. Phép tính thứ hai cộng tổng các khối đã lên lịch. Trang không trừ cái này cho cái kia và không dự đoán hành vi.",
        "measurement_label": "Bạn đang đo điều gì?",
        "measurement_options": {
            "total-device": "Tổng thời gian dùng máy",
            "social-media": "Mạng xã hội",
            "video": "Video",
            "games": "Trò chơi",
            "news-shopping": "Tin tức hoặc mua sắm",
        },
        "daily_label": "Số phút quan sát mỗi ngày hoạt động",
        "days_label": "Số ngày quan sát mỗi tuần",
        "block_minutes_label": "Độ dài khối chặn dự kiến",
        "block_minutes_options": {
            0: "Chưa chọn khối chặn",
            15: "15 phút",
            25: "25 phút",
            30: "30 phút",
            45: "45 phút",
            60: "60 phút",
            90: "90 phút",
            120: "120 phút",
        },
        "block_days_label": "Số ngày chặn dự kiến mỗi tuần",
        "window_label": "Khung giờ chặn",
        "window_options": {
            "custom": "Tùy chỉnh",
            "morning": "Buổi sáng",
            "work-study": "Làm việc hoặc học tập",
            "evening": "Buổi tối",
        },
        "essential_label": "Tôi đã rà soát quyền truy cập thiết yếu trước khi chặn",
        "update": "Cập nhật kế hoạch minh bạch",
        "result_observed_hours": "Số giờ quan sát tương đương theo năm",
        "result_observed_days": "Số ngày 24 giờ tương đương theo năm",
        "result_block_week": "Số phút chặn theo lịch mỗi tuần",
        "result_block_year": "Số giờ chặn theo lịch trong 52 tuần",
        "result_measurement": "Hạng mục đang đo",
        "result_plan": "Kiểm tra trước có thể đảo ngược",
        "observed_boundary": "Giá trị tương đương theo năm = phút mỗi ngày × ngày hoạt động ÷ 7 × 365. Nó chỉ phản ánh thói quen được nhập ở đây, không phải số đọc trực tiếp từ Screen Time.",
        "block_boundary": "Giờ chặn theo lịch = độ dài khối × số ngày chặn × 52. Đó chỉ là dự định trên lịch—không phải thời gian màn hình tiết kiệm được, sự chú ý lấy lại, sự tập trung đạt được hay công việc hoàn thành.",
        "window_steps": {
            "morning": (
                "Chọn giờ bắt đầu và kết thúc buổi sáng cụ thể, rồi xác nhận báo thức, di chuyển, xác thực và liên lạc thiết yếu vẫn dùng được.",
                "Chuẩn bị một hành động đầu tiên được phép trước khi khối chặn bắt đầu.",
            ),
            "work-study": (
                "Xác định kết quả công việc hoặc học tập trước khi chọn ứng dụng cần chặn.",
                "Giữ các công cụ liên lạc, xác thực, trợ năng và tra cứu cần thiết luôn khả dụng.",
            ),
            "evening": (
                "Chọn điểm kết thúc buổi tối cụ thể và bảo toàn liên lạc khẩn cấp cùng quyền truy cập chăm sóc.",
                "Chuẩn bị một hoạt động thư giãn được phép thay vì chỉ dựa vào sự cấm đoán trống rỗng.",
            ),
            "custom": (
                "Gọi tên tình huống thực tế bên ngoài trang này, rồi đặt thời điểm bắt đầu, kết thúc và lối thoát rõ ràng.",
                "Chỉ chặn các ứng dụng không liên quan đến tình huống đó và giữ các công cụ thiết yếu trong tầm tay.",
            ),
        },
        "essential_yes": "Kiểm tra lại danh sách được phép trước phiên đầu tiên và dùng khối thử ngắn nhất khả thi để thiết lập luôn có thể đảo ngược.",
        "essential_no": "Trước khi chặn bất cứ thứ gì, hãy xác định liên lạc thiết yếu, điều hướng, xác thực, trợ năng và công cụ chăm sóc, cùng một lối thoát hoặc cách khôi phục đáng tin cậy.",
        "preflight_title": "Năm bước kiểm tra trước một phiên chặn ứng dụng",
        "preflight": (
            "Khi có thể, dùng Cài đặt > Thời gian sử dụng để xác minh thói quen gốc thay vì đoán.",
            "Chỉ chọn các ứng dụng không liên quan đến khung giờ được bảo vệ cụ thể.",
            "Giữ liên lạc thiết yếu, điều hướng, xác thực, trợ năng và quyền truy cập chăm sóc luôn khả dụng.",
            "Xác định hành động thay thế được phép và cách kết thúc hoặc khôi phục phiên rõ ràng.",
            "Thử khối ngắn nhất khả thi, xem lại điều thực sự xảy ra, rồi điều chỉnh mà không tuyên bố tiết kiệm thời gian.",
        ),
        "scope_title": "Điều công cụ này không biết",
        "scope_text": "Nó không thể đọc báo cáo Screen Time, ứng dụng đã cài, thông báo, danh bạ, cài đặt thiết bị hay kết quả phiên của bạn. Nó dành cho việc lập kế hoạch cá nhân, không phải an toàn trẻ em, truy cập khẩn cấp, chăm sóc y tế, giám sát lao động hay điều trị.",
        "sources_title": "Ngữ cảnh tính năng chính thức, không phải bằng chứng kết quả",
        "sources_intro": "Apple mô tả cách xem hoạt động Screen Time, đặt lịch và giới hạn, và dùng Focus để giảm phiền nhiễu. Các tính năng đó không chứng minh một khối chặn dự kiến sẽ giảm sử dụng hay cải thiện tập trung.",
        "source_labels": (
            "Apple: bắt đầu với Thời gian sử dụng trên iPhone",
            "Apple: đặt lịch với Thời gian sử dụng trên iPhone",
            "Apple: thiết lập Focus trên iPhone",
        ),
        "webmcp_source": "Bản xem trước API mệnh lệnh Chrome WebMCP (có thể thay đổi)",
        "webmcp_description": "Tính phép quy đổi thời gian màn hình tương đương theo năm từ số phút và ngày tự nhập có giới hạn, cùng lịch chặn ứng dụng riêng có thể đảo ngược. Không bao giờ truy cập Screen Time, ứng dụng đã cài, tài khoản, danh bạ hay dữ liệu thiết bị, và không bao giờ trình bày khối chặn dự kiến như kết quả tiết kiệm thời gian, tập trung, sức khỏe hay năng suất.",
        "app_title": "Muốn một quy trình chặn tùy chọn ngay trên thiết bị?",
        "app_text": "LockHour Pro là tùy chọn. Trang App Store hiện tại của nó mô tả chặn theo giờ cho các ứng dụng đã chọn với mở khóa tự động, các chế độ Quick Focus, Deep Work, Study, Sleep Wind Down, Morning Reset và Custom, cùng widget và Live Activity. Trang cũng ghi không tài khoản, không quảng cáo hay theo dõi, dữ liệu trên thiết bị và mở khóa một lần. Hãy kiểm tra trang hiện tại để biết tính năng và tình trạng chính xác. Công cụ này hoạt động không cần ứng dụng.",
        "app_cta": "Xem LockHour Pro trên App Store",
        "faq_title": "Câu hỏi về lập kế hoạch thời gian màn hình",
        "faq": (
            (
                "Trang này có đọc Screen Time trên iPhone của tôi không?",
                "Không. Bạn tự nhập các con số có giới hạn; trang không có quyền truy cập thiết bị, ứng dụng hay tài khoản.",
            ),
            (
                "Giờ chặn theo lịch có phải là thời gian tiết kiệm được không?",
                "Không. Lịch chỉ là dự định. Trang này không bao giờ giả định khối chặn đã chạy hay đã thay đổi hành vi.",
            ),
            (
                "Mọi thời gian màn hình đều có hại sao?",
                "Không. Phép tính không gán nhãn tốt xấu cho công việc, liên lạc, điều hướng, đọc hay bất kỳ mục đích nào.",
            ),
            (
                "Có nên chặn cả ứng dụng thiết yếu không?",
                "Không. Hãy rà soát liên lạc, điều hướng, xác thực, trợ năng và quyền truy cập chăm sóc trước mọi hạn chế.",
            ),
        ),
        "footer": "Chỉ là phép tính lập kế hoạch riêng tư · không truy cập thiết bị · lên lịch không phải tiết kiệm",
        "index_title": "Công cụ lập kế hoạch thời gian màn hình & chặn ứng dụng riêng tư",
        "index_description": "Quy đổi thói quen sử dụng tự nhập theo năm và lên kế hoạch chặn có thể đảo ngược riêng, không truy cập Screen Time hay tuyên bố tiết kiệm giờ.",
    },
    "th": {
        "title": "เครื่องมือวางแผนเวลาหน้าจอและบล็อกแอปแบบส่วนตัว | คณิตศาสตร์โปร่งใส",
        "description": "แปลงรูปแบบเวลาหน้าจอที่คุณกรอกเองเป็นค่าเทียบเท่ารายปีแบบโปร่งใส พร้อมตารางบล็อกแอปที่ย้อนกลับได้ โดยไม่เข้าถึงข้อมูลอุปกรณ์",
        "tools": "เครื่องมือฟรี",
        "switch": "English",
        "eyebrow": "ฟรี · คำนวณในเครื่อง · ไม่เข้าถึงอุปกรณ์",
        "heading": "เครื่องมือวางแผนเวลาหน้าจอและบล็อกแอปแบบส่วนตัว",
        "lead": "กรอกรูปแบบที่คุณรู้อยู่แล้ว และวางแผนช่วงเวลาที่ต้องการปกป้องแยกต่างหาก เวลาบล็อกตามตารางจะไม่ถูกนำเสนอว่าเป็นเวลาที่ประหยัดได้หรือสมาธิที่รับประกัน",
        "badges": (
            "ไม่เข้าถึง Screen Time หรือแอป",
            "ไม่ต้องมีบัญชีหรือรายชื่อติดต่อ",
            "ไม่อ้างว่าประหยัดเวลา",
            "ไม่สัญญาเรื่องสมาธิหรือสุขภาพ",
        ),
        "planner": "เปรียบเทียบรูปแบบที่สังเกตได้กับบล็อกที่วางแผนไว้",
        "planner_intro": "การคำนวณแรกแปลงรูปแบบที่คุณกรอกเป็นรายปี การคำนวณที่สองรวมบล็อกตามตาราง หน้านี้ไม่นำค่าหนึ่งไปลบอีกค่าและไม่ทำนายพฤติกรรม",
        "measurement_label": "คุณกำลังวัดอะไร?",
        "measurement_options": {
            "total-device": "การใช้อุปกรณ์ทั้งหมด",
            "social-media": "โซเชียลมีเดีย",
            "video": "วิดีโอ",
            "games": "เกม",
            "news-shopping": "ข่าวหรือช้อปปิ้ง",
        },
        "daily_label": "นาทีที่สังเกตได้ต่อวันที่ใช้งาน",
        "days_label": "จำนวนวันที่สังเกตได้ต่อสัปดาห์",
        "block_minutes_label": "ความยาวบล็อกที่วางแผน",
        "block_minutes_options": {
            0: "ยังไม่เลือกบล็อก",
            15: "15 นาที",
            25: "25 นาที",
            30: "30 นาที",
            45: "45 นาที",
            60: "60 นาที",
            90: "90 นาที",
            120: "120 นาที",
        },
        "block_days_label": "จำนวนวันบล็อกที่วางแผนต่อสัปดาห์",
        "window_label": "ช่วงเวลาบล็อก",
        "window_options": {
            "custom": "กำหนดเอง",
            "morning": "ตอนเช้า",
            "work-study": "ทำงานหรือเรียน",
            "evening": "ตอนเย็น",
        },
        "essential_label": "ฉันตรวจสอบการเข้าถึงที่จำเป็นก่อนบล็อกแล้ว",
        "update": "อัปเดตแผนแบบโปร่งใส",
        "result_observed_hours": "ชั่วโมงที่สังเกตได้เทียบเท่ารายปี",
        "result_observed_days": "จำนวนวัน 24 ชั่วโมงเทียบเท่ารายปี",
        "result_block_week": "นาทีบล็อกตามตารางต่อสัปดาห์",
        "result_block_year": "ชั่วโมงบล็อกตามตารางตลอด 52 สัปดาห์",
        "result_measurement": "หมวดที่เลือกวัด",
        "result_plan": "ตรวจก่อนเริ่มแบบย้อนกลับได้",
        "observed_boundary": "ค่าเทียบเท่ารายปีใช้สูตร นาทีต่อวัน × วันที่ใช้งาน ÷ 7 × 365 ค่านี้สะท้อนเฉพาะรูปแบบที่กรอกไว้ที่นี่ ไม่ใช่ค่าที่อ่านจาก Screen Time โดยตรง",
        "block_boundary": "ชั่วโมงบล็อกตามตารางใช้สูตร ความยาวบล็อก × วันบล็อก × 52 มันเป็นเพียงความตั้งใจบนปฏิทิน—ไม่ใช่เวลาหน้าจอที่ประหยัดได้ ความสนใจที่ได้คืน สมาธิที่เพิ่มขึ้น หรืองานที่เสร็จ",
        "window_steps": {
            "morning": (
                "เลือกเวลาเริ่มและจบตอนเช้าที่แน่นอน แล้วยืนยันว่านาฬิกาปลุก การเดินทาง การยืนยันตัวตน และการติดต่อที่จำเป็นยังใช้ได้",
                "เตรียมการกระทำแรกที่อนุญาตไว้หนึ่งอย่างก่อนบล็อกเริ่ม",
            ),
            "work-study": (
                "กำหนดผลลัพธ์ของงานหรือการเรียนก่อนเลือกแอปที่จะบล็อก",
                "เก็บเครื่องมือการติดต่อ การยืนยันตัวตน การช่วยการเข้าถึง และการอ้างอิงที่จำเป็นให้พร้อมใช้",
            ),
            "evening": (
                "เลือกจุดสิ้นสุดตอนเย็นที่แน่นอน และคงการติดต่อฉุกเฉินกับการเข้าถึงการดูแลไว้",
                "เตรียมกิจกรรมผ่อนคลายที่อนุญาตแทนการพึ่งข้อห้ามที่ว่างเปล่า",
            ),
            "custom": (
                "ระบุสถานการณ์จริงนอกหน้านี้ แล้วตั้งเวลาเริ่ม เวลาจบ และทางออกที่ชัดเจน",
                "บล็อกเฉพาะแอปที่ไม่เกี่ยวกับสถานการณ์นั้น และเก็บเครื่องมือจำเป็นให้เข้าถึงได้",
            ),
        },
        "essential_yes": "ตรวจรายการที่อนุญาตอีกครั้งก่อนเซสชันแรก และใช้บล็อกทดสอบที่สั้นที่สุดเท่าที่ทำได้ เพื่อให้การตั้งค่ายังย้อนกลับได้",
        "essential_no": "ก่อนบล็อกสิ่งใด ให้ระบุการติดต่อที่จำเป็น การนำทาง การยืนยันตัวตน การช่วยการเข้าถึง และเครื่องมือดูแล พร้อมทางออกหรือวิธีกู้คืนที่เชื่อถือได้",
        "preflight_title": "ห้าข้อตรวจสอบก่อนเซสชันบล็อกแอป",
        "preflight": (
            "เมื่อทำได้ ใช้ การตั้งค่า > เวลาหน้าจอ เพื่อยืนยันรูปแบบต้นทางแทนการเดา",
            "เลือกเฉพาะแอปที่ไม่เกี่ยวข้องกับช่วงเวลาที่ต้องการปกป้อง",
            "เก็บการติดต่อที่จำเป็น การนำทาง การยืนยันตัวตน การช่วยการเข้าถึง และการเข้าถึงการดูแลให้พร้อมใช้",
            "กำหนดการกระทำทดแทนที่อนุญาต และวิธีจบหรือกู้คืนเซสชันที่ชัดเจน",
            "ทดสอบบล็อกที่สั้นที่สุดเท่าที่ทำได้ ทบทวนสิ่งที่เกิดขึ้นจริง แล้วปรับโดยไม่อ้างว่าประหยัดเวลา",
        ),
        "scope_title": "สิ่งที่เครื่องมือนี้ไม่รู้",
        "scope_text": "มันอ่านรายงาน Screen Time แอปที่ติดตั้ง การแจ้งเตือน รายชื่อติดต่อ การตั้งค่าอุปกรณ์ หรือผลของเซสชันไม่ได้ ใช้สำหรับวางแผนส่วนบุคคลเท่านั้น ไม่ใช่ความปลอดภัยเด็ก การเข้าถึงฉุกเฉิน การดูแลทางการแพทย์ การติดตามการจ้างงาน หรือการรักษา",
        "sources_title": "บริบทฟีเจอร์อย่างเป็นทางการ ไม่ใช่หลักฐานผลลัพธ์",
        "sources_intro": "Apple อธิบายการดูกิจกรรม Screen Time การตั้งตารางและขีดจำกัด และการใช้ Focus เพื่อลดสิ่งรบกวน ฟีเจอร์เหล่านั้นไม่ได้พิสูจน์ว่าบล็อกที่วางแผนจะลดการใช้หรือเพิ่มสมาธิ",
        "source_labels": (
            "Apple: เริ่มต้นกับเวลาหน้าจอบน iPhone",
            "Apple: ตั้งตารางด้วยเวลาหน้าจอบน iPhone",
            "Apple: ตั้งค่าโฟกัสบน iPhone",
        ),
        "webmcp_source": "ตัวอย่าง API เชิงคำสั่ง Chrome WebMCP (อาจเปลี่ยนแปลง)",
        "webmcp_description": "คำนวณค่าเทียบเท่ารายปีของเวลาหน้าจอแบบโปร่งใสจากนาทีและวันที่กรอกเองแบบมีขอบเขต พร้อมตารางบล็อกแอปแยกที่ย้อนกลับได้ ไม่เข้าถึง Screen Time แอปที่ติดตั้ง บัญชี รายชื่อติดต่อ หรือข้อมูลอุปกรณ์ และไม่นำเสนอบล็อกที่วางแผนว่าเป็นผลลัพธ์ด้านเวลา สมาธิ สุขภาพ หรือประสิทธิภาพ",
        "app_title": "อยากได้เวิร์กโฟลว์บล็อกบนอุปกรณ์แบบเลือกได้ไหม?",
        "app_text": "LockHour Pro เป็นตัวเลือกเสริม หน้า App Store ปัจจุบันอธิบายการบล็อกตามเวลาสำหรับแอปที่เลือกพร้อมปลดล็อกอัตโนมัติ โหมด Quick Focus, Deep Work, Study, Sleep Wind Down, Morning Reset และ Custom รวมถึงวิดเจ็ตและ Live Activity หน้าดังกล่าวยังระบุว่าไม่มีบัญชี โฆษณา หรือการติดตาม ข้อมูลอยู่ในเครื่อง และปลดล็อกครั้งเดียว โปรดตรวจหน้าปัจจุบันเพื่อดูฟีเจอร์ที่แน่นอน เครื่องมือนี้ใช้ได้โดยไม่ต้องมีแอป",
        "app_cta": "ดู LockHour Pro บน App Store",
        "faq_title": "คำถามเรื่องการวางแผนเวลาหน้าจอ",
        "faq": (
            (
                "หน้านี้อ่าน Screen Time บน iPhone ของฉันไหม?",
                "ไม่ คุณกรอกตัวเลขแบบมีขอบเขตเอง หน้านี้ไม่มีสิทธิ์เข้าถึงอุปกรณ์ แอป หรือบัญชี",
            ),
            (
                "ชั่วโมงบล็อกตามตารางเท่ากับเวลาที่ประหยัดได้ไหม?",
                "ไม่ ตารางคือความตั้งใจ หน้านี้ไม่เคยสมมติว่าบล็อกได้ทำงานหรือเปลี่ยนพฤติกรรมแล้ว",
            ),
            (
                "เวลาหน้าจอทั้งหมดเป็นอันตรายไหม?",
                "ไม่ การคำนวณไม่ตัดสินว่างาน การติดต่อ การนำทาง การอ่าน หรือการใช้งานใดดีหรือแย่",
            ),
            (
                "ควรบล็อกแอปที่จำเป็นด้วยไหม?",
                "ไม่ ตรวจการติดต่อ การนำทาง การยืนยันตัวตน การช่วยการเข้าถึง และการเข้าถึงการดูแลก่อนการจำกัดใด ๆ",
            ),
        ),
        "footer": "เป็นเพียงคณิตวางแผนส่วนตัว · ไม่เข้าถึงอุปกรณ์ · ตามตารางไม่ใช่ประหยัดได้",
        "index_title": "เครื่องมือวางแผนเวลาหน้าจอและบล็อกแอปแบบส่วนตัว",
        "index_description": "แปลงรูปแบบการใช้ที่กรอกเองเป็นรายปี และวางแผนบล็อกที่ย้อนกลับได้แยกต่างหาก โดยไม่เข้าถึง Screen Time หรืออ้างว่าประหยัดชั่วโมง",
    },
    "id": {
        "title": "Perencana Waktu Layar & Blokir Aplikasi Privat | Matematika Transparan",
        "description": "Ubah pola waktu layar yang Anda masukkan sendiri menjadi hitungan setara tahunan yang transparan dan jadwal blokir aplikasi yang dapat dibatalkan, tanpa mengakses data perangkat.",
        "tools": "Alat gratis",
        "switch": "English",
        "eyebrow": "Gratis · hitung lokal · tanpa akses perangkat",
        "heading": "Perencana waktu layar dan blokir aplikasi privat",
        "lead": "Masukkan pola yang sudah Anda ketahui dan rencanakan jendela terlindungi secara terpisah. Waktu blokir terjadwal tidak pernah disajikan sebagai waktu yang dihemat atau fokus yang dijamin.",
        "badges": (
            "Tanpa akses Screen Time atau aplikasi",
            "Tanpa akun atau akses kontak",
            "Tanpa klaim hemat waktu",
            "Tanpa janji fokus atau kesehatan",
        ),
        "planner": "Bandingkan pola yang diamati dengan blok yang direncanakan",
        "planner_intro": "Hitungan pertama menahunkan pola yang Anda masukkan. Hitungan kedua menjumlahkan blok terjadwal. Halaman ini tidak mengurangkan satu dari yang lain dan tidak memprediksi perilaku.",
        "measurement_label": "Apa yang Anda ukur?",
        "measurement_options": {
            "total-device": "Total penggunaan perangkat",
            "social-media": "Media sosial",
            "video": "Video",
            "games": "Gim",
            "news-shopping": "Berita atau belanja",
        },
        "daily_label": "Menit teramati per hari aktif",
        "days_label": "Hari teramati per minggu",
        "block_minutes_label": "Durasi blokir yang direncanakan",
        "block_minutes_options": {
            0: "Belum ada blok dipilih",
            15: "15 menit",
            25: "25 menit",
            30: "30 menit",
            45: "45 menit",
            60: "60 menit",
            90: "90 menit",
            120: "120 menit",
        },
        "block_days_label": "Hari blokir yang direncanakan per minggu",
        "window_label": "Jendela blokir",
        "window_options": {
            "custom": "Kustom",
            "morning": "Pagi",
            "work-study": "Kerja atau belajar",
            "evening": "Malam",
        },
        "essential_label": "Saya sudah meninjau akses esensial sebelum memblokir",
        "update": "Perbarui rencana transparan",
        "result_observed_hours": "Jam teramati setara tahunan",
        "result_observed_days": "Hari 24 jam setara tahunan",
        "result_block_week": "Menit blokir terjadwal per minggu",
        "result_block_year": "Jam blokir terjadwal selama 52 minggu",
        "result_measurement": "Kategori yang diukur",
        "result_plan": "Pemeriksaan awal yang dapat dibatalkan",
        "observed_boundary": "Setara tahunan memakai rumus menit harian × hari aktif ÷ 7 × 365. Nilai ini hanya mewakili pola yang dimasukkan di sini, bukan pembacaan langsung Screen Time.",
        "block_boundary": "Jam blokir terjadwal memakai durasi blok × hari blokir × 52. Itu hanyalah niat di kalender—bukan waktu layar yang dihemat, perhatian yang kembali, fokus yang diraih, atau pekerjaan yang selesai.",
        "window_steps": {
            "morning": (
                "Pilih waktu mulai dan selesai pagi yang pasti, lalu pastikan alarm, transportasi, autentikasi, dan komunikasi esensial tetap terjangkau.",
                "Siapkan satu tindakan pertama yang diizinkan sebelum blok dimulai.",
            ),
            "work-study": (
                "Tentukan hasil kerja atau belajar sebelum memilih aplikasi yang diblokir.",
                "Pastikan alat komunikasi, autentikasi, aksesibilitas, dan referensi yang dibutuhkan tetap tersedia.",
            ),
            "evening": (
                "Pilih titik akhir malam yang pasti dan pertahankan komunikasi darurat serta akses perawatan.",
                "Siapkan aktivitas relaksasi yang diizinkan alih-alih mengandalkan larangan kosong.",
            ),
            "custom": (
                "Sebutkan situasi nyata di luar halaman ini, lalu tetapkan awal, akhir, dan jalan keluar yang jelas.",
                "Blokir hanya aplikasi yang tidak terkait situasi itu dan jaga alat esensial tetap terjangkau.",
            ),
        },
        "essential_yes": "Periksa ulang daftar yang diizinkan sebelum sesi pertama dan gunakan blok uji tersingkat yang praktis agar pengaturan tetap dapat dibatalkan.",
        "essential_no": "Sebelum memblokir apa pun, kenali komunikasi esensial, navigasi, autentikasi, aksesibilitas, dan alat perawatan, plus jalan keluar atau pemulihan yang andal.",
        "preflight_title": "Lima pemeriksaan sebelum sesi blokir aplikasi",
        "preflight": (
            "Bila memungkinkan, gunakan Pengaturan > Durasi Layar untuk memverifikasi pola sumber alih-alih menebak.",
            "Pilih hanya aplikasi yang tidak terkait jendela terlindungi tertentu.",
            "Jaga komunikasi esensial, navigasi, autentikasi, aksesibilitas, dan akses perawatan tetap tersedia.",
            "Tentukan tindakan pengganti yang diizinkan dan cara jelas untuk mengakhiri atau memulihkan sesi.",
            "Uji blok tersingkat yang praktis, tinjau yang benar-benar terjadi, lalu sesuaikan tanpa mengklaim hemat waktu.",
        ),
        "scope_title": "Yang tidak diketahui perencana ini",
        "scope_text": "Ia tidak bisa membaca laporan Screen Time, aplikasi terpasang, notifikasi, kontak, pengaturan perangkat, atau hasil sesi Anda. Ini untuk perencanaan pribadi, bukan keselamatan anak, akses darurat, perawatan medis, pemantauan kerja, atau terapi.",
        "sources_title": "Konteks fitur resmi, bukan bukti hasil",
        "sources_intro": "Apple mendokumentasikan cara melihat aktivitas Screen Time, mengatur jadwal dan batas, serta memakai Focus untuk mengurangi gangguan. Fitur-fitur itu tidak membuktikan blok terencana akan mengurangi penggunaan atau meningkatkan fokus.",
        "source_labels": (
            "Apple: mulai dengan Durasi Layar di iPhone",
            "Apple: atur jadwal dengan Durasi Layar di iPhone",
            "Apple: menyiapkan Fokus di iPhone",
        ),
        "webmcp_source": "Pratinjau API imperatif Chrome WebMCP (dapat berubah)",
        "webmcp_description": "Hitung matematika waktu layar setara tahunan yang transparan dari menit dan hari yang dimasukkan sendiri secara terbatas, plus jadwal blokir aplikasi terpisah yang dapat dibatalkan. Tidak pernah mengakses Screen Time, aplikasi terpasang, akun, kontak, atau data perangkat, dan tidak pernah menyajikan blok terencana sebagai hasil hemat waktu, fokus, kesehatan, atau produktivitas.",
        "app_title": "Ingin alur blokir opsional langsung di perangkat?",
        "app_text": "LockHour Pro bersifat opsional. Halaman App Store-nya saat ini menjelaskan blokir berwaktu untuk aplikasi terpilih dengan buka kunci otomatis, mode Quick Focus, Deep Work, Study, Sleep Wind Down, Morning Reset, dan Custom, plus widget dan Live Activity. Halaman itu juga menyebut tanpa akun, iklan, atau pelacakan, data di perangkat, dan buka kunci sekali bayar. Periksa halaman terbaru untuk fitur pastinya. Perencana ini berfungsi tanpa aplikasi tersebut.",
        "app_cta": "Lihat LockHour Pro di App Store",
        "faq_title": "Pertanyaan perencanaan waktu layar",
        "faq": (
            (
                "Apakah halaman ini membaca Screen Time iPhone saya?",
                "Tidak. Anda memasukkan angka terbatas secara manual; halaman ini tidak punya akses perangkat, aplikasi, atau akun.",
            ),
            (
                "Apakah jam blokir terjadwal sama dengan waktu yang dihemat?",
                "Tidak. Jadwal adalah niat. Halaman ini tidak pernah berasumsi blok berjalan atau mengubah perilaku.",
            ),
            (
                "Apakah semua waktu layar berbahaya?",
                "Tidak. Hitungan ini tidak melabeli kerja, komunikasi, navigasi, membaca, atau penggunaan lain sebagai baik atau buruk.",
            ),
            (
                "Haruskah aplikasi esensial ikut diblokir?",
                "Tidak. Tinjau komunikasi, navigasi, autentikasi, aksesibilitas, dan akses perawatan sebelum pembatasan apa pun.",
            ),
        ),
        "footer": "Hanya matematika perencanaan privat · tanpa akses perangkat · terjadwal bukan berarti dihemat",
        "index_title": "Perencana Waktu Layar & Blokir Aplikasi Privat",
        "index_description": "Tahunkan pola penggunaan yang dimasukkan sendiri dan rencanakan blokir terpisah yang dapat dibatalkan tanpa mengakses Screen Time atau mengklaim jam yang dihemat.",
    },
    "tr": {
        "title": "Gizli Ekran Süresi ve Uygulama Engelleme Planlayıcı | Şeffaf Matematik",
        "description": "Kendi girdiğiniz ekran süresi düzenini şeffaf yıllık eşdeğer hesaba ve geri alınabilir ayrı bir uygulama engelleme programına dönüştürün; cihaz verisine erişmeden.",
        "tools": "Ücretsiz araçlar",
        "switch": "English",
        "eyebrow": "Ücretsiz · yerel hesap · cihaz erişimi yok",
        "heading": "Gizli ekran süresi ve uygulama engelleme planlayıcı",
        "lead": "Zaten bildiğiniz bir düzeni girin ve korunan bir zaman aralığını ayrıca planlayın. Programlanmış engelleme süresi asla kazanılmış zaman veya garantili odak olarak sunulmaz.",
        "badges": (
            "Ekran Süresi veya uygulama erişimi yok",
            "Hesap veya kişi erişimi yok",
            "Zaman tasarrufu iddiası yok",
            "Odak veya sağlık vaadi yok",
        ),
        "planner": "Gözlenen düzeni ve planlanan blokları karşılaştırın",
        "planner_intro": "İlk hesap girdiğiniz düzeni yıllığa çevirir. İkincisi programlanmış blokları toplar. Sayfa birini diğerinden çıkarmaz ve davranış tahmini yapmaz.",
        "measurement_label": "Neyi ölçüyorsunuz?",
        "measurement_options": {
            "total-device": "Toplam cihaz kullanımı",
            "social-media": "Sosyal medya",
            "video": "Video",
            "games": "Oyunlar",
            "news-shopping": "Haber veya alışveriş",
        },
        "daily_label": "Aktif gün başına gözlenen dakika",
        "days_label": "Haftada gözlenen gün sayısı",
        "block_minutes_label": "Planlanan engelleme süresi",
        "block_minutes_options": {
            0: "Blok seçilmedi",
            15: "15 dakika",
            25: "25 dakika",
            30: "30 dakika",
            45: "45 dakika",
            60: "60 dakika",
            90: "90 dakika",
            120: "120 dakika",
        },
        "block_days_label": "Haftada planlanan engelleme günü",
        "window_label": "Engelleme aralığı",
        "window_options": {
            "custom": "Özel",
            "morning": "Sabah",
            "work-study": "İş veya ders",
            "evening": "Akşam",
        },
        "essential_label": "Engellemeden önce temel erişimi gözden geçirdim",
        "update": "Şeffaf planı güncelle",
        "result_observed_hours": "Yıllık eşdeğer gözlenen saat",
        "result_observed_days": "Yıllık eşdeğer 24 saatlik gün",
        "result_block_week": "Haftalık programlanmış engelleme dakikası",
        "result_block_year": "52 haftada programlanmış engelleme saati",
        "result_measurement": "Seçilen ölçüm",
        "result_plan": "Geri alınabilir ön kontrol",
        "observed_boundary": "Yıllık eşdeğer, günlük dakika × aktif gün ÷ 7 × 365 formülünü kullanır. Yalnızca burada girilen düzeni temsil eder; doğrudan Ekran Süresi okuması değildir.",
        "block_boundary": "Programlanmış engelleme saatleri blok süresi × engelleme günü × 52 formülünü kullanır. Bunlar yalnızca takvim niyetidir—kazanılan ekran süresi, geri alınan dikkat, elde edilen odak veya biten iş değildir.",
        "window_steps": {
            "morning": (
                "Kesin bir sabah başlangıcı ve bitişi seçin; alarmların, ulaşımın, kimlik doğrulamanın ve temel iletişimin erişilebilir kaldığını doğrulayın.",
                "Blok başlamadan önce izin verilen tek bir ilk eylem hazırlayın.",
            ),
            "work-study": (
                "Engellenecek uygulamaları seçmeden önce iş veya ders hedefini tanımlayın.",
                "Gerekli iletişim, kimlik doğrulama, erişilebilirlik ve başvuru araçlarını kullanılabilir tutun.",
            ),
            "evening": (
                "Kesin bir akşam bitiş noktası seçin; acil iletişim ve bakım erişimini koruyun.",
                "Boş bir yasağa güvenmek yerine izin verilen bir rahatlama etkinliği hazırlayın.",
            ),
            "custom": (
                "Bu sayfanın dışındaki gerçek durumu adlandırın; net bir başlangıç, bitiş ve çıkış yolu belirleyin.",
                "Yalnızca o durumla ilgisiz uygulamaları engelleyin ve temel araçları erişilebilir tutun.",
            ),
        },
        "essential_yes": "İlk oturumdan önce izin listesini yeniden kontrol edin ve kurulumun geri alınabilir kalması için mümkün olan en kısa deneme bloğunu kullanın.",
        "essential_no": "Herhangi bir şeyi engellemeden önce temel iletişimi, navigasyonu, kimlik doğrulamayı, erişilebilirliği ve bakım araçlarını, ayrıca güvenilir bir çıkış veya kurtarma yolunu belirleyin.",
        "preflight_title": "Uygulama engelleme oturumundan önce beş kontrol",
        "preflight": (
            "Mümkünse tahmin etmek yerine Ayarlar > Ekran Süresi ile kaynak düzeni doğrulayın.",
            "Yalnızca korunan zaman aralığıyla ilgisiz uygulamaları seçin.",
            "Temel iletişim, navigasyon, kimlik doğrulama, erişilebilirlik ve bakım erişimini kullanılabilir tutun.",
            "İzin verilen alternatif eylemi ve oturumu bitirmenin veya kurtarmanın net yolunu tanımlayın.",
            "Mümkün olan en kısa bloğu deneyin, gerçekte olanı gözden geçirin, sonra zaman tasarrufu iddia etmeden ayarlayın.",
        ),
        "scope_title": "Bu planlayıcının bilmedikleri",
        "scope_text": "Ekran Süresi raporunuzu, yüklü uygulamaları, bildirimleri, kişileri, cihaz ayarlarını veya oturum sonuçlarını okuyamaz. Kişisel planlama içindir; çocuk güvenliği, acil erişim, tıbbi bakım, iş yeri takibi veya tedavi için değildir.",
        "sources_title": "Resmî özellik bağlamı, sonuç kanıtı değil",
        "sources_intro": "Apple; Ekran Süresi etkinliğini görüntülemeyi, program ve sınır belirlemeyi ve dikkat dağınıklığını azaltmak için Odak kullanmayı belgeler. Bu özellikler, planlanan bir bloğun kullanımı azaltacağını veya odağı artıracağını kanıtlamaz.",
        "source_labels": (
            "Apple: iPhone'da Ekran Süresi'ne başlama",
            "Apple: iPhone'da Ekran Süresi ile program belirleme",
            "Apple: iPhone'da Odak kurma",
        ),
        "webmcp_source": "Chrome WebMCP buyruk API önizlemesi (değişebilir)",
        "webmcp_description": "Sınırlı, kendi girilen dakika ve günlerden şeffaf yıllık eşdeğer ekran süresi hesabı ve geri alınabilir ayrı bir uygulama engelleme programı üretir. Ekran Süresi'ne, yüklü uygulamalara, hesaplara, kişilere veya cihaz verisine asla erişmez ve planlanan blokları asla kazanılmış zaman, odak, sağlık veya üretkenlik sonucu olarak sunmaz.",
        "app_title": "İsteğe bağlı, cihaz üzerinde bir engelleme akışı ister misiniz?",
        "app_text": "LockHour Pro isteğe bağlıdır. Güncel App Store sayfası; seçilen uygulamalar için otomatik kilit açmalı süreli engellemeyi, Quick Focus, Deep Work, Study, Sleep Wind Down, Morning Reset ve Custom modlarını, ayrıca widget ve Live Activity'yi anlatır. Sayfa ayrıca hesap, reklam veya takip olmadığını, verilerin cihazda kaldığını ve tek seferlik kilit açmayı belirtir. Kesin özellikler için güncel sayfayı kontrol edin. Bu planlayıcı uygulama olmadan da çalışır.",
        "app_cta": "App Store'da LockHour Pro'yu görüntüle",
        "faq_title": "Ekran süresi planlama soruları",
        "faq": (
            (
                "Bu sayfa iPhone Ekran Süremi okuyor mu?",
                "Hayır. Sınırlı sayıları elle siz girersiniz; sayfanın cihaz, uygulama veya hesap erişimi yoktur.",
            ),
            (
                "Programlanmış engelleme saatleri kazanılan zamanla aynı mı?",
                "Hayır. Program bir niyettir. Bu sayfa bloğun çalıştığını veya davranışı değiştirdiğini asla varsaymaz.",
            ),
            (
                "Tüm ekran süresi zararlı mı?",
                "Hayır. Hesap; işi, iletişimi, navigasyonu, okumayı veya başka bir kullanımı iyi ya da kötü diye etiketlemez.",
            ),
            (
                "Temel uygulamalar da engellenmeli mi?",
                "Hayır. Her kısıtlamadan önce iletişimi, navigasyonu, kimlik doğrulamayı, erişilebilirliği ve bakım erişimini gözden geçirin.",
            ),
        ),
        "footer": "Yalnızca gizli planlama matematiği · cihaz erişimi yok · programlanan, kazanılan değildir",
        "index_title": "Gizli Ekran Süresi ve Uygulama Engelleme Planlayıcı",
        "index_description": "Kendi girilen kullanım düzenini yıllığa çevirin ve Ekran Süresi'ne erişmeden, kazanılmış saat iddia etmeden ayrı geri alınabilir bloklar planlayın.",
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
