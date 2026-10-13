# AI Brief：Product Hunt 上架草稿（aibriefpack-02）

| 項目 | 內容 |
|---|---|
| 用途 | AI Brief 沒有現成搜尋需求，靠上架平台與教育內容讓人第一次看到「交給 AI 之前先整理」這一步 |
| 平台／對象 | Product Hunt（英文）；對象：經常把截圖、PDF 貼給 AI 的知識工作者、顧問、PM、研究者 |
| 發布者 | 店主 Guan Feng Lai 以**本人 Product Hunt 帳號**當 Maker 發布；首則留言以開發者身分寫 |
| Product Hunt 規則 | 發布時間建議太平洋時間 00:01；**不要**在任何地方請人「upvote」或用交換方式拉票，只能說「已經上線，歡迎留言回饋」；不要用多個帳號；整天回覆留言；圖庫與影片只用 App 真實畫面，示範資料必須是虛構的（假姓名、假電話） |
| 發布前請確認 | 1) Pricing 欄位：依 repo README 紀錄為「Free to start · one-time unlock」，選 PH 的「Free Options」；若 App 實際付費模式不同，改這裡與首則留言。2) App 內確實沒有內建聊天機器人、沒有把內容送到任何 LLM；若有，刪掉首則留言中「There's no chatbot inside」那句。3) 加入「連結」時 App 是否會連到該網站抓內容，回覆提問時照實說 |
| 事實依據 | App Store 商店文案（US，2026-10-13 lookup）；介面 50 種語言、App 內切換（店主確認） |

---

## 基本欄位

- **Name**：AI Brief
- **Tagline**（60 字元內，本稿 59）：`Review and redact screenshots before you paste them into AI`
- **Link**：https://apps.apple.com/app/id6791658210?pt=118326163&ct=aib_ph&mt=8
- **Topics**：Productivity、Privacy、Artificial Intelligence、iOS
- **Pricing**：Free Options（見上方「發布前請確認」）
- **Description**（260 字元內）：

```text
Add screenshots, PDFs, notes and links. AI Brief extracts facts with their source and confidence, flags conflicts and open questions, and lets you keep, replace or remove each detected private detail before you copy one clean brief into any AI chat.
```

## 圖庫（5 張，全部用虛構資料）

1. 封面：一疊截圖與 PDF → 一份有標題的 brief（真實 App 畫面並排）
2. 匯入來源：截圖、PDF、筆記、連結同時加入的畫面
3. 事實清單：每筆事實的來源與信賴度、一筆標出衝突
4. 隱私偵測：偵測到的假姓名「Jamie Doe」、假電話「+1 555 0100」逐項選保留／替換／移除
5. 完成：一鍵複製 brief 的畫面，角落文字「AI Brief never promises anonymity. Review before you send.」

## Maker 首則留言

```text
Hi Product Hunt, I'm Guan Feng, the developer of AI Brief.

The moment AI Brief is built for: you're about to drop a pile of screenshots, PDFs and notes into a chatbot. The answer may come back built on the wrong detail, and a client's name and phone number may go along for the ride.

AI Brief sits before the AI:
• Add screenshots, PDFs, files, copied text, notes or links, as many sources as you need
• It extracts facts, keeps each fact's source and confidence, and flags conflicts and open questions
• It detects private details but never removes anything automatically: you keep, replace or remove each one, applied at export
• Copy the finished brief in one tap and paste it into whichever AI chat you use

What it is not:
• It doesn't promise anonymity. Detection can miss things, so read the brief before sending it anywhere.
• There's no chatbot inside. The output is text, and you decide where it goes.

Privacy: OCR, PDF reading, duplicate checks, fact extraction and privacy detection use Apple frameworks on the device. No third-party ads, tracking, analytics or content telemetry.

Free to start, with a one-time unlock, no subscription. The interface is available in 50 languages and can be switched inside the app.

I'd really like feedback on two things: which kinds of private details you'd expect it to catch, and what shape of brief suits the AI tools you use.
```

## 當天要準備好的回覆（照實回答，不知道就說不知道）

- **「跟直接叫 AI 幫我去識別化有什麼不同？」**：先整理、先處理個資，再決定要不要送出；送出去之前就留在自己手上。
- **「偵測得到哪些類型？」**：照 App 實際支援的類型回答；不要列 App 沒有的類型。
- **「有沒有 Android／Mac 版？」**：照實回答目前只有 iOS（若 iPad 可用就說 iPhone 與 iPad）。
- **「會不會連網？」**：OCR、PDF 讀取、隱私偵測在裝置上；若加入連結時會去抓網頁，就照實說「adding a link fetches that page」。
