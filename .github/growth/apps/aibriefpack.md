# AI Brief（aibriefpack）

**一句話診斷**：沒有人在搜「交給 AI 之前先整理」這件事，名稱「AI Prompt from Files」又像提示詞庫，描述連免費或價格都沒寫——這是需求教育問題，不是曝光問題。

## 結論
沒有搜尋需求可吃：量測詞「prompt／summary／要約／摘要」全是別人的；名稱像提示詞庫；描述不提價格或免費範圍。low 優先維持，但要走「教育內容＋上架平台」而不是更多頁面。0 評分。

## 各市場真正問題
- **ja**：需求討論在企業內規，不在個人工具；描述三句重複。
- **en-US**：副標「Files to Clear Context」抽象；live 已刪介面字串，但無價格、重複未改。
- **zh-Hant**：描述只有 558 字（en 1,392），沒有情境。

## 第一輪修正
介面字串問題 live 已修（資料檔過時）；新增「描述完全沒寫價格／免費」這個漏洞；三則貼文與 live 相符。

## 行動
| claude | local | you |
|---|---|---|
| 「截圖貼給 AI 前的 5 步檢查」單頁指南（3 語） | 重匯出 aibriefpack_full.json | 描述加情境＋價格、刪重複、擴 zh-Hant／ja；副標「Redact & organize before AI」 |
| PH／Show HN／note.com 草稿 | | 修 vi／id 黏字關鍵字；加 50 語言句 |
| 貼文入庫；量測覆寫 ai prompt from files／個人情報 マスキング | | 本人上架 PH／Show HN，附虛構資料示範 |

## 二次審核修正

- 第一輪指出描述混進介面字串「Choose one or more sources above…」：live 已改為「Mix and match as many sources…」（zh/ja/ko 同步改），aibriefpack_full.json 過時；但「check every fact」三次重複與無價格說明仍在。
- 第一輪說 0 評分：本次六個店面確認 0，v1.0.5。
- 第一輪漏掉：描述完全沒寫免費／付費模式，使用者無法判斷下載後要付什麼。
- 第一輪三則貼文與 live 文案相符（來源＋信賴度、衝突與待解問題、逐項保留替換移除、不保證匿名、OCR 在裝置端），保留並補 50 語言一句。

## 各市場證據

| 語系 | 真正問題 | 證據 |
|---|---|---|
| ja | 成績單量的是「要約／まとめ／文書」，被摘要類 App 佔滿；名稱「資料から AI プロンプト」讀起來像摘要或提示詞工具。日本的「生成AI 情報漏洩」討論集中在企業內規，個人工具的搜尋需求幾乎沒有。描述 795 字、仍有三句重複「確認してください」。 | iTunes lookup 2026-10-13：JP 名稱 AI Brief：資料から AI プロンプト，評分 0，描述 795 字。成績單 issue #8（2026-10-13 04:31 UTC）：AI Brief 最佳名次 120（GR σύνοψη）。 |
| en-US | 「prompt」「summary」兩個量測詞都是別人的地盤；名稱說 prompt，描述說 brief，副標「Files to Clear Context」太抽象。live 描述已刪掉介面字串（第一輪指出的那句），但仍重複三次「check every fact」，且全篇沒有價格或免費說明。 | iTunes lookup 2026-10-13：US 名稱 AI Brief: AI Prompt from Files，副標 Files to Clear Context，評分 0，10 張截圖；描述第 3 點已改為「Mix and match as many sources as you need」。第一輪讀數，本次未重現：排名全為低量詞。 |
| zh-Hant | 母市場描述只有 558 字（en 1,392），沒有情境、沒有價格；「提示詞管理」第 20／33 這種低量詞也排不前。真正差異（每筆事實附來源與信賴度、個資逐項處理、不保證匿名）不在名稱與副標。 | iTunes lookup 2026-10-13：TW 名稱 AI Brief：檔案轉 AI 提示詞，描述 558 字，評分 0。第一輪讀數，本次未重現：提示詞管理 20／33。 |
