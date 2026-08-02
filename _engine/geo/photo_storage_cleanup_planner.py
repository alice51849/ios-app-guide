#!/usr/bin/env python3
"""Generate a nine-locale, private photo-storage cleanup planning tool."""

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
CONTENT_DATE = "2026-07-16"
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
    "vi": {
        "title": "Công cụ lập kế hoạch dọn dung lượng ảnh iPhone riêng tư | Không tải lên",
        "description": "Chỉ tính khoảng trống còn thiếu từ các con số dung lượng bạn nhập, rồi lập kế hoạch rà soát ảnh có thể đảo ngược, không tải lên, không quét, không ước lượng thư viện.",
        "tools": "Công cụ miễn phí",
        "switch": "English",
        "eyebrow": "Miễn phí · không truy cập ảnh · không ước tính dung lượng thu hồi",
        "heading": "Công cụ lập kế hoạch dọn dung lượng ảnh iPhone riêng tư",
        "lead": "Đo khoảng cách giữa dung lượng trống hiện tại và mục tiêu. Trang này không bao giờ đoán kích thước tệp trung bình, tỷ lệ trùng lặp hay mức dọn dẹp sẽ thu hồi.",
        "badges": ("Không ảnh, tệp hay metadata", "Không truy cập iCloud hay thiết bị", "Không xóa hay phân loại", "Không dự đoán dung lượng thu hồi"),
        "planner": "Tính khoảng trống đã biết",
        "planner_intro": "Chép các con số bạn thấy sẵn trong Cài đặt. Dung lượng Ảnh được báo riêng và không bao giờ bị coi là có thể xóa hay thu hồi.",
        "current_label": "Dung lượng trống hiện tại (GB)",
        "target_label": "Dung lượng trống mục tiêu (GB)",
        "photos_label": "Dung lượng Ảnh iPhone hiển thị (GB)",
        "icloud_label": "Trạng thái Ảnh iCloud",
        "icloud_options": {"unknown": "Chưa kiểm tra", "on-synced": "Bật — đồng bộ có vẻ hoàn tất", "on-syncing-or-paused": "Bật — đang đồng bộ, tạm dừng hoặc cảnh báo", "off": "Tắt"},
        "priority_label": "Khu vực rà soát đầu tiên",
        "priority_options": {"general": "Rà soát dung lượng tổng quát", "duplicates": "Bộ sưu tập Trùng lặp của Apple", "large-videos": "Video dung lượng lớn", "screenshots": "Ảnh chụp màn hình"},
        "copy_label": "Tôi đã xác minh bản sao độc lập của các bản gốc không thể thay thế",
        "deleted_label": "Tôi đã xem mục Đã xóa gần đây",
        "update": "Cập nhật kế hoạch riêng tư",
        "invalid_input": "Nhập đủ ba con số dung lượng từ 0 đến 2.048 GB.",
        "result_gap": "Khoảng trống còn thiếu",
        "result_current": "Dung lượng trống hiện tại",
        "result_target": "Dung lượng trống mục tiêu",
        "result_photos": "Dung lượng Ảnh được báo",
        "result_status": "Trạng thái mục tiêu",
        "met": "Đã đạt mục tiêu",
        "not_met": "Vẫn còn thiếu",
        "result_plan": "Kế hoạch rà soát có thể đảo ngược",
        "gap_boundary": "Công thức: max(0, GB trống mục tiêu − GB trống hiện tại). Cùng đơn vị GB bạn nhập. Kết quả không phải dự đoán về mức Ảnh hay PicClear có thể thu hồi.",
        "photos_boundary": "Dung lượng Ảnh được báo chỉ để tham khảo. Một số mục có thể quan trọng, đã đồng bộ, đã tối ưu, được chia sẻ, đã chỉnh sửa hoặc đã hiển thị khác trên thiết bị.",
        "icloud_steps": {
            "unknown": "Kiểm tra trạng thái đồng bộ Ảnh trước khi thay đổi bản gốc không thể thay thế; nếu Ảnh iCloud đang bật, chỉnh sửa và xóa có thể đồng bộ giữa các thiết bị.",
            "on-synced": "Ngay cả khi Ảnh iCloud có vẻ đã đồng bộ, thay đổi và xóa vẫn lan sang các thiết bị. Hãy coi đồng bộ là đồng bộ hóa, không phải bản sao độc lập duy nhất.",
            "on-syncing-or-paused": "Xử lý cảnh báo đang đồng bộ, tạm dừng hoặc thiếu dung lượng của Ảnh iCloud trước các thay đổi phá hủy, và xác minh những gì đã thực sự đồng bộ.",
            "off": "Khi Ảnh iCloud báo tắt, hãy xác minh một bản sao độc lập khác của bản gốc không thể thay thế trước các thay đổi phá hủy.",
        },
        "priority_steps": {
            "general": "Bắt đầu với gợi ý trong Cài đặt > Cài đặt chung > Dung lượng iPhone, rồi xem bộ sưu tập Trùng lặp của Apple, video và ảnh chụp màn hình theo từng nhóm nhỏ.",
            "duplicates": "Mở Ảnh > Bộ sưu tập > Tiện ích > Trùng lặp và xem từng lần gộp; bộ sưu tập có thể không xuất hiện nếu Ảnh chưa tìm thấy trùng lặp.",
            "large-videos": "Xem từng video về mức quan trọng và liệu bản gốc độc lập có mở được không; thời lượng hay thể loại không chứng minh video có thể bỏ.",
            "screenshots": "Xem bộ sưu tập Ảnh chụp màn hình theo nhóm nhỏ và giữ lại những gì cần cho hồ sơ, xác thực, du lịch, công việc hoặc trợ năng.",
        },
        "copy_yes": "Mở thử một mẫu từ bản sao độc lập trước khi xóa vĩnh viễn; riêng đồng bộ Ảnh iCloud không được coi ở đây là kho lưu độc lập.",
        "copy_no": "Dừng lại trước khi xóa vĩnh viễn và tạo bản sao độc lập kiểm chứng được của bản gốc không thể thay thế; thay đổi trên Ảnh iCloud có thể lan rộng.",
        "deleted_yes": "Kiểm tra lại Đã xóa gần đây trước khi xóa vĩnh viễn bất cứ thứ gì; xóa vĩnh viễn chấm dứt cửa sổ khôi phục thông thường.",
        "deleted_no": "Hãy xem mục Đã xóa gần đây. Apple cho biết mục đã xóa thường lưu ở đó 30 ngày; đừng dọn sạch cho đến khi chắc chắn và bản gốc thiết yếu đã được xác minh độc lập.",
        "final_step": "Sau một lô nhỏ đã rà soát, kiểm tra lại Dung lượng iPhone. Đo thay đổi thực tế thay vì giả định khoảng trống tính được bằng nội dung có thể xóa.",
        "checklist_title": "Trình tự dọn dẹp an toàn trước tiên",
        "checklist": (
            "Xác nhận dung lượng trống hiện tại và dung lượng Ảnh trong Cài đặt > Cài đặt chung > Dung lượng iPhone.",
            "Xác minh bản sao độc lập, mở được của bản gốc không thể thay thế trước khi xóa vĩnh viễn.",
            "Kiểm tra trạng thái đồng bộ Ảnh iCloud và nhớ rằng thay đổi có thể lan sang các thiết bị.",
            "Rà soát một danh mục theo lô nhỏ; đừng coi danh mục là bằng chứng một mục có thể bỏ.",
            "Kiểm tra lại Đã xóa gần đây và dung lượng thiết bị trước khi quyết định lô tiếp theo.",
        ),
        "scope_title": "Điều công cụ này không thể biết",
        "scope_text": "Nó không đọc được thư viện Ảnh, dung lượng, iCloud, album, tệp, metadata, mục ưa thích, trùng lặp, độ mờ, kích thước video hay kết quả xóa. Nó không bao giờ xác định thứ gì an toàn để xóa và không thể dự đoán dung lượng thu hồi.",
        "sources_title": "Các bước chính thức của Apple trước bất kỳ trình dọn tùy chọn nào",
        "sources_intro": "Apple mô tả Dung lượng iPhone, đồng bộ và tối ưu Ảnh iCloud, bộ sưu tập Trùng lặp và cửa sổ 30 ngày của Đã xóa gần đây. Hãy xác minh hướng dẫn hiện tại cho phiên bản iOS của bạn.",
        "source_labels": (
            "Apple: kiểm tra dung lượng trên iPhone và iPad",
            "Apple: sao lưu và đồng bộ ảnh, video với iCloud",
            "Apple: gộp ảnh và video trùng lặp trên iPhone",
            "Apple: xóa, khôi phục hoặc xóa vĩnh viễn ảnh và video",
        ),
        "webmcp_source": "Bản xem trước API mệnh lệnh Chrome WebMCP (có thể thay đổi)",
        "webmcp_description": "Chỉ tính max(0, GB trống mục tiêu trừ GB trống hiện tại) từ số liệu tự nhập có giới hạn, báo dung lượng Ảnh riêng, và trả về kế hoạch rà soát có thể đảo ngược. Không bao giờ truy cập ảnh, tệp, metadata, iCloud, tài khoản hay dung lượng thiết bị; không ước lượng dung lượng thu hồi, không phân loại phương tiện, không xóa gì.",
        "app_title": "Muốn quy trình rà soát thư viện tùy chọn ngay trên thiết bị?",
        "app_text": "PicClear Pro là tùy chọn. Trang App Store hiện tại ghi quét và xem trước miễn phí, mở khóa một lần để dọn dẹp; ứng dụng nhóm ảnh trùng, ảnh tương tự, ảnh chụp màn hình, ảnh mờ, video lớn và ảnh lớn ngay trên thiết bị để bạn rà soát. Trang cũng ghi không xóa gì cho đến khi xác nhận, có thể bảo vệ mục Ưa thích, hoạt động ngoại tuyến, không tài khoản, quảng cáo hay theo dõi. Kiểm tra trang hiện tại để biết tính năng chính xác. Công cụ này hoạt động không cần ứng dụng.",
        "app_cta": "Xem PicClear Pro trên App Store",
        "faq_title": "Câu hỏi về dọn dung lượng ảnh",
        "faq": (
            ("Trang này có quét thư viện ảnh của tôi không?", "Không. Nó chỉ nhận các con số dung lượng và lựa chọn trạng thái bạn nhập."),
            ("Khoảng trống có bằng dung lượng tôi thu hồi được không?", "Không. Đó chỉ là dung lượng trống mục tiêu trừ hiện tại, không bao giờ là ước tính về phương tiện có thể xóa."),
            ("Ảnh iCloud có phải bản sao lưu độc lập không?", "Công cụ này không coi riêng đồng bộ là độc lập vì thay đổi và xóa có thể lan sang các thiết bị."),
            ("Đã xóa gần đây có giải phóng dung lượng ngay không?", "Đừng mặc định như vậy. Apple mô tả cửa sổ khôi phục 30 ngày; hãy đo dung lượng sau các thay đổi đã rà soát."),
        ),
        "footer": "Chỉ là phép tính riêng tư · không truy cập ảnh · không xóa · không ước tính thu hồi",
        "index_title": "Công cụ lập kế hoạch dọn dung lượng ảnh riêng tư",
        "index_description": "Tính khoảng trống đã biết và lập kế hoạch rà soát có thể đảo ngược, không tải ảnh lên, không đoán dung lượng thu hồi.",
    },
    "th": {
        "title": "เครื่องมือวางแผนล้างพื้นที่รูปภาพ iPhone แบบส่วนตัว | ไม่อัปโหลด",
        "description": "คำนวณเฉพาะช่องว่างพื้นที่ว่างจากตัวเลขที่คุณกรอก แล้ววางแผนตรวจรูปภาพแบบย้อนกลับได้ โดยไม่อัปโหลด ไม่สแกน และไม่ประมาณคลังภาพ",
        "tools": "เครื่องมือฟรี",
        "switch": "English",
        "eyebrow": "ฟรี · ไม่เข้าถึงรูปภาพ · ไม่ประมาณพื้นที่คืน",
        "heading": "เครื่องมือวางแผนล้างพื้นที่รูปภาพ iPhone แบบส่วนตัว",
        "lead": "วัดช่องว่างระหว่างพื้นที่ว่างปัจจุบันกับเป้าหมาย หน้านี้ไม่เดาขนาดไฟล์เฉลี่ย อัตราภาพซ้ำ หรือปริมาณที่การล้างจะคืนมา",
        "badges": ("ไม่มีรูป ไฟล์ หรือเมทาดาทา", "ไม่เข้าถึง iCloud หรืออุปกรณ์", "ไม่ลบหรือจัดประเภท", "ไม่ทำนายพื้นที่ที่กู้คืนได้"),
        "planner": "คำนวณช่องว่างพื้นที่ที่ทราบ",
        "planner_intro": "คัดลอกตัวเลขที่เห็นได้ในการตั้งค่า พื้นที่ของรูปภาพถูกรายงานแยก และไม่ถูกถือว่าเป็นสิ่งที่ลบได้หรือกู้คืนได้",
        "current_label": "พื้นที่ว่างปัจจุบัน (GB)",
        "target_label": "พื้นที่ว่างเป้าหมาย (GB)",
        "photos_label": "พื้นที่รูปภาพที่ iPhone แสดง (GB)",
        "icloud_label": "สถานะรูปภาพ iCloud",
        "icloud_options": {"unknown": "ยังไม่ได้ตรวจ", "on-synced": "เปิด — ซิงก์ดูเหมือนเสร็จ", "on-syncing-or-paused": "เปิด — กำลังซิงก์ หยุดชั่วคราว หรือมีคำเตือน", "off": "ปิด"},
        "priority_label": "พื้นที่ตรวจอันดับแรก",
        "priority_options": {"general": "ตรวจพื้นที่ทั่วไป", "duplicates": "คอลเลกชันรายการซ้ำของ Apple", "large-videos": "วิดีโอขนาดใหญ่", "screenshots": "ภาพหน้าจอ"},
        "copy_label": "ฉันยืนยันสำเนาอิสระของต้นฉบับที่ทดแทนไม่ได้แล้ว",
        "deleted_label": "ฉันตรวจ 'เพิ่งลบ' แล้ว",
        "update": "อัปเดตแผนส่วนตัว",
        "invalid_input": "กรอกตัวเลขพื้นที่ทั้งสามค่า ตั้งแต่ 0 ถึง 2,048 GB",
        "result_gap": "ช่องว่างพื้นที่ว่างที่ยังขาด",
        "result_current": "พื้นที่ว่างปัจจุบัน",
        "result_target": "พื้นที่ว่างเป้าหมาย",
        "result_photos": "พื้นที่รูปภาพที่รายงาน",
        "result_status": "สถานะเป้าหมาย",
        "met": "ถึงเป้าหมายแล้ว",
        "not_met": "ยังขาดอยู่",
        "result_plan": "แผนตรวจแบบย้อนกลับได้",
        "gap_boundary": "สูตร: max(0, GB ว่างเป้าหมาย − GB ว่างปัจจุบัน) ใช้หน่วย GB เดียวกับที่กรอก ผลลัพธ์ไม่ใช่การทำนายว่ารูปภาพหรือ PicClear จะคืนพื้นที่ได้เท่าไร",
        "photos_boundary": "พื้นที่รูปภาพที่รายงานเป็นบริบทเท่านั้น บางรายการอาจสำคัญ ซิงก์แล้ว ถูกปรับให้เหมาะสม แชร์อยู่ แก้ไขแล้ว หรือแสดงต่างออกไปบนอุปกรณ์",
        "icloud_steps": {
            "unknown": "ตรวจสถานะซิงก์รูปภาพก่อนแก้ไขต้นฉบับที่ทดแทนไม่ได้ หากรูปภาพ iCloud เปิดอยู่ การแก้ไขและการลบอาจซิงก์ไปทุกอุปกรณ์",
            "on-synced": "แม้รูปภาพ iCloud ดูซิงก์เสร็จ การเปลี่ยนแปลงและการลบยังกระจายไปทุกอุปกรณ์ ให้ถือการซิงก์เป็นการซิงก์ ไม่ใช่สำเนาอิสระเพียงชุดเดียว",
            "on-syncing-or-paused": "แก้คำเตือนการซิงก์ หยุดชั่วคราว หรือพื้นที่ไม่พอของรูปภาพ iCloud ก่อนการเปลี่ยนแปลงเชิงทำลาย และยืนยันสิ่งที่ซิงก์แล้วจริง",
            "off": "เมื่อรูปภาพ iCloud ปิดอยู่ ให้ยืนยันสำเนาอิสระอีกชุดของต้นฉบับที่ทดแทนไม่ได้ก่อนการเปลี่ยนแปลงเชิงทำลาย",
        },
        "priority_steps": {
            "general": "เริ่มจากคำแนะนำใน การตั้งค่า > ทั่วไป > พื้นที่จัดเก็บ iPhone แล้วตรวจคอลเลกชันรายการซ้ำของ Apple วิดีโอ และภาพหน้าจอทีละกลุ่มเล็ก ๆ",
            "duplicates": "เปิด รูปภาพ > คอลเลกชัน > ยูทิลิตี้ > รายการซ้ำ และตรวจการรวมทีละรายการ คอลเลกชันอาจไม่แสดงถ้ารูปภาพยังไม่พบรายการซ้ำ",
            "large-videos": "ตรวจวิดีโอทีละรายการว่าสำคัญหรือไม่ และเปิดต้นฉบับอิสระได้หรือไม่ ความยาวหรือหมวดหมู่ไม่ได้พิสูจน์ว่าวิดีโอทิ้งได้",
            "screenshots": "ตรวจคอลเลกชันภาพหน้าจอทีละกลุ่มเล็ก และเก็บสิ่งที่จำเป็นสำหรับหลักฐาน การยืนยันตัวตน การเดินทาง งาน หรือการช่วยการเข้าถึง",
        },
        "copy_yes": "เปิดตัวอย่างจากสำเนาอิสระก่อนลบถาวร การซิงก์รูปภาพ iCloud อย่างเดียวไม่ถูกนับที่นี่ว่าเป็นคลังอิสระ",
        "copy_no": "หยุดก่อนลบถาวร และสร้างสำเนาอิสระที่ตรวจสอบได้ของต้นฉบับที่ทดแทนไม่ได้ การเปลี่ยนแปลงในรูปภาพ iCloud อาจกระจายต่อ",
        "deleted_yes": "ตรวจ 'เพิ่งลบ' อีกครั้งก่อนลบสิ่งใดถาวร การลบถาวรทำให้หมดช่วงกู้คืนตามปกติ",
        "deleted_no": "ตรวจ 'เพิ่งลบ' Apple ระบุว่ารายการที่ลบมักอยู่ที่นั่น 30 วัน อย่าล้างจนกว่าจะแน่ใจและต้นฉบับสำคัญได้รับการยืนยันแยกต่างหาก",
        "final_step": "หลังตรวจครบหนึ่งชุดเล็ก ให้ตรวจพื้นที่ iPhone อีกครั้ง วัดการเปลี่ยนแปลงจริงแทนการสมมติว่าช่องว่างที่คำนวณเท่ากับเนื้อหาที่ลบได้",
        "checklist_title": "ลำดับการล้างที่ปลอดภัยก่อน",
        "checklist": (
            "ยืนยันพื้นที่ว่างปัจจุบันและพื้นที่รูปภาพใน การตั้งค่า > ทั่วไป > พื้นที่จัดเก็บ iPhone",
            "ยืนยันสำเนาอิสระที่เปิดได้ของต้นฉบับที่ทดแทนไม่ได้ก่อนลบถาวร",
            "ตรวจสถานะซิงก์รูปภาพ iCloud และจำไว้ว่าการเปลี่ยนแปลงกระจายไปทุกอุปกรณ์ได้",
            "ตรวจทีละหมวดเป็นชุดเล็ก อย่าใช้หมวดหมู่เป็นข้อพิสูจน์ว่ารายการทิ้งได้",
            "ตรวจ 'เพิ่งลบ' และพื้นที่อุปกรณ์อีกครั้งก่อนตัดสินใจชุดถัดไป",
        ),
        "scope_title": "สิ่งที่เครื่องมือนี้ไม่มีทางรู้",
        "scope_text": "มันอ่านคลังรูปภาพ พื้นที่ iCloud อัลบั้ม ไฟล์ เมทาดาทา รายการโปรด รายการซ้ำ ความเบลอ ขนาดวิดีโอ หรือผลการลบไม่ได้ มันไม่เคยระบุว่าสิ่งใดปลอดภัยที่จะลบ และทำนายพื้นที่ที่กู้คืนได้ไม่ได้",
        "sources_title": "ขั้นตอนอย่างเป็นทางการของ Apple ก่อนใช้ตัวล้างเสริมใด ๆ",
        "sources_intro": "Apple อธิบายพื้นที่จัดเก็บ iPhone การซิงก์และปรับให้เหมาะสมของรูปภาพ iCloud คอลเลกชันรายการซ้ำ และช่วง 30 วันของ 'เพิ่งลบ' โปรดตรวจคำแนะนำปัจจุบันของ iOS รุ่นที่ใช้",
        "source_labels": (
            "Apple: ตรวจพื้นที่จัดเก็บบน iPhone และ iPad",
            "Apple: สำรองและซิงก์รูปภาพวิดีโอด้วย iCloud",
            "Apple: รวมรูปและวิดีโอที่ซ้ำบน iPhone",
            "Apple: ลบ กู้คืน หรือลบรูปและวิดีโอถาวร",
        ),
        "webmcp_source": "ตัวอย่าง API เชิงคำสั่ง Chrome WebMCP (อาจเปลี่ยนแปลง)",
        "webmcp_description": "คำนวณเพียง max(0, GB ว่างเป้าหมาย ลบ GB ว่างปัจจุบัน) จากตัวเลขที่กรอกเองแบบมีขอบเขต รายงานพื้นที่รูปภาพแยก และให้แผนตรวจแบบย้อนกลับได้ ไม่เข้าถึงรูป ไฟล์ เมทาดาทา iCloud บัญชี หรือพื้นที่อุปกรณ์ ไม่ประมาณพื้นที่กู้คืน ไม่จัดประเภทสื่อ และไม่ลบสิ่งใด",
        "app_title": "อยากได้เวิร์กโฟลว์ตรวจคลังภาพเสริมบนอุปกรณ์ไหม?",
        "app_text": "PicClear Pro เป็นตัวเลือกเสริม หน้า App Store ปัจจุบันระบุว่าการสแกนและพรีวิวฟรี ปลดล็อกครั้งเดียวเพื่อล้าง แอปจัดกลุ่มภาพซ้ำ ภาพคล้าย ภาพหน้าจอ ภาพเบลอ วิดีโอใหญ่ และภาพใหญ่บนอุปกรณ์เพื่อให้ตรวจ หน้ายังระบุว่าไม่ลบจนกว่าจะยืนยัน ปกป้องรายการโปรดได้ ทำงานออฟไลน์ ไม่มีบัญชี โฆษณา หรือการติดตาม โปรดตรวจหน้าปัจจุบันสำหรับฟีเจอร์ที่แน่นอน เครื่องมือนี้ใช้ได้โดยไม่ต้องมีแอป",
        "app_cta": "ดู PicClear Pro บน App Store",
        "faq_title": "คำถามเรื่องการล้างพื้นที่รูปภาพ",
        "faq": (
            ("หน้านี้สแกนคลังรูปของฉันไหม?", "ไม่ มันรับเฉพาะตัวเลขพื้นที่และสถานะที่คุณกรอก"),
            ("ช่องว่างเท่ากับพื้นที่ที่ฉันกู้คืนได้ไหม?", "ไม่ มันคือพื้นที่ว่างเป้าหมายลบปัจจุบันเท่านั้น ไม่ใช่การประมาณสื่อที่ลบได้"),
            ("รูปภาพ iCloud เป็นข้อมูลสำรองอิสระไหม?", "เครื่องมือนี้ไม่ถือว่าการซิงก์อย่างเดียวเป็นอิสระ เพราะการเปลี่ยนแปลงและการลบกระจายไปทุกอุปกรณ์ได้"),
            ("'เพิ่งลบ' คืนพื้นที่ทันทีไหม?", "อย่าสมมติเช่นนั้น Apple ระบุช่วงกู้คืน 30 วัน วัดพื้นที่หลังการเปลี่ยนแปลงที่ตรวจแล้ว"),
        ),
        "footer": "เป็นเพียงเลขคณิตส่วนตัว · ไม่เข้าถึงรูป · ไม่ลบ · ไม่ประมาณการกู้คืน",
        "index_title": "เครื่องมือวางแผนล้างพื้นที่รูปภาพแบบส่วนตัว",
        "index_description": "คำนวณช่องว่างพื้นที่ที่ทราบ และวางแผนตรวจแบบย้อนกลับได้ โดยไม่อัปโหลดรูปหรือเดาพื้นที่ที่กู้คืนได้",
    },
    "id": {
        "title": "Perencana Pembersihan Penyimpanan Foto iPhone Privat | Tanpa Unggah",
        "description": "Hitung hanya selisih ruang kosong dari angka penyimpanan yang Anda masukkan, lalu susun rencana tinjauan foto yang dapat dibatalkan tanpa mengunggah, memindai, atau menaksir pustaka Anda.",
        "tools": "Alat gratis",
        "switch": "English",
        "eyebrow": "Gratis · tanpa akses foto · tanpa taksiran ruang pulih",
        "heading": "Perencana pembersihan penyimpanan foto iPhone privat",
        "lead": "Ukur selisih antara ruang kosong saat ini dan target. Halaman ini tidak pernah menebak ukuran file rata-rata, tingkat duplikat, atau berapa banyak ruang yang akan pulih.",
        "badges": ("Tanpa foto, file, atau metadata", "Tanpa akses iCloud atau perangkat", "Tanpa penghapusan atau klasifikasi", "Tanpa prediksi ruang yang dapat dipulihkan"),
        "planner": "Hitung selisih penyimpanan yang diketahui",
        "planner_intro": "Salin angka yang sudah terlihat di Pengaturan. Penyimpanan Foto dilaporkan terpisah dan tidak pernah dianggap dapat dihapus atau dipulihkan.",
        "current_label": "Ruang kosong saat ini (GB)",
        "target_label": "Ruang kosong target (GB)",
        "photos_label": "Penyimpanan Foto yang ditampilkan iPhone (GB)",
        "icloud_label": "Status Foto iCloud",
        "icloud_options": {"unknown": "Belum diperiksa", "on-synced": "Aktif — sinkron tampak selesai", "on-syncing-or-paused": "Aktif — menyinkron, dijeda, atau ada peringatan", "off": "Nonaktif"},
        "priority_label": "Area tinjauan pertama",
        "priority_options": {"general": "Tinjauan penyimpanan umum", "duplicates": "Koleksi Duplikat Apple", "large-videos": "Video besar", "screenshots": "Tangkapan layar"},
        "copy_label": "Saya memverifikasi salinan independen dari master yang tak tergantikan",
        "deleted_label": "Saya sudah meninjau Baru Dihapus",
        "update": "Perbarui rencana privat",
        "invalid_input": "Masukkan ketiga angka penyimpanan dari 0 hingga 2.048 GB.",
        "result_gap": "Selisih ruang kosong tambahan",
        "result_current": "Ruang kosong saat ini",
        "result_target": "Ruang kosong target",
        "result_photos": "Penyimpanan Foto yang dilaporkan",
        "result_status": "Status target",
        "met": "Target sudah tercapai",
        "not_met": "Masih ada selisih",
        "result_plan": "Rencana tinjauan yang dapat dibatalkan",
        "gap_boundary": "Rumus selisih: max(0, GB kosong target − GB kosong saat ini). Satuan GB sama dengan yang Anda masukkan. Hasilnya bukan prediksi berapa yang bisa dipulihkan Foto atau PicClear.",
        "photos_boundary": "Penyimpanan Foto yang dilaporkan hanya konteks. Sebagian item mungkin penting, tersinkron, teroptimasi, dibagikan, sudah diedit, atau sudah ditampilkan berbeda di perangkat.",
        "icloud_steps": {
            "unknown": "Periksa status sinkron Foto sebelum mengubah master yang tak tergantikan; jika Foto iCloud aktif, pengeditan dan penghapusan dapat tersinkron antarperangkat.",
            "on-synced": "Meski Foto iCloud tampak tersinkron, perubahan dan penghapusan tetap menyebar antarperangkat. Anggap sinkron sebagai sinkronisasi, bukan satu-satunya salinan independen.",
            "on-syncing-or-paused": "Selesaikan peringatan menyinkron, jeda, atau penyimpanan Foto iCloud sebelum perubahan destruktif, dan pastikan apa yang benar-benar sudah tersinkron.",
            "off": "Saat Foto iCloud dilaporkan nonaktif, pastikan salinan independen lain dari master yang tak tergantikan sebelum perubahan destruktif.",
        },
        "priority_steps": {
            "general": "Mulai dari rekomendasi Pengaturan > Umum > Penyimpanan iPhone, lalu tinjau koleksi Duplikat Apple, video, dan tangkapan layar dalam kelompok kecil.",
            "duplicates": "Buka Foto > Koleksi > Utilitas > Duplikat dan tinjau tiap penggabungan; koleksi mungkin tidak muncul bila Foto belum menemukan duplikat.",
            "large-videos": "Tinjau video satu per satu untuk kepentingannya dan apakah master independen bisa dibuka; durasi atau kategori tidak membuktikan video layak dibuang.",
            "screenshots": "Tinjau koleksi Tangkapan Layar dalam kelompok kecil dan simpan yang dibutuhkan untuk arsip, autentikasi, perjalanan, kerja, atau aksesibilitas.",
        },
        "copy_yes": "Buka satu sampel dari salinan independen sebelum penghapusan permanen; sinkron Foto iCloud saja tidak dianggap arsip independen di sini.",
        "copy_no": "Berhenti sebelum penghapusan permanen dan buat salinan independen yang dapat diverifikasi dari master yang tak tergantikan; perubahan Foto iCloud dapat menyebar.",
        "deleted_yes": "Periksa ulang Baru Dihapus sebelum menghapus permanen apa pun; penghapusan permanen mengakhiri jendela pemulihan normal.",
        "deleted_no": "Tinjau Baru Dihapus. Apple menyebut item terhapus biasanya bertahan 30 hari di sana; jangan kosongkan sampai Anda yakin dan master penting terverifikasi independen.",
        "final_step": "Setelah satu batch kecil ditinjau, periksa lagi Penyimpanan iPhone. Ukur perubahan nyata alih-alih menganggap selisih terhitung sama dengan konten yang bisa dihapus.",
        "checklist_title": "Urutan pembersihan utamakan keselamatan",
        "checklist": (
            "Konfirmasi ruang kosong saat ini dan penyimpanan Foto di Pengaturan > Umum > Penyimpanan iPhone.",
            "Pastikan salinan independen yang bisa dibuka dari master tak tergantikan sebelum penghapusan permanen.",
            "Periksa status sinkron Foto iCloud dan ingat perubahan dapat menyebar antarperangkat.",
            "Tinjau satu kategori dalam batch kecil; jangan anggap kategori sebagai bukti item layak dibuang.",
            "Periksa ulang Baru Dihapus dan penyimpanan perangkat sebelum memutuskan batch berikutnya.",
        ),
        "scope_title": "Yang tidak dapat diketahui perencana ini",
        "scope_text": "Ia tidak bisa membaca pustaka Foto, penyimpanan, iCloud, album, file, metadata, favorit, duplikat, keburaman, ukuran video, atau hasil penghapusan. Ia tidak pernah menandai sesuatu aman dihapus dan tidak bisa memprediksi kapasitas yang pulih.",
        "sources_title": "Langkah resmi Apple sebelum pembersih opsional apa pun",
        "sources_intro": "Apple mendokumentasikan Penyimpanan iPhone, sinkronisasi dan optimasi Foto iCloud, koleksi Duplikat, dan jendela 30 hari Baru Dihapus. Verifikasi petunjuk terbaru untuk versi iOS Anda.",
        "source_labels": (
            "Apple: memeriksa penyimpanan di iPhone dan iPad",
            "Apple: mencadangkan dan menyinkronkan foto dan video dengan iCloud",
            "Apple: menggabungkan foto dan video duplikat di iPhone",
            "Apple: menghapus, memulihkan, atau menghapus permanen foto dan video",
        ),
        "webmcp_source": "Pratinjau API imperatif Chrome WebMCP (dapat berubah)",
        "webmcp_description": "Hitung hanya max(0, GB kosong target dikurangi GB kosong saat ini) dari angka yang dimasukkan sendiri secara terbatas, laporkan penyimpanan Foto terpisah, dan kembalikan rencana tinjauan yang dapat dibatalkan. Tidak pernah mengakses foto, file, metadata, iCloud, akun, atau penyimpanan perangkat; tidak pernah menaksir kapasitas pulih, mengklasifikasi media, atau menghapus apa pun.",
        "app_title": "Ingin alur tinjauan pustaka opsional di perangkat?",
        "app_text": "PicClear Pro bersifat opsional. Halaman App Store-nya saat ini menyebut pemindaian dan pratinjau gratis, dengan buka kunci sekali bayar untuk pembersihan; ia mengelompokkan duplikat, foto mirip, tangkapan layar, foto buram, video besar, dan foto besar di perangkat untuk ditinjau. Halaman itu menyebut tidak ada yang dihapus sebelum konfirmasi, Favorit dapat dilindungi, dan aplikasi bekerja offline tanpa akun, iklan, atau pelacakan. Periksa halaman terbaru untuk fitur pastinya. Perencana ini berfungsi tanpa aplikasi tersebut.",
        "app_cta": "Lihat PicClear Pro di App Store",
        "faq_title": "Pertanyaan pembersihan penyimpanan foto",
        "faq": (
            ("Apakah halaman ini memindai pustaka foto saya?", "Tidak. Ia hanya menerima angka penyimpanan dan pilihan status yang Anda masukkan."),
            ("Apakah selisih sama dengan ruang yang bisa saya pulihkan?", "Tidak. Itu hanya ruang kosong target dikurangi saat ini, bukan taksiran media yang bisa dihapus."),
            ("Apakah Foto iCloud cadangan independen?", "Perencana ini tidak menganggap sinkron saja sebagai independen karena perubahan dan penghapusan dapat menyebar antarperangkat."),
            ("Apakah Baru Dihapus langsung membebaskan ruang?", "Jangan berasumsi begitu. Apple mendokumentasikan jendela pemulihan 30 hari; ukur penyimpanan setelah perubahan yang ditinjau."),
        ),
        "footer": "Hanya aritmetika privat · tanpa akses foto · tanpa penghapusan · tanpa taksiran pemulihan",
        "index_title": "Perencana Pembersihan Penyimpanan Foto Privat",
        "index_description": "Hitung selisih ruang kosong yang diketahui dan susun rencana tinjauan yang dapat dibatalkan tanpa mengunggah foto atau menebak ruang pulih.",
    },
    "tr": {
        "title": "Gizli iPhone Fotoğraf Depolama Temizlik Planlayıcı | Yükleme Yok",
        "description": "Yalnızca girdiğiniz depolama sayılarından boş alan farkını hesaplayın, ardından kitaplığınızı yüklemeden, taramadan veya tahmin etmeden geri alınabilir bir fotoğraf inceleme planı kurun.",
        "tools": "Ücretsiz araçlar",
        "switch": "English",
        "eyebrow": "Ücretsiz · fotoğraf erişimi yok · geri kazanım tahmini yok",
        "heading": "Gizli iPhone fotoğraf depolama temizlik planlayıcı",
        "lead": "Mevcut ve hedef boş alan arasındaki farkı ölçün. Bu sayfa asla ortalama dosya boyutunu, kopya oranını veya temizliğin ne kadar alan kazandıracağını tahmin etmez.",
        "badges": ("Fotoğraf, dosya veya meta veri yok", "iCloud veya cihaz erişimi yok", "Silme veya sınıflandırma yok", "Geri kazanılabilir alan tahmini yok"),
        "planner": "Bilinen depolama farkını hesaplayın",
        "planner_intro": "Ayarlar'da zaten görebildiğiniz sayıları kopyalayın. Fotoğraf depolaması ayrı raporlanır ve asla silinebilir ya da geri kazanılabilir sayılmaz.",
        "current_label": "Mevcut boş alan (GB)",
        "target_label": "Hedef boş alan (GB)",
        "photos_label": "iPhone'un gösterdiği Fotoğraf depolaması (GB)",
        "icloud_label": "iCloud Fotoğrafları durumu",
        "icloud_options": {"unknown": "Kontrol edilmedi", "on-synced": "Açık — eşitleme tamam görünüyor", "on-syncing-or-paused": "Açık — eşitleniyor, duraklatıldı veya uyarı var", "off": "Kapalı"},
        "priority_label": "İlk inceleme alanı",
        "priority_options": {"general": "Genel depolama incelemesi", "duplicates": "Apple Kopyalar koleksiyonu", "large-videos": "Büyük videolar", "screenshots": "Ekran görüntüleri"},
        "copy_label": "Yeri doldurulamaz orijinallerin bağımsız kopyasını doğruladım",
        "deleted_label": "Son Silinenler'i inceledim",
        "update": "Gizli planı güncelle",
        "invalid_input": "Üç depolama sayısını da 0 ile 2.048 GB arasında girin.",
        "result_gap": "Ek boş alan farkı",
        "result_current": "Mevcut boş alan",
        "result_target": "Hedef boş alan",
        "result_photos": "Raporlanan Fotoğraf depolaması",
        "result_status": "Hedef durumu",
        "met": "Hedefe zaten ulaşıldı",
        "not_met": "Fark sürüyor",
        "result_plan": "Geri alınabilir inceleme planı",
        "gap_boundary": "Fark formülü: max(0, hedef boş GB − mevcut boş GB). Girdiğiniz GB birimi kullanılır. Sonuç, Fotoğraflar'ın veya PicClear'ın ne kazandıracağının tahmini değildir.",
        "photos_boundary": "Raporlanan Fotoğraf depolaması yalnız bağlamdır. Bazı öğeler önemli, eşitlenmiş, optimize edilmiş, paylaşılmış, düzenlenmiş veya cihazda farklı gösteriliyor olabilir.",
        "icloud_steps": {
            "unknown": "Yeri doldurulamaz orijinalleri değiştirmeden önce Fotoğraf eşitleme durumunu kontrol edin; iCloud Fotoğrafları açıksa düzenleme ve silmeler cihazlar arasında eşitlenebilir.",
            "on-synced": "iCloud Fotoğrafları eşitlenmiş görünse bile değişiklikler ve silmeler cihazlar arasında yayılır. Eşitlemeyi eşitleme olarak görün; tek bağımsız kopya saymayın.",
            "on-syncing-or-paused": "Yıkıcı değişikliklerden önce iCloud Fotoğrafları'nın eşitleniyor, duraklatıldı veya depolama uyarısını çözün ve gerçekte neyin eşitlendiğini doğrulayın.",
            "off": "iCloud Fotoğrafları kapalı görünüyorsa, yıkıcı değişikliklerden önce yeri doldurulamaz orijinallerin başka bir bağımsız kopyasını doğrulayın.",
        },
        "priority_steps": {
            "general": "Ayarlar > Genel > iPhone Depolama önerileriyle başlayın; ardından Apple Kopyalar koleksiyonunu, videoları ve ekran görüntülerini küçük gruplar halinde inceleyin.",
            "duplicates": "Fotoğraflar > Koleksiyonlar > Yardımcılar > Kopyalar'ı açın ve her birleştirmeyi inceleyin; Fotoğraflar kopya bulmadıysa koleksiyon görünmeyebilir.",
            "large-videos": "Videoları önem ve bağımsız orijinalin açılıp açılamadığı yönünden tek tek inceleyin; süre veya kategori bir videonun atılabilir olduğunu kanıtlamaz.",
            "screenshots": "Ekran Görüntüleri koleksiyonunu küçük gruplarla inceleyin; kayıt, kimlik doğrulama, seyahat, iş veya erişilebilirlik için gerekeni saklayın.",
        },
        "copy_yes": "Kalıcı silmeden önce bağımsız kopyadan bir örneği açın; yalnızca iCloud Fotoğrafları eşitlemesi burada bağımsız arşiv sayılmaz.",
        "copy_no": "Kalıcı silmeden önce durun ve yeri doldurulamaz orijinallerin doğrulanabilir bağımsız kopyasını oluşturun; iCloud Fotoğrafları değişiklikleri yayılabilir.",
        "deleted_yes": "Herhangi bir şeyi kalıcı silmeden önce Son Silinenler'i yeniden kontrol edin; kalıcı silme normal kurtarma penceresini bitirir.",
        "deleted_no": "Son Silinenler'i inceleyin. Apple, silinen öğelerin normalde 30 gün orada kaldığını belirtir; emin olana ve temel orijinaller bağımsız doğrulanana kadar boşaltmayın.",
        "final_step": "Küçük bir incelenmiş partiden sonra iPhone Depolama'yı yeniden kontrol edin. Hesaplanan farkın silinebilir içeriğe eşit olduğunu varsaymak yerine gerçek değişimi ölçün.",
        "checklist_title": "Önce güvenlik temizlik sırası",
        "checklist": (
            "Ayarlar > Genel > iPhone Depolama'da mevcut boş alanı ve Fotoğraf depolamasını doğrulayın.",
            "Kalıcı silmeden önce yeri doldurulamaz orijinallerin açılabilir bağımsız kopyasını doğrulayın.",
            "iCloud Fotoğrafları eşitleme durumunu kontrol edin; değişikliklerin cihazlar arasında yayılabileceğini unutmayın.",
            "Bir kategoriyi küçük partiler halinde inceleyin; kategoriyi bir öğenin atılabilir olduğunun kanıtı saymayın.",
            "Başka bir partiye karar vermeden önce Son Silinenler'i ve cihaz depolamasını yeniden kontrol edin.",
        ),
        "scope_title": "Bu planlayıcının bilemeyecekleri",
        "scope_text": "Fotoğraf kitaplığınızı, depolamayı, iCloud'u, albümleri, dosyaları, meta verileri, favorileri, kopyaları, bulanıklığı, video boyutlarını veya silme sonuçlarını okuyamaz. Hiçbir şeyi silinmesi güvenli diye işaretlemez ve geri kazanılan kapasiteyi tahmin edemez.",
        "sources_title": "Herhangi bir isteğe bağlı temizleyiciden önce resmî Apple adımları",
        "sources_intro": "Apple; iPhone Depolama'yı, iCloud Fotoğrafları eşitleme ve optimizasyonunu, Kopyalar koleksiyonunu ve 30 günlük Son Silinenler penceresini belgeler. iOS sürümünüz için güncel talimatları doğrulayın.",
        "source_labels": (
            "Apple: iPhone ve iPad'de depolamayı kontrol etme",
            "Apple: fotoğraf ve videoları iCloud ile yedekleme ve eşitleme",
            "Apple: iPhone'da yinelenen fotoğraf ve videoları birleştirme",
            "Apple: fotoğraf ve videoları silme, kurtarma veya kalıcı kaldırma",
        ),
        "webmcp_source": "Chrome WebMCP buyruk API önizlemesi (değişebilir)",
        "webmcp_description": "Sınırlı, kendi girilen sayılardan yalnızca max(0, hedef boş GB eksi mevcut boş GB) hesaplar, Fotoğraf depolamasını ayrı raporlar ve geri alınabilir bir inceleme planı döndürür. Fotoğraflara, dosyalara, meta verilere, iCloud'a, hesaplara veya cihaz depolamasına asla erişmez; geri kazanılabilir kapasiteyi tahmin etmez, medyayı sınıflandırmaz, hiçbir şeyi silmez.",
        "app_title": "İsteğe bağlı, cihaz üzerinde bir kitaplık inceleme akışı ister misiniz?",
        "app_text": "PicClear Pro isteğe bağlıdır. Güncel App Store sayfası tarama ve önizlemelerin ücretsiz olduğunu, temizlik için tek seferlik kilit açma bulunduğunu; kopyaları, benzer fotoğrafları, ekran görüntülerini, bulanık fotoğrafları, büyük videoları ve büyük fotoğrafları incelemeniz için cihazda gruplandırdığını yazar. Sayfa ayrıca onaydan önce hiçbir şeyin silinmediğini, Favoriler'in korunabildiğini ve uygulamanın hesapsız, reklamsız, takipsiz çevrimdışı çalıştığını belirtir. Kesin özellikler için güncel sayfayı kontrol edin. Bu planlayıcı uygulama olmadan da çalışır.",
        "app_cta": "App Store'da PicClear Pro'yu görüntüle",
        "faq_title": "Fotoğraf depolama temizlik soruları",
        "faq": (
            ("Bu sayfa fotoğraf kitaplığımı tarıyor mu?", "Hayır. Yalnızca girdiğiniz depolama sayılarını ve durum seçimlerini kabul eder."),
            ("Fark, geri kazanabileceğim alana eşit mi?", "Hayır. Yalnızca hedef boş alan eksi mevcut boş alandır; silinebilir medya tahmini değildir."),
            ("iCloud Fotoğrafları bağımsız bir yedek mi?", "Bu planlayıcı yalnız eşitlemeyi bağımsız saymaz; çünkü değişiklikler ve silmeler cihazlar arasında yayılabilir."),
            ("Son Silinenler alanı hemen boşaltır mı?", "Öyle varsaymayın. Apple 30 günlük kurtarma penceresini belgeler; incelenmiş değişikliklerden sonra depolamayı ölçün."),
        ),
        "footer": "Yalnızca gizli aritmetik · fotoğraf erişimi yok · silme yok · geri kazanım tahmini yok",
        "index_title": "Gizli Fotoğraf Depolama Temizlik Planlayıcı",
        "index_description": "Bilinen boş alan farkını hesaplayın ve fotoğraf yüklemeden ya da geri kazanılabilir alanı tahmin etmeden geri alınabilir bir inceleme planı kurun.",
    },
}


def _localized(
    locale: str,
    *,
    meta: tuple[str, ...],
    badges: tuple[str, ...],
    planner: tuple[str, str],
    labels: tuple[str, ...],
    icloud_options: tuple[str, ...],
    priority_options: tuple[str, ...],
    controls: tuple[str, str],
    results: tuple[str, ...],
    boundaries: tuple[str, str],
    icloud_steps: tuple[str, ...],
    priority_steps: tuple[str, ...],
    confirmations: tuple[str, ...],
    checklist: tuple[str, ...],
    scope: tuple[str, str],
    sources: tuple[str, str, tuple[str, ...]],
    webmcp: tuple[str, str],
    app: tuple[str, str, str],
    faq: tuple[str, tuple[tuple[str, str], ...]],
    footer: str,
    index: tuple[str, str],
) -> None:
    (
        title,
        description,
        tools,
        switch,
        eyebrow,
        heading,
        lead,
    ) = meta
    (
        current_label,
        target_label,
        photos_label,
        icloud_label,
        priority_label,
        copy_label,
        deleted_label,
    ) = labels
    (
        result_gap,
        result_current,
        result_target,
        result_photos,
        result_status,
        met,
        not_met,
        result_plan,
    ) = results
    sources_title, sources_intro, source_labels = sources
    faq_title, faq_items = faq
    COPY[locale] = {
        "title": title,
        "description": description,
        "tools": tools,
        "switch": switch,
        "eyebrow": eyebrow,
        "heading": heading,
        "lead": lead,
        "badges": badges,
        "planner": planner[0],
        "planner_intro": planner[1],
        "current_label": current_label,
        "target_label": target_label,
        "photos_label": photos_label,
        "icloud_label": icloud_label,
        "icloud_options": dict(zip(ICLOUD_STATUSES, icloud_options, strict=True)),
        "priority_label": priority_label,
        "priority_options": dict(zip(PRIORITIES, priority_options, strict=True)),
        "copy_label": copy_label,
        "deleted_label": deleted_label,
        "update": controls[0],
        "invalid_input": controls[1],
        "result_gap": result_gap,
        "result_current": result_current,
        "result_target": result_target,
        "result_photos": result_photos,
        "result_status": result_status,
        "met": met,
        "not_met": not_met,
        "result_plan": result_plan,
        "gap_boundary": boundaries[0],
        "photos_boundary": boundaries[1],
        "icloud_steps": dict(zip(ICLOUD_STATUSES, icloud_steps, strict=True)),
        "priority_steps": dict(zip(PRIORITIES, priority_steps, strict=True)),
        "copy_yes": confirmations[0],
        "copy_no": confirmations[1],
        "deleted_yes": confirmations[2],
        "deleted_no": confirmations[3],
        "final_step": confirmations[4],
        "checklist_title": checklist[0],
        "checklist": checklist[1:],
        "scope_title": scope[0],
        "scope_text": scope[1],
        "sources_title": sources_title,
        "sources_intro": sources_intro,
        "source_labels": source_labels,
        "webmcp_source": webmcp[0],
        "webmcp_description": webmcp[1],
        "app_title": app[0],
        "app_text": app[1],
        "app_cta": app[2],
        "faq_title": faq_title,
        "faq": faq_items,
        "footer": footer,
        "index_title": index[0],
        "index_description": index[1],
    }


_localized(
    "es-ES",
    meta=(
        "Planificador privado para liberar espacio de fotos en iPhone | Sin subir archivos",
        "Calcula solo la diferencia de espacio libre con los datos que introduces y crea una revisión reversible sin subir, escanear ni estimar tu fototeca.",
        "Herramientas gratis",
        "English",
        "Gratis · sin acceso a fotos · sin estimar espacio recuperable",
        "Planificador privado para liberar espacio de fotos en iPhone",
        "Mide la diferencia entre el espacio libre actual y el objetivo sin adivinar tamaños, duplicados ni cuánto recuperarás.",
    ),
    badges=(
        "Sin fotos, archivos ni metadatos",
        "Sin acceso al dispositivo ni a iCloud",
        "Sin borrar ni clasificar",
        "Sin predecir espacio recuperable",
    ),
    planner=(
        "Calcula una diferencia de espacio conocida",
        "Copia cifras visibles en Ajustes. El espacio de Fotos se muestra aparte y nunca se considera borrable ni recuperable.",
    ),
    labels=(
        "Espacio libre actual (GB)",
        "Espacio libre objetivo (GB)",
        "Espacio de Fotos indicado por el iPhone (GB)",
        "Estado de Fotos en iCloud",
        "Primera zona que revisar",
        "He comprobado una copia independiente de los originales irremplazables",
        "He revisado Eliminado recientemente",
    ),
    icloud_options=(
        "Sin comprobar",
        "Activado: la sincronización parece completa",
        "Activado: sincronizando, en pausa o con aviso",
        "Desactivado",
    ),
    priority_options=(
        "Revisión general del almacenamiento",
        "Colección Duplicados de Apple",
        "Vídeos grandes",
        "Capturas de pantalla",
    ),
    controls=(
        "Actualizar plan privado",
        "Introduce las tres cifras de almacenamiento entre 0 y 2.048 GB.",
    ),
    results=(
        "Espacio libre adicional necesario",
        "Espacio libre actual",
        "Espacio libre objetivo",
        "Espacio indicado para Fotos",
        "Estado del objetivo",
        "Objetivo alcanzado",
        "Aún falta espacio",
        "Plan de revisión reversible",
    ),
    boundaries=(
        "Fórmula: max(0, GB libres objetivo − GB libres actuales). Usa la misma unidad introducida y no predice lo que Fotos o PicClear pueden recuperar.",
        "El espacio de Fotos es solo contexto. Puede incluir contenido importante, sincronizado, optimizado, compartido, editado o contabilizado de otra forma.",
    ),
    icloud_steps=(
        "Comprueba la sincronización antes de cambiar originales irremplazables; con Fotos en iCloud, las ediciones y eliminaciones pueden propagarse.",
        "Aunque parezca sincronizado, los cambios se propagan entre dispositivos. La sincronización no sustituye una copia independiente.",
        "Resuelve primero cualquier pausa, sincronización o aviso de almacenamiento y comprueba qué contenido se ha sincronizado.",
        "Si Fotos en iCloud está desactivado, verifica otra copia independiente antes de realizar cambios destructivos.",
    ),
    priority_steps=(
        "Empieza por Ajustes > General > Almacenamiento del iPhone y revisa después Duplicados, vídeos y capturas en grupos pequeños.",
        "Abre Fotos > Colecciones > Utilidades > Duplicados y revisa cada fusión; la colección puede no aparecer si no se detectan duplicados.",
        "Revisa cada vídeo y abre una copia independiente; su duración o categoría no demuestra que sea prescindible.",
        "Revisa Capturas de pantalla en grupos pequeños y conserva las necesarias para trámites, viajes, trabajo, accesibilidad o autenticación.",
    ),
    confirmations=(
        "Abre una muestra desde la copia independiente antes de borrar permanentemente; la sincronización de iCloud no es un archivo independiente.",
        "Detente antes del borrado permanente y crea una copia independiente verificable de los originales irremplazables.",
        "Vuelve a revisar Eliminado recientemente antes de borrar para siempre; hacerlo termina el periodo normal de recuperación.",
        "Revisa Eliminado recientemente. Apple indica que los elementos suelen permanecer 30 días; no lo vacíes sin comprobar las copias esenciales.",
        "Tras revisar un grupo pequeño, vuelve a medir el almacenamiento del iPhone. No supongas que la diferencia calculada equivale a contenido borrable.",
    ),
    checklist=(
        "Secuencia de limpieza que prioriza la seguridad",
        "Confirma el espacio libre y el uso de Fotos en Ajustes > General > Almacenamiento del iPhone.",
        "Verifica una copia independiente y accesible de los originales irremplazables antes del borrado permanente.",
        "Comprueba Fotos en iCloud y recuerda que los cambios pueden propagarse entre dispositivos.",
        "Revisa solo un grupo pequeño y no confundas una categoría con permiso para borrar.",
        "Vuelve a comprobar Eliminado recientemente y el almacenamiento antes de continuar.",
    ),
    scope=(
        "Lo que este planificador no puede saber",
        "No puede leer tu fototeca, almacenamiento, iCloud, álbumes, archivos, metadatos, favoritos, duplicados, desenfoque, tamaños ni resultados. Nunca marca nada como seguro para borrar ni predice capacidad recuperada.",
    ),
    sources=(
        "Pasos oficiales de Apple antes de usar cualquier limpiador opcional",
        "Apple documenta el almacenamiento, Fotos en iCloud, Duplicados y el plazo de 30 días de Eliminado recientemente. Verifica los pasos para tu versión de iOS.",
        (
            "Apple: consultar el almacenamiento del iPhone y el iPad",
            "Apple: guardar y sincronizar fotos y vídeos con iCloud",
            "Apple: fusionar fotos y vídeos duplicados en el iPhone",
            "Apple: eliminar, recuperar o borrar permanentemente fotos y vídeos",
        ),
    ),
    webmcp=(
        "Vista previa de la API imperativa WebMCP de Chrome",
        "Calcula solo max(0, GB objetivo − GB actuales) con cifras limitadas introducidas por el usuario, informa del espacio de Fotos aparte y devuelve una revisión reversible. No accede a fotos, archivos, metadatos, iCloud, cuentas ni almacenamiento; tampoco estima, clasifica ni borra.",
    ),
    app=(
        "¿Quieres un flujo opcional de revisión en el dispositivo?",
        "PicClear Pro es opcional. Su ficha actual indica escaneo y vista previa gratuitos, desbloqueo único para limpiar y revisión local de duplicados, fotos similares, capturas, fotos borrosas y archivos grandes. Nada se elimina sin confirmación. Consulta la ficha vigente; este planificador funciona sin la app.",
        "Ver PicClear Pro en el App Store",
    ),
    faq=(
        "Preguntas sobre liberar espacio de fotos",
        (
            ("¿Esta página escanea mi fototeca?", "No. Solo acepta las cifras y opciones que introduces."),
            ("¿La diferencia equivale al espacio recuperable?", "No. Solo resta el espacio actual al objetivo y nunca estima contenido borrable."),
            ("¿Fotos en iCloud es una copia independiente?", "Este planificador no considera la sincronización una copia independiente porque los cambios pueden propagarse."),
            ("¿Eliminado recientemente libera espacio al instante?", "No lo supongas. Apple documenta un periodo de recuperación de 30 días; vuelve a medir después de revisar."),
        ),
    ),
    footer="Solo cálculo privado · sin acceso a fotos · sin borrar · sin estimar recuperación",
    index=(
        "Planificador privado para liberar espacio de fotos",
        "Calcula una diferencia conocida y crea una revisión reversible sin subir fotos ni adivinar espacio recuperable.",
    ),
)

_localized(
    "pt-BR",
    meta=(
        "Planejador privado para liberar espaço de fotos no iPhone | Sem upload",
        "Calcule apenas a diferença de espaço livre com os números informados e monte uma revisão reversível sem enviar, escanear ou estimar sua fototeca.",
        "Ferramentas gratuitas",
        "English",
        "Grátis · sem acesso às fotos · sem estimar espaço recuperável",
        "Planejador privado para liberar espaço de fotos no iPhone",
        "Meça a diferença entre o espaço livre atual e a meta sem adivinhar tamanho de arquivo, duplicatas ou quanto será recuperado.",
    ),
    badges=(
        "Sem fotos, arquivos ou metadados",
        "Sem acesso ao aparelho ou iCloud",
        "Sem excluir ou classificar",
        "Sem prever espaço recuperável",
    ),
    planner=(
        "Calcule uma diferença de espaço conhecida",
        "Copie números visíveis nos Ajustes. O uso de Fotos aparece separado e nunca é tratado como espaço apagável ou recuperável.",
    ),
    labels=(
        "Espaço livre atual (GB)",
        "Meta de espaço livre (GB)",
        "Uso de Fotos mostrado pelo iPhone (GB)",
        "Status do Fotos do iCloud",
        "Primeira área para revisar",
        "Verifiquei uma cópia independente dos originais insubstituíveis",
        "Revisei Apagados",
    ),
    icloud_options=(
        "Não verificado",
        "Ativado — sincronização parece concluída",
        "Ativado — sincronizando, pausado ou com aviso",
        "Desativado",
    ),
    priority_options=(
        "Revisão geral do armazenamento",
        "Coleção Duplicados da Apple",
        "Vídeos grandes",
        "Capturas de tela",
    ),
    controls=(
        "Atualizar plano privado",
        "Informe os três números de armazenamento entre 0 e 2.048 GB.",
    ),
    results=(
        "Espaço livre adicional necessário",
        "Espaço livre atual",
        "Meta de espaço livre",
        "Uso informado de Fotos",
        "Status da meta",
        "Meta já atingida",
        "Ainda falta espaço",
        "Plano de revisão reversível",
    ),
    boundaries=(
        "Fórmula: max(0, GB livres desejados − GB livres atuais). O resultado usa a mesma unidade e não prevê quanto Fotos ou PicClear podem recuperar.",
        "O uso de Fotos serve apenas como contexto. Ele pode incluir itens importantes, sincronizados, otimizados, compartilhados, editados ou contabilizados de outra forma.",
    ),
    icloud_steps=(
        "Confira a sincronização antes de alterar originais insubstituíveis; com Fotos do iCloud, edições e exclusões podem se propagar.",
        "Mesmo com sincronização concluída, alterações passam para outros aparelhos. Sincronização não substitui uma cópia independente.",
        "Resolva primeiro qualquer pausa, sincronização ou aviso de armazenamento e confirme o que realmente foi sincronizado.",
        "Se o Fotos do iCloud estiver desativado, verifique outra cópia independente antes de alterações destrutivas.",
    ),
    priority_steps=(
        "Comece em Ajustes > Geral > Armazenamento do iPhone e depois revise Duplicados, vídeos e capturas em pequenos grupos.",
        "Abra Fotos > Coleções > Utilitários > Duplicados e confira cada combinação; a coleção pode não aparecer sem duplicatas detectadas.",
        "Revise cada vídeo e abra uma cópia independente; duração ou categoria não prova que ele possa ser descartado.",
        "Revise Capturas de Tela em pequenos grupos e mantenha o que for necessário para registros, autenticação, viagens, trabalho ou acessibilidade.",
    ),
    confirmations=(
        "Abra uma amostra na cópia independente antes da exclusão permanente; a sincronização do iCloud não é um arquivo independente.",
        "Pare antes da exclusão permanente e crie uma cópia independente verificável dos originais insubstituíveis.",
        "Revise novamente Apagados antes de remover para sempre; a remoção permanente encerra a recuperação normal.",
        "Confira Apagados. A Apple informa que itens normalmente permanecem por 30 dias; não esvazie sem verificar as cópias essenciais.",
        "Após revisar um pequeno grupo, meça novamente o armazenamento. Não suponha que a diferença calculada seja conteúdo apagável.",
    ),
    checklist=(
        "Sequência de limpeza com segurança em primeiro lugar",
        "Confirme espaço livre e uso de Fotos em Ajustes > Geral > Armazenamento do iPhone.",
        "Verifique uma cópia independente e acessível dos originais insubstituíveis antes da exclusão permanente.",
        "Confira o Fotos do iCloud e lembre que alterações podem se propagar entre aparelhos.",
        "Revise apenas um pequeno grupo e nunca trate uma categoria como prova de que algo pode ser apagado.",
        "Confira novamente Apagados e o armazenamento antes de continuar.",
    ),
    scope=(
        "O que este planejador não consegue saber",
        "Ele não lê sua fototeca, armazenamento, iCloud, álbuns, arquivos, metadados, favoritos, duplicatas, desfoque, tamanhos ou resultados. Nunca classifica algo como seguro para excluir nem prevê capacidade recuperada.",
    ),
    sources=(
        "Etapas oficiais da Apple antes de qualquer limpador opcional",
        "A Apple documenta armazenamento, Fotos do iCloud, Duplicados e o prazo de 30 dias de Apagados. Confira as instruções para sua versão do iOS.",
        (
            "Apple: verificar o armazenamento do iPhone e iPad",
            "Apple: fazer backup e sincronizar fotos e vídeos com o iCloud",
            "Apple: combinar fotos e vídeos duplicados no iPhone",
            "Apple: apagar, recuperar ou remover fotos e vídeos permanentemente",
        ),
    ),
    webmcp=(
        "Prévia da API imperativa WebMCP do Chrome",
        "Calcula apenas max(0, meta em GB − GB atuais) com números limitados informados pelo usuário, relata Fotos separadamente e devolve uma revisão reversível. Não acessa fotos, arquivos, metadados, iCloud, contas ou armazenamento; não estima, classifica nem exclui.",
    ),
    app=(
        "Quer um fluxo opcional de revisão no aparelho?",
        "O PicClear Pro é opcional. A página atual informa análise e prévia gratuitas, desbloqueio único para limpeza e revisão local de duplicatas, fotos parecidas, capturas, fotos desfocadas e arquivos grandes. Nada é apagado sem confirmação. Confira a página atual; este planejador funciona sem o app.",
        "Ver o PicClear Pro na App Store",
    ),
    faq=(
        "Dúvidas sobre liberar espaço de fotos",
        (
            ("Esta página escaneia minha fototeca?", "Não. Ela aceita apenas os números e as opções que você informa."),
            ("A diferença é o espaço que posso recuperar?", "Não. É apenas a meta menos o espaço atual e nunca estima mídia apagável."),
            ("Fotos do iCloud é uma cópia independente?", "Este planejador não trata sincronização como cópia independente porque alterações podem se propagar."),
            ("Apagados libera espaço imediatamente?", "Não presuma isso. A Apple documenta recuperação por 30 dias; meça novamente após a revisão."),
        ),
    ),
    footer="Apenas cálculo privado · sem acesso às fotos · sem excluir · sem estimar recuperação",
    index=(
        "Planejador privado de espaço para fotos",
        "Calcule uma diferença conhecida e monte uma revisão reversível sem enviar fotos nem adivinhar espaço recuperável.",
    ),
)

_localized(
    "de-DE",
    meta=(
        "Privater Planer für iPhone-Fotospeicher | Kein Upload",
        "Berechne nur die Lücke zum gewünschten freien Speicher und erstelle einen umkehrbaren Prüfplan – ohne Upload, Scan oder Schätzung deiner Mediathek.",
        "Kostenlose Tools",
        "English",
        "Kostenlos · kein Fotozugriff · keine Schätzung",
        "Privater Planer für freien iPhone-Fotospeicher",
        "Miss den Abstand zwischen aktuellem und gewünschtem freien Speicher, ohne Dateigrößen, Duplikate oder Einsparungen zu erraten.",
    ),
    badges=(
        "Keine Fotos, Dateien oder Metadaten",
        "Kein Geräte- oder iCloud-Zugriff",
        "Kein Löschen oder Klassifizieren",
        "Keine Prognose des freigebbaren Speichers",
    ),
    planner=(
        "Bekannte Speicherlücke berechnen",
        "Übernimm Werte aus den Einstellungen. Der Fotospeicher wird getrennt angezeigt und nie als löschbar oder freigebbar behandelt.",
    ),
    labels=(
        "Aktuell freier Speicher (GB)",
        "Gewünschter freier Speicher (GB)",
        "Vom iPhone angezeigter Fotospeicher (GB)",
        "Status von iCloud-Fotos",
        "Zuerst zu prüfender Bereich",
        "Ich habe eine unabhängige Kopie unersetzlicher Originale geprüft",
        "Ich habe „Zuletzt gelöscht“ geprüft",
    ),
    icloud_options=(
        "Nicht geprüft",
        "Ein – Synchronisierung scheint abgeschlossen",
        "Ein – synchronisiert, pausiert oder Warnung",
        "Aus",
    ),
    priority_options=(
        "Allgemeine Speicherprüfung",
        "Apple-Sammlung „Duplikate“",
        "Große Videos",
        "Bildschirmfotos",
    ),
    controls=(
        "Privaten Plan aktualisieren",
        "Gib alle drei Speicherwerte zwischen 0 und 2.048 GB ein.",
    ),
    results=(
        "Zusätzlich benötigter freier Speicher",
        "Aktuell freier Speicher",
        "Gewünschter freier Speicher",
        "Gemeldeter Fotospeicher",
        "Zielstatus",
        "Ziel bereits erreicht",
        "Lücke bleibt",
        "Umkehrbarer Prüfplan",
    ),
    boundaries=(
        "Formel: max(0, gewünschte freie GB − aktuelle freie GB). Das Ergebnis nutzt dieselbe Einheit und sagt nicht voraus, was Fotos oder PicClear freigeben können.",
        "Der gemeldete Fotospeicher dient nur als Kontext. Inhalte können wichtig, synchronisiert, optimiert, geteilt, bearbeitet oder anders angerechnet sein.",
    ),
    icloud_steps=(
        "Prüfe vor Änderungen an unersetzlichen Originalen die Synchronisierung; Änderungen und Löschungen können über iCloud-Fotos weitergegeben werden.",
        "Auch bei abgeschlossener Synchronisierung werden Änderungen auf andere Geräte übertragen. Synchronisierung ersetzt kein unabhängiges Backup.",
        "Behebe zuerst Pausen, Synchronisierungs- oder Speicherwarnungen und prüfe, was tatsächlich synchronisiert wurde.",
        "Wenn iCloud-Fotos aus ist, prüfe vor destruktiven Änderungen eine andere unabhängige Kopie.",
    ),
    priority_steps=(
        "Beginne mit Einstellungen > Allgemein > iPhone-Speicher und prüfe danach Duplikate, Videos und Bildschirmfotos in kleinen Gruppen.",
        "Öffne Fotos > Sammlungen > Dienstprogramme > Duplikate und prüfe jede Zusammenführung; ohne erkannte Duplikate kann die Sammlung fehlen.",
        "Prüfe jedes Video und öffne eine unabhängige Kopie; Dauer oder Kategorie belegen nicht, dass es entbehrlich ist.",
        "Prüfe Bildschirmfotos in kleinen Gruppen und behalte alles, was für Nachweise, Anmeldung, Reisen, Arbeit oder Barrierefreiheit nötig ist.",
    ),
    confirmations=(
        "Öffne vor dauerhaftem Löschen Stichproben aus der unabhängigen Kopie; iCloud-Synchronisierung allein ist kein unabhängiges Archiv.",
        "Stoppe vor dauerhaftem Löschen und erstelle eine überprüfbare unabhängige Kopie unersetzlicher Originale.",
        "Prüfe „Zuletzt gelöscht“ erneut, bevor du etwas dauerhaft entfernst; danach endet die normale Wiederherstellung.",
        "Prüfe „Zuletzt gelöscht“. Apple nennt üblicherweise 30 Tage; leere es erst, wenn wichtige Originale unabhängig geprüft sind.",
        "Miss nach einer kleinen geprüften Gruppe den iPhone-Speicher erneut. Die berechnete Lücke ist nicht automatisch löschbarer Inhalt.",
    ),
    checklist=(
        "Sicherheitsorientierte Reihenfolge",
        "Prüfe freien Speicher und Fotospeicher unter Einstellungen > Allgemein > iPhone-Speicher.",
        "Prüfe vor dauerhaftem Löschen eine unabhängige, lesbare Kopie unersetzlicher Originale.",
        "Prüfe iCloud-Fotos und bedenke, dass Änderungen geräteübergreifend wirken können.",
        "Prüfe nur kleine Gruppen und behandle eine Kategorie nie als Löschfreigabe.",
        "Prüfe vor der nächsten Gruppe erneut „Zuletzt gelöscht“ und den Gerätespeicher.",
    ),
    scope=(
        "Was dieser Planer nicht wissen kann",
        "Er liest weder Mediathek, Speicher, iCloud, Alben, Dateien, Metadaten, Favoriten, Duplikate, Unschärfe, Größen noch Ergebnisse. Er markiert nichts als sicher löschbar und prognostiziert keinen freigebbaren Speicher.",
    ),
    sources=(
        "Offizielle Apple-Schritte vor einem optionalen Bereinigungstool",
        "Apple beschreibt iPhone-Speicher, iCloud-Fotos, Duplikate und die 30-Tage-Frist von „Zuletzt gelöscht“. Prüfe die Anleitung für deine iOS-Version.",
        (
            "Apple: Speicher auf iPhone und iPad prüfen",
            "Apple: Fotos und Videos mit iCloud sichern und synchronisieren",
            "Apple: Doppelte Fotos und Videos auf dem iPhone zusammenführen",
            "Apple: Fotos und Videos löschen, wiederherstellen oder dauerhaft entfernen",
        ),
    ),
    webmcp=(
        "Vorschau der imperativen Chrome-WebMCP-API",
        "Berechnet nur max(0, Ziel-GB − aktuelle GB) aus begrenzten Nutzereingaben, meldet Fotospeicher getrennt und liefert einen umkehrbaren Plan. Kein Zugriff auf Fotos, Dateien, Metadaten, iCloud, Konten oder Speicher; keine Schätzung, Klassifizierung oder Löschung.",
    ),
    app=(
        "Möchtest du optional direkt auf dem Gerät prüfen?",
        "PicClear Pro ist optional. Der aktuelle App-Store-Eintrag nennt kostenlosen Scan und Vorschau, einmaliges Freischalten der Bereinigung sowie lokale Prüfung von Duplikaten, ähnlichen Fotos, Bildschirmfotos, unscharfen Bildern und großen Dateien. Nichts wird ohne Bestätigung gelöscht. Prüfe den aktuellen Eintrag; der Planer funktioniert ohne App.",
        "PicClear Pro im App Store ansehen",
    ),
    faq=(
        "Fragen zum Freigeben von Fotospeicher",
        (
            ("Scannt diese Seite meine Mediathek?", "Nein. Sie verarbeitet nur eingegebene Speicherwerte und Auswahloptionen."),
            ("Entspricht die Lücke dem freigebbaren Speicher?", "Nein. Sie ist nur Ziel minus aktueller Speicher und schätzt keine löschbaren Medien."),
            ("Ist iCloud-Fotos ein unabhängiges Backup?", "Dieser Planer behandelt Synchronisierung nicht als unabhängige Kopie, da Änderungen weitergegeben werden können."),
            ("Gibt „Zuletzt gelöscht“ sofort Speicher frei?", "Verlass dich nicht darauf. Apple beschreibt 30 Tage Wiederherstellung; miss nach geprüften Änderungen erneut."),
        ),
    ),
    footer="Nur private Berechnung · kein Fotozugriff · kein Löschen · keine Schätzung",
    index=(
        "Privater Planer für Fotospeicher",
        "Berechne eine bekannte Lücke und erstelle einen umkehrbaren Prüfplan ohne Foto-Upload oder Schätzung.",
    ),
)

_localized(
    "fr-FR",
    meta=(
        "Planificateur privé pour libérer l’espace photo sur iPhone | Sans envoi",
        "Calculez uniquement l’écart d’espace libre à partir de vos chiffres, puis organisez une vérification réversible sans envoyer, analyser ni estimer votre photothèque.",
        "Outils gratuits",
        "English",
        "Gratuit · aucun accès aux photos · aucune estimation",
        "Planificateur privé pour libérer l’espace photo sur iPhone",
        "Mesurez l’écart entre l’espace libre actuel et l’objectif sans deviner la taille des fichiers, les doublons ni l’espace récupérable.",
    ),
    badges=(
        "Aucune photo, aucun fichier ni métadonnée",
        "Aucun accès à l’appareil ni à iCloud",
        "Aucune suppression ni classification",
        "Aucune prédiction d’espace récupérable",
    ),
    planner=(
        "Calculer un écart d’espace connu",
        "Recopiez les chiffres visibles dans Réglages. Le stockage Photos reste séparé et n’est jamais considéré comme supprimable ou récupérable.",
    ),
    labels=(
        "Espace libre actuel (Go)",
        "Espace libre visé (Go)",
        "Stockage Photos indiqué par l’iPhone (Go)",
        "État de Photos iCloud",
        "Première zone à vérifier",
        "J’ai vérifié une copie indépendante des originaux irremplaçables",
        "J’ai vérifié Supprimées récemment",
    ),
    icloud_options=(
        "Non vérifié",
        "Activé — synchronisation apparemment terminée",
        "Activé — synchronisation, pause ou alerte",
        "Désactivé",
    ),
    priority_options=(
        "Vérification générale du stockage",
        "Collection Doublons d’Apple",
        "Vidéos volumineuses",
        "Captures d’écran",
    ),
    controls=(
        "Actualiser le plan privé",
        "Saisissez les trois valeurs de stockage entre 0 et 2 048 Go.",
    ),
    results=(
        "Espace libre supplémentaire nécessaire",
        "Espace libre actuel",
        "Espace libre visé",
        "Stockage Photos indiqué",
        "État de l’objectif",
        "Objectif déjà atteint",
        "Écart restant",
        "Plan de vérification réversible",
    ),
    boundaries=(
        "Formule : max(0, Go libres visés − Go libres actuels). Le résultat conserve votre unité et ne prédit pas ce que Photos ou PicClear peut récupérer.",
        "Le stockage Photos sert uniquement de contexte. Des éléments peuvent être importants, synchronisés, optimisés, partagés, modifiés ou comptabilisés autrement.",
    ),
    icloud_steps=(
        "Vérifiez la synchronisation avant de modifier des originaux irremplaçables ; avec Photos iCloud, modifications et suppressions peuvent se propager.",
        "Même lorsque la synchronisation paraît terminée, les changements se propagent. Elle ne remplace pas une copie indépendante.",
        "Résolvez d’abord toute pause, synchronisation ou alerte de stockage, puis confirmez ce qui a réellement été synchronisé.",
        "Si Photos iCloud est désactivé, vérifiez une autre copie indépendante avant toute modification destructive.",
    ),
    priority_steps=(
        "Commencez par Réglages > Général > Stockage iPhone, puis vérifiez Doublons, vidéos et captures par petits groupes.",
        "Ouvrez Photos > Collections > Utilitaires > Doublons et examinez chaque fusion ; la collection peut être absente si aucun doublon n’est détecté.",
        "Examinez chaque vidéo et ouvrez une copie indépendante ; sa durée ou sa catégorie ne prouve pas qu’elle est inutile.",
        "Vérifiez les captures d’écran par petits groupes et conservez celles utiles aux justificatifs, voyages, connexions, travail ou à l’accessibilité.",
    ),
    confirmations=(
        "Ouvrez quelques fichiers depuis la copie indépendante avant toute suppression définitive ; la synchronisation iCloud seule n’est pas une archive indépendante.",
        "Arrêtez-vous avant la suppression définitive et créez une copie indépendante vérifiable des originaux irremplaçables.",
        "Revérifiez Supprimées récemment avant de supprimer définitivement ; cette action met fin à la récupération normale.",
        "Vérifiez Supprimées récemment. Apple indique que les éléments y restent généralement 30 jours ; ne videz rien avant de contrôler les copies essentielles.",
        "Après un petit groupe vérifié, mesurez de nouveau le stockage. Ne supposez pas que l’écart calculé correspond à du contenu supprimable.",
    ),
    checklist=(
        "Séquence de nettoyage axée sur la sécurité",
        "Confirmez l’espace libre et le stockage Photos dans Réglages > Général > Stockage iPhone.",
        "Vérifiez une copie indépendante et lisible des originaux irremplaçables avant toute suppression définitive.",
        "Vérifiez Photos iCloud et rappelez-vous que les changements peuvent se propager.",
        "N’examinez qu’un petit groupe et ne considérez jamais une catégorie comme une autorisation de supprimer.",
        "Revérifiez Supprimées récemment et le stockage avant de poursuivre.",
    ),
    scope=(
        "Ce que ce planificateur ne peut pas savoir",
        "Il ne lit ni photothèque, stockage, iCloud, albums, fichiers, métadonnées, favoris, doublons, flou, tailles ou résultats. Il ne déclare jamais un élément supprimable sans risque et ne prédit aucun espace récupéré.",
    ),
    sources=(
        "Étapes officielles Apple avant tout outil facultatif",
        "Apple documente le stockage iPhone, Photos iCloud, Doublons et le délai de 30 jours de Supprimées récemment. Vérifiez les instructions de votre version d’iOS.",
        (
            "Apple : consulter le stockage sur iPhone et iPad",
            "Apple : sauvegarder et synchroniser les photos et vidéos avec iCloud",
            "Apple : fusionner les photos et vidéos en double sur l’iPhone",
            "Apple : supprimer, récupérer ou effacer définitivement des photos et vidéos",
        ),
    ),
    webmcp=(
        "Aperçu de l’API WebMCP impérative de Chrome",
        "Calcule uniquement max(0, Go visés − Go actuels) à partir de valeurs bornées, sépare le stockage Photos et renvoie un plan réversible. Aucun accès aux photos, fichiers, métadonnées, iCloud, comptes ou stockage ; aucune estimation, classification ou suppression.",
    ),
    app=(
        "Vous souhaitez une vérification facultative sur l’appareil ?",
        "PicClear Pro est facultatif. Sa fiche actuelle indique une analyse et un aperçu gratuits, un déverrouillage unique du nettoyage et une vérification locale des doublons, photos similaires, captures, photos floues et fichiers volumineux. Rien n’est supprimé sans confirmation. Consultez la fiche actuelle ; ce planificateur fonctionne sans l’app.",
        "Voir PicClear Pro sur l’App Store",
    ),
    faq=(
        "Questions sur l’espace occupé par les photos",
        (
            ("Cette page analyse-t-elle ma photothèque ?", "Non. Elle accepte uniquement les valeurs et options que vous saisissez."),
            ("L’écart correspond-il à l’espace récupérable ?", "Non. Il s’agit seulement de l’objectif moins l’espace actuel, sans estimation des médias supprimables."),
            ("Photos iCloud est-il une copie indépendante ?", "Ce planificateur ne considère pas la synchronisation comme une copie indépendante, car les changements peuvent se propager."),
            ("Supprimées récemment libère-t-il immédiatement de l’espace ?", "Ne le supposez pas. Apple documente 30 jours de récupération ; mesurez de nouveau après vérification."),
        ),
    ),
    footer="Calcul privé uniquement · aucun accès aux photos · aucune suppression · aucune estimation",
    index=(
        "Planificateur privé d’espace photo",
        "Calculez un écart connu et créez une vérification réversible sans envoyer de photos ni deviner l’espace récupérable.",
    ),
)

_localized(
    "ja",
    meta=(
        "iPhone写真ストレージの非公開整理プランナー｜アップロードなし",
        "入力したストレージ数値だけで空き容量の差を計算し、写真を送信・走査・推定せずに元へ戻せる確認手順を作ります。",
        "無料ツール",
        "English",
        "無料・写真へのアクセスなし・回収容量の推定なし",
        "iPhone写真ストレージの非公開整理プランナー",
        "平均ファイルサイズ、重複率、整理で戻る容量を推測せず、現在と目標の空き容量差だけを測ります。",
    ),
    badges=(
        "写真・ファイル・メタデータを受け取らない",
        "端末やiCloudへアクセスしない",
        "削除も分類もしない",
        "回収できる容量を予測しない",
    ),
    planner=(
        "既知の空き容量差を計算",
        "「設定」で確認できる数値を入力します。写真の使用量は別に表示し、削除可能・回収可能な容量とは扱いません。",
    ),
    labels=(
        "現在の空き容量（GB）",
        "目標の空き容量（GB）",
        "iPhoneに表示される写真の使用量（GB）",
        "iCloud写真の状態",
        "最初に確認する場所",
        "かけがえのない原本の独立したコピーを確認済み",
        "「最近削除した項目」を確認済み",
    ),
    icloud_options=(
        "未確認",
        "オン — 同期完了と表示",
        "オン — 同期中・一時停止・警告あり",
        "オフ",
    ),
    priority_options=(
        "ストレージ全般",
        "Appleの「重複項目」",
        "大きなビデオ",
        "スクリーンショット",
    ),
    controls=(
        "非公開プランを更新",
        "3つのストレージ数値を0〜2,048 GBで入力してください。",
    ),
    results=(
        "追加で必要な空き容量",
        "現在の空き容量",
        "目標の空き容量",
        "表示された写真使用量",
        "目標の状態",
        "目標達成済み",
        "差が残っています",
        "元へ戻せる確認手順",
    ),
    boundaries=(
        "計算式：max(0, 目標空きGB − 現在空きGB)。入力と同じ単位を使い、写真やPicClearで回収できる容量は予測しません。",
        "写真の使用量は参考情報です。重要、同期済み、最適化済み、共有、編集済み、または端末上で別の形で計上された内容を含む場合があります。",
    ),
    icloud_steps=(
        "かけがえのない原本を変更する前に同期状態を確認してください。iCloud写真では編集や削除が他の端末にも反映されます。",
        "同期完了と表示されても変更は他の端末へ反映されます。同期だけを独立したコピーと考えないでください。",
        "削除を伴う変更の前に、同期中・一時停止・容量警告を解消し、実際に同期済みの内容を確認してください。",
        "iCloud写真がオフの場合、削除を伴う変更の前に別の独立したコピーを確認してください。",
    ),
    priority_steps=(
        "「設定 > 一般 > iPhoneストレージ」から始め、「重複項目」、ビデオ、スクリーンショットを少量ずつ確認します。",
        "「写真 > コレクション > ユーティリティ > 重複項目」を開き、結合ごとに確認します。重複が見つからない場合は表示されません。",
        "各ビデオの重要性と独立コピーが開けることを確認します。長さや分類だけでは不要と判断できません。",
        "スクリーンショットを少量ずつ確認し、記録、認証、旅行、仕事、アクセシビリティに必要なものを残します。",
    ),
    confirmations=(
        "完全に削除する前に独立コピーから数点を実際に開いてください。iCloud写真の同期だけを独立した保管とは扱いません。",
        "完全な削除を止め、かけがえのない原本について確認可能な独立コピーを作成してください。",
        "完全に消去する前に「最近削除した項目」を再確認してください。完全削除すると通常の復元期間が終わります。",
        "「最近削除した項目」を確認してください。Appleでは通常30日間保持されます。重要な原本を確認するまで空にしないでください。",
        "少量を確認したらiPhoneストレージを再度測ります。計算した差が削除可能な内容と同じだと考えないでください。",
    ),
    checklist=(
        "安全を優先した整理手順",
        "「設定 > 一般 > iPhoneストレージ」で空き容量と写真使用量を確認します。",
        "完全に削除する前に、かけがえのない原本の開ける独立コピーを確認します。",
        "iCloud写真の同期状態と、変更が端末間で反映されることを確認します。",
        "一度に少量だけ確認し、分類だけで削除可能と判断しません。",
        "次へ進む前に「最近削除した項目」と端末容量を再確認します。",
    ),
    scope=(
        "このプランナーが分からないこと",
        "写真ライブラリ、ストレージ、iCloud、アルバム、ファイル、メタデータ、お気に入り、重複、ぼけ、サイズ、削除結果を読み取れません。安全に削除できる項目を決めたり、回収容量を予測したりしません。",
    ),
    sources=(
        "任意の整理アプリを使う前に確認するApple公式手順",
        "AppleはiPhoneストレージ、iCloud写真、「重複項目」、「最近削除した項目」の30日間について案内しています。現在のiOS向け手順を確認してください。",
        (
            "Apple：iPhoneとiPadのストレージを確認する",
            "Apple：iCloudで写真とビデオを同期する",
            "Apple：iPhoneで重複する写真やビデオを結合する",
            "Apple：写真やビデオを削除・復元・完全削除する",
        ),
    ),
    webmcp=(
        "Chrome imperative WebMCP APIプレビュー",
        "範囲を限定した自己入力数値からmax(0, 目標GB − 現在GB)だけを計算し、写真使用量を分けて元へ戻せる手順を返します。写真、ファイル、メタデータ、iCloud、アカウント、端末容量へアクセスせず、推定・分類・削除もしません。",
    ),
    app=(
        "端末内で確認する任意の方法も見ますか？",
        "PicClear Proは任意です。現在の掲載情報では、走査とプレビューは無料、整理は一度の購入で解放され、重複、類似写真、スクリーンショット、ぼけた写真、大きなファイルを端末内で確認できます。確認なしには削除されません。最新の掲載情報を確認してください。このプランナーはアプリなしでも使えます。",
        "App StoreでPicClear Proを見る",
    ),
    faq=(
        "写真ストレージ整理の質問",
        (
            ("このページは写真ライブラリを走査しますか？", "いいえ。入力したストレージ数値と選択肢だけを受け取ります。"),
            ("容量差は回収できる容量ですか？", "いいえ。目標から現在値を引くだけで、削除可能なメディアは推定しません。"),
            ("iCloud写真は独立したバックアップですか？", "変更が端末間で反映されるため、このプランナーは同期だけを独立コピーとは扱いません。"),
            ("「最近削除した項目」ですぐ容量が空きますか？", "そうとは限りません。Appleは30日間の復元期間を案内しています。確認後に再度測ってください。"),
        ),
    ),
    footer="非公開の計算のみ・写真アクセスなし・削除なし・回収容量の推定なし",
    index=(
        "非公開の写真ストレージ整理プランナー",
        "写真を送信せず、回収容量を推測せずに、既知の差と元へ戻せる確認手順を作ります。",
    ),
)

_localized(
    "ko",
    meta=(
        "비공개 iPhone 사진 저장 공간 정리 플래너 | 업로드 없음",
        "직접 입력한 저장 공간 숫자로 필요한 여유 공간만 계산하고 사진을 업로드·스캔·추정하지 않는 되돌릴 수 있는 검토 순서를 만드세요.",
        "무료 도구",
        "English",
        "무료 · 사진 접근 없음 · 확보 가능 용량 추정 없음",
        "비공개 iPhone 사진 저장 공간 정리 플래너",
        "평균 파일 크기, 중복 비율, 정리 후 확보 용량을 추측하지 않고 현재와 목표 여유 공간의 차이만 측정합니다.",
    ),
    badges=(
        "사진·파일·메타데이터를 받지 않음",
        "기기 또는 iCloud에 접근하지 않음",
        "삭제하거나 분류하지 않음",
        "확보 가능 용량을 예측하지 않음",
    ),
    planner=(
        "확인된 저장 공간 차이 계산",
        "설정에서 이미 볼 수 있는 숫자를 입력하세요. 사진 사용량은 따로 표시하며 삭제하거나 확보할 수 있는 용량으로 간주하지 않습니다.",
    ),
    labels=(
        "현재 여유 공간(GB)",
        "목표 여유 공간(GB)",
        "iPhone에 표시된 사진 사용량(GB)",
        "iCloud 사진 상태",
        "먼저 검토할 영역",
        "대체할 수 없는 원본의 독립된 사본을 확인했습니다",
        "최근 삭제된 항목을 검토했습니다",
    ),
    icloud_options=(
        "확인하지 않음",
        "켬 — 동기화 완료로 보임",
        "켬 — 동기화 중, 일시 정지 또는 경고",
        "끔",
    ),
    priority_options=(
        "일반 저장 공간 검토",
        "Apple 중복된 항목",
        "대용량 비디오",
        "스크린샷",
    ),
    controls=(
        "비공개 계획 업데이트",
        "세 저장 공간 숫자를 모두 0~2,048GB로 입력하세요.",
    ),
    results=(
        "추가로 필요한 여유 공간",
        "현재 여유 공간",
        "목표 여유 공간",
        "표시된 사진 사용량",
        "목표 상태",
        "목표 달성",
        "차이 남음",
        "되돌릴 수 있는 검토 순서",
    ),
    boundaries=(
        "계산식: max(0, 목표 여유 GB − 현재 여유 GB). 입력한 단위를 그대로 사용하며 사진이나 PicClear가 확보할 용량을 예측하지 않습니다.",
        "사진 사용량은 참고 정보일 뿐입니다. 중요하거나 동기화·최적화·공유·편집되었거나 기기에서 다르게 계산된 항목이 포함될 수 있습니다.",
    ),
    icloud_steps=(
        "대체할 수 없는 원본을 바꾸기 전에 동기화 상태를 확인하세요. iCloud 사진에서는 편집과 삭제가 다른 기기에도 반영될 수 있습니다.",
        "동기화 완료로 보여도 변경 사항은 기기 간에 반영됩니다. 동기화를 독립된 사본 하나로 여기지 마세요.",
        "파괴적인 변경 전에 동기화, 일시 정지 또는 저장 공간 경고를 해결하고 실제 동기화된 항목을 확인하세요.",
        "iCloud 사진이 꺼져 있다면 파괴적인 변경 전에 별도의 독립된 사본을 확인하세요.",
    ),
    priority_steps=(
        "설정 > 일반 > iPhone 저장 공간에서 시작한 뒤 중복된 항목, 비디오, 스크린샷을 소량씩 검토하세요.",
        "사진 > 모음 > 유틸리티 > 중복된 항목에서 각 병합을 확인하세요. 중복이 감지되지 않으면 항목이 보이지 않을 수 있습니다.",
        "각 비디오의 중요성과 독립 사본이 열리는지 확인하세요. 길이나 분류만으로 불필요하다고 판단할 수 없습니다.",
        "스크린샷을 소량씩 검토하고 기록, 인증, 여행, 업무 또는 손쉬운 사용에 필요한 항목을 보관하세요.",
    ),
    confirmations=(
        "완전히 삭제하기 전에 독립 사본에서 일부 파일을 직접 열어 보세요. iCloud 사진 동기화만으로는 독립 보관본이 아닙니다.",
        "완전 삭제를 멈추고 대체할 수 없는 원본의 확인 가능한 독립 사본을 만드세요.",
        "완전히 제거하기 전에 최근 삭제된 항목을 다시 확인하세요. 완전 삭제하면 일반적인 복구 기간이 끝납니다.",
        "최근 삭제된 항목을 확인하세요. Apple에 따르면 보통 30일간 유지됩니다. 필수 원본을 확인하기 전에는 비우지 마세요.",
        "소량을 검토한 뒤 iPhone 저장 공간을 다시 측정하세요. 계산된 차이가 삭제 가능한 콘텐츠와 같다고 가정하지 마세요.",
    ),
    checklist=(
        "안전을 우선하는 정리 순서",
        "설정 > 일반 > iPhone 저장 공간에서 여유 공간과 사진 사용량을 확인하세요.",
        "완전 삭제 전에 대체할 수 없는 원본의 열 수 있는 독립 사본을 확인하세요.",
        "iCloud 사진 동기화 상태와 변경 사항이 기기 간에 반영될 수 있음을 확인하세요.",
        "한 번에 소량만 검토하고 분류만으로 삭제 가능하다고 판단하지 마세요.",
        "다음 단계 전에 최근 삭제된 항목과 기기 저장 공간을 다시 확인하세요.",
    ),
    scope=(
        "이 플래너가 알 수 없는 것",
        "사진 보관함, 저장 공간, iCloud, 앨범, 파일, 메타데이터, 즐겨찾기, 중복, 흐림, 크기 또는 삭제 결과를 읽지 못합니다. 어떤 항목도 안전하게 삭제할 수 있다고 표시하지 않으며 확보 용량도 예측하지 않습니다.",
    ),
    sources=(
        "선택형 정리 도구보다 먼저 확인할 Apple 공식 단계",
        "Apple은 iPhone 저장 공간, iCloud 사진, 중복된 항목과 최근 삭제된 항목의 30일 기간을 안내합니다. 현재 iOS 버전의 절차를 확인하세요.",
        (
            "Apple: iPhone 및 iPad 저장 공간 확인",
            "Apple: iCloud로 사진과 비디오 동기화",
            "Apple: iPhone에서 중복 사진과 비디오 병합",
            "Apple: 사진과 비디오 삭제, 복구 또는 완전 제거",
        ),
    ),
    webmcp=(
        "Chrome imperative WebMCP API 미리보기",
        "범위가 제한된 직접 입력 숫자로 max(0, 목표 GB − 현재 GB)만 계산하고 사진 사용량을 별도로 표시하며 되돌릴 수 있는 검토 순서를 반환합니다. 사진, 파일, 메타데이터, iCloud, 계정 또는 저장 공간에 접근하지 않고 추정·분류·삭제하지 않습니다.",
    ),
    app=(
        "기기에서 확인하는 선택형 워크플로도 볼까요?",
        "PicClear Pro는 선택 사항입니다. 현재 스토어 설명에는 무료 스캔과 미리보기, 일회성 정리 잠금 해제, 중복·유사 사진·스크린샷·흐린 사진·대용량 파일의 기기 내 검토가 명시되어 있습니다. 확인 전에는 삭제되지 않습니다. 최신 스토어 정보를 확인하세요. 이 플래너는 앱 없이도 작동합니다.",
        "App Store에서 PicClear Pro 보기",
    ),
    faq=(
        "사진 저장 공간 정리 질문",
        (
            ("이 페이지가 사진 보관함을 스캔하나요?", "아니요. 직접 입력한 저장 공간 숫자와 선택지만 받습니다."),
            ("계산된 차이가 확보 가능한 용량인가요?", "아니요. 목표에서 현재 값을 뺀 수치일 뿐 삭제 가능한 미디어를 추정하지 않습니다."),
            ("iCloud 사진은 독립된 백업인가요?", "변경 사항이 기기 간에 반영될 수 있어 이 플래너는 동기화만을 독립 사본으로 보지 않습니다."),
            ("최근 삭제된 항목이 즉시 공간을 비우나요?", "그렇게 가정하지 마세요. Apple은 30일 복구 기간을 안내합니다. 검토 후 다시 측정하세요."),
        ),
    ),
    footer="비공개 계산만 · 사진 접근 없음 · 삭제 없음 · 확보 용량 추정 없음",
    index=(
        "비공개 사진 저장 공간 정리 플래너",
        "사진을 업로드하거나 확보 용량을 추측하지 않고 확인된 차이와 되돌릴 수 있는 검토 순서를 만드세요.",
    ),
)

_localized(
    "zh-Hans",
    meta=(
        "私密 iPhone 照片储存空间清理规划器｜不上传",
        "只用自行输入的储存数字计算可用空间差距，再建立可逆检查顺序；不上传、不扫描、不估算相册。",
        "免费工具",
        "English",
        "免费 · 不访问照片 · 不估算可清理容量",
        "私密 iPhone 照片储存空间清理规划器",
        "量出当前与目标可用空间的差距；本页不猜平均文件大小、重复率或清理后能找回多少容量。",
    ),
    badges=(
        "不接收照片、文件或元数据",
        "不访问 iCloud 或设备",
        "不删除也不分类",
        "不预测可清理容量",
    ),
    planner=(
        "计算已知的储存空间差距",
        "输入你已经能在“设置”中看到的数字；照片用量会单独显示，绝不视为可删除或可找回容量。",
    ),
    labels=(
        "当前可用空间（GB）",
        "目标可用空间（GB）",
        "iPhone 显示的照片用量（GB）",
        "iCloud 照片状态",
        "第一个检查区域",
        "我已验证无法替代的原始文件有独立副本",
        "我已检查“最近删除”",
    ),
    icloud_options=(
        "尚未检查",
        "已开启，显示同步完成",
        "已开启，正在同步、暂停或有警告",
        "已关闭",
    ),
    priority_options=(
        "一般储存检查",
        "Apple“重复项目”",
        "大型视频",
        "截屏",
    ),
    controls=(
        "更新私密规划",
        "请完整输入三个 0 到 2,048 GB 的储存数字。",
    ),
    results=(
        "仍需增加的可用空间",
        "当前可用空间",
        "目标可用空间",
        "报告的照片用量",
        "目标状态",
        "已达到目标",
        "仍有差距",
        "可逆检查顺序",
    ),
    boundaries=(
        "差距公式：max（0，目标可用 GB − 当前可用 GB）。结果沿用输入的 GB 单位，不是照片或 PicClear 能找回多少容量的预测。",
        "照片用量只供参考；内容可能很重要、已同步、已优化、共享、编辑过，或在设备上以不同方式计算。",
    ),
    icloud_steps=(
        "更改无法替代的原始文件前，先检查照片同步状态；iCloud 照片开启时，编辑与删除可能同步到其他设备。",
        "即使 iCloud 照片显示同步完成，更改与删除仍会跨设备同步；不要把同步当作唯一独立副本。",
        "进行破坏性更改前，先处理 iCloud 照片同步、暂停或空间警告，并确认实际完成同步的内容。",
        "iCloud 照片报告为关闭时，进行破坏性更改前请验证无法替代的原始文件另有独立副本。",
    ),
    priority_steps=(
        "先看“设置 > 通用 > iPhone 储存空间”的建议，再分批检查 Apple“重复项目”、视频和截屏。",
        "打开“照片 > 精选集 > 实用工具 > 重复项目”并逐组检查合并；照片未找到重复项目时，该项目可能不会出现。",
        "逐一确认视频的重要性以及独立原件能否打开；时长或分类不代表视频可以丢弃。",
        "小批量检查“截屏”，保留记录、验证、旅行、工作或辅助功能所需的内容。",
    ),
    confirmations=(
        "永久删除前，先实际打开独立副本中的抽样文件；本工具不把 iCloud 照片同步单独视为独立存档。",
        "先停止永久删除，为无法替代的原始文件建立可验证的独立副本；iCloud 照片更改可能同步到其他设备。",
        "永久移除任何项目之前，重新检查“最近删除”；永久移除会结束正常的恢复期限。",
        "先检查“最近删除”。Apple 说明删除的项目通常保留 30 天；确认无误且重要原件已独立验证前，不要清空。",
        "完成一小批检查后，重新查看 iPhone 储存空间；测量真实变化，不要假设计算差距就是可删除内容。",
    ),
    checklist=(
        "安全优先的清理顺序",
        "到“设置 > 通用 > iPhone 储存空间”核对当前可用空间与照片用量。",
        "永久删除前，验证无法替代的原始文件另有可打开的独立副本。",
        "检查 iCloud 照片同步状态，并记住更改可能跨设备同步。",
        "每次只检查一小批；不可因为分类就判定内容可以丢弃。",
        "决定下一批前，重新检查“最近删除”与设备空间。",
    ),
    scope=(
        "这个规划器无法知道什么",
        "它无法读取照片图库、储存空间、iCloud、相册、文件、元数据、个人收藏、重复、模糊、视频大小或删除结果；不会把任何内容标成可安全删除，也无法预测可找回容量。",
    ),
    sources=(
        "任何可选清理工具之前，先看 Apple 官方步骤",
        "Apple 说明 iPhone 储存空间、iCloud 照片同步与优化、“重复项目”以及“最近删除”的 30 天期限；请按当前 iOS 版本核对最新步骤。",
        (
            "Apple：查看 iPhone 与 iPad 储存空间",
            "Apple：使用 iCloud 备份与同步照片和视频",
            "Apple：在 iPhone 上合并重复照片与视频",
            "Apple：删除、恢复或永久移除照片与视频",
        ),
    ),
    webmcp=(
        "Chrome WebMCP 命令式 API 预览",
        "只用有范围、自行输入的数字计算 max（0，目标可用 GB 减当前可用 GB），单独报告照片用量，再提供可逆检查顺序；不访问照片、文件、元数据、iCloud、账号或设备空间，不估算、不分类，也不删除。",
    ),
    app=(
        "需要可选的设备端图库检查流程吗？",
        "PicClear Pro 是可选工具；当前 App Store 页面说明可免费扫描与预览，一次性解锁清理，并在设备端把重复、相似照片、截屏、模糊照片和大型文件分组供检查。确认前不会删除。请以当前商店页面为准；本规划器无需 App 也能使用。",
        "在 App Store 查看 PicClear Pro",
    ),
    faq=(
        "照片储存空间清理常见问题",
        (
            ("这个网页会扫描我的照片图库吗？", "不会。它只接收你自行输入的储存数字与状态选项。"),
            ("计算差距等于能找回的空间吗？", "不等于。它只是目标可用空间减当前可用空间，绝不估算可删除媒体。"),
            ("iCloud 照片是独立备份吗？", "本工具不把同步单独视为独立副本，因为更改与删除可能跨设备同步。"),
            ("“最近删除”会立即释放空间吗？", "不要自行假设。Apple 说明有 30 天恢复期限；完成检查后重新测量空间。"),
        ),
    ),
    footer="只做私密计算 · 不访问照片 · 不删除 · 不估算可清理容量",
    index=(
        "私密照片储存空间清理规划器",
        "计算已知可用空间差距并建立可逆检查顺序，不上传照片，也不猜可清理容量。",
    ),
)

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
                "description": str(COPY[locale]["current_label"]),
            },
            "target_free_gb": {
                **number,
                "description": str(COPY[locale]["target_label"]),
            },
            "photos_storage_gb": {
                **number,
                "description": str(COPY[locale]["photos_label"]),
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
    alternates = "\n".join(
        f'<link rel="alternate" hreflang="{item}" href="{canonical(item)}">'
        for item in ALT_LOCALES
    ) + f'\n<link rel="alternate" hreflang="x-default" href="{canonical("en")}">'
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
        "featureList": [t["planner"], *t["badges"]],
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
{alternates}
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
    for locale in ALT_LOCALES:
        relative = Path("tools") / f"{SLUG}.html"
        if locale != "en":
            relative = Path(locale) / relative
        write_text_if_changed(
            pages / relative,
            render_page(locale, app_public),
        )
        outputs.append(canonical(locale))
        root = pages if locale == "en" else pages / locale
        update_one_index(root / "tools" / "index.html", locale)
    return outputs


def main() -> None:
    outputs = build()
    sitemap_count = write_tools_sitemap()
    for output in outputs:
        print(f"photo storage cleanup planner -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
