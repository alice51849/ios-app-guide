# AI Brief：三語貼文（aibriefpack-03）

| 項目 | 內容 |
|---|---|
| 用途 | 把「交給 AI 之前先整理、先處理個資」這件事講成具體動作，導向 `before-you-paste-to-ai-5-checks.html` 與 App |
| 平台／對象 | zh-Hant：Threads；ja：Threads／X（X 版請只取第一段＋最後一句，因字數限制）；en：LinkedIn／Threads |
| 發文者 | 店主 Guan Feng Lai，用**本人帳號**，正文已寫明開發者身分 |
| 發文規則 | 每帳號每天最多 3 則、同一則 21 天內不重發；正文不放連結，連結放第一則留言或簡介；不引用無出處的外洩事件數字；不點名任何 AI 服務或他牌；一律寫「不保證匿名」；不寫排名用語；商店描述沒有寫價格，所以貼文不寫價格 |
| 事實依據 | App Store 商店文案（US／TW／JP，2026-10-13 lookup）；介面 50 種語言、App 內切換（店主確認） |

> `app-posts.json` 已有第一輪三則（ct=`aibriefpack_*`）；本檔是第二輪，換成「具體動作」角度，ct 全新。

---

### 台灣：貼截圖給 AI 前的三個動作
- lang: zh-Hant
- ct: aib_tw_redact
- 平台: Threads
- 連結（放第一則留言）: https://apps.apple.com/app/id6791658210?pt=118326163&ct=aib_tw_redact&mt=8

```text
把一疊截圖丟給 AI 前，建議先做三件事：裁掉無關的部分、把姓名電話換成代號、註明每個重點出自哪張圖。

AI Brief 是我為這一步做的 iPhone App（我是開發者）。截圖、PDF、筆記、連結放進去，OCR 和 PDF 讀取在裝置上執行；每筆事實附來源和信賴度，也會列出互相矛盾、還沒回答的問題。偵測到的私密資訊不會自動刪，由你逐項保留、替換或移除，再一鍵複製去任何 AI。

它不保證完全匿名，送出前請自己讀一遍。介面 50 種語言，App 內切換。
```

### 日本：スクショだと守りにくい「個人情報を入力しない」ルール
- lang: ja
- ct: aib_jp_shanai
- 平台: Threads
- 連結（放第一則留言）: https://apps.apple.com/app/id6791658210?pt=118326163&ct=aib_jp_shanai&mt=8

```text
「生成AIに個人情報を入力しない」という社内ルール、スクショだと守るのが意外と難しいです。通知のプレビュー、トーク画面のアイコン、アドレスバー。

AI Brief（開発者です）は、スクショ・PDF・メモ・リンクを端末内でOCRし、出典と信頼度付きの事実に整理します。検出した個人情報は自動では消さず、項目ごとに保持・置換・削除を選べます。仕上がった要約はワンタップでコピーして、どのAIチャットにも貼れます。

匿名性は保証しません。送る前に必ず全文を確認してください。表示言語は50種類、アプリ内で切替可。
```

### 英文：貼進 chatbot 前先整理
- lang: en
- ct: aib_us_brief
- 平台: LinkedIn／Threads
- 連結（放第一則留言）: https://apps.apple.com/app/id6791658210?pt=118326163&ct=aib_us_brief&mt=8

```text
Before pasting screenshots into a chatbot: crop, swap names and numbers for placeholders, note where each fact came from.

I built AI Brief for iPhone for that step. OCR and PDF reading run on-device; each fact keeps its source and confidence; conflicts get flagged. Detected private details are never auto-removed: you keep, replace or remove each, then copy one brief into any AI chat.

No anonymity guarantee, so read it before you send. Interface in 50 languages, switch in-app.
```

## 給本機 Claude：併入 app-posts.json 的條目

這次雲端工作只能寫 `drafts/`，所以沒有動 `app-posts.json`。本機 Claude 審過後，可把下列物件直接加進 `posts` 陣列（`ct` 都是新的，不與第一輪重複）。

| ct | lang | 字元數（Threads 上限 500） |
|---|---|---|
| aib_tw_redact | zh-Hant | 231 |
| aib_jp_shanai | ja | 255 |
| aib_us_brief | en | 482 |

```json
[
 {
  "app": "aibriefpack",
  "app_id": "6791658210",
  "lang": "zh-Hant",
  "scenario": "台灣：貼截圖給 AI 前的三個動作",
  "ct": "aib_tw_redact",
  "text": "把一疊截圖丟給 AI 前，建議先做三件事：裁掉無關的部分、把姓名電話換成代號、註明每個重點出自哪張圖。\n\nAI Brief 是我為這一步做的 iPhone App（我是開發者）。截圖、PDF、筆記、連結放進去，OCR 和 PDF 讀取在裝置上執行；每筆事實附來源和信賴度，也會列出互相矛盾、還沒回答的問題。偵測到的私密資訊不會自動刪，由你逐項保留、替換或移除，再一鍵複製去任何 AI。\n\n它不保證完全匿名，送出前請自己讀一遍。介面 50 種語言，App 內切換。"
 },
 {
  "app": "aibriefpack",
  "app_id": "6791658210",
  "lang": "ja",
  "scenario": "日本：スクショだと守りにくい「個人情報を入力しない」ルール",
  "ct": "aib_jp_shanai",
  "text": "「生成AIに個人情報を入力しない」という社内ルール、スクショだと守るのが意外と難しいです。通知のプレビュー、トーク画面のアイコン、アドレスバー。\n\nAI Brief（開発者です）は、スクショ・PDF・メモ・リンクを端末内でOCRし、出典と信頼度付きの事実に整理します。検出した個人情報は自動では消さず、項目ごとに保持・置換・削除を選べます。仕上がった要約はワンタップでコピーして、どのAIチャットにも貼れます。\n\n匿名性は保証しません。送る前に必ず全文を確認してください。表示言語は50種類、アプリ内で切替可。"
 },
 {
  "app": "aibriefpack",
  "app_id": "6791658210",
  "lang": "en",
  "scenario": "英文：貼進 chatbot 前先整理",
  "ct": "aib_us_brief",
  "text": "Before pasting screenshots into a chatbot: crop, swap names and numbers for placeholders, note where each fact came from.\n\nI built AI Brief for iPhone for that step. OCR and PDF reading run on-device; each fact keeps its source and confidence; conflicts get flagged. Detected private details are never auto-removed: you keep, replace or remove each, then copy one brief into any AI chat.\n\nNo anonymity guarantee, so read it before you send. Interface in 50 languages, switch in-app."
 }
]
```
