# Lumi天氣星球：Telegram 三篇替換稿＋weather_full.json 語言行修正值（供 lumiweather-03 使用）

| 項目 | 內容 |
|---|---|
| 用途 | `telegram_posts.json` 裡 app `6779552704` 的三篇（en、zh-Hant、ja）仍是舊定位「child-friendly forecast／給孩子看的天氣／親子で見る天気」，與 live 的「What to Wear／穿搭建議」矛盾；`weather_full.json` 有 17 個語系寫「40 多種語言」（實際 50）。這裡是可直接貼上的替換文字 |
| 發在哪／給誰 | Telegram 頻道 LumiApps2026（telegram-daily 自動發文）＋負責 `_engine/data/weather_full.json` 的人。這份檔案本身不發文；**本次沒有修改 `telegram_posts.json` 與 `weather_full.json`** |
| 發文者 | Lumi Studio 官方頻道（店主 Guan Feng Lai 經營） |
| 發文規則 | 每則一個連結（維持 ct=telegram）；名稱用 live 名稱（若店主依 lumiweather-01 改了 TW／JP 名稱，這裡的名稱要跟著改）；不寫「給孩子看」；不做準確度比較 |
| 事實依據 | weather_full.json（en-US／zh-Hant／ja）：0–100 外出指數＋一句判斷；點指數看體感溫度、紫外線、降雨、風的影響；最適合出門的時段；帶傘、防曬、薄外套提示；今日頁免費；一次性解鎖逐時、一週預報、出門準備清單、多地點、Watch 預報，無訂閱；無帳號、無廣告；Apple WeatherKit。live 名稱（lumiweather.md，2026-10-13 lookup）：US「Lumi Weather: What to Wear」、TW「Lumi天氣星球：天氣預報與穿搭建議」、JP「ルミのおてんき星：天気予報・今日の服装」。50 種介面語言、App 內切換（店主確認） |
| 不能寫 | child-friendly／給孩子看的天氣／親子で見る；逐時與一週預報免費；颱風或警報功能；「買斷制」單獨出現而不說今日頁免費（容易被誤解成付費下載） |
| 連結 | https://apps.apple.com/app/id6779552704?pt=118326163&ct=telegram&mt=8 |

---

## Telegram

### 1. 取代 en（原文：`🌦️ Lumi Weather — a child-friendly forecast that helps kids learn to dress for the day…`）

```json
{
  "lang": "en",
  "app": "6779552704",
  "text": "🌦️ Lumi Weather: What to Wear — turns the forecast into a 0–100 outing score with a one-line verdict, the best time to head out, and tips on umbrella, sunscreen or a light jacket. Tap the score to see how feels-like temperature, UV, rain and wind shaped it. The Today screen works right away; a one-time unlock adds hourly, 7-day and the Get Ready checklist, no subscription. No ads, no account. 50 interface languages, switchable inside the app. Weather data: Apple WeatherKit.",
  "url": "https://apps.apple.com/app/id6779552704?pt=118326163&ct=telegram&mt=8"
}
```

### 2. 取代 zh-Hant（原文：`🌦️ 【Lumi 天氣星球】給孩子看的天氣,學會今天怎麼穿。買斷制、無廣告。`）

```json
{
  "lang": "zh-Hant",
  "app": "6779552704",
  "text": "🌦️ 【Lumi天氣星球：天氣預報與穿搭建議】把預報變成 0–100 的外出指數和一句白話判斷，標出今天最適合出門的時段，提醒帶傘、擦防曬或加件薄外套；點一下分數，就看得到體感溫度、紫外線、降雨和風各自的影響。今日頁打開就能用，逐時、一週預報與出門準備清單一次解鎖、不訂閱。無廣告、不用帳號。介面 50 種語言，可在 App 內切換。天氣資料來自 Apple WeatherKit。",
  "url": "https://apps.apple.com/app/id6779552704?pt=118326163&ct=telegram&mt=8"
}
```

### 3. 取代 ja（原文：`🌤️ Lumi Weather — 親子で見る天気アプリ。おでかけ指数と服装のヒント。買い切り、トラッキングなし。`）

```json
{
  "lang": "ja",
  "app": "6779552704",
  "text": "🌤️ ルミのおてんき星：天気予報・今日の服装 — 予報を0〜100の「おでかけ指数」とひと言に。おでかけに向いている時間帯や、傘・日焼け止め・薄手の上着のアドバイスも。指数をタップすれば、体感温度・紫外線・雨・風がどう影響したかがわかります。今日の画面はすぐ使えて、1時間ごと・週間予報・おでかけ準備リストは買い切りで追加（サブスクなし）。広告なし・アカウント不要。表示言語は50言語からアプリ内で切り替えられます。天気データは Apple WeatherKit。",
  "url": "https://apps.apple.com/app/id6779552704?pt=118326163&ct=telegram&mt=8"
}
```

---

## weather_full.json：語言行修正值（description 最後一段）

| 語系 | 現在 | 改成 |
|---|---|---|
| zh-Hant | Lumi天氣星球支援 40 多種語言，可以跟隨系統語言，也能自己選擇。 | Lumi天氣星球的介面支援 50 種語言，可以跟隨系統語言，也能在 App 內自己切換。 |
| ja | ルミのおてんき星は40以上の言語に対応し、システムの言語に合わせることも、好きな言語を選ぶこともできます。 | ルミのおてんき星の表示言語は50言語に対応し、システムの言語に合わせることも、アプリ内で好きな言語に切り替えることもできます。 |
| en-US | Lumi Weather is available in more than 40 languages and can follow your system language or one you choose. | Lumi Weather's interface is available in 50 languages and can follow your system language, or you can switch to another one inside the app. |
| ko | 루미 날씨는 40개 이상의 언어를 지원하며 시스템 언어를 따르거나 원하는 언어를 직접 선택할 수 있습니다. | 루미 날씨는 50개 언어의 화면 표시를 지원하며, 시스템 언어를 따르거나 앱 안에서 원하는 언어로 바꿀 수 있습니다. |

> 檔內共有 17 個語系的描述含「40」這個語言數，其餘 13 個語系請照同樣句型改成 50；改完後 GEO 頁與決策頁 copy 指紋會變，需本機 GrowthEngine 重新封存（見 README「交給你電腦上 Claude 的工作」第 1 項）。

## weather_full.json：前三個關鍵字（計分板量測詞）

| 語系 | 前三個改成 | 原本 |
|---|---|---|
| zh-Hant | `穿搭 天氣,今天穿什麼,外出指數` | 天氣,天氣預報,氣象 |
| ja | `服装 天気,おでかけ 天気,おでかけ指数` | 天気,天気予報,気象 |
| en-US | `what to wear weather,outfit weather,outing score` | weather,weather forecast,local weather |

> 同時建議刪掉三個語系關鍵字裡的親子舊詞（weather for kids、stroller、嬰兒推車、親子天氣、ベビーカー、子供 天気），由店主在 lumiweather-01 決定是否同步到 ASC。本次回傳的 challenge_terms 也列了這些量測詞。
