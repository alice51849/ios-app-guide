# DailyMate Lite: Speak Today（dailymatelite）

**一句話診斷**：免費、50 種學習語言、介面可切換，是「移工看護練中文／雇主家庭學看護母語」這個 50 語言主軸最強的 App，但 zh-Hant／id／vi 的 keywords 完全沒有「印尼文／越南文／bahasa mandarin／tiếng Trung」，連 56–75 筆結果的小池子都排不進前 10。

## DailyMate Lite（6794725568）— 優先度：中

**結論**：免費、50 種學習語言、介面可切換，是「移工看護練中文／雇主家庭學看護母語」最強的 App。但 zh-Hant／id／vi keywords 完全沒有「印尼文／越南文／bahasa mandarin／tiếng Trung」：TW「學越南文」只有 75 筆結果、第 1 名 93 則評分，我們排 #71；「學印尼文」56 筆、第 1 名 37 則，我們不在榜。

**各市場真正問題**
- zh-Hant：小池子拿得到，但關鍵字沒放。類別「教育＋旅遊」有利，不要改。
- id：名稱只有「DailyMate Lite」、沒有 bahasa mandarin；印尼看護多用印尼 Apple ID。免費層只含旅行初級，貼文要講明。
- vi：沒有 tiếng Trung／tiếng Hoa。
- ja：對手 17K–76 萬則，降為次要。

**行動**
- claude：三則看護情境貼文接進 app-posts.json 與 Telegram；成績單加 學印尼文／學越南文／belajar bahasa mandarin／học tiếng Trung；Shorts 腳本。
- local：threads-autopilot 每週 1 則雇主痛點貼文。
- you：zh-Hant／id／vi keywords 補學中文與印尼文、越南文詞；id 名稱帶關鍵字；promotionalText 改共用手機情境；先確認三語都在學習語言內；聯繫 One-Forty、新住民中心並取得社團版主同意。

## 二次審核修正

- 第一輪說「所有查詢前 180 名都找不到」：實測「學越南文」排 #71／75——有進榜但在底部；zh-Hant keywords 根本沒有「越南」，補上就能大幅前進（第 1 名只有 93 則評分）。
- 第一輪只建議改 id 名稱，漏掉 id／vi keywords 都沒有「學中文」的詞（bahasa mandarin／tiếng Trung），而這才是移工情境的搜尋詞。
- 第一輪說還沒確認印尼文、越南文、中文是否在 50 種學習語言內：lookup 介面語言表含 ID、VI、TH、ZH，listing 說任一學習語言都能選，但學習語言是否等於介面語言仍需 owner 確認，貼文發前核對。
- 第一輪把 ja 列為最佳市場：日本對手 17K–76 萬則、我們 ja 名稱無關鍵字，ja 降為次要。
- 第一輪沒注意 Lite 的次類別是「旅遊」（付費版是「參考」），這對旅遊短句搜尋有利，不要改。

## 各市場證據

| 語系 | 真正問題 | 證據 |
|---|---|---|
| zh-Hant | 「學印尼文」只有 56 筆結果、第 1 名 37 則評分；「學越南文」75 筆、第 1 名 93 則——我們在「學越南文」排 #71（倒數第 5），因為 zh-Hant keywords 沒有印尼文、越南文、泰文、看護、新住民。 | TW「學印尼文」56 筆無我方（#1 學印尼文 37 則、#3 5000片語 2 則）；「學越南文」#71／75（#1 學越南文 93 則、#3 nemo 1,992）；「旅遊英文」176 筆無（#1、#2 只有 5–6 則）。Lookup TW：免費、0 則、4+、類別 教育＋旅遊。 |
| id | id 名稱只有「DailyMate Lite」、keywords 沒有「bahasa mandarin／bahasa Taiwan」——印尼看護多用印尼 Apple ID，搜「belajar bahasa mandarin」找不到我們；免費層只有「旅行」初級，看護需要的健康／工作主題要付費。 | 本地檔 id：name「DailyMate Lite」、keywords「latihan percakapan,frasa perjalanan,pelafalan,mendengarkan,kosakata,belajar harian,lancar,komunikasi」。ID 店面搜尋因 Apple 限流本輪未量到（第一輪：前 180 名不在榜）；lookup 介面語言表含 ID、VI、TH、ZH。 |
| vi | vi keywords 有 tiếng Anh／Nhật／Hàn 卻沒有「tiếng Trung／tiếng Hoa」，在台越南移工與新住民學中文的詞完全沒接到。 | 本地檔 vi keywords：giao tiếp,du lịch,phát âm,nghe,tiếng Anh,Nhật,Hàn,Pháp,Đức,Ý,từ vựng,tự học,sân bay,khách sạn,thi,bé。VN 店面「học tiếng Trung」因限流未量到。vi 描述已寫 50 ngôn ngữ。 |
| ja | 日本人主要學英文，對手 英会話フレーズ1600 17K、Duolingo 76 萬；ja 名稱「ひとこと練習」無關鍵字——ja 只適合 X 貼文，不是主戰場。 | JP「旅行 英会話」160 筆無我方（#1 3,207、#2 17,314、#3 僅 7 則）；「英会話 フレーズ」166 筆無。Lookup JP：免費、0 則。 |
