# Lumi數學星球：Telegram 佇列文案（zh-Hant／ko／ja／en）（lumimath-04 的 Telegram 部分）

| 項目 | 內容 |
|---|---|
| 用途 | 佇列 `.github/scripts/telegram_posts.json` 裡 Lumi數學星球（id 6778269699）只有三則舊文案，內容停在「數數、形狀、基礎數學」，沒寫 50 種介面語言，也沒寫最有差異的「看圖就懂、規律邏輯、列印學習單」。本檔是四則替換文案。另外：每日精選的「今日焦點」會自動從 `app-posts.json` 挑 zh-Hant 貼文（≤600 字、不含連結），lumimath 的 zh-Hant 貼文已在裡面，**今日焦點不需要改程式** |
| 發在哪／給誰 | Lumi Studio 的 Telegram 頻道；zh-Hant、韓文、日文、英文讀者 |
| 發文者 | 由維護佇列的流程（店主或本機 Claude）把下面的 JSON 貼進 `telegram_posts.json`，以 Lumi Studio 頻道名義自動發出。本檔沒有改佇列、不會自動發出 |
| 發文規則 | 每則開頭寫「50 種介面語言、App 內切換、不必改手機語言」；只寫商店文案有的功能；不提任何數學競賽名稱；不點名其他 App；連結用 `ct=telegram`；名稱不用「探索版／体験版／체험판」字樣（lumimath-01 建議 ASC 移除） |
| 事實依據 | math_planet_full.json（zh-Hant／ko／ja／en-US）：每題都是圖（骰子、十格框、數線、長條圖）、還不識字也能玩、題目朗讀；超過 40 種題型自動分級（live 第一行寫 46，兩者都不矛盾「超過 40」）；答錯沒有刺耳音效；家長專區五大能力、標出弱項、一鍵集中練習、匯出可列印練習學習單與成長報告；前幾顆星球與每日挑戰免費、一次解鎖、無訂閱、無廣告、不蒐集資料、無帳號；題目與語音中英日韓。50 種介面語言、App 內切換（店主確認） |
| 不能寫 | 競賽名稱或「競賽級」「世界級」「電影級」；「依裝置自動偵測語言」（與 App 內切換矛盾）；50 語題目或語音；評分、排名、「最好」 |
| 連結 | https://apps.apple.com/app/id6778269699?pt=118326163&ct=telegram&mt=8 |

## 建議換掉的舊條目（在 `telegram_posts.json` 用 text 搜尋）

| lang | 舊文案開頭 | 為什麼換 |
|---|---|---|
| zh-Hant | 🔢 【Lumi 數學星球】用探險遊戲學數數與基礎數學 | 沒寫 50 語；「買斷制」對免費下載＋一次解鎖的 App 容易誤解；內容只到數數 |
| en | 🔢 Lumi Math Planet — a galaxy of number adventures for kids. | 同上；"Pay once" 讓人以為要先付費 |
| ja | 🪐 Lumi Math Planet — 惑星をつくりながら算数を学ぶ | 沒寫 50 語；「買い切り」同上 |

## 貼入佇列用 JSON（與現有條目格式相同，一行一則）

```json
{"lang": "zh-Hant", "app": "6778269699", "text": "🌐 介面 50 種語言，可在 App 內切換，不必改手機語言。\n🔢【Lumi數學星球】每一題都是圖：骰子、十格框、數線、長條圖，還不識字也能玩，題目會唸給孩子聽。從數數、加減到找規律與邏輯，超過 40 種題型自動分級，答錯沒有刺耳音效。家長專區看出弱項、集中練習，還能列印練習學習單。前幾顆星球與每日挑戰免費，一次解鎖、無訂閱、無廣告、不蒐集資料。題目與語音：中英日韓。", "url": "https://apps.apple.com/app/id6778269699?pt=118326163&ct=telegram&mt=8"}
{"lang": "ko", "app": "6778269699", "text": "🌐 화면 언어 50개, 휴대폰 언어 설정은 그대로 두고 앱 안에서 바꿀 수 있어요.\n🔢 Lumi 수학 행성: 모든 문제가 주사위·십틀·수직선·막대그래프 같은 그림이라 글을 못 읽어도 할 수 있고, 문제를 소리 내어 읽어 줘요. 수 세기와 덧셈·뺄셈부터 규칙 찾기와 논리까지 40가지 이상 유형이 자동으로 단계가 올라가요. 보호자 공간에서 약점을 찾아 집중 연습하고 연습 학습지도 인쇄. 처음 행성과 매일 챌린지는 무료, 한 번 구매로 전체 해제. 구독·광고·데이터 수집 없음. 문제와 음성은 한국어 지원.", "url": "https://apps.apple.com/app/id6778269699?pt=118326163&ct=telegram&mt=8"}
{"lang": "ja", "app": "6778269699", "text": "🌐 画面の言語は50言語。スマホの設定はそのままで、アプリ内で切り替えられます。\n🔢 Lumi算数プラネット：問題はすべてサイコロ・十マス・数直線・ぼうグラフなどの絵。字が読めなくても遊べて、問題は読み上げ。かずあそび・たし算ひき算から、きまり・論理まで40種類以上が自動でレベルアップ。保護者ページで苦手を見つけて集中れんしゅう、れんしゅうプリントも印刷できます。最初の星とまいにちチャレンジは無料、一度の購入で全部解放。サブスク・広告・データ収集なし。問題と音声は日本語対応。", "url": "https://apps.apple.com/app/id6778269699?pt=118326163&ct=telegram&mt=8"}
{"lang": "en", "app": "6778269699", "text": "🌐 50 interface languages, switchable inside the app without changing your phone's language.\n🔢 Lumi Math Planet: every question is a picture (dice, ten-frames, number lines, bar charts), so pre-readers can play, and every question is read aloud. 40+ question types, from counting and adding to patterns and logic, level up automatically. The Parent Zone spots weak areas, opens focused practice and exports a printable worksheet. Start free with the first planets and the daily challenge; unlock once. No subscription, no ads, no data collected. Questions and voice in English, Chinese, Japanese and Korean.", "url": "https://apps.apple.com/app/id6778269699?pt=118326163&ct=telegram&mt=8"}
```

## 純文字版（人工貼到頻道時用）

### zh-Hant

```text
🌐 介面 50 種語言，可在 App 內切換，不必改手機語言。
🔢【Lumi數學星球】每一題都是圖：骰子、十格框、數線、長條圖，還不識字也能玩，題目會唸給孩子聽。從數數、加減到找規律與邏輯，超過 40 種題型自動分級，答錯沒有刺耳音效。家長專區看出弱項、集中練習，還能列印練習學習單。前幾顆星球與每日挑戰免費，一次解鎖、無訂閱、無廣告、不蒐集資料。題目與語音：中英日韓。
https://apps.apple.com/app/id6778269699?pt=118326163&ct=telegram&mt=8
```

### ko

```text
🌐 화면 언어 50개, 휴대폰 언어 설정은 그대로 두고 앱 안에서 바꿀 수 있어요.
🔢 Lumi 수학 행성: 모든 문제가 주사위·십틀·수직선·막대그래프 같은 그림이라 글을 못 읽어도 할 수 있고, 문제를 소리 내어 읽어 줘요. 수 세기와 덧셈·뺄셈부터 규칙 찾기와 논리까지 40가지 이상 유형이 자동으로 단계가 올라가요. 보호자 공간에서 약점을 찾아 집중 연습하고 연습 학습지도 인쇄. 처음 행성과 매일 챌린지는 무료, 한 번 구매로 전체 해제. 구독·광고·데이터 수집 없음. 문제와 음성은 한국어 지원.
https://apps.apple.com/app/id6778269699?pt=118326163&ct=telegram&mt=8
```

### ja

```text
🌐 画面の言語は50言語。スマホの設定はそのままで、アプリ内で切り替えられます。
🔢 Lumi算数プラネット：問題はすべてサイコロ・十マス・数直線・ぼうグラフなどの絵。字が読めなくても遊べて、問題は読み上げ。かずあそび・たし算ひき算から、きまり・論理まで40種類以上が自動でレベルアップ。保護者ページで苦手を見つけて集中れんしゅう、れんしゅうプリントも印刷できます。最初の星とまいにちチャレンジは無料、一度の購入で全部解放。サブスク・広告・データ収集なし。問題と音声は日本語対応。
https://apps.apple.com/app/id6778269699?pt=118326163&ct=telegram&mt=8
```

### en

```text
🌐 50 interface languages, switchable inside the app without changing your phone's language.
🔢 Lumi Math Planet: every question is a picture (dice, ten-frames, number lines, bar charts), so pre-readers can play, and every question is read aloud. 40+ question types, from counting and adding to patterns and logic, level up automatically. The Parent Zone spots weak areas, opens focused practice and exports a printable worksheet. Start free with the first planets and the daily challenge; unlock once. No subscription, no ads, no data collected. Questions and voice in English, Chinese, Japanese and Korean.
https://apps.apple.com/app/id6778269699?pt=118326163&ct=telegram&mt=8
```
