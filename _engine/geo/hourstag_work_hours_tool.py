#!/usr/bin/env python3
"""Generate the private HoursTag work-time calculator and AI tool."""

from __future__ import annotations

import html
import json
import os
from pathlib import Path
import re
import sys

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
SLUG = "hours-of-work-calculator"
APP_KEY = "hourstag"
APP_ID = "6754218117"
CONTENT_DATE = "2026-07-17"
APP_STORE_SOURCE = f"https://apps.apple.com/us/app/id{APP_ID}"
WEBMCP_SOURCE = "https://developer.chrome.com/docs/ai/webmcp/imperative-api"
ALT_LOCALES = (
    "en",
    "zh-Hant",
    "zh-Hans",
    "ja",
    "ko",
    "fr-FR",
    "de-DE",
    "es-ES",
    "pt-BR",
    "vi",
    "th",
    "id",
    "tr",
)
INCOME_MODES = ("hourly", "monthly")
DECISION_TAGS = ("need", "want", "impulse")

COPY = {
    "en": {
        "title": "Hours of Work Calculator | Private Price-to-Time Tool",
        "description": (
            "Convert a price into work hours, workdays and savings effort with "
            "transparent local math. No account, upload, storage or financial advice."
        ),
        "tools": "Free tools",
        "switch": "繁體中文",
        "eyebrow": "Private calculator · transparent math · AI-callable",
        "heading": "What does this purchase cost in hours of your life?",
        "lead": (
            "Use your own take-home income to turn a price into work time before "
            "checkout. The result informs a pause; it never decides whether you should buy."
        ),
        "badges": (
            "Runs only in this browser",
            "No account or bank connection",
            "No saved wage or purchase",
            "No purchase or savings promise",
        ),
        "calculator": "Calculate one honest example",
        "calculator_intro": (
            "Choose hourly or monthly take-home income. Monthly mode divides income "
            "by the paid hours you enter; hourly mode ignores that field."
        ),
        "income_mode": "Income format",
        "income_modes": {
            "hourly": "Take-home amount per hour",
            "monthly": "Take-home amount per month",
        },
        "income": "Take-home income in your currency",
        "monthly_hours": "Paid work hours per month",
        "price": "Item price before tax",
        "tax": "Sales tax or VAT percent",
        "workday": "Hours in one workday",
        "saving_rate": "Percent of take-home income set aside",
        "decision_tag": "How would you label it right now?",
        "decision_tags": {
            "need": "Need",
            "want": "Want",
            "impulse": "Impulse",
        },
        "update": "Show the time cost",
        "effective_hourly": "Effective take-home per hour",
        "total_price": "Price including entered tax",
        "work_hours": "Work hours",
        "workdays": "Workdays",
        "workday_percent": "Percent of one workday",
        "saving_hours": "Earning hours at your saving rate",
        "saving_zero": "Set a saving rate above 0% to calculate",
        "validation_error": "Enter valid positive income and work-hour values.",
        "decision_prompt": {
            "need": (
                "Need: compare the time cost with urgency, available alternatives "
                "and the consequence of waiting."
            ),
            "want": (
                "Want: decide whether this is worth the displayed work time after "
                "a cooling-off period."
            ),
            "impulse": (
                "Impulse: leave checkout, save the item elsewhere and review the "
                "same time cost after the emotional peak passes."
            ),
        },
        "math_boundary": (
            "Formula: price with entered tax ÷ effective take-home hourly value. "
            "It excludes any tax, benefits, commute, unpaid work or care cost that "
            "is not already reflected in the numbers you enter."
        ),
        "method_title": "Three checks before treating the result as useful",
        "method_steps": (
            "Use take-home income rather than an inflated gross figure.",
            "Include realistic paid hours; monthly mode cannot infer unpaid work.",
            "Treat the result as one decision lens, not financial advice or a moral score.",
        ),
        "scope_title": "What this free calculator does not do",
        "scope_text": (
            "It does not connect to a bank, remember your income, save purchases, "
            "track categories, move money, block checkout or predict savings. Refreshing "
            "or closing the page clears the current example."
        ),
        "app_title": "Want this pause available for every purchase?",
        "app_text": (
            "The free page handles one temporary example. The current HoursTag App "
            "Store listing describes an on-device workflow that sets income once, "
            "converts prices to work time, tags Need, Want or Impulse, tracks goals "
            "and a wishlist, shows monthly category insights, and supports backup and "
            "restore. It also says no account, tracking or ads, with one paid download "
            "and no subscription or hidden upgrades. Check the current listing before buying."
        ),
        "app_cta": "View HoursTag on the App Store",
        "sources_title": "Current product source and AI-tool specification",
        "app_source": "HoursTag US App Store listing",
        "webmcp_source": "Chrome WebMCP imperative API preview",
        "webmcp_description": (
            "Calculate a purchase's work-time cost from bounded, self-entered take-home "
            "income and price data. Return transparent formulas, assumptions and a "
            "decision prompt without storing data, accessing accounts, recommending a "
            "purchase or promising savings."
        ),
        "faq_title": "Work-time calculation questions",
        "faq": (
            (
                "Should I use gross or take-home income?",
                "Use take-home income for a result closer to money you can actually spend. Adjust it yourself for costs the calculator cannot know.",
            ),
            (
                "Why does monthly mode ask for paid hours?",
                "Monthly income has no hourly meaning until it is divided by a realistic number of paid work hours.",
            ),
            (
                "Does a high time cost mean I should not buy something?",
                "No. The number makes one trade-off visible; urgency, joy, durability, alternatives and your wider finances still matter.",
            ),
            (
                "Does this page save my wage or purchase?",
                "No. The calculation stays in the current page and is not uploaded or stored.",
            ),
        ),
        "footer": (
            "Private local math only · no account or bank access · not financial advice"
        ),
        "index_title": "Hours of Work to Buy Calculator",
        "index_description": (
            "Convert a price into work hours, workdays and savings effort with private, transparent math."
        ),
    },
    "zh-Hant": {
        "title": "購物要工作幾小時計算器｜私密價格換時間工具",
        "description": (
            "用透明本機算式，把價格換算成工作小時、工作天與存錢所需工時；免帳號、不上傳、不儲存，也不提供理財建議。"
        ),
        "tools": "免費工具",
        "switch": "English",
        "eyebrow": "私密計算 · 透明算式 · AI 可呼叫",
        "heading": "這筆消費，要花掉你多少工作時間？",
        "lead": (
            "用自己的實領收入，在結帳前把價格換成工作時間。結果只幫你停一下想清楚，不替你決定該不該買。"
        ),
        "badges": (
            "只在本瀏覽器運算",
            "免帳號、不連銀行",
            "不儲存薪資或消費",
            "不保證省錢或購買成果",
        ),
        "calculator": "用一筆真實消費試算",
        "calculator_intro": (
            "可選時薪或月實領收入；月薪模式會除以你輸入的每月付薪工時，時薪模式則忽略該欄。"
        ),
        "income_mode": "收入格式",
        "income_modes": {
            "hourly": "每小時實領金額",
            "monthly": "每月實領金額",
        },
        "income": "以你的幣別輸入實領收入",
        "monthly_hours": "每月付薪工作小時",
        "price": "未稅商品價格",
        "tax": "營業稅或增值稅百分比",
        "workday": "一個工作日的小時數",
        "saving_rate": "實領收入中預計存下的百分比",
        "decision_tag": "你現在會把它歸為哪一類？",
        "decision_tags": {
            "need": "需要",
            "want": "想要",
            "impulse": "衝動",
        },
        "update": "顯示時間成本",
        "effective_hourly": "每小時實領等值",
        "total_price": "含輸入稅率後價格",
        "work_hours": "工作小時",
        "workdays": "工作天",
        "workday_percent": "占一個工作日比例",
        "saving_hours": "依存錢比例所需賺取工時",
        "saving_zero": "將存錢比例設為高於 0% 即可計算",
        "validation_error": "請輸入有效且大於零的收入與工作時數。",
        "decision_prompt": {
            "need": "需要：把時間成本和急迫性、替代方案，以及延後購買的後果一起比較。",
            "want": "想要：先經過冷靜期，再判斷它是否值得畫面顯示的工作時間。",
            "impulse": "衝動：先離開結帳頁、把商品存到別處，等情緒高峰過後再看一次相同的時間成本。",
        },
        "math_boundary": (
            "算式：含輸入稅率的價格 ÷ 每小時實領等值。沒有反映在輸入數字中的稅費、福利、通勤、無薪工作或照護成本，都不會自動納入。"
        ),
        "method_title": "採用結果前，先確認三件事",
        "method_steps": (
            "使用實領收入，不要用偏高的稅前數字。",
            "輸入真實付薪工時；月薪模式無法自行知道無薪工作。",
            "把結果當成一種決策視角，不是理財建議，也不是道德評分。",
        ),
        "scope_title": "這個免費計算器不會做什麼",
        "scope_text": (
            "它不連銀行、不記住收入、不儲存消費、不追蹤分類、不移動資金、不阻止結帳，也不預測能省下多少錢。重新整理或關閉頁面後，本次範例就會清除。"
        ),
        "app_title": "想讓每次消費前都有這個停頓嗎？",
        "app_text": (
            "免費網頁一次處理一個暫時範例。目前 HoursTag 的 App Store 頁面說明，它可在裝置端設定一次收入、把價格換成工作時間、標記「需要／想要／衝動」、追蹤目標與願望清單、查看每月分類洞察，並備份與還原。頁面也說明免帳號、無追蹤、無廣告，採一次付費下載，沒有訂閱或隱藏升級。購買前請再次確認目前上架頁。"
        ),
        "app_cta": "前往 App Store 查看 HoursTag",
        "sources_title": "目前產品來源與 AI 工具規格",
        "app_source": "HoursTag 美國 App Store 上架頁",
        "webmcp_source": "Chrome WebMCP imperative API 預覽規格",
        "webmcp_description": (
            "根據有範圍限制、由使用者自行輸入的實領收入與價格，計算消費所需工作時間；回傳透明算式、假設與決策提示，不儲存資料、不存取帳號、不建議購買，也不保證省錢。"
        ),
        "faq_title": "價格換算工作時間常見問題",
        "faq": (
            (
                "該用稅前收入還是實領收入？",
                "使用實領收入，會更接近真正可支配的金額；計算器不知道的成本，仍需由你自行調整。",
            ),
            (
                "為什麼月薪模式要輸入付薪工時？",
                "月收入必須除以一個真實的付薪工作小時數，才有每小時意義。",
            ),
            (
                "時間成本很高，就代表不該買嗎？",
                "不是。數字只呈現一項取捨；急迫性、快樂、耐用度、替代方案與整體財務狀況仍然重要。",
            ),
            (
                "這個頁面會儲存我的薪資或消費嗎？",
                "不會。計算只留在目前頁面，不會上傳或儲存。",
            ),
        ),
        "footer": "只做私密本機算式 · 不存取帳號或銀行 · 非理財建議",
        "index_title": "購物要工作幾小時計算器",
        "index_description": "用私密透明算式，把價格換算成工作小時、工作天與存錢所需工時。",
    },
    "zh-Hans": {
        "title": "购物要工作几小时计算器｜私密价格换时间工具",
        "description": "用透明本地计算，把价格换算成工作小时、工作日与攒钱所需工时；免账号、不上传、不存储，也不提供理财建议。",
        "tools": "免费工具",
        "switch": "English",
        "eyebrow": "私密计算 · 透明公式 · AI 可调用",
        "heading": "这笔消费，要花掉你多少工作时间？",
        "lead": "用自己的到手收入，在结账前把价格换成工作时间。结果只帮你停下来想清楚，不替你决定该不该买。",
        "badges": (
            "只在本浏览器计算",
            "免账号、不连银行",
            "不存储工资或消费",
            "不保证省钱或购买结果",
        ),
        "calculator": "用一笔真实消费试算",
        "calculator_intro": "可选时薪或每月到手收入；月收入模式会除以你输入的每月计薪工时，时薪模式则忽略该栏。",
        "income_mode": "收入格式",
        "income_modes": {
            "hourly": "每小时到手金额",
            "monthly": "每月到手金额",
        },
        "income": "以你的币种输入到手收入",
        "monthly_hours": "每月计薪工作小时",
        "price": "未税商品价格",
        "tax": "销售税或增值税百分比",
        "workday": "一个工作日的小时数",
        "saving_rate": "到手收入中计划存下的百分比",
        "decision_tag": "你现在会把它归为哪一类？",
        "decision_tags": {"need": "需要", "want": "想要", "impulse": "冲动"},
        "update": "显示时间成本",
        "effective_hourly": "每小时到手等值",
        "total_price": "含输入税率后的价格",
        "work_hours": "工作小时",
        "workdays": "工作日",
        "workday_percent": "占一个工作日的比例",
        "saving_hours": "按储蓄比例所需赚取工时",
        "saving_zero": "将储蓄比例设为高于 0% 即可计算",
        "validation_error": "请输入有效且大于零的收入与工作时数。",
        "decision_prompt": {
            "need": "需要：把时间成本与紧迫性、替代方案，以及推迟购买的后果一起比较。",
            "want": "想要：先经过冷静期，再判断它是否值得画面显示的工作时间。",
            "impulse": "冲动：先离开结账页、把商品存到别处，等情绪高峰过去后再看一次相同的时间成本。",
        },
        "math_boundary": "公式：含输入税率的价格 ÷ 每小时到手等值。没有反映在输入数字中的税费、福利、通勤、无薪工作或照护成本，都不会自动计入。",
        "method_title": "采用结果前，先确认三件事",
        "method_steps": (
            "使用到手收入，不要用偏高的税前数字。",
            "输入真实计薪工时；月收入模式无法自行知道无薪工作。",
            "把结果当作一种决策视角，不是理财建议，也不是道德评分。",
        ),
        "scope_title": "这个免费计算器不会做什么",
        "scope_text": "它不连接银行、不记住收入、不存储消费、不追踪分类、不转移资金、不阻止结账，也不预测能省下多少钱。刷新或关闭页面后，本次示例就会清除。",
        "app_title": "想让每次消费前都有这个停顿吗？",
        "app_text": "免费网页一次处理一个临时示例。目前 HoursTag 的 App Store 页面说明，它可在设备端设置一次收入、把价格换成工作时间、标记“需要／想要／冲动”、追踪目标与愿望清单、查看每月分类洞察，并备份与恢复。页面也说明免账号、无追踪、无广告，采用一次付费下载，没有订阅或隐藏升级。购买前请再次确认当前上架页。",
        "app_cta": "前往 App Store 查看 HoursTag",
        "sources_title": "当前产品来源与 AI 工具规范",
        "app_source": "HoursTag 美国 App Store 上架页",
        "webmcp_source": "Chrome WebMCP imperative API 预览规范",
        "webmcp_description": "根据有范围限制、由用户自行输入的到手收入与价格，计算消费所需工作时间；返回透明公式、假设与决策提示，不存储数据、不访问账号、不建议购买，也不保证省钱。",
        "faq_title": "价格换算工作时间常见问题",
        "faq": (
            ("该用税前收入还是到手收入？", "使用到手收入，会更接近真正可支配的金额；计算器不知道的成本，仍需由你自行调整。"),
            ("为什么月收入模式要输入计薪工时？", "月收入必须除以一个真实的计薪工作小时数，才有每小时意义。"),
            ("时间成本很高，就代表不该买吗？", "不是。数字只呈现一项取舍；紧迫性、快乐、耐用度、替代方案与整体财务状况仍然重要。"),
            ("这个页面会存储我的工资或消费吗？", "不会。计算只留在当前页面，不会上传或存储。"),
        ),
        "footer": "只做私密本地计算 · 不访问账号或银行 · 非理财建议",
        "index_title": "购物要工作几小时计算器",
        "index_description": "用私密透明计算，把价格换算成工作小时、工作日与攒钱所需工时。",
    },
    "ja": {
        "title": "購入価格を労働時間に換算｜プライベート計算ツール",
        "description": "価格を労働時間、勤務日数、貯蓄に必要な労働時間へ換算。アカウント、送信、保存は不要で、金融助言も行いません。",
        "tools": "無料ツール",
        "switch": "English",
        "eyebrow": "プライベート計算 · 透明な式 · AI から利用可能",
        "heading": "この買い物は、人生の労働時間でいくら？",
        "lead": "手取り収入を使い、会計前に価格を労働時間へ換算します。立ち止まって考えるための数字であり、購入の可否は決めません。",
        "badges": (
            "このブラウザ内だけで計算",
            "アカウント・銀行連携なし",
            "収入や購入内容を保存しない",
            "節約や購入結果を保証しない",
        ),
        "calculator": "実際の買い物を一件試算",
        "calculator_intro": "時給または月の手取りを選択します。月額モードは入力した月間有給労働時間で割り、時給モードではその欄を使いません。",
        "income_mode": "収入の形式",
        "income_modes": {"hourly": "1時間あたりの手取り", "monthly": "1か月あたりの手取り"},
        "income": "自分の通貨で手取り収入を入力",
        "monthly_hours": "月間の有給労働時間",
        "price": "税抜きの商品価格",
        "tax": "消費税・付加価値税率",
        "workday": "1勤務日の時間数",
        "saving_rate": "手取りから貯蓄に回す割合",
        "decision_tag": "今の気持ちに近い分類は？",
        "decision_tags": {"need": "必要", "want": "欲しい", "impulse": "衝動"},
        "update": "時間コストを表示",
        "effective_hourly": "実質手取り時給",
        "total_price": "入力税率を含む価格",
        "work_hours": "労働時間",
        "workdays": "勤務日数",
        "workday_percent": "1勤務日に占める割合",
        "saving_hours": "貯蓄率を踏まえた必要労働時間",
        "saving_zero": "貯蓄率を 0% より大きくすると計算できます",
        "validation_error": "収入と労働時間に、0 より大きい有効な値を入力してください。",
        "decision_prompt": {
            "need": "必要：時間コストを、緊急性、代替手段、先送りした場合の影響と比べてください。",
            "want": "欲しい：クールダウン期間を置き、表示された労働時間に見合うかを改めて判断してください。",
            "impulse": "衝動：いったん会計画面を離れ、商品を別の場所に保存し、気持ちが落ち着いてから同じ時間コストを見直してください。",
        },
        "math_boundary": "式：入力した税率込み価格 ÷ 実質手取り時給。入力値に含まれない税、福利厚生、通勤、無給労働、介護・育児コストは自動計算されません。",
        "method_title": "結果を使う前の3つの確認",
        "method_steps": (
            "高く見えやすい額面ではなく、手取り収入を使う。",
            "実際の有給労働時間を入力する。月額モードは無給労働を推測できません。",
            "結果は判断材料の一つであり、金融助言や善悪の採点ではありません。",
        ),
        "scope_title": "この無料計算ツールがしないこと",
        "scope_text": "銀行への接続、収入の記憶、購入の保存、カテゴリ追跡、送金、会計のブロック、節約額の予測は行いません。再読み込みまたはページを閉じると現在の例は消えます。",
        "app_title": "すべての買い物で、この立ち止まる習慣を身につけたいですか？",
        "app_text": "無料ページは一時的な例を一件だけ計算します。現在の App Store 掲載情報では、HoursTag は端末上で収入を一度設定し、価格を労働時間へ換算し、「必要・欲しい・衝動」のタグ、目標とウィッシュリスト、月別カテゴリ分析、バックアップと復元を利用できます。アカウント、トラッキング、広告はなく、買い切りでサブスクリプションや隠れたアップグレードもないと記載されています。購入前に最新の掲載情報をご確認ください。",
        "app_cta": "App Store で HoursTag を見る",
        "sources_title": "現在の商品情報と AI ツール仕様",
        "app_source": "HoursTag 米国 App Store 掲載情報",
        "webmcp_source": "Chrome WebMCP imperative API プレビュー仕様",
        "webmcp_description": "範囲を制限した自己入力の手取り収入と価格から、購入に必要な労働時間を計算します。透明な式、前提、判断の問いを返し、データ保存、アカウントアクセス、購入推奨、節約保証は行いません。",
        "faq_title": "価格と労働時間のよくある質問",
        "faq": (
            ("額面と手取りのどちらを使いますか？", "実際に使える金額に近づけるには手取りを使います。計算ツールが把握できない費用は自分で調整してください。"),
            ("月額モードで有給労働時間が必要なのはなぜですか？", "月収を実際の有給労働時間で割らなければ、1時間あたりの価値を出せないためです。"),
            ("時間コストが高ければ、買うべきではありませんか？", "いいえ。この数字は一つの交換条件を示すだけです。緊急性、喜び、耐久性、代替手段、家計全体も重要です。"),
            ("収入や購入内容は保存されますか？", "いいえ。計算は現在のページ内だけで行われ、送信も保存もされません。"),
        ),
        "footer": "プライベートな端末内計算のみ · アカウント・銀行アクセスなし · 金融助言ではありません",
        "index_title": "購入に必要な労働時間計算ツール",
        "index_description": "価格を労働時間、勤務日数、貯蓄に必要な労働時間へ、透明な式で換算します。",
    },
    "ko": {
        "title": "구매 가격을 노동시간으로 환산｜개인정보 보호 계산기",
        "description": "가격을 노동시간, 근무일, 저축에 필요한 근로시간으로 환산합니다. 계정·업로드·저장 없이 작동하며 금융 조언을 제공하지 않습니다.",
        "tools": "무료 도구",
        "switch": "English",
        "eyebrow": "비공개 계산 · 투명한 공식 · AI 호출 지원",
        "heading": "이 구매는 내 삶의 노동시간으로 얼마일까요?",
        "lead": "실수령 소득으로 결제 전 가격을 노동시간으로 바꿔 보세요. 잠시 멈춰 생각하기 위한 수치일 뿐, 구매 여부를 대신 결정하지 않습니다.",
        "badges": (
            "이 브라우저 안에서만 계산",
            "계정·은행 연결 없음",
            "급여나 구매 내역을 저장하지 않음",
            "절약이나 구매 결과를 보장하지 않음",
        ),
        "calculator": "실제 구매 한 건 계산하기",
        "calculator_intro": "시간당 또는 월 실수령 소득을 선택하세요. 월 소득 모드는 입력한 월 유급 근로시간으로 나누며, 시간당 모드에서는 해당 항목을 사용하지 않습니다.",
        "income_mode": "소득 입력 방식",
        "income_modes": {"hourly": "시간당 실수령액", "monthly": "월 실수령액"},
        "income": "사용하는 통화로 실수령 소득 입력",
        "monthly_hours": "월 유급 근로시간",
        "price": "세전 상품 가격",
        "tax": "판매세 또는 부가가치세율",
        "workday": "하루 근무시간",
        "saving_rate": "실수령 소득 중 저축 비율",
        "decision_tag": "지금 이 구매를 어떻게 분류하나요?",
        "decision_tags": {"need": "필요", "want": "원함", "impulse": "충동"},
        "update": "시간 비용 보기",
        "effective_hourly": "실질 시간당 실수령액",
        "total_price": "입력한 세율 포함 가격",
        "work_hours": "노동시간",
        "workdays": "근무일",
        "workday_percent": "하루 근무시간 대비 비율",
        "saving_hours": "저축 비율을 반영한 필요 근로시간",
        "saving_zero": "저축 비율을 0%보다 크게 설정하면 계산됩니다",
        "validation_error": "소득과 근로시간에 0보다 큰 올바른 값을 입력하세요.",
        "decision_prompt": {
            "need": "필요: 시간 비용을 긴급성, 대안, 구매를 미뤘을 때의 영향과 함께 비교하세요.",
            "want": "원함: 잠시 시간을 둔 뒤, 표시된 노동시간을 들일 가치가 있는지 다시 판단하세요.",
            "impulse": "충동: 결제 화면을 닫고 상품을 다른 곳에 저장한 뒤, 감정이 가라앉으면 같은 시간 비용을 다시 확인하세요.",
        },
        "math_boundary": "공식: 입력한 세율 포함 가격 ÷ 실질 시간당 실수령액. 입력값에 반영되지 않은 세금, 복리후생, 통근, 무급 노동, 돌봄 비용은 자동으로 포함되지 않습니다.",
        "method_title": "결과를 활용하기 전 세 가지 확인",
        "method_steps": (
            "부풀려 보일 수 있는 세전 금액보다 실수령 소득을 사용하세요.",
            "실제 유급 근로시간을 입력하세요. 월 소득 모드는 무급 노동을 추정할 수 없습니다.",
            "결과는 판단 기준 중 하나일 뿐 금융 조언이나 도덕적 점수가 아닙니다.",
        ),
        "scope_title": "이 무료 계산기가 하지 않는 일",
        "scope_text": "은행 연결, 소득 기억, 구매 저장, 카테고리 추적, 송금, 결제 차단, 절약액 예측을 하지 않습니다. 새로고침하거나 페이지를 닫으면 현재 예시는 사라집니다.",
        "app_title": "모든 구매 전에 이런 멈춤을 만들고 싶나요?",
        "app_text": "무료 페이지는 임시 예시 한 건만 계산합니다. 현재 App Store 설명에 따르면 HoursTag는 기기에서 소득을 한 번 설정하고 가격을 노동시간으로 환산하며, 필요·원함·충동 태그, 목표와 위시리스트, 월별 카테고리 인사이트, 백업과 복원을 제공합니다. 계정, 추적, 광고가 없고 구독이나 숨은 업그레이드 없이 한 번 구매하는 앱이라고 명시되어 있습니다. 구매 전 최신 등록 정보를 확인하세요.",
        "app_cta": "App Store에서 HoursTag 보기",
        "sources_title": "현재 제품 출처와 AI 도구 사양",
        "app_source": "HoursTag 미국 App Store 등록 정보",
        "webmcp_source": "Chrome WebMCP imperative API 미리보기 사양",
        "webmcp_description": "범위가 제한된 사용자의 실수령 소득과 가격 입력으로 구매 노동시간을 계산합니다. 투명한 공식, 가정, 판단 질문을 반환하며 데이터를 저장하거나 계정에 접근하거나 구매를 권유하거나 절약을 보장하지 않습니다.",
        "faq_title": "가격을 노동시간으로 환산하는 자주 묻는 질문",
        "faq": (
            ("세전 소득과 실수령 소득 중 무엇을 쓰나요?", "실제로 쓸 수 있는 돈에 가깝게 계산하려면 실수령 소득을 사용하세요. 계산기가 알 수 없는 비용은 직접 조정해야 합니다."),
            ("월 소득 모드에 유급 근로시간이 필요한 이유는 무엇인가요?", "월 소득을 현실적인 유급 근로시간으로 나눠야 시간당 가치가 나오기 때문입니다."),
            ("시간 비용이 높으면 사지 말아야 하나요?", "아닙니다. 이 숫자는 한 가지 기회비용만 보여 줍니다. 긴급성, 즐거움, 내구성, 대안, 전체 재정 상황도 중요합니다."),
            ("급여나 구매 내역을 저장하나요?", "아닙니다. 계산은 현재 페이지 안에서만 이루어지며 업로드되거나 저장되지 않습니다."),
        ),
        "footer": "비공개 로컬 계산만 제공 · 계정·은행 접근 없음 · 금융 조언 아님",
        "index_title": "구매에 필요한 노동시간 계산기",
        "index_description": "가격을 노동시간, 근무일, 저축에 필요한 근로시간으로 투명하게 환산합니다.",
    },
    "fr-FR": {
        "title": "Calculateur de prix en heures de travail｜Outil privé",
        "description": "Convertissez un prix en heures, journées de travail et effort d’épargne grâce à un calcul local transparent, sans compte, envoi, stockage ni conseil financier.",
        "tools": "Outils gratuits",
        "switch": "English",
        "eyebrow": "Calcul privé · formule transparente · accessible aux IA",
        "heading": "Combien d’heures de votre vie coûte cet achat ?",
        "lead": "Utilisez votre revenu net pour traduire un prix en temps de travail avant de payer. Le résultat invite à réfléchir ; il ne décide jamais à votre place.",
        "badges": (
            "Calcul uniquement dans ce navigateur",
            "Aucun compte ni lien bancaire",
            "Aucun salaire ou achat enregistré",
            "Aucune promesse d’économie ou d’achat",
        ),
        "calculator": "Tester un achat réel",
        "calculator_intro": "Choisissez un revenu net horaire ou mensuel. Le mode mensuel le divise par vos heures rémunérées ; le mode horaire ignore ce champ.",
        "income_mode": "Format du revenu",
        "income_modes": {"hourly": "Revenu net par heure", "monthly": "Revenu net par mois"},
        "income": "Revenu net dans votre devise",
        "monthly_hours": "Heures rémunérées par mois",
        "price": "Prix hors taxe",
        "tax": "Taxe de vente ou TVA en %",
        "workday": "Heures dans une journée de travail",
        "saving_rate": "Part du revenu net mise de côté",
        "decision_tag": "Comment classeriez-vous cet achat maintenant ?",
        "decision_tags": {"need": "Besoin", "want": "Envie", "impulse": "Impulsion"},
        "update": "Afficher le coût en temps",
        "effective_hourly": "Revenu net horaire effectif",
        "total_price": "Prix avec la taxe saisie",
        "work_hours": "Heures de travail",
        "workdays": "Journées de travail",
        "workday_percent": "Part d’une journée de travail",
        "saving_hours": "Heures gagnées selon votre taux d’épargne",
        "saving_zero": "Saisissez un taux d’épargne supérieur à 0 % pour calculer",
        "validation_error": "Saisissez des valeurs de revenu et d’heures valides et supérieures à zéro.",
        "decision_prompt": {
            "need": "Besoin : comparez le coût en temps à l’urgence, aux solutions de remplacement et aux conséquences d’une attente.",
            "want": "Envie : après un délai de réflexion, demandez-vous si cet achat vaut le temps de travail affiché.",
            "impulse": "Impulsion : quittez le paiement, enregistrez l’article ailleurs et réévaluez le même coût en temps une fois l’émotion retombée.",
        },
        "math_boundary": "Formule : prix avec la taxe saisie ÷ revenu net horaire effectif. Les impôts, avantages, trajets, tâches non rémunérées ou frais de garde absents de vos chiffres ne sont pas ajoutés automatiquement.",
        "method_title": "Trois vérifications avant d’utiliser le résultat",
        "method_steps": (
            "Utilisez le revenu net plutôt qu’un montant brut surestimé.",
            "Saisissez des heures rémunérées réalistes ; le mode mensuel ne peut pas deviner le travail non payé.",
            "Considérez le résultat comme un angle de décision, jamais comme un conseil financier ou un jugement moral.",
        ),
        "scope_title": "Ce que ce calculateur gratuit ne fait pas",
        "scope_text": "Il ne se connecte pas à une banque, ne mémorise pas vos revenus, n’enregistre pas vos achats, ne suit pas de catégories, ne transfère pas d’argent, ne bloque pas le paiement et ne prédit pas vos économies. Actualiser ou fermer la page efface l’exemple.",
        "app_title": "Vous voulez retrouver cette pause avant chaque achat ?",
        "app_text": "La page gratuite traite un exemple temporaire. La fiche App Store actuelle indique que HoursTag permet de définir une fois son revenu sur l’appareil, de convertir les prix en temps de travail, de classer Besoin, Envie ou Impulsion, de suivre des objectifs et une liste de souhaits, d’afficher des tendances mensuelles par catégorie, puis de sauvegarder et restaurer ses données. Elle indique aussi : aucun compte, suivi ou publicité, achat unique sans abonnement ni mise à niveau cachée. Vérifiez la fiche actuelle avant l’achat.",
        "app_cta": "Voir HoursTag sur l’App Store",
        "sources_title": "Source produit actuelle et spécification de l’outil IA",
        "app_source": "Fiche HoursTag sur l’App Store américain",
        "webmcp_source": "Aperçu de l’API impérative Chrome WebMCP",
        "webmcp_description": "Calcule le coût d’un achat en temps de travail à partir d’un revenu net et d’un prix saisis dans des limites définies. Renvoie formules, hypothèses et question de réflexion sans stockage, accès aux comptes, recommandation d’achat ni promesse d’économie.",
        "faq_title": "Questions sur le coût en temps de travail",
        "faq": (
            ("Faut-il saisir le revenu brut ou net ?", "Utilisez le revenu net pour vous rapprocher de l’argent réellement disponible. Ajustez vous-même les coûts inconnus du calculateur."),
            ("Pourquoi le mode mensuel demande-t-il les heures rémunérées ?", "Un revenu mensuel n’a de valeur horaire qu’après division par un nombre réaliste d’heures rémunérées."),
            ("Un coût en temps élevé signifie-t-il qu’il ne faut pas acheter ?", "Non. Le chiffre rend visible un seul arbitrage ; l’urgence, le plaisir, la durabilité, les alternatives et vos finances globales comptent aussi."),
            ("Cette page enregistre-t-elle mon salaire ou mon achat ?", "Non. Le calcul reste dans la page actuelle et n’est ni envoyé ni enregistré."),
        ),
        "footer": "Calcul local et privé uniquement · aucun accès aux comptes ou banques · pas un conseil financier",
        "index_title": "Calculateur d’heures de travail pour un achat",
        "index_description": "Convertissez un prix en heures, journées de travail et effort d’épargne grâce à une formule privée et transparente.",
    },
    "de-DE": {
        "title": "Kaufpreis in Arbeitszeit umrechnen｜Privater Rechner",
        "description": "Rechne einen Preis mit transparenter lokaler Mathematik in Arbeitsstunden, Arbeitstage und Sparaufwand um – ohne Konto, Upload, Speicherung oder Finanzberatung.",
        "tools": "Kostenlose Tools",
        "switch": "English",
        "eyebrow": "Private Berechnung · transparente Formel · KI-aufrufbar",
        "heading": "Wie viele Stunden deines Lebens kostet dieser Kauf?",
        "lead": "Rechne einen Preis vor dem Bezahlen mit deinem Nettoeinkommen in Arbeitszeit um. Das Ergebnis schafft eine Denkpause, entscheidet aber nie für dich.",
        "badges": (
            "Berechnung nur in diesem Browser",
            "Kein Konto oder Bankzugriff",
            "Kein Gehalt oder Kauf gespeichert",
            "Kein Spar- oder Kaufversprechen",
        ),
        "calculator": "Einen echten Kauf durchrechnen",
        "calculator_intro": "Wähle Netto pro Stunde oder Monat. Im Monatsmodus wird durch deine bezahlten Monatsstunden geteilt; im Stundenmodus bleibt dieses Feld unberücksichtigt.",
        "income_mode": "Einkommensformat",
        "income_modes": {"hourly": "Netto pro Stunde", "monthly": "Netto pro Monat"},
        "income": "Nettoeinkommen in deiner Währung",
        "monthly_hours": "Bezahlte Arbeitsstunden pro Monat",
        "price": "Artikelpreis vor Steuern",
        "tax": "Umsatz- oder Mehrwertsteuer in %",
        "workday": "Stunden pro Arbeitstag",
        "saving_rate": "Anteil des Nettoeinkommens zum Sparen",
        "decision_tag": "Wie würdest du den Kauf jetzt einordnen?",
        "decision_tags": {"need": "Bedarf", "want": "Wunsch", "impulse": "Impuls"},
        "update": "Zeitkosten anzeigen",
        "effective_hourly": "Effektiver Nettostundenlohn",
        "total_price": "Preis einschließlich eingegebener Steuer",
        "work_hours": "Arbeitsstunden",
        "workdays": "Arbeitstage",
        "workday_percent": "Anteil eines Arbeitstags",
        "saving_hours": "Erwerbsstunden bei deiner Sparquote",
        "saving_zero": "Lege eine Sparquote über 0 % fest, um zu rechnen",
        "validation_error": "Gib gültige positive Werte für Einkommen und Arbeitszeit ein.",
        "decision_prompt": {
            "need": "Bedarf: Vergleiche die Zeitkosten mit Dringlichkeit, Alternativen und den Folgen des Wartens.",
            "want": "Wunsch: Prüfe nach einer Bedenkzeit erneut, ob der Kauf die angezeigte Arbeitszeit wert ist.",
            "impulse": "Impuls: Verlasse den Bezahlvorgang, speichere den Artikel woanders und prüfe dieselben Zeitkosten nach dem emotionalen Höhepunkt erneut.",
        },
        "math_boundary": "Formel: Preis einschließlich eingegebener Steuer ÷ effektiver Nettostundenlohn. Steuern, Leistungen, Pendeln, unbezahlte Arbeit oder Betreuungskosten, die nicht in deinen Eingaben stecken, werden nicht automatisch berücksichtigt.",
        "method_title": "Drei Prüfungen, bevor du das Ergebnis nutzt",
        "method_steps": (
            "Nutze das Nettoeinkommen statt eines zu hoch wirkenden Bruttobetrags.",
            "Gib realistische bezahlte Stunden ein; der Monatsmodus kann unbezahlte Arbeit nicht erkennen.",
            "Sieh das Ergebnis als einen Blickwinkel, nicht als Finanzberatung oder moralische Bewertung.",
        ),
        "scope_title": "Was dieser kostenlose Rechner nicht tut",
        "scope_text": "Er verbindet sich nicht mit Banken, merkt sich kein Einkommen, speichert keine Käufe, verfolgt keine Kategorien, überweist kein Geld, blockiert keinen Checkout und prognostiziert keine Ersparnis. Neuladen oder Schließen löscht das aktuelle Beispiel.",
        "app_title": "Möchtest du diese Denkpause bei jedem Kauf?",
        "app_text": "Die kostenlose Seite berechnet ein vorübergehendes Beispiel. Laut aktueller App-Store-Beschreibung kannst du in HoursTag dein Einkommen einmal auf dem Gerät festlegen, Preise in Arbeitszeit umrechnen, Bedarf, Wunsch oder Impuls markieren, Ziele und Wunschlisten verfolgen, monatliche Kategorien auswerten sowie Daten sichern und wiederherstellen. Die Beschreibung nennt außerdem: kein Konto, Tracking oder Werbung, einmaliger Kauf ohne Abo oder versteckte Upgrades. Prüfe vor dem Kauf die aktuelle Store-Seite.",
        "app_cta": "HoursTag im App Store ansehen",
        "sources_title": "Aktuelle Produktquelle und Spezifikation des KI-Tools",
        "app_source": "HoursTag im US App Store",
        "webmcp_source": "Vorschau der imperativen Chrome-WebMCP-API",
        "webmcp_description": "Berechnet aus begrenzten, selbst eingegebenen Netto- und Preisdaten die Arbeitszeit eines Kaufs. Gibt transparente Formeln, Annahmen und einen Denkimpuls zurück – ohne Speicherung, Kontozugriff, Kaufempfehlung oder Sparversprechen.",
        "faq_title": "Fragen zur Umrechnung in Arbeitszeit",
        "faq": (
            ("Soll ich Brutto- oder Nettoeinkommen verwenden?", "Nutze Netto für ein Ergebnis näher am tatsächlich verfügbaren Geld. Kosten, die der Rechner nicht kennt, musst du selbst berücksichtigen."),
            ("Warum fragt der Monatsmodus nach bezahlten Stunden?", "Ein Monatseinkommen erhält erst durch die Division durch realistische bezahlte Stunden einen Stundenwert."),
            ("Bedeuten hohe Zeitkosten, dass ich nicht kaufen sollte?", "Nein. Die Zahl zeigt nur einen Tausch sichtbar; Dringlichkeit, Freude, Haltbarkeit, Alternativen und deine Gesamtfinanzen zählen ebenfalls."),
            ("Speichert die Seite mein Gehalt oder meinen Kauf?", "Nein. Die Berechnung bleibt auf der aktuellen Seite und wird weder hochgeladen noch gespeichert."),
        ),
        "footer": "Nur private lokale Berechnung · kein Konto- oder Bankzugriff · keine Finanzberatung",
        "index_title": "Arbeitszeit-Rechner für Einkäufe",
        "index_description": "Rechne einen Preis privat und transparent in Arbeitsstunden, Arbeitstage und Sparaufwand um.",
    },
    "es-ES": {
        "title": "Calculadora de precio en horas de trabajo｜Herramienta privada",
        "description": "Convierte un precio en horas, jornadas de trabajo y esfuerzo de ahorro con cálculo local transparente, sin cuenta, carga, almacenamiento ni asesoramiento financiero.",
        "tools": "Herramientas gratis",
        "switch": "English",
        "eyebrow": "Cálculo privado · fórmula transparente · accesible para IA",
        "heading": "¿Cuántas horas de tu vida cuesta esta compra?",
        "lead": "Usa tus ingresos netos para convertir un precio en tiempo de trabajo antes de pagar. El resultado invita a parar y pensar; nunca decide por ti.",
        "badges": (
            "Cálculo solo en este navegador",
            "Sin cuenta ni conexión bancaria",
            "No guarda sueldo ni compra",
            "Sin promesas de ahorro o compra",
        ),
        "calculator": "Calcular una compra real",
        "calculator_intro": "Elige ingresos netos por hora o por mes. El modo mensual divide por las horas remuneradas que indiques; el modo por hora ignora ese campo.",
        "income_mode": "Formato de ingresos",
        "income_modes": {"hourly": "Ingreso neto por hora", "monthly": "Ingreso neto por mes"},
        "income": "Ingreso neto en tu moneda",
        "monthly_hours": "Horas remuneradas al mes",
        "price": "Precio antes de impuestos",
        "tax": "Impuesto sobre ventas o IVA %",
        "workday": "Horas de una jornada laboral",
        "saving_rate": "Porcentaje del ingreso neto destinado al ahorro",
        "decision_tag": "¿Cómo clasificarías esta compra ahora?",
        "decision_tags": {"need": "Necesidad", "want": "Deseo", "impulse": "Impulso"},
        "update": "Mostrar el coste en tiempo",
        "effective_hourly": "Ingreso neto efectivo por hora",
        "total_price": "Precio con el impuesto indicado",
        "work_hours": "Horas de trabajo",
        "workdays": "Jornadas de trabajo",
        "workday_percent": "Porcentaje de una jornada",
        "saving_hours": "Horas de trabajo según tu tasa de ahorro",
        "saving_zero": "Indica una tasa de ahorro superior al 0 % para calcular",
        "validation_error": "Introduce valores válidos y positivos para ingresos y horas de trabajo.",
        "decision_prompt": {
            "need": "Necesidad: compara el coste en tiempo con la urgencia, las alternativas y las consecuencias de esperar.",
            "want": "Deseo: tras un periodo de reflexión, decide si merece las horas de trabajo mostradas.",
            "impulse": "Impulso: sal del pago, guarda el artículo en otro lugar y revisa el mismo coste en tiempo cuando pase el pico emocional.",
        },
        "math_boundary": "Fórmula: precio con el impuesto indicado ÷ ingreso neto efectivo por hora. No añade impuestos, prestaciones, desplazamientos, trabajo no remunerado ni cuidados que no estén reflejados en tus cifras.",
        "method_title": "Tres comprobaciones antes de usar el resultado",
        "method_steps": (
            "Usa ingresos netos y no una cifra bruta que exagere tu capacidad real.",
            "Introduce horas remuneradas realistas; el modo mensual no puede deducir el trabajo no pagado.",
            "Trata el resultado como una perspectiva, no como asesoramiento financiero ni juicio moral.",
        ),
        "scope_title": "Lo que no hace esta calculadora gratuita",
        "scope_text": "No se conecta al banco, no recuerda tus ingresos, no guarda compras, no sigue categorías, no mueve dinero, no bloquea el pago ni predice ahorros. Al recargar o cerrar la página se borra el ejemplo actual.",
        "app_title": "¿Quieres esta pausa antes de cada compra?",
        "app_text": "La página gratuita calcula un ejemplo temporal. La ficha actual de App Store indica que HoursTag permite configurar una vez los ingresos en el dispositivo, convertir precios en tiempo de trabajo, etiquetar Necesidad, Deseo o Impulso, seguir objetivos y una lista de deseos, ver análisis mensuales por categoría y hacer copias de seguridad y restaurarlas. También indica que no hay cuenta, seguimiento ni anuncios, y que es una compra única sin suscripción ni mejoras ocultas. Comprueba la ficha actual antes de comprar.",
        "app_cta": "Ver HoursTag en la App Store",
        "sources_title": "Fuente actual del producto y especificación de la herramienta de IA",
        "app_source": "Ficha de HoursTag en la App Store de EE. UU.",
        "webmcp_source": "Vista previa de la API imperativa Chrome WebMCP",
        "webmcp_description": "Calcula el coste de una compra en tiempo de trabajo a partir de ingresos netos y precio introducidos dentro de límites definidos. Devuelve fórmulas, supuestos y una pregunta de reflexión sin guardar datos, acceder a cuentas, recomendar la compra ni prometer ahorro.",
        "faq_title": "Preguntas sobre el coste en horas de trabajo",
        "faq": (
            ("¿Debo usar ingresos brutos o netos?", "Usa ingresos netos para acercarte al dinero realmente disponible. Ajusta por tu cuenta los costes que la calculadora no conoce."),
            ("¿Por qué el modo mensual pide horas remuneradas?", "Un ingreso mensual solo tiene valor por hora al dividirlo entre un número realista de horas remuneradas."),
            ("¿Un coste alto en tiempo significa que no debo comprar?", "No. La cifra muestra una sola compensación; también importan la urgencia, el disfrute, la durabilidad, las alternativas y tus finanzas globales."),
            ("¿La página guarda mi sueldo o mi compra?", "No. El cálculo se queda en la página actual y no se carga ni se almacena."),
        ),
        "footer": "Solo cálculo local y privado · sin acceso a cuentas o bancos · no es asesoramiento financiero",
        "index_title": "Calculadora de horas de trabajo para comprar",
        "index_description": "Convierte un precio en horas, jornadas de trabajo y esfuerzo de ahorro mediante una fórmula privada y transparente.",
    },
    "pt-BR": {
        "title": "Calculadora de preço em horas de trabalho｜Ferramenta privada",
        "description": "Converta um preço em horas, dias de trabalho e esforço de economia com cálculo local transparente, sem conta, envio, armazenamento ou orientação financeira.",
        "tools": "Ferramentas gratuitas",
        "switch": "English",
        "eyebrow": "Cálculo privado · fórmula transparente · acessível por IA",
        "heading": "Quantas horas da sua vida esta compra custa?",
        "lead": "Use sua renda líquida para transformar um preço em tempo de trabalho antes de pagar. O resultado cria uma pausa para pensar; nunca decide por você.",
        "badges": (
            "Cálculo somente neste navegador",
            "Sem conta ou conexão bancária",
            "Não salva salário ou compra",
            "Sem promessa de economia ou compra",
        ),
        "calculator": "Calcular uma compra real",
        "calculator_intro": "Escolha renda líquida por hora ou por mês. O modo mensal divide pelas horas remuneradas informadas; o modo por hora ignora esse campo.",
        "income_mode": "Formato da renda",
        "income_modes": {"hourly": "Renda líquida por hora", "monthly": "Renda líquida por mês"},
        "income": "Renda líquida na sua moeda",
        "monthly_hours": "Horas remuneradas por mês",
        "price": "Preço antes dos impostos",
        "tax": "Imposto sobre vendas ou IVA %",
        "workday": "Horas em um dia de trabalho",
        "saving_rate": "Percentual da renda líquida reservado",
        "decision_tag": "Como você classificaria esta compra agora?",
        "decision_tags": {"need": "Necessidade", "want": "Desejo", "impulse": "Impulso"},
        "update": "Mostrar o custo em tempo",
        "effective_hourly": "Renda líquida efetiva por hora",
        "total_price": "Preço com o imposto informado",
        "work_hours": "Horas de trabalho",
        "workdays": "Dias de trabalho",
        "workday_percent": "Percentual de um dia de trabalho",
        "saving_hours": "Horas ganhas conforme sua taxa de economia",
        "saving_zero": "Informe uma taxa de economia acima de 0% para calcular",
        "validation_error": "Informe valores válidos e positivos para renda e horas de trabalho.",
        "decision_prompt": {
            "need": "Necessidade: compare o custo em tempo com a urgência, as alternativas e as consequências de esperar.",
            "want": "Desejo: após um período de reflexão, decida se vale as horas de trabalho exibidas.",
            "impulse": "Impulso: saia do pagamento, salve o item em outro lugar e reveja o mesmo custo em tempo quando o pico emocional passar.",
        },
        "math_boundary": "Fórmula: preço com o imposto informado ÷ renda líquida efetiva por hora. Impostos, benefícios, deslocamento, trabalho não remunerado ou cuidados que não estejam nos seus números não são incluídos automaticamente.",
        "method_title": "Três verificações antes de usar o resultado",
        "method_steps": (
            "Use a renda líquida, não um valor bruto que exagere sua capacidade real.",
            "Informe horas remuneradas realistas; o modo mensal não consegue deduzir trabalho não pago.",
            "Trate o resultado como uma perspectiva, não como orientação financeira ou julgamento moral.",
        ),
        "scope_title": "O que esta calculadora gratuita não faz",
        "scope_text": "Ela não se conecta ao banco, não memoriza sua renda, não salva compras, não acompanha categorias, não movimenta dinheiro, não bloqueia o pagamento nem prevê economia. Recarregar ou fechar a página apaga o exemplo atual.",
        "app_title": "Quer ter esta pausa antes de cada compra?",
        "app_text": "A página gratuita calcula um exemplo temporário. A ficha atual da App Store informa que o HoursTag permite configurar a renda uma vez no aparelho, converter preços em tempo de trabalho, marcar Necessidade, Desejo ou Impulso, acompanhar metas e uma lista de desejos, ver análises mensais por categoria e fazer backup e restauração. Também informa que não há conta, rastreamento ou anúncios e que é uma compra única, sem assinatura ou upgrades ocultos. Confira a ficha atual antes de comprar.",
        "app_cta": "Ver o HoursTag na App Store",
        "sources_title": "Fonte atual do produto e especificação da ferramenta de IA",
        "app_source": "Ficha do HoursTag na App Store dos EUA",
        "webmcp_source": "Prévia da API imperativa Chrome WebMCP",
        "webmcp_description": "Calcula o custo de uma compra em tempo de trabalho a partir de renda líquida e preço inseridos dentro de limites definidos. Retorna fórmulas, premissas e uma pergunta de reflexão sem armazenar dados, acessar contas, recomendar a compra ou prometer economia.",
        "faq_title": "Perguntas sobre custo em horas de trabalho",
        "faq": (
            ("Devo usar renda bruta ou líquida?", "Use a renda líquida para se aproximar do dinheiro realmente disponível. Ajuste por conta própria os custos que a calculadora não conhece."),
            ("Por que o modo mensal pede horas remuneradas?", "Uma renda mensal só ganha valor por hora quando é dividida por um número realista de horas remuneradas."),
            ("Um custo alto em tempo significa que não devo comprar?", "Não. O número mostra apenas uma troca; urgência, satisfação, durabilidade, alternativas e suas finanças como um todo também importam."),
            ("A página salva meu salário ou minha compra?", "Não. O cálculo fica somente na página atual e não é enviado nem armazenado."),
        ),
        "footer": "Apenas cálculo local e privado · sem acesso a contas ou bancos · não é orientação financeira",
        "index_title": "Calculadora de horas de trabalho para comprar",
        "index_description": "Converta um preço em horas, dias de trabalho e esforço de economia com uma fórmula privada e transparente.",
    },
    "vi": {
        "title": "Máy tính giờ làm việc | Công cụ đổi giá thành thời gian riêng tư",
        "description": "Đổi một mức giá thành giờ làm, ngày công và nỗ lực tiết kiệm bằng phép tính cục bộ minh bạch. Không tài khoản, không tải lên, không lưu trữ, không tư vấn tài chính.",
        "tools": "Công cụ miễn phí",
        "switch": "English",
        "eyebrow": "Máy tính riêng tư · phép tính minh bạch · AI gọi được",
        "heading": "Món đồ này tốn bao nhiêu giờ cuộc đời bạn?",
        "lead": "Dùng thu nhập thực nhận của chính bạn để đổi giá thành thời gian làm việc trước khi thanh toán. Kết quả chỉ tạo một khoảng dừng; nó không bao giờ quyết định bạn có nên mua hay không.",
        "badges": ("Chỉ chạy trong trình duyệt này", "Không tài khoản hay kết nối ngân hàng", "Không lưu lương hay giao dịch", "Không hứa hẹn mua sắm hay tiết kiệm"),
        "calculator": "Tính một ví dụ trung thực",
        "calculator_intro": "Chọn thu nhập thực nhận theo giờ hoặc theo tháng. Chế độ tháng chia thu nhập cho số giờ được trả lương bạn nhập; chế độ giờ bỏ qua ô đó.",
        "income_mode": "Định dạng thu nhập",
        "income_modes": {"hourly": "Thực nhận mỗi giờ", "monthly": "Thực nhận mỗi tháng"},
        "income": "Thu nhập thực nhận theo tiền tệ của bạn",
        "monthly_hours": "Số giờ làm được trả lương mỗi tháng",
        "price": "Giá món hàng trước thuế",
        "tax": "Phần trăm thuế bán hàng hoặc VAT",
        "workday": "Số giờ trong một ngày công",
        "saving_rate": "Phần trăm thu nhập thực nhận để dành",
        "decision_tag": "Ngay lúc này bạn gắn nhãn nó thế nào?",
        "decision_tags": {"need": "Cần", "want": "Muốn", "impulse": "Bốc đồng"},
        "update": "Hiện chi phí thời gian",
        "effective_hourly": "Thực nhận hiệu dụng mỗi giờ",
        "total_price": "Giá gồm thuế đã nhập",
        "work_hours": "Giờ làm việc",
        "workdays": "Ngày công",
        "workday_percent": "Phần trăm của một ngày công",
        "saving_hours": "Số giờ kiếm tiền theo tỷ lệ tiết kiệm của bạn",
        "saving_zero": "Đặt tỷ lệ tiết kiệm trên 0% để tính",
        "validation_error": "Nhập thu nhập và số giờ làm hợp lệ, lớn hơn 0.",
        "decision_prompt": {
            "need": "Cần: so chi phí thời gian với mức cấp bách, lựa chọn thay thế sẵn có và hậu quả của việc chờ đợi.",
            "want": "Muốn: sau một khoảng thời gian nguội lại, hãy quyết định liệu nó có xứng với thời gian làm việc hiển thị không.",
            "impulse": "Bốc đồng: rời trang thanh toán, lưu món đồ ở nơi khác và xem lại cùng chi phí thời gian sau khi cảm xúc lắng xuống.",
        },
        "math_boundary": "Công thức: giá gồm thuế đã nhập ÷ giá trị thực nhận hiệu dụng mỗi giờ. Nó không tính thuế, phúc lợi, đi lại, việc không lương hay chi phí chăm sóc nào chưa nằm trong số liệu bạn nhập.",
        "method_title": "Ba kiểm tra trước khi coi kết quả là hữu ích",
        "method_steps": (
            "Dùng thu nhập thực nhận thay vì con số gộp bị thổi phồng.",
            "Nhập số giờ được trả lương thực tế; chế độ tháng không thể suy ra việc không lương.",
            "Coi kết quả là một lăng kính quyết định, không phải tư vấn tài chính hay điểm đạo đức.",
        ),
        "scope_title": "Điều máy tính miễn phí này không làm",
        "scope_text": "Nó không kết nối ngân hàng, không nhớ thu nhập, không lưu giao dịch, không theo dõi danh mục, không chuyển tiền, không chặn thanh toán, không dự đoán tiết kiệm. Làm mới hoặc đóng trang sẽ xóa ví dụ hiện tại.",
        "app_title": "Muốn khoảng dừng này cho mọi lần mua sắm?",
        "app_text": "Trang miễn phí chỉ xử lý một ví dụ tạm thời. Trang App Store hiện tại của HoursTag mô tả quy trình trên thiết bị: đặt thu nhập một lần, đổi giá thành thời gian làm việc, gắn nhãn Cần/Muốn/Bốc đồng, theo dõi mục tiêu và wishlist, xem thống kê danh mục hằng tháng, hỗ trợ sao lưu và khôi phục. Trang cũng ghi không tài khoản, không theo dõi hay quảng cáo, trả phí một lần, không đăng ký hay nâng cấp ẩn. Hãy kiểm tra trang hiện tại trước khi mua.",
        "app_cta": "Xem HoursTag trên App Store",
        "sources_title": "Nguồn sản phẩm hiện tại và đặc tả công cụ AI",
        "app_source": "Trang HoursTag trên App Store Hoa Kỳ",
        "webmcp_source": "Bản xem trước API mệnh lệnh Chrome WebMCP",
        "webmcp_description": "Tính chi phí thời gian làm việc của một lần mua từ thu nhập thực nhận và giá tự nhập có giới hạn. Trả về công thức, giả định minh bạch và một gợi ý quyết định, không lưu dữ liệu, không truy cập tài khoản, không khuyên mua, không hứa tiết kiệm.",
        "faq_title": "Câu hỏi về tính thời gian làm việc",
        "faq": (
            ("Nên dùng thu nhập gộp hay thực nhận?", "Dùng thực nhận để kết quả gần với số tiền bạn thật sự tiêu được. Tự điều chỉnh cho các chi phí máy tính không thể biết."),
            ("Vì sao chế độ tháng hỏi số giờ được trả lương?", "Thu nhập tháng không có nghĩa theo giờ cho đến khi chia cho số giờ làm được trả lương thực tế."),
            ("Chi phí thời gian cao nghĩa là không nên mua?", "Không. Con số chỉ làm rõ một sự đánh đổi; mức cấp bách, niềm vui, độ bền, lựa chọn thay thế và tài chính tổng thể vẫn quan trọng."),
            ("Trang này có lưu lương hay giao dịch của tôi không?", "Không. Phép tính chỉ nằm trong trang hiện tại, không tải lên hay lưu trữ."),
        ),
        "footer": "Chỉ tính cục bộ riêng tư · không truy cập tài khoản hay ngân hàng · không phải tư vấn tài chính",
        "index_title": "Máy tính đổi giá thành giờ làm việc",
        "index_description": "Đổi một mức giá thành giờ làm, ngày công và nỗ lực tiết kiệm bằng phép tính riêng tư, minh bạch.",
    },
    "th": {
        "title": "เครื่องคิดชั่วโมงทำงาน | เครื่องมือแปลงราคาเป็นเวลาแบบส่วนตัว",
        "description": "แปลงราคาเป็นชั่วโมงทำงาน วันทำงาน และความพยายามออมด้วยคณิตในเครื่องที่โปร่งใส ไม่มีบัญชี ไม่อัปโหลด ไม่เก็บข้อมูล ไม่ใช่คำแนะนำการเงิน",
        "tools": "เครื่องมือฟรี",
        "switch": "English",
        "eyebrow": "เครื่องคิดส่วนตัว · คณิตโปร่งใส · AI เรียกใช้ได้",
        "heading": "ของชิ้นนี้แลกกับกี่ชั่วโมงของชีวิตคุณ?",
        "lead": "ใช้รายได้สุทธิของคุณเองแปลงราคาเป็นเวลาทำงานก่อนจ่ายเงิน ผลลัพธ์แค่ชวนให้หยุดคิด ไม่เคยตัดสินแทนว่าคุณควรซื้อหรือไม่",
        "badges": ("ทำงานในเบราว์เซอร์นี้เท่านั้น", "ไม่มีบัญชีหรือเชื่อมธนาคาร", "ไม่บันทึกค่าจ้างหรือการซื้อ", "ไม่สัญญาเรื่องการซื้อหรือการออม"),
        "calculator": "คำนวณตัวอย่างจริงหนึ่งรายการ",
        "calculator_intro": "เลือกรายได้สุทธิแบบรายชั่วโมงหรือรายเดือน โหมดรายเดือนหารรายได้ด้วยชั่วโมงที่ได้ค่าจ้างที่คุณกรอก โหมดรายชั่วโมงไม่ใช้ช่องนั้น",
        "income_mode": "รูปแบบรายได้",
        "income_modes": {"hourly": "รายได้สุทธิต่อชั่วโมง", "monthly": "รายได้สุทธิต่อเดือน"},
        "income": "รายได้สุทธิในสกุลเงินของคุณ",
        "monthly_hours": "ชั่วโมงทำงานที่ได้ค่าจ้างต่อเดือน",
        "price": "ราคาสินค้าก่อนภาษี",
        "tax": "เปอร์เซ็นต์ภาษีขายหรือ VAT",
        "workday": "ชั่วโมงในหนึ่งวันทำงาน",
        "saving_rate": "เปอร์เซ็นต์รายได้สุทธิที่กันไว้ออม",
        "decision_tag": "ตอนนี้คุณติดป้ายมันว่าอะไร?",
        "decision_tags": {"need": "จำเป็น", "want": "อยากได้", "impulse": "วูบซื้อ"},
        "update": "แสดงต้นทุนเวลา",
        "effective_hourly": "รายได้สุทธิต่อชั่วโมงที่แท้จริง",
        "total_price": "ราคารวมภาษีที่กรอก",
        "work_hours": "ชั่วโมงทำงาน",
        "workdays": "วันทำงาน",
        "workday_percent": "เปอร์เซ็นต์ของหนึ่งวันทำงาน",
        "saving_hours": "ชั่วโมงหาเงินตามอัตราออมของคุณ",
        "saving_zero": "ตั้งอัตราออมมากกว่า 0% เพื่อคำนวณ",
        "validation_error": "กรอกรายได้และชั่วโมงทำงานที่ถูกต้องและมากกว่าศูนย์",
        "decision_prompt": {
            "need": "จำเป็น: เทียบต้นทุนเวลากับความเร่งด่วน ทางเลือกที่มี และผลของการรอ",
            "want": "อยากได้: หลังช่วงพักใจ ตัดสินว่ามันคุ้มกับเวลาทำงานที่แสดงหรือไม่",
            "impulse": "วูบซื้อ: ออกจากหน้าชำระเงิน เก็บสินค้าไว้ที่อื่น แล้วดูต้นทุนเวลาเดิมอีกครั้งเมื่ออารมณ์ผ่านไป",
        },
        "math_boundary": "สูตร: ราคารวมภาษีที่กรอก ÷ รายได้สุทธิต่อชั่วโมงที่แท้จริง ไม่รวมภาษี สวัสดิการ การเดินทาง งานไม่ได้ค่าจ้าง หรือค่าดูแลที่ไม่ได้อยู่ในตัวเลขที่คุณกรอก",
        "method_title": "สามข้อตรวจก่อนถือว่าผลลัพธ์มีประโยชน์",
        "method_steps": (
            "ใช้รายได้สุทธิ ไม่ใช่ตัวเลขก่อนหักที่ดูเกินจริง",
            "กรอกชั่วโมงที่ได้ค่าจ้างตามจริง โหมดรายเดือนคาดเดางานไม่ได้ค่าจ้างไม่ได้",
            "ถือผลลัพธ์เป็นมุมมองหนึ่งของการตัดสินใจ ไม่ใช่คำแนะนำการเงินหรือคะแนนศีลธรรม",
        ),
        "scope_title": "สิ่งที่เครื่องคิดฟรีนี้ไม่ทำ",
        "scope_text": "มันไม่เชื่อมธนาคาร ไม่จำรายได้ ไม่บันทึกการซื้อ ไม่ติดตามหมวดหมู่ ไม่โอนเงิน ไม่บล็อกการชำระ ไม่ทำนายการออม รีเฟรชหรือปิดหน้าแล้วตัวอย่างปัจจุบันจะหายไป",
        "app_title": "อยากมีจังหวะหยุดคิดแบบนี้ทุกการซื้อไหม?",
        "app_text": "หน้าเว็บฟรีรองรับตัวอย่างชั่วคราวทีละหนึ่ง หน้า App Store ปัจจุบันของ HoursTag อธิบายเวิร์กโฟลว์บนอุปกรณ์: ตั้งรายได้ครั้งเดียว แปลงราคาเป็นเวลาทำงาน ติดป้าย จำเป็น/อยากได้/วูบซื้อ ติดตามเป้าหมายและ wishlist ดูสถิติหมวดหมู่รายเดือน และรองรับสำรอง/กู้คืนข้อมูล หน้ายังระบุว่าไม่มีบัญชี การติดตาม หรือโฆษณา จ่ายครั้งเดียว ไม่มีสมัครสมาชิกหรืออัปเกรดแอบแฝง โปรดตรวจหน้าปัจจุบันก่อนซื้อ",
        "app_cta": "ดู HoursTag บน App Store",
        "sources_title": "แหล่งข้อมูลผลิตภัณฑ์ปัจจุบันและสเปกเครื่องมือ AI",
        "app_source": "หน้า HoursTag บน App Store สหรัฐฯ",
        "webmcp_source": "ตัวอย่าง API เชิงคำสั่ง Chrome WebMCP",
        "webmcp_description": "คำนวณต้นทุนเวลาทำงานของการซื้อจากรายได้สุทธิและราคาที่กรอกเองแบบมีขอบเขต คืนสูตร สมมติฐานโปร่งใส และคำถามชวนตัดสินใจ โดยไม่เก็บข้อมูล ไม่เข้าถึงบัญชี ไม่แนะนำให้ซื้อ ไม่สัญญาการออม",
        "faq_title": "คำถามเรื่องการคิดเวลาทำงาน",
        "faq": (
            ("ควรใช้รายได้ก่อนหักหรือสุทธิ?", "ใช้รายได้สุทธิเพื่อให้ใกล้เงินที่ใช้ได้จริง ปรับเองสำหรับต้นทุนที่เครื่องคิดไม่มีทางรู้"),
            ("ทำไมโหมดรายเดือนถามชั่วโมงที่ได้ค่าจ้าง?", "รายได้รายเดือนไม่มีความหมายต่อชั่วโมงจนกว่าจะหารด้วยชั่วโมงทำงานที่ได้ค่าจ้างตามจริง"),
            ("ต้นทุนเวลาสูงแปลว่าไม่ควรซื้อไหม?", "ไม่ ตัวเลขแค่ทำให้เห็นการแลกเปลี่ยนหนึ่งมุม ความเร่งด่วน ความสุข ความทนทาน ทางเลือก และการเงินโดยรวมยังสำคัญ"),
            ("หน้านี้บันทึกค่าจ้างหรือการซื้อของฉันไหม?", "ไม่ การคำนวณอยู่แค่ในหน้าปัจจุบัน ไม่ถูกอัปโหลดหรือจัดเก็บ"),
        ),
        "footer": "คณิตในเครื่องแบบส่วนตัวเท่านั้น · ไม่เข้าถึงบัญชีหรือธนาคาร · ไม่ใช่คำแนะนำการเงิน",
        "index_title": "เครื่องคิดกี่ชั่วโมงทำงานถึงซื้อได้",
        "index_description": "แปลงราคาเป็นชั่วโมงทำงาน วันทำงาน และความพยายามออม ด้วยคณิตส่วนตัวที่โปร่งใส",
    },
    "id": {
        "title": "Kalkulator Jam Kerja | Alat Privat Harga-ke-Waktu",
        "description": "Ubah harga menjadi jam kerja, hari kerja, dan upaya menabung dengan matematika lokal yang transparan. Tanpa akun, unggahan, penyimpanan, atau nasihat keuangan.",
        "tools": "Alat gratis",
        "switch": "English",
        "eyebrow": "Kalkulator privat · matematika transparan · dapat dipanggil AI",
        "heading": "Berapa jam hidup Anda harga pembelian ini?",
        "lead": "Gunakan penghasilan bersih Anda sendiri untuk mengubah harga menjadi waktu kerja sebelum membayar. Hasilnya hanya memberi jeda; ia tidak pernah memutuskan apakah Anda harus membeli.",
        "badges": ("Berjalan hanya di peramban ini", "Tanpa akun atau koneksi bank", "Tanpa menyimpan gaji atau pembelian", "Tanpa janji pembelian atau tabungan"),
        "calculator": "Hitung satu contoh yang jujur",
        "calculator_intro": "Pilih penghasilan bersih per jam atau per bulan. Mode bulanan membagi penghasilan dengan jam berbayar yang Anda masukkan; mode per jam mengabaikan kolom itu.",
        "income_mode": "Format penghasilan",
        "income_modes": {"hourly": "Bersih per jam", "monthly": "Bersih per bulan"},
        "income": "Penghasilan bersih dalam mata uang Anda",
        "monthly_hours": "Jam kerja berbayar per bulan",
        "price": "Harga barang sebelum pajak",
        "tax": "Persen pajak penjualan atau PPN",
        "workday": "Jam dalam satu hari kerja",
        "saving_rate": "Persen penghasilan bersih yang disisihkan",
        "decision_tag": "Bagaimana Anda melabelinya sekarang?",
        "decision_tags": {"need": "Butuh", "want": "Ingin", "impulse": "Impulsif"},
        "update": "Tampilkan biaya waktu",
        "effective_hourly": "Bersih efektif per jam",
        "total_price": "Harga termasuk pajak yang dimasukkan",
        "work_hours": "Jam kerja",
        "workdays": "Hari kerja",
        "workday_percent": "Persen dari satu hari kerja",
        "saving_hours": "Jam mencari uang pada tingkat menabung Anda",
        "saving_zero": "Atur tingkat menabung di atas 0% untuk menghitung",
        "validation_error": "Masukkan nilai penghasilan dan jam kerja yang valid dan positif.",
        "decision_prompt": {
            "need": "Butuh: bandingkan biaya waktu dengan urgensi, alternatif yang ada, dan konsekuensi menunggu.",
            "want": "Ingin: setelah masa jeda, putuskan apakah ini sepadan dengan waktu kerja yang ditampilkan.",
            "impulse": "Impulsif: tinggalkan halaman pembayaran, simpan barang di tempat lain, dan tinjau biaya waktu yang sama setelah puncak emosi lewat.",
        },
        "math_boundary": "Rumus: harga dengan pajak yang dimasukkan ÷ nilai bersih efektif per jam. Tidak mencakup pajak, tunjangan, perjalanan, kerja tak berbayar, atau biaya perawatan yang belum tercermin di angka yang Anda masukkan.",
        "method_title": "Tiga pemeriksaan sebelum menganggap hasilnya berguna",
        "method_steps": (
            "Gunakan penghasilan bersih, bukan angka kotor yang membengkak.",
            "Masukkan jam berbayar yang realistis; mode bulanan tidak bisa menebak kerja tak berbayar.",
            "Anggap hasilnya satu lensa keputusan, bukan nasihat keuangan atau skor moral.",
        ),
        "scope_title": "Yang tidak dilakukan kalkulator gratis ini",
        "scope_text": "Ia tidak terhubung ke bank, tidak mengingat penghasilan, tidak menyimpan pembelian, tidak melacak kategori, tidak memindahkan uang, tidak memblokir pembayaran, dan tidak memprediksi tabungan. Menyegarkan atau menutup halaman menghapus contoh saat ini.",
        "app_title": "Ingin jeda ini tersedia untuk setiap pembelian?",
        "app_text": "Halaman gratis menangani satu contoh sementara. Halaman App Store HoursTag saat ini menjelaskan alur di perangkat: atur penghasilan sekali, ubah harga menjadi waktu kerja, beri label Butuh/Ingin/Impulsif, lacak tujuan dan wishlist, lihat wawasan kategori bulanan, serta dukung cadangan dan pemulihan. Halaman itu juga menyebut tanpa akun, pelacakan, atau iklan, sekali bayar, tanpa langganan atau peningkatan tersembunyi. Periksa halaman terbaru sebelum membeli.",
        "app_cta": "Lihat HoursTag di App Store",
        "sources_title": "Sumber produk terkini dan spesifikasi alat AI",
        "app_source": "Halaman HoursTag di App Store AS",
        "webmcp_source": "Pratinjau API imperatif Chrome WebMCP",
        "webmcp_description": "Hitung biaya waktu kerja sebuah pembelian dari penghasilan bersih dan data harga yang dimasukkan sendiri secara terbatas. Kembalikan rumus, asumsi transparan, dan ajakan keputusan tanpa menyimpan data, mengakses akun, merekomendasikan pembelian, atau menjanjikan tabungan.",
        "faq_title": "Pertanyaan perhitungan waktu kerja",
        "faq": (
            ("Pakai penghasilan kotor atau bersih?", "Pakai penghasilan bersih agar hasil lebih dekat dengan uang yang benar-benar bisa dibelanjakan. Sesuaikan sendiri untuk biaya yang tidak diketahui kalkulator."),
            ("Mengapa mode bulanan menanyakan jam berbayar?", "Penghasilan bulanan tidak punya makna per jam sampai dibagi jumlah jam kerja berbayar yang realistis."),
            ("Apakah biaya waktu tinggi berarti tidak boleh beli?", "Tidak. Angka itu hanya menampakkan satu pertukaran; urgensi, kegembiraan, keawetan, alternatif, dan keuangan Anda secara luas tetap penting."),
            ("Apakah halaman ini menyimpan gaji atau pembelian saya?", "Tidak. Perhitungan tetap di halaman saat ini dan tidak diunggah atau disimpan."),
        ),
        "footer": "Hanya matematika lokal privat · tanpa akses akun atau bank · bukan nasihat keuangan",
        "index_title": "Kalkulator Jam Kerja untuk Membeli",
        "index_description": "Ubah harga menjadi jam kerja, hari kerja, dan upaya menabung dengan matematika privat yang transparan.",
    },
    "tr": {
        "title": "Çalışma Saati Hesaplayıcı | Gizli Fiyat-Zaman Aracı",
        "description": "Bir fiyatı şeffaf yerel matematikle çalışma saatine, iş gününe ve birikim çabasına çevirin. Hesap, yükleme, depolama veya finansal tavsiye yok.",
        "tools": "Ücretsiz araçlar",
        "switch": "English",
        "eyebrow": "Gizli hesaplayıcı · şeffaf matematik · AI çağırabilir",
        "heading": "Bu alışveriş hayatınızın kaç saatine mal oluyor?",
        "lead": "Ödemeden önce fiyatı kendi elinize geçen gelirinizle çalışma zamanına çevirin. Sonuç yalnızca bir duraklama sağlar; almanız gerekip gerekmediğine asla karar vermez.",
        "badges": ("Yalnızca bu tarayıcıda çalışır", "Hesap veya banka bağlantısı yok", "Ücret veya alışveriş kaydı yok", "Alışveriş veya birikim vaadi yok"),
        "calculator": "Dürüst bir örnek hesaplayın",
        "calculator_intro": "Saatlik veya aylık ele geçen geliri seçin. Aylık mod geliri girdiğiniz ücretli saatlere böler; saatlik mod o alanı yok sayar.",
        "income_mode": "Gelir biçimi",
        "income_modes": {"hourly": "Saat başına ele geçen", "monthly": "Ay başına ele geçen"},
        "income": "Para biriminizde ele geçen gelir",
        "monthly_hours": "Aylık ücretli çalışma saati",
        "price": "Vergi öncesi ürün fiyatı",
        "tax": "Satış vergisi veya KDV yüzdesi",
        "workday": "Bir iş günündeki saat",
        "saving_rate": "Kenara ayrılan ele geçen gelir yüzdesi",
        "decision_tag": "Şu anda nasıl etiketlerdiniz?",
        "decision_tags": {"need": "İhtiyaç", "want": "İstek", "impulse": "Anlık"},
        "update": "Zaman maliyetini göster",
        "effective_hourly": "Saat başına efektif ele geçen",
        "total_price": "Girilen vergi dahil fiyat",
        "work_hours": "Çalışma saati",
        "workdays": "İş günü",
        "workday_percent": "Bir iş gününün yüzdesi",
        "saving_hours": "Birikim oranınızda kazanma saati",
        "saving_zero": "Hesaplamak için birikim oranını %0'ın üzerine ayarlayın",
        "validation_error": "Geçerli, pozitif gelir ve çalışma saati değerleri girin.",
        "decision_prompt": {
            "need": "İhtiyaç: zaman maliyetini aciliyetle, mevcut alternatiflerle ve beklemenin sonucuyla karşılaştırın.",
            "want": "İstek: bir soğuma süresinden sonra bunun gösterilen çalışma süresine değip değmediğine karar verin.",
            "impulse": "Anlık: ödemeden çıkın, ürünü başka yere kaydedin ve duygusal zirve geçtikten sonra aynı zaman maliyetine yeniden bakın.",
        },
        "math_boundary": "Formül: girilen vergi dahil fiyat ÷ saat başına efektif ele geçen değer. Girdiğiniz sayılara yansımayan vergi, yan haklar, ulaşım, ücretsiz iş veya bakım maliyetlerini içermez.",
        "method_title": "Sonucu yararlı saymadan önce üç kontrol",
        "method_steps": (
            "Şişirilmiş brüt rakam yerine ele geçen geliri kullanın.",
            "Gerçekçi ücretli saatler girin; aylık mod ücretsiz işi çıkaramaz.",
            "Sonucu tek bir karar merceği sayın; finansal tavsiye veya ahlaki puan değil.",
        ),
        "scope_title": "Bu ücretsiz hesaplayıcının yapmadıkları",
        "scope_text": "Bankaya bağlanmaz, gelirinizi hatırlamaz, alışveriş kaydetmez, kategori takip etmez, para taşımaz, ödemeyi engellemez, birikim tahmini yapmaz. Sayfayı yenilemek veya kapatmak geçerli örneği siler.",
        "app_title": "Bu duraklamayı her alışverişte ister misiniz?",
        "app_text": "Ücretsiz sayfa tek geçici örnekle çalışır. HoursTag'in güncel App Store sayfası cihaz üzerinde bir akış anlatır: geliri bir kez ayarlayın, fiyatları çalışma zamanına çevirin, İhtiyaç/İstek/Anlık etiketleyin, hedefleri ve istek listesini takip edin, aylık kategori içgörülerini görün, yedekleme ve geri yüklemeyi kullanın. Sayfa ayrıca hesap, takip veya reklam olmadığını, tek seferlik ücretli indirme olduğunu, abonelik veya gizli yükseltme bulunmadığını belirtir. Satın almadan önce güncel sayfayı kontrol edin.",
        "app_cta": "App Store'da HoursTag'i görüntüle",
        "sources_title": "Güncel ürün kaynağı ve AI araç şartnamesi",
        "app_source": "HoursTag ABD App Store sayfası",
        "webmcp_source": "Chrome WebMCP buyruk API önizlemesi",
        "webmcp_description": "Sınırlı, kendi girilen ele geçen gelir ve fiyat verisinden bir alışverişin çalışma zamanı maliyetini hesaplar. Veri saklamadan, hesaplara erişmeden, satın alma önermeden veya birikim vaat etmeden şeffaf formüller, varsayımlar ve bir karar sorusu döndürür.",
        "faq_title": "Çalışma zamanı hesaplama soruları",
        "faq": (
            ("Brüt mü, ele geçen gelir mi kullanmalıyım?", "Gerçekten harcayabileceğiniz paraya yakın sonuç için ele geçen geliri kullanın. Hesaplayıcının bilemeyeceği maliyetler için kendiniz ayarlayın."),
            ("Aylık mod neden ücretli saatleri soruyor?", "Aylık gelir, gerçekçi ücretli çalışma saatine bölünene kadar saatlik bir anlam taşımaz."),
            ("Yüksek zaman maliyeti almamalıyım mı demek?", "Hayır. Sayı yalnızca bir dengeyi görünür kılar; aciliyet, keyif, dayanıklılık, alternatifler ve genel finansal durumunuz hâlâ önemlidir."),
            ("Bu sayfa ücretimi veya alışverişimi kaydediyor mu?", "Hayır. Hesaplama yalnızca geçerli sayfada kalır; yüklenmez veya saklanmaz."),
        ),
        "footer": "Yalnızca gizli yerel matematik · hesap veya banka erişimi yok · finansal tavsiye değildir",
        "index_title": "Satın Almak İçin Çalışma Saati Hesaplayıcı",
        "index_description": "Bir fiyatı gizli, şeffaf matematikle çalışma saatine, iş gününe ve birikim çabasına çevirin.",
    },
}

STYLE = r"""
:root{--ink:#17231d;--muted:#667269;--line:#dce5de;--paper:#fff;--bg:#f2f7f3;--forest:#244f3b;--mint:#7bb695;--soft:#e8f4ed;--gold:#f5ead0;--shadow:0 22px 60px rgba(26,67,46,.12)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 90% 0,#fff 0,var(--bg) 55%,#e5efe8 100%);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang TC","Noto Sans TC",sans-serif;line-height:1.62}
a{color:#286344}.wrap{width:min(1120px,calc(100% - 30px));margin:auto}.top{position:sticky;top:0;z-index:8;background:#fffffff2;border-bottom:1px solid var(--line);backdrop-filter:blur(14px)}.nav{min-height:62px;display:flex;align-items:center;justify-content:space-between;gap:16px}.nav a{text-decoration:none;font-weight:850;white-space:nowrap}.links{display:flex;gap:15px;overflow-x:auto}
.hero{padding:64px 0 30px}.eyebrow,.badge{display:inline-flex;border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 12px;font-size:13px;font-weight:850;color:var(--forest);white-space:nowrap}.hero h1,h2{font-family:ui-serif,Georgia,"Noto Serif TC",serif}.hero h1{font-size:clamp(34px,6vw,62px);line-height:1.04;letter-spacing:-.035em;margin:.3em 0 .22em;white-space:nowrap;overflow-x:auto}.lead{font-size:clamp(17px,2.2vw,21px);color:var(--muted);margin:0;white-space:nowrap;overflow-x:auto}.badges{display:flex;gap:8px;flex-wrap:wrap;margin-top:22px}
.calculator,.card,.app-card{background:rgba(255,255,255,.97);border:1px solid var(--line);border-radius:26px;box-shadow:var(--shadow)}.calculator{padding:clamp(20px,4vw,36px);margin:16px auto 30px}.calculator h2,.card h2,.app-card h2{font-size:clamp(24px,3.6vw,34px);line-height:1.14;margin:0;white-space:nowrap;overflow-x:auto}.intro{color:var(--muted);white-space:nowrap;overflow-x:auto}
.controls{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:22px}.field{min-width:0}.field label{display:block;font-size:13px;font-weight:850;color:var(--forest);margin-bottom:6px;white-space:nowrap;overflow-x:auto}select,input,button{font:inherit}select,input[type=number]{width:100%;min-height:46px;border:1px solid #cbd9cf;border-radius:13px;background:#fff;color:var(--ink);padding:9px 11px}.button{border:0;border-radius:999px;background:linear-gradient(135deg,var(--forest),#4d8b68);color:#fff!important;text-decoration:none;font-weight:850;padding:12px 18px;cursor:pointer;white-space:nowrap;box-shadow:0 9px 22px rgba(36,79,59,.2)}
.results{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:11px;margin-top:22px}.result{background:var(--soft);border:1px solid #cbe0d2;border-radius:17px;padding:14px;min-width:0}.result strong,.result span{display:block;white-space:nowrap;overflow-x:auto}.result strong{font-size:12px;color:#426852;text-transform:uppercase;letter-spacing:.04em}.result span{font-size:17px;color:#234c38;font-weight:820;margin-top:5px}.note{background:var(--gold);border:1px solid #e8d5a6;border-radius:16px;padding:13px 15px;margin:14px 0 0;white-space:nowrap;overflow-x:auto}.decision{background:#edf6ff;border:1px solid #cddff0}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:30px}.card,.app-card{padding:clamp(20px,3.5vw,30px)}.card p,.card li,.app-card p,.faq details p,.faq summary{white-space:nowrap;overflow-x:auto}.card ol{padding-left:22px}.card li{margin:8px 0}.source-list a{overflow-wrap:anywhere}.app-card{margin:0 auto 38px;background:linear-gradient(135deg,#fbfffc,#e5f3e9)}.app-card .button{display:inline-flex;margin-top:5px}.faq{margin-bottom:30px}.faq details{border:1px solid var(--line);border-radius:15px;background:#fff;padding:11px 14px;margin-top:9px}.faq summary{font-weight:830;cursor:pointer}.faq details p{color:var(--muted)}
.footer{background:var(--forest);color:#eff8f2;text-align:center;padding:27px 0;white-space:nowrap;overflow-x:auto}
@media(max-width:960px){.controls{grid-template-columns:repeat(2,minmax(0,1fr))}.results{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:560px){.controls,.results,.grid{grid-template-columns:1fr}.wrap{width:min(100% - 22px,1120px)}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important}}
"""

SCRIPT = r"""
(() => {
  const config = JSON.parse(document.getElementById("hours-config").textContent);
  const form = document.getElementById("hours-calculator");
  const fields = {
    income_mode: document.getElementById("income-mode"),
    take_home_income: document.getElementById("take-home-income"),
    paid_hours_per_month: document.getElementById("paid-hours-month"),
    purchase_price: document.getElementById("purchase-price"),
    tax_percent: document.getElementById("tax-percent"),
    workday_hours: document.getElementById("workday-hours"),
    saving_rate_percent: document.getElementById("saving-rate"),
    decision_tag: document.getElementById("decision-tag")
  };
  const output = {
    hourly: document.getElementById("result-hourly"),
    total: document.getElementById("result-total"),
    hours: document.getElementById("result-hours"),
    days: document.getElementById("result-days"),
    workday: document.getElementById("result-workday"),
    saving: document.getElementById("result-saving"),
    decision: document.getElementById("result-decision")
  };

  function round(value, digits = 2) {
    const factor = 10 ** digits;
    return Math.round((value + Number.EPSILON) * factor) / factor;
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

  function numberValue(input, name) {
    if (!Object.prototype.hasOwnProperty.call(input, name)) {
      throw new TypeError(`${name} is required.`);
    }
    const value = input[name];
    const schema = config.inputSchema.properties[name];
    if (typeof value !== "number" || !Number.isFinite(value)) {
      throw new TypeError(`${name} must be a finite number.`);
    }
    if ((schema.minimum !== undefined && value < schema.minimum) ||
        (schema.exclusiveMinimum !== undefined && value <= schema.exclusiveMinimum) ||
        (schema.maximum !== undefined && value > schema.maximum)) {
      throw new RangeError(`${name} is outside the supported range.`);
    }
    return value;
  }

  function calculate(input) {
    if (input === null || typeof input !== "object" || Array.isArray(input)) {
      throw new TypeError("WebMCP input must be an object.");
    }
    const allowed = new Set(Object.keys(config.inputSchema.properties));
    for (const name of Object.keys(input)) {
      if (!allowed.has(name)) {
        throw new RangeError(`${name} is not a supported input.`);
      }
    }
    const incomeMode = enumValue(input, "income_mode");
    const takeHomeIncome = numberValue(input, "take_home_income");
    const paidHours = numberValue(input, "paid_hours_per_month");
    const purchasePrice = numberValue(input, "purchase_price");
    const taxPercent = numberValue(input, "tax_percent");
    const workdayHours = numberValue(input, "workday_hours");
    const savingRate = numberValue(input, "saving_rate_percent");
    const decisionTag = enumValue(input, "decision_tag");
    const effectiveHourly = incomeMode === "hourly"
      ? takeHomeIncome
      : takeHomeIncome / paidHours;
    const totalPrice = purchasePrice * (1 + taxPercent / 100);
    const workHours = totalPrice / effectiveHourly;
    const savingHours = savingRate > 0
      ? workHours / (savingRate / 100)
      : null;
    return {
      selected_inputs: {
        income_mode: incomeMode,
        take_home_income: takeHomeIncome,
        paid_hours_per_month: incomeMode === "monthly" ? paidHours : null,
        purchase_price: purchasePrice,
        tax_percent: taxPercent,
        workday_hours: workdayHours,
        saving_rate_percent: savingRate,
        decision_tag: decisionTag
      },
      calculation: {
        effective_take_home_per_hour: round(effectiveHourly),
        price_including_entered_tax: round(totalPrice),
        work_hours: round(workHours),
        work_minutes: round(workHours * 60),
        workdays: round(workHours / workdayHours),
        percent_of_one_workday: round(workHours / workdayHours * 100),
        earning_hours_at_saving_rate: savingHours === null ? null : round(savingHours)
      },
      formulas: {
        effective_hourly: incomeMode === "hourly"
          ? "take_home_income"
          : "take_home_income / paid_hours_per_month",
        price_with_tax: "purchase_price * (1 + tax_percent / 100)",
        work_hours: "price_with_tax / effective_hourly",
        earning_hours_at_saving_rate:
          "work_hours / (saving_rate_percent / 100), when saving_rate_percent > 0"
      },
      decision_prompt: config.decisionPrompts[decisionTag],
      boundary: config.mathBoundary
    };
  }

  function format(value) {
    return new Intl.NumberFormat(undefined, {
      maximumFractionDigits: 2
    }).format(value);
  }

  function readForm() {
    return {
      income_mode: fields.income_mode.value,
      take_home_income: Number(fields.take_home_income.value),
      paid_hours_per_month: Number(fields.paid_hours_per_month.value),
      purchase_price: Number(fields.purchase_price.value),
      tax_percent: Number(fields.tax_percent.value),
      workday_hours: Number(fields.workday_hours.value),
      saving_rate_percent: Number(fields.saving_rate_percent.value),
      decision_tag: fields.decision_tag.value
    };
  }

  function render() {
    try {
      const result = calculate(readForm());
      output.hourly.textContent = format(result.calculation.effective_take_home_per_hour);
      output.total.textContent = format(result.calculation.price_including_entered_tax);
      output.hours.textContent = format(result.calculation.work_hours);
      output.days.textContent = format(result.calculation.workdays);
      output.workday.textContent = `${format(result.calculation.percent_of_one_workday)}%`;
      output.saving.textContent = result.calculation.earning_hours_at_saving_rate === null
        ? config.savingZero
        : format(result.calculation.earning_hours_at_saving_rate);
      output.decision.textContent = result.decision_prompt;
    } catch (error) {
      if (!(error instanceof TypeError || error instanceof RangeError)) throw error;
      for (const target of Object.values(output)) target.textContent = "—";
      output.decision.textContent = config.validationError;
    }
  }

  async function registerWebMcp() {
    if (!document.modelContext?.registerTool) return;
    await document.modelContext.registerTool({
      name: "calculate_purchase_work_time",
      description: config.toolDescription,
      inputSchema: config.inputSchema,
      annotations: {readOnlyHint: true, untrustedContentHint: false},
      execute: async (input) => {
        const calculation = calculate(input);
        const result = {
          result_type: "private_purchase_work_time_calculation",
          local_only_calculation: true,
          no_account_bank_or_device_access: true,
          no_purchase_recommendation_or_savings_promise: true,
          calculation,
          free_tool: config.freeTool,
          official_source: config.officialSource,
          webmcp_preview_source: config.webmcpSource
        };
        if (config.optionalApp) {
          result.optional_hourstag = config.optionalApp;
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


def webmcp_input_schema() -> dict[str, object]:
    return {
        "type": "object",
        "properties": {
            "income_mode": {
                "type": "string",
                "enum": list(INCOME_MODES),
                "description": "Whether take-home income is entered per hour or per month.",
            },
            "take_home_income": {
                "type": "number",
                "exclusiveMinimum": 0,
                "maximum": 1_000_000_000,
                "description": "Self-entered take-home income in the user's own currency.",
            },
            "paid_hours_per_month": {
                "type": "number",
                "exclusiveMinimum": 0,
                "maximum": 744,
                "description": (
                    "Paid hours per month. Used only in monthly mode; provide a "
                    "realistic positive value in hourly mode as well."
                ),
            },
            "purchase_price": {
                "type": "number",
                "minimum": 0,
                "maximum": 1_000_000_000,
                "description": "Purchase price before the separately entered tax rate.",
            },
            "tax_percent": {
                "type": "number",
                "minimum": 0,
                "maximum": 100,
            },
            "workday_hours": {
                "type": "number",
                "exclusiveMinimum": 0,
                "maximum": 24,
            },
            "saving_rate_percent": {
                "type": "number",
                "minimum": 0,
                "maximum": 100,
            },
            "decision_tag": {
                "type": "string",
                "enum": list(DECISION_TAGS),
            },
        },
        "required": [
            "income_mode",
            "take_home_income",
            "paid_hours_per_month",
            "purchase_price",
            "tax_percent",
            "workday_hours",
            "saving_rate_percent",
            "decision_tag",
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
    badges = "".join(
        f'<span class="badge">{html.escape(item)}</span>' for item in t["badges"]
    )
    steps = "".join(f"<li>{html.escape(item)}</li>" for item in t["method_steps"])
    faq = "".join(
        f"<details><summary>{html.escape(question)}</summary>"
        f"<p>{html.escape(answer)}</p></details>"
        for question, answer in t["faq"]
    )
    tracked_app_url = (
        appstore_url(APP_KEY, f"iag_hours_{locale.lower().replace('-', '_')}")
        if app_public
        else ""
    )
    app_card = ""
    app_schema = ""
    smart_banner = ""
    if tracked_app_url:
        smart_banner = (
            f'<meta name="apple-itunes-app" content="app-id={APP_ID}">'
        )
        app_card = (
            '<section class="app-card wrap"><h2>'
            f'{html.escape(t["app_title"])}</h2><p>{html.escape(t["app_text"])}</p>'
            f'<a class="button" href="{html.escape(tracked_app_url, quote=True)}" '
            f'rel="nofollow noopener">{html.escape(t["app_cta"])}</a></section>'
        )
        app_schema = json_script(
            {
                "@context": "https://schema.org",
                "@type": "MobileApplication",
                "name": "HoursTag: Hours to Buy",
                "operatingSystem": "iOS",
                "applicationCategory": "FinanceApplication",
                "url": appstore_url(APP_KEY),
                "installUrl": appstore_url(APP_KEY),
                "description": t["app_text"],
                "featureList": [
                    "Price-to-work-time conversion",
                    "Need, Want and Impulse tags",
                    "Goals and wishlist with progress",
                    "Monthly category insights",
                    "No account, tracking or ads",
                    "Paid download with no subscription",
                ],
            }
        )
    config = {
        "inputSchema": webmcp_input_schema(),
        "decisionPrompts": t["decision_prompt"],
        "savingZero": t["saving_zero"],
        "validationError": t["validation_error"],
        "mathBoundary": t["math_boundary"],
        "toolDescription": t["webmcp_description"],
        "freeTool": {
            "label": t["heading"],
            "url": url,
            "boundary": t["scope_text"],
        },
        "officialSource": {
            "label": t["app_source"],
            "url": APP_STORE_SOURCE,
        },
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
    web_schema = {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": t["heading"],
        "description": t["description"],
        "url": url,
        "inLanguage": locale,
        "datePublished": CONTENT_DATE,
        "dateModified": CONTENT_DATE,
        "applicationCategory": "FinanceApplication",
        "operatingSystem": "Any",
        "isAccessibleForFree": True,
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        "featureList": [
            "Local price-to-work-time calculation",
            "Hourly and monthly take-home income modes",
            "Entered tax and saving-rate scenarios",
            "Need, Want and Impulse reflection prompt",
            "No account, upload, storage or financial advice",
        ],
        "citation": [APP_STORE_SOURCE, WEBMCP_SOURCE],
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
{smart_banner}
<style>{STYLE}</style>
{json_script(web_schema)}
{json_script(faq_schema)}
{app_schema}
{feed_discovery_links()}
</head>
<body>
<header class="top"><div class="wrap nav"><a href="{home}">iOS App Guide</a><nav class="links"><a href="{tools}">{html.escape(t["tools"])}</a><a href="{alternate}">{html.escape(t["switch"])}</a></nav></div></header>
<main>
<section class="hero wrap"><div class="eyebrow">{html.escape(t["eyebrow"])}</div><h1>{html.escape(t["heading"])}</h1><p class="lead">{html.escape(t["lead"])}</p><div class="badges">{badges}</div></section>
<section class="calculator wrap"><h2>{html.escape(t["calculator"])}</h2><p class="intro">{html.escape(t["calculator_intro"])}</p>
<form id="hours-calculator"><div class="controls">
<div class="field"><label for="income-mode">{html.escape(t["income_mode"])}</label><select id="income-mode">{options(t["income_modes"])}</select></div>
<div class="field"><label for="take-home-income">{html.escape(t["income"])}</label><input id="take-home-income" type="number" min="0.01" max="1000000000" step="0.01" value="25" required></div>
<div class="field"><label for="paid-hours-month">{html.escape(t["monthly_hours"])}</label><input id="paid-hours-month" type="number" min="0.01" max="744" step="0.25" value="160" required></div>
<div class="field"><label for="purchase-price">{html.escape(t["price"])}</label><input id="purchase-price" type="number" min="0" max="1000000000" step="0.01" value="129" required></div>
<div class="field"><label for="tax-percent">{html.escape(t["tax"])}</label><input id="tax-percent" type="number" min="0" max="100" step="0.01" value="0" required></div>
<div class="field"><label for="workday-hours">{html.escape(t["workday"])}</label><input id="workday-hours" type="number" min="0.01" max="24" step="0.25" value="8" required></div>
<div class="field"><label for="saving-rate">{html.escape(t["saving_rate"])}</label><input id="saving-rate" type="number" min="0" max="100" step="0.1" value="10" required></div>
<div class="field"><label for="decision-tag">{html.escape(t["decision_tag"])}</label><select id="decision-tag">{options(t["decision_tags"])}</select></div>
</div><p><button class="button" type="submit">{html.escape(t["update"])}</button></p></form>
<div class="results"><div class="result"><strong>{html.escape(t["effective_hourly"])}</strong><span id="result-hourly"></span></div><div class="result"><strong>{html.escape(t["total_price"])}</strong><span id="result-total"></span></div><div class="result"><strong>{html.escape(t["work_hours"])}</strong><span id="result-hours"></span></div><div class="result"><strong>{html.escape(t["workdays"])}</strong><span id="result-days"></span></div><div class="result"><strong>{html.escape(t["workday_percent"])}</strong><span id="result-workday"></span></div><div class="result"><strong>{html.escape(t["saving_hours"])}</strong><span id="result-saving"></span></div></div>
<p class="note decision" id="result-decision"></p><p class="note">{html.escape(t["math_boundary"])}</p></section>
<section class="wrap grid"><article class="card"><h2>{html.escape(t["method_title"])}</h2><ol>{steps}</ol></article><article class="card"><h2>{html.escape(t["scope_title"])}</h2><p>{html.escape(t["scope_text"])}</p></article></section>
<section class="wrap card faq"><h2>{html.escape(t["faq_title"])}</h2>{faq}</section>
{app_card}
<section class="wrap card faq"><h2>{html.escape(t["sources_title"])}</h2><p><a href="{APP_STORE_SOURCE}" rel="noopener">{html.escape(t["app_source"])}</a></p><p><a href="{WEBMCP_SOURCE}" rel="noopener">{html.escape(t["webmcp_source"])}</a></p></section>
</main>
<footer class="footer"><div class="wrap">{html.escape(t["footer"])}</div></footer>
<script type="application/json" id="hours-config">{config_json}</script>
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
        write_text_if_changed(pages / relative, render_page(locale, app_public))
        outputs.append(canonical(locale))
    for locale in COPY:
        index = pages / "tools" / "index.html"
        if locale != "en":
            index = pages / locale / "tools" / "index.html"
        update_one_index(index, locale)
    return outputs


def main() -> None:
    outputs = build()
    sitemap_count = write_tools_sitemap()
    for output in outputs:
        print(f"HoursTag work-time tool -> {output}")
    print(f"tools sitemap -> {sitemap_count} urls")


if __name__ == "__main__":
    main()
