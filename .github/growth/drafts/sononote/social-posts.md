# Sono Note：四語貼文（sononote-02）

| 項目 | 內容 |
|---|---|
| 用途 | 「錄音轉文字／文字起こし」大詞進不了榜，改用差異點說話：摘要＋待辦＋後續郵件、就醫範本；對準「會議記錄 摘要」「議事録 要約」「voice memo summary」「catatan suara ringkasan」 |
| 平台／對象 | zh-Hant：Threads；ja：Threads；en：Threads／LinkedIn；id：店主本人 Facebook／Threads，進在台印尼看護社團前必須先取得版主同意 |
| 發文者 | 店主 Guan Feng Lai，用**本人帳號**，正文已寫明開發者身分 |
| 發文規則 | 每帳號每天最多 3 則、同一則 21 天內不重發；正文不放連結，連結放第一則留言或簡介；**不能再寫「全程在裝置上」「no cloud」**——live 已改成「Apple 語音辨識部分語言可能傳音訊給 Apple，切『僅限本機』才全在裝置」；就醫情境一律寫「先徵得醫師同意再錄音」；不比較他牌、不寫排名用語 |
| **id 那則：需先實測介面** | 發之前店主要先實測：(1) 介面切成印尼文時，錄中文是否正確轉成中文；(2)「Hanya di perangkat／僅限本機」模式下中文是否可用。兩項都確認才發；任一項不成立就改寫或不發 |
| 事實依據 | live 商店文案（2026-10-13 lookup，US／TW／JP／ID）；介面 50 種語言、App 內切換（店主確認） |

> `app-posts.json` 已有第一輪四則（ct=`sononote_*`，隱私句已是新版）。本檔是第二輪，換了情境角度，ct 全新，可與第一輪錯開輪替。

---

### 台灣：開完會，回座位前就把記錄整理好
- lang: zh-Hant
- ct: sono_tw_summary
- 平台: Threads
- 連結（放第一則留言）: https://apps.apple.com/app/id6782139553?pt=118326163&ct=sono_tw_summary&mt=8

```text
開完會最累的常常不是開會，是回座位後還要整理會議記錄、列待辦、寫跟進信。

我是 Sono Note 的開發者。走回座位的路上，對手機說一分鐘你記得的重點，它會轉成文字，整理出摘要、重點、待辦清單，再擬一封能直接寄出的後續郵件，語氣可以選。原始錄音留在筆記裡，可以重播核對。

不用帳號、沒有廣告，我們沒有自己的伺服器。語音辨識用 Apple 的，部分語言可能傳音訊給 Apple；切到「僅限本機」就全留在手機。免費每天 3 則、每則 3 分鐘；Pro 一次買斷。產生的文字請自己再核對。介面 50 種語言，App 內切換。
```

### 日本：録ったまま聞き返していない音声メモ
- lang: ja
- ct: sono_jp_youyaku
- 平台: Threads
- 連結（放第一則留言）: https://apps.apple.com/app/id6782139553?pt=118326163&ct=sono_jp_youyaku&mt=8

```text
録ったまま聞き返していない音声メモ、溜まっていませんか。

Sono Note（開発者です）は、話した内容を文字起こしして、要約・要点・ToDo、そのまま送れるフォローアップメールまで整えます。聞き返さなくても、要点を読めば済みます。元の録音はメモの中で再生できます。

アカウント不要・広告なし・自社サーバーなし。音声認識はAppleのもので、言語によっては音声がAppleに送られることがあります。「デバイス内のみ」モードなら端末内で完結。無料は1日3件・各3分、Proは買い切り。生成文は使う前に確認を。表示言語は50種類、アプリ内で切替可。
```

### 英文：通話後要的不是逐字稿，是摘要、待辦和跟進信
- lang: en
- ct: sono_us_summary
- 平台: Threads／LinkedIn
- 連結（放第一則留言）: https://apps.apple.com/app/id6782139553?pt=118326163&ct=sono_us_summary&mt=8

```text
After a call you rarely want the raw transcript. You want the summary, the to-dos and the follow-up email.

I built Sono Note for that: talk for a minute, get a summary, key points, action items and a follow-up email in your tone.

No account, no ads, no servers of ours. Transcription uses Apple speech recognition, which may send audio to Apple for some languages; Local Only mode keeps it on-device. Free: 3 notes a day, 3 min each. Pro is one-time. Review generated text before use.
```

### 印尼：在台看護陪 Ama／Akong 看診（需先實測介面，未實測不發）
- lang: id
- ct: sono_id_dokter
- 平台: Facebook／Threads（社團需版主同意）
- 連結（放第一則留言）: https://apps.apple.com/app/id6782139553?pt=118326163&ct=sono_id_dokter&mt=8

```text
Menemani Ama atau Akong ke dokter, lalu sulit menyampaikan pesan dokter?

Saya developer Sono Note. Template kunjungan dokter: minta izin dokter dulu, rekam, lalu dapat ringkasan, poin penting, dan daftar tugas.

Tampilan bisa diganti ke Bahasa Indonesia di aplikasi (50 bahasa). Tidak ada terjemahan: dokter bicara Mandarin, teksnya tetap Mandarin.

Tanpa akun dan iklan. Suara dikenali lewat Apple; mode Hanya di perangkat menjaga semuanya di iPhone. Gratis 3 catatan sehari, maks. 3 menit.
```

## 給本機 Claude：併入 app-posts.json 的條目

這次雲端工作只能寫 `drafts/`，所以沒有動 `app-posts.json`。本機 Claude 審過後，可把下列物件直接加進 `posts` 陣列（`ct` 都是新的，不與第一輪重複）。

| ct | lang | 字元數（Threads 上限 500） |
|---|---|---|
| sono_tw_summary | zh-Hant | 262 |
| sono_jp_youyaku | ja | 274 |
| sono_us_summary | en | 486 |
| sono_id_dokter | id | 492 |

```json
[
 {
  "app": "sononote",
  "app_id": "6782139553",
  "lang": "zh-Hant",
  "scenario": "台灣：開完會，回座位前就把記錄整理好",
  "ct": "sono_tw_summary",
  "text": "開完會最累的常常不是開會，是回座位後還要整理會議記錄、列待辦、寫跟進信。\n\n我是 Sono Note 的開發者。走回座位的路上，對手機說一分鐘你記得的重點，它會轉成文字，整理出摘要、重點、待辦清單，再擬一封能直接寄出的後續郵件，語氣可以選。原始錄音留在筆記裡，可以重播核對。\n\n不用帳號、沒有廣告，我們沒有自己的伺服器。語音辨識用 Apple 的，部分語言可能傳音訊給 Apple；切到「僅限本機」就全留在手機。免費每天 3 則、每則 3 分鐘；Pro 一次買斷。產生的文字請自己再核對。介面 50 種語言，App 內切換。"
 },
 {
  "app": "sononote",
  "app_id": "6782139553",
  "lang": "ja",
  "scenario": "日本：録ったまま聞き返していない音声メモ",
  "ct": "sono_jp_youyaku",
  "text": "録ったまま聞き返していない音声メモ、溜まっていませんか。\n\nSono Note（開発者です）は、話した内容を文字起こしして、要約・要点・ToDo、そのまま送れるフォローアップメールまで整えます。聞き返さなくても、要点を読めば済みます。元の録音はメモの中で再生できます。\n\nアカウント不要・広告なし・自社サーバーなし。音声認識はAppleのもので、言語によっては音声がAppleに送られることがあります。「デバイス内のみ」モードなら端末内で完結。無料は1日3件・各3分、Proは買い切り。生成文は使う前に確認を。表示言語は50種類、アプリ内で切替可。"
 },
 {
  "app": "sononote",
  "app_id": "6782139553",
  "lang": "en",
  "scenario": "英文：通話後要的不是逐字稿，是摘要、待辦和跟進信",
  "ct": "sono_us_summary",
  "text": "After a call you rarely want the raw transcript. You want the summary, the to-dos and the follow-up email.\n\nI built Sono Note for that: talk for a minute, get a summary, key points, action items and a follow-up email in your tone.\n\nNo account, no ads, no servers of ours. Transcription uses Apple speech recognition, which may send audio to Apple for some languages; Local Only mode keeps it on-device. Free: 3 notes a day, 3 min each. Pro is one-time. Review generated text before use."
 },
 {
  "app": "sononote",
  "app_id": "6782139553",
  "lang": "id",
  "scenario": "印尼：在台看護陪 Ama／Akong 看診（需先實測介面，未實測不發）",
  "ct": "sono_id_dokter",
  "text": "Menemani Ama atau Akong ke dokter, lalu sulit menyampaikan pesan dokter?\n\nSaya developer Sono Note. Template kunjungan dokter: minta izin dokter dulu, rekam, lalu dapat ringkasan, poin penting, dan daftar tugas.\n\nTampilan bisa diganti ke Bahasa Indonesia di aplikasi (50 bahasa). Tidak ada terjemahan: dokter bicara Mandarin, teksnya tetap Mandarin.\n\nTanpa akun dan iklan. Suara dikenali lewat Apple; mode Hanya di perangkat menjaga semuanya di iPhone. Gratis 3 catatan sehari, maks. 3 menit."
 }
]
```
