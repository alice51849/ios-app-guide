# Lumi 字母星球 Lite：Telegram 佇列文案（zh-Hant／ja／ko／en）（lumiletters-04 的 Telegram 部分）

| 項目 | 內容 |
|---|---|
| 用途 | 佇列 `.github/scripts/telegram_posts.json` 裡 Lumi 字母星球 Lite（id 6778748533）只有三則一句話的舊文案，沒寫 50 種介面語言、沒寫最有差異的 PDF 學習單，還寫「買斷制／Pay once」，讓人以為要先付費。本檔是四則替換文案。「今日焦點」會自動從 `app-posts.json` 挑 zh-Hant 貼文，lumiletters 的 zh-Hant 貼文已在裡面，**不需要改程式** |
| 發在哪／給誰 | Lumi Studio 的 Telegram 頻道；zh-Hant、日文、韓文、英文讀者 |
| 發文者 | 由維護佇列的流程（店主或本機 Claude）把下面的 JSON 貼進 `telegram_posts.json`，以 Lumi Studio 頻道名義自動發出。本檔沒有改佇列、不會自動發出 |
| 發文規則 | 每則開頭寫「50 種介面語言、App 內切換、不必改手機語言」；**不寫免費版含幾個字母**（live 寫「字母 A＋第一顆星球」、資料檔寫「A–D＋兩顆星球」，ASC 未定）；PDF 學習單要寫成「解鎖後」功能；不點名其他 App；連結用 `ct=telegram`。ja／ko 名稱照目前店面（レター／레터），並在括號補「ABC アプリ／ABC 앱」，讓讀者知道是字母 App |
| 事實依據 | letters_lite_full.json（zh-Hant／ja／ko／en-US）：字母名與發音、大小寫筆順描寫與十字輔助線、聽聲音點字母、26 位字母夥伴；免費下載先試玩、一次購買解鎖 26 個字母與 14 顆星球、無訂閱；解鎖後一鍵匯出 PDF 學習單（當天練過的字母）；完全無廣告、不收集資料、可離線、購買入口在家長關卡後；3–7 歲。50 種介面語言、App 內切換（店主確認） |
| 不能寫 | 免費字母數或星球數；「四種／四十四種語言」（舊說法）；評分、排名、「最好」 |
| 連結 | https://apps.apple.com/app/id6778748533?pt=118326163&ct=telegram&mt=8 |

## 建議換掉的舊條目（在 `telegram_posts.json` 用 text 搜尋）

| lang | 舊文案開頭 | 為什麼換 |
|---|---|---|
| zh-Hant | 🔤 【Lumi Letters Lite】用遊戲學英文字母與自然發音 | 沒寫 50 語與 PDF 學習單；「買斷制」對免費下載的 App 容易誤解 |
| en | 🔤 Lumi Letters Lite — playful ABC phonics, tracing & letter games for kids. | 同上；"Pay once" 讓人以為要先付費 |
| ja | 🔤 Lumi Letters — フォニックスで英語の文字と音を学ぶ | 名稱少了 Lite、和 Pro 混淆；沒寫 50 語 |

## 貼入佇列用 JSON（與現有條目格式相同，一行一則）

```json
{"lang": "zh-Hant", "app": "6778748533", "text": "🌐 介面 50 種語言，可在 App 內切換，不必改手機語言。\n🔤【Lumi 字母星球 Lite】先聽字母名和發音，再沿著筆順和十字輔助線描大寫、小寫，聽聲音點字母，一路收集 26 位字母夥伴。免費下載先試玩，喜歡再一次購買解鎖 26 個字母和 14 顆星球，沒有訂閱；解鎖後可一鍵匯出 PDF 學習單，印出來在紙上再練。完全無廣告、不收集資料、可離線，購買入口在家長關卡後面。", "url": "https://apps.apple.com/app/id6778748533?pt=118326163&ct=telegram&mt=8"}
{"lang": "ja", "app": "6778748533", "text": "🌐 画面の言語は50言語。スマホの設定はそのままで、アプリ内で切り替えられます。\n🔤 Lumi レター Lite（3〜7歳のABCアプリ）：文字の名前と音を聞いて、大文字・小文字を書き順と十字ガイドでなぞり、音を聞いて文字をタップ。26人の文字のなかまを集めます。無料で始めて、気に入ったら一回の購入で26文字と14の星を解放、サブスクなし。解放後はその日に練習した文字のPDFプリントを書き出せます。広告なし、データ収集なし、オフラインOK、購入は保護者ゲートの奥。", "url": "https://apps.apple.com/app/id6778748533?pt=118326163&ct=telegram&mt=8"}
{"lang": "ko", "app": "6778748533", "text": "🌐 화면 언어 50개, 휴대폰 언어 설정은 그대로 두고 앱 안에서 바꿀 수 있어요.\n🔤 Lumi 레터 Lite(3~7세 ABC 앱): 글자 이름과 소리를 듣고, 대문자·소문자를 획순과 십자 가이드로 따라 쓰고, 소리를 듣고 글자를 눌러요. 26명의 글자 친구를 모아요. 무료로 먼저 놀아 보고, 마음에 들면 한 번 구매로 26글자와 14개 행성 해제, 구독 없음. 해제 후엔 그날 연습한 글자로 PDF 학습지를 내보낼 수 있어요. 광고·데이터 수집 없음, 오프라인 가능, 구매 입구는 부모 확인 뒤에.", "url": "https://apps.apple.com/app/id6778748533?pt=118326163&ct=telegram&mt=8"}
{"lang": "en", "app": "6778748533", "text": "🌐 50 interface languages, switchable inside the app without changing your phone's language.\n🔤 Lumi Letters Lite (ABC for ages 3–7): hear each letter's name and sound, trace uppercase and lowercase with stroke order and crosshair guides, tap the letter you hear, and collect 26 letter friends. Free to download and try; one purchase unlocks all 26 letters and 14 planets, no subscription. Once unlocked, export a PDF worksheet of the letters practised today. No ads, no data collected, works offline, purchase behind a parent gate.", "url": "https://apps.apple.com/app/id6778748533?pt=118326163&ct=telegram&mt=8"}
```

## 純文字版（人工貼到頻道時用）

### zh-Hant

```text
🌐 介面 50 種語言，可在 App 內切換，不必改手機語言。
🔤【Lumi 字母星球 Lite】先聽字母名和發音，再沿著筆順和十字輔助線描大寫、小寫，聽聲音點字母，一路收集 26 位字母夥伴。免費下載先試玩，喜歡再一次購買解鎖 26 個字母和 14 顆星球，沒有訂閱；解鎖後可一鍵匯出 PDF 學習單，印出來在紙上再練。完全無廣告、不收集資料、可離線，購買入口在家長關卡後面。
https://apps.apple.com/app/id6778748533?pt=118326163&ct=telegram&mt=8
```

### ja

```text
🌐 画面の言語は50言語。スマホの設定はそのままで、アプリ内で切り替えられます。
🔤 Lumi レター Lite（3〜7歳のABCアプリ）：文字の名前と音を聞いて、大文字・小文字を書き順と十字ガイドでなぞり、音を聞いて文字をタップ。26人の文字のなかまを集めます。無料で始めて、気に入ったら一回の購入で26文字と14の星を解放、サブスクなし。解放後はその日に練習した文字のPDFプリントを書き出せます。広告なし、データ収集なし、オフラインOK、購入は保護者ゲートの奥。
https://apps.apple.com/app/id6778748533?pt=118326163&ct=telegram&mt=8
```

### ko

```text
🌐 화면 언어 50개, 휴대폰 언어 설정은 그대로 두고 앱 안에서 바꿀 수 있어요.
🔤 Lumi 레터 Lite(3~7세 ABC 앱): 글자 이름과 소리를 듣고, 대문자·소문자를 획순과 십자 가이드로 따라 쓰고, 소리를 듣고 글자를 눌러요. 26명의 글자 친구를 모아요. 무료로 먼저 놀아 보고, 마음에 들면 한 번 구매로 26글자와 14개 행성 해제, 구독 없음. 해제 후엔 그날 연습한 글자로 PDF 학습지를 내보낼 수 있어요. 광고·데이터 수집 없음, 오프라인 가능, 구매 입구는 부모 확인 뒤에.
https://apps.apple.com/app/id6778748533?pt=118326163&ct=telegram&mt=8
```

### en

```text
🌐 50 interface languages, switchable inside the app without changing your phone's language.
🔤 Lumi Letters Lite (ABC for ages 3–7): hear each letter's name and sound, trace uppercase and lowercase with stroke order and crosshair guides, tap the letter you hear, and collect 26 letter friends. Free to download and try; one purchase unlocks all 26 letters and 14 planets, no subscription. Once unlocked, export a PDF worksheet of the letters practised today. No ads, no data collected, works offline, purchase behind a parent gate.
https://apps.apple.com/app/id6778748533?pt=118326163&ct=telegram&mt=8
```
