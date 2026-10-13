# AI Brief：Show HN 貼文草稿（aibriefpack-02）

| 項目 | 內容 |
|---|---|
| 用途 | 在 Hacker News 以開發者身分說明 AI Brief 的做法與限制（裝置端處理、不保證匿名），換取技術讀者的回饋 |
| 平台／對象 | Hacker News「Show HN」；對象：會把文件、截圖交給 LLM 的工程師與知識工作者 |
| 發布者 | 店主 Guan Feng Lai 用**本人 HN 帳號**（最好是有正常留言紀錄的帳號）發布並回覆 |
| HN 規則 | Show HN 必須是大家能實際試用的東西（iOS App 可以，正文要寫明只有 iOS）；標題 80 字元內、不加感嘆號或行銷用語；**不要**請任何人去 upvote，也不要讓朋友集中投票；不要重複貼；整天親自回覆，被批評也照實回答；不寫「best」「#1」；不點名比較其他產品 |
| 發布前請確認 | 1) App 內沒有內建 LLM 呼叫（否則刪掉 "there's no chatbot inside"）。2) 付費模式依 repo README 紀錄為「Free to start · one-time unlock」，若不同就改。3) 加入連結時是否會連到該網站抓內容，回覆時照實說 |
| 事實依據 | App Store 商店文案（US，2026-10-13 lookup）；介面 50 種語言、App 內切換（店主確認） |

---

## 提交欄位

- **Title**（本稿 78 字元）：`Show HN: AI Brief, an iOS app to redact and organize screenshots before an LLM`
- **URL**：https://apps.apple.com/app/id6791658210?pt=118326163&ct=aib_hn&mt=8
- 提交後立刻在自己的貼文下留第一則留言（下方正文）。

## 第一則留言（正文）

```text
Hi HN, I'm the developer.

AI Brief is an iPhone app for the step before you paste material into an LLM.

You add screenshots, PDFs, files, notes, copied text or links. OCR, PDF reading, duplicate checks, fact extraction and privacy detection run on the device using Apple frameworks. The app pulls out facts with their source and a confidence level, flags conflicts and open questions between sources, and detects private details such as names and phone numbers.

Nothing detected is removed automatically. For each item you choose keep, replace or remove, and the choice is applied when you export. The result is one structured brief that you copy into whatever assistant you use; there's no chatbot inside the app.

Things I want to be upfront about:
- It does not guarantee anonymity. Detection misses things, so the brief should be reviewed before it goes anywhere.
- iOS only.
- Free to start, with a one-time unlock, no subscription. No third-party ads, tracking, analytics or content telemetry.
- The interface is available in 50 languages, switchable inside the app.

I'd especially like to hear about detection misses you'd consider unacceptable, and what output format suits the assistants you use.
```

## 可能被問到的問題（回覆方向，照實補細節）

- **"Why not just tell the LLM to anonymize it?"** → The point is to decide what leaves your hands before it leaves: the model only sees what you chose to keep, and only if you paste it.
- **"Which Apple frameworks?"** → 只說實際用了哪些；不確定就回 "Apple's on-device frameworks; I can follow up with specifics"，之後補。
- **"Does anything hit the network?"** → OCR/PDF/detection are on-device; 若加入連結會抓網頁，就說明 "adding a link fetches that page from its site"。
- **"What does the detector catch?"** → 照 App 實際類別列；承認會漏。
- **"Android / desktop?"** → 照實回答。
