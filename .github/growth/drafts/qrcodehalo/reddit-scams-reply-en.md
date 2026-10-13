# 【暫緩 HOLD】Reddit r/scams 回覆模板：掃了可疑 QR／想在打開前確認（qrcodehalo-05）

> **狀態：暫緩發布。** 等 qrcodehalo-03 定案後才用。版本 B（不提 App）其實隨時可用，但為了不讓帳號在身分未統一前出現「安全掃描」相關發言，一併暫緩。
> - 定案為 **A**（預設不自動開啟）：版本 A 的 "turn off 'Run action after scanning'" 那句改成 "scans stop at a review screen before anything opens"。
> - 定案為 **B**（維持自動執行）：版本 A 照現稿，關閉開關那句一字不刪。

| 項目 | 內容 |
|---|---|
| 用途 | US「qr code safe」利基開放（對手 0–44 則）但我們缺席；能接觸到這群人的地方是 r/scams 上「我掃了停車收費機上的 QR 怎麼辦」「打開前怎麼確認」的真實提問 |
| 發在哪／給誰 | r/scams 的真實求助串。讀者：剛掃了可疑 QR、或付了錢擔心被騙的人 |
| 發文者 | 店主 Guan Feng Lai 本人的 Reddit 帳號 |
| 發文規則 | ① r/scams 對推廣管得很嚴，回覆前讀側欄規則；**預設只用版本 B（不提 App）**。② 版本 A 只在規則允許、而且對方問「有沒有工具可以先檢查」時用；揭露句不可刪。③ 不放連結，對方再問才私訊。④ 已經付錢或輸入卡號的人，**先給止損步驟，絕不先推 App**。⑤ 不引用任何城市警告、新聞或機關通報（報告已撤回這類寫法）。⑥ 每週最多 3 則，同一串只回一次 |
| 事實依據 | 一般止損步驟（聯絡發卡銀行、改密碼、向當地主管機關報案）。App 段落：線上 v1.0.3 預設掃描後執行，可在設定關閉 "Run action after scanning" 再從 History 用 Security Check（app-posts.json qrcodehalo_en_1）；qrcodehalo_full.json en-US：on-device parsing into scheme, host, path, query and fragment；Safe／Caution／Blocked with transparent findings；no network reputation lookup；3 free successful scans；9 QR creators；one optional Lifetime Pro purchase, no subscription。50 種介面語言、App 內切換（店主確認）|
| 不能寫 | "never auto-opens"（與線上行為不符）；"detects all phishing"；任何其他 App 名稱；具體詐騙案例或數字 |
| 連結（只在被問時私訊） | https://apps.apple.com/app/id6806779853?pt=118326163&ct=qrh_en_reddit_scams&mt=8 |

---

## 情境 1：已經掃了、而且付了錢或輸入了卡號

### 版本 B（只用這個，這個情境不提 App）

```text
If you entered card details or paid through that page, do these first, today:

1. Call your card issuer or bank using the number on the back of your card (not any number from the page you landed on). Tell them the payment may be fraudulent and ask about blocking the card and disputing the charge.
2. If you created an account or typed a password on that page, change it, and change it anywhere else you reused it.
3. If the page made you install anything, delete it.
4. Report it to your local police or your country's fraud-reporting service, and tell whoever runs the parking meter or poster where the code was, so they can remove it.
5. Screenshot what you still have: the page, the URL, the charge on your statement. It helps with the dispute.

For next time: pay for parking through the official app or a website you type in yourself, rather than a code stuck on the machine.
```

---

## 情境 2：「掃 QR 之前／打開之前要怎麼確認？」

### 版本 B（預設）

```text
A few habits that cover most of it:

- Look at the code before you scan it. A sticker on top of a printed code, peeling edges or a different thickness is a red flag.
- Read the whole domain before you tap. Your phone's camera shows where the code goes; check the spelling against the real organisation's name, and be wary of short links you don't recognise.
- The padlock (https) only means the connection is encrypted. It doesn't mean the site is legitimate.
- If the page asks you to install an app, log in, or enter card details, stop and go to the official app or a website you type yourself instead.
```

### 版本 A（規則允許＋對方問有沒有工具時，接在 B 後面）

```text
Disclosure: I'm the developer of an iPhone app for the "read before you open" step, QR Code Halo. It splits the decoded link into scheme, host, path and query on the device and gives a Safe, Caution or Blocked finding with the reasons. Important: in the current version it runs the code's action right after scanning by default, so turn off "Run action after scanning" in Settings first, then check scans from History with Security Check. It doesn't look up online reputation, so it won't flag every scam site; it just makes it obvious where a code really goes. 3 free scans, no ads or account.
```
