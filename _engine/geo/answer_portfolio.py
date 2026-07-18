#!/usr/bin/env python3
"""Curated facts for portfolio-wide owned answers and decision tools."""

from __future__ import annotations

PORTFOLIO_QUERY = (
    "How can I find a privacy-first iPhone app with a one-time purchase?"
)
CONTENT_DATE = "2026-07-18"
APPLE_CAMPAIGN_SOURCE = (
    "https://developer.apple.com/help/app-store-connect-analytics/"
    "acquisition/campaign-links/"
)
GOOGLE_SCHEMA_SOURCE = (
    "https://developers.google.com/search/docs/appearance/"
    "structured-data/software-app"
)
SCHEMA_ITEM_LIST_SOURCE = "https://schema.org/ItemList"
WEBMCP_SOURCE = "https://developer.chrome.com/docs/ai/webmcp/imperative-api"

COPY = {
    "en": {
        "html_lang": "en",
        "title": "Private & Pay-Once iPhone App Finder",
        "description": (
            "Filter every verified live app in the Lumi Studio publisher portfolio "
            "by task, category, purchase model, privacy fact and Apple device surface."
        ),
        "heading": "Find the iPhone app that fits your task",
        "lead": (
            "Describe the job, then narrow the verified live portfolio using only "
            "published product facts. Results stay alphabetical and are never a paid ranking."
        ),
        "method_title": "How this finder chooses results",
        "method": [
            "Only apps present in the latest verified App Store availability cache are included.",
            "Filters use the maintained product registry: category, plain-language purpose, purchase model and explicitly stated capabilities.",
            "Results are alphabetical, not scored, sponsored or ordered by an invented popularity signal.",
            "Each result has one direct App Store link with an Apple campaign token for aggregate acquisition attribution.",
            "Supporting browser previews can expose the same read-only filters to an AI agent through WebMCP; every other browser keeps the complete human interface.",
        ],
        "boundaries_title": "What this finder does not claim",
        "boundaries": [
            "This is a first-party portfolio finder published by Lumi Studio, the developer of every listed app; it is not an independent review or third-party ranking.",
            "It does not invent prices, ratings, reviews, download counts or a best-app ranking.",
            "Privacy filters only match facts stated in the maintained listing data; absence of a badge is not a negative claim.",
            "App Store availability, compatibility and local pricing can change, so the current listing remains the final source before purchase.",
            "Filtering runs in the browser and does not submit, save or analyse the visitor's choices.",
            "WebMCP is a progressive preview integration, so its absence never blocks or changes the human finder.",
        ],
        "faqs": [
            (
                "Does the finder rank or score apps?",
                "No. Matching apps remain in alphabetical order. Filters only hide apps that do not match the selected published facts.",
            ),
            (
                "Does the finder collect my searches?",
                "No. Search and filtering run in the current browser page without an account, form submission, storage, cookies or analytics.",
            ),
            (
                "Are all apps subscriptions?",
                "No. The purchase filter distinguishes paid downloads, free-to-start apps with a lifetime unlock and any future model whose current details must be checked on the App Store.",
            ),
        ],
    },
    "zh-Hant": {
        "html_lang": "zh-Hant",
        "title": "隱私優先、一次買斷 iPhone App 篩選器",
        "description": "依任務、類別、購買模式、隱私事實與 Apple 裝置功能，篩選 Lumi Studio 開發者組合中已驗證上架的每款 App。",
        "heading": "找到真正符合任務的 iPhone App",
        "lead": "先描述要解決的事，再用公開產品事實縮小範圍。結果固定依名稱排序，不是付費排名。",
        "method_title": "篩選器如何產生結果",
        "method": [
            "只納入最新 App Store 可用性快取已驗證上架的 App。",
            "篩選依據來自維護中的產品資料：類別、白話用途、購買模式與明確列出的功能。",
            "結果依名稱排序，不計分、不接受贊助，也不使用虛構的熱門程度。",
            "每筆結果只有一個 App Store 直連，並使用 Apple campaign token 進行彙總下載歸因。",
            "支援中的瀏覽器預覽版可透過 WebMCP，讓 AI agent 使用相同的唯讀篩選；其他瀏覽器仍保留完整的人類操作介面。",
        ],
        "boundaries_title": "本工具不會做的宣稱",
        "boundaries": [
            "這是由全部上架 App 的開發者 Lumi Studio 發布的第一方作品集篩選器，不是獨立評測或第三方排行榜。",
            "不捏造價格、評分、評論、下載量或最佳 App 排名。",
            "隱私篩選只比對維護資料中明確寫出的事實；沒有徽章不代表負面判斷。",
            "App Store 供應、相容性與當地價格可能變動，購買前仍應以目前上架頁面為準。",
            "所有篩選只在瀏覽器執行，不送出、不儲存，也不分析訪客選項。",
            "WebMCP 是漸進式預覽整合；即使瀏覽器不支援，也不會阻擋或改變人類使用的篩選器。",
        ],
        "faqs": [
            (
                "篩選器會替 App 排名或打分數嗎？",
                "不會。符合條件的 App 固定依名稱排序；篩選只會隱藏不符合所選公開事實的項目。",
            ),
            (
                "篩選器會蒐集我的搜尋嗎？",
                "不會。搜尋與篩選只在目前瀏覽器頁面執行，免帳號、不送出表單、不儲存、不用 Cookie，也沒有分析追蹤。",
            ),
            (
                "這些 App 都是訂閱嗎？",
                "不是。購買篩選會分開呈現付費下載、免費開始加永久解鎖，以及未來任何需要在 App Store 確認目前詳情的模式。",
            ),
        ],
    },
}
