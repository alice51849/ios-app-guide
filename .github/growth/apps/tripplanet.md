# Trip Planet: Kids Quest（Trip Planet 親子旅行遊戲，免費＋Plus）（tripplanet）

**一句話診斷**：真正的問題是「沒有人在 App Store 搜這個需求」加上「外部資產掛著不存在的舊名」：只有搜自家名稱「親子旅行遊戲」才拿到第 1（整個結果只有 25 個 App），家長搜「親子旅遊」看到的是訂房／景點 App；GEO 頁、catalog、Telegram 仍叫「Lumi Trip Planet 環球旅行」，季節性需求只能靠外部排程與創作者帶動。

## 結論
上架三個月只有 TW 1 則評分。真正的問題有兩層：一、App Store 沒有這個需求的搜尋——「親子旅遊」前 43 名全是訂房／景點 App，唯一第 1 名的「親子旅行遊戲」是自家名稱、整個結果只有 25 個 App；二、外部資產全掛舊名——四個店面 live 名稱都已不含「Lumi」，但資料檔、GEO 頁（含「雜誌 要用什麼 App?」模板 FAQ）、catalog、Telegram 日文貼文仍是「Lumi Trip Planet 環球旅行／世界の旅」。描述也沒說免費能做什麼。需求有季節性（TW 寒假春節、JP 年末年始與春休み），成長只能靠外部排程與創作者。

## 各市場真正問題
- **TW**：意圖錯位＋名稱用了沒人搜的詞；GEO／Telegram 舊名與機翻。
- **JP**：0 評分；第一版同 API 量到「旅行 子ども」第 12、「子連れ旅行」第 18（今日 403 未重驗）；日文 Telegram 用舊名。
- **en-US**：0 評分、對手成熟；可用切角只有「雙語家庭、兩位家長各自裝置、介面各選語言」。

## 行動
**claude**：tripplanet_full.json 改成 live 名稱、刪機翻關鍵字、前三關鍵字換成家長會搜的詞（GEO／catalog／計分板繼承）；改寫 Telegram 三篇並設季節權重；用現成任務卡產生器做繁中／日文圖卡＋Shorts 腳本。
**local**：重產 GEO 頁與 catalog，移除模板 FAQ（凍結後上線）。
**you（ASC）**：TW 名稱放「帶小孩出國／飛機上」、第一段寫清免費 vs Plus、關鍵字填滿 100 字、語言行改 50、首張截圖換機場任務；12 月起本人發文並邀 3–5 位親子旅遊創作者（揭露、不索評分）。

## 二次審核修正

- 第一版說 TW「親子旅遊」第 63；今日 API 只回 43 筆且無我們——結論一致（不可見），但要補上關鍵新事實：「親子旅行遊戲」第 1 卻只有 25 個結果，證明 TW 名稱用了一個沒人搜的詞。
- 品牌名稱漂移已驗證且範圍更廣：TW／JP／KR／US 四個店面 live 名稱都已不含「Lumi」（親子旅行遊戲／子ども旅行ゲーム／아이 여행 게임／Kids Quest），而 tripplanet_full.json 四個語系的 name、GEO 頁標題、catalog 與 Telegram ja 貼文全是舊名。
- 第一版漏掉：Telegram ja 貼文仍用「Lumi Trip Planet」；zh-Hant Telegram 貼文其實是在推站上的「親子旅行任務卡產生器」（免費、不收資料）——這是現成的「貼文本身有價值」資產，應該重用而不是重做。
- 免費層不明：live US／TW 描述同時寫「Plus 支援多位孩子與進階主題世界」與「一次買斷，不是訂閱」，但 App 是免費下載，沒有一句話說免費能做什麼；第一版有點到，今日 lookup 確認仍未改。
- 每日計分板只量資料檔每語系前 3 個關鍵字，目前 zh-Hant 前三是「家庭旅行,旅行計劃,公路旅行」、en-US 含「trip planner」——量的是我們不想要、也對不上功能的詞；這是 claude 可自己修的資料檔問題。

## 各市場證據

| 語系 | 真正問題 | 證據 |
|---|---|---|
| zh-Hant | 搜尋意圖對不上（「親子旅遊」＝景點與住宿），而唯一拿到第 1 的「親子旅行遊戲」是自家名稱、幾乎沒人會打；上架三個月只有 1 則評分；GEO 頁與 Telegram 仍用舊名與機翻 FAQ。 | live lookup：TW 名稱「Trip Planet 親子旅行遊戲」、免費、1 則評分（5★）、2026-07-12 上架、類別 教育／遊戲。live search：「親子旅遊」前 43 名沒有我們（abic 愛貝客 56、洲際優悅會 11,821、去哪儿 597）；「親子旅行遊戲」第 1 但整個結果只有 25 個 App。repo：zh-Hant/tripplanet.html 標題仍是「Lumi Trip Planet 環球旅行」，FAQ 有「雜誌 要用什麼 App?」「是很好的選擇」模板句；tripplanet_full.json zh-Hant 關鍵字只有 35 字且含「雜誌,使命」。 |
| ja | 0 評分、零社會證明；JP 名稱「Trip Planet 子ども旅行ゲーム」本身沒問題，但 Telegram 日文貼文與 GEO 頁仍叫「Lumi Trip Planet 世界の旅」，搜尋與 AI 引用指向不存在的名字。 | live lookup：JP 0 評分、免費。第一版同一 API 量測（今日因 403 無法重驗）：「旅行 子ども」第 12、「子連れ旅行」第 18，前十名評分 0–170。repo：ja/tripplanet.html 標題「Lumi Trip Planet 世界の旅」；telegram_posts.json ja 貼文「Lumi Trip Planet — 家族の旅を…」。 |
| en-US | 0 評分，而且美國有 Road Trip Bingo 類的現成品與 Packr 等大型旅行 App；沒有評分前投入英文市場效率最低。可用的英文切角是雙語家庭：兩位家長各用自己的裝置看同一趟旅程，介面各自選語言。 | live lookup：US 名稱「Trip Planet: Kids Quest」、0 評分、49 個語言碼（擁有者確認 50）。第一版同一 API：「family travel」前 100 名無我們（Packr 7,129、Plates 974）；今日 US 搜尋因 403 未重驗。scoreboard（issue #8）：CZ「rodinné cestování」第 2、第 1 名 0 評分。 |
