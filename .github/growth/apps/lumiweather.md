# Lumi Weather: What to Wear（Lumi天氣星球，免費＋內購）（lumiweather）

**一句話診斷**：全球只有 3 則評分（TW 2、JP 1）；真正的問題是跟免費內建 Apple 天氣正面競爭，TW 與 JP 的線上名稱都把最擠的「天氣預報」放在最前面、把唯一差異「外出指數／おでかけ指数」藏在後面，免費層又把 Apple 免費就有的逐時／一週預報鎖起來；外部資產（GEO answers、Telegram）還停在舊的「給孩子看的天氣」定位。

## 結論
今日 lookup：TW 2 則、JP 1 則、US／ID／KR 0。真正的問題是跟免費內建 Apple 天氣正面競爭：「天氣／天気」大詞被 4–7 萬評分的 App 佔滿（第一版同 API 量到 TW 第 18），利基詞「穿搭 天氣」雖第 5 也只帶來 2 則評分——利基搜尋量小，差異必須靠外部內容送到人面前。TW 與 JP 的 live 名稱都把「天氣預報／天気予報」放最前面、把唯一差異「外出指數／おでかけ指数」藏在後面，與資料檔／GEO 不一致；描述寫「40 多種語言」（實際 50）；免費層鎖住 Apple 免費就有的逐時／一週預報。外部資產（Telegram、8 個 zh-Hant answers 頁）仍停在舊的「給孩子看的天氣」。

## 各市場真正問題
- **TW**：大詞不可能贏、利基詞量小；名稱順序與語言行要改。
- **JP**：名稱同樣漂移；「服装 天気」被 おしゃれ天気（22,906）壟斷。
- **en-US**：0 評分、最飽和，暫緩。
- **id**：ID 店面預設英文 listing（印尼文版存在）；可用場景是台灣的印尼籍看護在中文 iPhone 上切介面語言，只支援 iPhone。

## 行動
**you（ASC）**：TW／JP 名稱把外出指數放回最前、關鍵字避開大詞與親子舊詞、語言行改 50、核對 id 版 Apple Watch 敘述；評估逐時預報進免費層；天氣日當天本人發 Threads、錄三語 Shorts。
**claude**：改寫 Telegram 三篇（刪「給孩子看」）；weather_full.json 語言行改 50、前三關鍵字換成利基詞讓計分板量得到；寫 6 篇觸發式貼文、note 開發記、Shorts 腳本。
**local**：重產 8 個 answers 頁與 hub，從 kids 定位改成「今天穿什麼／外出指數」，GEO 名稱跟上 live。

## 二次審核修正

- 名稱漂移不只 TW：JP live 名稱「ルミのおてんき星：天気予報・今日の服装」同樣把「天気予報」放前面，與資料檔／GEO 的「おでかけ指数」不一致（第一版只點出 TW）。
- 語言數：live 描述（TW／JP／US／ID）寫「40 多種／40以上／more than 40 languages」，擁有者確認是 50，ASC 與資料檔都要改；第一版未處理。
- 第一版的「天氣第 18、穿搭 天氣第 5、服装 天気第 49」是同一 API 的早先量測，今日因 Apple 回 403 無法重驗，列為第一版數字；今日新驗證的是 5 個店面的評分（TW 2、JP 1、US／ID／KR 0）、名稱與描述。
- Telegram 既有三篇仍是舊定位「child-friendly forecast／給孩子看的天氣／親子で見る天気」，與 live 的成人「What to Wear／外出指數」矛盾；zh-Hant 8 個 answers 頁（best-weather-for-kids-app 等）也仍是「weather for kids／年齡適合的判斷」——第一版點到 GEO，但漏了 Telegram。
- 計分板只量資料檔每語系前 3 個關鍵字，目前 zh-Hant 前三是「天氣,天氣預報,氣象」、ja「天気,天気予報,気象」——量的是不可能贏的大詞，應改成利基詞，這是 claude 可自己改的資料檔。
- ID 店面預設英文不是錯誤（Apple 行為），印尼文 listing 確實存在；第一版對 id 市場的「台灣看護」切角成立，但要明說只支援 iPhone、兩人共用時只切介面語言。

## 各市場證據

| 語系 | 真正問題 | 證據 |
|---|---|---|
| zh-Hant | 「天氣」大詞被 Apple 天氣與 4–5 萬評分的 App 佔滿，不可能贏；利基詞「穿搭 天氣」雖排第 5 卻只帶來 2 則評分，代表利基本身搜尋量很小，差異化必須靠「看天氣發文」等外部內容送到人面前，而不是等人搜。線上名稱「天氣預報與穿搭建議」把差異放在後面，且與資料檔／GEO 的「外出指數與穿搭建議」不一致。 | live lookup：TW 名稱「Lumi天氣星球：天氣預報與穿搭建議」、免費、2 則評分（5★）、類別 天氣／生活風格、描述寫「支援 40 多種語言」（實際 50）。第一版同 API（今日 403 無法重驗）：「天氣」第 18（Apple 天氣 70,309、觀天氣 49,425、Windy 37,172）、「穿搭 天氣」第 5（Weather Fit 1,302）。repo：zh-Hant/lumiweather.html 標題用「外出指數與穿搭建議」，與 live 不同。 |
| ja | 名稱同樣漂移且把「天気予報」放前面；利基「服装 天気」由 おしゃれ天気（22,906）壟斷；只有 1 則評分。 | live lookup：JP 名稱「ルミのおてんき星：天気予報・今日の服装」、1 則評分（5★）；資料檔／GEO 名稱是「ルミのおてんき星 おでかけ指数」。第一版同 API：「服装 天気」第 49（おしゃれ天気 22,906）、「おでかけ 天気」第 7。來源：https://itunes.apple.com/lookup?id=6779552704&country=jp |
| en-US | 0 評分，英文市場最大也最飽和（Weather Fit 3,795），而且 iOS 內建天氣免費；在沒有評分前投入英文效率最低。 | live lookup：US 0 評分、名稱「Lumi Weather: What to Wear」、描述「more than 40 languages」。第一版同 API：「what to wear weather」第 29（Weather Fit 3,795）。 |
| id | ID 店面預設顯示英文 listing（印尼文版有上，需 lang=id 才看到），0 評分；真正可用的印尼語場景不在印尼，而是在台灣：照顧長輩的印尼籍看護用家中中文 iPhone，在 App 內把介面切成印尼語——這是 50 語的真實用途，但 iPhone 覆蓋有限，只能當低成本的補充市場。 | live lookup：country=id 預設回英文名稱／描述；加 lang=id 才回「Lumi Cuaca: Prakiraan Hari Ini」；0 評分。資料檔 id 描述寫「lihat skor di Apple Watch」，en-US／zh-Hant 寫 Watch 只看目前氣溫，未解鎖前不含預報——需核對。 |
