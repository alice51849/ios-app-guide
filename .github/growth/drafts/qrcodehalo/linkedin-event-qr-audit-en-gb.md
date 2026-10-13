# 【暫緩 HOLD】LinkedIn 貼文（en-GB）：活動主辦方印刷 QR 前的批次檢查（qrcodehalo-05）

> **狀態：暫緩發布。** 等 qrcodehalo-03 定案後才發。en-GB 副標目前是「Inspect before you open」，與線上 v1.0.3 預設行為矛盾；身分統一前不在英國店面做安全主軸的露出。
> - 定案為 **A**（預設不自動開啟）：刪掉 "One honest note" 那段中關閉開關的句子，改成 "Scans stop at a review screen before anything opens."
> - 定案為 **B**（維持自動執行）：照現稿，關閉開關那段一字不刪。

| 項目 | 內容 |
|---|---|
| 用途 | en-GB「qr code scanner」缺席（第 1 名 184,773 則），搜尋不可行；但 scoreboard 顯示「安全連結」命名在小店面可排名。LinkedIn 上的活動主辦、行銷與場館人員，是會一次處理上百張印刷 QR 的族群，Batch Risk & Difference Audit 對他們最有具體用途 |
| 發在哪／給誰 | 店主本人 LinkedIn（個人檔案，不用公司頁硬推）。讀者：英國的活動主辦、場館營運、行銷人員，要為票券、海報、菜單、名牌印刷大量 QR |
| 發文者 | 店主 Guan Feng Lai 本人，以開發者（founder）身分發 |
| 發文規則 | 英式拼字（organise、colour、favourite）；第一段就揭露身分；**連結放第一則留言**，不放在貼文本體；hashtag 最多 3 個；不引用任何事件、統計或機關警告；不寫 "best"、"#1"、"foolproof"；不點名其他 App；同一篇不重貼 |
| 事實依據 | qrcodehalo_full.json en-GB：Batch Risk & Difference Audit（exact duplicate groups and host groups, bounded comparison of lookalike hosts, overview + individual risk + full decoded content, unrestricted reading of the complete audit）；QR Verification（local reference, compare later scan by complete SHA-256 fingerprint, QR format, content type, URL components, security level）；history export as CSV；batch scanning with duplicate suppression；three successful scans per device free；one-off Lifetime Pro adds unlimited scans, batch saving and actions, batch creation and CSV, no subscription。自動執行：線上 v1.0.3 預設掃描後執行，設定可關閉 "Run action after scanning"。50 種介面語言、App 內切換（店主確認）|
| 不能寫 | "Recognition alone never triggers an external action"（repo 舊文案，與線上不符）；"catches every fake code" |
| 發前核對 | ① qrcodehalo-03 結論；② App 英文介面中開關名稱 |
| 連結（第一則留言） | https://apps.apple.com/app/id6806779853?pt=118326163&ct=qrh_gb_linkedin_event&mt=8 |

---

## 貼文

```text
If you're printing a few hundred QR codes for an event, here's a check worth adding to the run sheet before anything goes to the printer.

(Full disclosure: I build iPhone apps, including the QR tool I mention at the end. The checklist works without it.)

QR codes are unreadable to the eye, so mistakes survive proofreading:
• two tables or two ticket types quietly share the same code
• last year's campaign link is still in the template
• a code points to a staging or test domain
• one code in the batch goes somewhere slightly different from the rest

A simple pre-print routine:
1. Export every code you're about to print and keep a list of what each one should point to.
2. Scan the proofs, not just the source files, and compare the full destination, not just "it opened something".
3. Look for duplicates where you expect unique codes, and for any destination that isn't on your list.
4. Scan a sample of the finished prints on arrival, and again on site before doors open, in case anything has been stuck over.
5. Keep the list with the venue team so whoever is on shift can spot a replaced sticker.

The tool I built for steps 2 and 3 is QR Code Halo. Its Batch Risk & Difference Audit groups a set of codes into exact duplicates and shared hosts, makes a bounded comparison of lookalike hosts, and shows every full decoded payload with its risk level. QR Verification lets you save a known-good code as a local reference and compare later scans by their full SHA-256 fingerprint. Everything runs on the phone and history exports as CSV.

One honest note: the current version runs a code's action straight after scanning by default, so turn off "Run action after scanning" in Settings before you start. It also doesn't check online reputation, so it tells you where a code goes and whether it matches your reference, not whether a site is trustworthy.

The free version includes three successful scans, which is enough to try the workflow, not to audit a print run. Unlimited scanning and saving batch results come with a one-off Lifetime Pro purchase; there's no subscription. The interface is available in 50 languages, switchable inside the app, which helps with mixed-language venue teams.

What's on your pre-print checklist that I've missed?

#EventProfs #EventPlanning #QRCodes
```

## 第一則留言

```text
App Store link for anyone who wants to try it (I'm the developer): https://apps.apple.com/app/id6806779853?pt=118326163&ct=qrh_gb_linkedin_event&mt=8
```
