# ShotInbox 下載診斷：問題是「沒人看到」，不是「看了不下載」

## 1. 一句話結論
下載數＝曝光×轉換率。你說轉換率高，但 8/1–10/13 只有 27 次首次下載，最可能的原因是這段期間很少人看到 ShotInbox。舉例：假設轉換率是 10%，74 天大約只有 270 次曝光，每天不到 4 次；實際數字要到 ASC 查。文案確實有問題，但問題應該在名稱、副標題和關鍵字，這三個欄位決定 App Store 搜不搜得到你，問題不太在說服力。這是推斷，排名沒有實測。
注意：27 是很小的樣本。高轉換率可能來自原本就知道、直接搜「ShotInbox」的人，不代表陌生人也會一樣願意下載。

## 2. 根本原因排名
1. **搜尋很可能排不到（推斷影響最大）**：50 個語系的名稱都是英文「ShotInbox AI: Sort Screenshots」（_engine/data/shotinbox_full.json）。zh-Hant 副標題「本機截圖分類、OCR搜尋與時間軸」只用了 16/30 字，寫的還是功能。en-US 副標題「OCR Search & Photo Cleaner」用到的是照片清理的熱門詞。第三方快照顯示，這類詞被 Cleanup（約 62.8 萬則評分）這種大廠占著，0 評分的新 App 很難排上去。
2. **外部導流幾乎是零（影響大）**：GEO 網站的線上部署從 10/04 起凍結。Telegram 從 9/18 停發，今天才修好；.github/scripts/telegram_posts.json 的 258 則貼文裡只有 3 則是 ShotInbox。Threads 舊帳號因為每天發 30–48 則商店連結被停權。dev.to 文章（devto_articles.json）和影片（lumi-studio-app-video-lessons.json）裡，ShotInbox 都是 0。估計 8 月以來外部渠道帶來的點擊不超過 10 次左右（未驗證，拿不到訂閱數，也沒有 Search Console 資料）。
3. **沒有評分，也沒有第三方提及（中大，影響會累積）**：所有店面快照的評分都是 0。網路上搜 ShotInbox，只找到名字相近的 ShotBox 和「Shot Done: Screenshot Inbox」。AI 助理推薦 App 時，約 47.5% 會引用 App Store 頁面，而 0 評分代表那裡沒有口碑可以引用。品牌在 AI 回答裡的能見度，和 YouTube 提及的相關係數約 0.74，和第三方網站提及約 0.7，和自家網站頁數只有約 0.19。這是相關，不代表因果。
4. **市場小、定位分散（中）**：依第三方資料，專門整理截圖的 App 多半只有 4–37 則評分（Shutter Declutter 約 232 則）；需求大的是「照片清理」，那邊已被大廠占據。建議主打較精準的需求：「找回截圖裡的字」和「清掉多年積壓的舊截圖」。
5. **自家 GEO 內容有風險，成效也量不到（中）**：全站（53 款 App）有 46,101 個可被收錄的頁面（_engine/geo/reports/link_depth.json）。ShotInbox 的 en-US answers 頁彼此相似度 91–95%，有被 Google 2026 年的 scaled／doorway 規則判成垃圾內容的風險。全站共用同一個追蹤碼 ct=geo_pick，分不出下載從哪裡來。另外有兩頁截圖問答把人導去自家的 PicClear（id6780223070）。

## 3. 文案與圖文的具體問題
**商店頁（全部由你在 ASC 決定，我們不會動）**
- 非英語語系的名稱裡沒有當地語言的搜尋詞。「AI」佔 3 個字元，也可能讓重視隱私的人以為截圖會上傳。
- 關鍵字估計有三到四成用在搜尋需求低的賣點詞和分類詞上：zh-Hant 有「隱私保護,離線處理,永久買斷,對話,食譜,地圖」，ja 有「端末内,買い切り,ギャラリー」。
- 推廣文字用了開發者術語，例如「complete core workflow」「Apple Vision 與 Natural Language」。zh-Hant 的**描述**裡寫死了「US$5.99」。
- 依你提供的高轉換率，說服力不像主要瓶頸；但樣本小，建議還是把第一張截圖換成整理前後的對比。

**外宣（由我們負責）**
- 好文案其實有，例如 Telegram 的「截圖存了一堆,卻沒有一張真的處理掉?」，只是幾乎沒人看到。
- 數量最多的頁面在堆關鍵字：en-US/shotinbox.html 有「What is the best app for organizer?」，zh-Hant/shotinbox.html 有「相簿 最好用的 App 是哪個?」。
- alternatives/shotinbox-vs-captr.html 的比較表裡，對手那一欄是「Varies」，自家「No ads」那格反而是「—」。
- _engine/geo/shotinbox_public_site.py 生成的 200 個支援頁，卡片標題是「Vision · NaturalLanguage」「ShotInbox · BGAppRefresh」這類技術詞。頁面上也沒有可以點的 App Store 連結，只有 Smart App Banner 的 meta 標籤。
- 完全沒有畫面示範：data/result-image-coverage.json 裡 ShotInbox 的 50 個語系都是 BLOCKED_EVIDENCE；宣傳海報只是 App 圖示加漸層背景。
- 定位不一致：副標題主打「Photo Cleaner」，Telegram 強調「never deletes anything on its own」，「到底能不能幫我清」沒有講清楚。

## 4. 行動計畫
**(a) 我們立刻執行（不改 App、不動 ASC）**
1. 先處理風險，再恢復網站部署：每個語系把相似頁合併成 1 頁，其餘加 noindex；FAQ 改寫成真實問題；停用「vs」比較頁。
2. 追蹤碼依渠道分開，例如 geo_hub_en、tg_ja、yt_en、pr_applealmond。Telegram 目前共用的 social_shotinbox 也依語系拆開。
3. 截圖類查詢只導向 ShotInbox，容量和重複照片類查詢只導向 PicClear，兩頁互相連結。
4. 人工撰寫 3 篇教學（zh-Hant、ja、en）：「iPhone 截圖太多怎麼清、怎麼找回截圖裡的字」。
5. 到第三方平台各發一次、註明開發者身分、遵守各平台規則：AlternativeTo、Product Hunt、SaaSHub、Mergeek；投稿 Apple 仁、MrMad、MacMagazine、appgefahren；參加 r/iosapps 每週自我推廣串。每個平台的內容分開撰寫，不用自動化，也不大量發連結。
6. 製作 15 秒整理前後對比短片。**需要你先用示範資料（不含任何人的隱私）錄一段畫面。** 給 YouTuber 的兌換碼由你在 ASC 產生；請創作者標示為贈送或合作，不要求他們給好評。

**(b) 【由你在 ASC 決定，我們不會動】**（名稱、副標題、關鍵字要跟新版本一起送審；推廣文字隨時可以改）
- en-US：名稱「ShotInbox: Screenshot Cleaner」(29)／副標題「Organize, Search & Delete Fast」(30)／關鍵字「organizer,manager,cleanup,remove,old,find,storage,space,clutter,text,ocr,ai,receipt,camera,roll」(95)
- zh-Hant：名稱「截圖整理與清理 - ShotInbox」(19)／副標題「找回截圖裡的文字，刪除舊圖騰出空間」(17)／關鍵字「螢幕截圖,截屏,快照,相簿,照片,圖片,管理,分類,歸檔,收據,OCR,文字辨識,記憶體,容量,不足,瘦身,斷捨離,大量,自動,清除,找圖,離線,手機,AI」(78)
- ja：名稱「スクショ整理・削除 - ShotInbox」(21)／副標題「スクリーンショットを文字検索・削除で容量確保」(22)／關鍵字「写真,画像,アルバム,カメラロール,管理,分類,仕分け,片付け,掃除,クリーナー,OCR,文字認識,ストレージ,空き,不足,まとめて,断捨離,レシート,AI,自動,探す」(84)
- 刻意不放 duplicate、similar：搶不贏大廠，也會和 PicClear 搶流量。以上選詞是 ASO 判斷，沒有實測搜尋量。送審前請先在 Apple Search Ads 後台查這些詞的熱度。
- 文案要和免費版能做的事一致：描述裡寫明「batches & similar groups」屬於 Pro。
- zh-Hant 推廣文字範例：「截圖爆量、空間不足？輸入關鍵字就能找到截圖裡的文字，沒用的直接清掉。最近 50 張免費；一次買斷、無訂閱，全程在手機上處理。」描述裡寫死的 US$5.99 建議拿掉，或改成當地幣別。
- pt-BR、de、ko 的關鍵字請母語者重寫，例如巴西加 print／apagar，德國加 Bildschirmfoto，韓國加 스샷；現在用的「청소기」一般指吸塵器。
- 在 App 內邀請使用者評分需要改 App，由你決定。絕對不買評論，也不用假評論。

**(c) 要追蹤的指標（ASC → App Analytics）**
- 先記下 8/1–10/13 的基準數字：曝光（不重複裝置數）、產品頁瀏覽、轉換率、首次下載。
- 依來源類型（App Store 搜尋、瀏覽、App 轉介、網頁轉介）拆開下載數。如果大部分來自搜尋、曝光又極低，就證實了第 1 名的原因。
- 每週看美國、台灣、日本的曝光。新版上線 4 週後比較前後：目標是曝光成長；轉換率小幅下降是正常的。
- 在 Campaigns 報表看各追蹤碼（ct）的數字；人數太少時 Apple 可能不顯示。

限制：我們看不到 ASC 的數據，連 Apple 搜尋服務的請求也被 proxy 擋下（403），所以搜尋量、排名和觸及人數都是推斷。以上做法不保證下載一定成長，但每一步的成效都量得到。

## 查核備註
- **AI 引用說法改正**：原稿寫 AI 推薦 App「主要參考第三方網站」。依 context，AI 約 47.5% 引用的是 App Store 頁面，0.74／0.7／0.19 是「品牌能見度」的相關係數，所以已改正並註明相關不等於因果。
- **Telegram 停發日期**：context 寫「停到今天才修好」，原稿寫「9/18–10/12」，已改為「9/18 起停發，今天才修好」。
- **Telegram 引文不完整**：原句是「never deletes anything on its own」（不會自動刪除），和「Photo Cleaner」並不真的矛盾，已改成「定位不一致」。
- **US$5.99 的位置**：價格寫在 zh-Hant 的**描述**裡，不在推廣文字（_engine/data/shotinbox_full.json）。支援頁不是完全沒有 App Store 入口：沒有可點的 apps.apple.com 連結，但有 apple-itunes-app meta 標籤。兩處都已改正。
- **推斷語氣調整**：排名、評分數字（第三方快照，補上 Shutter Declutter 約 232 則）、Google 判罰、「轉換率證明說服力」都改成推斷或風險的語氣；46,101 頁註明是全站 53 款 App 的總數。
- **ASC 標示與合規**：ASC 段落改為明確的【由你在 ASC 決定，我們不會動】。兌換碼要求創作者標示贈送，不要求好評；外宣註明不自動化、不大量發連結。已核對 ASC 建議文案的字數（29/30/95、19/17/78、21/22/84）都正確。
